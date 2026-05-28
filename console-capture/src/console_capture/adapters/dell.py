"""Dell iDRAC 어댑터 - Redfish OEM ExportServerScreenShot (실코드, 타겟 도달 시 동작).

검증: 엔드포인트/응답 필드는 dell/iDRAC-Redfish-Scripting의 ExportServerScreenShotREDFISH.py 및
iDRAC9 Redfish API Guide 확인. 응답 JSON의 ServerScreenShotFile에 base64 이미지.
(덱 Path A. fw<7 RFB 풀스택은 이 어댑터 범위 밖 — 별도 구현 필요.)"""
from __future__ import annotations

import base64

import requests
import urllib3

from console_capture import pngutil
from console_capture.adapters.base import ProbeResult
from console_capture.models import CaptureResult

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_OEM_ACTION = ("/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/DellLCService/"
               "Actions/DellLCService.ExportServerScreenShot")


class DellAdapter:
    vendor = "dell"

    def _session_token(self, host, username, password, tls_verify) -> str:
        r = requests.post(
            f"https://{host}/redfish/v1/SessionService/Sessions",
            json={"UserName": username, "Password": password}, verify=tls_verify, timeout=15,
        )
        r.raise_for_status()
        token = r.headers.get("X-Auth-Token")
        if not token:
            raise RuntimeError("iDRAC에서 X-Auth-Token을 받지 못함")
        return token

    def probe(self, host, username, password, *, tls_verify=False):
        try:
            token = self._session_token(host, username, password, tls_verify)
            r = requests.get(f"https://{host}/redfish/v1/Managers/iDRAC.Embedded.1",
                             headers={"X-Auth-Token": token}, verify=tls_verify, timeout=15)
            fw = r.json().get("FirmwareVersion", "?")
            return ProbeResult(self.vendor, True, f"iDRAC fw={fw}; Redfish OEM screenshot 경로", True)
        except Exception as e:
            return ProbeResult(self.vendor, False, f"{type(e).__name__}: {e}", False)

    def capture(self, host, username, password, *, tls_verify=False, hostname=""):
        token = self._session_token(host, username, password, tls_verify)
        r = requests.post(f"https://{host}{_OEM_ACTION}", headers={"X-Auth-Token": token},
                          json={"FileType": "ServerScreenShot"}, verify=tls_verify, timeout=30)
        r.raise_for_status()
        raw = base64.b64decode(r.json()["ServerScreenShotFile"])
        ct = pngutil.detect_content_type(raw)
        w, h = pngutil.dimensions(raw)
        return CaptureResult(
            vendor=self.vendor, hostname=hostname or host, ip=host, image=raw,
            content_type=ct, width=w, height=h,
            backend="redfish-oem-screenshot", source_proof="redfish-oem-action",
            source_identifier=_OEM_ACTION,
        )
