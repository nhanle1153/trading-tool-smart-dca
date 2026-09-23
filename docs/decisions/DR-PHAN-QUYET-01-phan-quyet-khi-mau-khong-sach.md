# DR-PHAN-QUYET-01 — Phán quyết có nghĩa gì khi cỡ mẫu hoặc cấu trúc không cho câu trả lời sạch

> **Ngày chốt:** 24/09/2026 · **Người quyết:** chủ dự án (duyệt đề xuất phiên mã `69e2254e`; chọn hướng *"chuyển phép
> kiểm lên lúc thiết kế"* cho `MT-72` sau khi đề xuất đầu bị loại vì va điều kiện dừng — xem §4.1).
> **Giải:** `OQ-17` · `MT-72` · `MT-73` (`back-end-note.md` mục 6/7).
> **Chi phí:** **0 suất trial** · **0 dòng mã sản xuất** · **KHÔNG đổi một ngưỡng nào**.
> Mã `DR-PHAN-QUYET-01` + `TD-0372` đặt chỗ bằng commit `ea2bfee` (N12 mục 7c) trước khi file này tồn tại.

> 🔴 **PHIÊN SINH Ý TƯỞNG (IDEA) VÀ PHIÊN CHỌN KHÔNG ĐỌC FILE NÀY** (`DR-009`) — soạn bởi một phiên đã thấy số đo
> của Tool D. Nghĩa vụ ở §4 áp cho ứng viên **từ D0 trở đi**, tức SAU khi đã được chọn.

---

## 0. Khai thẳng — viết khi nào, và vì sao lúc này

Viết **sau** khi đã thấy kết cục của Zone Absorption LONG (cổng D4 `d5ef262`: Nhánh 1 = FAIL, `time_stop_ratio`
0,43%, `dsr_adjusted_expectancy` −0,2216). Viết **trước** 01/10/2026, ngày cửa CHỌN ứng viên kế tiếp mở, tức **trước
khi tồn tại một con số nào của ứng viên đó**. Đây là lúc duy nhất ba câu dưới đây còn trả lời được mà không bị nghi là
uốn theo số của người được áp.

Ba giới hạn, viết ra để không ai đọc quá tay:
1. **Không hồi tố.** Kết cục của ZA LONG giữ nguyên như `DR-ZA-01` ghi — DR này không đổi một chữ nào của nó.
2. **Không đổi ngưỡng nào** (§5).
3. Mọi số dẫn ở đây là số **đã đo**; nơi nào là ước lượng thì ghi rõ là ước lượng.

## 1. Một công thức, hai việc

Ba câu hỏi này cùng một gốc: một phán quyết **không phân biệt được** *"thiếu lợi thế"* với *"thiếu mẫu"* hay với
*"lỗi thiết kế"*. Công cụ phân biệt đã có sẵn trong mã và **không được chép lại** (`MT-03`):

```
thuế nhiễu  T = h · σ / √n          — thue_nhieu()        src/tool_d/gates/ket_cuc.py:55
kết cục     INCONCLUSIVE ⇔ giá trị < ngưỡng VÀ T > ngưỡng  — phan_loai_ket_cuc()  ket_cuc.py:112-119
so cặp      mean(d) − h · std(d)/√n_giao                    — so_paired()          ket_cuc.py:206
h = dsr_hurdle(N = 114) = 3,0777 ;  ngưỡng expectancy = 0,10 R
```

Cùng một phép tính dùng ở hai chỗ:
- **trước khi tiêu suất** — suất này mua được gì (§2, `OQ-17`);
- **trước khi tuyên bố một mức lỗi** — dữ liệu có đủ tư cách nói điều đó không (§3, `MT-73`).

## 2. `OQ-17` — cửa KHAI trước khi tiêu suất

### 2.1 Luật

Trước mỗi lô tiêu suất (D5, D9, D9.5, mọi lô đo lại, cho mọi ứng viên), DR của lô phải tính trước `T` và so với ngưỡng
của **chính tiêu chí** mà suất đó dự định phán quyết.

- `T ≤ ngưỡng` ⇒ không nghĩa vụ gì thêm.
- `T > ngưỡng` ⇒ **KHÔNG chặn**, nhưng DR của lô phải có **hai câu**: (a) suất này mua gì khi PASS gần như không đạt
  được ở cỡ mẫu này; (b) **tiêu chí nào trong lô vẫn đo được** dù expectancy sẽ INCONCLUSIVE — để một lô không bị bỏ oan
  vì một tiêu chí hỏng.

Tiền lệ: `DR-D4-08` §6 hỏi đúng câu (a) một lần và giữ lại 9 suất.

### 2.2 σ là của ĐẠI LƯỢNG ĐANG KIỂM — không phải của arm

| Phép phán quyết | σ dùng | Nguồn |
|---|---|---|
| Tiêu chí MỨC (Nhánh 1, `dsr_adjusted_expectancy`) | `std_r` của arm | bản ghi arm |
| Phép so CẶP (D5 §5.1 — `mean(d) − h·std(d)/√n_giao`) | `std(d)` — độ lệch chuẩn của **hiệu từng lệnh** | `so_paired()` |

🔴 Áp σ mức cho phép so cặp là **sai đơn vị**: hai cấu hình chồng lấn phần lớn tập lệnh có `std(d)` nhỏ hơn nhiều
`std_r`, và dùng nhầm sẽ gắn nhãn *"vô vọng"* cho một phép đo phân biệt được. (`OQ-17` bản đầu mắc đúng lỗi này.)

### 2.3 σ lấy từ đâu — quy tắc CON TRỎ, không ghim lô

- `σ` = giá trị `status == "ok"` của **bản ghi hiện vật ĐÃ COMMIT** gần nhất trên **hệ thống hiện hành**, cho đúng đại
  lượng ở §2.2.
- Nhiều nguồn ⇒ lấy **`max`** (sai về phía *khó tiêu suất hơn*).
- Không nguồn nào `ok` ⇒ luật **không áp**, DR của lô phải khai *"không ước lượng được T"* — không được điền số thay thế
  (N6).
- Hiện vật nằm trong `runs/**` (bị `.gitignore:16` che) **không** đủ tư cách làm nguồn: một quy tắc trỏ vào file ngoài
  lịch sử là quy tắc không tái lập được.

Bài học của chính `OQ-16`: ghim σ vào **một lô cụ thể** (`DR-D4-19`) thì lô đó chết trong 24 giờ và câu hỏi mất nguồn.

### 2.4 Phạm vi — cái gì luật này KHÔNG áp

- Chỉ áp cho tiêu chí dạng **expectancy**. Ở D9 đó là **1/8** tiêu chí Nhánh 1; tiêu chí CHẶN P0 của D9 là **PBO ≤ 0,5**
  — thuần thứ hạng, không bị thuế nhiễu. ⇒ **Luật này không phải lý do để hoãn hay bỏ D9.**
- Không phải một chốt. Không mã nào chặn `reserve()` vì `T` lớn.

### 2.5 Số minh hoạ (đã đo, ZA LONG — chỉ để thấy độ lớn, không áp cho ứng viên nào)

`D-0019`, `Z0-T1`, WFO: `σ = 1,1117` · `n = 231` ⇒ `T = 0,2251` = **2,25 lần** ngưỡng. Muốn `T ≤ 0,10` cần
`n ≥ 1.171` lệnh — gấp **5,1 lần**, ≈ 3,2 năm ở 365,25 lệnh/năm. Nguồn:
`docs/du-lieu-do/d4-lo-dr-d4-20/D-0019-arm_result.json` (`47b3060`).

## 3. `MT-73` — tiêu chuẩn bằng chứng cho `L1` / `L2` / `L3`

### 3.1 Vì sao cần tiêu chuẩn, không cần một nhãn

`DR-011` (`spec:3276`, `:3345-3378`) viết ba kết cục cho **lần chạm lockbox D9.5**; `spec:4290-4292` bắc cầu sang cổng
D0.9 nhưng để trống **ai gán mức** và **gán dựa trên bằng chứng gì**. `§11b.1` (`spec:4362-4376`) cảnh báo cạm bẫy nguy
nhất là *"phân loại nhầm `L2/L3` thành `L1` để được dùng quy trình rẻ hơn"*. Chiều ngược lại nguy không kém: gán `L3`
(*"dừng dự án"*) cho một phép đo **không có khả năng** nói điều đó.

### 3.2 Luật

| Mức | Nghĩa (`§11b.1`) | Điều kiện BẰNG CHỨNG tối thiểu để được gán |
|---|---|---|
| `L1` | sai GIÁ TRỊ, cấu trúc đúng | Chỉ ra được **một** tham số mà đổi riêng nó là đủ. Phải đổi > 1 tham số cùng lúc ⇒ **không phải `L1`** (`spec:3427-3437`) |
| `L2` | sai CẤU TRÚC | Có bằng chứng **cấu trúc** đo được — một cơ chế không hoạt động như thiết kế (ví dụ: một cửa thoát không bao giờ ràng buộc) |
| `L3` | sai GIẢ THUYẾT — không có lợi thế | Phép đo expectancy **có khả năng ra FAIL**: `T ≤ ngưỡng`, tức `phan_loai_ket_cuc()` **không** trả INCONCLUSIVE vì thuế nhiễu. Thiếu điều kiện này ⇒ **không được gán `L3`** |

- Mức chỉ được gán bằng **một DR của chủ dự án**, dẫn bằng chứng theo bảng trên. Không phiên nào tự gán.
- Không đủ bằng chứng cho mức nào ⇒ nhãn mạnh nhất được phép là *"bác bỏ ở cấu hình này"* — đúng chữ `DR-011`.

### 3.3 Áp vào ZA LONG — kiểm luật, KHÔNG gán mức

- `L3`: `T = 0,2251 > 0,10` ⇒ phép đo D4 **không đủ tư cách** nói *"không có lợi thế"*. **Không gán `L3`.**
- Bằng chứng có thật là **cấu trúc**: DG8 là cửa chết (§4.1). Đó là loại bằng chứng của `L2`.
- ⇒ Nhãn đứng vững là *"bác bỏ ở cấu hình này"*, như `DR-ZA-01` đã ghi. DR này **không** gán thêm mức nào cho ZA; nếu
  chủ dự án muốn gán, dùng luật §3.2.

### 3.4 Phạm vi của `retest_forbidden`

`retest_forbidden` cấm theo **cặp (cấu hình, tập dữ liệu)**: với ZA LONG là cấu hình của lô `DR-D4-20` trên WFO
`[T1, T2)`. Nó **không** cấm một ứng viên khác cấu trúc, và không cấm đo cấu hình đó trên một tập dữ liệu chưa từng dùng
(việc đó đã có luật riêng — `DR-011` gia hạn chỉ trên đoạn MỚI).

## 4. `MT-72` — tiêu chí `time_stop_ratio`: GIỮ NGUYÊN ngưỡng, chuyển phép kiểm lên LÚC THIẾT KẾ

### 4.1 Đề xuất đầu bị loại — ghi lại để không ai đề xuất lại

Đề xuất đầu của phiên `69e2254e`: biến biên dưới (< 5%) thành chẩn đoán, không FAIL. **Loại**, vì va hai văn bản đã
chốt, và lập luận *"không hồi tố"* không thoát được chữ của chúng:
- `DR-ZA-01` §6 mục 2: *"Có ai đề nghị nới dải `TIME_STOP_RATIO_BAND` … ⇒ dừng: … nới ngưỡng sau khi thấy số, và
  `DR-011` cấm tường minh."*
- `thresholds.py:100` (`TD-0277`/`MT-46`): *"Không nới chiều < 5% sau khi đã thấy con số đó."*

Phiên đề xuất đã đọc `DR-ZA-01` §6 trong cùng phiên mà không đối chiếu khi đề xuất — bắt được lúc chuẩn bị viết mã.

### 4.2 Luật

`TIME_STOP_RATIO_BAND = (0,05; 0,25)`, **cả hai biên đều chặn** — không đổi.

Mối lo của `MT-72` là thật: một ứng viên có các cửa thoát khác luôn đóng lệnh trước `max_hold_bars` sẽ trượt tiêu chí
này **vì thiết kế**, không vì thiếu lợi thế. Với ZA LONG: `TIME_STOP` = **0/160** (`TD-0246`, hệ thống cũ) và **1/246**
(`TD-0367`, hệ thống đã có `L-Z3`) — giữ nguyên độ lớn ở cả hai phiên bản mã; muốn chạm 5% cần gấp ~12 lần, trong khi
spec chặn `max_hold_bars` trong `[20, 40)` (`spec:1476-1481`).

Chỗ bắt đúng là **trước khi có dữ liệu thật**, không phải ở cổng:

1. **Ở D0 của ứng viên kế tiếp**, tài liệu thiết kế phải KHAI vai trò của DG8: cửa thoát nào được kỳ vọng đóng phần lớn
   lệnh, và vì sao tỉ lệ `TIME_STOP` kỳ vọng nằm trong `[5%, 25%]`.
2. **Trước suất đầu tiên**, đo phân bố `exit_reason` trên **EXPLORE, 0 suất** — kịch bản có sẵn
   `docs/du-lieu-do/do_td0193_lenh_nam_explore.py` đã đếm `exit_reason` (chỉ đếm, không PnL; `DR-D0PRE-05` §4 cho phép
   dùng EXPLORE để sinh và kiểm thiết kế).
3. `TIME_STOP` ngoài dải trên EXPLORE ⇒ **dừng trước khi tiêu suất**: sửa thiết kế (một lỗi `L2` bắt ở D0, rẻ nhất có
   thể), hoặc chủ dự án khai bằng DR rằng ứng viên sẽ vào cổng D0.9 với tiêu chí này biết trước là trượt.

### 4.3 Vì sao đây không phải một cách nới vòng

- Không ngưỡng nào đổi; cổng D0.9 chấm y như đã chấm ZA.
- Phép đo ở bước 2 là **cấu trúc** (đếm cửa thoát), không phải hiệu năng, và làm trên EXPLORE — không chạm CALIB/WFO/
  LOCKBOX.
- ⚠️ Rủi ro còn lại, khai thẳng: sửa thiết kế sau khi thấy phân bố `exit_reason` trên EXPLORE là một vòng
  *"nhìn rồi chỉnh"*. Giới hạn nó: chỉ được sửa để đưa `TIME_STOP` vào dải; mọi thay đổi ghi vào DR của ứng viên **trước**
  suất đầu tiên, và không được nhìn PnL trên EXPLORE lúc sửa.

## 5. Ranh giới — cái gì KHÔNG đổi

- Mọi ngưỡng: `0,10 R` · `≥ 20%` · `150 lệnh/năm` · dải `5–25%` (**cả hai biên**) · `PBO ≤ 0,5` · `N = 114` · rào
  `3,0777` · `|tier_b| = 12`.
- `DR-ZA-01` và kết cục của ZA LONG. `DR-011`. `TD-0277`/`MT-46`. `DR-D5-01`, `DR-D9-01`.
- Không mã sản xuất nào. Không test cũ nào.

## 6. Thi hành

| Việc | Khi nào |
|---|---|
| DR này | `TD-0372`, commit RIÊNG |
| Đóng `OQ-17`, `MT-72`, `MT-73` trong `back-end-note.md` (trỏ về DR này) | lệnh *"chuẩn hóa và lưu"* kế tiếp (N9) |
| Máy canh cho §4.2 bước 3 (từ chối suất đầu tiên của ứng viên khi chưa có artifact `exit_reason` EXPLORE) | **chưa làm** — mã việc riêng, cần *"bắt đầu code"*; hôm nay §4.2 là kỷ luật văn bản, không có máy giữ |

## 7. Điều kiện dừng / mở lại

- Có ai đề nghị đổi một ngưỡng ở §5 dựa vào DR này ⇒ **dừng**: DR này không cấp quyền đó.
- Một ứng viên đã có số trên CALIB/WFO ⇒ §4.2 không còn áp được *"trước khi có dữ liệu"* cho ứng viên đó; phải có DR riêng.
- Mở lại `MT-72` theo hướng đổi ngưỡng: chỉ bằng một DR **ghi đè có ý thức** `DR-ZA-01` §6 mục 2 và `MT-46`, viết trước khi
  có số của ứng viên được áp, và khai đúng tên việc đó là *"nới ngưỡng"*.

## 8. Điểm yếu

1. Viết sau khi đã thấy số của ZA LONG (§0).
2. §4.2 bước 3 chưa có máy canh — một nghĩa vụ chỉ nằm trong chữ là thứ `MT-71` vừa gọi tên.
3. Luật §3.2 cho `L3` phụ thuộc cỡ mẫu: ở tần suất lệnh hiện nay, **không phép đo nào trong đường ống** đủ tư cách gán
   `L3` cho một ứng viên có `σ` cỡ 1,1 R — nghĩa là con đường *"dừng dự án vì không có lợi thế"* gần như không bao giờ mở.
   Đó là hệ quả của số, không phải của DR này; khai ra để không ai tưởng đường đó đang mở.
