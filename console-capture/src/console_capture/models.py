"""캡처 결과 모델 + MQ 메시지 계약. 덱 p25의 backend manifest / inline result / Kafka 메시지 구조를 따른다."""
from __future__ import annotations

import base64
import hashlib
import time
import uuid
from dataclasses import dataclass


@dataclass
class CaptureResult:
    vendor: str
    hostname: str
    ip: str
    image: bytes
    content_type: str
    width: int
    height: int
    backend: str
    source_proof: str
    source_identifier: str = ""

    @property
    def byte_size(self) -> int:
        return len(self.image)

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.image).hexdigest()

    @property
    def base64(self) -> str:
        return base64.b64encode(self.image).decode("ascii")

    def manifest(self) -> dict:
        return {
            "backend": self.backend,
            "source_proof": self.source_proof,
            "source_identifier": self.source_identifier,
            "content_type": self.content_type,
            "byte_size": self.byte_size,
            "width": self.width,
            "height": self.height,
            "png_signature_ok": self.content_type == "image/png",
        }


def build_result_message(result: CaptureResult, request_id: str, max_inline_bytes: int,
                         reply: dict | None = None) -> dict:
    """MQ에 실을 메시지 생성. base64가 한도를 넘으면 덱과 동일하게 status=error + inline_payload_too_large."""
    b64 = result.base64
    image = {
        "delivery": "inline_base64",
        "content_type": result.content_type,
        "byte_size": result.byte_size,
        "sha256": result.sha256,
        "width": result.width,
        "height": result.height,
    }
    msg = {
        "type": "bmc_screen_result",
        "request_id": request_id,
        "ts": int(time.time()),
        "target": {"hostname": result.hostname, "vendor": result.vendor, "ip": result.ip},
        "reply": reply or {},
    }
    if len(b64) > max_inline_bytes:
        msg["status"] = "error"
        msg["error"] = {
            "code": "inline_payload_too_large",
            "message": f"base64 {len(b64)}B > limit {max_inline_bytes}B",
        }
        msg["image"] = image  # content_base64 생략 (덱: 초과 시 인라인 미동봉)
    else:
        msg["status"] = "success"
        image["content_base64"] = b64
        msg["image"] = image
    return msg


def build_capture_request(query: str, reply: dict, source: str, request_id: str | None = None) -> dict:
    """Slack/CLI 입력 -> 요청 큐 메시지. reply는 결과를 돌려보낼 곳(channel/thread/user)."""
    return {
        "type": "bmc_screen_request",
        "request_id": request_id or f"req-{uuid.uuid4().hex[:8]}",
        "ts": int(time.time()),
        "query": query,
        "reply": reply or {},
        "source": source,
    }


def build_error_message(request_id: str, reply: dict, code: str, message: str,
                        query: str | None = None, target: dict | None = None) -> dict:
    """캡처 실패(CMDB 미스/벤더 미지원/캡처 오류)를 결과 큐로. consumer가 스레드에 사람이 읽을 메시지로."""
    return {
        "type": "bmc_screen_result",
        "request_id": request_id,
        "ts": int(time.time()),
        "status": "error",
        "error": {"code": code, "message": message},
        "query": query,
        "target": target or {},
        "reply": reply or {},
    }
