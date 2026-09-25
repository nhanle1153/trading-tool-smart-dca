"""TD-0384 chặng 2 — tầng thuần lệnh CTRL D10 (`DR-D10-02` §5): tham số từ `tier_c.ctrl_d10`, giá ba tranche + SL,
cỡ tranche, lúc thoát, chọn rổ."""

from __future__ import annotations

import dataclasses
import math
from datetime import datetime, timedelta, timezone

import pytest

from tool_d.config.loader import load_tool_d_config
from tool_d.ops.ctrl_d10 import (
    LY_DO_THOAT_DU_3,
    LY_DO_THOAT_HET_GIO,
    CtrlD10Error,
    ThamSoCtrl,
    UngVienRo,
    chon_ro,
    doc_tham_so,
    ke_hoach_gia,
    ly_do_thoat,
    notional_moi_tranche,
)

UTC = timezone.utc
T0 = datetime(2026, 10, 1, 12, tzinfo=UTC)
TS = ThamSoCtrl(
    ro_so_cap=10, ro_tran_san_usdt=30.0, lech_t2_pct=0.3, lech_t3_pct=0.6, sl_pct=2.0,
    he_so_le_san=1.10, thoat_sau_du_3_phut=10.0, thoat_toi_da_gio=4.0,
)


class TestThamSoThat:
    def test_config_that_dung_so_da_chot_dr_d10_02_muc_5(self) -> None:
        """🔴 Ghim QUYẾT ĐỊNH (`DR-D10-02` §5, `b546b2b`): đổi một số ở YAML thì phải sửa dòng này — tức phải thấy DR."""
        assert doc_tham_so(load_tool_d_config()) == TS

    def test_thu_tu_gia_sai_chieu_bi_tu_choi(self) -> None:
        """SL nằm trên tranche chờ ⇒ tranche không bao giờ khớp trước khi SL nổ ⇒ D10 không sinh sự kiện đổi SL."""

        class Cfg:
            tier_c = {"ctrl_d10": {**dataclasses.asdict(TS), "sl_pct": 0.5}}

        with pytest.raises(CtrlD10Error, match="thứ tự"):
            doc_tham_so(Cfg())


class TestKeHoachGia:
    def test_ba_muc_va_sl_dung_cong_thuc(self) -> None:
        kh = ke_hoach_gia(100.0, TS)
        assert (kh.p1, kh.p2, kh.p3, kh.sl) == pytest.approx((100.0, 99.7, 99.4, 98.0))
        assert kh.p1 > kh.p2 > kh.p3 > kh.sl

    @pytest.mark.parametrize("p1", [0.0, -1.0, math.nan, math.inf])
    def test_p1_hong_thi_raise(self, p1) -> None:
        with pytest.raises(CtrlD10Error):
            ke_hoach_gia(p1, TS)


class TestNotional:
    def test_san_nhan_he_so_le(self) -> None:
        assert notional_moi_tranche(20.0, TS) == pytest.approx(22.0)

    @pytest.mark.parametrize("san", [0.0, -3.0, math.nan])
    def test_san_hong_thi_raise(self, san) -> None:
        with pytest.raises(CtrlD10Error):
            notional_moi_tranche(san, TS)


class TestLyDoThoat:
    def test_chua_du_va_chua_het_gio_thi_giu(self) -> None:
        assert ly_do_thoat(now=T0 + timedelta(hours=1), mo_luc=T0, so_tranche_da_khop=2, luc_khop_cuoi=T0, ts=TS) is None

    def test_du_3_nhung_chua_du_10_phut_thi_giu(self) -> None:
        cuoi = T0 + timedelta(minutes=30)
        assert ly_do_thoat(now=cuoi + timedelta(minutes=9), mo_luc=T0, so_tranche_da_khop=3, luc_khop_cuoi=cuoi, ts=TS) is None

    def test_du_3_va_du_10_phut_thi_thoat(self) -> None:
        cuoi = T0 + timedelta(minutes=30)
        kq = ly_do_thoat(now=cuoi + timedelta(minutes=10), mo_luc=T0, so_tranche_da_khop=3, luc_khop_cuoi=cuoi, ts=TS)
        assert kq == LY_DO_THOAT_DU_3

    def test_het_4_gio_thi_thoat_du_moi_tranche(self) -> None:
        kq = ly_do_thoat(now=T0 + timedelta(hours=4), mo_luc=T0, so_tranche_da_khop=1, luc_khop_cuoi=T0, ts=TS)
        assert kq == LY_DO_THOAT_HET_GIO

    def test_du_3_ma_thieu_moc_khop_cuoi_thi_raise(self) -> None:
        with pytest.raises(CtrlD10Error):
            ly_do_thoat(now=T0 + timedelta(hours=1), mo_luc=T0, so_tranche_da_khop=3, luc_khop_cuoi=None, ts=TS)


class TestChonRo:
    def test_loc_san_xep_thanh_khoan_lay_n_dau(self) -> None:
        ts = dataclasses.replace(TS, ro_so_cap=2)
        ung_vien = [
            UngVienRo("A/USDT:USDT", 5e8, 10.0),
            UngVienRo("B/USDT:USDT", 9e8, 31.0),  # sàn quá trần ⇒ loại dù thanh khoản cao nhất
            UngVienRo("C/USDT:USDT", 7e8, 30.0),  # đúng trần ⇒ giữ
            UngVienRo("D/USDT:USDT", 1e8, 5.0),
        ]
        assert chon_ro(ung_vien, ts) == ("C/USDT:USDT", "A/USDT:USDT")

    def test_thieu_du_lieu_bi_loai_khong_doan(self) -> None:
        ung_vien = [
            UngVienRo("A/USDT:USDT", None, 10.0),
            UngVienRo("B/USDT:USDT", 1e8, None),
            UngVienRo("C/USDT:USDT", math.nan, 10.0),
            UngVienRo("D/USDT:USDT", 1e6, 10.0),
        ]
        assert chon_ro(ung_vien, TS) == ("D/USDT:USDT",)

    def test_hoa_thanh_khoan_xep_theo_ten_tat_dinh(self) -> None:
        ung_vien = [UngVienRo("Z/USDT:USDT", 1e8, 10.0), UngVienRo("A/USDT:USDT", 1e8, 10.0)]
        assert chon_ro(ung_vien, TS) == ("A/USDT:USDT", "Z/USDT:USDT")

    def test_ro_rong_thi_tu_choi(self) -> None:
        with pytest.raises(CtrlD10Error, match="rỗng"):
            chon_ro([UngVienRo("A/USDT:USDT", 1e8, 99.0)], TS)
