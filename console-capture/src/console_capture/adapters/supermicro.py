"""Supermicro 어댑터 - Redfish 도달성 probe까지 동작.

Supermicro는 Redfish(X10/H11+ fw 3.xx)·HTML5 KVM은 있으나, '현재 화면을 PNG로 주는' 전용 스크린샷
API는 공식 문서에서 확정되지 않아 추후 실 하드웨어에서 (a) IPMI raw/ikvm, (b) web CGI,
(c) Redfish OEM 중 이미지 제공 경로를 검증한 뒤 단계적으로 추가할 계획."""
from __future__ import annotations

import requests
import urllib3

from console_capture.adapters.base import ProbeResult, VendorAdapterPending

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class SupermicroAdapter:
    vendor = "supermicro"

    def probe(self, host, username, password, *, tls_verify=False):
        try:
            r = requests.get(f"https://{host}/redfish/v1/", verify=tls_verify, timeout=10)
            return ProbeResult(
                self.vendor, r.status_code == 200,
                f"Redfish root status={r.status_code}; screenshot API는 실HW에서 "
                f"IPMI/CGI/Redfish OEM 검증 후 단계적으로 추가 예정",
                False,
            )
        except Exception as e:
            return ProbeResult(self.vendor, False, f"{type(e).__name__}: {e}", False)

    def capture(self, host, username, password, *, tls_verify=False, hostname=""):
        raise VendorAdapterPending(
            "Supermicro 스크린샷 캡처 경로는 실 하드웨어에서 IPMI raw / web CGI / Redfish OEM 중 "
            "PNG 제공 경로를 검증한 뒤 추가 예정.")
