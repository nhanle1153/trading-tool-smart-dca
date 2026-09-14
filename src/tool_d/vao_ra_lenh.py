"""TD-0239 — bộ sinh bản ghi `VAO_RA_LENH` (§8.3), nguồn cho D6 (lệch
khớp tranche, §9b.3) và mọi phép đếm THEO LỆNH THẬT thay vì theo lần chạy.

════ Vì sao tồn tại ════
`decision_log.py` (TD-0144/TD-0201) có cửa ghi hoạt động từ trước, và
`gap_ms.py` (TD-0244) đã nối được loại `DOI_SL`. Nhưng loại NỀN TẢNG nhất
— một sự kiện cho MỖI lần khớp entry — vẫn "0 người gọi sản xuất" (dòng
việc `TD-0239` trong `TASKS.md`): sổ tồn tại, luật đầy đủ, không ai ghi
vào (`TD-0168`, dạng nặng nhất của "thứ được canh không nằm trên đường
chạy").

════ Phạm vi — CHỈ chiều VÀO, không phải cả "vào/ra" ════
Tên loại trong `decision_log.TRUONG_KHOA` là `VAO_RA_LENH` (spec dòng
2644: *"bản ghi vào/ra lệnh"*), nhưng tiêu chí XONG của `TD-0239` chỉ đòi
*"Mỗi TRANCHE khớp sinh đúng một bản ghi"* — và "tranche" trong toàn dự
án luôn nghĩa là một lần ENTRY của DCA (1/2/3), không dùng cho lệnh
thoát. Module này CHỈ sinh bản ghi cho lệnh VÀO khớp. Bản ghi cho lệnh RA
(TP1/TP2/SL/DG6/DG8/force_exit) là phạm vi CHƯA MỞ — để dành một mã việc
riêng, không tự lấn sang ở đây (quy tắc 4: giới hạn phạm vi chỉnh sửa).

════ Vì sao hàm THUẦN, không tự validate rỗng ════
Cùng khuôn `gap_ms.sinh_ban_ghi_doi_sl`: chỉ dựng dict, không kiểm tra
trường rỗng/None — `decision_log.dedup_key()` là ĐIỂM NGHẼN DUY NHẤT mọi
bản ghi phải qua trước khi chạm file (bài học TD-0150: vá rải rác ở
nhiều hàm để lọt qua điểm chưa vá). Validate lặp ở đây sẽ là một nguồn
luật thứ hai, có thể trôi lệch với `TRUONG_KHOA`.

════ Nguồn từng trường (Quy tắc 7 — đã tra `tu-dien-du-lieu.md` TRƯỚC khi
đọc, không suy đoán từ tên) ════
  order_id ← `orders.order_id` (mã sàn cấp — khoá dedup, §8.3)
  ts       ← `orders.order_filled_date` (mốc khớp THẬT, khác order_date)
  price    ← `Order.safe_price` (property Freqtrade, KHÔNG phải cột DB —
             xác nhận bằng đọc mã nguồn `trade_model.py:140-141`; đây
             CHÍNH LÀ biến `exit_rate`/tương đương Freqtrade tự dùng để
             tính profit trong `recalc_trade_from_orders`, không phải
             một cách đọc giá tự nghĩ ra)
  amount   ← `Order.safe_amount_after_fee` (property, `trade_model.py:
             164-165` — khối lượng đã khớp TRỪ phí, đúng biến Freqtrade
             tự dùng cùng chỗ)
  side     ← `orders.ft_order_side` (`trade_model.py:91-92` — 'buy'/
             'sell'; giá trị 'stoploss' không xuất hiện ở đây, đó là
             `DOI_SL`)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

LOAI_VAO_RA_LENH = "VAO_RA_LENH"


def sinh_ban_ghi_vao_lenh(
    *,
    order_id: str,
    ts: datetime,
    trade_id: int,
    pair: str,
    tranche: int,
    side: str,
    price: float,
    amount: float,
    nguon: str,
) -> dict[str, Any]:
    """Sinh MỘT bản ghi Decision Log `VAO_RA_LENH` cho một lần entry khớp.

    :param order_id: `orders.order_id` — khoá dedup (§8.3).
    :param ts: `orders.order_filled_date` — mốc khớp THẬT.
    :param trade_id: `trades.id`.
    :param pair: cặp giao dịch — tham số callback Freqtrade, không phải
        cột DB (Order không có cột `pair` độc lập trong schema đã tra).
    :param tranche: số thứ tự tranche VỪA khớp (1/2/3) — nơi gọi phải
        truyền `trade.nr_of_successful_entries` NGAY SAU khi order này
        khớp, không phải đếm lại từ lịch sử (khác `gap_ms`, nơi phải suy
        ngược vì SL là lệnh riêng biệt không đi cùng nhịp entry).
    :param side: `orders.ft_order_side` — 'buy' hoặc 'sell'.
    :param price: `Order.safe_price`.
    :param amount: `Order.safe_amount_after_fee`.
    :param nguon: `"backtest" | "dry_run" | "live"` — dùng thẳng
        `self.dp.runmode.value` phía chiến lược, KHÔNG suy đoán ở đây
        (TD-0201, `decision_log.NGUON_HOP_LE`).
    """
    return {
        "loai": LOAI_VAO_RA_LENH,
        "nguon": nguon,
        "exchange_order_id": order_id,
        "ts": ts.isoformat(),
        "trade_id": trade_id,
        "pair": pair,
        "tranche": tranche,
        "side": side,
        "price": price,
        "amount": amount,
    }
