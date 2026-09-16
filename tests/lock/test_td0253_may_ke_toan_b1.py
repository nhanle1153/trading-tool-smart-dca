"""🔒 TD-0253 — máy kế toán B1 TẠI CỬA `TrialLedger.reserve()` (`DR-D5-01`).

Trước TD-0253, dòng B1 không có một phép kiểm nào: đặt chỗ `zss_threshold =
0.55` (không thuộc danh sách nào), đặt 100 suất, đặt khi cổng D4 chưa đóng —
đều ghi được, và vì sổ append-only nên một suất sai đã vào là đã chạm CALIB.

Chủ dự án chốt 16/09/2026 chặn tại cửa (Khối 19 chốt 10). Mỗi ca từ chối dưới
đây khẳng định HAI thứ: raise `B1Error` VÀ sổ không thêm dòng nào — từ chối mà
vẫn ghi thì cũng là không chặn.

Nguồn sự thật danh sách ứng viên là CHÍNH `DR-D5-01` §3.3 (có băm). Ca
`TestDrThat` đọc file thật — nếu ai đó sửa bảng ứng viên mà không sửa băm, ca
đó đỏ trước khi một suất nào kịp đặt.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tool_d.calibration.ung_vien import (
    DEFAULT_DR_D5_01_PATH,
    PARAM_MOC,
    PARAM_XAC_NHAN,
    UngVienError,
    bam_chuan_hoa,
    doc_bang_ung_vien,
)
from tool_d.ledger.registry import B1Error, TrialLedger

REPO_ROOT = Path(__file__).resolve().parents[2]
DR_THAT = REPO_ROOT / DEFAULT_DR_D5_01_PATH


def _prov() -> dict:
    return {
        "params_source": "yaml", "params_effective": {}, "git_sha": "a" * 40,
        "reproducible_from_sha": True, "data_hashes": {}, "cache_mode": "none", "guard_passed": True,
    }


def _state(tmp_path: Path, **khoa) -> Path:
    p = tmp_path / "runtime_state.json"
    p.write_text(json.dumps(khoa), encoding="utf-8")
    return p


def _so(tmp_path: Path, *, d4: bool | None = True, dr: Path = DR_THAT) -> tuple[TrialLedger, Path]:
    reg = tmp_path / "reg.jsonl"
    state = _state(tmp_path, **({} if d4 is None else {"d4_complete": d4}))
    return TrialLedger(reg, dr_d5_path=dr, runtime_state_path=state), reg


def _kw(**doi) -> dict:
    kw = dict(
        n_dang_ky=114, budget_line="B1", hypothesis_slot="D5", direction="LONG", dataset="CALIB",
        param_under_test="zss_threshold", param_value=0.4, params_frozen_hash="f", config_hash="c",
        code_commit="a" * 40, provenance=_prov(), contribution=1,
    )
    kw.update(doi)
    return kw


def _so_dong(reg: Path) -> int:
    return len([d for d in reg.read_text(encoding="utf-8").splitlines() if d.strip()]) if reg.exists() else 0


def _tu_choi(ledger: TrialLedger, reg: Path, **doi) -> None:
    truoc = _so_dong(reg)
    with pytest.raises(B1Error):
        ledger.reserve(**_kw(**doi))
    assert _so_dong(reg) == truoc, "TỪ CHỐI mà vẫn ghi sổ — cửa không chặn gì"


class TestDrThat:
    def test_doc_duoc_va_bam_khop(self) -> None:
        bang = doc_bang_ung_vien(DR_THAT)
        assert bang.arm == "Z0-T1" and bang.huong == "LONG" and bang.tran_suat == 16
        assert sorted(bang.tham_so) == [
            "buf_sl_atr", "dg7_funding_frac", "max_hold_bars_4h", "tp1_haircut_pct",
            "v_min", "wick_close_upper_frac", "zss_threshold",
        ]

    def test_nam_tham_so_giu_FROZEN_khong_nam_trong_bang(self) -> None:
        """§2.2 — bốn tham số bất khả trên `Z0-T1` + `mult_corr_thresholds`."""
        bang = doc_bang_ung_vien(DR_THAT)
        for k in ("dg4_bars_1h", "dg6a_atr_ratio", "dg6d_retrace_frac", "funding_rate_pct", "mult_corr_thresholds"):
            assert k not in bang.tham_so

    def test_sua_mot_o_ma_khong_sua_bam_thi_RAISE(self, tmp_path: Path) -> None:
        gia = tmp_path / "dr.md"
        gia.write_text(DR_THAT.read_text(encoding="utf-8").replace('"thu":[0.4,0.6]', '"thu":[0.4,0.7]', 1),
                       encoding="utf-8")
        with pytest.raises(UngVienError, match="BĂM LỆCH"):
            doc_bang_ung_vien(gia)

    def test_bam_chuan_hoa_khong_phu_thuoc_thu_tu_khoa(self) -> None:
        assert bam_chuan_hoa({"b": 1, "a": [1, 2]}) == bam_chuan_hoa({"a": [1, 2], "b": 1})


class TestTuChoiTaiCua:
    def test_cong_D4_chua_dong(self, tmp_path: Path) -> None:
        """§6.1 — kể cả khoá vắng mặt hoặc false."""
        for d4 in (None, False):
            sub = tmp_path / str(d4)
            sub.mkdir()
            ledger, reg = _so(sub, d4=d4)
            _tu_choi(ledger, reg)

    def test_runtime_state_hong_la_tu_choi(self, tmp_path: Path) -> None:
        state = tmp_path / "runtime_state.json"
        state.write_text("{không phải json", encoding="utf-8")
        reg = tmp_path / "reg.jsonl"
        _tu_choi(TrialLedger(reg, dr_d5_path=DR_THAT, runtime_state_path=state), reg)

    def test_gia_tri_ngoai_danh_sach(self, tmp_path: Path) -> None:
        ledger, reg = _so(tmp_path)
        _tu_choi(ledger, reg, param_value=0.55)

    def test_gia_tri_moc_khong_dat_cho_rieng(self, tmp_path: Path) -> None:
        """Mốc đi bằng suất `D5_MOC` duy nhất — đặt riêng là chạy mốc lần hai."""
        ledger, reg = _so(tmp_path)
        _tu_choi(ledger, reg, param_value=0.5)

    @pytest.mark.parametrize("khoa", ["dg4_bars_1h", "mult_corr_thresholds", "funding_rate_pct"])
    def test_tham_so_giu_FROZEN(self, tmp_path: Path, khoa: str) -> None:
        ledger, reg = _so(tmp_path)
        _tu_choi(ledger, reg, param_under_test=khoa, param_value=8)

    def test_ngoai_CALIB(self, tmp_path: Path) -> None:
        ledger, reg = _so(tmp_path)
        _tu_choi(ledger, reg, dataset="WFO")

    def test_SHORT(self, tmp_path: Path) -> None:
        ledger, reg = _so(tmp_path)
        _tu_choi(ledger, reg, direction="SHORT")

    def test_trung_suat_chua_hoan_tra(self, tmp_path: Path) -> None:
        ledger, reg = _so(tmp_path)
        ledger.reserve(**_kw())
        _tu_choi(ledger, reg)

    def test_moc_thu_hai(self, tmp_path: Path) -> None:
        ledger, reg = _so(tmp_path)
        ledger.reserve(**_kw(param_under_test=PARAM_MOC, param_value=None))
        _tu_choi(ledger, reg, param_under_test=PARAM_MOC, param_value=None)

    def test_xac_nhan_khong_doi_gi_khoi_moc(self, tmp_path: Path) -> None:
        ledger, reg = _so(tmp_path)
        _tu_choi(ledger, reg, param_under_test=PARAM_XAC_NHAN, param_value={"zss_threshold": 0.5})

    def test_xac_nhan_gia_tri_ngoai_danh_sach(self, tmp_path: Path) -> None:
        ledger, reg = _so(tmp_path)
        _tu_choi(ledger, reg, param_under_test=PARAM_XAC_NHAN, param_value={"zss_threshold": 0.45})

    def test_suat_thu_17_vuot_tran(self, tmp_path: Path) -> None:
        """Trần 16 = 1 mốc + 14 thử + 1 xác nhận (§4). Đặt đủ 16 hợp lệ rồi thêm
        một suất bất kỳ ⇒ từ chối. Không có đủ 16 giá trị thử khác nhau thì đã
        bị chặn trước bởi 'trùng suất' — nên đếm theo đúng đường hợp lệ."""
        ledger, reg = _so(tmp_path)
        bang = doc_bang_ung_vien(DR_THAT)
        ledger.reserve(**_kw(param_under_test=PARAM_MOC, param_value=None))
        for k, ts in bang.tham_so.items():
            for v in ts.thu:
                ledger.reserve(**_kw(param_under_test=k, param_value=v))
        ledger.reserve(**_kw(param_under_test=PARAM_XAC_NHAN, param_value={"zss_threshold": 0.4}))
        assert _so_dong(reg) == 16
        _tu_choi(ledger, reg, param_under_test=PARAM_XAC_NHAN, param_value={"buf_sl_atr": 0.3})


class TestChoQuaDungSuat:
    def test_suat_hop_le_ghi_duoc_va_so_mang_dung_gia_tri(self, tmp_path: Path) -> None:
        ledger, reg = _so(tmp_path)
        tid = ledger.reserve(**_kw(param_under_test="v_min", param_value=0.0))
        ev = json.loads(reg.read_text(encoding="utf-8").splitlines()[0])
        assert ev["trial_id"] == tid and ev["budget_line"] == "B1" and ev["param_value"] == 0.0

    def test_so_nguyen_va_so_thuc_cung_gia_tri(self, tmp_path: Path) -> None:
        """`max_hold_bars_4h` khai `20` trong DR; bộ chạy có thể truyền `20.0`."""
        ledger, _ = _so(tmp_path)
        ledger.reserve(**_kw(param_under_test="max_hold_bars_4h", param_value=20.0))

    def test_hoan_tra_thi_duoc_dat_lai(self, tmp_path: Path) -> None:
        """REFUNDED không đếm vào trần và không tính là trùng (DR-014 hoàn trả)."""
        ledger, _ = _so(tmp_path)
        tid = ledger.reserve(**_kw())
        ledger.refund(tid, cause_machine="OOM:signal_9_before_first_metric")
        ledger.reserve(**_kw())

    def test_dong_khac_B1_khong_di_qua_cua(self, tmp_path: Path) -> None:
        """Cửa chỉ gác B1 — B3/CTRL giữ nguyên hành vi (các test khoá cũ canh)."""
        ledger, reg = _so(tmp_path, d4=None)
        ledger.reserve(**_kw(budget_line="B3", param_value=0.55))
        assert _so_dong(reg) == 1
