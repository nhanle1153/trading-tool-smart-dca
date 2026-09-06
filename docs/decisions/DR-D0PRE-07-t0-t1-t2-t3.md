# DR-D0PRE-07 — Mốc chia CALIB / WFO / LOCKBOX (DR-011, TD-0084, OQ-05)

> Chốt bằng NGÀY CỤ THỂ, TRƯỚC khi chạy bất kỳ backtest nào trên dữ liệu này (spec dòng 3279-3280).
> Chủ dự án xác nhận ngày 06/09/2026 sau khi xem phân tích trên giá BTC futures thật (không phải
> "đánh giá cấu hình" theo MT-02 — đây là phép đo chế độ thị trường, không chạy chiến lược nào).

## 1. Mốc chốt

| Mốc | Ngày | Ý nghĩa |
|---|---|---|
| T0 | **09/04/2024** | Bắt đầu CALIB |
| T1 | **12/06/2025** | CALIB → WFO |
| T2 | **29/01/2026** | WFO → LOCKBOX |
| T3 | **06/09/2026** | Ngày niêm phong (hôm nay) |

| Đoạn | Khoảng | Độ dài | % tổng |
|---|---|---|---|
| CALIB [T0…T1] | 09/04/2024 → 12/06/2025 | 429 ngày | 49% |
| WFO [T1…T2] | 12/06/2025 → 29/01/2026 | 231 ngày | 26% |
| LOCKBOX [T2…T3] | 29/01/2026 → 06/09/2026 | 220 ngày | 25% |
| **Tổng [T0…T3]** | | **880 ngày (2,41 năm)** | 100% |

## 2. Vì sao T2 = 29/01/2026 — chế độ thị trường thật, không phải ngày chọn tuỳ ý

Nguồn: `GET /fapi/v1/klines` (BTCUSDT futures, 1d), gọi qua `src/tool_d/api_client/binance_public.py`
(hàm `get_klines`, thêm ở DR này) — phép đo chế độ thị trường trên BTC, KHÔNG phải đánh giá cấu hình
chiến lược nào (MT-02: không tính là "chạm dữ liệu").

```
Đỉnh toàn kỳ (1000 ngày gần nhất): $124.628  ngày 06/10/2025
Từ đỉnh, BTC điều chỉnh dao động -23% đến -32% suốt 10/2025-01/2026 (chưa ổn định)
Từ 29/01/2026: drawdown LIÊN TỤC ≤ -30% cho tới hôm nay (06/09/2026) — KHÔNG hồi phục lại
              trên -30% một lần nào trong suốt 220 ngày. Đỉnh sập: -53,0% (30/06/2026).
```

So sánh định lượng ba đoạn (spec §DR-011 điều kiện (b) đòi "≥1 chế độ thị trường khác biệt rõ rệt"):

| Đoạn | Drawdown trung bình | Drawdown sâu nhất | Giá đầu → cuối |
|---|---|---|---|
| CALIB | −11,1% | −28,1% | 69.189 → 108.600 |
| WFO | −13,7% | −32,0% | 105.610 → 89.262 |
| **LOCKBOX** | **−43,9%** | **−53,0%** | 84.605 → 79.610 |

Drawdown trung bình LOCKBOX gấp ~4 lần CALIB/WFO — đây là một chế độ sập kéo dài, khác hẳn giai đoạn
tăng-có-điều-chỉnh trước đó. Thoả điều kiện (b) bằng dữ liệu thật, không phải suy đoán trên giấy.

## 3. Bốn điều kiện chất lượng LOCKBOX (DR-011)

| Điều kiện | Yêu cầu | Kết quả |
|---|---|---|
| (a) Độ dài ≥ 20% tổng dữ liệu | ≥20% | **25%** — có biên trên sàn, không sát mép |
| (b) ≥1 chế độ thị trường khác biệt | rõ rệt | ✅ mục 2 — sập kéo dài −53%, gấp ~4× drawdown trung bình hai đoạn kia |
| (c) ≥30 lệnh dự kiến cho cấu hình tốt nhất | ≥30 | Ước lượng bằng phễu TD-0081/OQ-10 (129–1.652 lệnh/năm, 102 mã, long-only) quy ra 220 ngày: **78–996 lệnh**. Cận dưới đã dư margin so với sàn 30. **Vẫn là ước lượng tay, chưa phải số đo** — như OQ-10 đã ghi, số đo thật chỉ có ở D1 |
| (d) LOCKBOX là đoạn gần hiện tại nhất | T3 = ngày niêm phong | ✅ T3 = 06/09/2026 = hôm nay |

## 4. Độ phủ pool tại T0 — chấp nhận tăng dần, không phải lỗi thiết kế

Tại T0 (09/04/2024), chỉ **56/102 mã** trong pool đã tồn tại (tuổi niêm yết tính tới hôm nay ≥ 880
ngày). 46 mã còn lại lên sàn dần trong suốt CALIB/WFO. Đây **không phải khiếm khuyết của mốc chọn**:
LOCKBOX (đoạn quyết định GATE D0.9) luôn có **đủ 102/102 mã** vì T3 = hôm nay, theo đúng cấu trúc của
DR-011 (LOCKBOX là đoạn gần nhất). Việc CALIB dùng ít mã hơn ở giai đoạn đầu, nhiều mã hơn dần về sau
là đúng bản chất "point-in-time" mà H1-D (chưa xây, việc riêng của D1, đã ghi ở checklist H16-H18) sẽ
xử lý đúng cách khi build backtest thật — mốc ngày ở DR này không phụ thuộc vào H1-D đã xong hay chưa.

## 5. Phương án đã trình và lý do không chọn

| Phương án | Tỷ lệ LOCKBOX | Lý do không chọn |
|---|---|---|
| T0 = 02/09/2023 | 20% (đúng sàn) | Không có biên an toàn trên sàn tối thiểu spec — rủi ro nếu tính lại lệch nhỏ. Chỉ 43/102 mã tồn tại lúc T0 |
| **T0 = 09/04/2024 (chốt)** | **25%** | Biên an toàn hợp lý trên sàn 20%, 56/102 mã đã tồn tại, CALIB vẫn đủ dài (429 ngày) |
| T0 = 03/09/2024 | 30% | Biên an toàn lớn nhất, nhưng CALIB ngắn hơn (333 ngày) — đánh đổi không cần thiết khi 25% đã đủ margin |

Chủ dự án chọn **25%**.

## 6. Cơ chế niêm phong (thực thi ngay sau DR này)

Theo mục "CƠ CHẾ NIÊM PHONG" của DR-011 (spec dòng 3305-3320):

1. Dữ liệu LOCKBOX (OHLCV 1h/4h/1d + mark/funding_rate 1h, futures, 102 mã, khoảng [T2,T3]) tải bằng
   `freqtrade download-data` qua service `lockbox` (docker-compose — service DUY NHẤT thấy thật
   `lockbox/data/`, không bị volume ẩn danh che), lưu vào `lockbox/data/futures/`.
2. Hash SHA-256 toàn bộ file bằng `src/tool_d/lockbox/seal.py:build_seal()` (đã có từ TD-0070).
3. Ghi `lockbox/lockbox_seal_1.json` bằng `write_seal()` — từ chối ghi đè nếu đã tồn tại.
4. Từ thời điểm này, dữ liệu LOCKBOX coi như đã niêm phong. **CHƯA coi là đã "chạm"** (DR-014 mục 2:
   chạm = đánh giá cấu hình) — chạm thật là D9, ngoài phạm vi D0-PRE. Quy tắc quyết định trên lockbox
   (chọn đúng MỘT cấu hình từ WFO, điền ngưỡng PASS cho từng hướng) là tài liệu RIÊNG, viết TRƯỚC lần
   chạm duy nhất ở D9 — không viết ở đây vì WFO chưa chạy, chưa có cấu hình nào để đặt tên.

## 7. Giả định cần biết khi tới D1

- CALIB/WFO không tự động có đủ 102 mã — cách nạp đúng theo tuổi niêm yết từng mã là việc của H1-D
  (point-in-time pairlist), chưa xây ở D0-PRE, đã flag ở checklist H16-H18 của spec.
- Ước lượng lệnh trong mục 3(c) dùng lại phễu OQ-10 (đã có sai số lớn, tự thừa nhận từ TD-0081) —
  không phải cam kết con số thật; nếu D1 đo ra ít lệnh bất ngờ trong LOCKBOX, đó là dữ liệu mới, không
  phải lý do mở lại DR này (mốc ngày là bất biến sau niêm phong).
