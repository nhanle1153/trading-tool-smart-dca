"""TD-0083 — src/tool_d/pool.py: logic thuần chọn pool + tập EXPLORE."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from tool_d.pool import (
    EXCLUDE_FROM_TRADING,
    SymbolStat,
    build_symbol_stats,
    compute_pool,
    pairlist_over_time,
    pairlist_point_in_time,
)

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


T_PAST = datetime(2025, 9, 6, tzinfo=timezone.utc)  # "1 năm trước" so với NOW


class TestPairlistPointInTime:
    """TD-0096, H1-D — pool hợp lệ tại quá khứ `t`, không lệch sống sót."""

    def test_ma_niem_yet_sau_t_khong_co_mat(self) -> None:
        stats = [
            SymbolStat(symbol="OLDUSDT", onboard_date=T_PAST - timedelta(days=400), quote_volume_24h=20_000_000),
            SymbolStat(symbol="FUTUREUSDT", onboard_date=T_PAST + timedelta(days=10), quote_volume_24h=100_000_000),
        ]
        result = pairlist_point_in_time(stats, t=T_PAST, age_floor_days=180, volume_floor_usdt=15_000_000)
        assert result.trading == ("OLDUSDT",)
        assert "FUTUREUSDT" not in result.trading and "FUTUREUSDT" not in result.explore

    def test_ma_da_huy_niem_yet_truoc_t_khong_co_mat(self) -> None:
        stats = [
            SymbolStat(
                symbol="DEADUSDT",
                onboard_date=T_PAST - timedelta(days=400),
                quote_volume_24h=20_000_000,
                delisted_at=T_PAST - timedelta(days=1),  # huỷ NGAY TRƯỚC t
            ),
        ]
        result = pairlist_point_in_time(stats, t=T_PAST, age_floor_days=180, volume_floor_usdt=15_000_000)
        assert result.trading == () and result.explore == ()  # không tồn tại, không phải "trượt tiêu chí"

    def test_ma_huy_niem_yet_sau_t_van_co_mat(self) -> None:
        stats = [
            SymbolStat(
                symbol="SOONDEADUSDT",
                onboard_date=T_PAST - timedelta(days=400),
                quote_volume_24h=20_000_000,
                delisted_at=T_PAST + timedelta(days=30),  # huỷ SAU t -> vẫn đang sống tại t
            ),
        ]
        result = pairlist_point_in_time(stats, t=T_PAST, age_floor_days=180, volume_floor_usdt=15_000_000)
        assert result.trading == ("SOONDEADUSDT",)

    def test_ket_qua_khong_doi_khi_them_du_lieu_sau_t(self) -> None:
        base_stats = [
            SymbolStat(symbol="AAAUSDT", onboard_date=T_PAST - timedelta(days=400), quote_volume_24h=20_000_000),
        ]
        # "Dữ liệu sau t" xuất hiện thêm: một mã mới lên sàn sau t, và một mã bị huỷ sau t.
        extra_stats = base_stats + [
            SymbolStat(symbol="LATERUSDT", onboard_date=T_PAST + timedelta(days=5), quote_volume_24h=999_999_999),
            SymbolStat(
                symbol="AAAUSDT2",
                onboard_date=T_PAST - timedelta(days=400),
                quote_volume_24h=20_000_000,
                delisted_at=T_PAST + timedelta(days=200),
            ),
        ]
        r1 = pairlist_point_in_time(base_stats, t=T_PAST, age_floor_days=180, volume_floor_usdt=15_000_000)
        r2 = pairlist_point_in_time(extra_stats, t=T_PAST, age_floor_days=180, volume_floor_usdt=15_000_000)
        assert r1.trading == ("AAAUSDT",)
        # Thêm mã mới (chưa đủ tuổi tại t) và mã sẽ-huỷ-sau-t (còn sống tại t, thoả tiêu chí)
        # -> AAAUSDT2 hợp lệ và được thêm vào, nhưng AAAUSDT không đổi kết quả của chính nó.
        assert "AAAUSDT" in r2.trading
        assert "LATERUSDT" not in r2.trading and "LATERUSDT" not in r2.explore

    def test_volume_va_tuoi_van_ap_dung_binh_thuong_tai_t(self) -> None:
        stats = [
            SymbolStat(symbol="THINUSDT", onboard_date=T_PAST - timedelta(days=400), quote_volume_24h=500_000),
        ]
        result = pairlist_point_in_time(stats, t=T_PAST, age_floor_days=180, volume_floor_usdt=15_000_000)
        assert result.trading == () and result.explore == ("THINUSDT",)

    def test_btc_eth_van_luon_explore_tai_qua_khu(self) -> None:
        stats = [
            SymbolStat(symbol="BTCUSDT", onboard_date=T_PAST - timedelta(days=2000), quote_volume_24h=1_000_000_000),
        ]
        result = pairlist_point_in_time(stats, t=T_PAST, age_floor_days=180, volume_floor_usdt=15_000_000)
        assert result.trading == () and result.explore == ("BTCUSDT",)


T0, T1, T2 = (
    T_PAST,
    T_PAST + timedelta(days=90),
    T_PAST + timedelta(days=180),
)


def _flaky(volume_at_t0, volume_at_t1, volume_at_t2, onboard=T_PAST - timedelta(days=400)):
    return {
        T0: [SymbolStat(symbol="FLAKYUSDT", onboard_date=onboard, quote_volume_24h=volume_at_t0)],
        T1: [SymbolStat(symbol="FLAKYUSDT", onboard_date=onboard, quote_volume_24h=volume_at_t1)],
        T2: [SymbolStat(symbol="FLAKYUSDT", onboard_date=onboard, quote_volume_24h=volume_at_t2)],
    }


class TestPairlistOverTime:
    """TD-0097, §9c.4b(b) — EXPLORE là VĨNH VIỄN, không được quay lại trading."""

    def test_ma_bi_explore_hoa_khong_bao_gio_quay_lai_trading(self) -> None:
        # Đủ volume ở T0 (trading) -> tụt volume ở T1 (explore) -> hồi phục ở T2.
        # Không có cưỡng chế thì T2 sẽ lại là "trading" — spec cấm tuyệt đối điều đó.
        stats_by_t = _flaky(volume_at_t0=20_000_000, volume_at_t1=1_000_000, volume_at_t2=50_000_000)
        results = pairlist_over_time(stats_by_t, age_floor_days=180, volume_floor_usdt=15_000_000)
        assert results[T0].trading == ("FLAKYUSDT",)
        assert results[T1].trading == () and results[T1].explore == ("FLAKYUSDT",)
        assert results[T2].trading == (), "hồi phục volume KHÔNG được đưa mã trở lại trading"
        assert results[T2].explore == ("FLAKYUSDT",)

    def test_ma_moi_thoa_tieu_chi_ngay_lan_dau_van_vao_trading(self) -> None:
        # Mã CHƯA từng bị explore-hoá -> lần đầu thoả tiêu chí thì vào trading bình thường.
        stats_by_t = {
            T0: [],
            T1: [SymbolStat(symbol="NEWUSDT", onboard_date=T1 - timedelta(days=200), quote_volume_24h=20_000_000)],
        }
        results = pairlist_over_time(stats_by_t, age_floor_days=180, volume_floor_usdt=15_000_000)
        assert results[T1].trading == ("NEWUSDT",)

    def test_btc_eth_explore_moi_moc(self) -> None:
        stats_by_t = {
            T0: [SymbolStat(symbol="BTCUSDT", onboard_date=T_PAST - timedelta(days=2000), quote_volume_24h=1e9)],
            T1: [SymbolStat(symbol="BTCUSDT", onboard_date=T_PAST - timedelta(days=2000), quote_volume_24h=1e9)],
        }
        results = pairlist_over_time(stats_by_t, age_floor_days=180, volume_floor_usdt=15_000_000)
        assert all("BTCUSDT" not in r.trading and "BTCUSDT" in r.explore for r in results.values())

    def test_khong_phu_thuoc_thu_tu_truyen_vao_checkpoint(self) -> None:
        # Dict truyền vào không sắp xếp -> hàm phải tự sắp theo t, không theo thứ tự khai báo.
        stats_by_t = _flaky(volume_at_t0=20_000_000, volume_at_t1=1_000_000, volume_at_t2=50_000_000)
        shuffled = {T2: stats_by_t[T2], T0: stats_by_t[T0], T1: stats_by_t[T1]}
        results = pairlist_over_time(shuffled, age_floor_days=180, volume_floor_usdt=15_000_000)
        assert results[T2].trading == ()
