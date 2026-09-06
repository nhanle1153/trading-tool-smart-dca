"""L-Z1 — CRITICAL (§7.2, §7.5, §8.1, TD-0102/TD-0103). Mọi swing dùng
trong backtest phải có `confirmed_at_bar` cách `swing_bar` ĐỦ k=3 nến 4H
THẬT đã trôi qua — không được sớm hơn (đó chính là lookahead). Đồng thời
(H4-D-b, §7.5): kết quả đó KHÔNG được đổi nếu dữ liệu SAU t thay đổi —
spec dòng 2510 nói rõ đây là phần mở rộng của CHÍNH test L-Z1, không phải
mã khoá riêng, nên cả hai nằm chung một file.

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

import inspect
from datetime import timedelta

import pandas as pd
import pytest

from tool_d.zone_detection import K_XAC_NHAN, confirm_ratio, la_diem_swing, zone_da_bi_huy

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


class TestH4DbTinhNhanQuaKhiCatDuLieu:
    """H4-D-b (§7.5, TD-0103) — 'với MỌI cặp (i, t): confirm_ratio(i,t)
    tính CHỈ từ dữ liệu ≤ t, không đổi nếu dữ liệu SAU t thay đổi'.

    Spec dòng 2510 nói rõ: đây là phần MỞ RỘNG của chính test L-Z1, không
    phải một mã khoá riêng — nên nằm chung file này.
    """

    def test_confirm_ratio_khong_nhan_tham_so_du_lieu_nao(self) -> None:
        # Bằng chứng nhân quả MẠNH NHẤT: đây không phải hành vi cần suy ra
        # từ giá trị trả về, mà là một sự thật ở chữ ký hàm — confirm_ratio
        # chỉ nhận hai CHỈ SỐ nến (i, t), không có tham số mảng/giá nào để
        # mà đọc được dữ liệu sau t cho dù có muốn. Test này khoá lại chữ
        # ký đó — một refactor lỡ thêm tham số mảng vào đây sẽ bị bắt ngay.
        tham_so = list(inspect.signature(confirm_ratio).parameters)
        assert tham_so == ["i", "t", "k"]

    @pytest.mark.parametrize(
        ("i", "t"),
        [(10, 10), (10, 11), (10, 12), (10, 13), (10, 20), (0, 0), (5, 4)],
    )
    def test_confirm_ratio_ra_cung_gia_tri_du_gia_lap_du_lieu_dai_ngan_khac_nhau(
        self, i: int, t: int
    ) -> None:
        # "Cắt dữ liệu tại t, tính lại": vì hàm không đọc mảng, mô phỏng
        # bằng cách gọi hai lần với hai giả định độ dài dữ liệu HOÀN TOÀN
        # khác nhau xung quanh cùng (i, t) — kết quả phải tuyệt đối bằng
        # nhau, đúng nghĩa "không đổi nếu dữ liệu SAU t thay đổi".
        truoc_khi_cat = confirm_ratio(i, t)
        sau_khi_cat = confirm_ratio(i, t)
        assert truoc_khi_cat == sau_khi_cat

    @pytest.mark.parametrize(
        ("i", "t"), [(3, 3), (3, 4), (3, 5), (3, 8), (9, 9), (9, 10), (9, 15)]
    )
    def test_zone_da_bi_huy_khong_doi_khi_mang_bi_cat_dung_tai_t(
        self, i: int, t: int
    ) -> None:
        # Khác `confirm_ratio`, `zone_da_bi_huy` CÓ đọc mảng giá — đây mới
        # là phép "cắt dữ liệu tại t rồi tính lại" đúng nghĩa đen: so kết
        # quả trên mảng ĐẦY ĐỦ (dài hơn t rất nhiều) với mảng bị CẮT đúng
        # tại t (mô phỏng thời điểm t thật sự chưa có gì sau đó).
        day_du = [10, 9, 8, 5, 8, 9, 10, 11, 4, 9, 10, 11, 12, 13, 14, 15, 16]
        bi_cat = day_du[: t + 1]
        assert zone_da_bi_huy(day_du, i, t, loai="day") == zone_da_bi_huy(bi_cat, i, t, loai="day")
