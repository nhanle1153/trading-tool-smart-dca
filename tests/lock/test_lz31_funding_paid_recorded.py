"""L-Z31 (§4c.4, TD-0122) — `funding_paid_cumulative` ghi ở MỌI lệnh
đã đóng, mọi arm — kể cả lệnh đóng bằng TP/SL/DG6/DG8. Không có phân
bố đầy đủ thì không biết ngưỡng 0.3 có bao giờ ràng buộc không (cùng
lý do với L-Z19 cho `hold_duration_bars`).

`funding_paid_cumulative()` không nhánh theo lý do đóng — cùng một
công thức tính được cho MỌI lệnh, không phụ thuộc `exit_tag`.
"""

from __future__ import annotations

import pytest

from tool_d.funding_stop import funding_paid_cumulative


class TestGhiChoMoiLyDoDong:
    @pytest.mark.parametrize(
        "trade_funding_fees,exit_tag",
        [
            (-1.5, "TP1"),
            (-0.8, "TP2"),
            (0.0, "STOP_LOSS"),
            (-2.0, "DG6_A"),
            (-0.3, "TIME_STOP"),
            (2.5, "FUNDING_STOP"),  # ròng NHẬN funding nhưng vẫn đóng vì lý do khác
        ],
    )
    def test_tinh_duoc_bat_ke_ly_do_dong(self, trade_funding_fees: float, exit_tag: str) -> None:
        # exit_tag không được hàm dùng tới — thể hiện phép tính không
        # phân biệt loại lệnh đóng.
        assert funding_paid_cumulative(trade_funding_fees) == -trade_funding_fees

    def test_khong_tra_ve_none_hay_gia_tri_linh_canh(self) -> None:
        result = funding_paid_cumulative(0.0)
        assert result == 0.0 and result is not None
