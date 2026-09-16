"""🔒 TD-0284 — suất B1 trên WFO cho D9, chặn TẠI CỬA `reserve()` (`DR-D9-01` §3, §3.1, §6.1).

Chủ dự án chốt 17/09/2026 phương án (a): nhãn giữ `B1`, phân biệt bằng `dataset`.
Bảng rủi ro §3.1 chỉ ra ĐÚNG hai chỗ (a) phải sửa, mỗi chỗ một ca có răng ở đây:
- `ung_vien.py` đếm trần 16 của D5 — suất WFO KHÔNG được ăn vào trần đó;
- `audit_checks.py` L-Z15 — suất WFO KHÔNG được làm bằng chứng TUNED.

Mỗi ca từ chối khẳng định CẢ raise LẪN sổ không thêm dòng (khuôn TD-0253).
Nhánh CALIB giữ nguyên: `test_td0253_*` không đổi một khẳng định nào.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from tool_d.calibration.ung_vien import PARAM_MOC, PARAM_XAC_NHAN
from tool_d.ledger.audit_checks import check_lz15_calibrate_params_have_status
from tool_d.ledger.registry import B1Error, TrialLedger

REPO_ROOT = Path(__file__).resolve().parents[2]
DR_THAT = REPO_ROOT / "docs" / "decisions" / "DR-D5-01-pham-vi-ung-vien-luat-chon-calibration.md"
CFG_THAT = REPO_ROOT / "config" / "tool_d_config.yaml"


def _prov() -> dict:
    return {
        "params_source": "yaml", "params_effective": {}, "git_sha": "a" * 40,
        "reproducible_from_sha": True, "data_hashes": {}, "cache_mode": "none", "guard_passed": True,
    }


def _so(tmp_path: Path, *, d5: bool | None = True) -> tuple[TrialLedger, Path, Path]:
    reg = tmp_path / "reg.jsonl"
    state = tmp_path / "runtime_state.json"
    khoa = {"d4_complete": True, **({} if d5 is None else {"d5_complete": d5})}
    state.write_text(json.dumps(khoa), encoding="utf-8")
    return TrialLedger(reg, dr_d5_path=DR_THAT, runtime_state_path=state), reg, state


def _kw(**doi) -> dict:
    kw = dict(
        n_dang_ky=114, budget_line="B1", hypothesis_slot="D9", direction="LONG", dataset="WFO",
        param_under_test="zss_threshold", param_value=0.4, params_frozen_hash="f", config_hash="c",
        code_commit="a" * 40, provenance=_prov(), contribution=1,
    )
    kw.update(doi)
    return kw


def _calib(ledger: TrialLedger, khoa: str, gia_tri: object, *, seal: bool = True) -> str:
    tid = ledger.reserve(**_kw(hypothesis_slot="D5", dataset="CALIB", param_under_test=khoa, param_value=gia_tri))
    if seal:
        ledger.seal(tid, seal_path=f"runs/{tid}/metrics.seal")
    return tid


def _so_dong(reg: Path) -> int:
    return len([d for d in reg.read_text(encoding="utf-8").splitlines() if d.strip()]) if reg.exists() else 0


def _tu_choi(ledger: TrialLedger, reg: Path, match: str, **doi) -> None:
    truoc = _so_dong(reg)
    with pytest.raises(B1Error, match=match):
        ledger.reserve(**_kw(**doi))
    assert _so_dong(reg) == truoc, "TỪ CHỐI mà vẫn ghi sổ — cửa không chặn gì"


class TestDuongHopLe:
    def test_cau_hinh_calib_consumed_duoc_mot_suat_wfo(self, tmp_path: Path) -> None:
        ledger, reg, _ = _so(tmp_path)
        _calib(ledger, PARAM_MOC, None)
        _calib(ledger, "zss_threshold", 0.4)
        tid = ledger.reserve(**_kw())
        p = ledger.get(tid)
        assert p.budget_line == "B1" and p.dataset == "WFO"
        ledger.reserve(**_kw(param_under_test=PARAM_MOC, param_value=None))
        assert _so_dong(reg) == 2 + 2 + 2  # 2 RESERVE+SEAL CALIB, 2 RESERVE WFO

    def test_xac_nhan_ghep_khop_dict(self, tmp_path: Path) -> None:
        ledger, _, _ = _so(tmp_path)
        _calib(ledger, PARAM_XAC_NHAN, {"zss_threshold": 0.4, "buf_sl_atr": 0.3})
        ledger.reserve(**_kw(param_under_test=PARAM_XAC_NHAN, param_value={"buf_sl_atr": 0.3, "zss_threshold": 0.4}))

    def test_n_used_dem_ca_wfo_vi_van_trong_72_dang_ky(self, tmp_path: Path) -> None:
        """B1/WFO KHÔNG phải CTRL — tiêu suất thật, vào N_ĐÃ_DÙNG khi CONSUMED."""
        ledger, _, _ = _so(tmp_path)
        _calib(ledger, "zss_threshold", 0.4)
        tid = ledger.reserve(**_kw())
        ledger.seal(tid, seal_path=f"runs/{tid}/metrics.seal")
        assert ledger.n_used() == 2


class TestTuChoiTaiCua:
    @pytest.mark.parametrize("d5", [None, False])
    def test_cong_vao_d9_chua_mo(self, tmp_path: Path, d5) -> None:
        ledger, reg, state = _so(tmp_path, d5=True)
        _calib(ledger, "zss_threshold", 0.4)
        state.write_text(json.dumps({"d4_complete": True, **({} if d5 is None else {"d5_complete": d5})}), encoding="utf-8")
        _tu_choi(ledger, reg, "d5_complete")

    def test_cau_hinh_khong_co_suat_calib(self, tmp_path: Path) -> None:
        ledger, reg, _ = _so(tmp_path)
        _calib(ledger, "zss_threshold", 0.4)
        _tu_choi(ledger, reg, "không khớp", param_value=0.6)

    def test_suat_calib_chua_consumed_khong_tinh(self, tmp_path: Path) -> None:
        """RESERVED chưa có dấu = chưa chạy trên CALIB ⇒ chưa phải cấu hình D5 đã chạy."""
        ledger, reg, _ = _so(tmp_path)
        _calib(ledger, "zss_threshold", 0.4, seal=False)
        _tu_choi(ledger, reg, "không khớp")

    def test_suat_calib_refunded_khong_tinh(self, tmp_path: Path) -> None:
        ledger, reg, _ = _so(tmp_path)
        tid = _calib(ledger, "zss_threshold", 0.4, seal=False)
        ledger.refund(tid, cause_machine="OS_KILL:SIGKILL")
        _tu_choi(ledger, reg, "không khớp")

    def test_trung_suat_wfo(self, tmp_path: Path) -> None:
        ledger, reg, _ = _so(tmp_path)
        _calib(ledger, "zss_threshold", 0.4)
        _calib(ledger, PARAM_MOC, None)
        ledger.reserve(**_kw())
        _tu_choi(ledger, reg, "trùng suất WFO")

    def test_tran_wfo_tang_theo_so_suat_calib(self, tmp_path: Path) -> None:
        """Trần WFO = số suất CALIB CONSUMED, không phải hằng 16: 3 CALIB ⇒ đủ 3 WFO; thêm
        CALIB thứ tư ⇒ WFO thứ tư qua. Ca trần THẬT SỰ CHẶN ở `test_wfo_nhieu_hon_calib_bi_chan`."""
        ledger, reg, _ = _so(tmp_path)
        _calib(ledger, "zss_threshold", 0.4)
        _calib(ledger, PARAM_MOC, None)
        _calib(ledger, "buf_sl_atr", 0.3)
        ledger.reserve(**_kw())
        ledger.reserve(**_kw(param_under_test=PARAM_MOC, param_value=None))
        ledger.reserve(**_kw(param_under_test="buf_sl_atr", param_value=0.3))
        assert _so_dong(reg) == 9
        # 3 WFO = 3 CALIB. Thêm một cấu hình CALIB mới ⇒ trần 4 ⇒ WFO thứ tư qua:
        _calib(ledger, "buf_sl_atr", 0.5)
        ledger.reserve(**_kw(param_under_test="buf_sl_atr", param_value=0.5))

    def test_wfo_nhieu_hon_calib_bi_chan(self, tmp_path: Path) -> None:
        """Trần thật sự chặn: ghi TAY một dòng WFO thứ hai (đi vòng cửa, như một sổ bị sửa)
        rồi đặt suất hợp lệ ⇒ 2 WFO ≥ 1 CALIB ⇒ từ chối."""
        ledger, reg, _ = _so(tmp_path)
        _calib(ledger, "zss_threshold", 0.4)
        _calib(ledger, PARAM_MOC, None)
        ledger.reserve(**_kw(param_under_test=PARAM_MOC, param_value=None))
        dong = json.loads(reg.read_text(encoding="utf-8").splitlines()[-1])
        dong.update(trial_id="D-9000", param_under_test="v_min", param_value=1.5)
        with reg.open("a", encoding="utf-8") as f:
            f.write(json.dumps(dong, ensure_ascii=False) + "\n")
        _tu_choi(ledger, reg, "trần")

    def test_short(self, tmp_path: Path) -> None:
        ledger, reg, _ = _so(tmp_path)
        _calib(ledger, "zss_threshold", 0.4)
        _tu_choi(ledger, reg, "chỉ hướng", direction="SHORT")

    @pytest.mark.parametrize("ds", ["LOCKBOX", "N/A"])
    def test_tap_khac_van_bi_tu_choi(self, tmp_path: Path, ds: str) -> None:
        ledger, reg, _ = _so(tmp_path)
        _calib(ledger, "zss_threshold", 0.4)
        _tu_choi(ledger, reg, "CALIB", dataset=ds)


class TestHaiChoPhaiSuaCuaPhuongAnA:
    def test_suat_wfo_khong_an_vao_tran_16_cua_d5(self, tmp_path: Path) -> None:
        """Chỗ 1 (`ung_vien.py`): 8 CALIB + 8 WFO = 16 suất B1 chưa hoàn trả. Nếu trần D5 đếm
        gộp thì suất CALIB thứ 9 bị từ chối SAI; đếm riêng thì qua (8 < 16)."""
        ledger, _, _ = _so(tmp_path)
        cau_hinh = [(PARAM_MOC, None), ("zss_threshold", 0.4), ("zss_threshold", 0.6), ("buf_sl_atr", 0.3),
                    ("buf_sl_atr", 0.5), ("tp1_haircut_pct", 10), ("tp1_haircut_pct", 30), ("v_min", 0.0)]
        for k, v in cau_hinh:
            _calib(ledger, k, v)
        for k, v in cau_hinh:
            ledger.reserve(**_kw(param_under_test=k, param_value=v))
        _calib(ledger, "v_min", 1.5)

    def test_suat_wfo_khong_lam_bang_chung_tuned(self, tmp_path: Path) -> None:
        """Chỗ 2 (`audit_checks.py` L-Z15): TUNED trỏ tới suất B1 **WFO** CONSUMED ⇒ FAIL."""
        ledger, reg, _ = _so(tmp_path)
        _calib(ledger, "zss_threshold", 0.4)
        tid_wfo = ledger.reserve(**_kw())
        ledger.seal(tid_wfo, seal_path=f"runs/{tid_wfo}/metrics.seal")
        cfg, st = _status_tuned(tmp_path, "zss_threshold", 0.4, [tid_wfo])
        r = check_lz15_calibrate_params_have_status(cfg, st, reg)
        assert r.is_fail and "B1/WFO/CONSUMED" in r.evidence

    def test_suat_calib_van_la_bang_chung_hop_le(self, tmp_path: Path) -> None:
        ledger, reg, _ = _so(tmp_path)
        tid = _calib(ledger, "zss_threshold", 0.4)
        cfg, st = _status_tuned(tmp_path, "zss_threshold", 0.4, [tid])
        assert check_lz15_calibrate_params_have_status(cfg, st, reg).ok


def _status_tuned(tmp_path: Path, khoa: str, gia_tri: object, trial_ids: list[str]) -> tuple[Path, Path]:
    """Cùng khuôn `test_td0256_*::_status_tuned`: config thật với `khoa` = `gia_tri`,
    param_status thật với đúng `khoa` chuyển sang TUNED."""
    import re

    text, n = re.subn(rf"^  {khoa}: .*$", f"  {khoa}: {gia_tri}", CFG_THAT.read_text(encoding="utf-8"), count=1, flags=re.M)
    assert n == 1
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text(text, encoding="utf-8")
    doc = yaml.safe_load((REPO_ROOT / "config" / "param_status.yaml").read_text(encoding="utf-8"))
    muc = doc["params"][khoa]
    muc.update(status="TUNED", value=gia_tri, chua_calibrate=False, trial_ids=trial_ids)
    muc.pop("frozen_rationale", None)
    st = tmp_path / "status.yaml"
    st.write_text(yaml.safe_dump(doc, allow_unicode=True), encoding="utf-8")
    return cfg, st
