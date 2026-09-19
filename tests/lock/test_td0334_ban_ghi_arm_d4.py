"""TD-0334 (`DR-D4-14`) — test khoá cho `ablation/ban_ghi.py`.

Canh:
1. Lô D4 = đúng bốn arm `DR-D4-12` §4.1, ghim kèm DR.
2. Chỉ số tính trên `R_trien_khai` (đơn vị phán quyết, `DR-D4-12` §1), không trên
   `R_ngan_sach` — hai thang cho ra con số KHÁC nhau trên cùng lệnh, nên nhầm là bắt được.
3. `n < 2` / `n = 0` ⇒ `unreadable`, không `0.0` (N6).
4. Kết cục: `Z0-T1` phán quyết; arm mô tả ra PASS ⇒ bị từ chối; nhóm C ra khác
   INCONCLUSIVE ⇒ cờ đỏ tầng đo (`DR-D4-10` §2.2).
5. Đầu ra THẬT khớp `arm_result.schema.json` — bài học TD-0130: suite xanh không chứng
   minh cửa ghi và schema đồng ý với nhau nếu không có test bắt chúng nhìn nhau.
"""

from __future__ import annotations

import json
import math
from datetime import date, datetime
from pathlib import Path

import jsonschema
import pytest

from tool_d.ablation.ban_ghi import (
    LO_ARM_D4,
    BanGhiArmError,
    co_do_nhom_c,
    doc_pham_vi_delta_r,
    dung_ban_ghi_arm,
    lenh_theo_thang,
    thong_ke_arm,
)
from tool_d.gates.arm_record import ArmRecordError, validate_arm_record
from tool_d.gates.ket_cuc import thue_nhieu
from tool_d.measurement.provenance import Provenance
from tool_d.measurement.tri_state import Measured, Status
from tool_d.wfo.folds import Fold
from tool_d.wfo.lenh import LenhWFO

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((REPO_ROOT / "registry/schemas/arm_result.schema.json").read_text(encoding="utf-8"))

CUA_SO = (date(2025, 6, 12), date(2026, 1, 28))
FOLDS = (
    Fold(1, date(2025, 6, 12), date(2025, 9, 4), date(2025, 9, 4), date(2025, 10, 23)),
    Fold(2, date(2025, 6, 12), date(2025, 10, 23), date(2025, 10, 23), date(2025, 12, 11)),
    Fold(3, date(2025, 6, 12), date(2025, 12, 11), date(2025, 12, 11), date(2026, 1, 29)),
)
DELTA_R = {"so_ma": 2, "so_fill": 91, "dataset": "CALIB", "chien_luoc": "ZoneAbsorptionMinimal"}


def _prov() -> Provenance:
    return Provenance(
        params_source="yaml",
        params_effective={"tier_c.arm_ablation.arm": "Z0-T1"},
        git_sha="deadbeef",
        reproducible_from_sha=True,
        data_hashes={"x": "sha256:" + "0" * 64},
        cache_mode="none",
        guard_passed=True,
        runtime_image_digest="sha256:" + "a" * 64,
    )


def _l(ngay: datetime, pnl: float, *, rui_ro: float = 2.0, ke_hoach: float = 4.0) -> LenhWFO:
    return LenhWFO(
        pair="LTC/USDT:USDT",
        open_date=ngay,
        close_date=ngay,
        pnl_abs=pnl,
        rui_ro_da_trien_khai_usdt=rui_ro,
        planned_risk_usdt=ke_hoach,
    )


# Hai lệnh trong đoạn train-only (trước 2025-09-04), bốn lệnh trong đoạn test.
LENH = [
    _l(datetime(2025, 7, 1), 2.0),
    _l(datetime(2025, 8, 15), -2.0),
    _l(datetime(2025, 9, 10), 4.0),
    _l(datetime(2025, 11, 2), -1.0),
    _l(datetime(2025, 12, 20), 3.0),
    _l(datetime(2026, 1, 5), -2.0),
]


def _ban_ghi(arm: str = "Z0-T1", lenhs=LENH, nguong: float = 0.10) -> dict:
    return dung_ban_ghi_arm(
        arm=arm,
        lenhs=lenhs,
        cua_so=CUA_SO,
        folds=FOLDS,
        so_ma_da_chay=107,
        delta_r_pham_vi=DELTA_R,
        provenance=_prov(),
        trial_id="D-0014",
        nguong=nguong,
    )


class TestLoArm:
    def test_lo_d4_dung_bon_arm_DR_D4_12(self) -> None:
        assert LO_ARM_D4 == ("Z0-T1", "Z0", "Z0-T0", "Z3"), (
            "Lô D4 = 4/9 arm theo DR-D4-12 §4.1. Đổi lô là một QUYẾT ĐỊNH cần DR "
            "(DR-D4-12 §4.4), không phải sửa test cho xanh."
        )


class TestChiSo:
    def test_tinh_tren_R_trien_khai_khong_phai_R_ngan_sach(self) -> None:
        chi_so, _, _ = thong_ke_arm(LENH)
        r = [l.pnl_abs / 2.0 for l in LENH]
        m = sum(r) / len(r)
        s = math.sqrt(sum((x - m) ** 2 for x in r) / (len(r) - 1))
        assert chi_so["mean_r"].value == pytest.approx(m)
        assert chi_so["std_r"].value == pytest.approx(s)
        # R ngân sách báo CẠNH BÊN, mẫu số khác ⇒ con số khác.
        assert chi_so["mean_r_ngan_sach"].value == pytest.approx(m / 2)
        assert chi_so["ty_le_rui_ro_da_trien_khai"].value == pytest.approx(0.5)
        assert chi_so["thue_nhieu"].value == pytest.approx(thue_nhieu(std_r=s, n_trades=6))
        assert chi_so["dsr_adj"].value == pytest.approx(m - chi_so["thue_nhieu"].value)

    def test_n_mot_thi_unreadable_khong_phai_khong(self) -> None:
        chi_so, kc, pl = thong_ke_arm(LENH[:1])
        assert pl is None and kc.status is Status.UNREADABLE
        for k in ("std_r", "thue_nhieu", "dsr_adj"):
            assert chi_so[k].status is Status.UNREADABLE and chi_so[k].value is None
        assert chi_so["mean_r"].status is Status.OK

    def test_n_khong(self) -> None:
        chi_so, kc, _ = thong_ke_arm([])
        assert kc.status is Status.UNREADABLE
        assert all(m.value is None for m in chi_so.values())

    def test_lenh_theo_thang(self) -> None:
        assert lenh_theo_thang(LENH) == {
            "2025-07": 1, "2025-08": 1, "2025-09": 1, "2025-11": 1, "2025-12": 1, "2026-01": 1,
        }


class TestBanGhi:
    def test_hop_le_va_khop_schema(self) -> None:
        bg = _ban_ghi()
        assert validate_arm_record(bg) == []
        jsonschema.validate(bg, SCHEMA)

    def test_n_chi_test_dem_theo_fold(self) -> None:
        bg = _ban_ghi()
        assert (bg["n_toan_cua_so"], bg["n_chi_test"]) == (6, 4)

    def test_Z0_T1_phan_quyet_ba_arm_con_lai_mo_ta(self) -> None:
        # ngưỡng cao ⇒ không arm nào PASS được; ca này chỉ kiểm cờ phạm vi.
        assert _ban_ghi("Z0-T1", nguong=10.0)["pham_vi_phan_quyet"] == "phan_quyet"
        for arm in ("Z0", "Z0-T0", "Z3"):
            assert _ban_ghi(arm, nguong=10.0)["pham_vi_phan_quyet"] == "mo_ta"

    def test_arm_mo_ta_ra_PASS_bi_tu_choi(self) -> None:
        # ngưỡng âm rất sâu ⇒ phan_loai ra PASS ⇒ arm mô tả KHÔNG biểu diễn được.
        assert _ban_ghi("Z0-T1", nguong=-100.0)["ket_cuc"]["value"] == "PASS"
        with pytest.raises(ArmRecordError, match="mo_ta"):
            _ban_ghi("Z0-T0", nguong=-100.0)

    def test_khong_lenh_thi_tu_choi_voi_ly_do(self) -> None:
        with pytest.raises(BanGhiArmError, match="KHÔNG ĐO ĐƯỢC"):
            _ban_ghi(lenhs=[])

    def test_short_bi_tu_choi(self) -> None:
        with pytest.raises(BanGhiArmError, match="Long-only"):
            dung_ban_ghi_arm(
                arm="Z0", lenhs=LENH, cua_so=CUA_SO, folds=FOLDS, so_ma_da_chay=1,
                delta_r_pham_vi=DELTA_R, provenance=_prov(), trial_id="D-1", huong="SHORT",
            )


class TestCoDoNhomC:
    def test_inconclusive_khong_co_co(self) -> None:
        assert co_do_nhom_c("Z3", Measured.ok("INCONCLUSIVE")) is None

    def test_fail_o_nhom_c_la_co_do(self) -> None:
        assert "N10" in co_do_nhom_c("Z0", Measured.ok("FAIL"))

    def test_arm_ngoai_nhom_c_khong_ap(self) -> None:
        assert co_do_nhom_c("Z0-T1", Measured.ok("FAIL")) is None
        assert co_do_nhom_c("Z0-T0", Measured.ok("FAIL")) is None

    def test_unreadable_khong_co_co(self) -> None:
        assert co_do_nhom_c("Z3", Measured.unreadable("n<2")) is None


class TestPhamViDeltaR:
    def test_doc_tu_artifact_that(self) -> None:
        assert doc_pham_vi_delta_r() == {
            "so_ma": 2, "so_fill": 91, "dataset": "CALIB", "chien_luoc": "ZoneAbsorptionMinimal",
        }

    def test_file_hong_thi_raise(self, tmp_path) -> None:
        p = tmp_path / "x.json"
        p.write_text("{}", encoding="utf-8")
        with pytest.raises(BanGhiArmError):
            doc_pham_vi_delta_r(p)
