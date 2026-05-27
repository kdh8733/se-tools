"""Consumer (Slack uploader) - 결과 큐 소비 -> base64 디코드/검증 -> PNG write -> reply(channel/thread)로 업로드.

status=error면 사람이 읽을 실패 메시지를 같은 스레드에 올린다(조용히 사라지지 않음). 토큰 없으면 로컬 sink."""
from __future__ import annotations

import base64
import hashlib
import os
import sys

from console_capture import pngutil, slack_sink
from console_capture.config import Config, load_env_file
from console_capture.mq import RedisMQ


def handle(msg: dict, cfg: Config) -> None:
    rid = msg.get("request_id")
    reply = msg.get("reply", {})
    channel = reply.get("channel") or cfg.slack_channel
    thread_ts = reply.get("thread_ts") or None
    tgt = msg.get("target", {})
    img = msg.get("image", {})

    if msg.get("status") != "success":
        err = msg.get("error", {})
        label = msg.get("query") or tgt.get("hostname") or rid
        text = f":warning: `{label}` 캡처 실패 — {err.get('code')}: {err.get('message')}"
        print(f"[consumer] {rid} error -> {slack_sink.post_text(cfg.slack_token, channel, thread_ts, text)}",
              file=sys.stderr)
        return

    b64 = img.get("content_base64")
    if not b64:  # oversize 등으로 인라인 미동봉
        text = f":warning: `{tgt.get('hostname')}` 이미지 인라인 미동봉 (delivery={img.get('delivery')})"
        print(f"[consumer] {rid} no-inline -> {slack_sink.post_text(cfg.slack_token, channel, thread_ts, text)}",
              file=sys.stderr)
        return

    raw = base64.b64decode(b64)
    if img.get("sha256") and hashlib.sha256(raw).hexdigest() != img["sha256"]:
        print(f"[consumer] {rid} sha256 mismatch -> drop", file=sys.stderr)
        return
    pngutil.detect_content_type(raw)  # signature 검증(실패 시 raise)

    os.makedirs(cfg.capture_dir, exist_ok=True)
    name = f"{tgt.get('hostname') or tgt.get('ip') or rid}.png"
    path = os.path.join(cfg.capture_dir, name)
    with open(path, "wb") as f:
        f.write(raw)
    print(f"[consumer] {rid} wrote {path} ({len(raw)}B)", file=sys.stderr)

    res = slack_sink.deliver_image(
        path, token=cfg.slack_token, channel=channel, thread_ts=thread_ts, upload_dir=cfg.upload_dir,
        title=f"BMC console - {tgt.get('hostname')} ({tgt.get('vendor')})",
        comment=f"request_id={rid} - {img.get('width')}x{img.get('height')}",
    )
    print(f"[consumer] {rid} delivered -> {res}", file=sys.stderr)


def main(argv=None) -> int:
    load_env_file()
    cfg = Config.from_env()
    argv = argv if argv is not None else sys.argv[1:]
    once = "--once" in argv

    mq = RedisMQ(cfg.redis_url, cfg.stream, cfg.group, cfg.consumer)
    print(f"[consumer] listening stream={cfg.stream} group={cfg.group} "
          f"slack={'on' if cfg.slack_token else 'LOCAL-SINK'}", file=sys.stderr)
    while True:
        batch = mq.consume(block_ms=2000)
        for msg_id, msg in batch:
            try:
                handle(msg, cfg)
            except Exception as e:  # 개별 메시지 실패가 루프를 죽이지 않게
                print(f"[consumer] handle error: {type(e).__name__}: {e}", file=sys.stderr)
            finally:
                mq.ack(msg_id)
        if once and not batch:
            break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
