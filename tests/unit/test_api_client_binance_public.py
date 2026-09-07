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
    BASE_URL,
    BinancePrivateApiError,
    BinancePublicApiError,
    _sign,
    get_open_interest_hist,
    latency_samples_ms,
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


def _fake_conn(status: int = 200, body: bytes = b"{}") -> MagicMock:
    conn = MagicMock()
    resp = MagicMock()
    resp.status = status
    resp.read.return_value = body
    conn.getresponse.return_value = resp
    return conn


class TestLatencySamplesMs:
    """TD-0116 (H15) — testnet đã bị LOẠI bằng bằng chứng mã nguồn
    (Freqtrade `supports_demo_trading: False` cho Binance, cố ý), nên
    phép đo chạy trên production."""

    def test_khong_con_testnet_trong_module(self) -> None:
        import tool_d.api_client.binance_public as mod

        assert not hasattr(mod, "TESTNET_BASE_URL")
        assert "testnet" not in BASE_URL

    def test_lay_dung_so_mau_yeu_cau(self) -> None:
        with patch("http.client.HTTPSConnection", return_value=_fake_conn()):
            samples = latency_samples_ms(n=5, signed=False, reuse_connection=True)
        assert len(samples) == 5
        assert all(s >= 0.0 for s in samples)

    def test_reuse_connection_chi_mo_MOT_ket_noi(self) -> None:
        with patch("http.client.HTTPSConnection", return_value=_fake_conn()) as mock_conn:
            latency_samples_ms(n=10, signed=False, reuse_connection=True)
        assert mock_conn.call_count == 1  # ẤM: dùng lại, không bắt tay TLS lại

    def test_khong_reuse_thi_moi_mau_mot_ket_noi_moi(self) -> None:
        with patch("http.client.HTTPSConnection", return_value=_fake_conn()) as mock_conn:
            latency_samples_ms(n=10, signed=False, reuse_connection=False)
        assert mock_conn.call_count == 10  # LẠNH: mỗi mẫu cõng một bắt tay TLS

    def test_signed_gui_dung_header_va_khong_lo_secret(self) -> None:
        conn = _fake_conn()
        with patch("http.client.HTTPSConnection", return_value=conn):
            latency_samples_ms(
                n=1,
                signed=True,
                reuse_connection=True,
                api_key="fake_key",
                api_secret="fake_secret_value",
            )
        method, path = conn.request.call_args[0][0], conn.request.call_args[0][1]
        headers = conn.request.call_args[1]["headers"]
        assert method == "POST" and path.startswith("/fapi/v1/order/test?")
        assert headers["X-MBX-APIKEY"] == "fake_key"
        # Secret KHÔNG BAO GIỜ đi ra khỏi máy — chỉ chữ ký (hash một chiều).
        assert "fake_secret_value" not in path

    def test_khong_signed_dung_endpoint_public_lam_doi_chung(self) -> None:
        conn = _fake_conn()
        with patch("http.client.HTTPSConnection", return_value=conn):
            latency_samples_ms(n=1, signed=False, reuse_connection=True)
        method, path = conn.request.call_args[0][0], conn.request.call_args[0][1]
        assert method == "GET" and path == "/fapi/v1/time"
        assert conn.request.call_args[1]["headers"] == {}  # không gửi khoá cho endpoint public

    def test_signed_thieu_khoa_thi_raise_som_khong_goi_mang(self) -> None:
        with patch("http.client.HTTPSConnection") as mock_conn:
            with pytest.raises(ValueError):
                latency_samples_ms(n=1, signed=True, reuse_connection=True, api_key="", api_secret="")
        mock_conn.assert_not_called()

    def test_http_khong_200_thi_raise_khong_ghi_mau_rac(self) -> None:
        with patch("http.client.HTTPSConnection", return_value=_fake_conn(status=401, body=b"bad key")):
            with pytest.raises(BinancePrivateApiError, match="401"):
                latency_samples_ms(n=3, signed=False, reuse_connection=True)

    def test_loi_mang_thi_raise_binance_private_api_error(self) -> None:
        conn = _fake_conn()
        conn.request.side_effect = OSError("mô phỏng đứt mạng")
        with patch("http.client.HTTPSConnection", return_value=conn):
            with pytest.raises(BinancePrivateApiError):
                latency_samples_ms(n=1, signed=False, reuse_connection=True)

    def test_n_khong_hop_le_thi_raise(self) -> None:
        with pytest.raises(ValueError):
            latency_samples_ms(n=0, signed=False, reuse_connection=True)
