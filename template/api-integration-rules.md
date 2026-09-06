# Module: Quy tắc tích hợp API bên ngoài

> **Loại:** Module có điều kiện (conditional module)
> **Vị trí:** `/templates/api-integration-rules.md` — bản gốc chỉ đọc
> **Phiên bản:** 1.0
> **Áp dụng ở:** Stage kiến trúc (khai báo) + Stage review (nghiệm thu)

---

## 0. GATE CHECK — Có cần module này không?

Trả lời trước khi đọc tiếp. Chỉ cần **một** câu trả lời `CÓ` là bắt buộc áp dụng toàn bộ module.

| # | Câu hỏi | Trả lời |
|---|---------|---------|
| G1 | Dự án có gọi HTTP/HTTPS tới bất kỳ dịch vụ nào ngoài chính nó không? | ☐ Có ☐ Không |
| G2 | Có dùng SDK của bên thứ ba mà bên trong nó gọi mạng không? (Firebase, Supabase, Stripe, OpenAI…) | ☐ Có ☐ Không |
| G3 | Có webhook, cron job, hoặc worker chạy nền gọi ra ngoài không? | ☐ Có ☐ Không |
| G4 | Có scrape, crawl, hoặc poll dữ liệu từ nguồn ngoài không? | ☐ Có ☐ Không |

- **Tất cả `Không`** → Bỏ qua module này. Ghi vào tài liệu stage kiến trúc: `API Module: N/A`.
- **Có ít nhất một `Có`** → Bắt buộc hoàn thành Mục 2, 3, 4 trước khi viết dòng code đầu tiên.

> ⚠️ G2 là câu dễ trả lời sai nhất. Rất nhiều dự án tưởng "không gọi API" nhưng thực ra SDK đang gọi mạng ngầm.

---

## 1. Mức độ nghiêm trọng

| Mức | Ý nghĩa | Hành động khi vi phạm |
|-----|---------|----------------------|
| 🔴 **Blocker** | Không được merge, không được deploy | Reviewer trả lại, Builder sửa và nộp lại |
| 🟡 **Warning** | Được merge nhưng phải ghi nợ kỹ thuật | Ghi vào `TASKS.md` với nhãn `tech-debt` |

---

## 2. Nguyên tắc bắt buộc

### Nhóm A — Kiến trúc gọi ra ngoài

#### R1 — Single Egress 🔴 Blocker
M��i call ra ngoài đi qua đúng **1 module** (`api_client`). Không gọi rải rác.

**Lý do:** Không có một cửa duy nhất thì R2–R12 không thể áp dụng được. Đây là rule nền — hỏng R1 thì cả module này vô nghĩa.

**Câu hỏi kiểm:** Đếm số file chứa lệnh gọi HTTP trực tiếp (`fetch`, `axios`, `requests`, `http.Client`, `curl`…). Nếu **> 1** → FAIL, liệt kê đầy đủ đường dẫn file vi phạm.

---

#### R2 — Hard rate limit 🔴 Blocker
Limiter cứng ở tầng client; vượt thì **chờ**, không **bỏ qua**.

**Lý do:** Bỏ qua call khi vượt limit = mất dữ liệu âm thầm, không có lỗi để phát hiện.

**Câu hỏi kiểm:**
1. Có biến cấu hình giới hạn số call/đơn vị thời gian không? Không có → FAIL.
2. Khi chạm giới hạn, code đi vào nhánh **chờ** hay nhánh **return/skip**? Nếu là skip → FAIL.

---

#### R3 — Circuit breaker 🔴 Blocker
N lỗi liên tiếp → ngừng gọi, backoff lũy tiến.

**Lý do:** Không có breaker thì một sự cố phía đối tác biến thành vòng lặp đốt quota của bạn.

**Câu hỏi kiểm:**
1. Có biến ngưỡng N (số lỗi liên tiếp) không? Không có → FAIL.
2. Khoảng chờ giữa các lần thử có tăng dần không? Nếu cố định → FAIL.
3. Có ngưỡng chờ tối đa (max backoff) không? Không có → FAIL.

---

#### R4 — Phân biệt mã lỗi 🔴 Blocker
M� "quá tải" (backoff & retry) ≠ mã "đã bị ban" (dừng hẳn, alert, **không** retry).

**Lý do:** Retry khi đã bị ban làm ban vĩnh viễn thay vì tạm thời.

**Câu hỏi kiểm:** Có bảng ánh xạ mã lỗi → hành động không? Bảng phải phân biệt tối thiểu 3 nhóm: **retry được** / **dừng hẳn + alert** / **lỗi logic không retry**. Thiếu bảng, hoặc gộp tất cả lỗi thành một nhánh xử lý chung → FAIL.

---

#### R5 — Bounded loop 🔴 Blocker
M��i vòng lặp gọi API có giới hạn số vòng **và** timeout tổng.

**Câu hỏi kiểm:** Với mỗi vòng lặp có chứa call API: có biến đếm số vòng tối đa không, và có mốc thời gian dừng không? Thiếu **một trong hai** → FAIL.

---

#### R6 — Kill switch 🟡 Warning
Biến ENV tắt toàn bộ call mà không cần deploy lại.

**Câu hỏi kiểm:** Có biến ENV dạng `API_ENABLED` (hoặc tương đương) được kiểm tra bên trong `api_client` không? Không có → WARNING.

---

#### R7 — Tách môi trường 🔴 Blocker
MOCK / SANDBOX / LIVE. Dev và test **không bao giờ** dùng IP hoặc key của production.

**Câu hỏi kiểm:**
1. Có biến ENV chọn môi trường với đủ 3 giá trị không? Thiếu → FAIL.
2. Giá trị mặc định khi thiếu cấu hình là gì? Nếu mặc định rơi vào LIVE → FAIL. Mặc định **phải** là MOCK.

---

#### R8 — Log dedup + heartbeat 🟡 Warning
Lỗi lặp gộp thành 1 dòng kèm bộ đếm; 1 dòng summary mỗi 60s.

**Lý do:** Log nổ không phải vấn đề dung lượng — nó che lấp lỗi thật khi bạn debug.

**Câu hỏi kiểm:**
1. Lỗi giống nhau lặp lại có bị gộp kèm số đếm không?
2. Có dòng summary định kỳ (số call, số lỗi, độ trễ trung bình) không?
Thiếu một trong hai → WARNING.

> **Ghi chú:** Cân nhắc nâng R8 lên Blocker nếu dự án chạy nền không có người giám sát trực tiếp.

---

### Nhóm B — Bổ sung v1.0

#### R9 — Idempotency & điều kiện được retry 🔴 Blocker
Chỉ được retry call **idempotent**. Call không idempotent muốn retry thì bắt buộc có khóa chống trùng (idempotency key / request ID) do phía gọi sinh ra.

**Lý do:** R3 và R4 cho phép retry nhưng không nói *khi nào được phép*. Retry một call tạo bản ghi = tạo bản ghi trùng. Đây là lỗi tốn tiền thật, không phải lỗi kỹ thuật thuần — và nó không báo lỗi, chỉ âm thầm nhân đôi dữ liệu.

**Câu hỏi kiểm:**
1. Mỗi endpoint được gọi có được đánh dấu `idempotent: có/không` trong bảng khai báo (Mục 4) không? Thiếu → FAIL.
2. Với endpoint đánh dấu `không`: code có sinh khóa chống trùng trước khi gửi không? Không có → FAIL.
3. Endpoint đánh dấu `không` và **không** có khóa chống trùng mà vẫn nằm trong nhánh retry của R3 → FAIL.

---

#### R10 — Quản lý secret 🔴 Blocker
Key/token đọc từ ENV. Không hardcode, không commit, không log ra.

**Lý do:** R7 tách môi trường nhưng không nói key nằm ở đâu. Tách môi trường mà key vẫn nằm trong source code thì mới giải quyết được nửa vấn đề.

**Câu hỏi kiểm:**
1. Có chuỗi nào trông giống key/token nằm trực tiếp trong source không? Có → FAIL, liệt kê vị trí.
2. File chứa biến môi trường có nằm trong `.gitignore` không? Không → FAIL.
3. Có file mẫu (`.env.example`) chỉ chứa tên biến, không chứa giá trị thật không? Không → FAIL.
4. Có chỗ nào log ra toàn bộ header hoặc toàn bộ object cấu hình không? Có → FAIL (rò key qua log).

---

#### R11 — Timeout từng request 🔴 Blocker
M��i call đơn lẻ có timeout riêng, độc lập với timeout tổng của R5.

**Lý do:** R5 chỉ chặn ở mức vòng lặp. Một request treo vô hạn ngay vòng đầu vẫn lọt qua R5 và làm treo cả tiến trình.

**Câu hỏi kiểm:** Trong `api_client`, mỗi call có tham số timeout được set tường minh không? Nếu dựa vào timeout mặc định của thư viện → FAIL (mặc định của nhiều thư viện là *vô hạn*).

---

#### R12 — Bộ đếm quota & chi phí
**🔴 Blocker** nếu API tính phí theo số call hoặc có hạn mức cứng.
**🟡 Warning** nếu API miễn phí và không giới hạn.

**Lý do:** Số call API là tiền. Không có bộ đếm thì một vòng lặp lỗi chỉ bị phát hiện khi nhận hóa đơn hoặc khi bị khóa tài khoản.

**Câu hỏi kiểm:**
1. Có bộ đếm số call theo phiên/theo ngày không? Không → FAIL/WARNING theo phân loại trên.
2. Có ngưỡng cảnh báo khi chạm % hạn mức không? Không → WARNING.
3. Bộ đếm có tách theo môi trường (MOCK/SANDBOX/LIVE) không? Gộp chung → WARNING (số liệu LIVE bị nhiễu bởi dev).

---

## 3. Xử lý mâu thuẫn giữa các rule

Ghi rõ để AI không tự quyết mỗi lần một kiểu.

| Mâu thuẫn | Quy tắc thắng | Hành vi bắt buộc |
|-----------|---------------|------------------|
| **R2 vs R5** — chờ rate limit lâu hơn timeout tổng | **R5 thắng** | Dừng vòng lặp, trả về trạng thái `TIMEOUT_WHILE_RATE_LIMITED` (không phải lỗi thường), ghi log rõ nguyên nhân là do chờ limit chứ không phải API hỏng |
| **R3 vs R9** — breaker muốn retry call không idempotent | **R9 thắng** | Không retry. Đẩy vào hàng đợi chờ xử lý thủ công hoặc yêu cầu người dùng thử lại |
| **R6 vs mọi rule** — kill switch bật | **R6 thắng** | Trả về ngay, không gọi mạng, không tính vào bộ đếm lỗi của R3 |
| **R4 vs R3** — nhận mã "đã bị ban" | **R4 thắng** | Dừng hẳn + alert. Không đưa vào cơ chế backoff của R3 |

---

## 4. Form khai báo — điền ở Stage kiến trúc

Bắt buộc điền **trước khi** viết code. Chưa điền xong thì không mở gate sang stage code.

### 4.1 Danh sách dịch vụ ngoài

| # | Dịch vụ | Mục đích | Môi trường có sẵn | Tính phí theo call? |
|---|---------|----------|-------------------|---------------------|
| 1 | | | ☐ MOCK ☐ SANDBOX ☐ LIVE | ☐ Có ☐ Không |
| 2 | | | ☐ MOCK ☐ SANDBOX ☐ LIVE | ☐ Có ☐ Không |

### 4.2 Bảng endpoint

| Endpoint | Method | Idempotent? | Rate limit công bố | Timeout đặt (s) | Được retry? |
|----------|--------|-------------|--------------------|-----------------|-------------|
| | | ☐ Có ☐ Không | | | ☐ Có ☐ Không |

> Cột `Idempotent?` là cột quan trọng nhất bảng này. Điền sai ở đây → R9 mất tác dụng hoàn toàn.

### 4.3 Bảng mã lỗi (phục vụ R4)

| Mã lỗi | Nhóm | Hành động |
|--------|------|-----------|
| | ☐ Retry được ☐ Dừng hẳn + alert ☐ Lỗi logic | |

### 4.4 Ngưỡng cấu hình

| Tham số | Giá trị | Biến ENV |
|---------|---------|----------|
| Rate limit (call/giây) | | |
| N lỗi liên tiếp kích hoạt breaker | | |
| Backoff khởi điểm / tối đa (s) | | |
| Timeout từng request (s) | | |
| Timeout tổng vòng lặp (s) | | |
| Số vòng lặp tối đa | | |
| Hạn mức call/ngày + % cảnh báo | | |
| Kill switch | | |

---

## 5. Bảng nghiệm thu — dùng ở Stage review

Reviewer chạy trong **context sạch**, chỉ đọc code + bảng khai báo Mục 4. Không đọc lại lịch sử chat của Builder.

Kết quả mỗi dòng chỉ được là `PASS` / `FAIL` / `N/A` kèm **bằng chứng** (đường dẫn file + số dòng). Không chấp nhận kết luận chung chung.

| Mã | Kiểm | Mức | Kết quả | Bằng chứng |
|----|------|-----|---------|------------|
| R1 | Số file gọi HTTP trực tiếp = 1 | 🔴 | | |
| R2 | Có limiter + vượt thì chờ (không skip) | 🔴 | | |
| R3 | Có ngưỡng N + backoff tăng dần + max backoff | 🔴 | | |
| R4 | Có bảng mã lỗi ≥ 3 nhóm, xử lý tách nhánh | 🔴 | | |
| R5 | Mọi vòng lặp có max vòng + timeout tổng | 🔴 | | |
| R6 | Có ENV kill switch | 🟡 | | |
| R7 | Có 3 môi trường, mặc định = MOCK | 🔴 | | |
| R8 | Log gộp lỗi lặp + summary định kỳ | 🟡 | | |
| R9 | Mọi endpoint có cờ idempotent; non-idempotent có khóa chống trùng | 🔴 | | |
| R10 | Không secret trong source, .gitignore đúng, không log secret | 🔴 | | |
| R11 | Timeout set tường minh cho từng request | 🔴 | | |
| R12 | Có bộ đếm call + ngưỡng cảnh báo | 🔴/🟡 | | |

**Điều kiện qua gate:** 0 dòng `FAIL` ở mức 🔴. Mọi 🟡 `FAIL` phải được ghi vào `TASKS.md` nhãn `tech-debt` kèm ngày dự kiến xử lý.

---

## 6. Changelog

| Phiên bản | Ngày | Thay đổi |
|-----------|------|----------|
| 1.0 | | Khởi tạo. R1–R8 từ bản gốc. Bổ sung R9 (idempotency), R10 (secret), R11 (timeout từng request), R12 (quota). Thêm gate check Mục 0, bảng xử lý mâu thuẫn Mục 3, form khai báo Mục 4, bảng nghiệm thu Mục 5. Chuyển toàn bộ rule từ dạng khẩu hiệu sang dạng câu hỏi kiểm nhị phân. |
