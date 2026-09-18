# DR-IQ-02 — Sổ ý tưởng là nhật ký sự kiện; sự kiện HUỶ CHỌN (`VOIDED`)

> **Ngày chốt:** 19/09/2026 · **Người quyết:** chủ dự án (chọn phương án (b) của `MT-65` sau bảng so sánh ba
> phương án, duyệt kế hoạch, phiên mã `2febd25e`)
> **Chi phí:** **0 trial** · Không chạm dữ liệu thị trường · Không chạm lockbox.
> Mã `DR-IQ-02` + `TD-0325`…`TD-0327` đặt chỗ bằng commit `a98c890` (N12 mục 7c) trước khi file này tồn tại.

> ✅ **Phiên IDEA và phiên CHỌN ĐƯỢC đọc file này** (`DR-009`): nó chỉ nói luật ghi sổ, **không chứa con số
> hay kết cục định lượng nào của Tool D**. Ai sửa file này phải giữ nguyên tính chất đó.

---

## 1. Chuyện gì đã xảy ra

Ngày 18/09/2026 (quý 3), một dòng `SELECTED` cho `IQ-0002` được ghi vào `registry/idea_queue.jsonl`
(commit `71bbaa1`), theo yêu cầu tường minh của chủ dự án, trước ngày hiệu lực 01/10/2026 của
`DR-Q4-2026-tieu-chi-chon-y-tuong.md`. Phép kiểm `TD-0120` tra file tiêu chí theo quý của `selected_at`, nên thấy
quý 3 (`HAN_NGACH_CHON: 0`) và mã `TC-Q4-…` không có trong file quý 3. `TD-0120` không thuộc `WARN_ONLY_CODES`,
nên kiểm tra sổ đỏ, và mọi hàm đóng cổng từ chối. Sổ append-only nên không gỡ được dòng đó. Chi tiết ở `MT-65`
trong `back-end-note.md`.

## 2. Gốc thật: ba lỗ có từ trước, IQ-0002 chỉ là lần đầu đi đường thật

1. **Sổ ý tưởng chưa có luật chuyển trạng thái.** Spec §9c.7.3 cho một bản ghi đổi `status`
   QUEUED → SELECTED → ARCHIVED, nhưng sổ lại append-only. Đây là cùng mâu thuẫn mà `MT-01` đã giải cho sổ
   trial bằng luật "mỗi dòng là một sự kiện" (N8), kèm sự kiện sửa sai `REFUND`/`CONTAMINATE`. Sổ ý tưởng chưa
   từng được áp luật đó.
2. **Cửa CHỌN chưa từng chạy được đúng.**
   - Không có công cụ ghi dòng `SELECTED`: cửa NỘP chặn trạng thái này.
   - Cách chọn bình thường là chép nguyên văn nội dung đơn vào dòng `SELECTED`. Khi đó `TD-0126` so dòng chọn
     với **chính dòng QUEUED cùng mã**, báo trùng 100% và đỏ.
   - `TD-0124` đếm mọi dòng là một đơn nộp mới.
   - Mọi test khoá đều dựng một dòng `SELECTED` đứng một mình.
3. **Hạn ngạch chỉ kiểm khi bằng 0.** `TD-0120` không kiểm "số lần chọn ≤ `HAN_NGACH_CHON`".

## 3. Ba phương án đã xét

| | (a) Miễn trừ đích danh dòng IQ-0002 | **(b) Huỷ dòng, chọn lại trong quý 4** ✅ | (c) Đổi luật TD-0120 tra quý theo mã TC |
|---|---|---|---|
| Bản ghi chính thức của suất (d) | Mãi mãi là "chọn trước hiệu lực, được miễn trừ" | Lần chọn **có hiệu lực** mang ngày quý 4. Lần sớm vẫn thấy trong sổ, đã huỷ | Sạch về hình thức vì luật đã nới |
| Lớp canh | Tiền lệ "sai thì thêm miễn trừ" | Không nới luật nào; thêm một cách sửa sai có điều kiện chặt | Nới chung, mở lại đúng lỗ `TD-0120` đóng |
| Lần chọn sau | Vẫn hỏng (mục 2) | Sửa cả ba lỗ ở mục 2 | Vẫn hỏng |

**Loại (a)** vì nó để nguyên ba lỗ ở mục 2, và vì kết quả suất (d) sẽ mãi mang dấu miễn trừ. **Loại (c)** vì nó
cho phép chọn khi tiêu chí chưa có hiệu lực, đúng thứ `TD-0120` sinh ra để chặn.
**Giá của (b) về tiến độ gần như bằng 0:** `DR-Q4-2026` §1 buộc suất (d) phải có lockbox MỚI và đi đủ chu trình
từ D0, nên trial đầu tiên không thể chạy trong khoảng chờ tới 01/10.

## 4. Luật

### 4.1. Mỗi dòng là một sự kiện trên `idea_id`
Thứ tự sự kiện là thứ tự dòng trong file. Trạng thái hiện hành của một mã tính lại bằng cách đọc hết sổ.
**Không sửa, không xoá dòng đã ghi** (mở rộng N8 sang sổ ý tưởng).

| Trạng thái hiện hành | Sự kiện được phép tiếp theo | Trạng thái sau |
|---|---|---|
| *(chưa có dòng nào)* | `QUEUED` · `REJECTED` (cửa NỘP) | QUEUED · REJECTED |
| QUEUED | `SELECTED` (cửa CHỌN) · `ARCHIVED` | SELECTED · ARCHIVED |
| SELECTED | `VOIDED` (huỷ chọn) · `ARCHIVED` | QUEUED · ARCHIVED |
| REJECTED, ARCHIVED | *(không có — trạng thái cuối)* | — |

`VOIDED` đưa mã **về lại hàng chờ**. Dòng `SELECTED` đã bị huỷ **chỉ còn là dấu vết**: không còn chịu các phép
kiểm nội dung dành cho lần chọn (`TD-0119a/b`, `TD-0120`, luật 4.2), nhưng **vẫn được liệt kê** trong bằng chứng
của `TD-0120` để không ai phải đoán.

### 4.2. Trường nộp bất biến
`source`, `session_type`, `data_source`, `explore_evidence`, `title`, `mechanism`, `who_pays`, `durability`,
`phep_thu_du_kien`, `filter_verdict`, `overlaps_with`, `created_at` ở **mọi sự kiện sau dòng đầu** phải
**giống hệt dòng đầu**. `created_at` là thời điểm NỘP, không phải thời điểm của sự kiện.
**Muốn sửa ý tưởng thì nộp đơn mới** với `overlaps_with` trỏ mã cũ, rồi chọn đơn mới. Luật này chặn việc người
chọn nắn lại ý tưởng lúc chọn cho khớp tiêu chí.

### 4.3. Sự kiện `VOIDED` — fail-closed, chỉ ghi được khi đủ cả năm điều kiện
1. Trạng thái hiện hành là `SELECTED`.
2. **Không có trial nào** trong `trial_registry.jsonl` mang `hypothesis_slot` bằng mã đó, ở bất kỳ sự kiện nào.
   Một lần chọn đã tiêu ngân sách N thì không được huỷ để giấu.
3. Mỗi mã được huỷ **tối đa 1 lần** (cùng khuôn giới hạn `REFUND` của sổ trial), để chặn vòng chọn/huỷ/chọn.
4. `void_reason` trích mã một DR **có thật** trong `docs/decisions/`.
5. `voided_at` do máy đóng dấu.

Dòng `VOIDED` mang các trường nộp của dòng đầu (luật 4.2), `selected_at` của lần chọn bị huỷ (để chỉ đích danh),
và để `null` các trường cửa CHỌN còn lại.

### 4.4. Hạn ngạch
Số lần chọn **còn hiệu lực** có `selected_at` trong một quý phải **≤ `HAN_NGACH_CHON`** của file tiêu chí quý đó.
Luật này thay cho luật cũ chỉ kiểm "= 0". Lần chọn đã huỷ không được tính.

### 4.5. Thời điểm do máy đóng dấu
`selected_at` và `voided_at` do công cụ ghi từ đồng hồ UTC, **người không điền được**. Nếu tờ chọn tự điền
`selected_at` thì công cụ từ chối ghi. Đây là chỗ sửa thẳng nguyên nhân gốc của `MT-65`: một ngày chọn nằm trong
phiếu do người điền.

### 4.6. Công cụ
Cửa CHỌN và cửa HUỶ là hai cờ mới trên E6 (`trial_ledger_audit.py`), theo đúng khuôn `--nop-y-tuong`, và **không
thêm entrypoint** (L-Z36). Cả hai kiểm hết điều kiện **trước** khi mở file. Kiểm tra sổ có một phép kiểm mới canh
luật 4.1–4.3 để bắt cả dòng thêm tay, là lớp thứ hai bịt lỗ "sửa sổ bằng tay".

## 5. Áp cho IQ-0002
- Ghi một sự kiện `VOIDED` cho `IQ-0002` với lý do trích `DR-IQ-02` (`TD-0327`).
- Từ 01/10/2026: một phiên IDEA sạch **mới** chọn lại bằng công cụ cửa CHỌN. Bốn trường nộp giữ nguyên dòng
  QUEUED của `IQ-0002`. Các trường cửa CHỌN được lấy lại từ phiếu 18/09. Nếu muốn dùng bản nội dung đã viết lại
  trong phiếu 18/09, phải nộp đơn mới (`IQ-0003`, `overlaps_with: ["IQ-0002"]`) rồi chọn đơn đó.
- Luật 4.3 điều 3 nghĩa là **`IQ-0002` không còn lượt huỷ nào nữa**.

## 6. Không làm
- Không sửa, không xoá dòng `SELECTED` ngày 18/09.
- Không thêm danh sách miễn trừ nào vào phép kiểm.
- Không đổi cách `TD-0120` tra quý: vẫn tra theo `selected_at`.
- Chưa làm công cụ cho `ARCHIVED`, vì chưa có ca dùng. Bảng 4.1 đã định nghĩa sẵn sự kiện này để phép kiểm canh
  được dòng thêm tay.
