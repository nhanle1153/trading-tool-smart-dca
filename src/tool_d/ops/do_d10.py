"""TD-0413 (`DR-D10-02` §6.1, `MT-87`) — bộ đo D10 cho ứng viên IQ-0003 `RoFunding`, và ghi kết cục vào dòng CTRL đợt D10.

Phép đo (bản gốc ở DR, file này thi hành — N1):
- **Trượt giá** (`DR-D0-IQ0003` §13 (b)): trung bình |giá khớp − giá mở nến 1H của lần cân rổ| / giá mở nến, trên MỌI lệnh
  vào/ra (không tính lệnh stop) của đợt, **≤ 0,05%**.
- **SL thảm hoạ sống trên sàn** (`DR-D10-02` §6.1): mọi vị thế phải có ít nhất một lệnh `stoploss` trong DB live.
- `gap_ms` và tỉ lệ khớp post-only: **N/A** có lý do (nguyên tắc `MT-43` — không DCA, lệnh thị trường), không phải 0 (N6).
- Đủ mẫu = ≥ 30 lệnh VÀ ≥ 7 lần cân rổ (`DR-D10-02` §6.3 Q8, cùng hằng với máy canh `ngan_sach_d10_ro`).

Kết cục (sổ trial chỉ nhận ba giá trị): `KEPT` = D10 đạt · `REJECTED` = trượt giá vượt ngưỡng hoặc có vị thế thiếu stop ·
`INCONCLUSIVE` = thiếu mẫu, hoặc có lệnh không đọc được giá mở nến (không đoán — N6). Chi tiết từng lệnh ghi ra hiện vật
(đầu ra đúng danh sách cho phép `CTRL_VAN_HANH_ALLOWED`: `fill_price`, `p_i` = giá mở nến, `order_status`, `gap_ms` = N/A).
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from tool_d.ops.ngan_sach_d10_ro import DU_LAN_CAN_RO, DU_LENH_KHOP

NGUONG_TRUOT_GIA = 0.0005  # DR-D0-IQ0003 §13 (b): 0,05% — bằng một lần phí taker Binance
LY_DO_NA_GAP_MS = "N/A — RoFunding không DCA ⇒ khối lượng SL không bao giờ đổi (DR-D10-02 §6.1, nguyên tắc MT-43)"
LY_DO_NA_POST_ONLY = "N/A — RoFunding dùng lệnh thị trường, không post-only (DR-D10-02 §6.1)"


def gio_can_ro(moc: datetime) -> datetime:
    """Mốc nến 1H chứa lần khớp — UTC-aware, cắt về đầu giờ (SQLite trả không múi giờ, bài học TD-0403)."""
    moc = moc.replace(tzinfo=timezone.utc) if moc.tzinfo is None else moc.astimezone(timezone.utc)
    return moc.replace(minute=0, second=0, microsecond=0)


@dataclass(frozen=True)
class LenhKhop:
    trade_id: int
    pair: str
    side: str
    khop_luc: datetime
    gia_khop: float
    trang_thai: str


@dataclass(frozen=True)
class ViTheD10:
    trade_id: int
    pair: str
    co_lenh_stop: bool


@dataclass(frozen=True)
class KetQuaD10:
    so_lenh: int
    so_lan_can_ro: int
    truot_gia_tb: float | None
    truot_gia_max: float | None
    so_lenh_thieu_gia: int
    vi_the_thieu_stop: tuple[int, ...]
    verdict: str
    ly_do: tuple[str, ...]
    chi_tiet: tuple[dict[str, Any], ...] = field(default_factory=tuple)

    def ra_dict(self) -> dict[str, Any]:
        return {
            "nguon": "TD-0413 — DR-D10-02 §6.1, DR-D0-IQ0003 §13 (b)",
            "nguong_truot_gia": NGUONG_TRUOT_GIA,
            "so_lenh": self.so_lenh,
            "so_lan_can_ro": self.so_lan_can_ro,
            "truot_gia_tb": self.truot_gia_tb,
            "truot_gia_max": self.truot_gia_max,
            "so_lenh_thieu_gia": self.so_lenh_thieu_gia,
            "vi_the_thieu_stop": list(self.vi_the_thieu_stop),
            "gap_ms": LY_DO_NA_GAP_MS,
            "ty_le_khop_post_only": LY_DO_NA_POST_ONLY,
            "verdict": self.verdict,
            "ly_do": list(self.ly_do),
            "chi_tiet": list(self.chi_tiet),
        }


def danh_gia(
    lenh: Iterable[LenhKhop],
    gia_mo_nen: Mapping[tuple[str, datetime], float],
    vi_the: Iterable[ViTheD10],
) -> KetQuaD10:
    """Phán quyết thuần. `gia_mo_nen[(pair, gio_can_ro)]` = giá MỞ nến 1H; thiếu hoặc hỏng ⇒ lệnh đó "thiếu giá"."""
    ds = [x for x in lenh if x.side != "stoploss"]
    truot: list[float] = []
    chi_tiet: list[dict[str, Any]] = []
    thieu_gia = 0
    for x in ds:
        gio = gio_can_ro(x.khop_luc)
        mo = gia_mo_nen.get((x.pair, gio))
        hong = mo is None or not math.isfinite(mo) or mo <= 0 or not math.isfinite(x.gia_khop) or x.gia_khop <= 0
        tg = None if hong else abs(x.gia_khop - mo) / mo
        if tg is None:
            thieu_gia += 1
        else:
            truot.append(tg)
        chi_tiet.append({"trade_id": x.trade_id, "pair": x.pair, "side": x.side, "gio_can_ro": gio.isoformat(),
                         "fill_price": x.gia_khop, "p_i": mo, "order_status": x.trang_thai, "truot_gia": tg})
    lan_can_ro = {gio_can_ro(x.khop_luc) for x in ds}
    thieu_stop = tuple(sorted(v.trade_id for v in vi_the if not v.co_lenh_stop))
    tb = sum(truot) / len(truot) if truot else None

    ly_do: list[str] = []
    if thieu_stop:
        ly_do.append(f"vị thế thiếu lệnh SL trên sàn: {list(thieu_stop)} (DR-D10-02 §6.1)")
    if tb is not None and tb > NGUONG_TRUOT_GIA:
        ly_do.append(f"trượt giá trung bình {tb:.5%} > {NGUONG_TRUOT_GIA:.2%} (DR-D0-IQ0003 §13 b)")
    if ly_do:
        verdict = "REJECTED"
    else:
        if len(ds) < DU_LENH_KHOP or len(lan_can_ro) < DU_LAN_CAN_RO:
            ly_do.append(f"thiếu mẫu: {len(ds)} lệnh (cần ≥ {DU_LENH_KHOP}), {len(lan_can_ro)} lần cân rổ "
                         f"(cần ≥ {DU_LAN_CAN_RO}) — D10 chưa đạt (DR-D10-02 Q5)")
        if thieu_gia:
            ly_do.append(f"{thieu_gia} lệnh không đọc được giá mở nến 1H — không đoán (N6)")
        verdict = "INCONCLUSIVE" if ly_do else "KEPT"
    return KetQuaD10(
        so_lenh=len(ds),
        so_lan_can_ro=len(lan_can_ro),
        truot_gia_tb=tb,
        truot_gia_max=max(truot) if truot else None,
        so_lenh_thieu_gia=thieu_gia,
        vi_the_thieu_stop=thieu_stop,
        verdict=verdict,
        ly_do=tuple(ly_do),
        chi_tiet=tuple(chi_tiet),
    )


def ket_cuc_so_trial(kq: KetQuaD10) -> dict[str, Any]:
    """`outcome` của sự kiện CONSUME — schema sổ chỉ nhận bốn khoá; D10 đo MÁY nên không có kỳ vọng / Sharpe / lỗ lớn nhất.
    Chi tiết nằm ở hiện vật (`seal_path`)."""
    return {"expectancy": None, "sharpe": None, "n_trades": kq.so_lenh, "max_single_loss_ratio": None}
