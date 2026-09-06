"""TD-0092 — H19 phần 2: độ phủ dữ liệu + CẤM suy nguyên nhân từ khoảng
trống (spec dòng 4350, LD-28).

Nhóm test quan trọng nhất là `TestCamSuyNguyenNhan` — nó khoá đúng bài học
đã làm Tool A mất nhiều ngày: quy một khoảng trống cho "sàn thiếu dữ liệu"
mà chưa hỏi lại sàn.
"""

from __future__ import annotations

import pandas as pd
import pytest

from tool_d.data.coverage import (
    GapCause,
    attribute_from_listing_date,
    attribute_from_source_probe,
    compute_coverage,
    expected_candles,
    render_table,
)

H = 60 * 60_000  # 1 giờ, ms
T0 = 1_700_000_000_000 - (1_700_000_000_000 % H)  # canh biên giờ


def _df(offsets_h: list[int]) -> pd.DataFrame:
    ts = [T0 + i * H for i in offsets_h]
    return pd.DataFrame(
        {
            "date": pd.to_datetime(ts, unit="ms", utc=True).astype("datetime64[ms, UTC]"),
            "open": [1.0] * len(ts),
            "high": [1.0] * len(ts),
            "low": [1.0] * len(ts),
            "close": [1.0] * len(ts),
            "volume": [1.0] * len(ts),
        }
    )


def _cov(offsets_h: list[int], *, n_hours: int):
    return compute_coverage(
        _df(offsets_h),
        name="AAA-1h-futures.feather",
        timeframe="1h",
        range_start_ms=T0,
        range_end_ms=T0 + (n_hours - 1) * H,
    )


class TestDemNenMongDoi:
    def test_dung_so_nen_1h(self) -> None:
        assert expected_candles(timeframe="1h", range_start_ms=T0, range_end_ms=T0 + 9 * H) == 10

    def test_khung_la_thi_raise_khong_doan(self) -> None:
        with pytest.raises(ValueError):
            expected_candles(timeframe="15m", range_start_ms=T0, range_end_ms=T0 + H)

    def test_khung_15m_khong_ton_tai_vi_spec_da_xoa(self) -> None:
        from tool_d.data.coverage import TIMEFRAME_MS

        assert "15m" not in TIMEFRAME_MS  # L-Z33


class TestDoPhu:
    def test_du_nen_thi_100_phan_tram(self) -> None:
        c = _cov(list(range(10)), n_hours=10)
        assert c.expected == 10 and c.actual == 10
        assert c.is_full and c.gaps == ()

    def test_thieu_giua_thi_ra_dung_khoang_trong(self) -> None:
        c = _cov([0, 1, 2, 6, 7, 8, 9], n_hours=10)
        assert c.actual == 7 and len(c.gaps) == 1
        assert c.gaps[0].n_missing == 3
        assert c.gaps[0].start_ms == T0 + 3 * H

    def test_hai_khoang_trong_roi_rac(self) -> None:
        c = _cov([0, 2, 4, 5, 6, 9], n_hours=10)
        assert [g.n_missing for g in c.gaps] == [1, 1, 2]

    def test_thieu_hal_duoi_thi_khong_duoc_tu_khen_100_phan_tram(self) -> None:
        # 🔴 Đếm theo khoảng YÊU CẦU, không theo min/max của chính file.
        # Đếm theo min/max sẽ ra 100% cho một file mất hẳn nửa cuối.
        c = _cov([0, 1, 2, 3, 4], n_hours=10)
        assert c.expected == 10 and c.actual == 5
        assert not c.is_full and c.ratio == 0.5

    def test_nen_ngoai_khoang_yeu_cau_khong_duoc_tinh(self) -> None:
        c = _cov([0, 1, 2, 50, 60], n_hours=5)
        assert c.actual == 3


class TestCamSuyNguyenNhan:
    """🔴 Bài học LD-28. `gap_cause` chỉ có thể rời khỏi `pending` qua một
    trong hai hàm quy trách nhiệm, và cả hai đòi dữ liệu nguồn thật."""

    def test_mac_dinh_luon_la_chua_kiem_nguon(self) -> None:
        c = _cov([0, 1, 5, 6], n_hours=8)
        assert not c.gap_cause.is_ok()
        assert "chưa kiểm nguồn" in c.gap_cause.render()

    def test_ban_ghi_khong_co_cho_nao_ghi_nguyen_nhan_doan(self) -> None:
        # Gap là frozen dataclass, không có trường nguyên nhân nào để điền.
        c = _cov([0, 5], n_hours=8)
        assert not hasattr(c.gaps[0], "cause")
        assert not hasattr(c.gaps[0], "reason")
        with pytest.raises(Exception):
            c.gaps[0].start_ms = 0  # frozen

    def test_bao_cao_khong_bao_gio_in_nguyen_nhan_chua_kiem(self) -> None:
        c = _cov([0, 5], n_hours=8)
        out = c.render()
        assert "chưa kiểm nguồn" in out
        for tu_cam in ("sàn thiếu", "do sàn", GapCause.SAN_KHONG_CO.value):
            assert tu_cam not in out

    def test_hoi_lai_san_co_du_lieu_thi_ket_luan_LOI_CUA_TA(self) -> None:
        c = _cov([0, 5], n_hours=8)
        c2 = attribute_from_source_probe(c, gap=c.gaps[0], candles_returned_by_source=4)
        assert c2.gap_cause.value is GapCause.LOI_CUA_TA
        assert "lỗi ở phía ta" in c2.gap_cause.render()

    def test_hoi_lai_san_khong_co_thi_moi_duoc_noi_san_thieu(self) -> None:
        c = _cov([0, 5], n_hours=8)
        c2 = attribute_from_source_probe(c, gap=c.gaps[0], candles_returned_by_source=0)
        assert c2.gap_cause.value is GapCause.SAN_KHONG_CO

    def test_so_nen_am_thi_raise(self) -> None:
        c = _cov([0, 5], n_hours=8)
        with pytest.raises(ValueError):
            attribute_from_source_probe(c, gap=c.gaps[0], candles_returned_by_source=-1)


class TestQuyTrachNhiemTheoNgayNiemYet:
    def test_trong_hoan_toan_truoc_ngay_niem_yet_thi_ket_luan_duoc(self) -> None:
        c = _cov([5, 6, 7], n_hours=8)  # trống 5 giờ đầu
        c2 = attribute_from_listing_date(c, onboard_date_ms=T0 + 5 * H)
        assert c2.gap_cause.value is GapCause.CHUA_NIEM_YET

    def test_con_trong_sau_ngay_niem_yet_thi_TU_CHOI_ket_luan(self) -> None:
        # Mã đã lên sàn rồi mà vẫn thiếu -> ngày niêm yết KHÔNG giải thích
        # được; phải hỏi lại nguồn. Giữ nguyên `pending`.
        c = _cov([0, 1, 5, 6], n_hours=8)  # trống ở giữa, sau khi đã niêm yết
        c2 = attribute_from_listing_date(c, onboard_date_ms=T0)
        assert not c2.gap_cause.is_ok()

    def test_khong_co_khoang_trong_thi_giu_nguyen(self) -> None:
        c = _cov(list(range(8)), n_hours=8)
        assert attribute_from_listing_date(c, onboard_date_ms=T0) is c


class TestBangBaoCao:
    def test_dong_tong_dem_dung_so_file_chua_kiem_nguon(self) -> None:
        rows = [_cov(list(range(8)), n_hours=8), _cov([0, 5], n_hours=8)]
        out = render_table(rows)
        assert "Tổng 2 file: 1 đủ, 1 thiếu" in out
        assert "1 file có khoảng trống CHƯA kiểm nguồn" in out

    def test_khong_gop_nguyen_nhan_thanh_mot_cau_tom_tat(self) -> None:
        # Gộp lại sẽ đẻ ra đúng câu "phần lớn do sàn thiếu" mà H19 cấm.
        rows = [_cov([0, 5], n_hours=8) for _ in range(3)]
        out = render_table(rows)
        assert "phần lớn" not in out and "chủ yếu" not in out

    def test_loc_chi_hien_file_thieu(self) -> None:
        rows = [_cov(list(range(8)), n_hours=8), _cov([0, 5], n_hours=8)]
        out = render_table(rows, only_incomplete=True)
        assert out.count("AAA-1h-futures.feather") == 1
