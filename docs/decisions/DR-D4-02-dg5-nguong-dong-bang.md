# DR-D4-02 — Ngưỡng suy yếu ZSS của DG5: ĐÓNG BĂNG, không tính vào DOF gốc

> Chủ dự án quyết 08/09/2026 (TD-0169). Phát hiện khi làm TD-0181 (dựng DG1–DG5),
> phiên `…-e8` xác nhận độc lập.
>
> 🔴 File này commit **RIÊNG và TRƯỚC** mọi dòng cấu hình — cùng lý do DR-D4-01 và
> DR-D35-01: chọn ngưỡng sau khi đã nhìn thấy kết quả là uốn kết luận, và một quyết
> định về `N_ĐĂNG_KÝ` thì càng phải chốt trước vì `N` là mẫu số của rào DSR §10.2.

## 1. Sự việc

Spec §4 định nghĩa cổng DG5 là *"ZSS tính lại tại thời điểm xét tranche 2/3 **không
giảm > 30%** so với lúc tranche 1"*.

Con số 30% đó **không tồn tại ở bất kỳ đâu trong hệ thống tham số**:

| Nơi phải có | Thực tế |
|---|---|
| `config/tool_d_config.yaml` → `tier_b` | ❌ đủ 12 mục, không mục nào là DG5 |
| `config/tool_d_config.yaml` → `tier_frozen` | ❌ không có |
| `config/dof_inventory.yaml` → `rows` | ❌ mục `§4` chỉ có **DG4** |
| `config/dof_inventory.yaml` → `bo_sot` | ❌ chỉ có DG7 và `w_tranche` |

Tức DG5 hoạt động bằng một hằng số mà **không phép kiểm nào biết là nó tồn tại**.
Đây đúng hạng lỗi mà toàn bộ kiểm kê DOF sinh ra để chặn, và chính bảng đó đã tự sửa
một lần: dòng DG7 ghi `(0 — bỏ sót)`.

🔴 **Khác biệt so với hai dòng `bo_sot` đã có, và đây là chỗ quyết định:** DG7 và
`w_tranche` được **chính spec** thừa nhận là bỏ sót và đã cộng vào `DOF_gốc = 28`
(`dof_inventory.yaml` dòng 7-11 ghi *"Đẳng thức này trích NGUYÊN VĂN từ chính spec"*).
DG5 thì **spec cũng không đếm**. Nên xếp nó vào `bo_sot` không phải là ghi nhận một
thiếu sót đã biết — mà là **tuyên bố con số 28 spec tự trích là sai**.

## 2. Ba phương án, và cái giá thật của từng cái

| | Phương án | `N_ĐĂNG_KÝ` | Rào DSR §10.2 | Chi phí |
|---|---|---|---|---|
| A | **`tier_frozen` + `khong_dem_vao_dof_goc`** | **114** (không đổi) | **3,0777** (không đổi) | **0 trial** |
| B | `tier_b`, tunable #13 | 114 → **120** | 3,0777 → 3,0943 (**+0,54%**) | **+6 trial**, mở lại DR-D0PRE-02, `dof_goc` 28 → 29 |
| C | Hoãn, ghi mâu thuẫn | — | — | Chặn TD-0183 và TD-0184 |

Số của B tính từ chính công thức đã chốt ở `DR-D0PRE-02` dòng 30:

```
N = 4 + 3×(số tunable tier_b)×2 + 9×2 + 20
  = 4 + 3×12×2 + 9×2 + 20 = 114        ← hiện tại
  = 4 + 3×13×2 + 9×2 + 20 = 120        ← nếu thêm khoá vào tier_b
```

`+6 trial` đúng bằng đơn giá *"+1 tham số = +6 trial"* mà spec dùng ở PHẦN 3b cho
`v_min` — không phải một ước lượng dựng ra ở đây.

## 3. Chốt: **phương án A — đóng băng**

```yaml
tier_frozen:
  dg5_zss_decay_max: { value: 0.30, dof: 0 }

khong_dem_vao_dof_goc:
  - khoa: "dg5_zss_decay_max"
    ly_do: "§4 có ngưỡng nhưng bảng DR-010 không có dòng DG5 — chưa từng
            được đếm, đóng băng luôn (cùng hạng adx_threshold)"
```

**Vì sao A chứ không phải B.** Bảng `khong_dem_vao_dof_goc` **đã có sẵn tiền lệ đúng
hình dạng này** — `adx_threshold` được ghi thẳng *"chưa từng có trong 26"* (spec dòng
3168, LỖI 1 của v5), `mult_edge_thr`/`mult_deploy_thr` ghi *"chưa định nghĩa trước
v6"*. Tức hệ thống **đã có một chỗ đúng** để đặt "một bậc tự do chưa ai đếm, đóng
băng luôn, không tune". DG5 rơi đúng vào đó.

A cho phép làm điều quan trọng nhất — **ghi nhận rằng bậc tự do này TỒN TẠI** — mà
không phải trả 6 trial, và không phải tuyên bố con số spec trích nguyên văn là sai.

**Đánh đổi được chấp nhận, nói thẳng:** 30% trở thành **không tune được**. Muốn đổi
phải mở khoá, và mở khoá là **+6 vào N** theo §12c.3. Nghĩa là ta đang chấp nhận
30% là **một chỗ giữ chưa calibrate** — không có dữ liệu nào nói 30% đúng hơn 25%
hay 35%. Điều đó phải được đọc kèm mọi kết quả có DG5 tham gia (Z3, Z3b).

**Vì sao KHÔNG chọn C.** Hoãn không làm con số biến mất; nó chỉ chuyển thời điểm phát
hiện sang lúc TD-0184 cần chạy, tức lúc sửa đắt hơn. Và một hằng số không ai đếm nằm
im trong code là chính xác trạng thái mà quyết định này tồn tại để chấm dứt.

## 4. Điều kiện mở lại — viết TRƯỚC, để không ai biện minh sau

Cùng khuôn DR-Q3-2026 và DR-D35-01: ba điều kiện dưới đây viết ra **trước khi** có bất
kỳ kết quả ablation nào, để việc mở khoá 30% không thể được biện minh bằng một lập
luận dựng sau khi nhìn thấy số.

1. **Có dữ liệu.** ≥ 50 lệnh live đã đóng mà DG5 thực sự được xét (tức có tranche 2/3
   được cân nhắc), đủ để phân bố mức suy giảm ZSS có hình dạng.
2. **DG5 phải đang CÓ tác dụng.** Nếu §10.2 Nhánh 2 chọn **Z0** (bỏ DCA) thì DG5 là
   code chết — mở khoá một tham số của code chết là tiêu 6 trial vô nghĩa. Điều kiện
   này tự động không đạt trong ca đó.
3. **Phải qua DR-012 và tiêu 1 trial từ B3** như mọi lần đổi tham số, cộng +6 vào N.
   Không có đường tắt nào khác.

🔴 Ba điều kiện là **VÀ**, không phải HOẶC.

## 5. Điều quyết định này KHÔNG chốt

- **Không** nói 30% là con số đúng. Nó là con số của spec, được giữ nguyên và đóng băng
  ở trạng thái chưa calibrate.
- **Không** đụng tới `dof_goc = 28`, `tier_b = 12`, hay `N_ĐĂNG_KÝ = 114`. Cả ba giữ
  nguyên, và `L-Z29` phải vẫn xanh sau thay đổi này — đó là phép kiểm xác nhận rằng
  phương án A thật sự không tốn gì.
- **Không** liên quan tới câu hỏi §3.3b điều kiện (c) và `v_min` (MT-15) — đó là hai
  việc khác, ở hai vị trí khác trên đường tới hạn.

## 6. Lịch sử

| Ngày | Việc |
|---|---|
| 08/09/2026 | Phát hiện khi dựng DG1–DG5 (TD-0181); `nguong_giam_toi_da` để **bắt buộc, không mặc định** trong lúc chờ quyết |
| 08/09/2026 | Phiên `…-e8` xác nhận độc lập, tính ra hậu quả `N` 114 → 120 và nêu phương án đóng băng |
| 08/09/2026 | Chủ dự án chốt **phương án A — đóng băng** (TD-0169) |
