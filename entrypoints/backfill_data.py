"""E8 — backfill dữ liệu, sao lưu trước rồi mới verify (spec dòng 662, H19).

TD-0080: chế độ `--probe-coverage` — verify độ dài lịch sử Open Interest
THẬT SỰ Binance trả về. Đây là ĐO METADATA (khoảng thời gian sàn giữ dữ
liệu), KHÔNG PHẢI "chạm dữ liệu" theo nghĩa DR-014 (đánh giá cấu hình
trên CALIB/WFO/LOCKBOX — những tập đó CHƯA được chia, xem TD-0084) — nên
không cần reserve() qua ledger, đi dòng CTRL tự nhiên.

Chế độ backfill THẬT (sao lưu + gộp + verify byte-for-byte, H19, spec
dòng 5376-5377) chưa có mã việc TD riêng tại thời điểm sửa file này —
vẫn TỪ CHỐI như khung TD-0016.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

from tool_d.api_client.binance_public import BinancePublicApiError, get_open_interest_hist
from tool_d.gates.d0_pre import require_d0_pre_complete
from tool_d.measurement.guard import EXIT_GUARD_BLOCKED, GuardOutcome, measurement_guard

ENTRYPOINT = "E8"

EXIT_PROBE_FAILED = 93


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
    return parser


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
