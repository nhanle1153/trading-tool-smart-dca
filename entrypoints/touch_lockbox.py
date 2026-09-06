"""E4 — DR-011, mọi lần chạm lockbox phải ghi `lockbox_access.log` (spec dòng 658).

Khung TD-0016: `main()` gọi `measurement_guard()` ở dòng đầu tiên sau parse
tham số (canh bởi L-Z36, TD-0017). TD-0071 nối hai chế độ (H17):

    --verify-seal   chỉ kiểm SHA-256 của mọi đoạn niêm phong đang có so
                    với `lockbox/data/` (L-Z13/14) — KHÔNG ghi sổ truy cập,
                    vì đây là kiểm tra toàn vẹn, không phải một lần "chạm
                    để đánh giá" (spec chỉ đòi ghi sổ khi dùng dữ liệu cho
                    quyết định, dòng 3313).
    (mặc định)      chế độ chạm dữ liệu THẬT — TỪ CHỐI vô điều kiện. Việc
                    chạm lockbox để đánh giá là D9 (spec dòng 4493), ngoài
                    phạm vi backlog D0-PRE này; TD-0084 (Khối 8) chỉ NIÊM
                    PHONG (ghi seal), không CHẠM (không chạy backtest trên
                    dữ liệu lockbox).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tool_d.lockbox.seal import verify_all_seals
from tool_d.measurement.guard import EXIT_GUARD_BLOCKED, GuardOutcome, measurement_guard

ENTRYPOINT = "E4"

LOCKBOX_DIR = Path("lockbox")
LOCKBOX_DATA_DIR = LOCKBOX_DIR / "data"

# 89/90 — tiếp nối dải exit code riêng của guard (86) và cache policy (87);
# chọn số không trùng 0/1/2 để phân biệt được ngay trong log.
EXIT_LOCKBOX_VERIFY_FAILED = 89
EXIT_LOCKBOX_TOUCH_BLOCKED = 90


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

    if args.verify_seal:
        errors = verify_all_seals(LOCKBOX_DIR, LOCKBOX_DATA_DIR)
        if errors:
            print("🛑 L-Z14 FAIL — seal KHÔNG khớp dữ liệu lockbox:")
            for e in errors:
                print(f"  - {e}")
            return EXIT_LOCKBOX_VERIFY_FAILED
        print(
            "✅ verify-seal PASS (H17) — mọi đoạn niêm phong hiện có khớp "
            f"dữ liệu ({LOCKBOX_DATA_DIR})."
        )
        return 0

    print(
        "🛑 TỪ CHỐI: chế độ chạm lockbox THẬT bị khoá tới sau D9 (DR-011, "
        "spec dòng 3305-3320, 4493). D0-PRE chỉ được NIÊM PHONG (TD-0084), "
        "không được CHẠM để đánh giá. Dùng --verify-seal để kiểm con dấu."
    )
    return EXIT_LOCKBOX_TOUCH_BLOCKED


if __name__ == "__main__":
    sys.exit(main())
