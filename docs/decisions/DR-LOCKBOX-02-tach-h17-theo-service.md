# DR-LOCKBOX-02 — Tách H17 theo service: service pipeline canh CÁCH LY, service lockbox canh BĂM

> **Ngày chốt:** 18/09/2026 · **Người quyết:** chủ dự án (chọn hướng (a) trong hai hướng được trình, phiên
> mã `55661c40`) · **0 trial** · **N giữ 114** · không đổi tham số nào.
> **Thi hành:** `TD-0316` (Khối 26). **Commit RIÊNG và TRƯỚC** mọi dòng mã của `TD-0316`.
> **Chặn:** `TD-0309` (vá `verify_seal()` xét rổ) chờ DR này — nó sửa đúng hàm mà DR này đổi vai trò.
> Mã `DR-LOCKBOX-02` + `TD-0316` đặt chỗ bằng commit `2ed44fc` (N12 mục 7c).
> **Phát hiện:** phiên `-93` nêu nghi vấn · phiên `55661c40` đo · phiên `c95baba3` tìm mảnh thứ ba (test khoá)
> và bác một câu sai của `55661c40` về sổ truy cập (§0.3).

---

## 0. Vấn đề — ba thứ đã chốt không thể cùng đúng

### 0.1. Đo được (18/09/2026, `HEAD dda3726`, 0 trial — chỉ chạy `E4 --verify-seal`)

| Service | Kết quả | Exit |
|---|---|---|
| `lockbox` | `✅ verify-seal PASS` | 0 |
| `freqtrade` | `🛑 L-Z14 FAIL` — cả 510 file của `lockbox_seal_1.json` đều `MISSING` | 89 |

E1/E2/E3 gọi `verify_all_seals(LOCKBOX_DIR, LOCKBOX_FUTURES_DIR)` lúc khởi động (`run_backtest.py:164`,
`run_wfo.py:125`, `run_ablation.py:68`) và thoát `EXIT_LOCKBOX_VERIFY_FAILED` khi có lỗi. Ở service `freqtrade`
— nơi chúng chạy — **cổng này FAIL mọi lần**.

### 0.2. Ba mảnh va nhau

1. **Cách ly tầng OS** (`ARCHITECTURE.md` 3.1, `docker-compose.yml:34,41`): `lockbox/data` bị che ở
   `tests`/`freqtrade`. Service `lockbox` là service duy nhất thấy nó, *"chỉ hợp lệ sau D9"*
   (`docker-compose.yml:46-47`).
2. **Test khoá xác nhận FAIL ở đó là ĐÚNG** (`tests/unit/test_touch_lockbox.py:56-68`): *"--verify-seal PHẢI báo
   lệch (MISSING) ở service này — đúng thiết kế cách ly… Nếu test này bất ngờ PASS, cơ chế che volume đã hỏng"*.
3. **H17** (spec `:4348`): *"Kiểm SHA-256 lockbox mỗi lần khởi động pipeline (L-Z13/14)"* — và H17 thuộc
   danh sách **KHÔNG BAO GIỜ CẮT** (spec `:4506`).

⇒ E1/E2/E3 **không có service hợp lệ nào để chạy trước D9**: ở `freqtrade` thì cổng H17 luôn FAIL; ở `lockbox`
thì phá chính sự cách ly mà (1) và (2) canh. Lời khuyên cũ *"E1/E2/E3 phải chạy qua `lockbox`"*
(`research-log.md:1375-1376`, và commit `d2d3549`) mô tả đúng hiện tượng nhưng dừng ở *"dùng đúng service thì hết
lỗi"*, không hỏi *"dùng service đó có đúng mục đích không"*.

### 0.3. 🔴 Hôm nay H17 không có cơ chế nào chạy thật ở service pipeline

- `L-Z14` (băm dữ liệu): FAIL mọi lần ở service che lockbox (§0.1) — về định nghĩa, không phải trục trặc.
- `L-Z13` (sổ truy cập): `make_access_record`/`append_access_record` **0 lời gọi sản xuất**, kể cả trong E4;
  `read_access_log`/`validate_*` **0 lời gọi ngoài chính module**; file `lockbox/lockbox_access.log`
  **không tồn tại** (kiểm 18/09/2026). Phiên `55661c40` từng trình chủ dự án rằng `L-Z13` *"kiểm được đầy đủ ở
  mọi service"* — **SAI ở tầng sản xuất**; phiên `c95baba3` bắt và đính chính. Đã đính chính với chủ dự án
  trước khi viết DR này; lựa chọn (a) không đổi vì (b) chịu y như vậy.
- **Spec** H17 ghi `(L-Z13/14)`; **mã** mang tên H17 (`verify_all_seals`, `seal.py:132-145`) chỉ làm `L-Z14`.
  "H17 gộp hai phép" là chữ của spec, không phải thứ mã đang làm.

⇒ Thứ duy nhất đang thật sự bảo vệ lockbox trước D9 là **việc che volume của docker-compose** — và không có gì
lúc chạy kiểm rằng việc che đó còn hiệu lực.

## 1. H17 canh hai thứ khác nhau

| Mối nguy | Phép phát hiện | Chạy được ở service che lockbox? |
|---|---|---|
| Lockbox bị **ĐỌC** ngoài quy trình (nhìn trộm) — đúng chữ H17 *"bị chạm ngoài quy trình"* | Ngăn: **cách ly**. Ghi dấu: sổ truy cập `L-Z13` | Cách ly: **kiểm được** (hiện không ai kiểm). `L-Z13`: có nghĩa chỉ khi có đường ghi |
| Lockbox bị **SỬA** | Băm SHA-256 `L-Z14` | **Không**, về định nghĩa — dữ liệu bị che |

🔑 SHA-256 chứng minh **toàn vẹn**, **không** chứng minh **không bị đọc**. Băm dữ liệu mỗi lần chạy pipeline
không canh được đúng mối nguy mà H17 viết ra để canh.

## 2. Quyết định — hướng (a)

**Ở service che lockbox (`freqtrade`, `tests`), H17 lúc khởi động E1/E2/E3 gồm:**

1. **CÁCH LY CÒN HIỆU LỰC** — tiến trình KHÔNG đọc được một file dữ liệu lockbox nào. Đọc được ⇒ **DỪNG** (mã
   thoát riêng, không trùng mã FAIL băm). Đây là tấm chắn **mới lúc chạy**; trước DR này nó chỉ có trong test
   `test_touch_lockbox.py:56`.
2. **FILE SEAL KHÔNG BỊ SỬA** — mọi `lockbox/lockbox_seal_*.json` được git theo dõi và không có thay đổi chưa
   commit. Seal nằm ngoài vùng che, nên kiểm được ở đây.
3. **SỔ TRUY CẬP** — nếu file sổ tồn tại thì `validate_before_d9()` (0 bản ghi trước D9). 🔴 **Khai thẳng:**
   trước khi `TD-0274` nối đường GHI cho lần chạm, phép này **không chứng minh gì** — sổ trống vì chưa ai ghi,
   không phải vì không ai chạm. Không được tính nó là một tấm chắn cho tới lúc đó.

**E1/E2/E3 không gọi `verify_all_seals()` nữa.** Chạy chúng ở nơi thấy được dữ liệu lockbox ⇒ vi phạm điều 1 ⇒
DỪNG — pipeline không bao giờ cần dữ liệu lockbox; lần chạm duy nhất đi qua E4.

**Băm dữ liệu (`L-Z14`) ở service `lockbox`, qua E4 `--verify-seal`, BẮT BUỘC tại:**
- ngay trước lần chạm duy nhất (`TD-0274`) — đã là thiết kế sẵn có;
- mỗi lần kiểm bản backup (`--verify-backup`, `TD-0085`) — đã có;
- **mỗi lần đóng cổng giai đoạn** từ D5 trở đi: đóng cổng phải có bằng chứng `L-Z14` PASS ở service `lockbox`
  **sau** lần đóng cổng trước. Cơ chế cụ thể (ghi bằng chứng ở đâu, ai đọc) do `TD-0316` dựng — DR này chốt
  **yêu cầu**, không chốt cách làm.

## 3. Cái giá — chấp nhận có ý thức

Nếu dữ liệu lockbox bị **sửa**, ta phát hiện ở điểm băm kế tiếp (đóng cổng / kiểm backup / trước lần chạm) thay
vì ở lần chạy pipeline kế tiếp. Chấp nhận vì: tiến trình pipeline **không với tới** dữ liệu đó (điều 1 giờ được
kiểm lúc chạy), nên việc sửa chỉ có thể đến từ ngoài pipeline; và thời điểm duy nhất việc sửa gây hại — lần chạm —
**luôn** được băm ngay trước.

Hướng (b) (bước băm riêng ở service `lockbox` trước mỗi lần chạy, E1 đọc kết quả có hạn dùng) bị loại: thêm một
bước tay mỗi lần chạy và một con số "hạn dùng" mới phải chốt, trong khi bằng chứng vẫn chỉ là *"đã khớp lúc X"* —
về bản chất cũng lùi một bước như (a), chỉ phức tạp hơn. Hướng (c) (chạy E1/E2/E3 trong service `lockbox`) bị
loại vì phá chính sự cách ly.

## 4. Không phải cắt H17

H17 nằm trong danh sách KHÔNG BAO GIỜ CẮT (spec `:4506`). DR này **không bỏ phép nào**: nó tách H17 thành đúng
hai phần mà chính dòng spec của nó gọi tên (`L-Z13/14`), đặt mỗi phần vào nơi nó chạy được thật, và **thêm** một
phép chưa từng chạy lúc chạy (cách ly còn hiệu lực). `L-Z14` vẫn chạy, ở các điểm đã định tại §2.

## 5. Giữ nguyên / đổi

- **Giữ nguyên:** `test_touch_lockbox.py:56` (FAIL ở service `tests` là đúng); hành vi `E4 --verify-seal` ở cả hai
  service; `verify_seal()`/`verify_all_seals()` vẫn là công cụ băm của E4.
- **Đổi (việc của `TD-0316`):** E1/E2/E3 thay lời gọi `verify_all_seals()` bằng phép kiểm §2 điều 1–3. Test khoá
  `test_td0072_verify_seal_wired.py` (đang ghim *"E1/E2/E3 gọi `verify_all_seals`"*) **đảo chiều, không xoá**
  (tiền lệ `TD-0150`): ghim phép kiểm mới được nối, và `verify_all_seals` KHÔNG còn nằm ở đầu E1/E2/E3.
- **Nợ đã khai, không thuộc DR này:** test E1 hiện không chạy `main()` thật qua Docker (`test_td0312` gọi thẳng
  lõi, `test_td0313` chỉ kiểm AST) — nên chưa có gì kiểm đường guard→H17 thật; phiên `c95baba3` giữ nợ này.

## 6. Điểm yếu, khai thẳng

1. **Điều 2 dựa vào git** trong container — chậm và từng vượt hạn (`TD-0293`). Không đọc được git ⇒ DỪNG
   (fail-closed), không bỏ qua.
2. **Điều 1 chỉ mạnh bằng định nghĩa "không đọc được"** của nó. `TD-0316` phải định nghĩa theo **việc thử đọc
   thật một file lockbox đã biết tên trong seal**, không theo "thư mục trống" — thư mục trống vẫn có thể là một
   mount khác trỏ đúng dữ liệu.
3. **Điều 3 rỗng nghĩa** cho tới `TD-0274` (§2) — đã khai để không ai đếm nó là một tấm chắn.
4. **Phát hiện "bị sửa" muộn hơn** (§3).

## 7. Liên quan

- `TD-0309` (vá `verify_seal()` xét rổ, `DR-LOCKBOX-01`) làm SAU `TD-0316`: nó đổi `verify_all_seals()`, hàm mà DR
  này chuyển thành công cụ riêng của E4.
- Mâu thuẫn ba quyết định ở §0.2 sẽ được ghi thành **một** mục `MT` trong `back-end-note.md` ở lần "chuẩn hóa và
  lưu" kế tiếp (N9), trỏ về DR này — không chép lại nội dung (`MT-03`).
