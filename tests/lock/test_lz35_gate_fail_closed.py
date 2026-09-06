"""L-Z35 🔴 CRITICAL — Placeholder fail-closed: mọi ngưỡng GATE chưa điền
= +inf (KHÔNG PHẢI None, KHÔNG PHẢI 0.0). Gate không thể vô tình PASS.
Spec dòng 3949-3958, 4260.
"""

from __future__ import annotations

import math

import pytest

from tool_d.gates.thresholds import (
    DSR_ADJ_EXPECTANCY_MIN,
    GateResult,
    Verdict,
    best_known_result_for_test,
    evaluate_branch1,
)


class TestPlaceholderLaInfKhongPhaiNoneHay0:
    def test_dsr_threshold_hien_tai_la_inf(self) -> None:
        assert DSR_ADJ_EXPECTANCY_MIN == math.inf
        assert DSR_ADJ_EXPECTANCY_MIN is not None
        assert DSR_ADJ_EXPECTANCY_MIN != 0.0


class TestKetQuaCucTotVanPhaiFail:
    """Spec dòng 3952-3953: "Gate này KHÔNG THỂ pass bằng cách quên điền"."""

    def test_ket_qua_cuc_tot_gia_lap_van_fail(self) -> None:
        result = evaluate_branch1(best_known_result_for_test())
        assert result.verdict is Verdict.FAIL
        assert "dsr_adjusted_expectancy" in result.failed_criteria

    def test_chi_that_bai_o_dsr_khong_phai_tieu_chi_khac(self) -> None:
        # Mọi tiêu chí KHÁC trong bộ số giả lập đều đạt dư dả — chỉ DSR
        # fail, chứng minh gate không "ăn gian" bằng cách fail lung tung.
        result = evaluate_branch1(best_known_result_for_test())
        assert result.failed_criteria == ("dsr_adjusted_expectancy",)


class TestEvaluateBranch1HoatDongDungKhiNguongDuocDien:
    """Mô phỏng SAU KHI OQ-01 được điền (TD-0041) — gate phải hoạt động
    như một phép kiểm thật, không phải luôn luôn FAIL vĩnh viễn.
    """

    def test_pass_khi_tat_ca_tieu_chi_dat_va_nguong_da_dien(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "tool_d.gates.thresholds.DSR_ADJ_EXPECTANCY_MIN", 0.5
        )
        import tool_d.gates.thresholds as th

        metrics = best_known_result_for_test()
        metrics["dsr_adjusted_expectancy"] = 0.6  # vượt ngưỡng giả lập 0.5
        result = th.evaluate_branch1(metrics)
        assert result.verdict is Verdict.PASS
        assert result.failed_criteria == ()

    def test_fail_khi_duoi_nguong_da_dien(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import tool_d.gates.thresholds as th

        monkeypatch.setattr(th, "DSR_ADJ_EXPECTANCY_MIN", 0.5)
        metrics = best_known_result_for_test()
        metrics["dsr_adjusted_expectancy"] = 0.4  # dưới ngưỡng giả lập
        result = th.evaluate_branch1(metrics)
        assert result.verdict is Verdict.FAIL


class TestThieuDuLieuLaFailKhongPhaiPassNgam:
    def test_metrics_rong_thi_fail_tat_ca(self) -> None:
        result = evaluate_branch1({})
        assert result.verdict is Verdict.FAIL
        assert len(result.failed_criteria) == 7  # đủ 7 tiêu chí số của Nhánh 1


class TestGateResultRender:
    def test_pass_render(self) -> None:
        assert GateResult(verdict=Verdict.PASS).render() == "PASS"

    def test_fail_render_liet_ke_tieu_chi(self) -> None:
        r = GateResult(verdict=Verdict.FAIL, failed_criteria=("dsr_adjusted_expectancy",))
        assert "FAIL" in r.render()
        assert "dsr_adjusted_expectancy" in r.render()
