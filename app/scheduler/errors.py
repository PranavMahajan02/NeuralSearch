"""Turn exceptions into messages that are safe to store and show to the user."""

import re
from collections.abc import Iterable
from pathlib import Path

MAX_MESSAGE_LENGTH = 500

# Credentials that could appear in exception text (URLs, headers, reprs).
_BEARER = re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]+")
_TOKEN_LITERALS = re.compile(
    r"\b(?:ghp|gho|ghu|ghs|ghr|github_pat)_[A-Za-z0-9_]{10,}"
    r"|\bya29\.[A-Za-z0-9._-]+"
    r"|\b1//[A-Za-z0-9._-]{6,}"
    r"|\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"  # JWTs
)
# code/state: OAuth callback query strings (e.g. in access logs).
_KEY_VALUE = re.compile(
    r"(?i)\b(access_token|refresh_token|client_secret|id_token|token|password|secret|api_key|key|code|state)"
    r"=([^&\s'\"]+)"
)
_JSON_SECRET = re.compile(
    r"(?i)(['\"](?:access_token|refresh_token|client_secret|id_token|token|password)['\"]\s*:\s*['\"])[^'\"]+"
)

# Absolute paths. Windows segments may contain spaces ("C:\Users\Jane Doe\x");
# the last segment ends at whitespace. A drive letter must not follow a
# letter, so the "s:/" in "https://" is not taken for a path.
_WINDOWS_PATH = re.compile(
    r"(?<![A-Za-z])[A-Za-z]:[\\/](?:[^\\/\r\n'\"<>|*?:]+[\\/])*[^\\/\s'\"<>|*?:,;)\]]*"
    r"|\\\\[^\\\s'\"<>|*?:]+\\(?:[^\\\r\n'\"<>|*?:]+\\)*[^\\\s'\"<>|*?:,;)\]]*"
)
_POSIX_PATH = re.compile(r"(?<![\w.:/])/(?:[^/\s'\"<>]+/)+[^/\s'\"<>,;)\]]*")


# Request URLs (with their query strings) never belong in a stored error.
_URL = re.compile(r"(?i)\b(?:https?|wss?|ftp)://[^\s'\"<>]+")


def _redact_urls(text: str) -> str:

    return _URL.sub("<url>", text)


def redact_secrets(text: str) -> str:
    """Bearer tokens, provider token literals, JWTs and secret key=value pairs -> <redacted>.
    Also used by the log filter (app/core/logging_setup.py)."""

    text = _BEARER.sub("<redacted>", text)
    text = _TOKEN_LITERALS.sub("<redacted>", text)
    text = _KEY_VALUE.sub(lambda m: f"{m.group(1)}=<redacted>", text)
    text = _JSON_SECRET.sub(lambda m: f"{m.group(1)}<redacted>", text)

    return text


def _redact_paths(text: str, allowed_roots: Iterable[Path]) -> str:
    """Replace absolute paths with <path>, except paths inside allowed_roots
    (the user's own folders, the job temp dir), which stay readable."""

    protected = []

    def protect(match):
        protected.append(match.group(0))
        return f"\x00{len(protected) - 1}\x00"

    for root in allowed_roots:
        if not root:
            continue
        root_text = str(Path(root))
        for variant in {root_text, root_text.replace("\\", "/")}:
            # The root itself (it may contain spaces) plus the rest of the
            # path up to the next whitespace.
            pattern = re.compile(re.escape(variant) + r"[^\s'\"<>|*?]*", re.IGNORECASE)
            text = pattern.sub(protect, text)

    text = _WINDOWS_PATH.sub("<path>", text)
    text = _POSIX_PATH.sub("<path>", text)

    for index, original in enumerate(protected):
        text = text.replace(f"\x00{index}\x00", original)

    return text


def sanitize_error(error: BaseException, allowed_roots: Iterable[Path] = (), with_type: bool = True) -> str:
    """ "ExceptionType: message" with URLs, secrets and out-of-scope paths removed.

    with_type=False keeps only the message (for errors written for users)."""

    message = str(error).strip()

    text = type(error).__name__ + (f": {message}" if message else "") if with_type else message or type(error).__name__

    text = _redact_urls(text)
    text = redact_secrets(text)
    text = _redact_paths(text, list(allowed_roots))

    if len(text) > MAX_MESSAGE_LENGTH:
        text = text[: MAX_MESSAGE_LENGTH - 1] + "…"

    return text
