"""TD-0056 — entrypoints/trial_ledger_audit.py (E6): sổ rỗng exit 0, sổ
bẩn exit≠0, đúng định dạng "đã audit N/M (...)".
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "entrypoints"))

from trial_ledger_audit import EXIT_AUDIT_FAILED, run_audit  # noqa: E402


def _prov() -> dict:
    return {
        "params_source": "yaml", "params_effective": {}, "git_sha": "a" * 40,
        "reproducible_from_sha": True, "data_hashes": {}, "cache_mode": "none",
        "guard_passed": True,
    }


class TestSoRong:
    def test_so_rong_exit_0_dung_dinh_dang(self, tmp_path: Path) -> None:
        reg = tmp_path / "reg.jsonl"
        reg.touch()
        iq = tmp_path / "iq.jsonl"
        iq.touch()
        exit_code, text = run_audit(registry_path=reg, idea_queue_path=iq)
        assert exit_code == 0
        assert text.startswith("đã audit ")
        assert "chưa đo được" in text


class TestSoBan:
    def test_registered_muon_hon_executed_thi_exit_khac_0(self, tmp_path: Path) -> None:
        reg = tmp_path / "reg.jsonl"
        reg.write_text(
            json.dumps({
                "event": "RESERVE", "trial_id": "D-0001",
                "registered_at": "2026-09-06T10:00:00Z", "budget_line": "B1",
                "hypothesis_slot": "A", "direction": "LONG", "dataset": "CALIB",
                "param_under_test": "x", "param_value": 1, "params_frozen_hash": "f",
                "config_hash": "c", "code_commit": "a", "provenance": _prov(),
                "contribution": 1, "tool_id": "D",
            }, ensure_ascii=False) + "\n"
            + json.dumps({
                "event": "CONSUME", "trial_id": "D-0001",
                "executed_at": "2026-09-06T09:00:00Z",  # TRƯỚC registered_at -> vi phạm L-Z10
                "outcome": {"expectancy": None, "sharpe": None, "n_trades": None, "max_single_loss_ratio": None},
                "verdict": "INCONCLUSIVE", "rejection_reason": None, "retest_forbidden": True,
            }, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        iq = tmp_path / "iq.jsonl"
        iq.touch()
        exit_code, text = run_audit(registry_path=reg, idea_queue_path=iq)
        assert exit_code == EXIT_AUDIT_FAILED
        assert exit_code != 0
        assert "CHƯA ĐẠT" in text
        assert "L-Z10" in text
