"""SQLite persistence layer (file database, zero external setup).

Mirrors the previous relational schema: site_state, site_versions,
media_assets, captcha_challenges, auth_attempts, admin_sessions.
Timestamps are stored as UTC "YYYY-MM-DD HH:MM:SS.ffffff" strings so
lexicographic comparison matches chronological order.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

local = threading.local()
_init_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS site_state (
  id INTEGER PRIMARY KEY,
  revision INTEGER NOT NULL DEFAULT 0,
  draft_pages TEXT NOT NULL,
  published_pages TEXT NOT NULL,
  draft_theme TEXT NOT NULL,
  published_theme TEXT NOT NULL,
  published_at TEXT,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS site_versions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  pages TEXT NOT NULL,
  theme TEXT NOT NULL,
  published_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS media_assets (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  mime TEXT NOT NULL,
  kind TEXT NOT NULL,
  bytes INTEGER NOT NULL,
  data BLOB NOT NULL,
  created_at TEXT NOT NULL,
  deleted_at TEXT,
  width INTEGER,
  height INTEGER
);
CREATE TABLE IF NOT EXISTS captcha_challenges (
  id TEXT PRIMARY KEY,
  digest TEXT NOT NULL,
  ip_key TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  used INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS auth_attempts (
  key TEXT PRIMARY KEY,
  failures INTEGER NOT NULL DEFAULT 0,
  window_start TEXT NOT NULL,
  locked_until TEXT
);
CREATE TABLE IF NOT EXISTS admin_sessions (
  token_hash TEXT PRIMARY KEY,
  expires_at TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL DEFAULT '',
  body TEXT NOT NULL,
  created_at TEXT NOT NULL,
  read_at TEXT
);
CREATE TABLE IF NOT EXISTS visit_counts (
  path TEXT PRIMARY KEY,
  visits INTEGER NOT NULL DEFAULT 0,
  last_at TEXT
);
CREATE TABLE IF NOT EXISTS visit_seen (
  visitor TEXT NOT NULL,
  path TEXT NOT NULL,
  seen_at TEXT NOT NULL,
  PRIMARY KEY (visitor, path)
);
CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_media_deleted ON media_assets(deleted_at);
CREATE INDEX IF NOT EXISTS idx_versions_id ON site_versions(id DESC);
CREATE INDEX IF NOT EXISTS idx_messages_id ON messages(id DESC);
CREATE INDEX IF NOT EXISTS idx_messages_unread ON messages(read_at);
CREATE INDEX IF NOT EXISTS idx_visit_seen_at ON visit_seen(seen_at);
"""


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=timezone.utc)


def dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def loads(value: str, default: Any) -> Any:
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def _file_id(path: str):
    try:
        st = os.stat(path)
        return (st.st_dev, st.st_ino)
    except OSError:
        return None


def _open_configured(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    # Autocommit mode: bare statements commit immediately, so a request
    # thread can never leak an open transaction that would block other
    # writers on the WAL. Explicit transactions use `with conn:`.
    conn.isolation_level = None
    conn.execute("PRAGMA journal_mode=WAL").fetchone()
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def get_db(database_path: Path) -> sqlite3.Connection:
    """One connection per thread (SQLite connections are not thread-safe).

    Self-healing: the schema is applied on every new connection (it is
    idempotent), and if the database file disappears or is replaced while
    the server runs — fresh deploys, panel restarts, storage resets — the
    stale connection is dropped and a valid database is recreated.
    """
    path = str(database_path)
    fid = _file_id(path)
    conn = getattr(local, "conn", None)
    if (conn is not None and fid is not None
            and getattr(local, "path", None) == path
            and getattr(local, "fid", None) == fid):
        return conn
    if conn is not None:
        try:
            conn.close()
        except sqlite3.Error:
            pass
    database_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        conn = _open_configured(path)
        with _init_lock:
            conn.executescript(SCHEMA)
            migrate(conn)
    except sqlite3.DatabaseError:
        # The existing file is not a usable SQLite database (for example a
        # partial upload). It cannot hold real data, so rebuild it.
        try:
            conn.close()
        except Exception:
            pass
        try:
            database_path.unlink(missing_ok=True)
        except OSError:
            pass
        conn = _open_configured(path)
        with _init_lock:
            conn.executescript(SCHEMA)
            migrate(conn)
    local.conn = conn
    local.path = path
    local.fid = _file_id(path)
    return conn


def migrate(conn: sqlite3.Connection) -> None:
    """Additive migrations for databases made by an older build.

    CREATE TABLE IF NOT EXISTS cannot add a column to a table that already
    exists, so the few columns added after the first release are checked
    here. Existing rows keep their data; only the new columns are filled.
    """
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(media_assets)")}
    added = False
    for column in ("width", "height"):
        if column not in columns:
            conn.execute(f"ALTER TABLE media_assets ADD COLUMN {column} INTEGER")
            added = True
    if not added:
        return
    from .media import image_size  # imported late: media imports db helpers
    rows = conn.execute("SELECT id, mime, data FROM media_assets WHERE kind = 'image'").fetchall()
    for row in rows:
        size = image_size(bytes(row["data"]), row["mime"])
        if size:
            conn.execute("UPDATE media_assets SET width = ?, height = ? WHERE id = ?", (size[0], size[1], row["id"]))
    if rows:
        print(f"Database: measured {len(rows)} existing image(s)", flush=True)


def row_json(row: sqlite3.Row | None, fields: tuple[str, ...]):
    """Decode JSON columns on a row (None-safe)."""
    if row is None:
        return None
    data = dict(row)
    for field in fields:
        if data.get(field) is not None:
            data[field] = loads(data[field], {})
    return data
