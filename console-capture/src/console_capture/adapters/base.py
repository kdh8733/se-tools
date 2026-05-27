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


class NotImplementedInMVP(RuntimeError):
    """실 캡처 경로가 MVP 범위 밖(디코더/라이선스/미검증 API)일 때."""


@runtime_checkable
class CaptureAdapter(Protocol):
    vendor: str

    def probe(self, host: str, username: str, password: str, *, tls_verify: bool = False) -> ProbeResult:
        ...

    def capture(self, host: str, username: str, password: str, *,
                tls_verify: bool = False, hostname: str = "") -> CaptureResult:
        ...
