# DR-D0PRE-03 — Điền ngưỡng `DSR-adjusted expectancy` Nhánh 1 §10.2 (blocker B6, TD-0041)

> OQ-01. Ô trống DUY NHẤT còn lại của Nhánh 1 (spec dòng 4260). Viết ngày 06/09/2026, **TRƯỚC khi
> có bất kỳ kết quả đánh giá nào** (spec dòng 3956-3958 và TASKS TD-0041: "viết DR trước khi biết
> kết quả lần đánh giá tiếp theo"). Chủ dự án chốt sau khi xem ba phương án.
>
> 🔴 **Hệ quả bắt buộc phải nói thẳng (spec dòng 3957-3958):** chốt ngưỡng này đồng nghĩa thừa nhận
> hệ thống hiện **CHƯA qua gate** — chưa có một lần đánh giá nào, "kết quả tốt nhất hiện có" là
> *chưa đo* (−inf trong code), và L-Z35 canh đúng điều đó.

## 1. Spec để lộ HAI khoảng trống, không phải một

1. **Công thức** — spec chỉ nói "DSR tính với N = N_ĐĂNG_KÝ = 114" (dòng 4264-4265) và DR-013 (4)
   nói "Sharpe/DSR mỗi lệnh tính trên chuỗi R_realized". Chưa nơi nào viết ra *DSR-adjusted
   expectancy* là phép tính gì. Không định nghĩa công thức thì con số ngưỡng vô nghĩa.
2. **Con số** — v3 ghi "≥ 20%" không căn cứ; v6 xoá thành "......" và đặt câu hỏi mở #20: *"có cách
   suy nó từ chi phí giao dịch + funding kỳ vọng thay vì chọn tuỳ ý không?"*

## 2. Công thức chốt

```
DSR_adj_expectancy  =  mean(R)  −  √(2·ln N) × std(R) / √n_trades

   R          chuỗi R_realized mỗi lệnh (DR-013: pnl_abs / planned_risk_usdt,
              pnl_abs ĐÃ trừ phí + funding)
   N          = effective_n() — N_ĐĂNG_KÝ 114 trước live (DR-010 quy tắc 3),
              cộng Σcontribution trial CONSUMED sau live (§12c.2)
   n_trades   số lệnh trong mẫu đánh giá
```

Đọc bằng lời: *cận dưới của expectancy sau khi trừ đi phần "tình cờ chọn được cái tốt nhất trong
114 phép thử"*. `√(2·ln N)` chính là `dsr_hurdle(N)` đã có (L-Z34) — với N = 114 ≈ 3,08. N nối
thẳng vào phép tính, đổi N thì kết quả đổi (L-Z34 mở rộng canh điều này). Đơn vị: **R mỗi lệnh**.

Vì sao dạng này mà không phải DSR "chuẩn" của Bailey–López de Prado: DSR chuẩn trả về một xác suất
(Sharpe quan sát có vượt Sharpe kỳ vọng dưới null hay không), còn §10.2 đòi một **expectancy** so với
một **ngưỡng**. Công thức trên giữ đúng thành phần khử lạm phát (√(2·ln N)·σ/√n) và cho ra đại lượng
cùng đơn vị với ngưỡng. Đây là quyết định định nghĩa, ghi ở đây một lần — không viết lại ở nơi khác.

## 3. Con số chốt: **0,10 R**

### Suy từ chi phí — trả lời câu hỏi mở #20

`pnl_abs` **đã trừ** phí và funding (DR-013 (1)). Ngưỡng vì thế **không** cần che phí; nó chỉ cần che
những gì backtest **không nhìn thấy**:

| Thứ backtest không thấy | Ước lượng | Quy ra R (zone trung bình R_eff 1,5%) |
|---|---|---|
| Trượt giá khi SL khớp bằng lệnh thị trường (stop-market trên alt volume ≥ 15tr USDT/ngày, notional 60–200 USDT — không có tác động thị trường, chỉ spread + khoảng nhảy khi kích hoạt) | 0,05–0,10% notional, **chỉ ở lệnh thua** (~50% số lệnh) | 0,02–0,04 R / lệnh trung bình |
| Độ ưu ái khớp lệnh DCA (backtest khớp tại giá mở nến, trượt 0 — spec dòng 1207-1215) | **KHÔNG tính ở đây** — DR-015 đo riêng thành Δ_R tại cổng D3.5 và hiệu chỉnh hai chiều ở Nhánh 2. Tính vào ngưỡng này là đếm hai lần | — |
| Funding ngoài mô hình | Không — funding có trong `pnl_abs`, và DG7 chặn trần 0,3 R_eff | 0 |

Sàn chi phí không nhìn thấy ≈ 0,04 R. Nhân hệ số an toàn **2–3 lần** (vì trượt giá SL là ước lượng
chưa đo, sẽ đo thật ở D10 testnet) → **0,10 R**.

### Ba phương án đã trình, nghĩa kinh doanh

Với n ≈ 300 lệnh trong mẫu và std(R) ≈ 1,1 (giả định — phân bố R có TP1 ~1,2R, SL −1R, nhiều lệnh
|R| < 1 do chỉ khớp tranche 1), phần khử lạm phát ≈ 3,08 × 1,1 / √300 ≈ **0,20 R**. Vậy:

| Ngưỡng | mean(R) thô cần đạt | Tỷ lệ thắng cần có nếu TP1 ≈ 1,2R, SL −1R | Nhận xét |
|---|---|---|---|
| 0,05 R | ≥ 0,25 R | ~57% | che đúng 1 lần trượt giá, không dư |
| **0,10 R (chốt)** | ≥ 0,30 R | ~59% | che 2–3 lần trượt giá, có căn cứ chi phí |
| 0,20 R | ≥ 0,40 R | ~64% | số kế thừa v3, không căn cứ; dễ giết nhầm hệ thống sống |

Chủ dự án chọn **0,10 R**.

## 4. Giả định phải ghi rõ (để không bị đọc thành số đo)

- Biểu phí Binance USDⓈ-M dùng để lập luận "phí đã ở trong pnl_abs": maker 0,02%, taker 0,05% (bậc
  công khai). **Chưa xác minh theo bậc tài khoản thật** của chủ dự án — không ảnh hưởng con số ngưỡng
  (phí không nằm trong ngưỡng), chỉ ảnh hưởng cách đọc kết quả sau này.
- Trượt giá SL 0,05–0,10% là ước lượng theo cấu trúc sổ lệnh của nhóm mã đã lọc, **chưa đo**. D10
  (testnet) đo thật; nếu đo ra lớn hơn 0,10%/lệnh thua, ngưỡng này **không tự đổi** — mở DR mới, và
  DR mới cũng phải viết trước khi thấy kết quả gate kế tiếp.
- std(R) ≈ 1,1 và n ≈ 300 chỉ dùng để **minh hoạ độ khó** của từng phương án, không đi vào công thức.

## 5. Hệ quả kiểm tra

- `DSR_ADJ_EXPECTANCY_MIN = 0.10` trong `src/tool_d/gates/thresholds.py` — không còn `+inf`.
- `dsr_adjusted_expectancy()` trong `src/tool_d/gates/dsr.py` — N đi vào phép tính (L-Z34 mở rộng).
- L-Z35 chuyển sang biến thể spec dòng 3954-3955: *"kết quả tốt nhất hiện có vẫn FAIL"*. Kết quả tốt
  nhất hiện có = **chưa có** → `BEST_KNOWN_DSR_ADJ_EXPECTANCY = −inf` (trạng thái *chưa đo*, không
  phải số bịa — N6). Mỗi lần có kết quả đánh giá thật, cập nhật hằng số này **từ số đo** và test phải
  vẫn xanh cho tới khi gate thật sự qua; khi gate qua, test này đổi vai (không còn là placeholder).
- Blocker **B6 gỡ xong** tại commit này: N có (DR-D0PRE-02), công thức có (mục 2), số có (mục 3).
