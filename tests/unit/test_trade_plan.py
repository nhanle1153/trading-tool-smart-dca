"""TD-0114 — src/tool_d/trade_plan.py: kế hoạch tranche (§3.1, §3.5)."""

from __future__ import annotations

import pytest

from tool_d.trade_plan import KeHoachTranche, tinh_ke_hoach

KWARGS_MAC_DINH = dict(atr_4h=2.0, atr_1h_tai_tranche1=1.0)


class TestTinhKeHoach:
    def test_gia_dong_cua_trong_zone_dat_p1_tai_gia_dong_cua(self) -> None:
        # zone [95,100], dong cua = 97 (trong zone) -> p1 = min(100,97) = 97
        kh = tinh_ke_hoach(zone_low=95, zone_high=100, gia_dong_cua=97, **KWARGS_MAC_DINH)
        assert kh.p1 == 97

    def test_gia_bat_len_tren_zone_dat_p1_tai_zone_high(self) -> None:
        kh = tinh_ke_hoach(zone_low=95, zone_high=100, gia_dong_cua=105, **KWARGS_MAC_DINH)
        assert kh.p1 == 100

    def test_p2_p3_theo_dung_cong_thuc(self) -> None:
        kh = tinh_ke_hoach(zone_low=90, zone_high=100, gia_dong_cua=100, **KWARGS_MAC_DINH)
        assert kh.p2 == 95
        assert kh.p3 == 90

    def test_sl_ngoai_zone_theo_buf(self) -> None:
        # zone_low=100, atr_4h=5 -> gia tai i la dong_cua=100 (dung lam mau so ti le ATR)
        # buf_sl = 0.4 * 5/100 = 0.02 -> sl = 100*(1-0.02) = 98
        kh = tinh_ke_hoach(zone_low=100, zone_high=110, gia_dong_cua=100, atr_4h=5.0, atr_1h_tai_tranche1=1.0)
        assert kh.sl == pytest.approx(98.0)

    def test_r_eff_plan_duong_va_hop_ly(self) -> None:
        kh = tinh_ke_hoach(zone_low=90, zone_high=100, gia_dong_cua=95, **KWARGS_MAC_DINH)
        assert 0 < kh.r_eff_plan < 1

    def test_luu_dung_atr_1h_tai_tranche1_de_dg6_a_dung_sau(self) -> None:
        kh = tinh_ke_hoach(zone_low=90, zone_high=100, gia_dong_cua=95, atr_4h=2.0, atr_1h_tai_tranche1=1.23)
        assert kh.atr_1h_tai_tranche1 == 1.23


class TestKeHoachSerialize:
    def test_roundtrip_dict(self) -> None:
        kh = tinh_ke_hoach(zone_low=90, zone_high=100, gia_dong_cua=95, **KWARGS_MAC_DINH)
        kh2 = KeHoachTranche.from_dict(kh.to_dict())
        assert kh2 == kh
