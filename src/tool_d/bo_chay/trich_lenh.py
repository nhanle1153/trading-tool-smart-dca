"""`TD-0333` (`DR-D4-14`) — một lệnh trong export backtest Freqtrade → `LenhWFO`.

`wfo/lenh.py:9-14` tự khai nó THUẦN và chỉ mang CÔNG THỨC `DR-D4-12` §1.4; đường đọc
fill thật *"là việc của lõi bộ chạy dùng chung"*. Trước file này, đường đó chỉ có ở
một kịch bản đo (`docs/du-lieu-do/do_td0291_song_con_explore.py:109` `_r_trien_khai`)
— ngoài `src/`, không test, không ai gọi lại được. Đây là bản đưa vào lõi.

════ Hai vế rủi ro, hai nguồn — đọc kỹ trước khi sửa ════

* **`rui_ro_da_trien_khai_usdt`** (mẫu số của `R_trien_khai`, đơn vị phán quyết `DR-D4-12` §1) — đọc
  THẲNG từ fill: mỗi tranche đã khớp mang `amount × safe_price` và giá khớp thật, `sl`
  từ `enter_tag`. Không suy gì cả.
* **`planned_risk_usdt`** (mẫu số của `R_realized`, và của `ty_le_rui_ro_da_trien_khai`
  mà `arm_record.CHI_SO_BAT_BUOC` đòi) — **SUY NGƯỢC**. 🔴 Đo 19/09/2026 trong image:
  Freqtrade 2026.8 `LocalTrade.to_json` **không** xuất `custom_data`, nên `co_lenh`
  (nơi chiến lược cất `planned_risk_usdt`, `ZoneAbsorption.py:1204`) **không có trong
  export**. Chủ dự án chốt (`DR-D4-14` §10): dùng lại đúng hàm chiến lược dùng khi
  restart — `sizing.phuc_hoi_ke_hoach_sau_restart()` (MT-41) — từ `R_eff` của
  `enter_tag` + ký quỹ tranche 1 ĐÃ KHỚP. Không phải đường thứ hai: chiến lược sống
  sót qua restart bằng CHÍNH phép suy này.

⚠️ **Sai số đã biết, khai ra:** ký quỹ tranche 1 khớp thật đã bị làm tròn theo bước
khối lượng của sàn, nên `planned_risk_usdt` suy ngược lệch kế hoạch gốc đúng bằng phần
làm tròn đó. Không có sai số nào khác trong phép suy (`sizing.py` docstring).

🔴 **LONG-only.** `rui_ro_da_trien_khai_usdt` là công thức LONG, và D4 đợt này
Long-only (`DR-D4-01`). Lệnh Short ⇒ TỪ CHỐI, không lật dấu hộ.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from tool_d.bo_chay.yeu_cau import BoChayError
from tool_d.config.loader import ToolDConfig, resolve
from tool_d.sizing import SizingError, phuc_hoi_ke_hoach_sau_restart
from tool_d.wfo.lenh import LenhWFO, LenhWFOError, TrancheKhop, rui_ro_da_trien_khai_usdt

#: Bốn khoá `enter_tag` mà phép tính ở đây thật sự đọc. Tập con của
#: `ZoneAbsorption._KHOA_JSON` — không chép cả tập vì các khoá kia không dùng ở đây.
KHOA_TAG_CAN = ("p1", "p2", "p3", "sl")

#: Khoá hướng của tag (`ZoneAbsorption._KHOA_HUONG`, TD-0321): chỉ SHORT mang nó.
_KHOA_HUONG = "h"

#: Đòn bẩy của lệnh lệch `tier_a.L_exchange` quá mức này ⇒ phép suy `n_full` sai.
_DUNG_SAI_DON_BAY = 1e-9


class TrichLenhError(BoChayError):
    """Một lệnh không trích được đủ tin để đem vào bản ghi arm. Fail-closed."""


def _ngay_utc(ten: str, gia_tri: Any) -> datetime:
    """Chuỗi ngày của export (`'2025-07-01 00:00:00+00:00'`) → UTC không múi giờ,
    đúng quy ước `LenhWFO`."""
    if not isinstance(gia_tri, str) or not gia_tri:
        raise TrichLenhError(f"`{ten}` = {gia_tri!r} không phải chuỗi ngày")
    try:
        d = datetime.fromisoformat(gia_tri)
    except ValueError as exc:
        raise TrichLenhError(f"`{ten}` = {gia_tri!r} không đọc được: {exc}") from exc
    if d.tzinfo is not None:
        d = d.astimezone(timezone.utc).replace(tzinfo=None)
    return d


def _so_duong(ten: str, gia_tri: Any) -> float:
    try:
        v = float(gia_tri)
    except (TypeError, ValueError) as exc:
        raise TrichLenhError(f"`{ten}` = {gia_tri!r} không phải số") from exc
    if not math.isfinite(v) or v <= 0:
        raise TrichLenhError(f"`{ten}` = {gia_tri!r} phải là số hữu hạn > 0")
    return v


def doc_tag_long(tag: Any) -> tuple[float, float]:
    """`enter_tag` → `(sl, r_eff_plan)` của một lệnh LONG.

    `r_eff_plan = (p_avg − sl) / p_avg`, `p_avg = (p1 + p2 + p3) / 3` — cùng công thức
    `ZoneAbsorption._giai_ma` và `trade_plan.tinh_ke_hoach` (`:157`). Test khoá
    `TD-0333` đối chiếu từng bit với `_giai_ma` để hai chỗ không trôi lệch.
    """
    if not isinstance(tag, str) or not tag:
        raise TrichLenhError(f"enter_tag rỗng hoặc không phải chuỗi: {tag!r}")
    try:
        d = json.loads(tag)
    except ValueError as exc:
        raise TrichLenhError(f"enter_tag không phải JSON: {tag!r}") from exc
    if not isinstance(d, dict):
        raise TrichLenhError(f"enter_tag không phải object JSON: {tag!r}")
    if d.get(_KHOA_HUONG) is not None:
        raise TrichLenhError(
            f"enter_tag mang khoá hướng {_KHOA_HUONG!r}={d[_KHOA_HUONG]!r} — lệnh SHORT; "
            "D4 đợt này Long-only (DR-D4-01), không lật dấu hộ"
        )
    thieu = [k for k in KHOA_TAG_CAN if k not in d]
    if thieu:
        raise TrichLenhError(f"enter_tag thiếu {thieu}: {tag!r}")
    p1, p2, p3, sl = (_so_duong(k, d[k]) for k in KHOA_TAG_CAN)
    p_avg = (p1 + p2 + p3) / 3
    r_eff = (p_avg - sl) / p_avg
    if r_eff <= 0:
        raise TrichLenhError(f"R_eff = {r_eff} ≤ 0 (sl {sl} ≥ p_avg {p_avg}) — kế hoạch LONG hỏng")
    return sl, r_eff


def lenh_tu_freqtrade(t: Mapping[str, Any], *, cfg: ToolDConfig, arm: str) -> LenhWFO:
    """Một phần tử `KetQuaChay.lenh` → `LenhWFO`. Mọi nhánh hỏng đều raise.

    `cfg` phải là cấu hình PHỦ của chính lượt chạy (`MoiTruongChay.cfg_phu`), không
    phải file trong repo — `L_exchange`/`w_tranche` của lượt chạy mới là thứ đã định cỡ.
    """
    cap = t.get("pair")
    if not isinstance(cap, str) or not cap:
        raise TrichLenhError(f"lệnh không có `pair`: {dict(t)!r}")
    nhan = f"{cap} {t.get('open_date')}"
    if t.get("is_short") is True:
        raise TrichLenhError(f"{nhan}: lệnh SHORT — D4 đợt này Long-only (DR-D4-01)")
    if "profit_abs" not in t:
        raise TrichLenhError(f"{nhan}: thiếu `profit_abs` (DR-013)")

    sl, r_eff = doc_tag_long(t.get("enter_tag"))

    khop = sorted(
        (
            o
            for o in (t.get("orders") or ())
            if o.get("ft_is_entry") and o.get("order_filled_timestamp") and float(o.get("amount") or 0) > 0
        ),
        key=lambda o: o["order_filled_timestamp"],
    )
    if not khop:
        raise TrichLenhError(f"{nhan}: không có tranche nào đã khớp")
    tranches = [
        TrancheKhop(
            stake_usdt=_so_duong("amount", o["amount"]) * _so_duong("safe_price", o["safe_price"]),
            entry=_so_duong("safe_price", o["safe_price"]),
        )
        for o in khop
    ]

    don_bay = _so_duong("leverage", t.get("leverage"))
    l_exchange = float(resolve(cfg, "tier_a.L_exchange"))
    if abs(don_bay - l_exchange) > _DUNG_SAI_DON_BAY:
        raise TrichLenhError(
            f"{nhan}: đòn bẩy lệnh {don_bay} ≠ tier_a.L_exchange {l_exchange} — phép suy "
            "`n_full = ký_quỹ × L / w[0]` chỉ đúng khi hai số này bằng nhau"
        )
    ky_quy_t1 = tranches[0].stake_usdt / don_bay

    try:
        rui_ro = rui_ro_da_trien_khai_usdt(tranches, sl=sl)
        ke_hoach = phuc_hoi_ke_hoach_sau_restart(
            cfg=cfg, arm=arm, r_eff=r_eff, stake_tranche1_da_khop=ky_quy_t1
        )
        return LenhWFO(
            pair=cap,
            open_date=_ngay_utc("open_date", t.get("open_date")),
            close_date=_ngay_utc("close_date", t.get("close_date")),
            pnl_abs=float(t["profit_abs"]),
            rui_ro_da_trien_khai_usdt=rui_ro,
            planned_risk_usdt=ke_hoach.planned_risk_usdt,
        )
    except (LenhWFOError, SizingError, TypeError, ValueError) as exc:
        raise TrichLenhError(f"{nhan}: {exc}") from exc


__all__ = ["KHOA_TAG_CAN", "TrichLenhError", "doc_tag_long", "lenh_tu_freqtrade"]
