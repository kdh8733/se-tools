"""합성 콘솔 스크린샷 생성기. 실 BMC가 없는 로컬 PC에서 파이프라인 전체를 end-to-end로 돌리는 데모 엔진."""
from __future__ import annotations

import io
import os
import time

from PIL import Image, ImageDraw, ImageFont

from console_capture import pngutil
from console_capture.adapters.base import ProbeResult
from console_capture.models import CaptureResult

_W, _H = 1024, 768


def _font(size: int):
    for path in (r"C:\Windows\Fonts\consola.ttf", r"C:\Windows\Fonts\cour.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"):
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


class MockAdapter:
    vendor = "mock"

    def probe(self, host, username, password, *, tls_verify=False):
        return ProbeResult(self.vendor, True, "mock adapter (항상 사용 가능)", True)

    def capture(self, host, username, password, *, tls_verify=False, hostname=""):
        img = Image.new("RGB", (_W, _H), (8, 8, 16))
        d = ImageDraw.Draw(img)
        title, body = _font(28), _font(18)
        d.rectangle([0, 0, _W, 40], fill=(0, 90, 160))
        d.text((12, 6), "BMC VIRTUAL CONSOLE  (MOCK)", font=title, fill=(255, 255, 255))
        lines = [
            f"host      : {hostname or host}",
            f"bmc ip    : {host}",
            f"captured  : {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "POST .... CPU0 OK   Memory 512GB OK",
            "Initializing PCIe devices ...... done",
            "NIC1 link up 25Gbps   NIC2 link up 25Gbps",
            "Booting from disk ...",
            "[  OK  ] Reached target Multi-User System.",
            "",
            "login: _",
        ]
        y = 60
        for ln in lines:
            d.text((16, y), ln, font=body, fill=(0, 230, 120))
            y += 26
        # 색 막대 - 디코드/색 정합 눈검증용
        bars = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0),
                (0, 255, 255), (255, 0, 255), (255, 255, 255)]
        for i, c in enumerate(bars):
            d.rectangle([16 + i * 60, _H - 60, 16 + i * 60 + 56, _H - 20], fill=c)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        raw = buf.getvalue()
        w, h = pngutil.dimensions(raw)
        return CaptureResult(
            vendor=self.vendor, hostname=hostname or host, ip=host, image=raw,
            content_type="image/png", width=w, height=h,
            backend="mock-synthetic", source_proof="synthetic-generator", source_identifier="pillow",
        )
