"""🔴 L-Z58 (TD-0164) — hiệu chỉnh hai chiều của DR-015 §4.

Spec L-Z58 nguyên văn: *"Hiệu chỉnh hai chiều (DR-015 §4) trên bộ giả lập
có chênh lệch NHỎ hơn Δ_R → hệ thống kết luận 'KHÔNG PHÂN XỬ ĐƯỢC' và
chọn Z0 theo §5.1, không chọn DCA; trên bộ có chênh LỚN hơn → kết luận
không đổi giữa hai chiều và biên hiệu chỉnh được ghi kèm kết quả."*

Hai lớp quan trọng nhất ngoài hai vế đó:

  • `TestKhongDocSecion4MaThieuBuoc3` — §4 áp Δ_R **chỉ lên DCA**. Phép
    phạt bất đối xứng ấy chỉ chính đáng nếu sai số thước đặc thù tranche
    2+, và Bước 3 tồn tại để kiểm. Nên kết luận Bước 3 là tham số BẮT
    BUỘC, và cảnh báo của nó phải xuất hiện trong diễn giải.
  • `TestKhongBaoGioDanToiDUNG_DU_AN` — chọn Z0 là kết cục ĐÚNG HƯỚNG
    theo §10.1/§3.4b, KHÔNG phải thất bại. Đây là khoá chống hồi quy về
    lỗi v5 (cùng tinh thần L-Z57).
"""

from __future__ import annotations

import pytest

from tool_d.dr015.buoc4_hieu_chinh_hai_chieu import (
    NGUONG_VUOT,
    Arm,
    PhanXuError,
    hieu_chinh_hai_chieu,
)
from tool_d.measurement.tri_state import Measured

DELTA_R = 0.16  # xấp xỉ số đo thật của TD-0161 (0,1612)


def _chay(z0: float, z3: float, *, delta=DELTA_R, p_nf=0.0, buoc3="tuong_duong", **kw):
    arms = {
        "Z0": Arm("Z0", la_dca=False, expectancy_r=z0),
        "Z3": Arm("Z3", la_dca=True, expectancy_r=z3, **kw),
    }
    return hieu_chinh_hai_chieu(
        arms=arms,
        delta_r=Measured.ok(delta),
        p_nf_cao=Measured.ok(p_nf),
        ket_luan_buoc3=buoc3,
    )


class TestHaiVeCuaLZ58:
    def test_chenh_NHO_hon_delta_R_thi_KHONG_PHAN_XU_DUOC_va_chon_Z0(self) -> None:
        """Vế 1 của L-Z58. Z0=1,0 · Z3=1,25 → lợi thế thô +25% (vượt 20%),
        nhưng Δ_R=0,16 lớn hơn khoảng cách 0,25−0,20=0,05 nên chiều bất
        lợi rớt xuống dưới ngưỡng ⇒ người thắng đổi."""
        kq = _chay(1.0, 1.25)
        assert not kq.phan_xu_duoc
        assert kq.arm_chon == "Z0"
        assert "KHÔNG PHÂN XỬ ĐƯỢC" in kq.dien_giai
        assert kq.chieu_co_loi.vuot_nguong and not kq.chieu_bat_loi.vuot_nguong

    def test_chenh_LON_hon_delta_R_thi_ket_luan_KHONG_DOI_giua_hai_chieu(self) -> None:
        """Vế 2 của L-Z58. Z3 vượt xa tới mức −Δ_R vẫn còn trên ngưỡng."""
        kq = _chay(1.0, 1.60)
        assert kq.phan_xu_duoc and kq.arm_chon == "Z3"
        assert kq.chieu_bat_loi.vuot_nguong and kq.chieu_co_loi.vuot_nguong
        assert "VỮNG" in kq.dien_giai

    def test_bien_hieu_chinh_duoc_GHI_KEM_ket_qua(self) -> None:
        """Vế 2 đòi 'biên hiệu chỉnh được ghi kèm kết quả' — không chỉ
        nằm trong đầu người chạy."""
        kq = _chay(1.0, 1.60)
        assert kq.bien_hieu_chinh_delta_r == pytest.approx(DELTA_R)
        assert f"{DELTA_R:.4f}" in kq.dien_giai

    def test_DCA_yeu_han_thi_van_VUNG_va_chon_Z0(self) -> None:
        """Cùng nhánh thắng ở cả hai chiều — chỉ là nhánh Z0."""
        kq = _chay(1.0, 0.5)
        assert kq.phan_xu_duoc and kq.arm_chon == "Z0"
        assert "VỮNG" in kq.dien_giai and "SINGLE-ENTRY" in kq.dien_giai


class TestMoKhoa52:
    def test_mo_khoa_khi_doi_nguoi_thang_VA_loi_the_tho_du_20pct(self) -> None:
        kq = _chay(1.0, 1.25)  # thô +25%, đổi người thắng
        assert kq.mo_khoa_5_2 and "MỞ KHOÁ" in kq.dien_giai

    def test_KHONG_mo_khoa_khi_loi_the_tho_duoi_20pct(self) -> None:
        """§5.2 đòi CẢ HAI điều kiện. 'Lớn' không được để mơ hồ — mơ hồ
        chính là tội §4 vừa cấm."""
        kq = _chay(1.0, 1.10)  # thô +10%, vẫn đổi người thắng
        assert not kq.phan_xu_duoc
        assert not kq.mo_khoa_5_2 and "KHÔNG mở khoá" in kq.dien_giai

    def test_khong_mo_khoa_khi_da_phan_xu_duoc(self) -> None:
        kq = _chay(1.0, 1.60)
        assert not kq.mo_khoa_5_2


class TestKhongDocSecion4MaThieuBuoc3:
    """🔴 §4 phạt bất đối xứng — chỉ chính đáng nếu Bước 3 xác nhận."""

    def test_ket_luan_buoc3_la_bat_buoc(self) -> None:
        import inspect

        sig = inspect.signature(hieu_chinh_hai_chieu)
        assert sig.parameters["ket_luan_buoc3"].default is inspect.Parameter.empty

    def test_buoc3_khong_hop_le_thi_raise(self) -> None:
        with pytest.raises(PhanXuError, match="ket_luan_buoc3"):
            _chay(1.0, 1.6, buoc3="khong_biet")

    def test_TUONG_DUONG_thi_dien_giai_PHAI_canh_bao(self) -> None:
        """Số đo thật (TD-0163): Δ_R(Z0)/Δ_R(DCA) = 1,04 ⇒ tương đương.
        Phần lớn Δ_R là sai số CHUNG và tự triệt tiêu — đọc §4 mà thiếu
        câu này là để một phép phạt chạy sau khi đã mất phần lớn căn cứ."""
        kq = _chay(1.0, 1.60, buoc3="tuong_duong")
        assert "TƯƠNG ĐƯƠNG" in kq.dien_giai and "triệt tiêu" in kq.dien_giai

    def test_CHI_Z0_LECH_thi_ket_qua_bi_danh_dau_KHONG_DUNG_DUOC(self) -> None:
        kq = _chay(1.0, 1.60, buoc3="chi_z0_lech")
        assert "phạt nhầm" in kq.dien_giai and "KHÔNG dùng được" in kq.dien_giai

    def test_CHI_DCA_LECH_thi_khong_them_canh_bao(self) -> None:
        """Đối chứng: nếu mọi kết luận Bước 3 đều sinh cảnh báo thì cảnh
        báo mất nghĩa."""
        kq = _chay(1.0, 1.60, buoc3="chi_dca_lech")
        assert "phạt nhầm" not in kq.dien_giai and "triệt tiêu" not in kq.dien_giai


class TestFailClosed:
    @pytest.mark.parametrize("thieu", ["delta", "pnf"])
    def test_chua_do_duoc_thi_RAISE_khong_mac_dinh_0(self, thieu: str) -> None:
        """Mặc định 0 cho một đại lượng chưa đo là bịa ra 'không có sai
        số' — đúng thứ N6 cấm."""
        arms = {"Z0": Arm("Z0", False, 1.0), "Z3": Arm("Z3", True, 1.6)}
        kw = dict(
            arms=arms,
            delta_r=Measured.ok(DELTA_R),
            p_nf_cao=Measured.ok(0.0),
            ket_luan_buoc3="tuong_duong",
        )
        kw["delta_r" if thieu == "delta" else "p_nf_cao"] = Measured.unreadable("chưa đo")
        with pytest.raises(PhanXuError, match="KHÔNG mặc định 0"):
            hieu_chinh_hai_chieu(**kw)

    def test_thieu_arm_Z0_thi_raise(self) -> None:
        with pytest.raises(PhanXuError, match="Z0"):
            hieu_chinh_hai_chieu(
                arms={"Z3": Arm("Z3", True, 1.6)},
                delta_r=Measured.ok(DELTA_R),
                p_nf_cao=Measured.ok(0.0),
                ket_luan_buoc3="tuong_duong",
            )

    def test_thieu_ca_Z3_va_Z3b_thi_raise(self) -> None:
        """§10.2 so Z0 với tốt nhất của ĐÚNG {Z3, Z3b}, không phải với
        arm DCA bất kỳ."""
        with pytest.raises(PhanXuError, match="Z3"):
            hieu_chinh_hai_chieu(
                arms={"Z0": Arm("Z0", False, 1.0), "Z1": Arm("Z1", True, 5.0)},
                delta_r=Measured.ok(DELTA_R),
                p_nf_cao=Measured.ok(0.0),
                ket_luan_buoc3="tuong_duong",
            )

    @pytest.mark.parametrize("z0", [0.0, -0.5])
    def test_Z0_khong_duong_thi_RAISE_khong_tra_ti_le_vo_nghia(self, z0: float) -> None:
        """'Vượt Z0 ≥ 20%' là so sánh TƯƠNG ĐỐI; mẫu số không dương làm
        tỉ lệ vô nghĩa và đổi dấu tuỳ ý. Phải đưa lên người quyết."""
        with pytest.raises(PhanXuError, match="Z0"):
            _chay(z0, 1.6)

    def test_p_nf_duong_ma_thieu_expectancy_khong_tranche_thi_RAISE(self) -> None:
        """§3 đòi kịch bản bất lợi coi tranche không tồn tại. Bỏ qua nó vì
        thiếu dữ liệu sẽ làm kết quả LẠC QUAN hơn thực tế."""
        with pytest.raises(PhanXuError, match="expectancy_r_khong_tranche"):
            _chay(1.0, 1.6, p_nf=0.10)

    def test_p_nf_duong_co_du_du_lieu_thi_chay_va_LAM_XAU_di_cho_DCA(self) -> None:
        khong_pnf = _chay(1.0, 1.60, p_nf=0.0)
        co_pnf = _chay(1.0, 1.60, p_nf=0.30, expectancy_r_khong_tranche=0.8)
        assert co_pnf.loi_the_tho < khong_pnf.loi_the_tho


class TestKhongBaoGioDanToiDUNG_DU_AN:
    """🔴 Chọn Z0 là kết cục ĐÚNG HƯỚNG (§10.1, §3.4b) — không phải thất
    bại. Khoá chống hồi quy về lỗi v5, cùng tinh thần L-Z57."""

    @pytest.mark.parametrize("z3", [0.1, 0.5, 1.0, 1.10, 1.25, 1.60, 3.0])
    def test_moi_ket_cuc_deu_noi_du_an_TIEP_TUC(self, z3: float) -> None:
        kq = _chay(1.0, z3)
        if kq.arm_chon == "Z0":
            assert "TIẾP TỤC" in kq.dien_giai
        assert "DỪNG DỰ ÁN" not in kq.dien_giai

    def test_nguong_dung_bang_20_pct_theo_spec(self) -> None:
        assert NGUONG_VUOT == 0.20
