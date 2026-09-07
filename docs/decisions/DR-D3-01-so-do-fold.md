# DR-D3-01 — Sơ đồ fold cho H3-D Walk-forward orchestrator

> **Ngày chốt:** 07/09/2026 · **Người quyết:** chủ dự án · **Việc:** TD-0140 (Khối 14, D3)
> 🔒 **File này commit RIÊNG và TRƯỚC mọi dòng code fold.** Cùng khuôn OQ-07/TD-0120: sơ đồ
> fold phải niêm phong **trước khi nhìn thấy bất kỳ kết quả nào**, nếu không nó sẽ bị vặn theo
> số đã thấy — và đó đúng là kênh nhiễm mà walk-forward tồn tại để chặn.

---

## 1. Vì sao spec không trả lời được câu này

Spec `tool-d-smart-dca.md` (v8) **không định nghĩa sơ đồ fold ở bất kỳ dòng nào**: không nói
anchored hay rolling, không nói độ dài train/test, không nói bước trượt, không nói số fold.
Nó chỉ nói cửa sổ WFO là `[T1 … T2]` (dòng 3290) và rằng D9 cần *"WFO đã sinh đủ cặp IS/OOS
để CSCV có power"* (dòng 4326).

Đây là quyết định kỹ thuật bắt buộc phải chốt, không được tự chọn im lặng (CLAUDE.md quy tắc 2).

---

## 2. 🔴 Phát hiện đổi cách hiểu: WFO của Tool D KHÔNG khớp lại tham số

Walk-forward kinh điển dùng cửa sổ train để **khớp lại tham số**, rồi test out-of-sample.
Tool D **không làm vậy và không được phép làm vậy**:

- `N3` cấm vĩnh viễn `hyperopt` và mọi `*Parameter` của Freqtrade;
- `N4` buộc mọi tham số đến từ `config/tool_d_config.yaml`, không nơi nào khác.

Vậy cửa sổ train làm gì? Spec dòng 4326 trả lời: WFO sinh **cặp IS/OOS cho CSCV**. Tức train
dùng để **XẾP HẠNG các arm ablation** (Z0…Z3b, §D0.9), còn test kiểm **thứ hạng đó có giữ được
sang đoạn thời gian sau không**. Không có tham số liên tục nào được khớp.

**Hệ quả phải nhớ khi đọc kết quả D3:** đơn vị phân tích của fold là *thứ hạng giữa các arm*,
không phải *giá trị tuyệt đối của một arm*. Một arm có expectancy dương ở cả 3 fold nhưng thứ
hạng nhảy loạn thì đó là tín hiệu XẤU, dù mọi con số đều dương.

Điều này cũng khép đúng kênh nhiễm mà chính spec tự tố ở LỖI 4 (dòng 5113): *"WFO vẫn để người
vận hành nhìn kết quả rồi quay lại chỉnh ngưỡng — kênh nhiễm đi qua CON NGƯỜI, không qua code."*
Vì không có gì để chỉnh trong vòng WFO, kênh đó bị bịt ở tầng thiết kế chứ không bằng kỷ luật.

---

## 3. Số liệu dùng để quyết — nguồn và mức tin cậy, ghi rõ từng dòng

| Đại lượng | Giá trị | Nguồn | Tin được tới đâu |
|---|---|---|---|
| Cửa sổ WFO `[T1 … T2]` | 12/06/2025 → 29/01/2026 = **231 ngày = 33,0 tuần** | DR-011, `tier_c.data_split` | **Chắc chắn** — mốc đã niêm phong |
| Mật độ lệnh | **17,0 lệnh/mã/năm** | TD-0114 đo thật: 34 lệnh / 2 mã / 12 tháng | ⚠️ **Đo thật nhưng thiên lệch lên** — xem dưới |
| Khâu lọc trend + DG1-5 | giữ lại **8–20%** | `docs/estimate-trades-per-year.md` bước E (D0-PRE) | 🔴 **Ước lượng tay, chưa ai đo** — nguồn bất định lớn nhất (rộng 2,5 lần) |

🔴 **Hai lý do con số 17 lệnh/mã/năm là cận TRÊN, không phải kỳ vọng:**

1. Hai mã đo là **1000BONK + 1000PEPE** — meme coin biến động cao, gần như chắc chắn nằm trên
   trung vị của pool 102 mã.
2. `ZoneAbsorptionMinimal` lúc đó **chưa nối bộ lọc trend (Phần 2) lẫn DG1-5** — tức chưa đi
   qua khâu lọc mạnh nhất của phễu. Con số 17 là lượng lệnh **thô**, trước khâu đó.

**Nhân ra cả pool trong cửa sổ WFO:**

```
17,0 lệnh/mã/năm × 102 mã × 0,632 năm  ≈  1.097 lệnh THÔ
   sau khâu lọc trend + DG1-5 (8–20%)  ≈  88 … 219 lệnh trong TOÀN BỘ cửa sổ
```

---

## 4. Ba phương án đã cân, và số lệnh mỗi fold

| | Cấu trúc | Lệnh mỗi fold test |
|---|---|---|
| **PA-1** ✅ **ĐÃ CHỌN** | neo gốc (anchored), train đầu **12 tuần** + **3** × test **7 tuần** | **19 – 47** |
| PA-2 | neo gốc, train đầu 9 tuần + 4 × test 6 tuần | 16 – 40 |
| PA-3 | trượt (rolling), train 8 tuần + 5 × test 5 tuần | 13 – 33 |

**Mỏng dưới MỌI phương án — đây là sự thật của bài toán, không phải khuyết điểm của cách chia.**
Để so sánh: ngưỡng DSR với `N_ĐĂNG_KÝ = 114` là `√(2·ln 114) ≈ 3,07` sigma. Trên 30 lệnh thì
không phân giải nổi mức đó; con số ra sẽ là nhiễu chứ không phải kết luận.

---

## 5. QUYẾT ĐỊNH

### 5.1 Sơ đồ fold — PA-1: neo gốc, 3 fold

```
T1 = 2025-06-12                                              T2 = 2026-01-29
├──────── train khởi tạo 12 tuần ────────┤
│                                        ├── test fold 1: 7 tuần ──┤
├────────── train (neo gốc, dài dần) ─────────────────────────┤
│                                                             ├── test fold 2: 7 tuần ──┤
├──────────── train (neo gốc, dài dần) ─────────────────────────────────────────┤
│                                                                               ├── test fold 3: 7 tuần ──┤
                                                                                                    T2 ┤
```

- **Neo gốc (anchored), không trượt:** train của mọi fold đều bắt đầu tại `T1` và dài dần.
  Lý do chọn neo gốc thay vì trượt: cửa sổ chỉ có 33 tuần, cắt bỏ phần đầu của train (điều mà
  rolling làm) là **vứt đi dữ liệu vốn đã thiếu**. Trượt chỉ đáng khi có lý do tin rằng dữ liệu
  cũ gây hại (chế độ thị trường đổi hẳn) — chưa có bằng chứng nào cho điều đó ở đây, và
  **giả định không có bằng chứng thì không được đưa vào thiết kế**.
- **3 fold, không nhiều hơn:** ít fold nhất mà vẫn thấy được tính ổn định theo thời gian, nên
  mỗi fold dày nhất có thể.
- Cửa sổ test của ba fold **không chồng lấn nhau** và **nằm trọn trong `[T1, T2]`**.
- **Không fold nào chạm LOCKBOX** (`> T2`) — canh bằng `assert_dataset_timerange()` / `L-Z55`
  đã có sẵn, không viết lại phép kiểm.

### 5.2 🔴 Sàn số lệnh — khai TRƯỚC, không phải bào chữa sau

**`SAN_LENH_MOI_FOLD = 30`.**

Fold nào có **< 30 lệnh** trong cửa sổ test thì mọi chỉ số của fold đó ghi trạng thái
**`unreadable`**, KHÔNG ghi số (`N6`: cấm trả `0.0`, cấm giá trị lính canh, cấm hiện số kèm
cảnh báo — thà để trống).

Con số 30 là **chọn, không phải định lý**, và lý do chọn ghi ở đây để sau này cãi lại được:
dưới 30 lệnh thì sai số chuẩn của expectancy đã lớn hơn chính khoảng cách giữa các arm mà D0.9
định phân biệt, nên con số in ra không mang thông tin — nó chỉ tạo cảm giác có thông tin, đúng
thứ nguy hiểm hơn cả không có số.

### 5.3 🔴 Kết cục đã khai trước cho trường hợp mỏng

Nếu số lệnh đo được rơi vào cận dưới (~88 lệnh cả cửa sổ, tức đa số fold dưới sàn):

**→ D3 kết luận đúng phạm vi của nó: orchestrator ĐÚNG, thống kê CHƯA ĐỌC ĐƯỢC.**

Cụ thể D3 vẫn được coi là hoàn thành nếu 9 bug Tool A (spec dòng 4340) đều có máy canh và
`L-Z45`/`L-Z47` xanh — vì **đó mới là việc của D3**. Phán quyết thống kê hoãn sang **D9**, nơi
WFO chạy trên dữ liệu dài hơn.

**Hai đường KHÔNG được đi, ghi rõ để sau này không ai lách:**

- ❌ **Chia lại fold cho đủ dày sau khi đã thấy số.** Đây chính xác là thứ walk-forward sinh ra
  để chặn. Muốn đổi sơ đồ fold thì phải qua kênh đề xuất đổi tham số (`L-Z26`, sổ
  `param_change_proposals.jsonl`), có luận điểm trích được số, không phải sửa file này.
- ❌ **Nới cửa sổ WFO lấn sang LOCKBOX (`> T2`).** Phá DR-011, đốt lockbox trước D9.5 — sai phạm
  CRITICAL, và **không có lockbox thứ hai** (spec dòng 4002).

---

## 6. Điều kiện mở lại quyết định này

Viết trước, để việc đổi ý phải có căn cứ chứ không phải vì kết quả không đẹp:

1. **Đo được thật khâu lọc trend + DG1-5** (thay ước lượng 8–20% bằng số đo) và số lệnh cả cửa
   sổ vượt **400** → cân nhắc tăng lên 4–5 fold, vì lúc đó mỗi fold vẫn trên sàn 30.
2. **Cửa sổ WFO dài ra** do `T2` dịch (chỉ xảy ra nếu DR-011 được sửa qua kênh chính thức).
3. **Bằng chứng chế độ thị trường đổi hẳn** trong `[T1, T2]` → lúc đó neo gốc mới thành bất lợi
   và rolling mới có căn cứ. Chưa có bằng chứng nào tại thời điểm chốt.

---

## 7. Liên kết

- Việc: `TASKS.md` TD-0140 → TD-0141 (`wfo/folds.py`) đọc file này.
- Ràng buộc mốc dữ liệu: DR-011 (`T0/T1/T2/T3`), `L-Z55`, `assert_dataset_timerange()`.
- Đơn vị đo mỗi fold: DR-013 (`pnl_abs`, ghép fold bằng NHÂN) → TD-0142, `L-Z47`.
- Trạng thái `unreadable`: §0d.6, `L-Z41`, `src/tool_d/measurement/tri_state.py`.
