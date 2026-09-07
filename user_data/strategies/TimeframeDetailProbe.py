"""TimeframeDetailProbe — chiến lược THĂM DÒ cho TD-0113 (D5, §... khớp
tranche/SL/TP nhiều mức giá trong một nến 1H). KHÔNG phải chiến lược
thật. Vào lệnh ngay ở nến đầu tiên có dữ liệu; ROI 2%, stoploss -10% —
hai ngưỡng được dựng SẴN trong dữ liệu tổng hợp `td0113_make_data.py`
để cùng lọt vào MỘT nến 1H, nhưng ở HAI THỜI ĐIỂM 5m khác nhau (ROI đạt
trước, stoploss chạm sau). Mục tiêu: so exit_reason khi bật/tắt
`timeframe_detail=5m` để chứng minh thứ tự khớp theo dòng 5m thật.
"""

from __future__ import annotations

import pandas as pd
from freqtrade.strategy import IStrategy


class TimeframeDetailProbe(IStrategy):
    timeframe = "1h"
    minimal_roi = {"0": 0.01}
    stoploss = -0.10
    startup_candle_count = 0

    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        return dataframe

    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        dataframe.loc[dataframe.index == 0, "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        return dataframe
