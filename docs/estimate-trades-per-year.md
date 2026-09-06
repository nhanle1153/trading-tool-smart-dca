# Ước lượng số lệnh/năm bằng tính tay (TD-0081)

> Sàn yêu cầu bởi §10.2 (spec dòng 4274-4276): **≥150 lệnh/năm**, KHÔNG PHẢI trần. Đây là ước lượng
> **bằng suy luận**, không phải backtest thật (chưa có backtest nào chạy, đúng đúng nguyên tắc D0-PRE
> "cấm chạm dữ liệu"). Mọi số dưới đây là giả định có ghi rõ, không phải kết quả đo.

## 1. Đầu vào đã có thật (không phải giả định)

- Pool giao dịch: **102 mã** (TD-0083, `config/pool.yaml`, dữ liệu thật 06/09/2026).
- `enable_short: false` trong `tool_d_config.yaml` hiện tại — **CHỈ LONG được bật** cho tới khi DG7
  (funding stop) xong. Ước lượng dưới đây tính cho cấu hình HIỆN TẠI (long-only).
- Zone chỉ có 1 chiều tính (đáy cho LONG) khi short tắt.

## 2. Phễu ước lượng — từng bước, giả định ghi rõ

| Bước | Đại lượng | Giả định | Nguồn giả định |
|---|---|---|---|
| A | Số nến 4H/năm | 2.190 (365×6) | Số học |
| B | Ứng viên swing/mã/năm (k=3, §1.1) | **150–300** | Kinh nghiệm phân tích kỹ thuật: với cửa sổ xác nhận 3 nến mỗi bên (7 nến), thị trường crypto biến động vừa-cao cho pivot cứ ~7–15 nến lại xuất hiện 1 lần (một số là nhiễu). KHÔNG đo bằng dữ liệu thật Tool D — [CẦN CALIBRATE thật ở D1, H1-D] |
| C | Tỷ lệ qua ZSS ≥ 0.5 (§1.3) | **15–30%** | Ba thành phần ZSS (touch, volume_ratio, compression) đều là bộ lọc thật — không phải mọi swing đều "mạnh". Ngưỡng 0.5 chưa calibrate (chính nó là `[CẦN CALIBRATE]`) |
| D | Tỷ lệ còn "tươi" khi bị chạm (tuổi ≤40 nến, §1.3) | **70–90%** | Đa số swing được chạm lại trong vài ngày-tuần đầu nếu còn ý nghĩa; suy giảm theo thời gian |
| E | Tỷ lệ qua bộ lọc trend + DG1-DG6 (§2, §4 — "10 điều kiện nối AND", §0.3c) | **8–20%** | Đây là khâu lọc MẠNH NHẤT: đồng thuận 1D+4H, tuổi trend, ADX, xác nhận entry, đệm thanh lý — nhiều điều kiện độc lập nối AND. Không cộng dồn tuyến tính vì có tương quan giữa các điều kiện (VD trend rõ thường đi kèm ADX cao) — dùng khoảng rộng để phản ánh bất định |

## 3. Nhân phễu — long-only, 102 mã

```
Số lệnh/mã/năm = B × C × D × E

Cận DƯỚI (bi quan):  150 × 0.15 × 0.70 × 0.08  ≈  1.26 lệnh/mã/năm
Cận TRÊN (lạc quan):  300 × 0.30 × 0.90 × 0.20  ≈ 16.20 lệnh/mã/năm

Toàn pool (× 102 mã):
   Cận dưới:  1.26 × 102  ≈   129 lệnh/năm
   Cận trên: 16.20 × 102  ≈ 1.652 lệnh/năm
```

## 4. Kết luận

🔴 **Khoảng ước lượng (129–1.652 lệnh/năm) VẮT NGANG sàn 150** — không thể kết luận nhị phân dứt
khoát bằng suy luận tay với độ bất định lớn ở bước B/C/E (cả ba đều là `[CẦN CALIBRATE]` thật của
spec, chưa có số liệu). Cận dưới (129) **hụt sàn**; cận trên (1.652) vượt xa.

**Xử lý theo đúng tinh thần D0-PRE (không suy đoán, đo bằng dữ liệu thật khi có thể):**

1. **KHÔNG dừng dự án** — sàn 150 không phải điều kiện chặn D0-PRE, chỉ là điều kiện GATE ở D4
   (§10.2 Nhánh 1). Chưa tới lúc cần con số chính xác.
2. Đây là **rủi ro thiết kế đã biết**, ghi vào Open Questions (OQ-10 bên dưới) thay vì tự ý làm tròn
   thành "đạt" hay "hỏng" — làm vậy là đúng loại lỗi "bịa số khi chưa đo" mà PHẦN 0d cấm.
3. Số liệu THẬT đầu tiên sẽ có ở **D1** (H1-D pool point-in-time + zone detection thật chạy trên
   CALIB) — lúc đó ước lượng tay này được thay bằng số đo, không phải sửa lại phễu này.
4. Nếu tới D1 số đo thật cho thấy < 150 lệnh/năm rõ ràng, hai đòn bẩy đã sẵn có KHÔNG cần thiết kế
   lại: (a) bật `enable_short: true` sau khi DG7 xong (gần như GẤP ĐÔI cơ hội nếu long/short đối
   xứng), (b) pool đã có biên an toàn — 102 mã là kết quả của ngưỡng ĐỘC LẬP (DR-D0PRE-05), không
   phải trần cứng, có thể nới ngưỡng volume/tuổi nếu có lý do dữ liệu mới (qua DR mới, không tự ý).

## 5. Ghi vào Open Questions

| # | Câu hỏi mở | Ảnh hưởng | Mức độ |
|---|---|---|---|
| OQ-10 | Số lệnh/năm thật (sàn 150, §10.2) — ước lượng tay cho khoảng 129–1.652, vắt ngang sàn, không kết luận được | Không chặn D0-PRE. Chặn D4 nếu số đo thật ở D1 < 150 — khi đó cân nhắc bật `enable_short` hoặc nới ngưỡng pool | 🟡 Đo lại thật ở D1, không tự ý coi ước lượng tay là kết luận |
