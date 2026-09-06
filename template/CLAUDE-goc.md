# CLAUDE.md — Quy tắc vận hành AI cho project này

> File này tạo ở Giai đoạn 2 của quy trình vibe-code. Copy từ `templates/CLAUDE-goc.md`, sau đó bổ sung quy tắc riêng của project (nếu có) bên dưới phần gốc.
> **File này phải đồng bộ với Mục 0 (Nguyên tắc nền tảng) của `quy-trinh-vibe-code.md`** — mỗi khi Mục 0 thêm/sửa nguyên tắc, file này phải cập nhật theo ngay, không được để lệch (xem quy tắc 13 bên dưới).

## Quy tắc gốc (áp dụng mọi project — không tự ý bỏ)

1. **Chỉ được viết mã nguồn khi người dùng gõ chính xác "bắt đầu code".** Trước đó, dù kiến trúc/kế hoạch đã chốt, vẫn chưa được code. (Nguyên tắc 1, 5)

2. **Không được tự quyết các quyết định thực sự phải chốt** — kể cả quyết định kỹ thuật thuần túy (thiết kế API, chọn kiến trúc, chọn database, chọn cấu trúc dữ liệu quan trọng...). (Nguyên tắc 9)
   - Với quyết định ảnh hưởng trải nghiệm người dùng / quy tắc kinh doanh / chi phí: phân tích lý do, so sánh đánh đổi (trade-off), đề xuất phương án tối ưu — trình bày bằng **ngôn ngữ hậu quả kinh doanh (Business Logic)**, không dùng thuật ngữ kỹ thuật, vì người dùng không rành code.
   - Với quyết định kỹ thuật bắt buộc phải chốt: vẫn phải phân tích + trade-off + đề xuất như trên, nhưng được dùng thẳng thuật ngữ IT chuyên ngành — người dùng vẫn xử lý được ở mức này.
   - Chỉ chi tiết triển khai nhỏ, không ảnh hưởng hành vi hệ thống (đặt tên biến, tổ chức file nội bộ, thư viện phụ trợ không có đánh đổi đáng kể) mới được tự quyết mà không cần hỏi.

3. **Đọc lại file cũ trước khi rà soát mâu thuẫn** — không suy đoán dựa vào trí nhớ tạm của phiên chat. Luôn đọc `back-end-note.md` + `ARCHITECTURE.md` hiện có trước khi so sánh với ý tưởng mới. (Nguyên tắc 3)

4. **Giới hạn phạm vi chỉnh sửa** — chỉ sửa phần trực tiếp liên quan đến yêu cầu; phần chưa chắc chắn đưa vào mục "Open Questions", không tự ý lan sang phần khác. (Nguyên tắc 4)

5. **Không tự sửa/xóa nội dung đã chốt trong file đặc tả** (`back-end-note.md`, `ARCHITECTURE.md`, `TASKS.md`, `tu-dien-du-lieu.md`, `provider-map.md`) — phát hiện sai/thừa/cần đổi thì ghi vào mục đề xuất riêng, chờ duyệt (theo Phụ lục B của quy trình chính).

6. **Gặp lỗi runtime:** phân tích nguyên nhân dựa trên log lỗi được cung cấp, sửa đúng file liên quan, không đoán mò khi thiếu thông tin.

7. **Tra `tu-dien-du-lieu.md` trước khi đọc/ghi bất kỳ trường database nào** — không suy đoán ý nghĩa từ tên trường hay từ code cũ. Nếu trường cần dùng chưa có trong từ điển, dừng lại và báo cho người dùng trước khi viết code, không tự đoán ý nghĩa.

8. **Bất kỳ thay đổi migration nào (thêm/xóa/sửa bảng hoặc trường)** — dù nhỏ đến đâu — đều bắt buộc cập nhật `tu-dien-du-lieu.md` + ERD trong `ARCHITECTURE.md` ngay lập tức, không dồn lại để sau. **Không được tự viết từ điển dựa trên trí nhớ đã viết migration gì** — phải xuất schema thật từ database (sau khi migration đã chạy) và đối chiếu khớp trước khi coi là cập nhật xong. Database thật luôn là chân lý — nếu lệch, sửa từ điển theo database, không phải ngược lại.

9. **Môi trường nhất quán (parity):** local – staging – production phải cùng cấu hình (cùng Dockerfile, cùng cấu trúc biến môi trường) — không viết code hay cấu hình chỉ chạy đúng ở 1 môi trường. (Nguyên tắc 7)

10. **Mọi thay đổi phải có khả năng rollback:** trước khi đề xuất/thực hiện deploy, phải xác nhận có đường quay lui về bản trước đó nếu lỗi (giữ image tag cũ, không xóa bản trước khi bản mới đã ổn định). (Nguyên tắc 8)

11. **Phát hiện mâu thuẫn phải ghi nhận, không tự ý âm thầm chọn 1 bên** — ở BẤT KỲ lúc nào trong quá trình làm việc (không riêng giai đoạn bảo trì), nếu thấy 2 quyết định đã chốt trước đó (trong `back-end-note.md`, `ARCHITECTURE.md`, hoặc giữa UI đã chốt và yêu cầu mới) xung đột nhau, phải dừng lại, ghi vào mục "Mâu thuẫn & Cần làm rõ" trong `back-end-note.md`, phân loại 🔴 (chặn tiến độ, dừng code ngay) hoặc 🟡 (ghi nhận, tiếp tục việc khác nhưng phải giải quyết trước go-live) — không tự chọn 1 bên rồi code tiếp. (Nguyên tắc 10)

12. **Provider AI/dịch vụ bên thứ ba phải được bọc sau lớp trung gian (adapter)** — không gọi thẳng từ nghiệp vụ chính vào provider. Xem `provider-map.md` để biết provider đang dùng cho từng tác vụ (danh sách, chi phí, dự phòng). Nếu gate check ở `api-integration-rules.md` (Mục 0, G1-G4) có ít nhất 1 `CÓ` — tức có bất kỳ lệnh gọi API/dịch vụ ngoài nào, không riêng AI — bắt buộc áp dụng toàn bộ 12 nguyên tắc kỹ thuật (R1-R12: single egress, rate limit, circuit breaker, phân biệt mã lỗi, bounded loop, kill switch, tách môi trường, log dedup, idempotency, quản lý secret, timeout, quota) trong file đó, không chỉ dừng ở việc bọc adapter.

13. **Đồng bộ với quy trình chính:** nếu người dùng cập nhật Mục 0 (Nguyên tắc nền tảng) của `quy-trinh-vibe-code.md`, phải cập nhật ngay các quy tắc tương ứng trong file này — không để 2 file lệch nhau.

14. **`TASKS.md` là backlog tổng bắt buộc mọi project, không riêng trường hợp nhiều người/tab.** Trước khi chọn việc để code (bước "chọn 1 module nhỏ nhất chưa làm" ở Giai đoạn 3), luôn mở `TASKS.md`, lọc dòng 🔓, ưu tiên việc không phụ thuộc hoặc phụ thuộc đã ✅ — không tự bịa việc cần làm tiếp theo từ trí nhớ tạm của phiên chat. Khi làm việc trong context nhiều người/tab song song: trước khi bắt đầu code 1 việc, bắt buộc đổi trạng thái việc đó từ 🔓 sang 🔒 trong `TASKS.md` và commit ngay — không code trước khi đã ghi nhận. Khi xong, đổi sang ✅.

15. **Gate-check bắt buộc trước khi dùng 3 form điều kiện** — không tự động điền cả 3 chỉ vì file có sẵn trong `/templates`:
    - `form-phan-quyen.md` → chỉ dùng nếu Giai đoạn 1 đã xác nhận project có nhiều loại người dùng/vai trò.
    - `provider-map.md` → chỉ dùng nếu project có gọi provider AI/dịch vụ bên thứ ba.
    - `form-sow-kpi.md` → chỉ dùng nếu đủ cả 3 điều kiện kích hoạt Phụ lục A (đã có pipeline đa-agent ổn định qua Giai đoạn 3–6, đã có đủ dữ liệu phản hồi thật, đã thử rule-based/heuristic và xác nhận không đủ).
    Nếu điều kiện chưa rõ, phải hỏi người dùng trước, không tự suy đoán rồi điền form.

16. **Ranh giới template gốc và file làm việc — không nhầm lẫn:** mọi file trong `/templates` (`form-xac-dinh-pham-vi.md`, `form-phan-quyen.md`, `provider-map.md`, `form-sow-kpi.md`, `back-end-note-cau-truc.md`, `CLAUDE-goc.md`, `tu-dien-du-lieu.md`, `TASKS.md`, `api-integration-rules.md`) là **khuôn mẫu gốc, chỉ đọc, không được sửa trực tiếp**. Khi cần dùng, copy nội dung/copy file thành bản làm việc tại root project (`back-end-note.md`, `CLAUDE.md`, `tu-dien-du-lieu.md`, `TASKS.md`, `api-integration-rules.md`...) rồi mới điền/cập nhật ở bản copy đó. Nếu phát hiện bản thân template gốc cần sửa (ví dụ thêm cột mới cho mọi project sau này), phải báo rõ cho người dùng đây là sửa khuôn mẫu dùng chung, không phải sửa riêng cho project hiện tại.

17. **Gate check `api-integration-rules.md` phải chạy ở Giai đoạn 1, không phải đợi đến lúc code.** Nếu G1-G4 có ít nhất 1 `CÓ` — kể cả chỉ gọi 1 API duy nhất, không cần "nhiều provider" như điều kiện của `provider-map.md` — phải hoàn thành Mục 2-4 của module (12 nguyên tắc + form khai báo) **trước khi** cho phép kích hoạt câu lệnh "bắt đầu code". Nếu người dùng gõ "bắt đầu code" nhưng module chưa hoàn thành, phải dừng lại, nêu rõ phần còn thiếu, không tự ý bỏ qua vì đã có lệnh kích hoạt.

18. **Nghiệm thu R1-R12 phải chạy trong context sạch, tách khỏi phiên code.** Khi review code có gọi API ngoài (Bảng nghiệm thu Mục 5 của `api-integration-rules.md`), chỉ được đọc code thật + bảng khai báo Mục 4 — không dựa vào lịch sử chat lúc Builder code phần đó, tránh thiên vị do đã "biết trước" ý định của chính mình. Mỗi dòng kết quả (PASS/FAIL/N/A) phải kèm bằng chứng cụ thể (đường dẫn file + số dòng), không kết luận chung chung. Đây là cùng nguyên tắc "clean-context reviewing" áp dụng cho mọi việc rà soát mâu thuẫn trong quy trình.

---

## Quy tắc riêng của project (bổ sung khi cần)

*(Để trống — điền khi project có yêu cầu đặc thù, ví dụ: quy ước đặt tên riêng, giới hạn công nghệ, ràng buộc nghiệp vụ đặc biệt...)*
