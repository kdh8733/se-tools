"""Secret resolver - (vendor, ipmi_ip) -> 로그인 자격증명.

CMDB는 IP/vendor만 준다. 자격증명은 절대 CMDB나 코드에 두지 말고 여기서 분리 조회한다.
MVP는 로컬 YAML(LocalSecretResolver). 운영에서는 Vault/AWS Secrets Manager 구현체로 교체(OPERATIONS.md)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import yaml

# 시크릿 파일이 없을 때의 안전한 더미(주로 mock 데모용). 실 벤더는 secrets.yaml 필요.
_DEFAULT_DUMMY = {
    "default": {"username": "admin", "password": "changeme"},
    "mock": {"username": "mock", "password": "mock"},
}


@dataclass
class Credential:
    username: str
    password: str


@runtime_checkable
class SecretResolver(Protocol):
    def resolve(self, vendor: str, ip: str) -> Credential:
        ...


class LocalSecretResolver:
    """로컬 YAML 시크릿 파일 기반. 파일 없으면 mock/default 더미로 동작."""

    def __init__(self, path: str | None = None):
        self.path = path
        self._store = self._load(path)

    @staticmethod
    def _load(path: str | None) -> dict:
        if path and os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return dict(_DEFAULT_DUMMY)

    def resolve(self, vendor: str, ip: str) -> Credential:
        # 우선순위: "<vendor>:<ip>" > "<vendor>" > "default"
        for key in (f"{vendor}:{ip}", vendor, "default"):
            entry = self._store.get(key)
            if entry:
                return Credential(username=str(entry.get("username", "")),
                                  password=str(entry.get("password", "")))
        raise KeyError(f"자격증명 없음: vendor={vendor} ip={ip} (secrets 파일/default 확인)")
