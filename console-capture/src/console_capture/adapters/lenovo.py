"""Lenovo XCC 어댑터 - rp_screenshot 4-call flow (실코드, 디코더 0줄).

덱 p19: get_nonce -> login -> rp_screenshot 트리거 -> /download/HostScreenShot.png.
BMC가 직접 PNG를 만들어 디스크에 떨구므로 디코더가 필요 없다. content-type 대신 실제 bytes signature로 판단."""
from __future__ import annotations

import requests
import urllib3

from console_capture import pngutil
from console_capture.adapters.base import ProbeResult
from console_capture.models import CaptureResult

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class LenovoAdapter:
    vendor = "lenovo"

    def _login(self, host, username, password, tls_verify):
        s = requests.Session()
        s.verify = tls_verify
        base = f"https://{host}"
        nonce = s.post(f"{base}/api/providers/get_nonce", timeout=15).json().get("nonce", "")
        r = s.post(f"{base}/api/login",
                   headers={"Content-Security-Policy": f"nonce={nonce}"},
                   json={"username": username, "password": password}, timeout=15)
        r.raise_for_status()
        token = r.json().get("access_token")
        if not token:
            raise RuntimeError("XCC에서 access_token을 받지 못함")
        s.headers["Authorization"] = f"Bearer {token}"
        return s, base

    def probe(self, host, username, password, *, tls_verify=False):
        try:
            self._login(host, username, password, tls_verify)
            return ProbeResult(self.vendor, True, "XCC 로그인 OK; rp_screenshot 경로", True)
        except Exception as e:
            return ProbeResult(self.vendor, False, f"{type(e).__name__}: {e}", False)

    def capture(self, host, username, password, *, tls_verify=False, hostname=""):
        s, base = self._login(host, username, password, tls_verify)
        trig = s.get(f"{base}/api/providers/rp_screenshot", timeout=30).json()
        if trig.get("return", 0) != 0:
            raise RuntimeError(f"rp_screenshot 트리거 실패: {trig}")
        r = s.get(f"{base}/download/HostScreenShot.png", timeout=30)
        r.raise_for_status()
        raw = r.content
        ct = pngutil.detect_content_type(raw)
        w, h = pngutil.dimensions(raw)
        return CaptureResult(
            vendor=self.vendor, hostname=hostname or host, ip=host, image=raw,
            content_type=ct, width=w, height=h,
            backend="xcc-web-rp-screenshot", source_proof="built-in-capture-action",
            source_identifier="/download/HostScreenShot.png",
        )
