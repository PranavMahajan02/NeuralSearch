"""Fill the REQUIRED secrets in .env with strong random values.

    python scripts/generate_secrets.py            # creates .env from .env.example if needed
    python scripts/generate_secrets.py --env-file path/to/.env

Only EMPTY (or placeholder) values are filled: an existing secret is never
replaced, because changing e.g. POSTGRES_PASSWORD after the database was
initialised would lock the application out. Values are never printed - only the
names of the keys that were set. Standard library only (works before the
virtualenv exists).
"""

import argparse
import base64
import contextlib
import os
import re
import secrets
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PLACEHOLDERS = {"", "change-me", "replace-with-at-least-32-random-characters", "replace-with-a-fernet-key"}


def fernet_key() -> str:

    return base64.urlsafe_b64encode(os.urandom(32)).decode()


def token(length: int = 32) -> str:
    """URL-safe (no characters that need escaping in a postgresql:// or redis:// URL)."""

    return secrets.token_urlsafe(length)


GENERATORS = {
    "JWT_SECRET_KEY": lambda: token(48),
    "TOKEN_ENCRYPTION_KEY": fernet_key,
    "POSTGRES_PASSWORD": lambda: token(24),
    "POSTGRES_SUPERUSER_PASSWORD": lambda: token(24),
    "QDRANT_API_KEY": lambda: token(32),
    "REDIS_PASSWORD": lambda: token(24),
    "BACKUP_ENCRYPTION_KEY": fernet_key,
}

LINE = re.compile(r"^(?P<key>[A-Z][A-Z0-9_]*)=(?P<value>.*)$")


def fill(text: str) -> tuple[str, list[str]]:

    lines = text.splitlines()
    seen, filled, values = set(), [], {}

    for i, line in enumerate(lines):
        match = LINE.match(line)
        if not match:
            continue
        key, value = match["key"], match["value"].strip()
        seen.add(key)
        values[key] = value
        if key in GENERATORS and value in PLACEHOLDERS:
            values[key] = GENERATORS[key]()
            lines[i] = f"{key}={values[key]}"
            filled.append(key)

    for key in GENERATORS:
        if key not in seen:
            values[key] = GENERATORS[key]()
            lines.append(f"{key}={values[key]}")
            filled.append(key)

    # Keep the development DATABASE_URL in step with a freshly generated password.
    if "POSTGRES_PASSWORD" in filled:
        user = values.get("POSTGRES_USER") or "cogniseek"
        for i, line in enumerate(lines):
            if line.startswith("DATABASE_URL=") and f"{user}:change-me@" in line:
                lines[i] = line.replace(f"{user}:change-me@", f"{user}:{values['POSTGRES_PASSWORD']}@")

    return "\n".join(lines) + "\n", filled


def main(argv=None) -> int:

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--env-file", default=str(ROOT / ".env"))
    args = parser.parse_args(argv)

    env_file = Path(args.env_file)
    if not env_file.exists():
        shutil.copyfile(ROOT / ".env.example", env_file)
        print(f"created {env_file.name} from .env.example")

    text, filled = fill(env_file.read_text(encoding="utf-8"))
    env_file.write_text(text, encoding="utf-8")
    with contextlib.suppress(OSError):
        os.chmod(env_file, 0o600)

    if filled:
        print("generated: " + ", ".join(filled))
    else:
        print("all secrets already set; nothing changed")

    if "BACKUP_ENCRYPTION_KEY" in filled:
        print("IMPORTANT: copy BACKUP_ENCRYPTION_KEY to a password manager - backups cannot be restored without it.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
