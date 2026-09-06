"""L-Z35 🔴 CRITICAL — spec dòng 3949-3958.

Trước TD-0041: ngưỡng DSR là placeholder +inf (gate không thể PASS bằng
cách quên điền). Sau TD-0041 (DR-D0PRE-03): ngưỡng = 0,10 R, và L-Z35
chuyển sang biến thể dòng 3954-3955 — "kết quả tốt nhất hiện có vẫn FAIL",
chạy lại mỗi lần thay ngưỡng, chống hồi quy về trạng thái "gần đạt".
"""

from __future__ import annotations

import math

import pytest

from tool_d.gates.thresholds import (
    BEST_KNOWN_DSR_ADJ_EXPECTANCY,
    DSR_ADJ_EXPECTANCY_MIN,
    GateResult,
    Verdict,
    best_known_result_for_test,
    evaluate_branch1,
)


class TestNguongDaDienBangDR:
    def test_nguong_khop_dr_d0pre_03(self) -> None:
        # Đổi số này = DR mới (viết TRƯỚC khi thấy kết quả gate kế tiếp).
        assert DSR_ADJ_EXPECTANCY_MIN == 0.10

    def test_nguong_khong_con_placeholder_va_khong_phai_gia_tri_linh_canh(self) -> None:
        assert DSR_ADJ_EXPECTANCY_MIN is not None
        assert DSR_ADJ_EXPECTANCY_MIN != 0.0
        assert math.isfinite(DSR_ADJ_EXPECTANCY_MIN)
        assert DSR_ADJ_EXPECTANCY_MIN > 0


class TestKetQuaTotNhatHienCoVanFail:
    """Spec dòng 3954-3955. Kết quả tốt nhất hiện có = CHƯA CÓ lần đánh giá
    nào → -inf (trạng thái chưa đo, N6), không phải 0.0 hay số bịa.
    """

    def test_best_known_la_chua_do_khong_phai_so_bia(self) -> None:
        assert BEST_KNOWN_DSR_ADJ_EXPECTANCY == -math.inf

    def test_best_known_van_duoi_nguong(self) -> None:
        # Khi có số đo thật, hằng số BEST_KNOWN đổi; test này phải vẫn xanh
        # cho tới khi gate THẬT SỰ qua — lúc đó đổi vai test, không xoá.
        assert BEST_KNOWN_DSR_ADJ_EXPECTANCY < DSR_ADJ_EXPECTANCY_MIN

    def test_best_known_qua_gate_van_fail_va_chi_fail_o_dsr(self) -> None:
        # Mọi tiêu chí KHÁC trong bộ số đều đạt dư dả (giả lập) — chỉ DSR
        # fail, chứng minh gate chặn đúng chỗ, không "ăn gian" bằng cách
        # fail lung tung.
        result = evaluate_branch1(best_known_result_for_test())
        assert result.verdict is Verdict.FAIL
        assert result.failed_criteria == ("dsr_adjusted_expectancy",)


class TestGateHoatDongNhuPhepKiemThat:
    def test_pass_khi_dsr_vuot_nguong_that(self) -> None:
        metrics = best_known_result_for_test()
        metrics["dsr_adjusted_expectancy"] = DSR_ADJ_EXPECTANCY_MIN + 0.01
        result = evaluate_branch1(metrics)
        assert result.verdict is Verdict.PASS
        assert result.failed_criteria == ()

    def test_bang_dung_nguong_thi_pass(self) -> None:
        # "≥" theo đúng chữ của spec dòng 4260.
        metrics = best_known_result_for_test()
        metrics["dsr_adjusted_expectancy"] = DSR_ADJ_EXPECTANCY_MIN
        assert evaluate_branch1(metrics).verdict is Verdict.PASS

    def test_fail_khi_duoi_nguong_mot_chut(self) -> None:
        metrics = best_known_result_for_test()
        metrics["dsr_adjusted_expectancy"] = DSR_ADJ_EXPECTANCY_MIN - 0.01
        assert evaluate_branch1(metrics).verdict is Verdict.FAIL

    def test_nguong_van_dung_khi_thay_doi_qua_monkeypatch(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Gate đọc hằng số module lúc gọi, không "đóng băng" ở import — nếu
        # DR mới đổi số, gate đổi theo mà không cần sửa hàm.
        import tool_d.gates.thresholds as th

        monkeypatch.setattr(th, "DSR_ADJ_EXPECTANCY_MIN", 0.5)
        metrics = best_known_result_for_test()
        metrics["dsr_adjusted_expectancy"] = 0.4
        assert th.evaluate_branch1(metrics).verdict is Verdict.FAIL


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
