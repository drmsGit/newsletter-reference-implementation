"""What an uploaded file is, read from its first bytes (ADR-197 point 8).

The name a browser sends is the person's to choose; the bytes are not. So the
type and the pixel size come from the file header, for the four formats email
clients show — JPEG, PNG, GIF and WebP — without an image library: reading
dimensions is a few fixed offsets, and a new dependency would be a pinned,
hash-locked package to keep current for that (ADR-189).
"""
import struct

#: The four formats and the extension a generated name gets.
FORMATS = {"image/jpeg": "jpg", "image/png": "png", "image/gif": "gif", "image/webp": "webp"}


class NotAnImage(ValueError):
    pass


def inspect(data: bytes) -> tuple[str, int, int]:
    """(media type, width, height) of a JPEG, PNG, GIF or WebP; NotAnImage otherwise."""
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        width, height = struct.unpack(">II", data[16:24])
        return "image/png", width, height
    if data[:6] in (b"GIF87a", b"GIF89a") and len(data) >= 10:
        width, height = struct.unpack("<HH", data[6:10])
        return "image/gif", width, height
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP" and len(data) >= 30:
        return ("image/webp", *_webp_size(data))
    if data[:2] == b"\xff\xd8":
        return ("image/jpeg", *_jpeg_size(data))
    raise NotAnImage("only JPEG, PNG, GIF and WebP images can be uploaded")


def _webp_size(data: bytes) -> tuple[int, int]:
    chunk = data[12:16]
    if chunk == b"VP8X":
        width = 1 + int.from_bytes(data[24:27], "little")
        height = 1 + int.from_bytes(data[27:30], "little")
        return width, height
    if chunk == b"VP8 " and len(data) >= 30:
        width, height = struct.unpack("<HH", data[26:30])
        return width & 0x3FFF, height & 0x3FFF
    if chunk == b"VP8L" and len(data) >= 25:
        bits = int.from_bytes(data[21:25], "little")
        return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    raise NotAnImage("this WebP file could not be read")


def _jpeg_size(data: bytes) -> tuple[int, int]:
    """Walk the markers to the first start-of-frame, which holds the size."""
    i = 2
    while i + 9 < len(data):
        if data[i] != 0xFF:
            raise NotAnImage("this JPEG file could not be read")
        marker = data[i + 1]
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        length = struct.unpack(">H", data[i + 2:i + 4])[0]
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            height, width = struct.unpack(">HH", data[i + 5:i + 9])
            return width, height
        i += 2 + length
    raise NotAnImage("this JPEG file could not be read")
