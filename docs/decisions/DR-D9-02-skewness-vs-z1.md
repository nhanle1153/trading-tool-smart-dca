# DR-D9-02 — `MT-53`: tiêu chí "skewness không âm hơn skewness(Z1) quá 0,5"

> **Ngày chốt:** 17/09/2026 · **Người quyết:** chủ dự án (duyệt kế hoạch đánh giá tổng hợp §7.1, phiên `-33`)
> **Giải:** `MT-53` (`back-end-note.md` mục 7) · **Mở lại:** `DR-D4-12` §4.5 (hai đường *"chưa chọn"*) · **0 trial**
> **Chốt KHI CHƯA tồn tại một con số skewness nào** của bất kỳ arm nào trên bất kỳ tập dữ liệu nào (kiểm:
> `grep -rn skew docs/du-lieu-do/` rỗng ngày 17/09/2026). Commit RIÊNG và TRƯỚC mọi dòng mã của TD-0289.
> Đã nhắn `-30`/`-01` mã `DR-D9-02` + `TD-0289` trước khi mở file (N12 mục 6).

---

## 0. Vì sao cần DR này

Spec `:4273` (§10.2 Nhánh 1): *"✅ skewness(cấu hình tốt nhất) không âm hơn skewness(Z1) quá 0.5"*. Đây là
**dòng duy nhất** trong spec nhắc skewness — **không kèm lý do**. `DR-D4-12` §4 cắt arm `Z1`, nên §4.5 tự khai
tiêu chí thành `pending` và nêu hai đường mà không chọn. Hệ quả đã thi hành trong máy (`gates/d9_gate.py`,
TD-0285): tiêu chí `pending` ⇒ **Nhánh 1 không thể PASS trọn** — ở D4 lẫn D9 — dù chiến lược tốt đến đâu.

Một cổng không bao giờ PASS được thì sớm muộn bị nới **sau khi** đã thấy số. Chốt bây giờ, trước mọi con số.

## 1. Tiêu chí sinh ra để chặn gì — DIỄN GIẢI, cãi lại được

`Z1` = *"entry đơn, xác nhận entry, SL = 2,2 × ATR cố định (kiểu v1)"* (spec `:4155`) — mốc **không neo zone**,
**không DCA**. So skewness với mốc đó là để bắt một cấu hình có expectancy dương nhờ **đuôi lỗ ẩn** (thắng nhỏ
đều, thỉnh thoảng lỗ lớn) — hình rủi ro điển hình của **trung bình giá xuống**, đúng thứ ba tranche DCA tạo ra.

🔴 Spec không nói điều này bằng chữ. Nếu ai tìm được câu spec nói tiêu chí có mục đích khác, DR này phải mở lại.

## 2. Ba đường, so bằng hậu quả

Sai số chuẩn xấp xỉ của skewness mẫu: `SE ≈ √(6/n)` (phân phối gần chuẩn; đuôi dày thì còn lớn hơn).

| Đường | `n` mốc so (`DR-D4-10` §2.1) | `SE` mốc so | Hậu quả |
|---|---|---|---|
| (i) Chạy thêm `Z1` | 8 | ≈ 0,87 | Tốn 1 suất B2 để mua một con số mà sai số chuẩn lớn hơn chính ngưỡng 0,5 |
| (a) Đổi mốc so thành `Z0` | 28 | ≈ 0,46 | Ngưỡng 0,5 ≈ 1 sai số chuẩn ⇒ tiêu chí thành **tung đồng xu**: chặn hay cho qua do nhiễu. Và `Z0` **cùng họ SL neo zone** với ứng viên `Z0-T1` ⇒ phép so không còn hỏi câu §1 |
| **(b′) Không áp dụng có căn cứ cho cấu hình ENTRY ĐƠN; tự khôi phục cho cấu hình DCA** | — | — | Giữ đúng mục đích §1; không để nhiễu phán quyết |

## 3. Quyết định — (b′)

### 3.1 Phạm vi áp dụng, máy đọc được

- **Không áp dụng** khi cấu hình được đem phán quyết thuộc `arm_switches.ARM_DON_TRANCHE`
  (`Z0`, `Z1`, `Z0-T0`, `Z0-T1`, `Z0-V1`, `Z0-S1` — tập mã đã dùng để tắt DG1–DG5, `MT-44`). Không chép lại danh
  sách: đọc đúng hằng số đó.
- **Áp dụng, chặn như cũ** khi cấu hình thuộc arm DCA (`Z2`, `Z3`, `Z3b`). Khi đó mốc so `Z1` phải có **n ≥
  `tier_c.wfo_folds.san_lenh_moi_fold`** (30, dùng lại, không số mới); thiếu ⇒ `pending` ⇒ không PASS.

### 3.2 Vì sao không phải nới chuẩn

1. Entry đơn với SL bất biến (`tier_c.sl_immutable: true`) **không tạo được** đuôi lỗ kiểu trung bình giá xuống.
2. Đuôi lỗ **từng lệnh** đã có tiêu chí riêng, đo được, vẫn **chặn**:
   `max_single_trade_loss / risk_budget ≤ 1,15`.
3. Chốt **trước** khi có số (§0). Ngưỡng 0,5 **không đổi**; chỉ phạm vi áp dụng được khai.
4. Ứng viên đổi sang DCA thì tiêu chí **tự quay lại** — không có đường nào lặng lẽ bỏ nó cho arm DCA.

### 3.3 Không được im lặng

- Skewness của cấu hình được phán quyết **vẫn được đo và báo cáo** (mô tả, không chặn), ba trạng thái N6.
- Kết quả cổng phải **liệt kê tường minh** tiêu chí "không áp dụng" kèm mã DR này — không được xoá khoá khỏi danh
  sách tiêu chí để nó biến mất.
- "Không áp dụng có căn cứ" **khác** "chưa đo" (`pending`) và **khác** "đạt".

## 4. Thi hành — TD-0289 (chờ "bắt đầu code")

- `gates/thresholds.evaluate_branch1(metrics, *, pbo_chan, arm)` — `arm` bắt buộc, không mặc định. Arm entry đơn ⇒
  `skewness_diff_vs_z1` vào danh sách `khong_ap_dung` của `GateResult`, không vào `failed_criteria`.
- `gates/d9_gate.danh_gia_cong_d9(..., arm)` — cùng luật; `chi_so` vẫn nhận khoá skewness (khai `pending` được).
- `tests/lock/test_lz35_gate_fail_closed.py`: ca cũ **giữ nguyên** khẳng định 7 tiêu chí dưới một arm DCA; thêm ca
  arm entry đơn ⇒ 6 lỗi + 1 "không áp dụng".
- Test khoá mới: entry đơn + skewness `pending` ⇒ **không** chặn · DCA + skewness `pending` ⇒ **chặn** · arm lạ ⇒ raise.
  Kiểm-có-răng: coi mọi arm là entry đơn ⇒ ca DCA đỏ; coi mọi arm là DCA ⇒ ca entry đơn đỏ.

## 5. Điều kiện mở lại

1. Tìm được căn cứ spec cho mục đích khác của tiêu chí (§1).
2. Chủ dự án chọn đưa DCA trở lại làm ứng viên — tiêu chí tự áp dụng; cần kế hoạch đo `Z1` đủ mẫu.
3. Phát hiện cấu hình entry đơn tạo đuôi lỗ ngoài SL (gap, funding, thanh lý) — xem lại cùng `max_single_trade_loss`.

## 6. Phương án đã loại

| Loại | Vì sao |
|---|---|
| (i) chạy `Z1` | n = 8, sai số > ngưỡng; tốn suất |
| (a) mốc `Z0` | Tung đồng xu ở n = 28; mất câu hỏi gốc |
| Bỏ hẳn tiêu chí cho mọi arm | Mất lớp bảo vệ cho đúng loại cấu hình nó sinh ra để canh (DCA) |
| Đặt ngưỡng skewness tuyệt đối mới (vd ≥ −0,5) | Thêm một con số không ai đăng ký, đúng lỗi `DR-D4-02` chặn |
