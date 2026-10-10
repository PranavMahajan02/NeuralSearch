"""Phase 7A-F: timezone-aware UTC everywhere."""

import importlib.util
import re
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import text

from app.core.clock import iso, utcnow
from app.database.db import SessionLocal, engine
from app.database.models import IndexingJob

ROOT = Path(__file__).resolve().parent.parent


def test_no_naive_utcnow_left():

    offenders = [
        str(path.relative_to(ROOT))
        for folder in ("app", "scripts", "alembic", "tests")
        for path in (ROOT / folder).rglob("*.py")
        if "datetime.utcnow(" in path.read_text(encoding="utf-8") and path.name != "test_utc.py"
    ]
    assert offenders == []


def test_clock_is_aware_and_iso_has_an_offset():

    assert utcnow().tzinfo is UTC
    assert iso(datetime(2026, 1, 2, 3, 4, 5)) == "2026-01-02T03:04:05+00:00"   # legacy naive = UTC
    assert iso(None) is None


def test_every_timestamp_column_is_timestamptz():

    with SessionLocal() as db:
        naive = db.execute(text(
            "SELECT table_name || '.' || column_name FROM information_schema.columns "
            "WHERE table_schema = current_schema() AND data_type = 'timestamp without time zone'"
        )).scalars().all()
    assert naive == []


def test_api_timestamps_carry_an_offset(client, user):

    with SessionLocal() as db:
        db.add(IndexingJob(user_id=user["id"], platform="local", status="completed",
                           started_at=utcnow(), completed_at=utcnow()))
        db.commit()

    jobs = client.get("/index/jobs", headers=user["headers"]).json()
    exported = client.get("/auth/export", headers=user["headers"]).json()

    for value in (jobs[0]["started_at"], exported["profile"]["created_at"], exported["jobs"][0]["completed_at"]):
        assert re.search(r"(\+00:00|Z)$", value), value


def test_the_migration_keeps_the_utc_wall_clock(user):

    spec = importlib.util.spec_from_file_location("m0014", ROOT / "alembic" / "versions" / "0014_timestamptz.py")
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    with engine.begin() as conn, Operations.context(MigrationContext.configure(conn)):
        migration.downgrade()
        conn.execute(text(
            "INSERT INTO oauth_states (state, user_id, platform, expires_at) "
            "VALUES ('utc-check', :u, 'github', TIMESTAMP '2026-05-01 12:00:00')"
        ), {"u": user["id"]})
        migration.upgrade()
        value = conn.execute(text("SELECT expires_at FROM oauth_states WHERE state = 'utc-check'")).scalar()
        conn.execute(text("DELETE FROM oauth_states WHERE state = 'utc-check'"))

    assert value == datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
