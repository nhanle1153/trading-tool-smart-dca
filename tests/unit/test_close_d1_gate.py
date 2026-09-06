"""TD-0110 — `close_d1_gate()` (E6 `--close-d1-gate`): ghi
`runtime_state.json.d1_complete` từ suite pytest THẬT chạy trong chính
lần gọi này (MT-10 — nhãn `do-duoc` đúng nghĩa, không phải chuỗi gõ tay).

`pytest_cmd` được thay bằng lệnh giả nhanh trong các test dưới đây —
không chạy lại toàn bộ suite thật bên trong chính suite đang chạy nó
(sẽ tự đệ quy chậm). `is_d0_pre_complete` được monkeypatch trực tiếp
trên module (không `chdir`) — `chdir` sẽ làm hỏng các đường dẫn tương
đối mặc định khác (`config/tool_d_config.yaml`...) mà test không định
đụng tới.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "entrypoints"))

import trial_ledger_audit  # noqa: E402
from trial_ledger_audit import (  # noqa: E402
    EXIT_GATE_ALREADY_CLOSED,
    EXIT_GATE_AUDIT_DIRTY,
    close_d1_gate,
)

PASS_CMD = [sys.executable, "-c", "print('2 passed in 0.01s')"]
FAIL_CMD = [sys.executable, "-c", "print('1 failed, 1 passed in 0.01s'); import sys; sys.exit(1)"]


def _empty_ledger_kwargs(tmp_path: Path) -> dict:
    reg = tmp_path / "reg.jsonl"
    reg.touch()
    iq = tmp_path / "iq.jsonl"
    iq.touch()
    return {"registry_path": reg, "idea_queue_path": iq}


class TestTuChoiKhiD0PreChuaDong:
    def test_thieu_d0_pre_complete_thi_tu_choi(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(trial_ledger_audit, "is_d0_pre_complete", lambda: False)
        exit_code, text = close_d1_gate(
            runtime_state_path=tmp_path / "rs.json",
            pytest_cmd=PASS_CMD,
            **_empty_ledger_kwargs(tmp_path),
        )
        assert exit_code == EXIT_GATE_AUDIT_DIRTY
        assert "D0-PRE chưa đóng" in text
        assert not (tmp_path / "rs.json").exists()


class TestDongCongThanhCong:
    def test_suite_sach_thi_ghi_file_va_exit_0(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(trial_ledger_audit, "is_d0_pre_complete", lambda: True)
        state_path = tmp_path / "runtime_state.json"
        state_path.write_text(json.dumps({"d0_pre_complete": True}), encoding="utf-8")

        exit_code, text = close_d1_gate(
            runtime_state_path=state_path,
            pytest_cmd=PASS_CMD,
            **_empty_ledger_kwargs(tmp_path),
        )
        assert exit_code == 0
        data = json.loads(state_path.read_text(encoding="utf-8"))
        assert data["d1_complete"] is True
        assert len(data["d1_git_sha"]) == 40
        assert data["d0_pre_complete"] is True  # không phá khoá D0-PRE đã có

    def test_evidence_gan_dung_nhan_nguon_do_duoc(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(trial_ledger_audit, "is_d0_pre_complete", lambda: True)
        state_path = tmp_path / "runtime_state.json"
        state_path.write_text(json.dumps({"d0_pre_complete": True}), encoding="utf-8")

        close_d1_gate(runtime_state_path=state_path, pytest_cmd=PASS_CMD, **_empty_ledger_kwargs(tmp_path))
        data = json.loads(state_path.read_text(encoding="utf-8"))
        ev = data["d1_evidence"]
        assert ev["full_suite"]["nguon"] == "do-duoc"
        assert "2 passed" in ev["full_suite"]["noi_dung"]
        assert ev["trial_ledger_audit"]["nguon"] == "do-duoc"


class TestTuChoiTrenSuiteBan:
    def test_suite_that_bai_thi_khong_ghi_file(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(trial_ledger_audit, "is_d0_pre_complete", lambda: True)
        state_path = tmp_path / "runtime_state.json"
        state_path.write_text(json.dumps({"d0_pre_complete": True}), encoding="utf-8")
        before = state_path.read_text(encoding="utf-8")

        exit_code, text = close_d1_gate(
            runtime_state_path=state_path,
            pytest_cmd=FAIL_CMD,
            **_empty_ledger_kwargs(tmp_path),
        )
        assert exit_code == EXIT_GATE_AUDIT_DIRTY
        assert "suite pytest CHƯA sạch" in text
        assert state_path.read_text(encoding="utf-8") == before  # không ghi đè d0_pre_complete có sẵn


class TestTuChoiGhiLai:
    def test_da_dong_roi_thi_tu_choi_khong_ghi_de(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(trial_ledger_audit, "is_d0_pre_complete", lambda: True)
        state_path = tmp_path / "runtime_state.json"
        state_path.write_text(
            json.dumps({"d0_pre_complete": True, "d1_complete": True}), encoding="utf-8"
        )
        before = state_path.read_text(encoding="utf-8")

        exit_code, text = close_d1_gate(
            runtime_state_path=state_path, pytest_cmd=PASS_CMD, **_empty_ledger_kwargs(tmp_path)
        )
        assert exit_code == EXIT_GATE_ALREADY_CLOSED
        assert state_path.read_text(encoding="utf-8") == before


class TestMacDinhLaPytestThat:
    def test_khong_truyen_pytest_cmd_thi_mac_dinh_goi_pytest_that(self) -> None:
        # Không mock gì — xác nhận mặc định THẬT là `python -m pytest -q`,
        # không phải một lệnh giả nào đó chỉ tồn tại trong test.
        import inspect

        src = inspect.getsource(close_d1_gate)
        assert 'pytest_cmd or [sys.executable, "-m", "pytest", "-q"]' in src
