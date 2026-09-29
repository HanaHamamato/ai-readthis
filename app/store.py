"""Site state store — port of src/lib/server/store.ts onto SQLite.

Draft and published snapshots live side by side with an optimistic revision
counter; every publication backs up the previous published snapshot into
site_versions.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .db import dumps, get_db, loads, utcnow
from .validation import DEFAULT_THEME, HOME_PAGE, ValidationError, parse_pages, parse_theme, section_id  # noqa: F401


class AppError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


def get_site(db_path) -> dict[str, Any]:
    conn = get_db(db_path)
    with conn:
        conn.execute(
            """INSERT OR IGNORE INTO site_state (id, revision, draft_pages, published_pages, draft_theme, published_theme, updated_at)
               VALUES (1, 0, ?, ?, ?, ?, ?)""",
            (
                dumps([HOME_PAGE]), dumps([HOME_PAGE]),
                dumps(DEFAULT_THEME), dumps(DEFAULT_THEME), utcnow(),
            ),
        )
    row = conn.execute("SELECT * FROM site_state WHERE id = 1").fetchone()
    state = dict(row)
    state["draftPages"] = loads(state.pop("draft_pages"), [HOME_PAGE])
    state["publishedPages"] = loads(state.pop("published_pages"), [HOME_PAGE])
    state["draftTheme"] = loads(state.pop("draft_theme"), DEFAULT_THEME)
    state["publishedTheme"] = loads(state.pop("published_theme"), DEFAULT_THEME)
    return state


def referenced_media(pages: list[dict[str, Any]]) -> list[str]:
    """Every upload a page points at — single `mediaId`s and gallery lists."""
    refs: list[str] = []
    for page in pages:
        for block in page.get("blocks", []):
            media_id = block.get("mediaId")
            if media_id and media_id not in refs:
                refs.append(media_id)
            for gallery_id in block.get("mediaIds") or []:
                if gallery_id and gallery_id not in refs:
                    refs.append(gallery_id)
    return refs


def verify_media(conn, pages: list[dict[str, Any]]) -> None:
    refs = referenced_media(pages)
    if not refs:
        return
    placeholders = ",".join("?" * len(refs))
    rows = conn.execute(
        f"SELECT id, kind, deleted_at FROM media_assets WHERE id IN ({placeholders})", refs
    ).fetchall()
    if len(rows) != len(refs) or any(row["deleted_at"] for row in rows):
        raise AppError("A page uses a missing or deleted upload. Replace it before saving.")
    kinds = {row["id"]: row["kind"] for row in rows}
    for page in pages:
        for block in page.get("blocks", []):
            if block.get("type") == "image" and block.get("mediaId") and kinds.get(block["mediaId"]) != "image":
                raise AppError("An image block must use an image upload.")
            if block.get("type") == "file" and block.get("mediaId") and block["mediaId"] not in kinds:
                raise AppError("A file block uses an invalid upload.")
            if block.get("type") == "gallery":
                for gallery_id in block.get("mediaIds") or []:
                    if kinds.get(gallery_id) != "image":
                        raise AppError("A gallery can only hold image uploads.")


def save_draft(db_path, pages: list[dict[str, Any]], theme: dict[str, Any], revision: int) -> int:
    parse_pages(pages)
    parse_theme(theme)
    conn = get_db(db_path)
    verify_media(conn, pages)
    with conn:
        cursor = conn.execute(
            """UPDATE site_state SET draft_pages = ?, draft_theme = ?, revision = ?, updated_at = ?
               WHERE id = 1 AND revision = ?""",
            (dumps(pages), dumps(theme), revision + 1, utcnow(), revision),
        )
    if cursor.rowcount == 0:
        raise AppError("This draft changed elsewhere. Reload before saving again.", 409)
    return revision + 1


def publish_draft(db_path, revision: int) -> dict[str, Any]:
    conn = get_db(db_path)
    state = get_site(db_path)
    verify_media(conn, state["draftPages"])
    with conn:
        row = conn.execute("SELECT * FROM site_state WHERE id = 1").fetchone()
        current = dict(row)
        for field in ("draft_pages", "published_pages", "draft_theme", "published_theme"):
            current[field] = loads(current[field], {})
        if not current or current["revision"] != revision:
            raise AppError("This draft changed elsewhere. Reload before publishing.", 409)
        parse_pages(current["draft_pages"])
        parse_theme(current["draft_theme"])
        if current.get("published_at"):
            conn.execute(
                "INSERT INTO site_versions (pages, theme, published_at) VALUES (?, ?, ?)",
                (dumps(current["published_pages"]), dumps(current["published_theme"]), current["published_at"]),
            )
        published_at = datetime.now(timezone.utc)
        conn.execute(
            """UPDATE site_state SET published_pages = ?, published_theme = ?, published_at = ?,
               revision = ?, updated_at = ? WHERE id = 1""",
            (
                dumps(current["draft_pages"]), dumps(current["draft_theme"]),
                published_at.strftime("%Y-%m-%d %H:%M:%S.%f"), revision + 1,
                published_at.strftime("%Y-%m-%d %H:%M:%S.%f"),
            ),
        )
    return {
        "revision": revision + 1,
        "pages": current["draft_pages"],
        "theme": current["draft_theme"],
        "publishedAt": published_at.isoformat(),
    }


def get_versions(db_path) -> list[dict[str, Any]]:
    conn = get_db(db_path)
    rows = conn.execute("SELECT id, published_at, pages FROM site_versions ORDER BY id DESC LIMIT 50").fetchall()
    return [
        {
            "id": row["id"],
            "publishedAt": row["published_at"],
            "pages": loads(row["pages"], []),
        }
        for row in rows
    ]


def restore_version(db_path, version_id: int, revision: int) -> dict[str, Any]:
    conn = get_db(db_path)
    row = conn.execute("SELECT * FROM site_versions WHERE id = ?", (version_id,)).fetchone()
    if not row:
        raise AppError("That version no longer exists.", 404)
    pages = loads(row["pages"], [])
    theme = loads(row["theme"], {})
    verify_media(conn, pages)
    with conn:
        cursor = conn.execute(
            """UPDATE site_state SET draft_pages = ?, draft_theme = ?, revision = ?, updated_at = ?
               WHERE id = 1 AND revision = ?""",
            (dumps(pages), dumps(theme), revision + 1, utcnow(), revision),
        )
    if cursor.rowcount == 0:
        raise AppError("This draft changed elsewhere. Reload before restoring.", 409)
    return {"revision": revision + 1, "pages": pages, "theme": theme}


def is_media_published(db_path, media_id: str) -> bool:
    state = get_site(db_path)
    return media_id in referenced_media(state["publishedPages"])


def is_media_in_use(db_path, media_id: str) -> bool:
    state = get_site(db_path)
    if media_id in referenced_media(state["draftPages"] + state["publishedPages"]):
        return True
    for version in get_versions(db_path):
        if media_id in referenced_media(version["pages"]):
            return True
    return False
