"""E8 — backfill dữ liệu, sao lưu trước rồi mới verify (spec dòng 662, H19).

TD-0080: chế độ `--probe-coverage` — verify độ dài lịch sử Open Interest
THẬT SỰ Binance trả về. Đây là ĐO METADATA (khoảng thời gian sàn giữ dữ
liệu), KHÔNG PHẢI "chạm dữ liệu" theo nghĩa DR-014 (đánh giá cấu hình
trên CALIB/WFO/LOCKBOX — những tập đó CHƯA được chia, xem TD-0084) — nên
không cần reserve() qua ledger, đi dòng CTRL tự nhiên.

TD-0091 (H19, spec dòng 4350 + LD-27/28) — hai chế độ GÁC quanh lần tải:

    --snapshot-before   (a) sao lưu thư mục dữ liệu ra NGOÀI repo
                        (c) chụp dấu vân tay từng file -> `runs/backfill_snapshot.json`
    --verify-after      (b)(c) so lại: mọi nến trong khoảng CŨ phải còn
                        nguyên từng trường. Vi phạm -> exit 97, kèm chỉ dẫn
                        khôi phục từ bản sao lưu.

Việc TẢI vẫn do `freqtrade download-data` làm (đã kiểm chứng ở TD-0084);
E8 không tự tải — lớp gác không được phụ thuộc vào chính thứ nó giám sát.
Quy trình đúng: `--snapshot-before` → chạy download-data → `--verify-after`.

🔴 Phép so là ở mức NẾN, không phải bytes của file: gộp thêm nến mới làm
bytes đổi một cách HỢP LỆ. Xem `src/tool_d/data/backfill_guard.py`.
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
DEFAULT_BACKUP_ROOT = Path("../tool-d-data-backup")


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
        help=f"Nơi đặt bản sao lưu, NGOÀI repo (mặc định {DEFAULT_BACKUP_ROOT}).",
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
    return parser


def do_snapshot_before(*, data_dir: Path, backup_root: Path, out_path: Path) -> int:
    """H19 (a) sao lưu trước + (c) chụp dấu vân tay để verify sau."""
    if not data_dir.is_dir():
        print(f"🛑 {data_dir} chưa tồn tại — chưa có dữ liệu nào để gác. Lần tải ĐẦU TIÊN vào thư mục rỗng không cần H19 (không có gì để mất), nhưng phải chạy --snapshot-before NGAY SAU đó.")
        return EXIT_BACKFILL_UNSAFE
    dest = backup_data_dir(source_dir=data_dir, dest_root=backup_root)
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
