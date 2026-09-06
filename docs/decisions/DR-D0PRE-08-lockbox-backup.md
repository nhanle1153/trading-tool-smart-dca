# DR-D0PRE-08 — Backup lockbox ngoài git + test khôi phục thật (OQ-08, TD-0085)

> Spec dòng 4002: **không có "lockbox thứ hai"** — mất ổ đĩa chứa repo là mất khả năng xác nhận cuối
> cùng vĩnh viễn (LOCKBOX chỉ chạm đúng một lần, không tải lại được sau khi đã dùng). Chủ dự án chọn
> nơi lưu ngày 06/09/2026 sau khi xem đánh đổi.

## 1. Quyết định

- **Nơi lưu:** một thư mục khác trên cùng máy — `E:\lockbox-backup-tool-d\` (sibling của repo, ngoài
  `E:\Trading Tool_Smart DCA\`). Chủ dự án chọn phương án này để bắt đầu ngay; **không chống được mất
  máy/hỏng ổ đĩa vật lý** — chỉ chống được lỗi thao tác trong repo (xoá nhầm, `git clean -fdx`, hỏng
  working tree). Nâng cấp lên thư mục đồng bộ cloud (Google Drive/OneDrive…) là việc để sau, không
  chặn D0-PRE, ghi lại ở mục 4.
- **Chu kỳ:** chạy `--backup-to` thủ công sau mỗi lần niêm phong đoạn mới (segment gia hạn INCONCLUSIVE,
  tối đa 3 đoạn theo DR-011) — không có gì để backup thêm giữa hai lần niêm phong vì dữ liệu LOCKBOX
  bất biến sau khi ghi.

## 2. Cơ chế

`src/tool_d/lockbox/backup.py:backup_lockbox()` — sao chép nguyên vẹn `lockbox/lockbox_seal_*.json` +
`lockbox/data/` sang `<đích>/lockbox/`. **Không** sao chép `lockbox_access.log` (đó là sổ truy cập của
CHÍNH repo gốc — bản backup không phải một điểm truy cập, không tạo sự kiện chạm nào, đúng N8/DR-014).

CLI (`entrypoints/touch_lockbox.py`, E4):
```
--backup-to DIR      sao chép lockbox/ -> DIR/lockbox/ (ghi đè bản cũ)
--verify-backup DIR  verify_seal() trên DIR/lockbox/ — xác nhận bản backup tự nó khớp seal
```

Đây KHÔNG phải "chạm" (không đánh giá cấu hình nào, DR-014 mục 2) — không ghi sổ truy cập.

## 3. Test khôi phục THẬT đã chạy (06/09/2026, một lần, kết quả ghi lại)

1. `--backup-to E:/lockbox-backup-tool-d` (host Python — thao tác copy file thuần, không cần Freqtrade
   nên không bắt buộc Docker; N7 chỉ áp cho bằng chứng ĐO LƯỜNG/backtest, không áp cho thao tác vận
   hành thuần file I/O này) → 510 file, 39MB, khớp nguồn.
2. `--verify-backup E:/lockbox-backup-tool-d` → **PASS**, khớp 1 seal.
3. **Mô phỏng mất ổ đĩa gốc thật sự:** sao chép bản BACKUP (không phải bản gốc) sang một thư mục tạm
   hoàn toàn mới (`E:/lockbox-restore-test-tmp/`), chạy `verify_seal()` độc lập trên bản vừa khôi phục
   → **510/510 file khớp, danh sách lỗi rỗng = PASS**. Xoá thư mục tạm sau khi xác nhận (không phải
   backup — chỉ là bản dựng thử để kiểm chuỗi khôi phục có hoạt động).

Kết luận: chuỗi backup → khôi phục → xác nhận hoạt động đúng như thiết kế, trên dữ liệu LOCKBOX thật
(không phải seal giả trong `tmp_path`).

## 4. Còn để sau, không chặn D0-PRE

- Nâng cấp nơi lưu sang một vị trí chống được mất máy vật lý (cloud sync, ổ ngoài rời) — ghi lại làm
  việc mở, không tạo OQ mới vì không có quyết định kỹ thuật nào cần chốt thêm (`backup_lockbox()` nhận
  bất kỳ `dest_dir` nào, đổi nơi lưu chỉ là đổi tham số dòng lệnh).
- Tự động hoá lịch backup (hiện thủ công) — không cần thiết ở tần suất "một lần mỗi lần niêm phong
  đoạn mới", tối đa 3 lần trong đời một lockbox.
