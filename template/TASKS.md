# TASKS.md — Backlog Tổng & Tracker Công việc

> File này là **backlog tổng + tracker sống**, cập nhật liên tục trong lúc code — khác với `back-end-note.md` (chỉ chuẩn hóa/lưu theo chu kỳ).
> **Bắt buộc khởi tạo cho MỌI project cuối Giai đoạn 2**, kể cả chỉ 1 người/1 tab code — đây là nơi trả lời "còn bao nhiêu việc, làm việc nào tiếp theo" khi hệ thống có nhiều task (frontend + backend). Không chỉ dùng khi nhiều người/tab.
> Mỗi project có 1 file `TASKS.md` riêng, đặt cùng cấp với `back-end-note.md`.

## Quy tắc vận hành file này

1. **Mã việc:** `{Mã project}-{số thứ tự 4 chữ số}`, ví dụ `TD4-0001`, `AFF-0002`. Số **không bao giờ tái sử dụng**, kể cả khi việc bị hủy.
2. **Trạng thái công việc:** 🔓 Chưa làm · 🔒 Đang làm (bất kỳ ai, không cần ghi tên) · ✅ Done · ❌ Đã hủy.
3. **Trước khi bắt đầu code 1 việc:** đổi 🔓 → 🔒, commit + push dòng đó ngay lập tức, không code trước khi đã ghi nhận. Với project chỉ 1 người/1 tab, bước khóa này có thể nới lỏng, nhưng vẫn nên đổi trạng thái để theo dõi tiến độ.
3b. **Chọn việc tiếp theo:** lọc các dòng 🔓, ưu tiên việc không phụ thuộc gì hoặc có phụ thuộc (cột "Phụ thuộc vào") đã ✅.
4. **Khi làm xong:** đổi 🔒 → ✅.
5. **Việc bị hủy:** không xóa dòng — đổi thành ❌, giữ nguyên mã, để mọi tham chiếu cũ đến mã đó vẫn còn hiệu lực.
6. **Cập nhật trạng thái** (🔓/🔒/✅/❌): tự do, ngay lập tức, không cần qua bước "chuẩn hóa và lưu".
7. **Cập nhật nội dung việc** (thêm việc mới/hủy việc/sửa mô tả): phải ghi vào mục "Lịch sử thay đổi checklist" bên dưới — không tự ý sửa mà không ghi nhận.
8. **Cập nhật file dùng chung nhiều người/tab:** `git pull` trước khi sửa dòng của mình → chỉ sửa đúng dòng liên quan → commit + push ngay, không gộp nhiều thay đổi rồi mới commit 1 lần.
9. **Gọi bằng mã:** nhắc trực tiếp mã việc (ví dụ "TD4-0001 xong chưa", "hủy AFF-0015") — AI tra đúng dòng theo mã, không cần mô tả lại nội dung.
10. **Nhóm việc theo file/module không giao nhau** — mỗi "Mục lớn" chỉ nên gồm các việc đụng vào 1 tập file/thư mục không trùng với Mục lớn khác, để giảm khả năng xung đột khi merge.
11. **Nguồn tạo "Mục lớn":** lấy từ danh sách chức năng theo ưu tiên ở `form-xac-dinh-pham-vi.md` (Giai đoạn 1) kết hợp với các module/khối trong sơ đồ kiến trúc ở `ARCHITECTURE.md` (Giai đoạn 2) — không tự đặt Mục lớn tùy ý mà không đối chiếu 2 nguồn này.

## Checklist công việc

| Mã việc | Mục lớn | Tên việc | Trạng thái | Phụ thuộc vào (mã) | Ghi chú |
|---|---|---|---|---|---|
| | | | 🔓 | | |

## Lịch sử thay đổi checklist

| Mã việc | Loại thay đổi (➕ Thêm mới / ❌ Hủy / ♻️ Sửa đổi) | Nội dung cũ | Nội dung mới | Lý do | Ngày |
|---|---|---|---|---|---|
| | | | | | |
