"""TD-0247 (`DR-D1-03` §4) — đối chiếu dữ liệu nhập từ kho `data.binance.vision` với file
Freqtrade THẬT của một mã còn giao dịch. **0 trial** (so khớp định dạng, không đánh giá cấu hình).

Câu hỏi: đường nhập kho (`tool_d.data.kho_luu_tru`) có sinh ra đúng từng ô mà
`freqtrade download-data` sinh ra không? Chỉ khi đúng thì 7 mã đã huỷ niêm yết nhập từ
kho mới cùng loại dữ liệu với 100 mã còn lại của rổ `T1`.

Mã / tháng: AAVEUSDT, 05/2024 (mốc milli-giây) và 09/2025 (vùng 5m). Loại: `1h`/`4h`/`1d`
futures (+ `5m` tháng 09/2025), `1h-mark`, `1h-funding_rate`.

Chạy (N7 — trong Docker, service `freqtrade`):

    docker compose -f docker/docker-compose.yml run --rm freqtrade \
        docs/du-lieu-do/do_td0247_doi_chieu_kho_freqtrade.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from tool_d.api_client.binance_public import doc_csv_thang_kho
from tool_d.data.kho_luu_tru import doi_chieu_voi_freqtrade, funding_tu_kho, nen_tu_kho

REPO = Path(__file__).resolve().parents[2]
DU_LIEU = REPO / "user_data" / "data" / "binance" / "futures"
KET_QUA = REPO / "docs" / "du-lieu-do" / "td0247-doi-chieu-kho-freqtrade.json"
MA = "AAVEUSDT"
THANG = [(2024, 5), (2025, 9)]


def _freqtrade(ten: str, t0: pd.Timestamp, t1: pd.Timestamp) -> pd.DataFrame:
    df = pd.read_feather(DU_LIEU / ten)
    return df[(df["date"] >= t0) & (df["date"] < t1)].reset_index(drop=True)


def main() -> int:
    bang: dict[str, object] = {
        "nguon": "TD-0247 / DR-D1-03 §4, 17/09/2026 — kho data.binance.vision vs file freqtrade download-data "
        "trong user_data/data/binance/futures/. 0 trial.",
        "ma": MA,
        "cach_doc": "Đạt khi MỌI dòng có chi_kho = chi_freqtrade = 0 và mọi lech_theo_cot = 0 (dung sai 0).",
        "ket_qua": [],
    }
    dat = True
    for nam, thang in THANG:
        t0 = pd.Timestamp(nam, thang, 1, tz="UTC")
        t1 = t0 + pd.offsets.MonthBegin(1)
        base = MA[:-4]
        viec = [(tf, "futures", "klines") for tf in ("1h", "4h", "1d")]
        if (nam, thang) >= (2025, 6):
            viec.append(("5m", "futures", "klines"))
        viec += [("1h", "mark", "markPriceKlines"), ("1h", "funding_rate", "fundingRate")]
        for tf, hau_to, loai in viec:
            if loai == "fundingRate":
                kho = funding_tu_kho(doc_csv_thang_kho(loai=loai, symbol=MA, nam=nam, thang=thang))
            else:
                kho = nen_tu_kho(
                    doc_csv_thang_kho(loai=loai, symbol=MA, nam=nam, thang=thang, khung=tf),
                    la_mark=loai == "markPriceKlines",
                )
            ft = _freqtrade(f"{base}_USDT_USDT-{tf}-{hau_to}.feather", t0, t1)
            kq = doi_chieu_voi_freqtrade(kho, ft)
            ok = kq["chi_kho"] == 0 and kq["chi_freqtrade"] == 0 and not any(kq["lech_theo_cot"].values())
            dat = dat and ok
            dong = {"thang": f"{nam:04d}-{thang:02d}", "file": f"{tf}-{hau_to}", **kq, "khop": ok}
            bang["ket_qua"].append(dong)  # type: ignore[union-attr]
            print(dong)
    bang["dat"] = dat
    KET_QUA.write_text(json.dumps(bang, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n{'✅ KHỚP TUYỆT ĐỐI' if dat else '🛑 CÓ LỆCH'} — đã ghi {KET_QUA}")
    return 0 if dat else 1


if __name__ == "__main__":
    raise SystemExit(main())
