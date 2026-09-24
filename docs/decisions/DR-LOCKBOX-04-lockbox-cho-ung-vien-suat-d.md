# DR-LOCKBOX-04 — Ứng viên suất (d) dùng đoạn lockbox `[T2,T3]`; dữ liệu sau `T3` thành lớp XÁC NHẬN trước khi tăng vốn

> **Ngày chốt:** 24/09/2026 · **Người quyết:** chủ dự án (phiên mã `143375ad`, chọn phương án **C** qua công cụ hỏi-chọn,
> sau khi xem bảng so ba phương án A/B/C do phiên này soạn — phương án C được gắn *"(Recommended)"*; khai theo khuôn
> `DR-LOCKBOX-01` §1).
> **Chi phí:** **0 trial**. Không chạm dữ liệu, không chạm lockbox, không đọc file dữ liệu lockbox nào.
> Mã `DR-LOCKBOX-04` + `TD-0381`/`TD-0382` đặt chỗ bằng commit `45f1105` (N12 mục 7c). Commit **RIÊNG và TRƯỚC** mọi dòng mã.

> 🔴 **PHIÊN SINH Ý TƯỞNG (IDEA) VÀ PHIÊN CHỌN KHÔNG ĐỌC FILE NÀY** (`DR-009`). Lý do riêng của file này, ngoài lý do chung:
> nó nói lockbox của ứng viên nằm ở giai đoạn nào. Người sinh ý tưởng mà biết điều đó thì ý tưởng sẽ bị kéo về phía chế
> độ thị trường của chính giai đoạn đó — đúng thứ lockbox tồn tại để bắt.

---

## 0. Khai thẳng — viết khi nào

- Viết **sau** khi Zone Absorption LONG đã có kết cục ở cổng D4 (`DR-ZA-01`), tức sau khi biết ứng viên đầu tiên không đi
  tới lockbox. Đó chính là lý do đoạn `[T2,T3]` còn nguyên.
- Viết **trước** lần CHỌN còn hiệu lực đầu tiên của suất (d). Tại commit này, `registry/idea_queue.jsonl` có đúng một lần
  CHỌN (`IQ-0002`, `selected_at = 2026-09-18T13:27:23Z`) và lần đó **đã `VOIDED`** (`DR-IQ-02`) ⇒ chưa có ý tưởng nào
  đang được chọn. Kiểm được bằng thứ tự commit.
- DR này không chứa số kết quả nào của Tool D.

## 1. Vấn đề — một đoạn lockbox sẽ bỏ không, còn ứng viên thì chờ

`DR-IQ-01:86,125` và `DR-HUONG-01` §5 chốt: ứng viên chọn qua suất (d) dùng lockbox trên dữ liệu **sau `T3 = 06/09/2026`**.
Đặt cạnh điều kiện chất lượng lockbox của spec (`tool-d-smart-dca.md:3296-3304`):

- (a) độ dài ≥ 20% tổng dữ liệu. Với `T0 = 09/04/2024` (`DR-D0PRE-07`), đoạn mới bắt đầu từ `T3` phải dài **≥ ~220 ngày**
  ⇒ sớm nhất khoảng **giữa tháng 4/2027**;
- (b) phải chứa một chế độ thị trường khác CALIB+WFO. Không ai hẹn trước được thị trường, nên mốc trên có thể còn lùi.

Trong khi đó đoạn `[T2,T3]` = 29/01 → 06/09/2026 (`lockbox_seal_1.json`, rổ cấp lại theo `DR-LOCKBOX-01`) **chưa bị chạm
lần nào**: ứng viên duy nhất từng được giao dừng ở D4, không có bản ghi truy cập lockbox nào. Nó đã thoả (a) và (b) bằng
số đo lúc niêm phong (`DR-D0PRE-07` §3). Ứng viên kia đã `retest_forbidden` ở cấu hình đó (`DR-ZA-01` §2), nên giữ lập
trường cũ nghĩa là đoạn này **không ai dùng, mãi mãi**.

**Lời giao cũ không còn đường thi hành:** `DR-TRIEN-KHAI-01` §1 (19/09) giao `[T2,T3]` cho Zone Absorption LONG và buộc ý
tưởng (d) dùng dữ liệu sau `T3`. Hai ngày sau, `DR-ZA-01` §2 chốt **0 suất tiêu thêm** cho ZA LONG, không chạy D5/D9 ở chu
trình này ⇒ ZA không tới D9.5 ⇒ lời giao đó không bao giờ được dùng. DR này **thay** đúng dòng đó của `DR-TRIEN-KHAI-01`
§1 (dòng *"`DR-HUONG-01` §5 (dữ liệu sau `T3` thuộc ai)"*); các dòng khác của `DR-TRIEN-KHAI-01` không đổi. Từ lúc ứng viên
(d) đầu tiên được CHỌN còn hiệu lực, `[T2,T3]` thuộc ứng viên đó; mọi DR sau này muốn mở lại ZA LONG phải tự tìm lockbox
khác.

**Các chỗ ghi *"lockbox MỚI"* không cần đính chính** — `DR-ZA-01` §2 dòng 5, `DR-IQ-03` (dòng *"Ý tưởng được chọn cần
lockbox MỚI"*), `DR-Q4-2026` (cùng câu): cả ba đòi lockbox trên dữ liệu chưa từng dùng, và `[T2,T3]` thoả. `DR-Q4-2026` là
file phiên CHỌN đọc; không sửa nó để khỏi lộ lockbox là đoạn nào (xem khung đầu file).

**Chữ spec không cấm dùng đoạn này:** `:4134` đòi *"lockbox trên dữ liệu CHƯA TỪNG DÙNG"* — đoạn `[T2,T3]` chưa từng dùng.
`:3369` (*"LOCKBOX MỚI"*) nằm trong nhánh kết cục **sau** một lần chạm lockbox; ở đây chưa có lần chạm nào. Lập trường
*"phải là dữ liệu sau `T3`"* là **diễn giải** của `DR-IQ-01`, không phải chữ spec.

## 2. Quyết định

| # | Chốt |
|---|---|
| 1 | Ứng viên **đầu tiên** được CHỌN qua suất (d) dùng đoạn lockbox `[T2,T3]` cho lần chạm D9.5 duy nhất của nó. Seal hiệu lực và rổ theo `DR-LOCKBOX-01` (`seal_hieu_luc_doan_1()`, rổ tại `T2`) — DR này **không** đổi cách niêm phong |
| 2 | Mốc `T0`/`T1`/`T2`/`T3` (`DR-D0PRE-07`) **giữ nguyên** cho ứng viên: CALIB `[T0,T1]`, WFO `[T1,T2]`, LOCKBOX `[T2,T3]`. Không dời mốc theo ý tưởng |
| 3 | **Lớp xác nhận:** dữ liệu sau `T3` không còn là lockbox của ứng viên mà là **lớp xác nhận trước khi tăng vốn**. Ứng viên PASS lockbox được đi D10 → D11 → D12 như thường, nhưng vốn **không vượt mức D12** cho tới khi dữ liệu sau `T3` có **≥ 30 lệnh** của đúng cấu hình đã chạm lockbox **VÀ** đạt ngưỡng xác nhận ở §3 |
| 4 | Quy tắc nhường dữ liệu sau `T3` của `DR-HUONG-01` §5 **giữ nguyên cơ chế**; chỉ đổi **mục đích** của phần nhường: từ *"lockbox của ứng viên"* sang *"lớp xác nhận của ứng viên"* |
| 5 | Chỉ áp cho **một** ứng viên. Đoạn `[T2,T3]` bị chạm (bất kể kết cục) ⇒ ứng viên sau đó quay về lập trường cũ: lockbox trên dữ liệu chưa từng dùng, tức sau `T3` và ngoài phần đã dùng làm lớp xác nhận |
| 6 | `DR-LOCKBOX-03` (điều kiện ĐƯỢC chạm: D9 PASS, hoặc INCONCLUSIVE kèm ngưỡng ký trước) **áp nguyên** cho ứng viên này |

## 3. Lớp xác nhận — ô ký, ⏳ CHỜ CHỦ DỰ ÁN ĐIỀN

| Đại lượng (đo trên dữ liệu sau `T3`, cấu hình đã chạm lockbox, không đổi tham số) | Ngưỡng | Trạng thái |
|---|---|---|
| Số lệnh đã đóng `n` | ≥ 30 (cùng sàn `DR-011`, spec `:3302`) | ✅ chốt ở DR này |
| Chỉ số phán quyết thứ hai (tên + ngưỡng) | `......` | ⏳ chưa điền ⇒ `+inf` ⇒ **không được tăng vốn** |

- Ô trống = `+inf` (`L-Z35`, N6): lớp xác nhận **không thể vô tình PASS**. Hậu quả của việc không điền là **vốn đứng ở mức
  D12**, không phải được tăng.
- Ô phải được điền và commit **trước lần chạm D9.5 của ứng viên**, cùng lúc với ngưỡng PASS lockbox của nó (`TD-0274`).
  Kiểm bằng thứ tự commit. Điền sau khi thấy số trên dữ liệu sau `T3` là chọn ngưỡng theo kết quả.
- Không đạt ⇒ vốn không tăng; xử tiếp theo `DR-011`/`DR-012` như một kết cục thật, **không** coi là lý do chỉnh tham số.

## 4. Điều kiện kèm theo — viết trước

1. **Chỉ hiệu lực khi DR này commit trước lần CHỌN còn hiệu lực đầu tiên** (§0). Có một lần CHỌN còn hiệu lực trước commit
   này ⇒ DR vô hiệu với ý tưởng đó, quay về `DR-IQ-01`.
2. **`selection_reason` không được viện dẫn diễn biến thị trường sau `T2`.** Phiên CHỌN không đọc DR này (DR-009), nên điều
   kiện này do một phiên **không phải IDEA/CHỌN** kiểm ngay sau khi dòng CHỌN được ghi, **trước suất trial đầu tiên** của
   slot `IQ-xxxx`. Vi phạm ⇒ huỷ chọn bằng sự kiện `VOIDED` (`DR-IQ-02` §4.3, trích mã DR này).
   ⚠️ `VOIDED` chỉ ghi được khi slot **chưa có trial nào** (`DR-IQ-02` §4.3 điều 2). Phát hiện vi phạm **sau** suất đầu tiên
   ⇒ không huỷ được chọn, nên ứng viên **mất quyền dùng `[T2,T3]`** và quay về lập trường `DR-IQ-01` (lockbox sau `T3`).
3. **Ngưỡng PASS lockbox của ứng viên viết trước, theo từng hướng** (Long / Short riêng) — việc của `TD-0274` cho ứng viên
   này. Lý do riêng ở đây: đoạn `[T2,T3]` chỉ có một chế độ thị trường, nên kết quả trên nó lệch theo hướng giao dịch.
4. **Rổ:** nếu ứng viên cần một rổ khác rổ `T2` của `DR-LOCKBOX-01` ⇒ cần DR riêng trước khi cấp lại seal, không tự dời.

## 5. Điểm yếu — khai thẳng

- **Nhiễm hậu kiến.** Mọi người sinh ý tưởng hôm nay đều đã sống qua giai đoạn `[T2,T3]`. Ý tưởng có thể vô tình hợp với
  đoạn đó mà không ai định thế. Mức nhiễm này **ngang** mức của ứng viên đầu tiên lúc niêm phong (`T3` = ngày niêm phong =
  ngày dự án mở), nhưng "ngang" không phải "bằng không". Lớp xác nhận (§2 dòng 3) tồn tại để bù đúng điểm yếu này.
- **Một chế độ thị trường.** Lockbox này chỉ chứa một kiểu thị trường; ứng viên PASS trên nó chưa được kiểm ở kiểu khác.
  Cũng do lớp xác nhận bù, và do §4 điều 3.
- **Viết sau khi biết ứng viên đầu tiên không tới lockbox** — đúng hình *"lúc đang thua là lúc muốn thay nhất"*
  (`DR-Q3-2026` §2). Giảm nhẹ: DR không đổi ngưỡng nào, không đổi mốc nào, chỉ đổi **ai** được dùng một đoạn chưa ai dùng.
- **Diễn giải, cãi lại được:** đọc `:3369` là *"chỉ áp sau một lần chạm"* là diễn giải của DR này.
- **Phương án bị loại:** A — giữ nguyên, chờ tới ~04/2027 (đoạn `[T2,T3]` bỏ không vĩnh viễn); B — dùng `[T2,T3]` mà không
  có lớp xác nhận (không có lớp chặn nếu ý tưởng chỉ hợp với đoạn đó).

## 6. Điều kiện dừng

1. Có ai đề nghị chạm đoạn `[T2,T3]` lần thứ hai, cho ứng viên thứ hai, hay "thử cấu hình khác" trên nó ⇒ dừng (`DR-011`).
2. Có ai đề nghị điền hoặc nới ngưỡng §3 sau khi đã thấy số trên dữ liệu sau `T3` ⇒ dừng.
3. Có ai đề nghị tăng vốn quá mức D12 khi §3 chưa đạt, kể cả "tạm thời" ⇒ dừng (spec `:3419`).

## 7. Thi hành

| Mã | Việc |
|---|---|
| TD-0381 | DR này + đính chính nối cuối `DR-IQ-01`, `DR-HUONG-01` và `DR-TRIEN-KHAI-01` (giữ nguyên chữ cũ) |
| TD-0382 | Máy canh lớp xác nhận (§2 dòng 3, §3) — cần lệnh *"bắt đầu code"* |
| (MT) | Ghi một mục `MT` vào `back-end-note.md` mục 7 — chờ *"chuẩn hóa và lưu"* (N9) |

---

> ✅ **Ô KÝ §3 ĐÃ ĐIỀN — 24/09/2026, chủ dự án chọn qua công cụ hỏi-chọn (phiên mã `143375ad`, `TD-0386`). Nối cuối,
> bảng §3 giữ nguyên chữ.** Tại thời điểm điền: chưa có ứng viên nào được CHỌN còn hiệu lực, chưa có lần chạm lockbox nào,
> chưa có lệnh nào sau `T3` được đo cho bất kỳ cấu hình nào ⇒ ngưỡng được chốt **trước khi thấy số**.
>
> | Ô | Giá trị |
> |---|---|
> | Chỉ số phán quyết thứ hai | **`mean_r`** — trung bình `r_trien_khai` mỗi lệnh (`LenhWFO.r_trien_khai`, khoá `mean_r` của `ablation/ban_ghi.py:thong_ke_arm`), **không** trừ thuế DSR |
> | Ngưỡng | **≥ 0,10 R** — đúng ngưỡng kinh tế đang có của Nhánh 1 (`gates/thresholds.py` `DSR_ADJ_EXPECTANCY_MIN`), không đặt số mới |
> | Dữ liệu | backtest cấu hình đã chạm lockbox, trên dữ liệu **từ ngày CHỌN** của ứng viên (không phải từ `T3`), đo **đúng một lần** — máy thi hành ở `TD-0387`, bộ đo ở `DR-XAC-NHAN-01` |
>
> **Vì sao không dùng `dsr_adjusted_expectancy`:** lớp xác nhận là **một** phép thử đăng ký trước, không phải chọn cái tốt nhất
> trong `N` phép thử — khoản phạt đa phép thử đã trả ở lần chạm lockbox. Với độ lệch chuẩn minh hoạ ~1,1 R/lệnh (giả định,
> chưa đo trên ứng viên nào), ở n = 30 thuế DSR ≈ 3,08 × 1,1 / √30 ≈ 0,62 R ⇒ `dsr_adj ≥ 0` đòi mean ≈ 0,62 R, gần như
> không bao giờ đạt, tức vốn khoá vĩnh viễn.
>
> **Đánh đổi đã trình (cùng giả định):** không có lợi thế vẫn lọt ~31% (P(mean ≥ 0,10 | 0) ở n = 30); lợi thế thật 0,3 R qua
> ~84%. Các phương án bị loại: `mean_r ≥ 0` (lọt ~50%), cận dưới KTC95 ≥ 0 (lợi thế 0,3 R chỉ qua ~31%, vốn đứng yên lâu),
> `dsr_adj ≥ 0` (như trên). Hướng sai của ngưỡng đã chọn là **cho tăng vốn nhầm ~31% khi không có lợi thế** — chấp nhận vì
> đây là lớp THỨ HAI sau lockbox PASS, không phải lớp duy nhất.
