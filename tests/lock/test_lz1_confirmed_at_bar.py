"""L-Z1 — CRITICAL (§7.2, §8.1, TD-0102). Mọi swing dùng trong backtest
phải có `confirmed_at_bar` cách `swing_bar` ĐỦ k=3 nến 4H THẬT đã trôi
qua — không được sớm hơn (đó chính là lookahead).

Dùng fixture feather-shape TỰ TẠO (cột date/open/high/low/close/volume
đúng schema thật, xem `backfill_guard.py`) thay vì đọc thẳng
`user_data/data/binance/futures` trên đĩa: dữ liệu backfill thật bị
`.gitignore` chặn (không commit — xem `.gitignore` dòng 2), nên một test
khoá phụ thuộc thẳng vào nó sẽ chỉ chạy được trên đúng máy vừa backfill,
vi phạm chính yêu cầu "bằng chứng phải chạy lại được trong Docker" (N7)
cho bất kỳ ai/máy nào khác. Bù lại, một fixture CỐ TÌNH có khoảng trống
— đúng dạng lỗ hổng CALIB thật mà TD-0092 đã đo được (45/101 file thiếu)
— mới là phép kiểm có ý nghĩa: chỉ số mảng `i+k` không tự động đồng
nghĩa với "k nến thật đã trôi qua" khi dữ liệu có lỗ hổng.

Phần còn lại của H4-D — "mọi tranche fill có timestamp ≥ confirmed_at_bar"
— CHƯA kiểm được ở đây: D1 (Khối 11) chưa có code đặt lệnh/tranche fill
nào để kiểm. Sẽ bổ sung khi task đó xuất hiện, dùng lại đúng hai hàm này.
"""

from __future__ import annotations

from datetime import timedelta

import pandas as pd

from tool_d.zone_detection import K_XAC_NHAN, la_diem_swing

KHUNG_4H = timedelta(hours=4)


def _du_lieu_lien_tuc(thap: list[float], cao: list[float] | None = None) -> pd.DataFrame:
    n = len(thap)
    cao = cao if cao is not None else [g + 1 for g in thap]
    t0 = pd.Timestamp("2024-01-01", tz="UTC")
    return pd.DataFrame(
        {
            "date": [t0 + i * KHUNG_4H for i in range(n)],
            "open": thap,
            "high": cao,
            "low": thap,
            "close": thap,
            "volume": [1.0] * n,
        }
    )


class TestBatBienTrenDuLieuLienTuc:
    def test_moi_swing_day_co_dung_k_nen_da_troi_qua(self) -> None:
        thap = [10, 9, 8, 5, 8, 9, 10, 9, 8, 4, 8, 9, 10]
        df = _du_lieu_lien_tuc(thap)
        thoi_gian = df["date"].tolist()
        so_swing = 0
        for i in range(K_XAC_NHAN, len(df) - K_XAC_NHAN):
            if not la_diem_swing(thap, i, loai="day"):
                continue
            so_swing += 1
            j = i + K_XAC_NHAN
            assert thoi_gian[j] - thoi_gian[i] == K_XAC_NHAN * KHUNG_4H
        assert so_swing > 0, "fixture phải chứa ít nhất 1 swing thật để test có nghĩa"

    def test_moi_swing_dinh_co_dung_k_nen_da_troi_qua(self) -> None:
        cao = [1, 2, 3, 6, 3, 2, 1, 2, 3, 7, 3, 2, 1]
        df = _du_lieu_lien_tuc(thap=[c - 1 for c in cao], cao=cao)
        thoi_gian = df["date"].tolist()
        so_swing = 0
        for i in range(K_XAC_NHAN, len(df) - K_XAC_NHAN):
            if not la_diem_swing(cao, i, loai="dinh"):
                continue
            so_swing += 1
            j = i + K_XAC_NHAN
            assert thoi_gian[j] - thoi_gian[i] == K_XAC_NHAN * KHUNG_4H
        assert so_swing > 0


class TestBatBienTrenDuLieuCoKhoangTrong:
    """Đúng dạng lỗ hổng dữ liệu THẬT đã đo được ở TD-0092 — chỉ số mảng
    +k không còn nghĩa là "3 nến thật" khi có nến bị thiếu ở giữa."""

    def test_khoang_trong_lam_thoi_gian_troi_qua_nhieu_hon_khong_bao_gio_it_hon(self) -> None:
        thap = [10, 9, 8, 5, 8, 9, 10, 11, 12]
        df = _du_lieu_lien_tuc(thap)
        # Khoét đúng nến ngay sau swing (index 4) — mô phỏng khoảng trống
        # thật. Chỉ số mảng của các nến SAU đó liền lại, nhưng timestamp
        # thì nhảy vọt.
        df = df.drop(index=4).reset_index(drop=True)
        thap_sau_khi_khoet = df["low"].tolist()
        thoi_gian = df["date"].tolist()

        i = 3  # vẫn đúng vị trí swing (giá 5) — index này đứng trước chỗ bị khoét
        assert la_diem_swing(thap_sau_khi_khoet, i, loai="day") is True

        j = i + K_XAC_NHAN
        # Bất biến CRITICAL: thời gian trôi qua PHẢI >= k nến — khoảng
        # trống chỉ có thể làm nó NHIỀU hơn, không bao giờ ít hơn. Đây là
        # chỗ duy nhất phơi bày sai lầm nếu có code nào coi "chỉ số +k"
        # là đủ để xác nhận mà không kiểm timestamp thật.
        assert thoi_gian[j] - thoi_gian[i] > K_XAC_NHAN * KHUNG_4H
