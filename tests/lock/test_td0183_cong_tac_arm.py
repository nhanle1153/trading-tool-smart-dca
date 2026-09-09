"""🔴 TD-0183 — công tắc arm Z1 / Z0-S1 / Z2 (phạm vi rút gọn 2,5/4).

Yêu cầu của chính dòng TD-0183: *"mỗi công tắc một test chứng minh nó ĐỔI
HÀNH VI THẬT, không phải cờ chết"*. Nên mỗi công tắc ở đây có một ca so
**cùng đầu vào, hai arm** và đòi kết quả **khác nhau** — chứ không chỉ hỏi
"cờ có tồn tại không".

Ba thứ bộ test canh chặt nhất:

1. **`r_eff_plan` phải tính LẠI theo SL mới của Z1.** Đây là lỗi im lặng
   đắt nhất có thể có: `r_eff` chảy thẳng vào cỡ lệnh (§6.8e), nên một Z1
   mang `r_eff` của zone sẽ vào lệnh với cỡ của arm KHÁC, mà bảng kết quả
   vẫn trông hoàn toàn bình thường.
2. **`Z0-S1` KHÔNG được phụ thuộc `R_eff`.** Toàn bộ giá trị của arm này
   là tính robustness (§10.1b). Canh bằng cách đổi `r_eff` và đòi kết quả
   KHÔNG đổi — một test hỏi "có nhánh riêng không" sẽ không bắt được ca
   nhánh riêng vẫn lỡ chia cho `r_eff`.
3. **`Z0-T2` không được là arm thứ mười.** Đếm nhầm là tiêu thừa một suất
   thật trên tổng 114.
"""

from __future__ import annotations

import inspect

import pytest

from tool_d.arm_switches import (
    ARM_DON_TRANCHE,
    ARM_HOP_LE,
    HE_SO_ATR_Z1,
    ArmSwitchError,
    cong_ap_dung,
    duoc_them_tranche,
    ke_hoach_theo_arm,
    notional_tranche1_theo_arm,
    sl_neo_atr,
)
from tool_d.config.dof import ARM_B2_COUNT
from tool_d.notional import tranche1_notional
from tool_d.trade_plan import tinh_ke_hoach

# `buf_sl_he_so` giá trị THỬ (TD-0195) — mọi ca dưới kiểm quan hệ giữa các
# arm, không ca nào ghim con số sản xuất.
ZONE = dict(zone_low=90.0, zone_high=100.0, gia_dong_cua=95.0, atr_1h_tai_tranche1=1.0,
            buf_sl_he_so=0.4)
CO_LENH = dict(e_d=500.0, rho_pct=0.375, n_tranches=3)


def _cong(**ghi_de) -> dict[str, bool]:
    kq = {c: True for c in ("DG1", "DG2", "DG3", "DG4", "DG5")}
    kq.update(ghi_de)
    return kq


class TestDanhSachArm:
    def test_dung_CHIN_arm_khop_ARM_B2_COUNT(self) -> None:
        """Danh sách arm và hằng số ngân sách phải nhìn nhau. Hai nguồn sự
        thật cho cùng một con số chính là cơ chế đã gây lệch số của v5."""
        assert len(ARM_HOP_LE) == ARM_B2_COUNT == 9
        assert len(set(ARM_HOP_LE)) == 9

    def test_Z0_T2_KHONG_phai_arm_thu_muoi(self) -> None:
        """§10.1b: *"Mốc so sánh — không phải arm mới, không tốn trial
        thêm"*. Nó CHÍNH LÀ Z0."""
        assert "Z0-T2" not in ARM_HOP_LE
        assert "Z0" in ARM_HOP_LE

    def test_arm_la_thi_raise_va_noi_ro_bay_Z0_T2(self) -> None:
        with pytest.raises(ArmSwitchError, match="Z0-T2"):
            cong_ap_dung("Z0-T2")


class TestZ1SLNeoATR:
    def test_cong_thuc_dung_2_2_lan_ATR_duoi_p1(self) -> None:
        assert sl_neo_atr(p1=100.0, atr_4h=2.0) == pytest.approx(100.0 - 2.2 * 2.0)
        assert HE_SO_ATR_Z1 == 2.2

    def test_DOI_HANH_VI_THAT_Z1_khac_Z0_tren_cung_dau_vao(self) -> None:
        """🔴 Ca chứng minh công tắc không phải cờ chết."""
        z0 = ke_hoach_theo_arm(arm="Z0", atr_4h=2.0, **ZONE)
        z1 = ke_hoach_theo_arm(arm="Z1", atr_4h=2.0, **ZONE)
        assert z1.sl != z0.sl
        assert z1.r_eff_plan != z0.r_eff_plan
        # mọi thứ CÒN LẠI phải giống hệt — công tắc chỉ được đổi SL
        assert (z1.p1, z1.p2, z1.p3, z1.zone_low, z1.zone_high) == (
            z0.p1, z0.p2, z0.p3, z0.zone_low, z0.zone_high
        )

    def test_r_eff_plan_TINH_LAI_theo_sl_moi_khong_giu_cua_zone(self) -> None:
        """🔴 Lỗi im lặng đắt nhất: `r_eff` chảy vào cỡ lệnh (§6.8e). Một
        Z1 mang `r_eff` của zone sẽ vào lệnh với cỡ của arm KHÁC."""
        z1 = ke_hoach_theo_arm(arm="Z1", atr_4h=2.0, **ZONE)
        p_avg = (z1.p1 + z1.p2 + z1.p3) / 3
        assert z1.r_eff_plan == pytest.approx((p_avg - z1.sl) / p_avg)

    def test_arm_ZONE_tra_ve_DUNG_ket_qua_cua_tinh_ke_hoach(self) -> None:
        """Không dựng lại đối tượng cho nhánh thường — nếu dựng lại thì có
        nguồn sự thật thứ hai cho công thức §3.1."""
        goc = tinh_ke_hoach(atr_4h=2.0, **ZONE)
        for arm in ("Z0", "Z2", "Z3", "Z3b", "Z0-T0", "Z0-S1"):
            assert ke_hoach_theo_arm(arm=arm, atr_4h=2.0, **ZONE) == goc

    def test_ATR_qua_lon_lam_SL_AM_thi_RAISE(self) -> None:
        """🐛 Ca này bắt được lỗi thật trong chốt đầu tiên tôi viết: chốt
        `sl >= p_avg` một mình KHÔNG đủ. Với ATR rất lớn, `sl` ra **âm**
        — vẫn nhỏ hơn `p_avg` nên lọt qua — và `r_eff` ra 234%, tức cỡ
        lệnh nhỏ đi một cách vô nghĩa thay vì báo lỗi. Giá không âm được."""
        with pytest.raises(ArmSwitchError, match="≤ 0"):
            ke_hoach_theo_arm(arm="Z1", atr_4h=100.0, **ZONE)

    def test_ATR_qua_NHO_lam_SL_nam_tren_gia_vao_thi_RAISE(self) -> None:
        """Vế còn lại của cùng bất biến: `r_eff ≤ 0` chảy vào §6.8e sinh
        cỡ lệnh âm hoặc vô cực."""
        with pytest.raises(ArmSwitchError, match="r_eff"):
            ke_hoach_theo_arm(arm="Z1", atr_4h=0.1, **ZONE)

    def test_atr_am_thi_RAISE(self) -> None:
        with pytest.raises(ArmSwitchError, match="atr_4h"):
            sl_neo_atr(p1=100.0, atr_4h=-1.0)


class TestZ0S1DinhCoTheoVon:
    """📌 **DR-D4-07 đổi ĐƯỜNG VÀO, không nới một khẳng định nào.** Tham số
    `notional_co_dinh_usdt` (con số USDT cứng) bị bỏ vì cấu hình để `null` ⇒
    arm raise ⇒ **0 lệnh** trên 48 mã EXPLORE/22 tháng. Nay notional là đại
    lượng dẫn xuất `rho_pct/100 × E_D / notional_ref_r_eff`.

    Năm ca dưới đây **giữ nguyên khẳng định**, chỉ đổi tên tham số; `ref =
    0.00625` tái lập đúng notional 300 USDT của bản cũ nên các con số ghim
    không đổi. Một ca được **SIẾT** (khoảng hợp lệ `(0,1)` thay vì `> 0`).
    KHÔNG xoá ca nào — xoá một ca đỏ cho sạch bảng là cách một quyết định
    biến mất mà không ai ghi (tiền lệ TD-0150 xử hai ca của TD-0149).

    Bất biến MỚI mà DR-D4-07 thêm — *notional phải đổi khi `E_D` đổi* — nằm
    ở `test_td0191_thang_notional_z0_s1.py`, không nhồi vào đây."""

    def test_DOI_HANH_VI_THAT_khac_Z0_tren_cung_dau_vao(self) -> None:
        z0 = notional_tranche1_theo_arm(arm="Z0", r_eff=0.03, **CO_LENH)
        # DR-D4-07: tham số đổi từ con số USDT cứng sang THAM CHIẾU R_eff.
        # `ref = 0.00625` tái lập đúng notional 300 USDT của bản cũ, nên khẳng
        # định gốc giữ NGUYÊN GIÁ TRỊ — không nới, chỉ đổi đường vào.
        s1 = notional_tranche1_theo_arm(
            arm="Z0-S1", r_eff=0.03, notional_ref_r_eff=0.00625, **CO_LENH
        )
        assert s1 != z0
        assert s1 == pytest.approx(100.0)

    def test_KHONG_phu_thuoc_R_eff_day_la_toan_bo_gia_tri_cua_arm(self) -> None:
        """🔴 §10.1b: arm này tồn tại vì nó *"KHÔNG phụ thuộc `R_eff` tính
        đúng"*. Đổi `r_eff` gấp ba mà kết quả đổi thì arm mất ý nghĩa —
        và một test chỉ hỏi "có nhánh riêng không" sẽ không bắt được."""
        a = notional_tranche1_theo_arm(
            arm="Z0-S1", r_eff=0.01, notional_ref_r_eff=0.00625, **CO_LENH
        )
        b = notional_tranche1_theo_arm(
            arm="Z0-S1", r_eff=0.03, notional_ref_r_eff=0.00625, **CO_LENH
        )
        assert a == b
        # đối chứng: nhánh RỦI RO thì PHẢI đổi theo r_eff
        assert notional_tranche1_theo_arm(
            arm="Z0", r_eff=0.01, **CO_LENH
        ) != notional_tranche1_theo_arm(arm="Z0", r_eff=0.03, **CO_LENH)

    def test_nhanh_RUI_RO_goi_thang_ham_goc_khong_chep_cong_thuc(self) -> None:
        assert notional_tranche1_theo_arm(
            arm="Z0", r_eff=0.03, **CO_LENH
        ) == tranche1_notional(r_eff=0.03, **CO_LENH)

    def test_KHONG_co_gia_tri_mac_dinh_cho_notional_co_dinh(self) -> None:
        """🔴 Cùng chốt với ngưỡng DG5 (TD-0169): spec KHÔNG cho con số
        này ở đâu. §10.1b chỉ nói "notional CỐ ĐỊNH"; "300 USDT" ở dòng
        1285 nằm trong một lập luận minh hoạ, và `tool_d_config.yaml`
        không có khoá nào. Điền hộ là thêm một bậc tự do không ai đếm."""
        with pytest.raises(ArmSwitchError, match="notional_ref_r_eff"):
            notional_tranche1_theo_arm(arm="Z0-S1", r_eff=0.03, **CO_LENH)

    def test_truyen_notional_co_dinh_cho_arm_RUI_RO_thi_RAISE(self) -> None:
        """Im lặng bỏ qua tham số thừa là cách chỗ gọi tưởng mình đang
        chạy Z0-S1 trong khi thực ra chạy Z0."""
        with pytest.raises(ArmSwitchError, match="hiểu sai arm"):
            notional_tranche1_theo_arm(
                arm="Z0", r_eff=0.03, notional_ref_r_eff=0.00625, **CO_LENH
            )

    @pytest.mark.parametrize("xau", [0.0, -0.00625, 1.0, 3.0, 100.0])
    def test_tham_chieu_ngoai_khoang_thi_RAISE(self, xau: float) -> None:
        """DR-D4-07 SIẾT ca này, không nới: bản cũ chỉ chặn `≤ 0`. Tham chiếu
        là TỈ LỆ nên `1.0` trở lên cũng vô nghĩa, và `3.0` (gõ `3` thay vì
        `0.03`) làm cỡ lệnh nhỏ đi 100 lần mà không phép kiểm nào khác báo đỏ.

        ⚠️ **Giới hạn thật của chốt này, nói thẳng:** nó chỉ bắt được ca gõ
        nhầm ra ngoài `(0,1)`. Gõ `0.625` thay vì `0.00625` vẫn LỌT, vì cả hai
        đều là tỉ lệ hợp lệ về mặt hình thức. Không có cách nào phân biệt bằng
        kiểu dữ liệu — chỗ chặn ca đó là `test_gia_tri_dan_xuat_tren_cau_hinh_that`
        của TD-0191, đối chiếu với cấu hình THẬT."""
        with pytest.raises(ArmSwitchError):
            notional_tranche1_theo_arm(
                arm="Z0-S1", r_eff=0.03, notional_ref_r_eff=xau, **CO_LENH
            )


class TestZ2BoDG5:
    def test_Z2_bo_DUNG_DG5_giu_bon_cong_con_lai(self) -> None:
        assert cong_ap_dung("Z2") == ("DG1", "DG2", "DG3", "DG4")

    def test_Z3_va_Z3b_giu_du_nam_cong(self) -> None:
        assert cong_ap_dung("Z3") == ("DG1", "DG2", "DG3", "DG4", "DG5")
        assert cong_ap_dung("Z3b") == ("DG1", "DG2", "DG3", "DG4", "DG5")

    def test_DOI_HANH_VI_THAT_cung_ket_qua_cong_hai_arm_hai_ket_luan(self) -> None:
        """🔴 Ca chứng minh công tắc Z2 không phải cờ chết: DG5 đỏ, mọi
        cổng khác xanh → Z2 vẫn được bơm, Z3 thì không."""
        cong = _cong(DG5=False)
        assert duoc_them_tranche(arm="Z2", ket_qua_cong=cong) is True
        assert duoc_them_tranche(arm="Z3", ket_qua_cong=cong) is False

    def test_Z2_van_bi_chan_boi_bon_cong_con_lai(self) -> None:
        """Bỏ DG5 KHÔNG có nghĩa bỏ hết — nếu ca này xanh thì công tắc đã
        tắt nhầm cả cụm."""
        assert duoc_them_tranche(arm="Z2", ket_qua_cong=_cong(DG2=False)) is False

    def test_arm_ENTRY_DON_thi_RAISE_chu_khong_tra_True(self) -> None:
        """Trả `True` ở đây nghĩa là "được bơm thêm tranche" cho một arm
        không hề có tranche 2/3 — một câu trả lời sai cho một câu hỏi lẽ
        ra không được đặt."""
        for arm in sorted(ARM_DON_TRANCHE):
            assert cong_ap_dung(arm) == ()
            with pytest.raises(ArmSwitchError, match="ENTRY ĐƠN"):
                duoc_them_tranche(arm=arm, ket_qua_cong=_cong())

    def test_thieu_cong_arm_CAN_thi_RAISE_khong_coi_la_False(self) -> None:
        thieu = _cong()
        del thieu["DG4"]
        with pytest.raises(ArmSwitchError, match="DG4"):
            duoc_them_tranche(arm="Z3", ket_qua_cong=thieu)

    def test_thieu_DG5_KHONG_lam_Z2_do_vi_Z2_khong_dung_no(self) -> None:
        chi_bon = {c: True for c in ("DG1", "DG2", "DG3", "DG4")}
        assert duoc_them_tranche(arm="Z2", ket_qua_cong=chi_bon) is True


class TestKhongLamHaiVeDaLoaiBo:
    """Hai vế cố ý KHÔNG làm — có test để chúng không bị lặng lẽ thêm vào
    dưới dạng cờ chết, và để người sau đọc được LÝ DO."""

    def test_KHONG_co_cong_tac_mult_zss(self) -> None:
        """`mult_zss` không có ở tầng tính cỡ lệnh, nên "tắt mult_zss" sẽ
        là cờ chết — đúng thứ dòng TD-0183 tự cấm."""
        import ast

        import tool_d.arm_switches as mod

        # Hỏi bằng AST, không bằng chuỗi: docstring module CÓ nhắc
        # `mult_zss` để giải thích vì sao không làm vế đó. Bắt theo chuỗi
        # sẽ bắt luôn lời giải thích — đúng hình dạng lỗi `L-Z25` từng gặp
        # với `hyperopt` trong một câu văn.
        cay = ast.parse(inspect.getsource(mod))
        ten_dinh_nghia = {
            n.name for n in ast.walk(cay)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        } | {
            t.id for n in ast.walk(cay) if isinstance(n, ast.Assign)
            for t in n.targets if isinstance(t, ast.Name)
        } | {
            n.target.id for n in ast.walk(cay)
            if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)
        }
        assert not [t for t in ten_dinh_nghia if "mult_zss" in t.lower()], (
            "có định danh mang tên mult_zss — tắt một thứ chưa bật là cờ chết"
        )

    def test_KHONG_co_cong_tac_dieu_kien_c_o_module_nay(self) -> None:
        """Công tắc `(c)` thuộc `entry_confirmation.py` (MT-15), không
        thuộc tầng arm — hai chỗ cùng bật/tắt một thứ sẽ trôi lệch."""
        import tool_d.arm_switches as mod

        src = inspect.getsource(mod)
        assert "bat_dieu_kien_c" not in src
        assert "v_min" not in src

    def test_Z0_V1_van_la_arm_hop_le_du_cong_tac_o_noi_khac(self) -> None:
        """Nó vẫn là một trong chín cấu hình — chỉ là công tắc của nó nằm
        ở module khác. Loại nó khỏi danh sách sẽ làm lệch `ARM_B2_COUNT`."""
        assert "Z0-V1" in ARM_HOP_LE
        assert cong_ap_dung("Z0-V1") == ()
