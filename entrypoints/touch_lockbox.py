"""E4 — DR-011, mọi lần chạm lockbox phải ghi `lockbox_access.log` (spec dòng 658).

Khung TD-0016: chỉ dựng `main()` gọi `measurement_guard()` ở dòng đầu tiên
sau parse tham số (canh bởi L-Z36, TD-0017). Chế độ `--verify-seal` (H17)
là TD-0071 — chế độ chạm dữ liệu thật vẫn TỪ CHỐI cho tới sau D9.
"""

from __future__ import annotations

import argparse
import sys

from tool_d.measurement.guard import EXIT_GUARD_BLOCKED, GuardOutcome, measurement_guard

ENTRYPOINT = "E4"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="E4 touch_lockbox.py — DR-011 lockbox access")
    parser.add_argument(
        "--with-params-file",
        action="store_true",
        help="Cho phép chạy dù có <Strategy>.json cạnh strategy (0d.1) — cờ này được ghi vào provenance.",
    )
    parser.add_argument(
        "--verify-seal",
        action="store_true",
        help="Chế độ chỉ verify con dấu, không chạm dữ liệu thật (H17, TD-0071).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    args, _ = build_parser().parse_known_args(argv)

    report = measurement_guard(ENTRYPOINT, argv=argv, with_params_file=args.with_params_file)
    if report.outcome is GuardOutcome.BLOCKED:
        return EXIT_GUARD_BLOCKED

    raise NotImplementedError(
        "TD-0070/TD-0071 (seal + --verify-seal) chưa viết — TD-0016 chỉ dựng khung guard."
    )


if __name__ == "__main__":
    sys.exit(main())
