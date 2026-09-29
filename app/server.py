"""The HTTP server: routing, public pages, static assets, and the admin API.

Single process, standard library only. Run with ``python main.py``.
"""
from __future__ import annotations

import gzip
import json
import re
import traceback
import uuid
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from . import admin_html, backup, db as dbmod, engagement, render
from .config import Config
from .db import get_db, loads, utcnow
from .media import process_upload
from .security import (
    AuthError,
    SESSION_COOKIE,
    attempt_login,
    check_origin,
    create_challenge,
    has_session,
    read_json_body,
    remove_session,
)
from .store import (
    AppError,
    get_site,
    get_versions,
    is_media_in_use,
    is_media_published,
    publish_draft,
    referenced_media,
    restore_version,
    save_draft,
)
from .validation import ValidationError, parse_state_input

UUID_PARAM_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f-]{27,36}$", re.IGNORECASE)
SLUG_RE = re.compile(r"^[A-Za-z0-9._-]+$")

# Anything text-shaped is worth gzipping once it is big enough that the
# compression beats the header overhead.
COMPRESSIBLE = ("text/", "application/json", "application/xml", "image/svg+xml", "application/javascript")
GZIP_MIN_BYTES = 900
# How much of an over-sized upload to swallow so the 413 can be delivered.
DRAIN_LIMIT = 16 * 1024 * 1024

# Sent with every public HTML page. The page carries a live visit count, so
# it must not be cached. No X-Frame-Options / frame-ancestors on purpose:
# the studio preview and hosting panels legitimately embed the site.
PAGE_HEADERS = {
    "Cache-Control": "no-store",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-Content-Type-Options": "nosniff",
}

STATIC_MIME = {
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".txt": "text/plain; charset=utf-8",
    ".xml": "application/xml; charset=utf-8",
}


class Context:
    """Everything a handler needs for one request."""

    def __init__(self, handler: "Handler", path: str, query: dict[str, list[str]]):
        self.handler = handler
        self.path = path
        self.query = query
        self.config: Config = handler.cfg
        self.db_path = self.config.database_path
        self.headers = {k.lower(): v for k, v in handler.headers.items()}
        try:
            self.client_ip: str = handler.client_address[0]
        except Exception:  # pragma: no cover - defensive
            self.client_ip = ""

    @property
    def cookies(self) -> dict[str, str]:
        raw = self.headers.get("cookie", "")
        jar: dict[str, str] = {}
        cookie = SimpleCookie()
        try:
            cookie.load(raw)
            for key, morsel in cookie.items():
                jar[key] = morsel.value
        except Exception:
            pass
        return jar

    def session_token(self) -> str | None:
        return self.cookies.get(SESSION_COOKIE)

    def is_admin(self) -> bool:
        return has_session(get_db(self.db_path), self.session_token())


def iso_datetime(value: str | None) -> str | None:
    """SQLite UTC strings -> ISO-8601 for JSON (JS Date-friendly)."""
    if not value:
        return None
    parsed = dbmod.parse_dt(value)
    return parsed.isoformat().replace("+00:00", "Z") if parsed else value


class Handler(BaseHTTPRequestHandler):
    cfg: Config = None  # type: ignore[assignment]
    protocol_version = "HTTP/1.1"
    server_version = "HanaPortfolio/1.0"

    # ---------- low-level helpers ----------
    def log_message(self, fmt: str, *args: Any) -> None:
        print("%s - %s" % (self.address_string(), fmt % args), flush=True)

    def _read_body(self, max_bytes: int) -> bytes:
        raw_length = self.headers.get("Content-Length")
        try:
            length = int(raw_length or 0)
        except ValueError:
            length = 0
        if length > max_bytes:
            # Read and throw away a slightly-too-big upload (a 12 MB photo,
            # say) so the caller can actually read the friendly 413 instead
            # of a broken pipe. Anything wildly oversized is just dropped.
            if length <= max_bytes + DRAIN_LIMIT:
                remaining = length
                while remaining > 0:
                    chunk = self.rfile.read(min(65536, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
            else:
                self.close_connection = True
            raise AppError("That file is too big. Uploads are limited to 10 MB.", 413)
        if length <= 0:
            return b""
        data = self.rfile.read(length)
        self._consumed_body += len(data)
        return data

    def _accepts_gzip(self) -> bool:
        return "gzip" in (self.headers.get("Accept-Encoding") or "").lower()

    def _send(self, status: int, body: bytes | str = b"", content_type: str = "text/html; charset=utf-8", extra: dict[str, str] | None = None, head_only: bool = False) -> None:
        payload = body.encode("utf-8") if isinstance(body, str) else body
        headers = dict(extra or {})
        # HTML, CSS, JS and JSON compress to roughly a quarter of their size.
        # Media is already compressed, so it is left alone.
        if any(content_type.startswith(prefix) for prefix in COMPRESSIBLE):
            headers["Vary"] = "Accept-Encoding" if "Vary" not in headers else f"{headers['Vary']}, Accept-Encoding"
            if len(payload) >= GZIP_MIN_BYTES and self._accepts_gzip():
                payload = gzip.compress(payload, 6)
                headers["Content-Encoding"] = "gzip"
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        for key, value in headers.items():
            self.send_header(key, value)
        self.end_headers()
        if not head_only:
            self.wfile.write(payload)

    def _send_json(self, status: int, data: Any, extra: dict[str, str] | None = None, head_only: bool = False) -> None:
        headers = {"Cache-Control": "no-store"}
        headers.update(extra or {})
        self._send(status, json.dumps(data, ensure_ascii=False), "application/json; charset=utf-8", headers, head_only)

    def _send_html(self, status: int, html: str, extra: dict[str, str] | None = None, head_only: bool = False) -> None:
        headers = {"Cache-Control": "no-store"}
        headers.update(extra or {})
        self._send(status, html, "text/html; charset=utf-8", headers, head_only)

    def _cookie_secure_for_request(self) -> bool:
        mode = self.cfg.cookie_secure
        if mode == "on":
            return True
        if mode == "off":
            return False
        # "auto": only mark the cookie Secure when this request actually
        # arrived over HTTPS. A Secure cookie set over plain http is
        # silently dropped by browsers and breaks sign-in after reload.
        if self.cfg.trust_proxy:
            proto = (self.headers.get("X-Forwarded-Proto") or "").split(",")[0].strip().lower()
            if proto == "https":
                return True
        return False  # this process serves plain http directly

    def _set_session_cookie(self, token: str) -> None:
        parts = [
            f"{SESSION_COOKIE}={token}",
            "Path=/",
            "HttpOnly",
            "SameSite=Strict",
            f"Max-Age={12 * 60 * 60}",
        ]
        if self._cookie_secure_for_request():
            parts.append("Secure")
        self.send_header("Set-Cookie", "; ".join(parts))

    def _clear_session_cookie(self) -> None:
        parts = [f"{SESSION_COOKIE}=", "Path=/", "HttpOnly", "SameSite=Strict", "Max-Age=0"]
        if self._cookie_secure_for_request():
            parts.append("Secure")
        self.send_header("Set-Cookie", "; ".join(parts))

    # ---------- dispatch ----------
    def _dispatch(self, method: str) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = {k: v for k, v in parse_qs(parsed.query).items()}
        try:
            self._declared_body = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            self._declared_body = 0
        self._consumed_body = 0
        try:
            ctx = Context(self, path, query)
            self._route(method, ctx)
        except (AppError, AuthError, ValidationError) as error:
            status = getattr(error, "status", 400)
            if status in (400, 403, 404):
                self._send_html(status, render.not_found_document(self.cfg.site_url, error.message, site_name=self.cfg.site_name))
            else:
                self._send_json(status, {"error": error.message})
        except Exception:
            traceback.print_exc()
            self._send_json(500, {"error": "Something went wrong. Please try again."})
        finally:
            # If a request body was declared but not fully read, the leftover
            # bytes would corrupt the next request on this keep-alive socket.
            if self._consumed_body < self._declared_body:
                self.close_connection = True

    def do_GET(self) -> None:  # noqa: N802
        self._dispatch("GET")

    def do_HEAD(self) -> None:  # noqa: N802
        self._dispatch("HEAD")

    def do_POST(self) -> None:  # noqa: N802
        self._dispatch("POST")

    def do_PUT(self) -> None:  # noqa: N802
        self._dispatch("PUT")

    def do_PATCH(self) -> None:  # noqa: N802
        self._dispatch("PATCH")

    def do_DELETE(self) -> None:  # noqa: N802
        self._dispatch("DELETE")

    # ---------- routing ----------
    def _route(self, method: str, ctx: Context) -> None:
        path = ctx.path
        cfg = ctx.config
        head_only = method == "HEAD"

        if path in ("/", ""):
            return self._public_page(ctx, "")
        if path.startswith("/api/"):
            return self._api(method, ctx)
        if path == "/adminpanel" or path == "/adminpanel/":
            return self._adminpanel(ctx)
        if path.startswith("/adminpanel/preview"):
            return self._adminpanel_preview(ctx)
        if path in ("/portfolio.css", "/portfolio.js", "/favicon.svg", "/admin.css", "/admin.js"):
            return self._static_file(ctx, path, head_only)
        if path == "/robots.txt":
            return self._send(200, render.robots_txt(cfg.site_url), "text/plain; charset=utf-8", {"Cache-Control": "public, max-age=3600"}, head_only)
        if path == "/sitemap.xml":
            state = get_site(ctx.db_path)
            return self._send(200, render.sitemap_xml(state["publishedPages"], cfg.site_url), "application/xml; charset=utf-8", {"Cache-Control": "public, max-age=3600"}, head_only)
        if len(path.strip("/").split("/")) == 1 and SLUG_RE.match(path.strip("/")):
            return self._public_page(ctx, path.strip("/"))
        return self._send(404, render.not_found_document(cfg.site_url, site_name=cfg.site_name), head_only=head_only)

    # ---------- public site ----------
    def _public_page(self, ctx: Context, slug: str) -> None:
        state = get_site(ctx.db_path)
        pages = state["publishedPages"]
        theme = state["publishedTheme"]
        if slug == "":
            page = next((p for p in pages if p.get("id") == "home"), None)
        else:
            page = next((p for p in pages if p.get("slug") == slug and p.get("id") != "home"), None)
        if page is None:
            return self._send(404, render.not_found_document(ctx.config.site_url, site_name=ctx.config.site_name))
        media_info = _get_media_info(ctx, pages)
        media_urls = {mid: f"/api/media/{mid}" for mid in referenced_media(pages)}
        # Count the visit before rendering so the number a visitor sees
        # already includes their own arrival. HEAD requests never count.
        if self.command == "GET":
            try:
                engagement.record_visit(ctx.db_path, "/" + slug if slug else "/", ctx.headers, ctx.client_ip)
            except Exception:  # pragma: no cover - counting must never break a page
                traceback.print_exc()
        html = render.public_document(page, pages, theme, media_urls, media_info, ctx.config.site_url,
                                     site_name=ctx.config.site_name, site_description=ctx.config.site_description,
                                     visits=engagement.visit_total(ctx.db_path))
        self._send(200, html, extra=PAGE_HEADERS, head_only=self.command == "HEAD")

    # ---------- admin pages ----------
    def _adminpanel(self, ctx: Context) -> None:
        if ctx.is_admin():
            return self._send(200, admin_html.studio_loading_page())
        return self._send(200, admin_html.login_page(ctx.config.site_name))

    def _adminpanel_preview(self, ctx: Context) -> None:
        if not ctx.is_admin():
            return self._send(307, b"", extra={"Location": "/adminpanel"})
        state = get_site(ctx.db_path)
        slug = (ctx.query.get("slug") or [""])[0]
        page = next((p for p in state["draftPages"] if p.get("slug") == slug), None)
        if page is None:
            return self._send(404, render.not_found_document(ctx.config.site_url, site_name=ctx.config.site_name))
        media_info = _get_media_info(ctx, state["draftPages"])
        media_urls = {mid: f"/api/media/{mid}" for mid in referenced_media(state["draftPages"])}
        html = render.public_document(
            page, state["draftPages"], state["draftTheme"], media_urls, media_info,
            ctx.config.site_url, preview=True,
            site_name=ctx.config.site_name, site_description=ctx.config.site_description,
            visits=engagement.visit_total(ctx.db_path),
        )
        self._send(200, html, extra=PAGE_HEADERS)

    # ---------- static assets ----------
    def _static_file(self, ctx: Context, path: str, head_only: bool) -> None:
        name = path.lstrip("/")
        if "/" in name or name.startswith("."):
            return self._send(404, render.not_found_document(ctx.config.site_url, site_name=ctx.config.site_name))
        target: Path = ctx.config.root / "static" / name
        if not target.is_file():
            return self._send(404, render.not_found_document(ctx.config.site_url, site_name=ctx.config.site_name))
        data = target.read_bytes()
        content_type = STATIC_MIME.get(target.suffix, "application/octet-stream")
        # JS/CSS are never cached: the site is deployed by re-uploading files,
        # so a stale copy would hide the next fix for up to an hour.
        cache = "no-cache" if target.suffix in (".js", ".css") else "public, max-age=3600"
        self._send(200, data, content_type, {"Cache-Control": cache}, head_only)

    # ---------- API ----------
    def _api(self, method: str, ctx: Context) -> None:
        path = ctx.path
        db_path = ctx.db_path
        head_only = method == "HEAD"

        if path == "/api/health":
            if method not in ("GET", "HEAD"):
                return self._method_not_allowed()
            try:
                get_db(db_path).execute("SELECT 1").fetchone()
                return self._send_json(200, {"ok": True}, head_only=head_only)
            except Exception:
                return self._send_json(500, {"ok": False}, head_only=head_only)

        if path == "/api/auth/captcha":
            if method not in ("GET", "HEAD"):
                return self._method_not_allowed()
            try:
                return self._send_json(200, create_challenge(ctx.headers, ctx.config.trust_proxy, db_path, ctx.client_ip),
                                       head_only=head_only)
            except (AuthError, AppError) as error:
                return self._send_json(error.status, {"error": error.message}, head_only=head_only)

        if path == "/api/auth/login":
            if method != "POST":
                return self._method_not_allowed()
            try:
                check_origin(ctx.headers, ctx.config.site_url)
                payload = read_json_body(self._read_body(3000), 3000)
                if not isinstance(payload, dict):
                    raise AuthError("The passwords or challenge didn't match. Please try again.", 401)
                passwords = payload.get("passwords")
                challenge_id = payload.get("challengeId")
                answer = payload.get("answer")
                if (
                    not isinstance(passwords, list) or len(passwords) != 3
                    or not all(isinstance(p, str) and len(p) <= 256 for p in passwords)
                    or not isinstance(challenge_id, str) or not re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", challenge_id, re.IGNORECASE)
                    or not isinstance(answer, str) or len(answer) > 20
                ):
                    raise AuthError("The passwords or challenge didn't match. Please try again.", 401)
                token = attempt_login(ctx.headers, db_path, ctx.config.trust_proxy, passwords, challenge_id, answer,
                                      ctx.client_ip)
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self._set_session_cookie(token)
                body = b'{"ok":true}'
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except (AuthError, AppError) as error:
                return self._send_json(error.status, {"error": error.message})
            return None

        if path == "/api/auth/logout":
            if method != "POST":
                return self._method_not_allowed()
            try:
                check_origin(ctx.headers, ctx.config.site_url)
                remove_session(get_db(db_path), ctx.session_token())
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self._clear_session_cookie()
                body = b'{"ok":true}'
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except (AuthError, AppError) as error:
                return self._send_json(error.status, {"error": error.message})
            return None

        if path == "/api/messages":
            if method != "POST":
                return self._method_not_allowed()
            try:
                check_origin(ctx.headers, ctx.config.site_url)
                payload = read_json_body(self._read_body(20_000), 20_000)
                if not isinstance(payload, dict):
                    raise AppError(f"Please write at least {engagement.BODY_MIN} characters.")
                engagement.add_message(
                    db_path, payload.get("name", ""), payload.get("body", ""), ctx.headers, ctx.client_ip
                )
                return self._send_json(201, {"ok": True})
            except (AppError, AuthError, ValidationError) as error:
                return self._send_json(error.status, {"error": error.message})

        if path == "/api/admin/messages":
            return self._admin_messages(method, ctx)
        match = re.fullmatch(r"/api/admin/messages/(\d{1,18})", path)
        if match:
            return self._admin_message_id(method, ctx, int(match.group(1)))
        if path == "/api/admin/visits":
            return self._admin_visits(method, ctx)
        if path == "/api/admin/state":
            return self._admin_state(method, ctx)
        if path == "/api/admin/publish":
            return self._admin_publish(method, ctx)
        if path == "/api/admin/history":
            return self._admin_history(method, ctx)
        if path == "/api/admin/media":
            return self._admin_media(method, ctx)
        match = re.fullmatch(r"/api/admin/media/([0-9a-f-]+)", path)
        if match:
            return self._admin_media_id(method, ctx, match.group(1))
        match = re.fullmatch(r"/api/media/([0-9a-f-]+)", path)
        if match:
            return self._public_media(method, ctx, match.group(1))

        return self._send_json(404, {"error": "Not found."})

    def _method_not_allowed(self) -> None:
        self._send_json(405, {"error": "Method not allowed."})

    def _require_admin(self, ctx: Context, mutation: bool) -> None:
        if mutation:
            check_origin(ctx.headers, ctx.config.site_url)
        if not ctx.is_admin():
            raise AuthError("Your session has expired. Sign in again.", 401)

    def _admin_state(self, method: str, ctx: Context) -> None:
        if method not in ("GET", "HEAD", "PUT"):
            return self._method_not_allowed()
        head_only = method == "HEAD"
        try:
            self._require_admin(ctx, method == "PUT")
            if method == "GET":
                state = get_site(ctx.db_path)
                return self._send_json(
                    200,
                    {
                        "revision": state["revision"],
                        "pages": state["draftPages"],
                        "theme": state["draftTheme"],
                        "publishedAt": iso_datetime(state.get("published_at")),
                        "publishedPages": state["publishedPages"],
                    },
                    head_only=head_only,
                )
            payload = read_json_body(self._read_body(300_000), 300_000)
            revision, pages, theme = parse_state_input(payload)
            new_revision = save_draft(ctx.db_path, pages, theme, revision)
            return self._send_json(200, {"revision": new_revision, "message": "Draft saved."})
        except (AppError, AuthError, ValidationError) as error:
            return self._send_json(error.status, {"error": error.message})

    def _admin_publish(self, method: str, ctx: Context) -> None:
        if method != "POST":
            return self._method_not_allowed()
        try:
            self._require_admin(ctx, True)
            payload = read_json_body(self._read_body(2000), 2000)
            revision = payload.get("revision") if isinstance(payload, dict) else None
            if not isinstance(revision, int) or isinstance(revision, bool) or revision < 0:
                raise ValidationError("The draft revision is invalid.")
            published = publish_draft(ctx.db_path, revision)
            return self._send_json(
                200,
                {
                    "ok": True,
                    "revision": published["revision"],
                    "publishedAt": published["publishedAt"],
                },
            )
        except (AppError, AuthError, ValidationError) as error:
            return self._send_json(error.status, {"error": error.message})

    def _admin_history(self, method: str, ctx: Context) -> None:
        if method not in ("GET", "HEAD", "POST"):
            return self._method_not_allowed()
        head_only = method == "HEAD"
        try:
            self._require_admin(ctx, method == "POST")
            if method == "GET":
                versions = [
                    {"id": v["id"], "publishedAt": iso_datetime(v["publishedAt"]), "pageCount": len(v["pages"])}
                    for v in get_versions(ctx.db_path)
                ]
                return self._send_json(200, {"versions": versions}, head_only=head_only)
            payload = read_json_body(self._read_body(2000), 2000)
            version_id = payload.get("id") if isinstance(payload, dict) else None
            revision = payload.get("revision") if isinstance(payload, dict) else None
            if not isinstance(version_id, int) or isinstance(version_id, bool) or version_id < 1:
                raise ValidationError("That version no longer exists.")
            if not isinstance(revision, int) or isinstance(revision, bool) or revision < 0:
                raise ValidationError("The draft revision is invalid.")
            result = restore_version(ctx.db_path, version_id, revision)
            return self._send_json(200, result)
        except (AppError, AuthError, ValidationError) as error:
            return self._send_json(error.status, {"error": error.message})

    def _admin_messages(self, method: str, ctx: Context) -> None:
        if method not in ("GET", "HEAD"):
            return self._method_not_allowed()
        try:
            self._require_admin(ctx, False)
            messages = engagement.list_messages(ctx.db_path)
            return self._send_json(
                200,
                {
                    "messages": [{**m, "createdAt": iso_datetime(m["createdAt"])} for m in messages],
                    "unread": sum(1 for m in messages if not m["read"]),
                },
                head_only=method == "HEAD",
            )
        except (AppError, AuthError, ValidationError) as error:
            return self._send_json(error.status, {"error": error.message})

    def _admin_message_id(self, method: str, ctx: Context, message_id: int) -> None:
        if method not in ("PATCH", "DELETE"):
            return self._method_not_allowed()
        try:
            self._require_admin(ctx, True)
            if method == "DELETE":
                engagement.delete_message(ctx.db_path, message_id)
                return self._send_json(200, {"ok": True})
            payload = read_json_body(self._read_body(2000), 2000)
            read = payload.get("read") if isinstance(payload, dict) else None
            if not isinstance(read, bool):
                raise ValidationError("Choose whether the message is read.")
            engagement.set_message_read(ctx.db_path, message_id, read)
            return self._send_json(200, {"ok": True, "id": message_id, "read": read})
        except (AppError, AuthError, ValidationError) as error:
            return self._send_json(error.status, {"error": error.message})

    def _admin_visits(self, method: str, ctx: Context) -> None:
        if method not in ("GET", "HEAD", "PUT"):
            return self._method_not_allowed()
        try:
            self._require_admin(ctx, method == "PUT")
            state = get_site(ctx.db_path)
            known = list(state["publishedPages"]) + list(state["draftPages"])
            if method == "PUT":
                payload = read_json_body(self._read_body(2000), 2000)
                total = payload.get("displayedTotal") if isinstance(payload, dict) else None
                return self._send_json(200, _visit_payload(engagement.set_displayed_total(ctx.db_path, total, known)))
            return self._send_json(
                200, _visit_payload(engagement.visit_stats(ctx.db_path, known)), head_only=method == "HEAD"
            )
        except (AppError, AuthError, ValidationError) as error:
            return self._send_json(error.status, {"error": error.message})

    def _admin_media(self, method: str, ctx: Context) -> None:
        if method not in ("GET", "HEAD", "POST"):
            return self._method_not_allowed()
        head_only = method == "HEAD"
        try:
            self._require_admin(ctx, method == "POST")
            conn = get_db(ctx.db_path)
            if method == "GET":
                rows = conn.execute(
                    """SELECT id, name, mime, kind, bytes, created_at, width, height FROM media_assets
                       WHERE deleted_at IS NULL ORDER BY created_at DESC, id DESC"""
                ).fetchall()
                files = [
                    {
                        "id": row["id"], "name": row["name"], "mime": row["mime"],
                        "kind": row["kind"], "bytes": row["bytes"],
                        "createdAt": iso_datetime(row["created_at"]),
                        "width": row["width"], "height": row["height"],
                    }
                    for row in rows
                ]
                return self._send_json(200, {"files": files}, head_only=head_only)
            body = self._read_body(11 * 1024 * 1024)
            fields, files = parse_multipart(body, self.headers.get("Content-Type", ""))
            file = files.get("file")
            if not file:
                raise AppError("Choose a file to upload.")
            filename, data = file
            processed = process_upload(filename, data)
            asset_id = str(uuid.uuid4())
            now = utcnow()
            with conn:
                conn.execute(
                    """INSERT INTO media_assets (id, name, mime, kind, bytes, data, created_at, width, height)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (asset_id, processed["name"], processed["mime"], processed["kind"],
                     processed["bytes"], processed["data"], now, processed.get("width"), processed.get("height")),
                )
            saved = {
                "id": asset_id, "name": processed["name"], "mime": processed["mime"],
                "kind": processed["kind"], "bytes": processed["bytes"], "createdAt": iso_datetime(now),
                "width": processed.get("width"), "height": processed.get("height"),
            }
            return self._send_json(201, {"file": saved})
        except (AppError, AuthError, ValidationError) as error:
            return self._send_json(error.status, {"error": error.message})

    def _admin_media_id(self, method: str, ctx: Context, asset_id: str) -> None:
        if method not in ("PATCH", "PUT", "DELETE"):
            return self._method_not_allowed()
        try:
            self._require_admin(ctx, True)
            conn = get_db(ctx.db_path)
            if method == "PATCH":
                payload = read_json_body(self._read_body(2000), 2000)
                name = payload.get("name") if isinstance(payload, dict) else None
                revision = payload.get("revision") if isinstance(payload, dict) else None
                if not isinstance(name, str) or not name.strip() or len(name) > 110:
                    raise ValidationError("Give the file a name (1-110 characters).")
                if not isinstance(revision, int) or isinstance(revision, bool) or revision < 0:
                    raise AppError("Choose a file and reload the draft.")
                from .media import clean_name
                return self._send_json(200, _create_replacement(ctx, asset_id, revision, {"name": clean_name(name)}))
            if method == "PUT":
                body = self._read_body(11 * 1024 * 1024)
                fields, files = parse_multipart(body, self.headers.get("Content-Type", ""))
                file = files.get("file")
                if not file:
                    raise AppError("Choose a file and reload the draft.")
                filename, data = file
                raw_revision = fields.get("revision", [None])[0]
                if raw_revision is None or not raw_revision.lstrip("-").isdigit() or int(raw_revision) < 0:
                    raise AppError("Choose a file and reload the draft.")
                processed = process_upload(filename, data)
                return self._send_json(200, _create_replacement(ctx, asset_id, int(raw_revision), processed))
            if is_media_in_use(ctx.db_path, asset_id):
                raise AppError(
                    "This upload is used by a draft, published page, or saved version. Remove those references before deleting it.",
                    409,
                )
            now = utcnow()
            with conn:
                cursor = conn.execute(
                    "UPDATE media_assets SET deleted_at = ? WHERE id = ? AND deleted_at IS NULL",
                    (now, asset_id),
                )
            if cursor.rowcount == 0:
                raise AppError("Upload not found.", 404)
            return self._send_json(200, {"ok": True})
        except (AppError, AuthError, ValidationError) as error:
            return self._send_json(error.status, {"error": error.message})

    def _public_media(self, method: str, ctx: Context, asset_id: str) -> None:
        if method not in ("GET", "HEAD"):
            return self._method_not_allowed()
        head_only = method == "HEAD"
        if not UUID_PARAM_RE.match(asset_id):
            return self._send(404, "Not found", "text/plain; charset=utf-8", head_only=head_only)
        conn = get_db(ctx.db_path)
        row = conn.execute("SELECT * FROM media_assets WHERE id = ?", (asset_id,)).fetchone()
        if not row:
            return self._send(404, "Not found", "text/plain; charset=utf-8", head_only=head_only)
        published = is_media_published(ctx.db_path, asset_id)
        if not published and (not has_session(conn, ctx.session_token()) or row["deleted_at"]):
            return self._send(404, "Not found", "text/plain; charset=utf-8", head_only=head_only)
        safe_name = re.sub(r'[\r\n"\\]', "_", row["name"])
        disposition = "attachment" if row["kind"] == "file" else "inline"
        # An asset id never changes content: renaming or replacing an upload
        # mints a new id (copy-on-write). So the id is a content address and
        # the bytes can be cached hard, with an ETag for the revalidation.
        etag = f'"{asset_id}-{row["bytes"]}"'
        headers = {
            # No Content-Length here: _send() sets it from the payload. Sending
            # it twice makes strict proxies reject the response.
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": f'{disposition}; filename="{safe_name}"; filename*=UTF-8\'\'{quote_asset_name(row["name"])}',
            "Cache-Control": "public, max-age=31536000, immutable" if published else "private, no-store",
            "ETag": etag,
        }
        if row["kind"] == "file":
            headers["Content-Security-Policy"] = "sandbox"
        if published and _etag_matches(ctx.headers.get("if-none-match"), etag):
            return self._send(304, b"", row["mime"], headers, head_only=True)
        self._send(200, bytes(row["data"]), row["mime"], headers, head_only)


def quote_asset_name(name: str) -> str:
    from urllib.parse import quote
    return quote(name, safe="")


def _etag_matches(header: str | None, etag: str) -> bool:
    """True when the browser already holds this exact version."""
    if not header:
        return False
    if header.strip() == "*":
        return True
    for candidate in header.split(","):
        candidate = candidate.strip()
        if candidate.startswith("W/"):
            candidate = candidate[2:].strip()
        if candidate == etag:
            return True
    return False


def _visit_payload(stats: dict[str, Any]) -> dict[str, Any]:
    """Same statistics with JS-friendly timestamps."""
    return {**stats, "pages": [{**row, "lastAt": iso_datetime(row.get("lastAt"))} for row in stats.get("pages", [])]}


def _get_media_info(ctx: Context, pages: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    ids = referenced_media(pages)
    if not ids:
        return {}
    conn = get_db(ctx.db_path)
    placeholders = ",".join("?" * len(ids))
    rows = conn.execute(
        f"SELECT id, name, kind, mime, width, height FROM media_assets WHERE id IN ({placeholders})", ids
    ).fetchall()
    return {
        row["id"]: {"name": row["name"], "kind": row["kind"], "mime": row["mime"],
                    "width": row["width"], "height": row["height"]}
        for row in rows
    }


def _create_replacement(ctx: Context, asset_id: str, revision: int, replacement: dict[str, Any]) -> dict[str, Any]:
    conn = get_db(ctx.db_path)
    with conn:
        state_row = conn.execute("SELECT * FROM site_state WHERE id = 1").fetchone()
        old = conn.execute("SELECT * FROM media_assets WHERE id = ?", (asset_id,)).fetchone()
        if not old or old["deleted_at"]:
            raise AppError("This upload no longer exists.", 404)
        if state_row["revision"] != revision:
            raise AppError("Your draft changed elsewhere. Reload and try again.", 409)
        if replacement.get("kind") and replacement["kind"] != old["kind"]:
            raise AppError("Replace this upload with the same kind of file.")
        new_id = str(uuid.uuid4())
        new_name = replacement.get("name") or old["name"]
        new_mime = replacement.get("mime") or old["mime"]
        new_data = replacement.get("data") if replacement.get("data") is not None else old["data"]
        new_bytes = replacement.get("bytes") if replacement.get("bytes") is not None else len(old["data"])
        conn.execute(
            """INSERT INTO media_assets (id, name, mime, kind, bytes, data, created_at, width, height)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (new_id, new_name, new_mime, old["kind"], new_bytes, new_data, utcnow(),
             replacement.get("width", old["width"]), replacement.get("height", old["height"])),
        )
        pages = loads(state_row["draft_pages"], [])
        pages = [
            {
                **page,
                "blocks": [
                    {**block, "mediaId": new_id} if block.get("mediaId") == asset_id else block
                    for block in page.get("blocks", [])
                ],
            }
            for page in pages
        ]
        conn.execute(
            "UPDATE site_state SET draft_pages = ?, revision = ?, updated_at = ? WHERE id = 1",
            (dbmod.dumps(pages), revision + 1, utcnow()),
        )
        file_row = {
            "id": new_id, "name": new_name, "mime": new_mime, "kind": old["kind"],
            "bytes": new_bytes, "createdAt": iso_datetime(utcnow()),
            "width": replacement.get("width", old["width"]), "height": replacement.get("height", old["height"]),
        }
    return {"file": file_row, "pages": pages, "revision": revision + 1}


def parse_multipart(body: bytes, content_type: str) -> tuple[dict[str, list[str]], dict[str, tuple[str, bytes]]]:
    """Minimal multipart/form-data parser (fields + files).

    Strips exactly the protocol CRLFs around each part so binary content
    that begins or ends with CR/LF bytes is preserved untouched.
    """
    match = re.search(r'boundary=(?:"([^"]+)"|([^;]+))', content_type or "", re.IGNORECASE)
    if not match:
        return {}, {}
    boundary = ("--" + (match.group(1) or match.group(2).strip())).encode("latin-1")
    fields: dict[str, list[str]] = {}
    files: dict[str, tuple[str, bytes]] = {}
    for part in body.split(boundary):
        if part.startswith(b"\r\n"):
            part = part[2:]
        if part.endswith(b"\r\n"):
            part = part[:-2]
        if part in (b"", b"--"):
            continue
        if b"\r\n\r\n" not in part:
            continue
        header_block, content = part.split(b"\r\n\r\n", 1)
        headers = header_block.decode("latin-1", "replace")
        name_match = re.search(r'name="([^"]*)"', headers)
        if not name_match:
            continue
        field_name = name_match.group(1)
        filename_match = re.search(r'filename="([^"]*)"', headers)
        if filename_match is not None:
            filename = filename_match.group(1).split("/")[-1] or "upload"
            files[field_name] = (filename, content)
        else:
            fields.setdefault(field_name, []).append(content.decode("utf-8", "replace"))
    return fields, files


def serve(cfg: Config) -> None:
    Handler.cfg = cfg
    get_db(cfg.database_path)  # create the database and schema before serving
    print(f"Database: {cfg.database_path} (ready)", flush=True)
    backup.start(cfg.database_path)
    server = ThreadingHTTPServer((cfg.host, cfg.port), Handler)
    server.daemon_threads = True
    print(f"Hana portfolio studio is running at http://{cfg.host}:{cfg.port}", flush=True)
    print(f"Public origin (SITE_URL): {cfg.site_url}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
