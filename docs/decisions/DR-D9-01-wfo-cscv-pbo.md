# DR-D9-01 — D9: Walk-forward đủ phân hoạch + PBO/CSCV nâng lên P0

> **Ngày chốt:** 17/09/2026 · **Người quyết:** chủ dự án (hai lượt câu hỏi khi lập kế hoạch, phiên `-33`)
> **Mở lại:** (1) quyết định *"HOÃN đặc tả D5–D9"* ngày 13/09/2026, nay **cho riêng D9** (`DR-D5-01` §0 đã
> mở cho D5; `MT-48`); (2) `OQ-11` ở điểm *"D5–D9 là pha phát triển, không có khoá máy"* — D9 nay có khoá
> `d9_complete` (§6.3); (3) cách đọc *"B1 chỉ chạy trên CALIB"* mà cửa `TD-0253`
> (`src/tool_d/calibration/ung_vien.py:149`) mã hoá từ `DR-D5-01` §1 — §3.1 · **0 trial**
> **Commit RIÊNG và TRƯỚC mọi dòng mã** của Khối 23 — kiểm bằng
> `git merge-base --is-ancestor <sha_DR> <sha_code>`, không bằng mắt (khuôn `DR-D4-11` §7).
> Đã nhắn hai phiên `-30`/`-01` tên `DR-D9-01` + dãy `TD-0280…TD-0288` + `MT-51…MT-53` trước khi mở file
> (N12 mục 6). Va chạm dãy mã với `-01` (đặc tả nháp D6–D8, `DR-D6D8-01`) giải bằng cách `-33` **dời
> mã** — thứ tự pha D6–D8 đứng trước D9, và chưa bên nào commit.

---

## 0. Vì sao cần DR này

Spec **không có đặc tả D9**. `tool-d-smart-dca.md:4492` chỉ ghi `D5–D9 (giữ nguyên)`. Các câu chữ duy
nhất còn lại:

- `:4287-4288` — Nhánh 1 §10.2: *"PBO ≤ 0.5 qua CSCV trên 9 cấu hình, tính riêng mỗi hướng (H18) — 🟡 P1
  ở lần chạy đầu"*;
- `:4326` — *"CSCV cần ≥ 8 phân hoạch… tính và ghi lại PBO nhưng chưa dùng làm điều kiện chặn ở D0.9 lần
  đầu; nâng lên P0 ở GATE TOOL D (D9), nơi WFO đã sinh đủ cặp IS/OOS để CSCV có power"*;
- `:4349` (H18) — *"🟡 P1 ở D4, nâng P0 ở D9 — ở D9 (WFO đủ fold) dùng làm điều kiện chặn"*;
- `:4526-4531` — *"② ĐÃ CALIBRATE ↓ D9 (walk-forward) ③ ĐÃ WFO — sống sót qua nhiều fold ↓ D9.5"*;
- `:3291` — WFO `[T1 … T2]` dùng cho *"Walk-forward D3/D9, Ablation D0.9 (B2)"*.

Đối chiếu với repo ngày 17/09/2026, **bốn câu trong số đó không còn thi hành được theo chữ**:

1. **"Đủ fold" không đạt được bằng fold.** `DR-D3-01` chốt 3 fold anchored `12 + 3 × 7` tuần, vừa khít
   **33,0 tuần** của `[T1,T2]` (`config/tool_d_config.yaml:124-132`, `sinh_folds` raise nếu thiếu ngày).
   Không có chỗ cho fold thứ tư; rolling (`DR-D3-01` PA-3) tối đa 5 fold, vẫn dưới 8; kéo dài cửa sổ phải
   dời `T2` vào LOCKBOX — bị cấm (`DR-D3-01` §5.3, `DR-D0PRE-07` §7).
2. **"Trên 9 cấu hình" không còn tồn tại.** `DR-D4-12` §4 chỉ chạy 4 arm; `Z0` ≡ `Z3` trùng khít từng lệnh
   (TD-0228); bảy arm nhóm C là **mô tả**, cấm đọc như phán quyết (`DR-D4-10` §2.2). Arm lồng nhau
   (`Z3b ⊃ Z3 ⊃ Z2`, `:4326`).
3. **Không dòng ngân sách nào trả cho lượt chạy WFO của D9.** `B0 4 · B1 72 · B2 18 · B3 20` (`:3234-3239`);
   theo DR-014 (`:3493`, `:3514`) mỗi cấu hình đánh giá trên WFO là 1 trial.
4. **Code đang chặn PBO ở D4**, trái chữ P1: `src/tool_d/gates/thresholds.py:86` đưa `pbo` vào
   `failed_criteria` (thiếu ⇒ `+inf` ⇒ FAIL), trong khi comment dòng 39 ghi *"không chặn D0.9"* (`MT-51`).

Mọi câu *"chia mấy khối, so cấu hình nào, trả bằng suất nào, xếp hạng bằng gì"* — nếu quyết **sau** khi có
số WFO — là chỗ phép đo bị uốn (`DR-D4-12` §0). Nên chúng được chốt ở đây, khi **chưa tồn tại một con số
PnL nào của `ZoneAbsorption` trên cửa sổ WFO sau calibration** và D5 chưa tiêu suất nào.

**Vì sao mở lại quyết định HOÃN 13/09 cho D9:** chủ dự án yêu cầu triển khai D9 ngày 17/09 và duyệt kế
hoạch — quyết định mới hơn. DR này chỉ **đặc tả** D9 và dựng phần **0 trial**; nó **không** cho chạy lượt
WFO nào trước cổng vào (§6.1) và **không** đặc tả D6–D8 (phiên `-01` soạn nháp `DR-D6D8-01` song song).

---

## 1. Phạm vi

| Mục | Chốt | Căn cứ |
|---|---|---|
| Arm | **`Z0-T1`** với tham số sau D5 | `DR-D4-10` §2.4 (`MT-26` C); `DR-D5-01` §1 |
| Hướng | **Chỉ LONG.** PBO Short = `pending`, không phải `0.0` (N6) | `DR-D4-01`; chủ dự án 17/09 (Long-only tới live, theo `-01`) |
| Dữ liệu | **WFO `[T1, T2)`** = `[2025-06-12, 2026-01-29)` | `DR-011`; `DR-D0PRE-07` |
| Phép đo | Nhánh 1 §10.2 trên **đoạn test** của 3 fold · PBO qua CSCV trên **cả cửa sổ** | `MT-36`; §4 |
| Không thuộc D9 | Chạm LOCKBOX (D9.5) · chọn lại tham số · Short · FreqAI | `L-Z13`; `:4526` |

---

## 2. Tập cấu hình của CSCV — các biến thể D5

**Chốt:** tập CSCV = **đúng tập cấu hình B1 đã CONSUMED trên CALIB ở D5** (`DR-D5-01` §4: mốc · các giá trị
thử · xác nhận ghép nếu có), mỗi cấu hình chạy lại **một lần** trên WFO.

- **Đọc từ sổ trial**, không khai tay: `budget_line = B1`, `dataset = CALIB`, state `CONSUMED`. Không thêm
  cấu hình nào ngoài sổ, không bớt cấu hình nào *"trông vô nghĩa"*. Suất CALIB bị `REFUNDED` không vào tập.
- **Vì sao tập này, không phải arm D4:** PBO trả lời *"xác suất cấu hình được CHỌN chỉ thắng nhờ may trên
  dữ liệu đã dùng để chọn nó"*. Lựa chọn cuối cùng trước D9 là lựa chọn của D5; đo PBO trên arm D4 là đo
  một lựa chọn khác (và `Z0` ≡ `Z3` khiến tập 4 arm chỉ còn 3 phần tử phân biệt).
- **Gộp cấu hình trùng khít trước khi tính.** Hai cấu hình có **cùng dãy `(open_date, R)`** là cùng một
  chiến lược về mặt đo — giữ cả hai là đếm một điểm hai lần và kéo hạng. Gộp, ghi danh sách gộp vào hiện
  vật (`cau_hinh_gop_trung`). Đây là bài học `Z0` ≡ `Z3`, không phải một bộ lọc theo kết quả.
- **Dưới 2 cấu hình phân biệt sau gộp ⇒ PBO = `unreadable`.** Không có gì để xếp hạng.

🔴 **Giới hạn phải khai (chép vào `d9_han_che`):** CSCV đo overfitting của luật **argmax IS**. Luật chọn
thật của D5 (`DR-D5-01` §5) là *"giữ mốc trừ khi thắng rõ sau trừ nhiễu"* — bảo thủ hơn argmax. PBO ở đây
vì thế là **cận trên thô** cho rủi ro chọn quá tay của D5, không phải xác suất của đúng luật D5.

---

## 3. Ngân sách — phần B1 còn dư

**Chốt:** mỗi lượt WFO của D9 đặt chỗ một suất **`budget_line = B1`, `dataset = WFO`**.

| Mục | Giá trị |
|---|---|
| Suất WFO / cấu hình | **đúng 1** — cấu hình phải khớp một suất B1 CALIB CONSUMED (`param_under_test`, `param_value`) |
| Trần suất WFO | **= số suất B1 CALIB đã CONSUMED** (≤ 16, `DR-D5-01` §4) |
| Tổng B1 tối đa | CALIB ≤ 16 + WFO ≤ 16 = **≤ 32 ≤ 72** đăng ký |
| Chạy lại vì lỗi kỹ thuật | đi **B3** theo DR-014, không đi B1 (khuôn `DR-D5-01` §4) |
| Điều kiện đặt chỗ | cổng vào D9 đã mở (§6.1) — chặn **tại cửa** `registry.reserve()` (khuôn TD-0253) |

- **`N` đăng ký không tăng** vì suất nằm trong 72 đã đăng ký; `|tier_b| = 12` không đổi.
- 🔴 **Rào DSR của phán quyết D9 KHÔNG ghim cứng `N = 114`.** Spec `:2821`/`:4267`: overlap pool với Tool A
  ≥ 50% (H14) ⇒ DR-007 ⇒ **N là UNION**. Phiên `-01` đặt câu đó vào D6 (`DR-D6D8-01`, nháp). D9 đọc `N` từ
  nguồn kế toán hiện hành (`gates/dsr.py::effective_n` hoặc hàm thay thế nếu D6 chốt union) — **không**
  viết hằng số 114 ở tầng D9. Hôm nay nguồn đó trả 114, rào 3,0777.
  ✅ **`MT-50` chốt 17/09/2026 (`DR-D6D8-01`, `7428678`): ngưỡng DR-007 là `≥ 50%`.** Overlap đo ở TD-0261 (D6)
  `≥ 50%` ⇒ `N` của D9 là UNION với Tool A; `danh_gia_cong_d9(n_trials=…)` nhận đúng số đó, không sửa mã.
- 🟡 **Lệch chữ spec, khai thẳng (`MT-52`):** `:3291` gắn WFO với B2 (dùng chung ablation). B2 = `9 × 2`;
  D4 giữ 9 Long; nửa còn lại *"không tự động thuộc về Short"* (`DR-D4-01:113`) nhưng chỉ đủ 9 < 16. Chủ dự
  án chọn **B1 dư** thay vì B2 (không đủ suất) hay mở rộng `N` (nâng rào DSR, sửa mọi chỗ ghim 114).
- Suất B1 CALIB chưa dùng của D5 **không** chuyển sang WFO — trần WFO đếm theo suất CALIB đã CONSUMED,
  không theo 16.

### 3.1 Hai quyết định đã chốt chạm nhau — khai, không vá lặng lẽ (`MT-52`)

Phiên `-30` chỉ ra ngày 17/09, trước khi DR này commit:

- `DR-D5-01` §1 chốt dữ liệu D5 = CALIB; `TD-0253` mã hoá thành cửa fail-closed **tại `reserve()`**:
  `dataset != "CALIB"` ⇒ `B1Error` (`ung_vien.py:149-150`). Theo đúng chữ đó, **suất WFO đầu tiên của D9 bị
  từ chối** — và đó là cửa hoạt động đúng.
- Tiền lệ `DR-D4-01:113`: suất không dùng *"KHÔNG tự động"* thuộc về việc khác. Cùng logic, **"B1 dư" không
  tự động thuộc về D9** chỉ vì còn dư.

**Chủ dự án đã quyết 17/09** (câu hỏi lập kế hoạch có nêu thẳng *"phải khai trong DR và mở rộng máy kế
toán B1 (TD-0253), vì hiện nó chỉ nhận ứng viên trên CALIB"*). DR này là câu **tường minh** đó:

1. **Chuyển giao:** tối đa **16 suất** trong phần B1 đăng ký mà D5 không dùng được **giao cho D9**, chỉ dùng
   theo §3 (một suất WFO cho mỗi cấu hình CALIB đã CONSUMED). Phần còn lại ở quỹ chung, không để dành.
2. **Cửa `:149` KHÔNG bị nới.** Nhánh CALIB giữ nguyên từng chữ và mọi ca của `test_td0253_*` giữ nguyên
   khẳng định. `TD-0284` **thêm** một nhánh `dataset = WFO` với điều kiện **chặt hơn** (§3 + §6.1), mọi
   `dataset` khác (`LOCKBOX`, `N/A`) vẫn bị từ chối. Thứ tự bắt buộc: commit DR này **trước** commit mã
   `TD-0284` (`git merge-base --is-ancestor`).
3. **Nhãn sổ — đã chốt (a), xem cuối mục.** Mượn `budget_line = B1` cho WFO làm nhãn `B1`
   mang **hai nghĩa theo thời gian** (*"chạm CALIB để calibrate"* / *"chạm WFO để kiểm calibrate"*); mọi
   audit/báo cáo đọc `budget_line` phải phân biệt thêm bằng `dataset`. Hai đường:
   Hai phương án đổi **hai loại rủi ro khác nhau**, không cái nào tốt hơn tuyệt đối. Đã đọc mã ngày 17/09
   (không suy), các chỗ lọc `budget_line` trong `src/` + `entrypoints/`:

   | | (a) giữ `B1` + phân biệt bằng `dataset` | (b) nhãn riêng `B1W` |
   |---|---|---|
   | Nghĩa của sổ | nhãn `B1` mang **hai nghĩa theo thời gian** | sổ tự nói nghĩa |
   | Schema | không đổi | **phải** thêm `B1W` vào `enum` `trial_event.schema.json:51`; quên ⇒ `_append()` raise (TD-0150) — hỏng **ồn ào** |
   | Cửa `reserve()` | `registry.py:496` đã đưa `B1` qua cửa B1; nhánh WFO thêm vào cửa đó | `registry.py:496` chỉ đưa `B1` qua cửa ⇒ suất `B1W` **đi vòng qua toàn bộ cửa B1** nếu quên thêm — **rò im lặng** |
   | Trần | `ung_vien.py:183-201` đếm **gộp** mọi B1 vào trần 16 của D5 ⇒ phải tách theo `dataset` (rò theo chiều **chặn thừa**, an toàn) | mọi phép cộng theo dòng phải biết `B1W` thuộc 72 đăng ký; chỗ nào quên ⇒ `B1W` **thoát trần** (phiên `-30`) |
   | `L-Z15` | `audit_checks.py:275` nhận **mọi** `B1` CONSUMED làm bằng chứng TUNED ⇒ phải thêm `dataset == CALIB`, không thì suất WFO làm được bằng chứng calibrate | `:275` tự loại `B1W` (đúng) |
   | Tính vào `N` / rào DSR | không đổi | **fail-safe**: `registry.py:207` là danh sách CHẶN `!= CTRL` ⇒ nhãn mới tự tính vào `N` (phiên `-30`) — rủi ro của (b) khoanh ở **cửa** và **trần**, không lan sang `N` |
   | Chỗ khác | `d4_gate.py:136` lọc `B2`, `audit_checks.py:685` lọc `B3` — không chạm | như (a) |

   **Kiểm-có-răng bắt buộc cho `TD-0284` dù chọn bên nào:** (a) — suất `B1/WFO` không làm tăng bộ đếm trần
   CALIB · suất `B1/WFO` bị `L-Z15` từ chối làm bằng chứng TUNED · gỡ phép lọc `dataset` ⇒ hai ca đó **đỏ**.
   (b) — đặt chỗ `B1W` **đi qua** cửa B1 (gỡ ⇒ đỏ) · `B1` + `B1W` vượt 72 ⇒ từ chối, bỏ `B1W` khỏi phép cộng
   ⇒ ca đó **đỏ** · ghi `B1W` thật đối chiếu schema.

   **Đếm đủ, không chỉ hai chỗ đã nghĩ tới để tìm** (`grep -rn "['\"]B1['\"]\|BUDGET_LINE_B1"` trên `src/`
   + `entrypoints/`, 17/09): phép so nhãn trên **sổ** có **đúng ba** — `ung_vien.py:185`,
   `audit_checks.py:275`, `registry.py:496`. `ung_vien.py:111` so tiêu đề khối trong DR, không đọc sổ.

   🔴 **Bẫy thứ tự của (b)** (phiên `-30`): hôm nay một lần đặt chỗ `B1W` bị schema chặn — an toàn **do tình
   cờ**. Bước hiển nhiên khi làm `TD-0284` là thêm `B1W` vào enum; **đúng khoảnh khắc đó** `B1W` tới
   `registry.py:496`, không khớp `== "B1"`, và đi vòng qua cả cửa. Hành động sửa đúng tại chỗ mở lỗi toàn
   cục. Nếu chọn (b): sửa cả ba phép so **TRƯỚC**, mở enum **SAU**, kèm ca *"`B1W` sai ràng buộc ⇒ từ chối"*
   chạy được trước khi enum mở.

   ✅ **CHỦ DỰ ÁN CHỐT (a) — 17/09/2026**, sau khi thấy bảng này. Bảng giữ nguyên làm lịch sử.

   Lý do nghiêng **(a)** khi trình, đổi so với nháp đầu: lỗi tệ nhất của (b) là **cả cửa B1 bị đi vòng im lặng**
   (`registry.py:496`), còn các chỗ cần sửa của (a) đếm được hết (hai dòng) và hỏng về chiều chặn thừa hoặc
   có ca test bắt.

---

## 4. CSCV — viết trước, băm để máy đối chiếu

Theo Bailey, Borwein, López de Prado & Zhu (2014), *The Probability of Backtest Overfitting*.

### 4.1 Phân hoạch — tách khỏi fold

- `[T1, T2)` chia **S = 8 khối lịch bằng nhau**, mỗi khối **693 giờ** (231 × 24 / 8 chia hết; theo ngày
  thì lẻ 28,875). Mốc khối (UTC): `2025-06-12 00:00` · `07-10 21:00` · `08-08 18:00` · `09-06 15:00` ·
  `10-05 12:00` · `11-03 09:00` · `12-02 06:00` · `12-31 03:00` · `2026-01-29 00:00`.
- **Tách khỏi 3 fold của `DR-D3-01`.** Fold giữ nguyên vai trò phán quyết Nhánh 1 trên đoạn test (`MT-36`);
  CSCV là phép **riêng** trên cùng danh sách lệnh (§5). `DR-D3-01` **không** mở lại.
- **Lệnh gán vào khối theo `open_date`** (quyết định vào lệnh xảy ra trong khối đó). Nửa mở `[a, b)`.
  Lệnh có `open_date` ngoài `[T1, T2)` ⇒ **raise** (lỗi nối dữ liệu, không lặng lẽ bỏ).
- **Tổ hợp:** mọi cách chọn 4/8 khối làm IS, 4 còn lại làm OOS ⇒ **C(8,4) = 70**.

### 4.2 Chỉ số xếp hạng

- **Trung bình `R_trien_khai`** của các lệnh thuộc nửa đó, với `R_trien_khai = pnl_abs / rui_ro_da_trien_khai`
  (`DR-D4-12` §1 — đơn vị phán quyết Nhánh 1; `R_realized` báo cạnh bên, không xếp hạng).
- 🔴 **Đính chính so với kế hoạch đã duyệt:** kế hoạch ghi *"mean `R_realized`"*. `DR-D4-12` §1 (14/09) đã
  chuyển đơn vị phán quyết sang `R_trien_khai`; xếp hạng CSCV bằng một đơn vị khác với đơn vị gate đọc là
  hai thước cho một câu hỏi (`MT-03`). ✅ **Chủ dự án xác nhận `R_trien_khai` ngày 17/09/2026.**
- Cấm `profit_ratio` (DR-013, L-Z46). Cấm nhãn "R" trần (L-Z48c).
- **Vì sao trung bình theo lệnh, không phải Sharpe theo kỳ:** lệnh thưa (mỗi khối vài chục lệnh), chuỗi
  lợi nhuận theo ngày phần lớn là 0; gate §10.2 phán quyết bằng expectancy — xếp hạng cùng đại lượng.

### 4.3 Công thức

Với mỗi tổ hợp `c` và `N_c` cấu hình phân biệt (sau gộp §2):

```
IS-best   n* = argmax_n  mean_R_IS(n)
ω̄_c       = hạng_OOS(n*) / (N_c + 1)       hạng 1 = kém nhất, N_c = tốt nhất; hoà ⇒ hạng trung bình
λ_c       = ln( ω̄_c / (1 − ω̄_c) )
PBO       = #{ c : λ_c ≤ 0 } / 70
```

- **Hoà ở đỉnh IS** (nhiều cấu hình cùng max) ⇒ `λ_c` = **trung bình λ** của các cấu hình cùng đỉnh. Không
  chọn theo thứ tự tên/khoá — đó là phá hoà tuỳ ý, và kết quả phụ thuộc cách đặt tên.
- `λ_c ≤ 0` ⇔ cấu hình tốt nhất IS rơi **xuống bằng hoặc dưới trung vị** OOS.

### 4.4 Sàn mẫu — không thêm con số mới

- Dùng lại **`tier_c.wfo_folds.san_lenh_moi_fold` = 30** (`DR-D3-01` §5.2).
- Một cấu hình có **< 30 lệnh** ở nửa IS **hoặc** nửa OOS của tổ hợp `c` ⇒ tổ hợp `c` = `unreadable`.
- **PBO là SỐ chỉ khi 70/70 tổ hợp đọc được.** Ngược lại `PBO = unreadable` ⇒ tiêu chí PBO không thoả ⇒
  D9 không PASS (fail-closed, N6). **Cấm** tính PBO trên phần tổ hợp đọc được — bỏ tổ hợp theo số lệnh là
  chọn mẫu sau khi dữ liệu đã chạy.
- ⚠️ **Giá của chốt này, khai trước:** một ứng viên D5 cực thưa lệnh (ví dụ `zss_threshold = 0,6` hay
  `v_min = 1,5` lọc mạnh) có thể làm PBO không bao giờ là số. Kết cục đó **đúng hướng**: CSCV không có power
  trên tập đó, và §6 xử nó thành INCONCLUSIVE, không phải PASS. Nếu xảy ra, đường sửa là một DR mới **trước
  khi** nhìn λ nào (§8), không phải hạ sàn.

### 4.5 Khối băm

`TD-0281` đối chiếu `config/tool_d_config.yaml` và hằng số của `gates/cscv.py` với khối dưới; `TD-0282`
đọc khối qua cùng quy tắc chuẩn hoá của `DR-D5-01` §3.3:
`json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)` rồi `sha256` trên bytes UTF-8.

<!-- DR-D9-01:CSCV:BEGIN -->
```json
{"arm":"Z0-T1","budget_line":"B1","cscv":{"chi_so_xep_hang":"mean_R_trien_khai","do_dai_khoi_gio":693,"gan_lenh_theo":"open_date","hoa_dinh_is":"trung_binh_lambda","hoa_oos":"hang_trung_binh","pbo_max":0.5,"san_lenh_moi_nua":"tier_c.wfo_folds.san_lenh_moi_fold","so_khoi":8,"to_hop_doc_duoc_toi_thieu":"tat_ca"},"dataset":"WFO","dr":"DR-D9-01","huong":"LONG"}
```
<!-- DR-D9-01:CSCV:END -->

`sha256 = 7f8c5ff03bd2b8aefa997d8ea9ac382690d13f0b105908c727cd4c1a933260bb`

---

## 5. Cách chạy — một lượt toàn cửa sổ mỗi cấu hình, rồi cắt lát

```
mỗi cấu hình trong tập §2:
   reserve(B1, WFO)                       ← TRƯỚC khi đọc dữ liệu (L-Z52)
   seal
   backtest [T1, T2)  --timeframe-detail 5m, file cấu hình phủ (N4, TD-0255)
   consume
   ├─ cắt theo open_date vào 3 đoạn test fold  → Nhánh 1 (MT-36, n_chi_test)
   └─ cắt theo open_date vào 8 khối           → CSCV (§4)
```

- **Một cấu hình = một tập lệnh.** Chạy riêng từng fold rồi chạy thêm một lượt toàn cửa sổ sẽ cho **hai**
  tập lệnh lệch nhau ở biên fold, tức Nhánh 1 và PBO đọc hai bộ số khác nhau. Chủ dự án chọn cắt lát.
- **Giá phải trả, khai trước:** lệnh mở ở fold trước chiếm chỗ `max_open_trades` sang fold sau — giống live
  thật, khác thiết kế H3-D "mỗi fold một backtest độc lập". `chay_mot_fold` của `wfo/orchestrator.py` trở
  thành **bộ cắt lát** trên một lượt chạy, không phải một lượt backtest.
- **L-Z47** (cân đối số dư) kiểm trên **cả lượt**; **L-Z55** kiểm ngày quan sát thật của lượt; ngày lệnh
  đọc từ dataframe/kết quả backtest, **không** từ lời khai của bộ chạy (`d3_han_che`, nhãn `nguoi-khai`).
- Sổ trial ghi CẤU HÌNH; test của bộ chạy phải chứng minh đổi file phủ ⇒ **tập lệnh thật đổi** (`MT-23`).
- `chay_wfo` coi một fold dưới sàn là cả chuỗi `unreadable` (`MT-36` phần còn mở) — **giữ nguyên**, không
  sửa trong khối này.

### 5.1 🔴 ĐÍNH CHÍNH 17/09/2026 — D9 KHÔNG đi qua `chay_wfo` (chữ gạch dưới đây giữ làm lịch sử)

> ~~`chay_mot_fold` của `wfo/orchestrator.py` trở thành **bộ cắt lát** trên một lượt chạy~~

**Vì sao câu đó sai — lộ ra khi viết TD-0283, trước dòng mã nào của bộ chuyển:** `chay_wfo` gọi
`kiem_pham_vi_du_lieu()` tầng (b) (TD-0148) cho TỪNG fold, đòi `observed_end ≤ test_end − 1 ngày` của chính
fold đó. Một lượt toàn cửa sổ đọc tới `T2` ⇒ fold 1 và fold 2 bị từ chối. Bộ chuyển chỉ qua được bằng cách
**khai** ngày giả — đúng bẫy "lời khai" TD-0148 sinh ra để chặn. Hai quyết định chạm nhau (quy tắc 11):
§5 (một lượt, cắt lát) và TD-0148 (L-Z55 tầng b theo fold).

✅ **Chủ dự án chốt 17/09/2026: giữ "một lượt, cắt lát"; D9 KHÔNG đi qua `chay_wfo`.**
- D9 cắt lát trực tiếp bằng `wfo/lenh.py` (`cat_lat_theo_fold`, `cat_lat_theo_khoi`).
- **L-Z55 tầng (a)** (biên WFO `[T1, T2]`) và **L-Z47** kiểm trên **cả lượt**, ngày đọc từ dataframe thật.
- Không ghép đường vốn theo fold (một lượt đã là một đường vốn liên tục).
- `chay_wfo` và tầng (b) **giữ nguyên, không nới** — vẫn đúng cho thiết kế mỗi-fold-một-backtest.
- **Vì sao bỏ tầng (b) ở D9 là an toàn, không phải nới:** tầng (b) chặn rò dữ liệu tương lai giữa các fold
  khi fold SAU dùng kết quả KHỚP trên fold TRƯỚC. D9 không khớp tham số nào theo fold (`DR-D3-01` §2), và
  backtest nhân quả (H4-D; `lookahead-analysis` thật ở TD-0106) ⇒ lệnh trong đoạn test không đọc được nến sau nó. Tức mối đe doạ tầng (b)
  canh không tồn tại trên đường này. 🔴 Nếu D9 về sau khớp bất kỳ thứ gì theo fold, lập luận này hết đúng.

---

## 6. Cổng D9

### 6.1 Cổng vào (điều kiện được đặt chỗ suất WFO đầu tiên)

- **`d5_complete`** (TD-0257) — bắt buộc, máy kiểm tại cửa `reserve()`.
- **Cổng các pha D6–D8** nếu và khi `DR-D6D8-01` được chủ dự án chốt. Phiên `-01` đề xuất
  `d7_complete` (ngụ ý `d6`) + `d8_complete`, với lý do: D6 sửa `MT-30` (đổi số — sửa sau D9 là chạy lại
  WFO bằng suất mới) và chốt DR-007 (quyết định `N` của D9). DR này **không** ghi các khoá đó thành điều kiện
  vì chúng **chưa tồn tại và chưa chốt**; ghi một khoá không ai sinh ra là tạo một cổng không bao giờ mở
  được. ✅ **Chủ dự án chốt 17/09/2026: tạm chỉ `d5_complete`.** **Điều kiện mở lại:** khi `DR-D6D8-01` chốt, sửa §6.1 bằng một đính chính tại chỗ **trước** suất WFO
  đầu tiên.
- Bất kỳ thay đổi tham số nào **sau** khi D9 đã tiêu suất (D6–D8, DR-012 Hạng 1 đổi số) ⇒ kết quả D9 hết
  hiệu lực; chạy lại bằng **suất mới** (không hoàn trả, DR-014).

#### 6.1.1 🔴 ĐÍNH CHÍNH 17/09/2026 — cổng vào là `d5` + `d6` + `d7` + `d8` (các gạch trên giữ làm lịch sử)

> ~~✅ Chủ dự án chốt 17/09/2026: tạm chỉ `d5_complete`.~~ — đúng tại thời điểm viết, hết hiệu lực theo
> chính điều kiện mở lại ghi ở gạch đầu dòng trên.

`DR-D6D8-01` đã **CHỐT** (`7428678`, §6 dòng 236 + §8): chủ dự án chọn **ĐỢI** — loại *"chạy song song"* và
*"chỉ đợi D6"*. Cổng vào D9 từ nay:

| Khoá | Sinh bởi | Vì sao chặn D9 |
|---|---|---|
| `d5_complete` | TD-0257 | Tập CSCV là các cấu hình D5 đã CONSUMED (§2) |
| `d6_complete` | TD-0267 | D6 sửa `MT-30` (đổi số) và đo overlap H14 ⇒ `N` của D9 (§3) |
| `d7_complete` | TD-0273 (đòi `d6_complete`) | Hardening tồn vong — lỗi Hạng 1 lộ ra ở D7 đổi số |
| `d8_complete` | TD-0279 | Ngưỡng lockbox commit **trước** suất WFO đầu tiên |

- **Máy kiểm CẢ BỐN khoá tại cửa `reserve()`** (nhánh WFO, TD-0284 bổ sung). `DR-D6D8-01` viết *"`d7` ngụ ý
  `d6`"* — đúng theo chuỗi cổng TD-0273 → TD-0267, nhưng cửa sổ trial **không tin một hàm ý**: kiểm `d6`
  tường minh chặt hơn chữ, không trái chữ.
- **Không thành cổng-không-bao-giờ-mở:** ba khoá mới đều có việc sinh ra chúng trong `TASKS.md` (Khối 20–22).
  Trong lúc chờ, cửa từ chối với lý do đọc được, sổ không thêm dòng nào — đó là hành vi ĐÚNG của "đợi".
- 🔴 **Đọc đúng tiến độ (phiên `-30`):** cửa B1/WFO xong **không** có nghĩa D9 sắp chạy được. Đường găng thật
  là **năm hàm đóng cổng xếp nối tiếp, ngày 17/09 chưa hàm nào tồn tại**: `close_d4_gate` (TD-0186) →
  `close_d5_gate` (TD-0257) → `close_d6_gate` (TD-0267) → `close_d7_gate` (TD-0273) + `close_d8_gate` (TD-0279).
- 🔴 **CẤM ghi tay bất kỳ khoá `d5…d8_complete` nào vào `registry/runtime_state.json`** để gỡ chặn — kể cả
  "tạm", kể cả "chỉ để thử bộ chạy". Mỗi khoá chỉ được sinh bởi hàm `close_dN_gate` tương ứng, và hàm đó
  **phải kiểm tiêu chí máy trước khi ghi** (cây sạch, pytest thật, PASS ≥ 1 — khuôn `close_d3_5_gate`). Lý do
  chính là cảnh báo của `OQ-11`: một hàm chỉ ghi `true` khi được gọi, hay một dòng JSON gõ tay, là *"lời khai
  của người trông như bằng chứng máy"*. Test bộ chạy dùng `runtime_state` giả trong `tmp_path`, không dùng file thật.
- **`MT-49` chốt:** lockbox chạm ở **D9.5**, khớp §1 *"Không thuộc D9: chạm LOCKBOX"* (đính chính tại chỗ ở
  `DR-D0PRE-07` mục 6, phiên `-01`).

### 6.2 Tiêu chí phán quyết

- **Nhánh 1 §10.2** trên cấu hình D5 đã chọn (mốc, hoặc cấu hình ghép nếu xác nhận thắng), `n` = lệnh trong
  đoạn test (`MT-36`), rào DSR theo `N` hiện hành (§3), **cộng PBO ≤ 0,5 là tiêu chí CHẶN (P0)**.
- Kết cục theo **DR-011**: PASS / INCONCLUSIVE / FAIL — "không vào D9.5" **không** đồng nghĩa "dừng dự án".
- `PBO = unreadable` (§4.4) hoặc `pending` ⇒ tiêu chí PBO không thoả ⇒ tối đa INCONCLUSIVE.
- 🟡 **Khai thẳng (`MT-53`):** *"skewness(cấu hình tốt nhất) không âm hơn skewness(Z1) quá 0,5"* đang
  `pending` vì `Z1` bị cắt (`DR-D4-12` §4.5) ⇒ **Nhánh 1 chưa PASS trọn được ở D9** với chữ hiện tại. Phải
  giải trước go-live; **không** giải trong khối này, **không** lặng lẽ bỏ tiêu chí.

### 6.3 Khoá `d9_complete`

- `close_d9_gate()` trong E6 (`--close-d9-gate`), khuôn `close_d3_5_gate()`: đòi cổng vào §6.1 · cây sạch
  **trước** suite · full suite · chạy RIÊNG từng file test lõi, PASS ≥ 1 · gọi **cùng hàm** phán quyết mà E2
  dùng (điều kiện đóng cổng và điều kiện chạy là một) · hiện vật D9 hợp lệ.
- Ghi `d9_complete`, `d9_closed_at`, `d9_git_sha`, `d9_cay_sach`, `d9_evidence{nguon: do-duoc}`,
  `d9_ket_cuc`, `d9_han_che{nguon: nguoi-khai}`. Chạy lại ⇒ exit 94.
- **Mở lại `OQ-11`:** OQ-11 xếp D5–D9 là pha không khoá máy. D9 cần khoá vì `L-Z13` (`:3876`) đòi 0 bản ghi
  lockbox *"cho tới sau D9"* — không có khoá thì "sau D9" là lời khai.
- `d9_complete` ghi **kết cục** (kể cả INCONCLUSIVE/FAIL) — khoá chứng nhận **D9 đã đo xong đúng quy
  trình**, không chứng nhận PASS. Việc D9.5 được chạm lockbox hay không đọc `d9_ket_cuc`, là việc của D9.5.

---

## 7. PBO ở D4 — ghi số, không chặn (`MT-51`)

- `evaluate_branch1()` nhận tham số **bắt buộc, không mặc định** `pbo_chan: bool`. D4 (TD-0185) gọi với
  `False`: PBO vẫn báo, **không** vào `failed_criteria`. D9 gọi với `True`.
- Không mặc định ⇒ người gọi phải **khai tường minh**; một lời gọi quên khai là lỗi, không lặng lẽ chọn
  một phía.
- `tests/lock/test_lz35_gate_fail_closed.py`: ca hiện có giữ **nguyên khẳng định 7 tiêu chí** dưới
  `pbo_chan=True`; thêm ca `False` ⇒ 6. Đổi nhãn, không nới.
- Căn cứ phân loại: code lệch spec, spec thắng (N1), sửa kiểu DR-012 Hạng 1 — `evaluate_branch1` chưa có
  người gọi sản xuất nào, nên không kết quả cũ nào đổi.

---

## 8. Cấm và điều kiện mở lại

**Cấm, sau khi đã tồn tại bất kỳ `λ` nào trên WFO:** đổi S · đổi độ dài khối hay mốc khối · đổi luật gán
lệnh · đổi chỉ số xếp hạng · đổi sàn · tính PBO trên tập con tổ hợp · thêm/bớt cấu hình khỏi tập §2 · đổi
luật hoà · chạy lại một cấu hình *"vì nghi ngờ"* bằng B1.

**Muốn đổi bất kỳ mục nào ở trên:** DR mới **trước khi có số**, đi qua `L-Z26`
(`param_change_proposals.jsonl`), sửa khối băm §4.5 **và** dòng băm cùng một commit.

**Điều kiện mở lại viết trước:**
1. `DR-D6D8-01` chốt cổng hoặc đổi `N` ⇒ sửa §6.1 / §3 bằng đính chính tại chỗ, trước suất WFO đầu tiên.
2. D5 kết thúc với < 2 cấu hình phân biệt ⇒ PBO không đo được theo DR này ⇒ trình chủ dự án trước khi tiêu
   suất WFO nào (chạy Nhánh 1 cho một cấu hình vẫn có nghĩa; CSCV thì không).
3. Chu trình Short mở ⇒ DR riêng; không kế thừa tập cấu hình Long.

---

## 9. Hạn chế khai TRƯỚC — chép vào `d9_han_che` khi đóng cổng

- **Chỉ LONG.** PBO Short `pending`.
- **PBO đo luật argmax**, không đo đúng luật *"giữ mốc trừ khi thắng rõ"* của D5 (§2) — cận trên thô.
- **Tập cấu hình là biến thể một-tham-số quanh mốc** — tương quan cao giữa các cấu hình; PBO có xu hướng
  **thấp** hơn trên tập cấu hình giống nhau (thứ hạng nhiễu nhưng chênh lệch nhỏ). Không đọc PBO thấp như
  bằng chứng mạnh.
- **Cùng cửa sổ WFO đã được D4 dùng để chọn `Z0-T1`** (`DR-D4-11`, toàn cửa sổ) — WFO không còn là dữ liệu
  chưa nhìn thấy đối với lựa chọn arm. Chỉ LOCKBOX (D9.5) sạch.
- **Lệnh chiếm chỗ qua biên fold** (§5).
- **Skewness vs Z1 `pending`** ⇒ Nhánh 1 chưa PASS trọn (§6.2, `MT-53`).

---

## 10. Phương án đã LOẠI

| Loại | Vì sao |
|---|---|
| Mở lại `DR-D3-01`, thêm fold | 33 tuần không chứa fold thứ tư; rolling tối đa 5 < 8; kéo dài = dời `T2` vào LOCKBOX |
| S = 16 | ~14 ngày/khối, nửa IS/OOS mỏng ⇒ phần lớn tổ hợp dưới sàn; 12.870 tổ hợp không thêm thông tin khi lệnh thưa |
| CSCV trên 4 arm D4 | Chọn sai đối tượng (lựa chọn cuối là của D5); `Z0` ≡ `Z3` ⇒ 3 phần tử |
| Chạy lại 9 arm D4 với tham số D5 | 9 suất; 5 arm đã cắt (`DR-D4-12` §4); arm lồng nhau |
| Gộp arm D4 + biến thể D5 | ~20 suất; trộn hai lựa chọn khác nhau vào một thứ hạng |
| Trả bằng B2 | Chỉ 9 suất chưa gán < 16 |
| Mở rộng `N` (dòng B4) | Nâng rào DSR cho một phép đo mà 72 suất B1 đăng ký dư chỗ; sửa mọi chỗ ghim 114 |
| Mỗi fold một backtest + lượt toàn cửa sổ | Hai tập lệnh cho một cấu hình (§5) |
| Sharpe theo kỳ | Chuỗi ngày phần lớn bằng 0; lệch đơn vị với gate expectancy |
| PBO trên tổ hợp đọc được | Chọn mẫu theo số lệnh sau khi chạy |
| Phá hoà IS theo tên cấu hình | Kết quả phụ thuộc cách đặt tên |
| Ghim `N = 114` ở tầng D9 | DR-007 union có thể đổi `N` (§3) |

---

## 11. Thi hành

| Mã | Việc | Đầu vào từ DR này |
|---|---|---|
| `TD-0280` | DR này | — |
| `TD-0281` | Khoá `tier_c.cscv` trong YAML (N4) + đối chiếu khối băm §4.5 + DOF | §4.5 |
| `TD-0282` | `gates/cscv.py` hàm thuần `tinh_pbo` | §2 gộp · §4 |
| `TD-0283` | `wfo/lenh.py` bản ghi từng lệnh + cắt lát fold/khối (không có bộ chuyển `chay_mot_fold` — §5.1) | §5 · §5.1 |
| `TD-0284` | Cửa B1 `dataset = WFO` tại `reserve()` — nhãn (a) `B1` + `dataset`, sửa `ung_vien.py:185` + `audit_checks.py:275` | §3 · §3.1 · §6.1 |
| `TD-0285` | `evaluate_branch1(..., pbo_chan)` + `gates/d9_gate.py` | §6.2 · §7 |
| `TD-0286` | Bộ chạy D9 trên E2 `run_wfo.py` | §5 · §6.1 |
| `TD-0287` | `close_d9_gate()` + `d9_han_che` | §6.3 · §9 |
| `TD-0288` | Chạy D9 thật | toàn bộ |

🔴 Quy tắc gốc 1: `TD-0281…TD-0288` chỉ bắt đầu khi chủ dự án gõ **"bắt đầu code"**.
