"""TD-0083 — src/tool_d/pool.py: logic thuần chọn pool + tập EXPLORE."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from tool_d.pool import EXCLUDE_FROM_TRADING, build_symbol_stats, compute_pool

NOW = datetime(2026, 9, 6, tzinfo=timezone.utc)


def _exchange_info(symbols: list[dict]) -> dict:
    return {"symbols": symbols}


def _symbol(symbol: str, *, days_old: int, contract_type="PERPETUAL", quote="USDT", status="TRADING") -> dict:
    onboard = NOW - timedelta(days=days_old)
    return {
        "symbol": symbol,
        "contractType": contract_type,
        "quoteAsset": quote,
        "status": status,
        "onboardDate": int(onboard.timestamp() * 1000),
    }


def _ticker(symbol: str, volume: float) -> dict:
    return {"symbol": symbol, "quoteVolume": str(volume)}


class TestBuildSymbolStats:
    def test_loc_dung_perpetual_usdt_trading(self) -> None:
        info = _exchange_info([
            _symbol("BTCUSDT", days_old=2000),
            _symbol("BTCUSD_PERP", days_old=2000, quote="USD"),  # coin-margined, loại
            _symbol("BTCUSDT_240927", days_old=100, contract_type="CURRENT_QUARTER"),  # loại
            _symbol("DELISTEDUSDT", days_old=500, status="SETTLING"),  # loại
        ])
        tickers = [_ticker("BTCUSDT", 100.0)]
        stats = build_symbol_stats(info, tickers)
        assert [s.symbol for s in stats] == ["BTCUSDT"]

    def test_thieu_ticker_thi_volume_0(self) -> None:
        info = _exchange_info([_symbol("XUSDT", days_old=500)])
        stats = build_symbol_stats(info, [])
        assert stats[0].quote_volume_24h == 0.0


class TestComputePool:
    def test_btc_eth_luon_vao_explore_du_thoa_tieu_chi(self) -> None:
        stats = build_symbol_stats(
            _exchange_info([_symbol("BTCUSDT", days_old=2000), _symbol("ETHUSDT", days_old=2000)]),
            [_ticker("BTCUSDT", 1_000_000_000), _ticker("ETHUSDT", 900_000_000)],
        )
        result = compute_pool(stats, age_floor_days=180, volume_floor_usdt=15_000_000, now=NOW)
        assert result.trading == ()
        assert set(result.explore) == {"BTCUSDT", "ETHUSDT"}

    def test_thoa_ca_hai_tieu_chi_thi_vao_trading(self) -> None:
        stats = build_symbol_stats(
            _exchange_info([_symbol("AAAUSDT", days_old=200)]),
            [_ticker("AAAUSDT", 20_000_000)],
        )
        result = compute_pool(stats, age_floor_days=180, volume_floor_usdt=15_000_000, now=NOW)
        assert result.trading == ("AAAUSDT",)
        assert result.explore == ()

    def test_qua_tre_thi_vao_explore(self) -> None:
        stats = build_symbol_stats(
            _exchange_info([_symbol("NEWUSDT", days_old=30)]),
            [_ticker("NEWUSDT", 100_000_000)],  # volume cao nhưng qua tre
        )
        result = compute_pool(stats, age_floor_days=180, volume_floor_usdt=15_000_000, now=NOW)
        assert result.trading == ()
        assert result.explore == ("NEWUSDT",)

    def test_volume_thap_thi_vao_explore(self) -> None:
        stats = build_symbol_stats(
            _exchange_info([_symbol("THINUSDT", days_old=1000)]),
            [_ticker("THINUSDT", 500_000)],  # du tuoi nhung volume thap
        )
        result = compute_pool(stats, age_floor_days=180, volume_floor_usdt=15_000_000, now=NOW)
        assert result.trading == ()
        assert result.explore == ("THINUSDT",)

    def test_ket_qua_sap_xep_va_khong_trung(self) -> None:
        stats = build_symbol_stats(
            _exchange_info([_symbol("ZUSDT", days_old=200), _symbol("AUSDT", days_old=200)]),
            [_ticker("ZUSDT", 20_000_000), _ticker("AUSDT", 20_000_000)],
        )
        result = compute_pool(stats, age_floor_days=180, volume_floor_usdt=15_000_000, now=NOW)
        assert result.trading == ("AUSDT", "ZUSDT")  # đã sắp xếp

    def test_exclude_from_trading_dung_dung_hai_ma(self) -> None:
        assert EXCLUDE_FROM_TRADING == frozenset({"BTCUSDT", "ETHUSDT"})
