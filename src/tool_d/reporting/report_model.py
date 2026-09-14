"""Nội dung báo cáo định kỳ (§12d.2, E5 `periodic_report.py`, spec dòng
4782-4810). Canh bởi L-Z41 (TD-0061, phần "đầu ra thật của E5").

Danh sách chỉ số CỐ ĐỊNH theo đúng thứ tự bullet của §12d.2 BƯỚC 1. TD-0062
(sau) đóng băng danh sách này bằng test hồi quy giữ hash — **đổi nội dung
báo cáo = tiêu 1 trial** (spec dòng 4810), không được thêm/bớt/sửa nhãn tự
do sau khi đã đóng băng.

════ TD-0240 — đổi bộ TÍNH, KHÔNG đổi `code`/`label` ════
`build_metrics()` không còn trả TOÀN BỘ `pending` cứng — nó TÍNH THẬT các
chỉ số có đủ nguồn dữ liệu, nhận vào qua tham số (giữ THUẦN, không tự đọc
DB/file — phần đọc I/O thuộc `entrypoints/periodic_report.py` +
`reporting/freqtrade_db.py`, đúng khuôn `gap_ms.py`/`vao_ra_lenh.py`).

════ PHẠM VI — 8/22 chỉ số tính được, 14 còn lại vẫn `pending` với LÝ DO
MỚI (không phải câu `_VAN_HANH` cũ đã lỗi thời) ════
Chủ dự án chốt: chỉ làm chỉ số CÓ ĐỦ NGUỒN dữ liệu NGAY, không mở rộng
sang viết bản ghi RA lệnh/PLAN (đó là mã việc riêng, xem `vao_ra_lenh.py`).

  TÍNH ĐƯỢC (đọc `trades`/`orders` qua Freqtrade ORM, `decision_log.jsonl`
  loại `DOI_SL`, và `trial_registry.jsonl`):
    BUDGET_B3_REMAINING, BUDGET_N_CURRENT, BUDGET_DSR_CURRENT,
    SL_GAP_MS_DIST, H3, TRANCHE_FILL_1/2/3, WINRATE_LONG/SHORT.

  CÒN PENDING, và LÝ DO CỤ THỂ vì sao (không phải "D0-PRE chưa có code" —
  câu đó đã lỗi thời, chiến lược đã chạy thật):
    H1, H2, H4              — cần dữ liệu ZONE/ZSS/tp_source; không có cột
                               DB nào chứa chúng, cần bản ghi PLAN/RA lệnh
                               (mã việc chưa mở, xem `vao_ra_lenh.py`).
    EXPECTANCY_LONG/SHORT   — dự án định nghĩa expectancy THEO R_eff
                               (`gates/dsr.py`), cần `planned_risk_usdt`;
                               giá trị đó CHỈ nằm trong `custom_data`/
                               `enter_tag` mã hoá, không có cột DB riêng —
                               tính theo `pnl_abs` tuyệt đối sẽ là MỘT
                               ĐỊNH NGHĨA KHÁC với phần còn lại của dự án
                               (DR-013), không tự chọn.
    HOLD_DURATION_DIST      — đơn vị là BAR 4H (`time_stop.hold_duration_
                               bars`, nhận bar-index), DB chỉ lưu datetime
                               — quy đổi datetime→bar cần một bộ chuyển
                               đổi chưa có; tự suy bằng total_seconds/14400
                               sẽ là một cách tính THỨ HAI cho "hold
                               duration", có thể trôi khỏi định nghĩa
                               chuẩn (LD-09).
    LIQ_BUFFER_DIST         — công thức đã có (`spec:1866`), nhưng cần
                               `liquidation_price` (cột DB CHƯA TRA CỨU,
                               Quy tắc 7 cấm đọc trước khi tra) + giải mã
                               `sl`/`p_avg_plan` từ `enter_tag`.
    FUNDING_VS_R            — cần `planned_risk_usdt`/`R_eff`, cùng lý do
                               EXPECTANCY.
    TIER_BREAKDOWN          — chưa xác nhận nguồn ánh xạ mã→tier trên
                               đường sản xuất.
    SESSION_BREAKDOWN       — spec không định nghĩa ranh giới "phiên"
                               bằng số cụ thể; tự chọn ranh giới giờ UTC
                               là suy đoán (N6).
    EFFECTIVE_SAMPLE_SIZE   — công thức "điều chỉnh tương quan" chưa có
                               ở bất kỳ module nào của dự án.
    POSTONLY_FILL           — cần biết NO_FILL (lệnh không khớp), chưa
                               xác nhận Freqtrade có để lại dấu vết nào
                               trong DB khi entry không khớp và bị huỷ.

  Mọi chỉ số CÓ NGUỒN nhưng CHƯA CÓ LỆNH THẬT (n=0) vẫn `pending` — với lý
  do "chưa có lệnh đóng thật", khác hẳn lý do "thiếu nguồn cấu trúc" ở
  trên. Hai loại lý do không được gộp làm một (N6: phân biệt "chưa đo" ở
  từng NGUYÊN NHÂN, không phải một câu chung chung).
"""

from __future__ import annotations

import hashlib
import statistics
from collections.abc import Sequence
from dataclasses import dataclass

from tool_d.arm_switches import ARM_DON_TRANCHE
from tool_d.gates.dsr import N_DANG_KY, dsr_hurdle, effective_n
from tool_d.ledger.registry import TrialLedger
from tool_d.measurement.tri_state import Measured
from tool_d.reporting.freqtrade_db import LenhTomTat

_CAN_BAN_GHI_RA_LENH = (
    "cần bản ghi RA lệnh/PLAN (ZONE/ZSS/tp_source) — mã việc chưa mở, "
    "xem docstring `vao_ra_lenh.py`"
)
_CAN_R_TU_CUSTOM_DATA = (
    "cần planned_risk_usdt để tính theo R_eff (DR-013/gates/dsr.py) — giá trị "
    "đó chỉ nằm trong custom_data/enter_tag mã hoá, không có cột DB riêng; "
    "tính theo pnl_abs tuyệt đối sẽ là một định nghĩa expectancy khác với "
    "phần còn lại của dự án (LD-09)"
)
_CHUA_XAC_NHAN_NGUON = "chưa xác nhận nguồn dữ liệu trên đường sản xuất — chưa mở mã việc"
_CHUA_CO_LENH_DONG = "chưa có lệnh đóng thật"
_CHUA_CO_SU_KIEN_DOI_SL = "chưa có lần đổi khối lượng SL nào (arm single-entry, hoặc chưa tới tranche 2/3)"


@dataclass(frozen=True)
class ReportMetric:
    code: str
    label: str
    measured: Measured[object]


# (code, nhãn, lý do pending KHI KHÔNG TÍNH ĐƯỢC — dùng làm mặc định lúc
# gọi build_metrics() không tham số, vd. content_fingerprint()) — thứ tự
# = thứ tự bullet trong spec §12d.2. THỨ TỰ và (code, label) ĐÓNG BĂNG.
_METRIC_DEFS: tuple[tuple[str, str, str], ...] = (
    ("H1", "H-1 tỉ lệ zone bị huỷ khi chờ xác nhận (§7.4)", _CAN_BAN_GHI_RA_LENH),
    ("H2", "H-2 tương quan ZSS lúc entry ↔ kết quả lệnh", _CAN_BAN_GHI_RA_LENH),
    ("H3", "H-3 tỉ lệ đóng bằng TIME_STOP (dải 5–25%)", _CHUA_CO_LENH_DONG),
    ("H4", "H-4 tỉ lệ dùng TP_fallback (ngưỡng 40%)", _CAN_BAN_GHI_RA_LENH),
    ("WINRATE_LONG", "Win rate — Long", _CHUA_CO_LENH_DONG),
    ("WINRATE_SHORT", "Win rate — Short", _CHUA_CO_LENH_DONG),
    ("EXPECTANCY_LONG", "Expectancy — Long", _CAN_R_TU_CUSTOM_DATA),
    ("EXPECTANCY_SHORT", "Expectancy — Short", _CAN_R_TU_CUSTOM_DATA),
    (
        "HOLD_DURATION_DIST",
        "Phân bố hold_duration_bars (mọi lệnh)",
        "đơn vị là bar 4H (time_stop.hold_duration_bars nhận bar-index), "
        "DB chỉ lưu datetime — quy đổi cần một bộ chuyển đổi chưa có",
    ),
    (
        "LIQ_BUFFER_DIST",
        "Phân bố liq_buffer_ratio thực tế vs ngưỡng 8",
        "cần cột DB liquidation_price (CHƯA TRA CỨU — Quy tắc 7) và giải "
        "mã sl/p_avg_plan từ enter_tag",
    ),
    ("TRANCHE_FILL_1", "Tỉ lệ khớp tranche 1", "chưa có lệnh nào"),
    ("TRANCHE_FILL_2", "Tỉ lệ khớp tranche 2", "chưa có lệnh nào"),
    ("TRANCHE_FILL_3", "Tỉ lệ khớp tranche 3", "chưa có lệnh nào"),
    ("FUNDING_VS_R", "Funding tích luỹ / R_eff", _CAN_R_TU_CUSTOM_DATA),
    ("TIER_BREAKDOWN", "Tách theo tier thanh khoản", _CHUA_XAC_NHAN_NGUON),
    ("SESSION_BREAKDOWN", "Tách theo phiên", "spec không định nghĩa ranh giới giờ của một 'phiên' bằng số cụ thể"),
    (
        "EFFECTIVE_SAMPLE_SIZE",
        "Số mẫu HIỆU DỤNG (điều chỉnh tương quan) vs số lệnh danh nghĩa",
        "công thức 'điều chỉnh tương quan' chưa có ở bất kỳ module nào của dự án",
    ),
    ("BUDGET_B3_REMAINING", "Ngân sách: B3 còn lại", "ledger chưa được truyền vào"),
    ("BUDGET_N_CURRENT", "Ngân sách: N hiện tại", "ledger chưa được truyền vào"),
    ("BUDGET_DSR_CURRENT", "Ngân sách: DSR hiện tại", "ledger chưa được truyền vào"),
    (
        "POSTONLY_FILL",
        "🆕 v7 Tỉ lệ khớp post-only tranche 1/2/3 + NO_FILL (§3.5)",
        _CHUA_XAC_NHAN_NGUON,
    ),
    (
        "SL_GAP_MS_DIST",
        "🆕 v7 Phân bố gap_ms mỗi lần đổi khối lượng SL (§8.3, D2c)",
        _CHUA_CO_SU_KIEN_DOI_SL,
    ),
)

# Vị trí trong _METRIC_DEFS của các chỉ số ĐƯỢC tính thật — dùng để tránh
# lặp lại 21 dòng if/elif; mỗi phần tử là (code, hàm_tinh).
_TINH_DUOC: frozenset[str] = frozenset(
    {
        "H3",
        "WINRATE_LONG",
        "WINRATE_SHORT",
        "TRANCHE_FILL_1",
        "TRANCHE_FILL_2",
        "TRANCHE_FILL_3",
        "BUDGET_B3_REMAINING",
        "BUDGET_N_CURRENT",
        "BUDGET_DSR_CURRENT",
        "SL_GAP_MS_DIST",
    }
)


def _tinh_h3(trades: Sequence[LenhTomTat], *, loi: str | None) -> Measured[float]:
    if loi is not None:
        return Measured.unreadable(loi)
    da_dong = [t for t in trades if not t.is_open]
    if not da_dong:
        return Measured.pending(_CHUA_CO_LENH_DONG)
    so_time_stop = sum(1 for t in da_dong if t.exit_reason == "TIME_STOP")
    return Measured.ok(so_time_stop / len(da_dong))


def _tinh_winrate(trades: Sequence[LenhTomTat], *, is_short: bool, loi: str | None) -> Measured[float]:
    if loi is not None:
        return Measured.unreadable(loi)
    da_dong = [t for t in trades if not t.is_open and t.is_short == is_short]
    if not da_dong:
        return Measured.pending(_CHUA_CO_LENH_DONG)
    thang = sum(1 for t in da_dong if (t.close_profit_abs or 0.0) > 0)
    return Measured.ok(thang / len(da_dong))


def _tinh_tranche_fill(
    trades: Sequence[LenhTomTat], *, tranche: int, loi: str | None, arm: str | None
) -> Measured[float]:
    """🔴 Tranche ≥2 CHỈ có nghĩa trên arm CÓ DCA. Với arm thuộc
    `ARM_DON_TRANCHE` (kể cả arm sản xuất hiện tại, tuỳ thời điểm — xem
    `arm_switches.py:73-75`), `duoc_them_tranche()` không bao giờ trả
    `True` — kết quả sẽ LUÔN là 0/N, và đó là 0 CẤU TRÚC (không thể xảy
    ra), không phải "đã đo và bằng 0". Gộp hai loại 0 này là đúng cái bẫy
    `TD-0246` vừa đặt tên: một hằng số cấu trúc bị đọc như một phép đo.
    Phát hiện này của phiên `-54`, không phải của module này."""
    if loi is not None:
        return Measured.unreadable(loi)
    if tranche >= 2:
        if arm is None:
            return Measured.pending("chưa xác định arm sản xuất — không tính tranche ≥2 khi chưa biết arm")
        if arm in ARM_DON_TRANCHE:
            return Measured.pending(
                f"arm {arm!r} thuộc ARM_DON_TRANCHE (arm_switches.py) — tranche {tranche} "
                "KHÔNG BAO GIỜ được xét trên arm này (cấu trúc, không phải đo được và bằng 0)"
            )
    if not trades:
        return Measured.pending("chưa có lệnh nào")
    dat_toi = sum(1 for t in trades if t.so_tranche_khop >= tranche)
    return Measured.ok(dat_toi / len(trades))


def _tinh_budget(
    ledger: TrialLedger | None, *, so_lenh_da_dong: int, code: str, loi: str | None
) -> Measured[object]:
    if loi is not None:
        return Measured.unreadable(loi)
    if ledger is None:
        return Measured.pending("ledger chưa được truyền vào")
    if code == "BUDGET_N_CURRENT":
        return Measured.ok(ledger.n_used())
    if code == "BUDGET_B3_REMAINING":
        return Measured.ok(
            ledger.available(n_dang_ky=N_DANG_KY, so_lenh_da_dong=so_lenh_da_dong)
        )
    # BUDGET_DSR_CURRENT — rào tại N HIỆU DỤNG (gates/dsr.effective_n),
    # không phải n_used() một mình — đúng định nghĩa "mẫu số DSR" của dự
    # án, không phải cách đọc riêng của module này.
    return Measured.ok(dsr_hurdle(effective_n(n_consumed_since_live=ledger.n_used())))


def _tinh_sl_gap_ms(gap_ms_values: Sequence[float], *, loi: str | None) -> Measured[object]:
    if loi is not None:
        return Measured.unreadable(loi)
    if not gap_ms_values:
        return Measured.pending(_CHUA_CO_SU_KIEN_DOI_SL)
    gia_tri = list(gap_ms_values)
    return Measured.ok(
        {
            "n": len(gia_tri),
            "min": min(gia_tri),
            "p50": statistics.median(gia_tri),
            "max": max(gia_tri),
        }
    )


def build_metrics(
    *,
    trades: Sequence[LenhTomTat] = (),
    trades_error: str | None = None,
    gap_ms_values: Sequence[float] = (),
    gap_ms_error: str | None = None,
    ledger: TrialLedger | None = None,
    ledger_error: str | None = None,
    so_lenh_da_dong: int = 0,
    arm: str | None = None,
) -> list[ReportMetric]:
    """Danh sách chỉ số của kỳ báo cáo hiện tại.

    Hàm THUẦN — nhận dữ liệu ĐÃ ĐỌC SẴN, không tự mở DB/file. Phần đọc
    I/O (Freqtrade ORM, `decision_log.jsonl`, `trial_registry.jsonl`)
    thuộc `entrypoints/periodic_report.py`. Gọi không tham số (như
    `content_fingerprint()` làm) trả về đúng 22 `(code, label)` như cũ,
    tất cả `pending` — hash KHÔNG đổi.

    :param trades: mọi `LenhTomTat` đọc được từ DB (mở HAY đóng).
    :param trades_error: khác `None` khi ĐỌC DB THẤT BẠI (không phải
        "chưa có lệnh") — mọi chỉ số phụ thuộc `trades` trả về
        `unreadable`, KHÔNG bị nhầm với `pending` (N6: hai nguyên nhân
        khác nhau, không được gộp thành một câu chung chung).
    :param gap_ms_values: `gap_ms` của MỌI bản ghi `DOI_SL` trong
        `decision_log.jsonl` (đã lọc ở tầng gọi).
    :param gap_ms_error: khác `None` khi ĐỌC `decision_log.jsonl` thất bại.
    :param ledger: `TrialLedger` đã trỏ vào `trial_registry.jsonl` thật.
    :param ledger_error: khác `None` khi ĐỌC sổ trial thất bại.
    :param so_lenh_da_dong: số lệnh ĐÃ ĐÓNG thật — tham số duy nhất
        `TrialLedger.available()` chấp nhận để B3 tự tái sinh (L-Z27,
        không có tham số nào nhận thẳng một con số ngân sách).
    :param arm: arm ablation SẢN XUẤT hiện tại (`tier_c.arm_ablation.arm`
        qua `resolve()`). Bắt buộc để phân biệt "tranche ≥2 chưa từng
        khớp" (đo được, bằng 0) với "tranche ≥2 không thể xảy ra trên arm
        này" (`arm_switches.ARM_DON_TRANCHE`) — gộp hai loại 0 này là
        đúng cái bẫy `TD-0246` (phiên `-54`) vừa đặt tên.
    """
    ket_qua: list[ReportMetric] = []
    for code, label, ly_do_mac_dinh in _METRIC_DEFS:
        if code not in _TINH_DUOC:
            ket_qua.append(ReportMetric(code=code, label=label, measured=Measured.pending(ly_do_mac_dinh)))
            continue
        if code == "H3":
            m = _tinh_h3(trades, loi=trades_error)
        elif code == "WINRATE_LONG":
            m = _tinh_winrate(trades, is_short=False, loi=trades_error)
        elif code == "WINRATE_SHORT":
            m = _tinh_winrate(trades, is_short=True, loi=trades_error)
        elif code == "TRANCHE_FILL_1":
            m = _tinh_tranche_fill(trades, tranche=1, loi=trades_error, arm=arm)
        elif code == "TRANCHE_FILL_2":
            m = _tinh_tranche_fill(trades, tranche=2, loi=trades_error, arm=arm)
        elif code == "TRANCHE_FILL_3":
            m = _tinh_tranche_fill(trades, tranche=3, loi=trades_error, arm=arm)
        elif code == "SL_GAP_MS_DIST":
            m = _tinh_sl_gap_ms(gap_ms_values, loi=gap_ms_error)
        else:  # ba dòng BUDGET_*
            m = _tinh_budget(ledger, so_lenh_da_dong=so_lenh_da_dong, code=code, loi=ledger_error)
        ket_qua.append(ReportMetric(code=code, label=label, measured=m))
    return ket_qua


def content_fingerprint() -> str:
    """Vân tay nội dung báo cáo — SHA-256 của (code, label) TỪNG chỉ số,
    theo ĐÚNG thứ tự khai báo (TD-0062, spec dòng 4808).

    🔴 Đổi giá trị hàm này trả về = ĐỔI NỘI DUNG BÁO CÁO = TIÊU 1 TRIAL.
    Đây là quyết định quản trị (đi qua DR-012/ngân sách), không phải một
    refactor tự do — thêm/bớt/sửa nhãn một chỉ số ĐỀU làm hash đổi, có chủ
    đích. Chỉ hash `code`+`label` (KHÔNG hash lý do pending): lý do là văn
    bản vận hành nội bộ giải thích TẠI SAO chưa đo được, không phải một
    phần "nội dung báo cáo" mà LLM đọc để diễn giải — đổi câu chữ giải
    thích, hay đổi CÁCH TÍNH ra sao (TD-0240), không phải hành vi spec
    muốn chặn. Gọi `build_metrics()` KHÔNG tham số — (code, label) không
    phụ thuộc dữ liệu đầu vào.
    """
    payload = "\n".join(f"{m.code}|{m.label}" for m in build_metrics())
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
