"""Environment configuration.

Everything the server needs comes from the process environment, loaded from a
`.env` file in the project root when present (WispByte also allows setting the
same variables in the server panel — the panel wins over `.env` values).

`config.json` in the project root is the lowest-precedence layer: it holds the
values you normally don't touch from a panel (domain, bind host/port, site
name and description). Precedence: WispByte environment > .env > config.json >
built-in defaults.

Required:
    CAPTCHA_SECRET                 random private value (no fallback)
    ADMIN_PASSWORD_HASH_1/_2/_3    PBKDF2 hashes (see scripts/make_password_hash.py)

Optional:
    PORT            TCP port to listen on          (default 8000)
    HOST            interface to bind              (default 0.0.0.0)
    SITE_URL        public origin, e.g. https://hanainfo.wisp.uno
    DATABASE_PATH   SQLite file location           (default data/portfolio.db)
    TRUST_PROXY     "true" only behind a trusted proxy (default false)
    COOKIE_SECURE   force the session cookie's Secure flag: "true"/"false"
                    (default: auto — Secure only when the request is HTTPS)
"""
from __future__ import annotations

import json
import os
import re
import secrets
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_ENV_LINE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)?\s*$")


def load_dotenv(path: Path = ROOT / ".env") -> None:
    """Minimal .env loader: KEY=VALUE lines, # comments, optional quotes.

    Never overrides variables already present in the environment, so values
    set by the WispByte panel always win.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return
    for line in raw.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = _ENV_LINE.match(line)
        if not match:
            continue
        key, value = match.group(1), match.group(2) or ""
        value = value.strip()
        if value and value[0] in "\"'" and value.endswith(value[0]) and len(value) >= 2:
            value = value[1:-1]
        # Strip trailing inline comments on unquoted values.
        if not (value and value[0] in "\"'"):
            value = value.split(" #", 1)[0].rstrip()
        os.environ.setdefault(key, value)


def load_config_json(path: Path) -> dict:
    """Read config.json (domain, host, port, site_name, site_description)."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError:
        return {}
    except json.JSONDecodeError as exc:
        sys.exit(f"Invalid config.json: {exc}")
    return data if isinstance(data, dict) else {}


def _config_values(root: Path) -> None:
    """Feed config.json values into the environment (lowest precedence)."""
    site = load_config_json(root / "config.json")
    for cfg_key, env_key in (
        ("host", "HOST"), ("port", "PORT"),
        ("site_name", "SITE_NAME"), ("site_description", "SITE_DESCRIPTION"),
    ):
        value = site.get(cfg_key)
        if value is not None and str(value).strip():
            os.environ.setdefault(env_key, str(value).strip())
    domain = site.get("domain")
    if domain and str(domain).strip() and not (os.environ.get("SITE_URL") or "").strip():
        raw = str(domain).strip().strip("/")
        for scheme in ("https://", "http://"):
            if raw.startswith(scheme):
                raw = raw[len(scheme):]
                break
        os.environ.setdefault("SITE_URL", "https://" + raw)


def _require_int(name: str, default: int, minimum: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw.strip())
    except ValueError:
        sys.exit(f"Invalid {name}: {raw!r} is not an integer.")
    if value < minimum:
        sys.exit(f"Invalid {name}: must be >= {minimum}.")
    return value


def _origin(raw: str) -> str:
    return raw.rstrip("/").split("://", 1)[-1].split("/", 1)[0]


@dataclass(frozen=True)
class Config:
    port: int
    host: str
    site_url: str
    database_path: Path
    trust_proxy: bool
    cookie_secure: str  # "auto" | "on" | "off"
    root: Path
    site_name: str
    site_description: str


def ensure_captcha_secret(database_path: Path) -> None:
    """Guarantee a CAPTCHA_SECRET exists.

    An environment value always wins. Otherwise a random secret is generated
    once and kept next to the database (data/ is gitignored) — so a fresh
    deployment works without configuring the secret at all.
    """
    if (os.environ.get("CAPTCHA_SECRET") or "").strip():
        return
    secret_file = database_path.parent / "captcha_secret"
    secret = ""
    try:
        secret = secret_file.read_text(encoding="utf-8").strip()
    except OSError:
        secret = ""
    if not secret:
        secret = secrets.token_urlsafe(48)
        try:
            secret_file.parent.mkdir(parents=True, exist_ok=True)
            secret_file.write_text(secret, encoding="utf-8")
            print(f"CAPTCHA_SECRET not set: generated one and stored it at {secret_file}.", flush=True)
        except OSError:
            print("CAPTCHA_SECRET not set: using a random in-memory secret (challenges reset on restart).", flush=True)
    os.environ["CAPTCHA_SECRET"] = secret


def load_config(root: Path = ROOT) -> Config:
    load_dotenv(root / ".env")
    _config_values(root)
    port = _require_int("PORT", 8000, 1)
    host = (os.environ.get("HOST") or "0.0.0.0").strip() or "0.0.0.0"
    site_url = (os.environ.get("SITE_URL") or "https://hanainfo.wisp.uno").strip()
    if not site_url:
        sys.exit("Invalid SITE_URL: must not be empty.")
    if "://" not in site_url:
        site_url = "https://" + site_url
    site_url = site_url.rstrip("/")
    if _origin(site_url) != _origin(os.environ.get("SITE_URL", site_url)) and not site_url.startswith(("http://", "https://")):
        sys.exit(f"Invalid SITE_URL: {site_url!r}")
    database_path = (root / ((os.environ.get("DATABASE_PATH") or "data/portfolio.db").strip())).resolve()
    ensure_captcha_secret(database_path)
    trust_proxy = (os.environ.get("TRUST_PROXY") or "").strip().lower() == "true"
    site_name = (os.environ.get("SITE_NAME") or "").strip() or "Hana Hamamato"
    site_description = (os.environ.get("SITE_DESCRIPTION") or "").strip()
    raw_secure = (os.environ.get("COOKIE_SECURE") or "").strip().lower()
    if raw_secure in ("true", "1", "yes"):
        cookie_secure = "on"
    elif raw_secure in ("false", "0", "no"):
        cookie_secure = "off"
    else:
        # Default: match the actual connection — a Secure cookie sent over
        # plain http is rejected by browsers, which silently breaks sign-in.
        cookie_secure = "auto"
    return Config(
        port=port,
        host=host,
        site_url=site_url,
        database_path=database_path,
        trust_proxy=trust_proxy,
        cookie_secure=cookie_secure,
        root=root,
        site_name=site_name,
        site_description=site_description,
    )
