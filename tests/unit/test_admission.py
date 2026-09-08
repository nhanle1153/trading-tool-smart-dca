"""TD-0188 — kiểm tra kết nạp danh mục §6.8f Bước 2 (module thuần).

Ba nhóm đắt nhất:

1. **Bảng ví dụ của spec tái lập được** — 6 / 10 / 13 / 20 mã tối đa ở
   `R_eff` = 0,9 / 1,5 / 2,0 / 3,0 %, và **mọi hàng cho cùng tổng notional**
   (6×208 = 20×62). Nếu ca này đỏ thì hoặc module sai, hoặc spec sai — cả
   hai đều là thông tin, không phải chỗ để nới dung sai.
2. **Cả hai điều kiện đều phải kiểm.** Ở 3x trần rủi ro không bao giờ bind,
   nên một cài đặt chỉ kiểm margin vẫn XANH ở mọi ca 3x. Có ca ở `L=10x`
   để trần rủi ro bind trước — đó là ca duy nhất phân biệt được.
3. **Tính trên KẾ HOẠCH ĐẦY ĐỦ, không phải phần đã khớp.** Sai chỗ này cho
   mở nhiều lệnh hơn mức chịu được, và chỉ lộ ra đúng lúc mọi lệnh khớp đủ.
"""

from __future__ import annotations

from types import MappingProxyType

import pytest

from tool_d.admission import (
    TRAN_MARGIN_TREN_E_D,
    AdmissionError,
    ViTheMo,
    kiem_ket_nap,
    tinh_tran_notional_danh_muc,
)
from tool_d.config.loader import ToolDConfig, load_tool_d_config, resolve
from tool_d.sizing import HeSoMult, lap_ke_hoach_co_lenh

CFG_THAT = load_tool_d_config()
MULT_1 = HeSoMult(regime=1.0, zss=1.0, corr=1.0, dd=1.0, edge=1.0, deploy=1.0)


def _cfg(*, e_d=500.0, rho_pct=0.375, l_exchange=3.0, daily_loss=8.0) -> ToolDConfig:
    return ToolDConfig(
        tier_a=MappingProxyType({
            "E_D": e_d, "rho_pct": rho_pct, "L_exchange": l_exchange,
            "daily_loss_budget_pct": daily_loss,
        }),
        tier_b=MappingProxyType({}),
        tier_frozen=MappingProxyType({
            "w_tranche": MappingProxyType({"value": (0.3333, 0.3333, 0.3334), "dof": 0})
        }),
        tier_c=MappingProxyType({"n_tranches": 3}),
        raw_text="", sha256="",
    )


def _ke_hoach(cfg: ToolDConfig, r_eff: float):
    return lap_ke_hoach_co_lenh(cfg=cfg, arm="Z0", r_eff=r_eff, mult=MULT_1)


def _so_ma_toi_da(cfg: ToolDConfig, r_eff: float) -> int:
    """Nhét lệnh vào tới khi bị từ chối — số mã tối đa là KẾT QUẢ (§6.8f)."""
    mo: list[ViTheMo] = []
    while True:
        kq = kiem_ket_nap(cfg=cfg, ung_vien=_ke_hoach(cfg, r_eff), dang_mo=mo)
        if not kq.duoc_mo:
            return len(mo)
        mo.append(ViTheMo.tu_ke_hoach(_ke_hoach(cfg, r_eff)))
        if len(mo) > 500:
            raise AssertionError("không bao giờ bị từ chối — trần không có hiệu lực")


class TestBangViDuCuaSpec:
    """§6.8f — `E_D`=500, `rho`=0,375%, `L`=3x, `daily_loss`=8%."""

    @pytest.mark.parametrize("r_eff,so_ma", [(0.009, 6), (0.015, 10), (0.020, 13), (0.030, 20)])
    def test_so_ma_toi_da_khop_bang_spec(self, r_eff: float, so_ma: int) -> None:
        assert _so_ma_toi_da(_cfg(), r_eff) == so_ma

    def test_moi_hang_LAP_DAY_cung_mot_tran_notional(self) -> None:
        """🔑 Bất biến làm lộ ra rằng `L_D_max` không phải trần độc lập — nó
        là `0.85 × L_exchange` mang tên khác (§6.8c, v6 đã xoá).

        🔴 Phát biểu ĐÚNG không phải *"mọi hàng cho cùng một tổng"*: số mã là
        số NGUYÊN nên `n × notional` không bao giờ đúng bằng trần (13 × 93,75
        = 1218,75). Con số 1250 mà spec ghi cho cả hai hàng 6 và 20 là trùng
        hợp làm tròn của riêng hai hàng đó. Bất biến thật: mọi hàng **lấp đầy
        cùng một trần 1275 tới mức không nhét thêm được một lệnh nữa**. Bản
        đầu của ca này khẳng định theo spec và đỏ — lỗi của TEST."""
        cfg = _cfg()
        tran = tinh_tran_notional_danh_muc(e_d=500.0, l_exchange=3.0)
        for r in (0.009, 0.015, 0.020, 0.030):
            moi_lenh = _ke_hoach(cfg, r).n_full_usdt
            tong = _so_ma_toi_da(cfg, r) * moi_lenh
            assert tong <= tran + 1e-6, (r, tong, tran)
            assert tong + moi_lenh > tran, (r, tong, moi_lenh, tran)  # không nhét thêm được

    def test_tran_notional_danh_muc_bang_0_85_E_D_L(self) -> None:
        assert tinh_tran_notional_danh_muc(e_d=500.0, l_exchange=3.0) == pytest.approx(1275.0)

    def test_o_3x_MARGIN_luon_siet_truoc_rui_ro(self) -> None:
        """Trần rủi ro = 40/1,875 = 21 lệnh, margin cho 6–20 ⇒ rủi ro không
        bao giờ bind ở 3x. Ghim để không ai 'dọn' điều kiện (a) cho gọn."""
        cfg = _cfg()
        for r in (0.009, 0.015, 0.020, 0.030):
            n = _so_ma_toi_da(cfg, r)
            kq = kiem_ket_nap(cfg=cfg, ung_vien=_ke_hoach(cfg, r),
                              dang_mo=[ViTheMo.tu_ke_hoach(_ke_hoach(cfg, r))] * n)
            assert kq.rang_buoc_siet == "margin", (r, n, kq.dien_giai())


class TestPhaiKiemCA_HAI:
    """🔴 Ca DUY NHẤT phân biệt được cài đặt chỉ-kiểm-margin."""

    def test_o_don_bay_cao_thi_RUI_RO_siet_truoc(self) -> None:
        cfg = _cfg(l_exchange=10.0)
        r = 0.03
        n = _so_ma_toi_da(cfg, r)
        kq = kiem_ket_nap(cfg=cfg, ung_vien=_ke_hoach(cfg, r),
                          dang_mo=[ViTheMo.tu_ke_hoach(_ke_hoach(cfg, r))] * n)
        assert kq.rang_buoc_siet == "rủi ro", kq.dien_giai()
        # và trần rủi ro = 8% × 500 / 1,875 = 21 lệnh
        assert n == 21, n

    def test_ca_hai_cung_vuot_thi_bao_ca_hai(self) -> None:
        """Báo đúng một cái sẽ khiến người đọc nới nó rồi vẫn bị chặn."""
        cfg = _cfg()
        uv = _ke_hoach(cfg, 0.03)
        # margin 500 + 31,25 > 425 VÀ rủi ro 200 + 1,875 > 40 — cả hai cùng vượt.
        kq = kiem_ket_nap(cfg=cfg, ung_vien=uv, dang_mo=[ViTheMo(200.0, 500.0)])
        assert kq.rang_buoc_siet == "cả hai", kq.dien_giai()

    def test_duoc_mo_thi_rang_buoc_siet_la_None(self) -> None:
        assert kiem_ket_nap(cfg=_cfg(), ung_vien=_ke_hoach(_cfg(), 0.02), dang_mo=[]).rang_buoc_siet is None


class TestKeHoachDayDuKhongPhaiDaKhop:
    def test_dung_planned_margin_cua_CA_BA_tranche(self) -> None:
        """`planned_margin_usdt` = `N_full / L`, không phải margin tranche 1.
        Nếu chỗ gọi đưa margin của riêng tranche đã khớp, số mã tối đa sẽ
        gấp ~3 — trần vỡ đúng lúc mọi lệnh khớp đủ."""
        cfg = _cfg()
        kh = _ke_hoach(cfg, 0.02)
        assert kh.planned_margin_usdt == pytest.approx(kh.n_full_usdt / 3.0)
        assert kh.planned_margin_usdt == pytest.approx(3 * kh.stake_tranche(1), rel=1e-3)

    def test_vi_the_am_hoac_0_thi_RAISE_khong_phai_tu_choi(self) -> None:
        for r, m in ((0.0, 10.0), (-1.0, 10.0), (10.0, 0.0), (float("nan"), 10.0)):
            with pytest.raises(AdmissionError):
                ViTheMo(r, m)


class TestNguonSuThatCuaHangSo085:
    def test_TRAN_MARGIN_bang_dung_mult_deploy_thr_trong_yaml(self) -> None:
        """🔑 §6.8f là GỐC của 0,85; `mult_deploy_thr` là bên MƯỢN
        (`frozen_rationale`: *"dùng lại hằng số ĐÃ CÓ ở §6.8f"*). Không thêm
        khoá thứ ba — ghim quan hệ thay vì nhân bản con số (MT-03)."""
        assert TRAN_MARGIN_TREN_E_D == pytest.approx(
            float(resolve(CFG_THAT, "tier_frozen.mult_deploy_thr.value"))
        )

    def test_cau_hinh_THAT_cua_project_chay_duoc(self) -> None:
        # 🔴 Ghim QUAN HỆ, không ghim con số (TD-0171): bản cũ khẳng định
        # `425.0  # 0,85 × 500` và `40.0  # 8% × 500`. Đúng lúc viết, và im
        # lặng hết đúng khi DR-D4-05 nâng `E_D` 500 → 750 — Tầng A là tầng
        # "chỉnh tự do", tức nó SẼ đổi. Con số bị ghim đúng MỘT chỗ, ở
        # `test_sizing.py::test_E_D_dang_la_con_so_DR_D4_05_da_chot`, nơi
        # dòng assert có nêu đích danh DR.
        from tool_d.config.loader import resolve

        e_d = float(resolve(CFG_THAT, "tier_a.E_D"))
        daily_loss = float(resolve(CFG_THAT, "tier_a.daily_loss_budget_pct"))
        kq = kiem_ket_nap(cfg=CFG_THAT, ung_vien=_ke_hoach(CFG_THAT, 0.02), dang_mo=[])
        assert kq.duoc_mo
        assert kq.tran_margin == pytest.approx(TRAN_MARGIN_TREN_E_D * e_d)
        assert kq.tran_rui_ro == pytest.approx(daily_loss / 100.0 * e_d)


class TestFailClosed:
    def test_E_D_hoac_daily_loss_hong_thi_raise(self) -> None:
        for kw in ({"e_d": 0.0}, {"daily_loss": 0.0}, {"daily_loss": 101.0}):
            with pytest.raises(AdmissionError):
                kiem_ket_nap(cfg=_cfg(**kw), ung_vien=_ke_hoach(_cfg(), 0.02), dang_mo=[])

    def test_tran_notional_tu_choi_dau_vao_hong(self) -> None:
        with pytest.raises(AdmissionError):
            tinh_tran_notional_danh_muc(e_d=500.0, l_exchange=0.5)

    def test_dung_bang_tran_van_DUOC_mo(self) -> None:
        """Spec viết `≤`, không phải `<`."""
        cfg = _cfg()
        uv = _ke_hoach(cfg, 0.02)
        n = int((0.85 * 500.0 - uv.planned_margin_usdt) // uv.planned_margin_usdt)
        mo = [ViTheMo.tu_ke_hoach(uv)] * n
        kq = kiem_ket_nap(cfg=cfg, ung_vien=uv, dang_mo=mo)
        assert kq.duoc_mo and kq.tong_margin_sau_khi_mo <= kq.tran_margin
