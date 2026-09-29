"""Authentication, sessions, CAPTCHA challenges, lockouts, and origin checks.

Same security behavior as the original server:
- three independent password hashes from the private environment, fail closed
- one-use, short-lived HMAC-keyed CAPTCHA digests
- per-network login lockout (7 failures / 15 min window -> 20 min lock)
  plus a global ceiling, and challenge rate limits
- opaque random server-side sessions stored hashed
- same-origin checks for every mutating request

Password hashes use PBKDF2-HMAC-SHA256 (standard library only, no native
modules to install). Generate them with:  python scripts/make_password_hash.py
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from typing import Any

from . import captcha
from .db import get_db, parse_dt, utcnow
from .validation import ValidationError

SESSION_COOKIE = "hana_admin_session"
SESSION_HOURS = 12
LOGIN_MAX_FAILURES = 7
LOGIN_WINDOW = timedelta(minutes=15)
LOGIN_LOCK = timedelta(minutes=20)
CAPTCHA_MAX = 45
CAPTCHA_WINDOW = timedelta(minutes=10)
CAPTCHA_LOCK = timedelta(minutes=5)
GLOBAL_MAX = 250
GLOBAL_WINDOW = timedelta(minutes=10)
GLOBAL_LOCK = timedelta(minutes=10)
PBKDF2_ITERATIONS = 600_000


class AuthError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def generate_password_hash(password: str) -> str:
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return (
        f"pbkdf2_sha256${PBKDF2_ITERATIONS}$"
        f"{base64.b64encode(salt).decode()}${base64.b64encode(key).decode()}"
    )


def verify_password_hash(stored: str, password: str) -> bool:
    try:
        algorithm, iterations_raw, salt_b64, key_b64 = stored.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_raw)
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(key_b64)
    except (ValueError, TypeError):
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(expected, actual)


def password_hashes() -> list[str]:
    """All three admin password hashes, or fail closed if any is missing."""
    overrides = [
        os.environ.get("ADMIN_PASSWORD_HASH_1"),
        os.environ.get("ADMIN_PASSWORD_HASH_2"),
        os.environ.get("ADMIN_PASSWORD_HASH_3"),
    ]
    if not all(overrides):
        print("Admin sign-in is disabled: set ADMIN_PASSWORD_HASH_1, ADMIN_PASSWORD_HASH_2, "
              "and ADMIN_PASSWORD_HASH_3 in the server environment.", flush=True)
        raise AuthError("Admin sign-in is not configured.", 503)
    return overrides  # type: ignore[return-value]


def answer_digest(challenge_id: str, answer: str) -> str:
    key = os.environ.get("CAPTCHA_SECRET")
    if not key:
        print("Admin sign-in is disabled: set CAPTCHA_SECRET in the server environment.", flush=True)
        raise AuthError("CAPTCHA is not configured.", 503)
    return hmac.new(key.encode("utf-8"), f"{challenge_id}:{answer.strip()}".encode("utf-8"), hashlib.sha256).hexdigest()


def ip_key(headers: dict[str, str], trust_proxy: bool, client_ip: str | None = None) -> str:
    """Identify the caller for lockouts, without ever trusting spoofable input.

    Proxy headers are only read when the deployment guarantees its proxy
    overwrites client-supplied copies (TRUST_PROXY=true) — otherwise an
    attacker could rotate the header to escape every lockout. Without a
    trusted proxy the socket peer address is used: it cannot be forged, and
    it at least separates direct callers instead of putting the whole
    internet in one shared bucket.
    """
    ip = None
    if trust_proxy:
        ip = headers.get("x-real-ip") or (headers.get("x-forwarded-for") or "").split(",")[-1].strip()
    return digest(ip or (client_ip or "").strip() or "untrusted-network")


def check_limit(conn, key: str) -> bool:
    row = conn.execute("SELECT locked_until FROM auth_attempts WHERE key = ?", (key,)).fetchone()
    if not row or not row["locked_until"]:
        return False
    locked = parse_dt(row["locked_until"])
    return bool(locked and locked > datetime.now(timezone.utc))


def record_attempt(conn, key: str, maximum: int, window: timedelta, lock: timedelta) -> bool:
    now = datetime.now(timezone.utc)
    with conn:
        conn.execute(
            "INSERT OR IGNORE INTO auth_attempts (key, failures, window_start, locked_until) VALUES (?, 0, ?, NULL)",
            (key, utcnow()),
        )
        row = conn.execute("SELECT * FROM auth_attempts WHERE key = ?", (key,)).fetchone()
    entry_window_start = parse_dt(row["window_start"])
    reset = (now - entry_window_start) > window
    failures = (0 if reset else row["failures"]) + 1
    locked_until = None
    if failures >= maximum:
        locked_until = now + lock
    elif not reset:
        locked_until = parse_dt(row["locked_until"])
    with conn:
        conn.execute(
            "UPDATE auth_attempts SET failures = ?, window_start = ?, locked_until = ? WHERE key = ?",
            (failures, utcnow() if reset else row["window_start"], utcnow_from_dt(locked_until), key),
        )
    return bool(locked_until and locked_until > now)


def utcnow_from_dt(value: datetime | None) -> str | None:
    return value.strftime("%Y-%m-%d %H:%M:%S.%f") if value else None


def create_challenge(headers: dict[str, str], trust_proxy: bool, db_path, client_ip: str | None = None) -> dict[str, str]:
    conn = get_db(db_path)
    key = ip_key(headers, trust_proxy, client_ip)
    if check_limit(conn, f"captcha:{key}") or check_limit(conn, f"login:{key}") or check_limit(conn, "login:global"):
        raise AuthError("Too many attempts. Please try again later.", 429)
    if record_attempt(conn, f"captcha:{key}", CAPTCHA_MAX, CAPTCHA_WINDOW, CAPTCHA_LOCK):
        raise AuthError("Too many challenges. Please try again shortly.", 429)
    generated = captcha.generate()
    challenge_id = str(uuid.uuid4())
    answer_digest_value = answer_digest(challenge_id, generated["answer"])
    with conn:
        conn.execute("DELETE FROM captcha_challenges WHERE expires_at < ?", (utcnow(),))
        conn.execute(
            "INSERT INTO captcha_challenges (id, digest, ip_key, expires_at, used) VALUES (?, ?, ?, ?, 0)",
            (challenge_id, answer_digest_value, key,
             utcnow_from_dt(datetime.now(timezone.utc) + timedelta(minutes=5))),
        )
    return {
        "id": challenge_id,
        "image": "data:image/svg+xml;base64," + base64.b64encode(generated["svg"].encode("utf-8")).decode("ascii"),
    }


def consume_challenge(headers: dict[str, str], trust_proxy: bool, db_path, challenge_id: str, answer: str,
                      client_ip: str | None = None) -> bool:
    conn = get_db(db_path)
    key = ip_key(headers, trust_proxy, client_ip)
    row = conn.execute(
        """UPDATE captcha_challenges SET used = 1
           WHERE id = ? AND ip_key = ? AND used = 0 AND expires_at > ?
           RETURNING digest""",
        (challenge_id, key, utcnow()),
    ).fetchone()
    if not row:
        return False
    expected = bytes.fromhex(row["digest"])
    received = bytes.fromhex(answer_digest(challenge_id, answer))
    return len(expected) == len(received) and hmac.compare_digest(expected, received)


def attempt_login(headers: dict[str, str], db_path, trust_proxy: bool, passwords: list[str], challenge_id: str,
                  answer: str, client_ip: str | None = None) -> str:
    if not isinstance(passwords, list) or len(passwords) != 3 or not all(isinstance(p, str) for p in passwords):
        raise AuthError("The passwords or challenge didn't match. Please try again.", 401)
    conn = get_db(db_path)
    key = f"login:{ip_key(headers, trust_proxy, client_ip)}"
    if check_limit(conn, key) or check_limit(conn, "login:global"):
        raise AuthError("Too many attempts. Please try again in 20 minutes.", 429)
    challenge_valid = consume_challenge(headers, trust_proxy, db_path, challenge_id, answer, client_ip)
    # Verify every field independently even if an earlier one fails. Never reveal which field failed.
    hashes = password_hashes()
    checks = [verify_password_hash(h, passwords[i] or " ") for i, h in enumerate(hashes)]
    if not challenge_valid or any(not p for p in passwords) or not all(checks):
        locked = record_attempt(conn, key, LOGIN_MAX_FAILURES, LOGIN_WINDOW, LOGIN_LOCK)
        record_attempt(conn, "login:global", GLOBAL_MAX, GLOBAL_WINDOW, GLOBAL_LOCK)
        raise AuthError(
            "Too many attempts. Please try again in 20 minutes." if locked
            else "The passwords or challenge didn't match. Please try again.",
            429 if locked else 401,
        )
    token = secrets.token_urlsafe(32)
    with conn:
        conn.execute("DELETE FROM auth_attempts WHERE key = ?", (key,))
        conn.execute("DELETE FROM admin_sessions WHERE expires_at < ?", (utcnow(),))
        conn.execute(
            "INSERT INTO admin_sessions (token_hash, expires_at, created_at) VALUES (?, ?, ?)",
            (digest(token), utcnow_from_dt(datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS)), utcnow()),
        )
    return token


def has_session(conn, token: str | None) -> bool:
    if not token or not _is_token(token):
        return False
    row = conn.execute(
        "SELECT expires_at FROM admin_sessions WHERE token_hash = ?", (digest(token),)
    ).fetchone()
    if not row:
        return False
    expires = parse_dt(row["expires_at"])
    return bool(expires and expires > datetime.now(timezone.utc))


def _is_token(token: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9_-]{40,60}", token))


def remove_session(conn, token: str | None) -> None:
    if token:
        conn.execute("DELETE FROM admin_sessions WHERE token_hash = ?", (digest(token),))


def check_origin(headers: dict[str, str], site_url: str) -> None:
    """Same-origin check for every mutating request.

    Accepted when the browser Origin matches the public SITE_URL origin, or
    when it matches the origin this very request arrived on (Host /
    X-Forwarded-Host) — so the studio works no matter which domain, subdomain
    or preview URL the deployment is served from. Requests without an Origin
    header (non-browser clients) are accepted: browsers always send Origin on
    POST/PUT/PATCH/DELETE, so a genuine cross-site request is still rejected
    with 403.
    """
    origin = headers.get("origin")
    if not origin:
        return
    try:
        parsed = urlparse(origin)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError
    except Exception:
        raise AuthError("This request could not be verified. Refresh the page and try again.", 403)
    origin_host = parsed.netloc.lower()
    candidates = set()
    for name in ("host", "x-forwarded-host"):
        value = headers.get(name)
        if value:
            candidates.add(value.strip().lower())
    if site_url:
        parsed_site = urlparse(site_url)
        if parsed_site.netloc:
            candidates.add(parsed_site.netloc.lower())
    if origin_host not in candidates:
        raise AuthError("This request could not be verified. Refresh the page and try again.", 403)


def read_json_body(body: bytes, max_bytes: int) -> Any:
    if len(body) > max_bytes:
        raise AuthError("The request is too large.", 413)
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise AuthError("Please send valid JSON.") from None
