"""VMware ESXi 어댑터 - 라이선스 환경 확보 후 구현 예정. 현재는 구성/스캐폴딩.

실 경로(README 참고):
  - vim25 SOAP CreateScreenshot_Task -> datastore에 PNG 저장 -> datastore HTTP로 다운로드
  - 또는 /screen?id={moid} (Basic auth, image/png 직접 반환)
둘 다 BMC가 아니라 hypervisor가 VM 콘솔 프레임버퍼를 캡처한다(게스트 내부 에이전트 불필요)."""
from __future__ import annotations

from console_capture.adapters.base import ProbeResult, VendorAdapterPending


class VmwareAdapter:
    vendor = "vmware"

    def probe(self, host, username, password, *, tls_verify=False):
        return ProbeResult(
            self.vendor, False,
            "VMware는 라이선스 환경 확보 후 검증 예정. 경로: vim25 CreateScreenshot_Task 또는 /screen?id={moid}",
            False,
        )

    def capture(self, host, username, password, *, tls_verify=False, hostname=""):
        raise VendorAdapterPending(
            "VMware ESXi VM 콘솔 캡처는 vim25 SOAP(CreateScreenshot_Task->datastore) 또는 "
            "/screen?id={moid} 경로. 라이선스 환경 확보 후 구현 예정 — 현재는 구성만.")
