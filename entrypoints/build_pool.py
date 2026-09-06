"""E7 — chốt pool giao dịch (TD-0083) + tập EXPLORE (§0.3, §0.3b, §9c.4b).

🔴 H1-D ĐẦY ĐỦ (pairlist point-in-time chống survivorship bias khi
backtest xuyên nhiều mốc thời gian, spec dòng 4354) là việc RIÊNG của D1
(xem TASKS.md "Việc đã biết là sẽ có, chưa mở") — CHƯA viết ở đây.
TD-0083 chỉ làm việc HẸP HƠN: CHỐT MỘT LẦN danh sách pool giao dịch +
tập EXPLORE tại thời điểm hiện tại, tiêu 4 trial B0 (DR-D0PRE-05).

Khung TD-0016: `main()` gọi `measurement_guard()` ở dòng đầu tiên. Ghi
`config/pool.yaml` — MỘT LẦN, không được chọn lại sau khi thấy overlap
với Tool A (spec dòng 350-352): nếu file đã tồn tại, TỪ CHỐI ghi đè.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from tool_d.api_client.binance_public import BinancePublicApiError, get_exchange_info, get_ticker_24hr
from tool_d.gates.dsr import N_DANG_KY
from tool_d.ledger.registry import BudgetExhaustedError, TrialLedger
from tool_d.measurement.gitinfo import get_git_info
from tool_d.measurement.guard import EXIT_GUARD_BLOCKED, GuardOutcome, measurement_guard
from tool_d.pool import build_symbol_stats, compute_pool

ENTRYPOINT = "E7"

# DR-D0PRE-05 — chốt theo lý do độc lập, KHÔNG suy ngược từ pool_size_target.
AGE_FLOOR_DAYS = 180
VOLUME_FLOOR_USDT = 15_000_000.0

POOL_OUTPUT_PATH = Path("config/pool.yaml")

EXIT_POOL_ALREADY_COMMITTED = 94
EXIT_FETCH_FAILED = 95
EXIT_BUDGET_EXHAUSTED = 96

# 4 tiêu chí §0.3 — mỗi tiêu chí tiêu đúng 1 trial B0, KHÔNG phân biệt
# việc kết luận có ra một con số ngưỡng hay không (DR-D0PRE-05 mục 3/5).
CRITERIA = (
    (
        "volume_24h_usdt",
        VOLUME_FLOOR_USDT,
        "Ngưỡng 15.000.000 USDT/ngày — đủ sâu để volume_ratio (ZSS) không "
        "bị chi phối bởi vài lệnh cá biệt (DR-D0PRE-05 mục 2.i)",
    ),
    (
        "listing_age_days",
        AGE_FLOOR_DAYS,
        "Ngưỡng 180 ngày — đủ lịch sử liên tục cho CALIB/WFO, loại mã mới "
        "niêm yết đang biến động bất thường (DR-D0PRE-05 mục 2.ii)",
    ),
    (
        "post_only_cost_economics",
        None,
        "Không cần ngưỡng riêng — thuộc tính chung của sàn, thoả gián "
        "tiếp qua ngưỡng volume (DR-D0PRE-05 mục 2.iii)",
    ),
    (
        "tp_opposite_zone_distance",
        None,
        "Không cần ngưỡng pool tĩnh — kiểm tại thời điểm vào lệnh, không "
        "phải thuộc tính tĩnh của một mã (DR-D0PRE-05 mục 2.iv)",
    ),
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="E7 build_pool.py — chốt pool giao dịch (TD-0083)")
    parser.add_argument(
        "--with-params-file",
        action="store_true",
        help="Cho phép chạy dù có <Strategy>.json cạnh strategy (0d.1) — cờ này được ghi vào provenance.",
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Thực sự tiêu 4 trial B0 và ghi config/pool.yaml. Thiếu cờ này chỉ IN kết quả (chạy thử, không ghi sổ).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    args, _ = build_parser().parse_known_args(argv)

    report = measurement_guard(ENTRYPOINT, argv=argv, with_params_file=args.with_params_file)
    if report.outcome is GuardOutcome.BLOCKED:
        return EXIT_GUARD_BLOCKED

    if args.commit and POOL_OUTPUT_PATH.exists():
        print(
            f"🛑 {POOL_OUTPUT_PATH} đã tồn tại — pool ĐÃ được chốt trước đó. "
            "KHÔNG được chọn lại (spec dòng 350-352, §9c.4b ràng buộc (b)). "
            "Xoá thủ công + ghi DR mới nếu thực sự cần đổi tiêu chí."
        )
        return EXIT_POOL_ALREADY_COMMITTED

    try:
        exchange_info = get_exchange_info()
        tickers = get_ticker_24hr()
    except BinancePublicApiError as exc:
        print(f"🛑 Tải dữ liệu thất bại: {exc}")
        return EXIT_FETCH_FAILED

    stats = build_symbol_stats(exchange_info, tickers)
    result = compute_pool(stats, age_floor_days=AGE_FLOOR_DAYS, volume_floor_usdt=VOLUME_FLOOR_USDT)

    print(f"Tổng hợp đồng PERPETUAL/USDT đang TRADING: {len(stats)}")
    print(f"Pool giao dịch: {len(result.trading)} mã")
    print(f"Tập EXPLORE: {len(result.explore)} mã (gồm BTC/ETH)")

    if not args.commit:
        print("\n(chạy thử — dùng --commit để tiêu 4 trial B0 và ghi file thật)")
        return 0

    ledger = TrialLedger()
    git_info = get_git_info(Path("."))
    trial_ids: list[str] = []
    try:
        for param_name, value, note in CRITERIA:
            tid = ledger.reserve(
                n_dang_ky=N_DANG_KY,
                budget_line="B0",
                hypothesis_slot="POOL-0.3",
                direction="LONG",
                dataset="N/A",
                param_under_test=param_name,
                param_value=value,
                params_frozen_hash="n/a",
                config_hash="n/a",
                code_commit=git_info.sha,
                provenance={
                    "params_source": "yaml",
                    "params_effective": {param_name: value},
                    "git_sha": git_info.sha,
                    "reproducible_from_sha": git_info.is_clean,
                    "data_hashes": {},
                    "cache_mode": "none",
                    "guard_passed": True,
                },
                contribution=1,
            )
            trial_ids.append(tid)
            ledger.seal(tid, seal_path=f"runs/{tid}/metrics.seal")
            ledger.consume(
                tid,
                outcome={
                    "expectancy": None,
                    "sharpe": None,
                    "n_trades": None,
                    "max_single_loss_ratio": None,
                },
                verdict="KEPT",
                rejection_reason=note,
                retest_forbidden=True,
            )
    except BudgetExhaustedError as exc:
        print(f"🛑 Hết ngân sách B0: {exc}")
        return EXIT_BUDGET_EXHAUSTED

    POOL_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    POOL_OUTPUT_PATH.write_text(
        yaml.dump(
            {
                "committed_at_git_sha": git_info.sha,
                "criteria": {
                    "volume_24h_usdt_min": VOLUME_FLOOR_USDT,
                    "listing_age_days_min": AGE_FLOOR_DAYS,
                },
                "trading": list(result.trading),
                "explore": list(result.explore),
                "b0_trial_ids": trial_ids,
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    print(f"\n✅ Đã ghi {POOL_OUTPUT_PATH}, tiêu {len(trial_ids)} trial B0: {trial_ids}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
