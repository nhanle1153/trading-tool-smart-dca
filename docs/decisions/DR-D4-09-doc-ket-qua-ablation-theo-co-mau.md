# DR-D4-09 — Đọc kết quả ablation theo CỠ MẪU: phép so paired, và tách INCONCLUSIVE khỏi FAIL

> Quyết định của chủ dự án, 09/09/2026 (gói 4 việc, làm tuần tự — việc 2/4). Commit **RIÊNG và
> TRƯỚC** mọi dòng mã thi hành. Đã báo `-76`/`-46` trước khi mở file (N12 mục 6).
> Bằng chứng: `docs/du-lieu-do/td0193-lenh-nam-explore.json` (88 mã EXPLORE, 99,4 mã-năm, 0 trial).
> 🔴 **Viết TRƯỚC khi tồn tại một con số expectancy nào của Tool D** — spec dòng 3956-3958 đòi đúng
> thế, và đây là lúc DUY NHẤT sửa cách đọc gate mà không ai nghi *"sửa cho dễ qua"*.

## 1. Vấn đề — ba thứ ĐO ĐƯỢC, không phải ý kiến

### 1.1 Cỡ mẫu lệch tới hàng chục lần giữa các arm

Đo trên EXPLORE sau khi §3.3b được nối (TD-0193) và `mult_regime` được vá (TD-0198):

| Nhóm | Arm | Tín hiệu | Lệnh/năm (quy đổi pool 102) | **n trên WFO 0,63 năm** |
|---|---|---|---|---|
| A | `Z0-T0` (tắt hết Phần 2) | 1.977 | 1.276,5 | **~804** |
| B | `Z0-T1` (chỉ 4H) | 478 | 333,5 | **~210** |
| C | `Z0`,`Z1`,`Z2`,`Z3`,`Z3b`,`Z0-V1`,`Z0-S1` | 96 | 63,6 | **~40** |

⇒ chênh lệch cỡ mẫu giữa nhóm A và nhóm C là **~20×**.

Ablation D0.9 chạy trên **WFO [T1…T2] = 0,63 năm** (spec dòng 3287, bảng phân vùng) — không phải
toàn bộ [T0,T2]. Sàn §10.2 Nhánh 1 là **150 lệnh/năm**: nhóm C hụt, nhóm A/B vượt.

### 1.2 "Thuế nhiễu" — công thức, và vì sao nó áp đảo chính ngưỡng nó bảo vệ

Công thức trong code (`gates/dsr.py:52-69`, `gates/thresholds.py:24`):

```
DSR_adj(arm) = mean_R − h · std_R / √n        với h = √(2·ln N) = √(2·ln 114) = 3,0777
GATE Nhánh 1:  DSR_adj ≥ 0,10 R
```

Đặt **thuế nhiễu** ≡ `h · std_R / √n` — phần bị trừ đi vì *"ta chỉ tình cờ chọn được cái tốt nhất
trong N phép thử"*. Ngưỡng **hiệu dụng** của Nhánh 1 vì thế là `0,10 + thuế nhiễu`, không phải 0,10:

| n | thuế nhiễu (std=1,25) | **mean_R cần để PASS** |
|---|---|---|
| 40 (nhóm C) | 0,608 | **0,708 R** |
| 80 (nếu Long+Short gộp) | 0,430 | 0,530 R |
| 95 (nếu đúng sàn 150 lệnh/năm) | 0,395 | 0,495 R |
| ~804 (nhóm A) | 0,136 | 0,236 R |

⚠️ `std_R = 1,25` là **GIẢ ĐỊNH chưa đo** (đo `std_R` thật cần chạm PnL — xem §5). Nhưng kết luận
cho nhóm C **không phụ thuộc giả định đó**: ở n=40, thuế nhiễu = `0,487 × std_R`, và không `std_R`
thực tế nào của một hệ thống giao dịch đưa nó xuống dưới ~0,25.

🔑 **Sàn 150 lệnh/năm và rào DSR là hai tiêu chí trong CÙNG Nhánh 1 nhưng không nhất quán với
nhau:** đạt đúng sàn vẫn cho ngưỡng hiệu dụng ~0,50 R. Sàn được chọn như *"đủ mẫu tối thiểu"*,
nhưng công thức DSR đòi cỡ mẫu lớn hơn một bậc.

### 1.3 Nhánh 2 hiện so hai DSR-adj ĐỘC LẬP — thuế nhiễu cộng theo √2

§10.2 Nhánh 2: *"Tốt nhất trong {Z3, Z3b} vượt Z0 ≥ 20% DSR-adjusted expectancy"*. Hai vế là hai số
DSR-adj tính riêng, nên sai số của HIỆU là:

```
độc lập :  thuế(d) = h · √(std_A² + std_B²) / √n   = h · std · √2 / √n
paired  :  thuế(d) = h · std(d) / √n ,  std(d) = std · √(2 − 2ρ)
```

với `ρ` = tương quan giữa R của hai arm trên **cùng một lệnh**. Bảng (std=1,25):

| n | độc lập | ρ=0,5 | ρ=0,8 | ρ=0,9 | ρ=0,95 |
|---|---|---|---|---|---|
| **40** (nhóm C) | 0,860 | 0,608 | 0,385 | **0,272** | 0,192 |
| **210** (nhóm B) | 0,376 | 0,266 | 0,168 | 0,119 | 0,084 |
| **804** (nhóm A) | 0,192 | 0,136 | 0,086 | 0,061 | 0,043 |

Mức cần phát hiện của *"vượt ≥ 20%"* là `0,20 × e_baseline` — với `e = 0,10 R` thì chỉ **0,020 R**.

### 1.4 Hệ quả: gate hiện tại xếp hạng theo SỐ LỆNH, không theo EDGE

`DSR_adj` trừ một lượng tỉ lệ `1/√n`. Với chênh lệch n hàng chục lần giữa nhóm A và nhóm C, **arm
nhiều lệnh gần như chắc chắn đứng đầu bảng bất kể edge thật** — và arm nhiều lệnh nhất chính là
`Z0-T0`, arm **tắt hết bộ lọc trend**, thứ §10.1b cảnh báo *"nguy cơ thoái hoá thành
mean-reversion (DR-005)"*. Đây là thiên lệch **cấu trúc**, không phải nhiễu thống kê, và **không
chữa được bằng thêm dữ liệu** (thêm dữ liệu nâng cả hai vế, giữ nguyên tỉ lệ).

## 2. Quyết định

### 2.1 Nhánh 2 dùng phép so PAIRED trên tập GIAO

Với hai arm A (baseline) và B chạy trên cùng dữ liệu, lấy tập lệnh **giao** theo `(pair, giờ mở)`;
với mỗi lệnh `i` trong tập giao: `d_i = R_B,i − R_A,i` (R theo DR-013 = `pnl_abs / planned_risk_usdt`).

```
B vượt A ≥ 20%  ⟺  mean(d) − h · std(d) / √n_giao  ≥  0,20 × mean(R_A)
```

**Bắt buộc kèm:** `n_A`, `n_B`, `n_giao`, và `ρ` đo được. `n_giao` là mẫu số DUY NHẤT được dùng —
không phải `n_A` hay `n_B`.

🔴 **Chỉ áp cho arm THẬT SỰ cùng tập entry.** Đo được (`td0193-lenh-nam-explore.json`, khoá
`so_tap_lenh`): `Z0`/`Z1`/`Z2`/`Z3`/`Z3b`/`Z0-S1` rẽ nhánh **SAU** khi đã vào lệnh (DG5 gác tranche
2/3; DG6 đóng sớm; `notional` đổi cỡ; SL đổi mức) — không cái nào đụng điều kiện VÀO LỆNH. Hai
nhóm **KHÔNG** cùng tập, đã biết trước và phải so KHÔNG paired: `Z0-V1` (tắt điều kiện (c) ⇒ điều
kiện lỏng hơn ⇒ `Z0 ⊂ Z0-V1`) và `Z0-T0`/`Z0-T1` (khác bộ lọc trend). *(Câu hỏi do `-46` nêu; đã
đo thay vì giữ tiền đề tiện lợi.)*

### 2.2 BA kết cục, không phải hai — tách INCONCLUSIVE khỏi FAIL

§10.2 hiện gộp mọi thứ không PASS thành *"KHÔNG VÀO LIVE"*. Từ nay mỗi tiêu chí phải phân loại:

| Kết cục | Điều kiện | Nghĩa | Hành động |
|---|---|---|---|
| **PASS** | đạt ngưỡng | — | đi tiếp |
| **INCONCLUSIVE** | `thuế nhiễu > ngưỡng của chính tiêu chí đó` | **không đo được** — phép đo không có khả năng phân biệt "đạt" với "may mắn" | thêm mẫu / đổi thiết kế; **KHÔNG** phải bằng chứng chống |
| **FAIL** | thuế nhiễu ≤ ngưỡng **và** vẫn không đạt | đo được, và không đạt | xử theo DR-011 |

🔴 **Vì sao đây là điều quan trọng nhất của DR này.** Nếu Nhánh 2 trả *"Z3 không vượt Z0 ≥ 20%"* và
bị đọc thành FAIL, hệ quả là **bỏ DCA vĩnh viễn** — dựa trên một phép đo mà §1.3 vừa chứng minh là
**không có khả năng phát hiện** mức hiệu ứng đang hỏi. Đó là cách một kết luận sai đi vào dự án qua
cửa "gate đã chạy đúng quy trình".

### 2.3 Báo cáo BẮT BUỘC cho MỌI arm — ba con số, không phải một

`n` · `thuế nhiễu` (`h·std/√n`) · `DSR_adj`. Thiếu một ⇒ bản ghi kết quả không hợp lệ. Lý do: một
`DSR_adj` đứng một mình **không nói được** nó là *"edge yếu"* hay *"chưa đủ mẫu"* — hai thứ dẫn tới
hai hành động trái ngược. Cùng tinh thần `L-Z15` in con số ngay cả khi ĐẠT (TD-0190).

### 2.4 CẤM xếp hạng trực tiếp bằng DSR_adj giữa hai arm lệch cỡ mẫu

Khi `max(n)/min(n) ≥ 2`, không được dùng `DSR_adj` để nói arm nào *"tốt hơn"* — phải so bằng
`mean_R` thô kèm khoảng tin cậy của từng arm, và ghi rõ chênh lệch `n`. `DSR_adj` chỉ dùng cho câu
hỏi TUYỆT ĐỐI của Nhánh 1 (*"arm này có đủ tốt không"*), không cho câu hỏi TƯƠNG ĐỐI.

## 3. Vì sao đây là làm CHẶT hơn, không phải nới

Ba thay đổi, không cái nào hạ một ngưỡng nào:

1. **§2.1 paired** — giảm sai số của phép so, tức làm nó **nhạy hơn**; ngưỡng *"≥ 20%"* giữ nguyên
   con số. Và nó thêm một ràng buộc mới (phải chạy trên tập giao, phải khai `n_giao`).
2. **§2.2 ba kết cục** — thêm một cửa mà trước đây không có. Không kết cục nào từ FAIL chuyển sang
   PASS; chỉ có kết cục từ *"FAIL ngầm"* chuyển sang *"nói thẳng là không đo được"*.
3. **§2.3/§2.4** — thêm nghĩa vụ báo cáo và một điều CẤM. Cả hai chỉ trừ đi quyền của người đọc kết
   quả, không thêm.

## 4. Giới hạn TỰ KHAI — paired GIÚP nhưng KHÔNG CỨU

Với `ρ = 0,9`, `std = 1,25`, mức cần phát hiện `0,20 × e_A`:

| `e_A` (expectancy baseline) | mức cần phát hiện | **n_giao cần** |
|---|---|---|
| 0,10 R | 0,020 R | **~7.400** |
| 0,20 R | 0,040 R | ~1.850 |
| 0,30 R | 0,060 R | ~820 |
| 0,50 R | 0,100 R | ~300 |

Nhóm C có `n ≈ 40`. ⇒ **Kết cục nhiều khả năng nhất của Nhánh 2 là INCONCLUSIVE**, và DR này
không đổi điều đó — nó chỉ đảm bảo kết cục ấy được **gọi đúng tên**. Ghi ra đây để không ai đọc
DR này thành *"đã sửa xong vấn đề power"*.

## 5. Điều DR này KHÔNG chốt

- **Không** chốt `std_R` — con số 1,25 dùng xuyên suốt là GIẢ ĐỊNH minh hoạ. Đo `std_R` thật cần
  chạm PnL; trên EXPLORE thì vướng `DR-D0PRE-05` §4, trên pool thì vướng DR-014 (tốn trial) và
  MT-19. **Cần một quyết định riêng**, không gộp vào đây.
- **Không** chốt chạy bao nhiêu arm (việc 3/4 của gói), không chốt bật Short, không đụng
  `DR-D4-01` (Long-only, 9 trial) — chỉ đổi **cách đọc** kết quả.
- **Không** đổi ngưỡng nào: `0,10 R`, `≥ 20%`, `150 lệnh/năm`, `N = 114` giữ nguyên.

## 6. Kế toán DOF

`dof_goc` 28 · `|tier_b|` 12 · **N = 114** · rào DSR **3,0777** — không đổi. **0 trial**: DR này
không đánh giá cấu hình nào, chỉ định nghĩa cách đọc.

## 7. Điều kiện mở lại — viết TRƯỚC, khuôn OQ-07

1. `std_R` đo được (qua một quyết định riêng ở §5) và **lệch > 30%** so với 1,25 ⇒ tính lại toàn bộ
   bảng §1.2/§1.3/§4; kết luận định tính (*"nhóm C không thể PASS"*) chỉ đổi nếu `std_R < 0,5`.
2. `ρ` đo được **< 0,5** ⇒ lợi ích của paired nhỏ hơn bảng §1.3, phải ghi lại vào `d4_han_che`.
3. `n_giao` đo được **khác `n_A`/`n_B` quá 5%** ⇒ giả định "cùng tập entry" của §2.1 sai với nhóm
   đang xét, phải chuyển nhóm đó sang phép so KHÔNG paired.

❌ **KHÔNG** phải điều kiện mở lại: kết quả D4 không như mong đợi. Đó là đổi thước sau khi thấy số.

## 8. Việc thi hành

| Chặng | Việc |
|---|---|
| a | `gates/` — hàm `phan_loai_ket_cuc()` trả PASS/INCONCLUSIVE/FAIL theo §2.2; `so_paired()` theo §2.1 |
| b | Bản ghi kết quả ablation (TD-0184) mang `n`, `thue_nhieu`, `DSR_adj` cho mọi arm (§2.3) + `n_giao`/`rho` cho mọi cặp so |
| c | `L-Z57` mở rộng: bộ kết quả giả lập có `thuế nhiễu > ngưỡng` mà gate trả FAIL (thay vì INCONCLUSIVE) ⇒ test ĐỎ |
| d | ✅ Bảng §1.1 đã điền đủ ba nhóm (đo lại sau TD-0198, `sau198`) |

## 9. Lịch sử

| Ngày | Sự kiện |
|---|---|
| 09/09/2026 | TD-0193 đo được 63,6 lệnh/năm < sàn 150; phân tích power cho thấy vấn đề lớn hơn sàn |
| 09/09/2026 | `-46` nêu hai câu (tuổi trend? hướng lệch quy đổi?) — đo, cả hai lật giả thuyết |
| 09/09/2026 | `-46` nêu tiếp: "cùng tập tín hiệu" là tiền đề cần kiểm ⇒ §2.1 đo thay vì giả định |
| 09/09/2026 | Chủ dự án chốt gói 4 việc, làm tuần tự — DR này là việc 2/4 |
