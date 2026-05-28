"""Producer (manager) - 벤더 어댑터로 캡처 -> PNG 검증 -> base64 -> MQ 발행.

덱의 L1(manager) 책임: CLI 파싱 / vendor 정규화 / 캡처 오케스트레이션 / base64 / MQ 발행.
BMC 프로토콜은 모른다(어댑터가 담당)."""
from __future__ import annotations

import argparse
import copy
import json
import sys
import uuid

from console_capture import pipeline
from console_capture.adapters import get_adapter, known_vendors, normalize_vendor
from console_capture.adapters.base import VendorCaptureNotSupported
from console_capture.config import Config, load_env_file
from console_capture.mq import RedisMQ


def _redacted(msg: dict) -> dict:
    m = copy.deepcopy(msg)
    b64 = m.get("image", {}).get("content_base64")
    if b64:
        m["image"]["content_base64"] = f"<{len(b64)} base64 chars>"
    return m


def main(argv=None) -> int:
    load_env_file()
    cfg = Config.from_env()
    p = argparse.ArgumentParser(prog="console_capture-producer",
                                description="BMC/VM 콘솔 캡처 -> Message Queue 발행")
    p.add_argument("-V", "--vendor", required=True, help=f"벤더(alias 허용): {known_vendors()}")
    p.add_argument("-H", "--host", required=True, help="BMC/ESXi IP 또는 host")
    p.add_argument("-N", "--name", default="", help="논리 hostname (기본: host)")
    p.add_argument("-u", "--username", default="admin")
    p.add_argument("-p", "--password", default="")
    p.add_argument("--request-id", default=None)
    p.add_argument("--probe", action="store_true", help="capture 대신 capability probe만 수행")
    p.add_argument("--no-publish", action="store_true", help="MQ 발행 없이 결과를 stdout에만 출력")
    args = p.parse_args(argv)

    vendor = normalize_vendor(args.vendor)
    adapter = get_adapter(vendor)
    print(f"[mgr] normalize {args.vendor} -> {vendor}", file=sys.stderr)

    if args.probe:
        pr = adapter.probe(args.host, args.username, args.password, tls_verify=cfg.tls_verify)
        print(json.dumps(pr.__dict__, ensure_ascii=False, indent=2))
        return 0 if pr.reachable else 4

    rid = args.request_id or f"req-{uuid.uuid4().hex[:8]}"
    try:
        result, msg = pipeline.capture_to_message(
            vendor, args.host, args.username, args.password, name=args.name,
            request_id=rid, max_inline_bytes=cfg.max_inline_bytes, tls_verify=cfg.tls_verify)
    except VendorCaptureNotSupported as e:
        print(f"[mgr] {vendor} capture not supported: {e}", file=sys.stderr)
        return 3

    print(f"[mgr] captured {result.width}x{result.height} {result.byte_size}B "
          f"backend={result.backend}", file=sys.stderr)

    if args.no_publish:
        print(json.dumps(_redacted(msg), ensure_ascii=False, indent=2))
        return 0

    mq = RedisMQ(cfg.redis_url, cfg.stream)
    stream_id = mq.publish(msg)
    print(f"[mq] published request_id={rid} status={msg['status']} stream_id={stream_id}", file=sys.stderr)
    print(rid)  # stdout: request_id (스크립트 연계용)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
