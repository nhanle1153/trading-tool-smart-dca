"""🔒 TD-0238 (MT-40) — Đỉnh equity bền vững qua restart, tầng THUẦN.

Cùng khuôn `test_risk_supervisor.py::TestBenVungTrangThaiQuaRestart` —
state machine + ghi/đọc nguyên tử, không chạm CALIB/WFO/LOCKBOX, nhưng
vẫn chạy trong Docker theo quy ước chung (N7).
"""

from __future__ import annotations

import math

import pytest

from tool_d.equity_peak import (
    DinhEquityBenVung,
    DinhEquityError,
    dinh_equity_moi,
    doc_dinh_equity,
    luu_dinh_equity,
)


class TestDinhEquityMoi:
    def test_lan_dau_chua_co_dinh_lay_tong_hien_tai_lam_dinh(self) -> None:
        d = dinh_equity_moi(None, tong_hien_tai=1000.0, stake_currency="USDT")
        assert d == DinhEquityBenVung(dinh=1000.0, stake_currency="USDT")

    def test_tong_cao_hon_dinh_thi_nang_dinh(self) -> None:
        cu = DinhEquityBenVung(dinh=1000.0, stake_currency="USDT")
        moi = dinh_equity_moi(cu, tong_hien_tai=1100.0, stake_currency="USDT")
        assert moi.dinh == 1100.0

    def test_tong_thap_hon_dinh_thi_GIU_NGUYEN_dinh_cu(self) -> None:
        """Chính sách đã chốt (14/09/2026): không bao giờ giảm, không
        bao giờ reset theo kỳ."""
        cu = DinhEquityBenVung(dinh=1100.0, stake_currency="USDT")
        moi = dinh_equity_moi(cu, tong_hien_tai=1000.0, stake_currency="USDT")
        assert moi.dinh == 1100.0

    def test_tong_bang_dinh_thi_giu_nguyen_instance(self) -> None:
        cu = DinhEquityBenVung(dinh=1000.0, stake_currency="USDT")
        moi = dinh_equity_moi(cu, tong_hien_tai=1000.0, stake_currency="USDT")
        assert moi is cu

    @pytest.mark.parametrize("gia_tri", [0.0, -1.0, math.nan])
    def test_tong_hien_tai_khong_huu_hieu_thi_raise(self, gia_tri: float) -> None:
        with pytest.raises(DinhEquityError):
            dinh_equity_moi(None, tong_hien_tai=gia_tri, stake_currency="USDT")

    def test_stake_currency_lech_thi_raise_khong_am_tham_tron_don_vi(self) -> None:
        cu = DinhEquityBenVung(dinh=1000.0, stake_currency="USDT")
        with pytest.raises(DinhEquityError, match="đơn vị"):
            dinh_equity_moi(cu, tong_hien_tai=1100.0, stake_currency="BUSD")


class TestBenVungHoaDinhEquityQuaGhiDoc:
    """`luu_dinh_equity()`/`doc_dinh_equity()` — bài học `MT-40`: một đỉnh
    an toàn chỉ sống trong RAM là một đỉnh không tồn tại sau khi tiến
    trình restart."""

    def test_chua_co_file_tra_ve_None(self, tmp_path) -> None:
        duong_dan = tmp_path / "khong_ton_tai" / "state.json"
        assert doc_dinh_equity(duong_dan) is None

    def test_ghi_roi_doc_lai_khop_nguyen_ban(self, tmp_path) -> None:
        duong_dan = tmp_path / "state.json"
        goc = DinhEquityBenVung(dinh=1234.5, stake_currency="USDT")
        luu_dinh_equity(goc, duong_dan)
        assert doc_dinh_equity(duong_dan) == goc

    def test_dinh_cao_hon_song_sot_qua_ghi_doc(self, tmp_path) -> None:
        duong_dan = tmp_path / "state.json"
        goc = DinhEquityBenVung(dinh=987_654.321, stake_currency="USDT")
        luu_dinh_equity(goc, duong_dan)
        doc_lai = doc_dinh_equity(duong_dan)
        assert doc_lai.dinh == pytest.approx(987_654.321)

    def test_ghi_nguyen_tu_khong_de_lai_file_tam(self, tmp_path) -> None:
        duong_dan = tmp_path / "state.json"
        luu_dinh_equity(DinhEquityBenVung(dinh=1.0, stake_currency="USDT"), duong_dan)
        assert duong_dan.exists()
        assert not (tmp_path / "state.json.dang-ghi").exists()

    def test_file_hong_RAISE_khong_am_tham_coi_la_sach(self, tmp_path) -> None:
        """🔴 Ca quan trọng nhất: file CÓ tồn tại mà đọc hỏng KHÔNG được
        coi là "chưa từng ghi" — nó có thể đang che một đỉnh thật đã ghi
        trước đó. Khác hẳn ca 'chưa có file' ở trên."""
        duong_dan = tmp_path / "state.json"
        duong_dan.write_text("khong phai json hop le", encoding="utf-8")
        with pytest.raises(DinhEquityError, match="KHÔNG đọc được"):
            doc_dinh_equity(duong_dan)

    def test_thieu_khoa_ben_trong_cung_raise(self, tmp_path) -> None:
        duong_dan = tmp_path / "state.json"
        duong_dan.write_text('{"dinh": 100.0}', encoding="utf-8")
        with pytest.raises(DinhEquityError):
            doc_dinh_equity(duong_dan)

    @pytest.mark.parametrize(
        "noi_dung_json",
        [
            '{"dinh": -1.0, "stake_currency": "USDT"}',
            '{"dinh": 0.0, "stake_currency": "USDT"}',
            '{"dinh": "NaN", "stake_currency": "USDT"}',
        ],
    )
    def test_dinh_am_hoac_0_hoac_NaN_RAISE(self, tmp_path, noi_dung_json: str) -> None:
        duong_dan = tmp_path / "state.json"
        duong_dan.write_text(noi_dung_json, encoding="utf-8")
        with pytest.raises(DinhEquityError):
            doc_dinh_equity(duong_dan)

    def test_stake_currency_rong_RAISE(self, tmp_path) -> None:
        duong_dan = tmp_path / "state.json"
        duong_dan.write_text('{"dinh": 100.0, "stake_currency": ""}', encoding="utf-8")
        with pytest.raises(DinhEquityError):
            doc_dinh_equity(duong_dan)
