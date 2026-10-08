"""Account-level operations: delete everything of a user, export a user's data.

delete_account() is the single code path used by DELETE /auth/account and by
the admin cleanup script (scripts/delete_user.py).
"""

import logging
import shutil
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional

from qdrant_client.models import FilterSelector
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.models import (
    IndexedFile,
    IndexingJob,
    LocalStorageFolder,
    PlatformConnection,
    User,
)
from app.vectorstore.client import get_client
from app.vectorstore.config import all_collections
from app.vectorstore.query import user_filter


logger = logging.getLogger("cogniseek.account")


class JobStillRunning(Exception):
    """A running indexing job could still write points for this user."""


@dataclass
class DeletionReport:
    revoked: Dict[str, Optional[bool]] = field(default_factory=dict)
    points_deleted: Dict[str, int] = field(default_factory=dict)
    ledger_rows: int = 0
    upload_dir_removed: bool = False


def _revokers() -> Dict[str, Callable[[str], bool]]:

    from app.platforms.github.oauth import revoke_grant
    from app.platforms.google_drive.drive_service import revoke_token

    return {"google_drive": revoke_token, "github": revoke_grant}


def revoke_platform_tokens(db: Session, user_id) -> Dict[str, Optional[bool]]:
    """Revoke every stored Drive/GitHub grant at the provider (best effort: a
    token that is already invalid or a provider outage must not block the deletion)."""

    revokers = _revokers()
    result = {}

    for connection in db.query(PlatformConnection).filter(PlatformConnection.user_id == user_id):
        token = connection.refresh_token or connection.access_token
        revoke = revokers.get(connection.platform)
        if not token or revoke is None:
            result[connection.platform] = None
            continue
        try:
            result[connection.platform] = bool(revoke(token))
        except Exception as error:  # never let a provider error keep the data
            logger.warning("revoke failed for %s: %s", connection.platform, type(error).__name__)
            result[connection.platform] = False

    return result


def delete_account(db: Session, user_id, require_idle: bool = True) -> DeletionReport:
    """Delete a user and ALL of their data: platform grants (revoked first), vectors in
    every collection (filtered by user_id), ledger, jobs (+ errors, cascade), folders,
    connections, OAuth states, history, the upload directory and the user row.
    Existing tokens die with the user row (get_current_user finds no user)."""

    from app.core.ownership import user_upload_dir
    from app.scheduler.jobs import cancel_user_jobs

    report = DeletionReport()

    # A running job could keep writing points after the purge: stop it first.
    cancel_user_jobs(db, user_id)
    running = db.query(IndexingJob).filter(IndexingJob.user_id == user_id, IndexingJob.status == "running").count()
    if require_idle and running:
        raise JobStillRunning()

    report.revoked = revoke_platform_tokens(db, user_id)

    client = get_client()
    selector = FilterSelector(filter=user_filter(str(user_id), "all"))
    for name in all_collections():
        if not client.collection_exists(name):
            continue
        before = client.count(name, count_filter=selector.filter, exact=True).count
        client.delete(collection_name=name, points_selector=selector, wait=True)
        report.points_deleted[name] = before

    report.ledger_rows = db.query(IndexedFile).filter(IndexedFile.user_id == user_id).count()

    # Explicit deletes for tables without ON DELETE CASCADE; the rest cascades from users.
    db.query(PlatformConnection).filter(PlatformConnection.user_id == user_id).delete(synchronize_session=False)
    db.query(LocalStorageFolder).filter(LocalStorageFolder.user_id == user_id).delete(synchronize_session=False)
    db.execute(text("DELETE FROM users WHERE id = :u"), {"u": str(user_id)})
    db.commit()

    upload_dir = user_upload_dir(user_id)
    if upload_dir.exists():
        shutil.rmtree(upload_dir, ignore_errors=True)
        report.upload_dir_removed = True

    logger.info("account deleted: %d ledger rows, points %s", report.ledger_rows, report.points_deleted)

    return report


def export_account(db: Session, user_id) -> dict:
    """Everything CogniSeek stores about the user, without secrets or contents:
    profile, connections (account names only), folders, jobs, and the file ledger."""

    from app.core.clock import iso
    from app.scheduler.jobs import serialize_job

    user = db.get(User, user_id)

    return {
        "format": "cogniseek-export-v1",
        "profile": {"id": str(user.id), "name": user.full_name, "email": user.email,
                    "created_at": iso(user.created_at), "onboarding_completed": bool(user.onboarding_completed)},
        "connections": [
            {"platform": c.platform, "account_email": c.account_email, "account_name": c.account_name,
             "connected": bool(c.connected)}
            for c in db.query(PlatformConnection).filter(PlatformConnection.user_id == user_id)
        ],
        "local_folders": [f.folder_path for f in db.query(LocalStorageFolder).filter(LocalStorageFolder.user_id == user_id)],
        "jobs": [
            {k: (iso(v) if hasattr(v, "isoformat") else v) for k, v in serialize_job(job).items()}
            for job in db.query(IndexingJob).filter(IndexingJob.user_id == user_id).order_by(IndexingJob.created_at)
        ],
        "files": [
            {"platform": f.platform, "file_name": f.file_name, "path": f.display_path, "type": f.file_type,
             "version": f.version, "status": f.status, "indexed_at": iso(f.indexed_at)}
            for f in db.query(IndexedFile).filter(IndexedFile.user_id == user_id).order_by(IndexedFile.platform, IndexedFile.display_path)
        ],
    }
