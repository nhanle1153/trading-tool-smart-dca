# DR-LZ12-01 — `L-Z12` so nhầm đơn vị: `config_hash` định danh CẤU HÌNH, không định danh MÃ

> **Ngày chốt:** 20/09/2026 · **Người quyết:** chủ dự án (phiên mã `dd855fee`: chọn *"so cùng mã, loại dòng
> đếm"*, rồi **đổi quyết định** sau phép đo phản biện thành *"bỏ vế loại CTRL, chỉ giữ vế đổi đơn vị"*;
> giao phiên này vá).
> **Chi phí:** **0 trial** — `DR-012` Hạng 1 (mã không khớp ý nghĩa đã chốt). Không chạm dữ liệu, không chạm lockbox.
> Mã `DR-LZ12-01` + `TD-0366` đặt chỗ bằng commit `4c9cb8f` (N12 mục 7c). Commit **RIÊNG và TRƯỚC** mọi dòng mã.

> 🔑 **Ghi công:** phát hiện, chẩn đoán cơ chế, và **đính chính vế "loại CTRL"** đều là của phiên `69768527`.
> Phiên này kiểm độc lập từng số trên sổ thật rồi vá.

---

## 1. Chuyện gì xảy ra

Sau lô `DR-D4-20` (`D-0019`…`D-0022`), `L-Z12` (🔴 CRITICAL) báo đỏ 4 cặp và **chặn mọi entrypoint**:
`run_audit()` trả 92 ⇒ E1/E3 không chạy, và full suite cũng đỏ (hai ca `test_run_backtest_cache` gọi E1 qua
subprocess nhận đúng mã 92). Tức một chốt kế toán làm dừng toàn hệ thống, không riêng cổng D4.

Đo trên sổ thật (gom theo `config_hash`, in kèm `code_commit` và `outcome`):

| `config_hash` | Các suất | Mã nguồn |
|---|---|---|
| `e417…` | `D-0007` CTRL (255 lệnh) · `D-0015` B2 (255) · `D-0019` B2 (231) | **ba** mã khác nhau |
| `f6b0…` | `D-0008` CTRL (50) · `D-0020` B2 (46) | hai |
| `68f2…` | `D-0009` CTRL (892) · `D-0021` B2 (**912**) | hai |
| `6364…` | `D-0010` CTRL (49) · `D-0022` B2 (45) | hai |

## 2. Gốc — một câu

`audit_checks.py:127-157` gom theo `config_hash` **một mình**, rồi so nguyên `outcome`. Nhưng **kết quả phụ thuộc
CẤU HÌNH *và* MÃ**: bản vá LD-13 (`DR-D4-20`) đổi `n_trades` 255 → 231 mà `config_hash` không đổi một bit. Chốt
đang hỏi *"cùng cấu hình sao khác kết quả?"* trong khi dữ kiện trả lời là *"vì khác mã"* — và nó không có chỗ
nào để nhìn thấy điều đó.

Spec `:3874-3875` nhắm ca: *"chạy lại mà không ghi sổ ⇒ registry mất hiệu lực"*. Ca đó, theo định nghĩa, là **cùng
mã**. Nên đổi đơn vị so sánh là **trả chốt về đúng câu hỏi nó sinh ra để hỏi**, không phải nới nó.

## 3. Quyết định

| # | Chốt |
|---|---|
| 1 | Đơn vị so sánh của `L-Z12` = **`(config_hash, code_commit)`**. Cùng mã + cùng cấu hình mà khác `outcome` ⇒ vẫn ĐỎ |
| 2 | **GIỮ dòng `CTRL` trong phép so** |
| 3 | `code_commit` thiếu ở một dòng RESERVE ⇒ coi là chuỗi rỗng, vẫn gom — **không bỏ qua dòng đó** (fail-closed: thiếu xuất xứ thì so chặt hơn, không lỏng hơn) |
| 4 | **Loại `config_hash` lính canh `"n/a"`** khỏi phép gom (dòng E7 chốt pool, `D-0001`…`D-0004`) |
| 5 | **Không còn cặp nào so được ⇒ `pending`, KHÔNG phải `ok`** (N6) |

### 3.2 Vì sao chốt 4 và 5 là BẮT BUỘC, không phải trang trí — đo trước khi viết

Phiên `69768527` chỉ ra và phiên này kiểm lại trên sổ thật: gom theo `(config_hash, code_commit)` cho **10 nhóm**,
và **đúng MỘT** nhóm có ≥ 2 trial — chính là nhóm lính canh `config_hash = "n/a"` (`D-0001`…`D-0004`, bốn suất B0
chốt pool của E7, cùng mã, `outcome` đều rỗng).

⇒ Nếu chỉ đổi đơn vị mà **không** làm chốt 4 và 5, `L-Z12` sẽ trả **✅** — trong khi nó **không canh một cấu hình
thật nào**. Đó đúng là **PASS RỖNG**, thứ dự án này đã dính năm lần. Sau bản vá, trạng thái ĐÚNG của `L-Z12` trên
sổ hôm nay là **⏳ chưa đo được**, không phải ✅. Ai thấy ✅ ở đó nghĩa là phần loại lính canh chưa ăn.

### 3.1 Vì sao vế "loại dòng `CTRL`" bị BỎ — và đây là đính chính một quyết định đã duyệt

Bản trình ĐẦU cho chủ dự án có hai vế: đổi đơn vị **và** loại `CTRL`. Phép đo phản biện của phiên `69768527` bác
vế thứ hai bằng chính sổ thật:

- **Không đủ:** nhóm `e417…` có BA trial. Bỏ `CTRL` vẫn còn `D-0015` (255) so `D-0019` (231) ⇒ **vẫn đỏ**.
- **Có hại:** `CTRL` dạng *tái lập* (`MT-08`, `TD-0130`) tồn tại **đúng để** chứng minh cùng cấu hình cho cùng kết
  quả. `L-Z12` bỏ qua `CTRL` là tự làm câm lớp canh duy nhất kiểm được điều đó.
- Chi tiết đáng nhớ: `D-0007` (CTRL) và `D-0015` (B2) **khớp nhau hoàn toàn** — vì `D-0015` là suất hỏng sau con
  dấu nên cũng ghi `outcome` rỗng. Nên câu *"CTRL luôn null nên không bao giờ khớp trial thật"* là **sai một phần**.

Chủ dự án đổi quyết định trước khi có dòng mã nào — đúng thứ tự.

> 🔧 **Đính chính 24/09/2026 (`DR-DINH-DANH-01` §4.4) — chốt giữ `CTRL` ĐỨNG NGUYÊN, lý do hẹp lại.** Sau bản vá này,
> `CTRL` tái lập theo §0d.4 (chạy SAU một commit ⇒ khác `code_commit`) rơi vào **nhóm khác** trial gốc, nên `L-Z12`
> chỉ canh tái lập **cùng commit**, không canh ca §0d.4. Ca §0d.4 do phép kiểm `TD-0379` canh. Chữ cũ ở trên giữ nguyên.

## 4. KHÔNG thuộc DR này

- Không đổi `config_hash` (cách băm cấu hình) và không thêm mã nguồn vào băm đó.
- Không đụng các chốt audit khác, không đụng cổng D4, không đổi `N = 114` hay rào DSR.
- Không viết lại dòng sổ nào (`D-0007`…`D-0010`, `D-0015` giữ nguyên).

## 5. Nợ ghi theo quy tắc 11 — một mục `MT` khi *"chuẩn hóa và lưu"*

Hai điều đã chốt va nhau: khối xuất xứ coi `config_hash` là định danh của một lần chạy, còn `DR-012` Hạng 1 cho
phép sửa mã **0 trial** — nên hai lần chạy cùng `config_hash` có thể hợp lệ khác kết quả. DR này giải chỗ va ở
tầng phép kiểm; câu rộng hơn (*"một lần chạy được định danh bằng gì"*) ghi thành `MT` để chủ dự án quyết sau.

### 5.1 Mâu thuẫn MỚI do chính bản vá sinh ra — phải ghi, không được để ngầm

`registry._kiem_ctrl_tai_lap()` (`registry.py:436-464`) xác thực dòng `CTRL` dạng *tái lập* bằng `config_hash` +
`params_frozen_hash` và **cố ý không xét `code_commit`**. Sau bản vá, `L-Z12` xét mã còn **cửa ghi thì không** ⇒
hai lớp dùng hai định nghĩa trái nhau cho *"cùng một cấu hình"*, và một dòng `CTRL` có thể được công nhận *"tái
lập"* giữa hai phiên bản mã khác nhau.

Thêm một chi tiết phiên `69768527` đo được: cửa đó so `if moi != cu`, mà bốn dòng E7 có **cả** `config_hash` lẫn
`params_frozen_hash` là `"n/a"` ⇒ một `CTRL` trỏ về chúng sẽ **khớp hai chuỗi lính canh** và được ghi 0 suất. Sổ
hôm nay có **0** dòng tái lập nên **chưa có thiệt hại** — đây là nợ ghi trước, không phải sự cố.

🔴 **DR này KHÔNG sửa cửa ghi đó** (ngoài phạm vi, và sửa một cửa ghi fail-closed cần quyết định riêng). Ghi thành
`MT` ở lần *"chuẩn hóa và lưu"* kế tiếp.

## 6. Điều kiện dừng — viết TRƯỚC

1. Phải sửa một test cũ mới xanh (ngoài ca ghim chính `L-Z12`) ⇒ **dừng, báo**.
2. Sau khi vá mà E6 vẫn đỏ vì lý do khác ⇒ **dừng, đọc lý do thật**, không nới thêm chốt nào.
3. Sổ trial đổi dù một dòng trong lúc vá ⇒ dừng (bản vá là 0 trial).

## 7. Hành vi mong đợi — ghi trước để không đọc nhầm là lỗi

- 4 nhóm hiện tại **tan** (mỗi nhóm có ≥ 2 mã khác nhau) ⇒ `run_audit` về 0, E1/E3 chạy lại được.
- 🔴 `L-Z12` trên sổ hôm nay ra **⏳ chưa đo được**, KHÔNG phải ✅ (xem §3.2). Thấy ✅ ⇒ bản vá sai.
- Một ca **cùng mã + cùng cấu hình + khác `outcome`** vẫn phải đỏ — có test kiểm-có-răng ghim đúng ca đó.
- Hai ca `L-Z12` sẵn có trong `tests/unit/test_audit_checks.py` dùng CÙNG `code_commit` nên **không phân biệt được**
  luật cũ với luật mới; chúng vẫn xanh. Vì thế bản vá phải **thêm** ca cho: khác mã ⇒ hết đỏ · lính canh `"n/a"` bị
  loại · không còn cặp so được ⇒ `pending`.

## 8. Thủ tục — hai chỗ dễ sai, ghi để khỏi vấp

- **KHÔNG** đưa `L-Z12` vào `WARN_ONLY_CODES`: `test_td0118_*:144` ghim cứng `== frozenset({"L-Z17"})`, và một chốt
  CRITICAL hạ xuống cảnh báo là mất chốt.
- Đính chính spec `:3874` thì **nối vào cuối chính dòng đó**, không chèn dòng mới — chèn làm lệch mọi trích dẫn
  theo số dòng trong cả repo.
