# DR-D4-03 — `v_min` đóng băng TẠI CHỖ, và §3.3b về đúng công thức `(a VÀ c) HOẶC (b)`

> **Ngày chốt:** 08/09/2026 · **Người quyết:** chủ dự án · **Việc:** MT-15 (back-end-note mục 7)
> 🔒 **Commit RIÊNG và TRƯỚC mọi dòng mã.** Cùng khuôn DR-D3-01 / DR-D35-01 / DR-D4-01 /
> DR-D4-02. Lý do đặc biệt mạnh ở đây: quyết định này **đặt một giá trị tham số**, và §9c.5
> nói thẳng rằng đặt ngưỡng sau khi thấy số là chỗ uốn kết luận. Số `1.0` dưới đây được chọn
> khi **chưa có một kết quả ablation nào tồn tại**.

---

## 1. Cái đang hỏng (MT-15)

| | |
|---|---|
| Code + test khoá `L-Z6` | thi hành **`(a) HOẶC (b)`** |
| Spec PHẦN 3b (dòng 1289–1317) | **`(a VÀ c) HOẶC (b)`**, kèm *"không phải (a OR b OR c) — (c) là BỔ NGỮ cho (a), không phải tín hiệu độc lập"* |
| Spec dòng 1115 | (c) là *"BỔ NGỮ **BẮT BUỘC** cho (a)"* |
| Điều kiện (c) volume | **0 dòng code** |
| `tier_b.v_min` | `null`, trạng thái `TUNED_PENDING` (OQ-06) |

🔴 **Hệ quả nặng nhất không phải "thiếu một bộ lọc".** §10.1b định nghĩa arm **`Z0-V1` đúng
bằng "tắt (c)"**, tức `(a) HOẶC (b)` — chính là thứ code đang có. Nối như hiện tại thì **`Z0`
trùng khớp `Z0-V1`**: một suất trial trong 114 tiêu để đo một khác biệt **bằng không**, trong
khi bảng kết quả trông hoàn toàn bình thường — chỉ là hai cột giống hệt nhau. Không phép kiểm
nào hiện có báo đỏ vì nó.

**Và (c) chặn CẢ CHÍN ARM, không phải một.** Điều kiện (c) nằm trong định nghĩa `Z0` — baseline
của cả bảng. Không có `v_min` thì không arm nào chạy được. Không có đường "bỏ một arm cho xong".

---

## 2. Ràng buộc cứng: `L-Z15` chỉ cho HAI trạng thái

Spec dòng 3882–3884: *"Mọi tham số [CẦN CALIBRATE] đều có TRẠNG THÁI trong registry: **TUNED**
(có trial) hoặc **FROZEN** (có frozen_rationale). Không tham số nào ở trạng thái 'im lặng'"*
— 🔴 CRITICAL.

`TUNED_PENDING` **không phải một trong hai**. Nó là trạng thái trung gian project tự đặt ở
D0-PRE khi registry còn rỗng. Dù chọn gì, `v_min` cũng phải rời trạng thái đó.

---

## 3. 🔴 Cái bẫy đã loại phương án tưởng là hiển nhiên nhất

Phản xạ đầu tiên là chuyển `v_min` sang `tier_frozen` — đúng chỗ dành cho tham số đóng băng,
và đúng cách DR-D4-02 vừa xử lý DG5 sáng nay. **Nhưng ở đây nó HẠ RÀO DSR.**

`src/tool_d/config/dof.py:91` tính `N` **từ số khoá thật trong `tier_b`**, máy cưỡng chế:

```python
n_dang_ky_computed = 4 + 3 * tier_b_declared_count * 2 + ARM_B2_COUNT * 2 + 20
```

Chuyển `v_min` ra khỏi `tier_b` ⇒ `|tier_b|` **12 → 11** ⇒ `N` **114 → 108** ⇒ rào DSR
**3,0777 → 3,0601**.

**Rào thấp xuống nghĩa là dễ qua cổng hơn.** Một quyết định chọn cho tiện lại nới chuẩn đánh
giá của chính mình. Kèm theo: mở lại `DR-D0PRE-02` (114 đã niêm phong sau khi L-Z29 PASS) và
làm lệch `src/tool_d/gates/dsr.py:24` đang hardcode 114.

🔑 **Khác biệt với DG5 (DR-D4-02), để không ai coi hai ca là một:** DG5 **chưa từng được đếm**
nên đóng băng nó không trừ đi gì (`dof: 0`, `N` giữ nguyên). `v_min` **đã được đếm** — nó là
tham số #4 trong 12 — nên đóng băng theo cách đó **thật sự** rút một bậc tự do ra khỏi mẫu số.
Cùng một động tác, hai hậu quả trái ngược.

---

## 4. Quyết định

### 4.1 Viết điều kiện (c), công thức về đúng `(a VÀ c) HOẶC (b)`

`(c)` = `volume(nến 1H xác nhận) / volume_MA(20, 1H) ≥ v_min`, **VÀ** nến đó thoả `(a)`.
Không phải tín hiệu độc lập — đúng chữ PHẦN 3b.

`bat_dieu_kien_c` là **tham số BẮT BUỘC, KHÔNG mặc định** — cùng khuôn `truoc_ms`/`sau_ms` của
`fill_probe` (TD-0162) và `nguong_giam_toi_da` của DG5 (TD-0169). Một mặc định ở đây nghĩa là
arm nào quên khai sẽ lặng lẽ chạy như arm khác.

### 4.2 `v_min = 1.0`, **ĐÓNG BĂNG TẠI CHỖ** — giữ nguyên trong `tier_b`

| | |
|---|---|
| Giá trị | **1.0** |
| Vị trí | **`tier_b`** (KHÔNG chuyển sang `tier_frozen`) |
| Trạng thái | **`FROZEN`** trong `config/param_status.yaml`, kèm `frozen_rationale` |
| Trial tiêu | **0** |
| `\|tier_b\|` | **12** — không đổi |
| `N_ĐĂNG_KÝ` | **114** — không đổi |
| Rào DSR | **3,0777** — giữ mức KHÓ |

**Vì sao giữ trong `tier_b` dù đang đóng băng:** ta **vẫn bị tính phí** cho một bậc tự do mà
ta **không dùng**. Đó là bảo thủ về đúng phía — phía không thể tâng kết quả lên. Đổi lại, nó
trông hơi nghịch (một khoá "mỗi lần đổi = 1 trial" lại đang đóng băng); ghi ra đây để người
sau hiểu đó là **cố ý**, không phải quên dọn.

**Vì sao `1.0` — và vì sao nó KHÔNG phải một con số tune:** `1.0` là **mốc trung tính** của một
tỉ lệ so với chính trung bình 20 kỳ của nó. Không có dữ liệu nào nói 1.0 tốt hơn 0.9 hay 1.2 —
và đó chính là lý do nó hợp lệ: nó được chọn bằng **định nghĩa**, không bằng kết quả. PHẦN 3b
tự mô tả ca xấu là *"chạm + volume **THẤP** + giá dừng lại → không ai bảo vệ, chỉ tạm nghỉ"*;
"thấp" so với trung bình của chính nó là `< 1.0`. Đường phân đôi tự nhiên.

🔴 **Đây là CHỖ GIỮ CHƯA CALIBRATE.** Phải đọc kèm mọi kết quả có `Z0` tham gia — tức toàn bộ
bảng, vì `Z0` là baseline.

### 4.3 Thứ tự: ablation TRƯỚC, calibrate SAU

Phương án "tiêu 3 trial B1 calibrate `v_min` ngay" bị loại **có ý thức**. Suất đó có thật
(B1 = 3 giá trị × 12 tham số × 2 hướng = 72; phần của `v_min` ở hướng Long là 3 trial), nhưng
tiêu bây giờ là **tune một tham số trước khi biết tính năng của nó có đáng giữ không** — mà
`Z0-V1` sinh ra đúng để trả lời câu đó. Nếu ablation nói (c) vô dụng thì 3 trial ấy đã tiêu cho
một tham số sắp bị xoá.

---

## 5. Ba điều kiện MỞ LẠI — viết TRƯỚC, là VÀ không phải HOẶC

Cùng khuôn OQ-07 / DR-D4-01 §2b / DR-D4-02. Viết trước để việc calibrate `v_min` không thể
được biện minh bằng một lập luận dựng sau khi đã nhìn kết quả.

`v_min` chỉ được chuyển `FROZEN → TUNED` (tiêu 3 trial từ B1) khi **cả ba** đúng:

1. **`Z0` thắng `Z0-V1` trên `pnl_abs`** theo đúng cách đọc §10.1b — tức (c) có giá trị đo
   được ở `v_min = 1.0`. Thua hoặc tương đương ⇒ **xoá hẳn (c)**, không calibrate.
2. **Cổng D4 đã đóng.** Calibrate giữa chừng là đổi baseline trong lúc đang so sánh.
3. **Ngân sách B1 còn ≥ 3 suất** cho hướng đang chạy.

Không đủ ba → `v_min` giữ `1.0` và giữ `FROZEN`.

---

## 6. 🔴 Kèm theo: phải SIẾT `L-Z15`, nếu không quyết định này tự làm lớp canh câm

`check_lz15_calibrate_params_have_status()` (`audit_checks.py:162`) chỉ soi các tham số `tier_b`
đang **`null`**:

```python
null_params = sorted(k for k, v in cfg.tier_b.items() if not k.startswith("_") and v is None)
```

⇒ **Khoảnh khắc ta ghi `1.0` vào, `L-Z15` thôi không canh `v_min` nữa.** Nó không bao giờ hỏi
con số đó từ đâu ra. Một tham số **có giá trị, không có trial, không có `frozen_rationale`**
đúng là trạng thái *"im lặng"* mà spec dòng 3884 cấm — và máy hiện tại **không thấy được**.

Nói cách khác: làm phương án này một cách ngây thơ sẽ **tự tay làm câm lớp canh duy nhất đang
theo dõi tham số này**. Đó là một bẫy PASS RỖNG mới, sinh ra bởi chính hành động sửa.

**Phải siết cùng lượt:** `L-Z15` đổi từ *"tham số null phải khai trạng thái"* sang *"mọi tham
số **[CẦN CALIBRATE]** phải khai trạng thái, bất kể đã có giá trị hay chưa"*, và trạng thái
`FROZEN` bắt buộc kèm `frozen_rationale` không rỗng. Danh sách [CẦN CALIBRATE] không suy được
từ việc "có null hay không" — phải khai tường minh trong `param_status.yaml`.

---

## 7. Điều quyết định này KHÔNG chốt

- **Không chốt (c) là đúng hay sai.** Đó là việc của `Z0-V1`. Quyết định này chỉ làm cho câu
  hỏi đó **hỏi được**.
- **Không chốt giá trị cuối của `v_min`.** `1.0` là chỗ giữ, có điều kiện mở lại ở §5.
- **Không đổi `N_ĐĂNG_KÝ`.** 114 giữ nguyên; `DR-D0PRE-02` không bị mở lại.
- **Không xoá phép kiểm nào của `L-Z6`.** Xem §8.

---

## 8. Vì sao "phải sửa test khoá" hoá ra gần như không phải sửa

Lo ngại ban đầu khi ghi MT-15: giải quyết nó **bắt buộc đổi một test trong `tests/lock/`** —
đúng thứ dự án đòi lệnh tường minh mới được làm.

Nhưng vì `bat_dieu_kien_c` là tham số **bắt buộc**, **12 ca hiện có của `L-Z6` giữ NGUYÊN mọi
khẳng định** — chỉ thêm `bat_dieu_kien_c=False` vào lời gọi. Và khi đó chúng **trở thành bộ
test khoá cho chính arm `Z0-V1`**, vì `(a) HOẶC (b)` **đúng là định nghĩa của `Z0-V1`**.

Không xoá ca nào, không nới ca nào. Đúng tiền lệ TD-0150 (*"sửa thành khẳng định ngược, KHÔNG
xoá"*). Thứ trông như *phá một test khoá* hoá ra là **đổi nhãn nó về đúng arm mà nó vẫn luôn
mô tả**.

---

## 9. Lịch sử

- **08/09/2026** — tạo; chủ dự án chốt phương án C (đóng băng tại chỗ, `v_min = 1.0`) sau khi
  xem bảng chi phí bốn phương án. Điểm quyết định: C và A cùng tiêu 0 trial, nhưng A hạ rào
  DSR xuống 3,060 còn C giữ 3,078.
