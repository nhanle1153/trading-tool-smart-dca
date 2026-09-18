"""E2 — H3-D walk-forward orchestrator (spec dòng 656).

Khung TD-0016: chỉ dựng `main()` gọi `measurement_guard()` ở dòng đầu tiên
sau parse tham số (canh bởi L-Z36, TD-0017). TD-0057 nối `run_audit()`
(E6, H16) ngay sau đó — "tự kiểm cả chính nó" TRƯỚC MỖI lần chạy (spec
dòng 660). TD-0072 nối thêm cổng H17 (TD-0316/`DR-LOCKBOX-02`: nay là `kiem_h17()`). Logic WFO thật
là "VIẾT LẠI TỪ ĐẦU" theo bảng H3-D (spec dòng 4340).

TD-0145 nối phần ĐIỀU PHỐI: `wfo.orchestrator.chay_wfo()` gộp
`folds` (DR-D3-01) + `cache` (§0d.3, vân tay) + `equity` (L-Z47, ghép fold
bằng NHÂN). Khối guard/audit/seal ở đầu `main()` (TD-0016/0057/0072) KHÔNG
bị đụng tới — phần mới chỉ nằm SAU nó.

🔴 **Trạng thái 18/09/2026, nói rõ để không ai tưởng E2 đã chạy được:** E2
chưa nối bộ chạy nào — TD-0286 (*"Bộ chạy D9 trên E2"*) ⏸ theo `DR-IQ-01` §1.
`main()` in SƠ ĐỒ FOLD (sinh từ cấu hình, không chạm một byte dữ liệu thị trường)
rồi dừng với `EXIT_CHUA_CO_BO_CHAY` — một cổng có thông báo, không phải traceback.
Lõi bộ chạy dùng chung ĐÃ có (`tool_d.bo_chay`, E1 dùng từ TD-0313).

🔑 **Khi nối lại TD-0286, đường nối là `tool_d.wfo.lenh`, KHÔNG phải `chay_wfo`.**
Hai quyết định đã chốt, cùng chiều:
  • `DR-D9-01` §5 + §5.1 (17/09/2026): mỗi cấu hình chạy **MỘT** lượt `[T1, T2)`,
    cắt lát theo `open_date` — *"Một cấu hình = một tập lệnh"*. D9 KHÔNG đi qua
    `chay_wfo`: tầng (b) của `kiem_pham_vi_du_lieu` đòi `observed_end` của TỪNG
    fold, một lượt toàn cửa sổ chỉ qua được bằng cách KHAI ngày giả.
  • `DR-BC-01` §2 (18/09/2026): `main()` đặt chỗ **MỘT** suất cho cả cấu hình rồi
    truyền `GiayPhepChay` xuống; lõi chỉ CHỨNG MINH đã có đặt chỗ, không tạo ra nó.
    Lý do từ chối tự đặt chỗ ở tầng dưới — *không biết `budget_line` nào, đoán hộ
    là cách chắc chắn tiêu sai ngân sách* — giữ nguyên.
`chay_wfo` (thiết kế mỗi-fold-một-backtest, `DR-D3-01`) giữ nguyên, có test bảo vệ,
nhưng **hiện chưa có cổng nào dùng** (MT-61 (b)).

⚠️ **Đính chính tại chỗ (MT-61), giữ chữ cũ để ai đọc commit cũ không tưởng có hai
luật.** Bản trước viết: *"chưa có bộ chạy backtest thật ở bất kỳ đâu trong repo —
E1 `run_backtest.py` cũng còn `NotImplementedError`"* (sai từ `d2d3549`); và *"Chỗ
nối là `chay_mot_fold`"* (chữ TD-0145, lặp lại ở `d14f54c` — bản đó sửa theo
`DR-BC-01` §2 mà **không đối chiếu `DR-D9-01` §5.1**). Bản trước nữa còn viết
*"`chay_mot_fold` phải tự gọi `reserve()`"* — trái `DR-BC-01` §2.
"""

from __future__ import annotations

import argparse
import sys

from tool_d.config.loader import load_tool_d_config
from tool_d.gates.d0_pre import require_d0_pre_complete
from tool_d.lockbox.h17 import in_va_ma_thoat, kiem_h17
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
        "🛑 CHƯA CHẠY ĐƯỢC: E2 chưa nối bộ chạy (TD-0286 ⏸ theo DR-IQ-01 §1).",
        "   Lõi bộ chạy đã có (`tool_d.bo_chay`, E1 dùng từ TD-0313). D9 nối qua",
        "   `tool_d.wfo.lenh` — MỘT lượt mỗi cấu hình rồi cắt lát (DR-D9-01 §5.1),",
        "   KHÔNG qua `chay_wfo`. Đặt chỗ MỘT suất cho cả cấu hình ở main(),",
        "   TRƯỚC khi chạm dữ liệu (L-Z52, DR-BC-01 §2).",
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

    # H17 ở service CHE lockbox (DR-LOCKBOX-02, TD-0316): cách ly còn hiệu lực + seal không bị
    # sửa + sổ truy cập. Băm dữ liệu (`verify_all_seals`, L-Z14) là việc của E4 ở service
    # `lockbox` — ở đây dữ liệu bị che CÓ CHỦ ĐÍCH nên nó FAIL mọi lần (trước TD-0316: exit 89).
    ma_h17 = in_va_ma_thoat(
        kiem_h17(lockbox_dir=LOCKBOX_DIR, data_dir=LOCKBOX_FUTURES_DIR),
        ma_that_bai=EXIT_LOCKBOX_VERIFY_FAILED,
    )
    if ma_h17 is not None:
        return ma_h17

    print(in_so_do_fold())
    return EXIT_CHUA_CO_BO_CHAY


if __name__ == "__main__":
    sys.exit(main())
