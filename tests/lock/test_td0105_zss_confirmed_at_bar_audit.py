"""TD-0105 — H13 (spec dòng 4345): audit ZSS toàn bộ — `touch_count`,
`volume_ratio`, `compression` (và giá trị `zss()` tổng hợp từ ba cái đó)
KHÔNG được dùng dữ liệu ngoài `confirmed_at_bar`.

Không phải test riêng lẻ từng hàm (đã khoá ở `test_zone_strength.py`) —
đây là bài audit TÍCH HỢP: dựng một chuỗi giá dài, tính cả ba thành phần
+ `zss()` tại đúng `confirmed_at_bar`, rồi CẮT mảng dữ liệu ngay tại đó
và tính lại từ đầu — mọi giá trị phải giống hệt tuyệt đối. Không có L-Z
nào được spec gán cho H13 (chỉ có tên "H13", không có mã) nên đặt tên
theo quy ước tự đặt của repo (`test_td<số>_...`), không chiếm namespace
`L-Z`.
"""

from __future__ import annotations

from tool_d.zone_detection import K_XAC_NHAN
from tool_d.zone_strength import compression, touch_count, volume_ratio, zss

I_SWING = 25
CONFIRMED_AT_BAR = I_SWING + K_XAC_NHAN
ZONE_LOW, ZONE_HIGH = 100.0, 102.0


def _du_lieu_dai(n: int) -> dict[str, list[float]]:
    dong = [100.0 + (i % 7) * 0.3 for i in range(n)]
    thap = [c - 0.4 for c in dong]
    cao = [c + 0.4 for c in dong]
    # Đặt đúng swing tại I_SWING (đáy) và một cụm chạm-bật-ra ngay sau đó
    thap[I_SWING] = ZONE_LOW
    dong[I_SWING] = ZONE_LOW + 0.2
    thap[I_SWING + 1] = ZONE_LOW + 0.5  # chạm
    dong[I_SWING + 1] = ZONE_LOW + 0.5
    thap[I_SWING + 2] = ZONE_LOW + 0.5
    dong[I_SWING + 2] = ZONE_HIGH + 1.0  # bật ra -> đóng cụm, 1 touch
    volume = [10.0 + (i % 5) for i in range(n)]
    volume[I_SWING] = 40.0  # volume tăng vọt lúc hình thành zone
    # Từ giữa chuỗi trở đi biên độ giãn mạnh -> ATR về sau khác hẳn ATR lúc hình thành
    for i in range(50, n):
        cao[i] = dong[i] + 6.0
        thap[i] = dong[i] - 6.0
    return {"cao": cao, "thap": thap, "dong": dong, "volume": volume}


class TestAuditZssKhongDocDuLieuNgoaiConfirmedAtBar:
    def test_ca_ba_thanh_phan_va_zss_khong_doi_khi_cat_du_lieu(self) -> None:
        day_du = _du_lieu_dai(90)
        bi_cat = {k: v[: CONFIRMED_AT_BAR + 1] for k, v in day_du.items()}

        def tinh(du_lieu: dict[str, list[float]]) -> tuple[int, float, float, float]:
            t_c = touch_count(
                du_lieu["thap"], du_lieu["dong"], ZONE_LOW, ZONE_HIGH,
                i_swing=I_SWING, t=CONFIRMED_AT_BAR, loai="day",
            )
            v_r = volume_ratio(du_lieu["volume"], i_swing=I_SWING)
            comp = compression(
                du_lieu["cao"], du_lieu["thap"], du_lieu["dong"],
                i_hinh_thanh=I_SWING, i_hien_tai=CONFIRMED_AT_BAR,
            )
            assert v_r is not None
            assert comp is not None
            z = zss(touch=t_c, ty_le_volume=v_r, do_nen=comp)
            return t_c, v_r, comp, z

        truoc_khi_cat = tinh(day_du)
        sau_khi_cat = tinh(bi_cat)

        assert truoc_khi_cat == sau_khi_cat
        # Xác nhận fixture có nghĩa — không phải mọi giá trị đều 0/None trùng hợp
        assert truoc_khi_cat[0] == 1  # đúng 1 cụm chạm-bật-ra đã dựng
