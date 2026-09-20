"""TD-0360 (`DR-D4-20` §8) — BƯỚC HỢP ĐỒNG của sàn cho một cặp: đơn vị nhỏ nhất mà số lượng lệnh biểu diễn được.

Vì sao cần: `DR-D4-04` §7 (ii) đòi mọi lệnh đủ ba tranche có `cost_j / cost_1 ∈ [0,99; 1,01]`. Đo thật
(`TD-0359`, EXPLORE, 0 trial): 5/16 lệnh vượt dung sai, lệch lớn nhất **5,91%** — và cơ chế KHÔNG phải cỡ lệnh
tính sai. Ở `MTL` (`amount = 11`) và `ETH` (`amount = 0,008`), số lượng hợp đồng của BA tranche **bằng nhau**:
cỡ lệnh thiết kế bằng nhau về notional nên `amount_j` chỉ chênh chút ít, và **bước hợp đồng nuốt trọn phần chênh**
ở cỡ lệnh 12–30 USDT. Dung sai ±1% vì thế chặt hơn thứ SÀN biểu diễn được — chủ dự án chốt 20/09/2026: đổi chốt
thành `max(1%, một bước hợp đồng tại giá đó)`.

Không tự viết lại phép làm tròn của Freqtrade: đọc THẲNG `precision` + `precisionMode` của chính `Exchange` mà
backtest dùng (cùng khuôn `thanh_ly.tinh_liq_freqtrade` — `DR-D4-17`). Mode lạ (`SIGNIFICANT_DIGITS`) ⇒ trả `None`
⇒ tầng gọi giữ nguyên dung sai 1% (fail-closed: chặt hơn, không lỏng hơn).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

#: `pair -> bước hợp đồng` (None = không xác định được ⇒ dùng dung sai gốc).
BuocAmount = Callable[[str], "float | None"]


def buoc_amount_freqtrade(config_freqtrade: Path) -> BuocAmount:
    """Dựng `Exchange` Freqtrade MỘT lần (`dry_run`, `runmode=backtest`, bảng thị trường trong image)."""
    import ccxt
    from freqtrade.configuration.load_config import load_config_file
    from freqtrade.resolvers import ExchangeResolver

    cfg = load_config_file(str(config_freqtrade))
    cfg["dry_run"] = True
    cfg["runmode"] = "backtest"
    ex = ExchangeResolver.load_exchange(cfg, validate=False, load_leverage_tiers=False)

    def buoc(pair: str) -> float | None:
        prec = ex.get_precision_amount(pair)
        if prec is None:
            return None
        mode = ex.precisionMode
        if mode == ccxt.TICK_SIZE:
            return float(prec)
        if mode == ccxt.DECIMAL_PLACES:
            return float(10.0 ** -int(prec))
        return None  # SIGNIFICANT_DIGITS — không quy ra một bước cố định được

    return buoc


__all__ = ["BuocAmount", "buoc_amount_freqtrade"]
