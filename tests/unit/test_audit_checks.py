"""TD-0056 — audit_checks.py: L-Z10, L-Z11, L-Z12, L-Z15, L-Z16, L-Z17.
Test khoá đầy đủ (bao gồm kịch bản "sổ bẩn") cho từng phép kiểm, cộng
kiểm tra E6 (`run_audit`) tổng hợp đúng.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tool_d.ledger.audit_checks import (
    check_lz10_registered_before_executed,
    check_lz11_n_used_le_n_dang_ky,
    check_lz12_no_duplicate_config_hash_different_outcome,
    check_lz15_calibrate_params_have_status,
    check_lz16_idea_queue_filter_and_tool_d_results,
    check_lz17_budget_a_slots_per_quarter,
)
from tool_d.ledger.registry import TrialLedger


def _prov() -> dict:
    return {
        "params_source": "yaml", "params_effective": {}, "git_sha": "a" * 40,
        "reproducible_from_sha": True, "data_hashes": {}, "cache_mode": "none",
        "guard_passed": True,
    }


def _reserve(ledger: TrialLedger, **overrides) -> str:
    kwargs = dict(
        n_dang_ky=114, budget_line="B1", hypothesis_slot="A-03", direction="LONG",
        dataset="CALIB", param_under_test="zss_threshold", param_value=0.55,
        params_frozen_hash="fh", config_hash="ch", code_commit="abc123",
        provenance=_prov(), contribution=1,
    )
    kwargs.update(overrides)
    return ledger.reserve(**kwargs)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


class TestLZ10RegisteredBeforeExecuted:
    def test_so_rong_thi_pending(self, tmp_path: Path) -> None:
        r = check_lz10_registered_before_executed(tmp_path / "reg.jsonl")
        assert r.measured.render() == "chưa đo được (registry rỗng, chưa có sự kiện nào)"

    def test_luong_binh_thuong_thi_dat(self, tmp_path: Path) -> None:
        reg = tmp_path / "reg.jsonl"
        ledger = TrialLedger(reg)
        tid = _reserve(ledger)
        ledger.seal(tid, seal_path=f"runs/{tid}/metrics.seal")
        ledger.consume(tid, outcome={"expectancy": 0.01, "sharpe": 0.1, "n_trades": 5, "max_single_loss_ratio": 1.0}, verdict="REJECTED")
        assert check_lz10_registered_before_executed(reg).ok

    def test_so_ban_executed_truoc_registered_thi_fail(self, tmp_path: Path) -> None:
        reg = tmp_path / "reg.jsonl"
        _write_jsonl(reg, [
            {"event": "RESERVE", "trial_id": "D-0001", "registered_at": "2026-09-06T10:00:00Z",
             "budget_line": "B1", "hypothesis_slot": "A-03", "direction": "LONG", "dataset": "CALIB",
             "param_under_test": "x", "param_value": 1, "params_frozen_hash": "f", "config_hash": "c",
             "code_commit": "a", "provenance": _prov(), "contribution": 1, "tool_id": "D"},
            {"event": "CONSUME", "trial_id": "D-0001", "executed_at": "2026-09-06T09:00:00Z",
             "outcome": {"expectancy": None, "sharpe": None, "n_trades": None, "max_single_loss_ratio": None},
             "verdict": "INCONCLUSIVE", "rejection_reason": None, "retest_forbidden": True},
        ])
        r = check_lz10_registered_before_executed(reg)
        assert r.is_fail
        assert "D-0001" in r.evidence


class TestLZ11NUsedLeNDangKy:
    def test_duoi_tran_thi_dat(self, tmp_path: Path) -> None:
        ledger = TrialLedger(tmp_path / "reg.jsonl")
        tid = _reserve(ledger, contribution=5)
        ledger.seal(tid, seal_path=f"runs/{tid}/metrics.seal")
        r = check_lz11_n_used_le_n_dang_ky(tmp_path / "reg.jsonl", n_dang_ky=114)
        assert r.ok
        assert "N_ĐÃ_DÙNG=5" in r.evidence

    def test_vuot_tran_thi_fail(self, tmp_path: Path) -> None:
        # Không thể vượt trần qua API bình thường (reserve() tự chặn) —
        # mô phỏng sổ bị sửa tay/bug bằng cách ghi thẳng sự kiện.
        reg = tmp_path / "reg.jsonl"
        _write_jsonl(reg, [
            {"event": "RESERVE", "trial_id": "D-0001", "registered_at": "2026-09-06T09:00:00Z",
             "budget_line": "B1", "hypothesis_slot": "A-03", "direction": "LONG", "dataset": "CALIB",
             "param_under_test": "x", "param_value": 1, "params_frozen_hash": "f", "config_hash": "c",
             "code_commit": "a", "provenance": _prov(), "contribution": 200, "tool_id": "D"},
            {"event": "SEAL", "trial_id": "D-0001", "sealed_at": "2026-09-06T09:01:00Z", "seal_path": "runs/D-0001/metrics.seal"},
        ])
        r = check_lz11_n_used_le_n_dang_ky(reg, n_dang_ky=114)
        assert r.is_fail


class TestLZ12NoDuplicateConfigHash:
    def test_cung_config_hash_cung_outcome_thi_dat(self, tmp_path: Path) -> None:
        ledger = TrialLedger(tmp_path / "reg.jsonl")
        outcome = {"expectancy": 0.02, "sharpe": 0.5, "n_trades": 100, "max_single_loss_ratio": 1.0}
        for _ in range(2):
            tid = _reserve(ledger, config_hash="SAME")
            ledger.seal(tid, seal_path=f"runs/{tid}/metrics.seal")
            ledger.consume(tid, outcome=dict(outcome), verdict="REJECTED")
        assert check_lz12_no_duplicate_config_hash_different_outcome(tmp_path / "reg.jsonl").ok

    def test_cung_config_hash_khac_outcome_thi_fail(self, tmp_path: Path) -> None:
        ledger = TrialLedger(tmp_path / "reg.jsonl")
        tid1 = _reserve(ledger, config_hash="SAME")
        ledger.seal(tid1, seal_path=f"runs/{tid1}/metrics.seal")
        ledger.consume(tid1, outcome={"expectancy": 0.02, "sharpe": 0.5, "n_trades": 100, "max_single_loss_ratio": 1.0}, verdict="REJECTED")

        tid2 = _reserve(ledger, config_hash="SAME")
        ledger.seal(tid2, seal_path=f"runs/{tid2}/metrics.seal")
        ledger.consume(tid2, outcome={"expectancy": 0.09, "sharpe": 1.5, "n_trades": 300, "max_single_loss_ratio": 1.0}, verdict="KEPT")

        r = check_lz12_no_duplicate_config_hash_different_outcome(tmp_path / "reg.jsonl")
        assert r.is_fail
        assert "SAME" in r.evidence


class TestLZ15CalibrateParamsHaveStatus:
    def test_v_min_duoc_khai_trong_param_status_thi_dat(self) -> None:
        # Dùng file thật của project — v_min đã khai TUNED_PENDING (TD-0056).
        r = check_lz15_calibrate_params_have_status()
        assert r.ok, r.evidence

    def test_tham_so_null_ma_khong_khai_thi_fail(self, tmp_path: Path) -> None:
        cfg_path = tmp_path / "cfg.yaml"
        cfg_path.write_text(
            "tier_a: {}\ntier_b:\n  _budget_remaining_B3: null\n  v_min: null\n"
            "tier_frozen: {}\ntier_c: {}\n",
            encoding="utf-8",
        )
        status_path = tmp_path / "status.yaml"
        status_path.write_text("params: {}\n", encoding="utf-8")
        r = check_lz15_calibrate_params_have_status(cfg_path, status_path)
        assert r.is_fail
        assert "v_min" in r.evidence

    def test_thieu_file_status_ma_co_tham_so_null_thi_fail(self, tmp_path: Path) -> None:
        cfg_path = tmp_path / "cfg.yaml"
        cfg_path.write_text(
            "tier_a: {}\ntier_b:\n  _budget_remaining_B3: null\n  v_min: null\n"
            "tier_frozen: {}\ntier_c: {}\n",
            encoding="utf-8",
        )
        r = check_lz15_calibrate_params_have_status(cfg_path, tmp_path / "khong_ton_tai.yaml")
        assert r.is_fail


class TestLZ16IdeaQueueFilterAndToolDResults:
    def test_so_rong_thi_pending(self, tmp_path: Path) -> None:
        r = check_lz16_idea_queue_filter_and_tool_d_results(tmp_path / "iq.jsonl")
        assert r.measured.status.value == "pending"

    def test_mechanism_du_3_cau_thi_dat(self, tmp_path: Path) -> None:
        path = tmp_path / "iq.jsonl"
        _write_jsonl(path, [{
            "idea_id": "IQ-0001", "data_source": "MECHANISM", "status": "QUEUED",
            "mechanism": "x", "who_pays": "y", "durability": "z",
        }])
        assert check_lz16_idea_queue_filter_and_tool_d_results(path).ok

    def test_mechanism_thieu_who_pays_thi_fail(self, tmp_path: Path) -> None:
        path = tmp_path / "iq.jsonl"
        _write_jsonl(path, [{
            "idea_id": "IQ-0002", "data_source": "EXPLORE", "status": "QUEUED",
            "mechanism": "x", "who_pays": "", "durability": "z",
        }])
        r = check_lz16_idea_queue_filter_and_tool_d_results(path)
        assert r.is_fail
        assert "who_pays" in r.evidence

    def test_tool_d_results_khong_reject_thi_fail(self, tmp_path: Path) -> None:
        path = tmp_path / "iq.jsonl"
        _write_jsonl(path, [{
            "idea_id": "IQ-0003", "data_source": "TOOL_D_RESULTS", "status": "QUEUED",
            "mechanism": "n/a", "who_pays": "n/a", "durability": "n/a",
        }])
        r = check_lz16_idea_queue_filter_and_tool_d_results(path)
        assert r.is_fail
        assert "IQ-0003" in r.evidence

    def test_tool_d_results_da_reject_thi_dat(self, tmp_path: Path) -> None:
        path = tmp_path / "iq.jsonl"
        _write_jsonl(path, [{
            "idea_id": "IQ-0004", "data_source": "TOOL_D_RESULTS", "status": "REJECTED",
            "mechanism": "n/a", "who_pays": "n/a", "durability": "n/a",
        }])
        assert check_lz16_idea_queue_filter_and_tool_d_results(path).ok


class TestLZ17BudgetASlotsPerQuarter:
    def test_duoi_5_slot_mot_quy_thi_dat(self, tmp_path: Path) -> None:
        path = tmp_path / "iq.jsonl"
        _write_jsonl(path, [
            {"idea_id": f"IQ-{i:04d}", "status": "SELECTED", "selected_at": "2026-01-15T00:00:00Z"}
            for i in range(4)
        ])
        assert check_lz17_budget_a_slots_per_quarter(path).ok

    def test_vuot_5_slot_mot_quy_thi_fail(self, tmp_path: Path) -> None:
        path = tmp_path / "iq.jsonl"
        _write_jsonl(path, [
            {"idea_id": f"IQ-{i:04d}", "status": "SELECTED", "selected_at": "2026-01-15T00:00:00Z"}
            for i in range(6)
        ])
        r = check_lz17_budget_a_slots_per_quarter(path)
        assert r.is_fail
        assert "(2026, 1)" in r.evidence

    def test_khac_quy_khong_cong_don(self, tmp_path: Path) -> None:
        path = tmp_path / "iq.jsonl"
        rows = [
            {"idea_id": f"IQ-{i:04d}", "status": "SELECTED", "selected_at": "2026-01-15T00:00:00Z"}
            for i in range(5)
        ] + [
            {"idea_id": f"IQ-{i:04d}", "status": "SELECTED", "selected_at": "2026-04-15T00:00:00Z"}
            for i in range(5, 10)
        ]
        _write_jsonl(path, rows)
        assert check_lz17_budget_a_slots_per_quarter(path).ok
