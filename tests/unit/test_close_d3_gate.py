"""TD-0147 — `close_d3_gate()` (E6 `--close-d3-gate`).

Cùng khuôn `test_close_d2_gate.py`, thêm hai điều riêng của D3:

1. **Mỗi file test cốt lõi chạy RIÊNG, không gộp một lượt.** Gộp lại thì
   một file bị xoá/lọc hết vẫn cho tổng `N passed > 0` nhờ hai file kia,
   và cổng vẫn đóng được trong khi một phép kiểm cốt lõi đã biến mất.
   `test_moi_file_chay_RIENG_khong_gop` khoá điều đó.
2. **`d3_han_che` phải nói rõ cổng D3 KHÔNG chứng nhận đã có kết quả
   walk-forward.** D3 dựng bộ điều phối; nó không sinh ra một con số WFO
   nào vì chưa có bộ chạy backtest thật. Đọc cổng thành "đã có số" là
   hiểu sai đúng thứ PHẦN 0d tồn tại để chặn.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "entrypoints"))

import trial_ledger_audit  # noqa: E402
from trial_ledger_audit import (  # noqa: E402
    DUONG_DAN_TEST_D3,
    EXIT_GATE_ALREADY_CLOSED,
    EXIT_GATE_AUDIT_DIRTY,
    close_d3_gate,
)

PASS_CMD = [sys.executable, "-c", "print('900 passed in 200.0s')"]
FAIL_CMD = [sys.executable, "-c", "print('1 failed, 899 passed'); import sys; sys.exit(1)"]
# `pytest_d3_cmd` được nối thêm đường dẫn file ở cuối, nên lệnh giả phải
# nuốt được một tham số thừa.
D3_PASS = [sys.executable, "-c", "import sys; print('14 passed in 16.0s')", "--"]
D3_FAIL = [sys.executable, "-c", "import sys; print('2 failed, 12 passed'); sys.exit(1)", "--"]
D3_RONG = [sys.executable, "-c", "import sys; print('no tests ran in 0.01s')", "--"]


@pytest.fixture(autouse=True)
def _cay_sach(monkeypatch):
    """Mặc định coi cây làm việc là SẠCH.

    Bắt buộc phải có: repo này thường có nhiều phiên cùng sửa một thư mục
    đĩa, nên cây thật gần như luôn bẩn. Không cố định giá trị này thì mọi
    ca đường-thành-công của file sẽ đỏ/xanh theo việc phiên khác có đang gõ
    dở hay không — tức bộ test đo môi trường chứ không đo code.

    Ca `test_cay_ban_thi_TU_CHOI_truoc_khi_chay_suite` tự ghi đè lại.
    """
    from tool_d.measurement.gitinfo import GitInfo

    monkeypatch.setattr(
        trial_ledger_audit, "get_git_info", lambda _: GitInfo(sha="a" * 40, is_clean=True)
    )


def _empty_ledger_kwargs(tmp_path: Path) -> dict:
    reg = tmp_path / "reg.jsonl"
    reg.touch()
    iq = tmp_path / "iq.jsonl"
    iq.touch()
    return {"registry_path": reg, "idea_queue_path": iq}


def _state(tmp_path: Path, **khoa) -> Path:
    p = tmp_path / "runtime_state.json"
    mac_dinh = {"d0_pre_complete": True, "d1_complete": True, "d2_complete": True}
    mac_dinh.update(khoa)
    p.write_text(json.dumps(mac_dinh), encoding="utf-8")
    return p


def _goi(state_path: Path, tmp_path: Path, *, d3_cmd=D3_PASS, suite_cmd=PASS_CMD):
    return close_d3_gate(
        runtime_state_path=state_path,
        pytest_cmd=suite_cmd,
        pytest_d3_cmd=d3_cmd,
        **_empty_ledger_kwargs(tmp_path),
    )


class TestThuTuCong:
    def test_d0_pre_chua_dong_thi_tu_choi(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(trial_ledger_audit, "is_d0_pre_complete", lambda: False)
        exit_code, text = _goi(_state(tmp_path), tmp_path)
        assert exit_code == EXIT_GATE_AUDIT_DIRTY and "D0-PRE chưa đóng" in text

    def test_d1_chua_dong_thi_tu_choi(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(trial_ledger_audit, "is_d0_pre_complete", lambda: True)
        sp = _state(tmp_path, d1_complete=False)
        before = sp.read_text(encoding="utf-8")
        exit_code, text = _goi(sp, tmp_path)
        assert exit_code == EXIT_GATE_AUDIT_DIRTY and "d1_complete" in text
        assert sp.read_text(encoding="utf-8") == before

    def test_d2_chua_dong_thi_tu_choi(self, tmp_path: Path, monkeypatch) -> None:
        """D3 không thể đứng trước D2."""
        monkeypatch.setattr(trial_ledger_audit, "is_d0_pre_complete", lambda: True)
        sp = _state(tmp_path, d2_complete=False)
        before = sp.read_text(encoding="utf-8")
        exit_code, text = _goi(sp, tmp_path)
        assert exit_code == EXIT_GATE_AUDIT_DIRTY and "d2_complete" in text
        assert sp.read_text(encoding="utf-8") == before


class TestCayLamViecPhaiSach:
    """🔴 Lỗ hổng phát hiện khi chạy đóng cổng D3 THẬT lần đầu (08/09/2026).

    Ba cổng trước ghi `git_sha` nhưng KHÔNG ghi cây có sạch không. Với 4
    phiên cùng sửa một thư mục đĩa (N12), cây bẩn nghĩa là `d3_git_sha` trỏ
    tới một commit KHÔNG chứa thứ vừa được kiểm — bằng chứng tự mâu thuẫn.

    Lần chạy thật đó có 8 ca đỏ thoáng qua vì suite chạy 6,5 phút đúng lúc
    phiên song song sửa dở `registry.py`. Cổng từ chối vì suite đỏ — nhưng
    nếu các sửa đổi kia tình cờ không làm đỏ test nào thì cổng ĐÃ ĐÓNG, với
    bằng chứng sai. Đó là lý do phải kiểm riêng, không dựa vào may.
    """

    def test_cay_ban_thi_TU_CHOI_truoc_khi_chay_suite(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        from tool_d.measurement.gitinfo import GitInfo

        monkeypatch.setattr(trial_ledger_audit, "is_d0_pre_complete", lambda: True)
        monkeypatch.setattr(
            trial_ledger_audit, "get_git_info", lambda _: GitInfo(sha="f" * 40, is_clean=False)
        )
        goi: list[list[str]] = []
        that = trial_ledger_audit.subprocess.run
        monkeypatch.setattr(
            trial_ledger_audit.subprocess,
            "run",
            lambda cmd, **kw: (goi.append(list(cmd)), that(cmd, **kw))[1],
        )
        sp = _state(tmp_path)
        before = sp.read_text(encoding="utf-8")

        exit_code, text = _goi(sp, tmp_path)
        assert exit_code == EXIT_GATE_AUDIT_DIRTY
        assert "CHƯA SẠCH" in text
        assert sp.read_text(encoding="utf-8") == before
        # Từ chối TRƯỚC khi tốn 4 phút chạy suite — không lượt pytest nào.
        assert [c for c in goi if "pytest" in " ".join(c)] == []

    def test_cay_sach_thi_ghi_co_d3_cay_sach(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(trial_ledger_audit, "is_d0_pre_complete", lambda: True)
        sp = _state(tmp_path)
        _goi(sp, tmp_path)
        assert json.loads(sp.read_text(encoding="utf-8"))["d3_cay_sach"] is True


class TestDongCongThanhCong:
    def test_ghi_du_khoa_va_exit_0(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(trial_ledger_audit, "is_d0_pre_complete", lambda: True)
        sp = _state(tmp_path)
        exit_code, _ = _goi(sp, tmp_path)
        assert exit_code == 0
        d = json.loads(sp.read_text(encoding="utf-8"))
        assert d["d3_complete"] is True and len(d["d3_git_sha"]) == 40
        # không phá khoá của ba cổng trước
        assert d["d0_pre_complete"] and d["d1_complete"] and d["d2_complete"]

    def test_evidence_nhan_do_duoc_va_liet_ke_du_ba_file(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.setattr(trial_ledger_audit, "is_d0_pre_complete", lambda: True)
        sp = _state(tmp_path)
        _goi(sp, tmp_path)
        ev = json.loads(sp.read_text(encoding="utf-8"))["d3_evidence"]
        assert ev["full_suite"]["nguon"] == "do-duoc"
        assert ev["test_khoa_d3"]["nguon"] == "do-duoc"
        for duong_dan in DUONG_DAN_TEST_D3:
            assert duong_dan in ev["test_khoa_d3"]["noi_dung"]
        assert ev["trial_ledger_audit"]["nguon"] == "do-duoc"

    def test_han_che_noi_ro_KHONG_phai_da_co_ket_qua_WFO(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """🔴 Cổng D3 chứng nhận BỘ ĐIỀU PHỐI đúng, không chứng nhận đã có
        số. Ba giới hạn phải nằm trong file, dưới nhãn `nguoi-khai`."""
        monkeypatch.setattr(trial_ledger_audit, "is_d0_pre_complete", lambda: True)
        sp = _state(tmp_path)
        _goi(sp, tmp_path)
        hc = json.loads(sp.read_text(encoding="utf-8"))["d3_han_che"]
        assert hc["nguon"] == "nguoi-khai"
        noi_dung = hc["noi_dung"]
        assert "KHÔNG chứng nhận đã có kết quả walk-forward" in noi_dung
        assert "GIẢ" in noi_dung and "D3.5" in noi_dung  # giới hạn 1
        assert "TIN LỜI KHAI" in noi_dung  # giới hạn 2
        assert "unreadable" in noi_dung and "D9" in noi_dung  # giới hạn 3


class TestTuChoiKhiBangChungKhongDU:
    def test_suite_that_bai_thi_khong_ghi(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(trial_ledger_audit, "is_d0_pre_complete", lambda: True)
        sp = _state(tmp_path)
        before = sp.read_text(encoding="utf-8")
        exit_code, text = _goi(sp, tmp_path, suite_cmd=FAIL_CMD)
        assert exit_code == EXIT_GATE_AUDIT_DIRTY and "suite pytest CHƯA sạch" in text
        assert sp.read_text(encoding="utf-8") == before

    def test_test_khoa_d3_that_bai_thi_khong_ghi(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(trial_ledger_audit, "is_d0_pre_complete", lambda: True)
        sp = _state(tmp_path)
        before = sp.read_text(encoding="utf-8")
        exit_code, text = _goi(sp, tmp_path, d3_cmd=D3_FAIL)
        assert exit_code == EXIT_GATE_AUDIT_DIRTY and "cốt lõi CHƯA xanh" in text
        assert sp.read_text(encoding="utf-8") == before

    def test_test_khoa_d3_exit_0_nhung_0_ca_thi_tu_choi(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Bẫy PASS RỖNG của TD-0084."""
        monkeypatch.setattr(trial_ledger_audit, "is_d0_pre_complete", lambda: True)
        sp = _state(tmp_path)
        before = sp.read_text(encoding="utf-8")
        exit_code, text = _goi(sp, tmp_path, d3_cmd=D3_RONG)
        assert exit_code == EXIT_GATE_AUDIT_DIRTY and "PASS RỖNG" in text
        assert sp.read_text(encoding="utf-8") == before

    def test_da_dong_roi_thi_tu_choi_ghi_de(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(trial_ledger_audit, "is_d0_pre_complete", lambda: True)
        sp = _state(tmp_path, d3_complete=True)
        before = sp.read_text(encoding="utf-8")
        exit_code, _ = _goi(sp, tmp_path)
        assert exit_code == EXIT_GATE_ALREADY_CLOSED
        assert sp.read_text(encoding="utf-8") == before


class TestMoiFileChayRieng:
    def test_moi_file_chay_RIENG_khong_gop(self, tmp_path: Path, monkeypatch) -> None:
        """🔴 Gộp ba file vào MỘT lượt pytest thì một file bị xoá/lọc hết
        vẫn cho tổng `N passed > 0` nhờ hai file kia — cổng vẫn đóng được
        trong khi một phép kiểm cốt lõi đã biến mất. Ca này đếm số lần
        `subprocess.run` để khoá điều đó."""
        monkeypatch.setattr(trial_ledger_audit, "is_d0_pre_complete", lambda: True)
        goi: list[list[str]] = []
        that = trial_ledger_audit.subprocess.run

        def _ghi_lai(cmd, **kw):
            goi.append(list(cmd))
            return that(cmd, **kw)

        monkeypatch.setattr(trial_ledger_audit.subprocess, "run", _ghi_lai)
        _goi(_state(tmp_path), tmp_path)

        # Chỉ đếm lượt CHẠY TEST — `get_git_info()` cũng gọi `subprocess.run`
        # (git rev-parse / git status) và không liên quan gì ở đây.
        chay_test = [c for c in goi if "git" not in c[0]]  # phòng khi git vẫn được gọi
        # 1 lượt suite + đúng 1 lượt cho MỖI file cốt lõi
        assert len(chay_test) == 1 + len(DUONG_DAN_TEST_D3), chay_test
        for duong_dan in DUONG_DAN_TEST_D3:
            assert sum(1 for c in chay_test if duong_dan in c) == 1

    def test_ba_file_cot_loi_deu_CO_THAT_tren_dia(self) -> None:
        """Hằng số trỏ sai đường dẫn sẽ luôn cho 0 ca và làm cổng không
        bao giờ đóng được — nhưng chỉ phát hiện lúc chạy thật. Khoá ở đây."""
        for duong_dan in DUONG_DAN_TEST_D3:
            assert (REPO_ROOT / duong_dan).is_file(), duong_dan

    def test_mac_dinh_la_pytest_that(self) -> None:
        import inspect

        src = inspect.getsource(close_d3_gate)
        assert 'pytest_cmd or [sys.executable, "-m", "pytest", "-q"]' in src
        assert "DUONG_DAN_TEST_D3" in src
