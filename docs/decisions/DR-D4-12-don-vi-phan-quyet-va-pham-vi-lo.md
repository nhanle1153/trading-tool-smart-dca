# DR-D4-12 — Đơn vị phán quyết, ca INCONCLUSIVE, rổ dữ liệu, và phạm vi lô của D4

> **Ngày chốt:** 14/09/2026 · **Người quyết:** chủ dự án (bốn câu, trả lời trực tiếp)
> **Giải:** `MT-25` (phần đơn vị) · khoảng hở *"hành động khi INCONCLUSIVE"* · `MT-34` (phần thi
> hành) · lời mời quyết ở `DR-D4-10` §2.5 (*"thông tin đầu vào nếu chủ dự án muốn mở lại kế toán 9
> suất"*) · **0 trial**
> **Commit RIÊNG và TRƯỚC mọi dòng mã** — kiểm bằng `git merge-base --is-ancestor <sha_DR> <sha_code>`,
> không bằng mắt (khuôn `DR-D4-11` §7).
> Đã nhắn hai phiên song song trước khi mở file (N12 mục 6, sau sự cố *"hai `DR-D4-06`"*); cả hai
> xác nhận không mở DR nào và `DR-D4-12` trống.

---

## 0. Vì sao BỐN câu này phải chốt TRƯỚC, và vì sao bây giờ là lúc duy nhất

Trên đĩa hôm nay **không có một con số expectancy nào của Tool D**: `runs/` không có thư mục trial,
**0 file `.seal`**, `registry/trial_registry.jsonl` **13 dòng = 5 trial** (4 × `B0` + 1 × `CTRL`,
**0 dòng `B2`**), và cả 4 trial `B0` đều `outcome.expectancy: null`.

Spec dòng 3956-3958 đòi mọi thay đổi ngưỡng/cách đọc phải viết TRƯỚC khi thấy kết quả. Bốn câu dưới
đây đều **đổi cách đọc hoặc phạm vi**, không đổi một ngưỡng nào — nên đây là lúc **duy nhất** chốt
chúng mà không ai nghi *"sửa cho dễ qua"*. Cùng lý lẽ `DR-D4-10` §0 đã dùng.

🔴 **Cả bốn đều là quyết định của chủ dự án, không phải của tôi.** Phần phân tích và đề xuất đi
trước; phần chốt là câu trả lời trực tiếp. Mỗi mục ghi cả **phương án đã loại + lý do**, để người
sau khỏi đề xuất lại (khuôn `DR-D4-11` §6).

---

## 1. QUYẾT ĐỊNH 1 — Nhánh 1 phán quyết trên `R` theo rủi ro ĐÃ TRIỂN KHAI

### 1.1 Cơ chế, đọc được trên đĩa chứ không suy

| Chỗ | Nội dung |
|---|---|
| `sizing.py:340` | `planned_risk_usdt = n_full × r_eff` với `n_full` = notional **đủ ba tranche** |
| `trade_plan.py:73-74` | `p_avg = (p1 + p2 + p3) / 3` (*"TRỌNG_SỐ_TRANCHE bằng nhau cả ba"*), rồi `r_eff_plan = (p_avg − sl) / p_avg` |
| `trade_plan.py:68-70` | `p1 = min(zone_high, close)` · `p2 = (zone_high + zone_low)/2` · `p3 = zone_low` ⇒ **`p3 < p2 < p1`** |
| `td0228-z0-vs-dca-tap-lenh.json` | `Z0`: `phan_bo_tranche = {1: 22}` — **100% chỉ tranche 1 khớp** |
| `arm_switches.py:73` | `Z0` và `Z0-T1` đều thuộc `ARM_DON_TRANCHE` (khai tường minh, không suy) |

⇒ `planned_risk_usdt` là tổng rủi ro **ĐÚNG khi cả ba tranche khớp** (mẫu số dùng `p_avg`, đúng giá
vào trung bình của cả ba). Nhưng khi **chỉ tranche 1 khớp** — trường hợp của **100%** lệnh ở mọi arm
ứng viên — rủi ro thật bỏ ra là `stake₁ × (p1 − sl) / p1`, nhỏ hơn. Hệ số co:

```
λ  =  w₁ · [(p1 − sl)/p1]  ÷  [(p_avg − sl)/p_avg]
```

Và vì `p_avg < p1` (do `p3 < p2 < p1`) nên `(p1−sl)/p1 > (p_avg−sl)/p_avg`, tức **`λ > w₁ = 1/3`**.

### 1.2 Vì sao đây là nút có đòn bẩy lớn nhất trong bốn nút

`R` co thì **cả** `mean_R` **và** `std_R` co, nhưng hằng số `0,10` trong rào **không** co:

```
Rào hiện tại      :  mean_cur − (h/√n)·std_cur  ≥  0,10
Sang rủi ro ĐÃ triển khai (chia λ cả hai vế):
                     mean_cur − (h/√n)·std_cur  ≥  0,10·λ
```

Với `λ` quanh 0,5 thì rào trên **đại lượng đang đo hôm nay** nhẹ đi khoảng hai lần. Không nút nào
khác có đòn bẩy gần mức đó — `DR-D4-10` §1.4 đã đo: cắt `N` từ 114 xuống 20 chỉ hạ rào 20%.

### 1.3 🔴 `λ` KHÔNG phải hằng số — DR này vì thế KHÔNG ghim một con số nào

`λ` phụ thuộc **hình học zone của từng lệnh** (`p1` phụ thuộc `min(zone_high, close)`; `sl` phụ
thuộc `buf_sl` theo ATR). Hai hệ quả phải nói rõ:

1. Con số **`λ ≈ 0,53`** mà `DR-D4-10` §1.2 dùng là một **XẤP XỈ**, không phải một phép đo.
2. Phép đại số ở §1.2 giả định `λ` hằng số. Khi `λ` đổi theo lệnh thì `std_R` **không** co đúng
   `1/λ`, nên hệ số nhẹ đi **không** đúng bằng 2. **Tác động thật phải ĐO.**

⇒ DR này định nghĩa **đại lượng**, không ghim **con số**. Đúng bài học `TD-0171`: *tách ghim QUAN HỆ
khỏi ghim QUYẾT ĐỊNH*. `CHI_SO_BAT_BUOC` (`arm_record.py:105`) **đã** bắt buộc
`ty_le_rui_ro_da_trien_khai`, nên bản ghi arm mang **cả hai** vế — cùng khuôn `MT-36`/`MT-37`
(*"hai con số cạnh nhau, không phán xét"*).

### 1.4 Định nghĩa thi hành

Với mỗi lệnh `i`, tính trên **fill thật**:

```
rui_ro_da_trien_khai(i)  =  Σ  stake_j(i) × (entry_j(i) − sl(i)) / entry_j(i)
                          j ∈ tranche ĐÃ KHỚP của lệnh i

R_trien_khai(i)          =  pnl_abs(i) / rui_ro_da_trien_khai(i)
ty_le_rui_ro_da_trien_khai  =  trung bình của  rui_ro_da_trien_khai(i) / planned_risk_usdt(i)
```

`pnl_abs` theo `DR-013` — **đã trừ phí + funding**. `R_ngan_sach(i) = pnl_abs(i) / planned_risk_usdt(i)`
vẫn được tính và báo **cạnh bên**; phán quyết Nhánh 1 đọc `R_trien_khai`.

🔴 **`sizing.py` KHÔNG đổi một dòng.** Đây là đại lượng **ĐỌC** ở tầng đo, không phải đại lượng đặt
lệnh. Bất biến `planned_risk_usdt` không phụ thuộc `R_eff` (`sizing.py:28`) và `Σ w_tranche = 1`
(`:277`) giữ nguyên — chúng đang gánh việc: `DR-D4-10` §2.4 dùng đúng hai bất biến đó để **bác** lý
lẽ *"tranche 2/3 bơm thêm rủi ro"*.

### 1.5 Căn cứ — và nó là DIỄN GIẢI, cãi lại được

`DR-D0PRE-03` suy ngưỡng `0,10 R` từ *"chi phí backtest không thấy (trượt giá SL) × hệ số an toàn"*.
Trượt giá SL xảy ra trên **vị thế thật đang mở**, nên chi phí đó tỉ lệ với rủi ro **đã triển khai**,
không với ngân sách rủi ro đã đặt chỗ nhưng chưa dùng. Đó là lý do nghiêng về vế này.
🔴 Đây **không** phải chữ tường minh của `DR-D0PRE-03`; ghi là **DIỄN GIẢI** để cãi lại được.

### 1.6 Hệ quả cho Nhánh 2 — đổi đơn vị làm phép so CHẶT HƠN, không lỏng hơn

Trên tập giao `Z3` vs `Z0` (`n_giao = 22`, đo ở `TD-0228`): 12/22 lệnh của `Z3` chỉ khớp tranche 1 ⇒
mẫu số **bằng đúng** lệnh `Z0` tương ứng; 10 lệnh khớp thêm tranche ⇒ triển khai **nhiều rủi ro
hơn** nên phải kiếm nhiều hơn tương ứng mới ngang điểm. Ở đơn vị ngân-sách-rủi-ro thì hai vế có mẫu
số **giống nhau tuyệt đối**, tức DCA được so ở một thang **không phạt** việc nó dùng thêm vốn.

### 1.7 🔴 Một bất biến `TD-0184` phải ĐO, không được giả định

Ở lệnh khớp **đủ ba tranche**: `Σ rui_ro_da_trien_khai` có bằng `planned_risk_usdt` không?
Công thức nói **có** (đó là ý nghĩa của `p_avg`). Nhưng *"công thức nói có"* và *"fill thật cho bằng"*
là hai phát biểu khác nhau — và dự án đã trả giá nhiều lần cho việc gộp chúng. Lệch ⇒ **DỪNG, báo**,
không tự chỉnh hệ số cho khớp.

### 1.8 Phương án đã LOẠI

| Loại | Vì sao |
|---|---|
| **(1a)** Giữ mẫu số ngân sách rủi ro, chỉ BÁO thêm tỉ lệ triển khai | Rào thật nặng khoảng gấp hai thứ `DR-D0PRE-03` định đặt ⇒ một INCONCLUSIVE có thể là **hiện vật của mẫu số**, không phải của thị trường. Đúng câu hỏi chẩn đoán N10 (*"bot sai hay tầng đo sai?"*) |
| **(1c)** Hoãn, chạy D4 rồi tính lại | Đổi cách đọc sau khi thấy số là đúng thứ spec `:3956-3958` cấm. Hoãn = đóng cửa vĩnh viễn |

---

## 2. QUYẾT ĐỊNH 2 — `Z0-T1` = INCONCLUSIVE thì VẪN MỞ D5, kèm hai chốt cứng

### 2.1 Phát hiện buộc phải có quyết định này: D4 gần như KHÔNG THỂ ra FAIL

Suy thẳng từ mã (`ket_cuc.py:114-119`), không từ một tài liệu nào:

```
FAIL  ⟺  giá trị < ngưỡng  VÀ  thuế ≤ ngưỡng
Z0-T1 (n = 206):  thuế = (h/√n)·std_R = 0,2144·std_R ≤ 0,10  ⟺  std_R ≤ 0,4664
```

Một hệ có SL cứng tại `−1R` và TP tới `3,2R` **không thể** có `std_R` ≤ 0,47.
⇒ **`Z0-T1` chỉ có HAI kết cục khả dĩ: PASS hoặc INCONCLUSIVE. FAIL là bất khả.**
*(Arm duy nhất còn có thể FAIL là `Z0-T0`, cận `std_R` ≤ 0,966 — nhưng nó mang cờ `mo_ta`, không mua
một phán quyết Nhánh 1.)*

### 2.2 Và nhánh *"gia hạn"* của `DR-011` KHÔNG áp được — hai văn bản dùng CÙNG MỘT CHỮ cho hai kích hoạt khác nhau

| Nguồn | Kích hoạt INCONCLUSIVE | Hành động kèm theo |
|---|---|---|
| `DR-011` (spec `:3352-3361`) | **số lệnh thực tế < 30** | gia hạn, trần **2 lần**, lần thứ ba → FAIL mặc định |
| `DR-D4-09` §2.2 (`ket_cuc.py:116`) | **thuế nhiễu > ngưỡng của chính tiêu chí đó** | *"thêm mẫu / đổi thiết kế"* — **không có quy trình** |

`Z0-T1` có `n = 206` ≫ 30 ⇒ nhánh gia hạn của `DR-011` **không kích hoạt**. Và *"thêm mẫu"* không
có đường: CALIB bị phân vùng `DR-011`, LOCKBOX chỉ một lượt chạm, pool 204 mã đụng `DR-D0PRE-05`.
Với `Z0-T1` thì nút cũng **không phải `n`** — `n` đã 206; nút là **`mean_R` cần 0,22–0,42 R**.

⇒ Không có quyết định này thì D4 tiêu suất trial rồi dừng ở một **trạng thái không có bước kế tiếp
nào được định nghĩa**.

### 2.3 Chốt

INCONCLUSIVE ⇒ **vẫn mở D5 với `Z0-T1`**, và ghi **đúng tên kết cục** vào `d4_han_che` (nhãn
`nguoi-khai`). Bộ lọc thật là đường ống đã thiết kế: **D10 testnet → D11 dry-run → D12 vốn nhỏ**
(`E_D` 750, rủi ro **2,8125 USDT/lệnh** theo `DR-D4-05`). `Z0-T1` cho **325,6 lệnh/năm** ⇒ đạt 50
lệnh live (điều kiện `mult_edge`, và điều kiện mở lại (a) của `DR-Q3-2026`) trong **1,8 tháng**,
thay vì 13,4 tháng nếu chạy `Z0`.

### 2.4 🔴 HAI chốt cứng, viết TRƯỚC, để §2.3 không thành cửa sau

1. **Không ngưỡng nào đổi:** `0,10 R` · `≥ 20%` · `150 lệnh/năm` · `N = 114` · rào `3,0777` ·
   `|tier_b| = 12`. `BEST_KNOWN_DSR_ADJ_EXPECTANCY` (`thresholds.py:30`) giữ **`-inf`** cho tới khi
   có một PASS thật. INCONCLUSIVE **không** được ghi thành PASS ở bất kỳ chỗ nào.
2. **Điều kiện DỪNG viết trước, thay cho phán quyết D4 đã thiếu:** sau 50 lệnh live, `mult_edge`
   chạm 0,5 ⇒ **DỪNG**, không *"chờ thêm"*.
   ⚠️ Điều 2 mở rộng phạm vi sang **D10/D11**, ngoài phạm vi DR này ⇒ nó là **quyết định riêng**,
   phải có mã việc và văn bản riêng. Ghi ở đây để không ai coi §2.3 là đã đủ điều kiện.

### 2.5 Phương án đã LOẠI

| Loại | Vì sao |
|---|---|
| **(2b)** INCONCLUSIVE ⇒ D5 không mở, chỉ mở lại khi nâng `n` | Với `Z0-T1` thì `n` **đã** 206; nút là `mean_R`, nên *"nâng tần suất"* không gỡ được ⇒ thành **một chốt không bao giờ thoả được**, mà dự án đã ghi là *"tệ hơn không có chốt"* (bài học cổng D3) — chốt kiểu đó sớm muộn bị gỡ, và gỡ rồi mất luôn phần đúng của nó |
| **(2c)** Không quyết trước, xử khi thấy kết quả | Đúng ca `DR-D4-08` §6 đã chặn thành công một lần (viết điều kiện DỪNG trước ⇒ không tiêu 9 suất mua một INCONCLUSIVE). Quyết sau khi thấy số là chỗ ngưỡng bị uốn |

---

## 3. QUYẾT ĐỊNH 3 — Rổ pool (`MT-34`): khai hạn chế CÓ SỐ, không khai bằng chữ

### 3.1 Hai kênh, KHÔNG cùng mức nguy — và phân biệt này đổi hẳn hành động

| Kênh | Đo được | Chạm cửa sổ WFO (nơi `Z0-T1` được phán quyết)? |
|---|---|---|
| **(b) mã đã chết bị loại khỏi rổ** — survivorship bias đúng nghĩa | 31 mã ngừng sinh nến: **15 trong CALIB `[T0,T1]`**, **0 trong WFO `[T1,T2]`** | ✅ **KHÔNG**. Và 3/15 là **đổi ticker** (MATIC→POL, RNDR→RENDER, EOS→Vaulta) — tài sản vẫn sống ⇒ 15 còn là **cận trên** |
| **(a) mã chưa sinh vẫn nằm trong rổ** — chọn-rổ-bằng-thông-tin-tương-lai | **24/102 (23,5%)** không tồn tại tại `T1`; rổ đúng tại `T1` = 116 mã, chung 55, **`K = 61` (52,6%)** (`TD-0231`) | 🔴 **CÓ** — rổ được chọn vì có volume cao **tại 09/2026**, tức đã sống sót VÀ đã lớn |

### 3.2 Chốt

**Trước khi tiêu một suất `B2` nào**, đo **ĐẾM** lại phễu `Z0-T1` trên **rổ-đúng-tại-`T1`** (116 mã
của `TD-0231`) và đặt hai con số cạnh nhau — biến một **lời khai** thành một **phép đo**, cùng khuôn
`MT-36`/`MT-37`.

🔴 **Cần một DR NHỎ RIÊNG giải `MT-19`, và nó phải LIỆT KÊ ĐÍCH DANH từng tên trường** được thêm vào
`CTRL_OUTPUT_ALLOWED` (`registry.py:33`) — **không thêm một chỉ số hiệu năng nào**.
⚠️ Bản nháp đầu của kế hoạch viết *"mở cho **nhóm trường** ĐẾM"*. **Sai, đã sửa** (phiên `-4e` nêu,
nhận): `CTRL_OUTPUT_ALLOWED` là danh sách **CHO PHÉP**, và `TD-0130` chọn thế có lý do đã ghi —
*blocklist chỉ chặn được tên đã nghĩ ra trước*. Nới bằng một **mô tả loại** thì **nó thôi là danh
sách cho phép**, đúng điều `CLAUDE.md` đã cảnh báo ở `MT-19`: *"KHÔNG tự nới — nới một lần là mất
luôn tính fail-closed"*. Mỗi tên thêm vào phải có một câu **vì sao nó không phải chỉ số hiệu năng**.

`d4_han_che` **vẫn phải** ghi `K = 52,6%`, và ghi rằng chiều lệch của **TẦN SUẤT LỆNH chưa ai đo và
có thể NGƯỢC** — đúng chữ `MT-34`. Khai một chiều chưa đo, **kể cả chiều nghiêm hơn**, vẫn là khai.

### 3.3 Phương án đã LOẠI

| Loại | Vì sao |
|---|---|
| **(3a)** Dựng pool point-in-time đầy đủ trước D4 | `build_pool.py` **từ chối ghi đè** có chủ đích (spec `:350-352`: không được chọn lại pool sau khi đã thấy kết quả), và spec `:4338` nói đổi pool ⇒ **MỌI bảng `td0205…td0228` mất hiệu lực**, phải đo lại từ đầu. Và EXPLORE **cũng** là ảnh chụp hôm nay ⇒ phạm vi rộng hơn D4 |
| **(3b) thuần** Chạy rồi khai hạn chế bằng chữ | Một hạn chế **không lượng hoá được** thì nó chỉ là chữ |
| **(3c)** Thu cửa sổ D4 về đoạn rổ ổn định | Cửa sổ ngắn ⇒ `n` tụt ⇒ thuế nhiễu tăng ⇒ **tự tay đẩy `Z0-T1` VÀO** INCONCLUSIVE, làm §2 nặng hơn |

---

## 4. QUYẾT ĐỊNH 4 — Phạm vi lô: chạy **4/9** arm, giữ `N = 114`

### 4.1 Chạy arm nào, và suất đó mua gì

| Arm | `n` | Suất mua gì |
|---|---|---|
| **`Z0-T1`** | 206 | ✅ **Phán quyết Nhánh 1** — cấu hình ứng viên **DUY NHẤT** vượt sàn 150 lệnh/năm (`MT-26` (C)) |
| **`Z0`** | 28 | Mốc so paired (`= Z0-T2`, **0 trial thêm** theo §10.1b), mẫu số của phép so |
| **`Z0-T0`** | 883 | 🔬 **CHẨN ĐOÁN** *"Phần 2 đóng góp gì"* — **KHÔNG** mua một phán quyết (spec `:962` cảnh báo nó thoái hoá thành mean-reversion) |
| **`Z3`** | 28 | Một con số THẬT cho câu DCA ⇒ đơn `IQ-0001` có số đo thay vì trống |

**Cắt 5 arm:** `Z1` · `Z2` · `Z3b` · `Z0-V1` · `Z0-S1`. Tiêu **4/110 suất (3,6%)**, tiết kiệm **5**.

### 4.2 🔴 Kế toán — phải tách HAI việc, nếu không đây thành một lần nới rào

`dof.py:91` tính `N = 4 + 3·|tier_b|·2 + ARM_B2_COUNT·2 + 20` với `ARM_B2_COUNT = 9` (`dof.py:30`).

> **Chạy ít arm hơn** (tiết kiệm trial) **≠ đăng ký ít arm hơn** (hạ `N`, **hạ rào DSR**).

DR này giữ **`ARM_B2_COUNT = 9`**, **`N = 114`**, rào **`3,0777`**, `dof_goc` 28, `|tier_b|` 12 —
**không đổi một con số nào**. Đúng thứ `DR-D4-10` §1.4 cảnh báo: *đòn bẩy nằm ở `n`, không ở DOF*.

### 4.3 Ba căn cứ, xếp theo độ mạnh

1. **Không phải *"dừng giữa chừng"*.** `DR-D4-01` §4b từ chối *chạy từng arm rồi dừng khi thấy kết
   quả*. Đây là **đăng ký trước một lô hẹp hơn, KHI CHƯA tồn tại một con số PnL nào** (§0). Khác
   loại hành động, không phải cùng hành động ở mức độ khác.
2. **Căn cứ cắt là MA TRẬN THIẾT KẾ, không phải kết quả** — cả ba đều là phép **ĐẾM** trên EXPLORE,
   **0 PnL**, nên cắt không phải chọn-sau-khi-nhìn-số:
   - `Z2` khác `Z3` **ĐÚNG 0 lệnh** (`TD-0213`, trùng cả `exit_reason` lẫn `tp1_theo_nguon`);
   - `Z3b` khác `Z3` ở **đúng một lần nổ `DG6_EARLY_INVALIDATION`**, tập lệnh **trùng khít**
     (`TD-0213` + `TD-0228`);
   - `Z1` là **tập con NGHIÊM NGẶT** của `Z0` (`n_giao = 6`, `chi_co_o_B = 0`), 72,7% lệnh mất ở
     **cổng kết nạp §6.8f** vì `Z1` đổi SL ⇒ đổi cỡ lệnh ⇒ phép so của nó trả lời **CÂU KHÁC** câu
     §10.1 đặt ra (`MT-31`, hạng hỏng (3) của `DR-D4-10` §2.5).
3. **Giảm số cấu hình THẬT được đánh giá trong khi giữ nguyên hình phạt ĐÃ ĐĂNG KÝ** ⇒ phơi nhiễm
   đa phép thử **thật sự giảm**, rào **không đổi** ⇒ đây là làm **CHẶT hơn**, không phải nới.

### 4.4 Điều kiện mở lại cho 5 arm bị cắt, viết TRƯỚC

- 5 arm **KHÔNG bị bác bỏ** — vào Idea Queue cùng nhãn `DR-D4-10` §2.4 điều 2 dùng cho DCA:
  ***"chưa từng được đo, không phải đã thất bại"***.
- 5 suất trở về **quỹ chung, KHÔNG *"để dành"*** — đúng chữ `DR-D4-01:113`.
- ❌ **KHÔNG** phải điều kiện mở lại: *"thấy tiếc"*, hoặc một kết quả của `Z0-T1` không như mong đợi.

### 4.5 📌 Cái giá, khai ra chứ không ỉm

- **`Z0-S1` là một arm CHẨN ĐOÁN, không chỉ một arm mô tả.** §10.1b dòng 4240: `Z0-S1 > Z0` ⇒ **nghi
  `R_eff` tính SAI** (phân loại L2), *"KHÔNG phải 'vốn cố định tốt hơn'"*. Cắt nó là bỏ một cảm biến,
  và đó là một cái giá **có ý thức**.
- 🔴 **Tiêu chí *"skewness không âm hơn skewness(`Z1`) quá 0,5"* (`thresholds.py:35`, spec `:4273`)
  trở thành KHÔNG ĐO ĐƯỢC** vì `Z1` không chạy. Nó phải ở trạng thái **`pending`**, **cấm điền
  `0.0`** (N6), và phải khai vào `d4_han_che`. Gate không được coi tiêu chí thiếu là PASS ngầm —
  `thresholds.evaluate_branch1()` đã fail-closed đúng chiều đó (*"thiếu khoá nào → khoá đó coi là
  FAIL"*), nên **hệ quả thật là Nhánh 1 không thể PASS trọn vẹn ở đợt này**. Đây là thông tin phải
  nằm trước mắt chủ dự án, không phải một chi tiết thi hành. Hai đường xử, **chưa chọn, không gộp
  vào DR này**: (i) chạy thêm `Z1` chỉ để lấy skewness (tốn 1 suất, và `n = 8` nên con số cũng gần
  như vô nghĩa); (ii) một DR riêng đưa tiêu chí đó về `pending` có căn cứ. Ghi ra để nó không biến
  mất.

---

## 5. Vì sao cả bốn quyết định là làm CHẶT hơn, không phải nới

Không đổi **một ngưỡng nào**: `0,10 R` · `≥ 20%` · `150 lệnh/năm` · `N = 114` · rào `3,0777` ·
`|tier_b| = 12` · `ARM_B2_COUNT = 9`. Thứ đổi là **câu hỏi, đơn vị đọc, và phạm vi** — không phải
**thước**.

1. §1 đổi **đơn vị** sang thứ `DR-D0PRE-03` suy ngưỡng trên, và làm phép so Nhánh 2 **chặt hơn**
   (§1.6). Nó cũng thêm **một bất biến phải đo** (§1.7).
2. §2 **thêm** một điều kiện DỪNG ở D11 mà trước đây không có, và cấm đọc INCONCLUSIVE thành PASS.
3. §3 **thêm** một phép đo bắt buộc trước khi tiêu `B2`, và thêm nghĩa vụ khai `K` + khai rằng chiều
   lệch tần suất **chưa đo**.
4. §4 **giảm** số cấu hình thật được đánh giá trong khi **giữ nguyên** hình phạt đã đăng ký, và khai
   ra hai cái giá (§4.5) thay vì im lặng.

---

## 6. Kế toán

`dof_goc` 28 · `|tier_b|` 12 · `ARM_B2_COUNT` 9 · **`N_ĐĂNG_KÝ` = 114** · rào DSR **3,0777** —
**không đổi**.

**0 trial.** DR này không đánh giá cấu hình nào, không chạm CALIB/WFO/LOCKBOX. Lúc ký:
`registry/trial_registry.jsonl` **13 dòng = 5 trial** (4 × `B0` CONSUMED + 1 × `CTRL` RESERVED,
**0 dòng `B2`**); `n_used()` = **4**; còn **110** suất. `registry/idea_queue.jsonl` **1 dòng**
(`IQ-0001`, `TD-0226`).

Khi `TD-0184` chạy: **4 dòng `B2`** sẽ được `RESERVE` **cả lô trước arm đầu** (`DR-D4-01:114`), và
điều kiện 6 của `DR-D4-11` §3 — *"số dòng `B2` CONSUMED **khớp số arm đã chạy**"* — vì thế tự đúng
với phạm vi mới **mà không phải sửa một hằng số nào**. Đó chính là thứ `DR-D4-11` §3 nói khi chọn
ghim QUAN HỆ thay vì ghim số: `18` lỗi thời sau 24 giờ, `9` lỗi thời sau 6 ngày, quan hệ thì không.

---

## 7. Giới hạn TỰ KHAI

- **`λ` CHƯA ĐO.** §1.3 đã nói rõ nó đổi theo từng lệnh; mọi phát biểu về *"rào nhẹ đi bao nhiêu"*
  là xấp xỉ cho tới khi `TD-0184` báo `ty_le_rui_ro_da_trien_khai`.
- **`std_R` CHƯA ĐO** (`MT-27`). Mọi cận ở §2.1 dùng lập luận định tính (*"hệ có SL cứng −1R không
  thể có `std_R` ≤ 0,47"*), không dùng một số đo.
- 🔴 **Câu *"`Z3` và `Z0` khác `pnl_abs`"* là một SUY LUẬN, CHƯA phải phép đo.** Artifact
  `td0228-z0-vs-dca-tap-lenh.json` tự khai `ranh_gioi`: *"CHỈ đếm … KHÔNG expectancy, KHÔNG PnL"* —
  kiểm lại thì trong đó **không có một trường PnL nào**. Thứ **đo được** là `exit_reason` khác
  (`Z0`: 8 `trailing_stop_loss` / 6 `FUNDING_STOP` / 8 `TP2_TRAIL` · `Z3`: 7 / 8 / 7), nên `pnl_abs`
  **gần như chắc chắn** khác — nhưng **chưa đo**, và đo nó **là đánh giá cấu hình** nên **tốn trial**
  (`DR-014` §2). *(Phiên `-4e` nêu đúng ranh giới này sau khi tự rút lại một khẳng định ngược của
  chính họ; ghi vào đây vì nó cùng họ với lỗi §2.5 mà `TD-0228` vừa bắt: **sai ở NHÃN dán lên phép
  đo, không sai ở phép đo**.)*
- **Nguyên liệu H-4 KHÔNG đến từ Decision Log ở đợt này.** Phiên `-a1` (`TD-0239`) khai rõ bản ghi
  `VAO_RA_LENH` chỉ phủ chiều **VÀO** lệnh; `tp_source`/`tp_zone_age_bars` thuộc bản ghi **RA** lệnh,
  là **phạm vi CHƯA MỞ**. ⇒ `chi_so_h4()` phải đọc thẳng `custom_data`. Ghi ra vì bản nháp kế hoạch
  của tôi từng giả định ngược lại — một **lời khai về phạm vi việc của người khác**, chưa kiểm.
- **Chỉ LONG.** `DR-D4-01` §2 đã ghi; `d3_5_delta_r_niem_phong.SHORT = "unreadable"` ⇒ `L-Z56` từ
  chối chạy ablation Short. Điều kiện mở lại Short: `DR-D4-11` §5 (trỏ tới, **không chép lại**).
- **§4.5 điều 2 có thể làm Nhánh 1 không PASS trọn vẹn được ở đợt này.** DR này **không** giải nó —
  nó khai ra để chủ dự án biết trước khi `TD-0184` chạy.

---

## 8. Điều DR này KHÔNG chốt

- **Không** đụng `DR-D4-01` (Long-only, `RESERVE` cả lô, `B2`, `Z0-T2` = 0 trial) trừ **số lượng arm
  chạy** ở §4 — và đó đúng là mục `DR-D4-10` §2.5 mời chủ dự án quyết.
- **Không** đụng `DR-D4-09` (paired trên tập giao, ba kết cục, CẤM xếp hạng `DSR_adj` giữa arm lệch
  cỡ mẫu) và **không** đụng `DR-D4-10` (ai phán quyết / ai mô tả, mặc định `Z0` cho câu DCA).
- **Không** đụng `DR-D4-11` (tiêu chí đóng cổng D4). §6 chỉ ghi nhận rằng điều kiện 6 của nó tự đúng.
- **Không** chốt `std_R`, **không** chốt `ρ`, **không** chốt `λ`.
- **Không** giải **`MT-26` câu 2** (*xếp hạng phải dùng đại lượng bất biến theo cỡ mẫu*). **Cách đọc
  đề xuất, ghi ra chứ không im lặng bỏ qua:** với đúng **một** arm mang cờ `phan_quyet`, Nhánh 1 là
  câu hỏi **TUYỆT ĐỐI** ⇒ *"cấu hình tốt nhất"* = `Z0-T1` không đi qua một phép xếp hạng nào ⇒ câu 2
  **không kích hoạt ở vòng này**. Đây là **đề xuất cách đọc**, không phải một phán quyết — `MT-26`
  câu 2 vẫn **MỞ**.
- **Không** mở `CTRL_OUTPUT_ALLOWED` (§3.2 nói cần một DR **riêng**, liệt kê đích danh).
- **Không** chốt điều kiện DỪNG ở D11 (§2.4 điều 2) — mở rộng phạm vi sang D10/D11, phải là văn bản
  riêng.
- **Không** chốt cách xử tiêu chí `skewness vs Z1` (§4.5) — hai đường, chưa chọn.
- **Không** cấp phép chạm LOCKBOX. **Không** mở hướng SHORT.
- **Không** đổi `tier_c.arm_ablation.arm` (`TD-0227`, và `MT-35` đã chốt luật: *arm sản xuất = arm
  PASS Nhánh 1*).

---

## 9. Điều kiện mở lại — viết TRƯỚC, khuôn OQ-07

1. **`ty_le_rui_ro_da_trien_khai` đo được ≥ 0,95** ⇒ §1 gần như không đổi gì (mẫu số hai vế trùng
   nhau) ⇒ phải kiểm lại xem `MT-25` có thật là một cơ chế hay chỉ là một lo ngại; và cận lật của
   `DR-D4-10` §1.2 (`λ < 0,138`) phải tính lại bằng số đo.
2. **Bất biến §1.7 LỆCH** (ở lệnh đủ ba tranche, `Σ rui_ro_da_trien_khai ≠ planned_risk_usdt`) ⇒
   **DỪNG**, mở lại §1 toàn bộ: khi đó `planned_risk_usdt` không phải thứ nó tự khai, và **cả hai**
   vế đơn vị đều không đọc được.
3. **`std_R` đo được ≤ 0,4664** ⇒ §2.1 sai, `Z0-T1` có thể FAIL ⇒ §2 phải viết lại. *(Gần như chắc
   chắn không xảy ra với SL cứng `−1R`; nếu xảy ra, nghi thang `R` trước — `MT-25`.)*
4. **Phép đo §3.2 cho phễu `Z0-T1` trên rổ-đúng-tại-`T1` lệch > 30%** so với trên `pool.yaml` ⇒
   `K = 52,6%` không còn là *"khai hạn chế"* mà là *"đo sai rổ"* ⇒ phải xét lại (3a).
5. **`MT-26` câu 2 được chốt theo hướng đòi một phép xếp hạng** ⇒ cách đọc ở §8 hết hiệu lực, phải
   sửa tại chỗ.

❌ **KHÔNG** phải điều kiện mở lại: kết quả D4 không như mong đợi; hoặc `Z0-T1` ra INCONCLUSIVE —
đó là **một trong hai kết cục khả dĩ** mà §2.1 đã khai trước, không phải thông tin mới.

---

## 10. Việc thi hành

| Chặng | Việc |
|---|---|
| a | DR này commit **RIÊNG và TRƯỚC** mọi dòng mã; kiểm `git merge-base --is-ancestor` |
| b | DR **riêng** cho `MT-19`: liệt kê **đích danh** từng tên trường thêm vào `CTRL_OUTPUT_ALLOWED`, mỗi tên một câu vì-sao-không-phải-chỉ-số-hiệu-năng (§3.2) |
| c | Phép đo §3.2 — đếm phễu `Z0-T1` trên rổ-đúng-tại-`T1` (116 mã, `TD-0231`), ghi dòng `CTRL` dạng *đo thước*. **0 trial** |
| d | `TD-0184`: `metrics.py` báo **CẢ HAI** vế `R` (§1.4) + `ty_le_rui_ro_da_trien_khai`; **kiểm bất biến §1.7 và DỪNG nếu lệch**; chạy đúng **4 arm** của §4.1; `RESERVE` cả lô 4 suất trước arm đầu; `chi_so_h4()` đọc `custom_data` (§7) |
| e | `TD-0185`: `evaluate_branch1()` lên **ba** kết cục (gọi `phan_loai_ket_cuc`, không chép công thức); tiêu chí `skewness vs Z1` ở trạng thái **`pending`**, cấm `0.0` (§4.5) |
| f | `TD-0186`: `d4_han_che` khai đủ **sáu** điều — chỉ LONG · D4 không phán quyết câu DCA · `K = 52,6%` kèm *"chiều lệch tần suất CHƯA ĐO"* · chỉ chạy 4/9 arm theo DR này · `skewness vs Z1` = `pending` · và nếu `Z0-T1` = INCONCLUSIVE thì **khai thẳng** |
| g | Nộp 5 arm bị cắt vào Idea Queue (§4.4), `data_source = EXPLORE` + `explore_evidence` (`TD-0126`) |
| h | Test khoá cho §1: **không cho lẫn hai vế `R`** (cùng lớp lỗi `L-Z48c` sinh ra để chặn); và đính chính `DR-013` **tại chỗ**, **giữ nguyên chữ cũ** |

---

## 11. Lịch sử

| Ngày | Sự kiện |
|---|---|
| 10/09/2026 | `MT-25` ghi nhận thang `R_realized` của `Z0` bị CO; `DR-D4-10` §1.2 dùng `λ ≈ 0,53` làm xấp xỉ và chứng minh kết luận nhóm C đứng vững trừ khi `λ < 0,138` |
| 12/09/2026 | `MT-34` ghi nhận rổ pool là ảnh chụp 09/2026, ba đường (a)(b)(c) chưa chọn. `MT-26` (C) chốt `Z0-T1` là ứng viên duy nhất |
| 13/09/2026 | `MT-35` chốt *arm sản xuất = arm PASS Nhánh 1*, `Z0` **không** phải dự phòng. `MT-36` chốt phán quyết trên **toàn** cửa sổ WFO (`TD-0234`) |
| 14/09/2026 | `DR-D4-11` chốt cổng D4 đóng bằng **HIỆN VẬT**, bỏ hằng số 18/9, giữ QUAN HỆ |
| 14/09/2026 | `TD-0228` (`0edac03`): `Z0` vs `Z3`/`Z3b`/`Z2` **trùng tập TUYỆT ĐỐI** (6/6 cặp, `n_giao` 22/22) ⇒ luận điểm *"chọn `Z0` không mất lệnh nào"* của `DR-D4-10` §2.4 **đứng vững**; và §2.5 dòng *"`Z3b` vs `Z3` đúng 1/22 lệnh"* hoá ra là một khác biệt **`exit_reason`**, không phải khác biệt tập lệnh — ghi nhận, **không tự sửa DR** (quy tắc 11) |
| 14/09/2026 | `TD-0226` (`1a00c66`): DCA vào Idea Queue, `IQ-0001`, nhãn *"chưa từng được đo, không phải đã thất bại"*, điều kiện mở lại `n ≥ 319` |
| 14/09/2026 | **Chủ dự án chốt bốn câu — DR này.** Bốn đính chính đi kèm, cả bốn do đọc mã/đọc artifact/nghe phiên khác chứ không do lập luận: (a) `λ` **đổi theo từng lệnh** (`trade_plan.py:73-74`) nên *"rào nhẹ đi đúng hai lần"* là XẤP XỈ, và DR **không ghim `λ`**; (b) *"mở `CTRL_OUTPUT_ALLOWED` cho **nhóm** trường"* là **SAI** — phải liệt kê đích danh, nếu không nó thôi là danh sách CHO PHÉP; (c) *"`Z3` khác `Z0` về `pnl_abs`"* là **SUY LUẬN** từ `exit_reason`, **chưa đo** — artifact `td0228` không có một trường PnL nào; (d) Decision Log của `TD-0239` **không** mang `tp_source`/`tp_zone_age_bars` (chỉ phủ chiều VÀO lệnh) nên `chi_so_h4()` phải đọc `custom_data` — bản nháp kế hoạch đã giả định ngược lại |
