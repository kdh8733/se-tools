import base64

from console_capture import pngutil
from console_capture.adapters import get_adapter, known_vendors, normalize_vendor
from console_capture.adapters.base import VendorAdapterPending
from console_capture.adapters.mock import MockAdapter
from console_capture.models import build_result_message


def test_vendor_normalize():
    assert normalize_vendor("idrac") == "dell"
    assert normalize_vendor("ILO") == "hpe"
    assert normalize_vendor("hp") == "hpe"
    assert normalize_vendor("xcc") == "lenovo"
    assert normalize_vendor("smc") == "supermicro"
    assert normalize_vendor("esxi") == "vmware"


def test_unknown_vendor_raises():
    try:
        normalize_vendor("nonsense")
        assert False, "should raise"
    except KeyError:
        pass


def test_mock_capture_roundtrip():
    res = MockAdapter().capture("10.0.0.1", "u", "p", hostname="srv-test")
    assert res.content_type == "image/png"
    assert (res.width, res.height) == (1024, 768)
    assert pngutil.dimensions(res.image) == (1024, 768)

    msg = build_result_message(res, "req-x", max_inline_bytes=921600)
    assert msg["status"] == "success"
    raw = base64.b64decode(msg["image"]["content_base64"])
    assert pngutil.detect_content_type(raw) == "image/png"
    assert pngutil.dimensions(raw) == (1024, 768)
    assert msg["image"]["content_type"] == "image/png"
    # png_signature_ok는 backend manifest 쪽 필드
    assert res.manifest()["png_signature_ok"] is True


def test_oversize_guard():
    res = MockAdapter().capture("10.0.0.1", "u", "p", hostname="srv-test")
    msg = build_result_message(res, "req-x", max_inline_bytes=10)  # 의도적으로 작게
    assert msg["status"] == "error"
    assert msg["error"]["code"] == "inline_payload_too_large"
    assert "content_base64" not in msg["image"]


def test_all_adapters_have_interface():
    for v in known_vendors():
        a = get_adapter(v)
        assert hasattr(a, "probe") and hasattr(a, "capture")


def test_pending_adapters_raise():
    for v in ("hpe", "supermicro", "vmware"):
        try:
            get_adapter(v).capture("1.2.3.4", "u", "p")
            assert False, f"{v} should raise VendorAdapterPending"
        except VendorAdapterPending:
            pass


def test_invalid_image_rejected():
    try:
        pngutil.detect_content_type(b"not an image")
        assert False, "should raise"
    except pngutil.InvalidImageError:
        pass


# ----- CMDB / Secret / worker (요청→캡처 경로) -----

def test_cmdb_resolve():
    from console_capture.cmdb import CmdbNotFound, LocalInventoryCmdb

    c = LocalInventoryCmdb("inventory.yaml")
    assert c.resolve("srv-mock-01").vendor == "mock"
    assert c.resolve("MOCK-0001").ipmi_ip == "192.0.2.10"  # serial로도 조회
    try:
        c.resolve("does-not-exist")
        assert False, "should raise"
    except CmdbNotFound:
        pass


def test_secret_resolve_fallback():
    from console_capture.secrets_resolver import LocalSecretResolver

    s = LocalSecretResolver(None)  # 파일 없음 -> mock/default 더미
    assert s.resolve("mock", "1.2.3.4").username == "mock"
    assert s.resolve("whatever", "1.2.3.4").username == "admin"  # default fallback


def test_request_and_error_builders():
    from console_capture.models import build_capture_request, build_error_message

    r = build_capture_request("srv-1", {"channel": "C1"}, "slack")
    assert r["type"] == "bmc_screen_request" and r["query"] == "srv-1" and r["request_id"]
    e = build_error_message("req-1", {"channel": "C1"}, "cmdb_lookup_failed", "msg", query="srv-1")
    assert e["status"] == "error" and e["error"]["code"] == "cmdb_lookup_failed"


def _worker_process(query):
    from console_capture import worker
    from console_capture.cmdb import LocalInventoryCmdb
    from console_capture.config import Config
    from console_capture.models import build_capture_request
    from console_capture.secrets_resolver import LocalSecretResolver

    cfg = Config.from_env()
    req = build_capture_request(query, {"channel": "local"}, "test")
    return worker.process(req, cfg, LocalInventoryCmdb("inventory.yaml"), LocalSecretResolver(None))


def test_worker_mock_success():
    out = _worker_process("srv-mock-01")
    assert out["status"] == "success"
    assert out["target"]["vendor"] == "mock"
    assert out["image"]["content_base64"]


def test_worker_cmdb_miss():
    out = _worker_process("nope-not-here")
    assert out["status"] == "error" and out["error"]["code"] == "cmdb_lookup_failed"


def test_worker_vendor_adapter_pending():
    out = _worker_process("srv-hpe-01")  # hpe capture -> VendorAdapterPending
    assert out["status"] == "error" and out["error"]["code"] == "vendor_adapter_pending"
