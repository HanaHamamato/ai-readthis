"""Content validation — port of src/lib/site.ts (zod) to Python.

Same rules, same defaults, same error messages, so the editor and the
server reject exactly the same inputs as before.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Any

FONT_CHOICES = ["modern", "rounded", "editorial", "mono", "studio"]
BLOCK_TYPES = [
    "heading", "paragraph", "quote", "list", "code", "button", "image",
    "file", "card", "divider", "spacer", "section", "timeline", "gallery", "embed",
]
MAX_TIMELINE_ITEMS = 40
MAX_GALLERY_IMAGES = 24
FONT_OVERRIDES = ["inherit", *FONT_CHOICES]
ALIGNMENTS = ["left", "center", "right"]
SIZES = ["sm", "md", "lg", "xl"]
RESERVED_SLUGS = {
    "adminpanel", "api", "_next", "assets", "fonts", "favicon.ico",
    "robots.txt", "sitemap.xml", "portfolio.css", "portfolio.js",
}

COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
SLUG_RE = re.compile(r"^(?:[a-z0-9]+(?:-[a-z0-9]+)*)?$")
SAFE_RELATIVE_RE = re.compile(r"^/(?:[a-z0-9]+(?:-[a-z0-9]+)*\/?)?(?:#[a-z0-9-]+)?$", re.IGNORECASE)
SAFE_ANCHOR_RE = re.compile(r"^#[a-z0-9-]+$", re.IGNORECASE)
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)

# Embeds: the id is pulled out of the link and a fresh player URL is built from
# it, so nothing the visitor typed ever reaches the iframe src directly.
YOUTUBE_RE = re.compile(r"(?:youtube\.com/(?:watch\?(?:[^#]*&)?v=|embed/|shorts/|live/|v/)|youtu\.be/)([A-Za-z0-9_-]{6,24})")
VIMEO_RE = re.compile(r"vimeo\.com/(?:video/|channels/[A-Za-z0-9_-]+/)?(\d{6,15})")
VIDEO_FILE_RE = re.compile(r"\.(?:mp4|webm|ogv|mov|m4v)(?:[?#]|$)", re.IGNORECASE)


def parse_embed(url: Any) -> dict[str, str]:
    """Work out what a pasted link points at, without contacting anyone."""
    if not isinstance(url, str) or not url.strip():
        return {"kind": "", "src": "", "label": ""}
    url = url.strip()
    match = YOUTUBE_RE.search(url)
    if match:
        return {"kind": "youtube", "src": f"https://www.youtube-nocookie.com/embed/{match.group(1)}?rel=0&autoplay=1",
                "label": "YouTube"}
    match = VIMEO_RE.search(url)
    if match:
        return {"kind": "vimeo", "src": f"https://player.vimeo.com/video/{match.group(1)}?autoplay=1",
                "label": "Vimeo"}
    if VIDEO_FILE_RE.search(url) and (url.startswith(("https://", "http://")) or url.startswith("/")):
        return {"kind": "video", "src": url, "label": "Video"}
    return {"kind": "link", "src": url, "label": "Link"}


class ValidationError(Exception):
    """Carries the first issue message, like zod's error.issues[0].message."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


def _is_uuid(value: Any) -> bool:
    return isinstance(value, str) and bool(UUID_RE.match(value))


def _int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _str(value: Any) -> bool:
    return isinstance(value, str)


def parse_safe_link(value: Any) -> str:
    if value is None:
        return ""
    if not _str(value):
        raise ValidationError("Link destination is invalid.")
    if len(value) > 500:
        raise ValidationError("Link destination is too long.")
    if not value:
        return value
    if SAFE_RELATIVE_RE.match(value):
        return value
    if SAFE_ANCHOR_RE.match(value):
        return value
    if value.startswith(("http://", "https://", "mailto:")):
        if "://" in value:
            scheme, rest = value.split("://", 1)
            if "@" in rest.split("/", 1)[0]:
                raise ValidationError("Link destination is invalid.")
            return value
        return value
    raise ValidationError("Link destination is invalid.")


def _color(value: Any) -> str:
    if value is None:
        return ""
    if not _str(value) or not (COLOR_RE.match(value) or value == ""):
        raise ValidationError("Color must be a hex value like #7956c4.")
    return value


def parse_block(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError("Each block must be an object.")
    block_id = value.get("id")
    if not _is_uuid(block_id):
        raise ValidationError("A block is missing its id.")
    block_type = value.get("type")
    if block_type not in BLOCK_TYPES:
        raise ValidationError("A block has an unknown type.")
    text = value.get("text", "")
    title = value.get("title", "")
    if not _str(text) or len(text) > 16000:
        raise ValidationError("Block text is too long.")
    if not _str(title) or len(title) > 200:
        raise ValidationError("Block title is too long.")
    level = value.get("level", 2)
    if not _int(level) or not 1 <= level <= 3:
        raise ValidationError("Heading level must be 1, 2, or 3.")
    align = value.get("align", "left")
    if align not in ALIGNMENTS:
        raise ValidationError("Alignment is invalid.")
    size = value.get("size", "md")
    if size not in SIZES:
        raise ValidationError("Text size is invalid.")

    def bounded(name: str, key: str, low: int, high: int, default: int) -> int:
        raw = value.get(key, default)
        if not _int(raw) or not low <= raw <= high:
            raise ValidationError(f"{name} is out of range.")
        return raw

    media_id = value.get("mediaId", "")
    if not (media_id == "" or _is_uuid(media_id)):
        raise ValidationError("A block references an unknown upload.")
    alt = value.get("alt", "")
    if not _str(alt) or len(alt) > 250:
        raise ValidationError("Alt text is too long.")
    font_override = value.get("fontOverride", "inherit")
    if font_override not in FONT_OVERRIDES:
        raise ValidationError("Block font is invalid.")

    raw_items = value.get("items", [])
    if not isinstance(raw_items, list) or len(raw_items) > MAX_TIMELINE_ITEMS:
        raise ValidationError(f"A timeline can hold at most {MAX_TIMELINE_ITEMS} entries.")
    items: list[dict[str, str]] = []
    for entry in raw_items:
        if not isinstance(entry, dict):
            raise ValidationError("Each timeline entry must be an object.")
        label = entry.get("label", "")
        entry_title = entry.get("title", "")
        entry_text = entry.get("text", "")
        if not _str(label) or len(label) > 40:
            raise ValidationError("A timeline date is too long (40 characters).")
        if not _str(entry_title) or len(entry_title) > 120:
            raise ValidationError("A timeline title is too long (120 characters).")
        if not _str(entry_text) or len(entry_text) > 600:
            raise ValidationError("A timeline description is too long (600 characters).")
        items.append({"label": label, "title": entry_title, "text": entry_text})

    raw_gallery = value.get("mediaIds", [])
    if not isinstance(raw_gallery, list) or len(raw_gallery) > MAX_GALLERY_IMAGES:
        raise ValidationError(f"A gallery can hold at most {MAX_GALLERY_IMAGES} images.")
    media_ids: list[str] = []
    for entry in raw_gallery:
        if not _is_uuid(entry):
            raise ValidationError("A gallery references an unknown upload.")
        if entry not in media_ids:
            media_ids.append(entry)

    columns = value.get("columns", 3)
    if not _int(columns) or not 2 <= columns <= 4:
        raise ValidationError("Gallery columns must be 2, 3, or 4.")
    return {
        "id": block_id,
        "type": block_type,
        "text": text,
        "title": title,
        "url": parse_safe_link(value.get("url", "")),
        "newTab": bool(value.get("newTab", False)),
        "level": level,
        "align": align,
        "size": size,
        "width": bounded("Width", "width", 20, 100, 100),
        "spacing": bounded("Space below", "spacing", 0, 120, 24),
        "padding": bounded("Inner padding", "padding", 0, 100, 0),
        "marginTop": bounded("Margin above", "marginTop", 0, 120, 0),
        "color": _color(value.get("color", "")),
        "background": _color(value.get("background", "")),
        "mediaId": media_id,
        "alt": alt,
        "showDownload": bool(value.get("showDownload", True)),
        "fontOverride": font_override,
        "items": items,
        "mediaIds": media_ids,
        "columns": columns,
    }


def parse_page(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError("Each page must be an object.")
    page_id = value.get("id")
    if page_id != "home" and not _is_uuid(page_id):
        raise ValidationError("A page is missing its id.")
    title = value.get("title")
    if not _str(title) or not (1 <= len(title.strip()) <= 100):
        raise ValidationError("Every page needs a title (1–100 characters).")
    slug = value.get("slug")
    if not _str(slug) or len(slug) > 65 or not SLUG_RE.match(slug):
        raise ValidationError("The URL must use lowercase letters, numbers, and dashes.")
    description = value.get("description", "")
    if not _str(description) or len(description) > 260:
        raise ValidationError("The meta description is too long.")
    blocks = value.get("blocks")
    if not isinstance(blocks, list) or len(blocks) > 200:
        raise ValidationError("A page can contain at most 200 blocks.")
    parsed_blocks = [parse_block(block) for block in blocks]
    return {
        "id": page_id,
        "title": title,
        "slug": slug,
        "description": description,
        "visible": bool(value.get("visible", True)),
        "blocks": parsed_blocks,
    }


def parse_pages(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not 1 <= len(value) <= 50:
        raise ValidationError("The site needs between 1 and 50 pages.")
    pages = [parse_page(page) for page in value]
    first = pages[0]
    if first.get("id") != "home" or first.get("slug") != "" or sum(1 for p in pages if p["id"] == "home") != 1:
        raise ValidationError("Home must remain the first page at /.")
    slugs: set[str] = set()
    ids: set[str] = set()
    for page in pages:
        if (
            page["slug"] in slugs
            or page["id"] in ids
            or page["slug"] in RESERVED_SLUGS
            or (page["id"] != "home" and not page["slug"])
        ):
            raise ValidationError(f"Duplicate or reserved page path: {page['slug'] or '/'}.")
        slugs.add(page["slug"])
        ids.add(page["id"])
        block_ids = [block["id"] for block in page["blocks"]]
        if len(set(block_ids)) != len(block_ids):
            raise ValidationError(f"Duplicate blocks on {page['title']}.")
    return pages


def parse_theme(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError("The theme must be an object.")

    def color(key: str) -> str:
        raw = value.get(key)
        if not _str(raw) or not COLOR_RE.match(raw):
            raise ValidationError(f"The theme {key} color is invalid.")
        return raw

    def enum(key: str, choices: list[str]) -> str:
        raw = value.get(key)
        if raw not in choices:
            raise ValidationError(f"The theme {key} setting is invalid.")
        return raw

    def scale(key: str) -> float:
        raw = value.get(key)
        if not isinstance(raw, (int, float)) or isinstance(raw, bool) or not 0.8 <= float(raw) <= 1.5:
            raise ValidationError(f"The theme {key} is out of range.")
        return float(raw)

    def int_scale(key: str, low: int, high: int) -> int:
        raw = value.get(key)
        if not _int(raw) or not low <= raw <= high:
            raise ValidationError(f"The theme {key} is out of range.")
        return raw

    return {
        "mode": enum("mode", ["light", "dark"]),
        "background": color("background"),
        "surface": color("surface"),
        "text": color("text"),
        "muted": color("muted"),
        "accent": color("accent"),
        "font": enum("font", FONT_CHOICES),
        "headingScale": scale("headingScale"),
        "spacing": scale("spacing"),
        "radius": int_scale("radius", 0, 36),
        "borderWidth": int_scale("borderWidth", 0, 3),
        "shadow": enum("shadow", ["soft", "crisp", "none"]),
        "cardStyle": enum("cardStyle", ["elevated", "outline", "flat"]),
        "buttonStyle": enum("buttonStyle", ["solid", "outline", "soft"]),
        "animation": enum("animation", ["off", "subtle", "expressive"]),
    }


def parse_state_input(value: Any) -> tuple[int, list[dict[str, Any]], dict[str, Any]]:
    if not isinstance(value, dict):
        raise ValidationError("The draft payload is invalid.")
    revision = value.get("revision")
    if not _int(revision) or revision < 0:
        raise ValidationError("The draft revision is invalid.")
    pages = parse_pages(value.get("pages"))
    theme = parse_theme(value.get("theme"))
    return revision, pages, theme


DEFAULT_THEME: dict[str, Any] = {
    "mode": "light", "background": "#f8f6fc", "surface": "#ffffff", "text": "#29233a",
    "muted": "#786f88", "accent": "#7956c4", "font": "modern", "headingScale": 1,
    "spacing": 1, "radius": 22, "borderWidth": 1, "shadow": "soft",
    "cardStyle": "elevated", "buttonStyle": "solid", "animation": "subtle",
}

HOME_PAGE: dict[str, Any] = {
    "id": "home", "title": "Home", "slug": "",
    "description": "", "visible": True, "blocks": [],
}


def new_block(block_type: str) -> dict[str, Any]:
    return {
        "id": str(uuid.uuid4()), "type": block_type, "text": "", "title": "",
        "url": "", "newTab": False, "level": 2, "align": "left", "size": "md",
        "width": 100, "spacing": 24, "padding": 0, "marginTop": 0, "color": "",
        "background": "", "mediaId": "", "alt": "", "showDownload": True,
        "fontOverride": "inherit",
    }


def page_path(page: dict[str, Any]) -> str:
    return f"/{page['slug']}" if page.get("slug") else "/"


def section_id(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9\s-]", "", text.lower())
    cleaned = re.sub(r"\s+", "-", cleaned.strip())
    return cleaned[:64] or "section"


def is_external(url: str) -> bool:
    return bool(re.match(r"^https?://", url, re.IGNORECASE))


def safe_href(url: Any) -> str:
    if not _str(url):
        return "#"
    try:
        if parse_safe_link(url) != url:
            return "#"
        return url or "#"
    except ValidationError:
        return "#"


def is_valid_json_object(value: Any) -> bool:
    return isinstance(value, dict)
