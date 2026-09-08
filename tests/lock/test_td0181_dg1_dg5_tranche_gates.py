"""🔴 TD-0181 — DG1–DG5 (§4), năm cổng KÍCH HOẠT tranche mới.

Ba thứ bộ test này canh chặt nhất:

1. **Không cổng nào có giá trị mặc định lén.** DG4 và DG5 mang ngưỡng;
   cả hai phải là tham số BẮT BUỘC. Một mặc định ở đây là một bậc tự do
   không ai đếm, trong khi `N_ĐĂNG_KÝ = 114` là mẫu số của rào DSR đã
   cam kết.
2. **Không xét được KHÁC với cổng đóng.** Đầu vào hỏng phải `raise`, chứ
   trả `False` là biến một lỗi dữ liệu thành một quyết định giao dịch
   trông hoàn toàn bình thường.
3. **DG1 dùng giá ĐÓNG CỬA, không phải `low`.** Râu nến xuyên xuống rồi
   thu lại chính là hành vi hấp thụ mà chiến lược đi tìm — bắt nó thành
   "zone bị phá" là tự tay tắt cơ chế mình đang đo.
"""

from __future__ import annotations

import inspect

import pytest

from tool_d.dg1_dg5_tranche_gates import (
    TrancheGateError,
    danh_gia_tat_ca,
    dg1_zone_con_nguyen,
    dg2_trend_con_dung,
    dg3_margin_con_nguyen,
    dg4_con_trong_cua_so_cho,
    dg5_zss_khong_suy_yeu,
)


def _bo_day_du(**ghi_de):
    """Bộ đầu vào PASS cả năm cổng; mỗi test chỉ đổi đúng thứ nó xét."""
    day_du = dict(
        close_4h_ke_tu_tranche1=[100.0, 99.0],
        sl=95.0,
        huong="long",
        trend_dir_tai_tranche1="UP",
        trend_dir_hien_tai="UP",
        margin_reserve_con_lai=50.0,
        margin_can_cho_tranche=20.0,
        so_nen_1h_da_troi=3,
        dg4_bars_1h=8,
        zss_tai_tranche1=0.60,
        zss_hien_tai=0.55,
        nguong_giam_toi_da=0.30,
    )
    day_du.update(ghi_de)
    return day_du


class TestDG1ZoneConNguyen:
    def test_chua_nen_nao_dong_duoi_sl_thi_PASS(self) -> None:
        assert dg1_zone_con_nguyen(close_4h_ke_tu_tranche1=[100.0, 96.0], sl=95.0, huong="long")

    def test_mot_nen_dong_duoi_sl_thi_FAIL(self) -> None:
        assert not dg1_zone_con_nguyen(
            close_4h_ke_tu_tranche1=[100.0, 94.9], sl=95.0, huong="long"
        )

    def test_dong_cua_DUNG_BANG_sl_van_PASS(self) -> None:
        """§4 viết "đóng cửa DƯỚI sl". Đúng bằng không phải dưới, và biên
        này quyết định một ca thật: giá dừng chính xác ở mức SL."""
        assert dg1_zone_con_nguyen(close_4h_ke_tu_tranche1=[95.0], sl=95.0, huong="long")

    def test_KHONG_dung_low_cua_nen_chi_dung_close(self) -> None:
        """🔴 Ca quan trọng nhất của DG1. Hàm chỉ nhận `close`, nên nếu ai
        đổi sang truyền `low` vào thì ca này không đỏ — nó canh bằng cách
        khác: chữ ký hàm phải nói rõ nó nhận cái gì."""
        tham_so = inspect.signature(dg1_zone_con_nguyen).parameters
        assert "close_4h_ke_tu_tranche1" in tham_so
        assert not any("low" in t or "high" in t for t in tham_so)

    def test_danh_sach_rong_thi_PASS_khong_raise(self) -> None:
        """Chưa có nến 4H nào đóng kể từ tranche 1 là TRẠNG THÁI THẬT
        (tranche 1 vừa khớp), không phải thiếu dữ liệu."""
        assert dg1_zone_con_nguyen(close_4h_ke_tu_tranche1=[], sl=95.0, huong="long")

    def test_SHORT_dao_dau_hoan_toan(self) -> None:
        assert dg1_zone_con_nguyen(close_4h_ke_tu_tranche1=[100.0, 104.0], sl=105.0, huong="short")
        assert not dg1_zone_con_nguyen(close_4h_ke_tu_tranche1=[105.1], sl=105.0, huong="short")

    def test_huong_la_thi_raise_khong_doan(self) -> None:
        with pytest.raises(TrancheGateError, match="huong"):
            dg1_zone_con_nguyen(close_4h_ke_tu_tranche1=[100.0], sl=95.0, huong="LONG")


class TestDG2TrendConDung:
    def test_cung_huong_thi_PASS(self) -> None:
        assert dg2_trend_con_dung(trend_dir_tai_tranche1="UP", trend_dir_hien_tai="UP")

    def test_dao_hoan_toan_thi_FAIL(self) -> None:
        assert not dg2_trend_con_dung(trend_dir_tai_tranche1="UP", trend_dir_hien_tai="DOWN")

    def test_UP_sang_FLAT_cung_FAIL(self) -> None:
        """🔴 Diễn giải đã chọn, ghi ra để cãi lại được: `FLAT` nghĩa là
        "chưa có bằng chứng trend", và §2.5 đã tự loại `FLAT` ở bước vào
        lệnh — cho phép bơm thêm tiền vào bối cảnh mà chính hệ thống sẽ
        không cho mở lệnh mới là mâu thuẫn với chính nó."""
        assert not dg2_trend_con_dung(trend_dir_tai_tranche1="UP", trend_dir_hien_tai="FLAT")

    def test_FLAT_sang_FLAT_van_PASS(self) -> None:
        """Cổng hỏi "có ĐỔI không", không hỏi "có tốt không"."""
        assert dg2_trend_con_dung(trend_dir_tai_tranche1="FLAT", trend_dir_hien_tai="FLAT")


class TestDG3MarginConNguyen:
    def test_du_margin_thi_PASS(self) -> None:
        assert dg3_margin_con_nguyen(margin_reserve_con_lai=50.0, margin_can_cho_tranche=20.0)

    def test_dung_bang_nhau_van_PASS(self) -> None:
        assert dg3_margin_con_nguyen(margin_reserve_con_lai=20.0, margin_can_cho_tranche=20.0)

    def test_thieu_mot_chut_thi_FAIL(self) -> None:
        assert not dg3_margin_con_nguyen(
            margin_reserve_con_lai=19.99, margin_can_cho_tranche=20.0
        )

    @pytest.mark.parametrize(
        "con_lai,can", [(-1.0, 20.0), (50.0, -1.0)]
    )
    def test_margin_am_thi_RAISE_khong_tra_False(self, con_lai: float, can: float) -> None:
        """Margin âm là kế toán ở tầng trên đã hỏng. Trả `False` sẽ làm nó
        trông y hệt "hết margin" — một lỗi hệ thống đội lốt một trạng thái
        bình thường."""
        with pytest.raises(TrancheGateError, match="âm"):
            dg3_margin_con_nguyen(margin_reserve_con_lai=con_lai, margin_can_cho_tranche=can)


class TestDG4CuaSoCho:
    def test_trong_cua_so_thi_PASS(self) -> None:
        assert dg4_con_trong_cua_so_cho(so_nen_1h_da_troi=3, dg4_bars_1h=8)

    def test_DUNG_BANG_tran_van_PASS_vi_spec_viet_nho_hon_hoac_bang(self) -> None:
        assert dg4_con_trong_cua_so_cho(so_nen_1h_da_troi=8, dg4_bars_1h=8)

    def test_vuot_mot_nen_thi_FAIL(self) -> None:
        assert not dg4_con_trong_cua_so_cho(so_nen_1h_da_troi=9, dg4_bars_1h=8)

    def test_KHONG_co_gia_tri_mac_dinh_cho_nguong(self) -> None:
        """🔴 N4: tham số đọc từ `tool_d_config.yaml`, không hardcode. Một
        mặc định ở đây làm cổng vẫn chạy được khi cấu hình chưa nạp — và
        chạy bằng một con số không ai duyệt."""
        p = inspect.signature(dg4_con_trong_cua_so_cho).parameters["dg4_bars_1h"]
        assert p.default is inspect.Parameter.empty

    def test_tran_bang_0_thi_RAISE_vi_no_tat_DCA_am_tham(self) -> None:
        with pytest.raises(TrancheGateError, match="dg4_bars_1h"):
            dg4_con_trong_cua_so_cho(so_nen_1h_da_troi=0, dg4_bars_1h=0)

    def test_so_nen_am_thi_RAISE(self) -> None:
        with pytest.raises(TrancheGateError, match="âm"):
            dg4_con_trong_cua_so_cho(so_nen_1h_da_troi=-1, dg4_bars_1h=8)

    def test_don_vi_nam_trong_TEN_BIEN(self) -> None:
        """Câu hỏi mở #12 — không lặp lại lỗi "2×k" của DR-010, nơi một
        con số không mang đơn vị bị hiểu theo hai thang khác nhau."""
        ten = set(inspect.signature(dg4_con_trong_cua_so_cho).parameters)
        assert ten == {"so_nen_1h_da_troi", "dg4_bars_1h"}
        assert all("1h" in t for t in ten)


class TestDG5ZssKhongSuyYeu:
    def test_giam_it_hon_nguong_thi_PASS(self) -> None:
        assert dg5_zss_khong_suy_yeu(
            zss_tai_tranche1=0.60, zss_hien_tai=0.50, nguong_giam_toi_da=0.30
        )

    def test_giam_DUNG_BANG_nguong_van_PASS_vi_spec_viet_giam_LON_HON(self) -> None:
        """§4: *"không giảm > 30%"*. Giảm đúng 30% chưa phải "> 30%"."""
        assert dg5_zss_khong_suy_yeu(
            zss_tai_tranche1=1.0, zss_hien_tai=0.70, nguong_giam_toi_da=0.30
        )

    def test_giam_qua_nguong_thi_FAIL(self) -> None:
        assert not dg5_zss_khong_suy_yeu(
            zss_tai_tranche1=1.0, zss_hien_tai=0.69, nguong_giam_toi_da=0.30
        )

    def test_zss_TANG_thi_PASS(self) -> None:
        assert dg5_zss_khong_suy_yeu(
            zss_tai_tranche1=0.50, zss_hien_tai=0.80, nguong_giam_toi_da=0.30
        )

    def test_KHONG_co_gia_tri_mac_dinh_cho_nguong_30_phan_tram(self) -> None:
        """🔴 Chốt quan trọng nhất của TD-0181. Ngưỡng 30% của §4 KHÔNG có
        trong `tool_d_config.yaml` và KHÔNG có dòng nào trong kiểm kê DOF
        — điền hộ một mặc định ở đây là tạo một bậc tự do không ai đếm,
        trong khi `N_ĐĂNG_KÝ = 114` đã là mẫu số của rào DSR §10.2."""
        p = inspect.signature(dg5_zss_khong_suy_yeu).parameters["nguong_giam_toi_da"]
        assert p.default is inspect.Parameter.empty

    @pytest.mark.parametrize("xau", [0.0, 1.0, 30.0, -0.3])
    def test_nguong_ngoai_khoang_0_1_thi_RAISE(self, xau: float) -> None:
        """`30` thay vì `0.30` là lỗi kinh điển của tham số tỉ lệ, và nó
        đi qua im lặng: `zss >= zss1 * (1 - 30)` luôn đúng ⇒ cổng LUÔN
        PASS, tức DG5 bị tắt mà không ai biết."""
        with pytest.raises(TrancheGateError, match="TỈ LỆ|nguong_giam_toi_da"):
            dg5_zss_khong_suy_yeu(
                zss_tai_tranche1=0.60, zss_hien_tai=0.10, nguong_giam_toi_da=xau
            )

    def test_zss_tranche1_bang_0_thi_RAISE_khong_PASS_suong(self) -> None:
        """Với `zss1 = 0` thì `zss >= 0` luôn đúng ⇒ cổng luôn PASS. Đó là
        một cổng chết đội lốt một cổng đang chạy."""
        with pytest.raises(TrancheGateError, match="zss_tai_tranche1"):
            dg5_zss_khong_suy_yeu(
                zss_tai_tranche1=0.0, zss_hien_tai=0.0, nguong_giam_toi_da=0.30
            )

    def test_KHONG_tinh_lai_ZSS_trong_module_nay(self) -> None:
        """DG5 chỉ SO hai giá trị do `zone_strength.zss()` sinh ra. Viết
        lại phép tính là tạo nguồn sự thật thứ hai cho cùng đại lượng —
        đúng lỗi mà TD-0163 đã có test ghim ở chỗ khác."""
        import tool_d.dg1_dg5_tranche_gates as mod

        src = inspect.getsource(mod)
        assert "def zss" not in src
        assert "TRONG_SO_ZSS" not in src


class TestDanhGiaTatCa:
    def test_bo_day_du_PASS_ca_nam(self) -> None:
        assert danh_gia_tat_ca(**_bo_day_du()) == {
            "DG1": True, "DG2": True, "DG3": True, "DG4": True, "DG5": True
        }

    def test_hinh_dang_khoa_dung_decision_log(self) -> None:
        """§8 đặc tả khối `gates` là `{"DG1": ..., ..., "DG5": ...}`. Có
        hàm này chính là để không chỗ gọi nào tự lắp lấy rồi trôi lệch."""
        assert list(danh_gia_tat_ca(**_bo_day_du())) == ["DG1", "DG2", "DG3", "DG4", "DG5"]

    @pytest.mark.parametrize(
        "ma,ghi_de",
        [
            ("DG1", {"close_4h_ke_tu_tranche1": [94.0]}),
            ("DG2", {"trend_dir_hien_tai": "DOWN"}),
            ("DG3", {"margin_reserve_con_lai": 1.0}),
            ("DG4", {"so_nen_1h_da_troi": 99}),
            ("DG5", {"zss_hien_tai": 0.01}),
        ],
    )
    def test_moi_cong_hong_RIENG_LE_chi_lam_do_dung_no(self, ma: str, ghi_de: dict) -> None:
        """Nếu một ca làm nhiều cổng cùng đỏ thì các cổng đang dính vào
        nhau, và lúc đó decision log không còn nói được cổng NÀO đã chặn."""
        kq = danh_gia_tat_ca(**_bo_day_du(**ghi_de))
        assert kq[ma] is False
        assert all(v for k, v in kq.items() if k != ma)

    def test_KHONG_gop_thanh_mot_bool(self) -> None:
        """Ai cần "được bơm không" thì tự `all(...)` — và khi đó họ nhìn
        thấy mình đang bỏ qua thông tin cổng nào đã chặn."""
        assert isinstance(danh_gia_tat_ca(**_bo_day_du()), dict)

    def test_KHONG_co_cong_tac_bat_tat_cong_nao(self) -> None:
        """Z2 tắt DG5 là việc của TD-0183. Một công tắc lọt vào đây bây
        giờ sẽ là công tắc không ai test được là nó đổi hành vi thật."""
        ten = set(inspect.signature(danh_gia_tat_ca).parameters)
        assert not any("bat" in t or "tat" in t or "enable" in t for t in ten)


class TestKhongDungChungHangSoVoiDG6:
    def test_khong_import_hang_so_dong_bang_cua_dg6(self) -> None:
        """🔴 `dg4_bars_1h` (🟡 tunable #7) và `dg6b_bars_1h` (🔒 đóng
        băng, `dof: -1`) cùng bằng 8 nhưng KHÁC HẠNG. Gộp làm một hằng số
        biến một tham số đóng băng thành tune được — đúng chiều nới lỏng
        mà kiểm kê DOF tồn tại để chặn."""
        import ast

        import tool_d.dg1_dg5_tranche_gates as mod

        # Hỏi bằng AST chứ không bằng chuỗi: docstring của module CÓ nhắc
        # tên hằng số đó để giải thích vì sao không dùng nó. Bắt theo
        # chuỗi sẽ bắt luôn lời giải thích — đúng hình dạng lỗi mà L-Z25
        # từng gặp với `hyperopt` trong một câu văn.
        cay = ast.parse(inspect.getsource(mod))
        assert not [
            n for n in ast.walk(cay)
            if isinstance(n, ast.ImportFrom) and n.module == "tool_d.dg6_early_invalidation"
        ], "DG4 không được lấy ngưỡng từ hằng số ĐÓNG BĂNG của DG6"
        assert not [
            n for n in ast.walk(cay)
            if isinstance(n, ast.Name) and n.id == "SO_NEN_TOI_THIEU_B"
        ], "SO_NEN_TOI_THIEU_B bị DÙNG như một giá trị, không chỉ được nhắc tới"

    def test_dg6_van_giu_hang_so_rieng_khong_bi_sua(self) -> None:
        from tool_d.dg6_early_invalidation import SO_NEN_TOI_THIEU_B

        assert SO_NEN_TOI_THIEU_B == 8
