"""Kế hoạch tranche cho một zone — §3.1 (giá) + §3.5 (p1_order) — TD-0114.

Gộp p1/p2/p3/sl/`r_eff_plan`/`atr_1h_tai_tranche1` vào MỘT cấu trúc bất
biến, JSON hoá được — đây CHÍNH LÀ dữ liệu phải sống sót NGUYÊN VẸN qua
`trade.custom_data` ở các callback tranche 2/3 + `custom_exit` (L-Z49).
Ghi MỘT LẦN lúc tranche 1 khớp, không bao giờ tính lại theo giá hiện tại
(§4c.2 cảnh báo rõ: tính lại theo `p_avg` hiện tại làm ngưỡng thành mục
tiêu di động).

Phạm vi CHƯA phủ, nói thẳng: `p1` ở đây là `zone_high` danh nghĩa hoặc
giá đóng cửa nến zone 4H hình thành/xác nhận — CHƯA áp đúng "nến 1H đóng
cửa C" mà §3.3b/§3.5 mô tả (xác nhận entry qua §3.3b bị hoãn khỏi tín
hiệu vào lệnh ở TD-0114, xem ghi chú trong `ARCHITECTURE.md`/TASKS.md).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

BUF_SL_HE_SO = 0.4  # §3.1 — buf_sl = 0.4 × ATR(14,4H)/price, [CẦN CALIBRATE]
TRONG_SO_TRANCHE = 1 / 3  # §3.1 — w = [1/3,1/3,1/3], ĐÓNG BĂNG


@dataclass(frozen=True)
class KeHoachTranche:
    zone_low: float
    zone_high: float
    p1: float
    p2: float
    p3: float
    sl: float
    r_eff_plan: float
    atr_1h_tai_tranche1: float

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "KeHoachTranche":
        return cls(**d)


def tinh_ke_hoach(
    *, zone_low: float, zone_high: float, gia_dong_cua: float, atr_4h: float, atr_1h_tai_tranche1: float
) -> KeHoachTranche:
    """§3.1 (case LONG, zone đáy) + §3.5 (p1_order).

    `atr_4h` CHỈ dùng để tính `buf_sl` (đúng khung ATR spec chỉ định).
    `atr_1h_tai_tranche1` chỉ được LƯU LẠI ở đây, dùng cho DG6 điều
    kiện A sau này (`dg6_early_invalidation.dieu_kien_a`) — không tính
    gì với nó ở hàm này.
    """
    p1 = min(zone_high, gia_dong_cua)
    p2 = (zone_high + zone_low) / 2
    p3 = zone_low
    buf_sl = BUF_SL_HE_SO * atr_4h / zone_low
    sl = zone_low * (1 - buf_sl)
    p_avg = (p1 + p2 + p3) / 3  # TRONG_SO_TRANCHE bằng nhau cả ba
    r_eff_plan = (p_avg - sl) / p_avg
    return KeHoachTranche(
        zone_low=zone_low,
        zone_high=zone_high,
        p1=p1,
        p2=p2,
        p3=p3,
        sl=sl,
        r_eff_plan=r_eff_plan,
        atr_1h_tai_tranche1=atr_1h_tai_tranche1,
    )
