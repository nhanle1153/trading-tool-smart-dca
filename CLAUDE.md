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

---

## TRẠNG THÁI HIỆN TẠI

**Cập nhật lần cuối: 06/09/2026**

> ⚠️ **Hai phiên Claude Code cùng làm việc song song trên repo này** (chủ dự án xác nhận).
> Mục này có thể lệch nhịp vài phút so với phiên kia — luôn `git log --oneline` +
> đọc lại `TASKS.md` (cột 🔓/🔒/✅) trước khi chọn việc tiếp theo, đừng chỉ tin mục này.

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
   **Không tự chọn bên nào** — chờ chủ dự án quyết khi tới lượt nối API.

**Ghi chú song song (phiên chạy TD-0070, tách khỏi Khối 5 mà phiên kia đang làm):**
TD-0070 ✅ Xong 06/09/2026 — **Khối 7 (Lockbox)** mở đầu: `src/tool_d/lockbox/seal.py`
(`build_seal`/`write_seal` bất biến — từ chối ghi đè/`verify_seal` cho L-Z14) +
`access_log.py` (sổ JSONL append-only, tối đa 3 đoạn niêm phong không trùng seal cho
L-Z13). Chưa đụng dữ liệu lockbox thật (N2 — D0-PRE chưa đóng), toàn bộ test dùng
seal/dữ liệu giả trong `tmp_path`. `docker compose run --rm tests -k "lz13 or lz14"` →
25 passed; toàn bộ `pytest` → 224 passed. TD-0071/TD-0072 (Khối 7, còn lại) vẫn 🔓.
