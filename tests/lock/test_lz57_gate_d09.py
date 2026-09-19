"""L-Z57 🔴 CRITICAL (spec `:3979-3981`) + TD-0336 — GATE D0.9 §10.2, phần dựng.

    L-Z57 — Bộ kết quả giả lập "Z0 vượt trội mọi arm DCA" đưa qua GATE §10.2 → kết cục =
    "chọn Z0, dự án TIẾP TỤC", KHÔNG có đường nào dẫn tới DỪNG DỰ ÁN (khoá chống hồi quy
    về lỗi v5).

Ngoài ca đích danh của spec, file này quét TOÀN BỘ tổ hợp trạng thái (3 kết cục DSR × 3 trạng
thái cho mỗi tiêu chí trong tám = 19.683 ca) và khẳng định cho MỌI ca: dự án tiếp tục; PASS ⇔
đủ và đạt hết; FAIL ⇔ có ô đo được mà trượt. "Không có đường nào" là phát biểu về MỌI đường,
nên phép kiểm phải đi qua mọi đường chứ không chỉ một ca mẫu.
"""

from __future__ import annotations

import dataclasses
import itertools
from datetime import date, datetime

import pytest

from tool_d.ablation.ban_ghi import dung_ban_ghi_arm
from tool_d.gates.d0_9 import (
    CHI_BAO_CAO,
    TIEU_CHI_NHANH_1,
    GateD09Error,
    KetQuaGateD09,
    danh_gia_gate_d09,
)
from tool_d.gates.ket_cuc import KetCuc
from tool_d.measurement.provenance import Provenance
from tool_d.measurement.tri_state import Measured, Status
from tool_d.wfo.folds import Fold
from tool_d.wfo.lenh import LenhWFO

FOLDS = (Fold(1, date(2025, 6, 12), date(2025, 9, 4), date(2025, 9, 4), date(2026, 1, 29)),)
LENH = [
    LenhWFO("LTC/USDT:USDT", d, d, p, 2.0, 4.0)
    for d, p in (
        (datetime(2025, 7, 1), 2.0), (datetime(2025, 8, 15), -2.0), (datetime(2025, 9, 10), 4.0),
        (datetime(2025, 11, 2), -1.0), (datetime(2025, 12, 20), 3.0), (datetime(2026, 1, 5), -2.0),
    )
]
MA_KHAC = tuple(ma for ma, _ in TIEU_CHI_NHANH_1 if ma != "dsr_adj")
#: ngưỡng để phan_loai_ket_cuc ra đúng kết cục mong muốn trên LENH (thuế nhiễu ≈ 1,52).
NGUONG_CHO = {KetCuc.PASS: -100.0, KetCuc.INCONCLUSIVE: 0.10, KetCuc.FAIL: 10.0}


def _ban_ghi(arm: str = "Z0-T1", kc: KetCuc = KetCuc.PASS) -> dict:
    bg = dung_ban_ghi_arm(
        arm=arm, lenhs=LENH, cua_so=(date(2025, 6, 12), date(2026, 1, 28)), folds=FOLDS,
        so_ma_da_chay=107,
        delta_r_pham_vi={"so_ma": 2, "so_fill": 91, "dataset": "CALIB", "chien_luoc": "ZoneAbsorptionMinimal"},
        provenance=Provenance(
            params_source="yaml", params_effective={}, git_sha="deadbeef", reproducible_from_sha=True,
            data_hashes={}, cache_mode="none", guard_passed=True, runtime_image_digest="sha256:" + "a" * 64,
        ),
        trial_id="D-0020", nguong=NGUONG_CHO[kc],
    )
    assert bg["ket_cuc"]["value"] == kc.value
    return bg


BAN_GHI = {kc: _ban_ghi(kc=kc) for kc in KetCuc}
DAT_HET = {ma: Measured.ok(True) for ma in MA_KHAC}


class TestLZ57:
    def test_Z0_vuot_troi_moi_arm_DCA_thi_chon_Z0_va_TIEP_TUC(self) -> None:
        kq = danh_gia_gate_d09(
            ban_ghi_ung_vien=BAN_GHI[KetCuc.PASS], tieu_chi_khac=DAT_HET,
            ket_luan_z0t1_vs_z0t2="giữ nguyên Phần 2",
        )
        assert kq.nhanh_1 is KetCuc.PASS and kq.nhanh_2_da_chay
        assert kq.cau_hinh_chon == "Z0"
        assert kq.du_an_tiep_tuc is True
        assert "TIẾP TỤC" in kq.buoc_tiep

    def test_kieu_ket_qua_khong_co_truong_dung_du_an(self) -> None:
        ten = {f.name for f in dataclasses.fields(KetQuaGateD09)}
        assert not any("dung" in t for t in ten), ten

    def test_MOI_to_hop_trang_thai_du_an_deu_tiep_tuc(self) -> None:
        trang = (Measured.ok(True), Measured.ok(False), Measured.pending("chưa đo"))
        so_ca = 0
        for kc in KetCuc:
            for combo in itertools.product(range(3), repeat=len(MA_KHAC)):
                tc = {ma: trang[i] for ma, i in zip(MA_KHAC, combo)}
                kq = danh_gia_gate_d09(ban_ghi_ung_vien=BAN_GHI[kc], tieu_chi_khac=tc)
                so_ca += 1
                assert kq.du_an_tiep_tuc is True
                co_truot = kc is KetCuc.FAIL or 1 in combo
                du_dat = kc is KetCuc.PASS and all(i == 0 for i in combo)
                if co_truot:
                    assert kq.nhanh_1 is KetCuc.FAIL
                elif du_dat:
                    assert kq.nhanh_1 is KetCuc.PASS and kq.cau_hinh_chon == "Z0"
                else:
                    assert kq.nhanh_1 is KetCuc.INCONCLUSIVE
                assert kq.vao_live is (kq.nhanh_1 is KetCuc.PASS)
                assert kq.nhanh_2_da_chay is (kq.nhanh_1 is KetCuc.PASS)
        assert so_ca == 3 * 3 ** len(MA_KHAC)


class TestNhanh1:
    def test_chi_co_dsr_thi_INCONCLUSIVE_va_liet_ke_tam_o_thieu(self) -> None:
        kq = danh_gia_gate_d09(ban_ghi_ung_vien=BAN_GHI[KetCuc.PASS])
        assert kq.nhanh_1 is KetCuc.INCONCLUSIVE and not kq.vao_live
        assert kq.thieu == MA_KHAC
        assert "DR-011" in kq.buoc_tiep

    def test_dsr_INCONCLUSIVE_khong_bi_doc_thanh_FAIL(self) -> None:
        kq = danh_gia_gate_d09(ban_ghi_ung_vien=BAN_GHI[KetCuc.INCONCLUSIVE], tieu_chi_khac=DAT_HET)
        assert kq.nhanh_1 is KetCuc.INCONCLUSIVE and kq.thieu == ("dsr_adj",) and kq.truot == ()

    def test_thu_tu_va_ma_tieu_chi_ghim_theo_spec(self) -> None:
        assert [ma for ma, _ in TIEU_CHI_NHANH_1] == [
            "dsr_adj", "h4d", "liq_buffer", "lo_don_lenh", "skewness_z1",
            "so_lenh_nam", "time_stop", "h4_tp_fallback", "lz10_lz33",
        ]

    def test_bao_cao_khong_doi_ket_cuc(self) -> None:
        a = danh_gia_gate_d09(ban_ghi_ung_vien=BAN_GHI[KetCuc.PASS], tieu_chi_khac=DAT_HET)
        b = danh_gia_gate_d09(
            ban_ghi_ung_vien=BAN_GHI[KetCuc.PASS], tieu_chi_khac=DAT_HET,
            bao_cao={k: Measured.ok(0.9) for k in CHI_BAO_CAO},
        )
        assert a.nhanh_1 is b.nhanh_1 is KetCuc.PASS

    def test_thieu_ket_luan_z0t1_vs_z0t2_thi_ghi_ra(self) -> None:
        kq = danh_gia_gate_d09(ban_ghi_ung_vien=BAN_GHI[KetCuc.PASS], tieu_chi_khac=DAT_HET)
        assert kq.ghi_chep_thieu == ("ket_luan_z0t1_vs_z0t2",)


class TestTuChoiDauVao:
    def test_tieu_chi_la(self) -> None:
        with pytest.raises(GateD09Error, match="lạ"):
            danh_gia_gate_d09(ban_ghi_ung_vien=BAN_GHI[KetCuc.PASS], tieu_chi_khac={"liq_bufer": Measured.ok(True)})

    def test_dsr_khong_nhan_tu_ngoai(self) -> None:
        with pytest.raises(GateD09Error, match="dsr_adj"):
            danh_gia_gate_d09(ban_ghi_ung_vien=BAN_GHI[KetCuc.PASS], tieu_chi_khac={"dsr_adj": Measured.ok(True)})

    def test_gia_tri_khong_phai_bool(self) -> None:
        with pytest.raises(GateD09Error, match="bool"):
            danh_gia_gate_d09(ban_ghi_ung_vien=BAN_GHI[KetCuc.PASS], tieu_chi_khac={"h4d": Measured.ok(1)})

    def test_bao_cao_la(self) -> None:
        with pytest.raises(GateD09Error, match="báo cáo"):
            danh_gia_gate_d09(ban_ghi_ung_vien=BAN_GHI[KetCuc.PASS], bao_cao={"sharpe": Measured.ok(1.0)})

    @pytest.mark.parametrize("arm", ["Z0", "Z0-T0", "Z3"])
    def test_ung_vien_phai_la_arm_phan_quyet(self, arm) -> None:
        with pytest.raises(GateD09Error, match="Z0-T1"):
            danh_gia_gate_d09(ban_ghi_ung_vien=_ban_ghi(arm=arm, kc=KetCuc.INCONCLUSIVE))

    def test_ban_ghi_hong_bi_tu_choi(self) -> None:
        bg = dict(BAN_GHI[KetCuc.PASS])
        bg.pop("provenance")
        with pytest.raises(GateD09Error, match="không hợp lệ"):
            danh_gia_gate_d09(ban_ghi_ung_vien=bg)

    def test_status_khong_ok_cua_dsr_la_thieu(self) -> None:
        bg = dict(BAN_GHI[KetCuc.PASS])
        bg["ket_cuc"] = {"status": Status.UNREADABLE.value, "value": None, "note": "n<2"}
        kq = danh_gia_gate_d09(ban_ghi_ung_vien=bg, tieu_chi_khac=DAT_HET)
        assert kq.nhanh_1 is KetCuc.INCONCLUSIVE and kq.thieu == ("dsr_adj",)
