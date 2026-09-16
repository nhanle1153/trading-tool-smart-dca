# DR-D5-01 — Phạm vi, ứng viên và luật chọn của D5 (Calibration, ngân sách B1)

> **Ngày chốt:** 16/09/2026 · **Người quyết:** chủ dự án (ba lượt câu hỏi trong phiên `-24`, trả lời trực tiếp)
> **Mở lại:** (1) quyết định *"HOÃN đặc tả D5–D9"* ngày 13/09/2026 (đoạn mở Khối 18, `TASKS.md`);
> (2) `DR-D4-03` §5 điều 1 (điều kiện mở lại `v_min`) · **0 trial**
> **Commit RIÊNG và TRƯỚC mọi dòng mã** của Khối 19 — kiểm bằng
> `git merge-base --is-ancestor <sha_DR> <sha_code>`, không bằng mắt (khuôn `DR-D4-11` §7).
> Đã nhắn bốn phiên `-30`/`-ea`/`-df`/`-22` tên `DR-D5-01` + dãy `TD-0250…TD-0258` trước khi mở file
> (N12 mục 6); cả bốn xác nhận không dùng trùng.

---

## 0. Vì sao cần DR này

Spec **không có đặc tả D5**: `tool-d-smart-dca.md:4492` chỉ ghi `D5–D9 (giữ nguyên)`, kế thừa từ bản
tài liệu đã bị xoá. Ba câu chữ duy nhất còn lại:

- `:3235` — *"B1. Calibration — 3 giá trị × 12 tham số × 2 hướng → 72"*;
- `:4526-4527` — *"D4/D5 (calibration, tiêu trial từ B1) → ② ĐÃ CALIBRATE: chọn từ ≤3 ứng viên trên tập CALIB"*;
- §9.5 — mỗi lần hiệu chỉnh ngưỡng `[CẦN CALIBRATE]` **là một lần thử**, ghi `trial_registry` TRƯỚC khi chạm dữ liệu.

Ba câu đó không nói: **arm nào**, **tham số nào còn có nghĩa** trên hệ thống hôm nay, **giá trị thử
nào**, **đọc kết quả thế nào**, **khi nào dừng**. Mọi câu trong số đó, quyết **sau** khi thấy số là chỗ
ngưỡng bị uốn (`DR-D4-12` §0). Nên chúng được chốt ở đây, khi **chưa tồn tại một con số PnL nào trên
CALIB** cho bất kỳ cấu hình nào của `ZoneAbsorption`.

**Vì sao mở lại quyết định HOÃN 13/09:** chủ dự án yêu cầu triển khai D5 ngày 16/09 và duyệt kế hoạch —
quyết định mới hơn. DR này chỉ **đặc tả** D5; nó **không** đảo thứ tự ưu tiên testnet (Khối 18 vẫn đi
song song) và **không** cho tiêu suất nào trước khi cổng D4 đóng (§6.1). Ghi đích danh để repo không có
hai câu cùng đứng và ngược nhau (hình `MT-38`).

---

## 1. Phạm vi

| Mục | Chốt | Căn cứ |
|---|---|---|
| Arm | **`Z0-T1`** | `DR-D4-12` §2.3: kể cả INCONCLUSIVE, *"vẫn mở D5 với `Z0-T1`"*; `DR-D4-10` §2.4 (`MT-26` C) — cấu hình ứng viên duy nhất |
| Hướng | **Chỉ LONG** | `DR-D4-01`: Short hoãn có điều kiện. Nửa B1 của Short (`3 × 12`) **không** chuyển sang Long |
| Dữ liệu | **CALIB `[T0, T1]`** = `[2024-04-09, 2025-06-12]` | `DR-011`; `DR-D0PRE-07` |
| Rổ | Point-in-time có xuất xứ theo **`DR-D1-02`** (`TD-0247`), mốc `T0` | `MT-34` đường A-đầy-đủ |
| Độ phân giải | `--timeframe-detail 5m` bắt buộc | H5 (P0). Đo 16/09: 5m sớm nhất 2024-06-01 ⇒ `TD-0252` phải lấp trước |
| Ngân sách | **Trần 16 suất B1** (§4) | Dưới trần đăng ký; `N_ĐĂNG_KÝ` **giữ 114** |
| Cổng vào | `d4_complete` theo **`DR-D4-11`** (hiện vật) | **Không** theo `OQ-11` (đếm 18 trial — đã bị thay) |

🔴 **Không đổi bất kỳ ngưỡng nào của `DR-D4-12` §2.4:** `N = 114` · rào `3,0777` · `|tier_b| = 12` ·
`ARM_B2_COUNT = 9`. Dùng ít suất B1 hơn đăng ký **không** hạ `N` (quy tắc bất biến (3), spec `:3260`) —
cùng lý lẽ *"chạy ít ≠ đăng ký ít"* của `DR-D4-12` §4.2.

---

## 2. Tham số: 7 calibrate, 5 giữ FROZEN

Căn cứ phân loại là **ĐƯỜNG ĐỌC MÃ** (`file:line`) và **đơn vị phán quyết**, **không** phải số đếm trên
EXPLORE — `DR-D4-13` §1.2 mục 3 cấm dùng số EXPLORE làm lý do một cấu hình *"đáng tiêu suất"*.

### 2.1 Bảy tham số calibrate

| Tham số | Nhóm | Đường chạy trên `Z0-T1` |
|---|---|---|
| `zss_threshold` | LỌC LỆNH | `ZoneAbsorption.py:277` — ngưỡng nhận zone |
| `wick_close_upper_frac` | LỌC LỆNH | `:283` → `entry_confirmation.py` `la_nen_rejection` — nhánh (a) |
| `v_min` | LỌC LỆNH | `entry_confirmation.py:183` `hap_thu_co_volume` — điều kiện (c), AND với (a) |
| `buf_sl_atr` | KẾT CỤC | `:278` → `trade_plan.py:71-74` — SL, `r_eff_plan`, cỡ lệnh |
| `tp1_haircut_pct` | KẾT CỤC | `take_profit.py:141,170` — mức TP1 |
| `dg7_funding_frac` | KẾT CỤC | `:1160` `custom_exit`, **vô điều kiện** (`funding_stop.py:7-8`) |
| `max_hold_bars_4h` | KẾT CỤC | `:1155` `custom_exit`, vô điều kiện |

**LỌC LỆNH** = đổi *tập lệnh vào*, không đổi kết cục của lệnh chung. **KẾT CỤC** = giữ tập lệnh vào,
đổi cách lệnh kết thúc. Phân nhóm quyết định thước đo (§5).

### 2.2 Năm tham số giữ FROZEN — không tiêu suất

| Tham số | Vì sao không calibrate |
|---|---|
| `dg4_bars_1h` | **Bất khả trên arm này:** `ZoneAbsorption.py:1006-1007` `return None` khi `cong_ap_dung(arm) == ()`, đứng TRƯỚC lời gọi `danh_gia_tat_ca` (`:1031`); `Z0-T1 ∈ ARM_DON_TRANCHE` (`arm_switches.py:73-75`) |
| `dg6a_atr_ratio` | **Bất khả:** DG6 chỉ chạy ở `Z3b` (`ZoneAbsorption.py:1175`) |
| `dg6d_retrace_frac` | **Bất khả:** chỉ SHORT (`dg6_early_invalidation.py:98-99`) + 0 lời gọi `resolve(tier_b.dg6d_retrace_frac)` |
| `funding_rate_pct` | **Bất khả:** 0 lời gọi `resolve(tier_b.funding_rate_pct)` — `dieu_kien_d` chưa có người gọi (`MT-23`) |
| `mult_corr_thresholds` | **Có đường chạy nhưng thước D5 KHÔNG NHÌN THẤY nó.** `sizing.py:129-141` chỉ nhân cỡ lệnh (1,0/0,75/0,5). Đơn vị phán quyết là `R` theo rủi ro đã triển khai (`DR-D4-12` §1) — **bất biến với cỡ lệnh** (đo 08/09/2026). Mọi chênh lệch đo được sẽ đến từ **tác dụng phụ** (cổng kết nạp §6.8f, sàn min-notional `DR-D4-05`), không từ thứ nó sinh ra để làm (lỗ dồn khi các vị thế cùng sập). Chọn người thắng ở đây là chọn đúng vì sai lý do. Đánh giá thật cần sụt giảm DANH MỤC trên dữ liệu live (§12c) |

Bốn dòng đầu: tiêu suất là mua **đúng số 0** — cùng hình `MT-21`/`MT-23`, và bảng kết quả sẽ trông hoàn
toàn bình thường với hai cột giống hệt nhau.

🔴 **FROZEN→TUNED TẠI CHỖ.** Không khoá nào được chuyển ra khỏi `tier_b` trong D5: `dof.py:91` tính `N`
từ số khoá thật, chuyển một khoá ra ⇒ `N` 114→108, rào 3,0777→3,0601 — nới chuẩn của chính mình
(bài học `DR-D4-02` vs `DR-D4-03`).

---

## 3. Ứng viên — viết TRƯỚC, lý do từ định nghĩa chứ không từ dữ liệu

| Tham số | Mốc (hiện tại) | Thử | Lý do chọn |
|---|---|---|---|
| `zss_threshold` | 0,5 | **0,4 · 0,6** | Đối xứng ±0,1 quanh điểm giữa thang ZSS `[0,1]` |
| `wick_close_upper_frac` | 0,5 | **0,6 · 0,67** | **Chỉ phía chặt.** Tham số điều khiển HAI vế cùng lúc (`DR-D4-08` §3 #1): bóng ≥ f×range VÀ đóng cửa ≥ đáy + f×range. Dưới 0,5 thì vế sau không còn là *"nửa trên"* (spec `:1080`) ⇒ **đổi định nghĩa**, không hiệu chỉnh. 0,67 = quy ước nến búa (bóng ≈ 2/3 cây nến) |
| `v_min` | 1,0 | **0 · 1,5** | `0` = **gần như tắt điều kiện (c)** (xem §3.1). **Không thử 0,8:** PHẦN 3b (spec `:1302-1305`) định nghĩa ca xấu là *"chạm + volume THẤP → không ai bảo vệ"*; thử dưới 1,0 là thử đúng thứ spec đã gọi là sai |
| `buf_sl_atr` | 0,4 | **0,3 · 0,5** | Đối xứng; spec `:3270` tự nêu đúng câu *"`buf_sl` 0,4 hay 0,5 ATR?"* |
| `tp1_haircut_pct` | 20 | **10 · 30** | Đối xứng ±10 điểm phần trăm |
| `dg7_funding_frac` | 0,3 | **0,2 · 0,4** | Đối xứng ±0,1 phần `R_eff_plan` |
| `max_hold_bars_4h` | 24 | **20 · 32** | Biên spec `:1476-1481`: SÀN ≥ 3× chân trời EMA20(4H) ≈ 3,3 ngày ≈ **20 nến**; TRẦN < 40 (tuổi zone §1.3) |

### 3.1 `v_min = 0` — khai đúng nó là gì

`hap_thu_co_volume()` trả `False` khi `volume_ma` là NaN hoặc ≤ 0, **kể cả khi `v_min = 0`**. Nên ứng
viên `0` **gần như** tắt (c), khác đúng ở các nến có `volume_MA(20,1H)` chưa hợp lệ (vùng warmup,
nến volume 0). Chấp nhận khác biệt đó thay vì mở một công tắc mới ngoài chín arm B2.

⚠️ Kết cục *"`0` thắng"* **KHÔNG** được thi hành bằng cách ghi `v_min: 0.0` vào YAML — nó là kết luận
*"bỏ điều kiện (c)"*, và việc bỏ đi qua một thay đổi mã/DR riêng có test (`TD-0254` trả kết cục tường
minh, không trả số).

### 3.2 `v_min` mở lại `DR-D4-03` §5

`DR-D4-03` §5 cho `v_min` rời FROZEN khi **cả ba**: (1) `Z0` thắng `Z0-V1` trên `pnl_abs`; (2) cổng D4
đóng; (3) B1 còn ≥ 3 suất.

- **Điều 1 KHÔNG THỂ thoả** — `Z0-V1` bị cắt khỏi lô D4 (`DR-D4-12` §4.1), và arm sản xuất đã đổi từ
  `Z0` sang `Z0-T1`. Một chốt không bao giờ thoả được thì tệ hơn không có chốt (bài học cổng D3).
- **Thay điều 1 bằng:** phép so `v_min ∈ {0, 1.0}` trên CALIB, **trên đúng `Z0-T1`**, theo luật §5.2.
  Nó trả lời đúng câu điều 1 muốn hỏi (*"(c) có giá trị đo được ở 1,0 không"*), trong cùng suất calibrate.
- **Điều 2 và 3 giữ nguyên.**
- **Khác chữ `DR-D4-03` ở một chỗ, có chủ ý:** `DR-D4-03` viết *"thua hoặc TƯƠNG ĐƯƠNG ⇒ xoá hẳn (c)"*.
  DR này chốt **không phân biệt được ⇒ GIỮ 1,0**. Lý do: PHẦN 3b gọi (c) là *bổ ngữ BẮT BUỘC*; bỏ một
  điều kiện bắt buộc cần bằng chứng nó vô ích, *"chưa thấy nó có ích"* không đủ; và bỏ nó **không hạ `N`**
  (khoá vẫn nằm trong `tier_b`), nên không có lợi ích DSR nào đổi lại.

### 3.3 Băm danh sách ứng viên — máy đối chiếu, không tin lời khai

`TD-0253` từ chối đặt chỗ mọi suất B1 có `(tham số, giá trị)` không khớp khối dưới đây, và kiểm băm của
khối khớp dòng băm. Chuẩn hoá: `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`
rồi `sha256` trên bytes UTF-8.

<!-- DR-D5-01:UNG_VIEN:BEGIN -->
```json
{"arm":"Z0-T1","budget_line":"B1","dr":"DR-D5-01","huong":"LONG","tran_suat":16,"ung_vien":{"buf_sl_atr":{"moc":0.4,"nhom":"KET_CUC","thu":[0.3,0.5]},"dg7_funding_frac":{"moc":0.3,"nhom":"KET_CUC","thu":[0.2,0.4]},"max_hold_bars_4h":{"moc":24,"nhom":"KET_CUC","thu":[20,32]},"tp1_haircut_pct":{"moc":20,"nhom":"KET_CUC","thu":[10,30]},"v_min":{"moc":1.0,"nhom":"LOC_LENH","thu":[0.0,1.5]},"wick_close_upper_frac":{"moc":0.5,"nhom":"LOC_LENH","thu":[0.6,0.67]},"zss_threshold":{"moc":0.5,"nhom":"LOC_LENH","thu":[0.4,0.6]}}}
```
<!-- DR-D5-01:UNG_VIEN:END -->

`sha256 = 8f22faf3796a37c17860da5a77b3e0460c8600aebbc36c9124a1f4374ebec607`

---

## 4. Cách tiêu suất — mốc chung + thử từng tham số + xác nhận ghép

```
Suất 1        MỐC      — Z0-T1, cả 7 tham số ở giá trị hiện tại
Suất 2…15     THỬ      — mỗi lần đổi ĐÚNG MỘT tham số khỏi mốc, 7 × 2, theo thứ tự bảng §3
Suất 16       XÁC NHẬN — cấu hình ghép mọi giá trị đã thắng (CHỈ chạy nếu ≥ 1 tham số đổi)
                                                                 ────────────
                                                          trần   16 suất B1
```

- **Không lưới** (`3^7`). Không thử tổ hợp con khi xác nhận thua. Không thử giá trị thứ tư. Không chạy lại
  suất nào *"vì nghi ngờ"* — chạy lại vì lỗi kỹ thuật đi đường B3 theo DR-014, không đi B1.
- **Mốc chạy MỘT lần:** mọi phép so dùng chung suất 1. Để mỗi tham số tự chạy lại giá trị hiện tại là
  chạy cùng một cấu hình 7 lần, tiêu 7 suất mua thông tin bằng 0.
- **Rút gọn viết TRƯỚC cho `max_hold_bars_4h = 32`:** nếu `TD-0251` đếm được **không lệnh nào** của mốc
  giữ tới 24 nến 4H, thì trần 32 **về cấu trúc** cho đúng tập lệnh và kết cục của mốc ⇒ **bỏ suất đó** (trần
  còn 15). Đây là phép **đếm thời gian giữ lệnh**, không đọc PnL.
- Suất chưa dùng **không** chuyển sang dòng ngân sách khác (`DR-D4-01:113`).

---

## 5. Luật đọc — viết trước, không thêm con số mới nào

Mọi phép trừ nhiễu dùng `thue_nhieu()` (`src/tool_d/gates/ket_cuc.py:55`) với `h = dsr_hurdle(114) = 3,0777`
— **gọi**, không chép. Ngưỡng *"thắng rõ"* là **> 0 SAU KHI trừ nhiễu**: không đặt ngưỡng hiệu ứng
riêng (vd 0,10 R) — đó là bịa một tham số không ai đăng ký (`DR-D4-09` §6, docstring `ket_cuc.py:99-106`).
Đơn vị: `R` theo rủi ro đã triển khai (`DR-D4-12` §1), tính trên `pnl_abs` (DR-013). Khoá ghép lệnh:
`(pair, giờ mở)`.

### 5.1 Nhóm KẾT CỤC — so cặp trên tập giao

Cho mốc A và ứng viên B: `d_i = R_B,i − R_A,i` trên tập giao.

```
B thắng rõ  ⟺  mean(d) − h·std(d)/√n_giao  >  0
```

- Cả hai ứng viên cùng thắng rõ ⇒ chọn cái có `mean(d) − thuế` lớn hơn.
- Không ứng viên nào thắng rõ ⇒ **giữ mốc**.
- `n_giao < 2` ⇒ `pending` (N6), **giữ mốc**.
- 🔴 **Nếu tập lệnh KHÁC nhau** (`buf_sl_atr` đổi cỡ lệnh ⇒ cổng kết nạp có thể nhận/loại khác): áp **thêm**
  phép §5.2 cho phần chênh. B chỉ thắng khi phép giao nói *thắng rõ* **và** phép phần-chênh **không** nói
  *thua rõ*. Hai phép nói ngược nhau ⇒ giữ mốc, ghi hạn chế.

### 5.2 Nhóm LỌC LỆNH — đo riêng NHÓM LỆNH BỊ THÊM/BỚT

🔴 **Vì sao KHÔNG dùng `so_paired`:** bộ lọc chặt hơn chỉ BỚT lệnh; lệnh chung có kết cục y hệt ⇒
`d_i ≡ 0` trên tập giao ⇒ phép so cặp luôn ra *"không khác"*. Câu đúng là: ***"những lệnh mà giá trị
lỏng hơn cho thêm vào có lời không?"***

Cho hai giá trị kề nhau, `L` lỏng hơn và `S` chặt hơn; `E` = lệnh **chỉ có ở `L`**:

```
m = mean(R_E) ,  t = h·std(R_E)/√|E|
m − t > 0   ⇒  phần thêm lời rõ  ⇒  L tốt hơn S
m + t < 0   ⇒  phần thêm lỗ rõ   ⇒  S tốt hơn L
còn lại     ⇒  không phân biệt được
```

**Đi từng bước từ mốc, mỗi bước cần bằng chứng riêng:**

| Tham số | Thứ tự lỏng → chặt | Quyết định |
|---|---|---|
| `zss_threshold` | 0,4 → **0,5** → 0,6 | Bước (0,4 vs 0,5) *L tốt hơn* ⇒ 0,4. Bước (0,5 vs 0,6) *S tốt hơn* ⇒ 0,6. Cả hai cùng nói ⇒ **không đơn điệu ⇒ giữ 0,5**, ghi hạn chế. Không bước nào nói gì ⇒ giữ 0,5 |
| `v_min` | 0 → **1,0** → 1,5 | Như trên. *"0 tốt hơn 1,0"* ⇒ kết cục **"bỏ (c)"** (§3.1), không phải số |
| `wick_close_upper_frac` | **0,5** → 0,6 → 0,67 | Bước (0,5 vs 0,6) *S tốt hơn* ⇒ sang 0,6; **chỉ khi đã sang 0,6** mới xét bước (0,6 vs 0,67) |

- `|E| < 2` ⇒ `pending`, **giữ mốc**.
- 🔴 **Tập lệnh không lồng nhau** (có lệnh **chỉ có ở `S`**, vd vì cổng kết nạp danh mục đổi theo tập
  mở cùng lúc) ⇒ phép này **không áp được sạch** ⇒ giữ mốc, ghi số lệnh chỉ-ở-`S` vào hạn chế. Không
  vá bằng một phép khác nghĩ ra sau khi thấy số.

### 5.3 Xác nhận ghép

Chạy khi ≥ 1 tham số đổi. So cấu hình ghép `G` với mốc `A` bằng **chênh tổng R** trên CALIB, tách ba phần:

```
Δ  = Σ_giao d_i  +  Σ_{chỉ G} R  −  Σ_{chỉ A} R
SE = √( n_giao·var(d)  +  n_G'·var(R_chỉG)  +  n_A'·var(R_chỉA) )
G  xác nhận  ⟺  Δ − h·SE > 0
```

- Xác nhận ⇒ áp mọi giá trị đã thắng.
- **Không xác nhận ⇒ GIỮ NGUYÊN TOÀN BỘ MỐC** (chủ dự án chốt). Không thử bỏ bớt từng tham số.
- Phần có `n < 2` đóng góp 0 vào `SE` và được ghi hạn chế.

---

## 6. Điều kiện DỪNG — viết trước

1. **Không đặt chỗ suất B1 nào trước `d4_complete`** (`DR-D4-11`). Calibrate giữa chừng là đổi baseline
   trong lúc D4 đang so sánh (`DR-D4-03` §5 điều 2).
2. **Trước suất 1:** `TD-0251` đếm `n` của mốc trên CALIB (chỉ đếm, dòng `CTRL` theo `MT-19`) và báo
   **hiệu ứng nhỏ nhất phát hiện được** `h·std_R/√n`, với `std_R` lấy từ EXPLORE **chỉ để lập kế hoạch**
   (`DR-D4-13` §1.6). **Chủ dự án xác nhận đi/không đi** trước khi đặt chỗ suất đầu tiên.
   `n < 30` (mốc DR-011, không phải số mới) ⇒ **DỪNG**, không trình.
3. **Mốc (suất 1) sinh 0 lệnh hoặc lỗi kỹ thuật** ⇒ DỪNG D5; chạy lại đi đường B3.
4. **Phát hiện một tham số trong §2.1 KHÔNG đổi tập lệnh hay kết cục nào** giữa mốc và ứng viên (hai lượt
   trùng từng lệnh) ⇒ đó là **lỗi nối**, không phải kết quả: DỪNG các suất còn lại của tham số đó, mở việc
   sửa (bài học `MT-21`/`MT-23` — sổ ghi CẤU HÌNH, không ghi TẬP LỆNH).
5. **FreqAI đổi tín hiệu vào lệnh hoặc thoát lệnh** (Khối 17, `DR-FAI-01` chưa commit) **trước khi** D5
   đóng ⇒ dừng suất chưa chạy, trình lại phạm vi. **Sau khi** D5 đóng ⇒ kết quả D5 giữ nguyên, gắn nhãn
   *"calibrate trên hệ không-FreqAI"*; FreqAI không tự động kế thừa hay vô hiệu nó.

---

## 7. Hạn chế khai TRƯỚC — chép vào `d5_han_che` khi đóng cổng

- **Chỉ LONG.** Không nói gì về Short.
- **Chỉ CALIB.** Giá trị đã chọn chưa qua WFO (D9) hay LOCKBOX (D9.5) — trạng thái ② của §12b.1, không phải ③/④.
- **5/12 tham số không calibrate** (§2.2); `mult_corr_thresholds` cần dữ liệu danh mục live.
- **Một-tham-số-một-lần:** tương tác chỉ được kiểm ở một điểm (xác nhận ghép), không được khảo sát.
- **Nhiều tham số dự kiến giữ nguyên** vì ngưỡng *"thắng rõ"* sau khi trừ nhiễu với `h = 3,08` là chặt.
  *"Giữ mốc"* nghĩa là **không phân biệt được**, KHÔNG phải *"mốc đã được chứng minh tốt nhất"*.
- `v_min = 0` chỉ **gần** tắt (c) (§3.1).
- Số EXPLORE không xuất hiện làm căn cứ ở bất kỳ phán quyết nào của D5 (`DR-D4-13` §1.2).

---

## 8. Chưa chốt — trình chủ dự án

**`MT-18` phương án (b) có kích hoạt ở D5 không?** `L-Z29` canh SỐ ĐẾM `|tier_b|`, không canh DANH TÍNH.
D5 là lần đầu tham số `tier_b` đổi trạng thái hàng loạt. Đề xuất nhẹ hơn (b) nguyên bản: một test khoá ghim
**đúng tập 12 tên** khoá `tier_b` (không đổi hình dạng `dof_inventory.yaml`). Chưa chốt ⇒ `TD-0256` chỉ làm
phần `TUNED ⇒ trial_id` đã duyệt.

---

## 9. Phương án đã LOẠI

| Loại | Vì sao |
|---|---|
| Tiêu đủ **72** theo chữ `:3235` | Short hoãn (`DR-D4-01`); 4 tham số bất khả trên `Z0-T1` ⇒ mua số 0 |
| Calibrate đủ 12, LONG (36 suất) | 12 suất cho 4 tham số bất khả ra kết quả trùng khít |
| Mỗi tham số tự chạy đủ 3 giá trị (21 suất) | Mốc chạy lại 7 lần giống hệt; không kiểm tương tác |
| Lưới tổ hợp | `3^7` cấu hình; phá tinh thần *"≤3 ứng viên"* |
| Tiêu B1 song song D4 | Đổi baseline khi D4 đang so (`DR-D4-03` §5 điều 2) |
| `so_paired` cho nhóm lọc lệnh | `d ≡ 0` trên tập giao ⇒ luôn *"không khác"* (hình `MT-21`) |
| So `R` trung bình mỗi lệnh cho nhóm lọc | Thiên vị bộ lọc chặt: bớt lệnh làm trung bình đẹp lên dù tổng lời giảm |
| So tổng R/năm cho nhóm lọc | Gộp cả lệnh chung (không đổi) vào phương sai ⇒ nhiễu lớn hơn phép §5.2 cùng câu hỏi |
| Ngưỡng *"thắng rõ"* = 0,10 R sau trừ nhiễu | Thêm một ngưỡng hiệu ứng không ai đăng ký |
| Hoà `v_min` ⇒ bỏ (c) (chữ `DR-D4-03`) | Bỏ điều kiện bắt buộc cần bằng chứng vô ích; không lợi DSR (§3.2) |
| `v_min = 0,8` · `wick_close_upper_frac = 0,4` | Thử đúng thứ spec định nghĩa là sai / đổi định nghĩa điều kiện |
| Giữ `mult_corr_thresholds` trong D5 | Thước `R` bất biến với cỡ lệnh ⇒ chỉ đo tác dụng phụ (§2.2) |
| Giữ `v_min` FROZEN vì điều 1 `DR-D4-03` §5 | Điều 1 không thể thoả ⇒ tham số đi tới tiền thật mà chưa ai kiểm; câu điều 1 trả lời được ngay trong D5 |

---

## 10. Thi hành

| Mã | Việc | Đầu vào từ DR này |
|---|---|---|
| `TD-0251` | Đếm `n` + thời gian giữ lệnh của mốc trên CALIB | §4 rút gọn `max_hold`, §6.2 |
| `TD-0252` | Dữ liệu 5m CALIB | §1 |
| `TD-0253` | Máy kế toán B1: trần 16 · ứng viên khớp khối §3.3 + băm · 7 tham số | §3.3, §4 |
| `TD-0254` | `chon_gia_tri.py` thuần: §5.1 · §5.2 · §5.3 · kết cục *"bỏ (c)"* tường minh | §5, §3.1 |
| `TD-0255` | Bộ chạy trên E1, file cấu hình phủ, kiểm tập lệnh thật sự đổi | §6.4 |
| `TD-0256` | `L-Z15`: TUNED ⇒ `trial_id` B1 CONSUMED | §2 |
| `TD-0257` | `close_d5_gate()` + `d5_han_che` | §7 |
| `TD-0258` | Chạy ≤ 16 suất | §4, §6 |

🔴 Quy tắc gốc 1: `TD-0251…TD-0258` chỉ bắt đầu khi chủ dự án gõ **"bắt đầu code"**.
