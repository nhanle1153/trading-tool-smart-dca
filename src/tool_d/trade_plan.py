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

════ TD-0319 — tham số `huong`, chỉ DỰNG, công tắc tắt (DR-SHORT-01) ════

`huong` mặc định `"long"`: mọi lời gọi cũ (không truyền `huong`) chạy
ĐÚNG NHÁNH CODE CŨ, không một dòng nào đổi hành vi. Nhánh `"short"` là
GƯƠNG đại số của nhánh long, không phải "đảo dấu" hời hợt:

    LONG:  sl = zone_low  − buf_sl_he_so·atr_4h   (neo mép DƯỚI zone)
    SHORT: sl = zone_high + buf_sl_he_so·atr_4h   (neo mép TRÊN zone)

Rút gọn công thức LONG cho thấy vì sao đơn giản đến vậy: `buf_sl =
he_so·atr_4h/zone_low` rồi `sl = zone_low·(1−buf_sl) = zone_low −
he_so·atr_4h` — hệ số ATR chỉ mượn `zone_low` làm mẫu số phần trăm rồi
triệt tiêu lại. Nhân bản y hệt sang `zone_high` cho SHORT.

`p1`/`p3` cũng gương: LONG lấy `p1=min(zone_high, close)` (không vượt quá
đỉnh zone) và `p3=zone_low` (đáy zone). SHORT lấy `p1=max(zone_low,
close)` (không thấp hơn đáy zone) và `p3=zone_high` (đỉnh zone). `p2` là
điểm giữa zone — không phụ thuộc hướng.

`r_eff_plan` LONG = `(p_avg − sl)/p_avg` (sl DƯỚI p_avg). SHORT =
`(sl − p_avg)/p_avg` (sl TRÊN p_avg) — cùng ý nghĩa "khoảng cách tới SL
tính theo tỉ lệ trên giá vào trung bình", dương ở cả hai hướng.

🔴 Phép GƯƠNG này KHÔNG bảo toàn `r_eff_plan` dưới một phép phản chiếu
giá `x → K−x` tổng quát (mẫu số `p_avg` đổi thành `K−p_avg` ≠ `p_avg`
trừ khi `K = 2·p_avg`) — test gương ở `tests/unit/test_td0319_module_thuan_huong.py`
chỉ khẳng định p1/p2/p3/sl gương, KHÔNG khẳng định r_eff gương, và ghi
rõ lý do đại số thay vì âm thầm bỏ qua.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

TRONG_SO_TRANCHE = 1 / 3  # §3.1 — w = [1/3,1/3,1/3], ĐÓNG BĂNG

Huong = Literal["long", "short"]


class TradePlanError(ValueError):
    """Hướng không hợp lệ, hoặc thiếu đại lượng bắt buộc cho hướng đó."""

# 🔴 TD-0195 — `BUF_SL_HE_SO = 0.4` ĐÃ BỊ XOÁ: bản sao cứng của
# `tier_b.buf_sl_atr` (tunable #2). Xem chú thích cùng loại ở
# `zone_strength.py`. Hệ số nay là đối số BẮT BUỘC của `tinh_ke_hoach()`.
# Lưu ý `TRONG_SO_TRANCHE` KHÔNG cùng loại: nó ĐÓNG BĂNG ở
# `tier_frozen.w_tranche` và `sizing.py` đã đọc qua `resolve()` — hằng số
# ở đây chỉ còn là tài liệu của công thức p_avg, không phải ngưỡng tune.


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


def sl_kieu_zone(
    *,
    zone_low: float,
    zone_high: float | None = None,
    atr_4h: float,
    buf_sl_he_so: float,
    huong: Huong = "long",
) -> float:
    """SL kiểu ZONE §3.1 — NGUỒN DUY NHẤT của công thức (TD-0294).

    Hai nơi dùng PHẢI gọi đúng hàm này: `tinh_ke_hoach()` (SL thật của lệnh) và
    `ZoneAbsorption._xac_nhan_3_3b` (cắt cửa sổ + chặn xác nhận đã thủng SL). Bảo
    đảm *"xác nhận đòi close(C) > sl_zone ⇒ p1 > kh.sl"* chỉ đứng được khi hai
    phía là MỘT công thức; `buf_sl_he_so` là tunable #2 mà D5 calibrate — viết
    hai lần thì sửa một phía là lệnh dưới SL quay lại mà không phép kiểm nào đỏ.

    `huong="long"` (mặc định) là code CŨ nguyên vẹn — `zone_high` không được
    đọc. `huong="short"` (TD-0319, DR-SHORT-01, D-dựng, 0 trial) neo mép
    TRÊN zone thay vì mép dưới — xem docstring module về phép gương đại số.
    """
    if huong == "long":
        buf_sl = buf_sl_he_so * atr_4h / zone_low
        return zone_low * (1 - buf_sl)
    if huong == "short":
        if zone_high is None:
            raise TradePlanError("huong='short' bắt buộc truyền zone_high")
        buf_sl = buf_sl_he_so * atr_4h / zone_high
        return zone_high * (1 + buf_sl)
    raise TradePlanError(f"huong không hợp lệ: {huong!r}")


def tinh_ke_hoach(
    *,
    zone_low: float,
    zone_high: float,
    gia_dong_cua: float,
    atr_4h: float,
    atr_1h_tai_tranche1: float,
    buf_sl_he_so: float,
    huong: Huong = "long",
) -> KeHoachTranche:
    """§3.1 (case LONG, zone đáy) + §3.5 (p1_order). Case SHORT (zone đỉnh)
    là phần dựng TD-0319 (DR-SHORT-01), công tắc `enable_short` vẫn tắt.

    `atr_4h` CHỈ dùng để tính `buf_sl` (đúng khung ATR spec chỉ định).
    `atr_1h_tai_tranche1` chỉ được LƯU LẠI ở đây, dùng cho DG6 điều
    kiện A sau này (`dg6_early_invalidation.dieu_kien_a`) — không tính
    gì với nó ở hàm này.

    `buf_sl_he_so` = `tier_b.buf_sl_atr` (tunable #2), đọc từ
    `config/tool_d_config.yaml`; bắt buộc, không mặc định (TD-0195).

    `huong="long"` (mặc định) chạy đúng nhánh code cũ — hành vi không đổi
    một bit so với trước TD-0319.
    """
    if huong == "long":
        p1 = min(zone_high, gia_dong_cua)
        p3 = zone_low
        sl = sl_kieu_zone(
            zone_low=zone_low, atr_4h=atr_4h, buf_sl_he_so=buf_sl_he_so, huong="long"
        )
    elif huong == "short":
        p1 = max(zone_low, gia_dong_cua)
        p3 = zone_high
        sl = sl_kieu_zone(
            zone_low=zone_low, zone_high=zone_high, atr_4h=atr_4h,
            buf_sl_he_so=buf_sl_he_so, huong="short",
        )
    else:
        raise TradePlanError(f"huong không hợp lệ: {huong!r}")
    p2 = (zone_high + zone_low) / 2
    p_avg = (p1 + p2 + p3) / 3  # TRONG_SO_TRANCHE bằng nhau cả ba
    r_eff_plan = (p_avg - sl) / p_avg if huong == "long" else (sl - p_avg) / p_avg
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
