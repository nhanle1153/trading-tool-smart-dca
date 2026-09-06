# research-log.md — Nhật ký nghiên cứu Tool D

> **Append-only.** Không sửa, không xoá mục cũ. Ghi theo ngày, mục mới xuống dưới.
> Bắt buộc ghi mỗi lần: chẩn đoán "bot sai hay tầng đo sai" (§0d.7), quyết định chọn mốc dữ liệu
> (DR-011), và mỗi rủi ro tồn dư được chấp nhận có ý thức.

---

## 06/09/2026 — Khởi tạo repo, Giai đoạn 1–2

- Khởi tạo git repo, cây thư mục, 4 file quy trình.
- Chốt 7 quyết định nền tảng (xem `back-end-note.md` §0.2 và bảng đầu `TASKS.md`).
- Ghi nhận 7 mâu thuẫn, 5 trong đó đã chốt cách giải ngay (`back-end-note.md` mục 7).

### Rủi ro tồn dư được chấp nhận có ý thức

**RR-01 — L-Z25 không chứng minh được tuyệt đối rằng chưa từng chạy hyperopt.**
Spec (dòng 510) đòi grep cả "lịch sử lệnh". Kiểm được: `git grep` trên worktree,
`git log -S hyperopt --all` (bắt cả file đã xoá rồi), và `runs/cmd_audit.log` do wrapper tự ghi.
KHÔNG kiểm được: người dùng gõ thẳng `docker run ... freqtrade hyperopt` ngoài wrapper.
Chấp nhận vì cùng loại với thừa nhận của chính spec ở dòng 3317–3320 (cơ chế lockbox không cứng)
và 3507–3510. Biện pháp bù duy nhất là kỷ luật cá nhân — đã ghi thành điều cấm N3 trong `CLAUDE.md`.

**RR-02 — Lockbox chỉ tồn tại trên một ổ đĩa.** Dữ liệu lockbox không commit lên git (kích thước),
và spec dòng 4002 nói rõ không có lockbox thứ hai. Mất ổ = mất khả năng xác nhận cuối cùng của
cả dự án. Đã mở TD-0085 (backup ngoài git + **test khôi phục thật**) và OQ-08. Cho tới khi TD-0085
xong, đây là điểm hỏng đơn lẻ nghiêm trọng nhất của toàn bộ hạ tầng.
