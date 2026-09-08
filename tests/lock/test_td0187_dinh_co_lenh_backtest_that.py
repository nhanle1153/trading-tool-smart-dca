"""🔴 TD-0187 — tầng định cỡ §6.8f đo trên FILL của backtest THẬT (MT-16, DR-D4-04).

Ba điều `tests/unit/test_sizing.py` KHÔNG chứng minh được, và file này phải:

1. **Tỉ trọng tranche thật = ⅓ ⅓ ⅓.** Đọc `cost` từng lệnh vào trong file kết
   quả backtest — cùng cách MT-16 đo ra ¼-¼-½ trên 91 lượt khớp niêm phong.
   Một cấu hình `w_tranche` nạp được không nói gì về thứ đã chạy (ca
   `test_mot_phan_tu_..._VAN_qua_kiem_tong` đã ghim đúng giới hạn đó).
2. **D0.1 trên đường sản xuất:** `cost₁ ≈ (rho × E_D / R_eff) × w₁` với
   `R_eff` giải mã từ chính `enter_tag` của lệnh — tức cỡ lệnh THẬT biến
   theo `1/R_eff` và rủi ro kế hoạch = 1,875 USDT (DR-D0PRE-06).
3. **Đòn bẩy 3x thật sự được áp** — `trade["leverage"] == L_exchange`. Trước
   `ZoneAbsorption` không file nào cài `leverage()` ⇒ mọi backtest chạy 1x.

Và một phép đối chiếu: **`ZoneAbsorption` và `ZoneAbsorptionMinimal` cho
CÙNG zone trên CÙNG dữ liệu** (zl/zh/p1/p2/p3/sl bằng nhau). Phần zone của
file mới là bản chép của Minimal; ca này canh nó không trôi.

Bộ sinh dữ liệu tái dùng `_chia_nho`/`_ghi_feather` của L-Z49 qua importlib
(`tests/` không phải package). Khác L-Z49 ở hai chỗ có chủ đích: (a) 85
ngày UPTREND trước mẫu zone — để ADX(14,1D) ≥ 20 (mẩu §2.5 mà tầng định cỡ
đòi), (b) thêm khung 1D. Chuỗi phẳng của L-Z49 có ADX ≈ 0 nên với chiến
lược sản xuất sẽ không vào lệnh nào — và guard PASS RỖNG bên dưới bắt được.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CAP = "LTC_USDT_USDT"  # trong POOL (BTC/ETH la EXPLORE, DR-D0PRE-05); san notional 5 USDT, buoc khoi luong nho
SAN_XUAT, TOI_THIEU = "ZoneAbsorption", "ZoneAbsorptionMinimal"
TIMERANGE = "20250315-20250402"

# ── tái dùng bộ sinh nến của L-Z49 ────────────────────────────────────
_spec = importlib.util.spec_from_file_location(
    "lz49", REPO_ROOT / "tests" / "lock" / "test_lz49_lz50_backtest_nho.py"
)
_lz49 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_lz49)  # type: ignore[union-attr]
_chia_nho, _ghi_feather, _lenh_vao = _lz49._chia_nho, _lz49._ghi_feather, _lz49._lenh_vao


def _bars_4h_co_trend() -> list[tuple[float, float, float, float, float]]:
    """85 ngày uptrend 80 → 100 (ADX 1D cao), rồi ĐÚNG mẫu zone của L-Z49
    neo ở mức 100, rồi đuôi phẳng để lệnh có chỗ đóng theo DG8."""
    b: list[tuple[float, float, float, float, float]] = []
    n_pre = 85 * 6
    for k in range(n_pre):
        base = 80.0 + 20.0 * k / n_pre
        o = base + (0.2 if k % 2 else -0.2)
        b.append((o, o + 0.4, o - 0.4, o + (0.1 if k % 2 else -0.1), 1000.0))
    b += [
        (99.5, 99.5, 95.0, 96.0, 4000.0),      # swing đáy, volume cao
        (96.0, 96.8, 95.2, 96.6, 1200.0),
        (96.6, 97.0, 96.2, 96.8, 1000.0),
        (96.8, 97.1, 96.4, 96.9, 1000.0),      # nến tín hiệu
        (96.9, 97.0, 95.30, 95.40, 1000.0),    # chạm p1 → tranche 1
        (94.98, 95.10, 94.90, 94.95, 1000.0),  # mở ≤ p2 → tranche 2
        (94.60, 94.70, 94.40, 94.60, 1000.0),  # mở ≤ p3 → tranche 3
        (94.65, 95.20, 94.55, 95.10, 1000.0),
        (95.10, 95.60, 95.00, 95.50, 1000.0),
        (95.50, 96.00, 95.40, 95.90, 1000.0),
    ]
    for k in range(30):
        b.append((95.9, 96.3, 95.5, 95.9 + (0.1 if k % 2 else -0.1), 1000.0))
    return b


def _sinh_du_lieu(datadir: Path) -> None:
    rows4 = _bars_4h_co_trend()
    rows1 = [x for bar in rows4 for x in _chia_nho(bar, 4)]
    idx1 = pd.date_range("2025-01-01", periods=len(rows1), freq="1h", tz="UTC")
    df1 = pd.DataFrame(rows1, columns=["open", "high", "low", "close", "volume"])
    df1.insert(0, "date", idx1)
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    df4 = df1.set_index("date").resample("4h").agg(agg).reset_index()
    df1d = df1.set_index("date").resample("1D").agg(agg).reset_index()
    rows5 = [x for bar in rows1 for x in _chia_nho(bar, 12)]
    df5 = pd.DataFrame(rows5, columns=["open", "high", "low", "close", "volume"])
    df5.insert(0, "date", pd.date_range("2025-01-01", periods=len(rows5), freq="5min", tz="UTC"))

    d = datadir / "futures"
    _ghi_feather(df1, d / f"{CAP}-1h-futures.feather")
    _ghi_feather(df1, d / f"{CAP}-1h-mark.feather")
    _ghi_feather(df5, d / f"{CAP}-5m-futures.feather")
    _ghi_feather(df5, d / f"{CAP}-5m-mark.feather")
    _ghi_feather(df4, d / f"{CAP}-4h-futures.feather")
    _ghi_feather(df1d, d / f"{CAP}-1d-futures.feather")
    fund = pd.DataFrame({"date": idx1, "open": 0.0, "high": 0.0, "low": 0.0, "close": 0.0, "volume": 0.0})
    _ghi_feather(fund, d / f"{CAP}-1h-funding_rate.feather")


def _chay(tmp: Path, chien_luoc: str) -> dict:
    datadir, userdir = tmp / "data", tmp / f"userdir_{chien_luoc}"
    if not (datadir / "futures").exists():
        _sinh_du_lieu(datadir)
    (userdir / "strategies").mkdir(parents=True, exist_ok=True)
    cfg = json.loads((REPO_ROOT / "config" / "freqtrade" / "config.json").read_text(encoding="utf-8"))
    cfg["exchange"]["pair_whitelist"] = ["LTC/USDT:USDT"]
    cfg["max_open_trades"] = 1
    cfg["stake_amount"] = 100  # bị custom_stake_amount ghi đè — nếu KHÔNG, ca cỡ lệnh bên dưới đỏ
    cfg["dry_run"] = True
    cfg_path = tmp / f"cfg_{chien_luoc}.json"
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable, "-m", "freqtrade", "backtesting",
            "--config", str(cfg_path), "--datadir", str(datadir), "--userdir", str(userdir),
            "--strategy", chien_luoc, "--strategy-path", str(REPO_ROOT / "user_data" / "strategies"),
            "--timerange", TIMERANGE, "--timeframe-detail", "5m", "--cache", "none", "--export", "trades",
        ],
        capture_output=True, text=True, timeout=900, cwd=REPO_ROOT,
    )
    assert proc.returncode == 0, f"backtest {chien_luoc} thất bại:\n{proc.stdout[-3000:]}\n{proc.stderr[-3000:]}"
    # 🔴 Freqtrade NUỐT exception từ callback (`strategy_safe_wrapper`: log
    # WARNING rồi đi tiếp). Lần chạy đầu của TD-0187: SizingError "stake <
    # min_stake" bị nuốt 12 lần, lệnh mẫu biến mất trong im lặng, rc vẫn 0.
    # Một chốt fail-closed mà bị nuốt là một chốt không tồn tại — nên log
    # sạch là điều kiện của fixture, không phải của riêng một ca.
    log = proc.stdout + proc.stderr
    nuot = [d for d in log.splitlines() if "Strategy caused the following exception" in d]
    assert not nuot, f"{chien_luoc}: {len(nuot)} exception bị Freqtrade nuốt — dòng đầu:\n{nuot[0][:300]}"
    from freqtrade.data.btanalysis import load_backtest_stats

    files = sorted((userdir / "backtest_results").glob("backtest-result-*.zip"))
    assert files, "không có file kết quả"
    return load_backtest_stats(files[-1])["strategy"][chien_luoc]


@pytest.fixture(scope="module")
def tmp_module(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("td0187")


@pytest.fixture(scope="module")
def kq_san_xuat(tmp_module) -> dict:
    return _chay(tmp_module, SAN_XUAT)


@pytest.fixture(scope="module")
def kq_toi_thieu(tmp_module) -> dict:
    return _chay(tmp_module, TOI_THIEU)


def _lenh_du_ba_tranche(kq: dict) -> dict:
    ung = [t for t in kq["trades"] if len(_lenh_vao(t)) == 3]
    assert ung, f"không lệnh nào đủ 3 tranche — số tranche: {[len(_lenh_vao(t)) for t in kq['trades']]}"
    return ung[0]


class TestKhongPassRong:
    def test_co_lenh_va_co_lenh_du_ba_tranche(self, kq_san_xuat) -> None:
        assert len(kq_san_xuat["trades"]) >= 1, "0 lệnh — dữ liệu hỏng hoặc ADX(1D) < 20 chặn hết"
        _lenh_du_ba_tranche(kq_san_xuat)


class TestDonBay:
    def test_leverage_bang_L_exchange_khong_phai_1x(self, kq_san_xuat) -> None:
        """Trước file này không ai cài `leverage()` ⇒ 1x (MT-16 triệu chứng 5)."""
        from tool_d.config.loader import load_tool_d_config, resolve

        l_exchange = float(resolve(load_tool_d_config(), "tier_a.L_exchange"))
        for t in kq_san_xuat["trades"]:
            assert float(t["leverage"]) == pytest.approx(l_exchange), t["leverage"]
        assert l_exchange != 1.0, "cấu hình đang 1x thì ca này không phân biệt được gì"


class TestTiTrongTrancheThat:
    def test_ba_tranche_bang_nhau_KHONG_phai_1_1_2(self, kq_san_xuat) -> None:
        """🔴 Con số MT-16 đo được là 10 / 10 / 20. Ở đây phải là 1 : 1 : 1."""
        t = _lenh_du_ba_tranche(kq_san_xuat)
        cost = [float(o["cost"]) for o in _lenh_vao(t)]
        ty_le = [c / cost[0] for c in cost]
        assert all(abs(r - 1.0) < 0.01 for r in ty_le), f"tỉ lệ cost tranche = {ty_le} (MT-16 là [1, 1, 2])"


class TestD01TrenDuongSanXuat:
    def test_cost_tranche1_bang_N_full_nhan_w1_voi_R_eff_tu_chinh_tag(self, kq_san_xuat) -> None:
        """Rủi ro kế hoạch = rho × E_D = 1,875 USDT, cỡ lệnh biến theo 1/R_eff.
        `R_eff` lấy từ ĐÚNG enter_tag của lệnh — không dựng tay."""
        from tool_d.config.loader import load_tool_d_config, resolve

        cfg = load_tool_d_config()
        e_d = float(resolve(cfg, "tier_a.E_D"))
        rho = float(resolve(cfg, "tier_a.rho_pct")) / 100.0
        w = [float(x) for x in resolve(cfg, "tier_frozen.w_tranche.value")]

        t = _lenh_du_ba_tranche(kq_san_xuat)
        tag = json.loads(t["enter_tag"])
        p_avg = (tag["p1"] + tag["p2"] + tag["p3"]) / 3
        r_eff = (p_avg - tag["sl"]) / p_avg
        # Sáu hệ số §6.2 trong kịch bản này: zss đọc từ CHÍNH tag (không dựng
        # tay); regime = 1.0 vì dữ liệu 85 ngày uptrend cho ADX(1D) ≥ 25 (nếu
        # ca này đỏ ở hệ số 0,7 thì dữ liệu không mạnh như thiết kế — đó là
        # thông tin, không phải chỗ để nới); corr/dd/deploy = 1.0 vì chỉ một
        # vị thế, dd = 0, không vị thế khác; edge = 1.0 (chưa lệnh live).
        from tool_d.sizing import mult_zss

        mult = 1.0 * mult_zss(float(tag["zs"])) * 1.0 * 1.0 * 1.0 * 1.0
        assert 0.5 <= mult <= 1.0
        n_full = rho * mult * e_d / r_eff
        cost = [float(o["cost"]) for o in _lenh_vao(t)]
        # dung sai 1%: làm tròn khối lượng theo amount_precision + giá khớp lệch p_i một bước làm tròn
        assert cost[0] == pytest.approx(n_full * w[0], rel=0.01), (cost[0], n_full * w[0], r_eff)
        assert sum(cost) == pytest.approx(n_full, rel=0.01)
        # và tuyệt đối KHÔNG phải cỡ placeholder 10 USDT của config.json
        assert cost[0] > 15.0

    def test_stake_la_ky_quy_bang_cost_chia_L(self, kq_san_xuat) -> None:
        t = _lenh_du_ba_tranche(kq_san_xuat)
        o1 = _lenh_vao(t)[0]
        stake1 = float(o1.get("stake_amount") or o1.get("ft_stake_amount") or 0.0) or float(t["stake_amount"]) / 3
        assert stake1 * float(t["leverage"]) == pytest.approx(float(o1["cost"]), rel=0.02)


class TestTagMangDuKhoaMoi:
    def test_enter_tag_co_zs_t4_sw_va_t4_la_UP(self, kq_san_xuat) -> None:
        t = _lenh_du_ba_tranche(kq_san_xuat)
        tag = json.loads(t["enter_tag"])
        for k in ("zl", "zh", "p1", "p2", "p3", "sl", "zs", "t4", "sw"):
            assert k in tag, f"thiếu {k}"
        assert 0.0 < tag["zs"] <= 1.0
        # Không đoán hướng — TÍNH LẠI độc lập từ chính chuỗi 4H tổng hợp tại
        # nến đã đóng ngay trước giờ mở lệnh (bản đầu đoán "UP" và sai: cú rơi
        # 100→95 trong 4 nến kéo EMA20 xuống dưới EMA50 ⇒ DOWN là đúng dữ liệu).
        import numpy as np
        import talib
        from tool_d.trend_context import trend_dir_tai

        dong = np.asarray([b[3] for b in _bars_4h_co_trend()], dtype=float)
        t0 = pd.Timestamp("2025-01-01", tz="UTC")
        mo = pd.Timestamp(t["open_date"])
        idx_nen_dong_truoc = int((mo - t0) / pd.Timedelta(hours=4)) - 1
        ema_f, ema_s = talib.EMA(dong, timeperiod=20), talib.EMA(dong, timeperiod=50)
        # tín hiệu sinh ở nến j (đóng trước lệnh); trend ghi vào tag là trend TẠI j
        ky_vong = {trend_dir_tai(ema_f, ema_s, i) for i in (idx_nen_dong_truoc, idx_nen_dong_truoc - 1)}
        assert tag["t4"] in ky_vong, (tag["t4"], ky_vong, idx_nen_dong_truoc)
        assert len(t["enter_tag"]) <= 255, "order tag Binance giới hạn 255 ký tự"

    def test_moi_tag_tranche_2_3_khop_tranche_1(self, kq_san_xuat) -> None:
        """L-Z49 giữ nguyên trên chiến lược sản xuất."""
        t = _lenh_du_ba_tranche(kq_san_xuat)
        for o in _lenh_vao(t):
            assert o.get("ft_order_tag") == t["enter_tag"]


class TestCungZoneVoiMinimal:
    def test_san_xuat_va_toi_thieu_cho_CUNG_zone_tren_CUNG_du_lieu(self, kq_san_xuat, kq_toi_thieu) -> None:
        """Phần zone của `ZoneAbsorption` là bản chép của Minimal — canh nó không trôi."""
        assert kq_toi_thieu["trades"], "Minimal không vào lệnh trên dữ liệu này — bộ sinh đã lệch khỏi L-Z49"
        ta, tb = _lenh_du_ba_tranche(kq_san_xuat), _lenh_du_ba_tranche(kq_toi_thieu)
        # Cùng zone ⇒ cùng thời điểm mở (lệnh mẫu: 2025-03-27 16:00). Lần chạy
        # đầu ZoneAbsorption KHÔNG có lệnh này (bị min_stake chặn trong im lặng)
        # mà chỉ có các zone ở đuôi — so tag của "lệnh đủ 3 tranche đầu tiên"
        # thôi thì không phát hiện được sự vắng mặt đó.
        assert ta["open_date"][:13] == tb["open_date"][:13], (ta["open_date"], tb["open_date"])
        a, b = json.loads(ta["enter_tag"]), json.loads(tb["enter_tag"])
        for k in ("zl", "zh", "p1", "p2", "p3", "sl"):
            assert a[k] == pytest.approx(b[k], abs=1e-9), (k, a[k], b[k])

    def test_minimal_van_1x_va_1_1_2_de_doi_chung(self, kq_toi_thieu) -> None:
        """Đối chứng âm: chính Minimal trên cùng dữ liệu vẫn cho 1x và 1:1:2 —
        tức khác biệt đo được ở các ca trên là do TẦNG ĐỊNH CỠ, không do dữ liệu."""
        t = [x for x in kq_toi_thieu["trades"] if len(_lenh_vao(x)) == 3]
        assert t, "Minimal không có lệnh đủ 3 tranche"
        cost = [float(o["cost"]) for o in _lenh_vao(t[0])]
        assert float(t[0]["leverage"]) == pytest.approx(1.0)
        assert cost[2] / cost[0] == pytest.approx(2.0, rel=0.02), f"Minimal phải ra 1:1:2, đo được {[c / cost[0] for c in cost]}"
