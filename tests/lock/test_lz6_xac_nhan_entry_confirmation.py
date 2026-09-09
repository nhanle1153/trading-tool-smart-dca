"""L-Z6 — §3.3b + PHẦN 3b: xác nhận entry tranche 1 bằng price-action,
tối đa 3 nến chờ, KHÔNG mở rộng cửa sổ tìm kiếm (chống overfitting
ngược). Công thức đúng: **`(a VÀ c) HOẶC (b)`**.

Phạm vi CHƯA phủ: "mọi tranche 1 đã khớp đều có entry_confirmation
không rỗng" cần bản ghi tranche fill thật (§3.5) — chưa có code đặt
lệnh ở D1/D2. Test ở đây khoá đúng hành vi của `tim_xac_nhan_entry()`;
sẽ nối vào bản ghi plan thật khi TD-0114 dựng chiến lược.

════ MT-15 (08/09/2026) — vì sao `TestTimXacNhanEntry` giữ NGUYÊN mọi
khẳng định cũ mà vẫn là bản sửa đúng ════

Bản đầu khoá công thức `(a) HOẶC (b)`, thiếu hẳn điều kiện (c) mà PHẦN
3b gọi là *"BỔ NGỮ BẮT BUỘC cho (a)"*. Lo ngại lúc phát hiện: sửa nó
nghĩa là **phá một test khoá** — thứ dự án đòi lệnh tường minh mới được
làm, và là cách một quyết định biến mất mà không ai ghi.

Hoá ra không phải. Vì §10.1b định nghĩa arm **`Z0-V1` đúng bằng "tắt
(c)"**, tức `(a) HOẶC (b)` — **chính là công thức năm ca dưới đây vẫn
luôn mô tả**. Nên chúng chỉ cần khai tường minh `bat_dieu_kien_c=False, wick_frac=0.5`
và **trở thành bộ test khoá cho `Z0-V1`**. Không ca nào bị xoá, không
khẳng định nào bị nới. Thứ trông như phá một test khoá hoá ra là **đổi
nhãn nó về đúng arm mà nó vẫn luôn mô tả** (tiền lệ TD-0150).

`TestDieuKienC` và `TestCongThucKetHop` bên dưới là phần MỚI: khoá arm
`Z0` (bật (c)) và khoá đúng chỗ dễ sai nhất của công thức — xem
docstring của từng lớp.
"""

from __future__ import annotations

import pytest

from tool_d.entry_confirmation import (
    ThieuDuLieuVolumeError,
    hap_thu_co_volume,
    la_nen_rejection,
    phan_ky_momentum,
    tim_xac_nhan_entry,
)


class TestLaNenRejectionDay:
    def test_bong_duoi_du_50pt_va_dong_cua_nua_tren_la_rejection(self) -> None:
        # range=10 (100-90), bong_duoi=min(96,99)-90=6 (>=5), dong=99 nam nua tren (>=95)
        assert la_nen_rejection(96, 100, 90, 99, loai="day", wick_frac=0.5) is True

    def test_bong_duoi_khong_du_50pt_thi_khong_phai(self) -> None:
        # bong_duoi = min(94,95)-90=4 (<5)
        assert la_nen_rejection(94, 100, 90, 95, loai="day", wick_frac=0.5) is False

    def test_dong_cua_nua_duoi_thi_khong_phai_du_bong_du(self) -> None:
        # bong_duoi=8 (du) nhung dong=93 nam nua duoi (<95)
        assert la_nen_rejection(98, 100, 90, 93, loai="day", wick_frac=0.5) is False


class TestLaNenRejectionDinh:
    def test_bong_tren_du_va_dong_cua_nua_duoi_la_rejection(self) -> None:
        assert la_nen_rejection(94, 100, 90, 91, loai="dinh", wick_frac=0.5) is True


class TestWickFracLaThamSoTierB:
    """DR-D4-08 §3 #1 — `tier_b.wick_close_upper_frac` điều khiển CẢ HAI vế
    của (a) bằng MỘT số, và là tham số BẮT BUỘC (TD-0195/MT-23: bản trước
    là hai số ma `0.5`, không có đường đọc nào từ YAML)."""

    def test_wick_frac_bat_buoc_o_ca_hai_ham(self) -> None:
        import inspect

        for ham in (la_nen_rejection, tim_xac_nhan_entry):
            assert inspect.signature(ham).parameters["wick_frac"].default is inspect.Parameter.empty, ham.__name__

    def test_wick_frac_dieu_khien_ve_BONG(self) -> None:
        # bóng dưới = 6/10 range: đủ với 0,5, KHÔNG đủ với 0,7 (đóng cửa 99 vẫn thoả vế đóng)
        assert la_nen_rejection(96, 100, 90, 99, loai="day", wick_frac=0.5) is True
        assert la_nen_rejection(96, 100, 90, 99, loai="day", wick_frac=0.7) is False

    def test_wick_frac_dieu_khien_ve_DONG_CUA(self) -> None:
        # bóng 9/10 (dư với mọi ngưỡng); đóng cửa 96 = 60% range: đủ với 0,5, KHÔNG đủ với 0,7
        assert la_nen_rejection(99, 100, 90, 96, loai="day", wick_frac=0.5) is True
        assert la_nen_rejection(99, 100, 90, 96, loai="day", wick_frac=0.7) is False

    def test_wick_frac_ngoai_khoang_thi_RAISE(self) -> None:
        for xau in (0.0, 1.0, -0.1, float("nan")):
            with pytest.raises(ValueError):
                la_nen_rejection(96, 100, 90, 99, loai="day", wick_frac=xau)


class TestCongTacDieuKienCTheoArm:
    """§10.1b: `Z0-V1` = tắt (c); mọi arm khác bật. Bảng tường minh, arm lạ ⇒ raise."""

    def test_Z0_V1_tat_moi_arm_khac_bat(self) -> None:
        from tool_d.arm_switches import ARM_HOP_LE
        from tool_d.entry_confirmation import bat_dieu_kien_c_cua_arm

        assert bat_dieu_kien_c_cua_arm("Z0-V1") is False
        assert all(bat_dieu_kien_c_cua_arm(a) is True for a in ARM_HOP_LE if a != "Z0-V1")

    def test_arm_la_thi_RAISE_khong_mac_dinh_ve_Z0(self) -> None:
        from tool_d.arm_switches import ArmSwitchError
        from tool_d.entry_confirmation import bat_dieu_kien_c_cua_arm

        for la in ("Z0-T2", "", "Z9"):
            with pytest.raises(ArmSwitchError):
                bat_dieu_kien_c_cua_arm(la)


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
        assert tim_xac_nhan_entry(mo, cao, thap, dong, rsi, i_cham=0, loai="day", bat_dieu_kien_c=False, wick_frac=0.5) == 0

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
            tim_xac_nhan_entry(mo, cao, thap, dong, rsi, i_cham=0, loai="day", bat_dieu_kien_c=False, wick_frac=0.5, lan_cham_truoc=lan_cham_truoc)
            == 1
        )

    def test_het_3_nen_khong_xac_nhan_tra_ve_none(self) -> None:
        mo = [95, 95, 95]
        cao = [100, 100, 100]
        thap = [90, 90, 90]
        dong = [92, 92, 92]  # khong rejection nen nao
        rsi = [50, 50, 50]  # khong phan ky (khong co lan_cham_truoc)
        assert tim_xac_nhan_entry(mo, cao, thap, dong, rsi, i_cham=0, loai="day", bat_dieu_kien_c=False, wick_frac=0.5) is None

    def test_khong_mo_rong_cua_so_qua_3_nen(self) -> None:
        # xac nhan chi xuat hien o nen thu 4 (index 3) - PHAI bo lo, khong tim tiep
        mo = [95, 95, 95, 96]
        cao = [100, 100, 100, 100]
        thap = [90, 90, 90, 90]
        dong = [92, 92, 92, 99]  # nen index3 la rejection ro rang
        rsi = [50, 50, 50, 50]
        assert tim_xac_nhan_entry(mo, cao, thap, dong, rsi, i_cham=0, loai="day", bat_dieu_kien_c=False, wick_frac=0.5, so_nen_cho_toi_da=3) is None

    def test_khong_co_lan_cham_truoc_thi_chi_xet_rejection(self) -> None:
        mo = [95, 95]
        cao = [100, 100]
        thap = [90, 90]
        dong = [92, 92]
        rsi = [20, 90]  # neu co lan_cham_truoc se phan ky, nhung khong co -> None
        assert tim_xac_nhan_entry(mo, cao, thap, dong, rsi, i_cham=0, loai="day", bat_dieu_kien_c=False, wick_frac=0.5, lan_cham_truoc=None) is None


class TestDieuKienC:
    """PHẦN 3b (c) — hấp thụ có volume tại lúc chạm zone."""

    def test_volume_bang_dung_nguong_thi_dat(self) -> None:
        assert hap_thu_co_volume(100.0, 100.0, 1.0) is True

    def test_volume_duoi_nguong_thi_khong_dat(self) -> None:
        assert hap_thu_co_volume(99.0, 100.0, 1.0) is False

    def test_mau_so_bang_0_thi_FAIL_CLOSED_khong_chia_cho_0(self) -> None:
        """Không có mẫu số nghĩa là CHƯA BIẾT, và "chưa biết" ở cổng vào
        lệnh phải tính về phía KHÔNG vào."""
        assert hap_thu_co_volume(100.0, 0.0, 1.0) is False

    def test_NaN_thi_FAIL_CLOSED(self) -> None:
        nan = float("nan")
        assert hap_thu_co_volume(100.0, nan, 1.0) is False
        assert hap_thu_co_volume(nan, 100.0, 1.0) is False


class TestCongThucKetHop:
    """🔴 `(a VÀ c) HOẶC (b)` — KHÔNG phải `(a OR b OR c)`.

    Spec PHẦN 3b: *"(c) là BỔ NGỮ cho (a), không phải tín hiệu độc lập.
    Volume cao mà không có rejection = có thể đang bị xuyên qua."*
    """

    # nến 0: rejection rõ ràng (bóng dưới dài, đóng cửa nửa trên)
    MO, CAO, THAP, DONG = [96], [100], [90], [99]
    RSI = [50]

    def test_a_dung_c_dung_thi_XAC_NHAN(self) -> None:
        assert (
            tim_xac_nhan_entry(
                self.MO, self.CAO, self.THAP, self.DONG, self.RSI, i_cham=0,
                loai="day", bat_dieu_kien_c=True, wick_frac=0.5,
                volume=[150.0], volume_ma=[100.0], v_min=1.0,
            )
            == 0
        )

    def test_a_dung_c_SAI_thi_KHONG_xac_nhan(self) -> None:
        """Đây là ca phân biệt `Z0` với `Z0-V1`. Nếu ca này trả 0 thì
        (c) đang không có tác dụng gì, và hai arm lại trùng nhau."""
        assert (
            tim_xac_nhan_entry(
                self.MO, self.CAO, self.THAP, self.DONG, self.RSI, i_cham=0,
                loai="day", bat_dieu_kien_c=True, wick_frac=0.5,
                volume=[50.0], volume_ma=[100.0], v_min=1.0,
            )
            is None
        )

    def test_CUNG_du_lieu_do_Z0_V1_thi_VAN_xac_nhan(self) -> None:
        """🔑 Chứng kiến cụ thể rằng `Z0` và `Z0-V1` KHÔNG còn là một
        cấu hình. Cùng một đầu vào, hai kết quả khác nhau — nếu ca này
        và ca trên cho cùng kết quả thì một suất trial trong 114 đang
        đo một khác biệt bằng không (MT-15)."""
        assert (
            tim_xac_nhan_entry(
                self.MO, self.CAO, self.THAP, self.DONG, self.RSI, i_cham=0,
                loai="day", bat_dieu_kien_c=False, wick_frac=0.5,
            )
            == 0
        )

    def test_c_dung_nhung_a_SAI_thi_KHONG_xac_nhan(self) -> None:
        """(c) KHÔNG phải tín hiệu độc lập — volume cao mà không có
        rejection có thể đang là bị xuyên qua, không phải hấp thụ."""
        assert (
            tim_xac_nhan_entry(
                [95], [100], [90], [92], [50], i_cham=0,  # đóng cửa nửa dưới
                loai="day", bat_dieu_kien_c=True, wick_frac=0.5,
                volume=[999.0], volume_ma=[100.0], v_min=1.0,
            )
            is None
        )

    def test_nen_bi_c_LOAI_van_duoc_xet_tiep_bang_b(self) -> None:
        """🔴 Chỗ dễ viết sai nhất: công thức là `(a VÀ c) HOẶC (b)`,
        KHÔNG phải `nếu (a) thì (c), ngược lại (b)`. Một nến vừa là
        rejection (nhưng volume yếu) vừa có phân kỳ RSI thì VẪN phải
        được xác nhận qua vế (b). Cài đặt dùng `continue` sau khi (c)
        loại sẽ trượt ca này."""
        got = tim_xac_nhan_entry(
            [96], [100], [90], [99], [35], i_cham=0,
            loai="day", bat_dieu_kien_c=True, wick_frac=0.5,
            volume=[10.0], volume_ma=[100.0], v_min=1.0,  # (c) loại
            lan_cham_truoc=(94.0, 28.0),  # nhưng (b) đúng: rsi 35>28, giá 90<=94
        )
        assert got == 0

    def test_bat_c_ma_THIEU_du_lieu_thi_RAISE_khong_am_tham_bo_qua(self) -> None:
        """Bỏ qua (c) trong im lặng nghĩa là chạy `Z0-V1` dưới nhãn
        `Z0`, và không gì trong kết quả lộ ra điều đó."""
        for thieu in ("volume", "volume_ma", "v_min"):
            kw = {"volume": [100.0], "volume_ma": [100.0], "v_min": 1.0}
            kw.pop(thieu)
            with pytest.raises(ThieuDuLieuVolumeError, match="Z0-V1"):
                tim_xac_nhan_entry(
                    self.MO, self.CAO, self.THAP, self.DONG, self.RSI, i_cham=0,
                    loai="day", bat_dieu_kien_c=True, wick_frac=0.5, **kw,
                )

    def test_bat_dieu_kien_c_la_tham_so_BAT_BUOC(self) -> None:
        """Không mặc định — arm nào quên khai sẽ lặng lẽ chạy như arm
        khác, và hai arm lại nhập làm một (MT-15)."""
        import inspect

        sig = inspect.signature(tim_xac_nhan_entry)
        assert sig.parameters["bat_dieu_kien_c"].default is inspect.Parameter.empty
