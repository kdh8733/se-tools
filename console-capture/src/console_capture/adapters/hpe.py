"""HPE iLO 어댑터 - Redfish 세션 + capability probe까지 실코드.

live capture(/wss/ircport StateMachine 49-state 디코더)는 별도 백엔드 영역이라 capture()는 명시적으로 막는다.
probe로 GraphicalConsole/KVMIP 활성 여부를 확인하는 것까지가 이 어댑터의 책임."""
from __future__ import annotations

import requests
import urllib3

from console_capture.adapters.base import ProbeResult, VendorCaptureNotSupported

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class HpeAdapter:
    vendor = "hpe"

    def probe(self, host, username, password, *, tls_verify=False):
        try:
            base = f"https://{host}"
            r = requests.post(f"{base}/redfish/v1/SessionService/Sessions",
                              json={"UserName": username, "Password": password},
                              verify=tls_verify, timeout=15)
            r.raise_for_status()
            token = r.headers.get("X-Auth-Token")
            mgr = requests.get(f"{base}/redfish/v1/Managers/1/", headers={"X-Auth-Token": token},
                               verify=tls_verify, timeout=15).json()
            gc = mgr.get("GraphicalConsole", {})
            enabled = bool(gc.get("ServiceEnabled"))
            kvmip = "KVMIP" in gc.get("ConnectTypesSupported", [])
            return ProbeResult(
                self.vendor, True,
                f"iLO GraphicalConsole.ServiceEnabled={enabled}, KVMIP={kvmip}; "
                f"live framebuffer decode는 별도 live-frame 백엔드 영역(이 어댑터 미포함)",
                enabled and kvmip,
            )
        except Exception as e:
            return ProbeResult(self.vendor, False, f"{type(e).__name__}: {e}", False)

    def capture(self, host, username, password, *, tls_verify=False, hostname=""):
        raise VendorCaptureNotSupported(
            "HPE iLO live capture는 /wss/ircport StateMachine(49-state) + ColorCache 디코더가 필요해 "
            "이 어댑터의 범위 밖이다. probe로 capability만 확인하고, 실 캡처는 별도 ilo live-frame 백엔드에서 처리.")
