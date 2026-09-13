"""TD-0241 (`DR-D11-03`) — `tool_d.ops.risk_supervisor_daemon`, tầng THUẦN
`chay_mot_vong_giam_sat()`. Cùng khuôn `test_ops_heartbeat_watchdog.py`:
mọi lời gọi mạng nhận qua tham số callable, không phụ thuộc bot/sàn thật.
`main()` là khung CLI mỏng (`# pragma: no cover`), không test sâu ở đây —
xem smoke test thủ công trong `DR-D11-03`.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from tool_d.api_client.binance_public import BinanceBreakerMoError, BinancePrivateApiError
from tool_d.ops.risk_supervisor_daemon import chay_mot_vong_giam_sat
from tool_d.risk_supervisor import TrangThaiBenVung, TrangThaiBreaker

T0 = datetime(2026, 9, 14, 0, 0, 0, tzinfo=timezone.utc)


def _sach() -> TrangThaiBenVung:
    return TrangThaiBenVung(breaker=TrangThaiBreaker())


class TestDuongSachKhongThanhLy:
    def test_khong_lenh_thanh_ly_khong_dung_bot(self) -> None:
        goi_dung_bot: list[str] = []
        trang_thai_moi, nen_dung = chay_mot_vong_giam_sat(
            _sach(),
            now=T0,
            doc_account_fn=lambda: {"totalMarginBalance": "100"},
            doc_position_fn=lambda: [],
            doc_force_orders_fn=lambda: [],
            doc_breaker_hien_tai_fn=lambda: TrangThaiBreaker(),
            tu_thoi_diem_ms=1000,
            dung_bot_fn=lambda: goi_dung_bot.append("goi") or {"status": "ok"},
        )
        assert nen_dung is False
        assert trang_thai_moi.la_thanh_ly is False
        assert goi_dung_bot == []

    def test_lenh_thanh_ly_cu_hon_moc_khong_kich_hoat(self) -> None:
        _, nen_dung = chay_mot_vong_giam_sat(
            _sach(),
            now=T0,
            doc_account_fn=lambda: {},
            doc_position_fn=lambda: [],
            doc_force_orders_fn=lambda: [{"time": 500}],
            doc_breaker_hien_tai_fn=lambda: TrangThaiBreaker(),
            tu_thoi_diem_ms=1000,
            dung_bot_fn=lambda: (_ for _ in ()).throw(AssertionError("KHÔNG được gọi")),
        )
        assert nen_dung is False


class TestPhatHienThanhLyGoiDungBot:
    def test_lenh_thanh_ly_moi_kich_hoat_dung_bot_va_dat_co(self) -> None:
        goi_dung_bot: list[str] = []
        trang_thai_moi, nen_dung = chay_mot_vong_giam_sat(
            _sach(),
            now=T0,
            doc_account_fn=lambda: {},
            doc_position_fn=lambda: [],
            doc_force_orders_fn=lambda: [{"time": 5000}],
            doc_breaker_hien_tai_fn=lambda: TrangThaiBreaker(),
            tu_thoi_diem_ms=1000,
            dung_bot_fn=lambda: goi_dung_bot.append("goi") or {"status": "stopping trader ..."},
        )
        assert nen_dung is True
        assert trang_thai_moi.la_thanh_ly is True
        assert goi_dung_bot == ["goi"]

    def test_dung_bot_raise_thi_propagate_khong_bi_nuot(self) -> None:
        """R4/'KHÔNG nuốt' — `main()` bắt lỗi này ở tầng ngoài, không phải
        ở đây; `chay_mot_vong_giam_sat` không được tự âm thầm bỏ qua."""

        def dung_bot_loi() -> dict:
            raise RuntimeError("mô phỏng: không dừng được bot")

        with pytest.raises(RuntimeError, match="không dừng được bot"):
            chay_mot_vong_giam_sat(
                _sach(),
                now=T0,
                doc_account_fn=lambda: {},
                doc_position_fn=lambda: [],
                doc_force_orders_fn=lambda: [{"time": 5000}],
                doc_breaker_hien_tai_fn=lambda: TrangThaiBreaker(),
                tu_thoi_diem_ms=1000,
                dung_bot_fn=dung_bot_loi,
            )


class TestDungHanBreakerCungKichHoatDungBot:
    """§6.6(2): `dung_han` (418) 'CÙNG CẤP' `LIQUIDATED` — cũng phải gọi
    `dung_bot_fn` dù `force_orders` không hề có lệnh thanh lý nào."""

    def test_breaker_dung_han_du_khong_co_lenh_thanh_ly(self) -> None:
        goi_dung_bot: list[str] = []
        trang_thai_moi, nen_dung = chay_mot_vong_giam_sat(
            _sach(),
            now=T0,
            doc_account_fn=lambda: {},
            doc_position_fn=lambda: [],
            doc_force_orders_fn=lambda: [],
            doc_breaker_hien_tai_fn=lambda: TrangThaiBreaker(dung_han=True),
            tu_thoi_diem_ms=1000,
            dung_bot_fn=lambda: goi_dung_bot.append("goi") or {"status": "ok"},
        )
        assert nen_dung is True
        assert trang_thai_moi.breaker.dung_han is True
        assert goi_dung_bot == ["goi"]


class TestDaDungTuTruocKhongDocMangNua:
    """Vòng trước đã đặt cờ đỏ ⇒ vòng này KHÔNG được đọc mạng lần nữa —
    'CỜ ĐỎ, không tự gỡ' áp cả khi bị gọi lại do lỗi vận hành."""

    def test_da_thanh_ly_tu_truoc_khong_goi_bat_ky_ham_mang_nao(self) -> None:
        trang_thai_da_dung = TrangThaiBenVung(breaker=TrangThaiBreaker(), la_thanh_ly=True)

        def raise_neu_goi() -> object:
            raise AssertionError("KHÔNG được gọi lại mạng sau khi đã dừng")

        trang_thai_moi, nen_dung = chay_mot_vong_giam_sat(
            trang_thai_da_dung,
            now=T0,
            doc_account_fn=raise_neu_goi,
            doc_position_fn=raise_neu_goi,
            doc_force_orders_fn=raise_neu_goi,
            doc_breaker_hien_tai_fn=raise_neu_goi,
            tu_thoi_diem_ms=1000,
            dung_bot_fn=raise_neu_goi,
        )
        assert nen_dung is True
        assert trang_thai_moi == trang_thai_da_dung

    def test_da_dung_han_tu_truoc_khong_goi_mang(self) -> None:
        trang_thai_da_dung = TrangThaiBenVung(breaker=TrangThaiBreaker(dung_han=True))

        def raise_neu_goi() -> object:
            raise AssertionError("KHÔNG được gọi lại mạng sau khi đã dừng")

        _, nen_dung = chay_mot_vong_giam_sat(
            trang_thai_da_dung,
            now=T0,
            doc_account_fn=raise_neu_goi,
            doc_position_fn=raise_neu_goi,
            doc_force_orders_fn=raise_neu_goi,
            doc_breaker_hien_tai_fn=raise_neu_goi,
            tu_thoi_diem_ms=1000,
            dung_bot_fn=raise_neu_goi,
        )
        assert nen_dung is True


class TestMotEndpointLoiKhongLamHongCaVong:
    def test_force_orders_loi_khong_suy_dien_thanh_khong_thanh_ly(self) -> None:
        """N6 — đọc lỗi PHẢI khác 'đã đo, không thanh lý'. Vòng này chỉ
        giữ nguyên `la_thanh_ly` cũ (False), KHÔNG chủ động gán False mới
        từ một lần đọc thất bại (khác biệt không quan sát được ở state
        ban đầu False → False, nhưng hành vi code phải đi qua nhánh
        'không cập nhật', không phải nhánh 'cập nhật thành False')."""

        def force_orders_loi() -> list[dict]:
            raise BinancePrivateApiError("mô phỏng lỗi mạng")

        trang_thai_moi, nen_dung = chay_mot_vong_giam_sat(
            _sach(),
            now=T0,
            doc_account_fn=lambda: {"totalMarginBalance": "100"},
            doc_position_fn=lambda: [],
            doc_force_orders_fn=force_orders_loi,
            doc_breaker_hien_tai_fn=lambda: TrangThaiBreaker(so_loi_lien_tiep=1),
            tu_thoi_diem_ms=1000,
            dung_bot_fn=lambda: (_ for _ in ()).throw(AssertionError("KHÔNG được gọi")),
        )
        assert nen_dung is False
        assert trang_thai_moi.la_thanh_ly is False

    def test_mot_endpoint_loi_khong_lam_mat_endpoint_khac(self) -> None:
        """§6.6(4) — `account` lỗi không được làm mất kết quả `force_orders`
        đã đọc thành công (kiểm gián tiếp qua việc thanh lý vẫn được phát
        hiện dù `account` đọc lỗi)."""

        def account_loi() -> dict:
            raise BinanceBreakerMoError("breaker đang mở")

        trang_thai_moi, nen_dung = chay_mot_vong_giam_sat(
            _sach(),
            now=T0,
            doc_account_fn=account_loi,
            doc_position_fn=lambda: [],
            doc_force_orders_fn=lambda: [{"time": 5000}],
            doc_breaker_hien_tai_fn=lambda: TrangThaiBreaker(),
            tu_thoi_diem_ms=1000,
            dung_bot_fn=lambda: {"status": "ok"},
        )
        assert nen_dung is True
        assert trang_thai_moi.la_thanh_ly is True
