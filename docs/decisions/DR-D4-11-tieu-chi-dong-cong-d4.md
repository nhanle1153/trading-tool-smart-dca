# DR-D4-11 — Cổng D4 đóng bằng HIỆN VẬT, không bằng số trial đã tiêu

> **Ngày chốt:** 14/09/2026 · **Người quyết:** chủ dự án · **Việc:** `TD-0236` (Khối 18)
> **Giải:** `MT-38` (`back-end-note.md:127`) · **0 trial**
> **Commit RIÊNG và TRƯỚC mọi dòng mã** — kiểm bằng `git merge-base --is-ancestor`, không bằng mắt.

---

## 1. Mâu thuẫn có BA lớp, và sửa `18` thành `9` chỉ chạm lớp nông nhất

Tiêu chí hiện hành (`back-end-note.md:80`, `OQ-11` phương án PA3, chốt 07/09/2026, commit
`6342113`) định nghĩa khoá cổng là: *"`d4_complete` ← **đếm được đúng 18 trial `B2` CONSUMED**"*.

| Lớp | Nội dung | Bằng chứng |
|---|---|---|
| **(a) Số** | `DR-D4-01` cấp **9**, không phải 18 | `DR-D4-01:15` (*"Long trước, 9 trial"*), `:112` (*"Đợt này tiêu **nửa** của B2"*) |
| **(b) Hướng** | 9 suất là **Long-only**, và 9 suất còn lại **không có đường tiêu** | `DR-D4-01:113` (*"nửa còn lại **không tự động** thuộc về Short"*); `runtime_state.json` → `d3_5_delta_r_niem_phong.SHORT = "unreadable"` ⇒ điều kiện §2b(2) của `DR-D4-01` chưa đạt ⇒ `L-Z56` **từ chối** chạy ablation Short |
| **(c) Bản chất** | 9 suất **không mua 9 phán quyết** | `DR-D4-10:211-213`: `Z0-T1` = **phán quyết**, `Z0-T0` = **chẩn đoán** (*"suất này KHÔNG mua một phán quyết Nhánh 1"*), **7 arm nhóm C = thống kê MÔ TẢ**; `:215` *"**CẤM** đọc `DSR_adj` của nhóm C như một phán quyết"* |

Sổ thật lúc ký: `registry/trial_registry.jsonl` **13 dòng = 5 trial** (4 × `B0` + 1 × `CTRL`),
**0 dòng `B2`**. Cổng đòi 18, kịch bản tối đa cho 9, thực tế có 0.

**Chẩn đoán là *hai quyết định VA NHAU*, không phải *một cái thay cái kia*** — đây là dữ kiện, không
phải suy luận: `grep -n "d4_complete\|OQ-11\|runtime_state"` trong `DR-D4-01` cho **0 kết quả**, tức
quyết định cấp 9 **không biết** khoá cổng đòi 18. Thứ tự commit khớp: `6342113` (07/09) → `df011da`
(08/09).

---

## 2. Vì sao ĐẾM TRIAL là một PASS RỖNG dựng sẵn — lý do chính của DR này

Đếm trial từng là một **đại diện hợp lý** cho câu *"ablation đã thực sự chạy chưa"*. Sau
`DR-D4-10`, nó thôi là đại diện của bất cứ thứ gì:

> Nếu cổng đếm `N` dòng `B2` CONSUMED, nó sẽ **PASS kể cả khi toàn bộ `N` suất đó đều là loại
> MÔ TẢ và `Z0-T1` — cấu hình DUY NHẤT D4 còn phán quyết được — chưa từng chạy.**

Một cổng xanh trong khi thứ duy nhất nó tồn tại để chứng nhận đã **không xảy ra**. Không có ca đỏ
nào, không có triệu chứng nào. Đây đúng hình dạng mà dự án đã đặt tên nhiều lần (*"lớp canh chĩa
nhầm hướng"*, `TD-0168`; *"PASS RỖNG"*, cổng D2/`TD-0084`), và lần này nó **nằm sẵn trong định
nghĩa cổng** chứ không phải trong một phép kiểm nào.

⇒ Hạ khoá từ 18 xuống 9 **không sửa điều này** — nó chỉ làm con số khớp `DR-D4-01` trong khi giữ
nguyên tính chất PASS RỖNG.

---

## 3. QUYẾT ĐỊNH — cổng D4 đóng khi HIỆN VẬT chứng minh phán quyết đã xảy ra

Cổng `d4_complete` **THAY** tiêu chí đếm trial bằng tập điều kiện sau. Mọi điều kiện phải đạt;
thiếu một ⇒ **từ chối ghi khoá** (fail-closed, cùng khuôn `close_d3_5_gate()`).

| # | Điều kiện | Máy kiểm |
|---|---|---|
| 1 | Tồn tại bản ghi arm `Z0-T1` hợp lệ, mang `pham_vi_phan_quyet == "phan_quyet"` và `ket_cuc` ∈ {`PASS`, `INCONCLUSIVE`, `FAIL`} | `src/tool_d/gates/arm_record.py:150` `validate_arm_record()`; bảng cờ `:242-249` |
| 2 | Không bản ghi nào mang `pham_vi_phan_quyet == "mo_ta"` mà lại có `ket_cuc == "PASS"` | `arm_record.py:284` — **đã có sẵn**, DR này chỉ gọi nó ở tầng cổng |
| 3 | Mọi bản ghi mang `delta_r_pham_vi` + `so_ma_da_chay` | `registry/schemas/arm_result.schema.json:138` (`TD-0234`, đã `required`) |
| 4 | `d4_huong` được khai tường minh (đợt này: `"LONG"`) | trường mới trong `runtime_state.json` |
| 5 | `d4_han_che` nói rõ D4 **không** phán quyết câu DCA | `DR-D4-10` §8 chặng (d)(g), nhãn `nguoi-khai` |
| 6 | Số dòng `B2` CONSUMED **khớp số arm đã chạy**, không so với hằng số | đọc sổ `trial_registry.jsonl` |

### 🔑 Nguyên tắc thiết kế: bỏ HẰNG SỐ, giữ QUAN HỆ

Điều kiện 6 cố ý **không** mang một con số. `18` và `9` đều là hằng số sẽ lỗi thời — `18` đã lỗi
thời sau 24 giờ. *"Số trial đã tiêu khớp số arm đã chạy"* là một **quan hệ**, đúng ở mọi phạm vi
D4 tương lai (Long-only, cả hai hướng, hay một phạm vi khác chưa nghĩ ra).

Đây là bài học `TD-0171` áp nguyên: *tách ghim QUAN HỆ khỏi ghim QUYẾT ĐỊNH*. Quan hệ nằm ở điều
kiện 6; **quyết định** (phạm vi Long-only của đợt này) nằm ở điều kiện 4, đúng MỘT chỗ, và chỗ đó
buộc người sửa phải viết ra chữ `d4_huong` — không phải đổi một hằng số vô danh.

---

## 4. Thứ DR này KHÔNG đụng

- **Kế toán 9 suất của `DR-D4-01` giữ nguyên** — DR này đổi *cổng đọc gì*, không đổi *D4 tiêu bao
  nhiêu*. (Cùng kỷ luật `DR-D4-10:427`: *"DR này KHÔNG tự sửa kế toán 9 suất của `DR-D4-01`"*.)
- **`N_ĐĂNG_KÝ = 114`, rào DSR `3,0777`, `|tier_b| = 12`** — không đổi. DR này **0 trial**: không
  chạm CALIB/WFO/LOCKBOX, không đánh giá cấu hình nào.
- **`close_d4_gate()`** — thuộc `TD-0186`, không viết ở đây. DR này chỉ chốt *tiêu chí*; hàm đóng
  cổng là việc sau, và nó phải GỌI tiêu chí này chứ không khai lại (tránh hai danh sách song song
  trôi lệch — bài học cổng D3.5, nơi *"điều kiện đóng cổng"* và *"điều kiện được chạy ablation"*
  cố ý là MỘT hàm).
- **`back-end-note.md:80`** — nguồn của con số 18. Sửa nó cần lệnh **"chuẩn hóa và lưu"** (N9);
  DR này ghi nhận rằng nó **sẽ** phải sửa, và cho tới lúc đó hai văn bản còn lệch. Ghi ra để
  không ai tưởng đã đồng bộ.

---

## 5. Điều kiện mở lại cho hướng SHORT — viết TRƯỚC, không phải chốt rỗng

Cổng đóng với `d4_huong: "LONG"` **không** có nghĩa D4 đã phủ cả hai hướng. Mở cổng cho Short đòi
đủ **ba** điều kiện của `DR-D4-01` §2b (trỏ tới, **không chép lại** — một nguồn sự thật):

1. `DG7` tồn tại và có ngưỡng riêng đã calibrate;
2. `Δ_R(SHORT)` trạng thái `ok` và đã commit — 🔴 *"nếu phải sửa `L-Z56` để nó đi qua thì điều kiện
   này **chưa** đạt"*;
3. Ngân sách còn ≥ 9 suất sau khi trừ mọi thứ đã tiêu.

Hôm nay điều kiện 2 **chưa đạt** (`d3_5_delta_r_niem_phong.SHORT = "unreadable"`).

🔴 **KHÔNG tạo khoá `d4_short_complete`.** Phương án đó đã được xét và loại ở §6 — một khoá không
bao giờ đóng được thì sớm muộn bị gỡ, và lúc gỡ thì gỡ luôn phần đúng của nó (bài học cổng D3:
*"một chốt không bao giờ thoả được thì tệ hơn không có chốt"*).

---

## 6. Hai phương án đã xét và LOẠI — ghi ra để người sau khỏi đề xuất lại

**(a) Hạ khoá 18 → 9, thêm trường `d4_huong`.** Loại vì §2: nó sửa con số mà giữ nguyên tính chất
PASS RỖNG. Phần đúng của nó (`d4_huong`) **được giữ lại** làm điều kiện 4.

**(b) Tách `d4_long_complete` / `d4_short_complete`.** Diễn đạt đúng việc Short bị hoãn, nhưng tạo
một khoá mà hiện trạng **không có đường nào đóng** (điều kiện 2 của §2b bị chặn bởi một artifact đã
niêm phong). Loại vì lý do ở §5.

---

## 7. Thi hành, và kiểm-có-răng bắt buộc

1. DR này commit **RIÊNG và TRƯỚC** mọi dòng mã; kiểm `git merge-base --is-ancestor <sha_DR> <sha_code>`.
2. `TD-0236` khoá 🔓→🔒 và commit riêng **trước** khi viết mã (quy tắc 14, N12 mục 4).
3. Tiêu chí dựng thành hàm thuần + test khoá. **Ba phép phá bắt buộc, mỗi phép phải ra ca đỏ đã
   dự kiến:**
   - Bộ hiện vật chỉ gồm 8 arm `mo_ta`, **thiếu `Z0-T1`** ⇒ cổng **TỪ CHỐI**.
   - Bản ghi `Z0-T1` mang `pham_vi_phan_quyet = "mo_ta"` ⇒ cổng **TỪ CHỐI**.
   - Trả tiêu chí về hằng số `18` ⇒ **đúng 1 ca đỏ**, và ca đó phải là ca **nêu đích danh
     `DR-D4-11`** (ghim QUYẾT ĐỊNH), không phải ca ghim quan hệ.
4. Bằng chứng chạy trong Docker (N7). Sổ `trial_registry.jsonl` giữ nguyên số dòng trước/sau.

### 🔴 Đính chính 14/09/2026 — dự đoán ở mục 3 SAI, giữ nguyên chữ cũ làm lịch sử

Mục 3 viết *"Trả tiêu chí về hằng số `18` ⇒ **đúng 1 ca đỏ**"*. Đo thật trong Docker: **6 ca đỏ**.
Ca ghim QUYẾT ĐỊNH (`test_module_khong_chua_hang_so_18_hay_9`) **có** đỏ đúng như dự đoán, nhưng
năm ca nữa cũng đỏ vì ghim cứng `18` phá luôn **hành vi** chứ không chỉ vi phạm luật.

Kết quả **mạnh hơn** dự đoán, không yếu hơn — nhưng phải ghi lại, vì một dự đoán sai nằm trong tài
liệu quyết định thì lần sau có người đọc nó rồi tưởng lớp canh đã hỏng khi thấy 6 thay vì 1. Đây
cũng đúng bài học dự án đã trả giá nhiều lần: *phát biểu đúng mức những gì phép đo nói*.

Ba phép phá, kết quả THẬT (khôi phục `diff -q` giống hệt):

| Phép phá trên `d4_gate.py` | Ca đỏ |
|---|---|
| Bỏ `_kiem_arm_phan_quyet()` | **2** — `test_chi_co_arm_MO_TA_va_ke_toan_KHOP_van_bi_TU_CHOI`, `test_Z0_T1_thieu_ket_cuc_thi_TU_CHOI` |
| Ghim cứng `18` thay cho quan hệ | **6** — gồm ca ghim QUYẾT ĐỊNH |
| Bỏ `_kiem_ke_toan()` | **1** — `test_so_b2_lech_so_arm_thi_TU_CHOI` |

📌 Một quan sát từ phép phá thứ nhất, đáng ghi vì nó sửa một khẳng định ngầm: ca
`test_Z0_T1_mang_co_mo_ta_thi_TU_CHOI` **KHÔNG** đỏ khi bỏ `_kiem_arm_phan_quyet()` — nó được
`validate_arm_record()` bắt độc lập (`arm_record.py:242-252`). Tức ca đó canh **lớp cũ**, không
canh lớp mới. Hai lớp chồng nhau ở đúng chỗ này là tốt, nhưng đừng đọc nó thành *"tiêu chí mới
bắt được cờ sai"*.

## 8. Việc phái sinh, đã biết, chưa làm

- **`back-end-note.md:80`** còn ghi 18 — chờ lệnh "chuẩn hóa và lưu" (N9).
- **Front-end đã coi `d4_complete` là cổng cứng** — `dashboard-ui/src/toolD/nguHanhTrinh.js:62`,
  `:80` (`laCongCung: true`), có test ghim `nguHanhTrinh.test.js:20`. Repo riêng, **không** sửa từ
  đây; dashboard chỉ đọc khoá nên nó tự đúng theo, nhưng chữ *"18 trial"* ở `dashboard-ui/TASKS.md:366`
  sẽ lỗi thời — báo sang phía đó, không tự sửa.
- **`TASKS.md:481` (`TD-0236`) ghi Phụ thuộc `TD-0235 · TD-0186`** trong khi tiêu chí XONG của nó
  nói *"PHẢI xong TRƯỚC khi `close_d4_gate()` được viết một dòng nào"* — mà `close_d4_gate()` là sản
  phẩm của `TD-0186`. **Vòng tròn.** DR này đọc `TD-0186` ở đó là **tham chiếu chéo, không phải điều
  kiện tiên quyết**; ghi ra để cãi lại được chứ không im lặng chọn.
