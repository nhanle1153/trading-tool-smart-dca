"""Các phép kiểm tự động cho `trial_ledger_audit.py` (E6, H16).

Mỗi hàm trả về `CheckResult` — không raise, không in gì, chỉ tính toán.
`entrypoints/trial_ledger_audit.py` gọi tất cả rồi tổng hợp bằng
`tri_state.audit_line()`.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml

from tool_d.config.loader import DEFAULT_CONFIG_PATH, load_tool_d_config
from tool_d.ledger.registry import DEFAULT_REGISTRY_PATH, TrialLedger, TrialState
from tool_d.measurement.tri_state import Measured

DEFAULT_IDEA_QUEUE_PATH = Path("registry/idea_queue.jsonl")
DEFAULT_PARAM_STATUS_PATH = Path("config/param_status.yaml")

BUDGET_A_SLOTS_PER_QUARTER_MAX = 5  # DR-009, §9.3 — không nới vì có LLM


@dataclass(frozen=True)
class CheckResult:
    code: str  # "L-Z10", ...
    measured: Measured[bool]
    evidence: str = ""

    @property
    def ok(self) -> bool:
        return self.measured.is_ok() and self.measured.value is True

    @property
    def is_fail(self) -> bool:
        return self.measured.is_ok() and self.measured.value is False


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def _parse_iso(ts: str) -> datetime:
    """Đọc cả hai dạng: có micro giây (ghi bởi `registry.py` thật) và
    chỉ tới giây (fixture tay) — xem ghi chú ở `registry._utcnow_iso()`.
    """
    fmt = "%Y-%m-%dT%H:%M:%S.%fZ" if "." in ts else "%Y-%m-%dT%H:%M:%SZ"
    return datetime.strptime(ts, fmt)


# ── L-Z10 ─────────────────────────────────────────────────────────────
def check_lz10_registered_before_executed(
    registry_path: Path = DEFAULT_REGISTRY_PATH,
) -> CheckResult:
    """registered_at < executed_at cho MỌI trial (spec dòng 3872)."""
    events = _read_jsonl(registry_path)
    reserved_at: dict[str, str] = {
        e["trial_id"]: e["registered_at"] for e in events if e["event"] == "RESERVE"
    }
    violations: list[str] = []
    for e in events:
        if e["event"] != "CONSUME":
            continue
        tid = e["trial_id"]
        r_at = reserved_at.get(tid)
        if r_at is None:
            violations.append(f"{tid}: CONSUME không có RESERVE trước đó")
            continue
        if not (_parse_iso(r_at) < _parse_iso(e["executed_at"])):
            violations.append(f"{tid}: registered_at={r_at} không < executed_at={e['executed_at']}")
    if not events:
        return CheckResult("L-Z10", Measured.pending("registry rỗng, chưa có sự kiện nào"))
    return CheckResult(
        "L-Z10",
        Measured.ok(len(violations) == 0),
        evidence="; ".join(violations),
    )


# ── L-Z11 ─────────────────────────────────────────────────────────────
def check_lz11_n_used_le_n_dang_ky(
    registry_path: Path = DEFAULT_REGISTRY_PATH, *, n_dang_ky: int
) -> CheckResult:
    """N_ĐÃ_DÙNG ≤ N_ĐĂNG_KÝ tại mọi thời điểm (spec dòng 3873)."""
    ledger = TrialLedger(registry_path)
    n_used = ledger.n_used()
    return CheckResult(
        "L-Z11",
        Measured.ok(n_used <= n_dang_ky),
        evidence=f"N_ĐÃ_DÙNG={n_used}, N_ĐĂNG_KÝ={n_dang_ky}",
    )


# ── L-Z12 ─────────────────────────────────────────────────────────────
def check_lz12_no_duplicate_config_hash_different_outcome(
    registry_path: Path = DEFAULT_REGISTRY_PATH,
) -> CheckResult:
    """Không config_hash nào xuất hiện ở 2 trial với outcome khác nhau
    (spec dòng 3874-3875: "nếu có → có chạy lại không ghi sổ, registry
    mất hiệu lực")."""
    events = _read_jsonl(registry_path)
    config_hash_by_trial: dict[str, str] = {
        e["trial_id"]: e["config_hash"] for e in events if e["event"] == "RESERVE"
    }
    outcome_by_trial: dict[str, dict] = {
        e["trial_id"]: e["outcome"] for e in events if e["event"] == "CONSUME"
    }
    if not events:
        return CheckResult("L-Z12", Measured.pending("registry rỗng"))

    by_hash: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    for tid, outcome in outcome_by_trial.items():
        ch = config_hash_by_trial.get(tid)
        if ch is not None:
            by_hash[ch].append((tid, outcome))

    violations: list[str] = []
    for ch, entries in by_hash.items():
        if len(entries) < 2:
            continue
        first_tid, first_outcome = entries[0]
        for tid, outcome in entries[1:]:
            if outcome != first_outcome:
                violations.append(
                    f"config_hash={ch}: {first_tid} và {tid} có outcome khác nhau"
                )
    return CheckResult("L-Z12", Measured.ok(len(violations) == 0), evidence="; ".join(violations))


# ── L-Z15 ─────────────────────────────────────────────────────────────
def check_lz15_calibrate_params_have_status(
    config_path: Path = DEFAULT_CONFIG_PATH,
    status_path: Path = DEFAULT_PARAM_STATUS_PATH,
) -> CheckResult:
    """Mọi tham số Tầng B đang `null` (nghĩa [CẦN CALIBRATE]) phải xuất
    hiện trong `param_status.yaml` với trạng thái tường minh — thiếu mặt
    ở đó = "im lặng", CẤM (spec dòng 3882-3884)."""
    cfg = load_tool_d_config(config_path)
    null_params = sorted(k for k, v in cfg.tier_b.items() if not k.startswith("_") and v is None)

    if not status_path.exists():
        if null_params:
            return CheckResult(
                "L-Z15",
                Measured.ok(False),
                evidence=f"thiếu {status_path}, nhưng có tham số null: {null_params}",
            )
        return CheckResult("L-Z15", Measured.ok(True), evidence="không có tham số nào null")

    status_doc = yaml.safe_load(status_path.read_text(encoding="utf-8")) or {}
    declared = (status_doc.get("params") or {}).keys()

    silent = [p for p in null_params if p not in declared]
    return CheckResult(
        "L-Z15",
        Measured.ok(len(silent) == 0),
        evidence=f"tham số 'im lặng' (null nhưng không khai trạng thái): {silent}" if silent else "",
    )


# ── L-Z16 ─────────────────────────────────────────────────────────────
def check_lz16_idea_queue_filter_and_tool_d_results(
    idea_queue_path: Path = DEFAULT_IDEA_QUEUE_PATH,
) -> CheckResult:
    """data_source ∈ {MECHANISM, EXPLORE} phải trả lời đủ 3 câu bộ lọc
    §0.1 (mechanism/who_pays/durability không rỗng); data_source ==
    TOOL_D_RESULTS phải có status=REJECTED (spec dòng 3885-3887)."""
    entries = _read_jsonl(idea_queue_path)
    if not entries:
        return CheckResult("L-Z16", Measured.pending("idea_queue rỗng"))

    violations: list[str] = []
    for e in entries:
        ds = e.get("data_source")
        if ds in ("MECHANISM", "EXPLORE"):
            for field in ("mechanism", "who_pays", "durability"):
                if not (e.get(field) or "").strip() or e[field] == "n/a":
                    violations.append(f"{e['idea_id']}: thiếu câu trả lời '{field}'")
        elif ds == "TOOL_D_RESULTS":
            if e.get("status") != "REJECTED":
                violations.append(
                    f"{e['idea_id']}: data_source=TOOL_D_RESULTS nhưng status={e.get('status')} != REJECTED"
                )
    return CheckResult("L-Z16", Measured.ok(len(violations) == 0), evidence="; ".join(violations))


# ── L-Z17 ─────────────────────────────────────────────────────────────
def _quarter_of(d: date) -> tuple[int, int]:
    return d.year, (d.month - 1) // 3 + 1


def check_lz17_budget_a_slots_per_quarter(
    idea_queue_path: Path = DEFAULT_IDEA_QUEUE_PATH,
) -> CheckResult:
    """Số slot NGÂN SÁCH A đã tiêu (status==SELECTED) ≤ 5/quý — KHÔNG
    nới vì có LLM (spec dòng 3888-3889, DR-009)."""
    entries = _read_jsonl(idea_queue_path)
    selected = [e for e in entries if e.get("status") == "SELECTED" and e.get("selected_at")]
    if not entries:
        return CheckResult("L-Z17", Measured.pending("idea_queue rỗng"))

    counts: Counter[tuple[int, int]] = Counter()
    for e in selected:
        d = datetime.strptime(e["selected_at"], "%Y-%m-%dT%H:%M:%SZ").date()
        counts[_quarter_of(d)] += 1

    over = {q: c for q, c in counts.items() if c > BUDGET_A_SLOTS_PER_QUARTER_MAX}
    return CheckResult(
        "L-Z17",
        Measured.ok(len(over) == 0),
        evidence=f"quý vượt trần: {over}" if over else "",
    )


ALL_CHECKS = (
    "check_lz10_registered_before_executed",
    "check_lz11_n_used_le_n_dang_ky",
    "check_lz12_no_duplicate_config_hash_different_outcome",
    "check_lz15_calibrate_params_have_status",
    "check_lz16_idea_queue_filter_and_tool_d_results",
    "check_lz17_budget_a_slots_per_quarter",
)
