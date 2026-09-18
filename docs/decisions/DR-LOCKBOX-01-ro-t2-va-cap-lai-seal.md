# DR-LOCKBOX-01 — Lockbox chấm trên rổ tại `T2`; seal 1 được CẤP LẠI, không phải gia hạn

> **Ngày chốt:** 18/09/2026 · **Người quyết:** chủ dự án · **0 trial** · **N giữ 114**
> **Giải:** `MT-59` (`khoang_ton_tai` giữ mã đã chết) · `MT-60` (lockbox niêm phong sai rổ).
> **Thi hành:** Khối 26, `TD-0305` (DR này) → `TD-0306` · `TD-0307` · `TD-0309` làm ngay;
> `TD-0308` · `TD-0310` **vẫn ⏸** tới khi nối lại D8.
> **Commit RIÊNG và TRƯỚC mọi dòng mã** của Khối 26 phần B.
> **N12 mục 6:** mã `DR-LOCKBOX-01` đã nhắn trước và được phiên `-01` xác nhận còn trống; phiên `-93`
> rút bản nháp `DR-D1-06` cho cùng việc (chưa từng commit) để không thành hai nguồn sự thật.

---

## 0. Vấn đề — hai khiếm khuyết, và một trong hai sẽ im lặng

**`MT-60` — lockbox niêm phong đúng dữ liệu nhưng SAI RỔ.** `lockbox/lockbox_seal_1.json` băm 510 file =
102 mã × 5 loại, tập mã **trùng khít `config/pool.yaml`**, tức rổ đo **09/2026 — CUỐI** giai đoạn lockbox.
`DR-D1-05` §1 quy định LOCKBOX dùng rổ **tại `T2`**. Rổ đo ở cuối giai đoạn đã loại sẵn mọi mã suy giảm
trong giai đoạn ⇒ lần chạm lockbox duy nhất sẽ chấm cấu hình trên một rổ khác rổ WFO, **lệch sống sót
theo chiều PASS, đúng tại cổng cuối**. Mức lệch đo được (0 trial, đọc artifact đã commit, phiên `-93`):
`pool_dung_tai_t2` = 94 mã; 38 mã (40,4%) thuộc rổ `T2` mà `pool.yaml` không có; 46/102 (45,1%) mã trong
`pool.yaml` không thuộc rổ `T2`. Lệch gần **một nửa**, không phải ở rìa.

🔴 **Vì sao nó im lặng:** `verify_seal()` (`src/tool_d/lockbox/seal.py:96-121`) là danh sách ĐÓNG — nó
băm lại đúng các file đã ghi, **không nhìn tới danh sách mã nào**. Seal sai rổ vẫn PASS `L-Z14` mãi mãi.

**`MT-59` — `khoang_ton_tai` đánh giá quá đời sống mã đã huỷ niêm yết.** Artifact `TD-0230` suy "còn
sống" từ **sự có mặt file nến tháng**, nhưng kho `data.binance.vision` vẫn sinh nến ở giá thanh toán,
`volume = 0`, nhiều tháng sau khi ngừng giao dịch thật. Rổ `T1` không bị ảnh hưởng; dựng rổ `T2` bằng
khoảng đó thì **giữ lại mã đã chết**. `MT-59` chặn `MT-60`.

## 1. Cách các quyết định này được chốt — ghi ra để không ai đọc quá tay

Chủ dự án **chọn** trong các phương án do phiên `-93` (nay `-2c`) soạn, qua công cụ hỏi-chọn, **không gõ
tự do**. Ở cả 7 câu hỏi và một gói 6 câu mặc định, chủ dự án đều chọn đúng phương án được gắn *"(Đề
xuất)"* — tức đánh đổi được trình bày bằng lời và khung của phiên soạn. Phiên `-2c` tự khai điều đó và đề
nghị hỏi lại. Phiên `-2b` (từng tên `-a2`, phiên giữ Khối 26) đã trình lại toàn bộ cho chủ dự án ở phiên
mình và được **xác nhận: "Đúng, viết DR theo đó"** (18/09/2026). Lời chủ dự án gõ tay, nguyên văn:
*"TD-0302 (rổ T2 + lockbox) vẫn ⏸. Phải giải MT-59 và MT-60 trước lần chạm lockbox duy nhất. => triển
khai"* và *"=> okie bạn triển khai"*.

## 2. Quyết định

| # | Câu | Chốt |
|---|---|---|
| Q1 | Rổ cho lần chạm lockbox | **Rổ tại `T2`**, niêm phong bằng một seal **cấp lại** (§3). Seal 1 **giữ nguyên trên đĩa**, không sửa một byte. Lần chạm duy nhất bắt buộc trỏ seal cấp lại, có máy canh |
| Q2 | Làm gì ngay | Giải `MT-59` + chốt `MT-60` (DR này) + dựng `config/pool_t2.yaml`. **Hoãn** tải dữ liệu `[T2,T3]` + niêm phong tới khi nối lại D8. Rổ khoá **trước khi thấy bất kỳ số nào** |
| Q3 | Mức giải `MT-59` | **Đo trước** xem nó có làm lệch `pool_dung` tại `T2` không (0 trial). Kết quả nào cũng đưa mốc ngừng giao dịch THẬT vào `dung_ro_tai_moc()`, fail-closed — không dựa vào việc *"volume = 0 tình cờ loại giúp"* |
| Q4 | Gỡ ⏸ phần nào | Gỡ cho **DR + đo đời sống + dựng rổ + vá máy canh seal** (`TD-0305/0306/0307/0309`). **Giữ ⏸** tải dữ liệu + niêm phong (`TD-0308/0310`). Lần chạm thật (`TD-0274`) **khoá trong mọi trường hợp** |
| Q5 | Seal cấp lại có ăn vào trần 3 đoạn không | **Không.** Nhãn riêng *"cấp lại"*; chỉ seal **chưa từng bị chạm** mới được cấp lại; vẫn còn đủ **2 lần gia hạn** INCONCLUSIVE. Chi tiết và chốt kèm ở §3 |
| Q6 | Lần chạm có chạy `--timeframe-detail 5m` không | **Có.** Seal cấp lại gồm **6 loại file** (thêm `5m`), để lockbox chạy đúng cấu hình D5 (`DR-D5-01` bắt buộc `5m`) và D9 — quy tắc 9. Seal 1 có **0 file `5m`** (ba phiên đo độc lập). Giá: 5m của `[T2,T3]` là dữ liệu **chưa ai tải**, không chép lại được |
| Q7 | Mã sống tại `T2` nhưng huỷ niêm yết giữa `[T2,T3]` | **Giữ trong rổ, cắt dữ liệu tại mốc ngừng giao dịch** — như rổ `T0` đã làm với 18 mã. Lockbox thấy đúng thứ một người giao dịch thật tại `T2` sẽ gặp |
| iii | Mã có dữ liệu EXPLORE | **Loại** khỏi rổ `T2`, như rổ `T0`/`T1` (`DR-D1-03` §1). Không loại = mã đã nhìn trộm lọt vào phiên chấm cuối |
| iv | Nguồn độc lập thứ hai | **Bắt buộc** trước khi ghi `pool_t2.yaml`: `exchangeInfo` (mã kết luận *"chết trước `T2`"* mà còn `TRADING` hôm nay ⇒ DỪNG) + hỏi API cho mã kho-cụt lọt rổ |
| v | Định nghĩa *"sống tại `T2`"* | Có giao dịch THẬT — nến 1d cuối có `volume > 0` trước `T2`, đo được. Tiêu chí 15tr USDT / 180 ngày áp **riêng**, không trộn vào định nghĩa *"sống"* |
| vi | Đo đời sống cho bao nhiêu mã | Chỉ mã **lọt rổ** (~94), khoảng tồn tại cũ làm **cận trên**. Không đo cả 864 mã |
| vii | Khối cấu hình lockbox | Đặt ở **`tier_c`** — cấu trúc, không phải tham số, không tính DOF; đổi = phải có DR. **N giữ 114:** `dof.py:104` tính `N = 4 + 3×|tier_b|×2 + arm×2 + 20`, không đọc `tier_c` (đo từ mã, không suy) |
| viii | 46 mã trong seal 1 nhưng ngoài rổ `T2` | **Giữ file trên đĩa** (seal 1 vẫn kiểm được), **cấm dùng**. Lần chạm chấm **CHỈ** trên rổ `T2` |

## 3. Cơ chế "cấp lại" — và vì sao nó KHÔNG được mang tên `lockbox_seal_2.json`

**Vấn đề đặt tên là vấn đề thật, không phải thẩm mỹ.** `seal.py:80` ghi *"Gia hạn tạo FILE MỚI
(`lockbox_seal_2.json`, `_3.json`...)"*, và `L-Z13` (spec `:3876-3880`) cho *"tối đa 3 đoạn (1 gốc + 2 gia
hạn INCONCLUSIVE)"*. Gia hạn theo spec `:3356-3359` là niêm phong **dữ liệu MỚI** `[T3_cũ … T3_mới]`. Bản
cấp lại thì niêm phong **cùng khoảng `[T2,T3]`** với rổ đã sửa — khác nghĩa hẳn. Nếu bản cấp lại chiếm tên
`seal_2`, lần gia hạn thật đầu tiên mất chỗ, tức cấp lại **vẫn ăn vào trần** — ngược đúng điều Q5 chốt.

⇒ **Bản cấp lại mang tên `lockbox_seal_1_cap_lai.json`**, vẫn khớp mẫu `lockbox_seal_*.json` mà
`discover_seals()` (`seal.py:124-129`) và `backup.py:40` dùng — nên nó được backup và `verify_all_seals()`
kiểm như mọi seal khác. Không mã nào tách số đoạn từ tên file (kiểm bằng `grep`, 18/09/2026). Nó **là đoạn
1**, thay thế seal 1; `lockbox_seal_2.json` và `_3.json` giữ nguyên cho hai lần gia hạn.

Seal 1 **không được sửa** (`DR-D0PRE-07` §6, *"commit, không sửa"*), nên việc *"đã bị thay thế"* được khai
**trong bản cấp lại** (trường `thay_the: "lockbox_seal_1.json"`), không khai trong seal 1.

**Với `L-Z13` không phải đổi gì:** `validate_access_log()` (`access_log.py:90-123`) chỉ đếm số bản ghi
(`MAX_SEGMENTS = 3`, `:28`) và đòi `seal_path`/`seal_file_hash` đôi một khác nhau — **không đọc khoá
`segment` lần nào**. Lần chạm đoạn 1 ghi đúng một bản ghi trỏ bản cấp lại; seal 1 có **0 bản ghi vĩnh
viễn**; hai lần gia hạn nếu có dùng `seal_2`, `seal_3` ⇒ tổng tối đa 3 bản ghi, khớp trần sẵn có.

### Chốt kèm — thêm để cửa "cấp lại" không thành cửa đổi rổ sau khi đã thấy số

Q5 mở một cơ chế mới mà spec không có. Để nó không thể dùng đổi rổ theo kết quả:

1. **Chỉ cấp lại seal CHƯA TỪNG BỊ CHẠM** — sổ truy cập không có bản ghi nào trỏ nó (Q5).
2. **Tối đa MỘT lần cấp lại cho đoạn 1.**
3. **Rổ trong bản cấp lại phải là `config/pool_t2.yaml` đúng nội dung của commit ĐẦU TIÊN của file đó, và
   commit đó phải có TRƯỚC sự kiện `CONSUMED` đầu tiên không thuộc `B0`/`CTRL` trong
   `registry/trial_registry.jsonl`.** Sửa rổ sau mốc đó ⇒ máy từ chối cấp lại, cần DR mới.
4. Bản cấp lại phải trỏ tới DR cho phép nó (DR này).

🔑 **Chốt 3 thay cho câu tôi nói với chủ dự án lúc xác nhận** (*"không được cấp lại sau khi đã có bất kỳ
kết quả D9 nào"*). Đọc đúng chữ câu đó thì nó **chặn chính kế hoạch vừa chốt**: niêm phong được hoãn tới
lúc nối lại D8 (Q2), mà lúc đó D4/D5 đã tiêu suất rồi. Thứ cần khoá không phải *thời điểm niêm phong* mà
là *thời điểm chọn rổ* — rổ khoá trước mọi số, niêm phong về sau chỉ băm đúng rổ đã khoá. Chặt hơn câu cũ
ở chỗ đáng chặt (rổ), lỏng hơn ở chỗ không cần (lúc băm).

Máy canh đi cùng `TD-0309` (`kiem_pool_seal()`, ba trạng thái `KHAI_DUNG`/`KHAI_SAI`/`KHONG_KHAI`) và
`TD-0310` (`--tap LOCKBOX` tự chọn seal đang hiệu lực của đoạn 1; **không nhận đường dẫn seal**, nên người
vận hành không có cách gõ ra seal 1 — tiền lệ `TD-0127`).

## 4. Phạm vi thi hành

| Việc | Trạng thái | Ghi chú |
|---|---|---|
| `TD-0305` DR này | ✅ khi commit | |
| `TD-0306` đo đời sống → artifact MỚI | **gỡ ⏸** | Q3 bước 1 + iv + v + vi; không sửa `td0230`/`td0247`; không ghi dòng `CTRL` |
| `TD-0307` rổ `T2` | **gỡ ⏸** | Q2 + iii + vii; phép so bất đối xứng với `td0231` (không đòi khít — con số đó tính bằng chính hàm sai) |
| `TD-0309` vá `verify_seal` xét rổ | **gỡ ⏸** | §3 chốt 1–4 |
| `TD-0308` dữ liệu `[T2,T3]` (6 loại, có 5m) | **⏸ tới D8** | Q4 + Q6 + Q7; dữ liệu ở lại `lockbox/data/futures/`, chạy service `lockbox` |
| `TD-0310` ghi bản cấp lại | **⏸ tới D8** | §3 |
| `TD-0274` lần chạm thật | **khoá** | Không thuộc DR này |

## 5. Điều kiện mở lại

- Đo ở `TD-0306` cho thấy `MT-59` **không** làm lệch `pool_dung` tại `T2` ⇒ vẫn giữ bước sửa đường sản xuất
  (Q3 bước 2 chốt *"kết quả nào cũng sửa"*); chỉ ghi kết quả, không mở lại DR.
- Số mã rổ `T2` chết trong `[T2,T3]` ra **0** ⇒ đáng nghi (kỳ vọng nền ~3,1–3,4, P(0) ≈ 4%, là cận dưới vì
  đoạn này BTC −53%) ⇒ phải đối chiếu một mã cụ thể trước khi nhận, không mở lại DR.
- Cần cấp lại **lần thứ hai**, hoặc sửa `pool_t2.yaml` sau sự kiện `CONSUMED` đầu tiên ngoài `B0`/`CTRL` ⇒
  **DR mới**.

## 6. Điểm yếu, khai thẳng

1. **"Cấp lại" là cơ chế spec không có.** DR này thêm nó; nó không mâu thuẫn chữ nào của spec (gia hạn
   vẫn nguyên nghĩa, `L-Z13` không đổi), nhưng là một mở rộng. §3 chốt 1–4 là toàn bộ hàng rào của nó.
2. **Mọi phương án được trình bằng khung của một phiên** (§1). Xác nhận lại ở phiên thứ hai giảm rủi ro
   chép sai, không giảm rủi ro khung trình bày thiên về một phía.
3. **Chốt 3 dựa vào thời gian commit git**, sửa được bằng tay. Nó chặn sai sót và đổi rổ vô tình, không
   chặn một người cố ý làm giả lịch sử git.
4. **Lockbox ra phán quyết muộn:** dữ liệu tải ở D8, sau D4/D5/D9. Rổ đã khoá trước, nên trễ không làm
   lệch rổ — nhưng nếu dữ liệu `[T2,T3]` của mã nào đó không tải được lúc đó thì mới biết lúc đó.
