# DR-BC-01 — Lõi bộ chạy backtest: phạm vi, kế toán suất, và ranh giới của chữ "chạm"

> **Ngày chốt:** 18/09/2026 · **Người quyết:** chủ dự án (ba câu hỏi trả lời trong chat, phiên `-13`)
> **Mã việc:** `TD-0311` (Khối 27) · **Chi phí:** **0 trial**
> **Commit RIÊNG và TRƯỚC mọi dòng mã** của `TD-0312`/`TD-0313` (tiền lệ `DR-D4-08`, `DR-D4-01`).
> Tên `DR-BC-01` + mã `TD-0311…0313` đã nhắn phiên `-93` trước khi mở file (N12 mục 6) và được xác
> nhận còn trống.

---

## 0. Vấn đề

`ro_cho_tap()` (`src/tool_d/pool_giai_doan.py:44`, TD-0299 ✅) là **hàm chọn rổ theo giai đoạn**:
CALIB → `config/pool_t0.yaml`, WFO → `config/pool_t1.yaml`, LOCKBOX → từ chối (`MT-60`), và không
bao giờ trả `config/pool.yaml`. Nó có 11 test khoá và **không có một lời gọi sản xuất nào**.

Lý do đã được khai thẳng ở `docs/research-log.md:3095` và `DR-D1-05` §1: *"E1/E2/E3 **chưa** gọi hàm
này vì chúng chưa có bộ chạy thật; **khi viết bộ chạy thì phải gọi nó, không tự đọc file rổ**."*

Trạng thái ba entrypoint tại ngày chốt:

| | | |
|---|---|---|
| E1 | `entrypoints/run_backtest.py:65` | `NotImplementedError` |
| E2 | `entrypoints/run_wfo.py:119` | in sơ đồ fold rồi `EXIT_CHUA_CO_BO_CHAY` (97) |
| E3 | `entrypoints/run_ablation.py:75` | `NotImplementedError` |

**Cái giá của việc để nguyên** không phải là "thiếu một tính năng". Khối 25 đã dựng 143 mã rổ `T0` +
107 mã rổ `T1` và 1.357 file dữ liệu **đúng mốc**, chính là để chặn lệch sống sót theo chiều PASS ở
CALIB và WFO. Chừng nào không ai gọi `ro_cho_tap()`, công sức đó **không chảy vào phép đo nào**, và
người viết bộ chạy sau này — có thể là chính chúng ta sáu tháng nữa — sẽ làm đúng cái việc tự nhiên
nhất: mở thẳng một file rổ. Lúc đó không phép kiểm nào báo đỏ, vì `verify_seal()` không xét danh sách
pool (`MT-60` đã ghi đúng hình dạng này).

---

## 1. Phạm vi — lõi là HẠ TẦNG ĐO, không phải nối lại đường ống

`DR-IQ-01` §1 (17/09/2026) tạm dừng TD-0184 (bộ chạy ablation E3), cổng D4, D5 chạy B1, và D9
(TD-0286…0288). **Cùng bảng đó** ghi ▶ *giữ nguyên* cho:

> *"Hạ tầng đo (sổ trial, lockbox, cổng, testnet/D10–D11, Risk Supervisor) — **không phụ thuộc chiến lược**"*

và ▶ *làm tiếp* cho rổ pool point-in-time với lý do *"dùng lại cho MỌI chiến lược trên pool"*.

**Chốt:** lõi bộ chạy thuộc đúng hàng ▶ đó. Nó nhận một tên tập dữ liệu, một cửa sổ thời gian và một
tên chiến lược; nó không biết gì về Zone Absorption, về arm, về DG1–DG8. Bất kỳ ý tưởng nào thắng
suất (d) của `DR-IQ-01` §3 đều cần **đúng** lõi này. Dựng nó bây giờ tiêu **0 suất** và rút ngắn
đường đi của ứng viên kế tiếp.

### 1.1 Trong phạm vi

- `src/tool_d/bo_chay/` — dựng môi trường chạy, gọi Freqtrade, đọc kết quả, khai phạm vi ngày thật.
- Nối `ro_cho_tap()` vào lõi, làm nó thành **cửa duy nhất** lấy rổ + thư mục dữ liệu.
- Nối lõi vào **E1** `run_backtest.py`.
- Test khoá bằng **dữ liệu tự dựng** trong `tmp_path` (tiền lệ `tests/lock/test_lz49_lz50_backtest_nho.py`).

### 1.2 NGOÀI phạm vi — nói rõ để không ai đọc quá tay

- ❌ Bộ chạy ablation E3 (TD-0184 ⏸).
- ❌ Nối `chay_mot_fold` vào E2 (TD-0286 ⏸ tường minh trong `TASKS.md:671`).
- ❌ **Mọi lượt chạy thật trên `pool_t0`/`pool_t1`.** Một lượt như thế là *đánh giá cấu hình trên
  CALIB/WFO* = "chạm" theo `DR-014` §2 / `MT-02` ⇒ **tiêu 1 suất trong 114**, và `seal()` khiến nó
  không hoàn lại được (`L-Z53`). Lõi vì thế **mặc định không chạy**: thiếu cờ `--chay` thì E1 in kế
  hoạch rồi thoát bằng mã riêng, sổ trial bất biến từng byte.
- ❌ `gates/`, `wfo/lenh.py`, `gates/arm_record.py`.

🔴 **Việc có bộ chạy KHÔNG phải điều kiện nối lại đường ống.** `DR-IQ-01` §1 đã viết điều kiện nối
lại theo hướng bất đối xứng: phải có **dữ liệu MỚI chưa từng dùng** (sau `T3 = 2026-09-06`) đủ để
một phép đo đổi kết luận, **kèm DR viết TRƯỚC khi đo**. "Giờ đã có bộ chạy" không nằm trong danh
sách đó, và ghi câu này ra đây chính là để nó không lặng lẽ trở thành lý do thứ tư.

---

## 2. Đơn vị đặt chỗ trial = một CẤU HÌNH, không phải một fold

**Chốt:** một lượt walk-forward 3 fold tiêu **1 suất**, không phải 3.

**Căn cứ:**

- `DR-D4-10` §2.1 và `gates/arm_record.py` (TD-0232) đếm 9 arm = 9 suất — **một arm một lượt**, tức
  đơn vị kế toán là *cấu hình*.
- `DR-D9-01` §5: *"mỗi cấu hình chạy MỘT backtest"*.
- Cơ khí: `chay_wfo()` tính `van_tay_hien_tai(..., data_hashes=…)` ở `orchestrator.py:138` — **trước**
  vòng lặp fold. Nếu đặt chỗ nằm bên trong `chay_mot_fold` thì việc đọc dữ liệu để băm đã xảy ra
  **trước đặt chỗ đầu tiên**, tức đúng thứ tự `L-Z52` cấm. Cách đọc "một suất mỗi fold" không chỉ
  đắt gấp ba, nó còn **tự mâu thuẫn** với chốt mà nó định phục vụ.

### 2.1 🔴 Quyết định này SỬA chữ đang có ở hai chỗ

Cả hai chỗ dưới đây hiện viết ngược lại, và **phải sửa cùng đợt** — để không có hai nguồn sự thật:

| Chỗ | Chữ cũ | Thay bằng |
|---|---|---|
| `entrypoints/run_wfo.py:21-24` | *"chỗ nối là `chay_mot_fold` — và nó phải tự gọi `TrialLedger.reserve()` TRƯỚC khi chạm dữ liệu"* | `main()` của entrypoint đặt chỗ **một** suất cho cả cấu hình; `chay_mot_fold` chỉ **chứng minh** đã có đặt chỗ, qua `GiayPhepChay` |
| `src/tool_d/wfo/orchestrator.py:24-28` | *"`reserve()` phải được gọi TRƯỚC khi `chay_mot_fold` chạm dữ liệu … Chỗ gọi truyền vào một `chay_mot_fold` đã tự đặt chỗ"* | như trên |

**Phần KHÔNG đổi, và nó là phần quan trọng:** lý do `orchestrator` từ chối tự đặt chỗ — *"nó không
biết `budget_line` nào, và đoán hộ là cách chắc chắn tiêu sai ngân sách"* — vẫn đúng nguyên vẹn, và
chính là căn cứ của §4 bên dưới. Cái sai của chữ cũ là **ai** đặt chỗ và **bao nhiêu lần**, không
phải nguyên tắc *"không đoán hộ"*.

### 2.2 Cơ chế thay thế: `GiayPhepChay`

Lõi **không tạo** đặt chỗ, nhưng **từ chối chạy nếu không có**. `chay_mot_luot()` nhận một
`GiayPhepChay(ledger, trial_id, budget_line)` và ở dòng đầu tự **đọc lại sổ**, đòi trạng thái
`RESERVED`. Nó không nhận lời khai — cùng triết lý `DR-014` §3 (*"máy tự ghi, người không có đường
nhập liệu"*) và cùng bài học `MT-10`/TD-0148 (*"một bộ chạy trả ngày dự kiến thay vì ngày thật sẽ vô
hiệu hoá phép kiểm hoàn toàn"*).

---

## 3. "Băm dữ liệu" KHÔNG phải "chạm dữ liệu"

**Vấn đề:** `L-Z52` đòi `reserve()` chạy *"TRƯỚC KHI CHẠM BẤT KỲ DỮ LIỆU NÀO"*
(`ledger/registry.py:497-498`). Nhưng `registry/schemas/trial_event.schema.json` đặt `provenance`
là **bắt buộc** cho sự kiện `RESERVE`, và §0d.5 đòi đủ 7 khoá — trong đó có `data_hashes`. Mà băm
file là **mở file dữ liệu ra đọc byte**.

**Chốt:** băm ≠ chạm. Được phép băm trước rồi `reserve()` sau, và dòng `RESERVE` mang `data_hashes`
đầy đủ ngay.

**Căn cứ:** `DR-014` §2 và `MT-02` định nghĩa "chạm" là **ĐÁNH GIÁ CẤU HÌNH** trên CALIB/WFO/LOCKBOX.
`N2` của `CLAUDE.md` chép lại cùng định nghĩa, và nói thêm rằng *đo thông tin mô tả* (danh sách cặp,
min notional, độ dài lịch sử) **không** tính là chạm. Đọc byte để tính sha256 không đánh giá cấu hình
nào; kết quả của nó là một chuỗi hex về **nội dung file**, không phải một phát biểu về chiến lược.

### 3.1 🔴 Giá phải trả, ghi ra để không ai quên

Đây là **nới một định nghĩa bằng lập luận**, và dự án này đã trả giá cho việc nới chốt trước đây
(`L-Z17`). Nên phạm vi của §3 hẹp đúng bằng câu sau, không rộng hơn một chữ:

> Chỉ *đọc byte của file dữ liệu để tính hàm băm* mới được coi là không-chạm.

**Không** mở cho: nạp dataframe, tính chỉ báo, đếm nến, đọc ngày đầu/cuối, hay bất kỳ việc đọc nào
khác. Nếu sau này cần một việc đọc mới trước `reserve()`, đó là một quyết định **mới**, không phải
suy ra từ dòng này.

### 3.2 Hệ quả phải giữ

Vân tay cache WFO (`wfo/cache.py:67-79`) vẫn **bắt buộc** mang hash thật. Một `data_hash` rỗng sẽ
khớp với chính nó ở lần chạy sau và mở lại đúng cái bẫy Tool A mà module cache sinh ra để chặn.
Phương án *"`RESERVE` ghi `data_hashes` rỗng, bản đủ vào `CONSUME`"* (tiền lệ `build_pool.py:482`)
đã được cân nhắc và **loại**, vì `validate_provenance()` không đòi dict khác rỗng
(`provenance.py:154-186`) ⇒ không máy nào bắt được nếu nó rỗng vĩnh viễn.

---

## 4. `budget_line` không có giá trị mặc định

**Chốt:** E1 **bắt buộc** khai `--budget-line`, tập đóng `{B1, B2, B3, CTRL}`. Thiếu ⇒ từ chối chạy,
sổ không thêm dòng nào.

**Căn cứ:** `orchestrator.py:26-28` — *"đoán hộ là cách chắc chắn tiêu sai ngân sách"*. Câu N3 của
`CLAUDE.md` (*"Cần 'xem thử' thì đó là E1 với `budget_line = B3` và có ghi sổ"*) gợi B3 **về ngữ
nghĩa**, nhưng biến nó thành **mặc định của CLI** chính là đoán hộ: người gõ lệnh sẽ không bao giờ
phải nhìn thấy mình đang tiêu dòng nào.

Ràng buộc kèm theo, thi hành bằng máy:

- `B1` — để `_kiem_cua_b1()` (`registry.py:456`) tự phán theo `DR-D5-01`; E1 không chép lại luật.
- `CTRL` — bắt buộc kèm `--reproduces-trial-id` **hoặc** `--ctrl-output`, và từ chối nếu đầu ra có bất
  kỳ chỉ số hiệu năng nào. `CTRL_OUTPUT_ALLOWED` (`registry.py:65`) là **danh sách CHO PHÉP**, không
  phải blocklist — giữ nguyên tính fail-closed đó, không nới (xem `MT-19`, còn mở).

---

## 5. Điều kiện mở lại phần đang ⏸

Không có gì trong DR này gỡ ⏸ cho TD-0184, TD-0286, TD-0258, hay cổng D4. Điều kiện nối lại vẫn đúng
nguyên văn `DR-IQ-01` §1, và DR này **thêm** một câu để bịt một lối vòng có thể mở ra từ chính nó:

> 🔴 Sự tồn tại của một bộ chạy backtest chạy được **không** là căn cứ nối lại. Cũng không phải:
> *"đằng nào cũng đã viết xong, chạy thử một lượt cho biết"* — một lượt như thế là `seal()`, và
> `seal()` không hoàn lại được.

---

## 6. Giới hạn đã biết tại ngày chốt

1. **Chưa xác minh** cận trên của `--timerange` Freqtrade là BAO GỒM hay KHÔNG BAO GỒM nến đúng tại
   mốc. Việc này chặn `TD-0312` và **phải đo**, không đoán: dữ liệu `pool_t1` kết thúc đúng
   `2026-01-29 00:00 UTC` = `T2`, trong khi `kiem_pham_vi_du_lieu()` (`wfo/folds.py:244`) chỉ cho tới
   `test_end − 1 ngày`. Lệch một ngày ở đây là **một ngày dữ liệu tương lai**.
2. **Bằng chứng của Khối 27 là bằng chứng về CƠ CHẾ, không phải về DỮ LIỆU.** Test dùng dữ liệu tự
   dựng trong `tmp_path`. Ba đường đã cân nhắc: chạy thật trên `pool_t1` = tiêu 1 suất (loại, §1.2);
   chạy trên EXPLORE = 0 suất nhưng `ro_cho_tap("EXPLORE")` **từ chối** nên không đi qua chính mối
   nối cần chứng minh (loại); fixture tự dựng (chọn). Giới hạn này phải nằm trong docstring của test,
   không để ngầm.
3. **Rổ `T0` không có dữ liệu 5m** (`DR-D1-05` §3; đo lại 18/09: `pool_t0/futures` **0** file 5m,
   `pool_t1/futures` **107** file). ⇒ CALIB chưa chạy được `--timeframe-detail 5m` cho tới `TD-0252`.
   Lõi vì thế **từ chối** khi được xin 5m mà thư mục không có, thay vì im lặng chạy ở độ phân giải
   1H — đúng cái bẫy `do_td0193_lenh_nam_explore.py:21-22` đã ghi.
4. **Nến startup đọc sang vùng tập trước.** `ZoneAbsorption.startup_candle_count = 1000` nến 1H
   ≈ 41,7 ngày, và file dữ liệu `pool_t1` bắt đầu từ `T0`. Một lượt WFO vì thế **đọc byte vùng CALIB**
   để khởi động chỉ báo, trong khi cửa sổ đánh giá vẫn là `[T1, T2)` và `L-Z55` vẫn xanh. Câu hỏi
   *"warm-up có tính là chạm CALIB không"* **chưa ai chốt**; DR này không chốt hộ, chỉ bắt lõi khai
   thêm `nap_start`/`nap_end` cạnh `observed_start`/`observed_end` để khi có người hỏi thì có số mà
   trả lời, thay vì phải nhớ.
5. **Hai tập lệnh cho cùng một cấu hình.** E2 qua `chay_wfo` chạy **3 lượt** (mỗi fold một lượt, bắt
   buộc bởi `kiem_pham_vi_du_lieu` tầng (b)); còn `wfo/lenh.py:16-21` + `DR-D9-01` §5.1 chạy **1 lượt**
   toàn cửa sổ rồi cắt lát. Không phải lỗi — trạng thái danh mục §6.8f và biên fold khác nhau thật —
   nhưng là **hai nguồn số**, và phải khai bản nào nuôi cổng nào. Ghi thành `MT-61`.
