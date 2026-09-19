"""TD-0123 — src/tool_d/dg6_early_invalidation.py: DG6 (§4.1)."""

from __future__ import annotations

import pytest

from tool_d.dg6_early_invalidation import (
    NGUONG_DECAY_C,
    SO_NEN_TOI_THIEU_B,
    dg6_dong_vi_the,
    dieu_kien_a,
    dieu_kien_b,
    dieu_kien_c,
    dieu_kien_d,
    price_decay_ratio,
    ty_le_hoi_ve_p1,
)


# Ngưỡng THỬ — `NGUONG_ATR_RATIO_A` đã bị xoá (TD-0195); giá trị thật đọc
# từ `tier_b.dg6a_atr_ratio` ở tầng chiến lược.
ATR_RATIO_THU = 1.8

# Ngưỡng THỬ — `NGUONG_FUNDING_D` đã bị xoá (TD-0320); giá trị thật đọc từ
# `tier_b.funding_rate_pct` (÷100) ở tầng chiến lược khi TD-0321 nối.
FUNDING_THU = -0.0005

# Ngưỡng THỬ — `NGUONG_HOI_GIA_D` đã bị xoá (TD-0323); giá trị thật đọc từ
# `tier_b.dg6d_retrace_frac` (tỉ lệ, KHÔNG chia 100) ở tầng chiến lược.
HOI_GIA_THU = 0.5


class TestDieuKienA:
    def test_atr_gian_va_gia_bat_loi_long_thi_true(self) -> None:
        assert dieu_kien_a(2.0, 95, p_avg=100, huong="long", nguong_atr_ratio=ATR_RATIO_THU) is True

    def test_atr_gian_nhung_gia_thuan_loi_thi_false(self) -> None:
        assert dieu_kien_a(2.0, 105, p_avg=100, huong="long", nguong_atr_ratio=ATR_RATIO_THU) is False

    def test_atr_chua_du_nguong_thi_false(self) -> None:
        assert dieu_kien_a(ATR_RATIO_THU - 0.01, 95, p_avg=100, huong="long",
                           nguong_atr_ratio=ATR_RATIO_THU) is False

    def test_short_dao_dau(self) -> None:
        assert dieu_kien_a(2.0, 105, p_avg=100, huong="short", nguong_atr_ratio=ATR_RATIO_THU) is True
        assert dieu_kien_a(2.0, 95, p_avg=100, huong="short", nguong_atr_ratio=ATR_RATIO_THU) is False


class TestDieuKienB:
    def test_du_8_nen_va_chua_hoi_qua_p1_long_thi_true(self) -> None:
        dong = [98, 97, 99, 98, 97, 96, 98, 99]  # khong nen nao >= p1=100
        assert dieu_kien_b(dong, p1=100, so_nen_da_troi=8, huong="long") is True

    def test_chua_du_8_nen_thi_false(self) -> None:
        dong = [98] * 7
        assert dieu_kien_b(dong, p1=100, so_nen_da_troi=7, huong="long") is False

    def test_da_hoi_qua_p1_long_thi_false(self) -> None:
        dong = [98, 97, 101, 98, 97, 96, 98, 99]  # index2 = 101 >= p1
        assert dieu_kien_b(dong, p1=100, so_nen_da_troi=8, huong="long") is False

    def test_short_dao_dau(self) -> None:
        dong = [102, 103, 101, 102, 103, 104, 102, 101]  # khong nen nao <= p1=100
        assert dieu_kien_b(dong, p1=100, so_nen_da_troi=8, huong="short") is True


class TestPriceDecayRatio:
    def test_long_giua_p_avg_va_sl(self) -> None:
        # p_avg=100, sl=90, gia=93 -> (100-93)/(100-90)=0.7
        assert price_decay_ratio(p_avg=100, gia_hien_tai=93, sl=90, huong="long") == pytest.approx(0.7)

    def test_short_dao_dau(self) -> None:
        # p_avg=100, sl=110, gia=107 -> (107-100)/(110-100)=0.7
        assert price_decay_ratio(p_avg=100, gia_hien_tai=107, sl=110, huong="short") == pytest.approx(0.7)

    def test_sl_bang_p_avg_thi_raise(self) -> None:
        with pytest.raises(ValueError):
            price_decay_ratio(p_avg=100, gia_hien_tai=95, sl=100, huong="long")


class TestDieuKienC:
    def test_du_nguong_va_trend_dao_thi_true(self) -> None:
        assert dieu_kien_c(NGUONG_DECAY_C, True) is True

    def test_chua_du_nguong_thi_false(self) -> None:
        assert dieu_kien_c(NGUONG_DECAY_C - 0.01, True) is False

    def test_du_nguong_nhung_trend_chua_dao_thi_false(self) -> None:
        assert dieu_kien_c(0.9, False) is False


class TestTyLeHoiVeP1:
    def test_hoi_mot_nua_quang_duong(self) -> None:
        # gia_vao=90, p1=100 -> quang duong=10; gia_hien_tai=95 -> da di 5 -> 0.5
        assert ty_le_hoi_ve_p1(gia_vao=90, gia_hien_tai=95, p1=100) == pytest.approx(0.5)

    def test_di_nguoc_huong_p1_thi_khong_am(self) -> None:
        assert ty_le_hoi_ve_p1(gia_vao=90, gia_hien_tai=85, p1=100) == 0.0


class TestDieuKienD:
    def test_short_funding_am_va_hoi_qua_50pt_thi_true(self) -> None:
        assert dieu_kien_d(
            -0.001, 0.6, huong="short", nguong_funding=FUNDING_THU, nguong_hoi_gia=HOI_GIA_THU
        ) is True

    def test_long_luon_false(self) -> None:
        assert dieu_kien_d(
            -0.001, 0.6, huong="long", nguong_funding=FUNDING_THU, nguong_hoi_gia=HOI_GIA_THU
        ) is False

    def test_funding_chua_du_am_thi_false(self) -> None:
        assert dieu_kien_d(
            FUNDING_THU + 0.0001, 0.6, huong="short",
            nguong_funding=FUNDING_THU, nguong_hoi_gia=HOI_GIA_THU,
        ) is False

    def test_hoi_gia_chua_du_thi_false(self) -> None:
        assert dieu_kien_d(
            -0.001, HOI_GIA_THU - 0.01, huong="short",
            nguong_funding=FUNDING_THU, nguong_hoi_gia=HOI_GIA_THU,
        ) is False

    def test_nguong_hoi_gia_di_qua_doi_so(self) -> None:
        """TD-0323: ngưỡng hồi giá là ĐỐI SỐ, không còn hằng cứng — đổi đối số
        đổi kết quả tại cùng một tỉ lệ hồi 0.6."""
        chung = dict(huong="short", nguong_funding=FUNDING_THU)
        assert dieu_kien_d(-0.001, 0.6, nguong_hoi_gia=0.5, **chung) is True
        assert dieu_kien_d(-0.001, 0.6, nguong_hoi_gia=0.7, **chung) is False

    def test_nguong_funding_khong_co_mac_dinh(self) -> None:
        """Cùng khuôn `nguong_zss`/`nguong_atr_ratio` (TD-0195): mặc định
        là chỗ để một đường gọi quên khai mà vẫn lặng lẽ chạy."""
        import inspect

        chu_ky = inspect.signature(dieu_kien_d)
        assert chu_ky.parameters["nguong_funding"].default is inspect.Parameter.empty
        assert chu_ky.parameters["nguong_hoi_gia"].default is inspect.Parameter.empty


class TestDg6DongViThe:
    def test_khong_dieu_kien_nao_dung_thi_false(self) -> None:
        assert dg6_dong_vi_the(a=False, b=False, c=False, d=False) is False

    def test_bat_ky_dieu_kien_nao_dung_thi_true(self) -> None:
        assert dg6_dong_vi_the(a=True, b=False, c=False, d=False) is True
        assert dg6_dong_vi_the(a=False, b=True, c=False, d=False) is True
        assert dg6_dong_vi_the(a=False, b=False, c=True, d=False) is True
        assert dg6_dong_vi_the(a=False, b=False, c=False, d=True) is True
