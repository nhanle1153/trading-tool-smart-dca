"""TD-0384 — tầng THUẦN của lệnh CTRL D10 (`DR-D10-02` §5): chọn rổ, giá ba tranche + SL, cỡ tranche, lúc thoát.

D10 đo HẠ TẦNG (SL sống trên sàn, `gap_ms` khi đổi khối lượng SL, post-only, trượt giá) bằng lệnh CTRL trung tính —
KHÔNG phải một chiến lược nghiên cứu (`DR-D10-02` §3 Q1, `MT-78`). Mọi số đọc từ `tier_c.ctrl_d10` (N4); chiến lược
`user_data/strategies/CtrlD10.py` chỉ nối các hàm ở đây vào callback Freqtrade.

🔴 N6 — đầu vào hỏng (giá ≤ 0, NaN, thiếu dữ liệu sàn) thì RAISE, không trả số rác: một cỡ lệnh bịa trên tiền thật là
thứ tệ nhất bộ chạy này có thể làm.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta

from tool_d.config.loader import ToolDConfig, resolve

LY_DO_THOAT_DU_3 = "CTRL_DU_3_TRANCHE"
LY_DO_THOAT_HET_GIO = "CTRL_HET_GIO"


class CtrlD10Error(ValueError):
    """Đầu vào của tầng CTRL hỏng — fail-closed (N6)."""


@dataclass(frozen=True)
class ThamSoCtrl:
    ro_so_cap: int
    ro_tran_san_usdt: float
    lech_t2_pct: float
    lech_t3_pct: float
    sl_pct: float
    he_so_le_san: float
    thoat_sau_du_3_phut: float
    thoat_toi_da_gio: float


def doc_tham_so(cfg: ToolDConfig) -> ThamSoCtrl:
    """Đọc `tier_c.ctrl_d10` qua `resolve()` (N4). Khoá thiếu ⇒ `KeyError` từ `resolve`, không mặc định."""

    def r(k: str):
        return resolve(cfg, f"tier_c.ctrl_d10.{k}")

    ts = ThamSoCtrl(
        ro_so_cap=int(r("ro_so_cap")),
        ro_tran_san_usdt=float(r("ro_tran_san_usdt")),
        lech_t2_pct=float(r("lech_t2_pct")),
        lech_t3_pct=float(r("lech_t3_pct")),
        sl_pct=float(r("sl_pct")),
        he_so_le_san=float(r("he_so_le_san")),
        thoat_sau_du_3_phut=float(r("thoat_sau_du_3_phut")),
        thoat_toi_da_gio=float(r("thoat_toi_da_gio")),
    )
    # Thứ tự giá phải đúng chiều Long: p1 > p2 > p3 > sl. Cấu hình ngược thì SL nằm TRÊN tranche chờ — một lệnh chờ
    # không bao giờ khớp trước khi SL nổ, và D10 sẽ không sinh được sự kiện đổi SL nào mà không ai hiểu vì sao.
    if not (0 < ts.lech_t2_pct < ts.lech_t3_pct < ts.sl_pct):
        raise CtrlD10Error(
            f"tier_c.ctrl_d10 sai thứ tự: cần 0 < lech_t2 ({ts.lech_t2_pct}) < lech_t3 ({ts.lech_t3_pct}) < sl ({ts.sl_pct})"
        )
    if ts.ro_so_cap < 1 or ts.ro_tran_san_usdt <= 0 or ts.he_so_le_san < 1:
        raise CtrlD10Error(f"tier_c.ctrl_d10 không hợp lệ: {ts}")
    if ts.thoat_sau_du_3_phut <= 0 or ts.thoat_toi_da_gio <= 0:
        raise CtrlD10Error(f"tier_c.ctrl_d10 mốc thoát phải > 0: {ts}")
    return ts


@dataclass(frozen=True)
class KeHoachGiaCtrl:
    p1: float
    p2: float
    p3: float
    sl: float


def ke_hoach_gia(p1: float, ts: ThamSoCtrl) -> KeHoachGiaCtrl:
    """`p2 = p1·(1 − lech_t2)`, `p3 = p1·(1 − lech_t3)`, `sl = p1·(1 − sl_pct)` — Long, `DR-D10-02` §5.2."""
    if not math.isfinite(p1) or p1 <= 0:
        raise CtrlD10Error(f"p1 phải > 0 và hữu hạn, nhận {p1!r}")
    return KeHoachGiaCtrl(
        p1=p1,
        p2=p1 * (1 - ts.lech_t2_pct / 100),
        p3=p1 * (1 - ts.lech_t3_pct / 100),
        sl=p1 * (1 - ts.sl_pct / 100),
    )


def notional_moi_tranche(san_usdt: float, ts: ThamSoCtrl) -> float:
    """Sàn Tool D × `he_so_le_san` (§5.2). Ba tranche bằng nhau."""
    if not math.isfinite(san_usdt) or san_usdt <= 0:
        raise CtrlD10Error(f"sàn Tool D phải > 0 và hữu hạn, nhận {san_usdt!r} — không có sàn thì không định cỡ (N6)")
    return san_usdt * ts.he_so_le_san


def ly_do_thoat(
    *,
    now: datetime,
    mo_luc: datetime,
    so_tranche_da_khop: int,
    luc_khop_cuoi: datetime | None,
    ts: ThamSoCtrl,
) -> str | None:
    """`CTRL_DU_3_TRANCHE` khi đã đủ 3 tranche và qua `thoat_sau_du_3_phut`; `CTRL_HET_GIO` khi qua `thoat_toi_da_gio`
    kể từ lúc mở; không thì `None`. Hết giờ được xét TRƯỚC — một vị thế treo quá hạn phải đóng dù đang ở tranche nào."""
    if now - mo_luc >= timedelta(hours=ts.thoat_toi_da_gio):
        return LY_DO_THOAT_HET_GIO
    if so_tranche_da_khop >= 3:
        if luc_khop_cuoi is None:
            raise CtrlD10Error("đủ 3 tranche mà không có mốc khớp cuối — không suy được lúc thoát (N6)")
        if now - luc_khop_cuoi >= timedelta(minutes=ts.thoat_sau_du_3_phut):
            return LY_DO_THOAT_DU_3
    return None


@dataclass(frozen=True)
class UngVienRo:
    cap: str  # tên cặp Freqtrade, ví dụ "DOGE/USDT:USDT"
    quote_volume_24h: float | None  # None = không đọc được
    san_usdt: float | None  # sàn Tool D mỗi tranche; None = không tính được


def chon_ro(ung_vien: Iterable[UngVienRo], ts: ThamSoCtrl) -> tuple[str, ...]:
    """§5.1 — lọc sàn ≤ `ro_tran_san_usdt`, xếp `quoteVolume` 24h giảm dần, lấy `ro_so_cap` cặp đầu.

    Ứng viên thiếu thanh khoản hoặc thiếu sàn bị LOẠI (không đoán là đạt). Hoà thanh khoản thì xếp theo tên để kết quả
    tất định. Rổ rỗng ⇒ `CtrlD10Error` (fail-closed: bộ chạy không được bật với 0 cặp)."""
    hop_le = [
        u
        for u in ung_vien
        if u.quote_volume_24h is not None
        and math.isfinite(u.quote_volume_24h)
        and u.san_usdt is not None
        and math.isfinite(u.san_usdt)
        and 0 < u.san_usdt <= ts.ro_tran_san_usdt
    ]
    hop_le.sort(key=lambda u: (-u.quote_volume_24h, u.cap))
    ro = tuple(u.cap for u in hop_le[: ts.ro_so_cap])
    if not ro:
        raise CtrlD10Error(f"không cặp nào qua lọc sàn ≤ {ts.ro_tran_san_usdt} USDT — rổ D10 rỗng, từ chối bật")
    return ro
