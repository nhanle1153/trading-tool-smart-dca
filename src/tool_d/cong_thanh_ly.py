"""`TD-0364` (`MT-69`) — cổng §6.4 `L-Z3` trên đường VÀO LỆNH: từ chối mở khi đệm thanh lý mỏng.

Spec `:1866-1871`:

    🚪 GATE §6.4:  liq_buffer_ratio ≥ 8  tại thời điểm xét tranche 1
                   không thoả → TỪ CHỐI mở, bất kể ZSS cao thế nào
    🔒 Ngưỡng 8: CẤP C, khoá vĩnh viễn, KHÔNG tune, KHÔNG tính vào N.

Trước `TD-0364`, `liq_buffer_ratio` **chỉ tồn tại ở tầng ĐO** (`ablation/`, `gates/thresholds.py`) — tức Nhánh 1
báo được *"đệm trung bình"* nhưng **không có gì chặn** một lệnh đệm mỏng lúc mở. Đó là `MT-69`. Đo `TD-0363`
(EXPLORE CALIB, 0 suất): 7,3–9,4% số lệnh có tỉ số < 8, min 4,86 — trung bình 18,31 **không** nói lên được điều
đó, đuôi mới là chỗ thanh lý xảy ra.

🔴 Vì sao module này KHÔNG chứa công thức: công thức nằm ở `ablation/thanh_ly.liq_buffer_ke_hoach()` (`TD-0348`,
`DR-D4-17`) và phải có **đúng một nguồn** (N1/`MT-03`). Ở đây chỉ có phần *quyết định*: so với ngưỡng, và biến
mọi ca "không tính được" thành TỪ CHỐI.

🔴 Fail-closed, ba ca đều TỪ CHỐI và đều nói ra lý do:
  1. `tinh_liq` trả `None` (cặp không có bảng bậc đòn bẩy) — không biết giá thanh lý thì không biết đệm dày mỏng;
  2. `ThanhLyError` (kế hoạch không hợp lệ: `sl ≥ p_avg_plan`, trọng số lệch, giá âm);
  3. tỉ số < ngưỡng.
Không ca nào được trả một con số thay thế (N6: cấm `0.0`, cấm giá trị lính canh). Im lặng cho qua ở đây nghĩa là
một vị thế có thể bị thanh lý trước khi chạm SL, trên tiền thật.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from tool_d.ablation.thanh_ly import DemThanhLy, HamThanhLy, ThanhLyError, liq_buffer_ke_hoach

#: Mã phép kiểm trong spec — nhắc trong mọi dòng log để phép từ chối truy ngược được.
MA_CONG = "L-Z3"


@dataclass(frozen=True)
class KetQuaCong:
    """`qua=False` ⇒ KHÔNG được mở/bơm thêm. `dem` là `None` khi không tính được (không phải "bằng 0")."""

    qua: bool
    dem: DemThanhLy | None
    ly_do: str  # rỗng ⇔ qua


def xet_cong_l_z3(
    *,
    pair: str,
    p: Sequence[float],
    sl: float,
    w: Sequence[float],
    n_full: float,
    don_bay: float,
    ham: HamThanhLy | None,
    nguong: float,
    tranche: int,
    la_short: bool = False,
) -> KetQuaCong:
    """Xét cổng trên **kế hoạch đủ ba tranche** (spec `:1857`), không phải trên phần đã khớp.

    `ham is None` ⇒ TỪ CHỐI: không có đường tính giá thanh lý thì cổng không được coi là đã qua.
    """
    if ham is None:
        return KetQuaCong(False, None, f"{MA_CONG}: không dựng được hàm giá thanh lý")
    try:
        dem = liq_buffer_ke_hoach(
            pair=pair, p=p, sl=sl, w=w, n_full=n_full, don_bay=don_bay,
            liquidation_buffer=ham.liquidation_buffer, tinh_liq=ham.tinh, la_short=la_short,
        )
    except ThanhLyError as e:
        return KetQuaCong(False, None, f"{MA_CONG}: kế hoạch không tính được tỉ số — {e}")
    if dem is None:
        return KetQuaCong(False, None, f"{MA_CONG}: {pair} không có trong bảng bậc đòn bẩy")
    if not math.isfinite(dem.ty_so) or dem.ty_so < nguong:
        return KetQuaCong(False, dem, ly_do_tu_choi(pair, dem=dem, nguong=nguong, tranche=tranche))
    return KetQuaCong(True, dem, "")


def ly_do_tu_choi(pair: str, *, dem: DemThanhLy, nguong: float, tranche: int) -> str:
    """Một dòng log ĐẾM ĐƯỢC, mang **cả tử và mẫu** — spec `:1885` điểm 2: *"không có hai số đầu thì L-Z3 fail
    mà không biết fail vì đâu"*. Khuôn tên giống `POST_ONLY_TU_CHOI` để cùng một kiểu grep."""
    return (
        f"LIQ_BUFFER_TU_CHOI {pair} tranche={tranche} ty_so={dem.ty_so:.4f} nguong={nguong:.4g} "
        f"liq_dist_pct={dem.liq_dist_pct:.6g} r_eff_pct={dem.r_eff_pct:.6g} "
        f"p_avg_plan={dem.p_avg_plan:.10g} liq_price={dem.liq_price:.10g} ({MA_CONG}, §6.4)"
    )


def de_ghi_so(dem: DemThanhLy | None) -> dict | None:
    """Ba số bắt buộc cho Decision Log (spec `:1880-1888`), kèm hai giá để truy ngược. `None` giữ nguyên `None`:
    chưa đo được thì để trống, không điền `0.0` (N6)."""
    if dem is None:
        return None
    return {
        "liq_buffer_ratio": dem.ty_so,
        "liq_dist_pct": dem.liq_dist_pct,
        "r_eff_pct": dem.r_eff_pct,
        "p_avg_plan": dem.p_avg_plan,
        "liq_price": dem.liq_price,
        "liq_price_tho": dem.liq_price_tho,
    }


__all__ = ["MA_CONG", "KetQuaCong", "de_ghi_so", "ly_do_tu_choi", "xet_cong_l_z3"]
