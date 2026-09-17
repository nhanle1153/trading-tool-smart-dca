"""TD-0247 (`DR-D1-03` §4) — dữ liệu `[T0,T2]` cho rổ `T1` trong `user_data/data/pool_t1/futures/`.

Bốn thao tác, mỗi thao tác một hàm, không hàm nào gọi hàm nào:

  • `sao_chep_ma_co_san()`  — 55 mã đã đủ file ở `binance/`: chép nguyên byte, kiểm sha256.
  • `nhap_ma_tu_kho()`      — mã đã huỷ niêm yết: nhập từ kho (`tool_d.data.kho_luu_tru`).
  • `cat_den_moc()`         — cắt nến sau `T2` (bug TD-0093: `download-data` lấn quá mốc cuối).
  • `kiem_du_lieu_ro()`     — kiểm đủ rổ bằng máy trước khi coi `TD-0247` xong.

`DR-D1-03` §5: mã ngừng giao dịch trước `T2` được CẮT tại nến 1h futures cuối có
`volume > 0` (`moc_ngung_giao_dich()`); sau mốc đó kho vẫn sinh nến phẳng giá thanh
toán, volume 0, không funding — giữ lại là cho backtest vào lệnh ma.

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
from tool_d.ledger.timerange import (
    DatasetBoundary,
    TimerangeViolationError,
    assert_dataset_timerange,
)


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

#: `DR-D1-05` §3 — năm loại của rổ `T0` TRƯỚC `TD-0252` (không 5m). Giữ lại vì `TD-0301` đã
#: chép/nhập 715 file theo đúng kế hoạch này: nó là mô tả của thứ ĐANG NẰM trên đĩa, và là
#: đầu vào cho đường bổ sung ở `nhap_them_loai_file()`.
NAM_LOAI_FILE_T0: tuple[LoaiFile, ...] = tuple(lf for lf in SAU_LOAI_FILE if lf.khung != "5m")

#: `DR-D1-05` §3b.1 (`TD-0252`) — 5m của rổ `T0` bắt đầu từ `t0`, KHÁC 5m của rổ `T1` (từ `t1`).
#: Hai rổ cần hai mốc bắt đầu khác nhau cho cùng một khung, nên đây là `LoaiFile` RIÊNG chứ không
#: phải sửa trường `tu_moc` của `SAU_LOAI_FILE` — sửa tại chỗ sẽ làm 107 mã rổ `T1` (đã đủ 6 file,
#: 5m phủ `[T1,T2]`) bị `kiem_du_lieu_ro()` coi là "thiếu đầu" và phải tải lại toàn bộ.
LOAI_5M_T0: LoaiFile = LoaiFile("5m", "futures", "klines", "t0")

#: `DR-D1-05` §3b.1 — kế hoạch đầy đủ của rổ `T0`. 5m đặt CUỐI: `nhap_ma_tu_kho()` đòi phần tử 0
#: là 1h futures (dùng để đo mốc ngừng giao dịch).
SAU_LOAI_FILE_T0: tuple[LoaiFile, ...] = NAM_LOAI_FILE_T0 + (LOAI_5M_T0,)

#: Theo tên rổ: (kế hoạch file, tên mốc CUỐI của dữ liệu). File đầu tiên PHẢI là 1h futures
#: (dùng để đo mốc ngừng giao dịch).
KE_HOACH_THEO_RO: dict[str, tuple[tuple[LoaiFile, ...], str]] = {
    "t0": (SAU_LOAI_FILE_T0, "t1"),
    "t1": (SAU_LOAI_FILE, "t2"),
}


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


#: `DR-D1-03` §5 — đuôi ≥ số nến 1h liền nhau `volume = 0` ở cuối file thì coi là nến chết.
NEN_CHET_TOI_THIEU = 24


def moc_ngung_giao_dich(nen_1h: pd.DataFrame, t2: date) -> pd.Timestamp | None:
    """Mốc mở của nến 1h futures CUỐI có `volume > 0`, nếu nó sớm hơn `T2 − 1 giờ`;
    `None` nếu mã còn giao dịch tới `T2`. Raise nếu không có nến nào có giao dịch."""
    co_gd = nen_1h[nen_1h["volume"] > 0]
    if co_gd.empty:
        raise DuLieuRoError("không có nến 1h nào có volume > 0 — không đo được mốc ngừng giao dịch")
    cuoi = co_gd["date"].max()
    return cuoi if cuoi < _moc_ts(t2) - pd.Timedelta(hours=1) else None


def duoi_nen_chet(nen_1h: pd.DataFrame) -> int:
    """Số nến 1h liền nhau ở CUỐI file có `volume = 0`."""
    dem = 0
    for v in reversed(nen_1h["volume"].tolist()):
        if v > 0:
            break
        dem += 1
    return dem


@dataclass(frozen=True)
class KetQuaNhap:
    so_hang: dict[str, int]
    moc_ngung: pd.Timestamp | None
    gia_dong_cuoi: float  # giá đóng nến 1h CUỐI được giữ (nến giao dịch cuối nếu có mốc ngừng)


def sao_chep_ma_co_san(
    nguon: Path, dich: Path, ma: Sequence[str], *, loai_file: Sequence[LoaiFile] = SAU_LOAI_FILE
) -> list[str]:
    """Chép nguyên byte các file `loai_file` của từng mã; kiểm sha256 sau chép. Trả tên file đã chép.

    Từ chối (trước khi chép file nào) nếu: thiếu file nguồn, hoặc file đích đã tồn tại."""
    viec: list[tuple[Path, Path]] = []
    for s in ma:
        for lf in loai_file:
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


def _dung_khung(
    *,
    symbol: str,
    lf: LoaiFile,
    khoang: Mapping[str, str],
    moc: Mapping[str, date],
    doc_csv: Callable[..., list[list[str]]],
    thang_cuoi: tuple[int, int],
) -> pd.DataFrame:
    """Dựng MỘT khung của một mã từ các file tháng của kho, cắt về `>= moc[lf.tu_moc]`.

    Tách khỏi `nhap_ma_tu_kho()` (TD-0252) để `nhap_them_loai_file()` dùng lại **cùng một**
    đường dựng — không chép luật ra chỗ thứ hai. Không cắt mốc CUỐI: người gọi cắt, vì mốc
    cuối hiệu dụng phụ thuộc mốc ngừng giao dịch mà chỉ người gọi biết.
    """
    bat_dau = max(moc[lf.tu_moc], _dau_thang(khoang["thang_dau"]))
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
                f"TRONG khoảng cần tải (trước mốc cuối hiệu dụng) — không lấp"
            ) from exc
        phan.append(
            funding_tu_kho(hang)
            if lf.loai_kho == "fundingRate"
            else nen_tu_kho(hang, la_mark=lf.loai_kho == "markPriceKlines")
        )
    if not phan:
        raise DuLieuRoError(f"{symbol} {lf.khung}-{lf.hau_to}: 0 tháng trong khoảng cần")
    df = pd.concat(phan, ignore_index=True).sort_values("date").reset_index(drop=True)
    if df["date"].duplicated().any():
        raise DuLieuRoError(f"{symbol} {lf.khung}-{lf.hau_to}: trùng mốc giữa hai tháng liền kề")
    return df[df["date"] >= _moc_ts(moc[lf.tu_moc])].reset_index(drop=True)


def nhap_ma_tu_kho(
    symbol: str,
    *,
    dich: Path,
    khoang: Mapping[str, str],
    moc: Mapping[str, date],
    doc_csv: Callable[..., list[list[str]]],
    loai_file: Sequence[LoaiFile] = SAU_LOAI_FILE,
    moc_cuoi: str = "t2",
) -> KetQuaNhap:
    """Nhập 6 file cho một mã từ kho. `khoang = {"thang_dau", "thang_cuoi"}` (TD-0230);
    `moc = {"t0", "t1", "t2"}`.

    Thứ tự: dựng nến 1h futures trước ⇒ đo mốc ngừng giao dịch (§5) ⇒ mốc cuối hiệu
    dụng = mốc ngừng (nếu có) hoặc `T2`. Tháng cần tải = giao của [mốc bắt đầu, mốc cuối]
    với [thang_dau, thang_cuoi]; MỌI tháng đó phải có file — 404 ⇒ từ chối (N6).
    Chỉ ghi khi cả 6 loại đã dựng xong."""
    if loai_file[0] != SAU_LOAI_FILE[0]:
        raise DuLieuRoError("kế hoạch file phải bắt đầu bằng 1h futures (đo mốc ngừng giao dịch)")
    t2 = moc[moc_cuoi]  # mốc CUỐI của dữ liệu rổ (tên biến giữ từ bản T1)
    for lf in loai_file:
        if (dich / ten_file(symbol, lf)).exists():
            raise DuLieuRoError(f"file đích đã tồn tại, không ghi đè: {dich / ten_file(symbol, lf)}")

    def _dung(lf: LoaiFile, thang_cuoi: tuple[int, int]) -> pd.DataFrame:
        return _dung_khung(
            symbol=symbol, lf=lf, khoang=khoang, moc=moc, doc_csv=doc_csv, thang_cuoi=thang_cuoi
        )

    thang_cuoi_kho = min(_thang(t2), _thang(_dau_thang(khoang["thang_cuoi"])))
    nen_1h = _dung(loai_file[0], thang_cuoi_kho)
    nen_1h = nen_1h[nen_1h["date"] <= _moc_ts(t2)].reset_index(drop=True)
    moc_ngung = moc_ngung_giao_dich(nen_1h, t2)
    moc_cuoi = moc_ngung if moc_ngung is not None else _moc_ts(t2)
    thang_cuoi = min(thang_cuoi_kho, (moc_cuoi.year, moc_cuoi.month))

    khung_ghi: list[tuple[Path, pd.DataFrame]] = []
    for lf in loai_file:
        df = nen_1h if lf is loai_file[0] else _dung(lf, thang_cuoi)
        df = df[df["date"] <= moc_cuoi].reset_index(drop=True)
        if df.empty:
            raise DuLieuRoError(f"{symbol} {lf.khung}-{lf.hau_to}: rỗng sau khi cắt về [{moc[lf.tu_moc]}, {moc_cuoi}]")
        khung_ghi.append((dich / ten_file(symbol, lf), df))

    dich.mkdir(parents=True, exist_ok=True)
    so_hang: dict[str, int] = {}
    for dst, df in khung_ghi:
        df.to_feather(dst)
        so_hang[dst.name] = len(df)
    nen_cuoi_giu = nen_1h[nen_1h["date"] <= moc_cuoi]
    return KetQuaNhap(so_hang=so_hang, moc_ngung=moc_ngung, gia_dong_cuoi=float(nen_cuoi_giu["close"].iloc[-1]))


def nhap_them_loai_file(
    symbol: str,
    *,
    dich: Path,
    khoang: Mapping[str, str],
    moc: Mapping[str, date],
    doc_csv: Callable[..., list[list[str]]],
    loai_file: Sequence[LoaiFile],
    moc_cuoi: str = "t1",
    moc_ngung: pd.Timestamp | None = None,
) -> dict[str, int]:
    """TD-0252 (`DR-D1-05` §3b) — nhập THÊM các loại file còn thiếu cho một mã ĐÃ có sẵn các
    loại khác trong `dich`. Trả `{tên file: số hàng}`.

    Khác `nhap_ma_tu_kho()` ở đúng một điểm, và điểm đó là lý do hàm này tồn tại: nó **không đo**
    mốc ngừng giao dịch. Mốc do người gọi cấp (`moc_ngung`), đọc từ artifact đã ghi lúc nhập
    lần đầu. Đo lại trên khung khác có thể ra mốc khác mốc của file `1h` cùng mã ⇒ hai file cùng
    mã kết thúc lệch nhau ⇒ `kiem_du_lieu_ro()` báo đỏ. Vì thế hàm này cũng KHÔNG ghi artifact.

    Fail-closed, theo thứ tự kiểm:
      • `loai_file` rỗng ⇒ từ chối (không im lặng làm 0 file rồi báo thành công);
      • bất kỳ file đích nào đã tồn tại ⇒ từ chối, **không ghi file nào** (không ghi đè);
      • `moc_ngung` muộn hơn mốc cuối của rổ ⇒ từ chối (cấp nhầm artifact của rổ khác);
      • dựng xong HẾT rồi mới ghi (tất-cả-hoặc-không);
      • cắt xong mà rỗng ⇒ từ chối (không ghi file rỗng).
    """
    if not loai_file:
        raise DuLieuRoError(f"{symbol}: danh sách loại file cần nhập thêm rỗng — không có gì để làm")
    moc_cuoi_ro = _moc_ts(moc[moc_cuoi])
    if moc_ngung is not None and moc_ngung > moc_cuoi_ro:
        raise DuLieuRoError(
            f"{symbol}: mốc ngừng {moc_ngung} muộn hơn mốc cuối của rổ ({moc_cuoi_ro}) — "
            f"artifact mốc ngừng có phải của rổ này không?"
        )
    for lf in loai_file:
        if (dich / ten_file(symbol, lf)).exists():
            raise DuLieuRoError(f"file đích đã tồn tại, không ghi đè: {dich / ten_file(symbol, lf)}")

    moc_hieu_dung = moc_ngung if moc_ngung is not None else moc_cuoi_ro
    thang_cuoi = min(
        _thang(_dau_thang(khoang["thang_cuoi"])), (moc_hieu_dung.year, moc_hieu_dung.month)
    )

    khung_ghi: list[tuple[Path, pd.DataFrame]] = []
    for lf in loai_file:
        df = _dung_khung(
            symbol=symbol, lf=lf, khoang=khoang, moc=moc, doc_csv=doc_csv, thang_cuoi=thang_cuoi
        )
        df = df[df["date"] <= moc_hieu_dung].reset_index(drop=True)
        if df.empty:
            raise DuLieuRoError(
                f"{symbol} {lf.khung}-{lf.hau_to}: rỗng sau khi cắt về "
                f"[{moc[lf.tu_moc]}, {moc_hieu_dung}]"
            )
        khung_ghi.append((dich / ten_file(symbol, lf), df))

    dich.mkdir(parents=True, exist_ok=True)
    so_hang: dict[str, int] = {}
    for dst, df in khung_ghi:
        df.to_feather(dst)
        so_hang[dst.name] = len(df)
    return so_hang


def kiem_pham_vi_dataset(
    thu_muc: Path,
    ro: Sequence[str],
    loai_file: Sequence[LoaiFile],
    *,
    dataset: str,
    boundary: DatasetBoundary,
) -> list[str]:
    """TD-0252 — nối `assert_dataset_timerange()` (L-Z55) vào dữ liệu rổ THẬT trên đĩa.
    Trả danh sách lỗi (rỗng = không vi phạm).

    Hai vế KHÁC nguồn, đúng điều kiện `DatasetBoundary` đòi: `observed_*` đọc từ chính file
    feather; `boundary` đến từ `tool_d_config.yaml` qua `dataset_boundaries_from_config()`.

    🔴 **Phạm vi, đừng đọc quá tay:** `DatasetBoundary` mang kiểu `date`, nên phép kiểm này chỉ
    phân giải tới NGÀY — một nến `2025-06-12 00:05` vẫn lọt qua đây. Phép kiểm theo MỐC là
    `kiem_du_lieu_ro()` (vế *"có nến sau T1"*). Hàm này **bổ sung**, không **thay thế** hàm đó.
    """
    loi: list[str] = []
    for s in ro:
        for lf in loai_file:
            f = thu_muc / ten_file(s, lf)
            if not f.is_file():
                continue  # THIẾU là việc của kiem_du_lieu_ro(); ở đây không nhân đôi phép kiểm
            try:
                df = pd.read_feather(f, columns=["date"])
            except Exception as exc:
                loi.append(f"{f.name}: KHÔNG ĐỌC ĐƯỢC ({type(exc).__name__}: {exc})")
                continue
            if df.empty:
                continue
            try:
                assert_dataset_timerange(
                    dataset=dataset,
                    observed_start=df["date"].min().date(),
                    observed_end=df["date"].max().date(),
                    boundary=boundary,
                )
            except TimerangeViolationError as exc:
                loi.append(f"{f.name}: {exc}")
    return loi


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
    moc_ngung: Mapping[str, pd.Timestamp] | None = None,
    *,
    loai_file: Sequence[LoaiFile] = SAU_LOAI_FILE,
    moc_cuoi: str = "t2",
) -> list[str]:
    """Trả danh sách lỗi (rỗng = đủ). Với mỗi mã × 6 loại file:

      • file tồn tại và không rỗng;
      • không nến nào sau `T2 00:00`;
      • nến ĐẦU ≤ max(mốc bắt đầu của loại, đầu tháng niêm yết) + 31 ngày
        (ngày niêm yết thật nằm trong tháng đầu, kho chỉ cho tháng);
      • nến CUỐI ≥ T2 − 1 ngày nếu mã còn sống qua tháng T2, hoặc ≥ đầu tháng huỷ niêm yết;
      • `DR-D1-03` §5: mã có trong `moc_ngung` thì mọi file kết thúc trong
        [mốc ngừng − 1 ngày, mốc ngừng]; mã KHÔNG có trong đó mà nến 1h futures có đuôi
        ≥ `NEN_CHET_TOI_THIEU` nến `volume = 0` ⇒ lỗi "đuôi nến chết chưa khai".
    """
    moc_ngung = moc_ngung or {}
    t2 = _moc_ts(moc[moc_cuoi])
    NHAN = moc_cuoi.upper()
    loi: list[str] = []
    for s in ro:
        if s not in khoang:
            loi.append(f"{s}: không có khoảng tồn tại TD-0230")
            continue
        k = khoang[s]
        for lf in loai_file:
            f = thu_muc / ten_file(s, lf)
            if not f.is_file():
                loi.append(f"{f.name}: THIẾU")
                continue
            try:
                df = pd.read_feather(f, columns=["date"])
            except Exception as exc:  # feather hỏng (đứt khi ghi) — một dòng lỗi, không traceback
                loi.append(f"{f.name}: KHÔNG ĐỌC ĐƯỢC ({type(exc).__name__}: {exc})")
                continue
            if df.empty:
                loi.append(f"{f.name}: RỖNG")
                continue
            dau, cuoi = df["date"].min(), df["date"].max()
            if cuoi > t2:
                loi.append(f"{f.name}: có nến sau {NHAN} ({cuoi})")
            if s in moc_ngung:
                ngung = moc_ngung[s]
                if cuoi > ngung or cuoi < ngung - pd.Timedelta(days=1):
                    loi.append(f"{f.name}: kết thúc {cuoi} không khớp mốc ngừng giao dịch {ngung}")
                bat_dau_can = max(moc[lf.tu_moc], _dau_thang(k["thang_dau"]))
                if dau > _moc_ts(bat_dau_can) + pd.Timedelta(days=31):
                    loi.append(f"{f.name}: bắt đầu {dau.date()} muộn hơn cần ({bat_dau_can} + 31 ngày)")
                continue
            # TD-0252: so khung/hậu tố TƯỜNG MINH, không dựa vào VỊ TRÍ phần tử. Với kế hoạch
            # đã lọc (vd chỉ 5m, đường `--chi-loai`), `loai_file[0]` KHÔNG còn là 1h futures và
            # `duoi_nen_chet()` sẽ đếm đuôi volume 0 trên nến 5m — báo động giả.
            if lf.khung == "1h" and lf.hau_to == "futures":
                duoi = duoi_nen_chet(pd.read_feather(f, columns=["volume"]))
                if duoi >= NEN_CHET_TOI_THIEU:
                    loi.append(f"{f.name}: đuôi {duoi} nến 1h volume = 0 — nến chết chưa khai mốc ngừng giao dịch")
            bat_dau_can = max(moc[lf.tu_moc], _dau_thang(k["thang_dau"]))
            if dau > _moc_ts(bat_dau_can) + pd.Timedelta(days=31):
                loi.append(f"{f.name}: bắt đầu {dau.date()} muộn hơn cần ({bat_dau_can} + 31 ngày)")
            if _thang(_dau_thang(k["thang_cuoi"])) > _thang(moc[moc_cuoi]):
                if cuoi < t2 - pd.Timedelta(days=1):
                    loi.append(f"{f.name}: kết thúc {cuoi} sớm hơn {NHAN} − 1 ngày dù mã còn sống")
            elif cuoi < _moc_ts(_dau_thang(k["thang_cuoi"])):
                loi.append(f"{f.name}: kết thúc {cuoi.date()} trước tháng huỷ niêm yết {k['thang_cuoi']}")
    return loi
