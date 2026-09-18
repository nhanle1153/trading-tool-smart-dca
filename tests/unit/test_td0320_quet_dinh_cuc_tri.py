"""TD-0320 (DR-SHORT-01, DR-012 Hạng 1) — sửa lỗi thật trong
`quet_xac_nhan_zone()`: vòng quét cụm tìm mốc CỰC TRỊ cho lượt sau
(dùng cho điều kiện (b) — phân kỳ momentum) so `<` VÔ ĐIỀU KIỆN, tức
luôn tìm giá trị NHỎ NHẤT trong cụm. Đúng cho `loai="day"` (cần đáy
thấp nhất), SAI cho `loai="dinh"` (cần đỉnh CAO NHẤT, phải so `>`).

Đây KHÔNG phải diễn giải mới — nó là lỗi code-vs-spec thuần tuý (DR-012
Hạng 1, 0 trial, tự do sửa). Đường Long sản xuất (`ZoneAbsorption.py`)
chỉ gọi hàm này với `loai="day"` nên KHÔNG bị ảnh hưởng; kịch bản dưới
đây khoá riêng nhánh `loai="dinh"`.

🔑 **Vì sao bug chỉ gây SAI theo MỘT chiều, không phải cả hai** (giải
thích trong test, không chỉ trong code): với `loai="dinh"`, điều kiện
(b) là `gia_hien_tai >= gia_truoc`. Mốc `gia_truoc` do bug tính LUÔN
NHỎ HƠN HOẶC BẰNG mốc đúng (bug tìm MIN thay vì MAX của cùng một cụm),
nên bug chỉ có thể làm điều kiện DỄ THOẢ HƠN — tức XÁC NHẬN GIẢ (lạc
quan), không bao giờ BỎ LỠ một xác nhận thật. Cùng chiều với bug LONG
đã sửa 09/09/2026 (dùng nến đầu cụm thay vì đáy thật) — xem "Diễn giải
#1" trong docstring module.

Kịch bản dùng chung cho cả hai test dưới: cụm chạm lượt 1 (idx 0-3, giá
CAO = [95, 92, 99, 96]) — cực trị ĐÚNG là 99 (idx 2), cực trị theo bug
(MIN của cụm) là 92 (idx 1). Không candle nào trong cụm xác nhận được
lượt 1 (thân nến bằng High → `la_nen_rejection` luôn `False`, và
`lan_cham_truoc=None` ở lượt 1 nên (b) không có gì để so). Lượt 2 (idx
5) có RSI thấp hơn mốc lượt 1 (40 < 60) — vế RSI của phân kỳ luôn thoả
— nên toàn bộ kết quả CHỈ phụ thuộc vào mốc GIÁ được chọn cho lượt 1."""

from __future__ import annotations

from tool_d.entry_confirmation import quet_xac_nhan_zone

N = 10
ZL, ZH = 90.0, 100.0
CUM_LUOT_1 = [95.0, 92.0, 99.0, 96.0]  # min=92 (idx1, bug) ; max=99 (idx2, đúng)


def _du_lieu(gia_luot_2: float) -> dict:
    mo = [0.0] * N
    cao = [0.0] * N
    thap = [0.0] * N
    dong = [0.0] * N
    rsi = [0.0] * N

    # idx0-3: cụm chạm lượt 1 — thân nến = High (mo=dong=cao) nên
    # `la_nen_rejection` luôn False (bóng trên = 0), (a) không bao giờ
    # thoả bất kể bat_dieu_kien_c.
    for i, c in enumerate(CUM_LUOT_1):
        cao[i], thap[i], mo[i], dong[i], rsi[i] = c, c - 1.0, c, c, 60.0

    # idx4: nến đệm NGOÀI zone — kết thúc cụm lượt 1.
    cao[4] = thap[4] = mo[4] = dong[4] = 110.0
    rsi[4] = 60.0

    # idx5: nến đầu cụm lượt 2, TRONG zone. RSI thấp hơn mốc lượt 1
    # (40 < 60) — vế RSI của (b) luôn thoả, phép thử chỉ còn phụ thuộc
    # mốc GIÁ do lượt 1 để lại.
    cao[5] = thap[5] = mo[5] = dong[5] = gia_luot_2
    thap[5] = gia_luot_2 - 1.0
    rsi[5] = 40.0

    # idx6-9: nến đệm NGOÀI zone, RSI == mốc lượt 1 (60) để (b) LUÔN
    # False tại đây bất kể giá — chặn mọi khả năng lượt 3 gây nhiễu.
    for i in (6, 7, 8, 9):
        cao[i] = thap[i] = mo[i] = dong[i] = 110.0
        rsi[i] = 60.0

    vol = [10.0] * N
    vma = [10.0] * N
    return dict(mo=mo, cao=cao, thap=thap, dong=dong, rsi=rsi, volume=vol, volume_ma=vma)


class TestQuetDinhDungCucTriCaoNhatKhongPhaiMin:
    def test_gia_giua_min_va_max_KHONG_xac_nhan_o_dung_code(self) -> None:
        """Gương đúng: mốc = 99 (max thật). 95 >= 99 là False -> (b)
        không thoả -> KHÔNG có xác nhận phản thực nào.

        🔴 Kiểm có răng — đã PHÁ THẬT trước khi viết bài test này (đổi
        vòng quét về so `<` vô điều kiện như bản lỗi, chạy lại chính
        kịch bản này trên bản phá): kết quả đổi thành
        `nen_xac_nhan_phan_thuc=5, lan_cham_phan_thuc=2` — tức bug làm
        lượt 2 xác nhận GIẢ ngay tại nến đầu tiên của cụm, vì mốc so
        sánh (92, do bug chọn MIN) thấp hơn 95. Không sửa lại comparator
        sẽ không có cách nào cho test này thấy sự khác biệt bằng dữ liệu
        tổng hợp — đúng tinh thần N7 (chỉ chạy thật mới là bằng chứng)
        áp cho chính vòng đời viết test, không chỉ cho suite Docker."""
        d = _du_lieu(gia_luot_2=95.0)
        kq = quet_xac_nhan_zone(
            d["mo"], d["cao"], d["thap"], d["dong"], d["rsi"], d["volume"], d["volume_ma"],
            zone_low=ZL, zone_high=ZH, tu=0, den=N, v_min=1.0,
            loai="dinh", lan_cham_truoc_khi_xac_nhan=None,
            bat_dieu_kien_c=False, wick_frac=0.5,
        )
        assert kq.nen_xac_nhan_phan_thuc is None
        assert kq.lan_cham_phan_thuc == 0
        # Phương án A (lượt 1) không bị ảnh hưởng bởi bug này — lượt 1
        # không có `lan_cham_truoc` nên (b) vốn đã không khả dụng.
        assert kq.nen_xac_nhan_that is None

    def test_gia_dung_bang_cuc_tri_that_THI_xac_nhan(self) -> None:
        """Đối chứng dương: mốc = 99 (max thật). 99 >= 99 là True -> (b)
        thoả tại nến đầu cụm lượt 2 (idx 5) -> xác nhận phản thực lượt 2.

        Không có ca này, bản vá dễ bị nghi ngờ theo chiều ngược: "vá
        bằng cách làm nhánh dinh không bao giờ xác nhận được nữa" cũng
        sẽ làm ca âm ở trên xanh."""
        d = _du_lieu(gia_luot_2=99.0)
        kq = quet_xac_nhan_zone(
            d["mo"], d["cao"], d["thap"], d["dong"], d["rsi"], d["volume"], d["volume_ma"],
            zone_low=ZL, zone_high=ZH, tu=0, den=N, v_min=1.0,
            loai="dinh", lan_cham_truoc_khi_xac_nhan=None,
            bat_dieu_kien_c=False, wick_frac=0.5,
        )
        assert kq.nen_xac_nhan_phan_thuc == 5
        assert kq.lan_cham_phan_thuc == 2
        assert kq.loai_xac_nhan_that is None  # lượt 1 (Phương án A) vẫn không xác nhận


class TestQuetDayKhongDoiHanhVi:
    """Đối chứng hồi quy: cùng kịch bản, đổi `loai="day"` (dùng `thap`
    thay `cao`) — vòng quét MIN vẫn đúng, kết quả phải giống hệt trước
    TD-0320 (nhánh `if loai == "day"` chạy đúng công thức cũ)."""

    def test_day_van_tim_dung_min_nhu_truoc(self) -> None:
        mo = [0.0] * N
        cao = [0.0] * N
        thap = [0.0] * N
        dong = [0.0] * N
        rsi = [0.0] * N
        cum = [95.0, 98.0, 92.0, 96.0]  # min=92 (idx2, đáy thật) — vị trí LỆCH idx đầu cụm
        for i, c in enumerate(cum):
            thap[i], cao[i], mo[i], dong[i], rsi[i] = c, c + 1.0, c, c, 60.0
        thap[4] = cao[4] = mo[4] = dong[4] = 80.0  # đệm NGOÀI zone [90,100]
        rsi[4] = 60.0
        # lượt 2: giá NẰM GIỮA nến đầu cụm (95) và đáy thật (92) -> chỉ
        # xác nhận nếu mốc = đáy thật (92), không xác nhận nếu mốc = nến
        # đầu cụm (95) — cùng cấu trúc phân biệt như test "dinh" ở trên.
        thap[5] = cao[5] = mo[5] = dong[5] = 93.0
        rsi[5] = 80.0  # CAO hơn mốc (60) -> vế RSI của (b) cho "day" luôn thoả (rsi_hien_tai > rsi_truoc)
        for i in (6, 7, 8, 9):
            thap[i] = cao[i] = mo[i] = dong[i] = 80.0
            rsi[i] = 60.0
        vol = [10.0] * N
        vma = [10.0] * N

        kq = quet_xac_nhan_zone(
            mo, cao, thap, dong, rsi, vol, vma,
            zone_low=90.0, zone_high=100.0, tu=0, den=N, v_min=1.0,
            loai="day", lan_cham_truoc_khi_xac_nhan=None,
            bat_dieu_kien_c=False, wick_frac=0.5,
        )
        # (b) cho "day": rsi_hien_tai > rsi_truoc and gia_hien_tai <= gia_truoc
        # 93 <= 92 (đáy thật)? False -> KHÔNG xác nhận, đúng công thức cũ.
        assert kq.nen_xac_nhan_phan_thuc is None
        assert kq.lan_cham_phan_thuc == 0
