"""TD-0080 — api_client/binance_public.py. Test đơn vị dùng mock (không
phụ thuộc mạng thật để chạy nhanh/ổn định) — bằng chứng THẬT về độ phủ
30 ngày của OI history đã xác nhận bằng tay (curl trực tiếp) và bằng
`entrypoints/backfill_data.py --probe-coverage` thật, ghi ở
`docs/research-log.md`, không lặp lại ở đây (đúng L-Z51: không coi mock
là "đạt" cho phát hiện thật).
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from tool_d.api_client.binance_public import (
    TESTNET_BASE_URL,
    BinancePrivateApiError,
    BinancePublicApiError,
    _sign,
    get_open_interest_hist,
    order_test_latency_ms,
)


def _fake_response(payload: list[dict]) -> MagicMock:
    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = json.dumps(payload).encode()
    return cm


class TestGetOpenInterestHist:
    def test_goi_dung_url_va_tra_ve_du_lieu(self) -> None:
        payload = [{"symbol": "BTCUSDT", "timestamp": 1000}]
        with patch("tool_d.api_client.binance_public.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = _fake_response(payload)
            result = get_open_interest_hist(symbol="BTCUSDT", period="1d", limit=500)
        assert result == payload
        called_url = mock_urlopen.call_args[0][0]
        assert "symbol=BTCUSDT" in called_url
        assert "period=1d" in called_url
        assert "limit=500" in called_url

    def test_limit_ngoai_khoang_thi_raise_khong_tu_sua(self) -> None:
        with pytest.raises(ValueError):
            get_open_interest_hist(symbol="BTCUSDT", limit=501)
        with pytest.raises(ValueError):
            get_open_interest_hist(symbol="BTCUSDT", limit=0)

    def test_loi_mang_thi_raise_binance_public_api_error(self) -> None:
        with patch("tool_d.api_client.binance_public.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = TimeoutError("mô phỏng timeout")
            with pytest.raises(BinancePublicApiError):
                get_open_interest_hist(symbol="BTCUSDT")

    def test_json_hong_thi_raise_khong_tra_du_lieu_rac(self) -> None:
        cm = MagicMock()
        cm.__enter__.return_value.read.return_value = b"khong phai json"
        with patch("tool_d.api_client.binance_public.urllib.request.urlopen", return_value=cm):
            with pytest.raises(BinancePublicApiError):
                get_open_interest_hist(symbol="BTCUSDT")


class TestProbeCoverageEntrypoint:
    """Kiểm logic tính toán của probe_oi_coverage() bằng dữ liệu giả lập
    — KHÔNG thay thế bằng chứng thật (đã ghi research-log riêng)."""

    def test_tinh_dung_khoang_ngay_tu_du_lieu_gia_lap(self) -> None:
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "entrypoints"))
        from backfill_data import probe_oi_coverage

        fake_data = [
            {"symbol": "BTCUSDT", "timestamp": 1754524800000},  # 2025-08-07 UTC (ví dụ)
            {"symbol": "BTCUSDT", "timestamp": 1757116800000},  # 30 ngày sau
        ]
        with patch(
            "backfill_data.get_open_interest_hist", return_value=fake_data
        ):
            text = probe_oi_coverage("BTCUSDT")
        assert "2 bản ghi" in text
        assert "30 ngày" in text

    def test_du_lieu_rong_thi_bao_khong_do_duoc(self) -> None:
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "entrypoints"))
        from backfill_data import probe_oi_coverage

        with patch("backfill_data.get_open_interest_hist", return_value=[]):
            text = probe_oi_coverage("BTCUSDT")
        assert "không đo được" in text


class TestSign:
    """`_sign()` phải là HMAC-SHA256 chuẩn Binance — chữ ký sai/dấu sai
    làm sàn từ chối lặng lẽ (cùng dạng lỗi LD-14 đã gặp ở DG7)."""

    def test_vector_co_dinh_dung_hmac_sha256(self) -> None:
        # Vector tự tính bằng hashlib độc lập, không copy từ tài liệu
        # Binance — chỉ xác nhận _sign() dùng đúng thuật toán/encoding.
        import hashlib
        import hmac as hmac_module
        import urllib.parse

        params = {"symbol": "BTCUSDT", "timestamp": "123456"}
        expected = hmac_module.new(
            b"mysecret", urllib.parse.urlencode(params).encode("utf-8"), hashlib.sha256
        ).hexdigest()
        assert _sign(params, "mysecret") == expected

    def test_doi_secret_thi_doi_chu_ky(self) -> None:
        params = {"symbol": "BTCUSDT", "timestamp": "123456"}
        assert _sign(params, "secret_a") != _sign(params, "secret_b")


class TestOrderTestLatencyMs:
    def test_mac_dinh_dung_testnet_khong_phai_production(self) -> None:
        import inspect

        default_base_url = inspect.signature(order_test_latency_ms).parameters["base_url"].default
        assert default_base_url == TESTNET_BASE_URL
        assert "testnet" in TESTNET_BASE_URL

    def test_goi_thanh_cong_tra_ve_latency_khong_am(self) -> None:
        cm = MagicMock()
        cm.__enter__.return_value.read.return_value = b"{}"
        with patch("tool_d.api_client.binance_public.urllib.request.urlopen", return_value=cm):
            latency = order_test_latency_ms(api_key="fake_key", api_secret="fake_secret")
        assert latency >= 0.0

    def test_request_ky_dung_bang_api_key_va_khong_lo_secret_vao_url(self) -> None:
        cm = MagicMock()
        cm.__enter__.return_value.read.return_value = b"{}"
        with patch("tool_d.api_client.binance_public.urllib.request.urlopen", return_value=cm) as mock_urlopen:
            order_test_latency_ms(api_key="fake_key", api_secret="fake_secret_value")
        sent_request = mock_urlopen.call_args[0][0]
        # `Request.add_header()` lưu khoá dưới dạng `.capitalize()` --
        # tra lại đúng casing đã lưu ("X-mbx-apikey"), không phải chuỗi
        # gốc truyền vào lúc tạo request.
        assert sent_request.get_header("X-mbx-apikey") == "fake_key"
        assert sent_request.method == "POST"
        # Secret KHÔNG BAO GIỜ xuất hiện trực tiếp trong URL — chỉ chữ
        # ký (hash một chiều) mới được gửi đi.
        assert "fake_secret_value" not in sent_request.full_url

    def test_loi_mang_thi_raise_binance_private_api_error(self) -> None:
        with patch("tool_d.api_client.binance_public.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = TimeoutError("mô phỏng timeout")
            with pytest.raises(BinancePrivateApiError):
                order_test_latency_ms(api_key="fake_key", api_secret="fake_secret")
