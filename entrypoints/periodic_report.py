"""E5 — báo cáo định kỳ, nguồn số duy nhất LLM được đọc (spec dòng 659, §12d.2).

Khung TD-0016: chỉ dựng `main()` gọi `measurement_guard()` ở dòng đầu tiên
sau parse tham số (canh bởi L-Z36, TD-0017). Nội dung báo cáo thật (ba
trạng thái dữ liệu, cấm giá trị lính canh — L-Z41) chưa có mã việc TD riêng
tại thời điểm tạo file này, sẽ thêm khi tới Khối tương ứng.
"""

from __future__ import annotations

import argparse
import sys

from tool_d.measurement.guard import EXIT_GUARD_BLOCKED, GuardOutcome, measurement_guard

ENTRYPOINT = "E5"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="E5 periodic_report.py — báo cáo định kỳ (§12d.2)")
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
        "Nội dung báo cáo định kỳ (§12d.2) chưa viết — TD-0016 chỉ dựng khung guard."
    )


if __name__ == "__main__":
    sys.exit(main())
