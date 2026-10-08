"""Delete a throwaway end-to-end test user and ALL of their data.

    python scripts/delete_e2e_user.py e2e-1a2b3c@cogniseek.dev

Used by the Playwright smoke test (frontend/e2e) for cleanup. For safety it
only accepts e-mails of the form e2e-<id>@cogniseek.dev, so it can never
delete a real account. Removes the user's vectors (Qdrant, filtered by
user_id), ledger rows, jobs, folders, platform connections, OAuth states and
the user row. Files on disk are never touched.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import text  # noqa: E402

from app.database.db import SessionLocal  # noqa: E402
from app.database.models import User  # noqa: E402
from app.services.index_store import purge_platform  # noqa: E402

E2E_EMAIL = re.compile(r"^e2e-[a-z0-9-]{4,40}@cogniseek\.dev$")

PLATFORMS = ("local", "google_drive", "github")


def delete_user(email: str) -> bool:

    if not E2E_EMAIL.fullmatch(email):
        raise SystemExit(f"Refusing to delete {email!r}: only e2e-<id>@cogniseek.dev test users can be deleted.")

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).one_or_none()
        if user is None:
            print("no such user (already deleted)")
            return False
        user_id = user.id

    purged = sum(purge_platform(str(user_id), platform) for platform in PLATFORMS)

    with SessionLocal() as db:
        # platform_connections has no ON DELETE CASCADE; the rest cascades from users.
        db.execute(text("DELETE FROM platform_connections WHERE user_id = :u"), {"u": user_id})
        db.execute(text("DELETE FROM users WHERE id = :u"), {"u": user_id})
        db.commit()

    print(f"deleted test user and {purged} indexed files")
    return True


if __name__ == "__main__":

    if len(sys.argv) != 2:
        raise SystemExit(__doc__)

    delete_user(sys.argv[1].strip().lower())
