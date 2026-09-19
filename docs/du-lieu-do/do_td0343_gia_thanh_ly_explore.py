"""TD-0343 — export backtest trên dữ liệu THẬT có `liquidation_price` không? EXPLORE, 0 trial.

Câu hỏi DUY NHẤT: `liq_buffer_ratio_mean` (TD-0342, spec `:1866`) có nguồn số khi D4 đo thật không? Trên fixture
TỔNG HỢP, `liquidation_price` ra `None`. Chẩn đoán ban đầu (*"thiếu bảng bậc đòn bẩy"*) có thể SAI: bảng
`binance_leverage_tiers.json` có trong image, lệnh fixture vẫn nhận đòn bẩy 3x, và log không có cảnh báo
*"Unable to calculate liquidation price"* của `update_liquidation_prices`. Nên đo TÁCH HAI tầng:

  (a) SÀN ẢO có tính được giá thanh lý không — gọi thẳng `Exchange.get_liquidation_price()` ngoài backtest;
  (b) BACKTEST có GHI giá đó vào lệnh không — đếm `trades[*].liquidation_price` khác `None` trong export.

(a) có mà (b) không ⇒ vấn đề ở đường backtest/export, không phải ở dữ liệu sàn. Cả hai không ⇒ vấn đề dữ liệu sàn.

🔴 Ranh giới (`DR-D4-13` §1.2): EXPLORE, ngoài sổ ngân sách (DR-014 §2) — không `reserve()`. Số ở đây KHÔNG phải chỉ số
hiệu năng và không làm bằng chứng cổng nào. Cửa sổ CALIB `[T0, T1)` như TD-0291 §8 — KHÔNG đo WFO.

Chạy trong Docker (N7):
  docker compose -f docker/docker-compose.yml run --rm freqtrade \
      docs/du-lieu-do/do_td0343_gia_thanh_ly_explore.py [--max-coins N] [--ket-qua PATH]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

import pandas as pd  # noqa: E402

from tool_d.config.loader import load_tool_d_config  # noqa: E402
from tool_d.ledger.timerange import dataset_boundaries_from_config  # noqa: E402

_spec = importlib.util.spec_from_file_location("do_td0291", REPO / "docs" / "du-lieu-do" / "do_td0291_song_con_explore.py")
td0291 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(td0291)
td0193 = td0291.td0193

KET_QUA = REPO / "docs" / "du-lieu-do" / "td0343-gia-thanh-ly-explore.json"
ARM = "Z0-T1"
CANH_BAO_FREQTRADE = "Unable to calculate liquidation price"


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True).stdout.strip()


def _bang_bac() -> dict:
    import freqtrade.exchange as fe

    f = Path(fe.__file__).parent / "binance_leverage_tiers.json"
    if not f.is_file():
        return {"file": str(f), "co": False}
    d = json.loads(f.read_text(encoding="utf-8"))
    return {"file": str(f), "co": True, "so_cap": len(d), "_bang": d}


def _san_ao_tinh_duoc(cap: str, open_rate: float, amount: float, stake: float, don_bay: float) -> dict:
    """(a) — gọi thẳng `get_liquidation_price` trên một Exchange dựng từ config dự án (dry-run, futures isolated)."""
    try:
        from freqtrade.resolvers import ExchangeResolver

        cfg = json.loads((REPO / "config" / "freqtrade" / "config.json").read_text(encoding="utf-8"))
        cfg["dry_run"] = True
        cfg["runmode"] = "backtest"
        cfg["exchange"]["pair_whitelist"] = [cap]
        ex = ExchangeResolver.load_exchange(cfg, validate=False, load_leverage_tiers=True)
        gia = ex.get_liquidation_price(
            pair=cap, open_rate=open_rate, is_short=False, amount=amount,
            stake_amount=stake, leverage=don_bay, wallet_balance=stake,
        )
        return {"ket_qua": gia, "co_bac_cho_cap": cap in getattr(ex, "_leverage_tiers", {}),
                "max_leverage": ex.get_max_leverage(cap, stake * don_bay)}
    except Exception as exc:  # chẩn đoán: ghi lỗi, không nuốt
        return {"loi": f"{type(exc).__name__}: {exc}"[:500]}


def _cot_export() -> dict:
    """(c) — backtest ghi kết quả bằng `trade_list_to_dataframe(..., columns=BT_DATA_COLUMNS)`: cột nào KHÔNG có
    trong danh sách đó thì bị cắt khi ghi file, dù giá trị có trên đối tượng lệnh lúc chạy (đo 19/09/2026: có)."""
    import inspect

    from freqtrade.data.btanalysis import BT_DATA_COLUMNS, bt_fileutils

    dong = [i for i, l in enumerate(inspect.getsource(bt_fileutils).splitlines(), 1)
            if "columns=BT_DATA_COLUMNS" in l and "from_records" in l]
    return {
        "liquidation_price_trong_BT_DATA_COLUMNS": "liquidation_price" in BT_DATA_COLUMNS,
        "so_cot_export": len(BT_DATA_COLUMNS),
        "noi_cat": f"freqtrade/data/btanalysis/bt_fileutils.py:{dong}",
    }


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
    if ket_qua.exists():
        print(f"🛑 {ket_qua} đã tồn tại — không ghi đè", flush=True)
        return 3

    cfg = load_tool_d_config(REPO / "config" / "tool_d_config.yaml")
    b = dataset_boundaries_from_config(cfg)
    t1 = pd.Timestamp(b["CALIB"].end)
    td0193.T2 = pd.Timestamp(t1, tz="UTC")
    td0193.TIMERANGE = f"{td0193.T0:%Y%m%d}-{td0193.T2:%Y%m%d}"

    ma = [m for m in td0193._cac_ma() if td0193._du_du_lieu(m)]
    if a.max_coins:
        ma = ma[: a.max_coins]
    print(f"EXPLORE {len(ma)} mã · {td0193.TIMERANGE} · arm {ARM}", flush=True)

    bac = _bang_bac()
    cap_explore = [m.replace("_USDT_USDT", "/USDT:USDT") for m in ma]
    bang = bac.pop("_bang", {})
    bac["so_ma_explore_co_bac"] = sum(1 for c in cap_explore if c in bang)
    bac["ma_explore_khong_bac"] = [c for c in cap_explore if c not in bang][:20]

    t = time.time()
    trades, log = td0291._chay_backtest(ma, ARM)
    giay = round(time.time() - t, 1)
    co_gia = [x for x in trades if x.get("liquidation_price") is not None]
    so_canh_bao = sum(1 for d in log.splitlines() if CANH_BAO_FREQTRADE in d)

    san_ao = {"ghi_chu": "không có lệnh nào để lấy tham số mẫu"}
    if trades:
        x = trades[0]
        vao = [o for o in x["orders"] if o.get("ft_is_entry") and o.get("order_filled_timestamp")]
        amount = float(vao[0]["amount"])
        gia_vao = float(vao[0]["safe_price"])
        don_bay = float(x["leverage"])
        san_ao = {"cap": x["pair"], "open_rate": gia_vao, "amount": amount, "don_bay": don_bay,
                  **_san_ao_tinh_duoc(x["pair"], gia_vao, amount, amount * gia_vao / don_bay, don_bay)}

    kq = {
        "nguon": "TD-0343 — EXPLORE, 0 trial, CALIB [T0,T1) (khuôn TD-0291 §8)",
        "chay_luc_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "git_sha": _git("rev-parse", "HEAD"),
        "arm": ARM,
        "so_ma": len(ma),
        "timerange": td0193.TIMERANGE,
        "giay": giay,
        "b_backtest_ghi_vao_lenh": {
            "tong_lenh": len(trades),
            "lenh_co_liquidation_price": len(co_gia),
            "mau_gia_tri": [{"pair": x["pair"], "liquidation_price": x["liquidation_price"],
                             "open_rate": x.get("open_rate"), "leverage": x.get("leverage")} for x in co_gia[:5]],
            "so_dong_canh_bao_freqtrade": so_canh_bao,
        },
        "a_san_ao_tinh_truc_tiep": san_ao,
        "bang_bac_don_bay": bac,
        "c_nguyen_nhan_export": _cot_export(),
    }
    ket_qua.parent.mkdir(parents=True, exist_ok=True)
    ket_qua.write_text(json.dumps(kq, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    print(json.dumps({k: kq[k] for k in ("b_backtest_ghi_vao_lenh", "a_san_ao_tinh_truc_tiep")},
                     ensure_ascii=False, default=str, indent=1), flush=True)
    print(f"bảng bậc: {bac}", flush=True)
    print(f"→ {ket_qua}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
