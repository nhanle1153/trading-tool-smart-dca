"""E5 — báo cáo định kỳ, nguồn số duy nhất LLM được đọc (spec dòng 659, §12d.2).

Khung TD-0016: `main()` gọi `measurement_guard()` ở dòng đầu tiên sau parse
tham số (canh bởi L-Z36, TD-0017). TD-0060 (spec §12d.2 BƯỚC 1) nối:

    - Khối xuất xứ (0d.5) IN Ở ĐẦU báo cáo — spec dòng 4797: "Khối
      provenance ở ĐẦU báo cáo". `data_files={}` vì E5 không tự đọc file
      dữ liệu thị trường nào (nó đọc SỐ ĐÃ TÍNH SẴN từ kỳ vận hành, việc
      của Khối tương ứng khi tới lượt — chưa viết ở D0-PRE).
    - Bảng chỉ số CỐ ĐỊNH (`tool_d.reporting.report_model`) — TẤT CẢ
      `pending` ở D0-PRE (chưa có strategy code, chưa có lệnh đóng thật).
    - Dòng tổng dùng chung `audit_line()` với E6 (spec dòng 4801-4802 tái
      dùng đúng câu chữ "đã audit N/M (...)").

Không có nhánh FAIL: E5 là báo cáo, không phải GATE — luôn exit 0 sau khi
qua guard, kể cả khi mọi chỉ số đều pending (đó là thông tin, không phải lỗi).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tool_d.config.loader import DEFAULT_CONFIG_PATH, load_tool_d_config
from tool_d.measurement.guard import EXIT_GUARD_BLOCKED, GuardOutcome, measurement_guard
from tool_d.measurement.provenance import build_provenance
from tool_d.measurement.tri_state import audit_line, scan_for_sentinels
from tool_d.reporting.report_model import build_metrics

ENTRYPOINT = "E5"
REPO_DIR = Path(".")

# Chỉ ra ngoài do lỗi lập trình (sentinel lọt khỏi Measured.render()) —
# không phải trạng thái vận hành bình thường nào của báo cáo.
EXIT_SENTINEL_LEAKED = 93


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="E5 periodic_report.py — báo cáo định kỳ (§12d.2)")
    parser.add_argument(
        "--with-params-file",
        action="store_true",
        help="Cho phép chạy dù có <Strategy>.json cạnh strategy (0d.1) — cờ này được ghi vào provenance.",
    )
    return parser


def render_report(
    *, report_guard_passed: bool, params_source: str, config_path: Path = DEFAULT_CONFIG_PATH
) -> str:
    """Dựng toàn bộ văn bản báo cáo — tách khỏi `main()` để test được mà
    không cần chạy tiến trình con (test hành vi CLI đầy đủ là TD-0061)."""
    cfg = load_tool_d_config(config_path)
    prov = build_provenance(
        params_source=params_source,
        params_effective=dict(cfg.tier_b),
        repo_dir=REPO_DIR,
        data_files={},
        cache_mode="none",
        guard_passed=report_guard_passed,
    )

    lines = [
        "═" * 70,
        "KHỐI XUẤT XỨ (0d.5) — spec dòng 4797: in Ở ĐẦU báo cáo",
        "═" * 70,
        f"  git_sha:               {prov.git_sha}",
        f"  reproducible_from_sha: {prov.reproducible_from_sha}",
        f"  guard_passed:          {prov.guard_passed}",
        f"  cache_mode:            {prov.cache_mode}",
        f"  params_source:         {prov.params_source}",
        f"  data_hashes:           {prov.data_hashes}",
        "",
        "BÁO CÁO ĐỊNH KỲ (§12d.2) — D0-PRE: chưa có kỳ vận hành nào",
        "-" * 70,
    ]

    metrics = build_metrics()
    for m in metrics:
        lines.append(f"  {m.code:<24s} {m.label:<62s} {m.measured.render()}")

    lines.append("-" * 70)
    lines.append(audit_line(ok=0, fail=0, unmeasured=len(metrics), total=len(metrics)))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    args, _ = build_parser().parse_known_args(argv)

    report = measurement_guard(ENTRYPOINT, argv=argv, with_params_file=args.with_params_file)
    if report.outcome is GuardOutcome.BLOCKED:
        return EXIT_GUARD_BLOCKED

    text = render_report(report_guard_passed=report.guard_passed, params_source=report.params_source)

    leaked = scan_for_sentinels(text)
    if leaked:
        print("🛑 LỖI LẬP TRÌNH: giá trị lính canh lọt ra báo cáo (L-Z41):", leaked)
        return EXIT_SENTINEL_LEAKED

    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
