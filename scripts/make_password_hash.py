#!/usr/bin/env python3
"""Generate a PBKDF2-HMAC-SHA256 hash for one of the admin passwords.

Usage:

    python scripts/make_password_hash.py "your password"
    python scripts/make_password_hash.py          # prompts, hidden input

Copy each of the three resulting values into ADMIN_PASSWORD_HASH_1,
ADMIN_PASSWORD_HASH_2, and ADMIN_PASSWORD_HASH_3 in your .env. The three
passwords must be different and each hash is generated with its own random
salt. Plain passwords never live in the repository.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.security import generate_password_hash  # noqa: E402


def main() -> None:
    if len(sys.argv) > 1:
        password = sys.argv[1]
    else:
        try:
            import getpass
            password = getpass.getpass("Password (input hidden): ")
        except ImportError:  # pragma: no cover
            password = input("Password: ")
    if not password:
        print("The password must not be empty.", file=sys.stderr)
        raise SystemExit(1)
    print(generate_password_hash(password))


if __name__ == "__main__":
    main()
