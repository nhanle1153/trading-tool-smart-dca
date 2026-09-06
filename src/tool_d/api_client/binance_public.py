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
