"""E3 — D0.9 ablation, 9 arm × 2 hướng (spec dòng 657).

Khung TD-0016: chỉ dựng `main()` gọi `measurement_guard()` ở dòng đầu tiên
sau parse tham số (canh bởi L-Z36, TD-0017). TD-0057 nối `run_audit()`
(E6, H16) ngay sau đó — "tự kiểm cả chính nó" TRƯỚC MỖI lần chạy (spec
dòng 660). Logic ablation thật chưa có mã việc TD riêng tại thời điểm
sửa file này, sẽ thêm khi tới Khối tương ứng.
"""

from __future__ import annotations

import argparse
import sys

from tool_d.measurement.guard import EXIT_GUARD_BLOCKED, GuardOutcome, measurement_guard
from trial_ledger_audit import run_audit

ENTRYPOINT = "E3"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="E3 run_ablation.py — D0.9 ablation, 9 arm x 2 hướng")
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

    audit_exit, audit_text = run_audit()
    if audit_exit != 0:
        print(audit_text)
        return audit_exit

    raise NotImplementedError(
        "Logic D0.9 ablation chưa viết — TD-0016 chỉ dựng khung guard."
    )


if __name__ == "__main__":
    sys.exit(main())
