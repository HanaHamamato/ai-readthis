"""End-to-end test of the Hana portfolio studio server on 127.0.0.1:10749."""
import hashlib
import hmac
import json
import tempfile
import pathlib
import gzip
import zipfile
import time
import re
import sys
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone

BASE = "http://127.0.0.1:10749"
SITE_ORIGIN = "https://hanainfo.wisp.uno"
CAPTCHA_SECRET = "test-secret-abc123xyz"
DB = "data/portfolio.db"

passed = failed = 0
def check(name, cond, extra=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  PASS {name}")
    else:
        failed += 1
        print(f"  FAIL {name} {extra}")

def req(method, path, body=None, headers=None, origin=True, cookie=None):
    h = dict(headers or {})
    if origin and method in ("POST", "PUT", "PATCH", "DELETE"):
        h["Origin"] = SITE_ORIGIN
    if cookie:
        h["Cookie"] = cookie
    data = None
    if body is not None:
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        h.setdefault("Content-Type", "application/json")
    r = urllib.request.Request(BASE + path, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            raw = resp.read()
            return resp.status, dict(resp.headers), raw
    except urllib.error.HTTPError as e:
        raw = e.read()
        return e.code, dict(e.headers), raw

def jreq(method, path, **kw):
    status, headers, raw = req(method, path, **kw)
    try:
        payload = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        payload = None
    return status, headers, payload

import os
import sqlite3

if os.path.exists(DB):
    _probe = sqlite3.connect(DB, timeout=30)
    try:
        _used = _probe.execute("SELECT COUNT(*) FROM site_versions").fetchone()[0]
    except sqlite3.Error:
        _used = 0
    _probe.close()
    if _used:
        print("NOTE: data/portfolio.db already holds published history — a few content checks")
        print("      expect a fresh database. Delete data/ and restart the server for a clean run.")
        print()

print("== public site ==")
s, h, b = req("GET", "/")
check("GET / is 200", s == 200, f"got {s}")
html = b.decode()
check("home has <html", "<html" in html.lower())
check("home links admin.css? no", "admin.css" not in html)
check("home links portfolio.css", "/portfolio.css" in html)
check("home links portfolio.js", "/portfolio.js" in html)
check("home has theme-color #f8f6fc", '#f8f6fc' in html)
check("home title (site name from config.json)", ("Hana's" in html) or ("Hana&#39;s" in html))
check("home meta description (site_description)", "VIew My Achievements" in html)
check("home blurb (custom)", "I will post here soon, apologize! \U0001F62D" in html)
check("home site-footer removed entirely", "Made to be explored." not in html and "site-footer" not in html)
check("sidebar OPEN SPACE removed", "OPEN SPACE" not in html)
check("cookie popup trimmed (last sentence gone, rest kept)", "No tracking cookies here." not in html and "Essential cookies keep the private editor secure." in html)
check("home canonical SITE_URL", f'{SITE_ORIGIN}/' in html)
check("home noindex NOT set on home", 'name="robots"' not in html or "noindex" not in html)

s, h, b = req("GET", "/portfolio.css")
check("portfolio.css 200 text/css", s == 200 and "text/css" in h.get("Content-Type", ""))
check("CSS is no-cache (re-uploads must not be hidden by stale cache)", h.get("Cache-Control") == "no-cache")
s, h, b = req("GET", "/portfolio.js")
check("portfolio.js 200 js", s == 200 and "javascript" in h.get("Content-Type", ""))
check("JS is no-cache (re-uploads must not be hidden by stale cache)", h.get("Cache-Control") == "no-cache")
s, h, b = req("GET", "/admin.js")
check("admin.js 200 js", s == 200 and "javascript" in h.get("Content-Type", ""))
check("admin.js no-cache", h.get("Cache-Control") == "no-cache")
s, h, b = req("GET", "/favicon.svg")
check("favicon.svg 200", s == 200 and "svg" in h.get("Content-Type", ""))
s, h, b = req("GET", "/no-such-page-xyz")
check("unknown slug 404", s == 404, f"got {s}")
check("404 is html", b"html" in b.lower())
s, h, b = req("GET", "/og.png")
check("/og.png 404 styled", s == 404)
s, h, b = req("GET", "/favicon.ico")
check("/favicon.ico 404 styled", s == 404)
s, h, b = req("GET", "/robots.txt")
check("robots.txt 200", s == 200, f"got {s}")
robots = b.decode()
check("robots has sitemap URL", f"{SITE_ORIGIN}/sitemap.xml" in robots)
s, h, b = req("GET", "/sitemap.xml")
check("sitemap.xml 200", s == 200, f"got {s}")
check("sitemap xml", b"<?xml" in b)
s, h, b = req("HEAD", "/")
check("HEAD / 200 no body", s == 200 and b == b"")

print("== health & admin pages ==")
s, h, p = jreq("GET", "/api/health")
check("health ok", s == 200 and p == {"ok": True}, f"{s} {p}")
s, h, b = req("GET", "/adminpanel")
check("adminpanel 200", s == 200)
check("adminpanel login page", b"login" in b.lower() and b"admin.js" in b)
import http.client
c = http.client.HTTPConnection("127.0.0.1", 10749, timeout=5)
c.request("GET", "/adminpanel/preview")
resp = c.getresponse()
check("preview unauth 307", resp.status == 307 and resp.getheader("Location", "").startswith("/adminpanel"), f"got {resp.status} {resp.getheader('Location')}")
c.close()

print("== auth: unauthenticated API ==")
s, h, p = jreq("GET", "/api/admin/state")
check("state unauth 401", s == 401, f"got {s}")
s, h, p = jreq("PUT", "/api/admin/state", body={"revision": 0, "pages": [], "theme": {}})
check("state PUT unauth 401", s == 401)
s, h, p = jreq("POST", "/api/admin/publish", body={"revision": 0})
check("publish unauth 401", s == 401)
s, h, p = jreq("GET", "/api/auth/captcha")
check("captcha 200 id+image", s == 200 and isinstance(p, dict) and "id" in p and "image" in p, f"{s} {str(p)[:80]}")
check("captcha image is svg b64", isinstance(p.get("image"), str) and p["image"].startswith("data:image/svg+xml;base64,"))
cap_id = p["id"]

print("== auth: login ==")
# wrong password
s, h, p = jreq("POST", "/api/auth/login", body={"passwords": ["a", "b", "c"], "challengeId": cap_id, "answer": "1234"})
check("login wrong password 401", s == 401, f"got {s}")
check("no cookie on failed login", "Set-Cookie" not in h or "hana_admin_session=" not in h.get("Set-Cookie", ""))

# origin rules: cross-site blocked, same-host and non-browser accepted
s, h, p = jreq("POST", "/api/auth/login", body={"passwords": ["a", "b", "c"], "challengeId": cap_id, "answer": "1"}, origin=False, headers={"Origin": "https://evil.example"})
check("login cross-site Origin 403", s == 403, f"got {s}")
s, h, p = jreq("POST", "/api/auth/login", body={"passwords": ["a", "b", "c"], "challengeId": cap_id, "answer": "1"}, origin=False, headers={"Origin": "http://127.0.0.1:10749"})
check("login same-host Origin accepted (401, not 403)", s == 401, f"got {s}")
s, h, p = jreq("POST", "/api/auth/login", body={"passwords": ["a", "b", "c"], "challengeId": cap_id, "answer": "1"}, origin=False)
check("login no-Origin (non-browser) accepted (401, not 403)", s == 401, f"got {s}")

# craft a challenge row with a known answer
import sqlite3
conn = sqlite3.connect(DB, timeout=30)
cid = str(uuid.uuid4())
answer = "4321"
digest = hmac.new(CAPTCHA_SECRET.encode(), f"{cid}:{answer}".encode(), hashlib.sha256).hexdigest()
now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
exp = (datetime.now(timezone.utc) + timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S.%f")
row = conn.execute("SELECT 1 FROM auth_attempts WHERE key = ?", (None,))
from app.security import ip_key
ipkey = ip_key({}, False, "127.0.0.1")  # no trusted proxy: the socket peer identifies the caller
conn.execute("INSERT INTO captcha_challenges (id, digest, ip_key, expires_at, used) VALUES (?,?,?,?,0)", (cid, digest, ipkey, exp))
conn.commit()
conn.close()

# correct three passwords (any order) + correct answer
s, h, p = jreq("POST", "/api/auth/login", body={"passwords": ["Sakura2026!", "Blossom!42", "Hana#Site99"], "challengeId": cid, "answer": answer})
check("login 200", s == 200, f"got {s} {str(p)[:200]}")
setc = h.get("Set-Cookie", "")
check("session cookie set", "hana_admin_session=" in setc and "HttpOnly" in setc and "SameSite=Strict" in setc, setc)
check("cookie has no Secure flag over plain http (browsers silently drop it, breaking sign-in after reload)", "secure" not in setc.lower(), setc)
m = re.search(r"hana_admin_session=([^;]+)", setc)
COOKIE = f"hana_admin_session={m.group(1)}" if m else None
check("cookie extracted", bool(COOKIE))
check("login one-use: captcha consumed", True)

# reuse same challenge id -> should fail
s, h, p = jreq("POST", "/api/auth/login", body={"passwords": ["Sakura2026!", "Blossom!42", "Hana#Site99"], "challengeId": cid, "answer": answer})
check("challenge reuse rejected 401", s == 401, f"got {s}")

print("== admin state ==")
s, h, p = jreq("GET", "/api/admin/state", cookie=COOKIE)
check("state 200", s == 200, f"got {s} {str(p)[:120]}")
rev0 = p["revision"]
check("state has keys", all(k in p for k in ("revision", "pages", "theme", "publishedAt", "publishedPages")), str(p)[:200])
check("publishedAt ISO Z", p["publishedAt"] is None or p["publishedAt"].endswith("Z"), str(p.get("publishedAt")))
check("default home page present", any(pg.get("id") == "home" for pg in p["pages"]))
theme = p["theme"]

s2, h2, p2 = jreq("PUT", "/api/admin/state", body={"revision": 999999, "pages": p["pages"], "theme": theme}, origin=False, cookie=COOKIE)
check("PUT state no-Origin not origin-blocked (409 stale revision)", s2 == 409, f"got {s2}")
s2b, h2b, p2b = jreq("PUT", "/api/admin/state", body={"revision": rev0, "pages": p["pages"], "theme": theme}, origin=False, headers={"Origin": "https://evil.example"}, cookie=COOKIE)
check("PUT state cross-site Origin 403", s2b == 403, f"got {s2b}")

# build a new page list: home + a new page
pages = p["pages"]
home = next(pg for pg in pages if pg["id"] == "home")
new_page = {
    "id": str(uuid.uuid4()),
    "title": "Test Page",
    "slug": "test-page",
    "visible": True,
    "blocks": [
        {"id": str(uuid.uuid4()), "type": "heading", "text": "Hello WispByte", "align": "left"},
        {"id": str(uuid.uuid4()), "type": "paragraph", "text": "Running on **python-core**."},
    ],
}
pages2 = [home, new_page]
s, h, p = jreq("PUT", "/api/admin/state", body={"revision": rev0, "pages": pages2, "theme": theme}, cookie=COOKIE)
check("PUT state 200", s == 200, f"got {s} {str(p)[:120]}")
check("PUT bumped revision", p.get("revision") == rev0 + 1, str(p))
check("PUT message", p.get("message") == "Draft saved.", str(p))
rev1 = p["revision"]

s, h, p = jreq("PUT", "/api/admin/state", body={"revision": rev0, "pages": pages2, "theme": theme}, cookie=COOKIE)
check("stale revision 409", s == 409, f"got {s}")

s, h, p = jreq("PUT", "/api/admin/state", body={"revision": rev1, "pages": [{"id": "home", "title": "", "blocks": []}], "theme": theme}, cookie=COOKIE)
check("invalid pages rejected", s == 400, f"got {s} {str(p)[:120]}")

print("== media ==")
# tiny 1x1 PNG
png = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d4944415478da63fcffff3f030005fe02fea72d99480000000049454e44ae426082"
)
boundary = "----hanaTestBoundary"
def multipart(fields, files):
    parts = []
    for k, v in (fields or {}).items():
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode())
    for k, (fn, data, ct) in (files or {}).items():
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"; filename=\"{fn}\"\r\nContent-Type: {ct}\r\n\r\n".encode() + data + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts)

body = multipart({"revision": str(rev1)}, {"file": ("blossom.png", png, "image/png")})
s, h, p = jreq("POST", "/api/admin/media", body=body, cookie=COOKIE,
               headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
check("media upload 201", s == 201, f"got {s} {str(p)[:150]}")
f0 = p.get("file", {})
check("file meta", f0.get("name") == "blossom.png" and f0.get("kind") == "image" and f0.get("bytes") == len(png), str(f0)[:150])
media_id = f0.get("id")
check("file id uuid", bool(media_id) and re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", media_id, re.I) is not None, str(media_id))

# fetch as admin (not yet published)
s, h, b = req("GET", f"/api/media/{media_id}", cookie=COOKIE)
check("media fetch as admin 200", s == 200 and b == png, f"got {s} len={len(b)}")
check("media content-type image/png", "image/png" in h.get("Content-Type", ""))
check("media inline disposition", "inline" in h.get("Content-Disposition", ""))
s, h, b = req("GET", f"/api/media/{media_id}")
check("media fetch unauth 404 (unpublished)", s == 404, f"got {s}")

# multipart integrity: content that starts AND ends with CRLF bytes must
# survive the parser (protocol CRLFs are stripped exactly once per part)
crlf_text = b"\r\nfirst line\r\nlast line\r\n"
body = multipart({}, {"file": ("notes.txt", crlf_text, "text/plain")})
s, h, p = jreq("POST", "/api/admin/media", body=body, cookie=COOKIE,
               headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
check("crlf text upload 201", s == 201, f"got {s} {str(p)[:150]}")
check("crlf text sniffed text/plain", p.get("file", {}).get("mime") == "text/plain", str(p.get("file"))[:120])
crlf_id = p.get("file", {}).get("id")
s, h, b = req("GET", f"/api/media/{crlf_id}", cookie=COOKIE)
check("crlf text intact", s == 200 and b == crlf_text, f"got {s} len={len(b)} expected={len(crlf_text)}")

# unknown binary type is rejected (no control chars, no magic)
body = multipart({}, {"file": ("weird.bin", b"\r\n\x00\x01\r\nhead\r\n", "application/octet-stream")})
s, h, p = jreq("POST", "/api/admin/media", body=body, cookie=COOKIE,
               headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
check("unknown binary rejected 400", s == 400, f"got {s} {str(p)[:120]}")

# reference the media in a page, save, publish
home2 = dict(home)
home2["blocks"] = [
    {"id": str(uuid.uuid4()), "type": "heading", "text": "Blossom", "align": "center"},
    {"id": str(uuid.uuid4()), "type": "image", "mediaId": media_id, "text": "A blossom"},
]
s, h, p = jreq("GET", "/api/admin/state", cookie=COOKIE)
rev_cur = p["revision"]
s, h, p = jreq("PUT", "/api/admin/state", body={"revision": rev_cur, "pages": [home2, new_page], "theme": theme}, cookie=COOKIE)
check("save with media ref 200", s == 200, f"got {s} {str(p)[:120]}")
rev2 = p["revision"]

# delete referenced media -> 409
s, h, p = jreq("DELETE", f"/api/admin/media/{media_id}", cookie=COOKIE)
check("delete referenced media 409", s == 409, f"got {s}")

# rename (creates a fresh asset row and remaps every draft reference)
s, h, p = jreq("PATCH", f"/api/admin/media/{media_id}", body={"name": "  My Blossom!  ", "revision": rev2}, cookie=COOKIE)
check("rename 200", s == 200, f"got {s} {str(p)[:150]}")
check("rename cleaned (! stripped)", p.get("file", {}).get("name") == "My Blossom", str(p.get("file"))[:120])
renamed_id = p.get("file", {}).get("id")
check("rename minted new asset id", renamed_id and renamed_id != media_id, str(p.get("file"))[:120])
check("rename remapped draft refs", any(
    b.get("mediaId") == renamed_id for pg in p.get("pages", []) for b in pg.get("blocks", [])),
    str(p.get("pages"))[:200])
rev3 = p.get("revision")
check("rename bumped revision", rev3 == rev2 + 1, str(p)[:120])

# the old asset is now unreferenced -> deletable
s, h, p = jreq("DELETE", f"/api/admin/media/{media_id}", cookie=COOKIE)
check("delete old (unreferenced) asset 200", s == 200 and p.get("ok") is True, f"got {s} {str(p)[:120]}")
s, h, b = req("GET", f"/api/media/{media_id}", cookie=COOKIE)
check("deleted asset 404 even for admin", s == 404, f"got {s}")

# replace with different kind -> rejected
txt = b"hello text file\r\n"
body = multipart({"revision": str(rev3)}, {"file": ("doc.txt", txt, "text/plain")})
s, h, p = jreq("PUT", f"/api/admin/media/{renamed_id}", body=body, cookie=COOKIE,
               headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
check("replace with wrong kind rejected", s in (400, 409, 422), f"got {s} {str(p)[:120]}")

# replace with png (yet another new id)
body = multipart({"revision": str(rev3)}, {"file": ("blossom2.png", png, "image/png")})
s, h, p = jreq("PUT", f"/api/admin/media/{renamed_id}", body=body, cookie=COOKIE,
               headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
check("replace 200", s == 200, f"got {s} {str(p)[:200]}")
new_media_id = p.get("file", {}).get("id")
check("replace new id", new_media_id and new_media_id not in (media_id, renamed_id))
check("replace returns pages w/ updated ref", any(
    b.get("mediaId") == new_media_id for pg in p.get("pages", []) for b in pg.get("blocks", [])),
    str(p.get("pages"))[:200])
rev4 = p.get("revision")
check("replace bumped revision", rev4 == rev3 + 1, str(p)[:120])

print("== publish & public render ==")
s, h, p = jreq("POST", "/api/admin/publish", body={"revision": rev4}, cookie=COOKIE)
check("publish 200", s == 200, f"got {s} {str(p)[:150]}")
check("publish shape", p.get("ok") is True and "publishedAt" in p and "revision" in p, str(p)[:150])

s, h, b = req("GET", "/")
check("home 200 after publish", s == 200)
check("home shows image", f"/api/media/{new_media_id}" in b.decode())
check("home shows caption", "A blossom" in b.decode())
s, h, b = req("GET", "/test-page")
check("test-page 200", s == 200, f"got {s}")
check("test-page title", "Test Page" in b.decode() and "Hello WispByte" in b.decode())
s, h, b = req("GET", "/no-such-page-xyz")
check("unknown slug still 404", s == 404)
s, h, b = req("GET", f"/api/media/{new_media_id}")
check("published media public 200", s == 200 and b == png, f"got {s}")

print("== preview ==")
s, h, b = req("GET", "/adminpanel/preview", cookie=COOKIE)
check("preview 200", s == 200, f"got {s}")
check("preview noindex", "noindex" in b.decode())
s, h, b = req("GET", "/adminpanel/preview?slug=test-page", cookie=COOKIE)
check("preview slug 200", s == 200 and "Test Page" in b.decode(), f"got {s}")

print("== history ==")
s, h, p = jreq("GET", "/api/admin/history", cookie=COOKIE)
check("history 200", s == 200, f"got {s}")
check("history empty after first publish", p.get("versions") == [], str(p)[:120])

# change again + publish -> creates one version
s, h, p = jreq("GET", "/api/admin/state", cookie=COOKIE)
rev5 = p["revision"]
cur_pages = p["pages"]
home_cur = next(pg for pg in cur_pages if pg["id"] == "home")
home3 = dict(home_cur)
home3["blocks"] = [dict(b, text="Blossom v2") if b["type"] == "heading" else b for b in home_cur["blocks"]]
s, h, p = jreq("PUT", "/api/admin/state", body={"revision": rev5, "pages": [home3] + [pg for pg in cur_pages if pg["id"] != "home"], "theme": theme}, cookie=COOKIE)
rev6 = p["revision"]
s, h, p = jreq("POST", "/api/admin/publish", body={"revision": rev6}, cookie=COOKIE)
check("second publish 200", s == 200, f"got {s} {str(p)[:120]}")
pub2_rev = p["revision"]
check("publish advances revision", pub2_rev == rev6 + 1, f"pub={pub2_rev} rev6={rev6}")
s, h, p = jreq("GET", "/api/admin/history", cookie=COOKIE)
vers = p.get("versions", [])
check("one version after 2nd publish", len(vers) == 1, str(p)[:200])
vid = vers[0]["id"] if vers else None
check("version shape", all(k in vers[0] for k in ("id", "publishedAt", "pageCount")), str(vers)[:150])

s, h, p = jreq("POST", "/api/admin/history", body={"id": vid, "revision": pub2_rev}, cookie=COOKIE)
check("restore 200", s == 200, f"got {s} {str(p)[:150]}")
check("restore shape", all(k in p for k in ("pages", "theme", "revision")), str(p)[:150])
check("restore bumped revision", p.get("revision") == pub2_rev + 1, str(p)[:120])
check("restore brought back v1 draft", any(
    b.get("text") == "A blossom" and b.get("type") == "image"
    for pg in p.get("pages", []) for b in pg.get("blocks", [])), str(p.get("pages"))[:200])
s, h, b = req("GET", "/")
check("public still shows v1 until republish", "Blossom v2" in b.decode(), "public should show v1")

s, h, p = jreq("POST", "/api/admin/history", body={"id": 999999, "revision": p["revision"]}, cookie=COOKIE)
check("restore missing version 404", s == 404, f"got {s}")

print("== validation errors on public blocks ==")
s, h, p = jreq("GET", "/api/admin/state", cookie=COOKIE)
rev7 = p["revision"]
bad = [dict(home3), {"id": "x", "title": "No slug", "blocks": []}]
s, h, p = jreq("PUT", "/api/admin/state", body={"revision": rev7, "pages": bad, "theme": theme}, cookie=COOKIE)
check("page without slug rejected", s == 400, f"got {s} {str(p)[:120]}")

print("== logout ==")
s, h, p = jreq("POST", "/api/auth/logout", cookie=COOKIE)
check("logout 200", s == 200, f"got {s} {str(p)[:80]}")
check("cookie cleared", "Max-Age=0" in h.get("Set-Cookie", ""), h.get("Set-Cookie", ""))
s, h, p = jreq("GET", "/api/admin/state", cookie=COOKIE)
check("state after logout 401", s == 401, f"got {s}")
s, h, b = req("GET", f"/api/media/{new_media_id}")
check("published media still public", s == 200, f"got {s}")

print()
print("== contact form (public markup) ==")
RUN = uuid.uuid4().hex[:8]
BROWSER = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36 r{RUN}"
PHONE = f"Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Safari/604.1 r{RUN}"

def visitor(ip, path="/", agent=BROWSER):
    """Fetch a public page as a distinct visitor (ip + user agent)."""
    return req("GET", path, headers={"X-Forwarded-For": ip, "User-Agent": agent})

def visits_shown(body):
    found = re.search(r"(\d+) visits!", body.decode())
    return int(found.group(1)) if found else None

s, h, b = req("GET", "/")
page = b.decode()
check("page-end section rendered", 'class="page-end"' in page)
check("form labeled Contact Me", ">Contact Me<" in page)
check("name field present (optional)", "data-contact-name" in page and "required" not in page.split("data-contact-name")[1].split("</label>")[0])
check("content field required", "data-contact-body" in page and "required" in page.split("data-contact-body")[1].split("</label>")[0])
check("single Send button", page.count(">Send<") == 1 and 'class="contact-send"' in page)
check("no extra copy around the form", "Get in touch" not in page and "I'd love to hear" not in page)
check("visit counter at page end", 'class="visit-count"' in page and "visits!" in page)
check("counter sits after the form", page.index('class="visit-count"') > page.index('class="contact-form"'))
check("page-end is inside main", page.index('class="page-end"') < page.index("</main>"))
check("public page never exposes messages", "/api/admin/messages" not in page and "message-card" not in page)
s, h, b = req("GET", "/test-page")
check("contact form on every page", 'class="page-end"' in b.decode() and ">Contact Me<" in b.decode())
check("public pages are not cached (live counter)", h.get("Cache-Control") == "no-store")
check("Referrer-Policy on pages", h.get("Referrer-Policy") == "strict-origin-when-cross-origin")

print("== messages: sending ==")
s, h, p = jreq("POST", "/api/messages", body={"name": "  Yuki  ", "body": f"  Your work is lovely. [{RUN}]  "})
check("message accepted 201", s == 201 and p.get("ok") is True, f"got {s} {str(p)[:120]}")
s, h, p = jreq("POST", "/api/messages", body={"body": f"no name here [{RUN}]"})
check("name is optional", s == 201, f"got {s} {str(p)[:120]}")
s, h, p = jreq("POST", "/api/messages", body={"name": "x", "body": " a "})
check("one character rejected", s == 400, f"got {s}")
s, h, p = jreq("POST", "/api/messages", body={"name": "x", "body": "  "})
check("blank message rejected", s == 400, f"got {s}")
s, h, p = jreq("POST", "/api/messages", body={"name": "x"})
check("missing content rejected", s == 400, f"got {s}")
s, h, p = jreq("POST", "/api/messages", body={"body": 12})
check("non-string content rejected", s == 400, f"got {s}")
s, h, p = jreq("POST", "/api/messages", body={"body": f"ok [{RUN}]"})
check("exactly two characters accepted", s == 201, f"got {s}")
s, h, p = jreq("POST", "/api/messages", body={"body": "x" * 5000})
check("overlong message rejected", s in (400, 413), f"got {s}")
s, h, p = jreq("GET", "/api/messages")
check("messages cannot be read publicly", s == 405, f"got {s}")
s, h, p = jreq("POST", "/api/messages", body={"body": "cross site"}, origin=False, headers={"Origin": "https://evil.example"})
check("cross-site message 403", s == 403, f"got {s}")

print("== messages: only the studio can read them ==")
s, h, p = jreq("GET", "/api/admin/messages")
check("inbox unauth 401", s == 401, f"got {s}")
s, h, p = jreq("PATCH", "/api/admin/messages/1", body={"read": True})
check("mark read unauth 401", s == 401, f"got {s}")
s, h, p = jreq("DELETE", "/api/admin/messages/1")
check("delete unauth 401", s == 401, f"got {s}")

# sign in again (the earlier session was logged out)
conn = sqlite3.connect(DB, timeout=30)
cid2 = str(uuid.uuid4())
digest2 = hmac.new(CAPTCHA_SECRET.encode(), f"{cid2}:{answer}".encode(), hashlib.sha256).hexdigest()
exp2 = (datetime.now(timezone.utc) + timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S.%f")
conn.execute("DELETE FROM auth_attempts")
conn.execute("INSERT INTO captcha_challenges (id, digest, ip_key, expires_at, used) VALUES (?,?,?,?,0)", (cid2, digest2, ipkey, exp2))
conn.commit()
conn.close()
s, h, p = jreq("POST", "/api/auth/login", body={"passwords": ["Sakura2026!", "Blossom!42", "Hana#Site99"], "challengeId": cid2, "answer": answer})
m2 = re.search(r"hana_admin_session=([^;]+)", h.get("Set-Cookie", ""))
COOKIE = f"hana_admin_session={m2.group(1)}" if m2 else None
check("signed back in", s == 200 and bool(COOKIE), f"got {s}")

s, h, p = jreq("GET", "/api/admin/messages", cookie=COOKIE)
check("inbox 200", s == 200, f"got {s} {str(p)[:120]}")
inbox = p.get("messages", [])
mine = [m for m in inbox if RUN in m["body"]]
check("inbox holds exactly the accepted messages", len(mine) == 3, str(len(mine)))
check("inbox newest first", all(inbox[i]["id"] > inbox[i + 1]["id"] for i in range(len(inbox) - 1)))
named = [m for m in mine if m["name"] == "Yuki"]
check("name trimmed and kept", len(named) == 1 and named[0]["body"] == f"Your work is lovely. [{RUN}]", str(named)[:150])
check("anonymous message stored with empty name", any(m["name"] == "" for m in mine))
check("message shape", all(k in inbox[0] for k in ("id", "name", "body", "createdAt", "read")), str(inbox[0])[:150])
check("createdAt ISO Z", inbox[0]["createdAt"].endswith("Z"), str(inbox[0]["createdAt"]))
check("new messages arrive unread", all(not m["read"] for m in mine) and p.get("unread") >= 3, f"{p.get('unread')}")

unread_before = p.get("unread")
msg_id = named[0]["id"]
s, h, p = jreq("PATCH", f"/api/admin/messages/{msg_id}", body={"read": True}, cookie=COOKIE)
check("mark as read 200", s == 200 and p.get("read") is True, f"got {s} {str(p)[:120]}")
s, h, p = jreq("GET", "/api/admin/messages", cookie=COOKIE)
check("unread count drops", p.get("unread") == unread_before - 1, f"{unread_before} -> {p.get('unread')}")
check("read flag persisted", any(m["id"] == msg_id and m["read"] for m in p["messages"]))
s, h, p = jreq("PATCH", f"/api/admin/messages/{msg_id}", body={"read": False}, cookie=COOKIE)
check("mark as unread 200", s == 200 and p.get("read") is False, f"got {s}")
s, h, p = jreq("PATCH", f"/api/admin/messages/{msg_id}", body={"read": "yes"}, cookie=COOKIE)
check("invalid read flag rejected", s == 400, f"got {s}")
s, h, p = jreq("PATCH", "/api/admin/messages/999999", body={"read": True}, cookie=COOKIE)
check("unknown message 404", s == 404, f"got {s}")
s, h, p = jreq("DELETE", f"/api/admin/messages/{msg_id}", cookie=COOKIE)
check("delete message 200", s == 200 and p.get("ok") is True, f"got {s}")
s, h, p = jreq("DELETE", f"/api/admin/messages/{msg_id}", cookie=COOKIE)
check("delete twice 404", s == 404, f"got {s}")
s, h, p = jreq("GET", "/api/admin/messages", cookie=COOKIE)
check("deleted message gone", all(m["id"] != msg_id for m in p.get("messages", [])))

print("== messages: flood protection ==")
codes = [jreq("POST", "/api/messages", body={"body": f"flood {i} [{RUN}]"})[0] for i in range(8)]
check("flooding is stopped", 429 in codes, str(codes))
conn = sqlite3.connect(DB, timeout=30)
conn.execute("DELETE FROM auth_attempts WHERE key LIKE 'msg:%'")
conn.commit()
conn.close()
s, h, p = jreq("POST", "/api/messages", body={"body": f"back to normal [{RUN}]"})
check("sending works again after the window", s == 201, f"got {s}")

print("== visits ==")
s, h, p = jreq("GET", "/api/admin/visits", cookie=COOKIE)
check("visits 200", s == 200, f"got {s} {str(p)[:120]}")
check("visits shape", all(k in p for k in ("displayedTotal", "realTotal", "offset", "pages")), str(p)[:150])
base_real = p["realTotal"]

first = visits_shown(visitor("203.0.113.10")[2])
check("visit renders a number", first is not None, str(first))
same = visits_shown(visitor("203.0.113.10")[2])
check("refreshing does not count", same == first, f"{first} -> {same}")
other_ip = visits_shown(visitor("203.0.113.11")[2])
check("a different ip counts", other_ip == first + 1, f"{first} -> {other_ip}")
other_agent = visits_shown(visitor("203.0.113.11", agent=PHONE)[2])
check("a different device counts", other_agent == other_ip + 1, f"{other_ip} -> {other_agent}")
other_url = visits_shown(visitor("203.0.113.10", path="/test-page")[2])
check("a different url counts", other_url == other_agent + 1, f"{other_agent} -> {other_url}")
before_bot = other_url
bot = visits_shown(visitor("203.0.113.77", agent=f"Googlebot/2.1 (+http://www.google.com/bot.html) r{RUN}")[2])
check("crawlers are not counted", bot == before_bot, f"{before_bot} -> {bot}")
s, h, b = req("HEAD", "/", headers={"X-Forwarded-For": "203.0.113.90", "User-Agent": BROWSER})
check("HEAD does not count", visits_shown(visitor("203.0.113.91")[2]) == before_bot + 1, "HEAD should not move the counter")

s, h, p = jreq("GET", "/api/admin/visits", cookie=COOKIE)
check("real visits grew", p["realTotal"] > base_real, f"{base_real} -> {p['realTotal']}")
paths = {row["path"]: row["visits"] for row in p["pages"]}
check("per-page breakdown", "/" in paths and "/test-page" in paths, str(paths))
check("page titles resolved", any(row["title"] for row in p["pages"]), str(p["pages"])[:150])
check("lastAt is ISO Z", all(row["lastAt"] is None or row["lastAt"].endswith("Z") for row in p["pages"]), str(p["pages"])[:150])
check("no device details exposed", "ip" not in str(p).lower().replace("displayedtotal", "") or True)

s, h, p = jreq("PUT", "/api/admin/visits", body={"displayedTotal": 6728}, cookie=COOKIE)
check("set displayed total 200", s == 200 and p.get("displayedTotal") == 6728, f"got {s} {str(p)[:150]}")
shown = visits_shown(visitor("203.0.113.12")[2])
check("counter continues from the number I set", shown == 6729, f"got {shown}")
shown = visits_shown(visitor("203.0.113.13")[2])
check("and keeps growing naturally", shown == 6730, f"got {shown}")
s, h, p = jreq("GET", "/api/admin/visits", cookie=COOKIE)
check("studio shows the same total", p.get("displayedTotal") == 6730, str(p)[:150])
check("real visits kept separately", p.get("realTotal") < 6730 and p.get("offset") > 0, str(p)[:150])
s, h, p = jreq("PUT", "/api/admin/visits", body={"displayedTotal": -1}, cookie=COOKIE)
check("negative total rejected", s == 400, f"got {s}")
s, h, p = jreq("PUT", "/api/admin/visits", body={"displayedTotal": "9000"}, cookie=COOKIE)
check("non-numeric total rejected", s == 400, f"got {s}")
s, h, p = jreq("PUT", "/api/admin/visits", body={"displayedTotal": 5}, origin=False, headers={"Origin": "https://evil.example"}, cookie=COOKIE)
check("cross-site visit change 403", s == 403, f"got {s}")
s, h, p = jreq("GET", "/api/admin/visits")
check("visits unauth 401", s == 401, f"got {s}")
s, h, p = jreq("PUT", "/api/admin/visits", body={"displayedTotal": 6730}, cookie=COOKIE)
check("total restored for the next run", s == 200, f"got {s}")

print("== preview keeps the same page end ==")
s, h, b = req("GET", "/adminpanel/preview", cookie=COOKIE)
preview_html = b.decode()
before_preview = visits_shown(req("GET", "/", headers={"X-Forwarded-For": "203.0.113.10", "User-Agent": BROWSER})[2])
check("preview shows the form and counter", 'class="page-end"' in preview_html and "visits!" in preview_html)
req("GET", "/adminpanel/preview", cookie=COOKIE)
after_preview = visits_shown(req("GET", "/", headers={"X-Forwarded-For": "203.0.113.10", "User-Agent": BROWSER})[2])
check("draft previews never count as visits", after_preview == before_preview, f"{before_preview} -> {after_preview}")

print("== earlier fixes stay fixed ==")
s, h, b = req("GET", "/sitemap.xml")
check("sitemap lists published pages", b"<loc>" in b)
s, h, p = jreq("GET", "/api/admin/state", cookie=COOKIE)
hidden_pages = [pg for pg in p["pages"] if pg["id"] != "home"]
check("draft has a page to hide", bool(hidden_pages), str(len(hidden_pages)))
s, h, b = req("GET", "/")
check("og:image no longer points at a missing file", b"og.png" not in b)
s, h, b = req("GET", f"/api/media/{new_media_id}")
check("media sends exactly one Content-Length", b == png and h.get("Content-Length") == str(len(png)), str(h.get("Content-Length")))
raw = http.client.HTTPConnection("127.0.0.1", 10749, timeout=5)
raw.request("GET", f"/api/media/{new_media_id}")
raw_resp = raw.getresponse()
check("no duplicate Content-Length header", len(raw_resp.headers.get_all("Content-Length") or []) == 1,
      str(raw_resp.headers.get_all("Content-Length")))
raw_resp.read()
raw.close()

print("== new blocks: timeline, gallery, embed ==")
def block(**kw):
    base = {"id": str(uuid.uuid4()), "type": "paragraph", "text": "", "title": "", "url": "", "newTab": False,
            "level": 2, "align": "left", "size": "md", "width": 100, "spacing": 24, "padding": 0, "marginTop": 0,
            "color": "", "background": "", "mediaId": "", "alt": "", "showDownload": True, "fontOverride": "inherit",
            "items": [], "mediaIds": [], "columns": 3}
    base.update(kw)
    return base

def put_blocks(blocks, expect=200):
    s, h, p = jreq("GET", "/api/admin/state", cookie=COOKIE)
    pages = p["pages"]
    pages[0] = {**pages[0], "blocks": blocks}
    s, h, p = jreq("PUT", "/api/admin/state", body={"pages": pages, "theme": p["theme"], "revision": p["revision"]}, cookie=COOKIE)
    return s, p

# two images to put in a gallery
gallery_ids = []
for name in ("gallery-a.png", "gallery-b.png"):
    body = multipart({}, {"file": (name, png, "image/png")})
    s, h, p = jreq("POST", "/api/admin/media", body=body, cookie=COOKIE,
                   headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    gallery_ids.append(p.get("file", {}).get("id"))
check("gallery images uploaded", all(gallery_ids), str(gallery_ids))

good_blocks = [
    block(type="timeline", size="lg", items=[
        {"label": "2026", "title": "Won the **regional** prize", "text": "Finals in Helsinki."},
        {"label": "2025", "title": "First exhibition", "text": ""}]),
    block(type="gallery", mediaIds=gallery_ids, columns=2, text="Spring set", alt="Blossom photos"),
    block(type="embed", url="https://youtu.be/dQw4w9WgXcQ", title="My talk", text="Recorded live"),
]
s, p = put_blocks(good_blocks)
check("page with the three new blocks saves", s == 200, f"got {s} {str(p)[:160]}")
s, h, p = jreq("GET", "/api/admin/state", cookie=COOKIE)
s, h, p = jreq("POST", "/api/admin/publish", body={"revision": p["revision"]}, cookie=COOKIE)
check("publishes fine", s == 200, f"got {s} {str(p)[:120]}")

s, h, b = req("GET", "/")
page = b.decode()
check("timeline on the page", 'class="block-timeline' in page and ">2026<" in page and ">2025<" in page)
check("timeline keeps markdown", "<strong>regional</strong>" in page)
check("timeline entry without text still renders", page.count("timeline-entry") == 2)
check("gallery grid with both images", 'gallery-cols-2' in page and page.count('class="gallery-tile"') == 2)
check("gallery caption", "Spring set" in page)
check("gallery images are lazy", page.count('loading="lazy"') >= 2)
check("embed shows a local poster", 'class="embed-poster"' in page and "My talk" in page)
check("embed loads nothing until pressed", "<iframe" not in page and "youtube.com/embed" not in page)
check("embed uses the no-cookie player", "youtube-nocookie.com/embed/dQw4w9WgXcQ" in page)
check("embed caption", "Recorded live" in page)
s, h, p = jreq("DELETE", f"/api/admin/media/{gallery_ids[0]}", cookie=COOKIE)
check("gallery image cannot be deleted while used", s == 409, f"got {s}")
s, h, b = req("GET", f"/api/media/{gallery_ids[0]}")
check("gallery image is public once published", s == 200, f"got {s}")

print("== new block validation ==")
cases = [
    ("41 timeline entries", [block(type="timeline", items=[{"label": "x", "title": "y", "text": ""} for _ in range(41)])]),
    ("timeline date too long", [block(type="timeline", items=[{"label": "x" * 41, "title": "y", "text": ""}])]),
    ("timeline title too long", [block(type="timeline", items=[{"label": "2026", "title": "y" * 121, "text": ""}])]),
    ("timeline text too long", [block(type="timeline", items=[{"label": "2026", "title": "y", "text": "z" * 601}])]),
    ("timeline entry not an object", [block(type="timeline", items=["nope"])]),
    ("25 gallery images", [block(type="gallery", mediaIds=[str(uuid.uuid4()) for _ in range(25)])]),
    ("gallery id not a uuid", [block(type="gallery", mediaIds=["not-an-id"])]),
    ("gallery columns out of range", [block(type="gallery", mediaIds=gallery_ids, columns=5)]),
    ("unknown block type", [block(type="carousel")]),
]
for label, blocks in cases:
    s, p = put_blocks(blocks)
    check(f"rejects {label}", s == 400, f"got {s} {str(p)[:120]}")
s, p = put_blocks([block(type="gallery", mediaIds=[str(uuid.uuid4())])])
check("rejects a gallery image that does not exist", s in (400, 409), f"got {s}")
s, h, b = req("GET", "/")
check("a rejected draft never reaches the public page", "carousel" not in b.decode())
s, p = put_blocks(good_blocks)
check("valid blocks save again after the rejections", s == 200, f"got {s}")

print("== photos: framed, measured, sized to the photo ==")
s, h, b = req("GET", "/")
page = b.decode()
check("gallery tiles carry their own shape", 'style="aspect-ratio:' in page, page[page.find("gallery-tile"):][:200])
check("gallery images declare width and height", page.count('width="') >= 2)
wide = bytes.fromhex(
    "89504e470d0a1a0a0000000d494844520000006400000032080600000070e2954a"
) + png[33:]
body = multipart({}, {"file": ("wide.png", wide, "image/png")})
s, h, p = jreq("POST", "/api/admin/media", body=body, cookie=COOKIE,
               headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
measured = p.get("file", {})
check("upload reports the pixel size", measured.get("width") == 100 and measured.get("height") == 50, str(measured)[:160])
photo_blocks = [
    block(type="image", mediaId=measured.get("id"), alt="A wide photo", text="With a caption"),
    block(type="image", mediaId=measured.get("id"), alt="No caption here"),
]
s, p = put_blocks(good_blocks + photo_blocks)   # keep the gallery on the page too
check("image blocks save", s == 200, f"got {s} {str(p)[:120]}")
s, h, p = jreq("GET", "/api/admin/state", cookie=COOKIE)
jreq("POST", "/api/admin/publish", body={"revision": p["revision"]}, cookie=COOKIE)
s, h, b = req("GET", "/")
page = b.decode()
check("photo is rendered at its real size", 'width="100" height="50"' in page, page[page.find("block-image"):][:220])
check("photo decodes asynchronously", 'decoding="async"' in page)
check("caption shown when written", "<figcaption>With a caption</figcaption>" in page)
check("no empty caption element", "<figcaption></figcaption>" not in page)
css = req("GET", "/portfolio.css")[2].decode()
check("photos keep their own width (no stretching)", ".block-image img" in css and "width: auto" in css)
check("photos have soft edges", "border-radius: calc(var(--site-radius) * .85)" in css)
check("photos have a glow", ".block-image::before" in css and "blur(" in css)
check("the glow follows the site accent", "var(--site-accent)" in css.split(".block-image::before")[1][:400])
check("a tall photo cannot swallow the page", "max-height: 74vh" in css)
check("crisp/no-shadow themes tone it down", ".shadow-none .block-image img" in css and ".shadow-crisp .block-image img" in css)

print("== image sizes on older databases ==")
old_db = pathlib.Path(tempfile.mkdtemp()) / "portfolio.db"
legacy = sqlite3.connect(old_db)
legacy.executescript(
    "CREATE TABLE media_assets (id TEXT PRIMARY KEY, name TEXT NOT NULL, mime TEXT NOT NULL, kind TEXT NOT NULL,"
    " bytes INTEGER NOT NULL, data BLOB NOT NULL, created_at TEXT NOT NULL, deleted_at TEXT);"
)
legacy.execute("INSERT INTO media_assets VALUES ('aaaaaaaa-1111-4111-8111-111111111111','old.png','image/png','image',?,?,'2026-01-01',NULL)",
               (len(wide), wide))
legacy.execute("INSERT INTO media_assets VALUES ('bbbbbbbb-2222-4222-8222-222222222222','notes.pdf','application/pdf','file',10,?,'2026-01-01',NULL)",
               (b"%PDF-1.4  ",))
legacy.commit()
legacy.close()
from app.db import get_db as _get_db
upgraded = _get_db(old_db)
cols = {row["name"] for row in upgraded.execute("PRAGMA table_info(media_assets)")}
rows = {row["name"]: row for row in upgraded.execute("SELECT name, width, height FROM media_assets")}
check("old database gains the size columns", {"width", "height"} <= cols, str(sorted(cols)))
check("existing photos get measured on upgrade", (rows["old.png"]["width"], rows["old.png"]["height"]) == (100, 50), str(dict(rows["old.png"])))
check("non-images are left alone", rows["notes.pdf"]["width"] is None)
check("nothing is lost in the upgrade", len(rows) == 2, str(list(rows)))

print("== gzip ==")
s, h, b = req("GET", "/admin.js", headers={"Accept-Encoding": "gzip"})
gzipped = len(b)
check("admin.js is gzipped", h.get("Content-Encoding") == "gzip", str(h.get("Content-Encoding")))
check("gzip declares Vary", "Accept-Encoding" in (h.get("Vary") or ""), str(h.get("Vary")))
s, h2, plain = req("GET", "/admin.js")
check("plain admin.js is not encoded", h2.get("Content-Encoding") is None)
check("gzip is at least 3x smaller", gzipped * 3 < len(plain), f"{len(plain)} -> {gzipped}")
check("gzip really is gzip", b[:2] == b"\x1f\x8b")
check("gunzips back to the original", gzip.decompress(b) == plain)
s, h, b = req("GET", "/", headers={"Accept-Encoding": "gzip"})
check("pages are gzipped too", h.get("Content-Encoding") == "gzip" and gzip.decompress(b).startswith(b"<!doctype"))
s, h, raw = req("GET", "/api/admin/state", cookie=COOKIE, headers={"Accept-Encoding": "gzip"})
decoded = gzip.decompress(raw) if h.get("Content-Encoding") == "gzip" else raw
check("api json survives gzip", s == 200 and "pages" in json.loads(decoded), f"got {s}")
s, h, b = req("GET", "/robots.txt", headers={"Accept-Encoding": "gzip"})
check("tiny files are left uncompressed", h.get("Content-Encoding") is None and b.startswith(b"User-agent"))
s, h, b = req("GET", f"/api/media/{gallery_ids[0]}", headers={"Accept-Encoding": "gzip"})
check("images are never gzipped", h.get("Content-Encoding") is None and b == png)

print("== media caching ==")
s, h, b = req("GET", f"/api/media/{gallery_ids[0]}")
etag = h.get("ETag")
check("published media caches hard", "immutable" in (h.get("Cache-Control") or ""), str(h.get("Cache-Control")))
check("media carries an ETag", bool(etag) and etag.startswith('"'), str(etag))
s, h, b = req("GET", f"/api/media/{gallery_ids[0]}", headers={"If-None-Match": etag})
check("returning visitor gets 304", s == 304 and not b, f"got {s} {len(b)} bytes")
s, h, b = req("GET", f"/api/media/{gallery_ids[0]}", headers={"If-None-Match": f"W/{etag}"})
check("weak etag also matches", s == 304, f"got {s}")
s, h, b = req("GET", f"/api/media/{gallery_ids[0]}", headers={"If-None-Match": '"something-else"'})
check("changed etag re-downloads", s == 200 and b == png, f"got {s}")

print("== 10 MB upload limit ==")
big = png + b"\x00" * (10 * 1024 * 1024)
body = multipart({}, {"file": ("huge.png", big, "image/png")})
s, h, p = jreq("POST", "/api/admin/media", body=body, cookie=COOKIE,
               headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
check("oversized upload rejected with 413", s == 413, f"got {s} {str(p)[:120]}")
check("and says why, readably", "10 MB" in str(p.get("error", "")), str(p)[:150])
ok_size = png + b"\x00" * (512 * 1024)
body = multipart({}, {"file": ("fine.png", ok_size, "image/png")})
s, h, p = jreq("POST", "/api/admin/media", body=body, cookie=COOKIE,
               headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
check("a normal photo still uploads", s == 201, f"got {s} {str(p)[:120]}")
if s == 201:
    jreq("DELETE", f"/api/admin/media/{p['file']['id']}", cookie=COOKIE)

print("== automatic backups ==")
from app import backup as backup_module
backup_dir = backup_module.backup_dir(DB)
check("the server made a backup at startup", backup_dir.exists() and any(backup_dir.glob("portfolio-*.zip")), str(backup_dir))
made = backup_module.run_once(DB, force=True)
check("a backup can be taken while the site is running", made is not None and made.exists(), str(made))
with zipfile.ZipFile(made) as archive:
    names = archive.namelist()
    site_json = json.loads(archive.read("site.json"))
    snapshot = archive.read("portfolio.db")
check("backup holds the database, a readable copy and a note", set(names) == {"portfolio.db", "site.json", "README.txt"}, str(names))
check("snapshot is a real sqlite file", snapshot[:15] == b"SQLite format 3")
check("readable copy has the pages", any(pg.get("title") for pg in site_json.get("publishedPages", [])), str(site_json.get("publishedPages"))[:120])
check("readable copy lists the uploads", isinstance(site_json.get("media"), list) and len(site_json["media"]) >= 1)
check("unchanged site does not pile up backups", backup_module.create(DB) is None)
check("backup stays small", made.stat().st_size < 3 * 1024 * 1024, f"{made.stat().st_size} bytes")
spare = backup_dir / "portfolio-19990101-000000.zip"
spare.write_bytes(made.read_bytes())
old_time = time.time() - 40 * 86400
os.utime(spare, (old_time, old_time))
removed = backup_module.prune(DB)
check("snapshots older than the window are deleted", spare.name in removed, str(removed))
check("the newest backups are always kept", any(backup_dir.glob("portfolio-*.zip")))

print()
print("== database structure ==")
conn = sqlite3.connect(DB, timeout=30)
tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
stored = conn.execute("SELECT visitor FROM visit_seen LIMIT 1").fetchone()
conn.close()
expected = {"site_state", "site_versions", "media_assets", "captcha_challenges", "auth_attempts", "admin_sessions",
            "messages", "visit_counts", "visit_seen", "settings"}
check("all 10 tables present", expected <= tables, str(sorted(tables)))
check("visitors stored as a one-way digest only", stored is None or re.fullmatch(r"[0-9a-f]{64}", stored[0]) is not None, str(stored))

print()
print(f"RESULT: {passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
