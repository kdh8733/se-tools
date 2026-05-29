"""HPE iLO 어댑터 - Redfish 세션 + capability probe까지 실코드.

live capture(/wss/ircport StateMachine 49-state 디코더)는 추후 별도 live-frame 디코더로 확장 예정.
현재는 probe로 GraphicalConsole/KVMIP 활성 여부를 확인하는 것까지 동작."""
from __future__ import annotations

import requests
import urllib3

from console_capture.adapters.base import ProbeResult, VendorAdapterPending

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
                f"live framebuffer decode는 추후 별도 디코더로 확장 예정",
                enabled and kvmip,
            )
        except Exception as e:
            return ProbeResult(self.vendor, False, f"{type(e).__name__}: {e}", False)

    def capture(self, host, username, password, *, tls_verify=False, hostname=""):
        raise VendorAdapterPending(
            "HPE iLO live capture는 /wss/ircport StateMachine(49-state) + ColorCache 디코더 구현이 필요. "
            "추후 별도 live-frame 백엔드로 확장 예정 — 현재는 probe로 capability 확인까지 제공.")
