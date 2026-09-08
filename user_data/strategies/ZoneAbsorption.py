"""ZoneAbsorption — chiến lược SẢN XUẤT của Tool D (DR-D4-04, TD-0187).

Đây là chiến lược DUY NHẤT mà D4 chạy. `ZoneAbsorptionMinimal.py` KHÔNG bị
sửa một dòng — nó là fixture của `L-Z49` (CRITICAL) với bằng chứng
backtest thật, và docstring của chính nó khai việc nối tầng này là *"ngoài
phạm vi hẹp của L-Z49"*. Phần zone/kế hoạch tranche ở đây **chép nguyên
vẹn** logic của Minimal (cùng hàm thuần, cùng thứ tự) — hai file phải cho
cùng zone trên cùng dữ liệu; test khoá TD-0187 đối chiếu điều đó.

════ TD-0187 thêm gì so với Minimal — và vì sao từng thứ ════

1. **`leverage()` trả `tier_a.L_exchange`.** Không cài thì Freqtrade mặc
   định 1x (tài liệu: *"If not implemented, leverage defaults to 1x"*).
   Repo trước file này KHÔNG có `leverage()` ở đâu ⇒ mọi backtest tới nay
   chạy 1x, không phải 3x đã chốt DR-D0PRE-06 (MT-16, triệu chứng 5).

2. **`custom_stake_amount()` = tầng định cỡ §6.8f B1** qua `sizing.py`:
   `rho_eff = rho × 6 mult`, `N_full = rho_eff × E_D / R_eff`, stake tranche
   1 = `N_full × w₁ / L_exchange`. 🔴 `stake` của Freqtrade là KÝ QUỸ
   (*"position size = initial capital × leverage"*) nên phải chia
   `L_exchange` — ở 1x hai thứ trùng nhau, đúng lý do lỗi này sống được.

3. **`adjust_trade_position()` trả `N_full × wᵢ / L_exchange`, KHÔNG trả
   `trade.stake_amount`.** `trade.stake_amount` là TỔNG hiện tại; trả nó là
   10 → +10 → +20, chính cơ chế sinh tỉ trọng ¼-¼-½ đo được trên 91 lượt
   khớp niêm phong (MT-16). `N_full` đọc từ `custom_data` chốt lúc tranche
   1 — đúng đường `L-Z49` đã kiểm, không tính lại.

4. **DG1–DG5 (TD-0181) nối vào tranche 2/3** qua `danh_gia_tat_ca()` +
   `arm_switches.duoc_them_tranche()`. Minimal kích hoạt tranche thuần theo
   giá; từ đây cổng nào của arm đóng thì KHÔNG bơm thêm.

5. **Arm đọc từ `tier_c.arm_ablation.arm`** (N4). `Z0-T2` không phải arm.

════ Kế hoạch cỡ lệnh đi qua ba callback như thế nào ════

    custom_stake_amount(pair, entry_tag, …)     ← CHƯA có Trade
        → tính HeSoMult, lap_ke_hoach_co_lenh()  → cất tạm self._cho[pair]
        → trả stake tranche 1
    confirm_trade_entry(pair, …)                 ← vẫn CHƯA có Trade
        → không có kế hoạch tạm / HALT → False (fail-closed, không mở)
    order_filled(pair, trade, order, …)          ← CÓ Trade, tranche 1 vừa khớp
        → trade.set_custom_data("co_lenh", …) + ("ke_hoach", …)
    adjust_trade_position(trade, …)              ← đọc custom_data, KHÔNG tính lại

Cất tạm theo `pair` là đủ vì một pair chỉ có một vị thế mở; ở `order_filled`
có `trade.id` thật nên từ đó về sau mọi thứ đi qua `custom_data` (D7: assert
theo trade, không trộn giữa các cặp).

════ Sáu hệ số trong backtest D4 — TƯỜNG MINH, không "vắng mặt lặng lẽ" ════

| hệ số   | nguồn trong file này                                              |
|---------|-------------------------------------------------------------------|
| regime  | ADX(14,1D) tại nến tín hiệu (`adx_1d` merge từ khung 1D)          |
| zss     | ZSS của zone tại nến tín hiệu (khoá `zs` trong enter_tag)         |
| corr    | mean |corr(log-return 1H, 720 nến)| với mọi vị thế ĐANG MỞ         |
| dd      | drawdown từ đỉnh equity ĐÃ THỰC HIỆN của ví — xem hạn chế bên dưới |
| edge    | **= 1.0** — chưa có lệnh live (spec dòng 1774)                     |
| deploy  | Σ notional đã khớp / Σ notional kế hoạch, trên vị thế đang mở      |

⚠️ **Hạn chế nói thẳng (ghi vào `d4_han_che` khi đóng cổng):** `mult_dd`
đo trên equity **đã thực hiện** (`wallets.get_total(stake)`), spec §12c.5
đòi *"equity đã bao gồm PnL chưa thực hiện"*. Trong callback chỉ có giá
của pair hiện tại nên PnL chưa thực hiện của các pair khác không tính được
sạch tại đây; phần thiếu này làm dd đo được **nhỏ hơn hoặc bằng** dd thật,
tức `mult_dd` **nới hơn** thiết kế ở đúng lúc thị trường sập. Đây là chỗ
phải làm đúng trước D11 (dry-run có API equity), không phải chỗ để im.

════ Phạm vi CHƯA phủ trong file này, nói thẳng ════

  - **Phần 2 (trend filter) và §3.3b (xác nhận entry) CHƯA nối vào tín
    hiệu vào lệnh** — TD-0182. Duy nhất điều kiện `ADX(1D) ≥ adx_threshold`
    của §2.5 được nối ở đây, vì `mult_regime` không có nhánh cho ADX < 20
    (spec: *"§2.5 đã chặn"*) — nối một mẩu §2.5 để tầng định cỡ nhất quán,
    KHÔNG phải để thay TD-0182.
  - **Kết nạp danh mục §6.8f B2** (Σ risk / Σ margin) — TD-0188; móc ở
    `confirm_trade_entry()`.
  - **Chốt lời PHẦN 5** — TD-0189; `minimal_roi` vẫn tắt, `stoploss` chỉ là
    lưới cuối.
  - **Ghi Decision Log PLAN/GATE_CHECK** — TD-0184 (bộ chạy). Mọi trường
    §8.3 cần (`mult_breakdown`, `rho_eff`, `planned_risk_usdt`,
    `planned_margin_usdt`, `l_exchange_at_entry`, `tranche_weights`) đã có
    trong `custom_data["co_lenh"]`.
  - LONG only (DR-D4-01). DG6 điều kiện C/D vẫn `False` như Minimal.
  - **DG6 chỉ bật ở arm `Z3b`** — DIỄN GIẢI: §10.1 định nghĩa Z3 = *"KHÔNG
    DG6"*, Z3b = *"CỘNG DG6"*, các arm khác không nhắc. Chọn tắt cho mọi arm
    ≠ Z3b để cặp Z3/Z3b cô lập được DG6; ghi ra để cãi lại được.
"""

from __future__ import annotations

import json
import logging
import math
from datetime import datetime

import numpy as np
import pandas as pd
import talib
from freqtrade.persistence import Trade
from freqtrade.strategy import IStrategy, merge_informative_pair, stoploss_from_absolute

from tool_d.arm_switches import ARM_HOP_LE, cong_ap_dung, duoc_them_tranche
from tool_d.config.loader import load_tool_d_config, resolve
from tool_d.dg1_dg5_tranche_gates import danh_gia_tat_ca
from tool_d.dg6_early_invalidation import dg6_dong_vi_the, dieu_kien_a, dieu_kien_b
from tool_d.funding_stop import funding_paid_cumulative, is_funding_stop_triggered
from tool_d.sizing import (
    HeSoMult,
    KeHoachCoLenh,
    SizingError,
    lap_ke_hoach_co_lenh,
    mult_corr,
    mult_dd,
    mult_deploy,
    mult_edge,
    mult_regime,
    mult_zss,
)
from tool_d.time_stop import is_time_stop_triggered
from tool_d.trade_plan import KeHoachTranche, tinh_ke_hoach
from tool_d.trend_context import trend_dir_tai
from tool_d.zone_detection import K_XAC_NHAN, la_diem_swing, zone_da_bi_huy
from tool_d.zone_strength import compression, touch_count, volume_ratio, zone_hop_le, zss

logger = logging.getLogger(__name__)

BUF_ZONE = 0.3  # §1.1 — như Minimal
CUA_SO_CORR_NEN_1H = 720  # §6.2 hệ số 3 — 30 ngày, HẰNG SỐ ĐỊNH NGHĨA (LD-35b)
EMA_NHANH, EMA_CHAM = 20, 50  # §2.1

# Khoá viết tắt của enter_tag. Bốn khoá mới so với Minimal: zs (ZSS tại tín
# hiệu — cho mult_zss và DG5), t4 (trend_dir 4H tại tín hiệu — mốc DG2),
# sw (timestamp ms nến swing 4H — để tính lại ZSS hiện tại cho DG5).
_KHOA_JSON = ("zl", "zh", "p1", "p2", "p3", "sl", "zs", "t4", "sw")


def _ma_hoa(kh: KeHoachTranche, *, zss_value: float, trend_4h: str, swing_ts_ms: int) -> str:
    return json.dumps(
        {
            "zl": kh.zone_low, "zh": kh.zone_high, "p1": kh.p1, "p2": kh.p2, "p3": kh.p3,
            "sl": kh.sl, "zs": round(zss_value, 6), "t4": trend_4h, "sw": swing_ts_ms,
        },
        separators=(",", ":"),
    )


def _giai_ma(tag: str | None, *, atr_1h_tai_tranche1: float) -> tuple[KeHoachTranche, dict] | None:
    if not tag:
        return None
    try:
        d = json.loads(tag)
    except (ValueError, TypeError):
        return None
    if not all(k in d for k in _KHOA_JSON):
        return None
    p_avg = (d["p1"] + d["p2"] + d["p3"]) / 3
    kh = KeHoachTranche(
        zone_low=d["zl"], zone_high=d["zh"], p1=d["p1"], p2=d["p2"], p3=d["p3"], sl=d["sl"],
        r_eff_plan=(p_avg - d["sl"]) / p_avg, atr_1h_tai_tranche1=atr_1h_tai_tranche1,
    )
    return kh, d


class ZoneAbsorption(IStrategy):
    timeframe = "1h"
    informative_timeframe = "4h"
    informative_1d = "1d"
    can_short = False
    # 1000 nến 1H ≈ 42 ngày: đủ để ADX(14,1D) và EMA50(1D) có giá trị khi
    # backtest bắt đầu. 200 của Minimal không đủ cho khung 1D.
    startup_candle_count = 1000
    position_adjustment_enable = True
    max_entry_position_adjustment = 2
    use_custom_stoploss = True

    minimal_roi = {"0": 10}  # TP thật = TD-0189 (PHẦN 5)
    # Lưới cuối; SL THẬT đọc từ kế hoạch qua custom_stoploss (chỉ được siết,
    # không nới). Giá trị là "rủi ro trên vốn đã nhân đòn bẩy": −0.30 ở 3x
    # = giá đi ngược 10%, xa hơn mọi SL zone hợp lệ (R_eff ≤ ~3%) nhưng
    # vẫn trong đệm thanh lý (~33% ở 3x, L-Z3 ≥ 8).
    # 🔴 KHÔNG dùng −0.9 như Minimal: Freqtrade nhân SÀN stake lên theo
    # 1/(1−|stoploss|) để dự phòng lỗ — với −0.9 là ×10, và lần chạy đầu
    # của file này đã bị chính điều đó chặn lệnh mẫu (stake 14,7 < min 18,4)
    # rồi NUỐT exception. Đây là một trong ba thứ TD-0082 chưa tính
    # (cùng với mult_* và phép chia đòn bẩy) — xem MT-16 triệu chứng (vii).
    stoploss = -0.30

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self._cfg = load_tool_d_config()
        self._arm = str(resolve(self._cfg, "tier_c.arm_ablation.arm"))
        if self._arm not in ARM_HOP_LE:
            raise SizingError(f"tier_c.arm_ablation.arm = {self._arm!r} không thuộc {ARM_HOP_LE}")
        self._notional_co_dinh = resolve(self._cfg, "tier_c.arm_ablation.notional_co_dinh_usdt")
        self._l_exchange = float(resolve(self._cfg, "tier_a.L_exchange"))
        self._adx_threshold = float(resolve(self._cfg, "tier_frozen.adx_threshold.value"))
        self._cho: dict[str, dict] = {}   # pair → kế hoạch cỡ lệnh chờ order_filled
        self._halt: set[str] = set()      # pair đang bị HALT tại lúc định cỡ
        self._dinh_equity: float | None = None

    # ── dữ liệu ──────────────────────────────────────────────────────

    def informative_pairs(self):
        pairs = self.dp.current_whitelist()
        return [(p, self.informative_timeframe) for p in pairs] + [(p, self.informative_1d) for p in pairs]

    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        dataframe["atr_1h"] = talib.ATR(dataframe["high"], dataframe["low"], dataframe["close"], timeperiod=14)

        inf4 = self.dp.get_pair_dataframe(pair=metadata["pair"], timeframe=self.informative_timeframe)
        inf4 = self._tinh_zone_4h(inf4)
        dataframe = merge_informative_pair(dataframe, inf4, self.timeframe, self.informative_timeframe, ffill=True)

        inf1d = self.dp.get_pair_dataframe(pair=metadata["pair"], timeframe=self.informative_1d)
        inf1d["adx"] = talib.ADX(inf1d["high"], inf1d["low"], inf1d["close"], timeperiod=14)
        dataframe = merge_informative_pair(dataframe, inf1d[["date", "adx"]], self.timeframe, self.informative_1d, ffill=True)
        return dataframe

    def _tinh_zone_4h(self, inf: pd.DataFrame) -> pd.DataFrame:
        """CHÉP NGUYÊN logic Minimal._tinh_zone_4h — cùng zone trên cùng dữ
        liệu — cộng thêm: EMA20/50 4H → trend_dir_4h; ZSS, swing ts vào tag."""
        n = len(inf)
        thap, cao, dong, volume = (inf[c].tolist() for c in ("low", "high", "close", "volume"))
        ts_ms = (inf["date"].astype("int64") // 10**6).tolist()
        atr = talib.ATR(np.asarray(cao, dtype=float), np.asarray(thap, dtype=float), np.asarray(dong, dtype=float), timeperiod=14)
        ema_f = talib.EMA(np.asarray(dong, dtype=float), timeperiod=EMA_NHANH)
        ema_s = talib.EMA(np.asarray(dong, dtype=float), timeperiod=EMA_CHAM)
        trend = [trend_dir_tai(ema_f, ema_s, i) for i in range(n)]

        zone_valid = [False] * n
        tag_col = [""] * n
        for i in range(K_XAC_NHAN, n):
            if not la_diem_swing(thap, i, loai="day"):
                continue
            if math.isnan(atr[i]) or dong[i] == 0:
                continue
            buf = BUF_ZONE * atr[i] / dong[i]
            zone_low, zone_high = thap[i] * (1 - buf), thap[i] * (1 + buf)
            j = i + K_XAC_NHAN
            if j >= n or zone_da_bi_huy(thap, i, j, loai="day"):
                continue
            v_r = volume_ratio(volume, i_swing=i)
            comp = compression(cao, thap, dong, i_hinh_thanh=i, i_hien_tai=j)
            if v_r is None or comp is None:
                continue
            tc = touch_count(thap, dong, zone_low, zone_high, i_swing=i, t=j, loai="day")
            diem = zss(touch=tc, ty_le_volume=v_r, do_nen=comp)
            if not zone_hop_le(zss_value=diem, so_touch=tc, tuoi_nen=K_XAC_NHAN) or math.isnan(atr[j]):
                continue
            kh = tinh_ke_hoach(zone_low=zone_low, zone_high=zone_high, gia_dong_cua=dong[j], atr_4h=atr[j], atr_1h_tai_tranche1=0.0)
            zone_valid[j] = True
            tag_col[j] = _ma_hoa(kh, zss_value=diem, trend_4h=trend[j], swing_ts_ms=int(ts_ms[i]))

        inf["zone_valid"] = zone_valid
        inf["ke_hoach_json"] = tag_col
        inf["trend_dir_4h"] = trend
        return inf

    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        sfx = f"_{self.informative_timeframe}"
        # Mẩu DUY NHẤT của §2.5 nối ở đây: ADX(1D) ≥ ngưỡng — vì mult_regime
        # không có nhánh cho ADX thấp hơn (spec: "§2.5 đã chặn"). Phần còn lại
        # của Phần 2 + §3.3b là TD-0182.
        hop_le = dataframe[f"zone_valid{sfx}"] & (dataframe[f"adx_{self.informative_1d}"] >= self._adx_threshold)
        dataframe.loc[hop_le, "enter_long"] = 1
        dataframe.loc[hop_le, "enter_tag"] = dataframe.loc[hop_le, f"ke_hoach_json{sfx}"]
        return dataframe

    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        return dataframe

    # ── đòn bẩy + định cỡ ───────────────────────────────────────────

    def leverage(self, pair, current_time, current_rate, proposed_leverage, max_leverage, entry_tag, side, **kwargs) -> float:
        if self._l_exchange > max_leverage:
            raise SizingError(f"L_exchange={self._l_exchange} > max_leverage sàn cho {pair} = {max_leverage}")
        return self._l_exchange

    def custom_stake_amount(self, pair, current_time, current_rate, proposed_stake, min_stake, max_stake, leverage, entry_tag, side, **kwargs) -> float:
        hang = self._hang_hien_tai(pair)
        giai = _giai_ma(entry_tag, atr_1h_tai_tranche1=0.0)
        if hang is None or giai is None:
            raise SizingError(f"{pair}: vào lệnh mà không có kế hoạch tranche trong enter_tag — không định cỡ mò")
        kh, d = giai

        mult = HeSoMult(
            regime=mult_regime(
                adx_1d=float(hang[f"adx_{self.informative_1d}"]),
                strong=float(resolve(self._cfg, "tier_frozen.mult_regime.value.strong")),
                weak=float(resolve(self._cfg, "tier_frozen.mult_regime.value.weak")),
                adx_split=float(resolve(self._cfg, "tier_frozen.mult_regime.value.adx_split")),
                adx_threshold=self._adx_threshold,
            ),
            zss=mult_zss(float(d["zs"])),
            corr=mult_corr(corr_pool=self._corr_pool(pair), nguong=tuple(resolve(self._cfg, "tier_b.mult_corr_thresholds"))),
            dd=mult_dd(
                dd_pct=self._dd_pct(),
                soft_pct=float(resolve(self._cfg, "tier_c.dd_ladder_pct.soft")),
                halt_pct=float(resolve(self._cfg, "tier_c.dd_ladder_pct.halt")),
            ),
            edge=mult_edge(edge_ratio=None, so_lenh_live=0, nguong=float(resolve(self._cfg, "tier_frozen.mult_edge_thr.value"))),
            deploy=mult_deploy(deployed_ratio=self._deployed_ratio(), nguong=float(resolve(self._cfg, "tier_frozen.mult_deploy_thr.value"))),
        )
        if mult.la_halt:
            # Không hỏi cỡ lúc HALT (§12c.5). confirm_trade_entry sẽ từ chối.
            self._halt.add(pair)
            self._cho.pop(pair, None)
            return proposed_stake
        self._halt.discard(pair)

        plan = lap_ke_hoach_co_lenh(
            cfg=self._cfg, arm=self._arm, r_eff=kh.r_eff_plan, mult=mult,
            notional_co_dinh_usdt=self._notional_co_dinh,
        )
        stake1 = plan.stake_tranche(1)
        # Freqtrade sẽ cắt về max_stake / từ chối dưới min_stake một cách IM
        # LẶNG — cả hai đều phá D0.1 mà không để lại dấu vết. Raise thay vì để nó cắt.
        if stake1 > max_stake:
            raise SizingError(f"{pair}: stake tranche 1 = {stake1:.4f} > max_stake {max_stake:.4f} — ví không đủ, không được cắt ngầm")
        if min_stake is not None and stake1 < min_stake:
            raise SizingError(f"{pair}: stake tranche 1 = {stake1:.4f} < min_stake {min_stake:.4f} — dưới sàn sàn giao dịch (TD-0082 đáng lẽ đã lọc)")
        self._cho[pair] = {"co_lenh": plan.to_dict(), "ke_hoach": kh.to_dict(), "tag": d}
        return stake1

    def confirm_trade_entry(self, pair, order_type, amount, rate, time_in_force, current_time, entry_tag, side, **kwargs) -> bool:
        if pair in self._halt:
            return False  # HALT §12c.5 — ngừng MỞ lệnh mới
        return pair in self._cho  # không có kế hoạch cỡ lệnh → không mở (fail-closed)

    def order_filled(self, pair, trade, order, current_time, **kwargs) -> None:
        if order.ft_order_side != trade.entry_side or trade.nr_of_successful_entries != 1:
            return
        cho = self._cho.pop(pair, None)
        if cho is None:
            raise SizingError(f"{pair}: tranche 1 khớp mà không có kế hoạch cỡ lệnh chờ — thứ tự callback đã hỏng")
        hang = self._hang_hien_tai(pair)
        kh = cho["ke_hoach"]
        kh["atr_1h_tai_tranche1"] = float(hang["atr_1h"]) if hang is not None and not math.isnan(hang["atr_1h"]) else 0.0
        trade.set_custom_data("co_lenh", cho["co_lenh"])
        trade.set_custom_data("ke_hoach", kh)
        trade.set_custom_data("tag", cho["tag"])

    def custom_entry_price(self, pair, trade, current_time, proposed_rate, entry_tag, side, **kwargs):
        """Limit tại p1 / p2 / p3 — như Minimal (§3.5 post-only). Thiếu hàm
        này thì vào lệnh theo giá mở nến, phá luôn L-Z50 (fill không được
        tệ hơn kế hoạch) — bản nháp đầu của file này đã quên nó."""
        if trade is None:
            giai = _giai_ma(entry_tag, atr_1h_tai_tranche1=0.0)
            return proposed_rate if giai is None else giai[0].p1
        kh, _, _ = self._doc_ke_hoach(trade)
        return kh.p2 if trade.nr_of_successful_entries == 1 else kh.p3

    # ── tranche 2/3 ─────────────────────────────────────────────────

    def _doc_ke_hoach(self, trade) -> tuple[KeHoachTranche, KeHoachCoLenh, dict]:
        raw_kh, raw_cl, tag = trade.get_custom_data("ke_hoach"), trade.get_custom_data("co_lenh"), trade.get_custom_data("tag")
        if raw_kh is None or raw_cl is None or tag is None:
            # KHÔNG tái tạo từ dataframe (bug TD-0114) và KHÔNG tính lại cỡ
            # lệnh — thiếu là lỗi lắp ráp, không phải "chưa có".
            raise SizingError(f"trade {trade.id} ({trade.pair}) thiếu kế hoạch trong custom_data — L-Z49 đã bị vi phạm")
        return KeHoachTranche.from_dict(raw_kh), KeHoachCoLenh.from_dict(raw_cl), tag

    def adjust_trade_position(self, trade, current_time, current_rate, current_profit, min_stake, max_stake,
                              current_entry_rate, current_exit_rate, current_entry_profit, current_exit_profit, **kwargs):
        if trade.has_open_orders or trade.nr_of_successful_entries >= 3:
            return None
        if cong_ap_dung(self._arm) == ():
            return None  # arm entry đơn — không bao giờ thêm tranche
        kh, cl, tag = self._doc_ke_hoach(trade)
        i = trade.nr_of_successful_entries + 1  # tranche sắp xét: 2 hoặc 3
        muc = kh.p2 if i == 2 else kh.p3
        if current_rate > muc:
            return None

        cong = danh_gia_tat_ca(
            close_4h_ke_tu_tranche1=self._close_4h_ke_tu(trade, current_time),
            sl=kh.sl,
            huong="long",
            trend_dir_tai_tranche1=tag["t4"],
            trend_dir_hien_tai=self._trend_4h_hien_tai(trade.pair, current_time),
            margin_reserve_con_lai=max(cl.planned_margin_usdt - float(trade.stake_amount), 0.0),
            margin_can_cho_tranche=cl.stake_tranche(i),
            so_nen_1h_da_troi=int((current_time - trade.open_date_utc).total_seconds() // 3600),
            dg4_bars_1h=int(resolve(self._cfg, "tier_b.dg4_bars_1h")),
            zss_tai_tranche1=float(tag["zs"]),
            zss_hien_tai=self._zss_hien_tai(trade.pair, tag, current_time),
            nguong_giam_toi_da=float(resolve(self._cfg, "tier_frozen.dg5_zss_decay_max.value")),
        )
        # Dấu vết GATE_CHECK (§8.3) — DEBUG để không nhiễu log thường; bộ chạy
        # E3 (TD-0184) sẽ ghi vào Decision Log, đây là chỗ nó lấy dữ liệu.
        logger.debug("GATE_CHECK %s trade=%s tranche=%d t=%s %s", trade.pair, trade.id, i, current_time, cong)
        if not duoc_them_tranche(arm=self._arm, ket_qua_cong=cong):
            return None
        stake_i = cl.stake_tranche(i)
        if stake_i > max_stake:
            raise SizingError(f"{trade.pair}: stake tranche {i} = {stake_i:.4f} > max_stake {max_stake:.4f}")
        # Tag = CÙNG kế hoạch tranche 1 (mặt cắt L-Z49 quan sát từ ngoài).
        return stake_i, trade.enter_tag

    # ── thoát ────────────────────────────────────────────────────────

    def custom_stoploss(self, pair, trade, current_time, current_rate, current_profit, **kwargs):
        """SL tuyệt đối = `kh.sl` (bất biến D0.2), quy đổi ĐÚNG đòn bẩy.

        🔴 Minimal trả `(sl / current_rate) − 1`. Freqtrade hiểu giá trị đó
        là *"rủi ro của lệnh"* trên vốn ĐÃ NHÂN đòn bẩy (*"10% stoploss at
        10x triggers on a 1% move"*), nên ở 3x SL thật nằm gần gấp BA so với
        kế hoạch — lần chạy đầu của file này: 38/38 lệnh nổ stop trong vài
        phút ở giá CAO HƠN `sl`. Vô hình ở 1x (Minimal), lộ ngay khi đòn
        bẩy thật (MT-16 triệu chứng vi). `stoploss_from_absolute(...,
        leverage=)` là hàm Freqtrade cấp đúng cho việc này."""
        kh, _, _ = self._doc_ke_hoach(trade)
        return stoploss_from_absolute(kh.sl, current_rate, is_short=trade.is_short, leverage=trade.leverage)

    def custom_exit(self, pair, trade, current_time, current_rate, current_profit, **kwargs):
        kh, _, _ = self._doc_ke_hoach(trade)
        gio = (current_time - trade.open_date_utc).total_seconds() / 3600
        if is_time_stop_triggered(tranche1_bar=0, current_bar=int(gio // 4),
                                  max_hold_bars=int(resolve(self._cfg, "tier_b.max_hold_bars_4h"))):
            return "TIME_STOP"
        fpc = funding_paid_cumulative(trade.funding_fees)
        if kh.r_eff_plan > 0 and is_funding_stop_triggered(
            funding_paid_cumulative=fpc, r_eff_plan=kh.r_eff_plan,
            threshold_frac=float(resolve(self._cfg, "tier_b.dg7_funding_frac")),
        ):
            return "FUNDING_STOP"
        if self._arm != "Z3b":
            return None  # DG6 chỉ ở Z3b — xem diễn giải trong docstring module
        hang = self._hang_hien_tai(pair)
        atr_now = float(hang["atr_1h"]) if hang is not None and not math.isnan(hang["atr_1h"]) else None
        a = False
        if atr_now is not None and kh.atr_1h_tai_tranche1 > 0:
            a = dieu_kien_a(atr_now / kh.atr_1h_tai_tranche1, current_rate, p_avg=trade.open_rate, huong="long")
        b = False
        df, _ = self.dp.get_analyzed_dataframe(pair=pair, timeframe=self.timeframe)
        if df is not None:
            dong = df.loc[df["date"] > trade.open_date_utc, "close"].tolist()
            b = dieu_kien_b(dong, p1=kh.p1, so_nen_da_troi=len(dong), huong="long")
        return "DG6_EARLY_INVALIDATION" if dg6_dong_vi_the(a=a, b=b, c=False, d=False) else None

    # ── trợ giúp đọc dữ liệu (không tính toán nghiệp vụ) ─────────────

    def _hang_hien_tai(self, pair: str):
        df, _ = self.dp.get_analyzed_dataframe(pair=pair, timeframe=self.timeframe)
        return None if df is None or df.empty else df.iloc[-1]

    def _df_4h(self, pair: str, current_time: datetime) -> pd.DataFrame:
        """Khung 4H CHỈ gồm nến ĐÃ ĐÓNG tại `current_time`.

        🔴 Trong backtest, `dp.get_pair_dataframe()` trả TOÀN BỘ dữ liệu đã
        nạp — kể cả nến tương lai. Dùng thẳng `iloc[-1]` ở callback là
        lookahead: DG1/DG2/DG5 sẽ "biết" giá sắp tới. Cùng họ lỗi B2 mà
        H4-D canh ở zone detection, nhưng ở một mặt cắt H4-D KHÔNG phủ
        (callback, không phải populate). Cắt theo `date + 4h ≤ now`."""
        df = self.dp.get_pair_dataframe(pair=pair, timeframe=self.informative_timeframe)
        return df[df["date"] + pd.Timedelta(hours=4) <= current_time]

    def _close_4h_ke_tu(self, trade, current_time: datetime) -> list[float]:
        df = self._df_4h(trade.pair, current_time)
        return df.loc[df["date"] > trade.open_date_utc, "close"].tolist()

    def _trend_4h_hien_tai(self, pair: str, current_time: datetime) -> str:
        df = self._df_4h(pair, current_time)
        dong = df["close"].to_numpy(dtype=float)
        if len(dong) <= EMA_CHAM:
            return "FLAT"  # chưa đủ lịch sử = chưa có bằng chứng trend (fail-closed, như trend_context)
        ema_f, ema_s = talib.EMA(dong, timeperiod=EMA_NHANH), talib.EMA(dong, timeperiod=EMA_CHAM)
        return trend_dir_tai(ema_f, ema_s, len(dong) - 1)

    def _zss_hien_tai(self, pair: str, tag: dict, current_time: datetime) -> float:
        """ZSS tính LẠI cho cùng zone tại nến 4H ĐÃ ĐÓNG gần nhất (DG5)."""
        df = self._df_4h(pair, current_time)
        ts = (df["date"].astype("int64") // 10**6).tolist()
        try:
            i_swing = ts.index(int(tag["sw"]))
        except ValueError as exc:
            raise SizingError(f"{pair}: không tìm thấy nến swing {tag['sw']} trong khung 4H — không tính lại ZSS mò") from exc
        t = len(df) - 1
        thap, cao, dong, vol = (df[c].tolist() for c in ("low", "high", "close", "volume"))
        v_r = volume_ratio(vol, i_swing=i_swing)
        comp = compression(cao, thap, dong, i_hinh_thanh=i_swing, i_hien_tai=t)
        if v_r is None or comp is None:
            return float("nan")  # dg5 fail-closed với NaN (TrancheGateError) — không bịa số
        tc = touch_count(thap, dong, tag["zl"], tag["zh"], i_swing=i_swing, t=t, loai="day")
        return zss(touch=tc, ty_le_volume=v_r, do_nen=comp)

    def _vi_the_mo_khac(self, pair: str) -> list:
        return [t for t in Trade.get_trades_proxy(is_open=True) if t.pair != pair]

    def _corr_pool(self, pair: str) -> float:
        khac = self._vi_the_mo_khac(pair)
        if not khac:
            return 0.0
        r0 = self._log_return_1h(pair)
        vals = []
        for t in khac:
            r1 = self._log_return_1h(t.pair)
            n = min(len(r0), len(r1))
            if n < 30:
                continue
            c = np.corrcoef(r0[-n:], r1[-n:])[0, 1]
            if not math.isnan(c):
                vals.append(abs(c))
        return float(np.mean(vals)) if vals else 0.0

    def _log_return_1h(self, pair: str) -> np.ndarray:
        df, _ = self.dp.get_analyzed_dataframe(pair=pair, timeframe=self.timeframe)
        dong = df["close"].to_numpy(dtype=float)[-(CUA_SO_CORR_NEN_1H + 1):]
        return np.diff(np.log(dong))

    def _dd_pct(self) -> float:
        if not self.wallets:
            return 0.0
        tong = float(self.wallets.get_total(self.config["stake_currency"]))
        if self._dinh_equity is None or tong > self._dinh_equity:
            self._dinh_equity = tong
        if not self._dinh_equity:
            return 0.0
        return max(0.0, (self._dinh_equity - tong) / self._dinh_equity * 100.0)

    def _deployed_ratio(self) -> float:
        khop = ke_hoach = 0.0
        for t in Trade.get_trades_proxy(is_open=True):
            cl = t.get_custom_data("co_lenh")
            if cl is None:
                continue
            ke_hoach += float(cl["n_full_usdt"])
            khop += float(t.stake_amount) * float(getattr(t, "leverage", 1.0) or 1.0)
        return 0.0 if ke_hoach <= 0 else min(khop / ke_hoach, 1.0)
