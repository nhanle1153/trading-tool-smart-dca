"""🔒 TD-0426 (`MT-40`, `DR-D6D8-01` §4.2) — đỉnh equity đặt lại ở ĐÚNG HAI sự kiện có ghi sổ, không gì khác.

Chủ dự án chốt 17/09/2026: (a) `NAP_RUT` — đỉnh DỊCH đúng số tiền; (b) `ABORT` — chu trình giả thuyết mới, đỉnh mới.
Ngoài hai sự kiện đó KHÔNG BAO GIỜ (không sau HALT, không theo lịch, không khi restart). Tới 26/09/2026 mã vẫn thi hành
chính sách cũ 14/09 *"không bao giờ"* — không có đường nào cho hai sự kiện: rút 10% vốn ⇒ bot đọc thành sụt 10% ⇒ HALT
oan; sau ABORT chu trình mới thừa hưởng đỉnh cũ ⇒ bị chặn từ lệnh đầu.

`DR-D6D8-01` §4.2 đòi phép kiểm chạy qua ĐƯỜNG SẢN XUẤT ⇒ `TestDuongSanXuat` gọi đúng `ZoneAbsorption.bot_start()` /
`_dd_pct()` (cùng khuôn `test_td0238_dinh_equity_ben_vung_qua_restart.py`). `TestSoSuKien` khoá tầng thuần.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from tool_d.equity_peak import (
    ABORT,
    BAM_RONG,
    LOAI_SU_KIEN,
    NAP_RUT,
    DinhEquityBenVung,
    DinhEquityError,
    SuKienDinh,
    cap_nhat_dinh,
    doc_dinh_equity,
    doc_so_su_kien,
    duong_dan_so_su_kien,
    ghi_su_kien,
)
from tool_d.sizing import mult_dd

REPO_ROOT = Path(__file__).resolve().parents[2]
NGUON_CHIEN_LUOC = REPO_ROOT / "user_data/strategies/ZoneAbsorption.py"


def _import_chien_luoc():
    if str(REPO_ROOT / "user_data/strategies") not in sys.path:
        sys.path.insert(0, str(REPO_ROOT / "user_data/strategies"))
    spec = importlib.util.spec_from_file_location("ZoneAbsorption", NGUON_CHIEN_LUOC)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class _ViGia:
    def __init__(self, tong: float) -> None:
        self._tong = tong

    def get_total(self, currency: str) -> float:
        return self._tong


def _bot(ZA, trang_thai: Path, runmode: str = "dry_run"):
    s = ZA.ZoneAbsorption(config={"stake_currency": "USDT", "exchange": {"name": "binance"}})
    s._duong_dan_dinh_equity = trang_thai
    s.dp = SimpleNamespace(runmode=SimpleNamespace(value=runmode))
    s.bot_start()
    return s


def _doc(s, tong: float) -> float:
    s.wallets = _ViGia(tong)
    return s._dd_pct()


def _nap_rut(so_tien: float, ghi_chu: str = "test") -> SuKienDinh:
    return SuKienDinh(loai=NAP_RUT, stake_currency="USDT", luc_utc="2026-09-26T00:00:00Z", ghi_chu=ghi_chu,
                      so_tien=so_tien)


def _abort() -> SuKienDinh:
    return SuKienDinh(loai=ABORT, stake_currency="USDT", luc_utc="2026-09-26T00:00:00Z", ghi_chu="ABORT L3")


@pytest.fixture
def ZA():
    return _import_chien_luoc()


@pytest.fixture
def tt(tmp_path: Path) -> Path:
    return tmp_path / "dry_run" / "equity_peak_state.json"


class TestDuongSanXuat:
    def test_DOI_CHUNG_rut_KHONG_ghi_so_thi_HALT(self, ZA, tt) -> None:
        """Đối chứng: không có sự kiện nào thì rút 100 từ đỉnh 1100 đọc thành sụt 9,09% ⇒ HALT (hành vi đúng khi
        KHÔNG ai ghi sổ — tiền biến mất không lý do phải bị coi là sụt)."""
        s = _bot(ZA, tt)
        _doc(s, 1100.0)
        assert mult_dd(dd_pct=_doc(s, 1000.0), soft_pct=5.0, halt_pct=8.0) == 0.0

    def test_rut_CO_ghi_so_thi_dinh_DICH_dung_so_tien_va_khong_HALT(self, ZA, tt) -> None:
        s = _bot(ZA, tt)
        _doc(s, 1100.0)
        ghi_su_kien(duong_dan_so_su_kien(tt), _nap_rut(-100.0))  # ghi SAU khi tiền đã rời
        assert _doc(s, 1000.0) == pytest.approx(0.0)
        assert s._dinh_equity == pytest.approx(1000.0)
        assert _doc(s, 950.0) == pytest.approx(5.0)  # sụt THẬT sau đó vẫn đo đúng từ đỉnh đã dịch

    def test_nap_CO_ghi_so_dich_dinh_len_dung_so_tien_khong_ve_muc_hien_tai(self, ZA, tt) -> None:
        s = _bot(ZA, tt)
        _doc(s, 1100.0)
        _doc(s, 1000.0)  # đang sụt 9,09%
        ghi_su_kien(duong_dan_so_su_kien(tt), _nap_rut(500.0))  # ghi TRƯỚC khi chuyển vào
        _doc(s, 1000.0)
        assert s._dinh_equity == pytest.approx(1600.0), "đỉnh DỊCH +500, không về mức hiện tại"
        assert _doc(s, 1500.0) == pytest.approx(100.0 / 1600.0 * 100.0), "nạp không xoá được sụt 100 đang có"

    def test_ABORT_mo_chu_trinh_moi_dinh_moi_la_equity_lan_doc_ke_tiep(self, ZA, tt) -> None:
        s = _bot(ZA, tt)
        _doc(s, 1100.0)
        assert _doc(s, 850.0) > 20.0
        ghi_su_kien(duong_dan_so_su_kien(tt), _abort())
        assert _doc(s, 850.0) == pytest.approx(0.0)
        assert s._dinh_equity == pytest.approx(850.0)

    def test_restart_KHONG_ap_lai_su_kien_da_ap(self, ZA, tt) -> None:
        """Sự kiện thứ ba bị cấm: restart. Và một sự kiện đã áp không được áp lần hai sau restart."""
        s1 = _bot(ZA, tt)
        _doc(s1, 1100.0)
        ghi_su_kien(duong_dan_so_su_kien(tt), _nap_rut(-100.0))
        _doc(s1, 1000.0)
        s2 = _bot(ZA, tt)
        assert s2._dinh_equity == pytest.approx(1000.0)
        _doc(s2, 1000.0)
        assert s2._dinh_equity == pytest.approx(1000.0), "rút -100 bị áp HAI lần sau restart"
        assert doc_dinh_equity(tt).so_su_kien_da_ap == 1

    def test_restart_KHONG_dat_lai_dinh(self, ZA, tt) -> None:
        s1 = _bot(ZA, tt)
        _doc(s1, 1100.0)
        s2 = _bot(ZA, tt)
        assert mult_dd(dd_pct=_doc(s2, 1000.0), soft_pct=5.0, halt_pct=8.0) == 0.0

    @pytest.mark.parametrize("loai", ["HALT", "RESTART", "RESET_LICH", "nap_rut"])
    def test_su_kien_THU_BA_trong_so_thi_TU_CHOI(self, ZA, tt, loai: str) -> None:
        s = _bot(ZA, tt)
        _doc(s, 1100.0)
        so = duong_dan_so_su_kien(tt)
        so.write_bytes((json.dumps({"loai": loai, "stake_currency": "USDT", "luc_utc": "x", "ghi_chu": "x"}) + "\n")
                       .encode("utf-8"))
        with pytest.raises(DinhEquityError, match="ĐÚNG HAI"):
            _doc(s, 1000.0)

    def test_backtest_khong_doc_khong_tao_so(self, ZA, tmp_path) -> None:
        tt = tmp_path / "bt" / "equity_peak_state.json"
        s = _bot(ZA, tt, runmode="backtest")
        _doc(s, 1100.0)
        _doc(s, 1000.0)
        assert not tt.parent.exists()


class TestSoSuKien:
    def test_dung_hai_loai_cap_C(self) -> None:
        assert LOAI_SU_KIEN == (NAP_RUT, ABORT)

    def test_ghi_roi_doc_lai_va_chi_ghi_LF(self, tmp_path) -> None:
        so = tmp_path / "so.jsonl"
        ghi_su_kien(so, _nap_rut(-50.0))
        ghi_su_kien(so, _abort())
        assert b"\r\n" not in so.read_bytes()
        assert [sk.loai for _, sk in doc_so_su_kien(so)] == [NAP_RUT, ABORT]

    def test_sua_dong_DA_AP_thi_TU_CHOI(self, tmp_path) -> None:
        so = tmp_path / "so.jsonl"
        ghi_su_kien(so, _nap_rut(-100.0))
        moi = cap_nhat_dinh(DinhEquityBenVung(1100.0, "USDT"), tong_hien_tai=1000.0, stake_currency="USDT",
                            so_su_kien=so)
        so.write_bytes(so.read_bytes().replace(b"-100.0", b"-10.0"))
        with pytest.raises(DinhEquityError, match="append-only"):
            cap_nhat_dinh(moi, tong_hien_tai=1000.0, stake_currency="USDT", so_su_kien=so)

    def test_xoa_dong_DA_AP_thi_TU_CHOI(self, tmp_path) -> None:
        so = tmp_path / "so.jsonl"
        ghi_su_kien(so, _nap_rut(-100.0))
        moi = cap_nhat_dinh(DinhEquityBenVung(1100.0, "USDT"), tong_hien_tai=1000.0, stake_currency="USDT",
                            so_su_kien=so)
        so.write_bytes(b"")
        with pytest.raises(DinhEquityError, match="append-only"):
            cap_nhat_dinh(moi, tong_hien_tai=1000.0, stake_currency="USDT", so_su_kien=so)

    def test_file_trang_thai_TRUOC_TD_0426_doc_duoc_va_ap_moi_su_kien(self, tmp_path) -> None:
        tt = tmp_path / "equity_peak_state.json"
        tt.write_text(json.dumps({"dinh": 1100.0, "stake_currency": "USDT"}), encoding="utf-8")
        cu = doc_dinh_equity(tt)
        assert (cu.so_su_kien_da_ap, cu.bam_su_kien_da_ap) == (0, BAM_RONG)
        so = duong_dan_so_su_kien(tt)
        ghi_su_kien(so, _nap_rut(-100.0))
        assert cap_nhat_dinh(cu, tong_hien_tai=1000.0, stake_currency="USDT", so_su_kien=so).dinh == 1000.0

    @pytest.mark.parametrize(
        "sk",
        [
            SuKienDinh(loai=NAP_RUT, stake_currency="USDT", luc_utc="x", ghi_chu="x", so_tien=0.0),
            SuKienDinh(loai=NAP_RUT, stake_currency="USDT", luc_utc="x", ghi_chu="", so_tien=5.0),
            SuKienDinh(loai="HALT", stake_currency="USDT", luc_utc="x", ghi_chu="x"),
        ],
    )
    def test_ghi_su_kien_sai_hinh_thi_TU_CHOI_truoc_khi_ghi(self, tmp_path, sk) -> None:
        so = tmp_path / "so.jsonl"
        with pytest.raises(DinhEquityError):
            ghi_su_kien(so, sk)
        assert not so.exists()

    def test_lech_don_vi_thi_TU_CHOI(self, tmp_path) -> None:
        so = tmp_path / "so.jsonl"
        ghi_su_kien(so, SuKienDinh(loai=NAP_RUT, stake_currency="USDC", luc_utc="x", ghi_chu="x", so_tien=-1.0))
        with pytest.raises(DinhEquityError, match="đơn vị"):
            cap_nhat_dinh(DinhEquityBenVung(1100.0, "USDT"), tong_hien_tai=1000.0, stake_currency="USDT",
                          so_su_kien=so)

    def test_rut_vuot_dinh_thi_TU_CHOI(self, tmp_path) -> None:
        so = tmp_path / "so.jsonl"
        ghi_su_kien(so, _nap_rut(-2000.0))
        with pytest.raises(DinhEquityError, match="≤ 0"):
            cap_nhat_dinh(DinhEquityBenVung(1100.0, "USDT"), tong_hien_tai=500.0, stake_currency="USDT",
                          so_su_kien=so)

    def test_dong_cuoi_ghi_do_thi_TU_CHOI(self, tmp_path) -> None:
        so = tmp_path / "so.jsonl"
        so.write_bytes(b'{"loai": "ABORT"')
        with pytest.raises(DinhEquityError, match="ghi dở"):
            doc_so_su_kien(so)
