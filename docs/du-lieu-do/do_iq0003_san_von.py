"""TD-0406 — đo sàn lệnh tối thiểu cho rổ `IQ-0003` để chốt `tier_a.von_ro_usdt` (`DR-D0-IQ0003` §10 câu c).

0 suất, đo MÔ TẢ. Cố ý KHÔNG đọc dữ liệu thị trường của CALIB/WFO (vướng `MT-19`): chỉ đọc
  • danh sách mã `trading` của `config/pool_t0.yaml` / `config/pool_t1.yaml` (cấu hình rổ, không phải giá);
  • metadata sàn HIỆN TẠI (`MIN_NOTIONAL`, `LOT_SIZE`) + giá hiện tại, qua adapter `binance_public` (single egress, R1–R12).

Quy tắc (DR §10 câu c): `von_ro_usdt ≥ 1,1 × 2 × k_max × sàn_max / ro_don_bay`, `sàn = san_tool_d()` (DR-D4-05, max mọi
đường chạy) với stoploss hiệu dụng của RoFunding `−ro_stop_tham_hoa_pct × ro_don_bay_san / 100`.

⚠️ Giới hạn, khai trong hiện vật: (1) giá HIỆN TẠI, không phải giá lịch sử — vế `min_qty × giá` có thể lệch, nhưng vế
`MIN_NOTIONAL` quyết định sàn ở gần như mọi mã; (2) mã đã huỷ niêm yết không còn trong `exchangeInfo` ⇒ gán sàn LỚN NHẤT
của các mã còn lại (bảo thủ), liệt kê tên.

Chạy (Docker): `docker compose -f docker/docker-compose.yml run --rm --entrypoint python freqtrade
docs/du-lieu-do/do_iq0003_san_von.py --ket-qua docs/du-lieu-do/IQ-0003-san-von.json`
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from tool_d.api_client.binance_public import get_exchange_info, get_ticker_price
from tool_d.config.loader import load_tool_d_config, resolve
from tool_d.notional import SymbolFilters, san_tool_d
from tool_d.ro_funding import MA_LOAI_CO_DINH, so_k

HE_SO_LE = 1.1
FILE_RO = {"CALIB": Path("config/pool_t0.yaml"), "WFO": Path("config/pool_t1.yaml")}


def _bo_loc(exchange_info: dict, gia: dict[str, float]) -> dict[str, SymbolFilters]:
    out: dict[str, SymbolFilters] = {}
    for s in exchange_info["symbols"]:
        loc = {x["filterType"]: x for x in s.get("filters", [])}
        sym = s["symbol"]
        if "MIN_NOTIONAL" not in loc or "LOT_SIZE" not in loc or sym not in gia:
            continue
        out[sym] = SymbolFilters(
            symbol=sym,
            min_notional_usdt=float(loc["MIN_NOTIONAL"]["notional"]),
            step_size=float(loc["LOT_SIZE"]["stepSize"]),
            min_qty=float(loc["LOT_SIZE"]["minQty"]),
            price=gia[sym],
        )
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ket-qua", required=True, type=Path)
    args = ap.parse_args(argv)

    cfg = load_tool_d_config()
    pct = float(resolve(cfg, "tier_c.ro_funding.ro_stop_tham_hoa_pct"))
    lev_san = float(resolve(cfg, "tier_c.ro_funding.ro_don_bay_san"))
    don_bay = float(resolve(cfg, "tier_c.ro_funding.ro_don_bay"))
    ty_le_k = float(resolve(cfg, "tier_c.ro_funding.ro_ty_le_k"))
    k_min = int(resolve(cfg, "tier_c.ro_funding.ro_k_toi_thieu"))
    stoploss = -pct * lev_san / 100

    gia = {p["symbol"]: float(p["price"]) for p in get_ticker_price()}
    bo_loc = _bo_loc(get_exchange_info(), gia)

    theo_tap: dict[str, dict] = {}
    for tap, file_ro in FILE_RO.items():
        trading = [m for m in yaml.safe_load(file_ro.read_text(encoding="utf-8"))["trading"]]
        trading = [m for m in trading if m.removesuffix("USDT") not in MA_LOAI_CO_DINH]
        san = {m: san_tool_d(bo_loc[m], strategy_stoploss=stoploss) for m in trading if m in bo_loc}
        thieu = sorted(m for m in trading if m not in bo_loc)
        if not san:
            print(f"🛑 {tap}: không mã nào có metadata sàn — không kết luận được")
            return 2
        san_max_biet = max(san.values())
        theo_tap[tap] = {
            "file_ro": file_ro.as_posix(),
            "so_ma_trading": len(trading),
            "k_max": so_k(len(trading), ty_le_k=ty_le_k, k_toi_thieu=k_min),
            "san_max_usdt": round(san_max_biet, 4),
            "ma_san_max": sorted(m for m, v in san.items() if math.isclose(v, san_max_biet)),
            "phan_bo_san_usdt": {f"{v:.2f}": sum(1 for x in san.values() if math.isclose(x, v)) for v in sorted(set(san.values()))},
            "ma_thieu_metadata_gan_san_max": thieu,
        }

    k_max = max(t["k_max"] for t in theo_tap.values())
    san_max = max(t["san_max_usdt"] for t in theo_tap.values())
    von_toi_thieu = HE_SO_LE * 2 * k_max * san_max / don_bay
    von_de_xuat = math.ceil(von_toi_thieu / 100) * 100
    kq = {
        "nguon": "TD-0406 — DR-D0-IQ0003 §10 câu (c); 0 suất, đo mô tả, không đọc dữ liệu thị trường CALIB/WFO",
        "luc_do_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stoploss_hieu_dung": stoploss,
        "ro_don_bay": don_bay,
        "ro_don_bay_san": lev_san,
        "he_so_le": HE_SO_LE,
        "theo_tap": theo_tap,
        "k_max": k_max,
        "san_max_usdt": san_max,
        "von_toi_thieu_usdt": round(von_toi_thieu, 2),
        "von_de_xuat_usdt": von_de_xuat,
        "gioi_han": [
            "giá HIỆN TẠI, không phải giá lịch sử của giai đoạn — vế min_qty × giá có thể lệch",
            "mã đã huỷ niêm yết không có trong exchangeInfo — liệt kê ở ma_thieu_metadata_gan_san_max, coi như sàn lớn nhất",
        ],
    }
    args.ket_qua.write_text(json.dumps(kq, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: kq[k] for k in ("k_max", "san_max_usdt", "von_toi_thieu_usdt", "von_de_xuat_usdt")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
