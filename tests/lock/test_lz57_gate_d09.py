"""L-Z57 🔴 CRITICAL (spec `:3979-3981`) + TD-0336/TD-0341 — GATE D0.9 §10.2 cho D4.

    L-Z57 — Bộ kết quả giả lập "Z0 vượt trội mọi arm DCA" đưa qua GATE §10.2 → kết cục =
    "chọn Z0, dự án TIẾP TỤC", KHÔNG có đường nào dẫn tới DỪNG DỰ ÁN.

File này:
1. Ca đích danh của spec.
2. Quét TOÀN BỘ tổ hợp (3 kết cục DSR × 3 trạng thái cho mỗi tiêu chí trong tám = 19.683 ca): dự án luôn tiếp tục;
   PASS ⇔ đủ và đạt hết; FAIL ⇔ có ô đo được mà trượt; skewness-so-`Z1` KHÔNG BAO GIỜ đổi kết cục của `Z0-T1`
   (`DR-D9-02`, arm entry đơn).
3. 🔄 TD-0341 — ĐỐI CHIẾU D4↔D9: cùng lệnh, cùng chỉ số ⇒ `danh_gia_gate_d09` và `danh_gia_cong_d9` cho CÙNG kết
   cục và cùng tập "không đạt / chưa đo / không áp dụng". Đây là thứ giữ hai lớp tách-ba-kết-cục không trôi lệch.
"""

from __future__ import annotations

import dataclasses
import itertools
from datetime import date, datetime, timedelta

import pytest

from tool_d.ablation.ban_ghi import dung_ban_ghi_arm
from tool_d.gates.cscv import KetQuaPBO
from tool_d.gates.d0_9 import (
    CHI_BAO_CAO,
    TIEU_CHI_BO_TEST,
    TIEU_CHI_NHANH_1,
    GateD09Error,
    KetQuaGateD09,
    danh_gia_gate_d09,
)
from tool_d.gates.d9_gate import TIEU_CHI_KHAI, danh_gia_cong_d9
from tool_d.gates.dsr import N_DANG_KY
from tool_d.gates.ket_cuc import KetCuc
from tool_d.gates.thresholds import TIEU_CHI_SKEWNESS_Z1
from tool_d.measurement.provenance import Provenance
from tool_d.measurement.tri_state import Measured, Status
from tool_d.wfo.folds import Fold
from tool_d.wfo.lenh import LenhWFO

FOLDS = (Fold(1, date(2025, 6, 12), date(2025, 9, 4), date(2025, 9, 4), date(2026, 1, 29)),)
CUA_SO = (date(2025, 6, 12), date(2026, 1, 28))


def _lenhs(pnls: list[float]) -> list[LenhWFO]:
    d0 = datetime(2025, 6, 15)
    return [LenhWFO("LTC/USDT:USDT", d0 + timedelta(days=3 * i), d0 + timedelta(days=3 * i), p, 2.0, 4.0)
            for i, p in enumerate(pnls)]


#: Ba bộ lệnh cho ba kết cục DSR ở NGƯỠNG THẬT (0,10): R_trien_khai = pnl / 2.
LENH_THEO_KC = {
    KetCuc.PASS: _lenhs([2.2 if i % 2 else 1.8 for i in range(60)]),          # mean 1,0 · thuế ≈ 0,04
    KetCuc.FAIL: _lenhs([-1.8 if i % 2 else -2.2 for i in range(60)]),        # mean −1,0 · thuế ≈ 0,04
    KetCuc.INCONCLUSIVE: _lenhs([2.0, -2.0, 4.0, -1.0, 3.0, -2.0]),          # thuế ≈ 1,5 > 0,10
}


def _prov() -> Provenance:
    return Provenance(
        params_source="yaml", params_effective={}, git_sha="deadbeef", reproducible_from_sha=True,
        data_hashes={}, cache_mode="none", guard_passed=True, runtime_image_digest="sha256:" + "a" * 64,
    )


def _ban_ghi(kc: KetCuc, arm: str = "Z0-T1") -> dict:
    bg = dung_ban_ghi_arm(
        arm=arm, lenhs=LENH_THEO_KC[kc], cua_so=CUA_SO, folds=FOLDS, so_ma_da_chay=107,
        delta_r_pham_vi={"so_ma": 2, "so_fill": 91, "dataset": "CALIB", "chien_luoc": "ZoneAbsorptionMinimal"},
        provenance=_prov(), trial_id="D-0020",
    )
    assert bg["ket_cuc"]["value"] == kc.value
    return bg


BAN_GHI = {kc: _ban_ghi(kc) for kc in KetCuc}
DAT = {
    "liq_buffer_ratio_mean": 20.0, "max_single_trade_loss_over_risk_budget": 1.0, TIEU_CHI_SKEWNESS_Z1: 0.0,
    "trades_per_year": 300.0, "tp_fallback_ratio": 0.1, "time_stop_ratio": 0.1,
}
TRUOT = {
    "liq_buffer_ratio_mean": 5.0, "max_single_trade_loss_over_risk_budget": 2.0, TIEU_CHI_SKEWNESS_Z1: 0.9,
    "trades_per_year": 50.0, "tp_fallback_ratio": 0.9, "time_stop_ratio": 0.5,
}
assert set(DAT) == set(TRUOT) == set(TIEU_CHI_KHAI)
CHI_SO_DAT = {k: Measured.ok(v) for k, v in DAT.items()}
BO_TEST_DAT = {k: Measured.ok(True) for k in TIEU_CHI_BO_TEST}


def _trang(k: str, i: int, bool_: bool = False) -> Measured:
    if i == 2:
        return Measured.pending("chưa đo")
    if bool_:
        return Measured.ok(i == 0)
    return Measured.ok(DAT[k] if i == 0 else TRUOT[k])


class TestLZ57:
    def test_Z0_vuot_troi_moi_arm_DCA_thi_chon_Z0_va_TIEP_TUC(self) -> None:
        kq = danh_gia_gate_d09(
            ban_ghi_ung_vien=BAN_GHI[KetCuc.PASS], chi_so=CHI_SO_DAT, bo_test=BO_TEST_DAT,
            ket_luan_z0t1_vs_z0t2="giữ nguyên Phần 2",
        )
        assert kq.nhanh_1 is KetCuc.PASS and kq.nhanh_2_da_chay
        assert kq.cau_hinh_chon == "Z0" and kq.du_an_tiep_tuc is True
        assert "TIẾP TỤC" in kq.buoc_tiep

    def test_kieu_ket_qua_khong_co_truong_dung_du_an(self) -> None:
        # Danh sách CHO PHÉP, khớp tuyệt đối — thêm trường nào (vd một cờ "dừng dự án") là phải sửa dòng này có chủ
        # đích. (Bản đầu dò chuỗi con "dung" và bắt nhầm `khong_ap_dung` — đo ngữ nghĩa bằng cú pháp.)
        assert {f.name for f in dataclasses.fields(KetQuaGateD09)} == {
            "nhanh_1", "truot", "thieu", "khong_ap_dung", "dsr_ket_cuc", "vao_live", "nhanh_2_da_chay",
            "cau_hinh_chon", "buoc_tiep", "du_an_tiep_tuc", "bao_cao", "ghi_chep_thieu",
        }

    def test_MOI_to_hop_trang_thai_du_an_deu_tiep_tuc(self) -> None:
        so_ca = 0
        khac_skew = [k for k in TIEU_CHI_KHAI if k != TIEU_CHI_SKEWNESS_Z1]
        for kc in KetCuc:
            for combo in itertools.product(range(3), repeat=len(TIEU_CHI_KHAI) + len(TIEU_CHI_BO_TEST)):
                so = dict(zip(TIEU_CHI_KHAI, combo))
                bt = dict(zip(TIEU_CHI_BO_TEST, combo[len(TIEU_CHI_KHAI):]))
                kq = danh_gia_gate_d09(
                    ban_ghi_ung_vien=BAN_GHI[kc],
                    chi_so={k: _trang(k, i) for k, i in so.items()},
                    bo_test={k: _trang(k, i, bool_=True) for k, i in bt.items()},
                )
                so_ca += 1
                assert kq.du_an_tiep_tuc is True
                assert kq.khong_ap_dung == (TIEU_CHI_SKEWNESS_Z1,)
                chi_tinh = [so[k] for k in khac_skew] + list(bt.values())
                if kc is KetCuc.FAIL or 1 in chi_tinh:
                    assert kq.nhanh_1 is KetCuc.FAIL
                elif kc is KetCuc.PASS and all(i == 0 for i in chi_tinh):
                    assert kq.nhanh_1 is KetCuc.PASS and kq.cau_hinh_chon == "Z0"
                else:
                    assert kq.nhanh_1 is KetCuc.INCONCLUSIVE
                assert kq.vao_live is (kq.nhanh_1 is KetCuc.PASS)
                assert kq.nhanh_2_da_chay is (kq.nhanh_1 is KetCuc.PASS)
        assert so_ca == 3 * 3 ** (len(TIEU_CHI_KHAI) + len(TIEU_CHI_BO_TEST))


class TestDoiChieuD4VaD9:
    @pytest.mark.parametrize("kc", list(KetCuc))
    def test_cung_dau_vao_cung_ket_cuc(self, kc) -> None:
        pbo = KetQuaPBO(pbo=Measured.ok(0.2), so_cau_hinh_dau_vao=4, so_cau_hinh_phan_biet=4,
                        cau_hinh_gop_trung=(), so_to_hop=70, so_to_hop_doc_duoc=70, to_hop=())
        r = [l.r_trien_khai for l in LENH_THEO_KC[kc]]
        for combo in itertools.product(range(3), repeat=len(TIEU_CHI_KHAI)):
            cs = {k: _trang(k, i) for k, i in zip(TIEU_CHI_KHAI, combo)}
            d4 = danh_gia_gate_d09(ban_ghi_ung_vien=BAN_GHI[kc], chi_so=cs, bo_test=BO_TEST_DAT)
            d9 = danh_gia_cong_d9(r_trien_khai_test=r, n_trials=N_DANG_KY, chi_so=cs, ket_qua_pbo=pbo, arm="Z0-T1")
            assert d4.nhanh_1 is d9.ket_cuc, combo
            assert set(d4.truot) == set(d9.khong_dat) and set(d4.thieu) == set(d9.chua_do), combo
            assert d4.khong_ap_dung == d9.khong_ap_dung


class TestNhanh1:
    def test_chi_co_dsr_thi_INCONCLUSIVE_va_liet_ke_o_thieu(self) -> None:
        kq = danh_gia_gate_d09(ban_ghi_ung_vien=BAN_GHI[KetCuc.PASS])
        assert kq.nhanh_1 is KetCuc.INCONCLUSIVE and not kq.vao_live
        assert kq.thieu == tuple(k for k in TIEU_CHI_NHANH_1 if k not in ("dsr_adjusted_expectancy", TIEU_CHI_SKEWNESS_Z1))
        assert "DR-011" in kq.buoc_tiep

    def test_dsr_INCONCLUSIVE_khong_bi_doc_thanh_FAIL(self) -> None:
        kq = danh_gia_gate_d09(ban_ghi_ung_vien=BAN_GHI[KetCuc.INCONCLUSIVE], chi_so=CHI_SO_DAT, bo_test=BO_TEST_DAT)
        assert kq.nhanh_1 is KetCuc.INCONCLUSIVE and kq.thieu == ("dsr_adjusted_expectancy",) and kq.truot == ()

    def test_bao_cao_khong_doi_ket_cuc(self) -> None:
        kq = danh_gia_gate_d09(
            ban_ghi_ung_vien=BAN_GHI[KetCuc.PASS], chi_so=CHI_SO_DAT, bo_test=BO_TEST_DAT,
            bao_cao={k: Measured.ok(0.9) for k in CHI_BAO_CAO},
        )
        assert kq.nhanh_1 is KetCuc.PASS

    def test_thieu_ket_luan_z0t1_vs_z0t2_thi_ghi_ra(self) -> None:
        kq = danh_gia_gate_d09(ban_ghi_ung_vien=BAN_GHI[KetCuc.PASS], chi_so=CHI_SO_DAT, bo_test=BO_TEST_DAT)
        assert kq.ghi_chep_thieu == ("ket_luan_z0t1_vs_z0t2",)

    def test_module_khong_chua_nguong_rieng(self) -> None:
        from pathlib import Path

        nguon = (Path(__file__).resolve().parents[2] / "src/tool_d/gates/d0_9.py").read_text(encoding="utf-8")
        for so in ("1.15", "0.40", "150", "8.0", "0.25"):
            assert so not in nguon, f"d0_9.py chứa ngưỡng {so} — ngưỡng chỉ ở thresholds.py (N1)"


class TestTuChoiDauVao:
    def test_chi_so_la(self) -> None:
        with pytest.raises(GateD09Error, match="lạ"):
            danh_gia_gate_d09(ban_ghi_ung_vien=BAN_GHI[KetCuc.PASS], chi_so={"liq_bufer": Measured.ok(1.0)})

    def test_dsr_khong_nhan_tu_ngoai(self) -> None:
        with pytest.raises(GateD09Error, match="lạ"):
            danh_gia_gate_d09(ban_ghi_ung_vien=BAN_GHI[KetCuc.PASS], chi_so={"dsr_adjusted_expectancy": Measured.ok(1.0)})

    def test_bo_test_khong_phai_bool(self) -> None:
        with pytest.raises(GateD09Error, match="bool"):
            danh_gia_gate_d09(ban_ghi_ung_vien=BAN_GHI[KetCuc.PASS], bo_test={"h4d": Measured.ok(1)})

    def test_khong_phai_measured(self) -> None:
        with pytest.raises(GateD09Error, match="Measured"):
            danh_gia_gate_d09(ban_ghi_ung_vien=BAN_GHI[KetCuc.PASS], chi_so={"trades_per_year": 300.0})

    def test_bao_cao_la(self) -> None:
        with pytest.raises(GateD09Error, match="lạ"):
            danh_gia_gate_d09(ban_ghi_ung_vien=BAN_GHI[KetCuc.PASS], bao_cao={"sharpe": Measured.ok(1.0)})

    @pytest.mark.parametrize("arm", ["Z0", "Z0-T0", "Z3"])
    def test_ung_vien_phai_la_arm_phan_quyet(self, arm) -> None:
        with pytest.raises(GateD09Error, match="Z0-T1"):
            danh_gia_gate_d09(ban_ghi_ung_vien=_ban_ghi(KetCuc.INCONCLUSIVE, arm=arm))

    def test_ban_ghi_hong_bi_tu_choi(self) -> None:
        bg = dict(BAN_GHI[KetCuc.PASS])
        bg.pop("provenance")
        with pytest.raises(GateD09Error, match="không hợp lệ"):
            danh_gia_gate_d09(ban_ghi_ung_vien=bg)

    def test_ket_cuc_ban_ghi_lech_nguong_chung_thi_raise(self) -> None:
        bg = dict(BAN_GHI[KetCuc.PASS])
        bg["ket_cuc"] = {"status": "ok", "value": "FAIL", "note": None}
        with pytest.raises(GateD09Error, match="ngưỡng lệch"):
            danh_gia_gate_d09(ban_ghi_ung_vien=bg)

    def test_status_khong_ok_cua_dsr_la_thieu(self) -> None:
        bg = dict(BAN_GHI[KetCuc.PASS])
        bg["ket_cuc"] = {"status": Status.UNREADABLE.value, "value": None, "note": "n<2"}
        kq = danh_gia_gate_d09(ban_ghi_ung_vien=bg, chi_so=CHI_SO_DAT, bo_test=BO_TEST_DAT)
        assert kq.nhanh_1 is KetCuc.INCONCLUSIVE and kq.thieu == ("dsr_adjusted_expectancy",)
