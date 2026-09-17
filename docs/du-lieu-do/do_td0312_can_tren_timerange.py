"""Phép đo MÔ TẢ (0 trial) — `TD-0312` / `DR-BC-01` §6.1: cận trên của `--timerange`
Freqtrade là BAO GỒM hay KHÔNG BAO GỒM nến đúng tại mốc, và dạng unix giây có nhận không?

🔴 **Vì sao phải đo chứ không đọc tài liệu rồi tin.** Dữ liệu rổ `T1` kết thúc đúng
`2026-01-29 00:00 UTC` = `T2`, trong khi `kiem_pham_vi_du_lieu()` (`wfo/folds.py:244`)
chỉ cho `observed_end` tới `test_end − 1 ngày`. Nếu cận trên là BAO GỒM thì fold cuối
**luôn** raise `TimerangeViolationError`; nếu KHÔNG BAO GỒM thì nó vừa khít. Lệch một
ngày ở đây là **một ngày dữ liệu tương lai** — đúng lớp lỗi TD-0093.

**Cách phân biệt (điểm then chốt):** dữ liệu phải kéo dài **QUÁ** mốc yêu cầu. Nếu dữ
liệu dừng đúng tại mốc thì `backtest_end` bị kẹp bởi dữ liệu chứ không bởi `--timerange`,
và phép đo không phân biệt được hai giả thuyết — nó cho cùng một con số trong cả hai
trường hợp. (Đây chính là chỗ bản đầu suýt sai: fixture `L-Z49` dừng TRƯỚC mốc yêu cầu
nên `backtest_end` của nó **không** nói gì về tính bao gồm.)

  dữ liệu : 2024-12-01 00:00  →  2025-01-25 00:00   (kéo QUÁ mốc 5 ngày)

  ca A — `--timerange 20241215-20250120` (dạng ngày)
     BAO GỒM      ⇒ backtest_end = 2025-01-20 00:00
     KHÔNG BAO GỒM⇒ backtest_end = 2025-01-19 23:00

  ca B — cùng cửa sổ nhưng cận trên lùi **1 giây**, truyền bằng unix giây.
     Hỏi hai thứ cùng lúc: Freqtrade có NHẬN dạng unix giây không, và nếu nhận thì
     nó có cắt đúng nến `23:00` không. Đây là dạng mà bộ chạy cần cho cửa sổ NỬA MỞ
     `[tu, den)` của `Fold` — dạng ngày sẽ thừa đúng một nến.

Giá phẳng, volume đều: phép đo này chỉ hỏi về BIÊN THỜI GIAN, không hỏi về lệnh.
**0 lệnh là kết quả hợp lệ ở đây** (khác `L-Z49`, nơi 0 lệnh là pass rỗng) — biên thời
gian do engine cắt dữ liệu quyết định, không do chiến lược có vào lệnh hay không.

Chạy trong Docker (N7):
  docker compose -f docker/docker-compose.yml run --rm freqtrade \
      docs/du-lieu-do/do_td0312_can_tren_timerange.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
KET_QUA = REPO / "docs" / "du-lieu-do" / "td0312-can-tren-timerange.json"
CAP = "BTC_USDT_USDT"
CHIEN_LUOC = "ZoneAbsorptionMinimal"  # startup 200 nến 1H, nhẹ hơn ZoneAbsorption (1000)

DU_LIEU_TU = "2024-12-01"
DU_LIEU_DEN = "2025-01-25"  # KÉO QUÁ mốc yêu cầu — xem docstring
XIN_TU = pd.Timestamp("2024-12-15", tz="UTC")
XIN_DEN = pd.Timestamp("2025-01-20", tz="UTC")  # cận trên "không bao gồm" mà ta MUỐN


def _ghi(df: pd.DataFrame, duong: Path) -> None:
    duong.parent.mkdir(parents=True, exist_ok=True)
    df.reset_index(drop=True).to_feather(duong)


def _sinh_du_lieu(datadir: Path) -> pd.Timestamp:
    """Giá phẳng, volume đều. Trả về mốc nến 1H CUỐI CÙNG có trong dữ liệu."""
    idx1 = pd.date_range(DU_LIEU_TU, DU_LIEU_DEN, freq="1h", tz="UTC")
    df1 = pd.DataFrame(
        {"date": idx1, "open": 100.0, "high": 100.5, "low": 99.5, "close": 100.0, "volume": 1000.0}
    )

    r = (
        df1.set_index("date")
        .resample("4h")
        .agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
        .reset_index()
    )
    # Chuỗi 4H bắt đầu TRƯỚC 1H (cùng lý do đã ghi ở `test_lz49_lz50_backtest_nho.py`:
    # nến 1h đầu chưa có nến 4h nào đóng ⇒ cột informative NaN ⇒ chiến lược vỡ khi mask).
    dem = r.iloc[[0, 0]].copy()
    dem["date"] = [idx1[0] - pd.Timedelta(hours=8), idx1[0] - pd.Timedelta(hours=4)]
    r = pd.concat([dem, r], ignore_index=True)

    d = datadir / "futures"
    _ghi(df1, d / f"{CAP}-1h-futures.feather")
    _ghi(df1, d / f"{CAP}-1h-mark.feather")
    _ghi(r, d / f"{CAP}-4h-futures.feather")
    fund = pd.DataFrame(
        {"date": idx1, "open": 0.0, "high": 0.0, "low": 0.0, "close": 0.0, "volume": 0.0}
    )
    _ghi(fund, d / f"{CAP}-1h-funding_rate.feather")
    return idx1[-1]


def _utc(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000, timezone.utc)


def _chay(tmp: Path, datadir: Path, timerange: str, nhan: str) -> dict:
    """Một lượt backtest, trả về đúng những gì đọc được. Không diễn giải ở đây."""
    userdir = tmp / f"userdir_{nhan}"
    (userdir / "strategies").mkdir(parents=True, exist_ok=True)

    cfg = json.loads((REPO / "config" / "freqtrade" / "config.json").read_text(encoding="utf-8"))
    cfg["exchange"]["pair_whitelist"] = ["BTC/USDT:USDT"]
    cfg["dry_run"] = True
    cfg_path = tmp / f"cfg_{nhan}.json"
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable, "-m", "freqtrade", "backtesting",
            "--config", str(cfg_path),
            "--datadir", str(datadir),
            "--userdir", str(userdir),
            "--strategy", CHIEN_LUOC,
            "--strategy-path", str(REPO / "user_data" / "strategies"),
            "--timerange", timerange,
            "--cache", "none",
            "--export", "trades",
        ],
        capture_output=True, text=True, timeout=1800,
    )
    if proc.returncode != 0:
        # Ca B có thể hỏng vì Freqtrade KHÔNG nhận dạng unix giây — đó cũng là một
        # kết quả đo, không phải sự cố. Ghi lại thay vì raise.
        return {
            "timerange_truyen": timerange,
            "returncode": proc.returncode,
            "loi": (proc.stdout + proc.stderr)[-1200:],
        }

    from freqtrade.data.btanalysis import load_backtest_stats

    files = sorted((userdir / "backtest_results").glob("backtest-result-*.zip"))
    kq = load_backtest_stats(files[-1])["strategy"][CHIEN_LUOC]
    return {
        "timerange_truyen": timerange,
        "returncode": 0,
        "timerange_trong_bao_cao": kq.get("timerange"),
        "backtest_start": str(_utc(kq["backtest_start_ts"])),
        "backtest_end": str(_utc(kq["backtest_end_ts"])),
        "so_lenh": kq.get("total_trades"),
    }


def _ket_luan_can_tren(ca_a: dict) -> str:
    """N6: không ép về một trong hai nhãn khi số không khớp giả thuyết nào."""
    if ca_a.get("returncode") != 0:
        return "KHONG_DOC_DUOC"
    ket_thuc = pd.Timestamp(ca_a["backtest_end"])
    if ket_thuc == XIN_DEN:
        return "BAO_GOM"
    if ket_thuc == XIN_DEN - pd.Timedelta(hours=1):
        return "KHONG_BAO_GOM"
    return "KHONG_DOC_DUOC"


def _ket_luan_unix(ca_b: dict) -> str:
    if ca_b.get("returncode") != 0:
        return "KHONG_NHAN_DANG_UNIX"
    ket_thuc = pd.Timestamp(ca_b["backtest_end"])
    if ket_thuc == XIN_DEN - pd.Timedelta(hours=1):
        return "NHAN_VA_CAT_DUNG"
    if ket_thuc == XIN_DEN:
        return "NHAN_NHUNG_VAN_BAO_GOM"
    return "KHONG_DOC_DUOC"


def do() -> dict:
    tmp = Path(tempfile.mkdtemp(prefix="td0312_"))
    datadir = tmp / "data"
    nen_cuoi = _sinh_du_lieu(datadir)

    tr_a = f"{XIN_TU:%Y%m%d}-{XIN_DEN:%Y%m%d}"
    tr_b = f"{int(XIN_TU.timestamp())}-{int(XIN_DEN.timestamp()) - 1}"

    ca_a = _chay(tmp, datadir, tr_a, "a")
    ca_b = _chay(tmp, datadir, tr_b, "b")

    return {
        "_doc": "TD-0312 / DR-BC-01 §6.1 — can tren cua --timerange. 0 trial, du lieu tu dung.",
        "chien_luoc": CHIEN_LUOC,
        "du_lieu_tu": DU_LIEU_TU,
        "du_lieu_den": DU_LIEU_DEN,
        "nen_1h_cuoi_trong_du_lieu": str(nen_cuoi),
        "cua_so_muon_do": {
            "tu_bao_gom": str(XIN_TU),
            "den_KHONG_bao_gom": str(XIN_DEN),
            "nen_cuoi_dung_ra_phai_doc": str(XIN_DEN - pd.Timedelta(hours=1)),
        },
        "ca_a_dang_ngay": ca_a,
        "ca_b_dang_unix_giay_lui_1s": ca_b,
        "ket_luan_can_tren": _ket_luan_can_tren(ca_a),
        "ket_luan_dang_unix": _ket_luan_unix(ca_b),
        "_giai_thich": {
            "BAO_GOM": f"backtest_end == {XIN_DEN} — nen tai moc ĐƯỢC tinh",
            "KHONG_BAO_GOM": f"backtest_end == {XIN_DEN - pd.Timedelta(hours=1)} — nen tai moc BI LOAI",
            "NHAN_VA_CAT_DUNG": "dang unix giay dung duoc cho cua so NUA MO cua Fold",
            "KHONG_NHAN_DANG_UNIX": "Freqtrade tu choi dang unix giay — phai dung duong khac",
        },
    }


if __name__ == "__main__":
    ra = do()
    KET_QUA.write_text(json.dumps(ra, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(ra, indent=2, ensure_ascii=False))
    print(f"\n-> {KET_QUA}")
