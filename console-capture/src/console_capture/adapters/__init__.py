"""벤더 어댑터 레지스트리 + 이름 정규화 (덱 p23: alias -> canonical)."""
from __future__ import annotations

from console_capture.adapters import dell, hpe, lenovo, mock, supermicro, vmware

# CLI/Slack이 쓰는 alias -> 내부 canonical 벤더명
_ALIAS = {
    "mock": "mock", "fake": "mock", "demo": "mock",
    "dell": "dell", "idrac": "dell",
    "hpe": "hpe", "hp": "hpe", "ilo": "hpe",
    "lenovo": "lenovo", "xcc": "lenovo",
    "supermicro": "supermicro", "smc": "supermicro", "smci": "supermicro",
    "vmware": "vmware", "esxi": "vmware",
}

_REGISTRY = {
    "mock": mock.MockAdapter(),
    "dell": dell.DellAdapter(),
    "hpe": hpe.HpeAdapter(),
    "lenovo": lenovo.LenovoAdapter(),
    "supermicro": supermicro.SupermicroAdapter(),
    "vmware": vmware.VmwareAdapter(),
}


def normalize_vendor(vendor: str) -> str:
    key = vendor.strip().lower()
    if key not in _ALIAS:
        raise KeyError(f"unknown vendor '{vendor}'. known aliases: {sorted(_ALIAS)}")
    return _ALIAS[key]


def get_adapter(vendor: str):
    return _REGISTRY[normalize_vendor(vendor)]


def known_vendors() -> list[str]:
    return sorted(_REGISTRY)
