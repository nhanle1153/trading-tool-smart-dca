"""🔒 TD-0257 — kết quả B1 tính lại từ sổ (`calibration/ket_qua_b1.py`) + tiêu chí cổng D5 (`gates/d5_gate.py`).

Dựng sổ TẠM với suất B1 thật qua `TrialLedger.reserve()` (khoá `D5_DO_TAM_DUNG` tắt trong tiến trình test) và
`lenh_r.json` giả. Mỗi ca phá ĐÚNG MỘT hàng của bảng tiêu chí ⇒ đúng một lý do từ chối.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from tool_d.calibration.bang_r import ghi_bang_r
from tool_d.calibration.chon_gia_tri import HanhDong
from tool_d.calibration.ket_qua_b1 import THU_TU_LONG_DEN_CHAT, KetQuaB1Error, tinh_quyet_dinh_b1
from tool_d.calibration.ung_vien import PARAM_MOC, PARAM_XAC_NHAN, BangUngVien, ThamSoUngVien, doc_bang_ung_vien
from tool_d.gates.d5_gate import THAM_SO_KHONG_CALIBRATE, D5GateError, d5_han_che, kiem_tieu_chi_dong_d5
from tool_d.ledger.registry import TrialLedger
from tool_d.wfo.lenh import LenhWFO

REPO_ROOT = Path(__file__).resolve().parents[2]
DR_THAT = REPO_ROOT / "docs/decisions/DR-D5-01-pham-vi-ung-vien-luat-chon-calibration.md"
BANG = doc_bang_ung_vien(DR_THAT)
R_MOC = [1.2, -1.0, 0.4, -0.7, 2.1, -1.0, 0.3, -0.2, 1.5, -1.1]


@pytest.fixture(autouse=True)
def _mo_khoa_d5(monkeypatch):
    """Khoá `D5_DO_TAM_DUNG` có test riêng (`test_td0373`); ở đây cần đặt được suất B1 trong sổ TẠM."""
    from tool_d.ablation import khoa_do

    monkeypatch.setattr(khoa_do, "D5_DO_TAM_DUNG", False)


def _lenh(rs: list[float], *, lech: int = 0) -> list[LenhWFO]:
    t0 = datetime(2024, 5, 1)
    return [
        LenhWFO(f"A{i}/USDT:USDT", t0 + timedelta(hours=i + lech), t0 + timedelta(hours=i + lech + 5), r, 1.0, 1.0)
        for i, r in enumerate(rs)
    ]


class SoTam:
    """Sổ + `runs/` tạm. `them(ten, gia_tri, r)` đặt chỗ → niêm phong → tiêu → ghi `lenh_r.json`."""

    def __init__(self, tmp_path: Path) -> None:
        self.runs = tmp_path / "runs"
        self.reg = tmp_path / "reg.jsonl"
        state = tmp_path / "runtime_state.json"
        state.write_text(json.dumps({"d4_complete": True}), encoding="utf-8")
        self.so = TrialLedger(self.reg, dr_d5_path=DR_THAT, runtime_state_path=state)

    def them(self, ten: str, gia_tri, lenhs: list[LenhWFO]) -> str:
        tid = self.so.reserve(
            n_dang_ky=114, budget_line="B1", hypothesis_slot="D5", direction="LONG", dataset="CALIB",
            param_under_test=ten, param_value=gia_tri, params_frozen_hash="f", config_hash="c",
            code_commit="a" * 40,
            provenance={
                "params_source": "yaml", "params_effective": {}, "git_sha": "a" * 40,
                "reproducible_from_sha": True, "data_hashes": {}, "cache_mode": "none", "guard_passed": True,
            },
            contribution=1,
        )
        self.so.seal(tid, seal_path=f"runs/{tid}/metrics.seal")
        ghi_bang_r(self.runs / tid, lenhs, trial_id=tid)
        self.so.consume(
            tid, outcome={"expectancy": None, "sharpe": None, "n_trades": len(lenhs), "max_single_loss_ratio": None},
            verdict="INCONCLUSIVE",
        )
        return tid

    def proj(self) -> list:
        return list(self.so.projections().values())

    def kq(self):
        return tinh_quyet_dinh_b1(self.proj(), runs_dir=self.runs, bang=BANG)


def _lo_giu_moc(so: SoTam) -> None:
    """Mốc + 14 suất; mọi ứng viên cho ĐÚNG tập lệnh và kết cục của mốc ⇒ không gì thắng ⇒ giữ mốc/pending."""
    so.them(PARAM_MOC, None, _lenh(R_MOC))
    for ten, ts in BANG.tham_so.items():
        for v in ts.thu:
            so.them(ten, v, _lenh(R_MOC))


def _status_moc() -> dict:
    ps = {ten: {"status": "FROZEN", "value": ts.moc} for ten, ts in BANG.tham_so.items()}
    ps.update({ten: {"status": "FROZEN", "value": 1} for ten in THAM_SO_KHONG_CALIBRATE})
    return ps


class TestKetQuaB1:
    def test_khong_co_moc_la_thieu(self, tmp_path) -> None:
        kq = SoTam(tmp_path).kq()
        assert PARAM_MOC in kq.thieu and kq.moc_trial is None and kq.quyet_dinh == {}

    def test_lo_giu_moc_moi_tham_so_co_quyet_dinh(self, tmp_path) -> None:
        so = SoTam(tmp_path)
        _lo_giu_moc(so)
        kq = so.kq()
        assert kq.thieu == {} and set(kq.quyet_dinh) == set(BANG.tham_so)
        assert kq.tham_so_doi() == {} and kq.so_lenh_moc == len(R_MOC)
        assert set(kq.tham_so_giu_moc()) == set(BANG.tham_so)
        assert kq.gia_tri_cuoi(BANG) == {k: ts.moc for k, ts in BANG.tham_so.items()}

    def test_ket_cuc_thang_ro_la_DOI(self, tmp_path) -> None:
        so = SoTam(tmp_path)
        so.them(PARAM_MOC, None, _lenh(R_MOC))
        so.them("buf_sl_atr", 0.3, _lenh(R_MOC))
        so.them("buf_sl_atr", 0.5, _lenh([r + 1.0 for r in R_MOC]))
        q = so.kq().quyet_dinh["buf_sl_atr"]
        assert q.hanh_dong is HanhDong.DOI and q.gia_tri == 0.5

    def test_thieu_mot_gia_tri_ket_cuc_la_thieu_khong_phai_giu_moc(self, tmp_path) -> None:
        so = SoTam(tmp_path)
        so.them(PARAM_MOC, None, _lenh(R_MOC))
        so.them("buf_sl_atr", 0.3, _lenh(R_MOC))
        kq = so.kq()
        assert "buf_sl_atr" in kq.thieu and "buf_sl_atr" not in kq.quyet_dinh

    def test_thieu_file_bang_thuoc_la_thieu(self, tmp_path) -> None:
        so = SoTam(tmp_path)
        tid = so.them(PARAM_MOC, None, _lenh(R_MOC))
        (so.runs / tid / "lenh_r.json").unlink()
        assert PARAM_MOC in so.kq().thieu

    def test_xac_nhan_ghep_duoc_tinh(self, tmp_path) -> None:
        so = SoTam(tmp_path)
        so.them(PARAM_MOC, None, _lenh(R_MOC))
        so.them(PARAM_XAC_NHAN, {"buf_sl_atr": 0.5}, _lenh([r + 1.0 for r in R_MOC]))
        kq = so.kq()
        assert kq.xac_nhan is not None and kq.xac_nhan.xac_nhan is True
        assert kq.gia_tri_xac_nhan == {"buf_sl_atr": 0.5}

    def test_thu_tu_lech_bang_ung_vien_thi_raise(self) -> None:
        """Đổi DR (bảng đã băm) mà không đổi `THU_TU_LONG_DEN_CHAT` ⇒ lỗi cài đặt, không âm thầm dùng thứ tự cũ."""
        ts = dict(BANG.tham_so)
        ts["zss_threshold"] = ThamSoUngVien(nhom="LOC_LENH", moc=0.5, thu=(0.45, 0.6))
        bang = BangUngVien(dr=BANG.dr, arm=BANG.arm, huong=BANG.huong, tran_suat=16, tham_so=ts, sha256="x")
        with pytest.raises(KetQuaB1Error, match="zss_threshold"):
            tinh_quyet_dinh_b1([], runs_dir=Path("."), bang=bang)

    def test_thu_tu_khop_dung_bang_that(self) -> None:
        for ten, ts in BANG.tham_so.items():
            if ts.nhom == "LOC_LENH":
                assert sorted(THU_TU_LONG_DEN_CHAT[ten]) == sorted([ts.moc, *ts.thu])


def _kiem(so: SoTam, ps: dict | None = None, **kw) -> list[str]:
    b1 = sum(1 for p in so.proj() if p.budget_line == "B1")
    return kiem_tieu_chi_dong_d5(
        ket_qua=so.kq(), bang=BANG, so_b1_calib_consumed=kw.pop("so_b1", b1),
        param_status=_status_moc() if ps is None else ps, **kw,
    )


class TestTieuChiD5:
    def test_lo_giu_moc_day_du_la_DAT(self, tmp_path) -> None:
        so = SoTam(tmp_path)
        _lo_giu_moc(so)
        assert _kiem(so) == []

    def test_so_that_hom_nay_khong_moc_la_TU_CHOI(self, tmp_path) -> None:
        loi = _kiem(SoTam(tmp_path))
        assert any(PARAM_MOC in x for x in loi)

    def test_moc_0_lenh_la_DUNG(self, tmp_path) -> None:
        so = SoTam(tmp_path)
        so.them(PARAM_MOC, None, [])
        assert any("§6.3" in x for x in _kiem(so))

    def test_vuot_tran(self, tmp_path) -> None:
        so = SoTam(tmp_path)
        _lo_giu_moc(so)
        assert any("trần 16" in x for x in _kiem(so, so_b1=17))

    def test_TD0251_bao_khong_lenh_giu_du_thi_tran_15(self, tmp_path) -> None:
        so = SoTam(tmp_path)
        _lo_giu_moc(so)  # 15 suất — đúng trần 15, chưa vượt
        assert _kiem(so, co_lenh_moc_giu_du=False) == []
        assert any("trần 15" in x for x in _kiem(so, so_b1=16, co_lenh_moc_giu_du=False))

    def test_tham_so_thieu_suat_la_TU_CHOI(self, tmp_path) -> None:
        so = SoTam(tmp_path)
        so.them(PARAM_MOC, None, _lenh(R_MOC))
        loi = _kiem(so)
        assert loi and all(x.split(":")[0] in BANG.tham_so for x in loi)

    def test_doi_ma_chua_co_xac_nhan_la_TU_CHOI(self, tmp_path) -> None:
        so = SoTam(tmp_path)
        _lo_giu_moc_tru(so, "buf_sl_atr")
        so.them("buf_sl_atr", 0.3, _lenh(R_MOC))
        so.them("buf_sl_atr", 0.5, _lenh([r + 1.0 for r in R_MOC]))
        # Đúng lý do "chưa có suất", không chỉ "có chữ D5_XAC_NHAN" — phá nhánh này thì nhánh so giá trị vẫn
        # nhắc tới D5_XAC_NHAN, và khẳng định lỏng sẽ PASS RỖNG (bắt được khi phá thật).
        assert any("chưa có suất" in x and PARAM_XAC_NHAN in x for x in _kiem(so))

    def test_xac_nhan_ghep_sai_gia_tri_la_TU_CHOI(self, tmp_path) -> None:
        so = SoTam(tmp_path)
        _lo_giu_moc_tru(so, "buf_sl_atr")
        so.them("buf_sl_atr", 0.3, _lenh(R_MOC))
        so.them("buf_sl_atr", 0.5, _lenh([r + 1.0 for r in R_MOC]))
        so.them(PARAM_XAC_NHAN, {"buf_sl_atr": 0.3}, _lenh([r + 1.0 for r in R_MOC]))
        assert any("xác nhận một cấu hình khác" in x for x in _kiem(so))

    def test_doi_co_xac_nhan_dat_va_status_TUNED_la_DAT(self, tmp_path) -> None:
        so = SoTam(tmp_path)
        _lo_giu_moc_tru(so, "buf_sl_atr")
        so.them("buf_sl_atr", 0.3, _lenh(R_MOC))
        so.them("buf_sl_atr", 0.5, _lenh([r + 1.0 for r in R_MOC]))
        so.them(PARAM_XAC_NHAN, {"buf_sl_atr": 0.5}, _lenh([r + 1.0 for r in R_MOC]))
        ps = _status_moc()
        assert any("buf_sl_atr" in x and "TUNED" in x for x in _kiem(so, ps))
        ps["buf_sl_atr"] = {"status": "TUNED", "value": 0.5}
        assert _kiem(so, ps) == []

    def test_xac_nhan_truot_thi_giu_TOAN_BO_moc(self, tmp_path) -> None:
        """§5.3: không xác nhận ⇒ giá trị phải chạy là mốc ⇒ status TUNED 0.5 là SAI."""
        so = SoTam(tmp_path)
        _lo_giu_moc_tru(so, "buf_sl_atr")
        so.them("buf_sl_atr", 0.3, _lenh(R_MOC))
        so.them("buf_sl_atr", 0.5, _lenh([r + 1.0 for r in R_MOC]))
        so.them(PARAM_XAC_NHAN, {"buf_sl_atr": 0.5}, _lenh([r - 1.0 for r in R_MOC]))
        assert _kiem(so) == []
        ps = _status_moc()
        ps["buf_sl_atr"] = {"status": "TUNED", "value": 0.5}
        assert any("buf_sl_atr" in x for x in _kiem(so, ps))

    def test_xac_nhan_khi_khong_gi_doi_la_TU_CHOI(self, tmp_path) -> None:
        so = SoTam(tmp_path)
        _lo_giu_moc(so)
        so.them(PARAM_XAC_NHAN, {"buf_sl_atr": 0.5}, _lenh(R_MOC))
        assert any("không tham số nào đổi" in x for x in _kiem(so))

    @pytest.mark.parametrize("ten", sorted(THAM_SO_KHONG_CALIBRATE))
    def test_nam_tham_so_khong_calibrate_phai_FROZEN(self, tmp_path, ten) -> None:
        so = SoTam(tmp_path)
        _lo_giu_moc(so)
        ps = _status_moc()
        ps[ten] = {"status": "TUNED", "value": 1}
        assert any(ten in x and "§2.2" in x for x in _kiem(so, ps))

    def test_kieu_sai_la_raise(self) -> None:
        with pytest.raises(D5GateError):
            kiem_tieu_chi_dong_d5(ket_qua={}, bang=BANG, so_b1_calib_consumed=0, param_status={})

    def test_han_che_du_bay_dieu_va_danh_sach_giu_moc(self, tmp_path) -> None:
        so = SoTam(tmp_path)
        _lo_giu_moc(so)
        hc = d5_han_che(so.kq(), co_lenh_moc_giu_du=None)
        for muc in ("(1)", "(2)", "(3)", "(4)", "(5)", "(6)", "(7)", "(8)", "(9)"):
            assert muc in hc
        assert "CHỈ LONG" in hc and all(t in hc for t in BANG.tham_so)


def _lo_giu_moc_tru(so: SoTam, bo: str) -> None:
    so.them(PARAM_MOC, None, _lenh(R_MOC))
    for ten, ts in BANG.tham_so.items():
        if ten == bo:
            continue
        for v in ts.thu:
            so.them(ten, v, _lenh(R_MOC))
