"""TD-0086 — `close_d0_pre_gate()` (E6 `--close-gate`): ghi
`runtime_state.json.d0_pre_complete` từ audit THẬT, bất biến sau khi ghi.

Dùng `tmp_path` cho `runtime_state_path` + sổ trial giả lập (không đụng
`registry/runtime_state.json` thật của repo — file đó CHỈ được ghi một
lần bởi chính TD-0086 thật, không phải bởi test). `repo_dir` giữ nguyên
mặc định "." (repo thật) vì `get_git_info()` cần một repo git thật —
đọc git info không phải hành động cần cách ly.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "entrypoints"))

from trial_ledger_audit import (  # noqa: E402
    EXIT_GATE_ALREADY_CLOSED,
    EXIT_GATE_AUDIT_DIRTY,
    close_d0_pre_gate,
)


def _empty_ledger_kwargs(tmp_path: Path) -> dict:
    reg = tmp_path / "reg.jsonl"
    reg.touch()
    iq = tmp_path / "iq.jsonl"
    iq.touch()
    return {"registry_path": reg, "idea_queue_path": iq}


class TestDongCongThanhCong:
    def test_audit_sach_thi_ghi_file_va_exit_0(self, tmp_path: Path) -> None:
        state_path = tmp_path / "runtime_state.json"
        exit_code, text = close_d0_pre_gate(
            runtime_state_path=state_path, **_empty_ledger_kwargs(tmp_path)
        )
        assert exit_code == 0
        assert state_path.exists()
        data = json.loads(state_path.read_text(encoding="utf-8"))
        assert data["d0_pre_complete"] is True
        assert len(data["git_sha"]) == 40
        assert "evidence" in data and "lock_tests" in data["evidence"]

    def test_khong_bia_gia_tri_linh_canh_cho_git_sha(self, tmp_path: Path) -> None:
        state_path = tmp_path / "runtime_state.json"
        close_d0_pre_gate(runtime_state_path=state_path, **_empty_ledger_kwargs(tmp_path))
        data = json.loads(state_path.read_text(encoding="utf-8"))
        assert data["git_sha"] not in ("", "UNKNOWN", None)


class TestTuChoiGhiLai:
    def test_da_dong_roi_thi_tu_choi_khong_ghi_de(self, tmp_path: Path) -> None:
        state_path = tmp_path / "runtime_state.json"
        state_path.write_text(json.dumps({"d0_pre_complete": True, "closed_at": "x"}), encoding="utf-8")
        before = state_path.read_text(encoding="utf-8")

        exit_code, text = close_d0_pre_gate(
            runtime_state_path=state_path, **_empty_ledger_kwargs(tmp_path)
        )
        assert exit_code == EXIT_GATE_ALREADY_CLOSED
        assert state_path.read_text(encoding="utf-8") == before

    def test_file_ton_tai_nhung_chua_dong_thi_van_cho_ghi(self, tmp_path: Path) -> None:
        # File có thể tồn tại vì lý do khác (VD ghi dở, hoặc trạng thái
        # runtime khác trong tương lai) — chỉ từ chối khi ĐÚNG khoá đã True.
        state_path = tmp_path / "runtime_state.json"
        state_path.write_text(json.dumps({"some_other_key": 1}), encoding="utf-8")

        exit_code, _ = close_d0_pre_gate(runtime_state_path=state_path, **_empty_ledger_kwargs(tmp_path))
        assert exit_code == 0
        data = json.loads(state_path.read_text(encoding="utf-8"))
        assert data["d0_pre_complete"] is True


class TestTuChoiTrenAuditBan:
    def test_audit_fail_thi_khong_ghi_file(self, tmp_path: Path) -> None:
        # Sổ bẩn: registered SAU executed (L-Z10 fail) — tái dùng chính
        # fixture đã canh L-Z10 ở test_trial_ledger_audit_entrypoint.py,
        # viết gọn trực tiếp ở đây để không phụ thuộc file test khác.
        prov = {
            "params_source": "yaml", "params_effective": {}, "git_sha": "a" * 40,
            "reproducible_from_sha": True, "data_hashes": {}, "cache_mode": "none",
            "guard_passed": True,
        }
        reg = tmp_path / "reg.jsonl"
        reg.write_text(
            json.dumps({
                "event": "RESERVE", "trial_id": "D-0001",
                "registered_at": "2026-09-06T12:00:00Z", "budget_line": "B1",
                "hypothesis_slot": "A", "direction": "LONG", "dataset": "CALIB",
                "param_under_test": "x", "param_value": 1, "params_frozen_hash": "f",
                "config_hash": "c", "code_commit": "a", "provenance": prov,
                "contribution": 1, "tool_id": "D",
            }, ensure_ascii=False) + "\n"
            + json.dumps({
                "event": "CONSUME", "trial_id": "D-0001",
                "executed_at": "2026-09-06T10:00:00Z",  # TRƯỚC registered_at -> L-Z10 fail
                "outcome": {"expectancy": None, "sharpe": None, "n_trades": None, "max_single_loss_ratio": None},
                "verdict": "INCONCLUSIVE", "rejection_reason": "test", "retest_forbidden": False,
            }) + "\n",
            encoding="utf-8",
        )
        iq = tmp_path / "iq.jsonl"
        iq.touch()
        state_path = tmp_path / "runtime_state.json"

        exit_code, text = close_d0_pre_gate(
            runtime_state_path=state_path, registry_path=reg, idea_queue_path=iq
        )
        assert exit_code == EXIT_GATE_AUDIT_DIRTY
        assert not state_path.exists()
