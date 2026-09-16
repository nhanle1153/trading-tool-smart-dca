"""TD-0254 — tầng chọn giá trị calibration (`DR-D5-01` §5).

Thứ đắt nhất bộ test này giữ: **nhóm LỌC LỆNH không được đo bằng phép so cặp**
(ca `TestVinhSaoKhongSoCap`) — làm thế thì `d ≡ 0` trên tập giao và mọi bộ lọc
đều *"không khác"*, đúng hình `MT-21`. Còn lại: ba kết cục mỗi phép, đi từng
bước từ mốc, `v_min` trả HÀNH ĐỘNG chứ không trả `0.0`, xác nhận ghép, fail-closed.
"""

from __future__ import annotations

import math

import pytest

from tool_d.calibration.chon_gia_tri import (
    ChonGiaTriError,
    HanhDong,
    MotPhia,
    PhanXet,
    SoSanhLoc,
    chon_ket_cuc,
    chon_loc_lenh,
    so_ket_cuc,
    so_loc_lenh,
    xac_nhan_ghep,
    xet_mot_phia,
)
from tool_d.gates.dsr import dsr_hurdle

H = dsr_hurdle(114)  # 3,0777


def _lenh(r: list[float], *, bat_dau: int = 0) -> dict[tuple[str, int], float]:
    return {("X/USDT", bat_dau + i): v for i, v in enumerate(r)}


def _xen_ke(n: int, m: float, bien: float) -> list[float]:
    """n lệnh trung bình đúng m, độ lệch ±bien xen kẽ (n chẵn)."""
    return [m + (bien if i % 2 == 0 else -bien) for i in range(n)]


class TestMotPhia:
    def test_loi_ro_khi_can_duoi_duong(self) -> None:
        kq = xet_mot_phia(_xen_ke(400, 0.5, 1.0))
        assert kq.ket_luan is MotPhia.LOI_RO
        assert kq.thue == pytest.approx(H * math.sqrt(400 / 399) / math.sqrt(400))

    def test_lo_ro_khi_can_tren_am(self) -> None:
        assert xet_mot_phia(_xen_ke(400, -0.5, 1.0)).ket_luan is MotPhia.LO_RO

    def test_khong_phan_biet_khi_nhieu_lon_hon_hieu_ung(self) -> None:
        assert xet_mot_phia(_xen_ke(20, 0.2, 1.0)).ket_luan is MotPhia.KHONG_PHAN_BIET

    def test_duoi_hai_lenh_la_PENDING_khong_phai_0(self) -> None:
        """N6: không có std thì không kết luận — không trả 'không phân biệt'
        trông như đã đo."""
        for r in ([], [3.0]):
            kq = xet_mot_phia(r)
            assert kq.ket_luan is MotPhia.PENDING and kq.mean_r is None

    def test_nan_raise(self) -> None:
        with pytest.raises(ChonGiaTriError):
            xet_mot_phia([1.0, float("nan")])


class TestVinhSaoKhongSoCap:
    def test_bo_loc_chi_bot_lenh_thi_tap_giao_d_bang_0(self) -> None:
        """🔴 Ca ghim LÝ DO TỒN TẠI của `so_loc_lenh`. Bộ lọc chặt chỉ bỏ 200
        lệnh lỗ; lệnh chung giữ nguyên R. So cặp trên giao cho hiệu ĐÚNG 0 —
        không phân biệt được gì. Phép phần-thêm thấy ngay phần bị bỏ lỗ rõ."""
        chung = _lenh(_xen_ke(400, 0.3, 1.0))
        them = _lenh(_xen_ke(200, -0.6, 0.5), bat_dau=10_000)
        r_long = {**chung, **them}
        r_chat = dict(chung)

        so_cap = so_ket_cuc(r_moc=r_long, r_thu=r_chat)
        assert so_cap.mean_hieu == 0.0

        kq = so_loc_lenh(r_long=r_long, r_chat=r_chat)
        assert kq.ket_qua is SoSanhLoc.CHAT_TOT_HON
        assert kq.phan_them.n == 200 and kq.n_giao == 400


class TestSoLocLenh:
    def test_phan_them_loi_ro_thi_long_tot_hon(self) -> None:
        chung = _lenh([0.1] * 10)
        r_long = {**chung, **_lenh(_xen_ke(300, 0.8, 1.0), bat_dau=100)}
        assert so_loc_lenh(r_long=r_long, r_chat=chung).ket_qua is SoSanhLoc.LONG_TOT_HON

    def test_khong_long_nhau_khong_ap_duoc(self) -> None:
        r_long = _lenh([1.0, 1.0, 1.0])
        r_chat = {**_lenh([1.0, 1.0]), ("Y/USDT", 7): -1.0}
        kq = so_loc_lenh(r_long=r_long, r_chat=r_chat)
        assert kq.ket_qua is SoSanhLoc.KHONG_LONG_NHAU and kq.n_chi_o_chat == 1

    def test_phan_them_duoi_hai_lenh_la_PENDING(self) -> None:
        chung = _lenh([0.5] * 50)
        r_long = {**chung, ("Z/USDT", 1): 5.0}
        assert so_loc_lenh(r_long=r_long, r_chat=chung).ket_qua is SoSanhLoc.PENDING


class TestSoKetCuc:
    def test_thang_ro_khi_hieu_cap_duong_sau_tru_thue(self) -> None:
        moc = _lenh(_xen_ke(300, 0.2, 1.0))
        thu = {k: v + 0.3 for k, v in moc.items()}
        kq = so_ket_cuc(r_moc=moc, r_thu=thu)
        assert kq.ket_qua is PhanXet.THANG_RO
        assert kq.can_duoi_hieu == pytest.approx(0.3)  # std(d) = 0 ⇒ thuế 0

    def test_khong_thang_khi_nhieu_nuot_hieu(self) -> None:
        moc = _lenh([0.0] * 20)
        thu = _lenh(_xen_ke(20, 0.1, 1.0))
        assert so_ket_cuc(r_moc=moc, r_thu=thu).ket_qua is PhanXet.KHONG_THANG

    def test_giao_duoi_hai_la_PENDING(self) -> None:
        assert so_ket_cuc(r_moc=_lenh([1.0]), r_thu=_lenh([2.0])).ket_qua is PhanXet.PENDING

    def test_thang_o_giao_nhung_lenh_THEM_lo_ro_thi_KHONG_THANG(self) -> None:
        """§5.1: hai phép nói ngược nhau ⇒ không thắng, và cờ mâu thuẫn bật."""
        moc = _lenh([0.0] * 50)
        thu = {**{k: 0.5 for k in moc}, **_lenh(_xen_ke(300, -1.0, 0.5), bat_dau=9_000)}
        kq = so_ket_cuc(r_moc=moc, r_thu=thu)
        assert kq.ket_qua is PhanXet.KHONG_THANG and kq.mau_thuan

    def test_lenh_BI_BO_loi_ro_cung_la_thua_o_phan_chenh(self) -> None:
        """DIỄN GIẢI hai phía (docstring `so_ket_cuc`): ứng viên bỏ đi một nhóm
        lệnh lời rõ thì không được tính là thắng chỉ nhờ phần giao."""
        moc = {**_lenh([0.0] * 50), **_lenh(_xen_ke(300, 1.0, 0.5), bat_dau=9_000)}
        thu = {k: 0.5 for k in _lenh([0.0] * 50)}
        kq = so_ket_cuc(r_moc=moc, r_thu=thu)
        assert kq.ket_qua is PhanXet.KHONG_THANG and kq.mau_thuan


def _kq_ket_cuc(px: PhanXet, can_duoi: float | None) -> object:
    moc = _lenh([0.0] * 10)
    kq = so_ket_cuc(r_moc=moc, r_thu=moc)
    return type(kq)(
        ket_qua=px, n_giao=10, mean_hieu=None, thue=None, can_duoi_hieu=can_duoi,
        phan_them=kq.phan_them, phan_bo=kq.phan_bo, mau_thuan=False,
    )


class TestChonKetCuc:
    def test_khong_ai_thang_thi_giu_moc(self) -> None:
        qd = chon_ket_cuc(moc=0.4, ket_qua={0.3: _kq_ket_cuc(PhanXet.KHONG_THANG, -0.1),
                                            0.5: _kq_ket_cuc(PhanXet.KHONG_THANG, -0.2)})
        assert qd.hanh_dong is HanhDong.GIU_MOC and qd.gia_tri == 0.4

    def test_ca_hai_thang_lay_can_duoi_lon_hon(self) -> None:
        qd = chon_ket_cuc(moc=20, ket_qua={10: _kq_ket_cuc(PhanXet.THANG_RO, 0.05),
                                           30: _kq_ket_cuc(PhanXet.THANG_RO, 0.09)})
        assert qd.hanh_dong is HanhDong.DOI and qd.gia_tri == 30

    def test_moi_phep_pending_thi_PENDING_giu_gia_tri_moc(self) -> None:
        qd = chon_ket_cuc(moc=24, ket_qua={20: _kq_ket_cuc(PhanXet.PENDING, None),
                                           32: _kq_ket_cuc(PhanXet.PENDING, None)})
        assert qd.hanh_dong is HanhDong.PENDING and qd.gia_tri == 24

    def test_rong_raise(self) -> None:
        with pytest.raises(ChonGiaTriError):
            chon_ket_cuc(moc=1, ket_qua={})


def _kq_loc(ss: SoSanhLoc) -> object:
    kq = so_loc_lenh(r_long=_lenh([1.0]), r_chat=_lenh([1.0]))
    return type(kq)(ket_qua=ss, phan_them=kq.phan_them, n_giao=0, n_chi_o_chat=0)


class TestChonLocLenh:
    TT = [0.4, 0.5, 0.6]

    def test_phia_long_tot_hon_thi_doi_sang_long(self) -> None:
        qd = chon_loc_lenh(thu_tu_long_den_chat=self.TT, moc=0.5, so_sanh={
            (0.4, 0.5): _kq_loc(SoSanhLoc.LONG_TOT_HON),
            (0.5, 0.6): _kq_loc(SoSanhLoc.KHONG_PHAN_BIET)})
        assert qd.hanh_dong is HanhDong.DOI and qd.gia_tri == 0.4

    def test_phia_chat_tot_hon_thi_doi_sang_chat(self) -> None:
        qd = chon_loc_lenh(thu_tu_long_den_chat=self.TT, moc=0.5, so_sanh={
            (0.4, 0.5): _kq_loc(SoSanhLoc.CHAT_TOT_HON),
            (0.5, 0.6): _kq_loc(SoSanhLoc.CHAT_TOT_HON)})
        assert qd.hanh_dong is HanhDong.DOI and qd.gia_tri == 0.6

    def test_hai_phia_cung_noi_tot_hon_thi_GIU_MOC(self) -> None:
        qd = chon_loc_lenh(thu_tu_long_den_chat=self.TT, moc=0.5, so_sanh={
            (0.4, 0.5): _kq_loc(SoSanhLoc.LONG_TOT_HON),
            (0.5, 0.6): _kq_loc(SoSanhLoc.CHAT_TOT_HON)})
        assert qd.hanh_dong is HanhDong.GIU_MOC and "ĐƠN ĐIỆU" in qd.ly_do

    def test_khong_long_nhau_thi_giu_moc(self) -> None:
        qd = chon_loc_lenh(thu_tu_long_den_chat=self.TT, moc=0.5, so_sanh={
            (0.4, 0.5): _kq_loc(SoSanhLoc.KHONG_LONG_NHAU),
            (0.5, 0.6): _kq_loc(SoSanhLoc.KHONG_PHAN_BIET)})
        assert qd.hanh_dong is HanhDong.GIU_MOC

    def test_moi_buoc_dau_pending_thi_PENDING(self) -> None:
        qd = chon_loc_lenh(thu_tu_long_den_chat=self.TT, moc=0.5, so_sanh={
            (0.4, 0.5): _kq_loc(SoSanhLoc.PENDING), (0.5, 0.6): _kq_loc(SoSanhLoc.PENDING)})
        assert qd.hanh_dong is HanhDong.PENDING and qd.gia_tri == 0.5

    def test_wick_moc_long_nhat_buoc_hai_chi_xet_khi_da_sang_buoc_mot(self) -> None:
        """`wick_close_upper_frac`: mốc 0,5 là lỏng nhất. Bước (0,6→0,67) KHÔNG
        được xét khi bước (0,5→0,6) chưa sang — thiếu cặp đó cũng không raise."""
        tt = [0.5, 0.6, 0.67]
        qd = chon_loc_lenh(thu_tu_long_den_chat=tt, moc=0.5, so_sanh={
            (0.5, 0.6): _kq_loc(SoSanhLoc.KHONG_PHAN_BIET)})
        assert qd.hanh_dong is HanhDong.GIU_MOC
        qd2 = chon_loc_lenh(thu_tu_long_den_chat=tt, moc=0.5, so_sanh={
            (0.5, 0.6): _kq_loc(SoSanhLoc.CHAT_TOT_HON), (0.6, 0.67): _kq_loc(SoSanhLoc.CHAT_TOT_HON)})
        assert qd2.gia_tri == 0.67

    def test_v_min_0_thang_tra_BO_DIEU_KIEN_C_khong_tra_so(self) -> None:
        """`DR-D5-01` §3.1: không được lặng lẽ ghi `0.0` vào cấu hình."""
        qd = chon_loc_lenh(thu_tu_long_den_chat=[0.0, 1.0, 1.5], moc=1.0, gia_tri_tat=0.0, so_sanh={
            (0.0, 1.0): _kq_loc(SoSanhLoc.LONG_TOT_HON), (1.0, 1.5): _kq_loc(SoSanhLoc.KHONG_PHAN_BIET)})
        assert qd.hanh_dong is HanhDong.BO_DIEU_KIEN_C and qd.gia_tri is None

    def test_thieu_cap_can_xet_thi_raise(self) -> None:
        with pytest.raises(ChonGiaTriError):
            chon_loc_lenh(thu_tu_long_den_chat=self.TT, moc=0.5, so_sanh={
                (0.4, 0.5): _kq_loc(SoSanhLoc.KHONG_PHAN_BIET)})

    def test_moc_ngoai_thu_tu_raise(self) -> None:
        with pytest.raises(ChonGiaTriError):
            chon_loc_lenh(thu_tu_long_den_chat=self.TT, moc=0.55, so_sanh={})


class TestXacNhanGhep:
    def test_ghep_tang_ro_tong_R_thi_xac_nhan(self) -> None:
        moc = _lenh(_xen_ke(300, 0.1, 1.0))
        ghep = {k: v + 0.2 for k, v in moc.items()}
        kq = xac_nhan_ghep(r_moc=moc, r_ghep=ghep)
        assert kq.xac_nhan is True and kq.delta == pytest.approx(60.0)

    def test_tach_ba_phan_dung_cong_thuc(self) -> None:
        moc = {**_lenh([0.0, 1.0, 2.0]), **_lenh([-1.0, 1.0], bat_dau=50)}
        ghep = {**_lenh([1.0, 1.0, 1.0]), **_lenh([3.0, 5.0], bat_dau=80)}
        kq = xac_nhan_ghep(r_moc=moc, r_ghep=ghep)
        d = [1.0, 0.0, -1.0]
        var_d = sum(x * x for x in d) / 2
        se = math.sqrt(3 * var_d + 2 * 2.0 + 2 * 2.0)
        assert kq.delta == pytest.approx(0.0 + 8.0 - 0.0)
        assert kq.se == pytest.approx(se)
        assert kq.can_duoi == pytest.approx(8.0 - H * se)

    def test_ghep_khong_hon_moc_ro_thi_khong_xac_nhan(self) -> None:
        moc = _lenh(_xen_ke(40, 0.1, 1.0))
        ghep = _lenh(_xen_ke(40, 0.12, 1.0)[::-1])  # ngược pha ⇒ hiệu cặp dao động ±2, có nhiễu thật
        assert xac_nhan_ghep(r_moc=moc, r_ghep=ghep).xac_nhan is False

    def test_moi_phan_duoi_hai_lenh_thi_PENDING_va_ghi_han_che(self) -> None:
        kq = xac_nhan_ghep(r_moc=_lenh([1.0]), r_ghep=_lenh([2.0]))
        assert kq.xac_nhan is None and kq.han_che
