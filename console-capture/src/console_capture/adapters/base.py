from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from console_capture.models import CaptureResult


@dataclass
class ProbeResult:
    vendor: str
    reachable: bool
    detail: str
    can_capture: bool


class VendorCaptureNotSupported(RuntimeError):
    """벤더의 실 캡처 경로가 이 구현에서 미지원(디코더/라이선스/미검증 API)."""


@runtime_checkable
class CaptureAdapter(Protocol):
    vendor: str

    def probe(self, host: str, username: str, password: str, *, tls_verify: bool = False) -> ProbeResult:
        ...

    def capture(self, host: str, username: str, password: str, *,
                tls_verify: bool = False, hostname: str = "") -> CaptureResult:
        ...
