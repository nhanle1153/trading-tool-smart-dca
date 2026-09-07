"""L-Z30 🔴 CRITICAL (§4c.4, TD-0122) — KHÔNG có lệnh đã đóng nào với
`funding_paid_cumulative > 0.35 × R_eff_plan` (biên 0.05 cho độ trễ
giữa hai mốc funding 8h).

DG7 áp dụng KHÔNG ĐIỀU KIỆN (§4c.2, cùng lý do với DG8/§4b.2) — chữ ký
hàm không có tham số lãi/TP1/trend nên không có "cửa" ngoại lệ.
"""

from __future__ import annotations

import inspect

from tool_d.funding_stop import is_funding_stop_triggered

THRESHOLD_FRAC = 0.3
MARGIN_FRAC = 0.05  # §4c.4 — độ trễ giữa hai mốc funding 8h


class TestKhongCoNgoaiLe:
    def test_chu_ky_khong_co_tham_so_ngoai_le(self) -> None:
        params = set(inspect.signature(is_funding_stop_triggered).parameters)
        for cam in ("profit", "current_profit", "trend_dir", "zss", "is_profitable", "tp1_hit"):
            assert cam not in params


class TestBienChinhXac:
    def test_dung_bang_nguong_thi_kich_hoat(self) -> None:
        r_eff = 100.0
        assert is_funding_stop_triggered(
            funding_paid_cumulative=THRESHOLD_FRAC * r_eff, r_eff_plan=r_eff, threshold_frac=THRESHOLD_FRAC
        ) is True

    def test_duoi_nguong_thi_chua_kich_hoat(self) -> None:
        r_eff = 100.0
        assert is_funding_stop_triggered(
            funding_paid_cumulative=THRESHOLD_FRAC * r_eff - 0.01,
            r_eff_plan=r_eff,
            threshold_frac=THRESHOLD_FRAC,
        ) is False

    def test_funding_rong_am_khong_bao_gio_kich_hoat(self) -> None:
        # Ròng lại NHẬN funding (âm) -> không bao giờ trigger, đúng thiết kế.
        assert is_funding_stop_triggered(
            funding_paid_cumulative=-5.0, r_eff_plan=100.0, threshold_frac=THRESHOLD_FRAC
        ) is False


class TestKhongVuotTranKhiKiemMoiMocFunding:
    """Mô phỏng kiểm tra tại MỖI mốc funding 8h (bước tăng nhỏ, tối đa
    bằng đúng biên 0.05×R_eff_plan mà spec cho phép) — giá trị tại lần
    kích hoạt đầu tiên không vượt 0.35×R_eff_plan."""

    def test_buoc_tang_trong_bien_thi_khong_vuot_0_35(self) -> None:
        r_eff = 100.0
        step = MARGIN_FRAC * r_eff  # bước funding lớn nhất còn trong biên cho phép
        cumulative = 0.0
        while not is_funding_stop_triggered(
            funding_paid_cumulative=cumulative, r_eff_plan=r_eff, threshold_frac=THRESHOLD_FRAC
        ):
            cumulative += step
        assert cumulative <= (THRESHOLD_FRAC + MARGIN_FRAC) * r_eff
