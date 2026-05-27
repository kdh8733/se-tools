"""Slack 봇 - !bmc 메시지 prefix 와 /bmc 슬래시 커맨드 둘 다 지원 (Socket Mode).

입력을 받아 capture_request만 발행한다(캡처/업로드는 worker/consumer 담당 - 즉시 ack 후 비동기).
토큰(xoxb-+xapp-)이 없으면 안내 후 종료. 토큰 없이 테스트하려면: python -m console_capture.request <query>"""
from __future__ import annotations

import re
import sys

from console_capture.config import Config, load_env_file
from console_capture.models import build_capture_request
from console_capture.mq import RedisMQ

HELP = (
    "*BMC 콘솔 스크린샷 봇*\n"
    "• `!bmc <SERIAL|HOSTNAME>` 또는 `/bmc <SERIAL|HOSTNAME>` — 해당 서버 콘솔 캡처\n"
    "• `!bmc help` — 도움말\n"
    "CMDB에서 벤더/IPMI IP를 찾아 캡처 후 같은 스레드에 이미지를 업로드합니다."
)


def parse_query(text: str) -> str | None:
    """'!bmc srv-01' / '/bmc help' / 'srv-01'(슬래시 인자) 모두 처리. help/빈값이면 None."""
    parts = (text or "").strip().split()
    if parts and parts[0].lower() in ("!bmc", "/bmc", "bmc"):
        parts = parts[1:]
    if not parts or parts[0].lower() == "help":
        return None
    return parts[0]


def main(argv=None) -> int:
    load_env_file()
    cfg = Config.from_env()
    if not (cfg.slack_token and cfg.slack_app_token):
        print("[slackbot] SLACK_BOT_TOKEN(xoxb-) + SLACK_APP_TOKEN(xapp-)가 필요합니다(Socket Mode).\n"
              "           토큰 없이 테스트하려면: python -m console_capture.request <SERIAL|HOSTNAME>",
              file=sys.stderr)
        return 2

    from slack_bolt import App
    from slack_bolt.adapter.socket_mode import SocketModeHandler

    app = App(token=cfg.slack_token)
    mq = RedisMQ(cfg.redis_url, cfg.request_stream)

    def dispatch(query, channel, thread_ts, user, say, ack=None):
        if ack:
            ack()
        if cfg.allowed_channels and channel not in cfg.allowed_channels:
            say(text=":no_entry: 이 채널에서는 BMC 캡처가 허용되지 않습니다.", thread_ts=thread_ts)
            return
        req = build_capture_request(
            query, {"channel": channel, "thread_ts": thread_ts or "", "user": user}, source="slack")
        mq.publish(req)
        say(text=f":mag: `{query}` 조회·캡처 중… (request_id `{req['request_id']}`)", thread_ts=thread_ts)

    @app.message(re.compile(r"(?i)^\s*!bmc\b"))
    def on_message(message, say):
        q = parse_query(message.get("text", ""))
        thread_ts = message.get("thread_ts") or message.get("ts")
        if q is None:
            say(text=HELP, thread_ts=thread_ts)
            return
        dispatch(q, message.get("channel"), thread_ts, message.get("user"), say)

    @app.command("/bmc")
    def on_slash(ack, command, say):
        q = parse_query(command.get("text", ""))
        if q is None:
            ack()
            say(text=HELP)
            return
        dispatch(q, command.get("channel_id"), None, command.get("user_id"), say, ack=ack)

    print(f"[slackbot] Socket Mode 시작. request_stream={cfg.request_stream}", file=sys.stderr)
    SocketModeHandler(app, cfg.slack_app_token).start()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
