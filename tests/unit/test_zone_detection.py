"""TD-0100 — src/tool_d/zone_detection.py: swing detection thuần (§1.1)."""

from __future__ import annotations

from tool_d.zone_detection import K_XAC_NHAN, la_diem_swing


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
