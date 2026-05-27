"""CMDB resolver - serial/hostname -> (vendor, ipmi_ip).

MVP는 로컬 YAML 인벤토리(LocalInventoryCmdb). 실 CMDB는 동일 인터페이스(CmdbResolver)를 따르는
API 구현체로 교체하면 된다(README 'CMDB 연동' 참고). 자격증명은 여기서 다루지 않는다 - SecretResolver 담당."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import yaml


@dataclass
class CmdbRecord:
    hostname: str
    serial: str
    vendor: str
    ipmi_ip: str


class CmdbError(RuntimeError):
    pass


class CmdbNotFound(CmdbError):
    pass


class CmdbAmbiguous(CmdbError):
    pass


@runtime_checkable
class CmdbResolver(Protocol):
    def resolve(self, query: str) -> CmdbRecord:
        ...


class LocalInventoryCmdb:
    """로컬 YAML 인벤토리 기반 resolver."""

    def __init__(self, path: str):
        self.path = path
        self._records = self._load(path)

    @staticmethod
    def _load(path: str) -> list[CmdbRecord]:
        if not os.path.exists(path):
            raise CmdbError(f"인벤토리 파일 없음: {path}")
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return [
            CmdbRecord(
                hostname=str(r.get("hostname", "")),
                serial=str(r.get("serial", "")),
                vendor=str(r.get("vendor", "")),
                ipmi_ip=str(r.get("ipmi_ip", "")),
            )
            for r in data.get("servers", [])
        ]

    def resolve(self, query: str) -> CmdbRecord:
        q = query.strip().lower()
        matches = [r for r in self._records if q in (r.serial.lower(), r.hostname.lower())]
        if not matches:
            raise CmdbNotFound(f"CMDB에서 '{query}'를 찾지 못함 (serial/hostname 기준)")
        if len(matches) > 1:
            raise CmdbAmbiguous(f"'{query}' 다중 매칭: {[m.hostname for m in matches]}")
        return matches[0]
