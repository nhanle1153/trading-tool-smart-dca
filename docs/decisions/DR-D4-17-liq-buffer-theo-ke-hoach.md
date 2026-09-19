# DR-D4-17 — `liq_buffer_ratio` tính theo KẾ HOẠCH, bằng hàm giá thanh lý của Freqtrade (thay nguồn export đã bị cắt)

> **Ngày chốt:** 19/09/2026 · **Người quyết:** chủ dự án (chọn *"(A) Tính theo kế hoạch"*, phiên mã `69768527`)
> **Chi phí:** **0 trial**. Không đụng ngưỡng (`LIQ_BUFFER_RATIO_MEAN_MIN = 8`, Cấp C khoá vĩnh viễn, §6.4b).
> Mã `DR-D4-17` + `TD-0348` đặt chỗ bằng commit `5536b07` (N12 mục 7c). **Commit TRƯỚC mã.**

---

## 1. Vì sao phải đổi nguồn

`TD-0342` đọc `liquidation_price` từ export backtest. `TD-0343` đo trên EXPLORE thật: **0/162 lệnh** có giá trị đó. Nguyên nhân
**không phải** thiếu bảng bậc đòn bẩy (chẩn đoán đầu, SAI). Backtest có tính giá thanh lý lúc chạy, nhưng Freqtrade ghi file qua
`trade_list_to_dataframe(..., columns=BT_DATA_COLUMNS)` (`bt_fileutils.py:535`), và 28 cột đó không có `liquidation_price`.
Nếu giữ nguồn cũ thì `liq_buffer_ratio_mean` luôn `unreadable`, nên Nhánh 1 **không bao giờ PASS** (gate đọc `-inf`).

Ba đường đã trình: (A) tính theo kế hoạch · (B) vá cột export trong image (đụng digest `MT-07` + parity quy tắc 9) · (C) để
`unreadable`. Chủ dự án chọn **(A)**.

## 2. Định nghĩa (đọc thẳng spec `:1858–1866`, không phải diễn giải mới)

Spec: *"Tính trên KẾ HOẠCH ĐẦY ĐỦ 3 TRANCHE (D0.3/D0.5), KHÔNG phải trên phần đã khớp"*. Vậy đại lượng này **không phụ thuộc
fill**, và export không cần mang nó.

```
p_j, sl        — từ enter_tag của lệnh (giá kế hoạch tính tại nến xác nhận)
w_j            — doc_trong_so_tranche(cfg)
N_full         — notional tranche 1 đã khớp / w_1          (giá trị ĐÃ dùng để định cỡ, sizing.py:242; cùng DR-D4-15)
L              — tier_a.L_exchange                          (đòn bẩy kế hoạch)

p_avg_plan     = Σ w_j · p_j                                (chữ spec :1861; tiền lệ arm_switches.py:157)
amount_plan    = Σ N_full · w_j / p_j                       (khối lượng nếu khớp đủ 3 tranche đúng giá kế hoạch)
open_rate_vt   = N_full / amount_plan                       (giá vào của VỊ THẾ đó, đúng nghĩa trade.open_rate)
liq_price      = Exchange.get_liquidation_price(pair, open_rate_vt, is_short=False, amount_plan,
                                                stake_amount = N_full / L, leverage = L, wallet_balance = N_full / L)
liq_buffer_ratio = (p_avg_plan − liq_price) / (p_avg_plan − sl)
```

Decision Log (spec `:1885` điểm 2) ghi đủ tử và mẫu: `liq_dist_pct = (p_avg_plan − liq_price)/p_avg_plan`,
`r_eff_pct = (p_avg_plan − sl)/p_avg_plan`, cùng tỉ số.

## 3. Ba chỗ có lựa chọn, ghi rõ để cãi lại được

| # | Chỗ | Chọn | Vì sao · độ lớn |
|---|---|---|---|
| 1 | Giá vào đưa cho hàm thanh lý | `open_rate_vt` (trung bình **điều hoà** theo notional), **không** `p_avg_plan` | Công thức Binance dùng `amount × open_rate` = notional thật của vị thế. Tỉ số vẫn dùng `p_avg_plan` đúng chữ spec. Hai số lệch ở bậc hai theo độ giãn `p_1…p_3`: với zone 3% thì dưới 0,01% giá |
| 2 | Đệm `liquidation_buffer` | Cổng đọc giá **ĐÃ DỊCH** (`get_liquidation_price`, `liquidation_buffer = 0,05`) | Đúng hàm chủ dự án chọn, và đúng nghĩa cột đã duyệt 19/09. Chiều **thận trọng**: điểm thanh lý bị dời về phía giá vào nên tỉ số nhỏ đi khoảng 5%. Giá **thô** (spec `:1862`) ghi cạnh làm `liq_price_tho = (liq − b·open_rate_vt)/(1 − b)`. 🔴 **Ước lượng, chưa đo trên lệnh D4:** ở 3x khoảng cách thanh lý đã dịch ≈ 30,7% (ROSE), nên tỉ số trung bình ≈ 30,7% / HM(`R_eff`). Dùng HM 2,868% của 83 lệnh Z0 EXPLORE (09/09) thì ra ≈ 10,7 (giá thô ≈ 11,3). Từng lệnh xuống dưới 8 khi `R_eff` > 3,8%. Lề so với 8 không lớn, nên **lựa chọn này CÓ THỂ lật cổng**. Đổi sang giá thô = sửa một dòng + một DR, không sửa sau khi đã thấy kết quả |
| 3 | Bậc mmr tra theo gì | Theo `stake_amount`, như Freqtrade tự làm (`dry_run_liquidation_price` gọi `get_maintenance_ratio_and_amt(pair, stake_amount)`) | Spec viết *"theo bậc notional"*. Ở cỡ lệnh của Tool D (`N_full ≈ 2,81 USDT / R_eff`, ≈ 216 USDT ở `R_eff` nhỏ nhất đo được 1,3%) thì cả hai cùng rơi bậc 1. Đo 19/09: ROSE mmr 0,015 và 1000RATS 0,02, **giống nhau** ở cả hai cách tra. Chỉ lệch khi notional vượt bậc 1 (thường ≥ 5.000 USDT) |

## 4. Thi hành (`TD-0348`)

- `src/tool_d/ablation/thanh_ly.py`: hàm THUẦN `liq_buffer_ke_hoach(...)`, **nhận hàm tính giá thanh lý qua tham số**, cùng
  `tinh_liq_freqtrade(cfg_freqtrade)` dựng `Exchange` một lần (`dry_run=True`, `runmode="backtest"`,
  `load_leverage_tiers=True`: đọc bảng bậc đóng gói trong image, **không cần mạng**, đo 0,1 s).
- `chi_so_export.liq_buffer_ratio_mean` đổi nguồn: bỏ đọc `liquidation_price` của export. Một lệnh mà hàm trả `None` (cặp
  không có trong bảng bậc) ⇒ cả chỉ số `unreadable` kèm số lệnh, **không bỏ lệnh cho đẹp trung bình** (N6).
- `chay_lo()` dựng hàm thanh lý **TRƯỚC khi đặt chỗ**. Dựng lỗi ⇒ từ chối trước khi tiêu suất nào.
- Đối chiếu Freqtrade thật trong test: ROSE `open 0,09196 · amount 345 · 3x ⇒ 0,0637`; 1000RATS `0,12868 · 71 ⇒ 0,0896`
  (khớp `TD-0343`).

## 5. Không thuộc DR này — ghi để khỏi hiểu nhầm

🔴 **Cổng §6.4 lúc VÀO LỆNH (`L-Z3`: `liq_buffer_ratio ≥ 8` ở tranche 1, từ chối mở) chưa có dòng mã nào** trong
`ZoneAbsorption.py` hay `src/` (grep 19/09/2026: 0 kết quả cho `liq_buffer`/`L-Z3` ngoài tầng đo). Hàm ở §4 là **tầng đo** cho
tiêu chí Nhánh 1. Nó **không** thay cổng vào lệnh. Việc nối nó vào chiến lược là quyết định riêng, **chưa có mã việc**, trình
ở lần *"chuẩn hóa và lưu"* tới. Ghi chú vận hành spec `:1897`: ở 3x cổng đó *"gần như luôn qua"*, nên thiếu nó không đổi số D4
đang dựng. Dù vậy spec gọi `L-Z3` là test CRITICAL.
