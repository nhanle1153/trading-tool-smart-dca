# DR-D0PRE-01 — Verify `zone_width_min_atr` có phải code chết (§3.3)

> Việc TD-0030, thứ tự bắt buộc (1) trong Khối 3 — **phải xong trước** TD-0031 (xác nhận DOF)
> và TD-0032 (chốt N_ĐĂNG_KÝ), vì kết quả ở đây đổi N (spec dòng 1070-1071: chết → 114, sống → 120).
>
> Nguồn: spec §3.3 (dòng 1031-1070) đã tự phân tích gần hết vấn đề và tự đề xuất kết luận
> ("🚪 ĐỀ XUẤT CHỐT"). Việc của DR này là xác minh lại lập luận đó bằng đại số, xác nhận không
> bỏ sót trường hợp nào, và **chốt chính thức** — spec chỉ mới "đề xuất", chưa "chốt".

## 1. Câu hỏi

Bộ lọc §3.3: `zone_width_pct ≥ 0.5 × ATR(14,4H)/price` có bao giờ **loại** một zone không, hay
nó luôn đúng (không tác dụng, "code chết")?

## 2. Zone width theo cấu trúc — không phải ước lượng, là đẳng thức

Theo §1.1 (dòng 697-700), zone hình thành tại nến swing thời điểm `i`:
```
buf = 0.3 × ATR(14,4H)/price  (tính TẠI i, "buf = 0.3 × ATR(14,4H)/price tại i")
Zone = [swing_price × (1 − buf), swing_price × (1 + buf)]
```
Suy ra trực tiếp, không có bước làm tròn/cắt nào khác được nhắc ở §1.1 hay §1b (kiểm tra: PHẦN 1b
chỉ có "4 quy tắc xử lý nhiều zone", không có quy tắc nào sửa lại biên zone đã hình thành):

```
zone_high − zone_low = swing_price × (1+buf) − swing_price × (1−buf) = swing_price × 2 × buf

zone_width_pct := (zone_high − zone_low) / swing_price = 2 × buf = 2 × 0.3 × ATR_i/price_i
                = 0.6 × ATR_i/price_i                                          (*)
```

`(*)` là **đẳng thức đúng cho MỌI zone**, không phải cận dưới ước lượng — không có cơ chế nào
trong spec làm zone hẹp lại sau khi hình thành.

## 3. Hai cách đọc "ATR ở thời điểm nào" cho vế ngưỡng — cả hai đều dẫn tới xoá

**Đọc (i) — ngưỡng dùng CÙNG một mốc ATR/price với `buf`** (tức ATR tại thời điểm hình thành
zone, hoặc tại bất kỳ thời điểm nào miễn là CÙNG mốc với vế trái):

```
Điều kiện lọc:  0.6 × (ATR/price)  ≥  0.5 × (ATR/price)
```
Với `ATR/price > 0` luôn dương (ATR là chỉ báo biến động, không âm; giá không âm), chia cả hai vế
cho `(ATR/price)`:
```
0.6 ≥ 0.5   —  ĐÚNG VỚI MỌI GIÁ TRỊ ATR/price
```
Đây là một **hằng đẳng thức**, không phải một điều kiện phụ thuộc dữ liệu. Bộ lọc **không bao giờ**
có thể trả về "zone quá hẹp" — nó luôn PASS. **CODE CHẾT theo nghĩa chặt nhất** (không phải "hiếm
khi kích hoạt", mà là "toán học không cho phép kích hoạt").

**Đọc (ii) — ngưỡng dùng ATR HIỆN TẠI (tại thời điểm đánh giá, có thể muộn hơn lúc hình thành
zone tới 40 nến 4H — §1.3 "tuổi zone ≤ 40 nến"), còn `buf` vẫn đóng băng ở ATR lúc hình thành**:

```
Điều kiện lọc:  0.6 × (ATR_hình_thành/price_hình_thành)  ≥  0.5 × (ATR_hiện_tại/price_hiện_tại)
```
Giờ bộ lọc CÓ THỂ kích hoạt — khi biến động đã **giãn ra đủ nhiều** kể từ lúc zone hình thành
(vế phải lớn lên). Nhưng khi đó bộ lọc không còn đo "zone này có hẹp bất thường không" — nó đo
**"biến động đã đổi bao nhiêu so với lúc hình thành"**, đúng bằng định nghĩa:
```
compression = ATR_hiện_tại / ATR_hình_thành      (§1.2, thành phần (c) của ZSS)
```
Tức đọc (ii) không tạo ra một bộ lọc "chống zone hẹp" độc lập — nó **trùng chức năng** với thành
phần `compression` đã có sẵn trong ZSS, chỉ khác tên gọi và ngưỡng cắt. Giữ nó là giữ hai cơ chế
đo cùng một thứ dưới hai tên khác nhau — vi phạm nguyên tắc đơn giản, và là đúng loại lỗi kế toán
DOF mà DR-010 tồn tại để chặn (một tín hiệu bị đếm hai lần dưới hai vỏ bọc khác nhau).

## 4. Hai lớp chặn thay thế đã tồn tại

Rủi ro thật mà bộ lọc này định giải quyết — "zone quá hẹp → notional suy ra vô lý lớn" (§3.2,
bảng ví dụ: zone hẹp 1.06% cho N_full/E lên tới 0.417) — đã có **hai lớp chặn độc lập khác**,
không phụ thuộc bộ lọc `zone_width_min_atr`:

1. **§6.4 — Gate đệm thanh lý:** chặn trực tiếp mọi trường hợp size lớn đẩy đòn bẩy hiệu dụng
   tới gần giá thanh lý, bất kể lý do gốc là gì (zone hẹp hay bất kỳ nguyên nhân nào khác).
2. **§6.8f — Kiểm tra kết nạp:** chặn theo trần margin danh mục tổng, không cho một vị thế đơn lẻ
   (dù zone hẹp hay rộng) vượt ngân sách vốn cho phép.

Hai lớp này đo **hậu quả** (size/margin/đệm thanh lý thực tế) thay vì đo **nguyên nhân** (zone hẹp
hay không) — mạnh hơn về logic (không thể bị "lách" bởi zone hẹp nhưng volatility thấp làm size
vẫn hợp lý), và đã tồn tại trong spec độc lập với bộ lọc đang xét.

## 5. Kết luận — CHẾT, XOÁ HẲN

Cả hai cách đọc hợp lý duy nhất của "ATR ở thời điểm nào" đều dẫn tới cùng một quyết định:

| Cách đọc | Kết quả | Lý do xoá |
|---|---|---|
| (i) Cùng mốc ATR/price | Không bao giờ kích hoạt (hằng đẳng thức 0.6≥0.5) | Toán học, không phụ thuộc dữ liệu |
| (ii) Ngưỡng dùng ATR hiện tại, buf đóng băng | Có thể kích hoạt, nhưng đo sai thứ (trùng compression) | Trùng chức năng ZSS, vi phạm đơn giản |

**Quyết định: XOÁ `zone_width_min_atr` HẲN khỏi `tool_d_config.yaml`, không để lại dạng comment**
(đúng chỉ dẫn spec dòng 1070 và MT-04 trong `back-end-note.md`: "comment còn đó là lời mời bật
lại mà không qua DR"). Rủi ro zone hẹp gây size vô lý được hai lớp chặn ở mục 4 xử lý, không có
khoảng trống nào bị bỏ ngỏ.

**Hệ quả trực tiếp cho TD-0031/TD-0032:** bộ lọc này CHẾT → `N_ĐĂNG_KÝ = 114` (không phải 120),
theo đúng bảng đối chiếu spec dòng 4423. Bảng DOF của DR-010 (TD-0031) phải khớp con số này khi
xác nhận lại từng dòng — nếu tổng không ra 114, đó là dấu hiệu TD-0031 tìm thấy một sai lệch kế
toán khác, không phải lý do quay lại xem xét quyết định của DR này.

## 6. Phạm vi KHÔNG thuộc DR này

- Không đánh giá lại bất kỳ ngưỡng `[CẦN CALIBRATE]` nào khác (`ZSS ≥ 0.5`, `v_min`...).
- Không sửa `w_a/w_b/w_c` hay các trọng số ZSS khác — nằm ngoài câu hỏi zone-width.
- Không phải backtest hay đo thực nghiệm — toàn bộ lập luận trên là **phân tích cấu trúc công
  thức**, đúng ranh giới D0-PRE (spec dòng 4464: cấm chạm dữ liệu trước khi D0-PRE xong).

## 7. Lịch sử

| Ngày | Sự kiện |
|---|---|
| 06/09/2026 | Tạo DR, kết luận CHẾT, áp dụng vào `tool_d_config.yaml` (TD-0030) |
