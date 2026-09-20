"""🔴 TD-0321 (DR-SHORT-01, D-dựng, 0 trial) — đường SHORT của `ZoneAbsorption`
chạy trên backtest Freqtrade THẬT, với dữ liệu TỔNG HỢP lật gương.

Phạm vi nói thẳng: đây là bằng chứng rằng đường Short được DỰNG đúng và nối
đủ (tín hiệu → định cỡ → kết nạp → ba tranche DCA-lên → TP1/TP2 → SL), KHÔNG
phải bằng chứng về lợi thế của Short. Không một con số nào ở đây đo trên dữ
liệu thị trường — chỉ chuỗi giá tổng hợp — nên không phải "chạm" theo
`DR-014` §2 và không tiêu suất trial nào. Khâu ĐO Short vẫn ⏸ theo
`DR-HUONG-01` §3 + `DR-D4-01` §2b, và `tier_a.enable_short` trong YAML THẬT
vẫn `false` (ca `TestCongTacTat` ghim điều đó).

════ Vì sao gương qua K = 190, không phải K tuỳ ý ════

Bộ sinh của `test_td0187` neo mọi thứ quanh giá ~95 (zone đáy ở 95, vào
lệnh ở ~95). Lật `x → K − x` với K bất kỳ vẫn cho một chuỗi hợp lệ, nhưng
`R_eff` là TỈ LỆ `(sl − p_avg) / p_avg` chứ không phải khoảng giá: lật quanh
K = 120 đặt zone ở ~25 nên cùng một khoảng ATR chia cho 25 thay vì 95 ⇒
`R_eff` phình ~4 lần ⇒ `N_full = rho_eff × E_D / R_eff` co ~4 lần ⇒ tranche 1
chỉ 17,9 USDT, dưới sàn 30 USDT của LTC (`SAN_TOOL_D TU_CHOI`) ⇒ 0 lệnh. Đó là
lỗi của FIXTURE (đo được lúc dựng file này), không phải của chiến lược. K =
190 = 2 × 95 lật QUA ĐÚNG mức vào lệnh nên hình học quanh zone giữ nguyên
và cỡ lệnh (69 USDT/tranche) qua sàn như bản Long.

════ Hai lỗi thật mà chính file test này bắt được khi dựng ════

1. Freqtrade gán `enter_tag = ""` cho cả cột TRƯỚC khi gọi `populate_entry_
   trend` (`advise_entry`, `interface.py:1856`). Bản đầu chỉ ghi tag Short khi
   ô `isna()` nên KHÔNG BAO GIỜ ghi ⇒ mọi lệnh Short vào với tag rỗng ⇒
   `custom_stake_amount` raise ⇒ `strategy_safe_wrapper` NUỐT ⇒ 0 lệnh, rc = 0.
   Phép thử trên dataframe TỰ DỰNG không thấy vì nó không đi qua `advise_entry`
   — `TestTagGhiKhiCotDaDatChuoiRong` mô phỏng đúng bước đó.
2. Xem đoạn trên về K.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import talib

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

# ── tái dùng bộ sinh nến của TD-0187 (`tests/` không phải package) ─────────
_spec = importlib.util.spec_from_file_location(
    "td0187", REPO_ROOT / "tests" / "lock" / "test_td0187_dinh_co_lenh_backtest_that.py"
)
_td0187 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_td0187)  # type: ignore[union-attr]

CAP = _td0187.CAP
TIMERANGE = _td0187.TIMERANGE
PAIR = CAP.replace("_USDT_USDT", "/USDT:USDT")
K_GUONG = 190.0  # xem docstring module: 2 × 95, KHÔNG phải số tuỳ ý
TY_LE_CHOT_TP1 = 0.5


def _guong(rows: list[tuple]) -> list[tuple]:
    """Lật nến OHLCV qua `K_GUONG`: `high' = K − low`, `low' = K − high`."""
    return [(K_GUONG - o, K_GUONG - l, K_GUONG - h, K_GUONG - c, v) for (o, h, l, c, v) in rows]


def _rows4_guong() -> list[tuple]:
    return _guong(_td0187._bars_4h_co_trend())


def _rows1_guong() -> list[tuple]:
    # Lật KẾT QUẢ 1H của bản Long (gồm cả bốn nến 1H "chạm p1" đặc biệt) thay vì
    # dựng lại từ 4H đã lật — để hình dạng nến xác nhận §3.3b được lật NGUYÊN VẸN.
    return _guong(_td0187._rows1_tu_rows4(_td0187._bars_4h_co_trend()))


def _khung_1h_4h() -> tuple[pd.DataFrame, pd.DataFrame]:
    rows1 = _rows1_guong()
    bat_dau = _td0187._moc_bat_dau(len(rows1))
    df1 = pd.DataFrame(rows1, columns=["open", "high", "low", "close", "volume"])
    df1.insert(0, "date", pd.date_range(bat_dau, periods=len(rows1), freq="1h", tz="UTC"))
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    df4 = df1.set_index("date").resample("4h").agg(agg).reset_index()
    return df1, df4


# ── nạp chiến lược THẬT (không mock) ──────────────────────────────────────
def _chien_luoc(**thuoc_tinh):
    spec = importlib.util.spec_from_file_location(
        "ZoneAbsorptionTD0321", REPO_ROOT / "user_data" / "strategies" / "ZoneAbsorption.py"
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)  # type: ignore[union-attr]
    s = m.ZoneAbsorption(config={"stake_currency": "USDT", "exchange": {"name": "binance"}})
    for k, v in thuoc_tinh.items():
        setattr(s, k, v)
    return s


def _cot_1h(df1: pd.DataFrame) -> pd.DataFrame:
    d = df1.copy()
    d["atr_1h"] = talib.ATR(d["high"], d["low"], d["close"], timeperiod=14)
    d["rsi_1h"] = talib.RSI(d["close"], timeperiod=14)
    d["volume_ma_1h"] = d["volume"].rolling(20).mean()
    return d


def _dataframe_san_sang_vao_lenh(s, df1: pd.DataFrame, df4: pd.DataFrame) -> pd.DataFrame:
    """Đúng chuỗi bước mà `populate_indicators` chạy trước `populate_entry_trend`."""
    from freqtrade.strategy import merge_informative_pair

    d = _cot_1h(df1)
    inf4 = s._tinh_zone_4h(df4.copy())
    s._xac_nhan_3_3b(d, inf4, PAIR)
    s._xac_nhan_3_3b_short(d, inf4, PAIR)
    d = merge_informative_pair(d, inf4, "1h", "4h", ffill=True)
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    df1d = df1.set_index("date").resample("1D").agg(agg).reset_index()
    inf1d = s._tinh_trend_1d(df1d)
    return merge_informative_pair(
        d, inf1d[["date", "adx", "trend_dir_1d", "tuoi_trend_1d"]], "1h", "1d", ffill=True
    )


# ═══════════════════════════════════════════════════════════════════════════
class TestBoSinhGuongKhongPassRong:
    """Đối chứng thường trực: bộ sinh lật gương phải CÓ thứ để đo — nếu không,
    mọi khẳng định về lệnh Short phía dưới xanh-vô-nghĩa (bài học TD-0182/0194)."""

    def test_co_zone_dinh_de_vao_lenh_va_zone_day_lam_dich_TP(self) -> None:
        rows4 = _rows4_guong()
        assert _td0187._dem_zone(rows4, "dinh") >= 1, "không có zone ĐỈNH để vào lệnh Short"
        assert _td0187._dem_zone(rows4, "day") >= 1, "không có zone ĐÁY làm đích TP1 của Short"

    def test_xac_nhan_3_3b_short_co_it_nhat_mot_tin_hieu(self) -> None:
        df1, df4 = _khung_1h_4h()
        s = _chien_luoc()
        d = _cot_1h(df1)
        inf4 = s._tinh_zone_4h(df4.copy())
        assert inf4["zone_valid_short"].any(), "không zone đỉnh nào hợp lệ trong `_tinh_zone_4h`"
        s._xac_nhan_3_3b_short(d, inf4, PAIR)
        assert d["xac_nhan_3_3b_short"].any(), "không nến xác nhận §3.3b nào cho Short"


# ═══════════════════════════════════════════════════════════════════════════
class TestPopulateEntryTrendShort:
    def test_enable_short_true_sinh_enter_short_voi_tag_huong_s(self) -> None:
        df1, df4 = _khung_1h_4h()
        s = _chien_luoc(_enable_short=True, _enable_long=False)
        d = _dataframe_san_sang_vao_lenh(s, df1, df4)
        ra = s.populate_entry_trend(d.copy(), {"pair": PAIR})
        assert "enter_short" in ra.columns and ra["enter_short"].fillna(0).sum() >= 1, (
            "không có tín hiệu Short nào — trend DOWN/ADX/tuổi trend chặn hết?"
        )
        dong = ra.index[ra["enter_short"] == 1][0]
        tag = json.loads(ra.loc[dong, "enter_tag"])
        assert tag["h"] == "s"
        assert tag["t4"] == "DOWN"
        # Hình học GƯƠNG: SL > p3 > p2 > p1 (LONG là sl < p3 < p2 < p1).
        assert tag["p1"] < tag["p2"] < tag["p3"] < tag["sl"], tag
        assert len(ra.loc[dong, "enter_tag"]) <= 255, "order tag Binance giới hạn 255 ký tự"
        assert "enter_long" not in ra.columns or ra["enter_long"].fillna(0).sum() == 0

    def test_enable_short_false_khong_tao_cot_enter_short_nao(self) -> None:
        """`enable_short` tắt ⇒ dataframe đầu ra byte-đồng-nhất với trước TD-0321:
        KHÔNG một cột `enter_short` nào (kể cả toàn 0)."""
        df1, df4 = _khung_1h_4h()
        s = _chien_luoc(_enable_short=False)
        d = _dataframe_san_sang_vao_lenh(s, df1, df4)
        assert d["xac_nhan_3_3b_short"].any(), "dữ liệu phải CÓ tín hiệu Short để công tắc có gì mà chặn"
        ra = s.populate_entry_trend(d.copy(), {"pair": PAIR})
        assert "enter_short" not in ra.columns, "công tắc tắt mà vẫn tạo cột enter_short"

    def test_enable_long_false_khong_sinh_enter_long(self) -> None:
        df1, df4 = _khung_1h_4h()
        s = _chien_luoc(_enable_long=False, _enable_short=False)
        d = _dataframe_san_sang_vao_lenh(s, df1, df4)
        assert d["xac_nhan_3_3b"].any(), "dữ liệu phải CÓ tín hiệu Long để công tắc có gì mà chặn"
        ra = s.populate_entry_trend(d.copy(), {"pair": PAIR})
        assert "enter_long" not in ra.columns or ra["enter_long"].fillna(0).sum() == 0


class TestTagGhiKhiCotDaDatChuoiRong:
    """🔴 Lỗi thật #1 của file này — xem docstring module."""

    def test_tag_short_van_duoc_ghi_khi_freqtrade_da_gan_chuoi_rong(self) -> None:
        df1, df4 = _khung_1h_4h()
        s = _chien_luoc(_enable_short=True, _enable_long=False)
        d = _dataframe_san_sang_vao_lenh(s, df1, df4)
        # Đúng thứ `IStrategy.advise_entry` làm TRƯỚC `populate_entry_trend`:
        d.loc[:, "enter_tag"] = ""
        ra = s.populate_entry_trend(d, {"pair": PAIR})
        vao = ra.index[ra["enter_short"] == 1]
        assert len(vao) >= 1
        assert all(ra.loc[i, "enter_tag"] != "" for i in vao), (
            "có tín hiệu Short nhưng enter_tag vẫn rỗng ⇒ custom_stake_amount sẽ raise "
            "'không có kế hoạch tranche' và Freqtrade NUỐT nó (0 lệnh, rc = 0)"
        )


class TestCongTacTat:
    def test_ghim_enable_short_false_trong_yaml_that(self) -> None:
        """🔴 ĐỔI GIÁ TRỊ NÀY LÀ MỞ KHÂU ĐO SHORT — không phải sửa một hằng số.

        Điều kiện mở lại nằm ở `DR-HUONG-01` §3 (ý tưởng suất (d) có kết cục tại
        cổng + một DR viết TRƯỚC khi đo) và `DR-D4-01` §2b (DG7 riêng, Δ_R(SHORT)
        `ok`, ≥ 9 suất). `DR-SHORT-01` chỉ cho phép DỰNG code, không cho bật.
        Ai đổi dòng này phải sửa CHÍNH dòng assert này, tức phải đọc tên các
        quyết định đó."""
        from tool_d.config.loader import load_tool_d_config, resolve

        assert resolve(load_tool_d_config(), "tier_a.enable_short") is False, (
            "tier_a.enable_short đã bị bật: khâu ĐO Short mở khoá theo DR-HUONG-01 §3 và "
            "DR-D4-01 §2b, không phải theo DR-SHORT-01 (chỉ cho DỰNG code)."
        )

    def test_chien_luoc_that_doc_hai_cong_tac_tu_yaml(self) -> None:
        s = _chien_luoc()
        assert s._enable_short is False
        assert s._enable_long is True

    def test_chot_kep_confirm_trade_entry_tu_choi_short_khi_tat(self) -> None:
        """Cửa cuối: dù `enter_short` lọt tới đây bằng đường nào khác, lệnh vẫn
        bị từ chối. Trả `False` (không raise): raise bị Freqtrade nuốt."""
        s = _chien_luoc()
        assert s.confirm_trade_entry(
            PAIR, "limit", 1.0, 1.0, "GTC", pd.Timestamp("2025-03-27", tz="UTC"), "{}", "short"
        ) is False

    def test_chot_kep_confirm_trade_entry_tu_choi_long_khi_enable_long_tat(self) -> None:
        s = _chien_luoc(_enable_long=False)
        assert s.confirm_trade_entry(
            PAIR, "limit", 1.0, 1.0, "GTC", pd.Timestamp("2025-03-27", tz="UTC"), "{}", "long"
        ) is False


class TestCongTrancheVaTp1TheoHuong:
    """🔴 Lỗ hổng phủ mà PHÁ THẬT lộ ra khi dựng file này: đảo chiều điều kiện
    bơm tranche 2/3 (`current_rate < muc` ↔ `> muc`) KHÔNG làm đỏ ca backtest nào
    — lệnh limit đặt tại p2/p3 tự khớp khi giá tới, bất kể cổng mở sớm hay
    muộn, nên fixture không phân biệt được. Cổng là điều kiện KÍCH HOẠT (khi nào
    được đặt lệnh), một khác biệt chỉ lộ ra ở đúng chỗ ta hỏi: hàm có đi qua
    cổng không. Nên hỏi thẳng, bằng vật thay thế tối thiểu, ở hai hướng."""

    @staticmethod
    def _trade(*, la_short: bool, so_tranche: int = 1):
        from types import SimpleNamespace

        return SimpleNamespace(
            is_short=la_short, has_open_orders=False, nr_of_successful_exits=0,
            nr_of_successful_entries=so_tranche, pair=PAIR, id=1, stake_amount=100.0,
            open_date_utc=pd.Timestamp("2025-03-27", tz="UTC"),
        )

    def _gate_qua_hay_chan(self, *, la_short: bool, current_rate: float) -> bool:
        """True nếu `adjust_trade_position` ĐI QUA cổng giá tới bước tính ZSS
        (bước ngay sau cổng), False nếu bị chặn tại cổng."""
        from tool_d.trade_plan import KeHoachTranche

        s = _chien_luoc()
        if la_short:
            kh = KeHoachTranche(zone_low=94.65, zone_high=95.35, p1=94.65, p2=95.0, p3=95.35,
                                sl=95.8, r_eff_plan=0.0085, atr_1h_tai_tranche1=0.3)
        else:
            kh = KeHoachTranche(zone_low=94.65, zone_high=95.35, p1=95.35, p2=95.0, p3=94.65,
                                sl=94.2, r_eff_plan=0.0085, atr_1h_tai_tranche1=0.3)
        goi: list = []
        s._xet_tp1 = lambda trade, rate: None
        s._doc_ke_hoach = lambda trade: (kh, None, {"t4": "DOWN" if la_short else "UP", "zs": 0.6})

        def _zss(pair, tag, current_time, loai="day"):
            goi.append(loai)
            return float("nan")  # NaN ⇒ hàm trả None ngay sau, không cần dựng cả thế giới

        s._zss_hien_tai = _zss
        s.adjust_trade_position(
            self._trade(la_short=la_short), pd.Timestamp("2025-03-27 20:00", tz="UTC"), current_rate,
            0.0, 0.0, 1e9, current_rate, current_rate, 0.0, 0.0,
        )
        assert len(goi) <= 1
        # tầng chọn `loai` cho DG5 cũng phải đúng hướng: SHORT đọc `cao` ("dinh").
        assert not goi or goi[0] == ("dinh" if la_short else "day"), goi
        return bool(goi)

    # 🔴 ĐẢO CHIỀU 20/09/2026 (`DR-D4-20` §2 chốt 3, chủ dự án duyệt sửa khẳng định — điều kiện dừng
    # `DR-D4-20` §5.1). Chiều CŨ ghim ở bốn ca dưới đây là *"chỉ bơm khi giá ĐÃ XUỐNG tới p2"*; lúc đó
    # lệnh mua limit tại p2 nằm TRÊN giá thị trường ⇒ sàn thật từ chối (post-only, LD-13) ⇒ tranche 2/3
    # không khớp được trên tiền thật. Luật mới: ĐẶT LỆNH CHỜ TRƯỚC, khi giá còn ở phía maker của p2.
    # Câu hỏi của test KHÔNG đổi (cổng có cho đặt lệnh không; DG5 đọc đúng loại zone theo hướng) —
    # chỉ kỳ vọng đảo. Ca biên (giá bằng đúng p2) giữ nguyên: bằng nhau thì vẫn cho đặt.

    def test_short_dat_truoc_khi_gia_CON_DUOI_p2(self) -> None:
        """SHORT bán tại p2: giá thị trường còn DƯỚI p2 ⇒ lệnh nằm phía maker ⇒ ĐƯỢC đặt."""
        assert self._gate_qua_hay_chan(la_short=True, current_rate=94.0) is True

    def test_short_bi_chan_khi_gia_DA_VUOT_p2(self) -> None:
        """Giá đã vượt p2 ⇒ lệnh bán tại p2 nằm dưới thị trường ⇒ sàn từ chối ⇒ KHÔNG đặt."""
        assert self._gate_qua_hay_chan(la_short=True, current_rate=95.5) is False

    def test_short_di_qua_dung_tai_bien_p2(self) -> None:
        """Bằng đúng p2 thì vẫn cho đặt (lề nghiêng về phía CHO ĐẶT — `post_only.bi_san_tu_choi`)."""
        assert self._gate_qua_hay_chan(la_short=True, current_rate=95.0) is True

    def test_long_dat_truoc_khi_gia_CON_TREN_p2(self) -> None:
        """LONG mua tại p2: giá còn TRÊN p2 ⇒ lệnh nằm phía maker ⇒ ĐƯỢC đặt (đây là lệnh chờ)."""
        assert self._gate_qua_hay_chan(la_short=False, current_rate=96.0) is True

    def test_long_bi_chan_khi_gia_DA_TUT_DUOI_p2(self) -> None:
        """Giá đã tụt dưới p2 ⇒ lệnh mua tại p2 nằm trên thị trường ⇒ sàn từ chối ⇒ KHÔNG đặt."""
        assert self._gate_qua_hay_chan(la_short=False, current_rate=94.5) is False

    # ── TP1 ───────────────────────────────────────────────────────────────
    @staticmethod
    def _tp1(*, la_short: bool, tp1_gia: float, current_rate: float):
        from types import SimpleNamespace

        s = _chien_luoc()
        chot = {"tp1_gia": tp1_gia, "ty_le_chot_tp1": 0.5, "tp_source": "zone_doi_dien"}
        trade = SimpleNamespace(
            is_short=la_short, pair=PAIR, stake_amount=100.0,
            get_custom_data=lambda k: chot if k == "chot_loi" else None,
        )
        return s._xet_tp1(trade, current_rate)

    def test_tp1_short_chua_toi_khi_gia_van_TREN_muc(self) -> None:
        assert self._tp1(la_short=True, tp1_gia=93.0, current_rate=94.0) is None

    def test_tp1_short_chot_khi_gia_XUONG_toi_muc(self) -> None:
        giam, tag = self._tp1(la_short=True, tp1_gia=93.0, current_rate=92.5)
        assert giam == pytest.approx(-50.0) and tag == "TP1_zone_doi_dien"

    def test_tp1_long_chua_toi_khi_gia_van_DUOI_muc_hoi_quy(self) -> None:
        assert self._tp1(la_short=False, tp1_gia=97.0, current_rate=96.0) is None

    def test_tp1_long_chot_khi_gia_LEN_toi_muc_hoi_quy(self) -> None:
        giam, _ = self._tp1(la_short=False, tp1_gia=97.0, current_rate=97.5)
        assert giam == pytest.approx(-50.0)


# ═══════════════════════════════════════════════════════════════════════════
# BACKTEST THẬT — subprocess `freqtrade backtesting`, cô lập cwd (xem TD-0239)
# ═══════════════════════════════════════════════════════════════════════════

def _ghi_du_lieu(datadir: Path) -> None:
    rows1 = _rows1_guong()
    bat_dau = _td0187._moc_bat_dau(len(rows1))
    idx1 = pd.date_range(bat_dau, periods=len(rows1), freq="1h", tz="UTC")
    df1 = pd.DataFrame(rows1, columns=["open", "high", "low", "close", "volume"])
    df1.insert(0, "date", idx1)
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    df4 = df1.set_index("date").resample("4h").agg(agg).reset_index()
    df1d = df1.set_index("date").resample("1D").agg(agg).reset_index()
    rows5 = [x for bar in rows1 for x in _td0187._chia_nho(bar, 12)]
    df5 = pd.DataFrame(rows5, columns=["open", "high", "low", "close", "volume"])
    df5.insert(0, "date", pd.date_range(bat_dau, periods=len(rows5), freq="5min", tz="UTC"))
    fund = pd.DataFrame({"date": idx1, "open": 0.0, "high": 0.0, "low": 0.0, "close": 0.0, "volume": 0.0})
    d = datadir / "futures"
    for nhan, df in (
        ("1h-futures", df1), ("1h-mark", df1), ("5m-futures", df5), ("5m-mark", df5),
        ("4h-futures", df4), ("1d-futures", df1d), ("1h-funding_rate", fund),
    ):
        _td0187._ghi_feather(df, d / f"{CAP}-{nhan}.feather")


def _chay(tmp: Path, ten: str, *, sua_yaml: dict[str, str]) -> dict:
    """Backtest THẬT trên dữ liệu lật gương, mỗi lượt một thư mục cwd riêng với
    bản sao `config/` đã sửa YAML — KHÔNG đụng một byte nào của repo thật."""
    datadir = tmp / "data"
    if not (datadir / "futures").exists():
        _ghi_du_lieu(datadir)
    run = tmp / f"run_{ten}"
    shutil.copytree(REPO_ROOT / "config", run / "config")
    yaml_p = run / "config" / "tool_d_config.yaml"
    y = yaml_p.read_text(encoding="utf-8")
    for cu, moi in sua_yaml.items():
        assert cu in y, f"YAML không còn dòng {cu!r} — cập nhật fixture"
        y = y.replace(cu, moi)
    yaml_p.write_text(y, encoding="utf-8")

    cfg = json.loads((run / "config" / "freqtrade" / "config.json").read_text(encoding="utf-8"))
    cfg["exchange"]["pair_whitelist"] = [PAIR]
    cfg["max_open_trades"] = 1
    cfg["stake_amount"] = 100
    cfg["dry_run"] = True
    cfg_path = run / "cfg.json"
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
    userdir = run / "userdir"
    (userdir / "strategies").mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [
            sys.executable, "-m", "freqtrade", "backtesting",
            "--config", str(cfg_path), "--datadir", str(datadir), "--userdir", str(userdir),
            "--strategy", "ZoneAbsorption", "--strategy-path", str(REPO_ROOT / "user_data" / "strategies"),
            "--timerange", TIMERANGE, "--timeframe-detail", "5m", "--cache", "none", "--export", "trades",
        ],
        capture_output=True, text=True, timeout=900, cwd=run,
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT / "src")},
    )
    assert proc.returncode == 0, f"backtest thất bại:\n{proc.stdout[-3000:]}\n{proc.stderr[-3000:]}"
    log = proc.stdout + proc.stderr
    # Freqtrade NUỐT exception của callback — log sạch là điều kiện của fixture.
    nuot = [d for d in log.splitlines() if "Strategy caused the following exception" in d]
    assert not nuot, f"{len(nuot)} exception bị Freqtrade nuốt — dòng đầu:\n{nuot[0][:300]}"
    from freqtrade.data.btanalysis import load_backtest_stats

    files = sorted((userdir / "backtest_results").glob("backtest-result-*.zip"))
    assert files, "không có file kết quả"
    kq = load_backtest_stats(files[-1])["strategy"]["ZoneAbsorption"]
    kq["_log"] = log
    return kq


@pytest.fixture(scope="module")
def tmp_module(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("td0321")


@pytest.fixture(scope="module")
def kq_short(tmp_module) -> dict:
    """Bật Short, TẮT Long — cô lập đường Short (và chứng minh công tắc Long)."""
    return _chay(
        tmp_module, "short",
        sua_yaml={"enable_short: false": "enable_short: true", "enable_long: true": "enable_long: false"},
    )


@pytest.fixture(scope="module")
def kq_yaml_that(tmp_module) -> dict:
    """YAML THẬT không sửa gì (`enable_short: false`) trên CÙNG dữ liệu có tín hiệu Short."""
    return _chay(tmp_module, "yaml_that", sua_yaml={})


def _lenh_short(kq: dict) -> list[dict]:
    return [t for t in kq["trades"] if t["is_short"]]


def _vao_short(t: dict) -> list[dict]:
    """Lệnh VÀO của một vị thế short là lệnh `sell`; lệnh THOÁT là `buy`."""
    return [o for o in t["orders"] if o.get("ft_order_side") == "sell"]


def _thoat_short(t: dict) -> list[dict]:
    return [o for o in t["orders"] if o.get("ft_order_side") == "buy"]


def _lenh_du_ba_tranche_short(kq: dict) -> dict:
    ung = [t for t in _lenh_short(kq) if len(_vao_short(t)) == 3]
    assert ung, f"không lệnh Short nào đủ 3 tranche — số tranche: {[len(_vao_short(t)) for t in _lenh_short(kq)]}"
    return ung[0]


class TestBacktestThatCoLenhShort:
    def test_khong_pass_rong_co_lenh_short_du_ba_tranche(self, kq_short) -> None:
        assert len(_lenh_short(kq_short)) >= 1, (
            "0 lệnh Short — mọi khẳng định dưới đây xanh-vô-nghĩa. Xem log SAN_TOOL_D/KET_NAP."
        )
        _lenh_du_ba_tranche_short(kq_short)

    def test_enable_long_false_khong_co_lenh_long_nao(self, kq_short) -> None:
        assert all(t["is_short"] for t in kq_short["trades"]), [t["is_short"] for t in kq_short["trades"]]

    def test_don_bay_bang_L_exchange(self, kq_short) -> None:
        from tool_d.config.loader import load_tool_d_config, resolve

        l_exchange = float(resolve(load_tool_d_config(), "tier_a.L_exchange"))
        for t in _lenh_short(kq_short):
            assert float(t["leverage"]) == pytest.approx(l_exchange)


class TestTrancheDCALen:
    def test_ba_tranche_ban_voi_gia_TANG_dan(self, kq_short) -> None:
        """Gương của DCA-xuống: Long mua rẻ dần (p1 > p2 > p3), Short bán ĐẮT dần."""
        gia = [float(o["safe_price"]) for o in _vao_short(_lenh_du_ba_tranche_short(kq_short))]
        assert gia == sorted(gia) and len(set(gia)) == 3, f"giá tranche Short không tăng dần: {gia}"

    def test_ba_tranche_cost_bang_nhau_1_1_1(self, kq_short) -> None:
        cost = [float(o["cost"]) for o in _vao_short(_lenh_du_ba_tranche_short(kq_short))]
        ty_le = [c / cost[0] for c in cost]
        assert all(abs(r - 1.0) < 0.01 for r in ty_le), f"tỉ lệ cost tranche Short = {ty_le}"

    def test_cost_tranche1_qua_san_tool_d_khong_phai_lenh_bi_nuot(self, kq_short) -> None:
        """Cỡ lệnh ≥ sàn 30 USDT của LTC: bản K = 120 ra 17,9 và bị `SAN_TOOL_D
        TU_CHOI` — lệnh không hề mở. Ghim để K không bị đổi lại mà không ai thấy."""
        cost1 = float(_vao_short(_lenh_du_ba_tranche_short(kq_short))[0]["cost"])
        assert cost1 >= 30.0, cost1


class TestSLTrenGiaVao:
    def test_stop_loss_tuyet_doi_TREN_gia_vao_trung_binh(self, kq_short) -> None:
        t = _lenh_du_ba_tranche_short(kq_short)
        assert float(t["stop_loss_abs"]) > float(t["open_rate"]), (t["stop_loss_abs"], t["open_rate"])

    def test_sl_khop_tag_va_tren_moi_tranche(self, kq_short) -> None:
        t = _lenh_du_ba_tranche_short(kq_short)
        tag = json.loads(t["enter_tag"])
        assert float(t["stop_loss_abs"]) == pytest.approx(tag["sl"], rel=1e-6)
        assert all(float(o["safe_price"]) < tag["sl"] for o in _vao_short(t))


class TestChotLoiDuoi:
    def test_tp1_thoat_mot_phan_o_muc_DUOI_gia_vao(self, kq_short) -> None:
        t = _lenh_du_ba_tranche_short(kq_short)
        thoat = _thoat_short(t)
        assert len(thoat) >= 2, f"cần TP1 + TP2, có {len(thoat)} lệnh thoát"
        gia_vao_tb = float(t["open_rate"])
        tp1 = thoat[0]
        assert float(tp1["safe_price"]) < gia_vao_tb, (tp1["safe_price"], gia_vao_tb)
        tong_vao = sum(float(o["amount"]) for o in _vao_short(t))
        assert float(tp1["amount"]) == pytest.approx(TY_LE_CHOT_TP1 * tong_vao, rel=0.02)

    def test_tp2_trail_dong_phan_con_lai_o_muc_DUOI_gia_vao(self, kq_short) -> None:
        t = _lenh_du_ba_tranche_short(kq_short)
        assert t["exit_reason"] == "TP2_TRAIL", t["exit_reason"]
        assert float(_thoat_short(t)[-1]["safe_price"]) < float(t["open_rate"])

    def test_tp1_lay_tu_zone_day_DUOI_khong_phai_nang(self, kq_short) -> None:
        """Nguồn TP1 = zone đối diện (zone ĐÁY), không rơi nạng: chứng minh
        `_zone_day_duoi` + `chon_muc_tp1(huong="short")` được nối thật."""
        log = kq_short["_log"]
        dong = [d for d in log.splitlines() if "TP_CHON" in d]
        assert dong, "không có dấu vết TP_CHON — `_cap_nhat_chot_loi` không chạy trên đường thật"
        assert all("nguon=zone_doi_dien" in d for d in dong), dong[:3]
        assert any("TP_ZONE_UNGVIEN_SHORT" in d for d in log.splitlines())


class TestTagMangKhoaHuong:
    def test_enter_tag_co_h_s_va_hinh_hoc_guong(self, kq_short) -> None:
        t = _lenh_du_ba_tranche_short(kq_short)
        tag = json.loads(t["enter_tag"])
        assert tag["h"] == "s"
        assert tag["t4"] == "DOWN"
        assert tag["p1"] < tag["p2"] < tag["p3"] < tag["sl"]
        assert len(t["enter_tag"]) <= 255, "order tag Binance giới hạn 255 ký tự"

    def test_moi_tag_tranche_khop_tranche_1(self, kq_short) -> None:
        """L-Z49: tag mọi tranche bằng tag tranche 1 (mặt cắt quan sát từ ngoài)."""
        t = _lenh_du_ba_tranche_short(kq_short)
        for o in _vao_short(t):
            assert o.get("ft_order_tag") == t["enter_tag"], (o.get("ft_order_tag"), t["enter_tag"])


class TestYamlThatKhongSinhLenhShort:
    def test_khong_co_lenh_short_nao_du_du_lieu_co_tin_hieu_short(self, kq_yaml_that) -> None:
        """🔴 Bản ghim mạnh nhất của công tắc: cùng dữ liệu mà `kq_short` sinh lệnh
        Short, YAML thật (`enable_short: false`) phải sinh ĐÚNG 0."""
        assert not _lenh_short(kq_yaml_that), [t["open_date"] for t in _lenh_short(kq_yaml_that)]
        log = kq_yaml_that["_log"]
        assert "XAC_NHAN_3_3B_SHORT" in log, (
            "đường Short không hề chạy — công tắc không chặn được gì, ca này xanh-vô-nghĩa"
        )
