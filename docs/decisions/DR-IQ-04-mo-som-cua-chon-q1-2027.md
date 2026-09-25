# DR-IQ-04 — Mở sớm cửa CHỌN: tiêu chí + hạn ngạch `DR-Q1-2027` có hiệu lực từ 25/09/2026

> **Ngày chốt:** 25/09/2026 · **Người quyết:** chủ dự án (*"Dùng luôn từ ngày hôm nay 25/09"*), phiên mã `12c579bc`
> thi hành (`TD-0421`, đặt chỗ `eb668b4`) · **Chi phí:** 0 suất. Không đổi `N`, không đổi rào, không thêm lượt chọn nào.

> 🔴 **File này được viết để phiên IDEA sạch (`DR-009`) đọc được**, cùng luật với `DR-Q1-2027`: nó **không** ghi con
> số hay kết cục định lượng nào của Tool D.

---

## 1. Quyết định

Tiêu chí chọn và hạn ngạch của **`DR-Q1-2027-tieu-chi-chon-y-tuong.md`** có hiệu lực **sớm, từ 25/09/2026**, thay vì từ
01/01/2027. Một lần chọn ghi trong khoảng **25/09/2026 – 31/12/2026** được đối chiếu với `DR-Q1-2027` và **tính vào quỹ
hạn ngạch của quý 1/2027**.

<!-- DR-IQ-04:MO_SOM:BEGIN -->
```json
{"tieu_chi": "DR-Q1-2027-tieu-chi-chon-y-tuong.md", "tu_ngay": "2026-09-25", "cat_khoi": "DR-IQ-03"}
```
<!-- DR-IQ-04:MO_SOM:END -->

Khối trên là thứ máy đọc (`tieu_chi_cho_ngay()`, dùng chung cho **cửa CHỌN** và **audit `TD-0120`**). Khoá `cat_khoi`
nói: khối mở sớm của `DR-IQ-03` **thôi phủ** từ 25/09/2026. Khối hỏng, trỏ file không có, hay cắt một khối không chồng
⇒ máy **từ chối**, không quay về mặc định trong im lặng.

## 2. Đây là một lần GHI ĐÈ có ý thức — khai thẳng

- `DR-Q1-2027` ghi *"Phạm vi hiệu lực: quý 1/2027"*. DR này **ghi đè** vế ngày bắt đầu.
- `DR-IQ-03` mở sớm tiêu chí quý 4/2026 cho `[24/09, 01/10)`. DR này **cắt** cửa sổ đó tại 25/09/2026. Lần chọn đã ghi
  ngày 24/09/2026 vẫn đối chiếu `DR-Q4-2026` như cũ.
- Lượt chọn quý 4/2026 đã dùng; `DR-Q4-2026` cấm chọn bù. Lượt mở ở đây **không phải lượt bù**: nó là lượt của quý
  1/2027 được dùng sớm. Quý 4/2026 không có thêm lượt nào.
- **Vì sao chấp nhận được:** tiêu chí `TC-Q1-2027-xx` viết và commit **trước** quyết định này. Thứ thay đổi chỉ là
  **ngày** được phép dùng chúng. Cùng dạng với tiền lệ `DR-IQ-03`.

## 3. Ràng buộc đi kèm — không có chúng thì không mở

1. **MỘT lượt:** đúng `HAN_NGACH_CHON` của `DR-Q1-2027`. Chọn trước 01/01/2027 thì quý 1/2027 còn **0**; lượt kế tiếp
   thuộc quý 2/2027 (cần file tiêu chí quý đó).
2. **Chỉ mã `TC-Q1-2027-xx`.** Trích mã quý khác ⇒ từ chối.
3. **`TC-Q1-2027-00` bắt buộc:** tờ chọn ghi phép tính xác suất phát hiện; dưới 50% ⇒ không chọn.
4. **Đường đi sau chọn:** `DR-VONG-DOI-01`.

## 4. Giữ nguyên mọi chốt khác

- **Phiên IDEA sạch** chọn (`DR-009`, `DR-IQ-02` §5), qua công cụ `--chon-y-tuong` của E6. Không ghi tay.
- Danh sách loại trừ **Z-1…Z-5** (`DR-IQ-01A`).
- Trần nộp đơn theo quý, luật nộp đơn, `N`, rào: không đổi.

## 5. Không thuộc DR này

- Không sửa chữ của `DR-IQ-03`, `DR-Q4-2026`, `DR-Q1-2027`, `DR-IQ-01A`, `DR-IQ-02`.
- Không ghi dòng CHỌN nào. Tab thi hành DR này đã thấy số Tool D nên **không được chọn** (`DR-009`).
