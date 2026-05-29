"""Capture worker - 요청 큐 소비 -> CMDB resolve -> secret resolve -> 벤더 캡처 -> 결과 큐 발행.

덱의 BMC 망 안에서 도는 워커에 해당(아웃바운드로 broker에 붙음). 모든 실패는 status=error 결과로 발행해
consumer가 Slack 스레드에 사람이 읽을 메시지로 돌려준다(조용히 사라지지 않음)."""
from __future__ import annotations

import sys

from console_capture import pipeline
from console_capture.adapters import normalize_vendor
from console_capture.adapters.base import VendorAdapterPending
from console_capture.cmdb import CmdbError, LocalInventoryCmdb
from console_capture.config import Config, load_env_file
from console_capture.models import build_error_message
from console_capture.mq import RedisMQ
from console_capture.secrets_resolver import LocalSecretResolver


def process(req: dict, cfg: Config, cmdb, secrets) -> dict:
    rid = req.get("request_id")
    query = req.get("query", "")
    reply = req.get("reply", {})

    # 1) CMDB: serial/hostname -> vendor + ipmi_ip
    try:
        rec = cmdb.resolve(query)
    except CmdbError as e:
        return build_error_message(rid, reply, "cmdb_lookup_failed", str(e), query=query)

    try:
        vendor = normalize_vendor(rec.vendor)
    except KeyError as e:
        return build_error_message(rid, reply, "vendor_unknown", str(e), query=query,
                                   target={"hostname": rec.hostname, "vendor": rec.vendor, "ip": rec.ipmi_ip})
    target = {"hostname": rec.hostname, "vendor": vendor, "ip": rec.ipmi_ip, "serial": rec.serial}

    # 2) Secret store: 자격증명 (CMDB와 분리)
    try:
        cred = secrets.resolve(vendor, rec.ipmi_ip)
    except KeyError as e:
        return build_error_message(rid, reply, "secret_lookup_failed", str(e), query=query, target=target)

    # 3) 벤더 분기 캡처
    try:
        _, msg = pipeline.capture_to_message(
            vendor, rec.ipmi_ip, cred.username, cred.password,
            name=rec.hostname, request_id=rid, max_inline_bytes=cfg.max_inline_bytes,
            tls_verify=cfg.tls_verify, reply=reply,
        )
        return msg
    except VendorAdapterPending as e:
        return build_error_message(rid, reply, "vendor_adapter_pending", str(e), query=query, target=target)
    except Exception as e:  # 네트워크/인증/디코드 등 캡처 실패
        return build_error_message(rid, reply, "capture_failed", f"{type(e).__name__}: {e}",
                                   query=query, target=target)


def main(argv=None) -> int:
    load_env_file()
    cfg = Config.from_env()
    argv = argv if argv is not None else sys.argv[1:]
    once = "--once" in argv

    cmdb = LocalInventoryCmdb(cfg.inventory)
    secrets = LocalSecretResolver(cfg.secrets)
    req_mq = RedisMQ(cfg.redis_url, cfg.request_stream, f"{cfg.group}-worker", cfg.consumer)
    res_mq = RedisMQ(cfg.redis_url, cfg.stream)

    print(f"[worker] listening request_stream={cfg.request_stream} inventory={cfg.inventory} "
          f"secrets={cfg.secrets or '(default dummy)'}", file=sys.stderr)
    while True:
        batch = req_mq.consume(block_ms=2000)
        for msg_id, req in batch:
            try:
                out = process(req, cfg, cmdb, secrets)
                res_mq.publish(out)
                tag = (out.get("error", {}).get("code") if out.get("status") == "error"
                       else out.get("target", {}).get("vendor"))
                print(f"[worker] {req.get('request_id')} query={req.get('query')} "
                      f"-> {out.get('status')} ({tag})", file=sys.stderr)
            except Exception as e:
                print(f"[worker] fatal: {type(e).__name__}: {e}", file=sys.stderr)
            finally:
                req_mq.ack(msg_id)
        if once and not batch:
            break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
