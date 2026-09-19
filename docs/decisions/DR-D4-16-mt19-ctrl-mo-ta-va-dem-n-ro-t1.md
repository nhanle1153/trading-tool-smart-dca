# DR-D4-16 — Thi hành `MT-19` (CTRL dạng thứ ba *đo mô tả*) + đếm `n` 4 arm trên rổ T1

> **Ngày chốt:** 19/09/2026 · **Người quyết:** chủ dự án (chọn *"Code MT-19 + đếm ngay"*, phiên mã `69768527`)
> **Chi phí:** **0 trial** trong N · +12 sự kiện CTRL trên sổ thật · một lượt nhìn cửa sổ WFO **chỉ bằng số đếm lệnh**.
> Mã `DR-D4-16` + `TD-0344` + `TD-0345` đặt chỗ bằng commit `e3b2848` (N12 mục 7c).

> 🔴 **PHIÊN SINH Ý TƯỞNG (IDEA) VÀ PHIÊN CHỌN KHÔNG ĐỌC FILE NÀY** (`DR-009`).

---

## 1. Chỗ va, ghi theo quy tắc 11

| Quyết định cũ | Chữ đang có | DR này đổi gì |
|---|---|---|
| `DR-IQ-01` §1 (17/09), bảng, dòng *"TD-0247 phần đo lại phễu/n/lệnh-năm Z0-T1/Z0/Z0-T0/Z3 trên rổ mới"* | ⏸ tạm dừng; xác nhận ở `c113567` | **Gỡ ⏸ CHỈ dòng này.** Mọi ⏸ khác của `DR-IQ-01` §1 (bộ chạy ablation, cổng D4, D5 B1, D9, D6–D8) **đứng nguyên** |
| `MT-19` (14/09) | đã chốt đường (c), *"Chưa có mã việc"* | Thi hành, tên trường liệt kê ĐÍCH DANH ở §3 — thay chỗ *"DR riêng"* mà `DR-D4-12` §10(b) đòi |
| `DR-D4-12` §10(c) | *"ghi dòng CTRL dạng **đo thước**"* | ❌ đọc sai theo `MT-19`: dạng đúng là **đo mô tả** (dạng thứ ba). Danh sách đo thước D3.5 **không đụng một chữ** |

**Khai thẳng:** quyết định SAU khi đã thấy EXPLORE ≈ 0 (`DR-IQ-01` §0), khi D4-đo vẫn khoá. Phép đếm thêm **một lượt nhìn cửa sổ
WFO** cho một giả thuyết đang tạm dừng — chỉ số lệnh, không một con số lãi/lỗ nào (§3 là danh sách CHO PHÉP, không phải cấm).
Cửa sổ WFO đã từng bị nhìn qua đếm lệnh trên rổ cũ (`DR-SONG-CON-01:82`, TD-0205/0212).

## 2. Vì sao cần — điều kiện 3 của `DR-D4-14` §6

Spec `:4338` (*"mỗi lần đổi pool = mọi số cũ không so sánh được"*) làm các số `325,6` lệnh/năm · `n = 206` · `44,8` (đo trên
`pool.yaml` 102 mã) mất hiệu lực sau khi `TD-0247` dựng rổ T1 point-in-time. Bảng `n` của `DR-D4-12` §4.1 phải đo lại trên rổ
mới trước khi D4-đo dựa vào nó.

## 3. `MT-19` đường (c) — dạng CTRL thứ ba *đo mô tả*

Khai bằng trường `ctrl_mo_ta_whitelist`; đầu ra giới hạn cứng vào `CTRL_MO_TA_ALLOWED` — **liệt kê đích danh**, mỗi tên một câu
vì-sao-không-phải-chỉ-số-hiệu-năng:

| Tên | Vì sao không phải chỉ số hiệu năng |
|---|---|
| `so_lenh` | Đếm sự kiện VÀO lệnh — không mang dấu hay độ lớn của lãi/lỗ |
| `lenh_moi_nam` | `so_lenh` chia năm phủ — biến đổi tuyến tính của một số đếm, không thêm thông tin kết quả |
| `so_lenh_theo_thang` | Phân bố THỜI GIAN của sự kiện vào lệnh — không chứa kết quả lệnh |
| `so_ma_co_lenh` | Số mã sinh ≥ 1 lệnh — độ rộng tín hiệu, không phải kết quả |
| `phan_bo_so_tranche` | Số lệnh theo số tranche đã khớp (1/2/3) — cơ học khớp lệnh, không phải kết quả |

🔴 **Cố ý KHÔNG cho phép** (ghi ra để người sau khỏi đề xuất lại): `exit_reason` hay phân bố lý do thoát — tỉ lệ TP/SL rò thẳng
thắng/thua; thời gian giữ lệnh — tương quan với kết quả; mọi thứ có `profit`/`pnl`/`R`. Thêm tên = **DR mới**.

**Ràng buộc thi hành của `MT-19` (sai là mở cửa lách):** ba dạng loại trừ nhau — khai **đúng một** trong `reproduces_trial_id` ·
`ctrl_output_whitelist` · `ctrl_mo_ta_whitelist`; khai chồng bất kỳ hai ⇒ TỪ CHỐI; không khai ⇒ TỪ CHỐI. Đổi *"một trong HAI"*
thành *"một trong BA"* với ba nhánh tường minh **trong CÙNG commit** với việc thêm trường.

## 4. Phép đếm (`TD-0345`)

- 4 arm `LO_ARM_D4` (`Z0-T1`, `Z0`, `Z0-T0`, `Z3`), Long; rổ `ro_cho_tap("WFO")` (rổ T1); cửa sổ biên WFO `[T1, T2]`.
- `--timeframe-detail 5m` nếu độ phủ 5m đạt; không thì 1H kèm ghi chú (đủ để ĐẾM, không đủ để nói về TP).
- Mỗi arm một CTRL dạng 3 trên sổ THẬT: RESERVE → `chay_mot_luot` (`L-Z52`) → SEAL → đếm → CONSUME (verdict `INCONCLUSIVE`,
  outcome không số hiệu năng). 0 vào N.
- Hàm đếm THUẦN trả CHỈ các tên §3; artifact `docs/du-lieu-do/td0345-dem-n-4-arm-ro-t1.json`.
- Kết quả ghi CẠNH số cũ, không phán xét; bảng `DR-D4-12` §4.1 đọc số mới từ artifact.

## 5. KHÔNG làm

- Gỡ ⏸ nào khác của `DR-IQ-01` §1; lật `D4_DO_TAM_DUNG`; đặt chỗ `B2`.
- In, ghi, hay tính bất kỳ đại lượng lãi/lỗ nào từ lượt chạy (kể cả vào log người đọc).
- Đụng `CTRL_OUTPUT_ALLOWED` (D3.5 Bước 1).

## 6. Điều kiện dừng

- Cần thêm một tên ngoài §3 để đếm xong ⇒ dừng, DR mới.
- Một test cũ phải sửa khẳng định mới xanh ⇒ dừng, báo.
- Sổ trial đổi khác đúng +12 sự kiện CTRL, hoặc `n_used()` đổi ⇒ dừng.
