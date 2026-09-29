"""Admin HTML shells: the sign-in page and the studio loading screen.

The studio itself is rendered by static/admin.js after it fetches the
workspace state — exactly like the original client component, which also
served only a loading screen server-side.
"""
from __future__ import annotations

from .render import esc, icon


def _head(title: str, description: str = "") -> str:
    description_tag = f'<meta name="description" content="{esc(description)}">' if description else ""
    return (
        "<!doctype html><html lang=\"en\"><head><!-- admin-build: 2026-09-26-5 -->"
        "<meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        '<meta name="robots" content="noindex, nofollow">'
        '<link rel="icon" href="/favicon.svg">'
        f"{description_tag}"
        f"<title>{esc(title)}</title>"
        '<link rel="stylesheet" href="/portfolio.css">'
        '<link rel="stylesheet" href="/admin.css">'
        "</head>"
    )


def login_page(site_name: str = "Hana Hamamato") -> str:
    password_fields = ""
    for index in range(3):
        password_fields += (
            f'<label class="login-field"><span><b>0{index + 1}</b> Password {index + 1}</span>'
            f'<input type="password" data-pw="{index}" placeholder="Enter password" '
            f'autocomplete="new-password" required maxlength="256"></label>'
        )
    return (
        _head("Private Studio — Hana")
        + "<body>"
        '<main class="login-page" id="login-app">'
        '<div class="login-story"><div class="login-story-top">'
        '<span class="login-story-logo">h<span>.</span></span><span>PRIVATE SPACE</span></div>'
        '<div class="login-story-center"><div class="story-art" aria-hidden="true">'
        # A non-void element must be closed: `<div ... />` is ignored by the
        # HTML parser, which kept this div open and pulled the whole sign-in
        # form inside the story panel instead of the second grid column.
        '<div class="story-art-ring"></div><div class="story-art-card"><span>h.</span>'
        '<span class="story-art-flower">\u2733</span></div>'
        '<span class="story-art-star">\u2726</span></div></div></div>'
        '<div class="login-form-side"><div class="login-form-wrap">'
        f'<div class="login-icon">{icon("lock-keyhole", 21, 1.8)}</div>'
        '<span class="admin-eyebrow">PRIVATE WORKSPACE</span>'
        '<h2>Welcome back<span>.</span></h2>'
        '<form id="login-form" novalidate>'
        f'<div class="password-heading"><button type="button" id="toggle-passwords" aria-label="Show passwords">'
        f'{icon("eye", 17)} <span>Show</span></button></div>'
        f"{password_fields}"
        '<div class="captcha-heading"><span>SECURITY CHECK</span>'
        f'<button type="button" id="new-challenge" aria-label="Get a new challenge">{icon("refresh-cw", 16)} New challenge</button></div>'
        '<div class="captcha-row">'
        '<div class="captcha-image" id="captcha-image"><span>Creating challenge...</span></div>'
        '<label class="captcha-answer"><span>Answer</span>'
        '<input id="captcha-answer" inputmode="numeric" type="text" placeholder="?" autocomplete="off" maxlength="20" required></label>'
        "</div>"
        '<div id="login-error-slot"></div>'
        f'<button type="submit" class="login-submit" id="login-submit" disabled>Enter studio {icon("arrow-right", 18)}</button>'
        "</form>"
        '</div><div class="login-form-bottom"><a href="/">\u2190 Back to portfolio</a>'
        "</div></div>"
        "</main>"
        '<script src="/admin.js" defer></script>'
        "</body></html>"
    )


def studio_loading_page() -> str:
    return (
        _head("Private Studio — Hana")
        + "<body>"
        '<div class="admin-loading" id="admin-root"><span class="loading-mark">h.</span>'
        "<p>Opening your studio...</p></div>"
        '<script src="/admin.js" defer></script>'
        "</body></html>"
    )
