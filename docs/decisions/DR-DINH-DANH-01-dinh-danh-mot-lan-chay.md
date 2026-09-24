# DR-DINH-DANH-01 — Một lần chạy được định danh bằng gì · điểm kiểm soát tái lập §0d.4

> **Ngày chốt:** 24/09/2026 · **Người quyết:** chủ dự án (duyệt phương án C cho cả `MT-75` lẫn `MT-76`; chọn ngưỡng tái lập
> `0,001 R`). Phân tích + soạn: phiên mã `30c2eea5`.
> **Chi phí:** **0 trial** — không chạm dữ liệu, không chạm lockbox, không đổi `N = 114`, không đổi rào DSR.
> Mã `DR-DINH-DANH-01` + `TD-0377`…`TD-0380` đặt chỗ bằng commit `488a6e8` (N12 mục 7c). Commit **RIÊNG và TRƯỚC**
> mọi dòng mã của Khối 36.

---

## 1. Chuyện gì xảy ra

`TD-0366` (`DR-LZ12-01`) vá `L-Z12` để so theo cặp `(config_hash, code_commit)` và để lại hai nợ: `MT-75` (*"một lần
chạy được định danh bằng gì"*) và `MT-76` (*"cửa ghi `CTRL` tái lập không xét phiên bản mã, và khớp được lính canh
`"n/a"`"*). Rà toàn repo 24/09/2026 (đọc mã thật, không từ trí nhớ) cho thấy hai mục là **một câu hỏi, hai mặt**.

## 2. Đo trên đĩa — năm yếu tố quyết định một kết quả, sổ đang ghi từng cái một cách RỜI

| Yếu tố | Hôm nay ghi ở đâu | Khoảng hở |
|---|---|---|
| Tham số (`tool_d_config.yaml`) | `config_hash` = sha256 văn bản yaml (`config/loader.py:97`; đường chạy qua `bo_chay/moi_truong.py:141,158`) | `params_frozen_hash` **luôn bằng** `config_hash` trên cả 22 dòng ⇒ "hai băm độc lập" ở cửa `CTRL` tái lập thật ra là **một** |
| Mã | `code_commit` = HEAD (`measurement/gitinfo.py:55-61`) | 🔴 **22/22 dòng RESERVE có `reproducible_from_sha = False`** — hai lần chạy cùng commit vẫn có thể chạy mã khác nhau. E1/E3 chỉ GHI cờ; chỉ các hàm đóng cổng mới chặn cây bẩn |
| Dữ liệu | `provenance.data_hashes` | Không phép so nào đọc |
| Phạm vi (dataset, hướng, arm) | Trường riêng của RESERVE | Cửa tái lập **không so** |
| Môi trường (image Freqtrade) | Chỉ trong `provenance.cache_key()` (`measurement/provenance.py:214-236`) — **chưa ai gọi** | — |

⇒ **Không có trường nào định danh "một lần chạy".** Mỗi phép kiểm tự chọn một tập con: `L-Z12` chọn `(config, commit)`,
cửa tái lập chọn `config`, cache WFO (`wfo/cache.py:127-131, 223-229`) chọn `config + code + data`. Đúng hình dạng đã gây
sự cố `L-Z12` 20/09: một phép kiểm chọn nhầm tập con, đỏ oan, chặn cả hệ thống.

## 3. Ba phát hiện đổi cách đọc `MT-76`

1. 🔴 **"Bắt cửa ghi xét thêm `code_commit`" là SAI HƯỚNG.** Spec §0d.4 (`:586-595`): điểm kiểm soát = *"đưa giá trị mới
   vào `tool_d_config.yaml`, **commit**; chạy lại MỘT backtest …; kết quả phải KHỚP với bản ghi registry của trial đã chấp
   nhận giá trị đó (sai số ≤ 0.1% expectancy)"*. Điểm kiểm soát **theo định nghĩa chạy trên commit khác** trial gốc; chính
   mục đích của nó là chứng minh *"mã đã đổi ở giữa mà kết quả không trôi"*. Đòi cùng commit = mọi điểm kiểm soát không
   bao giờ thoả được — một chốt không bao giờ thoả được thì tệ hơn không có chốt.
2. 🔴 **Bước 3 của §0d.4 (so kết quả, ≤ 0,1%) CHƯA CÓ MỘT DÒNG MÃ.** `reproduces_trial_id` chỉ xuất hiện ở cửa ghi
   (`registry.py`). Và do `DR-LZ12-01`, một `CTRL` tái lập khác commit rơi vào **nhóm khác** trial gốc trong `L-Z12` ⇒
   **không gì kiểm điều §0d.4 đòi**. Đây là khoảng hở lớn nhất, lớn hơn cả hai mục `MT` như đã viết.
3. **Chưa có đường chạy tái lập nào.** Không entrypoint nào truyền `reproduces_trial_id`; E1 liệt kê `CTRL` nhưng không có
   đối số khai dạng tái lập. Sổ có 0 dòng tái lập ⇒ chưa thiệt hại. Điểm kiểm soát thật đầu tiên: lần đổi trạng thái tham
   số kế tiếp (`DR-012` Hạng 2) hoặc trước D11.

## 4. Quyết định

### 4.1 Định danh HAI TẦNG — mỗi phép kiểm khai mình dùng tầng nào

| Tầng | Gồm | Dùng cho |
|---|---|---|
| **Định danh CẤU HÌNH** | `config_hash` — **không đổi cách băm** (`DR-LZ12-01` §4 giữ nguyên) | Cửa `CTRL` tái lập (cùng cấu hình, mã ĐƯỢC khác) |
| **Định danh LẦN CHẠY** (dấu vân tay) | cấu hình + `code_commit` + **băm diff chưa commit của các file ảnh hưởng phép đo** (tập `THU_MUC_ANH_HUONG_PHEP_DO` + file đã theo dõi, cùng quy tắc `thay_doi_anh_huong_phep_do()`, `gitinfo.py:70`) + `data_hashes` + phạm vi (`dataset`, `direction`, arm) + image digest | `L-Z12` (bằng nhau TUYỆT ĐỐI: cùng vân tay khác kết quả ⇒ chạy lại không ghi sổ) |

- Vân tay ghi vào mọi dòng RESERVE **MỚI** (E1, E3, DR-015 bước 1). **E7 miễn** — dòng chốt pool mang lính canh `"n/a"`,
  không phải một lần chạy cấu hình.
- Dòng CŨ không có vân tay và **không được viết bù** (sổ append-only). `L-Z12` gom theo vân tay khi có, về cặp
  `(config_hash, code_commit)` của `DR-LZ12-01` khi không có.
- Dùng lại `cache_key()` cho phần `params_effective + git_sha + data_hashes + runtime_image_digest`; phần diff chưa commit
  và phạm vi **bọc thêm bên ngoài**, **không sửa `cache_key()`** — nó là khoá cache WFO, đổi nó là làm lạnh toàn bộ cache.

### 4.2 Cửa ghi `CTRL` tái lập — siết đúng trục (`MT-76`)

| # | Chốt | Vì sao |
|---|---|---|
| 1 | Từ chối `config_hash`/`params_frozen_hash` lính canh `"n/a"`/`""` (ở gốc hoặc ở dòng mới) | Hai chuỗi lính canh bằng nhau không chứng minh cùng cấu hình (`D-0001`…`D-0004`) |
| 2 | Gốc phải là trial THẬT: `budget_line ∈ {B1, B2, B3}`, CONSUMED, `outcome.expectancy` khác null | Không có gì để tái lập ở một dòng B0/CTRL hay một trial chưa ra số |
| 3 | `dataset`, `direction`, `param_under_test`, `param_value`, `provenance.data_hashes` phải BẰNG gốc | Đổi dữ liệu/phạm vi là phép thử mới, phải tiêu ngân sách |
| 4 | `code_commit` **ĐƯỢC khác** gốc — và vẫn được ghi | §0d.4, phát hiện 3.1. Loại hẳn phương án *"xét thêm `code_commit`"* |

### 4.3 Phép kiểm kết quả — bước 3 của §0d.4 thành máy

Mọi `CTRL` tái lập đã CONSUMED phải thoả:

```
abs(E_ctrl − E_gốc) ≤ max(0,001 × abs(E_gốc), san_tuyet_doi)        san_tuyet_doi = 0,001 R
```

- **Vì sao cần sàn tuyệt đối** (chủ dự án chọn 24/09/2026): expectancy của hệ thống này thường sát 0 (`Z0-T1` EXPLORE
  −0,0015 R) ⇒ 0,1% của nó ≈ 0 và gần như không lần tái lập nào đạt. `0,001 R` = **1% ngưỡng quyết định DSR 0,10 R**
  (`gates/thresholds.py`). Backtest cùng dữ liệu vốn tất định, nên sàn này chặt mà vẫn thoả được.
- Ngưỡng nằm trong `tool_d_config.yaml` (N4), là hằng kiểm soát, **không phải tham số chiến lược** ⇒ không vào bảng DOF,
  không đổi `N`. Thiếu khoá ⇒ phép kiểm **không PASS** (N6, cùng tinh thần `+inf`).
- Lệch ⇒ **ĐỎ**, và theo §0d.4 bước 4: *"giá trị CHƯA được áp, điều tra trước"*. 0 dòng tái lập ⇒ `pending`, không `ok`.
- Tên test theo `MT-09`: `test_td0379_*` — **không cấp mã `L-Z` mới**. **Không** vào `WARN_ONLY_CODES`.

### 4.4 Đính chính lý do của `DR-LZ12-01` §3.1

`DR-LZ12-01` giữ `CTRL` trong `L-Z12` với lý do *"`CTRL` tái lập tồn tại đúng để chứng minh cùng cấu hình cho cùng kết
quả"*. Chốt **giữ nguyên** (một lần chạy lại CÙNG vân tay vẫn phải khớp), nhưng lý do chỉ đúng cho tái lập **cùng
commit** — không phải ca §0d.4. Ca §0d.4 do phép kiểm 4.3 canh. Đính chính **nối vào cuối** §3.1 của `DR-LZ12-01`, giữ
chữ cũ.

## 5. KHÔNG thuộc DR này

- Không đổi cách băm `config_hash`; không sửa `cache_key()`; không viết lại dòng sổ nào.
- **Không bắt cây sạch trước khi đặt suất** (phương án D bị loại): với 2–3 phiên song song trên một thư mục (chủ dự án đã
  cố ý không dùng worktree, N12 mục 5), file dở của phiên khác sẽ chặn suất liên tục. Băm diff trong vân tay thay thế.
- Không dựng đường chạy tái lập ở E1 — việc riêng, **trước D11**. Khi dựng, nó sẽ gặp một cửa ghi và một phép kiểm đã đúng.

## 6. Thứ tự thi hành (Khối 36)

1. `TD-0377` — DR này (commit riêng, trước mọi dòng mã).
2. `TD-0378` — cửa ghi (4.2). **Chờ `TD-0375` rời `registry.py`** (cùng hàm `reserve()`).
3. `TD-0379` — phép kiểm kết quả (4.3).
4. `TD-0380` — vân tay lần chạy (4.1). 🔑 **Làm SỚM, trước suất kế tiếp:** mỗi suất đặt trước khi có vân tay là một bản
   ghi **vĩnh viễn** không định danh lại được. Cửa CHỌN ý tưởng đã mở (`DR-IQ-03`), D5 còn suất B1 phía trước.
5. "Chuẩn hóa và lưu": nối cách giải vào `MT-75`/`MT-76` khi `TD-0378`…`TD-0380` xong.

## 7. Điều kiện dừng — viết TRƯỚC

1. Phải sửa một khẳng định của test cũ (ngoài ca `L-Z12` gom theo vân tay) mới xanh ⇒ **dừng, báo**. Riêng
   `tests/lock/test_td0130_*` phải xanh **không đổi khẳng định nào**.
2. Sau mỗi việc, E6 trên sổ thật phải 0 chưa đạt; ca mới ⏳ (sổ có 0 dòng tái lập, 0 vân tay trùng). Thấy ✅ ở ca mới
   ⇒ PASS RỖNG, bản vá sai.
3. Sổ trial đổi dù một dòng trong lúc vá ⇒ dừng (khối này 0 trial).
4. Thêm khoá ngưỡng vào `tool_d_config.yaml` làm đỏ một phép kiểm DOF/`L-Z15`/`L-Z29` ⇒ **dừng, báo**: nghĩa là hằng
   kiểm soát đang bị đếm như tham số — cần chỗ đặt khác, không nới phép kiểm.

## 8. Điểm yếu đã biết — ghi để không ai tưởng đã kín

- Vân tay chứa băm diff chưa commit, nhưng **không chứa nội dung** diff ⇒ biết *"hai lần chạy khác mã"*, không tái dựng
  được mã đã chạy. Muốn tái dựng thì vẫn phải chạy trên cây sạch (các cổng đã đòi).
- 22 dòng cũ mãi mãi chỉ có cặp `(config, commit)` và `reproducible_from_sha = False`.
- Ngưỡng 4.3 so **expectancy** như chữ spec; `n_trades` lệch mà expectancy khớp vẫn QUA. Có chủ ý (spec chỉ nêu
  expectancy); ghi để nếu sau này cần siết thì là một DR mới, không phải một bản vá lặng lẽ.
