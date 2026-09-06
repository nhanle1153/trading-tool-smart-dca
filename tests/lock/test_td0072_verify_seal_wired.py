"""TD-0072 — `verify_all_seals()` (E4, H17) phải được gọi trong `main()`
của E1/E2/E3, đứng SAU `measurement_guard()` và `run_audit()`. Kiểm bằng
AST, cùng phương pháp L-Z36/TD-0057.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ENTRYPOINTS_WITH_SEAL_VERIFY = ("run_backtest.py", "run_wfo.py", "run_ablation.py")


def _main_function_calls(entrypoint_file: str) -> list[str]:
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


class TestVerifyAllSealsDuocGoiTrongMain:
    @pytest.mark.parametrize("entrypoint_file", ENTRYPOINTS_WITH_SEAL_VERIFY)
    def test_verify_all_seals_co_mat_trong_main(self, entrypoint_file: str) -> None:
        calls = _main_function_calls(entrypoint_file)
        assert "verify_all_seals" in calls, f"{entrypoint_file}: main() không gọi verify_all_seals()"

    @pytest.mark.parametrize("entrypoint_file", ENTRYPOINTS_WITH_SEAL_VERIFY)
    def test_thu_tu_guard_audit_seal(self, entrypoint_file: str) -> None:
        calls = _main_function_calls(entrypoint_file)
        assert (
            calls.index("measurement_guard")
            < calls.index("run_audit")
            < calls.index("verify_all_seals")
        )

    def test_import_dung_module(self) -> None:
        for f in ENTRYPOINTS_WITH_SEAL_VERIFY:
            text = (REPO_ROOT / "entrypoints" / f).read_text(encoding="utf-8")
            assert "from tool_d.lockbox.seal import verify_all_seals" in text
            assert "from touch_lockbox import" in text and "LOCKBOX_DIR" in text

    def test_dung_thu_muc_futures_khong_phai_thu_muc_data_cha(self) -> None:
        # TD-0084 — bug thật đã bắt: build_seal() (E4 --seal-initial) hash
        # file trong lockbox/data/futures/ (Freqtrade --trading-mode futures
        # luôn lồng thêm thư mục con "futures/"), nhưng verify_all_seals()
        # từng được gọi với LOCKBOX_DATA_DIR (= lockbox/data, THIẾU
        # "/futures") → mọi file báo "MISSING", L-Z14 FAIL 100% dù dữ liệu
        # đúng. Không ai bắt được vì trước TD-0084 chưa từng có seal thật
        # (0 seal = PASS rỗng, che mất bug). Khoá: phải dùng
        # LOCKBOX_FUTURES_DIR, KHÔNG được quay lại LOCKBOX_DATA_DIR.
        for f in ENTRYPOINTS_WITH_SEAL_VERIFY:
            text = (REPO_ROOT / "entrypoints" / f).read_text(encoding="utf-8")
            assert "LOCKBOX_FUTURES_DIR" in text
            assert "verify_all_seals(LOCKBOX_DIR, LOCKBOX_DATA_DIR)" not in text
            assert "verify_all_seals(LOCKBOX_DIR, LOCKBOX_FUTURES_DIR)" in text
