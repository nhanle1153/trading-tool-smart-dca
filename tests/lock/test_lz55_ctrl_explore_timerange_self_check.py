"""L-Z55 — Mọi lần chạy dòng CTRL/EXPLORE có assert timerange-tập-dữ-liệu
PASS trong log; thiếu → coi là chạm tập đánh giá. Spec dòng 3973-3975,
DR-014 §2 (dòng 3492-3494): "bộ chạy PHẢI tự khẳng định timerange/tập
dữ liệu bằng assert, KHÔNG NHẬN khai báo của người chạy".
"""

from __future__ import annotations

from datetime import date

import pytest

from tool_d.ledger.timerange import (
    DatasetBoundary,
    TimerangeViolationError,
    assert_dataset_timerange,
)

CALIB = DatasetBoundary("CALIB", date(2024, 1, 1), date(2025, 6, 30))
EXPLORE = DatasetBoundary("EXPLORE", date(2025, 7, 1), date(2026, 3, 31))
CTRL = DatasetBoundary("CTRL", date(2025, 7, 1), date(2026, 3, 31))


class TestNamTronThiPass:
    def test_du_lieu_nam_tron_trong_ranh_gioi_thi_khong_raise(self) -> None:
        assert_dataset_timerange(
            dataset="CALIB",
            observed_start=date(2024, 2, 1),
            observed_end=date(2024, 12, 31),
            boundary=CALIB,
        )  # không raise = PASS

    def test_khop_dung_bien_thi_van_pass(self) -> None:
        assert_dataset_timerange(
            dataset="CALIB",
            observed_start=CALIB.start,
            observed_end=CALIB.end,
            boundary=CALIB,
        )


class TestKhaiSaiDatasetBiTuChoi:
    """Không nhận lời khai — nhãn tự xưng phải khớp đúng ranh giới đối chiếu."""

    def test_khai_explore_nhung_doi_chieu_voi_ranh_gioi_calib_thi_raise(self) -> None:
        with pytest.raises(TimerangeViolationError, match="không khớp"):
            assert_dataset_timerange(
                dataset="EXPLORE",
                observed_start=date(2024, 2, 1),
                observed_end=date(2024, 6, 1),
                boundary=CALIB,  # cố tình đối chiếu sai ranh giới
            )


class TestChamTapDanhGiaThiRaise:
    """Kịch bản "khai CTRL/EXPLORE để né đặt chỗ, rồi lặng lẽ đọc
    CALIB/WFO/LOCKBOX" — phải bị bắt."""

    def test_khai_explore_nhung_du_lieu_thuc_te_lan_sang_calib_thi_raise(self) -> None:
        with pytest.raises(TimerangeViolationError, match="CHẠM TẬP ĐÁNH GIÁ"):
            assert_dataset_timerange(
                dataset="EXPLORE",
                observed_start=date(2025, 6, 1),  # trước EXPLORE.start -> lấn sang CALIB
                observed_end=date(2025, 8, 1),
                boundary=EXPLORE,
            )

    def test_vuot_qua_bien_tren_cung_bi_bat(self) -> None:
        with pytest.raises(TimerangeViolationError):
            assert_dataset_timerange(
                dataset="CTRL",
                observed_start=date(2025, 8, 1),
                observed_end=date(2026, 6, 1),  # vượt CTRL.end
                boundary=CTRL,
            )

    def test_du_lieu_1_ngay_ngoai_bien_cung_bi_bat(self) -> None:
        # Ranh giới chặt — lệch dù chỉ 1 ngày vẫn phải bị từ chối, không
        # có "nới nhẹ cho tiện". CALIB.end = 2025-06-30, thử 2025-07-01.
        with pytest.raises(TimerangeViolationError):
            assert_dataset_timerange(
                dataset="CALIB",
                observed_start=CALIB.start,
                observed_end=date(2025, 7, 1),
                boundary=CALIB,
            )
