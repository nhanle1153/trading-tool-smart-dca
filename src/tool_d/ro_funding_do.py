"""TD-0408 — bộ đo LỢI SUẤT NGÀY của rổ funding `IQ-0003` (`DR-D0-IQ0003` §13 (a), §14). Tầng THUẦN.

Luật (viết TRƯỚC khi chạy suất, chủ dự án chốt 25/09/2026):
  • một quan sát = một ngày lịch UTC, từ ngày của lần cân rổ ĐẦU TIÊN có lệnh mở tới ngày cuối cửa sổ `[tu, den)`;
  • lợi suất ngày = Σ `profit_abs` (DR-013 — đã trừ phí + funding) các lệnh ĐÓNG trong ngày / `von_ro_usdt`;
  • ngày không đóng lệnh nào = 0 (lãi/lỗ ĐÃ CHỐT theo ngày đóng — không định giá lại vị thế đang mở);
  • chỉ số: `n`, `mean`, `std` (mẫu), `h = √(2·ln N)`, `mean − h·std/√n` (cùng công thức `gates.dsr`, đơn vị khác R_realized);
  • lệnh đóng ĐÚNG tại biên `den` (00:00 — Freqtrade `force_exit` khi hết cửa sổ) thuộc NGÀY CUỐI cửa sổ
    (đo được ở TD-0408 trên backtest thật; viết vào `DR-D0-IQ0003` §14 trước suất).
Kèm, CHỈ GHI, không phán quyết: funding nhận ròng + tỉ phần trong lãi ròng (điều 4 `nguong_bac_bo`), tách chân
Long/Short, số lệnh theo nhãn thoát.

N6: lệnh thiếu trường ⇒ raise, không coi là 0; 0 lệnh ⇒ chỉ số `None`, không `0.0`.
"""

from __future__ import annotations

import math
import statistics
from collections import Counter
from collections.abc import Iterable, Mapping
from datetime import date, datetime, timedelta, timezone
from typing import Any

from tool_d.gates.dsr import dsr_adjusted_expectancy, dsr_hurdle

TRUONG_BAT_BUOC = ("open_date", "close_date", "profit_abs", "is_short", "funding_fees", "exit_reason")
DON_VI = "loi_suat_ngay_tren_von_ro (không phải R_realized)"


class RoFundingDoError(ValueError):
    """Không đo được — TỪ CHỐI, không đoán (N6)."""


def _ngay(gia_tri: Any) -> date:
    """Ngày UTC của một mốc thời gian lệnh (chuỗi ISO, số mili-giây, hay `datetime`)."""
    if isinstance(gia_tri, datetime):
        dt = gia_tri
    elif isinstance(gia_tri, (int, float)) and not isinstance(gia_tri, bool):
        dt = datetime.fromtimestamp(gia_tri / 1000, tz=timezone.utc)
    elif isinstance(gia_tri, str):
        dt = datetime.fromisoformat(gia_tri.replace("Z", "+00:00"))
    else:
        raise RoFundingDoError(f"mốc thời gian không đọc được: {gia_tri!r}")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).date()


def do_loi_suat_ngay(
    lenh: Iterable[Mapping[str, Any]], *, von_usdt: float, tu: date, den: date, n_trials: int
) -> dict[str, Any]:
    """Chuỗi lợi suất ngày + chỉ số §14. `den` là biên MỞ (ngày cuối cửa sổ = `den − 1 ngày`)."""
    if not (isinstance(von_usdt, (int, float)) and von_usdt > 0):
        raise RoFundingDoError(f"von_usdt phải > 0, nhận {von_usdt!r}")
    if not tu < den:
        raise RoFundingDoError(f"cửa sổ rỗng [{tu}, {den})")
    ds = list(lenh)
    for i, t in enumerate(ds):
        thieu = [k for k in TRUONG_BAT_BUOC if k not in t or t[k] is None]
        if thieu:
            raise RoFundingDoError(f"lệnh #{i} ({t.get('pair')}) thiếu trường {thieu}")
    ngay_cuoi = den - timedelta(days=1)
    kq: dict[str, Any] = {"don_vi": DON_VI, "von_usdt": von_usdt, "cua_so": [tu.isoformat(), den.isoformat()],
                          "n_trials": n_trials, "so_lenh": len(ds)}
    if not ds:
        kq.update(n_ngay=0, mean=None, std=None, h=None, can_duoi=None, chuoi_ngay={})
        return kq

    ngay_dau = min(_ngay(t["open_date"]) for t in ds)
    if ngay_dau < tu:
        raise RoFundingDoError(f"lệnh mở {ngay_dau} trước cửa sổ {tu}")
    pnl_theo_ngay: Counter[date] = Counter()
    for t in ds:
        d = _ngay(t["close_date"])
        if d == den:
            d = ngay_cuoi  # biên mở của cửa sổ = mốc đóng cưỡng bức khi hết dữ liệu (xem docstring)
        if not ngay_dau <= d <= ngay_cuoi:
            raise RoFundingDoError(f"lệnh {t.get('pair')} đóng {d} ngoài [{ngay_dau}, {ngay_cuoi}]")
        pnl_theo_ngay[d] += float(t["profit_abs"])
    so_ngay = (ngay_cuoi - ngay_dau).days + 1
    chuoi = {(ngay_dau + timedelta(days=k)).isoformat(): pnl_theo_ngay.get(ngay_dau + timedelta(days=k), 0.0) / von_usdt
             for k in range(so_ngay)}
    gia_tri = list(chuoi.values())
    mean = statistics.fmean(gia_tri)
    std = statistics.stdev(gia_tri) if len(gia_tri) >= 2 else None
    kq.update(
        n_ngay=len(gia_tri),
        ngay_dau=ngay_dau.isoformat(),
        mean=mean,
        std=std,
        h=dsr_hurdle(n_trials),
        can_duoi=dsr_adjusted_expectancy(mean, std, len(gia_tri), n_trials=n_trials) if std is not None else None,
        chuoi_ngay=chuoi,
    )

    tong_pnl = math.fsum(float(t["profit_abs"]) for t in ds)
    tong_funding = math.fsum(float(t["funding_fees"]) for t in ds)
    chan: dict[str, dict[str, Any]] = {}
    for ten, la_short in (("long", False), ("short", True)):
        nhom = [t for t in ds if bool(t["is_short"]) is la_short]
        chan[ten] = {
            "so_lenh": len(nhom),
            "profit_abs": math.fsum(float(t["profit_abs"]) for t in nhom),
            "funding_fees": math.fsum(float(t["funding_fees"]) for t in nhom),
        }
    kq["chi_ghi"] = {
        "ghi_chu": "chỉ ghi, không phán quyết (DR-D0-IQ0003 §14); funding_fees theo quy ước Freqtrade (âm = trả)",
        "tong_profit_abs": tong_pnl,
        "tong_funding_fees": tong_funding,
        "ty_phan_funding_trong_lai_rong": (tong_funding / tong_pnl) if tong_pnl > 0 else None,
        "tach_chan": chan,
        "nhan_thoat": dict(sorted(Counter(str(t["exit_reason"]) for t in ds).items())),
    }
    return kq
