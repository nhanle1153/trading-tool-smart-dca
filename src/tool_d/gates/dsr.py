"""Rào DSR (Deflated Sharpe Ratio) — N không phải số trang trí.

L-Z34 (spec dòng 3940-3948): N phải NỐI VÀO PHÉP TÍNH, không phải nằm
trong chú thích. Tool A tin một con số DOF suốt 4 tháng trước khi phát
hiện nó không đi vào phép tính nào — `dsr_hurdle()` tồn tại để phép tính
đó không thể "quên" tham số N.

N đọc từ đâu (spec dòng 3946-3948, và changelog v7→v8 mục (ii)):
    - TRƯỚC live: N = N_ĐĂNG_KÝ (114, DR-D0PRE-02) — một hằng số ĐÃ CHỐT,
      không phải N_ĐÃ_DÙNG (N_ĐÃ_DÙNG dùng để CƯỠNG CHẾ luật dừng
      N_ĐÃ_DÙNG ≤ N_ĐĂNG_KÝ, DR-010 quy tắc 3 — vai trò khác, không phải
      mẫu số DSR).
    - SAU live: N = N_ĐĂNG_KÝ + Σcontribution(trial CONSUMED sau live)
      (§12c.2, "nuôi N sau live"). `effective_n()` nhận hai số đã tính
      sẵn — việc đọc thật từ `trial_registry.jsonl` là của `ledger.py`
      (Khối 5, TD-0050+), CHƯA tồn tại ở D0-PRE. Không dựng logic đọc
      registry ở đây trước khi ledger có hình hài, tránh phải sửa ngược.
"""

from __future__ import annotations

import math

N_DANG_KY = 114  # DR-D0PRE-02 — đã chốt (TD-0032), không phải hằng số tự do


def dsr_hurdle(n_trials: int) -> float:
    """√(2·ln N) — rào Sharpe kỳ vọng dưới giả thuyết "toàn bộ N phép thử
    đều là nhiễu, ta chỉ tình cờ chọn được cái tốt nhất".

    Raise nếu `n_trials <= 1` — log(N) không có ý nghĩa thống kê ở N nhỏ
    như vậy (fail-closed, không âm thầm trả NaN hay số lính canh).
    """
    if n_trials <= 1:
        raise ValueError(f"N phải > 1 để rào DSR có nghĩa, nhận: {n_trials}")
    return math.sqrt(2 * math.log(n_trials))


def effective_n(*, n_dang_ky: int = N_DANG_KY, n_consumed_since_live: int = 0) -> int:
    """N hiệu dụng dùng làm mẫu số DSR.

    `n_consumed_since_live`: Σcontribution của các trial CONSUMED SAU LIVE
    (§12c.2) — KHÔNG bao gồm trial tiêu trước live (những trial đó nằm
    TRONG ngân sách `n_dang_ky`, không cộng thêm). Mặc định 0 (D0-PRE,
    chưa live).
    """
    if n_consumed_since_live < 0:
        raise ValueError("n_consumed_since_live không thể âm")
    return n_dang_ky + n_consumed_since_live
