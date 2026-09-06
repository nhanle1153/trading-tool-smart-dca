"""L-Z54 — 4 dòng bảng phân loại DR-014 §5 (spec dòng 3529-3541) + trần
trả lại 3 lần cho cùng một giả thuyết.

Bảng đầy đủ có 6 dòng; 2 dòng cuối (nhiễm tham số sau khi chạy, khởi
chạy không đặt chỗ mà vẫn chạy được) đã kiểm ở TD-0051
(`TestContaminate` trong test_ledger_registry.py, qua `mark_contaminated()`)
— file này kiểm 4 dòng còn lại, ánh xạ trực tiếp vào `TrialLedger`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tool_d.ledger.budget import REFUND_CAP_PER_HYPOTHESIS, HypothesisKey
from tool_d.ledger.registry import SealedTrialError, TrialLedger, TrialState


def _prov() -> dict:
    return {
        "params_source": "yaml",
        "params_effective": {},
        "git_sha": "a" * 40,
        "reproducible_from_sha": True,
        "data_hashes": {},
        "cache_mode": "none",
        "guard_passed": True,
    }


def _reserve(ledger: TrialLedger, **overrides) -> str:
    kwargs = dict(
        n_dang_ky=114,
        budget_line="B1",
        hypothesis_slot="A-03",
        direction="LONG",
        dataset="CALIB",
        param_under_test="zss_threshold",
        param_value=0.55,
        params_frozen_hash="fh",
        config_hash="ch",
        code_commit="abc123",
        provenance=_prov(),
        contribution=1,
    )
    kwargs.update(overrides)
    return ledger.reserve(**kwargs)


class TestBonDongBangDR014:
    """4 dòng bảng §5 ánh xạ trực tiếp vào API TrialLedger."""

    def test_dong_1_guard_chan_truoc_khi_chay_thi_refunded(self, tmp_path: Path) -> None:
        ledger = TrialLedger(tmp_path / "reg.jsonl")
        tid = _reserve(ledger)
        # Guard chặn TRƯỚC khi bất kỳ lệnh chạy nào bắt đầu -> chưa từng
        # seal() (không có chỉ số nào tồn tại).
        result = ledger.refund(tid, cause_machine="GUARD_BLOCK:0d.1:HIDDEN_PARAM_FILE")
        assert result is TrialState.REFUNDED
        assert ledger.get(tid).state is TrialState.REFUNDED

    def test_dong_2_mat_mang_oom_chua_co_chi_so_thi_refunded(self, tmp_path: Path) -> None:
        ledger = TrialLedger(tmp_path / "reg.jsonl")
        tid = _reserve(ledger)
        result = ledger.refund(tid, cause_machine="OS_KILL:OOM:signal_9_before_first_metric")
        assert result is TrialState.REFUNDED
        assert ledger.get(tid).state is TrialState.REFUNDED

    def test_dong_3_nguoi_dung_tay_sau_ket_qua_mot_phan_thi_van_consumed(
        self, tmp_path: Path
    ) -> None:
        ledger = TrialLedger(tmp_path / "reg.jsonl")
        tid = _reserve(ledger)
        # "Kết quả một phần" = ĐÃ có chỉ số đầu tiên -> đã seal().
        ledger.seal(tid, seal_path=f"runs/{tid}/metrics.seal")
        # "Người dừng tay" cố gọi refund() -> PHẢI bị từ chối, không có
        # quyền phủ quyết (DR-014 §3) -> trial VẪN CONSUMED.
        with pytest.raises(SealedTrialError):
            ledger.refund(tid, cause_machine="MANUAL_STOP_ATTEMPTED")
        assert ledger.get(tid).state is TrialState.CONSUMED

    def test_dong_4_chay_xong_thay_ket_qua_thi_consumed(self, tmp_path: Path) -> None:
        ledger = TrialLedger(tmp_path / "reg.jsonl")
        tid = _reserve(ledger)
        ledger.seal(tid, seal_path=f"runs/{tid}/metrics.seal")
        ledger.consume(
            tid,
            outcome={"expectancy": 0.03, "sharpe": 1.1, "n_trades": 180, "max_single_loss_ratio": 1.0},
            verdict="KEPT",
        )
        proj = ledger.get(tid)
        assert proj.state is TrialState.CONSUMED
        assert proj.outcome_written is True
        assert proj.outcome["expectancy"] == 0.03


class TestTranTraLai3Lan:
    """DR-014 §5: trần 3 lần cho CÙNG một giả thuyết (hypothesis_slot +
    param_under_test + param_value). Lần thứ 4 -> vẫn CONSUMED."""

    def test_ba_lan_dau_hoan_tra_binh_thuong_lan_4_cuong_che_consumed(
        self, tmp_path: Path
    ) -> None:
        ledger = TrialLedger(tmp_path / "reg.jsonl")
        key = HypothesisKey("A-03", "zss_threshold", 0.55)
        assert REFUND_CAP_PER_HYPOTHESIS == 3

        trial_ids: list[str] = []
        for i in range(REFUND_CAP_PER_HYPOTHESIS):
            tid = _reserve(ledger)
            trial_ids.append(tid)
            result = ledger.refund(tid, cause_machine=f"GUARD_BLOCK:lan_{i + 1}")
            assert result is TrialState.REFUNDED, f"lần {i + 1} phải hoàn trả được"

        assert ledger.refund_count(key) == 3

        # Lần thứ 4 cho CÙNG giả thuyết -> cưỡng chế CONSUMED, KHÔNG hoàn trả.
        tid_4 = _reserve(ledger)
        result_4 = ledger.refund(tid_4, cause_machine="GUARD_BLOCK:lan_4")
        assert result_4 is TrialState.CONSUMED
        proj_4 = ledger.get(tid_4)
        assert proj_4.state is TrialState.CONSUMED
        assert proj_4.outcome["expectancy"] is None  # không có số liệu thật, chỉ cưỡng chế kế toán
        assert proj_4.outcome_written is True
        assert ledger.n_used() == 1  # CHỈ trial thứ 4 tính vào N_ĐÃ_DÙNG, 3 lần đầu vẫn REFUNDED

    def test_giai_thuyet_khac_khong_bi_anh_huong_boi_tran_cua_giai_thuyet_kia(
        self, tmp_path: Path
    ) -> None:
        ledger = TrialLedger(tmp_path / "reg.jsonl")
        for _ in range(REFUND_CAP_PER_HYPOTHESIS):
            tid = _reserve(ledger, param_under_test="zss_threshold", param_value=0.55)
            ledger.refund(tid, cause_machine="GUARD_BLOCK:x")

        # Giả thuyết KHÁC (param_value khác) chưa chạm trần -> vẫn hoàn
        # trả bình thường.
        tid_other = _reserve(ledger, param_under_test="zss_threshold", param_value=0.60)
        result = ledger.refund(tid_other, cause_machine="GUARD_BLOCK:y")
        assert result is TrialState.REFUNDED
