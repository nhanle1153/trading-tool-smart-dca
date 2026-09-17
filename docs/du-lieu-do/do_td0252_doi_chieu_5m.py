"""TD-0252 (`DR-D1-05` §3b.3) — 🚪 CỔNG: đối chiếu 5m từ kho với file Freqtrade THẬT, trong
**kỷ nguyên CALIB**. **0 trial** (so khớp định dạng, không đánh giá cấu hình nào).

Vì sao phải có cổng này trước khi nhập một byte nào: `DR-D1-05` §3b.3 chọn lấy 5m cho cả 143 mã
từ kho `data.binance.vision` thay vì `freqtrade download-data`, để khử bằng cấu tạo hai bẫy đã
cắn dự án (TD-0093 `--timerange` không dừng đúng mốc; TD-0200 tải 5m kéo theo mark+funding ghi
đè file đã cắt). Cái giá là phải chứng minh kho sinh ra ĐÚNG từng ô mà Freqtrade sinh ra — nếu
lệch, 143 mã vừa nhập là rác im lặng.

Artifact cũ `td0247-doi-chieu-kho-freqtrade.json` **không phủ ca này**: nó đối chiếu 5m ở
`2025-09`, tức **kỷ nguyên micro-giây**. `kho_luu_tru._moc()` đổi đơn vị theo ngưỡng `1e14`, còn
`2024-06` là **milli-giây**, và ở kỷ nguyên đó 5m chưa từng được đối chiếu — chỉ `1h`/`4h`/`1d`/
mark/funding mới có.

Mã đối chứng: `1000BONKUSDT` và `1000PEPEUSDT`, tháng `2024-06` và `2024-07` — hai mã duy nhất
có file 5m Freqtrade thật phủ được kỷ nguyên đó (tải ở TD-0115, `user_data/data/binance/futures/`).

Chạy (N7 — trong Docker, service `freqtrade`):

    docker compose -f docker/docker-compose.yml run --rm freqtrade \
        docs/du-lieu-do/do_td0252_doi_chieu_5m.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from tool_d.api_client.binance_public import doc_csv_thang_kho
from tool_d.data.kho_luu_tru import doi_chieu_voi_freqtrade, nen_tu_kho

REPO = Path(__file__).resolve().parents[2]
DU_LIEU = REPO / "user_data" / "data" / "binance" / "futures"
KET_QUA = REPO / "docs" / "du-lieu-do" / "td0252-doi-chieu-kho-freqtrade-5m.json"
MA = ["1000BONKUSDT", "1000PEPEUSDT"]
THANG = [(2024, 6), (2024, 7)]


def _freqtrade(ten: str, t0: pd.Timestamp, t1: pd.Timestamp) -> pd.DataFrame:
    df = pd.read_feather(DU_LIEU / ten)
    return df[(df["date"] >= t0) & (df["date"] < t1)].reset_index(drop=True)


def main() -> int:
    bang: dict[str, object] = {
        "nguon": (
            "TD-0252 / DR-D1-05 §3b.3, 18/09/2026 — kho data.binance.vision vs file freqtrade "
            "download-data, khung 5m, KỶ NGUYÊN CALIB (milli-giây). Bổ sung đúng chỗ mà "
            "td0247-doi-chieu-kho-freqtrade.json không phủ (nó đo 5m ở 2025-09, micro-giây). 0 trial."
        ),
        "ma": MA,
        "thang": [f"{n:04d}-{t:02d}" for n, t in THANG],
        "cach_doc": "Đạt khi MỌI dòng có chi_kho = chi_freqtrade = 0 và mọi lech_theo_cot = 0 (dung sai 0).",
        "ket_qua": [],
    }
    dat = True
    for symbol in MA:
        base = symbol[:-4]
        for nam, thang in THANG:
            t0 = pd.Timestamp(nam, thang, 1, tz="UTC")
            t1 = t0 + pd.offsets.MonthBegin(1)
            kho = nen_tu_kho(
                doc_csv_thang_kho(loai="klines", symbol=symbol, nam=nam, thang=thang, khung="5m"),
                la_mark=False,
            )
            ft = _freqtrade(f"{base}_USDT_USDT-5m-futures.feather", t0, t1)
            kq = doi_chieu_voi_freqtrade(kho, ft)
            ok = kq["chi_kho"] == 0 and kq["chi_freqtrade"] == 0 and not any(kq["lech_theo_cot"].values())
            dat = dat and ok
            dong = {
                "ma": symbol,
                "thang": f"{nam:04d}-{thang:02d}",
                "file": "5m-futures",
                "so_nen_kho": len(kho),
                "so_nen_freqtrade": len(ft),
                **kq,
                "khop": ok,
            }
            bang["ket_qua"].append(dong)  # type: ignore[union-attr]
            print(dong)
    bang["dat"] = dat
    KET_QUA.write_text(json.dumps(bang, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"\n{'✅ KHỚP TUYỆT ĐỐI' if dat else '🛑 CÓ LỆCH'} — đã ghi {KET_QUA}")
    if not dat:
        print("   CỔNG ĐÓNG: không nhập 5m từ kho cho tới khi giải thích được chỗ lệch.")
    return 0 if dat else 1


if __name__ == "__main__":
    raise SystemExit(main())
