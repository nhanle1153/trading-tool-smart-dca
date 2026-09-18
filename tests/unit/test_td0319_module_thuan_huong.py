"""TD-0319 (DR-SHORT-01) — tham số `huong` trong `trade_plan.py`,
`arm_switches.py`, `take_profit.py`. CHỈ DỰNG, `enable_short` vẫn tắt —
xem `docs/decisions/DR-SHORT-01-dung-duong-short-cong-tac-tat.md`.

Bất biến bắt buộc của cả file này (đọc kỹ trước khi sửa bất cứ gì ở đây):
mọi test Long CŨ ở `test_trade_plan.py` / `test_td0183_cong_tac_arm.py` /
`test_take_profit.py` phải xanh KHÔNG SỬA một khẳng định nào — bằng chứng
nằm ở việc ba file đó không xuất hiện trong diff của TD-0319. File này chỉ
CỘNG THÊM test cho nhánh `huong="short"` mới và cho phép GƯƠNG so hai
nhánh, không lặp lại các test Long đã có.

Hai kỹ thuật gương khác nhau, có chủ đích (xem docstring module gốc):
- `trade_plan`/`arm_switches`: gương price-level đúng với MỌI hằng số
  phản chiếu K (`x -> K - x`), vì p1/p2/p3/sl đều là hàm TUYẾN TÍNH của
  zone_low/zone_high/close.
- `take_profit`: gương chỉ sạch khi mirror qua chính `p_avg`
  (K = 2*p_avg) — `p_avg` là tham số ĐỘC LẬP ở đây, không suy ra từ zone.
"""

from __future__ import annotations

import pytest

from tool_d.arm_switches import ArmSwitchError, ke_hoach_theo_arm, sl_neo_atr
from tool_d.take_profit import (
    TP_SOURCE_NANG,
    TP_SOURCE_ZONE,
    TakeProfitError,
    ThamSoTP,
    chon_muc_tp1,
    tp1_tu_zone,
    tp2_muc_trail,
)
from tool_d.trade_plan import TradePlanError, sl_kieu_zone, tinh_ke_hoach

BUF_SL_THU = 0.4
KWARGS_MAC_DINH = dict(atr_4h=2.0, atr_1h_tai_tranche1=1.0, buf_sl_he_so=BUF_SL_THU)


# ═══════════════════════════ trade_plan.py ═══════════════════════════


class TestSlKieuZoneShort:
    def test_cong_thuc_neo_MEP_TREN_zone(self) -> None:
        # zone_high=110, atr_4h=5 -> buf = 0.4*5/110 -> sl = 110*(1+buf) = 110+2 = 112
        sl = sl_kieu_zone(
            zone_low=100, zone_high=110, atr_4h=5.0, buf_sl_he_so=0.4, huong="short"
        )
        assert sl == pytest.approx(112.0)

    def test_rut_gon_dai_so_sl_short_bang_zone_high_cong_he_so_atr(self) -> None:
        """sl = zone_high*(1+he_so*atr/zone_high) = zone_high + he_so*atr —
        cùng phép rút gọn đã ghi trong docstring module."""
        zone_high, atr_4h, he_so = 250.0, 3.0, 0.4
        sl = sl_kieu_zone(
            zone_low=200, zone_high=zone_high, atr_4h=atr_4h, buf_sl_he_so=he_so,
            huong="short",
        )
        assert sl == pytest.approx(zone_high + he_so * atr_4h)

    def test_thieu_zone_high_thi_raise(self) -> None:
        with pytest.raises(TradePlanError, match="zone_high"):
            sl_kieu_zone(zone_low=100, atr_4h=5.0, buf_sl_he_so=0.4, huong="short")

    def test_huong_la_thi_raise(self) -> None:
        with pytest.raises(TradePlanError, match="huong"):
            sl_kieu_zone(zone_low=100, atr_4h=5.0, buf_sl_he_so=0.4, huong="xuong")  # type: ignore[arg-type]


class TestTinhKeHoachShort:
    def test_gia_dong_cua_trong_zone_dat_p1_tai_gia_dong_cua(self) -> None:
        # zone [95,100], dong cua = 97 (trong zone) -> p1 = max(95,97) = 97
        kh = tinh_ke_hoach(
            zone_low=95, zone_high=100, gia_dong_cua=97, huong="short", **KWARGS_MAC_DINH
        )
        assert kh.p1 == 97

    def test_gia_rot_xuong_duoi_zone_dat_p1_tai_zone_low(self) -> None:
        kh = tinh_ke_hoach(
            zone_low=95, zone_high=100, gia_dong_cua=90, huong="short", **KWARGS_MAC_DINH
        )
        assert kh.p1 == 95

    def test_p2_p3_theo_dung_cong_thuc_short(self) -> None:
        # p3 SHORT = zone_high (khác LONG: p3 = zone_low)
        kh = tinh_ke_hoach(
            zone_low=90, zone_high=100, gia_dong_cua=90, huong="short", **KWARGS_MAC_DINH
        )
        assert kh.p2 == 95
        assert kh.p3 == 100

    def test_sl_TREN_zone_high_theo_buf(self) -> None:
        # zone_high=110, atr_4h=5 -> sl = 110 + 0.4*5 = 112
        kh = tinh_ke_hoach(
            zone_low=100, zone_high=110, gia_dong_cua=110, atr_4h=5.0,
            atr_1h_tai_tranche1=1.0, buf_sl_he_so=BUF_SL_THU, huong="short",
        )
        assert kh.sl == pytest.approx(112.0)

    def test_r_eff_plan_duong_va_hop_ly(self) -> None:
        kh = tinh_ke_hoach(
            zone_low=90, zone_high=100, gia_dong_cua=95, huong="short", **KWARGS_MAC_DINH
        )
        assert 0 < kh.r_eff_plan < 1

    def test_r_eff_plan_short_la_sl_tru_p_avg_chia_p_avg(self) -> None:
        """Gương của Long: LONG dùng `(p_avg-sl)/p_avg` (sl DƯỚI p_avg);
        SHORT dùng `(sl-p_avg)/p_avg` (sl TRÊN p_avg) — không phải cùng
        một công thức đổi dấu vô nghĩa, mà là hai chốt fail-closed khác
        hướng bảo đảm cùng một tính chất: kết quả dương."""
        kh = tinh_ke_hoach(
            zone_low=90, zone_high=100, gia_dong_cua=95, huong="short", **KWARGS_MAC_DINH
        )
        p_avg = (kh.p1 + kh.p2 + kh.p3) / 3
        assert kh.r_eff_plan == pytest.approx((kh.sl - p_avg) / p_avg)
        assert kh.sl > p_avg

    def test_huong_la_thi_raise(self) -> None:
        with pytest.raises(TradePlanError, match="huong"):
            tinh_ke_hoach(
                zone_low=90, zone_high=100, gia_dong_cua=95, huong="ngang",  # type: ignore[arg-type]
                **KWARGS_MAC_DINH,
            )


class TestGuongTradePlanLongShort:
    """🔴 Bất biến quan trọng nhất của TD-0319: lật giá `x -> K-x` (K bất
    kỳ) phải biến kế hoạch LONG thành đúng gương của kế hoạch SHORT trên
    zone đã lật — nếu một dấu `+`/`-` bị viết nhầm ở đâu đó, test này đỏ
    dù mọi test Long/Short "đứng riêng" ở trên vẫn có thể xanh (chúng
    không so sánh hai hướng với nhau)."""

    @pytest.mark.parametrize("k", [0.0, 500.0, -37.5])
    def test_lat_gia_bien_ke_hoach_long_thanh_guong_cua_short(self, k: float) -> None:
        zone_low, zone_high, close = 90.0, 100.0, 97.0
        atr_4h, atr_1h, buf = 3.0, 1.0, 0.4

        dai = tinh_ke_hoach(
            zone_low=zone_low, zone_high=zone_high, gia_dong_cua=close,
            atr_4h=atr_4h, atr_1h_tai_tranche1=atr_1h, buf_sl_he_so=buf,
            huong="long",
        )
        ngan = tinh_ke_hoach(
            zone_low=k - zone_high, zone_high=k - zone_low, gia_dong_cua=k - close,
            atr_4h=atr_4h, atr_1h_tai_tranche1=atr_1h, buf_sl_he_so=buf,
            huong="short",
        )
        assert ngan.p1 == pytest.approx(k - dai.p1)
        assert ngan.p2 == pytest.approx(k - dai.p2)
        assert ngan.p3 == pytest.approx(k - dai.p3)
        assert ngan.sl == pytest.approx(k - dai.sl)
        # r_eff_plan KHÔNG gương dưới K tuỳ ý (mẫu số p_avg đổi bất đối
        # xứng) — cố ý KHÔNG khẳng định ở đây, xem docstring module.


# ═══════════════════════════ arm_switches.py ═══════════════════════════


class TestSlNeoAtrShort:
    def test_cong_thuc_dung_2_2_lan_ATR_TREN_p1(self) -> None:
        assert sl_neo_atr(p1=100.0, atr_4h=2.0, huong="short") == pytest.approx(
            100.0 + 2.2 * 2.0
        )

    def test_DOI_HANH_VI_THAT_Z1_khac_Z0_short(self) -> None:
        zone = dict(zone_low=90.0, zone_high=100.0, gia_dong_cua=95.0,
                     atr_1h_tai_tranche1=1.0, buf_sl_he_so=0.4)
        z0 = ke_hoach_theo_arm(arm="Z0", atr_4h=2.0, huong="short", **zone)
        z1 = ke_hoach_theo_arm(arm="Z1", atr_4h=2.0, huong="short", **zone)
        assert z1.sl != z0.sl
        assert z1.r_eff_plan != z0.r_eff_plan
        assert (z1.p1, z1.p2, z1.p3, z1.zone_low, z1.zone_high) == (
            z0.p1, z0.p2, z0.p3, z0.zone_low, z0.zone_high
        )

    def test_sl_khong_tren_p_avg_thi_raise(self) -> None:
        """Gương của ca Long 'ATR quá lớn làm SL âm' — ở Short, ATR quá
        NHỎ làm SL không vượt được p_avg."""
        zone = dict(zone_low=10.0, zone_high=1000.0, gia_dong_cua=10.0,
                     atr_1h_tai_tranche1=1.0, buf_sl_he_so=0.4)
        with pytest.raises(ArmSwitchError, match="trên giá vào trung bình"):
            ke_hoach_theo_arm(arm="Z1", atr_4h=0.001, huong="short", **zone)

    def test_huong_la_thi_raise(self) -> None:
        with pytest.raises(ArmSwitchError, match="huong"):
            sl_neo_atr(p1=100.0, atr_4h=2.0, huong="cheo")  # type: ignore[arg-type]


class TestGuongArmSwitches:
    @pytest.mark.parametrize("k", [0.0, 300.0])
    def test_lat_gia_bien_sl_neo_atr_long_thanh_guong_short(self, k: float) -> None:
        p1, atr_4h = 100.0, 2.0
        dai = sl_neo_atr(p1=p1, atr_4h=atr_4h, huong="long")
        ngan = sl_neo_atr(p1=k - p1, atr_4h=atr_4h, huong="short")
        assert ngan == pytest.approx(k - dai)


# ═══════════════════════════ take_profit.py ═══════════════════════════


THAM_SO = ThamSoTP(
    tp1_haircut_pct=20.0, tp2_trail_atr=1.5, tp_fallback_dist_r=4.0,
    tp_fallback_target_r=1.5,
)


class TestTp1TuZoneShort:
    def test_tp1_tru_dan_tu_p_avg_xuong(self) -> None:
        # p_avg=100, zone=90 (duoi), haircut=20% -> tp1 = 100 - 0.8*10 = 92
        tp1 = tp1_tu_zone(
            p_avg=100.0, gia_zone_doi_dien=90.0, tp1_haircut_pct=20.0, huong="short"
        )
        assert tp1 == pytest.approx(92.0)

    def test_zone_tren_p_avg_thi_raise(self) -> None:
        with pytest.raises(TakeProfitError, match="NẰM DƯỚI"):
            tp1_tu_zone(
                p_avg=100.0, gia_zone_doi_dien=110.0, tp1_haircut_pct=20.0,
                huong="short",
            )

    def test_huong_la_thi_raise(self) -> None:
        with pytest.raises(TakeProfitError, match="huong"):
            tp1_tu_zone(
                p_avg=100.0, gia_zone_doi_dien=90.0, tp1_haircut_pct=20.0,
                huong="cheo",  # type: ignore[arg-type]
            )


class TestChonMucTp1Short:
    def test_chon_zone_gan_nhat_PHIA_DUOI(self) -> None:
        kq = chon_muc_tp1(
            p_avg=100.0, r_eff_plan=0.05,
            gia_cac_zone_doi_dien=[80.0, 96.0, 60.0],
            tham_so=THAM_SO, huong="short",
        )
        assert kq.tp_source == TP_SOURCE_ZONE
        assert kq.zone_gia_goc == 96.0

    def test_khong_co_zone_trong_tam_thi_dung_nang_TRU(self) -> None:
        kq = chon_muc_tp1(
            p_avg=100.0, r_eff_plan=0.01,  # khoang nho -> tran nho -> khong zone nao trong tam
            gia_cac_zone_doi_dien=[10.0],
            tham_so=THAM_SO, huong="short",
        )
        assert kq.tp_source == TP_SOURCE_NANG
        khoang = 100.0 * 0.01
        assert kq.tp1_gia == pytest.approx(100.0 - THAM_SO.tp_fallback_target_r * khoang)

    def test_huong_la_thi_raise(self) -> None:
        with pytest.raises(TakeProfitError, match="huong"):
            chon_muc_tp1(
                p_avg=100.0, r_eff_plan=0.05, gia_cac_zone_doi_dien=[90.0],
                tham_so=THAM_SO, huong="cheo",  # type: ignore[arg-type]
            )


class TestGuongTakeProfitQuaPAvg:
    """Gương ở đây SẠCH khi mirror qua chính `p_avg` (K = 2*p_avg), không
    phải K tuỳ ý — xem docstring module `take_profit`."""

    def test_tp1_tu_zone_guong_qua_p_avg(self) -> None:
        p_avg = 100.0
        zone_dai = 130.0  # tren p_avg
        zone_ngan = 2 * p_avg - zone_dai  # 70.0, duoi p_avg

        dai = tp1_tu_zone(
            p_avg=p_avg, gia_zone_doi_dien=zone_dai, tp1_haircut_pct=20.0, huong="long"
        )
        ngan = tp1_tu_zone(
            p_avg=p_avg, gia_zone_doi_dien=zone_ngan, tp1_haircut_pct=20.0, huong="short"
        )
        assert ngan == pytest.approx(2 * p_avg - dai)

    def test_chon_muc_tp1_guong_qua_p_avg_nhanh_zone(self) -> None:
        p_avg = 100.0
        zones_dai = [110.0, 96.0, 140.0]  # 96 < p_avg bi loai boi nhanh LONG
        zones_ngan = [2 * p_avg - z for z in zones_dai]

        dai = chon_muc_tp1(
            p_avg=p_avg, r_eff_plan=0.05, gia_cac_zone_doi_dien=zones_dai,
            tham_so=THAM_SO, huong="long",
        )
        ngan = chon_muc_tp1(
            p_avg=p_avg, r_eff_plan=0.05, gia_cac_zone_doi_dien=zones_ngan,
            tham_so=THAM_SO, huong="short",
        )
        assert dai.tp_source == TP_SOURCE_ZONE
        assert ngan.tp_source == TP_SOURCE_ZONE
        assert ngan.tp1_gia == pytest.approx(2 * p_avg - dai.tp1_gia)
        assert ngan.zone_gia_goc == pytest.approx(2 * p_avg - dai.zone_gia_goc)

    def test_chon_muc_tp1_guong_qua_p_avg_nhanh_nang(self) -> None:
        p_avg = 100.0
        dai = chon_muc_tp1(
            p_avg=p_avg, r_eff_plan=0.01, gia_cac_zone_doi_dien=[10.0],
            tham_so=THAM_SO, huong="long",
        )
        ngan = chon_muc_tp1(
            p_avg=p_avg, r_eff_plan=0.01, gia_cac_zone_doi_dien=[190.0],
            tham_so=THAM_SO, huong="short",
        )
        assert dai.tp_source == TP_SOURCE_NANG
        assert ngan.tp_source == TP_SOURCE_NANG
        assert ngan.tp1_gia == pytest.approx(2 * p_avg - dai.tp1_gia)


class TestTp2MucTrailShort:
    def test_trail_TREN_day_gia(self) -> None:
        muc = tp2_muc_trail(
            gia_thap_nhat_sau_tp1=100.0, atr_1h=2.0, tp2_trail_atr=1.5, huong="short"
        )
        assert muc == pytest.approx(100.0 + 1.5 * 2.0)

    def test_thieu_day_gia_thi_raise(self) -> None:
        with pytest.raises(TakeProfitError, match="gia_thap_nhat_sau_tp1"):
            tp2_muc_trail(atr_1h=2.0, tp2_trail_atr=1.5, huong="short")

    def test_huong_la_thi_raise(self) -> None:
        with pytest.raises(TakeProfitError, match="huong"):
            tp2_muc_trail(
                gia_thap_nhat_sau_tp1=100.0, atr_1h=2.0, tp2_trail_atr=1.5,
                huong="cheo",  # type: ignore[arg-type]
            )


class TestGuongTp2MucTrail:
    # K < dinh (120) sẽ làm `k - dinh` âm — `_so_duong` đúng đắn từ chối giá
    # không dương (N6), nên chỉ thử K giữ cả hai vế dương, đúng miền giá thật.
    @pytest.mark.parametrize("k", [200.0, 260.0])
    def test_lat_gia_bien_trail_long_thanh_guong_short(self, k: float) -> None:
        dinh, atr_1h, he_so = 120.0, 2.0, 1.5
        dai = tp2_muc_trail(
            gia_cao_nhat_sau_tp1=dinh, atr_1h=atr_1h, tp2_trail_atr=he_so, huong="long"
        )
        ngan = tp2_muc_trail(
            gia_thap_nhat_sau_tp1=k - dinh, atr_1h=atr_1h, tp2_trail_atr=he_so,
            huong="short",
        )
        assert ngan == pytest.approx(k - dai)
