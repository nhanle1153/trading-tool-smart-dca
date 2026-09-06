# Đối chiếu min notional + độ thô bước lot của pool (TD-0082)

> Spec dòng 2751-2754: L-Z20 khẳng định lúc entry `|tổng thang − rho_eff × E_D| ≤ 1% × rho_eff × E_D`,
> vi phạm → **từ chối vào lệnh**, "nối vào kiểm min-notional ở D0-PRE". Bảng này là phép kiểm đó,
> chạy trên metadata thật của sàn (không phải "chạm dữ liệu" theo DR-014 mục 2, 0 trial).
>
> Lệnh sinh bảng (chạy trong Docker, 06/09/2026):
> `docker compose -f docker/docker-compose.yml run --rm freqtrade entrypoints/build_pool.py --check-min-notional`
> Logic thuần: `src/tool_d/notional.py` (test `tests/unit/test_notional.py`).

## 1. Đầu vào

- Pool: **102 mã** (`config/pool.yaml`, TD-0083).
- `E_D` = 500, `rho` = 0,375%, `n_tranches` = 3 → rủi ro/lệnh **1,875 USDT**, dung sai L-Z20 = 1% = **0,01875 USDT** (DR-D0PRE-06).
- Bộ lọc sàn: `MIN_NOTIONAL.notional`, `LOT_SIZE.stepSize` (`GET /fapi/v1/exchangeInfo`), giá `GET /fapi/v1/ticker/price`.
- Ba độ rộng zone spec minh hoạ ở §6.8f: 3% (rộng — notional NHỎ NHẤT, ca xấu nhất cho min notional), 1,5%, 0,9%.

## 2. Kết quả

| R_eff | Tranche 1 (USDT) | Qua min notional | Qua L-Z20 (làm tròn lot ≤ 1%) |
|---|---|---|---|
| 3,0% | 20,8 | **102/102** | 81/102 |
| 1,5% | 41,7 | **102/102** | 91/102 |
| 0,9% | 69,4 | **102/102** | 94/102 |

Phân bố sàn min notional: 98 mã **5 USDT**, 4 mã **20 USDT**. Ở ca xấu nhất tranche 1 = 20,8 USDT vẫn
qua cả 4 mã sàn 20 — nhưng **sát sàn**: `E_D` < 480 sẽ làm 4 mã đó rớt.

Mã rớt L-Z20 (bước lot × giá quá thô so với ngân sách rủi ro 1,875 USDT):

| R_eff | Số mã | Danh sách |
|---|---|---|
| 3,0% | 21 | AAVE, ASTER, AVAX, BNB, CAKE, HYPE, ICP, INJ, JTO, LDO, LIT, NEAR, PENDLE, PROM, SOL, UAI, UNI, XMR, ZEC, ZEN, 币安人生 |
| 1,5% | 11 | AAVE, AVAX, BNB, CAKE, HYPE, ICP, NEAR, PENDLE, SOL, UNI, ZEC |
| 0,9% | 8 | AAVE, AVAX, BNB, CAKE, ICP, NEAR, PENDLE, UNI |

## 3. Kết luận theo tiêu chí nghiệm thu của TD-0082

**Min notional: KHÔNG có vi phạm** → không cần nâng `E_D`, không cần đặt sàn, không cần DR mới cho
tiêu chí này.

**L-Z20 (làm tròn lot): có 8–21 mã (tuỳ độ rộng zone) sẽ bị hệ thống TỪ CHỐI vào lệnh** — đúng cơ chế
spec quy định, không phải lỗi. Đây là hệ quả đã được trình và chủ dự án chấp nhận khi chọn `E_D` = 500
(DR-D0PRE-06 mục 4). Không sửa gì ở D0-PRE. Ghi nhận hai điểm cho D1:

1. Khi H1-D dựng pairlist point-in-time, **không loại trước** các mã này khỏi pool — L-Z20 từ chối theo
   từng zone cụ thể (R_eff thật), không phải theo mã; ở zone hẹp nhiều mã trong danh sách vẫn vào được.
2. Nếu số lệnh/năm đo thật ở D1 hụt sàn 150 (OQ-10), nâng `E_D` là đòn bẩy đầu tiên: bảng ở
   DR-D0PRE-06 mục 3 cho thấy 1.000 USDT lấy lại ~10 mã ở zone rộng.

**Giả định của phép kiểm:** sai số làm tròn tối đa = 3 tranche × nửa bước lot × khoảng cách tới SL,
cùng chiều. Bộ đặt lệnh thật (D1) có thể làm tròn tranche cuối theo chiều bù để tổng khớp ngân sách —
khi đó số mã rớt sẽ **ít hơn** bảng này. Bảng này là cận trên bi quan, chủ ý.
