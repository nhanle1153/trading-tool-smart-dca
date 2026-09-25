# Phiên IDEA sạch — sinh, nộp và CHỌN ý tưởng (tạo ngày {ngay})

> Thư mục này do `scripts/tao_phien_sach.py` của repo Tool D tạo, và nằm **ngoài** repo một cách cố ý: `CLAUDE.md` của
> repo không tự nạp vào phiên chat mở tại đây. Đó là cơ chế "phiên sạch" mà DR-009 đòi hỏi.

## Việc cần làm

1. Sinh một hoặc vài ý tưởng giao dịch mới, cơ chế **khác hẳn** các họ bị loại trong `DR-IQ-01A-danh-sach-loai-tru-co-che.md`.
2. Soạn đơn (cửa NỘP) thành file `don-N.yaml` theo `mau-don-y-tuong.yaml`. Chủ dự án chạy lệnh ghi vào sổ.
3. Sau khi nộp: xếp hạng các ý tưởng đang QUEUED theo **file tiêu chí chọn của quý** (`{tieu_chi}`), rồi soạn tờ chọn
   `to-chon.yaml` cho **đúng một** ý tưởng (cửa CHỌN). Chủ dự án chạy lệnh chọn.
4. Làm đúng MỌI yêu cầu trong file tiêu chí, kể cả phần tính toán bắt buộc đi kèm tờ chọn (nếu file đó đòi).

Không có ý tưởng nào đủ tốt thì **không chọn**. Để suất hết hạn còn hơn tiêu nó cho một ý tưởng yếu.

## Ranh giới — ĐỌC TRƯỚC KHI NGHĨ Ý TƯỞNG

**ĐƯỢC đọc:** mọi file trong thư mục này; kiến thức thị trường, tài liệu bên ngoài; phân tích tự làm trên dữ liệu thị
trường thô của tập EXPLORE (không tính là nhiễm).

**CẤM đọc, kể cả vô tình:** bất kỳ file nào khác trong repo `C:\Trading Tool_Smart DCA` (nhất là `CLAUDE.md`,
`back-end-note.md`, `TASKS.md`, `docs/research-log.md`, `docs/du-lieu-do/**`, `docs/lich-su/**`, các `docs/decisions/DR-*`
không có trong thư mục này, `registry/idea_queue.jsonl` bản đầy đủ); mọi kết quả backtest/WFO/ablation của Tool D. Nghi
ngờ phiên đã nhiễm ⇒ khai `data_source: TOOL_D_RESULTS` (tự loại đơn).

## Luật cần nhớ

- **Sổ là nhật ký sự kiện** (`DR-IQ-02`): trường đã nộp không sửa được. Muốn đổi nội dung một ý tưởng đã có ⇒ nộp đơn mới,
  khai `overlaps_with: ["IQ-xxxx"]`.
- Trần nộp 10 đơn/quý (đơn bị từ chối cũng tính). Máy từ chối `mechanism` gần trùng ý tưởng đã REJECTED.
- Tờ chọn: `selected_at` **để trống** (máy đóng dấu); `selection_reason` trích mã tiêu chí có trong file tiêu chí của quý,
  ghi rõ *"không thuộc Z-1…Z-5"* kèm lý do, và **chỉ lập luận bằng cơ chế kinh tế** — không viện dẫn diễn biến giá hay sự
  kiện thị trường cụ thể nào có ngày tháng.
- Tờ chọn — **độ mạnh thống kê:** nếu file tiêu chí khai dòng `DO_MANH_TOI_THIEU`, tờ chọn phải có khối:
  ```yaml
  do_manh:
    don_vi: "lợi suất ngày"      # đơn vị của một quan sát
    sigma: 0.0                   # độ lệch chuẩn một quan sát — từ dữ liệu thô EXPLORE hoặc lập luận cơ chế
    n_lockbox: 0                 # số quan sát dự kiến trên lockbox (số nguyên)
    mu: 0.0                      # lợi thế tự khai, cùng đơn vị
    nguon_sigma: "…"             # sigma lấy từ đâu, tính thế nào
    xac_suat_khai: 0.0           # tuỳ chọn — máy chỉ in cạnh, không dùng
  ```
  Máy **tự tính** xác suất phát hiện `Φ(μ·√n/σ − h)` với rào `h` của dự án; dưới ngưỡng ⇒ từ chối ghi.

## Cách nộp và chọn — phiên này KHÔNG chạy lệnh nào

🔴 Phiên IDEA không chạy lệnh Docker hay lệnh nào đụng tới repo: báo cáo kiểm tra sổ in sau khi ghi có thể chứa số kết quả
của Tool D. Việc của phiên này: soạn file trong **thư mục này**, rồi dừng.

**Cách nộp (script canh thư mục của chủ dự án, `TD-0422`):**
- Soạn nháp `don-N.yaml` / `to-chon.yaml` ở thư mục này. Nháp **không** bao giờ bị nộp.
- CHỈ khi chủ dự án bảo nộp một đơn, chép đúng file đó vào thư mục con `cho-nop\`. Script sẽ tự nộp. Mỗi lần nộp, kể cả
  bị từ chối, tính vào trần 10 đơn/quý, nên đừng đặt file vào `cho-nop\` để "thử".
- Tờ chọn: chép `to-chon.yaml` vào `cho-nop\`. Script chỉ chọn sau khi chủ dự án gõ xác nhận ở cửa sổ canh.
- Kết quả (chỉ dòng ✅/🛑 đã lọc) nằm ở cuối `ket-qua-nop.txt` trong thư mục này. Tự đọc file đó, không cần chủ dự án dán.
- Bị 🛑 thì sửa file trong `cho-nop\` (lưu đè). Nội dung đổi, script nộp lại.

Không có script canh thì chủ dự án chạy lệnh tay (xem `LOI-MO-DAU.md`) và dán lại **chỉ** dòng ✅ hoặc 🛑.

⚠️ Mở phiên này là **phiên mới**, không "tiếp tục" phiên cũ.
