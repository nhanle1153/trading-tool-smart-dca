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
| 3 | Telegram Bot API — `sendMessage` | Cảnh báo MỘT CHIỀU khi heartbeat của tiến trình Freqtrade cũ quá ngưỡng, hoặc trạng thái bot khác `RUNNING` kéo dài — TD-0209, dùng từ D10-D12 (dry-run trở đi, watchdog KHÔNG chạy ở D0-PRE vì chưa có tiến trình dài nào để giám sát) | ☐ MOCK ☑ LIVE (Telegram không cấp sandbox riêng cho Bot API — kiểm bằng bot Telegram thật trỏ vào chat thử nghiệm, không phải môi trường giả lập) ☐ SANDBOX | ☐ Có ☑ Không |
| 4 | Binance USDⓈ-M Futures REST **KÝ** — đọc margin/vị thế/thanh lý (`GET /fapi/v2/account`, `/fapi/v2/positionRisk`, `/fapi/v1/forceOrders`) | Risk Supervisor (§6.6, TD-0241) tự đọc trạng thái tài khoản — dùng từ D11-D12, KHÔNG chạy ở D0-PRE/D4 (không có tài khoản live để đọc) | ☑ MOCK (test đơn vị) ☐ SANDBOX (không có testnet cho endpoint này, `DR-D35-01`) ☑ LIVE (D11-D12) | ☐ Có ☑ Không |
| 5 | Freqtrade REST API **CỤC BỘ** — `POST /api/v1/stop` | Risk Supervisor dừng HẲN vòng lặp bot khi `LIQUIDATED`/breaker `dung_han` (TD-0241, `DR-D11-03`) — control API của CHÍNH tiến trình Freqtrade trên máy, KHÔNG phải Binance | ☑ MOCK (test đơn vị) ☑ LIVE (D11-D12, chỉ khi Freqtrade chạy với `-c config/freqtrade/config.risk_supervisor.json`) ☐ SANDBOX | ☐ Có ☑ Không |
| 6 | Binance **kho lưu trữ công khai** `data.binance.vision` (file ZIP tĩnh, không phải REST) | Dữ liệu lịch sử đã đóng: nến 1d theo THÁNG (volume rổ point-in-time, `TD-0231`/`TD-0247`/`TD-0300`/`TD-0307`), dump `aggTrades` theo NGÀY (`TD-0162`, DR-015 bước 2), nến 1d theo NGÀY cho rổ `XAC_NHAN` tại ngày CHỌN (`TD-0391`, `DR-XAC-NHAN-01` §9); liệt kê bucket (`TD-0230`). Chỉ ĐỌC | ☐ MOCK ☐ SANDBOX ☑ LIVE (dữ liệu công khai, không khoá) | ☐ Có ☑ Không |
| 7 | Binance **SAPI KÝ** — `GET /sapi/v1/account/apiRestrictions` (host `api.binance.com`, KHÁC `fapi`) | Máy kiểm bảo mật TÀI KHOẢN PHỤ trước MỖI lần bật bộ chạy D10 (`DR-D10-02` Q3): IP whitelist phải bật, quyền rút / chuyển tiền phải tắt — không thoả ⇒ TỪ CHỐI bật. Gọi MỘT lần mỗi lần khởi động, không nằm trong vòng lặp | ☑ MOCK (test đơn vị) ☐ SANDBOX (không có testnet cho endpoint này) ☑ LIVE (D10+, key tài khoản phụ) | ☐ Có ☑ Không |

> ⚠️ G2 đã đúng như cảnh báo của template: SDK `ccxt` (Freqtrade dùng nội bộ) gọi mạng ngầm — không
> tự viết HTTP client riêng, nhưng vẫn phải áp R1-R12 vì bản chất vẫn là gọi ra ngoài.
> ⚠️ Dịch vụ #3 (Telegram) là gate check RIÊNG, mở lại theo quy tắc 17 khi TD-0209 được nêu (13/09/2026)
> — chủ dự án đã chốt kênh qua trao đổi trực tiếp; provider-map.md đã có dòng tương ứng. Watchdog là
> **tiến trình tách riêng**, không chạy trong tiến trình Freqtrade chính (chốt cùng lúc, lý do: một
> tiến trình đã chết thì không tự báo được chính nó đã chết).

## 4.2. Bảng endpoint

| Endpoint | Method | Idempotent? | Rate limit công bố | Timeout đặt (s) | Được retry? |
|----------|--------|-------------|--------------------|-----------------|-------------|
| `GET /fapi/v1/klines` | GET | ☑ Có | weight 1–5 (theo `limit`), trần 2400 weight/phút/IP | 10 | ☑ Có |
| `GET /futures/data/openInterestHist` | GET | ☑ Có | cùng nhóm weight REST public | 10 | ☑ Có |
| `GET /fapi/v1/exchangeInfo` | GET | ☑ Có | weight ~1 | 10 | ☑ Có |
| `POST /fapi/v1/order` (đặt lệnh, D3.5+) | POST | ☐ Không | order weight riêng, trần lệnh/10s theo cấp tài khoản | 10 | ☐ Không *(R9: cần idempotency key, xem 4.4)* |
| `DELETE /fapi/v1/order` (huỷ lệnh, D3.5+) | DELETE | ☑ Có | cùng nhóm order weight | 10 | ☑ Có *(huỷ một lệnh đã huỷ trả lỗi rõ ràng, không tạo tác dụng phụ)* |
| `PUT /fapi/v1/order` (sửa khối lượng SL, D3.5+) | PUT | ☐ Không | cùng nhóm order weight | 10 | ☐ Không *(R9: cần idempotency key)* |
| `POST /bot<token>/sendMessage` (Telegram, TD-0209) | POST | ☐ Không | ~30 msg/s/bot toàn cục (không dùng gần tới trần — watchdog chỉ gửi khi CHUYỂN trạng thái) | 10 | ☑ Có *(R9: KHÔNG retry nội bộ — một lần thử/vòng poll, vòng poll 60s sau tự thử lại nếu thất bại; xem 4.4b)* |
| `GET /fapi/v2/account`, `GET /fapi/v2/positionRisk` (Risk Supervisor, TD-0241) | GET | ☑ Có | Cùng nhóm weight REST public KÝ, chịu `tier_c.api_calls_per_min` (Cấp C) | 10 | ☑ Có |
| `GET /fapi/v1/forceOrders?autoCloseType=LIQUIDATION` (Risk Supervisor, TD-0241) | GET | ☑ Có | Cùng nhóm weight REST public KÝ | 10 | ☑ Có |
| `POST /api/v1/stop` (Freqtrade cục bộ, TD-0241) | POST | ☑ Có *(xác nhận qua mã nguồn `rpc.py:978` — gọi khi đã `STOPPED` trả `"already stopped"`, không lỗi)* | Không công bố (control API cục bộ, không phải Binance) | 10 | ☑ Có *(R5 bounded — tối đa 5 lần, backoff cố định 2s; 401 KHÔNG retry, xem 4.3)* |
| `GET data.binance.vision/data/futures/um/monthly/klines/<SYM>/1d/<SYM>-1d-<YYYY-MM>.zip` (`doc_quote_volume_1d_thang`) | GET | ☑ Có | Không công bố; KHÔNG áp `tier_c.api_calls_per_min` (trần đó của `fapi.binance.com`) — dùng CHUNG breaker R3 | 60 | ☑ Có *(bên gọi chạy lại; 404 = DỮ KIỆN `NenThangKhongCoError`, không retry, không tính lỗi breaker)* |
| `GET data.binance.vision/data/futures/um/monthly/<loai>/<SYM>/[<khung>/]<file>.zip` (`doc_csv_thang_kho`: nến, mark, `fundingRate`… theo THÁNG, `TD-0247`) | GET | ☑ Có | Như trên | 120 | ☑ Có *(404 = `NenThangKhongCoError`; lỗi khác / zip hỏng / 0 hàng ⇒ `KhoLuuTruError`)* |
| `GET data.binance.vision/data/futures/um/daily/aggTrades/<SYM>/<SYM>-aggTrades-<YYYY-MM-DD>.zip` (`tai_dump_agg_trades`) | GET | ☑ Có | Như trên | 120 | ☑ Có *(có cache đĩa, đổi tên nguyên tử; 404 = `AggTradesNotFoundError`)* |
| `GET data.binance.vision/data/futures/um/daily/klines/<SYM>/1d/<SYM>-1d-<YYYY-MM-DD>.zip` (`TD-0391`, chưa code) | GET | ☑ Có | Như trên | 60 | ☑ Có *(404 = dữ kiện, cùng họ `NenThangKhongCoError` ⇒ `dung_ro_tai_moc` xếp `kho_404`; không đọc ngày HÔM NAY — file ngày chưa đóng)* |
| `GET s3-ap-northeast-1.amazonaws.com/data.binance.vision?prefix=…` (liệt kê bucket S3 đứng sau kho, `liet_ke_kho_luu_tru`) | GET | ☑ Có | Như trên | 30 | ☑ Có *(prefix rỗng bị cấm; lỗi ⇒ `KhoLuuTruError`, không trả rỗng)* |
| `GET /sapi/v1/account/apiRestrictions` (`api.binance.com`, `DR-D10-02` Q3, TD-0384 — chưa code) | GET | ☑ Có | weight 1 theo tài liệu Binance (**chưa verify bằng gọi thật**); gọi một lần/lần khởi động ⇒ không chịu áp lực trần | 10 | ☑ Có *(qua breaker R3 hiện có; hết lượt ⇒ TỪ CHỐI bật D10, không bật mù)* |

> Cột `Idempotent?` — endpoint đặt lệnh và sửa lệnh đánh dấu **Không**: gọi lại khi không chắc lệnh
> trước có tới nơi hay không (timeout, mất kết nối) có thể tạo lệnh trùng hoặc sửa hai lần. Freqtrade
> tự sinh `newClientOrderId` làm khoá chống trùng phía client — đây chính là cơ chế R9 đòi hỏi, không
> tự viết thêm lớp idempotency key riêng chồng lên.
> `sendMessage` cũng **Không** idempotent (gọi lại tạo tin nhắn trùng, không lỗi) — R9 xử bằng
> **chống trùng ở tầng gọi**: chỉ gọi khi trạng thái CHUYỂN (OK→bất thường, bất thường→OK), không gọi
> mỗi lượt poll dù trạng thái không đổi — nên không cần idempotency key phía Telegram.

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
| Telegram 429 (Too Many Requests) | ☑ Retry được | Backoff luỹ tiến, tôn trọng `retry_after` trong body nếu có |
| Telegram 401 (Unauthorized — token sai) | ☑ Lỗi logic | Không retry — token cấu hình sai, dừng watchdog + ghi log cục bộ MỨC CAO NHẤT (đây là ca "kênh báo lỗi tự nó hỏng", không được im lặng) |
| Telegram 400 (Bad Request — chat_id/text sai) | ☑ Lỗi logic | Không retry — lỗi cấu hình, ghi log cục bộ |
| Telegram 5xx / timeout / lỗi kết nối | ☑ Retry được | KHÔNG backoff nội bộ — một lần thử, thất bại thì ghi log cục bộ + giữ nguyên trạng thái "chưa báo", vòng poll 60s kế tiếp tự thử lại (4.4b) |
| Freqtrade control API 401 (Unauthorized — sai username/password, TD-0241) | ☑ Lỗi logic | Không retry — lỗi CẤU HÌNH cục bộ (`.env` sai), raise `FreqtradeAuthError` ngay ở lần gọi đầu tiên |
| Freqtrade control API 5xx / timeout / lỗi kết nối (TD-0241) | ☑ Retry được | Backoff CỐ ĐỊNH 2s (không luỹ tiến — sự kiện dừng khẩn cấp cần thử nhanh, không phải tiết kiệm tài nguyên), tối đa 5 lần rồi RAISE (không nuốt) |
| `apiRestrictions` -2014 / -2015 (API key sai định dạng / key sai, IP không trong whitelist, hoặc thiếu quyền) | ☑ Lỗi logic | Không retry — TỪ CHỐI bật D10 + log mức cao nhất. Ghi chú: gọi từ IP ngoài whitelist mà nhận -2015 là whitelist ĐANG hoạt động, nhưng bộ chạy vẫn phải dừng vì không đọc được cấu hình tài khoản (`DR-D10-02` Q3) |
| `apiRestrictions` -1021 (timestamp ngoài `recvWindow`) | ☑ Lỗi logic | Không retry — lệch đồng hồ máy chạy, lỗi CẤU HÌNH cục bộ; TỪ CHỐI bật D10 |
| `apiRestrictions` 5xx / timeout / lỗi kết nối | ☑ Retry được | Qua breaker R3 hiện có; hết lượt hoặc breaker mở ⇒ TỪ CHỐI bật D10 (fail-closed: không đọc được thì coi như KHÔNG an toàn) |
| `apiRestrictions` trả 200 nhưng thiếu trường cần kiểm | ☑ Lỗi logic | TỪ CHỐI bật D10 (N6 — không đoán giá trị mặc định cho một cờ bảo mật) |

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

### 4.4b. Ngưỡng riêng cho watchdog heartbeat (TD-0209) — ✅ dùng nguyên đề xuất (14/09/2026)

Cùng loại quyết định với OQ-09 (chi tiết triển khai, không phải tham số tín hiệu — Nguyên tắc 9), nên
đề xuất số cụ thể kèm lý do thay vì hỏi mở, theo đúng khuôn đã dùng cho breaker/backoff. Chủ dự án gõ
"bắt đầu code" không kèm điều chỉnh nào — coi là xác nhận dùng nguyên bảng dưới (trừ một chỗ ĐỔI lúc
code, ghi tại chỗ, xem dòng "Số lần retry").

| Tham số | Đề xuất | Lý do |
|---|---|---|
| Chu kỳ ghi heartbeat | Mỗi vòng lặp bot — hiện `internals.process_throttle_secs = 5` giây (`config/freqtrade/config.json:125`) | Ghi file cục bộ, không phải lệnh gọi mạng — chi phí gần như 0, tận dụng đúng nhịp đã có sẵn |
| Nội dung heartbeat | `{thoi_diem, trang_thai, trang_thai_tu_luc}` (ba trường, không phải hai — thêm `trang_thai_tu_luc` lúc code) — `trang_thai` đọc từ trạng thái nội bộ Freqtrade (RUNNING/STOPPED/...) | Tên việc TD-0209 nói rõ **hai** thứ cần bắt: tiến trình CHẾT/TREO (`thoi_diem` cũ) VÀ tiến trình còn sống nhưng bot đã dừng (`trang_thai` khác RUNNING). Vế thứ hai cần biết trạng thái đó đã kéo dài BAO LÂU, không chỉ ĐANG là gì — nếu không có `trang_thai_tu_luc` thì watchdog phải tự nhớ lịch sử giữa các lần poll (mất khi restart); có trường này thì mỗi lần đọc heartbeat là ĐỦ để đánh giá, không cần trạng thái riêng của watchdog cho phần này (`src/tool_d/ops/heartbeat.py`) |
| Ngưỡng cảnh báo — heartbeat cũ quá (tiến trình chết/treo) | **300 giây (5 phút)** | = 60× chu kỳ ghi; gấp **5 lần** trần backoff breaker (60s, TD-0196) và gấp **~27 lần** độ trễ lạnh tệ nhất từng đo (11s, TD-0116) — đủ lớn để không báo giả vì một vòng lặp chậm bất thường, đủ nhỏ để không bỏ lỡ một ca chết thật hàng giờ liền |
| Ngưỡng cảnh báo — `state != RUNNING` kéo dài | **300 giây (5 phút)**, cùng số với trên | Đủ thời gian cho một thao tác dừng CÓ CHỦ ĐÍCH ngắn (vd restart thủ công) không bị báo nhầm, vẫn đủ nhanh để bắt ca dừng ngoài ý muốn trong cùng một ca làm việc |
| Chu kỳ watchdog kiểm tra file | 60 giây | Đủ nhỏ so với ngưỡng 300s (thêm tối đa 60s độ trễ phát hiện); watchdog không gọi Binance nên không cạnh tranh trần API |
| Số lần retry gửi Telegram trước khi ghi log cục bộ | ~~3 lần, backoff 2s→4s→8s~~ → **ĐỔI lúc code (14/09/2026): MỘT lần thử/vòng poll, không backoff nội bộ** | Đề xuất ban đầu tưởng tượng Telegram được gọi liên tục như Binance (cần backoff riêng); thực ra watchdog CHỈ gọi khi CHUYỂN trạng thái, và đã có chu kỳ poll 60s làm cơ chế thử-lại-tự-nhiên — thêm backoff nội bộ là một tầng lặp lại của chính chu kỳ poll (Nguyên tắc 4, tránh trùng cơ chế). Gửi thất bại → GIỮ NGUYÊN trạng thái "chưa báo", vòng poll kế tiếp tự thử lại; không mất bằng chứng vì `KetQuaGuiTelegram.thanh_cong=False` được trả về cho tầng gọi ghi log (không nuốt, MT-16 vii) — xem `src/tool_d/ops/heartbeat_watchdog.py::chay_mot_vong` |
| Chống spam | Chỉ gửi khi trạng thái CHUYỂN (OK→bất thường, bất thường→OK) | Không gửi lặp lại mỗi lượt poll trong khi tình trạng không đổi; gửi thêm đúng 1 tin khi phục hồi để người nhận biết đã hết |
| Secret | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` qua ENV, thêm vào `.env.example` (không có giá trị thật) | Cùng cơ chế `BINANCE_API_KEY`/`SECRET` đã có (TD-0242) — tham số VẬN HÀNH, không qua `tool_d_config.yaml` (N4) |
| Vị trí module watchdog | Ngoài `entrypoints/` (không phải E9) | Không sinh "file kết quả" đo lường, không chạm CALIB/WFO/LOCKBOX/`measurement_guard()` — không thuộc phạm vi khoá 8 file của L-Z36 (spec dòng 664, 671-674: chỉ cấm entrypoint sinh file kết quả nằm ngoài danh sách) |
| Cơ chế khởi chạy watchdog thật trên máy | Chưa chốt — quyết khi tới D11 setup thật | Cùng khuôn "hàm thuần trước, nối vào tiến trình thật là việc SAU" đã dùng ở `risk_supervisor.py` (TD-0196) và `validate_credentials_for_live()` (TD-0242) — TODO (2) còn treo từ TD-0196 |

**✅ Xác nhận (14/09/2026):** tầng thuần đã dựng — `src/tool_d/ops/heartbeat.py` (ghi/đọc heartbeat,
tri-state N6), `src/tool_d/ops/telegram_client.py` (single-egress R1, dùng NHÃN lỗi của
`risk_supervisor` chứ KHÔNG dùng lại state machine breaker — lý do ở docstring đầu file),
`src/tool_d/ops/heartbeat_watchdog.py` (đánh giá + chống spam + `chay_mot_vong()`). 56 test, Docker
(N7): `docker compose -f docker/docker-compose.yml run --rm tests -q tests/unit/test_ops_heartbeat.py
tests/unit/test_ops_telegram_client.py tests/unit/test_ops_heartbeat_watchdog.py` → **56 passed**.
Kiểm-có-răng: phá `quyet_dinh_loai_tin()` (bỏ hai nhánh CHUYỂN trạng thái) → đúng 3 ca đỏ, đúng các ca
canh cơ chế chống spam/phục hồi — không phải phần còn lại của suite. **CHƯA nối vào Freqtrade/launcher
thật** (D10-D12 chưa mở) — hai TODO cuối `heartbeat_watchdog.py` (cơ chế khởi chạy trên máy; xác nhận
Freqtrade có gọi vòng lặp worker ở CẢ hai trạng thái RUNNING/STOPPED hay chỉ RUNNING, chưa đọc mã
nguồn cho câu này — rule 6, không đoán).

### 4.4c. Máy kiểm bảo mật tài khoản phụ D10 — dịch vụ #7 (`DR-D10-02` Q3, chốt 25/09/2026, chưa code)

Bảng quyết định trên JSON trả về. Tên trường lấy theo tài liệu Binance, **CHƯA verify bằng gọi thật** — việc đầu tiên
khi code (`TD-0384`) là gọi thật MỘT lần bằng key tài khoản phụ, đối chiếu tên + kiểu trường, rồi mới viết bảng này thành mã.

| Trường | Điều kiện được bật D10 | Lý do |
|---|---|---|
| `ipRestrict` | phải `true` | IP whitelist tắt ⇒ lộ key là mất quyền điều khiển từ bất kỳ đâu (`DR-D11-01` §3) |
| `enableWithdrawals` | phải `false` | Key D10 chỉ cần giao dịch futures; quyền rút là rủi ro không có lợi ích |
| `enableInternalTransfer` | phải `false` | Cùng lý do; `DR-D11-01` §3 đòi tắt Universal Transfer |
| `permitsUniversalTransfer` | phải `false` | Như trên |
| `enableFutures` | phải `true` | Không có quyền futures thì bộ chạy không đặt được lệnh — báo sớm thay vì lỗi giữa chừng |
| Thiếu bất kỳ trường nào ở trên | TỪ CHỐI | N6: không đoán mặc định cho một cờ bảo mật |

Áp R1–R12 cho endpoint này:

| R | Cách áp |
|---|---|
| R1 single egress | Đi qua `_goi_json_ky(path, base_url=SPOT_BASE_URL)` sẵn có ở `src/tool_d/api_client/binance_public.py` — KHÔNG dựng module ký thứ hai. Khi code phải sửa chú thích `SPOT_BASE_URL` (hôm nay ghi *chỉ dùng cho phép đo latency*) |
| R2 rate limit | Chung `_cho_nhip_goi()`; một lần gọi/lần khởi động nên không đáng kể |
| R3 circuit breaker | Chung breaker của `binance_public.py`; breaker mở ⇒ TỪ CHỐI bật |
| R4 phân biệt mã lỗi | Bốn dòng `apiRestrictions` ở 4.3 |
| R5 bounded loop | Không có vòng lặp — một lần gọi, thử lại tối đa theo breaker |
| R6 kill switch | Không bật D10 (Q6 bật bằng tay, không tự khởi động lại) |
| R7 tách môi trường | Key RIÊNG của tài khoản phụ, không dùng chung key nào khác; dry-run không gọi endpoint này |
| R8 log dedup | Một dòng log mỗi lần khởi động, không lặp |
| R9 idempotency | GET chỉ đọc, idempotent tự nhiên |
| R10 secret | Key/secret tài khoản phụ qua biến môi trường, file `.env.*` đã `.gitignore`; không in giá trị ra log hay kết quả lệnh (bài học 24/09, `TD-0393`) |
| R11 timeout | 10 s, như mọi endpoint Binance khác |
| R12 quota | Không có hạn mức ngày; weight 1 so với trần phút |

## 5. Bảng nghiệm thu — TD-0197, 09/09/2026

Chạy lần đầu sau khi TD-0197 nối R2/R3 vào `src/tool_d/api_client/binance_public.py` (đã có gọi
mạng thật từ TD-0080/82/83/84/116/162). Reviewer chạy trong **context sạch** (subagent riêng, chỉ
đọc code + Mục 4, không đọc lịch sử chat/thiết kế — đúng rule 18). Sau khi reviewer trả 2 FAIL 🔴
(R5, R10), builder vá tại chỗ — hai dòng đó đánh dấu **PASS (đã vá sau khi nghiệm thu, CHƯA qua
nghiệm thu clean-context lần hai)**, phân biệt với các dòng PASS nguyên bản của reviewer.

| Mã | Kiểm | Mức | Kết quả | Bằng chứng |
|----|------|-----|---------|------------|
| R1 | Số file gọi HTTP trực tiếp = 1 | 🔴 | PASS | Grep toàn `src/`+`entrypoints/` chỉ khớp `src/tool_d/api_client/binance_public.py` |
| R2 | Có limiter + vượt trần thì CHỜ (không skip) | 🔴 | PASS | `_tran_goi_theo_phut()` đọc `tier_c.api_calls_per_min` qua `resolve()` (`binance_public.py:81-88`); `_cho_nhip_goi()` (dòng 107-114) `time.sleep()` rồi VẪN gọi tiếp, không skip |
| R3 | Có ngưỡng N + backoff tăng dần + max | 🔴 | PASS | `risk_supervisor.py`: `NGUONG_BREAKER_MAC_DINH=5`, `BACKOFF_KHOI_DIEM_S=1.0`/`BACKOFF_TOI_DA_S=60.0` (dòng 47-49), `_backoff_ke_tiep()` nhân đôi kẹp trần (dòng 152-154), nối qua `_kiem_tra_breaker()` (`binance_public.py:91-104`) |
| R4 | Bảng mã lỗi ≥ 3 nhóm, xử lý tách nhánh | 🔴 | PASS | `phan_loai_ma_loi()` trả 4 nhãn (`risk_supervisor.py:98-121`), `ghi_nhan_ket_qua()` xử khác nhau từng nhóm (dòng 178-198) |
| R5 | Mọi vòng lặp có max vòng + timeout tổng | 🔴 | **PASS (đã vá)** | Reviewer FAIL ban đầu: `latency_samples_ms()` không trần `n`, không hạn chót tổng. Vá: `MAX_MAU_LATENCY=200` (`binance_public.py:59`) + `han_chot_s = time.monotonic() + n*timeout`, kiểm mỗi vòng, raise nếu vượt — không trả kết quả một phần (dòng 267-268, 286-291). Test: `test_n_vuot_tran_thi_raise_khong_goi_mang`, `test_vuot_han_chot_tong_thi_dung_khong_tra_ket_qua_mot_phan` |
| R6 | Có ENV kill switch | 🟡 | FAIL | `binance_public.py`/`risk_supervisor.py` không tự kiểm ENV kill switch nào trước khi gọi mạng đọc dữ liệu công khai (`dry_run` là của engine đặt lệnh Freqtrade, khác phạm vi) — ghi tech-debt, xem `TASKS.md` TD-0197 |
| R7 | Có 3 môi trường, mặc định MOCK | 🔴 | N/A (giai đoạn hiện tại) | Chỉ endpoint đọc công khai, không có sandbox cho market data (docstring dòng 12-20). Endpoint đặt lệnh chưa có code — **phải nghiệm thu lại từ đầu ở D3.5** khi viết code thật, không coi N/A hôm nay là còn hiệu lực |
| R8 | Log gộp lỗi lặp + summary định kỳ | 🟡 | FAIL | Không có `logging`/`print` nào trong `binance_public.py`/`risk_supervisor.py` — ghi tech-debt |
| R9 | Cờ idempotent; non-idempotent có khoá chống trùng | 🔴 | PASS (phạm vi hiện tại) | Mục 4.2 đủ cờ; 5 endpoint GET đã có code đều idempotent; 3 endpoint đặt/sửa/huỷ lệnh chưa có code — **nghiệm thu lại ở D3.5** |
| R10 | Không secret trong source, .gitignore đúng, không log secret | 🔴 | **PASS (đã vá)** | Reviewer FAIL ban đầu: thiếu `.env.example` dù `.env.binance` (giá trị thật, đã gitignore đúng) tồn tại ở gốc repo. Vá: tạo `.env.example` (chỉ tên biến `BINANCE_API_KEY`/`BINANCE_API_SECRET`, `.gitignore:22` đã có `!.env.example`) |
| R11 | Timeout tường minh từng request | 🔴 | PASS | `DEFAULT_TIMEOUT_S=10.0`, mọi hàm truyền `timeout=` tường minh vào `urlopen`/`HTTPSConnection` |
| R12 | Bộ đếm call + ngưỡng cảnh báo | 🟡 | FAIL | Mục 4.4 khai "cảnh báo ở 80% trần" nhưng không có bộ đếm/cảnh báo nào trong code — ghi tech-debt |

**Kết luận:** 0 dòng FAIL ở mức 🔴 (điều kiện qua gate, template Mục 5) — **QUA GATE**. Ba dòng 🟡 FAIL
(R6/R8/R12) ghi `tech-debt` vào `TASKS.md` (TD-0197), không chặn. R7/R9 giữ N/A/PASS **có điều kiện**,
bắt buộc nghiệm thu lại trong context sạch riêng khi D3.5 viết code đặt lệnh thật.

## 6. Lịch sử thay đổi

| Phiên bản | Ngày | Thay đổi |
|-----------|------|----------|
| 1.0 | 06/09/2026 | Khởi tạo (TD-0079). Điền Mục 4.1-4.4 cho Binance USDⓈ-M Futures — cả nhóm đọc dữ liệu (D0-PRE) và nhóm đặt lệnh (D3.5+, điền sẵn vì là quyết định nền tảng một lần). Hai ngưỡng breaker/backoff đánh dấu "đề xuất", chưa chốt bằng DR |
| 1.1 | 09/09/2026 | OQ-09 xác nhận (TD-0196): ngưỡng breaker 5 lỗi liên tiếp, backoff 1s→2s→4s→…→60s — giữ đúng số đề xuất ban đầu. Bắt đầu implement `src/tool_d/risk_supervisor.py` (khung THUẦN — phân loại lỗi theo Mục 4.3, state machine circuit breaker, khai lại có chủ đích §6.6(2)). Chưa có tiến trình chạy thật (dry-run/live) — Mục 5 (bảng nghiệm thu) vẫn CHƯA chạy |
| 1.2 | 09/09/2026 | TD-0197: nối R2 (rate limit) + R3 (circuit breaker) vào `binance_public.py`. Chạy Bảng nghiệm thu Mục 5 lần đầu (reviewer context sạch) — 2 FAIL 🔴 (R5, R10) đã vá; 3 FAIL 🟡 (R6, R8, R12) ghi tech-debt vào `TASKS.md`, không chặn gate. R7/R9 N/A/PASS có điều kiện, chờ nghiệm thu lại ở D3.5 |
| 1.3 | 13/09/2026 | TD-0209 (gate check, chưa có dòng code): thêm dịch vụ #3 Telegram Bot API vào Mục 4.1-4.3 (chủ dự án chốt kênh + cách phát hiện qua trao đổi trực tiếp). Thêm Mục 4.4b — 9 tham số ĐỀ XUẤT (ngưỡng heartbeat, chu kỳ watchdog, retry, vị trí module...), CHỜ chủ dự án xác nhận trước khi "bắt đầu code" theo quy tắc 17. `provider-map.md` đã có dòng tương ứng |
| 1.4 | 14/09/2026 | TD-0209: "bắt đầu code" — dựng tầng thuần (`src/tool_d/ops/{heartbeat,telegram_client,heartbeat_watchdog}.py`), 56 test Docker. Đổi 1 tham số lúc code (retry Telegram: bỏ backoff nội bộ 3 lần, dùng chu kỳ poll 60s làm cơ chế thử lại — ghi tại chỗ ở 4.4b, không xoá đề xuất cũ). Chưa nối vào Freqtrade/launcher thật |
| 1.5 | 25/09/2026 | Khai bù dịch vụ #6 `data.binance.vision` vào Mục 4.1–4.2 (lệnh "chuẩn hóa và lưu", phiên mã `143375ad`). Bốn đường đọc đã dùng từ `TD-0162`/`TD-0230`/`TD-0231`/`TD-0247` mà **chưa từng được khai** (nợ cũ, phát hiện khi chuẩn bị `TD-0391`) + đường nến 1d theo NGÀY mới cho rổ `XAC_NHAN` (`DR-XAC-NHAN-01` §9) — khai TRƯỚC khi code theo quy tắc 17. Không đổi dòng cũ nào; R1 giữ nguyên: mọi đường nằm trong `src/tool_d/api_client/binance_public.py` |
| 1.6 | 25/09/2026 | Thêm dịch vụ **#7** Binance SAPI ký `GET /sapi/v1/account/apiRestrictions` vào Mục 4.1–4.3 + mục **4.4c** (bảng quyết định + R1–R12) cho máy kiểm bảo mật tài khoản phụ D10 (`DR-D10-02` Q3, chốt `5bb2b58`). Lệnh "chuẩn hóa và lưu" 25/09/2026, phiên mã `dd89043d`. Chỉ THÊM, không sửa/xoá dòng nào có sẵn. Hoàn tất điều kiện quy tắc 17 cho phần này TRƯỚC "bắt đầu code" `TD-0384`. Tên trường trả về CHƯA verify bằng gọi thật |
