"""TD-0378 (`DR-DINH-DANH-01` §4.2, giải `MT-76`) — cửa ghi `CTRL` tái lập siết đúng trục.

Trước TD-0378 cửa chỉ so `config_hash` + `params_frozen_hash` (hai băm này LUÔN bằng nhau trên sổ thật ⇒ thật ra là
MỘT phép so), nên: (a) một `CTRL` trỏ về dòng E7 chốt pool khớp hai chuỗi lính canh `"n/a"` và được ghi 0 suất;
(b) một "tái lập" trên dataset / dữ liệu / phạm vi KHÁC vẫn được ghi 0 suất.

🔑 Hướng NGƯỢC bị loại có chủ ý: bắt cùng `code_commit`. §0d.4 chạy điểm kiểm soát SAU khi commit giá trị mới —
bắt cùng commit là làm mọi điểm kiểm soát không thoả được. Ca `test_KHAC_code_commit_van_ghi_duoc` ghim điều đó.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tool_d.ledger.registry import CtrlClaimError, TrialLedger

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


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    (r / "src").mkdir(parents=True)
    (r / "src/a.py").write_text("X = 1\n", encoding="utf-8")
    for lenh in (["init", "-q"], ["add", "-A"], ["commit", "-qm", "seed"]):
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *lenh], cwd=r, check=True,
                       capture_output=True)
    return r


def _kw(**doi) -> dict:
    k = {
        "n_dang_ky": 114, "budget_line": "B3", "hypothesis_slot": "A-03", "direction": "LONG",
        "dataset": "CALIB", "param_under_test": "zss_threshold", "param_value": 0.55,
        "params_frozen_hash": "c" * 64, "config_hash": "c" * 64, "code_commit": "a" * 40,
        "provenance": PROVENANCE, "contribution": 1,
    }
    k.update(doi)
    return k


def _goc(so: TrialLedger, *, tieu_thu: bool = True, expectancy: float | None = 0.02, **doi) -> str:
    tid = so.reserve(**_kw(**doi))
    so.seal(tid, seal_path=f"runs/{tid}/metrics.seal")
    if tieu_thu:
        so.consume(tid, outcome={**OUTCOME, "expectancy": expectancy}, verdict="REJECTED")
    return tid


def _so_dong(p: Path) -> int:
    return sum(1 for d in p.read_text(encoding="utf-8").splitlines() if d.strip())


class TestTaiLapHopLe:
    def test_KHAC_code_commit_van_ghi_duoc(self, tmp_path: Path, repo: Path) -> None:
        """§0d.4: *"đưa giá trị mới vào tool_d_config.yaml, commit; chạy lại …"* — điểm kiểm soát khác commit theo
        định nghĩa. Ca này đỏ ⇒ ai đó đã đi đúng hướng `DR-DINH-DANH-01` §3.1 loại."""
        so = TrialLedger(tmp_path / "reg.jsonl", repo_dir=repo)
        goc = _goc(so)
        assert so.reserve(**_kw(budget_line="CTRL", reproduces_trial_id=goc, code_commit="b" * 40))


class TestTuChoiTaiCua:
    @pytest.mark.parametrize("gia_tri", ["n/a", ""])
    def test_hash_linh_canh(self, tmp_path: Path, repo: Path, gia_tri: str) -> None:
        """Ca `MT-76` đo được: hai chuỗi lính canh bằng nhau KHÔNG chứng minh cùng cấu hình."""
        so_path = tmp_path / "reg.jsonl"
        so = TrialLedger(so_path, repo_dir=repo)
        goc = _goc(so, config_hash=gia_tri, params_frozen_hash=gia_tri)
        truoc = _so_dong(so_path)
        with pytest.raises(CtrlClaimError, match="lính canh"):
            so.reserve(**_kw(budget_line="CTRL", reproduces_trial_id=goc,
                             config_hash=gia_tri, params_frozen_hash=gia_tri))
        assert _so_dong(so_path) == truoc

    def test_goc_la_dong_B0(self, tmp_path: Path, repo: Path) -> None:
        so = TrialLedger(tmp_path / "reg.jsonl", repo_dir=repo)
        goc = _goc(so, budget_line="B0", dataset="N/A", hypothesis_slot="POOL-0.3")
        with pytest.raises(CtrlClaimError, match="B1/B2/B3"):
            so.reserve(**_kw(budget_line="CTRL", reproduces_trial_id=goc, dataset="N/A", hypothesis_slot="POOL-0.3"))

    def test_goc_la_dong_CTRL(self, tmp_path: Path, repo: Path) -> None:
        """Tái lập một điểm kiểm soát là chuỗi tái lập không có trial thật nào ở đầu."""
        so = TrialLedger(tmp_path / "reg.jsonl", repo_dir=repo)
        goc = so.reserve(**_kw(budget_line="CTRL", ctrl_output_whitelist=["price_delta"]))
        so.seal(goc, seal_path=f"runs/{goc}/metrics.seal")
        so.consume(goc, outcome=OUTCOME, verdict="REJECTED")
        with pytest.raises(CtrlClaimError, match="B1/B2/B3"):
            so.reserve(**_kw(budget_line="CTRL", reproduces_trial_id=goc))

    def test_goc_chua_CONSUMED(self, tmp_path: Path, repo: Path) -> None:
        so = TrialLedger(tmp_path / "reg.jsonl", repo_dir=repo)
        goc = _goc(so, tieu_thu=False)
        with pytest.raises(CtrlClaimError, match="chưa CONSUMED"):
            so.reserve(**_kw(budget_line="CTRL", reproduces_trial_id=goc))

    def test_goc_CONSUMED_nhung_khong_co_expectancy(self, tmp_path: Path, repo: Path) -> None:
        so = TrialLedger(tmp_path / "reg.jsonl", repo_dir=repo)
        goc = _goc(so, expectancy=None)
        with pytest.raises(CtrlClaimError, match="expectancy"):
            so.reserve(**_kw(budget_line="CTRL", reproduces_trial_id=goc))

    @pytest.mark.parametrize(
        "doi, ten",
        [
            ({"dataset": "WFO"}, "dataset"),
            ({"direction": "SHORT"}, "direction"),
            ({"param_under_test": "buf_sl_atr"}, "param_under_test"),
            ({"param_value": 0.6}, "param_value"),
            ({"provenance": {**PROVENANCE, "data_hashes": {"BTC_USDT-1h.feather": "e" * 64}}}, "data_hashes"),
        ],
        ids=["dataset", "direction", "param_under_test", "param_value", "data_hashes"],
    )
    def test_pham_vi_hoac_du_lieu_lech(self, tmp_path: Path, repo: Path, doi: dict, ten: str) -> None:
        """Đổi dữ liệu hay phạm vi là PHÉP THỬ MỚI — phải tiêu ngân sách, không được ghi 0 suất."""
        so_path = tmp_path / "reg.jsonl"
        so = TrialLedger(so_path, repo_dir=repo)
        goc = _goc(so)
        truoc = _so_dong(so_path)
        with pytest.raises(CtrlClaimError, match=ten):
            so.reserve(**_kw(budget_line="CTRL", reproduces_trial_id=goc, **doi))
        assert _so_dong(so_path) == truoc
