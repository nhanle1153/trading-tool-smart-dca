"""TD-0337 (`DR-D4-14`, phần dựng của TD-0186) — `close_d4_gate()` (E6 `--close-d4-gate`).

Canh:
1. 🔴 **Trên trạng thái THẬT hôm nay cổng TỪ CHỐI** và không ghi một byte nào vào
   `runtime_state.json` — hành vi mong đợi ghi trước ở `DR-D4-14` §8.
2. Ba phép phá bắt buộc của `DR-D4-11` §7: thiếu `Z0-T1` ⇒ từ chối; `Z0-T1` mang `mo_ta` ⇒ từ
   chối; kế toán B2 lệch số bản ghi ⇒ từ chối (QUAN HỆ, không hằng số).
3. Bốn bằng chứng `DR-D4-04` §7 (TD-0339) đọc từ hiện vật E3 — trượt/thiếu ⇒ từ chối; §1.7 lệch > 5% ⇒ DỪNG
   (`DR-D4-15`). Gate §10.2 được GHI, không chặn đóng cổng (`DR-D4-11`).
4. Đường thành công (bằng chứng đọc từ hiện vật E3, TD-0339): ghi `d4_complete`,
   `d4_huong = "LONG"`, `d4_han_che` nhắc DCA; chạy lại ⇒ 94.
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "entrypoints"))

import trial_ledger_audit  # noqa: E402
from trial_ledger_audit import (  # noqa: E402
    BANG_CHUNG_DR_D4_04,
    DUONG_DAN_TEST_D4,
    EXIT_GATE_ALREADY_CLOSED,
    EXIT_GATE_AUDIT_DIRTY,
    build_parser,
    close_d4_gate,
)

from tool_d.ablation.ban_ghi import LO_ARM_D4, dung_ban_ghi_arm  # noqa: E402
from tool_d.measurement.tri_state import Measured  # noqa: E402
from tool_d.ledger.registry import TrialLedger  # noqa: E402
from tool_d.measurement.provenance import Provenance  # noqa: E402
from tool_d.wfo.folds import Fold  # noqa: E402
from tool_d.wfo.lenh import LenhWFO  # noqa: E402

PASS_CMD = [sys.executable, "-c", "print('2700 passed in 900.0s')"]
D4_PASS = [sys.executable, "-c", "import sys; print('17 passed in 3.0s')", "--"]

FOLDS = (Fold(1, date(2025, 6, 12), date(2025, 9, 4), date(2025, 9, 4), date(2026, 1, 29)),)
LENH = [
    LenhWFO("LTC/USDT:USDT", d, d, p, 2.0, 4.0)
    for d, p in (
        (datetime(2025, 7, 1), 2.0), (datetime(2025, 8, 15), -2.0), (datetime(2025, 9, 10), 4.0),
        (datetime(2025, 11, 2), -1.0), (datetime(2025, 12, 20), 3.0), (datetime(2026, 1, 5), -2.0),
    )
]


@pytest.fixture(autouse=True)
def _moi_truong_sach(monkeypatch):
    """Cây sạch + D0-PRE đóng — cùng lý do bộ test cổng D3.5: không ghim thì ca đường-thành-công
    đỏ/xanh theo việc phiên khác đang gõ dở, tức đo MÔI TRƯỜNG chứ không đo code."""
    from tool_d.measurement.gitinfo import GitInfo

    monkeypatch.setattr(trial_ledger_audit, "get_git_info", lambda _: GitInfo(sha="c" * 40, is_clean=True))
    monkeypatch.setattr(trial_ledger_audit, "_thay_doi_anh_huong_phep_do", lambda _: [])
    monkeypatch.setattr(trial_ledger_audit, "is_d0_pre_complete", lambda: True, raising=False)


def _state(tmp_path: Path, **khoa) -> Path:
    p = tmp_path / "runtime_state.json"
    s = {"d0_pre_complete": True, "d1_complete": True, "d2_complete": True, "d3_complete": True, "d3_5_complete": True}
    s.update(khoa)
    p.write_text(json.dumps(s), encoding="utf-8")
    return p


def _prov() -> Provenance:
    return Provenance(
        params_source="yaml", params_effective={}, git_sha="deadbeef", reproducible_from_sha=True,
        data_hashes={}, cache_mode="none", guard_passed=True, runtime_image_digest="sha256:" + "a" * 64,
    )


def _dat_cho_b2(so: TrialLedger, arm: str) -> str:
    tid = so.reserve(
        n_dang_ky=114, budget_line="B2", hypothesis_slot="TD-0337-TEST", direction="LONG", dataset="WFO",
        param_under_test="tier_c.arm_ablation.arm", param_value=arm, params_frozen_hash="n/a",
        config_hash="n/a", code_commit="0" * 40,
        provenance={
            "params_source": "yaml", "params_effective": {}, "git_sha": "0" * 40,
            "reproducible_from_sha": True, "data_hashes": {}, "cache_mode": "none", "guard_passed": True,
        },
        contribution=1,
    )
    so.seal(tid, seal_path=f"runs/{tid}/metrics.seal")
    so.consume(tid, outcome={"expectancy": None, "sharpe": None, "n_trades": 6, "max_single_loss_ratio": None},
               verdict="INCONCLUSIVE")
    return tid


#: Chỉ số export "đạt" — đúng các khoá `chi_so_export.chi_so_tu_export` sinh ra.
CHI_SO_THEM_DAT = {
    "tp_fallback_ratio": Measured.ok(0.1),
    "time_stop_ratio": Measured.ok(0.1),
    "max_single_trade_loss_over_risk_budget": Measured.ok(1.0),
    "trades_per_year": Measured.ok(300.0),
    "skewness_r_trien_khai": Measured.ok(0.0),
    "ti_trong_tranche_dat": Measured.ok(True),
    "stake_theo_r_eff_rho": Measured.ok(0.8),
    "bat_bien_1_7_ty_so_trung_vi": Measured.ok(0.98),
}


def _hien_vat(
    tmp_path: Path, arms=LO_ARM_D4, *, so_b2: int | None = None, sua=None, them=None,
    chien_luoc: str | None = "ZoneAbsorption",
) -> dict:
    """Dựng `runs/` + sổ tạm. `so_b2` khác số arm ⇒ kế toán lệch có chủ đích."""
    runs = tmp_path / "runs"
    reg = tmp_path / "reg.jsonl"
    iq = tmp_path / "iq.jsonl"
    iq.touch()
    so = TrialLedger(path=reg)
    for i, arm in enumerate(arms):
        tid = _dat_cho_b2(so, arm) if (so_b2 is None or i < so_b2) else f"D-99{i}"
        bg = dung_ban_ghi_arm(
            arm=arm, lenhs=LENH, cua_so=(date(2025, 6, 12), date(2026, 1, 28)), folds=FOLDS, so_ma_da_chay=107,
            delta_r_pham_vi={"so_ma": 2, "so_fill": 91, "dataset": "CALIB", "chien_luoc": "ZoneAbsorptionMinimal"},
            provenance=_prov(), trial_id=tid, nguong=0.10,
            chi_so_them={**CHI_SO_THEM_DAT, **(them or {})},
        )
        if sua:
            sua(bg)
        (runs / tid).mkdir(parents=True)
        (runs / tid / "arm_result.json").write_text(json.dumps(bg, ensure_ascii=False), encoding="utf-8")
        if chien_luoc is not None:
            (runs / tid / "ket_qua_chay.json").write_text(json.dumps({"chien_luoc": chien_luoc}), encoding="utf-8")
    return {"runs_dir": runs, "registry_path": reg, "idea_queue_path": iq}


def _goi(sp: Path, hv: dict, bo_test=D4_PASS):
    return close_d4_gate(
        runtime_state_path=sp, pytest_cmd=PASS_CMD, pytest_d4_cmd=D4_PASS, pytest_bo_test_cmd=bo_test, **hv
    )


class TestTrangThaiThatHomNay:
    def test_tu_choi_va_khong_ghi_byte_nao(self) -> None:
        sp = REPO_ROOT / "registry" / "runtime_state.json"
        truoc = sp.read_bytes()
        ma, text = close_d4_gate(
            runtime_state_path=sp, repo_dir=REPO_ROOT, runs_dir=REPO_ROOT / "runs",
            registry_path=REPO_ROOT / "registry" / "trial_registry.jsonl",
            pytest_cmd=PASS_CMD, pytest_d4_cmd=D4_PASS,
        )
        assert ma == EXIT_GATE_AUDIT_DIRTY
        assert "Z0-T1" in text and "DR-D4-04 §7" in text
        assert sp.read_bytes() == truoc


class TestThuTuCong:
    @pytest.mark.parametrize("khoa", ["d1_complete", "d2_complete", "d3_complete", "d3_5_complete"])
    def test_cong_truoc_chua_dong(self, tmp_path, khoa) -> None:
        sp = _state(tmp_path, **{khoa: False})
        ma, text = _goi(sp, _hien_vat(tmp_path))
        assert ma == EXIT_GATE_AUDIT_DIRTY and khoa in text

    def test_da_dong_thi_94(self, tmp_path) -> None:
        sp = _state(tmp_path, d4_complete=True)
        assert _goi(sp, _hien_vat(tmp_path))[0] == EXIT_GATE_ALREADY_CLOSED

    def test_cay_ban_thi_tu_choi(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr(trial_ledger_audit, "_thay_doi_anh_huong_phep_do", lambda _: ["M src/x.py"])
        ma, text = _goi(_state(tmp_path), _hien_vat(tmp_path))
        assert ma == EXIT_GATE_AUDIT_DIRTY and "ẢNH HƯỞNG PHÉP ĐO" in text


class TestBaPhepPhaDRD411:
    def test_thieu_Z0_T1(self, tmp_path) -> None:
        ma, text = _goi(_state(tmp_path), _hien_vat(tmp_path, arms=("Z0", "Z0-T0", "Z3")))
        assert ma == EXIT_GATE_AUDIT_DIRTY and "thiếu bản ghi arm 'Z0-T1'" in text

    def test_Z0_T1_mang_mo_ta(self, tmp_path) -> None:
        def _sua(bg):
            if bg["arm"] == "Z0-T1":
                bg["pham_vi_phan_quyet"] = "mo_ta"

        ma, text = _goi(_state(tmp_path), _hien_vat(tmp_path, sua=_sua))
        assert ma == EXIT_GATE_AUDIT_DIRTY and "phan_quyet" in text

    def test_ke_toan_B2_lech_so_ban_ghi(self, tmp_path) -> None:
        ma, text = _goi(_state(tmp_path), _hien_vat(tmp_path, so_b2=3))
        assert ma == EXIT_GATE_AUDIT_DIRTY and "kế toán lệch" in text


class TestBangChungDRD404:
    """TD-0339 — bốn bằng chứng đọc từ hiện vật E3. Mỗi cái trượt ⇒ cổng TỪ CHỐI, không ghi byte nào."""

    @pytest.mark.parametrize(
        "kw, mong",
        [
            ({"chien_luoc": None}, "chien_luoc_da_chay"),
            ({"chien_luoc": "ZoneAbsorptionMinimal"}, "ZoneAbsorptionMinimal"),
            ({"them": {"ti_trong_tranche_dat": Measured.ok(False)}}, "ti_trong_tranche_fill"),
            ({"them": {"stake_theo_r_eff_rho": Measured.ok(-0.2)}}, "stake_theo_r_eff"),
            ({"them": {"stake_theo_r_eff_rho": Measured.unreadable("stake hằng")}}, "stake hằng"),
            ({"them": {"tp_fallback_ratio": Measured.unreadable("0 lần TP1")}}, "h4_tp_fallback"),
        ],
    )
    def test_bang_chung_truot_thi_tu_choi(self, tmp_path, kw, mong) -> None:
        sp = _state(tmp_path)
        truoc = sp.read_text(encoding="utf-8")
        ma, text = _goi(sp, _hien_vat(tmp_path, **kw))
        assert ma == EXIT_GATE_AUDIT_DIRTY and "DR-D4-04 §7" in text and mong in text
        assert sp.read_text(encoding="utf-8") == truoc

    def test_bon_bang_chung_dung_ten(self) -> None:
        assert [t for t, _ in BANG_CHUNG_DR_D4_04] == [
            "chien_luoc_da_chay", "ti_trong_tranche_fill", "stake_theo_r_eff", "h4_tp_fallback",
        ]


class TestBatBien17:
    @pytest.mark.parametrize("ty_so", [0.90, 1.07])
    def test_lech_qua_5_phan_tram_thi_DUNG(self, tmp_path, ty_so) -> None:
        ma, text = _goi(_state(tmp_path), _hien_vat(tmp_path, them={"bat_bien_1_7_ty_so_trung_vi": Measured.ok(ty_so)}))
        assert ma == EXIT_GATE_AUDIT_DIRTY and "DR-D4-15" in text

    def test_khong_do_duoc_thi_khong_dung_nhung_khai_trong_han_che(self, tmp_path) -> None:
        sp = _state(tmp_path)
        ma, text = _goi(sp, _hien_vat(tmp_path, them={"bat_bien_1_7_ty_so_trung_vi": Measured.unreadable("0 lệnh đủ ba tranche")}))
        assert ma == 0, text
        assert "0 lệnh đủ ba tranche" in json.loads(sp.read_text(encoding="utf-8"))["d4_han_che"]["noi_dung"]


class TestDuongThanhCong:
    def test_dong_ghi_khoa_roi_chay_lai_94(self, tmp_path) -> None:
        sp = _state(tmp_path)
        hv = _hien_vat(tmp_path)
        ma, text = _goi(sp, hv)
        assert ma == 0, text
        s = json.loads(sp.read_text(encoding="utf-8"))
        assert s["d4_complete"] is True and s["d4_huong"] == "LONG"
        han_che = s["d4_han_che"]["noi_dung"]
        assert s["d4_han_che"]["nguon"] == "nguoi-khai" and "DCA" in han_che
        for muc in ("(1)", "(2)", "(3)", "(4)", "(5)", "(6)", "(7)", "(8)"):
            assert muc in han_che, muc
        assert {t for t, _ in BANG_CHUNG_DR_D4_04} <= set(s["d4_evidence"])
        # Bản ghi mẫu 6 lệnh ⇒ DSR INCONCLUSIVE; liq_buffer còn pending (TD-0342, chờ duyệt nghĩa cột) ⇒ Nhánh 1
        # KHÔNG thể PASS — và cổng VẪN đóng, vì D4 đóng bằng hiện vật phán quyết (DR-D4-11), không đòi PASS.
        assert "Nhánh 1 = INCONCLUSIVE" in s["d4_evidence"]["gate_d09"]["noi_dung"]
        assert "liq_buffer_ratio_mean" in s["d4_evidence"]["gate_d09"]["noi_dung"]
        assert "skewness_diff_vs_z1" in s["d4_evidence"]["gate_d09"]["noi_dung"]  # liệt kê "không áp dụng"
        assert _goi(sp, hv)[0] == EXIT_GATE_ALREADY_CLOSED

    def test_bo_test_truot_van_DONG_cong_nhung_ghi_FAIL(self, tmp_path) -> None:
        """DR-D4-11: cổng đóng bằng HIỆN VẬT phán quyết — kết cục FAIL cũng là kết quả của D4, không phải lý do giữ cổng."""
        sp = _state(tmp_path)
        truot = [sys.executable, "-c", "import sys; print('1 failed, 16 passed'); sys.exit(1)", "--"]
        ma, text = _goi(sp, _hien_vat(tmp_path), bo_test=truot)
        assert ma == 0, text
        gate = json.loads(sp.read_text(encoding="utf-8"))["d4_evidence"]["gate_d09"]["noi_dung"]
        assert "Nhánh 1 = FAIL" in gate and "h4d" in gate


class TestNoiVaoE6:
    def test_co_co_close_d4_gate(self) -> None:
        assert build_parser().parse_args(["--close-d4-gate"]).close_d4_gate is True

    def test_moi_mau_bo_test_khop_dung_mot_file(self) -> None:
        from trial_ledger_audit import DUONG_DAN_TEST_H4D, DUONG_DAN_TEST_LZ10_LZ33, _mo_rong_mau

        assert len(_mo_rong_mau(DUONG_DAN_TEST_H4D + DUONG_DAN_TEST_LZ10_LZ33, REPO_ROOT)) == 21

    def test_file_test_cot_loi_ton_tai(self) -> None:
        for p in DUONG_DAN_TEST_D4:
            assert (REPO_ROOT / p).is_file(), p
