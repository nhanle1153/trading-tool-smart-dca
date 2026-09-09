# api-integration-rules.md — Tool D (Smart DCA)

> Bản làm việc, copy từ `template/api-integration-rules.md` (TD-0079). Gate check G1-G4 (Giai đoạn 1
> của quy trình vibe-code) đã xác nhận ✅ **CÓ** ở `back-end-note.md` §0.3: gọi REST/WebSocket Binance,
> dùng SDK ccxt qua Freqtrade, poll dữ liệu OHLCV/OI — bắt buộc áp toàn bộ 12 nguyên tắc R1-R12.
>
> **Phạm vi D0-PRE:** chỉ các endpoint ĐỌC (klines, OI history, exchangeInfo) — dùng cho TD-0080/0082/0083.
> Endpoint ĐẶT LỆNH chỉ dùng từ D3.5 (testnet) trở đi — điền sẵn ở đây vì đây là quyết định nền tảng
> một lần, không phải điền lại mỗi giai đoạn.

## 4.1. Danh sách dịch vụ ngoài

| # | Dịch vụ | Mục đích | Môi trường có sẵn | Tính phí theo call? |
|---|---------|----------|-------------------|---------------------|
| 1 | Binance USDⓈ-M Futures REST — public market data | Tải OHLCV lịch sử, Open Interest lịch sử, metadata sàn (min notional, precision) — dùng ở D0-PRE và mọi giai đoạn backtest | ☐ MOCK ☐ SANDBOX ☑ LIVE (dữ liệu công khai, không có sandbox riêng cho market data) | ☐ Có ☑ Không |
| 2 | Binance USDⓈ-M Futures REST + WebSocket — đặt/sửa/huỷ lệnh, User Data Stream | Thực thi giao dịch thật (tranche, SL, TP) — **chỉ dùng từ D3.5 (testnet) trở đi, KHÔNG dùng ở D0-PRE** | ☑ MOCK (backtest/dry-run) ☑ SANDBOX (testnet, D3.5/D10) ☑ LIVE (D12, vốn nhỏ) | ☐ Có ☑ Không *(miễn phí truy cập API — chi phí thật là phí giao dịch, xem `provider-map.md`)* |

> ⚠️ G2 đã đúng như cảnh báo của template: SDK `ccxt` (Freqtrade dùng nội bộ) gọi mạng ngầm — không
> tự viết HTTP client riêng, nhưng vẫn phải áp R1-R12 vì bản chất vẫn là gọi ra ngoài.

## 4.2. Bảng endpoint

| Endpoint | Method | Idempotent? | Rate limit công bố | Timeout đặt (s) | Được retry? |
|----------|--------|-------------|--------------------|-----------------|-------------|
| `GET /fapi/v1/klines` | GET | ☑ Có | weight 1–5 (theo `limit`), trần 2400 weight/phút/IP | 10 | ☑ Có |
| `GET /futures/data/openInterestHist` | GET | ☑ Có | cùng nhóm weight REST public | 10 | ☑ Có |
| `GET /fapi/v1/exchangeInfo` | GET | ☑ Có | weight ~1 | 10 | ☑ Có |
| `POST /fapi/v1/order` (đặt lệnh, D3.5+) | POST | ☐ Không | order weight riêng, trần lệnh/10s theo cấp tài khoản | 10 | ☐ Không *(R9: cần idempotency key, xem 4.4)* |
| `DELETE /fapi/v1/order` (huỷ lệnh, D3.5+) | DELETE | ☑ Có | cùng nhóm order weight | 10 | ☑ Có *(huỷ một lệnh đã huỷ trả lỗi rõ ràng, không tạo tác dụng phụ)* |
| `PUT /fapi/v1/order` (sửa khối lượng SL, D3.5+) | PUT | ☐ Không | cùng nhóm order weight | 10 | ☐ Không *(R9: cần idempotency key)* |

> Cột `Idempotent?` — endpoint đặt lệnh và sửa lệnh đánh dấu **Không**: gọi lại khi không chắc lệnh
> trước có tới nơi hay không (timeout, mất kết nối) có thể tạo lệnh trùng hoặc sửa hai lần. Freqtrade
> tự sinh `newClientOrderId` làm khoá chống trùng phía client — đây chính là cơ chế R9 đòi hỏi, không
> tự viết thêm lớp idempotency key riêng chồng lên.

## 4.3. Bảng mã lỗi (phục vụ R4)

| Mã lỗi | Nhóm | Hành động |
|--------|------|-----------|
| HTTP 429 (Too Many Requests) | ☑ Retry được | Backoff luỹ tiến, tôn trọng header `Retry-After` nếu có |
| HTTP 418 (IP Auto-Banned) | ☑ Dừng hẳn + alert | Đã bị cấm vì vi phạm 429 lặp lại — retry ngay = kéo dài lệnh cấm. Risk Supervisor phải dừng TOÀN BỘ (§6.6, cùng cấp độ với LIQUIDATED) |
| -1003 (Too many requests — weight limit) | ☑ Retry được | Cùng nhóm 429, backoff luỹ tiến |
| -1015 (Too many new orders) | ☑ Retry được | Backoff luỹ tiến |
| HTTP 5xx (lỗi phía sàn) | ☑ Retry được | Backoff luỹ tiến, tối đa theo R5 |
| -1121 (Invalid symbol) | ☑ Lỗi logic | Không retry — cấu hình sai (pool có mã không tồn tại), dừng và báo |
| -2010 (lệnh sẽ khớp ngay lập tức / không đủ số dư) | ☑ Lỗi logic | Không retry — dấu hiệu định cỡ sai hoặc margin không đủ, phải dừng tranche đó và ghi Decision Log |
| -2011 (Unknown order, huỷ lệnh không tồn tại) | ☑ Lỗi logic | Không retry — lệnh đã khớp/huỷ trước đó, đối chiếu lại trạng thái thay vì lặp lại thao tác |
| -2019 (Margin is insufficient) | ☑ Lỗi logic | Không retry — Risk Supervisor phải chặn TRƯỚC khi tới đây (kiểm tra kết nạp §6.8f), gặp lỗi này nghĩa là có lỗ hổng ở tầng kiểm tra trước |

## 4.4. Ngưỡng cấu hình

| Tham số | Giá trị | Biến ENV |
|---------|---------|----------|
| Rate limit (call/giây) | 0.5/giây tự áp (= 30/phút, `tier_c.api_calls_per_min`, §6.9.5) — thấp hơn nhiều trần thật 2400 weight/phút của Binance | *(không đọc từ ENV — Tầng C, cấm theo N4/0d.4)* |
| N lỗi liên tiếp kích hoạt breaker | ✅ **5** — chủ dự án xác nhận 09/09/2026 (TD-0196) | `TOOLD_BREAKER_THRESHOLD` (vận hành, không phải tham số tín hiệu) |
| Backoff khởi điểm / tối đa (s) | ✅ **1s / 60s, nhân đôi mỗi lần** (1→2→4→…→60, kẹp trần) — chủ dự án xác nhận 09/09/2026 (TD-0196) | `TOOLD_BREAKER_BACKOFF_MAX_S` (khởi điểm cố định 1s, không cần biến riêng) |
| Timeout từng request (s) | 10 | — |
| Timeout tổng vòng lặp (s) | 60 (một chu kỳ poll đầy đủ danh sách pool ~100 mã) | — |
| Số vòng lặp tối đa | Không giới hạn cứng — bounded bởi `api_calls_per_min` × thời gian, không phải đếm vòng | — |
| Hạn mức call/ngày + % cảnh báo | Không có hạn mức ngày (Binance tính theo phút, không theo ngày) — cảnh báo ở 80% trần phút tự áp (24/30) | — |
| Kill switch | `dry_run: true` trong `config/freqtrade/config.json` (đã có, TD-0026) — tắt hoàn toàn mọi lệnh gọi ĐẶT LỆNH mà không cần đổi code | `FREQTRADE__DRY_RUN` (biến vận hành chuẩn của Freqtrade, không phải tham số Tool D) |

> ⚠️ Hai tham số N lỗi liên tiếp kích hoạt breaker và backoff là chi tiết triển khai R3 (Circuit
> breaker) — thuộc loại "chi tiết kỹ thuật nhỏ không ảnh hưởng hành vi hệ thống" theo Nguyên tắc 9,
> KHÔNG phải tham số tín hiệu chiến lược, nên không cần chốt bằng DR và không tính vào N_ĐĂNG_KÝ.
> ✅ **Đã xác nhận 09/09/2026** (OQ-09, TD-0196) — dùng đúng đề xuất ban đầu, không đổi số.

## 5. Bảng nghiệm thu — CHƯA chạy ở D0-PRE

Bảng nghiệm thu Mục 5 (R1-R12, `template/api-integration-rules.md`) chỉ chạy được sau khi có code
gọi mạng thật — D0-PRE chưa viết `api_client`/lớp adapter Binance nào (đúng N2: cấm chạm dữ liệu
trước khi cổng D0-PRE đóng). Sẽ chạy nghiệm thu này ở Khối 8 khi TD-0080 (verify OI) và TD-0083 (chốt
pool) thực sự gọi mạng lần đầu.

## 6. Lịch sử thay đổi

| Phiên bản | Ngày | Thay đổi |
|-----------|------|----------|
| 1.0 | 06/09/2026 | Khởi tạo (TD-0079). Điền Mục 4.1-4.4 cho Binance USDⓈ-M Futures — cả nhóm đọc dữ liệu (D0-PRE) và nhóm đặt lệnh (D3.5+, điền sẵn vì là quyết định nền tảng một lần). Hai ngưỡng breaker/backoff đánh dấu "đề xuất", chưa chốt bằng DR |
| 1.1 | 09/09/2026 | OQ-09 xác nhận (TD-0196): ngưỡng breaker 5 lỗi liên tiếp, backoff 1s→2s→4s→…→60s — giữ đúng số đề xuất ban đầu. Bắt đầu implement `src/tool_d/risk_supervisor.py` (khung THUẦN — phân loại lỗi theo Mục 4.3, state machine circuit breaker, khai lại có chủ đích §6.6(2)). Chưa có tiến trình chạy thật (dry-run/live) — Mục 5 (bảng nghiệm thu) vẫn CHƯA chạy |
