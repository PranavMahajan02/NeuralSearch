"""Retries for connector HTTP calls (Drive and GitHub).

- retry 429 / 5xx / connection errors / timeouts, up to MAX_TRIES attempts
- exponential backoff with full jitter, honouring Retry-After
- GitHub rate limits (X-RateLimit-Remaining: 0): wait for X-RateLimit-Reset
  if that is under MAX_RATE_LIMIT_WAIT seconds, otherwise fail the job with
  "rate limited until <time>"
- every request has a timeout
- transient network / TLS errors (ssl.SSLError, connection resets,
  IncompleteRead, httplib2 transport errors) are retried with backoff
- a 429 / rate limit seen by ONE request pauses ALL of them (CooldownGate):
  downloads run in parallel (settings.INDEX_IO_WORKERS), and the limit is per
  account, not per request
"""

import logging
import random
import threading
import time
from datetime import datetime, timezone
from typing import Callable, Optional

import requests

from app.platforms.errors import PlatformPreconditionError


logger = logging.getLogger("cogniseek.http")

MAX_TRIES = 5
BASE_DELAY = 1.0
MAX_DELAY = 30.0
MAX_RATE_LIMIT_WAIT = 60.0
DEFAULT_TIMEOUT = (10, 60)      # connect, read (seconds)

RETRY_STATUSES = {429, 500, 502, 503, 504}

# Indirection so tests can run without real sleeping.
sleep = time.sleep
now = time.time


class CooldownGate:
    """Process-wide pause shared by every connector request.

    hold(seconds) extends the pause; wait() blocks until it is over (it sleeps
    outside the lock, so other threads can extend it meanwhile)."""

    def __init__(self) -> None:

        self._lock = threading.Lock()
        self._until = 0.0

    def hold(self, seconds: float) -> None:

        with self._lock:
            self._until = max(self._until, now() + max(0.0, seconds))

    def remaining(self) -> float:

        with self._lock:
            return max(0.0, self._until - now())

    def wait(self) -> None:
        """Sleep out the current pause, once (whoever extends it meanwhile
        waits too, and every request checks again before it is sent)."""

        delay = self.remaining()
        if delay > 0:
            sleep(delay)

    def reset(self) -> None:

        with self._lock:
            self._until = 0.0


gate = CooldownGate()


class RateLimited(PlatformPreconditionError):
    """The remote API is rate limiting us for longer than we are willing to wait."""


def transient_network_errors() -> tuple:
    """Exception types that mean "the connection broke", not "the request was
    wrong": retry them (on a fresh connection, see call_with_retry's on_retry)."""

    import http.client
    import ssl

    types = [requests.ConnectionError, requests.Timeout, ConnectionError, TimeoutError,
             ssl.SSLError, http.client.IncompleteRead, http.client.HTTPException]
    try:
        import httplib2
        types.append(httplib2.HttpLib2Error)
    except ImportError:  # pragma: no cover - httplib2 ships with googleapiclient
        pass
    return tuple(types)


def backoff_delay(attempt: int) -> float:
    """Full jitter: uniform(0, min(MAX_DELAY, BASE_DELAY * 2**attempt))."""

    return random.uniform(0, min(MAX_DELAY, BASE_DELAY * (2 ** attempt)))


def _retry_after_seconds(headers) -> Optional[float]:

    value = (headers or {}).get("Retry-After")

    if not value:
        return None

    try:
        return max(0.0, float(value))
    except ValueError:
        pass

    try:
        from email.utils import parsedate_to_datetime
        return max(0.0, parsedate_to_datetime(value).timestamp() - now())
    except (TypeError, ValueError):
        return None


def rate_limit_wait(status: int, headers) -> Optional[float]:
    """Seconds to wait for a GitHub primary rate limit, or None if not one.

    Raises RateLimited when the reset is too far away to wait for."""

    headers = headers or {}

    if status not in (403, 429) or headers.get("X-RateLimit-Remaining") != "0":
        return None

    reset = headers.get("X-RateLimit-Reset")

    if not reset:
        return None

    wait = float(reset) - now()

    if wait > MAX_RATE_LIMIT_WAIT:
        until = datetime.fromtimestamp(float(reset), tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        raise RateLimited(f"GitHub API rate limited until {until}. Try again later.")

    return max(0.0, wait) + 1.0


def request(
    method: str,
    url: str,
    session: Optional[requests.Session] = None,
    max_tries: int = MAX_TRIES,
    timeout=DEFAULT_TIMEOUT,
    **kwargs
) -> requests.Response:
    """requests.request with retries. Returns the final response (any status);
    raises on connection errors after the last try or on long rate limits."""

    http = session or requests

    for attempt in range(max_tries):

        last = attempt == max_tries - 1
        gate.wait()

        try:
            response = http.request(method, url, timeout=timeout, **kwargs)
        except transient_network_errors() as error:
            if last:
                raise
            delay = backoff_delay(attempt)
            logger.warning("%s %s failed (%s); retry %d in %.1fs", method, url, type(error).__name__, attempt + 1, delay)
            sleep(delay)
            continue

        wait = rate_limit_wait(response.status_code, response.headers)

        if wait is not None:
            if last:
                return response
            logger.warning("Rate limited on %s; waiting %.0fs for the reset", url, wait)
            gate.hold(wait)          # every parallel request waits, not just this one
            continue

        if response.status_code in RETRY_STATUSES and not last:
            delay = _retry_after_seconds(response.headers)
            delay = backoff_delay(attempt) if delay is None else min(delay, MAX_RATE_LIMIT_WAIT)
            logger.warning("%s %s -> %d; retry %d in %.1fs", method, url, response.status_code, attempt + 1, delay)
            if response.status_code == 429:
                gate.hold(delay)     # account-wide: pause all parallel requests
            else:
                sleep(delay)
            continue

        return response

    return response


def call_with_retry(
    fn: Callable,
    status_of: Callable[[Exception], Optional[int]],
    headers_of: Callable[[Exception], dict] = lambda error: {},
    max_tries: int = MAX_TRIES,
    on_retry: Optional[Callable[[Exception], None]] = None
):
    """Retry a client-library call (e.g. googleapiclient .execute()) that
    raises on HTTP errors. Non-retryable errors are re-raised immediately.

    on_retry(error) runs before retrying a transient network error, e.g. to
    replace a connection that a TLS error left in an unknown state."""

    for attempt in range(max_tries):

        gate.wait()

        try:
            return fn()

        except transient_network_errors() as error:
            if attempt == max_tries - 1:
                raise
            status = None
            delay = backoff_delay(attempt)
            logger.warning("network error (%s); retry %d", type(error).__name__, attempt + 1)
            if on_retry is not None:
                on_retry(error)

        except Exception as error:
            status = status_of(error)
            if status not in RETRY_STATUSES or attempt == max_tries - 1:
                raise
            delay = _retry_after_seconds(headers_of(error))
            delay = backoff_delay(attempt) if delay is None else min(delay, MAX_RATE_LIMIT_WAIT)

        logger.warning("call failed; retry %d in %.1fs", attempt + 1, delay)
        if status == 429:
            gate.hold(delay)
        else:
            sleep(delay)
