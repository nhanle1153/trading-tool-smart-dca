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


def require_d0_pre_complete(
    entrypoint: str, runtime_state_path: Path = DEFAULT_RUNTIME_STATE_PATH
) -> int | None:
    """TD-0090 — chốt chặn dùng chung cho mọi entrypoint sắp chạm dữ liệu.

    Trả `None` = được phép đi tiếp. Trả `EXIT_D0_PRE_GATE_CLOSED` (và IN lý
    do) = D0-PRE chưa hoàn tất, TỪ CHỐI chạm dữ liệu (§N2, spec dòng 4464).

    🔴 Phạm vi áp dụng — KHÔNG phải "mọi entrypoint, mọi chế độ":
    `CLAUDE.md` N2 viết "mọi entrypoint phải từ chối chạy", nhưng đọc theo
    nghĩa đen thì chính quy trình D0-PRE không chạy được (E5/E6 phải chạy
    ĐƯỢC lúc cổng chưa hoàn tất — E6 `--close-gate` là thứ ĐÓNG cổng; E7/E8
    phải chạy được để chốt pool và đo metadata, đúng như TD-0080/TD-0083 đã
    làm). Cách đọc nhất quán, cũng là cách docstring module này viết từ
    D0-PRE: chốt chặn gác **hành động chạm dữ liệu** (đánh giá cấu hình
    trên CALIB/WFO/LOCKBOX — định nghĩa MT-02), không gác việc khởi chạy
    tiến trình. Cụ thể:
      - E1/E2/E3: gác VÔ ĐIỀU KIỆN — ba entrypoint này không có chế độ nào
        khác ngoài đánh giá cấu hình trên dữ liệu.
      - E8: gác nhánh backfill THẬT; `--probe-coverage` (đo metadata) vẫn
        chạy được trước cổng.
      - E7: nhánh chạm dữ liệu (H1-D point-in-time) chưa tồn tại — gác khi
        TD-0096 viết nhánh đó, không cắm sẵn một lệnh kiểm không bao giờ
        kích hoạt (cùng lý do L-Z34 tồn tại: kiểm tra không nối vào việc
        thật là trang trí).
    """
    if is_d0_pre_complete(runtime_state_path):
        return None
    print(
        f"🛑 {entrypoint} TỪ CHỐI: cổng D0-PRE chưa hoàn tất — thiếu khoá "
        f"`d0_pre_complete: true` trong {runtime_state_path} (§N2, spec dòng 4464). "
        "Khoá đó chỉ sinh từ MỘT LẦN CHẠY THẬT của "
        "`trial_ledger_audit.py --close-gate` (TD-0086), không được tạo tay."
    )
    return EXIT_D0_PRE_GATE_CLOSED
