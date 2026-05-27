"""capture + 결과메시지 빌드 공유 로직. producer(직접 호출)와 worker(CMDB 경유)가 함께 쓴다."""
from __future__ import annotations

from console_capture.adapters import get_adapter
from console_capture.models import CaptureResult, build_result_message


def capture(vendor: str, host: str, username: str, password: str, *,
            name: str = "", tls_verify: bool = False) -> CaptureResult:
    return get_adapter(vendor).capture(host, username, password, tls_verify=tls_verify, hostname=name)


def capture_to_message(vendor: str, host: str, username: str, password: str, *,
                       name: str, request_id: str, max_inline_bytes: int,
                       tls_verify: bool = False, reply: dict | None = None):
    result = capture(vendor, host, username, password, name=name, tls_verify=tls_verify)
    return result, build_result_message(result, request_id, max_inline_bytes, reply=reply)
