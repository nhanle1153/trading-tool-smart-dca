"""DG7 — Funding Stop, thuộc nhóm ĐÓNG VỊ THẾ (§4c, TD-0122).

Kiểm tra LIÊN TỤC sau khi tranche 1 khớp, tại mỗi mốc funding 8h:
`funding_paid_cumulative(từ tranche 1) ≥ threshold_frac × R_eff_plan`
→ đóng TOÀN BỘ vị thế bằng MARKET, tag `FUNDING_STOP`.

🔴 ÁP DỤNG KHÔNG ĐIỀU KIỆN, cùng lý do với DG8 (§4b.2) — `is_funding_stop_triggered()`
CỐ Ý không nhận tham số lãi/TP1/`trend_dir`.

🔴 NGUỒN DỮ LIỆU (LD-14, §4c.2) — Freqtrade TỰ tích luỹ `trade.funding_fees`
native ở cả backtest lẫn live, quy ước ÂM = đã trả. KHÔNG tự xây pipeline
tích luỹ song song (LD-09: không tạo nguồn sự thật thứ hai). Công thức
`-trade.funding_fees` đã đúng cho CẢ Long lẫn Short — Freqtrade tự tính
dấu funding theo hướng lệnh, không cần code này phân biệt lại.

`R_eff_plan` PHẢI là giá trị ĐÓNG BĂNG tại thời điểm lập kế hoạch (D0.5,
3 tranche đầy đủ) — người gọi tự giữ giá trị đó cố định, hàm này không
có trạng thái nên không thể tự vô tình tính lại theo `p_avg` hiện tại.
"""

from __future__ import annotations


def funding_paid_cumulative(trade_funding_fees: float) -> float:
    """§4c.2 — quy ước Freqtrade: ÂM nghĩa là đã trả. Đảo dấu để có
    một con số "đã trả tích luỹ" dương khi thật sự tốn phí, âm (không
    bao giờ kích hoạt DG7) khi ròng lại NHẬN funding."""
    return -trade_funding_fees


def is_funding_stop_triggered(
    *, funding_paid_cumulative: float, r_eff_plan: float, threshold_frac: float
) -> bool:
    """DG7 — True khi chi phí funding tích luỹ đã ăn hết `threshold_frac`
    phần rủi ro kế hoạch. KHÔNG kiểm bất kỳ điều kiện nào khác."""
    return funding_paid_cumulative >= threshold_frac * r_eff_plan
