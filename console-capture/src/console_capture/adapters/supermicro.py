"""Supermicro 어댑터 - Redfish 도달성 probe까지만.

주의(검증 결과): Supermicro는 Redfish(X10/H11+ fw 3.xx)·HTML5 KVM은 있으나, '현재 화면을 PNG로 주는'
전용 스크린샷 API를 공식 문서로 확인하지 못했다. 단정하지 않고, 실 하드웨어에서
(a) IPMI raw/ikvm, (b) web CGI, (c) Redfish OEM 중 무엇이 이미지를 주는지 검증 후 구현 예정."""
from __future__ import annotations

import requests
import urllib3

from console_capture.adapters.base import NotImplementedInMVP, ProbeResult

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class SupermicroAdapter:
    vendor = "supermicro"

    def probe(self, host, username, password, *, tls_verify=False):
        try:
            r = requests.get(f"https://{host}/redfish/v1/", verify=tls_verify, timeout=10)
            return ProbeResult(
                self.vendor, r.status_code == 200,
                f"Redfish root status={r.status_code}; screenshot API 미확인 "
                f"(실HW에서 IPMI/CGI/Redfish OEM 검증 필요)",
                False,
            )
        except Exception as e:
            return ProbeResult(self.vendor, False, f"{type(e).__name__}: {e}", False)

    def capture(self, host, username, password, *, tls_verify=False, hostname=""):
        raise NotImplementedInMVP(
            "Supermicro 스크린샷 캡처 경로를 공식 문서로 확인하지 못했다. 실 하드웨어에서 "
            "IPMI raw / web CGI / Redfish OEM 중 PNG를 주는 경로를 검증한 뒤 구현할 것.")
