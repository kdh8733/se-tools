"""request - 캡처 요청을 요청 큐에 발행. Slack 봇 입력을 토큰 없이 CLI로 시뮬레이션(데모/테스트용).

실제 입력은 slackbot.py(!bmc / /bmc)가 동일한 capture_request를 발행한다."""
from __future__ import annotations

import argparse
import sys

from console_capture.config import Config, load_env_file
from console_capture.models import build_capture_request
from console_capture.mq import RedisMQ


def main(argv=None) -> int:
    load_env_file()
    cfg = Config.from_env()
    p = argparse.ArgumentParser(prog="console_capture-request",
                                description="캡처 요청 발행 (Slack 입력 시뮬레이션)")
    p.add_argument("query", help="SERIAL 또는 HOSTNAME")
    p.add_argument("--channel", default="local", help="결과를 돌려보낼 채널(데모는 local)")
    p.add_argument("--thread", default="", help="thread_ts")
    p.add_argument("--user", default="cli")
    args = p.parse_args(argv)

    req = build_capture_request(
        args.query,
        {"channel": args.channel, "thread_ts": args.thread, "user": args.user},
        source="cli",
    )
    mq = RedisMQ(cfg.redis_url, cfg.request_stream)
    stream_id = mq.publish(req)
    print(f"[request] published request_id={req['request_id']} query={args.query} "
          f"stream_id={stream_id}", file=sys.stderr)
    print(req["request_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
