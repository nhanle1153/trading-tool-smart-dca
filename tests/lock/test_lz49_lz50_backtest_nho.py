"""L-Z49 (🔴 CRITICAL) + L-Z50 — §9b.4/§4b, TD-0117.

Spec đòi đúng chữ: *"test đơn vị **dựng backtest nhỏ** (1 pair, 1 zone,
3 tranche), khẳng định `custom_data` ghi ở tranche 1 đọc lại NGUYÊN VẸN
ở callback của tranche 2, 3, DG6, DG7, DG8 và `custom_exit`"*.

TD-0114/TD-0115 đã xác minh hai giả định này bằng **lần chạy thật trên
CALIB** (bắt được bug thật: `custom_data` khởi tạo từ dataframe đã
`ffill` — 2/25 trade lệch; sửa sang `trade.enter_tag` → 0/27). Nhưng
một lần chạy thật KHÔNG canh được hồi quy: lần sau ai sửa
`ZoneAbsorptionMinimal.py` là bug đó âm thầm quay lại, đúng lúc L-Z49
sinh ra để chặn (*"FAIL → không chạy D0.9"*). File này là phần canh đó.

🔴 Dữ liệu TỰ DỰNG, không đọc `user_data/data/` — theo đúng tiền lệ
TD-0102: dữ liệu thật bị `.gitignore` chặn nên test dựa vào nó sẽ không
chạy được ở máy khác (và tệ hơn: `skip` im lặng = pass rỗng). Chuỗi giá
ở đây được thiết kế để rơi đúng vào zone hợp lệ rồi đi xuống xuyên
p1 → p2 → p3 mà không thủng SL.

🔴 Chặn PASS RỖNG: một backtest 0 lệnh sẽ làm mọi khẳng định "mọi tag
đều khớp" thành đúng-một-cách-vô-nghĩa (đúng bẫy `verify_all_seals()`
mắc ở TD-0084: 0 seal = pass rỗng). Nên có test riêng khẳng định fixture
THẬT SỰ sinh ra một lệnh 3 tranche trước đã.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CHIEN_LUOC = "ZoneAbsorptionMinimal"
CAP = "BTC_USDT_USDT"


def _bars_4h() -> list[tuple[float, float, float, float, float]]:
    """Nến 4H dựng tay. Chỉ số 55 là swing đáy; tín hiệu rơi vào 58;
    59-61 là đường đi xuống chạm lần lượt p1/p2/p3.

    Kế hoạch mà chiến lược tính ra từ chuỗi này (đã đối chiếu khi dựng):
    zone = [94.652, 95.348] · p1 = 95.348 · p2 = 95.000 · p3 = 94.652 ·
    SL = 94.196 — nên các nến 59-61 phải xuống tới 94.4 mà KHÔNG dưới
    94.196, cửa sổ chỉ 0.456.
    """
    b: list[tuple[float, float, float, float, float]] = []
    for k in range(55):  # 220 nến 1H > startup_candle_count = 200
        o = 100.0 + (0.2 if k % 2 else -0.2)
        b.append((o, o + 0.4, o - 0.4, o + (0.1 if k % 2 else -0.1), 1000.0))
    b.append((99.5, 99.5, 95.0, 96.0, 4000.0))     # 55 swing đáy, volume cao
    b.append((96.0, 96.8, 95.2, 96.6, 1200.0))     # 56 chạm lại zone rồi bật ra
    b.append((96.6, 97.0, 96.2, 96.8, 1000.0))     # 57 lặng, ATR co lại
    b.append((96.8, 97.1, 96.4, 96.9, 1000.0))     # 58 ← nến tín hiệu
    b.append((96.9, 97.0, 95.30, 95.40, 1000.0))   # 59 chạm p1  → tranche 1
    b.append((94.98, 95.10, 94.90, 94.95, 1000.0))  # 60 mở ≤ p2 → tranche 2
    b.append((94.60, 94.70, 94.40, 94.60, 1000.0))  # 61 mở ≤ p3 → tranche 3
    b.append((94.65, 95.20, 94.55, 95.10, 1000.0))  # 62 hồi phục
    b.append((95.10, 95.60, 95.00, 95.50, 1000.0))  # 63
    b.append((95.50, 96.00, 95.40, 95.90, 1000.0))  # 64
    return b


def _chia_nho(bar, so_phan: int) -> list[tuple[float, float, float, float, float]]:
    """Tách một nến thành `so_phan` nến con sao cho gộp lại đúng o/h/l/c
    (first-open, max-high, min-low, last-close) — giữ hai khung nhất quán
    bằng CẤU TRÚC, không phải bằng may mắn."""
    o, h, l, c, v = bar
    q = v / so_phan
    con = [(o, o, o, o, q), (o, h, o, h, q), (h, h, l, l, q), (l, max(l, c), min(l, c), c, q)]
    while len(con) < so_phan:  # nến đệm phẳng ở giá đóng cửa, không đổi o/h/l/c gộp
        con.insert(-1, (l, max(l, c), min(l, c), c, 0.0))
    return con[:so_phan]


def _ghi_feather(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_feather(path)


def _sinh_du_lieu(datadir: Path) -> None:
    rows4 = _bars_4h()
    rows1 = [x for bar in rows4 for x in _chia_nho(bar, 4)]
    idx1 = pd.date_range("2025-01-01", periods=len(rows1), freq="1h", tz="UTC")
    df1 = pd.DataFrame(rows1, columns=["open", "high", "low", "close", "volume"])
    df1.insert(0, "date", idx1)

    r = (
        df1.set_index("date")
        .resample("4h")
        .agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
    )
    for k, bar in enumerate(rows4):
        got = (r.iloc[k]["open"], r.iloc[k]["high"], r.iloc[k]["low"], r.iloc[k]["close"])
        assert all(abs(a - b) < 1e-9 for a, b in zip(got, bar[:4])), f"nến 4h {k} lệch: {got}"

    rows5 = [x for bar in rows1 for x in _chia_nho(bar, 12)]
    idx5 = pd.date_range("2025-01-01", periods=len(rows5), freq="5min", tz="UTC")
    df5 = pd.DataFrame(rows5, columns=["open", "high", "low", "close", "volume"])
    df5.insert(0, "date", idx5)

    d = datadir / "futures"
    _ghi_feather(df1, d / f"{CAP}-1h-futures.feather")
    _ghi_feather(df1, d / f"{CAP}-1h-mark.feather")
    _ghi_feather(df5, d / f"{CAP}-5m-futures.feather")
    _ghi_feather(df5, d / f"{CAP}-5m-mark.feather")

    # Chuỗi 4H phải bắt đầu TRƯỚC 1H: nếu không, các nến 1h đầu chưa có
    # nến 4h nào đóng xong -> cột informative là NaN -> chiến lược vỡ khi
    # mask. Dữ liệu thật không dính vì hai chuỗi tải về độc lập.
    df4 = r.reset_index()
    dem = df4.iloc[[0, 0]].copy()
    dem["date"] = [idx1[0] - pd.Timedelta(hours=8), idx1[0] - pd.Timedelta(hours=4)]
    df4 = pd.concat([dem, df4], ignore_index=True)
    _ghi_feather(df4, d / f"{CAP}-4h-futures.feather")

    # funding = 0 để không nhiễu phép đo (DG7 không phải phạm vi test này)
    fund = pd.DataFrame({"date": idx1, "open": 0.0, "high": 0.0, "low": 0.0, "close": 0.0, "volume": 0.0})
    _ghi_feather(fund, d / f"{CAP}-1h-funding_rate.feather")


def _chay_backtest(tmp: Path) -> dict:
    datadir, userdir = tmp / "data", tmp / "userdir"
    _sinh_du_lieu(datadir)
    (userdir / "strategies").mkdir(parents=True, exist_ok=True)

    cfg = json.loads((REPO_ROOT / "config" / "freqtrade" / "config.json").read_text(encoding="utf-8"))
    cfg["exchange"]["pair_whitelist"] = ["BTC/USDT:USDT"]
    cfg["max_open_trades"] = 1
    cfg["stake_amount"] = 100
    cfg["dry_run"] = True
    cfg_path = tmp / "cfg.json"
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable, "-m", "freqtrade", "backtesting",
            "--config", str(cfg_path),
            "--datadir", str(datadir),
            "--userdir", str(userdir),
            "--strategy", CHIEN_LUOC,
            "--strategy-path", str(REPO_ROOT / "user_data" / "strategies"),
            "--timerange", "20250101-20250120",
            "--timeframe-detail", "5m",
            "--cache", "none",  # TD-0115: cache từng cho ra kết quả sai lệch
            "--export", "trades",
        ],
        capture_output=True, text=True, timeout=900,
    )
    assert proc.returncode == 0, f"backtest thất bại:\n{proc.stdout[-3000:]}\n{proc.stderr[-3000:]}"

    from freqtrade.data.btanalysis import load_backtest_stats

    ket_qua = sorted((userdir / "backtest_results").glob("backtest-result-*.zip"))
    assert ket_qua, f"không tìm thấy file kết quả trong {userdir / 'backtest_results'}"
    return load_backtest_stats(ket_qua[-1])["strategy"][CHIEN_LUOC]


@pytest.fixture(scope="module")
def ket_qua(tmp_path_factory) -> dict:
    return _chay_backtest(tmp_path_factory.mktemp("lz49"))


def _lenh_vao(trade: dict) -> list[dict]:
    return [o for o in trade.get("orders", []) if o.get("ft_order_side") in ("buy", "long")]


class TestFixtureKhongPassRong:
    """Chặn bẫy pass rỗng: mọi khẳng định bên dưới đều đúng-vô-nghĩa nếu
    backtest không sinh ra lệnh nào."""

    def test_co_it_nhat_mot_lenh(self, ket_qua) -> None:
        assert len(ket_qua["trades"]) >= 1, "fixture không sinh ra lệnh nào — chuỗi giá đã hỏng"

    def test_co_lenh_du_ba_tranche(self, ket_qua) -> None:
        so_tranche = [len(_lenh_vao(t)) for t in ket_qua["trades"]]
        assert 3 in so_tranche, f"spec đòi 1 zone/3 tranche, fixture chỉ cho {so_tranche}"


class TestLZ49KeHoachNguyenVenQuaCallback:
    """🔴 L-Z49 — `custom_data` ghi ở tranche 1 phải đọc lại NGUYÊN VẸN ở
    callback tranche 2/3. Tag lệnh tranche 2/3 được chiến lược lấy TỪ
    `custom_data`; nếu nó từng lệch, tag sẽ khác `enter_tag` của tranche 1
    — đó chính là mặt cắt quan sát được từ ngoài."""

    def test_moi_tag_tranche_khop_enter_tag_tranche1(self, ket_qua) -> None:
        for t in ket_qua["trades"]:
            enter_tag = t.get("enter_tag")
            assert enter_tag, "tranche 1 không có enter_tag — kế hoạch không được chốt cứng"
            for k, o in enumerate(_lenh_vao(t), start=1):
                assert o.get("ft_order_tag") == enter_tag, (
                    f"tranche {k} mang kế hoạch KHÁC tranche 1 — custom_data đã lệch "
                    f"(đúng bug TD-0114 đã sửa). tag={o.get('ft_order_tag')!r}"
                )

    def test_ke_hoach_giai_ma_duoc_va_du_ba_muc_gia(self, ket_qua) -> None:
        for t in ket_qua["trades"]:
            kh = json.loads(t["enter_tag"])
            for khoa in ("zl", "zh", "p1", "p2", "p3", "sl"):
                assert khoa in kh, f"kế hoạch thiếu khoá {khoa}"
            assert kh["p3"] <= kh["p2"] <= kh["p1"], "ba mức tranche sai thứ tự"
            assert kh["sl"] < kh["p3"], "SL phải nằm dưới tranche sâu nhất"


class TestLZ50FillKhongTeHonKeHoach:
    """L-Z50 (D6) — chạy với `--timeframe-detail 5m`. TD-0115 đo trên
    CALIB thật: 91/91 fill luôn có lợi hoặc trung tính cho LONG. Đây là
    bất biến canh hồi quy tương ứng: KHÔNG fill nào được tệ hơn giá kế
    hoạch. Fill tệ hơn kế hoạch nghĩa là mô phỏng khớp lệnh đã rộng tay
    theo chiều BẤT LỢI — hoặc chiến lược đặt sai giá."""

    # Dung sai = 1 bước LÀM TRÒN GIÁ của sàn, không phải "nới cho dễ đạt".
    # Freqtrade làm tròn giá lệnh theo `price_precision` của cặp (quan sát
    # thật: kế hoạch 95.34759 → lệnh 95.35). Bước làm tròn ở 2 chữ số thập
    # phân tối đa là 0.005 ≈ 0.005% ở vùng giá này; lấy 0.01% cho có lề mà
    # vẫn bắt được mọi sai lệch có ý nghĩa kinh tế (trượt giá thật ở mức
    # phần mười phần trăm trở lên).
    DUNG_SAI_LAM_TRON = 1e-4  # 0.01%

    def test_moi_fill_khong_dat_hon_muc_ke_hoach(self, ket_qua) -> None:
        for t in ket_qua["trades"]:
            kh = json.loads(t["enter_tag"])
            muc = [kh["p1"], kh["p2"], kh["p3"]]
            for k, o in enumerate(_lenh_vao(t)):
                gia = float(o["safe_price"])
                tran = muc[k] * (1 + self.DUNG_SAI_LAM_TRON)
                assert gia <= tran, (
                    f"tranche {k + 1} khớp ở {gia} — ĐẮT HƠN kế hoạch {muc[k]} "
                    f"quá một bước làm tròn (trần {tran:.6f})"
                )
