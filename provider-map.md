# provider-map.md — Tool D (Smart DCA)

> Bản làm việc, copy từ `template/provider-map.md` (TD-0079). Nguồn quyết định: `tool-d-smart-dca.md`
> §0.3 (sàn), §6.6 (Risk Supervisor), §6.9.5 (tier_c.api_calls_per_min). Đây KHÔNG phải một lựa chọn
> mở — spec đặt tên Binance USDⓈ-M Futures xuyên suốt tài liệu; mục này ghi lại lý do và ràng buộc
> kỹ thuật đi kèm, không phải một quyết định còn tranh luận.

| Tác vụ | Provider chính | Provider dự phòng | Input/Output | Chi phí/đơn vị | Rate limit | Lý do chọn |
|---|---|---|---|---|---|---|
| Dữ liệu lịch sử OHLCV (backtest/calib) | Binance USDⓈ-M Futures REST — `GET /fapi/v1/klines` (qua Freqtrade `download-data` / ccxt) | **Không có.** Xem "Vì sao không có dự phòng" bên dưới | JSON: mảng nến `[open_time, O, H, L, C, V, close_time, ...]` | Miễn phí (không tính phí/lệnh gọi) | Weight-based, klines weight 1–5 tuỳ `limit`, trần 2400 weight/phút toàn IP (§6.6 dùng Cấp C = 30 gọi/phút, thấp hơn nhiều để chừa lề cho lệnh giao dịch thật) | Duy nhất khớp với sàn thực thi lệnh — dữ liệu backtest phải cùng nguồn với dữ liệu live để không lệch vi cấu trúc thị trường |
| Open Interest lịch sử | Binance USDⓈ-M Futures REST — `GET /futures/data/openInterestHist` | Không có | JSON: `{symbol, sumOpenInterest, sumOpenInterestValue, timestamp}` | Miễn phí | Cùng nhóm weight với REST public | TD-0080 cần verify độ dài lịch sử thật trả về (nghi vấn ~30 ngày, spec dòng 4457-4460) — ảnh hưởng trực tiếp thiết kế chỉ báo nếu đúng |
| Metadata sàn (min notional, precision, danh sách cặp) | Binance USDⓈ-M Futures REST — `GET /fapi/v1/exchangeInfo` | Không có | JSON: quy tắc lot size, tick size, min notional theo từng symbol | Miễn phí | Weight thấp (~1) | Cần cho TD-0082 (kiểm min notional) và TD-0083 (chốt pool ~100 mã) |
| Đặt/sửa/huỷ lệnh (chỉ D3.5 trở đi — **KHÔNG dùng ở D0-PRE**) | Binance USDⓈ-M Futures REST + User Data Stream (WebSocket), qua Freqtrade exchange abstraction | Không có | JSON lệnh, cập nhật vị thế qua WS | Miễn phí truy cập API; **chi phí thật là phí giao dịch** (maker/taker) + funding — không phải phí gọi API | Order weight riêng, trần lệnh/10s theo cấp tài khoản | Đích đến cuối cùng của toàn bộ pipeline (D12 — vốn nhỏ); TD-0028 đã đọc mã nguồn Freqtrade xác nhận cơ chế huỷ/đặt lại SL khi khối lượng đổi |
| Cảnh báo vận hành — heartbeat/idle tiến trình (TD-0209, D10-D12) | Telegram Bot API — `POST https://api.telegram.org/bot<token>/sendMessage` | **Không có** — kênh DUY NHẤT, chốt qua trao đổi trực tiếp với chủ dự án 13/09/2026 (xem lý do dưới) | Gửi: JSON `{chat_id, text}`. Nhận: `{ok, result}` hoặc `{ok:false, error_code, description}` | Miễn phí (không tính phí/lệnh gọi) | ~30 message/giây/bot toàn cục — không đáng lo vì watchdog chỉ gửi khi CHUYỂN trạng thái (OK→bất thường, bất thường→OK), không gửi mỗi vòng poll | Kênh MỘT CHIỀU (chỉ gửi, không nhận lệnh điều khiển bot) — **độc lập với khối `telegram`/`api_server` của chính Freqtrade**, khối đó vẫn TẮT theo thiết kế D0-PRE (`config/freqtrade/config.json:116`). Watchdog là tiến trình tách riêng, không phải plugin Freqtrade |
| Risk Supervisor đọc margin/vị thế/thanh lý (TD-0241, D11-D12) | Binance USDⓈ-M Futures REST **KÝ** — `GET /fapi/v2/account`, `GET /fapi/v2/positionRisk`, `GET /fapi/v1/forceOrders?autoCloseType=LIQUIDATION` | Không có — cùng lý do hàng OHLCV/order-placement phía trên (đích thực thi duy nhất) | JSON: margin/balance tổng, vị thế + giá thanh lý theo symbol, danh sách lệnh bị thanh lý (rỗng = chưa có) | Miễn phí truy cập API | Cùng ngân sách `tier_c.api_calls_per_min` (Cấp C, §6.6(3)) — đi qua ĐÚNG điểm nghẽn `_goi_json_ky()` trong `api_client/binance_public.py`, không phải đường riêng đứng ngoài breaker/giãn nhịp | Đóng TODO (3) của `risk_supervisor.py` (TD-0196). `autoCloseType=LIQUIDATION` là bộ lọc phía SERVER, xác nhận qua mã nguồn `ccxt` bundled trong image (`DR-D11-03` §2.4), không phải đoán qua trang docs render-JS |
| Risk Supervisor dừng bot khi LIQUIDATED/`dung_han` (TD-0241, D11-D12) | Freqtrade REST API **CỤC BỘ** — `POST http://127.0.0.1:8081/api/v1/stop` (control API của CHÍNH tiến trình Freqtrade, không phải Binance) | Không có — đây là control API của một tiến trình DUY NHẤT trên máy, không có "provider" thứ hai | Gửi: không cần body. Nhận: `{"status": "stopping trader ..."}` hoặc `{"status": "already stopped"}` (idempotent, xác nhận qua `rpc.py:978`, `DR-D11-03` §2.1) | Miễn phí (nội bộ, không qua mạng ngoài) | Không áp `tier_c.api_calls_per_min` — đây KHÔNG phải traffic Binance, và chỉ gọi khi có sự kiện dừng khẩn cấp (R5 bounded retry riêng, `freqtrade_control.py`) | **Single Egress RIÊNG**, tách khỏi `api_client` của Binance (module `api_client/freqtrade_control.py`) — cùng tinh thần Telegram đã tách ở trên. `listen_ip_address` PHẢI `127.0.0.1`, không bao giờ `0.0.0.0`. Chỉ bật qua `-c config/freqtrade/config.risk_supervisor.json` (file phụ, KHÔNG dùng mặc định — xem comment trong chính file đó) |

## Vì sao KHÔNG có provider dự phòng

Khác với các dịch vụ AI/thanh toán thông thường (nơi đổi provider chỉ là đổi lớp adapter), **toàn bộ
spec được xây dựng quanh hành vi cụ thể của Binance**: cơ chế `STOP_MARKET` huỷ+đặt lại (D2a, TD-0028),
không hỗ trợ `closePosition=true` (D2b), ngưỡng đệm thanh lý, cấu trúc funding rate 8 giờ/lần — tất cả
là giả định RIÊNG của Binance Futures, đã verify bằng đọc mã nguồn thật, không phải cấu hình chung
chung. Đổi sang sàn khác (Bybit, OKX...) sẽ đòi verify lại toàn bộ PHẦN 9b (D1-D7) từ đầu, không phải
"đổi 1 dòng config". Đây là quyết định nền tảng khó đảo ngược đúng nghĩa — ghi nhận thẳng, không giả
vờ có dự phòng cho có.

**Telegram (kênh cảnh báo TD-0209)** không có dự phòng vì lý do khác — đây KHÔNG phải hạ tầng thực thi
chiến lược, chỉ là kênh MỘT CHIỀU báo cho người, nên nếu Telegram tự nó lỗi (token sai, sập dịch vụ),
đường lùi là **ghi log cục bộ + thử lại ở lượt poll kế tiếp** (xem `api-integration-rules.md` 4.4),
không phải đổi sang một dịch vụ nhắn tin thứ hai — thêm provider thứ hai cho một cảnh báo phụ trợ là
phình kiến trúc không cần thiết (Nguyên tắc 4).

## Nguyên tắc kiến trúc bắt buộc

- **Single Egress (R1, `api-integration-rules.md`):** mọi lệnh gọi Binance đi qua đúng 1 module
  `api_client` (chưa viết ở D0-PRE — Freqtrade's exchange abstraction đóng vai trò này khi implement
  thật, không tự viết HTTP client riêng chồng lên).
- Freqtrade tự xử lý phần lớn R2 (rate limit), R3 (circuit breaker qua ccxt), R7 (tách môi trường:
  `dry_run`/testnet/live trong `config/freqtrade/config.json`, TD-0026) — KHÔNG tự viết lại các cơ
  chế này, chỉ cấu hình đúng.
- `tier_c.api_calls_per_min: 30` (§6.9.5) là **trần tự áp**, thấp hơn nhiều so với trần thật của
  Binance (2400 weight/phút) — chừa lề an toàn, không phải giới hạn kỹ thuật của sàn.
- **Single Egress cho Telegram là một điểm nghẽn RIÊNG**, tách khỏi `api_client` của Binance (module
  khác, dịch vụ khác, không dùng chung hàm gọi mạng) — mọi lệnh gửi Telegram đi qua đúng 1 hàm.

## Giám sát chi phí

- API market data + đặt lệnh: **miễn phí** — không có "hoá đơn API" để theo dõi.
- Chi phí thật cần giám sát là **phí giao dịch + funding** (đã có cơ chế riêng: DR-013 đơn vị đo
  `pnl_abs`, DG7 funding stop §4c) — không thuộc phạm vi provider-map này.
- Rủi ro thật của tầng API là **bị khoá IP/tài khoản do vượt rate limit**, không phải chi phí tiền —
  giám sát bằng Risk Supervisor (§6.6) đếm số gọi/phút, không phải đếm tiền.
- Ngưỡng cảnh báo: vượt 80% trần tự áp (24/30 gọi/phút) → cảnh báo qua Risk Supervisor. 🔄 TD-0241
  (`DR-D11-03`): tiến trình `ops/risk_supervisor_daemon.py` đã tồn tại và gọi thật (breaker/backoff
  đã có từ TD-0196/TD-0197) — cảnh báo NGƯỠNG 80% (chưa tới mức mở breaker) vẫn CHƯA có, chỉ có hai
  đầu: chạy bình thường và breaker mở hẳn. Ghi nợ, không chặn D11.

## Lịch sử thay đổi Provider

| Tác vụ | Provider cũ | Provider mới | Lý do đổi | Ngày |
|---|---|---|---|---|
| — | — | — | Khởi tạo lần đầu (TD-0079), chưa có thay đổi | 06/09/2026 |
| Cảnh báo vận hành | — (chưa có) | Telegram Bot API | Thêm mới cho TD-0209 (heartbeat/idle) — chủ dự án chốt qua trao đổi trực tiếp 13/09/2026, chưa có dòng code nào | 13/09/2026 |
