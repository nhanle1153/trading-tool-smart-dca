# DR-SONG-CON-01 — Cổng sống còn: Zone Absorption LONG có đáng tiêu suất đo không?

> **Ngày chốt:** 17/09/2026 · **Người quyết:** chủ dự án (đánh giá tổng hợp, §4 Bước 2 + §7; hai chốt: *"chắc chắn
> thống kê trên hết"* và *"lỗ rõ sau phí ⇒ dừng chiến lược, chuyển ý tưởng"*) · phiên `-33`
> **0 trial** · **Commit RIÊNG và TRƯỚC** script đo và artifact số của TD-0291 — kiểm bằng
> `git merge-base --is-ancestor <sha_DR> <sha_artifact>`.
> Đã nhắn `-30`/`-01` mã `DR-SONG-CON-01` + `TD-0290`/`TD-0291` trước khi mở file (N12 mục 6).

---

## 0. Vì sao cần DR này

Sau 11 ngày, **chưa có một con số lời/lỗ nào của chiến lược** ở bất kỳ tập dữ liệu nào (`MT-27`). Đường ống còn
lại sẽ tiêu tới ~41 suất đo (D4 9 · D5 ≤ 16 · D9 ≤ 16) trên một chiến lược chưa biết có lợi thế. Mức lời cần để
PASS rất cao: **~0,21–0,42 R mỗi lệnh sau phí** (`td0184-do-nhay-rao-dsr.json`).

Phép đo này trả lời **một câu duy nhất**: *có đáng tiêu suất đo vào Zone Absorption LONG không?* Nó **không**
phán quyết PASS/FAIL của cổng nào.

## 1. Căn cứ hợp lệ và ranh giới

- `DR-D4-13` §1.2: EXPLORE **được** tính PnL/`std_R` ở 0 trial, nhưng **cấm** làm căn cứ phán quyết cổng hay
  chọn arm/tham số. Cổng sống còn là **cổng DỪNG** (có tiếp tục tiêu suất không), không phải phán quyết cổng.
- DR-014 §2: EXPLORE nằm **ngoài sổ ngân sách** ⇒ không `reserve()`, sổ trial không thêm dòng.
- 🔴 **Cấm tuyệt đối:**
  - đưa bất kỳ số nào ở đây vào `tool_d_config.yaml` / `param_status.yaml`;
  - dùng để chọn giá trị tham số (D5), xếp hạng arm (D4), hay chọn cấu hình ghép;
  - chạy lại với tham số khác "để xem";
  - dùng làm bằng chứng PASS ở bất kỳ cổng nào.
- **Khai DR-009:** người quyết (chủ dự án, các phiên) **sẽ nhìn thấy** số này. Đó là cái giá đã chấp nhận
  (đánh giá tổng hợp §3, phương án B). Luật §4 viết trước để số không uốn được quyết định.

## 2. Đo gì — chốt trước

| Mục | Chốt |
|---|---|
| Arm | **`Z0-T1`**, LONG, chiến lược sản xuất `ZoneAbsorption`, tham số **hiện hành** trong YAML — không đổi một giá trị nào |
| Dữ liệu | **EXPLORE** (`user_data/data/explore/`, 88 mã, tách hẳn rổ pool), timerange **`[T0, T2)` = `20240409–20260129`** — không chạm LOCKBOX |
| Cửa sổ con | CALIB `[T0,T1)` và WFO `[T1,T2)` báo **riêng** + **gộp** |
| Khung | 1H; ⚠️ **không** `--timeframe-detail` (EXPLORE không có 5m) — xem §5 |
| Đơn vị | **`R_trien_khai = pnl_abs / rui_ro_da_trien_khai_usdt`** (`DR-D4-12` §1.4, công thức ở `wfo/lenh.rui_ro_da_trien_khai_usdt`); `pnl_abs` đã trừ phí + funding (DR-013). `R_realized` báo cạnh bên, không dùng cho luật |
| Thống kê | `n` · `mean` · `std` (mẫu, `n−1`) · khoảng tin cậy 95% `mean ± 1,96·std/√n` · phân bố kiểu thoát · tỉ lệ lệnh lời |
| Chẩn đoán kèm | `Z0-T0` cùng cách đo — **chỉ mô tả**, không vào luật |

**Mức cần để PASS** (`M`), tính bằng đúng công thức `td0184`, không thêm con số mới:

```
M      = DSR_ADJ_EXPECTANCY_MIN + √(2·ln N) · std / √n_cong
n_cong = (n_EXPLORE / mã-năm EXPLORE) × 102 mã pool × (147 / 365 năm)     ← số lệnh dự kiến trong
                                                                             3 đoạn test D4 (MT-36)
N      = N hiện hành: 114; nếu TD-0261 đã đo và DR-007 áp dụng (overlap ≥ 50%) ⇒ N union
```

Nếu TD-0261 **chưa** đo lúc chạy: báo `M` ở `N = 114` **và** ghi `M_union = pending`; luật §4 dùng `N = 114`,
và kết luận "ĐI" bị gắn nhãn *"chưa tính DR-007"* cho tới khi TD-0261 xong.

## 3. Ba trạng thái (N6)

- `n` gộp < 30 (mốc DR-011, không phải số mới) ⇒ **`unreadable`** ⇒ không áp luật, trình chủ dự án.
- Chạy lỗi / thiếu dữ liệu một phần ⇒ ghi `unreadable` kèm lý do; **không** điền số từ phần chạy được.

## 4. Luật — viết trước, áp máy móc

Áp trên số **gộp** `[T0, T2)`, theo thứ tự:

| # | Điều kiện | Quyết định |
|---|---|---|
| 1 | `n < 30` | **KHÔNG KẾT LUẬN** — trình chủ dự án |
| 2 | Cận trên khoảng tin cậy 95% `< 0` (lỗ rõ sau phí) | **DỪNG Zone Absorption LONG** (chủ dự án đã chốt): không tiêu suất D4/D5/D9; ghi research-log; ý tưởng kế tiếp từ Idea Queue; hạ tầng đo giữ nguyên |
| 3 | `mean ≥ M` **và** `mean > 0` ở **cả hai** cửa sổ con CALIB, WFO | **ĐI** — đường găng D4 → D5 → D6–D8 → D9 hết tốc lực |
| 4 | Còn lại (dương nhưng dưới `M`, hoặc dấu lệch giữa hai cửa sổ) | **KHÔNG TIÊU SUẤT lúc này** — đường ống sẽ ra INCONCLUSIVE với xác suất cao. Trình chủ dự án: chờ thêm dữ liệu theo thời gian, hoặc quyết khác có ghi lý do |

- Điều kiện "dấu cùng chiều ở hai cửa sổ" (luật 3) là **điều kiện nhất quán**, không phải một ngưỡng số mới: một
  lợi thế chỉ có ở một nửa thời gian không phải lý do để tiêu 41 suất.
- 🔴 Cấm đổi thứ tự luật, đổi `M`, đổi cửa sổ, hay bỏ điều kiện 3 **sau** khi đã có artifact.

## 5. Hạn chế khai trước — chép vào artifact

1. **Không có dữ liệu 5m** ⇒ thứ tự chạm SL/TP trong cùng nến 1H là xấp xỉ, **chiều lệch chưa biết** (H5 P0 đòi
   5m cho phép đo thật). Số EXPLORE vì thế **kém tin hơn** số D4 sẽ đo.
2. **EXPLORE ≠ pool:** lợi thế trên 88 mã EXPLORE không chứng minh lợi thế trên 102 mã pool (và ngược lại).
3. **Cửa sổ WFO đã được D4 nhìn thấy** qua đếm lệnh (TD-0193/0205/0212) — chỉ đếm, chưa PnL; ghi ra.
4. **Một cấu hình** (`Z0-T1`, tham số hiện hành, chưa calibrate): luật 2 bác **cấu hình này**; nó là căn cứ dừng
   chiến lược vì D5 chỉ dò quanh mốc (`DR-D5-01` §3) và ngưỡng thắng rõ rất chặt — không kỳ vọng D5 lật dấu.

## 6. Lỗi kỹ thuật và chạy lại

- Phát hiện lỗi mã **trước** khi đọc số (crash, thiếu dữ liệu) ⇒ sửa, chạy lại, không giới hạn.
- Phát hiện lỗi mã **sau** khi đã có artifact (DR-012 Hạng 1: mã không khớp spec) ⇒ được chạy lại **đúng một lần**
  sau commit sửa; artifact cũ **giữ nguyên**, artifact mới ghi `sha` sửa + lý do; luật áp trên bản sửa.
  Lần thứ hai ⇒ trình chủ dự án. Không có "lỗi" nào được định nghĩa bằng "số trông xấu".

## 7. Thi hành

| Mã | Việc |
|---|---|
| `TD-0290` | DR này |
| `TD-0291` | Script `docs/du-lieu-do/do_td0291_song_con_explore.py` (dùng lại khung `do_td0193_*`, `wfo/lenh`) + artifact `docs/du-lieu-do/td0291-song-con-explore.json` ghi đủ §2, §3, §5, kết luận theo §4. **Chờ "bắt đầu code"** |
