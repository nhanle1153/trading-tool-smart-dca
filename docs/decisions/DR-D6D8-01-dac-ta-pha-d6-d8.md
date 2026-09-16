# DR-D6D8-01 — Đặc tả pha D6, D7, D8 (khoảng giữa calibration D5 và walk-forward D9)

> 🔴 **BẢN NHÁP — CHƯA CHỐT.** Chưa có hiệu lực chừng nào còn một ô `__CHUA_DIEN__` (§8).
> **Ngày soạn:** 17/09/2026 · **Phiên:** `-01` · **Người quyết:** chủ dự án (hai câu đã trả lời 17/09, §1)
> **Mở lại:** (1) quyết định *"dựng testnet trước, HOÃN đặc tả D5–D9"* ngày 13/09/2026 (đoạn mở
> Khối 18, `TASKS.md`); `DR-D5-01` §0 đã mở lại phần D5; DR này mở lại phần **D6–D8**. (2) Câu
> *"D6–D9 vẫn hoãn"* trong ô giải của `MT-48` (`back-end-note.md`). Quyết định mới hơn, cùng người
> quyết. Khai đích danh để repo không có hai câu cùng đứng và ngược nhau (hình `MT-38`). **Không** đảo
> thứ tự ưu tiên testnet/Khối 18; D9 vẫn hoãn **ở DR này** (phiên `-33` đặc tả riêng bằng `DR-D9-01`).
> **Kế toán:** toàn bộ D6–D8 = **0 trial** (§2).
> Đã nhắn hai phiên `-33` (đang làm D9) và `-30` tên `DR-D6D8-01` + dãy `TD-0260…TD-0279` +
> `MT-49…MT-50` + Khối 20–22 **trước** khi mở file (N12 mục 6). Va chạm mã với `-33` đã giải:
> `-33` dời sang Khối 23 / `TD-0280…TD-0288` / `MT-51…MT-53` / `DR-D9-01`.

> ⚠️ **BẪY KÝ HIỆU — đọc trước:** trong DR này **D6, D7, D8 là tên PHA lộ trình** (PHẦN 12). Spec
> §9b.2 dùng **cùng ký hiệu** cho **GIẢ ĐỊNH**: *D6* = `adjust_trade_position` đánh giá tại giá mở nến
> (lệch khớp tranche), *D7* = `trade.custom_data` ổn định. Hai thứ không liên quan. Mọi chỗ nhắc giả
> định trong file này đều ghi rõ chữ *"giả định"*. Vì bẫy này, DR **không** dùng tên kiểu `DR-D7-01`
> (dễ đọc thành *"DR về giả định D7"*); tên `DR-D7-01` báo các phiên hôm 17/09 **bỏ, không dùng**.

---

## 0. Vì sao cần DR này

`tool-d-smart-dca.md:4492` chỉ ghi `D5–D9 (giữ nguyên) Tuần 9–17`. Bản tài liệu mà dòng này "giữ
nguyên" **chưa bao giờ nằm trong git**: spec có đúng một commit (`9c3d585`), `git log -S` chỉ ra các
commit *trích* dòng 4492. Đã rà repo Tool A, `template/`, `dashboard-ui/`, và không nơi nào định nghĩa
D6, D7, D8. `DR-D5-01` đã đặc tả D5. Phiên `-33` đang đặc tả D9 (`DR-D9-01`). **D6–D8 là khoảng trống
duy nhất còn lại** giữa ② *đã calibrate* và ③ *đã WFO* (`spec:4526-4530`).

Không đặc tả thì đường mặc định là nhảy D5 → D9. Ba hậu quả của đường đó:

1. D9 chấm một hệ thống **khác** hệ thống sẽ chạy live. Các hạng mục hardening H2, H5, H14 chưa bao giờ
   được xác minh trên cấu hình cuối.
2. Các cầu dao Cấp C (§12c.3) chưa từng bị thử ở đòn bẩy 3x trên cấu hình cuối. `L-Z3` (đệm thanh lý)
   chỉ thành thật từ TD-0187; trước đó mọi backtest đều chạy 1x.
3. Ngưỡng lockbox bị điền **sau khi đã thấy số WFO**. `spec:3324-3326` cấm: *"Phải điền đầy đủ và
   commit TRƯỚC lần chạm duy nhất"*.

### 0.1. Dấu vết còn lại trong spec — D6–D8 phải khớp

| Neo | Chữ | Ràng buộc lên thiết kế |
|---|---|---|
| `spec:279` | *"B7 chặn D7. Nhưng KHÔNG chặn D4"* | D7 là pha mà cơ chế đóng vị thế theo thời gian **phải đã đúng**. Đây là **pha**, không phải giả định: cùng câu đặt D7 cạnh *"D4 — D0.9 phải chạy CÓ DG8"*, và D0.9 là pha ablation |
| `spec:1491-1494` | *"không đợi D7"*, *"thêm sau ở D7"* | Bản lộ trình cũ đặt việc hoàn thiện các cổng thoát ở D7 |
| `spec:2932` | *"D9 (Walk-forward + GATE)"* | D9 là phán quyết; D6–D8 là **chuẩn bị**, không phán quyết |
| `spec:4326`, `:4349` | PBO/CSCV thành P0 ở *"GATE TOOL D (D9)"* | Tiền đăng ký PBO là việc của D9 (`DR-D9-01`), không lặp lại ở đây |
| `spec:4526-4530` | ② calibrate (D4/D5) → ③ WFO (D9) | D6–D8 **không** sinh trạng thái tham số mới ⇒ 0 trial |
| `spec:3876` | `L-Z13`: 0 bản ghi lockbox *"cho tới sau D9"* | D6–D8 không chạm lockbox |
| §11 (`spec:4336-4352`) | **H2, H5, H9/H10, H14 không được gán pha nào** | Đây là phần ruột của D6–D8 |
| Tool A `tool-a-v10-full-spec.md:5171-5176` | A1-c chiến lược đầy đủ → A1-d 5m (H5) → A1.5 shadow → A1.7 stress thanh lý (H10) | Cùng khuôn "v10 gốc" mà `spec:4354` nói Tool D thừa kế. **Suy luận, không phải bằng chứng** |

---

## 1. Hai quyết định của chủ dự án (17/09/2026)

### 1.1. Long-only tới live

D6–D8 chỉ làm hướng LONG, nối tiếp `DR-D4-01` và `DR-D5-01` §1. Short thành **một chu trình riêng về
sau**: D3.5-Short → D4-Short → D5-Short → WFO → **lockbox MỚI**.

🔴 **Giá phải trả, ghi để không ai tưởng là miễn phí.** `DR-011` (`spec:3335-3337`): *"MỘT LẦN CHẠM =
MỘT PHIÊN CHẠY DUY NHẤT, sinh HAI bộ metric (Long và Short)"*. Mang cấu hình Long-only ra lockbox
`[T2,T3]` thì lần chạm duy nhất đó **tiêu luôn cho Short**. Short về sau phải chờ dữ liệu mới rồi niêm
phong đoạn `[T3_cũ … T3_mới]`, cùng cơ chế với nhánh INCONCLUSIVE của DR-011.

Căn cứ chọn: `Δ_R(SHORT)` vẫn là `"unreadable"` (`runtime_state.json.d3_5_delta_r_niem_phong`). Short
cần DG7 cùng ngưỡng riêng (`spec:1162`). Theo `DR-D5-01` §1, nửa B1 của Short không chuyển sang Long,
nên chu trình Short vẫn còn ngân sách của nó. Đuổi kịp Short trong D6–D8 thì tốn thêm khoảng 4 suất B2
và ≤ 16 suất B1, kéo dài nhiều tuần, trong khi Long còn chưa qua D4.

### 1.2. D7 dùng kịch bản tổng hợp + dòng CTRL

Stress test dùng **kịch bản giá dựng tay**: không chạm dữ liệu, 0 trial. Phần cần dữ liệu lịch sử
(tần suất kích hoạt DG6/DG7/DG8) chạy trên CALIB dưới dạng **dòng CTRL**. Đầu ra chỉ gồm chỉ số an toàn,
**không có expectancy**. Cách ghi sổ: §4.3.

---

## 2. Nguyên tắc chung của D6–D8

| # | Nguyên tắc | Vì sao |
|---|---|---|
| P1 | **0 trial.** Không `reserve()` nào ở B1/B2/B3 | Mỗi suất tiêu thêm hoặc làm tăng N (nâng rào DSR), hoặc là một lần thử cấu hình thứ hai. B3 để dành cho lúc live (§12c.2) |
| P2 | **Không chạm WFO `[T1,T2]`, không chạm LOCKBOX `[T2,T3]`** | WFO thuộc D9 (`DR-D9-01`). Phiên `-33` đã báo D9 dùng phần B1 dư trên chính cửa sổ này. Hai pha cùng chạm thì tranh cùng một thông tin |
| P3 | Dữ liệu được dùng: **EXPLORE** (§9c.4b, 0 trial), **kịch bản tổng hợp**, **CALIB qua dòng CTRL** (đầu ra có danh sách cho phép) | DR-014 §2: "chạm" = đánh giá cấu hình. Đo mô tả không phải đánh giá |
| P4 | **Không thêm biến thể cấu hình.** Ablation DG8 (+2 suất, `spec:1500-1504`), Short, FreqAI (`DR-FAI-01`) đều **ngoài** D6–D8 | Đưa biến số mới vào đúng lúc cần đóng băng |
| P5 | **Lỗi code phát hiện được sửa ngay** theo DR-012 Hạng 1 (0 trial). **Mọi thay đổi giá trị tham số thì không** | `spec:4651-4676`. Sửa lỗi làm đổi số thì D9 phải chạy **sau** bản sửa |
| P6 | **Mỗi pha một cổng máy**: `d6_complete` / `d7_complete` / `d8_complete` + tag, khuôn `close_d3_5_gate()` (kiểm cây sạch TRƯỚC suite, chạy riêng file test lõi, PASS ≥ 1). Cờ nằm trên **E6**, không thêm entrypoint thứ 9 (`L-Z36`) | Bài học cổng D1/D2/D3: sha không có cây sạch thì không truy lại được |

---

## 3. D6 — Niêm phong ứng viên & xác minh đúng hệ thống cuối

**Mục tiêu:** D9 chấm **đúng một** cấu hình, và đó đúng là thứ sẽ chạy live. **Đòi:** `d5_complete`.

| # | Việc | Dữ liệu / kế toán | Căn cứ |
|---|---|---|---|
| D6.1 | **H14 + DR-007 — chốt N của D9 TRƯỚC D9.** Đo overlap giữa rổ pool Tool D (sau TD-0247) và pool Tool A, rồi áp DR-007 **máy móc**: dưới ngưỡng thì N tách; từ ngưỡng trở lên thì N = UNION với sổ trial Tool A tại thời điểm chạy cổng. Ghi research-log. **Không** quay lại đổi tiêu chí pool | Chỉ danh sách mã, 0 trial. Chưa từng đo: grep `H14` / `DR-007` chỉ ra `DR-D0PRE-02:51` | `spec:2818-2857`, `:4267-4268`. ⚠️ Ngưỡng tự mâu thuẫn, xem §9 |
| D6.2 | **Kiểm kê DOF sau D4/D5.** Bỏ DCA làm chết DG5 và một phần DG1–DG4. Thêm `MT-44`: DG1–DG5 không bao giờ được xét trên `Z0-T1`. **Chỉ ghi** research-log, **không** hạ N của D9 | 0 trial | `spec:4314-4316`: *"HẠ N cho vòng sau … không tự động áp"* |
| D6.3 | **`MT-30` có chạm `Z0-T1` không — ĐO, không suy.** `MT-30` là lỗi của DCA-xuống (`p_avg` tụt khi tranche 2/3 khớp). `Z0-T1` là đơn tranche nên *dự kiến* `p_avg` bất biến và lỗi không chạm, nhưng đó là suy luận. Chạm thì sửa Hạng 1 trước D9; không chạm thì ghi `MT-30` là N/A cho arm sản xuất, **vẫn** là nợ của chu trình DCA | EXPLORE, 0 trial | `back-end-note.md` `MT-30` |
| D6.4 | **H5 — `timeframe-detail 5m` trên cấu hình cuối.** Xác minh swing 4H và tín hiệu không lệch do intrabar: so tập lệnh có/không detail, và soi các lệnh lệch | EXPLORE, 0 trial. Cần TD-0252 (5m phủ CALIB) | `spec:4342` (H5, P0, chưa gán pha) |
| D6.5 | **H2 — danh mục ràng buộc thật.** Trên backtest cấp rổ pool mới: kết nạp §6.8f (TD-0188 ✅) · `mult_corr` · `mult_deploy` có **lần nào** ràng buộc không; phân bố số vị thế đồng thời; tỉ lệ lệnh bị từ chối vì danh mục. Bằng chứng "có răng": phá cổng thì số lệnh đổi | EXPLORE, 0 trial | `spec:4339`, §6.8f. Cùng lớp lỗi "cổng không bao giờ ràng buộc" với `MT-44` |
| D6.6 | **Niêm phong cấu hình ứng viên.** `config_hash` + `params_frozen_hash` + git sha của `Z0-T1` LONG mang giá trị D5 → `runtime_state.json.d6_ung_vien`. Bất biến, từ chối ghi đè (khuôn `src/tool_d/lockbox/seal.py`) | 0 trial | Làm SAU D6.3 và D6.5: nếu một trong hai sửa code thì hash đổi |

**Cổng D6:** `d5_complete` · `d6_ung_vien` tồn tại · N của D9 đã ghi kèm kết quả DR-007 · báo cáo
H5/H2 có artifact `docs/du-lieu-do/` · `MT-30` có kết luận đo được.

**Ngoài phạm vi D6:** đổi bất kỳ giá trị tham số nào; chạy `Z0-T1` trên CALIB/WFO để xem lãi lỗ.

---

## 4. D7 — Hardening tồn vong ("B7 chặn D7")

**Mục tiêu:** chứng minh mọi cầu dao Cấp C (§12c.3) **thật sự nổ** ở `L_exchange = 3` trên cấu hình
`d6_ung_vien`. D7 **không** hỏi *"lời bao nhiêu"*. **Đòi:** `d6_complete`.

### 4.1. Stress thanh lý — H9/H10 (`spec:4344`)

- **Dải `R_eff` lấy từ đo thật, không lấy dải thiết kế 0,9–3,0%.** `TD-0191` đã chứng minh dải thiết kế
  chứa một chế độ không tồn tại: min đo được 1,303%, median 3,028%. Dải dùng cho D7 phải đo lại trên
  `d6_ung_vien` (EXPLORE).
- **Kịch bản tổng hợp** (`__CHUA_DIEN__` biên độ cụ thể, xem §8):
  - gap xuyên SL trong một nến 5m;
  - wick cực đoan chạm vùng thanh lý rồi hồi;
  - funding cực đoan kéo dài;
  - nhiều mã tương quan cùng vào lệnh trong một nến 1H.
- **Tiêu chí:** `liq_buffer_ratio ≥ 8` (§6.4b) và `max_single_trade_loss / risk_budget ≤ 1.15` ở **mọi**
  kịch bản. Kịch bản làm vỡ tiêu chí là **phát hiện**, không phải thất bại của pha. Ghi nhận rồi xử theo
  §11b.1 (L1/L2); **không** tinh chỉnh tham số ngay trong D7.

### 4.2. Thang drawdown 5/8/20% (§12c.5)

- Chạy lại trên **chuỗi equity tổng hợp**, qua đúng đường sản xuất (`ZoneAbsorption._dd_pct()` +
  `equity_peak.py` của TD-0238 + Risk Supervisor của TD-0241):
  - `mult_dd` 1,0 → 0,5 → HALT;
  - điều kiện khởi động lại sau HALT: mọi vị thế đóng, 2 × `max_hold_bars`, một dòng research-log;
  - nửa size tới khi drawdown ≤ 5%;
  - trần 3 HALT / chu kỳ 100 lệnh, lần thứ 4 = ABORT;
  - vượt 20% = ABORT.
- **`MT-40` phần còn mở:** *"đỉnh equity reset khi nào"* là một tham số chưa ai đếm vào kiểm kê DOF.
  D7 phải có câu trả lời của chủ dự án, hoặc chứng minh TD-0238 đã giải phần đó.
- 🔑 Phép kiểm phải chạy qua **đường sản xuất**, không qua mẫu dựng tay. Đây là câu chẩn đoán của rà
  soát 08/09: *"ca sai có đi qua đường sản xuất thật không?"*

### 4.3. DG6/DG7/DG8 trên dữ liệu thật — dòng CTRL *đo mô tả*

- 🔴 **Đính chính so với kế hoạch đã duyệt:** kế hoạch ghi *"DR mở rộng `CTRL_OUTPUT_ALLOWED`"*. Làm thế
  **trái `MT-19`**, vì chủ dự án đã chốt ngày 14/09/2026 đường (c): thêm **dạng CTRL thứ ba (đo mô tả)**
  với allowlist riêng, và **không nới** danh sách ba trường của D3.5. D7 dùng đường (c).
- Danh sách tên đầu ra dự kiến, **mỗi tên phải kèm một câu vì-sao-không-phải-chỉ-số-hiệu-năng**
  (`__CHUA_DIEN__`, §8):
  - tỉ lệ lệnh đóng bằng `TIME_STOP` (DG8);
  - tỉ lệ đóng bằng DG7 funding stop;
  - tỉ lệ đóng bằng DG6;
  - phân bố `hold_duration_bars`;
  - phân bố `liq_buffer_ratio`.
- ⚠️ **Câu phải hỏi chủ dự án, không tự quyết:** `max_single_trade_loss / risk_budget` và phân bố lý do
  thoát lệnh có phải *chỉ số hiệu năng trá hình* không? Biết tỉ lệ stop-loss là biết một phần
  expectancy. Nếu có thì bỏ khỏi CTRL; tiêu chí 1.15 khi đó chỉ kiểm được trên kịch bản tổng hợp (§4.1)
  và ở D9.
- Kèm theo: `MT-44`, ghi `BAT_KHA` cho DG1–DG5 trên `Z0-T1`. `MT-46` (1): `dg7_funding_frac` đóng băng
  với lý do *"chỉ áp cho SHORT"* trong khi code áp cho cả Long (đo được: kết thúc 19,4% lệnh `Z0-T1`) —
  sửa lời khai trạng thái, **không** sửa giá trị.
- **Phụ thuộc:** code của dạng CTRL thứ ba. Hiện grep `ctrl_mo_ta` trong `src/` cho **0 kết quả**, và
  `TD-0251` là việc đầu tiên sẽ cần nó.

### 4.4. Sự cố vận hành

Mỗi ca phải có **phá-thật-chạy-lại** (vô hiệu hoá cơ chế thì test phải đỏ):

- khởi động lại giữa vị thế đang mở: kế hoạch và đỉnh equity sống sót (TD-0237/0238);
- 418/429 → dừng ngay, backoff nhiều tầng (§6.6, TD-0241);
- thiếu API key → từ chối chạy (TD-0242);
- LIQUIDATED → dừng toàn hệ thống (§6.6 ràng buộc 2).

**Cổng D7:** `d6_complete` · mọi cầu dao ở §4.1–§4.4 có ít nhất một test chạy qua đường sản xuất và đỏ
khi bị vô hiệu hoá · artifact stress có xuất xứ (§0d.5) · `MT-40` có kết luận.

---

## 5. D8 — Tiền đăng ký lockbox (D9.5) và dọn nợ trước go-live

**Mục tiêu:** mọi quy tắc phán quyết **còn trống** được commit **trước** khi có số. Chỉ giấy tờ, không
chạm dữ liệu. **Soạn được ngay, song song với D5–D7.**

| # | Việc | Căn cứ |
|---|---|---|
| D8.1 | **Quy tắc lockbox — điền các ô `......` của DR-011** (`spec:3328-3343`) trừ ô *"cấu hình"*. Ô đó điền sau D9 theo luật *"đúng MỘT cấu hình, chọn từ WFO"*. Điền: ngưỡng DSR-adjusted expectancy cho LONG; `≤ 1.15`; `liq_buffer ≥ 8`; `≥ 30` lệnh; câu tường minh *"Short không được đánh giá; lần chạm này tiêu lockbox cho Short"* (§1.1) | `spec:3324-3326` |
| D8.2 | **Kiểm lại điều kiện chất lượng lockbox (c)**: *"≥ 30 lệnh dự kiến cho cấu hình tốt nhất"*, với rổ pool mới (TD-0247). Ước lượng bằng **tốc độ lệnh đếm được trên CALIB** (TD-0251, CTRL chỉ đếm) nhân độ dài `[T2,T3]`. **Không** đếm trên lockbox, vì đếm trên lockbox cũng là chạm | DR-011 (c); `DR-D4-12` §2.2 phân biệt INCONCLUSIVE n < 30 với INCONCLUSIVE thuế nhiễu |
| D8.3 | **Hệ quả Long-only cho Short:** bổ sung **một đoạn** vào điều kiện mở lại Short đã có (`DR-D4-01` §2b): Short cần lockbox MỚI. **Không** viết DR Short thứ hai (N12 mục 6: một ý, một file) | `DR-D4-01` §2b |
| D8.4 | **Đóng nợ trước go-live** (`back-end-note.md:128`: *"không mang mâu thuẫn 🟡 vượt qua go-live"*): `MT-26` câu 2 · `MT-27` · `MT-28` (ô DSR `spec:4260` còn trống; sửa spec cần duyệt) · `MT-33` (🔴; với một arm phán quyết có thể N/A, phải ghi lý do) · `MT-46`. Đánh dấu `OQ-10`/`OQ-12`/`OQ-13` ✅ nếu đủ bằng chứng. **Mỗi MT là một quyết định của chủ dự án**, ghi qua lệnh "chuẩn hóa và lưu" | `TASKS.md` đoạn mở Khối 18 |
| D8.5 | **Hai mâu thuẫn mới** (§9) → `MT-49`, `MT-50` | Quy tắc 11 |

**Cổng D8:** các văn bản D8.1/D8.3 đã commit, không còn `__CHUA_DIEN__` · D8.2 có con số kèm xuất xứ ·
mọi MT ở D8.4/D8.5 có trạng thái ✅ hoặc quyết định *"mang theo có ý thức"* của chủ dự án.

**Ngoài phạm vi D8 — thuộc `DR-D9-01` (phiên `-33`):** sơ đồ fold WFO, ngưỡng PBO/CSCV, tập cấu hình
CSCV, sàn lệnh/năm cho D9, thuế nhiễu D9. Kế hoạch đã duyệt từng đặt những việc này vào D8. Đã **gỡ**
để không có hai nguồn sự thật (N12 mục 6).

---

## 6. Ranh giới với D9 và thứ tự

```
TD-0247 → D4 → D5 → D6 → D7 ─┐
                              ├→ D9 (WFO + GATE, DR-D9-01) → D9.5 lockbox → D10 → D11 → D12
D8 (soạn từ bây giờ) ─────────┘
```

**Đề xuất điều kiện vào D9** (đã báo phiên `-33` để khớp vào `DR-D9-01`):
`d5_complete` + `d7_complete` (ngụ ý `d6_complete`) + `d8_complete`.

| Vì sao D9 phải đợi | |
|---|---|
| D6.1 | N của D9 phụ thuộc DR-007. `DR-D9-01` **không nên** ghi cứng `N = 114` |
| D6.3 · D7 | Có thể lộ lỗi Hạng 1 **đổi số**. Sửa sau D9 = chạy lại WFO bằng suất mới (`-33` đã ghi đúng luật này) |
| D6.6 | D9 chấm cấu hình **đã băm**. Không có hash thì *"cấu hình đem ra lockbox"* không truy được về thứ D9 đã chấm |
| D8.1 | Ngưỡng lockbox phải commit **trước khi thấy số WFO**. Không thể "sau D9, trước D9.5", vì lúc đó người điền đã biết WFO ra bao nhiêu |

⚠️ **Đánh đổi của điều kiện này:** D9 trễ thêm thời gian của D6–D8. Phương án ngược lại (D9 chạy song
song D6–D7) nhanh hơn, nhưng chấp nhận rủi ro phải chạy lại WFO **bằng suất mới** nếu D6/D7 lộ lỗi đổi
số. Chọn chặn vì suất B1 dư có hạn, còn thời gian thì không phải ngân sách thống kê.
`__CHUA_DIEN__`: chủ dự án xác nhận (§8).

---

## 7. Đính chính so với kế hoạch đã duyệt 17/09/2026

| Kế hoạch ghi | DR này ghi | Vì sao |
|---|---|---|
| D7: *"DR mở rộng `CTRL_OUTPUT_ALLOWED`"* | Dùng dạng CTRL thứ ba *đo mô tả* | Trái `MT-19` (chốt 14/09, đường c). Phát hiện khi đọc lại `back-end-note.md` trước khi viết (quy tắc 3) |
| D8: *"DR điều kiện mở chu trình Short"* | Bổ sung một đoạn vào `DR-D4-01` §2b | Ba điều kiện mở lại Short đã có sẵn ở đó |
| D8: *"DR tiền đăng ký WFO (D9)"* | Gỡ, trỏ sang `DR-D9-01` | Phiên `-33` đang viết đúng văn bản đó |
| D6: *"sửa `MT-30` trước D9"* | *Đo* xem `MT-30` có chạm `Z0-T1` không | `Z0-T1` đơn tranche; sửa một lỗi không nằm trên đường chạy sản xuất là đoán, không phải đo |
| `MT-33` là 🟡 | `MT-33` là 🔴 | Đọc lại `back-end-note.md` |

---

## 8. Ô chưa chốt — `__CHUA_DIEN__`

| Ô | Câu hỏi cho chủ dự án | Đề xuất |
|---|---|---|
| §4.1 biên độ kịch bản | Gap bao nhiêu %, funding bao nhiêu, bao nhiêu mã cùng vào lệnh? | Neo vào sự kiện lịch sử **đã biết công khai** (vd 05/08/2024, 10/10/2025), lấy **biên độ** chứ không lấy chuỗi giá. Chép chuỗi giá của một ngày nằm trong CALIB/WFO là chạm dữ liệu |
| §4.3 danh sách tên CTRL | Lý do thoát lệnh và tỉ lệ lỗ/ngân sách có được coi là "mô tả" không? | Chỉ cho `hold_duration_bars` + `liq_buffer_ratio` + tỉ lệ `TIME_STOP`/DG7/DG6 **gộp một số** (không tách SL/TP). Tiêu chí 1.15 kiểm trên kịch bản tổng hợp |
| §4.2 `MT-40` | Đỉnh equity reset khi nào (không bao giờ · sau ABORT · khi nạp vốn)? | Chỉ reset khi **nạp/rút vốn có ghi sổ**, còn lại không bao giờ. Không phải tham số tune được, xếp Cấp C |
| §6 điều kiện vào D9 | D9 đợi D6–D8, hay chạy song song rồi chấp nhận rủi ro chạy lại? | Đợi (lý do ở §6) |
| D6.1 ngưỡng DR-007 | `> 50%` (`spec:2821`) hay `≥ 50%` (`spec:2854`, `:4267`)? | Xem §9, `MT-50` |

---

## 9. Mâu thuẫn phát hiện khi soạn (chờ "chuẩn hóa và lưu" để ghi `back-end-note.md`)

- **`MT-49` 🟡 — lockbox được chạm ở D9 hay D9.5?** `DR-D0PRE-07:85-87` viết *"chạm thật là D9"* và
  *"lần chạm duy nhất ở D9"*. Spec viết `D9.5 — LOCKBOX: chạm ĐÚNG MỘT LẦN` (`:4493`), `L-Z13` *"cho tới
  sau D9"* (`:3876`). Chữ spec và cổng `L-Z13` đều nghiêng D9.5; không tự chọn bên. Hệ quả nếu đọc theo
  `DR-D0PRE-07`: `DR-D9-01` có thể tưởng lockbox nằm trong phạm vi của nó.
- **`MT-50` 🟡 — ngưỡng DR-007 là `> 50%` hay `≥ 50%`?** `spec:2821` *"overlap > 50%"*, còn `spec:2854` và
  `:4267` *"≥ 50%"*. Chỉ khác nhau đúng ở ca overlap = 50,0%. Rẻ nếu chốt **trước** khi đo (D6.1), đắt nếu
  chốt sau.

---

## 10. Phủ sóng — đối chiếu với các hạng mục chưa có pha

| Hạng mục | Pha | Ghi chú |
|---|---|---|
| H2 Portfolio Context | D6.5 | |
| H5 timeframe-detail 5m | D6.4 | |
| H9/H10 stress thanh lý | D7 §4.1 | |
| H14 pool overlap | D6.1 | Sau khi live: đo lại mỗi lần rà pool hàng tháng (`spec:2855`), không thuộc D6 |
| Risk Supervisor §6.6 | D7 §4.4 | Code đã có (TD-0241); D7 chỉ chứng minh cầu dao nổ |
| Ablation DG8 +2 suất | **Không** | P4; `spec:1500-1504` đề xuất hoãn |
| Short | **Không** | §1.1 |
| FreqAI | **Không** | `DR-FAI-01` (nháp, chưa commit) là giả thuyết riêng |
| PBO/CSCV P0, fold WFO | **Không** | `DR-D9-01` |

Khẳng định cho cả ba pha: **0 trial · không entrypoint mới · không chạm WFO/LOCKBOX · không dùng cơ chế
tham số Freqtrade · không đọc tham số từ env.**
