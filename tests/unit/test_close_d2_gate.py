"""TD-0117 — `close_d2_gate()` (E6 `--close-d2-gate`): ghi
`runtime_state.json.d2_complete` từ pytest THẬT chạy trong chính lần
gọi này (MT-10 — nhãn `do-duoc` đúng nghĩa, không phải chuỗi gõ tay).

Điểm khác cổng D1 mà bộ test này tồn tại để canh: cổng D2 chạy RIÊNG
file test khoá L-Z49/L-Z50 và đòi số ca PASS >= 1. Suite tổng xanh
KHÔNG chứng minh file đó còn tồn tại — xoá hẳn đi thì suite vẫn xanh.
Ca `test_lz_exit_0_nhung_0_ca_thi_tu_choi` là ca quan trọng nhất ở đây:
nó dựng đúng tình huống "PASS rỗng" của TD-0084.

`pytest_cmd`/`pytest_lz_cmd` được thay bằng lệnh giả nhanh — không chạy
lại toàn bộ suite thật bên trong chính suite đang chạy nó.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "entrypoints"))

import trial_ledger_audit  # noqa: E402
from trial_ledger_audit import (  # noqa: E402
    DUONG_DAN_TEST_LZ49_LZ50,
    EXIT_GATE_ALREADY_CLOSED,
    EXIT_GATE_AUDIT_DIRTY,
    close_d2_gate,
)

PASS_CMD = [sys.executable, "-c", "print('700 passed in 60.0s')"]
FAIL_CMD = [sys.executable, "-c", "print('1 failed, 699 passed'); import sys; sys.exit(1)"]
LZ_PASS_CMD = [sys.executable, "-c", "print('5 passed in 18.0s')"]
LZ_FAIL_CMD = [sys.executable, "-c", "print('2 failed, 3 passed'); import sys; sys.exit(1)"]
# Exit 0 nhưng KHÔNG ca nào chạy — đúng hình dạng của việc file test bị
# xoá/đổi tên: `pytest -q <file không có>` với `--co` rỗng vẫn có thể
# trả 0 tuỳ cấu hình, và dòng tổng kết không có chữ "passed" nào.
LZ_RONG_CMD = [sys.executable, "-c", "print('no tests ran in 0.01s')"]


def _empty_ledger_kwargs(tmp_path: Path) -> dict:
    reg = tmp_path / "reg.jsonl"
    reg.touch()
    iq = tmp_path / "iq.jsonl"
    iq.touch()
    return {"registry_path": reg, "idea_queue_path": iq}


def _state(tmp_path: Path, **khoa) -> Path:
    p = tmp_path / "runtime_state.json"
    p.write_text(json.dumps({"d0_pre_complete": True, **khoa}), encoding="utf-8")
    return p


def _goi(state_path: Path, tmp_path: Path, *, lz_cmd=LZ_PASS_CMD, suite_cmd=PASS_CMD):
    return close_d2_gate(
        runtime_state_path=state_path,
        pytest_cmd=suite_cmd,
        pytest_lz_cmd=lz_cmd,
        **_empty_ledger_kwargs(tmp_path),
    )


class TestThuTuCong:
    def test_d0_pre_chua_dong_thi_tu_choi(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(trial_ledger_audit, "is_d0_pre_complete", lambda: False)
        exit_code, text = _goi(_state(tmp_path, d1_complete=True), tmp_path)
        assert exit_code == EXIT_GATE_AUDIT_DIRTY
        assert "D0-PRE chưa đóng" in text

    def test_d1_chua_dong_thi_tu_choi(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(trial_ledger_audit, "is_d0_pre_complete", lambda: True)
        state_path = _state(tmp_path)  # không có d1_complete
        before = state_path.read_text(encoding="utf-8")
        exit_code, text = _goi(state_path, tmp_path)
        assert exit_code == EXIT_GATE_AUDIT_DIRTY
        assert "d1_complete" in text
        assert state_path.read_text(encoding="utf-8") == before


class TestDongCongThanhCong:
    def test_ghi_du_khoa_va_exit_0(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(trial_ledger_audit, "is_d0_pre_complete", lambda: True)
        state_path = _state(tmp_path, d1_complete=True)
        exit_code, _ = _goi(state_path, tmp_path)
        assert exit_code == 0
        data = json.loads(state_path.read_text(encoding="utf-8"))
        assert data["d2_complete"] is True
        assert len(data["d2_git_sha"]) == 40
        # không phá khoá của các cổng trước
        assert data["d0_pre_complete"] is True and data["d1_complete"] is True

    def test_evidence_co_muc_lz49_lz50_rieng_nhan_do_duoc(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.setattr(trial_ledger_audit, "is_d0_pre_complete", lambda: True)
        state_path = _state(tmp_path, d1_complete=True)
        _goi(state_path, tmp_path)
        ev = json.loads(state_path.read_text(encoding="utf-8"))["d2_evidence"]
        assert ev["full_suite"]["nguon"] == "do-duoc"
        assert ev["lz49_lz50"]["nguon"] == "do-duoc"
        assert DUONG_DAN_TEST_LZ49_LZ50 in ev["lz49_lz50"]["noi_dung"]
        assert "5 passed" in ev["lz49_lz50"]["noi_dung"]
        assert ev["trial_ledger_audit"]["nguon"] == "do-duoc"

    def test_ghi_ro_D2b_D2c_D4_la_HOAN_khong_phai_da_qua(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # Cổng đóng KHÔNG được ngầm hiểu là cả D2 đã verify xong — ba
        # mục Testnet/Live-only phải nằm trong file dưới nhãn nguoi-khai.
        monkeypatch.setattr(trial_ledger_audit, "is_d0_pre_complete", lambda: True)
        state_path = _state(tmp_path, d1_complete=True)
        _goi(state_path, tmp_path)
        hoan = json.loads(state_path.read_text(encoding="utf-8"))["d2_hoan_lai"]
        assert hoan["nguon"] == "nguoi-khai"
        assert "D2b" in hoan["noi_dung"] and "D2c" in hoan["noi_dung"] and "D4" in hoan["noi_dung"]


class TestTuChoiKhiBangChungKhongDU:
    def test_suite_that_bai_thi_khong_ghi(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(trial_ledger_audit, "is_d0_pre_complete", lambda: True)
        state_path = _state(tmp_path, d1_complete=True)
        before = state_path.read_text(encoding="utf-8")
        exit_code, text = _goi(state_path, tmp_path, suite_cmd=FAIL_CMD)
        assert exit_code == EXIT_GATE_AUDIT_DIRTY
        assert "suite pytest CHƯA sạch" in text
        assert state_path.read_text(encoding="utf-8") == before

    def test_lz_that_bai_thi_khong_ghi(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(trial_ledger_audit, "is_d0_pre_complete", lambda: True)
        state_path = _state(tmp_path, d1_complete=True)
        before = state_path.read_text(encoding="utf-8")
        exit_code, text = _goi(state_path, tmp_path, lz_cmd=LZ_FAIL_CMD)
        assert exit_code == EXIT_GATE_AUDIT_DIRTY
        assert "L-Z49/L-Z50 CHƯA xanh" in text
        assert state_path.read_text(encoding="utf-8") == before

    def test_lz_exit_0_nhung_0_ca_thi_tu_choi(self, tmp_path: Path, monkeypatch) -> None:
        """🔴 Ca cốt lõi — bẫy PASS RỖNG của TD-0084.

        Suite tổng xanh, lệnh L-Z49/L-Z50 exit 0, nhưng KHÔNG ca nào
        chạy (file bị xoá/đổi tên/lọc hết). Nếu cổng chỉ nhìn exit code
        thì nó đóng ngon lành mà không có một phép kiểm D2 nào đứng sau.
        """
        monkeypatch.setattr(trial_ledger_audit, "is_d0_pre_complete", lambda: True)
        state_path = _state(tmp_path, d1_complete=True)
        before = state_path.read_text(encoding="utf-8")
        exit_code, text = _goi(state_path, tmp_path, lz_cmd=LZ_RONG_CMD)
        assert exit_code == EXIT_GATE_AUDIT_DIRTY
        assert "PASS RỖNG" in text
        assert state_path.read_text(encoding="utf-8") == before

    def test_da_dong_roi_thi_tu_choi_ghi_de(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(trial_ledger_audit, "is_d0_pre_complete", lambda: True)
        state_path = _state(tmp_path, d1_complete=True, d2_complete=True)
        before = state_path.read_text(encoding="utf-8")
        exit_code, _ = _goi(state_path, tmp_path)
        assert exit_code == EXIT_GATE_ALREADY_CLOSED
        assert state_path.read_text(encoding="utf-8") == before


class TestMacDinhLaPytestThat:
    def test_khong_truyen_cmd_thi_mac_dinh_chay_pytest_that(self) -> None:
        # Xác nhận mặc định THẬT là pytest, và file L-Z49/L-Z50 mặc định
        # trỏ tới một file CÓ THẬT trên đĩa — hằng số trỏ sai đường dẫn
        # sẽ luôn cho "0 ca" và làm cổng không bao giờ đóng được.
        import inspect

        src = inspect.getsource(close_d2_gate)
        assert 'pytest_cmd or [sys.executable, "-m", "pytest", "-q"]' in src
        assert "DUONG_DAN_TEST_LZ49_LZ50" in src
        assert (REPO_ROOT / DUONG_DAN_TEST_LZ49_LZ50).is_file()


class TestDemCaPass:
    def test_doc_dung_so_ca(self) -> None:
        assert trial_ledger_audit._dem_ca_pass("5 passed in 18.0s") == 5
        assert trial_ledger_audit._dem_ca_pass("2 failed, 3 passed in 1s") == 3

    def test_khong_doc_duoc_thi_tra_0_khong_doan(self) -> None:
        assert trial_ledger_audit._dem_ca_pass("no tests ran") == 0
        assert trial_ledger_audit._dem_ca_pass("") == 0
