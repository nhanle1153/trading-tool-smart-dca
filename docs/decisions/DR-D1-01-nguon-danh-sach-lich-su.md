# DR-D1-01 — Nguồn danh sách lịch sử symbol đã huỷ niêm yết (H1-D, TD-0095)

> TD-0095. Câu hỏi ban đầu (spec, §9c.4/H1-D): API `exchangeInfo` của Binance chỉ trả symbol
> ĐANG hoạt động — không có endpoint chính thức nào liệt kê symbol đã huỷ niêm yết trong quá khứ.
> Giả định mặc định của TASKS.md là "Không có nguồn → chấp nhận survivorship bias, ghi hướng lệch".
> **Kết luận của DR này: giả định đó SAI. Có nguồn thật, miễn phí, và đã kiểm chứng được — không
> chấp nhận bias.**

## 1. Nguồn tìm được: `data.binance.vision`

Đây là kho lưu trữ tĩnh công khai của chính Binance (không phải REST API giao dịch), chứa file
nến lịch sử OHLCV theo ngày, tổ chức theo thư mục `data/futures/um/daily/klines/<SYMBOL>/<khung>/`.
Khác với `exchangeInfo` (chỉ phản ánh trạng thái HIỆN TẠI), kho này **không xoá thư mục của symbol
đã huỷ niêm yết** — file lịch sử vẫn còn nguyên vẹn vĩnh viễn.

**Đã gọi thật** (`GET https://s3-ap-northeast-1.amazonaws.com/data.binance.vision/` — bucket S3
đứng sau `data.binance.vision`, dùng tham số `prefix`/`delimiter`/`marker` chuẩn S3 ListObjects,
phân trang qua `NextMarker` vì mỗi trang giới hạn 1000 mục):

- Tổng **1.027 thư mục symbol** từng tồn tại trong `futures/um/daily/klines/` (mọi thời điểm).
- Loại 51 thư mục hợp đồng KỲ HẠN (tên có `_YYMMDD`, ví dụ `BTCUSDT_210326`) — Tool D chỉ giao dịch
  PERPETUAL, không giao dịch kỳ hạn.
- Loại 103 thư mục không phải cặp quote USDT (USDC-margined, BUSD cũ, v.v.) — pool Tool D chỉ nhận
  quote USDT (`config/pool.yaml`).
- Còn lại **874 thư mục ứng viên perpetual/USDT**.

Đối chiếu với `exchangeInfo` THẬT gọi cùng thời điểm (`GET /fapi/v1/exchangeInfo`, lọc
`quoteAsset=USDT` + `contractType=PERPETUAL`): **658 symbol đang có trên sàn** (528 `TRADING`,
129 `SETTLING` — đang đóng dần nhưng CHƯA gỡ hẳn, không tính là đã huỷ; 1 `PENDING_TRADING`).

**874 (archive) − 658 (đang có, mọi trạng thái) = 219 symbol perpetual/USDT đã thật sự biến mất
khỏi `exchangeInfo` nhưng còn dấu vết trong kho lưu trữ** — đây chính là danh sách "đã huỷ niêm
yết" mà H1-D cần. Ví dụ: `BTTUSDT`, `BTSUSDT`, `BZRXUSDT`, `AUDIOUSDT`, cùng một nhóm token cổ
phiếu hoá (`AAPLUSDT`, `AMZNUSDT`, `TSLA`-nhóm...) mà Binance từng thử nghiệm rồi rút.

## 2. Xác nhận kho lưu trữ cho ra được MỐC NGÀY thật, không chỉ tên symbol

Kiểm một symbol đã huỷ (`BTTUSDT`, khung 1h) bằng đúng cơ chế ListObjects (không đoán):

```
data/futures/um/daily/klines/BTTUSDT/1h/BTTUSDT-1h-2021-04-06.zip   ← file ĐẦU
data/futures/um/daily/klines/BTTUSDT/1h/BTTUSDT-1h-2022-01-26.zip   ← file CUỐI
```

Tức `BTTUSDT` tồn tại trên futures từ 06/04/2021 đến 26/01/2022 rồi huỷ niêm yết — một mốc NGÀY CỤ
THỂ đo được, không phải suy đoán. Cơ chế này áp dụng được cho toàn bộ 219 symbol: liệt kê thư mục
`<SYMBOL>/1d/` của từng symbol, lấy tên file đầu/cuối là ngày lên sàn/rời sàn thật.

## 3. Hệ quả cho TD-0096 (`pairlist_point_in_time(t)`)

**Không mở DR chấp nhận survivorship bias.** TD-0096 phải nạp thêm 219 symbol này (cùng khoảng
tồn tại đo được ở mục 2) vào tập ứng viên khi tính pool tại mốc `t` lùi về quá khứ — nếu không, mọi
mốc `t` trước ngày một symbol bị huỷ sẽ thiếu đúng những mã lẽ ra phải có mặt, làm pool tại quá khứ
trông "sạch" hơn thực tế (đúng chiều lệch mà H1-D được sinh ra để chặn).

**Giới hạn thẳng thắn của nguồn này** (ghi để không ai tưởng nó hoàn hảo):
- Đây là nguồn **cộng đồng/kho tĩnh của Binance**, không phải endpoint tài liệu chính thức có SLA —
  rủi ro tồn dư: kho có thể ngừng cập nhật hoặc đổi cấu trúc trong tương lai. Chấp nhận được vì kho
  đã hoạt động ổn định nhiều năm và được chính cộng đồng `python-binance`/`freqtrade` dùng làm
  nguồn tải dữ liệu chuẩn.
- Chỉ cho biết symbol tồn tại trong khoảng nào — KHÔNG cho biết volume/OI lịch sử trực tiếp qua
  phép liệt kê thư mục (muốn có volume phải tải file nến thật, việc đó thuộc TD-0096, không phải
  TD-0095 — TD-0095 chỉ khảo sát NGUỒN).
- 219 là con số ứng viên tại một lát cắt thời gian (hôm nay); một vài symbol trong nhóm `SETTLING`
  hiện tại (129) rồi cũng sẽ rơi vào nhóm này khi Binance gỡ hẳn — không tính vào 219 vì tại thời
  điểm đo chúng chưa huỷ.

## 4. Việc còn lại

Danh sách 219 symbol thô lưu tạm ở scratchpad phiên làm việc — TD-0096 khi triển khai
`pairlist_point_in_time(t)` phải tự gọi lại quy trình ở mục 1-2 (không hard-code danh sách vào
code, vì danh sách này còn tăng theo thời gian — mỗi lần chạy thật phải đo lại, không dùng bản ghi
cũ, đúng tinh thần H19/LD-28 "không tin số cũ khi nguồn có thể đã đổi").
