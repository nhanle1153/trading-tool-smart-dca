"""TD-0018 — `assert_cache_none()` nối vào E1. Canh bởi L-Z38.

Chạy E1 như một tiến trình con (không `import entrypoints...` — thư mục đó
không phải package trên `pythonpath`, và verify chính thức của TD-0018
trong TASKS.md cũng là gọi trực tiếp qua CLI) để khoá đúng hành vi người
vận hành thấy: thiếu `--cache none` phải TỪ CHỐI (exit 87), không tự chèn.

Test khoá AST kiểm tra guard được gọi trong `main()` của mọi entrypoint
(TD-0017, L-Z36) nằm ở test_lz36_entrypoint_guard.py.

TD-0084 — sau khi `lockbox_seal_1.json` niêm phong thật, `verify_all_seals()`
(TD-0072, chạy SAU cache-check, TRƯỚC `NotImplementedError`) chặn đường đi
tiếp trong service `tests` (nơi bộ test này chạy) vì `lockbox/data/` bị
volume ẩn danh che (ARCHITECTURE.md 3.1) — seal khớp thật ở service
`lockbox` (DR-D0PRE-07 mục 6) nhưng KHÔNG khớp ở đây, đúng thiết kế cách
ly. Vì vậy đường đi "cache OK -> rơi xuống NotImplementedError" không còn
quan sát được từ service `tests` nữa — cache-check vẫn PASS (không đổi),
chỉ là bước SAU nó (seal-verify) giờ chặn trước khi tới đích cũ.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
E1 = REPO_ROOT / "entrypoints" / "run_backtest.py"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(E1), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


class TestAssertCacheNoneNoiVaoE1:
    def test_thieu_co_cache_none_thi_tu_choi(self) -> None:
        result = _run("--timerange", "X")
        assert result.returncode == 87
        assert "--cache none" in result.stdout

    def test_co_cache_none_thi_khong_bi_chan_boi_cache_check(self) -> None:
        # Guard PASS, cache OK -> KHÔNG bị assert_cache_none chặn (exit khác 87).
        # 🔁 ĐẢO CHIỀU 18/09/2026 (TD-0316, DR-LOCKBOX-02): bản trước khẳng định exit 89 —
        # tức ghim ĐÚNG hành vi hỏng (E1 không bao giờ qua cổng seal ở service chạy nó). Nay
        # E1 THẬT (tiến trình con, main() thật) qua H17 và dừng ở cổng KẾ: thiếu --tap (107).
        # Đây là ca đường-chạy-thật duy nhất qua cổng H17 của E1.
        result = _run("--timerange", "X", "--cache", "none")
        assert result.returncode == 107, result.stdout
        assert "thiếu --tap" in result.stdout
        assert "H17" not in result.stdout and "L-Z14" not in result.stdout

    def test_dang_viet_co_cach_khac_van_duoc_nhan_dien(self) -> None:
        result = _run("--timerange", "X", "--cache=none")
        assert result.returncode == 107, result.stdout
        assert "thiếu --tap" in result.stdout
