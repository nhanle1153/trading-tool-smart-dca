# DR-D4-10 — Tái định phạm vi D4 theo CỠ MẪU: D4 được hỏi HAI câu, không phải chín

> Quyết định của chủ dự án, 10/09/2026 (phương án **A** trong ba phương án trình ở TD-0208).
> Commit **RIÊNG và TRƯỚC** mọi dòng mã thi hành. Đã báo phiên `c3` trước khi mở file (N12 mục 6);
> `c3` xác nhận không mở DR nào, không va.
> Bằng chứng: `docs/du-lieu-do/td0205-lenh-nam-wfo-explore.json` (88 mã EXPLORE, đo RIÊNG trên
> cửa sổ WFO, 0 trial) và `docs/doi-chieu-checklist-antioverfitting.md` (TD-0208).
> 🔴 **Viết TRƯỚC khi tồn tại một con số expectancy nào của Tool D** (`runs/` không có thư mục trial,
> 0 file `.seal`, 4/114 trial đã tiêu đều `outcome.expectancy: null`) — spec dòng 3956-3958 đòi
> đúng thế, và đây là lúc **DUY NHẤT** sửa phạm vi gate mà không ai nghi *"sửa cho dễ qua"*.

---

## 1. Vấn đề — số học, không phải ý kiến

### 1.1 `n` đo thật thấp hơn thứ `DR-D4-09` giả định

`DR-D4-09 §1.1` lập bảng `n` bằng **ngoại suy** từ `td0193` (cửa sổ `[T0,T2]`, 63,6 lệnh/năm × 0,63).
TD-0205 sau đó đo **RIÊNG trong cửa sổ WFO** — chính cửa sổ ablation chạy — và ra thấp hơn:

| Nhóm | Arm | `n` DR-D4-09 **ngoại suy** | `n` **ĐO, sau bản vá TD-0207** | Lệch |
|---|---|---|---|---|
| A | `Z0-T0` (tắt hết Phần 2) | ~804 | **883** | +10% |
| B | `Z0-T1` (chỉ 4H, bỏ 1D) | ~210 | **206** | −2% |
| **C** | `Z0` `Z1` `Z2` `Z3` `Z3b` `Z0-V1` `Z0-S1` | ~40 | **28** | **−29%** |

Nguồn: `td0205-lenh-nam-wfo-explore.json` (đo lần đầu) và `td0212-ba-arm-sau-va.json` (**đo lại
sau bản vá TD-0207**, 88 mã, 0 trial). Cả ba cột `n` ở trên là số **sau vá**.

⚠️ **Bản vá đổi số đếm của arm nhiều lệnh, KHÔNG đổi của arm ít lệnh** — và điều đó có cơ chế đọc
được, không phải nhiễu: `Z0-T0` **746 → 686 lệnh** (−8%), trong khi `Z0-T1` **160 → 160** và `Z0`
**22 → 22**. TP1 theo zone đối diện nằm xa hơn nạng `1,5R` (tới `3,2R`), nên lệnh **giữ chỗ lâu
hơn**; ở arm ~700 lệnh thì các lệnh tranh nhau chỗ mở trên cùng một cặp và số đếm tụt, ở arm 22
lệnh thì gần như không có cạnh tranh nên không thấy gì. Dấu vết đi kèm: `TIME_STOP` của `Z0-T0`
tăng **5 → 8**.
🔑 ⇒ Câu *"`Z0` 22 → 22 nên số đếm không phụ thuộc tầng chốt lời"* là một **QUAN SÁT trên một arm ít
cạnh tranh, không phải một nguyên tắc**. Áp nó sang nhóm A thì `n` sai 8%. Ghi ra vì đây đúng lớp
lỗi *"sai ở NHÃN dán lên phép đo"* — và lần này nó bị bắt bởi phép đo, không bởi lý lẽ.

Cơ chế đã đo, không phải nhiễu: `1D = UP` chỉ **15,85%** trong WFO so với **19,02%** trên `[T0,T2]`
(`z = −2,22`) — WFO là cửa sổ **nghịch chiều Long**. Độ phủ mã-năm của WFO còn **cao hơn** (90% vs
63%), nên sụt giảm **không** do thiếu dữ liệu.

⇒ Mọi bảng ở `DR-D4-09` §1.2/§1.3/§4 đang **lạc quan hơn thực tế ~19%** ở nhóm C
(`h/√n`: 0,487 → **0,578**). 🔴 **KHÔNG sửa `DR-D4-09`** (quy tắc 5) — đính chính ghi tại đây.

### 1.2 Nhóm C là INCONCLUSIVE — chứng minh được TRƯỚC khi chạy, 0 trial

`DR-D4-09 §2.2` định nghĩa: **INCONCLUSIVE ⇔ `thuế nhiễu > ngưỡng của chính tiêu chí đó`**.

```
thuế nhiễu(nhóm C) = h/√n · std_R = 3,0777/√28,3 · std_R = 0,5784 · std_R
ngưỡng Nhánh 1     = 0,10 R
⇒ INCONCLUSIVE  ⇔  std_R > 0,1729
```

**Không cần chạy để biết.** Không có hệ thống giao dịch nào — có SL cứng tại `−1R` theo thiết kế và
TP tới `3,2R` — cho `std_R` dưới 0,17. Ngưỡng **hiệu dụng** của nhóm C vì thế là:

| `std_R` | 0,58 | 1,00 | 1,25 | 1,50 |
|---|---|---|---|---|
| `mean_R` cần để PASS | **0,435** | 0,678 | **0,823** | 0,968 |

Cận dưới 0,58 đã rất rộng lượng, mà vẫn đòi lệnh trung bình lãi **0,44 R**. Không đạt được.

🔑 **Ca nghi ngờ mạnh nhất đã bị chặn bằng số** (phiên `c3` nêu, đúng chỗ): `MT-25` ghi thang
`R_realized` của Z0 bị **CO** (mẫu số `planned_risk` tính đủ 3 tranche trong khi Z0 chỉ khớp 1).
Thang co ⇒ `std_R` đo được nhỏ hơn thật ⇒ về lý thuyết thuế nhiễu có thể tụt **xuống dưới** ngưỡng
và lật nhóm C từ INCONCLUSIVE sang **FAIL** — một kết luận mạnh hơn hẳn và **sai**. Điểm lật:
`std_R < 0,1729`, tức hệ số co `λ < 0,138`. Với `λ ≈ 0,53` (tỉ trọng rủi ro tranche 1) thuế nhiễu
vẫn **0,383**. ⇒ **Kết luận đứng trừ khi thang co hơn 7 lần.** `MT-25` không lật được DR này.

### 1.3 Đây là *"ngoài tầm với"*, không phải *"thiếu mẫu"*

`n` cần để ngưỡng hiệu dụng xuống mức một hệ thống thật có thể đạt (`std_R = 1,25`):

| `mean_R` mục tiêu | 0,50 R | 0,40 R | 0,30 R | 0,25 R | 0,20 R |
|---|---|---|---|---|---|
| `n` cần | 93 | 164 | **370** | 658 | 1.480 |

Trần trên của **mọi** đòn bẩy còn lại, cộng dồn hết:

| Bước | `n` |
|---|---|
| hiện tại | 28 |
| × 2 — pool 204 mã (đụng `DR-D0PRE-05`, thanh khoản kém hơn) | 57 |
| × 2,86 — dùng cả CALIB+WFO (**phá phân vùng `DR-011`**) | **162** |

**162 < 370.** Kể cả làm hết mọi thứ và chấp nhận phá hai quyết định đã chốt, nhóm C vẫn hụt hơn
một nửa. ⇒ Nhóm C **không thể** được phán quyết bởi Nhánh 1, bây giờ hay về sau.

🔴 **`×2` cho "bật Short" đã bị LOẠI khỏi bảng trên, có căn cứ văn bản:** spec dòng 4187 đòi
*"chạy **hai lần độc lập** — một cho Long, một cho Short — không giả định kết quả Long tự động áp
dụng cho Short"*, và dòng 4973-4974 lặp lại *"chạy TÁCH RIÊNG… **không dùng chung kết quả**"*;
`DR-D4-01 §4` định nghĩa đơn vị tiêu là **1 trial / 1 cấu hình / 1 hướng**. ⇒ Với một arm Long,
mở Short **không cộng `n` nào cả** — nó tạo một bộ arm THỨ HAI có `n` riêng.
*(Bản nháp đầu của TD-0208 tính `×2` này và ra trần 324; đó là **sai**, đã bỏ. Kết luận **mạnh hơn**
sau khi bỏ, không yếu đi.)*

### 1.4 Giảm DOF không phải một đòn bẩy — chênh khoảng 30 lần

§10.1b bán ý *"`Z0-T1` ≥ `Z0-T2` → giảm 3 DOF → hạ `N`, hạ rào DSR"*. Đúng về hướng, **không đáng
kể về lượng**, vì `h = √(2·ln N)` phụ thuộc `N` theo **log**:

| `N` | 114 | 96 | 78 | 54 | 20 |
|---|---|---|---|---|---|
| `h` | 3,0777 | 3,0214 | 2,9518 | 2,8245 | 2,4477 |

`N` 114 → 96 hạ `h` **1,8%**. Cắt tận `N = 20` cũng chỉ hạ **20%**. Trong khi `n` 28 → 206 hạ thuế
nhiễu **63%**. ⇒ Ai định đóng băng thêm tham số để *"hạ rào cho dễ qua"* thì nên biết trước: đòn bẩy
nằm ở `n`, không ở DOF. *(Phiên `c3` tính độc lập, cùng kết luận: `N` 114→30 hạ `h` 15,3%.)*

### 1.5 Nhánh 1 nay chỉ còn ĐÚNG MỘT tiêu chí hỏng

Sau `TD-0207` (`61479b7`), H-4 đo lại trên **cả ba arm** (`td0212-ba-arm-sau-va.json`) — tất cả đều
dưới ngưỡng 40% của §10.2:

| Arm | `TP1_zone_doi_dien` | `TP1_fallback` | **H-4** |
|---|---|---|---|
| `Z0-T0` | 163 | 46 | **22,0%** |
| `Z0-T1` | 58 | 4 | **6,5%** |
| `Z0` | 7 | 1 | **12,5%** |

**H-4 không còn là tiêu chí hỏng** — nó từng là một lỗi mã, không phải một tính chất của thị trường.

⇒ Trong toàn bộ Nhánh 1, tiêu chí duy nhất đang hỏng là **44,8 lệnh/năm < sàn 150**. Và cách đọc
chính con số đó lại treo vào **`MT-29`** (§10.2 áp cho MỖI HƯỚNG hay cho TỔNG hệ thống — chưa chốt).

---

## 2. Quyết định

### 2.1 D4 được hỏi HAI câu, không phải chín

| Câu hỏi | Arm mang câu trả lời | `n` | Phán quyết được? |
|---|---|---|---|
| **Bộ lọc trend Phần 2 có đáng không?** | `Z0-T0` · `Z0-T1` · `Z0`(=`Z0-T2`) | 883 · 206 · 28 | ✅ **CÓ** cho A và B |
| **DCA ba tranche có đáng không?** | `Z0` vs `Z3`/`Z3b` | 28 vs 28 | ❌ **KHÔNG**, và không bao giờ ở tần suất này |

D4 từ nay **chỉ phán quyết câu thứ nhất**. Câu thứ hai chuyển sang đường ở §2.4.

### 2.2 Dự báo INCONCLUSIVE của nhóm C được ghi TRƯỚC, không phát hiện SAU

Bảy arm nhóm C **được khai là INCONCLUSIVE ngay tại DR này**, kèm phép tính §1.2. Khi bộ chạy
TD-0184 trả kết quả, việc nhóm C ra INCONCLUSIVE là **xác nhận một dự báo**, không phải một phát
hiện. 🔴 **Nếu nhóm C ra bất cứ kết cục nào KHÁC INCONCLUSIVE ⇒ nghi ngờ BỘ ĐO trước, không mừng.**
Cụ thể: ra FAIL nghĩa là `std_R` đo được < 0,173 ⇒ gần như chắc chắn thang `R_realized` sai
(`MT-25`), không phải arm dở; ra PASS nghĩa là `mean_R ≥ 0,44 R` ⇒ gần như chắc chắn lookahead hoặc
lỗi kế toán. Cả hai đều là **cờ đỏ về tầng đo**, đúng câu hỏi chẩn đoán N10.

### 2.3 Chín trial vẫn tiêu như `DR-D4-01` đã chốt — nhưng đổi MỤC ĐÍCH của bảy suất

**Không đụng `DR-D4-01`**: vẫn `RESERVE` cả 9 trước khi chạy arm đầu, vẫn Long-only, vẫn `B2`.
🔴 **Không mở lại** phương án *"chạy từng arm rồi dừng giữa chừng"* mà chủ dự án đã từ chối ở
`DR-D4-01 §4b` — DR này quyết TRƯỚC khi chạy, không dừng giữa chừng.

Đổi là đổi **hai suất mua gì và bảy suất mua gì**:

| Arm | Suất mua cái gì |
|---|---|
| `Z0-T0`, `Z0-T1` | **Phán quyết Nhánh 1** — PASS/INCONCLUSIVE/FAIL đầy đủ |
| 7 arm nhóm C | **Thống kê MÔ TẢ** — `mean_R` thô + khoảng tin cậy + `n` + thuế nhiễu, làm đầu vào cho quyết định ở §2.4 |

🔴 **CẤM đọc `DSR_adj` của nhóm C như một phán quyết** — mở rộng `DR-D4-09 §2.4` (vốn chỉ cấm xếp
hạng GIỮA hai arm lệch cỡ mẫu) sang cả câu hỏi TUYỆT ĐỐI khi `thuế nhiễu > ngưỡng`.

### 2.4 Câu DCA đi đường nào — và mặc định khi không đo được

Câu *"DCA ba tranche có đáng không"* rời khỏi cổng thống kê và đi đường **lý lẽ thiết kế + quan sát
vận hành**, quyết tại **D11 (dry-run)** với ba đầu vào, tất cả đã hoặc sẽ có mà không tốn trial thêm:

1. `mean_R` thô + CI của `Z0` vs `Z3`/`Z3b` từ §2.3 — **mô tả, không phán quyết**;
2. phân bố tranche thực tế (đã đo: chỉ **18,07%** lệnh bơm đủ 3 tranche, `dg2-explore-quet-arm.json`);
3. hành vi tranche 2/3 quan sát ở dry-run.

🔴 **Mặc định khi cả ba không cho kết luận rõ: `Z0` single-entry.** Lý do — và đây là phần cần chủ
dự án xác nhận tường minh, không phải phần tôi tự chốt:

- §10.1 đã viết sẵn *"Z0 ≥ Z3/Z3b → bỏ DCA, Tool D thành single-entry — **kết quả TỐT, không phải
  thất bại**"*;
- một cơ chế **không chứng minh được là đáng** thì không nên lên tiền thật — cùng logic fail-closed
  mà N6 áp cho gate (*"gate không thể vô tình PASS"*);
- tranche 2/3 **bơm thêm tiền khi giá đi ngược**, tức hướng sai của nó đắt hơn hướng sai của việc
  bỏ qua — cùng tiêu chí bất đối xứng đã dùng để chốt `MT-22` phương án A.

⏳ **Chờ chủ dự án xác nhận mặc định này.** Nếu không xác nhận, câu DCA ở lại trạng thái mở và
**không được ngầm hiểu theo hướng nào**.

---

## 3. Vì sao đây là làm CHẶT hơn, không phải nới

Không đổi **một ngưỡng nào**: `0,10 R` · `≥ 20%` · `150 lệnh/năm` · `N = 114` · rào `3,0777` giữ
nguyên tuyệt đối. Thứ đổi là **câu hỏi**, không phải **thước**.

Và nó chặt hơn ở ba chỗ:

1. **Ngăn một kết luận SAI đi vào dự án qua cửa hợp lệ.** Nếu để nguyên, Nhánh 2 trả *"Z3 không vượt
   Z0 ≥ 20%"* rồi bị đọc thành FAIL ⇒ **bỏ DCA vĩnh viễn dựa trên một phép đo không có khả năng
   phát hiện mức hiệu ứng đang hỏi** (`DR-D4-09 §4`: cần `n_giao ≈ 7.400`, có 28).
2. **Ngăn `Z0-T0` thắng bảng vì đông lệnh chứ không vì có edge.** `DR-D4-09 §1.4` đã chỉ ra thiên
   lệch cấu trúc này; DR này thi hành hệ quả — `Z0-T0` được phán quyết, nhưng phán quyết đó là về
   **chính nó**, không phải một thứ hạng so với nhóm C.
3. **Ghi dự báo TRƯỚC** (§2.2), nên bộ đo bị chính dự báo của mình kiểm tra ngược.

---

## 4. Giới hạn TỰ KHAI

- **Không cứu được vấn đề power.** DR này không làm nhóm C đo được; nó chỉ đảm bảo không ai tiêu 9
  suất rồi tưởng mình đã hỏi được câu DCA. Cùng tinh thần `DR-D4-09 §4`.
- **`std_R` vẫn CHƯA ĐO** (`MT-27`). Mọi bảng dùng dải 0,58–1,50 thay vì một số. Kết luận §1.2 đúng
  trên **toàn dải**, và §1.2 đã cho cận lật tường minh (`std_R < 0,173`).
- ~~`Z0-T0` và `Z0-T1` là số TRƯỚC bản vá `TD-0207`~~ ✅ **ĐÃ GIẢI** — `TD-0212` đo lại cả ba arm sau
  vá (`td0212-ba-arm-sau-va.json`): `Z0-T0` 883 (−8%), `Z0-T1` 206 (không đổi), `Z0` 28 (không đổi).
  **§7 điều kiện 3 đã kiểm và KHÔNG kích hoạt** (`Z0-T1` không rơi dưới 100) ⇒ §2.1 giữ nguyên.
  Mọi con số `n` trong DR này nay là số **sau vá**, không còn trộn hai hệ thống.
- **Kết luận này chỉ cho LONG.** `DR-D4-01 §2` đã ghi; Short mở ra một bộ arm thứ hai với `n` riêng
  chưa ai đo (`do_short_pheu_tin_hieu_explore.json` mới tới tầng tín hiệu, con số 237,8 lệnh/năm là
  **ƯỚC LƯỢNG**, không đo).

---

## 5. Điều DR này KHÔNG chốt

- **Không** chốt `MT-29` (§10.2 áp cho mỗi hướng hay cho tổng hệ thống). Nó quyết cách đọc chính con
  số 44,8 vs 150 — cần quyết riêng, không gộp vào đây.
- **Không** chốt `std_R` (`MT-27`), không chốt `ρ`.
- **Không** đụng `DR-D4-01` (Long-only, 9 trial, đặt chỗ cả lô) và **không** đụng `DR-D4-09` (cách
  đọc kết quả) — chỉ ghi đính chính `n` cho §1.1 của nó tại §1.1 trên.
- **Không** đổi ngưỡng nào của §10.2, không đổi `N`, không đóng băng thêm tham số nào.
- **Không** cấp phép chạm LOCKBOX. Phương án *"dùng cả CALIB+WFO"* ở §1.3 chỉ là **phép tính trần**,
  **không phải đề xuất** — nó phá phân vùng `DR-011` và DR này không xin phép làm thế.
- **Không** chốt mặc định `Z0` single-entry của §2.4 — đó là đề xuất chờ chủ dự án xác nhận.

---

## 6. Kế toán

`dof_goc` 28 · `|tier_b|` 12 · **`N` = 114** · rào DSR **3,0777** — **không đổi**.
**0 trial**: DR này không đánh giá cấu hình nào, không chạm CALIB/WFO/LOCKBOX. Sổ
`trial_registry.jsonl` giữ nguyên 13 dòng tại thời điểm ký.

---

## 7. Điều kiện mở lại — viết TRƯỚC, khuôn OQ-07

1. **`std_R` đo được < 0,173** ⇒ §1.2 sai, nhóm C không còn là INCONCLUSIVE-theo-định-nghĩa ⇒ tính
   lại toàn bộ DR. *(Cận này gần như chắc chắn không xảy ra với một hệ thống có SL cứng `−1R`; nếu
   xảy ra, nghi thang `R_realized` trước — `MT-25`.)*
2. **`n` của nhóm C đo được ≥ 370** trên một cửa sổ hợp lệ mà **không** phá `DR-011` và **không**
   đổi định nghĩa arm ⇒ câu DCA phán quyết được, §2.1 và §2.4 phải viết lại.
3. **`Z0-T1` đo lại sau `TD-0207` cho `n` < 100** ⇒ nhóm B rơi khỏi vùng phán quyết được, §2.1 chỉ
   còn `Z0-T0`, và phải ghi vào `d4_han_che`.
4. **`MT-29` chốt theo hướng "§10.2 áp cho TỔNG hệ thống"** ⇒ phải xét lại §1.3 (Short khi đó có
   cộng `n`, trần đổi từ 162 lên ~324 — vẫn dưới 370, nhưng phải tính lại và ghi).

❌ **KHÔNG** phải điều kiện mở lại: kết quả D4 không như mong đợi; hoặc *"nhóm C ra INCONCLUSIVE
thật"* — đó là **xác nhận dự báo §2.2**, không phải thông tin mới.

---

## 8. Việc thi hành

| Chặng | Việc |
|---|---|
| a | `TD-0184` (bộ chạy ablation): bản ghi kết quả mang cờ `pham_vi_phan_quyet` ∈ {`phan_quyet`, `mo_ta`} cho từng arm, gán theo §2.1 — **không** để bộ đọc tự suy từ `n` |
| b | Gate `L-Z57`: bộ kết quả giả lập trong đó một arm nhóm C mang `DSR_adj` vượt ngưỡng mà cờ là `mo_ta` ⇒ gate **KHÔNG** được trả PASS ⇒ test ĐỎ nếu trả |
| c | Test khoá: dự báo §2.2 được ghim thành hằng — arm nhóm C mà kết cục ≠ INCONCLUSIVE ⇒ báo đỏ kèm thông báo trỏ về §2.2 (cờ đỏ tầng đo, không phải kết quả) |
| d | `d4_han_che` khi đóng cổng D4: ghi rõ D4 **không** phán quyết câu DCA, kèm §2.4 |

---

## 9. Lịch sử

| Ngày | Sự kiện |
|---|---|
| 09/09/2026 | `DR-D4-08 §6` dừng TD-0184 vì 63,6 lệnh/năm < sàn 150 — dự báo INCONCLUSIVE, chưa lượng hoá |
| 09/09/2026 | `DR-D4-09` định nghĩa ba kết cục và phép so paired, dùng `n ≈ 40` ngoại suy |
| 10/09/2026 | TD-0205 **đo** `n` riêng trên WFO: nhóm C là **28**, không phải 40 |
| 10/09/2026 | TD-0207 vá lỗi TP1 ⇒ H-4 100% → 18,2%; Nhánh 1 còn đúng một tiêu chí hỏng |
| 10/09/2026 | TD-0208 đối chiếu checklist ngoài; phép tính 0-trial cho thấy nhóm C **ngoài tầm với**, không phải thiếu mẫu |
| 10/09/2026 | Phiên `c3` bác `×2` cho Short (spec dòng 4187 / 4973-4974) ⇒ trần 324 → **162**, kết luận mạnh hơn; và chặn ca nghi ngờ `MT-25` bằng cận `λ < 0,138` |
| 10/09/2026 | Chủ dự án chốt **phương án A** — DR này |
| 10/09/2026 | `TD-0212` đo lại ba arm SAU bản vá: `Z0-T0` 883 (−8%), `Z0-T1` 206, `Z0` 28. **§7 điều kiện 3 kiểm — KHÔNG kích hoạt**, §2.1 giữ nguyên. H-4 cả ba arm dưới 40%. Bản vá đổi số đếm của arm nhiều lệnh, không đổi arm ít lệnh — cơ chế tranh chỗ mở, §1.1 |
