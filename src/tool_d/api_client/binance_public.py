"""Binance USDⓈ-M Futures — R1 Single Egress: đây PHẢI là module DUY
NHẤT trong toàn bộ codebase gọi thẳng ra mạng tới Binance. Không gọi
`urllib`/`requests`/`httpx` trực tiếp ở nơi khác — kể cả trong
entrypoint (`api-integration-rules.md` Mục 2, R1).

Phần lớn hàm dưới đây là endpoint ĐỌC công khai (không cần API key —
R10 không áp dụng, không có secret nào để quản lý). `order_test_latency_ms()`
(TD-0116, H15 §6.7) là ngoại lệ DUY NHẤT — gọi endpoint KÝ (signed) trên
Binance Futures TESTNET để đo latency network+auth, vẫn nằm trong cùng
module này để giữ đúng nguyên tắc Single Egress (không tạo module thứ
hai gọi mạng chỉ vì một hàm cần ký request).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import urllib.parse
import urllib.request
from urllib.error import HTTPError, URLError

BASE_URL = "https://fapi.binance.com"
TESTNET_BASE_URL = "https://testnet.binancefuture.com"  # TD-0116, §6.7
DEFAULT_TIMEOUT_S = 10.0  # R11 — timeout riêng cho từng request, không dựa mặc định thư viện


class BinancePublicApiError(RuntimeError):
    """Lỗi khi gọi endpoint public Binance (mạng, HTTP, hoặc timeout)."""


class BinancePrivateApiError(RuntimeError):
    """Lỗi khi gọi endpoint KÝ (signed) Binance — mạng, HTTP, timeout,
    hoặc sàn từ chối do khoá/chữ ký/tham số sai."""


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


def _sign(params: dict[str, str], secret: str) -> str:
    """HMAC-SHA256 trên chuỗi query — đúng chuẩn ký request của Binance."""
    query = urllib.parse.urlencode(params)
    return hmac.new(secret.encode("utf-8"), query.encode("utf-8"), hashlib.sha256).hexdigest()


def order_test_latency_ms(
    *,
    api_key: str,
    api_secret: str,
    base_url: str = TESTNET_BASE_URL,
    symbol: str = "BTCUSDT",
    quantity: str = "0.001",
    timeout: float = DEFAULT_TIMEOUT_S,
) -> float:
    """H15 (§6.7, TD-0116) — `POST /fapi/v1/order/test`, đo round-trip
    latency network+auth THẬT tới Binance.

    Endpoint KHÔNG BAO GIỜ khớp lệnh thật — dừng trước bước matching
    engine (đã verify qua tài liệu Binance, không suy đoán) — nên
    latency đo được là CẬN DƯỚI của một lệnh thật (bỏ qua round-trip xử
    lý khớp lệnh), dùng làm ước lượng ban đầu, không thay thế đo lại ở
    dry-run/live.

    Mặc định `base_url=TESTNET_BASE_URL` — chủ dự án chọn hướng testnet
    (không cần tạo key production, §6.7 mục điều kiện bảo mật chỉ áp
    dụng khi dùng key production).
    """
    params = {
        "symbol": symbol,
        "side": "BUY",
        "type": "MARKET",
        "quantity": quantity,
        "timestamp": str(int(time.time() * 1000)),
        "recvWindow": "5000",
    }
    query = urllib.parse.urlencode(params)
    signature = _sign(params, api_secret)
    url = f"{base_url}/fapi/v1/order/test?{query}&signature={signature}"
    req = urllib.request.Request(url, method="POST", headers={"X-MBX-APIKEY": api_key})
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            resp.read()
    except (HTTPError, URLError, TimeoutError) as exc:
        raise BinancePrivateApiError(f"gọi {url.split('?')[0]} thất bại: {exc}") from exc
    return (time.monotonic() - t0) * 1000.0


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
