"""Upload inspection and processing — port of src/lib/server/media.ts.

File types are detected from real byte signatures (not the extension or the
client's MIME claim). Still images are re-encoded to WebP through Pillow when
Pillow is available in the environment (add it in WispByte's "Additional
Python Packages" as ``Pillow``); otherwise the original bytes are stored and
served as-is, so the app works with zero third-party dependencies.
"""
from __future__ import annotations

import io
import re
import struct
import unicodedata
import zipfile
from typing import Any

from .store import AppError

try:  # Optional: image optimization. Not required to run.
    from PIL import Image as _PILImage  # type: ignore

    HAVE_PILLOW = True
except Exception:  # pragma: no cover - environment dependent
    HAVE_PILLOW = False

IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/avif"}
VIDEO_MIMES = {"video/mp4", "video/webm", "video/quicktime"}
FILE_MIMES = {
    "application/pdf", "application/zip", "application/x-zip-compressed",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/msword", "application/vnd.ms-excel", "application/vnd.ms-powerpoint",
    "application/x-7z-compressed", "application/x-rar-compressed",
    "audio/mpeg", "audio/wav", "audio/ogg", "audio/flac",
}

MAX_UPLOAD = 10 * 1024 * 1024
MAX_IMAGE = 10 * 1024 * 1024


def clean_name(name: str) -> str:
    cleaned = unicodedata.normalize("NFKC", name or "")
    part = re.split(r"[\\/]", cleaned)[-1]
    part = re.sub(r"[^\w ().\-]", "", part)
    part = part.lstrip(".").strip()[:110]
    return part or "upload"


def media_extension(mime: str) -> str:
    extensions = {
        "image/webp": "webp", "image/gif": "gif", "image/png": "png", "image/jpeg": "jpg",
        "image/avif": "avif", "video/mp4": "mp4", "video/webm": "webm",
        "video/quicktime": "mov", "application/pdf": "pdf", "application/zip": "zip",
        "text/plain": "txt", "text/csv": "csv",
    }
    return extensions.get(mime, "bin")


def _ftyp_brand(data: bytes) -> str:
    if len(data) >= 12 and data[4:8] == b"ftyp":
        return data[8:12].decode("latin-1", "replace").strip("\x00")
    return ""


def detect_type(data: bytes, filename: str) -> str | None:
    """Return a MIME type from the byte signature, or None for unknown binary."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if data[:4] == b"RIFF" and len(data) >= 12:
        if data[8:12] == b"WEBP":
            return "image/webp"
        if data[8:12] == b"WAVE":
            return "audio/wav"
    brand = _ftyp_brand(data)
    if brand in ("avif", "avis", "mif1"):
        return "image/avif"
    if brand in ("isom", "iso2", "mp41", "mp42", "m4v ", "M4V ", "M4A ", "mp4v"):
        return "video/mp4"
    if brand in ("qt  ", "qtm ", "avc1"):
        return "video/quicktime"
    if data.startswith(b"\x1a\x45\xdf\xa3"):
        return "video/webm"
    if data.startswith(b"%PDF"):
        return "application/pdf"
    if data.startswith(b"PK\x03\x04"):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                names = archive.namelist()
                if names:
                    first = names[0].split("/", 1)[0]
                    if first == "word":
                        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    if first == "ppt":
                        return "application/vnd.openxmlformats-officedocument.presentationml.presentation"
                    if first == "xl":
                        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        except Exception:
            return None
        return "application/zip"
    if data.startswith(b"7z\xbc\xaf\x27\x1c"):
        return "application/x-7z-compressed"
    if data.startswith(b"Rar!\x1a\x07"):
        return "application/x-rar-compressed"
    if data.startswith(b"OggS"):
        return "audio/ogg"
    if data.startswith(b"fLaC"):
        return "audio/flac"
    if data.startswith(b"ID3") or (len(data) >= 2 and data[0] == 0xFF and (data[1] & 0xE2) == 0xE2):
        return "audio/mpeg"
    if data.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        # Legacy Office (doc/xls/ppt) — treat as the closest supported kind.
        return "application/msword"
    return None


def image_size(data: bytes, mime: str = "") -> tuple[int, int] | None:
    """Read pixel dimensions straight out of the file header.

    Pillow is optional on the host, so the sizes are parsed by hand. Knowing
    them lets the page reserve the exact space for a photo, which stops the
    layout jumping while images load.
    """
    try:
        if data[:8] == b"\x89PNG\r\n\x1a\n" and data[12:16] == b"IHDR":
            width, height = struct.unpack(">II", data[16:24])
            return int(width), int(height)
        if data[:3] == b"GIF":
            width, height = struct.unpack("<HH", data[6:10])
            return int(width), int(height)
        if data[:2] == b"\xff\xd8":  # JPEG: walk the segments to SOFn
            index = 2
            while index + 9 < len(data):
                if data[index] != 0xFF:
                    index += 1
                    continue
                marker = data[index + 1]
                if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                    index += 2
                    continue
                length = struct.unpack(">H", data[index + 2:index + 4])[0]
                if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                    height, width = struct.unpack(">HH", data[index + 5:index + 9])
                    return int(width), int(height)
                index += 2 + length
            return None
        if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            chunk = data[12:16]
            if chunk == b"VP8 ":
                width, height = struct.unpack("<HH", data[26:30])
                return int(width) & 0x3FFF, int(height) & 0x3FFF
            if chunk == b"VP8L":
                bits = int.from_bytes(data[21:25], "little")
                return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
            if chunk == b"VP8X":
                width = int.from_bytes(data[24:27], "little") + 1
                height = int.from_bytes(data[27:30], "little") + 1
                return width, height
    except (struct.error, IndexError, ValueError):
        return None
    return None


def process_upload(name: str, data: bytes) -> dict[str, Any]:
    """Validate and normalize an upload. Returns {name, mime, kind, data, bytes}."""
    if not data or len(data) > MAX_UPLOAD:
        raise AppError("That file is too big. Uploads are limited to 10 MB.", 413)
    mime = detect_type(data, name) or ""
    kind: str
    if mime in IMAGE_MIMES:
        kind = "image"
        if len(data) > MAX_IMAGE:
            raise AppError("That image is too big. Uploads are limited to 10 MB.", 413)
        if mime != "image/gif" and HAVE_PILLOW:
            try:
                image = _PILImage.open(io.BytesIO(data))
                image.load()
                width, height = image.size
                if not width or not height:
                    raise AppError("This image could not be read. Try another image.")
                try:
                    exif = image.getexif()
                    orientation = exif.get(0x0112) if exif else None
                except Exception:
                    orientation = None
                transpose_map = {
                    2: _PILImage.FLIP_LEFT_RIGHT, 3: _PILImage.ROTATE_180,
                    4: _PILImage.FLIP_TOP_BOTTOM, 5: _PILImage.TRANSPOSE,
                    6: _PILImage.ROTATE_270, 7: _PILImage.TRANSVERSE, 8: _PILImage.ROTATE_90,
                }
                if orientation in transpose_map:
                    image = image.transpose(transpose_map[orientation])
                if image.mode not in ("RGB", "RGBA", "L"):
                    image = image.convert("RGBA" if image.info.get("transparency") is not None else "RGB")
                if max(image.size) > 2400:
                    image.thumbnail((2400, 2400))
                buffer = io.BytesIO()
                image.save(buffer, format="WEBP", quality=86, method=4)
                image.close()
                data = buffer.getvalue()
            except AppError:
                raise
            except Exception:
                raise AppError("This image could not be read. Try another image.") from None
            else:
                mime = "image/webp"
    elif mime in VIDEO_MIMES:
        kind = "video"
    elif mime in FILE_MIMES:
        kind = "file"
    elif mime == "":
        # Unknown binary — only accept clean plain text (never HTML/SVG/script payloads).
        try:
            text = data.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            raise AppError(
                "This file type is not supported. Try a PDF, document, archive, text file, image, or video."
            ) from None
        if re.search(r"[\u0000-\u0008\u000e-\u001f]", text):
            raise AppError(
                "This file type is not supported. Try a PDF, document, archive, text file, image, or video."
            )
        if re.match(r"^\s*<(?:!doctype|html|svg|script|\?xml)", text, re.IGNORECASE) or re.search(r"<script[\s>]", text, re.IGNORECASE):
            raise AppError(
                "This file type is not supported. Try a PDF, document, archive, text file, image, or video."
            )
        head = text[:300]
        # re.match anchors at position 0, so the extension has to be searched.
        is_csv = re.match(r"^([^\n]*,){1,}[^\n]*\n", head) and re.search(r"\.csv$", name or "", re.IGNORECASE)
        mime = "text/csv" if is_csv else "text/plain"
        kind = "file"
    else:
        raise AppError(
            "This file type is not supported. Try a PDF, document, archive, text file, image, or video."
        )
    size = image_size(data, mime) if kind == "image" else None
    return {"name": clean_name(name), "mime": mime, "kind": kind, "data": data, "bytes": len(data),
            "width": size[0] if size else None, "height": size[1] if size else None}
