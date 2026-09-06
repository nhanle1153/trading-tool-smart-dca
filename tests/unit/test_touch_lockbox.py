"""TD-0071 — E4 `touch_lockbox.py`, chế độ `--verify-seal` (H17) + TỪ CHỐI
chế độ chạm thật. Canh bởi L-Z13/L-Z14 (đã kiểm ở mức hàm trong
`tests/lock/test_lz14_lockbox_seal_hash.py`); test này khoá đúng HÀNH VI
người vận hành thấy qua CLI, cùng phong cách `test_run_backtest_cache.py`
(TD-0018): chạy như tiến trình con, `cwd=REPO_ROOT`.

TD-0084 — sau khi niêm phong `lockbox_seal_1.json` thật (DR-D0PRE-07),
`lockbox/` KHÔNG còn rỗng, nhưng test này chạy TRONG container `tests`
(docker-compose), nơi `lockbox/data/` bị volume ẩn danh CHE (chỉ service
`lockbox` thấy dữ liệu thật — ARCHITECTURE.md 3.1). Vì vậy `--verify-seal`
ở ĐÂY phải BÁO LỆCH (MISSING) — đúng thiết kế cách ly, không phải lỗi.
PASS thật trên dữ liệu thật đã xác nhận thủ công qua service `lockbox`
(xem DR-D0PRE-07 mục 6); không lặp lại xác nhận đó trong bộ test chạy ở
service `tests` vì bản chất service này không nhìn thấy dữ liệu đó.

Test `--seal-initial` dùng `tmp_path` (không đụng seal thật của repo —
seal bất biến, không được ghi/xoá ngoài ý muốn khi chạy test).

Không dùng `tmp_path` làm `cwd` cho các test verify/từ-chối vì
`measurement_guard()` đọc `config/tool_d_config.yaml` theo đường dẫn
tương đối — cách ly khỏi repo thật sẽ làm guard tự crash trước khi chạm
tới code cần kiểm.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
E4 = REPO_ROOT / "entrypoints" / "touch_lockbox.py"
ACCESS_LOG = REPO_ROOT / "lockbox" / "lockbox_access.log"
SEAL_1 = REPO_ROOT / "lockbox" / "lockbox_seal_1.json"

sys.path.insert(0, str(REPO_ROOT / "entrypoints"))


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(E4), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


class TestVerifySealModeTrenLockboxThat:
    def test_seal_1_ton_tai_that(self) -> None:
        # TD-0084 — lockbox_seal_1.json đã niêm phong thật (DR-D0PRE-07).
        # Seal thêm là tín hiệu TỐT (nghiên cứu đã tiến) — cập nhật giả
        # định "0 seal" của trước TD-0084, không phải lỗi.
        assert SEAL_1.exists(), "lockbox_seal_1.json chưa có — TD-0084 chưa chạy hay bị xoá nhầm?"

    def test_trong_container_tests_du_lieu_bi_che_nen_verify_fail(self) -> None:
        # Test này chạy TRONG service `tests` — `lockbox/data/` bị volume
        # ẩn danh che (ARCHITECTURE.md 3.1), nên file OHLCV thật KHÔNG
        # nhìn thấy được từ đây dù seal đã khớp thật ở service `lockbox`
        # (xác nhận thủ công, DR-D0PRE-07 mục 6). --verify-seal PHẢI báo
        # lệch (MISSING) ở service này — đúng thiết kế cách ly, không
        # phải lỗi L-Z14. Nếu test này bất ngờ PASS, cơ chế che volume đã
        # hỏng — soát lại docker-compose.yml, không phải sửa test.
        result = _run("--verify-seal")
        from touch_lockbox import EXIT_LOCKBOX_VERIFY_FAILED

        assert result.returncode == EXIT_LOCKBOX_VERIFY_FAILED
        assert "MISSING" in result.stdout

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


class TestSealInitialTrenRepoThat:
    """`lockbox_seal_1.json` đã niêm phong thật (TD-0084) — `--seal-initial`
    chạy LẠI trên repo thật phải TỪ CHỐI (seal bất biến, spec dòng 3312),
    không được ghi đè. Đây chính là cách CLI này chỉ chạy đúng một lần
    trong đời repo."""

    def test_chay_lai_thi_tu_choi_khong_ghi_de(self) -> None:
        before = SEAL_1.read_text(encoding="utf-8")
        result = _run("--seal-initial")
        from touch_lockbox import EXIT_LOCKBOX_SEAL_FAILED

        assert result.returncode == EXIT_LOCKBOX_SEAL_FAILED
        assert SEAL_1.read_text(encoding="utf-8") == before

    def test_chay_lai_khong_ghi_so_truy_cap(self) -> None:
        _run("--seal-initial")
        assert not ACCESS_LOG.exists()


class TestSealInitialLogicCoLap:
    """Kiểm logic `_seal_initial()` cách ly khỏi repo thật bằng monkeypatch
    (không đụng `lockbox_seal_1.json` thật — seal bất biến)."""

    def _import(self):
        import touch_lockbox as e4

        return e4

    def test_thu_muc_du_lieu_khong_ton_tai_thi_that_bai(self, tmp_path, monkeypatch) -> None:
        e4 = self._import()
        monkeypatch.setattr(e4, "SEAL_1_PATH", tmp_path / "lockbox_seal_1.json")
        monkeypatch.setattr(e4, "LOCKBOX_FUTURES_DIR", tmp_path / "data" / "futures")
        assert e4._seal_initial() == e4.EXIT_LOCKBOX_SEAL_FAILED
        assert not (tmp_path / "lockbox_seal_1.json").exists()

    def test_thu_muc_rong_thi_that_bai(self, tmp_path, monkeypatch) -> None:
        e4 = self._import()
        futures_dir = tmp_path / "data" / "futures"
        futures_dir.mkdir(parents=True)
        monkeypatch.setattr(e4, "SEAL_1_PATH", tmp_path / "lockbox_seal_1.json")
        monkeypatch.setattr(e4, "LOCKBOX_FUTURES_DIR", futures_dir)
        assert e4._seal_initial() == e4.EXIT_LOCKBOX_SEAL_FAILED

    def test_co_du_lieu_thi_ghi_seal_hop_le(self, tmp_path, monkeypatch) -> None:
        e4 = self._import()
        futures_dir = tmp_path / "data" / "futures"
        futures_dir.mkdir(parents=True)
        (futures_dir / "BTC_USDT_USDT-1h-futures.feather").write_bytes(b"fake-ohlcv-bytes")
        (futures_dir / "BTC_USDT_USDT-1d-futures.feather").write_bytes(b"fake-ohlcv-bytes-2")
        seal_path = tmp_path / "lockbox_seal_1.json"
        monkeypatch.setattr(e4, "SEAL_1_PATH", seal_path)
        monkeypatch.setattr(e4, "LOCKBOX_FUTURES_DIR", futures_dir)

        assert e4._seal_initial() == 0
        assert seal_path.exists()

        from tool_d.lockbox.seal import verify_seal

        assert verify_seal(seal_path, futures_dir) == []

    def test_verify_voi_thu_muc_cha_futures_thi_bao_missing(self, tmp_path, monkeypatch) -> None:
        # TD-0084 — tái hiện đúng bug thật đã bắt: seal chỉ lưu tên file
        # (không có tiền tố thư mục), nên verify PHẢI trỏ đúng thư mục
        # `.../futures/` — trỏ vào thư mục CHA (kiểu `LOCKBOX_DATA_DIR` cũ)
        # khiến mọi file báo "MISSING" dù dữ liệu tồn tại nguyên vẹn.
        e4 = self._import()
        parent_dir = tmp_path / "data"
        futures_dir = parent_dir / "futures"
        futures_dir.mkdir(parents=True)
        (futures_dir / "BTC_USDT_USDT-1d-futures.feather").write_bytes(b"fake-ohlcv-bytes")
        seal_path = tmp_path / "lockbox_seal_1.json"
        monkeypatch.setattr(e4, "SEAL_1_PATH", seal_path)
        monkeypatch.setattr(e4, "LOCKBOX_FUTURES_DIR", futures_dir)
        assert e4._seal_initial() == 0

        from tool_d.lockbox.seal import verify_seal

        assert verify_seal(seal_path, futures_dir) == []  # đúng thư mục -> PASS
        errors = verify_seal(seal_path, parent_dir)  # SAI (thư mục cha) -> phải bắt được
        assert errors and all("MISSING" in e for e in errors)

    def test_da_co_seal_thi_tu_choi_ghi_de(self, tmp_path, monkeypatch) -> None:
        e4 = self._import()
        seal_path = tmp_path / "lockbox_seal_1.json"
        seal_path.write_text('{"segment": 1}', encoding="utf-8")
        monkeypatch.setattr(e4, "SEAL_1_PATH", seal_path)
        assert e4._seal_initial() == e4.EXIT_LOCKBOX_SEAL_FAILED
        assert seal_path.read_text(encoding="utf-8") == '{"segment": 1}'
