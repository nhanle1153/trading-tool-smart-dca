"""TD-0396 — `DR-BIEN-THE-01`: `so_bien_the` đếm CẤU HÌNH phân biệt, không đếm suất.

Ba lớp, cùng một luật:
  1. `tool_d.ledger.bien_the` — đọc danh sách khoá từ khối `DR-BIEN-THE-01:KHOA` (DR đã commit, đúng một khối/slot) và
     băm đúng các khoá đó: đổi khoá NGOÀI danh sách không đổi hash, đổi khoá TRONG danh sách thì đổi.
  2. Cửa ghi `TrialLedger.reserve()` — slot đã khai `so_bien_the` ⇒ dòng vào `N` phải mang `bien_the_hash`, và số hash
     phân biệt (kể cả dòng mới) ≤ số đã khai. Từ chối TRƯỚC khi ghi; sổ đứng yên.
  3. Audit `TD-0119b` — đếm hash phân biệt trên suất CONSUMED; dòng thiếu hash đếm riêng mỗi dòng.

Repo git THẬT trong `tmp_path` — "đã commit" là thứ đang được kiểm (khuôn `test_td0375`).
"""

from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from tool_d.gates.exit_reason_thiet_ke import duong_dan_artifact
from tool_d.ledger.audit_checks import check_td0119_so_bien_the_khong_vuot_khai
from tool_d.ledger.bien_the import BienTheError, doc_khoa_bien_the, la_bien_the_hash, tinh_bien_the_hash
from tool_d.ledger.registry import BienTheVuotKhaiError, TrialLedger

SLOT = "IQ-0042"
KHOA = ["tier_a.von", "tier_c.ro.cua_so"]
HASH_A = "a" * 64
HASH_B = "b" * 64
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


def _khoi(slot: str = SLOT, khoa: object = None) -> str:
    return (
        "<!-- DR-BIEN-THE-01:KHOA:BEGIN -->\n```json\n"
        + json.dumps({"slot": slot, "khoa": KHOA if khoa is None else khoa})
        + "\n```\n<!-- DR-BIEN-THE-01:KHOA:END -->\n"
    )


class TestDocKhoa:
    def test_dr_da_commit_mot_khoi_thi_doc_duoc(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        _ghi(repo, "docs/decisions/DR-D0-X.md", "# D0\n" + _khoi() + _khoi(slot="IQ-0099", khoa=["tier_a.khac"]))
        assert doc_khoa_bien_the(SLOT, repo_dir=repo) == tuple(KHOA)

    def test_khong_co_khoi_thi_tu_choi(self, tmp_path: Path) -> None:
        with pytest.raises(BienTheError, match="thấy 0"):
            doc_khoa_bien_the(SLOT, repo_dir=_repo(tmp_path))

    def test_hai_dr_cung_slot_thi_tu_choi(self, tmp_path: Path) -> None:
        """Hai nguồn sự thật cho một danh sách khoá (N1) — không chọn bừa một."""
        repo = _repo(tmp_path)
        _ghi(repo, "docs/decisions/DR-A.md", _khoi())
        _ghi(repo, "docs/decisions/DR-B.md", _khoi())
        with pytest.raises(BienTheError, match="thấy 2"):
            doc_khoa_bien_the(SLOT, repo_dir=repo)

    def test_dr_chua_commit_thi_tu_choi(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        _ghi(repo, "docs/decisions/DR-A.md", _khoi(), commit=False)
        with pytest.raises(BienTheError, match="CHƯA COMMIT"):
            doc_khoa_bien_the(SLOT, repo_dir=repo)

    @pytest.mark.parametrize("khoa", [[], ["von"], ["tier_a.x", "tier_a.x"], "tier_a.x", [1]])
    def test_danh_sach_khoa_hong_thi_tu_choi(self, tmp_path: Path, khoa: object) -> None:
        repo = _repo(tmp_path)
        _ghi(repo, "docs/decisions/DR-A.md", _khoi(khoa=khoa))
        with pytest.raises(BienTheError, match="khoá `tier_\\*`"):
            doc_khoa_bien_the(SLOT, repo_dir=repo)

    def test_khoi_hong_cua_slot_nay_thi_tu_choi(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        _ghi(repo, "docs/decisions/DR-A.md",
             "<!-- DR-BIEN-THE-01:KHOA:BEGIN -->\n{\"slot\": \"" + SLOT + "\", \"khoa\": [...]}\n<!-- DR-BIEN-THE-01:KHOA:END -->")
        with pytest.raises(BienTheError, match="hỏng"):
            doc_khoa_bien_the(SLOT, repo_dir=repo)

    def test_khoi_vi_du_hong_cua_slot_khac_bi_bo_qua(self, tmp_path: Path) -> None:
        """Ca thật bắt được lúc chạy trên repo: khối VÍ DỤ trong `DR-BIEN-THE-01` §3 không phải JSON hợp lệ."""
        repo = _repo(tmp_path)
        _ghi(repo, "docs/decisions/DR-VI-DU.md",
             "<!-- DR-BIEN-THE-01:KHOA:BEGIN -->\n{\"slot\": \"IQ-xxxx\", \"khoa\": [...]}\n<!-- DR-BIEN-THE-01:KHOA:END -->")
        _ghi(repo, "docs/decisions/DR-D0.md", _khoi())
        assert doc_khoa_bien_the(SLOT, repo_dir=repo) == tuple(KHOA)

    def test_dr_that_cua_iq0003_khai_dung_mot_khoi(self) -> None:
        """DR thiết kế thật (`DR-D0-IQ0003`, `3369483`) đọc được — chạy trên repo làm việc."""
        khoa = doc_khoa_bien_the("IQ-0003", repo_dir=Path("."))
        assert "tier_a.von_ro_usdt" in khoa and "tier_a.enable_short" in khoa


class TestBamKhoa:
    @staticmethod
    def _cfg(von: float = 1000.0, cua_so: int = 72, ngoai: int = 3) -> SimpleNamespace:
        return SimpleNamespace(tier_a={"von": von, "L_exchange": ngoai}, tier_c={"ro": {"cua_so": cua_so}})

    def test_doi_khoa_ngoai_danh_sach_khong_doi_hash(self) -> None:
        """Lý do tồn tại của DR §2 điều 3: tham số ZA đổi thì ứng viên không bị đếm thêm biến thể."""
        assert tinh_bien_the_hash(self._cfg(ngoai=3), KHOA) == tinh_bien_the_hash(self._cfg(ngoai=9), KHOA)

    @pytest.mark.parametrize("doi", [{"von": 1001.0}, {"cua_so": 48}])
    def test_doi_khoa_trong_danh_sach_thi_doi_hash(self, doi: dict) -> None:
        assert tinh_bien_the_hash(self._cfg(), KHOA) != tinh_bien_the_hash(self._cfg(**doi), KHOA)

    def test_thu_tu_khoa_khong_doi_hash(self) -> None:
        assert tinh_bien_the_hash(self._cfg(), KHOA) == tinh_bien_the_hash(self._cfg(), list(reversed(KHOA)))

    def test_khoa_khong_ton_tai_thi_no(self) -> None:
        with pytest.raises(KeyError):
            tinh_bien_the_hash(self._cfg(), ["tier_a.khong_co"])

    def test_hash_dung_dang(self) -> None:
        assert la_bien_the_hash(tinh_bien_the_hash(self._cfg(), KHOA))


def _so_y_tuong(thu_muc: Path, so_bien_the: int | None) -> None:
    """Hai dòng QUEUED → SELECTED hợp lệ theo `duyet_so` (DR-IQ-02 §4.1)."""
    nop = {"idea_id": SLOT, "status": "QUEUED", "mechanism": "m", "who_pays": "w", "durability": "d"}
    chon = dict(nop, status="SELECTED", selected_at="2026-10-01T00:00:00Z", so_bien_the=so_bien_the)
    (thu_muc / "idea_queue.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in (nop, chon)) + "\n", encoding="utf-8"
    )


def _so_trial(tmp_path: Path, *, so_bien_the: int | None = 1) -> tuple[TrialLedger, Path]:
    repo = _repo(tmp_path)
    # Cửa thiết kế TD-0375 đứng trước: hiện vật EXPLORE trong dải để đi tới cửa biến thể.
    _ghi(repo, duong_dan_artifact(SLOT).as_posix(), json.dumps(
        {"lenh_that": {"A": {"so_lenh": 100, "exit_reason": {"TIME_STOP": 10, "stop_loss": 90}}}}
    ))
    thu_muc = tmp_path / "registry"
    thu_muc.mkdir()
    if so_bien_the is not None:
        _so_y_tuong(thu_muc, so_bien_the)
    duong = thu_muc / "trial_registry.jsonl"
    return TrialLedger(duong, repo_dir=repo), duong


def _reserve(so: TrialLedger, bien_the_hash: str | None) -> str:
    return so.reserve(
        n_dang_ky=114, so_lenh_da_dong=0, tool_id="D", budget_line="B3", hypothesis_slot=SLOT,
        direction="LONG", dataset="CALIB", param_under_test="x", param_value=1,
        params_frozen_hash="f" * 64, config_hash="c" * 64, code_commit="a" * 40,
        provenance=PROVENANCE, contribution=1, bien_the_hash=bien_the_hash,
    )


def _so_dong(duong: Path) -> int:
    return len([d for d in duong.read_text(encoding="utf-8").splitlines() if d.strip()])


class TestCuaReserve:
    def test_slot_da_khai_ma_thieu_hash_thi_tu_choi_so_dung_yen(self, tmp_path: Path) -> None:
        so, duong = _so_trial(tmp_path)
        with pytest.raises(BienTheVuotKhaiError, match="phải mang `bien_the_hash`"):
            _reserve(so, None)
        assert _so_dong(duong) == 0

    def test_cung_cau_hinh_nhieu_suat_la_mot_bien_the(self, tmp_path: Path) -> None:
        """Nghĩa mới của `so_bien_the: 1` — CALIB, WFO, lockbox cùng một cấu hình."""
        so, duong = _so_trial(tmp_path)
        for _ in range(3):
            _reserve(so, HASH_A)
        assert _so_dong(duong) == 3
        assert {json.loads(d)["bien_the_hash"] for d in duong.read_text(encoding="utf-8").splitlines()} == {HASH_A}

    def test_cau_hinh_thu_hai_vuot_khai_thi_tu_choi_so_dung_yen(self, tmp_path: Path) -> None:
        so, duong = _so_trial(tmp_path)
        _reserve(so, HASH_A)
        with pytest.raises(BienTheVuotKhaiError, match="biến thể thứ 2"):
            _reserve(so, HASH_B)
        assert _so_dong(duong) == 1

    def test_khai_hai_thi_cau_hinh_thu_hai_qua(self, tmp_path: Path) -> None:
        so, duong = _so_trial(tmp_path, so_bien_the=2)
        _reserve(so, HASH_A)
        _reserve(so, HASH_B)
        assert _so_dong(duong) == 2

    def test_hash_sai_dang_thi_tu_choi(self, tmp_path: Path) -> None:
        so, duong = _so_trial(tmp_path)
        with pytest.raises(BienTheVuotKhaiError, match="sha256"):
            _reserve(so, "khong-phai-hash")
        assert _so_dong(duong) == 0

    def test_slot_chua_khai_thi_hanh_vi_cu_giu_nguyen(self, tmp_path: Path) -> None:
        """Không có lần CHỌN nào khai `so_bien_the` cho slot ⇒ cửa này không áp (các test cũ gọi reserve không hash)."""
        so, duong = _so_trial(tmp_path, so_bien_the=None)
        _reserve(so, None)
        assert _so_dong(duong) == 1


class TestAudit:
    @staticmethod
    def _consumed(duong: Path, tid: str, bien_the_hash: str | None) -> None:
        reserve = {
            "event": "RESERVE", "trial_id": tid, "registered_at": "2026-10-02T10:00:00Z", "budget_line": "B3",
            "hypothesis_slot": SLOT, "direction": "LONG", "dataset": "CALIB", "param_under_test": "x",
            "param_value": 1, "params_frozen_hash": "f", "config_hash": "c", "code_commit": "a",
            "provenance": PROVENANCE, "contribution": 1, "tool_id": "D",
        }
        if bien_the_hash is not None:
            reserve["bien_the_hash"] = bien_the_hash
        consume = {
            "event": "CONSUME", "trial_id": tid, "executed_at": "2026-10-02T11:00:00Z",
            "outcome": {"expectancy": None, "sharpe": None, "n_trades": None, "max_single_loss_ratio": None},
            "verdict": "INCONCLUSIVE", "rejection_reason": None, "retest_forbidden": True,
        }
        with duong.open("a", encoding="utf-8") as f:
            f.write(json.dumps(reserve) + "\n" + json.dumps(consume) + "\n")

    def _chay(self, tmp_path: Path, hashes: list[str | None]):
        thu_muc = tmp_path / "registry"
        thu_muc.mkdir()
        _so_y_tuong(thu_muc, 1)
        duong = thu_muc / "trial_registry.jsonl"
        duong.touch()
        for i, h in enumerate(hashes):
            self._consumed(duong, f"D-{i + 1:04d}", h)
        return check_td0119_so_bien_the_khong_vuot_khai(thu_muc / "idea_queue.jsonl", duong)

    def test_ba_suat_mot_cau_hinh_thi_dat(self, tmp_path: Path) -> None:
        assert self._chay(tmp_path, [HASH_A, HASH_A, HASH_A]).ok is True

    def test_hai_cau_hinh_vuot_khai_thi_do(self, tmp_path: Path) -> None:
        kq = self._chay(tmp_path, [HASH_A, HASH_B])
        assert kq.is_fail is True and "2 cấu hình phân biệt" in kq.evidence

    def test_dong_thieu_hash_dem_rieng_tung_dong(self, tmp_path: Path) -> None:
        kq = self._chay(tmp_path, [None, None])
        assert kq.is_fail is True and "2 cấu hình phân biệt" in kq.evidence


class TestE1NoiDung:
    def test_e1_tinh_va_truyen_bien_the_hash_vao_reserve(self) -> None:
        """E1 là đường đặt suất của ứng viên — nó phải truyền `bien_the_hash` vào đúng lời gọi `reserve()`."""
        cay = ast.parse(Path("entrypoints/run_backtest.py").read_text(encoding="utf-8"))
        goi = [
            n for n in ast.walk(cay)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "reserve"
        ]
        assert goi, "E1 không còn gọi reserve()"
        assert all(any(k.arg == "bien_the_hash" for k in n.keywords) for n in goi)
        assert "tinh_bien_the_hash(" in Path("entrypoints/run_backtest.py").read_text(encoding="utf-8")
