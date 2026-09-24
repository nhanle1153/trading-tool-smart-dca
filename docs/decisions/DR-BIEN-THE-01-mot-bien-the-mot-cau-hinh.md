# DR-BIEN-THE-01 — `so_bien_the` đếm CẤU HÌNH, không đếm suất

> **Ngày chốt:** 24/09/2026 · **Người quyết:** chủ dự án (trả lời `MT-80` hướng (b); chọn định danh "chỉ các tham số
> chiến lược đọc") · phiên mã `12c579bc` thi hành.
> **Chi phí:** 0 trial. Không đổi `N = 114`, không đổi rào DSR, không sửa dòng sổ nào.
> Mã `DR-BIEN-THE-01` + `TD-0395` đặt chỗ bằng commit `9ce15cd` (N12 mục 7c). Commit **RIÊNG và TRƯỚC** `TD-0396` (mã).

> 🔴 **PHIÊN IDEA/CHỌN KHÔNG ĐỌC FILE NÀY** (`DR-009`).

---

## 1. Chỗ vênh (`MT-80`)

Cửa CHỌN bắt khai `so_bien_the` (MT-12). `TD-0119b` (`src/tool_d/ledger/audit_checks.py:679`) đối chiếu nó với sổ trial
bằng cách đếm **số suất CONSUMED** mang `hypothesis_slot = IQ-xxxx` và vào `N`. `IQ-0003` khai `so_bien_the: 1`, nghĩa
người khai: *"tham số cố định, không thử lưới"*. Máy đọc theo nghĩa **suất**, nên cả chu trình CALIB → WFO → lockbox chỉ
được tiêu một suất, trong khi mỗi đoạn là một lần chạy riêng.

## 2. Quyết định

1. **Một biến thể = một CẤU HÌNH của ứng viên.** Một cấu hình cố định đo qua đủ các đoạn của chu trình tính là **một**
   biến thể. Cấu hình thứ hai trên cùng slot là biến thể thứ hai.
2. **`so_bien_the` so với số cấu hình PHÂN BIỆT**, không so với số suất. Mỗi suất vẫn tính vào `N` như cũ: DR này đổi cách
   đếm biến thể, **không** đổi kế toán ngân sách.
3. **Định danh cấu hình = dấu băm các tham số chiến lược THẬT SỰ ĐỌC**, không phải `config_hash` cả file. Lý do:
   `config_hash` đổi mỗi khi bất kỳ dòng nào của `tool_d_config.yaml` đổi (tham số ZA, lật `enable_short`, việc vận hành),
   nên một ứng viên không đổi gì vẫn bị đếm thêm biến thể và bị chặn oan.

## 3. Định danh — máy đọc được, khai trước

- DR thiết kế D0 của ứng viên chứa khối:

  ```
  <!-- DR-BIEN-THE-01:KHOA:BEGIN -->
  {"slot": "IQ-xxxx", "khoa": ["tier_a....", "tier_c....", ...]}
  <!-- DR-BIEN-THE-01:KHOA:END -->
  ```

  `khoa` liệt kê **mọi** khoá `tool_d_config.yaml` mà chiến lược của slot đọc, **kể cả khoá dùng chung** (vốn, công tắc
  hướng). DR phải đã commit. Khối hỏng, slot sai, hay danh sách rỗng ⇒ từ chối (fail-closed).
- `bien_the_hash` = sha256 của JSON chuẩn hoá (`sort_keys`, không khoảng trắng) của `{khoa: resolve(cfg, khoa)}` trên đúng
  danh sách đó. E1 tính và ghi vào dòng `RESERVE` **mới** của slot `IQ-xxxx`. Schema sổ thêm trường (tuỳ chọn, chỉ bắt
  buộc với slot `IQ-xxxx` khi dòng vào `N`).
- **Danh sách khoá phải đầy đủ — máy kiểm, không tin lời khai:** một test AST đọc file chiến lược của slot và đòi mọi
  chuỗi `"tier_*.…"` truyền cho `resolve()` đều có mặt trong `khoa`. Chiến lược đọc một khoá ngoài danh sách ⇒ đỏ. Không
  có kiểm này thì lối "chỉnh một khoá không khai" mở lại đúng thứ `so_bien_the` sinh ra để chặn.

## 4. Phép đếm mới của `TD-0119b` (`TD-0396`)

- Với mỗi slot đã khai `so_bien_the`: lấy các suất CONSUMED vào `N` (giữ nguyên lọc `_dem_vao_n` của `TD-0389`).
- Số biến thể = số giá trị `bien_the_hash` phân biệt. **Dòng không có `bien_the_hash`** (dòng cũ, hay đường ghi quên
  tính) **đếm là một biến thể riêng mỗi dòng**: thiếu định danh thì đếm theo hướng khó tiêu suất hơn.
- Vi phạm khi số biến thể > `so_bien_the`. Dòng `evidence` liệt kê từng hash và số suất của nó.
- `reserve()` chặn **trước** khi ghi: dòng RESERVE mới của slot `IQ-xxxx` mà làm số biến thể vượt `so_bien_the` ⇒ từ chối.
  Audit bắt dòng thêm tay là lớp thứ hai.

## 5. Không đổi

- Sổ ý tưởng không đổi một dòng. `so_bien_the: 1` của `IQ-0003` giữ nguyên.
- Slot không phải `IQ-xxxx` không bị ảnh hưởng.
- Mỗi suất vẫn chịu mọi cửa hiện hành của sổ (cửa thiết kế `TD-0375`/`DR-CAN-RO-01`, cửa tập dữ liệu, `L-Z55`…).

## 6. Điểm yếu — khai thẳng

- Quyết định đến sau khi một ứng viên cụ thể đã được chọn, và nó nới đúng cái cổng ứng viên đó sẽ chạm. Đối trọng:
  nghĩa mới **trùng lời khai** của chính người chọn (tờ chọn `IQ-0003`: *"tham số cố định, không thử lưới"*), và mỗi suất
  vẫn trả đủ giá vào `N`.
- Chạy cùng một cấu hình nhiều lần trên cùng một đoạn vẫn chỉ là "một biến thể" theo phép đếm này. Chặn việc đó là việc
  của `L-Z12` và kỷ luật tái lập (`DR-DINH-DANH-01`), không phải của `so_bien_the`.
