"""ZoneDetectionProbe — chiến lược THĂM DÒ, không phải chiến lược thật
(TD-0106). Mục đích DUY NHẤT: cho `freqtrade lookahead-analysis` có tín
hiệu entry/exit thật để soi Zone Detection Engine (PHẦN 1 của spec) —
đúng phần §7 cảnh báo có nguy cơ lookahead cố hữu (swing cần 3 nến sau
để xác nhận).

KHÔNG dùng để backtest kết quả thật, KHÔNG có tranche/SL/TP theo spec,
KHÔNG có gate DG1-DG8 (những cái đó thuộc các Phần khác, chưa tới lượt ở
D1 Khối 11). `minimal_roi`/`stoploss` ở đây là giá trị VÔ HIỆU HOÁ có chủ
đích (không phải kết quả tối ưu hoá), chỉ để không có gì cản lookahead-
analysis quan sát entry/exit signal.

Toàn bộ tính swing/confirm/ZSS tái dùng NGUYÊN VẸN
`tool_d.zone_detection`/`tool_d.zone_strength` — không viết lại logic
trong file này, đúng nguyên tắc một nguồn sự thật.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import talib
from freqtrade.strategy import IStrategy, merge_informative_pair

from tool_d.zone_detection import K_XAC_NHAN, confirm_ratio, la_diem_swing, zone_da_bi_huy
from tool_d.zone_strength import NGUONG_ZSS, compression, touch_count, volume_ratio, zone_hop_le, zss

BUF_HE_SO = 0.3  # §1.1 — buf = 0.3 × ATR(14,4H) / price, KHÔNG phải tham số mới


class ZoneDetectionProbe(IStrategy):
    timeframe = "1h"
    informative_timeframe = "4h"
    startup_candle_count = 200

    # Giá trị THĂM DÒ để có lệnh đóng thật cho lookahead-analysis đếm
    # (không đóng lệnh -> mọi lệnh là "forced exit", bị công cụ loại bỏ
    # khỏi phép kiểm) — KHÔNG PHẢI kết quả tối ưu hoá, không liên quan gì
    # tới §6.8e (định cỡ rủi ro thật thuộc phần khác, chưa xây ở D1).
    minimal_roi = {"0": 0.02}
    stoploss = -0.05

    def informative_pairs(self):
        pairs = self.dp.current_whitelist()
        return [(p, self.informative_timeframe) for p in pairs]

    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        inf = self.dp.get_pair_dataframe(pair=metadata["pair"], timeframe=self.informative_timeframe)
        inf = self._tinh_zone_4h(inf)
        dataframe = merge_informative_pair(dataframe, inf, self.timeframe, self.informative_timeframe, ffill=True)
        return dataframe

    def _tinh_zone_4h(self, inf: pd.DataFrame) -> pd.DataFrame:
        """Quét swing đáy trên khung 4H, sinh `zone_hop_le`/`mult_zss_adjusted`.

        Vòng lặp Python thuần (không vector hoá) là CỐ Ý: đây là chiến
        lược thăm dò, mục tiêu là tái dùng ĐÚNG các hàm đã khoá test ở
        TD-0100→0105, không phải một bản viết lại tối ưu hoá hiệu năng.
        """
        n = len(inf)
        thap = inf["low"].tolist()
        cao = inf["high"].tolist()
        dong = inf["close"].tolist()
        volume = inf["volume"].tolist()
        atr = talib.ATR(np.asarray(cao, dtype=float), np.asarray(thap, dtype=float), np.asarray(dong, dtype=float), timeperiod=14)

        zone_hop_le_col = [False] * n
        zone_confirmed_col = [False] * n
        mult_zss_col = [0.0] * n

        for i in range(K_XAC_NHAN, n):
            if not la_diem_swing(thap, i, loai="day"):
                continue
            if np.isnan(atr[i]) or dong[i] == 0:
                continue
            buf = BUF_HE_SO * atr[i] / dong[i]
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
            ty_le = confirm_ratio(i, j)

            # `zone_confirmed`: MỌI swing đã xác nhận (bất kể ZSS) — dùng
            # làm tín hiệu entry cho probe, vì mục tiêu TD-0106 là soi
            # LOOKAHEAD ở cơ chế xác nhận swing (§7), không phải đánh giá
            # chất lượng zone. Cổng `zone_hop_le` (§1.3, NGUONG_ZSS=0.5,
            # "CẦN CALIBRATE") vẫn tính riêng và phơi ra như một indicator
            # để lookahead-analysis kiểm luôn cả ZSS, không chỉ swing.
            zone_confirmed_col[j] = True
            mult_zss_col[j] = diem * ty_le
            if zone_hop_le(zss_value=diem, so_touch=tc, tuoi_nen=K_XAC_NHAN):
                zone_hop_le_col[j] = True

        inf["zone_confirmed"] = zone_confirmed_col
        inf["zone_hop_le"] = zone_hop_le_col
        inf["mult_zss_adjusted"] = mult_zss_col
        return inf

    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        col = f"zone_confirmed_{self.informative_timeframe}"
        dataframe.loc[dataframe[col], "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        # Không có exit thật ở phạm vi Phần 1 (DG/TP/SL thuộc phần khác,
        # chưa xây) — cố ý để trống, KHÔNG bịa điều kiện thoát.
        return dataframe

    def custom_exit(self, pair, trade, current_time, current_rate, current_profit, **kwargs):
        # KHÔNG phải DG8/TIME_STOP thật (§4) — chỉ để lệnh đóng lại nhanh
        # trong lúc thăm dò, tránh một lệnh treo hàng tháng che mất các
        # tín hiệu swing khác mà lookahead-analysis cần đếm.
        if (current_time - trade.open_date_utc).total_seconds() >= 24 * 3600:
            return "probe_time_stop"
        return None
