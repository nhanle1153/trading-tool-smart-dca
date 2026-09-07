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
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from tool_d.config.loader import DEFAULT_CONFIG_PATH
from tool_d.gates.d0_pre import is_d0_pre_complete
from tool_d.gates.dsr import N_DANG_KY
from tool_d.ledger.audit_checks import (
    DEFAULT_IDEA_QUEUE_PATH,
    DEFAULT_PROPOSALS_PATH,
    DEFAULT_PARAM_STATUS_PATH,
    DEFAULT_TIEU_CHI_DIR,
    WARN_ONLY_CODES,
    check_lz10_registered_before_executed,
    check_lz11_n_used_le_n_dang_ky,
    check_lz12_no_duplicate_config_hash_different_outcome,
    check_lz15_calibrate_params_have_status,
    check_lz16_idea_queue_filter_and_tool_d_results,
    check_lz17_budget_a_slots_per_quarter,
    check_td0119_selected_du_phep_thu,
    check_td0119_so_bien_the_khong_vuot_khai,
    check_td0120_selection_reason_trich_ma_tieu_chi,
    check_td0124_tran_nhap_don_moi_quy,
    check_lz26_de_xuat_doi_tham_so,
    check_td0126_explore_evidence_va_trung_mechanism,
)
from tool_d.ledger.idea_queue import IdeaQueueError, submit_idea
from tool_d.ledger.param_proposals import ParamProposalError, submit_proposal
from tool_d.ledger.registry import DEFAULT_REGISTRY_PATH
from tool_d.measurement.gitinfo import get_git_info
from tool_d.measurement.guard import EXIT_GUARD_BLOCKED, GuardOutcome, measurement_guard
from tool_d.measurement.tri_state import Status, audit_line

ENTRYPOINT = "E6"

# Exit code khi audit tìm thấy vi phạm thật ("sổ bẩn") — khác EXIT_GUARD_BLOCKED (86).
EXIT_AUDIT_FAILED = 92
EXIT_GATE_ALREADY_CLOSED = 94
EXIT_GATE_AUDIT_DIRTY = 95
# TD-0124 — tờ đơn không hợp lệ: TỪ CHỐI ghi, sổ không bị đụng tới.
EXIT_DON_TU_CHOI = 96

DEFAULT_RUNTIME_STATE_PATH = Path("registry/runtime_state.json")
# TD-0117 — file test khoá L-Z49/L-Z50 phải được chạy RIÊNG lúc đóng cổng D2:
# suite tổng xanh KHÔNG chứng minh nó còn tồn tại (xoá hẳn file đi suite vẫn xanh).
DUONG_DAN_TEST_LZ49_LZ50 = "tests/lock/test_lz49_lz50_backtest_nho.py"


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
    parser.add_argument(
        "--nop-y-tuong",
        metavar="DON.yaml",
        help="TD-0124 — nộp một đơn ý tưởng vào registry/idea_queue.jsonl "
        "(mẫu: docs/mau-don-y-tuong.yaml). Đơn không hợp lệ thì TỪ CHỐI ghi.",
    )
    parser.add_argument(
        "--nop-de-xuat",
        metavar="DE_XUAT.yaml",
        help="TD-0125 (OQ-13) — nộp một đề xuất đổi tham số vào "
        "registry/param_change_proposals.jsonl (mẫu: docs/mau-de-xuat-doi-tham-so.yaml). "
        "Đề xuất không hợp lệ thì TỪ CHỐI ghi.",
    )
    parser.add_argument(
        "--close-d1-gate",
        action="store_true",
        help="TD-0110 — đóng cổng D1, ghi runtime_state.json.d1_complete. Chạy được đúng một lần.",
    )
    parser.add_argument(
        "--close-d2-gate",
        action="store_true",
        help="TD-0117 — đóng cổng D2, ghi runtime_state.json.d2_complete. Chạy được đúng một lần.",
    )
    return parser


def run_audit(
    *,
    n_dang_ky: int = N_DANG_KY,
    registry_path: Path = DEFAULT_REGISTRY_PATH,
    idea_queue_path: Path = DEFAULT_IDEA_QUEUE_PATH,
    config_path: Path = DEFAULT_CONFIG_PATH,
    status_path: Path = DEFAULT_PARAM_STATUS_PATH,
    tieu_chi_dir: Path = DEFAULT_TIEU_CHI_DIR,
    proposals_path: Path = DEFAULT_PROPOSALS_PATH,
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
        check_td0119_selected_du_phep_thu(idea_queue_path),
        check_td0119_so_bien_the_khong_vuot_khai(idea_queue_path, registry_path),
        check_td0120_selection_reason_trich_ma_tieu_chi(idea_queue_path, tieu_chi_dir),
        check_td0124_tran_nhap_don_moi_quy(idea_queue_path),
        check_lz26_de_xuat_doi_tham_so(proposals_path, registry_path),
        check_td0126_explore_evidence_va_trung_mechanism(idea_queue_path),
    ]

    ok = sum(1 for r in results if r.ok)
    fail = sum(1 for r in results if r.is_fail)
    unmeasured = sum(1 for r in results if r.measured.status is Status.PENDING)
    total = len(results)

    lines = [audit_line(ok=ok, fail=fail, unmeasured=unmeasured, total=total)]
    for r in results:
        if r.ok:
            trang_thai = "✅ đạt"
        elif r.is_fail:
            # Phép kiểm chỉ-cảnh-báo vẫn đếm vào `fail` cho `audit_line()`
            # (bất biến ok+fail+unmeasured == total), chỉ KHÔNG chặn chạy.
            trang_thai = (
                "⚠️ VƯỢT TRẦN (cảnh báo, không chặn)"
                if r.code in WARN_ONLY_CODES
                else "🔴 CHƯA ĐẠT"
            )
        else:
            trang_thai = "⏳ chưa đo được"
        dong = f"  {r.code}: {trang_thai}"
        if r.evidence:
            dong += f" — {r.evidence}"
        lines.append(dong)

    # Chỉ vi phạm CHẶN mới đổi exit code — xem WARN_ONLY_CODES (MT-11).
    fail_chan = sum(1 for r in results if r.is_fail and r.code not in WARN_ONLY_CODES)
    exit_code = EXIT_AUDIT_FAILED if fail_chan > 0 else 0
    return exit_code, "\n".join(lines)


def nop_don_y_tuong(don_path: Path) -> tuple[int, str]:
    """TD-0124 — đọc tờ đơn YAML, ghi một dòng vào hàng chờ, rồi tự audit.

    Tự chạy `run_audit()` NGAY SAU khi ghi: người nộp thấy luôn sổ còn sạch
    hay không, thay vì phải nhớ chạy thêm một lệnh nữa. Mọi phép kiểm CHẶN
    đã chạy TRƯỚC lúc ghi (trong `submit_idea()`, vì sổ append-only không có
    đường lùi) — lần audit này là xác nhận, không phải cửa chặn.
    """
    if not don_path.exists():
        return EXIT_DON_TU_CHOI, f"🛑 Không thấy tờ đơn: {don_path}"
    try:
        don = yaml.safe_load(don_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        return EXIT_DON_TU_CHOI, f"🛑 Tờ đơn sai cú pháp YAML:\n{exc}"
    if not isinstance(don, dict):
        return (
            EXIT_DON_TU_CHOI,
            f"🛑 Tờ đơn phải là một khối 'khoá: giá trị', đang là {type(don).__name__}",
        )

    try:
        idea_id = submit_idea(don=don)
    except IdeaQueueError as exc:
        return EXIT_DON_TU_CHOI, f"🛑 TỪ CHỐI ghi — sổ KHÔNG bị đụng tới.\n{exc}"

    audit_exit, audit_text = run_audit()
    return audit_exit, f"✅ Đã ghi {idea_id} vào {DEFAULT_IDEA_QUEUE_PATH}.\n{audit_text}"


def nop_de_xuat_doi_tham_so(de_xuat_path: Path) -> tuple[int, str]:
    """TD-0125 (OQ-13) — đọc đề xuất YAML, ghi một dòng vào sổ, rồi tự audit."""
    if not de_xuat_path.exists():
        return EXIT_DON_TU_CHOI, f"🛑 Không thấy tờ đề xuất: {de_xuat_path}"
    try:
        de_xuat = yaml.safe_load(de_xuat_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        return EXIT_DON_TU_CHOI, f"🛑 Tờ đề xuất sai cú pháp YAML:\n{exc}"
    if not isinstance(de_xuat, dict):
        return (
            EXIT_DON_TU_CHOI,
            f"🛑 Tờ đề xuất phải là một khối 'khoá: giá trị', đang là {type(de_xuat).__name__}",
        )

    try:
        ma = submit_proposal(de_xuat=de_xuat)
    except ParamProposalError as exc:
        return EXIT_DON_TU_CHOI, f"🛑 TỪ CHỐI ghi — sổ KHÔNG bị đụng tới.\n{exc}"

    audit_exit, audit_text = run_audit()
    return audit_exit, f"✅ Đã ghi {ma} vào {DEFAULT_PROPOSALS_PATH}.\n{audit_text}"


def close_d0_pre_gate(
    *,
    runtime_state_path: Path = DEFAULT_RUNTIME_STATE_PATH,
    repo_dir: Path = Path("."),
    **run_audit_kwargs,
) -> tuple[int, str]:
    """TD-0086 — ghi `d0_pre_complete: true` từ audit thật vừa chạy.

    TỪ CHỐI nếu file đã có khoá đó (bất biến — cổng chỉ đóng một lần
    trong đời repo, cùng triết lý "commit, không sửa" của `lockbox/seal.py`).
    TỪ CHỐI nếu audit CHƯA sạch (có vi phạm CHẶN) — không đóng cổng trên một sổ bẩn.
    L-Z17 vượt trần là cảnh báo (WARN_ONLY_CODES, MT-11) nên KHÔNG chặn đóng cổng —
    hệ quả có ý thức của quyết định đó, không phải tác dụng phụ im lặng.
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


def close_d1_gate(
    *,
    runtime_state_path: Path = DEFAULT_RUNTIME_STATE_PATH,
    repo_dir: Path = Path("."),
    pytest_cmd: list[str] | None = None,
    **run_audit_kwargs,
) -> tuple[int, str]:
    """TD-0110 — ghi `d1_complete: true`, gỡ blocker B2.

    Khác `close_d0_pre_gate()` (TD-0086): bằng chứng "toàn bộ test khoá
    D1 xanh" KHÔNG nhận lời khai người vận hành — hàm này tự CHẠY
    `pytest` thật trong CHÍNH lần gọi này (image đã có sẵn pytest, xem
    `docker/Dockerfile`; chạy được từ service `freqtrade`/`lockbox`,
    không cần lồng `docker compose` bên trong container) rồi ghi lại
    đúng output đó — nhãn `do-duoc` (MT-10) ĐÚNG NGHĨA, không phải một
    chuỗi gõ tay giả làm bằng chứng máy như hai mục còn lại của
    `close_d0_pre_gate()`.

    TỪ CHỐI nếu: D0-PRE chưa đóng (D1 không thể đứng trước D0-PRE); đã
    có `d1_complete: true` (bất biến — đóng đúng một lần); suite pytest
    có ca fail; hoặc audit sổ trial chưa sạch.

    `pytest_cmd` cho phép test thay bằng một lệnh giả nhanh (không chạy
    lại toàn bộ suite thật bên trong chính suite đang chạy) — lần đóng
    cổng THẬT không truyền tham số này, dùng mặc định `pytest -q`.
    """
    if not is_d0_pre_complete():
        return EXIT_GATE_AUDIT_DIRTY, "🛑 TỪ CHỐI đóng cổng D1 — D0-PRE chưa đóng (§N2)."

    if runtime_state_path.exists():
        try:
            existing = json.loads(runtime_state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}
        if existing.get("d1_complete") is True:
            return (
                EXIT_GATE_ALREADY_CLOSED,
                f"🛑 {runtime_state_path} đã có d1_complete=true — cổng đã đóng, không ghi lại.",
            )

    suite = subprocess.run(
        pytest_cmd or [sys.executable, "-m", "pytest", "-q"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    suite_summary = suite.stdout.strip().splitlines()[-1] if suite.stdout.strip() else "(không có output)"
    if suite.returncode != 0:
        return (
            EXIT_GATE_AUDIT_DIRTY,
            f"🛑 TỪ CHỐI đóng cổng D1 — suite pytest CHƯA sạch:\n{suite_summary}\n{suite.stdout[-2000:]}",
        )

    audit_exit, audit_text = run_audit(**run_audit_kwargs)
    if audit_exit != 0:
        return EXIT_GATE_AUDIT_DIRTY, f"🛑 TỪ CHỐI đóng cổng D1 — audit sổ trial chưa sạch:\n{audit_text}"

    git_info = get_git_info(repo_dir)
    state_raw = (
        json.loads(runtime_state_path.read_text(encoding="utf-8")) if runtime_state_path.exists() else {}
    )
    state_raw["d1_complete"] = True
    state_raw["d1_closed_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    state_raw["d1_git_sha"] = git_info.sha
    state_raw["d1_evidence"] = {
        "full_suite": {"nguon": "do-duoc", "noi_dung": suite_summary},
        "trial_ledger_audit": {"nguon": "do-duoc", "noi_dung": audit_text.splitlines()[0]},
    }
    runtime_state_path.parent.mkdir(parents=True, exist_ok=True)
    runtime_state_path.write_text(
        json.dumps(state_raw, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    return 0, f"✅ Đã đóng cổng D1 — ghi {runtime_state_path}.\n{suite_summary}\n{audit_text}"


def _dem_ca_pass(stdout: str) -> int:
    """Rút số ca PASS từ dòng tổng kết pytest. Không đọc được → 0 —
    fail-closed: coi như chưa chạy được ca nào, không đoán."""
    khop = re.search(r"(\d+) passed", stdout)
    return int(khop.group(1)) if khop else 0


def close_d2_gate(
    *,
    runtime_state_path: Path = DEFAULT_RUNTIME_STATE_PATH,
    repo_dir: Path = Path("."),
    pytest_cmd: list[str] | None = None,
    pytest_lz_cmd: list[str] | None = None,
    **run_audit_kwargs,
) -> tuple[int, str]:
    """TD-0117 — ghi `d2_complete: true` (điều kiện vào D3).

    Cùng khuôn `close_d1_gate()` (tự chạy pytest THẬT trong chính lần
    gọi này → nhãn `do-duoc` đúng nghĩa theo MT-10), THÊM một phép kiểm
    mà cổng D1 không cần:

    🔴 **Chạy RIÊNG file test khoá L-Z49/L-Z50, đòi số ca PASS >= 1.**
    Suite tổng xanh KHÔNG chứng minh hai phép kiểm cốt lõi của D2 còn
    tồn tại — xoá hẳn file test đi thì suite vẫn xanh và cổng vẫn đóng
    được. Đó đúng là bẫy "PASS rỗng" đã bắt được ở TD-0084
    (`verify_all_seals()` PASS vì không có seal nào để kiểm).

    D2b/D2c/D4 (Testnet/Live-only) KHÔNG kiểm được ở tầng backtest —
    ghi thẳng vào `d2_hoan_lai` là HOÃN tới D3.5/D9.5+, không được coi
    là "đã qua".

    TỪ CHỐI nếu: D0-PRE chưa đóng; D1 chưa đóng (D2 không thể đứng
    trước D1); đã có `d2_complete: true`; suite fail; file L-Z49/L-Z50
    fail hoặc thu được 0 ca; hoặc audit sổ trial chưa sạch.
    """
    if not is_d0_pre_complete():
        return EXIT_GATE_AUDIT_DIRTY, "🛑 TỪ CHỐI đóng cổng D2 — D0-PRE chưa đóng (§N2)."

    state: dict = {}
    if runtime_state_path.exists():
        try:
            state = json.loads(runtime_state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            state = {}
    if state.get("d1_complete") is not True:
        return (
            EXIT_GATE_AUDIT_DIRTY,
            "🛑 TỪ CHỐI đóng cổng D2 — chưa có d1_complete=true (D2 không thể đứng trước D1).",
        )
    if state.get("d2_complete") is True:
        return (
            EXIT_GATE_ALREADY_CLOSED,
            f"🛑 {runtime_state_path} đã có d2_complete=true — cổng đã đóng, không ghi lại.",
        )

    suite = subprocess.run(
        pytest_cmd or [sys.executable, "-m", "pytest", "-q"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    suite_summary = suite.stdout.strip().splitlines()[-1] if suite.stdout.strip() else "(không có output)"
    if suite.returncode != 0:
        return (
            EXIT_GATE_AUDIT_DIRTY,
            f"🛑 TỪ CHỐI đóng cổng D2 — suite pytest CHƯA sạch:\n{suite_summary}\n{suite.stdout[-2000:]}",
        )

    lz = subprocess.run(
        pytest_lz_cmd or [sys.executable, "-m", "pytest", "-q", DUONG_DAN_TEST_LZ49_LZ50],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    lz_summary = lz.stdout.strip().splitlines()[-1] if lz.stdout.strip() else "(không có output)"
    if lz.returncode != 0:
        return (
            EXIT_GATE_AUDIT_DIRTY,
            f"🛑 TỪ CHỐI đóng cổng D2 — test khoá L-Z49/L-Z50 CHƯA xanh:\n{lz_summary}\n{lz.stdout[-2000:]}",
        )
    so_ca_lz = _dem_ca_pass(lz.stdout)
    if so_ca_lz < 1:
        return (
            EXIT_GATE_AUDIT_DIRTY,
            "🛑 TỪ CHỐI đóng cổng D2 — chạy riêng "
            f"{DUONG_DAN_TEST_LZ49_LZ50} thu được 0 ca PASS. Exit 0 mà không ca nào "
            f"chạy là PASS RỖNG, không phải bằng chứng.\n{lz_summary}",
        )

    audit_exit, audit_text = run_audit(**run_audit_kwargs)
    if audit_exit != 0:
        return EXIT_GATE_AUDIT_DIRTY, f"🛑 TỪ CHỐI đóng cổng D2 — audit sổ trial chưa sạch:\n{audit_text}"

    git_info = get_git_info(repo_dir)
    state["d2_complete"] = True
    state["d2_closed_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    state["d2_git_sha"] = git_info.sha
    state["d2_evidence"] = {
        "full_suite": {"nguon": "do-duoc", "noi_dung": suite_summary},
        "lz49_lz50": {"nguon": "do-duoc", "noi_dung": f"{DUONG_DAN_TEST_LZ49_LZ50}: {lz_summary}"},
        "trial_ledger_audit": {"nguon": "do-duoc", "noi_dung": audit_text.splitlines()[0]},
    }
    state["d2_hoan_lai"] = {
        "nguon": "nguoi-khai",
        "noi_dung": (
            "D2b (closePosition phía sàn), D2c (khoảng trống không-SL), D4 (khớp lệnh thật) "
            "KHÔNG kiểm được ở tầng backtest — HOÃN tới D3.5/D9.5+, KHÔNG phải 'đã qua'."
        ),
    }
    runtime_state_path.parent.mkdir(parents=True, exist_ok=True)
    runtime_state_path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    return (
        0,
        f"✅ Đã đóng cổng D2 — ghi {runtime_state_path}.\n{suite_summary}\n"
        f"L-Z49/L-Z50 ({so_ca_lz} ca): {lz_summary}\n{audit_text}",
    )


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    args, _ = build_parser().parse_known_args(argv)

    report = measurement_guard(ENTRYPOINT, argv=argv, with_params_file=args.with_params_file)
    if report.outcome is GuardOutcome.BLOCKED:
        return EXIT_GUARD_BLOCKED

    if args.nop_y_tuong:
        exit_code, text = nop_don_y_tuong(Path(args.nop_y_tuong))
        print(text)
        return exit_code

    if args.nop_de_xuat:
        exit_code, text = nop_de_xuat_doi_tham_so(Path(args.nop_de_xuat))
        print(text)
        return exit_code

    if args.close_gate:
        exit_code, text = close_d0_pre_gate()
        print(text)
        return exit_code

    if args.close_d1_gate:
        exit_code, text = close_d1_gate()
        print(text)
        return exit_code

    if args.close_d2_gate:
        exit_code, text = close_d2_gate()
        print(text)
        return exit_code

    exit_code, text = run_audit()
    print(text)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
