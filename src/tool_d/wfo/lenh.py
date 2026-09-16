"""TD-0283 — bản ghi TỪNG LỆNH cho WFO của D9 + cắt lát theo fold / theo khối CSCV.

`DR-D9-01` §5: mỗi cấu hình chạy MỘT backtest trên `[T1, T2)`; ba đoạn test
của fold (Nhánh 1, `MT-36`) và tám khối CSCV (§4) đều cắt từ CÙNG danh sách
lệnh đó, gán theo `open_date`. Một cấu hình, một tập lệnh.

════ Phạm vi — cố ý HẸP ════

Module này THUẦN: nhận lệnh đã có số, không đọc kết quả Freqtrade. Kiểm ngày
17/09/2026: trong `src/` **chưa có** đường nào trích `rui_ro_da_trien_khai` theo
từng lệnh từ fill thật (`arm_record.py` chỉ mang số tổng hợp; bộ chạy ablation
TD-0184 còn 🔓). Đường đọc fill đó là việc của lõi bộ chạy dùng chung
(TD-0184 / TD-0286) — viết một bản ở đây là tạo đường thứ hai sẽ trôi lệch.
Ở đây chỉ có CÔNG THỨC `DR-D4-12` §1.4 dạng hàm thuần, để lõi đó gọi.

🔴 Không có bộ chuyển `chay_mot_fold` ở đây: một lượt chạy toàn cửa sổ đọc dữ
liệu tới `T2`, mà `chay_wfo` → `kiem_pham_vi_du_lieu` tầng (b) (TD-0148) đòi
`observed_end ≤ test_end − 1 ngày` của TỪNG fold. Bộ chuyển chỉ qua được bằng
cách KHAI ngày giả — đúng bẫy "lời khai" TD-0148 sinh ra để chặn. Chờ chủ dự
án chốt (`DR-D9-01` §5 đính chính).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, time
from typing import Iterable, Sequence

from tool_d.gates.cscv_cau_hinh import CauHinhCSCV
from tool_d.wfo.folds import Fold


class LenhWFOError(ValueError):
    """Bản ghi lệnh hỏng hoặc cắt lát không hợp lệ. Fail-closed."""


def _duong_huu_han(ten: str, v: float) -> float:
    if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) or v <= 0:
        raise LenhWFOError(f"`{ten}` phải là số hữu hạn > 0, nhận {v!r}")
    return float(v)


@dataclass(frozen=True)
class TrancheKhop:
    """Một tranche ĐÃ KHỚP của lệnh: vốn ký quỹ × đòn bẩy (`stake_usdt`) và giá khớp thật."""

    stake_usdt: float
    entry: float


def rui_ro_da_trien_khai_usdt(tranches: Sequence[TrancheKhop], *, sl: float) -> float:
    """`DR-D4-12` §1.4, LONG: `Σ stake_j × (entry_j − sl) / entry_j` trên tranche ĐÃ KHỚP.

    Không tranche nào khớp ⇒ raise (lệnh không tồn tại, không phải rủi ro 0).
    `entry_j ≤ sl` ⇒ raise: với LONG đó là SL nằm trên giá vào — kế hoạch hỏng,
    không phải một rủi ro âm để cộng.
    """
    if not tranches:
        raise LenhWFOError("không có tranche đã khớp — không định nghĩa được rủi ro đã triển khai")
    sl = _duong_huu_han("sl", sl)
    tong: list[float] = []
    for i, t in enumerate(tranches):
        stake = _duong_huu_han(f"tranche[{i}].stake_usdt", t.stake_usdt)
        entry = _duong_huu_han(f"tranche[{i}].entry", t.entry)
        if entry <= sl:
            raise LenhWFOError(f"tranche[{i}]: entry {entry} ≤ sl {sl} — LONG không có rủi ro dương")
        tong.append(stake * (entry - sl) / entry)
    return math.fsum(tong)


@dataclass(frozen=True)
class LenhWFO:
    """Một lệnh đã đóng. Ngày UTC không múi giờ (cùng quy ước `CauHinhCSCV`).

    `pnl_abs` theo DR-013 (đã trừ phí + funding). Hai thước cạnh nhau, không phán
    xét (`DR-D4-12` §1.3): `r_trien_khai` là đơn vị phán quyết và xếp hạng CSCV;
    `r_realized` (mẫu số `planned_risk_usdt`) báo cạnh bên.
    """

    pair: str
    open_date: datetime
    close_date: datetime
    pnl_abs: float
    rui_ro_da_trien_khai_usdt: float
    planned_risk_usdt: float

    def __post_init__(self) -> None:
        if not self.pair:
            raise LenhWFOError("pair rỗng")
        for ten in ("open_date", "close_date"):
            v = getattr(self, ten)
            if not isinstance(v, datetime) or v.tzinfo is not None:
                raise LenhWFOError(f"`{ten}` phải là datetime UTC không múi giờ, nhận {v!r}")
        if self.close_date < self.open_date:
            raise LenhWFOError(f"{self.pair}: close_date {self.close_date} < open_date {self.open_date}")
        if not isinstance(self.pnl_abs, (int, float)) or isinstance(self.pnl_abs, bool) or not math.isfinite(self.pnl_abs):
            raise LenhWFOError(f"{self.pair}: pnl_abs không hữu hạn: {self.pnl_abs!r}")
        _duong_huu_han("rui_ro_da_trien_khai_usdt", self.rui_ro_da_trien_khai_usdt)
        _duong_huu_han("planned_risk_usdt", self.planned_risk_usdt)

    @property
    def r_trien_khai(self) -> float:
        return self.pnl_abs / self.rui_ro_da_trien_khai_usdt

    @property
    def r_realized(self) -> float:
        return self.pnl_abs / self.planned_risk_usdt


def _trong_cua_so(lenhs: Iterable[LenhWFO], t1: datetime, t2: datetime) -> list[LenhWFO]:
    ds = list(lenhs)
    for l in ds:
        if not (t1 <= l.open_date < t2):
            raise LenhWFOError(f"{l.pair}: open_date {l.open_date} ngoài [{t1}, {t2}) — lỗi nối dữ liệu")
    return ds


def cat_lat_theo_fold(
    lenhs: Iterable[LenhWFO], folds: Sequence[Fold], *, t1: datetime, t2: datetime
) -> tuple[tuple[LenhWFO, ...], ...]:
    """Lát lệnh vào ĐOẠN TEST của từng fold theo `open_date`, nửa mở `[test_start, test_end)`.

    Lệnh mở trong đoạn train-only đầu cửa sổ (trước fold 1) KHÔNG vào lát nào —
    đúng `MT-36`: `n_chi_test ≤ n_toan_cua_so`. Lệnh ngoài `[t1, t2)` ⇒ raise.
    """
    ds = _trong_cua_so(lenhs, t1, t2)
    lat: list[tuple[LenhWFO, ...]] = []
    for f in folds:
        a, b = datetime.combine(f.test_start, time()), datetime.combine(f.test_end, time())
        if not (t1 <= a < b <= t2):
            raise LenhWFOError(f"fold {f.chi_so}: đoạn test [{a}, {b}) ngoài [{t1}, {t2})")
        lat.append(tuple(sorted((l for l in ds if a <= l.open_date < b), key=lambda l: (l.open_date, l.pair))))
    return tuple(lat)


def cat_lat_theo_khoi(lenhs: Iterable[LenhWFO], ch: CauHinhCSCV) -> tuple[tuple[LenhWFO, ...], ...]:
    """Lát lệnh vào `ch.so_khoi` khối CSCV theo `open_date`. Mọi lệnh thuộc đúng một khối."""
    ds = _trong_cua_so(lenhs, ch.t1, ch.t2)
    lat: list[list[LenhWFO]] = [[] for _ in range(ch.so_khoi)]
    for l in ds:
        lat[(l.open_date - ch.t1) // ch.do_dai_khoi].append(l)
    return tuple(tuple(sorted(x, key=lambda l: (l.open_date, l.pair))) for x in lat)


__all__ = [
    "LenhWFO",
    "LenhWFOError",
    "TrancheKhop",
    "cat_lat_theo_fold",
    "cat_lat_theo_khoi",
    "rui_ro_da_trien_khai_usdt",
]
