"""E3 — D0.9 ablation, 9 arm × 2 hướng (spec dòng 657).

Khung TD-0016: chỉ dựng `main()` gọi `measurement_guard()` ở dòng đầu tiên
sau parse tham số (canh bởi L-Z36, TD-0017). TD-0057 nối `run_audit()`
(E6, H16) ngay sau đó — "tự kiểm cả chính nó" TRƯỚC MỖI lần chạy (spec
dòng 660). TD-0072 nối thêm cổng H17 (TD-0316/`DR-LOCKBOX-02`: nay là `kiem_h17()`). Logic ablation
thật chưa có mã việc TD riêng tại thời điểm sửa file này, sẽ thêm khi
tới Khối tương ứng.

🔴 TD-0165 nối `kiem_cong_d35()` (`L-Z56` CRITICAL) — entrypoint này TỪ
CHỐI chạy khi kết quả Δ_R của cổng D3.5 chưa commit đầy đủ. Chốt đó đứng
TRƯỚC cổng H17 (`kiem_h17()`) có chủ đích: nó rẻ, và nó chặn đúng thứ tự sai
mà DR-015 §1 gọi là "trạng thái tệ nhất có thể".
"""

from __future__ import annotations

import argparse
import sys

from tool_d.dr015.cong_d35 import EXIT_CHUA_CO_DELTA_R, CongD35ChuaDongError, kiem_cong_d35
from tool_d.gates.d0_pre import require_d0_pre_complete
from tool_d.lockbox.h17 import in_va_ma_thoat, kiem_h17
from tool_d.measurement.guard import EXIT_GUARD_BLOCKED, GuardOutcome, measurement_guard
from touch_lockbox import EXIT_LOCKBOX_VERIFY_FAILED, LOCKBOX_DIR, LOCKBOX_FUTURES_DIR
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

    gate_exit = require_d0_pre_complete(ENTRYPOINT)
    if gate_exit is not None:
        return gate_exit

    audit_exit, audit_text = run_audit()
    if audit_exit != 0:
        print(audit_text)
        return audit_exit

    # 🔴 L-Z56 (TD-0165) — đứng TRƯỚC mọi việc tốn thời gian, và trước cả
    # verify_seal: chạy ablation mà chưa có Δ_R đã commit là chính trạng
    # thái DR-015 §1 gọi là "tệ nhất có thể" (kết luận Z0-vs-DCA hình
    # thành TRƯỚC, thước kiểm SAU). Từ chối sớm, không đốt thời gian.
    try:
        kiem_cong_d35()
    except CongD35ChuaDongError as exc:
        print(exc)
        return EXIT_CHUA_CO_DELTA_R

    # H17 ở service CHE lockbox (DR-LOCKBOX-02, TD-0316): cách ly còn hiệu lực + seal không bị
    # sửa + sổ truy cập. Băm dữ liệu (`verify_all_seals`, L-Z14) là việc của E4 ở service
    # `lockbox` — ở đây dữ liệu bị che CÓ CHỦ ĐÍCH nên nó FAIL mọi lần (trước TD-0316: exit 89).
    ma_h17 = in_va_ma_thoat(
        kiem_h17(lockbox_dir=LOCKBOX_DIR, data_dir=LOCKBOX_FUTURES_DIR),
        ma_that_bai=EXIT_LOCKBOX_VERIFY_FAILED,
    )
    if ma_h17 is not None:
        return ma_h17

    raise NotImplementedError(
        "Logic D0.9 ablation chưa viết — TD-0016 chỉ dựng khung guard."
    )


if __name__ == "__main__":
    sys.exit(main())
