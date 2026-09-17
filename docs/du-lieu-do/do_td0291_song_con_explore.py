"""TD-0291 — Cổng sống còn (`DR-SONG-CON-01`): Zone Absorption LONG trên EXPLORE, 0 trial.

Câu hỏi DUY NHẤT: *có đáng tiêu suất đo vào Zone Absorption LONG không?* Luật viết
TRƯỚC ở `DR-SONG-CON-01` §4 (`dd76a61`), thi hành ở `gates/song_con.py` (`79eaa0b`).
Script này KHÔNG quyết gì: nó chạy backtest, trích `R_trien_khai` từng lệnh, rồi gọi
đúng hàm luật đó.

🔴 Ranh giới (`DR-SONG-CON-01` §1): số ở đây KHÔNG vào YAML, KHÔNG chọn tham số, KHÔNG
xếp hạng arm, KHÔNG làm bằng chứng PASS ở cổng nào. EXPLORE ngoài sổ ngân sách
(DR-014 §2) — không `reserve()`, sổ trial không thêm dòng.

Đo:
  • `Z0-T1` (arm ứng viên) — áp luật.
  • `Z0-T0` — CHẨN ĐOÁN, chỉ mô tả, không áp luật.
  • EXPLORE 88 mã, MỘT lượt backtest `[T0, T2)`, cắt theo `open_date` thành CALIB `[T0,T1)` · WFO `[T1,T2)`.
  • `R_trien_khai = profit_abs / Σ amount·(giá khớp − sl)` trên lệnh vào ĐÃ KHỚP
    (`DR-D4-12` §1.4, qua `wfo.lenh.rui_ro_da_trien_khai_usdt`). `profit_abs` của Freqtrade
    futures đã trừ phí và cộng/trừ funding (`trade_model.py`, nhánh FUTURES) = `pnl_abs` DR-013.
  • `sl` đọc từ khoá `sl` trong JSON `enter_tag` (kế hoạch tính lại tại nến xác nhận §3.3b).
  • `R_realized` (mẫu số `planned_risk_usdt`): file xuất backtest KHÔNG mang `custom_data`
    ⇒ ghi `pending`, không suy.

Fail-closed (§3): một lệnh không trích được, backtest lỗi, hay có exception bị nuốt ⇒ CẢ
arm `unreadable`, không điền số từ phần chạy được.

Chạy trong Docker (N7):
  docker compose -f docker/docker-compose.yml run --rm freqtrade \
      docs/du-lieu-do/do_td0291_song_con_explore.py [--max-coins N] [--ket-qua PATH]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from tool_d.config.loader import load_tool_d_config  # noqa: E402
from tool_d.gates.dsr import effective_n  # noqa: E402
from tool_d.gates.song_con import KetLuanSongCon, ThongKe, danh_gia_song_con, thong_ke  # noqa: E402
from tool_d.ledger.timerange import dataset_boundaries_from_config  # noqa: E402
from tool_d.measurement.tri_state import Measured  # noqa: E402
from tool_d.wfo.folds import sinh_folds  # noqa: E402
from tool_d.wfo.lenh import TrancheKhop, rui_ro_da_trien_khai_usdt  # noqa: E402

_spec = importlib.util.spec_from_file_location("do_td0193", REPO / "docs" / "du-lieu-do" / "do_td0193_lenh_nam_explore.py")
td0193 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(td0193)

KET_QUA = REPO / "docs" / "du-lieu-do" / "td0291-song-con-explore.json"
DR = "DR-SONG-CON-01"
DR_SHA = "dd76a61"
LUAT_SHA = "79eaa0b"


class TrichLenhError(RuntimeError):
    """Một lệnh không trích được `R_trien_khai` — fail-closed cho cả arm."""


def _git(*args: str) -> str:
    r = subprocess.run(["git", "--no-optional-locks", *args], cwd=REPO, capture_output=True, text=True, timeout=60)
    return r.stdout.strip()


def _chay_backtest(ma: list[str], arm: str) -> tuple[list[dict], str]:
    """Khuôn `do_td0193.do_backtest`, nhưng TRẢ danh sách lệnh thay vì chỉ đếm."""
    tmp = Path(tempfile.mkdtemp(prefix=f"td0291_{arm}_"))
    try:
        td0193._yaml_voi_arm(arm, tmp)
        (tmp / "user_data" / "strategies").mkdir(parents=True)
        cfg = json.loads((REPO / "config" / "freqtrade" / "config.json").read_text(encoding="utf-8"))
        cfg["exchange"]["pair_whitelist"] = [m.replace("_USDT_USDT", "/USDT:USDT") for m in ma]
        cfg["dry_run"] = True
        (tmp / "cfg.json").write_text(json.dumps(cfg), encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, "-m", "freqtrade", "backtesting", "--config", str(tmp / "cfg.json"),
             "--datadir", str(td0193.THU_MUC.parent), "--userdir", str(tmp / "user_data"),
             "--strategy", "ZoneAbsorption", "--strategy-path", str(REPO / "user_data" / "strategies"),
             "--timerange", td0193.TIMERANGE, "--cache", "none", "--export", "trades"],
            capture_output=True, text=True, cwd=tmp, timeout=14400,
            env={**os.environ, "PYTHONPATH": str(REPO / "src")},
        )
        log = proc.stdout + proc.stderr
        if proc.returncode != 0:
            raise TrichLenhError(f"backtest {arm} rc={proc.returncode}: {log[-2000:]}")
        from freqtrade.data.btanalysis import load_backtest_stats

        files = sorted((tmp / "user_data" / "backtest_results").glob("backtest-result-*.zip"))
        trades = load_backtest_stats(files[-1])["strategy"]["ZoneAbsorption"]["trades"]
        return trades, log
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _r_trien_khai(t: dict) -> tuple[pd.Timestamp, float, float]:
    """(open_date UTC không múi giờ, pnl_abs, R_trien_khai) của MỘT lệnh; lỗi ⇒ raise."""
    try:
        sl = float(json.loads(t["enter_tag"])["sl"])
    except (KeyError, TypeError, ValueError) as e:
        raise TrichLenhError(f"{t.get('pair')} {t.get('open_date')}: enter_tag không có `sl` đọc được: {e!r}") from e
    khop = [
        TrancheKhop(stake_usdt=float(o["amount"]) * float(o["safe_price"]), entry=float(o["safe_price"]))
        for o in t["orders"]
        if o.get("ft_is_entry") and o.get("order_filled_timestamp") and float(o.get("amount") or 0) > 0
    ]
    try:
        rui_ro = rui_ro_da_trien_khai_usdt(khop, sl=sl)
    except ValueError as e:
        raise TrichLenhError(f"{t.get('pair')} {t.get('open_date')}: {e}") from e
    od = pd.Timestamp(t["open_date"])
    od = od.tz_convert("UTC").tz_localize(None) if od.tzinfo else od
    pnl = float(t["profit_abs"])
    return od, pnl, pnl / rui_ro


def _tk_dict(tk: ThongKe) -> dict:
    def m(x: Measured) -> object:
        return round(x.value, 6) if x.is_ok() else {"trang_thai": x.status.value, "ly_do": x.note}

    return {"n": tk.n, "mean": m(tk.mean), "std": m(tk.std), "ktc95_duoi": m(tk.ci_duoi), "ktc95_tren": m(tk.ci_tren)}


def do_arm(ma: list[str], arm: str, *, t1: pd.Timestamp, ap_luat: bool, ma_nam: float,
           so_ma_pool: int, nam_test: float, n_trials: int) -> dict:
    t0 = time.time()
    try:
        trades, log = _chay_backtest(ma, arm)
        nuot = sum(1 for d in log.splitlines() if "Strategy caused the following exception" in d)
        if nuot:
            raise TrichLenhError(f"{nuot} exception bị Freqtrade nuốt (MT-16 vii) — lệnh có thể đã mất im lặng")
        dong = [_r_trien_khai(t) for t in trades]
    except TrichLenhError as e:
        return {"arm": arm, "trang_thai": "unreadable", "ly_do": str(e), "giay": round(time.time() - t0, 1)}

    r_calib = [r for od, _, r in dong if od < t1]
    r_wfo = [r for od, _, r in dong if od >= t1]
    ra: dict = {
        "arm": arm,
        "vai_tro": "UNG_VIEN — áp luật §4" if ap_luat else "CHẨN ĐOÁN — chỉ mô tả, KHÔNG áp luật",
        "so_lenh": len(trades),
        "calib": _tk_dict(thong_ke(r_calib)),
        "wfo": _tk_dict(thong_ke(r_wfo)),
        "gop": _tk_dict(thong_ke(r_calib + r_wfo)),
        "ty_le_lenh_loi": round(sum(1 for _, p, _r in dong if p > 0) / len(dong), 4) if dong else None,
        "tong_pnl_abs_usdt": round(sum(p for _, p, _r in dong), 4),
        "exit_reason": dict(Counter(t["exit_reason"] for t in trades)),
        "phan_bo_tranche": dict(Counter(str(sum(1 for o in t["orders"] if o.get("ft_is_entry"))) for t in trades)),
        "r_realized": {"trang_thai": "pending", "ly_do": "file xuất backtest không mang custom_data (planned_risk_usdt)"},
        "exception_bi_nuot": 0,
        "giay": round(time.time() - t0, 1),
    }
    if ap_luat:
        kq = danh_gia_song_con(
            r_calib=r_calib, r_wfo=r_wfo, ma_nam=ma_nam, so_ma_pool=so_ma_pool, nam_test=nam_test, n_trials=n_trials,
        )
        ra["luat"] = {
            "ket_luan": kq.ket_luan.value,
            "ly_do": kq.ly_do,
            "n_cong": round(kq.n_cong.value, 3) if kq.n_cong.is_ok() else {"trang_thai": kq.n_cong.status.value, "ly_do": kq.n_cong.note},
            "M_can_N": round(kq.m_can.value, 6) if kq.m_can.is_ok() else {"trang_thai": kq.m_can.status.value, "ly_do": kq.m_can.note},
            "N": kq.n_trials,
            "M_union": {"trang_thai": "pending", "ly_do": "TD-0261 (overlap H14 / DR-007) chưa đo — kết luận ĐI (nếu có) chưa tính DR-007"},
        }
    print(f"[{arm}] {json.dumps(ra, ensure_ascii=False)}", flush=True)
    return ra


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-coins", type=int, default=0, help="CHỈ để thử máy; artifact thật chạy đủ mã")
    ap.add_argument("--ket-qua", default=None)
    a = ap.parse_args()
    ket_qua = Path(a.ket_qua) if a.ket_qua else KET_QUA
    if not ket_qua.is_absolute():
        ket_qua = REPO / ket_qua
    if a.max_coins and not a.ket_qua:
        print("🛑 --max-coins chỉ để thử máy — không ghi đè artifact thật; truyền --ket-qua", flush=True)
        return 2
    if ket_qua == KET_QUA and KET_QUA.exists():
        print("🛑 artifact thật đã tồn tại — DR §6: chạy lại chỉ theo luật chạy lại, ghi file MỚI", flush=True)
        return 3

    cfg = load_tool_d_config(REPO / "config" / "tool_d_config.yaml")
    b = dataset_boundaries_from_config(cfg)
    t0, t1, t2 = pd.Timestamp(b["CALIB"].start), pd.Timestamp(b["WFO"].start), pd.Timestamp(b["WFO"].end)
    assert f"{t0:%Y%m%d}-{t2:%Y%m%d}" == td0193.TIMERANGE, "cửa sổ td0193 lệch data_split niêm phong"
    folds = sinh_folds(cfg)
    nam_test = sum((f.test_end - f.test_start).days for f in folds) / 365
    so_ma_pool = len(td0193._ten_pool())
    n_trials = effective_n()

    ma = [m for m in td0193._cac_ma() if td0193._du_du_lieu(m)]
    if a.max_coins:
        ma = ma[: a.max_coins]
    ma_nam = sum(td0193._nam_phu(pd.read_feather(td0193.THU_MUC / f"{m}-1h-futures.feather")) for m in ma)
    print(f"EXPLORE {len(ma)} mã · {ma_nam:.2f} mã-năm · {td0193.TIMERANGE} · pool {so_ma_pool} · năm-test {nam_test:.4f} · N {n_trials}", flush=True)

    kq = {
        "nguon": f"TD-0291 — {DR} ({DR_SHA}), luật {LUAT_SHA}, EXPLORE, 0 trial",
        "chay_luc_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "git_sha": _git("rev-parse", "HEAD"),
        "cay_do_ban": [ln for ln in _git("status", "--porcelain").splitlines()
                       if ln[3:].split("/")[0] in {"src", "tests", "entrypoints", "config", "registry"}],
        "ranh_gioi": (
            "Cổng DỪNG, không phải phán quyết cổng (DR-D4-13 §1.2). Số KHÔNG vào YAML, KHÔNG chọn tham số, "
            "KHÔNG xếp hạng arm, KHÔNG làm bằng chứng PASS. EXPLORE ngoài sổ ngân sách (DR-014 §2). "
            "Người quyết ĐÃ nhìn thấy số này (DR-009)."
        ),
        "han_che": [
            "Không có dữ liệu 5m ⇒ không --timeframe-detail; thứ tự chạm SL/TP trong nến 1H là xấp xỉ, chiều lệch chưa biết",
            "EXPLORE ≠ pool: lợi thế trên 88 mã EXPLORE không chứng minh lợi thế trên 102 mã pool",
            "Cửa sổ WFO đã được D4 nhìn qua ĐẾM lệnh (TD-0193/0205/0212), chưa PnL",
            "Một cấu hình (Z0-T1, tham số hiện hành, chưa calibrate)",
            "N = 114; DR-007 union chưa đo (TD-0261)",
        ],
        "tham_so_luat": {
            "timerange": td0193.TIMERANGE, "T1": f"{t1:%Y-%m-%d}",
            "so_ma_explore": len(ma), "ma_nam_explore": round(ma_nam, 4),
            "so_ma_pool": so_ma_pool, "nam_test": round(nam_test, 6), "N": n_trials,
        },
        "Z0-T1": do_arm(ma, "Z0-T1", t1=t1, ap_luat=True, ma_nam=ma_nam, so_ma_pool=so_ma_pool, nam_test=nam_test, n_trials=n_trials),
        "Z0-T0": do_arm(ma, "Z0-T0", t1=t1, ap_luat=False, ma_nam=ma_nam, so_ma_pool=so_ma_pool, nam_test=nam_test, n_trials=n_trials),
    }
    ket_qua.write_text(json.dumps(kq, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"→ {ket_qua}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
