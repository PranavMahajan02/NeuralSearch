"""Phase 7A-D3/E: health vs readiness, request ids, redacted logs, metrics."""

import io
import json
import logging

from app.core.logging_setup import build_handler, request_id_var


# ---------------------------------------------------------------------------
# Health / readiness
# ---------------------------------------------------------------------------

def test_health_is_a_dependency_free_liveness_probe(client):

    response = client.get("/health")

    assert response.status_code == 200 and response.json() == {"status": "ok"}


def test_ready_checks_every_dependency(client):

    body = client.get("/ready").json()

    assert body["status"] == "ready"
    assert set(body["checks"]) == {"database", "qdrant", "redis", "models"}


def test_ready_is_503_when_a_dependency_is_down_without_leaking_details(client, monkeypatch):

    import app.routes.health as health

    def qdrant_down():
        raise ConnectionError("qdrant:6333 refused, api-key=hunter2")

    monkeypatch.setitem(health.CHECKS, "qdrant", qdrant_down)

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json()["checks"]["qdrant"] is False
    assert "hunter2" not in response.text and "6333" not in response.text


# ---------------------------------------------------------------------------
# Request ids
# ---------------------------------------------------------------------------

def test_every_response_has_a_request_id(client):

    first = client.get("/health").headers["X-Request-ID"]
    second = client.get("/health").headers["X-Request-ID"]

    assert len(first) >= 8 and first != second


def test_a_well_formed_incoming_request_id_is_kept_and_a_bad_one_replaced(client):

    kept = client.get("/health", headers={"X-Request-ID": "caddy-req-12345678"})
    replaced = client.get("/health", headers={"X-Request-ID": "bad id\r\nSet-Cookie: x"})

    assert kept.headers["X-Request-ID"] == "caddy-req-12345678"
    assert replaced.headers["X-Request-ID"] != "bad id" and "\n" not in replaced.headers["X-Request-ID"]


# ---------------------------------------------------------------------------
# Logs never contain secrets
# ---------------------------------------------------------------------------

SECRETS = {
    "bearer": "Authorization: Bearer abcDEF123456.secretpart",
    "google": "token ya29.A0ARrdaM-secretvalue",
    "github": "pat ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345",
    # Assembled at runtime so secret scanners do not flag a fake token in the source.
    "jwt": "jwt " + ".".join(["eyJ" + "hbGciOiJIUzI1NiJ9", "eyJ" + "1c2VyX2lkIjoiMTIzNCJ9", "c2lnbmF0dXJlc2VjcmV0"]),
    "query": "GET /platforms/google-drive/callback?code=4/0AQSTgQsecret&state=statesecret123 200",
    "json": '{"refresh_token": "1//0gsecretrefresh"}',
}


def _capture(log_format):

    stream = io.StringIO()
    handler = build_handler(log_format)
    handler.setStream(stream)
    logger = logging.getLogger("cogniseek.test-redaction")
    logger.handlers[:] = [handler]
    logger.propagate = False
    return logger, stream


def test_log_filter_redacts_tokens_in_messages_args_and_tracebacks():

    logger, stream = _capture("text")

    for value in SECRETS.values():
        logger.warning("%s", value)
    try:
        raise RuntimeError("failed with access_token=supersecret-access")
    except RuntimeError:
        logger.exception("provider call failed")

    output = stream.getvalue()
    for leaked in ("secretpart", "secretvalue", "ghp_ABCDEF", "c2lnbmF0dXJlc2VjcmV0", "0AQSTgQsecret",
                   "statesecret123", "0gsecretrefresh", "supersecret-access"):
        assert leaked not in output, leaked
    assert output.count("<redacted>") >= len(SECRETS)


def test_json_logs_are_one_object_per_line_with_the_request_id():

    logger, stream = _capture("json")
    token = request_id_var.set("req-abc12345")
    try:
        logger.info("searching %s", SECRETS["bearer"])
    finally:
        request_id_var.reset(token)

    entry = json.loads(stream.getvalue().strip())
    assert entry["request_id"] == "req-abc12345"
    assert entry["level"] == "INFO" and "secretpart" not in entry["message"]
    assert entry["ts"].endswith("+00:00")


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def test_metrics_expose_http_search_and_job_series(client, user, monkeypatch):

    import app.routes.search as search_route

    monkeypatch.setattr(search_route, "search", lambda **_: {"total": 0, "results": [], "possible_matches": []})
    client.post("/search/", json={"query": "q"}, headers=user["headers"])

    text = client.get("/metrics").text

    assert "cogniseek_search_seconds_count" in text
    assert "http_request_duration_seconds" in text
    assert "cogniseek_index_jobs_total" in text
