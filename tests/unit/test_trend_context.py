"""TD-0119 — src/tool_d/trend_context.py: Context Trend Filter (Phần 2)."""

from __future__ import annotations

import math

import pytest

from tool_d.trend_context import (
    K_TUOI_TREND_TOI_THIEU,
    NGUONG_ADX,
    du_dieu_kien_vao_lenh,
    trend_dir_tai,
    tuoi_trend_nen,
    xac_nhan_da_khung,
)

NAN = float("nan")


class TestTrendDirTai:
    def test_fast_tren_slow_va_doc_duong_la_up(self) -> None:
        ema_fast = [0.0] * 11 + [110.0]
        ema_slow = [100.0] * 12
        ema_slow[1] = 95.0  # i=11, do_tre=10 -> so voi ema_slow[1]; doc = 100-95 = +5
        assert trend_dir_tai(ema_fast, ema_slow, 11) == "UP"

    def test_fast_duoi_slow_va_doc_am_la_down(self) -> None:
        ema_fast = [0.0] * 11 + [90.0]
        ema_slow = [100.0] * 12
        ema_slow[1] = 105.0  # doc = 100-105 = -5
        assert trend_dir_tai(ema_fast, ema_slow, 11) == "DOWN"

    def test_fast_tren_slow_nhung_doc_am_la_flat(self) -> None:
        # Mau thuan: fast>slow (co ve UP) nhung EMA cham (slow) dang di
        # xuong -> khong du dong thuan, phai la FLAT theo dung cong thuc.
        ema_fast = [0.0] * 11 + [110.0]
        ema_slow = [100.0] * 12
        ema_slow[1] = 105.0  # doc = 100-105 = -5
        assert trend_dir_tai(ema_fast, ema_slow, 11) == "FLAT"

    def test_chua_du_do_tre_thi_flat(self) -> None:
        ema_fast = [110.0] * 5
        ema_slow = [100.0] * 5
        assert trend_dir_tai(ema_fast, ema_slow, 5, do_tre=10) == "FLAT"

    def test_nan_thi_flat(self) -> None:
        ema_fast = [0.0] * 10 + [NAN, 110.0]
        ema_slow = [100.0] * 12
        assert trend_dir_tai(ema_fast, ema_slow, 11) == "FLAT"


class TestXacNhanDaKhung:
    def test_hai_khung_dong_thuan_thi_true(self) -> None:
        assert xac_nhan_da_khung("UP", "UP") is True

    def test_hai_khung_khac_nhau_thi_false(self) -> None:
        assert xac_nhan_da_khung("UP", "FLAT") is False
        assert xac_nhan_da_khung("UP", "DOWN") is False


class TestTuoiTrendNen:
    def test_tim_dung_diem_cross_gan_nhat(self) -> None:
        # cross tu DOWN sang UP tai index 5 (tu index 5 fast>slow)
        ema_fast = [90, 90, 90, 90, 90, 110, 110, 110]
        ema_slow = [100] * 8
        assert tuoi_trend_nen(ema_fast, ema_slow, 7) == 2  # 7-5=2

    def test_chua_tim_duoc_cross_trong_du_lieu_tra_ve_none(self) -> None:
        ema_fast = [110] * 5  # luon UP, khong co diem doi dau trong du lieu
        ema_slow = [100] * 5
        assert tuoi_trend_nen(ema_fast, ema_slow, 4) is None

    def test_nan_tai_i_tra_ve_none(self) -> None:
        ema_fast = [110, NAN]
        ema_slow = [100, 100]
        assert tuoi_trend_nen(ema_fast, ema_slow, 1) is None


class TestDuDieuKienVaoLenh:
    KWARGS_DAT = dict(
        huong_muc_tieu="UP", huong_1d="UP", huong_4h="UP",
        adx_1d=25.0, tuoi_nen=K_TUOI_TREND_TOI_THIEU,
    )

    def test_dat_ca_bon_dieu_kien_thi_true(self) -> None:
        assert du_dieu_kien_vao_lenh(**self.KWARGS_DAT) is True

    def test_huong_1d_khong_khop_muc_tieu_thi_false(self) -> None:
        kw = {**self.KWARGS_DAT, "huong_1d": "DOWN"}
        assert du_dieu_kien_vao_lenh(**kw) is False

    def test_khong_dong_thuan_da_khung_thi_false(self) -> None:
        kw = {**self.KWARGS_DAT, "huong_4h": "FLAT"}
        assert du_dieu_kien_vao_lenh(**kw) is False

    def test_adx_duoi_nguong_thi_false(self) -> None:
        kw = {**self.KWARGS_DAT, "adx_1d": NGUONG_ADX - 0.01}
        assert du_dieu_kien_vao_lenh(**kw) is False

    def test_chua_du_tuoi_trend_thi_false(self) -> None:
        kw = {**self.KWARGS_DAT, "tuoi_nen": K_TUOI_TREND_TOI_THIEU - 1}
        assert du_dieu_kien_vao_lenh(**kw) is False

    def test_tuoi_none_thi_false(self) -> None:
        kw = {**self.KWARGS_DAT, "tuoi_nen": None}
        assert du_dieu_kien_vao_lenh(**kw) is False
