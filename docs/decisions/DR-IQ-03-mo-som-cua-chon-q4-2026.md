# DR-IQ-03 — Mở sớm cửa CHỌN: tiêu chí + hạn ngạch `DR-Q4-2026` có hiệu lực từ 24/09/2026

> **Ngày chốt:** 24/09/2026 · **Người quyết:** chủ dự án (*"mở chọn ngay, không chờ 01/10"*), phiên mã `dd855fee`
> thi hành · **Chi phí:** 0 suất. Không đổi `N = 114`, không đổi hạn ngạch nào, không thêm suất nào.
> Mã `DR-IQ-03` + `TD-0376` đặt chỗ bằng commit `b4a3cbe` (N12 mục 7c). Commit **RIÊNG và TRƯỚC** mọi dòng mã.

> 🔴 **File này được viết để phiên IDEA sạch (`DR-009`) đọc được**, cùng luật với `DR-Q4-2026`: nó **không** ghi con
> số hay kết cục định lượng nào của Tool D. Phiên chọn đọc file này cùng `DR-Q4-2026` và `DR-IQ-01A`, không mở gì khác.

---

## 1. Quyết định

Tiêu chí chọn và hạn ngạch của **`DR-Q4-2026-tieu-chi-chon-y-tuong.md`** có hiệu lực **sớm, từ 24/09/2026**, thay
vì từ 01/10/2026. Một lần chọn ghi trong khoảng **24/09 – 30/09/2026** được đối chiếu với `DR-Q4-2026` và **tính vào
quỹ hạn ngạch của quý 4/2026**.

<!-- DR-IQ-03:MO_SOM:BEGIN -->
```json
{"tieu_chi": "DR-Q4-2026-tieu-chi-chon-y-tuong.md", "tu_ngay": "2026-09-24"}
```
<!-- DR-IQ-03:MO_SOM:END -->

Khối trên là thứ máy đọc (`idea_queue.tieu_chi_cho_ngay()`, `TD-0376`), dùng chung cho **cửa CHỌN** và **audit
`TD-0120`**. Khối hỏng, hoặc trỏ tới file không tồn tại ⇒ máy **từ chối**, không quay về mặc định trong im lặng.

## 2. Đây là một lần GHI ĐÈ có ý thức — khai thẳng

- `DR-Q4-2026` ghi *"Phạm vi hiệu lực: quý 4/2026 (01/10/2026 – 31/12/2026)"*. DR này **ghi đè** vế ngày bắt đầu.
- `DR-Q3-2026` khai `HAN_NGACH_CHON: 0` và *"sửa giữa quý chỉ có hiệu lực từ quý sau. Không có ngoại lệ"*. DR này
  **không sửa** file đó và không nâng hạn ngạch quý 3. Nó chuyển các ngày cuối quý 3 sang dùng **tiêu chí đã viết
  sẵn** của quý 4. Đây vẫn là ngoại lệ đối với tinh thần câu *"không có ngoại lệ"*, nên phải khai ra đây.
- Tiền lệ cùng dạng: `DR-D4-19`, chủ dự án ghi đè một điều kiện đã viết trước, và khai là ghi đè chứ không giả vờ
  điều kiện đã thoả.
- **Vì sao chấp nhận được:** tiêu chí `TC-Q4-2026-xx` viết và commit **trước** khi có quyết định này. Không có tiêu
  chí nào được viết sau khi nhìn hàng chờ. Thứ thay đổi chỉ là **ngày** được phép dùng chúng.

## 3. Ba ràng buộc đi kèm — không có chúng thì không mở

1. **MỘT suất dùng chung Q3 + Q4.** Chọn trong 24–30/09 thì ăn luôn hạn ngạch 1 của quý 4: quý 4 còn **0**. Máy
   thi hành bằng cách đếm lần chọn sớm vào quỹ của quý 4. Mở sớm không được biến thành hai suất.
2. **Chỉ mã `TC-Q4-2026-xx`.** Lý do chọn phải trích mã có trong `DR-Q4-2026`. Trích mã `TC-Q3-…` ⇒ từ chối.
3. **Không lùi hơn 24/09/2026.** Lần chọn mang ngày sớm hơn vẫn tra `DR-Q3-2026` (hạn ngạch 0) ⇒ từ chối.

## 4. Giữ nguyên mọi chốt khác của suất này

- **Phiên IDEA sạch** chọn (`DR-009`, `DR-IQ-02` §5), qua công cụ `--chon-y-tuong` của E6. Không ghi tay, không
  dùng script.
- Danh sách loại trừ **Z-1…Z-5** (`DR-IQ-01A`), gồm `IQ-0001`. `selection_reason` phải khai *"không thuộc
  Z-1…Z-5"* và vì sao.
- Ý tưởng được chọn cần **lockbox MỚI** và đi đủ chu trình từ D0. Suất đầu tiên của nó vẫn phải qua mọi cửa hiện
  hành của sổ trial.
- Suất hết hạn **31/12/2026**, không dồn, không chọn bù.

## 5. Cảnh báo cho người chọn

`IQ-0002` đã dùng hết lượt huỷ (`DR-IQ-02`). Chọn nó là **không có đường lùi**: sai thì không có sự kiện `VOIDED`
nào gỡ được nữa. Đọc kỹ `DR-Q4-2026` và `DR-IQ-01A` trước khi chọn.

## 6. Không thuộc DR này

- Không sửa `DR-Q3-2026`, `DR-Q4-2026`, `DR-IQ-01A`, `DR-IQ-02`.
- Không đổi luật nộp đơn, trần nộp 10 đơn/quý, `N = 114`, hay rào DSR.
- Không ghi dòng CHỌN nào. Tab thi hành DR này đã thấy số Tool D nên **không được chọn** (`DR-009`).
