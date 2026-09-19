"""`TD-0348` (`DR-D4-17`) — `liq_buffer_ratio` tính theo KẾ HOẠCH đủ ba tranche (spec `:1858–1866`).

Tầng THUẦN. Giá thanh lý không tự tính ở đây: hàm nhận `tinh_liq` qua tham số. Đường sản xuất tiêm
`tinh_liq_freqtrade()`, tức chính `Exchange.get_liquidation_price()` mà backtest Freqtrade gọi. Test tiêm hàm giả để
kiểm đại số, và có một ca đối chiếu với hàm thật.

Vì sao không đọc export: Freqtrade cắt cột `liquidation_price` khi ghi file (`bt_fileutils.py:535`, đo `TD-0343`). Vì sao
không cần fill: spec viết *"Tính trên KẾ HOẠCH ĐẦY ĐỦ 3 TRANCHE, KHÔNG phải trên phần đã khớp"*.

Ba lựa chọn đã khai ở `DR-D4-17` §3: (1) hàm thanh lý nhận giá vào của VỊ THẾ (`open_rate_vt`, trung bình điều hoà theo
notional), còn tỉ số dùng `p_avg_plan = Σ w·p` đúng chữ spec; (2) cổng đọc giá ĐÃ DỊCH `liquidation_buffer`, giá thô ghi
cạnh; (3) bậc mmr tra theo `stake_amount` như Freqtrade.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

#: `(pair, open_rate, amount, stake_amount, leverage) -> giá thanh lý đã dịch buffer | None`.
TinhLiq = Callable[[str, float, float, float, float], "float | None"]


class ThanhLyError(ValueError):
    """Kế hoạch không tính được tỉ số (sl không dưới giá vào, trọng số lệch, ...). Fail-closed."""


@dataclass(frozen=True)
class DemThanhLy:
    """Đủ tử và mẫu cho Decision Log (spec `:1885` điểm 2), không chỉ tỉ số."""

    p_avg_plan: float
    liq_price: float  # ĐÃ dịch `liquidation_buffer` — số cổng đọc (DR-D4-17 §3 dòng 2)
    liq_price_tho: float  # trước khi dịch — chữ spec `:1862`, ghi cạnh
    liq_dist_pct: float
    r_eff_pct: float
    ty_so: float


def liq_buffer_ke_hoach(
    *,
    pair: str,
    p: Sequence[float],
    sl: float,
    w: Sequence[float],
    n_full: float,
    don_bay: float,
    liquidation_buffer: float,
    tinh_liq: TinhLiq,
) -> DemThanhLy | None:
    """`None` ⇔ `tinh_liq` trả `None` (cặp không có trong bảng bậc). Người gọi phải biến nó thành `unreadable`."""
    if len(p) != len(w) or not p:
        raise ThanhLyError(f"{pair}: {len(p)} giá kế hoạch nhưng {len(w)} trọng số")
    if abs(math.fsum(w) - 1.0) > 1e-9:
        raise ThanhLyError(f"{pair}: tổng trọng số tranche {math.fsum(w)} ≠ 1")
    if n_full <= 0 or don_bay <= 0 or any(x <= 0 for x in p):
        raise ThanhLyError(f"{pair}: n_full={n_full}, don_bay={don_bay}, p={list(p)} — phải dương")
    p_avg = math.fsum(wj * pj for wj, pj in zip(w, p))
    if sl >= p_avg:
        raise ThanhLyError(f"{pair}: sl {sl} ≥ p_avg_plan {p_avg} — Long-only, mẫu số phải dương")

    amount = math.fsum(n_full * wj / pj for wj, pj in zip(w, p))
    open_rate_vt = n_full / amount
    stake = n_full / don_bay
    liq = tinh_liq(pair, open_rate_vt, amount, stake, don_bay)
    if liq is None:
        return None
    liq = float(liq)
    liq_tho = (liq - liquidation_buffer * open_rate_vt) / (1.0 - liquidation_buffer)
    return DemThanhLy(
        p_avg_plan=p_avg,
        liq_price=liq,
        liq_price_tho=liq_tho,
        liq_dist_pct=(p_avg - liq) / p_avg,
        r_eff_pct=(p_avg - sl) / p_avg,
        ty_so=(p_avg - liq) / (p_avg - sl),
    )


@dataclass(frozen=True)
class HamThanhLy:
    """Hàm thanh lý kèm `liquidation_buffer` của CHÍNH sàn đã dựng nó, để giá thô tính ngược đúng hệ số."""

    tinh: TinhLiq
    liquidation_buffer: float


def tinh_liq_freqtrade(config_freqtrade: Path) -> HamThanhLy:
    """Dựng `Exchange` Freqtrade MỘT lần: `dry_run`, `runmode=backtest`, bảng bậc đóng gói trong image (không cần mạng).

    Import Freqtrade ở trong hàm: tầng thuần phía trên phải import được khi không có Freqtrade.
    """
    from freqtrade.configuration.load_config import load_config_file
    from freqtrade.exceptions import InvalidOrderException
    from freqtrade.resolvers import ExchangeResolver

    cfg = load_config_file(str(config_freqtrade))
    cfg["dry_run"] = True
    cfg["runmode"] = "backtest"
    ex = ExchangeResolver.load_exchange(cfg, validate=False, load_leverage_tiers=True)

    def tinh(pair: str, open_rate: float, amount: float, stake_amount: float, leverage: float) -> float | None:
        try:
            return ex.get_liquidation_price(
                pair=pair, open_rate=open_rate, is_short=False, amount=amount,
                stake_amount=stake_amount, leverage=leverage, wallet_balance=stake_amount,
            )
        except InvalidOrderException:
            # Đo 19/09/2026: cặp không có trong bảng bậc ⇒ "Maintenance margin rate ... is unavailable". Trả None để
            # người gọi ghi `unreadable` kèm tên cặp (N6), thay vì sập cả arm SAU con dấu.
            return None

    return HamThanhLy(tinh=tinh, liquidation_buffer=float(ex.liquidation_buffer))


__all__ = ["DemThanhLy", "HamThanhLy", "ThanhLyError", "TinhLiq", "liq_buffer_ke_hoach", "tinh_liq_freqtrade"]
