# back-end-note.md — Cấu trúc chuẩn

> Đây là file trung tâm nhất của quy trình — nơi lưu mọi quyết định thiết kế, dùng lại xuyên suốt Giai đoạn 1 đến Giai đoạn 7.
> Copy cấu trúc này thành `back-end-note.md` riêng của project khi bắt đầu Giai đoạn 1.
> Cập nhật theo nguyên tắc B.5 — nối thêm có ngày tháng, không ghi đè lịch sử cũ.

## 1. UI Behavior
*Hành vi giao diện đã chốt — điền ở bước "Trích xuất Hợp đồng Dữ liệu" cuối Giai đoạn 3.*

| Màn hình | Hành vi | Ghi chú |
|---|---|---|

## 2. Data Shape
*Trường dữ liệu mỗi màn hình cần, kiểu dữ liệu.*

| Màn hình | Trường | Kiểu | Ghi chú |
|---|---|---|---|

## 3. Draft API needs
*Nhu cầu API nháp suy ra từ UI — chưa phải thiết kế API chính thức (việc đó chốt ở Giai đoạn 2/4 theo Nguyên tắc 9).*

| Tác vụ | API cần | Input | Output |
|---|---|---|---|

## 4. Validation Rules
*Giới hạn nhập liệu đã thể hiện trên UI.*

| Trường | Quy tắc validate |
|---|---|

## 5. Edge Cases
*Trạng thái rỗng, lỗi, loading đã thiết kế trên UI.*

| Tình huống | Hành vi mong đợi |
|---|---|

## 6. Open Questions
*Điều gì đó CHƯA quyết định — khác với Mâu thuẫn (mục 7, là điều ĐÃ quyết định nhưng xung đột nhau).*

| Câu hỏi mở | Ảnh hưởng nếu chưa trả lời | Mức độ (🔴 chặn tiến độ / 🟡 chốt sau) |
|---|---|---|

## 7. Mâu thuẫn & Cần làm rõ
*Áp dụng xuyên suốt Giai đoạn 1→7, không riêng vòng lặp bảo trì. Ghi nhận khi 2 quyết định đã chốt ở 2 thời điểm/giai đoạn khác nhau xung đột nhau — không được AI tự ý âm thầm chọn 1 bên rồi làm tiếp.*

| Mâu thuẫn phát hiện | Giai đoạn nào với giai đoạn nào | Mức độ (🔴 Chặn tiến độ / 🟡 Có thể chốt sau) | Cách giải quyết | Ngày | Người quyết định |
|---|---|---|---|---|---|

> 🔴 Chặn tiến độ: dừng code ngay, xử lý trước khi tiếp tục.
> 🟡 Có thể chốt sau: ghi nhận, tiếp tục phần khác, bắt buộc giải quyết trước khi qua Giai đoạn 5 (Kiểm tra trước go-live) — không được mang mâu thuẫn 🟡 vượt qua go-live.

## 8. Lịch sử thay đổi
*Theo Phụ lục B.5 — nối thêm, không ghi đè.*

| Mục thay đổi | Loại thay đổi (➕ Thêm mới / ❌ Hủy / ♻️ Sửa đổi) | Nội dung cũ | Nội dung mới | Lý do | Ngày |
|---|---|---|---|---|---|
