"""DG8 — Time Stop, thuộc nhóm ĐÓNG VỊ THẾ (§4b, TD-0121).

Kiểm tra LIÊN TỤC sau khi tranche 1 khớp: `bars_since_tranche1` (đếm
bằng nến 4H) ≥ `max_hold_bars` → đóng TOÀN BỘ vị thế bằng MARKET, tag
`TIME_STOP`.

🔴 ÁP DỤNG KHÔNG ĐIỀU KIỆN (§4b.2) — hàm này CỐ Ý không nhận bất kỳ
tham số nào về lãi/lỗ, TP1, `trend_dir`, hay ZSS. Mỗi ngoại lệ thêm vào
là một bậc tự do mới, và chính ngoại lệ "đang lãi thì cho ở lại" là
cách một time stop bị vô hiệu hoá trong thực tế (spec dòng 1461-1463).

`max_hold_bars` đọc từ `tier_b.max_hold_bars_4h` (`config/tool_d_config.yaml`,
mục #11, §4b.3) — không hardcode ở đây, người gọi tự đọc config rồi
truyền vào (giữ hàm thuần, không phụ thuộc I/O, cùng pattern
`zone_detection.py`/`zone_strength.py`).
"""

from __future__ import annotations


def bars_since_tranche1(tranche1_bar: int, current_bar: int) -> int:
    """Số nến 4H đã trôi qua kể từ khi tranche 1 khớp (chỉ số nến,
    khớp quy ước bar-index của `zone_detection.py`)."""
    if current_bar < tranche1_bar:
        raise ValueError("current_bar phải >= tranche1_bar")
    return current_bar - tranche1_bar


def is_time_stop_triggered(*, tranche1_bar: int, current_bar: int, max_hold_bars: int) -> bool:
    """DG8 — True khi đã tới hạn giữ lệnh. KHÔNG kiểm bất kỳ điều kiện
    nào khác — đây chính là điểm mấu chốt của "áp dụng không điều kiện"."""
    return bars_since_tranche1(tranche1_bar, current_bar) >= max_hold_bars


def hold_duration_bars(tranche1_bar: int, close_bar: int) -> int:
    """L-Z19 — số nến đã giữ lệnh, ghi cho MỌI lệnh đã đóng bất kể lý
    do đóng (TP/SL/DG6/DG7/DG8) — dùng chung công thức với
    `bars_since_tranche1`, vì về mặt số học đây là cùng một phép đếm,
    chỉ khác mục đích đọc (đang diễn ra vs. đã kết thúc)."""
    if close_bar < tranche1_bar:
        raise ValueError("close_bar phải >= tranche1_bar")
    return bars_since_tranche1(tranche1_bar, close_bar)
