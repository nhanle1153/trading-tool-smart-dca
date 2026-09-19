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
    check_td0277_loi_khai_frozen_khop_dia,
    check_lz16_idea_queue_filter_and_tool_d_results,
    check_lz17_budget_a_slots_per_quarter,
    check_td0119_selected_du_phep_thu,
    check_td0119_so_bien_the_khong_vuot_khai,
    check_td0120_selection_reason_trich_ma_tieu_chi,
    check_td0124_tran_nhap_don_moi_quy,
    check_lz26_de_xuat_doi_tham_so,
    check_td0126_explore_evidence_va_trung_mechanism,
    check_td0326_so_y_tuong_nhat_ky_su_kien,
    check_lz27_tran_b3,
    check_lz28_doi_tham_so_dung_diem_quyet_dinh,
)
from tool_d.ledger.backlog_check import bao_cao as bao_cao_backlog
from tool_d.ledger.idea_queue import IdeaQueueError, chon_y_tuong, huy_chon, submit_idea
from tool_d.ledger.param_proposals import ParamProposalError, submit_proposal
from tool_d.ledger.registry import DEFAULT_REGISTRY_PATH
from tool_d.measurement.gitinfo import get_git_info

# `_thay_doi_anh_huong_phep_do` chuyển sang `gitinfo` ngày 17/09/2026 (TD-0247,
# `DR-D1-03` §2) để E7 dùng chung đúng một quy tắc. Giữ tên cũ ở đây: cổng
# D3/D3.5 và test của chúng gọi/monkeypatch `trial_ledger_audit._thay_doi_anh_huong_phep_do`.
from tool_d.measurement.gitinfo import (  # noqa: F401 — THU_MUC_... tái xuất cho người đọc cũ
    THU_MUC_ANH_HUONG_PHEP_DO,
    thay_doi_anh_huong_phep_do as _thay_doi_anh_huong_phep_do,
)
from tool_d.measurement.guard import EXIT_GUARD_BLOCKED, GuardOutcome, measurement_guard
from tool_d.measurement.tri_state import Status, audit_line

ENTRYPOINT = "E6"

# Exit code khi audit tìm thấy vi phạm thật ("sổ bẩn") — khác EXIT_GUARD_BLOCKED (86).
EXIT_AUDIT_FAILED = 92
EXIT_GATE_ALREADY_CLOSED = 94
EXIT_GATE_AUDIT_DIRTY = 95
# TD-0124 — tờ đơn không hợp lệ: TỪ CHỐI ghi, sổ không bị đụng tới.
EXIT_DON_TU_CHOI = 96
# TD-0331 (OQ-15) — `--kiem-backlog` có cảnh báo. CHỈ để người đọc: không nối vào `run_audit()`
# hay cổng đóng, nên không thay đổi bất kỳ mã thoát nào của luồng audit/đóng cổng.
EXIT_BACKLOG_CO_CANH_BAO = 97

DEFAULT_RUNTIME_STATE_PATH = Path("registry/runtime_state.json")
# TD-0117 — file test khoá L-Z49/L-Z50 phải được chạy RIÊNG lúc đóng cổng D2:
# suite tổng xanh KHÔNG chứng minh nó còn tồn tại (xoá hẳn file đi suite vẫn xanh).
DUONG_DAN_TEST_LZ49_LZ50 = "tests/lock/test_lz49_lz50_backtest_nho.py"
# TD-0147 — ba file test khoá CỐT LÕI của D3, chạy RIÊNG lúc đóng cổng D3
# vì cùng lý do như D2: suite tổng xanh KHÔNG chứng minh chúng còn tồn tại.
# L-Z47 (ghép fold bằng NHÂN), L-Z45 (dedup_key), TD-0148 (L-Z55 phạm vi
# dữ liệu thật — chính là thứ đã CHẶN cổng này cho tới khi làm xong).
DUONG_DAN_TEST_D3 = (
    "tests/lock/test_lz47_can_doi_va_ghep_fold.py",
    "tests/lock/test_lz45_dedup_key_append_only.py",
    "tests/lock/test_td0148_pham_vi_du_lieu_that.py",
)
# TD-0166 — năm file test khoá CỐT LÕI của D3.5, mỗi file chạy RIÊNG một
# lượt. Phủ đủ BỐN thành phần của DR-015, không rút gọn còn "vài cái tiêu
# biểu": Bước 1 (Δ_R), Bước 2 (tỷ lệ không khớp), Bước 3 (đối chứng Z0),
# §4 (hiệu chỉnh hai chiều, L-Z58), và chốt chặn ablation (L-Z56).
DUONG_DAN_TEST_D3_5 = (
    "tests/unit/test_dr015_buoc1_lech_tranche.py",
    "tests/lock/test_td0162_ty_le_khong_khop.py",
    "tests/lock/test_td0163_doi_chung_z0.py",
    "tests/lock/test_lz58_hieu_chinh_hai_chieu.py",
    "tests/lock/test_lz56_chan_ablation_thieu_delta_r.py",
)
# TD-0337 (`DR-D4-14`) — file test khoá CỐT LÕI của D4, mỗi file chạy RIÊNG một lượt: tiêu chí
# đóng cổng (DR-D4-11), bản ghi arm (MT-36/37), trích lệnh, lệnh → bản ghi, bộ chạy E3 (L-Z52/53
# trên đường E3), gate §10.2 (L-Z57), và chốt L-Z56 mà E3 đứng sau.
DUONG_DAN_TEST_D4 = (
    "tests/lock/test_td0236_tieu_chi_dong_cong_d4.py",
    "tests/lock/test_td0232_ban_ghi_arm.py",
    "tests/lock/test_td0333_trich_lenh.py",
    "tests/lock/test_td0334_ban_ghi_arm_d4.py",
    "tests/lock/test_td0335_e3_bo_chay_ablation.py",
    "tests/lock/test_lz57_gate_d09.py",
    "tests/lock/test_lz56_chan_ablation_thieu_delta_r.py",
)


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
        "--chon-y-tuong",
        metavar="TO_CHON.yaml",
        help="TD-0326 (DR-IQ-02) — ghi sự kiện SELECTED cho một ý tưởng đang QUEUED. "
        "selected_at do máy đóng dấu; tờ chọn tự điền thì TỪ CHỐI.",
    )
    parser.add_argument(
        "--huy-chon",
        metavar="IQ-xxxx",
        help="TD-0326 (DR-IQ-02 §4.3) — ghi sự kiện VOIDED huỷ lần chọn đang hiệu lực. "
        "Bắt buộc kèm --ly-do trích một DR có thật.",
    )
    parser.add_argument("--ly-do", metavar="TEXT", help="Lý do cho --huy-chon.")
    parser.add_argument(
        "--kiem-backlog",
        action="store_true",
        help="TD-0331 (OQ-15) — báo dòng 🔒 đã có commit mã việc, ô trạng thái lẫn ký hiệu, "
        "và dòng mang cụm '⏸ TẠM DỪNG' mà trạng thái không ⏸. Chỉ BÁO, không chặn, không ghi file.",
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
    parser.add_argument(
        "--close-d3-gate",
        action="store_true",
        help="TD-0147 — đóng cổng D3, ghi runtime_state.json.d3_complete. Chạy được đúng một lần.",
    )
    parser.add_argument(
        "--close-d3-5-gate",
        action="store_true",
        help="TD-0166 — đóng cổng D3.5, ghi runtime_state.json.d3_5_complete. Chạy được đúng một lần.",
    )
    parser.add_argument(
        "--close-d4-gate",
        action="store_true",
        help="TD-0337 — đóng cổng D4 (DR-D4-11 §3), ghi runtime_state.json.d4_complete. Chạy được đúng một lần.",
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
        check_lz15_calibrate_params_have_status(config_path, status_path, registry_path),
        check_td0277_loi_khai_frozen_khop_dia(status_path),
        check_lz16_idea_queue_filter_and_tool_d_results(idea_queue_path),
        check_lz17_budget_a_slots_per_quarter(idea_queue_path),
        check_td0119_selected_du_phep_thu(idea_queue_path),
        check_td0119_so_bien_the_khong_vuot_khai(idea_queue_path, registry_path),
        check_td0120_selection_reason_trich_ma_tieu_chi(idea_queue_path, tieu_chi_dir),
        check_td0124_tran_nhap_don_moi_quy(idea_queue_path),
        check_lz26_de_xuat_doi_tham_so(proposals_path, registry_path),
        check_td0126_explore_evidence_va_trung_mechanism(idea_queue_path),
        check_td0326_so_y_tuong_nhat_ky_su_kien(idea_queue_path, registry_path, tieu_chi_dir),
        check_lz27_tran_b3(registry_path),
        check_lz28_doi_tham_so_dung_diem_quyet_dinh(proposals_path),
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


def chon_don_y_tuong(to_chon_path: Path) -> tuple[int, str]:
    """TD-0326 (DR-IQ-02) — đọc tờ chọn YAML, ghi sự kiện SELECTED, rồi tự audit."""
    if not to_chon_path.exists():
        return EXIT_DON_TU_CHOI, f"🛑 Không thấy tờ chọn: {to_chon_path}"
    try:
        to_chon = yaml.safe_load(to_chon_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        return EXIT_DON_TU_CHOI, f"🛑 Tờ chọn sai cú pháp YAML:\n{exc}"
    if not isinstance(to_chon, dict):
        return EXIT_DON_TU_CHOI, "🛑 Tờ chọn phải là một khối 'khoá: giá trị'"
    try:
        idea_id = chon_y_tuong(to_chon=to_chon)
    except IdeaQueueError as exc:
        return EXIT_DON_TU_CHOI, f"🛑 TỪ CHỐI ghi — sổ KHÔNG bị đụng tới.\n{exc}"
    audit_exit, audit_text = run_audit()
    return audit_exit, f"✅ Đã ghi {idea_id} SELECTED vào {DEFAULT_IDEA_QUEUE_PATH}.\n{audit_text}"


def huy_chon_y_tuong(idea_id: str, ly_do: str | None) -> tuple[int, str]:
    """TD-0326 (DR-IQ-02 §4.3) — ghi sự kiện VOIDED, rồi tự audit."""
    if not (ly_do or "").strip():
        return EXIT_DON_TU_CHOI, "🛑 --huy-chon bắt buộc kèm --ly-do trích một DR có thật."
    try:
        huy_chon(idea_id=idea_id, ly_do=ly_do)
    except IdeaQueueError as exc:
        return EXIT_DON_TU_CHOI, f"🛑 TỪ CHỐI ghi — sổ KHÔNG bị đụng tới.\n{exc}"
    audit_exit, audit_text = run_audit()
    return audit_exit, f"✅ Đã ghi {idea_id} VOIDED vào {DEFAULT_IDEA_QUEUE_PATH}.\n{audit_text}"


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



def close_d3_gate(
    *,
    runtime_state_path: Path = DEFAULT_RUNTIME_STATE_PATH,
    repo_dir: Path = Path("."),
    pytest_cmd: list[str] | None = None,
    pytest_d3_cmd: list[str] | None = None,
    **run_audit_kwargs,
) -> tuple[int, str]:
    """TD-0147 — ghi `d3_complete: true` (điều kiện vào D3.5).

    Cùng khuôn `close_d2_gate()`: tự chạy pytest THẬT trong chính lần gọi
    này (nhãn `do-duoc` đúng nghĩa, MT-10) và chạy RIÊNG bộ test khoá cốt
    lõi, đòi số ca PASS >= 1 — suite tổng xanh KHÔNG chứng minh chúng còn
    tồn tại (bẫy PASS RỖNG của TD-0084).

    🔴 **Cổng này KHÔNG có nghĩa "đã có kết quả walk-forward".** D3 dựng
    *bộ điều phối* H3-D và bịt bốn bug Tool A mà spec dòng 4340 liệt kê;
    nó KHÔNG sinh ra một con số WFO nào, vì chưa có bộ chạy backtest thật
    (E2 dừng ở `EXIT_CHUA_CO_BO_CHAY`). Điều đó ghi thẳng vào
    `d3_han_che` — đọc cổng D3 thành "đã có số" là hiểu sai đúng thứ mà
    PHẦN 0d tồn tại để chặn.

    TỪ CHỐI nếu: D0-PRE/D1/D2 chưa đóng (D3 không thể đứng trước D2); đã
    có `d3_complete: true`; suite fail; bất kỳ file test cốt lõi nào fail
    hoặc thu được 0 ca; hoặc audit sổ trial chưa sạch.
    """
    if not is_d0_pre_complete():
        return EXIT_GATE_AUDIT_DIRTY, "🛑 TỪ CHỐI đóng cổng D3 — D0-PRE chưa đóng (§N2)."

    state: dict = {}
    if runtime_state_path.exists():
        try:
            state = json.loads(runtime_state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            state = {}
    for khoa, ten in (("d1_complete", "D1"), ("d2_complete", "D2")):
        if state.get(khoa) is not True:
            return (
                EXIT_GATE_AUDIT_DIRTY,
                f"🛑 TỪ CHỐI đóng cổng D3 — chưa có {khoa}=true "
                f"(D3 không thể đứng trước {ten}).",
            )
    if state.get("d3_complete") is True:
        return (
            EXIT_GATE_ALREADY_CLOSED,
            f"🛑 {runtime_state_path} đã có d3_complete=true — cổng đã đóng, không ghi lại.",
        )

    # 🔴 Cây làm việc phải SẠCH trước khi chạy bất cứ phép đo nào.
    #
    # Project này thường có NHIỀU phiên cùng sửa MỘT thư mục đĩa (N12). Nếu
    # cây bẩn thì `d3_git_sha` ghi lại HEAD — một commit KHÔNG chứa thứ vừa
    # được kiểm. Bằng chứng khi đó tự mâu thuẫn: nó nói "đã kiểm ở sha X"
    # trong khi cái được kiểm là "X cộng vài file ai đó đang gõ dở".
    #
    # Đã xảy ra thật ở lần chạy đóng cổng D3 đầu tiên (08/09/2026): 8 ca đỏ
    # thoáng qua vì suite chạy 6,5 phút, đúng lúc phiên song song sửa dở
    # `registry.py`. Lần đó cổng từ chối vì suite đỏ — nhưng nếu các sửa đổi
    # kia tình cờ không làm đỏ test nào thì cổng đã đóng, với bằng chứng sai.
    #
    # Cách gỡ khi gặp: bảo phiên kia commit, rồi chạy lại. Đây là điều kiện
    # ĐẠT ĐƯỢC, không phải bế tắc.
    git_info = get_git_info(repo_dir)
    ban = _thay_doi_anh_huong_phep_do(repo_dir)
    if ban:
        return (
            EXIT_GATE_AUDIT_DIRTY,
            "🛑 TỪ CHỐI đóng cổng D3 — cây làm việc có thay đổi ẢNH HƯỞNG PHÉP ĐO "
            "nhưng chưa commit. Đóng cổng lúc này sẽ ghi d3_git_sha = "
            f"{git_info.sha[:12]} cho một lần kiểm KHÔNG chạy trên đúng commit đó.\n"
            + "\n".join(f"  {d}" for d in ban)
            + "\nBảo phiên đang sửa commit xong rồi chạy lại.",
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
            f"🛑 TỪ CHỐI đóng cổng D3 — suite pytest CHƯA sạch:\n{suite_summary}\n{suite.stdout[-2000:]}",
        )

    # Mỗi file chạy RIÊNG, không gộp một lượt: gộp lại thì một file bị xoá
    # hoặc lọc hết vẫn cho tổng > 0 nhờ hai file kia, và cổng vẫn đóng được
    # trong khi một phép kiểm cốt lõi đã biến mất.
    d3_bang_chung: list[str] = []
    for duong_dan in DUONG_DAN_TEST_D3:
        lenh = (
            [*pytest_d3_cmd, duong_dan]
            if pytest_d3_cmd
            else [sys.executable, "-m", "pytest", "-q", duong_dan]
        )
        kq = subprocess.run(lenh, cwd=repo_dir, capture_output=True, text=True)
        tom_tat = kq.stdout.strip().splitlines()[-1] if kq.stdout.strip() else "(không có output)"
        if kq.returncode != 0:
            return (
                EXIT_GATE_AUDIT_DIRTY,
                f"🛑 TỪ CHỐI đóng cổng D3 — test khoá cốt lõi CHƯA xanh: "
                f"{duong_dan}\n{tom_tat}\n{kq.stdout[-2000:]}",
            )
        so_ca = _dem_ca_pass(kq.stdout)
        if so_ca < 1:
            return (
                EXIT_GATE_AUDIT_DIRTY,
                f"🛑 TỪ CHỐI đóng cổng D3 — chạy riêng {duong_dan} thu được 0 ca "
                f"PASS. Exit 0 mà không ca nào chạy là PASS RỖNG, không phải "
                f"bằng chứng.\n{tom_tat}",
            )
        d3_bang_chung.append(f"{duong_dan}: {tom_tat}")

    audit_exit, audit_text = run_audit(**run_audit_kwargs)
    if audit_exit != 0:
        return EXIT_GATE_AUDIT_DIRTY, f"🛑 TỪ CHỐI đóng cổng D3 — audit sổ trial chưa sạch:\n{audit_text}"

    state["d3_complete"] = True
    state["d3_closed_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    state["d3_git_sha"] = git_info.sha
    state["d3_cay_sach"] = True  # đã kiểm ở đầu hàm, không đóng cổng trên cây bẩn
    state["d3_evidence"] = {
        "full_suite": {"nguon": "do-duoc", "noi_dung": suite_summary},
        "test_khoa_d3": {"nguon": "do-duoc", "noi_dung": " | ".join(d3_bang_chung)},
        "trial_ledger_audit": {"nguon": "do-duoc", "noi_dung": audit_text.splitlines()[0]},
    }
    state["d3_han_che"] = {
        "nguon": "nguoi-khai",
        "noi_dung": (
            "Cổng D3 chứng nhận BỘ ĐIỀU PHỐI H3-D đúng, KHÔNG chứng nhận đã có kết "
            "quả walk-forward. (1) Chưa có bộ chạy backtest thật — E2 dừng ở "
            "EXIT_CHUA_CO_BO_CHAY, toàn bộ phép kiểm mới chỉ được nuôi bằng bộ chạy "
            "GIẢ trong test; bảo đảm trên dữ liệu thật là việc của D3.5. "
            "(2) Phép kiểm phạm vi dữ liệu (TD-0148) VẪN TIN LỜI KHAI của bộ chạy: "
            "bộ chạy trả ngày dự kiến thay vì ngày thật đọc từ dataframe sẽ vô hiệu "
            "hoá nó. (3) DR-D3-01 §5.3: với 19-47 lệnh/fold ước tính, nhiều fold có "
            "thể rơi dưới sàn 30 và ghi `unreadable` — khi đó D3 kết luận đúng phạm "
            "vi là 'orchestrator ĐÚNG, thống kê CHƯA ĐỌC ĐƯỢC', phán quyết thống kê "
            "hoãn tới D9."
        ),
    }
    runtime_state_path.parent.mkdir(parents=True, exist_ok=True)
    runtime_state_path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    return (
        0,
        f"✅ Đã đóng cổng D3 — ghi {runtime_state_path}.\n{suite_summary}\n"
        + "\n".join(f"  {d}" for d in d3_bang_chung)
        + f"\n{audit_text}",
    )


def _chay_rieng_tung_file(
    duong_dans: tuple[str, ...],
    *,
    ten_cong: str,
    repo_dir: Path,
    pytest_cmd: list[str] | None,
) -> tuple[str | None, list[str]]:
    """Chạy RIÊNG từng file test khoá, đòi mỗi file có >= 1 ca PASS.

    Trả `(lý_do_từ_chối, bằng_chứng)` — `None` ở vế đầu nghĩa là đạt.

    🔴 Mỗi file MỘT lượt, không gộp: gộp lại thì một file bị xoá hoặc lọc
    hết vẫn cho tổng `N passed > 0` nhờ các file kia, và cổng vẫn đóng
    được trong khi một phép kiểm cốt lõi đã biến mất (bài học TD-0117).
    """
    bang_chung: list[str] = []
    for duong_dan in duong_dans:
        lenh = (
            [*pytest_cmd, duong_dan]
            if pytest_cmd
            else [sys.executable, "-m", "pytest", "-q", duong_dan]
        )
        kq = subprocess.run(lenh, cwd=repo_dir, capture_output=True, text=True)
        tom_tat = kq.stdout.strip().splitlines()[-1] if kq.stdout.strip() else "(không có output)"
        if kq.returncode != 0:
            return (
                f"🛑 TỪ CHỐI đóng cổng {ten_cong} — test khoá cốt lõi CHƯA xanh: "
                f"{duong_dan}\n{tom_tat}\n{kq.stdout[-2000:]}",
                bang_chung,
            )
        if _dem_ca_pass(kq.stdout) < 1:
            return (
                f"🛑 TỪ CHỐI đóng cổng {ten_cong} — chạy riêng {duong_dan} thu được 0 ca "
                f"PASS. Exit 0 mà không ca nào chạy là PASS RỖNG, không phải bằng "
                f"chứng.\n{tom_tat}",
                bang_chung,
            )
        bang_chung.append(f"{duong_dan}: {tom_tat}")
    return None, bang_chung


def close_d3_5_gate(
    *,
    runtime_state_path: Path = DEFAULT_RUNTIME_STATE_PATH,
    repo_dir: Path = Path("."),
    pytest_cmd: list[str] | None = None,
    pytest_d35_cmd: list[str] | None = None,
    **run_audit_kwargs,
) -> tuple[int, str]:
    """TD-0166 — ghi `d3_5_complete: true` (điều kiện vào D4).

    Cùng khuôn `close_d3_gate()` và mang theo cả ba bài học của lần đóng
    cổng D3 hôm nay: tự chạy pytest THẬT (nhãn `do-duoc`, MT-10), kiểm
    cây làm việc **không có thay đổi ảnh hưởng phép đo**, và chạy RIÊNG
    từng file test cốt lõi.

    🔴 **Điểm khác biệt lớn nhất so với ba cổng trước: cổng này gọi
    `kiem_cong_d35()` — chính cái máy mà E3 dùng để TỪ CHỐI chạy
    ablation.** Nghĩa là điều kiện đóng cổng D3.5 và điều kiện cho phép
    chạy ablation là **MỘT**, không phải hai danh sách song song sẽ trôi
    lệch nhau. Nó kiểm ba artifact của D3.5 đã commit thật, và tính lại
    Δ_R từ dữ liệu thô để chắc artifact chưa trôi khỏi code.

    TỪ CHỐI nếu: bất kỳ cổng D0-PRE/D1/D2/D3 nào chưa đóng; đã có
    `d3_5_complete`; cây có thay đổi chưa commit ảnh hưởng phép đo; suite
    fail; bất kỳ file test cốt lõi nào fail hoặc 0 ca; `kiem_cong_d35()`
    từ chối; hoặc audit sổ trial chưa sạch.
    """
    if not is_d0_pre_complete():
        return EXIT_GATE_AUDIT_DIRTY, "🛑 TỪ CHỐI đóng cổng D3.5 — D0-PRE chưa đóng (§N2)."

    state: dict = {}
    if runtime_state_path.exists():
        try:
            state = json.loads(runtime_state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            state = {}
    for khoa, ten in (("d1_complete", "D1"), ("d2_complete", "D2"), ("d3_complete", "D3")):
        if state.get(khoa) is not True:
            return (
                EXIT_GATE_AUDIT_DIRTY,
                f"🛑 TỪ CHỐI đóng cổng D3.5 — chưa có {khoa}=true "
                f"(D3.5 không thể đứng trước {ten}).",
            )
    if state.get("d3_5_complete") is True:
        return (
            EXIT_GATE_ALREADY_CLOSED,
            f"🛑 {runtime_state_path} đã có d3_5_complete=true — cổng đã đóng, không ghi lại.",
        )

    git_info = get_git_info(repo_dir)
    ban = _thay_doi_anh_huong_phep_do(repo_dir)
    if ban:
        return (
            EXIT_GATE_AUDIT_DIRTY,
            "🛑 TỪ CHỐI đóng cổng D3.5 — cây làm việc có thay đổi ẢNH HƯỞNG PHÉP ĐO "
            f"nhưng chưa commit. d3_5_git_sha = {git_info.sha[:12]} sẽ KHÔNG khớp thứ "
            "vừa được kiểm.\n" + "\n".join(f"  {d}" for d in ban),
        )

    # 🔴 Cùng một máy mà E3 dùng để TỪ CHỐI chạy ablation. Điều kiện đóng
    # cổng và điều kiện chạy ablation là MỘT — hai danh sách song song sẽ
    # trôi lệch, và lúc đó "cổng đã đóng" không còn bảo đảm E3 chạy được.
    from tool_d.dr015.cong_d35 import CongD35ChuaDongError, kiem_cong_d35

    try:
        delta_niem_phong = kiem_cong_d35(repo_dir=repo_dir)
    except CongD35ChuaDongError as exc:
        return EXIT_GATE_AUDIT_DIRTY, f"🛑 TỪ CHỐI đóng cổng D3.5 — {exc}"

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
            f"🛑 TỪ CHỐI đóng cổng D3.5 — suite pytest CHƯA sạch:\n{suite_summary}\n"
            f"{suite.stdout[-2000:]}",
        )

    ly_do, d35_bang_chung = _chay_rieng_tung_file(
        DUONG_DAN_TEST_D3_5, ten_cong="D3.5", repo_dir=repo_dir, pytest_cmd=pytest_d35_cmd
    )
    if ly_do:
        return EXIT_GATE_AUDIT_DIRTY, ly_do

    audit_exit, audit_text = run_audit(**run_audit_kwargs)
    if audit_exit != 0:
        return (
            EXIT_GATE_AUDIT_DIRTY,
            f"🛑 TỪ CHỐI đóng cổng D3.5 — audit sổ trial chưa sạch:\n{audit_text}",
        )

    state["d3_5_complete"] = True
    state["d3_5_closed_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    state["d3_5_git_sha"] = git_info.sha
    state["d3_5_cay_sach"] = True
    state["d3_5_delta_r_niem_phong"] = {
        h: v.get("gia_tri") if v.get("trang_thai") == "ok" else v.get("trang_thai")
        for h, v in delta_niem_phong.items()
    }
    state["d3_5_evidence"] = {
        "full_suite": {"nguon": "do-duoc", "noi_dung": suite_summary},
        "test_khoa_d3_5": {"nguon": "do-duoc", "noi_dung": " | ".join(d35_bang_chung)},
        "cong_d35_kiem_cong": {
            "nguon": "do-duoc",
            "noi_dung": "kiem_cong_d35() PASS — ba artifact đã commit, Δ_R tính lại khớp",
        },
        "trial_ledger_audit": {"nguon": "do-duoc", "noi_dung": audit_text.splitlines()[0]},
    }
    state["d3_5_han_che"] = {
        "nguon": "nguoi-khai",
        "noi_dung": (
            "(1) Bước 2 đo GIÁN TIẾP: suy tỷ lệ không khớp từ dữ liệu khớp lệnh thật, "
            "KHÔNG đặt lệnh thật (DR-D35-01 — testnet bị loại vì sổ lệnh riêng, con số ở "
            "đó nói về một thị trường khác). Ba thứ KHÔNG quan sát được: post-only bị sàn "
            "từ chối, khớp MỘT PHẦN, vị trí hàng đợi — cả ba tính về phía p_nf_cao, không "
            "cái nào làm kết luận lạc quan hơn thực tế. "
            "(2) Chỉ hướng LONG (ZoneAbsorptionMinimal LONG-only, TD-0114); Δ_R(SHORT) là "
            "`unreadable`, KHÔNG phải 0. Bật Short thì L-Z56 sẽ TỪ CHỐI chạy ablation cho "
            "tới khi có Δ_R(SHORT) thật. "
            "(3) 🔴 Bước 3 kết luận hai nhánh lệch TƯƠNG ĐƯƠNG (Δ_R Z0/DCA = 1,04) — phần "
            "lớn Δ_R là sai số CHUNG cho cả hai nhánh và tự triệt tiêu khi so sánh, nên "
            "hiệu chỉnh của §4 RỘNG HƠN bất lợi thực của riêng DCA. Đọc kết quả §4 mà "
            "thiếu câu này là để một phép phạt bất đối xứng chạy sau khi đã mất phần lớn "
            "căn cứ. "
            "(4) p_nf = 0 đo trên tập backtest ĐÃ CẤP khớp — đúng tập §3 cần (phép hiệu "
            "chỉnh trừ đi tranche 'backtest đã cho'), KHÔNG trả lời câu rộng hơn 'mô hình "
            "khớp của backtest có rộng tay nói chung không'."
        ),
    }
    runtime_state_path.parent.mkdir(parents=True, exist_ok=True)
    runtime_state_path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    return (
        0,
        f"✅ Đã đóng cổng D3.5 — ghi {runtime_state_path}.\n{suite_summary}\n"
        + "\n".join(f"  {d}" for d in d35_bang_chung)
        + f"\n{audit_text}",
    )


#: `DR-D4-04` §7 (TD-0186): bốn bằng chứng `do-duoc` cổng D4 phải có — thiếu một ⇒ TỪ CHỐI.
#: "D4 chạy trên hệ thống 40 USDT / ¼¼½ / không-TP là D4 của một hệ thống khác."
BANG_CHUNG_DR_D4_04 = (
    ("chien_luoc_da_chay", "tên chiến lược đã chạy = ZoneAbsorption (không phải Minimal)"),
    ("ti_trong_tranche_fill", "tỉ trọng tranche đo từ fill THẬT = ⅓⅓⅓"),
    ("stake_theo_r_eff", "stake biến thiên theo 1/R_eff"),
    ("h4_tp_fallback", "H-4 — tỉ lệ TP rơi nạng"),
)

#: TD-0338 — hai tiêu chí Nhánh 1 dạng "bộ test PASS" (`gates/d0_9.TIEU_CHI_BO_TEST`), mỗi file chạy RIÊNG.
DUONG_DAN_TEST_H4D = (
    "tests/lock/test_lz1_confirmed_at_bar.py",
    "tests/lock/test_td0105_zss_confirmed_at_bar_audit.py",
    "tests/lock/test_td0170_lookahead_cong_dg.py",
)
#: L-Z10…L-Z33 (spec §9c.6). L-Z10/11/12/15/16/17 sống trong `test_audit_checks.py`, L-Z20 trong `test_notional.py`;
#: L-Z21/22 có test từ TD-0338; L-Z23 không có trong spec. Phần tử có thể là mẫu glob — mỗi mẫu phải khớp ĐÚNG MỘT file
#: (`_mo_rong_mau`), thiếu hay thừa ⇒ tiêu chí `unreadable`, không PASS rỗng.
DUONG_DAN_TEST_LZ10_LZ33 = (
    "tests/unit/test_audit_checks.py",
    "tests/lock/test_lz13_lockbox_access_log.py",
    "tests/lock/test_lz14_lockbox_seal_hash.py",
    "tests/lock/test_td0190_lz15_pham_vi_tu_tier_b.py",
    "tests/lock/test_td0118_lz17_canh_bao_khong_chan.py",
    "tests/lock/test_lz18_time_stop_ceiling.py",
    "tests/lock/test_lz19_hold_duration_recorded.py",
    "tests/unit/test_notional.py",
    "tests/lock/test_lz21_lz22_ket_nap_danh_muc.py",
    "tests/lock/test_lz24_freqtrade_config_flags.py",
    "tests/lock/test_lz25_*.py",  # mẫu glob: tên file chứa chuỗi L-Z25 cấm trong mã chạy được
    "tests/lock/test_lz26_de_xuat_doi_tham_so.py",
    "tests/lock/test_lz27_lz28_ngan_sach_b3_va_diem_quyet_dinh.py",
    "tests/lock/test_lz29_dof_accounting.py",
    "tests/lock/test_lz30_funding_stop_ceiling.py",
    "tests/lock/test_lz31_funding_paid_recorded.py",
    "tests/lock/test_lz32_forbidden_leverage_vars.py",
    "tests/lock/test_lz33_no_15m_timeframe.py",
)


def _theo_arm(ban_ghi: list[dict]) -> dict[str, dict]:
    return {bg.get("arm"): bg for bg in ban_ghi}


def _chi_so(bg: dict | None, khoa: str):
    """Một ô `chi_so` của bản ghi arm → `Measured`; thiếu bản ghi/thiếu khoá ⇒ `pending` (không bịa)."""
    from tool_d.measurement.tri_state import Measured, Status

    if bg is None:
        return Measured.pending("không có bản ghi arm")
    o = (bg.get("chi_so") or {}).get(khoa)
    if not isinstance(o, dict) or "status" not in o:
        return Measured.pending(f"bản ghi không có chi_so.{khoa}")
    return Measured(status=Status(o["status"]), value=o.get("value"), note=o.get("note"))


def _d4_han_che(ban_ghi: list[dict]) -> str:
    """`DR-D4-12` §10(f) — SÁU điều, cộng nguồn `planned_risk_usdt` (`DR-D4-14` §10) và §1.7 (`DR-D4-15`)."""
    theo = _theo_arm(ban_ghi)
    kc = (theo.get("Z0-T1") or {}).get("ket_cuc", {}).get("value")
    b17 = _chi_so(theo.get("Z3"), "bat_bien_1_7_ty_so_trung_vi")
    muc_17 = f"trung vị {b17.value:.4f}" if b17.is_ok() else f"không đo được — {b17.note}"
    muc_6 = (
        f"(6) Kết cục Z0-T1 = {kc} — khai thẳng: ở cỡ mẫu này D4 KHÔNG phân biệt được lợi thế với may mắn "
        "(DR-D4-12 §2). "
        if kc == "INCONCLUSIVE"
        else f"(6) Kết cục Z0-T1 = {kc}. "
    )
    return (
        "(1) Chỉ hướng LONG (DR-D4-01); Short HOÃN — cần DG7 riêng + Δ_R(SHORT) + lockbox mới; 'đã đóng cho Long' "
        "KHÔNG có nghĩa 'đã phủ cả hai hướng'. "
        "(2) D4 KHÔNG phán quyết câu DCA (DR-D4-10 §2.4): mặc định Z0 single-entry, DCA vào Idea Queue với nhãn "
        "'chưa từng được đo, không phải đã thất bại'; arm Z3 chỉ mua con số MÔ TẢ. "
        "(3) Rổ: K = 52,6% (DR-D4-12 §3) — chiều lệch tần suất CHƯA ĐO. "
        "(4) Chỉ chạy 4/9 arm (DR-D4-12 §4): Z0-T1 phán quyết; Z0/Z0-T0/Z3 mô tả; 5 arm bị cắt 'chưa từng được đo'; "
        "N giữ 114. "
        "(5) Skewness-so-Z1: KHÔNG ÁP DỤNG cho Z0-T1 (arm entry đơn, DR-D9-02 b′) — không phải 'đạt', không phải "
        "'chưa đo'. "
        + muc_6
        + "(7) planned_risk_usdt SUY NGƯỢC từ fill tranche 1 (DR-D4-14 §10). "
        + f"(8) Bất biến §1.7 (DR-D4-15): {muc_17}."
    )


def _dem_b2_da_tieu(registry_path: Path) -> int:
    from tool_d.ledger.registry import TrialLedger, TrialState

    return sum(
        1
        for p in TrialLedger(path=registry_path).projections().values()
        if p.budget_line == "B2" and p.state is TrialState.CONSUMED
    )


def _doc_ban_ghi_arm(runs_dir: Path) -> tuple[list[dict], list[str]]:
    ban_ghi: list[dict] = []
    loi: list[str] = []
    for duong in sorted(runs_dir.glob("*/arm_result.json")):
        try:
            ban_ghi.append(json.loads(duong.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError) as exc:
            loi.append(f"{duong}: không đọc được ({exc})")
    return ban_ghi, loi


def _bang_chung_dr_d4_04(ban_ghi: list[dict], runs_dir: Path) -> tuple[dict, list[str]]:
    """Bốn bằng chứng `DR-D4-04` §7 (TD-0339), đọc từ hiện vật của E3 — không nhận lời khai (MT-10).

    (i) `ket_qua_chay.json` của MỌI bản ghi: `chien_luoc` = `ZoneAbsorption` (khoá báo cáo thật, `doc_ket_qua`).
    (ii) `Z3` (arm DCA duy nhất của lô): `ti_trong_tranche_dat` đo được và đạt.
    (iii) `Z0-T1`: `stake_theo_r_eff_rho` đo được và > 0.
    (iv) `Z0-T1`: `tp_fallback_ratio` đo được (ngưỡng ≤ 40% là việc của gate §10.2, không phải của bằng chứng).
    Trả `(bằng chứng, vấn đề)`; vấn đề ≠ rỗng ⇒ cổng TỪ CHỐI (TD-0186: *"Thiếu một ⇒ cổng từ chối"*).
    """
    theo = _theo_arm(ban_ghi)
    bc: dict[str, str] = {}
    van_de: list[str] = []

    if not ban_ghi:
        van_de.append("chien_luoc_da_chay: 0 bản ghi arm")
    else:
        sai = []
        for bg in ban_ghi:
            f = runs_dir / str(bg.get("trial_id")) / "ket_qua_chay.json"
            try:
                ten = json.loads(f.read_text(encoding="utf-8")).get("chien_luoc")
            except (OSError, json.JSONDecodeError):
                ten = None
            if ten != "ZoneAbsorption":
                sai.append(f"{bg.get('arm')}: {ten!r}")
        if sai:
            van_de.append(f"chien_luoc_da_chay: {sai}")
        else:
            bc["chien_luoc_da_chay"] = f"{len(ban_ghi)}/{len(ban_ghi)} lượt = ZoneAbsorption (khoá báo cáo thật)"

    for ten, arm, khoa, dat in (
        ("ti_trong_tranche_fill", "Z3", "ti_trong_tranche_dat", lambda v: v is True),
        ("stake_theo_r_eff", "Z0-T1", "stake_theo_r_eff_rho", lambda v: v > 0),
        ("h4_tp_fallback", "Z0-T1", "tp_fallback_ratio", lambda v: True),
    ):
        m = _chi_so(theo.get(arm), khoa)
        if not m.is_ok():
            van_de.append(f"{ten}: {arm}.{khoa} không đo được — {m.note}")
        elif not dat(m.value):
            van_de.append(f"{ten}: {arm}.{khoa} = {m.value!r} — ĐO ĐƯỢC mà không đạt")
        else:
            bc[ten] = f"{arm}.{khoa} = {m.value!r}"
    return bc, van_de


def _mo_rong_mau(duong_dans: tuple[str, ...], repo_dir: Path) -> tuple[str, ...]:
    """Mẫu glob → đường dẫn thật; mỗi phần tử phải khớp ĐÚNG MỘT file."""
    ra = []
    for d in duong_dans:
        khop = sorted(repo_dir.glob(d)) if any(c in d for c in "*?[") else [repo_dir / d]
        if len(khop) != 1 or not khop[0].is_file():
            raise FileNotFoundError(f"{d}: khớp {len(khop)} file (cần đúng 1)")
        ra.append(str(khop[0].relative_to(repo_dir)).replace("\\", "/"))
    return tuple(ra)


def _chay_bo_test(duong_dans: tuple[str, ...], *, ten: str, repo_dir: Path, pytest_cmd: list[str] | None):
    """Tiêu chí dạng "bộ test PASS" → `Measured[bool]`. 0 ca PASS là KHÔNG ĐO ĐƯỢC, không phải trượt."""
    from tool_d.measurement.tri_state import Measured

    try:
        duong_dans = _mo_rong_mau(duong_dans, repo_dir)
    except FileNotFoundError as exc:
        return Measured.unreadable(str(exc))
    ly_do, _ = _chay_rieng_tung_file(duong_dans, ten_cong=ten, repo_dir=repo_dir, pytest_cmd=pytest_cmd)
    if ly_do is None:
        return Measured.ok(True)
    if "0 ca PASS" in ly_do:
        return Measured.unreadable(ly_do.splitlines()[0])
    return Measured.ok(False)


def close_d4_gate(
    *,
    runtime_state_path: Path = DEFAULT_RUNTIME_STATE_PATH,
    repo_dir: Path = Path("."),
    runs_dir: Path = Path("runs"),
    registry_path: Path = DEFAULT_REGISTRY_PATH,
    pytest_cmd: list[str] | None = None,
    pytest_d4_cmd: list[str] | None = None,
    pytest_bo_test_cmd: list[str] | None = None,
    **run_audit_kwargs,
) -> tuple[int, str]:
    """TD-0337 (`DR-D4-14`, phần dựng của TD-0186) — ghi `d4_complete: true` (điều kiện vào D5).

    Khuôn `close_d3_5_gate()`. Tiêu chí là `DR-D4-11` §3 — cổng đóng bằng HIỆN VẬT, không bằng
    số trial đã tiêu — và hàm này **gọi** `kiem_tieu_chi_dong_d4()` chứ không khai lại luật.
    Cộng bốn bằng chứng `DR-D4-04` §7 mà TD-0186 đòi.

    Các phép kiểm RẺ (bản ghi, sổ, tiêu chí, bằng chứng) đứng TRƯỚC suite pytest: từ chối sớm.

    🔴 Hành vi mong đợi hôm nay (`DR-D4-14` §8): TỪ CHỐI — 0 bản ghi arm, 0 suất B2, và bốn
    bằng chứng `DR-D4-04` §7 chưa có nguồn. Đó là cổng làm đúng việc, không phải cổng hỏng.
    """
    if not is_d0_pre_complete():
        return EXIT_GATE_AUDIT_DIRTY, "🛑 TỪ CHỐI đóng cổng D4 — D0-PRE chưa đóng (§N2)."

    state: dict = {}
    if runtime_state_path.exists():
        try:
            state = json.loads(runtime_state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            state = {}
    for khoa in ("d1_complete", "d2_complete", "d3_complete", "d3_5_complete"):
        if state.get(khoa) is not True:
            return EXIT_GATE_AUDIT_DIRTY, f"🛑 TỪ CHỐI đóng cổng D4 — chưa có {khoa}=true."
    if state.get("d4_complete") is True:
        return (
            EXIT_GATE_ALREADY_CLOSED,
            f"🛑 {runtime_state_path} đã có d4_complete=true — cổng đã đóng, không ghi lại.",
        )

    git_info = get_git_info(repo_dir)
    ban = _thay_doi_anh_huong_phep_do(repo_dir)
    if ban:
        return (
            EXIT_GATE_AUDIT_DIRTY,
            "🛑 TỪ CHỐI đóng cổng D4 — cây làm việc có thay đổi ẢNH HƯỞNG PHÉP ĐO nhưng chưa "
            f"commit. d4_git_sha = {git_info.sha[:12]} sẽ KHÔNG khớp thứ vừa được kiểm.\n"
            + "\n".join(f"  {d}" for d in ban),
        )

    from tool_d.gates.d4_gate import kiem_tieu_chi_dong_d4

    ban_ghi, loi_doc = _doc_ban_ghi_arm(runs_dir)
    ly_do = list(loi_doc)
    ly_do += kiem_tieu_chi_dong_d4(
        ban_ghi_arm=ban_ghi,
        so_dong_b2_consumed=_dem_b2_da_tieu(registry_path),
        d4_huong="LONG",
        d4_han_che=_d4_han_che(ban_ghi),
    )
    bang_chung_he_thong, van_de_bang_chung = _bang_chung_dr_d4_04(ban_ghi, runs_dir)
    if van_de_bang_chung:
        ly_do.append(f"bằng chứng DR-D4-04 §7 chưa đạt: {van_de_bang_chung}")
    from tool_d.ablation.chi_so_export import bat_bien_1_7_lech

    b17 = _chi_so(_theo_arm(ban_ghi).get("Z3"), "bat_bien_1_7_ty_so_trung_vi")
    if bat_bien_1_7_lech(b17):
        ly_do.append(
            f"bất biến §1.7 LỆCH — trung vị D_fill/D_ke = {b17.value:.4f} (DR-D4-15) ⇒ DỪNG, mở lại DR-D4-12 §1"
        )
    if ly_do:
        return (
            EXIT_GATE_AUDIT_DIRTY,
            "🛑 TỪ CHỐI đóng cổng D4 (DR-D4-11 §3 + DR-D4-04 §7):\n" + "\n".join(f"  - {x}" for x in ly_do),
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
            f"🛑 TỪ CHỐI đóng cổng D4 — suite pytest CHƯA sạch:\n{suite_summary}\n{suite.stdout[-2000:]}",
        )

    ly_do_test, d4_bang_chung = _chay_rieng_tung_file(
        DUONG_DAN_TEST_D4, ten_cong="D4", repo_dir=repo_dir, pytest_cmd=pytest_d4_cmd
    )
    if ly_do_test:
        return EXIT_GATE_AUDIT_DIRTY, ly_do_test

    # Cùng MỘT sổ cho phép đếm B2 ở trên và cho audit — hai sổ khác nhau là hai sự thật.
    audit_exit, audit_text = run_audit(registry_path=registry_path, **run_audit_kwargs)
    if audit_exit != 0:
        return EXIT_GATE_AUDIT_DIRTY, f"🛑 TỪ CHỐI đóng cổng D4 — audit sổ trial chưa sạch:\n{audit_text}"

    # Gate §10.2 (TD-0336/0341) — GHI, không chặn: DR-D4-11 đóng cổng bằng HIỆN VẬT phán quyết; kết cục nào
    # (PASS/INCONCLUSIVE/FAIL) cũng là kết quả của D4. Hai tiêu chí bộ-test chạy THẬT ở đây.
    from tool_d.gates.d0_9 import danh_gia_gate_d09
    from tool_d.gates.d9_gate import TIEU_CHI_KHAI

    theo = _theo_arm(ban_ghi)
    z0 = theo.get("Z0") or {}
    ung_vien = theo["Z0-T1"]
    gate = danh_gia_gate_d09(
        ban_ghi_ung_vien=ung_vien,
        chi_so={k: _chi_so(ung_vien, k) for k in TIEU_CHI_KHAI},
        bo_test={
            "h4d": _chay_bo_test(DUONG_DAN_TEST_H4D, ten="D4/h4d", repo_dir=repo_dir, pytest_cmd=pytest_bo_test_cmd),
            "lz10_lz33": _chay_bo_test(
                DUONG_DAN_TEST_LZ10_LZ33, ten="D4/lz10_lz33", repo_dir=repo_dir, pytest_cmd=pytest_bo_test_cmd
            ),
        },
        ket_luan_z0t1_vs_z0t2=(
            f"Z0-T1 {ung_vien['ket_cuc']['value']} (n = {ung_vien['n_toan_cua_so']}) vs Z0 = Z0-T2 "
            f"{z0.get('ket_cuc', {}).get('value')} (n = {z0.get('n_toan_cua_so')}) — đọc từ bản ghi"
        ),
    )

    state["d4_complete"] = True
    state["d4_closed_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    state["d4_git_sha"] = git_info.sha
    state["d4_cay_sach"] = True
    state["d4_huong"] = "LONG"
    state["d4_evidence"] = {
        "full_suite": {"nguon": "do-duoc", "noi_dung": suite_summary},
        "test_khoa_d4": {"nguon": "do-duoc", "noi_dung": " | ".join(d4_bang_chung)},
        "tieu_chi_dr_d4_11": {
            "nguon": "do-duoc",
            "noi_dung": f"kiem_tieu_chi_dong_d4() PASS — {len(ban_ghi)} bản ghi arm, "
            f"{len(ban_ghi)} suất B2 CONSUMED",
        },
        **{ten: {"nguon": "do-duoc", "noi_dung": v} for ten, v in bang_chung_he_thong.items()},
        "gate_d09": {
            "nguon": "do-duoc",
            "noi_dung": (
                f"Nhánh 1 = {gate.nhanh_1.value} · trượt {list(gate.truot)} · chưa đủ {list(gate.thieu)} · "
                f"không áp dụng {list(gate.khong_ap_dung)} · {gate.buoc_tiep}"
            ),
        },
        "trial_ledger_audit": {"nguon": "do-duoc", "noi_dung": audit_text.splitlines()[0]},
    }
    state["d4_han_che"] = {"nguon": "nguoi-khai", "noi_dung": _d4_han_che(ban_ghi)}
    runtime_state_path.parent.mkdir(parents=True, exist_ok=True)
    runtime_state_path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    return (
        0,
        f"✅ Đã đóng cổng D4 — ghi {runtime_state_path}.\n{suite_summary}\n"
        + "\n".join(f"  {d}" for d in d4_bang_chung)
        + f"\n{audit_text}",
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

    if args.chon_y_tuong:
        exit_code, text = chon_don_y_tuong(Path(args.chon_y_tuong))
        print(text)
        return exit_code

    if args.huy_chon:
        exit_code, text = huy_chon_y_tuong(args.huy_chon, args.ly_do)
        print(text)
        return exit_code

    if args.nop_de_xuat:
        exit_code, text = nop_de_xuat_doi_tham_so(Path(args.nop_de_xuat))
        print(text)
        return exit_code

    if args.kiem_backlog:
        co_canh_bao, text = bao_cao_backlog()
        print(text)
        return EXIT_BACKLOG_CO_CANH_BAO if co_canh_bao else 0

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

    if args.close_d3_gate:
        exit_code, text = close_d3_gate()
        print(text)
        return exit_code

    if args.close_d3_5_gate:
        exit_code, text = close_d3_5_gate()
        print(text)
        return exit_code

    if args.close_d4_gate:
        exit_code, text = close_d4_gate()
        print(text)
        return exit_code

    exit_code, text = run_audit()
    print(text)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
