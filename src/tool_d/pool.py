"""Chốt pool giao dịch + tập EXPLORE — §0.3, §0.3b, §0.3c, §9c.4b (TD-0083).

Logic THUẦN (không gọi mạng) — nhận dữ liệu đã tải sẵn (từ
`api_client.binance_public`), trả về kết quả. Tách riêng để test được
không cần mạng thật.

🔴 Tiêu chí (i)-(iv) là HÀNG RÀO CỨNG, không ép cho đủ `pool_size_target`
(spec dòng 385-387: "Pool = số mã vượt tiêu chí, có thể 73 hay 88").
Ngưỡng ở đây được chọn ĐỘC LẬP theo lý do chất lượng dữ liệu của từng
tiêu chí (xem `docs/decisions/DR-D0PRE-05-pool-criteria.md`) — việc kết
quả ra gần đúng 100 là TRÙNG HỢP xác nhận thêm, KHÔNG PHẢI mục tiêu suy
ngược ra ngưỡng.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

# §0.3b — quyết định VẬN HÀNH cố định, không phải kết luận từ dữ liệu.
EXCLUDE_FROM_TRADING: frozenset[str] = frozenset({"BTCUSDT", "ETHUSDT"})


@dataclass(frozen=True)
class SymbolStat:
    symbol: str
    onboard_date: datetime
    quote_volume_24h: float


@dataclass(frozen=True)
class PoolResult:
    trading: tuple[str, ...]  # đã sắp xếp, dùng để backtest/live
    explore: tuple[str, ...]  # BTC/ETH + mọi mã trượt tiêu chí


def build_symbol_stats(
    exchange_info: dict, tickers: list[dict], *, now: datetime | None = None
) -> list[SymbolStat]:
    """Gộp `exchangeInfo` (onboardDate) + `ticker/24hr` (quoteVolume) cho
    mọi hợp đồng PERPETUAL/USDT đang TRADING."""
    tickers_by_symbol = {t["symbol"]: t for t in tickers}
    stats: list[SymbolStat] = []
    for s in exchange_info["symbols"]:
        if not (
            s.get("contractType") == "PERPETUAL"
            and s.get("quoteAsset") == "USDT"
            and s.get("status") == "TRADING"
        ):
            continue
        symbol = s["symbol"]
        ticker = tickers_by_symbol.get(symbol)
        volume = float(ticker["quoteVolume"]) if ticker else 0.0
        onboard = datetime.fromtimestamp(s["onboardDate"] / 1000, tz=timezone.utc)
        stats.append(SymbolStat(symbol=symbol, onboard_date=onboard, quote_volume_24h=volume))
    return stats


def compute_pool(
    stats: list[SymbolStat],
    *,
    age_floor_days: int,
    volume_floor_usdt: float,
    now: datetime | None = None,
) -> PoolResult:
    """Áp tiêu chí (i) volume, (ii) tuổi niêm yết. (iii)/(iv) không cần
    ngưỡng lọc riêng (xem DR-D0PRE-05) — không áp dụng ở đây.

    §0.3b: BTC/ETH luôn vào EXPLORE, không bao giờ vào `trading` — kể cả
    khi chúng thoả tiêu chí (chúng luôn thoả, thanh khoản cao nhất).
    """
    now = now or datetime.now(timezone.utc)
    trading: list[str] = []
    explore: list[str] = []

    for stat in stats:
        age_days = (now - stat.onboard_date).days
        if stat.symbol in EXCLUDE_FROM_TRADING:
            explore.append(stat.symbol)
            continue
        passes = age_days >= age_floor_days and stat.quote_volume_24h >= volume_floor_usdt
        (trading if passes else explore).append(stat.symbol)

    return PoolResult(trading=tuple(sorted(trading)), explore=tuple(sorted(explore)))
