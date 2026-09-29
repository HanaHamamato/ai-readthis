# Hana’s — Portfolio & Content Studio

A personal portfolio with a private content studio (`/adminpanel`) where
Hana edits pages, themes, media, and publish history. Everything is written
by her from scratch.

## What this is

One small **Python** web server (standard library only) that serves:

- the public portfolio at `/` and each page at `/<slug>` (identity and
  domain come from `config.json`), each ending with a small **Contact Me**
  form and a visit count,
- the private studio at `/adminpanel` (three-password login + one-use
  numeric CAPTCHA),
- a small JSON API for the studio: drafts, publishing, version history,
  media uploads, messages, and visits,
- media served from an embedded **SQLite** database (`data/portfolio.db` —
  created automatically, keep it in your backups).

There is no Node.js, no external database, and no build step.

## Running it

```bash
python main.py
```

The server reads configuration from, in order of precedence:

1. the process environment (the WispByte server panel),
2. a `.env` file in this directory (see `.env.example`),
3. `config.json` in this directory,
4. built-in defaults.

### config.json

```json
{
  "domain": "hanainfo.wisp.uno",
  "host": "0.0.0.0",
  "port": 10749,
  "site_name": "Hana's",
  "site_description": "VIew My Achievements"
}
```

- `domain` — your public domain; the public origin becomes `https://<domain>`
  unless `SITE_URL` is set elsewhere.
- `host` / `port` — where the server binds (it runs on `0.0.0.0:10749` by
  default).
- `site_name` / `site_description` — shown in page titles, meta/OG tags and
  the site footer.

### Required settings

| Variable | Purpose |
| --- | --- |
| `PORT` / `HOST` | Where the server listens/binds (see `config.json`) |
| `SITE_URL` | Public origin, e.g. `https://hanainfo.wisp.uno` |
| `CAPTCHA_SECRET` | Optional: one-use CAPTCHA digests key. If unset, a random one is generated on first start and kept in `data/captcha_secret` |
| `ADMIN_PASSWORD_HASH_1/2/3` | PBKDF2 hashes of three different admin passwords |
| `SITE_NAME` / `SITE_DESCRIPTION` | Override the `config.json` identity values |

### Password hashes

```bash
python scripts/make_password_hash.py "your password"
```

Run it three times with three different passwords and put the results in
`ADMIN_PASSWORD_HASH_1`, `_2`, and `_3`. Plain passwords are never stored
or committed; only the hashes are.

## Deploying on WispByte

1. Create a new server with the **Python** runtime.
2. Upload this project's files (everything in this directory).
3. In **Startup**, set the command to:
   ```
   python main.py
   ```
4. Add `Pillow` under **Additional Python Packages** (optional, but
   recommended — it lets the studio auto-optimize uploaded images).
5. Check that `config.json` has your domain (e.g. `hanainfo.wisp.uno`) and
   port, or create a `.env` with the values from the table above.
6. Start the server. The public site is on `/`, the studio on `/adminpanel`.

## Studio guide

- **Login** — enter the same three passwords (in any order) plus the
  numeric CAPTCHA. Sessions last 12 hours.
- **Pages** — reorder, rename, hide, and edit pages; each page is a list of
  blocks: heading, paragraph, quote, list, code, button, image, file/video,
  card, divider, spacing, section, **timeline** (dated milestones),
  **gallery** (image grid with a lightbox) and **video embed** (YouTube,
  Vimeo or a direct video link; nothing loads from them until a visitor
  presses play). Drag a block on the canvas to reorder it.
- **While you edit** — the draft saves itself a couple of seconds after you
  stop typing, undo/redo (Ctrl+Z / Ctrl+Shift+Z) covers every change, and
  Ctrl+S saves while Ctrl+P opens Publish. Typing never rebuilds the form,
  so the cursor stays where you left it.
- **Theme** — fonts, palette, radius, spacing, motion, shadows.
- **Media** — upload, rename, replace, and delete images/files (stored in
  the database; deleting only works while unreferenced). Photos are shown
  in soft-edged frames with a gentle accent glow, at their own size (never
  stretched), and the page reserves the exact space so nothing jumps while
  they load. Uploads are capped
  at 10 MB, and anything bigger is refused with a clear message before it
  is sent.
- **Messages** — everything visitors send through the *Contact Me* form at
  the end of every page. Only you can read them; visitors never see each
  other's notes. Mark them read or delete them.
- **Visits** — total and per-page visit counts. The same person reloading a
  page is not counted twice, and crawlers are ignored. Set the number your
  pages show to any value you like — new visits keep adding to it. No
  cookies, no IP addresses and no device details are stored: a visitor is
  remembered only as a one-way digest that expires.
- **History** — every publish is saved as a version and can be restored to
  the draft at any time.

## Backups

The site backs itself up on its own: a snapshot every 12 hours into
`data/backups/`, deleted after 21 days.

```
data/backups/portfolio-20260926-1830.zip
  portfolio.db   consistent snapshot, taken safely while the site runs
  site.json      readable copy of the pages, theme and upload list
  README.txt     how to put it back
```

Nothing is written when nothing changed since the last snapshot, and the
folder is capped by total size, so it stays small. To restore: stop the
site, unzip, copy `portfolio.db` over `data/portfolio.db` (removing any
`-wal`/`-shm` files next to it), start again.

| setting | default | meaning |
| --- | --- | --- |
| `BACKUP_EVERY_HOURS` | `12` | how often to snapshot (`0` turns it off) |
| `BACKUP_KEEP_DAYS` | `21` | how long a snapshot is kept |
| `BACKUP_MAX_MB` | `400` | total size budget for the folder |

## Project layout

```
main.py               entry point — `python main.py`
app/
  config.py           .env + environment loading
  server.py           HTTP server, routing, all API endpoints
  render.py           public HTML rendering (the designed site)
  admin_html.py       studio shell HTML
  store.py            SQLite schema + draft/publish/history logic
  security.py         passwords, sessions, CAPTCHA, rate limiting
  captcha.py          one-use numeric CAPTCHA (PIL, no external services)
  validation.py       page/block input validation
  engagement.py       contact messages + the visit counter
  media.py            upload size/type limits and optimization
  backup.py           automatic 12-hourly snapshots of the database
  db.py               database helpers
static/
  portfolio.css       public site styles
  portfolio.js        public site scripts
  admin.css           studio styles
  admin.js            studio app
  favicon.svg
scripts/
  make_password_hash.py
.env.example          configuration template
data/                 SQLite database (created at runtime, not committed)
```
