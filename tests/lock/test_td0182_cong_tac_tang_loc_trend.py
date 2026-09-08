"""TD-0182 — công tắc tầng lọc trend cho Z0-T0 / Z0-T1 / Z0-T2 (§10.1b).

Thứ bộ test này canh chặt nhất **không phải** "mỗi tầng trả đúng giá
trị" — mà là **ba tầng THẬT SỰ khác nhau**.

Lý do: một công tắc mà mọi nhánh cho cùng kết quả vẫn làm mọi phép kiểm
kiểu "gọi được, không nổ" xanh hết, trong khi arm `Z0-T1` sẽ tiêu một
suất trong 114 để đo lại đúng thứ `Z0-T2` đã đo. Đó là bẫy PASS RỖNG ở
dạng đắt nhất của dự án này: nó không làm hỏng phép đo, nó **đốt ngân
sách phép thử** — và bảng kết quả sẽ trông hoàn toàn bình thường, chỉ
là hai cột giống hệt nhau mà không ai biết vì sao.

`TestBaTangTHUCSUKhacNhau` chặn đúng ca đó bằng chứng kiến cụ thể, chứ
không bằng lời hứa.
"""

from __future__ import annotations

import pytest

from tool_d.arms import (
    TANG_HOP_LE,
    TANG_THEO_ARM,
    ArmKhongHopLeError,
    du_dieu_kien_trend_theo_tang,
    tang_cua_arm,
)

# Hai bộ đầu vào được chọn để TÁCH ĐÔI các tầng, không phải để "trông
# giống dữ liệu thật". Xem `TestBaTangTHUCSUKhacNhau` giải thích từng bộ.
NGUOC_4H = dict(  # 4H đi ngược hướng vào lệnh, 1D thì thuận
    huong_muc_tieu="UP", huong_1d="UP", huong_4h="DOWN", adx_1d=30.0, tuoi_nen_1d=10
)
YEU_1D = dict(  # 4H thuận, nhưng 1D không có trend
    huong_muc_tieu="UP", huong_1d="FLAT", huong_4h="UP", adx_1d=30.0, tuoi_nen_1d=10
)
THUAN_HET = dict(  # mọi điều kiện đều đạt
    huong_muc_tieu="UP", huong_1d="UP", huong_4h="UP", adx_1d=30.0, tuoi_nen_1d=10
)


class TestBaTangTHUCSUKhacNhau:
    """🔴 Phần đáng giá nhất của file. Xem docstring module."""

    def test_KHONG_khac_CHI_4H_tren_mot_dau_vao_cu_the(self) -> None:
        """4H đi ngược hướng vào lệnh: bỏ hết bộ lọc thì vẫn vào, giữ
        4H thì bị chặn. Nếu hai tầng này cho cùng kết quả ở MỌI đầu vào
        thì `Z0-T0` và `Z0-T1` là một arm được đếm hai lần."""
        assert du_dieu_kien_trend_theo_tang(tang="KHONG", **NGUOC_4H) is True
        assert du_dieu_kien_trend_theo_tang(tang="CHI_4H", **NGUOC_4H) is False

    def test_CHI_4H_khac_DAY_DU_tren_mot_dau_vao_cu_the(self) -> None:
        """4H thuận nhưng 1D `FLAT`: bỏ tầng 1D thì vào được, giữ đủ
        bốn điều kiện thì không. Đây CHÍNH LÀ câu hỏi §10.1b gọi là
        'arm quan trọng nhất' — tầng 1D có giá trị RIÊNG ngoài 4H không."""
        assert du_dieu_kien_trend_theo_tang(tang="CHI_4H", **YEU_1D) is True
        assert du_dieu_kien_trend_theo_tang(tang="DAY_DU", **YEU_1D) is False

    def test_KHONG_khac_DAY_DU_tren_mot_dau_vao_cu_the(self) -> None:
        assert du_dieu_kien_trend_theo_tang(tang="KHONG", **YEU_1D) is True
        assert du_dieu_kien_trend_theo_tang(tang="DAY_DU", **YEU_1D) is False

    def test_ba_tang_khong_phai_ba_ten_goi_cua_mot_thu(self) -> None:
        """Gộp lại: tồn tại đầu vào mà bộ ba kết quả PHÂN BIỆT được từng
        cặp. Ca này đỏ nghĩa là ít nhất hai arm đang đo cùng một thứ."""
        ket_qua = {
            t: tuple(
                du_dieu_kien_trend_theo_tang(tang=t, **dv) for dv in (NGUOC_4H, YEU_1D)
            )
            for t in TANG_HOP_LE
        }
        assert len(set(ket_qua.values())) == 3, ket_qua


class TestDayDuKhongChepLaiPhepTinh:
    def test_DAY_DU_goi_thang_ham_cua_trend_context(self) -> None:
        """MT-03: chép bốn điều kiện sang `arms.py` tạo nguồn sự thật
        thứ hai. Ca này ghim việc gọi lại, không chép."""
        import inspect

        import tool_d.arms as mod

        src = inspect.getsource(mod.du_dieu_kien_trend_theo_tang)
        assert "du_dieu_kien_vao_lenh(" in src
        # và KHÔNG tự dựng lại bốn điều kiện
        assert "NGUONG_ADX" not in src
        assert "K_TUOI_TREND_TOI_THIEU" not in src

    def test_DAY_DU_khop_TUNG_DIEM_voi_du_dieu_kien_vao_lenh(self) -> None:
        from tool_d.trend_context import du_dieu_kien_vao_lenh

        for dv in (NGUOC_4H, YEU_1D, THUAN_HET):
            mong_doi = du_dieu_kien_vao_lenh(
                huong_muc_tieu=dv["huong_muc_tieu"],
                huong_1d=dv["huong_1d"],
                huong_4h=dv["huong_4h"],
                adx_1d=dv["adx_1d"],
                tuoi_nen=dv["tuoi_nen_1d"],
            )
            assert du_dieu_kien_trend_theo_tang(tang="DAY_DU", **dv) is mong_doi


class TestZ0VaZ0T2LaMOT:
    """🔴 DR-D4-01 §3: đếm `Z0-T2` thành arm thứ 10 là tiêu thừa một
    suất trên tổng 114."""

    def test_Z0_va_Z0_T2_cung_mot_tang(self) -> None:
        assert tang_cua_arm("Z0") == tang_cua_arm("Z0-T2") == "DAY_DU"

    def test_bang_arm_chi_co_ba_TANG_dù_co_MUOI_TEN(self) -> None:
        """🔴 SỬA từ "bốn tên" — bản đầu chỉ phủ nhóm T0/T1/T2 vì lúc đó
        chưa cần nạp CHIẾN LƯỢC với arm khác. Thiếu sót lộ ra khi
        `ZoneAbsorption` chạy arm mặc định `Z3` và `tang_cua_arm` raise —
        không xoá khẳng định cũ, sửa thành đúng số 10 (9 arm thật của
        `arm_switches.ARM_HOP_LE` + alias `Z0-T2`), vẫn chỉ ba TẦNG."""
        assert len(TANG_THEO_ARM) == 10
        assert set(TANG_THEO_ARM.values()) == set(TANG_HOP_LE)

    def test_TANG_THEO_ARM_phu_dung_CHIN_arm_that(self) -> None:
        """Không để hai bảng trôi lệch: mọi arm `arm_switches.ARM_HOP_LE`
        khai phải tra được tầng trend ở đây, nếu không `ZoneAbsorption`
        nạp arm đó sẽ raise ngay ở `__init__` — đúng ca đã xảy ra."""
        from tool_d.arm_switches import ARM_HOP_LE

        thieu = set(ARM_HOP_LE) - set(TANG_THEO_ARM)
        assert not thieu, f"arm chưa có tầng trend: {thieu}"

    def test_moi_arm_ngoai_T0_T1_deu_DAY_DU(self) -> None:
        """Chỉ trục trend của Z0-T0/Z0-T1 bị đổi; các arm còn lại đo trục
        KHÁC (SL/cỡ lệnh/DG/volume) nên KHÔNG được tắt trend filter theo —
        tắt lây là trộn hai biến vào một arm (bài học MT-15)."""
        from tool_d.arm_switches import ARM_HOP_LE

        cho_day_du = set(ARM_HOP_LE) - {"Z0-T0", "Z0-T1"}
        assert all(TANG_THEO_ARM[a] == "DAY_DU" for a in cho_day_du), {
            a: TANG_THEO_ARM[a] for a in cho_day_du
        }


class TestFailClosed:
    def test_ten_arm_la_khong_mac_dinh_ve_DAY_DU(self) -> None:
        """Một tên gõ sai chạy lặng lẽ như Z0 sẽ sinh ra arm ghi nhãn
        `Z0-T1` nhưng đo `Z0-T2`, và không gì trong kết quả lộ ra."""
        with pytest.raises(ArmKhongHopLeError, match="Z0-T3"):
            tang_cua_arm("Z0-T3")

    def test_tang_la_khong_mac_dinh_ve_DAY_DU(self) -> None:
        with pytest.raises(ArmKhongHopLeError, match="CHI_1D"):
            du_dieu_kien_trend_theo_tang(tang="CHI_1D", **THUAN_HET)

    def test_chuoi_rong_cung_bi_tu_choi(self) -> None:
        with pytest.raises(ArmKhongHopLeError):
            tang_cua_arm("")


class TestCHI_4H_KHONG_con_phu_thuoc_1D:
    """🔴 Nếu `CHI_4H` còn đọc `huong_1d` thì arm `Z0-T1` không đo được
    thứ nó sinh ra để đo — tầng 1D vẫn đang lọc, chỉ là qua cửa khác."""

    def test_doi_huong_1d_KHONG_lam_doi_ket_qua_cua_CHI_4H(self) -> None:
        for h1d in ("UP", "DOWN", "FLAT"):
            dv = dict(THUAN_HET, huong_1d=h1d)
            assert du_dieu_kien_trend_theo_tang(tang="CHI_4H", **dv) is True

    def test_doi_adx_1d_KHONG_lam_doi_ket_qua_cua_CHI_4H(self) -> None:
        """ADX(1D) ≥ 20 là điều kiện của tầng 1D — `Z0-T1` bỏ nó."""
        dv = dict(THUAN_HET, adx_1d=0.0)
        assert du_dieu_kien_trend_theo_tang(tang="CHI_4H", **dv) is True

    def test_doi_tuoi_trend_KHONG_lam_doi_ket_qua_cua_CHI_4H(self) -> None:
        """Tuổi trend ≥5 ngày cũng là tầng 1D. Ghi chú: `trend_age_days`
        trong `tier_frozen` mang `frozen_until: "Z0-T1_result"` — tức
        chính arm này là thứ mở khoá nó."""
        for tuoi in (None, 0, 1):
            dv = dict(THUAN_HET, tuoi_nen_1d=tuoi)
            assert du_dieu_kien_trend_theo_tang(tang="CHI_4H", **dv) is True

    def test_KHONG_thi_moi_dau_vao_deu_vao_duoc(self) -> None:
        for dv in (NGUOC_4H, YEU_1D, THUAN_HET):
            assert du_dieu_kien_trend_theo_tang(tang="KHONG", **dv) is True
