"""Connector transports under the parallel pipeline (INDEX_IO_WORKERS > 1).

Bug: the 7A.5 pipeline shared ONE googleapiclient service / httplib2.Http
between download threads; httplib2 is not thread-safe, so concurrent downloads
corrupted the shared TLS connection (SSL bad record mac / wrong version number).
Fix: one authorized transport per thread (DriveClient.thread_http), one
requests.Session per thread (GitHubClient.session), and TLS / connection errors
retried on a fresh transport.
"""

import datetime
import http.server
import ipaddress
import socketserver
import ssl
import threading
import time
from pathlib import Path

import httplib2
import pytest

from app.platforms import http as connector_http
from app.platforms.indexing import process_files

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


class Ctx:
    """The part of JobContext that process_files uses."""

    def __init__(self):
        self.lock = threading.Lock()
        self.ok, self.failed = 0, []

    def is_cancelled(self):
        return False

    def start_file(self, ref):
        pass

    def file_succeeded(self):
        with self.lock:
            self.ok += 1

    def file_failed(self, ref, error):
        with self.lock:
            self.failed.append((ref, repr(error)))

    def report_progress(self, force=False):
        pass


def drive_service(api_endpoint="https://www.googleapis.com"):
    """The REAL googleapiclient Drive service (bundled discovery doc, no network)."""

    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    credentials = Credentials(token="test-token")
    service = build(
        "drive",
        "v3",
        credentials=credentials,
        static_discovery=True,
        cache_discovery=False,
        client_options={"api_endpoint": api_endpoint},
    )
    return credentials, service


class GuardedHttp:
    """An httplib2-like transport that records concurrent use by two threads."""

    violations = []

    def __init__(self, payload: bytes, delay: float = 0.002):
        self.payload, self.delay = payload, delay
        self.busy = threading.Lock()
        self.threads = set()

    def request(self, uri, method="GET", body=None, headers=None, **kwargs):
        if not self.busy.acquire(blocking=False):
            GuardedHttp.violations.append((id(self), threading.get_ident()))
            self.busy.acquire()
        try:
            self.threads.add(threading.get_ident())
            time.sleep(self.delay)  # widen the window a shared object would hit
            response = httplib2.Response(
                {"status": "200", "content-range": f"bytes 0-{len(self.payload) - 1}/{len(self.payload)}"}
            )
            return response, self.payload
        finally:
            self.busy.release()


@pytest.fixture
def drive_client(user, db, monkeypatch):

    from app.platforms.google_drive.drive_service import DriveClient

    def make(**kwargs):
        credentials, service = drive_service(kwargs.pop("api_endpoint", "https://www.googleapis.com"))
        return DriveClient(user["id"], credentials, service=service, **kwargs)

    return make


def download_all(client, tmp_path, count=50, workers=4):

    ctx = Ctx()
    files = [{"id": f"file{n}", "mimeType": "application/pdf"} for n in range(count)]
    results = {}

    def handle(position, file):
        path = client.download(file, tmp_path / f"{file['id']}.bin")
        results[file["id"]] = Path(path).read_bytes()

    process_files(ctx, files, lambda f: f["id"], handle, workers=workers, prefetch=8)
    return ctx, results


# ---------------------------------------------------------------------------
# 1. No transport is ever used by two threads at once
# ---------------------------------------------------------------------------


def test_parallel_drive_downloads_use_one_transport_per_thread(drive_client, tmp_path):

    GuardedHttp.violations = []
    created = []

    def factory():
        transport = GuardedHttp(b"%PDF-1.4 hello")
        created.append(transport)
        return transport

    client = drive_client(http_factory=factory)

    ctx, results = download_all(client, tmp_path)

    assert ctx.failed == [] and ctx.ok == 50
    assert all(content == b"%PDF-1.4 hello" for content in results.values())
    assert GuardedHttp.violations == []  # never two threads on one transport
    assert 1 <= len(created) <= 4  # one per worker thread, reused
    assert all(len(t.threads) == 1 for t in created)


def test_the_old_shared_transport_is_detected_as_unsafe(drive_client, tmp_path):
    """Control: the pre-fix behaviour (one transport for all threads) trips the guard."""

    GuardedHttp.violations = []
    shared = GuardedHttp(b"x", delay=0.005)
    client = drive_client(http_factory=lambda: shared)

    download_all(client, tmp_path, count=30)

    assert GuardedHttp.violations, "the instrumented transport must catch concurrent use"


# ---------------------------------------------------------------------------
# 2. Real TLS: 50 parallel downloads from a local HTTPS server, 0 errors
# ---------------------------------------------------------------------------


def self_signed_cert(directory: Path):

    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "127.0.0.1")])
    now = datetime.datetime.now(datetime.UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=1))
        .not_valid_after(now + datetime.timedelta(hours=1))
        .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]), False)
        .sign(key, hashes.SHA256())
    )
    cert_path, key_path = directory / "cert.pem", directory / "key.pem"
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    )
    return cert_path, key_path


@pytest.fixture
def https_server(tmp_path):

    cert, key = self_signed_cert(tmp_path)

    class Handler(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"  # keep-alive: connections are reused, as with Google

        def do_GET(self):
            file_id = self.path.split("/files/")[1].split("?")[0]
            body = (f"content of {file_id} " * 2000).encode()  # ~30 KB, several TLS records
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Content-Range", f"bytes 0-{len(body) - 1}/{len(body)}")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
        daemon_threads = True

    server = Server(("127.0.0.1", 0), Handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert, key)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"https://127.0.0.1:{server.server_address[1]}", str(cert)
    server.shutdown()


def test_fifty_parallel_tls_downloads_with_real_transports(drive_client, https_server, tmp_path):

    import google_auth_httplib2

    endpoint, ca = https_server
    client = None

    def factory():
        return google_auth_httplib2.AuthorizedHttp(client.credentials, http=httplib2.Http(ca_certs=ca, timeout=10))

    client = drive_client(api_endpoint=endpoint, http_factory=factory)

    ctx, results = download_all(client, tmp_path, count=50, workers=4)

    assert ctx.failed == [] and ctx.ok == 50
    for file_id, content in results.items():
        assert content == (f"content of {file_id} " * 2000).encode()


# ---------------------------------------------------------------------------
# 3. A TLS error is retried on a fresh transport
# ---------------------------------------------------------------------------


def test_a_single_ssl_error_is_retried_on_a_fresh_transport_and_succeeds(drive_client, tmp_path, monkeypatch):

    monkeypatch.setattr(connector_http, "sleep", lambda s: None)
    transports = []

    class FlakyOnce(GuardedHttp):
        def request(self, *args, **kwargs):
            if len(transports) == 1:
                raise ssl.SSLError("DECRYPTION_FAILED_OR_BAD_RECORD_MAC")
            return super().request(*args, **kwargs)

    def factory():
        transport = FlakyOnce(b"%PDF ok")
        transports.append(transport)
        return transport

    client = drive_client(http_factory=factory)

    path = client.download({"id": "F", "mimeType": "application/pdf"}, tmp_path / "f.pdf")

    assert Path(path).read_bytes() == b"%PDF ok"
    assert len(transports) == 2  # the broken connection was replaced


@pytest.mark.parametrize(
    "error",
    [
        ssl.SSLError("WRONG_VERSION_NUMBER"),
        httplib2.ServerNotFoundError("dns"),
        ConnectionResetError("reset"),
        __import__("http.client").client.IncompleteRead(b"partial"),
    ],
)
def test_transient_network_errors_are_retryable(monkeypatch, error):

    monkeypatch.setattr(connector_http, "sleep", lambda s: None)
    calls, resets = [], []

    def flaky():
        calls.append(1)
        if len(calls) == 1:
            raise error
        return "ok"

    result = connector_http.call_with_retry(flaky, status_of=lambda e: None, on_retry=resets.append)

    assert result == "ok" and len(calls) == 2 and resets == [error]


def test_requests_path_retries_an_ssl_error(monkeypatch):

    monkeypatch.setattr(connector_http, "sleep", lambda s: None)
    attempts = []

    class Session:
        def request(self, method, url, timeout=None, **kwargs):
            attempts.append(url)
            if len(attempts) == 1:
                raise ssl.SSLError("internal error")
            return type("R", (), {"status_code": 200, "headers": {}})()

    assert connector_http.request("GET", "https://api.github.com/x", session=Session()).status_code == 200
    assert len(attempts) == 2


def test_a_persistent_tls_failure_ends_as_a_sanitized_file_error(drive_client, tmp_path, monkeypatch):

    from app.scheduler.errors import sanitize_error

    monkeypatch.setattr(connector_http, "sleep", lambda s: None)

    class AlwaysBroken(GuardedHttp):
        def request(self, *args, **kwargs):
            raise ssl.SSLError("[SSL: WRONG_VERSION_NUMBER] https://www.googleapis.com/x?access_token=secret123")

    client = drive_client(http_factory=lambda: AlwaysBroken(b""))

    with pytest.raises(ssl.SSLError) as caught:
        client.download({"id": "F", "mimeType": "application/pdf"}, tmp_path / "f.pdf")

    message = sanitize_error(caught.value)
    assert "secret123" not in message and "googleapis.com" not in message


# ---------------------------------------------------------------------------
# 4. Refreshed credentials are saved once
# ---------------------------------------------------------------------------


def test_a_refreshed_token_is_persisted_exactly_once(drive_client, monkeypatch):

    import app.platforms.google_drive.drive_service as drive

    saved = []
    monkeypatch.setattr(
        drive, "persist_credentials", lambda user_id, creds: saved.append(creds.token) or time.sleep(0.01)
    )
    client = drive_client(http_factory=lambda: GuardedHttp(b""))
    client.credentials.token = "refreshed-token"

    threads = [threading.Thread(target=client.save_if_refreshed) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert saved == ["refreshed-token"]


# ---------------------------------------------------------------------------
# 5. GitHub: one requests.Session per thread
# ---------------------------------------------------------------------------


def test_github_client_gives_every_thread_its_own_session():

    from app.platforms.github.github_service import GitHubClient

    client = GitHubClient("token")
    sessions, barrier = {}, threading.Barrier(4)

    def grab(n):
        barrier.wait()
        sessions[n] = client.session
        assert client.session is sessions[n]  # stable within a thread

    threads = [threading.Thread(target=grab, args=(n,)) for n in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len({id(s) for s in sessions.values()}) == 4
    assert all(s.headers["Authorization"] == "Bearer token" for s in sessions.values())


# ---------------------------------------------------------------------------
# 6. Qdrant client and DB sessions under the same parallel load
# ---------------------------------------------------------------------------


def test_parallel_upserts_and_ledger_writes_are_safe(user):
    """qdrant-client's HTTP transport is httpx.Client (documented thread-safe);
    the ledger opens one SQLAlchemy session per call from a thread-safe pool."""

    from app.services import index_store
    from app.services.index_store import FileMeta, IndexPoint
    from tests.conftest import _bag_of_words_vector

    ctx = Ctx()

    def handle(position, n):
        meta = FileMeta(
            user_id=user["id"],
            platform="google_drive",
            source_id=f"par-{n}",
            file_name=f"f{n}.txt",
            display_path=f"f{n}.txt",
            file_type="document",
            version="1",
        )
        index_store.upsert_file(meta, [IndexPoint("document", _bag_of_words_vector(f"word{n}", 384), 0, f"word{n}")])

    process_files(ctx, list(range(40)), str, handle, workers=4)

    assert ctx.failed == [] and ctx.ok == 40
    assert len(index_store.list_sources(user["id"], "google_drive")) == 40


def test_only_the_local_in_process_qdrant_is_serialized():

    from qdrant_client import QdrantClient

    from app.vectorstore.client import _Serialized, _thread_safe

    assert isinstance(_thread_safe(QdrantClient(":memory:")), _Serialized)
    server = QdrantClient(host="127.0.0.1", port=1, https=False)  # no request is sent
    assert _thread_safe(server) is server
