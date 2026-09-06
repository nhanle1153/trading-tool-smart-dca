"""Điểm gọi mạng — R1 Single Egress (`api-integration-rules.md`, TD-0079).

binance_public.py — các endpoint ĐỌC công khai của Binance USDⓈ-M Futures
(không cần API key). Dùng cho TD-0080 (probe độ phủ OI), TD-0082 (min
notional), TD-0083 (chốt pool) — mọi lệnh gọi ĐỌC dữ liệu sàn đi qua đây,
không gọi thẳng `urllib`/`requests` ở nơi khác.

Endpoint ĐẶT LỆNH (private, cần API key) chưa viết — chỉ dùng từ D3.5
(testnet) trở đi, ngoài phạm vi D0-PRE.
"""
