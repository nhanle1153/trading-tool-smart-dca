"""Binance USDⓈ-M Futures — endpoint ĐỌC công khai. R1 Single Egress:
đây PHẢI là module DUY NHẤT trong toàn bộ codebase gọi thẳng ra mạng tới
Binance. Không gọi `urllib`/`requests`/`httpx` trực tiếp ở nơi khác —
kể cả trong entrypoint (`api-integration-rules.md` Mục 2, R1).

Chỉ endpoint public (không cần API key — R10 không áp dụng ở đây, không
có secret nào để quản lý). Endpoint private (đặt lệnh) là việc của D3.5+.
"""

from __future__ import annotations

import json
import urllib.request
from urllib.error import HTTPError, URLError

BASE_URL = "https://fapi.binance.com"
DEFAULT_TIMEOUT_S = 10.0  # R11 — timeout riêng cho từng request, không dựa mặc định thư viện


class BinancePublicApiError(RuntimeError):
    """Lỗi khi gọi endpoint public Binance (mạng, HTTP, hoặc timeout)."""


def get_exchange_info(*, timeout: float = DEFAULT_TIMEOUT_S) -> dict:
    """`GET /fapi/v1/exchangeInfo` — metadata mọi hợp đồng (trạng thái,
    ngày lên sàn `onboardDate`, precision, min notional). Dùng cho
    TD-0082 (min notional) và TD-0083 (chốt pool).
    """
    url = f"{BASE_URL}/fapi/v1/exchangeInfo"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310
            return json.loads(resp.read())
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise BinancePublicApiError(f"gọi {url} thất bại: {exc}") from exc


def get_ticker_24hr(*, timeout: float = DEFAULT_TIMEOUT_S) -> list[dict]:
    """`GET /fapi/v1/ticker/24hr` — thống kê 24h MỌI hợp đồng (bao gồm
    `quoteVolume`, dùng làm proxy volume cho tiêu chí (i) §0.3). Không
    truyền `symbol` để lấy TOÀN BỘ trong 1 lệnh gọi (tránh N lệnh gọi
    riêng cho N mã — đúng tinh thần R2/bounded loop).
    """
    url = f"{BASE_URL}/fapi/v1/ticker/24hr"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310
            return json.loads(resp.read())
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise BinancePublicApiError(f"gọi {url} thất bại: {exc}") from exc


def get_ticker_price(*, timeout: float = DEFAULT_TIMEOUT_S) -> list[dict]:
    """`GET /fapi/v1/ticker/price` — giá hiện tại MỌI hợp đồng, payload nhỏ
    hơn nhiều so với `ticker/24hr` (TD-0082: `ticker/24hr` từng timeout ở
    10s khi chỉ cần giá để quy bước lot ra USDT). Một lệnh gọi cho toàn bộ
    (R2/bounded loop).
    """
    url = f"{BASE_URL}/fapi/v1/ticker/price"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310
            return json.loads(resp.read())
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise BinancePublicApiError(f"gọi {url} thất bại: {exc}") from exc


def get_klines(
    *,
    symbol: str,
    interval: str,
    start_time_ms: int | None = None,
    end_time_ms: int | None = None,
    limit: int = 1500,
    timeout: float = DEFAULT_TIMEOUT_S,
) -> list[list]:
    """`GET /fapi/v1/klines` — nến lịch sử (OHLCV). Dùng cho TD-0084 (đo
    độ dài dữ liệu thật + nhận diện chế độ thị trường cho mốc CALIB/WFO/
    LOCKBOX, DR-011). `limit` tối đa Binance công bố là 1500 — raise nếu
    ngoài khoảng, không tự cắt bớt (fail-closed, giống `get_open_interest_hist`).
    """
    if not (1 <= limit <= 1500):
        raise ValueError(f"limit phải trong [1, 1500], nhận: {limit}")
    params = [f"symbol={symbol}", f"interval={interval}", f"limit={limit}"]
    if start_time_ms is not None:
        params.append(f"startTime={start_time_ms}")
    if end_time_ms is not None:
        params.append(f"endTime={end_time_ms}")
    url = f"{BASE_URL}/fapi/v1/klines?{'&'.join(params)}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310 — URL cố định, không do người dùng nhập
            return json.loads(resp.read())
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise BinancePublicApiError(f"gọi {url} thất bại: {exc}") from exc


def get_open_interest_hist(
    *,
    symbol: str,
    period: str = "1d",
    limit: int = 500,
    timeout: float = DEFAULT_TIMEOUT_S,
) -> list[dict]:
    """`GET /futures/data/openInterestHist` — dùng để verify độ dài lịch
    sử Open Interest THẬT SỰ Binance trả về (TD-0080, spec dòng 4457-4460).

    `limit` tối đa Binance công bố là 500 — không tự động cắt bớt hay nới
    ra, raise nếu ngoài khoảng hợp lệ (fail-closed, không âm thầm sửa
    tham số người gọi).
    """
    if not (1 <= limit <= 500):
        raise ValueError(f"limit phải trong [1, 500], nhận: {limit}")
    url = f"{BASE_URL}/futures/data/openInterestHist?symbol={symbol}&period={period}&limit={limit}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310 — URL cố định, không do người dùng nhập
            return json.loads(resp.read())
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise BinancePublicApiError(f"gọi {url} thất bại: {exc}") from exc
