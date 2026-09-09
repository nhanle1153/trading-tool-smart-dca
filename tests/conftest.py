"""TD-0197 — reset trạng thái mạng (breaker + nhịp gọi) của
`tool_d.api_client.binance_public` TRƯỚC MỖI test, toàn bộ suite.

Cần thiết vì TD-0197 nối rate-limit + circuit breaker vào module đó bằng
STATE CẤP MODULE (không phải một client/đối tượng khởi tạo lại mỗi lần
— xem docstring `dat_lai_trang_thai_mang_cho_kiem()`). Không reset thì:
(a) một ca kiểm mô phỏng lỗi 429 nhiều lần sẽ để breaker MỞ, làm ca sau
đó (bất kỳ file nào, không riêng file vừa mô phỏng) bị `BinanceBreakerMoError`
dù không liên quan; (b) `_lan_goi_cuoi_mang_s` còn giá trị từ ca trước sẽ
khiến `_cho_nhip_goi()` gọi `time.sleep()` THẬT (tới 2s ở trần 30/phút)
giữa các test — làm suite chậm và không xác định theo thứ tự chạy.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _reset_trang_thai_mang_binance() -> None:
    from tool_d.api_client.binance_public import dat_lai_trang_thai_mang_cho_kiem

    dat_lai_trang_thai_mang_cho_kiem()
