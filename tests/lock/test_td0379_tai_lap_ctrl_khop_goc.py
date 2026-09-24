"""TD-0379 (`DR-DINH-DANH-01` §4.3) — điểm kiểm soát tái lập §0d.4 bước 3 thành MÁY.

Spec §0d.4: *"chạy lại MỘT backtest điểm kiểm soát … kết quả phải KHỚP với bản ghi registry của trial đã chấp nhận
giá trị đó (sai số ≤ 0.1% expectancy); lệch → giá trị CHƯA được áp"*. Tới 24/09/2026 bước so kết quả có **0 dòng
mã**. Ngưỡng: `abs(E_ctrl − E_gốc) ≤ max(0,001 × abs(E_gốc), 0,001 R)` — sàn tuyệt đối chủ dự án chọn 24/09/2026.

Tên test theo `MT-09` (không cấp mã `L-Z` mới).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tool_d.ledger.audit_checks import check_td0379_tai_lap_ctrl_khop_goc
from tool_d.ledger.registry import TrialLedger

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_THAT = REPO_ROOT / "config/tool_d_config.yaml"
PROVENANCE = {
    "params_source": "yaml",
    "params_effective": {},
    "git_sha": "a" * 40,
    "reproducible_from_sha": False,
    "data_hashes": {"BTC_USDT-1h.feather": "d" * 64},
    "cache_mode": "none",
    "guard_passed": True,
}


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


def _outcome(e: float | None) -> dict:
    return {"expectancy": e, "sharpe": 0.5, "n_trades": 100, "max_single_loss_ratio": 1.0}


def _so_tai_lap(
    tmp_path: Path, repo: Path, *, e_goc: float | None, e_ctrl: float | None, goc_consumed: bool = True
) -> Path:
    """Trial gốc B3 + một dòng CTRL tái lập (§0d.4: chạy SAU một commit ⇒ khác `code_commit`).

    `goc_consumed=False`: cửa ghi (TD-0378) KHÔNG cho ghi ca này nữa, nên dựng sổ hợp lệ rồi XOÁ dòng CONSUME của gốc —
    mô phỏng sổ ghi trước TD-0378 hay bị sửa tay, đúng chỗ phép kiểm sau-sự-việc vẫn phải canh."""
    so_path = tmp_path / "reg.jsonl"
    so = TrialLedger(so_path, repo_dir=repo)
    goc = so.reserve(**_kw())
    so.seal(goc, seal_path=f"runs/{goc}/metrics.seal")
    so.consume(goc, outcome=_outcome(e_goc if goc_consumed else 0.02), verdict="REJECTED")
    ctrl = so.reserve(**_kw(budget_line="CTRL", reproduces_trial_id=goc, code_commit="b" * 40))
    so.seal(ctrl, seal_path=f"runs/{ctrl}/metrics.seal")
    so.consume(ctrl, outcome=_outcome(e_ctrl), verdict="REJECTED")
    if not goc_consumed:
        dong = so_path.read_text(encoding="utf-8").splitlines(keepends=True)
        giu = [d for d in dong if not ('"CONSUME"' in d and f'"{goc}"' in d)]
        assert len(giu) == len(dong) - 1
        so_path.write_text("".join(giu), encoding="utf-8")
    return so_path


def _config(tmp_path: Path, *, bo_nguong: bool = False) -> Path:
    text = CONFIG_THAT.read_text(encoding="utf-8")
    if bo_nguong:
        dong = text.splitlines(keepends=True)
        i = next(k for k, d in enumerate(dong) if d.startswith("  tai_lap_ctrl:"))
        j = i + 1
        while j < len(dong) and dong[j].startswith("    "):
            j += 1
        text = "".join(dong[:i] + dong[j:])
        assert "tai_lap_ctrl" not in text
    p = tmp_path / "tool_d_config.yaml"
    p.write_text(text, encoding="utf-8")
    return p


class TestNguongTrongConfig:
    def test_config_that_mang_dung_nguong_chu_du_an_chon(self) -> None:
        """Ghim QUYẾT ĐỊNH ở đúng một chỗ, nêu đích danh DR (bài học TD-0171: tách ghim quan hệ khỏi ghim quyết định)."""
        from tool_d.config.loader import load_tool_d_config

        t = load_tool_d_config(CONFIG_THAT).tier_c["tai_lap_ctrl"]
        assert (t["sai_so_tuong_doi"], t["san_tuyet_doi_r"]) == (0.001, 0.001), "DR-DINH-DANH-01 §4.3"

    def test_khong_nam_trong_tier_b_khong_dem_dof(self) -> None:
        from tool_d.config.loader import load_tool_d_config

        assert "tai_lap_ctrl" not in load_tool_d_config(CONFIG_THAT).tier_b

    def test_khong_la_canh_bao(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("e6", REPO_ROOT / "entrypoints/trial_ledger_audit.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert "TD-0379" not in mod.WARN_ONLY_CODES


class TestPhepKiem:
    def test_khong_co_tai_lap_thi_PENDING(self, tmp_path: Path, repo: Path) -> None:
        so_path = tmp_path / "reg.jsonl"
        so = TrialLedger(so_path, repo_dir=repo)
        t = so.reserve(**_kw())
        so.seal(t, seal_path=f"runs/{t}/metrics.seal")
        so.consume(t, outcome=_outcome(0.02), verdict="REJECTED")
        r = check_td0379_tai_lap_ctrl_khop_goc(so_path, _config(tmp_path))
        assert r.measured.status.value == "pending", r.measured.render()

    def test_khop_tuyet_doi_thi_DAT(self, tmp_path: Path, repo: Path) -> None:
        r = check_td0379_tai_lap_ctrl_khop_goc(_so_tai_lap(tmp_path, repo, e_goc=0.02, e_ctrl=0.02), _config(tmp_path))
        assert r.ok, r.evidence

    @pytest.mark.parametrize(
        "e_goc, e_ctrl, dat",
        [
            (0.0, 0.0009, True),     # sàn 0,001 R thắng khi E_gốc sát 0 — chính lý do có sàn
            (0.0, 0.0011, False),
            (-0.0015, -0.0006, True),  # Z0-T1 EXPLORE: 0,1% của nó ≈ 0,0000015 — không sàn thì không bao giờ đạt
            (2.0, 2.0019, True),     # vế tương đối thắng: 0,1% × 2 = 0,002
            (2.0, 2.0021, False),
        ],
    )
    def test_dung_sai_max_tuong_doi_va_san(
        self, tmp_path: Path, repo: Path, e_goc: float, e_ctrl: float, dat: bool
    ) -> None:
        r = check_td0379_tai_lap_ctrl_khop_goc(
            _so_tai_lap(tmp_path, repo, e_goc=e_goc, e_ctrl=e_ctrl), _config(tmp_path)
        )
        assert r.ok is dat, r.evidence
        if not dat:
            assert "CHƯA được áp" in r.evidence

    def test_thieu_nguong_thi_DO_khong_PASS(self, tmp_path: Path, repo: Path) -> None:
        """N6: thước không có thì không được coi là khớp."""
        r = check_td0379_tai_lap_ctrl_khop_goc(
            _so_tai_lap(tmp_path, repo, e_goc=0.02, e_ctrl=0.02), _config(tmp_path, bo_nguong=True)
        )
        assert r.is_fail
        assert "tai_lap_ctrl" in r.evidence

    def test_goc_chua_CONSUMED_thi_DO(self, tmp_path: Path, repo: Path) -> None:
        r = check_td0379_tai_lap_ctrl_khop_goc(
            _so_tai_lap(tmp_path, repo, e_goc=0.02, e_ctrl=0.02, goc_consumed=False), _config(tmp_path)
        )
        assert r.is_fail
        assert "chưa CONSUMED" in r.evidence

    def test_expectancy_thieu_thi_DO(self, tmp_path: Path, repo: Path) -> None:
        r = check_td0379_tai_lap_ctrl_khop_goc(_so_tai_lap(tmp_path, repo, e_goc=0.02, e_ctrl=None), _config(tmp_path))
        assert r.is_fail
        assert "thiếu expectancy" in r.evidence
