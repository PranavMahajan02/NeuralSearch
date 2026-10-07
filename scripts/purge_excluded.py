"""Remove already-indexed files that match INDEX_EXCLUDE_GLOBS (generated/noise files).

    python scripts/purge_excluded.py --dry-run            # list counts, change nothing
    python scripts/purge_excluded.py                      # delete them (every user)
    python scripts/purge_excluded.py --email a@b.com      # one user only

Deletes per user through index_store.delete_sources (vectors + ledger rows),
so another user's data is never touched. The next indexing run records the
files as 'excluded' instead of indexing them again. Files on disk, in Drive or
on GitHub are never touched. Prints counts and platforms only, not file names
(--show-names prints them).
"""

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.database.db import SessionLocal  # noqa: E402
from app.database.models import IndexedFile, User  # noqa: E402
from app.platforms.indexing import is_excluded  # noqa: E402
from app.services import index_store  # noqa: E402


def find_matches(session_factory=SessionLocal, email=None):
    """{user_id: {platform: [source_id, ...]}} of non-excluded ledger rows matching the globs."""

    matches = defaultdict(lambda: defaultdict(list))

    with session_factory() as db:
        query = db.query(IndexedFile.user_id, IndexedFile.platform, IndexedFile.source_id, IndexedFile.file_name)
        query = query.filter(IndexedFile.status != "excluded")
        if email:
            query = query.join(User, User.id == IndexedFile.user_id).filter(User.email == email.lower())
        for user_id, platform, source_id, file_name in query.all():
            if is_excluded(file_name):
                matches[str(user_id)][platform].append((source_id, file_name))

    return matches


def purge(dry_run: bool, email=None, show_names=False, session_factory=SessionLocal) -> Counter:

    totals = Counter()

    for user_id, platforms in find_matches(session_factory, email).items():
        for platform, rows in platforms.items():
            totals[platform] += len(rows)
            print(f"user {user_id[:8]}... {platform}: {len(rows)} file(s){' (dry run)' if dry_run else ''}")
            if show_names:
                for _, name in rows:
                    print(f"    {name}")
            if not dry_run:
                index_store.delete_sources(user_id, platform, [source_id for source_id, _ in rows],
                                           session_factory=session_factory)

    print(f"{'would delete' if dry_run else 'deleted'} {sum(totals.values())} file(s): {dict(totals)}")

    return totals


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--email")
    parser.add_argument("--show-names", action="store_true")
    args = parser.parse_args()

    purge(args.dry_run, args.email, args.show_names)
