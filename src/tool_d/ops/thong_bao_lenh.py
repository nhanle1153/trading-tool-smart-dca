"""TD-0405 — soạn tin Telegram khi một lệnh vào KHỚP (dry-run D11, `ZoneAbsorption`).

Chủ dự án chốt 25/09/2026 khuôn tin (tranche 1):

    🆕 Lệnh mới #10 LAB/USDT:USDT SHORT 5x
    Ký quỹ 299.74 USDT · vị thế 1,498.69 USDT
    Cắt lỗ 0.05761 (cách giá vào 4.75%)
    Rủi ro nếu chạm cắt lỗ: 71.12 USDT = 3.37% vốn (vốn 2,113.11 USDT, chưa gồm phí)

Tranche 2/3 đổi dòng đầu thành `➕ Vào thêm lần k/n #id …`; mọi số là TỔNG vị thế SAU lần khớp đó (không phải
riêng phần vừa thêm) — thứ chủ dự án cần biết là *đang* chịu rủi ro bao nhiêu. "Vốn" = tổng ví lúc khớp.

Hàm THUẦN: không đọc tham số (N4 không liên quan — đây chỉ là trình bày), không gọi mạng. Lời gửi nằm ở
`ZoneAbsorption.order_filled()` qua `dp.send_msg` (Telegram tích hợp của Freqtrade, TD-0393).

🔴 N6: số nào chưa có thì ghi "chưa đo được", KHÔNG in `0.00`. SL nằm sai phía giá vào (Long mà `sl ≥ giá vào`,
Short mà `sl ≤ giá vào`) thì rủi ro theo công thức ra số vô nghĩa ⇒ báo bất thường thay vì in số đó.
"""

from __future__ import annotations

import math
from decimal import Decimal

CHUA_DO = "chưa đo được"


def _co_so(x: float | None) -> bool:
    return x is not None and math.isfinite(x)


def _usdt(x: float) -> str:
    return f"{x:,.2f}"


def _gia(x: float) -> str:
    """Sáu chữ số có nghĩa, không bao giờ ra dạng `1e-05` (giá coin rất nhỏ)."""
    return format(Decimal(f"{x:.6g}"), "f")


def _don_bay(x: float) -> str:
    return f"{x:g}x"


def soan_tin_vao_lenh(
    *,
    trade_id: int,
    pair: str,
    is_short: bool,
    leverage: float,
    tranche: int,
    so_tranche: int | None,
    stake_usdt: float | None,
    amount: float | None,
    open_rate: float | None,
    sl: float | None,
    von_usdt: float | None,
) -> str:
    huong = "SHORT" if is_short else "LONG"
    if tranche <= 1:
        dau = f"🆕 Lệnh mới #{trade_id} {pair} {huong} {_don_bay(leverage)}"
    else:
        lan = f"{tranche}/{so_tranche}" if so_tranche else f"{tranche}"
        dau = f"➕ Vào thêm lần {lan} #{trade_id} {pair} {huong} {_don_bay(leverage)}"

    ky_quy = f"{_usdt(stake_usdt)} USDT" if _co_so(stake_usdt) else CHUA_DO
    co_vi_the = _co_so(amount) and _co_so(open_rate) and open_rate > 0
    vi_the = f"{_usdt(amount * open_rate)} USDT" if co_vi_the else CHUA_DO
    dong_von = f"Ký quỹ {ky_quy} · vị thế {vi_the}"

    if not _co_so(sl) or sl <= 0:
        return "\n".join([dau, dong_von, f"Cắt lỗ: {CHUA_DO}", f"Rủi ro nếu chạm cắt lỗ: {CHUA_DO}"])
    if not co_vi_the:
        return "\n".join([dau, dong_von, f"Cắt lỗ {_gia(sl)}", f"Rủi ro nếu chạm cắt lỗ: {CHUA_DO}"])

    khoang = (sl - open_rate) if is_short else (open_rate - sl)
    if khoang <= 0:
        return "\n".join([
            dau,
            dong_von,
            f"⚠️ Cắt lỗ {_gia(sl)} nằm SAI phía giá vào {_gia(open_rate)} ({huong})",
            f"Rủi ro nếu chạm cắt lỗ: {CHUA_DO} — kiểm tra lệnh ngay",
        ])

    dong_sl = f"Cắt lỗ {_gia(sl)} (cách giá vào {khoang / open_rate * 100:.2f}%)"
    rui_ro = amount * khoang
    if _co_so(von_usdt) and von_usdt > 0:
        phan_von = f"{rui_ro / von_usdt * 100:.2f}% vốn (vốn {_usdt(von_usdt)} USDT, chưa gồm phí)"
    else:
        phan_von = f"% vốn {CHUA_DO} (chưa gồm phí)"
    return "\n".join([dau, dong_von, dong_sl, f"Rủi ro nếu chạm cắt lỗ: {_usdt(rui_ro)} USDT = {phan_von}"])
