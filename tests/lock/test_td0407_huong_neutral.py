"""TD-0407 — hướng `NEUTRAL` trong sổ trial (`DR-D0-IQ0003` §14, `MT-82`).

Rổ trung tính giữ CẢ HAI chân; ghi `LONG` là ghi sai mãi mãi vào sổ append-only. Nhưng một nhãn hướng mới mà ai cũng
khai được thì chỉ là lời khai: cửa ghi nhận `NEUTRAL` CHỈ cho slot `IQ-xxxx` có đúng một DR thiết kế đã commit khai lớp
`CAN_RO_THEO_LICH` (khối `DR-CAN-RO-01:LOP`). Mọi ca từ chối kiểm luôn sổ đứng yên.

Repo git THẬT trong `tmp_path` (khuôn `test_td0398`).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from tool_d.gates.exit_reason_thiet_ke import (
    LOP_CAN_RO,
    ExitReasonThietKeError,
    duong_dan_artifact,
    kiem_huong_neutral,
)
from tool_d.ledger.registry import HuongNeutralError, TrialLedger

SLOT = "IQ-0042"
PROVENANCE = {
    "params_source": "yaml",
    "params_effective": {},
    "git_sha": "a" * 40,
    "reproducible_from_sha": True,
    "data_hashes": {"X_USDT-1h.feather": "b" * 64},
    "cache_mode": "none",
    "guard_passed": True,
}


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    (repo / "README").write_text("x", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "seed")
    return repo


def _ghi(repo: Path, rel: str, noi_dung: str, *, commit: bool = True) -> None:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(noi_dung, encoding="utf-8")
    if commit:
        _git(repo, "add", rel)
        _git(repo, "commit", "-qm", rel)


def _dr(slot: str = SLOT) -> str:
    return (
        f"# DR thiết kế {slot}\n\nTheo `DR-CAN-RO-01`.\n\n<!-- DR-CAN-RO-01:LOP:BEGIN -->\n```json\n"
        + json.dumps({"slot": slot, "lop": LOP_CAN_RO})
        + "\n```\n<!-- DR-CAN-RO-01:LOP:END -->\n"
    )


class TestHamThuan:
    def test_dr_lop_ro_da_commit_thi_qua(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        _ghi(repo, "docs/decisions/DR-D0-X.md", _dr())
        kiem_huong_neutral(SLOT, repo_dir=repo)

    @pytest.mark.parametrize("slot", ["A-01", "B2", "IQ-42", "TD-0335-TEST"])
    def test_slot_khong_phai_ung_vien_thi_tu_choi(self, tmp_path: Path, slot: str) -> None:
        with pytest.raises(ExitReasonThietKeError, match="chỉ cho slot ứng viên"):
            kiem_huong_neutral(slot, repo_dir=_repo(tmp_path))

    def test_khong_co_dr_lop_ro_thi_tu_choi(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        _ghi(repo, "docs/decisions/DR-D0-X.md", _dr(slot="IQ-0099"))
        with pytest.raises(ExitReasonThietKeError, match="thấy 0"):
            kiem_huong_neutral(SLOT, repo_dir=repo)

    def test_hai_dr_cung_slot_thi_tu_choi(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        _ghi(repo, "docs/decisions/DR-A.md", _dr())
        _ghi(repo, "docs/decisions/DR-B.md", _dr())
        with pytest.raises(ExitReasonThietKeError, match="thấy 2"):
            kiem_huong_neutral(SLOT, repo_dir=repo)

    def test_dr_chua_commit_thi_tu_choi(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        _ghi(repo, "docs/decisions/DR-A.md", _dr(), commit=False)
        with pytest.raises(ExitReasonThietKeError, match="CHƯA COMMIT"):
            kiem_huong_neutral(SLOT, repo_dir=repo)

    def test_dr_that_cua_iq0003_qua(self) -> None:
        """DR thiết kế thật (`DR-D0-IQ0003`) — repo làm việc."""
        kiem_huong_neutral("IQ-0003", repo_dir=Path("."))


class TestCuaReserve:
    @staticmethod
    def _so(tmp_path: Path, *, co_dr: bool) -> tuple[TrialLedger, Path]:
        repo = _repo(tmp_path)
        if co_dr:
            _ghi(repo, "docs/decisions/DR-D0-X.md", _dr())
        # Cửa thiết kế TD-0375 đứng sau: hiện vật EXPLORE trong dải để đi tới cuối reserve().
        _ghi(repo, duong_dan_artifact(SLOT).as_posix(), json.dumps(
            {"lenh_that": {"A": {"so_lenh": 100, "exit_reason": {"TIME_STOP": 10, "stop_loss": 90}}}}
        ))
        duong = tmp_path / "reg" / "trial_registry.jsonl"
        return TrialLedger(duong, repo_dir=repo), duong

    @staticmethod
    def _reserve(so: TrialLedger, **doi) -> str:
        tham_so = dict(
            n_dang_ky=114, so_lenh_da_dong=0, tool_id="D", budget_line="B3", hypothesis_slot=SLOT,
            direction="NEUTRAL", dataset="CALIB", param_under_test="cau_hinh", param_value="v1",
            params_frozen_hash="f" * 64, config_hash="c" * 64, code_commit="a" * 40,
            provenance=PROVENANCE, contribution=1,
        )
        tham_so.update(doi)
        return so.reserve(**tham_so)

    def test_neutral_co_lop_ro_thi_ghi_duoc_va_so_mang_neutral(self, tmp_path: Path) -> None:
        so, duong = self._so(tmp_path, co_dr=True)
        self._reserve(so)
        dong = [json.loads(d) for d in duong.read_text(encoding="utf-8").splitlines()]
        assert len(dong) == 1 and dong[0]["direction"] == "NEUTRAL"

    def test_neutral_khong_lop_ro_thi_tu_choi_so_dung_yen(self, tmp_path: Path) -> None:
        so, duong = self._so(tmp_path, co_dr=False)
        with pytest.raises(HuongNeutralError, match="TỪ CHỐI"):
            self._reserve(so)
        assert duong.read_text(encoding="utf-8").strip() == ""

    def test_neutral_slot_za_thi_tu_choi(self, tmp_path: Path) -> None:
        so, duong = self._so(tmp_path, co_dr=True)
        with pytest.raises(HuongNeutralError, match="chỉ cho slot ứng viên"):
            self._reserve(so, hypothesis_slot="A-01")
        assert duong.read_text(encoding="utf-8").strip() == ""

    def test_long_khong_bi_cua_neutral_dong_toi(self, tmp_path: Path) -> None:
        so, duong = self._so(tmp_path, co_dr=False)
        self._reserve(so, direction="LONG")
        assert len(duong.read_text(encoding="utf-8").splitlines()) == 1


class TestE1NhanNeutral:
    def test_argparse_e1_co_neutral(self) -> None:
        van_ban = Path("entrypoints/run_backtest.py").read_text(encoding="utf-8")
        assert 'choices=("LONG", "SHORT", "NEUTRAL")' in van_ban
