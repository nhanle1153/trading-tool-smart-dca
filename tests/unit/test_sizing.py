"""TD-0187 — tầng định cỡ lệnh §6.8f B1 / §6.2 (module thuần).

Test khoá đo từ backtest THẬT (tỉ trọng ⅓⅓⅓ từ `cost`, stake ∝ 1/R_eff)
nằm ở `tests/lock/test_td0187_*` cùng chiến lược `ZoneAbsorption`. File
này khoá các bất biến ĐẠI SỐ của module — thứ phải đúng trước cả khi có
backtest, và thứ backtest không kiểm được sạch (backtest cho một điểm, bất
biến là mọi điểm).

Ba bất biến đắt nhất, theo thứ tự:
1. **D0.1:** với arm rủi-ro-cố-định, `planned_risk_usdt` KHÔNG phụ thuộc
   `R_eff`. Đây là toàn bộ lý do tầng này tồn tại.
2. **§6.2 bao trùm:** không đường nào sinh `mult > 1.0` ⇒ `rho_eff ≤ rho`.
3. **stake là KÝ QUỸ:** `Σ stake_i × L_exchange == N_full`. Sai chỗ này là
   sai toàn bộ cỡ lệnh, và backtest 1x sẽ KHÔNG lộ ra (1x thì hai thứ
   trùng nhau — đúng lý do lỗi này sống được tới hôm nay).
"""

from __future__ import annotations

from types import MappingProxyType

import pytest

from tool_d.config.loader import ToolDConfig, load_tool_d_config
from tool_d.sizing import (
    SO_LENH_LIVE_TOI_THIEU_CHO_EDGE,
    HeSoMult,
    KeHoachCoLenh,
    SizingError,
    doc_trong_so_tranche,
    lap_ke_hoach_co_lenh,
    mult_corr,
    mult_dd,
    mult_deploy,
    mult_edge,
    mult_regime,
    mult_zss,
)

CFG_THAT = load_tool_d_config()
MULT_1 = HeSoMult(regime=1.0, zss=1.0, corr=1.0, dd=1.0, edge=1.0, deploy=1.0)


def _cfg(*, e_d=500.0, rho_pct=0.375, l_exchange=3.0, w=(0.3333, 0.3333, 0.3334), n_tranches=3) -> ToolDConfig:
    fz = MappingProxyType({"w_tranche": MappingProxyType({"value": tuple(w), "dof": 0})})
    return ToolDConfig(
        tier_a=MappingProxyType({"E_D": e_d, "rho_pct": rho_pct, "L_exchange": l_exchange}),
        tier_b=MappingProxyType({}),
        tier_frozen=fz,
        tier_c=MappingProxyType({"n_tranches": n_tranches}),
        raw_text="", sha256="",
    )


# ── 1. D0.1 — rủi ro cố định, không phụ thuộc R_eff ────────────────────

class TestBatBienD01:
    def test_planned_risk_KHONG_doi_khi_R_eff_gap_ba(self) -> None:
        a = lap_ke_hoach_co_lenh(cfg=_cfg(), arm="Z0", r_eff=0.01, mult=MULT_1)
        b = lap_ke_hoach_co_lenh(cfg=_cfg(), arm="Z0", r_eff=0.03, mult=MULT_1)
        assert a.planned_risk_usdt == pytest.approx(b.planned_risk_usdt, abs=1e-9)
        # và bằng đúng rho × E_D = 0.375% × 500 = 1.875 USDT (DR-D0PRE-06)
        assert a.planned_risk_usdt == pytest.approx(1.875, abs=1e-9)

    def test_zone_rong_thi_N_full_NHO_di_dung_ti_le(self) -> None:
        a = lap_ke_hoach_co_lenh(cfg=_cfg(), arm="Z0", r_eff=0.01, mult=MULT_1)
        b = lap_ke_hoach_co_lenh(cfg=_cfg(), arm="Z0", r_eff=0.03, mult=MULT_1)
        assert a.n_full_usdt == pytest.approx(3 * b.n_full_usdt)

    def test_con_so_thiet_ke_62_den_208_USDT(self) -> None:
        """DR-D4-04 §1: với R_eff 0,9%–3% thì N_full = 1,875/R_eff ≈ 62–208.
        Đây là dải MT-16 so với 39,98 USDT hằng số đã chạy."""
        cao = lap_ke_hoach_co_lenh(cfg=_cfg(), arm="Z0", r_eff=0.009, mult=MULT_1).n_full_usdt
        thap = lap_ke_hoach_co_lenh(cfg=_cfg(), arm="Z0", r_eff=0.03, mult=MULT_1).n_full_usdt
        assert cao == pytest.approx(208.33, abs=0.01)
        assert thap == pytest.approx(62.5, abs=0.01)

    def test_Z0_S1_CO_Y_pha_bat_bien_nay(self) -> None:
        """§10.1b: vốn cố định KHÔNG chia R_eff ⇒ rủi ro biến thiên. Nếu ca
        này báo 'bằng nhau' thì Z0-S1 đang chạy như Z0 — hình dạng MT-15."""
        a = lap_ke_hoach_co_lenh(cfg=_cfg(), arm="Z0-S1", r_eff=0.01, mult=MULT_1, notional_co_dinh_usdt=90.0)
        b = lap_ke_hoach_co_lenh(cfg=_cfg(), arm="Z0-S1", r_eff=0.03, mult=MULT_1, notional_co_dinh_usdt=90.0)
        assert a.n_full_usdt == b.n_full_usdt == pytest.approx(90.0)
        assert a.planned_risk_usdt == pytest.approx(0.9) and b.planned_risk_usdt == pytest.approx(2.7)


# ── 2. §6.2 bao trùm — không mult nào > 1 ──────────────────────────────

class TestRangBuocBaoTrum:
    @pytest.mark.parametrize("ten", ["regime", "zss", "corr", "dd", "edge", "deploy"])
    def test_mult_lon_hon_1_bi_tu_choi_o_cua_vao(self, ten: str) -> None:
        kw = dict(regime=1.0, zss=1.0, corr=1.0, dd=1.0, edge=1.0, deploy=1.0)
        kw[ten] = 1.0001
        with pytest.raises(SizingError, match="TRẦN"):
            HeSoMult(**kw)

    def test_mult_am_bi_tu_choi(self) -> None:
        with pytest.raises(SizingError):
            HeSoMult(regime=1.0, zss=-0.1, corr=1.0, dd=1.0, edge=1.0, deploy=1.0)

    def test_rho_eff_KHONG_BAO_GIO_vuot_rho(self) -> None:
        m = HeSoMult(regime=1.0, zss=1.0, corr=1.0, dd=1.0, edge=1.0, deploy=1.0)
        kh = lap_ke_hoach_co_lenh(cfg=_cfg(rho_pct=0.375), arm="Z0", r_eff=0.02, mult=m)
        assert kh.rho_eff_pct <= kh.rho_pct
        m2 = HeSoMult(regime=0.7, zss=0.5, corr=0.5, dd=0.5, edge=0.5, deploy=0.5)
        kh2 = lap_ke_hoach_co_lenh(cfg=_cfg(rho_pct=0.375), arm="Z0", r_eff=0.02, mult=m2)
        assert kh2.rho_eff_pct == pytest.approx(0.375 * 0.7 * 0.5**5)
        assert kh2.n_full_usdt < kh.n_full_usdt


# ── 3. stake là KÝ QUỸ ─────────────────────────────────────────────────

class TestStakeLaKyQuy:
    def test_tong_stake_nhan_L_bang_N_full(self) -> None:
        kh = lap_ke_hoach_co_lenh(cfg=_cfg(l_exchange=3.0), arm="Z0", r_eff=0.015, mult=MULT_1)
        tong_stake = sum(kh.stake_tranche(i) for i in (1, 2, 3))
        assert tong_stake * 3.0 == pytest.approx(kh.n_full_usdt, rel=1e-9)
        assert kh.planned_margin_usdt == pytest.approx(kh.n_full_usdt / 3.0)

    def test_o_1x_stake_TRUNG_notional_dung_ly_do_loi_song_duoc(self) -> None:
        """Backtest 1x không phân biệt được ký quỹ với notional — đó là lý
        do thiếu `leverage()` không bị bắt suốt từ D1. Ghim để nhớ."""
        kh = lap_ke_hoach_co_lenh(cfg=_cfg(l_exchange=1.0), arm="Z0", r_eff=0.015, mult=MULT_1)
        assert kh.stake_tranche(1) == pytest.approx(kh.notional_tranche(1))

    def test_ti_trong_doc_tu_cau_hinh_khong_hardcode_mot_phan_ba(self) -> None:
        kh = lap_ke_hoach_co_lenh(cfg=_cfg(w=(0.5, 0.3, 0.2)), arm="Z0", r_eff=0.02, mult=MULT_1)
        assert kh.w_tranche == (0.5, 0.3, 0.2)
        assert kh.notional_tranche(1) == pytest.approx(0.5 * kh.n_full_usdt)

    def test_w_tranche_THAT_trong_yaml_tong_bang_1_va_gan_mot_phan_ba(self) -> None:
        w = doc_trong_so_tranche(CFG_THAT)
        assert sum(w) == pytest.approx(1.0, abs=1e-3)
        assert all(abs(x - 1 / 3) < 1e-3 for x in w)

    def test_w_tranche_khong_tong_1_thi_raise(self) -> None:
        with pytest.raises(SizingError, match="Σ w_tranche"):
            doc_trong_so_tranche(_cfg(w=(0.3, 0.3, 0.3)))

    def test_mot_phan_tu_mot_phan_tu_mot_nua_VAN_qua_kiem_tong(self) -> None:
        """🔴 Ghim một GIỚI HẠN, không phải một tính năng: ¼-¼-½ — đúng tỉ
        trọng MT-16 đã chạy — CỘNG LẠI BẰNG 1, nên phép kiểm tổng KHÔNG bắt
        được nó. Bản đầu của test này tưởng nó bắt được và đỏ đúng chỗ đó
        (lỗi của test, không phải của module — cùng hình dạng TD-0142).
        Đây là lý do test khoá TD-0187 phải ĐO tỉ trọng từ fill của backtest
        THẬT: một cấu hình nạp được không nói gì về thứ đã chạy."""
        assert doc_trong_so_tranche(_cfg(w=(0.25, 0.25, 0.5))) == (0.25, 0.25, 0.5)

    def test_tranche_ngoai_1_3_thi_raise(self) -> None:
        kh = lap_ke_hoach_co_lenh(cfg=_cfg(), arm="Z0", r_eff=0.02, mult=MULT_1)
        with pytest.raises(SizingError):
            kh.stake_tranche(4)


# ── 4. Kế hoạch sống sót qua custom_data (đường L-Z49) ─────────────────

class TestKeHoachRoundTrip:
    def test_to_dict_from_dict_nguyen_ven(self) -> None:
        kh = lap_ke_hoach_co_lenh(cfg=_cfg(), arm="Z3b", r_eff=0.0123, mult=HeSoMult(0.7, 0.8, 0.75, 0.5, 1.0, 1.0))
        lai = KeHoachCoLenh.from_dict(kh.to_dict())
        assert lai == kh
        assert lai.mult == {"regime": 0.7, "zss": 0.8, "corr": 0.75, "dd": 0.5, "edge": 1.0, "deploy": 1.0}


# ── 5. Từng hệ số ──────────────────────────────────────────────────────

class TestMultRegime:
    K = dict(strong=1.0, weak=0.7, adx_split=25.0, adx_threshold=20.0)

    def test_manh_yeu(self) -> None:
        assert mult_regime(adx_1d=25.0, **self.K) == 1.0
        assert mult_regime(adx_1d=24.99, **self.K) == 0.7
        assert mult_regime(adx_1d=20.0, **self.K) == 0.7

    def test_ADX_duoi_nguong_vao_lenh_la_LOI_tang_tren_khong_phai_0(self) -> None:
        """Spec: 'KHÔNG có nhánh thứ ba: ADX < 20 đã bị §2.5 chặn'."""
        with pytest.raises(SizingError, match="§2.5"):
            mult_regime(adx_1d=19.9, **self.K)


class TestMultZss:
    def test_clip(self) -> None:
        assert mult_zss(0.3) == 0.5 and mult_zss(0.5) == 0.5 and mult_zss(0.8) == 0.8 and mult_zss(1.2) == 1.0


class TestMultCorr:
    def test_ba_bac(self) -> None:
        ng = (0.60, 0.85)
        assert mult_corr(corr_pool=0.0, nguong=ng) == 1.0
        assert mult_corr(corr_pool=0.60, nguong=ng) == 1.0
        assert mult_corr(corr_pool=0.61, nguong=ng) == 0.75
        assert mult_corr(corr_pool=0.86, nguong=ng) == 0.5

    def test_nguong_that_trong_yaml_dung_hinh(self) -> None:
        from tool_d.config.loader import resolve
        ng = resolve(CFG_THAT, "tier_b.mult_corr_thresholds")
        assert mult_corr(corr_pool=0.7, nguong=ng) == 0.75


class TestMultDd:
    def test_thang_ba_muc_don_vi_phan_tram(self) -> None:
        assert mult_dd(dd_pct=5.0, soft_pct=5, halt_pct=8) == 1.0
        assert mult_dd(dd_pct=5.01, soft_pct=5, halt_pct=8) == 0.5
        assert mult_dd(dd_pct=8.0, soft_pct=5, halt_pct=8) == 0.5
        assert mult_dd(dd_pct=8.01, soft_pct=5, halt_pct=8) == 0.0

    def test_HALT_thi_KHONG_duoc_hoi_co_lenh(self) -> None:
        """mult_dd = 0 là HALT, không phải size 0 (§12c.5). Hỏi cỡ lúc HALT
        rồi nhận về 0 là cách HALT biến thành 'lệnh cỡ 0' âm thầm."""
        m = HeSoMult(regime=1.0, zss=1.0, corr=1.0, dd=0.0, edge=1.0, deploy=1.0)
        assert m.la_halt
        with pytest.raises(SizingError, match="HALT"):
            lap_ke_hoach_co_lenh(cfg=_cfg(), arm="Z0", r_eff=0.02, mult=m)


class TestMultEdge:
    def test_chua_du_50_lenh_live_thi_luon_1(self) -> None:
        assert mult_edge(edge_ratio=None, so_lenh_live=0, nguong=0.5) == 1.0
        assert mult_edge(edge_ratio=None, so_lenh_live=SO_LENH_LIVE_TOI_THIEU_CHO_EDGE - 1, nguong=0.5) == 1.0

    def test_chua_du_mau_ma_truyen_edge_ratio_la_mau_thuan(self) -> None:
        with pytest.raises(SizingError, match="1774"):
            mult_edge(edge_ratio=0.3, so_lenh_live=10, nguong=0.5)

    def test_du_mau_thi_ap_nguong(self) -> None:
        assert mult_edge(edge_ratio=0.49, so_lenh_live=50, nguong=0.5) == 0.5
        assert mult_edge(edge_ratio=0.5, so_lenh_live=50, nguong=0.5) == 1.0


class TestMultDeploy:
    def test_nguong_085(self) -> None:
        assert mult_deploy(deployed_ratio=0.85, nguong=0.85) == 1.0
        assert mult_deploy(deployed_ratio=0.86, nguong=0.85) == 0.5


# ── 6. Fail-closed ở cửa ───────────────────────────────────────────────

class TestFailClosed:
    def test_R_eff_khong_duong_thi_raise(self) -> None:
        for r in (0.0, -0.01, float("nan")):
            with pytest.raises(SizingError):
                lap_ke_hoach_co_lenh(cfg=_cfg(), arm="Z0", r_eff=r, mult=MULT_1)

    def test_Z0_S1_thieu_notional_co_dinh_thi_raise_KHONG_mac_dinh(self) -> None:
        from tool_d.arm_switches import ArmSwitchError
        with pytest.raises(ArmSwitchError, match="notional_co_dinh_usdt"):
            lap_ke_hoach_co_lenh(cfg=_cfg(), arm="Z0-S1", r_eff=0.02, mult=MULT_1)

    def test_arm_rui_ro_co_dinh_ma_truyen_notional_co_dinh_thi_raise(self) -> None:
        from tool_d.arm_switches import ArmSwitchError
        with pytest.raises(ArmSwitchError):
            lap_ke_hoach_co_lenh(cfg=_cfg(), arm="Z0", r_eff=0.02, mult=MULT_1, notional_co_dinh_usdt=50.0)

    def test_doc_cau_hinh_THAT_cua_project_dung_duoc(self) -> None:
        """Đường sản xuất thật: E_D/rho/L_exchange/w_tranche từ YAML thật.

        🔴 Ghim QUAN HỆ, không ghim con số (TD-0171): bản cũ khẳng định
        `planned_risk == 1.875`, đúng vì `E_D` khi đó là 500. Một con số
        tuyệt đối như thế **im lặng hết đúng** khi Tầng A đổi — mà Tầng A
        là tầng *"chỉnh tự do"*, tức nó SẼ đổi. Ca này nay đòi
        `planned_risk == rho × E_D` đọc thẳng từ YAML; nó đúng ở mọi `E_D`
        và vẫn bắt được lỗi thật vì `lap_ke_hoach_co_lenh` đi qua đường
        khác hẳn (arm_switches → tranche1_notional → ×n → ×r_eff).
        """
        from tool_d.config.loader import resolve

        e_d = float(resolve(CFG_THAT, "tier_a.E_D"))
        rho = float(resolve(CFG_THAT, "tier_a.rho_pct"))
        kh = lap_ke_hoach_co_lenh(cfg=CFG_THAT, arm="Z0", r_eff=0.02, mult=MULT_1)
        assert kh.l_exchange == 3.0 and kh.rho_pct == rho
        assert kh.planned_risk_usdt == pytest.approx(rho / 100.0 * e_d, abs=1e-9)

    def test_E_D_dang_la_con_so_DR_D4_05_da_chot(self) -> None:
        """Ghim QUYẾT ĐỊNH, tách khỏi ca ghim quan hệ ở trên.

        Ca trên cố ý đúng ở mọi `E_D`, nên một mình nó thì `E_D` đổi lặng
        lẽ cũng không ai biết. Ca này là chỗ con số bị ghim — và nó nêu
        đích danh DR, nên đổi `E_D` buộc phải sửa một dòng có nhắc tới
        quyết định, thay vì sửa một hằng số vô danh."""
        from tool_d.config.loader import resolve

        assert float(resolve(CFG_THAT, "tier_a.E_D")) == 750.0, (
            "E_D khác 750 — DR-D4-05 §2.2 chốt 750 (nâng từ 500). Đổi số này "
            "cần một DR mới, không phải sửa test cho khớp."
        )
