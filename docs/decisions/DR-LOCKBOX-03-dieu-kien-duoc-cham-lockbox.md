# DR-LOCKBOX-03 — Điều kiện ĐƯỢC CHẠM lockbox ở D9.5, viết TRƯỚC khi thấy số D9

> **Ngày chốt:** 20/09/2026 · **Người quyết:** chủ dự án (chọn *"Có, viết DR chốt điều kiện trước"*, phiên mã `69768527`)
> **Chi phí:** **0 trial**, không chạm dữ liệu. Mã `DR-LOCKBOX-03` + `TD-0365` đặt chỗ bằng commit `0390488` (N12 mục 7c).
> **Nối thêm** cho `DR-TRIEN-KHAI-01` §3 — **không sửa một chữ nào** của DR đó, cũng không sửa `DR-LOCKBOX-01`/`-02`.

> 🔴 **PHIÊN SINH Ý TƯỞNG (IDEA) VÀ PHIÊN CHỌN KHÔNG ĐỌC FILE NÀY** (`DR-009`) — soạn bởi một phiên đã thấy số D4.

---

## 0. Khai thẳng — viết sau khi đã thấy số D4, trước khi thấy số D9

Lô `DR-D4-20` đã cho số thật trên WFO (hiện vật bền: `docs/du-lieu-do/d4-lo-dr-d4-20/` + manifest sha256, `47b3060`):
`Z0-T1` n **231**, mean **+0,0035 R**, `dsr_adj` **−0,2216**. DR này được viết **sau** khi biết con số đó và **trước**
khi D5/D9 chạy — nói thẳng để không ai đọc nó như một luật trung lập soạn từ đầu.

Nó **không** đòi dừng đường ống: `DR-TRIEN-KHAI-01` chốt chạy tiếp D5 → D9 → D9.5 bất kể kết cục, và DR này giữ nguyên
điều đó cho D5 và D9. Nó chỉ đặt **một chốt ở đúng một chỗ**: bước chạm lockbox.

## 1. Chỗ trống đang có — vì sao không viết gì cũng là một quyết định

`DR-D9-01` §6.3 viết: *"Việc D9.5 được chạm lockbox hay không đọc `d9_ket_cuc`, **là việc của D9.5**"* — tức giao việc,
chưa ra luật. `DR-TRIEN-KHAI-01` §1 lại chốt *"nối lại toàn bộ đường ống D5 → D9 → D9.5 **ngay**"*. Ghép hai câu đó mà
không thêm gì thì mặc định thành **"chạy tới đâu thì chạm tới đó"**, và cái chốt duy nhất còn lại là trí nhớ con người.

**Vì sao chỗ này đáng một chốt riêng, khác mọi bước trước:** mọi thứ khác trong dự án tiêu **suất trial** — thứ còn 105
suất và tái tạo được bằng cách đăng ký thêm. Lockbox tiêu **đoạn niêm phong**: `access_log.py:5,27` cho **tối đa 3 đoạn**
(1 gốc + 2 gia hạn), và `DR-011` chỉ cho gia hạn khi kết cục là **INCONCLUSIVE**. Chạm bằng một ứng viên rồi mới biết nó
≈ 0 thì đoạn đó **không lấy lại được cho ứng viên sau** — kể cả ý tưởng (d) của `DR-HUONG-01`.

🔑 Lockbox sinh ra để **xác nhận thứ trông có lợi thế**. Đem nó xác nhận thứ vừa đo ≈ 0 không sai về quy trình, nhưng
tiêu một tài nguyên không tái tạo để mua một thông tin đã biết trước phần lớn.

## 2. Luật — fail-closed, mặc định KHÔNG CHẠM

Trước khi E4 được phép chạm lockbox (`touch_lockbox.py`, chế độ chạm thật của `TD-0352`), phải thoả **một trong hai**:

| # | Đường | Điều kiện |
|---|---|---|
| A | **D9 PASS** | `runtime_state.json.d9_ket_cuc == "PASS"` theo đúng `DR-D9-01` §6.2 (gồm PBO ≤ 0,5 là tiêu chí CHẶN). Không cần thêm gì — đây chính là ca lockbox được thiết kế cho |
| B | **D9 INCONCLUSIVE + chủ dự án ký số** | `d9_ket_cuc == "INCONCLUSIVE"` **và** mọi ngưỡng ở §3 đã được chủ dự án điền bằng SỐ **trước khi kết quả D9 được đọc**, và số đo D9 thoả hết |

`d9_ket_cuc == "FAIL"` ⇒ **không chạm**, không có đường B. Muốn chạm sau một FAIL thì cần một DR mới, viết sau khi nhìn
số, khai rõ vì sao — cùng khuôn ngoại lệ 1 của `DR-TRIEN-KHAI-01` §3.

🔴 **Ngưỡng chưa điền = `+inf`, không phải `None`, không phải `0`** (`L-Z35`): bảng §3 để trống thì đường B **không thể
vô tình thoả**. Đây là lý do DR này an toàn khi viết trước — nó không đoán hộ con số nào.

## 3. Ô ký — ⏳ CHỜ CHỦ DỰ ÁN ĐIỀN, mỗi ô một SỐ

| Đại lượng (đo ở D9, hướng LONG) | Ngưỡng để được chạm | Trạng thái |
|---|---|---|
| `dsr_adjusted_expectancy` | `......` | ⏳ chưa điền ⇒ `+inf` ⇒ không chạm |
| `mean_r` (kỳ vọng theo R, chưa trừ thuế nhiễu) | `......` | ⏳ chưa điền ⇒ `+inf` ⇒ không chạm |
| Số lệnh `n` của đoạn test | `......` (sàn cứng 30 đã có ở `TD-0275`/`DR-011`) | ⏳ chưa điền |

**Khuyến nghị của phiên `69768527`, chờ chủ dự án bác hoặc nhận:** `dsr_adj ≥ 0` · `mean_r > 0` · `n ≥ 30`.

Lập luận: `dsr_adj ≥ 0` nghĩa là *"sau khi trừ thuế nhiễu, lợi thế đo được không âm"* — đây là mức **thấp hơn hẳn** rào
PASS `0,10` của Nhánh 1, nên nó **không** biến lockbox thành cổng thứ hai của D9; nó chỉ loại đúng ca đã thấy ở D4
(`dsr_adj = −0,2216`, tức lockbox sẽ xác nhận một thứ mà chính phép đo trước đó nói là không có gì). Đổi lại, nếu số D9
rơi vào khoảng `[0; 0,10)` thì vẫn được chạm — đúng tinh thần *"INCONCLUSIVE thì đi hỏi lockbox"* của `DR-011`.

⚠️ **Đánh đổi phải biết trước khi ký:** chốt này có thể **giữ lại một lợi thế thật**. Nếu chiến lược có edge nhỏ mà D9
đo được `dsr_adj` âm nhẹ do nhiễu, ta bỏ lỡ lần xác nhận. Hướng sai của chốt này là **bỏ lỡ**, hướng sai của việc không
có chốt là **mất vĩnh viễn một đoạn lockbox** — chọn chiều bỏ lỡ vì nó còn đường quay lại, chiều kia thì không.

## 4. Không thuộc DR này

- **Ngưỡng PASS của chính lần chạm** (DSR-adj, `max_single_trade_loss/risk_budget ≤ 1,15`, `liq_buffer ≥ 8`, `n ≥ 30`):
  đó là `DR-011` spec `:3338-3343`, việc của **`TD-0274`**, commit trước suất WFO đầu tiên của D9. Hai câu khác nhau:
  DR này hỏi *"có được chạm không"*, `TD-0274` hỏi *"chạm rồi thì gọi là PASS khi nào"*. Không gộp — gộp là tạo nguồn
  sự thật thứ hai cho ngưỡng lockbox (`N1`/`MT-03`).
- **Rổ và seal dùng cho lần chạm**: `DR-LOCKBOX-01` (rổ T2, seal cấp lại, không ăn trần 3 đoạn).
- **Cách ly lockbox khỏi container**: `DR-LOCKBOX-02` / `kiem_h17()`.
- **Cổng tiền D12**: `DR-TRIEN-KHAI-01` §3 — DR này không đụng bốn điều kiện đó.

## 5. Thi hành và điều kiện dừng

- **`TD-0352`** (chế độ chạm thật của E4, hiện `touch_lockbox.py:190-196` luôn từ chối) **phải đọc luật này bằng máy**:
  đọc `d9_ket_cuc` + bảng §3; thiếu một ô ⇒ từ chối, in ra ô nào thiếu. Không để nó là kỷ luật con người.
- Chốt ở §2 **chặn** thì không được gỡ vì nó đang chặn. Muốn đi tiếp sau FAIL: DR mới, không nới DR này.
- Bảng §3 phải được điền **trước khi bất kỳ ai đọc kết quả D9**. Điền sau khi đã thấy số là chọn ngưỡng theo kết quả —
  đúng thứ toàn bộ PHẦN 0d của spec tồn tại để chặn. Kiểm bằng **thứ tự commit** (cùng cách `TD-0274` được kiểm).
