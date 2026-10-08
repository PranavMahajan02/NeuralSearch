"""Phase 7A-C/D: deployment configuration invariants (compose, Caddy, images, secrets)."""

import importlib
import re
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

generate_secrets = importlib.import_module("generate_secrets")


def compose(name="docker-compose.yml"):

    return yaml.safe_load((ROOT / name).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# docker-compose.yml
# ---------------------------------------------------------------------------

def test_only_caddy_publishes_ports():

    services = compose()["services"]

    assert [name for name, s in services.items() if s.get("ports")] == ["caddy"]
    assert sorted(services["caddy"]["ports"]) == ["443:443", "443:443/udp", "80:80"]


def test_data_services_are_only_on_the_internal_data_network():

    spec = compose()
    services, networks = spec["services"], spec["networks"]

    assert networks["data"]["internal"] is True and networks["app"]["internal"] is True
    for name in ("postgres", "qdrant", "redis"):
        assert services[name]["networks"] == ["data"], name
    assert "data" not in services["caddy"]["networks"]          # Caddy reaches the backend only
    assert set(services["backend"]["networks"]) == {"data", "app", "egress"}


def test_services_start_in_dependency_order_on_health():

    services = compose()["services"]

    assert {k: v["condition"] for k, v in services["backend"]["depends_on"].items()} == {
        "postgres": "service_healthy", "qdrant": "service_healthy", "redis": "service_healthy"}
    assert services["caddy"]["depends_on"] == {"backend": {"condition": "service_healthy"}}
    for name in ("postgres", "qdrant", "redis"):
        assert services[name]["healthcheck"]["test"], name


def test_secrets_are_required_and_production_is_forced():

    text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    for key in ("POSTGRES_SUPERUSER_PASSWORD", "POSTGRES_PASSWORD", "QDRANT_API_KEY", "REDIS_PASSWORD"):
        assert re.search(r"\$\{" + key + r":\?REQUIRED", text), key

    backend = compose()["services"]["backend"]
    assert backend["environment"]["ENV"] == "production"
    assert backend["environment"]["ALLOWED_LOCAL_ROOTS"] == "/data"
    assert any(v.endswith(":/data:ro") for v in backend["volumes"])


def test_container_settings_override_development_values_from_env_file():
    """The backend reads .env (env_file), which holds development values such as
    DATA_DIR=data; every path/host setting must be pinned in `environment`."""

    environment = compose()["services"]["backend"]["environment"]
    for key in ("DATABASE_URL", "QDRANT_HOST", "QDRANT_LOCATION", "REDIS_URL", "DATA_DIR", "TEMP_DIR",
                "ALLOWED_LOCAL_ROOTS", "POPPLER_PATH", "FRONTEND_URL", "BACKEND_PUBLIC_URL", "CORS_ORIGINS",
                "GOOGLE_REDIRECT_URI", "GITHUB_OAUTH_CONFIG_PATH", "GOOGLE_CLIENT_SECRET_PATH", "ENV"):
        assert key in environment, key
    assert environment["DATA_DIR"].startswith("/") and environment["TEMP_DIR"].startswith("/")


def test_the_app_database_role_is_not_a_superuser():

    postgres = compose()["services"]["postgres"]["environment"]
    script = (ROOT / "deploy/postgres/initdb/01-app-role.sh").read_text(encoding="utf-8")

    assert postgres["POSTGRES_USER"] == "postgres"          # bootstrap superuser is separate
    assert "NOSUPERUSER NOCREATEDB NOCREATEROLE" in script
    assert "CREATE EXTENSION IF NOT EXISTS pg_trgm" in script
    assert "CREATE EXTENSION IF NOT EXISTS pgcrypto" in script


def test_dev_files_never_bind_all_interfaces():

    for name in ("docker-compose.dev.yml", "docker-compose.override.example.yml"):
        for service in compose(name)["services"].values():
            for port in service.get("ports", []):
                assert port.startswith("127.0.0.1:"), (name, port)


# ---------------------------------------------------------------------------
# Caddy
# ---------------------------------------------------------------------------

CADDYFILE = (ROOT / "deploy/caddy/Caddyfile").read_text(encoding="utf-8")


def test_metrics_are_never_proxied():

    assert CADDYFILE.index("handle /api/metrics*") < CADDYFILE.index("handle_path /api/*")


def test_csp_is_strict():

    csp = re.search(r'Content-Security-Policy "([^"]+)"', CADDYFILE).group(1)

    assert "unsafe-inline" not in csp and "unsafe-eval" not in csp
    assert "script-src 'self'" in csp and "frame-ancestors 'none'" in csp and "object-src 'none'" in csp
    assert "Strict-Transport-Security" in CADDYFILE and "admin off" in CADDYFILE


def test_the_frontend_has_no_inline_scripts_or_third_party_assets():

    html = (ROOT / "frontend/index.html").read_text(encoding="utf-8")
    css = (ROOT / "frontend/src/index.css").read_text(encoding="utf-8")

    for script in re.findall(r"<script\b[^>]*>(.*?)</script>", html, re.S):
        assert script.strip() == ""                       # only <script src=...>
    assert "<style" not in html
    assert "googleapis" not in css and "http" not in css


# ---------------------------------------------------------------------------
# Images
# ---------------------------------------------------------------------------

def test_backend_image_is_non_root_and_migrates_on_start():

    dockerfile = (ROOT / "backend/Dockerfile").read_text(encoding="utf-8")
    entrypoint = (ROOT / "backend/entrypoint.sh").read_text(encoding="utf-8")

    assert "USER cogniseek" in dockerfile and "TORCH_VARIANT=cpu" in dockerfile
    assert "poppler-utils" in dockerfile and "ffmpeg" in dockerfile
    assert entrypoint.index("alembic upgrade head") < entrypoint.index("exec uvicorn")
    assert '--workers "${WORKERS:-1}"' in entrypoint and "--proxy-headers" in entrypoint


def test_container_scripts_keep_lf_line_endings():

    attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert re.search(r"^\*\.sh\s+text eol=lf$", attributes, re.M)
    for path in ("backend/entrypoint.sh", "deploy/postgres/initdb/01-app-role.sh"):
        assert b"\r\n" not in (ROOT / path).read_bytes(), path


def test_secrets_and_data_never_enter_the_build_context():

    ignored = (ROOT / ".dockerignore").read_text(encoding="utf-8").split()
    for entry in (".env", "credentials/", "data/", "backups/", ".git", "venv/"):
        assert entry in ignored, entry


# ---------------------------------------------------------------------------
# scripts/generate_secrets.py
# ---------------------------------------------------------------------------

def _values(path: Path) -> dict:

    return dict(line.split("=", 1) for line in path.read_text(encoding="utf-8").splitlines() if "=" in line)


def test_generate_secrets_fills_empty_values_only_and_prints_no_values(tmp_path, capsys):

    env = tmp_path / ".env"
    env.write_text("JWT_SECRET_KEY=\nPOSTGRES_USER=cogniseek\nPOSTGRES_PASSWORD=keep-me-please\n"
                   "DATABASE_URL=postgresql://cogniseek:change-me@localhost:5432/cogniseek\n", encoding="utf-8")

    generate_secrets.main(["--env-file", str(env)])
    first = env.read_text(encoding="utf-8")
    values = _values(env)

    assert len(values["JWT_SECRET_KEY"]) >= 32
    assert values["POSTGRES_PASSWORD"] == "keep-me-please"          # never replaced
    for key in generate_secrets.GENERATORS:
        assert values[key], key
    from cryptography.fernet import Fernet
    Fernet(values["TOKEN_ENCRYPTION_KEY"].encode())
    Fernet(values["BACKUP_ENCRYPTION_KEY"].encode())

    printed = capsys.readouterr().out
    assert values["JWT_SECRET_KEY"] not in printed and "JWT_SECRET_KEY" in printed

    generate_secrets.main(["--env-file", str(env)])                 # idempotent
    assert env.read_text(encoding="utf-8") == first


def test_generate_secrets_keeps_the_dev_database_url_in_step(tmp_path):

    env = tmp_path / ".env"
    env.write_text("POSTGRES_PASSWORD=\nDATABASE_URL=postgresql://cogniseek:change-me@localhost:5432/cogniseek\n",
                   encoding="utf-8")

    generate_secrets.main(["--env-file", str(env)])
    values = _values(env)

    assert values["DATABASE_URL"] == f"postgresql://cogniseek:{values['POSTGRES_PASSWORD']}@localhost:5432/cogniseek"


@pytest.mark.parametrize("key", list(generate_secrets.GENERATORS))
def test_env_example_lists_every_required_secret_empty(key):

    example = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert re.search(rf"^{key}=$", example, re.M), key
