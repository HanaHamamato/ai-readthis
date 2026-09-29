/* Hana studio — client application.
 *
 * Vanilla JS port of the original React components (AdminLogin,
 * AdminDashboard, PageEditor, ThemePanel, MediaPanel, HistoryPanel).
 * The DOM structure and class names match the originals, so static/admin.css
 * (the design sheet, unchanged) renders it identically.
 */
(() => {
  "use strict";

  // ---------- helpers ----------
  const esc = (value) =>
    String(value === null || value === undefined ? "" : value)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");

  const ICONS = {
    menu: '<line x1="4" x2="20" y1="6" y2="6"/><line x1="4" x2="20" y1="12" y2="12"/><line x1="4" x2="20" y1="18" y2="18"/>',
    x: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
    save: '<path d="M15.2 3a2 2 0 0 1 1.4.6l3.8 3.8a2 2 0 0 1 .6 1.4V19a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z"/><path d="M17 21v-7a1 1 0 0 0-1-1H8a1 1 0 0 0-1 1v7"/><path d="M7 3v4a1 1 0 0 0 1 1h7"/>',
    sparkles: '<path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"/><path d="M20 3v4"/><path d="M22 5h-4"/>',
    layoutTemplate: '<rect width="18" height="7" x="3" y="3" rx="1"/><rect width="9" height="7" x="3" y="14" rx="1"/><rect width="5" height="7" x="16" y="14" rx="1"/>',
    settings2: '<path d="M20 7h-9"/><path d="M14 17H5"/><circle cx="17" cy="17" r="3"/><circle cx="7" cy="7" r="3"/>',
    image: '<rect width="18" height="18" x="3" y="3" rx="2" ry="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/>',
    history: '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l4 2"/>',
    plus: '<path d="M5 12h14"/><path d="M12 5v14"/>',
    arrowUp: '<path d="m5 12 7-7 7 7"/><path d="M12 19V5"/>',
    arrowDown: '<path d="M12 5v14"/><path d="m19 12-7 7-7-7"/>',
    copy: '<rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/>',
    trash2: '<path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/><line x1="10" x2="10" y1="11" y2="17"/><line x1="14" x2="14" y1="11" y2="17"/>',
    externalLink: '<path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>',
    logOut: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" x2="9" y1="12" y2="12"/>',
    check: '<path d="M20 6 9 17l-5-5"/>',
    clock3: '<path d="M12 6v6l4 2"/><circle cx="12" cy="12" r="10"/>',
    chevronDown: '<path d="m6 9 6 6 6-6"/>',
    fileStack: '<path d="M15.5 2H8a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V7.5L15.5 2z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/>',
    fileText: '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/>',
    fileUp: '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="m9 13 3-3 3 3"/><path d="M12 10v8"/>',
    uploadCloud: '<path d="M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242"/><path d="M12 12v9"/><path d="m16 16-4-4-4 4"/>',
    pencil: '<path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/><path d="m15 5 4 4"/>',
    rotateCcw: '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/>',
    play: '<polygon points="6 3 20 12 6 21 6 3"/>',
    arrowDownToLine: '<path d="M12 17V3"/><path d="m6 11 6 6 6-6"/><path d="M19 21H5"/>',
    arrowRight: '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
    arrowLeft: '<path d="m12 19-7-7 7-7"/><path d="M19 12H5"/>',
    arrowUpRight: '<path d="M7 7h10v10"/><path d="M7 17 17 7"/>',
    eye: '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>',
    eyeOff: '<path d="M9.88 9.88a3 3 0 1 0 4.24 4.24"/><path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68"/><path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61"/><line x1="2" x2="22" y1="2" y2="22"/>',
    lockKeyhole: '<rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><circle cx="12" cy="16" r="1"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    refreshCw: '<path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/>',
    type: '<polyline points="4 7 4 4 20 4 20 7"/><line x1="9" x2="15" y1="20" y2="20"/><line x1="12" x2="12" y1="4" y2="20"/>',
    bold: '<path d="M14 12a4 4 0 0 0 0-8H6v8"/><path d="M15 20a4 4 0 0 0 0-8H6v8Z"/>',
    italic: '<line x1="19" x2="10" y1="4" y2="4"/><line x1="14" x2="5" y1="20" y2="20"/><line x1="15" x2="9" y1="4" y2="20"/>',
    code2: '<path d="m18 16 4-4-4-4"/><path d="m6 8-4 4 4 4"/><path d="m14.5 4-5 16"/>',
    link2: '<path d="M9 17H7A5 5 0 0 1 7 7h2"/><path d="M15 7h2a5 5 0 1 1 0 10h-2"/><line x1="8" x2="16" y1="12" y2="12"/>',
    list: '<path d="M3 12h.01"/><path d="M3 18h.01"/><path d="M3 6h.01"/><path d="M8 12h13"/><path d="M8 18h13"/><path d="M8 6h13"/>',
    quote: '<path d="M3 21c3 0 7-1 7-8V5c0-1.25-.756-2.017-2-2H4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2 1 0 1 0 1 1v1c0 1-1 2-2 2s-1 .008-1 1.031V20c0 1 0 1 1 1z"/><path d="M15 21c3 0 7-1 7-8V5c0-1.25-.757-2.017-2-2h-4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2 1 0 1 0 1 1v1c0 1-1 2-2 2s-1 .008-1 1.031V20c0 1 0 1 1 1z"/>',
    mousePointer2: '<path d="m4 4 7.07 17 2.51-7.39L21 11.07z"/><path d="m13 13 6 6"/>',
    alignLeft: '<line x1="21" x2="3" y1="6" y2="6"/><line x1="15" x2="3" y1="12" y2="12"/><line x1="17" x2="3" y1="18" y2="18"/>',
    alignCenter: '<line x1="21" x2="3" y1="6" y2="6"/><line x1="17" x2="7" y1="12" y2="12"/><line x1="19" x2="5" y1="18" y2="18"/>',
    alignRight: '<line x1="21" x2="3" y1="6" y2="6"/><line x1="21" x2="9" y1="12" y2="12"/><line x1="21" x2="7" y1="18" y2="18"/>',
    minus: '<path d="M5 12h14"/>',
    moveVertical: '<path d="m8 9 4-4 4 4"/><path d="m16 15-4 4-4-4"/><path d="M12 5v14"/>',
    columns3: '<rect width="18" height="18" x="3" y="3" rx="2"/><path d="M9 3v18"/><path d="M15 3v18"/>',
    heading1: '<path d="M4 12h8"/><path d="M4 18V6"/><path d="M12 18V6"/><path d="M21 18h-4c0-4 4-3 4-6 0-1.5-2-2.5-4-1"/>',
    home: '<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z"/><path d="M9 21v-7h6v7"/>',
    mail: '<rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>',
    gallery: '<rect width="7" height="7" x="3" y="3" rx="1"/><rect width="7" height="7" x="14" y="3" rx="1"/><rect width="7" height="7" x="14" y="14" rx="1"/><rect width="7" height="7" x="3" y="14" rx="1"/>',
    undo2: '<path d="M9 14 4 9l5-5"/><path d="M4 9h10.5a5.5 5.5 0 0 1 5.5 5.5 5.5 5.5 0 0 1-5.5 5.5H11"/>',
    redo2: '<path d="m15 14 5-5-5-5"/><path d="M20 9H9.5A5.5 5.5 0 0 0 4 14.5 5.5 5.5 0 0 0 9.5 20H13"/>',
    gripVertical: '<circle cx="9" cy="6" r="1"/><circle cx="9" cy="12" r="1"/><circle cx="9" cy="18" r="1"/><circle cx="15" cy="6" r="1"/><circle cx="15" cy="12" r="1"/><circle cx="15" cy="18" r="1"/>',
    alertTriangle: '<path d="m21.7 18-8-14a2 2 0 0 0-3.4 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.7-3"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
    mailOpen: '<path d="M21.2 8.4c.5.38.8.97.8 1.6v10a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V10a2 2 0 0 1 .8-1.6l8-6a2 2 0 0 1 2.4 0z"/><path d="m22 10-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 10"/>',
    barChart3: '<path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/>',
  };

  const icon = (name, size = 16, strokeWidth = 2) =>
    `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="${strokeWidth}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name] || ""}</svg>`;

  // crypto.randomUUID() only exists in secure contexts (https / localhost).
  // Over plain http it is undefined and every block/page creation silently
  // throws. Fall back to a UUID-shaped id so the studio works everywhere.
  const newId = () => {
    try {
      if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") return crypto.randomUUID();
    } catch { /* non-secure context */ }
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
      const r = (Math.random() * 16) | 0;
      return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
    });
  };

  const FONT_CHOICES = ["modern", "rounded", "editorial", "mono", "studio"];
  const BLOCK_TYPES = ["heading", "paragraph", "quote", "list", "code", "button", "image", "file", "card", "divider", "spacer", "section", "timeline", "gallery", "embed"];
  const BLOCK_NAMES = {
    heading: "Heading", paragraph: "Paragraph", quote: "Quote", list: "List", code: "Code",
    button: "Button", image: "Image", file: "File / video", card: "Card", divider: "Divider",
    spacer: "Spacing", section: "Section", timeline: "Timeline", gallery: "Gallery", embed: "Video embed",
  };
  const BLOCK_ICONS = {
    heading: "heading1", paragraph: "alignLeft", quote: "quote", list: "list", code: "code2",
    button: "mousePointer2", image: "image", file: "fileUp", card: "columns3",
    divider: "minus", spacer: "moveVertical", section: "sparkles",
    timeline: "clock3", gallery: "gallery", embed: "play",
  };
  const MAX_TIMELINE_ITEMS = 40;
  const MAX_GALLERY_IMAGES = 24;
  const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;

  // Same link parsing as app/validation.py: build the player URL from the id.
  const YOUTUBE_RE = /(?:youtube\.com\/(?:watch\?(?:[^#]*&)?v=|embed\/|shorts\/|live\/|v\/)|youtu\.be\/)([A-Za-z0-9_-]{6,24})/;
  const VIMEO_RE = /vimeo\.com\/(?:video\/|channels\/[A-Za-z0-9_-]+\/)?(\d{6,15})/;
  const VIDEO_FILE_RE = /\.(?:mp4|webm|ogv|mov|m4v)(?:[?#]|$)/i;
  function parseEmbed(url) {
    if (typeof url !== "string" || !url.trim()) return { kind: "", src: "", label: "" };
    const value = url.trim();
    const youtube = YOUTUBE_RE.exec(value);
    if (youtube) return { kind: "youtube", src: `https://www.youtube-nocookie.com/embed/${youtube[1]}?rel=0&autoplay=1`, label: "YouTube" };
    const vimeo = VIMEO_RE.exec(value);
    if (vimeo) return { kind: "vimeo", src: `https://player.vimeo.com/video/${vimeo[1]}?autoplay=1`, label: "Vimeo" };
    if (VIDEO_FILE_RE.test(value) && (/^https?:\/\//.test(value) || value.startsWith("/"))) return { kind: "video", src: value, label: "Video" };
    return { kind: "link", src: value, label: "Link" };
  }
  const FONT_LABELS = { modern: "Modern", rounded: "Rounded", editorial: "Editorial", mono: "Monospace", studio: "Studio" };
  const FONT_NOTES = {
    modern: "Clear & balanced", rounded: "Soft & friendly", editorial: "A little literary",
    mono: "Made for makers", studio: "Clean & considered",
  };
  const TEXT_TYPES = ["heading", "paragraph", "quote", "list", "code", "button", "card", "section", "image", "file"];

  const isUuid = (value) => /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value || "");
  const pagePath = (page) => (page.slug ? `/${page.slug}` : "/");

  function safeHref(url) {
    if (typeof url !== "string" || !url) return "#";
    if (/^\/(?:[a-z0-9]+(?:-[a-z0-9]+)*\/?)?(?:#[a-z0-9-]+)?$/i.test(url)) return url;
    if (/^#[a-z0-9-]+$/i.test(url)) return url;
    if (/^(https?:\/\/|mailto:)/i.test(url)) {
      if (url.includes("://")) {
        const host = url.split("://")[1].split("/")[0];
        if (host.includes("@")) return "#";
      }
      return url;
    }
    return "#";
  }

  const sectionId = (text) =>
    (String(text || "").toLowerCase().replace(/[^a-z0-9\s-]/g, "").trim().replace(/\s+/g, "-").slice(0, 64)) || "section";

  // Markdown-like inline formatting (same rules as the server renderer).
  const mdText = (value) =>
    esc(value)
      .replace(/`([^`\n]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>")
      .replace(/\*([^*\n]+)\*/g, "<em>$1</em>")
      .replace(/~~([^~\n]+)~~/g, "<del>$1</del>")
      .replace(/\n/g, "<br>");

  function inlineMd(value, newTab = false) {
    const linkRe = /\[([^\]]+)\]\(([^)\s]+)\)/g;
    let result = "";
    let cursor = 0;
    let match;
    while ((match = linkRe.exec(value))) {
      result += mdText(value.slice(cursor, match.index));
      const url = safeHref(match[2]);
      const label = mdText(match[1]);
      if (url === "#") result += label;
      else result += `<a href="${esc(url)}"${newTab ? ' target="_blank" rel="noopener noreferrer"' : ""}>${label}</a>`;
      cursor = match.index + match[0].length;
    }
    return result + mdText(value.slice(cursor));
  }

  const imageDimensions = (info) => (info && info.width && info.height ? ` width="${info.width}" height="${info.height}"` : "");
  const aspectStyle = (info) => (info && info.width && info.height ? ` style="aspect-ratio:${info.width}/${info.height}"` : "");

  function blockStyle(block) {
    const parts = [
      `width:${block.width ?? 100}%`,
      "max-width:100%",
      `margin-top:${block.marginTop ?? 0}px`,
      block.type === "spacer" ? "margin-bottom:0" : `margin-bottom:calc(${block.spacing ?? 24}px * var(--site-spacing))`,
    ];
    if (block.padding) parts.push(`padding:${block.padding}px`);
    parts.push(`text-align:${block.align || "left"}`);
    if (block.color) parts.push(`color:${block.color}`);
    if (block.background) parts.push(`background-color:${block.background}`);
    return parts.join(";");
  }

  function blockHtml(block, mediaUrls = {}, mediaInfo = {}, editing = false) {
    const btype = block.type || "";
    const text = block.text || "";
    const mediaId = block.mediaId || "";
    const mediaUrl = mediaUrls[mediaId] || (mediaId ? `/api/media/${mediaId}` : "");
    const info = mediaInfo[mediaId] || {};
    let content = "";
    if (btype === "heading") {
      const inner = text ? inlineMd(text, block.newTab) : editing ? '<span class="block-empty">A new heading</span>' : "";
      content = `<h${block.level || 2} id="${esc(sectionId(text))}" class="block-heading block-heading-${block.size || "md"}">${inner}</h${block.level || 2}>`;
    } else if (btype === "paragraph") {
      const inner = text ? inlineMd(text, block.newTab) : editing ? '<span class="block-empty">Write something lovely here...</span>' : "";
      content = `<p class="block-paragraph block-text-${block.size || "md"}">${inner}</p>`;
    } else if (btype === "quote") {
      const inner = text ? inlineMd(text, block.newTab) : editing ? '<span class="block-empty">A quote worth keeping.</span>' : "";
      content = `<blockquote class="block-quote block-text-${block.size || "md"}"><span class="quote-mark">\u201c</span>${inner}</blockquote>`;
    } else if (btype === "list") {
      const lines = text.split("\n").map((line) => line.trim()).map((line) => line.replace(/^(?:[-*\u2022]|\d+\.)\s*/, "")).filter(Boolean);
      if (lines.length) {
        content = `<ul class="block-list block-text-${block.size || "md"}">${lines.map((line) => `<li>${inlineMd(line, block.newTab)}</li>`).join("")}</ul>`;
      } else if (editing) {
        content = '<span class="block-empty">Add one item per line</span>';
      }
    } else if (btype === "code") {
      content = text ? `<pre class="block-code"><code>${esc(text)}</code></pre>` : editing ? '<span class="block-empty">Your code goes here</span>' : "";
    } else if (btype === "button") {
      if (block.url) {
        content = `<a class="site-button block-button" href="${esc(safeHref(block.url))}"${block.newTab ? ' target="_blank" rel="noopener noreferrer"' : ""}>${esc(text || "Explore")}${icon("arrowUpRight", 17)}</a>`;
      } else if (editing) {
        content = '<span class="block-empty">Add a label and destination to make a button</span>';
      }
    } else if (btype === "image") {
      if (mediaId) {
        const caption = text ? `<figcaption>${esc(text)}</figcaption>` : "";
        content = `<figure class="block-image"><img src="${esc(mediaUrl)}" alt="${esc(block.alt || "")}"` +
          `${imageDimensions(info)} loading="lazy" decoding="async">${caption}</figure>`;
      } else if (editing) {
        content = '<span class="block-empty">Choose an image from your library</span>';
      }
    } else if (btype === "file") {
      if (mediaId) {
        const label = block.title || info.name || "File";
        const video = info.kind === "video" ? `<video controls preload="metadata" playsinline src="${esc(mediaUrl)}" aria-label="${esc(block.alt || label)}"></video>` : "";
        const glyph = info.kind === "video" ? icon("play", 21) : icon("fileText", 21);
        const download = block.showDownload !== false
          ? `<a href="${esc(mediaUrl)}" download="${esc(info.name || label)}" class="file-download" aria-label="Download ${esc(label)}">${icon("arrowDownToLine", 17)}<span>Download</span></a>` : "";
        const description = text ? `<small>${esc(text)}</small>` : "";
        content = `<div class="file-block">${video}<div class="file-card"><span class="file-card-icon">${glyph}</span><span class="file-card-text"><strong>${esc(label)}</strong>${description}</span>${download}</div></div>`;
      } else if (editing) {
        content = '<span class="block-empty">Choose a file from your library</span>';
      }
    } else if (btype === "card") {
      const target = block.newTab ? ' target="_blank" rel="noopener noreferrer"' : "";
      const titleHtml = block.title ? `<h3>${esc(block.title)}</h3>` : "";
      const descriptionText = text || (editing ? "Write a little about this..." : "");
      const linkHtml = block.url
        ? `<a class="card-link" href="${esc(safeHref(block.url))}"${target}>Explore ${icon("arrowUpRight", 15)}</a>` : "";
      content = `<article class="content-card"><span class="card-sparkle">\u2733</span>${titleHtml}<div class="card-description">${inlineMd(descriptionText, block.newTab)}</div>${linkHtml}</article>`;
    } else if (btype === "section") {
      const eyebrow = block.title || "A little more";
      const heading = text || (editing ? "Your section heading" : "");
      content = `<section class="content-section" id="${esc(sectionId(block.title || block.text || ""))}"><span class="section-eyebrow">${esc(eyebrow)}</span><h2>${esc(heading)}</h2></section>`;
    } else if (btype === "timeline") {
      const entries = (block.items || []).filter((item) => item.label || item.title || item.text);
      if (entries.length) {
        const rows = entries.map((item) =>
          `<li class="timeline-entry"><span class="timeline-dot" aria-hidden="true"></span><div class="timeline-body">` +
          (item.label ? `<span class="timeline-when">${esc(item.label)}</span>` : "") +
          (item.title ? `<h3 class="timeline-title">${inlineMd(item.title, block.newTab)}</h3>` : "") +
          (item.text ? `<p class="timeline-text">${inlineMd(item.text, block.newTab)}</p>` : "") +
          `</div></li>`).join("");
        content = `<ol class="block-timeline block-text-${block.size || "md"}">${rows}</ol>`;
      } else if (editing) {
        content = '<span class="block-empty">Add your first milestone — a date, a title, a line about it</span>';
      }
    } else if (btype === "gallery") {
      const ids = (block.mediaIds || []).filter(Boolean);
      if (ids.length) {
        const tiles = ids.map((id, index) => {
          const url = mediaUrls[id] || `/api/media/${id}`;
          const details = mediaInfo[id] || {};
          const alt = block.alt || details.name || "";
          return `<button type="button" class="gallery-tile" data-gallery-open="${index}" data-gallery-src="${esc(url)}" ` +
            `data-gallery-caption="${esc(details.name || "")}"${aspectStyle(details)} aria-label="Open image ${index + 1} of ${ids.length}">` +
            `<img src="${esc(url)}" alt="${esc(alt)}"${imageDimensions(details)} loading="lazy" decoding="async"></button>`;
        }).join("");
        content = `<figure class="block-gallery gallery-cols-${block.columns || 3}" data-gallery><div class="gallery-grid">${tiles}</div>` +
          (text ? `<figcaption class="gallery-caption">${esc(text)}</figcaption>` : "") + `</figure>`;
      } else if (editing) {
        content = '<span class="block-empty">Pick a few images from your library</span>';
      }
    } else if (btype === "embed") {
      const media = parseEmbed(block.url || "");
      const label = block.title || "";
      if (media.kind === "youtube" || media.kind === "vimeo") {
        content = `<figure class="block-embed" data-embed-frame="${esc(media.src)}" data-embed-title="${esc(label || media.label)}">` +
          `<button type="button" class="embed-poster" aria-label="Play ${esc(label || media.label)}">` +
          `<span class="embed-play">${icon("play", 26)}</span>` +
          `<span class="embed-meta"><strong>${esc(label || "Watch the video")}</strong>` +
          `<small>${esc(media.label)} \u00b7 loads only when you press play</small></span></button>` +
          (text ? `<figcaption>${esc(text)}</figcaption>` : "") + `</figure>`;
      } else if (media.kind === "video") {
        content = `<figure class="block-embed block-embed-file"><video controls preload="none" playsinline src="${esc(safeHref(media.src))}" ` +
          `aria-label="${esc(label || block.alt || "Video")}"></video>` + (text ? `<figcaption>${esc(text)}</figcaption>` : "") + `</figure>`;
      } else if (media.kind === "link") {
        content = `<a class="site-button block-button" href="${esc(safeHref(block.url || ""))}"${block.newTab ? ' target="_blank" rel="noopener noreferrer"' : ""}>` +
          `${esc(label || text || "Open link")}${icon("arrowUpRight", 17)}</a>`;
      } else if (editing) {
        content = '<span class="block-empty">Paste a YouTube, Vimeo or video link</span>';
      }
    } else if (btype === "divider") {
      content = '<hr class="block-divider">';
    } else if (btype === "spacer") {
      content = `<div class="block-spacer" style="height:${block.spacing ?? 24}px" aria-hidden="true"></div>`;
    }
    if (!content) return "";
    return `<div data-block-id="${esc(block.id || "")}" class="portfolio-block portfolio-block-${esc(btype)} reveal font-${esc(block.fontOverride || "inherit")}" style="${blockStyle(block)}">${content}</div>`;
  }

  function contentBlocksHtml(blocks, mediaUrls = {}, mediaInfo = {}, editing = false) {
    const rendered = blocks.map((block) => blockHtml(block, mediaUrls, mediaInfo, editing)).filter(Boolean);
    return `<div class="content-blocks">${rendered.join("")}</div>`;
  }

  const themeStyleVars = (theme) =>
    `--site-bg:${theme.background};--site-surface:${theme.surface};--site-text:${theme.text};` +
    `--site-muted:${theme.muted};--site-accent:${theme.accent};--site-radius:${theme.radius}px;` +
    `--site-heading-scale:${theme.headingScale};--site-spacing:${theme.spacing};--site-border-width:${theme.borderWidth}px`;

  const siteClasses = (theme) =>
    `public-site font-${theme.font} theme-${theme.mode} motion-${theme.animation} ` +
    `shadow-${theme.shadow} cards-${theme.cardStyle} buttons-${theme.buttonStyle}`;

  // Client-side validation (same rules and messages as the server).
  const SLUG_RE = /^(?:[a-z0-9]+(?:-[a-z0-9]+)*)?$/;
  const COLOR_RE = /^#[0-9a-fA-F]{6}$/;
  const RESERVED = new Set(["adminpanel", "api", "_next", "assets", "fonts", "favicon.ico", "robots.txt", "sitemap.xml", "portfolio.css", "portfolio.js"]);

  function validatePages(pages) {
    if (!Array.isArray(pages) || pages.length < 1 || pages.length > 50) return "The site needs between 1 and 50 pages.";
    const parsed = [];
    for (const page of pages) {
      if (!page || typeof page !== "object") return "Each page must be an object.";
      if (page.id !== "home" && !isUuid(page.id)) return "A page is missing its id.";
      if (typeof page.title !== "string" || page.title.trim().length < 1 || page.title.trim().length > 100) return "Every page needs a title (1–100 characters).";
      if (typeof page.slug !== "string" || page.slug.length > 65 || !SLUG_RE.test(page.slug)) return "The URL must use lowercase letters, numbers, and dashes.";
      if (typeof page.description !== "string" || page.description.length > 260) return "The meta description is too long.";
      if (!Array.isArray(page.blocks) || page.blocks.length > 200) return "A page can contain at most 200 blocks.";
      for (const block of page.blocks) {
        if (!block || typeof block !== "object") return "Each block must be an object.";
        if (!isUuid(block.id)) return "A block is missing its id.";
        if (!BLOCK_TYPES.includes(block.type)) return "A block has an unknown type.";
        if (typeof block.text !== "string" || block.text.length > 16000) return "Block text is too long.";
        if (typeof block.title !== "string" || block.title.length > 200) return "Block title is too long.";
        if (block.level !== 1 && block.level !== 2 && block.level !== 3) return "Heading level must be 1, 2, or 3.";
        if (!["left", "center", "right"].includes(block.align)) return "Alignment is invalid.";
        if (!["sm", "md", "lg", "xl"].includes(block.size)) return "Text size is invalid.";
        const ranges = { width: [20, 100], spacing: [0, 120], padding: [0, 100], marginTop: [0, 120] };
        for (const [key, [low, high]] of Object.entries(ranges)) {
          if (!Number.isInteger(block[key]) || block[key] < low || block[key] > high) return `${key[0].toUpperCase() + key.slice(1)} is out of range.`;
        }
        if (block.mediaId !== "" && !isUuid(block.mediaId)) return "A block references an unknown upload.";
        if (typeof block.alt !== "string" || block.alt.length > 250) return "Alt text is too long.";
        if (!["inherit", ...FONT_CHOICES].includes(block.fontOverride)) return "Block font is invalid.";
        const items = block.items || [];
        if (!Array.isArray(items) || items.length > MAX_TIMELINE_ITEMS) return `A timeline can hold at most ${MAX_TIMELINE_ITEMS} entries.`;
        for (const item of items) {
          if (!item || typeof item !== "object") return "Each timeline entry must be an object.";
          if (typeof item.label !== "string" || item.label.length > 40) return "A timeline date is too long (40 characters).";
          if (typeof item.title !== "string" || item.title.length > 120) return "A timeline title is too long (120 characters).";
          if (typeof item.text !== "string" || item.text.length > 600) return "A timeline description is too long (600 characters).";
        }
        const gallery = block.mediaIds || [];
        if (!Array.isArray(gallery) || gallery.length > MAX_GALLERY_IMAGES) return `A gallery can hold at most ${MAX_GALLERY_IMAGES} images.`;
        for (const id of gallery) if (!isUuid(id)) return "A gallery references an unknown upload.";
        const columns = block.columns ?? 3;
        if (!Number.isInteger(columns) || columns < 2 || columns > 4) return "Gallery columns must be 2, 3, or 4.";
      }
      parsed.push(page);
    }
    if (parsed[0].id !== "home" || parsed[0].slug !== "" || parsed.filter((p) => p.id === "home").length !== 1) return "Home must remain the first page at /.";
    const slugs = new Set();
    const ids = new Set();
    for (const page of parsed) {
      if (slugs.has(page.slug) || ids.has(page.id) || RESERVED.has(page.slug) || (page.id !== "home" && !page.slug)) {
        return `Duplicate or reserved page path: ${page.slug || "/"}.`;
      }
      slugs.add(page.slug);
      ids.add(page.id);
      const blockIds = page.blocks.map((block) => block.id);
      if (new Set(blockIds).size !== blockIds.length) return `Duplicate blocks on ${page.title}.`;
    }
    return null;
  }

  async function requestApi(url, method = "GET", body) {
    const response = await fetch(url, {
      method,
      credentials: "same-origin",
      cache: "no-store",
      headers: body instanceof FormData ? undefined : body !== undefined ? { "Content-Type": "application/json" } : undefined,
      body: body instanceof FormData ? body : body !== undefined ? JSON.stringify(body) : undefined,
    });
    let result;
    try { result = await response.json(); } catch { throw new Error("The server did not respond. Try again."); }
    if (!response.ok) throw new Error(typeof result.error === "string" ? result.error : "Something went wrong. Try again.");
    return result;
  }

  // =====================================================================
  // Sign-in
  // =====================================================================
  const loginApp = document.getElementById("login-app");
  if (loginApp) {
    const state = { challenge: null, captchaBusy: false, busy: false, visible: false };
    const imageSlot = document.getElementById("captcha-image");
    const answerInput = document.getElementById("captcha-answer");
    const submitButton = document.getElementById("login-submit");
    const errorSlot = document.getElementById("login-error-slot");

    const showError = (message) => { errorSlot.innerHTML = message ? `<div role="alert" class="login-error">${esc(message)}</div>` : ""; };

    async function loadChallenge() {
      state.captchaBusy = true;
      state.challenge = null;
      answerInput.value = "";
      imageSlot.innerHTML = "<span>Creating challenge...</span>";
      submitButton.disabled = true;
      const challengeButton = document.getElementById("new-challenge");
      const spinner = challengeButton.querySelector("svg");
      if (spinner) spinner.classList.add("spin");
      try {
        const response = await fetch("/api/auth/captcha", { cache: "no-store" });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Could not load the challenge.");
        state.challenge = data;
        imageSlot.innerHTML = `<img src="${esc(data.image)}" alt="Arithmetic challenge: calculate the answer shown in the image">`;
        submitButton.disabled = false;
      } catch (issue) {
        showError(issue instanceof Error ? issue.message : "Could not load the challenge.");
        imageSlot.innerHTML = "<span>Challenge unavailable</span>";
      } finally {
        state.captchaBusy = false;
        if (spinner) spinner.classList.remove("spin");
        const challengeButton2 = document.getElementById("new-challenge");
        if (challengeButton2) challengeButton2.disabled = state.busy;
      }
    }

    document.getElementById("toggle-passwords").addEventListener("click", () => {
      state.visible = !state.visible;
      document.querySelectorAll("[data-pw]").forEach((input) => { input.type = state.visible ? "text" : "password"; });
      const button = document.getElementById("toggle-passwords");
      button.setAttribute("aria-label", state.visible ? "Hide passwords" : "Show passwords");
      button.innerHTML = `${icon(state.visible ? "eyeOff" : "eye", 17)} <span>${state.visible ? "Hide" : "Show"}</span>`;
    });

    document.getElementById("new-challenge").addEventListener("click", () => { showError(""); void loadChallenge(); });

    document.getElementById("login-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const passwords = [...document.querySelectorAll("[data-pw]")].map((input) => input.value);
      const answer = answerInput.value;
      if (passwords.some((value) => !value) || !answer.trim() || !state.challenge) {
        showError("Fill in all three passwords and solve the challenge.");
        return;
      }
      state.busy = true;
      showError("");
      submitButton.innerHTML = `Checking... ${icon("arrowRight", 18)}`;
      submitButton.disabled = true;
      try {
        const response = await fetch("/api/auth/login", {
          method: "POST",
          credentials: "same-origin",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ passwords, challengeId: state.challenge.id, answer }),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Sign-in failed. Please try again.");
        document.querySelectorAll("[data-pw]").forEach((input) => { input.value = ""; });
        answerInput.value = "";
        location.reload();
      } catch (issue) {
        showError(issue instanceof Error ? issue.message : "Sign-in failed. Please try again.");
        document.querySelectorAll("[data-pw]").forEach((input) => { input.value = ""; });
        await loadChallenge();
      } finally {
        state.busy = false;
        submitButton.innerHTML = `Enter studio ${icon("arrowRight", 18)}`;
        submitButton.disabled = !state.challenge;
      }
    });

    void loadChallenge();
  }

  // =====================================================================
  // Studio
  // =====================================================================
  const adminRoot = document.getElementById("admin-root");
  if (adminRoot) {
    const state = {
      loading: true,
      busy: false,
      pages: [],
      theme: null,
      revision: 0,
      publishedAt: null,
      media: [],
      versions: [],
      messages: [],
      visits: null,
      visitDraft: null,
      past: [],
      future: [],
      lastEditKey: "",
      lastEditAt: 0,
      autosaveTimer: null,
      autosaveState: "",
      saving: false,
      alert: null,
      selectedId: "home",
      section: "pages",
      dirty: false,
      notice: null,
      addOpen: false,
      publishOpen: false,
      newTitle: "",
      newSlug: "",
      newVisible: true,
      mobileNav: false,
      canvasSize: "desktop",
      selectedBlockId: null,
      adding: false,
      renaming: null,
      renameName: "",
      dragging: false,
    };

    const current = () => state.pages.find((item) => item.id === state.selectedId) || state.pages[0];
    const selectedBlock = () => {
      const page = current();
      return page ? page.blocks.find((block) => block.id === state.selectedBlockId) || null : null;
    };
    const mediaInfo = () => Object.fromEntries(state.media.map((item) => [item.id, { name: item.name, kind: item.kind, mime: item.mime, width: item.width, height: item.height }]));
    const unreadMessages = () => state.messages.filter((item) => !item.read).length;
    const whenText = (value) => { const date = new Date(value); return Number.isNaN(date.getTime()) ? "" : date.toLocaleString(); };
    const messageOf = (issue) => (issue instanceof Error ? issue.message : "Something went wrong. Try again.");

    // ---------- rendering ----------
    // Re-rendering replaces the DOM, which would throw away whatever the
    // cursor was in. Remember the focused control (and its caret and the
    // scroll position of the panes) so a redraw is invisible while typing.
    const SCROLL_KEEP = [".admin-body", "#inspector", ".canvas-content", ".editor-layout"];
    function focusSnapshot() {
      const el = document.activeElement;
      const scroll = SCROLL_KEEP.map((selector) => {
        const node = document.querySelector(selector);
        return node ? { selector, top: node.scrollTop } : null;
      }).filter(Boolean);
      const snapshot = { selector: null, start: null, end: null, scroll, window: window.scrollY };
      if (!el || !el.matches || !el.matches("input, textarea, select")) return snapshot;
      const d = el.dataset || {};
      const quote = (value) => String(value).replace(/"/g, '\\"');
      if (el.id) snapshot.selector = `#${el.id}`;
      else if (d.itemField !== undefined) snapshot.selector = `[data-item-field="${quote(d.itemField)}"][data-item-index="${quote(d.itemIndex)}"]`;
      else if (d.inspector !== undefined) snapshot.selector = `[data-inspector="${quote(d.inspector)}"]`;
      else if (d.inspectorNumber !== undefined) snapshot.selector = `[data-inspector-number="${quote(d.inspectorNumber)}"]`;
      else if (d.pageField !== undefined) snapshot.selector = `[data-page-field="${quote(d.pageField)}"]`;
      else if (d.range !== undefined) snapshot.selector = `[data-range="${quote(d.range)}"]`;
      else if (d.color !== undefined) snapshot.selector = `[data-color="${quote(d.color)}"]`;
      else if (d.themeField !== undefined) snapshot.selector = `[data-theme-field="${quote(d.themeField)}"]`;
      else if (d.visitInput !== undefined) snapshot.selector = "[data-visit-input]";
      try {
        snapshot.start = el.selectionStart;
        snapshot.end = el.selectionEnd;
      } catch { /* selection is not available on every input type */ }
      return snapshot;
    }

    function restoreFocus(snapshot) {
      if (!snapshot) return;
      snapshot.scroll.forEach(({ selector, top }) => {
        const node = document.querySelector(selector);
        if (node) node.scrollTop = top;
      });
      if (snapshot.window) window.scrollTo(0, snapshot.window);
      if (!snapshot.selector) return;
      const node = document.querySelector(snapshot.selector);
      if (!node || node === document.activeElement) return;
      node.focus({ preventScroll: true });
      if (snapshot.start !== null && snapshot.start !== undefined) {
        try { node.setSelectionRange(snapshot.start, snapshot.end); } catch { /* not a text field */ }
      }
    }

    function render() {
      if (state.loading) return;
      const focus = focusSnapshot();
      renderShell();
      restoreFocus(focus);
    }

    function renderShell() {
      adminRoot.className = "";
      const page = current();
      if (!state.theme || !page) {
        adminRoot.innerHTML = `<div class="admin-loading"><p>Couldn't load the workspace.</p><button type="button" data-action="retry">Try again</button>${state.notice ? `<span role="alert">${esc(state.notice.text)}</span>` : ""}</div>`;
        bindGlobalEvents();
        return;
      }
      const sectionLabel = state.section === "pages" ? "PAGES" : state.section.toUpperCase();
      const headerTitle =
        state.section === "pages" ? (page.id === "home" ? "Main / Home" : page.title)
        : state.section === "theme" ? "Make it yours."
        : state.section === "media" ? "Your media."
        : state.section === "messages" ? "Your messages."
        : state.section === "visits" ? "Your visits." : "Past versions.";
      const headerTag =
        state.section === "pages" ? "PAGE BUILDER" : state.section === "theme" ? "THEME EDITOR"
        : state.section === "media" ? "ASSET LIBRARY"
        : state.section === "messages" ? "PRIVATE INBOX"
        : state.section === "visits" ? "AUDIENCE" : "YOUR BACKUPS";
      const headerSub =
        state.section === "pages" ? "Arrange the details, then see how they all come together."
        : state.section === "theme" ? "One visual language for every page."
        : state.section === "media" ? "Everything you need to bring your pages to life."
        : state.section === "messages" ? "Notes people sent you from the contact form."
        : state.section === "visits" ? "How many people opened your pages."
        : "Go back without losing your way forward.";
      const navItem = (section, iconName, label, count) =>
        `<button type="button" class="admin-nav-item ${state.section === section ? "active" : ""}" data-nav="${section}">` +
        `${icon(iconName, 19)} ${label}${count !== undefined ? `<span class="admin-nav-count">${count}</span>` : ""}</button>`;

      const noticeHtml = state.notice
        ? `<div class="admin-notice ${state.notice.tone === "error" ? "error" : state.notice.tone === "info" ? "info" : ""}" role="${state.notice.tone === "error" ? "alert" : "status"}">` +
          `<span>${state.notice.tone === "success" ? icon("check", 17) : state.notice.tone === "error" ? icon("x", 17) : icon("sparkles", 17)}</span>` +
          `<p>${esc(state.notice.text)}</p>` +
          `<button type="button" data-action="dismiss-notice" aria-label="Dismiss message">${icon("x", 16)}</button></div>`
        : "";

      adminRoot.innerHTML = `
      <div class="admin-app">
        <header class="admin-mobile-header">
          <button type="button" data-action="open-mobile-nav" aria-label="Open workspace menu">${icon("menu", 21)}</button>
          <strong>hana<span>.</span> studio</strong>
          <button type="button" data-action="save" aria-label="Save draft" ${state.busy ? "disabled" : ""}>${icon("save", 20)}</button>
        </header>
        ${state.mobileNav ? `<button class="admin-scrim" type="button" data-action="close-mobile-nav" aria-label="Close workspace menu"></button>` : ""}
        <aside class="admin-sidebar ${state.mobileNav ? "open" : ""}">
          <div class="admin-brand">
            <span class="admin-brand-mark">h<span>.</span></span>
            <div><strong>hana. studio</strong><small>YOUR CREATIVE SPACE</small></div>
            <button type="button" class="admin-menu-close" data-action="close-mobile-nav" aria-label="Close menu">${icon("x", 18)}</button>
          </div>
          <div class="admin-sidebar-content">
            <span class="admin-nav-label">WORKSPACE</span>
            ${navItem("pages", "layoutTemplate", "Pages", state.pages.length)}
            <div class="admin-page-list">
              ${state.pages.map((item) =>
                `<button type="button" class="admin-page-item ${state.section === "pages" && state.selectedId === item.id ? "selected" : ""}" data-page="${esc(item.id)}">` +
                `<span class="page-list-dot"></span><span>${esc(item.id === "home" ? "Main / Home" : item.title)}</span>` +
                `${!item.visible ? `<span class="page-hidden-symbol" title="Hidden from navigation">\u25cb</span>` : ""}</button>`
              ).join("")}
              <button type="button" class="admin-add-page" data-action="add-page">${icon("plus", 15)} Add page</button>
            </div>
            ${navItem("theme", "settings2", "Theme")}
            ${navItem("media", "image", "Media library")}
            ${navItem("messages", "mail", "Messages", unreadMessages() || undefined)}
            ${navItem("visits", "barChart3", "Visits")}
            ${navItem("history", "history", "Version history")}
          </div>
          <div class="admin-sidebar-bottom">
            <div class="admin-sidebar-tip">${icon("sparkles", 19)}<span>Make something<br />that feels like you.</span></div>
            <a href="/" target="_blank" rel="noopener noreferrer" class="admin-view-site">${icon("externalLink", 17)} View public site</a>
            <button type="button" class="admin-logout" data-action="logout">${icon("logOut", 17)} Log out</button>
          </div>
        </aside>
        <div class="admin-main">
          <div class="admin-topbar">
            <div class="admin-breadcrumb">WORKSPACE <span>/</span> ${sectionLabel}</div>
            <div class="admin-topbar-right">
              <span class="draft-indicator ${state.dirty ? "unsaved" : ""}"><i></i>${state.dirty ? "Unsaved changes" : "Draft saved"}</span>
              <span class="topbar-avatar">H</span>
            </div>
          </div>
          <div class="admin-body">
            <div class="admin-page-header">
              <div>
                <div class="admin-header-tag"><span>\u2733</span> ${headerTag}</div>
                <h1>${esc(headerTitle)}</h1>
                <p>${esc(headerSub)}</p>
              </div>
              <div class="admin-header-actions">
                <button type="button" class="action-history" data-action="undo" ${state.past.length && !state.busy ? "" : "disabled"} title="Undo (Ctrl+Z)" aria-label="Undo">${icon("undo2", 16)}</button>
                <button type="button" class="action-history" data-action="redo" ${state.future.length && !state.busy ? "" : "disabled"} title="Redo (Ctrl+Shift+Z)" aria-label="Redo">${icon("redo2", 16)}</button>
                <button type="button" class="action-preview" data-action="preview" ${state.busy ? "disabled" : ""}>${icon("externalLink", 16)} Preview</button>
                <button type="button" class="action-save" data-action="save" ${state.busy ? "disabled" : ""}>${icon("save", 16)} Save draft</button>
                <button type="button" class="action-publish" data-action="publish-open" ${state.busy ? "disabled" : ""}>${icon("sparkles", 16)} Publish</button>
              </div>
            </div>
            ${noticeHtml}
            <div id="section-content"></div>
            <footer class="admin-footer"><span>HANA STUDIO <span>\u2733</span> PRIVATE WORKSPACE</span></footer>
          </div>
        </div>
        ${state.addOpen ? addPageModalHtml() : ""}
        ${state.publishOpen ? publishModalHtml() : ""}
        ${state.alert ? alertModalHtml() : ""}
      </div>`;
      renderSection();
      bindGlobalEvents();
    }

    function renderSection() {
      const slot = document.getElementById("section-content");
      if (!slot) return;
      if (state.section === "pages") renderPagesSection(slot);
      else if (state.section === "theme") renderThemeSection(slot);
      else if (state.section === "media") renderMediaSection(slot);
      else if (state.section === "messages") renderMessagesSection(slot);
      else if (state.section === "visits") renderVisitsSection(slot);
      else renderHistorySection(slot);
    }

    // ---------- pages section ----------
    function canvasHtml() {
      const page = current();
      if (!page) return "";
      if (!page.blocks.length) {
        return `<div class="canvas-empty"><span>\u2733</span><h4>A blank canvas, all yours.</h4><p>Add a block to start shaping this page.</p><button type="button" data-action="add-first-block">${icon("plus", 15)} Add your first block</button></div>`;
      }
      return page.blocks
        .map((block, index) =>
          `<div class="canvas-block ${state.selectedBlockId === block.id ? "selected" : ""}" role="button" tabindex="0" draggable="true" data-block="${esc(block.id)}" aria-label="Select ${BLOCK_NAMES[block.type]} block ${index + 1}, drag to reorder">` +
          `<span class="canvas-block-tag">${BLOCK_NAMES[block.type]}</span>` +
          `<span class="canvas-block-grip" title="Drag to reorder" aria-hidden="true">${icon("gripVertical", 15)}</span>` +
          contentBlocksHtml([block], {}, mediaInfo(), true) +
          `</div>`
        )
        .join("");
    }

    function renderCanvas() {
      const slot = document.getElementById("canvas-content");
      const shell = document.querySelector(".canvas-shell");
      const topline = document.querySelector(".canvas-topline");
      if (!slot) return;
      slot.innerHTML = canvasHtml();
      if (shell) shell.className = `canvas-shell canvas-${state.canvasSize}`;
      if (topline && current()) topline.children[1].textContent = `/${current().slug || ""}`;
      bindCanvasEvents();
    }

    function inspectorHtml() {
      const block = selectedBlock();
      const page = current();
      const theme = state.theme;
      if (!block) {
        return `<div class="inspector-heading"><span class="admin-kicker">PROPERTIES</span><h3>Select a block</h3><p>Choose a block on the canvas to edit it here.</p></div>`;
      }
      const type = block.type;
      const textHint =
        type === "list" ? "One item per line" : type === "code" ? "Paste or write your code" : type === "button" ? "Button label"
        : type === "image" ? "Optional caption" : type === "file" ? "Optional description" : type === "section" ? "Section heading"
        : type === "gallery" || type === "embed" ? "Optional caption"
        : "Write your content here...";
      const hasTitleField = ["card", "section", "file", "embed"].includes(type);
      const hasTextField = TEXT_TYPES.includes(type) || ["gallery", "embed"].includes(type);
      const textLabel = type === "image" ? "Caption" : type === "file" ? "Description" : type === "section" ? "Eyebrow label"
        : type === "gallery" || type === "embed" ? "Caption" : "Text";
      const hasUrlField = ["button", "card", "embed"].includes(type);
      const hasNewTab = ["button", "card", "heading", "paragraph", "quote", "list", "timeline"].includes(type);
      const hasMedia = ["image", "file"].includes(type);
      const embedInfo = type === "embed" ? parseEmbed(block.url || "") : null;
      const galleryPicker = state.media.filter((item) => item.kind === "image");
      const mediaOptions = state.media
        .filter((item) => (type === "image" ? item.kind === "image" : item.kind !== "image"))
        .map((item) => `<option key="${item.id}" value="${item.id}" ${item.id === block.mediaId ? "selected" : ""}>${esc(item.name)}</option>`)
        .join("");
      const content = `
        <div class="inspector-actions">
          <button type="button" data-block-action="up" ${page.blocks[0]?.id === block.id ? "disabled" : ""} title="Move up" aria-label="Move block up">${icon("arrowUp", 17)}</button>
          <button type="button" data-block-action="down" ${page.blocks.at(-1)?.id === block.id ? "disabled" : ""} title="Move down" aria-label="Move block down">${icon("arrowDown", 17)}</button>
          <button type="button" data-block-action="duplicate" title="Duplicate block" aria-label="Duplicate block">${icon("copy", 17)}</button>
          <button type="button" class="danger" data-block-action="remove" title="Remove block" aria-label="Remove block">${icon("trash2", 17)}</button>
        </div>
        <div class="inspector-section">
          <h4>Content</h4>
          ${hasTitleField ? `<label class="admin-field"><span>${type === "section" ? "Eyebrow label" : type === "embed" ? "Video title" : "Title / file label"}</span><input data-inspector="title" value="${esc(block.title)}" maxlength="200" placeholder="Title"></label>` : ""}
          ${hasTextField ? `<label class="admin-field"><span>${textLabel}</span><textarea id="block-text-input" data-inspector="text" placeholder="${esc(textHint)}" rows="${type === "code" ? 9 : 5}" maxlength="16000">${esc(block.text)}</textarea></label>` : ""}
          ${["heading", "paragraph", "quote", "list", "card"].includes(type) ? `<div class="format-toolbar" role="toolbar" aria-label="Text formatting">
            <button type="button" data-markup="**" title="Bold" aria-label="Bold selected text">${icon("bold", 15)}</button>
            <button type="button" data-markup="*" title="Italic" aria-label="Italic selected text">${icon("italic", 15)}</button>
            <button type="button" data-markup="\`" title="Inline code" aria-label="Format selected text as code">${icon("code2", 15)}</button>
            <button type="button" data-markup="link" title="Insert link" aria-label="Link selected text">${icon("link2", 15)}</button>
            <span>Use **bold**, *italic*, \`code\` or [links](url).</span>
          </div>` : ""}
          ${type === "heading" ? `<label class="admin-field"><span>Heading level</span><select data-inspector="level">
            <option value="1" ${block.level === 1 ? "selected" : ""}>H1 — Page heading</option>
            <option value="2" ${block.level === 2 ? "selected" : ""}>H2 — Section heading</option>
            <option value="3" ${block.level === 3 ? "selected" : ""}>H3 — Subheading</option>
          </select></label>` : ""}
          ${hasUrlField ? `<label class="admin-field"><span>${type === "embed" ? "Video link" : "Link destination"}</span><input data-inspector="url" value="${esc(block.url)}" placeholder="${type === "embed" ? "https://youtu.be/... or a .mp4 link" : "/about, #work or https://..."}" maxlength="500"></label>` : ""}
          ${type === "embed" ? `<p class="inspector-hint ${embedInfo.kind && embedInfo.kind !== "link" ? "good" : ""}">${
            !embedInfo.kind ? "Paste a YouTube, Vimeo or direct video link."
            : embedInfo.kind === "link" ? "That link isn't a video — it will show as a button instead."
            : `${embedInfo.label} detected. Nothing loads from ${embedInfo.label} until a visitor presses play.`}</p>` : ""}
          ${type === "timeline" ? timelineEditorHtml(block) : ""}
          ${type === "gallery" ? galleryEditorHtml(block, galleryPicker) : ""}
          ${hasNewTab ? `<label class="admin-checkbox"><input type="checkbox" data-inspector="newTab" ${block.newTab ? "checked" : ""}><span><strong>Open links in a new tab</strong><small>Also applies to inline links in this block.</small></span></label>` : ""}
          ${hasMedia ? `
            <label class="admin-field"><span>${type === "image" ? "Image" : "File or video"}</span>
              <select data-inspector="mediaId"><option value="">Choose an upload</option>${mediaOptions}</select></label>
            <label class="inspector-upload">${icon("fileUp", 16)} Upload a new ${type === "image" ? "image" : "file"}
              <input type="file" data-inspector="upload" ${type === "image" ? 'accept="image/png,image/jpeg,image/webp,image/gif,image/avif"' : ""}></label>
            <label class="admin-field"><span>${type === "image" ? "Alt text (describe the image)" : "Video description / accessible label"}</span>
              <input data-inspector="alt" value="${esc(block.alt)}" placeholder="Describe what this shows" maxlength="250"></label>
            ${type === "file" ? `<label class="admin-checkbox"><input type="checkbox" data-inspector="showDownload" ${block.showDownload !== false ? "checked" : ""}><span><strong>Show Download button</strong><small>Videos remain playable either way.</small></span></label>` : ""}` : ""}
        </div>
        <div class="inspector-section">
          <h4>Appearance</h4>
          <label class="admin-field"><span>Text size</span><select data-inspector="size">
            <option value="sm" ${block.size === "sm" ? "selected" : ""}>Small</option>
            <option value="md" ${block.size === "md" ? "selected" : ""}>Medium</option>
            <option value="lg" ${block.size === "lg" ? "selected" : ""}>Large</option>
            <option value="xl" ${block.size === "xl" ? "selected" : ""}>Extra large</option>
          </select></label>
          <div class="admin-field"><span>Alignment</span><div class="alignment-group">
            ${["left", "center", "right"].map((value) => `<button type="button" data-align="${value}" class="${block.align === value ? "selected" : ""}" title="Align ${value}" aria-label="Align ${value}">${icon({ left: "alignLeft", center: "alignCenter", right: "alignRight" }[value], 17)}</button>`).join("")}
          </div></div>
          ${type !== "spacer" ? `<label class="admin-range"><span>Width <b data-range-label="width">${block.width}%</b></span><input type="range" data-range="width" min="20" max="100" step="5" value="${block.width}"></label>` : ""}
          <label class="admin-range"><span>${type === "spacer" ? "Height" : "Space below"} <b data-range-label="spacing">${block.spacing}px</b></span><input type="range" data-range="spacing" min="0" max="120" step="4" value="${block.spacing}"></label>
          <label class="admin-range"><span>Margin above <b data-range-label="marginTop">${block.marginTop}px</b></span><input type="range" data-range="marginTop" min="0" max="120" step="4" value="${block.marginTop}"></label>
          <label class="admin-range"><span>Inner padding <b data-range-label="padding">${block.padding}px</b></span><input type="range" data-range="padding" min="0" max="100" step="4" value="${block.padding}"></label>
          <label class="admin-field"><span>Block font</span><select data-inspector="fontOverride">
            <option value="inherit" ${block.fontOverride === "inherit" ? "selected" : ""}>Use site font</option>
            ${FONT_CHOICES.map((font) => `<option value="${font}" ${block.fontOverride === font ? "selected" : ""}>${FONT_LABELS[font]}</option>`).join("")}
          </select></label>
          <div class="block-color-grid">
            <label class="admin-field"><span>Text color</span><input type="color" data-color="color" value="${esc(block.color || theme.text)}"></label>
            <label class="admin-field"><span>Background</span><input type="color" data-color="background" value="${esc(block.background || theme.surface)}"></label>
          </div>
          <div class="reset-colors">
            <button type="button" data-reset-color="color">${icon("rotateCcw", 13)} Reset text</button>
            <button type="button" data-reset-color="background">${icon("rotateCcw", 13)} Reset background</button>
          </div>
        </div>`;
      return `
        <div class="inspector-heading"><span class="admin-kicker">PROPERTIES</span><h3>${BLOCK_NAMES[type]}</h3><p>Make this block yours.</p></div>
        <div class="inspector-body">${content}</div>`;
    }

    function timelineEditorHtml(block) {
      const items = block.items || [];
      const rows = items.map((item, index) => `
        <div class="timeline-row" data-item-row="${index}" draggable="false">
          <div class="timeline-row-head">
            <span>${index + 1}</span>
            <div>
              <button type="button" data-item-move="${index}" data-item-dir="-1" ${index === 0 ? "disabled" : ""} title="Move entry up" aria-label="Move entry up">${icon("arrowUp", 14)}</button>
              <button type="button" data-item-move="${index}" data-item-dir="1" ${index === items.length - 1 ? "disabled" : ""} title="Move entry down" aria-label="Move entry down">${icon("arrowDown", 14)}</button>
              <button type="button" class="danger" data-item-remove="${index}" title="Remove entry" aria-label="Remove entry">${icon("trash2", 14)}</button>
            </div>
          </div>
          <input data-item-field="label" data-item-index="${index}" value="${esc(item.label || "")}" maxlength="40" placeholder="2026 — or any date">
          <input data-item-field="title" data-item-index="${index}" value="${esc(item.title || "")}" maxlength="120" placeholder="What happened">
          <textarea data-item-field="text" data-item-index="${index}" rows="2" maxlength="600" placeholder="A line about it (optional)">${esc(item.text || "")}</textarea>
        </div>`).join("");
      return `
        <div class="admin-field"><span>Milestones</span>
          <div class="timeline-editor">${rows || `<p class="inspector-hint">No entries yet.</p>`}</div>
          <button type="button" class="inspector-add" data-item-add ${items.length >= MAX_TIMELINE_ITEMS ? "disabled" : ""}>${icon("plus", 14)} Add a milestone</button>
        </div>`;
    }

    function galleryEditorHtml(block, images) {
      const chosen = (block.mediaIds || []).filter(Boolean);
      const picked = chosen.map((id, index) => {
        const item = images.find((entry) => entry.id === id);
        return `
          <div class="gallery-row" data-gallery-row="${index}">
            <img src="/api/media/${esc(id)}" alt="">
            <span>${esc(item ? item.name : "Missing upload")}</span>
            <button type="button" data-gallery-move="${index}" data-gallery-dir="-1" ${index === 0 ? "disabled" : ""} title="Move left" aria-label="Move image earlier">${icon("arrowUp", 14)}</button>
            <button type="button" data-gallery-move="${index}" data-gallery-dir="1" ${index === chosen.length - 1 ? "disabled" : ""} title="Move right" aria-label="Move image later">${icon("arrowDown", 14)}</button>
            <button type="button" class="danger" data-gallery-remove="${index}" title="Remove from gallery" aria-label="Remove from gallery">${icon("x", 14)}</button>
          </div>`;
      }).join("");
      const options = images.filter((item) => !chosen.includes(item.id))
        .map((item) => `<option value="${esc(item.id)}">${esc(item.name)}</option>`).join("");
      return `
        <div class="admin-field"><span>Images (${chosen.length}/${MAX_GALLERY_IMAGES})</span>
          <div class="gallery-editor">${picked || `<p class="inspector-hint">No images picked yet.</p>`}</div>
          ${chosen.length >= MAX_GALLERY_IMAGES ? "" : `<select data-gallery-add><option value="">Add an image…</option>${options}</select>`}
          <label class="inspector-upload">${icon("fileUp", 16)} Upload images to the gallery
            <input type="file" data-gallery-upload multiple accept="image/png,image/jpeg,image/webp,image/gif,image/avif"></label>
        </div>
        <label class="admin-field"><span>Columns</span><select data-inspector-number="columns">
          ${[2, 3, 4].map((value) => `<option value="${value}" ${(block.columns || 3) === value ? "selected" : ""}>${value} across</option>`).join("")}
        </select></label>`;
    }

    function renderInspector() {
      const panel = document.getElementById("inspector");
      if (!panel) return;
      panel.innerHTML = inspectorHtml();
      bindInspectorEvents();
    }

    function renderPagesSection(slot) {
      const page = current();
      const theme = state.theme;
      slot.innerHTML = `
        <div class="page-utility">
          <span>${icon("fileStack", 15)} <span data-page-path>${page.id === "home" ? "/" : `/${esc(page.slug)}`}</span> <i>\u00b7</i>
          <span data-page-visibility>${page.visible ? "In navigation" : "Hidden from navigation"}</span></span>
          <div>
            <button type="button" data-action="page-up" ${page.id === "home" || state.pages[1]?.id === page.id ? "disabled" : ""} title="Move page up">${icon("arrowUp", 15)}</button>
            <button type="button" data-action="page-down" ${page.id === "home" || state.pages.at(-1)?.id === page.id ? "disabled" : ""} title="Move page down">${icon("arrowDown", 15)}</button>
            <button type="button" data-action="page-duplicate" title="Duplicate page">${icon("copy", 15)}<span>Duplicate</span></button>
            <button type="button" class="danger" data-action="page-delete" title="${page.id === "home" ? "Reset Home" : "Delete page"}">${icon("trash2", 15)}<span>${page.id === "home" ? "Reset" : "Delete"}</span></button>
          </div>
        </div>
        <div class="editor-layout">
          <div class="editor-main">
            <div class="workspace-card page-settings">
              <div class="workspace-card-heading">
                <div><span class="admin-kicker">PAGE DETAILS</span><h3 data-settings-title>${page.id === "home" ? "Main / Home" : esc(page.title)}</h3></div>
                <span class="settings-symbol">\u2733</span>
              </div>
              <div class="page-fields">
                <label class="admin-field"><span>Page title</span><input data-page-field="title" value="${esc(page.title)}" maxlength="100" placeholder="Page title"></label>
                <label class="admin-field"><span>URL / slug</span><div class="url-field"><span>/</span>
                  <input data-page-field="slug" value="${esc(page.slug)}" ${page.id === "home" ? "disabled" : ""} maxlength="65" placeholder="${page.id === "home" ? "home" : "about"}"></div></label>
                <label class="admin-field page-description-field"><span>Meta description</span>
                  <input data-page-field="description" value="${esc(page.description)}" maxlength="260" placeholder="A short description for search and sharing"></label>
                <label class="admin-checkbox page-visibility"><input type="checkbox" data-page-field="visible" ${page.visible ? "checked" : ""}>
                  <span><strong>Show in All Pages navigation</strong><small>Hidden pages still work with their direct URL.</small></span></label>
              </div>
            </div>
            <div class="canvas-heading">
              <div><span class="admin-kicker">THE CANVAS</span><h3>Build your page <span>\u2733</span></h3></div>
              <div class="device-toggle" role="group" aria-label="Canvas width">
                <button type="button" data-device="desktop" class="${state.canvasSize === "desktop" ? "selected" : ""}">Desktop</button>
                <button type="button" data-device="mobile" class="${state.canvasSize === "mobile" ? "selected" : ""}">Mobile</button>
              </div>
            </div>
            <div class="canvas-shell canvas-${state.canvasSize}">
              <div class="admin-canvas ${siteClasses(theme)}" style="${themeStyleVars(theme)}">
                <div class="canvas-topline"><span>h.</span><span>/${esc(page.slug || "")}</span><span>\u2733</span></div>
                <div class="canvas-content" id="canvas-content">${canvasHtml()}</div>
                <div class="canvas-bottom">HANA HAMAMATO <span>\u2733</span></div>
              </div>
            </div>
            <div class="block-add-area">
              <button type="button" class="block-add-trigger" data-action="toggle-add" aria-expanded="${state.adding}">${icon("plus", 18)} Add a block ${icon("chevronDown", 16, 2).replace("<svg", `<svg class="${state.adding ? "rotate" : ""}"`)}</button>
              ${state.adding ? `<div class="block-palette">${BLOCK_TYPES.map((type) => `<button type="button" data-add-block="${type}">${icon(BLOCK_ICONS[type], 18, 1.7)}<span>${BLOCK_NAMES[type]}</span></button>`).join("")}</div>` : ""}
            </div>
          </div>
          <aside class="inspector-panel" id="inspector">${inspectorHtml()}</aside>
        </div>`;
      syncPageMeta();
      bindCanvasEvents();
      bindPageSectionEvents();
      bindInspectorEvents();
    }

    function syncPageMeta() {
      const page = current();
      if (!page) return;
      const set = (selector, value) => document.querySelectorAll(selector).forEach((node) => { node.textContent = value; });
      set("[data-page-path]", page.id === "home" ? "/" : `/${page.slug}`);
      set("[data-page-visibility]", page.visible ? "In navigation" : "Hidden from navigation");
      set("[data-settings-title]", page.id === "home" ? "Main / Home" : page.title);
      const heading = document.querySelector(".admin-page-header h1");
      if (heading && state.section === "pages") heading.textContent = page.id === "home" ? "Main / Home" : page.title;
      document.querySelectorAll("[data-page]").forEach((node) => {
        if (node.dataset.page === page.id) {
          const label = node.children[1];
          if (label) label.textContent = page.id === "home" ? "Main / Home" : page.title;
        }
      });
      const topline = document.querySelector(".canvas-topline");
      if (topline) topline.children[1].textContent = `/${page.slug || ""}`;
    }

    // ---------- theme section ----------
    const DARK_PALETTE = { background: "#191724", surface: "#252132", text: "#f6f1fb", muted: "#b2a7c2", accent: "#b993ed" };
    const LIGHT_PALETTE = { background: "#f8f6fc", surface: "#ffffff", text: "#29233a", muted: "#786f88", accent: "#7956c4" };

    function renderThemeSection(slot) {
      const theme = state.theme;
      const page = current();
      const paletteRows = [
        ["background", "Background"], ["surface", "Surface / cards"], ["text", "Text"],
        ["muted", "Secondary text"], ["accent", "Accent"],
      ]
        .map(([key, label]) =>
          `<label class="theme-color-row"><span>${label}</span><span><input type="color" data-theme-color="${key}" value="${esc(theme[key])}"><code data-theme-code="${key}">${esc(theme[key])}</code></span></label>`
        )
        .join("");
      const previewInner = page.blocks.length
        ? `<div class="theme-preview-blocks">${contentBlocksHtml(page.blocks.slice(0, 3), {}, mediaInfo(), true)}</div>`
        : `<h3>Main Page Hasn't Been <em>Configured</em> Yet<span>.</span></h3><p>I will post here soon, apologize! 😭</p><span class="theme-preview-button">A little detail ${icon("arrowRight", 13)}</span>`;
      slot.innerHTML = `
        <div class="theme-layout">
          <div class="theme-controls">
            <div class="workspace-card">
              <span class="admin-kicker">SITE-WIDE APPEARANCE</span>
              <h3>Set the mood <span class="theme-heading-star">\u2733</span></h3>
              <p class="panel-intro">A change here carries through every page, including the sidebar.</p>
              <div class="setting-group"><h4>Color mode</h4>
                <div class="segmented-control">
                  <button type="button" data-mode="light" class="${theme.mode === "light" ? "selected" : ""}">\u2600 Light</button>
                  <button type="button" data-mode="dark" class="${theme.mode === "dark" ? "selected" : ""}">\u263e Dark</button>
                </div>
              </div>
              <div class="setting-group"><h4>Colors</h4><div class="theme-color-list">${paletteRows}</div></div>
              <div class="setting-group"><h4>Default font</h4>
                <p class="setting-hint">Visitors can still choose their own from the public sidebar.</p>
                <div class="theme-font-list">
                  ${FONT_CHOICES.map((font) =>
                    `<button type="button" class="theme-font-option ${theme.font === font ? "selected" : ""}" data-theme-font="${font}">` +
                    `<span class="font-${font}">Aa</span><strong>${FONT_LABELS[font]}</strong><i>${theme.font === font ? "\u2713" : ""}</i></button>`
                  ).join("")}
                </div>
              </div>
            </div>
            <div class="workspace-card">
              <span class="admin-kicker">THE DETAILS</span>
              <h3>Shape &amp; motion</h3>
              <div class="setting-group">
                <label class="admin-range"><span>Heading scale <b data-range-label="headingScale">${Math.round(theme.headingScale * 100)}%</b></span><input type="range" data-theme-range="headingScale" min="0.8" max="1.5" step="0.05" value="${theme.headingScale}"></label>
                <label class="admin-range"><span>Page spacing <b data-range-label="spacing">${Math.round(theme.spacing * 100)}%</b></span><input type="range" data-theme-range="spacing" min="0.8" max="1.5" step="0.05" value="${theme.spacing}"></label>
                <label class="admin-range"><span>Corner radius <b data-range-label="radius">${theme.radius}px</b></span><input type="range" data-theme-range="radius" min="0" max="36" step="2" value="${theme.radius}"></label>
                <label class="admin-range"><span>Border width <b data-range-label="borderWidth">${theme.borderWidth}px</b></span><input type="range" data-theme-range="borderWidth" min="0" max="3" step="1" value="${theme.borderWidth}"></label>
              </div>
              <div class="theme-selects">
                <label class="admin-field"><span>Shadows</span><select data-theme-select="shadow">
                  ${["soft:Soft", "crisp:Crisp", "none:None"].map((entry) => { const [value, label] = entry.split(":"); return `<option value="${value}" ${theme.shadow === value ? "selected" : ""}>${label}</option>`; }).join("")}
                </select></label>
                <label class="admin-field"><span>Cards</span><select data-theme-select="cardStyle">
                  ${["elevated:Elevated", "outline:Outlined", "flat:Flat"].map((entry) => { const [value, label] = entry.split(":"); return `<option value="${value}" ${theme.cardStyle === value ? "selected" : ""}>${label}</option>`; }).join("")}
                </select></label>
                <label class="admin-field"><span>Buttons</span><select data-theme-select="buttonStyle">
                  ${["solid:Solid", "outline:Outline", "soft:Soft"].map((entry) => { const [value, label] = entry.split(":"); return `<option value="${value}" ${theme.buttonStyle === value ? "selected" : ""}>${label}</option>`; }).join("")}
                </select></label>
                <label class="admin-field"><span>Scroll animation</span><select data-theme-select="animation">
                  ${["subtle:Subtle", "expressive:Expressive", "off:Off"].map((entry) => { const [value, label] = entry.split(":"); return `<option value="${value}" ${theme.animation === value ? "selected" : ""}>${label}</option>`; }).join("")}
                </select></label>
              </div>
            </div>
          </div>
          <div class="theme-preview-column">
            <div class="theme-preview-sticky">
              <div class="theme-preview-label"><span>LIVE THEME PREVIEW</span><span>\u2733</span></div>
              <div id="theme-preview" class="theme-preview ${siteClasses(theme)}" style="${themeStyleVars(theme)}">
                <div class="theme-preview-sidebar"><span>h.</span><div><i></i> Home</div><div><i></i> All pages</div><div><i></i> Fonts</div></div>
                <div class="theme-preview-body">
                  <span class="theme-preview-top">${page.slug ? esc(page.title.toUpperCase()) : "Home"}</span>
                  <div class="theme-preview-inner">
                    ${previewInner}
                  </div>
                </div>
              </div>
              <p class="theme-preview-caption">Changes here are a draft until you press Publish.</p>
            </div>
          </div>
        </div>`;
      bindThemeSectionEvents();
    }

    function renderThemePreview() {
      const target = document.getElementById("theme-preview");
      const theme = state.theme;
      const page = current();
      if (!target || !page) return;
      const previewInner = page.blocks.length
        ? `<div class="theme-preview-blocks">${contentBlocksHtml(page.blocks.slice(0, 3), {}, mediaInfo(), true)}</div>`
        : `<h3>Main Page Hasn't Been <em>Configured</em> Yet<span>.</span></h3><p>I will post here soon, apologize! 😭</p><span class="theme-preview-button">A little detail ${icon("arrowRight", 13)}</span>`;
      target.className = `theme-preview ${siteClasses(theme)}`;
      target.setAttribute("style", themeStyleVars(theme));
      const body = target.querySelector(".theme-preview-body");
      if (body) {
        body.innerHTML = `
          <span class="theme-preview-top">${page.slug ? esc(page.title.toUpperCase()) : "Home"}</span>
          <div class="theme-preview-inner">
            ${previewInner}
          </div>`;
      }
    }

    // ---------- media section ----------
    function renderMediaSection(slot) {
      const media = state.media;
      const cards = media
        .map((asset) => {
          const thumb =
            asset.kind === "image" ? `<img src="/api/media/${asset.id}" alt="${esc(asset.name)}" loading="lazy">`
            : asset.kind === "video" ? icon("play", 30) : icon("fileText", 30);
          const info =
            state.renaming === asset.id
              ? `<form data-rename-form="${asset.id}"><input data-rename-input autofocus value="${esc(state.renameName)}" maxlength="110" aria-label="New file name"><button type="submit" ${state.busy || !state.renameName.trim() ? "disabled" : ""}>Save</button></form>`
              : `<strong title="${esc(asset.name)}">${esc(asset.name)}</strong>`;
          return `
            <article class="media-card">
              <div class="media-thumb">${thumb}</div>
              <div class="media-card-info">${info}<small>${asset.kind.toUpperCase()} \u00b7 ${(asset.bytes / (1024 * 1024)).toFixed(2)} MB</small></div>
              <div class="media-actions">
                <button type="button" data-rename="${asset.id}" title="Rename" aria-label="Rename ${esc(asset.name)}" ${state.busy ? "disabled" : ""}>${icon("pencil", 15)}</button>
                <label title="Replace" aria-label="Replace ${esc(asset.name)}">${icon("rotateCcw", 15)}<input type="file" data-replace="${asset.id}" ${state.busy ? "disabled" : ""}></label>
                <a title="Download" aria-label="Download ${esc(asset.name)}" href="/api/media/${asset.id}" download="${esc(asset.name)}">${icon("arrowDownToLine", 15)}</a>
                <button type="button" data-delete-media="${asset.id}" title="Delete" aria-label="Delete ${esc(asset.name)}" class="danger" ${state.busy ? "disabled" : ""}>${icon("trash2", 15)}</button>
              </div>
            </article>`;
        })
        .join("");
      slot.innerHTML = `
        <div class="media-panel">
          <div class="workspace-card media-intro">
            <div><span class="admin-kicker">YOUR LIBRARY</span><h3>Files &amp; images <span>\u2733</span></h3>
              <p>Keep the pieces of your pages here. Images are optimized; other files are available as downloads.</p></div>
            <span class="media-count">${media.length} ${media.length === 1 ? "upload" : "uploads"}</span>
          </div>
          <label class="media-dropzone ${state.dragging ? "dragging" : ""}" data-dropzone>
            ${icon("uploadCloud", 28, 1.5)}
            <strong>Drop files here, or choose from your device</strong>
            <span>Images, GIFs, video, PDFs, documents, archives and text \u00b7 up to 32 MB</span>
            <span class="media-browse">Browse files ${icon("arrowRight", 15)}</span>
            <input type="file" multiple data-media-upload ${state.busy ? "disabled" : ""}>
          </label>
          ${media.length
            ? `<div class="media-grid">${cards}</div>`
            : `<div class="media-empty">${icon("image", 27)}<strong>No uploads yet</strong><span>Your images and files will show up here.</span></div>`}
        </div>`;
      bindMediaSectionEvents();
    }

    // ---------- messages section ----------
    function renderMessagesSection(slot) {
      const unread = unreadMessages();
      const cards = state.messages
        .map(
          (message) => `
            <article class="message-card ${message.read ? "" : "unread"}">
              <div class="message-head">
                <span class="message-from">${icon(message.read ? "mailOpen" : "mail", 15)}
                  <strong>${message.name ? esc(message.name) : "Anonymous Message"}</strong></span>
                <span class="message-when">${esc(whenText(message.createdAt))}</span>
              </div>
              <p class="message-body">${esc(message.body).replace(/\n/g, "<br>")}</p>
              <div class="message-actions">
                <button type="button" data-message-read="${message.id}" data-message-value="${message.read ? "unread" : "read"}" ${state.busy ? "disabled" : ""}>
                  ${icon(message.read ? "rotateCcw" : "check", 14)} ${message.read ? "Mark as unread" : "Mark as read"}</button>
                <button type="button" class="danger" data-message-delete="${message.id}" ${state.busy ? "disabled" : ""}>${icon("trash2", 14)} Delete</button>
              </div>
            </article>`
        )
        .join("");
      slot.innerHTML = `
        <div class="messages-panel">
          <div class="workspace-card media-intro">
            <div><span class="admin-kicker">PRIVATE INBOX</span><h3>Messages <span>\u2733</span></h3>
              <p>Only you can read these. Visitors never see each other's notes.</p></div>
            <span class="media-count">${unread} unread</span>
          </div>
          ${state.messages.length
            ? `<div class="message-list">${cards}</div>`
            : `<div class="media-empty">${icon("mail", 27)}<strong>No messages yet</strong><span>Notes from your contact form will show up here.</span></div>`}
        </div>`;
      bindMessagesSectionEvents();
    }

    // ---------- visits section ----------
    function renderVisitsSection(slot) {
      const visits = state.visits || { displayedTotal: 0, realTotal: 0, offset: 0, pages: [] };
      const target = state.visitDraft === null ? String(visits.displayedTotal) : state.visitDraft;
      const rows = visits.pages
        .map(
          (row) => `
            <div class="visit-row">
              <span class="visit-path">${esc(row.path)}${row.title ? ` <i>${esc(row.title)}</i>` : ""}</span>
              <span class="visit-number">${row.visits}</span>
            </div>`
        )
        .join("");
      slot.innerHTML = `
        <div class="visits-panel">
          <div class="workspace-card">
            <span class="admin-kicker">SHOWN ON YOUR PAGES</span>
            <h3>Visit counter <span>\u2733</span></h3>
            <p class="panel-intro">Every new visitor adds one. The same person reloading a page is not counted again.</p>
            <div class="visit-stats">
              <div class="visit-stat"><strong>${visits.displayedTotal}</strong><span>SHOWN TOTAL</span></div>
              <div class="visit-stat"><strong>${visits.realTotal}</strong><span>REAL VISITS</span></div>
              <div class="visit-stat"><strong>${visits.offset >= 0 ? "+" : ""}${visits.offset}</strong><span>STARTING POINT</span></div>
            </div>
            <form class="visit-form" data-visit-form>
              <label class="admin-field"><span>Set the number your pages show</span>
                <input type="number" data-visit-input min="0" max="1000000000" step="1" value="${esc(target)}"></label>
              <button type="submit" ${state.busy ? "disabled" : ""}>${icon("save", 15)} Save</button>
            </form>
          </div>
          <div class="workspace-card">
            <span class="admin-kicker">PAGE BY PAGE</span>
            <h3>Where they went</h3>
            ${visits.pages.length
              ? `<div class="visit-rows">${rows}</div>`
              : `<p class="panel-intro">No visits recorded yet.</p>`}
          </div>
        </div>`;
      bindVisitsSectionEvents();
    }

    // ---------- history section ----------
    function renderHistorySection(slot) {
      const items = state.versions
        .map(
          (version) => `
            <div class="history-item">
              <span class="history-marker">${icon("clock3", 16)}</span>
              <div><strong>${esc(new Date(version.publishedAt).toLocaleString())}</strong>
              <span>${version.pageCount} ${version.pageCount === 1 ? "page" : "pages"} \u00b7 saved publication</span></div>
              <button type="button" data-restore="${version.id}" ${state.busy ? "disabled" : ""}>${icon("rotateCcw", 15)} Restore to draft</button>
            </div>`
        )
        .join("");
      slot.innerHTML = `
        <div class="history-panel">
          <div class="workspace-card">
            <span class="admin-kicker">SAFETY NET</span><h3>Version history <span>\u2733</span></h3>
            <p class="panel-intro">Every new publication keeps the previous one. Restoring puts a version back into your draft; publish again when you're ready.</p>
          </div>
          <div class="history-timeline">
            <div class="history-item current">
              <span class="history-marker">${icon("sparkles", 16)}</span>
              <div><strong>Currently published</strong><span>${state.publishedAt ? esc(new Date(state.publishedAt).toLocaleString()) : "Nothing published yet"}</span></div>
              <span class="history-current-label">LIVE</span>
            </div>
            ${items}
            ${!state.versions.length ? `<div class="history-empty">Earlier publications will appear here after your second publish.</div>` : ""}
          </div>
        </div>`;
    }

    // ---------- modals ----------
    function addPageModalHtml() {
      return `
        <div class="admin-modal-overlay" data-overlay="add">
          <div class="admin-modal" role="dialog" aria-modal="true" aria-labelledby="add-page-title">
            <button type="button" class="modal-close" data-action="add-cancel" aria-label="Close">${icon("x", 19)}</button>
            <span class="modal-icon">${icon("plus", 21)}</span>
            <span class="admin-kicker">A NEW CORNER</span>
            <h2 id="add-page-title">Add a page<span>.</span></h2>
            <p>Start with a name and a place for it to live.</p>
            <form data-add-form>
              <label class="admin-field"><span>Page title</span>
                <input data-add-title autofocus value="${esc(state.newTitle)}" maxlength="100" placeholder="About" required></label>
              <label class="admin-field"><span>URL / slug</span>
                <div class="url-field"><span>/</span><input data-add-slug value="${esc(state.newSlug)}" maxlength="65" placeholder="about" required></div></label>
              <label class="admin-checkbox"><input type="checkbox" data-add-visible ${state.newVisible ? "checked" : ""}>
                <span><strong>Show in All Pages navigation</strong><small>You can change this later.</small></span></label>
              <div class="modal-actions">
                <button type="button" data-action="add-cancel">Cancel</button>
                <button type="submit">Create page ${icon("arrowRight", 16)}</button>
              </div>
            </form>
          </div>
        </div>`;
    }

    function publishModalHtml() {
      return `
        <div class="admin-modal-overlay" data-overlay="publish">
          <div class="admin-modal" role="dialog" aria-modal="true" aria-labelledby="publish-title">
            <button type="button" class="modal-close" data-action="publish-cancel" aria-label="Close">${icon("x", 19)}</button>
            <span class="modal-icon">${icon("sparkles", 21)}</span>
            <span class="admin-kicker">READY WHEN YOU ARE</span>
            <h2 id="publish-title">Publish your site<span>?</span></h2>
            <p>Your draft ${state.dirty ? "will be saved and then " : "will "}go live. The previous published version will be kept in history.</p>
            <div class="publish-summary">
              <span>${icon("fileStack", 17)} ${state.pages.length} ${state.pages.length === 1 ? "page" : "pages"}</span>
              <span>${icon("clock3", 17)} Previous version backed up</span>
            </div>
            <div class="modal-actions">
              <button type="button" data-action="publish-cancel">Not yet</button>
              <button type="button" data-action="publish-confirm">Publish now ${icon("arrowRight", 16)}</button>
            </div>
          </div>
        </div>`;
    }

    function alertModalHtml() {
      return `
        <div class="admin-modal-overlay" data-overlay="alert">
          <div class="admin-modal" role="alertdialog" aria-modal="true" aria-labelledby="alert-title">
            <button type="button" class="modal-close" data-action="alert-close" aria-label="Close">${icon("x", 18)}</button>
            <div class="modal-icon warn">${icon("alertTriangle", 22)}</div>
            <h2 id="alert-title">${esc(state.alert.title)}</h2>
            <p>${esc(state.alert.text)}</p>
            <div class="modal-actions">
              <button type="button" data-action="alert-close">Got it</button>
            </div>
          </div>
        </div>`;
    }

    // ---------- state transitions ----------
    function changePages(next, editKey) {
      pushHistory(editKey);
      state.pages = next;
      afterChange();
    }
    function changeTheme(next, editKey) {
      pushHistory(editKey);
      state.theme = next;
      afterChange();
    }
    function afterChange() {
      state.dirty = true;
      state.notice = null;
      // The notice is part of the shell; drop it without a full redraw so
      // typing never rebuilds (and never unfocuses) the editor.
      document.querySelector(".admin-notice")?.remove();
      state.autosaveState = "";
      updateDraftIndicator();
      updateHistoryButtons();
      scheduleAutosave();
    }
    function updateDraftIndicator() {
      const el = document.querySelector(".draft-indicator");
      if (!el) return;
      el.classList.toggle("unsaved", state.dirty && state.autosaveState !== "saving");
      el.classList.toggle("autosaving", state.autosaveState === "saving");
      el.classList.toggle("autofailed", state.autosaveState === "error");
      const textNode = el.childNodes[1];
      const label =
        state.autosaveState === "saving" ? "Saving\u2026"
        : state.autosaveState === "error" ? "Couldn't autosave \u2014 press Save draft"
        : state.autosaveState === "waiting" ? "Waiting to autosave\u2026"
        : state.dirty ? "Unsaved changes"
        : state.autosaveState === "saved" ? "Saved automatically" : "Draft saved";
      if (textNode && textNode.nodeType === 3) textNode.nodeValue = label;
    }

    // ---------- undo / redo ----------
    function snapshotState() {
      return {
        pages: JSON.parse(JSON.stringify(state.pages)),
        theme: { ...state.theme },
        selectedId: state.selectedId,
        selectedBlockId: state.selectedBlockId,
      };
    }
    function pushHistory(editKey) {
      const now = Date.now();
      // Typing into the same field keeps collapsing into one undo step,
      // so undo jumps back a word or a field — not a single letter.
      if (editKey && editKey === state.lastEditKey && now - state.lastEditAt < 900) {
        state.lastEditAt = now;
        return;
      }
      state.past.push(snapshotState());
      if (state.past.length > 60) state.past.shift();
      state.future = [];
      state.lastEditKey = editKey || "";
      state.lastEditAt = now;
    }
    function applySnapshot(snapshot) {
      state.pages = snapshot.pages;
      state.theme = snapshot.theme;
      if (state.pages.some((page) => page.id === snapshot.selectedId)) state.selectedId = snapshot.selectedId;
      const page = current();
      state.selectedBlockId = page && page.blocks.some((b) => b.id === snapshot.selectedBlockId) ? snapshot.selectedBlockId : null;
      state.dirty = true;
      state.notice = null;
      state.lastEditKey = "";
      state.autosaveState = "";
      render();
      scheduleAutosave();
    }
    function undo() {
      if (!state.past.length || state.busy) return;
      state.future.push(snapshotState());
      applySnapshot(state.past.pop());
    }
    function redo() {
      if (!state.future.length || state.busy) return;
      state.past.push(snapshotState());
      applySnapshot(state.future.pop());
    }
    function updateHistoryButtons() {
      const undoButton = document.querySelector("[data-action='undo']");
      const redoButton = document.querySelector("[data-action='redo']");
      if (undoButton) undoButton.disabled = !state.past.length || state.busy;
      if (redoButton) redoButton.disabled = !state.future.length || state.busy;
    }

    // ---------- autosave ----------
    function scheduleAutosave(delay = 2200) {
      if (state.autosaveTimer) clearTimeout(state.autosaveTimer);
      state.autosaveTimer = window.setTimeout(() => { void autosave(); }, delay);
    }
    async function autosave() {
      state.autosaveTimer = null;
      if (!state.dirty || state.busy || state.saving || !state.theme) return;
      if (validatePages(state.pages)) {
        // Half-finished content: keep it in the editor and try again later
        // instead of throwing an error in the middle of a sentence.
        state.autosaveState = "waiting";
        updateDraftIndicator();
        scheduleAutosave(4000);
        return;
      }
      state.saving = true;
      state.autosaveState = "saving";
      updateDraftIndicator();
      try {
        const result = await requestApi("/api/admin/state", "PUT", { pages: state.pages, theme: state.theme, revision: state.revision });
        state.revision = result.revision;
        state.dirty = false;
        state.autosaveState = "saved";
      } catch (issue) {
        state.autosaveState = "error";
      } finally {
        state.saving = false;
        updateDraftIndicator();
      }
    }
    function setNotice(tone, text) {
      state.notice = { tone, text };
    }
    function showError(issue) {
      const message = messageOf(issue);
      setNotice("error", message);
      render();
      if (message.includes("session has expired")) location.reload();
    }

    async function saveDraft() {
      if (!state.theme) throw new Error("The workspace is still loading.");
      if (!state.dirty) return state.revision;
      const problem = validatePages(state.pages);
      if (problem) throw new Error(problem);
      state.busy = true;
      render();
      try {
        const result = await requestApi("/api/admin/state", "PUT", { pages: state.pages, theme: state.theme, revision: state.revision });
        state.revision = result.revision;
        state.dirty = false;
        setNotice("success", "Draft saved. Your public site hasn't changed.");
        return result.revision;
      } finally {
        state.busy = false;
        render();
      }
    }

    async function saveClick() {
      try {
        if (state.dirty) await saveDraft();
        else setNotice("info", "Everything is already saved as a draft.");
        render();
      } catch (issue) {
        showError(issue);
      }
    }

    async function preview() {
      try {
        if (state.dirty) await saveDraft();
        const page = current();
        location.href = `/adminpanel/preview?slug=${encodeURIComponent(page?.slug || "")}`;
      } catch (issue) {
        showError(issue);
      }
    }

    async function publish() {
      state.publishOpen = false;
      state.busy = true;
      render();
      try {
        const currentRevision = state.dirty ? await saveDraftQuiet() : state.revision;
        const result = await requestApi("/api/admin/publish", "POST", { revision: currentRevision });
        state.revision = result.revision;
        state.publishedAt = result.publishedAt;
        state.dirty = false;
        setNotice("success", "Published. Your public portfolio is live.");
        const history = await requestApi("/api/admin/history");
        state.versions = history.versions;
        render();
      } catch (issue) {
        showError(issue);
      } finally {
        state.busy = false;
        render();
      }
    }
    // Like saveDraft, but without the notice flicker mid-publish.
    async function saveDraftQuiet() {
      if (!state.theme) throw new Error("The workspace is still loading.");
      if (!state.dirty) return state.revision;
      const problem = validatePages(state.pages);
      if (problem) throw new Error(problem);
      const result = await requestApi("/api/admin/state", "PUT", { pages: state.pages, theme: state.theme, revision: state.revision });
      state.revision = result.revision;
      state.dirty = false;
      return result.revision;
    }

    function addPage() {
      const title = state.newTitle.trim();
      const slug = state.newSlug.trim().toLowerCase();
      if (!title || !slug) {
        setNotice("error", "Give the new page a title and a URL.");
        render();
        return;
      }
      const next = { id: newId(), title, slug, description: "", visible: state.newVisible, blocks: [] };
      const test = validatePages([...state.pages, next]);
      if (test) {
        setNotice("error", test);
        render();
        return;
      }
      changePages([...state.pages, next]);
      state.selectedId = next.id;
      state.section = "pages";
      state.addOpen = false;
      state.newTitle = "";
      state.newSlug = "";
      state.newVisible = true;
      setNotice("info", "Page added to your draft. Add content, then save and publish when ready.");
      render();
    }

    function duplicatePage() {
      const page = current();
      if (!page) return;
      const base = (page.slug || "home") + "-copy";
      let slug = base;
      let counter = 2;
      while (state.pages.some((item) => item.slug === slug)) slug = `${base}-${counter++}`;
      const copy = {
        ...page,
        id: newId(),
        title: `${page.title} copy`.slice(0, 100),
        slug,
        visible: false,
        blocks: page.blocks.map((block) => ({ ...block, id: newId() })),
      };
      changePages([...state.pages, copy]);
      state.selectedId = copy.id;
      setNotice("info", "A hidden copy was added to your draft.");
      render();
    }

    function deletePage() {
      const page = current();
      if (!page) return;
      if (page.id === "home") {
        if (!window.confirm("Reset the Home draft? After publishing, the designed placeholder will appear instead of the current Home page.")) return;
        changePages(state.pages.map((item) => (item.id === "home" ? { ...item, blocks: [], description: "" } : item)));
        setNotice("info", "Home reset in the draft. The public page remains unchanged until publishing.");
      } else {
        if (!window.confirm(`Delete \u201c${page.title}\u201d from the draft? It stays live until you publish.`)) return;
        changePages(state.pages.filter((item) => item.id !== page.id));
        state.selectedId = "home";
      }
      render();
    }

    function reorder(direction) {
      const page = current();
      if (!page || page.id === "home") return;
      const index = state.pages.findIndex((item) => item.id === page.id);
      const target = index + direction;
      if (target <= 0 || target >= state.pages.length) return;
      const next = [...state.pages];
      [next[index], next[target]] = [next[target], next[index]];
      changePages(next);
      render();
    }

    function formatSize(bytes) {
      if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
      return `${Math.max(1, Math.round(bytes / 1024))} KB`;
    }

    function showAlert(title, text) {
      state.alert = { title, text };
      render();
    }

    async function upload(file, options = {}) {
      if (file.size > MAX_UPLOAD_BYTES) {
        showAlert(
          "That file is too big",
          `\u201c${file.name}\u201d is ${formatSize(file.size)}. Uploads are limited to ${formatSize(MAX_UPLOAD_BYTES)} — resize or compress it and try again.`,
        );
        return null;
      }
      state.busy = true;
      render();
      try {
        const form = new FormData();
        form.append("file", file);
        const result = await requestApi("/api/admin/media", "POST", form);
        state.media = [result.file, ...state.media];
        if (!options.quiet) setNotice("success", `\u201c${result.file.name}\u201d was added to your library.`);
        return result.file;
      } catch (issue) {
        showError(issue);
        return null;
      } finally {
        state.busy = false;
        render();
      }
    }

    async function mutateAsset(asset, method, value) {
      try {
        const currentRevision = state.dirty ? await saveDraftQuiet() : state.revision;
        state.busy = true;
        render();
        let payload = { name: value, revision: currentRevision };
        if (value instanceof File) {
          const form = new FormData();
          form.append("file", value);
          form.append("revision", String(currentRevision));
          payload = form;
        }
        const result = await requestApi(`/api/admin/media/${asset.id}`, method, payload);
        state.pages = result.pages;
        state.revision = result.revision;
        state.dirty = false;
        const refreshed = await requestApi("/api/admin/media");
        state.media = refreshed.files;
        setNotice("success", "Updated in the draft. Published pages and past versions kept the original file.");
      } catch (issue) {
        showError(issue);
      } finally {
        state.busy = false;
        render();
      }
    }

    async function deleteAsset(asset) {
      if (!window.confirm(`Delete \u201c${asset.name}\u201d from the library? Files used by pages or history cannot be deleted.`)) return;
      try {
        if (state.dirty) await saveDraftQuiet();
        state.busy = true;
        render();
        await requestApi(`/api/admin/media/${asset.id}`, "DELETE");
        state.media = state.media.filter((item) => item.id !== asset.id);
        setNotice("success", "Upload removed from your library.");
      } catch (issue) {
        showError(issue);
      } finally {
        state.busy = false;
        render();
      }
    }

    async function restore(version) {
      if (!window.confirm(`Restore the version from ${new Date(version.publishedAt).toLocaleString()} to your draft? Unsaved draft edits will be replaced; the live site won't change until you publish.`)) return;
      state.busy = true;
      render();
      try {
        const result = await requestApi("/api/admin/history", "POST", { id: version.id, revision: state.revision });
        state.pages = result.pages;
        state.theme = result.theme;
        state.revision = result.revision;
        state.selectedId = "home";
        state.dirty = false;
        state.section = "pages";
        setNotice("success", "Previous version restored to your draft. Preview it before publishing.");
        render();
      } catch (issue) {
        showError(issue);
      } finally {
        state.busy = false;
        render();
      }
    }

    async function setMessageRead(id, read) {
      state.busy = true;
      render();
      try {
        await requestApi(`/api/admin/messages/${id}`, "PATCH", { read });
        state.messages = state.messages.map((item) => (item.id === id ? { ...item, read } : item));
      } catch (issue) {
        showError(issue);
      } finally {
        state.busy = false;
        render();
      }
    }

    async function deleteMessage(id) {
      if (!window.confirm("Delete this message? It cannot be brought back.")) return;
      state.busy = true;
      render();
      try {
        await requestApi(`/api/admin/messages/${id}`, "DELETE");
        state.messages = state.messages.filter((item) => item.id !== id);
        setNotice("success", "Message deleted.");
      } catch (issue) {
        showError(issue);
      } finally {
        state.busy = false;
        render();
      }
    }

    async function saveVisitTotal(value) {
      const total = Number(value);
      if (!Number.isInteger(total) || total < 0 || total > 1000000000) {
        setNotice("error", "Choose a whole number between 0 and 1000000000.");
        render();
        return;
      }
      state.busy = true;
      render();
      try {
        state.visits = await requestApi("/api/admin/visits", "PUT", { displayedTotal: total });
        state.visitDraft = null;
        setNotice("success", "Saved. Your pages show this number from now on.");
      } catch (issue) {
        showError(issue);
      } finally {
        state.busy = false;
        render();
      }
    }

    async function logout() {
      try {
        await requestApi("/api/auth/logout", "POST");
        location.reload();
      } catch (issue) {
        showError(issue);
      }
    }

    function chooseSection(next) {
      state.section = next;
      state.mobileNav = false;
      state.notice = null;
      state.selectedBlockId = null;
      state.visitDraft = null;
      render();
    }

    // ---------- block editing ----------
    // `inspector: true` for changes that alter which controls are shown
    // (adding a gallery image, a timeline entry, a new upload). Plain text
    // edits only refresh the preview, so the field you are typing in is
    // never rebuilt and never loses the cursor.
    function updateBlock(patch, options = {}) {
      const page = current();
      const block = selectedBlock();
      if (!page || !block) return;
      const nextBlock = { ...block, ...patch };
      const editKey = `${block.id}:${Object.keys(patch).join(",")}`;
      changePages(
        state.pages.map((item) => (item.id === page.id ? { ...item, blocks: item.blocks.map((b) => (b.id === block.id ? nextBlock : b)) } : item)),
        editKey,
      );
      renderCanvas();
      if (options.inspector) renderInspector();
    }

    function updateItems(items, options = {}) {
      updateBlock({ items }, options);
    }

    function moveBlockTo(sourceId, targetId, after) {
      const page = current();
      if (!page || !sourceId || sourceId === targetId) return;
      const blocks = [...page.blocks];
      const from = blocks.findIndex((b) => b.id === sourceId);
      if (from < 0) return;
      const [moved] = blocks.splice(from, 1);
      const to = blocks.findIndex((b) => b.id === targetId);
      if (to < 0) return;
      blocks.splice(after ? to + 1 : to, 0, moved);
      changePages(state.pages.map((item) => (item.id === page.id ? { ...item, blocks } : item)));
      state.selectedBlockId = sourceId;
      renderCanvas();
      renderInspector();
    }

    function addBlock(type) {
      const page = current();
      if (!page) return;
      const block = {
        id: newId(), type, text: "", title: "", url: "", newTab: false, level: 2, align: "left",
        size: "md", width: 100, spacing: 24, padding: 0, marginTop: 0, color: "", background: "",
        mediaId: "", alt: "", showDownload: true, fontOverride: "inherit",
        items: type === "timeline" ? [{ label: "", title: "", text: "" }] : [], mediaIds: [], columns: 3,
      };
      changePages(state.pages.map((item) => (item.id === page.id ? { ...item, blocks: [...item.blocks, block] } : item)));
      state.selectedBlockId = block.id;
      state.adding = false;
      render();
      renderInspector();
    }

    function moveBlock(direction) {
      const page = current();
      const block = selectedBlock();
      if (!page || !block) return;
      const index = page.blocks.findIndex((b) => b.id === block.id);
      const target = index + direction;
      if (target < 0 || target >= page.blocks.length) return;
      const blocks = [...page.blocks];
      [blocks[index], blocks[target]] = [blocks[target], blocks[index]];
      changePages(state.pages.map((item) => (item.id === page.id ? { ...item, blocks } : item)));
      render();
    }

    function duplicateBlock() {
      const page = current();
      const block = selectedBlock();
      if (!page || !block) return;
      const index = page.blocks.findIndex((b) => b.id === block.id);
      const copy = { ...block, id: newId() };
      const blocks = [...page.blocks];
      blocks.splice(index + 1, 0, copy);
      changePages(state.pages.map((item) => (item.id === page.id ? { ...item, blocks } : item)));
      state.selectedBlockId = copy.id;
      render();
      renderInspector();
    }

    function removeBlock() {
      const page = current();
      const block = selectedBlock();
      if (!page || !block) return;
      if (!window.confirm(`Remove this ${BLOCK_NAMES[block.type].toLowerCase()} block from the draft?`)) return;
      changePages(state.pages.map((item) => (item.id === page.id ? { ...item, blocks: item.blocks.filter((b) => b.id !== block.id) } : item)));
      state.selectedBlockId = null;
      render();
      renderInspector();
    }

    function insertMarkup(before, after = before, fallback = "text") {
      const field = document.getElementById("block-text-input");
      const block = selectedBlock();
      if (!field || !block) return;
      const start = field.selectionStart;
      const end = field.selectionEnd;
      const chosen = block.text.slice(start, end) || fallback;
      const nextText = block.text.slice(0, start) + before + chosen + after + block.text.slice(end);
      updateBlock({ text: nextText });
      requestAnimationFrame(() => {
        const current = document.getElementById("block-text-input");
        if (!current) return;
        current.value = nextText;
        current.focus();
        current.setSelectionRange(start + before.length, start + before.length + chosen.length);
      });
    }

    // ---------- events ----------
    let dragBlockId = null;
    function clearDropHints() {
      document.querySelectorAll(".canvas-block").forEach((node) => node.classList.remove("drop-before", "drop-after", "dragging"));
    }

    function bindCanvasEvents() {
      document.querySelectorAll("[data-block]").forEach((node) => {
        node.ondragstart = (event) => {
          dragBlockId = node.dataset.block;
          node.classList.add("dragging");
          event.dataTransfer.effectAllowed = "move";
          try { event.dataTransfer.setData("text/plain", dragBlockId); } catch { /* older browsers */ }
        };
        node.ondragend = () => { dragBlockId = null; clearDropHints(); };
        node.ondragover = (event) => {
          if (!dragBlockId || dragBlockId === node.dataset.block) return;
          event.preventDefault();
          event.dataTransfer.dropEffect = "move";
          const box = node.getBoundingClientRect();
          const after = event.clientY > box.top + box.height / 2;
          node.classList.toggle("drop-after", after);
          node.classList.toggle("drop-before", !after);
        };
        node.ondragleave = () => node.classList.remove("drop-before", "drop-after");
        node.ondrop = (event) => {
          if (!dragBlockId) return;
          event.preventDefault();
          const after = node.classList.contains("drop-after");
          const source = dragBlockId;
          dragBlockId = null;
          clearDropHints();
          moveBlockTo(source, node.dataset.block, after);
        };
        node.onclick = (event) => {
          event.preventDefault();
          state.selectedBlockId = node.dataset.block;
          renderCanvas();
          renderInspector();
        };
        node.onkeydown = (event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            state.selectedBlockId = node.dataset.block;
            renderCanvas();
            renderInspector();
          }
        };
      });
      document.querySelectorAll("[data-add-block]").forEach((button) => {
        button.onclick = () => addBlock(button.dataset.addBlock);
      });
    }

    function bindPageSectionEvents() {
      document.querySelectorAll("[data-page-field]").forEach((input) => {
        const field = input.dataset.pageField;
        const apply = () => {
          const page = current();
          if (!page) return;
          const value = field === "visible" ? input.checked : input.value;
          changePages(state.pages.map((item) => (item.id === page.id ? { ...item, [field]: value } : item)));
          syncPageMeta();
        };
        input.addEventListener("input", apply);
        if (field === "visible") input.addEventListener("change", apply);
      });
      document.querySelectorAll("[data-device]").forEach((button) => {
        button.onclick = () => {
          state.canvasSize = button.dataset.device;
          document.querySelectorAll("[data-device]").forEach((other) => other.classList.toggle("selected", other === button));
          const shell = document.querySelector(".canvas-shell");
          if (shell) shell.className = `canvas-shell canvas-${state.canvasSize}`;
        };
      });
      const trigger = document.querySelector("[data-action='toggle-add']");
      if (trigger) trigger.onclick = () => toggleAddBlock();
    }

    // The "Add a block" accordion. Kept as one function so both the section
    // binding and the global data-action switch drive the exact same logic —
    // bindGlobalEvents() rebinds [data-action] buttons on every render, so a
    // handler that only lived on the section binding gets silently clobbered.
    function toggleAddBlock() {
      state.adding = !state.adding;
      const area = document.querySelector(".block-add-area");
      if (!area) return;
      area.innerHTML = `
        <button type="button" class="block-add-trigger" data-action="toggle-add" aria-expanded="${state.adding}">${icon("plus", 18)} Add a block ${icon("chevronDown", 16, 2).replace("<svg", `<svg class="${state.adding ? "rotate" : ""}"`)}</button>
        ${state.adding ? `<div class="block-palette">${BLOCK_TYPES.map((type) => `<button type="button" data-add-block="${type}">${icon(BLOCK_ICONS[type], 18, 1.7)}<span>${BLOCK_NAMES[type]}</span></button>`).join("")}</div>` : ""}`;
      bindCanvasEvents();
      const fresh = area.querySelector("[data-action='toggle-add']");
      if (fresh) fresh.onclick = () => toggleAddBlock();
    }

    function bindInspectorEvents() {
      const panel = document.getElementById("inspector");
      if (!panel) return;
      const block0 = selectedBlock();

      // Timeline entries
      panel.querySelectorAll("[data-item-field]").forEach((input) => {
        input.addEventListener("input", () => {
          const block = selectedBlock();
          if (!block) return;
          const index = Number(input.dataset.itemIndex);
          const items = (block.items || []).map((item, i) => (i === index ? { ...item, [input.dataset.itemField]: input.value } : item));
          updateItems(items);
        });
      });
      panel.querySelector("[data-item-add]")?.addEventListener("click", () => {
        const block = selectedBlock();
        if (!block) return;
        const items = [...(block.items || []), { label: "", title: "", text: "" }];
        if (items.length > MAX_TIMELINE_ITEMS) return;
        updateItems(items, { inspector: true });
      });
      panel.querySelectorAll("[data-item-remove]").forEach((button) => {
        button.addEventListener("click", () => {
          const block = selectedBlock();
          if (!block) return;
          const index = Number(button.dataset.itemRemove);
          updateItems((block.items || []).filter((_, i) => i !== index), { inspector: true });
        });
      });
      panel.querySelectorAll("[data-item-move]").forEach((button) => {
        button.addEventListener("click", () => {
          const block = selectedBlock();
          if (!block) return;
          const index = Number(button.dataset.itemMove);
          const target = index + Number(button.dataset.itemDir);
          const items = [...(block.items || [])];
          if (target < 0 || target >= items.length) return;
          [items[index], items[target]] = [items[target], items[index]];
          updateItems(items, { inspector: true });
        });
      });

      // Gallery images
      panel.querySelector("[data-gallery-add]")?.addEventListener("change", (event) => {
        const block = selectedBlock();
        const id = event.target.value;
        if (!block || !id) return;
        const ids = [...(block.mediaIds || [])];
        if (!ids.includes(id) && ids.length < MAX_GALLERY_IMAGES) ids.push(id);
        updateBlock({ mediaIds: ids }, { inspector: true });
      });
      panel.querySelectorAll("[data-gallery-remove]").forEach((button) => {
        button.addEventListener("click", () => {
          const block = selectedBlock();
          if (!block) return;
          const index = Number(button.dataset.galleryRemove);
          updateBlock({ mediaIds: (block.mediaIds || []).filter((_, i) => i !== index) }, { inspector: true });
        });
      });
      panel.querySelectorAll("[data-gallery-move]").forEach((button) => {
        button.addEventListener("click", () => {
          const block = selectedBlock();
          if (!block) return;
          const index = Number(button.dataset.galleryMove);
          const target = index + Number(button.dataset.galleryDir);
          const ids = [...(block.mediaIds || [])];
          if (target < 0 || target >= ids.length) return;
          [ids[index], ids[target]] = [ids[target], ids[index]];
          updateBlock({ mediaIds: ids }, { inspector: true });
        });
      });
      panel.querySelector("[data-gallery-upload]")?.addEventListener("change", async (event) => {
        const files = Array.from(event.target.files || []);
        event.target.value = "";
        const block = selectedBlock();
        if (!files.length || !block) return;
        const added = [];
        for (const file of files) {
          const uploaded = await upload(file, { quiet: true });
          if (uploaded && uploaded.kind === "image") added.push(uploaded.id);
          else if (uploaded) showAlert("That file isn't an image", `\u201c${uploaded.name}\u201d was added to your library, but a gallery can only hold images.`);
        }
        if (!added.length) return;
        const ids = [...(selectedBlock()?.mediaIds || []), ...added].slice(0, MAX_GALLERY_IMAGES);
        updateBlock({ mediaIds: ids }, { inspector: true });
        setNotice("success", added.length === 1 ? "Image added to the gallery." : `${added.length} images added to the gallery.`);
        render();
      });
      panel.querySelectorAll("[data-inspector-number]").forEach((input) => {
        input.addEventListener("change", () => updateBlock({ [input.dataset.inspectorNumber]: Number(input.value) }));
      });
      void block0;
      const bindText = (input) => {
        input.addEventListener("input", () => updateBlock({ [input.dataset.inspector]: input.value }));
      };
      panel.querySelectorAll("[data-inspector]").forEach((input) => {
        const key = input.dataset.inspector;
        if (key === "upload") {
          input.addEventListener("change", async (event) => {
            const file = event.target.files?.[0];
            event.target.value = "";
            const block = selectedBlock();
            if (!file || !block) return;
            const uploaded = await upload(file);
            if (uploaded) {
              if (block.type === "image" && uploaded.kind !== "image") {
                window.alert("Please choose an image for an image block. Your file was added to the library.");
                return;
              }
              updateBlock({ mediaId: uploaded.id, ...(block.type === "file" && !block.title ? { title: uploaded.name } : {}) }, { inspector: true });
            }
          });
          return;
        }
        if (key === "mediaId") {
          input.addEventListener("change", () => {
            const item = state.media.find((asset) => asset.id === input.value);
            const block = selectedBlock();
            updateBlock({ mediaId: input.value, ...(block?.type === "file" && item && !block.title ? { title: item.name } : {}) }, { inspector: true });
          });
          return;
        }
        if (key === "level" || key === "size" || key === "fontOverride") {
          input.addEventListener("change", () => {
            const value = key === "level" ? Number(input.value) : input.value;
            updateBlock({ [key]: value });
          });
          return;
        }
        if (key === "newTab" || key === "showDownload") {
          input.addEventListener("change", () => updateBlock({ [key]: input.checked }));
          return;
        }
        bindText(input);
      });
      panel.querySelectorAll("[data-markup]").forEach((button) => {
        button.onclick = () => {
          const token = button.dataset.markup;
          if (token === "**") insertMarkup("**");
          else if (token === "*") insertMarkup("*");
          else if (token === "`") insertMarkup("`");
          else if (token === "link") insertMarkup("[", "](https://example.com)", "link text");
        };
      });
      panel.querySelectorAll("[data-align]").forEach((button) => {
        button.onclick = () => {
          updateBlock({ align: button.dataset.align });
          panel.querySelectorAll("[data-align]").forEach((other) => other.classList.toggle("selected", other === button));
        };
      });
      panel.querySelectorAll("[data-range]").forEach((input) => {
        input.addEventListener("input", () => {
          const key = input.dataset.range;
          const value = Number(input.value);
          const label = panel.querySelector(`[data-range-label="${key}"]`);
          if (label) label.textContent = key === "width" ? `${value}%` : `${value}px`;
          updateBlock({ [key]: value });
        });
      });
      panel.querySelectorAll("[data-color]").forEach((input) => {
        input.addEventListener("input", () => updateBlock({ [input.dataset.color]: input.value }));
      });
      panel.querySelectorAll("[data-reset-color]").forEach((button) => {
        button.onclick = () => updateBlock({ [button.dataset.resetColor]: "" }, { inspector: true });
      });
      panel.querySelectorAll("[data-block-action]").forEach((button) => {
        button.onclick = () => {
          const action = button.dataset.blockAction;
          if (action === "up") moveBlock(-1);
          else if (action === "down") moveBlock(1);
          else if (action === "duplicate") duplicateBlock();
          else if (action === "remove") removeBlock();
        };
      });
    }

    function bindThemeSectionEvents() {
      const slot = document.getElementById("section-content");
      slot.querySelectorAll("[data-mode]").forEach((button) => {
        button.onclick = () => {
          const palette = button.dataset.mode === "dark" ? DARK_PALETTE : LIGHT_PALETTE;
          changeTheme({ ...state.theme, mode: button.dataset.mode, ...palette });
          renderSection();
        };
      });
      slot.querySelectorAll("[data-theme-color]").forEach((input) => {
        input.addEventListener("input", () => {
          const key = input.dataset.themeColor;
          changeTheme({ ...state.theme, [key]: input.value });
          const code = slot.querySelector(`[data-theme-code="${key}"]`);
          if (code) code.textContent = input.value;
          renderThemePreview();
        });
      });
      slot.querySelectorAll("[data-theme-font]").forEach((button) => {
        button.onclick = () => {
          changeTheme({ ...state.theme, font: button.dataset.themeFont });
          renderSection();
        };
      });
      slot.querySelectorAll("[data-theme-range]").forEach((input) => {
        input.addEventListener("input", () => {
          const key = input.dataset.themeRange;
          const value = Number(input.value);
          changeTheme({ ...state.theme, [key]: value });
          const label = slot.querySelector(`[data-range-label="${key}"]`);
          if (label) label.textContent = key === "headingScale" || key === "spacing" ? `${Math.round(value * 100)}%` : `${value}px`;
          renderThemePreview();
        });
      });
      slot.querySelectorAll("[data-theme-select]").forEach((input) => {
        input.addEventListener("change", () => {
          changeTheme({ ...state.theme, [input.dataset.themeSelect]: input.value });
          renderThemePreview();
        });
      });
    }

    function bindMediaSectionEvents() {
      const slot = document.getElementById("section-content");
      const dropzone = slot.querySelector("[data-dropzone]");
      if (dropzone) {
        dropzone.addEventListener("dragover", (event) => {
          event.preventDefault();
          state.dragging = true;
          dropzone.classList.add("dragging");
        });
        dropzone.addEventListener("dragleave", () => {
          state.dragging = false;
          dropzone.classList.remove("dragging");
        });
        dropzone.addEventListener("drop", async (event) => {
          event.preventDefault();
          state.dragging = false;
          dropzone.classList.remove("dragging");
          for (const file of Array.from(event.dataTransfer.files)) await upload(file);
        });
        const input = dropzone.querySelector("[data-media-upload]");
        if (input) {
          input.addEventListener("change", async (event) => {
            const files = Array.from(event.target.files || []);
            event.target.value = "";
            for (const file of files) await upload(file);
          });
        }
      }
      const renameInputEl = slot.querySelector("[data-rename-input]");
      if (renameInputEl) {
        renameInputEl.addEventListener("input", () => {
          state.renameName = renameInputEl.value;
          const formButton = renameInputEl.parentElement?.querySelector("button");
          if (formButton) formButton.disabled = state.busy || !state.renameName.trim();
        });
        renameInputEl.focus();
      }
      slot.querySelectorAll("[data-rename]").forEach((button) => {
        button.onclick = () => {
          const asset = state.media.find((item) => item.id === button.dataset.rename);
          if (!asset) return;
          state.renaming = state.renaming === asset.id ? null : asset.id;
          state.renameName = asset.name;
          renderMediaSection(document.getElementById("section-content"));
        };
      });
      slot.querySelectorAll("[data-rename-form]").forEach((form) => {
        form.addEventListener("submit", async (event) => {
          event.preventDefault();
          const asset = state.media.find((item) => item.id === form.dataset.renameForm);
          if (!asset) return;
          await mutateAsset(asset, "PATCH", state.renameName);
          state.renaming = null;
          renderMediaSection(document.getElementById("section-content"));
        });
      });
      slot.querySelectorAll("[data-replace]").forEach((input) => {
        input.addEventListener("change", (event) => {
          const file = event.target.files?.[0];
          const asset = state.media.find((item) => item.id === input.dataset.replace);
          if (file && asset) void mutateAsset(asset, "PUT", file);
          event.target.value = "";
        });
      });
      slot.querySelectorAll("[data-delete-media]").forEach((button) => {
        button.onclick = () => {
          const asset = state.media.find((item) => item.id === button.dataset.deleteMedia);
          if (asset) void deleteAsset(asset);
        };
      });
    }

    function bindMessagesSectionEvents() {
      const slot = document.getElementById("section-content");
      if (!slot) return;
      slot.querySelectorAll("[data-message-read]").forEach((button) => {
        button.onclick = () =>
          void setMessageRead(Number(button.dataset.messageRead), button.dataset.messageValue === "read");
      });
      slot.querySelectorAll("[data-message-delete]").forEach((button) => {
        button.onclick = () => void deleteMessage(Number(button.dataset.messageDelete));
      });
    }

    function bindVisitsSectionEvents() {
      const slot = document.getElementById("section-content");
      if (!slot) return;
      const input = slot.querySelector("[data-visit-input]");
      if (input) input.addEventListener("input", () => { state.visitDraft = input.value; });
      const form = slot.querySelector("[data-visit-form]");
      if (form) {
        form.addEventListener("submit", (event) => {
          event.preventDefault();
          void saveVisitTotal(input ? input.value : "");
        });
      }
    }

    function bindGlobalEvents() {
      document.querySelectorAll("[data-nav]").forEach((button) => {
        button.onclick = () => chooseSection(button.dataset.nav);
      });
      document.querySelectorAll("[data-page]").forEach((button) => {
        button.onclick = () => {
          state.selectedId = button.dataset.page;
          state.selectedBlockId = null;
          chooseSection("pages");
        };
      });
      document.querySelectorAll("[data-action]").forEach((button) => {
        const action = button.dataset.action;
        button.onclick = () => {
          switch (action) {
            case "open-mobile-nav":
              state.mobileNav = true;
              render();
              break;
            case "close-mobile-nav":
              state.mobileNav = false;
              render();
              break;
            case "save":
              void saveClick();
              break;
            case "preview":
              void preview();
              break;
            case "publish-open":
              state.publishOpen = true;
              render();
              break;
            case "publish-cancel":
              state.publishOpen = false;
              render();
              break;
            case "publish-confirm":
              void publish();
              break;
            case "add-page":
              state.addOpen = true;
              state.mobileNav = false;
              render();
              break;
            case "add-cancel":
              state.addOpen = false;
              render();
              break;
            case "dismiss-notice":
              state.notice = null;
              render();
              break;
            case "logout":
              void logout();
              break;
            case "retry":
              void load();
              break;
            case "undo":
              undo();
              break;
            case "redo":
              redo();
              break;
            case "alert-close":
              state.alert = null;
              render();
              break;
            case "page-up":
              reorder(-1);
              break;
            case "page-down":
              reorder(1);
              break;
            case "page-duplicate":
              duplicatePage();
              break;
            case "page-delete":
              deletePage();
              break;
            case "toggle-add":
              toggleAddBlock();
              break;
            case "add-first-block":
              state.adding = true;
              render();
              break;
          }
        };
      });
      document.querySelectorAll("[data-restore]").forEach((button) => {
        button.onclick = () => {
          const version = state.versions.find((item) => item.id === Number(button.dataset.restore));
          if (version) void restore(version);
        };
      });
      const addOverlay = document.querySelector('[data-overlay="add"]');
      if (addOverlay) {
        addOverlay.addEventListener("mousedown", (event) => {
          if (event.target === addOverlay) {
            state.addOpen = false;
            render();
          }
        });
        const form = addOverlay.querySelector("[data-add-form]");
        if (form) {
          const titleInput = form.querySelector("[data-add-title]");
          const slugInput = form.querySelector("[data-add-slug]");
          titleInput?.addEventListener("input", () => {
            state.newTitle = titleInput.value;
            if (!state.newSlug) {
              state.newSlug = titleInput.value.toLowerCase().trim().replace(/[^a-z0-9\s-]/g, "").replace(/\s+/g, "-");
              if (slugInput) slugInput.value = state.newSlug;
            }
          });
          slugInput?.addEventListener("input", () => {
            state.newSlug = slugInput.value.toLowerCase().replace(/[^a-z0-9-]/g, "");
            slugInput.value = state.newSlug;
          });
          form.querySelector("[data-add-visible]")?.addEventListener("change", (event) => {
            state.newVisible = event.target.checked;
          });
          form.addEventListener("submit", (event) => {
            event.preventDefault();
            addPage();
          });
        }
      }
      const publishOverlay = document.querySelector('[data-overlay="publish"]');
      if (publishOverlay) {
        publishOverlay.addEventListener("mousedown", (event) => {
          if (event.target === publishOverlay) {
            state.publishOpen = false;
            render();
          }
        });
      }
    }

    // ---------- boot ----------
    async function load() {
      state.loading = true;
      try {
        const [workspace, uploads, history, inbox, visits] = await Promise.all([
          requestApi("/api/admin/state"),
          requestApi("/api/admin/media"),
          requestApi("/api/admin/history"),
          requestApi("/api/admin/messages"),
          requestApi("/api/admin/visits"),
        ]);
        state.pages = workspace.pages;
        state.theme = workspace.theme;
        state.revision = workspace.revision;
        state.publishedAt = workspace.publishedAt;
        state.media = uploads.files;
        state.versions = history.versions;
        state.messages = inbox.messages;
        state.visits = visits;
        state.visitDraft = null;
        state.dirty = false;
        state.loading = false;
        render();
        bindGlobalEvents();
      } catch (issue) {
        state.loading = false;
        state.notice = { tone: "error", text: messageOf(issue) };
        render();
        if (messageOf(issue).includes("session has expired")) location.reload();
      }
    }

    // Window-level wiring, registered once: shortcuts, autosave safety nets.
    function bindWindowEvents() {
      document.addEventListener("keydown", (event) => {
        if (!(event.metaKey || event.ctrlKey) || event.altKey) return;
        const key = (event.key || "").toLowerCase();
        if (key === "s") {
          event.preventDefault();
          void saveClick();
        } else if (key === "p") {
          event.preventDefault();
          if (state.busy || state.loading || state.publishOpen) return;
          state.publishOpen = true;
          render();
        } else if (key === "z" && !event.shiftKey) {
          if (isTypingTarget(event.target)) return;
          event.preventDefault();
          undo();
        } else if ((key === "z" && event.shiftKey) || key === "y") {
          if (isTypingTarget(event.target) && key === "y") return;
          event.preventDefault();
          redo();
        }
      });
      // Typing inside a field keeps the browser's own undo; the studio-wide
      // undo takes over everywhere else.
      function isTypingTarget(target) {
        return !!target && typeof target.matches === "function" && target.matches("input, textarea");
      }
      document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "hidden") void autosave();
      });
      window.addEventListener("pagehide", () => { void autosave(); });
      window.addEventListener("beforeunload", (event) => {
        if (!state.dirty) return;
        event.preventDefault();
        event.returnValue = "";
      });
    }

    bindWindowEvents();
    void load();
  }
})();
