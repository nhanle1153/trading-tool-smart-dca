"""TD-0171 (mở lại TD-0082) — sàn min-notional THẬT vs công thức cỡ lệnh THẬT.

Bảng `docs/min-notional-check.md` kết luận *"102/102 qua"* bằng hai giả định
mà TD-0187 đã làm sai cả hai:

1. **Tử số:** dùng `rho` thô. Cỡ lệnh thật là `rho_eff = rho × Π mult_*`
   với **mọi `mult_* ≤ 1.0`** (§6.2, `HeSoMult` từ chối > 1.0) ⇒ notional
   thật ≤ notional đã kiểm. Bảng cũ lệch đúng chiều tâng kết quả lên.
2. **Mẫu số:** so với `MIN_NOTIONAL.notional` trần trụi. Freqtrade so với
   `max(cost_min × stoploss_reserve, amount_min × price × margin_reserve)`
   (`exchange.py:_get_stake_amount_limit`) — CAO HƠN, và có thêm một vế
   (`LOT_SIZE.minQty`) mà `build_symbol_filters()` chưa từng đọc.

🔴 Vế *"chưa chia đòn bẩy"* của ghi chú MT-16 là SAI, xem
`test_don_bay_khong_co_mat_va_do_la_co_y`.
"""

from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path

import pytest

from tool_d.notional import (
    SymbolFilters,
    check_symbol,
    san_min_notional_freqtrade,
)

E_D, RHO, N_TR = 500.0, 0.375, 3  # DR-D0PRE-06, D0.4
STOPLOSS_CONFIG = -0.99  # config/freqtrade/config.json:37 — "lưới cuối" §0c.3


def _mult_grid() -> list[tuple[str, float]]:
    """`entrypoints/` không nằm trên pythonpath (L-Z36 khoá đúng 8 file) —
    nạp theo đường dẫn thay vì `import`."""
    duong_dan = Path(__file__).resolve().parents[2] / "entrypoints" / "build_pool.py"
    spec = importlib.util.spec_from_file_location("build_pool_td0171", duong_dan)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return list(mod.MULT_GRID)


def _f(**kw) -> SymbolFilters:
    d = dict(symbol="XUSDT", min_notional_usdt=5.0, step_size=0.001, min_qty=0.001, price=1.0)
    d.update(kw)
    return SymbolFilters(**d)


class TestSanThatCuaFreqtrade:
    def test_stoploss_099_lam_he_so_du_tru_cham_tran_1_5(self) -> None:
        # (1+0.05)/(1-0.99) = 105 → bị kẹp về trần 1.5 ⇒ sàn 5 → 7,5
        assert san_min_notional_freqtrade(_f(), stoploss=STOPLOSS_CONFIG) == pytest.approx(7.5)

    def test_tran_1_5_khong_phai_hang_so_hardcode(self) -> None:
        # SL hẹp → hệ số 1.05/0.99 ≈ 1.0606, KHÔNG phải 1.5. Ca này bắt bản
        # cài đặt nhân bừa 1.5 cho mọi trường hợp.
        assert san_min_notional_freqtrade(_f(), stoploss=-0.01) == pytest.approx(5 * 1.05 / 0.99)

    def test_ve_min_qty_thang_khi_lot_tho(self) -> None:
        # minQty 0,001 × giá 100.000 × 1,05 = 105 USDT ≫ 5 × 1,5 = 7,5.
        # Vế này `build_symbol_filters()` cũ KHÔNG đọc ⇒ sàn bị khai thiếu 14 lần.
        f = _f(min_qty=0.001, price=100_000.0)
        assert san_min_notional_freqtrade(f, stoploss=STOPLOSS_CONFIG) == pytest.approx(105.0)

    def test_lay_ve_LON_hon_chu_khong_phai_ve_dau_tien(self) -> None:
        cao = _f(min_notional_usdt=100.0, min_qty=0.001, price=1.0)
        assert san_min_notional_freqtrade(cao, stoploss=STOPLOSS_CONFIG) == pytest.approx(150.0)


class TestMultLamNhoNotional:
    def test_khai_mult_product_la_BAT_BUOC(self) -> None:
        # Không mặc định: mặc định 1.0 là cách bảng cũ nói dối mà không ai
        # gõ một con số sai nào (cùng chốt với ngưỡng DG5, DR-D4-02).
        with pytest.raises(TypeError):
            check_symbol(  # type: ignore[call-arg]
                _f(), e_d=E_D, rho_pct=RHO, r_eff=0.03, n_tranches=N_TR,
                stoploss=STOPLOSS_CONFIG,
            )

    def test_mult_nho_hon_1_lam_tranche1_nho_di_dung_ti_le(self) -> None:
        chung = dict(e_d=E_D, rho_pct=RHO, r_eff=0.03, n_tranches=N_TR, stoploss=STOPLOSS_CONFIG)
        day_du = check_symbol(_f(), mult_product=1.0, **chung)
        thuc_te = check_symbol(_f(), mult_product=0.62, **chung)
        assert thuc_te.tranche1_notional_usdt == pytest.approx(
            day_du.tranche1_notional_usdt * 0.62
        )

    def test_mult_product_ngoai_khoang_0_1_thi_raise(self) -> None:
        # §6.2: rho là TRẦN. Π mult_* > 1 là tầng trên đã hỏng, không phải
        # một cỡ lệnh to hơn.
        with pytest.raises(ValueError):
            check_symbol(
                _f(), mult_product=1.2, e_d=E_D, rho_pct=RHO, r_eff=0.03,
                n_tranches=N_TR, stoploss=STOPLOSS_CONFIG,
            )


class TestLatKetLuanCu:
    def test_ma_san_20_usdt_QUA_o_bang_cu_nhung_ROT_o_san_that(self) -> None:
        # Đây là ca lật kết luận "102/102 qua". Bảng cũ: 20,83 ≥ 20 → QUA.
        # Sàn thật: 20 × 1,5 = 30 > 20,83 → RỚT, ngay cả khi Π mult_* = 1.
        f = _f(min_notional_usdt=20.0, min_qty=0.001, price=1.0)
        c = check_symbol(
            f, mult_product=1.0, e_d=E_D, rho_pct=RHO, r_eff=0.03, n_tranches=N_TR,
            stoploss=STOPLOSS_CONFIG,
        )
        assert c.tranche1_notional_usdt == pytest.approx(20.83, abs=0.01)
        assert c.san_usdt == pytest.approx(30.0)
        assert not c.passes_min_notional

    def test_mult_thuc_te_lam_ma_san_5_usdt_cung_rot(self) -> None:
        # Π mult_* = 0,7 × 0,62 = 0,434 (regime weak × ZSS sát ngưỡng) →
        # 20,83 × 0,434 = 9,04 ... vẫn qua 7,5. Hạ thêm một bậc corr (0,75)
        # → 6,78 < 7,5 ⇒ RỚT. Mã sàn 5 USDT không còn là "luôn an toàn".
        c = check_symbol(
            _f(), mult_product=0.7 * 0.62 * 0.75, e_d=E_D, rho_pct=RHO, r_eff=0.03,
            n_tranches=N_TR, stoploss=STOPLOSS_CONFIG,
        )
        assert c.tranche1_notional_usdt < c.san_usdt
        assert not c.passes_min_notional


class TestDonBayCoYVangMat:
    def test_don_bay_khong_co_mat_va_do_la_co_y(self) -> None:
        """🔴 Ghim một điều ĐÃ ĐO, không phải một điều đã suy luận.

        `exchange.py:_get_stake_amount_limit` trả sàn rồi gọi
        `_get_stake_amount_considering_leverage(...)` = `/ leverage`; còn
        `stake` mà chiến lược trả cũng là `notional / L` (`sizing.py:
        stake_tranche`). Đòn bẩy chia CẢ HAI VẾ ⇒ triệt tiêu khỏi phép so.

        Nên `check_symbol` KHÔNG nhận đòn bẩy. Thêm nó vào là mời một phép
        nhân/chia thứ hai vào đúng chỗ vừa chứng minh là không có tác dụng —
        và một sàn bị chia 3 lần nữa thì mọi mã đều "qua".
        """
        assert "leverage" not in inspect.signature(check_symbol).parameters
        assert "l_exchange" not in inspect.signature(check_symbol).parameters
        assert "leverage" not in inspect.signature(san_min_notional_freqtrade).parameters


class TestDaiMultCuaBangDoiChieu:
    """Dải `Π mult_*` mà bảng đối chiếu quét. Ghim vào ĐỊNH NGHĨA §6.2 chứ
    không để là mấy con số gõ tay: một điểm lưới sai thì bảng vẫn in ra đẹp
    đẽ và không ai biết mình đang đọc ca nào."""

    def test_moi_diem_luoi_nam_trong_khoang_hop_le(self) -> None:
        MULT_GRID = _mult_grid()

        assert MULT_GRID, "dải rỗng thì bảng không nói gì"
        for ten, gt in MULT_GRID:
            assert 0 < gt <= 1.0, f"{ten}: {gt} ngoài (0,1] — §6.2 rho là TRẦN"

    def test_diem_xau_nhat_dung_bang_tich_sau_he_so_xau_nhat(self) -> None:
        MULT_GRID = _mult_grid()

        # §6.2: regime weak 0,7 · ZSS sàn 0,5 · corr cao 0,5 · dd soft 0,5 ·
        # edge 1,0 (backtest, spec dòng 1774) · deploy quá 0,85 → 0,5.
        xau_nhat = 0.7 * 0.5 * 0.5 * 0.5 * 1.0 * 0.5
        assert min(gt for _, gt in MULT_GRID) == pytest.approx(xau_nhat)

    def test_luoi_co_diem_1_0_de_doi_chieu_duoc_voi_bang_cu(self) -> None:
        MULT_GRID = _mult_grid()

        assert any(gt == 1.0 for _, gt in MULT_GRID)


class TestSauDuongChayBonSan:
    """🔴 Đo 09/09/2026: Freqtrade KHÔNG dùng `stoploss` của config cho mọi
    phép kiểm sàn. Nó truyền một hằng số KHÁC NHAU theo từng đường chạy, và
    **backtest với live không dùng cùng một sàn** — một cấu hình qua sàn ở
    D4 (backtest) vẫn có thể rớt sàn ở D11/D12 (live), im lặng.

    Bằng chứng (đọc trong image):
      backtesting.py:1087  vào lệnh          → -0.05  (pos_adjust → 0.0)
      backtesting.py:723   phần dư sau TP    → -0.1, KHÔNG truyền leverage
      freqtradebot.py:1185 vào lệnh live     → strategy.stoploss
      freqtradebot.py:846  phần dư live      → strategy.stoploss
    """

    def test_sau_duong_chay_deu_co_ten_va_gia_tri(self) -> None:
        from tool_d.notional import sl_hieu_dung

        assert sl_hieu_dung("backtest_vao_lenh", strategy_stoploss=-0.99) == -0.05
        assert sl_hieu_dung("backtest_tranche_2_3", strategy_stoploss=-0.99) == 0.0
        assert sl_hieu_dung("backtest_phan_du", strategy_stoploss=-0.99) == -0.1
        assert sl_hieu_dung("live_vao_lenh", strategy_stoploss=-0.99) == -0.99
        assert sl_hieu_dung("live_tranche_2_3", strategy_stoploss=-0.99) == 0.0
        assert sl_hieu_dung("live_phan_du", strategy_stoploss=-0.99) == -0.99

    def test_duong_chay_la_khong_biet_thi_raise(self) -> None:
        from tool_d.notional import sl_hieu_dung

        with pytest.raises(ValueError):
            sl_hieu_dung("backtest", strategy_stoploss=-0.99)

    def test_backtest_va_live_KHAC_san_o_cung_mot_ma(self) -> None:
        """Ca chính: sàn backtest THẤP HƠN sàn live ⇒ D4 dễ hơn D11."""
        from tool_d.notional import sl_hieu_dung

        f = _f()
        san_bt = san_min_notional_freqtrade(
            f, stoploss=sl_hieu_dung("backtest_vao_lenh", strategy_stoploss=-0.99)
        )
        san_live = san_min_notional_freqtrade(
            f, stoploss=sl_hieu_dung("live_vao_lenh", strategy_stoploss=-0.99)
        )
        assert san_bt == pytest.approx(5.0 * 1.05 / 0.95)
        assert san_live == pytest.approx(7.5)
        assert san_bt < san_live
