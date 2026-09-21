# DR-ZA-01 — Kết cục của Zone Absorption LONG sau cổng D4: BÁC BỎ ở cấu hình này

> **Ngày chốt:** 21/09/2026 · **Người quyết:** chủ dự án (phiên mã `dd855fee`, bốn câu trả lời: đọc FAIL theo
> `DR-011` · không tiêu thêm suất cho ZA LONG · dựng máy D5→D9.5 ở mức 0 suất · *"không chờ 01/10"* hiểu là làm
> ngay mọi việc không cần suất).
> **Chi phí:** **0 trial**. Không chạm dữ liệu, không chạm lockbox, không gỡ ⏸ nào.
> Mã `DR-ZA-01` + `TD-0368`…`TD-0370` đặt chỗ bằng commit `a04e7a2` (N12 mục 7c). Commit **RIÊNG và TRƯỚC** mọi dòng mã.

> 🔴 **PHIÊN SINH Ý TƯỞNG (IDEA) VÀ PHIÊN CHỌN KHÔNG ĐỌC FILE NÀY** (`DR-009`) — nó chứa số kết quả của Tool D.

---

## 1. Sự việc — cổng D4 đã đóng, phán quyết Nhánh 1 = FAIL

Chạy thật trong Docker (`E6 --close-d4-gate`, exit 0, `d5ef262`, tag `d4-complete`): full suite **3060 passed,
0 failed**; audit sổ trial 10/16 đạt, 0 chưa đạt; `d4_cay_sach = true`; `d4_huong = LONG`.

| Đại lượng (`Z0-T1`, WFO `[T1,T2)`, rổ T1 107 mã) | Đo được | Ngưỡng | Đọc đúng |
|---|---|---|---|
| `dsr_adjusted_expectancy` | **−0,2216** | ≥ 0,10 | **chưa đủ** |
| mean `R_triển_khai` · KTC95 | **+0,0035** · [−0,1398; +0,1469] | — | không phân biệt được với 0 |
| `std_R` · `n` | 1,1117 · **231** | — | thuế nhiễu 0,2251 |
| `time_stop_ratio` | **0,43%** | dải 5–25% | **TRƯỢT** |
| `trades_per_year` | 365,25 | ≥ 150 | đạt |
| `tp_fallback_ratio` | 6,03% | ≤ 40% | đạt |
| Ba arm còn lại | `Z0` −0,112 · `Z0-T0` −0,188 · `Z3` −0,104 | — | không arm nào dương |

**Hai con số quyết định hướng đi:**
1. Để PASS ở `n = 231` cần mean ≈ **0,3251 R** — gấp **92 lần** giá trị đo được.
2. Ngay cả với **dữ liệu vô hạn** (thuế nhiễu → 0), ngưỡng kinh tế vẫn là 0,10 R ⇒ vẫn gấp **28 lần** ước lượng
   điểm. Chỉ mép trên của khoảng tin cậy (0,1469) mới vượt ngưỡng. ⇒ *"Chờ thêm dữ liệu"* **không cứu được**
   ứng viên này; và `DR-011` cũng chỉ cho gia hạn khi **thiếu mẫu** (`n < 30`), không phải khi thiếu lợi thế.

## 2. Quyết định

| # | Chốt |
|---|---|
| 1 | **Zone Absorption LONG bị BÁC BỎ Ở CẤU HÌNH NÀY** — đọc theo `DR-011` FAIL (`spec:3364-3372`): `n = 231 ≥ 30` **và** ngưỡng không đạt |
| 2 | Ghi **`retest_forbidden`** cho cấu hình này. **KHÔNG** tune lại cấu hình vừa chết, **KHÔNG** thử cấu hình thứ hai trên cùng lockbox, **KHÔNG** nới ngưỡng PASS |
| 3 | **0 suất tiêu thêm** cho ZA LONG. `TD-0258` (≤ 16 B1) và `TD-0288` (≤ 16 WFO) **không chạy** ở chu trình này ⇒ giữ **105/114** cho ứng viên sau |
| 4 | 🔴 **KHÔNG tuyên bố L3.** Khoảng tin cậy chứa cả giá trị dương: đây là *"không có bằng chứng lợi thế"*, KHÔNG phải *"có bằng chứng không có lợi thế"*. `spec:4371` — không có đường nào từ L3 về L1, nên L3 phải đắt và phải chắc |
| 5 | **Dự án KHÔNG dừng.** Ứng viên kế tiếp lấy từ Idea Queue (`DR-Q4-2026`: hạn ngạch 1, cửa chọn 01/10–31/12), chạy đủ chu trình từ D0 với **lockbox MỚI** trên dữ liệu chưa từng dùng |
| 6 | Máy D5→D9.5 **vẫn dựng tiếp, ở mức 0 suất** (khuôn `DR-D4-14`: dựng đủ, khoá khâu đo) — để ứng viên kế tiếp chạy được ngay, không phải viết mã vào đúng lúc dễ bị kết quả dẫn dắt |

**Vì sao không phân hạng L1/L2/L3 ngay ở DR này:** `spec:4290-4292` bắc cầu từ cổng D0.9 sang *"ba kết cục của
`DR-011`"* nhưng không nói ai gán mức; `DR-FAI-01` ghi thẳng *"Phân hạng do `DR-011` quyết, **chưa ai chạy**"*.
Gán mức lúc này là quyết một câu chưa có quy trình — ghi thành `MT` ở §4.

## 3. Ranh giới — cái gì KHÔNG đổi

- `N = 114`, rào DSR `3,0777`, mọi ngưỡng §10.2 **giữ nguyên**. DR này không nới một con số nào.
- `runtime_state.json` (hiện vật cổng đã ghi) **không sửa**; sổ trial **không viết lại**.
- Không chạy lại lô D4: mua lại một kết cục đã biết bằng 4–5 suất là đúng thứ `DR-011` cấm.
- Không đụng `khoa_do.D4_DO_TAM_DUNG` (đã về `True` ở `TD-0362`).

## 4. Ba mục `MT` theo quy tắc 11 — ghi khi *"chuẩn hóa và lưu"*

### 4.1 🔴 Tiêu chí H-3 gần như KHÔNG THỂ thoả với chính thiết kế này — chuyện CẤU TRÚC, không phải cỡ mẫu

Phân bố lý do thoát lệnh của `Z0-T1` (`TD-0246`, phiên `69e2254e` đo): trailing SL **75** · TP2 **54** ·
FUNDING_STOP **31** · TIME_STOP **0**. Ba cửa kia luôn đóng lệnh trước 96 giờ ⇒ **DG8 là cửa chết** trên arm này.
Muốn chạm sàn 5% phải tăng gấp ~12 lần, trong khi `max_hold_bars` bị spec chặn trong `[20, 40)` (`spec:1476-1481`)
— hạ 24 → 20 chỉ cắt 17% chân trời.

⇒ **16 suất B1 của D5 không gỡ được tiêu chí đang trượt**, dù `max_hold_bars_4h` nằm trong bảy tham số calibrate
(`DR-D5-01` §2.1, thử `20 · 32`). Đây là *"một chốt không bao giờ thoả được"* — đúng bài học cổng D3, và dự án đã
tự ghi rằng loại chốt đó **tệ hơn không có chốt** vì sớm muộn bị gỡ.

🔴 **Không nới dải sau khi đã thấy số 0,43%** — `TD-0277`/`MT-46` chốt đúng điều này, và `thresholds.py:96-101`
ghi lại nguyên văn. **Phải quyết TRƯỚC khi ứng viên kế tiếp tới cổng D0.9**, nếu không ứng viên mới sẽ trượt đúng
chỗ ZA vừa trượt vì một lý do **không liên quan tới lợi thế của nó**.

### 4.2 Phạm vi *"ba kết cục"* của `DR-011`

`DR-011` viết cho **lần chạm lockbox D9.5** (`spec:3276`, `:3345-3378`). `spec:4290-4292` bắc cầu sang cổng D0.9
nhưng không định nghĩa ai gán L1/L2/L3, cũng không nói `retest_forbidden` ở D4 có cùng nghĩa với ở D9.5 hay không.

### 4.3 Lỗ hổng xuất xứ của cổng — đo được, không suy

`runtime_state.d4_git_sha = 7c8c8f8` (cây được **CHỨNG NHẬN**) trong khi bốn bản ghi arm mang
`provenance.git_sha = 29f9f52` (cây đã **ĐO**) — **cách nhau 9 commit**, gồm `TD-0360` (đổi dung sai tỉ trọng),
`TD-0362` (lật khoá đo) và `TD-0364` (nối cổng `L-Z3`, **đổi hành vi vào lệnh**). Cơ chế:
`trial_ledger_audit.py:1298` ghi `git_info.sha` = HEAD **lúc chạy cổng**, không phải sha của lô.

⇒ Mọi số ở §1 mô tả hệ thống **TRƯỚC** khi có `L-Z3`. Chín điều trong `d4_han_che` không điều nào nói ra khoảng
lệch này, nên người đọc `runtime_state.json` sẽ tin `7c8c8f8` là cây đã đo. Phát hiện của phiên `69e2254e`.
**Cách xử:** không sửa hiện vật, không chạy lại lô — dựng **máy canh** (`TD-0369`) để lần sau cổng tự báo.

## 5. Hành vi mong đợi — ghi trước để không đọc nhầm là lỗi

- Cổng D5/D6/D7/D8/D9 dựng xong, chạy trên trạng thái THẬT ⇒ **TỪ CHỐI** (chưa có suất nào của pha đó). Đó là
  cổng làm đúng việc, không phải cổng hỏng.
- Sổ trial sau toàn bộ đợt dựng máy: vẫn **9 suất vào `N`**; chỉ tăng dòng `CTRL` *đo mô tả*.
- Dry-run tiếp tục chạy bằng cấu hình hiện hành; số của nó là **số vận hành**, không phải số hiệu năng.

## 6. Điều kiện dừng — viết TRƯỚC

1. Một test cũ phải **sửa khẳng định** mới xanh ⇒ dừng, báo.
2. Có ai đề nghị nới dải `TIME_STOP_RATIO_BAND`, hạ `DSR_ADJ_EXPECTANCY_MIN`, hay chạy lại lô D4 ⇒ dừng: cả ba đều
   là *nới ngưỡng sau khi thấy số*, và `DR-011` cấm tường minh.
3. Sổ trial tăng dù một suất vào `N` trong đợt dựng máy ⇒ dừng.
