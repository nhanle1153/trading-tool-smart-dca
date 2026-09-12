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
| **C** | `Z0` `Z1` `Z2` `Z3` `Z3b` `Z0-V1` `Z0-S1` | ~40 (một số chung) | **8 → 40** (bảy số riêng) | xem §2.5 |

🔴 **`DR-D4-09` gộp bảy arm nhóm C vào MỘT con số `n`, và `TD-0214` chứng minh phép gộp đó SAI.**
`n` thật trải từ **7,7** (`Z1`) tới **39,9** (`Z0-V1`) — chênh **5,2 lần**. Bảng `n` phải tách theo
arm; chi tiết ở §2.5. *(Đây là giả định kế thừa, không phải phát hiện mới của DR này — nhưng DR này
là nơi nó bị bác, nên ghi ở đây.)*

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
thuế nhiễu(arm) = h/√n · std_R          h = 3,0777
ngưỡng Nhánh 1  = 0,10 R
⇒ INCONCLUSIVE ⇔ std_R > 0,10·√n / h

  arm "khoẻ" nhất nhóm C — Z0-V1, n = 40 :  std_R > 0,205
  arm điển hình         — Z0,   n = 28 :  std_R > 0,173
  arm đuối nhất         — Z1,   n =  8 :  std_R > 0,090
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
| **DCA ba tranche có đáng không?** | `Z0` vs `Z3`/`Z3b` | 28 vs 28 vs 28 | ❌ **KHÔNG**, và không bao giờ ở tần suất này |
| **SL neo zone có tốt hơn SL theo ATR không?** | `Z1` vs `Z0` | 8 vs 28, `n_giao = 6` | ❌ **KHÔNG** — và vì một lý do khác hẳn, xem §2.5 hạng (3) |

`n` của **cả chín arm**, lần đầu đo trên cùng một hệ thống (sau vá `TD-0207`):

| Arm | `Z1` | `Z0`=`Z3`=`Z3b`=`Z2` | `Z0-S1` | `Z0-V1` | `Z0-T1` | `Z0-T0` |
|---|---|---|---|---|---|---|
| **`n`** | **8** | 28 | 31 | 40 | **206** | **883** |
| sàn `S` = `h/√n` | 1,109 | 0,578 | 0,555 | 0,487 | 0,214 | 0,104 |

Vạch phân chia giữa *"phán quyết được"* và *"không"* nằm đúng giữa `Z0-V1` (40) và `Z0-T1` (206) —
và nó trùng khít với ranh giới **có/không có tầng lọc trend 1D**, không phải một ngưỡng tuỳ ý.

D4 từ nay **chỉ phán quyết câu thứ nhất**. Câu thứ hai chuyển sang đường ở §2.4.

### 2.2 Dự báo INCONCLUSIVE của nhóm C được ghi TRƯỚC, không phát hiện SAU

Bảy arm nhóm C **được khai là INCONCLUSIVE ngay tại DR này**, kèm phép tính §1.2. Khi bộ chạy
TD-0184 trả kết quả, việc nhóm C ra INCONCLUSIVE là **xác nhận một dự báo**, không phải một phát
hiện. 🔴 **Nếu nhóm C ra bất cứ kết cục nào KHÁC INCONCLUSIVE ⇒ nghi ngờ BỘ ĐO trước, không mừng.**
Cụ thể: ra FAIL nghĩa là `std_R` đo được thấp hơn **điểm lật của chính arm đó** — `0,090` (`Z1`) ·
`0,173` (`Z0`/`Z3`/`Z3b`/`Z2`) · `0,180` (`Z0-S1`) · `0,205` (`Z0-V1`) — ⇒ gần như chắc chắn thang
`R_realized` sai (`MT-25`), không phải arm dở; ra PASS nghĩa là `mean_R` vượt ngưỡng hiệu dụng của
arm đó (thấp nhất là `0,383 R` ở `Z0-V1`, cao nhất `0,743 R` ở `Z1`, tính ở `std_R = 0,58`) ⇒ gần
như chắc chắn lookahead hoặc
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

✅ **ĐÃ DUYỆT — chủ dự án chốt 12/09/2026: mặc định `Z0` single-entry.** Mục này ghi cả đường đã bị
loại lẫn lý do, vì đường bị loại **do chính bản trước của mục này đề ra**.

🔴 **ĐÍNH CHÍNH — bản trước định tuyến câu DCA sang D11 (dry-run). Đó là SAI HƯỚNG: D11 có ÍT thông
tin hơn chỗ ta đang đứng.** Tính từ 44,8 lệnh/năm đã đo (quy đổi pool 102):

| Giai đoạn | Số lệnh |
|---|---|
| Backtest WFO — **đang có** | **28** |
| Dry-run 2 tháng | 7,5 |
| Dry-run 3 tháng | 11,2 |
| Dry-run 12 tháng | 44,8 |
| Cần để **thôi** INCONCLUSIVE (`std_R` = 0,58) | **319** ⇒ **7,1 năm** chạy liên tục |

⇒ **Câu DCA không bao giờ được trả lời bằng dữ liệu ở tần suất này** — không ở backtest, không ở
dry-run, không ở nhiều năm live đầu. *"Quyết sau"* vì thế **không phải một lựa chọn**, nó là hoãn
không có đường ra. Và hoãn thì đắt hơn: mang thêm máy móc chưa xác minh vào tiền thật, **và tiêu
lượt chạm lockbox duy nhất** (`DR-011`) cho một cấu hình không biện minh được.

🔴 **Cảnh báo về đầu vào (2) — con số `18,07%` đã bị RÚT khỏi DR này.** Bản đầu dẫn *"chỉ 18,07%
lệnh bơm đủ 3 tranche"* từ `dg2-explore-quet-arm.json`. Kiểm header file đó: **48 mã alt**, cửa sổ
**`[T0,T2]`**, đo **09/09/2026** — tức trước cả `19dfabc` (nối §3.3b) lẫn `61479b7` (vá TP). Ba
điểm lệch cùng lúc: sai số mã (48 vs 88), sai cửa sổ (không phải WFO — cửa sổ ablation thật), và
`DR-D4-08 §8` đã ghi sẵn bằng chữ rằng bảng arm đo trước `19dfabc` **không so trực tiếp được** với
sau.
🔑 **Nặng hơn cả lỗi thời: dùng con số đó làm bằng chứng là VÒNG TRÒN.** Sau bản vá, TP1 nổ theo
zone ở 18/22 lệnh `Z0`; cộng với chốt *"đã chốt TP1 thì KHÔNG DCA thêm"* (09/09/2026), một tỉ lệ
"đủ 3 tranche" thấp phần lớn phản ánh **chính luật thoát của ta**, không phản ánh việc DCA có giá
trị hay không. Lấy nó để kết luận *"DCA ít khi tham gia nên bỏ cũng được"* là dùng hệ quả của một
quyết định của mình làm bằng chứng cho một quyết định khác của mình.
⏳ `Z3`/`Z2` **chưa từng được đo lại sau bản vá** (kiểm: `td0205`, `td0212`, `td0207-h4-sau-va` đều
chỉ có `Z0-T0`/`Z0-T1`/`Z0`). Phải đo lại trước khi đầu vào (2) được dùng — **0 trial**, EXPLORE,
chỉ đếm.

🔴 **Mặc định đề xuất khi cả ba đầu vào không cho kết luận rõ: `Z0` single-entry.**

⚠️ **ĐÂY LÀ MỘT QUYẾT ĐỊNH MỚI, KHÔNG PHẢI MỘT DẪN CHIẾU.** Bản đầu của DR này trình nó như thứ
§10.1 đã ngụ ý — **sai**. Kiểm spec: dòng **4295** ghi *"NHÁNH 2 … **CHỈ chạy nếu Nhánh 1 đã
PASS**"*, và mọi điều khoản mặc-định-Z0 (nhánh "KHÔNG" ở dòng 4310, và `DR-015 §5.1` dẫn ở dòng
4302) đều nằm **bên trong Nhánh 2**. Nhóm C là **INCONCLUSIVE**, không phải PASS ⇒ **không điều
khoản nào trong số đó kích hoạt**. ⇒ Spec **không có** mặc định cho trạng thái *"Nhánh 1
INCONCLUSIVE"*. Ba lý lẽ dưới đây là **lý do đề xuất**, không phải căn cứ văn bản.

- 🟢 **Có tiền lệ nguyên tắc, ở mức TƯƠNG TỰ chứ không phải dẫn chiếu:** dòng 4302 lập nguyên tắc
  *"backtest không đủ tư cách phân xử ⇒ rơi vào nhánh KHÔNG (mặc định Z0) — dự án TIẾP TỤC bình
  thường, đây không phải kết cục xấu"*. Nguyên tắc đó chỉ đúng hướng với ta; nhưng nó viết cho một
  chế độ hỏng **khác** (người thắng đổi giữa hai chiều hiệu chỉnh Δ_R), không phải cho thiếu mẫu.
  Dùng được như **loại suy**, không dùng được như trích dẫn.
- 🟢 **Fail-closed:** một cơ chế **không chứng minh được là đáng** thì không nên lên tiền thật —
  cùng logic N6 áp cho gate (*"gate không thể vô tình PASS"*). Đây là lý lẽ mạnh nhất trong ba cái,
  vì nó không cần một phép đo nào.
- 🟢 **Máy móc chưa xác minh — lý lẽ THAY THẾ cho lý lẽ rủi ro đã bị rút (xem ngay dưới).** `Z0` bỏ
  được: kế hoạch ba mức giá, `adjust_trade_position`, DG1–DG5, năm hệ số `mult_*`, luật *"đã chốt
  TP1 thì không DCA thêm"*, và **nguyên nhân gốc của `MT-25`** (thang `R_realized` co vì mẫu số giả
  định ba tranche). DCA là phần hệ thống có **nhiều máy móc chưa xác minh nhất**, và đồng thời là
  phần **duy nhất không thể xác minh**.

- 🔴 ~~**Khẩu vị rủi ro:** tranche 2/3 bơm thêm tiền khi giá đi ngược, nên hướng sai của nó đắt hơn~~
  **RÚT — lý lẽ này SAI, không phải yếu.** Kiểm code: `sizing.py:28` ghi *"`planned_risk_usdt` không
  đổi tới 1e-9"* dù khớp một hay ba tranche, và `sizing.py:277` chặn cứng `Σ w_tranche = 1`.
  ⇒ **Tổng rủi ro mỗi lệnh bị chặn cứng theo thiết kế** (`D0.1`: size suy ngược từ ngân sách rủi ro
  cố định). DCA **không** bơm thêm rủi ro — nó phân bổ **cùng một** ngân sách rủi ro vào ba mức giá.
  Giữ lại dòng gạch để không ai dựng lại lý lẽ đó lần nữa. *(Phiên `c3` hạ nó xuống "khẩu vị rủi
  ro"; kiểm code thì phải bỏ hẳn — đây là lần thứ sáu trong hai ngày một suy luận nghe hợp lý bị một
  phép kiểm dưới một phút bác.)* Tiền lệ `MT-22` có phép
  đo kèm (A 43,1% vs B 81,2%); ở đây **không có**. Vì thế nó đứng ở hạng thấp hơn hai cái trên.

#### Cái giá thật của việc bỏ DCA — nhỏ hơn tên gọi của nó gợi ý

🔑 **`Z0` và `Z3` có ĐÚNG CÙNG 22 lệnh** (`td0212` + `td0213`, cùng phễu 2.621 → 1.104 → 32). DCA
**không tạo thêm một cơ hội nào** — nó chỉ đổi chuyện xảy ra **sau khi** vào lệnh. Chọn `Z0` vì thế
**không mất lệnh nào**, chỉ mất cơ chế hạ giá vào trung bình.

Cơ chế đó hiện thân ở mức: tranche 2 nổ **8/22 (36%)**, tranche 3 nổ **2/22 (9,1%)**. Hơn một nửa
số lệnh (**12/22**) dừng ở một tranche — tức **đã chạy như `Z0`** rồi.

#### Bốn điều được chốt

1. **Mặc định `Z0` single-entry.** Căn cứ: không phán quyết được ở **mọi** giai đoạn (bảng trên) +
   lockbox chỉ một lượt chạm + `Z0` không mất lệnh nào.
2. 🔴 **DCA KHÔNG BỊ BÁC BỎ.** Nó chuyển thành giả thuyết trong Idea Queue, ghi nguyên văn:
   ***"chưa từng được đo, không phải đã thất bại"***. Phân biệt này bắt buộc — `DR-D4-09 §2.2` sinh
   ra đúng để chặn việc đọc INCONCLUSIVE thành FAIL, và bỏ DCA **vĩnh viễn** dựa trên một phép đo
   không có khả năng phát hiện chính là kết cục nó cấm.
3. **Điều kiện mở lại, viết TRƯỚC (khuôn OQ-07):** DCA được xét lại khi hệ thống đạt **`n ≥ 319`**
   trên một cấu hình cố định. ⚠️ Ở 44,8 lệnh/năm đó là **7,1 năm**, nên trên thực tế đây là **điều
   kiện về việc NÂNG TẦN SUẤT, không phải về việc chờ** — nói thẳng để không ai tưởng nó sẽ tự đến.
   ❌ **KHÔNG** phải điều kiện mở lại: *"thấy tiếc"*, hoặc một kết quả `Z0` không như mong đợi.
4. **Phương án giữa (bỏ tranche 3, giữ hai tranche) bị LOẠI ở đây, có lý do.** Tranche 3 chỉ nổ
   9,1% nên nó rẻ về máy móc — nhưng đó là **cấu hình không ai đăng ký**, và chọn nó **vì vừa nhìn
   thấy tranche 3 hiếm nổ** chính là chọn-sau-khi-nhìn-số mà `DR-010` sinh ra để cấm. Nó thuộc Idea
   Queue, không thuộc quyết định này.

🔴 **Điều quyết định này KHÔNG dựa vào:** không một con số expectancy/PnL nào — vì trên đĩa **không
có con số nào để dựa vào**. Nó **không** phát biểu rằng DCA kém. Nó phát biểu rằng **không thể
biết**, và đưa thứ không biện minh được vào lượt lockbox duy nhất là cái giá cao hơn cái mất khi bỏ
nó.

---

### 2.5 BA cách một ma trận ablation không đo được thứ nó khai — và dự án nay có ví dụ thật cho cả ba

§1.2 là hạng **(0)**: *mẫu quá nhỏ so với nhiễu*. Nó cần một giả định về `std_R`. Ba hạng dưới đây
**không cần giả định nào** — chúng là tính chất của **ma trận thiết kế**, không phải của nhiễu:

| Hạng | Nội dung | Ví dụ thật | Trạng thái |
|---|---|---|---|
| **(1)** | **Biến KHÔNG đổi gì** — hai arm cho cùng một tập lệnh | `MT-21` (`Z1`≡`Z0`), `MT-15` (`Z0`≡`Z0-V1`) | ✅ **đã chết bằng phép đo** (`TD-0214`) — chúng trùng vì arm **chưa được nối** |
| **(2)** | **Biến gần như không tồn tại** — đổi, nhưng quá ít để phân xử | `Z2` vs `Z3` (**0** lệnh khác), `Z3b` vs `Z3` (**1/22** lệnh) | 🔴 còn sống (`TD-0213`) |
| **(3)** | **Biến đổi KÈM một thứ khác đổi theo** — arm khác thật, nhưng khác vì **hai** lý do trộn vào nhau | `Z1` vs `Z0` (`TD-0215`) | 🔴 **mới**, xem dưới |

🔴 **Hạng (3) khác hai hạng kia ở chỗ đòi cách xử ngược lại.** Hạng (1) và (2) là *"không đo được"*
⇒ hành động là thêm mẫu hoặc bỏ phép so. Hạng (3) là *"**đo được, nhưng không phải thứ mình
tưởng**"* ⇒ hành động là **sửa lại câu hỏi**, vì con số vẫn ra và vẫn trông hợp lệ.

**Ca `Z1` vs `Z0`** (`td0215-z1-vs-z0-tap-lenh.json`, `Z0`+`Z1` chạy CÙNG một lượt):
`n_A = 22 · n_B = 6 · n_giao = 6 · chi_co_o_B = 0` ⇒ **`Z1` là tập con NGHIÊM NGẶT của `Z0`**.
72,7% lệnh của `Z0` biến mất trong `Z1`, và biến mất ở **cổng kết nạp §6.8f** — vì `Z1` đổi SL ⇒
`r_eff_plan` đổi ⇒ cỡ lệnh đổi ⇒ bị chặn — **không phải vì SL tốt hay xấu**.

Phải tách hai vế, vì chúng khác nhau:

- **(i) Nội tại — KHÔNG hỏng.** Trên 6 lệnh giao, `Z1` và `Z0` khác **đúng một** biến (kiểu SL).
  Phép so paired ở đó **hợp lệ về cấu trúc**. Không được ghi là *"phép so vô hiệu"* — nó không vô
  hiệu, nó **hẹp**.
- **(ii) Ngoại suy — HỎNG.** Sáu lệnh đó được chọn bởi **chính cơ chế tương quan với biến đang
  xét** (cỡ lệnh là hàm của SL). Kết quả trên chúng **không suy rộng** ra 22 lệnh của `Z0`.

⇒ Phép so `Z1` vs `Z0` **không** trả lời *"SL neo zone hay SL ATR tốt hơn"*. Nó trả lời *"trên tập
con 27% mà cả hai kiểu SL cùng qua được cổng kết nạp, kiểu nào tốt hơn"* — một câu hỏi khác, và
không phải câu §10.1 đặt ra. Cộng thêm cỡ mẫu: `n_giao = 6` cho thuế nhiễu paired **0,497** (`ρ`=0,95)
đến **1,571** (`ρ`=0,5), tức **5,0 → 15,7 lần** ngưỡng 0,10 R — nên kể cả vế (i) hợp lệ, nó cũng
không phán quyết được gì.

📌 **Một quan sát thật về SL, chỉ là trên `n = 6`:** `Z1` có `TIME_STOP` **2/6 (33%)** trong khi
`Z0` có **0/22**. SL theo `2,2×ATR` giữ lệnh tới hết hạn ở một phần ba số ca. Ghi vì nó là dấu hiệu
về hành vi, **không** dùng làm căn cứ.

---

**Phần dưới đây là chi tiết của hạng (1) và (2), đo ở `TD-0213`/`TD-0214`.**

`TD-0213` + `TD-0214` (`td0213-arm-dca-sau-va.json`, `td0214-ba-arm-cuoi-sau-va.json`; 88 mã, WFO,
**sau vá**, 0 trial) là **lần đầu cả chín arm có số trên cùng một hệ thống**. Hai kết quả, ngược
hướng nhau:

| Phép so | Biến điều khiển | `n` của arm | Trạng thái **sau vá** |
|---|---|---|---|
| `Z2` vs `Z3` | DG5 | 28 vs 28 | 🔴 **0 lệnh khác nhau** — trùng khít cả `exit_reason` lẫn `tp1_theo_nguon` |
| `Z3b` vs `Z3` | DG6 Early Invalidation | 28 vs 28 | 🔴 **đúng 1/22 lệnh** (`DG6_EARLY_INVALIDATION` nổ 1 lần) |
| `Z1` vs `Z0` | SL neo zone vs `2,2×ATR` | **8** vs 28 | ✅ **KHÁC RÕ** — 6 vs 22 lệnh, `n_giao = 6` |
| `Z0-V1` vs `Z0` | điều kiện (c) volume | **40** vs 28 | ✅ **KHÁC RÕ** — 31 vs 22 lệnh |
| `Z0-S1` vs `Z0` | notional cố định | **31** vs 28 | ✅ **KHÁC** — 24 vs 22 lệnh |

🔴 **Ba dòng ⏳ trước đây nay đã có số, và chúng BÁC hai kết luận-trùng cũ — bằng phép đo, không
bằng lập luận:** `MT-21` (*"`Z1` ≡ `Z0`"*) và `MT-15` (*"`Z0` trùng khít `Z0-V1`"*) **đều hết hiệu
lực** sau `TD-0192`/`TD-0193`. Cả hai từng đúng vì arm **chưa được nối**; nối rồi thì chúng là arm
thật, có tập lệnh riêng.

⚠️ **Và cả hai chết theo hướng làm bài toán KHÓ HƠN, không dễ hơn:** chúng không phải arm thừa —
chúng là arm thật với cỡ mẫu **riêng, phần lớn NHỎ hơn** `Z0`. `Z1` chỉ **6 lệnh** (`n = 8`, sàn
`S = 1,109`) — **arm đuối nhất trong cả chín**, kém `Z0` gần gấp đôi về sàn.

🔑 **Chênh lệch `n` trong nhóm C KHÔNG đến từ tranh chỗ mở — nó đến từ TẦNG ENTRY khác nhau.**
`Z1` đổi SL ⇒ `r_eff_plan` đổi ⇒ cỡ lệnh đổi ⇒ cổng kết nạp §6.8f chặn khác; `Z0-V1` tắt điều kiện
(c) volume ⇒ nhiều tín hiệu hơn. Tức tiền đề *"cả nhóm C chung tầng entry"* **sai ngay ở tiền đề**,
không phải sai ở hệ quả — khác hẳn cơ chế tranh chỗ đã giải thích `Z0-T0` ở §1.1.

🔑 **Vì sao đây là một hạng riêng, không phải một biến thể của §1.2.** Lập luận INCONCLUSIVE ở §1.2
nói *"mẫu quá nhỏ so với nhiễu"* và cần một giả định về `std_R`. Hạng này nói *"**biến điều khiển
gần như không thay đổi trên dữ liệu này**"* — nó là tính chất của **ma trận thiết kế**, không phải
của nhiễu, nên nó đúng **với mọi `std_R`, không cần giả định nào**. Một khác biệt một-lệnh không
phân xử được tiêu chí *"vượt ≥ 20%"* dù phương sai bằng bao nhiêu.

⇒ Hệ quả cho §2.3: trong bảy suất mua **thống kê mô tả**, ít nhất **một suất (`Z2`) mua một tập
lệnh trùng khít với `Z3`**, và một suất nữa (`Z3b`) mua một tập lệch đúng một lệnh. Ghi ra để chủ
dự án biết trước khi D4 chạy. 🔴 **DR này KHÔNG tự sửa kế toán 9 suất của `DR-D4-01`** — đó là
quyết định của chủ dự án; đây chỉ là thông tin đầu vào nếu chủ dự án muốn mở lại nó.

📌 **Chỗ này là một ca đáng giữ về kỷ luật suy luận, vì cả hai chiều đều xảy ra trong một ngày.**
Bản trước của §2.5 (viết khi mới có `TD-0213`) từ chối suy rộng kết quả của ba arm sang bảy, và ghi
*"không có phép đo thì không có phát biểu"* cho ba dòng ⏳. `TD-0214` xác nhận sự thận trọng đó là
đúng: bốn arm đo trước **thật sự** chung `n = 28`, nhưng ba arm còn lại **không**, và nếu suy rộng
thì `Z1` đã bị gán `n = 28` trong khi thật ra là **8** — sai **3,5 lần**, đúng ở arm đuối nhất.
Ngược lại, kết luận-trùng cũ (`MT-21`, `MT-15`) tồn tại được lâu **chính vì** ai đó từng suy rộng
một quan sát qua một bản vá đã làm nó hết đúng.

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
- ✅ ~~Giả định *"cả nhóm C cùng `n = 28` vì chung tầng entry"* chưa được kiểm~~ — **ĐÃ KIỂM VÀ ĐÃ
  BÁC** (`TD-0213` + `TD-0214`): `n` trải **8 → 40**, giả định sai. Giữ nguyên đoạn ghi-trước dưới
  đây vì nó là thứ giữ cho phép đo không bị đọc quá tay, và vì nó **đã ứng nghiệm đúng**.

  **Cách đọc kết quả đó ĐƯỢC VIẾT TRƯỚC KHI CÓ SỐ, đây:** `n` tới hạn để một arm nhóm C **thôi**
  là INCONCLUSIVE-theo-định-nghĩa (tức thuế nhiễu tụt xuống bằng ngưỡng 0,10 R) là

  | `std_R` | 0,58 | 1,00 | 1,25 | 1,50 |
  |---|---|---|---|---|
  | `n` tới hạn | **319** | 947 | 1.480 | 2.131 |

  ⇒ Ngay cả ở `std_R` rộng lượng nhất, một arm nhóm C phải có `n ≥ 319`.
  **Kết luận §1.2/§2.1/§2.2 vì thế BẤT BIẾN với mọi kết quả có thể có.** Thứ duy nhất phải sửa nếu
  các arm lệch nhau là **bảng `n` theo arm** ở §2.1/§2.3 — tách từng arm thay vì ghi chung 28.
  🔑 Ghi trước để phép đo sắp tới không thể được đọc thành *"đã gỡ được vấn đề"* dù nó ra số nào.

  ✅ **ĐÃ ỨNG NGHIỆM, đúng cả hai vế** (`TD-0213` + `TD-0214`): `n` nhóm C hoá ra trải **8 → 40**
  chứ không đồng nhất, nên **đã phải tách bảng** — đúng thứ duy nhất đoạn này nói sẽ phải sửa. Và
  kết luận **không đổi**: arm cao nhất nhóm C là `Z0-V1` với `n = 40`, vẫn kém cận 319 **tám lần**;
  arm thấp nhất `Z1` với `n = 8` kém **41 lần**. Biên rộng hơn trước khi đo, không hẹp lại.

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
- ~~Không chốt mặc định `Z0` single-entry của §2.4 — đó là đề xuất chờ chủ dự án xác nhận.~~
  ✅ **ĐÃ CHỐT 12/09/2026** — xem §2.4. Giữ dòng gạch để thấy rõ nó từng là đề xuất, không phải
  thứ DR này tự quyết từ đầu.
- **Không** chốt *"DCA bị bác bỏ"*. §2.4 điều 2 nói ngược lại: DCA vào Idea Queue với nhãn *"chưa
  từng được đo"*. Ai đọc DR này thành *"dự án đã loại DCA"* là đọc sai.
- **Không** chốt cấu hình hai tranche (§2.4 điều 4) — nó chưa được đăng ký, thuộc Idea Queue.

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
| e | ✅ Đo lại `Z3`/`Z2` sau bản vá — xong ở `TD-0213`/`TD-0214`/`TD-0215` |
| f | **Nộp DCA vào Idea Queue** (§2.4 điều 2) qua `E6 --nop-y-tuong`, `mechanism` = *"hạ giá vào trung bình ba tranche neo zone"*, kèm nguyên văn *"chưa từng được đo, không phải đã thất bại"* và điều kiện mở lại `n ≥ 319`. 🔴 Ghi `data_source` và `explore_evidence` đúng: mọi số dẫn là **EXPLORE, 0 trial** (`TD-0126` bắt buộc) |
| g | `d4_han_che` khi đóng cổng D4: thêm dòng **"D4 không phán quyết câu DCA; mặc định `Z0` theo `DR-D4-10 §2.4`, DCA nằm ở Idea Queue"** — nhãn `nguoi-khai`, không được ghi thành `do-duoc` |
| h | `tier_c.arm_ablation.arm` hiện là **`"Z3"`** (`config/tool_d_config.yaml:139`). Chú thích tại chỗ ghi giá trị này *"chỉ để chiến lược NẠP ĐƯỢC ngoài ablation; bộ chạy E3 ghi đè theo từng arm"* ⇒ nó **không** ảnh hưởng kết quả ablation, **nhưng nó CHÍNH LÀ arm chạy ở dry-run và live** — tức đúng chỗ §2.4 vừa chốt. 🔴 **Đổi sang `Z0` KHÔNG làm trong DR này**: đó là thay đổi hành vi hệ thống, phải là một việc riêng có test khoá + kiểm-có-răng, và `arm` là khoá `tier_c` nên phải rà kế toán DOF trước khi đụng |

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
| 10/09/2026 | Phiên `c3` soi §2.4, bắt ba lỗi: (a) mặc-định-Z0 nằm TRONG Nhánh 2 mà spec 4295 khoá sau "Nhánh 1 đã PASS" ⇒ đây là quyết định MỚI, không phải dẫn chiếu; (b) `18,07%` là số 48 mã / `[T0,T2]` / trước cả hai bản vá ⇒ **rút khỏi DR**; (c) lý lẽ bất đối xứng là khẩu vị rủi ro, không suy từ đo ⇒ hạ hạng. Cả ba đã kiểm lại trên đĩa và **nhận** |
| 12/09/2026 | **Chủ dự án chốt §2.4: mặc định `Z0` single-entry.** DCA **không bị bác bỏ** — vào Idea Queue với nhãn *"chưa từng được đo"*, điều kiện mở lại `n ≥ 319`. Hai đính chính đi kèm: (a) định tuyến sang D11 là **sai hướng** — dry-run chỉ cho 7,5–11 lệnh, ÍT hơn 28 đang có, và cần **7,1 năm** để đạt 319; (b) lý lẽ *"tranche 2/3 bơm thêm rủi ro"* **bị RÚT vì SAI** — `sizing.py:28,277` chặn cứng tổng rủi ro, DCA phân bổ cùng một ngân sách vào ba mức giá |
| 11/09/2026 | `TD-0215`: `Z1` là **tập con NGHIÊM NGẶT** của `Z0` (`n_giao = 6`, `chi_co_o_B = 0`) — 72,7% lệnh mất ở cổng kết nạp §6.8f vì `Z1` đổi SL ⇒ đổi cỡ lệnh. Sinh **hạng hỏng (3)** ở §2.5: *"đo được nhưng không phải thứ mình tưởng"*. §2.1 thêm một câu hỏi D4 **không** trả lời được |
| 10/09/2026 | `TD-0213` + `TD-0214`: **lần đầu cả chín arm có số trên cùng một hệ thống**. `n` nhóm C trải **8 → 40** (không đồng nhất như `DR-D4-09` gộp) ⇒ tách bảng theo arm, đúng thứ §4 ghi trước là sẽ phải sửa. `MT-21`/`MT-15` hết hiệu lực **bằng phép đo**. Kết luận không đổi, biên rộng hơn |
| 10/09/2026 | `TD-0212` đo lại ba arm SAU bản vá: `Z0-T0` 883 (−8%), `Z0-T1` 206, `Z0` 28. **§7 điều kiện 3 kiểm — KHÔNG kích hoạt**, §2.1 giữ nguyên. H-4 cả ba arm dưới 40%. Bản vá đổi số đếm của arm nhiều lệnh, không đổi arm ít lệnh — cơ chế tranh chỗ mở, §1.1 |
