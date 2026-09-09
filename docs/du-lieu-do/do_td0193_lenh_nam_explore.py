"""Phép đo MÔ TẢ (0 trial) — DR-D4-08 §6: SỐ LỆNH/NĂM sau khi nối §3.3b (TD-0193).

Câu hỏi phải trả lời TRƯỚC khi `TD-0184` đặt chỗ 9 suất trial: hệ thống như
đang cấu hình có đủ mẫu để Nhánh 1 (§10.2, sàn 150 lệnh/năm) nói được gì
không? Trước TD-0193, `dg2-explore-quet-arm.json` cho Z0 83 lệnh / 48 mã /
21,7 tháng ≈ 46 lệnh/năm ⇒ quy đổi thô pool 102 mã ≈ 97/năm — DƯỚI sàn.

🔴 Chạy trên tập **EXPLORE** (`user_data/data/explore/`), KHÔNG phải pool.
`DR-D0PRE-05` §4: EXPLORE dùng để SINH giả thuyết, 0 trial, ngoài phạm vi
DR-014 (đường vòng hợp lệ MT-19). **CHỈ ĐẾM**: số zone, số nến xác nhận,
số tín hiệu sau bộ lọc trend, số lệnh, phân bố tranche/`wait_bars`/nhánh
xác nhận, tỉ lệ TP theo nguồn. **KHÔNG** expectancy, **KHÔNG** PnL theo arm
— DR-D0PRE-05 cấm dùng EXPLORE để validate.

Hai tầng đo, cố ý tách:
  (i)  PHỄU TÍN HIỆU — gọi thẳng các phương thức SẢN XUẤT của `ZoneAbsorption`
       (`_tinh_zone_4h` → `_xac_nhan_3_3b` → `populate_entry_trend`), không
       phụ thuộc vốn/kết nạp. Trả lời: §3.3b cắt bao nhiêu, trend cắt bao nhiêu.
  (ii) LỆNH THẬT — `freqtrade backtesting` với cấu hình THẬT (E_D, kết nạp
       §6.8f, sàn DR-D4-05). Trả lời: hệ thống như sẽ chạy cho bao nhiêu lệnh.
       ⚠️ EXPLORE không có dữ liệu 5m ⇒ chạy KHÔNG `--timeframe-detail`; khớp
       lệnh/TP ở độ phân giải 1H — đủ để ĐẾM lệnh, không đủ để nói về TP.

Chạy trong Docker (N7):
  docker compose -f docker/docker-compose.yml run --rm freqtrade \
      docs/du-lieu-do/do_td0193_lenh_nam_explore.py [--arms Z3,Z0] [--max-coins N]
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import talib

REPO = Path(__file__).resolve().parents[2]
THU_MUC = REPO / "user_data" / "data" / "explore" / "futures"
KET_QUA = REPO / "docs" / "du-lieu-do" / "td0193-lenh-nam-explore.json"

# Mốc CALIB/WFO đã niêm phong (TD-0084, `lockbox/lockbox_seal_1.json`): T0 = 09/04/2024,
# T2 = 29/01/2026. Cùng cửa sổ [T0,T2] mà `dg2-explore-quet-arm.json` dùng.
T0, T2 = pd.Timestamp("2024-04-09", tz="UTC"), pd.Timestamp("2026-01-29", tz="UTC")
TIMERANGE = f"{T0:%Y%m%d}-{T2:%Y%m%d}"
POOL_SIZE = 102  # để quy đổi thô — EXPLORE ≠ pool, chỉ là tỉ lệ


def _chien_luoc(arm: str):
    sys.path.insert(0, str(REPO / "user_data" / "strategies"))
    from tool_d.arms import tang_cua_arm
    from tool_d.entry_confirmation import bat_dieu_kien_c_cua_arm
    from ZoneAbsorption import ZoneAbsorption

    s = ZoneAbsorption(config={"stake_currency": "USDT", "exchange": {"name": "binance"}})
    # Ba thuộc tính __init__ suy từ arm — đặt lại như thể YAML ghi arm này.
    s._arm = arm
    s._bat_dieu_kien_c = bat_dieu_kien_c_cua_arm(arm)
    s._tang_loc_trend = tang_cua_arm(arm)
    return s


def _cac_ma() -> list[str]:
    ma = []
    for f in sorted(THU_MUC.glob("*-1h-futures.feather")):
        ten = f.name.replace("-1h-futures.feather", "")
        if all((THU_MUC / f"{ten}-{k}.feather").exists() for k in ("4h-futures", "1d-futures", "1h-mark", "1h-funding_rate")):
            ma.append(ten)
    return ma


def _nam_phu(df1: pd.DataFrame) -> float:
    if df1.empty:
        return 0.0
    a, b = max(df1["date"].iloc[0], T0), min(df1["date"].iloc[-1], T2)
    return max((b - a).total_seconds() / (365.25 * 86400), 0.0)


def _du_du_lieu(ten: str) -> bool:
    """Cùng một bộ lọc cho CẢ HAI tầng đo — phễu và backtest phải đếm trên
    cùng tập mã, nếu không mẫu số `ma_nam` lệch nhau (lần chạy đầu vỡ ở đúng
    chỗ này: một mã có file 1H rỗng lọt vào tầng backtest)."""
    df1 = pd.read_feather(THU_MUC / f"{ten}-1h-futures.feather")
    df4 = pd.read_feather(THU_MUC / f"{ten}-4h-futures.feather")
    df1d = pd.read_feather(THU_MUC / f"{ten}-1d-futures.feather")
    return len(df1) >= 1200 and len(df4) >= 60 and len(df1d) >= 60 and _nam_phu(df1) > 0


def do_pheu(ma: list[str], arms: list[str]) -> dict:
    from freqtrade.strategy import merge_informative_pair

    ra: dict = {}
    for arm in arms:
        s = _chien_luoc(arm)
        tong = Counter()
        wb, ec, lc = Counter(), Counter(), Counter()
        nam = 0.0
        t0 = time.time()
        for ten in ma:
            df1 = pd.read_feather(THU_MUC / f"{ten}-1h-futures.feather")
            df4 = pd.read_feather(THU_MUC / f"{ten}-4h-futures.feather")
            df1d = pd.read_feather(THU_MUC / f"{ten}-1d-futures.feather")
            nam += _nam_phu(df1)
            d = df1.copy()
            d["atr_1h"] = talib.ATR(d["high"], d["low"], d["close"], timeperiod=14)
            d["rsi_1h"] = talib.RSI(d["close"], timeperiod=14)
            d["volume_ma_1h"] = d["volume"].rolling(20).mean()
            inf4 = s._tinh_zone_4h(df4.copy())
            s._xac_nhan_3_3b(d, inf4, ten)
            d = merge_informative_pair(d, inf4, "1h", "4h", ffill=True)
            inf1d = s._tinh_trend_1d(df1d.copy())
            d = merge_informative_pair(d, inf1d[["date", "adx", "trend_dir_1d", "tuoi_trend_1d"]], "1h", "1d", ffill=True)
            d = s.populate_entry_trend(d, {"pair": ten})
            trong = (d["date"] >= T0) & (d["date"] <= T2)
            # zone: đếm nến 4H xác nhận rơi trong cửa sổ
            z4 = inf4[(inf4["date"] >= T0) & (inf4["date"] <= T2)]
            tong["zone"] += int(z4["zone_valid"].sum())
            tong["A"] += int(d.loc[trong, "xac_nhan_3_3b"].sum())
            tong["B"] += int(d.loc[trong, "xac_nhan_phan_thuc_b"].sum())
            tong["tin_hieu_sau_trend"] += int(d.loc[trong, "enter_long"].fillna(0).sum()) if "enter_long" in d else 0
            for tag in d.loc[trong & d["xac_nhan_3_3b"].astype(bool), "ke_hoach_json_3_3b"]:
                j = json.loads(tag)
                wb[j["wb"]] += 1; ec[j["ec"]] += 1; lc[j["lc"]] += 1
        ra[arm] = {
            "so_ma": len(ma), "ma_nam": round(nam, 2),
            "zone": tong["zone"], "A_xac_nhan": tong["A"], "B_phan_thuc": tong["B"],
            "tin_hieu_sau_trend": tong["tin_hieu_sau_trend"],
            "ty_le_A_tren_zone": round(tong["A"] / tong["zone"], 4) if tong["zone"] else None,
            "ty_le_B_tren_zone": round(tong["B"] / tong["zone"], 4) if tong["zone"] else None,
            "tin_hieu_moi_ma_nam": round(tong["tin_hieu_sau_trend"] / nam, 3) if nam else None,
            "tin_hieu_quy_doi_pool_102_moi_nam": round(tong["tin_hieu_sau_trend"] / nam * POOL_SIZE, 1) if nam else None,
            "phan_bo_wait_bars": dict(sorted(wb.items())),
            "phan_bo_nhanh_xac_nhan": dict(ec),
            "phan_bo_luot_cham_phan_thuc_B": dict(sorted(lc.items())),
            "giay": round(time.time() - t0, 1),
        }
        print(f"[phễu] {arm}: {ra[arm]}", flush=True)
    return ra


def _yaml_voi_arm(arm: str, dest: Path) -> None:
    """Chép TOÀN BỘ `config/` sang cwd tạm, chỉ đổi đúng dòng `arm:` — loader
    đọc `config/tool_d_config.yaml` tương đối cwd, nên đây là cách đổi arm mà
    KHÔNG chạm file trong repo (đúng cách E3/TD-0184 sẽ ghi đè theo từng arm)."""
    shutil.copytree(REPO / "config", dest / "config")
    y = dest / "config" / "tool_d_config.yaml"
    src = y.read_text(encoding="utf-8")
    dong = [ln for ln in src.splitlines() if ln.strip().startswith("arm:")]
    assert len(dong) == 1, dong
    y.write_text(src.replace(dong[0], f'    arm: "{arm}"'), encoding="utf-8")


def do_backtest(ma: list[str], arm: str) -> dict:
    tmp = Path(tempfile.mkdtemp(prefix=f"td0193_{arm}_"))
    _yaml_voi_arm(arm, tmp)
    (tmp / "user_data" / "strategies").mkdir(parents=True)
    cfg = json.loads((REPO / "config" / "freqtrade" / "config.json").read_text(encoding="utf-8"))
    cfg["exchange"]["pair_whitelist"] = [m.replace("_USDT_USDT", "/USDT:USDT") for m in ma]
    cfg["dry_run"] = True
    (tmp / "cfg.json").write_text(json.dumps(cfg), encoding="utf-8")
    t0 = time.time()
    proc = subprocess.run(
        [sys.executable, "-m", "freqtrade", "backtesting", "--config", str(tmp / "cfg.json"),
         "--datadir", str(THU_MUC.parent), "--userdir", str(tmp / "user_data"),
         "--strategy", "ZoneAbsorption", "--strategy-path", str(REPO / "user_data" / "strategies"),
         "--timerange", TIMERANGE, "--cache", "none", "--export", "trades"],
        capture_output=True, text=True, cwd=tmp, timeout=7200,
        env={**__import__("os").environ, "PYTHONPATH": str(REPO / "src")},
    )
    log = proc.stdout + proc.stderr
    nuot = [d for d in log.splitlines() if "Strategy caused the following exception" in d]
    if proc.returncode != 0:
        print(log[-4000:])
        raise SystemExit(f"backtest {arm} rc={proc.returncode}")
    from freqtrade.data.btanalysis import load_backtest_stats

    files = sorted((tmp / "user_data" / "backtest_results").glob("backtest-result-*.zip"))
    kq = load_backtest_stats(files[-1])["strategy"]["ZoneAbsorption"]
    trades = kq["trades"]
    n_tranche = Counter(len([o for o in t["orders"] if o.get("ft_is_entry")]) for t in trades)
    ly_do = Counter(t["exit_reason"] for t in trades)
    tp1 = Counter(
        o.get("ft_order_tag") for t in trades for o in t["orders"]
        if not o.get("ft_is_entry") and str(o.get("ft_order_tag", "")).startswith("TP1_")
    )
    nam = sum(_nam_phu(pd.read_feather(THU_MUC / f"{m}-1h-futures.feather")) for m in ma)
    ra = {
        "so_ma": len(ma), "ma_nam": round(nam, 2), "so_lenh": len(trades),
        "lenh_moi_ma_nam": round(len(trades) / nam, 3) if nam else None,
        "lenh_quy_doi_pool_102_moi_nam": round(len(trades) / nam * POOL_SIZE, 1) if nam else None,
        "phan_bo_tranche": {str(k): v for k, v in sorted(n_tranche.items())},
        "exit_reason": dict(ly_do),
        "tp1_theo_nguon": dict(tp1),
        "exception_bi_nuot": len(nuot),
        "giay": round(time.time() - t0, 1),
        "ghi_chu": "KHÔNG --timeframe-detail (EXPLORE không có 5m); chỉ đếm, không PnL",
    }
    print(f"[backtest] {arm}: {ra}", flush=True)
    shutil.rmtree(tmp, ignore_errors=True)
    return ra


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", default="Z3,Z0")
    ap.add_argument("--max-coins", type=int, default=0)
    ap.add_argument("--skip-backtest", action="store_true")
    a = ap.parse_args()
    arms = a.arms.split(",")
    ma = [m for m in _cac_ma() if _du_du_lieu(m)]
    if a.max_coins:
        ma = ma[: a.max_coins]
    print(f"EXPLORE: {len(ma)} mã đủ file · timerange {TIMERANGE} · arms {arms}", flush=True)
    kq = {
        "nguon": "phiên be, 09/09/2026 — TD-0193/DR-D4-08 §6, tập EXPLORE, 0 trial",
        "ranh_gioi": "CHỈ đếm zone/xác nhận/tín hiệu/lệnh và phân bố. KHÔNG expectancy, KHÔNG PnL theo arm (DR-D0PRE-05 §4).",
        "timerange": TIMERANGE, "san_nhanh_1": 150,
        "pheu_tin_hieu": do_pheu(ma, arms),
    }
    if not a.skip_backtest:
        kq["lenh_that"] = {arm: do_backtest(ma, arm) for arm in arms}
    KET_QUA.write_text(json.dumps(kq, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"→ {KET_QUA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
