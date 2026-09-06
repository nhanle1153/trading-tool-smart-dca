"""TD-0094 — `dataset_boundaries_from_config()`: CALIB/WFO/LOCKBOX đọc
từ `tier_c.data_split` (T0-T3, DR-D0PRE-07), không hardcode ở nơi gọi.

Bối cảnh: TD-0093 phát hiện `freqtrade download-data --timerange` không
tôn trọng mốc kết thúc — dữ liệu LOCKBOX lọt vào thư mục làm việc dù
lệnh gọi khai đúng. File trên đĩa KHÔNG đáng tin về phạm vi ngày; cơ chế
bảo vệ thật (L-Z55, `assert_dataset_timerange`) đã có sẵn từ trước
nhưng chưa nối được với cấu hình thật — hàm này là chỗ nối đó.
"""

from __future__ import annotations

from datetime import date

import pytest

from tool_d.config.loader import load_tool_d_config
from tool_d.ledger.timerange import (
    TimerangeViolationError,
    assert_dataset_timerange,
    dataset_boundaries_from_config,
)


@pytest.fixture
def cfg():
    return load_tool_d_config()


class TestDocBienTuConfigThat:
    def test_ba_dataset_dung_moc_DR_D0PRE_07(self, cfg) -> None:
        b = dataset_boundaries_from_config(cfg)
        assert set(b) == {"CALIB", "WFO", "LOCKBOX"}
        assert b["CALIB"] == b["CALIB"].__class__("CALIB", date(2024, 4, 9), date(2025, 6, 12))
        assert b["WFO"].start == date(2025, 6, 12) and b["WFO"].end == date(2026, 1, 29)
        assert b["LOCKBOX"].start == date(2026, 1, 29) and b["LOCKBOX"].end == date(2026, 9, 6)

    def test_lien_tuc_khong_co_khoang_ho_giua_ba_doan(self, cfg) -> None:
        b = dataset_boundaries_from_config(cfg)
        assert b["CALIB"].end == b["WFO"].start
        assert b["WFO"].end == b["LOCKBOX"].start

    def test_noi_duoc_thang_voi_assert_dataset_timerange(self, cfg) -> None:
        b = dataset_boundaries_from_config(cfg)
        # Dữ liệu "quan sát được" nằm trọn trong CALIB -> không raise.
        assert_dataset_timerange(
            dataset="CALIB",
            observed_start=date(2024, 5, 1),
            observed_end=date(2025, 6, 1),
            boundary=b["CALIB"],
        )

    def test_du_lieu_lan_qua_lockbox_bi_bat(self, cfg) -> None:
        # Đúng kịch bản TD-0093: khai WFO nhưng dữ liệu thật (do bug
        # download-data) lấn qua hẳn ranh giới LOCKBOX.
        b = dataset_boundaries_from_config(cfg)
        with pytest.raises(TimerangeViolationError, match="CHẠM TẬP ĐÁNH GIÁ"):
            assert_dataset_timerange(
                dataset="WFO",
                observed_start=date(2025, 7, 1),
                observed_end=date(2026, 9, 5),  # TD-0093: file thật lấn tới đây
                boundary=b["WFO"],
            )
