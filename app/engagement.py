"""Visitor-facing extras: contact messages and the visit counter.

Both features are deliberately private and cookie-free:

* **Messages** are write-only for the public. `POST /api/messages` stores a
  note and answers with nothing but ``{"ok": true}``; the studio is the only
  place where messages can be read, edited or deleted. One visitor can never
  see another visitor's message.
* **Visits** store no IP address, user agent, screen size or any other device
  detail. A visitor is remembered only as a one-way digest keyed with the
  private CAPTCHA secret, purely so the same person refreshing a page is not
  counted twice within ``VISIT_WINDOW``. The digests expire and are deleted.

The counter is per URL path, and the number shown on the public pages is the
site total plus an offset the studio can set, so the displayed total can be
started at any value and still grows by one for every new visit.
"""
from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from .db import get_db, utcnow
from .security import check_limit, record_attempt
from .store import AppError

# ── Messages ──────────────────────────────────────────────────────────────
NAME_MAX = 60
BODY_MIN = 2
BODY_MAX = 4000
MESSAGE_MAX = 5
MESSAGE_WINDOW = timedelta(minutes=10)
MESSAGE_LOCK = timedelta(minutes=10)
MESSAGE_GLOBAL_MAX = 200
MESSAGE_GLOBAL_WINDOW = timedelta(hours=1)
MESSAGE_GLOBAL_LOCK = timedelta(hours=1)
MESSAGE_LIMIT = 500

# ── Visits ────────────────────────────────────────────────────────────────
VISIT_WINDOW = timedelta(hours=12)
VISIT_MAX = 1_000_000_000
OFFSET_KEY = "visit_offset"

# Crawlers, previews and command-line clients are not people; counting them
# would make the number meaningless.
_BOT_RE = re.compile(
    r"bot\b|bot/|robot|crawler|crawl|spider|slurp|scrape|monitor|uptime|preview|"
    r"facebookexternalhit|embedly|headless|phantomjs|lighthouse|pingdom|"
    r"curl/|wget|python-urllib|python-requests|libwww|okhttp|java/|go-http|axios",
    re.IGNORECASE,
)
_CONTROL_RE = re.compile(r"[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]")


def _clean_text(value: str) -> str:
    return _CONTROL_RE.sub("", value.replace("\r\n", "\n").replace("\r", "\n"))


# ── visitor identity (never stored in readable form) ─────────────────────
def visitor_key(headers: dict[str, str], client_ip: str | None) -> str:
    """One-way digest of the network address for de-duplication only.

    Proxy headers are used when present because they are what identifies a
    visitor behind the hosting panel's proxy. They are trusted for *counting*
    only — never for authentication or rate limiting of sign-in, which keep
    using the stricter `security.ip_key`.
    """
    forwarded = (headers.get("x-forwarded-for") or "").split(",")[0].strip()
    ip = forwarded or (headers.get("x-real-ip") or "").strip() or (client_ip or "")
    agent = (headers.get("user-agent") or "")[:200]
    secret = os.environ.get("CAPTCHA_SECRET") or "hana-visits"
    return hashlib.sha256(f"{secret}|{ip}|{agent}".encode("utf-8")).hexdigest()


def is_countable(headers: dict[str, str]) -> bool:
    agent = (headers.get("user-agent") or "").strip()
    if not agent or _BOT_RE.search(agent):
        return False
    purpose = f"{headers.get('sec-purpose', '')} {headers.get('purpose', '')}".lower()
    return "prefetch" not in purpose and "prerender" not in purpose


# ── settings ─────────────────────────────────────────────────────────────
def get_setting(conn, key: str, default: str = "") -> str:
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(conn, key: str, value: Any) -> None:
    with conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, str(value)),
        )


def _offset(conn) -> int:
    try:
        return int(get_setting(conn, OFFSET_KEY, "0") or 0)
    except ValueError:
        return 0


def _real_total(conn) -> int:
    row = conn.execute("SELECT COALESCE(SUM(visits), 0) AS total FROM visit_counts").fetchone()
    return int(row["total"] or 0)


# ── visits ───────────────────────────────────────────────────────────────
def record_visit(db_path, path: str, headers: dict[str, str], client_ip: str | None) -> bool:
    """Count one visit to `path`. Returns True when the counter moved.

    The same visitor reloading the same page inside VISIT_WINDOW is ignored,
    while the same visitor opening a different page is counted again.
    """
    if not is_countable(headers):
        return False
    conn = get_db(db_path)
    visitor = visitor_key(headers, client_ip)
    cutoff = (datetime.now(timezone.utc) - VISIT_WINDOW).strftime("%Y-%m-%d %H:%M:%S.%f")
    row = conn.execute(
        "SELECT seen_at FROM visit_seen WHERE visitor = ? AND path = ?", (visitor, path)
    ).fetchone()
    if row and row["seen_at"] > cutoff:
        return False
    stamp = utcnow()
    with conn:
        conn.execute(
            "INSERT INTO visit_seen (visitor, path, seen_at) VALUES (?, ?, ?) "
            "ON CONFLICT(visitor, path) DO UPDATE SET seen_at = excluded.seen_at",
            (visitor, path, stamp),
        )
        conn.execute(
            "INSERT INTO visit_counts (path, visits, last_at) VALUES (?, 1, ?) "
            "ON CONFLICT(path) DO UPDATE SET visits = visits + 1, last_at = excluded.last_at",
            (path, stamp),
        )
        conn.execute("DELETE FROM visit_seen WHERE seen_at < ?", (cutoff,))
    return True


def visit_total(db_path) -> int:
    """The number shown on the public pages: real visits + the studio offset."""
    conn = get_db(db_path)
    return max(0, _real_total(conn) + _offset(conn))


def visit_stats(db_path, pages: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    conn = get_db(db_path)
    titles: dict[str, str] = {}
    for page in pages or []:
        slug = page.get("slug") or ""
        titles[f"/{slug}" if slug else "/"] = page.get("title", "")
    rows = conn.execute(
        "SELECT path, visits, last_at FROM visit_counts ORDER BY visits DESC, path ASC LIMIT 200"
    ).fetchall()
    real_total = _real_total(conn)
    offset = _offset(conn)
    return {
        "realTotal": real_total,
        "offset": offset,
        "displayedTotal": max(0, real_total + offset),
        "pages": [
            {
                "path": row["path"],
                "title": titles.get(row["path"], ""),
                "visits": int(row["visits"] or 0),
                "lastAt": row["last_at"],
            }
            for row in rows
        ],
    }


def set_displayed_total(db_path, value: Any, pages: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= VISIT_MAX:
        raise AppError(f"Choose a number between 0 and {VISIT_MAX}.")
    conn = get_db(db_path)
    set_setting(conn, OFFSET_KEY, value - _real_total(conn))
    return visit_stats(db_path, pages)


# ── messages ─────────────────────────────────────────────────────────────
def _rate_limit(conn, visitor: str) -> None:
    key = f"msg:{visitor[:32]}"
    if check_limit(conn, key) or check_limit(conn, "msg:global"):
        raise AppError("Too many messages just now. Please try again later.", 429)
    if record_attempt(conn, key, MESSAGE_MAX, MESSAGE_WINDOW, MESSAGE_LOCK):
        raise AppError("Too many messages just now. Please try again later.", 429)
    if record_attempt(conn, "msg:global", MESSAGE_GLOBAL_MAX, MESSAGE_GLOBAL_WINDOW, MESSAGE_GLOBAL_LOCK):
        raise AppError("Too many messages just now. Please try again later.", 429)


def add_message(db_path, name: Any, body: Any, headers: dict[str, str], client_ip: str | None) -> dict[str, Any]:
    if name is None:
        name = ""
    if not isinstance(name, str) or not isinstance(body, str):
        raise AppError(f"Please write at least {BODY_MIN} characters.")
    if len(name) > 400 or len(body) > BODY_MAX * 2:
        raise AppError("That message is too long.", 413)
    clean_name = re.sub(r"\s+", " ", _clean_text(name)).strip()[:NAME_MAX]
    clean_body = _clean_text(body).strip()
    if len(clean_body) < BODY_MIN:
        raise AppError(f"Please write at least {BODY_MIN} characters.")
    if len(clean_body) > BODY_MAX:
        raise AppError(f"Please keep it under {BODY_MAX} characters.")
    conn = get_db(db_path)
    _rate_limit(conn, visitor_key(headers, client_ip))
    now = utcnow()
    with conn:
        conn.execute(
            "INSERT INTO messages (name, body, created_at, read_at) VALUES (?, ?, ?, NULL)",
            (clean_name, clean_body, now),
        )
    return {"ok": True}


def list_messages(db_path) -> list[dict[str, Any]]:
    conn = get_db(db_path)
    rows = conn.execute(
        "SELECT id, name, body, created_at, read_at FROM messages ORDER BY id DESC LIMIT ?",
        (MESSAGE_LIMIT,),
    ).fetchall()
    return [
        {
            "id": row["id"],
            "name": row["name"] or "",
            "body": row["body"],
            "createdAt": row["created_at"],
            "read": bool(row["read_at"]),
        }
        for row in rows
    ]


def unread_count(db_path) -> int:
    conn = get_db(db_path)
    row = conn.execute("SELECT COUNT(*) AS total FROM messages WHERE read_at IS NULL").fetchone()
    return int(row["total"] or 0)


def set_message_read(db_path, message_id: int, read: bool) -> None:
    conn = get_db(db_path)
    with conn:
        cursor = conn.execute(
            "UPDATE messages SET read_at = ? WHERE id = ?",
            (utcnow() if read else None, message_id),
        )
    if cursor.rowcount == 0:
        raise AppError("That message no longer exists.", 404)


def delete_message(db_path, message_id: int) -> None:
    conn = get_db(db_path)
    with conn:
        cursor = conn.execute("DELETE FROM messages WHERE id = ?", (message_id,))
    if cursor.rowcount == 0:
        raise AppError("That message no longer exists.", 404)
