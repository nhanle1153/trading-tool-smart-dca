# DR-D4-04 — Chiến lược SẢN XUẤT `ZoneAbsorption`: phạm vi BẮT BUỘC gồm tầng định cỡ (§6.8f) và chốt lời (PHẦN 5)

> **Ngày chốt:** 08/09/2026 · **Người quyết:** chủ dự án · **Việc:** MT-16, MT-17 (back-end-note mục 7)
> 🔒 **Commit RIÊNG và TRƯỚC mọi dòng mã.** Cùng khuôn DR-D4-01/02/03. Quyết định này
> **viết lại phạm vi D4**, nên nó phải đứng trước mọi dòng code của các việc nó sinh ra.

---

## 1. Vì sao có quyết định này — và vì sao bản trình đầu SAI

Bản trình đầu (08/09, chiều) đặt hai câu cạnh nhau như hai lựa chọn ngang hàng: *(a) sửa
`ZoneAbsorptionMinimal` hay dựng chiến lược riêng; (b) có đưa tầng định cỡ §6.8e vào cùng
phạm vi không* — kèm chữ *"nghiêng: phải"* và một **cảnh báo chi phí** đặt cạnh làm đối
trọng: *"dựng tầng định cỡ ⇒ phải đo lại Δ_R, mở lại artifact D3.5"*.

Chủ dự án bác cách đóng khung đó: *"Position sizing và tỉ lệ R:R cực kì quan trọng trong
quản trị rủi ro và chiến lược"*. Kiểm lại thì họ đúng ở **ba** chỗ, không phải một:

**(i) Định cỡ không phải lựa chọn.** §10.2 phán quyết bằng expectancy tính theo **R**
(ngưỡng `0,10 R`, DR-D0PRE-03). Không định cỡ theo rủi ro cố định (D0.1) thì *"1 R"* trôi
theo từng lệnh — con số phán quyết **không có đơn vị**. Và hiện `stake_amount: 10` là cỡ
thật của mọi lệnh (MT-16), tức rủi ro/lệnh = `40 × R_eff` = 0,36–1,2 USDT **biến thiên**,
trong khi thiết kế là `rho × E_D` = 1,875 USDT **cố định**.

**(ii) Cảnh báo chi phí Δ_R là GIẢ.** Đo lại trên chính artifact D3.5 (24 lệnh đủ ba tranche):

```
Δ_R với cỡ lệnh ×1, ×3, ×20        :  giống hệt tới chữ số thứ 16   (bất biến tuyệt đối)
Δ_R tỉ trọng ĐÃ CHẠY   ¼ ¼ ½        :  0,132585
Δ_R tỉ trọng THIẾT KẾ  ⅓ ⅓ ⅓        :  0,132423                       (lệch 0,12%)
```

Lý do: `lệch_R = qty × Δgiá / planned_risk`, tử số và mẫu số cùng tỉ lệ với cỡ lệnh.
**Artifact D3.5 không cần mở lại.** Đối trọng đó không tồn tại — nó là một lý do tự dựng
để do dự trước một việc bắt buộc. *(0,1326 ≠ 0,1612 niêm phong chỉ vì lọc 24/35 lệnh; không
phải Δ_R "sửa lại".)*

**(iii) Vế "reward" cũng không có code.** `ZoneAbsorptionMinimal` đặt `minimal_roi = {"0":
10}` (tắt), `src/tool_d/` không có module TP nào, `TASKS.md` không có dòng nào về TP. Mọi
lệnh chỉ thoát bằng SL / DG6 / DG7 / DG8 (hết giờ). Trong khi chính spec — câu hỏi mở #3 và
#11 (dòng 5045, 5052) — nói D0.9 sẽ *"trả lời bằng số"* về TP và về xung đột DG8/TP2: **spec
mặc định D0.9 chạy CÓ TP.** Khối 16 khi mở đã đối chiếu *chín arm* với code, nhưng không đối
chiếu *chiến lược* với danh mục phần của spec — đó là sót của phiên mở khối.

Về chữ "R:R": spec §5.1 **cố ý không dùng R:R cố định** — risk = `rho × E_D` cố định (D0.1),
reward = khoảng cách tới zone đối diện. R:R ở Tool D là **một đầu ra đo được trên từng lệnh**,
và chỉ đo được khi **cả hai tầng** cùng tồn tại. Hiện không tầng nào tồn tại.

---

## 2. Quyết định

### 2.1 Dựng `user_data/strategies/ZoneAbsorption.py` — chiến lược SẢN XUẤT, file MỚI

`ZoneAbsorptionMinimal.py` **giữ nguyên, không sửa một dòng** — nó là fixture của `L-Z49`
(CRITICAL) với bằng chứng backtest thật, và docstring của chính nó khai việc nối Phần 2/§3.3b
là *"ngoài phạm vi hẹp của L-Z49"*. Sửa nó là đổi đối tượng mà một bằng chứng đã niêm phong
đang nói về. `entrypoints/` vẫn đúng 8 file — không đụng `L-Z36`. `user_data/strategies/`
đã có 3 file; thêm 1 không phá kiến trúc nào. **`ZoneAbsorption` là chiến lược DUY NHẤT D4
chạy;** cổng D4 phải ghi tên file này vào evidence.

### 2.2 Phạm vi BẮT BUỘC — bảy tầng, không tầng nào là tuỳ chọn

| # | Tầng | Spec | Hiện trạng | Việc |
|---|---|---|---|---|
| 1 | **Định cỡ theo rủi ro + 6 hệ số** | §6.8f B1, §6.2 | 0 dòng | TD-0187 |
| 2 | **Kết nạp danh mục** Σ risk / Σ margin | §6.8f B2 | 0 dòng (`max_open_trades=100` placeholder) | TD-0188 |
| 3 | **Tỉ trọng tranche ⅓⅓⅓ thật sự thi hành** | §3.1 | sai (¼¼½) | trong TD-0187 |
| 4 | **Chốt lời TP1 / TP2 / fallback** | PHẦN 5 | 0 dòng | TD-0189 |
| 5 | Nối Phần 2 + §3.3b vào tín hiệu | §2, §3.3b | module có, chưa nối | TD-0182 (đổi đích sang `ZoneAbsorption`) |
| 6 | Nối DG1–DG5 vào tranche 2/3 | §4 | hàm thuần có (TD-0181), chưa nối | TD-0187 |
| 7 | Công tắc arm | §10.1/10.1b | phần lớn có (TD-0182/0183) | nối trong 5–6 |

### 2.3 Thứ tự: ĐỊNH CỠ TRƯỚC — vì mọi thứ khác là hệ quả của nó

Ba trong bốn triệu chứng của MT-16 (tỉ trọng ¼¼½, `Z0-S1` vô nghĩa, `r_eff_plan` lệch 10,6%
→ DG7 muộn) **đều là bug của tầng định cỡ**, không phải ba bug riêng. Dựng tầng đó đúng là
sửa cả ba cùng lúc. Dựng TP hay nối tín hiệu trước rồi mới định cỡ là dựng trên một nền sẽ
đổi.

---

## 3. Đặc tả tầng định cỡ — chép ĐÚNG §6.8f, không diễn giải thêm

```
BƯỚC 1 — cỡ lệnh ứng viên (rủi ro cố định, D0.1):
   rho_eff = rho × mult_regime × mult_zss × mult_corr × mult_dd × mult_edge × mult_deploy
   N_full  = (rho_eff × E_D) / R_eff
   margin  = N_full / L_exchange
   stake tranche i = N_full × w_tranche[i]          ← ⅓ ⅓ ⅓, tier_frozen

BƯỚC 2 — kết nạp. Chỉ mở nếu SAU KHI mở vẫn thoả CẢ HAI:
   (a) Σ rủi ro (mọi vị thế, KẾ HOẠCH đầy đủ, tương quan = 1) ≤ daily_loss_budget_pct × E_D
   (b) Σ margin (mọi vị thế, KẾ HOẠCH đầy đủ)                 ≤ 0.85 × E_D
```

🔴 **RÀNG BUỘC BAO TRÙM (§6.2):** mọi `mult_*` **≤ 1.0**. `rho` là TRẦN. Tín hiệu tốt không
được cược to hơn — chỉ được HẠ ở tín hiệu xấu. Phải có test khoá: không đường nào trong code
sinh ra `mult > 1.0`.

**Sáu hệ số trong BACKTEST (D4) — phải TƯỜNG MINH, không được "vắng mặt lặng lẽ":**

| Hệ số | Trong backtest | Căn cứ |
|---|---|---|
| `mult_regime` | tính từ ADX(14,1D) | §6.2 hệ số 1, `tier_frozen.mult_regime` |
| `mult_zss` | `clip(ZSS, 0.5, 1.0)` | §6.2 hệ số 2 |
| `mult_corr` | tính từ corr_pool các vị thế mở; không vị thế → 1.0 | §6.2 hệ số 3 |
| `mult_dd` | tính từ equity Tool D; **0.0 = HALT, không phải size 0** | §6.2 hệ số 4, §12c.5 |
| `mult_edge` | **= 1.0** — spec dòng 1774: *"Trước 50 lệnh live: mult_edge = 1.0"* | §6.2 hệ số 5 |
| `mult_deploy` | tính từ deployed_ratio | §6.2 hệ số 6 |

Mỗi hệ số phải xuất hiện trong bản ghi Decision Log của lệnh (§8) với giá trị thật — để ai
đọc lại biết `mult_edge = 1.0` là *"chưa đủ mẫu"*, không phải *"quên tính"*.

**Cơ chế hiện đang sai và cách sửa trong `ZoneAbsorption`:** `adjust_trade_position()` KHÔNG
được trả `trade.stake_amount` (tổng hiện tại). Nó trả `N_full × w_tranche[i]` với `N_full`
**đọc từ kế hoạch chốt lúc tranche 1** (`custom_data`, đúng đường L-Z49 đã kiểm), không tính
lại — vì `R_eff` đóng băng lúc entry (§5.1 v8 dòng 1667). Test khoá: chạy backtest nhỏ thật,
đọc `cost` từng tranche trong file kết quả, tỉ trọng phải là ⅓⅓⅓ ± 1%, và `stake` phải
**biến thiên** theo `1/R_eff` giữa các lệnh.

---

## 4. Đặc tả tầng chốt lời — chép ĐÚNG PHẦN 5

```
TP1 = zone đối diện gần nhất theo hướng lệnh, trừ hao tp1_haircut_pct   → chốt 50% vị thế
TP2 = trail ATR(14,1H) × tp2_trail_atr (1.5, tier_frozen) sau khi TP1 chạm
Fallback: nếu KHÔNG có zone đối diện trong 4.0 × R_eff
          → TP = p_avg + 1.5 × R_eff, tag `tp_source: "fallback_r_multiple"`
```

- **`4.0` và `1.5` nhân với `R_eff` — một KHOẢNG GIÁ đóng băng lúc entry**, không phải R tiền
  tệ (v8, dòng 1667). Trong code và log phải viết `4.0 × R_eff`, không bao giờ "4R".
- Zone đối diện = đỉnh swing gần nhất, **cùng thuật toán Phần 1** (`zone_detection` với
  `loai="dinh"`) — không viết thuật toán mới.
- **Chỉ số H-4 (§11b.2)** phải được ghi từ D4: tỉ lệ lệnh dùng fallback. > 40% ⇒ tiền đề "luôn
  có zone đối diện" sai ⇒ phân loại L2, **không** tune nạng.
- **DG8 áp dụng KHÔNG ĐIỀU KIỆN, kể cả khi TP2 đang trail** — mặc định v3.2 (câu hỏi mở #11).
  Nếu D0.9 cho thấy TIME_STOP cắt nhiều lệnh lãi thì đó là arm riêng phải đăng ký trial.
- **`p_avg` dùng cho TP fallback phải là giá trung bình THẬT theo tỉ trọng ⅓⅓⅓** — sau khi
  tầng 3 (§3) đúng thì `(p1+p2+p3)/3` mới đúng. Đây là lý do nữa TP đứng sau định cỡ.

---

## 5. Ba con số cần chủ dự án — cùng khuôn `v_min`, sẽ hỏi khi tới, KHÔNG tự điền

| # | Con số | Tình trạng | Cần gì |
|---|---|---|---|
| 1 | `tp1_haircut_pct` (tunable #9) | `= 20` trong YAML, spec dòng 1655 `[CẦN CALIBRATE]`, **không có trong `param_status.yaml`** | 🔴 **Đang "im lặng" theo nghĩa L-Z15** — đúng lớp lỗ hổng vừa bịt cho `v_min`, nhưng bản siết chỉ soi mục *đã khai*. Phải quyết TUNED hay FROZEN **trước khi TP chạy** |
| 2 | `notional_co_dinh_usdt` (arm Z0-S1) | tham số bắt buộc của `notional_tranche1_theo_arm()`, spec không chốt (300 USDT dòng 1285 là minh hoạ) | chủ dự án cho một con số hoặc một quy tắc suy ra |
| 3 | `mult_edge = 1.0` trong backtest | spec dòng 1774 nói thẳng | chỉ cần xác nhận và ghi vào Decision Log |

⚠️ **Việc kéo theo (TD-0190):** rà **toàn bộ** dấu `[CẦN CALIBRATE]` trong spec (25 chỗ) và đối
chiếu với `param_status.yaml`. `v_min` và `tp1_haircut_pct` chắc chắn không phải hai cái duy nhất.

---

## 6. Điều quyết định này KHÔNG chốt

- **Không chốt giá trị** của bất kỳ tham số nào ở §5.
- **Không đổi `N_ĐĂNG_KÝ`** — `|tier_b|` vẫn 12, `ARM_B2_COUNT` vẫn 9. Không thêm DOF.
- **Không mở lại D3.5.** Δ_R đứng nguyên (§1.ii).
- **Không xoá `ZoneAbsorptionMinimal`.** Nó ở lại chừng nào `L-Z49` còn trỏ vào nó.
- **Không quyết cách đọc kết quả arm.** Bảng §10.1/§10.1b giữ nguyên vai trò.

---

## 7. Hệ quả lên Khối 16 (TASKS.md)

Thêm **TD-0187** (định cỡ §6.8f B1 + tỉ trọng + nối DG1–5), **TD-0188** (kết nạp §6.8f B2),
**TD-0189** (TP PHẦN 5), **TD-0190** (rà `[CẦN CALIBRATE]`). **TD-0182** đổi đích sang
`ZoneAbsorption`, phụ thuộc TD-0187. **TD-0184** (bộ chạy) phụ thuộc 0182/0183/0187/0188/0189.
**TD-0186** (cổng D4) thêm điều kiện: evidence phải chứa tên chiến lược `ZoneAbsorption` +
tỉ trọng tranche đo từ fill thật = ⅓⅓⅓ + stake biến thiên theo `1/R_eff`.

---

## 8. Lịch sử

- **08/09/2026** — tạo. Chủ dự án bác bản trình đầu (định cỡ là lựa chọn + chi phí Δ_R), duyệt
  phạm vi bảy tầng bắt buộc và thứ tự định-cỡ-trước. Cảnh báo chi phí Δ_R rút lại có số liệu.
