"""TD-0184 (lô `DR-D4-19`, sau lượt 2 — `708a268`, `1a4d084`) — đếm lệnh bị Freqtrade KẸP GIÁ, EXPLORE, 0 trial.

Câu hỏi DUY NHẤT (chủ dự án chọn "đo cả hai trước", 19/09/2026): nếu chiến lược từ chối tranche 1 giống sàn từ chối
post-only (spec §3.5 LD-13), MỖI mức luật cắt bao nhiêu lệnh?

  • Mức HẸP      — cả nến lúc đặt nằm dưới `p1` ⇒ Freqtrade kẹp `min(p1, high)` và khớp ở đỉnh nến
                   (`backtesting.py get_valid_entry_price_and_stake`, Freqtrade 2026.8). Đúng loại lệnh làm hỏng lượt 2.
  • Mức ĐÚNG SPEC — giá mở lúc đặt < `p1` ⇒ lệnh post-only mua tại `p1` nằm trên thị trường ⇒ sàn từ chối.

🔑 EXPLORE KHÔNG có dữ liệu 5m (0 file), còn E3 chạy `--timeframe-detail 5m`. Khi có detail, Freqtrade mở lệnh ở nến
5m ĐẦU của nến chính (`time_pair_generator`), nên:
  • ĐÚNG SPEC không phụ thuộc detail (nến 5m đầu cùng giá MỞ với nến 1H);
  • HẸP đo ở 1H là CẬN DƯỚI: đỉnh 5m ≤ đỉnh 1H ⇒ `hep(1H) ≤ hep(5m) ≤ dung_spec`.

Cùng khuôn `do_td0291_song_con_explore.py` (dùng lại `_chay_backtest`): CHỈ CALIB `[T0, T1)` (`DR-SONG-CON-01` §8 cấm
đọc WFO trên EXPLORE), ngoài sổ ngân sách (DR-014 §2), không `reserve()`. **Chỉ ĐẾM** — không đọc PnL, không xếp hạng
arm. Số là bậc một: lệnh bị bỏ sẽ nhường chỗ/vốn cho lệnh khác, phần đó chỉ thấy khi chạy lại với luật đã chọn.

Chạy trong Docker (N7):
  docker compose -f docker/docker-compose.yml run --rm freqtrade docs/du-lieu-do/do_td0184_kep_gia_explore.py
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from tool_d.config.loader import load_tool_d_config  # noqa: E402
from tool_d.ledger.timerange import dataset_boundaries_from_config  # noqa: E402

_spec = importlib.util.spec_from_file_location("do_td0291", REPO / "docs" / "du-lieu-do" / "do_td0291_song_con_explore.py")
td0291 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(td0291)
td0193 = td0291.td0193

KET_QUA = REPO / "docs" / "du-lieu-do" / "td0184-kep-gia-explore.json"
ARMS = ("Z0-T1", "Z0", "Z0-T0", "Z3")  # lô `DR-D4-12` §4
_EPS = 1e-9


class DemError(RuntimeError):
    """Một lệnh không đọc được — fail-closed cho cả arm."""


def _nen_1h(ma: str, cache: dict) -> pd.DataFrame:
    if ma not in cache:
        df = pd.read_feather(td0193.THU_MUC / f"{ma}-1h-futures.feather")
        df["date"] = pd.to_datetime(df["date"], utc=True)
        cache[ma] = df.set_index("date")
    return cache[ma]


def _dem_mot_lenh(t: dict, cache: dict) -> dict:
    try:
        tag = json.loads(t["enter_tag"])
        p = [float(tag["p1"]), float(tag["p2"]), float(tag["p3"])]
        sl = float(tag["sl"])
    except (KeyError, TypeError, ValueError) as e:
        raise DemError(f"{t.get('pair')} {t.get('open_date')}: enter_tag không đọc được: {e!r}") from e
    vao = sorted(
        (o for o in t["orders"] if o.get("ft_is_entry") and o.get("order_filled_timestamp") and float(o.get("amount") or 0) > 0),
        key=lambda o: int(o["order_filled_timestamp"]),
    )
    if not vao:
        raise DemError(f"{t.get('pair')} {t.get('open_date')}: không có tranche nào khớp")
    ma = t["pair"].replace("/USDT:USDT", "_USDT_USDT")
    df = _nen_1h(ma, cache)
    # Export backtest là bản RÚT GỌN (`Order.to_json(minified=True)`: không có `order_timestamp`). Tranche 1 được đặt
    # tại nến tạo trade (`_enter_trade` → `LocalTrade(open_date=current_time)`), nên mốc đặt = `open_date` của trade.
    dat = pd.Timestamp(t["open_date"])
    dat = (dat.tz_convert("UTC") if dat.tzinfo else dat.tz_localize("UTC")).floor("1h")
    if dat not in df.index:
        raise DemError(f"{t['pair']}: không có nến 1H lúc đặt {dat}")
    nen = df.loc[dat]
    gia1 = float(vao[0]["safe_price"])
    ra = {
        # Kẹp: khớp ĐÚNG đỉnh nến và đỉnh nến dưới p1 (so với đỉnh thay vì với p1 để không lẫn làm tròn theo bước giá).
        "t1_hep": float(nen["high"]) < p[0] and math.isclose(gia1, float(nen["high"]), rel_tol=_EPS),
        "t1_dung_spec": float(nen["open"]) < p[0] * (1 - _EPS),
        "t1_duoi_sl": gia1 <= sl,
        "t23_kep": 0,
        "t23_duoi_sl": 0,
    }
    for k, o in enumerate(vao[1:3], start=1):
        g = float(o["safe_price"])
        ra["t23_kep"] += g < p[k] * (1 - 1e-6)
        ra["t23_duoi_sl"] += g <= sl
    return ra


def do_arm(ma: list[str], arm: str, t0: pd.Timestamp, t1: pd.Timestamp) -> dict:
    bam = time.time()
    try:
        trades, log = td0291._chay_backtest(ma, arm)
        nuot = sum(1 for d in log.splitlines() if "Strategy caused the following exception" in d)
        if nuot:
            raise DemError(f"{nuot} exception bị Freqtrade nuốt (MT-16 vii)")
        cache: dict = {}
        dem = []
        for t in trades:
            od = pd.Timestamp(t["open_date"])
            od = od.tz_convert("UTC").tz_localize(None) if od.tzinfo else od
            if not (t0 <= od < t1):
                raise DemError(f"lệnh mở ngoài CALIB [T0,T1): {od} — §8 cấm đọc WFO")
            dem.append((t, _dem_mot_lenh(t, cache)))
    except (DemError, td0291.TrichLenhError) as e:
        return {"arm": arm, "trang_thai": "unreadable", "ly_do": str(e), "giay": round(time.time() - bam, 1)}

    n = len(dem)

    def _dem(khoa: str) -> int:
        return int(sum(d[khoa] for _, d in dem))

    def _vd(khoa: str) -> list[str]:
        return [f"{t['pair']} {t['open_date']}" for t, d in dem if d[khoa]][:3]

    ra = {
        "arm": arm,
        "so_lenh": n,
        "so_lenh_nhieu_tranche": sum(1 for t, _ in dem if sum(1 for o in t["orders"] if o.get("ft_is_entry")) > 1),
        "tranche1": {
            k: {"so_lenh": _dem(k), "ty_le": round(_dem(k) / n, 4) if n else None, "vi_du": _vd(k)}
            for k in ("t1_hep", "t1_dung_spec", "t1_duoi_sl")
        },
        "tranche23": {"so_tranche_khop_duoi_muc": _dem("t23_kep"), "so_tranche_duoi_sl": _dem("t23_duoi_sl")},
        "giay": round(time.time() - bam, 1),
    }
    print(f"[{arm}] {json.dumps(ra, ensure_ascii=False)}", flush=True)
    return ra


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-coins", type=int, default=0, help="CHỈ để thử máy")
    ap.add_argument("--ket-qua", default=None)
    a = ap.parse_args()
    ket_qua = Path(a.ket_qua) if a.ket_qua else KET_QUA
    if not ket_qua.is_absolute():
        ket_qua = REPO / ket_qua
    if a.max_coins and not a.ket_qua:
        print("🛑 --max-coins chỉ để thử máy — truyền --ket-qua", flush=True)
        return 2
    if ket_qua == KET_QUA and KET_QUA.exists():
        print("🛑 artifact đã tồn tại — ghi file MỚI", flush=True)
        return 3

    cfg = load_tool_d_config(REPO / "config" / "tool_d_config.yaml")
    b = dataset_boundaries_from_config(cfg)
    t0, t1 = pd.Timestamp(b["CALIB"].start), pd.Timestamp(b["CALIB"].end)
    assert f"{t0:%Y%m%d}" == f"{td0193.T0:%Y%m%d}", "T0 của td0193 lệch data_split niêm phong"
    td0193.T2 = pd.Timestamp(t1, tz="UTC")
    td0193.TIMERANGE = f"{td0193.T0:%Y%m%d}-{td0193.T2:%Y%m%d}"

    ma = [m for m in td0193._cac_ma() if td0193._du_du_lieu(m)]
    if a.max_coins:
        ma = ma[: a.max_coins]
    print(f"EXPLORE {len(ma)} mã · {td0193.TIMERANGE} · 1H (không có 5m) · 0 trial", flush=True)

    ket = {arm: do_arm(ma, arm, t0, t1) for arm in ARMS}
    ra = {
        "nguon": "TD-0184 — đếm lệnh bị kẹp giá (DR-D4-19, sau lượt 2 708a268), EXPLORE CALIB [T0,T1), 0 trial",
        "chay_luc_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "git_sha": td0291._git("rev-parse", "HEAD"),
        "cay_sach": td0291._git("status", "--porcelain", "--untracked-files=no") == "",
        "so_ma_explore": len(ma),
        "cua_so": [f"{t0:%Y-%m-%d}", f"{t1:%Y-%m-%d}"],
        "timeframe_detail": None,
        "doc_dung": (
            "t1_hep ở 1H là CẬN DƯỚI của mức HẸP khi chạy 5m; t1_dung_spec không phụ thuộc detail. "
            "Bậc một: không tính lệnh khác lấp chỗ lệnh bị bỏ."
        ),
        "arm": ket,
    }
    ket_qua.write_text(json.dumps(ra, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"→ {ket_qua.relative_to(REPO)}", flush=True)
    return 0 if all(v.get("trang_thai") != "unreadable" for v in ket.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
