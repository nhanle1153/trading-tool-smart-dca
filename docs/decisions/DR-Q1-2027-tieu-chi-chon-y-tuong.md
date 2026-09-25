# DR-Q1-2027 — Tiêu chí chọn ý tưởng ra khỏi Idea Queue, quý 1/2027

> **Chốt 25/09/2026** (chủ dự án), soạn bởi phiên mã `12c579bc` (`TD-0420`; bản nháp `93f0d16` để hạn ngạch 0). Commit RIÊNG
> và TRƯỚC mọi dòng `SELECTED` của quý 1/2027.

> ✅ **Phiên IDEA/CHỌN ĐƯỢC đọc file này.** 🔴 File này cố ý **không** ghi con số hay kết cục định lượng nào của Tool D.

**Phạm vi hiệu lực:** quý 1/2027 (01/01/2027 – 31/03/2027). **Append-only:** sửa giữa quý chỉ có hiệu lực từ quý sau.

---

## 1. HẠN NGẠCH CHỌN QUÝ NÀY

```
HAN_NGACH_CHON: 1
```

Chủ dự án chốt **1** (25/09/2026). Ý tưởng được chọn đi theo `DR-VONG-DOI-01` (vòng đời chung cho ứng viên) và dùng lockbox
`[T2,T3]` nếu tới được bước lockbox (`DR-VONG-DOI-01` §6 (b)).

**Giới hạn:** không chọn ý tưởng thuộc Z-1…Z-5 (`DR-IQ-01A`); CHỌN do phiên IDEA sạch (DR-009); `selection_reason` không
tham chiếu kết quả định lượng Tool D và không viện dẫn diễn biến thị trường cụ thể có ngày tháng; không dồn, không chọn bù.

## 2. ĐIỀU KIỆN LOẠI TRƯỚC KHI XẾP HẠNG — không đạt thì không được chọn

### TC-Q1-2027-00 — Độ mạnh thống kê đủ (bắt buộc, `DR-VONG-DOI-01` §3)
Tờ chọn khai đơn vị đo, `σ` (ước lượng từ dữ liệu thô EXPLORE hoặc lập luận cơ chế), `n` dự kiến trên lockbox, lợi thế tự
khai `μ`, rào `h = √(2·ln N)`, và xác suất phát hiện ≈ `Φ(μ·√n/σ − h)`. **Dưới 50% ⇒ không chọn** (chủ dự án chốt
25/09/2026; tương đương `μ ≥ h·σ/√n`).
*Vì sao:* một phép thử không có khả năng PASS ở cỡ mẫu hiện có sẽ tiêu suất và lockbox mà không trả lời được câu hỏi nào.

## 3. TIÊU CHÍ XẾP HẠNG — THỨ TỰ TỪ ĐIỂN, không phải điểm có trọng số

**TC-Q1-2027-01 quyết định trước; chỉ khi hoà mới xét 02**, và cứ thế.

### TC-Q1-2027-01 — Không phụ thuộc một chiều thị trường (yêu cầu chủ dự án, 25/09/2026)
Cơ chế sinh lợi được trong cả giai đoạn giá tăng lẫn giá giảm: hoặc trung tính hướng, hoặc có **luật đổi chiều khai TRƯỚC**,
đo được trên cả hai chế độ. Ý tưởng chỉ thắng khi thị trường đi một chiều xếp sau.
*Vì sao:* không chôn vốn khi thị trường đổi xu hướng.

### TC-Q1-2027-02 — Cơ chế độc lập với thanh khoản zone
Ý tưởng **không** dựa vào "dòng lệnh còn lại ở vùng giá cũ" (giữ nguyên tinh thần `TC-Q4-2026-01`).

### TC-Q1-2027-03 — Sức mạnh của câu "AI TRẢ TIỀN"
Người thua ở phía bên kia có bị **cấu trúc ép** tiếp tục thua không (bắt buộc phòng hộ, thanh lý, theo chỉ số), hay chỉ là
"có lẽ có ai đó thua".

### TC-Q1-2027-04 — Dùng lại được hạ tầng đo đã có
Futures Binance, 1H chính / 4H, 1D informative / 5m `timeframe_detail`, pool point-in-time, chiến lược chọn theo tên + file
phủ Freqtrade theo chiến lược, đo theo ngày hoặc theo lệnh. **Xếp cuối là cố ý: rẻ không bao giờ được thắng đúng.**

---

## 4. Máy kiểm được gì

`selection_reason` phải trích ít nhất một mã `TC-Q1-2027-nn` có thật trong file này; `HAN_NGACH_CHON` giới hạn số lần
chọn. `TC-Q1-2027-00` (độ mạnh) **chưa có máy kiểm** — người chọn phải ghi phép tính trong tờ chọn; máy kiểm là việc sau
(`MT-89`).
