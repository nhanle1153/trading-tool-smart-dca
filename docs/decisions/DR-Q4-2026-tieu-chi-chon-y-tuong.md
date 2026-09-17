# DR-Q4-2026 — Tiêu chí chọn ý tưởng ra khỏi Idea Queue, quý 4/2026

> Viết 17/09/2026, **TRƯỚC** khi quý 4 bắt đầu. Kế nhiệm `DR-Q3-2026`. Chủ dự án chốt 17/09/2026 qua
> **`DR-IQ-01`** (điều kiện (d)). File này commit RIÊNG và TRƯỚC mọi dòng `SELECTED` của quý 4.

**Phạm vi hiệu lực:** quý 4/2026 (01/10/2026 – 31/12/2026).
**Append-only:** sửa file này giữa quý **chỉ có hiệu lực từ quý sau**. Không có ngoại lệ.

---

## 1. HẠN NGẠCH CHỌN QUÝ NÀY: 1

```
HAN_NGACH_CHON: 1
```

**Vì sao 1 — điều kiện (d) của `DR-IQ-01` §3 đã thoả** (chủ dự án xác nhận tạm dừng tiêu suất Zone Absorption
LONG, 17/09/2026). Ba điều kiện `(a)(b)(c)` của `DR-Q3-2026` §2 **không** xảy ra; đây là suất (d), **đúng một lần**.
🔴 File này cố ý **không** ghi con số hay kết cục định lượng nào của Tool D — nó là tài liệu phiên CHỌN (phiên IDEA
sạch, DR-009) được phép đọc. **Phiên chọn KHÔNG đọc `DR-IQ-01` §0 và §2** (có số kết quả).

**Giới hạn của suất này** (`DR-IQ-01` §3, nhắc lại để người chọn đọc tại chỗ):
- **KHÔNG** dùng cho ý tưởng thuộc danh sách loại trừ **Z-1…Z-5** (`DR-IQ-01` §3.1) — gồm **IQ-0001** (Z-2).
  `selection_reason` phải khai *"không thuộc Z-1…Z-5"* và vì sao; nghi ngờ ⇒ coi như thuộc.
- **CHỌN do phiên IDEA sạch** (`DR-IQ-01` §3.2): chưa đọc kết quả Tool D; `selection_reason` không tham chiếu kết
  quả định lượng Tool D.
- Ý tưởng được chọn vẫn qua cửa CHỌN (MT-12), cần **lockbox MỚI**, đi đủ chu trình từ D0.
- Không dồn, không chọn bù: không chọn trong quý 4 thì suất này **không** chuyển sang quý sau.

⚠️ Máy TD-0120 chỉ đọc con số hạn ngạch; các giới hạn trên **không có máy kiểm** — người chọn phải trích
`DR-IQ-01` §3.1 trong `selection_reason`.

## 2. ĐIỀU KIỆN MỞ CỬA CHỌN CHO QUÝ SAU (quý 1/2027)

```
MO_LAI_KHI:  (a) hoặc (b) hoặc (c) hoặc (d)
```

Giữ nguyên `(a)(b)(c)` của `DR-Q3-2026` §2, cộng `(d)` của `DR-IQ-01` §3 — (d) chỉ thoả lại khi có một cổng sống
còn MỚI, viết trước, cho một ứng viên MỚI, ra luật 2 hoặc 4. **Không cái nào xảy ra → quý sau MẶC ĐỊNH là 0.**

---

## 3. TIÊU CHÍ XẾP HẠNG — THỨ TỰ TỪ ĐIỂN, không phải điểm có trọng số

Nội dung **chép nguyên** `DR-Q3-2026` §3 — chỉ đổi mã quý (máy TD-0120 đòi mã đúng quý của `selected_at`).
**TC-Q4-2026-01 quyết định trước; chỉ khi hoà mới xét tới 02**, và cứ thế.

### TC-Q4-2026-01 — Cơ chế độc lập với thanh khoản zone
Ý tưởng **không** dựa vào "dòng lệnh còn lại ở vùng giá cũ".
*Suy từ:* §6.2 edge decay + §9c.7.2. Một ứng viên chết **cùng lý do** với đương kim thì không phải
người thay thế — nó chỉ là cùng một cược viết bằng chữ khác.

### TC-Q4-2026-02 — Sức mạnh của câu "AI TRẢ TIỀN"
Không chỉ *trả lời được*, mà: người thua ở phía bên kia có bị **cấu trúc ép** phải tiếp tục thua
không (bắt buộc phòng hộ, bắt buộc thanh lý, bắt buộc theo chỉ số), hay chỉ là "có lẽ có ai đó thua".
*Suy từ:* §0.1 — bộ lọc rẻ nhất và là chỗ phần lớn ý tưởng LLM chết.

### TC-Q4-2026-03 — Bác bỏ được bằng ÍT dữ liệu
Tần suất tín hiệu cao hơn → cần đoạn lockbox ngắn hơn để kết luận.
*Suy từ:* lockbox là tài nguyên khan hiếm nhất của cả dự án (`DR-Q3-2026` §1 ràng buộc ③).

### TC-Q4-2026-04 — Dùng lại được hạ tầng đo đã có
1H chính, 4H/1D informative, 5m `timeframe_detail`, futures Binance, pool point-in-time (TD-0247).
*Suy từ:* chi phí. Ý tưởng cần dữ liệu tick / options / sàn khác đòi **cả một tầng đo mới**,
vượt xa 1 suất Ngân sách A.
**Xếp cuối là cố ý: rẻ không bao giờ được thắng đúng.**

---

## 4. Vì sao không dùng điểm có trọng số — và phần máy kiểm được

Giữ nguyên `DR-Q3-2026` §4 và §5 (không chép lại lập luận, một ý một nguồn): thứ tự từ điển không có núm để
vặn; `selection_reason` phải trích ít nhất một mã `TC-Q4-2026-nn` có thật trong file này; `SELECTED` trong quý
khai `HAN_NGACH_CHON: 0` hoặc quý không có file tiêu chí ⇒ sổ bẩn.
