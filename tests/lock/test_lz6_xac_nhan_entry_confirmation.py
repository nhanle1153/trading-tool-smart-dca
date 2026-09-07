"""L-Z6 — §3.3b: xác nhận entry tranche 1 bằng price-action, tối đa 3
nến chờ, KHÔNG mở rộng cửa sổ tìm kiếm (chống overfitting ngược).

Phạm vi CHƯA phủ: "mọi tranche 1 đã khớp đều có entry_confirmation
không rỗng" cần bản ghi tranche fill thật (§3.5) — chưa có code đặt
lệnh ở D1/D2. Test ở đây khoá đúng hành vi của `tim_xac_nhan_entry()`;
sẽ nối vào bản ghi plan thật khi TD-0114 dựng chiến lược.
"""

from __future__ import annotations

from tool_d.entry_confirmation import la_nen_rejection, phan_ky_momentum, tim_xac_nhan_entry


class TestLaNenRejectionDay:
    def test_bong_duoi_du_50pt_va_dong_cua_nua_tren_la_rejection(self) -> None:
        # range=10 (100-90), bong_duoi=min(96,99)-90=6 (>=5), dong=99 nam nua tren (>=95)
        assert la_nen_rejection(96, 100, 90, 99, loai="day") is True

    def test_bong_duoi_khong_du_50pt_thi_khong_phai(self) -> None:
        # bong_duoi = min(94,95)-90=4 (<5)
        assert la_nen_rejection(94, 100, 90, 95, loai="day") is False

    def test_dong_cua_nua_duoi_thi_khong_phai_du_bong_du(self) -> None:
        # bong_duoi=8 (du) nhung dong=93 nam nua duoi (<95)
        assert la_nen_rejection(98, 100, 90, 93, loai="day") is False


class TestLaNenRejectionDinh:
    def test_bong_tren_du_va_dong_cua_nua_duoi_la_rejection(self) -> None:
        assert la_nen_rejection(94, 100, 90, 91, loai="dinh") is True


class TestPhanKyMomentum:
    def test_rsi_day_cao_hon_gia_day_thap_hon_la_phan_ky_day(self) -> None:
        assert phan_ky_momentum(rsi_hien_tai=35, gia_hien_tai=98, rsi_truoc=28, gia_truoc=100, loai="day") is True

    def test_rsi_khong_cao_hon_thi_khong_phan_ky(self) -> None:
        assert phan_ky_momentum(rsi_hien_tai=25, gia_hien_tai=98, rsi_truoc=28, gia_truoc=100, loai="day") is False

    def test_gia_khong_thap_hon_bang_thi_khong_phan_ky(self) -> None:
        assert phan_ky_momentum(rsi_hien_tai=35, gia_hien_tai=102, rsi_truoc=28, gia_truoc=100, loai="day") is False


class TestTimXacNhanEntry:
    def test_tim_thay_rejection_ngay_nen_dau(self) -> None:
        mo = [96, 0, 0]
        cao = [100, 0, 0]
        thap = [90, 0, 0]
        dong = [99, 0, 0]
        rsi = [50, 0, 0]
        assert tim_xac_nhan_entry(mo, cao, thap, dong, rsi, i_cham=0, loai="day") == 0

    def test_tim_thay_o_nen_thu_hai_qua_phan_ky(self) -> None:
        # nen 0: khong rejection, khong du du lieu lan cham truoc -> bo qua
        # nen 1: phan ky momentum dung
        mo = [95, 95]
        cao = [100, 100]
        thap = [90, 90]
        dong = [92, 92]  # dong cua nua duoi -> khong phai rejection o ca hai nen
        rsi = [20, 35]
        lan_cham_truoc = (94.0, 28.0)  # (gia, rsi) lan cham truoc: gia=94, rsi=28
        assert (
            tim_xac_nhan_entry(mo, cao, thap, dong, rsi, i_cham=0, loai="day", lan_cham_truoc=lan_cham_truoc)
            == 1
        )

    def test_het_3_nen_khong_xac_nhan_tra_ve_none(self) -> None:
        mo = [95, 95, 95]
        cao = [100, 100, 100]
        thap = [90, 90, 90]
        dong = [92, 92, 92]  # khong rejection nen nao
        rsi = [50, 50, 50]  # khong phan ky (khong co lan_cham_truoc)
        assert tim_xac_nhan_entry(mo, cao, thap, dong, rsi, i_cham=0, loai="day") is None

    def test_khong_mo_rong_cua_so_qua_3_nen(self) -> None:
        # xac nhan chi xuat hien o nen thu 4 (index 3) - PHAI bo lo, khong tim tiep
        mo = [95, 95, 95, 96]
        cao = [100, 100, 100, 100]
        thap = [90, 90, 90, 90]
        dong = [92, 92, 92, 99]  # nen index3 la rejection ro rang
        rsi = [50, 50, 50, 50]
        assert tim_xac_nhan_entry(mo, cao, thap, dong, rsi, i_cham=0, loai="day", so_nen_cho_toi_da=3) is None

    def test_khong_co_lan_cham_truoc_thi_chi_xet_rejection(self) -> None:
        mo = [95, 95]
        cao = [100, 100]
        thap = [90, 90]
        dong = [92, 92]
        rsi = [20, 90]  # neu co lan_cham_truoc se phan ky, nhung khong co -> None
        assert tim_xac_nhan_entry(mo, cao, thap, dong, rsi, i_cham=0, loai="day", lan_cham_truoc=None) is None
