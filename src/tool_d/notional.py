"""TD-0082 — kiểm min notional + độ thô bước lot từng mã so với tranche 1
nhỏ nhất (spec dòng 2751-2754: L-Z20 "vi phạm → TỪ CHỐI VÀO LỆNH … nối vào
kiểm min-notional ở D0-PRE"). Logic thuần, không gọi mạng.

Hai điều kiện, tính ở ZONE RỘNG NHẤT (R_eff lớn → notional nhỏ nhất):
  (1) min notional: tranche 1 = rho × E_D / (n_tranches × R_eff) ≥ sàn sàn.
  (2) L-Z20: sai số rủi ro do làm tròn lot ≤ 1% × rho × E_D.
      Sai số tối đa = n_tranches × (nửa bước lot) × giá × R_eff
      (mỗi tranche lệch tối đa nửa bước, cùng chiều, nhân khoảng cách tới SL).
"""

from __future__ import annotations

from dataclasses import dataclass

LZ20_TOLERANCE = 0.01  # spec dòng 2751: ≤ 1% × rho_eff × E_D


@dataclass(frozen=True)
class SymbolFilters:
    symbol: str
    min_notional_usdt: float
    step_size: float
    price: float


@dataclass(frozen=True)
class NotionalCheck:
    symbol: str
    tranche1_notional_usdt: float
    min_notional_usdt: float
    lot_risk_error_usdt: float
    lot_risk_tolerance_usdt: float

    @property
    def passes_min_notional(self) -> bool:
        return self.tranche1_notional_usdt >= self.min_notional_usdt

    @property
    def passes_lz20(self) -> bool:
        return self.lot_risk_error_usdt <= self.lot_risk_tolerance_usdt


def tranche1_notional(*, e_d: float, rho_pct: float, r_eff: float, n_tranches: int) -> float:
    """N_full / n_tranches với N_full = (rho × E_D) / R_eff (§6.8e, w = 1/3)."""
    if r_eff <= 0:
        raise ValueError(f"r_eff phải > 0, nhận: {r_eff}")
    return (rho_pct / 100.0) * e_d / r_eff / n_tranches


def check_symbol(
    f: SymbolFilters, *, e_d: float, rho_pct: float, r_eff: float, n_tranches: int
) -> NotionalCheck:
    risk_budget = (rho_pct / 100.0) * e_d
    return NotionalCheck(
        symbol=f.symbol,
        tranche1_notional_usdt=tranche1_notional(
            e_d=e_d, rho_pct=rho_pct, r_eff=r_eff, n_tranches=n_tranches
        ),
        min_notional_usdt=f.min_notional_usdt,
        lot_risk_error_usdt=n_tranches * 0.5 * f.step_size * f.price * r_eff,
        lot_risk_tolerance_usdt=LZ20_TOLERANCE * risk_budget,
    )


def build_symbol_filters(
    exchange_info: dict, prices: list[dict], symbols: set[str]
) -> list[SymbolFilters]:
    """Ghép `exchangeInfo.filters` (MIN_NOTIONAL, LOT_SIZE) với `ticker/price`
    cho đúng tập `symbols`. Thiếu bộ lọc hay thiếu giá → raise (fail-closed,
    không gán 0)."""
    price_by = {p["symbol"]: float(p["price"]) for p in prices}
    out: list[SymbolFilters] = []
    for s in exchange_info["symbols"]:
        sym = s["symbol"]
        if sym not in symbols:
            continue
        filters = {x["filterType"]: x for x in s["filters"]}
        if "MIN_NOTIONAL" not in filters or "LOT_SIZE" not in filters:
            raise ValueError(f"{sym}: thiếu bộ lọc MIN_NOTIONAL/LOT_SIZE trong exchangeInfo")
        if sym not in price_by:
            raise ValueError(f"{sym}: không có giá trong ticker/price")
        out.append(
            SymbolFilters(
                symbol=sym,
                min_notional_usdt=float(filters["MIN_NOTIONAL"]["notional"]),
                step_size=float(filters["LOT_SIZE"]["stepSize"]),
                price=price_by[sym],
            )
        )
    missing = symbols - {f.symbol for f in out}
    if missing:
        raise ValueError(f"không thấy trong exchangeInfo: {sorted(missing)}")
    return sorted(out, key=lambda f: f.symbol)
