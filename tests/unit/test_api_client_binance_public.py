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
    BinancePublicApiError,
    get_open_interest_hist,
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
