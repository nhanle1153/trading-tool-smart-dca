"""E1 — wrapper cho freqtrade backtesting (spec dòng 655).

Khung TD-0016: `main()` gọi `measurement_guard()` ở dòng đầu tiên sau parse
tham số (canh bởi L-Z36, TD-0017). TD-0018 nối thêm `assert_cache_none()`
(L-Z38) ngay sau guard — TỪ CHỐI nếu thiếu `--cache none`, không tự chèn.
TD-0057 nối `run_audit()` (E6, H16) ngay sau đó — "tự kiểm cả chính nó"
TRƯỚC MỖI lần backtest (spec dòng 660). Logic backtest thật là việc ở
Khối 2/3.
"""

from __future__ import annotations

import argparse
import sys

from tool_d.gates.cache_policy import assert_cache_none
from tool_d.measurement.guard import EXIT_GUARD_BLOCKED, GuardOutcome, measurement_guard
from trial_ledger_audit import run_audit

ENTRYPOINT = "E1"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="E1 run_backtest.py — wrapper cho freqtrade backtesting")
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

    cache_exit = assert_cache_none(argv)
    if cache_exit is not None:
        return cache_exit

    audit_exit, audit_text = run_audit()
    if audit_exit != 0:
        print(audit_text)
        return audit_exit

    raise NotImplementedError(
        "Logic backtest thật chưa viết — việc ở Khối 2/3."
    )


if __name__ == "__main__":
    sys.exit(main())
