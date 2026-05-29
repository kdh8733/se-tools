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


class VendorAdapterPending(RuntimeError):
    """벤더 어댑터가 아직 추가되지 않은 상태(실 환경에서 검증 후 단계적으로 추가)."""


@runtime_checkable
class CaptureAdapter(Protocol):
    vendor: str

    def probe(self, host: str, username: str, password: str, *, tls_verify: bool = False) -> ProbeResult:
        ...

    def capture(self, host: str, username: str, password: str, *,
                tls_verify: bool = False, hostname: str = "") -> CaptureResult:
        ...
