# Provider Map — Bản đồ Provider AI/Dịch vụ bên thứ ba

> Dùng khi hệ thống gọi đến 1 hoặc nhiều provider AI/dịch vụ bên ngoài (sinh ảnh, AI content, gửi email, thanh toán...).
> Điền ở Giai đoạn 1, copy vào `back-end-note.md` của project.
> Đây là quyết định nền tảng khó đảo ngược — áp Nguyên tắc 9: AI phải phân tích trade-off + đề xuất, không tự chọn.

| Tác vụ | Provider chính | Provider dự phòng | Input/Output | Chi phí/đơn vị | Rate limit | Lý do chọn |
|---|---|---|---|---|---|---|
| | | | | | | |

## Nguyên tắc kiến trúc bắt buộc

- **Mỗi provider phải được bọc sau 1 lớp trung gian (interface/adapter)** trong code — nghiệp vụ chính gọi vào lớp trung gian này, không gọi thẳng vào provider.
- Khi cần đổi provider (giá tăng, bị giới hạn, ngừng dịch vụ) → chỉ sửa lớp trung gian, không sửa lại toàn bộ logic nghiệp vụ.

## Giám sát chi phí

- Theo dõi chi phí gọi API tích lũy theo provider — tránh trường hợp lỗi logic gọi lặp vô hạn gây phát sinh chi phí lớn mà không ai biết cho đến khi nhận hóa đơn.
- Ngưỡng cảnh báo chi phí (nếu có): __________

## Lịch sử thay đổi Provider

| Tác vụ | Provider cũ | Provider mới | Lý do đổi | Ngày |
|---|---|---|---|---|
| | | | | |
