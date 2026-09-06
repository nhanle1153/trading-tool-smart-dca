"""Ngưỡng GATE D0.9, Nhánh 1 — §10.2 (spec dòng 4251-4276). Canh bởi L-Z35.

Nhánh 1 có **đúng một** ô còn trống trong toàn bộ spec: "DSR-adjusted
expectancy ≥ ......". Mọi ngưỡng khác của Nhánh 1 (đệm thanh lý, tỉ lệ lỗ
tối đa, skewness, số lệnh/năm tối thiểu, dải TIME_STOP, TP_fallback, PBO)
đã có số cụ thể trong spec — không phải "chưa điền", không cần fail-closed.

🔴 Ô trống fail-closed = `+inf` (KHÔNG PHẢI `None`, KHÔNG PHẢI `0.0`) —
để GATE không thể vô tình PASS khi ngưỡng chưa được điền bằng một DR thật
(spec dòng 3949-3958).
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum

# ═══════════ Ô CHƯA ĐIỀN — chờ OQ-01 / blocker B6 (TD-0041) ═══════════
# Spec dòng 4260: "DSR-adjusted expectancy ≥ ...... 🔴 PHẢI ĐIỀN SỐ Ở
# D0-PRE ... cho tới khi điền, giá trị trong code = +inf".
DSR_ADJ_EXPECTANCY_MIN: float = math.inf

# ═══════════ Ngưỡng ĐÃ CÓ SỐ trong spec (không phải ô trống) ═══════════
LIQ_BUFFER_RATIO_MEAN_MIN: float = 8.0  # §6.4b
MAX_SINGLE_TRADE_LOSS_OVER_RISK_BUDGET_MAX: float = 1.15
SKEWNESS_DIFF_VS_Z1_MAX: float = 0.5  # "không âm hơn Z1 quá 0.5"
TRADES_PER_YEAR_MIN: float = 150.0  # SÀN, không phải trần
TIME_STOP_RATIO_BAND: tuple[float, float] = (0.05, 0.25)
TP_FALLBACK_RATIO_MAX: float = 0.40  # > 40% -> L2, không vào live
PBO_MAX: float = 0.5  # 🟡 P1 ở lần chạy đầu — không chặn D0.9, nâng P0 ở D9

# Nhánh 2 (§10.2, chỉ chạy nếu Nhánh 1 PASS) — cùng loại "đã có số".
BRANCH2_DCA_BEATS_Z0_MIN_PCT: float = 20.0
BRANCH2_LIQ_BUFFER_RATIO_FACTOR: float = 1.3


class Verdict(Enum):
    PASS = "pass"
    FAIL = "fail"


@dataclass(frozen=True)
class GateResult:
    verdict: Verdict
    failed_criteria: tuple[str, ...] = field(default_factory=tuple)

    def render(self) -> str:
        if self.verdict is Verdict.PASS:
            return "PASS"
        return "FAIL — " + ", ".join(self.failed_criteria)


def evaluate_branch1(metrics: Mapping[str, float]) -> GateResult:
    """Kiểm các tiêu chí SỐ của Nhánh 1 (spec dòng 4257-4276).

    KHÔNG kiểm các tiêu chí dạng "PASS/FAIL của bộ test khác" (H4-D,
    L-Z10→L-Z33, phân bố hold_duration/funding báo cáo) — đó là việc của
    chính các bộ test đó, không phải của module ngưỡng số này.

    `metrics` thiếu khoá nào → khoá đó coi là FAIL (fail-closed, không
    coi thiếu dữ liệu là "PASS ngầm").
    """
    checks: dict[str, bool] = {
        "dsr_adjusted_expectancy": metrics.get("dsr_adjusted_expectancy", -math.inf)
        >= DSR_ADJ_EXPECTANCY_MIN,
        "liq_buffer_ratio_mean": metrics.get("liq_buffer_ratio_mean", -math.inf)
        >= LIQ_BUFFER_RATIO_MEAN_MIN,
        "max_single_trade_loss_over_risk_budget": metrics.get(
            "max_single_trade_loss_over_risk_budget", math.inf
        )
        <= MAX_SINGLE_TRADE_LOSS_OVER_RISK_BUDGET_MAX,
        "skewness_diff_vs_z1": metrics.get("skewness_diff_vs_z1", math.inf)
        <= SKEWNESS_DIFF_VS_Z1_MAX,
        "trades_per_year": metrics.get("trades_per_year", -math.inf) >= TRADES_PER_YEAR_MIN,
        "tp_fallback_ratio": metrics.get("tp_fallback_ratio", math.inf)
        <= TP_FALLBACK_RATIO_MAX,
        "pbo": metrics.get("pbo", math.inf) <= PBO_MAX,
    }
    failed = tuple(name for name, ok in checks.items() if not ok)
    return GateResult(
        verdict=Verdict.PASS if not failed else Verdict.FAIL,
        failed_criteria=failed,
    )


def best_known_result_for_test() -> dict[str, float]:
    """Bộ số CỰC TỐT giả lập — dùng riêng cho test L-Z35 (dòng 3952-3953:
    "Gate này KHÔNG THỂ pass bằng cách quên điền"). Mọi tiêu chí ngoại trừ
    DSR đều đạt dư dả; DSR để trần vì đó chính là ô đang bị fail-closed.
    KHÔNG dùng hàm này ở bất kỳ đâu ngoài test — đây không phải dữ liệu
    thật, chỉ là phép thử "gate có bị lách được không".
    """
    return {
        "dsr_adjusted_expectancy": 1_000_000.0,  # "cực tốt" cỡ nào cũng vô nghĩa khi ngưỡng là +inf
        "liq_buffer_ratio_mean": 100.0,
        "max_single_trade_loss_over_risk_budget": 0.01,
        "skewness_diff_vs_z1": 0.0,
        "trades_per_year": 10_000.0,
        "tp_fallback_ratio": 0.0,
        "pbo": 0.0,
    }
