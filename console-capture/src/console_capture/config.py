from __future__ import annotations

import os
from dataclasses import dataclass


def _bool(v: str | None, default: bool = False) -> bool:
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


def load_env_file(path: str = ".env") -> None:
    """python-dotenv 의존성 없이 .env를 환경변수로 로드(이미 설정된 값은 유지)."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip())


@dataclass(frozen=True)
class Config:
    redis_url: str
    stream: str            # 결과 큐
    request_stream: str    # 요청 큐
    group: str
    consumer: str
    slack_token: str | None
    slack_app_token: str | None
    slack_channel: str | None
    allowed_channels: tuple[str, ...]
    inventory: str
    secrets: str | None
    tls_verify: bool
    max_inline_bytes: int
    capture_dir: str
    upload_dir: str

    @classmethod
    def from_env(cls) -> "Config":
        allowed = os.getenv("CC_ALLOWED_CHANNELS", "").strip()
        return cls(
            redis_url=os.getenv("CC_REDIS_URL", "redis://127.0.0.1:6379/0"),
            stream=os.getenv("CC_STREAM", "bmc_screen_result"),
            request_stream=os.getenv("CC_REQUEST_STREAM", "bmc_screen_request"),
            group=os.getenv("CC_GROUP", "slackbot"),
            consumer=os.getenv("CC_CONSUMER", "consumer-1"),
            slack_token=os.getenv("SLACK_BOT_TOKEN") or None,
            slack_app_token=os.getenv("SLACK_APP_TOKEN") or None,
            slack_channel=os.getenv("SLACK_CHANNEL") or None,
            allowed_channels=tuple(c.strip() for c in allowed.split(",") if c.strip()),
            inventory=os.getenv("CC_INVENTORY", "inventory.yaml"),
            secrets=os.getenv("CC_SECRETS") or None,
            tls_verify=_bool(os.getenv("CC_TLS_VERIFY"), False),
            max_inline_bytes=int(os.getenv("CC_MAX_INLINE_BYTES", "921600")),
            capture_dir=os.getenv("CC_CAPTURE_DIR", "captures"),
            upload_dir=os.getenv("CC_UPLOAD_DIR", "uploads"),
        )
