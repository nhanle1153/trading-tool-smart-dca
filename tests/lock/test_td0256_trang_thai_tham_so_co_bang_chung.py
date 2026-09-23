"""🔒 TD-0256 — trạng thái tham số phải có BẰNG CHỨNG, ở hai tầng.

(i) **`L-Z15`: `status: TUNED` phải trỏ tới suất B1 CONSUMED thật.** Trước đây
    `TUNED` là một chữ: phép kiểm xanh khi có lời khai, không hỏi trial nào đã
    tune. Cùng hình dạng TD-0246 bắt được — lớp canh kiểm SỰ CÓ MẶT của lời
    khai, không kiểm NỘI DUNG.

(ii) **`L-Z29` so TẬP TÊN `tier_b`, không chỉ SỐ ĐẾM** — `MT-18` phương án (b),
    chủ dự án chốt 16/09/2026 (`DR-D5-01` §8). Tráo một khoá `tier_b` lấy một
    khoá khác mà giữ `|tier_b| = 12` thì `N = 114`, rào DSR `3,0777` đứng im
    trong khi thứ đang được tune đã đổi hẳn — và trước TD-0256 mọi phép kiểm
    đắt tiền của dự án đều xanh (ca `test_trao_khoa_giu_so_dem_la_DO`).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

from tool_d.config.dof import DofMismatchError, assert_dof_or_block, dof_report
from tool_d.ledger.audit_checks import check_lz15_calibrate_params_have_status
from tool_d.ledger.registry import TrialLedger

REPO_ROOT = Path(__file__).resolve().parents[2]
CFG_THAT = REPO_ROOT / "config" / "tool_d_config.yaml"
INV_THAT = REPO_ROOT / "config" / "dof_inventory.yaml"
DR_THAT = REPO_ROOT / "docs" / "decisions" / "DR-D5-01-pham-vi-ung-vien-luat-chon-calibration.md"


# ════ (ii) L-Z29 — tập tên ════


@pytest.fixture(autouse=True)
def _mo_khoa_d5(monkeypatch):
    """TD-0373: file này kiểm LUẬT của cửa B1 (`DR-D5-01`), nên cần đặt được suất trong sổ TẠM. Khoá
    `D5_DO_TAM_DUNG` chặn TRƯỚC luật đó; tắt nó chỉ trong tiến trình test này — khoá có test riêng
    (`tests/lock/test_td0373_khoa_do_d5.py`), khẳng định ở đây giữ nguyên."""
    from tool_d.ablation import khoa_do

    monkeypatch.setattr(khoa_do, "D5_DO_TAM_DUNG", False)


def _cfg_trao(tmp_path: Path, cu: str, moi_dong: str) -> Path:
    """Bản sao config thật, thay ĐÚNG dòng khoá `cu` trong khối tier_b."""
    text = CFG_THAT.read_text(encoding="utf-8")
    text2, n = re.subn(rf"^  {cu}: .*$", moi_dong, text, count=1, flags=re.M)
    assert n == 1, f"không tìm thấy dòng khoá {cu} trong config thật"
    p = tmp_path / "cfg.yaml"
    p.write_text(text2, encoding="utf-8")
    return p


class TestTapTenTierB:
    def test_file_that_12_ten_khop_N_114(self) -> None:
        r = dof_report(config_path=CFG_THAT, inventory_path=INV_THAT)
        assert r.tier_b_ten_ok, r.render()
        assert len(r.tier_b_ten_bang) == 12 and r.tier_b_ten_that == r.tier_b_ten_bang
        assert r.n_dang_ky_computed == 114 and r.dof_goc_declared == 28

    def test_trao_khoa_giu_so_dem_la_DO(self, tmp_path: Path) -> None:
        """🔴 Ca `MT-18`: bỏ `dg7_funding_frac` khỏi tier_b, đưa một khoá
        `tier_frozen` (`trend_age_days`) vào. Số đếm vẫn 12 — bản cũ xanh."""
        cfg = _cfg_trao(tmp_path, "dg7_funding_frac", "  trend_age_days: 5")
        r = dof_report(config_path=cfg, inventory_path=INV_THAT)
        assert r.tier_b_declared_count == r.tier_b_from_table_sum == 12, "ca này phải GIỮ số đếm"
        assert not r.tier_b_ten_ok and not r.tier_b_ok
        with pytest.raises(DofMismatchError, match="TÊN tier_b"):
            assert_dof_or_block(config_path=cfg, inventory_path=INV_THAT)

    def test_muc_dof_v6_1_thieu_khoa_la_DO(self, tmp_path: Path) -> None:
        inv = yaml.safe_load(INV_THAT.read_text(encoding="utf-8"))
        muc = next(r for r in inv["rows"] if r["dof_v6"] == 1)
        del muc["khoa_tier_b"]
        p = tmp_path / "inv.yaml"
        p.write_text(yaml.safe_dump(inv, allow_unicode=True), encoding="utf-8")
        with pytest.raises(DofMismatchError, match="thiếu khoa_tier_b"):
            assert_dof_or_block(config_path=CFG_THAT, inventory_path=p)

    def test_muc_dof_v6_0_khai_khoa_la_DO(self, tmp_path: Path) -> None:
        """Dòng §3.3d nhắc `funding_rate_pct` trong chữ nhưng `dof_v6: 0` — khai
        khoá ở đó là đếm một bậc tự do hai lần."""
        inv = yaml.safe_load(INV_THAT.read_text(encoding="utf-8"))
        muc = next(r for r in inv["rows"] if r["dof_v6"] == 0)
        muc["khoa_tier_b"] = "funding_rate_pct"
        p = tmp_path / "inv.yaml"
        p.write_text(yaml.safe_dump(inv, allow_unicode=True), encoding="utf-8")
        with pytest.raises(DofMismatchError, match="TÊN tier_b"):
            assert_dof_or_block(config_path=CFG_THAT, inventory_path=p)


# ════ (i) L-Z15 — TUNED có trial ════


def _prov() -> dict:
    return {
        "params_source": "yaml", "params_effective": {}, "git_sha": "a" * 40,
        "reproducible_from_sha": True, "data_hashes": {}, "cache_mode": "none", "guard_passed": True,
    }


def _status_tuned(tmp_path: Path, khoa: str, gia_tri: object, trial_ids: list[str] | None) -> tuple[Path, Path]:
    """Bản sao config thật với `khoa` = `gia_tri`, và param_status thật với
    đúng `khoa` chuyển sang TUNED."""
    cfg = _cfg_trao(tmp_path, khoa, f"  {khoa}: {gia_tri}")
    doc = yaml.safe_load((REPO_ROOT / "config" / "param_status.yaml").read_text(encoding="utf-8"))
    muc = doc["params"][khoa]
    muc["status"] = "TUNED"
    muc["value"] = gia_tri
    muc["chua_calibrate"] = False
    muc.pop("frozen_rationale", None)
    if trial_ids is not None:
        muc["trial_ids"] = trial_ids
    st = tmp_path / "status.yaml"
    st.write_text(yaml.safe_dump(doc, allow_unicode=True), encoding="utf-8")
    return cfg, st


def _so_b1(tmp_path: Path) -> tuple[TrialLedger, Path]:
    reg = tmp_path / "reg.jsonl"
    state = tmp_path / "runtime_state.json"
    state.write_text(json.dumps({"d4_complete": True}), encoding="utf-8")
    return TrialLedger(reg, dr_d5_path=DR_THAT, runtime_state_path=state), reg


def _tieu_thu_b1(ledger: TrialLedger, khoa: str, gia_tri: object) -> str:
    tid = ledger.reserve(
        n_dang_ky=114, budget_line="B1", hypothesis_slot="D5", direction="LONG", dataset="CALIB",
        param_under_test=khoa, param_value=gia_tri, params_frozen_hash="f", config_hash="c",
        code_commit="a" * 40, provenance=_prov(), contribution=1,
    )
    ledger.seal(tid, seal_path=f"runs/{tid}/metrics.seal")
    return tid


class TestTunedCoBangChung:
    def test_file_that_hien_tai_van_DAT(self) -> None:
        """Chưa tham số nào TUNED ⇒ phần (i) không đổi kết quả trên file thật."""
        assert check_lz15_calibrate_params_have_status().ok

    def test_TUNED_khong_trial_ids_la_FAIL(self, tmp_path: Path) -> None:
        cfg, st = _status_tuned(tmp_path, "zss_threshold", 0.4, None)
        r = check_lz15_calibrate_params_have_status(cfg, st, tmp_path / "reg.jsonl")
        assert r.is_fail and "không có trial_ids" in r.evidence

    def test_TUNED_tro_toi_trial_khong_ton_tai_la_FAIL(self, tmp_path: Path) -> None:
        cfg, st = _status_tuned(tmp_path, "zss_threshold", 0.4, ["D-9999"])
        r = check_lz15_calibrate_params_have_status(cfg, st, tmp_path / "reg.jsonl")
        assert r.is_fail and "không có trong sổ" in r.evidence

    def test_TUNED_khop_suat_B1_CONSUMED_la_DAT(self, tmp_path: Path) -> None:
        ledger, reg = _so_b1(tmp_path)
        tid = _tieu_thu_b1(ledger, "zss_threshold", 0.4)
        cfg, st = _status_tuned(tmp_path, "zss_threshold", 0.4, [tid])
        r = check_lz15_calibrate_params_have_status(cfg, st, reg)
        assert r.ok, r.evidence
        assert "1 đã TUNED" in r.evidence

    def test_TUNED_gia_tri_config_khac_suat_da_thu_la_FAIL(self, tmp_path: Path) -> None:
        """Suất thử 0,4 nhưng config đang chạy 0,6 — lời khai TUNED trỏ nhầm bằng chứng."""
        ledger, reg = _so_b1(tmp_path)
        tid = _tieu_thu_b1(ledger, "zss_threshold", 0.4)
        cfg, st = _status_tuned(tmp_path, "zss_threshold", 0.6, [tid])
        r = check_lz15_calibrate_params_have_status(cfg, st, reg)
        assert r.is_fail and "không phải zss_threshold=0.6" in r.evidence

    def test_TUNED_tro_toi_suat_chua_CONSUMED_la_FAIL(self, tmp_path: Path) -> None:
        ledger, reg = _so_b1(tmp_path)
        tid = ledger.reserve(
            n_dang_ky=114, budget_line="B1", hypothesis_slot="D5", direction="LONG", dataset="CALIB",
            param_under_test="zss_threshold", param_value=0.4, params_frozen_hash="f", config_hash="c",
            code_commit="a" * 40, provenance=_prov(), contribution=1,
        )
        cfg, st = _status_tuned(tmp_path, "zss_threshold", 0.4, [tid])
        r = check_lz15_calibrate_params_have_status(cfg, st, reg)
        assert r.is_fail and "RESERVED" in r.evidence
