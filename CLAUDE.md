# CLAUDE.md — Quy tắc vận hành AI cho Tool D (Smart DCA)

> Tạo ở Giai đoạn 2 của quy trình vibe-code, ngày 06/09/2026.
> Phần "Quy tắc gốc" copy nguyên văn từ `template/CLAUDE-goc.md` — không tự ý sửa.
> Phần "Quy tắc riêng của project" bên dưới là bổ sung đặc thù cho Tool D.
> **Nguồn sự thật kỹ thuật của project này là `tool-d-smart-dca.md` (v8, ở gốc repo).**

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

## Quy tắc riêng của project — Tool D

> Các quy tắc dưới đây sinh ra từ chính đặc thù của Tool D: đây là **project nghiên cứu định lượng**,
> nơi sản phẩm không phải "phần mềm chạy được" mà là **những con số đáng tin**. Một con số sai
> không làm chương trình báo lỗi — nó chỉ âm thầm dẫn tới một quyết định sai. Toàn bộ PHẦN 0d
> của spec tồn tại vì lý do đó (Tool A đã dính ba lần).

### N1 — Nguồn sự thật, theo thứ tự ưu tiên

1. `tool-d-smart-dca.md` (v8) — spec kỹ thuật. **Không được chép nội dung sang file khác.**
2. `back-end-note.md` — chỉ chứa phạm vi, quyết định nền tảng, Open Questions, Mâu thuẫn, Lịch sử. Trỏ số § sang spec.
3. `ARCHITECTURE.md` — kiến trúc, cây thư mục, sơ đồ.
4. `TASKS.md` — backlog.

Mâu thuẫn giữa 4 file → spec thắng, và phải ghi vào mục 7 của `back-end-note.md`, không tự chọn một bên.

### N2 — 🔴 CẤM chạm dữ liệu thị trường trước khi cổng D0-PRE đóng

Spec dòng 4464: *"KHÔNG ĐƯỢC CHẠM DỮ LIỆU TRƯỚC KHI D0-PRE XONG"*.

"Chạm" định nghĩa theo DR-014 mục 2 = **đánh giá cấu hình** trên CALIB/WFO/LOCKBOX.
Đo thông tin mô tả (danh sách cặp, min notional, độ dài lịch sử OI) **không** tính là chạm,
nhưng vẫn phải ghi sổ dòng `CTRL` và chỉ được làm ở Khối 8 của `TASKS.md`.

Chưa có khoá `d0_pre_complete` trong `registry/runtime_state.json` (sinh từ một lần chạy thật,
không phải mock — L-Z51) thì mọi entrypoint phải **từ chối chạy**.

### N3 — 🔴 CẤM VĨNH VIỄN, không có ngoại lệ, không có "chỉ thử một lần"

| Cấm | Vì sao | Test canh |
|---|---|---|
| `hyperopt` (mọi hình thức) | 500 epoch = 500 phép thử, phá sạch ngân sách N=114 của DR-010. **Phát hiện một lần chạy → toàn bộ registry mất hiệu lực** | L-Z25 |
| `IntParameter` / `DecimalParameter` / `CategoricalParameter` / `BooleanParameter` / `RealParameter` | Mở cửa cho hyperopt và cho file `<Strategy>.json` ẩn | L-Z37 |
| FreqAI, Edge Positioning, `trailing_stop` dựng sẵn | §0c.2 | L-Z24 |
| Khung thời gian 15m | §3.3c đã xoá. Chỉ 1H chính, 4H/1D informative, 5m chỉ `timeframe_detail` | L-Z33 |
| `profit_ratio` trong tầng đo | DR-013: mọi chỉ số tổng hợp tính trên `pnl_abs` | L-Z46 |
| Thêm entrypoint thứ 9 | §0d.2 dòng 664: *"Không có E9 script thử nghiệm nhanh"*. Cần "xem thử" thì đó là E1 với `budget_line = B3` và **có ghi sổ** | L-Z36 |
| Đọc tham số Tầng B/C từ biến môi trường | §0d.4: env chỉ cho vận hành (khoá/mở, chế độ, đường dẫn) | L-Z39 |

### N4 — Mọi tham số đọc từ `config/tool_d_config.yaml`, không nơi nào khác

Đây là **nguồn sự thật duy nhất** cho tham số (§6.9.5). Không hardcode trong code,
không đọc từ env, không dùng cơ chế tham số của Freqtrade.

### N5 — Guard trước, việc tốn thời gian sau

Mọi entrypoint E1–E8 gọi `measurement_guard()` ở **dòng đầu tiên sau khi parse tham số**
(§0d.2 dòng 652). Gọi tường minh, **không bọc trong decorator** — L-Z36 kiểm bằng AST,
decorator làm test phải suy luận và dễ PASS giả.

### N6 — Không bịa số. Ba trạng thái, không gộp thành 0

§0d.6: mọi chỉ số chưa đo có trạng thái `pending`, đọc lỗi thì `unreadable`.
**Cấm** trả `0.0` khi chưa đo. **Cấm** giá trị lính canh (`-1`, `"UNKNOWN"`, `""`).
**Cấm** hiện số cũ kèm cảnh báo — thà để trống.

Ngưỡng gate chưa điền = `+inf`, không phải `None`, không phải `0.0` (L-Z35) —
để gate **không thể vô tình PASS**.

### N7 — Bằng chứng phải chạy trong Docker

Python trên máy là 3.14; Freqtrade cần 3.11–3.13 và không hỗ trợ Windows native.
Chỉ kết quả từ `docker compose -f docker/docker-compose.yml run --rm tests` mới được
coi là bằng chứng. Chạy pytest trực tiếp trên host là **tiện lợi khi soạn thảo,
không phải bằng chứng** — vì nó xác minh một môi trường không phải môi trường sẽ sinh số
(đúng hình dạng lỗi LD-04).

### N8 — Sổ trial là sổ nhật ký sự kiện, append-only tuyệt đối

Giải mâu thuẫn nội tại của spec (dòng 3706 "mỗi dòng một trial, cấm sửa dòng cũ"
vs dòng 3738 "state chuyển RESERVED→CONSUMED"): mỗi dòng `trial_registry.jsonl` là
**một sự kiện** (`RESERVE` / `SEAL` / `CONSUME` / `REFUND` / `CONTAMINATE`) mang cùng `trial_id`.
Trạng thái hiện tại tính lại bằng cách đọc hết sổ. **Không bao giờ sửa hay xoá một dòng đã ghi.**
Đã ghi vào mục 7 của `back-end-note.md`.

### N9 — Ba câu hỏi trước khi ghi file đặc tả (Phụ lục B.3), không bỏ qua

Trước khi ghi `back-end-note.md` / `ARCHITECTURE.md` / `tu-dien-du-lieu.md`, phải trả lời
**trong chat**: (1) mục nào giữ nguyên 100%, (2) mục nào đổi và đổi gì, (3) có mục nào bị xoá không và vì sao.
Câu lệnh kích hoạt ghi: **"chuẩn hóa và lưu"**.

### N10 — Chẩn đoán: "bot sai" hay "tầng đo sai"?

§0d.7. Khi thấy chỉ số bất thường, câu hỏi **ĐẦU TIÊN** — trước khi mở code chiến lược — là:
*"Lệnh THẬT trên sàn có đúng thiết kế không?"*, trả lời bằng dữ liệu lệnh thật đối chiếu Decision Log.
Khớp → lỗi tầng đo, **không đụng chiến lược**. Lệch → giờ mới mở code chiến lược.
Bắt buộc ghi `docs/research-log.md` mỗi lần chẩn đoán.

### N11 — Ánh xạ "Giai đoạn 4 Staging" của quy trình sang bot trading

Quy trình gốc viết cho web app trên Render. Tool D là bot chạy local. Ánh xạ đã chốt:

| Quy trình gốc | Tool D |
|---|---|
| Cùng 1 Dockerfile local–staging–prod | ✅ giữ nguyên |
| DB staging riêng | SQLite dry-run riêng, tách hẳn DB live |
| Image Preview trên Render | ❌ bỏ → dùng image **digest** local + tag git |
| "Test trên URL preview như production" | **Binance testnet** (D3.5, D10) → **dry-run** (D11) |
| Production | **D12 — vốn nhỏ** |
| Health check `/health` | Risk Supervisor §6.6 |
| Rollback về image tag cũ | ✅ giữ, nhưng phải qua DR-012 Hạng 1 |

**Giai đoạn 4 không áp cho D0-PRE.**

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

---

## TRẠNG THÁI HIỆN TẠI

**Cập nhật lần cuối: 06/09/2026**

> ⚠️ **Hai phiên Claude Code cùng làm việc song song trên repo này** (chủ dự án xác nhận).
> Mục này có thể lệch nhịp vài phút so với phiên kia — luôn `git log --oneline` +
> đọc lại `TASKS.md` (cột 🔓/🔒/✅) trước khi chọn việc tiếp theo, đừng chỉ tin mục này.

**Đang ở (cập nhật 09/09/2026, phiên `-f4`):** ✅ **TD-0182 ĐÓNG** — `7c06a8d` (code) +
`88eaf5f` (TASKS) + `10cb8f2` (research-log). Full suite **1400 passed, 0 failed**.

🔑 **KẾT LUẬN ĐO ĐƯỢC, GIỮ NGUYÊN QUYẾT ĐỊNH CŨ:** *"DG2 đọc chặt có giết tranche 3 không?"*
→ **KHÔNG.** Đo trên **48 mã alt EXPLORE** (0 trial, [T0,T2], dữ liệu THẬT): DG2 chặt **21,0%**
vs lỏng **22,2%** đủ ba tranche ⇒ giá của cách đọc chặt là **1,2 điểm phần trăm** ≈ một lệnh
trên 81. Không mở DR, không đụng `dg2_trend_con_dung()`. Kiểm có răng: DG2 chặn ở tranche 2 rơi
**16 → 0** khi nới.

🔴 **HAI CON SỐ VỀ HỆ THỐNG, PHẢI ĐỌC KÈM MỌI KẾT QUẢ D4** (không phải về fixture):
**chỉ ~21% lệnh bơm đủ ba tranche, 41% dừng ở MỘT tranche** — ablation D4 sắp đo một cỗ máy DCA
mà tranche 2/3 hiếm khi xảy ra. Và **DG4 (trần chờ 8 nến 1H) chặn nhiều gấp bảy DG2**. ⚠️ Nhưng
tỉ lệ theo *lần xét cổng* **thổi phồng cổng DAI** (hết cửa sổ rồi thì mọi lần hỏi sau đều chặn)
và **làm nhẹ cổng THOÁNG QUA** — con số đáng tin là phân bố theo LỆNH. `dg4_bars_1h` là `tier_b`
**chưa hề calibrate** (TD-0190: 12/12 đều là chỗ giữ).

🔑 **HÌNH DẠNG LỖI THỨ TƯ — bộ sinh dữ liệu LỖI THỜI so với hệ thống nó nuôi.** Ba cái đã ghi:
*lớp canh cùn* · *chĩa nhầm hướng* · *người bị canh tự chọn phạm vi*. Cái mới: **không ai viết
sai dòng nào** — fixture đúng với hệ thống CŨ, im lặng sai với hệ thống MỚI, và im lặng theo
hướng nguy nhất là **0 lệnh** (mọi khẳng định về lệnh đều **đúng-vô-nghĩa**). Fixture cũ khớp đủ
3 tranche do **TRÙNG HỢP**: hệ thống cũ không lọc trend nên lệnh mở lúc 4H đang DOWN ⇒ `t4=DOWN`
⇒ DG2 so `DOWN==DOWN` cho qua. Tức **nó nghiệm thu cỗ máy DCA bằng một lệnh mà hệ thống mới sẽ
không bao giờ mở**.

📌 **Bẫy PASS RỖNG cụ thể nhất từ trước tới nay, tự tạo rồi tự bắt:** ca `test_enter_tag_...`
chép hằng số `"2025-01-01"` (lần thứ BA trong file) để đổi giờ ra chỉ số nến. Kéo dài lịch sử
làm chỉ số trỏ vào **nến 513, giá 44,30 — cách nến tín hiệu 60 NGÀY** — mà **vẫn XANH** vì nến
sai tình cờ cũng `UP`. Chỉ số đúng: 873, giá 96,90. Vá bằng `_moc_bat_dau()` suy từ ĐUÔI.

🐛 **Ba lỗi chỉ lộ trên dữ liệu THẬT:** (i) `zone_valid_4h` mang `NaN` ở vùng warmup ⇒ pandas từ
chối mảng có `NaN` làm mặt nạ ⇒ backtest **CRASH**; (ii) bug TD-0093 tái hiện y nguyên —
`download-data --timerange` **không tôn trọng mốc kết thúc**, **10/10 file** lấn quá T2, hai file
`1d`/`funding_rate` chạy tới **2026-09-07/08** (sâu 7 tháng vào LOCKBOX); (iii) **BTC/ETH không
định cỡ nổi một lệnh nào** ở `E_D = 500` — 48+24 `SizingError`, xác nhận độc lập cho TD-0082.

🔑 **BÀI HỌC LỜI KHAI — cùng cái bẫy TD-0041, ở chỗ THỨ BA.** Tôi chuyển mô tả TD-0082 (*"chưa
chia đòn bẩy"*) cho phiên `-94` **như thể đã kiểm chứng**; họ đo lại và bác: `min_stake` đã chia
đòn bẩy, `stake` ta cũng chia, **hai vế cùng chia nên đòn bẩy triệt tiêu**. N12 mục 3 dạy đừng
tin ✅ trong `TASKS.md`; CLAUDE.md đã ghi *"một dòng trạng thái có ngày tháng trông giống sự thật
hơn một cái ✅"*. Nay thêm: ***một dòng MÔ TẢ VIỆC cũng là lời khai, không phải bằng chứng.***

⚠️ **Phạm vi, đừng đọc quá tay:** 72 exception BTC/ETH là bằng chứng **CƠ CHẾ**, không phải vi
phạm của pool — BTC/ETH **không nằm trong pool giao dịch** (§0.3b). Con số alt là **17/81 trên 48
mã EXPLORE**; **chưa ai đo** con số cho pool 102 mã.

📂 Dữ liệu EXPLORE ở `user_data/data/explore/` (đã `.gitignore`), **tách hẳn** thư mục 102 mã pool
để ràng buộc *"EXPLORE không rò vào pool"* nằm ở **tầng thư mục** chứ không ở kỷ luật con người.
Tải không tiêu trial (DR-014 chỉ tính *đánh giá cấu hình*); đã cắt và kiểm nằm trọn [T0,T2].

⏳ **Còn treo:** ghi **MT mới** vào `back-end-note.md` mục 7 — khoảng hở giữa *"đo mô tả được phép
trên CALIB"* (N2) và *"`CTRL_OUTPUT_ALLOWED` chỉ nhận 3 trường của DR-015"* (`registry.py:33`):
hai quyết định đã chốt va nhau, quy tắc 11 buộc ghi nhận. Phân loại 🟡 — không chặn việc vừa rồi
(đã đi đường EXPLORE) nhưng **sẽ chặn ca đo mô tả tiếp theo trên dữ liệu pool**. Chờ lệnh
"chuẩn hóa và lưu" (N9).

*(Đoạn "Đang ở" cũ bên dưới giữ nguyên làm lịch sử.)*

**Đang ở (cập nhật 09/09/2026, phiên TD-0171):** ✅ **TD-0171 đóng — `DR-D4-05` chốt, `E_D` 500 → 750.**
Mở lại TD-0082 vì bảng cũ (*"102/102 qua, KHÔNG có vi phạm"*) so **cỡ lệnh tính sai** với **sàn tính
sai**, và cả hai lệch **cùng một chiều — chiều nói "qua"**: tử số dùng `rho` thô (cỡ lệnh thật mang
`Π mult_* ≤ 1`, §6.2), mẫu số dùng `MIN_NOTIONAL` trần trụi (sàn thật còn nhân hệ số dự trữ, và có
vế `minQty × giá` mà code **chưa từng đọc** — nó là vế quyết định ở BTC). Đo lại trên metadata sàn
THẬT (0 trial): **4/102 mã rớt ngay ở ca TỐT NHẤT** (BCH/ETC/LINK/LTC). Full suite **1406 passed**.

🔴 **PHÁT HIỆN LỚN HƠN CON SỐ — backtest và live KHÔNG dùng cùng một sàn, lệch HAI CHIỀU NGƯỢC NHAU.**
Freqtrade truyền một `stoploss` **khác nhau** cho từng đường chạy (backtest vào lệnh `-0.05` hằng số
trong mã; phần dư `-0.1` không truyền `leverage`; live thì `strategy.stoploss`). Vào lệnh: live 7,50
vs backtest 5,53. Phần dư: backtest 5,83 vs live 2,50. Ở `Π mult_* = 0,326` zone 3% thì **backtest
cho 94/102 mã vào lệnh, live cho 0/102** — cùng cấu hình, cùng pool, cùng ngày. Đây là lỗ hổng
**parity (quy tắc 9)**, nên `DR-D4-05` chốt Tool D **tự tính MỘT sàn = `max` mọi đường chạy** thay vì
dùng sàn của đường đang chạy: lấy đúng từng đường thì D4 và D11 vẫn hành xử khác nhau, chỉ khác là ta
biết về nó. Giá phải trả (chặt hơn Freqtrade ở vài đường) chấp nhận có ý thức.

🔴 **Và lệnh dưới sàn BIẾN MẤT IM LẶNG:** `backtesting.py:1173` là một `if` **không có `else`**; phần
dư ở `:774` cũng `return trade` không log. Phiên `-f4` chứng kiến **72 lệnh mất** trên một lượt
backtest báo *thành công*. Vì thế `kiem_san_tool_d()` trả **lý do đọc được**, không trả `bool`.

🔑 **BÀI HỌC ĐẮT NHẤT, và nó TỰ LẶP LẠI BA LẦN trong chính đợt này: một con số đo đúng MỘT LẦN rồi
được đọc như thể LUÔN đúng.** (1) bảng `102/102` của TD-0082; (2) giả định *"config ghi `stoploss =
-0.99` thì Freqtrade dùng −0,99"* — backtest **hardcode `-0.05`**, tôi phải đính chính bản đo của
chính mình sau một giờ; (3) ba khẳng định `1.875` / `425.0` / `40.0` đóng băng trong test, đúng lúc
viết và **im lặng hết đúng** khi Tầng A đổi — mà Tầng A là tầng *"chỉnh tự do"*, tức nó **sẽ** đổi.
**Cách chữa KHÔNG phải cập nhật số, mà là TÁCH ghim QUAN HỆ khỏi ghim QUYẾT ĐỊNH:** quan hệ
(`planned_risk == rho × E_D` đọc từ YAML) đúng ở mọi `E_D` và vẫn bắt lỗi thật vì đường tính của code
khác đường của test; còn con số bị ghim **đúng MỘT chỗ**, nơi dòng `assert` **nêu đích danh DR** — đổi
`E_D` vì thế buộc phải sửa một dòng có nhắc tới quyết định, không phải một hằng số vô danh. Kiểm có
răng ba lần: bỏ hệ số dự trữ → 8 đỏ · phá `max` → 3 đỏ · trả `E_D` về 500 → **đúng 1 đỏ, đúng ca ghim
quyết định**, ca ghim quan hệ vẫn xanh.

📌 **`E_D` = 750 chứ KHÔNG phải 720 như tôi đề xuất đầu:** ở 720, tranche 1 zone 3% ra **đúng 30,00**
trong khi sàn của 4 mã kia cũng **đúng 30,00**. Một chốt thoả bằng **đẳng thức chính xác** là chốt
không có lề, và nó sẽ lật **im lặng**. Hệ quả tiền bạc đã trình và được duyệt: rủi ro mỗi lệnh
1,875 → **2,8125 USDT (+50%)**, trần lỗ ngày xấu 40 → 60; số lệnh tối đa cùng lúc **không đổi**.
Đây là **mở lại quyết định `DR-D0PRE-06` mà chủ dự án đã chủ động chọn khác** (tôi từng khuyến nghị
≥ 1.000, chủ dự án chọn 500) — thông tin MỚI không phải *"tôi vẫn muốn số to hơn"* mà là quyết định
đó dựa trên bảng `102/102` nay biết là sai. Đã gắn đính chính vào `DR-D0PRE-06`, **giữ nguyên chữ
cũ** vì nó ghi lại thứ chủ dự án đã NHÌN THẤY khi quyết.

⚠️ **CHƯA nối vào chiến lược.** `san_tool_d()`/`kiem_san_tool_d()` mới là tầng thuần; `ZoneAbsorption`
chưa gọi. Phiên `-2f` dùng nó ở TD-0189. **Còn treo:** danh sách 17 mã rớt trên tập alt EXPLORE
(phiên `-f4` sẽ gửi) để đối chiếu **tập DỰ ĐOÁN rớt** với **tập THỰC SỰ rớt** — lệch mới là thứ đáng
giá, vì nó nghĩa là còn một vế nữa của sàn chưa đọc ra. Và **chưa ai đo** con số cho pool 102 mã trên
lệnh thật (vướng ngân sách trial).
*(Đoạn "Đang ở" cũ bên dưới giữ nguyên làm lịch sử.)*


**Đang ở (cập nhật 08/09/2026, phiên mở D4):** 🚪 **D4 ĐÃ MỞ — Khối 16 (TD-0180…TD-0186).**
**TD-0180 ✅** — `docs/decisions/DR-D4-01-pham-vi-va-ke-toan.md` (`df011da`), commit **RIÊNG và
TRƯỚC** mọi dòng mã arm. Chủ dự án chốt: **(a) Long trước, 9 trial** (Short hoãn CÓ ĐIỀU KIỆN);
**(b) xác nhận tiêu B2**, 9 trên 110 suất còn lại. Full suite **1186 passed, 0 failed** (7:56).

🔴 **PHÁT HIỆN LỚN NHẤT KHI MỞ KHỐI: D4 phần lớn là DỰNG arm, KHÔNG phải chạy arm.** Tên khối
*"Ablation"* gợi ý sai rằng việc còn lại là bấm nút. Đối chiếu §10.1/§10.1b với mã ngày 08/09:
**DG1–DG5 không có một dòng nào**; Z1/Z2/Z0-V1/Z0-S1 chưa có công tắc; Phần 2 và §3.3b có module
nhưng **chưa nối vào tín hiệu vào lệnh**. Chính docstring `ZoneAbsorptionMinimal` đã tự khai điều
này — không ai giấu, chỉ là không ai đọc.

🔑 **Vòng lặp Short, và vì sao KHÔNG phá bằng cách nới chốt:** `L-Z56` từ chối chạy nếu
`enable_short: true` mà thiếu Δ_R(SHORT); Δ_R(SHORT) lại cần lệnh Short để đo; chiến lược đang
LONG-only. Nới `L-Z56` = chạy arm Short trên một thước chưa từng kiểm cho hướng Short, đúng trạng
thái DR-015 §1 gọi là *"tệ nhất có thể"*. **Chốt đang chặn thì không được gỡ vì nó đang chặn.**
Đường đã chọn (spec §3.3d cho phép bằng chữ): Long trước, kèm **ba điều kiện mở lại viết TRƯỚC**
(khuôn OQ-07) — chỉ điều kiện 2 có máy canh; §7 của DR ghi ba dòng ❌ để không ai coi `L-Z56` xanh
là đủ. 🔴 Kết luận D4 đợt này **chỉ có giá trị cho LONG**, phải ghi vào `d4_han_che` khi đóng cổng.

🔴 **`Z0-T2` KHÔNG phải arm thứ 10 — nó CHÍNH LÀ `Z0`** (§10.1b: *"không tốn trial thêm"*). Chín
cấu hình, không phải mười. Đếm nhầm là tiêu thừa một suất thật. Có test ghim ở `arms.py`.

**TD-0182 làm DỞ, có lý do:** `d87203a` — `src/tool_d/arms.py` + test khoá (**15 passed**), ba tầng
`KHONG`/`CHI_4H`/`DAY_DU`. Phần **nối vào tín hiệu vào lệnh CHƯA làm**, bị chặn bởi **MT-15**.
Hai điểm thiết kế: (i) `CHI_4H` cố ý **KHÔNG** gọi `xac_nhan_da_khung()` — hàm đó so 1D với 4H,
tức nó CHÍNH LÀ tầng 1D mà Z0-T1 đang bỏ; giữ lại thì arm không đo được thứ nó sinh ra để đo
(diễn giải, đã ghi docstring để cãi lại được); (ii) khoá `tier_c.arm_ablation` **chưa thêm** vào
YAML — thêm bây giờ là một khoá không ai đọc.

🔴 **MT-15 — bẫy PASS RỖNG ở một dạng CHƯA từng gặp: nó không làm hỏng phép đo, nó ĐỐT NGÂN SÁCH.**
`entry_confirmation.py` + test khoá `L-Z6` thi hành `(a) HOẶC (b)`; spec PHẦN 3b (dòng 1289–1317)
đòi `(a VÀ c) HOẶC (b)` và dòng 1115 gọi (c) là *"BỔ NGỮ **BẮT BUỘC** cho (a)"*. Điều kiện (c)
volume có **0 dòng code**, `v_min` vẫn `null` (OQ-06). Hệ quả nặng nhất **không phải** thiếu một
bộ lọc: §10.1b định nghĩa `Z0-V1` **đúng bằng "tắt (c)"**, tức `(a) HOẶC (b)` — chính là thứ code
đang có ⇒ **`Z0` TRÙNG KHỚP `Z0-V1`**, một suất trial trong 114 tiêu để đo khác biệt **bằng
không**, và bảng kết quả trông hoàn toàn bình thường, chỉ là hai cột giống hệt nhau. **Không phép
kiểm nào hiện có báo đỏ vì nó.** Để **chờ** theo quy tắc 11 (sửa = phải đổi một test trong
`tests/lock/`). **MT-14** ghi nợ đặc tả từ D3.5: Bước 2 đo KHÔNG trên testnet, lệch chữ spec dòng
39/2975 — đã chốt TRƯỚC khi đo bằng `DR-D35-01`, kèm giá phải trả.

🔴 **BÀI HỌC N12 Ở MỘT CHỖ QUY TẮC CHƯA NÓI TỚI — chính mục này lừa được hai phiên.** Câu *"Chặn
thêm bởi TD-0041… vẫn cần chủ dự án quyết"* ở cuối đoạn D3.5 **SAI** (TD-0041 đóng từ 06/09,
`ba2af6a`), và **cả tôi lẫn phiên `-d8` đều tin nó** cho tới khi kiểm đĩa. N12 mục 3 dạy đừng tin
chữ ✅ **trong `TASKS.md`** — thứ lừa được cả hai là một **câu văn xuôi trong `CLAUDE.md`**, nơi
không có cột trạng thái nào để mà nghi ngờ. **Một dòng trạng thái có ngày tháng trông giống một sự
thật hơn là một cái ✅.** Đã gắn đính chính tại chỗ thay vì xoá.

✅ **MT-15 ĐÃ THI HÀNH** (`DR-D4-03` `8046a27` + vá `942efe7`, chủ dự án chốt phương án C):
`v_min = 1.0` **FROZEN, ĐÓNG BĂNG TẠI CHỖ** — giữ trong `tier_b` nên `|tier_b|` vẫn 12, **N vẫn
114**, rào DSR vẫn **3,0777**. Docker **1217 passed, 0 failed**; +17 ca, −0 ca; phá thật trên
**file sản xuất** ra đúng 1 ca đỏ. OQ-06 ✅ đóng. ✅ Cache 599 MB đã xoá.

🔑 **Ba bài học của đợt MT-15, đáng nhớ hơn bản vá:**
1. **Cùng một động tác, hai hậu quả trái ngược.** Đóng băng DG5 (`dof: 0`) giữ N = 114; đóng băng
   `v_min` theo cách đó lại hạ N xuống 108 và **rào DSR xuống 3,0601** — vì `dof.py:91` tính N từ
   số khoá THẬT trong `tier_b`. Phân biệt bằng đúng một câu: ***"thứ này đã nằm trong 12 chưa?"***
   Rào thấp xuống = dễ qua cổng hơn; một quyết định chọn cho tiện mà nới chuẩn của chính mình.
2. 🔴 **BẪY PASS RỖNG THỨ NĂM — và khác bốn cái trước ở chỗ nó DO CHÍNH HÀNH ĐỘNG SỬA TẠO RA.**
   `check_lz15` chỉ soi tham số `tier_b` đang `null`, nên **khoảnh khắc ghi `1.0` vào là nó thôi
   canh `v_min`**. Vá xong mà không siết thì tự làm câm lớp canh duy nhất theo dõi tham số đó.
3. **Nỗi lo "phải phá một test khoá" hoá ra SAI.** 5 lời gọi cũ giữ NGUYÊN khẳng định, chỉ thêm
   `bat_dieu_kien_c=False`, và **trở thành test khoá cho chính arm `Z0-V1`** — vì `(a) HOẶC (b)`
   đúng là định nghĩa `Z0-V1`. Thứ trông như phá một test khoá hoá ra là **đổi nhãn nó về đúng
   arm mà nó vẫn luôn mô tả**.

✅ **TD-0181 · TD-0169 · TD-0183 đóng (phiên `-f6`).** **TD-0181** — DG1–DG5 (§4) nay có
máy: năm hàm THUẦN + 45 test; DG4 đọc `dg4_bars_1h` từ cấu hình (N4) và **KHÔNG dùng chung hằng
số với DG6** (`dg6b_bars_1h` là 🔒 `dof: -1`, gộp lại là biến tham số đóng băng thành tune được).
**TD-0169 / DR-D4-02** — ngưỡng 30% của DG5 là **bậc tự do không ai đếm** (không có trong config,
không có dòng nào trong kiểm kê DOF); chủ dự án chốt **đóng băng**, `dof: 0`, **N giữ 114**, rào
DSR **3,0777**, **0 trial**. 🔑 **Phân biệt phải nhớ, hai phiên cùng rút ra:** đóng băng một thứ
**chưa từng được đếm** thì không trừ gì (DG5); đóng băng một thứ **đã nằm trong 12** thì thật sự
rút một bậc khỏi mẫu số và **NỚI** rào DSR (`v_min`, DR-D4-03). Cùng động tác, hậu quả trái ngược
— câu phân biệt là *"thứ này đã nằm trong 12 chưa?"*. **TD-0183** — công tắc arm **rút gọn 2,5/4**
(`arm_switches.py` + 27 test): Z1 (SL `p1 − 2,2×ATR`, `r_eff_plan` **tính lại**) · Z0-S1 (không
chia `R_eff`) · nửa Z2 (bỏ đúng DG5). **KHÔNG** làm Z0-V1 (MT-15) và vế *không `mult_zss`* — tắt
thứ chưa bật là **cờ chết**, có test ghim để chúng không lặng lẽ quay lại. Full suite **1244
passed, 0 failed**.

🔑 **Bài học đo lường của phiên, đắt và đáng giữ:** một lượt suite ra **16 ca đỏ** hoá ra là
**nhiễu chéo** — hai container pytest chồng nhau kéo 7:47 → **21 phút**; chạy riêng thì xanh hết.
🔴 Chẩn đoán đầu của tôi (*"phiên kia sửa file"*) **SAI VỀ CƠ CHẾ**: hai commit trong cửa sổ đó là
`.md`, mà **pytest không thu `.md`** — đúng lại bài học kép của `4ec0fd3` (chẩn đoán theo *hình
dạng hậu quả* thay vì kiểm *cơ chế*). Hai quy ước sinh ra từ đây, cả hai phiên đang giữ:
**(1)** ai sắp chạy full suite thì **nhắn trước**, người kia xác nhận rồi mới chạy; **(2)** ⚠️
**giữ TRỌN output rồi mới lọc** — cả hai phiên đều dính bẫy `docker compose … | tail -N`, lượt nào
đỏ là **mất sạch chi tiết lỗi**, không truy được ca nào.

🔴 **MT-16 — CHẶN CỔNG D4, chưa giải, chờ chủ dự án: KHÔNG CÓ TẦNG ĐỊNH CỠ LỆNH.**
`custom_stake_amount` (§6.8e) **0 dòng code** toàn repo; 5/6 hệ số §6.2 **0 dòng**. Đo trên
artifact D3.5 **đã niêm phong**: cỡ lệnh **39,98 USDT hằng số** (thiết kế: 62–208, biến theo
`R_eff`), tỉ trọng **¼-¼-½** thay vì `[⅓,⅓,⅓]` mà `trade_plan.py:21` ghi *"ĐÓNG BĂNG"*.
🔑 **Bằng chứng mạnh nhất là một dòng chú thích TỰ CHỨNG MINH MÌNH SAI:** `config.json:11` viết
*"giá trị 10 không bao giờ thật sự được dùng"* vì `custom_stake_amount()` sẽ ghi đè — hàm đó
chưa bao giờ được viết. **Đặt tên theo GỐC, không theo triệu chứng** (*"thiếu `mult_zss`"* sẽ
khiến người sau vá `mult_zss` rồi tưởng xong). ⚠️ **Chi phí phải biết TRƯỚC khi quyết:** dựng
tầng định cỡ ⇒ `planned_risk` đổi ⇒ **phải ĐO LẠI Δ_R**, tức mở lại artifact niêm phong của D3.5.

✅ **ĐÃ QUYẾT — `DR-D4-04` (`e5138ec`), và chủ dự án BÁC cách tôi đóng khung.** Tôi trình *"có đưa
tầng định cỡ vào phạm vi không"* như một **lựa chọn** kèm chữ "nghiêng". Sai: §10.2 phán quyết
bằng expectancy **theo R**; không định cỡ theo rủi ro cố định thì *"1 R"* trôi theo từng lệnh và
con số phán quyết **không có đơn vị**. Chốt: dựng **`ZoneAbsorption.py`** (file MỚI, sản xuất;
Minimal giữ nguyên làm fixture `L-Z49`), **bảy tầng BẮT BUỘC**, thứ tự **định cỡ TRƯỚC**.

**TD-0187 ✅** (`c0ba7a0` `sizing.py` + `bfe01ed` chiến lược): full suite **1288 passed, 0 failed**.
Đo trên **FILL backtest THẬT**: tỉ trọng **1 : 1 : 1** (MT-16 là 1:1:2) · `leverage = 3` (trước:
1x) · `stake × L == cost` · cỡ lệnh biến theo `1/R_eff`. Phá thật (trả `trade.stake_amount` về)
→ **đúng 3 ca đỏ**. Còn **TD-0188** (kết nạp §6.8f B2), **TD-0189** (TP = MT-17), TD-0182 phần nối.

🔴 **BA LỖI CHỈ LỘ RA KHI ĐÒN BẨY THÀNH THẬT — MT-16 (v)(vi)(vii), đọc trước khi động vào chiến lược:**
1. **Không file nào cài `leverage()`** ⇒ Freqtrade mặc định **1x** ⇒ mọi backtest tới 08/09 chạy
   1x, không phải `L_exchange = 3`. Kéo theo **`L-Z3` (đệm thanh lý) CHƯA TỪNG bị thử thách** —
   ở 1x không có thanh lý. Một cổng an toàn chưa bao giờ có cơ hội đỏ.
2. **SL bị NHÂN đòn bẩy — bug sống từ D1, vô hình ĐÚNG VÌ tầng đòn bẩy chưa tồn tại.**
   `ZoneAbsorptionMinimal:256` trả `(kh.sl / current_rate) − 1`; Freqtrade hiểu đó là *rủi ro trên
   vốn ĐÃ NHÂN đòn bẩy*. Ở 3x SL thật gần **gấp BA** kế hoạch — đo được **38/38 lệnh nổ stop
   trong vài phút, ở giá CAO HƠN `sl`**. Dùng `stoploss_from_absolute(..., leverage=)`.
3. **Freqtrade NUỐT exception của callback.** `strategy_safe_wrapper` hạ mọi lỗi thành WARNING rồi
   đi tiếp, `rc = 0` — `SizingError` fail-closed bị nuốt 12 lần, lệnh mẫu biến mất trong im lặng.
   **Một chốt fail-closed bị nuốt là một chốt KHÔNG TỒN TẠI** — PASS RỖNG ở tầng framework, không
   phép kiểm nào của dự án nhìn thấy. Test khoá TD-0187 nay **CẤM** dòng log đó; TD-0184 phải kế thừa.

🔴 **Lookahead ở CALLBACK — mặt cắt `H4-D` KHÔNG phủ:** `dp.get_pair_dataframe()` gọi từ callback
trả **toàn bộ** dữ liệu kể cả nến TƯƠNG LAI (chỉ `get_analyzed_dataframe()` mới bị cắt). DG1/DG2/DG5
phải đi qua `_df_4h(pair, current_time)` cắt `date + 4h ≤ now`. Test khoá riêng: phiên `-f6` nhận.

🔑 **BÀI HỌC LỚN NHẤT NGÀY 08/09 — NĂM lần suy luận nghe hợp lý bị một phép đo dưới một phút bác:**
*"phiên kia sửa file"* (thật ra là hai container chồng nhau) · *"phải đo lại Δ_R"* (Δ_R **bất biến**
với cỡ lệnh tới bit cuối — câu sai này đã **lan qua hai phiên** trước khi có ai đo) · *"biên DG4"*
(DG4 cho qua 71% số ca) · `mult = 1` (thật ra `mult_zss ≈ 0,62`) · `t4 = "UP"` (thật ra `DOWN`).
**Câu chặn, dùng từ nay:** *"đại lượng này có NHÌN THẤY thứ tôi sắp đổi không?"* và *"đo rẻ hơn đoán"*.
Hai ca cuối là **giả định của TEST sai, không phải máy sai** — xử bằng cách đổi giả định thành
**phép đo**, không sửa số cho khớp. Đó là ranh giới giữa *sửa test* và *nới test*.

⏳ **Còn chờ chủ dự án:** (1) `tp1_haircut_pct = 20` — có giá trị, **không có trạng thái** trong
`param_status.yaml`; TUNED hay FROZEN, quyết **trước khi TD-0189 chạy**; (2) phương án cho **`L-Z15`
mở rộng phạm vi** của phiên `-f6` (**11/12 tham số `tier_b` đang "im lặng"**, sẽ làm suite đỏ 22 ca
— *"đỏ nói thật"*); (3) **mở lại `TD-0082`** (min-notional chưa nhân `mult_*`/chia đòn bẩy).

**Chia việc đang chạy:** phiên này **TD-0182**; phiên `-d8` **TD-0181** (DG1–DG5). TD-0183 phụ
thuộc CẢ HAI — ai xong trước cũng phải hỏi trước khi nhận.
*(Đoạn "Đang ở" cũ bên dưới giữ nguyên làm lịch sử.)*

**Đang ở (cập nhật 08/09/2026, phiên D3.5):** 🚪 **D3.5 ĐÓNG — tag `d3-5-complete`.** Khối 15
xong sạch: **TD-0160…TD-0167 đều ✅**. Chạy thật qua service **`freqtrade`** (`E6 --close-d3-5-gate`,
exit 0): `full_suite` **1102 passed** · năm file test cốt lõi mỗi file chạy RIÊNG (Bước 1 **23** ·
Bước 2 **33** · Bước 3 **14** · L-Z58 **28** · L-Z56 **14**) · audit **5/14 đạt, 0 chưa đạt**.
`d3_5_git_sha` khớp đúng HEAD; chạy lại → exit **94**. **Năm cổng đã đóng:** `d0-pre` → `d1` →
`d2` → `d3` → `d3-5`.

🔑 **Thiết kế đáng giữ:** cổng D3.5 gọi thẳng `kiem_cong_d35()` — **chính hàm E3 dùng để TỪ CHỐI
chạy ablation** — nên "điều kiện đóng cổng" và "điều kiện được chạy ablation" là **MỘT**, không
phải hai danh sách song song sẽ trôi lệch. Xác nhận sau khi đóng: E3 đi qua `L-Z56` và dừng ở
`NotImplementedError` của logic ablation (việc của D4).

🔴 **BA PHÁT HIỆN LẬT NGƯỢC GIẢ ĐỊNH — đọc trước khi động vào D4:**
1. **Δ_R KHÔNG đặc thù DCA.** Bước 3: Δ_R(Z0) = 0,1552 vs Δ_R(DCA) = 0,1612 → tỉ lệ **1,04**,
   TƯƠNG ĐƯƠNG. DR-015 giả định sai số cộng dồn theo tranche nên DCA chịu nhiều hơn; dữ liệu nói
   tranche 1 (thứ Z0 cũng có) lệch gần bằng hệt. Hệ quả: hiệu chỉnh bất đối xứng của §4 **rộng
   hơn bất lợi thực của riêng DCA**. Vì thế `ket_luan_buoc3` là **tham số BẮT BUỘC** của §4.
2. **Con số Bước 2 từng SAI 16,5%** vì neo cửa sổ một phía vào `order_filled_timestamp` — mốc đó
   KHÔNG phải lần giá chạm thật và lệch **cả hai chiều**. Độ nhạy: 16,5% ở cửa sổ 0 → **0% ở cửa
   sổ ≥ 15 phút**, phẳng tới 3h; trễ tối đa **+4,4 phút** (dưới một nến 5m).
3. **`L-Z56` lộ ra TD-0161 không lưu Δ_R ra file** — không có gì để "đã commit", tức Δ_R có thể
   đổi lặng lẽ sau khi thấy kết quả ablation. Đã sinh artifact niêm phong + chốt **tính lại và
   đối chiếu** để artifact không trôi khỏi code.

⚠️ **`d3_5_han_che` ghi BỐN điều** vì cổng này dễ bị đọc quá tay nhất (có `p_nf = 0` trông rất
sạch): Bước 2 đo **gián tiếp** (không đặt lệnh thật; post-only bị từ chối / khớp một phần / vị trí
hàng đợi đều KHÔNG quan sát được, đều tính về phía bất lợi); chỉ **LONG** (bật Short thì L-Z56
CHẶN ablation); Bước 3 **tương đương**; `p_nf = 0` đo trên tập **ĐÃ CẤP** khớp.

🔴 **TD-0168 ✅ (sau khi cổng đã đóng) — phát hiện thứ TƯ, và nó là loại nguy nhất vì suite vẫn
xanh suốt:** vòng đo chốt của TD-0162 **KHÔNG đi qua `do_ty_le_khong_khop()`**. Nó là kịch bản
viết thẳng, quét mỗi dump một lượt rồi phân loại tại chỗ (gọi hàm kia ngây thơ sẽ mở lại 45 dump /
599 MB tới 91 lần). Cùng LUẬT phân loại, **khác ĐƯỜNG CHẠY** ⇒ **33 phép kiểm của TD-0162 canh một
hàm mà đường sản xuất chưa từng gọi**, và `chi_tiet` (dấu vết 91 ca mà docstring hứa "để truy ngược
khi số trông lạ") chưa bao giờ được lưu ra đâu. Đây là câu hỏi chẩn đoán của dự án — *"ca sai có đi
qua đường sản xuất thật không?"* — ở **CHIỀU NGƯỢC LẠI: thứ được canh không nằm trên đường chạy.**
Nhận diện nó cần đọc kịch bản chạy thật, không phép kiểm nào tự nói ra.
✅ **Đã vá và kết quả củng cố TD-0162, không lật:** `src/tool_d/dr015/buoc2_chi_tiet.py` gọi THẲNG
hàm đó, ghi `docs/du-lieu-do/dr015-buoc2-chi-tiet.json` (91 dòng, **FILE RIÊNG** — không chạm ba
artifact `L-Z56` đã niêm phong, không thêm vào `FILE_KET_QUA_D35`). Nó **TỪ CHỐI GHI** nếu lệch
artifact, và đường chạy độc lập **tái lập ĐÚNG 8 con số niêm phong** (3 số đếm 91/0/0 · `p_nf` 0/0 ·
biên −9,2828/−0,1403/−2,1233/0 ca · trễ −179,9989/+4,4055/−4,8849/76 ca) ⇒ **xác nhận độc lập cho
`p_nf = [0,0]`**. Full suite **1126 passed**; `kiem_cong_d35()` vẫn xanh. 🔑 **Bài học chọn phép so:**
P10/P25/P75/P90 cố ý đứng NGOÀI phép đối chiếu vì artifact không ghi cách nội suy — và đúng thế
thật, `tre.P25`/`tre.P75` **lệch**, `bien.P10/P90` thì khớp. Một phép kiểm báo đỏ vì **chênh quy
ước** sớm muộn bị gỡ, gỡ rồi mất luôn phần đúng của nó.

**Bước tiếp theo:** **D4** — 🔴 Ablation D0.9, 9 cấu hình × 2 hướng, **blocker B4**. ~~Chặn thêm bởi
**TD-0041 (ngưỡng DSR, blocker B6)** — con số đó vẫn cần chủ dự án quyết.~~
🔴 **ĐÍNH CHÍNH 08/09/2026 — câu gạch trên SAI, và nó đã lừa HAI phiên.** TD-0041 đã đóng từ
**06/09/2026** (commit `ba2af6a`, `DR-D0PRE-03`): `gates/thresholds.py:24` →
`DSR_ADJ_EXPECTANCY_MIN = 0.10`, **blocker B6 đã gỡ**. Thứ còn `-inf` là
`BEST_KNOWN_DSR_ADJ_EXPECTANCY` — *kết quả tốt nhất hiện có*, đúng như nó phải thế.
Giữ nguyên chữ cũ làm lịch sử, gắn đính chính tại chỗ để cái bẫy hết hiệu lực.
*(Đoạn "Đang ở" cũ bên dưới giữ nguyên làm lịch sử.)*

**Đang ở (cập nhật 08/09/2026, phiên cổng D3):** 🚪 **D3 ĐÓNG — tag `d3-complete`.**
Khối 14 xong sạch: **TD-0140…TD-0148 đều ✅**. Chạy thật trong Docker qua service **`freqtrade`**
(`E6 --close-d3-gate`, exit 0): `full_suite` **973 passed** · `test_khoa_d3` (L-Z47 22 · L-Z45 23
· TD-0148 14, **mỗi file chạy RIÊNG một lượt**) · audit **5/14 đạt, 0 chưa đạt**. Chạy lại → exit
**94**. `d3_git_sha` **khớp đúng HEAD** và `d3_cay_sach: true`.

🔴 **ĐỌC SAI CHỖ NÀY LÀ HỎNG CẢ D3.5:** cổng D3 chứng nhận **BỘ ĐIỀU PHỐI H3-D đúng**, **KHÔNG**
chứng nhận đã có kết quả walk-forward. Chưa có bộ chạy backtest thật (E2 dừng ở
`EXIT_CHUA_CO_BO_CHAY`); mọi phép kiểm mới chỉ được nuôi bằng **bộ chạy GIẢ**. Và TD-0148 **vẫn
tin lời khai của bộ chạy** — trả ngày *dự kiến* thay vì ngày *thật đọc từ dataframe* là vô hiệu
hoá nó hoàn toàn. **D3.5 viết bộ chạy thật: BẮT BUỘC đọc ngày từ dataframe + test khoá riêng.**
Đã ghi trong `d3_han_che` (nhãn `nguoi-khai`), không để ngầm hiểu.

**Ba bài học từ lần chạy THẬT** (chi tiết `docs/research-log.md` 08/09/2026):
1. 🔴 **Ba cổng D1/D2/D3 đều ghi `git_sha` mà KHÔNG cổng nào kiểm cây sạch.** Lần chạy đầu 8 ca
   đỏ (`test_lz27_lz28`+`test_td0130`), chạy lại riêng **40/40 xanh** — suite của cổng chạy 6,5
   phút, đúng lúc phiên khác sửa dở `registry.py`. Cổng từ chối vì suite đỏ, **nhưng nếu sửa đổi
   đó tình cờ không làm đỏ test nào thì cổng ĐÃ ĐÓNG** với sha trỏ tới commit không chứa thứ vừa
   kiểm. Đã vá cho D3 (kiểm TRƯỚC cả suite). 🔴 **D1/D2 không truy lại được — hạn chế đã ghi sổ,
   KHÔNG sửa vì là bằng chứng đã niêm phong.**
2. **Chốt đầu viết QUÁ CHẶT** (dùng thẳng `is_clean`, tính cả rác chưa theo dõi) → cổng không bao
   giờ đóng được. **Một chốt không bao giờ thoả được thì tệ hơn không có chốt** — sớm muộn bị gỡ.
   Sửa thành phân loại: file **đã theo dõi** bị sửa luôn tính; file **chưa theo dõi** chỉ tính khi
   nằm trong `src/ tests/ entrypoints/ config/ registry/schemas/` (một `.py` chưa commit trong
   `tests/` VẪN được pytest thu và VẪN không có trong commit).
3. **Suite KHÔNG độc lập với service** — chạy nhầm `lockbox` làm 3 test đỏ ĐÚNG, vì đó là service
   duy nhất *không che* `lockbox/data/`. "N passed" là phát biểu về MỘT service.

**Bẫy PASS RỖNG thứ ba của khối** (đúng họ với kết luận *"ca sai chỉ đi qua mẫu dựng tay"*):
fixture autouse che chính hàm cần kiểm → giữ `PHAN_LOAI_THAT` từ lúc import.

**Bước tiếp theo:** **D3.5** — 🚪 cổng sai lệch thước đo (DR-015), chặn D4. Cần testnet.
*(Đoạn "Đang ở" cũ bên dưới giữ nguyên làm lịch sử.)*

**Đang ở (cập nhật 08/09/2026, phiên rà lớp canh):** **TD-0150 ✅ đóng** + **rà TOÀN BỘ lớp canh xong**.

1. **TD-0150 — cửa ghi sổ trial nay đối chiếu schema TRƯỚC khi append.** Phiên `…-91` phát hiện khi
   làm TD-0149, tôi tái lập độc lập rồi nhận việc. Vá ở **`_append()` — điểm nghẽn DUY NHẤT**, không
   vá từng hàm: khoảng hở lộ ra ở HAI trường khác nhau (`seal_path`, `verdict`) nên nó là tính chất
   của cửa ghi; vá từng hàm là mời lỗi thứ ba xuất hiện ở hàm thứ bảy. Kèm test AST canh cho điểm
   nghẽn thật sự duy nhất. Hai test ghim hiện trạng của TD-0149 **sửa thành khẳng định ngược, KHÔNG
   xoá** — xoá một test đỏ cho sạch bảng là cách một quyết định biến mất mà không ai ghi.
   Docker **958 → 966 passed**; phiên `…-91` chạy lại độc lập **968 passed, 0 failed**.

2. 🔑 **Rà toàn bộ lớp canh bằng PHÁ THẬT — 19/19 phép phá đều bị bắt, không có lớp canh giả.**
   Cách đếm bằng heuristic cú pháp đã **thất bại** (20/46 rồi 0/46, mâu thuẫn ⇒ vô giá trị) — bài
   học: **đừng đo tính chất NGỮ NGHĨA bằng dấu hiệu CÚ PHÁP**. Lab dựng bằng `git clone --local`
   (KHÔNG `cp -r` — bản chép đầu lệch giữa chừng vì phiên khác đang sửa file).
   🔴 **Hai lần máy báo "xanh" đều là NGƯỜI PHÁ SAI**, không phải lớp canh giả — tin ngay kết quả
   đầu thì đã vu oan hai lớp canh tốt.

3. 🔑 **Kết luận lật ngược giả thuyết, và đây là phần đáng nhớ nhất của cả ngày:** nếu mọi lớp canh
   đều có răng thì ba sự cố trong ngày **không phải do lớp canh cùn**. Điểm chung của cả ba (schema
   không biết khoá mới; L-Z55 ở `folds` hai vế cùng nguồn; N12 mục 5 hở ca file MỚI) là: **ca sai
   chỉ đi qua MẪU DỰNG TAY, chưa bao giờ đi qua ĐƯỜNG SẢN XUẤT THẬT.** Lớp canh sắc nhưng chĩa nhầm
   hướng. **Câu hỏi chẩn đoán dùng từ nay:** *"Ca sai đó có đi qua đường sản xuất thật không?"*
   Bài học phụ: **đo phủ sóng theo TỪNG FILE là sai đơn vị** — phủ sóng của `check_td0120` nằm ở
   `test_td0124_*`, khác file.

**Nợ đã ghi, chưa tới hạn:** ~10 lớp canh đang được nuôi bằng mẫu dựng tay vì **bộ sinh thật chưa tồn
tại** (chiến lược chưa viết) — L-Z1/6/18/19/30/31/34/35/43, TD-0105. Hợp lý hôm nay, nhưng **D3.5 là
đúng lúc khoảng hở loại này sinh ra**; khi bộ sinh ra đời phải nối test vào nó, không để nguyên mẫu
tay. Chi tiết + giới hạn của kết luận ("không thấy thêm", không phải "chứng minh không còn") ở
`docs/research-log.md` 08/09/2026.
*(Đoạn "Đang ở" cũ bên dưới giữ nguyên làm lịch sử.)*


**Đang ở (cập nhật 07/09/2026, phiên L-Z27/L-Z28):** **TD-0127 ✅ đóng.** Chủ dự án chốt phạm vi
**làm phần đo được ngay** thay vì hoãn tới D3.5 — vì cả hai luật đo bằng SỐ LỆNH ĐÃ ĐÓNG mà Tool D
chưa có lệnh live nào.
- **L-Z27 làm TRỌN VẸN**, và phần mạnh nhất **không phải phép kiểm lúc audit**: `TrialLedger`
  bỏ hẳn tham số `n_tai_sinh`, chỉ nhận `so_lenh_da_dong` rồi tự áp `min(floor(lệnh/25), 20)`.
  *"Tăng B3 bằng tay"* thành **không biểu diễn được**, thay vì bị chặn sau khi đã xảy ra — một phép
  kiểm có thể bị bỏ qua, một tham số không tồn tại thì không ai truyền vào được.
- **L-Z28 fail-closed:** đề xuất đã APPLIED mà không chứng minh được là rơi đúng điểm quyết định →
  **BÁO ĐỎ**. Im lặng ở đây nghĩa là tham số đã đổi thật trên tiền thật mà không ai kiểm được.
- 🔎 Ngoại lệ **DR-012 Hạng 1 cố ý KHÔNG thêm ô khai nào**: Hạng 1 là *lỗi code không khớp spec*,
  sửa tự do 0 trial, **không phải đổi tham số** → không bao giờ vào sổ đề xuất. Thêm ô *"đây là sửa
  lỗi"* sẽ mở đúng cái cửa L-Z28 sinh ra để đóng.
Docker: **817 baseline + 22 = 839 collected, 838 passed**. E6 sổ thật exit 0, **4/12 → 5/14**.
🔴 **Vì sao §12c.3 (Cấp B cần HAI điểm quyết định LIÊN TIẾP) vẫn chưa kiểm được — nay đã rõ nguyên
nhân gốc:** sổ đề xuất **không có trường nào neo vào điểm quyết định**, mà neo được thì cần số lệnh
live. Nối nguồn số lệnh (DB Freqtrade) là việc **D3.5+**, đã ghi vào TASKS.
⚠️ **Bắt được 1 test đỏ KHÔNG thuộc đợt này:** L-Z46 bắt chuỗi `profit_ratio` trong
`src/tool_d/wfo/equity.py` — file **chưa commit của phiên song song**, chuỗi nằm ở **dòng chú thích
giải thích chính lệnh cấm** (đúng hình dạng L-Z25/`hyperopt` của TD-0125). Đã báo phiên đó kèm tiền
lệ *diễn đạt lại, không nới phép kiểm*; **không tự sửa file đang dở của người khác** (N12).
*(Đoạn "Đang ở" cũ bên dưới giữ nguyên làm lịch sử.)*


**Đang ở (cập nhật 07/09/2026, phiên kế toán CTRL):** **TD-0130 ✅ đóng — MT-08 đã có máy thi hành.**
Đây là việc *đã CHỐT từ 07/09 nhưng 0 dòng code*: chính sách "CTRL không tính vào N" nói ở 5 chỗ trong
spec, chốt ở MT-02 rồi MT-08, mà `registry.py` vẫn cộng CTRL vào `n_used()` và chặn ghi điểm kiểm soát
khi ngân sách cạn. Ba chỗ sửa + **cửa xác thực CTRL fail-closed**: CTRL đứng ngoài ngân sách nên "khai
CTRL" là đặc quyền — phải thuộc ĐÚNG MỘT dạng *tái lập* (hash khớp bản ghi gốc) hoặc *đo thước*
(`ctrl_output_whitelist`), máy đối chiếu chứ không nhận lời khai. Khai **cả hai** cũng bị từ chối.
🔴 Làm **chặt hơn** kế hoạch: `CTRL_OUTPUT_ALLOWED` là danh sách **CHO PHÉP** chứ không phải blocklist
chuỗi cấm — đúng chữ spec dòng 3605-3607; blocklist chỉ chặn được tên đã nghĩ ra trước.
Docker: **744 (baseline đo lại ngay lúc so) + 18 = 762 passed, 0 failed**; baseline **đo lại ngay trước khi so** bằng
`--collect-only`, không lấy từ file (bài học "mốc 629 vs 624": hai phiên chạy song song thì mốc test
của phiên kia dịch dưới chân mình). E6 sổ thật exit 0, `N_ĐÃ_DÙNG=4` không đổi, sổ vẫn 12 dòng.
**Chọn việc này vì nó không giẫm hai phiên kia** — TD-0127 (việc 🔓 duy nhất lúc đó) phải sửa
`audit_checks.py` + `trial_ledger_audit.py`, đúng hai file cả hai phiên đang gõ dở. TD-0130 chỉ đụng
`registry.py` + 1 file test mới; `check_lz11` tự đúng theo vì nó gọi `ledger.n_used()`.

🐛 **Bắt được một lỗi do CHÍNH phiên này gây ra, lúc đang soạn tài liệu:** commit đầu (`5d5ae82`)
thêm hai khoá vào sự kiện RESERVE nhưng quên `trial_event.schema.json` — schema có
`additionalProperties: false`, nên **dòng CTRL đầu tiên ghi vào sổ thật sẽ vi phạm chính schema mà
audit dùng**. **735 test xanh vẫn không bắt được**, vì `test_registry_schemas.py` chỉ đối chiếu
FIXTURE GÕ TAY, chưa dòng nào đối chiếu đầu ra THẬT của `reserve()`; sổ thật thì chưa có dòng CTRL
nào để nổ. Vá ở `e6a67f1` + **3 test đối chiếu đầu ra thật với chính schema audit dùng** — đóng cả
LỚP lỗi chứ không chỉ ca vừa gặp. Bài học rút ra rộng hơn TD-0130: **"suite xanh" không chứng minh
cửa ghi và schema đồng ý với nhau**, nếu không có test nào bắt hai thứ đó nhìn nhau.
✅ **Đã "chuẩn hóa và lưu"** (`1e8ae07`): MT-08 → ✅ đã thi hành; mục 8 back-end-note + mục 7/8
ARCHITECTURE. Quyết định hoãn `tu-dien-du-lieu.md` tới D3.5 **giữ nguyên** (không thêm bảng CSDL nào).

**Còn treo sau việc này:**
- 🔓 **TD-0127** (`L-Z27` + `L-Z28`) vẫn chưa ai làm, hạn chót trước D11. Giờ hai phiên kia đã rời
  `audit_checks.py` thì nó hết va chạm.
- 🧹 Hai thư mục rác ở gốc repo từ lệnh shell nhầm: `C:/` và `ls -la /`. Vẫn chờ đồng ý mới xoá.
*(Đoạn "Đang ở" cũ bên dưới giữ nguyên làm lịch sử.)*


**Đang ở (cập nhật 07/09/2026, phiên cổng D2):** 🚪 **D2 ĐÓNG — tag `d2-complete`, TD-0117 ✅.**
`runtime_state.json.d2_complete` sinh từ MỘT LẦN CHẠY THẬT trong Docker (`E6 --close-d2-gate`,
exit 0); ba mục evidence đều `do-duoc` đúng nghĩa MT-10 vì hàm TỰ gọi pytest trong chính lần
đóng cổng: `full_suite` **720 passed** · `lz49_lz50` **5 passed** · audit sổ trial **4/12 đạt,
0 chưa đạt**. Chạy lại → exit **94**, từ chối ghi đè.
🔴 **Điều đáng nhớ nhất của đợt này — cổng D2 có một phép kiểm mà cổng D1 không có.** Cổng D1
chỉ hỏi *"suite xanh chưa?"*; với D2 câu đó KHÔNG đủ, vì xoá hẳn `test_lz49_lz50_backtest_nho.py`
đi thì suite vẫn xanh và cổng vẫn đóng được — trong khi hai phép kiểm cốt lõi của D2 đã biến mất.
Nên `close_d2_gate()` chạy **RIÊNG** file đó và đòi **số ca PASS ≥ 1**; exit 0 mà 0 ca chạy bị
từ chối thẳng ("PASS RỖNG, không phải bằng chứng"). Cùng hình dạng lỗi đã cắn ở TD-0084, nhưng
lần này chốt viết TRƯỚC. Đã kiểm chốt có răng (vô hiệu hoá → đúng 1 ca đỏ, không phải cả bộ).
🔴 **KHÔNG tự phong cho D2 nhiều hơn nó có:** `d2_hoan_lai` (nhãn `nguoi-khai`) ghi thẳng
**D2b/D2c/D4 là HOÃN tới D3.5/D9.5+, không phải "đã qua"** — cần lệnh thật trên sàn. D2c còn
vướng phát hiện của TD-0116: latency **LẠNH** bất ổn (14/30 mẫu >1s, max 11 giây) → cửa sổ
không-SL có thể vượt 15 giây; phải giải quyết trước khi có lệnh thật.
**Bước tiếp theo:** D3 (chưa mở). Còn treo từ phiên song song: 🔓 TD-0127 (`L-Z27`/`L-Z28`,
hạn trước D11).
*(Đoạn "Đang ở" cũ bên dưới giữ nguyên làm lịch sử.)*

**Đang ở (cập nhật 07/09/2026, cuối phiên công cụ nhập liệu):** **TD-0124 + TD-0125 + TD-0126 ✅;
OQ-13 đóng; đã ghi `back-end-note.md` + `ARCHITECTURE.md` (lệnh "chuẩn hóa và lưu" 07/09/2026).**

🔴 **VIỆC QUAN TRỌNG NHẤT PHIÊN NÀY — suýt xoá bản backup lockbox.** Tôi liệt kê thư mục `C:` ở gốc
repo là "rác" và xin xoá; chủ dự án đồng ý. Mở ra xem trước khi xoá thì nó chứa **511 file dữ liệu
lockbox khớp từng byte**. Tên thật là `C` + **U+F03A** (dấu hai chấm giả) — do truyền đường dẫn
Windows vào `backup_lockbox(dest_dir=...)` từ Git Bash. Nghiêm trọng hơn: nó nằm NGOÀI đường dẫn mà
`docker-compose.yml` che, nên **lockbox lọt vào container** (1023 → nay 513 file `.feather` thấy
được), phá đúng thứ `ARCHITECTURE.md` 3.1 gọi là hàng rào ở tầng hệ điều hành. Hoá ra
`E:\lockbox-backup-tool-d` đã có bản backup **đầy đủ 512/512**, nên bản trong repo là bản THỪA — đã
xoá sau khi verify sha256, đã kiểm lại container. **Hai bài học ghi ở `docs/research-log.md`:**
(1) "rác" là một *kết luận* rút từ cái tên, không phải một *quan sát*; (2) `pathlib.Path("C:/…")`
hiểu là ổ đĩa C: nên phép đo đầu tiên trả "0 file" — một kết quả SAI mà lại khớp với giả thuyết sẵn
có. **Số liệu ủng hộ giả thuyết của mình là lúc phải nghi ngờ phép đo nhất.**

Các việc còn lại:
1. **TD-0126 ✅** — `explore_evidence` bắt buộc khi `data_source=EXPLORE`; và so `mechanism` để chặn
   **nộp lại ý tưởng đã bị loại dưới tên khác** (§9c.7.4 ràng buộc 3, tương đương
   `retest_forbidden`). 🐛 Test bắt được bug thật trong chính code này: `đ` (U+0111) **không tách
   được bằng NFD** — nó là ký tự CƠ SỞ, nên `"đóng"` → `"ong"` còn `"dong"` giữ nguyên. Ngưỡng nghi
   trùng cố ý đặt sai thì **rẻ** (khai thêm một dòng, không mất đơn) và **không** vào
   `tool_d_config.yaml`.
2. **Va chạm mã việc đã giải:** cặp D2 đổi số **TD-0119 → TD-0128, TD-0120 → TD-0129**; cặp Idea
   Queue **giữ nguyên**. Tiêu chí: *phía nào có ĐỊNH DANH MÁY ĐỌC thì phía đó không đổi* — mã Idea
   Queue đã ăn vào tên file test, tên hàm, và chuỗi E6 **in ra trong đầu ra thật**. Lịch sử git
   không viết lại được, nên kèm **TỪ ĐIỂN ĐỔI TÊN** ở đầu Khối 13 + alias trong docstring.
3. **Giấy tờ đã xong:** OQ-13 → ✅; **MT-13** mới; MT-11 nối thêm câu (trần nhập đã có test khoá);
   ARCHITECTURE có sổ thứ ba + ghi rõ **nguồn sự thật hình dạng sổ là JSON Schema trong
   `registry/schemas/`**, không nhân đôi ra `.md` (bài học MT-03). Từ điển dữ liệu **giữ hoãn** tới
   D3.5 theo quyết định chủ dự án.

Docker: **720 passed, 0 failed** (699 → 720, đúng +21). E6 trên sổ thật: `đã audit 4/12`, exit 0.
Cả hai sổ mới vẫn **0 dòng** — mọi thử nghiệm chạy trong hộp cát.

**Bước tiếp theo / còn treo:**
- 🔓 **TD-0127** (`L-Z27` + `L-Z28`) — hoãn **có lý do**, không phải quên: `L-Z28` cần đánh số điểm
  quyết định, `L-Z27` phần "chỉ tăng theo `floor(lệnh/25)`" cần lệnh live — cả hai chưa tồn tại.
  Viết bây giờ là viết test cho cơ chế chưa có, phải mock, đúng thứ **L-Z51** cấm. Hạn: **trước D11**.
- 🔴 **Phạm vi L-Z26 KHÔNG phủ:** §12c.3 đòi Cấp B có HAI điểm quyết định LIÊN TIẾP — cùng lý do
  trên, đã ghi vào TD-0127.
- ⚠️ **Phiên song song đang làm TD-0117** (cổng D2, `--close-d2-gate`). Mốc test dịch dưới chân:
  luôn đo baseline lại ngay trước khi so (`--ignore` file test mới), đừng lấy con số từ `TASKS.md`.
*(Đoạn “Đang ở” cũ bên dưới giữ nguyên làm lịch sử.)*

**Đang ở (cập nhật 07/09/2026, phiên công cụ nhập liệu):** **TD-0124 + TD-0125 ✅ đóng; OQ-13 đóng.**
Hai kênh nhập liệu trước đây ở cùng một tình trạng — **luật viết rất chặt, không dòng code nào thi
hành** — nay đều có máy TỪ CHỐI GHI:

1. **TD-0124 — công cụ nộp đơn ý tưởng.** Cửa GHI đầu tiên cho `idea_queue.jsonl` (trước đó chỉ có
   phần ĐỌC; mọi đơn phải gõ tay 20 khoá JSON, `additionalProperties: false`). Sáu ca fail-closed,
   kiểm **TRƯỚC** khi mở file — sổ append-only không có đường lùi. Kèm **trần NHẬP 10 đơn/quý**
   (spec dòng 4095), lấp đúng lỗ hổng MT-11 tự ghi là *"mới là văn bản; chưa code"*. Trần này
   **chặn CỨNG**, khác trần CHỌN L-Z17 mà MT-11 đã nới: trần CHỌN là kỷ luật con người và không
   chảy vào N/DSR, trần NHẬP thì có.
2. **TD-0125 (OQ-13) — sổ THỨ BA `param_change_proposals.jsonl` + `L-Z26`** (🔴 CRITICAL, trước đó
   **0 dòng code**). Tám ca từ chối ghi. Điểm thiết kế then chốt: `luan_diem` là **mảng có cấu
   trúc** `{chi_so, gia_tri (SỐ), dai_ky_vong, tham_so_tro_toi}` — câu không trích được số thì
   **không biểu diễn được**, thay vì một ô văn xuôi kèm lời hứa cần người nhớ luật mới thi hành.
   Chốt riêng chống *"đề xuất một BỘ tham số"*: mọi luận điểm phải trỏ **cùng một** tham số.
3. **Không thêm entrypoint thứ 9** — cả hai công cụ là cờ trên E6 (`--nop-y-tuong`, `--nop-de-xuat`).
   `entrypoints/` vẫn **đúng 8 file**. Phương án "CLI nằm ngoài `entrypoints/`" bị loại có ý thức:
   không vi phạm *chữ* của L-Z36 nhưng mở đúng lỗ hổng danh sách đóng tồn tại để bịt.
4. **Không sửa `periodic_report.py`** — `bao_cao_hash` do máy tự băm từ file báo cáo E5 đã lưu,
   tránh hẳn *"đổi nội dung báo cáo = tiêu 1 trial"* (dòng 4808) và `FROZEN_CONTENT_HASH` (TD-0062).

Docker: **687 passed, 0 failed** (629 → 657 → 687, mỗi bước tăng ĐÚNG số test mới). E6 trên sổ thật:
`đã audit 4/11`, exit 0. Sổ thật vẫn 0 dòng ở cả hai sổ mới — mọi thử nghiệm chạy trong hộp cát.
🔴 **`L-Z25` bắt được chuỗi cấm trong thông báo lúc chạy** — diễn đạt lại, **không nới phép kiểm nào**.

**Còn treo / bước tiếp theo:**
- ⏳ **Chưa ghi `back-end-note.md` + `ARCHITECTURE.md`** — N9 đòi lệnh **"chuẩn hóa và lưu"**. Nội
  dung đã soạn: OQ-13 → ✅ Đã giải; **MT-13** mới (sổ thứ ba); MT-11 thêm một câu (trần nhập đã có
  test khoá); sơ đồ LEDGER + cây thư mục + §7 ERD của ARCHITECTURE.
- ✅ **Từ điển dữ liệu:** chủ dự án chốt **giữ hoãn** tới D3.5 (`ARCHITECTURE.md:229`) — đợt này chỉ
  thêm sổ JSONL, không thêm bảng CSDL; nguồn sự thật là JSON Schema trên đĩa, không nhân đôi ra .md.
- 🔓 **TD-0126** (`explore_evidence` bắt buộc khi EXPLORE + query trùng `mechanism`), 🔓 **TD-0127**
  (`L-Z27` + `L-Z28`, cùng khối §12d.4, cũng 0 dòng code). Cả hai hạn chót **trước D11**.
- 🔴 **Phạm vi L-Z26 KHÔNG phủ:** §12c.3 đòi Cấp B có HAI điểm quyết định LIÊN TIẾP — chưa kiểm được
  vì chưa có đánh số điểm quyết định (chưa có lệnh live). Đã ghi vào TD-0127.
- 🔴 **Cần chủ dự án quyết — va chạm mã việc:** `TD-0119`/`TD-0120` đang dùng **HAI LẦN** cho hai
  việc khác hẳn (`TASKS.md:203-204` khối D2 vs `:213-214` khối Idea Queue), vi phạm quy tắc 1 của
  `TASKS.md`. Đã lan vào docstring `entry_confirmation.py`/`trend_context.py`. Không tự sửa.
- ✅ **Mốc 629 vs 624 — đã truy ra nguồn, KHÔNG phải lệch số.** Commit `2659a5d` của **phiên song
  song** (TD-0117, `test_lz49_lz50_backtest_nho.py`, đúng **5 test**) rơi vào giữa đợt này. Mốc
  **624** vẫn đúng tại thời điểm được ghi. Bài học đúng ở đây không phải "chữ ghi sai" mà là: khi
  hai phiên cùng chạy, **mốc test của phiên kia dịch dưới chân mình** — nên baseline phải đo lại
  ngay trước khi so, không lấy từ file (đã làm: `--ignore` chính file test mới).
- 🧹 Hai thư mục rác ở gốc repo từ lệnh shell nhầm: `C:/` và `ls -la /`. Chờ đồng ý mới xoá.
*(Đoạn “Đang ở” cũ bên dưới giữ nguyên làm lịch sử.)*

**Đang ở (cập nhật 07/09/2026, phiên Idea Queue):** **TD-0118 + TD-0119 + TD-0120 ✅ đóng; OQ-07 đóng.**
Ba quyết định về hàng chờ ý tưởng, đều đã ghi sổ và có máy canh:
1. **MT-11** — trần Ngân sách A = **5 suất/quý dùng chung Tool A + D** (dòng “1/quý” ở §9c.7.4 là
   nhịp khuyến nghị, không phải trần cứng); `L-Z17` nới thành **cảnh báo, không chặn chạy**
   (`WARN_ONLY_CODES`) — sửa có ý thức dòng H16. **`L-Z16` giữ chặn cứng** (chống nhiễm dữ liệu,
   không phải kỷ luật cá nhân), có test canh riêng để không bị nới lây.
2. **MT-12** — sửa đặc tả §9c.7.3: tờ đơn ý tưởng **hai cửa**. Cửa NỘP rẻ (+ `phep_thu_du_kien`),
   cửa CHỌN chặt (`tin_hieu`/`quy_tac`/`nguong_bac_bo`/`so_bien_the`, fail-closed). `so_bien_the`
   **nối vào sổ trial** qua `hypothesis_slot = IQ-xxxx` → máy đếm CONSUMED ≤ số đã khai, không
   nhận lời khai suông (cùng bài học MT-10).
3. **OQ-13** — kênh đề xuất đổi tham số khi đã chạy (§12c.3/§12d): luật đủ nhưng **`L-Z26` chưa có
   một dòng code nào** và chưa có sổ ghi đề xuất. Không chặn D2, **phải xong trước D11 (dry-run)**.
4. **OQ-07 ✅ đóng** — `docs/decisions/DR-Q3-2026-tieu-chi-chon-y-tuong.md`, commit **RIÊNG và
   TRƯỚC** mọi dòng đơn (spec dòng 4935). **Hạn ngạch chọn quý 3/2026 = 0** — vì Tool D chưa có
   lệnh live nào, `mult_edge` cần **50 lệnh live** nên tín hiệu “edge chết” chưa thể xuất hiện,
   và lockbox có ĐÚNG MỘT mà Zone Absorption chưa chạm. Kèm **ba điều kiện mở lại** viết trước
   (`mult_edge = 0.5` / phán quyết L2-L3 / B3 cạn) và **4 tiêu chí thứ tự từ điển** `TC-Q3-2026-01…04`
   — không dùng điểm có trọng số vì trọng số vặn được sau khi đã nhìn thấy đơn. Máy kiểm `TD-0120`:
   `selection_reason` phải trích mã TC có thật; 4 ca fail-closed. **Cửa NỘP đã mở** (10 đơn/quý);
   phiên sinh ý tưởng phải **bịt mắt** (không xem kết quả Tool D — DR-009).
Docker: **624 passed, 0 failed**. E6 trên sổ thật: `đã audit 4/9 (4 đạt, 0 chưa đạt, 5 chưa đo được)`. Nguyên tắc phải nhớ khi làm tiếp (§12d.2): ranh giới hợp lệ
**không phải “ai bấm nút”** mà là **“không gian tìm kiếm có bị chặn TRƯỚC không”** — “LLM đề xuất,
người duyệt” một mình KHÔNG đủ. Còn treo: **công cụ nộp đơn** (làm sau, giờ đã có cấu trúc tờ đơn để dựa vào). Ghi nhận:
trần **nhập** queue 10 ý tưởng/quý vẫn **chưa có test khoá nào** thi hành.
*(Đoạn “Đang ở” cũ bên dưới giữ nguyên làm lịch sử.)*

**Đang ở (cập nhật 07/09/2026):** 🚪 **D1 ĐÓNG — tag `d1-complete`, gỡ blocker B2.** Hai nhánh
việc chạy song song suốt D1, không giẫm nhau (kiểm `git log`/`git status`/diff trước mỗi lần đụng
file chung): nhánh H1-D/backfill (TD-0090→0097 + TD-0107 review) và nhánh zone detection/H4-D/H13
(TD-0100→0106). TD-0093 bắt được bug thật: `freqtrade download-data --timerange` không tôn trọng
mốc kết thúc — dữ liệu LOCKBOX lọt vào thư mục làm việc, đã cắt lại đúng phạm vi, mở TD-0094 (nối
`assert_dataset_timerange()`/L-Z55 có sẵn với cấu hình thật — **chưa** wiring được vào E1/E2/E3 vì
ba entrypoint đó chưa có logic tải dữ liệu thật, để dành cho task D2+ viết logic đó). TD-0095 tìm
được nguồn thật cho symbol đã huỷ niêm yết (`data.binance.vision`, 219 mã) thay vì chấp nhận
survivorship bias như dự kiến ban đầu. TD-0106 chạy `lookahead-analysis` thật — không thấy bias.
Review độc lập (subagent context sạch) bắt được 1 bug thật ở `touch_count()` (đã sửa, TD-0107).
`close_d1_gate()` (E6, `--close-d1-gate`) tự chạy `pytest` thật trong chính lần đóng cổng — nhãn
bằng chứng `do-duoc` đúng nghĩa theo MT-10 (khác cổng D0-PRE cũ, có 2/3 mục evidence là chuỗi gõ
tay). Chạy thật: 492 passed, audit sổ trial 4/6 đạt. **Bước tiếp theo:** D2 (chưa mở) — verify giả
định D1-D7, H15.
*(Đoạn "Đang ở" cũ bên dưới giữ nguyên làm lịch sử.)*

Cũ (06/09/2026, đêm khuya): 🚪 **D0-PRE ĐÓNG — 62/62 việc xong, tag `d0-pre-complete`.**
Ba điều kiện chạy THẬT xác nhận: lock tests 215/215, `trial_ledger_audit.py` 4/6 đạt (0 fail),
`periodic_report.py` sạch 22/22 pending — ghi vào `registry/runtime_state.json.d0_pre_complete: true`
qua `trial_ledger_audit.py --close-gate` (E6, TD-0086), bất biến (đã test từ chối ghi lại). Suite
Docker cuối: **352 passed**. Trong đêm cũng chốt nốt: ba con số Tầng A/C (DR-D0PRE-03/04/06 — DSR
0,10 R_realized/blocker B6 gỡ, drawdown 5/8/20%, `E_D` 500/3x), TD-0082 (min notional 102/102 qua),
TD-0084 (mốc CALIB/WFO/LOCKBOX bằng giá BTC thật — T0=09/04/24, T1=12/06/25, T2=29/01/26, T3=hôm nay
— niêm phong `lockbox_seal_1.json`, 510 file OHLCV thật; **bắt được và sửa 1 bug thật**:
`verify_all_seals()` trỏ sai thư mục, tồn tại từ TD-0071/72, không bị bắt vì trước đó chưa có seal
thật), TD-0085 (backup lockbox + khôi phục thật PASS). OQ-01/02/03/05/08 đóng trong `back-end-note.md`.
**Bước tiếp theo (D1):** bắt đầu viết logic chiến lược thật (zone detection, tranche, gate DG1–DG8) —
nối `is_d0_pre_complete()` vào đầu E1/E2/E3/E7/E8 là việc đầu tiên của D1, chưa làm ở D0-PRE.
*(Đoạn "Đang ở" cũ bên dưới giữ nguyên làm lịch sử.)*
Cũ: **Giai đoạn 3**, backend đã qua hết **Khối 1** (cổng L-Z36→L-Z41 sạch, tag
`d0pre-0d-live`) và đang ở **Khối 2** (DR-013 xong, config Freqtrade + TD-0028 đang làm).

**Backend — đã xong:**
- Khối 0 (TD-0001→0005): repo git local, Docker + docker-compose, `git_sha` khớp trong container.
- Khối 1 (TD-0010→0020): toàn bộ tầng chống nhiễm phép đo — `tri_state`, `provenance` (L-Z40),
  `config/tool_d_config.yaml` + `loader.py` (12 tham số tunable), `guard.py` (`measurement_guard()`,
  verify thủ công exit 86 + file không bị xoá), 8 khung entrypoint E1–E8, `assert_cache_none()`
  trong E1, test L-Z36/L-Z37/L-Z39/L-Z32/L-Z33/L-Z46/L-Z48c. **Cổng Khối 1 đã đóng** (TD-0020).
- Khối 2 (đang làm): TD-0025 DR-013 (đơn vị đo `pnl_abs`) xong. TD-0028 (đọc mã nguồn Freqtrade
  cho D2a/D2b/D6/D7) → `docs/freqtrade-source-read.md` — D2a xác nhận đúng (cơ chế huỷ+đặt lại
  SL, 2 bước tách rời, cận trên khoảng trống = 5s `PROCESS_THROTTLE_SECS`), D2b xác nhận
  **KHÔNG** hỗ trợ `closePosition`, D6 xác nhận đúng (dùng giá MỞ nến — rủi ro số một), D7 xác
  nhận cơ chế an toàn + phát hiện phụ (phải assert `trade.id != 0` trước khi gọi custom_data khi
  implement thật, tránh trộn dữ liệu giữa các cặp giao dịch khác nhau).
- `dashboard-ui/` (front-end, việc riêng): dựng xong khung React + Chakra UI cho 8 trang dashboard
  Tool A/D từ mock JSON, đã tách thành **repo GitHub riêng** (không gộp vào repo backend), đã push
  lên `github.com/nhanle1153/front-end-trading-tool-smart-dca` (nhánh `main`) — xem chi tiết ở mục
  TD-0006/TD-0007 trong `TASKS.md`. Chưa nối API thật.

**Còn thiếu / bước tiếp theo:**
1. **TD-0003** — tạo repo GitHub private cho backend và push (chờ chủ dự án đồng ý).
2. ~~`dashboard-ui/` cần chủ dự án tạo repo GitHub trống (private) rồi cấp link để thêm remote + push.~~
   ✅ Xong 06/09/2026 — đã push lên `github.com/nhanle1153/front-end-trading-tool-smart-dca`.
3. ~~Khối 2 còn TD-0026 (config Freqtrade thật) + TD-0027 (test L-Z24/L-Z25/L-Z42).~~
   ✅ Xong 06/09/2026 — `config/freqtrade/config.json` + 3 test khoá
   (`tests/lock/test_lz24_*`, `test_lz25_*`, `test_lz42_*`), 179 test xanh trong Docker.
4. Khối 3 (thứ tự cứng 1→2→3, không song song): verify `zone_width` chết hay không → xác nhận
   bảng DOF → chốt `N_ĐĂNG_KÝ`.
5. Ba con số chặn tiến độ cần chủ dự án quyết khi tới lượt: **OQ-01** (ngưỡng DSR — blocker B6),
   **OQ-02** (vốn `E_D`), **OQ-03** (thang drawdown).
6. 🔵 **Câu hỏi mở do phía front-end nêu (ghi nhận, chưa chốt, chưa chặn việc gì bên backend):**
   dashboard sẽ lấy số thật bằng cách nào — (a) backend mở API REST, hay (b) backend xuất file
   JSON định kỳ để front-end đọc? Liên quan trực tiếp tới backend vì hiện `entrypoints/` bị khoá
   cứng ở **đúng 8 file** (test L-Z36); phương án (a) cần thêm entrypoint thứ 9 → phải sửa đặc tả
   kiến trúc trước. Phương án (b) tận dụng `periodic_report` sẵn có, không đụng kiến trúc.
   Chi tiết + bảng đánh đổi: mục `OQ-FE-01` trong `TASKS.md` của repo front-end.
   ✅ **Đã chốt 06/09/2026 — phương án (b), đọc file.** Căn cứ mạnh hơn cả chi phí: §12d.2 **cấm**
   truy vấn dữ liệu thô, và định nghĩa báo cáo là tài liệu cố định xuất theo kỳ. **Không cần thêm
   entrypoint thứ 9, không đụng L-Z36.**

7. ✅ **ĐÃ CHỐT 07/09/2026 — `CTRL` KHÔNG tính vào N; `registry.py` phải sửa cho khớp.**
   (front-end phát hiện; chủ dự án duyệt **phương án A + cơ chế xác thực**)

   **Đây không phải mâu thuẫn chính sách — chính sách đã chốt từ trước.** Spec nói CTRL không
   tính vào N ở **5 chỗ** (§0d.4 dòng 594, DR-014 §2 dòng 3490 *"ngoài sổ này"*, dòng 3608
   *"dòng CTRL, 0 trial"*, dòng 3715, changelog v8 dòng 71), và chính chủ dự án đã chốt
   *"vẫn ghi sổ dòng `CTRL` (0 trial)"* trong **MT-02** (`back-end-note.md` mục 7, 06/09/2026).
   Cái đang sai là **code chưa thi hành điều đã chốt**.

   **Ba lỗi trong `src/tool_d/ledger/registry.py`:**
   1. `TrialProjection` không lưu `budget_line` → `n_used()`/`n_reserved()` cộng cả CTRL.
   2. `reserve()` chặn `contribution < 1` → dòng "CTRL 0 trial" mà MT-02 yêu cầu **không ghi được**.
   3. `reserve()` kiểm ngân sách cho mọi dòng → khi N cạn thì **không ghi được điểm kiểm soát**,
      đúng lúc sắp go-live là lúc cần kiểm tra tái lập nhất.

   **Phương án đã duyệt:**
   - `TrialProjection` mang `budget_line`; `n_used()`, `n_reserved()` và phép kiểm ngân sách trong
     `reserve()` **loại CTRL ra**. Giữ nguyên bất biến `contribution >= 1` (không mở đường mức 0 —
     đó là bất biến fail-closed cố ý).
   - CTRL phải khai thuộc **một trong hai dạng hợp lệ, máy kiểm chứ không nhận lời khai**
     (cùng triết lý DR-014 §3 *"máy tự ghi, người không có đường nhập liệu"*):
     - *tái lập* (§0d.4): có `reproduces_trial_id`, và `config_hash` + `params_frozen_hash`
       **bằng đúng** bản ghi của trial đó;
     - *đo thước* (D3.5 Bước 1, MT-02): đầu ra bị giới hạn cứng vào danh sách trắng không chứa
       bất kỳ chỉ số hiệu năng nào (spec dòng 3605-3607 *"bộ chạy cưỡng chế danh sách này"*).
     Không thoả dạng nào → **từ chối ghi CTRL** (fail-closed), tính như trial thường.
     Lý do cần cơ chế này: L-Z55 một mình KHÔNG đủ cho CTRL, vì một điểm kiểm soát hợp lệ *có*
     chạm CALIB nên không vi phạm timerange — chỗ phân biệt phải là ĐẦU RA.
   - Test khoá mới **`test_td0087_ctrl_khong_tinh_vao_n.py`** (KHÔNG dùng mã `L-Z56` — mã đó đã
     có chủ, spec gán cho test khác của DR-015; xem MT-09): 1 trial B1 + 1 trial CTRL đều
     CONSUMED → `n_used() == 1`; và `reserve()` dòng CTRL vẫn thành công khi ngân sách đã cạn.

   **Vì sao đáng sửa** (suy từ hằng số spec, không cần dữ liệu): điểm kiểm soát chạy sau MỖI lần
   một tham số đổi trạng thái (§0d.4); Tầng B có 12 tham số, trần B3 = 20 → cận trên ~20-25 trial
   trên tổng 114 (**~18-22% ngân sách nghiên cứu**) bốc hơi vì kế toán sai. Nguy hơn con số:
   càng kỷ luật (càng chạy nhiều điểm kiểm soát) càng bị phạt → sẽ dẫn tới bỏ điểm kiểm soát.
   Méo mó DSR thì không đáng kể (N 114→134 chỉ nâng ngưỡng √(2·ln N) +1,7%).

   **Sổ hiện tại:** 12 sự kiện / 4 trial, **tất cả B0, chưa có dòng CTRL nào** → chưa có thiệt hại,
   không phải viết lại sổ. Đây là thời điểm rẻ nhất để sửa.

   **Việc còn lại:** ghi quyết định vào `back-end-note.md` mục 7 (**mở rộng MT-02**, không tạo mục
   mới — cùng một quyết định đang thiếu phần thi hành) + tạo việc TD tương ứng. Dashboard front-end
   **chờ backend sửa xong mới đổi theo** (nó tồn tại để soi lệch số; đổi trước là tự tạo lệch giả).
   Chi tiết phân tích: mục `OQ-FE-03` trong `TASKS.md` của repo front-end.

**Ghi chú song song (phiên chạy TD-0070, tách khỏi Khối 5 mà phiên kia đang làm):**
TD-0070 ✅ Xong 06/09/2026 — **Khối 7 (Lockbox)** mở đầu: `src/tool_d/lockbox/seal.py`
(`build_seal`/`write_seal` bất biến — từ chối ghi đè/`verify_seal` cho L-Z14) +
`access_log.py` (sổ JSONL append-only, tối đa 3 đoạn niêm phong không trùng seal cho
L-Z13). Chưa đụng dữ liệu lockbox thật (N2 — D0-PRE chưa đóng), toàn bộ test dùng
seal/dữ liệu giả trong `tmp_path`. `docker compose run --rm tests -k "lz13 or lz14"` →
25 passed; toàn bộ `pytest` → 224 passed. TD-0071/TD-0072 (Khối 7, còn lại) vẫn 🔓.
