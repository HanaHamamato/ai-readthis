#!/usr/bin/env python3
"""Hana's portfolio studio — entry point.

Start the whole site (public portfolio, private studio, and all APIs) with:

    python main.py

Configuration comes from a `.env` file in this directory (see .env.example)
and/or the process environment. At minimum the server needs:

    PORT            TCP port to listen on          (default 8000)
    SITE_URL        public origin (e.g. https://hanainfo.wisp.uno)
    CAPTCHA_SECRET  a random private value
    ADMIN_PASSWORD_HASH_1 / _2 / _3
                    PBKDF2 hashes — python scripts/make_password_hash.py

Only the Python standard library is required. Optionally, add the ``Pillow``
package to enable automatic image optimization (uploads are stored as-is
without it).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.config import load_config  # noqa: E402
from app.server import serve  # noqa: E402


def main() -> None:
    config = load_config()
    serve(config)


if __name__ == "__main__":
    main()
