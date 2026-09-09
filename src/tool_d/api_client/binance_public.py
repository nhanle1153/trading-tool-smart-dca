"""Binance USDⓈ-M Futures — R1 Single Egress: đây PHẢI là module DUY
NHẤT trong toàn bộ codebase gọi thẳng ra mạng tới Binance. Không gọi
`urllib`/`requests`/`httpx` trực tiếp ở nơi khác — kể cả trong
entrypoint (`api-integration-rules.md` Mục 2, R1).

Phần lớn hàm dưới đây là endpoint ĐỌC công khai (không cần API key —
R10 không áp dụng, không có secret nào để quản lý). `latency_samples_ms()`
(TD-0116, H15 §6.7) là ngoại lệ DUY NHẤT — gọi được endpoint KÝ (signed),
vẫn nằm trong cùng module này để giữ đúng Single Egress (không tạo module
thứ hai gọi mạng chỉ vì một hàm cần ký request).

🔴 TD-0116 — KHÔNG có `TESTNET_BASE_URL` ở đây, và đó là một kết luận đã
kiểm chứng bằng mã nguồn, không phải thiếu sót: Freqtrade 2026.8 CỐ Ý
tắt testnet cho Binance (`exchange/binance.py`: `"supports_demo_trading":
False`, kèm chú thích *"Intentionally Disabled as it's a separate market
- not a simulated live market"*; `exchange.py:validate_demo_trading()`
raise `ConfigurationError` nếu bật). `ccxt` bên dưới CÓ `set_sandbox_mode`
nhưng Freqtrade không bao giờ gọi. Hệ quả cho H15: testnet là một thị
trường RIÊNG, đo latency tới đó là đo hạ tầng mà bot sẽ không bao giờ
dùng — nên phép đo chạy trên production.

🔴 TD-0197 — R2 (rate limit) + R3 (circuit breaker) nối vào ĐÚNG MỘT
điểm nghẽn (`_goi_json_cong_khai`) cho 5 hàm GET/JSON bên dưới, dùng lại
tầng THUẦN đã dựng ở `risk_supervisor.py` (TD-0196) thay vì viết lại.
Trần gọi/phút đọc từ `tier_c.api_calls_per_min` qua `resolve()` (N4 —
không hardcode, không ENV: đây là tham số Tầng C, khác ngưỡng breaker
`TOOLD_BREAKER_THRESHOLD` vốn là tham số VẬN HÀNH). `latency_samples_ms()`
CỐ Ý đứng ngoài — nó đo RTT, thêm throttle/breaker sẽ phá chính phép đo
nó đang làm (đã là ngoại lệ ghi rõ ở trên). `tai_dump_agg_trades()` (host
khác, không có trần gọi/phút công bố) chỉ nhận phần breaker, không nhận
phần giãn nhịp theo `tier_c.api_calls_per_min`.
"""

from __future__ import annotations

import hashlib
import hmac
import http.client
import json
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError

from tool_d.config.loader import load_tool_d_config, resolve
from tool_d.risk_supervisor import (
    TrangThaiBreaker,
    doc_nguong_breaker,
    ghi_nhan_ket_qua,
    phan_loai_ma_loi,
)

BASE_URL = "https://fapi.binance.com"
SPOT_BASE_URL = "https://api.binance.com"  # TD-0116: chỉ dùng cho phép ĐO latency (H15), không dùng cho dữ liệu/nghiệp vụ — Tool D giao dịch futures
DEFAULT_TIMEOUT_S = 10.0  # R11 — timeout riêng cho từng request, không dựa mặc định thư viện
MAX_MAU_LATENCY = 200  # R5 — trần trên cho `n` của latency_samples_ms(); không ca dùng thật nào (H15 §6.7) cần hơn vài chục mẫu


class BinancePublicApiError(RuntimeError):
    """Lỗi khi gọi endpoint public Binance (mạng, HTTP, hoặc timeout)."""


class BinancePrivateApiError(RuntimeError):
    """Lỗi khi gọi endpoint KÝ (signed) Binance — mạng, HTTP, timeout,
    hoặc sàn từ chối do khoá/chữ ký/tham số sai."""


class BinanceBreakerMoError(BinancePublicApiError):
    """R3 — circuit breaker đang chặn gọi mạng: hoặc `DUNG_HAN` (từng gặp
    HTTP 418, cờ vĩnh viễn cần can thiệp thủ công), hoặc còn trong cửa sổ
    backoff sau nhiều lỗi 429/5xx liên tiếp. KHÔNG gọi mạng khi lỗi này
    xảy ra — gọi tiếp trong lúc đang bị cấm chỉ kéo dài án phạt."""


_trang_thai_breaker = TrangThaiBreaker()
_lan_goi_cuoi_mang_s: float | None = None


def _tran_goi_theo_phut() -> float:
    """N4 — `tier_c.api_calls_per_min` phải đọc từ `tool_d_config.yaml`
    qua `resolve()`, không hardcode, không qua ENV."""
    cfg = load_tool_d_config()
    tran = float(resolve(cfg, "tier_c.api_calls_per_min"))
    if tran <= 0:
        raise BinancePublicApiError(f"tier_c.api_calls_per_min phải > 0, nhận: {tran}")
    return tran


def _kiem_tra_breaker() -> None:
    if _trang_thai_breaker.duoc_phep_goi(now=datetime.now(timezone.utc)):
        return
    if _trang_thai_breaker.dung_han:
        raise BinanceBreakerMoError(
            "circuit breaker đang DUNG_HAN (từng gặp HTTP 418) — cần can "
            "thiệp thủ công, không tự gỡ (§6.6, cùng cấp LIQUIDATED)"
        )
    assert _trang_thai_breaker.thoi_diem_mo is not None  # mo_tam=True luôn kèm mốc mở
    mo_lai = _trang_thai_breaker.thoi_diem_mo + timedelta(seconds=_trang_thai_breaker.backoff_s)
    raise BinanceBreakerMoError(
        f"circuit breaker đang backoff sau {_trang_thai_breaker.so_loi_lien_tiep} lỗi "
        f"liên tiếp — thử lại sau {mo_lai.isoformat()}"
    )


def _cho_nhip_goi() -> None:
    global _lan_goi_cuoi_mang_s
    khoang_toi_thieu = 60.0 / _tran_goi_theo_phut()
    if _lan_goi_cuoi_mang_s is not None:
        con_thieu = khoang_toi_thieu - (time.monotonic() - _lan_goi_cuoi_mang_s)
        if con_thieu > 0:
            time.sleep(con_thieu)
    _lan_goi_cuoi_mang_s = time.monotonic()


def _ghi_nhan_thanh_cong() -> None:
    global _trang_thai_breaker
    _trang_thai_breaker = ghi_nhan_ket_qua(_trang_thai_breaker, None, now=datetime.now(timezone.utc))


def _ghi_nhan_that_bai(*, http_status: int) -> None:
    global _trang_thai_breaker
    loai = phan_loai_ma_loi(http_status=http_status)
    _trang_thai_breaker = ghi_nhan_ket_qua(
        _trang_thai_breaker, loai, now=datetime.now(timezone.utc), nguong=doc_nguong_breaker()
    )


def dat_lai_trang_thai_mang_cho_kiem() -> None:
    """CHỈ dùng trong test — đưa breaker/nhịp gọi về sạch giữa các ca,
    tránh một ca rò trạng thái sang ca sau. State sống ở cấp MODULE (không
    phải một lớp/đối tượng) vì mỗi entrypoint là MỘT process ngắn chạy
    rồi thoát — không có ai khởi tạo lại một "client" giữa các lượt gọi
    trong cùng lần chạy."""
    global _trang_thai_breaker, _lan_goi_cuoi_mang_s
    _trang_thai_breaker = TrangThaiBreaker()
    _lan_goi_cuoi_mang_s = None


def _goi_json_cong_khai(url: str, *, timeout: float) -> Any:
    """R1 (điểm nghẽn duy nhất cho 5 hàm GET/JSON bên dưới) + R2 (giãn
    nhịp) + R3 (circuit breaker) + R4 (phân loại lỗi trước khi ghi nhận).
    """
    _kiem_tra_breaker()
    _cho_nhip_goi()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310
            du_lieu = json.loads(resp.read())
    except HTTPError as exc:
        _ghi_nhan_that_bai(http_status=exc.code)
        raise BinancePublicApiError(f"gọi {url} thất bại: {exc}") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        # Không có http_status để phân loại (đứt mạng/DNS/timeout trước khi
        # có phản hồi) — không ghi nhận vào breaker, đúng chữ `phan_loai_
        # ma_loi()` (chỉ phân loại được khi có http_status HOẶC ma_binance).
        raise BinancePublicApiError(f"gọi {url} thất bại: {exc}") from exc
    _ghi_nhan_thanh_cong()
    return du_lieu


def get_exchange_info(*, timeout: float = DEFAULT_TIMEOUT_S) -> dict:
    """`GET /fapi/v1/exchangeInfo` — metadata mọi hợp đồng (trạng thái,
    ngày lên sàn `onboardDate`, precision, min notional). Dùng cho
    TD-0082 (min notional) và TD-0083 (chốt pool).
    """
    url = f"{BASE_URL}/fapi/v1/exchangeInfo"
    return _goi_json_cong_khai(url, timeout=timeout)


def get_ticker_24hr(*, timeout: float = DEFAULT_TIMEOUT_S) -> list[dict]:
    """`GET /fapi/v1/ticker/24hr` — thống kê 24h MỌI hợp đồng (bao gồm
    `quoteVolume`, dùng làm proxy volume cho tiêu chí (i) §0.3). Không
    truyền `symbol` để lấy TOÀN BỘ trong 1 lệnh gọi (tránh N lệnh gọi
    riêng cho N mã — đúng tinh thần R2/bounded loop).
    """
    url = f"{BASE_URL}/fapi/v1/ticker/24hr"
    return _goi_json_cong_khai(url, timeout=timeout)


def get_ticker_price(*, timeout: float = DEFAULT_TIMEOUT_S) -> list[dict]:
    """`GET /fapi/v1/ticker/price` — giá hiện tại MỌI hợp đồng, payload nhỏ
    hơn nhiều so với `ticker/24hr` (TD-0082: `ticker/24hr` từng timeout ở
    10s khi chỉ cần giá để quy bước lot ra USDT). Một lệnh gọi cho toàn bộ
    (R2/bounded loop).
    """
    url = f"{BASE_URL}/fapi/v1/ticker/price"
    return _goi_json_cong_khai(url, timeout=timeout)


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
    return _goi_json_cong_khai(url, timeout=timeout)


def _sign(params: dict[str, str], secret: str) -> str:
    """HMAC-SHA256 trên chuỗi query — đúng chuẩn ký request của Binance."""
    query = urllib.parse.urlencode(params)
    return hmac.new(secret.encode("utf-8"), query.encode("utf-8"), hashlib.sha256).hexdigest()


def _signed_path(path: str, api_secret: str, extra_params: dict[str, str] | None) -> str:
    """Gắn `timestamp`/`recvWindow`/`signature` vào `path`. Gọi lại cho
    MỖI mẫu đo — Binance từ chối timestamp cũ quá `recvWindow`, nên không
    thể ký một lần rồi dùng lại cho cả loạt."""
    params = dict(extra_params or {})
    params["timestamp"] = str(int(time.time() * 1000))
    params["recvWindow"] = "5000"
    return f"{path}?{urllib.parse.urlencode(params)}&signature={_sign(params, api_secret)}"


def latency_samples_ms(
    *,
    n: int,
    reuse_connection: bool,
    base_url: str = BASE_URL,
    path: str = "/fapi/v1/time",
    method: str = "GET",
    signed: bool = False,
    api_key: str = "",
    api_secret: str = "",
    extra_params: dict[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT_S,
) -> list[float]:
    """H15 (§6.7, TD-0116) — đo `n` mẫu round-trip latency tới Binance.

    🔴 `reuse_connection` là tham số QUAN TRỌNG NHẤT ở đây, không phải
    tuỳ chọn tối ưu vặt:

      • `False` (LẠNH) — mỗi mẫu mở TCP+TLS mới. Đây là latency lần gọi
        đầu sau khi bot vừa khởi động hoặc kết nối vừa đứt.
      • `True` (ẤM) — dùng lại một kết nối cho cả `n` mẫu. Đây mới là
        latency mà bot THẬT thấy khi đang chạy, vì Freqtrade/ccxt giữ
        kết nối sống (persistent session).

    Đo lẫn lộn hai chế độ này cho ra một con số không thuộc về tình
    huống nào — mẫu lạnh cõng thêm bắt tay TLS (thường gấp 2-3 lần),
    nên nếu chỉ đo lạnh sẽ thổi phồng đúng con số đang dùng để đánh giá
    khoảng trống không-SL của D2c (§8.3).

    Cách dùng đúng là đo THEO CẶP trên CÙNG host: một endpoint public
    (không ký) làm đối chứng, một endpoint ký — hiệu giữa hai số mới là
    chi phí auth phía sàn, tách khỏi RTT mạng thuần. So hai số khác host
    (spot vs futures) thì KHÔNG hợp lệ: khác hạ tầng.

    🔴 R5 (bounded loop) — `n` bị chặn trần bởi `MAX_MAU_LATENCY`, và cả
    vòng lặp có HẠN CHÓT TỔNG = `n * timeout` (worst-case nếu mọi mẫu đều
    ăn trọn timeout riêng của nó): vượt hạn chót thì DỪNG và raise, không
    âm thầm trả về danh sách THIẾU mẫu (N6 — không trả số lính canh/dữ
    liệu một phần khi chưa đo đủ).
    """
    if n < 1:
        raise ValueError(f"n phải >= 1, nhận: {n}")
    if n > MAX_MAU_LATENCY:
        raise ValueError(f"n phải <= {MAX_MAU_LATENCY} (R5 — bounded loop), nhận: {n}")
    if signed and not (api_key and api_secret):
        raise ValueError("signed=True cần cả api_key lẫn api_secret")

    host = urllib.parse.urlparse(base_url).netloc
    headers = {"X-MBX-APIKEY": api_key} if signed else {}
    samples: list[float] = []
    han_chot_s = time.monotonic() + n * timeout
    conn = http.client.HTTPSConnection(host, timeout=timeout) if reuse_connection else None
    try:
        for _ in range(n):
            if time.monotonic() > han_chot_s:
                raise BinancePrivateApiError(
                    f"vượt timeout tổng ({n * timeout:.0f}s cho {n} mẫu) — dừng vòng lặp, "
                    f"chỉ thu được {len(samples)}/{n} mẫu (R5, không trả kết quả một phần)"
                )
            req_path = _signed_path(path, api_secret, extra_params) if signed else path
            c = conn or http.client.HTTPSConnection(host, timeout=timeout)
            t0 = time.monotonic()
            try:
                c.request(method, req_path, headers=headers)
                resp = c.getresponse()
                body = resp.read()
                if resp.status != 200:
                    raise BinancePrivateApiError(
                        f"{method} {path} -> HTTP {resp.status}: {body[:300]!r}"
                    )
                samples.append((time.monotonic() - t0) * 1000.0)
            except OSError as exc:
                raise BinancePrivateApiError(f"gọi {host}{path} thất bại: {exc}") from exc
            finally:
                if conn is None:
                    c.close()
    finally:
        if conn is not None:
            conn.close()
    return samples


AGG_TRADES_HOST = "data.binance.vision"


class AggTradesNotFoundError(BinancePublicApiError):
    """Không có dump `aggTrades` cho mã/ngày đó (HTTP 404). Tách riêng khỏi
    lỗi mạng: một ngày không có dump là DỮ KIỆN (mã chưa niêm yết, hoặc
    kho chưa cập nhật), không phải sự cố — bên gọi phải xử tường minh,
    không được lặng lẽ coi như 'không có giao dịch nào'."""


def tai_dump_agg_trades(
    *,
    symbol: str,
    ngay: date,
    thu_muc_cache: Path,
    timeout: float = 120.0,
) -> Path:
    """TD-0162 — tải dump `aggTrades` MỘT NGÀY từ `data.binance.vision`.

    🔴 Vì sao không dùng REST `/fapi/v1/aggTrades`: Binance giới hạn cửa sổ
    tra cứu **2 ngày gần nhất** (`-4166: Search window is restricted to
    recent 2 days only`, kiểm 08/09/2026). Tập CALIB là 2024-06 → 2025-06,
    nên đường REST KHÔNG dùng được cho phép đo này. Kho dump lịch sử là
    nguồn duy nhất — cùng nguồn đã dùng ở TD-0095 cho mã đã huỷ niêm yết
    (`docs/decisions/DR-D1-01-nguon-danh-sach-lich-su.md`).

    Đặt ở đây, không phải module riêng, vì **R1 Single Egress**: đây phải
    là module DUY NHẤT gọi thẳng ra mạng tới Binance — kể cả tới host phụ
    `data.binance.vision`.

    Có cache trên đĩa: đã tải rồi thì KHÔNG tải lại. Dump ngày là bất biến
    (dữ liệu lịch sử đã đóng), nên cache không cần vân tay như cache WFO
    (TD-0143) — nhưng cũng vì thế, **đừng dùng hàm này cho ngày HÔM NAY**:
    ngày chưa đóng thì dump chưa đầy đủ.
    """
    ten = f"{symbol}-aggTrades-{ngay.isoformat()}.zip"
    dich = thu_muc_cache / ten
    if dich.exists() and dich.stat().st_size > 0:
        return dich

    duong_dan = f"/data/futures/um/daily/aggTrades/{symbol}/{ten}"
    # R3 — CÙNG breaker với `_goi_json_cong_khai` (một hạ tầng Binance),
    # nhưng KHÔNG áp `tier_c.api_calls_per_min` — đó là trần weight công
    # bố riêng cho `fapi.binance.com`, không có trần tương đương công bố
    # cho `data.binance.vision`.
    _kiem_tra_breaker()
    conn = http.client.HTTPSConnection(AGG_TRADES_HOST, timeout=timeout)
    try:
        conn.request("GET", duong_dan)
        resp = conn.getresponse()
        if resp.status == 404:
            resp.read()
            raise AggTradesNotFoundError(
                f"không có dump aggTrades cho {symbol} ngày {ngay} "
                f"(HTTP 404 tại {AGG_TRADES_HOST}{duong_dan})"
            )
        if resp.status != 200:
            _ghi_nhan_that_bai(http_status=resp.status)
            raise BinancePublicApiError(
                f"tải {AGG_TRADES_HOST}{duong_dan} thất bại: HTTP {resp.status}"
            )
        noi_dung = resp.read()
        _ghi_nhan_thanh_cong()
    except OSError as exc:
        raise BinancePublicApiError(f"tải {AGG_TRADES_HOST}{duong_dan} thất bại: {exc}") from exc
    finally:
        conn.close()

    thu_muc_cache.mkdir(parents=True, exist_ok=True)
    tam = dich.with_suffix(".zip.dang-tai")
    tam.write_bytes(noi_dung)
    tam.replace(dich)  # đổi tên nguyên tử: không để lại file tải dở mang tên thật
    return dich


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
    return _goi_json_cong_khai(url, timeout=timeout)
