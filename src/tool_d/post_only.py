"""TD-0355/TD-0356 (`DR-D4-20`) — luật post-only LD-13: lệnh nào SÀN THẬT sẽ từ chối.

Spec §3.5 (`:1175`): *"lệnh post-only ở giá ≥ ask bị sàn từ chối, không phải khớp taker"*. Một lệnh MUA limit đặt
**trên** giá thị trường sẽ lấy thanh khoản ⇒ với `time_in_force = "PO"` sàn từ chối thẳng, không khớp. Chiều SHORT
đối xứng: lệnh BÁN limit đặt **dưới** giá thị trường bị từ chối.

🔴 Vì sao phải có hàm này thay vì tin backtest: Freqtrade 2026.8 backtest KHÔNG mô phỏng post-only. Nó **kẹp** giá
lệnh về `min(giá_lệnh, đỉnh nến)` (LONG, `backtesting.py:1056`) rồi khớp nếu `low ≤ giá ≤ high` (`:1240`). Hai hậu
quả, cả hai là lệnh live KHÔNG BAO GIỜ có:
  1. cả nến nằm dưới `p1` ⇒ khớp ở ĐỈNH nến, có khi dưới cả `sl` (ca `D-0015`, lô `DR-D4-19`);
  2. nến mở dưới `p1` rồi bật lên ⇒ khớp đúng `p1`, **trông hoàn toàn bình thường** trong mọi bảng kết quả.
Ca (2) là lý do `DR-D4-20` loại mức hẹp *"cả nến dưới p1"*: nó chỉ bắt ca (1).

Hàm THUẦN, không biết Freqtrade. Nguồn "giá thị trường lúc đặt" do tầng gọi truyền vào — và ở cả hai chế độ chạy
nó đi qua CÙNG một đường: `custom_entry_price(proposed_rate=...)` cho tranche 1, `adjust_trade_position(
current_rate=...)` cho tranche 2/3 (backtest: giá MỞ nến — `backtesting.py:1151`, `:721`; live: giá hiện hành).
Không rẽ nhánh theo runmode — bài học `DR-D4-05`: lấy chuẩn của đường đang chạy là cách backtest và live lệch nhau
mà không ai thấy.
"""

from __future__ import annotations

import math

#: Lề tương đối khi so hai giá. Không phải tham số chiến lược (không vào kiểm kê DOF): nó chỉ chặn việc hai số
#: bằng nhau về ý nghĩa bị lệch ở chữ số cuối vì bước giá/làm tròn của sàn.
EPS = 1e-9


class PostOnlyError(ValueError):
    """Giá đầu vào không hợp lệ — fail-closed, không đoán (N6)."""


def _gia_duong(ten: str, v: float) -> float:
    if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) or v <= 0:
        raise PostOnlyError(f"`{ten}` phải là số hữu hạn > 0, nhận {v!r}")
    return float(v)


def bi_san_tu_choi(gia_lenh: float, gia_thi_truong: float, *, la_short: bool, eps: float = EPS) -> bool:
    """`True` ⇒ sàn thật TỪ CHỐI lệnh post-only này ⇒ chiến lược không được đặt nó.

    LONG (mua): từ chối khi `gia_thi_truong < gia_lenh` — mua trên giá thị trường là lấy thanh khoản.
    SHORT (bán): từ chối khi `gia_thi_truong > gia_lenh`.

    Bằng nhau (trong lề `eps`) ⇒ **KHÔNG** từ chối: lệnh đặt đúng giá thị trường còn có thể nằm ở phía maker của
    sổ lệnh. Đây là chỗ duy nhất luật này có lề, và lề nghiêng về phía CHO ĐẶT — ngược lại sẽ chặn cả những lệnh
    hợp lệ mà không ai biết.
    """
    gia_lenh = _gia_duong("gia_lenh", gia_lenh)
    gia_thi_truong = _gia_duong("gia_thi_truong", gia_thi_truong)
    if la_short:
        return gia_thi_truong > gia_lenh * (1 + eps)
    return gia_thi_truong < gia_lenh * (1 - eps)


def ly_do_tu_choi(pair: str, *, gia_lenh: float, gia_thi_truong: float, la_short: bool, tranche: int) -> str:
    """Một dòng log ĐẾM ĐƯỢC (khuôn `HUONG_TU_CHOI`/`SAN_TU_CHOI` đang có) — phép từ chối im lặng là phép từ
    chối không ai kiểm được."""
    huong = "SHORT" if la_short else "LONG"
    return (
        f"POST_ONLY_TU_CHOI {pair} tranche={tranche} huong={huong} "
        f"gia_lenh={gia_lenh:.10g} gia_thi_truong={gia_thi_truong:.10g} (LD-13, DR-D4-20)"
    )


__all__ = ["EPS", "PostOnlyError", "bi_san_tu_choi", "ly_do_tu_choi"]
