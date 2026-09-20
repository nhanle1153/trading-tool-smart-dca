"""TD-0359 (`DR-D4-20` §7, sau khi cổng D4 từ chối) — tỉ trọng tranche LỆCH bao nhiêu và VÌ SAO. EXPLORE, 0 trial.

Cổng D4 từ chối lô `DR-D4-20` với một lý do ĐO ĐƯỢC: `ti_trong_tranche_dat = False` ở arm `Z3`
(`chi_so_export.py:114` — mọi lệnh đủ ba tranche phải có `cost_j / cost_1 ∈ [0,99; 1,01]`). Câu hỏi N10 phải
trả lời TRƯỚC khi đụng vào chiến lược hay vào cổng: **cỡ lệnh sai, hay chỉ là làm tròn của sàn?**

Hai giả thuyết phân biệt được bằng số:
- **Làm tròn:** `cost_j` lệch vì `amount` bị cắt về bước hợp đồng (`amount_to_contract_precision`). Lệch sẽ NHỎ
  và LỚN DẦN khi giá mỗi đơn vị càng lớn so với cỡ lệnh (bước hợp đồng càng thô so với notional).
- **Cỡ lệnh sai:** lệch mang cấu trúc — ví dụ `cost_2/cost_1 ≈ p2/p1` (quên nhân lại theo giá) hoặc một tỉ lệ
  cố định khác 1 — và không co lại theo độ mịn của bước giá.

Chỉ ĐẾM và đo tỉ lệ; không PnL, không xếp hạng arm. Cùng khuôn `do_td0184_kep_gia_explore.py`: EXPLORE CALIB
`[T0,T1)`, ngoài sổ ngân sách (DR-014 §2), không `reserve()`.

Chạy trong Docker (N7):
  docker compose -f docker/docker-compose.yml run --rm freqtrade docs/du-lieu-do/do_td0359_ti_trong_tranche_explore.py
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

_spec = importlib.util.spec_from_file_location(
    "do_td0291", REPO / "docs" / "du-lieu-do" / "do_td0291_song_con_explore.py"
)
td0291 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(td0291)
td0193 = td0291.td0193

KET_QUA = REPO / "docs" / "du-lieu-do" / "td0359-ti-trong-tranche-explore.json"
ARM = "Z3"  # arm DCA duy nhất của lô (ba arm kia thuộc ARM_DON_TRANCHE)
DUNG_SAI = 0.01  # `chi_so_export.DUNG_SAI_TI_TRONG`


def _vao_da_khop(t: dict) -> list[dict]:
    return sorted(
        (o for o in t["orders"] if o.get("ft_is_entry") and o.get("order_filled_timestamp")
         and float(o.get("amount") or 0) > 0),
        key=lambda o: int(o["order_filled_timestamp"]),
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-coins", type=int, default=0)
    ap.add_argument("--ket-qua", default=None)
    a = ap.parse_args()
    ket_qua = Path(a.ket_qua) if a.ket_qua else KET_QUA
    if not ket_qua.is_absolute():
        ket_qua = REPO / ket_qua
    if ket_qua == KET_QUA and KET_QUA.exists():
        print("🛑 artifact đã tồn tại — ghi file MỚI", flush=True)
        return 3

    ma = [m for m in td0193._cac_ma() if td0193._du_du_lieu(m)]
    if a.max_coins:
        ma = ma[: a.max_coins]
    print(f"EXPLORE {len(ma)} mã · {td0193.TIMERANGE} · arm {ARM} · 0 trial", flush=True)

    trades, log = td0291._chay_backtest(ma, ARM)
    nuot = sum(1 for d in log.splitlines() if "Strategy caused the following exception" in d)
    if nuot:
        print(f"🛑 {nuot} exception bị Freqtrade nuốt (MT-16 vii)", flush=True)
        return 1

    dong = []
    for t in trades:
        vao = _vao_da_khop(t)
        if len(vao) < 3:
            continue
        cost = [float(o["amount"]) * float(o["safe_price"]) for o in vao[:3]]
        amount = [float(o["amount"]) for o in vao[:3]]
        gia = [float(o["safe_price"]) for o in vao[:3]]
        dong.append(
            {
                "pair": t["pair"],
                "open_date": str(t["open_date"]),
                "ty_le_cost": [c / cost[0] for c in cost],
                "ty_le_gia": [g / gia[0] for g in gia],
                # Bước hợp đồng suy từ chính `amount` đã khớp: notional của MỘT bước ở giá tranche 1.
                "notional_tranche1": cost[0],
                "amount_tranche1": amount[0],
            }
        )

    lech = [max(abs(r - 1.0) for r in d["ty_le_cost"]) for d in dong]
    qua_dung_sai = [d for d, l in zip(dong, lech) if l > DUNG_SAI]
    # Nếu là LÀM TRÒN: lệch tương quan ÂM với notional (cỡ lệnh càng to, một bước hợp đồng càng nhỏ tương đối).
    # Nếu là CỠ LỆNH SAI: `ty_le_cost` bám sát `ty_le_gia` (hoặc một hằng số), không phụ thuộc notional.
    bam_gia = [
        max(abs(rc - rg) for rc, rg in zip(d["ty_le_cost"], d["ty_le_gia"])) for d in dong
    ]

    ra = {
        "nguon": "TD-0359 — tỉ trọng tranche trên EXPLORE CALIB, 0 trial, CHỈ đếm/đo tỉ lệ (DR-D4-20 §7)",
        "chay_luc_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "git_sha": td0291._git("rev-parse", "HEAD"),
        "cay_sach": td0291._git("status", "--porcelain", "--untracked-files=no") == "",
        "arm": ARM,
        "so_ma_explore": len(ma),
        "so_lenh_du_ba_tranche": len(dong),
        "so_lenh_qua_dung_sai": len(qua_dung_sai),
        "dung_sai": DUNG_SAI,
        "lech_lon_nhat": max(lech) if lech else None,
        "lech_trung_vi": statistics.median(lech) if lech else None,
        "khoang_cach_toi_ty_le_GIA_lon_nhat": max(bam_gia) if bam_gia else None,
        "doc_dung": (
            "`ty_le_cost` gần 1 và lệch nhỏ ⇒ làm tròn bước hợp đồng. `ty_le_cost` bám `ty_le_gia` "
            "(khoảng cách ≈ 0) ⇒ cỡ lệnh tính sai theo giá, KHÔNG phải làm tròn."
        ),
        "vi_du": sorted(dong, key=lambda d: -max(abs(r - 1.0) for r in d["ty_le_cost"]))[:5],
    }
    ket_qua.write_text(json.dumps(ra, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in ra.items() if k != "vi_du"}, ensure_ascii=False), flush=True)
    print(f"→ {ket_qua.relative_to(REPO)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
