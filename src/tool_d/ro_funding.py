"""TD-0400 — tầng THUẦN của rổ funding chéo `IQ-0003` (`DR-D0-IQ0003` §3).

Không import Freqtrade: chiến lược `RoFunding` chỉ nạp dữ liệu và gọi các hàm ở đây, nên luật chọn rổ kiểm được bằng
dữ liệu tổng hợp mà không cần backtest.

Luật (DR §3, dịch từ tờ chọn — DIỄN GIẢI ghi rõ):
  • chỉ số của một mã tại lần cân rổ `t` = TỔNG `funding_rate` các kỳ chốt có `date ∈ (t − cửa_sổ, t]` (chủ dự án chốt:
    tổng trong 72h, không phải trung bình 9 kỳ — mã chốt 4h và 8h so được với nhau);
  • đủ điều kiện ⇔ kỳ chốt ĐẦU TIÊN của mã có `date ≤ t − cửa_sổ` (đủ lịch sử) và mã có mặt tại `t`;
  • xếp GIẢM dần theo chỉ số, hoà thì theo tên mã (tất định); SHORT = `k` mã đầu, LONG = `k` mã cuối,
    `k = max(k_tối_thiểu, floor(tỉ_lệ_k × n))`; `n < số_coin_tối_thiểu` ⇒ không nhóm nào.

🔴 Chống nhìn trước: mọi hàm nhận `t` và CHỈ dùng dòng có `date ≤ t`, kể cả khi được đưa cả chuỗi (backtest nạp toàn bộ
dữ liệu cho `dp.get_pair_dataframe()` — bài học `_df_4h`, `_funding_8h` của ZA).
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta

import pandas as pd

#: BTC/ETH loại tường minh (DR §3 điều 3) — `pool_t*.yaml` đã loại sẵn, đây là chốt kép rẻ.
MA_LOAI_CO_DINH = frozenset({"BTC", "ETH"})


class RoFundingError(ValueError):
    """Dữ liệu hay tham số không dùng được — TỪ CHỐI, không đoán (N6)."""


@dataclass(frozen=True)
class NhomRo:
    """Kết quả một lần cân rổ. `k = 0` và hai tập rỗng ⇔ không đủ mã, ngày đó không có nhóm nào."""

    t: datetime
    k: int
    short: frozenset[str]
    long: frozenset[str]
    so_ma_du_dieu_kien: int

    def nhom_cua(self, ma: str) -> str | None:
        if ma in self.short:
            return "short"
        if ma in self.long:
            return "long"
        return None


def ma_goc(cap: str) -> str:
    """`"ABC/USDT:USDT"` → `"ABC"`; `"ABC_USDT_USDT"` → `"ABC"`."""
    return cap.replace("_", "/").split("/")[0]


def chi_so_funding(funding: pd.DataFrame, t: datetime, *, cua_so_gio: int) -> float | None:
    """Tổng funding trong `(t − cửa_sổ, t]`; `None` nếu mã chưa đủ lịch sử tại `t` (không phải 0.0 — N6).

    `funding` có cột `date` (UTC) và `funding_rate`, chỉ gồm dòng kỳ chốt."""
    if funding is None or funding.empty:
        return None
    if "date" not in funding or "funding_rate" not in funding:
        raise RoFundingError(f"dữ liệu funding thiếu cột `date`/`funding_rate`: {list(funding.columns)}")
    da_biet = funding[funding["date"] <= t]
    if da_biet.empty or da_biet["date"].iloc[0] > t - timedelta(hours=cua_so_gio):
        return None
    trong_cua_so = da_biet[da_biet["date"] > t - timedelta(hours=cua_so_gio)]["funding_rate"]
    if trong_cua_so.isna().any():
        raise RoFundingError(f"funding NaN trong cửa sổ kết thúc {t} — không coi NaN là 0")
    return float(trong_cua_so.sum())


def so_k(n: int, *, ty_le_k: float, k_toi_thieu: int) -> int:
    return max(k_toi_thieu, math.floor(ty_le_k * n))


def chia_nhom(
    chi_so: Mapping[str, float],
    t: datetime,
    *,
    ty_le_k: float,
    k_toi_thieu: int,
    so_coin_toi_thieu: int,
) -> NhomRo:
    """Chia nhóm từ `{mã: chỉ số}` của các mã ĐÃ đủ điều kiện."""
    n = len(chi_so)
    if n < so_coin_toi_thieu:
        return NhomRo(t=t, k=0, short=frozenset(), long=frozenset(), so_ma_du_dieu_kien=n)
    k = so_k(n, ty_le_k=ty_le_k, k_toi_thieu=k_toi_thieu)
    if 2 * k > n:
        # Không thể có cùng một mã ở cả hai chân. Với tham số hiện hành (k_min 3, n ≥ 6) không xảy ra; xảy ra là
        # tham số sai — từ chối thay vì lặng lẽ cho hai nhóm giao nhau.
        raise RoFundingError(f"2k = {2 * k} > {n} mã đủ điều kiện tại {t} — hai chân sẽ chồng nhau")
    xep = sorted(chi_so.items(), key=lambda kv: (-kv[1], kv[0]))
    short = frozenset(m for m, _ in xep[:k])
    long = frozenset(m for m, _ in xep[-k:])
    return NhomRo(t=t, k=k, short=short, long=long, so_ma_du_dieu_kien=n)


def nhom_tai(
    funding_theo_ma: Mapping[str, pd.DataFrame],
    co_mat_tai_t: Iterable[str],
    t: datetime,
    *,
    cua_so_gio: int,
    ty_le_k: float,
    k_toi_thieu: int,
    so_coin_toi_thieu: int,
) -> NhomRo:
    """Một lần cân rổ trọn vẹn: lọc đủ điều kiện → chỉ số → chia nhóm. `co_mat_tai_t` = mã có nến tại `t`."""
    co_mat = set(co_mat_tai_t)
    chi_so: dict[str, float] = {}
    for ma, funding in funding_theo_ma.items():
        if ma in MA_LOAI_CO_DINH or ma not in co_mat:
            continue
        gia_tri = chi_so_funding(funding, t, cua_so_gio=cua_so_gio)
        if gia_tri is not None:
            chi_so[ma] = gia_tri
    return chia_nhom(chi_so, t, ty_le_k=ty_le_k, k_toi_thieu=k_toi_thieu, so_coin_toi_thieu=so_coin_toi_thieu)


def la_moc_can_ro(t: datetime, *, gio_utc: int) -> bool:
    """`t` là lúc KHỚP của một lần cân rổ (mở nến 1H `gio_utc`:00 UTC)."""
    return t.hour == gio_utc and t.minute == 0 and t.second == 0


def notional_moi_vi_the(von_usdt: float, k: int) -> float:
    """`von / (2k)` — DR §4. `k = 0` (không có nhóm) không mở vị thế nào ⇒ gọi với k = 0 là lỗi."""
    if k <= 0:
        raise RoFundingError("k = 0 — ngày không có nhóm thì không mở vị thế")
    if not (isinstance(von_usdt, (int, float)) and von_usdt > 0):
        raise RoFundingError(f"vốn rổ phải > 0, nhận {von_usdt!r}")
    return von_usdt / (2 * k)
