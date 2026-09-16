# DR-D4-13 — Ranh giới EXPLORE theo đúng chữ spec, và đơn vị của `DR-D4-09` §7 điều 1

> **Ngày chốt:** 16/09/2026 · **Người quyết:** chủ dự án (hai câu, trả lời trực tiếp)
> **Giải:** `MT-24` (trích dẫn bịa về ranh giới EXPLORE) · `MT-25` (phần còn lại — cách đọc
> `DR-D4-09` §7 điều 1; phần đơn vị đã giải ở `DR-D4-12` §1) · **0 trial**
> **KHÔNG giải, và không gỡ chặn:** `TD-0184` vẫn bị chặn bởi `TD-0247` (rổ pool point-in-time,
> `MT-34`/`MT-45`). Đọc DR này thành *"TD-0184 hết bị chặn"* là đọc sai.
> Đã nhắn ba phiên song song trước khi mở file (N12 mục 6). `-ea`, `-30`: không giữ `MT-24`/`MT-25`.
> `-df` đang gom quyết định cho DR của `TD-0247` và **nhường số `D4-13`**, sẽ lấy số kế tiếp.

---

## 0. Vì sao phải có DR, thay vì sửa một câu chú thích

`MT-24` không phải lỗi chính tả. Một câu **paraphrase không đánh dấu** đã đi qua bốn chỗ, và ở chỗ
thứ ba bị **đóng khung thành trích dẫn nguyên văn**:

| # | Chỗ | Chữ |
|---|---|---|
| 1 | `DR-D4-08:87` | *"chỉ đếm, không PnL, đúng ranh giới `DR-D0PRE-05` §4"* — paraphrase, không ngoặc kép |
| 2 | `DR-D4-09:158` | *"trên EXPLORE thì vướng `DR-D0PRE-05` §4"* — dựa vào (1) |
| 3 | `docs/du-lieu-do/td0184-do-nhay-rao-dsr.py:12-13` | *"`DR-D0PRE-05` §4 cấm THẲNG — "KHÔNG expectancy, KHÔNG PnL theo arm""* — **có ngoặc kép** |
| 4 | khoá `ranh_gioi` trong `docs/du-lieu-do/td0193-lenh-nam-explore.json` | artifact — **KHÔNG sửa**, sửa là hỏng xuất xứ |

Đọc lại nguồn gốc (16/09/2026, mở file chứ không tin trích dẫn):

- **`DR-D0PRE-05` §4** chỉ ghi: *"Tập EXPLORE (§9c.4b) = BTC + ETH + mọi mã KHÔNG thoả tiêu chí
  (i)/(ii). Dùng để SINH giả thuyết, 0 trial. 🔴 Ràng buộc cứng: một mã đã vào EXPLORE **không bao
  giờ** được chuyển sang pool giao dịch…"*. **Không có chữ nào về PnL hay expectancy.**
- **Spec §9c.4b** (bảng phân vùng, cột *"Dùng cho"* của EXPLORE): *"SINH giả thuyết · **Phân tích
  KHÔNG giới hạn, 0 trial**"*. Hai ràng buộc cứng: *"(a) EXPLORE KHÔNG BAO GIỜ dùng để validate bất
  cứ thứ gì"* · *"(b) Coin nào đã ở EXPLORE thì KHÔNG BAO GIỜ được đưa vào pool giao dịch"*. Và:
  *"EXPLORE miễn phí ở bước SINH, không miễn phí ở bước KIỂM CHỨNG"*.
- **`DR-014` §2** (spec, khối kế toán): *"mọi lần chạy trên EXPLORE: ngoài sổ này"* — luật **KẾ
  TOÁN** (0 trial bất kể đo gì), **không phải** luật **NỘI DUNG**.

⇒ Cách đọc *"EXPLORE chỉ được ĐẾM"* **chặt hơn spec**, và chưa từng được ai quyết — nó được **thừa
kế bằng trích dẫn**.

🔑 **Ghi lại một lần trượt trong chính quá trình ra DR này**, cùng họ với lỗi nó sửa: lượt hỏi đầu,
phiên soạn DR khuyến nghị *"giữ chỉ đếm"* với lập luận *"đo `std_R` chạm ràng buộc (a)"*, **không nêu**
câu *"Phân tích KHÔNG giới hạn"* — vì chưa mở §9c.4b ra đọc. Chủ dự án đã chọn theo khuyến nghị đó.
Mở nguồn lúc chuẩn bị viết thì thấy; đã hỏi lại kèm dữ kiện, chủ dự án chọn **theo đúng spec**.
Một lời khuyên nói về nguồn mà chưa đọc nguồn là **lời khai**, không phải bằng chứng — kể cả khi nó
tới từ chính phiên đang sửa lỗi lời khai.

---

## 1. QUYẾT ĐỊNH 1 (`MT-24`) — EXPLORE theo đúng spec §9c.4b

### 1.1 Được phép, 0 trial

Mọi phân tích trên EXPLORE, **kể cả** đại lượng cần `pnl_abs`: `mean_R`, `std_R`, expectancy,
win-rate, PnL theo arm, phân bố `R`. Không cần đặt chỗ trial, không cần DR riêng cho từng lần đo.

### 1.2 Cấm cứng — ràng buộc (a) của spec, viết thành hành vi kiểm được

Một con số đo trên EXPLORE **không được** xuất hiện làm căn cứ ở:

1. **Bất kỳ phán quyết cổng nào** (PASS / FAIL / INCONCLUSIVE của D4 hay cổng sau) — kể cả dạng
   *"EXPLORE cũng cho thấy…"* đặt cạnh số đo trên pool. Đây là chữ tường minh của (a).
2. **Lý do đổi bộ arm, ngưỡng, hay cách đọc đã viết TRƯỚC** của D4 (`DR-D4-09`, `DR-D4-10`,
   `DR-D4-12` §4 — 4 arm chọn theo ma trận thiết kế). Spec dòng 3956-3957 đòi DR chốt **ngưỡng** viết
   TRƯỚC khi biết kết quả; `DR-D4-12` §0 mở rộng cùng lý lẽ sang **cách đọc/phạm vi**. Và EXPLORE
   **không độc lập** với pool — BTC/ETH, xương sống của nó, tương quan 0,7–0,85 với altcoin
   (§9c.4b tự khai).
3. **Lý do chứng minh một cấu hình "đáng tiêu suất"** trong một DR hay một bản đặt chỗ `B1`/`B2`.
   Giả thuyết sinh từ EXPLORE đi qua **Idea Queue** với `data_source = EXPLORE` + `explore_evidence`
   (`TD-0126`) và **trả trial đầy đủ** khi kiểm chứng trên pool — đúng câu *"không miễn phí ở bước
   KIỂM CHỨNG"*.

🔴 Mục 2 và 3 là **DIỄN GIẢI** của (a) sang hành vi cụ thể, không phải chữ tường minh — ghi ra để
cãi lại được.

### 1.3 Mọi đầu ra EXPLORE có PnL phải tự khai nhãn

Tệp kết quả mang `nguon`/`data_source` = EXPLORE và một dòng giới hạn: *"EXPLORE ≠ pool (rổ khác —
`MT-34`; không độc lập — BTC/ETH tương quan 0,7–0,85 với altcoin, §9c.4b); không dùng làm căn cứ
phán quyết (`DR-D4-13` §1.2)"*.
Khuôn đã có ở mục *"Giới hạn TỰ KHAI"* của các báo cáo `td02xx`.

### 1.4 KHÔNG có máy chặn — khai thẳng

DR này **không** thêm code. Cấm ở §1.2 hôm nay là **kỷ luật con người**, không có test khoá.
Điều kiện dựng máy (viết TRƯỚC): **khi có bộ chạy đầu tiên ghi một bản ghi arm/cổng** (`arm_record.py`)
mà có thể nhận đầu vào từ dữ liệu EXPLORE ⇒ bản ghi đó phải từ chối (fail-closed) mọi `data_source`
khác CALIB/WFO/LOCKBOX. Chưa có đường chạy nào như vậy, nên viết chốt bây giờ là chốt cho thứ chưa
tồn tại (đúng lý lẽ `L-Z51`).

### 1.5 Phương án đã LOẠI

| Loại | Vì sao |
|---|---|
| **(1a)** Giữ *"EXPLORE chỉ ĐẾM"* như kỷ luật tự đặt, chặt hơn spec | Chủ dự án chọn lúc đầu dựa trên khuyến nghị thiếu dữ kiện (§0), đổi sau khi thấy chữ spec. Giữ nó sẽ sinh **một mâu thuẫn MỚI** DR-vs-spec phải theo dõi (N1: spec thắng), và tự bỏ công cụ 0 trial duy nhất để ước lượng `std_R` (`MT-27`) |
| **(1b)** Mở có rào: danh sách CHO PHÉP chỉ xuất `std_R` + `ty_le_rui_ro_da_trien_khai` | Giải một vấn đề spec không đặt ra. Và rào đó **không chặn được thứ nó định chặn**: tính `std` bắt buộc tính `mean` trước, chỉ là không in ra |

### 1.6 Hệ quả cho các tài liệu đã viết

- `DR-D4-09` §5 (*"Đo `std_R` thật cần chạm PnL; trên EXPLORE thì vướng `DR-D0PRE-05` §4"*) — vế
  EXPLORE **hết đúng**. `std_R` đo được trên EXPLORE, 0 trial. ⚠️ Con số đó **chỉ** dùng cho việc
  *lên kế hoạch cỡ mẫu*, **không** thay được `std_R` đo trên WFO ở `TD-0184` cho mọi phép tính
  trong phán quyết (§1.2 mục 1).
- DR này **không** mở mã việc đo `std_R` trên EXPLORE — `DR-D4-12` §2.1 đã chọn đường không cần con
  số đó trước `TD-0184`. Ai muốn đo thì mở việc riêng.
- Đính chính **tại chỗ, giữ chữ cũ** ở ba chỗ (1)(2)(3) của §0. Chỗ (4) là artifact — không sửa;
  giá trị mặc định `ranh_gioi` trong script `td0193` **giữ nguyên** để artifact còn tái lập được
  (research-log 10/09/2026).

---

## 2. QUYẾT ĐỊNH 2 (`MT-25` phần còn lại) — `DR-D4-09` §7 điều 1 đọc trên `R_trien_khai`

### 2.1 Chữ đang có

`DR-D4-09` §7 điều 1: *"`std_R` đo được … và lệch > 30% so với 1,25 ⇒ tính lại toàn bộ bảng
§1.2/§1.3/§4; kết luận định tính (…) chỉ đổi nếu `std_R < 0,5`."*

`MT-25` chỉ ra: điều này giữ `mean_R` cố định khi cho `std_R` chạy — **sai** nếu `std_R` nhỏ đi vì
đơn vị `R` bị co (mẫu số là ngân sách rủi ro đủ ba tranche trong khi chỉ tranche 1 khớp), vì khi đó
`mean_R` co theo; **đúng** nếu `std_R` nhỏ vì phân tán thật sự chặt.

### 2.2 Quyết định

**Mọi `std_R` và `mean_R` trong `DR-D4-09` §7 điều 1 là của `R_trien_khai`** — đúng đại lượng
`DR-D4-12` §1.4 định nghĩa và Nhánh 1 phán quyết trên đó. Cả hai hằng số `1,25` và `0,5` **giữ
nguyên**, áp **trực tiếp** lên `std(R_trien_khai)`.

Căn cứ: trên `R_trien_khai` mẫu số là rủi ro **thật đã bỏ ra** của từng lệnh, nên cơ chế *"R co vì
mẫu số lớn hơn rủi ro thật"* của `MT-25` (i) **không còn nằm trên con số được đọc**. Một `std_R` nhỏ
trên thang đó là phân tán chặt thật ⇒ đúng trường hợp mà `MT-25` tự khai là §7 điều 1 **đúng**.
🔴 Đây là **DIỄN GIẢI** dựa trên định nghĩa của `DR-D4-12` §1.4, chưa có phép đo xác nhận.

### 2.3 🔴 CẤM quy đổi ngưỡng bằng một `λ`

Nếu ai đó có trong tay `std(R_ngan_sach)` thay vì `std(R_trien_khai)`: **không** được đổi ngưỡng
kiểu `0,5 × λ` hay `0,5 / λ` với bất kỳ `λ` nào (`0,53` hay số khác). `DR-D4-12` §1.3 đã chỉ ra `λ`
**đổi theo từng lệnh** (phụ thuộc hình học zone), nên `std` không co đúng `1/λ`, và `DR-D4-12` cố ý
**không ghim con số `λ` nào**. Cách đúng duy nhất: **tính lại `std` trên `R_trien_khai`** từ bản ghi
arm — bản ghi mang **cả hai** vế (`DR-D4-12` §1.4, `arm_record.py` `CHI_SO_BAT_BUOC`).

### 2.4 Hai tài liệu phải đọc KÈM, không chép lại

- `DR-D4-12` §1.7 — bất biến *"ở lệnh đủ ba tranche, `Σ rui_ro_da_trien_khai` = `planned_risk_usdt`"*
  phải được **ĐO** ở `TD-0184`; lệch ⇒ **DỪNG**. Nếu bất biến đó gãy thì `R_trien_khai` không đọc
  được, và §2.2 của DR này **mất căn cứ** cùng lúc.
- `DR-D4-12` §9 điều 3 (*"`std_R` đo được ≤ 0,4664 ⇒ §2.1 sai"*) — cùng đơn vị `R_trien_khai`,
  hai điều kiện mở lại nhất quán với nhau.

### 2.5 Phương án đã LOẠI

| Loại | Vì sao |
|---|---|
| **(2a)** Viết lại §7 điều 1 thành ngưỡng trên Sharpe mỗi lệnh `mean_R/std_R` | Bền hơn nếu sau này có người đọc nhầm đơn vị, nhưng là **đổi một điều kiện mở lại đã viết TRƯỚC** — phải tính lại bảng ngưỡng, thêm một con số mới để cãi. Khi đơn vị đã chốt ở `DR-D4-12` thì không mua thêm gì |
| **(2b)** Giữ `R_ngan_sach` cho §7 điều 1, quy đổi bằng `λ ≈ 0,53` | Cấm ở §2.3 |

---

## 3. Điều DR này KHÔNG chốt

- **Không** gỡ chặn `TD-0184` — chặn bởi `TD-0247`.
- **Không** đổi ngưỡng nào: `0,10 R`, `150 lệnh/năm`, `1,25`, `0,5`, `N = 114` giữ nguyên.
- **Không** mở việc đo `std_R` trên EXPLORE (§1.6).
- **Không** trả lời câu hỏi mở số 14 của spec (dòng 5054: *"có nên coi giả thuyết sinh từ EXPLORE là
  tốn nửa trial thay vì 0 trial?"*). DR này áp **chữ hiện hành** của §9c.4b (0 trial ở bước SINH);
  nếu câu 14 được chốt theo hướng tính phí thì đó là điều kiện mở lại §5 mục 3.
- **Không** đụng `MT-38` — đã giải ở `DR-D4-11` + `TD-0236`; phần còn lại là mã `close_d4_gate()`
  (`TD-0186`), không phải quyết định.
- **Không** thêm code, không sửa artifact.

## 4. Kế toán DOF

`dof_goc` 28 · `|tier_b|` 12 · **N = 114** · rào DSR **3,0777** — không đổi. **0 trial**: DR này không
đánh giá cấu hình nào.

## 5. Điều kiện mở lại — viết TRƯỚC, khuôn OQ-07

1. **Bất biến `DR-D4-12` §1.7 lệch** ⇒ §2 mất căn cứ, mở lại cùng `DR-D4-12` §1.
2. **Phát hiện một con số EXPLORE đã được dùng làm căn cứ** ở một trong ba chỗ của §1.2 ⇒ dựng máy
   chặn ngay (§1.4), không đợi điều kiện ở đó, và ghi `MT` mới.
3. **Spec §9c.4b được sửa** (ví dụ thu hẹp *"Phân tích KHÔNG giới hạn"*) ⇒ §1 phải viết lại theo spec.

❌ **KHÔNG** phải điều kiện mở lại: một phép đo trên EXPLORE cho kết quả xấu/đẹp, hoặc `TD-0184` ra
INCONCLUSIVE.

## 6. Việc thi hành

| # | Việc | Ai / khi nào |
|---|---|---|
| a | Đính chính tại chỗ `DR-D4-08:87`, `DR-D4-09:158` (§5), `DR-D4-09` §7 điều 1 — giữ chữ cũ | Cùng đợt, commit riêng sau DR này |
| b | Đính chính docstring `td0184-do-nhay-rao-dsr.py:12-13` — chỉ chú thích, không đổi logic | Chờ lệnh *"bắt đầu code"* (quy tắc gốc 1) |
| c | `back-end-note.md` mục 7 (`MT-24` ✅, `MT-25` phần còn lại ✅) + mục 8 | Chờ lệnh *"chuẩn hóa và lưu"* (N9) |
