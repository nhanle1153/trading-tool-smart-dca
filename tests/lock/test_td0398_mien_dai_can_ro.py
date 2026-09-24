"""TD-0398 — `DR-CAN-RO-01`: dải `TIME_STOP` của cổng thiết kế (`TD-0375`) không áp cho lớp `CAN_RO_THEO_LICH`.

Lối miễn phải HẸP (DR §3): khai lớp trong một DR đã commit có khối máy đọc đúng slot · mọi nhãn thoát thuộc tập của
lớp · có ít nhất một lệnh `CAN_RO`. Thiếu điều 2 ⇒ áp dải như cũ (không được miễn). Thiếu điều 1 hoặc 3 ⇒ từ chối.
Không khai lớp ⇒ hành vi `TD-0375` không đổi (mọi ca của `test_td0375_*` giữ nguyên khẳng định).

Repo git THẬT trong `tmp_path` — "đã commit" chính là thứ đang được kiểm (khuôn `test_td0375`).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from tool_d.ablation.chi_so_export import EXIT_CAN_RO
from tool_d.gates.exit_reason_thiet_ke import (
    LOP_CAN_RO,
    NHAN_THOAT_CAN_RO,
    ExitReasonThietKeError,
    duong_dan_artifact,
    kiem_exit_reason_thiet_ke,
)
from tool_d.ledger.registry import ThietKeChuaKiemError, TrialLedger

SLOT = "IQ-0042"
DR = "docs/decisions/DR-D0-IQ0042.md"
PROVENANCE = {
    "params_source": "yaml",
    "params_effective": {"zss_threshold": 0.5},
    "git_sha": "a" * 40,
    "reproducible_from_sha": True,
    "data_hashes": {"BTC_USDT-1h.feather": "b" * 64},
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


def _khoi(slot: str = SLOT, lop: str = LOP_CAN_RO) -> str:
    return (
        "<!-- DR-CAN-RO-01:LOP:BEGIN -->\n```json\n"
        + json.dumps({"slot": slot, "lop": lop})
        + "\n```\n<!-- DR-CAN-RO-01:LOP:END -->\n"
    )


def _dr(khoi: str | None = None) -> str:
    return f"# DR thiết kế {SLOT}\n\nTheo `DR-CAN-RO-01`.\n\n" + (_khoi() if khoi is None else khoi)


def _hien_vat(exit_reason: dict[str, int], **them) -> dict:
    kq = {
        "lenh_that": {"RO": {"so_lenh": sum(exit_reason.values()), "exit_reason": exit_reason}},
        "lop_chien_luoc": LOP_CAN_RO,
        "dr_thiet_ke": DR,
    }
    kq.update(them)
    return kq


RO_HOP_LE = {EXIT_CAN_RO: 90, "stop_loss": 7, "force_exit": 3}


def _dung(tmp_path: Path, kq: dict, *, dr: str | None = None, commit_dr: bool = True) -> Path:
    repo = _repo(tmp_path)
    _ghi(repo, DR, _dr() if dr is None else dr, commit=commit_dr)
    _ghi(repo, duong_dan_artifact(SLOT).as_posix(), json.dumps(kq))
    return repo


class TestMienDai:
    def test_ro_khai_dung_thi_qua_du_time_stop_bang_0(self, tmp_path: Path) -> None:
        """Ca gốc của `MT-81`: TIME_STOP 0% — không có lớp thì cổng chặn, có lớp hợp lệ thì qua."""
        kiem_exit_reason_thiet_ke(SLOT, repo_dir=_dung(tmp_path, _hien_vat(RO_HOP_LE)))

    def test_khong_khai_lop_thi_hanh_vi_td0375_giu_nguyen(self, tmp_path: Path) -> None:
        kq = _hien_vat(RO_HOP_LE)
        del kq["lop_chien_luoc"], kq["dr_thiet_ke"]
        with pytest.raises(ExitReasonThietKeError, match="ngoài dải"):
            kiem_exit_reason_thiet_ke(SLOT, repo_dir=_dung(tmp_path, kq))

    def test_tap_nhan_dung_theo_dr(self) -> None:
        assert NHAN_THOAT_CAN_RO == {"CAN_RO", "stop_loss", "stoploss_on_exchange", "force_exit"}


class TestDieu2NhanNgoaiLop:
    @pytest.mark.parametrize("nhan_la", ["roi", "TIME_STOP", "custom_exit", "liquidation", "TP2_TRAIL"])
    def test_nhan_ngoai_lop_thi_ap_dai_nhu_cu(self, tmp_path: Path, nhan_la: str) -> None:
        """Chiến lược có cửa thoát theo giá khai lớp rổ ⇒ KHÔNG được miễn. Ở đây TIME_STOP ngoài dải ⇒ chặn."""
        er = dict(RO_HOP_LE)
        er[nhan_la] = er.get(nhan_la, 0) + 1
        with pytest.raises(ExitReasonThietKeError, match="ngoài dải"):
            kiem_exit_reason_thiet_ke(SLOT, repo_dir=_dung(tmp_path, _hien_vat(er)))

    def test_nhan_ngoai_lop_ma_time_stop_trong_dai_thi_qua_bang_dai(self, tmp_path: Path) -> None:
        """Không được miễn KHÔNG có nghĩa là bị chặn: dải vẫn là phép kiểm hợp lệ cho chiến lược đó."""
        er = {EXIT_CAN_RO: 80, "TIME_STOP": 10, "stop_loss": 10}
        kiem_exit_reason_thiet_ke(SLOT, repo_dir=_dung(tmp_path, _hien_vat(er)))


class TestDieu3CoCanRoThat:
    def test_khong_co_lenh_can_ro_thi_tu_choi(self, tmp_path: Path) -> None:
        with pytest.raises(ExitReasonThietKeError, match=f"0 lệnh `{EXIT_CAN_RO}`"):
            kiem_exit_reason_thiet_ke(SLOT, repo_dir=_dung(tmp_path, _hien_vat({"stop_loss": 5, "force_exit": 5})))


class TestDieu1KhaiLop:
    def test_lop_la_thi_tu_choi(self, tmp_path: Path) -> None:
        with pytest.raises(ExitReasonThietKeError, match="chỉ nhận"):
            kiem_exit_reason_thiet_ke(SLOT, repo_dir=_dung(tmp_path, _hien_vat(RO_HOP_LE, lop_chien_luoc="RO_KHAC")))

    def test_thieu_dr_thiet_ke_thi_tu_choi(self, tmp_path: Path) -> None:
        kq = _hien_vat(RO_HOP_LE)
        del kq["dr_thiet_ke"]
        with pytest.raises(ExitReasonThietKeError, match="đường dẫn"):
            kiem_exit_reason_thiet_ke(SLOT, repo_dir=_dung(tmp_path, kq))

    def test_dr_chua_commit_thi_tu_choi(self, tmp_path: Path) -> None:
        with pytest.raises(ExitReasonThietKeError, match="DR thiết kế"):
            kiem_exit_reason_thiet_ke(SLOT, repo_dir=_dung(tmp_path, _hien_vat(RO_HOP_LE), commit_dr=False))

    @pytest.mark.parametrize("duong", ["docs/DR-x.md", "/abs/DR.md", "docs/decisions/DR-x.txt", "docs/decisions/a/DR.md"])
    def test_dr_sai_dia_chi_thi_tu_choi(self, tmp_path: Path, duong: str) -> None:
        with pytest.raises(ExitReasonThietKeError, match="phải trỏ tới"):
            kiem_exit_reason_thiet_ke(SLOT, repo_dir=_dung(tmp_path, _hien_vat(RO_HOP_LE, dr_thiet_ke=duong)))

    def test_dr_khong_nhac_dr_can_ro_thi_tu_choi(self, tmp_path: Path) -> None:
        dr = f"# DR {SLOT}\n\n" + _khoi().replace("DR-CAN-RO-01", "DR-KHAC-01")
        with pytest.raises(ExitReasonThietKeError, match="không nhắc đích danh"):
            kiem_exit_reason_thiet_ke(SLOT, repo_dir=_dung(tmp_path, _hien_vat(RO_HOP_LE), dr=dr))

    @pytest.mark.parametrize(
        "khoi",
        [
            "",  # không có khối
            _khoi() + _khoi(),  # hai khối
            _khoi(slot="IQ-0099"),  # slot lệch
            _khoi(lop="RO_KHAC"),  # lớp lệch
            "<!-- DR-CAN-RO-01:LOP:BEGIN -->\n{hong\n<!-- DR-CAN-RO-01:LOP:END -->\n",  # JSON hỏng
        ],
    )
    def test_khoi_may_doc_hong_thi_tu_choi(self, tmp_path: Path, khoi: str) -> None:
        with pytest.raises(ExitReasonThietKeError, match="khối"):
            kiem_exit_reason_thiet_ke(SLOT, repo_dir=_dung(tmp_path, _hien_vat(RO_HOP_LE), dr=_dr(khoi)))


class TestCuaReserve:
    """Cửa ở `TrialLedger.reserve()` — mọi đường ghi sổ đều đi qua."""

    def _reserve(self, so: TrialLedger) -> str:
        return so.reserve(
            n_dang_ky=114, so_lenh_da_dong=0, tool_id="D", budget_line="B3", hypothesis_slot=SLOT,
            direction="LONG", dataset="CALIB", param_under_test="zss_threshold", param_value=0.5,
            params_frozen_hash="f" * 64, config_hash="c" * 64, code_commit="a" * 40,
            provenance=PROVENANCE, contribution=1,
        )

    def test_ro_hop_le_thi_ghi_duoc(self, tmp_path: Path) -> None:
        repo = _dung(tmp_path, _hien_vat(RO_HOP_LE))
        duong = tmp_path / "trial_registry.jsonl"
        self._reserve(TrialLedger(duong, repo_dir=repo))
        assert len(duong.read_text(encoding="utf-8").splitlines()) == 1

    def test_ro_thieu_can_ro_bi_tu_choi_so_dung_yen(self, tmp_path: Path) -> None:
        repo = _dung(tmp_path, _hien_vat({"stop_loss": 5}))
        duong = tmp_path / "trial_registry.jsonl"
        with pytest.raises(ThietKeChuaKiemError):
            self._reserve(TrialLedger(duong, repo_dir=repo))
        assert not duong.exists() or duong.read_text(encoding="utf-8").strip() == ""
