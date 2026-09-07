# DR-Q3-2026 — Tiêu chí chọn ý tưởng ra khỏi Idea Queue, quý 3/2026

> Giải **OQ-07**. §9c.7.4 bắt viết tiêu chí **TRƯỚC** khi mở hàng chờ và commit vào git;
> mở queue trước khi commit tiêu chí là **điều cấm** (spec dòng 4935).
> File này commit **RIÊNG và TRƯỚC** dòng `idea_queue.jsonl` đầu tiên.
> Chủ dự án chốt 07/09/2026.

**Phạm vi hiệu lực:** quý 3/2026 (01/07/2026 – 30/09/2026).
**Append-only:** sửa file này giữa quý **chỉ có hiệu lực từ quý sau**. Không có ngoại lệ —
tiêu chí sửa được giữa chừng thì không còn là "tiêu chí viết trước".

---

## 1. HẠN NGẠCH CHỌN QUÝ NÀY: 0

```
HAN_NGACH_CHON: 0
```

Không chọn ý tưởng nào ra khỏi hàng chờ trong quý 3/2026. Cửa **NỘP** vẫn mở (trần 10 đơn/quý).

**Vì sao 0 — ba ràng buộc cứng, không phải khẩu vị:**

1. **Tool D chưa có một lệnh thật nào.** Đang ở D2 trên đường D0→D12; live vốn nhỏ là D12.

2. **Cơ chế phát hiện "edge đã chết" CHƯA THỂ kích hoạt về mặt toán học.** §6.2 hệ số 5:
   `edge_ratio_D` tính trên **50 lệnh live gần nhất**; trước đủ 50 lệnh thì `mult_edge = 1.0`
   **theo định nghĩa**, không phải vì chưa đo. Tín hiệu "cần người thay thế" còn cách nhiều tháng.

3. **Lockbox có ĐÚNG MỘT và Zone Absorption chưa chạm.** Mỗi ứng viên mới cần lockbox trên dữ
   liệu **chưa từng dùng** (DR-011, DR-012 Hạng 2, §9c.7.5); dữ liệu sạch tích luỹ ~1 quý mỗi quý.
   Spec để ngỏ chính chuyện này ở câu hỏi mở #10: *"ứng viên thứ hai lấy lockbox ở đâu? […] Đây là
   trần cứng cho nhịp thay thế chiến lược."*

→ Chọn một ý tưởng lúc này = tiêu 1 suất Ngân sách A **+ đòi một lockbox chưa tồn tại**, để thay
một chiến lược **chưa ai biết có hỏng không**.

**Khai 0 không mất gì:** §9c.7.4 cho "chọn **tối đa** 1/quý", và cấm dồn slot / chọn bù —
nên không khai thì cũng không tích luỹ được gì để mất.

---

## 2. ĐIỀU KIỆN MỞ LẠI CỬA CHỌN — viết TRƯỚC, cần MỘT trong ba

```
MO_LAI_KHI:  (a) hoặc (b) hoặc (c)
```

| Mã | Điều kiện | Nguồn |
|---|---|---|
| **(a)** | `mult_edge = 0.5`, tức `edge_ratio_D < 0.5` trên 50 lệnh live gần nhất | §6.2 hệ số 5 |
| **(b)** | Một phán quyết **L2** (sai cấu trúc) hoặc **L3** (sai giả thuyết) | §11b.1 + DR-012 — cả hai đều đòi suất Ngân sách A + lockbox MỚI |
| **(c)** | **B3 cạn** (20/20) mà vẫn cần đổi tham số | DR-012 Hạng 2: *"hết ngân sách dự phòng → phải mở giả thuyết mới ở NGÂN SÁCH A và chạy lại chu trình từ đầu"* |

**Không cái nào xảy ra → quý sau MẶC ĐỊNH lại là 0.** Không phải quyết định lại, không phải bàn lại.

**Vì sao viết trước mới có tác dụng:** §9c.7.2 nói mục đích của hàng chờ là *"có sẵn quy trình khai
tử + thay thế […] thay vì phải nghĩ vội lúc đang thua"*. Lúc đang thua là lúc bạn **muốn** thay nhất
và **tệ nhất** trong việc quyết định thay. Ba điều kiện trên đều là sự kiện đọc được từ số, không
phải cảm giác.

---

## 3. TIÊU CHÍ XẾP HẠNG — THỨ TỰ TỪ ĐIỂN, không phải điểm có trọng số

Áp dụng khi cửa chọn mở lại. **TC-Q3-2026-01 quyết định trước; chỉ khi hoà mới xét tới 02**, và cứ thế.

### TC-Q3-2026-01 — Cơ chế độc lập với thanh khoản zone
Ý tưởng **không** dựa vào "dòng lệnh còn lại ở vùng giá cũ".
*Suy từ:* §6.2 edge decay + §9c.7.2. Một ứng viên chết **cùng lý do** với đương kim thì không phải
người thay thế — nó chỉ là cùng một cược viết bằng chữ khác.

### TC-Q3-2026-02 — Sức mạnh của câu "AI TRẢ TIỀN"
Không chỉ *trả lời được*, mà: người thua ở phía bên kia có bị **cấu trúc ép** phải tiếp tục thua
không (bắt buộc phòng hộ, bắt buộc thanh lý, bắt buộc theo chỉ số), hay chỉ là "có lẽ có ai đó thua".
*Suy từ:* §0.1 — bộ lọc rẻ nhất và là chỗ phần lớn ý tưởng LLM chết.

### TC-Q3-2026-03 — Bác bỏ được bằng ÍT dữ liệu
Tần suất tín hiệu cao hơn → cần đoạn lockbox ngắn hơn để kết luận.
*Suy từ:* ràng buộc ③ ở mục 1 — lockbox là tài nguyên khan hiếm nhất của cả dự án.

### TC-Q3-2026-04 — Dùng lại được hạ tầng đo đã có
1H chính, 4H/1D informative, 5m `timeframe_detail`, futures Binance, pool 102 mã.
*Suy từ:* chi phí. Ý tưởng cần dữ liệu tick / options / sàn khác đòi **cả một tầng đo mới**,
vượt xa 1 suất Ngân sách A.
**Xếp cuối là cố ý: rẻ không bao giờ được thắng đúng.**

---

## 4. Vì sao KHÔNG dùng điểm số có trọng số

Trọng số chính là **một bộ tham số**. Sau khi đã nhìn thấy các đơn trong hàng chờ, người chấm sẽ
chỉnh trọng số cho ra kết quả mình vốn đã thích — và **không ai đo được lần chỉnh đó**. Đúng thứ
§9c.7.4 gọi là *"bước CHỌN bị nhiễm, và nó VÔ HÌNH vì không ai ghi sổ cho bước chọn"*.

Thứ tự từ điển **không có núm nào để vặn**.

---

## 5. Phần máy kiểm được (TD-0120)

Spec tự thừa nhận ràng buộc *"`selection_reason` phải viết bằng cơ chế kinh tế"* **không thực thi
được bằng máy**. Nhưng một nửa thì được — cùng thủ thuật §12d dùng cho báo cáo định kỳ
(*"mọi câu phải trích một con số"*):

- `selection_reason` phải **trích ít nhất một mã `TC-Qx-yyyy-nn` có thật** trong file tiêu chí của
  **đúng quý** ghi ở `selected_at`. Không trích được → **từ chối**, tính là sổ bẩn.
- Quý khai `HAN_NGACH_CHON: 0` mà có dòng `SELECTED` → **sổ bẩn**.
- Quý chưa có file tiêu chí mà có dòng `SELECTED` → **sổ bẩn** (fail-closed — đúng điều cấm ở dòng 4935).

Máy vẫn **không** kiểm được nội dung câu đó có trung thực không. Nhưng nó chặn được ca dễ xảy ra
nhất: **chọn theo một tiêu chí mới nghĩ ra sau khi đã nhìn thấy các đơn**.
