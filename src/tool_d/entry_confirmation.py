"""§3.3b — Xác nhận entry tranche 1 bằng price-action (TD-0129, trước 07/09/2026
đánh số TD-0120; L-Z6).

ZSS (§1.2) chỉ đo chất lượng LỊCH SỬ của zone; đây là lớp xác nhận hấp
thụ đang diễn ra NGAY LÚC giá chạm zone — (a) nến rejection HOẶC (b)
phân kỳ momentum RSI, tối đa 3 nến chờ, KHÔNG mở rộng cửa sổ (chống
overfitting ngược — nới thời gian chờ tới khi thấy xác nhận sẽ luôn
"thành công" trên dữ liệu lịch sử nhưng vô nghĩa).

RSI(14,1H) tính bằng TA-Lib ở tầng gọi (cùng kiểu với ATR trong
`zone_strength.py`) — module này chỉ nhận mảng RSI đã tính sẵn.
"""

from __future__ import annotations

from typing import Literal, Sequence

SO_NEN_CHO_MAC_DINH = 3


def la_nen_rejection(mo: float, cao: float, thap: float, dong: float, *, loai: Literal["day", "dinh"]) -> bool:
    """§3.3b(a) — bóng đối hướng ≥50% range nến, đóng cửa nửa còn lại.

    Zone đáy (`loai="day"`, case LONG): bóng DƯỚI ≥50% range, đóng cửa
    trong nửa TRÊN. Zone đỉnh (`loai="dinh"`) đảo dấu.
    """
    bien_do = cao - thap
    if bien_do <= 0:
        return False
    if loai == "day":
        bong_duoi = min(mo, dong) - thap
        return bong_duoi >= 0.5 * bien_do and dong >= thap + 0.5 * bien_do
    bong_tren = cao - max(mo, dong)
    return bong_tren >= 0.5 * bien_do and dong <= cao - 0.5 * bien_do


def phan_ky_momentum(
    *, rsi_hien_tai: float, gia_hien_tai: float, rsi_truoc: float, gia_truoc: float, loai: Literal["day", "dinh"]
) -> bool:
    """§3.3b(b) — zone đáy: RSI tạo đáy CAO HƠN trong khi giá tạo đáy
    THẤP HƠN hoặc BẰNG so với lần chạm trước. Zone đỉnh đảo dấu."""
    if loai == "day":
        return rsi_hien_tai > rsi_truoc and gia_hien_tai <= gia_truoc
    return rsi_hien_tai < rsi_truoc and gia_hien_tai >= gia_truoc


def tim_xac_nhan_entry(
    mo: Sequence[float],
    cao: Sequence[float],
    thap: Sequence[float],
    dong: Sequence[float],
    rsi: Sequence[float],
    i_cham: int,
    *,
    loai: Literal["day", "dinh"],
    lan_cham_truoc: tuple[float, float] | None = None,
    so_nen_cho_toi_da: int = SO_NEN_CHO_MAC_DINH,
) -> int | None:
    """Quét tối đa `so_nen_cho_toi_da` nến kể từ `i_cham` (nến giá vừa
    chạm zone) tìm rejection HOẶC phân kỳ RSI. Trả về chỉ số nến xác
    nhận đầu tiên, hoặc `None` nếu hết hạn mà chưa có — KHÔNG BAO GIỜ
    tìm tiếp ngoài cửa sổ này (đúng lời spec, chống overfitting ngược).

    `lan_cham_truoc` = (giá, RSI) của lần chạm zone gần nhất — `None`
    nếu đây là lần chạm đầu tiên (không có gì để so, chỉ còn phần (a)).
    """
    gia_bien_muc = thap if loai == "day" else cao
    cuoi = min(i_cham + so_nen_cho_toi_da, len(dong))
    for j in range(i_cham, cuoi):
        if la_nen_rejection(mo[j], cao[j], thap[j], dong[j], loai=loai):
            return j
        if lan_cham_truoc is not None:
            gia_truoc, rsi_truoc = lan_cham_truoc
            if phan_ky_momentum(
                rsi_hien_tai=rsi[j], gia_hien_tai=gia_bien_muc[j], rsi_truoc=rsi_truoc, gia_truoc=gia_truoc, loai=loai
            ):
                return j
    return None
