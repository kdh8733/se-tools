"""Message Queue 추상화 - Redis Streams 구현.

Redis Streams는 consumer group + ack를 제공해 덱의 Kafka consumer-group 시맨틱을 로컬에서 1:1로 흉내낸다.
프로덕션에서 Kafka로 바꿀 때 이 클래스의 publish/consume/ack 인터페이스만 맞추면 된다."""
from __future__ import annotations

import json

import redis


class RedisMQ:
    def __init__(self, url: str, stream: str, group: str | None = None, consumer: str | None = None):
        self.r = redis.from_url(url, decode_responses=True)
        self.stream = stream
        self.group = group
        self.consumer = consumer

    def ping(self) -> bool:
        return self.r.ping()

    def publish(self, message: dict) -> str:
        return self.r.xadd(self.stream, {"data": json.dumps(message, ensure_ascii=False)})

    def ensure_group(self) -> None:
        try:
            # id="0": 그룹 생성 시점 이전 메시지도 ">"로 받을 수 있게 스트림 처음부터.
            self.r.xgroup_create(self.stream, self.group, id="0", mkstream=True)
        except redis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

    def consume(self, block_ms: int = 2000, count: int = 10) -> list[tuple[str, dict]]:
        self.ensure_group()
        resp = self.r.xreadgroup(self.group, self.consumer, {self.stream: ">"}, count=count, block=block_ms)
        out: list[tuple[str, dict]] = []
        if resp:
            _, entries = resp[0]
            for msg_id, fields in entries:
                out.append((msg_id, json.loads(fields["data"])))
        return out

    def ack(self, msg_id: str) -> None:
        self.r.xack(self.stream, self.group, msg_id)
