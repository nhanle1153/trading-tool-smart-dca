"""TD-0412 (`DR-D10-02` §6, §6.3) — `RoFunding` chạy ở D10 (lệnh live tối thiểu, tiền thật, tài khoản phụ).

Lớp con, KHÔNG sửa `RoFunding.py` (file của ứng viên IQ-0003, kỷ luật `DR-BIEN-THE-01`). Chỉ đổi đúng ba thứ:
  1. Vốn rổ: đọc `config["tool_d_d10"]["von_ro_usdt"]` do bộ khởi chạy D10 tính (`DR-D10-02` §6.3 Q7/Q9), thay vốn sản xuất
     `tier_a.von_ro_usdt`. Thiếu hay hỏng ⇒ TỪ CHỐI khởi động (không rơi về vốn sản xuất — đó là tiền gấp ~10 lần).
  2. Máy canh D10 (`ops/ngan_sach_d10_ro.py`) chạy SAU chốt gốc của `RoFunding` ở `confirm_trade_entry`: đủ mẫu ⇒ dừng mở
     mới, hết hạn, trần ký quỹ 50%, số dư không đọc được ⇒ từ chối. Lệnh RA không qua máy canh.
  3. Heartbeat cho watchdog D10 (runmode `live`), cùng khuôn `ZoneAbsorption`/`CtrlD10`.
Mọi thứ khác — nhóm rổ, giờ cân rổ, định cỡ, stop thảm hoạ, nhãn thoát — là của `RoFunding`, nên D10 đo đúng chiến lược sẽ
lên tiền.
"""

from __future__ import annotations

import logging
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

from freqtrade.persistence import Trade

sys.path.insert(0, str(Path(__file__).resolve().parent))  # nạp lớp cha cùng thư mục chiến lược

from RoFunding import RoFunding  # noqa: E402

from tool_d.ops.heartbeat import Heartbeat, duong_dan_heartbeat, ghi_heartbeat  # noqa: E402
from tool_d.ops.heartbeat_watchdog import TRANG_THAI_BINH_THUONG  # noqa: E402
from tool_d.ops.ngan_sach_d10_ro import TrangThaiD10Ro, xet_vao_lenh  # noqa: E402
from tool_d.ro_funding import RoFundingError  # noqa: E402

logger = logging.getLogger(__name__)

KHOA_CAU_HINH_D10 = "tool_d_d10"


def _utc(moc: datetime) -> datetime:
    """SQLite trả ngày giờ không múi giờ (UTC) — chuẩn hoá trước mọi phép so (bài học TD-0403)."""
    return moc.replace(tzinfo=timezone.utc) if moc.tzinfo is None else moc.astimezone(timezone.utc)


class RoFundingD10(RoFunding):
    def __init__(self, config: dict) -> None:
        super().__init__(config)
        von = (config.get(KHOA_CAU_HINH_D10) or {}).get("von_ro_usdt")
        if not isinstance(von, (int, float)) or isinstance(von, bool) or not math.isfinite(von) or von <= 0:
            raise RoFundingError(
                f"{KHOA_CAU_HINH_D10}.von_ro_usdt = {von!r} — thiếu vốn D10 từ bộ khởi chạy (DR-D10-02 §6.3 Q9); "
                "KHÔNG rơi về vốn sản xuất tier_a.von_ro_usdt"
            )
        self._von = float(von)
        self._heartbeat_cu: Heartbeat | None = None

    def bot_loop_start(self, current_time: datetime, **kwargs) -> None:
        runmode = self.dp.runmode.value
        if runmode not in ("live", "dry_run"):
            return
        duong = duong_dan_heartbeat(runmode)
        duong.parent.mkdir(parents=True, exist_ok=True)
        self._heartbeat_cu = ghi_heartbeat(
            duong, trang_thai=TRANG_THAI_BINH_THUONG, now=current_time, heartbeat_cu=self._heartbeat_cu
        )

    def _trang_thai_d10(self) -> TrangThaiD10Ro:
        """Đọc lại từ DB mỗi lần (MT-40): lệnh vào/ra đã khớp (không tính lệnh stop), số lần cân rổ khác nhau có lệnh
        vào khớp, mốc vị thế đầu, ký quỹ đang mở, số dư ví."""
        tat_ca = Trade.get_trades_proxy()
        so_lenh = 0
        lan_can_ro: set[datetime] = set()
        for t in tat_ca:
            for o in t.orders:
                if o.ft_order_side == "stoploss" or o.status != "closed" or o.order_filled_date is None:
                    continue
                so_lenh += 1
                if o.ft_order_side == t.entry_side:
                    lan_can_ro.add(_utc(o.order_filled_date).replace(minute=0, second=0, microsecond=0))
        so_du = None
        if self.wallets is not None:
            try:
                so_du = float(self.wallets.get_total(self.config["stake_currency"]))
            except Exception:  # noqa: BLE001 — không đọc được ⇒ None ⇒ máy canh TỪ CHỐI (N6)
                logger.exception("D10_RO không đọc được số dư ví")
        return TrangThaiD10Ro(
            so_lenh_khop=so_lenh,
            so_lan_can_ro=len(lan_can_ro),
            moc_vi_the_dau=min((_utc(t.open_date) for t in tat_ca), default=None),
            ky_quy_dang_mo=float(sum(t.stake_amount for t in tat_ca if t.is_open)),
            so_du=so_du,
        )

    def confirm_trade_entry(
        self, pair, order_type, amount, rate, time_in_force, current_time, entry_tag, side, **kwargs
    ) -> bool:
        if not super().confirm_trade_entry(
            pair, order_type, amount, rate, time_in_force, current_time, entry_tag, side, **kwargs
        ):
            return False
        ly_do = xet_vao_lenh(self._trang_thai_d10(), ky_quy_lenh=amount * rate / self._don_bay_san, now=_utc(current_time))
        if ly_do:
            logger.info("D10_RO TU_CHOI %s %s: %s", side, pair, " | ".join(ly_do))
            return False
        return True
