"""TD-0384 — chiến lược CTRL của bộ chạy D10 (lệnh live tối thiểu, `DR-D10-02`).

KHÔNG phải một chiến lược nghiên cứu: không tín hiệu, không kỳ vọng lãi. Nó đặt lệnh có chủ đích để đo HẠ TẦNG — SL
sống trên sàn, `gap_ms` khi khối lượng SL đổi, post-only có khớp hay bị từ chối, trượt giá khớp (`DR-D10-02` §3 Q1,
`MT-78`). Mọi vị thế là CTRL, 0 trial.

Hình dạng (`DR-D10-02` §5.2, tham số ở `tier_c.ctrl_d10`):
  • Long. Tranche 1 limit post-only tại giá mua tốt nhất (`entry_pricing.price_side = same`) ⇒ `p1`.
  • Tranche 2 / 3: lệnh chờ tại `p1·(1 − 0,3%)` / `p1·(1 − 0,6%)`, đặt sau khi tranche trước khớp.
  • Mỗi tranche = sàn Tool D × 1,10; đòn bẩy `tier_a.L_exchange`.
  • SL = `p1·(1 − 2%)`, bất biến, sống trên sàn (`stoploss_on_exchange`).
  • Thoát 10 phút sau khi đủ 3 tranche, hoặc 4 giờ sau khi mở.

Máy canh ngân sách (`ops/ngan_sach_d10.py`) chạy ở MỌI lần mở vị thế và bơm tranche; trạng thái đọc lại từ DB Freqtrade
và sổ Decision Log mỗi lần — không đếm trong RAM (MT-40). Mọi logic ở ba module thuần `ops/ctrl_d10.py`,
`ops/ngan_sach_d10.py`, `notional.py`; file này chỉ nối chúng vào callback.

🔴 Callback bị Freqtrade nuốt exception (MT-16 vii): chỗ nào một lỗi có thể cướp mất lệnh bảo vệ vốn (giá SL) thì tính
phần thiết yếu TRƯỚC và bọc phần phụ trong `try` (khuôn TD-0403).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import pandas as pd
from freqtrade.persistence import Trade
from freqtrade.strategy import IStrategy, stoploss_from_absolute

from tool_d.config.loader import load_tool_d_config, resolve
from tool_d.gap_ms import LOAI_DOI_SL, LenhSl, sinh_ban_ghi_doi_sl
from tool_d.ledger.decision_log import duong_dan_decision_log, ghi_neu_chua_co
from tool_d.notional import bo_loc_tu_market, san_tool_d
from tool_d.ops.ctrl_d10 import doc_tham_so, ke_hoach_gia, ly_do_thoat, notional_moi_tranche
from tool_d.ops.heartbeat import Heartbeat, duong_dan_heartbeat, ghi_heartbeat
from tool_d.ops.heartbeat_watchdog import TRANG_THAI_BINH_THUONG
from tool_d.ops.ngan_sach_d10 import TrangThaiD10, xet_them_tranche, xet_vi_the_moi
from tool_d.post_only import bi_san_tu_choi
from tool_d.vao_ra_lenh import sinh_ban_ghi_vao_lenh

logger = logging.getLogger(__name__)

TAG_CTRL = "CTRL_D10"
KHOA_P1 = "ctrl_p1"


def _utc(moc: datetime) -> datetime:
    """SQLite trả ngày giờ KHÔNG múi giờ (UTC), bộ nhớ trả CÓ múi giờ — chuẩn hoá trước mọi phép so (bài học TD-0403)."""
    return moc.replace(tzinfo=timezone.utc) if moc.tzinfo is None else moc.astimezone(timezone.utc)


class CtrlD10(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = "1h"
    can_short = False
    stoploss = -0.99  # SL thật là `custom_stoploss` (p1 × (1 − 2%)); giá trị này chỉ là trần an toàn, cùng config
    use_custom_stoploss = True
    position_adjustment_enable = True
    max_entry_position_adjustment = 2  # tranche 2 và 3
    minimal_roi = {"0": 10}  # không chốt lời theo ROI — thoát do `custom_exit` hoặc SL
    process_only_new_candles = True

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self._cfg = load_tool_d_config()
        self._ts = doc_tham_so(self._cfg)
        self._l = float(resolve(self._cfg, "tier_a.L_exchange"))
        self._heartbeat_cu: Heartbeat | None = None

    # ── vận hành ────────────────────────────────────────────────────

    def _runmode(self) -> str:
        return self.dp.runmode.value

    def bot_loop_start(self, current_time: datetime, **kwargs) -> None:
        """Heartbeat cho watchdog D10 (TD-0209/TD-0350), CHỈ live/dry_run — cùng khuôn `ZoneAbsorption`."""
        if self._runmode() not in ("live", "dry_run"):
            return
        duong = duong_dan_heartbeat(self._runmode())
        duong.parent.mkdir(parents=True, exist_ok=True)
        self._heartbeat_cu = ghi_heartbeat(
            duong, trang_thai=TRANG_THAI_BINH_THUONG, now=current_time, heartbeat_cu=self._heartbeat_cu
        )

    # ── dữ liệu / tín hiệu ─────────────────────────────────────────

    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        return dataframe

    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        # Tín hiệu vào LUÔN bật: có vào lệnh hay không do máy canh ngân sách quyết ở `confirm_trade_entry`
        # (tuần tự, ≤ 20 vị thế, cửa sổ, ký quỹ). Rổ (≤ 10 cặp, `DR-D10-02` §5.1) là whitelist của bản cấu hình phủ.
        dataframe["enter_long"] = 1
        dataframe["enter_tag"] = TAG_CTRL
        return dataframe

    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        return dataframe

    # ── ngân sách ──────────────────────────────────────────────────

    def _so_su_kien_doi_sl(self) -> int:
        duong = duong_dan_decision_log(self._runmode())
        if not duong.exists():
            return 0
        dem = 0
        for dong in duong.read_text(encoding="utf-8").splitlines():
            if not dong.strip():
                continue
            ban_ghi = json.loads(dong)
            if ban_ghi.get("loai") == LOAI_DOI_SL and ban_ghi.get("nguon") == self._runmode():
                dem += 1
        return dem

    def _trang_thai(self) -> TrangThaiD10:
        """Đọc lại từ nguồn BỀN mỗi lần (DB Freqtrade + sổ Decision Log), không giữ trong RAM (MT-40)."""
        tat_ca = Trade.get_trades_proxy()
        dang_mo = [t for t in tat_ca if t.is_open]
        so_du = None
        if self.wallets is not None:
            try:
                so_du = float(self.wallets.get_total(self.config["stake_currency"]))
            except Exception:  # noqa: BLE001 — không đọc được ⇒ None ⇒ máy canh TỪ CHỐI (N6)
                logger.exception("D10_NGAN_SACH không đọc được số dư ví")
        return TrangThaiD10(
            so_vi_the_da_mo=len(tat_ca),
            so_vi_the_dang_mo=len(dang_mo),
            moc_vi_the_dau=min((_utc(t.open_date) for t in tat_ca), default=None),
            so_su_kien_doi_sl=self._so_su_kien_doi_sl(),
            ky_quy_dang_mo=float(sum(t.stake_amount for t in dang_mo)),
            so_du=so_du,
        )

    # ── định cỡ ────────────────────────────────────────────────────

    def _notional_tranche(self, pair: str, gia: float) -> float | None:
        """Sàn Tool D × `he_so_le_san`. Không đọc được bộ lọc sàn ⇒ `None` ⇒ không vào lệnh (fail-closed)."""
        try:
            market = self.dp._exchange._markets[pair]  # noqa: SLF001 — ccxt limits không có API công khai
            san = san_tool_d(bo_loc_tu_market(pair, market, gia=gia), strategy_stoploss=float(self.stoploss))
            return notional_moi_tranche(san, self._ts)
        except Exception as exc:  # noqa: BLE001 — mọi lỗi định cỡ về một kết cục: không vào lệnh, có log
            logger.info("CTRL_D10 %s không định cỡ được: %s", pair, exc)
            return None

    def leverage(self, pair, current_time, current_rate, proposed_leverage, max_leverage, entry_tag, side, **kwargs) -> float:
        if self._l > max_leverage:
            logger.warning("CTRL_D10 %s: L_exchange=%s > max sàn %s — dùng %s", pair, self._l, max_leverage, max_leverage)
            return float(max_leverage)
        return self._l

    def custom_stake_amount(self, pair, current_time, current_rate, proposed_stake, min_stake, max_stake, leverage,
                            entry_tag, side, **kwargs) -> float:
        notional = self._notional_tranche(pair, current_rate)
        if notional is None:
            return 0.0
        return notional / leverage

    def confirm_trade_entry(self, pair, order_type, amount, rate, time_in_force, current_time, entry_tag, side,
                            **kwargs) -> bool:
        ly_do = xet_vi_the_moi(self._trang_thai(), ky_quy_lenh=amount * rate / self._l, now=_utc(current_time))
        if ly_do:
            logger.info("D10_NGAN_SACH TU_CHOI vị thế mới %s: %s", pair, " | ".join(ly_do))
            return False
        return True

    # ── tranche ────────────────────────────────────────────────────

    def custom_entry_price(self, pair, trade, current_time, proposed_rate, entry_tag, side, **kwargs):
        if trade is None:
            return proposed_rate  # tranche 1: giá mua tốt nhất (post-only, `price_side = same`)
        p1 = trade.get_custom_data(KHOA_P1)
        if p1 is None:
            return None  # không có p1 thì không có mức chờ — `adjust_trade_position` đã chặn trước
        kh = ke_hoach_gia(float(p1), self._ts)
        return kh.p2 if trade.nr_of_successful_entries == 1 else kh.p3

    def adjust_trade_position(self, trade, current_time, current_rate, current_profit, min_stake, max_stake,
                              current_entry_rate, current_exit_rate, current_entry_profit, current_exit_profit,
                              **kwargs):
        if trade.has_open_orders or trade.nr_of_successful_entries >= 3:
            return None
        p1 = trade.get_custom_data(KHOA_P1)
        if p1 is None:
            logger.error("CTRL_D10 trade %s thiếu %s — không đặt tranche chờ", trade.id, KHOA_P1)
            return None
        kh = ke_hoach_gia(float(p1), self._ts)
        muc = kh.p2 if trade.nr_of_successful_entries == 1 else kh.p3
        if bi_san_tu_choi(muc, current_rate, la_short=False):
            return None  # giá đã xuống dưới mức chờ ⇒ lệnh post-only tại `muc` sẽ bị sàn từ chối
        notional = self._notional_tranche(trade.pair, muc)
        if notional is None:
            return None
        stake = notional / trade.leverage
        ly_do = xet_them_tranche(self._trang_thai(), ky_quy_them=stake, now=_utc(current_time))
        if ly_do:
            logger.info("D10_NGAN_SACH TU_CHOI tranche %s trade %s: %s",
                        trade.nr_of_successful_entries + 1, trade.id, " | ".join(ly_do))
            return None
        return stake

    def order_filled(self, pair, trade, order, current_time, **kwargs) -> None:
        if order.ft_order_side != trade.entry_side:
            return
        if trade.nr_of_successful_entries == 1 and trade.get_custom_data(KHOA_P1) is None:
            trade.set_custom_data(KHOA_P1, float(order.safe_price))
        try:  # sổ đo không được cướp phần thiết yếu phía trên (khuôn TD-0403/TD-0239)
            ban_ghi = sinh_ban_ghi_vao_lenh(
                order_id=order.order_id,
                ts=order.order_filled_date,
                trade_id=trade.id,
                pair=pair,
                tranche=trade.nr_of_successful_entries,
                side=order.ft_order_side,
                price=order.safe_price,
                amount=order.safe_amount_after_fee,
                nguon=self._runmode(),
            )
            ghi_neu_chua_co(duong_dan_decision_log(self._runmode()), ban_ghi)
        except Exception:  # noqa: BLE001
            logger.exception("%s: ghi VAO_RA_LENH thất bại (TD-0384)", pair)

    # ── SL / thoát ────────────────────────────────────────────────

    def custom_stoploss(self, pair, trade, current_time, current_rate, current_profit, **kwargs):
        p1 = trade.get_custom_data(KHOA_P1)
        if p1 is None:
            logger.error("CTRL_D10 trade %s thiếu %s — không tính được SL (giữ SL hiện có)", trade.id, KHOA_P1)
            return None
        kh = ke_hoach_gia(float(p1), self._ts)
        sl = stoploss_from_absolute(kh.sl, current_rate, is_short=False, leverage=trade.leverage)
        try:  # TD-0403 — sổ đo không được cướp giá SL
            self._ghi_gap_ms(trade, sl_price=kh.sl)
        except Exception:  # noqa: BLE001
            logger.exception("%s: ghi gap_ms thất bại — SL vẫn được trả về (TD-0384)", pair)
        return sl

    def _ghi_gap_ms(self, trade, *, sl_price: float) -> None:
        """Một bản ghi `DOI_SL` mỗi lần khối lượng SL trên sàn đổi — cùng khuôn `ZoneAbsorption._ghi_gap_ms`."""
        lenh_sl = [
            LenhSl(
                order_id=o.order_id,
                status=o.status,
                amount=o.amount if o.amount is not None else o.ft_amount,
                order_date=o.order_date,
                order_update_date=o.order_update_date,
            )
            for o in trade.orders
            if o.ft_order_side == "stoploss"
        ]
        if len(lenh_sl) < 2:
            return
        moc_khop_entry = [
            o.order_filled_date
            for o in trade.orders
            if o.ft_order_side == trade.entry_side and o.status == "closed" and o.order_filled_date is not None
        ]
        for bg in sinh_ban_ghi_doi_sl(
            lenh_sl=lenh_sl, moc_khop_entry=moc_khop_entry, trade_id=trade.id, sl_price=sl_price,
            nguon=self._runmode(),
        ):
            ghi_neu_chua_co(duong_dan_decision_log(self._runmode()), bg)

    def custom_exit(self, pair, trade, current_time, current_rate, current_profit, **kwargs):
        moc_khop = [
            _utc(o.order_filled_date)
            for o in trade.orders
            if o.ft_order_side == trade.entry_side and o.status == "closed" and o.order_filled_date is not None
        ]
        return ly_do_thoat(
            now=_utc(current_time),
            mo_luc=_utc(trade.open_date),
            so_tranche_da_khop=trade.nr_of_successful_entries,
            luc_khop_cuoi=max(moc_khop, default=None),
            ts=self._ts,
        )
