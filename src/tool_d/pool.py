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
    # H1-D (TD-0096, DR-D1-01) — mốc huỷ niêm yết THẬT, đo được từ
    # data.binance.vision cho mã không còn trong exchangeInfo hiện tại.
    # `None` = còn đang giao dịch (hoặc chưa biết mốc huỷ).
    delisted_at: datetime | None = None


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


def pairlist_point_in_time(
    stats: list[SymbolStat],
    *,
    t: datetime,
    age_floor_days: int,
    volume_floor_usdt: float,
) -> PoolResult:
    """H1-D (TD-0096) — pool hợp lệ tại một thời điểm `t` trong QUÁ KHỨ,
    không lệch sống sót (survivorship bias).

    Khác `compute_pool()` (chỉ tính đúng cho "bây giờ", dùng danh sách
    mã đang TRADING của `exchangeInfo` hiện tại): mã đã huỷ niêm yết
    TRƯỚC `t` phải KHÔNG có mặt (đã rời sàn, không thể giao dịch tại t),
    và mã CHƯA lên sàn tại `t` cũng KHÔNG có mặt (đã có ở `compute_pool`
    qua điều kiện tuổi, nhưng lọc thẳng ở đây để không phụ thuộc dấu của
    `age_days`). Không lọc hai trường hợp này → pool tại quá khứ sẽ
    "sạch" hơn thực tế, đúng chiều lệch mà DR-D1-01 đo được (219 mã).

    🔴 `stat.quote_volume_24h` PHẢI là volume TẠI thời điểm `t` (người
    gọi tự cung cấp từ dữ liệu lịch sử) — hàm này không tự suy volume.
    """
    eligible = [
        s
        for s in stats
        if s.onboard_date <= t and (s.delisted_at is None or s.delisted_at > t)
    ]
    return compute_pool(eligible, age_floor_days=age_floor_days, volume_floor_usdt=volume_floor_usdt, now=t)


def pairlist_over_time(
    stats_by_checkpoint: dict[datetime, list[SymbolStat]],
    *,
    age_floor_days: int,
    volume_floor_usdt: float,
) -> dict[datetime, PoolResult]:
    """H1-D (TD-0097, §9c.4b) — quét nhiều mốc `t` THEO THỨ TỰ THỜI GIAN,
    cưỡng chế ràng buộc cứng (b): *"Coin nào đã ở EXPLORE thì KHÔNG BAO
    GIỜ được đưa vào pool giao dịch sau này — kể cả khi nó bắt đầu thoả
    tiêu chí §0.3. Không có ngoại lệ."*

    `pairlist_point_in_time()` một mình KHÔNG đủ: nó vô trạng thái, mỗi
    lần gọi tính lại từ đầu — một mã trượt tiêu chí ở mốc sớm rồi hồi
    phục volume/tuổi ở mốc muộn sẽ được tính lại vào `trading`, đúng
    thứ "biến EXPLORE thành tập train" mà spec cấm tuyệt đối. Hàm này
    cộng dồn một tập cấm VĨNH VIỄN qua các mốc: mã nào từng rơi vào
    `explore` ở bất kỳ mốc nào (khi nó ĐÃ TỒN TẠI, không phải mốc trước
    khi nó lên sàn) thì bị khoá khỏi `trading` ở mọi mốc SAU đó.

    `stats_by_checkpoint[t]` là ảnh chụp `SymbolStat` (gồm volume TẠI
    `t`) dùng riêng cho mốc đó — volume thật đổi theo thời gian, không
    phải một con số cố định dùng chung cho mọi mốc.
    """
    permanently_excluded: set[str] = set()
    results: dict[datetime, PoolResult] = {}
    for t in sorted(stats_by_checkpoint):
        raw = pairlist_point_in_time(
            stats_by_checkpoint[t],
            t=t,
            age_floor_days=age_floor_days,
            volume_floor_usdt=volume_floor_usdt,
        )
        trading = tuple(s for s in raw.trading if s not in permanently_excluded)
        demoted_now = set(raw.trading) & permanently_excluded
        explore = tuple(sorted(set(raw.explore) | demoted_now))
        permanently_excluded |= set(raw.explore)
        results[t] = PoolResult(trading=trading, explore=explore)
    return results
