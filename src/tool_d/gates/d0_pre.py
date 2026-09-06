"""Cổng D0-PRE — spec dòng 4464: "KHÔNG ĐƯỢC CHẠM DỮ LIỆU TRƯỚC KHI D0-PRE
XONG".

`is_d0_pre_complete()` là điểm kiểm DUY NHẤT mà mọi entrypoint có khả năng
chạm CALIB/WFO/LOCKBOX (E1, E2, E3, E7, E8) phải gọi trước khi làm vậy.
Fail-closed tuyệt đối: file thiếu, đọc lỗi, hoặc thiếu khoá đều là False.
"""

from __future__ import annotations

import json
from pathlib import Path

DEFAULT_RUNTIME_STATE_PATH = Path("registry/runtime_state.json")

# Exit code khi entrypoint từ chối vì cổng D0-PRE chưa đóng.
EXIT_D0_PRE_GATE_CLOSED = 90


def is_d0_pre_complete(runtime_state_path: Path = DEFAULT_RUNTIME_STATE_PATH) -> bool:
    """True CHỈ KHI file tồn tại và có khoá `d0_pre_complete: true`.

    Không tồn tại, không đọc được (JSON hỏng), hoặc thiếu khoá -> False.
    Khoá đó chỉ được ghi bởi MỘT lần chạy thật ở cổng TD-0086 (L-Z51,
    spec dòng 2997) — không có cách nào khác để hàm này trả True.
    """
    try:
        data = json.loads(runtime_state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return data.get("d0_pre_complete") is True
