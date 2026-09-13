"""TD-0241 (`DR-D11-03`) — `api_client/freqtrade_control.py`. Mock mạng,
không phụ thuộc một bot Freqtrade sống (đó là việc D11 — xem docstring
module: bằng chứng ENDPOINT/idempotency/auth đã xác nhận bằng đọc mã
nguồn Freqtrade thật, ghi trong `DR-D11-03` §2, không lặp lại ở đây).
"""

from __future__ import annotations

import base64
import json
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import pytest

from tool_d.api_client.freqtrade_control import (
    FreqtradeAuthError,
    FreqtradeControlError,
    dung_bot,
)


def _fake_response(payload: dict) -> MagicMock:
    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = json.dumps(payload).encode()
    return cm


class TestDungBotDuongSach:
    def test_goi_dung_url_phuong_thuc_va_auth_basic(self) -> None:
        with patch("tool_d.api_client.freqtrade_control.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = _fake_response({"status": "stopping trader ..."})
            ket_qua = dung_bot("http://127.0.0.1:8080", username="u", password="p")
        assert ket_qua == {"status": "stopping trader ..."}
        req = mock_urlopen.call_args[0][0]
        assert req.full_url == "http://127.0.0.1:8080/api/v1/stop"
        assert req.get_method() == "POST"
        tin = base64.b64encode(b"u:p").decode("ascii")
        assert req.headers.get("Authorization") == f"Basic {tin}"

    def test_bo_dau_gach_cheo_thua_o_base_url(self) -> None:
        with patch("tool_d.api_client.freqtrade_control.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = _fake_response({"status": "already stopped"})
            dung_bot("http://127.0.0.1:8080/", username="u", password="p")
        assert mock_urlopen.call_args[0][0].full_url == "http://127.0.0.1:8080/api/v1/stop"

    def test_goi_lap_lai_khi_da_stopped_khong_loi_dung_idempotent(self) -> None:
        """Freqtrade trả 'already stopped' khi gọi lặp — daemon KHÔNG cần
        tự khử trùng lặp, chỉ cần không coi đó là lỗi."""
        with patch("tool_d.api_client.freqtrade_control.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = _fake_response({"status": "already stopped"})
            ket_qua = dung_bot("http://127.0.0.1:8080", username="u", password="p")
        assert ket_qua["status"] == "already stopped"


class TestPhanLoaiLoiVaRetry:
    def test_401_khong_retry_raise_ngay(self) -> None:
        goi_gia = MagicMock(side_effect=HTTPError(url="x", code=401, msg="unauthorized", hdrs=None, fp=None))
        with patch("tool_d.api_client.freqtrade_control.urllib.request.urlopen", goi_gia):
            with pytest.raises(FreqtradeAuthError, match="CẤU HÌNH cục bộ"):
                dung_bot("http://127.0.0.1:8080", username="u", password="sai", so_lan_thu_lai=5)
        assert goi_gia.call_count == 1

    def test_loi_mang_retry_du_so_lan_roi_raise(self) -> None:
        goi_gia = MagicMock(side_effect=URLError("mất kết nối"))
        ngu_gia = MagicMock()
        with patch("tool_d.api_client.freqtrade_control.urllib.request.urlopen", goi_gia):
            with pytest.raises(FreqtradeControlError, match="KHÔNG dừng được bot"):
                dung_bot(
                    "http://127.0.0.1:8080",
                    username="u",
                    password="p",
                    so_lan_thu_lai=3,
                    ham_ngu=ngu_gia,
                )
        assert goi_gia.call_count == 3
        assert ngu_gia.call_count == 2  # nghỉ GIỮA các lần, không nghỉ sau lần cuối

    def test_thanh_cong_o_lan_thu_hai_khong_raise(self) -> None:
        goi_gia = MagicMock(
            side_effect=[URLError("tạm thời"), _fake_response({"status": "stopping trader ..."})]
        )
        with patch("tool_d.api_client.freqtrade_control.urllib.request.urlopen", goi_gia):
            ket_qua = dung_bot(
                "http://127.0.0.1:8080", username="u", password="p", so_lan_thu_lai=5, ham_ngu=MagicMock()
            )
        assert ket_qua["status"] == "stopping trader ..."
        assert goi_gia.call_count == 2

    def test_http_500_duoc_phan_loai_va_retry(self) -> None:
        goi_gia = MagicMock(
            side_effect=HTTPError(url="x", code=500, msg="server error", hdrs=None, fp=None)
        )
        with patch("tool_d.api_client.freqtrade_control.urllib.request.urlopen", goi_gia):
            with pytest.raises(FreqtradeControlError):
                dung_bot(
                    "http://127.0.0.1:8080", username="u", password="p", so_lan_thu_lai=2, ham_ngu=MagicMock()
                )
        assert goi_gia.call_count == 2

    def test_so_lan_thu_lai_duoi_1_raise_ngay(self) -> None:
        with pytest.raises(ValueError):
            dung_bot("http://127.0.0.1:8080", username="u", password="p", so_lan_thu_lai=0)
