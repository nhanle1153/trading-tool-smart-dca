# DR-D4-01 — Phạm vi và kế toán của D4 (Ablation D0.9)

> **Ngày chốt:** 08/09/2026 · **Người quyết:** chủ dự án · **Việc:** TD-0180 (Khối 16, D4)
> 🔒 **File này commit RIÊNG và TRƯỚC mọi dòng mã arm.** Cùng khuôn DR-D3-01 / DR-D35-01 /
> OQ-07. Lý do không đổi: §9c.5 và DR-015 §4 đều nói cùng một điều — **chọn phạm vi sau khi
> thấy số là uốn kết luận bằng một cửa khác**. Với D4 thì cửa đó rộng nhất, vì D4 là lần
> đầu tiên dự án tiêu ngân sách phép thử ở quy mô hai chữ số.

---

## 1. Hai câu hỏi được đặt ra, và câu trả lời

| # | Câu hỏi | Chốt |
|---|---|---|
| (a) | Chạy **Long trước** (9 trial) rồi Short sau, hay chờ dựng Short xong để chạy đủ 18 trial một lượt? | **Long trước, 9 trial.** |
| (b) | Xác nhận tiêu **B2** trên tổng `N_ĐĂNG_KÝ = 114`? | **Xác nhận**, tiêu 9 suất cho đợt này. |

Sổ trial tại thời điểm chốt: **13 sự kiện / 4 trial B0 đã tiêu + 1 dòng CTRL** (CTRL đứng
ngoài ngân sách theo MT-08). `N_ĐÃ_DÙNG = 4`, còn **110**. Sau D4-Long: `N_ĐÃ_DÙNG = 13`.

---

## 2. Vì sao Long trước — và vì sao đây KHÔNG phải một lối tắt

Có một vòng lặp thật, không phải bất tiện về lịch trình:

```
L-Z56 TỪ CHỐI chạy ablation nếu tier_a.enable_short = true
      mà Δ_R(SHORT) chưa "ok"
                    ↑                              ↓
      Δ_R(SHORT) đo bằng lượt khớp tranche của lệnh SHORT
                    ↑                              ↓
      chưa có lệnh Short nào — ZoneAbsorptionMinimal LONG-only (TD-0114)
```

Vòng lặp này **không phá được bằng cách nới `L-Z56`**. Nới nó nghĩa là cho phép chạy arm
Short trên một thước chưa từng kiểm cho hướng Short — đúng trạng thái mà DR-015 §1 gọi là
*"tệ nhất có thể"*. Chốt sinh ra để chặn điều đó thì không được gỡ vì nó đang chặn.

Ba đường phá vòng lặp, và lý do chọn đường thứ ba:

| Đường | Đánh giá |
|---|---|
| Nới `L-Z56` cho hướng Short | ❌ **Loại.** Xem trên. |
| Chạy một "D3.5 thu nhỏ" cho Short trước D4 | 🟡 Đúng về nguyên tắc nhưng **không thực hiện được hôm nay**: Bước 1 cần lượt khớp tranche THẬT của lệnh Short, mà nguồn duy nhất cho tới giờ (TD-0115, 91 lượt trên CALIB) sinh từ backtest LONG. Đo Short cần trước hết **có mã Short**, tức đúng thứ đang bị chặn. |
| **Chạy Long trước, Short hoãn có điều kiện** | ✅ **Chọn.** Spec §3.3d cho phép đúng đường này bằng chữ: *"Nếu chỉ có thời gian/dữ liệu chạy một hướng trước, làm Long trước (đối xứng tự nhiên hơn với hầu hết chỉ báo dùng), Short chạy sau khi có DG7 và ngưỡng riêng đã calibrate."* |

🔴 **Điều Long-first KHÔNG cấp phép cho ai:** kết luận của D4 đợt này **chỉ có giá trị cho
hướng LONG**. Spec §10.1 nói thẳng *"không giả định kết quả Long tự động áp dụng cho Short"*,
và §3.3d liệt kê ba bất đối xứng cụ thể (funding, biến động nền, short squeeze). Cụ thể:
DG6 điều kiện A (ATR ratio ngưỡng 1.8) **phải calibrate riêng cho Short** (§3.3d dòng 1159).

⇒ Cổng D4 phải ghi phạm vi này ra bằng chữ, nhãn `nguoi-khai`, cùng cách `d3_5_han_che` đã
làm. Một kết luận "Z3 thắng Z0" mà không kèm chữ "cho LONG" là một câu sẽ bị đọc rộng ra
sau sáu tháng, khi không ai còn nhớ đợt này chỉ chạy một hướng.

### 2b. Ba điều kiện mở lại hướng Short — viết TRƯỚC, không viết sau

Cùng khuôn "ba điều kiện mở lại" của OQ-07 (DR-Q3-2026). Viết trước để việc bật Short không
thể được biện minh bằng một lập luận dựng sau khi nhìn kết quả Long.

Hướng Short chỉ được bật khi **cả ba** đúng:

1. **DG7 đã tồn tại và có ngưỡng riêng đã calibrate** (§3.3d dòng 1162 — chữ của spec).
2. **Δ_R(SHORT) đo được, ở trạng thái `ok`, và đã commit** vào
   `docs/du-lieu-do/dr015-buoc1-delta-r.json` — tức `kiem_cong_d35()` tự đi qua, không cần
   ai sửa gì. Nếu phải sửa `L-Z56` để nó đi qua thì điều kiện này **chưa** đạt.
3. **Ngân sách còn ≥ 9 suất** sau khi trừ mọi thứ đã tiêu tính tới lúc đó.

Không đạt đủ ba → Short vẫn hoãn, và **`tier_a.enable_short` giữ `false`**. `L-Z56` là máy
thi hành điều kiện 2; điều kiện 1 và 3 chưa có máy canh — ghi ra đây để không ai coi việc
`L-Z56` xanh là đủ.

---

## 3. Chín cấu hình, và trạng thái mã nguồn THẬT của từng cái

🔴 **Phát hiện quan trọng nhất khi soạn quyết định này: D4 phần lớn là DỰNG arm, không phải
CHẠY arm.** Đối chiếu bảng §10.1/§10.1b với mã nguồn ngày 08/09/2026:

| # | Cấu hình | §  | Trạng thái mã |
|---|---|---|---|
| Z0 | Entry đơn tại p1, xác nhận entry §3.3b, SL neo zone, full size | 10.1 | 🟡 module `entry_confirmation.py` **có**, chưa nối vào tín hiệu vào lệnh |
| Z1 | Entry đơn, SL = 2.2×ATR cố định | 10.1 | 🔴 **chưa có** |
| Z2 | 3 tranche neo zone, không DG5, không `mult_zss` | 10.1 | 🔴 **chưa có công tắc** |
| Z3 | 3 tranche đầy đủ DG1–DG5 + `mult_zss`, KHÔNG DG6 | 10.1 | 🔴 **DG1–DG5 không có một dòng nào** |
| Z3b | Như Z3, CỘNG DG6 (Early Invalidation §4.1) | 10.1 | 🔴 **chưa có** |
| Z0-T0 | Zone + xác nhận entry, **không bộ lọc trend nào** | 10.1b | 🟡 `trend_context.py` **có**, chưa nối |
| Z0-T1 | Chỉ giữ 4H (§2.2), bỏ tầng 1D | 10.1b | 🟡 như trên, chưa có công tắc theo tầng |
| Z0-V1 | Như Z0, **tắt** điều kiện (c) volume ở §3.3b | 10.1b | 🔴 **chưa có công tắc** |
| Z0-S1 | Như Z0, notional **cố định** thay vì rủi ro cố định | 10.1b | 🔴 **chưa có** |

`Z0-T2` **không nằm trong bảng vì nó CHÍNH LÀ Z0** — spec ghi rõ *"Mốc so sánh — không phải
arm mới, không tốn trial thêm"*. Đếm nhầm nó thành arm thứ 10 là tiêu thừa 1 suất.

Chính docstring của `ZoneAbsorptionMinimal` đã tự khai điều này: *"LONG only, chưa nối Phần
2/§3.3b vào tín hiệu vào lệnh, chưa có DG1-5"*. Không ai giấu gì; chỉ là tên khối *"D4 —
Ablation"* gợi ý sai rằng việc còn lại là bấm nút chạy.

⇒ **Hệ quả lên thứ tự việc:** TD-0181…TD-0184 (dựng DG1–DG5, nối Phần 2 + §3.3b, dựng công
tắc arm, dựng bộ chạy ablation) phải xong **trước khi** đặt chỗ bất kỳ trial nào.

---

## 4. Kế toán trial — chốt chi tiết để không cãi lại sau

**9 trial, dòng ngân sách `B2`, một trial cho mỗi cấu hình ở hướng LONG.**

| Điều | Chốt |
|---|---|
| Đơn vị tiêu | **1 trial / 1 cấu hình / 1 hướng.** 9 cấu hình × 1 hướng = 9. |
| Dòng ngân sách | `B2` (§10.1b: *"B2 = 18 (9 cấu hình × 2 hướng)"*). Đợt này tiêu **nửa** của B2. |
| Nửa còn lại | **Không tự động thuộc về Short.** Nếu §2b không đạt, 9 suất đó ở lại quỹ chung, không "để dành". |
| Thời điểm ĐẶT CHỖ | `RESERVE` cho **cả 9** trước khi chạy arm đầu tiên. |
| Thời điểm NIÊM PHONG | `SEAL` do **bộ chạy tự gọi** ngay khi chỉ số đầu tiên của arm tồn tại trong bộ nhớ — trước cả khi in ra (DR-014). |
| Hoàn lại | Chỉ qua `REFUND` theo DR-014, trần **3 lần/giả thuyết**. Không có đường nào khác. |
| `Z0-T2` | **0 trial** — nó là Z0. |
| Điểm kiểm soát | Dòng `CTRL`, **0 trial**, đứng ngoài N (MT-08). Chạy sau mỗi lần một tham số đổi trạng thái. |

### 4b. Vì sao đặt chỗ CẢ 9 một lượt, không đặt lần lượt

Chủ dự án được đề nghị phương án "chạy từng arm một, dừng được giữa chừng" và **không chọn**.
Ghi lại lý do để quyết định này cãi lại được:

Dừng giữa chừng sau khi đã thấy kết quả arm trước là **một dạng chọn-sau-khi-nhìn-số**. Nó
không sai về đạo đức, nhưng nó làm `N` — mẫu số của rào DSR ở §10.2 — trở thành một đại
lượng **phụ thuộc kết quả**, tức chính thứ DSR sinh ra để hiệu chỉnh. Đặt chỗ cả 9 trước
khi chạy giữ `N` là một hằng số biết trước.

Đánh đổi được chấp nhận: nếu arm đầu cho tín hiệu rõ ràng thì vẫn phải chạy đủ 9. Chi phí là
thời gian máy, không phải tính đúng đắn.

---

## 5. Điều quyết định này KHÔNG chốt

Ghi ra để không ai đọc rộng file này, cùng lý do §2 ghi phạm vi của kết luận Long:

- **Không chốt ngưỡng nào của cổng D0.9 (§10.2).** Hai nhánh + `L-Z57` là việc của TD-0185.
- **Không chốt thứ tự chạy 9 arm.** Thứ tự không ảnh hưởng kế toán (đã đặt chỗ cả lô) và
  không ảnh hưởng kết quả (mỗi arm độc lập). Để bộ chạy quyết.
- **Không chốt cách đọc kết quả.** Bảng "Đọc kết quả" của §10.1/§10.1b đã có sẵn trong spec;
  nhắc lại ở đây sẽ tạo nguồn sự thật thứ hai (bài học MT-03).
- **Không cấp phép chạm dữ liệu LOCKBOX.** D4 chạy trên CALIB/WFO theo DR-011; lockbox vẫn
  đóng tới sau D9 (H17).

---

## 6. Hai việc đi kèm, chốt cùng lượt

**(a) Hai quy ước phân vị cùng tồn tại trong repo — GIỮ NGUYÊN, không mở niêm phong.**
`_p90()` của TD-0161 nội suy tuyến tính; vòng đo chốt của TD-0162 dùng chỉ số cắt cụt
`xs[int(q*(n-1))]`. Thống nhất về một hàm sẽ đổi **4 ô phân vị tóm tắt** nằm trong
`docs/du-lieu-do/dr015-buoc2-ty-le-khong-khop.json` — một artifact cổng D3.5 **đã niêm
phong**. Chủ dự án chốt: **không đụng artifact**, chỉ ghi rõ hai quy ước (đã làm ở `d1f73f2`).

Lý do: sửa một bằng chứng đã niêm phong **sau khi cổng đóng** là đúng thứ DR-015 §1 tồn tại
để chặn, và nó tạo tiền lệ "artifact sửa được". Nợ kỹ thuật còn lại — hai quy ước cùng sống —
được chấp nhận có ý thức, và **đã có văn bản** nên không ai đọc nhầm thành lệch dữ liệu.
🔴 Không đại lượng nào chảy vào §4 bị ảnh hưởng: `p_nf`, Δ_R và mọi thứ §4 dùng đều không
phải phân vị nội suy.

**(b) Cache dump 599 MB — XOÁ.** `user_data/data/dr015cache/` (45 dump `aggTrades`, do phiên
`-d8` tạo để container đọc được). Đã gitignore (`.gitignore:2` — `user_data/data/**`), không
nằm trong repo, **tái tạo được** bằng `tai_dump_agg_trades()` từ `data.binance.vision`. Chủ
dự án chốt xoá. Đánh đổi: nếu D9 cần đo lại Bước 2 thì phải tải lại (thời gian mạng, không
mất dữ liệu).

---

## 7. Bảng thi hành — cái gì có máy canh, cái gì chỉ là chữ

| Điều đã chốt | Có máy canh không |
|---|---|
| Δ_R phải có và đã commit trước khi chạy arm | ✅ `L-Z56` (`kiem_cong_d35()`), nối vào E3 |
| Bật Short thì phải có Δ_R(SHORT) | ✅ `L-Z56` qua `_huong_can_co()`, đọc `tier_a.enable_short` |
| Không tiêu quá ngân sách | ✅ `TrialLedger.available()` + DR-014 |
| CTRL không tính vào N | ✅ MT-08, `registry.py` |
| Chạy đúng 9 arm, không 10 | ❌ **chưa** — sẽ do TD-0184 dựng |
| Kết luận D4 chỉ áp cho LONG | ❌ **chỉ là chữ** — phải ghi vào `d4_han_che` khi đóng cổng |
| Ba điều kiện mở lại Short (§2b) | 🟡 điều kiện 2 có `L-Z56`; điều kiện 1 và 3 chỉ là chữ |

---

## 8. Lịch sử

- **08/09/2026** — tạo, chốt (a) Long trước 9 trial, (b) xác nhận tiêu B2, cùng hai việc đi
  kèm ở §6. Chủ dự án quyết qua bốn câu hỏi trực tiếp.
