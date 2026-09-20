# DR-D4-20 — Luật vào lệnh theo đúng spec LD-13 + tranche 2/3 đặt lệnh chờ TRƯỚC

> **Ngày chốt:** 20/09/2026 · **Người quyết:** chủ dự án (phiên mã `dd855fee`, trả lời ba câu: luật *"đúng spec
> LD-13"* · tranche 2/3 *"đặt lệnh chờ trước theo §3.5"* · giao lại ba khoá mồ côi; duyệt kế hoạch).
> **Chi phí:** **0 trial** — `DR-012` Hạng 1 (mã không khớp spec, sửa tự do). Không chạm lockbox, không gỡ ⏸ nào.
> Mã `DR-D4-20` + `TD-0354`…`TD-0358` đặt chỗ bằng commit `4794d3f` (N12 mục 7c) trước khi file này tồn tại.

> 🔴 **PHIÊN SINH Ý TƯỞNG (IDEA) VÀ PHIÊN CHỌN KHÔNG ĐỌC FILE NÀY** (`DR-009`).

---

## 1. Hai chỗ mã không khớp spec — độc lập nhau

### 1.1 Tranche 1 vào lệnh ở giá mà sàn thật từ chối

Đọc mã nguồn Freqtrade 2026.8 trong image (N7/quy tắc 6, không suy):

- `backtesting.py:1147-1160` `_enter_trade` → `get_valid_entry_price_and_stake(..., propose_rate=row[OPEN_IDX], ...)`;
- `:1038-1056` gọi `custom_entry_price(proposed_rate=row[OPEN_IDX])` rồi **KẸP**: LONG `propose_rate = min(propose_rate, row[HIGH_IDX])`;
- `:1240` `_get_order_filled(rate, row)` → khớp khi `low ≤ rate ≤ high`.

⇒ Nến mà **cả nến nằm dưới `p1`**: lệnh bị kéo về đỉnh nến và khớp ở đó — có thể **dưới `sl`** (ca `D-0015`,
`708a268`). Nến **mở dưới `p1` rồi bật lên trên**: lệnh khớp đúng `p1`, **trông hoàn toàn bình thường**.

Sàn thật: lệnh **mua post-only đặt trên giá thị trường** lấy thanh khoản ⇒ **bị từ chối**, không khớp
(spec `:1175`, §3.5 LD-13). Cả hai ca trên đều là lệnh live KHÔNG BAO GIỜ có.

### 1.2 Tranche 2/3 đặt lệnh SAI THỜI ĐIỂM

`ZoneAbsorption.py:1408` chỉ bơm khi giá **đã xuống tới** mức (`current_rate > muc ⇒ return None` cho LONG), và
`backtesting.py:721` truyền `current_rate = row[OPEN_IDX]`. Lúc đó lệnh mua tại `p2`/`p3` nằm **trên** giá thị
trường ⇒ live từ chối y như §1.1. Spec `:1180` viết tranche 2/3 là *"lệnh chờ sống trong cửa sổ DG4"* — tức
**đặt TRƯỚC rồi nằm chờ**, không phải chờ giá tới rồi mới đặt.

Backtest có giữ lệnh chờ qua nến: `manage_open_orders`/`check_order_cancel` (`:1330`, `:1378`) huỷ theo
`unfilledtimeout`, không huỷ ngay cuối nến. Nên mô hình lệnh chờ chạy được ở **cả** backtest và live.

## 2. Quyết định

| # | Chốt |
|---|---|
| 1 | **Luật LD-13, mức ĐÚNG SPEC:** giá thị trường **lúc đặt** thấp hơn giá lệnh (LONG) ⇒ **KHÔNG đặt lệnh**. Áp cho **mọi tranche** |
| 2 | ❌ **Loại mức HẸP** (*"cả nến dưới `p1`"*): nó chỉ bắt ca khớp ở đỉnh nến, để lại ca *"mở dưới `p1`, bật lên trên"* — lệnh live không có, mà mọi bảng kết quả trông bình thường. Đúng hình dạng lỗi im lặng dự án này sinh ra để chặn |
| 3 | **Tranche 2/3 đặt lệnh chờ TRƯỚC:** đặt tại `p2`/`p3` khi giá còn **trên** mức, trong cửa sổ DG4; bỏ điều kiện *"chỉ bơm khi giá đã xuống tới mức"* |
| 4 | **Nguồn giá thị trường lúc đặt = `proposed_rate` của `custom_entry_price`** (tranche 1) và `current_rate` của `adjust_trade_position` (tranche 2/3). Freqtrade truyền giá MỞ nến ở backtest và giá hiện hành ở live ⇒ **một đường mã cho mọi chế độ**, không rẽ nhánh theo runmode |

**Vì sao chốt 4 quan trọng:** `confirm_trade_entry` nhận `rate` **đã bị kẹp**, nên một chốt dựa vào `rate` sẽ
hành xử khác nhau giữa backtest và live — đúng lỗ hổng parity mà `DR-D4-05` đã phải sửa một lần.

## 3. KHÔNG thuộc DR này

- Cổng `L-Z3` (`liq_buffer_ratio ≥ 8`) lúc vào lệnh — `MT-69`, chưa có mã, **vẫn chưa có** sau DR này.
- Câu giá thanh lý dịch đệm hay thô — `MT-70`, chờ chủ dự án.
- Bật `enable_short`; đổi arm sản xuất (`TD-0227`); gỡ ⏸ nào; lật `D4_DO_TAM_DUNG` (đang `False` từ `50249a3`).
- Đổi `N = 114`, rào DSR, ngưỡng §10.2.

## 4. Hệ quả phải khai — số cũ mất hiệu lực SO SÁNH

Bản vá đổi **luật vào lệnh của mọi arm**. Vì vậy, theo đúng `spec:4338` (*"mỗi lần đổi pool = mọi số cũ không so
sánh được"*, cùng lý lẽ cho đổi luật vào lệnh):

- `TD-0345` (`Z0-T1` 255 · `Z0` 50 · `Z0-T0` 892 · `Z3` 49, rổ T1) — **đo trên hệ thống CŨ**, không so trực tiếp.
- Δ_R của D3.5 (`dr015-buoc1-delta-r.json`, artifact niêm phong `L-Z56`) — đo trên cùng đường backtest cũ.
  **KHÔNG sửa artifact** (nó là bằng chứng đã niêm phong); ghi hạn chế và đo lại khi tới lượt.
- Mọi phễu EXPLORE trước 20/09/2026.
- `OQ-16` (`back-end-note.md`, phiên `69e2254e` ghi 19/09) lấy `σ` từ **bản ghi arm WFO của lô `DR-D4-19`** — lô
  đó dừng giữa chừng và thuộc hệ thống cũ ⇒ khi `OQ-16` được chốt, nó phải trỏ sang nguồn `σ` của lô đo lại.

### 4.1 `D-0015` — suất đã tiêu, thuộc hệ thống CŨ

`D-0015` (`Z0-T1`, `708a268`) CONSUME với lỗi sau con dấu, không hoàn lại được (`L-Z53`). Nó **không** được dùng
làm kết quả của bất kỳ arm nào: hệ thống đã đổi luật vào lệnh. `n_used = 5/114` giữ nguyên, không viết lại sổ.

### 4.2 Ngân sách lô đo lại — CHƯA QUYẾT ở DR này

`DR-D4-19` §5: *"Sổ trial tăng khác đúng 4 suất B2 ⇒ dừng"*. Lô đo lại 4 arm cần **thêm 4 suất** (`n_used` 5 → 9).
Đây là **mở lại ngân sách** của `DR-D4-19` ⇒ **trình chủ dự án**, kèm số đo `TD-0358`. 🔴 Không tự chạy.
Nếu số đo cho `n < 30` hoặc lệnh/năm dưới sàn 150 (§10.2) ⇒ khuyến nghị **không** chạy lô.

## 5. Điều kiện dừng — viết TRƯỚC

1. Một test cũ phải **sửa khẳng định** mới xanh ⇒ dừng, báo (kế thừa `DR-D4-14` §7).
2. Cần sửa `L-Z56`, artifact niêm phong D3.5, hay `validate_arm_record()` để đi tiếp ⇒ dừng.
3. Sổ trial hoặc `runtime_state.json` đổi dù một dòng trong lúc vá ⇒ dừng (bản vá là 0 trial).
4. Đọc mã nguồn Freqtrade thấy khác mô tả §1 ⇒ dừng, sửa DR trước, không vá theo trí nhớ.
5. `unfilledtimeout.entry = 180` phút (3 nến) cắt ngắn cửa sổ DG4 8 nến ⇒ **ghi nợ `MT` và báo**, không tự đổi
   `config.json` (con số đó do spec `:1198` chốt và có `L-Z42` canh).

## 6. Hành vi mong đợi sau khi vá — ghi trước để không đọc nhầm là lỗi

- Số lệnh **giảm** ở mọi arm (bỏ lệnh live không có). Giảm bao nhiêu: `TD-0358` đo, không đoán.
- Tranche 2/3 **có thể tăng** số lần khớp (trước đây gần như không đặt được lệnh hợp lệ). Chiều và độ lớn: đo.
- Lệnh khớp **dưới `sl`** phải biến mất hoàn toàn — nếu còn, bản vá chưa đúng chỗ.

## 7. BỔ SUNG 20/09/2026 — chủ dự án duyệt 4 suất `B2` cho lô ĐO LẠI

§4.2 để ngỏ ngân sách và ghi *"trình chủ dự án"*. Sau khi đọc số đo `TD-0358` (`Z0-T1` 162 → 137 lệnh trên cùng
tập EXPLORE; lớp lệnh sàn thật từ chối về 0; `Z3` 23/32 lệnh bơm nhiều tranche), chủ dự án chốt: **chạy lô**.

| Mục | Chốt |
|---|---|
| Ngân sách | **4 suất `B2`** cho 4 arm (`DR-D4-12` §4). `n_used` 5 → **9**/114. `N = 114` và rào `3,0777` KHÔNG đổi |
| `hypothesis_slot` | **`DR-D4-20`** — lô này chạy trên hệ thống ĐÃ VÁ. Slot khác `DR-D4-19` để sổ tự phân biệt hai hệ thống, không cần ai nhớ |
| `D-0015` | Giữ nguyên trong sổ, **thuộc lô cũ** (`DR-D4-19`, hệ thống chưa vá). KHÔNG dùng làm kết quả của arm nào, KHÔNG viết lại sổ |
| Trần suất không hoàn | `B2` không REFUND tối đa **5** = 1 (`D-0015`, lô cũ) + 4 (lô này). Suất thứ 6 ⇒ cần DR mới |

🔴 **Chốt máy phải đổi theo** (`tests/unit/test_registry_schemas.py`): bản cũ ghim *"mọi `B2` mang slot
`DR-D4-19`"* và *"≤ 4 suất không hoàn"* — đúng chữ `DR-D4-19` §5 lúc đó. Nay ghim: slot thuộc
`{DR-D4-19, DR-D4-20}`, `DR-D4-19` giữ **đúng 1** suất không hoàn (`D-0015`), `DR-D4-20` tối đa **4**. Sửa khẳng
định của một test khoá — chủ dự án duyệt cùng quyết định này, và chốt mới CHẶT HƠN bản cũ ở chỗ nó tách trần
theo từng lô thay vì một con số gộp.

**Điều kiện dừng của lô, kế thừa `DR-D4-19` §5 nguyên văn:** lỗi/từ chối giữa lô ⇒ không chạy lại tuỳ tiện; cổng
D4 từ chối ⇒ đọc lý do thật, không nới chốt nào; sổ tăng khác đúng 4 suất `B2` ⇒ dừng; log cho thấy nến ngoài
`[2025-06-12, 2026-01-29)` ⇒ dừng.
