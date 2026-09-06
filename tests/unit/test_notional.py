"""TD-0082 — src/tool_d/notional.py: min notional + làm tròn lot (L-Z20)."""

from __future__ import annotations

import pytest

from tool_d.notional import SymbolFilters, build_symbol_filters, check_symbol, tranche1_notional

E_D, RHO, N_TR = 500.0, 0.375, 3  # DR-D0PRE-06, D0.4


class TestTranche1Notional:
    def test_khop_vi_du_spec_zone_rong_3pct(self) -> None:
        # §6.8f ví dụ: R_eff 3% → notional/lệnh 62,5 → tranche 1 ≈ 20,8
        assert tranche1_notional(e_d=E_D, rho_pct=RHO, r_eff=0.03, n_tranches=N_TR) == pytest.approx(20.83, abs=0.01)

    def test_zone_hep_thi_notional_lon_hon(self) -> None:
        assert tranche1_notional(e_d=E_D, rho_pct=RHO, r_eff=0.009, n_tranches=N_TR) > tranche1_notional(
            e_d=E_D, rho_pct=RHO, r_eff=0.03, n_tranches=N_TR
        )

    def test_r_eff_khong_duong_thi_raise(self) -> None:
        with pytest.raises(ValueError):
            tranche1_notional(e_d=E_D, rho_pct=RHO, r_eff=0, n_tranches=N_TR)


class TestCheckSymbol:
    def test_ma_san_5_usdt_buoc_lot_min_qua_ca_hai(self) -> None:
        f = SymbolFilters("AAAUSDT", min_notional_usdt=5.0, step_size=1.0, price=0.01)
        c = check_symbol(f, e_d=E_D, rho_pct=RHO, r_eff=0.03, n_tranches=N_TR)
        assert c.passes_min_notional and c.passes_lz20

    def test_ma_san_20_usdt_van_qua_o_e_d_500(self) -> None:
        f = SymbolFilters("BBBUSDT", min_notional_usdt=20.0, step_size=0.001, price=1.0)
        c = check_symbol(f, e_d=E_D, rho_pct=RHO, r_eff=0.03, n_tranches=N_TR)
        assert c.passes_min_notional  # 20,83 ≥ 20

    def test_ma_san_20_usdt_rot_neu_e_d_400(self) -> None:
        f = SymbolFilters("BBBUSDT", min_notional_usdt=20.0, step_size=0.001, price=1.0)
        c = check_symbol(f, e_d=400.0, rho_pct=RHO, r_eff=0.03, n_tranches=N_TR)
        assert not c.passes_min_notional

    def test_coin_gia_cao_buoc_tho_rot_lz20(self) -> None:
        # step×price = 13,4 USDT (cỡ AAVE): sai số 3×0,5×13,4×0,03 = 0,60 > 1%×1,875 = 0,01875
        f = SymbolFilters("AAVEUSDT", min_notional_usdt=5.0, step_size=0.1, price=134.0)
        c = check_symbol(f, e_d=E_D, rho_pct=RHO, r_eff=0.03, n_tranches=N_TR)
        assert c.passes_min_notional and not c.passes_lz20

    def test_dung_cong_thuc_sai_so(self) -> None:
        f = SymbolFilters("X", min_notional_usdt=5.0, step_size=0.1, price=100.0)
        c = check_symbol(f, e_d=E_D, rho_pct=RHO, r_eff=0.02, n_tranches=N_TR)
        assert c.lot_risk_error_usdt == pytest.approx(3 * 0.5 * 0.1 * 100 * 0.02)
        assert c.lot_risk_tolerance_usdt == pytest.approx(0.01 * 0.00375 * 500)


class TestBuildSymbolFilters:
    def _info(self, sym: str, mn: str = "5", step: str = "0.001") -> dict:
        return {
            "symbol": sym,
            "filters": [
                {"filterType": "MIN_NOTIONAL", "notional": mn},
                {"filterType": "LOT_SIZE", "stepSize": step, "minQty": step},
            ],
        }

    def test_chi_lay_dung_tap_symbols_va_sap_xep(self) -> None:
        info = {"symbols": [self._info("ZUSDT"), self._info("AUSDT"), self._info("OTHERUSDT")]}
        prices = [{"symbol": "ZUSDT", "price": "1"}, {"symbol": "AUSDT", "price": "2"}]
        out = build_symbol_filters(info, prices, {"ZUSDT", "AUSDT"})
        assert [f.symbol for f in out] == ["AUSDT", "ZUSDT"]
        assert out[0].price == 2.0 and out[0].min_notional_usdt == 5.0

    def test_thieu_gia_thi_raise_khong_gan_0(self) -> None:
        info = {"symbols": [self._info("AUSDT")]}
        with pytest.raises(ValueError):
            build_symbol_filters(info, [], {"AUSDT"})

    def test_thieu_ma_trong_exchange_info_thi_raise(self) -> None:
        info = {"symbols": [self._info("AUSDT")]}
        with pytest.raises(ValueError):
            build_symbol_filters(info, [{"symbol": "AUSDT", "price": "1"}], {"AUSDT", "BUSDT"})
