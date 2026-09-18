"""TD-0072 — cổng H17 phải được gọi trong `main()` của E1/E2/E3, đứng SAU
`measurement_guard()` và `run_audit()`. Kiểm bằng AST, cùng phương pháp L-Z36/TD-0057.

🔁 ĐẢO CHIỀU 18/09/2026 (TD-0316, `DR-LOCKBOX-02`), không xoá — tiền lệ TD-0150. Bản trước ghim
*"E1/E2/E3 gọi `verify_all_seals()`"*; hàm đó băm dữ liệu lockbox, mà ở service chạy pipeline dữ
liệu bị che CÓ CHỦ ĐÍCH ⇒ exit 89 MỌI LẦN. Nay cổng H17 ở E1/E2/E3 là `kiem_h17()` (cách ly còn
hiệu lực + seal không bị sửa + sổ truy cập); `verify_all_seals()` thành công cụ riêng của E4.
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
    def test_kiem_h17_co_mat_va_verify_all_seals_KHONG_con_trong_main(self, entrypoint_file: str) -> None:
        calls = _main_function_calls(entrypoint_file)
        assert "kiem_h17" in calls, f"{entrypoint_file}: main() không gọi kiem_h17()"
        assert "verify_all_seals" not in calls, (
            f"{entrypoint_file}: main() còn gọi verify_all_seals() — ở service che lockbox nó FAIL mọi lần"
        )

    @pytest.mark.parametrize("entrypoint_file", ENTRYPOINTS_WITH_SEAL_VERIFY)
    def test_thu_tu_guard_audit_seal(self, entrypoint_file: str) -> None:
        calls = _main_function_calls(entrypoint_file)
        assert (
            calls.index("measurement_guard")
            < calls.index("run_audit")
            < calls.index("kiem_h17")
        )

    def test_import_dung_module(self) -> None:
        for f in ENTRYPOINTS_WITH_SEAL_VERIFY:
            text = (REPO_ROOT / "entrypoints" / f).read_text(encoding="utf-8")
            assert "from tool_d.lockbox.h17 import in_va_ma_thoat, kiem_h17" in text
            assert "from tool_d.lockbox.seal import verify_all_seals" not in text
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
            # TD-0316: bài học giữ nguyên — truyền nhầm thư mục cha thì phép CÁCH LY thành PASS
            # rỗng (thư mục sai luôn "không đọc được"), đúng hình bug TD-0084 theo chiều ngược.
            assert "data_dir=LOCKBOX_DATA_DIR" not in text
            assert "kiem_h17(lockbox_dir=LOCKBOX_DIR, data_dir=LOCKBOX_FUTURES_DIR)" in text
