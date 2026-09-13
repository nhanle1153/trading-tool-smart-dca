"""TD-0209 — Telegram Bot API single-egress (`src/tool_d/ops/telegram_client.py`).

Dùng mock cho `urllib.request.urlopen` (cùng khuôn `test_api_client_binance_
public.py`) — không phụ thuộc bot Telegram thật để chạy nhanh/ổn định.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

import pytest

from tool_d.risk_supervisor import KHONG_NHAN_DIEN, LOI_LOGIC, RETRY
from tool_d.ops.telegram_client import (
    ENV_TELEGRAM_BOT_TOKEN,
    ENV_TELEGRAM_CHAT_ID,
    TelegramCredentialsMissingError,
    TelegramError,
    doc_thong_tin_bot,
    gui_tin_nhan,
    phan_loai_loi_telegram,
)

_ENV_DAY_DU = {ENV_TELEGRAM_BOT_TOKEN: "123:abc", ENV_TELEGRAM_CHAT_ID: "999"}


def _http_error(ma_http: int) -> HTTPError:
    return HTTPError(url="https://api.telegram.org/x", code=ma_http, msg="mô phỏng", hdrs=None, fp=None)


def _fake_response(payload: dict) -> MagicMock:
    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = json.dumps(payload).encode()
    return cm


class TestDocThongTinBot:
    def test_du_ca_hai_bien_thi_qua(self) -> None:
        assert doc_thong_tin_bot(env=_ENV_DAY_DU) == ("123:abc", "999")

    def test_thieu_token_raise(self) -> None:
        with pytest.raises(TelegramCredentialsMissingError):
            doc_thong_tin_bot(env={ENV_TELEGRAM_CHAT_ID: "999"})

    def test_thieu_chat_id_raise(self) -> None:
        with pytest.raises(TelegramCredentialsMissingError):
            doc_thong_tin_bot(env={ENV_TELEGRAM_BOT_TOKEN: "123:abc"})

    def test_ca_hai_rong_raise(self) -> None:
        with pytest.raises(TelegramCredentialsMissingError):
            doc_thong_tin_bot(env={})


class TestPhanLoaiLoiTelegram:
    @pytest.mark.parametrize("http_status", [429, 500, 502, 599])
    def test_retry(self, http_status: int) -> None:
        assert phan_loai_loi_telegram(http_status=http_status) == RETRY

    @pytest.mark.parametrize("http_status", [400, 401])
    def test_loi_logic(self, http_status: int) -> None:
        assert phan_loai_loi_telegram(http_status=http_status) == LOI_LOGIC

    def test_ma_la_khong_nhan_dien(self) -> None:
        assert phan_loai_loi_telegram(http_status=404) == KHONG_NHAN_DIEN


class TestGuiTinNhan:
    def test_text_rong_raise(self) -> None:
        with pytest.raises(TelegramError):
            gui_tin_nhan("", env=_ENV_DAY_DU)

    def test_thieu_credential_raise_khong_phai_ket_qua_that_bai(self) -> None:
        with pytest.raises(TelegramCredentialsMissingError):
            gui_tin_nhan("xin chao", env={})

    def test_gui_thanh_cong(self) -> None:
        with patch("tool_d.ops.telegram_client.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = _fake_response({"ok": True, "result": {}})
            ket_qua = gui_tin_nhan("xin chao", env=_ENV_DAY_DU)

        assert ket_qua.thanh_cong
        assert ket_qua.loai_loi is None

    def test_dung_dung_url_va_body(self) -> None:
        with patch("tool_d.ops.telegram_client.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = _fake_response({"ok": True})
            gui_tin_nhan("xin chao", env=_ENV_DAY_DU)

        req = mock_urlopen.call_args[0][0]
        assert req.full_url == "https://api.telegram.org/bot123:abc/sendMessage"
        assert json.loads(req.data) == {"chat_id": "999", "text": "xin chao"}

    def test_telegram_tra_ok_false_la_loi_logic(self) -> None:
        with patch("tool_d.ops.telegram_client.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = _fake_response({"ok": False, "error_code": 400, "description": "sai"})
            ket_qua = gui_tin_nhan("xin chao", env=_ENV_DAY_DU)

        assert not ket_qua.thanh_cong
        assert ket_qua.loai_loi == LOI_LOGIC

    def test_http_429_la_retry(self) -> None:
        with patch("tool_d.ops.telegram_client.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = _http_error(429)
            ket_qua = gui_tin_nhan("xin chao", env=_ENV_DAY_DU)

        assert not ket_qua.thanh_cong
        assert ket_qua.loai_loi == RETRY

    def test_http_401_la_loi_logic(self) -> None:
        with patch("tool_d.ops.telegram_client.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = _http_error(401)
            ket_qua = gui_tin_nhan("xin chao", env=_ENV_DAY_DU)

        assert not ket_qua.thanh_cong
        assert ket_qua.loai_loi == LOI_LOGIC

    def test_timeout_la_retry_khong_raise(self) -> None:
        with patch("tool_d.ops.telegram_client.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = TimeoutError("mô phỏng timeout")
            ket_qua = gui_tin_nhan("xin chao", env=_ENV_DAY_DU)

        assert not ket_qua.thanh_cong
        assert ket_qua.loai_loi == RETRY

    def test_that_bai_khong_bao_gio_thieu_loai_loi(self) -> None:
        with patch("tool_d.ops.telegram_client.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = _http_error(418)  # mã KHÔNG có trong bảng Telegram
            ket_qua = gui_tin_nhan("xin chao", env=_ENV_DAY_DU)

        assert not ket_qua.thanh_cong
        assert ket_qua.loai_loi is not None
