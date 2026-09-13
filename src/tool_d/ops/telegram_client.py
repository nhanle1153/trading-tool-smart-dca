"""Telegram Bot API — R1 Single Egress cho kênh cảnh báo TD-0209.

Đây PHẢI là module DUY NHẤT gọi mạng tới Telegram (cùng nguyên tắc
`api_client/binance_public.py` áp cho Binance) — một dịch vụ ngoài, một
điểm nghẽn. Gate check (quyết tắc 17) đã điền ở `provider-map.md` +
`api-integration-rules.md` Mục 4.1-4.4b TRƯỚC file này (13/09/2026).

🔴 KHÔNG dùng lại state machine circuit-breaker của `risk_supervisor.py`
(`TrangThaiBreaker`) — đó là mô hình "N lỗi liên tiếp → mở cửa sổ backoff
PHỦ NHIỀU LẦN GỌI", đúng cho Binance vì bot gọi liên tục trong một vòng
lặp dày (mỗi vài giây). Telegram ở đây chỉ được gọi khi watchdog PHÁT
HIỆN CHUYỂN TRẠNG THÁI (không phải mỗi vòng poll), nên một lần gọi thất
bại chỉ cần chờ VÒNG POLL KẾ TIẾP (`heartbeat_watchdog.py`, chu kỳ 60s)
thử lại — không cần một bộ đếm/backoff riêng chồng lên. Tái dùng NHÃN lỗi
(`RETRY`/`LOI_LOGIC`/`KHONG_NHAN_DIEN` từ `risk_supervisor`) để log cùng
một ngôn ngữ trong toàn dự án, nhưng không tái dùng CƠ CHẾ breaker.
"""

from __future__ import annotations

import json
import os
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError

from tool_d.risk_supervisor import KHONG_NHAN_DIEN, LOI_LOGIC, RETRY

DEFAULT_TIMEOUT_S = 10.0  # R11 — cùng số với binance_public.py, không có lý do khác đi

ENV_TELEGRAM_BOT_TOKEN = "TELEGRAM_BOT_TOKEN"
ENV_TELEGRAM_CHAT_ID = "TELEGRAM_CHAT_ID"

_API_BASE = "https://api.telegram.org"

_RETRY_HTTP = {429}
_LOI_LOGIC_HTTP = {400, 401}


class TelegramError(RuntimeError):
    """Lỗi cấu hình/đầu vào của tầng gửi Telegram — fail-closed, không đoán."""


class TelegramCredentialsMissingError(TelegramError):
    """Thiếu `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` — lỗi CẤU HÌNH cục bộ,
    KHÔNG phải sự cố mạng/dịch vụ (cùng tinh thần `BinanceCredentialsMissingError`,
    TD-0242) — phải raise thẳng ra, không nuốt thành "gửi thất bại" chung chung."""


def doc_thong_tin_bot(*, env: Mapping[str, str] | None = None) -> tuple[str, str]:
    nguon = env if env is not None else os.environ
    token = nguon.get(ENV_TELEGRAM_BOT_TOKEN, "")
    chat_id = nguon.get(ENV_TELEGRAM_CHAT_ID, "")
    thieu = [ten for ten, gt in ((ENV_TELEGRAM_BOT_TOKEN, token), (ENV_TELEGRAM_CHAT_ID, chat_id)) if not gt]
    if thieu:
        raise TelegramCredentialsMissingError(f"thiếu biến ENV: {', '.join(thieu)}")
    return token, chat_id


def phan_loai_loi_telegram(*, http_status: int) -> str:
    """Bảng mã lỗi Telegram — `api-integration-rules.md` Mục 4.3. Chỉ ba
    nhãn (không có `DUNG_HAN`): Telegram không có khái niệm "cấm IP vĩnh
    viễn" tương đương HTTP 418 của Binance."""
    if http_status in _RETRY_HTTP or (500 <= http_status < 600):
        return RETRY
    if http_status in _LOI_LOGIC_HTTP:
        return LOI_LOGIC
    return KHONG_NHAN_DIEN


@dataclass(frozen=True)
class KetQuaGuiTelegram:
    """`thanh_cong=False` KHÔNG BAO GIỜ kèm `loai_loi=None` — nếu gửi thất
    bại thì PHẢI phân loại được, `KHONG_NHAN_DIEN` là "biết là lỗi nhưng
    chưa gặp mã này trước", không phải một khoảng trống."""

    thanh_cong: bool
    loai_loi: str | None
    chi_tiet: str | None


def gui_tin_nhan(text: str, *, timeout: float = DEFAULT_TIMEOUT_S, env: Mapping[str, str] | None = None) -> KetQuaGuiTelegram:
    """Gửi MỘT tin nhắn — MỘT lần thử, không tự retry (xem docstring đầu
    file: retry là việc của vòng poll bên ngoài). Thiếu credential →
    RAISE `TelegramCredentialsMissingError` (lỗi cấu hình, không phải kết
    quả gửi thất bại — tầng gọi KHÔNG được bắt lỗi này rồi coi như đã thử
    gửi, đúng bài học R10/TD-0242).
    """
    if not text:
        raise TelegramError("text rỗng — không có gì để gửi")
    token, chat_id = doc_thong_tin_bot(env=env)
    url = f"{_API_BASE}/bot{token}/sendMessage"
    body = json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, method="POST", headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            du_lieu: Any = json.loads(resp.read())
    except HTTPError as exc:
        loai = phan_loai_loi_telegram(http_status=exc.code)
        return KetQuaGuiTelegram(thanh_cong=False, loai_loi=loai, chi_tiet=f"HTTP {exc.code}: {exc}")
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        # Không có http_status (đứt mạng/DNS/timeout trước khi có phản hồi)
        # — cùng chữ `phan_loai_ma_loi()` của risk_supervisor: xếp RETRY vì
        # đây đúng loại lỗi "thử lại có cơ hội thành công", không phải lỗi
        # cấu hình.
        return KetQuaGuiTelegram(thanh_cong=False, loai_loi=RETRY, chi_tiet=str(exc))

    if not du_lieu.get("ok", False):
        return KetQuaGuiTelegram(
            thanh_cong=False, loai_loi=LOI_LOGIC, chi_tiet=f"Telegram trả ok=false: {du_lieu}"
        )
    return KetQuaGuiTelegram(thanh_cong=True, loai_loi=None, chi_tiet=None)
