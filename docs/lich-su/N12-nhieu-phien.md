# Lịch sử — N12 bản đầy đủ (kỷ luật git khi nhiều phiên cùng sửa một thư mục)

> Chuyển NGUYÊN VĂN từ `CLAUDE.md` ngày 25/09/2026 (`TD-0417`) khi chủ dự án chốt **một phiên duy nhất** trên repo.
> Muốn quay lại chạy nhiều phiên: đọc hết file này và khôi phục luật vào `CLAUDE.md` TRƯỚC khi mở phiên thứ hai.
> ⟲ **Đã khôi phục vào `CLAUDE.md` ngày 26/09/2026 (`TD-0429`)** — chủ dự án chọn quay lại nhiều phiên. Bản trong
> `CLAUDE.md` là bản hiệu lực; file này giữ làm lịch sử.


### N12 — 🔴 Kỷ luật git khi có 2 phiên cùng sửa một thư mục đĩa

Project này thường có **hai phiên Claude Code chạy song song trên cùng một thư mục** (không phải
worktree/branch riêng — quyết định của chủ dự án, xem TRẠNG THÁI HIỆN TẠI). `git add <file>` chụp
**toàn bộ nội dung file đang có trên đĩa tại thời điểm gọi**, không phân biệt được dòng mình vừa sửa
với dòng phiên kia đang gõ dở cùng lúc — đã gây ít nhất 3 lần một task bị đánh dấu ✅ giả trong
`TASKS.md` dù chưa có code thật (xem `docs/research-log.md`).

**Bắt buộc, cho MỌI lần commit đụng tới `TASKS.md` (hoặc bất kỳ file trạng thái dùng chung nào —
`CLAUDE.md`, `back-end-note.md`):**

1. **Không bao giờ `git add TASKS.md` (hay `git add -A`) ngay sau khi sửa** — luôn `git diff --
   TASKS.md` (hoặc `git diff --cached` sau khi add) và **đọc lại toàn bộ diff** trước khi commit.
   Diff phải khớp CHÍNH XÁC những gì mình chủ định sửa — không hơn, không kém.
2. **Thấy dòng lạ trong diff** (task khác đổi trạng thái mà mình không đụng tới) → đó là thay đổi
   của phiên kia đang dở, **không phải của mình**. Dùng `git reset TASKS.md`, sửa lại file bằng tay
   cho đúng ý mình (giữ nguyên dòng lạ đó ở trạng thái CŨ nếu chưa chắc phiên kia đã xong, hoặc xác
   minh bằng cách kiểm tra code/test thật có tồn tại không), rồi `git add` lại.
3. **Trước khi TIN bất kỳ dòng ✅ nào trong `TASKS.md`** (kể cả dòng do chính mình hay phiên kia ghi
   trước đó) khi nó là điều kiện phụ thuộc (`Phụ thuộc vào`) cho việc sắp làm — xác minh bằng
   **bằng chứng trên đĩa** (file/commit/test tương ứng có tồn tại thật không), không tin chữ ghi
   suông. Đây chính là cách cả 3 lần đánh dấu sai đã được bắt trong phiên trước.
4. Việc chỉ để KHOÁ (🔓→🔒) hay HOÀN TẤT (🔒→✅) một dòng: sửa **đúng một dòng**, commit **riêng**,
   không gộp chung với các file code khác trong cùng một `git add`.

5. 🔴 **Commit THẲNG theo tên file, đừng bỏ vào giỏ rồi gói** (thêm 07/09/2026 sau sự cố thứ 4):

   ```
   # File ĐÃ CÓ trong git (sửa file cũ) — không cần add:
   git commit -F <file-message> -- <đường/dẫn/file> [file2 ...]

   # File MỚI (chưa từng commit) — BẮT BUỘC add, và phải gộp CÙNG MỘT LỆNH:
   git add <file mới> && git commit -F <file-message> -- <file mới>

   git add <file> && git commit                     # ❌ SAI, kể cả khi add đích danh
   ```

   ⚠️ **`git commit -- <file MỚI>` mà chưa `add` sẽ BÁO LỖI** `pathspec did not match any file(s)`
   — pathspec chỉ nhìn được file git đã biết. Đây chính là chỗ dễ tưởng nhầm: sự cố `4ec0fd3` nuốt
   **hai file MỚI**, nên nếu chỉ nhớ mỗi dòng "không cần add" thì quy tắc này **không ngăn được
   chính sự cố sinh ra nó**.

   **Vì sao mục 1-4 ở trên KHÔNG đủ:** mọi phiên trên cùng thư mục dùng CHUNG một `.git/index`
   (kiểm bằng `git rev-parse --git-dir` — một `.git` duy nhất, không worktree riêng). `git commit`
   **không** gói "thứ mình vừa `add`" — nó gói **TOÀN BỘ index**. Phiên kia `git add` file của họ
   xong, đang soạn message; mình `git add` thêm file của mình rồi `git commit` → **gói luôn cả của
   họ**, dưới nhãn của mình. Phiên kia sẽ thấy `git commit` của họ báo *"nothing added to commit"*.

   Có pathspec thì `--only` là mặc định: git chỉ commit đúng những path đó lấy từ working tree,
   **bỏ qua phần còn lại của index** và giữ nguyên thứ phiên khác đang stage.

   **Quy tắc này bảo vệ MỘT CHIỀU — phải hiểu đúng chiều nào:**

   | | Có được bảo vệ không? |
   |---|---|
   | Mình **gây hại cho phiên khác** (nuốt file họ) | ✅ CHẶN ĐƯỢC, kể cả file mới (sau khi add) |
   | Mình **bị phiên khác hại** (file mình vừa `add` bị họ cuốn đi) | ❌ **KHÔNG** chặn được |

   Chiều thứ hai không có cú pháp nào đóng được: file mình vừa `git add` nằm trong index dùng chung,
   phiên khác chạy `git commit` không pathspec là cuốn luôn. **Chỉ thu hẹp được cửa sổ, bằng cách
   đổi THỨ TỰ LÀM VIỆC: soạn commit message TRƯỚC (ra file), rồi `add` và `commit` trong CÙNG một
   lệnh.** Sự cố `4ec0fd3` xảy ra đúng vì phiên kia `git add` xong rồi mới ngồi soạn message dài —
   cửa sổ mở hàng chục giây; nếu message đã sẵn thì nó chỉ còn vài mili giây.

   🔒 **Cách đóng HẲN** là mỗi phiên một index riêng (`GIT_INDEX_FILE`) hoặc worktree riêng — chủ dự
   án đã **cố ý chọn KHÔNG dùng worktree**, nên chấp nhận rủi ro còn lại là một quyết định có ý
   thức, không phải sơ suất. Ghi ra đây để không ai coi mục 5 là bùa hộ mệnh.

   ⚠️ **Cách này KHÔNG thay thế được mục 1.** `git commit -- <paths>` vẫn chụp **nội dung working
   tree** của chính path đó, nên với file dùng chung (`TASKS.md`, `CLAUDE.md`, `back-end-note.md`)
   thì hiểm hoạ gốc của N12 còn nguyên: **vẫn phải `git diff -- <file>` và đọc hết diff trước khi
   commit**. Pathspec chặn việc nuốt file LẠ; nó không chặn việc chụp nhầm DÒNG lạ trong file mình
   đang commit.

   📌 Sự cố `4ec0fd3` (07/09/2026): commit mang nhãn *"TASKS.md: TD-0127 hoàn tất"* nhưng nuốt kèm
   2 file code TD-0143 của phiên khác. Lệnh dùng lúc đó là `git add TASKS.md` — **đích danh đúng
   một file**, tức chẩn đoán ban đầu *"chắc do `git add -A`"* là SAI. Đối chứng: 9 commit khác cùng
   phiên, cùng kiểu `add` đích danh, đều sạch — khác nhau ở chỗ 9 cái kia có chạy `git diff --cached
   --stat` ngay trước khi commit. Bài học kép: (a) index dùng chung là cơ chế thật; (b) chẩn đoán
   theo **hình dạng hậu quả** thay vì kiểm **cơ chế** thì giả thuyết vẫn khớp hiện tượng mà vẫn sai
   — chi tiết trong `docs/research-log.md`.

6. 🔴 **Quy ước MỚI (09/09/2026, sự cố "hai `DR-D4-06`"): trước khi bắt đầu soạn một tài liệu
   quyết định mới (`docs/decisions/DR-*.md`, một mục `MT-*` mới), NHẮN phiên kia tên/mã dự kiến —
   cùng hạng với quy ước "nhắn trước khi chạy full suite".**

   ➡️ **18/09/2026: CƠ CHẾ của mục này được thay ở mục 7** (đặt chỗ bằng COMMIT, nhắn chỉ để báo). Lý do
   bên dưới giữ nguyên hiệu lực.

   Mục 1-5 ở trên chặn được việc **nuốt file** của phiên khác qua index dùng chung. Chúng **không**
   chặn được việc hai phiên **độc lập viết hai file khác tên cho cùng một quyết định**: hai phiên
   cùng phát hiện mâu thuẫn §1.3/§5.1 của TD-0189, cùng lúc, mỗi phiên tự đặt tên `DR-D4-06` cho
   file của mình. Cả hai commit đều **sạch** theo đúng nghĩa mục 1-5 (không file nào bị nuốt) —
   nhưng kết quả vẫn là **hai nguồn sự thật cho một quyết định**, đúng thứ N1/MT-03 (dự án Tool D)
   sinh ra để cấm. Sáu tháng nữa ai đó sửa một file, file kia vẫn nói bản cũ, không ai biết.

   🔑 **Vì sao đây là khoảng hở riêng, không phải một biến thể của sự cố cũ:** `4ec0fd3` là chuyện
   *một file, hai phiên cùng ghi* — index dùng chung là cơ chế, pathspec là thuốc. Sự cố này là
   chuyện *một Ý, hai file* — không có index nào nhìn thấy hai file khác tên đang mô tả cùng một
   thứ. **Giấy tờ quyết định không có cơ chế khoá nào tương đương 🔒 của `TASKS.md`.** Cả hai phiên
   trong sự cố đều hành xử ĐÚNG theo quy tắc 11 (thấy mâu thuẫn thì ghi, không tự chọn bên) — không
   ai sai, cơ chế thiếu.

   Phát hiện trùng SAU khi cả hai đã viết thì giải bằng tiêu chí đã dùng ở va chạm mã việc
   TD-0119/TD-0120 của project Tool D: **phía nào có ĐỊNH DANH MÁY ĐỌC được (đường dẫn file bằng
   chứng, tên hàm/biến code đã trỏ tới) thì phía đó không đổi** — phía kia gộp nội dung vào rồi
   xoá, không giữ cả hai.

7. 🔴 **Quy ước (18/09/2026, chủ dự án chốt): ĐĨA là trọng tài · VIỆC là địa chỉ · MÃ PHIÊN là chữ ký.**

   **Vì sao:** hậu tố tên phiên (`-a2`, `-93`…) **ĐỔI khi phiên khởi động lại**, và một tên cũ có thể được
   gán cho một phiên KHÁC. Đo 18/09: `-93` và `-2c` cùng là mã phiên `4168d1eb` (bền), nhưng tên `-a2` chỉ
   **HAI** mã khác nhau trong cùng một ngày (`55661c40` giữ Khối 26, `c95baba3` từng là `-13`) ⇒ tin nhắn
   gửi "`-a2`" rơi nhầm phiên. Tài liệu có ≈362 chỗ ghi tên phiên; ~15 chỗ dùng nó làm **địa chỉ** cho việc
   còn mở, và sau mỗi lần khởi động lại chúng trỏ sai người **mà trông vẫn đúng**. Năm sự cố cùng một gốc —
   dùng TIN NHẮN hoặc TÊN làm cơ chế thay vì ĐĨA: tin rơi nhầm phiên · va mã `TD-0304/0305` và `TD-0314`
   (18/09), "hai `DR-D4-06`" (09/09) · khoá mồ côi `TD-0216`/`TD-0247` · chờ một phiên đã không còn tên đó
   báo chạy xong suite · mục "Chia việc" cũ vẫn mang tiêu đề "hiện tại".

   a. **Mã phiên = 8 ký tự đầu UUID phiên** — chính là tên thư mục nháp
      `…/claude/c--Trading-Tool-Smart-DCA/<mã-phiên>/scratchpad` mà mỗi phiên được cấp. Bền qua khởi động
      lại. Tra ngược một tên cũ ra mã: `grep -l "This session is trading-tool-smart-dca-<xx> "
      ~/.claude/projects/c--Trading-Tool-Smart-DCA/*.jsonl`.
   b. **Commit khoá / hoàn tất / đặt chỗ mang dòng chữ ký `Phien: <mã phiên>`** (đặt trước
      `Co-Authored-By`). Ai giữ `TD-xxxx` tra được bằng máy:
      `git log -1 -G"^\| TD-xxxx \|.*\| 🔒 \|" -- TASKS.md` → commit gần nhất chạm dòng đang khoá → dòng
      `Phien:`. 🔴 *Đính chính cùng ngày:* bản đầu ghi `git log -S"TD-xxxx"` — **SAI**: `-S` chỉ bắt commit
      làm đổi **số lần xuất hiện** của chuỗi, mà commit khoá chỉ đổi 🔓 → 🔒 nên mã việc không đổi số lần
      ⇒ `-S` bỏ qua đúng commit cần tìm (đo trên TD-0306: `-S` trả `96f1b78`, `-G` trả commit khoá `0069ec8`).
      ⚠️ **Chỉ áp cho commit từ 18/09/2026.** Commit cũ **không** có dòng `Phien:` vì quy ước chưa tồn
      tại — **thiếu dòng `Phien:` KHÔNG phải bằng chứng khoá mồ côi**; với commit cũ, tra theo mã việc
      (cùng lệnh `-G` ở trên; nó vẫn tìm ra commit khoá cũ, chỉ không có dòng `Phien:` để đọc) rồi hỏi theo
      mã việc (phiên mã `95c7a7bf` nêu).
   c. **Đặt chỗ mã `TD`/`DR`/`MT` bằng COMMIT, không bằng tin nhắn:** ghi mã dự kiến vào `TASKS.md` ngay
      trong commit khoá (tiền lệ: Khối 26 đặt chỗ `DR-LOCKBOX-01` như vậy). **Ngay trước khi ghi**, chạy lại
      `git log --oneline -10` và tra mã cuối đã cấp — trạng thái đĩa lúc lập kế hoạch đã cũ. Vẫn nhắn để
      báo, nhưng **mã chỉ là của mình khi đã nằm trên đĩa**.
   d. **Không dùng tên phiên làm ĐỊA CHỈ trong tài liệu.** Chủ việc hiện tại = 🔒 + commit khoá. Tên phiên
      chỉ là nhãn lịch sử, kèm ngày (và mã phiên khi cần): *"phiên `-a2` (18/09, mã `55661c40`)"*. Muốn tìm
      người đang làm một việc: hỏi theo **mã việc** hoặc **mã phiên**, không theo tên chép từ file.
   e. **Tài nguyên dùng chung: ĐO, không chờ tin.** Trước khi chạy full suite: `docker ps` phải rỗng. Vẫn
      nhắn báo, nhưng không chờ ai xác nhận — phiên được chờ có thể đã không còn mang tên đó.
   f. **Khoá mồ côi** (🔒 mà không phiên nào nhận khi hỏi theo mã việc/mã phiên): phiên phát hiện **chỉ
      BÁO chủ dự án, không tự nhận**. Chủ dự án giao lại; commit giao lại ghi `Phien: <mã cũ> → <mã mới>`.
      File phiên `~/.claude/projects/c--Trading-Tool-Smart-DCA/<mã>.jsonl` lâu không cập nhật là **bằng
      chứng**, không phải giấy phép tự nhận.

   ⚠️ **Phạm vi:** ~300 chỗ tên phiên mang nghĩa **LỊCH SỬ / ghi công** giữ nguyên — chúng đúng tại thời
   điểm viết. Chỉ các chỗ đang làm địa chỉ cho việc còn mở được gắn chú thích mã phiên (18/09/2026).
