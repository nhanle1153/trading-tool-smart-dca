"""TD-0057 — `run_audit()` (E6, H16) phải được gọi trong `main()` của
E1/E2/E3, TRƯỚC bất kỳ lệnh tốn thời gian nào (spec dòng 660: "tự kiểm
cả chính nó" TRƯỚC MỖI lần backtest). Kiểm bằng AST — cùng phương pháp
với L-Z36 (test_lz36_entrypoint_guard.py), không phải chạy thử rồi đoán.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ENTRYPOINTS_WITH_AUDIT = ("run_backtest.py", "run_wfo.py", "run_ablation.py")


def _main_function_calls(entrypoint_file: str) -> list[str]:
    """Tên các hàm được gọi trực tiếp bên trong `main()`, theo ĐÚNG thứ
    tự xuất hiện trong mã nguồn."""
    path = REPO_ROOT / "entrypoints" / entrypoint_file
    tree = ast.parse(path.read_text(encoding="utf-8"))
    calls: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "main":
            for sub in ast.walk(node):
                if isinstance(sub, ast.Call):
                    func = sub.func
                    if isinstance(func, ast.Name):
                        calls.append(func.id)
                    elif isinstance(func, ast.Attribute):
                        calls.append(func.attr)
            break
    return calls


class TestRunAuditDuocGoiTrongMainCuaE1E2E3:
    @pytest.mark.parametrize("entrypoint_file", ENTRYPOINTS_WITH_AUDIT)
    def test_run_audit_co_mat_trong_main(self, entrypoint_file: str) -> None:
        calls = _main_function_calls(entrypoint_file)
        assert "run_audit" in calls, f"{entrypoint_file}: main() không gọi run_audit()"

    @pytest.mark.parametrize("entrypoint_file", ENTRYPOINTS_WITH_AUDIT)
    def test_run_audit_dung_sau_guard_khong_bi_bo_qua_boi_return_som(
        self, entrypoint_file: str
    ) -> None:
        # measurement_guard() vẫn phải đứng TRƯỚC run_audit() — guard là
        # lớp canh ngoài cùng (0d.1), audit sổ là lớp canh sau đó (H16).
        calls = _main_function_calls(entrypoint_file)
        assert calls.index("measurement_guard") < calls.index("run_audit")

    def test_import_run_audit_tu_dung_module(self) -> None:
        for f in ENTRYPOINTS_WITH_AUDIT:
            text = (REPO_ROOT / "entrypoints" / f).read_text(encoding="utf-8")
            assert "from trial_ledger_audit import run_audit" in text, f"{f} thiếu import run_audit"


class TestKhongBoTacDungCuaCacTest0016_0018:
    """Đảm bảo TD-0057 không vô tình xoá mất các cơ chế đã có (L-Z36:
    danh sách đóng entrypoint, TD-0018: assert_cache_none của E1)."""

    def test_e1_van_giu_assert_cache_none_truoc_run_audit(self) -> None:
        calls = _main_function_calls("run_backtest.py")
        assert calls.index("assert_cache_none") < calls.index("run_audit")

    def test_danh_sach_dong_entrypoint_khong_doi(self) -> None:
        files = sorted(p.name for p in (REPO_ROOT / "entrypoints").glob("*.py"))
        assert files == [
            "backfill_data.py",
            "build_pool.py",
            "periodic_report.py",
            "run_ablation.py",
            "run_backtest.py",
            "run_wfo.py",
            "touch_lockbox.py",
            "trial_ledger_audit.py",
        ]
