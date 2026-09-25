# DR-VONG-DOI-01 — Vòng đời chung cho ứng viên suất (d)

> **Trạng thái: CHỐT 25/09/2026** — chủ dự án trả lời §4 (a)(b)(c), xem §6. Soạn bởi phiên mã `12c579bc` (`TD-0420`,
> đặt chỗ `4d76675`; bản nháp `93f0d16`). Giải `MT-88`. **Chi phí:** 0 trial.

> ✅ **Phiên IDEA/CHỌN ĐƯỢC đọc file này:** nó chỉ nói thủ tục, không chứa con số hay kết cục định lượng nào của Tool D.
> Ai sửa file này phải giữ nguyên tính chất đó.

---

## 1. Vì sao

Luật vòng đời hiện có (D5–D9, điều kiện chạm lockbox `DR-LOCKBOX-03`) viết cho một chiến lược nhiều biến thể, một hướng,
đơn vị R. Ứng viên suất (d) có thể chỉ có **một cấu hình** (`so_bien_the: 1`), không có D9/PBO, và đơn vị đo khác ⇒ không
có đường hợp lệ nào tới lockbox (`MT-88`). DR này viết MỘT đường chung, trước khi chọn ứng viên kế tiếp.

## 2. Đường đi (áp cho ứng viên một cấu hình; ứng viên nhiều biến thể vẫn đi D5–D9 như cũ)

| Bước | Việc | Viết/khoá TRƯỚC bước |
|---|---|---|
| 0 | **CHỌN** ở phiên IDEA sạch, kèm **phép tính độ mạnh thống kê** theo tiêu chí quý (§3) | — |
| 1 | **DR thiết kế D0**: tham số (ngoài `tier_b`), khối `DR-BIEN-THE-01:KHOA`, lớp thoát lệnh, đơn vị đo, **ngưỡng PASS lockbox + cổng vào lockbox (§2.1)** | mã chiến lược |
| 2 | **Dựng + chạy thử trọn đường đo** trên dữ liệu tổng hợp qua ĐÚNG entrypoint sẽ dùng (bắt lỗi đo sau niêm phong) | suất đầu |
| 3 | **Đếm trên EXPLORE** (0 suất, cổng thiết kế `TD-0375`/`DR-CAN-RO-01`) | suất đầu |
| 4 | **CALIB** `[T0,T1)` — một suất; khai thuế nhiễu `T = h·σ/√n` trước (luật khai hiện hành của sổ trial) | suất |
| 5 | **WFO** `[T1,T2)` — một suất; khai `T` trước | suất |
| 6 | **Lockbox** — chạm một lần nếu cổng §2.1 thoả | lần chạm |
| 7 | D10 → D11 → D12 theo `DR-TRIEN-KHAI-01`; vốn giữ trần D12 tới lớp xác nhận | tiền thật |

### 2.1 Cổng vào lockbox cho ứng viên một cấu hình — thay `DR-LOCKBOX-03` §2 cho lớp này

- Viết trong DR thiết kế D0 (bước 1), **trước suất CALIB**, không phải sau WFO.
- Dạng: một điều kiện máy đọc được trên kết quả WFO, **không** đòi PBO. Đề xuất mặc định: *WFO có mean cùng dấu với lợi
  thế đã khai VÀ mọi điều kiện "đúng cơ chế" đã đăng ký đạt*. Cổng này KHÔNG phải cổng thống kê (rào `h` áp ở lockbox).
- Lockbox dùng ngưỡng PASS đã viết ở bước 1; không được viết lại sau khi thấy CALIB/WFO.

## 3. Độ mạnh thống kê — phép tính bắt buộc ở cửa CHỌN (giải `MT-89` cùng tiêu chí quý)

Với rào `h = √(2·ln N)` và cỡ mẫu lockbox dự kiến `n` (số quan sát theo đơn vị đo của ứng viên), phép thử chỉ PASS khi
`mean > h·σ/√n`. Tờ chọn phải khai: đơn vị đo, `σ` ước lượng **từ dữ liệu thô EXPLORE hoặc lập luận cơ chế** (không từ kết
quả Tool D), `n` dự kiến trên lockbox, mức lợi thế tự khai `μ`, và **xác suất phát hiện** ≈ `Φ(μ·√n/σ − h)`.

## 4. Câu hỏi cho chủ dự án — chốt TRƯỚC khi DR có hiệu lực

- **(a) Ngưỡng độ mạnh tối thiểu ở cửa CHỌN.** Đề xuất: xác suất phát hiện ≥ 50% ở mức lợi thế tờ chọn tự khai. Thấp hơn ⇒
  không được chọn.
- **(b) Lockbox `[T2,T3]`** (chưa chạm; `DR-LOCKBOX-04` §2.5 gắn cho ứng viên suất (d) ĐẦU TIÊN). Chuyển cho ứng viên kế
  tiếp (cần DR bổ sung `DR-LOCKBOX-04`), hay dành lại?
- **(c) `N = 114` và rào `h`.** Giữ nguyên (đề xuất — đổi sau khi đã biết kết quả là nới chuẩn của chính mình), hay đổi
  bằng DR riêng trước khi thấy dữ liệu mới?

## 5. Không thuộc DR này

Không sửa `DR-LOCKBOX-03` (vẫn đúng cho ZA/ứng viên nhiều biến thể), không đổi seal, không chạm lockbox, không đổi
`N`/`h` (trừ khi §4 (c) chốt khác bằng DR riêng).

## 6. Chủ dự án chốt §4 — 25/09/2026

- **(a)** Ngưỡng độ mạnh ở cửa CHỌN: **xác suất phát hiện ≥ 50%** ở mức lợi thế tờ chọn tự khai (`Φ(μ·√n/σ − h) ≥ 0,5`,
  tương đương `μ ≥ h·σ/√n`). Dưới ngưỡng ⇒ không được chọn. Ghi vào tiêu chí quý (`TC-Q1-2027-00`).
- **(b)** Lockbox `[T2,T3]` **chuyển cho ứng viên kế tiếp** — ứng viên đầu tiên THỰC SỰ chạm lockbox. Ghi bổ sung vào
  `DR-LOCKBOX-04` (§2.5 cũ gắn cho "ứng viên suất (d) đầu tiên", tức IQ-0003, đã dừng mà không chạm).
- **(c)** **Giữ nguyên `N = 114` và rào `h`.** Cửa độ mạnh (a) lọc trước các ý tưởng không đo nổi, thay vì nới chuẩn sau khi
  đã biết kết quả.
- Hạn ngạch chọn quý 1/2027 = **1** (`DR-Q1-2027`).

