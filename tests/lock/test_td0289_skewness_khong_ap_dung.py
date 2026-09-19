"""TD-0289 (`DR-D9-02` §4, phương án b′) — tiêu chí skewness-so-`Z1` KHÔNG áp dụng cho arm entry đơn.

`MT-53`: `Z1` bị cắt khỏi lô (`DR-D4-12` §4) ⇒ tiêu chí *"skewness(cấu hình tốt nhất) không âm hơn skewness(Z1) quá
0,5"* không đo được ⇒ Nhánh 1 không bao giờ PASS trọn. `DR-D9-02` chốt: với arm thuộc `ARM_DON_TRANCHE` tiêu chí KHÔNG
áp dụng (liệt kê tường minh, không xoá khoá); với arm DCA áp dụng và chặn như cũ.

Ba trạng thái phải phân biệt được — "không áp dụng có căn cứ" KHÁC "chưa đo" và KHÁC "đạt" (`DR-D9-02` §3.3).
"""

from __future__ import annotations

import pytest

from tool_d.arm_switches import ARM_DON_TRANCHE, ARM_HOP_LE
from tool_d.gates.cscv import KetQuaPBO
from tool_d.gates.d9_gate import TIEU_CHI_KHAI, danh_gia_cong_d9
from tool_d.gates.dsr import N_DANG_KY
from tool_d.gates.ket_cuc import KetCuc
from tool_d.gates.thresholds import TIEU_CHI_SKEWNESS_Z1, Verdict, evaluate_branch1
from tool_d.measurement.tri_state import Measured

DAT = {
    "dsr_adjusted_expectancy": 1.0,
    "liq_buffer_ratio_mean": 20.0,
    "max_single_trade_loss_over_risk_budget": 1.0,
    "trades_per_year": 300.0,
    "tp_fallback_ratio": 0.1,
    "time_stop_ratio": 0.1,
}  # KHÔNG có khoá skewness


class TestEvaluateBranch1:
    @pytest.mark.parametrize("arm", sorted(ARM_DON_TRANCHE))
    def test_entry_don_thieu_skewness_van_PASS_va_liet_ke_khong_ap_dung(self, arm) -> None:
        r = evaluate_branch1(DAT, pbo_chan=False, arm=arm)
        assert r.verdict is Verdict.PASS
        assert r.khong_ap_dung == (TIEU_CHI_SKEWNESS_Z1,)
        assert "DR-D9-02" in r.render()

    @pytest.mark.parametrize("arm", sorted(set(ARM_HOP_LE) - ARM_DON_TRANCHE))
    def test_arm_DCA_thieu_skewness_thi_CHAN(self, arm) -> None:
        r = evaluate_branch1(DAT, pbo_chan=False, arm=arm)
        assert r.verdict is Verdict.FAIL
        assert r.failed_criteria == (TIEU_CHI_SKEWNESS_Z1,)
        assert r.khong_ap_dung == ()

    def test_entry_don_bo_rong_la_sau_loi_cong_mot_khong_ap_dung(self) -> None:
        r = evaluate_branch1({}, pbo_chan=False, arm="Z0-T1")
        assert len(r.failed_criteria) == 6 and TIEU_CHI_SKEWNESS_Z1 not in r.failed_criteria
        assert r.khong_ap_dung == (TIEU_CHI_SKEWNESS_Z1,)

    @pytest.mark.parametrize("arm", ["Z0-T2", "", "z0"])
    def test_arm_la_thi_raise(self, arm) -> None:
        with pytest.raises(ValueError, match="DR-D9-02"):
            evaluate_branch1(DAT, pbo_chan=False, arm=arm)

    def test_arm_khong_co_mac_dinh(self) -> None:
        with pytest.raises(TypeError):
            evaluate_branch1(DAT, pbo_chan=False)  # type: ignore[call-arg]


_PBO = KetQuaPBO(
    pbo=Measured.ok(0.2), so_cau_hinh_dau_vao=4, so_cau_hinh_phan_biet=4, cau_hinh_gop_trung=(),
    so_to_hop=70, so_to_hop_doc_duoc=70, to_hop=(),
)


def _chi_so(skew: Measured[float]) -> dict:
    cs = {k: Measured.ok(v) for k, v in DAT.items() if k in TIEU_CHI_KHAI}
    cs[TIEU_CHI_SKEWNESS_Z1] = skew
    return cs


def _d9(arm: str, skew: Measured[float]):
    return danh_gia_cong_d9(
        r_trien_khai_test=[1.0 + (0.1 if i % 2 else -0.1) for i in range(200)],
        n_trials=N_DANG_KY,
        chi_so=_chi_so(skew),
        ket_qua_pbo=_PBO,
        arm=arm,
    )


class TestCongD9:
    def test_entry_don_skewness_pending_KHONG_chan(self) -> None:
        kq = _d9("Z0-T1", Measured.pending("Z1 bị cắt"))
        assert kq.ket_cuc is KetCuc.PASS
        assert TIEU_CHI_SKEWNESS_Z1 not in kq.chua_do
        assert kq.khong_ap_dung == (TIEU_CHI_SKEWNESS_Z1,)

    def test_DCA_skewness_pending_la_CHUA_DO(self) -> None:
        kq = _d9("Z3", Measured.pending("Z1 bị cắt"))
        assert kq.ket_cuc is KetCuc.INCONCLUSIVE
        assert TIEU_CHI_SKEWNESS_Z1 in kq.chua_do and kq.khong_ap_dung == ()

    def test_DCA_skewness_do_duoc_ma_truot_la_FAIL(self) -> None:
        kq = _d9("Z3", Measured.ok(0.9))
        assert kq.ket_cuc is KetCuc.FAIL and TIEU_CHI_SKEWNESS_Z1 in kq.khong_dat

    def test_arm_khong_co_mac_dinh(self) -> None:
        with pytest.raises(TypeError):
            danh_gia_cong_d9(  # type: ignore[call-arg]
                r_trien_khai_test=[1.0, 2.0], n_trials=N_DANG_KY, chi_so=_chi_so(Measured.ok(0.0)),
                ket_qua_pbo=_PBO,
            )
