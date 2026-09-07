"""Context Trend Filter — Phần 2 (TD-0128, trước 07/09/2026 đánh số TD-0119).

§2.1 (`trend_dir_tai`), §2.2 (`xac_nhan_da_khung`, L-Z8), §2.3
(`tuoi_trend_nen`), §2.5 (`du_dieu_kien_vao_lenh`). EMA/ADX tính bằng
TA-Lib ở tầng gọi (giống `zone_strength.compression`) — module này chỉ
nhận mảng EMA/ADX đã tính sẵn, không tự gọi TA-Lib, để giữ mỗi hàm THUẦN
và dễ test bằng số dựng tay.

🔴 Phạm vi CHƯA phủ: L-Z8 ("trend_dir_1d == trend_dir_4h tại MỌI bản ghi
plan") chỉ kiểm được đầy đủ khi có bản ghi plan thật (§8) — chưa có code
đặt lệnh nào ở D1/D2 để sinh ra plan. `xac_nhan_da_khung()` ở đây là
mảnh ghép đúng, sẽ được nối vào plan thật khi TD-0114 dựng chiến lược.
"""

from __future__ import annotations

import math
from typing import Literal, Sequence

TrendDir = Literal["UP", "DOWN", "FLAT"]

K_TUOI_TREND_TOI_THIEU = 5  # §2.3 — [CẦN CALIBRATE], nến ứng với timeframe truyền vào
NGUONG_ADX = 20  # §2.5


def trend_dir_tai(ema_fast: Sequence[float], ema_slow: Sequence[float], i: int, *, do_tre: int = 10) -> TrendDir:
    """§2.1 — `UP` nếu fast>slow VÀ slope(slow) dương; `DOWN` đảo lại;
    ngược lại (kể cả mâu thuẫn hoặc chưa đủ dữ liệu) là `FLAT`.

    `FLAT` khi thiếu dữ liệu là lựa chọn fail-closed có chủ đích: không
    có bằng chứng trend là chính xác trạng thái "chưa có bằng chứng",
    không phải một sentinel bịa ra.
    """
    if i - do_tre < 0 or i >= len(ema_fast) or i >= len(ema_slow):
        return "FLAT"
    f, s, s_truoc = ema_fast[i], ema_slow[i], ema_slow[i - do_tre]
    if any(math.isnan(x) for x in (f, s, s_truoc)):
        return "FLAT"
    do_doc = s - s_truoc
    if f > s and do_doc > 0:
        return "UP"
    if f < s and do_doc < 0:
        return "DOWN"
    return "FLAT"


def xac_nhan_da_khung(huong_1d: TrendDir, huong_4h: TrendDir) -> bool:
    """§2.2, L-Z8 — hai khung PHẢI đồng thuận (kể cả cùng là `FLAT`;
    §2.5 tự loại `FLAT` ở bước điều kiện vào lệnh, không phải ở đây)."""
    return huong_1d == huong_4h


def tuoi_trend_nen(ema_fast: Sequence[float], ema_slow: Sequence[float], i: int) -> int | None:
    """§2.3 — số nến kể từ lần cross gần nhất theo đúng hướng hiện tại.

    `None` nếu tại `i` chưa đủ dữ liệu (NaN) hoặc không tìm được điểm
    cross trong toàn bộ lịch sử đã cho — KHÔNG suy đoán "đủ tuổi" khi
    không biết cross xảy ra khi nào (fail-closed, cùng tinh thần
    `volume_ratio`/`compression` ở `zone_strength.py`).
    """
    if i >= len(ema_fast) or i >= len(ema_slow):
        return None
    if math.isnan(ema_fast[i]) or math.isnan(ema_slow[i]):
        return None
    dau_hien_tai = _dau(ema_fast[i] - ema_slow[i])
    for j in range(i - 1, -1, -1):
        if math.isnan(ema_fast[j]) or math.isnan(ema_slow[j]):
            return None
        if _dau(ema_fast[j] - ema_slow[j]) != dau_hien_tai:
            return i - (j + 1)
    return None


def _dau(x: float) -> int:
    return 1 if x > 0 else (-1 if x < 0 else 0)


def du_dieu_kien_vao_lenh(
    *,
    huong_muc_tieu: TrendDir,
    huong_1d: TrendDir,
    huong_4h: TrendDir,
    adx_1d: float,
    tuoi_nen: int | None,
) -> bool:
    """§2.5 — bốn điều kiện, TẤT CẢ phải đạt. `FLAT`/đảo hướng/ADX yếu/
    trend non đều loại thẳng, không có gate mềm (đúng ý spec: đây là
    ca dễ lẫn với mean-reversion nhất)."""
    if huong_1d != huong_muc_tieu:
        return False
    if not xac_nhan_da_khung(huong_1d, huong_4h):
        return False
    if adx_1d < NGUONG_ADX:
        return False
    if tuoi_nen is None or tuoi_nen < K_TUOI_TREND_TOI_THIEU:
        return False
    return True
