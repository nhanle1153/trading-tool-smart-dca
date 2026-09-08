"""TD-0082 — kiểm min notional + độ thô bước lot từng mã so với tranche 1
nhỏ nhất (spec dòng 2751-2754: L-Z20 "vi phạm → TỪ CHỐI VÀO LỆNH … nối vào
kiểm min-notional ở D0-PRE"). Logic thuần, không gọi mạng.

Hai điều kiện, tính ở ZONE RỘNG NHẤT (R_eff lớn → notional nhỏ nhất):
  (1) min notional: tranche 1 = rho_eff × E_D / (n_tranches × R_eff) ≥ sàn thật.
  (2) L-Z20: sai số rủi ro do làm tròn lot ≤ 1% × rho × E_D.
      Sai số tối đa = n_tranches × (nửa bước lot) × giá × R_eff
      (mỗi tranche lệch tối đa nửa bước, cùng chiều, nhân khoảng cách tới SL).

TD-0171 (mở lại TD-0082, 08/09/2026) sửa HAI giả định của bản đầu — cả hai
đều lệch về phía nói "qua", tức về phía tâng kết quả lên:

  **Tử số** dùng `rho` thô. Cỡ lệnh thật (TD-0187, §6.8f B1) là
  `rho_eff = rho × Π mult_*` với mọi `mult_* ≤ 1.0` (§6.2 — `rho` là TRẦN)
  nên notional thật ≤ notional đã kiểm. Vì thế `mult_product` là tham số
  **BẮT BUỘC, không mặc định**: một mặc định `1.0` chính là cách bảng cũ
  nói dối mà không ai gõ một con số sai nào.

  **Mẫu số** so với `MIN_NOTIONAL.notional` trần trụi. Freqtrade so với
  `max(cost_min × stoploss_reserve, amount_min × price × margin_reserve)`
  rồi chia đòn bẩy (`exchange.py:_get_stake_amount_limit`, đọc trong image
  ngày 08/09/2026). Với `stoploss = -0.99` của `config.json` thì
  `stoploss_reserve` chạm trần **1,5** nên sàn cao hơn 50%. Còn vế `minQty`
  thì `build_symbol_filters()` chưa từng đọc.

🔴 **Đòn bẩy KHÔNG có mặt ở đây, và đó là kết luận ĐO được, không phải bỏ
sót.** Ghi chú MT-16 nghi *"chưa chia đòn bẩy"*. Đọc mã nguồn: sàn được chia
`leverage` (`_get_stake_amount_considering_leverage`), mà `stake` do chiến
lược trả cũng là `notional / L` (`sizing.stake_tranche`). Đòn bẩy chia **cả
hai vế** nên triệt tiêu khỏi phép so; PASS/FAIL không đổi ở 1x hay 3x. Thêm
nó vào đây là chia sàn thêm một lần nữa, khi đó mọi mã đều "qua". Test ghim:
`tests/lock/test_td0171_san_min_notional_that.py`.
"""

from __future__ import annotations

from dataclasses import dataclass

LZ20_TOLERANCE = 0.01  # spec dòng 2751: ≤ 1% × rho_eff × E_D

#: `freqtrade/constants.py:DEFAULT_AMOUNT_RESERVE_PERCENT` (đọc trong image
#: 08/09/2026). Ta KHÔNG đặt `amount_reserve_percent` trong config.json nên
#: mặc định này là con số thật đang chạy.
MARGIN_RESERVE_PERCENT = 0.05

#: Trần của `stoploss_reserve` trong `_get_stake_amount_limit`
#: (`max(min(x, 1.5), 1)`). Với `stoploss = -0.99` của ta thì x = 105, tức
#: luôn chạm trần này.
STOPLOSS_RESERVE_MAX = 1.5


@dataclass(frozen=True)
class SymbolFilters:
    symbol: str
    min_notional_usdt: float
    step_size: float
    min_qty: float
    price: float


@dataclass(frozen=True)
class NotionalCheck:
    symbol: str
    tranche1_notional_usdt: float
    min_notional_usdt: float  # `MIN_NOTIONAL.notional` trần trụi của sàn
    san_usdt: float  # sàn THẬT Freqtrade áp — xem san_min_notional_freqtrade
    san_ve_thang: str  # "cost" hay "amount": vế nào quyết định sàn
    lot_risk_error_usdt: float
    lot_risk_tolerance_usdt: float

    @property
    def passes_min_notional(self) -> bool:
        return self.tranche1_notional_usdt >= self.san_usdt

    @property
    def passes_lz20(self) -> bool:
        return self.lot_risk_error_usdt <= self.lot_risk_tolerance_usdt


def tranche1_notional(*, e_d: float, rho_pct: float, r_eff: float, n_tranches: int) -> float:
    """N_full / n_tranches với N_full = (rho × E_D) / R_eff (§6.8e, w = 1/3)."""
    if r_eff <= 0:
        raise ValueError(f"r_eff phải > 0, nhận: {r_eff}")
    return (rho_pct / 100.0) * e_d / r_eff / n_tranches


#: 🔴 Đo 09/09/2026 trong image: Freqtrade KHÔNG dùng `stoploss` của config
#: cho mọi phép kiểm sàn — nó truyền một hằng số KHÁC NHAU theo từng đường
#: chạy. Hệ quả nặng nhất: **backtest và live không cùng một sàn**, nên một
#: cấu hình qua sàn ở D4 (backtest) vẫn có thể rớt sàn ở D11/D12 (live) —
#: đúng thứ quy tắc 9 (parity local–staging–prod) tồn tại để chặn.
#:
#: `"strategy"` = lấy `strategy.stoploss` (của ta: -0.99 → chạm trần 1,5).
#:   backtesting.py:1087   vào lệnh        -0.05   (pos_adjust → 0.0)
#:   backtesting.py:723    phần dư sau TP  -0.1, KHÔNG truyền leverage
#:   freqtradebot.py:1185  vào lệnh live   strategy.stoploss (pos_adjust → 0.0)
#:   freqtradebot.py:846   phần dư live    strategy.stoploss
SL_THEO_DUONG_CHAY: dict[str, float | str] = {
    "backtest_vao_lenh": -0.05,
    "backtest_tranche_2_3": 0.0,
    "backtest_phan_du": -0.1,
    "live_vao_lenh": "strategy",
    "live_tranche_2_3": 0.0,
    "live_phan_du": "strategy",
}


def sl_hieu_dung(duong_chay: str, *, strategy_stoploss: float) -> float:
    """`stoploss` Freqtrade THỰC SỰ truyền vào phép kiểm sàn ở `duong_chay`.

    Tên đường chạy phải khai tường minh — không có mặc định "cái hay dùng":
    chính việc tưởng mọi đường dùng chung `stoploss` của config đã làm bảng
    đo đầu của TD-0171 quá bi quan ở backtest (7,50 thay vì 5,53).
    """
    if duong_chay not in SL_THEO_DUONG_CHAY:
        raise ValueError(
            f"đường chạy không rõ: {duong_chay!r}. Phải là một trong "
            f"{sorted(SL_THEO_DUONG_CHAY)}"
        )
    gt = SL_THEO_DUONG_CHAY[duong_chay]
    return strategy_stoploss if gt == "strategy" else float(gt)


def san_min_notional_freqtrade(
    f: SymbolFilters,
    *,
    stoploss: float,
    amount_reserve_percent: float = MARGIN_RESERVE_PERCENT,
) -> float:
    """Sàn notional Freqtrade THẬT SỰ áp — chép đúng `_get_stake_amount_limit`.

    Trả sàn tính bằng **notional** (chưa chia đòn bẩy): xem docstring module
    về việc đòn bẩy triệt tiêu khỏi phép so.
    """
    if not (0 <= amount_reserve_percent < 1):
        raise ValueError(
            f"amount_reserve_percent phải trong [0,1), nhận {amount_reserve_percent}"
        )
    margin_reserve = 1.0 + amount_reserve_percent
    if abs(stoploss) == 1:
        stoploss_reserve = STOPLOSS_RESERVE_MAX
    else:
        stoploss_reserve = margin_reserve / (1 - abs(stoploss))
    stoploss_reserve = max(min(stoploss_reserve, STOPLOSS_RESERVE_MAX), 1.0)
    return max(
        f.min_notional_usdt * stoploss_reserve,
        f.min_qty * f.price * margin_reserve,
    )


def _ve_thang(f: SymbolFilters, *, stoploss: float) -> str:
    """Vế nào quyết định sàn — để bảng đối chiếu nói được LÝ DO rớt, không
    chỉ nói rớt."""
    chi_cost = SymbolFilters(f.symbol, f.min_notional_usdt, f.step_size, 0.0, f.price)
    if san_min_notional_freqtrade(f, stoploss=stoploss) > san_min_notional_freqtrade(
        chi_cost, stoploss=stoploss
    ):
        return "amount"
    return "cost"


def check_symbol(
    f: SymbolFilters,
    *,
    e_d: float,
    rho_pct: float,
    mult_product: float,
    r_eff: float,
    n_tranches: int,
    stoploss: float,
) -> NotionalCheck:
    """`mult_product` = tích sáu hệ số §6.2. **Bắt buộc khai, không mặc
    định** (xem docstring module). `stoploss` là `stoploss` của config
    Freqtrade — nó vào sàn qua `stoploss_reserve`.

    ⚠️ Dung sai L-Z20 vẫn tính trên `rho` THÔ, không phải `rho_eff`: spec
    dòng 2751 neo dung sai vào ngân sách rủi ro danh nghĩa. Hạ nó theo
    `mult_*` là tự nới một chốt của spec.
    """
    if mult_product != mult_product or not (0 < mult_product <= 1.0):
        raise ValueError(
            f"mult_product phải trong (0, 1] — §6.2: rho là TRẦN, mọi mult_* ≤ 1.0. "
            f"Nhận {mult_product}"
        )
    risk_budget = (rho_pct / 100.0) * e_d
    return NotionalCheck(
        symbol=f.symbol,
        tranche1_notional_usdt=tranche1_notional(
            e_d=e_d, rho_pct=rho_pct * mult_product, r_eff=r_eff, n_tranches=n_tranches
        ),
        min_notional_usdt=f.min_notional_usdt,
        san_usdt=san_min_notional_freqtrade(f, stoploss=stoploss),
        san_ve_thang=_ve_thang(f, stoploss=stoploss),
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
                min_qty=float(filters["LOT_SIZE"]["minQty"]),
                price=price_by[sym],
            )
        )
    missing = symbols - {f.symbol for f in out}
    if missing:
        raise ValueError(f"không thấy trong exchangeInfo: {sorted(missing)}")
    return sorted(out, key=lambda f: f.symbol)
