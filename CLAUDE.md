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

⚠️ **Ngoại lệ hẹp cho `tu-dien-du-lieu.md` — xem N13:** phần do MÁY SINH (cột *"nơi đọc"*) được sinh
lại cùng commit code, không cần lệnh trên. Phần NGHĨA của cột vẫn theo N9.

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

### N12 — 🔴 Kỷ luật git khi nhiều phiên cùng sửa một thư mục đĩa (chủ dự án chốt lại 26/09/2026, `TD-0429`)

> **Đảo `TD-0417`** (25/09/2026 chốt *"một phiên duy nhất"*). Mục 1–7 dưới đây chép **nguyên văn** từ
> `docs/lich-su/N12-nhieu-phien.md` (bản đã dùng tới 25/09). Mục 8 giữ các điều của bản rút gọn 25/09 mà bản cũ không có.


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

8. **Giữ từ bản rút gọn 25/09/2026 (`TD-0417`), vẫn hiệu lực:**
   a. **Phiên IDEA/CHỌN sạch (DR-009) chạy ở thư mục RIÊNG ngoài repo**, dựng bằng `scripts/tao_phien_sach.py` — không bao
      giờ mở trong repo, dù có bao nhiêu phiên.
   b. **Commit file MỚI:** `git add <f> && git commit -F <msg> -- <f>` trong CÙNG một lệnh. Soạn message ra file trước.
   c. **Dịch vụ chạy dài (dry-run, D10) đọc thẳng thư mục làm việc:** sửa cấu hình chưa commit sẽ có hiệu lực ở lần khởi động
      lại kế tiếp (`MT-86`) — commit ngay hoặc dừng dịch vụ trước khi sửa. Với nhiều phiên: sửa dở của phiên KHÁC cũng lọt vào.
   d. **Trước full suite:** `docker info` chạy được (daemon tắt thì `docker ps` rỗng giả) rồi `docker ps` không có container
      test nào khác; giữ trọn output rồi mới lọc.
   e. **Chỉ dừng container theo ĐÚNG ID mình khởi**, không lọc theo tên (`docker-tests-run…` là tên chung của mọi phiên).
   f. **Tiêu một suất trial là đổi trạng thái sổ thật:** sửa dây `tests/unit/test_registry_schemas.py::_kiem_so_that` kèm DR
      trong cùng đợt, và chạy lại full suite SAU khi tiêu suất.

### N13 — `tu-dien-du-lieu.md`: phần máy sinh đi cùng code, phần nghĩa đi qua người

Chủ dự án chốt 17/09/2026 (phiên `-33`, phương án do phiên `-30` nêu). **Vì sao:** từ TD-0245 từ điển là
**sản phẩm máy sinh**, và test `test_td0245_…::test_khop_tung_ky_tu_voi_ban_sinh_lai` so file trên đĩa với
bản sinh lại **từng ký tự**. Bộ sinh quét `src/tool_d/**/*.py` để dựng cột *"nơi đọc"*, nên **mọi commit hợp
lệ thêm một chỗ đọc cột DB Freqtrade đều làm suite đỏ** cho tới khi sinh lại. Nếu áp N9 cho cả file thì
suite đỏ theo nhịp code D9–D11, rồi *"N failed"* thành bình thường và một ca đỏ thật lẫn vào (đúng chuyện
ca `idea_queue` đỏ ~2,5 ngày không ai nhận, 14–16/09).

1. **Cột "nơi đọc" = chỉ mục dẫn xuất.** Code mới làm lệch cột này thì chạy
   `docker compose -f docker/docker-compose.yml run --rm freqtrade -m tool_d.tu_dien.ghi_tu_dien`
   và commit file sinh lại **cùng đợt với code gây ra nó**, không cần "chuẩn hóa và lưu".
2. **Trước khi commit, đọc `git diff -- tu-dien-du-lieu.md`.** Diff chỉ được đổi ô *"nơi đọc"*. Có bất kỳ
   thay đổi nào khác (nghĩa, kiểu, cột mới/mất) ⇒ **dừng**, quay về N9.
3. 🔴 **Điều kiện bắt buộc, không phải trang trí:** một chỗ đọc mới chỉ hợp lệ khi cột đó **đã có nghĩa được
   duyệt** trong `src/tool_d/tu_dien/y_nghia_cot.py`. Máy đã thi hành: `kiem_quy_tac_7()` báo
   `DOC-COT-CHUA-TRA` (test `TestBQuyTac7CoMay::test_khong_co_vi_pham`). Ca đó đỏ thì **không** được sinh lại
   cho xanh. Thêm nghĩa cho một cột vẫn là việc của N9 + Quy tắc 7.
4. Đo lại schema, Freqtrade nâng cấp, đổi `y_nghia_cot.py`: **vẫn theo N9**, không thuộc ngoại lệ này.

---

## TRẠNG THÁI HIỆN TẠI

**Cập nhật: 25/09/2026, phiên mã `12c579bc`.** Mục này chỉ TRỎ, không chép số. Đĩa thắng mục này: đọc `git log`,
`TASKS.md`, `registry/`, `back-end-note.md` mục 7 trước khi chọn việc. Lịch sử trước ngày này (có số kết quả — phiên
IDEA/CHỌN không đọc): `docs/lich-su/trang-thai-den-25-09-2026.md`.

- **Chỉ chạy LONG, không tiền:** dry-run D11 Zone Absorption LONG chạy lại 25/09/2026 (`TD-0423`, quan sát — KHÔNG lật
  `DR-ZA-01`); D10 không chạy; `enable_short: false` (`DR-SHORT-03`).
- **Zone Absorption LONG:** loại (`DR-ZA-01`). ZA SHORT: dựng code, không đo (`DR-SHORT-01`/`-03`).
- **Ứng viên suất (d) `IQ-0003`:** dừng ở WFO, INCONCLUSIVE vì thiếu độ mạnh thống kê (`DR-KET-CUC-IQ0003-01`). Lockbox
  `[T2,T3]` CHƯA chạm.
- **Ngân sách trial:** đọc bằng máy (E6 `trial_ledger_audit.py`), không ghi con số ở đây.
- **Khối 39 xong** (`TD-0417`…`TD-0420`): một phiên duy nhất (⟲ đảo lại 26/09/2026 — quay lại nhiều phiên, `TD-0429`), `CLAUDE.md` gọn, script phiên sạch, vòng đời chung cho ứng
  viên (`DR-VONG-DOI-01`) + tiêu chí chọn quý 1/2027 (`DR-Q1-2027`, hạn ngạch 1, độ mạnh thống kê ≥ 50%). `[T2,T3]` chuyển cho
  ứng viên kế tiếp (`DR-LOCKBOX-04` bổ sung).
- **Bước kế tiếp:** cửa CHỌN đã mở từ 25/09/2026 (`DR-IQ-04`, dùng trước lượt quý 1/2027, `TD-0421`) — chủ dự án chạy
  `python scripts/tao_phien_sach.py --tieu-chi docs/decisions/DR-Q1-2027-tieu-chi-chon-y-tuong.md`.
- **Mâu thuẫn chờ chủ dự án:** `back-end-note.md` mục 7, các dòng 🟡 chưa giải.
- **Phiên ý tưởng sạch:** chạy `python scripts/tao_phien_sach.py` (xem `docs/phien-sach/`), mở phiên Claude MỚI trong thư
  mục nó tạo — không mở trong repo.
