"""TD-0241 (`DR-D11-03`) — điểm gọi DUY NHẤT tới REST API điều khiển của
CHÍNH tiến trình Freqtrade cục bộ. §6.6(2): Risk Supervisor coi
`LIQUIDATED` là "cờ đỏ dừng TOÀN HỆ THỐNG" — module này là cách nó thi
hành điều đó trên một bot đang chạy thật.

Tách khỏi `api_client/binance_public.py` một cách có chủ đích: đây KHÔNG
phải Binance, là một dịch vụ KHÁC (control API cục bộ của chính bot, nghe
ở `127.0.0.1`) — cùng tinh thần Telegram đã tách thành "một điểm nghẽn
RIÊNG" trong `provider-map.md` (mỗi dịch vụ ngoài một module, không dùng
chung hàm gọi mạng).

════ Bằng chứng đọc mã nguồn Freqtrade thật (`DR-D11-03` §2), không đoán ════

- `POST /api/v1/stop` (`api_trading.py:327`) dừng HẲN vòng lặp bot
  (`State.STOPPED`) — KHÁC `/stopentry`/`/stopbuy`/`/pause`, những cái đó
  chỉ CHẶN mở lệnh mới, giữ nguyên vị thế đang mở. §6.6(2) đòi "dừng TOÀN
  HỆ THỐNG" nên chọn `/stop`.
- `_rpc_stop()` (`rpc.py:978`) **idempotent**: gọi khi đã `STOPPED` trả
  `{"status": "already stopped"}`, không lỗi — daemon gọi lặp lại (do
  retry mạng) không cần tự khử trùng lặp.
- Xác thực chấp nhận HTTP Basic TRỰC TIẾP (`http_basic_or_jwt_token`,
  `api_auth.py`) — không bắt buộc bước `/token/login` lấy JWT trước, nên
  `dung_bot()` chỉ cần MỘT request, không hai.
"""

from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable

DEFAULT_TIMEOUT_S = 10.0
SO_LAN_THU_LAI_MAC_DINH = 5
CHO_GIUA_CAC_LAN_S = 2.0


class FreqtradeControlError(RuntimeError):
    """Lỗi khi gọi REST API điều khiển của Freqtrade cục bộ (mạng, HTTP,
    timeout, hoặc hết số lần thử lại)."""


class FreqtradeAuthError(FreqtradeControlError):
    """HTTP 401 — sai username/password. Lỗi CẤU HÌNH cục bộ, KHÔNG retry
    (cùng tinh thần `BinanceCredentialsMissingError` của `binance_public.py`
    — thử lại một mật khẩu sai không bao giờ thành công, chỉ trì hoãn phát
    hiện đúng lúc cần dừng bot NHANH nhất)."""


class FreqtradeBatLaiBotError(FreqtradeControlError):
    """TD-0434 (`api-integration-rules.md` 4.4d luật 1) — `/stopentry` vừa chuyển một bot `STOPPED` sang `PAUSED`, tức
    BẬT LẠI vòng lặp của một bot đã dừng hẳn (`rpc.py:998-1004`). Không được xảy ra; tầng gọi phải `/stop` ngay."""


#: `rpc.py:1000-1004` (Freqtrade 2026.8) — chuỗi trả về khi `/stopentry` gặp bot `STOPPED`.
_DAU_HIEU_BAT_LAI = "starting bot with trader in paused state"


def _goi_dung_mot_lan(
    base_url: str, path: str, *, username: str, password: str, timeout: float, method: str = "POST"
) -> dict:
    url = f"{base_url.rstrip('/')}{path}"
    tin = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    req = urllib.request.Request(url, method=method, headers={"Authorization": f"Basic {tin}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            raise FreqtradeAuthError(
                f"Freqtrade control API ({url}) từ chối username/password — "
                "lỗi CẤU HÌNH cục bộ, KHÔNG phải sự cố mạng/bot"
            ) from exc
        raise FreqtradeControlError(f"gọi {url} thất bại: HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise FreqtradeControlError(f"gọi {url} thất bại: {exc}") from exc


def dung_bot(
    base_url: str,
    *,
    username: str,
    password: str,
    timeout: float = DEFAULT_TIMEOUT_S,
    so_lan_thu_lai: int = SO_LAN_THU_LAI_MAC_DINH,
    cho_giua_cac_lan_s: float = CHO_GIUA_CAC_LAN_S,
    ham_ngu: Callable[[float], None] = time.sleep,
) -> dict:
    """`POST /api/v1/stop` — dừng HẲN vòng lặp bot (§6.6(2)).

    R5 (bounded retry): tối đa `so_lan_thu_lai` lần, KHÔNG lặp vô hạn.
    R4 (phân loại lỗi): 401 KHÔNG retry — raise `FreqtradeAuthError` ngay
    ở lần đầu. Lỗi mạng/HTTP khác thì retry có nghỉ cố định giữa các lần;
    hết số lần vẫn lỗi thì RAISE `FreqtradeControlError`, KHÔNG nuốt — tầng
    gọi (daemon) phải coi "không dừng được bot khi tài khoản đã thanh lý"
    là sự kiện nghiêm trọng nhất có thể, không phải một lỗi bỏ qua được.

    `ham_ngu` nhận qua tham số (mặc định `time.sleep`) để test không phải
    chờ thật giữa các lần thử — cùng khuôn `latency_samples_ms` cho phép
    tiêm hàm thời gian.
    """
    return _goi_co_thu_lai(
        base_url, "/api/v1/stop", username=username, password=password, timeout=timeout,
        so_lan_thu_lai=so_lan_thu_lai, cho_giua_cac_lan_s=cho_giua_cac_lan_s, ham_ngu=ham_ngu,
        viec="dừng được bot",
    )


def tam_ngung_mo_lenh(
    base_url: str,
    *,
    username: str,
    password: str,
    timeout: float = DEFAULT_TIMEOUT_S,
    so_lan_thu_lai: int = SO_LAN_THU_LAI_MAC_DINH,
    cho_giua_cac_lan_s: float = CHO_GIUA_CAC_LAN_S,
    ham_ngu: Callable[[float], None] = time.sleep,
) -> dict:
    """TD-0434 — `POST /api/v1/stopentry`: HALT (§12c.5 bước 1) — ngừng MỞ lệnh mới và bơm thêm, vị thế đang mở chạy tiếp.

    Idempotent khi bot `RUNNING`/`PAUSED` (`rpc.py:991-1004`). 🔴 Gọi khi bot `STOPPED` thì Freqtrade BẬT LẠI vòng lặp ở
    `PAUSED` — tầng gọi PHẢI không gọi hàm này khi có cờ đỏ (`api-integration-rules.md` 4.4d luật 1); nếu vẫn xảy ra, hàm
    này nhận ra chuỗi trả về và raise `FreqtradeBatLaiBotError` để tầng gọi `/stop` ngay, không im lặng.
    """
    kq = _goi_co_thu_lai(
        base_url, "/api/v1/stopentry", username=username, password=password, timeout=timeout,
        so_lan_thu_lai=so_lan_thu_lai, cho_giua_cac_lan_s=cho_giua_cac_lan_s, ham_ngu=ham_ngu,
        viec="tạm ngừng được việc mở lệnh",
    )
    if _DAU_HIEU_BAT_LAI in str(kq.get("status", "")):
        raise FreqtradeBatLaiBotError(
            f"{base_url}/api/v1/stopentry vừa BẬT LẠI một bot đang dừng hẳn ({kq!r}) — phải /stop ngay"
        )
    return kq


def doc_so_lenh_dong(
    base_url: str,
    *,
    username: str,
    password: str,
    timeout: float = DEFAULT_TIMEOUT_S,
    so_lan_thu_lai: int = SO_LAN_THU_LAI_MAC_DINH,
    cho_giua_cac_lan_s: float = CHO_GIUA_CAC_LAN_S,
    ham_ngu: Callable[[float], None] = time.sleep,
) -> int:
    """TD-0434 chặng 2 — `GET /api/v1/profit` → `closed_trade_count`: mọi lệnh ĐÃ ĐÓNG trong DB của bot (`rpc.py:594-623`,
    Freqtrade 2026.8 — lọc `close_date >= epoch`). Nguồn đếm chu kỳ cho trần HALT §12c.5 (`DR-TANG-CHAN-01` §8).

    Trường thiếu / sai kiểu / âm ⇒ `FreqtradeControlError` — KHÔNG trả 0 (N6: "0 lệnh" là một con số, "không đọc được" thì không).
    """
    kq = _goi_co_thu_lai(
        base_url, "/api/v1/profit", username=username, password=password, timeout=timeout,
        so_lan_thu_lai=so_lan_thu_lai, cho_giua_cac_lan_s=cho_giua_cac_lan_s, ham_ngu=ham_ngu,
        viec="đọc được số lệnh đã đóng", method="GET",
    )
    so = kq.get("closed_trade_count") if isinstance(kq, dict) else None
    if type(so) is not int or so < 0:
        raise FreqtradeControlError(f"{base_url}/api/v1/profit: closed_trade_count không hợp lệ ({so!r})")
    return so


def _goi_co_thu_lai(
    base_url: str,
    path: str,
    *,
    username: str,
    password: str,
    timeout: float,
    so_lan_thu_lai: int,
    cho_giua_cac_lan_s: float,
    ham_ngu: Callable[[float], None],
    viec: str,
    method: str = "POST",
) -> dict:
    """R5 bounded retry DÙNG CHUNG cho mọi lời gọi control API (R1 — một đường ra): 401 không retry; lỗi khác thử lại
    tối đa `so_lan_thu_lai` lần, nghỉ cố định; hết lượt thì RAISE, không nuốt."""
    if so_lan_thu_lai < 1:
        raise ValueError(f"so_lan_thu_lai phải >= 1, nhận: {so_lan_thu_lai}")
    loi_cuoi: FreqtradeControlError | None = None
    for lan in range(1, so_lan_thu_lai + 1):
        try:
            return _goi_dung_mot_lan(
                base_url, path, username=username, password=password, timeout=timeout, method=method
            )
        except FreqtradeAuthError:
            raise
        except FreqtradeControlError as exc:
            loi_cuoi = exc
            if lan < so_lan_thu_lai:
                ham_ngu(cho_giua_cac_lan_s)
    assert loi_cuoi is not None  # vòng lặp trên luôn gán trước khi tới đây
    raise FreqtradeControlError(
        f"KHÔNG {viec} qua {base_url}{path} sau {so_lan_thu_lai} lần thử — "
        f"lỗi lần cuối: {loi_cuoi}"
    ) from loi_cuoi
