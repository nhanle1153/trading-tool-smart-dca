"""Công cụ VẬN HÀNH (ops) — KHÔNG phải logic chiến lược/đo lường.

Khác với phần còn lại của `src/tool_d/` (zone detection, sizing, ledger...),
package này không chạm CALIB/WFO/LOCKBOX và không gọi `measurement_guard()`
— nó giám sát "tiến trình có đang sống/chạy hay không" (TD-0209), không
đánh giá một cấu hình nào. Vì vậy các script trong `entrypoints/` (khoá
cứng 8 file, L-Z36) không áp dụng ở đây — xem docstring `heartbeat_watchdog.py`.
"""
