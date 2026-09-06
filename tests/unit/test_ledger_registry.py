"""TD-0051 — TrialLedger: reserve/seal/consume/refund, Khả dụng, bản chiếu.

Test khoá cứng riêng (L-Z52→L-Z55) nằm ở TD-0052→0055. File này kiểm cơ
chế nền: chuỗi reserve→seal→consume đúng available() ở từng bước, cùng
các bất biến DR-014 §5/§6.

Mọi test dùng `tmp_path` — KHÔNG BAO GIỜ chạm registry/trial_registry.jsonl
thật của project.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tool_d.ledger.budget import HypothesisKey
from tool_d.ledger.registry import (
    AlreadyFinalizedError,
    BudgetExhaustedError,
    LedgerError,
    SealedTrialError,
    TrialLedger,
    TrialState,
    UnknownTrialError,
)


def _prov() -> dict:
    return {
        "params_source": "yaml",
        "params_effective": {"zss_threshold": 0.55},
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


class TestChuoiReserveSealConsume:
    def test_available_dung_o_tung_buoc(self, tmp_path: Path) -> None:
        ledger = TrialLedger(tmp_path / "reg.jsonl")
        assert ledger.available(n_dang_ky=114) == 114

        tid = _reserve(ledger)
        assert ledger.available(n_dang_ky=114) == 113  # RESERVED chiếm chỗ ngay

        ledger.seal(tid, seal_path=f"runs/{tid}/metrics.seal")
        assert ledger.available(n_dang_ky=114) == 113  # seal không đổi kế toán

        ledger.consume(
            tid,
            outcome={"expectancy": 0.02, "sharpe": 0.9, "n_trades": 200, "max_single_loss_ratio": 1.0},
            verdict="REJECTED",
        )
        assert ledger.available(n_dang_ky=114) == 113  # đã CONSUMED, không quay lại pool
        assert ledger.n_used() == 1
        assert ledger.n_reserved() == 0

    def test_trial_da_tieu_khong_bao_gio_quay_lai_pool(self, tmp_path: Path) -> None:
        ledger = TrialLedger(tmp_path / "reg.jsonl")
        tid = _reserve(ledger, contribution=5)
        ledger.consume(tid, outcome={"expectancy": None, "sharpe": None, "n_trades": None, "max_single_loss_ratio": None}, verdict="INCONCLUSIVE")
        before = ledger.available(n_dang_ky=114)
        # Gọi lại available() nhiều lần không tự "hồi phục".
        assert ledger.available(n_dang_ky=114) == before == 109

    def test_ban_chieu_dung_sau_nhieu_trial(self, tmp_path: Path) -> None:
        ledger = TrialLedger(tmp_path / "reg.jsonl")
        t1 = _reserve(ledger, contribution=1)
        t2 = _reserve(ledger, contribution=2, param_under_test="buf_sl_atr", param_value=0.4)
        ledger.consume(t1, outcome={"expectancy": 0.01, "sharpe": 0.1, "n_trades": 10, "max_single_loss_ratio": 1.0}, verdict="REJECTED")
        # t2 vẫn RESERVED
        proj = ledger.projections()
        assert proj[t1].state is TrialState.CONSUMED
        assert proj[t2].state is TrialState.RESERVED
        assert ledger.n_used() == 1
        assert ledger.n_reserved() == 2
        assert ledger.available(n_dang_ky=114) == 114 - 1 - 2


class TestBudgetExhausted:
    def test_khong_du_kha_dung_thi_raise_truoc_khi_chay(self, tmp_path: Path) -> None:
        ledger = TrialLedger(tmp_path / "reg.jsonl")
        with pytest.raises(BudgetExhaustedError):
            _reserve(ledger, n_dang_ky=114, contribution=115)

    def test_reserve_dung_het_roi_reserve_them_1_thi_raise(self, tmp_path: Path) -> None:
        ledger = TrialLedger(tmp_path / "reg.jsonl")
        _reserve(ledger, n_dang_ky=2, contribution=2)
        with pytest.raises(BudgetExhaustedError):
            _reserve(ledger, n_dang_ky=2, contribution=1)

    def test_contribution_duoi_1_thi_raise(self, tmp_path: Path) -> None:
        ledger = TrialLedger(tmp_path / "reg.jsonl")
        with pytest.raises(LedgerError):
            _reserve(ledger, contribution=0)


class TestSealVaRefund:
    def test_da_seal_thi_refund_raise_sealed_error(self, tmp_path: Path) -> None:
        ledger = TrialLedger(tmp_path / "reg.jsonl")
        tid = _reserve(ledger)
        ledger.seal(tid, seal_path=f"runs/{tid}/metrics.seal")
        with pytest.raises(SealedTrialError):
            ledger.refund(tid, cause_machine="EXIT_CODE:1")

    def test_seal_hai_lan_thi_raise(self, tmp_path: Path) -> None:
        ledger = TrialLedger(tmp_path / "reg.jsonl")
        tid = _reserve(ledger)
        ledger.seal(tid, seal_path=f"runs/{tid}/metrics.seal")
        with pytest.raises(AlreadyFinalizedError):
            ledger.seal(tid, seal_path=f"runs/{tid}/metrics.seal")

    def test_refund_chua_seal_thi_ok_va_tra_ve_refunded(self, tmp_path: Path) -> None:
        ledger = TrialLedger(tmp_path / "reg.jsonl")
        tid = _reserve(ledger)
        result = ledger.refund(tid, cause_machine="GUARD_BLOCK:HIDDEN_PARAM_FILE")
        assert result is TrialState.REFUNDED
        assert ledger.get(tid).state is TrialState.REFUNDED
        assert ledger.available(n_dang_ky=114) == 114  # hoàn trả, KHÔNG mất chỗ


class TestOutcomeChiGhiMotLan:
    def test_consume_hai_lan_thi_raise(self, tmp_path: Path) -> None:
        ledger = TrialLedger(tmp_path / "reg.jsonl")
        tid = _reserve(ledger)
        ledger.consume(tid, outcome={"expectancy": 0.01, "sharpe": 0.1, "n_trades": 5, "max_single_loss_ratio": 1.0}, verdict="REJECTED")
        with pytest.raises(AlreadyFinalizedError):
            ledger.consume(tid, outcome={"expectancy": 0.02, "sharpe": 0.2, "n_trades": 6, "max_single_loss_ratio": 1.0}, verdict="KEPT")


class TestUnknownTrial:
    def test_thao_tac_tren_trial_chua_reserve_thi_raise(self, tmp_path: Path) -> None:
        ledger = TrialLedger(tmp_path / "reg.jsonl")
        with pytest.raises(UnknownTrialError):
            ledger.get("D-9999")
        with pytest.raises(UnknownTrialError):
            ledger.seal("D-9999", seal_path="runs/D-9999/metrics.seal")


class TestContaminate:
    def test_danh_dau_nhiem_tren_trial_da_consumed(self, tmp_path: Path) -> None:
        ledger = TrialLedger(tmp_path / "reg.jsonl")
        tid = _reserve(ledger)
        ledger.consume(tid, outcome={"expectancy": 0.01, "sharpe": 0.1, "n_trades": 5, "max_single_loss_ratio": 1.0}, verdict="REJECTED")
        ledger.mark_contaminated(tid, reason="config_hash trùng D-0099 với outcome khác nhau")
        # Trạng thái VẪN CONSUMED — không đổi, không hoàn trả (spec dòng 3557).
        assert ledger.get(tid).state is TrialState.CONSUMED

    def test_khong_the_danh_dau_nhiem_tren_trial_chua_consumed(self, tmp_path: Path) -> None:
        ledger = TrialLedger(tmp_path / "reg.jsonl")
        tid = _reserve(ledger)
        with pytest.raises(LedgerError):
            ledger.mark_contaminated(tid, reason="x")


class TestHypothesisKey:
    def test_matches_dung(self) -> None:
        key = HypothesisKey("A-03", "zss_threshold", 0.55)
        assert key.matches(hypothesis_slot="A-03", param_under_test="zss_threshold", param_value=0.55)
        assert not key.matches(hypothesis_slot="A-03", param_under_test="zss_threshold", param_value=0.60)
        assert not key.matches(hypothesis_slot="A-04", param_under_test="zss_threshold", param_value=0.55)


class TestSealTuTinhLaConsumed:
    """DR-014 §1: "CÓ con dấu ⇒ CONSUMED" — một quy tắc ĐỊNH NGHĨA, không
    phụ thuộc việc sự kiện CONSUME (mang outcome thật) đã ghi hay chưa.
    Đây là bất biến L-Z53 dựa vào (TD-0053) — kiểm riêng ở đây vì nó
    thuộc cơ chế nền của TrialLedger, không riêng kịch bản giết tiến trình.
    """

    def test_da_seal_nhung_chua_ghi_outcome_van_tinh_la_consumed(self, tmp_path: Path) -> None:
        ledger = TrialLedger(tmp_path / "reg.jsonl")
        tid = _reserve(ledger)
        ledger.seal(tid, seal_path=f"runs/{tid}/metrics.seal")
        # CHƯA gọi consume() — vẫn phải tính là CONSUMED cho mục đích
        # kế toán (n_used), vì "có con dấu" đã đủ theo DR-014 §1.
        assert ledger.get(tid).state is TrialState.CONSUMED
        assert ledger.n_used() == 1
        assert ledger.n_reserved() == 0

    def test_sau_do_van_ghi_outcome_that_duoc_binh_thuong(self, tmp_path: Path) -> None:
        # Luồng bình thường: seal() rồi consume() vẫn phải chạy được —
        # sửa lỗi thiết kế không được làm hỏng luồng đã có (TD-0051).
        ledger = TrialLedger(tmp_path / "reg.jsonl")
        tid = _reserve(ledger)
        ledger.seal(tid, seal_path=f"runs/{tid}/metrics.seal")
        ledger.consume(
            tid,
            outcome={"expectancy": 0.02, "sharpe": 0.9, "n_trades": 200, "max_single_loss_ratio": 1.0},
            verdict="REJECTED",
        )
        assert ledger.get(tid).outcome_written is True
        assert ledger.get(tid).state is TrialState.CONSUMED
        assert ledger.n_used() == 1  # không đếm hai lần dù sealed lẫn outcome_written đều True
