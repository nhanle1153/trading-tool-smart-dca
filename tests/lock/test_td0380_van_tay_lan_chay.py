"""TD-0380 (`DR-DINH-DANH-01` §4.1) — dấu vân tay LẦN CHẠY ghi tại cửa ghi sổ trial.

Vì sao: tới 24/09/2026 hệ thống không có trường nào định danh "một lần chạy" — `L-Z12` chọn `(config, commit)`, cửa
`CTRL` tái lập chọn `config`, cache WFO chọn `config + code + data`; và 22/22 dòng RESERVE mang
`reproducible_from_sha = False`, tức `code_commit` một mình không định danh được mã đã chạy.

Mọi ca dùng một repo git THẬT trong `tmp_path`: vân tay đổi vì mã đổi thật trên đĩa, không vì một chuỗi giả.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import jsonschema
import pytest

from tool_d.ledger.audit_checks import check_lz12_no_duplicate_config_hash_different_outcome
from tool_d.ledger.registry import TrialLedger
from tool_d.measurement.gitinfo import GitInfoError

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((REPO_ROOT / "registry/schemas/trial_event.schema.json").read_text(encoding="utf-8"))
PROVENANCE = {
    "params_source": "yaml",
    "params_effective": {},
    "git_sha": "a" * 40,
    "reproducible_from_sha": False,
    "data_hashes": {"BTC_USDT-1h.feather": "d" * 64},
    "cache_mode": "none",
    "guard_passed": True,
}
OUTCOME = {"expectancy": 0.02, "sharpe": 0.5, "n_trades": 100, "max_single_loss_ratio": 1.0}


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=repo, check=True, capture_output=True
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    (r / "src").mkdir(parents=True)
    (r / "src/chien_luoc.py").write_text("X = 1\n", encoding="utf-8")
    _git(r, "init", "-q")
    _git(r, "add", "-A")
    _git(r, "commit", "-qm", "seed")
    return r


def _reserve(so: TrialLedger, **doi) -> str:
    tham_so = {
        "n_dang_ky": 114, "budget_line": "B3", "hypothesis_slot": "A-03", "direction": "LONG",
        "dataset": "CALIB", "param_under_test": "zss_threshold", "param_value": 0.55,
        "params_frozen_hash": "c" * 64, "config_hash": "c" * 64, "code_commit": "a" * 40,
        "provenance": PROVENANCE, "contribution": 1,
    }
    tham_so.update(doi)
    return so.reserve(**tham_so)


def _reserve_rows(path: Path) -> list[dict]:
    return [
        json.loads(d) for d in path.read_text(encoding="utf-8").splitlines() if d.strip()
        if json.loads(d)["event"] == "RESERVE"
    ]


def _van_tay(path: Path) -> list[str | None]:
    return [r.get("run_fingerprint") for r in _reserve_rows(path)]


class TestCuaGhiTuTinhVanTay:
    def test_dong_moi_mang_van_tay_hop_le_schema(self, tmp_path: Path, repo: Path) -> None:
        so_path = tmp_path / "reg.jsonl"
        _reserve(TrialLedger(so_path, repo_dir=repo))
        dong = _reserve_rows(so_path)[0]
        assert isinstance(dong.get("run_fingerprint"), str) and len(dong["run_fingerprint"]) == 64
        jsonschema.validate(dong, SCHEMA)

    def test_cung_moi_thu_thi_cung_van_tay(self, tmp_path: Path, repo: Path) -> None:
        so_path = tmp_path / "reg.jsonl"
        so = TrialLedger(so_path, repo_dir=repo)
        _reserve(so)
        _reserve(so)
        a, b = _van_tay(so_path)
        assert a == b

    def test_ma_doi_CHUA_COMMIT_cung_commit_thi_khac_van_tay(self, tmp_path: Path, repo: Path) -> None:
        """🔑 Ca sinh ra TD-0380: `code_commit` y hệt, mã chạy thật khác nhau (thay đổi dở chưa commit)."""
        so_path = tmp_path / "reg.jsonl"
        so = TrialLedger(so_path, repo_dir=repo)
        _reserve(so)
        (repo / "src/chien_luoc.py").write_text("X = 2\n", encoding="utf-8")
        _reserve(so)
        a, b = _van_tay(so_path)
        assert a != b

    def test_file_chua_theo_doi_TRONG_vung_do_cung_lam_doi_van_tay(self, tmp_path: Path, repo: Path) -> None:
        """Một `.py` chưa commit trong `src/` vẫn được import khi chạy — cùng quy tắc `thay_doi_anh_huong_phep_do()`."""
        so_path = tmp_path / "reg.jsonl"
        so = TrialLedger(so_path, repo_dir=repo)
        _reserve(so)
        (repo / "src/moi").mkdir()
        (repo / "src/moi/them.py").write_text("Y = 1\n", encoding="utf-8")
        _reserve(so)
        a, b = _van_tay(so_path)
        assert a != b

    def test_rac_NGOAI_vung_do_khong_lam_doi_van_tay(self, tmp_path: Path, repo: Path) -> None:
        """Ảnh chụp, thư mục nháp ở gốc repo không đổi hành vi — không được tách hai lần chạy giống nhau."""
        so_path = tmp_path / "reg.jsonl"
        so = TrialLedger(so_path, repo_dir=repo)
        _reserve(so)
        (repo / "scratch_dl").mkdir()
        (repo / "scratch_dl/rac.txt").write_text("rac\n", encoding="utf-8")
        _reserve(so)
        a, b = _van_tay(so_path)
        assert a == b

    @pytest.mark.parametrize(
        "doi",
        [
            {"dataset": "WFO"},
            {"direction": "SHORT"},
            {"param_value": 0.6},
            {"code_commit": "b" * 40},
            {"config_hash": "e" * 64, "params_frozen_hash": "e" * 64},
            {"provenance": {**PROVENANCE, "data_hashes": {"BTC_USDT-1h.feather": "f" * 64}}},
        ],
        ids=["dataset", "direction", "param_value", "code_commit", "config_hash", "data_hashes"],
    )
    def test_moi_yeu_to_deu_tach_van_tay(self, tmp_path: Path, repo: Path, doi: dict) -> None:
        so_path = tmp_path / "reg.jsonl"
        so = TrialLedger(so_path, repo_dir=repo)
        _reserve(so)
        _reserve(so, **doi)
        a, b = _van_tay(so_path)
        assert a != b

    def test_dong_linh_canh_n_a_KHONG_mang_van_tay(self, tmp_path: Path, repo: Path) -> None:
        """E7 chốt pool ghi `config_hash = "n/a"` — không phải một lần chạy cấu hình."""
        so_path = tmp_path / "reg.jsonl"
        _reserve(
            TrialLedger(so_path, repo_dir=repo), budget_line="B0", dataset="N/A",
            config_hash="n/a", params_frozen_hash="n/a", hypothesis_slot="POOL-0.3",
        )
        assert "run_fingerprint" not in _reserve_rows(so_path)[0]

    def test_git_loi_thi_TU_CHOI_va_so_khong_doi_dong_nao(self, tmp_path: Path) -> None:
        """FAIL-CLOSED: không định danh được mã ⇒ không đặt suất, KHÔNG ghi vân tay giả kiểu "sạch"."""
        khong_phai_repo = tmp_path / "khong_git"
        khong_phai_repo.mkdir()
        so_path = tmp_path / "reg.jsonl"
        with pytest.raises(GitInfoError):
            _reserve(TrialLedger(so_path, repo_dir=khong_phai_repo))
        assert so_path.read_text(encoding="utf-8") == ""


class TestLZ12GomTheoVanTay:
    def test_cung_commit_KHAC_ma_chua_commit_khac_ket_qua_thi_khong_do(self, tmp_path: Path, repo: Path) -> None:
        """Trước TD-0380, cặp `(config, commit)` gom hai lần chạy này làm MỘT và báo đỏ oan — đúng hình dạng sự cố
        `L-Z12` 20/09 lặp lại ở tầng thay đổi chưa commit."""
        so_path = tmp_path / "reg.jsonl"
        so = TrialLedger(so_path, repo_dir=repo)
        t1 = _reserve(so)
        (repo / "src/chien_luoc.py").write_text("X = 2\n", encoding="utf-8")
        t2 = _reserve(so)
        for tid, e in ((t1, 0.02), (t2, 0.09)):
            so.seal(tid, seal_path=f"runs/{tid}/metrics.seal")
            so.consume(tid, outcome={**OUTCOME, "expectancy": e}, verdict="REJECTED")
        r = check_lz12_no_duplicate_config_hash_different_outcome(so_path)
        assert not r.is_fail, r.evidence

    def test_cung_van_tay_khac_ket_qua_thi_DO_va_bang_chung_neu_van_tay(self, tmp_path: Path, repo: Path) -> None:
        so_path = tmp_path / "reg.jsonl"
        so = TrialLedger(so_path, repo_dir=repo)
        t1, t2 = _reserve(so), _reserve(so)
        for tid, e in ((t1, 0.02), (t2, 0.09)):
            so.seal(tid, seal_path=f"runs/{tid}/metrics.seal")
            so.consume(tid, outcome={**OUTCOME, "expectancy": e}, verdict="REJECTED")
        r = check_lz12_no_duplicate_config_hash_different_outcome(so_path)
        assert r.is_fail
        assert f"run_fingerprint={_van_tay(so_path)[0]}" in r.evidence

    def test_dong_CU_khong_van_tay_van_gom_theo_cap(self, tmp_path: Path, repo: Path) -> None:
        """Sổ append-only: dòng ghi trước TD-0380 không có vân tay và không được viết bù ⇒ về cặp của `DR-LZ12-01`."""
        so_path = tmp_path / "reg.jsonl"
        so = TrialLedger(so_path, repo_dir=repo)
        t1, t2 = _reserve(so), _reserve(so)
        for tid, e in ((t1, 0.02), (t2, 0.09)):
            so.seal(tid, seal_path=f"runs/{tid}/metrics.seal")
            so.consume(tid, outcome={**OUTCOME, "expectancy": e}, verdict="REJECTED")
        dong = [json.loads(d) for d in so_path.read_text(encoding="utf-8").splitlines() if d.strip()]
        for d in dong:
            d.pop("run_fingerprint", None)
        so_cu = tmp_path / "so_cu.jsonl"
        so_cu.write_text("".join(json.dumps(d, ensure_ascii=False) + "\n" for d in dong), encoding="utf-8")
        r = check_lz12_no_duplicate_config_hash_different_outcome(so_cu)
        assert r.is_fail
        assert "run_fingerprint" not in r.evidence
