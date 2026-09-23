"""🔒 TD-0373 (`DR-ZA-01` §2) — khoá đo D5 `D5_DO_TAM_DUNG`: 0 suất `B1` cho Zone Absorption LONG.

Trước khoá này, *"0 suất B1"* chỉ là chữ: `d4_complete = true` nên `registry.reserve()` nhận một suất B1 hợp lệ
theo `DR-D5-01` ngay khi ai đó chạy E1. Canh:

1. Khoá đang BẬT (ghim giá trị kèm DR — muốn lật phải sửa đúng dòng có nhắc quyết định).
2. Cửa sổ `TrialLedger.reserve(budget_line="B1")` từ chối với ĐÚNG sổ + trạng thái cho qua khi khoá tắt — tức khoá là
   thứ duy nhất chặn, và sổ không thêm dòng nào.
3. Khoá đứng ĐẦU `_kiem_cua_b1()` (trước khi đọc DR/sổ).
4. E1 `--budget-line B1` ⇒ `EXIT_D5_DO_TAM_DUNG` TRƯỚC khi đọc cấu hình/rổ, trước khi tạo `TrialLedger`.
5. Dòng không phải B1 không bị khoá này chặn.
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from tool_d.ablation import khoa_do
from tool_d.ledger.registry import B1Error, TrialLedger
from tool_d.measurement.guard import GuardOutcome

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "entrypoints"))
import run_backtest  # noqa: E402

DR_THAT = REPO_ROOT / "docs/decisions/DR-D5-01-pham-vi-ung-vien-luat-chon-calibration.md"


def _prov() -> dict:
    return {
        "params_source": "yaml", "params_effective": {}, "git_sha": "a" * 40,
        "reproducible_from_sha": True, "data_hashes": {}, "cache_mode": "none", "guard_passed": True,
    }


def _so(tmp_path: Path) -> tuple[TrialLedger, Path]:
    reg = tmp_path / "reg.jsonl"
    state = tmp_path / "runtime_state.json"
    state.write_text(json.dumps({"d4_complete": True}), encoding="utf-8")
    return TrialLedger(reg, dr_d5_path=DR_THAT, runtime_state_path=state), reg


def _kw(**doi) -> dict:
    kw = dict(
        n_dang_ky=114, budget_line="B1", hypothesis_slot="D5", direction="LONG", dataset="CALIB",
        param_under_test="zss_threshold", param_value=0.4, params_frozen_hash="f", config_hash="c",
        code_commit="a" * 40, provenance=_prov(), contribution=1,
    )
    kw.update(doi)
    return kw


def _so_dong(reg: Path) -> int:
    return len(reg.read_text(encoding="utf-8").splitlines()) if reg.exists() else 0


class TestKhoaDangBat:
    def test_khoa_d5_BAT(self) -> None:
        assert khoa_do.D5_DO_TAM_DUNG is True, (
            "DR-ZA-01 §2: 0 suất B1 cho ZA LONG. Lật khoá cần ứng viên được CHỌN + DR mở khoá viết trước."
        )

    def test_ly_do_neu_dich_danh_DR(self) -> None:
        assert "DR-ZA-01" in khoa_do.LY_DO_KHOA_D5 and "D5_DO_TAM_DUNG" in khoa_do.LY_DO_KHOA_D5


class TestCuaSo:
    def test_reserve_B1_bi_tu_choi_so_dung_yen(self, tmp_path) -> None:
        so, reg = _so(tmp_path)
        with pytest.raises(B1Error, match="D5_DO_TAM_DUNG"):
            so.reserve(**_kw())
        assert _so_dong(reg) == 0

    def test_cung_suat_ay_qua_duoc_khi_tat_khoa(self, tmp_path, monkeypatch) -> None:
        """Kiểm có răng: chứng minh KHOÁ là thứ duy nhất chặn ca trên, không phải một luật khác của DR-D5-01."""
        monkeypatch.setattr(khoa_do, "D5_DO_TAM_DUNG", False)
        so, reg = _so(tmp_path)
        so.reserve(**_kw())
        assert _so_dong(reg) == 1

    @pytest.mark.parametrize("dong", ["B0", "B3"])
    def test_dong_khac_khong_qua_khoa_d5(self, tmp_path, dong) -> None:
        so, reg = _so(tmp_path)
        so.reserve(**_kw(budget_line=dong, param_under_test="n/a", param_value=None))
        assert _so_dong(reg) == 1

    def test_khoa_dung_dau_cua_b1(self) -> None:
        """Lệnh đầu tiên (sau docstring + import cục bộ) của `_kiem_cua_b1` là phép kiểm khoá."""
        nguon = (REPO_ROOT / "src/tool_d/ledger/registry.py").read_text(encoding="utf-8")
        cay = ast.parse(nguon)
        ham = next(n for n in ast.walk(cay) if isinstance(n, ast.FunctionDef) and n.name == "_kiem_cua_b1")
        than = [n for n in ham.body if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant))]
        than = [n for n in than if not isinstance(n, ast.ImportFrom)]
        dau = than[0]
        assert isinstance(dau, ast.If) and "D5_DO_TAM_DUNG" in ast.unparse(dau.test)


def _chan(ten: str):
    def _f(*_a, **_k):
        raise AssertionError(f"E1 gọi {ten} dù khoá D5 đang bật")

    return _f


class TestE1:
    @pytest.fixture
    def e1_qua_nam_cong(self, monkeypatch):
        """Cho E1 qua năm cổng đứng trước (guard, D0-PRE, cache, audit, H17) để ca đo ĐÚNG khoá D5, và chặn
        mọi thứ phía sau — đọc cấu hình, rổ, mở sổ — bằng lỗi: khoá phải trả về TRƯỚC chúng."""
        monkeypatch.setattr(
            run_backtest, "measurement_guard", lambda *a, **k: SimpleNamespace(outcome=GuardOutcome.PASS)
        )
        monkeypatch.setattr(run_backtest, "require_d0_pre_complete", lambda *_a: None)
        monkeypatch.setattr(run_backtest, "assert_cache_none", lambda *_a: None)
        monkeypatch.setattr(run_backtest, "run_audit", lambda *a, **k: (0, ""))
        monkeypatch.setattr(run_backtest, "in_va_ma_thoat", lambda *a, **k: None)
        monkeypatch.setattr(run_backtest, "kiem_h17", lambda *a, **k: None)
        for ten in ("load_tool_d_config", "ro_cho_tap", "TrialLedger"):
            monkeypatch.setattr(run_backtest, ten, _chan(ten))

    def test_B1_thoat_ma_rieng_truoc_khi_doc_gi(self, e1_qua_nam_cong, capsys) -> None:
        ma = run_backtest.main(["--tap", "CALIB", "--budget-line", "B1", "--param-under-test", "D5_MOC", "--chay"])
        assert ma == run_backtest.EXIT_D5_DO_TAM_DUNG
        assert "D5_DO_TAM_DUNG" in capsys.readouterr().out

    def test_ma_thoat_moi_khong_trung_E3(self) -> None:
        import run_ablation

        assert run_backtest.EXIT_D5_DO_TAM_DUNG != run_ablation.EXIT_D4_DO_TAM_DUNG

    def test_dong_khac_di_qua_khoa(self, e1_qua_nam_cong) -> None:
        """B3 không bị khoá D5 chặn: E1 đi tiếp tới đọc cấu hình (ở đây bị chặn giả ⇒ AssertionError)."""
        with pytest.raises(AssertionError, match="load_tool_d_config"):
            run_backtest.main(["--tap", "CALIB", "--budget-line", "B3"])
