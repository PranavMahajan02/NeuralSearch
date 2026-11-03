"""Delete a user and ALL of their data (admin; same code path as DELETE /auth/account).

    python scripts/delete_user.py someone@example.com --dry-run
    python scripts/delete_user.py someone@example.com

Revokes the user's Drive/GitHub grants, deletes their vectors in every collection,
their ledger, jobs, folders, connections, OAuth states, upload directory and the user.
The owner account(s) in COGNISEEK_OWNER_EMAIL (env or .env) are refused unconditionally;
without that setting the script refuses to run unless --no-owner-protection is given.
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.core.config import settings  # noqa: E402
from app.database.db import SessionLocal  # noqa: E402
from app.database.models import IndexedFile, User  # noqa: E402
from app.services.account_service import delete_account  # noqa: E402


def protected_emails() -> set[str]:
    return {e.strip().lower() for e in settings.COGNISEEK_OWNER_EMAIL.split(",") if e.strip()}


def mask(email: str) -> str:
    name, _, domain = email.partition("@")
    return f"{name[:2]}***@{domain}"


def main(email: str, dry_run: bool, owner_protection: bool = True) -> int:

    email = email.strip().lower()
    protected = protected_emails()
    if owner_protection and not protected:
        raise SystemExit("Set COGNISEEK_OWNER_EMAIL (the owner account to protect) or pass --no-owner-protection.")
    if email in protected:
        raise SystemExit(f"Refusing: {mask(email)} is protected.")

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).one_or_none()
        if user is None:
            print(f"{mask(email)}: no such user")
            return 0
        files = db.query(IndexedFile).filter(IndexedFile.user_id == user.id).count()
        print(f"{mask(email)} ({str(user.id)[:8]}…): {files} ledger rows")
        if dry_run:
            return 0
        report = delete_account(db, user.id)
    print(
        f"deleted {mask(email)}: revoked {report.revoked}, points {report.points_deleted}, "
        f"ledger rows {report.ledger_rows}, upload dir removed {report.upload_dir_removed}"
    )
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("email")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-owner-protection", action="store_true", help="run without COGNISEEK_OWNER_EMAIL set")
    args = parser.parse_args()
    sys.exit(main(args.email, args.dry_run, owner_protection=not args.no_owner_protection))
