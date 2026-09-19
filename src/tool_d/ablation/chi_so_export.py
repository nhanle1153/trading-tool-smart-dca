"""`TD-0338` + `TD-0339` (`DR-D4-14`, `DR-D4-15`) — chỉ số Nhánh 1 và bằng chứng `DR-D4-04` §7 đọc THẲNG từ export.

Tầng THUẦN: nhận `KetQuaChay.lenh` (dict lệnh của export backtest Freqtrade, đã lọc bởi `doc_ket_qua.TRUONG_LENH`)
và/hoặc `LenhWFO` đã trích. Không đọc `custom_data` — export KHÔNG mang nó (đo 19/09/2026, `DR-D4-14` §10).

════ Mỗi số đọc từ đâu ════

| Khoá | Nguồn trong export | Căn cứ |
|---|---|---|
| `tp_fallback_ratio` | `orders[].ft_order_tag` của lần thoát từng phần TP1 | `ZoneAbsorption.py` `_xet_tp1` trả tag `TP1_<tp_source>`; cùng cách đếm `DR-D4-10` §1.5 |
| `time_stop_ratio` | `exit_reason == "TIME_STOP"` | `ZoneAbsorption.custom_exit` |
| `max_single_trade_loss_over_risk_budget` | `max(−pnl_abs / planned_risk_usdt)` | `planned_risk_usdt` suy ngược, `DR-D4-14` §10 |
| `trades_per_year` | số lệnh / năm phủ của cửa sổ QUAN SÁT | `MT-29`: sàn áp MỖI HƯỚNG — module này Long-only |
| `skewness_r_trien_khai` | skewness mẫu của `R_trien_khai` | MÔ TẢ (`DR-D9-02` §3.3), không chặn |
| `ti_trong_tranche_dat` | `orders[].cost` của lệnh đủ 3 tranche | tiền lệ `test_td0187::TestTiTrongTrancheThat` (±1%) |
| `stake_theo_r_eff_rho` | Spearman(notional tranche 1, `1/R_eff`) | mốc 0 tự nhiên — hằng số thì ρ không định nghĩa |
| `bat_bien_1_7_ty_so_trung_vi` | fill vs công thức ĐÚNG theo giá kế hoạch | `DR-D4-15` §2.1 |

🔴 Không số nào ở đây được bịa: không đo được ⇒ `unreadable` kèm lý do (N6). Tag TP1 lạ ⇒ raise (một tag mới mà
bộ đếm không biết là một TP1 bị đếm sót — đúng hình PASS RỖNG).
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from datetime import date
from statistics import median
from typing import Any

from tool_d.bo_chay.trich_lenh import TrichLenhError, doc_tag_long
from tool_d.config.loader import ToolDConfig
from tool_d.gates.thresholds import BAT_BIEN_1_7_DUNG_SAI
from tool_d.measurement.tri_state import Measured
from tool_d.sizing import doc_trong_so_tranche
from tool_d.take_profit import TP_SOURCE_NANG, TP_SOURCE_ZONE
from tool_d.wfo.lenh import LenhWFO

TAG_TP1_ZONE = f"TP1_{TP_SOURCE_ZONE}"
TAG_TP1_NANG = f"TP1_{TP_SOURCE_NANG}"
#: `ZoneAbsorption.custom_exit` trả đúng chuỗi này (`tool_d/time_stop.py` là nơi ra quyết định).
EXIT_TIME_STOP = "TIME_STOP"
#: Tiền lệ `test_td0187_dinh_co_lenh_backtest_that.py::TestTiTrongTrancheThat` — sai số làm tròn khối lượng.
DUNG_SAI_TI_TRONG = 0.01
SO_TRANCHE_DU = 3


class ChiSoExportError(ValueError):
    """Export mang thứ bộ đếm không hiểu. Fail-closed."""


def _vao_da_khop(t: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return sorted(
        (o for o in (t.get("orders") or ())
         if o.get("ft_is_entry") and o.get("order_filled_timestamp") and float(o.get("amount") or 0) > 0),
        key=lambda o: o["order_filled_timestamp"],
    )


def tp_fallback_ratio(lenh: Sequence[Mapping[str, Any]]) -> Measured[float]:
    """H-4 = số lần TP1 rơi nạng / số lần TP1 nổ (mẫu số = TP1 ĐÃ NỔ, cùng cách `DR-D4-10` §1.5)."""
    zone = nang = 0
    for t in lenh:
        for o in t.get("orders") or ():
            tag = str(o.get("ft_order_tag") or "")
            if o.get("ft_is_entry") or not tag.startswith("TP1_"):
                continue
            if tag == TAG_TP1_ZONE:
                zone += 1
            elif tag == TAG_TP1_NANG:
                nang += 1
            else:
                raise ChiSoExportError(f"tag TP1 lạ {tag!r} — hợp lệ: {TAG_TP1_ZONE}, {TAG_TP1_NANG}")
    if zone + nang == 0:
        return Measured.unreadable("0 lần TP1 nổ — H-4 không có mẫu số")
    return Measured.ok(nang / (zone + nang))


def time_stop_ratio(lenh: Sequence[Mapping[str, Any]]) -> Measured[float]:
    if not lenh:
        return Measured.unreadable("0 lệnh")
    return Measured.ok(sum(1 for t in lenh if t.get("exit_reason") == EXIT_TIME_STOP) / len(lenh))


def max_lo_don_lenh_tren_ngan_sach(lenhs: Sequence[LenhWFO]) -> Measured[float]:
    """`max(−pnl_abs / planned_risk_usdt)`, sàn 0: không lệnh lỗ nào ⇒ lỗ đơn lệnh lớn nhất ĐO ĐƯỢC là 0."""
    if not lenhs:
        return Measured.unreadable("0 lệnh")
    return Measured.ok(max(0.0, max(-l.pnl_abs / l.planned_risk_usdt for l in lenhs)))


def lenh_moi_nam(so_lenh: int, observed_start: date, observed_end: date) -> Measured[float]:
    ngay = (observed_end - observed_start).days + 1
    if ngay <= 0:
        return Measured.unreadable(f"cửa sổ quan sát rỗng [{observed_start}, {observed_end}]")
    return Measured.ok(so_lenh / (ngay / 365.25))


def skewness(xs: Sequence[float]) -> Measured[float]:
    """Skewness mẫu g1 = m3 / m2^1,5. MÔ TẢ."""
    n = len(xs)
    if n < 3:
        return Measured.unreadable(f"n = {n} < 3")
    m = math.fsum(xs) / n
    m2 = math.fsum((x - m) ** 2 for x in xs) / n
    if m2 == 0:
        return Measured.unreadable("phương sai 0 — skewness không định nghĩa")
    return Measured.ok(math.fsum((x - m) ** 3 for x in xs) / n / m2**1.5)


def ti_trong_tranche(lenh: Sequence[Mapping[str, Any]]) -> Measured[bool]:
    """`DR-D4-04` §7 (ii): ở MỌI lệnh đủ ba tranche, `cost_j / cost_1` ∈ [1 − 1%, 1 + 1%]."""
    du = [t for t in lenh if len(_vao_da_khop(t)) == SO_TRANCHE_DU]
    if not du:
        return Measured.unreadable("0 lệnh khớp đủ ba tranche")
    for t in du:
        cost = [float(o["amount"]) * float(o["safe_price"]) for o in _vao_da_khop(t)]
        if any(abs(c / cost[0] - 1.0) > DUNG_SAI_TI_TRONG for c in cost):
            return Measured.ok(False)
    return Measured.ok(True)


def _hang(xs: Sequence[float]) -> list[float]:
    thu_tu = sorted(range(len(xs)), key=xs.__getitem__)
    hang = [0.0] * len(xs)
    i = 0
    while i < len(thu_tu):
        j = i
        while j + 1 < len(thu_tu) and xs[thu_tu[j + 1]] == xs[thu_tu[i]]:
            j += 1
        for k in range(i, j + 1):
            hang[thu_tu[k]] = (i + j) / 2 + 1
        i = j + 1
    return hang


def spearman(xs: Sequence[float], ys: Sequence[float]) -> Measured[float]:
    if len(xs) != len(ys):
        raise ChiSoExportError("hai dãy khác độ dài")
    if len(xs) < 3:
        return Measured.unreadable(f"n = {len(xs)} < 3")
    rx, ry = _hang(xs), _hang(ys)
    mx, my = math.fsum(rx) / len(rx), math.fsum(ry) / len(ry)
    sx = math.fsum((a - mx) ** 2 for a in rx)
    sy = math.fsum((b - my) ** 2 for b in ry)
    if sx == 0 or sy == 0:
        return Measured.unreadable("một dãy hằng — tương quan không định nghĩa (stake HẰNG SỐ rơi vào đây)")
    return Measured.ok(math.fsum((a - mx) * (b - my) for a, b in zip(rx, ry)) / math.sqrt(sx * sy))


def stake_theo_r_eff(lenh: Sequence[Mapping[str, Any]]) -> Measured[float]:
    """`DR-D4-04` §7 (iii): ρ Spearman giữa notional tranche 1 và `1/R_eff`. Đạt ⇔ ρ > 0."""
    notional, nghich = [], []
    for t in lenh:
        vao = _vao_da_khop(t)
        if not vao:
            continue
        try:
            _, r_eff = doc_tag_long(t.get("enter_tag"))
        except TrichLenhError as exc:
            raise ChiSoExportError(f"{t.get('pair')}: {exc}") from exc
        notional.append(float(vao[0]["amount"]) * float(vao[0]["safe_price"]))
        nghich.append(1.0 / r_eff)
    return spearman(notional, nghich)


def bat_bien_1_7(lenh: Sequence[Mapping[str, Any]], *, cfg: ToolDConfig) -> Measured[float]:
    """`DR-D4-15` §2.1 — trung vị `D_fill / D_ke` trên lệnh khớp đủ ba tranche.

        D_fill = Σ amount_j · (fill_j − sl)
        D_ke   = N_full · Σ w_j · (p_j − sl) / p_j,   N_full = notional_tranche1 / w_1

    `N_full` là giá trị đã dùng để định cỡ (notional tranche 1 = `N_full · w_1`, `sizing.py:242`).
    """
    w = doc_trong_so_tranche(cfg)
    ty_so: list[float] = []
    for t in lenh:
        vao = _vao_da_khop(t)
        if len(vao) != SO_TRANCHE_DU:
            continue
        tag = json.loads(t["enter_tag"])
        sl, _ = doc_tag_long(t["enter_tag"])
        p = [float(tag["p1"]), float(tag["p2"]), float(tag["p3"])]
        n_full = float(vao[0]["amount"]) * float(vao[0]["safe_price"]) / w[0]
        d_ke = n_full * math.fsum(wj * (pj - sl) / pj for wj, pj in zip(w, p))
        d_fill = math.fsum(float(o["amount"]) * (float(o["safe_price"]) - sl) for o in vao)
        ty_so.append(d_fill / d_ke)
    if not ty_so:
        return Measured.unreadable("0 lệnh khớp đủ ba tranche — §1.7 không có gì để đo (DR-D4-15 §2.2)")
    return Measured.ok(median(ty_so))


def bat_bien_1_7_lech(m: Measured[float]) -> bool:
    """`DR-D4-15`: DỪNG ⇔ `|trung_vi − 1| > dung sai`. `unreadable` ⇒ KHÔNG dừng (không có gì để kết luận)."""
    return m.is_ok() and abs(float(m.value) - 1.0) > BAT_BIEN_1_7_DUNG_SAI


def chi_so_tu_export(
    *, lenh: Sequence[Mapping[str, Any]], lenhs: Sequence[LenhWFO], cfg: ToolDConfig,
    observed_start: date, observed_end: date,
) -> dict[str, Measured[Any]]:
    """Toàn bộ khoá thêm cho `chi_so` của bản ghi arm. Tên bốn khoá đầu TRÙNG `d9_gate.TIEU_CHI_KHAI`."""
    if any(t.get("is_short") is True for t in lenh):
        raise ChiSoExportError("có lệnh SHORT — D4 đợt này Long-only (DR-D4-01), sàn 150 áp mỗi hướng (MT-29)")
    return {
        "tp_fallback_ratio": tp_fallback_ratio(lenh),
        "time_stop_ratio": time_stop_ratio(lenh),
        "max_single_trade_loss_over_risk_budget": max_lo_don_lenh_tren_ngan_sach(lenhs),
        "trades_per_year": lenh_moi_nam(len(lenh), observed_start, observed_end),
        "skewness_r_trien_khai": skewness([l.r_trien_khai for l in lenhs]),
        "ti_trong_tranche_dat": ti_trong_tranche(lenh),
        "stake_theo_r_eff_rho": stake_theo_r_eff(lenh),
        "bat_bien_1_7_ty_so_trung_vi": bat_bien_1_7(lenh, cfg=cfg),
    }


__all__ = [
    "ChiSoExportError",
    "bat_bien_1_7",
    "bat_bien_1_7_lech",
    "chi_so_tu_export",
    "lenh_moi_nam",
    "max_lo_don_lenh_tren_ngan_sach",
    "skewness",
    "spearman",
    "stake_theo_r_eff",
    "ti_trong_tranche",
    "time_stop_ratio",
    "tp_fallback_ratio",
]
