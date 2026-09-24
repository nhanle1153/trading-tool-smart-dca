"""TD-0403 — `gap_ms.py` trộn ngày giờ naive/aware, và sổ đo hỏng không được cướp giá SL.

Hai thứ được khoá, cả hai bắt nguồn từ lỗi ĐO ĐƯỢC trên dry-run D11 (24/09/2026, 07:01:38 và 07:55:53):
1. `sinh_ban_ghi_doi_sl()` chịu được `order_date`/`order_update_date`/`moc_khop_entry` trộn naive (nạp từ SQLite) với
   aware (vừa tạo trong bộ nhớ) — trước đây ném `TypeError` ở `sorted(...)` và `m <= moi.order_date`.
2. `ZoneAbsorption.custom_stoploss()` VẪN TRẢ GIÁ SL khi `_ghi_gap_ms()` nổ. Freqtrade nuốt exception của callback;
   nếu sổ đo chạy trước `return` thì SL không được cập nhật vòng đó — sổ đo cướp mất lệnh bảo vệ vốn.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from tool_d.gap_ms import LenhSl, sinh_ban_ghi_doi_sl

REPO_ROOT = Path(__file__).resolve().parents[2]
UTC = timezone.utc
T0 = datetime(2026, 1, 1, 0, 0, 0)  # naive — đúng dạng SQLite trả về


def _lenh(order_id, status, amount, order_date, order_update_date=None) -> LenhSl:
    return LenhSl(order_id=order_id, status=status, amount=amount,
                  order_date=order_date, order_update_date=order_update_date)


def _bo_ba(*, naive_dau: bool, moc_aware: bool):
    """Một cặp huỷ→tạo-lại cách nhau ĐÚNG 22 ms, hai mốc entry. `naive_dau`: lệnh cũ naive, lệnh mới aware."""
    cu_ngay, moi_ngay = T0, T0 + timedelta(seconds=60, milliseconds=22)
    cu_capnhat = T0 + timedelta(seconds=60)
    if naive_dau:
        moi_ngay = moi_ngay.replace(tzinfo=UTC)  # lệnh vừa tạo trong bộ nhớ
    else:
        cu_ngay, cu_capnhat, moi_ngay = (x.replace(tzinfo=UTC) for x in (cu_ngay, cu_capnhat, moi_ngay))
    lenh_sl = [_lenh("SL1", "canceled", 10.0, cu_ngay, cu_capnhat), _lenh("SL2", "open", 20.0, moi_ngay)]
    moc = [T0, T0 + timedelta(seconds=30)]  # hai tranche đã khớp TRƯỚC lệnh SL mới
    if moc_aware:
        moc = [m.replace(tzinfo=UTC) for m in moc]
    return lenh_sl, moc


class TestTronNaiveAware:
    def test_lenh_sl_tron_naive_aware_van_do_dung_gap_ms(self) -> None:
        lenh_sl, moc = _bo_ba(naive_dau=True, moc_aware=False)
        (bg,) = sinh_ban_ghi_doi_sl(lenh_sl=lenh_sl, moc_khop_entry=moc, trade_id=1, sl_price=100.0, nguon="dry_run")
        assert bg["gap_ms"] == pytest.approx(22.0)
        assert bg["tranche"] == 2

    def test_moc_khop_entry_tron_naive_aware_van_dem_dung_tranche(self) -> None:
        lenh_sl, moc = _bo_ba(naive_dau=False, moc_aware=True)
        moc = [moc[0].replace(tzinfo=None), moc[1]]  # mốc đầu naive, mốc sau aware
        (bg,) = sinh_ban_ghi_doi_sl(lenh_sl=lenh_sl, moc_khop_entry=moc, trade_id=1, sl_price=100.0, nguon="dry_run")
        assert bg["tranche"] == 2

    def test_tron_hay_khong_tron_cho_cung_ket_qua(self) -> None:
        """Cùng SỰ KIỆN, khác dạng ghi ngày giờ ⇒ cùng `gap_ms`/`tranche`/khối lượng (chỉ `ts` giữ dạng đầu vào)."""
        ket_qua = []
        for naive_dau, moc_aware in ((True, False), (False, True), (True, True), (False, False)):
            lenh_sl, moc = _bo_ba(naive_dau=naive_dau, moc_aware=moc_aware)
            (bg,) = sinh_ban_ghi_doi_sl(lenh_sl=lenh_sl, moc_khop_entry=moc, trade_id=1, sl_price=100.0, nguon="dry_run")
            ket_qua.append({k: v for k, v in bg.items() if k != "ts"})
        assert all(k == ket_qua[0] for k in ket_qua)

    def test_aware_mui_gio_khac_duoc_quy_doi_dung(self) -> None:
        """Aware ở UTC+7 KHÔNG được coi như UTC: cùng một khoảnh khắc, `gap_ms` vẫn 22 ms."""
        gmt7 = timezone(timedelta(hours=7))
        cu = T0.replace(tzinfo=UTC)
        moi = (T0 + timedelta(seconds=60, milliseconds=22)).replace(tzinfo=UTC).astimezone(gmt7)
        lenh_sl = [_lenh("SL1", "canceled", 10.0, cu, cu + timedelta(seconds=60)), _lenh("SL2", "open", 20.0, moi)]
        (bg,) = sinh_ban_ghi_doi_sl(lenh_sl=lenh_sl, moc_khop_entry=[cu], trade_id=1, sl_price=100.0, nguon="dry_run")
        assert bg["gap_ms"] == pytest.approx(22.0)


def _chien_luoc():
    """Nạp chiến lược THẬT bằng `import` (không `spec_from_file_location`) để công cụ phá-thật trong bộ nhớ thấy được."""
    duong = str(REPO_ROOT / "user_data/strategies")
    if duong not in sys.path:
        sys.path.insert(0, duong)
    import ZoneAbsorption  # noqa: PLC0415

    s = ZoneAbsorption.ZoneAbsorption(config={"stake_currency": "USDT", "exchange": {"name": "binance"}})
    s._doc_ke_hoach = lambda trade: (SimpleNamespace(sl=95.0), None, None)
    return s


TRADE = SimpleNamespace(pair="TRUMP/USDT:USDT", is_short=False, leverage=3)


class TestCustomStoplossKhongBiSoDoCuopGia:
    @staticmethod
    def _lam_no(s) -> None:
        def no(trade, *, sl_price):
            raise TypeError("can't compare offset-naive and offset-aware datetimes")

        s._ghi_gap_ms = no

    def test_sl_van_duoc_tra_ve_khi_ghi_gap_ms_no(self) -> None:
        from freqtrade.strategy import stoploss_from_absolute

        s = _chien_luoc()
        self._lam_no(s)
        kq = s.custom_stoploss("TRUMP/USDT:USDT", TRADE, datetime(2026, 9, 24, tzinfo=UTC), 100.0, 0.0)
        assert kq is not None and kq > 0
        assert kq == pytest.approx(stoploss_from_absolute(95.0, 100.0, is_short=False, leverage=3))

    def test_loi_ghi_gap_ms_duoc_log_error_khong_im(self, caplog) -> None:
        s = _chien_luoc()
        self._lam_no(s)
        with caplog.at_level(logging.ERROR):
            s.custom_stoploss("TRUMP/USDT:USDT", TRADE, datetime(2026, 9, 24, tzinfo=UTC), 100.0, 0.0)
        loi = [r for r in caplog.records if r.levelno >= logging.ERROR]
        assert loi and "TD-0403" in loi[0].getMessage() and "TRUMP/USDT:USDT" in loi[0].getMessage()
