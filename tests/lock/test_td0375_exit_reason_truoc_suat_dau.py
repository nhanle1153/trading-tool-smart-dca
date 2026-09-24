"""TD-0375 — `DR-PHAN-QUYET-01` §4.2 bước 3 có máy: CHẶN CỨNG suất đầu tiên của ứng viên `IQ-xxxx`.

Trước việc này nghĩa vụ *"đếm `exit_reason` trên EXPLORE trước suất đầu tiên"* chỉ là chữ (DR §6, §8 điểm yếu 2).
Luật chặn đúng hình dạng `MT-72`: ZA LONG đo `TIME_STOP` 1/246 — DG8 là cửa chết, và cổng D0.9 loại nhầm một giả
thuyết vì THIẾT KẾ. Chủ dự án chốt 24/09/2026: chặn cứng, không chỉ cảnh báo.

Repo git THẬT trong `tmp_path` — không mock `git`, vì "đã commit" chính là thứ đang được kiểm (khuôn `test_lz56`).
Mỗi ca từ chối kiểm luôn **sổ không thêm dòng nào** (sổ append-only không lùi được).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from tool_d.gates.exit_reason_thiet_ke import (
    ExitReasonThietKeError,
    duong_dan_artifact,
    kiem_exit_reason_thiet_ke,
)
from tool_d.gates.thresholds import TIME_STOP_RATIO_BAND
from tool_d.ledger.registry import ThietKeChuaKiemError, TrialLedger

SLOT = "IQ-0042"
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


def _hien_vat(so_lenh: int, time_stop: int) -> dict:
    """Khuôn đầu ra `do_td0193_lenh_nam_explore.py` (khoá `lenh_that`)."""
    return {"lenh_that": {"A1": {
        "so_lenh": so_lenh,
        "exit_reason": {"TIME_STOP": time_stop, "trailing_stop_loss": so_lenh - time_stop},
    }}}


def _ghi(repo: Path, rel: str, noi_dung: str, *, commit: bool = True) -> None:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(noi_dung, encoding="utf-8")
    if commit:
        _git(repo, "add", rel)
        _git(repo, "commit", "-qm", rel)


def _ghi_hien_vat(repo: Path, kq: dict, *, slot: str = SLOT, commit: bool = True) -> None:
    _ghi(repo, duong_dan_artifact(slot).as_posix(), json.dumps(kq), commit=commit)


def _reserve(so: TrialLedger, **doi) -> str:
    tham_so = {
        "n_dang_ky": 114, "so_lenh_da_dong": 0, "tool_id": "D", "budget_line": "B3",
        "hypothesis_slot": SLOT, "direction": "LONG", "dataset": "CALIB",
        "param_under_test": "zss_threshold", "param_value": 0.5,
        "params_frozen_hash": "f" * 64, "config_hash": "c" * 64, "code_commit": "a" * 40,
        "provenance": PROVENANCE, "contribution": 1,
    }
    tham_so.update(doi)
    return so.reserve(**tham_so)


def _so(tmp_path: Path, repo: Path) -> tuple[TrialLedger, Path]:
    duong = tmp_path / "trial_registry.jsonl"
    return TrialLedger(duong, repo_dir=repo), duong


def _so_dong(duong: Path) -> int:
    return len([d for d in duong.read_text(encoding="utf-8").splitlines() if d.strip()])


class TestHamThuan:
    def test_trong_dai_thi_qua(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        _ghi_hien_vat(repo, _hien_vat(100, 10))
        kiem_exit_reason_thiet_ke(SLOT, repo_dir=repo)

    @pytest.mark.parametrize("time_stop", [0, 4, 26, 100])
    def test_ngoai_dai_ca_hai_bien_deu_chan(self, tmp_path: Path, time_stop: int) -> None:
        """Cả hai biên đều chặn (`DR-PHAN-QUYET-01` §4.2) — biên dưới KHÔNG thành chẩn đoán (§4.1 đã loại)."""
        repo = _repo(tmp_path)
        _ghi_hien_vat(repo, _hien_vat(100, time_stop))
        with pytest.raises(ExitReasonThietKeError, match="ngoài dải"):
            kiem_exit_reason_thiet_ke(SLOT, repo_dir=repo)

    def test_bien_dung_bang_nguong_la_trong_dai(self, tmp_path: Path) -> None:
        lo, hi = TIME_STOP_RATIO_BAND
        repo = _repo(tmp_path)
        _ghi_hien_vat(repo, {"lenh_that": {
            "lo": {"so_lenh": 100, "exit_reason": {"TIME_STOP": round(lo * 100), "x": 100 - round(lo * 100)}},
            "hi": {"so_lenh": 100, "exit_reason": {"TIME_STOP": round(hi * 100), "x": 100 - round(hi * 100)}},
        }})
        kiem_exit_reason_thiet_ke(SLOT, repo_dir=repo)

    def test_mot_arm_ngoai_dai_la_du_de_chan(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        kq = _hien_vat(100, 10)
        kq["lenh_that"]["A2"] = {"so_lenh": 246, "exit_reason": {"TIME_STOP": 1, "TP2_TRAIL": 245}}
        _ghi_hien_vat(repo, kq)
        with pytest.raises(ExitReasonThietKeError, match="A2"):
            kiem_exit_reason_thiet_ke(SLOT, repo_dir=repo)

    def test_thieu_hien_vat_thi_chan(self, tmp_path: Path) -> None:
        with pytest.raises(ExitReasonThietKeError, match="KHÔNG TỒN TẠI"):
            kiem_exit_reason_thiet_ke(SLOT, repo_dir=_repo(tmp_path))

    def test_hien_vat_chua_commit_thi_chan(self, tmp_path: Path) -> None:
        """`DR-PHAN-QUYET-01` §2.3: file ngoài lịch sử không tái lập được (bài học `runs/D-0015`)."""
        repo = _repo(tmp_path)
        _ghi_hien_vat(repo, _hien_vat(100, 10), commit=False)
        with pytest.raises(ExitReasonThietKeError, match="CHƯA COMMIT"):
            kiem_exit_reason_thiet_ke(SLOT, repo_dir=repo)

    def test_hien_vat_sua_sau_commit_thi_chan(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        _ghi_hien_vat(repo, _hien_vat(100, 0))
        _ghi_hien_vat(repo, _hien_vat(100, 10), commit=False)  # đổi số trên đĩa cho "đẹp"
        with pytest.raises(ExitReasonThietKeError, match="ĐÃ SỬA SAU KHI COMMIT"):
            kiem_exit_reason_thiet_ke(SLOT, repo_dir=repo)

    @pytest.mark.parametrize("noi_dung", [
        "{không phải json",
        json.dumps({"lenh_that": {}}),
        json.dumps({"khac": 1}),
        json.dumps({"lenh_that": {"A1": {"so_lenh": 0, "exit_reason": {}}}}),
        json.dumps({"lenh_that": {"A1": {"so_lenh": 10, "exit_reason": {"TIME_STOP": 1, "x": 5}}}}),
        json.dumps({"lenh_that": {"A1": {"so_lenh": 10, "exit_reason": {"TIME_STOP": 1.0, "x": 9}}}}),
        json.dumps({"lenh_that": {"A1": {"so_lenh": "10", "exit_reason": {"TIME_STOP": 1, "x": 9}}}}),
    ], ids=["json-hong", "lenh-that-rong", "thieu-lenh-that", "0-lenh", "tong-lech", "dem-float", "so-lenh-chuoi"])
    def test_hien_vat_hong_thi_chan_khong_doan(self, tmp_path: Path, noi_dung: str) -> None:
        """N6: không đo được ⇒ từ chối, không coi là 0% hay "trong dải"."""
        repo = _repo(tmp_path)
        _ghi(repo, duong_dan_artifact(SLOT).as_posix(), noi_dung)
        with pytest.raises(ExitReasonThietKeError):
            kiem_exit_reason_thiet_ke(SLOT, repo_dir=repo)


class TestLoiThoatDrBietTruoc:
    """Lối thoát duy nhất §4.2 bước 3 cho phép: chủ dự án khai bằng DR rằng ứng viên vào cổng biết trước là trượt."""

    DR = "docs/decisions/DR-IQ-0042-biet-truoc-truot.md"
    NOI_DUNG_DR = f"# {SLOT}\n\nTheo `DR-PHAN-QUYET-01` §4.2 bước 3: vào cổng D0.9 biết trước là trượt TIME_STOP.\n"

    def _kq(self) -> dict:
        kq = _hien_vat(100, 0)
        kq["dr_biet_truoc_truot"] = self.DR
        return kq

    def test_dr_da_commit_dung_dia_chi_thi_qua(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        _ghi(repo, self.DR, self.NOI_DUNG_DR)
        _ghi_hien_vat(repo, self._kq())
        kiem_exit_reason_thiet_ke(SLOT, repo_dir=repo)

    def test_dr_chua_commit_thi_chan(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        _ghi(repo, self.DR, self.NOI_DUNG_DR, commit=False)
        _ghi_hien_vat(repo, self._kq())
        with pytest.raises(ExitReasonThietKeError, match="CHƯA COMMIT"):
            kiem_exit_reason_thiet_ke(SLOT, repo_dir=repo)

    def test_dr_khong_nhac_dich_danh_slot_thi_chan(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        _ghi(repo, self.DR, "# IQ-0001\n\nTheo `DR-PHAN-QUYET-01`.\n")
        _ghi_hien_vat(repo, self._kq())
        with pytest.raises(ExitReasonThietKeError, match="đích danh"):
            kiem_exit_reason_thiet_ke(SLOT, repo_dir=repo)

    @pytest.mark.parametrize("duong", ["docs/du-lieu-do/x.md", "docs/decisions/sub/x.md", "docs/decisions/x.txt", ""])
    def test_dr_sai_dia_chi_thi_chan(self, tmp_path: Path, duong: str) -> None:
        repo = _repo(tmp_path)
        kq = self._kq()
        kq["dr_biet_truoc_truot"] = duong
        _ghi_hien_vat(repo, kq)
        with pytest.raises(ExitReasonThietKeError):
            kiem_exit_reason_thiet_ke(SLOT, repo_dir=repo)


class TestNoiVaoReserve:
    """Cửa ở `TrialLedger.reserve()` — mọi đường ghi sổ đều đi qua."""

    def test_suat_dau_tien_thieu_hien_vat_bi_tu_choi_so_dung_yen(self, tmp_path: Path) -> None:
        so, duong = _so(tmp_path, _repo(tmp_path))
        with pytest.raises(ThietKeChuaKiemError, match="TỪ CHỐI suất đầu tiên"):
            _reserve(so)
        assert _so_dong(duong) == 0

    @pytest.mark.parametrize("budget_line", ["B2", "B3"])
    def test_moi_dong_danh_gia_deu_bi_chan(self, tmp_path: Path, budget_line: str) -> None:
        """B1 có cửa riêng đứng TRƯỚC (`D5_DO_TAM_DUNG`, TD-0373) nên không dùng để thử cửa này."""
        so, duong = _so(tmp_path, _repo(tmp_path))
        with pytest.raises(ThietKeChuaKiemError):
            _reserve(so, budget_line=budget_line)
        assert _so_dong(duong) == 0

    def test_ngoai_dai_bi_tu_choi_so_dung_yen(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        _ghi_hien_vat(repo, _hien_vat(246, 1))
        so, duong = _so(tmp_path, repo)
        with pytest.raises(ThietKeChuaKiemError, match="ngoài dải"):
            _reserve(so)
        assert _so_dong(duong) == 0

    def test_trong_dai_thi_ghi_duoc(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        _ghi_hien_vat(repo, _hien_vat(100, 10))
        so, duong = _so(tmp_path, repo)
        _reserve(so)
        assert _so_dong(duong) == 1

    def test_suat_thu_hai_cung_slot_khong_kiem_lai(self, tmp_path: Path) -> None:
        """Cửa chỉ canh suất ĐẦU TIÊN — hiện vật bị xoá sau đó không làm gãy các suất kế của ứng viên đã qua cửa."""
        repo = _repo(tmp_path)
        _ghi_hien_vat(repo, _hien_vat(100, 10))
        so, duong = _so(tmp_path, repo)
        _reserve(so)
        (repo / duong_dan_artifact(SLOT)).unlink()
        _reserve(so, param_value=0.6)
        assert _so_dong(duong) == 2

    def test_slot_khac_van_phai_qua_cua(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        _ghi_hien_vat(repo, _hien_vat(100, 10))
        so, duong = _so(tmp_path, repo)
        _reserve(so)
        with pytest.raises(ThietKeChuaKiemError):
            _reserve(so, hypothesis_slot="IQ-0043")
        assert _so_dong(duong) == 1

    @pytest.mark.parametrize("slot", ["A-01", "A-03", "IQ-42", "iq-0042", "IQ-00420"])
    def test_slot_khong_phai_ung_vien_khong_bi_ap(self, tmp_path: Path, slot: str) -> None:
        """ZA LONG (`A-xx`) giữ nguyên hành vi — sổ trial hiện có không đổi."""
        so, duong = _so(tmp_path, _repo(tmp_path))
        _reserve(so, hypothesis_slot=slot)
        assert _so_dong(duong) == 1

    def test_B0_khong_bi_ap(self, tmp_path: Path) -> None:
        """B0 = tiêu chí pool, hạ tầng — không phải đánh giá cấu hình của ứng viên."""
        so, duong = _so(tmp_path, _repo(tmp_path))
        _reserve(so, budget_line="B0", dataset="N/A")
        assert _so_dong(duong) == 1

    def test_CTRL_khong_bi_ap(self, tmp_path: Path) -> None:
        so, duong = _so(tmp_path, _repo(tmp_path))
        _reserve(so, budget_line="CTRL", ctrl_output_whitelist=["price_delta", "tranche_index"])
        assert _so_dong(duong) == 1

    def test_mac_dinh_repo_dir_la_goc_repo_that(self) -> None:
        """Không có tham số nào TẮT cửa: mặc định trỏ gốc repo thật (cwd), nơi hôm nay KHÔNG có hiện vật `IQ-*`."""
        import inspect

        assert inspect.signature(TrialLedger).parameters["repo_dir"].default == Path(".")
