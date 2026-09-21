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
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class TinhLiq(Protocol):
    """`(pair, open_rate, amount, stake_amount, leverage[, la_short]) -> giá thanh lý đã dịch buffer | None`.

    🔴 `Protocol` chứ không phải `Callable[...]` (`TD-0364`, phiên `-f3` tái lập được cửa hở): chiều SHORT truyền
    thêm `la_short=True`, nên một giao ước khai 5 đối số là **khai sai thực tế** — hàm giả 5 đối số đi đường Short
    sẽ ăn `TypeError` lúc chạy, và nếu ai bắt `Exception` quanh lời gọi (đường chiến lược hay bị
    `strategy_safe_wrapper` nuốt, `MT-16` vii) thì nó thành *từ chối im lặng mọi lệnh Short*. Khai bằng `Protocol`
    để chỗ sai lộ ra lúc soạn thảo; `ThanhLyError` bên dưới lo nốt phần lúc chạy.
    """

    def __call__(
        self, pair: str, open_rate: float, amount: float, stake_amount: float, leverage: float,
        la_short: bool = False,
    ) -> float | None: ...


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
    la_short: bool = False,
) -> DemThanhLy | None:
    """`None` ⇔ `tinh_liq` trả `None` (cặp không có trong bảng bậc). Người gọi phải biến nó thành `unreadable`.

    `la_short` (`TD-0364`): spec `:1856` viết *"case LONG (SHORT đảo dấu)"*. Chiều SHORT đảo cả tử lẫn mẫu —
    giá thanh lý nằm TRÊN giá vào, `sl` cũng vậy. Mặc định `False` nên mọi người gọi của tầng ĐO (D4 Long-only)
    không đổi một chữ.
    """
    if len(p) != len(w) or not p:
        raise ThanhLyError(f"{pair}: {len(p)} giá kế hoạch nhưng {len(w)} trọng số")
    if abs(math.fsum(w) - 1.0) > 1e-9:
        raise ThanhLyError(f"{pair}: tổng trọng số tranche {math.fsum(w)} ≠ 1")
    if n_full <= 0 or don_bay <= 0 or any(x <= 0 for x in p):
        raise ThanhLyError(f"{pair}: n_full={n_full}, don_bay={don_bay}, p={list(p)} — phải dương")
    p_avg = math.fsum(wj * pj for wj, pj in zip(w, p))
    mau = (sl - p_avg) if la_short else (p_avg - sl)
    if mau <= 0:
        huong = "SHORT" if la_short else "LONG"
        raise ThanhLyError(f"{pair}: sl {sl} sai phía so với p_avg_plan {p_avg} ({huong}) — mẫu số phải dương")

    amount = math.fsum(n_full * wj / pj for wj, pj in zip(w, p))
    open_rate_vt = n_full / amount
    stake = n_full / don_bay
    # 🔴 Gọi BẤT ĐỐI XỨNG có chủ ý: chiều Long giữ nguyên giao ước 5 đối số của `TinhLiq`. Thêm một đối số cho
    # mọi lời gọi sẽ buộc sửa KHẲNG ĐỊNH của `test_td0338_chi_so_export.py` (nó ghim đúng bộ 5 đối số đã nhận)
    # — mà "phải sửa khẳng định cũ mới xanh" là điều kiện DỪNG của `DR-D4-14` §7.
    if la_short:
        try:
            liq = tinh_liq(pair, open_rate_vt, amount, stake, don_bay, la_short=True)
        except TypeError as e:  # hàm được tiêm chỉ nhận 5 đối số — fail-closed, ĐỌC ĐƯỢC, không nuốt
            raise ThanhLyError(
                f"{pair}: hàm thanh lý được tiêm không nhận `la_short` — chiều SHORT cần giao ước 6 đối số ({e})"
            ) from e
    else:
        liq = tinh_liq(pair, open_rate_vt, amount, stake, don_bay)
    if liq is None:
        return None
    liq = float(liq)
    # Đại số của đệm giống nhau ở cả hai chiều: Freqtrade dịch `|open − liq| × buffer` về phía giá vào
    # (`Exchange.get_liquidation_price`, đọc trong image 2026.8), nên phép tính ngược ra giá THÔ không đổi.
    liq_tho = (liq - liquidation_buffer * open_rate_vt) / (1.0 - liquidation_buffer)
    tu = (liq - p_avg) if la_short else (p_avg - liq)
    return DemThanhLy(
        p_avg_plan=p_avg,
        liq_price=liq,
        liq_price_tho=liq_tho,
        liq_dist_pct=tu / p_avg,
        r_eff_pct=mau / p_avg,
        ty_so=tu / mau,
    )


@dataclass(frozen=True)
class HamThanhLy:
    """Hàm thanh lý kèm `liquidation_buffer` của CHÍNH sàn đã dựng nó, để giá thô tính ngược đúng hệ số."""

    tinh: TinhLiq
    liquidation_buffer: float


def ham_tu_exchange(ex) -> HamThanhLy:
    """Bọc một `Exchange` Freqtrade ĐÃ CÓ (không dựng sàn thứ hai).

    `TD-0364` cần đúng hàm này từ trong chiến lược, nơi `self.dp._exchange` CHÍNH LÀ sàn mà bộ chạy đang dùng —
    dựng một `Exchange` thứ hai ở đó là tự tạo hai nguồn cho cùng một con số, đúng thứ `DR-D4-05` gọi tên
    (*"lấy chuẩn của đường đang chạy"* là cách backtest và live lệch nhau mà không ai thấy).

    Import Freqtrade ở trong hàm: tầng thuần phía trên phải import được khi không có Freqtrade.
    """
    from freqtrade.exceptions import InvalidOrderException

    def tinh(
        pair: str, open_rate: float, amount: float, stake_amount: float, leverage: float,
        la_short: bool = False,
    ) -> float | None:
        try:
            return ex.get_liquidation_price(
                pair=pair, open_rate=open_rate, is_short=la_short, amount=amount,
                stake_amount=stake_amount, leverage=leverage, wallet_balance=stake_amount,
            )
        except InvalidOrderException:
            # Đo 19/09/2026: cặp không có trong bảng bậc ⇒ "Maintenance margin rate ... is unavailable". Trả None để
            # người gọi ghi `unreadable` kèm tên cặp (N6), thay vì sập cả arm SAU con dấu.
            return None

    return HamThanhLy(tinh=tinh, liquidation_buffer=float(ex.liquidation_buffer))


def tinh_liq_freqtrade(config_freqtrade: Path) -> HamThanhLy:
    """Dựng `Exchange` Freqtrade MỘT lần: `dry_run`, `runmode=backtest`, bảng bậc đóng gói trong image (không cần mạng).

    Dùng cho tầng ĐO (bộ chạy lô), nơi chưa có sàn nào trong tay. Trong chiến lược thì dùng `ham_tu_exchange()`.
    """
    from freqtrade.configuration.load_config import load_config_file
    from freqtrade.resolvers import ExchangeResolver

    cfg = load_config_file(str(config_freqtrade))
    cfg["dry_run"] = True
    cfg["runmode"] = "backtest"
    ex = ExchangeResolver.load_exchange(cfg, validate=False, load_leverage_tiers=True)
    return ham_tu_exchange(ex)


__all__ = [
    "DemThanhLy",
    "HamThanhLy",
    "ThanhLyError",
    "TinhLiq",
    "ham_tu_exchange",
    "liq_buffer_ke_hoach",
    "tinh_liq_freqtrade",
]
