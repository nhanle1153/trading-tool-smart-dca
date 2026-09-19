"""Ngưỡng GATE D0.9, Nhánh 1 — §10.2 (spec dòng 4251-4276). Canh bởi L-Z35.

Ô trống duy nhất của Nhánh 1 ("DSR-adjusted expectancy ≥ ......") đã được
điền bằng DR-D0PRE-03 (TD-0041, 06/09/2026): **0,10 R_realized**, suy từ chi phí
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

from tool_d.arm_switches import ARM_DON_TRANCHE, ARM_HOP_LE

#: `DR-D9-02` §3.1 (b′) — tiêu chí KHÔNG áp dụng cho arm entry đơn (`ARM_DON_TRANCHE`), áp dụng và chặn như cũ
#: cho arm DCA. Tên khoá là của chính tiêu chí trong `evaluate_branch1`.
TIEU_CHI_SKEWNESS_Z1 = "skewness_diff_vs_z1"

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
# TD-0277 (MT-46, chủ dự án chốt 18/09/2026): dải CHẶN cả hai biên, đúng chữ
# spec :4277-4278 + :4290. Trước đó hằng số này xuất hiện đúng một lần toàn
# repo — tại dòng này — tức gate lặng lẽ bỏ một tiêu chí spec.
TIME_STOP_RATIO_BAND: tuple[float, float] = (0.05, 0.25)
TP_FALLBACK_RATIO_MAX: float = 0.40  # > 40% -> L2, không vào live
PBO_MAX: float = 0.5  # H18: D4 chỉ GHI (pbo_chan=False), D9 CHẶN (pbo_chan=True) — DR-D9-01 §7, MT-51

# DR-D4-15 (sửa DR-D4-12 §1.7): trung vị D_fill / D_ke trên lệnh đủ ba tranche lệch khỏi 1 quá mức này ⇒
# DỪNG D4. Lấy từ ngưỡng 0,95 CÓ SẴN ở DR-D4-12 §9.1 ("hai vế đơn vị trùng nhau"), đối xứng — không phải số mới.
BAT_BIEN_1_7_DUNG_SAI: float = 0.05

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
    #: `DR-D9-02` §3.3 — "không áp dụng có căn cứ" KHÁC "chưa đo" và KHÁC "đạt": liệt kê tường minh, không xoá khoá.
    khong_ap_dung: tuple[str, ...] = field(default_factory=tuple)

    def render(self) -> str:
        them = f" · không áp dụng (DR-D9-02): {', '.join(self.khong_ap_dung)}" if self.khong_ap_dung else ""
        if self.verdict is Verdict.PASS:
            return "PASS" + them
        return "FAIL — " + ", ".join(self.failed_criteria) + them


def evaluate_branch1(metrics: Mapping[str, float], *, pbo_chan: bool, arm: str) -> GateResult:
    """Kiểm các tiêu chí SỐ của Nhánh 1 (spec dòng 4257-4276).

    `pbo_chan` — BẮT BUỘC khai, KHÔNG có mặc định (`DR-D9-01` §7, `MT-51`):
    spec :4326/:4349 cho PBO là P1 ở D4 (chỉ ghi) và P0 ở D9 (chặn). Trước
    TD-0285 hàm này chặn PBO ở MỌI nơi gọi, trái chữ spec. Một mặc định sẽ
    lặng lẽ chọn một phía cho người quên khai — nên người gọi phải nói.
      • `False` (D4): PBO không vào `failed_criteria`; giá trị vẫn ở
        `metrics` để bản ghi báo cạnh bên.
      • `True`  (D9): PBO thiếu ⇒ `+inf` ⇒ FAIL tiêu chí, như mọi tiêu chí khác.

    KHÔNG kiểm các tiêu chí dạng "PASS/FAIL của bộ test khác" (H4-D,
    L-Z10→L-Z33, phân bố hold_duration/funding báo cáo) — đó là việc của
    chính các bộ test đó, không phải của module ngưỡng số này.

    `metrics` thiếu khoá nào → khoá đó coi là FAIL (fail-closed, không
    coi thiếu dữ liệu là "PASS ngầm").

    `time_stop_ratio` (TD-0277, MT-46) — tỉ lệ lệnh đóng bằng TIME_STOP phải
    nằm TRONG `TIME_STOP_RATIO_BAND`, CẢ HAI biên đều chặn. Spec gọi nó là
    "ngưỡng chẩn đoán" nhưng liệt nó trong danh sách ✅ Nhánh 1, và :4290 viết
    *"thiếu một tiêu chí → không vào live"*. 🔴 Hệ quả biết TRƯỚC khi nối:
    `Z0-T1` đo được 0% (`td0246`) ⇒ FAIL tiêu chí này. Không nới chiều < 5%
    sau khi đã thấy con số đó — muốn nới phải viết DR (back-end-note MT-46).
    """
    lo_ts, hi_ts = TIME_STOP_RATIO_BAND
    time_stop_ratio = metrics.get("time_stop_ratio", math.nan)
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
        # NaN (thiếu khoá) so sánh ra False ở cả hai vế ⇒ FAIL.
        "time_stop_ratio": lo_ts <= time_stop_ratio <= hi_ts,
    }
    if not isinstance(pbo_chan, bool):
        raise TypeError(f"pbo_chan phải là bool tường minh, nhận {pbo_chan!r}")
    if arm not in ARM_HOP_LE:
        raise ValueError(f"arm {arm!r} không thuộc {ARM_HOP_LE} — DR-D9-02 §4: arm lạ ⇒ raise")
    if pbo_chan:
        checks["pbo"] = metrics.get("pbo", math.inf) <= PBO_MAX
    khong_ap_dung: tuple[str, ...] = ()
    if arm in ARM_DON_TRANCHE:
        # DR-D9-02 §3.1: entry đơn + SL bất biến không tạo được đuôi lỗ kiểu trung bình giá xuống; đuôi lỗ
        # từng lệnh vẫn bị chặn bởi `max_single_trade_loss_over_risk_budget`. Đọc ĐÚNG hằng số, không chép.
        checks.pop(TIEU_CHI_SKEWNESS_Z1)
        khong_ap_dung = (TIEU_CHI_SKEWNESS_Z1,)
    failed = tuple(name for name, ok in checks.items() if not ok)
    return GateResult(
        verdict=Verdict.PASS if not failed else Verdict.FAIL,
        failed_criteria=failed,
        khong_ap_dung=khong_ap_dung,
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
        "time_stop_ratio": 0.10,  # giữa dải 5–25% (TD-0277)
        "pbo": 0.0,
    }
