"""ZoneAbsorptionMinimal — chiến lược TỐI THIỂU THẬT cho TD-0114 (L-Z49
CRITICAL, D7). Tái dùng NGUYÊN VẸN mọi hàm thuần đã khoá test ở Khối 11
(`zone_detection`, `zone_strength`) và Khối 13 (`trend_context` — CHƯA
nối vào tín hiệu vào lệnh, xem "Phạm vi" dưới) + `entry_confirmation`
(CHƯA nối, cùng lý do) + `dg6_early_invalidation`/`funding_stop`/
`time_stop` (ĐÃ nối vào `custom_exit`) + `trade_plan` (kế hoạch tranche
qua `trade.custom_data`).

Mục tiêu DUY NHẤT của file này: chứng minh bằng backtest THẬT rằng kế
hoạch (`KeHoachTranche`) ghi lúc tranche 1 khớp sống sót NGUYÊN VẸN qua
callback tranche 2/3 (`adjust_trade_position`) và `custom_exit` — đây
chính là L-Z49. Cơ chế chứng minh: mọi lệnh (entry lẫn exit) của CÙNG
một trade mang cùng JSON kế hoạch làm tag (`_ma_hoa_ke_hoach`, nén
`zone_low`/`zone_high`/`p1`/`p2`/`p3`/`sl`) — nếu `custom_data` bị
mất/lệch giữa các callback, tag đọc lại ở tranche 2/3 sẽ KHÁC
`trade.enter_tag` của tranche 1, và khác biệt đó xuất hiện thẳng trong
`enter_tag`/order tag của file kết quả backtest xuất ra — kiểm được từ
BÊN NGOÀI, không cần tin lời code.

🐛 **Bug thật bắt được và đã sửa khi chạy backtest thật lần đầu (ghi lại
để không ai vô tình quay lại cách cũ):** phiên bản đầu tái tạo kế hoạch
(khi `custom_data` còn trống) bằng cách đọc "hàng cuối" của dataframe đã
merge từ khung 4H (`merge_informative_pair(..., ffill=True)`). `ffill`
chỉ giữ giá trị hợp lệ trong đúng cửa sổ 4H của zone đó — nếu lệnh chờ
tranche 1 (post-only, tối đa 3 nến chờ theo §3.5) khớp SAU khi đã lăn
sang cửa sổ 4H kế tiếp (cửa sổ đó chưa có zone mới → cột trở lại NaN),
`get_analyzed_dataframe().iloc[-1]` tại đúng lúc khớp có thể rơi vào
cửa sổ NaN đó, hoặc tệ hơn — nếu MỘT zone MỚI đã được xác nhận ở cửa sổ
kế tiếp, đọc nhầm SANG zone mới đó. Backtest thật (07/09/2026, 2 mã,
20240601-20250601) bắt được đúng 2/25 trade nhiều tranche có vân tay
zone KHÔNG khớp giữa tranche 1 và tranche 2/3 — chính xác là ca thứ hai.
**Sửa:** nguồn dữ liệu KHỞI TẠO kế hoạch đổi sang `trade.enter_tag`
(snapshot JSON được Freqtrade chốt cứng vào lúc ĐẶT LỆNH, không đổi
theo dataframe về sau) thay vì đọc lại dataframe đã merge — xem
`_doc_hoac_khoi_tao_ke_hoach`. Sau lần khởi tạo đầu, mọi lần đọc sau đó
vẫn đi qua `trade.custom_data` như thiết kế ban đầu — đây chính là phần
L-Z49 thật sự kiểm.

🔴 Phạm vi CHƯA phủ, nói thẳng (xem OQ-12 và ghi chú tại chỗ):
  - LONG ONLY. Short hoãn theo đúng khuyến nghị §3.3d ("Long trước").
  - Entry KHÔNG dùng Phần 2 (`trend_context`) hay §3.3b
    (`entry_confirmation`) — hai module đó ĐÃ kiểm đúng độc lập
    (TD-0128/0129) nhưng nối vào tín hiệu vào lệnh thật cần thêm 2
    khung dữ liệu (1D cho trend, RSI cho phân kỳ) — để dành cho task
    dựng chiến lược SẢN XUẤT, ngoài phạm vi hẹp của L-Z49.
  - DG1–DG5 (gate kích hoạt tranche MỚI) CHƯA xây — tranche 2/3 kích
    hoạt thuần tuý theo giá chạm p2/p3. DG6/7/8 (ĐÓNG vị thế ĐÃ có) đã
    nối đủ.
  - DG6 điều kiện C/D được GỌI nhưng LUÔN nhận `False`/tắt (C cần
    `trend_dir` — chưa nối; D chỉ áp Short — không áp dụng ở bản LONG
    ONLY này) — không phải "đã kiểm và không kích hoạt", mà là "chưa
    có dữ liệu để kiểm", ghi rõ để không ai đọc nhầm thành đã xác nhận.
  - `p1` dùng giá đóng cửa nến zone 4H xác nhận, CHƯA đúng "nến 1H đóng
    cửa C" của §3.3b/§3.5 (xem docstring `trade_plan.py`).
"""

from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
import talib
from freqtrade.strategy import IStrategy, merge_informative_pair

from tool_d.dg6_early_invalidation import dg6_dong_vi_the, dieu_kien_a, dieu_kien_b
from tool_d.funding_stop import funding_paid_cumulative, is_funding_stop_triggered
from tool_d.time_stop import is_time_stop_triggered
from tool_d.trade_plan import KeHoachTranche, tinh_ke_hoach
from tool_d.zone_detection import K_XAC_NHAN, la_diem_swing, zone_da_bi_huy
from tool_d.zone_strength import compression, touch_count, volume_ratio, zone_hop_le, zss

BUF_ZONE = 0.3  # §1.1 — buf = 0.3 × ATR(14,4H)/price
MAX_HOLD_BARS_4H = 24  # §4b.3 — DG8, [CẦN CALIBRATE]
FUNDING_THRESHOLD_FRAC = 0.3  # §4c.2 — DG7

# Khoá viết tắt để JSON gọn trong 255 ký tự cho phép của order tag.
_KHOA_JSON = ("zl", "zh", "p1", "p2", "p3", "sl")


def _ma_hoa_ke_hoach(kh: KeHoachTranche) -> str:
    """Nén 6 trường giá của kế hoạch thành JSON gọn — dùng làm
    `enter_tag`/order tag. ĐÂY LÀ NGUỒN DỮ LIỆU ĐÁNG TIN CẬY DUY NHẤT để
    khởi tạo lại kế hoạch (xem "Bug thật bắt được" ở docstring module):
    Freqtrade chốt cứng tag vào lệnh lúc TẠO, không đọc lại dataframe."""
    return json.dumps(
        {"zl": kh.zone_low, "zh": kh.zone_high, "p1": kh.p1, "p2": kh.p2, "p3": kh.p3, "sl": kh.sl}
    )


def _giai_ma_ke_hoach(tag: str | None, *, atr_1h_tai_tranche1: float) -> KeHoachTranche | None:
    """Đảo ngược `_ma_hoa_ke_hoach`. `None` nếu tag không phải JSON hợp
    lệ (không phải lỗi — chỉ đơn giản là chưa có kế hoạch nào để đọc)."""
    if not tag:
        return None
    try:
        d = json.loads(tag)
    except (ValueError, TypeError):
        return None
    if not all(k in d for k in _KHOA_JSON):
        return None
    p_avg = (d["p1"] + d["p2"] + d["p3"]) / 3
    return KeHoachTranche(
        zone_low=d["zl"],
        zone_high=d["zh"],
        p1=d["p1"],
        p2=d["p2"],
        p3=d["p3"],
        sl=d["sl"],
        r_eff_plan=(p_avg - d["sl"]) / p_avg,
        atr_1h_tai_tranche1=atr_1h_tai_tranche1,
    )


class ZoneAbsorptionMinimal(IStrategy):
    timeframe = "1h"
    informative_timeframe = "4h"
    can_short = False
    startup_candle_count = 200
    position_adjustment_enable = True
    max_entry_position_adjustment = 2  # tranche 2 + tranche 3
    use_custom_stoploss = True

    # Vô hiệu hoá có chủ đích — TP thật (Phần 6) chưa xây; SL thật đọc
    # từ custom_stoploss (kế hoạch), giá trị lớp dưới đây chỉ là lưới
    # cuối không bao giờ chạm tới trong điều kiện bình thường.
    minimal_roi = {"0": 10}
    stoploss = -0.9

    def informative_pairs(self):
        pairs = self.dp.current_whitelist()
        return [(p, self.informative_timeframe) for p in pairs]

    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        dataframe["atr_1h"] = talib.ATR(dataframe["high"], dataframe["low"], dataframe["close"], timeperiod=14)
        inf = self.dp.get_pair_dataframe(pair=metadata["pair"], timeframe=self.informative_timeframe)
        inf = self._tinh_zone_4h(inf)
        dataframe = merge_informative_pair(dataframe, inf, self.timeframe, self.informative_timeframe, ffill=True)
        return dataframe

    def _tinh_zone_4h(self, inf: pd.DataFrame) -> pd.DataFrame:
        n = len(inf)
        thap = inf["low"].tolist()
        cao = inf["high"].tolist()
        dong = inf["close"].tolist()
        volume = inf["volume"].tolist()
        atr = talib.ATR(np.asarray(cao, dtype=float), np.asarray(thap, dtype=float), np.asarray(dong, dtype=float), timeperiod=14)

        zone_valid = [False] * n
        ke_hoach_json_col = [""] * n

        for i in range(K_XAC_NHAN, n):
            if not la_diem_swing(thap, i, loai="day"):
                continue
            if math.isnan(atr[i]) or dong[i] == 0:
                continue
            buf = BUF_ZONE * atr[i] / dong[i]
            zone_low, zone_high = thap[i] * (1 - buf), thap[i] * (1 + buf)
            j = i + K_XAC_NHAN
            if j >= n:
                continue
            if zone_da_bi_huy(thap, i, j, loai="day"):
                continue
            v_r = volume_ratio(volume, i_swing=i)
            comp = compression(cao, thap, dong, i_hinh_thanh=i, i_hien_tai=j)
            if v_r is None or comp is None:
                continue
            tc = touch_count(thap, dong, zone_low, zone_high, i_swing=i, t=j, loai="day")
            diem = zss(touch=tc, ty_le_volume=v_r, do_nen=comp)
            if not zone_hop_le(zss_value=diem, so_touch=tc, tuoi_nen=K_XAC_NHAN):
                continue
            if math.isnan(atr[j]):
                continue
            kh = tinh_ke_hoach(zone_low=zone_low, zone_high=zone_high, gia_dong_cua=dong[j], atr_4h=atr[j], atr_1h_tai_tranche1=0.0)
            zone_valid[j] = True
            ke_hoach_json_col[j] = _ma_hoa_ke_hoach(kh)

        inf["zone_valid"] = zone_valid
        inf["ke_hoach_json"] = ke_hoach_json_col
        return inf

    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        sfx = f"_{self.informative_timeframe}"
        hop_le = dataframe[f"zone_valid{sfx}"]
        dataframe.loc[hop_le, "enter_long"] = 1
        # Chốt CỨNG kế hoạch vào enter_tag ngay tại nến tín hiệu — Freqtrade
        # chụp giá trị này vào lệnh lúc TẠO lệnh, không đọc lại dataframe
        # sau đó. Đây là nguồn dữ liệu ĐÁNG TIN CẬY duy nhất để khởi tạo
        # custom_data, xem ghi chú "Bug thật bắt được" ở docstring module.
        dataframe.loc[hop_le, "enter_tag"] = dataframe.loc[hop_le, f"ke_hoach_json{sfx}"]
        return dataframe

    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        return dataframe

    def _lay_hang_hien_tai(self, pair: str) -> pd.Series | None:
        df, _ = self.dp.get_analyzed_dataframe(pair=pair, timeframe=self.timeframe)
        if df is None or df.empty:
            return None
        return df.iloc[-1]

    def _doc_hoac_khoi_tao_ke_hoach(self, trade) -> KeHoachTranche | None:
        """Đọc `trade.custom_data` nếu đã có (đây chính là phần L-Z49
        kiểm — dữ liệu phải sống sót nguyên vẹn qua MỌI lần gọi). Lần
        ĐẦU TIÊN (chưa có), khởi tạo từ `trade.enter_tag` — snapshot
        JSON Freqtrade chốt cứng lúc TẠO lệnh tranche 1, không phải từ
        dataframe đã merge (xem "Bug thật bắt được" ở docstring module)
        — rồi ghi NGAY vào `custom_data` để các lần đọc sau đi đúng
        đường L-Z49 muốn kiểm."""
        raw = trade.get_custom_data("ke_hoach")
        if raw is not None:
            return KeHoachTranche.from_dict(raw)
        hang = self._lay_hang_hien_tai(trade.pair)
        atr_1h = float(hang["atr_1h"]) if hang is not None and not math.isnan(hang["atr_1h"]) else 0.0
        kh = _giai_ma_ke_hoach(trade.enter_tag, atr_1h_tai_tranche1=atr_1h)
        if kh is None:
            return None
        trade.set_custom_data("ke_hoach", kh.to_dict())
        return kh

    def custom_entry_price(self, pair, trade, current_time, proposed_rate, entry_tag, side, **kwargs):
        if trade is None:
            hang = self._lay_hang_hien_tai(pair)
            if hang is None:
                return proposed_rate
            kh = _giai_ma_ke_hoach(hang.get(f"ke_hoach_json_{self.informative_timeframe}"), atr_1h_tai_tranche1=0.0)
            return proposed_rate if kh is None else kh.p1
        kh = self._doc_hoac_khoi_tao_ke_hoach(trade)
        if kh is None:
            return proposed_rate
        return kh.p2 if trade.nr_of_successful_entries == 1 else kh.p3

    def adjust_trade_position(
        self, trade, current_time, current_rate, current_profit, min_stake, max_stake,
        current_entry_rate, current_exit_rate, current_entry_profit, current_exit_profit, **kwargs,
    ):
        kh = self._doc_hoac_khoi_tao_ke_hoach(trade)
        if kh is None or trade.nr_of_successful_entries >= 3:
            return None
        # Gắn LẠI đúng JSON kế hoạch (không phải tính mới) làm tag của
        # lệnh tranche 2/3 — nếu custom_data từng bị lệch, tag ở đây sẽ
        # KHÁC `trade.enter_tag` của tranche 1, lộ ra ngay khi đối
        # chiếu file backtest xuất ra (chính là phép kiểm L-Z49 ngoài).
        tag = _ma_hoa_ke_hoach(kh)
        if trade.nr_of_successful_entries == 1 and current_rate <= kh.p2:
            return trade.stake_amount, tag
        if trade.nr_of_successful_entries == 2 and current_rate <= kh.p3:
            return trade.stake_amount, tag
        return None

    def custom_stoploss(self, pair, trade, current_time, current_rate, current_profit, **kwargs):
        kh = self._doc_hoac_khoi_tao_ke_hoach(trade)
        if kh is None:
            return None
        return (kh.sl / current_rate) - 1

    def custom_exit(self, pair, trade, current_time, current_rate, current_profit, **kwargs):
        kh = self._doc_hoac_khoi_tao_ke_hoach(trade)
        if kh is None:
            return None

        gio_da_troi = (current_time - trade.open_date_utc).total_seconds() / 3600
        nen_4h_da_troi = int(gio_da_troi // 4)
        if is_time_stop_triggered(tranche1_bar=0, current_bar=nen_4h_da_troi, max_hold_bars=MAX_HOLD_BARS_4H):
            return "TIME_STOP"

        fpc = funding_paid_cumulative(trade.funding_fees)
        if kh.r_eff_plan > 0 and is_funding_stop_triggered(
            funding_paid_cumulative=fpc, r_eff_plan=kh.r_eff_plan, threshold_frac=FUNDING_THRESHOLD_FRAC
        ):
            return "FUNDING_STOP"

        hang = self._lay_hang_hien_tai(pair)
        atr_1h_hien_tai = float(hang["atr_1h"]) if hang is not None and not math.isnan(hang["atr_1h"]) else None
        a = False
        if atr_1h_hien_tai is not None and kh.atr_1h_tai_tranche1 > 0:
            ty_le = atr_1h_hien_tai / kh.atr_1h_tai_tranche1
            a = dieu_kien_a(ty_le, current_rate, p_avg=trade.open_rate, huong="long")

        b = False
        if hang is not None:
            df, _ = self.dp.get_analyzed_dataframe(pair=pair, timeframe=self.timeframe)
            if df is not None:
                dong_tu_tranche1 = df.loc[df["date"] > trade.open_date_utc, "close"].tolist()
                so_nen = len(dong_tu_tranche1)
                b = dieu_kien_b(dong_tu_tranche1, p1=kh.p1, so_nen_da_troi=so_nen, huong="long")

        # C/D: CHƯA có dữ liệu trend_dir (C) và không áp dụng ở bản
        # LONG ONLY này (D) — luôn False, xem "Phạm vi" ở docstring module.
        if dg6_dong_vi_the(a=a, b=b, c=False, d=False):
            return "DG6_EARLY_INVALIDATION"
        return None
