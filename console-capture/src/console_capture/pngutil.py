"""이미지 bytes 검증/치수 파싱 (stdlib만). 덱의 'TRUST THE BYTES' 원칙 - content-type 헤더가 아니라
실제 signature로 판단한다."""
from __future__ import annotations

import struct

PNG_SIG = b"\x89PNG\r\n\x1a\n"
JPEG_SIG = b"\xff\xd8"


class InvalidImageError(ValueError):
    pass


def detect_content_type(raw: bytes) -> str:
    if raw[:8] == PNG_SIG:
        return "image/png"
    if raw[:2] == JPEG_SIG:
        return "image/jpeg"
    raise InvalidImageError("PNG/JPEG signature 불일치 - 캡처 bytes가 이미지가 아님")


def _png_dimensions(raw: bytes) -> tuple[int, int]:
    if raw[:8] != PNG_SIG or raw[12:16] != b"IHDR":
        raise InvalidImageError("PNG IHDR 없음")
    w, h = struct.unpack(">II", raw[16:24])
    return w, h


def _jpeg_dimensions(raw: bytes) -> tuple[int, int]:
    i, n = 2, len(raw)
    while i < n - 9:
        if raw[i] != 0xFF:
            i += 1
            continue
        marker = raw[i + 1]
        if marker in (0xC0, 0xC1, 0xC2, 0xC3):
            h = struct.unpack(">H", raw[i + 5:i + 7])[0]
            w = struct.unpack(">H", raw[i + 7:i + 9])[0]
            return w, h
        seg_len = struct.unpack(">H", raw[i + 2:i + 4])[0]
        i += 2 + seg_len
    raise InvalidImageError("JPEG SOF 마커 없음")


def dimensions(raw: bytes) -> tuple[int, int]:
    return _png_dimensions(raw) if detect_content_type(raw) == "image/png" else _jpeg_dimensions(raw)
