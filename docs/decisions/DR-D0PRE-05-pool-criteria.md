# DR-D0PRE-05 — Chốt tiêu chí pool giao dịch (§0.3, TD-0083)

> TD-0083. Tiêu ngân sách **4 trial B0** (DR-010: "1 trial/tiêu chí, KHÔNG tune"). Đây là quyết
> định MỘT LẦN — không được chọn lại sau khi thấy overlap với Tool A cao/thấp (spec dòng 350-352).

## 1. 🔴 Kỷ luật bắt buộc: tiêu chí là hàng rào cứng, không suy ngược từ số lượng

Spec cảnh báo tường minh (dòng 385-387): *"Không ép cho đủ 100. Pool = số mã vượt tiêu chí, có thể
73 hay 88."* Bốn ngưỡng dưới đây được chọn **độc lập theo lý do chất lượng dữ liệu của từng tiêu
chí** — việc kết quả cuối cùng ra gần đúng `pool_size_target: 100` (đã có sẵn trong
`tool_d_config.yaml` từ TD-0013) là **trùng hợp xác nhận thêm**, KHÔNG PHẢI cách tôi chọn ra hai con
số này. Ghi rõ ở đây để không ai (kể cả chính tôi ở vòng sau) đọc ngược thành "chọn ngưỡng để ra
100".

## 2. Bốn tiêu chí (i)-(iv), spec dòng 318-329

### (i) Volume 24h ≥ 15.000.000 USDT

**Lý do độc lập:** tiêu chí (i) đòi volume đủ lớn để `volume_ratio` (thành phần (b) của ZSS, §1.2 —
`volume(nến swing) / volume_MA(20,4H)`) phản ánh tín hiệu thật, không phải nhiễu thống kê. Ở mức
volume thấp, một vài lệnh lớn đơn lẻ có thể làm `volume_ratio` nhảy vọt không liên quan gì đến hấp
thụ thật. 15 triệu USDT/ngày là mức thanh khoản đủ sâu để dao động ngày-qua-ngày không bị chi phối
bởi một vài lệnh cá biệt — đồng thời đủ chặt để loại các mã đuôi dài (rank >150 trong 528 hợp đồng
đang giao dịch, dữ liệu thật lấy 06/09/2026) có sổ lệnh mỏng, spread rộng, không phù hợp lệnh
post-only maker (gián tiếp thoả luôn tiêu chí (iii), xem mục 3).

### (ii) Tuổi niêm yết ≥ 180 ngày (6 tháng)

**Lý do độc lập:** tiêu chí (ii) đòi đủ lịch sử giao dịch để zone có cơ hội được "touch" trước khi
hết hạn, và — quan trọng hơn — để bản thân quá trình CALIB/WFO (nhiều tháng dữ liệu, chưa chốt mốc
chính xác ở TD-0084) có đủ lịch sử LIÊN TỤC mà không bị đứt gãy do mã mới lên sàn. 180 ngày là sàn
tối thiểu để một mã có ít nhất nửa năm dữ liệu trước khi bất kỳ cửa sổ CALIB nào bắt đầu — loại các
mã mới niêm yết đang trong giai đoạn biến động bất thường (pump/dump sau niêm yết), đúng tinh thần
"tránh khai thác dữ liệu nhiễu" mà (ii) hướng tới.

### (iii) Cost economics lệnh post-only — KHÔNG cần ngưỡng lọc riêng

**Kết luận:** đây là thuộc tính CỦA SÀN (cấu trúc phí maker theo tier tài khoản, §3.5 dòng 324-327),
áp dụng ĐỒNG NHẤT cho mọi mã trên Binance USDⓈ-M — không phải thuộc tính riêng của từng symbol có
thể lọc bằng ngưỡng. Rủi ro thật của (iii) (spread rộng làm lệnh post-only khó khớp) đã được chặn
GIÁN TIẾP bởi ngưỡng volume (i) — thanh khoản sâu tự nhiên đi kèm spread hẹp hơn. Không thêm bậc tự
do mới cho tiêu chí này (đúng nguyên tắc "không thêm tham số khi chưa có bằng chứng cần thiết").

### (iv) Khoảng cách zone đối diện cho TP có nghĩa — KHÔNG cần ngưỡng lọc pool tĩnh

**Kết luận:** đây là kiểm tra TẠI THỜI ĐIỂM VÀO LỆNH (mỗi zone cụ thể, tại mỗi thời điểm cụ thể),
không phải thuộc tính tĩnh của một mã để lọc trước ở tầng pool. Logic TP (§5.1) tự chịu trách nhiệm
từ chối setup không tìm được zone đối diện hợp lý — không cần nhân đôi kiểm tra này ở tầng chọn pool.

## 3. Kết quả áp dụng trên dữ liệu thật (06/09/2026)

Gọi `GET /fapi/v1/exchangeInfo` + `GET /fapi/v1/ticker/24hr` (qua `api_client.binance_public`,
TD-0079/0080 hạ tầng có sẵn) — **528 hợp đồng PERPETUAL/USDT đang TRADING**.

| Ngưỡng tuổi | Còn lại (đã loại BTC/ETH) | Volume tại hạng-100 |
|---|---|---|
| ≥90 ngày | 514 | 17.100.000 USDT |
| **≥180 ngày (chọn)** | 496 | **15.500.000 USDT** |
| ≥270 ngày | 465 | 14.600.000 USDT |
| ≥365 ngày | 399 | 10.800.000 USDT |

Áp đúng (180 ngày, 15.000.000 USDT) → kết quả thật ghi trong `config/pool.yaml` (sinh bởi E7,
`entrypoints/build_pool.py --commit`, TD-0083). Số lượng cuối cùng **không được chỉnh lại** dù khác
100 — đúng kỷ luật mục 1.

## 4. BTC/ETH và tập EXPLORE

- BTCUSDT, ETHUSDT: loại khỏi pool GIAO DỊCH theo quyết định vận hành cố định của spec (§0.3b, dòng
  360-361) — KHÔNG áp dụng tiêu chí (i)-(iv) cho chúng (chúng luôn thoả, thanh khoản cao nhất sàn;
  lý do loại là cơ chế thị trường hiệu quả nhất, không phải điểm dữ liệu). Dữ liệu của chúng vẫn tải
  và giữ (spec dòng 371-376) — chúng là xương sống của tập EXPLORE.
- Tập EXPLORE (§9c.4b) = BTC + ETH + mọi mã KHÔNG thoả tiêu chí (i)/(ii). Dùng để SINH giả thuyết, 0
  trial. 🔴 Ràng buộc cứng: một mã đã vào EXPLORE **không bao giờ** được chuyển sang pool giao dịch
  sau này, kể cả khi sau đó nó thoả tiêu chí — không có ngoại lệ (spec dòng 3826-3828).

## 5. Ngân sách tiêu

4 trial B0, mỗi trial ứng với một tiêu chí (contribution=1/trial):

| Trial | Tiêu chí | Kết luận |
|---|---|---|
| B0-1 | (i) Volume | Ngưỡng 15.000.000 USDT/ngày |
| B0-2 | (ii) Tuổi niêm yết | Ngưỡng 180 ngày |
| B0-3 | (iii) Cost economics | Không cần ngưỡng riêng — thoả gián tiếp qua (i) |
| B0-4 | (iv) Khoảng cách TP | Không cần ngưỡng pool tĩnh — kiểm tại thời điểm vào lệnh |

## 6. Lịch sử

| Ngày | Sự kiện |
|---|---|
| 06/09/2026 | Chốt 4 tiêu chí, chủ dự án xác nhận (i)=15tr USDT, (ii)=180 ngày sau khi xem phân tích dữ liệu thật |
