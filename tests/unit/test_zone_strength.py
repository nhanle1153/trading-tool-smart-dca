"""TD-0104 — src/tool_d/zone_strength.py: ZSS (§1.2) + ngưỡng nhận zone (§1.3)."""

from __future__ import annotations

import pytest

from tool_d.zone_strength import (
    NGUONG_TUOI_ZONE_TOI_DA,
    NGUONG_ZSS,
    TRONG_SO_ZSS,
    compression,
    touch_count,
    volume_ratio,
    zone_hop_le,
    zss,
)

ZONE_LOW, ZONE_HIGH = 100.0, 102.0  # buf giả định, không quan trọng cho test này


class TestTouchCountDay:
    """Zone đáy — CHẠM dùng `low`, BẬT RA khi `close` > zone_high."""

    def test_khong_cham_lan_nao_thi_bang_0(self) -> None:
        thap = [110, 108, 106, 104]  # không nến nào chạm [100,102]
        dong = thap
        assert touch_count(thap, dong, ZONE_LOW, ZONE_HIGH, i_swing=0, t=3, loai="day") == 0

    def test_cham_roi_bat_ra_ngay_cung_nen_dem_1(self) -> None:
        # index1: low=101 (chạm), close=103 (bật ra cùng nến)
        thap = [100, 101, 105]
        dong = [100, 103, 105]
        assert touch_count(thap, dong, ZONE_LOW, ZONE_HIGH, i_swing=0, t=2, loai="day") == 1

    def test_cham_nen_ke_tiep_moi_bat_ra_van_dem_1_cum(self) -> None:
        # index1: low=101 (chạm), close=101 (còn kẹt trong zone)
        # index2: close=103 (nến kế tiếp bật ra) -> đóng cụm, đếm 1
        thap = [100, 101, 105, 105]
        dong = [100, 101, 103, 105]
        assert touch_count(thap, dong, ZONE_LOW, ZONE_HIGH, i_swing=0, t=3, loai="day") == 1

    def test_cum_cham_nhieu_nen_lien_tiep_van_chi_dem_1(self) -> None:
        # index1,2,3 đều chạm+đóng trong zone, index4 mới bật ra -> 1 touch
        thap = [100, 101, 100.5, 101, 105]
        dong = [100, 101, 100.7, 101, 103]
        assert touch_count(thap, dong, ZONE_LOW, ZONE_HIGH, i_swing=0, t=4, loai="day") == 1

    def test_dong_duoi_zone_low_khong_phai_touch(self) -> None:
        # index1: low=101 (chạm) nhưng close=99 (< zone_low) -> KHÔNG phải touch
        thap = [100, 101, 105]
        dong = [100, 99, 105]
        assert touch_count(thap, dong, ZONE_LOW, ZONE_HIGH, i_swing=0, t=2, loai="day") == 0

    def test_hai_cum_cham_rieng_biet_dem_2(self) -> None:
        thap = [100, 101, 105, 101, 105]
        dong = [100, 103, 105, 103, 105]  # index1 và index3 đều bật ra cùng nến
        assert touch_count(thap, dong, ZONE_LOW, ZONE_HIGH, i_swing=0, t=4, loai="day") == 2

    def test_khong_tinh_lan_dau_hinh_thanh_tai_i_swing(self) -> None:
        # i_swing chính là nến hình thành zone (low = zone_low đúng biên) —
        # KHÔNG được tính là touch dù về mặt số học nó "chạm".
        thap = [100, 105, 105]
        dong = [100, 105, 105]
        assert touch_count(thap, dong, ZONE_LOW, ZONE_HIGH, i_swing=0, t=2, loai="day") == 0

    def test_point_in_time_khong_dem_touch_sau_t(self) -> None:
        thap = [100, 101, 105, 101, 105]
        dong = [100, 103, 105, 103, 105]
        # tại t=2 mới chỉ có 1 touch xảy ra (index1); touch thứ 2 (index3) ở tương lai
        assert touch_count(thap, dong, ZONE_LOW, ZONE_HIGH, i_swing=0, t=2, loai="day") == 1

    def test_vo_giua_cum_roi_bat_ra_sau_khong_duoc_tinh_la_touch(self) -> None:
        # TD-0107 (bug thật, phát hiện qua review độc lập): index1 chạm và
        # mở cụm; index2 giá VỠ SÂU dưới zone_low NGAY GIỮA lúc đang chờ
        # bật ra; index3 mới bật ra thật. Bản lỗi cũ chỉ kiểm `bat_ra` khi
        # `dang_trong_cum=True`, bỏ sót cú vỡ giữa chừng -> đếm nhầm thành
        # 1. Đúng theo spec (close < zone_low -> KHÔNG phải touch, "zone bị
        # phá"), cụm đã vỡ này không được tính.
        thap = [100, 101, 90, 103]
        dong = [100, 101, 90, 103]
        assert touch_count(thap, dong, ZONE_LOW, ZONE_HIGH, i_swing=0, t=3, loai="day") == 0


class TestTouchCountDinh:
    """Zone đỉnh — đảo dấu: CHẠM dùng `high`, BẬT RA khi `close` < zone_low."""

    def test_cham_roi_bat_ra_cung_nen(self) -> None:
        cao = [100, 101, 90]
        dong = [100, 99, 90]  # index1: high=101 chạm, close=99 (< zone_low) -> bật ra
        assert touch_count(cao, dong, ZONE_LOW, ZONE_HIGH, i_swing=0, t=2, loai="dinh") == 1

    def test_dong_tren_zone_high_khong_phai_touch(self) -> None:
        cao = [100, 101, 90]
        dong = [100, 103, 90]  # close vượt zone_high -> không phải touch (vỡ lên)
        assert touch_count(cao, dong, ZONE_LOW, ZONE_HIGH, i_swing=0, t=2, loai="dinh") == 0


class TestVolumeRatio:
    def test_du_20_nen_tinh_dung_trung_binh(self) -> None:
        volume = [10.0] * 19 + [30.0]  # MA20 = (19*10 + 30)/20 = 11.0
        assert volume_ratio(volume, i_swing=19) == pytest.approx(30.0 / 11.0)

    def test_chua_du_20_nen_tra_ve_none(self) -> None:
        volume = [10.0] * 10
        assert volume_ratio(volume, i_swing=9) is None


class TestCompression:
    def test_atr_giai_ra_ngay_lon_hon_luc_hinh_thanh_thi_ti_le_lon_hon_1(self) -> None:
        n = 60
        dong = [100 + i * 0.1 for i in range(n)]
        thap = [c - 0.5 for c in dong]
        cao_hep = [c + 0.5 for c in dong]  # biên độ nhỏ ở giai đoạn đầu
        cao = list(cao_hep)
        # từ nến 40 trở đi biên độ giãn mạnh -> ATR tăng
        for i in range(40, n):
            cao[i] = dong[i] + 5.0
            thap[i] = dong[i] - 5.0
        ti_le = compression(cao, thap, dong, i_hinh_thanh=20, i_hien_tai=59)
        assert ti_le is not None
        assert ti_le > 1.0

    def test_chua_du_du_lieu_cho_atr_tra_ve_none(self) -> None:
        n = 5
        dong = [100.0] * n
        assert compression(dong, dong, dong, i_hinh_thanh=0, i_hien_tai=4) is None


class TestZss:
    def test_trong_so_dong_bang_bang_1_phan_3(self) -> None:
        assert TRONG_SO_ZSS == pytest.approx(1 / 3)

    def test_cong_thuc_dung_theo_spec(self) -> None:
        # touch=2 -> min(2,3)/3 = 2/3 ; volume_ratio=1.5 -> clip(1.5,0,2)/2 = 0.75
        # compression=0.5 -> clip(2-0.5,0,2)/2 = clip(1.5,0,2)/2 = 0.75
        gia_tri = zss(touch=2, ty_le_volume=1.5, do_nen=0.5)
        ky_vong = (1 / 3) * (2 / 3) + (1 / 3) * 0.75 + (1 / 3) * 0.75
        assert gia_tri == pytest.approx(ky_vong)

    def test_touch_vuot_tran_3_bi_kep(self) -> None:
        a = zss(touch=3, ty_le_volume=0.0, do_nen=2.0)
        b = zss(touch=10, ty_le_volume=0.0, do_nen=2.0)
        assert a == pytest.approx(b)

    def test_volume_ratio_am_bi_kep_ve_0(self) -> None:
        a = zss(touch=0, ty_le_volume=-5.0, do_nen=2.0)
        b = zss(touch=0, ty_le_volume=0.0, do_nen=2.0)
        assert a == pytest.approx(b)


class TestZoneHopLe:
    def test_dat_ca_ba_dieu_kien_thi_hop_le(self) -> None:
        assert zone_hop_le(zss_value=NGUONG_ZSS, so_touch=1, tuoi_nen=NGUONG_TUOI_ZONE_TOI_DA) is True

    def test_zss_duoi_nguong_thi_khong_hop_le(self) -> None:
        assert zone_hop_le(zss_value=NGUONG_ZSS - 0.01, so_touch=5, tuoi_nen=1) is False

    def test_chua_co_touch_nao_thi_khong_hop_le(self) -> None:
        assert zone_hop_le(zss_value=1.0, so_touch=0, tuoi_nen=1) is False

    def test_qua_tuoi_toi_da_thi_khong_hop_le(self) -> None:
        assert zone_hop_le(zss_value=1.0, so_touch=5, tuoi_nen=NGUONG_TUOI_ZONE_TOI_DA + 1) is False
