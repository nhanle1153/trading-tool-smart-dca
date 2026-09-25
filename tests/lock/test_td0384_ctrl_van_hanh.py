"""TD-0384 (`DR-D10-02` §5.3) — dạng CTRL thứ TƯ *đo vận hành*: MỘT dòng cho cả đợt D10.

Canh bốn ràng buộc, cùng khuôn `test_td0344_ctrl_mo_ta.py` (dạng thứ ba):
1. Allowlist ĐÍCH DANH `CTRL_VAN_HANH_ALLOWED` = bốn tên của `DR-D10-02` §2 mục 6; ba danh sách cũ KHÔNG đổi một chữ.
2. Khai chồng với bất kỳ dạng nào ⇒ TỪ CHỐI (đếm số dạng, không so cặp — `MT-19`).
3. Chỉ dành cho D10 (`hypothesis_slot = "D10"`, `dataset = "N/A"`) và tối đa MỘT dòng D10 đang mở.
4. Đầu ra THẬT của `reserve()` khớp `trial_event.schema.json`; dòng CTRL này không vào N.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from tool_d.ledger.registry import (
    CTRL_MO_TA_ALLOWED,
    CTRL_OUTPUT_ALLOWED,
    CTRL_VAN_HANH_ALLOWED,
    CtrlClaimError,
    TrialLedger,
)

REPO = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((REPO / "registry/schemas/trial_event.schema.json").read_text(encoding="utf-8"))
VAN_HANH = ["fill_price", "gap_ms", "order_status", "p_i"]
KET_CUC = {"expectancy": None, "sharpe": None, "n_trades": None, "max_single_loss_ratio": None}


def _kw(**them) -> dict:
    kw = dict(
        n_dang_ky=114, budget_line="CTRL", hypothesis_slot="D10", direction="LONG", dataset="N/A",
        param_under_test="d10_ha_tang", param_value={"ro": ["DOGE/USDT:USDT"]}, params_frozen_hash="fh",
        config_hash="ch", code_commit="abc123",
        provenance={"params_source": "yaml", "params_effective": {}, "git_sha": "a" * 40, "reproducible_from_sha": True,
                    "data_hashes": {}, "cache_mode": "none", "guard_passed": True},
        contribution=1,
    )
    kw.update(them)
    return kw


def _su_kien(p: Path) -> list[dict]:
    return [json.loads(d) for d in p.read_text(encoding="utf-8").splitlines() if d.strip()]


class TestDanhSach:
    def test_allowlist_dich_danh_dr_d10_02(self) -> None:
        assert CTRL_VAN_HANH_ALLOWED == frozenset(VAN_HANH), "Thêm tên = DR mới, không phải sửa test cho xanh."

    def test_ba_danh_sach_cu_khong_doi_mot_chu(self) -> None:
        assert CTRL_OUTPUT_ALLOWED == frozenset({"price_delta", "tranche_index", "direction"})
        assert CTRL_MO_TA_ALLOWED == frozenset(
            {"so_lenh", "lenh_moi_nam", "so_lenh_theo_thang", "so_ma_co_lenh", "phan_bo_so_tranche"}
        )

    def test_khong_giao_nhau_voi_danh_sach_khac(self) -> None:
        assert not (CTRL_VAN_HANH_ALLOWED & (CTRL_OUTPUT_ALLOWED | CTRL_MO_TA_ALLOWED))

    def test_schema_cung_danh_sach_voi_ma(self) -> None:
        """Schema và mã là hai nơi giữ một danh sách — phải trùng TẬP, không chỉ "có mặt"."""
        nut = next((v["ctrl_van_hanh_whitelist"] for v in _tat_ca_dict(SCHEMA) if "ctrl_van_hanh_whitelist" in v), None)
        assert nut is not None, "schema không có khoá ctrl_van_hanh_whitelist"
        assert set(nut["items"]["enum"]) == set(CTRL_VAN_HANH_ALLOWED)


def _tat_ca_dict(nut):
    if isinstance(nut, dict):
        yield nut
        for v in nut.values():
            yield from _tat_ca_dict(v)
    elif isinstance(nut, list):
        for v in nut:
            yield from _tat_ca_dict(v)


class TestNhan:
    def test_dong_d10_duoc_ghi_va_khop_schema(self, tmp_path) -> None:
        so = TrialLedger(path=tmp_path / "so.jsonl")
        tid = so.reserve(**_kw(ctrl_van_hanh_whitelist=VAN_HANH))
        e = _su_kien(tmp_path / "so.jsonl")[0]
        assert e["trial_id"] == tid and e["ctrl_van_hanh_whitelist"] == VAN_HANH
        assert not {"ctrl_output_whitelist", "ctrl_mo_ta_whitelist", "reproduces_trial_id"} & set(e)
        jsonschema.validate(e, SCHEMA)

    def test_khong_vao_N(self, tmp_path) -> None:
        so = TrialLedger(path=tmp_path / "so.jsonl")
        tid = so.reserve(**_kw(ctrl_van_hanh_whitelist=["gap_ms"]))
        so.consume(tid, outcome=KET_CUC, verdict="INCONCLUSIVE")
        assert so.n_used() == 0

    def test_dong_truoc_da_consume_thi_dot_moi_duoc_mo(self, tmp_path) -> None:
        so = TrialLedger(path=tmp_path / "so.jsonl")
        tid = so.reserve(**_kw(ctrl_van_hanh_whitelist=["gap_ms"]))
        so.consume(tid, outcome=KET_CUC, verdict="INCONCLUSIVE")
        so.reserve(**_kw(ctrl_van_hanh_whitelist=["gap_ms"], param_value={"ro": ["XRP/USDT:USDT"]}))


class TestTuChoi:
    @pytest.mark.parametrize("ten", ["pnl_abs", "profit_ratio", "win_rate", "expectancy"])
    def test_ten_ngoai_allowlist(self, tmp_path, ten) -> None:
        with pytest.raises(CtrlClaimError, match="ngoài danh sách"):
            TrialLedger(path=tmp_path / "so.jsonl").reserve(**_kw(ctrl_van_hanh_whitelist=["gap_ms", ten]))

    def test_danh_sach_rong(self, tmp_path) -> None:
        with pytest.raises(CtrlClaimError, match="RỖNG"):
            TrialLedger(path=tmp_path / "so.jsonl").reserve(**_kw(ctrl_van_hanh_whitelist=[]))

    @pytest.mark.parametrize(
        "chong",
        [{"ctrl_output_whitelist": ["price_delta"]}, {"ctrl_mo_ta_whitelist": ["so_lenh"]}],
        ids=["chong-do-thuoc", "chong-mo-ta"],
    )
    def test_khai_chong_thi_tu_choi(self, tmp_path, chong) -> None:
        with pytest.raises(CtrlClaimError, match="CHỒNG"):
            TrialLedger(path=tmp_path / "so.jsonl").reserve(**_kw(ctrl_van_hanh_whitelist=["gap_ms"], **chong))

    @pytest.mark.parametrize("ghi_de", [{"hypothesis_slot": "TD-0345"}, {"dataset": "WFO"}], ids=["slot", "dataset"])
    def test_chi_danh_cho_d10(self, tmp_path, ghi_de) -> None:
        with pytest.raises(CtrlClaimError, match="chỉ dành cho D10"):
            TrialLedger(path=tmp_path / "so.jsonl").reserve(**_kw(ctrl_van_hanh_whitelist=["gap_ms"], **ghi_de))

    def test_dong_d10_thu_hai_khi_dong_truoc_con_mo(self, tmp_path) -> None:
        so = TrialLedger(path=tmp_path / "so.jsonl")
        so.reserve(**_kw(ctrl_van_hanh_whitelist=["gap_ms"]))
        with pytest.raises(CtrlClaimError, match="đang mở"):
            so.reserve(**_kw(ctrl_van_hanh_whitelist=["gap_ms"], param_value={"ro": ["XRP/USDT:USDT"]}))
        assert len(_su_kien(tmp_path / "so.jsonl")) == 1  # sổ không đổi dòng nào

    def test_khong_khai_dang_nao_van_liet_ke_ca_dang_van_hanh(self, tmp_path) -> None:
        with pytest.raises(CtrlClaimError, match="đo vận hành"):
            TrialLedger(path=tmp_path / "so.jsonl").reserve(**_kw())
