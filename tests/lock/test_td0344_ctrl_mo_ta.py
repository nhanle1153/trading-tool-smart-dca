"""TD-0344 (`MT-19` đường (c), `DR-D4-16` §3) — dạng CTRL thứ BA *đo mô tả*.

Canh đúng ba ràng buộc `MT-19` tự viết ra:
1. Allowlist **đích danh** (`CTRL_MO_TA_ALLOWED`) — tên ngoài danh sách ⇒ TỪ CHỐI; danh sách D3.5 (`CTRL_OUTPUT_ALLOWED`)
   **không đổi một chữ**.
2. 🔴 **Khai chồng bất kỳ hai dạng ⇒ TỪ CHỐI.** `MT-19`: ba phép kiểm cũ là NHỊ PHÂN — thêm trường mà không đổi chúng thì
   khai chồng với `ctrl_output_whitelist` sẽ QUA và danh sách mô tả bị bỏ qua IM LẶNG.
3. Đầu ra THẬT của `reserve()` khớp `trial_event.schema.json` (bài học TD-0130/TD-0149: suite xanh không chứng minh cửa ghi
   và schema đồng ý với nhau nếu không có test bắt chúng nhìn nhau). CTRL dạng 3 không vào N.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from tool_d.ledger.registry import (
    CTRL_MO_TA_ALLOWED,
    CTRL_OUTPUT_ALLOWED,
    CtrlClaimError,
    TrialLedger,
)

REPO = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((REPO / "registry/schemas/trial_event.schema.json").read_text(encoding="utf-8"))
MO_TA = ["so_lenh", "lenh_moi_nam", "so_lenh_theo_thang", "so_ma_co_lenh", "phan_bo_so_tranche"]


def _kw(**them) -> dict:
    kw = dict(
        n_dang_ky=114, budget_line="CTRL", hypothesis_slot="TD-0345", direction="LONG", dataset="WFO",
        param_under_test="tier_c.arm_ablation.arm", param_value="Z0-T1", params_frozen_hash="fh", config_hash="ch",
        code_commit="abc123",
        provenance={"params_source": "yaml", "params_effective": {}, "git_sha": "a" * 40, "reproducible_from_sha": True,
                    "data_hashes": {}, "cache_mode": "none", "guard_passed": True},
        contribution=1,
    )
    kw.update(them)
    return kw


def _su_kien(p: Path) -> list[dict]:
    return [json.loads(d) for d in p.read_text(encoding="utf-8").splitlines() if d.strip()]


class TestDanhSach:
    def test_allowlist_dich_danh_DR_D4_16(self) -> None:
        assert CTRL_MO_TA_ALLOWED == frozenset(MO_TA), (
            "Allowlist đo mô tả ghim theo DR-D4-16 §3. Thêm tên = DR mới, không phải sửa test cho xanh."
        )

    def test_danh_sach_D35_khong_doi_mot_chu(self) -> None:
        assert CTRL_OUTPUT_ALLOWED == frozenset({"price_delta", "tranche_index", "direction"})

    def test_hai_danh_sach_khong_giao_nhau(self) -> None:
        assert not (CTRL_MO_TA_ALLOWED & CTRL_OUTPUT_ALLOWED)

    def test_schema_cung_danh_sach_voi_ma(self) -> None:
        """Schema và mã là hai nơi giữ một danh sách — phải trùng tập, không chỉ "có mặt"."""

        def tim(nut):
            if isinstance(nut, dict):
                if "ctrl_mo_ta_whitelist" in nut:
                    return nut["ctrl_mo_ta_whitelist"]
                for v in nut.values():
                    r = tim(v)
                    if r is not None:
                        return r
            elif isinstance(nut, list):
                for v in nut:
                    r = tim(v)
                    if r is not None:
                        return r
            return None

        nut = tim(SCHEMA)
        assert nut is not None, "schema không có khoá ctrl_mo_ta_whitelist"
        assert set(nut["items"]["enum"]) == set(CTRL_MO_TA_ALLOWED)


class TestNhan:
    def test_khai_mot_minh_dang_3_duoc_ghi_va_khop_schema(self, tmp_path) -> None:
        so = TrialLedger(path=tmp_path / "so.jsonl")
        tid = so.reserve(**_kw(ctrl_mo_ta_whitelist=MO_TA))
        e = _su_kien(tmp_path / "so.jsonl")[0]
        assert e["trial_id"] == tid and e["ctrl_mo_ta_whitelist"] == MO_TA
        assert "ctrl_output_whitelist" not in e and "reproduces_trial_id" not in e
        jsonschema.validate(e, SCHEMA)

    def test_ctrl_dang_3_khong_vao_N(self, tmp_path) -> None:
        so = TrialLedger(path=tmp_path / "so.jsonl")
        tid = so.reserve(**_kw(ctrl_mo_ta_whitelist=["so_lenh"]))
        so.seal(tid, seal_path=f"runs/{tid}/metrics.seal")
        so.consume(tid, outcome={"expectancy": None, "sharpe": None, "n_trades": 10, "max_single_loss_ratio": None},
                   verdict="INCONCLUSIVE")
        assert so.n_used() == 0


class TestTuChoi:
    @pytest.mark.parametrize("ten", ["profit_abs", "exit_reason", "win_rate", "mean_r", "price_delta"])
    def test_ten_ngoai_allowlist(self, tmp_path, ten) -> None:
        with pytest.raises(CtrlClaimError, match="ngoài danh sách"):
            TrialLedger(path=tmp_path / "so.jsonl").reserve(**_kw(ctrl_mo_ta_whitelist=["so_lenh", ten]))

    def test_danh_sach_rong(self, tmp_path) -> None:
        with pytest.raises(CtrlClaimError, match="RỖNG"):
            TrialLedger(path=tmp_path / "so.jsonl").reserve(**_kw(ctrl_mo_ta_whitelist=[]))

    @pytest.mark.parametrize(
        "chong",
        [
            {"ctrl_output_whitelist": ["price_delta"]},
            {"reproduces_trial_id": "D-0001"},
            {"ctrl_output_whitelist": ["price_delta"], "reproduces_trial_id": "D-0001"},
        ],
    )
    def test_khai_chong_voi_dang_khac_thi_TU_CHOI(self, tmp_path, chong) -> None:
        """Ràng buộc MT-19 — nếu nhánh chặn khai chồng vắng, ca `ctrl_output_whitelist` sẽ QUA ở nhánh đo thước và
        danh sách mô tả bị bỏ qua IM LẶNG."""
        p = tmp_path / "so.jsonl"
        with pytest.raises(CtrlClaimError, match="CHỒNG"):
            TrialLedger(path=p).reserve(**_kw(ctrl_mo_ta_whitelist=["so_lenh"], **chong))
        assert not p.exists() or p.read_text(encoding="utf-8").strip() == ""

    def test_khong_khai_dang_nao_thi_liet_ke_BA_dang(self, tmp_path) -> None:
        with pytest.raises(CtrlClaimError, match="BA dạng"):
            TrialLedger(path=tmp_path / "so.jsonl").reserve(**_kw())
