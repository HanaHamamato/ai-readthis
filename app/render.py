"""HTML rendering for the public site, preview, robots and sitemap.

The markup mirrors the original React components (same element structure,
classes and inline styles), so public/portfolio.css — the design sheet —
renders it exactly as before. The data-* attributes are the hooks that
public/portfolio.js (unchanged) wires up for fonts, menus and the cookie
notice.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from .engagement import BODY_MAX, BODY_MIN, NAME_MAX
from .validation import is_external, page_path, parse_embed, safe_href, section_id

FONT_NOTES = {
    "modern": "Clear & balanced", "rounded": "Soft & friendly", "editorial": "A little literary",
    "mono": "Made for makers", "studio": "Clean & considered",
}
FONT_LABELS = {"modern": "Modern", "rounded": "Rounded", "editorial": "Editorial", "mono": "Monospace", "studio": "Studio"}


def esc(value: Any) -> str:
    return (
        str(value if value is not None else "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _svg(body: str, size: int = 19) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" '
        f'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        f'aria-hidden="true">{body}</svg>'
    )


# Lucide icon geometry (24x24 stroke paths).
ICONS = {
    "home": '<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z"/><path d="M9 21v-7h6v7"/>',
    "file-stack": '<path d="M15.5 2H8a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V7.5L15.5 2z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/>',
    "type": '<polyline points="4 7 4 4 20 4 20 7"/><line x1="9" x2="15" y1="20" y2="20"/><line x1="12" x2="12" y1="4" y2="20"/>',
    "chevron-down": '<path d="m6 9 6 6 6-6"/>',
    "menu": '<line x1="4" x2="20" y1="6" y2="6"/><line x1="4" x2="20" y1="12" y2="12"/><line x1="4" x2="20" y1="18" y2="18"/>',
    "x": '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
    "sparkles": '<path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"/><path d="M20 3v4"/><path d="M22 5h-4"/>',
    "arrow-left": '<path d="m12 19-7-7 7-7"/><path d="M19 12H5"/>',
    "arrow-right": '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
    "arrow-up-right": '<path d="M7 7h10v10"/><path d="M7 17 17 7"/>',
    "arrow-down-to-line": '<path d="M12 17V3"/><path d="m6 11 6 6 6-6"/><path d="M19 21H5"/>',
    "play": '<polygon points="6 3 20 12 6 21 6 3"/>',
    "file-text": '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/>',
    "lock-keyhole": '<rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><circle cx="12" cy="16" r="1"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    "eye": '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>',
    "eye-off": '<path d="M9.88 9.88a3 3 0 1 0 4.24 4.24"/><path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68"/><path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61"/><line x1="2" x2="22" y1="2" y2="22"/>',
    "refresh-cw": '<path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/>',
}


def icon(name: str, size: int = 19, stroke_width: float = 2) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" '
        f'fill="none" stroke="currentColor" stroke-width="{stroke_width}" stroke-linecap="round" '
        f'stroke-linejoin="round" aria-hidden="true">{ICONS[name]}</svg>'
    )


def _md_text(value: str) -> str:
    out = esc(value)
    out = _CODE_RE.sub(r"<code>\1</code>", out)
    out = _BOLD_RE.sub(r"<strong>\1</strong>", out)
    out = _ITALIC_RE.sub(r"<em>\1</em>", out)
    out = _DEL_RE.sub(r"<del>\1</del>", out)
    return out.replace("\n", "<br>")


_CODE_RE = re.compile(r"`([^`\n]+)`")
_BOLD_RE = re.compile(r"\*\*([^*\n]+)\*\*")
_ITALIC_RE = re.compile(r"\*([^*\n]+)\*")
_DEL_RE = re.compile(r"~~([^~\n]+)~~")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")


def inline_md(value: str, new_tab: bool = False) -> str:
    """Markdown-like inline formatting (bold, italic, code, del, links)."""
    result = ""
    cursor = 0
    for match in _LINK_RE.finditer(value):
        result += _md_text(value[cursor:match.start()])
        url = safe_href(match.group(2))
        label = _md_text(match.group(1))
        if url == "#":
            result += label
        else:
            # Same rule as the original: new-tab only for external or
            # same-site links, and only when the block opts into it.
            blank = new_tab and (is_external(url) or url.startswith("/"))
            target = ' target="_blank" rel="noopener noreferrer"' if blank else ""
            result += f'<a href="{esc(url)}"{target}>{label}</a>'
        cursor = match.end()
    return result + _md_text(value[cursor:])


def block_style(block: dict[str, Any]) -> str:
    parts = [
        f"width:{block.get('width', 100)}%",
        "max-width:100%",
        f"margin-top:{block.get('marginTop', 0)}px",
    ]
    if block.get("type") == "spacer":
        parts.append("margin-bottom:0")
    else:
        parts.append(f"margin-bottom:calc({block.get('spacing', 24)}px * var(--site-spacing))")
    if block.get("padding"):
        parts.append(f"padding:{block['padding']}px")
    parts.append(f"text-align:{block.get('align', 'left')}")
    if block.get("color"):
        parts.append(f"color:{block['color']}")
    if block.get("background"):
        parts.append(f"background-color:{block['background']}")
    return ";".join(parts)


def block_html(block: dict[str, Any], media_urls: dict[str, str], media_info: dict[str, dict[str, str]], editing: bool = False) -> str:
    btype = block.get("type", "")
    text = block.get("text", "")
    media_id = block.get("mediaId", "")
    media_url = media_urls.get(media_id) or (f"/api/media/{media_id}" if media_id else "")
    info = media_info.get(media_id) or {}
    content = ""
    if btype == "heading":
        level = block.get("level", 2)
        inner = inline_md(text, block.get("newTab", False)) if text else (
            '<span class="block-empty">A new heading</span>' if editing else ""
        )
        content = f"<h{level} id=\"{esc(section_id(text))}\" class=\"block-heading block-heading-{block.get('size', 'md')}\">{inner}</h{level}>"
    elif btype == "paragraph":
        inner = inline_md(text, block.get("newTab", False)) if text else (
            '<span class="block-empty">Write something lovely here...</span>' if editing else ""
        )
        content = f'<p class="block-paragraph block-text-{block.get("size", "md")}">{inner}</p>'
    elif btype == "quote":
        inner = inline_md(text, block.get("newTab", False)) if text else (
            '<span class="block-empty">A quote worth keeping.</span>' if editing else ""
        )
        content = (
            f'<blockquote class="block-quote block-text-{block.get("size", "md")}">'
            f'<span class="quote-mark">\u201c</span>{inner}</blockquote>'
        )
    elif btype == "list":
        lines = [line.strip() for line in text.split("\n")]
        lines = [re.sub(r"^(?:[-*\u2022]|\d+\.)\s*", "", line) for line in lines if line.strip()]
        if lines:
            items = "".join(f"<li>{inline_md(line, block.get('newTab', False))}</li>" for line in lines)
            content = f'<ul class="block-list block-text-{block.get("size", "md")}">{items}</ul>'
        elif editing:
            content = '<span class="block-empty">Add one item per line</span>'
    elif btype == "code":
        content = f'<pre class="block-code"><code>{esc(text)}</code></pre>' if text else (
            '<span class="block-empty">Your code goes here</span>' if editing else ""
        )
    elif btype == "button":
        if block.get("url"):
            target = ' target="_blank" rel="noopener noreferrer"' if block.get("newTab") else ""
            content = (
                f'<a class="site-button block-button" href="{esc(safe_href(block["url"]))}"{target}>'
                f"{esc(text or 'Explore')}{icon('arrow-up-right', 17)}</a>"
            )
        elif editing:
            content = '<span class="block-empty">Add a label and destination to make a button</span>'
    elif btype == "image":
        if media_id:
            caption = f"<figcaption>{esc(text)}</figcaption>" if text else ""
            content = (
                f'<figure class="block-image"><img src="{esc(media_url)}" alt="{esc(block.get("alt", ""))}"'
                f'{image_dimensions(info)} loading="lazy" decoding="async">{caption}</figure>'
            )
        elif editing:
            content = '<span class="block-empty">Choose an image from your library</span>'
    elif btype == "file":
        if media_id:
            label = block.get("title") or info.get("name") or "File"
            video = ""
            if info.get("kind") == "video":
                video = f'<video controls preload="metadata" playsinline src="{esc(media_url)}" aria-label="{esc(block.get("alt") or label)}"></video>'
            glyph = icon("play", 21) if info.get("kind") == "video" else icon("file-text", 21)
            download = ""
            if block.get("showDownload", True):
                download = (
                    f'<a href="{esc(media_url)}" download="{esc(info.get("name") or label)}" class="file-download" '
                    f'aria-label="Download {esc(label)}">{icon("arrow-down-to-line", 17)}<span>Download</span></a>'
                )
            description = f"<small>{esc(text)}</small>" if text else ""
            content = (
                f'<div class="file-block">{video}<div class="file-card">'
                f'<span class="file-card-icon">{glyph}</span>'
                f'<span class="file-card-text"><strong>{esc(label)}</strong>{description}</span>'
                f"{download}</div></div>"
            )
        elif editing:
            content = '<span class="block-empty">Choose a file from your library</span>'
    elif btype == "card":
        target = ' target="_blank" rel="noopener noreferrer"' if block.get("newTab") else ""
        title_html = f"<h3>{esc(block.get('title'))}</h3>" if block.get("title") else ""
        description_text = text or ("Write a little about this..." if editing else "")
        link_html = (
            f'<a class="card-link" href="{esc(safe_href(block["url"]))}"{target}>Explore {icon("arrow-up-right", 15)}</a>'
            if block.get("url") else ""
        )
        content = (
            f'<article class="content-card"><span class="card-sparkle">\u2733</span>{title_html}'
            f'<div class="card-description">{inline_md(description_text, block.get("newTab", False))}</div>'
            f"{link_html}</article>"
        )
    elif btype == "section":
        eyebrow = block.get("title") or "A little more"
        heading = text or ("Your section heading" if editing else "")
        content = (
            f'<section class="content-section" id="{esc(section_id(block.get("title") or block.get("text", "")))}">'
            f'<span class="section-eyebrow">{esc(eyebrow)}</span><h2>{esc(heading)}</h2></section>'
        )
    elif btype == "timeline":
        entries = [item for item in (block.get("items") or []) if (item.get("label") or item.get("title") or item.get("text"))]
        if entries:
            rows = ""
            for item in entries:
                label = f'<span class="timeline-when">{esc(item.get("label", ""))}</span>' if item.get("label") else ""
                heading = f'<h3 class="timeline-title">{inline_md(item.get("title", ""), block.get("newTab", False))}</h3>' if item.get("title") else ""
                note = f'<p class="timeline-text">{inline_md(item.get("text", ""), block.get("newTab", False))}</p>' if item.get("text") else ""
                rows += (
                    f'<li class="timeline-entry"><span class="timeline-dot" aria-hidden="true"></span>'
                    f'<div class="timeline-body">{label}{heading}{note}</div></li>'
                )
            content = f'<ol class="block-timeline block-text-{block.get("size", "md")}">{rows}</ol>'
        elif editing:
            content = '<span class="block-empty">Add your first milestone — a date, a title, a line about it</span>'
    elif btype == "gallery":
        ids = [mid for mid in (block.get("mediaIds") or []) if mid]
        if ids:
            tiles = ""
            for index, mid in enumerate(ids):
                url = media_urls.get(mid) or f"/api/media/{mid}"
                details = media_info.get(mid) or {}
                caption = details.get("name", "")
                alt = block.get("alt") or caption
                tiles += (
                    f'<button type="button" class="gallery-tile" data-gallery-open="{index}" '
                    f'data-gallery-src="{esc(url)}" data-gallery-caption="{esc(caption)}"'
                    f'{aspect_style(details)} aria-label="Open image {index + 1} of {len(ids)}">'
                    f'<img src="{esc(url)}" alt="{esc(alt)}"{image_dimensions(details)} '
                    f'loading="lazy" decoding="async"></button>'
                )
            caption_html = f'<figcaption class="gallery-caption">{esc(text)}</figcaption>' if text else ""
            content = (
                f'<figure class="block-gallery gallery-cols-{block.get("columns", 3)}" data-gallery>'
                f'<div class="gallery-grid">{tiles}</div>{caption_html}</figure>'
            )
        elif editing:
            content = '<span class="block-empty">Pick a few images from your library</span>'
    elif btype == "embed":
        media = parse_embed(block.get("url", ""))
        label = block.get("title") or ""
        if media["kind"] in ("youtube", "vimeo"):
            content = (
                f'<figure class="block-embed" data-embed-frame="{esc(media["src"])}" data-embed-title="{esc(label or media["label"])}">'
                f'<button type="button" class="embed-poster" aria-label="Play {esc(label or media["label"])}">'
                f'<span class="embed-play">{icon("play", 26)}</span>'
                f'<span class="embed-meta"><strong>{esc(label or "Watch the video")}</strong>'
                f'<small>{esc(media["label"])} \u00b7 loads only when you press play</small></span></button>'
                + (f'<figcaption>{esc(text)}</figcaption>' if text else "")
                + "</figure>"
            )
        elif media["kind"] == "video":
            content = (
                f'<figure class="block-embed block-embed-file">'
                f'<video controls preload="none" playsinline src="{esc(safe_href(media["src"]))}" '
                f'aria-label="{esc(label or block.get("alt") or "Video")}"></video>'
                + (f'<figcaption>{esc(text)}</figcaption>' if text else "")
                + "</figure>"
            )
        elif media["kind"] == "link":
            target = ' target="_blank" rel="noopener noreferrer"' if block.get("newTab") else ""
            content = (
                f'<a class="site-button block-button" href="{esc(safe_href(block.get("url", "")))}"{target}>'
                f'{esc(label or text or "Open link")}{icon("arrow-up-right", 17)}</a>'
            )
        elif editing:
            content = '<span class="block-empty">Paste a YouTube, Vimeo or video link</span>'
    elif btype == "divider":
        content = '<hr class="block-divider">'
    elif btype == "spacer":
        content = f'<div class="block-spacer" style="height:{block.get("spacing", 24)}px" aria-hidden="true"></div>'
    if not content:
        return ""
    return (
        f'<div data-block-id="{esc(block.get("id", ""))}" class="portfolio-block portfolio-block-{esc(btype)} '
        f'reveal font-{esc(block.get("fontOverride", "inherit"))}" style="{block_style(block)}">{content}</div>'
    )


def content_blocks_html(blocks: list[dict[str, Any]], media_urls: dict[str, str], media_info: dict[str, dict[str, str]]) -> str:
    rendered = [block_html(block, media_urls, media_info) for block in blocks]
    return f'<div class="content-blocks">{"".join(r for r in rendered if r)}</div>'


def theme_style_vars(theme: dict[str, Any]) -> str:
    return (
        f"--site-bg:{theme.get('background', '')};--site-surface:{theme.get('surface', '')};"
        f"--site-text:{theme.get('text', '')};--site-muted:{theme.get('muted', '')};"
        f"--site-accent:{theme.get('accent', '')};--site-radius:{theme.get('radius', 22)}px;"
        f"--site-heading-scale:{theme.get('headingScale', 1)};--site-spacing:{theme.get('spacing', 1)};"
        f"--site-border-width:{theme.get('borderWidth', 1)}px"
    )


def site_classes(theme: dict[str, Any]) -> str:
    return (
        f"public-site font-{theme.get('font', 'modern')} theme-{theme.get('mode', 'light')} "
        f"motion-{theme.get('animation', 'subtle')} shadow-{theme.get('shadow', 'soft')} "
        f"cards-{theme.get('cardStyle', 'elevated')} buttons-{theme.get('buttonStyle', 'solid')}"
    )


def _empty_page_html(page: dict[str, Any]) -> str:
    is_home = page.get("id") == "home"
    eyebrow = ""
    if not is_home:
        eyebrow = f'<div class="eyebrow"><span class="eyebrow-dot"></span>{esc(page.get("title", "").upper())}</div>'
    if is_home:
        headline = "Main Page Hasn’t Been <em>Configured</em> Yet"
        blurb = "I will post here soon, apologize! 😭"
    else:
        headline = "This page is <em>coming soon</em>"
        blurb = "Check back in a little while."
    return (
        f'<div class="empty-page"><div class="empty-copy reveal is-visible">{eyebrow}'
        f"<h1>{headline}<span class=\"hero-dot\">.</span></h1><p>{blurb}</p></div>"
        f'<div class="empty-art" aria-hidden="true"><div class="art-orbit orbit-one"></div>'
        f'<div class="art-orbit orbit-two"></div><div class="art-card art-card-back"><span>\u2733</span>'
        f'<span class="art-line"></span><span class="art-line short"></span></div>'
        f'<div class="art-card art-card-front"><div class="art-flower">\u2733</div></div>'
        f'<span class="art-cross art-cross-one">\u2726</span><span class="art-cross art-cross-two">\u2733</span></div></div>'
    )


def _published_page_html(page: dict[str, Any], theme: dict[str, Any], media_urls: dict[str, Any], media_info: dict[str, dict[str, str]], site_name: str) -> str:
    is_home = page.get("id") == "home"
    blocks = page.get("blocks", [])
    if is_home:
        eyebrow_html = ""
    else:
        eyebrow_html = f'<span class="eyebrow"><span class="eyebrow-dot"></span>EXPLORE / {esc(page.get("title", "").upper())}</span>'
    has_h1 = any(b.get("type") == "heading" and b.get("level") == 1 for b in blocks)
    if is_home or has_h1:
        title_html = f'<h1 class="visually-hidden">{esc(site_name if is_home else page.get("title", ""))}</h1>'
    else:
        title_html = f'<h1 class="published-title">{esc(page.get("title", ""))}<span class="hero-dot">.</span></h1>'
    description = ""
    if not is_home and page.get("description"):
        description = f'<p class="published-description">{esc(page.get("description", ""))}</p>'
    return (
        f'<div class="published-page"><div class="published-intro reveal is-visible">'
        f'{eyebrow_html}{title_html}{description}</div>'
        f'{content_blocks_html(blocks, media_urls, media_info)}</div>'
    )


def image_dimensions(info: dict[str, Any]) -> str:
    """width/height attributes so the page reserves the exact space."""
    width, height = info.get("width"), info.get("height")
    if not width or not height:
        return ""
    return f' width="{int(width)}" height="{int(height)}"'


def aspect_style(info: dict[str, Any]) -> str:
    width, height = info.get("width"), info.get("height")
    if not width or not height:
        return ""
    return f' style="aspect-ratio:{int(width)}/{int(height)}"'


def page_end_html(visits: int) -> str:
    """The end of every public page: the contact form and the visit count."""
    try:
        count = max(0, int(visits))
    except (TypeError, ValueError):
        count = 0
    return (
        '<section class="page-end">'
        '<form class="contact-form" data-contact novalidate>'
        '<h2 class="contact-title">Contact Me</h2>'
        '<label class="contact-field"><span>Name</span>'
        f'<input type="text" data-contact-name maxlength="{NAME_MAX}" autocomplete="name"></label>'
        '<label class="contact-field"><span>Content</span>'
        f'<textarea data-contact-body rows="4" minlength="{BODY_MIN}" maxlength="{BODY_MAX}" required></textarea></label>'
        '<button type="submit" class="contact-send" data-contact-send>Send</button>'
        '<p class="contact-status" role="status" data-contact-status hidden></p>'
        "</form>"
        f'<span class="visit-count" data-visit-count>{count} visits!</span>'
        "</section>"
    )


def site_body(page: dict[str, Any], pages: list[dict[str, Any]], theme: dict[str, Any],
             media_urls: dict[str, str], media_info: dict[str, dict[str, str]],
             site_name: str, preview: bool = False, preview_pages: list[dict[str, Any]] | None = None,
             visits: int = 0) -> str:
    is_home = page.get("id") == "home"
    nav_pages = pages if preview_pages is None else preview_pages
    visible = [p for p in nav_pages if p.get("visible") and p.get("id") != "home"]
    year = datetime.now().year

    home_nav_class = "sidebar-item active" if is_home else "sidebar-item"
    page_items = (
        f'<a href="/" class="{home_nav_class}"'
        + (' aria-current="page"' if is_home else "")
        + f'>{icon("home")}<span>Home</span>'
        + ('<span class="nav-active-dot"></span>' if is_home else "")
        + "</a>"
    )
    panel_items = f'<a href="/" class="{("selected" if is_home else "").strip()}">Home</a>'
    for item in visible:
        panel_items += (
            f'<a href="{page_path(item)}" '
            f'class="{("selected" if page.get("id") == item.get("id") else "").strip()}">'
            f"{esc(item.get('title', ''))}</a>"
        )
    if not visible:
        panel_items += '<span class="sidebar-quiet">More pages soon.</span>'

    font_options = ""
    for font in ("modern", "rounded", "editorial", "mono", "studio"):
        selected = " selected" if theme.get("font") == font else ""
        check = '<span class="font-check">\u2713</span>' if theme.get("font") == font else ""
        font_options += (
            f'<button type="button" class="font-option{selected}" data-font="{font}">'
            f'<span class="font-sample font-{font}">Aa</span>'
            f"<span><strong>{FONT_LABELS[font]}</strong><small>{FONT_NOTES[font]}</small></span>{check}</button>"
        )

    ribbon = ""
    if preview:
        ribbon = (
            f'<div class="preview-ribbon"><span>{icon("sparkles", 15)} Draft preview \u2014 only you can see this</span>'
            f'<a href="/adminpanel">{icon("arrow-left", 15)} Back to editor</a></div>'
        )

    top_line = "Home" if is_home else esc(page.get("title", ""))
    return (
        f'<div class="{site_classes(theme)}" data-default-font="{theme.get("font", "modern")}" style="{theme_style_vars(theme)}">'
        f"{ribbon}"
        f'<header class="mobile-topbar"><a class="mobile-brand" href="/">h<span>.</span></a>'
        f"<span>{esc(site_name.upper())}</span>"
        f'<button type="button" data-menu aria-label="Open menu" aria-expanded="false">{icon("menu", 22)}</button></header>'
        f'<button class="mobile-scrim" type="button" aria-label="Close menu" hidden></button>'
        f'<aside class="site-sidebar">'
        f'<a href="/" class="site-brand"><span class="brand-mark">h<span>.</span></span>'
        f'<span class="brand-copy"><strong>hana.</strong></span></a>'
        f'<div class="sidebar-nav-label">EXPLORE</div>'
        f'<nav class="sidebar-navigation" aria-label="Portfolio navigation">'
        f"{page_items}"
        f'<button type="button" class="sidebar-item{" active-soft" if not is_home else ""}" data-toggle="pages" aria-expanded="false">'
        f'{icon("file-stack")}<span>All pages</span>{icon("chevron-down", 16)}</button>'
        f'<div class="sidebar-expand" data-panel="pages" aria-label="Published pages" hidden>{panel_items}</div>'
        f'<button type="button" class="sidebar-item" data-toggle="fonts" aria-expanded="false">'
        f'{icon("type")}<span>Fonts</span>{icon("chevron-down", 16)}</button>'
        f'<div class="font-options" data-panel="fonts" hidden>{font_options}'
        f'<button class="font-reset" data-font="default" type="button">Use site default</button></div>'
        f"</nav>"
        f'<div class="sidebar-bottom"><div class="sidebar-footer">'
        f"<span>\u00a9 {year} {esc(site_name.upper())}</span></div></div></aside>"
        f'<main class="site-main" id="main-content">'
        f'<div class="site-topline"><div class="topline-path">{top_line}</div></div>'
        + (
            _empty_page_html(page)
            if not page.get("blocks")
            else _published_page_html(page, theme, media_urls, media_info, site_name)
        )
        + page_end_html(visits)
        + "</main>"
        f'<div role="dialog" aria-labelledby="cookie-title" aria-describedby="cookie-description" class="cookie-card" hidden>'
        f'<div class="cookie-icon">\u2733</div>'
        f'<button class="cookie-close" data-cookie="later" type="button" aria-label="Close cookie notice">\u00d7</button>'
        f'<h2 id="cookie-title">A quick note about cookies</h2>'
        f'<p id="cookie-description">Essential cookies keep the private editor secure. Your font choice stays on '
        f"your device.</p>"
        f'<div class="cookie-actions"><button type="button" data-cookie="accepted">Allow essentials '
        f'{icon("arrow-right", 16)}</button><button type="button" data-cookie="later">Not now</button></div></div>'
        f"</div>"
    )


def public_document(page: dict[str, Any], pages: list[dict[str, Any]], theme: dict[str, Any],
                    media_urls: dict[str, str], media_info: dict[str, dict[str, str]],
                    site_url: str, preview: bool = False,
                    site_name: str = "Hana Hamamato", site_description: str = "",
                    visits: int = 0) -> str:
    is_home = page.get("id") == "home"
    base = site_url.rstrip("/")
    if is_home:
        title = f"{site_name} — Portfolio"
        description = page.get("description") or site_description or f"{site_name} — Portfolio"
        url = "/"
    else:
        title = f"{page.get('title', '')} — {site_name}"
        description = page.get("description") or f"{page.get('title', '')} — {site_name}"
        url = page_path(page)
    canonical = base + url
    og_url = base + url
    title_for_tag = "Draft preview — Hana Studio" if preview else title
    robots = ' name="robots" content="noindex, nofollow"' if preview else ""
    return (
        "<!doctype html><html lang=\"en\"><head>"
        "<meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        f"<meta name=\"theme-color\" content=\"#f8f6fc\">"
        f"{robots}"
        f"<link rel=\"icon\" href=\"/favicon.svg\">"
        f"<meta name=\"description\" content=\"{esc(description)}\">"
        f'<link rel="canonical" href="{esc(canonical)}">'
        f'<meta property="og:type" content="website">'
        f'<meta property="og:title" content="{esc(title)}">'
        f'<meta property="og:description" content="{esc(description)}">'
        f'<meta property="og:url" content="{esc(og_url)}">'
        f"<title>{esc(title_for_tag)}</title>"
        '<link rel="stylesheet" href="/portfolio.css">'
        '<script defer src="/portfolio.js"></script>'
        "</head><body>"
        + site_body(page, pages, theme, media_urls, media_info, site_name, preview=preview, visits=visits)
        + "</body></html>"
    )


def not_found_document(site_url: str, message: str = "This page could not be found.", site_name: str = "Hana Hamamato") -> str:
    base = site_url.rstrip("/")
    return (
        "<!doctype html><html lang=\"en\"><head>"
        "<meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        '<meta name="robots" content="noindex, nofollow">'
        '<link rel="icon" href="/favicon.svg">'
        f"<title>Not found — {esc(site_name)}</title>"
        '<link rel="stylesheet" href="/portfolio.css">'
        "</head><body style=\"display:grid;place-items:center;min-height:100vh;background:var(--site-bg,#f8f6fc);"
        "font-family:'Manrope',Arial,sans-serif;color:#29233a;margin:0\">"
        '<div style="text-align:center;padding:24px">'
        '<div style="font:italic 44px \'Instrument Serif\',Georgia,serif;color:#7956c4;margin-bottom:10px">h<span style="color:#b993ed">.</span></div>'
        f"<h1 style=\"font-size:22px;margin:0 0 8px\">404</h1>"
        f"<p style=\"color:#786f88;font-size:14px;margin:0 0 22px\">{esc(message)}</p>"
        f'<a href="/" style="color:#7956c4;font-weight:700;text-decoration:none;font-size:14px">\u2190 Back to home</a>'
        "</div></body></html>"
    )


def robots_txt(site_url: str) -> str:
    base = site_url.rstrip("/")
    return (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /adminpanel\n"
        "Disallow: /api/admin\n"
        "Disallow: /api/auth\n"
        f"Sitemap: {base}/sitemap.xml\n"
    )


def sitemap_xml(pages: list[dict[str, Any]], site_url: str) -> str:
    """Only pages that are actually linked: home plus every visible page.

    Pages hidden from the navigation keep working through their direct URL,
    but advertising them in the sitemap would defeat the point of hiding.
    """
    base = site_url.rstrip("/")
    listed = [p for p in pages if p.get("id") == "home" or p.get("visible")]
    entries = "".join(f"<url><loc>{esc(base + page_path(p))}</loc></url>" for p in listed)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"{entries}</urlset>"
    )
