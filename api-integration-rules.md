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
