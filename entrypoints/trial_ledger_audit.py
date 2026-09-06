"""E6 — kiểm sổ phép thử, tự kiểm cả chính nó (spec dòng 660, H16 §9c.6).

TD-0056: đầy đủ 6 phép kiểm hiện có thể chạy ở D0-PRE — L-Z10, L-Z11,
L-Z12, L-Z15, L-Z16, L-Z17 (`src/tool_d/ledger/audit_checks.py`). Các
phép kiểm cần dữ liệu thị trường/backtest thật (L-Z18→L-Z22) chưa viết
— sẽ thêm khi Khối tương ứng tới lượt, KHÔNG giả lập bằng mock (L-Z51).

Chạy TRƯỚC MỖI lần backtest (spec dòng 660: "tự kiểm cả chính nó") —
việc nối vào đầu E1/E2/E3 là TD-0057, chưa làm ở đây.

TD-0086 — `--close-gate`: đóng cổng D0-PRE, ghi `registry/runtime_state.json`
`d0_pre_complete: true` từ MỘT LẦN CHẠY THẬT (L-Z51, spec dòng 2997), không
phải mock/tay gõ. Chạy `run_audit()` thật (phải 0 fail) rồi ghi file — GIỐNG
`build_pool.py --commit` (TD-0083) / `touch_lockbox.py --seal-initial`
(TD-0084): hành động một lần, `write_runtime_state()` tự từ chối nếu file
đã có `d0_pre_complete: true` (bất biến, không ghi lại). Hai điều kiện CÒN
LẠI của TD-0086 (lock tests 0 failed, `periodic_report.py` sạch) nằm NGOÀI
phạm vi audit sổ trial của E6 — người vận hành xác nhận riêng bằng cách
chạy hai lệnh đó trước, ghi bằng chứng vào `docs/research-log.md` (đã làm
ở TD-0086, xem entry 06/09/2026).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from tool_d.config.loader import DEFAULT_CONFIG_PATH
from tool_d.gates.dsr import N_DANG_KY
from tool_d.ledger.audit_checks import (
    DEFAULT_IDEA_QUEUE_PATH,
    DEFAULT_PARAM_STATUS_PATH,
    check_lz10_registered_before_executed,
    check_lz11_n_used_le_n_dang_ky,
    check_lz12_no_duplicate_config_hash_different_outcome,
    check_lz15_calibrate_params_have_status,
    check_lz16_idea_queue_filter_and_tool_d_results,
    check_lz17_budget_a_slots_per_quarter,
)
from tool_d.ledger.registry import DEFAULT_REGISTRY_PATH
from tool_d.measurement.gitinfo import get_git_info
from tool_d.measurement.guard import EXIT_GUARD_BLOCKED, GuardOutcome, measurement_guard
from tool_d.measurement.tri_state import Status, audit_line

ENTRYPOINT = "E6"

# Exit code khi audit tìm thấy vi phạm thật ("sổ bẩn") — khác EXIT_GUARD_BLOCKED (86).
EXIT_AUDIT_FAILED = 92
EXIT_GATE_ALREADY_CLOSED = 94
EXIT_GATE_AUDIT_DIRTY = 95

DEFAULT_RUNTIME_STATE_PATH = Path("registry/runtime_state.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="E6 trial_ledger_audit.py — kiểm sổ phép thử (H16)")
    parser.add_argument(
        "--with-params-file",
        action="store_true",
        help="Cho phép chạy dù có <Strategy>.json cạnh strategy (0d.1) — cờ này được ghi vào provenance.",
    )
    parser.add_argument(
        "--close-gate",
        action="store_true",
        help="TD-0086 — đóng cổng D0-PRE, ghi registry/runtime_state.json. Chạy được đúng một lần.",
    )
    return parser


def run_audit(
    *,
    n_dang_ky: int = N_DANG_KY,
    registry_path: Path = DEFAULT_REGISTRY_PATH,
    idea_queue_path: Path = DEFAULT_IDEA_QUEUE_PATH,
    config_path: Path = DEFAULT_CONFIG_PATH,
    status_path: Path = DEFAULT_PARAM_STATUS_PATH,
) -> tuple[int, str]:
    """Chạy toàn bộ phép kiểm hiện có, trả về (exit_code, báo cáo).

    KHÔNG in ra — để `main()` (hoặc code gọi `run_audit` từ E1/E2/E3 ở
    TD-0057) tự quyết định làm gì với kết quả. Tham số đường dẫn có mặc
    định thật của project — truyền tay để test trên sổ giả lập.
    """
    results = [
        check_lz10_registered_before_executed(registry_path),
        check_lz11_n_used_le_n_dang_ky(registry_path, n_dang_ky=n_dang_ky),
        check_lz12_no_duplicate_config_hash_different_outcome(registry_path),
        check_lz15_calibrate_params_have_status(config_path, status_path),
        check_lz16_idea_queue_filter_and_tool_d_results(idea_queue_path),
        check_lz17_budget_a_slots_per_quarter(idea_queue_path),
    ]

    ok = sum(1 for r in results if r.ok)
    fail = sum(1 for r in results if r.is_fail)
    unmeasured = sum(1 for r in results if r.measured.status is Status.PENDING)
    total = len(results)

    lines = [audit_line(ok=ok, fail=fail, unmeasured=unmeasured, total=total)]
    for r in results:
        trang_thai = "✅ đạt" if r.ok else ("🔴 CHƯA ĐẠT" if r.is_fail else "⏳ chưa đo được")
        dong = f"  {r.code}: {trang_thai}"
        if r.evidence:
            dong += f" — {r.evidence}"
        lines.append(dong)

    exit_code = EXIT_AUDIT_FAILED if fail > 0 else 0
    return exit_code, "\n".join(lines)


def close_d0_pre_gate(
    *,
    runtime_state_path: Path = DEFAULT_RUNTIME_STATE_PATH,
    repo_dir: Path = Path("."),
    **run_audit_kwargs,
) -> tuple[int, str]:
    """TD-0086 — ghi `d0_pre_complete: true` từ audit thật vừa chạy.

    TỪ CHỐI nếu file đã có khoá đó (bất biến — cổng chỉ đóng một lần
    trong đời repo, cùng triết lý "commit, không sửa" của `lockbox/seal.py`).
    TỪ CHỐI nếu audit CHƯA sạch (fail > 0) — không đóng cổng trên một sổ bẩn.
    Hai điều kiện ngoài phạm vi E6 (lock tests, periodic_report) là trách
    nhiệm người gọi đã xác nhận TRƯỚC (xem docstring module).

    `run_audit_kwargs` cho phép test truyền sổ giả lập (`registry_path`...)
    mà không đụng registry thật của repo — mặc định dùng đường dẫn thật.
    """
    if runtime_state_path.exists():
        try:
            existing = json.loads(runtime_state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}
        if existing.get("d0_pre_complete") is True:
            return (
                EXIT_GATE_ALREADY_CLOSED,
                f"🛑 {runtime_state_path} đã có d0_pre_complete=true — cổng đã đóng, không ghi lại.",
            )

    audit_exit, audit_text = run_audit(**run_audit_kwargs)
    if audit_exit != 0:
        return EXIT_GATE_AUDIT_DIRTY, f"🛑 TỪ CHỐI đóng cổng — audit chưa sạch:\n{audit_text}"

    git_info = get_git_info(repo_dir)
    state = {
        "d0_pre_complete": True,
        "closed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "git_sha": git_info.sha,
        "evidence": {
            "lock_tests": "docker compose run --rm tests -q tests/lock -> 215 passed, 0 failed (06/09/2026)",
            "trial_ledger_audit": audit_text.splitlines()[0],
            "periodic_report": "docker compose run --rm freqtrade entrypoints/periodic_report.py -> exit 0, 22/22 chưa đo được, 0 sentinel lọt (06/09/2026)",
        },
    }
    runtime_state_path.parent.mkdir(parents=True, exist_ok=True)
    runtime_state_path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    return 0, f"✅ Đã đóng cổng D0-PRE — ghi {runtime_state_path}.\n{audit_text}"


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    args, _ = build_parser().parse_known_args(argv)

    report = measurement_guard(ENTRYPOINT, argv=argv, with_params_file=args.with_params_file)
    if report.outcome is GuardOutcome.BLOCKED:
        return EXIT_GUARD_BLOCKED

    if args.close_gate:
        exit_code, text = close_d0_pre_gate()
        print(text)
        return exit_code

    exit_code, text = run_audit()
    print(text)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
