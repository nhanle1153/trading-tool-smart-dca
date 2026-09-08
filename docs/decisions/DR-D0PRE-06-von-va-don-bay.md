# DR-D0PRE-06 — Chốt `E_D`, `L_exchange`, `rho_pct`, `daily_loss_budget_pct` (Tầng A, TD-0043)

> 🔴 **`E_D` ĐÃ ĐỔI 500 → 750 bằng `DR-D4-05` (09/09/2026). Đọc mục 3 dưới đây kèm đính chính này.**
> Mục 3 lập luận trên câu *"`E_D` = 500 → **102/102 mã qua**, nhưng sát sàn"* — câu đó **SAI**:
> đúng ra là **98/102**, và bốn mã BCH/ETC/LINK/LTC đã **VƯỢT** sàn chứ không phải "sát". Bảng cũ
> so cỡ lệnh tính bằng `rho` thô với `MIN_NOTIONAL` trần trụi, trong khi cỡ lệnh thật mang
> `Π mult_* ≤ 1` và sàn thật còn nhân hệ số dự trữ. Chi tiết: `docs/min-notional-check.md` §4.
>
> **Giữ nguyên chữ cũ làm lịch sử** — không sửa số trong mục 3, vì nó ghi lại *thứ chủ dự án đã
> nhìn thấy khi quyết*, và đó mới là thứ giải thích được vì sao 500 được chọn.


> OQ-02. Bốn con số Tầng A (§6.9.2) — chỉnh tự do, **0 trial**, không tính vào N_ĐĂNG_KÝ.
> Chủ dự án chốt ngày 06/09/2026 sau khi xem bảng đánh đổi đo trên dữ liệu thật của sàn.
> Viết TRƯỚC khi có bất kỳ backtest nào (D0-PRE, N2) — đúng yêu cầu spec dòng 4449.

## 1. Giá trị chốt

| Tham số | Giá trị | Nguồn quyết định |
|---|---|---|
| `E_D` | **500 USDT** | Chủ dự án chọn (= ví dụ minh hoạ của spec §6.8, §6.8f) |
| `L_exchange` | **3x** | Chủ dự án chọn (mặc định spec §6.9.5) |
| `rho_pct` | **0,375%** | Giữ nguyên spec §6.9.5 |
| `daily_loss_budget_pct` | **8,0%** | Giữ nguyên spec §6.9.5 — **đi cặp** với mức HALT 8% của thang drawdown (DR-D0PRE-04, §12c.5) |

Ràng buộc kèm theo (spec §6.8, §6.9.2): `E_D` **không phải số dư ví**. `tradable_balance_ratio`
trong `config/freqtrade/config.json` phải khớp tỉ lệ `E_D / số dư sub-account`. Với ví dụ spec
(ví 1.000, `E_D` 500) → 0,5. Nếu số dư sub-account thật khác 1.000 USDT, chủ dự án chỉnh
`tradable_balance_ratio` cho khớp — đó là chỉnh Tầng A, không cần DR mới, nhưng phải commit.

## 2. Điều spec đã quyết hộ — không phải chỗ để chọn

- Rủi ro mỗi lệnh = `rho × E_D` = **1,875 USDT**, cố định, **không phụ thuộc đòn bẩy** (D0.1, §6.8b).
- Trần margin = 0,85 × E_D = 425 USDT (điều kiện (b), §6.8f). `L_D_max` đã bị xoá (≡ 0,85 × L_exchange).
- Trần rủi ro một ngày xấu = 8% × 500 = 40 USDT = **21 lệnh thua cùng lúc** (giả định tương quan = 1).
- Số vị thế mở song song là **kết quả** của §6.8f (6–20 tuỳ độ rộng zone), không phải tham số.

## 3. Đánh đổi đã trình chủ dự án — đo trên dữ liệu thật (06/09/2026, 102 mã pool)

Nguồn: `GET /fapi/v1/exchangeInfo` (bộ lọc `MIN_NOTIONAL`, `LOT_SIZE`) + `GET /fapi/v1/ticker/price`,
gọi qua `src/tool_d/api_client/binance_public.py` và `urllib` (metadata, không phải "chạm dữ liệu" theo
DR-014 mục 2). Bảng đầy đủ ở `docs/min-notional-check.md` (TD-0082).

**Min notional:** 98 mã sàn 5 USDT, 4 mã sàn 20 USDT. Ở zone rộng nhất spec minh hoạ (R_eff = 3%),
tranche 1 = `rho × E_D / (3 × R_eff)` = 20,8 USDT với `E_D` = 500 → **102/102 mã qua**, nhưng sát sàn.

**Làm tròn lot (L-Z20, sai số kế hoạch ≤ 1% × rho × E_D):** sai số tối đa = 3 tranche × nửa bước lot
× khoảng cách tới SL. Số mã còn vào được lệnh:

| `E_D` | Zone rộng (R_eff 3%) | Zone trung bình (1,5%) | Zone hẹp (0,9%) |
|---|---|---|---|
| **500 (chốt)** | 82/102 | 91/102 | 94/102 |
| 1.000 | 91/102 | 94/102 | 98/102 |
| 2.000 | 94/102 | 98/102 | 98/102 |
| 5.000 | 98/102 | 101/102 | 102/102 |

Mã bị từ chối ở `E_D` = 500 là coin giá cao, bước lot thô (AAVE, AVAX, BNB, UNI, ICP, NEAR, CAKE…).
**Từ chối không mất tiền** — L-Z20 từ chối vào lệnh (spec dòng 2751-2754), không vào lệnh sai cỡ.
Hệ quả duy nhất: giảm số lệnh/năm, thứ đang vắt ngang sàn 150 (OQ-10).

**`L_exchange` 3x vs 5x:** đòn bẩy không đổi lỗ mỗi lệnh. Ở 3x đệm thanh lý ≈ 21,5× nên gate ≥ 8× gần
như không bao giờ từ chối (spec dòng 1897); 5x cho nhiều lệnh song song hơn nhưng loại nhiều zone hẹp,
và đổi sau này bắt buộc chạy lại phân bố `liq_buffer_ratio` trên CALIB (§6.9.2 ngoại lệ).

## 4. Khuyến nghị đã nêu và lựa chọn của chủ dự án

Tôi khuyến nghị `E_D` ≥ 1.000 (giữ được 91–98/102 mã). Chủ dự án chọn **500** — chấp nhận mất ~20%
pool ở zone rộng để giữ vốn thử nghiệm nhỏ. Đây là quyết định về vốn, thuộc chủ dự án. Ghi lại để
khi số lệnh/năm đo thật ở D1 hụt sàn 150, **nâng `E_D` là đòn bẩy đầu tiên** cần xem (cùng với bật
`enable_short` sau DG7 — xem `docs/estimate-trades-per-year.md`).

## 5. Hệ quả kiểm tra

- `config/tool_d_config.yaml` Tầng A giữ nguyên giá trị, gỡ nhãn `[CHỜ DR — OQ-02]`, trỏ về DR này.
- L-Z29 không đổi (Tầng A không nằm trong kiểm kê DOF) — chạy lại để xác nhận.
- Giả định cần xác minh khi tới D3.5/D10: biểu phí Binance USDⓈ-M theo bậc tài khoản thật
  (tài liệu này không dùng phí; DR-D0PRE-03 có dùng).
