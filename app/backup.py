"""Automatic local backups of the whole site.

The database *is* the site: pages, theme, every upload, the history and the
messages all live in one SQLite file. This module keeps a rolling set of
snapshots next to it so a bad edit, a failed upload or a panel accident is
never the end of the story.

    data/backups/portfolio-20260926-1830.zip
      ├── portfolio.db   consistent snapshot (SQLite online backup API)
      ├── site.json      readable copy of the pages and theme
      └── README.txt     how to put it back

Defaults: a snapshot every 12 hours, deleted after 21 days. A snapshot is
skipped when nothing changed since the last one, and the folder is also
capped by total size, so the backups stay small even with a heavy library.

Overridable with BACKUP_EVERY_HOURS, BACKUP_KEEP_DAYS, BACKUP_MAX_MB
(set BACKUP_EVERY_HOURS=0 to switch automatic backups off).
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
import traceback
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

FOLDER = "backups"
PREFIX = "portfolio-"
RESTORE_NOTE = """How to restore this backup

1. Stop the site.
2. Unzip this file.
3. Copy portfolio.db over data/portfolio.db (keep a copy of the current one
   first, and delete any data/portfolio.db-wal and -shm files next to it).
4. Start the site again.

site.json is a readable copy of the same pages and theme, in case you only
want to look something up or copy a paragraph back by hand.
"""


def _env_float(name: str, default: float) -> float:
    try:
        value = float(os.environ.get(name, "") or default)
        return value if value >= 0 else default
    except ValueError:
        return default


def settings() -> dict[str, float]:
    return {
        "every_hours": _env_float("BACKUP_EVERY_HOURS", 12.0),
        "keep_days": _env_float("BACKUP_KEEP_DAYS", 21.0),
        "max_mb": _env_float("BACKUP_MAX_MB", 400.0),
    }


def backup_dir(db_path) -> Path:
    return Path(db_path).parent / FOLDER


def _fingerprint(db_path) -> str:
    """Cheap signature of everything worth backing up."""
    conn = sqlite3.connect(f"file:{Path(db_path)}?mode=ro", uri=True, timeout=30)
    try:
        conn.row_factory = sqlite3.Row
        state = conn.execute("SELECT revision, updated_at FROM site_state WHERE id = 1").fetchone()
        media = conn.execute("SELECT COUNT(*) AS n, COALESCE(SUM(bytes), 0) AS b FROM media_assets").fetchone()
        versions = conn.execute("SELECT COUNT(*) AS n FROM site_versions").fetchone()
        messages = conn.execute("SELECT COUNT(*) AS n, COALESCE(MAX(id), 0) AS last FROM messages").fetchone()
        return "|".join(str(part) for part in (
            state["revision"] if state else 0,
            state["updated_at"] if state else "",
            media["n"], media["b"], versions["n"], messages["n"], messages["last"],
        ))
    finally:
        conn.close()


def _site_json(db_path) -> bytes:
    conn = sqlite3.connect(f"file:{Path(db_path)}?mode=ro", uri=True, timeout=30)
    try:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM site_state WHERE id = 1").fetchone()
        payload: dict[str, Any] = {"savedAt": datetime.now(timezone.utc).isoformat()}
        if row:
            payload.update({
                "revision": row["revision"],
                "publishedAt": row["published_at"],
                "draftPages": json.loads(row["draft_pages"]),
                "draftTheme": json.loads(row["draft_theme"]),
                "publishedPages": json.loads(row["published_pages"]),
                "publishedTheme": json.loads(row["published_theme"]),
            })
        media = conn.execute("SELECT id, name, mime, kind, bytes, created_at FROM media_assets WHERE deleted_at IS NULL").fetchall()
        payload["media"] = [dict(item) for item in media]
        return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    finally:
        conn.close()


def _snapshot_db(db_path, target: Path) -> None:
    """Copy the live database safely, even while it is being written to."""
    source = sqlite3.connect(f"file:{Path(db_path)}?mode=ro", uri=True, timeout=60)
    try:
        destination = sqlite3.connect(target, timeout=60)
        try:
            source.backup(destination)
        finally:
            destination.close()
    finally:
        source.close()


def prune(db_path, keep_days: float | None = None, max_mb: float | None = None) -> list[str]:
    """Delete snapshots older than the window, then trim by total size."""
    options = settings()
    keep_days = options["keep_days"] if keep_days is None else keep_days
    max_mb = options["max_mb"] if max_mb is None else max_mb
    folder = backup_dir(db_path)
    if not folder.exists():
        return []
    files = sorted(folder.glob(f"{PREFIX}*.zip"), key=lambda item: item.stat().st_mtime)
    removed: list[str] = []
    cutoff = (datetime.now(timezone.utc) - timedelta(days=keep_days)).timestamp()
    for item in list(files):
        # Always keep the two newest, no matter how old they are: an idle
        # site should still have something to restore from.
        if len(files) - len(removed) <= 2:
            break
        if item.stat().st_mtime < cutoff:
            item.unlink(missing_ok=True)
            removed.append(item.name)
    remaining = [item for item in files if item.name not in removed]
    budget = max_mb * 1024 * 1024
    total = sum(item.stat().st_size for item in remaining)
    for item in remaining:
        if total <= budget or len(remaining) - len(removed) <= 2:
            break
        total -= item.stat().st_size
        item.unlink(missing_ok=True)
        removed.append(item.name)
    return removed


def create(db_path, force: bool = False) -> Path | None:
    """Write one snapshot. Returns None when nothing changed since the last."""
    folder = backup_dir(db_path)
    folder.mkdir(parents=True, exist_ok=True)
    marker = folder / ".last.json"
    fingerprint = _fingerprint(db_path)
    if not force and marker.exists():
        try:
            previous = json.loads(marker.read_text())
            if previous.get("fingerprint") == fingerprint and (folder / previous.get("file", "")).exists():
                return None
        except (ValueError, OSError):
            pass
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    target = folder / f"{PREFIX}{stamp}.zip"
    temp_db = folder / f".snapshot-{stamp}.db"
    try:
        _snapshot_db(db_path, temp_db)
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            archive.write(temp_db, "portfolio.db")
            archive.writestr("site.json", _site_json(db_path))
            archive.writestr("README.txt", RESTORE_NOTE)
    finally:
        temp_db.unlink(missing_ok=True)
        for leftover in folder.glob(".snapshot-*.db*"):
            leftover.unlink(missing_ok=True)
    marker.write_text(json.dumps({"fingerprint": fingerprint, "file": target.name, "at": stamp}))
    return target


def run_once(db_path, force: bool = False) -> Path | None:
    made = create(db_path, force=force)
    removed = prune(db_path)
    if made:
        size = made.stat().st_size / 1024 / 1024
        print(f"Backup: {made.name} ({size:.1f} MB)", flush=True)
    if removed:
        print(f"Backup: removed {len(removed)} old snapshot(s)", flush=True)
    return made


def _loop(db_path, every_hours: float) -> None:
    interval = every_hours * 3600
    while True:
        try:
            run_once(db_path)
        except Exception:  # pragma: no cover - a backup must never stop the site
            traceback.print_exc()
        deadline = time.time() + interval
        while time.time() < deadline:
            time.sleep(min(300.0, max(1.0, deadline - time.time())))


def start(db_path) -> threading.Thread | None:
    """Kick off the background schedule (runs one backup right away)."""
    options = settings()
    if options["every_hours"] <= 0:
        print("Backups: disabled (BACKUP_EVERY_HOURS=0)", flush=True)
        return None
    thread = threading.Thread(target=_loop, args=(db_path, options["every_hours"]), daemon=True, name="backup")
    thread.start()
    print(
        f"Backups: every {options['every_hours']:g}h into {backup_dir(db_path)}, "
        f"kept for {options['keep_days']:g} days",
        flush=True,
    )
    return thread
