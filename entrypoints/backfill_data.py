"""E8 — backfill dữ liệu, sao lưu trước rồi mới verify (spec dòng 662, H19).

TD-0080: chế độ `--probe-coverage` — verify độ dài lịch sử Open Interest
THẬT SỰ Binance trả về. Đây là ĐO METADATA (khoảng thời gian sàn giữ dữ
liệu), KHÔNG PHẢI "chạm dữ liệu" theo nghĩa DR-014 (đánh giá cấu hình
trên CALIB/WFO/LOCKBOX — những tập đó CHƯA được chia, xem TD-0084) — nên
không cần reserve() qua ledger, đi dòng CTRL tự nhiên.

TD-0091 (H19, spec dòng 4350 + LD-27/28) — hai chế độ GÁC quanh lần tải:

    --snapshot-before   (a) sao lưu thư mục dữ liệu vào `--backup-root`
                        (c) chụp dấu vân tay từng file -> `runs/backfill_snapshot.json`
    --verify-after      (b)(c) so lại: mọi nến trong khoảng CŨ phải còn
                        nguyên từng trường. Vi phạm -> exit 97, kèm chỉ dẫn
                        khôi phục từ bản sao lưu.

Việc TẢI vẫn do `freqtrade download-data` làm (đã kiểm chứng ở TD-0084);
E8 không tự tải — lớp gác không được phụ thuộc vào chính thứ nó giám sát.
Quy trình đúng: `--snapshot-before` → chạy download-data → `--verify-after`.

🔴 Phép so ở (b)/(c) (`--verify-after`) là ở mức NẾN, không phải bytes của
file: gộp thêm nến mới làm bytes đổi một cách HỢP LỆ. Phép so của
`--snapshot-before` (a) (`backup_data_dir()`, TD-0203) thì NGƯỢC LẠI —
byte-đối-byte với nguồn, vì sao lưu không gộp gì cả. Xem
`src/tool_d/data/backfill_guard.py`.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone

from pathlib import Path

from tool_d.api_client.binance_public import (
    BinancePublicApiError,
    get_klines,
    get_open_interest_hist,
)
from tool_d.data.backfill_guard import (
    BackupVerificationError,
    RangeDigest,
    backup_data_dir,
    read_candles,
    snapshot_dir,
    verify_old_candles_preserved,
)
from tool_d.data.coverage import (
    TIMEFRAME_MS,
    cause_from_source_probe,
    compute_coverage,
    render_table,
)
from tool_d.gates.d0_pre import require_d0_pre_complete
from tool_d.measurement.guard import EXIT_GUARD_BLOCKED, GuardOutcome, measurement_guard

ENTRYPOINT = "E8"

EXIT_PROBE_FAILED = 93
EXIT_BACKFILL_UNSAFE = 97  # H19: dữ liệu cũ bị đụng -> DỪNG, không đi tiếp

# H19 — thư mục dữ liệu làm việc (CALIB/WFO). Lockbox có đường riêng, ĐÃ
# niêm phong (TD-0084), không bao giờ backfill thêm vào đó.
DEFAULT_DATA_DIR = Path("user_data/data/binance/futures")

# TD-0203 — TRƯỚC đây `../tool-d-data-backup`: trong container, cwd là
# `/workspace` (`working_dir` của compose) và CHỈ `..:/workspace` được
# mount — `../tool-d-data-backup` resolve ra `/tool-d-data-backup`, KHÔNG
# nằm trên volume nào, và biến mất khi container bị `--rm`. Bằng chứng
# thật: `--snapshot-before` chạy TD-0093 (07/09/2026) không để lại một
# byte nào ở đích (`docs/research-log.md` 09-10/09/2026), dù lệnh báo
# thành công — `backup_data_dir()` (TD-0203) không có cách nào phát hiện
# điều này TỪ BÊN TRONG một tiến trình duy nhất (file THẬT SỰ ở đó tại
# lúc kiểm, chỉ mất SAU KHI tiến trình kết thúc).
#
# Đổi mặc định vào `runs/` — CÙNG quy ước với `--snapshot-out` bên dưới
# (vốn đã mặc định `runs/backfill_snapshot.json`, đã an toàn từ đầu) —
# vì `runs/` luôn nằm TRONG cây làm việc, tức luôn ở trên volume `..:
# /workspace` dù chạy trong Docker hay (theo giả thuyết "route thứ ba"
# của phiên `-46`, TD-0200) trực tiếp trên host. `runs/**` đã có trong
# `.gitignore` — bản sao lưu (có thể hàng trăm MB dữ liệu nến) không bao
# giờ lọt vào git.
DEFAULT_BACKUP_ROOT = Path("runs/backfill_backup")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="E8 backfill_data.py — backfill an toàn (H19)")
    parser.add_argument(
        "--with-params-file",
        action="store_true",
        help="Cho phép chạy dù có <Strategy>.json cạnh strategy (0d.1) — cờ này được ghi vào provenance.",
    )
    parser.add_argument(
        "--probe-coverage",
        action="store_true",
        help="Chỉ đo độ dài lịch sử Open Interest Binance thật sự trả về (TD-0080), không backfill.",
    )
    parser.add_argument("--symbol", default="BTCUSDT", help="Mã dùng để thăm dò (mặc định BTCUSDT).")
    parser.add_argument(
        "--snapshot-before",
        action="store_true",
        help="H19 (a)(c) — sao lưu + chụp dấu vân tay dữ liệu hiện có TRƯỚC khi tải. In file snapshot để truyền cho --verify-after.",
    )
    parser.add_argument(
        "--verify-after",
        metavar="SNAPSHOT_JSON",
        help="H19 (b)(c) — so dữ liệu hiện tại với snapshot: mọi nến CŨ phải còn nguyên. Có vi phạm -> exit 97.",
    )
    parser.add_argument(
        "--data-dir",
        default=str(DEFAULT_DATA_DIR),
        help=f"Thư mục dữ liệu cần gác (mặc định {DEFAULT_DATA_DIR}).",
    )
    parser.add_argument(
        "--backup-root",
        default=str(DEFAULT_BACKUP_ROOT),
        help=(
            f"Nơi đặt bản sao lưu (mặc định {DEFAULT_BACKUP_ROOT}, trong cây làm việc — "
            "TD-0203). Truyền tay một đường dẫn khác là tự chịu trách nhiệm rằng nó bền "
            "vững (vd một volume đã mount thật) — backup_data_dir() không kiểm được điều đó."
        ),
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="H19 — in bảng ĐỘ PHỦ DỮ LIỆU cho --data-dir trong khoảng --from/--to. KHÔNG kết luận nguyên nhân khoảng trống.",
    )
    parser.add_argument(
        "--probe-gap",
        metavar="SYMBOL",
        help="H19/LD-28 — hỏi LẠI SÀN đúng cửa sổ --from/--to cho SYMBOL (vd BTCUSDT). Đây là cách DUY NHẤT kết luận nguyên nhân khoảng trống.",
    )
    parser.add_argument("--from", dest="range_from", help="Mốc đầu, YYYY-MM-DD (UTC).")
    parser.add_argument("--to", dest="range_to", help="Mốc cuối, YYYY-MM-DD (UTC).")
    parser.add_argument("--timeframe", default="1h", help="Khung thời gian (mặc định 1h).")
    parser.add_argument(
        "--candle-type",
        default="futures",
        choices=("futures", "mark"),
        help="Loại nến để tính độ phủ (mặc định futures). `funding_rate` KHÔNG tính được theo khung file — xem ghi chú khi chạy.",
    )
    parser.add_argument(
        "--snapshot-out",
        default="runs/backfill_snapshot.json",
        help="Nơi ghi file snapshot (mặc định runs/backfill_snapshot.json).",
    )
    # TD-0247 / DR-D1-03 §4 — dữ liệu [T0,T2] cho rổ T1 (config/pool_t1.yaml).
    parser.add_argument(
        "--ro-t1-sao-chep",
        action="store_true",
        help=f"Chép nguyên byte mã rổ T1 đã đủ 6 file ở {DEFAULT_DATA_DIR} sang {POOL_T1_DATA_DIR} (không ghi đè).",
    )
    parser.add_argument(
        "--ro-t1-nhap-kho",
        metavar="PAIRS",
        help="Nhập 6 file/mã từ kho data.binance.vision cho các mã (phẩy ngăn cách, vd DEGOUSDT,MKRUSDT) — chỉ dùng cho mã ĐÃ HUỶ niêm yết.",
    )
    parser.add_argument(
        "--cat-den-t2",
        action="store_true",
        help="Cắt mọi nến sau T2 trong --data-dir (bắt buộc truyền --data-dir tường minh). Bug TD-0093.",
    )
    parser.add_argument(
        "--ro-t1-kiem",
        action="store_true",
        help=f"Kiểm đủ rổ T1 trong {POOL_T1_DATA_DIR}: 6 file/mã, không rỗng, không lấn T2, đúng mốc đầu/cuối.",
    )
    # TD-0301 / DR-D1-05 — cùng các thao tác, theo MỐC rổ (t0 = CALIB, t1 = WFO).
    parser.add_argument(
        "--moc",
        choices=sorted(CAU_HINH_RO),
        help="Rổ theo giai đoạn cho --ro-sao-chep / --ro-nhap-kho / --ro-kiem (bắt buộc với ba cờ đó).",
    )
    parser.add_argument("--ro-sao-chep", action="store_true", help="Chép nguyên byte mã rổ --moc đã đủ file từ các thư mục nguồn (không ghi đè).")
    parser.add_argument("--ro-nhap-kho", metavar="PAIRS", help="Nhập từ kho data.binance.vision cho mã ĐÃ HUỶ niêm yết của rổ --moc.")
    parser.add_argument("--ro-kiem", action="store_true", help="Kiểm đủ dữ liệu rổ --moc.")
    # TD-0252 / DR-D1-05 §3b — bổ sung MỘT loại file vào rổ đã có sẵn các loại khác.
    parser.add_argument(
        "--chi-loai",
        metavar="KHUNG",
        help=(
            "Chỉ thao tác trên loại file có khung này trong kế hoạch của --moc (vd 5m). Khung "
            "không có trong kế hoạch ⇒ TỪ CHỐI, không lặng lẽ thành tập rỗng rồi báo thành công."
        ),
    )
    parser.add_argument(
        "--ro-con-thieu",
        action="store_true",
        help="CHỈ IN danh sách mã còn thiếu loại file của --moc/--chi-loai (phẩy ngăn cách). Không ghi gì.",
    )
    parser.add_argument(
        "--ro-do-phu",
        action="store_true",
        help=(
            "Đo độ phủ khung chi tiết bằng ĐÚNG đường backtest đi (history.load_data, "
            "startup_candles=0) và ghi artifact. Thiếu ⇒ exit khác 0."
        ),
    )
    parser.add_argument(
        "--do-phu-out",
        default="docs/du-lieu-do/td0252-do-phu-5m-calib.json",
        help="Nơi ghi artifact độ phủ của --ro-do-phu.",
    )
    parser.add_argument(
        "--cat-den-t1",
        action="store_true",
        help="Cắt mọi nến sau T1 trong --data-dir (bắt buộc --data-dir tường minh) — dữ liệu rổ T0/CALIB.",
    )
    return parser


POOL_T1_DATA_DIR = Path("user_data/data/pool_t1/futures")
POOL_T1_YAML = Path("config/pool_t1.yaml")
NGUON_TD0230 = Path("docs/du-lieu-do/td0230-lech-song-sot-pool.json")
MOC_NGUNG_JSON = Path("docs/du-lieu-do/td0247-moc-ngung-giao-dich.json")
EXIT_RO_T1_LOI = 98

#: `DR-D1-05` — mốc rổ → (thư mục dữ liệu, file rổ, artifact mốc ngừng, các thư mục NGUỒN để chép).
#: Kế hoạch file + mốc cuối lấy từ `pool_t1_du_lieu.KE_HOACH_THEO_RO` (một nguồn).
CAU_HINH_RO: dict[str, tuple[Path, Path, Path, tuple[Path, ...]]] = {
    "t0": (
        Path("user_data/data/pool_t0/futures"),
        Path("config/pool_t0.yaml"),
        Path("docs/du-lieu-do/td0301-moc-ngung-giao-dich-t0.json"),
        (DEFAULT_DATA_DIR, POOL_T1_DATA_DIR),
    ),
    "t1": (POOL_T1_DATA_DIR, POOL_T1_YAML, MOC_NGUNG_JSON, (DEFAULT_DATA_DIR,)),
}


def _loai_file_cho(moc: str, chi_loai: str | None):
    """TD-0252 — kế hoạch file của rổ `moc`, lọc theo `--chi-loai` nếu có.

    Khung không có trong kế hoạch ⇒ `DuLieuRoError`. Không trả tập rỗng: một thao tác trên 0 loại
    file sẽ chạy xong và in ✅ mà không làm gì — đúng hình PASS RỖNG."""
    from tool_d.data.pool_t1_du_lieu import KE_HOACH_THEO_RO, DuLieuRoError

    loai_file, moc_cuoi = KE_HOACH_THEO_RO[moc]
    if chi_loai is None:
        return loai_file, moc_cuoi
    loc = tuple(lf for lf in loai_file if lf.khung == chi_loai)
    if not loc:
        co = sorted({lf.khung for lf in loai_file})
        raise DuLieuRoError(f"--chi-loai {chi_loai!r} không có trong kế hoạch rổ {moc.upper()} (có: {co})")
    return loc, moc_cuoi


def _duong_moc_ngung(moc: str) -> Path:
    # t1 đọc hằng module lúc GỌI (test monkeypatch `MOC_NGUNG_JSON`).
    return MOC_NGUNG_JSON if moc == "t1" else CAU_HINH_RO[moc][2]


def _doc_moc_ngung(moc: str = "t1") -> dict:
    """`DR-D1-03` §5 — {mã: {"moc_ngung": iso, ...}} đã đo khi nhập kho. Chưa có file = rỗng."""
    duong = _duong_moc_ngung(moc)
    if not duong.is_file():
        return {}
    return json.loads(duong.read_text(encoding="utf-8"))["ma"]


def _ghi_moc_ngung(symbol: str, ban_ghi: dict, moc: str = "t1") -> None:
    """Gộp một mã vào artifact; mã đã có với mốc KHÁC ⇒ từ chối (không ghi đè im lặng)."""
    duong = _duong_moc_ngung(moc)
    moc_cuoi = "T2" if moc == "t1" else "T1"
    du_lieu = (
        json.loads(duong.read_text(encoding="utf-8"))
        if duong.is_file()
        else {
            "nguon": f"TD-0247/TD-0301 / DR-D1-03 §5, DR-D1-05 — rổ {moc.upper()}: mốc ngừng giao dịch đo khi nhập kho: "
            f"nến 1h futures CUỐI có volume > 0 (sớm hơn {moc_cuoi} − 1 giờ). Sau mốc, kho sinh nến phẳng giá "
            "thanh toán, volume 0. 0 trial.",
            "ma": {},
        }
    )
    cu = du_lieu["ma"].get(symbol)
    if cu is not None and cu["moc_ngung"] != ban_ghi["moc_ngung"]:
        raise RuntimeError(f"{symbol}: artifact đã ghi mốc {cu['moc_ngung']}, lần đo này ra {ban_ghi['moc_ngung']} — không ghi đè")
    du_lieu["ma"][symbol] = ban_ghi
    duong.write_text(json.dumps(du_lieu, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def _moc_phan_vung() -> dict:
    from datetime import date

    from tool_d.config.loader import load_tool_d_config, resolve

    tho = resolve(load_tool_d_config(), "tier_c.data_split")
    return {k: date.fromisoformat(str(v)) for k, v in tho.items()}


def _ro_va_khoang(moc: str) -> tuple[list[str], dict]:
    import yaml

    ro = list(yaml.safe_load(CAU_HINH_RO[moc][1].read_text(encoding="utf-8"))["trading"])
    khoang = json.loads(NGUON_TD0230.read_text(encoding="utf-8"))["khoang_ton_tai"]
    return ro, khoang


def _ro_t1_va_khoang() -> tuple[list[str], dict]:
    return _ro_va_khoang("t1")


def do_ro_sao_chep(moc: str, chi_loai: str | None = None) -> int:
    """Chép mã đã đủ file theo THỨ TỰ nguồn: mã đủ ở nguồn đầu thì lấy nguồn đầu; mã có một PHẦN
    file ở bất kỳ nguồn nào mà không đủ ở nguồn trước đó ⇒ từ chối, không đoán."""
    from tool_d.data.pool_t1_du_lieu import DuLieuRoError, sao_chep_ma_co_san, ten_file

    thu_muc, _, _, cac_nguon = CAU_HINH_RO[moc]
    try:
        loai_file, _ = _loai_file_cho(moc, chi_loai)
    except DuLieuRoError as exc:
        print(f"🛑 {exc}")
        return EXIT_RO_T1_LOI
    ro, _ = _ro_va_khoang(moc)
    theo_nguon: dict[Path, list[str]] = {n: [] for n in cac_nguon}
    thieu_mot_phan: list[str] = []
    con_lai = 0
    for s in ro:
        chon = None
        for nguon in cac_nguon:
            co = [(nguon / ten_file(s, lf)).is_file() for lf in loai_file]
            if all(co):
                chon = nguon
                break
            if any(co):
                thieu_mot_phan.append(f"{s} @ {nguon}")
                break
        if chon is not None:
            theo_nguon[chon].append(s)
        else:
            con_lai += 1
    if thieu_mot_phan:
        print(f"🛑 {len(thieu_mot_phan)} mã có MỘT PHẦN file ở nguồn — không đoán nên chép hay tải: {thieu_mot_phan}")
        return EXIT_RO_T1_LOI
    try:
        tong = 0
        for nguon, ma in theo_nguon.items():
            if ma:
                tong += len(sao_chep_ma_co_san(nguon, thu_muc, ma, loai_file=loai_file))
    except DuLieuRoError as exc:
        print(f"🛑 {exc}")
        return EXIT_RO_T1_LOI
    chi_tiet = " · ".join(f"{len(m)} mã từ {n}" for n, m in theo_nguon.items())
    print(f"✅ Rổ {moc.upper()}: đã chép {tong} file ({chi_tiet}, sha256 khớp) -> {thu_muc}. Còn {con_lai} mã phải tải/nhập.")
    return 0


def do_ro_t1_sao_chep() -> int:
    return do_ro_sao_chep("t1")


def do_ro_nhap_kho(moc: str, pairs: str, chi_loai: str | None = None) -> int:
    import pandas as pd

    from tool_d.api_client.binance_public import KhoLuuTruError, doc_csv_thang_kho
    from tool_d.data.kho_luu_tru import DuLieuKhoError
    from tool_d.data.pool_t1_du_lieu import DuLieuRoError, nhap_ma_tu_kho, nhap_them_loai_file

    thu_muc = CAU_HINH_RO[moc][0]
    try:
        loai_file, moc_cuoi = _loai_file_cho(moc, chi_loai)
    except DuLieuRoError as exc:
        print(f"🛑 {exc}")
        return EXIT_RO_T1_LOI
    ro, khoang = _ro_va_khoang(moc)
    ma = [x.strip() for x in pairs.split(",") if x.strip()]
    ngoai = [s for s in ma if s not in ro or s not in khoang]
    if not ma or ngoai:
        print(f"🛑 mã không thuộc rổ {moc.upper()} hoặc không có khoảng tồn tại TD-0230: {ngoai or '(rỗng)'}")
        return EXIT_RO_T1_LOI
    moc_ngay = _moc_phan_vung()

    if chi_loai is not None:
        # 🔴 Đường BỔ SUNG (TD-0252). Mốc ngừng giao dịch ĐỌC từ artifact, KHÔNG đo lại — xem
        # `nhap_them_loai_file()`. Artifact vắng mặt ⇒ TỪ CHỐI: thiếu nó thì 18 mã đã ngừng giao
        # dịch trong CALIB sẽ bị cắt tại T1 và nhận một đuôi nến phẳng volume 0 dài nhiều tháng,
        # đúng thứ `DR-D1-03` §5 sinh ra để chặn — và nhánh mã-có-mốc-ngừng của `kiem_du_lieu_ro()`
        # sẽ không chạy, nên không phép kiểm nào báo đỏ.
        duong_artifact = _duong_moc_ngung(moc)
        if not duong_artifact.is_file():
            print(
                f"🛑 --chi-loai cần artifact mốc ngừng giao dịch {duong_artifact} — không có thì "
                f"mã đã ngừng sẽ bị cắt sai mốc trong im lặng. DỪNG."
            )
            return EXIT_RO_T1_LOI
        da_ghi = _doc_moc_ngung(moc)
        print(f"ℹ️  mốc ngừng ĐỌC từ {duong_artifact} ({len(da_ghi)} mã), KHÔNG đo lại.")
        for s in ma:
            ban_ghi = da_ghi.get(s)
            try:
                so_hang = nhap_them_loai_file(
                    s, dich=thu_muc, khoang=khoang[s], moc=moc_ngay, doc_csv=doc_csv_thang_kho,
                    loai_file=loai_file, moc_cuoi=moc_cuoi,
                    moc_ngung=None if ban_ghi is None else pd.Timestamp(ban_ghi["moc_ngung"]),
                )
            except (DuLieuRoError, DuLieuKhoError, KhoLuuTruError) as exc:
                print(f"🛑 {s}: {exc} — DỪNG, mã này không ghi file nào")
                return EXIT_RO_T1_LOI
            ngung = f" · cắt tại mốc ngừng {ban_ghi['moc_ngung']}" if ban_ghi else ""
            print(f"✅ {s}: " + ", ".join(f"{k} {v} hàng" for k, v in so_hang.items()) + ngung)
        return 0

    for s in ma:
        try:
            kq = nhap_ma_tu_kho(
                s, dich=thu_muc, khoang=khoang[s], moc=moc_ngay, doc_csv=doc_csv_thang_kho,
                loai_file=loai_file, moc_cuoi=moc_cuoi,
            )
        except (DuLieuRoError, DuLieuKhoError, KhoLuuTruError) as exc:
            print(f"🛑 {s}: {exc} — DỪNG, các mã trước đã ghi đủ file, mã này không ghi file nào")
            return EXIT_RO_T1_LOI
        if kq.moc_ngung is not None:
            _ghi_moc_ngung(
                s,
                {
                    "moc_ngung": kq.moc_ngung.isoformat(),
                    "gia_dong_nen_cuoi": kq.gia_dong_cuoi,
                    "so_hang_1h_futures": kq.so_hang[f"{s[:-4]}_USDT_USDT-1h-futures.feather"],
                },
                moc,
            )
        ngung = (
            f" · NGỪNG GIAO DỊCH {kq.moc_ngung} (đã cắt, ghi {_duong_moc_ngung(moc)})" if kq.moc_ngung is not None else ""
        )
        print(f"✅ {s}: " + ", ".join(f"{k} {v} hàng" for k, v in kq.so_hang.items()) + ngung)
    return 0


def do_ro_t1_nhap_kho(pairs: str) -> int:
    return do_ro_nhap_kho("t1", pairs)


def do_cat_den_moc(data_dir: Path, ten_moc: str) -> int:
    from tool_d.data.pool_t1_du_lieu import DuLieuRoError, cat_den_moc

    if not data_dir.is_dir():
        print(f"🛑 {data_dir} không tồn tại.")
        return EXIT_RO_T1_LOI
    moc_ngay = _moc_phan_vung()[ten_moc]
    try:
        da_cat = cat_den_moc(data_dir, moc_ngay)
    except DuLieuRoError as exc:
        print(f"🛑 {exc}")
        return EXIT_RO_T1_LOI
    print(f"✅ Cắt về ≤ {moc_ngay} 00:00 UTC: {len(da_cat)} file có nến lấn, bỏ tổng {sum(da_cat.values())} hàng.")
    for k, v in sorted(da_cat.items())[:20]:
        print(f"  - {k}: bỏ {v}")
    return 0


def do_cat_den_t2(data_dir: Path) -> int:
    return do_cat_den_moc(data_dir, "t2")


def do_ro_kiem(moc: str, chi_loai: str | None = None) -> int:
    import pandas as pd

    from tool_d.data.pool_t1_du_lieu import DuLieuRoError, kiem_du_lieu_ro, kiem_pham_vi_dataset

    thu_muc = CAU_HINH_RO[moc][0]
    try:
        loai_file, moc_cuoi = _loai_file_cho(moc, chi_loai)
    except DuLieuRoError as exc:
        print(f"🛑 {exc}")
        return EXIT_RO_T1_LOI
    ro, khoang = _ro_va_khoang(moc)
    moc_ngung = {k: pd.Timestamp(v["moc_ngung"]) for k, v in _doc_moc_ngung(moc).items()}
    loi = kiem_du_lieu_ro(
        thu_muc, ro, khoang, _moc_phan_vung(), moc_ngung, loai_file=loai_file, moc_cuoi=moc_cuoi
    )
    # TD-0252 — L-Z55 trên dữ liệu rổ THẬT. Chỉ rổ `T0` có một dataset đơn để đối chiếu.
    if moc == "t0":
        from tool_d.config.loader import load_tool_d_config
        from tool_d.ledger.timerange import dataset_boundaries_from_config

        bien = dataset_boundaries_from_config(load_tool_d_config())["CALIB"]
        loi = loi + kiem_pham_vi_dataset(thu_muc, ro, loai_file, dataset="CALIB", boundary=bien)
    else:
        print(
            "ℹ️  Bỏ L-Z55 cho rổ T1: dữ liệu rổ đó trải CALIB+WFO ([T0,T2]) nên không có MỘT "
            "dataset đơn nào để đối chiếu — bỏ qua TƯỜNG MINH, không giả vờ đã kiểm."
        )
    NHAN, CUOI = moc.upper(), moc_cuoi.upper()
    if loi:
        print(f"🛑 Rổ {NHAN} CHƯA đủ dữ liệu — {len(loi)} lỗi:")
        for x in loi[:40]:
            print(f"  - {x}")
        if len(loi) > 40:
            print(f"  … và {len(loi) - 40} lỗi nữa")
        return EXIT_RO_T1_LOI
    print(
        f"✅ Rổ {NHAN} đủ dữ liệu: {len(ro)} mã × {len(loai_file)} file, không lấn {CUOI}, đúng mốc đầu/cuối; "
        f"{len(moc_ngung)} mã ngừng giao dịch trước {CUOI} đã cắt đúng mốc: {sorted(moc_ngung)}."
    )
    return 0


def do_ro_t1_kiem() -> int:
    return do_ro_kiem("t1")


def do_ro_con_thieu(moc: str, chi_loai: str | None) -> int:
    """TD-0252 — in danh sách mã còn thiếu loại file đã lọc, phẩy ngăn cách để truyền thẳng vào
    `--ro-nhap-kho`. CHỈ ĐỌC, không ghi gì. Lượt nhập chạy hàng giờ; đứt giữa chừng thì chạy lại
    lệnh này để biết còn những mã nào, thay vì thêm một cờ "bỏ qua file đã có" (phá fail-closed)."""
    from tool_d.data.pool_t1_du_lieu import DuLieuRoError, ten_file

    thu_muc = CAU_HINH_RO[moc][0]
    try:
        loai_file, _ = _loai_file_cho(moc, chi_loai)
    except DuLieuRoError as exc:
        print(f"🛑 {exc}")
        return EXIT_RO_T1_LOI
    ro, _ = _ro_va_khoang(moc)
    thieu = [s for s in ro if any(not (thu_muc / ten_file(s, lf)).is_file() for lf in loai_file)]
    khung = ", ".join(sorted({lf.khung for lf in loai_file}))
    print(f"Rổ {moc.upper()} — {len(thieu)}/{len(ro)} mã còn thiếu loại file khung [{khung}]:")
    print(",".join(thieu) if thieu else "(không mã nào — đủ)")
    return 0


def do_ro_do_phu(moc: str, chi_loai: str | None, out_path: Path) -> int:
    """TD-0252 (`DR-D1-05` §3b.4) — độ phủ khung chi tiết, đo bằng ĐÚNG đường backtest đi.

    Dùng `history.load_data(..., startup_candles=0)` — đúng bộ tham số
    `Backtesting._load_bt_data_detail()` truyền — rồi hỏi đúng câu `backtesting.py:1739` hỏi
    (`pair in self.detail_data`), CỘNG phần mà câu đó không thấy: lỗ hổng GIỮA chuỗi của một mã
    đã có mặt. Đếm file trên đĩa chứng minh file tồn tại, không chứng minh bộ chạy nạp được.

    **0 trial:** không nạp strategy, không tính chỉ báo, không sinh một chỉ số hiệu năng nào —
    cùng tiền lệ TD-0200 (DR-014 §2 chỉ tính *đánh giá cấu hình*).
    """
    import json

    from freqtrade.configuration import TimeRange
    from freqtrade.data import history
    from freqtrade.enums import CandleType

    from tool_d.data.do_phu_chi_tiet import cho_thieu_khung_chi_tiet, tom_tat_theo_ma
    from tool_d.data.pool_t1_du_lieu import DuLieuRoError

    thu_muc = CAU_HINH_RO[moc][0]
    try:
        loai_file, moc_cuoi = _loai_file_cho(moc, chi_loai)
    except DuLieuRoError as exc:
        print(f"🛑 {exc}")
        return EXIT_RO_T1_LOI
    khung_ct = sorted({lf.khung for lf in loai_file})
    if len(khung_ct) != 1:
        print(f"🛑 --ro-do-phu cần ĐÚNG MỘT khung chi tiết, --chi-loai đang cho {khung_ct}.")
        return EXIT_RO_T1_LOI
    khung_ct = khung_ct[0]

    ro, _ = _ro_va_khoang(moc)
    moc_ngay = _moc_phan_vung()
    bat_dau, ket_thuc = moc_ngay[moc], moc_ngay[moc_cuoi]
    cap = [f"{s[:-4]}/USDT:USDT" for s in ro]
    tr = TimeRange("date", "date", int(_to_ms(bat_dau.isoformat()) / 1000), int(_to_ms(ket_thuc.isoformat()) / 1000))

    def _nap(khung: str):
        return history.load_data(
            datadir=thu_muc,
            pairs=cap,
            timeframe=khung,
            timerange=tr,
            startup_candles=0,
            fail_without_data=False,
            data_format="feather",
            candle_type=CandleType.FUTURES,
        )

    nen_chinh, nen_ct = _nap("1h"), _nap(khung_ct)
    thieu = cho_thieu_khung_chi_tiet(nen_chinh, nen_ct)
    bang = tom_tat_theo_ma(nen_chinh, nen_ct, cap)
    tong_nen_ct = sum(len(df) for df in nen_ct.values())

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(
            {
                "nguon": (
                    f"TD-0252 — độ phủ {khung_ct} rổ {moc.upper()} trên [{bat_dau}, {ket_thuc}]. Đo bằng "
                    "history.load_data(startup_candles=0), ĐÚNG bộ tham số Backtesting."
                    "_load_bt_data_detail() truyền; không nạp strategy, không sinh chỉ số hiệu năng. 0 trial."
                ),
                "moc": {moc: str(bat_dau), moc_cuoi: str(ket_thuc)},
                "ro": {"file": str(CAU_HINH_RO[moc][1]), "so_ma": len(ro)},
                "tong": {
                    "nap_duoc_khung_chinh": len(nen_chinh),
                    "nap_duoc_khung_chi_tiet": len(nen_ct),
                    "so_ma_thieu": len(thieu),
                    "tong_nen_chi_tiet": tong_nen_ct,
                },
                "thieu": [
                    {
                        "symbol": t.symbol,
                        "ly_do": t.ly_do,
                        "so_gio_chinh": t.so_gio_chinh,
                        "so_gio_thieu": t.so_gio_thieu,
                        "vi_du_gio": list(t.vi_du_gio),
                    }
                    for t in thieu
                ],
                "theo_ma": bang,
                "ranh_gioi": [
                    "Mẫu số là mã NẠP ĐƯỢC khung chính, không phải toàn rổ (bài học TD-0200: mã "
                    "niêm yết sau mốc chỉ có dữ liệu từ ngày niêm yết).",
                    "H19/LD-28: KHÔNG kết luận nguyên nhân bất kỳ lỗ hổng nào chưa chạy --probe-gap.",
                ],
            },
            ensure_ascii=False,
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"📊 Nạp được khung chính 1h: {len(nen_chinh)}/{len(cap)} mã · {khung_ct}: {len(nen_ct)} mã")
    print(f"   Tổng nến {khung_ct}: {tong_nen_ct:,} · artifact -> {out_path}")
    if thieu:
        print(f"🛑 {len(thieu)} mã CHƯA đủ {khung_ct} — chốt là ĐỦ hoặc TỪ CHỐI, không có mức giữa:")
        for t in thieu[:20]:
            print(f"  - {t.mo_ta()}")
        if len(thieu) > 20:
            print(f"  … và {len(thieu) - 20} mã nữa (xem artifact)")
        print("   Lỗ hổng GIỮA chuỗi: chạy --probe-gap cho đúng cửa sổ đó trước khi kết luận nguyên nhân.")
        return EXIT_RO_T1_LOI
    print(f"✅ Không một giờ khung chính nào thiếu nến {khung_ct}, trên toàn bộ {len(nen_chinh)} mã nạp được.")
    return 0


def do_snapshot_before(*, data_dir: Path, backup_root: Path, out_path: Path) -> int:
    """H19 (a) sao lưu trước + (c) chụp dấu vân tay để verify sau."""
    if not data_dir.is_dir():
        print(f"🛑 {data_dir} chưa tồn tại — chưa có dữ liệu nào để gác. Lần tải ĐẦU TIÊN vào thư mục rỗng không cần H19 (không có gì để mất), nhưng phải chạy --snapshot-before NGAY SAU đó.")
        return EXIT_BACKFILL_UNSAFE
    try:
        dest = backup_data_dir(source_dir=data_dir, dest_root=backup_root)
    except BackupVerificationError as exc:
        print(f"🛑 H19 (a) FAIL — bản sao lưu vừa chép KHÔNG khớp nguồn: {exc}")
        print(f"   Bản sao lưu CŨ ở {backup_root / data_dir.name} chưa hề bị đụng tới.")
        return EXIT_BACKFILL_UNSAFE
    snap = snapshot_dir(data_dir)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({name: asdict(d) for name, d in snap.items()}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"✅ H19 (a) đã sao lưu {data_dir} -> {dest}")
    print(f"✅ H19 (c) đã chụp {len(snap)} file -> {out_path}")
    return 0


def do_verify_after(*, data_dir: Path, snapshot_path: Path) -> int:
    """H19 (b)(c) — mọi nến trong khoảng CŨ phải còn nguyên sau khi tải."""
    if not snapshot_path.is_file():
        print(f"🛑 không đọc được snapshot {snapshot_path} — chạy --snapshot-before TRƯỚC khi tải.")
        return EXIT_BACKFILL_UNSAFE
    raw = json.loads(snapshot_path.read_text(encoding="utf-8"))
    before = {name: RangeDigest(**d) for name, d in raw.items()}
    errors = verify_old_candles_preserved(before, data_dir)
    if errors:
        print(f"🛑 H19 FAIL — dữ liệu CŨ bị đụng ({len(errors)} file). Đây là bẫy LD-27 (ghi đè theo khoảng ngày yêu cầu), KHÔI PHỤC TỪ BẢN SAO LƯU trước khi làm gì tiếp:")
        for e in errors[:20]:
            print(f"  - {e}")
        if len(errors) > 20:
            print(f"  … và {len(errors) - 20} file nữa")
        return EXIT_BACKFILL_UNSAFE
    print(f"✅ H19 PASS — {len(before)} file: mọi nến cũ còn nguyên, lần tải này là GỘP đúng nghĩa.")
    return 0


def _to_ms(day: str) -> int:
    return int(datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)


def do_coverage(
    *, data_dir: Path, timeframe: str, candle_type: str, range_from: str, range_to: str
) -> int:
    """H19 — bảng độ phủ. CỐ Ý không kết luận nguyên nhân bất kỳ khoảng
    trống nào; mọi dòng thiếu đều hiện "chưa kiểm nguồn trực tiếp" cho tới
    khi người vận hành chạy `--probe-gap` cho đúng cửa sổ đó.

    🔴 Chỉ tính cho `futures`/`mark`. File `*-1h-funding_rate.feather` mang
    nhãn `1h` trong TÊN nhưng sàn trả funding mỗi 8 giờ (một số mã 4 giờ) —
    đo nó theo bước 1h ra "thiếu 87,5%" trên 102 file hoàn toàn lành lặn.
    Phát hiện khi chạy lần đầu trên dữ liệu thật. Nhịp funding là thứ SÀN
    quy định, không suy từ chính dữ liệu được (suy ra thì một chuỗi mất
    đều đặn một nửa số điểm vẫn "đủ 100%" — đúng loại chỉ số tự khen mình
    mà H19 sinh ra để chặn). Muốn đo độ phủ funding thì phải khai nhịp từ
    nguồn sàn trước; chưa khai thì KHÔNG in ra một con số nào.
    """
    if not data_dir.is_dir():
        print(f"🛑 {data_dir} không tồn tại.")
        return EXIT_BACKFILL_UNSAFE
    start_ms, end_ms = _to_ms(range_from), _to_ms(range_to)
    n_funding = len(list(data_dir.glob(f"*-{timeframe}-funding_rate.feather")))
    if n_funding:
        print(
            f"ℹ️  Bỏ qua {n_funding} file `funding_rate`: nhịp funding do SÀN quy định "
            "(8h, một số mã 4h), không phải khung ghi trong tên file — chưa khai nhịp "
            "từ nguồn thì không in độ phủ, thay vì in một con số sai.\n"
        )
    rows = []
    for path in sorted(data_dir.glob(f"*-{timeframe}-{candle_type}.feather")):
        m = read_candles(path)
        if not m.is_ok():
            print(f"⚠️  {path.name}: {m.render()}")
            continue
        rows.append(
            compute_coverage(
                m.value,
                name=path.name,
                timeframe=timeframe,
                range_start_ms=start_ms,
                range_end_ms=end_ms,
            )
        )
    if not rows:
        print(f"🛑 không đọc được file {timeframe}-{candle_type} nào trong {data_dir}.")
        return EXIT_BACKFILL_UNSAFE
    print(render_table(rows, only_incomplete=True))
    return 0


def do_probe_gap(*, symbol: str, timeframe: str, range_from: str, range_to: str) -> int:
    """H19/LD-28 — hỏi LẠI SÀN đúng cửa sổ bị trống. Đây là phép kiểm Tool A
    đã bỏ qua và mất nhiều ngày vì nó; nó rẻ tới mức không có lý do bỏ qua."""
    start_ms, end_ms = _to_ms(range_from), _to_ms(range_to)
    try:
        candles = get_klines(
            symbol=symbol, interval=timeframe, start_time_ms=start_ms, end_time_ms=end_ms
        )
    except BinancePublicApiError as exc:
        print(f"🛑 hỏi lại sàn thất bại: {exc} — CHƯA kết luận được nguyên nhân, thử lại.")
        return EXIT_PROBE_FAILED

    expected = (end_ms - start_ms) // TIMEFRAME_MS[timeframe] + 1
    cause = cause_from_source_probe(len(candles))
    print(
        f"Hỏi lại sàn {symbol} {timeframe} [{range_from} → {range_to}]: "
        f"sàn trả về {len(candles)}/{expected} nến."
    )
    print(f"Kết luận (từ nguồn thật, không suy đoán): {cause}")
    return 0


def probe_oi_coverage(symbol: str = "BTCUSDT") -> str:
    """Gọi `GET /futures/data/openInterestHist` với `limit=500` (tối đa
    Binance cho phép) — nếu sàn thật sự giữ ít hơn 500 ngày, số bản ghi
    trả về sẽ ít hơn 500, và đó CHÍNH LÀ độ phủ thật (spec dòng
    4457-4460: nghi vấn ~30 ngày).
    """
    data = get_open_interest_hist(symbol=symbol, period="1d", limit=500)
    if not data:
        return f"probe OI ({symbol}): 0 bản ghi — không đo được"
    oldest = datetime.fromtimestamp(data[0]["timestamp"] / 1000, tz=timezone.utc)
    newest = datetime.fromtimestamp(data[-1]["timestamp"] / 1000, tz=timezone.utc)
    span_days = (newest - oldest).days
    return (
        f"probe OI ({symbol}): {len(data)} bản ghi, "
        f"{oldest.date().isoformat()} -> {newest.date().isoformat()} = {span_days} ngày phủ dữ liệu"
    )


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    args, _ = build_parser().parse_known_args(argv)

    report = measurement_guard(ENTRYPOINT, argv=argv, with_params_file=args.with_params_file)
    if report.outcome is GuardOutcome.BLOCKED:
        return EXIT_GUARD_BLOCKED

    if args.probe_coverage:
        try:
            print(probe_oi_coverage(args.symbol))
        except BinancePublicApiError as exc:
            print(f"🛑 probe thất bại: {exc}")
            return EXIT_PROBE_FAILED
        return 0

    if args.coverage or args.probe_gap:
        gate_exit = require_d0_pre_complete(ENTRYPOINT)
        if gate_exit is not None:
            return gate_exit
        if not (args.range_from and args.range_to):
            print("🛑 cần --from và --to (YYYY-MM-DD).")
            return EXIT_BACKFILL_UNSAFE
        if args.probe_gap:
            return do_probe_gap(
                symbol=args.probe_gap,
                timeframe=args.timeframe,
                range_from=args.range_from,
                range_to=args.range_to,
            )
        return do_coverage(
            data_dir=Path(args.data_dir),
            timeframe=args.timeframe,
            candle_type=args.candle_type,
            range_from=args.range_from,
            range_to=args.range_to,
        )

    if (
        args.ro_t1_sao_chep or args.ro_t1_nhap_kho or args.cat_den_t2 or args.ro_t1_kiem
        or args.ro_sao_chep or args.ro_nhap_kho or args.ro_kiem or args.cat_den_t1
        or args.ro_con_thieu or args.ro_do_phu
    ):
        gate_exit = require_d0_pre_complete(ENTRYPOINT)
        if gate_exit is not None:
            return gate_exit
        if (args.ro_t1_sao_chep or args.ro_t1_nhap_kho or args.ro_t1_kiem) and args.moc not in (None, "t1"):
            print("🛑 cờ --ro-t1-* chỉ cho rổ T1; dùng --ro-sao-chep/--ro-nhap-kho/--ro-kiem với --moc.")
            return EXIT_RO_T1_LOI
        if (
            args.ro_sao_chep or args.ro_nhap_kho or args.ro_kiem
            or args.ro_con_thieu or args.ro_do_phu
        ) and args.moc is None:
            print(
                "🛑 --ro-sao-chep/--ro-nhap-kho/--ro-kiem/--ro-con-thieu/--ro-do-phu "
                "cần --moc TƯỜNG MINH (t0 = CALIB, t1 = WFO)."
            )
            return EXIT_RO_T1_LOI
        if args.chi_loai is not None and not (
            args.ro_sao_chep or args.ro_nhap_kho or args.ro_kiem
            or args.ro_con_thieu or args.ro_do_phu
        ):
            print("🛑 --chi-loai chỉ đi kèm --ro-sao-chep/--ro-nhap-kho/--ro-kiem/--ro-con-thieu/--ro-do-phu.")
            return EXIT_RO_T1_LOI
        if args.ro_t1_sao_chep:
            return do_ro_t1_sao_chep()
        if args.ro_t1_nhap_kho:
            return do_ro_t1_nhap_kho(args.ro_t1_nhap_kho)
        if args.ro_con_thieu:
            return do_ro_con_thieu(args.moc, args.chi_loai)
        if args.ro_do_phu:
            return do_ro_do_phu(args.moc, args.chi_loai, Path(args.do_phu_out))
        if args.ro_sao_chep:
            return do_ro_sao_chep(args.moc, args.chi_loai)
        if args.ro_nhap_kho:
            return do_ro_nhap_kho(args.moc, args.ro_nhap_kho, args.chi_loai)
        if args.cat_den_t2 or args.cat_den_t1:
            if not any(x == "--data-dir" or x.startswith("--data-dir=") for x in argv):
                print("🛑 --cat-den-t1/--cat-den-t2 cần --data-dir TƯỜNG MINH (không cắt thư mục mặc định do vô ý).")
                return EXIT_RO_T1_LOI
            return do_cat_den_moc(Path(args.data_dir), "t2" if args.cat_den_t2 else "t1")
        if args.ro_kiem:
            return do_ro_kiem(args.moc, args.chi_loai)
        return do_ro_t1_kiem()

    if args.snapshot_before or args.verify_after:
        gate_exit = require_d0_pre_complete(ENTRYPOINT)
        if gate_exit is not None:
            return gate_exit
        data_dir = Path(args.data_dir)
        if args.snapshot_before:
            return do_snapshot_before(
                data_dir=data_dir,
                backup_root=Path(args.backup_root),
                out_path=Path(args.snapshot_out),
            )
        return do_verify_after(data_dir=data_dir, snapshot_path=Path(args.verify_after))

    # TD-0090 — từ đây trở xuống là nhánh CHẠM DỮ LIỆU thật (ghi lịch sử
    # giá vào đĩa). `--probe-coverage` ở trên KHÔNG bị gác vì đó là đo
    # metadata, MT-02 cho phép trước cổng (và TD-0080 đã chạy đúng như vậy).
    gate_exit = require_d0_pre_complete(ENTRYPOINT)
    if gate_exit is not None:
        return gate_exit

    raise NotImplementedError(
        "Logic backfill an toàn (H19) chưa viết — chỉ --probe-coverage (TD-0080) đã có."
    )


if __name__ == "__main__":
    sys.exit(main())
