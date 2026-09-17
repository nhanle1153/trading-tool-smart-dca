"""TD-0247 (`DR-D1-03` §4) — dữ liệu `[T0,T2]` cho rổ `T1` trong `user_data/data/pool_t1/futures/`.

Bốn thao tác, mỗi thao tác một hàm, không hàm nào gọi hàm nào:

  • `sao_chep_ma_co_san()`  — 55 mã đã đủ file ở `binance/`: chép nguyên byte, kiểm sha256.
  • `nhap_ma_tu_kho()`      — mã đã huỷ niêm yết: nhập từ kho (`tool_d.data.kho_luu_tru`).
  • `cat_den_moc()`         — cắt nến sau `T2` (bug TD-0093: `download-data` lấn quá mốc cuối).
  • `kiem_du_lieu_ro()`     — kiểm đủ rổ bằng máy trước khi coi `TD-0247` xong.

Đọc mạng được TIÊM (`doc_csv`), nên test chạy không cần mạng. Mọi thao tác ghi
đều TỪ CHỐI ghi đè file đã tồn tại, trừ `cat_den_moc()` (chỉ bỏ hàng, không thêm).
"""

from __future__ import annotations

import hashlib
import shutil
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from tool_d.api_client.binance_public import NenThangKhongCoError
from tool_d.data.kho_luu_tru import funding_tu_kho, nen_tu_kho


@dataclass(frozen=True)
class LoaiFile:
    khung: str
    hau_to: str  # "futures" | "mark" | "funding_rate"
    loai_kho: str  # "klines" | "markPriceKlines" | "fundingRate"
    tu_moc: str  # "t0" | "t1"


#: Sáu loại file mỗi mã — đúng quy ước đo trên `user_data/data/binance/futures/` 17/09/2026.
SAU_LOAI_FILE: tuple[LoaiFile, ...] = (
    LoaiFile("1h", "futures", "klines", "t0"),
    LoaiFile("4h", "futures", "klines", "t0"),
    LoaiFile("1d", "futures", "klines", "t0"),
    LoaiFile("5m", "futures", "klines", "t1"),
    LoaiFile("1h", "mark", "markPriceKlines", "t0"),
    LoaiFile("1h", "funding_rate", "fundingRate", "t0"),
)


class DuLieuRoError(RuntimeError):
    """Thao tác dữ liệu rổ không thể hoàn tất mà không đoán — fail-closed."""


def ten_file(symbol: str, lf: LoaiFile) -> str:
    if not symbol.endswith("USDT"):
        raise DuLieuRoError(f"mã {symbol!r} không kết thúc bằng USDT")
    return f"{symbol[:-4]}_USDT_USDT-{lf.khung}-{lf.hau_to}.feather"


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _moc_ts(d: date) -> pd.Timestamp:
    return pd.Timestamp(d.year, d.month, d.day, tz="UTC")


def _dau_thang(s: str) -> date:
    y, m = (int(x) for x in s.split("-"))
    return date(y, m, 1)


def _thang(d: date) -> tuple[int, int]:
    return d.year, d.month


def cac_thang(tu: tuple[int, int], den: tuple[int, int]) -> list[tuple[int, int]]:
    """Các tháng từ `tu` tới `den`, gồm cả hai đầu."""
    ra: list[tuple[int, int]] = []
    y, m = tu
    while (y, m) <= den:
        ra.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return ra


def sao_chep_ma_co_san(nguon: Path, dich: Path, ma: Sequence[str]) -> list[str]:
    """Chép nguyên byte 6 file của từng mã; kiểm sha256 sau chép. Trả tên file đã chép.

    Từ chối (trước khi chép file nào) nếu: thiếu file nguồn, hoặc file đích đã tồn tại."""
    viec: list[tuple[Path, Path]] = []
    for s in ma:
        for lf in SAU_LOAI_FILE:
            src, dst = nguon / ten_file(s, lf), dich / ten_file(s, lf)
            if not src.is_file():
                raise DuLieuRoError(f"thiếu file nguồn {src}")
            if dst.exists():
                raise DuLieuRoError(f"file đích đã tồn tại, không ghi đè: {dst}")
            viec.append((src, dst))
    dich.mkdir(parents=True, exist_ok=True)
    for src, dst in viec:
        shutil.copyfile(src, dst)
        if _sha256(src) != _sha256(dst):
            raise DuLieuRoError(f"chép lệch byte: {src} -> {dst}")
    return [dst.name for _, dst in viec]


def nhap_ma_tu_kho(
    symbol: str,
    *,
    dich: Path,
    khoang: Mapping[str, str],
    moc: Mapping[str, date],
    doc_csv: Callable[..., list[list[str]]],
) -> dict[str, int]:
    """Nhập 6 file cho một mã từ kho. `khoang = {"thang_dau", "thang_cuoi"}` (TD-0230);
    `moc = {"t0", "t1", "t2"}`. Trả {tên file: số hàng}.

    Tháng cần tải = giao của [mốc bắt đầu, T2] với [thang_dau, thang_cuoi]. MỌI tháng
    trong đó phải có file — 404 ở giữa ⇒ từ chối (N6), không lấp."""
    t2 = moc["t2"]
    ket_qua: dict[str, int] = {}
    khung_ghi: list[tuple[Path, pd.DataFrame]] = []
    for lf in SAU_LOAI_FILE:
        dst = dich / ten_file(symbol, lf)
        if dst.exists():
            raise DuLieuRoError(f"file đích đã tồn tại, không ghi đè: {dst}")
        bat_dau = max(moc[lf.tu_moc], _dau_thang(khoang["thang_dau"]))
        thang_cuoi = min(_thang(t2), _thang(_dau_thang(khoang["thang_cuoi"])))
        phan: list[pd.DataFrame] = []
        for nam, thang in cac_thang(_thang(bat_dau), thang_cuoi):
            try:
                hang = doc_csv(
                    loai=lf.loai_kho,
                    symbol=symbol,
                    nam=nam,
                    thang=thang,
                    khung=None if lf.loai_kho == "fundingRate" else lf.khung,
                )
            except NenThangKhongCoError as exc:
                raise DuLieuRoError(
                    f"{symbol} {lf.khung}-{lf.hau_to}: kho thiếu tháng {nam:04d}-{thang:02d} nằm "
                    f"TRONG khoảng tồn tại {khoang['thang_dau']}…{khoang['thang_cuoi']} — không lấp"
                ) from exc
            phan.append(funding_tu_kho(hang) if lf.loai_kho == "fundingRate" else nen_tu_kho(hang, la_mark=lf.loai_kho == "markPriceKlines"))
        if not phan:
            raise DuLieuRoError(f"{symbol} {lf.khung}-{lf.hau_to}: 0 tháng trong khoảng cần")
        df = pd.concat(phan, ignore_index=True).sort_values("date").reset_index(drop=True)
        if df["date"].duplicated().any():
            raise DuLieuRoError(f"{symbol} {lf.khung}-{lf.hau_to}: trùng mốc giữa hai tháng liền kề")
        df = df[(df["date"] >= _moc_ts(moc[lf.tu_moc])) & (df["date"] <= _moc_ts(t2))].reset_index(drop=True)
        if df.empty:
            raise DuLieuRoError(f"{symbol} {lf.khung}-{lf.hau_to}: rỗng sau khi cắt về [{moc[lf.tu_moc]}, {t2}]")
        khung_ghi.append((dst, df))
    # Chỉ ghi khi CẢ 6 loại đã dựng xong — không để lại một mã nửa vời.
    dich.mkdir(parents=True, exist_ok=True)
    for dst, df in khung_ghi:
        df.to_feather(dst)
        ket_qua[dst.name] = len(df)
    return ket_qua


def cat_den_moc(thu_muc: Path, moc_cuoi: date) -> dict[str, int]:
    """Bỏ mọi hàng có `date > moc_cuoi 00:00 UTC` trong mọi `.feather`. Trả {file: số hàng đã bỏ}
    (chỉ file có bỏ). Không thêm hàng nào — không phải backfill (TD-0093)."""
    moc = _moc_ts(moc_cuoi)
    da_cat: dict[str, int] = {}
    for f in sorted(thu_muc.glob("*.feather")):
        df = pd.read_feather(f)
        giu = df[df["date"] <= moc]
        if len(giu) != len(df):
            if giu.empty:
                raise DuLieuRoError(f"{f.name}: toàn bộ nến sau {moc_cuoi} — cắt sẽ rỗng file, dừng")
            giu.reset_index(drop=True).to_feather(f)
            da_cat[f.name] = len(df) - len(giu)
    return da_cat


def kiem_du_lieu_ro(
    thu_muc: Path,
    ro: Sequence[str],
    khoang: Mapping[str, Mapping[str, str]],
    moc: Mapping[str, date],
) -> list[str]:
    """Trả danh sách lỗi (rỗng = đủ). Với mỗi mã × 6 loại file:

      • file tồn tại và không rỗng;
      • không nến nào sau `T2 00:00`;
      • nến ĐẦU ≤ max(mốc bắt đầu của loại, đầu tháng niêm yết) + 31 ngày
        (ngày niêm yết thật nằm trong tháng đầu, kho chỉ cho tháng);
      • nến CUỐI ≥ T2 − 1 ngày nếu mã còn sống qua tháng T2, hoặc ≥ đầu tháng huỷ niêm yết.
    """
    t2 = _moc_ts(moc["t2"])
    loi: list[str] = []
    for s in ro:
        if s not in khoang:
            loi.append(f"{s}: không có khoảng tồn tại TD-0230")
            continue
        k = khoang[s]
        for lf in SAU_LOAI_FILE:
            f = thu_muc / ten_file(s, lf)
            if not f.is_file():
                loi.append(f"{f.name}: THIẾU")
                continue
            df = pd.read_feather(f, columns=["date"])
            if df.empty:
                loi.append(f"{f.name}: RỖNG")
                continue
            dau, cuoi = df["date"].min(), df["date"].max()
            if cuoi > t2:
                loi.append(f"{f.name}: có nến sau T2 ({cuoi})")
            bat_dau_can = max(moc[lf.tu_moc], _dau_thang(k["thang_dau"]))
            if dau > _moc_ts(bat_dau_can) + pd.Timedelta(days=31):
                loi.append(f"{f.name}: bắt đầu {dau.date()} muộn hơn cần ({bat_dau_can} + 31 ngày)")
            if _thang(_dau_thang(k["thang_cuoi"])) > _thang(moc["t2"]):
                if cuoi < t2 - pd.Timedelta(days=1):
                    loi.append(f"{f.name}: kết thúc {cuoi} sớm hơn T2 − 1 ngày dù mã còn sống")
            elif cuoi < _moc_ts(_dau_thang(k["thang_cuoi"])):
                loi.append(f"{f.name}: kết thúc {cuoi.date()} trước tháng huỷ niêm yết {k['thang_cuoi']}")
    return loi
