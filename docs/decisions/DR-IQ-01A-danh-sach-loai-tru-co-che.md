# DR-IQ-01A — Danh sách loại trừ cơ chế cho suất (d) — NGUỒN DUY NHẤT

> Phụ lục của `DR-IQ-01` (§3.1), tách ra 17/09/2026 theo phản biện phiên `-30`: phiên CHỌN sạch (DR-009) phải
> phán được một ý tưởng *"có thuộc Z-1…Z-5 không"* mà **không phải mở file có số kết quả**.
> 🔴 **File này KHÔNG chứa và KHÔNG được thêm** bất kỳ con số, kết cục hay tham chiếu kết quả định lượng nào của
> Tool D. Phiên CHỌN chỉ cần đọc file này + `DR-Q4-2026-tieu-chi-chon-y-tuong.md` + sổ `idea_queue.jsonl`.

---

## Vì sao cần danh sách viết trước

Suất (d) sinh ra để **THAY** ứng viên hiện tại (Zone Absorption), không để thử lại chính nó. Phép chặn đổi tên có sẵn
(`idea_queue.tim_nghi_trung`, so từ trên `mechanism`) chỉ so với **các đơn trong sổ** — mà Zone Absorption là giả
thuyết gốc trong spec, **không phải một đơn**, nên phép so đó không nhìn thấy nó. Danh sách dưới đây thay phép so chữ.

## Danh sách

Suất (d) **KHÔNG** được dùng cho ý tưởng mà cơ chế sinh lời thuộc BẤT KỲ mục nào:

| # | Họ cơ chế bị loại | Ví dụ viết bằng chữ khác |
|---|---|---|
| Z-1 | Phản ứng giá / hấp thụ thanh khoản tại vùng cung-cầu dựng từ swing | "hồi quy trung bình tại vùng thanh khoản", "đáy cấu trúc có lệnh chờ" |
| Z-2 | Vào nhiều lần / trung bình giá trong hoặc quanh vùng đó | **IQ-0001** (Smart DCA ba tranche neo zone) |
| Z-3 | Xác nhận vào lệnh tại vùng (nến rút chân, phân kỳ RSI, volume) | "entry có xác nhận tại vùng hỗ trợ" |
| Z-4 | Cấu trúc chốt lời/cắt lỗ neo vùng đối diện, hoặc bội số R của một thiết lập vùng | "sửa tỉ lệ lời/lỗ của chiến lược vùng" |
| Z-5 | Mọi thay đổi tham số, bộ lọc, khung thời gian của `ZoneAbsorption` | "Z0-T1 với ngưỡng ZSS khác" |

## Luật áp dụng

- `selection_reason` phải khai tường minh *"không thuộc Z-1…Z-5"* và vì sao; thiếu câu đó thì người duyệt coi như thuộc.
- Nghi ngờ thuộc hay không ⇒ **coi như thuộc** (fail-closed).
- ⚠️ **Không có máy canh danh sách này.** Cửa CHỌN (TD-0120) chỉ kiểm `selection_reason` trích mã `TC-Qx-yyyy-nn` có
  thật. Một máy chỉ kiểm được lời khai *có mặt*, không kiểm được nó *đúng* — phán xét cuối là người. Đừng coi danh
  sách này được canh như cửa B1 của sổ trial.
- Sửa danh sách: DR mới, commit **trước** khi nhìn các đơn nộp trong quý áp dụng.
