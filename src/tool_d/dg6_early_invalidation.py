"""DG6 — Early Invalidation (TD-0123, §4.1).

Bốn điều kiện, (A) HOẶC (B) HOẶC (C) HOẶC (D nếu SHORT) đúng → đóng
TOÀN BỘ vị thế bằng MARKET. Đây là nhóm ĐÓNG VỊ THẾ (cùng DG7/DG8),
kiểm tra LIÊN TỤC sau khi tranche 1 đã khớp — khác DG1-DG5 (gate kích
hoạt tranche mới).

Điều kiện A dùng lại đúng công thức `compression` (tỉ lệ ATR hiện tại /
ATR tại một mốc tham chiếu) đã có ở `zone_strength.py` — chỉ khác mốc
tham chiếu là lúc tranche 1 khớp, không phải lúc zone hình thành. Gọi
`zone_strength.compression(..., i_hinh_thanh=i_tranche1, i_hien_tai=i)`
ở tầng chiến lược, truyền kết quả vào `dieu_kien_a` ở đây — không viết
lại phép tính ATR.

════ TD-0320 (DR-SHORT-01) — `dieu_kien_d` nay đọc ngưỡng qua đối số ════

🔴 TD-0195 — `NGUONG_ATR_RATIO_A = 1.8` ĐÃ BỊ XOÁ: bản sao cứng của
`tier_b.dg6a_atr_ratio` (tunable #8). `dieu_kien_a()` nhận ngưỡng qua
đối số bắt buộc; người gọi đọc YAML. Xem chú thích cùng loại ở
`zone_strength.py`. Cùng cách vá nay áp cho `dieu_kien_d()`.

🔴 **Bẫy đơn vị, đã khai TRƯỚC khi vá (ghi nợ từ TD-0123), nay đóng:**
YAML ghi `tier_b.funding_rate_pct: -0.05` là PHẦN TRĂM; hằng số cũ
`NGUONG_FUNDING_D = -0.0005` ở đây là TỈ LỆ — cùng một số vật lý, khác
ĐƠN VỊ. `dieu_kien_d()` nhận `nguong_funding` qua đối số bắt buộc (cùng
khuôn `nguong_atr_ratio`); người gọi ở tầng chiến lược đọc
`resolve(cfg, "tier_b.funding_rate_pct") / 100` — CHIA 100 tường minh
tại đúng MỘT chỗ, không lặp phép chia ở nơi khác.

════ TD-0323 (DR-SHORT-01) — `dieu_kien_d` NAY CÓ NGƯỜI GỌI SẢN XUẤT ════

`ZoneAbsorption.custom_exit` (arm `Z3b`, chỉ SHORT) gọi `dieu_kien_d()` thay
cho `d=False` cứng. `NGUONG_HOI_GIA_D = 0.5` ĐÃ BỊ XOÁ — bản sao cứng của
`tier_b.dg6d_retrace_frac`, cùng lớp với `NGUONG_ATR_RATIO_A`/`NGUONG_FUNDING_D`
(TD-0195). Ngưỡng hồi giá nay đi qua đối số BẮT BUỘC `nguong_hoi_gia`; tầng
gọi đọc YAML (đã là tỉ lệ 0..1, KHÔNG chia 100 — khác `funding_rate_pct`).
"""

from __future__ import annotations

from typing import Literal, Sequence

Huong = Literal["long", "short"]

SO_NEN_TOI_THIEU_B = 8  # 🔒 = DG4, đóng băng
NGUONG_DECAY_C = 0.7


def dieu_kien_a(
    atr_ty_le: float, gia_hien_tai: float, *, p_avg: float, huong: Huong, nguong_atr_ratio: float
) -> bool:
    """Momentum đảo ngược: ATR giãn ≥ ngưỡng kể từ tranche 1 KHỚP, VÀ giá
    đang ở phía bất lợi so với `p_avg` hiện tại.

    `nguong_atr_ratio` = `tier_b.dg6a_atr_ratio` (tunable #8), đọc từ
    `config/tool_d_config.yaml`; bắt buộc, không mặc định (TD-0195).
    """
    bat_loi = gia_hien_tai < p_avg if huong == "long" else gia_hien_tai > p_avg
    return atr_ty_le >= nguong_atr_ratio and bat_loi


def dieu_kien_b(dong_tu_tranche1: Sequence[float], *, p1: float, so_nen_da_troi: int, huong: Huong) -> bool:
    """Hết cửa sổ hợp lý (≥8 nến 1H) mà giá CHƯA từng đóng cửa hồi
    lại qua `p1` — hấp thụ coi như hỏng."""
    if so_nen_da_troi < SO_NEN_TOI_THIEU_B:
        return False
    if huong == "long":
        da_hoi = any(c >= p1 for c in dong_tu_tranche1)
    else:
        da_hoi = any(c <= p1 for c in dong_tu_tranche1)
    return not da_hoi


def price_decay_ratio(*, p_avg: float, gia_hien_tai: float, sl: float, huong: Huong) -> float:
    """Tỉ lệ quãng đường đã đi từ `p_avg` tới `sl`. `sl` luôn xa `p_avg`
    hơn theo hướng bất lợi — mẫu số bằng 0 là dữ liệu sai, raise thay vì
    chia 0 âm thầm."""
    if huong == "long":
        mau_so = p_avg - sl
        if mau_so <= 0:
            raise ValueError("LONG yêu cầu sl < p_avg")
        return (p_avg - gia_hien_tai) / mau_so
    mau_so = sl - p_avg
    if mau_so <= 0:
        raise ValueError("SHORT yêu cầu sl > p_avg")
    return (gia_hien_tai - p_avg) / mau_so


def dieu_kien_c(ty_le_decay: float, trend_da_dao_hoac_mat_xac_nhan: bool) -> bool:
    """Đã đi ≥70% quãng đường tới SL VÀ bối cảnh xu hướng đã đổi."""
    return ty_le_decay >= NGUONG_DECAY_C and trend_da_dao_hoac_mat_xac_nhan


def ty_le_hoi_ve_p1(*, gia_vao: float, gia_hien_tai: float, p1: float) -> float:
    """Tỉ lệ quãng đường đã hồi từ giá vào lệnh (tranche gần nhất) về
    phía `p1`. Không bao giờ âm — đi ngược hướng `p1` không phải "hồi"."""
    quang_duong = abs(p1 - gia_vao)
    if quang_duong == 0:
        return 0.0
    da_di = (gia_hien_tai - gia_vao) if p1 > gia_vao else (gia_vao - gia_hien_tai)
    return max(0.0, da_di) / quang_duong


def dieu_kien_d(
    funding_rate_8h_gan_nhat: float,
    ty_le_hoi_p1: float,
    *,
    huong: Huong,
    nguong_funding: float,
    nguong_hoi_gia: float,
) -> bool:
    """CHỈ áp dụng cho SHORT — rủi ro short squeeze (§3.3d).

    `nguong_funding` = `tier_b.funding_rate_pct` (tunable #5) ĐÃ CHIA 100
    bởi tầng gọi — bắt buộc, không mặc định (TD-0320, cùng khuôn
    `nguong_atr_ratio` của `dieu_kien_a`). Xem cảnh báo đơn vị ở docstring
    module: truyền thẳng `-0.05` (chưa chia) thay vì `-0.0005` làm ngưỡng
    sai 100 lần mà không phép kiểm kiểu nào tự bắt được.

    `nguong_hoi_gia` = `tier_b.dg6d_retrace_frac` (tỉ lệ 0..1, KHÔNG chia
    100) — bắt buộc, không mặc định (TD-0323).
    """
    if huong != "short":
        return False
    return funding_rate_8h_gan_nhat < nguong_funding and ty_le_hoi_p1 > nguong_hoi_gia


def dg6_dong_vi_the(*, a: bool, b: bool, c: bool, d: bool) -> bool:
    """(A) HOẶC (B) HOẶC (C) HOẶC (D) — bất kỳ điều kiện nào đúng."""
    return a or b or c or d
