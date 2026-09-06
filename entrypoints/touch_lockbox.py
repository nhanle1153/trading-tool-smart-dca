"""E4 — DR-011, mọi lần chạm lockbox phải ghi `lockbox_access.log` (spec dòng 658).

Khung TD-0016: `main()` gọi `measurement_guard()` ở dòng đầu tiên sau parse
tham số (canh bởi L-Z36, TD-0017). TD-0071 nối hai chế độ (H17):

    --verify-seal   chỉ kiểm SHA-256 của mọi đoạn niêm phong đang có so
                    với `lockbox/data/` (L-Z13/14) — KHÔNG ghi sổ truy cập,
                    vì đây là kiểm tra toàn vẹn, không phải một lần "chạm
                    để đánh giá" (spec chỉ đòi ghi sổ khi dùng dữ liệu cho
                    quyết định, dòng 3313).
    --seal-initial  TD-0084 — ghi `lockbox_seal_1.json` LẦN ĐẦU cho đoạn
                    LOCKBOX [T2,T3] đã chốt (DR-D0PRE-07). Hash TOÀN BỘ
                    file trong `lockbox/data/futures/` (đã tải bằng
                    `freqtrade download-data`, service `lockbox` — service
                    DUY NHẤT thấy `lockbox/data/` thật). KHÔNG ghi sổ truy
                    cập — đây là NIÊM PHONG (đóng gói + hash), không phải
                    CHẠM để đánh giá (DR-014 mục 2, MT-02). `write_seal()`
                    tự từ chối nếu file seal đã tồn tại — chỉ chạy được
                    một lần trong đời repo.
    --backup-to DIR TD-0085 (OQ-08) — sao chép seal + `lockbox/data/` sang
                    `DIR/lockbox/` NGOÀI git (spec dòng 4002: không có
                    "lockbox thứ hai" — mất ổ đĩa này là mất vĩnh viễn).
                    Không ghi sổ truy cập (không phải chạm để đánh giá).
                    Ghi đè bản backup cũ mỗi lần chạy — backup phản ánh
                    trạng thái MỚI NHẤT, không phải append-only.
    (mặc định)      chế độ chạm dữ liệu THẬT — TỪ CHỐI vô điều kiện. Việc
                    chạm lockbox để đánh giá là D9 (spec dòng 4493), ngoài
                    phạm vi backlog D0-PRE này; TD-0084 (Khối 8) chỉ NIÊM
                    PHONG (ghi seal), không CHẠM (không chạy backtest trên
                    dữ liệu lockbox).
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from tool_d.lockbox.backup import backup_lockbox
from tool_d.lockbox.seal import build_seal, verify_all_seals, verify_seal, write_seal
from tool_d.measurement.guard import EXIT_GUARD_BLOCKED, GuardOutcome, measurement_guard

ENTRYPOINT = "E4"

LOCKBOX_DIR = Path("lockbox")
LOCKBOX_DATA_DIR = LOCKBOX_DIR / "data"
LOCKBOX_FUTURES_DIR = LOCKBOX_DATA_DIR / "futures"
SEAL_1_PATH = LOCKBOX_DIR / "lockbox_seal_1.json"

# DR-D0PRE-07 (TD-0084) — mốc CALIB/WFO/LOCKBOX đã chốt. LOCKBOX = [T2,T3].
DATE_RANGE_SEGMENT_1 = {
    "T0": "2024-04-09",
    "T1": "2025-06-12",
    "T2": "2026-01-29",
    "T3": "2026-09-06",
}

# 89/90 — tiếp nối dải exit code riêng của guard (86) và cache policy (87);
# chọn số không trùng 0/1/2 để phân biệt được ngay trong log.
EXIT_LOCKBOX_VERIFY_FAILED = 89
EXIT_LOCKBOX_TOUCH_BLOCKED = 90
EXIT_LOCKBOX_SEAL_FAILED = 91
EXIT_LOCKBOX_BACKUP_FAILED = 88  # dải riêng 86-91 đã kín (86 guard, 87 cache, 89/90/91 lockbox) — 88 còn trống, không phải cache_policy


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
    parser.add_argument(
        "--seal-initial",
        action="store_true",
        help="TD-0084 — ghi lockbox_seal_1.json lần đầu cho đoạn LOCKBOX (DR-D0PRE-07). Chạy được đúng một lần.",
    )
    parser.add_argument(
        "--backup-to",
        metavar="DIR",
        help="TD-0085 (OQ-08) — sao chép lockbox/ (seal + data) sang DIR/lockbox/, ngoài git.",
    )
    parser.add_argument(
        "--verify-backup",
        metavar="DIR",
        help="TD-0085 — verify_seal trên bản backup tại DIR/lockbox/ (mô phỏng khôi phục sau mất ổ đĩa).",
    )
    return parser


def _seal_initial() -> int:
    if SEAL_1_PATH.exists():
        print(f"🛑 {SEAL_1_PATH} đã tồn tại — seal bất biến, không niêm phong lại (spec dòng 3312).")
        return EXIT_LOCKBOX_SEAL_FAILED
    if not LOCKBOX_FUTURES_DIR.is_dir():
        print(f"🛑 {LOCKBOX_FUTURES_DIR} không tồn tại — tải dữ liệu LOCKBOX trước bằng "
              "`freqtrade download-data` (service `lockbox`, xem DR-D0PRE-07 mục 6).")
        return EXIT_LOCKBOX_SEAL_FAILED
    data_files = {p.name: p for p in sorted(LOCKBOX_FUTURES_DIR.glob("*.feather"))}
    if not data_files:
        print(f"🛑 {LOCKBOX_FUTURES_DIR} rỗng — không có gì để niêm phong.")
        return EXIT_LOCKBOX_SEAL_FAILED
    seal = build_seal(
        segment=1,
        sealed_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        date_range=DATE_RANGE_SEGMENT_1,
        data_files=data_files,
    )
    write_seal(seal, SEAL_1_PATH)
    print(f"✅ Đã niêm phong {SEAL_1_PATH} — {len(data_files)} file, đoạn {DATE_RANGE_SEGMENT_1}.")
    return 0


def _backup_to(dest_dir: Path) -> int:
    try:
        dest_lockbox = backup_lockbox(source_lockbox_dir=LOCKBOX_DIR, dest_dir=dest_dir)
    except FileNotFoundError as exc:
        print(f"🛑 {exc}")
        return EXIT_LOCKBOX_BACKUP_FAILED
    print(f"✅ Đã backup {LOCKBOX_DIR} -> {dest_lockbox}")
    return 0


def _verify_backup(dest_dir: Path) -> int:
    dest_lockbox = dest_dir / LOCKBOX_DIR.name
    seal_paths = sorted(dest_lockbox.glob("lockbox_seal_*.json"))
    if not seal_paths:
        print(f"🛑 Không thấy lockbox_seal_*.json nào ở {dest_lockbox}.")
        return EXIT_LOCKBOX_BACKUP_FAILED
    all_errors: list[str] = []
    for seal_path in seal_paths:
        errors = verify_seal(seal_path, dest_lockbox / "data" / "futures")
        all_errors.extend(f"{seal_path.name}: {e}" for e in errors)
    if all_errors:
        print(f"🛑 Khôi phục từ {dest_lockbox} KHÔNG khớp seal:")
        for e in all_errors:
            print(f"  - {e}")
        return EXIT_LOCKBOX_BACKUP_FAILED
    print(f"✅ Khôi phục từ {dest_lockbox} khớp {len(seal_paths)} seal — backup dùng được.")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    args, _ = build_parser().parse_known_args(argv)

    report = measurement_guard(ENTRYPOINT, argv=argv, with_params_file=args.with_params_file)
    if report.outcome is GuardOutcome.BLOCKED:
        return EXIT_GUARD_BLOCKED

    if args.verify_seal:
        errors = verify_all_seals(LOCKBOX_DIR, LOCKBOX_FUTURES_DIR)
        if errors:
            print("🛑 L-Z14 FAIL — seal KHÔNG khớp dữ liệu lockbox:")
            for e in errors:
                print(f"  - {e}")
            return EXIT_LOCKBOX_VERIFY_FAILED
        print(
            "✅ verify-seal PASS (H17) — mọi đoạn niêm phong hiện có khớp "
            f"dữ liệu ({LOCKBOX_FUTURES_DIR})."
        )
        return 0

    if args.seal_initial:
        return _seal_initial()

    if args.backup_to:
        return _backup_to(Path(args.backup_to))

    if args.verify_backup:
        return _verify_backup(Path(args.verify_backup))

    print(
        "🛑 TỪ CHỐI: chế độ chạm lockbox THẬT bị khoá tới sau D9 (DR-011, "
        "spec dòng 3305-3320, 4493). D0-PRE chỉ được NIÊM PHONG (TD-0084), "
        "không được CHẠM để đánh giá. Dùng --verify-seal để kiểm con dấu."
    )
    return EXIT_LOCKBOX_TOUCH_BLOCKED


if __name__ == "__main__":
    sys.exit(main())
