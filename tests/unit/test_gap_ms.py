"""TD-0244 — bộ sinh `gap_ms` (`src/tool_d/gap_ms.py`), §8.3 LD-21, D2c.

Test ĐƠN VỊ cho hàm thuần. Phần đo trên lệnh THẬT (D10, môi trường live
tối thiểu — `DR-D11-01`/`DR-D11-02`) thuộc chặng nối vào `ZoneAbsorption.
custom_stoploss()`, sau khi phiên sở hữu file đó commit — cùng bài học
TD-0168 áp cho `test_take_profit.py`: một hàm chỉ được canh bằng mẫu dựng
tay chưa chắc nằm trên đường sản xuất.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from tool_d.gap_ms import LOAI_DOI_SL, LenhSl, sinh_ban_ghi_doi_sl

T0 = datetime(2026, 1, 1, 0, 0, 0)


def _lenh(order_id: str, status: str, amount: float, order_date: datetime,
          order_update_date: datetime | None = None) -> LenhSl:
    return LenhSl(
        order_id=order_id,
        status=status,
        amount=amount,
        order_date=order_date,
        order_update_date=order_update_date,
    )


class TestLenhDauTienKhongSinhBanGhi:
    def test_mot_lenh_sl_duy_nhat_khong_co_gi_de_doi(self):
        """Lệnh SL đặt lúc tranche 1 khớp — chưa có gì để ĐỔI."""
        lenh_sl = [_lenh("SL1", "open", 10.0, T0)]
        ket_qua = sinh_ban_ghi_doi_sl(
            lenh_sl=lenh_sl, moc_khop_entry=[T0], trade_id=1,
            sl_price=100.0, nguon="live",
        )
        assert ket_qua == []

    def test_khong_co_lenh_sl_nao(self):
        assert sinh_ban_ghi_doi_sl(
            lenh_sl=[], moc_khop_entry=[], trade_id=1, sl_price=100.0, nguon="live",
        ) == []


class TestMotLanDoiKhoiLuong:
    def test_sinh_dung_mot_ban_ghi_voi_gap_ms_dung(self):
        """Tranche 1 → SL1 (amount 10). Tranche 2 khớp lúc T0+10p → huỷ SL1
        (order_update_date = lúc huỷ) → SL2 tạo lại 3,2s sau (amount 20)."""
        khop_tranche2 = T0 + timedelta(minutes=10)
        huy_luc = khop_tranche2 + timedelta(milliseconds=100)
        tao_lai_luc = huy_luc + timedelta(milliseconds=3200)
        lenh_sl = [
            _lenh("SL1", "canceled", 10.0, T0, order_update_date=huy_luc),
            _lenh("SL2", "open", 20.0, tao_lai_luc),
        ]
        ket_qua = sinh_ban_ghi_doi_sl(
            lenh_sl=lenh_sl,
            moc_khop_entry=[T0, khop_tranche2],
            trade_id=42,
            sl_price=95.5,
            nguon="live",
        )
        assert len(ket_qua) == 1
        bg = ket_qua[0]
        assert bg["loai"] == LOAI_DOI_SL == "DOI_SL"
        assert bg["nguon"] == "live"
        assert bg["trade_id"] == 42
        assert bg["tranche"] == 2  # hai mốc khớp <= tao_lai_luc
        assert bg["sl_price"] == 95.5
        assert bg["sl_qty_old"] == 10.0
        assert bg["sl_qty_new"] == 20.0
        assert bg["sl_order_id_old"] == "SL1"
        assert bg["sl_order_id_new"] == "SL2"
        assert bg["gap_ms"] == 3200.0
        assert bg["ts"] == tao_lai_luc.isoformat()

    def test_thu_tu_lenh_sl_dao_nguoc_trong_input_van_dung(self):
        """Hàm tự sắp theo `order_date` — người gọi không cần sắp trước."""
        huy_luc = T0 + timedelta(seconds=1)
        tao_lai_luc = huy_luc + timedelta(seconds=2)
        lenh_sl = [
            _lenh("SL2", "open", 20.0, tao_lai_luc),
            _lenh("SL1", "canceled", 10.0, T0, order_update_date=huy_luc),
        ]
        ket_qua = sinh_ban_ghi_doi_sl(
            lenh_sl=lenh_sl, moc_khop_entry=[T0], trade_id=1,
            sl_price=100.0, nguon="dry_run",
        )
        assert len(ket_qua) == 1
        assert ket_qua[0]["gap_ms"] == 2000.0


class TestHaiLanDoiLienTiep:
    def test_sinh_hai_ban_ghi_doc_lap(self):
        """Tranche 1→2→3: hai lần đổi khối lượng, hai bản ghi riêng."""
        t_tranche2 = T0 + timedelta(minutes=5)
        t_tranche3 = T0 + timedelta(minutes=15)
        huy1 = t_tranche2 + timedelta(milliseconds=50)
        tao2 = huy1 + timedelta(milliseconds=1500)
        huy2 = t_tranche3 + timedelta(milliseconds=80)
        tao3 = huy2 + timedelta(milliseconds=4800)
        lenh_sl = [
            _lenh("SL1", "canceled", 10.0, T0, order_update_date=huy1),
            _lenh("SL2", "canceled", 20.0, tao2, order_update_date=huy2),
            _lenh("SL3", "open", 30.0, tao3),
        ]
        ket_qua = sinh_ban_ghi_doi_sl(
            lenh_sl=lenh_sl,
            moc_khop_entry=[T0, t_tranche2, t_tranche3],
            trade_id=7,
            sl_price=88.0,
            nguon="live",
        )
        assert len(ket_qua) == 2
        assert ket_qua[0]["sl_order_id_old"] == "SL1"
        assert ket_qua[0]["sl_order_id_new"] == "SL2"
        assert ket_qua[0]["gap_ms"] == 1500.0
        assert ket_qua[0]["tranche"] == 2
        assert ket_qua[1]["sl_order_id_old"] == "SL2"
        assert ket_qua[1]["sl_order_id_new"] == "SL3"
        assert ket_qua[1]["gap_ms"] == 4800.0
        assert ket_qua[1]["tranche"] == 3


class TestKhongSuyDoanKhiThieuDuLieu:
    """N6 — cấm bịa `gap_ms` khi không có mốc huỷ đọc được."""

    def test_thieu_order_update_date_thi_bo_qua_khong_bia_gap(self):
        lenh_sl = [
            _lenh("SL1", "canceled", 10.0, T0, order_update_date=None),
            _lenh("SL2", "open", 20.0, T0 + timedelta(seconds=1)),
        ]
        ket_qua = sinh_ban_ghi_doi_sl(
            lenh_sl=lenh_sl, moc_khop_entry=[T0], trade_id=1,
            sl_price=100.0, nguon="live",
        )
        assert ket_qua == []

    def test_lenh_cu_khong_o_trang_thai_canceled_thi_bo_qua(self):
        """Hai lệnh SL 'open' đồng thời không phải một cặp huỷ→tạo-lại hợp lệ."""
        lenh_sl = [
            _lenh("SL1", "open", 10.0, T0),
            _lenh("SL2", "open", 20.0, T0 + timedelta(seconds=1)),
        ]
        ket_qua = sinh_ban_ghi_doi_sl(
            lenh_sl=lenh_sl, moc_khop_entry=[T0], trade_id=1,
            sl_price=100.0, nguon="live",
        )
        assert ket_qua == []


class TestDuTruongKhongThua:
    """L-Z44 lesson (`test_lz44_khai_lai_hang_so_supervisor.py`, TD-0241):
    một trường bị khai lại mà KHÔNG nằm trong bảng đối chiếu vẫn nằm ngoài
    tầm canh bốn ngày liền, dù mọi test hỏi "bốn cái kia có khớp không".
    Câu phải hỏi là "có ĐÚNG BẤY NHIÊU cái không" — kiểm bằng tập khoá,
    không phải bằng loại trừ."""

    KHOA_BAT_BUOC = frozenset(
        {
            "loai",
            "nguon",
            "ts",
            "trade_id",
            "tranche",
            "sl_price",
            "sl_qty_old",
            "sl_qty_new",
            "sl_order_id_old",
            "sl_order_id_new",
            "gap_ms",
        }
    )

    def test_ban_ghi_co_dung_khoa_khong_thieu_khong_thua(self):
        """Chín trường bắt buộc của spec §8.3 (dòng 2669-2671:
        ts/trade_id/tranche/sl_price/sl_qty_old/sl_qty_new/sl_order_id_old/
        sl_order_id_new/gap_ms) cộng `loai`/`nguon` (TD-0144/TD-0201, cửa
        ghi Decision Log đòi hai trường này để dựng khoá + phân loại
        nguồn) — ĐÚNG mười một, không hơn không kém."""
        huy_luc = T0 + timedelta(seconds=1)
        tao_lai_luc = huy_luc + timedelta(seconds=2)
        lenh_sl = [
            _lenh("SL1", "canceled", 10.0, T0, order_update_date=huy_luc),
            _lenh("SL2", "open", 20.0, tao_lai_luc),
        ]
        ket_qua = sinh_ban_ghi_doi_sl(
            lenh_sl=lenh_sl, moc_khop_entry=[T0], trade_id=1,
            sl_price=100.0, nguon="live",
        )
        assert len(ket_qua) == 1
        assert set(ket_qua[0].keys()) == self.KHOA_BAT_BUOC


class TestGoiLaiKhongSinhKhacBiet:
    """Bất biến khiến việc KHÔNG giữ trạng thái tiến trình an toàn (né hình
    dạng lỗi MT-40/MT-41): gọi lại với cùng đầu vào phải cho cùng bản ghi
    hệt nhau, kể cả `dedup_key` — cửa ghi (`ledger.decision_log`) mới là nơi
    chống trùng, không phải hàm này."""

    def test_hai_lan_goi_cung_du_lieu_cho_cung_ket_qua(self):
        huy_luc = T0 + timedelta(seconds=1)
        tao_lai_luc = huy_luc + timedelta(seconds=5)
        lenh_sl = [
            _lenh("SL1", "canceled", 10.0, T0, order_update_date=huy_luc),
            _lenh("SL2", "open", 20.0, tao_lai_luc),
        ]
        kwargs = dict(
            lenh_sl=lenh_sl, moc_khop_entry=[T0], trade_id=1,
            sl_price=100.0, nguon="live",
        )
        assert sinh_ban_ghi_doi_sl(**kwargs) == sinh_ban_ghi_doi_sl(**kwargs)
