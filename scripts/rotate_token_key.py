"""Rotate TOKEN_ENCRYPTION_KEY: re-encrypt every stored OAuth token with a new key.

    # 1. generate a new key (prints it ONCE; put it in your password manager)
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    # 2. stop the backend, then (DATABASE_URL from .env; keys from the environment):
    set OLD_TOKEN_ENCRYPTION_KEY=<current key>    (PowerShell: $env:OLD_TOKEN_ENCRYPTION_KEY=...)
    set NEW_TOKEN_ENCRYPTION_KEY=<new key>
    python scripts/rotate_token_key.py --dry-run
    python scripts/rotate_token_key.py
    # 3. put the new key in .env as TOKEN_ENCRYPTION_KEY, start the backend

Re-encrypts platform_connections.access_token, refresh_token and token_json in ONE
transaction: every value is decrypted with the old key, encrypted with the new one,
and verified to decrypt again before the commit. A value that the old key cannot
decrypt aborts the whole rotation (nothing is written). Keys are never printed.
"""

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

COLUMNS = ("access_token", "refresh_token", "token_json")


def rotate(engine, old_key: str, new_key: str, dry_run: bool = False) -> dict:
    from cryptography.fernet import Fernet, InvalidToken
    from sqlalchemy import text

    old, new = Fernet(old_key.encode()), Fernet(new_key.encode())
    counts = {"rows": 0, "values": 0}

    with engine.begin() as conn:
        rows = conn.execute(text(f"SELECT id, {', '.join(COLUMNS)} FROM platform_connections FOR UPDATE")).all()
        for row in rows:
            updates = {}
            for column in COLUMNS:
                value = getattr(row, column)
                if value is None:
                    continue
                try:
                    plain = old.decrypt(value.encode("ascii"))
                except (InvalidToken, ValueError) as error:
                    raise SystemExit(
                        f"row {row.id}: {column} does not decrypt with the OLD key; nothing was changed"
                    ) from error
                rotated = new.encrypt(plain).decode("ascii")
                assert new.decrypt(rotated.encode("ascii")) == plain
                updates[column] = rotated
            if updates:
                counts["rows"] += 1
                counts["values"] += len(updates)
                if not dry_run:
                    assignments = ", ".join(f"{column} = :{column}" for column in updates)
                    conn.execute(
                        text(f"UPDATE platform_connections SET {assignments} WHERE id = :id"), {**updates, "id": row.id}
                    )
        if dry_run:
            conn.rollback()

    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="decrypt and re-encrypt in memory; write nothing")
    args = parser.parse_args()

    old_key, new_key = os.environ.get("OLD_TOKEN_ENCRYPTION_KEY"), os.environ.get("NEW_TOKEN_ENCRYPTION_KEY")
    if not old_key or not new_key:
        raise SystemExit("Set OLD_TOKEN_ENCRYPTION_KEY and NEW_TOKEN_ENCRYPTION_KEY in the environment.")
    if old_key == new_key:
        raise SystemExit("The new key must differ from the old one.")

    from app.database.db import engine

    counts = rotate(engine, old_key, new_key, dry_run=args.dry_run)
    verb = "would re-encrypt" if args.dry_run else "re-encrypted"
    print(f"{verb} {counts['values']} values in {counts['rows']} connections")
    if not args.dry_run:
        print("Now set TOKEN_ENCRYPTION_KEY in .env to the NEW key and restart the backend.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
