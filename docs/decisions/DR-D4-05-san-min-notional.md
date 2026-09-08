# DR-D4-05 — Sàn min-notional: một sàn duy nhất của Tool D, và nâng `E_D`

> Quyết định của chủ dự án, 09/09/2026. Sinh từ **TD-0171** (mở lại TD-0082).
> Bằng chứng: `docs/min-notional-check.md` §4 (đo trên metadata sàn thật, 0 trial).
> Commit **RIÊNG và TRƯỚC** mọi dòng mã thi hành — tiền lệ DR-D4-02 / DR-D4-03.

## 1. Vấn đề

Bảng TD-0082 (06/09/2026) kết luận *"min notional: KHÔNG có vi phạm, 102/102 mã qua"*. Kết luận đó
sai ở **cả hai vế** của phép so, và cả hai đều lệch về **cùng một chiều — chiều nói "qua"**:

- **Tử số:** tính bằng `rho` thô. Cỡ lệnh thật (TD-0187, §6.8f B1) là `rho × Π mult_*`, mọi
  `mult_* ≤ 1.0` (§6.2 — `rho` là TRẦN). Notional thật luôn **≤** notional đã kiểm.
- **Mẫu số:** so với `MIN_NOTIONAL.notional` trần trụi. Freqtrade so với
  `max(cost_min × stoploss_reserve, minQty × giá × margin_reserve)`, và vế `minQty` thì code cũ
  **chưa từng đọc** (nó là vế quyết định ở BTC).

Đo lại: **4/102 mã rớt sàn ngay ở ca tốt nhất** (BCH, ETC, LINK, LTC). Và hai thứ nghiêm trọng hơn
con số:

**(a) Backtest và live KHÔNG dùng cùng một sàn**, lệch theo hai chiều ngược nhau:

| Đường chạy | `stoploss` Freqtrade truyền | Sàn ở mã sàn 5 USDT |
|---|---|---|
| Backtest — vào lệnh | −0,05 (hằng số trong mã) | 5,53 |
| Backtest — phần dư sau chốt lời | −0,1, KHÔNG truyền `leverage` | 5,83 |
| Live — vào lệnh | `strategy.stoploss` = −0,99 → trần 1,5 | **7,50** |
| Live — phần dư | −0,99, **CÓ** truyền `leverage` | **2,50** |

Ở `Π mult_* = 0,326`, zone 3%: **backtest cho 94/102 mã vào lệnh, live cho 0/102**. Cùng cấu hình,
cùng pool, cùng ngày. Đây là lỗ hổng **parity** (quy tắc 9), không phải một con số lệch.

**(b) Lệnh dưới sàn biến mất IM LẶNG.** `optimize/backtesting.py:1173` là một `if` **không có
`else`**; `:774` (phần dư) cũng `return trade` không log. Cộng thêm `strategy_safe_wrapper` nuốt
`SizingError` của ta thành WARNING với `rc = 0`. Phiên `-f4` chứng kiến **72 lệnh biến mất** trên
BTC/ETH trong một lượt backtest báo "thành công".

## 2. Quyết định

### 2.1 Phương án C — Tool D tự đặt MỘT sàn, từ chối tường minh (chốt)

Tool D **không** ủy thác phép kiểm sàn cho Freqtrade. Ta tự tính **một sàn duy nhất** cho mỗi mã:

```
san_tool_d(mã) = max( sàn của MỌI đường chạy trong SL_THEO_DUONG_CHAY )
```

và **từ chối vào lệnh / từ chối chốt lời một phần** khi cỡ lệnh dưới sàn đó, **fail-closed và có ghi
sổ** — không im lặng.

**Vì sao lấy `max` chứ không lấy sàn của đường chạy hiện tại:** lấy đúng sàn từng đường thì backtest
và live vẫn hành xử khác nhau, tức lỗ hổng parity còn nguyên — chỉ khác là ta biết về nó. Lấy `max`
làm cho **một cấu hình qua được ở D4 thì cũng qua được ở D11/D12**, và đó chính là điều quy tắc 9
đòi. Cái giá: ở vài đường chạy ta chặt hơn Freqtrade, tức bỏ một số lệnh mà sàn thật vẫn cho qua.
**Chấp nhận có ý thức** — bảo thủ về phía không thể tâng kết quả lên, cùng lập luận đã dùng khi giữ
`v_min` trong `tier_b` (DR-D4-03).

**Vì sao không dựa vào việc Freqtrade tự chặn:** nó chặn **im lặng**. Một lệnh bị bỏ mà không ai đếm
thì §10.2 đang so các arm trên những tập lệnh khác nhau mà bảng kết quả vẫn trông bình thường — đúng
họ "PASS RỖNG" mà dự án đã dính năm lần.

### 2.2 Phương án A — nâng `E_D` 500 → **750** (chốt, 0 trial)

`E_D` là Tầng A (*"chỉnh tự do, 0 trial"*). Đổi từ 500 lên **750**; `tradable_balance_ratio` của
`config/freqtrade/config.json` chỉnh theo cho khớp (`750/1.000 = 0,75`, §6.9.2 đòi khớp).

🔴 **Vì sao 750 chứ không phải 720 như bản đề xuất ban đầu:** ở `E_D` = 720, tranche 1 ở zone 3% là
**đúng 30,00 USDT** trong khi sàn live của 4 mã kia cũng **đúng 30,00**. Một chốt thoả bằng **đẳng
thức chính xác** là chốt không có lề: chỉ cần một thay đổi nhỏ ở phía sàn là nó lật, và nó sẽ lật
**im lặng**. 750 cho tranche 1 = 31,25, tức **lề 4,2%**.

🔴 **Đây là mở lại một quyết định chủ dự án đã cân nhắc và chọn khác.** `DR-D0PRE-06` ghi rõ: tôi
khuyến nghị `E_D ≥ 1.000`, chủ dự án **chọn 500**, chấp nhận đánh đổi. Thông tin MỚI làm quyết định
đó đáng xem lại **không phải** là "tôi vẫn muốn số to hơn", mà là: DR-D0PRE-06 mục 3 dựa trên câu
*"`E_D` = 500 → **102/102 mã qua**, nhưng sát sàn"* — và câu đó **nay biết là sai** (đúng ra là
98/102, và "sát sàn" thực chất đã **vượt** sàn ở 4 mã). Quyết định 500 được đưa ra trên một bảng số
sai; nó xứng đáng được xem lại trên bảng đúng.

**Hệ quả tiền bạc, nói thẳng:** rủi ro mỗi lệnh đi từ `0,375% × 500 = 1,875` USDT lên
`0,375% × 750 = 2,8125` USDT (**+50%**); trần lỗ một ngày xấu từ 40 lên 60 USDT. Vốn phân bổ cho
Tool D tăng 50%. Số lệnh tối đa cùng lúc **không đổi** (6–20 tuỳ zone) vì cả rủi ro lẫn margin đều
tỉ lệ thuận với `E_D` — đã có test ghim ở `test_admission.py`.

### 2.3 KHÔNG làm — phương án B (nâng cỡ lệnh cho đủ sàn)

Bị loại **có ý thức**, không phải bỏ sót. Nâng cỡ lệnh để chạm sàn nghĩa là rủi ro thật vượt
`rho_eff × E_D` — cược to hơn trần, đúng thứ §6.2 cấm bằng câu *"`rho` là TRẦN; tín hiệu tốt không
được cược to hơn"*. Nó cũng phá bất biến D0.1 (rủi ro kế hoạch không phụ thuộc `R_eff`), thứ mà toàn
bộ phán quyết §10.2 theo đơn vị R đang dựa vào.

## 3. Thứ tự thi hành, và vì sao A phải xếp sau

**C** chỉ đụng `src/tool_d/notional.py` (+ test) — làm được ngay.

🔴 **A phải đợi**, vì nó đổi số dưới chân hai phiên đang chạy:

- `tests/lock/test_td0187_*.py` ghim `rủi ro kế hoạch = 1,875 USDT` — file này phiên `-f4` **đang
  sửa dở** (TD-0182). Sửa file thuộc sân phiên khác là điều quy ước hai phiên **cấm**, kể cả tạm
  (bài học TD-0170: bản phá bị ghi đè giữa chừng, lượt chạy báo *12 passed* — một phép đo hỏng trông
  y hệt một phép đo đạt).
- `src/tool_d/take_profit.py` (phiên `-2f`, TD-0189) đang lấy `E_D = 500` làm ca minh hoạ trung tâm.
- Mọi backtest hai phiên đó đang chạy sẽ đổi kết quả giữa chừng.

⇒ A thi hành **sau khi TD-0182 và TD-0189 đã commit xong**, như một việc riêng, một commit riêng.

**KHÔNG cần đo lại gì đã niêm phong.** Δ_R **bất biến** với cỡ lệnh (`lệch_R = qty × Δgiá /
planned_risk` có cỡ lệnh ở cả tử lẫn mẫu — đã kiểm ×1/×3/×20 giống hệt tới bit cuối). Câu chặn của
dự án: *"đại lượng này có NHÌN THẤY thứ tôi sắp đổi không?"* — với Δ_R, câu trả lời là **không**.

## 4. Điều kiện mở lại (viết TRƯỚC, khuôn OQ-07)

Quyết định này được xem lại nếu **bất kỳ** điều nào xảy ra:

1. **Số lệnh/năm đo thật tụt dưới sàn 150** (TD-0081, OQ-10) *vì* sàn của mục 2.1 — phân biệt được
   bằng sổ từ chối: nếu phần lớn lệnh mất là do sàn chứ do bộ lọc thì đây là dấu hiệu, và đòn bẩy
   đầu tiên là `E_D` chứ không phải nới sàn.
2. **Freqtrade đổi hằng số** ở `_get_stake_amount_limit` hoặc ở một trong sáu đường chạy — bảng
   `SL_THEO_DUONG_CHAY` khi đó sai, và nó **không có máy canh tự động** (ta không kiểm soát mã nguồn
   của họ). Phải đọc lại mã nguồn mỗi lần nâng phiên bản Freqtrade.
3. **Sàn của sàn giao dịch đổi** (`MIN_NOTIONAL` / `LOT_SIZE` của Binance) — bảng §4.3 chụp ngày
   09/09/2026, không tự cập nhật.

## 5. Cái quyết định này KHÔNG giải quyết

Ghi ra để không ai đọc quá tay, cùng khuôn `d3_5_han_che`:

- ❌ **Không** sửa được việc Freqtrade nuốt exception — nó vẫn nuốt; ta chỉ tránh không dựa vào nó.
- ❌ **Không** có con số cho pool 102 mã trên **lệnh thật**. Số 17/81 mà phiên `-f4` đo nằm trên
  **48 mã alt EXPLORE**, cùng họ chứ không phải bằng chứng trực tiếp về pool; đường đo trên pool
  vướng ngân sách trial nên **chưa ai đi**.
- ❌ **Không** phủ hướng SHORT (D4 đợt này chỉ LONG — DR-D4-01).
- ❌ Sàn ở mục 2.1 là sàn **min-notional**. `L-Z20` (làm tròn lot) là chốt **khác**, giữ nguyên, và
  dung sai của nó vẫn neo vào `rho` THÔ theo spec dòng 2751 — không hạ theo `mult_*`.
