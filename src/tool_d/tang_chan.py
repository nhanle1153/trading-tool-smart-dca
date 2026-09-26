"""TD-0435 (`DR-TANG-CHAN-01` §4 điều 3) — chiến lược ĐỌC mức sụt Supervisor công bố, áp bậc 5% (nửa cỡ lệnh).

Phương án C: Supervisor (tiến trình riêng, §6.6) là chủ DUY NHẤT của đỉnh + mức sụt khi chạy dài, và thi hành phần CỨNG
(HALT `/stopentry`, ABORT `/stop`). Phần MỀM — nhân cỡ lệnh 0,5 khi dd trong (soft, halt] — Supervisor không làm được qua
API, nên chiến lược làm, bằng ĐÚNG MỘT hàm ở đây. Test khoá `TD-0436` buộc mọi chiến lược lên tiền gọi hàm này.

FAIL-CLOSED: thiếu `dd_state.json`, file hỏng, cũ quá `NGUONG_HEARTBEAT_CU_S` (Supervisor đã chết — cùng nghĩa với
heartbeat, `TD-0433` (b)), cờ đỏ, HALT/ABORT, hoặc `BINH_THUONG` mà chưa đo được dd ⇒ hệ số **0 = không mở lệnh**. Một bot
lên tiền mà không có Supervisor sống thì không được mở lệnh — đó là chủ đích, không phải lỗi.

Chỉ dùng ở runmode `live`/`dry_run`. Backtest không có Supervisor ⇒ chiến lược giữ công thức riêng (không đổi số đã đo).
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from tool_d.ops.heartbeat_watchdog import NGUONG_HEARTBEAT_CU_S
from tool_d.risk_supervisor import (
    ABORT,
    BINH_THUONG,
    HALT,
    NUA_CO,
    TEN_FILE_DD_STATE,
    RiskSupervisorError,
    doc_dd_state,
)
from tool_d.sizing import mult_dd

_LOG = logging.getLogger(__name__)

#: Cùng gốc với `ops/risk_supervisor_daemon.duong_dan_theo_runmode()` — mỗi runmode một Supervisor, một thư mục (N11).
THU_MUC_SUPERVISOR = Path("runs/risk_supervisor")
RUNMODE_CO_SUPERVISOR = ("live", "dry_run")


def duong_dan_dd_state(runmode: str, *, goc: Path | None = None) -> Path:
    """`goc=None` ⇒ `THU_MUC_SUPERVISOR` đọc LÚC GỌI (test đổi được gốc mà vẫn đi qua đường sản xuất thật)."""
    if runmode not in RUNMODE_CO_SUPERVISOR:
        raise ValueError(f"runmode {runmode!r} không có Supervisor — chỉ {RUNMODE_CO_SUPERVISOR}")
    return (THU_MUC_SUPERVISOR if goc is None else goc) / runmode / TEN_FILE_DD_STATE


def mult_dd_tu_supervisor(
    runmode: str, *, now: datetime, soft_pct: float, halt_pct: float, goc: Path | None = None,
) -> float:
    """Hệ số `dd` (§6.2 hệ số 4) cho định cỡ lệnh ở live/dry-run. `0.0` = không mở lệnh (khớp nghĩa `sizing.mult_dd`).

    `soft_pct`/`halt_pct` đọc từ `tier_c.dd_ladder_pct` bởi chiến lược (N4) — hàm không tự đọc cấu hình.
    """
    duong = duong_dan_dd_state(runmode, goc=goc)
    try:
        st = doc_dd_state(duong)
    except RiskSupervisorError as exc:
        _LOG.warning("TANG_CHAN %s: không đọc được mức sụt Supervisor (%s) — KHÔNG mở lệnh", runmode, exc)
        return 0.0
    tuoi_s = (now - st.luc_utc).total_seconds()
    if tuoi_s > NGUONG_HEARTBEAT_CU_S or tuoi_s < -NGUONG_HEARTBEAT_CU_S:
        _LOG.warning("TANG_CHAN %s: dd_state cũ %.0f s (> %.0f s) — Supervisor không còn sống, KHÔNG mở lệnh",
                     runmode, tuoi_s, NGUONG_HEARTBEAT_CU_S)
        return 0.0
    if st.co_do or st.muc in (HALT, ABORT):
        return 0.0
    if st.muc == NUA_CO:
        # §12c.5 BƯỚC 3: mở lại ở nửa cỡ tới khi dd ≤ soft — Supervisor giữ mức này, hệ số là bậc giữa của CHÍNH thang.
        return mult_dd(dd_pct=halt_pct, soft_pct=soft_pct, halt_pct=halt_pct)
    if st.muc == BINH_THUONG:
        if st.dd_pct is None:
            _LOG.warning("TANG_CHAN %s: Supervisor chưa đo được dd — KHÔNG mở lệnh", runmode)
            return 0.0
        return mult_dd(dd_pct=st.dd_pct, soft_pct=soft_pct, halt_pct=halt_pct)
    return 0.0  # không tới được (doc_dd_state đã kiểm mức) — vẫn đóng
