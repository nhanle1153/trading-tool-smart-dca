"""TD-0240 — `src/tool_d/reporting/freqtrade_db.py`: đọc DB Freqtrade
thật qua chính ORM của Freqtrade (`init_db()` + `Trade.get_trades()`).

Test TÍCH HỢP THẬT (không mock ORM) — tạo Trade/Order bằng chính lớp
`Trade`/`Order` của Freqtrade trên một DB SQLite TẠM (`tmp_path`, không
đụng DB thật của repo — khác hẳn bài học `TD-0239`: ở đây `db_url` LUÔN
là tham số, module không có mặc định ngầm nào để lỡ tay chạm sản xuất).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from tool_d.reporting.freqtrade_db import FreqtradeDbError, doc_danh_sach_lenh, doc_db_url_tu_config


def _db_url(tmp_path: Path, ten: str = "test.sqlite") -> str:
    return f"sqlite:///{tmp_path / ten}"


def _tao_lenh(
    *,
    db_url: str,
    pair: str = "BTC/USDT:USDT",
    is_open: bool = False,
    is_short: bool = False,
    exit_reason: str | None = "TIME_STOP",
    close_profit_abs: float | None = 5.0,
    so_order_entry: int = 1,
) -> None:
    """Tạo MỘT trade + `so_order_entry` order entry đã khớp, bằng đúng
    lớp `Trade`/`Order` của Freqtrade — không tự viết SQL (LD-09)."""
    from freqtrade.enums import TradingMode
    from freqtrade.persistence import Order, Trade, init_db

    init_db(db_url)
    now = datetime.now(timezone.utc)
    t = Trade(
        pair=pair,
        stake_amount=10.0,
        amount=0.01,
        open_rate=50000.0,
        open_date=now,
        is_open=is_open,
        close_date=None if is_open else now,
        exchange="binance",
        fee_open=0.001,
        fee_close=0.001,
        is_short=is_short,
        leverage=3.0,
        trading_mode=TradingMode.FUTURES,
        exit_reason=None if is_open else exit_reason,
        close_profit_abs=None if is_open else close_profit_abs,
        close_profit=None if is_open else 0.1,
    )
    Trade.session.add(t)
    Trade.commit()

    for i in range(so_order_entry):
        Trade.session.add(
            Order(
                ft_trade_id=t.id,
                ft_pair=pair,
                ft_is_open=False,
                ft_order_side=t.entry_side,
                ft_amount=0.01,
                ft_price=50000.0,
                order_id=f"ORD-{t.id}-{i}",
                status="closed",
                order_type="limit",
                side=t.entry_side,
                price=50000.0,
                amount=0.01,
                filled=0.01,
                order_date=now,
                order_filled_date=now,
            )
        )
    Trade.commit()


class TestDocDanhSachLenh:
    def test_db_chua_tung_ton_tai_tra_rong_khong_phai_loi(self, tmp_path: Path) -> None:
        """`init_db()` tự tạo bảng nếu chưa có — DB rỗng là "chưa có
        lệnh nào", KHÔNG phải lỗi đọc (N6)."""
        ket_qua = doc_danh_sach_lenh(_db_url(tmp_path))
        assert ket_qua == []

    def test_doc_dung_mot_lenh_da_dong(self, tmp_path: Path) -> None:
        db_url = _db_url(tmp_path)
        _tao_lenh(db_url=db_url, exit_reason="TIME_STOP", close_profit_abs=5.0, so_order_entry=2)
        ket_qua = doc_danh_sach_lenh(db_url)
        assert len(ket_qua) == 1
        lenh = ket_qua[0]
        assert lenh.is_open is False
        assert lenh.is_short is False
        assert lenh.exit_reason == "TIME_STOP"
        assert lenh.close_profit_abs == 5.0
        assert lenh.so_tranche_khop == 2, "phải đếm ĐÚNG số order entry_side đã status=closed"

    def test_lenh_con_mo_khong_doc_close_profit_abs(self, tmp_path: Path) -> None:
        """Bẫy đã tra trong `tu-dien-du-lieu.md`: `close_profit_abs` chỉ
        là TỔNG khi trade đã đóng hẳn — với lệnh còn mở, đọc nó có thể
        chỉ là lãi của lần thoát từng phần cuối, không phải PnL thật.
        Module này KHÔNG đọc nó khi `is_open=True` (trả `None`)."""
        db_url = _db_url(tmp_path)
        _tao_lenh(db_url=db_url, is_open=True)
        ket_qua = doc_danh_sach_lenh(db_url)
        assert ket_qua[0].is_open is True
        assert ket_qua[0].close_profit_abs is None

    def test_dem_dung_tranche_khong_lan_lenh_khac(self, tmp_path: Path) -> None:
        db_url = _db_url(tmp_path)
        _tao_lenh(db_url=db_url, pair="BTC/USDT:USDT", so_order_entry=1)
        _tao_lenh(db_url=db_url, pair="ETH/USDT:USDT", so_order_entry=3)
        ket_qua = {l.so_tranche_khop for l in doc_danh_sach_lenh(db_url)}
        assert ket_qua == {1, 3}

    def test_short_duoc_doc_dung(self, tmp_path: Path) -> None:
        db_url = _db_url(tmp_path)
        _tao_lenh(db_url=db_url, is_short=True)
        assert doc_danh_sach_lenh(db_url)[0].is_short is True


class TestDocDbUrlTuConfig:
    def test_doc_dung_khoa_db_url(self, tmp_path: Path) -> None:
        import json

        p = tmp_path / "config.json"
        p.write_text(json.dumps({"db_url": "sqlite:////tmp/x.sqlite"}), encoding="utf-8")
        assert doc_db_url_tu_config(p) == "sqlite:////tmp/x.sqlite"

    def test_thieu_khoa_thi_raise(self, tmp_path: Path) -> None:
        import json

        p = tmp_path / "config.json"
        p.write_text(json.dumps({"khong_co_db_url": True}), encoding="utf-8")
        with pytest.raises(FreqtradeDbError):
            doc_db_url_tu_config(p)
