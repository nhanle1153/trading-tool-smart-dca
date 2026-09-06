"""E2 — H3-D walk-forward orchestrator (spec dòng 656).

Khung TD-0016: chỉ dựng `main()` gọi `measurement_guard()` ở dòng đầu tiên
sau parse tham số (canh bởi L-Z36, TD-0017). TD-0057 nối `run_audit()`
(E6, H16) ngay sau đó — "tự kiểm cả chính nó" TRƯỚC MỖI lần chạy (spec
dòng 660). TD-0072 nối thêm `verify_all_seals()` (H17). Logic WFO thật
là "VIẾT LẠI TỪ ĐẦU" theo bảng H3-D (spec dòng 4340) — chưa có mã việc
TD riêng tại thời điểm sửa file này.
"""

from __future__ import annotations

import argparse
import sys

from tool_d.gates.d0_pre import require_d0_pre_complete
from tool_d.lockbox.seal import verify_all_seals
from tool_d.measurement.guard import EXIT_GUARD_BLOCKED, GuardOutcome, measurement_guard
from touch_lockbox import EXIT_LOCKBOX_VERIFY_FAILED, LOCKBOX_DIR, LOCKBOX_FUTURES_DIR
from trial_ledger_audit import run_audit

ENTRYPOINT = "E2"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="E2 run_wfo.py — H3-D walk-forward orchestrator")
    parser.add_argument(
        "--with-params-file",
        action="store_true",
        help="Cho phép chạy dù có <Strategy>.json cạnh strategy (0d.1) — cờ này được ghi vào provenance.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    args, _ = build_parser().parse_known_args(argv)

    report = measurement_guard(ENTRYPOINT, argv=argv, with_params_file=args.with_params_file)
    if report.outcome is GuardOutcome.BLOCKED:
        return EXIT_GUARD_BLOCKED

    gate_exit = require_d0_pre_complete(ENTRYPOINT)
    if gate_exit is not None:
        return gate_exit

    audit_exit, audit_text = run_audit()
    if audit_exit != 0:
        print(audit_text)
        return audit_exit

    seal_errors = verify_all_seals(LOCKBOX_DIR, LOCKBOX_FUTURES_DIR)
    if seal_errors:
        print("🛑 L-Z14 FAIL — seal KHÔNG khớp dữ liệu lockbox:")
        for e in seal_errors:
            print(f"  - {e}")
        return EXIT_LOCKBOX_VERIFY_FAILED

    raise NotImplementedError(
        "Logic H3-D walk-forward orchestrator chưa viết — TD-0016 chỉ dựng khung guard."
    )


if __name__ == "__main__":
    sys.exit(main())
