"""TD-0100/TD-0101 — src/tool_d/zone_detection.py: swing detection (§1.1) +
độ tin cậy tăng dần / điều kiện huỷ (§7.4)."""

from __future__ import annotations

import pytest

from tool_d.zone_detection import K_XAC_NHAN, confirm_ratio, la_diem_swing, zone_da_bi_huy


class TestLaDiemSwingDay:
    def test_diem_thap_nhat_trong_cua_so_la_swing_khi_du_du_lieu(self) -> None:
        # i=3: thấp nhất trong [0,6]. Mảng dài tới index 6 = i+k, vừa đủ.
        gia = [10, 9, 8, 5, 8, 9, 10]
        assert la_diem_swing(gia, 3, loai="day") is True

    def test_chua_xac_nhan_khi_thieu_nen_sau(self) -> None:
        gia = [10, 9, 8, 5, 8, 9, 10]
        # Cùng đúng dữ liệu đó nhưng bị cắt trước khi có đủ 3 nến sau i=3.
        for do_dai in range(0, 6):  # tới index 5, còn thiếu index 6
            assert la_diem_swing(gia[:do_dai], 3, loai="day") is False

    def test_diem_khong_phai_cuc_tieu_thi_khong_phai_swing(self) -> None:
        gia = [10, 9, 8, 5, 4, 9, 10]  # i=3 (giá 5) không phải min — index 4 (giá 4) mới là
        assert la_diem_swing(gia, 3, loai="day") is False

    def test_thieu_nen_truoc_thi_khong_phai_swing(self) -> None:
        gia = [10, 9, 8, 5, 8, 9, 10]
        assert la_diem_swing(gia, 2, loai="day") is False  # i=2 cần index -1, không có

    def test_du_lieu_tuong_lai_ngoai_cua_so_khong_lam_doi_ket_qua(self) -> None:
        # Chốt tính chất "hàm THUẦN, không đọc dữ liệu sau t": cắt đúng tại
        # i+k rồi nối thêm bất kỳ giá trị tương lai nào (kể cả cực đoan) —
        # kết quả PHẢI giữ nguyên vì hàm không có cách nào nhìn thấy chúng.
        goc = [10, 9, 8, 5, 8, 9, 10]
        ket_qua_goc = la_diem_swing(goc, 3, loai="day")
        voi_tuong_lai = goc + [0.001, 999, -50]
        assert la_diem_swing(goc, 3, loai="day") == ket_qua_goc
        # gọi lại với mảng dài hơn nhưng CÙNG index i vẫn phải xét đúng cửa
        # sổ [i-k, i+k] cố định — không bị ảnh hưởng bởi phần thừa phía sau.
        assert la_diem_swing(voi_tuong_lai, 3, loai="day") == ket_qua_goc


class TestLaDiemSwingDinh:
    def test_diem_cao_nhat_trong_cua_so_la_swing(self) -> None:
        gia = [1, 2, 3, 6, 3, 2, 1]
        assert la_diem_swing(gia, 3, loai="dinh") is True

    def test_chua_xac_nhan_khi_thieu_nen_sau(self) -> None:
        gia = [1, 2, 3, 6, 3, 2, 1]
        assert la_diem_swing(gia[:6], 3, loai="dinh") is False


def test_k_xac_nhan_dung_bang_3_theo_spec() -> None:
    assert K_XAC_NHAN == 3


class TestConfirmRatio:
    def test_bon_moc_theo_spec_7_4(self) -> None:
        i = 10
        assert confirm_ratio(i, i) == 0
        assert confirm_ratio(i, i + 1) == pytest.approx(1 / 3)
        assert confirm_ratio(i, i + 2) == pytest.approx(2 / 3)
        assert confirm_ratio(i, i + 3) == 1.0

    def test_qua_moc_i_cong_k_thi_giu_nguyen_1_0(self) -> None:
        i = 10
        assert confirm_ratio(i, i + 4) == 1.0
        assert confirm_ratio(i, i + 100) == 1.0

    def test_t_truoc_i_thi_ve_0_khong_am(self) -> None:
        # Không nên xảy ra trong luồng thật (xác nhận chỉ chạy sau khi
        # swing hình thành tại i) nhưng hàm THUẦN không được trả số âm
        # vô nghĩa nếu lỡ gọi sai thứ tự.
        assert confirm_ratio(10, 9) == 0


class TestZoneDaBiHuy:
    def test_gia_khong_vuot_qua_i_thi_chua_bi_huy(self) -> None:
        gia = [10, 9, 8, 5, 6, 7, 8]  # đáy tại i=3 (giá 5), sau đó không xuống dưới 5
        assert zone_da_bi_huy(gia, 3, 6, loai="day") is False

    def test_gia_tao_day_moi_thap_hon_thi_bi_huy_vinh_vien(self) -> None:
        gia = [10, 9, 8, 5, 4, 7, 8]  # index 4 = 4, thấp hơn đáy tại i=3
        assert zone_da_bi_huy(gia, 3, 4, loai="day") is True
        # đã huỷ tại t=4 thì tại các t sau đó vẫn phải huỷ — "vĩnh viễn"
        assert zone_da_bi_huy(gia, 3, 6, loai="day") is True

    def test_dinh_bi_huy_khi_gia_vuot_cao_hon(self) -> None:
        gia = [1, 2, 3, 6, 7, 2, 1]  # đỉnh tại i=3 (giá 6), index 4 = 7 vượt qua
        assert zone_da_bi_huy(gia, 3, 4, loai="dinh") is True

    def test_chua_co_nen_nao_sau_i_thi_chua_the_huy(self) -> None:
        gia = [10, 9, 8, 5, 8, 9, 10]
        assert zone_da_bi_huy(gia, 3, 3, loai="day") is False

    def test_du_lieu_sau_t_khong_lam_doi_ket_qua(self) -> None:
        # Cùng tinh thần TD-0100: hàm THUẦN, chỉ xét (i, t] — dữ liệu sau
        # t (kể cả cực đoan) không được phép ảnh hưởng câu trả lời tại t.
        goc = [10, 9, 8, 5, 6, 7, 8]
        ket_qua_goc = zone_da_bi_huy(goc, 3, 5, loai="day")
        voi_tuong_lai = goc + [-999]  # nếu đọc lố sẽ đổi kết quả thành True
        assert zone_da_bi_huy(voi_tuong_lai, 3, 5, loai="day") == ket_qua_goc
