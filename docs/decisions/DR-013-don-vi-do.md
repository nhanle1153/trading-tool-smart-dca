# DR-013 — Đơn vị đo: `pnl_abs` và R (LD-07, LD-08)

> Trạng thái: **CHỐT** (v7 + tu chính v8). Nguồn: `tool-d-smart-dca.md` dòng 2691-2810.
> File này KHÔNG phải bản sao độc lập của spec — mọi con số/công thức phải đối chiếu lại
> spec khi có bất đồng (N1, `CLAUDE.md`). Mục đích của file: gom một chỗ để code và test
> tra cứu nhanh, và là nơi TD-0025 neo bảng ba chữ "R" mà L-Z48c grep.

## Bối cảnh

Tool A cộng dồn `profit_ratio` của 871 lệnh ra −1464% — một con số không thể tồn tại.
`profit_ratio` là lợi nhuận theo MẪU SỐ RIÊNG của từng lệnh (stake khác nhau); với DCA,
stake của một trade còn đổi giữa chừng theo số tranche khớp, nên `profit_ratio` càng khó
diễn giải hơn. Tool A cũng dùng `initial_stop_loss_abs` làm mẫu số R — sai, vì Freqtrade
gán trường đó bằng stoploss TĨNH lúc mở, TRƯỚC khi `custom_stoploss` siết lại → mẫu số
rộng gấp ~1,85 lần, làm sai toàn bộ chỉ số dẫn xuất, kể cả số đã ghi vào sổ trial.

## Quyết định

**(1) Mọi chỉ số tổng hợp tính trên `pnl_abs`.** Expectancy, Sharpe, DSR, CVaR, đường vốn —
tất cả tính trên `pnl_abs` (USDT, đã trừ phí + funding). KHÔNG BAO GIỜ trên `profit_ratio`.

Kiểm bất biến kế toán mỗi fold:

```
starting_balance + Σ pnl_abs == final_balance
```

Ghép nhiều fold thành một đường vốn liên tục bằng **nhân** hệ số, không cộng — mỗi fold
backtest độc lập, tự reset vốn.

**(2) `R_realized = pnl_abs / planned_risk_usdt`.**

```
planned_risk_usdt = rho_eff × E_D, ĐÓNG BĂNG tại tranche 1
```

đã có sẵn trong `block_zone_plan` (bắt buộc cho L-Z20). Mẫu số là **ngân sách rủi ro kế
hoạch** — D0.1 định nghĩa rủi ro mỗi lệnh chính là con số đó, và nó là thứ DUY NHẤT bất
biến suốt vòng đời một trade nhiều tranche (trả lời câu hỏi mở LD-08: không phải "giá vào
tranche 1" hay "giá vào trung bình", mà là ngân sách kế hoạch).

Hệ quả đúng và có ý nghĩa: trade chỉ khớp tranche 1 rồi chạm SL có
`|R_realized| ≈ w[0] × (p1−sl)/(p_avg_plan−sl) < 1`. Đó là thông tin thật ("DCA chưa kịp
phát huy"), không phải lỗi.

**(3) Tầng đo NHẬN mẫu số qua tham số bắt buộc** (đọc từ `custom_data` / Decision Log).
Thiếu bản ghi → RAISE. KHÔNG lùi về hằng số trong code — hằng số có thể đã đổi, chia lại
bằng hằng số cũ ra số sai ÂM THẦM.

**(4) Sharpe/DSR mỗi lệnh tính trên chuỗi `R_realized`**, KHÔNG trên `pnl_abs/E_D` (`E_D`
đổi khi nạp/rút vốn) và KHÔNG trên `profit_ratio` (mẫu số trôi theo tranche).

## Tu chính v8

**(2b) Nguồn sự thật của `planned_risk_usdt`** — chốt phía nào khi hai cách tính lệch nhau
vì làm tròn:

```
planned_risk_usdt := Σ ( qty_i_kế_hoạch × |p_i_kế_hoạch − sl_price| )
                      trên THANG ĐẦY ĐỦ theo thiết kế lệnh
```

với `qty_i` SAU khi làm tròn lot-size/min-notional (đúng khối lượng sẽ gửi lên sàn), và
`p1 = p1_order` THẬT của §3.5, không phải `zone_high` danh nghĩa.

`rho_eff × E_D` là NGÂN SÁCH; tổng thang là KẾ HOẠCH THI HÀNH. Khi hai số này lệch (lot
thô, `E_D` nhỏ, zone hẹp), thứ có thể thật sự mất là KẾ HOẠCH — nên nó là mẫu số của
`R_realized`.

Khẳng định bắt buộc lúc entry (đây chính là L-Z20, giờ có chiều thi hành rõ):

```
|tổng thang − rho_eff × E_D| ≤ 1% × rho_eff × E_D
```

VI PHẠM → **TỪ CHỐI VÀO LỆNH** (zone quá hẹp / lot quá thô cho `E_D` hiện tại — nối vào
kiểm min-notional ở D0-PRE), không phải ghi cảnh báo rồi vào.

Hệ quả: `N_full` tính lại theo `p1_order` thật (chốt câu hỏi mở #27 của spec).

**(2c) Tính chất phải giữ** (kiểm bằng test, không bằng lời):

- Chạm SL sau khi khớp đủ thang = −1,00R trước phí; SAU phí + funding + trượt stop-market
  phải nằm trong `[−1.15R, −1.00R)` — trần 1.15 chính là `max_single_trade_loss / risk_budget
  ≤ 1.15` của §10.2/DR-011, hai con số này từ nay là MỘT.
- Z0 chạm SL dùng CÙNG hàm tính, không nhánh code riêng — công thức thoái hoá tự nhiên khi
  thang chỉ có 1 tranche.
- SL dời (hoà vốn, v.v.) → `R_realized` KHÔNG đổi. Thiếu bản ghi → raise (đã có ở (3)).
- Trần thang = 3 tranche (D0.4) là điều kiện tồn tại của R — đã thoả từ thiết kế, ghi lại
  để thấy sự phụ thuộc.
- Lưu THÀNH PHẦN THÔ tại tranche 1 (`sl_price`, `p1_order`/`p2`/`p3`, qty từng tranche —
  đã có ở §8.3) ⇒ mẫu số kiểu-A (riêng tranche 1) và kiểu-D (phần đã khớp) TÍNH LẠI ĐƯỢC bất
  cứ lúc nào làm số CHẨN ĐOÁN — nhưng CHỈ định nghĩa (2)/(2b) ở trên nuôi gate/DSR, số khác
  phải mang tên khác.

**(2d) Bảng tên gọi — ba chữ "R" là ba đại lượng khác nhau, cấm chữ "R" trần:**

| Tên | Đơn vị | Là gì |
|---|---|---|
| `R_eff` / `r_eff_pct` | khoảng GIÁ (%) | `p_avg_plan` → SL, nuôi `TP_fallback`, DG7, `liq_buffer` |
| `planned_risk_usdt` | USDT | mẫu số duy nhất của `R_realized` |
| `R_realized` | bội số (không thứ nguyên) | `pnl_abs / planned_risk_usdt` |

Vì khối lượng tăng theo tranche mà `planned_risk_usdt` không đổi, khoảng GIÁ ứng với +1R co
lại khi thang khớp thêm — nên MỤC TIÊU THOÁT phải neo giá/zone (§5.1), và mốc fallback phải
gọi tường minh là "bội số `R_eff`" (khoảng giá), **không bao giờ chỉ là "R" trần.**

Ví dụ đúng/sai khi viết code hay tài liệu:

- ✅ `TP_fallback = p_avg + 1.5 × R_eff`
- ✅ `funding_paid_cumulative ≥ 0.3 × R_eff`
- ❌ `"4R"`, `tp_source = "4R_fallback"`, biến đặt tên trần `R = ...`

## Test liên quan

| Test | Nội dung | Trạng thái ở D0-PRE |
|---|---|---|
| **L-Z46** 🔴 CRITICAL | grep tầng đo: không có `profit_ratio` trong phép cộng/trung bình; không có `initial_stop_loss_abs` | ✅ TD-0019 |
| L-Z47 | Σ `pnl_abs` khớp `final_balance` từng fold, sai số < 0.01 USDT | Chờ tầng đo thật có dữ liệu lệnh (D1+) |
| L-Z48 | mọi `R_realized` có `planned_risk_usdt > 0` từ bản ghi; lệnh thiếu bản ghi → tầng đo raise | Chờ tầng đo thật có dữ liệu lệnh (D1+) |
| L-Z48b 🆕 v8 | mô phỏng khớp đủ thang rồi chạm SL vùng: `R_realized ∈ [−1.15, −1.00)`; Z0 cùng dải, cùng hàm tính (kiểm bằng call-graph) | Chờ logic tính `R_realized` (D1+) |
| **L-Z48c** 🆕 v8 | grep code + Decision Log: không có định danh/nhãn "R" trần; chỉ `{R_eff, r_eff_pct, planned_risk_usdt, R_realized}` và dẫn xuất có tên đầy đủ | ✅ TD-0019 |

## Tham chiếu

- Spec: `tool-d-smart-dca.md` §DR-013 (dòng 2691-2810), §8.3 (khối lưu trữ), §10.2/DR-011
  (trần 1.15 chung với `max_single_trade_loss`), L-Z20 (khẳng định lệch thang lúc entry).
- Code hiện có tuân thủ DR này (D0-PRE, chưa có logic backtest thật): `tests/lock/test_lz46_profit_ratio_banned.py`,
  `tests/lock/test_lz48c_no_bare_r_label.py`.
