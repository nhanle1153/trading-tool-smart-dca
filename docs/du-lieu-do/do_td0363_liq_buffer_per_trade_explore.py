"""TD-0363 (`MT-69`) — phân bố **TỪNG LỆNH** của `liq_buffer_ratio` trên EXPLORE. 0 trial.

Câu hỏi DUY NHẤT: nếu nối cổng §6.4 `L-Z3` (từ chối mở khi tỉ số < 8) vào đường vào lệnh thì **bao nhiêu lệnh bị
loại**? Lô `DR-D4-20` chỉ cho biết **trung bình** (`Z0-T1` 18,31 · `Z0` 20,12 · `Z0-T0` 16,57 · `Z3` 20,33) — trung
bình KHÔNG chặn được đuôi, nên không suy ra được tỉ lệ dưới ngưỡng. Đo rẻ hơn đoán.

🔴 Ranh giới (`DR-D4-13` §1.2): EXPLORE, ngoài sổ ngân sách (`DR-014` §2) — **không** `reserve()`. Cửa sổ CALIB
`[T0, T1)` như `TD-0291` §8 / `TD-0358`, KHÔNG đo WFO. Số ở đây là **cận** cho tác động của `L-Z3`, không phải số
trên rổ T1: EXPLORE khác rổ, khác cửa sổ (spec `:4338`).

Dùng lại `ablation/thanh_ly.liq_buffer_ke_hoach` qua `chi_so_export.dem_thanh_ly_lenh` — **cùng một hàm** mà tầng đo
và (sau này) cổng vào lệnh dùng, không viết công thức thứ hai (N1/`MT-03`).

⚠️ Với arm ĐƠN TRANCHE (`Z0-T1`, `Z0`, `Z0-T0`), tỉ số tính theo **kế hoạch đủ 3 tranche** đúng spec `:1875` trong khi
vị thế THẬT chỉ có tranche 1 ⇒ đệm thật RỘNG hơn số ở đây. Số này vì thế là **cận dưới** (thận trọng) cho các arm đó.

Chạy trong Docker (N7):
  docker compose -f docker/docker-compose.yml run --rm freqtrade docs/du-lieu-do/do_td0363_liq_buffer_per_trade_explore.py
"""
from __future__ import annotations

import importlib.util
import json
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

import pandas as pd  # noqa: E402

from tool_d.ablation.ban_ghi import LO_ARM_D4  # noqa: E402
from tool_d.ablation.chi_so_export import ChiSoExportError, dem_thanh_ly_lenh  # noqa: E402
from tool_d.ablation.thanh_ly import tinh_liq_freqtrade  # noqa: E402
from tool_d.config.loader import load_tool_d_config, resolve  # noqa: E402
from tool_d.gates.thresholds import LIQ_BUFFER_RATIO_MEAN_MIN  # noqa: E402
from tool_d.ledger.timerange import dataset_boundaries_from_config  # noqa: E402
from tool_d.measurement.gitinfo import get_git_info  # noqa: E402

_spec = importlib.util.spec_from_file_location("do_td0291", REPO / "docs" / "du-lieu-do" / "do_td0291_song_con_explore.py")
td0291 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(td0291)
td0193 = td0291.td0193

KET_QUA = REPO / "docs" / "du-lieu-do" / "td0363-liq-buffer-per-trade-explore.json"
#: Trung bình đo được ở lô `DR-D4-20` (WFO, rổ T1) — ghi CẠNH để thấy EXPLORE lệch bao nhiêu, KHÔNG dùng để kết luận.
TRUNG_BINH_LO_WFO = {"Z0-T1": 18.30855465659627, "Z0": 20.12380315169036, "Z0-T0": 16.566374470515484, "Z3": 20.32729009451434}


def _phan_vi(xs: list[float], p: float) -> float:
    """Phân vị kiểu "lấy phần tử", không nội suy — tránh đúng chỗ `TD-0168` từng lệch vì hai quy ước nội suy."""
    s = sorted(xs)
    i = min(len(s) - 1, max(0, int(round(p / 100 * (len(s) - 1)))))
    return s[i]


def do_arm(ma: list[str], arm: str, cfg, ham) -> dict:
    t = time.time()
    trades, _log = td0291._chay_backtest(ma, arm)
    ty_so: list[float] = []
    khong_tinh_duoc: list[str] = []
    loi: list[str] = []
    for tr in trades:
        try:
            d = dem_thanh_ly_lenh(tr, cfg=cfg, ham=ham)
        except ChiSoExportError as exc:
            loi.append(f"{tr.get('pair')}: {str(exc)[:120]}")
            continue
        if d is None:
            khong_tinh_duoc.append(str(tr.get("pair")))
        else:
            ty_so.append(d.ty_so)
    ra: dict = {
        "so_lenh": len(trades),
        "so_lenh_tinh_duoc": len(ty_so),
        "so_lenh_san_khong_co_bac": sorted(set(khong_tinh_duoc)),
        "loi_trich": loi[:5],
        "giay": round(time.time() - t, 1),
        "trung_binh_lo_wfo_de_doi_chieu": TRUNG_BINH_LO_WFO.get(arm),
    }
    if ty_so:
        duoi = [x for x in ty_so if x < LIQ_BUFFER_RATIO_MEAN_MIN]
        ra.update(
            min=min(ty_so), max=max(ty_so),
            trung_binh=statistics.fmean(ty_so), trung_vi=statistics.median(ty_so),
            P1=_phan_vi(ty_so, 1), P5=_phan_vi(ty_so, 5), P10=_phan_vi(ty_so, 10), P25=_phan_vi(ty_so, 25),
            so_lenh_duoi_nguong=len(duoi),
            ty_le_duoi_nguong=len(duoi) / len(ty_so),
        )
    return ra


def main() -> int:
    if KET_QUA.exists():
        print(f"🛑 {KET_QUA} đã tồn tại — không ghi đè, không đo lại", flush=True)
        return 3
    cfg = load_tool_d_config(REPO / "config" / "tool_d_config.yaml")
    bien = dataset_boundaries_from_config(cfg)
    t1 = pd.Timestamp(bien["CALIB"].end)
    td0193.T2 = pd.Timestamp(t1, tz="UTC")
    td0193.TIMERANGE = f"{td0193.T0:%Y%m%d}-{td0193.T2:%Y%m%d}"
    ma = [m for m in td0193._cac_ma() if td0193._du_du_lieu(m)]
    git = get_git_info(REPO)
    ham = tinh_liq_freqtrade(REPO / "config" / "freqtrade" / "config.json")
    print(f"EXPLORE {len(ma)} mã · {td0193.TIMERANGE} · ngưỡng {LIQ_BUFFER_RATIO_MEAN_MIN} · "
          f"đòn bẩy {resolve(cfg, 'tier_a.L_exchange')} · buffer {ham.liquidation_buffer}", flush=True)

    ket: dict[str, dict] = {}
    for arm in LO_ARM_D4:
        ket[arm] = do_arm(ma, arm, cfg, ham)
        r = ket[arm]
        if r.get("so_lenh_tinh_duoc"):
            print(f"  {arm:6s} n {r['so_lenh_tinh_duoc']:4d} · min {r['min']:7.2f} · P5 {r['P5']:7.2f} · "
                  f"trung vị {r['trung_vi']:7.2f} · dưới {LIQ_BUFFER_RATIO_MEAN_MIN}: "
                  f"{r['so_lenh_duoi_nguong']} ({r['ty_le_duoi_nguong']:.1%})  ({r['giay']}s)", flush=True)
        else:
            print(f"  {arm:6s} KHÔNG lệnh nào tính được ({r['so_lenh']} lệnh thô)", flush=True)

    KET_QUA.write_text(json.dumps({
        "nguon": "TD-0363 — MT-69, phân bố TỪNG LỆNH của liq_buffer_ratio, EXPLORE CALIB [T0,T1), 0 trial",
        "chay_luc_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "git_sha": git.sha, "cay_sach": git.is_clean,
        "so_ma_explore": len(ma), "timerange": td0193.TIMERANGE,
        "nguong_L_Z3": LIQ_BUFFER_RATIO_MEAN_MIN,
        "don_bay": resolve(cfg, "tier_a.L_exchange"),
        "liquidation_buffer": ham.liquidation_buffer,
        "arm": ket,
        "han_che": [
            "EXPLORE ≠ rổ T1 và cửa sổ CALIB ≠ WFO — số này là CẬN cho tác động của L-Z3, không phải số của lô D4",
            "Arm đơn tranche: tỉ số theo KẾ HOẠCH 3 tranche (spec :1875) trong khi vị thế thật chỉ có tranche 1 ⇒ "
            "đệm thật rộng hơn ⇒ số ở đây là cận DƯỚI, thận trọng",
            "Giá thanh lý ĐÃ DỊCH đệm (DR-D4-17 §3 dòng 2, MT-70) ⇒ tỉ số nhỏ hơn giá thô khoảng 5%",
            "Bậc MỘT: chỉ đếm lệnh ĐÃ mở bị loại; không tính lệnh khác lấp chỗ lệnh bị bỏ (cùng giới hạn TD-0358)",
        ],
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"→ {KET_QUA}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
