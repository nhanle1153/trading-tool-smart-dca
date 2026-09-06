"""TD-0071 — E4 `touch_lockbox.py`, chế độ `--verify-seal` (H17) + TỪ CHỐI
chế độ chạm thật. Canh bởi L-Z13/L-Z14 (đã kiểm ở mức hàm trong
`tests/lock/test_lz14_lockbox_seal_hash.py`); test này khoá đúng HÀNH VI
người vận hành thấy qua CLI, cùng phong cách `test_run_backtest_cache.py`
(TD-0018): chạy như tiến trình con, `cwd=REPO_ROOT`.

Chạy trên `lockbox/` THẬT của repo — ở D0-PRE hiện tại nó không có seal
nào (đúng trạng thái trước TD-0084), nên `--verify-seal` phải PASS
(0 seal = không có gì để xác nhận). Không dùng `tmp_path` làm `cwd` vì
`measurement_guard()` đọc `config/tool_d_config.yaml` theo đường dẫn
tương đối — cách ly khỏi repo thật sẽ làm guard tự crash trước khi chạm
tới code của TD-0071 (case lệch seal/nhiều seal đã kiểm ở mức hàm).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
E4 = REPO_ROOT / "entrypoints" / "touch_lockbox.py"
ACCESS_LOG = REPO_ROOT / "lockbox" / "lockbox_access.log"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(E4), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


class TestVerifySealModeTrenLockboxThat:
    def test_khong_co_seal_nao_thi_pass(self) -> None:
        # Đúng trạng thái D0-PRE hiện tại (trước TD-0084) — assert lại để
        # nếu ai đó lỡ thêm lockbox_seal_*.json thật vào repo, test này
        # đỏ và nhắc soát lại giả định, thay vì âm thầm sai.
        assert list((REPO_ROOT / "lockbox").glob("lockbox_seal_*.json")) == []

        result = _run("--verify-seal")
        assert result.returncode == 0
        assert "PASS" in result.stdout

    def test_verify_seal_khong_ghi_so_truy_cap(self) -> None:
        _run("--verify-seal")
        assert not ACCESS_LOG.exists()


class TestCheDoChamThatBiTuChoi:
    def test_khong_co_co_verify_seal_thi_tu_choi(self) -> None:
        result = _run()
        assert result.returncode not in (0, 86, 87)  # không lẫn với guard/cache
        assert "TỪ CHỐI" in result.stdout

    def test_tu_choi_khong_ghi_so_truy_cap(self) -> None:
        _run()
        assert not ACCESS_LOG.exists()

    def test_ma_thoat_khac_verify_seal_va_guard(self) -> None:
        tu_choi = _run().returncode
        verify_ok = _run("--verify-seal").returncode
        assert tu_choi != verify_ok
