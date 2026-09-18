# DR-FAI-01 — Mở lại §0c.2 cho FreqAI

## ⛔ ĐÃ ĐÓNG 18/09/2026 — đọc mục này trước mọi thứ bên dưới

> **Chủ dự án quyết 18/09/2026: ĐÓNG Khối 17.** `TD-0216…TD-0225` → ❌. Chủ dự án chọn phương án
> *"Đóng Khối 17, giữ hồ sơ"* trong ba phương án do phiên mã `4168d1eb` trình (đó là phương án được
> đánh dấu "Đề xuất"; hai phương án kia: tạm dừng không ai giữ · tiếp tục và điền năm ô).
>
> **DR này KHÔNG có hiệu lực và sẽ không bao giờ có.** Các ô `__CHUA_DIEN__` bên dưới **giữ nguyên, không
> điền** — phép kiểm ở đầu tài liệu cố ý vẫn khác 0. Toàn bộ nội dung từ "TRẠNG THÁI: BẢN NHÁP" trở xuống
> là **bản nháp gốc, giữ nguyên chữ**, lưu làm hồ sơ.
>
> **Hệ quả:** lệnh cấm FreqAI giữ **nguyên hiệu lực đầy đủ** — spec §0c.2 (`:462-473`), `CLAUDE.md` N3,
> test khoá `L-Z24`, `config/freqtrade/config.json` không có khoá `freqai`. Quyết định 12/09/2026 *"Tool D
> sẽ dùng FreqAI"* được **thay** bằng quyết định này.

**Vì sao đóng — cả bốn điều đọc từ chính bản nháp và từ đĩa, không suy:**

1. **Đường A (FreqAI trong Tool D) đã tự đóng** bởi quyết định hạ tầng cùng ngày 12/09 của chủ dự án —
   giữ nguyên digest ảnh Docker, không thêm thư viện ML (§4b bên dưới). Ảnh đó **không import nổi FreqAI**
   (`TD-0219`: thiếu `datasieve`).
2. **Đường B (giả thuyết riêng) cần một GIẢ THUYẾT, không phải một công cụ** (§5.2, đính chính 13/09):
   hàng chờ ý tưởng từ chối đơn thiếu `who_pays`, và *"dùng FreqAI"* là phương pháp — không trả lời được
   *"ai trả tiền cho lợi thế này"*.
3. **Năm ô quyết định trống từ 12/09**, và khoá `TD-0216` **mồ côi**: phiên viết bản nháp (mã phiên
   `869c86a0`, tên lúc đó `-70`) hoạt động lần cuối **13/09 17:06**; file nằm ngoài git 5 ngày, có rủi ro
   bị một commit không pathspec của phiên khác gom nhầm (`CLAUDE.md` N12 mục 7f).
4. `DR-IQ-01` (17/09) và `DR-HUONG-01` (18/09) đặt **suất (d)** làm hướng chính; không DR nào sau 12/09
   nhắc tới FreqAI hay Khối 17.

**Đường quay lại — đóng không có nghĩa là cấm thêm:** ML/FreqAI chỉ quay lại được như **PHƯƠNG PHÁP của
một ý tưởng** đi qua Idea Queue — phiên IDEA sạch nộp, có `who_pays`, qua cửa CHỌN, ngân sách và lockbox
riêng (đúng chữ spec `:472-473`). Khi đó **mở một DR MỚI**; **không** mở lại DR này, **không** dựng lại
Khối 17. Phân tích §3–§9 bên dưới dùng lại được làm tư liệu cho DR mới đó.

**Không đổi gì:** `L-Z24` · config · `Dockerfile` · `N = 114` · rào DSR `3,0777` · sổ trial (0 dòng mới).
`MT-32` — mã đã giữ chỗ cho đầu ra `TD-0217` — **để trống vĩnh viễn**, số không tái sử dụng.

⚠️ **Phiên viết mục ĐÓNG này đã đọc kết quả Tool D** (nhiễm theo DR-009), nên nó **không** đề xuất ý
tưởng nào dùng ML — chỉ ghi đường quay lại.

---

> **TRẠNG THÁI: 🔴 BẢN NHÁP — CHƯA CHỐT.** Mọi ô mang lính canh `__CHUA_DIEN__` là **quyết định
> của chủ dự án**, không phải của tôi. Chừng nào còn **một** ô chưa điền thì DR này **chưa có hiệu lực**,
> và `TD-0217…TD-0225` **chưa được phép chạm một dòng mã nào**.
>
> 🔴 **Phép kiểm, cố ý KHÔNG viết bằng một con số:**
> `grep -cE '^[A-Z_]+:.*__CHUA_DIEN__' docs/decisions/DR-FAI-01-*.md` → phải bằng **0**.
> Neo vào **dạng khai báo** (`KHOÁ: giá trị` ở đầu dòng) chứ không vào dấu chấm lửng — bản vá đầu
> dùng `grep` đếm `......` và **tự khớp với chính dòng lệnh của nó**, nên không bao giờ về 0.
>
> ⚠️ **`__CHUA_DIEN__` KHÔNG phải thứ N6 cấm — phòng trước để người sau khỏi bắt nhầm.** N6 cấm
> **giá trị lính canh** (`-1`, `"UNKNOWN"`, `""`) vì chúng **chảy được vào phép tính** và trông
> như dữ liệu thật. Lính canh ở đây ngược hẳn: nó nằm trong **văn bản quyết định**, không đi qua
> `resolve()` nào, **không chảy đi đâu được**; và có một **cái máy bắt buộc nó phải biến mất**
> trước khi DR có hiệu lực. Lính canh mà máy đếm về 0 là **fail-closed**; lính canh mà **không ai
> đếm** mới là thứ N6 cấm.
> Bản đầu ghi *"bốn ô"* bằng tay; đợt sửa §5.2b thêm ô thứ năm mà con số đó **không ai sửa** ⇒ một
> chốt fail-closed **tự nới ra mà không ai đụng vào nó** (phiên `[3f7d14]` bắt). Không có con số
> nào thì không có gì để lỗi thời.
>
> Lập 12/09/2026 · `TD-0216` · **0 trial** (không đánh giá cấu hình nào trên CALIB/WFO/LOCKBOX)

---

## §0 — Địa vị của tài liệu này

Đây là **giấy tờ quyết định**, không phải nguồn sự thật kỹ thuật. Thứ tự N1 giữ nguyên:
`tool-d-smart-dca.md` (v8) thắng mọi thứ. DR này **không sửa spec** (quy tắc 5) — spec giữ nguyên
chữ *"MODULE CẤM TUYỆT ĐỐI"*; DR là chỗ ghi rằng chủ dự án đã quyết khác, và ghi **cái giá**.

Commit **RIÊNG và TRƯỚC** mọi dòng mã của Khối 17 — cùng kỷ luật `DR-D4-01`/`DR-D4-08`/`DR-D4-10`.
Lý do không phải thủ tục: một DR viết **sau** khi đã thấy kết quả thì không ai phân biệt được
*"quyết định"* với *"giải thích cho việc đã xảy ra"*.

---

## §1 — Điều đang bị mở lại, nguyên văn

`tool-d-smart-dca.md:462-473` (§0c.2):

> ❌ **FREQAI — huấn luyện lại liên tục = số phép thử ngầm VÔ HẠN**
> […] Ba lý do không tương thích:
> **(a)** Không đếm được N → DSR vô nghĩa
> **(b)** Backtest thật của FreqAI tốn thời gian tương đương chạy dry → KHÔNG chạy được GATE D0.9
> **(c)** Mô hình tự thích ứng KHÔNG BAO GIỜ *"sai"* một cách quan sát được — nó chỉ thích ứng.
> Ngược lại toàn bộ triết lý bác-bỏ-được.
> **Muốn thử ML → đó là GIẢ THUYẾT RIÊNG, ngân sách riêng, lockbox riêng. Không phải nâng cấp
> cho Tool D.**

Đang thi hành lệnh cấm này: `CLAUDE.md` **N3**, test khoá **`L-Z24`**
(`tests/lock/test_lz24_freqtrade_config_flags.py`), và `config/freqtrade/config.json` cố ý
**không có khoá `freqai`**.

**Chủ dự án chốt ngày 12/09/2026: Tool D sẽ dùng FreqAI.** DR này thi hành quyết định đó.

---

## §2 — 🔴 LÝ DO MỞ *(ô trống — chủ dự án điền)*

```
LY_DO_MO: __CHUA_DIEN__
```

**Vì sao ô này bắt buộc, và vì sao nó không phải hình thức.** Sáu tháng nữa, người đọc `Khối 17`
sẽ phải trả lời được câu *"vì sao dự án mở một thứ nó từng cấm tuyệt đối"* mà không cần hỏi ai.
Nếu ô này trống, cách đọc mặc định sẽ là cách đọc **sai và tiện nhất**: *"FreqAI là cách gỡ bế
tắc D4"* — §3 dưới đây chứng minh nó sai.

🔴 **Một tiền đề bị loại trước, bằng số:** nếu lý do mở là *"để cải thiện kết quả"* thì tiền đề đó
**sai** và phải được ghi là sai ngay tại đây, không phải phát hiện sau. Xem §3.

🔴 **Và lý do mở phải khai ĐỘC LẬP VỚI D4 — ràng buộc thêm 12/09/2026 sau khi `MT-29` chốt.**
Hai quyết định cùng ngày (`MT-29` sàn-mỗi-hướng ⇒ D4 Long dừng; và quyết định mở FreqAI) **không
có quan hệ nhân quả**. Nếu ô này khai bất kỳ chữ nào ngụ ý FreqAI gỡ được D4, nó **va thẳng vào
`MT-29` vừa chốt**: FreqAI không sinh thêm một lệnh nào, mà nhóm arm chính chỉ có `n = 28`.
Viết rời nhau để sáu tháng nữa không ai đọc hai quyết định này thành **một chuỗi nhân quả không
có thật**.

---

## §3 — Thứ FreqAI KHÔNG giải, đo được chứ không suy đoán

| Đại lượng | Đo được | Nguồn |
|---|---|---|
| `n` — số lệnh arm chính trên cửa sổ WFO | **28** | `TD-0205`, `docs/du-lieu-do/td0205-lenh-nam-wfo-explore.json` |
| `n` cần để **một** arm thôi INCONCLUSIVE | **≥ 319** | `DR-D4-10 §1.2` |
| Lệnh/năm quy đổi pool 102 | **44,8** | `TD-0207` (đã đo lại sau bản vá) |
| Sàn của chính spec | **150 lệnh/năm** | `tool-d-smart-dca.md:4274` |
| Sàn đó áp cho **MỖI HƯỚNG**, không phải tổng | **đã chốt 12/09/2026** | `MT-29` phương án (A), `back-end-note.md:118` |

🔴 **Cập nhật cùng ngày:** `MT-29` chốt sàn 150 lệnh/năm áp cho **mỗi hướng**, nên `44,8 < 150` là
một **fail dứt khoát cho arm `Z0`** — không còn là con số đang chờ ai quyết.

🔴 **ĐÍNH CHÍNH tại chỗ (cùng ngày, phiên `[3f7d14]` bắt) — bản đầu của mục này viết thêm câu
*"D4 Long-only KHÔNG CHẠY, 0 suất trial tiêu"*. Câu đó SAI, và tôi tự kiểm `td0212` trước khi
sửa:**

| arm | số lệnh | lệnh/năm quy đổi pool 102 | vs sàn 150 |
|---|---|---|---|
| `Z0-T0` | 686 | **1.396,0** | ✅ vượt |
| `Z0-T1` | 160 | **325,6** | ✅ vượt |
| `Z0` | 22 | **44,8** | ❌ trượt |

⇒ `44,8` là số của **một arm**, không phải của D4. Câu cũ đúng với **7/9 arm** và **sai với hai
arm Phần 2**; tệ hơn, nó **ngầm trả lời câu 1 của `MT-26`** (*"`Z0-T0`/`Z0-T1` có phải cấu hình
ứng viên không"*) trong khi `MT-26` lúc đó ghi CHƯA GIẢI. `MT-26` nay đã chốt **phương án (C)**:
`Z0-T1` là **cấu hình ỨNG VIÊN**, `Z0-T0` chỉ là arm **CHẨN ĐOÁN** ⇒ D4 có **đúng một ứng viên
vượt sàn**, không phải không có ứng viên nào.

🔑 **Vì sao câu sai đó lọt vào đây — ghi lại vì nó là hình dạng lỗi của cả ngày 12/09:** nó
**không phải** kết quả tôi đo. Nó là một **tóm tắt do phiên khác chuyển sang**; tôi kiểm
`back-end-note.md:118` thấy `MT-29` có thật, rồi **nhận luôn phần hệ quả mà không kiểm số theo
từng arm**. **Kiểm một nửa rồi tin cả câu.** Bài học đúng cho người đọc sau: một dẫn chiếu có
thật **không** chứng minh phần suy ra từ nó.

**Đặt một tầng học máy lên 28 mẫu làm bài toán overfitting NẶNG HƠN, không nhẹ đi.** Một mô hình
LightGBM/torch mang hàng nghìn tham số; `N = 114` của DR-010 được dựng cho một hệ thống có **12**
bậc tự do đếm được. Tỉ lệ mẫu-trên-bậc-tự-do là thứ FreqAI làm xấu đi, không cải thiện.

⚠️ Câu này **không** nói FreqAI vô dụng. Nó nói: bất kỳ lý do mở nào dựa trên *"có thêm mô hình
thì kết quả sẽ khá hơn ở cùng lượng dữ liệu này"* đều **đã bị một phép đo bác trước**.

---

## §4 — Ba lý do cấm của spec: trả lời từng cái

Không lý do nào được bỏ qua im lặng. Mỗi cái hoặc **được giải**, hoặc **được khai là rủi ro chấp
nhận có ý thức** — ghi rõ ai chấp nhận và đổi lấy gì.

### (a) Không đếm được N → DSR vô nghĩa — **KHÔNG GIẢI ĐƯỢC, chỉ chọn cách sống chung**

`src/tool_d/gates/dsr.py:24` ghim `N_DANG_KY = 114` ⇒ rào `√(2·ln N) = 3,0777`. Bậc tự do **thực
tế** của một mô hình học được là số tham số của mô hình, không phải số khoá trong config. Ba đường
ra ở §5; **phải chọn đúng một**, và cả ba đều có giá.

🔴 **Không được để trống rồi chạy trước tính sau.** N6: ngưỡng chưa điền = `+inf`, để cổng **không
thể vô tình PASS**.

🔴 **(a) KHÁC HẠNG với vấn đề cỡ mẫu, đừng xếp chung** (phiên `[67bb21]` nêu, nhận): cỡ mẫu là
*"`n` quá nhỏ"* — **đo được**, và về nguyên tắc **cộng thêm được**. *Không đếm được `N`* thì không
đo được và không cộng được. Hệ quả cụ thể: Nhánh 1 §10.2 đứng trên **HAI** rào cùng phục vụ *"đủ
mẫu để kết luận"* — **sàn 150 lệnh/năm mỗi hướng** (`MT-29`, thô) và **rào DSR `√(2·ln N)`**
(tinh). Cỡ mẫu nhỏ làm hỏng **một** rào. `N` không đếm được làm hỏng **cả hai** — vì rào tinh mất
nghĩa, còn rào thô thì một mình nó chưa bao giờ đủ để phán quyết.

⇒ Vì thế `§5.4` (kế toán trial khi retrain) là ô **khó nhất và quan trọng nhất** trong năm ô, không
phải `§5.2b`. `§5.2b` chọn sai thì ta đo một thứ không phán quyết được; `§5.4` chọn sai thì **không
còn cái thước nào cả**.

### (b) Backtest FreqAI tốn thời gian tương đương chạy dry → không chạy được GATE D0.9 — **ĐO ĐƯỢC, chưa ai đo**

Đây là lý do **duy nhất trong ba cái có thể biến thành một con số**.

🔴 **Phép đo chạy trên EXPLORE, KHÔNG chạm CALIB/WFO ⇒ 0 trial** (tiền lệ `TD-0193`/`TD-0205`/
`DR-D4-08 §6`). Bản nháp đầu viết *"trên cửa sổ WFO với pool thật"* — làm đúng chữ đó thì theo
`DR-014 §2` nó là một **đánh giá cấu hình ⇒ tiêu một trial**, và **buộc phải chốt `§5.4` trước khi
bấm nút**, tức phép đo rẻ nhất của DR này lại bị khoá sau ô khó nhất của nó. Thời gian tường của
một lượt backtest **không phụ thuộc dữ liệu thuộc phân vùng nào**, nên EXPLORE trả lời đúng câu
§4(b) hỏi mà không tiêu suất nào (phiên `[3f7d14]` nêu).

🔴 **Điều kiện dừng, viết TRƯỚC khi chạy** (khuôn `DR-D4-08 §6`): `TD-0219` cho thấy ảnh Docker
**không có thư viện ML**, **hoặc** thời gian tường **vượt ngân sách thời gian của GATE D0.9** ⇒
**DỪNG, trình chủ dự án** — không tự nới, không tự đổi phạm vi. Viết trước để kết quả **không thể**
bị đọc thành *"chỉ cần chờ lâu hơn"*.

🔴 **Và phải đo SỚM, vì nó quyết định CẤU TRÚC của DR này chứ không phải một chi tiết.** Nếu chữ
của spec đúng — backtest FreqAI tốn thời gian cỡ một lượt dry-run — thì mọi kế hoạch đánh giá
FreqAI qua D4/D9 **không chạy được về mặt vật lý**, và khi đó §6 phải chọn phạm vi khác chứ không
phải tìm cách chờ lâu hơn. Đây là lý do `TD-0219` (ảnh Docker) đứng ngay sau `TD-0217` ở §10.

### (c) Mô hình tự thích ứng không bao giờ *"sai"* quan sát được — **KHÔNG GIẢI ĐƯỢC, và đây là cái nặng nhất**

Đây không phải lo ngại kỹ thuật, nó là lo ngại **nhận thức luận**, và nó đánh vào đúng thứ Tool D
được dựng để bảo vệ: một phát biểu bác bỏ được. Một chiến lược rule-based sai thì sai **quan sát
được** — DG2 chặn nhầm, TP1 rơi nạng 100%, `_zone_dinh_tren` đọc sai cột. Cả ba lỗi đó **đã được
bắt trong tuần này** đúng vì hệ thống không tự điều chỉnh để che chúng.

Một mô hình huấn luyện lại liên tục thì không có trạng thái *"sai"* — nó có trạng thái *"đã thích
ứng"*. Hệ quả cụ thể, không trừu tượng: **§10.2 Nhánh 1 và cả tầng chẩn đoán §0d.7 (N10) mất điểm
tựa.** N10 hỏi *"lệnh THẬT có đúng thiết kế không?"* — câu đó chỉ trả lời được khi có một **thiết
kế cố định** để đối chiếu.

🔴 **Không có phương án kỹ thuật nào trong tài liệu này giải quyết (c).** Nếu chấp nhận, phải chấp
nhận tường minh, và §8 phải mang một điều kiện đóng lại **không dựa vào việc mô hình tự khai**.

---

## §4b — 🔴 Đổi ảnh Docker KHÔNG phải chuyện của riêng nhánh FreqAI

`TD-0219` đo được: ảnh đang ghim **không chạy được FreqAI**. Nên nếu đi tiếp thì phải đổi digest — và
**phạm vi của việc đó rộng hơn nhiều so với cách `§9` mục 1 đóng khung** (phiên `[3f7d14]` nêu, nhận).

**Vì sao rộng hơn:** ảnh biến thể `_freqai` có thể khác **cả `pandas`/`numpy`/`ta-lib`**, mà **MỌI**
con số rule-based của dự án — `td0193` → `td0215`, gồm `n = 28`, `44,8 lệnh/năm`, phễu tín hiệu, các
quan hệ tập hợp của `MT-33` — đều đo trên digest `7031bca4…`. Nếu ảnh mới đổi một chữ số ở tầng chỉ
báo thì **toàn bộ nền so sánh của D4 trôi**, không riêng nhánh FreqAI. Đây là rủi ro với **công việc
đã làm xong**, không phải với công việc sắp làm.

### 🔴 Điều kiện TIÊN QUYẾT trước khi đổi digest — biến giả định thành số

> Chạy **đúng một phép đo cũ** trên **cả hai ảnh** và so kết quả — gợi ý: đếm lệnh `Z0` của `td0212`
> (22 lệnh · 44,8/năm · `so_tap_lenh` với `Z0-T1`). **0 trial**, trên **EXPLORE**, vài phút.
>
> - **Trùng khít từng con số** ⇒ đổi digest **an toàn cho toàn bộ nền đã đo**; ghi vào DR như một
>   **dữ kiện**, không phải một hy vọng.
> - **Lệch bất kỳ chỗ nào** ⇒ đổi ảnh **kéo theo phải đo lại nền**, và cái giá đó phải nằm **trên
>   bàn TRƯỚC khi chủ dự án quyết**, không phải phát hiện sau.

Cùng khuôn với thứ vừa cứu `§4(b)`: thay một câu *"chắc là không sao"* bằng một phép kiểm vài phút.

**Đã thử một đường rẻ hơn, và nó KHÔNG kết luận được — ghi lại để người sau khỏi thử lại.**
Giả thuyết (phiên `[3f7d14]` nêu): nếu ảnh `_freqai` được dựng `FROM` chính ảnh thường rồi
`pip install` thêm bộ ML, thì thư viện nền **giống nhau theo cấu trúc** ⇒ khỏi cần phép so hai ảnh.
Kiểm **0 tải, 0 trial** ngày 12/09: (i) tìm `Dockerfile*` trong `/freqtrade` của ảnh đang chạy →
**rỗng** (bản cài editable không mang theo thư mục `docker/`); (ii) `docker history` trên digest
đang ghim → **`No such image`** (máy chỉ giữ các ảnh *dẫn xuất* đã build, không giữ base rời).
⇒ **Giả thuyết chưa bác được, cũng chưa xác nhận được bằng dữ liệu tại chỗ.** Muốn trả lời thì
phải đọc `Dockerfile.freqai` từ kho nguồn Freqtrade (tiền lệ `TD-0028`) — **chưa làm**. Chừng nào
chưa có câu trả lời đó thì **phép so hai ảnh ở trên vẫn BẮT BUỘC**, không được bỏ vì *"chắc là
`FROM` ảnh thường"*.

### 🔴 ĐƯỜNG THỨ BA — đo được 12/09, và nó gỡ mâu thuẫn mà hai phương án kia tạo ra

Cả `§4b` ở trên lẫn mọi trao đổi trước đó đóng khung lựa chọn thành **nhị phân**: *giữ digest đang
ghim* **hoặc** *đổi sang ảnh `_freqai`*. **Khung đó thiếu một đường**, và bỏ sót nó tạo ra một mâu
thuẫn không cần thiết: `TD-0219` đo được ảnh hiện tại **không chạy nổi FreqAI**, nên *"giữ nguyên
digest"* + *"Tool D sẽ dùng FreqAI"* là hai câu **không thể cùng đúng**.

**Đường bị bỏ sót:** ảnh ta chạy **không phải** ảnh gốc — `docker/Dockerfile` dựng một ảnh **DẪN
XUẤT** `FROM freqtradeorg/freqtrade@sha256:7031bca4…` rồi `pip install --user pytest pyyaml
jsonschema`. Thêm hai gói ML **vào chính bước đó** thì **base digest giữ nguyên**.

**Đo (12/09, `pip install --dry-run` trong container, 0 trial, không cài gì):**

```
Requirement already satisfied: pandas        3.0.5      (từ datasieve)
Requirement already satisfied: numpy         2.4.6      (từ lightgbm)
Requirement already satisfied: scikit-learn  1.9.0
Requirement already satisfied: scipy         1.17.1
Requirement already satisfied: joblib        1.5.3
Would install datasieve-0.1.9 lightgbm-4.7.0
```

⇒ **Cài đúng HAI gói. Không gói nào đang có bị nâng cấp** — `pandas`/`numpy`/`scikit-learn`/`scipy`
đều **already satisfied**. Tức **tầng chỉ báo không đổi một chữ số**, nên nền so sánh
`td0193 → td0215` **đứng nguyên**, và **phép so hai ảnh ở điều 3 không cần chạy** — không phải vì
ta chấp nhận rủi ro, mà vì **đã đo và rủi ro đó bằng không**.

**Ba điều phải khai kèm, không được bỏ:**
1. **Ghim phiên bản chính xác** (`datasieve==0.1.9`, `lightgbm==4.7.0`) — cùng kỷ luật `pytest==9.1.1`
   đã có trong `Dockerfile`. `--dry-run` hôm nay **không bảo đảm** lần giải phụ thuộc sau giống hệt.
2. **Đường này KHÔNG im lặng — nhưng phải quy công đúng cơ chế.** Bản đầu của mục này ghi *"nhờ
   `TD-0229` `cache_key()` gộp `runtime_image_digest`"*. **Sai chỗ quy công:** đọc
   `provenance.py:84` — `doc_runtime_image_digest()` lấy dòng `FROM …@sha256:` của
   `docker/Dockerfile`, tức **digest ảnh GỐC**, mà đường thứ ba **không đổi** dòng đó. Thứ thật sự
   bắt được là **`git_sha`**: `Dockerfile` nằm trong git, thêm hai dòng `pip install` là commit đổi
   ⇒ `cache_key` đổi ⇒ không dùng lại kết quả cũ được. Ba mức, phải phân biệt:

   | Thay đổi | Bị bắt bởi |
   |---|---|
   | đổi dòng `FROM` (base digest) | ✅ **cả** `git_sha` **và** `runtime_image_digest` |
   | thêm gói pip vào `Dockerfile`, **đã commit** ← *đường thứ ba* | ✅ **`git_sha`** |
   | dựng lại ảnh từ `Dockerfile` **chưa commit**, hoặc `pip install` trong container đang chạy | ❌ **không gì cả** |

   🔴 Dòng thứ ba là **khoảng hở còn nguyên**, và nó còn nguyên vì mọi lớp canh môi trường đều canh
   **mô tả của ảnh** (`Dockerfile` trong git), **không canh ảnh đang chạy** (phiên `[3f7d14]` đính
   chính phạm vi `TD-0229` của chính họ). Đóng nó cần digest ảnh **dẫn xuất** lúc chạy — `docker
   history` đã thử và thất bại (xem trên). ⇒ **Đường thứ ba buộc phải commit `Dockerfile` TRƯỚC khi
   dựng lại ảnh**, không được sửa tay rồi build.

   Ba điều kiện tiên quyết `§7.1` **không phải viện tới**: `L-Z40` và `REQUIRED_PROVENANCE_KEYS`
   (7, đúng tập spec §0d.5 đòi) **không bị sửa** — `TD-0229` tách hằng riêng `KHOA_XUAT_XU_TOOL_D`.
3. `torch`/`catboost`/`xgboost` **chưa cần** — `lightgbm` là mô hình mặc định của FreqAI. Thêm gói
   nào là quyết định của `§6`, và mỗi gói thêm phải chạy lại chính phép `--dry-run` này.

⚠️ Đường này **không** trả lời *có nên dùng FreqAI hay không* — nó chỉ gỡ bỏ cái chặn hạ tầng, và
làm điều đó **mà không đụng một con số đã đo nào**.

🔴 **VÀ NÓ KHÔNG GIẢI BÀI TOÁN QUẢN TRỊ — phải đọc kèm, nếu không thì khung ba ô cũng hẹp, chỉ
hẹp theo chiều khác** (phiên `[3f7d14]` nêu, nhận). Spec `:472-473` đòi ML là *"giả thuyết riêng,
**ngân sách riêng, lockbox riêng**"*. Đường thứ ba đặt hai gói ML vào **ảnh DÙNG CHUNG** của
local–staging–prod — tức đi **ngược chiều** *"riêng"* đó: nó biến FreqAI thành một phần của hạ
tầng chung thay vì một nhánh tách biệt. ⇒ Nó rẻ và an toàn về **kỹ thuật**, nhưng **không** làm
cho `§5` đường A trở nên đúng chữ spec, và **không** thay thế câu hỏi `§6`.

**Ba phương án, đọc theo HAI trục — bảng này là thứ phải trình, không phải một trục:**

| | Kỹ thuật (chạy được? nền so sánh?) | Quản trị (đúng chữ spec `:472-473`?) |
|---|---|---|
| **Giữ nguyên hoàn toàn** | ❌ FreqAI **không chạy được** (`TD-0219`) | ✅ không đụng gì |
| **Đổi sang ảnh `_freqai`** | ⚠️ chạy được, nhưng **chưa biết** nền có trôi không (phép so chưa chạy) | ❌ ảnh chung của cả hệ thống ⇒ ngược *"riêng"* |
| **Đường thứ ba** (thêm 2 gói vào `Dockerfile` của ta) | ✅ chạy được · ✅ nền **đo được là không trôi** | ❌ vẫn là ảnh chung ⇒ ngược *"riêng"* |

⇒ Không ô nào xanh cả hai trục. **Đó chính là nội dung thật của câu hỏi `§6`**, không phải một
chi tiết hạ tầng có thể quyết riêng.

### 🔴 QUYẾT ĐỊNH HẠ TẦNG 12/09/2026, và hệ quả của nó lên `§5`

**Chủ dự án chốt (ghi ở `TASKS.md` TD-0219, commit `e123126`, phiên `[3f7d14]` chuyển): GIỮ NGUYÊN
digest, KHÔNG đổi sang ảnh `_freqai`.** Căn cứ là **quản trị**, không phải hạ tầng: spec `:472-473`
(*"ML → giả thuyết riêng, ngân sách riêng, lockbox riêng"*). Đường thứ ba **không lật** quyết định
đó — nó giải bài toán kỹ thuật, không giải bài toán quản trị (xem bảng hai trục trên).

⚠️ **Địa vị của dòng này:** đây là quyết định **chuyển qua phiên khác**, không phải chủ dự án nói
thẳng với phiên giữ DR. Nó **đã được ghi vào `TASKS.md`** nên có định danh máy đọc; nhưng nếu chủ
dự án đọc lại và thấy khác thì **sửa ở đây trước khi DR có hiệu lực**.

🔴 **HỆ QUẢ, và nó thu hẹp toàn bộ `§5` xuống MỘT câu hỏi:**

1. Giữ digest, **không thêm gói** ⇒ `TD-0219` đã đo: FreqAI **không chạy được**. Vậy **đường A của
   `§5.1` (FreqAI trong Tool D, dùng hạ tầng chung) nay ĐÓNG** — không phải vì ai cấm, mà vì quyết
   định hạ tầng vừa rút mất phương tiện của nó.
2. Còn lại **đường B** — giả thuyết riêng, **hạ tầng riêng** (ảnh riêng là hợp lệ ở đây, vì nó
   không phải ảnh dùng chung của local–staging–prod). Đúng chữ spec `:472-473`, và **nhất quán với
   chính căn cứ của quyết định trên**.
3. Nhưng `§5.2` đã đo: đường B bị chặn bằng máy — `DR-Q3-2026:17` `HAN_NGACH_CHON: 0`, ba điều kiện
   mở lại **đều chưa xảy ra**, và quý sau **mặc định lại 0**.

⇒ **FreqAI hiện KHÔNG CÓ ĐƯỜNG ĐI NÀO mà không đè lên một chốt đã chốt**, và sau quyết định hạ tầng
thì chốt đó **chỉ còn đúng một cái**: `DR-Q3-2026`. Câu hỏi cho chủ dự án vì thế **không còn là**
*"đường nào"* — nó là: ***có viết một DR đè `DR-Q3-2026` để mở cửa chọn cho FreqAI trong quý này
hay không?*** Nếu không, FreqAI **ở lại hàng chờ** cho tới khi một điều kiện mở lại nổ.

📌 Điều này **không mâu thuẫn** với quyết định 12/09 *"Tool D sẽ dùng FreqAI"* — nó chỉ nói **khi
nào** và **theo tư cách nào**. Nhưng nó phải được nói **thẳng**, vì hai quyết định cùng ngày, đọc
rời nhau, cho cảm giác FreqAI đang được tiến hành trong khi **chưa có đường nào mở**.

### ⚠️ Hệ quả parity — là quyết định hạ tầng của TOÀN dự án

Quy tắc 9 đòi local–staging–prod **cùng một ảnh**. Nên nhận ảnh `_freqai` nghĩa là nó thành ảnh của
**cả hệ thống**, kể cả phần rule-based không dùng FreqAI. **Không có kiểu *"ảnh riêng cho nhánh
FreqAI"***. Vì thế đây **không** phải chi tiết triển khai của Khối 17 — nó là một quyết định hạ tầng
đứng ngang hàng với `§6`, và phải được trình như thế.

---

## §5 — Hai đường đi, và mỗi đường va vào một chốt đã chốt

Spec `:471-473` nói thẳng đường nào là đường của nó: *"giả thuyết riêng, ngân sách riêng, lockbox
riêng. **Không phải nâng cấp cho Tool D**"*. Nhưng đường đó có một cánh cửa đang **đóng bằng số**.

### 5.1 Đường A — FreqAI là **sửa đổi của chiến lược hiện tại**

Nằm trong `ZoneAbsorption`, dùng chung `N = 114`, chung lockbox, chung GATE D0.9.

| | |
|---|---|
| Được | Không cần lockbox mới. Không đụng Idea Queue. |
| Mất | Va thẳng lý do **(a)**: `N = 114` không mô tả nổi bậc tự do của một mô hình học ⇒ rào DSR `3,0777` **không còn nghĩa gì** cho nhánh này. Và đi ngược chữ tường minh của spec `:473`. |

### 5.2 Đường B — FreqAI là **giả thuyết riêng** (đúng chữ spec)

Ngân sách riêng, lockbox riêng, đi qua Idea Queue §9c.7.

🔴 **Cánh cửa này đang ĐÓNG BẰNG SỐ, và tôi phát hiện khi kiểm chứ không phải khi đoán:**
`docs/decisions/DR-Q3-2026-tieu-chi-chon-y-tuong.md:17` khai **`HAN_NGACH_CHON: 0`** cho quý này
(quý 3/2026 — hôm nay 12/09/2026 nằm trong quý đó). Dòng `:108` ghi: *"Quý khai `HAN_NGACH_CHON: 0`
mà có dòng `SELECTED` → **sổ bẩn**"*.

Ba điều kiện mở lại cửa chọn (`DR-Q3-2026 §2`) — **không cái nào đã xảy ra**:

| Mã | Điều kiện | Trạng thái hôm nay |
|---|---|---|
| (a) | `mult_edge = 0.5` trên **50 lệnh live** gần nhất | ❌ Tool D có **0 lệnh live** |
| (b) | Một phán quyết **L2** hoặc **L3** | ❌ chưa có phán quyết nào — D4 chưa đóng |
| (c) | **B3 cạn** (20/20) | ❌ `trial_registry.jsonl` 13 dòng, B3 = 0 |

⇒ **Đường B không đi được trong quý này** nếu không có một DR mới đè lên `DR-Q3-2026`. Đây **không
phải** lý do để bỏ đường B — đó là một **cái giá phải biết trước khi chọn**, và nó rất có thể là
lý do khiến chủ dự án chọn khác.

🔴 **ĐÍNH CHÍNH 13/09/2026 — CỬA "NỘP" CŨNG KHÔNG MỞ, và đây mới là cái chặn ĐẦU TIÊN.**
Bản trước của DR này (và hai lần tôi trình chủ dự án) nói *"cửa NỘP đang mở, nộp FreqAI vào hàng
chờ là bước rẻ nhất, 0 trial"*. **SAI** — phiên `[3f7d14]` nêu, tôi tự kiểm mã:

`src/tool_d/ledger/idea_queue.py:53` — `BO_LOC_FIELDS = ("mechanism", "who_pays", "durability")`;
`:258-268` **từ chối ghi** nếu bất kỳ trường nào rỗng **hoặc** bằng `"n/a"`, với lý do ghi thẳng
trong mã: *"`who_pays` là câu giết ý tưởng — không trả lời được AI TRẢ TIỀN thì ý tưởng không vào
hàng chờ (spec dòng 4914)"*. Đường `TOOL_D_RESULTS` cũng không thoát: `:234` bắt buộc
`status = REJECTED`.

🔑 **Vì sao nó chặn: *"dùng FreqAI"* là một PHƯƠNG PHÁP, không phải một GIẢ THUYẾT.** Hàng chờ
nhận *"tồn tại lợi thế X vì bên Y trả tiền, bền vì Z"* — ML là **cách khai thác** một giả thuyết
như thế, không phải bản thân giả thuyết. Một tờ đơn *"dùng FreqAI"* không có `who_pays` nào để
điền, nên nó **không biểu diễn được** trong sổ.

⇒ **Thứ đang thiếu KHÔNG phải một suất chọn — mà là một GIẢ THUYẾT.** Câu *"có đè `DR-Q3-2026`
không"* vẫn là một câu thật, nhưng nó là câu **thứ hai**; đè hạn ngạch mà không có giả thuyết thì
vẫn không nộp nổi một tờ đơn. Và ngược lại: **có** giả thuyết thì cửa NỘP mở (0 trial), chỉ còn
cửa CHỌN vướng hạn ngạch.

📌 Đường mở hợp pháp sẵn có, **chưa phải dữ kiện**: điều kiện **(b)** của `DR-Q3-2026` = *một phán
quyết L2/L3*, mà `DR-D4-09 §2.2` định tuyến **FAIL → xử theo `DR-011`** (nơi phân hạng L1/L2/L3).
`Z0-T1` **FAIL** ⇒ (b) **có thể** nổ hợp pháp. ⚠️ **INCONCLUSIVE thì KHÔNG** — §2.2 ghi rõ nó
*"không phải bằng chứng chống"*. Phân hạng do `DR-011` quyết, **chưa ai chạy**.

🔴 **Và cửa này KHÔNG tự mở lại vào quý sau.** `DR-Q3-2026 §2`: *"Không cái nào xảy ra → quý sau
**MẶC ĐỊNH lại là 0**. Không phải quyết định lại, không phải bàn lại"*. Nên *"chờ sang quý 4"*
**không phải một đường đi** — nó chỉ là đường B bị hoãn mà cửa vẫn đóng y nguyên.

⚠️ Và lockbox: `DR-011` cho **đúng một** lockbox, Zone Absorption **chưa chạm**. Một giả thuyết
mới cần lockbox trên dữ liệu **chưa từng dùng** — dữ liệu sạch tích luỹ khoảng một quý mỗi quý.

### 5.2b 🔴 Số nến lớn giúp HUẤN LUYỆN, KHÔNG giúp PHÁN QUYẾT — đừng trộn hai cổ chai

Một lập luận nghe xuôi và **sai**, đã bị phiên `[3f7d14]` bác, ghi lại để không ai dựng lại nó:
*"`n = 28` là bế tắc ở tầng LỆNH, mà ML học ở tầng NẾN (~213.839 nến trên EXPLORE), nên tách riêng
là đặt FreqAI vào chỗ dữ liệu thật sự có."*

Nửa đầu đúng, **kết luận không theo**. Số nến quyết định việc mô hình có **khớp được tham số** mà
không overfit hay không. Nó **không** đụng tới việc **phán quyết**, vì mọi cổng của dự án đo theo
**LỆNH**: DSR-adjusted expectancy **mỗi lệnh** · sàn **150 lệnh/năm** (`:4274`) · `h/√n` với `n` là
**số lệnh**. ⇒ Một chiến lược ML riêng mà cũng chỉ giao dịch ~45 lệnh/năm thì **va đúng bức tường
cũ**, và lần này **không ai nghi**, vì nó *"đã có 213.839 nến"*.

**Câu đúng:** đường B đáng chọn vì một chiến lược riêng **được tự do chọn tần suất giao dịch mà
cổng của chính nó phán quyết được** — thứ tầng entry hiện tại của Tool D (zone + lọc trend 1D +
§3.3b, cắt 97,1%) không cho phép. Tách riêng chỉ **CHO PHÉP** chọn tần suất khác; nó không tự tạo
ra tần suất đó.

🔴 **Ràng buộc kéo ra từ đây, bắt buộc nếu chọn đường B:** phải khai **tần suất lệnh mục tiêu
TRƯỚC khi dựng**, và nó phải ≥ sàn mà cổng của chính nhánh đó dùng. Nếu không, kết cục
INCONCLUSIVE **chứng minh được trước khi chạy** — đúng phép tính `DR-D4-10 §1.2` đã làm cho nhóm C,
và lần đó nó tiết kiệm được chín suất trial.

```
TAN_SUAT_LENH_MUC_TIEU:  __CHUA_DIEN__  lệnh/năm MỖI HƯỚNG   (chuẩn so: 150 — MT-29, KHÔNG dựng chuẩn song song)
```

🔴 **Ô khai này KHÔNG chứng minh gì cả, và phải hiểu đúng việc của nó** (phiên `[3f7d14]` bắt —
bản đầu của mục này là một **PASS RỖNG**): một con số **người viết ra** không phải một con số **đo
được**. Ai cũng khai được `200` rồi dựng ra một thứ chạy `40`, và phép kiểm *"ô khai ≥ sàn"* **vẫn
XANH**. Đúng họ `TD-0082` — *một dòng mô tả việc cũng là lời khai, không phải bằng chứng*.

Việc thật của ô khai: **ghim vạch TRƯỚC khi nhìn thấy số**, chống lại việc hạ mục tiêu sau khi đo.
Thứ **phán quyết** phải là một phép đo:

> **Trước khi đặt chỗ trial đầu tiên cho nhánh này:** đo tần suất lệnh **THẬT** trên EXPLORE
> (**0 trial**, chỉ đếm — tiền lệ `TD-0193`/`TD-0205`/`DR-D4-08 §6`). Đo được **<
> `TAN_SUAT_LENH_MUC_TIEU` đã khai** *hoặc* **< 150 lệnh/năm cho hướng đang xét** ⇒ **DỪNG,
> trình chủ dự án** — không tự nới, không tự chạy tiếp. Ô khai **không thay thế** phép đo.
>
> ⚠️ **Phép đo đó thừa hưởng lệch sống sót của tập mã, phải khai kèm chứ đừng để nó trông sạch hơn
> thực tế** (`MT-34`, phiên `[3f7d14]` mở 12/09): EXPLORE cũng là **ảnh chụp hôm nay**, dựng từ
> danh sách mã **đang niêm yết**. Đo sơ bộ trên pool 102: **43,1% mã không tồn tại tại `T0`**,
> **23,5% không tồn tại tại `T1`**.
>
> 🔴 **Hai đại lượng, hai chiều lệch KHÁC NHAU — không gộp** (bản đầu của mục này gộp, phiên
> `[3f7d14]` bắt):
>
> | Đại lượng | Chiều lệch của kênh sống sót |
> |---|---|
> | **Expectancy / `mean_R`** | **LÊN — chiều PASS.** Mã sập thì rời sàn, không vào mẫu; mẫu còn lại đẹp hơn trung bình thật |
> | **Tần suất lệnh (lệnh/năm)** — *chính là thứ `§5.2b` đo* | 🔴 **CHƯA XÁC ĐỊNH, không khai chiều** |
>
> Bản đầu viết *"lệnh/năm là **cận trên**"*. Câu đó **chưa có căn cứ**: nó đòi tiền đề *"mã sống
> sót sinh nhiều tín hiệu hơn mã đã chết"*, **chưa ai đo**. Có thể **ngược** — mã sập thường biến
> động mạnh hơn, mà hệ này vào lệnh theo zone + xác nhận, nên nhiều khả năng mã chết sinh **nhiều**
> tín hiệu hơn; nếu thế thì loại chúng ra làm tần suất **THẤP đi** ⇒ lệch **chiều FAIL** ⇒ `§5.2b`
> đang **chặt hơn** thực tế, không lỏng hơn. **Khai sai chiều theo hướng "nghiêm hơn" cũng là một
> lỗi** — đó là *"ảnh trong gương của PASS RỖNG"*: một phép đo không bao giờ chạy, không để lại
> dấu vết nào để nghi.
>
> 📌 **Và đây là lệch THÀNH PHẦN MẪU, không phải lệch ĐỘ DÀI — hai thứ hay bị gộp.** `td0212` ghi
> `ma_nam = 50,12` cho 88 mã trên cửa sổ 0,632 năm ⇒ **0,569 năm/mã < 0,632**, tức kịch bản đo
> **đã** trừ phần dữ liệu thiếu của mã lên sàn muộn. Cái còn lại là *ai có mặt trong mẫu*, không
> phải *mỗi mã có bao nhiêu dữ liệu*.
> 🔑 Tin tốt sơ bộ, **chưa chốt**: kênh *"mã đã chết bị loại khỏi rổ"* có **0 mã** giữa `T1` và
> `T2` ⇒ nếu số đó đứng sau lượt chạy lại thì cửa sổ **WFO không bị kênh này chạm**, chỉ CALIB bị.
> **Chờ `TD-0230` đóng mới được dẫn như một dữ kiện.**
>
> ⚠️ **Cửa sổ đo — và ĐÍNH CHÍNH một đoạn tôi tự ghi sai vào đây ngày 13/09.**
> Bản trước của mục này viết: *"phán quyết trên **test-only**; nếu `§5.2b` đo lệnh/năm toàn cửa sổ
> rồi so sàn thì nó so **sai đơn vị cửa sổ**"*. **SAI** — và tôi ghi nó vào đây **từ một lời thuật**
> mà không tự đọc nguồn.
>
> Đọc `DR-D3-01 §2` (`:30-35`) thì cả câu hỏi *test-only hay toàn cửa sổ* đều đặt sai: *"train dùng
> để **XẾP HẠNG các arm ablation**, còn test kiểm **thứ hạng đó có giữ được** sang đoạn sau… **đơn
> vị phân tích của fold là *thứ hạng giữa các arm*, không phải *giá trị tuyệt đối của một arm***"*.
> Mà Nhánh 1 hỏi đúng một **giá trị tuyệt đối** — và dưới `DR-D4-10` chỉ còn **một** ứng viên, nên
> **không có thứ hạng nào để đo**. ⇒ Chủ dự án chốt 13/09: **Nhánh 1 phán quyết trên TOÀN cửa sổ
> WFO**; fold là việc của D9. Rào `mean_R` về **0,368** (không phải 0,436), và **sàn 30 lệnh/fold
> KHÔNG áp** cho Nhánh 1.
>
> ⇒ **`§5.2b` đo trên toàn cửa sổ WFO là ĐÚNG đơn vị.** Không phải quy về đoạn test.
>
> 🔴 **Và phải khai RỔ: rổ chạy backtest hiện KHÔNG CÓ XUẤT XỨ** (phiên `[3f7d14]` phát hiện
> 13/09, tôi tự kiểm). `runs/pool_pairs.json` — rổ mà `download-data` **thật sự** dùng — **không
> được git theo dõi** (`git ls-files runs/` chỉ ra `.gitkeep`) và **không có bộ sinh nào trong
> repo**; `config/freqtrade/config.json` mang `pair_whitelist` **đúng 2 mã placeholder**
> (`BTC`, `ETH` — mà §0.3b còn **không xếp** vào pool giao dịch). ⇒ Mọi phép đo *lệnh/năm*, kể cả
> phép đo `§5.2b` bắt buộc ở trên, **không chứng minh được nó chạy trên rổ nào**. Đây là một khoá
> xuất xứ bị thiếu ở tầng dữ liệu, không phải tiểu tiết vận hành: nó làm câu *"đo trên EXPLORE"*
> thành một **lời khai**, đúng thứ `§5.2b` sinh ra để thay thế.
>
> 🔴 Sàn so sánh lấy **đúng chuẩn `MT-29`** (150 lệnh/năm **mỗi hướng**, chốt 12/09/2026), **không
> dựng một chuẩn song song cho nhánh FreqAI** — hai chuẩn cho cùng một câu hỏi *"đủ mẫu chưa"*
> là đúng hình dạng `MT-03` sinh ra để cấm.
>
> ⚠️ **Ô này CHỈ phủ vế LỆNH.** Nhánh FreqAI có **hai** câu hỏi cỡ mẫu trên **hai đơn vị**: đủ
> **nến/đặc trưng** để *khớp tham số* (vế huấn luyện) và đủ **lệnh** để *phán quyết* (vế cổng).
> Sàn 150 được hiệu chỉnh cho vế thứ hai và **không nói gì** về vế thứ nhất. Gộp hai câu vào một
> ngưỡng là đúng hình dạng `L-Z48c` (phiên `[67bb21]` nêu). Vế huấn luyện, nếu cần ngưỡng, phải
> là một ô **riêng** — DR này **không** mở ô đó vì chưa chốt §6 phạm vi. Điều kiện xét lại của `MT-29` cũng đã viết theo
> **phép đo** chứ không theo lời khai, nên hai chỗ khớp nhau về cơ chế, không chỉ về con số.

**Đối chiếu để thấy vì sao:** thứ thật sự cứu được chín suất trial ở `DR-D4-08 §6` **không phải**
một lời khai lệnh/năm — nó là một **phép ĐẾM trên EXPLORE, 0 trial, chạy TRƯỚC khi đặt chỗ**.
Ràng buộc viết theo lời khai chặn được người **cẩu thả**; viết theo phép đo thì chặn được cả người
**tự tin sai** — và ca `adjust_trade_position` hôm nay cho thấy nhóm thứ hai mới là nhóm đang gây
lỗi ở dự án này.

### 5.2c ⚠️ Hệ quả thật của mỗi đường — khai thẳng, vì người quyết phải thấy trước khi chọn

| Đường | Quý 3/2026 có gì |
|---|---|
| **B qua cửa NỘP** (không đè chốt nào) | 🔴 **KHÔNG có một dòng mã FreqAI nào.** FreqAI được **GHI NHẬN**, không được **DỰNG**. `TD-0217…TD-0225` ở lại 🔓 vô thời hạn, và cửa chọn **không tự mở** ở quý 4 |
| **B + một DR đè `DR-Q3-2026`** | Dựng được ngay. Giá: đè lên một cơ chế điều kiện-mở-lại viết ra **đúng để chặn việc quyết vội** |
| **A** (trong Tool D) | Dựng được ngay, không đụng Idea Queue. Giá: §7.3.5 — hoặc đè `DR-D0PRE-02`, hoặc khai DSR không áp dụng |

🔴 **Không có đường thứ tư kiểu *"vừa dựng ngay vừa không đè chốt nào"*.** Quyết định ngày 12/09
của chủ dự án, về bản chất, **chính là một lần CHỌN** theo nghĩa §9c.7.4 — mà `DR-Q3-2026:108` ghi:
*"quý khai `HAN_NGACH_CHON: 0` mà có dòng `SELECTED` → **sổ bẩn**"*. Nên DR đè lên `DR-Q3-2026`
không phải thủ tục thừa: nó **chính là thứ giữ sổ sạch** nếu muốn dựng trong quý này.

### 5.3 Vì sao tôi không tự chọn

Quy tắc 2: đây là quyết định ảnh hưởng ngân sách nghiên cứu và chuẩn phán quyết của cả dự án.
Đường A rẻ và sai chữ spec; đường B đúng chữ spec và bị một chốt khác chặn. **Cả hai đều là đánh
đổi thật, không có đáp án hiển nhiên.**

### 5.4 🔴 Kế toán trial *(ô trống — chủ dự án điền)*

```
MOT_LAN_BACKTEST_FREQAI_TIEU:  __CHUA_DIEN__  trial
KE_TOAN_KHI_RETRAIN:           __CHUA_DIEN__
```

`DR-014 §2`: *mọi lần **đánh giá cấu hình** trên CALIB/WFO/LOCKBOX = **1 trial***. Một lượt
backtest FreqAI retrain hàng chục lần trên cùng cửa sổ. Ba cách đọc đều đọc xuôi — **1 trial cho
cả lượt** · **1 trial mỗi lần retrain** · **đứng ngoài sổ** — và ba cách cho ba con số N lệch
nhau hàng chục lần.

Chốt xong phải có **máy thi hành** ở `src/tool_d/ledger/registry.py` (`TD-0221`). Tiền lệ **MT-08**:
chính sách chốt 07/09 mà `registry.py` 0 dòng thi hành, phải mở `TD-0130` để vá sau.

🔴 **Một khoản chi THỨ HAI, dễ bị bỏ sót vì nó không trông giống một phép đo** (phiên `[3f7d14]` nêu
qua `MT-42`, tôi tự kiểm): **thêm bất kỳ chỉ số FreqAI nào vào báo cáo định kỳ E5 là TIÊU MỘT
TRIAL.** Không phải một lần gõ thêm nhãn. Cơ chế: `content_fingerprint()` băm `code` **cộng**
`label` của từng chỉ số, và vân tay đó bị ghim cứng ở `tests/unit/test_report_content_frozen.py:21`
(`FROZEN_CONTENT_HASH`, TD-0062 niêm phong); spec dòng 4808 khai thẳng *"đổi nội dung báo cáo =
tiêu 1 trial"*.

⇒ Nếu `§6` chốt một phạm vi cần theo dõi *chất lượng mô hình*, *tần suất huấn luyện lại*, hay bất
cứ chỉ số nào của FreqAI **hiện lên báo cáo**, thì khoản đó phải nằm trong `§5.4` **trước khi chủ
dự án quyết** — cùng hạng với câu `N`/rào DSR của `TD-0222`, không phải chi tiết triển khai.

⚠️ Và một hệ quả ngược, đáng biết: `report_model.py` hiện để cả **22 chỉ số ở `pending` bằng một
hằng số chuỗi**, **không có bộ tính** (`MT-42`). Nên kể cả khi FreqAI sinh ra chỉ số, **không có
đường nào để nó hiện ra trong E5** — tức khoản chi trên chỉ phát sinh khi có người dựng bộ tính,
và lúc đó nó phát sinh **cho cả 22 chỉ số cũ lẫn chỉ số mới**, không tách riêng được.

🔴 **⇒ Khoản chi này PHỤ THUỘC THỨ TỰ, không phải một con số cố định** (phiên `[3f7d14]` phát
triển, nhận):

| Thứ tự | Tốn |
|---|---|
| `TD-0240` (dựng bộ tính 22 chỉ số) chạy **trước**, FreqAI thêm nhãn **sau** | **2 suất** — hàm băm đổi hai lần |
| FreqAI vào **cùng lượt** với bộ tính | **1 suất** — một lần đổi mua cả hai |

🔴 Ghi điều này **không phải để chọn cái rẻ** — chọn thứ tự vì giá là đúng cách một quyết định kỹ
thuật bị tiền uốn. Ghi để `§5.4` khai rằng **khoản chi là hàm của thứ tự thi hành**, nên nếu chủ
dự án muốn giữ hai việc tách nhau vì lý do khác (ví dụ không trộn một việc D11 với một việc
FreqAI), thì **cái giá của việc tách phải nằm trên bàn lúc quyết**, không phát hiện sau.

📌 **Một chi tiết MAY, đã kiểm chứ không nhận suông:** hàm băm cố ý **KHÔNG** băm câu lý do
`pending` — `payload = f"{m.code}|{m.label}"`, và docstring `reporting/report_model.py:95-98`
khai chủ đích: *"lý do là văn bản vận hành nội bộ… đổi câu chữ giải thích không phải hành vi spec
muốn chặn"*. ⇒ Sửa một câu `pending` lỗi thời là **0 trial**. Ranh giới đúng là: đổi **bộ TÍNH**
hay đổi **câu lý do** thì rẻ; đổi `code`/`label` thì tốn.

---

## §6 — 🔴 PHẠM VI: FreqAI đứng ở đâu *(ô trống — chủ dự án điền)*

```
PHAM_VI: __CHUA_DIEN__
```

Bốn vị trí khả dĩ, hậu quả khác hẳn nhau:

| Vị trí | Hệ quả |
|---|---|
| **Lọc tín hiệu vào lệnh** (mô hình nói có/không sau khi luật đã sinh tín hiệu) | Nhẹ nhất. Zone/DG/TP giữ nguyên, tầng đo giữ nguyên. `n = 28` **giảm tiếp**, vì lọc chỉ bớt lệnh |
| **Định cỡ** (mô hình điều chỉnh `stake`) | 🔴 Va `D0.1`: cỡ lệnh suy ngược từ ngân sách rủi ro cố định. Đây đúng lý do **Edge Positioning bị cấm** (`§0c.2`) — hai cơ chế định cỡ chạy song song |
| **Chốt lời / thoát lệnh** | Va `§5.1` và `DR-D4-06`; `custom_exit`/`adjust_trade_position` đang mang TP1/TP2 |
| **Thay hẳn zone absorption** | Không còn là Tool D. Đây là đường B của §5.2 — và nếu chọn, `TAN_SUAT_LENH_MUC_TIEU` ở §5.2b là **ô bắt buộc**, không phải tuỳ chọn |

🔴 **Một ràng buộc có sẵn, dù phạm vi chọn thế nào:** nếu FreqAI điều khiển việc **bơm tranche
2/3**, nó đang chạm một câu hỏi **ĐANG ĐÓNG** — `DR-D4-10 §2.4` chốt mặc định `Z0` single-entry,
điều kiện mở lại `n ≥ 319` đã viết trước. Mở lại phải qua DR, **không ngầm hiểu**.

⚠️ Và một dữ kiện về mã, đã đọc file chứ không suy: `adjust_trade_position` **vẫn trên đường chạy
sản xuất** ngay cả với `arm = Z0` — `ZoneAbsorption.py:886-887` xét TP1 **trước** chốt arm ở `:891`.
Ai bọc/bỏ/thay callback đó vì tưởng nó đã chết thì **TP1 chết theo, và chết im lặng** (`MT-16 (vii)`).

---

## §7 — 🔴 ĐIỀU DR NÀY KHÔNG CHO PHÉP

Mục này tồn tại vì Khối 17 **buộc** phải sửa một test khoá (`L-Z24` đang ghim `freqai.enabled =
false`) — chỗ **duy nhất** trong dự án mà việc đó hợp lệ. Một tiền lệ như thế, nếu không đóng khung,
sẽ được dẫn lại **mà không mang theo lý do**.

### 7.1 Ba điều kiện tiên quyết để chạm `L-Z24` — thiếu một là không hợp lệ

| # | Điều kiện | Kiểm bằng |
|---|---|---|
| 1 | Tồn tại một DR đã commit đổi **chính điều khoản spec** mà test thi hành, và commit đó đứng **TRƯỚC** commit sửa test | `git merge-base --is-ancestor <commit DR> <commit sửa test>` → **exit 0** mới hợp lệ. Phép kiểm **nhị phân**, không phải `git log` liệt kê rồi người đọc tự suy thứ tự — *đọc tóm tắt không phải đọc* |
| 2 | **Đổi nhãn, không gỡ răng** — sau khi sửa, test vẫn thi hành *một* điều khoản, chỉ là điều khoản mới | Phá thật: làm sai hành vi mới ⇒ **phải đỏ** |
| 3 | Phạm vi ghi theo **MÃ TEST**, không theo phạm trù | Ghi đích danh *"`L-Z24`, và chỉ khoá `freqai.enabled`"* |

**Vì sao điều 1 là điều mạnh nhất:** chỗ khác nhau giữa *"lần này hợp lệ"* và *"sửa test khi nó
cản"* **không nằm ở mức độ chính đáng** — nằm ở một dữ kiện đọc được trên đĩa: điều khoản spec bên
dưới **đã bị đổi trước đó**. Test không sai; thứ nó canh đã đổi.

**Vì sao điều 3 dùng danh sách CHO PHÉP:** *"các test khoá liên quan FreqAI"* là một **phạm trù**,
mà phạm trù thì tự nở ra. Bài học `TD-0130`: danh sách cho phép chặn được cả tên chưa ai nghĩ tới;
blocklist chỉ chặn được tên đã nghĩ ra trước.

### 7.2 Căn cứ **KHÔNG** hợp lệ — viết ra vì im lặng ở đây là nơi tiền lệ sinh ra

> ❌ *"Test khoá đang cản tiến độ."*
> ❌ *"Chủ dự án đã đồng ý"* nói chung.
>
> Chủ dự án đồng ý **đổi spec** là hợp lệ. Chủ dự án đồng ý **sửa test** mà spec không đổi thì
> **không** — vì khi đó test và spec lệch nhau, và **spec thắng** (N1).

### 7.3 DR này KHÔNG chốt, và ai đọc thành đã chốt là đọc sai

1. ❌ **Không** gỡ lệnh cấm `hyperopt` (`L-Z25`). Spec `:448-460` gọi hyperopt là *"mối nguy lớn
   nhất, **lớn hơn FreqAI nhiều**"* — hai lệnh cấm khác lý do, mở cái này không kéo theo cái kia.
2. ❌ **Không** gỡ `L-Z37` (`IntParameter`/`DecimalParameter`/…).
3. ❌ **Không** gỡ lệnh cấm **Edge Positioning** — nó xung đột `D0.1`, lý do không liên quan gì FreqAI.
4. ❌ **Không** mở entrypoint thứ chín (`L-Z36`, `§0d.2:664`).
5. ❌ **Không** đổi bất kỳ ngưỡng nào đang có: `0,10 R` · `≥ 20%` · `150 lệnh/năm` · `N = 114` ·
   rào `3,0777`. 🔴 **Đổi `N` đòi một DR ĐÈ LÊN `DR-D0PRE-02` — file riêng, commit riêng**, không
   phải một đoạn trong DR này. Cùng logic §7.1 điều 1: *điều khoản bên dưới phải bị đổi bằng DR của
   chính nó, trước đã*. Viết thế để điều kiện **không thể thoả được từ bên trong `DR-FAI-01`** —
   bản nháp đầu ghi *"quyết định riêng phải ghi rõ ở §5.4"*, mà §5.4 nằm trong chính DR này, nên
   câu đó **vừa cấm vừa chỉ đường** (phiên `[3f7d14]` bắt).

   🔴 **Và phải khai CHIỀU, vì im lặng ở đây mặc định chọn phương án dễ.** Giữ `N = 114` trong khi
   §4(a) tự thừa nhận DOF của mô hình **không được đếm** thì không bảo toàn *ý nghĩa* của cổng —
   nó bảo toàn **con số** trong khi con số thôi có nghĩa. Cơ chế, một dòng: `h = √(2·ln N)`; số phép
   thử hữu hiệu **tăng** (retrain hàng chục lần mỗi lượt) mà `N` giữ **114** ⇒ `h` giữ **3,0777**
   trong khi nó **phải cao hơn** ⇒ **rào thấp hơn mức đáng phải có** ⇒ **cổng DỄ QUA HƠN**. Tức
   điều khoản này, viết như bản nháp đầu, **chốt vào chiều fail-open** và **đối đầu trực tiếp với
   chính §4(a)**, nơi dẫn N6 (*"ngưỡng chưa điền = `+inf`, để cổng không thể vô tình PASS"*).

   > ⚠️ **Hai đường hợp lệ, không có đường thứ ba:** **(i)** khai cổng DSR **KHÔNG áp dụng** cho
   > đường FreqAI **và nêu thước thay thế**; hoặc **(ii)** nâng `N` bằng một DR đè `DR-D0PRE-02`.
   > **Im lặng không phải đường thứ ba — im lặng là chọn (i) mà không khai.**
6. ❌ **Không** mở lại câu hỏi DCA (`DR-D4-10 §2.4`, điều kiện `n ≥ 319`).

---

## §8 — 🔴 ĐIỀU KIỆN ĐÓNG LẠI — viết TRƯỚC *(ô trống — chủ dự án điền)*

```
TAT_FREQAI_KHI:  (a) __CHUA_DIEN__ hoặc (b) __CHUA_DIEN__ hoặc (c) __CHUA_DIEN__
```

Khuôn `OQ-07` / `DR-D4-01 §7` / `DR-Q3-2026 §2`: điều kiện phải là **sự kiện đọc được từ số**,
không phải cảm giác, và phải viết **trước khi có con số nào** — vì lúc đang thua là lúc người ta
**muốn** giữ nhất và **tệ nhất** trong việc quyết định.

🔴 **Ràng buộc riêng của ca này, sinh từ §4(c):** ít nhất một điều kiện phải **không dựa vào việc
mô hình tự khai** (không dùng loss/score/confidence của chính mô hình). Một mô hình tự thích ứng
sẽ luôn báo cáo rằng nó đang thích ứng tốt.

Gợi ý ba khuôn có sẵn trong dự án, chủ dự án sửa hoặc bỏ: thang drawdown `5/8/20%`
(`DR-D0PRE-04`) · phán quyết **L2/L3** (`§11b.1`) · sai lệch giữa lệnh THẬT và Decision Log (`N10`).

---

## §9 — Giới hạn TỰ KHAI

1. **Tôi chưa từng chạy FreqAI trong repo này.** Mọi phát biểu về hành vi của nó ở trên là đọc
   spec + đọc cấu hình, **không phải đo**.
   ✅ **`TD-0219` nay ĐÃ ĐO** (12/09/2026, `docs/du-lieu-do/td0219-anh-docker-thu-vien-ml.json`,
   **0 trial**): `sklearn 1.9.0` ✅ · `joblib 1.5.3` ✅ · **`datasieve`/`lightgbm`/`catboost`/
   `torch`/`xgboost` THIẾU** ⇒ **`import freqtrade.freqai.freqai_interface` → `ModuleNotFoundError:
   datasieve`**. 🔑 Thư mục `freqtrade/freqai/` **CÓ tồn tại** — dừng ở dấu hiệu đó thì kết luận
   **ngược hẳn**; thư mục là **hình dạng**, import được mới là **cơ chế**.
   ⇒ **Điều kiện dừng §4(b) — viết TRƯỚC khi chạy — đã NỔ.** Không tự đổi digest, không tự đổi
   phạm vi: trình chủ dự án.
2. **`§4(b)` chưa có số, và KHÔNG đo được ở trạng thái hiện tại** — hai lý do **độc lập**, gỡ một
   cái vẫn còn cái kia: **(i)** ảnh Docker không import nổi FreqAI (mục 1); **(ii)** repo có **0
   dòng** chiến lược FreqAI — `grep` cho `feature_engineering_expand_all` / `set_freqai_targets` /
   `freqaimodel` trả **0 kết quả**, mà một phép đo thời gian tường **cần** một chiến lược để chạy.
   🔴 Và viết chiến lược đó **chính là chạm mã Khối 17**, thứ `§0` của DR này cấm khi còn ô trống.
   ⇒ Vì thế thứ tự *"đo `§4(b)` trước, điền ô sau"* **không khả thi**: `§4(b)` **phụ thuộc** vào
   `§6` phạm vi, không độc lập với nó. `TD-0219` thì ngược lại — độc lập thật, và đã đo xong.
3. **Con số `n = 28` là của arm rule-based hiện tại**, đo trên **EXPLORE** (`TD-0205`). Không ai
   biết `n` của một hệ thống có FreqAI là bao nhiêu — nhưng mọi cơ chế đã biết đều làm nó **giảm**,
   không tăng.
4. Tài liệu này **không** khảo sát mô hình nào (LightGBM/XGBoost/torch) — chọn mô hình là chi tiết
   triển khai, chỉ có nghĩa **sau khi** §6 chốt phạm vi.

---

## §10 — Việc thi hành

Sau khi **mọi** ô lính canh `__CHUA_DIEN__` được điền (kiểm bằng lệnh ở đầu tài liệu — **không** đếm bằng số viết tay): `TD-0217` (giấy tờ) → `TD-0219` (ảnh Docker) → `TD-0222` (N/DSR) →
`TD-0220` (config) → `TD-0218` (`L-Z24`) → `TD-0221` (kế toán) → `TD-0223` (rò rỉ) → `TD-0224`
(quan hệ D4) → `TD-0225` (bộ chạy + xuất xứ).

🔴 Thứ tự **TD-0222 trước TD-0220** là cố ý: khoá config là bậc tự do, mà đếm bậc tự do thế nào thì
phải chốt trước khi thêm bậc tự do.

---

## §11 — Lịch sử

| Ngày | Việc |
|---|---|
| 12/09/2026 | Lập bản nháp (`TD-0216`). **Năm** ô chờ chủ dự án: `§2` lý do mở · `§5.2b` tần suất lệnh mục tiêu · `§5.4` kế toán trial ·
`§6` phạm vi · `§8` điều kiện đóng lại. Ba điều kiện tiên quyết `§7.1` do phiên `[3f7d14]` đề nghị, nhận nguyên. **Đọc chéo cùng ngày** bắt hai
chỗ, đã vá trước khi commit: `§7.3.5` hở theo chiều **fail-open** (giữ `N` mà không đếm DOF ⇒ rào DSR
thấp hơn mức đáng phải có ⇒ cổng dễ qua hơn) và tự quy chiếu vào `§5.4`; `§7.1` điều 1 đổi từ `git log`
liệt kê sang phép kiểm nhị phân `git merge-base --is-ancestor`. Và một sai của bản nháp đầu do chính
tôi đóng khung hỏng: *"hoãn sang quý 4"* **không phải một đường đi** — `DR-Q3-2026 §2` ghi quý sau
**mặc định lại là 0**. Phát hiện khi soạn: **cửa chọn Idea Queue quý 3/2026 = 0** (`DR-Q3-2026:17`), không điều kiện mở lại nào đã xảy ra ⇒ đường B của `§5.2` bị chặn trong quý này. |
