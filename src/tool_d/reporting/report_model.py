"""Nội dung báo cáo định kỳ (§12d.2, E5 `periodic_report.py`, spec dòng
4782-4810). Canh bởi L-Z41 (TD-0061, phần "đầu ra thật của E5").

Danh sách chỉ số CỐ ĐỊNH theo đúng thứ tự bullet của §12d.2 BƯỚC 1. TD-0062
(sau) đóng băng danh sách này bằng test hồi quy giữ hash — **đổi nội dung
báo cáo = tiêu 1 trial** (spec dòng 4810), không được thêm/bớt/sửa nhãn tự
do sau khi đã đóng băng.

Ở D0-PRE, MỌI chỉ số ở đây là `pending`: các chỉ số vận hành (H-1…H-4, win
rate, phân bố...) cần lệnh đã đóng thật, và D0-PRE chưa có strategy code
(§0d — Khối 1-8 chỉ dựng tầng chống nhiễm phép đo). Ba dòng "Ngân sách"
(B3/N/DSR) đọc được từ `trial_registry.jsonl` ngay cả khi sổ rỗng, nhưng
cũng để `pending` — báo cáo này mô tả một PHIÊN VẬN HÀNH SỐNG, và sổ hiện
chưa ghi một sự kiện CONSUME nào (0 vẫn là một con số có nghĩa nhưng không
phải nghĩa mà báo cáo này định trả lời; kiểm sổ sách tĩnh là việc của E6
`trial_ledger_audit.py`, không phải E5).
"""

from __future__ import annotations

from dataclasses import dataclass

from tool_d.measurement.tri_state import Measured

_VAN_HANH = "chưa có lệnh đóng thật — D0-PRE chưa có strategy code (Khối 1-8)"
_NGAN_SACH = (
    "mô tả một phiên vận hành sống; sổ trial hiện chưa ghi sự kiện CONSUME nào (D0-PRE)"
)


@dataclass(frozen=True)
class ReportMetric:
    code: str
    label: str
    measured: Measured[object]


# (code, nhãn, lý do pending) — thứ tự = thứ tự bullet trong spec §12d.2.
_METRIC_DEFS: tuple[tuple[str, str, str], ...] = (
    ("H1", "H-1 tỉ lệ zone bị huỷ khi chờ xác nhận (§7.4)", _VAN_HANH),
    ("H2", "H-2 tương quan ZSS lúc entry ↔ kết quả lệnh", _VAN_HANH),
    ("H3", "H-3 tỉ lệ đóng bằng TIME_STOP (dải 5–25%)", _VAN_HANH),
    ("H4", "H-4 tỉ lệ dùng TP_fallback (ngưỡng 40%)", _VAN_HANH),
    ("WINRATE_LONG", "Win rate — Long", _VAN_HANH),
    ("WINRATE_SHORT", "Win rate — Short", _VAN_HANH),
    ("EXPECTANCY_LONG", "Expectancy — Long", _VAN_HANH),
    ("EXPECTANCY_SHORT", "Expectancy — Short", _VAN_HANH),
    ("HOLD_DURATION_DIST", "Phân bố hold_duration_bars (mọi lệnh)", _VAN_HANH),
    ("LIQ_BUFFER_DIST", "Phân bố liq_buffer_ratio thực tế vs ngưỡng 8", _VAN_HANH),
    ("TRANCHE_FILL_1", "Tỉ lệ khớp tranche 1", _VAN_HANH),
    ("TRANCHE_FILL_2", "Tỉ lệ khớp tranche 2", _VAN_HANH),
    ("TRANCHE_FILL_3", "Tỉ lệ khớp tranche 3", _VAN_HANH),
    ("FUNDING_VS_R", "Funding tích luỹ / R_eff", _VAN_HANH),
    ("TIER_BREAKDOWN", "Tách theo tier thanh khoản", _VAN_HANH),
    ("SESSION_BREAKDOWN", "Tách theo phiên", _VAN_HANH),
    (
        "EFFECTIVE_SAMPLE_SIZE",
        "Số mẫu HIỆU DỤNG (điều chỉnh tương quan) vs số lệnh danh nghĩa",
        _VAN_HANH,
    ),
    ("BUDGET_B3_REMAINING", "Ngân sách: B3 còn lại", _NGAN_SACH),
    ("BUDGET_N_CURRENT", "Ngân sách: N hiện tại", _NGAN_SACH),
    ("BUDGET_DSR_CURRENT", "Ngân sách: DSR hiện tại", _NGAN_SACH),
    (
        "POSTONLY_FILL",
        "🆕 v7 Tỉ lệ khớp post-only tranche 1/2/3 + NO_FILL (§3.5)",
        _VAN_HANH,
    ),
    (
        "SL_GAP_MS_DIST",
        "🆕 v7 Phân bố gap_ms mỗi lần đổi khối lượng SL (§8.3, D2c)",
        _VAN_HANH,
    ),
)


def build_metrics() -> list[ReportMetric]:
    """Danh sách chỉ số của kỳ báo cáo hiện tại — TẤT CẢ `pending` ở D0-PRE.

    Trả về list MỚI mỗi lần gọi (không chia sẻ instance `Measured` giữa các
    lần gọi) — vô hại vì `Measured` bất biến, nhưng tránh mọi hiểu nhầm về
    trạng thái dùng chung.
    """
    return [ReportMetric(code=c, label=label, measured=Measured.pending(why)) for c, label, why in _METRIC_DEFS]
