"""Danh sách ĐÓNG các đường sinh số liệu E1-E8 (spec dòng 649-665, §0d.2).

Nguồn sự thật DUY NHẤT cho entrypoint hợp lệ. Thêm entrypoint mới PHẢI sửa
CẢ ở đây LẪN test L-Z36 (TD-0017) — tách hai chỗ này ra là đúng lỗi đã hạ
Tool A: guard nối vào một số script, bỏ sót đúng script nuôi gate (spec
dòng 546-550).

🔴 Không có E9 "script thử nghiệm nhanh" (spec dòng 664).
"""

from __future__ import annotations

from pathlib import Path

CLOSED_ENTRYPOINTS: dict[str, str] = {
    "E1": "run_backtest.py",
    "E2": "run_wfo.py",
    "E3": "run_ablation.py",
    "E4": "touch_lockbox.py",
    "E5": "periodic_report.py",
    "E6": "trial_ledger_audit.py",
    "E7": "build_pool.py",
    "E8": "backfill_data.py",
}

ENTRYPOINTS_DIR = Path("entrypoints")


def assert_closed_entrypoint_set(entrypoints_dir: Path = ENTRYPOINTS_DIR) -> None:
    """Raise AssertionError nếu nội dung thư mục lệch danh sách đóng.

    Lệch theo CẢ hai chiều: file thừa (entrypoint không nằm trong danh sách
    — bẫy "script thử nghiệm nhanh" spec cấm) VÀ file thiếu (một E-số nào
    đó bị xoá nhầm mà không xoá luôn khỏi danh sách).
    """
    on_disk = {p.name for p in entrypoints_dir.glob("*.py")}
    expected = set(CLOSED_ENTRYPOINTS.values())

    extra = sorted(on_disk - expected)
    missing = sorted(expected - on_disk)
    if extra or missing:
        raise AssertionError(
            f"Thư mục {entrypoints_dir} lệch danh sách đóng CLOSED_ENTRYPOINTS — "
            f"thừa: {extra or 'none'}, thiếu: {missing or 'none'}"
        )
