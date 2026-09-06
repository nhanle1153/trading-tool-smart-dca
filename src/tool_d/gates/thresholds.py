"""Ngưỡng GATE D0.9, Nhánh 1 — §10.2 (spec dòng 4251-4276). Canh bởi L-Z35.

Ô trống duy nhất của Nhánh 1 ("DSR-adjusted expectancy ≥ ......") đã được
điền bằng DR-D0PRE-03 (TD-0041, 06/09/2026): **0,10 R**, suy từ chi phí
backtest không nhìn thấy (trượt giá SL) × hệ số an toàn. Công thức của đại
lượng này ở `dsr.dsr_adjusted_expectancy()`.

🔴 L-Z35 giờ ở biến thể spec dòng 3954-3955: "kết quả tốt nhất hiện có vẫn
FAIL". Kết quả tốt nhất hiện có = CHƯA CÓ (chưa có lần đánh giá nào) →
`BEST_KNOWN_DSR_ADJ_EXPECTANCY = -inf` — trạng thái *chưa đo*, không phải
số bịa (N6). Cập nhật hằng số này CHỈ từ số đo thật, kèm commit.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum

# ═══════════ Đã điền — DR-D0PRE-03 (TD-0041), blocker B6 gỡ ═══════════
# Đơn vị: R mỗi lệnh. Đổi số này = DR mới, viết TRƯỚC khi thấy kết quả gate
# kế tiếp (spec dòng 3956-3958).
DSR_ADJ_EXPECTANCY_MIN: float = 0.10

# Kết quả tốt nhất hiện có của chính đại lượng trên. -inf = CHƯA CÓ lần đánh
# giá nào (không phải 0.0, không phải None — N6). Khi có số đo thật, ghi số
# đo vào đây kèm trial_id trong commit message; L-Z35 đòi nó vẫn < ngưỡng
# cho tới khi gate thật sự qua.
BEST_KNOWN_DSR_ADJ_EXPECTANCY: float = -math.inf

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
    """Bộ số cho test L-Z35 biến thể "kết quả tốt nhất hiện có vẫn FAIL"
    (spec dòng 3954-3955). Mọi tiêu chí KHÁC đạt dư dả (giả lập) để chứng
    minh gate chỉ chặn đúng ở DSR; riêng DSR lấy ĐÚNG kết quả tốt nhất hiện
    có (`BEST_KNOWN_DSR_ADJ_EXPECTANCY`), không giả lập. KHÔNG dùng hàm này
    ngoài test.
    """
    return {
        "dsr_adjusted_expectancy": BEST_KNOWN_DSR_ADJ_EXPECTANCY,
        "liq_buffer_ratio_mean": 100.0,
        "max_single_trade_loss_over_risk_budget": 0.01,
        "skewness_diff_vs_z1": 0.0,
        "trades_per_year": 10_000.0,
        "tp_fallback_ratio": 0.0,
        "pbo": 0.0,
    }
