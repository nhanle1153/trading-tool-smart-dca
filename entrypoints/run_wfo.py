"""E2 — H3-D walk-forward orchestrator (spec dòng 656).

Khung TD-0016: chỉ dựng `main()` gọi `measurement_guard()` ở dòng đầu tiên
sau parse tham số (canh bởi L-Z36, TD-0017). Logic WFO thật là "VIẾT LẠI TỪ
ĐẦU" theo bảng H3-D (spec dòng 4340) — chưa có mã việc TD riêng tại thời
điểm tạo file này, sẽ thêm khi tới Khối tương ứng.
"""

from __future__ import annotations

import argparse
import sys

from tool_d.measurement.guard import EXIT_GUARD_BLOCKED, GuardOutcome, measurement_guard

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

    raise NotImplementedError(
        "Logic H3-D walk-forward orchestrator chưa viết — TD-0016 chỉ dựng khung guard."
    )


if __name__ == "__main__":
    sys.exit(main())
