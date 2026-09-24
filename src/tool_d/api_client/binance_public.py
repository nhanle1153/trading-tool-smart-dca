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

🔴 TD-0242 — `validate_credentials_for_live()` là hàm THUẦN, chưa nối vào
entrypoint nào (không có entrypoint thật nào đặt lệnh thật hôm nay — 8
entrypoint E1-E8 hiện có đều KHÔNG cần credential ký; `latency_samples_ms`
nhận `api_key`/`api_secret` trực tiếp từ tham số, không tự đọc ENV). Đúng
khuôn đã dùng ở `risk_supervisor.py` (TD-0196): hàm thuần trước, nối vào
một entrypoint/tiến trình thật là việc SAU khi D10-D12 (live) thật sự
được viết — có phép kiểm để không bị quên tới lúc đó.
"""

from __future__ import annotations

import hashlib
import hmac
import http.client
import io
import json
import os
import time
import urllib.parse
import urllib.request
import zipfile
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree
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


class BinanceCredentialsMissingError(BinancePrivateApiError):
    """TD-0242 — thiếu `BINANCE_API_KEY`/`BINANCE_API_SECRET` lúc SẮP gọi
    endpoint KÝ (đặt lệnh thật). Tách riêng khỏi mọi lỗi trên: những lỗi đó
    xảy ra SAU khi đã gửi request (mạng, HTTP, sàn từ chối chữ ký/tham số);
    lỗi này xảy ra TRƯỚC khi gửi bất cứ gì — 0 byte ra mạng. Gộp chung hai
    loại sẽ khiến người vận hành đi kiểm tra trạng thái sàn/mạng thay vì
    kiểm tra `.env` cục bộ, đúng thứ Tiêu chí XONG của TD-0242 cấm ("không
    phải một lỗi mạng trông giống sự cố sàn")."""


ENV_BINANCE_API_KEY = "BINANCE_API_KEY"
ENV_BINANCE_API_SECRET = "BINANCE_API_SECRET"

# Exit code riêng cho "thiếu credential lúc cần gọi endpoint ký" — nối tiếp
# dải exit code riêng của dự án (86 guard · 87 cache · 88-91 lockbox · 92
# audit · 94-98 các cổng/entrypoint khác) — 99 còn trống. Entrypoint tương
# lai (D10-D12, chưa viết — không có entrypoint thứ 9, N3) dùng hằng số
# này khi bắt `BinanceCredentialsMissingError` ở `main()`.
EXIT_MISSING_API_CREDENTIALS = 99


def validate_credentials_for_live(*, env: Mapping[str, str] | None = None) -> tuple[str, str]:
    """Fail-closed TRƯỚC khi một entrypoint cần đặt lệnh thật (dry_run=false,
    §6.9.5) gọi endpoint KÝ — gọi hàm này Ở ĐẦU, cùng tinh thần `measurement_
    guard()` (N5): kiểm TRƯỚC việc tốn thời gian/mạng, không bọc trong
    decorator để không phải suy luận khi kiểm bằng AST.

    Rỗng tính như thiếu — cùng quy ước đã có ở `latency_samples_ms`
    (`signed and not (api_key and api_secret)`), không tạo hai chuẩn khác
    nhau cho cùng một khái niệm "thiếu key" trong cùng module.

    🔴 KHÔNG đọc `tool_d_config.yaml` — đây là bí mật vận hành (N4/§0d.4:
    "env chỉ cho vận hành, khoá/mở, chế độ, đường dẫn"), không phải tham
    số Tầng B/C; nguồn duy nhất là biến môi trường thật lúc chạy, không
    phải file cấu hình đã commit (`config/freqtrade/config.json` CỐ Ý giữ
    `api_key`/`secret` rỗng — TD-0242, R10).

    Trả về `(api_key, api_secret)` khi đủ cả hai, để bên gọi không phải
    đọc lại `os.environ` một lần nữa (tránh lệch nếu biến đổi giữa hai lần
    đọc — dù hiếm, đọc MỘT LẦN vẫn là kỷ luật an toàn hơn).

    🔴 **Phạm vi, đọc đúng (bổ sung sau khi `DR-D11-02` đổi D10 sang lệnh
    LIVE TỐI THIỂU — phiên `-3f` nêu, 13/09/2026):**

    1. Hàm này CHỈ kiểm SỰ HIỆN DIỆN (biến rỗng/vắng mặt) — 0 byte ra
       mạng, nên KHÔNG thể biết khoá sai/hết hạn/thiếu quyền Futures/bị
       khoá IP. Đó là lỗi xảy ra SAU khi đã gửi request, thuộc phạm vi
       `phan_loai_ma_loi()` (`risk_supervisor.py`) đọc từ HTTP status/mã
       Binance thật — hai hàm phủ hai THỜI ĐIỂM khác nhau (trước/sau khi
       gửi), KHÔNG phải hai đường đọc lỗi song song cho cùng một sự kiện.
       Đừng gộp: gộp sẽ làm hàm này phải đoán một điều nó không có dữ
       liệu để biết.
    2. **Chỉ được gọi từ `main()` của entrypoint (điểm vào tiến trình),
       KHÔNG BAO GIỜ từ bên trong một callback chiến lược** (`custom_stake_
       amount`, `confirm_trade_entry`, `custom_stoploss`...). Freqtrade bọc
       mọi callback bằng `strategy_safe_wrapper`, hạ MỌI exception xuống
       WARNING rồi tiếp tục chạy — `MT-16` (vii) đã đo đúng cơ chế này nuốt
       `SizingError` fail-closed 12 lần trong một lượt. Gọi hàm này từ một
       callback = tự đặt chốt fail-closed vào đúng chỗ nó chắc chắn bị nuốt.

       🔑 Ràng buộc này hôm nay là LỜI KHAI (docstring), chưa phải BẰNG
       CHỨNG (N12 mục 3: một dòng mô tả cũng là lời khai, không phải máy
       canh) — cùng hình dạng đã cắn dự án ở `ZoneAbsorption.py:224`
       ("chỉ được siết, không nới", 0 dòng thi hành, phiên `-3f` chỉ ra
       13/09/2026). Thiết kế gợi ý cho phép kiểm AST đi kèm khi có call
       site thật (viết TRƯỚC khi có call site sẽ là PASS RỖNG nếu thiếu
       teeth test bằng nguồn giả — không viết ở đây):
         - Theo khuôn `find_guard_violation()` (`guard_ast_check.py`), NHƯNG
           dùng ALLOW-list thay vì deny-list callback (bài học MT-08: danh
           sách CHO PHÉP an toàn hơn danh sách CẤM) — `ast.walk` tìm mọi
           `Call` gọi `validate_credentials_for_live`; với MỖI lời gọi, xác
           nhận `FunctionDef` bao nó tên là `main` (không phải: không nằm
           trong danh sách callback bị cấm).
         - Kiểm-có-răng bằng NGUỒN GIẢ (chuỗi văn bản qua `ast.parse`,
           không cần entrypoint/strategy thật): (a) lời gọi trong
           `def main():` → sạch; (b) lời gọi trong `def custom_stoploss(
           self, ...):` → đúng 1 vi phạm.
    """
    nguon = env if env is not None else os.environ
    api_key = nguon.get(ENV_BINANCE_API_KEY, "")
    api_secret = nguon.get(ENV_BINANCE_API_SECRET, "")
    thieu = [
        ten
        for ten, gia_tri in (
            (ENV_BINANCE_API_KEY, api_key),
            (ENV_BINANCE_API_SECRET, api_secret),
        )
        if not gia_tri
    ]
    if thieu:
        raise BinanceCredentialsMissingError(
            f"Thiếu biến môi trường {', '.join(thieu)} — đây là lỗi CẤU HÌNH cục bộ, "
            "KHÔNG phải sự cố mạng/sàn Binance. Đặt trong `.env.binance` (tên biến xem "
            "`.env.example`) trước khi chạy entrypoint cần đặt lệnh thật; KHÔNG BAO GIỜ "
            "commit giá trị thật vào `config/freqtrade/config.json`."
        )
    return api_key, api_secret


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


def trang_thai_breaker_hien_tai() -> TrangThaiBreaker:
    """TD-0241 (`DR-D11-03`) — đọc (KHÔNG sửa) trạng thái breaker hiện tại
    của tiến trình. Breaker ở đây là biến MODULE, sống trong RAM của MỘT
    tiến trình (đúng comment ở `dat_lai_trang_thai_mang_cho_kiem`) — tầng
    gọi cần BỀN VỮNG HOÁ nó qua khởi động lại (bài học `MT-40`/`MT-41`)
    phải tự đọc bằng hàm này rồi ghi ra đĩa (`risk_supervisor.luu_trang_thai`),
    vì module này không tự ghi file — không phải việc của R1/R2/R3/R4."""
    return _trang_thai_breaker


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


def _goi_json_ky(
    path: str,
    *,
    api_key: str,
    api_secret: str,
    extra_params: dict[str, str] | None = None,
    base_url: str = BASE_URL,
    timeout: float = DEFAULT_TIMEOUT_S,
) -> Any:
    """TD-0241 (DR-D11-03) — điểm nghẽn cho các GET KÝ đọc margin/vị thế/
    thanh lý (Risk Supervisor, §6.6). Đi qua ĐÚNG cùng breaker/giãn nhịp/
    phân loại lỗi với `_goi_json_cong_khai` (R1/R2/R3/R4) — KHÁC
    `latency_samples_ms`, hàm đó CỐ Ý đứng ngoài vì đo RTT thuần (xem
    docstring của nó). Đọc margin/vị thế là traffic VẬN HÀNH thật, không
    phải một phép đo latency, nên không được đứng ngoài breaker/rate-limit.
    """
    _kiem_tra_breaker()
    _cho_nhip_goi()
    url = f"{base_url}{_signed_path(path, api_secret, extra_params)}"
    req = urllib.request.Request(url, headers={"X-MBX-APIKEY": api_key})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            du_lieu = json.loads(resp.read())
    except HTTPError as exc:
        _ghi_nhan_that_bai(http_status=exc.code)
        raise BinancePrivateApiError(f"gọi {path} thất bại: {exc}") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        # Không có http_status để phân loại (đứt mạng/DNS/timeout trước khi
        # có phản hồi) — không ghi nhận vào breaker, cùng chữ `_goi_json_cong_khai`.
        raise BinancePrivateApiError(f"gọi {path} thất bại: {exc}") from exc
    _ghi_nhan_thanh_cong()
    return du_lieu


def get_account_info(*, api_key: str, api_secret: str, timeout: float = DEFAULT_TIMEOUT_S) -> dict:
    """`GET /fapi/v2/account` — margin/balance tổng (TD-0241, Risk Supervisor
    §6.6). Trường dùng ở tầng gọi: `totalMarginBalance`, `totalMaintMargin`,
    `availableBalance`, `positions[].{maintMargin,initialMargin,
    unrealizedProfit,isolated}` (xác nhận qua tài liệu Binance, `DR-D11-03`).
    """
    return _goi_json_ky("/fapi/v2/account", api_key=api_key, api_secret=api_secret, timeout=timeout)


def get_position_risk(*, api_key: str, api_secret: str, timeout: float = DEFAULT_TIMEOUT_S) -> list[dict]:
    """`GET /fapi/v2/positionRisk` — vị thế + giá thanh lý ước tính theo
    từng symbol (TD-0241)."""
    return _goi_json_ky("/fapi/v2/positionRisk", api_key=api_key, api_secret=api_secret, timeout=timeout)


def get_force_orders(
    *,
    api_key: str,
    api_secret: str,
    start_time_ms: int | None = None,
    timeout: float = DEFAULT_TIMEOUT_S,
) -> list[dict]:
    """`GET /fapi/v1/forceOrders?autoCloseType=LIQUIDATION` — lệnh bị THANH
    LÝ thật (TD-0241, đóng TODO #1 của `risk_supervisor.py`). `autoCloseType`
    là tham số REQUEST lọc phía server, KHÔNG phải trường trong response —
    bất kỳ phần tử nào trả về ⇒ đã có lệnh bị thanh lý (`DR-D11-03` §2.4,
    xác nhận qua mã nguồn `ccxt/binance.py:13351` bundled trong image, không
    đoán qua trang docs render-JS không đọc được).
    """
    extra: dict[str, str] = {"autoCloseType": "LIQUIDATION"}
    if start_time_ms is not None:
        extra["startTime"] = str(start_time_ms)
    return _goi_json_ky(
        "/fapi/v1/forceOrders", api_key=api_key, api_secret=api_secret, extra_params=extra, timeout=timeout
    )


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


def _ma_url(x: str) -> str:
    """Mã hoá phần trăm một đoạn đường dẫn URL.

    🔴 **Không phải phòng xa — đã nổ thật, và nó SỐNG ở cả hàm bên cạnh.**
    `http.client` đòi dòng request thuần ASCII (`_encode_request` gọi
    `request.encode("ascii")`), nên một ký tự ngoài ASCII trong đường dẫn làm
    nó raise `UnicodeEncodeError` **trước khi** gửi đi. Mà sàn có mã tên phi
    ASCII: `config/pool.yaml` có `币安人生USDT` **trong chính pool 102 mã giao
    dịch**, và kho lưu trữ còn `我踏马来了USDT` · `牛来USDT` · `龙虾USDT` ·
    `哈基米USDT`.

    ⇒ `tai_dump_agg_trades()` (DR-015 Bước 2) mang **cùng** lỗi này từ TD-0162
    và chưa nổ chỉ vì chưa lần nào chạm đúng mã đó. Vá cả hai chỗ, không vá
    một chỗ rồi để chỗ kia — biết mà để lại là chọn để nó nổ lần sau.
    """
    return urllib.parse.quote(x, safe="")


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

    duong_dan = f"/data/futures/um/daily/aggTrades/{_ma_url(symbol)}/{_ma_url(ten)}"
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


# Kho lưu trữ tĩnh của Binance đứng sau một bucket S3 — liệt kê được bằng
# ListObjects (v1) với `prefix`/`delimiter`/`marker`. CÙNG host với
# `tai_dump_agg_trades`, nên dùng lại đúng hằng `AGG_TRADES_HOST`.
KHO_LUU_TRU_ENDPOINT = "s3-ap-northeast-1.amazonaws.com"
KHO_LUU_TRU_BUCKET = AGG_TRADES_HOST

# R5 — vòng lặp CÓ BIÊN. Mỗi trang tối đa 1000 khoá; 500 trang = 500.000
# khoá, dư sức cho mọi prefix của kho này. Vượt trần ⇒ RAISE, KHÔNG cắt
# bớt im lặng: một danh sách bị cắt ngắn mà không ai biết đọc thành "kho
# chỉ có thế", tức im lặng theo chiều "không thiếu gì" (N6).
TRAN_TRANG_LIET_KE = 500

_NS_S3 = "{http://s3.amazonaws.com/doc/2006-03-01/}"


class KhoLuuTruError(BinancePublicApiError):
    """Liệt kê kho lưu trữ thất bại.

    CỐ Ý là exception chứ không phải danh sách rỗng: ở phép đo TD-0230,
    "rỗng" đọc thành *"không mã nào bị thiếu khỏi pool"* — tức im lặng
    đúng theo chiều PASS, chiều mà không cổng nào của dự án bắt được.
    """


@dataclass(frozen=True)
class KetQuaLietKe:
    """Kết quả một lượt liệt kê. `so_trang >= 1` là bằng chứng đã có phản
    hồi THẬT, nên `khoa == [] and thu_muc == []` phân biệt được với lỗi:
    rỗng-thật thì `so_trang >= 1`, lỗi thì đã raise từ trước."""

    prefix: str
    khoa: tuple[str, ...]
    thu_muc: tuple[str, ...]
    so_trang: int


def _doc_xml_kho_luu_tru(duong_dan: str, *, timeout: float) -> Any:
    """Một request tới bucket. R3 — dùng CÙNG breaker với các hàm khác
    (một hạ tầng Binance); KHÔNG áp `tier_c.api_calls_per_min` vì trần đó
    là trần weight công bố riêng cho `fapi.binance.com`, đúng như
    `tai_dump_agg_trades` đã ghi."""
    _kiem_tra_breaker()
    conn = http.client.HTTPSConnection(KHO_LUU_TRU_ENDPOINT, timeout=timeout)
    try:
        conn.request("GET", duong_dan)
        resp = conn.getresponse()
        if resp.status != 200:
            resp.read()
            _ghi_nhan_that_bai(http_status=resp.status)
            raise KhoLuuTruError(
                f"liệt kê {KHO_LUU_TRU_ENDPOINT}{duong_dan} thất bại: HTTP {resp.status}"
            )
        noi_dung = resp.read()
        _ghi_nhan_thanh_cong()
    except OSError as exc:
        raise KhoLuuTruError(
            f"liệt kê {KHO_LUU_TRU_ENDPOINT}{duong_dan} thất bại: {exc}"
        ) from exc
    finally:
        conn.close()
    try:
        return ElementTree.fromstring(noi_dung)
    except ElementTree.ParseError as exc:
        raise KhoLuuTruError(
            f"phản hồi của {KHO_LUU_TRU_ENDPOINT}{duong_dan} không phải XML hợp lệ: {exc}"
        ) from exc


def liet_ke_kho_luu_tru(
    *,
    prefix: str,
    delimiter: str | None = None,
    timeout: float = 30.0,
    tran_trang: int = TRAN_TRANG_LIET_KE,
) -> KetQuaLietKe:
    """TD-0230 — liệt kê kho tĩnh `data.binance.vision` qua S3 ListObjects.

    Đây là nguồn mà `DR-D1-01` §1-2 đã dùng thật để lấy danh sách mã đã
    huỷ niêm yết và mốc lên/rời sàn của từng mã: kho KHÔNG xoá thư mục của
    mã đã huỷ, khác `exchangeInfo` (chỉ phản ánh trạng thái HIỆN TẠI).

    Đặt ở đây, không phải module riêng — **R1 Single Egress**, cùng lý do
    `tai_dump_agg_trades` đã ghi.

    🔴 **Phân trang là phần BẮT BUỘC, không phải tối ưu.** Mỗi trang tối
    đa 1000 mục; `DR-D1-01` §1 đã nêu đúng chỗ này (*"phân trang qua
    `NextMarker` vì mỗi trang giới hạn 1000 mục"*). Dừng ở trang đầu cho
    một câu trả lời **nhỏ hơn thực tế** — và ở phép đo TD-0230, nhỏ hơn
    thực tế nghĩa là *"pool thiếu ít mã hơn"*, tức lệch đúng chiều PASS.

    `NextMarker` chỉ được bucket trả khi có `delimiter`; không có
    `delimiter` thì marker của trang sau là **khoá cuối** của trang này
    (đúng chuẩn ListObjects v1). Xử cả hai, không giả định một dạng.
    """
    if not prefix:
        raise KhoLuuTruError("prefix rỗng — sẽ liệt kê TOÀN BỘ bucket, không cho phép")
    if tran_trang < 1:
        raise KhoLuuTruError(f"tran_trang phải >= 1, nhận: {tran_trang}")

    khoa: list[str] = []
    thu_muc: list[str] = []
    marker: str | None = None
    so_trang = 0

    while True:
        tham_so: dict[str, str] = {"prefix": prefix}
        if delimiter is not None:
            tham_so["delimiter"] = delimiter
        if marker is not None:
            tham_so["marker"] = marker
        duong_dan = f"/{KHO_LUU_TRU_BUCKET}/?" + urllib.parse.urlencode(tham_so)

        goc = _doc_xml_kho_luu_tru(duong_dan, timeout=timeout)
        so_trang += 1

        # `Key` chỉ xuất hiện trong `Contents`, `Prefix` con của
        # `CommonPrefixes` chỉ xuất hiện ở đó — nhưng `Prefix` cũng là thẻ
        # cấp GỐC (echo lại prefix đã gửi), nên KHÔNG được `iter("Prefix")`
        # thẳng: sẽ hút luôn thẻ gốc và sinh một "thư mục" giả.
        khoa_trang = [
            k.text for c in goc.iter(f"{_NS_S3}Contents")
            for k in c.findall(f"{_NS_S3}Key") if k.text
        ]
        khoa.extend(khoa_trang)
        thu_muc.extend(
            p.text for cp in goc.iter(f"{_NS_S3}CommonPrefixes")
            for p in cp.findall(f"{_NS_S3}Prefix") if p.text
        )

        bi_cat = goc.findtext(f"{_NS_S3}IsTruncated", default="false").strip().lower()
        if bi_cat != "true":
            break
        if so_trang >= tran_trang:
            raise KhoLuuTruError(
                f"prefix {prefix!r} còn bị cắt sau {so_trang} trang (trần "
                f"{tran_trang}) — KHÔNG trả danh sách thiếu; siết prefix hoặc "
                "nâng trần một cách tường minh"
            )
        tiep = goc.findtext(f"{_NS_S3}NextMarker")
        if tiep:
            marker = tiep
        elif thu_muc and delimiter is not None:
            marker = thu_muc[-1]
        elif khoa_trang:
            marker = khoa_trang[-1]
        else:
            raise KhoLuuTruError(
                f"prefix {prefix!r}: bucket báo IsTruncated=true nhưng không có "
                "NextMarker và trang rỗng — không suy ra được marker kế tiếp"
            )

    return KetQuaLietKe(
        prefix=prefix,
        khoa=tuple(khoa),
        thu_muc=tuple(thu_muc),
        so_trang=so_trang,
    )


class NenThangKhongCoError(BinancePublicApiError):
    """Kho không có file nến tháng đó cho mã đó (HTTP 404).

    Tách riêng khỏi lỗi mạng, cùng lý do `AggTradesNotFoundError`: một tháng
    không có file là **DỮ KIỆN** (mã chưa lên sàn, hoặc đã rời sàn), không
    phải sự cố. Bên gọi phải xử tường minh — coi nó như *"volume = 0"* là
    gộp *"không đo được"* với *"đo được và bằng 0"*, đúng thứ N6 cấm.
    """


# Nến Binance: 0 open_time · 1 open · 2 high · 3 low · 4 close · 5 volume
# · 6 close_time · 7 QUOTE_VOLUME · 8 count · 9 taker_buy_volume
# · 10 taker_buy_quote_volume · 11 ignore
_COT_OPEN_TIME = 0
_COT_QUOTE_VOLUME = 7

# 🔴 Binance đã ĐỔI ĐƠN VỊ mốc thời gian trong kho lưu trữ: file cũ ghi
# MILLI-giây, file mới ghi MICRO-giây. Không phát hiện được thì mọi mốc đọc
# lệch ~1000 lần và rơi về năm 1970 — mà 1970 thì "trước mọi mốc T", tức
# lệch đúng theo chiều "mã nào cũng đã tồn tại". Ngưỡng: 1e14 ms ≈ năm 5138,
# nên mọi giá trị lớn hơn thế chắc chắn là micro-giây.
_NGUONG_MICRO_GIAY = 1e14


def doc_quote_volume_1d_thang(
    *,
    symbol: str,
    nam: int,
    thang: int,
    timeout: float = 60.0,
) -> dict[date, float]:
    """TD-0231 — đọc `quote_volume` từng NGÀY của một THÁNG, từ kho lưu trữ.

    Dùng để dựng lại `SymbolStat.quote_volume_24h` **TẠI một mốc `t` trong quá
    khứ** — chính thứ docstring `pool.py` của `pairlist_point_in_time()` đòi
    bên gọi tự cung cấp, và chưa từng có ai cung cấp.

    Đặt ở đây, không phải module riêng — **R1 Single Egress**, cùng lý do
    `tai_dump_agg_trades()` đã ghi.

    Đọc nhánh **monthly** (≈30 hàng/file) thay vì `daily/` (1 hàng/file): một
    lượt tải là đủ cho cả tháng.

    🔴 **Fail-closed ba chỗ:**

    1. HTTP 404 ⇒ `NenThangKhongCoError` — dữ kiện, không phải 0.
    2. Mốc thời gian đọc ra **không nằm trong đúng tháng đã hỏi** ⇒ raise.
       Đây là chốt canh **lẫn đơn vị** (milli/micro-giây): lệch đơn vị đẩy
       mọi mốc về 1970, mà 1970 *"trước mọi mốc T"* nghĩa là *"mã nào cũng
       đã tồn tại"* — lệch đúng chiều làm rổ trông đầy hơn thực tế.
    3. `quote_volume` không parse được ⇒ raise, không bỏ qua hàng đó.
    """
    ten = f"{symbol}-1d-{nam:04d}-{thang:02d}.zip"
    duong_dan = (
        f"/data/futures/um/monthly/klines/{_ma_url(symbol)}/1d/{_ma_url(ten)}"
    )

    _kiem_tra_breaker()
    conn = http.client.HTTPSConnection(AGG_TRADES_HOST, timeout=timeout)
    try:
        conn.request("GET", duong_dan)
        resp = conn.getresponse()
        if resp.status == 404:
            resp.read()
            raise NenThangKhongCoError(
                f"kho không có {ten} (HTTP 404 tại {AGG_TRADES_HOST}{duong_dan})"
            )
        if resp.status != 200:
            resp.read()
            _ghi_nhan_that_bai(http_status=resp.status)
            raise KhoLuuTruError(
                f"tải {AGG_TRADES_HOST}{duong_dan} thất bại: HTTP {resp.status}"
            )
        noi_dung = resp.read()
        _ghi_nhan_thanh_cong()
    except OSError as exc:
        raise KhoLuuTruError(
            f"tải {AGG_TRADES_HOST}{duong_dan} thất bại: {exc}"
        ) from exc
    finally:
        conn.close()

    try:
        with zipfile.ZipFile(io.BytesIO(noi_dung)) as z:
            ten_csv = z.namelist()[0]
            tho = z.read(ten_csv).decode("utf-8")
    except (zipfile.BadZipFile, IndexError, UnicodeDecodeError) as exc:
        raise KhoLuuTruError(f"{ten} không giải nén được: {exc}") from exc

    ket_qua: dict[date, float] = {}
    for dong in tho.splitlines():
        dong = dong.strip()
        if not dong:
            continue
        o = dong.split(",")
        if len(o) <= _COT_QUOTE_VOLUME:
            raise KhoLuuTruError(f"{ten}: hàng thiếu cột — {dong[:80]!r}")
        try:
            moc_tho = float(o[_COT_OPEN_TIME])
        except ValueError:
            # Hàng tiêu đề của file mới — bỏ qua đúng hàng đó, không bỏ file.
            continue
        chia = 1_000_000.0 if moc_tho > _NGUONG_MICRO_GIAY else 1_000.0
        ngay = datetime.fromtimestamp(moc_tho / chia, tz=timezone.utc).date()
        if (ngay.year, ngay.month) != (nam, thang):
            raise KhoLuuTruError(
                f"{ten}: mốc {moc_tho!r} đọc ra {ngay.isoformat()}, không nằm "
                f"trong tháng {nam:04d}-{thang:02d} — nghi LẪN ĐƠN VỊ "
                "(milli/micro-giây). DỪNG, không trả số sai đơn vị."
            )
        try:
            ket_qua[ngay] = float(o[_COT_QUOTE_VOLUME])
        except ValueError as exc:
            raise KhoLuuTruError(
                f"{ten}: quote_volume không đọc được ở {ngay}: {o[_COT_QUOTE_VOLUME]!r}"
            ) from exc

    if not ket_qua:
        raise KhoLuuTruError(f"{ten}: giải nén được nhưng 0 hàng đọc được")
    return ket_qua


def doc_quote_volume_1d_ngay(
    *,
    symbol: str,
    ngay: date,
    timeout: float = 60.0,
    hom_nay: date | None = None,
) -> dict[date, float]:
    """TD-0391 (`DR-XAC-NHAN-01` §9) — `quote_volume` của ĐÚNG MỘT ngày UTC, từ kho NGÀY.

    Dùng cho rổ `XAC_NHAN` tại ngày CHỌN: kho THÁNG của tháng đó chỉ có sau khi hết tháng, kho NGÀY có từ
    hôm sau (chủ dự án chọn, 24/09/2026). Trả CÙNG hình `{ngày: quote_volume}` với
    `doc_quote_volume_1d_thang()` để `dung_ro_tai_moc()` dùng lại nguyên. R1: nằm ở module này, cùng
    breaker R3, KHÔNG áp `tier_c.api_calls_per_min` (trần của `fapi.binance.com`).

    🔴 Fail-closed, cùng tinh thần bản tháng:
    1. `ngay` ≥ hôm nay (UTC) ⇒ `ValueError`, KHÔNG gọi mạng — file ngày chưa đóng thì volume thiếu.
    2. HTTP 404 ⇒ `NenThangKhongCoError` — dữ kiện (mã không giao dịch ngày đó), không phải 0.
    3. Mốc của hàng khác `ngay` (lẫn đơn vị milli/micro-giây, hoặc file sai) ⇒ `KhoLuuTruError`.
    4. Không đúng MỘT hàng dữ liệu, hoặc `quote_volume` không đọc được ⇒ `KhoLuuTruError`.
    """
    hom_nay = hom_nay or datetime.now(timezone.utc).date()
    if ngay >= hom_nay:
        raise ValueError(f"ngày {ngay} chưa đóng (hôm nay UTC {hom_nay}) — file ngày chưa đầy đủ, không đọc")
    ten = f"{symbol}-1d-{ngay.isoformat()}.zip"
    duong_dan = f"/data/futures/um/daily/klines/{_ma_url(symbol)}/1d/{_ma_url(ten)}"

    _kiem_tra_breaker()
    conn = http.client.HTTPSConnection(AGG_TRADES_HOST, timeout=timeout)
    try:
        conn.request("GET", duong_dan)
        resp = conn.getresponse()
        if resp.status == 404:
            resp.read()
            raise NenThangKhongCoError(f"kho không có {ten} (HTTP 404 tại {AGG_TRADES_HOST}{duong_dan})")
        if resp.status != 200:
            resp.read()
            _ghi_nhan_that_bai(http_status=resp.status)
            raise KhoLuuTruError(f"tải {AGG_TRADES_HOST}{duong_dan} thất bại: HTTP {resp.status}")
        noi_dung = resp.read()
        _ghi_nhan_thanh_cong()
    except OSError as exc:
        raise KhoLuuTruError(f"tải {AGG_TRADES_HOST}{duong_dan} thất bại: {exc}") from exc
    finally:
        conn.close()

    try:
        with zipfile.ZipFile(io.BytesIO(noi_dung)) as z:
            tho = z.read(z.namelist()[0]).decode("utf-8")
    except (zipfile.BadZipFile, IndexError, UnicodeDecodeError) as exc:
        raise KhoLuuTruError(f"{ten} không giải nén được: {exc}") from exc

    ket_qua: dict[date, float] = {}
    so_hang = 0
    for dong in tho.splitlines():
        o = dong.strip().split(",")
        if o == [""]:
            continue
        if len(o) <= _COT_QUOTE_VOLUME:
            raise KhoLuuTruError(f"{ten}: hàng thiếu cột — {dong[:80]!r}")
        try:
            moc_tho = float(o[_COT_OPEN_TIME])
        except ValueError:
            continue  # hàng tiêu đề
        chia = 1_000_000.0 if moc_tho > _NGUONG_MICRO_GIAY else 1_000.0
        ngay_hang = datetime.fromtimestamp(moc_tho / chia, tz=timezone.utc).date()
        if ngay_hang != ngay:
            raise KhoLuuTruError(
                f"{ten}: mốc {moc_tho!r} đọc ra {ngay_hang.isoformat()}, không phải {ngay.isoformat()} — "
                "nghi LẪN ĐƠN VỊ hoặc sai file. DỪNG, không trả số."
            )
        try:
            ket_qua[ngay_hang] = float(o[_COT_QUOTE_VOLUME])
        except ValueError as exc:
            raise KhoLuuTruError(f"{ten}: quote_volume không đọc được: {o[_COT_QUOTE_VOLUME]!r}") from exc
        so_hang += 1
    if so_hang != 1:
        raise KhoLuuTruError(f"{ten}: {so_hang} hàng dữ liệu cho một file ngày (cần đúng 1)")
    return ket_qua


#: TD-0247 (`DR-D1-03`) — ba loại dữ liệu tháng của kho cần cho một mã đã huỷ
#: niêm yết (Freqtrade `download-data` không tải được mã không còn trên sàn).
LOAI_KHO_THANG = ("klines", "markPriceKlines", "fundingRate")


def doc_csv_thang_kho(
    *,
    loai: str,
    symbol: str,
    nam: int,
    thang: int,
    khung: str | None = None,
    timeout: float = 120.0,
) -> list[list[str]]:
    """TD-0247 — đọc NGUYÊN các hàng CSV của một file tháng trong kho lưu trữ.

    `loai` ∈ `LOAI_KHO_THANG`. `klines`/`markPriceKlines` cần `khung` (`5m`,
    `1h`…); `fundingRate` không có khung. Trả các hàng đã tách cột, BỎ hàng
    tiêu đề (hàng mà cột đầu không phải số). Chuyển sang định dạng Freqtrade là
    việc của `tool_d.data.kho_luu_tru` (logic thuần, test được không cần mạng).

    Cùng chỗ với `doc_quote_volume_1d_thang()` — **R1 Single Egress**.

    🔴 Fail-closed: 404 ⇒ `NenThangKhongCoError` (dữ kiện, không phải 0);
    HTTP khác / mạng / zip hỏng / 0 hàng ⇒ `KhoLuuTruError`.
    """
    if loai not in LOAI_KHO_THANG:
        raise ValueError(f"loai {loai!r} không thuộc {LOAI_KHO_THANG}")
    if loai == "fundingRate":
        ten = f"{symbol}-fundingRate-{nam:04d}-{thang:02d}.zip"
        duong_dan = f"/data/futures/um/monthly/fundingRate/{_ma_url(symbol)}/{_ma_url(ten)}"
    else:
        if not khung:
            raise ValueError(f"loai {loai!r} cần khung")
        ten = f"{symbol}-{khung}-{nam:04d}-{thang:02d}.zip"
        duong_dan = f"/data/futures/um/monthly/{loai}/{_ma_url(symbol)}/{khung}/{_ma_url(ten)}"

    _kiem_tra_breaker()
    _cho_nhip_goi()
    conn = http.client.HTTPSConnection(AGG_TRADES_HOST, timeout=timeout)
    try:
        conn.request("GET", duong_dan)
        resp = conn.getresponse()
        if resp.status == 404:
            resp.read()
            raise NenThangKhongCoError(f"kho không có {ten} (HTTP 404 tại {AGG_TRADES_HOST}{duong_dan})")
        if resp.status != 200:
            resp.read()
            _ghi_nhan_that_bai(http_status=resp.status)
            raise KhoLuuTruError(f"tải {AGG_TRADES_HOST}{duong_dan} thất bại: HTTP {resp.status}")
        noi_dung = resp.read()
        _ghi_nhan_thanh_cong()
    except OSError as exc:
        raise KhoLuuTruError(f"tải {AGG_TRADES_HOST}{duong_dan} thất bại: {exc}") from exc
    finally:
        conn.close()

    try:
        with zipfile.ZipFile(io.BytesIO(noi_dung)) as z:
            tho = z.read(z.namelist()[0]).decode("utf-8")
    except (zipfile.BadZipFile, IndexError, UnicodeDecodeError) as exc:
        raise KhoLuuTruError(f"{ten} không giải nén được: {exc}") from exc

    hang: list[list[str]] = []
    for dong in tho.splitlines():
        dong = dong.strip()
        if not dong:
            continue
        o = dong.split(",")
        try:
            float(o[0])
        except ValueError:
            continue  # hàng tiêu đề
        hang.append(o)
    if not hang:
        raise KhoLuuTruError(f"{ten}: giải nén được nhưng 0 hàng đọc được")
    return hang


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
