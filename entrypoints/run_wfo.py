"""E2 — H3-D walk-forward orchestrator (spec dòng 656).

Khung TD-0016: chỉ dựng `main()` gọi `measurement_guard()` ở dòng đầu tiên
sau parse tham số (canh bởi L-Z36, TD-0017). TD-0057 nối `run_audit()`
(E6, H16) ngay sau đó — "tự kiểm cả chính nó" TRƯỚC MỖI lần chạy (spec
dòng 660). TD-0072 nối thêm `verify_all_seals()` (H17). Logic WFO thật
là "VIẾT LẠI TỪ ĐẦU" theo bảng H3-D (spec dòng 4340).

TD-0145 nối phần ĐIỀU PHỐI: `wfo.orchestrator.chay_wfo()` gộp
`folds` (DR-D3-01) + `cache` (§0d.3, vân tay) + `equity` (L-Z47, ghép fold
bằng NHÂN). Khối guard/audit/seal ở đầu `main()` (TD-0016/0057/0072) KHÔNG
bị đụng tới — phần mới chỉ nằm SAU nó.

🔴 **Cái CÒN THIẾU, nói rõ để không ai tưởng E2 đã chạy được:** chưa có bộ
chạy backtest thật ở bất kỳ đâu trong repo — E1 `run_backtest.py` cũng còn
`NotImplementedError` (việc của Khối 2/3). Vì vậy `main()` in ra SƠ ĐỒ FOLD
(sinh từ cấu hình, không chạm một byte dữ liệu thị trường nào) rồi dừng với
`EXIT_CHUA_CO_BO_CHAY`. Đó là một cổng có thông báo, không phải một
traceback — và nó chứng minh đường nối cấu hình → fold đã sống.

🔴 **Khi có bộ chạy thật, chỗ nối là `chay_mot_fold`** — và nó phải tự gọi
`TrialLedger.reserve()` TRƯỚC khi chạm dữ liệu (L-Z52). `orchestrator` cố ý
không tự đặt chỗ: nó không biết `budget_line` nào, đoán hộ là cách chắc
chắn tiêu sai ngân sách.
"""

from __future__ import annotations

import argparse
import sys

from tool_d.config.loader import load_tool_d_config
from tool_d.gates.d0_pre import require_d0_pre_complete
from tool_d.lockbox.seal import verify_all_seals
from tool_d.measurement.guard import EXIT_GUARD_BLOCKED, GuardOutcome, measurement_guard
from tool_d.wfo.folds import san_lenh_moi_fold, sinh_folds
from touch_lockbox import EXIT_LOCKBOX_VERIFY_FAILED, LOCKBOX_DIR, LOCKBOX_FUTURES_DIR
from trial_ledger_audit import run_audit

ENTRYPOINT = "E2"

# Sơ đồ fold dựng được, nhưng chưa có bộ chạy backtest để chạy nó.
# Mã riêng, KHÁC mọi mã lỗi khác: đây không phải sai sót nào cả, chỉ là
# một mảnh chưa tới lượt (E1 cũng vậy).
EXIT_CHUA_CO_BO_CHAY = 97


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="E2 run_wfo.py — H3-D walk-forward orchestrator")
    parser.add_argument(
        "--with-params-file",
        action="store_true",
        help="Cho phép chạy dù có <Strategy>.json cạnh strategy (0d.1) — cờ này được ghi vào provenance.",
    )
    return parser


def in_so_do_fold() -> str:
    """Dựng sơ đồ fold từ cấu hình và trả về dạng đọc được.

    Tách khỏi `main()` để test được mà không phải chạy qua guard/audit/seal
    (chúng cần trạng thái repo thật). KHÔNG chạm dữ liệu thị trường: fold
    sinh ra từ đúng bốn mốc ngày trong `tier_c.data_split` và ba con số
    trong `tier_c.wfo_folds`.
    """
    cfg = load_tool_d_config()
    folds = sinh_folds(cfg)
    san = san_lenh_moi_fold(cfg)

    dong = [
        "SƠ ĐỒ FOLD WALK-FORWARD (DR-D3-01, neo gốc)",
        "-" * 68,
    ]
    for f in folds:
        dong.append(
            f"  fold {f.chi_so}: train [{f.train_start} → {f.train_end})  "
            f"test [{f.test_start} → {f.test_end})  "
            f"({f.train_ngay}d / {f.test_ngay}d)"
        )
    dong += [
        "-" * 68,
        f"  sàn số lệnh mỗi fold: {san} — dưới sàn thì chỉ số ghi `unreadable`,",
        "  KHÔNG ghi số (DR-D3-01 §5.2, N6).",
        "",
        "🛑 CHƯA CHẠY ĐƯỢC: không có bộ chạy backtest thật (E1 cũng chưa có).",
        "   Phần điều phối đã sẵn sàng ở `tool_d.wfo.orchestrator.chay_wfo()`;",
        "   thiếu đúng một mảnh là hàm chạy backtest cho một cửa sổ thời gian.",
        "   Khi viết mảnh đó: nó phải gọi `TrialLedger.reserve()` TRƯỚC khi",
        "   chạm dữ liệu (L-Z52).",
    ]
    return "\n".join(dong)


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

    print(in_so_do_fold())
    return EXIT_CHUA_CO_BO_CHAY


if __name__ == "__main__":
    sys.exit(main())
