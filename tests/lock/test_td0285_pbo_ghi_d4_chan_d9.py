"""🔒 TD-0285 — cổng D9: PBO CHẶN (P0), ba kết cục, `N` không ghim (`DR-D9-01` §6.2, §7).

Phần "D4 chỉ ghi PBO" khoá ở `test_lz35_gate_fail_closed.py` (cùng hàm
`evaluate_branch1`, ca `pbo_chan=False`). File này khoá `danh_gia_cong_d9()`.

Số liệu dựng để tính tay được:
- `_on_dinh(m)` = 100 lệnh `m ± 0,1` xen kẽ ⇒ std ≈ 0,1005, thuế nhiễu ở N=114 ≈ 0,031.
- `_nhieu(m)`   = 400 lệnh `m ± 1` xen kẽ ⇒ std ≈ 1,00125, thuế ≈ 0,154 (N=114).
"""

from __future__ import annotations

import ast
import math
from pathlib import Path

import pytest

from tool_d.gates.cscv import KetQuaPBO
from tool_d.gates.d9_gate import TIEU_CHI_KHAI, CongD9Error, danh_gia_cong_d9
from tool_d.gates.dsr import N_DANG_KY
from tool_d.gates.ket_cuc import KetCuc
from tool_d.measurement.tri_state import Measured

REPO_ROOT = Path(__file__).resolve().parents[2]


def _on_dinh(m: float, n: int = 100) -> list[float]:
    return [m + (0.1 if i % 2 else -0.1) for i in range(n)]


def _nhieu(m: float, n: int = 400) -> list[float]:
    return [m + (1.0 if i % 2 else -1.0) for i in range(n)]


def _pbo(m: Measured[float]) -> KetQuaPBO:
    return KetQuaPBO(
        pbo=m, so_cau_hinh_dau_vao=4, so_cau_hinh_phan_biet=4, cau_hinh_gop_trung=(),
        so_to_hop=70, so_to_hop_doc_duoc=70 if m.is_ok() else 0, to_hop=(),
    )


def _chi_so(**sua: Measured[float]) -> dict[str, Measured[float]]:
    tot = {
        "liq_buffer_ratio_mean": Measured.ok(20.0),
        "max_single_trade_loss_over_risk_budget": Measured.ok(1.0),
        "skewness_diff_vs_z1": Measured.ok(0.0),
        "trades_per_year": Measured.ok(300.0),
        "tp_fallback_ratio": Measured.ok(0.1),
        "time_stop_ratio": Measured.ok(0.10),  # TD-0277 — giữa dải 5–25%
    }
    tot.update(sua)
    return tot


def _goi(r=None, *, n_trials: int = N_DANG_KY, chi_so=None, pbo: Measured[float] = Measured.ok(0.2)):
    return danh_gia_cong_d9(
        r_trien_khai_test=_on_dinh(1.0) if r is None else r,
        n_trials=n_trials,
        chi_so=_chi_so() if chi_so is None else chi_so,
        ket_qua_pbo=_pbo(pbo),
    )


class TestBaKetCuc:
    def test_moi_tieu_chi_dat_thi_pass(self) -> None:
        kq = _goi()
        assert kq.ket_cuc is KetCuc.PASS and kq.khong_dat == () and kq.chua_do == ()

    def test_pbo_la_so_vuot_nguong_thi_fail_va_chi_pbo(self) -> None:
        """P0: mọi thứ khác đạt, chỉ PBO = 0,8 ⇒ FAIL. Ở D4 cùng số này không chặn."""
        kq = _goi(pbo=Measured.ok(0.8))
        assert kq.ket_cuc is KetCuc.FAIL and kq.khong_dat == ("pbo",)

    def test_pbo_bang_dung_nguong_thi_dat(self) -> None:
        assert _goi(pbo=Measured.ok(0.5)).ket_cuc is KetCuc.PASS

    def test_pbo_unreadable_thi_inconclusive_khong_phai_pass(self) -> None:
        kq = _goi(pbo=Measured.unreadable("12/70 tổ hợp dưới sàn"))
        assert kq.ket_cuc is KetCuc.INCONCLUSIVE and kq.chua_do == ("pbo",)

    def test_skewness_pending_nhu_hom_nay_thi_khong_pass(self) -> None:
        """MT-53: Z1 bị cắt ⇒ skewness `pending` ⇒ D9 KHÔNG PASS dù mọi thứ khác đạt."""
        kq = _goi(chi_so=_chi_so(skewness_diff_vs_z1=Measured.pending("Z1 bị cắt — DR-D4-12 §4.5")))
        assert kq.ket_cuc is KetCuc.INCONCLUSIVE and kq.chua_do == ("skewness_diff_vs_z1",)

    def test_expectancy_nhieu_hon_nguong_thi_inconclusive(self) -> None:
        """400 lệnh 0,2 ± 1: giá trị ≈ 0,046 < 0,10 nhưng thuế ≈ 0,154 > 0,10 ⇒ không phân biệt."""
        kq = _goi(_nhieu(0.2))
        assert kq.phan_loai_expectancy.ket_cuc is KetCuc.INCONCLUSIVE
        assert kq.ket_cuc is KetCuc.INCONCLUSIVE and kq.chua_do == ("dsr_adjusted_expectancy",)

    def test_fail_dung_truoc_inconclusive(self) -> None:
        """Expectancy âm rõ (−0,5 ± 0,1) ⇒ FAIL, dù PBO chưa đo được."""
        kq = _goi(_on_dinh(-0.5), pbo=Measured.unreadable("dưới sàn"))
        assert kq.ket_cuc is KetCuc.FAIL
        assert kq.khong_dat == ("dsr_adjusted_expectancy",) and kq.chua_do == ("pbo",)

    def test_duoi_hai_lenh_thi_expectancy_chua_do(self) -> None:
        kq = _goi([0.5])
        assert kq.ket_cuc is KetCuc.INCONCLUSIVE and "dsr_adjusted_expectancy" in kq.chua_do
        assert kq.phan_loai_expectancy is None

    def test_tieu_chi_khac_do_duoc_ma_truot_thi_fail(self) -> None:
        kq = _goi(chi_so=_chi_so(trades_per_year=Measured.ok(149.0)))
        assert kq.ket_cuc is KetCuc.FAIL and kq.khong_dat == ("trades_per_year",)


class TestNKhongGhim:
    def test_n_doi_thi_ket_cuc_doi(self) -> None:
        """400 lệnh 0,3 ± 1: N=114 ⇒ giá trị ≈ 0,146 ≥ 0,10 PASS; N=10¹² (rào ≈ 7,43) ⇒ thuế
        ≈ 0,372 ⇒ INCONCLUSIVE. Cổng đọc N được truyền vào — DR-007 union đổi được N."""
        assert _goi(_nhieu(0.3), n_trials=114).ket_cuc is KetCuc.PASS
        assert _goi(_nhieu(0.3), n_trials=10**12).ket_cuc is KetCuc.INCONCLUSIVE

    def test_n_trials_khong_co_mac_dinh(self) -> None:
        with pytest.raises(TypeError):
            danh_gia_cong_d9(r_trien_khai_test=_on_dinh(1.0), chi_so=_chi_so(), ket_qua_pbo=_pbo(Measured.ok(0.1)))  # type: ignore[call-arg]

    @pytest.mark.parametrize("xau", [True, 1, 0, 2.0, "114"])
    def test_n_trials_xau(self, xau) -> None:
        with pytest.raises(CongD9Error):
            _goi(n_trials=xau)


class TestDauVao:
    def test_thieu_tieu_chi_phai_khai_pending_khong_duoc_bo(self) -> None:
        cs = _chi_so()
        del cs["tp_fallback_ratio"]
        with pytest.raises(CongD9Error, match="thiếu"):
            _goi(chi_so=cs)

    @pytest.mark.parametrize("la", ["pbo", "dsr_adjusted_expectancy", "khac"])
    def test_khong_nhan_pbo_hay_expectancy_tu_ngoai(self, la: str) -> None:
        cs = {**_chi_so(), la: Measured.ok(0.0)}
        with pytest.raises(CongD9Error, match="thừa"):
            _goi(chi_so=cs)

    def test_chi_so_phai_la_measured(self) -> None:
        with pytest.raises(CongD9Error, match="Measured"):
            _goi(chi_so={**_chi_so(), "trades_per_year": 300.0})

    def test_r_khong_huu_han(self) -> None:
        with pytest.raises(CongD9Error):
            _goi([1.0, math.nan])


class TestDuongNoi:
    def test_d9_gate_goi_evaluate_branch1_voi_pbo_chan_true(self) -> None:
        """AST: lời gọi duy nhất trong d9_gate.py truyền `pbo_chan=True` là HẰNG, không biến."""
        cay = ast.parse((REPO_ROOT / "src/tool_d/gates/d9_gate.py").read_text(encoding="utf-8"))
        goi = [
            n for n in ast.walk(cay)
            if isinstance(n, ast.Call) and getattr(n.func, "attr", getattr(n.func, "id", None)) == "evaluate_branch1"
        ]
        assert len(goi) == 1
        kw = {k.arg: k.value for k in goi[0].keywords}
        assert isinstance(kw.get("pbo_chan"), ast.Constant) and kw["pbo_chan"].value is True

    def test_tieu_chi_khai_cong_expectancy_pbo_bang_bay_tieu_chi_nhanh1(self) -> None:
        from tool_d.gates.thresholds import evaluate_branch1

        assert set(evaluate_branch1({}, pbo_chan=True).failed_criteria) == set(TIEU_CHI_KHAI) | {
            "dsr_adjusted_expectancy", "pbo"
        }
