# DR-D4-19 — Nối lại khâu ĐO D4 (ghi đè có ý thức `DR-IQ-01` §1)

> **Ngày chốt:** 19/09/2026 · **Người quyết:** chủ dự án (phiên mã `58cebb70`, trả lời câu hỏi hướng đi:
> *"Mở khoá, đo D4 ngay"*, rồi duyệt kế hoạch).
> **Chi phí:** **4 suất `B2`** (sổ append-only, không hoàn lại) · `n_used` 4 → 8 · `N = 114` và rào `3,0777` không đổi.
> Mã `DR-D4-19` đặt chỗ bằng commit `cdb37d2` (N12 mục 7c) trước khi file này tồn tại. Commit **RIÊNG và TRƯỚC**
> mọi thay đổi code (lật `D4_DO_TAM_DUNG`) và mọi lần chạy E3.

> 🔴 **PHIÊN SINH Ý TƯỞNG (IDEA) VÀ PHIÊN CHỌN KHÔNG ĐỌC FILE NÀY** (`DR-009`) — soạn bởi một phiên đã thấy
> số đo của Tool D.

---

## 0. Khai thẳng — đây là GHI ĐÈ, không phải thoả điều kiện

`DR-D4-14` §6 đòi đủ ba điều kiện để lật khoá đo. Trạng thái 19/09/2026 đọc từ đĩa:

| # | Điều kiện | Trạng thái |
|---|---|---|
| 1 | `DR-IQ-01` §1 nguyên chữ: dữ liệu MỚI sau `T3 = 2026-09-06` đủ để một phép đo đổi kết luận · DR nối lại viết TRƯỚC · không có ý tưởng (d) đang trong chu trình | ❌ **KHÔNG thoả** — mới 13 ngày dữ liệu sau `T3`; DR này KHÔNG dùng dữ liệu sau `T3` |
| 2 | `TD-0261` ✅ (N theo H14/DR-007) | ✅ `7154d95` — overlap 19,65% < 50%, `N` giữ 114 |
| 3 | Đếm `n` 4 arm trên rổ T1 (0 trial) | ✅ `TD-0345` (`00e0be0`): `Z0-T1` 255 · `Z0` 50 · `Z0-T0` 892 · `Z3` 49 |

⇒ Điều kiện 1 **bị chủ dự án ghi đè**, không được thoả. Nói thẳng để không ai đọc DR này thành *"điều kiện
`DR-IQ-01` đã đạt"*. Tương tự, `DR-HUONG-01` §2 đã loại phương án B (*"gỡ ⏸, chạy D4 → D9 cho ZA LONG"*); DR này
mở **đúng một lô D4**, không mở D5–D9.

**Zone Absorption LONG là giả thuyết ĐÃ CÓ kết quả EXPLORE ≈ 0** (`DR-IQ-01` §0, `TD-0291`: `Z0-T1` mean
−0,0015 R, KTC95 [−0,177; +0,175]). DR này được quyết SAU khi đã thấy con số đó.

`DR-IQ-01`, `DR-HUONG-01`, `DR-D4-12`, `DR-D4-14` **giữ nguyên chữ**; DR này chỉ thêm, không sửa chúng.

## 1. Kết cục đã biết trước, và giá đã được trình

Trình cho chủ dự án TRƯỚC khi chốt (câu hỏi hướng đi, phiên `58cebb70`):
- Tiêu **4 suất `B2`**, không lấy lại được.
- Kết cục **gần như chắc INCONCLUSIVE**: ước lượng từ EXPLORE (`std_R` ≈ 1,14 — KHÔNG phải số đo WFO), ở n = 255
  thuế nhiễu ≈ 0,22 R ⇒ PASS cần mean ≈ 0,32 R, FAIL cần `std_R` ≤ 0,52 (`TASKS.md` dòng TD-0184, đính chính
  19/09). `DR-IQ-01` §2.1 cùng kết luận.
- Va với suất (d) mở 01/10/2026 — giải ở §4.

Chủ dự án chọn đo. Lý do được ghi nhận: **con số THẬT trên WFO** thay cho ước lượng từ EXPLORE, và đóng D4 bằng
hiện vật thay vì để ⏸ vô hạn.

## 2. Phạm vi đo

- Lô **4 arm** theo `DR-D4-12` §4: `Z0-T1` (phán quyết Nhánh 1) · `Z0` (= `Z0-T2`, mốc so) · `Z0-T0` (chẩn đoán)
  · `Z3` (số DCA). Không thêm arm; 5 arm cắt giữ nguyên điều kiện mở lại `DR-D4-12` §4.4.
- Rổ T1 (`config/pool_t1.yaml`, 107 mã), cửa sổ WFO nửa mở **`[T1, T2)` = `[2025-06-12, 2026-01-29)`** (`DR-D9-01`,
  `cua_so_tap()`), `timeframe_detail` 5m, **chỉ LONG** (`enable_short` giữ `false`).
- `hypothesis_slot = DR-D4-19` (`DR-D4-14` §4 để trống cho DR nối lại chốt).
- Bộ chạy: E3 `entrypoints/run_ablation.py --chay` (TD-0335) trong Docker, đúng như đã dựng — **không sửa một dòng
  bộ chạy nào** để đo.
- Chấm: `trial_ledger_audit.py --close-d4-gate` (TD-0337), trong đó gọi `danh_gia_gate_d09` (TD-0336/0341). Đây là
  đường DUY NHẤT chấm cổng §10.2 ⇒ ra kết quả TD-0185 **đồng nghĩa** đóng D4 (TD-0186), ghi `d4_complete`.
- Không ngưỡng nào đổi (`DR-D4-12` §2.4 chốt 1): `0,10 R` · `≥ 20%` · `150 lệnh/năm` · `N = 114` · rào `3,0777`.

## 3. Đọc kết cục — viết TRƯỚC khi đo

| Kết cục Nhánh 1 (`Z0-T1`) | Hành động |
|---|---|
| **PASS** | Ghi nhận. `BEST_KNOWN_DSR_ADJ_EXPECTANCY` chỉ cập nhật theo quy trình sẵn có. Sang D5 **phải có DR riêng** |
| **INCONCLUSIVE** | Ghi đúng tên kết cục vào `d4_han_che`. ZA LONG **quay lại ⏸** theo `DR-IQ-01` §1. **D5 KHÔNG mở tự động** |
| **FAIL** | Phân loại theo §11b của spec (L2/L3) bằng một DR riêng. **Không** tự động tuyên bố dừng dự án |

🔴 **Đính chính `DR-D4-12` §2.3 cho lô này:** §2.3 chốt *"INCONCLUSIVE ⇒ vẫn mở D5 với `Z0-T1`"*. Chốt đó được viết
khi đường ống ZA LONG chưa bị tạm dừng. Dưới `DR-IQ-01` §1 (D5 TD-0258 ⏸) và `DR-HUONG-01` §2, DR này **không** kéo
D5 theo: `d4_complete: true` là điều kiện CẦN để vào D5, không phải lệnh mở D5. Chữ `DR-D4-12` §2.3 giữ nguyên làm
lịch sử.

## 4. Suất (d) — không có hai thứ chạy cùng lúc

`DR-IQ-01` §1 cấm song song một ý tưởng (d) đang trong chu trình với ZA LONG. Hôm nay **chưa có** ý tưởng (d) nào
trong chu trình (suất (d) mở 01/10/2026, `DR-HUONG-01`). Ràng buộc:
- Lô D4 này (chạy E3 + đóng cổng) phải xong **trước 01/10/2026**. Quá hạn mà chưa xong ⇒ dừng, báo chủ dự án, không
  tự kéo dài.
- Sau lô, ZA LONG **về lại ⏸** bất kể kết cục (trừ khi một DR riêng quyết khác sau PASS). `D4_DO_TAM_DUNG` lật lại
  `True` trong commit đóng việc, để E3 không chạy lần hai.
- Thứ tự ưu tiên `DR-HUONG-01` giữ nguyên: suất (d) vẫn là hướng chính.

## 5. Điều kiện dừng

Kế thừa nguyên `DR-D4-14` §7, cộng:
- Lật khoá mà có test nào khác ngoài dòng ghim quyết định phải sửa khẳng định mới xanh ⇒ dừng.
- E3 báo lỗi/từ chối giữa lô ⇒ **không chạy lại tuỳ tiện**. Suất đã có kết quả đầu là CONSUMED (`L-Z53`); suất chưa
  chạy thì refund theo máy. Báo chủ dự án trước khi đặt thêm suất nào.
- Cổng D4 từ chối ⇒ đọc lý do thật, báo; **không nới chốt nào** cho cổng qua.
- Sổ trial tăng khác đúng 4 suất `B2` ⇒ dừng.
- Log chạy cho thấy nến ngoài `[2025-06-12, 2026-01-29)` (chạm LOCKBOX) ⇒ dừng.

## 6. Thi hành

| Bước | Việc |
|---|---|
| 1 | DR này (commit riêng) |
| 2 | `khoa_do.D4_DO_TAM_DUNG = False` + dòng ghim trong test khoá TD-0335 trỏ về DR này (`DR-D4-14` §2.2) |
| 3 | E3 `--chay --hypothesis-slot DR-D4-19` — TD-0184 |
| 4 | `--close-d4-gate` — TD-0185 + TD-0186 |
| 5 | `docs/research-log.md` · đóng ✅ ba dòng · lật khoá về `True` (§4) · mục `MT` ở `back-end-note.md` §7 chờ *"chuẩn hóa và lưu"* |
