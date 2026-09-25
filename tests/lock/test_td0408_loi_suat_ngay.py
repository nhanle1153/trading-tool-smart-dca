"""TD-0408 — bộ đo lợi suất ngày của rổ (`tool_d.ro_funding_do`) + nhánh E1 (`DR-D0-IQ0003` §13 a, §14).

Luật viết TRƯỚC suất: quan sát = ngày lịch UTC từ ngày mở lệnh đầu tiên tới ngày cuối cửa sổ; lợi suất ngày = Σ
`profit_abs` lệnh ĐÓNG trong ngày / vốn rổ; ngày không đóng lệnh = 0; `mean − h·std/√n` với `h = √(2·ln N)`.
Ca chạy trên lệnh THẬT do Freqtrade xuất nằm ở `test_td0400_ro_funding.py::TestBacktestThat` (cùng fixture backtest).
"""

from __future__ import annotations

import ast
import math
import statistics
from datetime import date
from pathlib import Path

import pytest

from tool_d.gates.dsr import dsr_hurdle
from tool_d.ro_funding_do import RoFundingDoError, do_loi_suat_ngay

TU, DEN = date(2025, 1, 1), date(2025, 1, 11)  # ngày cuối = 10/01
VON = 1000.0


def _lenh(mo: str, dong: str, pnl: float, *, short: bool = False, funding: float = 0.0, thoat: str = "CAN_RO") -> dict:
    return {"pair": "X/USDT:USDT", "open_date": mo, "close_date": dong, "profit_abs": pnl, "is_short": short,
            "funding_fees": funding, "exit_reason": thoat}


LENH = [
    _lenh("2025-01-03 00:00:00+00:00", "2025-01-05 00:00:00+00:00", 10.0, funding=4.0),
    _lenh("2025-01-03 00:00:00+00:00", "2025-01-05 00:00:00+00:00", -4.0, short=True, funding=1.0),
    _lenh("2025-01-05 00:00:00+00:00", "2025-01-08 10:00:00+00:00", 6.0, short=True, funding=2.0, thoat="stop_loss"),
]


class TestChuoiNgay:
    def test_gop_theo_ngay_dong_va_ngay_khong_la_0(self) -> None:
        kq = do_loi_suat_ngay(LENH, von_usdt=VON, tu=TU, den=DEN, n_trials=114)
        assert kq["ngay_dau"] == "2025-01-03" and kq["n_ngay"] == 8  # 03 → 10
        assert kq["chuoi_ngay"]["2025-01-05"] == pytest.approx(6.0 / VON)
        assert kq["chuoi_ngay"]["2025-01-08"] == pytest.approx(6.0 / VON)
        assert kq["chuoi_ngay"]["2025-01-04"] == 0.0 and kq["chuoi_ngay"]["2025-01-10"] == 0.0

    def test_chi_so_dung_cong_thuc(self) -> None:
        kq = do_loi_suat_ngay(LENH, von_usdt=VON, tu=TU, den=DEN, n_trials=114)
        gt = list(kq["chuoi_ngay"].values())
        assert kq["mean"] == pytest.approx(statistics.fmean(gt))
        assert kq["std"] == pytest.approx(statistics.stdev(gt))
        assert kq["h"] == pytest.approx(math.sqrt(2 * math.log(114))) == dsr_hurdle(114)
        assert kq["can_duoi"] == pytest.approx(kq["mean"] - kq["h"] * kq["std"] / math.sqrt(kq["n_ngay"]))

    def test_chi_ghi_funding_tach_chan_nhan_thoat(self) -> None:
        ghi = do_loi_suat_ngay(LENH, von_usdt=VON, tu=TU, den=DEN, n_trials=114)["chi_ghi"]
        assert ghi["tong_profit_abs"] == pytest.approx(12.0) and ghi["tong_funding_fees"] == pytest.approx(7.0)
        assert ghi["ty_phan_funding_trong_lai_rong"] == pytest.approx(7.0 / 12.0)
        assert ghi["tach_chan"]["long"]["so_lenh"] == 1 and ghi["tach_chan"]["short"]["so_lenh"] == 2
        assert ghi["nhan_thoat"] == {"CAN_RO": 2, "stop_loss": 1}

    def test_lai_rong_khong_duong_thi_ty_phan_funding_none(self) -> None:
        ghi = do_loi_suat_ngay([_lenh("2025-01-03", "2025-01-04", -1.0, funding=2.0)],
                               von_usdt=VON, tu=TU, den=DEN, n_trials=114)["chi_ghi"]
        assert ghi["ty_phan_funding_trong_lai_rong"] is None

    def test_moc_mili_giay_doc_duoc(self) -> None:
        """Freqtrade có nơi ghi mốc bằng mili-giây (bẫy đơn vị `doc_ket_qua`)."""
        ms = 1736294400000  # 2025-01-08 00:00 UTC
        kq = do_loi_suat_ngay([_lenh("2025-01-03 00:00:00+00:00", ms, 5.0)], von_usdt=VON, tu=TU, den=DEN, n_trials=114)
        assert kq["chuoi_ngay"]["2025-01-08"] == pytest.approx(5.0 / VON)


class TestFailClosed:
    def test_khong_lenh_thi_none_khong_phai_0(self) -> None:
        kq = do_loi_suat_ngay([], von_usdt=VON, tu=TU, den=DEN, n_trials=114)
        assert kq["mean"] is None and kq["can_duoi"] is None and kq["n_ngay"] == 0

    @pytest.mark.parametrize("truong", ["profit_abs", "close_date", "funding_fees", "is_short", "exit_reason"])
    def test_lenh_thieu_truong_thi_tu_choi(self, truong: str) -> None:
        t = dict(LENH[0])
        del t[truong]
        with pytest.raises(RoFundingDoError, match="thiếu trường"):
            do_loi_suat_ngay([t], von_usdt=VON, tu=TU, den=DEN, n_trials=114)

    def test_lenh_dong_ngoai_cua_so_thi_tu_choi(self) -> None:
        with pytest.raises(RoFundingDoError, match="ngoài"):
            do_loi_suat_ngay([_lenh("2025-01-03", "2025-01-12", 1.0)], von_usdt=VON, tu=TU, den=DEN, n_trials=114)

    def test_dong_dung_bien_den_thuoc_ngay_cuoi(self) -> None:
        """Ca thật (TD-0408): `force_exit` khi hết cửa sổ đóng ĐÚNG 00:00 của `den` ⇒ tính vào ngày cuối (10/01)."""
        kq = do_loi_suat_ngay([_lenh("2025-01-03", "2025-01-11 00:00:00+00:00", 3.0, thoat="force_exit")],
                              von_usdt=VON, tu=TU, den=DEN, n_trials=114)
        assert kq["chuoi_ngay"]["2025-01-10"] == pytest.approx(3.0 / VON) and "2025-01-11" not in kq["chuoi_ngay"]

    @pytest.mark.parametrize("von", [0, -1, None])
    def test_von_khong_hop_le_thi_tu_choi(self, von) -> None:
        with pytest.raises(RoFundingDoError, match="von_usdt"):
            do_loi_suat_ngay(LENH, von_usdt=von, tu=TU, den=DEN, n_trials=114)


class TestNhanhE1:
    NGUON = Path("entrypoints/run_backtest.py")

    def test_nhanh_ro_khong_goi_trich_lenh_za_va_consume_dung_mot_lan(self) -> None:
        van_ban = self.NGUON.read_text(encoding="utf-8")
        cay = ast.parse(van_ban)
        nhanh = [
            n for n in ast.walk(cay)
            if isinstance(n, ast.If) and "CHIEN_LUOC_RO" in ast.unparse(n.test)
        ]
        assert len(nhanh) == 1, "cần đúng một nhánh RoFunding sau con dấu"
        than = ast.unparse(ast.Module(body=nhanh[0].body, type_ignores=[]))
        assert "do_loi_suat_ngay(" in than and "ro_ngay.json" in than
        assert "lenh_tu_freqtrade" not in than and "ghi_bang_r" not in than
        assert van_ban.count("ledger.consume(") == 1  # TD-0313

    def test_zip_ket_qua_duoc_chep_vao_runs(self) -> None:
        assert "shutil.copy2(kq.duong_ket_qua, thu_muc_ra" in self.NGUON.read_text(encoding="utf-8")
