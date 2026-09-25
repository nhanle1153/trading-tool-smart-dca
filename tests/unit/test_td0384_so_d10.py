"""TD-0384 (`DR-D10-02` §5.3) — đặt chỗ MỘT dòng CTRL đo vận hành cho đợt D10 qua E6 `--d10-dat-cho`.

Chạy trên một repo git TẠM (cấu hình thật + rổ giả đã commit), sổ trial TẠM — không đụng sổ thật."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest
import yaml

from tool_d.ledger.registry import TrialLedger
from tool_d.ops.live_d10 import RO_D10
from tool_d.ops.so_d10 import THAM_SO_D10, dat_cho_dong_d10

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((REPO_ROOT / "registry/schemas/trial_event.schema.json").read_text(encoding="utf-8"))
RO = ["DOGE/USDT:USDT", "XRP/USDT:USDT"]


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path) -> Path:
    if shutil.which("git") is None:
        pytest.skip("không có git")
    r = tmp_path / "r"
    for rel in ("config/tool_d_config.yaml", "docker/Dockerfile"):
        (r / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO_ROOT / rel, r / rel)
    (r / RO_D10).write_text(yaml.safe_dump({"cap": RO}), encoding="utf-8")
    _git(r, "init", "-q")
    _git(r, "config", "user.email", "t@t")
    _git(r, "config", "user.name", "t")
    _git(r, "add", "-A")
    _git(r, "commit", "-qm", "goc")
    return r


class TestDatCho:
    def test_ghi_dung_mot_dong_ctrl_van_hanh_khop_schema(self, repo, tmp_path) -> None:
        so_path = tmp_path / "so.jsonl"
        tid = dat_cho_dong_d10(ledger=TrialLedger(path=so_path, repo_dir=repo), repo_dir=repo)
        (e,) = [json.loads(d) for d in so_path.read_text(encoding="utf-8").splitlines() if d.strip()]
        assert e["trial_id"] == tid and e["budget_line"] == "CTRL" and e["hypothesis_slot"] == "D10"
        assert e["dataset"] == "N/A" and e["param_under_test"] == THAM_SO_D10
        assert e["param_value"]["ro"] == RO and e["param_value"]["ctrl_d10"]["sl_pct"] == 2
        assert sorted(e["ctrl_van_hanh_whitelist"]) == ["fill_price", "gap_ms", "order_status", "p_i"]
        assert "run_fingerprint" in e
        jsonschema.validate(e, SCHEMA)

    def test_ro_sua_sau_commit_thi_khong_ghi(self, repo, tmp_path) -> None:
        (repo / RO_D10).write_text(yaml.safe_dump({"cap": ["BTC/USDT:USDT"]}), encoding="utf-8")
        so_path = tmp_path / "so.jsonl"
        with pytest.raises(Exception, match="SỬA sau commit"):
            dat_cho_dong_d10(ledger=TrialLedger(path=so_path, repo_dir=repo), repo_dir=repo)
        assert not so_path.exists() or so_path.read_text(encoding="utf-8").strip() == ""

    def test_dot_thu_hai_khi_dot_dau_con_mo_thi_tu_choi(self, repo, tmp_path) -> None:
        so_path = tmp_path / "so.jsonl"
        so = TrialLedger(path=so_path, repo_dir=repo)
        dat_cho_dong_d10(ledger=so, repo_dir=repo)
        with pytest.raises(Exception, match="đang mở"):
            dat_cho_dong_d10(ledger=so, repo_dir=repo)


class TestE6:
    def test_e6_tu_choi_khi_ro_chua_commit_so_khong_doi(self, tmp_path) -> None:
        if str(REPO_ROOT / "entrypoints") not in sys.path:
            sys.path.insert(0, str(REPO_ROOT / "entrypoints"))
        import trial_ledger_audit as e6  # noqa: PLC0415

        r = tmp_path / "r"
        (r / "config").mkdir(parents=True)
        shutil.copy(REPO_ROOT / "config/tool_d_config.yaml", r / "config/tool_d_config.yaml")
        _git(r, "init", "-q")
        so_path = tmp_path / "so.jsonl"
        ma, text = e6.d10_dat_cho(registry_path=so_path, repo_dir=r)
        assert ma == e6.EXIT_DON_TU_CHOI and "TỪ CHỐI đặt chỗ D10" in text
        # `TrialLedger()` tạo file sổ RỖNG lúc khởi tạo — thứ phải kiểm là KHÔNG có dòng sự kiện nào.
        assert not so_path.exists() or so_path.read_text(encoding="utf-8").strip() == ""

    def test_co_d10_dat_cho_trong_parser(self) -> None:
        if str(REPO_ROOT / "entrypoints") not in sys.path:
            sys.path.insert(0, str(REPO_ROOT / "entrypoints"))
        import trial_ledger_audit as e6  # noqa: PLC0415

        assert e6.build_parser().parse_args(["--d10-dat-cho"]).d10_dat_cho is True
