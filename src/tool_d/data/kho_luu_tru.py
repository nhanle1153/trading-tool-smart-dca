"""TD-0247 (`DR-D1-03`) — chuyển hàng CSV tháng của kho `data.binance.vision`
sang đúng định dạng file `.feather` mà Freqtrade đọc.

Vì sao cần: `freqtrade download-data` chỉ tải được mã CÒN trên sàn. Rổ `T1`
có 7 mã đã huỷ niêm yết (6 `SETTLING` + 1 vắng khỏi `exchangeInfo`); bỏ chúng
là tái tạo lệch sống sót mà `TD-0247` sinh ra để sửa. Kho lưu trữ là nguồn duy
nhất còn giữ nến của chúng.

Logic THUẦN, không gọi mạng (hàng CSV do `doc_csv_thang_kho()` cấp). Định dạng
đích đo từ file Freqtrade THẬT (`user_data/data/binance/futures/`, 17/09/2026):

  • `<tf>-futures` / `<tf>-mark`: cột `date, open, high, low, close, volume`,
    `date` = `datetime64[ms, UTC]` (mốc MỞ nến), số là `float64`.
    `-mark` có `volume = 0.0` trên toàn file.
  • `1h-funding_rate`: cột `date, funding_rate`, một hàng mỗi kỳ funding.

🔴 Không tự làm tròn mốc, không tự lấp nến thiếu, không bỏ hàng trùng lặng lẽ:
trùng mốc mà khác giá trị ⇒ raise. Khớp định dạng được CHỨNG MINH bằng phép đối
chiếu với một mã còn giao dịch (xem `doi_chieu_voi_freqtrade`), không bằng suy luận.
"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

# Cùng ngưỡng với `binance_public._NGUONG_MICRO_GIAY`: kho đã đổi đơn vị mốc
# từ milli sang micro-giây. 1e14 ms ≈ năm 5138.
_NGUONG_MICRO_GIAY = 1e14

COT_NEN = ["date", "open", "high", "low", "close", "volume"]
COT_FUNDING = ["date", "funding_rate"]


class DuLieuKhoError(ValueError):
    """Hàng CSV kho không chuyển được mà không phải đoán."""


def _moc(tho: str) -> pd.Timestamp:
    v = float(tho)
    don_vi = "us" if v > _NGUONG_MICRO_GIAY else "ms"
    return pd.Timestamp(int(v), unit=don_vi, tz="UTC")


def _khung(df: pd.DataFrame, cot: list[str], ten: str) -> pd.DataFrame:
    df = df[cot].sort_values("date", kind="stable").reset_index(drop=True)
    trung = df[df["date"].duplicated(keep=False)]
    if not trung.empty:
        if len(trung.drop_duplicates()) != len(trung.drop_duplicates(subset=["date"])):
            raise DuLieuKhoError(f"{ten}: trùng mốc với giá trị KHÁC nhau — không tự chọn: {trung.head(4).to_dict('records')}")
        df = df.drop_duplicates(subset=["date"]).reset_index(drop=True)
    df["date"] = df["date"].astype("datetime64[ms, UTC]")
    return df


def nen_tu_kho(hang: Sequence[Sequence[str]], *, la_mark: bool) -> pd.DataFrame:
    """`klines` / `markPriceKlines`: 0 open_time · 1 open · 2 high · 3 low · 4 close · 5 volume …

    `volume` của futures lấy cột 5 (khối lượng tài sản CƠ SỞ — cùng nghĩa với
    Freqtrade); của mark đặt `0.0` (đúng file Freqtrade thật)."""
    if not hang:
        raise DuLieuKhoError("0 hàng nến")
    try:
        ban_ghi = [
            {
                "date": _moc(o[0]),
                "open": float(o[1]),
                "high": float(o[2]),
                "low": float(o[3]),
                "close": float(o[4]),
                "volume": 0.0 if la_mark else float(o[5]),
            }
            for o in hang
        ]
    except (IndexError, ValueError) as exc:
        raise DuLieuKhoError(f"hàng nến không đọc được: {exc}") from exc
    return _khung(pd.DataFrame(ban_ghi), COT_NEN, "mark" if la_mark else "futures")


#: Độ trễ tối đa của `calc_time` so với tròn giờ mà vẫn coi là cùng kỳ funding.
#: Đo 17/09/2026 (AAVE 05/2024 + 09/2025): kho ghi `1714665600002` (lệch 1–7 ms),
#: Freqtrade ghi tròn giờ; số hàng và giá trị trùng hết. Lệch ≥ ngưỡng này thì
#: KHÔNG làm tròn — đó không còn là jitter mà là một mốc khác.
DO_TRE_FUNDING_TOI_DA = pd.Timedelta(seconds=60)


def funding_tu_kho(hang: Sequence[Sequence[str]]) -> pd.DataFrame:
    """`fundingRate`: 0 calc_time · 1 funding_interval_hours · 2 last_funding_rate.

    Mốc làm tròn XUỐNG giờ (khớp Freqtrade); từ chối nếu độ lệch ≥
    `DO_TRE_FUNDING_TOI_DA`."""
    if not hang:
        raise DuLieuKhoError("0 hàng funding")
    ban_ghi = []
    try:
        for o in hang:
            tho = _moc(o[0])
            tron = tho.floor("h")
            if tho - tron >= DO_TRE_FUNDING_TOI_DA:
                raise DuLieuKhoError(
                    f"funding calc_time {o[0]} lệch {tho - tron} so với tròn giờ — "
                    "vượt ngưỡng jitter, không làm tròn"
                )
            ban_ghi.append({"date": tron, "funding_rate": float(o[2])})
    except (IndexError, ValueError) as exc:
        if isinstance(exc, DuLieuKhoError):
            raise
        raise DuLieuKhoError(f"hàng funding không đọc được: {exc}") from exc
    return _khung(pd.DataFrame(ban_ghi), COT_FUNDING, "funding")


def doi_chieu_voi_freqtrade(kho: pd.DataFrame, freqtrade: pd.DataFrame, *, dung_sai: float = 0.0) -> dict:
    """So hai khung trên phần giao mốc `date`. Trả số mốc chung, số mốc chỉ ở
    mỗi bên, và số ô lệch vượt `dung_sai` theo từng cột — không kết luận hộ."""
    chung = kho.merge(freqtrade, on="date", how="inner", suffixes=("_kho", "_ft"))
    cot = [c for c in kho.columns if c != "date"]
    lech = {c: int((abs(chung[f"{c}_kho"] - chung[f"{c}_ft"]) > dung_sai).sum()) for c in cot}
    return {
        "chung": len(chung),
        "chi_kho": int((~kho["date"].isin(freqtrade["date"])).sum()),
        "chi_freqtrade": int((~freqtrade["date"].isin(kho["date"])).sum()),
        "lech_theo_cot": lech,
    }
