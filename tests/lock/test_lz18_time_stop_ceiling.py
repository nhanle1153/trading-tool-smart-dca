"""L-Z18 🔴 CRITICAL (§4b.6, TD-0121) — KHÔNG có bản ghi lệnh nào với
`hold_duration_bars > max_hold_bars`.

DG8 áp dụng KHÔNG ĐIỀU KIỆN (§4b.2) — test này khoá đúng điều đó: hàm
quyết định time-stop không nhận bất kỳ tham số nào về lãi/lỗ/trend/ZSS,
nên không có "cửa" nào để một ngoại lệ lọt qua và kéo dài `hold` vượt
`max_hold_bars`.
"""

from __future__ import annotations

import inspect

import pytest

from tool_d.time_stop import bars_since_tranche1, is_time_stop_triggered


class TestKhongCoNgoaiLe:
    """Chữ ký hàm CỐ Ý không có tham số lãi/trend/ZSS — không có gì để
    dùng làm ngoại lệ dù muốn."""

    def test_chu_ky_khong_co_tham_so_ngoai_le(self) -> None:
        params = set(inspect.signature(is_time_stop_triggered).parameters)
        for cam in ("profit", "current_profit", "trend_dir", "zss", "is_profitable", "tp1_hit"):
            assert cam not in params


class TestBienTrenChinhXac:
    def test_dung_bang_max_hold_bars_thi_kich_hoat(self) -> None:
        assert is_time_stop_triggered(tranche1_bar=100, current_bar=124, max_hold_bars=24) is True

    def test_it_hon_mot_nen_thi_chua_kich_hoat(self) -> None:
        assert is_time_stop_triggered(tranche1_bar=100, current_bar=123, max_hold_bars=24) is False

    def test_vuot_qua_van_kich_hoat_khong_tu_het_han(self) -> None:
        # Nếu vì lý do gì đó bị kiểm trễ (bỏ lỡ một nến), DG8 vẫn phải
        # kích hoạt — không có khái niệm "quá hạn nên thôi khỏi đóng".
        assert is_time_stop_triggered(tranche1_bar=100, current_bar=130, max_hold_bars=24) is True

    def test_ngay_tai_tranche1_chua_kich_hoat_neu_max_duong(self) -> None:
        assert is_time_stop_triggered(tranche1_bar=100, current_bar=100, max_hold_bars=24) is False


class TestKhongDeHoldVuotTran:
    """Mô phỏng một vòng lặp kiểm tra mỗi nến — hold thực tế (nến kích
    hoạt lần đầu) không bao giờ vượt `max_hold_bars`."""

    @pytest.mark.parametrize("max_hold_bars", [1, 5, 24, 40])
    def test_nen_kich_hoat_dau_tien_dung_bang_max_hold_bars(self, max_hold_bars: int) -> None:
        tranche1_bar = 0
        first_trigger_bar = next(
            b
            for b in range(0, max_hold_bars + 5)
            if is_time_stop_triggered(tranche1_bar=tranche1_bar, current_bar=b, max_hold_bars=max_hold_bars)
        )
        actual_hold = bars_since_tranche1(tranche1_bar, first_trigger_bar)
        assert actual_hold == max_hold_bars  # đúng bằng, không sớm hơn không muộn hơn

    def test_current_bar_truoc_tranche1_thi_raise(self) -> None:
        with pytest.raises(ValueError):
            is_time_stop_triggered(tranche1_bar=100, current_bar=50, max_hold_bars=24)
