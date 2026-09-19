"""TD-0330 (OQ-14b) — khoá CẢ HAI chiều của cực trị cụm trong `quet_xac_nhan_zone()`.

Vì sao có file này: phá-thật của `TD-0320` (`1be9b88`, công cụ `TD-0329`) cho thấy chiều
**Long** (`loai="day"`, cực trị = giá NHỎ NHẤT của cụm) chỉ được canh bởi MỘT test ngoài ca
`day` của chính `TD-0320`. Khi vá quá tay (luôn so `>`), `test_lz6` và `test_td0294` vẫn xanh.
Đường Long là đường đang sinh tiền, nên lớp canh mỏng ở đây không chấp nhận được.

════ Thiết kế: cực trị đặt ở nến CUỐI cụm ════

Điều kiện (b) của §3.3b so giá lượt chạm sau với MỐC lượt trước (giá tại cực trị THẬT của cả
cụm trước). Có ba cách chọn mốc SAI, và kịch bản ở đây làm chúng cho ba kết quả KHÁC NHAU:

    cách chọn mốc              day (Long, thấp nhất)      dinh (Short, cao nhất)
    ─────────────────────────  ─────────────────────────  ─────────────────────────
    ĐÚNG: cực trị thật         91  (nến CUỐI)             99  (nến CUỐI)
    sai: nến ĐẦU cụm (09/09)   96                         94
    sai: luôn min (TD-0320)    91 (trùng — day đúng)      92  ← làm hỏng dinh
    sai: luôn max (vá quá tay) 98  ← làm hỏng day         99 (trùng — dinh đúng)

Cực trị nằm ở nến CUỐI nên nó KHÁC nến đầu cụm; giá lượt 2 đặt GIỮA mốc đúng và mốc sai ⇒ chỉ
mốc đúng mới cho kết quả "không xác nhận". Ca dương (đúng bằng cực trị) chống hướng ngược:
"vá bằng cách không bao giờ xác nhận" cũng làm ca âm xanh.

Vế RSI luôn thoả (lượt 2 lệch đúng chiều so với 60) ⇒ kết quả CHỈ phụ thuộc mốc GIÁ.
Thân nến = giá cực trị ⇒ `la_nen_rejection` luôn False ⇒ lượt 1 không tự xác nhận.

Nghiệm thu bằng công cụ `TD-0329` (`tests/tools/specs/td0330_khoa_hai_chieu.json`, `tests` chỉ
là FILE NÀY): M1 phải làm đỏ ca âm `dinh`, M2 phải làm đỏ ca âm `day`.
"""

from __future__ import annotations

import pytest

from tool_d.entry_confirmation import quet_xac_nhan_zone

N = 10
ZL, ZH = 90.0, 100.0

# cụm lượt 1, đã kiểm: cực trị thật ở nến CUỐI (idx 3), khác nến đầu và khác cực trị ngược.
CUM = {
    "day": [96.0, 98.0, 97.0, 91.0],   # min 91 (idx3) · đầu 96 · max 98
    "dinh": [94.0, 92.0, 93.0, 99.0],  # max 99 (idx3) · đầu 94 · min 92
}
NGOAI_ZONE = {"day": 80.0, "dinh": 110.0}
RSI_LUOT_2 = {"day": 80.0, "dinh": 40.0}  # vế RSI của (b) luôn thoả


def _du_lieu(loai: str, gia_luot_2: float) -> dict:
    mo, cao, thap, dong, rsi = ([0.0] * N for _ in range(5))
    for i, c in enumerate(CUM[loai]):
        if loai == "day":
            thap[i], cao[i] = c, c + 1.0
        else:
            cao[i], thap[i] = c, c - 1.0
        mo[i] = dong[i] = c
        rsi[i] = 60.0
    ngoai = NGOAI_ZONE[loai]
    mo[4] = cao[4] = thap[4] = dong[4] = ngoai
    rsi[4] = 60.0
    mo[5] = dong[5] = cao[5] = gia_luot_2
    thap[5] = gia_luot_2 if loai == "day" else gia_luot_2 - 1.0
    rsi[5] = RSI_LUOT_2[loai]
    for i in (6, 7, 8, 9):  # đệm NGOÀI zone, RSI == mốc ⇒ (b) luôn False ở đây
        mo[i] = cao[i] = thap[i] = dong[i] = ngoai
        rsi[i] = 60.0
    return dict(mo=mo, cao=cao, thap=thap, dong=dong, rsi=rsi, vol=[10.0] * N, vma=[10.0] * N)


def _quet(loai: str, gia_luot_2: float):
    d = _du_lieu(loai, gia_luot_2)
    return quet_xac_nhan_zone(
        d["mo"], d["cao"], d["thap"], d["dong"], d["rsi"], d["vol"], d["vma"],
        zone_low=ZL, zone_high=ZH, tu=0, den=N, v_min=1.0, loai=loai,
        lan_cham_truoc_khi_xac_nhan=None, bat_dieu_kien_c=False, wick_frac=0.5,
    )


# (loai, giá lượt 2, có xác nhận phản thực không, vì sao)
CA = [
    pytest.param("day", 93.0, False, id="day-93-khong_xac_nhan"),    # giữa min thật 91 và nến đầu 96 / max 98
    pytest.param("day", 91.0, True, id="day-91-bang_cuc_tri"),       # đúng bằng đáy thật
    pytest.param("day", 90.5, True, id="day-90.5-thap_hon_cuc_tri"), # thấp hơn đáy thật, vẫn trong zone
    pytest.param("dinh", 96.0, False, id="dinh-96-khong_xac_nhan"),  # giữa max thật 99 và nến đầu 94 / min 92
    pytest.param("dinh", 99.0, True, id="dinh-99-bang_cuc_tri"),     # đúng bằng đỉnh thật
    pytest.param("dinh", 99.5, True, id="dinh-99.5-cao_hon_cuc_tri"),
]


class TestCucTriCumHaiChieu:
    @pytest.mark.parametrize("loai,gia,co_xac_nhan", CA)
    def test_xac_nhan_khi_va_chi_khi_gia_toi_cuc_tri_that(self, loai, gia, co_xac_nhan) -> None:
        kq = _quet(loai, gia)
        if co_xac_nhan:
            assert kq.nen_xac_nhan_phan_thuc == 5, kq
            assert kq.lan_cham_phan_thuc == 2, kq
        else:
            assert kq.nen_xac_nhan_phan_thuc is None, (
                f"loai={loai}: giá {gia} CHƯA tới cực trị thật của cụm ({CUM[loai][-1]}) mà vẫn "
                f"xác nhận ⇒ mốc so đang là một giá khác cực trị thật: {kq}"
            )
            assert kq.lan_cham_phan_thuc == 0

    @pytest.mark.parametrize("loai", ["day", "dinh"])
    def test_luot_1_khong_bao_gio_tu_xac_nhan_o_kich_ban_nay(self, loai) -> None:
        """Đối chứng của chính kịch bản: lượt 1 không có mốc trước và không có nến rejection nên
        không được xác nhận ⇒ mọi khác biệt ở các ca trên chỉ đến từ mốc GIÁ của cụm lượt 1."""
        assert _quet(loai, 50.0).nen_xac_nhan_that is None

    @pytest.mark.parametrize("loai", ["day", "dinh"])
    def test_kich_ban_dung_hinh_dang_cuc_tri_o_nen_cuoi(self, loai) -> None:
        """Khoá GIẢ ĐỊNH của thiết kế: nếu ai đổi số liệu làm cực trị rơi về nến đầu, ba cách
        chọn sai lại trùng nhau và cả file này trở thành xanh-vô-nghĩa."""
        cum = CUM[loai]
        cuc_tri = min(cum) if loai == "day" else max(cum)
        cuc_tri_nguoc = max(cum) if loai == "day" else min(cum)
        assert cum.index(cuc_tri) == len(cum) - 1
        assert cum[0] not in (cuc_tri, cuc_tri_nguoc)
        assert ZL <= min(cum) and max(cum) <= ZH
