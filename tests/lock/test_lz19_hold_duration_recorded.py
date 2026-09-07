"""L-Z19 (§4b.6, TD-0121) — `hold_duration_bars` ghi ở MỌI lệnh đã
đóng, mọi arm — kể cả lệnh đóng bằng TP/SL (để dựng phân bố hold,
§10.2), không chỉ lệnh đóng bởi DG8.

`hold_duration_bars()` không nhánh theo lý do đóng — cùng một công
thức áp dụng cho TP/SL/DG6/DG7/DG8, nên không có đường nào một loại
lệnh đóng bị bỏ sót khỏi việc ghi nhận.
"""

from __future__ import annotations

import pytest

from tool_d.time_stop import bars_since_tranche1, hold_duration_bars


class TestGhiChoMoiLyDoDong:
    @pytest.mark.parametrize(
        "close_bar,exit_tag",
        [
            (105, "TP1"),
            (110, "TP2"),
            (100, "STOP_LOSS"),
            (108, "DG6_A"),
            (112, "FUNDING_STOP"),
            (124, "TIME_STOP"),
        ],
    )
    def test_tinh_duoc_hold_duration_bat_ke_ly_do_dong(self, close_bar: int, exit_tag: str) -> None:
        # exit_tag không được hàm dùng tới — chỉ để thể hiện rằng phép
        # tính không phân biệt loại lệnh đóng.
        tranche1_bar = 100
        assert hold_duration_bars(tranche1_bar, close_bar) == close_bar - tranche1_bar

    def test_dong_ngay_tai_nen_tranche1_khop_thi_hold_bang_0(self) -> None:
        assert hold_duration_bars(100, 100) == 0

    def test_dung_cong_thuc_voi_bars_since_tranche1(self) -> None:
        assert hold_duration_bars(100, 130) == bars_since_tranche1(100, 130)

    def test_close_bar_truoc_tranche1_thi_raise(self) -> None:
        with pytest.raises(ValueError):
            hold_duration_bars(100, 99)
