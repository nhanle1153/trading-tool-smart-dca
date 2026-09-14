"""E5 — báo cáo định kỳ, nguồn số duy nhất LLM được đọc (spec dòng 659, §12d.2).

Khung TD-0016: `main()` gọi `measurement_guard()` ở dòng đầu tiên sau parse
tham số (canh bởi L-Z36, TD-0017). TD-0060 (spec §12d.2 BƯỚC 1) nối:

    - Khối xuất xứ (0d.5) IN Ở ĐẦU báo cáo — spec dòng 4797: "Khối
      provenance ở ĐẦU báo cáo". `data_files={}` vì E5 không tự đọc file
      dữ liệu thị trường nào (nó đọc SỐ ĐÃ TÍNH SẴN từ kỳ vận hành, việc
      của Khối tương ứng khi tới lượt — chưa viết ở D0-PRE).
    - Bảng chỉ số CỐ ĐỊNH (`tool_d.reporting.report_model`) — TD-0240 đổi
      bộ TÍNH: 8/22 chỉ số tính THẬT từ DB Freqtrade (qua ORM,
      `reporting/freqtrade_db.py`) + `decision_log.jsonl` + sổ trial; 14
      còn lại `pending` với LÝ DO CỤ THỂ (thiếu nguồn cấu trúc, không
      phải câu cũ "D0-PRE chưa có strategy code" — câu đó đã lỗi thời từ
      lúc chiến lược chạy thật, MT-42 chỉ ra đúng điểm này).
    - Dòng tổng dùng chung `audit_line()` với E6 (spec dòng 4801-4802 tái
      dùng đúng câu chữ "đã audit N/M (...)").

Không có nhánh FAIL: E5 là báo cáo, không phải GATE — luôn exit 0 sau khi
qua guard. Mọi lỗi đọc DB/Decision Log/sổ trial được BẮT tại nguồn và biến
thành trạng thái `unreadable` cho đúng chỉ số bị ảnh hưởng — không làm E5
crash, và không lẫn với `pending` (N6: "lỗi đọc" khác "chưa có dữ liệu").
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tool_d.config.loader import DEFAULT_CONFIG_PATH, load_tool_d_config, resolve
from tool_d.ledger.decision_log import DEFAULT_DECISION_LOG_PATH
from tool_d.ledger.registry import DEFAULT_REGISTRY_PATH, TrialLedger
from tool_d.measurement.guard import EXIT_GUARD_BLOCKED, GuardOutcome, measurement_guard
from tool_d.measurement.provenance import (
    build_provenance,
    doc_runtime_image_digest,
)
from tool_d.measurement.tri_state import Status, audit_line, scan_for_sentinels
from tool_d.reporting.freqtrade_db import FreqtradeDbError, doc_danh_sach_lenh, doc_db_url_tu_config
from tool_d.reporting.report_model import build_metrics

ENTRYPOINT = "E5"
REPO_DIR = Path(".")
DEFAULT_FREQTRADE_CONFIG_PATH = Path("config/freqtrade/config.json")

# Chỉ ra ngoài do lỗi lập trình (sentinel lọt khỏi Measured.render()) —
# không phải trạng thái vận hành bình thường nào của báo cáo.
EXIT_SENTINEL_LEAKED = 93


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="E5 periodic_report.py — báo cáo định kỳ (§12d.2)")
    # TD-0240 — ba cờ ĐỂ TRỐNG mặc định (None): khi không truyền, render_report()
    # tự dùng đường sản xuất thật. Tồn tại DUY NHẤT để TEST override được —
    # `db_url` trong config.json là đường TUYỆT ĐỐI, nên KHÔNG có cách nào
    # cô lập bằng cwd/copy config như bài học TD-0239 (đó là đường tương đối,
    # đây thì không); không có cờ này, mọi test chạy CLI của E5 sẽ tự tạo
    # `user_data/tradesv3_dryrun.sqlite` THẬT trong repo mỗi lần chạy.
    parser.add_argument("--freqtrade-config-path", type=Path, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--decision-log-path", type=Path, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--registry-path", type=Path, default=None, help=argparse.SUPPRESS)
    parser.add_argument(
        "--with-params-file",
        action="store_true",
        help="Cho phép chạy dù có <Strategy>.json cạnh strategy (0d.1) — cờ này được ghi vào provenance.",
    )
    return parser


def _doc_trades_an_toan(freqtrade_config_path: Path) -> tuple[list, str | None]:
    """TD-0240 — fail-closed: trả `([], lý_do)` nếu đọc lỗi, KHÔNG để
    exception lan ra `main()` (spec: "Không có nhánh FAIL: E5 luôn exit
    0"). `lý_do` khác `None` là tín hiệu cho `build_metrics()` biết đây
    là UNREADABLE, không phải "chưa có lệnh" (N6)."""
    try:
        db_url = doc_db_url_tu_config(freqtrade_config_path)
        return doc_danh_sach_lenh(db_url), None
    except FreqtradeDbError as exc:
        return [], str(exc)


def _doc_gap_ms_an_toan(decision_log_path: Path) -> tuple[list[float], str | None]:
    if not decision_log_path.exists():
        return [], None  # sổ chưa tồn tại = chưa có sự kiện nào, KHÔNG phải lỗi đọc
    try:
        gia_tri: list[float] = []
        for dong in decision_log_path.read_text(encoding="utf-8").splitlines():
            if not dong.strip():
                continue
            d = json.loads(dong)
            if d.get("loai") == "DOI_SL" and "gap_ms" in d:
                gia_tri.append(float(d["gap_ms"]))
        return gia_tri, None
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return [], f"đọc {decision_log_path} thất bại: {exc}"


def _doc_ledger_an_toan(registry_path: Path) -> tuple[TrialLedger | None, str | None]:
    try:
        return TrialLedger(registry_path), None
    except Exception as exc:  # noqa: BLE001 - fail-closed, không để crash E5
        return None, f"mở {registry_path} thất bại: {exc}"


def render_report(
    *,
    report_guard_passed: bool,
    params_source: str,
    config_path: Path = DEFAULT_CONFIG_PATH,
    freqtrade_config_path: Path = DEFAULT_FREQTRADE_CONFIG_PATH,
    decision_log_path: Path = DEFAULT_DECISION_LOG_PATH,
    registry_path: Path = DEFAULT_REGISTRY_PATH,
) -> str:
    """Dựng toàn bộ văn bản báo cáo — tách khỏi `main()` để test được mà
    không cần chạy tiến trình con (test hành vi CLI đầy đủ là TD-0061).

    TD-0240 — ba tham số đường dẫn mới đều CÓ mặc định trỏ vào ĐÚNG vị
    trí sản xuất của dự án (khác `reporting/freqtrade_db.py`, module đó
    KHÔNG có mặc định — xem docstring ở đó về bài học TD-0239). Ở TẦNG
    ENTRYPOINT này, mặc định trỏ vào sản xuất là ĐÚNG vai trò của nó;
    test truyền tham số riêng để cô lập.
    """
    cfg = load_tool_d_config(config_path)
    prov = build_provenance(
        params_source=params_source,
        params_effective=dict(cfg.tier_b),
        repo_dir=REPO_DIR,
        data_files={},
        cache_mode="none",
        guard_passed=report_guard_passed,
        # TD-0229 — khoá xuất xứ thứ 8 (MT-07), xem chú thích ở
        # `dr015/buoc1_lech_tranche.py`. Fail-closed, không bắt lỗi.
        runtime_image_digest=doc_runtime_image_digest(REPO_DIR),
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
        f"  runtime_image_digest:  {prov.runtime_image_digest}",
        "",
        "BÁO CÁO ĐỊNH KỲ (§12d.2)",
        "-" * 70,
    ]

    trades, trades_error = _doc_trades_an_toan(freqtrade_config_path)
    gap_ms_values, gap_ms_error = _doc_gap_ms_an_toan(decision_log_path)
    ledger, ledger_error = _doc_ledger_an_toan(registry_path)
    so_lenh_da_dong = sum(1 for t in trades if not t.is_open)
    # TD-0246 (phiên -54): DG1-DG5, và vì thế TRANCHE_FILL ≥2, không bao
    # giờ được xét trên arm ∈ ARM_DON_TRANCHE — build_metrics() cần biết
    # arm SẢN XUẤT để không đọc "0 cấu trúc" thành "đã đo và bằng 0".
    arm = resolve(cfg, "tier_c.arm_ablation.arm")

    metrics = build_metrics(
        trades=trades,
        trades_error=trades_error,
        gap_ms_values=gap_ms_values,
        gap_ms_error=gap_ms_error,
        ledger=ledger,
        ledger_error=ledger_error,
        so_lenh_da_dong=so_lenh_da_dong,
        arm=arm,
    )
    for m in metrics:
        lines.append(f"  {m.code:<24s} {m.label:<62s} {m.measured.render()}")

    ok = sum(1 for m in metrics if m.measured.status is Status.OK)
    fail = sum(1 for m in metrics if m.measured.status is Status.UNREADABLE)
    unmeasured = sum(1 for m in metrics if m.measured.status is Status.PENDING)

    lines.append("-" * 70)
    lines.append(audit_line(ok=ok, fail=fail, unmeasured=unmeasured, total=len(metrics)))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    args, _ = build_parser().parse_known_args(argv)

    report = measurement_guard(ENTRYPOINT, argv=argv, with_params_file=args.with_params_file)
    if report.outcome is GuardOutcome.BLOCKED:
        return EXIT_GUARD_BLOCKED

    # Chỉ truyền override khi CÓ truyền — không ghi đè mặc định sản xuất
    # của render_report() bằng None tường minh (argparse type=Path không
    # tự áp default; giữ hành vi "không truyền = dùng sản xuất" tường minh).
    duong_dan_tuy_chinh = {}
    if args.freqtrade_config_path is not None:
        duong_dan_tuy_chinh["freqtrade_config_path"] = args.freqtrade_config_path
    if args.decision_log_path is not None:
        duong_dan_tuy_chinh["decision_log_path"] = args.decision_log_path
    if args.registry_path is not None:
        duong_dan_tuy_chinh["registry_path"] = args.registry_path

    text = render_report(
        report_guard_passed=report.guard_passed,
        params_source=report.params_source,
        **duong_dan_tuy_chinh,
    )

    leaked = scan_for_sentinels(text)
    if leaked:
        print("🛑 LỖI LẬP TRÌNH: giá trị lính canh lọt ra báo cáo (L-Z41):", leaked)
        return EXIT_SENTINEL_LEAKED

    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
