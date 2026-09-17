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
    return parser


POOL_T1_DATA_DIR = Path("user_data/data/pool_t1/futures")
POOL_T1_YAML = Path("config/pool_t1.yaml")
NGUON_TD0230 = Path("docs/du-lieu-do/td0230-lech-song-sot-pool.json")
MOC_NGUNG_JSON = Path("docs/du-lieu-do/td0247-moc-ngung-giao-dich.json")
EXIT_RO_T1_LOI = 98


def _doc_moc_ngung() -> dict:
    """`DR-D1-03` §5 — {mã: {"moc_ngung": iso, ...}} đã đo khi nhập kho. Chưa có file = rỗng."""
    if not MOC_NGUNG_JSON.is_file():
        return {}
    return json.loads(MOC_NGUNG_JSON.read_text(encoding="utf-8"))["ma"]


def _ghi_moc_ngung(symbol: str, ban_ghi: dict) -> None:
    """Gộp một mã vào artifact; mã đã có với mốc KHÁC ⇒ từ chối (không ghi đè im lặng)."""
    du_lieu = (
        json.loads(MOC_NGUNG_JSON.read_text(encoding="utf-8"))
        if MOC_NGUNG_JSON.is_file()
        else {
            "nguon": "TD-0247 / DR-D1-03 §5 — mốc ngừng giao dịch đo khi nhập kho: nến 1h futures CUỐI có "
            "volume > 0 (sớm hơn T2 − 1 giờ). Sau mốc, kho sinh nến phẳng giá thanh toán, volume 0. 0 trial.",
            "ma": {},
        }
    )
    cu = du_lieu["ma"].get(symbol)
    if cu is not None and cu["moc_ngung"] != ban_ghi["moc_ngung"]:
        raise RuntimeError(f"{symbol}: artifact đã ghi mốc {cu['moc_ngung']}, lần đo này ra {ban_ghi['moc_ngung']} — không ghi đè")
    du_lieu["ma"][symbol] = ban_ghi
    MOC_NGUNG_JSON.write_text(json.dumps(du_lieu, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def _moc_phan_vung() -> dict:
    from datetime import date

    from tool_d.config.loader import load_tool_d_config, resolve

    tho = resolve(load_tool_d_config(), "tier_c.data_split")
    return {k: date.fromisoformat(str(v)) for k, v in tho.items()}


def _ro_t1_va_khoang() -> tuple[list[str], dict]:
    import yaml

    ro = list(yaml.safe_load(POOL_T1_YAML.read_text(encoding="utf-8"))["trading"])
    khoang = json.loads(NGUON_TD0230.read_text(encoding="utf-8"))["khoang_ton_tai"]
    return ro, khoang


def do_ro_t1_sao_chep() -> int:
    from tool_d.data.pool_t1_du_lieu import SAU_LOAI_FILE, DuLieuRoError, sao_chep_ma_co_san, ten_file

    ro, _ = _ro_t1_va_khoang()
    du, thieu_mot_phan = [], []
    for s in ro:
        co = [(DEFAULT_DATA_DIR / ten_file(s, lf)).is_file() for lf in SAU_LOAI_FILE]
        if all(co):
            du.append(s)
        elif any(co):
            thieu_mot_phan.append(s)
    if thieu_mot_phan:
        print(f"🛑 {len(thieu_mot_phan)} mã có MỘT PHẦN file ở {DEFAULT_DATA_DIR} — không đoán nên chép hay tải: {thieu_mot_phan}")
        return EXIT_RO_T1_LOI
    try:
        da_chep = sao_chep_ma_co_san(DEFAULT_DATA_DIR, POOL_T1_DATA_DIR, du)
    except DuLieuRoError as exc:
        print(f"🛑 {exc}")
        return EXIT_RO_T1_LOI
    print(f"✅ Đã chép {len(du)} mã ({len(da_chep)} file, sha256 khớp) -> {POOL_T1_DATA_DIR}. Còn {len(ro) - len(du)} mã phải tải/nhập.")
    return 0


def do_ro_t1_nhap_kho(pairs: str) -> int:
    from tool_d.api_client.binance_public import KhoLuuTruError, doc_csv_thang_kho
    from tool_d.data.kho_luu_tru import DuLieuKhoError
    from tool_d.data.pool_t1_du_lieu import DuLieuRoError, nhap_ma_tu_kho

    ro, khoang = _ro_t1_va_khoang()
    ma = [x.strip() for x in pairs.split(",") if x.strip()]
    ngoai = [s for s in ma if s not in ro or s not in khoang]
    if not ma or ngoai:
        print(f"🛑 mã không thuộc rổ T1 hoặc không có khoảng tồn tại TD-0230: {ngoai or '(rỗng)'}")
        return EXIT_RO_T1_LOI
    moc = _moc_phan_vung()
    for s in ma:
        try:
            kq = nhap_ma_tu_kho(s, dich=POOL_T1_DATA_DIR, khoang=khoang[s], moc=moc, doc_csv=doc_csv_thang_kho)
        except (DuLieuRoError, DuLieuKhoError, KhoLuuTruError) as exc:
            print(f"🛑 {s}: {exc} — DỪNG, các mã trước đã ghi đủ 6 file, mã này không ghi file nào")
            return EXIT_RO_T1_LOI
        if kq.moc_ngung is not None:
            _ghi_moc_ngung(
                s,
                {
                    "moc_ngung": kq.moc_ngung.isoformat(),
                    "gia_dong_nen_cuoi": kq.gia_dong_cuoi,
                    "so_hang_1h_futures": kq.so_hang[f"{s[:-4]}_USDT_USDT-1h-futures.feather"],
                },
            )
        ngung = f" · NGỪNG GIAO DỊCH {kq.moc_ngung} (đã cắt, ghi {MOC_NGUNG_JSON})" if kq.moc_ngung is not None else ""
        print(f"✅ {s}: " + ", ".join(f"{k} {v} hàng" for k, v in kq.so_hang.items()) + ngung)
    return 0


def do_cat_den_t2(data_dir: Path) -> int:
    from tool_d.data.pool_t1_du_lieu import DuLieuRoError, cat_den_moc

    if not data_dir.is_dir():
        print(f"🛑 {data_dir} không tồn tại.")
        return EXIT_RO_T1_LOI
    t2 = _moc_phan_vung()["t2"]
    try:
        da_cat = cat_den_moc(data_dir, t2)
    except DuLieuRoError as exc:
        print(f"🛑 {exc}")
        return EXIT_RO_T1_LOI
    print(f"✅ Cắt về ≤ {t2} 00:00 UTC: {len(da_cat)} file có nến lấn, bỏ tổng {sum(da_cat.values())} hàng.")
    for k, v in sorted(da_cat.items())[:20]:
        print(f"  - {k}: bỏ {v}")
    return 0


def do_ro_t1_kiem() -> int:
    from tool_d.data.pool_t1_du_lieu import kiem_du_lieu_ro

    ro, khoang = _ro_t1_va_khoang()
    import pandas as pd

    moc_ngung = {k: pd.Timestamp(v["moc_ngung"]) for k, v in _doc_moc_ngung().items()}
    loi = kiem_du_lieu_ro(POOL_T1_DATA_DIR, ro, khoang, _moc_phan_vung(), moc_ngung)
    if loi:
        print(f"🛑 Rổ T1 CHƯA đủ dữ liệu — {len(loi)} lỗi:")
        for x in loi[:40]:
            print(f"  - {x}")
        if len(loi) > 40:
            print(f"  … và {len(loi) - 40} lỗi nữa")
        return EXIT_RO_T1_LOI
    print(
        f"✅ Rổ T1 đủ dữ liệu: {len(ro)} mã × 6 file, không lấn T2, đúng mốc đầu/cuối; "
        f"{len(moc_ngung)} mã ngừng giao dịch trước T2 đã cắt đúng mốc: {sorted(moc_ngung)}."
    )
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

    if args.ro_t1_sao_chep or args.ro_t1_nhap_kho or args.cat_den_t2 or args.ro_t1_kiem:
        gate_exit = require_d0_pre_complete(ENTRYPOINT)
        if gate_exit is not None:
            return gate_exit
        if args.ro_t1_sao_chep:
            return do_ro_t1_sao_chep()
        if args.ro_t1_nhap_kho:
            return do_ro_t1_nhap_kho(args.ro_t1_nhap_kho)
        if args.cat_den_t2:
            if not any(x == "--data-dir" or x.startswith("--data-dir=") for x in argv):
                print("🛑 --cat-den-t2 cần --data-dir TƯỜNG MINH (không cắt thư mục mặc định do vô ý).")
                return EXIT_RO_T1_LOI
            return do_cat_den_t2(Path(args.data_dir))
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
