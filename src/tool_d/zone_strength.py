"""Zone Strength Score (ZSS) — §1.2, ngưỡng nhận zone §1.3 (TD-0104).

Ba thành phần đo trên dữ liệu OHLCV thuần (§1.2): `touch_count` (định
nghĩa số LD-35 — "Cấp C, cùng loại với k, 0 bậc tự do", không phải một
ngưỡng để suy diễn), `volume_ratio`, `compression`. Trọng số `w_a=w_b=w_c
=1/3` ĐÓNG BĂNG theo spec — không có cơ chế tune nào ở đây.

🔴 Phạm vi CHƯA phủ ở module này: quy tắc "close < zone_low → zone bị phá
(DG1)" trong định nghĩa touch_count chỉ được thi hành ở MỨC KHÔNG TÍNH
TOUCH cho nến đó — phần "zone bị phá" là một gate riêng (§4, DG1), chưa
có code entrypoint/chiến lược nào ở D1 để nối vào, nên chưa hiện diện ở
đây. Sẽ nối khi DG1 được implement.
"""

from __future__ import annotations

from typing import Literal, Sequence

TRONG_SO_ZSS = 1 / 3  # w_a = w_b = w_c — ĐÓNG BĂNG (§1.2), không tune
NGUONG_TUOI_ZONE_TOI_DA = 40  # §1.3 — 40 nến 4H ~ 6.7 ngày

# 🔴 TD-0195 — `NGUONG_ZSS = 0.5` ĐÃ BỊ XOÁ khỏi đây, KHÔNG phải đổi tên.
# Nó là bản sao cứng của `tier_b.zss_threshold` (tunable #1, tính vào
# N = 114). Hai nguồn sự thật cho một con số, và vì hai giá trị đang
# BẰNG NHAU nên không phép kiểm nào báo đỏ — trong khi mọi trial B3
# calibrate khoá đó sẽ tiêu một suất thật để đo một thay đổi KHÔNG XẢY
# RA (`zone_hop_le` đọc hằng, không đọc YAML). Ngưỡng nay là đối số
# BẮT BUỘC; người gọi đọc `resolve(cfg, "tier_b.zss_threshold")`.
# KHÔNG đặt lại một mặc định ở đây: mặc định là chỗ để một đường gọi
# quên khai mà vẫn lặng lẽ chạy — đúng lý do `bat_dieu_kien_c` của
# `entry_confirmation` cũng không có mặc định.


def touch_count(
    gia_cham: Sequence[float],
    dong: Sequence[float],
    zone_low: float,
    zone_high: float,
    i_swing: int,
    t: int,
    *,
    loai: Literal["day", "dinh"],
) -> int:
    """§1.2(a) + LD-35 — đếm số CỤM chạm-rồi-bật-ra trong `(i_swing, t]`.

    `gia_cham` = giá dùng để phát hiện CHẠM (low cho zone đáy, high cho
    zone đỉnh). `dong` = giá đóng cửa, dùng để phát hiện BẬT RA. KHÔNG
    tính nến `i_swing` (đó là nến hình thành zone, không phải touch) và
    KHÔNG đọc gì sau `t` (point-in-time).

    Zone đáy (`loai="day"`): BẬT RA khi `dong > zone_high`; đóng cửa dưới
    `zone_low` không phải touch (§1.2: "zone bị phá", xem giới hạn phạm vi
    ở docstring module). Zone đỉnh (`loai="dinh"`) đảo dấu cả hai chiều.
    """
    dem = 0
    dang_trong_cum = False
    for j in range(i_swing + 1, t + 1):
        cham = zone_low <= gia_cham[j] <= zone_high
        if loai == "day":
            bat_ra = dong[j] > zone_high
            vo_huong_nguoc = dong[j] < zone_low
        else:
            bat_ra = dong[j] < zone_low
            vo_huong_nguoc = dong[j] > zone_high

        if dang_trong_cum:
            if bat_ra:
                dem += 1
                dang_trong_cum = False
            elif vo_huong_nguoc:
                # TD-0107: vỡ NGƯỢC HƯỚNG giữa lúc đang chờ bật ra — cụm
                # coi như đã hỏng, không được tính dù sau đó có bật ra.
                dang_trong_cum = False
            # còn lại: vẫn kẹt trong zone, cụm tiếp tục chờ nến sau
            continue

        if not cham:
            continue
        if bat_ra:
            dem += 1
        elif vo_huong_nguoc:
            pass  # không phải touch — "zone bị phá" (DG1, ngoài phạm vi module này)
        else:
            dang_trong_cum = True
    return dem


def volume_ratio(volume: Sequence[float], i_swing: int, *, period: int = 20) -> float | None:
    """§1.2(b) — `volume(nến swing) / volume_MA(period, 4H)`.

    `None` nếu chưa đủ `period` nến TRƯỚC VÀ TẠI `i_swing` để tính MA
    (point-in-time — không lùi ra ngoài lịch sử có thật).
    """
    if i_swing - (period - 1) < 0:
        return None
    cua_so = volume[i_swing - (period - 1) : i_swing + 1]
    ma = sum(cua_so) / period
    if ma == 0:
        return None
    return volume[i_swing] / ma


def compression(
    cao: Sequence[float],
    thap: Sequence[float],
    dong: Sequence[float],
    *,
    i_hinh_thanh: int,
    i_hien_tai: int,
    period: int = 14,
) -> float | None:
    """§1.2(c) — `ATR(period,4H)_hiện_tại / ATR(period,4H)_lúc_hình_thành_zone`.

    Dùng TA-Lib (đã có sẵn trong ảnh Freqtrade — không tự viết lại ATR).
    `None` nếu một trong hai điểm chưa đủ dữ liệu cho ATR (NaN).
    """
    import numpy as np
    import talib

    atr = talib.ATR(
        np.asarray(cao, dtype=float), np.asarray(thap, dtype=float), np.asarray(dong, dtype=float), timeperiod=period
    )
    atr_hinh_thanh = atr[i_hinh_thanh]
    atr_hien_tai = atr[i_hien_tai]
    if np.isnan(atr_hinh_thanh) or np.isnan(atr_hien_tai) or atr_hinh_thanh == 0:
        return None
    return float(atr_hien_tai / atr_hinh_thanh)


def zss(*, touch: int, ty_le_volume: float, do_nen: float) -> float:
    """§1.2 — công thức ZSS, trọng số đóng băng `TRONG_SO_ZSS`."""
    thanh_phan_touch = min(touch, 3) / 3
    thanh_phan_volume = _kep(ty_le_volume, 0, 2) / 2
    thanh_phan_nen = _kep(2 - do_nen, 0, 2) / 2
    return TRONG_SO_ZSS * (thanh_phan_touch + thanh_phan_volume + thanh_phan_nen)


def _kep(x: float, thap: float, cao: float) -> float:
    return max(thap, min(cao, x))


def zone_hop_le(*, zss_value: float, so_touch: int, tuoi_nen: int, nguong_zss: float) -> bool:
    """§1.3 — ba điều kiện nhận zone, TẤT CẢ phải đạt.

    `nguong_zss` = `tier_b.zss_threshold` (tunable #1), đọc từ
    `config/tool_d_config.yaml` — N4 cấm hardcode. Tham số **bắt buộc,
    không mặc định** (TD-0195): xem chú thích ở đầu module.

    `NGUONG_TUOI_ZONE_TOI_DA` thì KHÁC — nó không nằm trong `tier_b`,
    không phải bậc tự do nào trong kiểm kê DOF, nên giữ là hằng số ở đây
    là đúng chỗ. Phân biệt: *"khoá này có trong `tier_b` không?"* —
    cùng câu hỏi đã dùng để phân biệt DG5 với `v_min` (DR-D4-02 vs
    DR-D4-03).
    """
    if nguong_zss != nguong_zss:  # NaN
        raise ValueError("nguong_zss là NaN — 'không đọc được' KHÁC 'zone không hợp lệ'")
    return zss_value >= nguong_zss and so_touch >= 1 and tuoi_nen <= NGUONG_TUOI_ZONE_TOI_DA
