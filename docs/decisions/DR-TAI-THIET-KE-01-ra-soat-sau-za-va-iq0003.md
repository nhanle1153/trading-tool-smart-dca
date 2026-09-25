# DR-TAI-THIET-KE-01 — Rà soát sau ZA LONG và IQ-0003, trước vòng ý tưởng kế tiếp (NHÁP)

> **Trạng thái: NHÁP — chủ dự án đọc và quyết §5.** Soạn 25/09/2026, phiên mã `12c579bc` (`TD-0416`, đặt chỗ `82fa025`).
> **Chi phí:** 0 trial.

> 🔴 **PHIÊN IDEA/CHỌN KHÔNG ĐỌC FILE NÀY** (`DR-009`). Phiên soạn đã nhiễm: file này chỉ bàn **cấu trúc và quy trình**,
> **không** sinh, gợi ý hay chấm ý tưởng giao dịch nào. Số đo chỉ được TRỎ tới, không chép lại.

---

## 1. Hiện trạng (25/09/2026)

| Mục | Trạng thái | Nguồn |
|---|---|---|
| Zone Absorption LONG | FAIL ở D4, `retest_forbidden` | `DR-ZA-01` |
| IQ-0003 (rổ funding trung tính) | INCONCLUSIVE vì thiếu độ mạnh thống kê; lockbox chưa chạm | `DR-KET-CUC-IQ0003-01` |
| Ngân sách trial | 103/114 còn lại (đọc lại `n_used()` trước khi dùng con số này) | `registry/trial_registry.jsonl` |
| Lockbox `[T2, T3]` | chưa chạm, gắn cho ứng viên suất (d) đầu tiên | `DR-LOCKBOX-04` §2.5 |
| Suất (d) quý 4/2026 | đã dùng | `DR-IQ-03` §3.1 |
| Short | tắt lại; đường Short của ZA dựng rồi, không đo | `DR-SHORT-03` |
| Dry-run D11 / D10 | dừng 25/09/2026 08:38 UTC / không chạy | `DR-SHORT-03` §3, `DR-KET-CUC-IQ0003-01` §3 |

**Hạ tầng dùng lại được** (không phụ thuộc chiến lược): sổ trial append-only + cửa ghi (biến thể theo cấu hình
`DR-BIEN-THE-01`, hướng `NEUTRAL` `TD-0407`, cổng thiết kế `TD-0375`/`DR-CAN-RO-01`); bộ chạy E1 theo tên chiến lược + file
phủ Freqtrade theo chiến lược (`TD-0400`); rổ theo giai đoạn point-in-time; bộ đo lợi suất ngày (`TD-0408`); trần vốn D12
(`TD-0382`/`TD-0404`); hạ tầng D10 (`TD-0384`, `TD-0411`–`0413`).

## 2. Bài học cấu trúc — không phải bài học về thị trường

1. **Độ mạnh thống kê phải kiểm ở cửa CHỌN, không phải sau khi đã tiêu suất.** Rào `h = √(2·ln N) ≈ 3,08` (N = 114) và
   lockbox ~217 ngày có nghĩa: một phép thử chỉ PASS được khi `mean > h·σ/√n`. Với σ lợi suất ngày cỡ 1–1,5% (thước đo đã
   commit của IQ-0003), mức đó ≈ 0,3%/ngày. `n cần ≈ (h·σ/mean)²`. Ngưỡng bác bỏ của IQ-0003 được viết và chọn mà không ai
   tính dòng này; phải tới lúc dò đường lockbox mới lộ ra. → `MT` đề xuất (§6).
2. **Vòng đời D5–D9 và điều kiện chạm lockbox (`DR-LOCKBOX-03`) viết cho ZA** (LONG, đơn vị R, arm, PBO trên các biến thể
   D5). Ứng viên suất (d) một cấu hình không đi qua được, và không có văn bản nào nói ứng viên phải đi đường nào. → `MT` đề
   xuất (§6).
3. **Hai lần suýt mất suất vì máy đo hỏng SAU niêm phong** (E1 trích lệnh kiểu ZA; lệnh đóng cưỡng bức ở biên cửa sổ). Cả
   hai chỉ bắt được nhờ chạy máy đo trên backtest thật TRƯỚC khi tiêu suất. Nên thành luật: *mọi đường đo mới phải chạy trọn
   trên dữ liệu tổng hợp qua đúng entrypoint trước suất đầu tiên*.
4. **Dịch vụ chạy dài đọc thẳng thư mục làm việc** ⇒ cấu hình chưa commit có hiệu lực (`MT-86`).
5. **Nhịp một suất (d) mỗi quý + một lockbox dùng một lần** làm mỗi vòng ý tưởng dài nhiều tháng. Cùng lúc đó, lockbox
   ngắn làm phép đo yếu (điểm 1).

## 3. Yêu cầu chủ dự án nêu (25/09/2026)

*"Thị trường có tăng có giảm, cần linh hoạt để khỏi chôn vốn khi qua giai đoạn downtrend và uptrend."* Dưới dạng **ràng buộc
cho tiêu chí chọn quý tới** (không phải ý tưởng):
- cơ chế **không phụ thuộc một chiều thị trường**, hoặc có **luật đổi chiều khai TRƯỚC**, đo được trên cả hai chế độ;
- tờ chọn phải kèm **phép tính độ mạnh thống kê** (§2.1) với σ và n dự kiến của chính phép thử;
- báo cáo tách theo chế độ thị trường (tăng / giảm / đi ngang) là **chỉ ghi**, không thay tiêu chí chính.

## 4. Những gì KHÔNG đổi được mà không có DR riêng

`N = 114`, rào `h`, các mốc T0–T3, seal 1, luật một lần chạm lockbox, `DR-009` (phiên sạch), `retest_forbidden` của ZA LONG.

## 5. Câu hỏi cho chủ dự án — quyết TRƯỚC khi thấy dữ liệu mới

1. **Độ mạnh thống kê:** bắt buộc ở cửa CHỌN từ quý 1/2027 (tiêu chí `TC-Q1-2027-xx` mới)? Ngưỡng tối thiểu (ví dụ xác suất
   phát hiện ≥ 50% ở mức lợi thế mà chính tờ chọn khai)?
2. **Rào và lockbox cho vòng sau:** giữ `N = 114` và lockbox `[T2, T3]` (~217 ngày), hay dùng dữ liệu sau `T3` để có đoạn
   dài hơn (chờ thêm thời gian)? Đổi `N` hay rào đều là quyết định lớn, phải có DR.
3. **Vòng đời tổng quát:** viết lại D5–D9 + `DR-LOCKBOX-03` dạng áp cho mọi ứng viên (một cấu hình hay nhiều cấu hình, mọi
   hướng, mọi đơn vị đo)?
4. **Nhịp ý tưởng:** khi nào mở phiên IDEA sạch cho quý 1/2027? Có nới hạn ngạch chọn (hiện 1/quý cho suất (d)) không?
5. **Hạ tầng vận hành:** dry-run/D10 để dừng tới khi có ứng viên qua lockbox, hay chạy lại riêng để đo hạ tầng lệnh (không
   gắn chiến lược)?

## 6. `MT` đề xuất — CHƯA ghi `back-end-note.md` (chờ lệnh "chuẩn hóa và lưu")

- **Vòng đời D5–D9 + `DR-LOCKBOX-03` không áp được cho ứng viên suất (d) một cấu hình** (§2.2). `MT-87` đã có chủ ⇒ lấy mã
  còn trống lúc ghi.
- **Thiếu kiểm độ mạnh thống kê ở cửa CHỌN** (§2.1).
