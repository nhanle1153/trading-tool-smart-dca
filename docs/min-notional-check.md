# Đối chiếu min notional + độ thô bước lot của pool (TD-0082)

> 🔴 **BẢN 06/09/2026 DƯỚI ĐÂY ĐÃ BỊ BÁC MỘT PHẦN — đọc Mục 4 (TD-0171, 08/09/2026) TRƯỚC.**
> Kết luận *"Min notional: KHÔNG có vi phạm"* ở Mục 3 dựa trên hai giả định mà tầng định cỡ
> thật (TD-0187) và mã nguồn Freqtrade đều nói là sai. Giữ nguyên chữ cũ làm lịch sử, gắn
> đính chính tại chỗ — không xoá, để cái bẫy hết hiệu lực mà vẫn truy được vì sao đã tin.

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

---

## 4. Đo lại — TD-0171 (08/09/2026)

> Lệnh sinh bảng (Docker, 08/09/2026):
> `docker compose -f docker/docker-compose.yml run --rm freqtrade entrypoints/build_pool.py --check-min-notional`
> Test khoá: `tests/lock/test_td0171_san_min_notional_that.py` (13 ca).

### 4.1 Hai giả định của bản đầu, và vì sao cả hai đều lệch về phía "qua"

**Tử số — dùng `rho` thô.** Lúc viết bản đầu, tầng định cỡ chưa tồn tại (MT-16: `custom_stake_amount`
0 dòng). TD-0187 dựng nó thì cỡ lệnh thật là `rho_eff = rho × Π mult_*`, với **mọi `mult_* ≤ 1.0`**
(§6.2 — `rho` là TRẦN, `HeSoMult` từ chối khởi tạo nếu có hệ số > 1). Notional thật **≤** notional đã
kiểm, mọi lúc.

**Mẫu số — so với `MIN_NOTIONAL.notional` trần trụi.** Freqtrade so với
`max(cost_min × stoploss_reserve, minQty × giá × margin_reserve)` rồi chia đòn bẩy
(`freqtrade/exchange/exchange.py:_get_stake_amount_limit`, đọc trong image ngày 08/09/2026). Với
`stoploss = -0.99` của `config/freqtrade/config.json` thì `stoploss_reserve = 1,05/(1−0,99) = 105`,
bị kẹp về **trần 1,5** ⇒ sàn cao hơn 50% ở mọi mã. Vế `minQty` thì `build_symbol_filters()` **chưa
từng đọc** — nó quyết định sàn ở **3/102 mã**.

🔴 **Vế *"chưa chia đòn bẩy"* của ghi chú MT-16 là SAI — đây là kết luận ĐO, không phải suy luận.**
Sàn được chia `leverage` (`_get_stake_amount_considering_leverage`), mà `stake` chiến lược trả cũng
là `notional / L` (`sizing.stake_tranche`). Đòn bẩy chia **cả hai vế** nên triệt tiêu khỏi phép so:
PASS/FAIL y hệt ở 1x và 3x. Thêm đòn bẩy vào phép kiểm này là chia sàn thêm một lần nữa, khi đó
**mọi mã đều "qua"** — tức đúng chiều tâng kết quả lên, lần thứ ba. Có test ghim
(`test_don_bay_khong_co_mat_va_do_la_co_y`) để không ai "sửa cho đủ" sau này.

### 4.2 🔴 Đính chính TRONG CHÍNH ĐỢT NÀY — có SÁU đường chạy, BỐN sàn

Bản đo đầu của TD-0171 (09/09/2026, sáng) giả định Freqtrade dùng `stoploss` của
`config.json` (−0,99) cho mọi phép kiểm sàn. **Sai.** Đọc kỹ mã nguồn thì mỗi đường chạy truyền một
hằng số khác nhau:

| Đường chạy | `stoploss` truyền vào | Hệ số dự trữ | Sàn ở mã sàn 5 USDT |
|---|---|---|---|
| Backtest — vào lệnh (`backtesting.py:1087`) | **−0,05** (hằng số trong mã) | 1,105 | **5,53** |
| Backtest — tranche 2/3 (`pos_adjust`) | **0,0** | 1,05 | 5,25 |
| Backtest — phần dư sau thoát một phần (`:723`) | **−0,1**, KHÔNG truyền `leverage` | 1,167 | 5,83 |
| Live — vào lệnh (`freqtradebot.py:1185`) | `strategy.stoploss` = **−0,99** | **1,5** (trần) | **7,50** |
| Live — tranche 2/3 | 0,0 | 1,05 | 5,25 |
| Live — phần dư (`:846`) | `strategy.stoploss`, **CÓ** truyền `leverage` | 1,5 rồi **chia 3** | 2,50 |

🔴 **Hệ quả nặng nhất là một lỗ hổng PARITY (quy tắc 9), không phải một con số lệch:** backtest và
live **không dùng cùng một sàn**, và lệch theo **hai chiều ngược nhau** — vào lệnh thì live chặt hơn
(7,50 vs 5,53), phần dư thì backtest chặt hơn (5,83 vs 2,50). Một cấu hình qua sàn ở **D4
(backtest)** vẫn có thể không mở được lệnh nào ở **D11/D12 (live)**, và không có gì báo.

Bảng đo được tham số hoá theo đường chạy (`notional.sl_hieu_dung`) chứ không chọn một sàn rồi gọi
nó là *"sàn"* — chính việc tưởng có một sàn duy nhất đã sinh ra bản sai ở trên.

### 4.3 Bảng mới — số mã qua sàn THẬT / 102


**Đường chạy `backtest_vao_lenh`** (sàn 5,53 — đây là sàn D4 chạy dưới). Vế quyết định sàn: cost 98
mã · amount 4 mã.

| Π mult_* | R_eff 3,0% | R_eff 1,5% | R_eff 0,9% |
|---|---|---|---|
| 1,000 — mọi hệ số tối đa (ca TỐT NHẤT) | **98/102** (tr.1 = 20,83) | 102/102 (41,67) | 102/102 (69,44) |
| 0,700 — regime weak (ADX 20–25) | 98/102 (14,58) | 102/102 (29,17) | 102/102 (48,61) |
| 0,434 — weak × ZSS 0,62 (đo thật ở MT-16) | 97/102 (9,04) | 98/102 (18,08) | 102/102 (30,14) |
| 0,326 — thêm corr 0,75 | 94/102 (6,78) | 97/102 (13,56) | 102/102 (22,60) |
| 0,175 — weak × ZSS sàn 0,5 × corr 0,5 | **0/102** (3,65) | 95/102 (7,29) | 97/102 (12,15) |
| 0,044 — ca XẤU NHẤT khả dĩ | **0/102** (0,91) | **0/102** (1,82) | **0/102** (3,04) |

**Đường chạy `live_vao_lenh`** (sàn 7,50). Vế quyết định sàn: cost 99 mã · amount 3 mã.

| Π mult_* | R_eff 3,0% | R_eff 1,5% | R_eff 0,9% |
|---|---|---|---|
| 1,000 | **98/102** (20,83) | 102/102 (41,67) | 102/102 (69,44) |
| 0,700 | 98/102 (14,58) | 98/102 (29,17) | 102/102 (48,61) |
| 0,434 | 97/102 (9,04) | 98/102 (18,08) | 102/102 (30,14) |
| 0,326 | **0/102** (6,78) | 97/102 (13,56) | 98/102 (22,60) |
| 0,175 | **0/102** (3,65) | **0/102** (7,29) | 97/102 (12,15) |
| 0,044 | **0/102** (0,91) | **0/102** (1,82) | **0/102** (3,04) |

🔴 **So hai bảng ở ô `Π mult_* = 0,326`, zone 3%: backtest 94/102 · live 0/102.** Cùng một cấu hình,
cùng một pool, cùng một ngày — backtest cho gần như cả pool vào lệnh, live không cho mã nào. Đây là
chỗ lỗ hổng parity thôi trừu tượng.

Bốn mã rớt ngay ở ca tốt nhất trên **cả hai** đường chạy: **BCHUSDT, ETCUSDT, LINKUSDT, LTCUSDT**
(sàn sàn 20 USDT ⇒ 22,11 ở backtest / 30,00 ở live, đều > 20,83).

L-Z20 không đổi (dung sai neo vào `rho` thô theo spec dòng 2751, không hạ theo `mult_*`):
81/102 · 91/102 · 94/102.

### 4.4 Vách 0/102 — điều đáng sợ hơn con số

Sàn thấp nhất mà mọi mã đều có là `5 × hệ_số` — 5,53 ở backtest, 7,50 ở live. Nên khi tranche 1 tụt
xuống dưới ngưỡng đó thì **không phải "vài mã rớt" mà là KHÔNG MÃ NÀO vào lệnh được**: bảng live
nhảy thẳng 97/102 → 0/102 chỉ vì `Π mult_*` đi từ 0,434 xuống 0,326; bảng backtest cũng có vách
nhưng ở chỗ khác (94/102 → 0/102 giữa 0,326 và 0,175). Không có vùng suy giảm dần để ai kịp nhận ra,
và **hai vách nằm ở hai chỗ khác nhau**.

🔴 **Và hệ thống KHÔNG kêu khi điều đó xảy ra.** `optimize/backtesting.py:1173`:

```python
if stake_amount and (not min_stake_amount or stake_amount >= min_stake_amount):
    ...   # vào lệnh
# không có else: rơi xuống dưới, return trade (None nếu là lệnh mới)
```

Không log, không exception. Lệnh biến mất **im lặng**, y hệt hình dạng lỗi MT-16 (vii) — *"một chốt
fail-closed bị nuốt là một chốt KHÔNG TỒN TẠI"*. Hệ quả cho D4: hai arm khác nhau ở `Π mult_*` sẽ
khác nhau ở **số lệnh vào được**, mà bảng kết quả §10.2 trông vẫn hoàn toàn bình thường.

### 4.5 Xác nhận độc lập trên LỆNH THẬT (phiên `-f4`, 09/09/2026)

Mục 4.2–4.4 đo trên **metadata sàn** — nó nói *"cỡ lệnh sẽ rớt sàn"*, chưa nói *"đã rớt"*. Phiên `-f4`
tình cờ gặp mặt còn lại khi chạy backtest `ZoneAbsorption` trên [T0, T2] cho TD-0182, và báo lại:

| Tập | Quan sát |
|---|---|
| BTC | **48 exception** `SizingError: stake tranche 1 = 7–17 < min_stake 23–36 USDT`; 2 lệnh, **0 tranche khớp** |
| ETH | 24 exception cùng dạng |
| 48 mã alt EXPLORE | **17 exception / 81 lệnh** (~21% số lệnh mất một tranche) |

**Tái lập bằng mô hình của mục này** (đo lại 09/09/2026, không lấy con số của phiên kia làm gốc):

| Mã | `MIN_NOTIONAL` | `minQty × giá` | Sàn notional (backtest) | Sàn ký quỹ ở 3x |
|---|---|---|---|---|
| BTCUSDT | 50,00 | **78,54** ← vế thắng | 82,47 | **27,49** |
| ETHUSDT | 20,00 ← vế thắng | 2,49 | 22,11 | 7,37 |

27,49 nằm gọn trong dải **23–36** mà `-f4` quan sát ⇒ mô hình sàn của mục này **tái lập được lệnh
thật**, không chỉ đúng trên giấy. Và với BTC thì vế thắng là **`minQty × giá`** — đúng cái vế mà
`build_symbol_filters()` bản đầu **không đọc**.

🔴 **Ba ghi chú để không ai đọc quá tay số liệu này:**

1. **BTC/ETH KHÔNG nằm trong pool giao dịch** (TD-0083 loại hẳn, chỉ giữ ở tập EXPLORE). Nên 72
   exception của BTC/ETH **không phải** vi phạm mới của pool 102 mã — nó là bằng chứng về **cơ chế**.
   Con số đáng lo là **17/81 trên tập alt**.
2. **Cỡ lệnh rơi dưới sàn theo GIÁ của mã, không theo mã.** Mã đắt dính nặng, alt rẻ hầu như không.
   Nên một lượt kiểm chỉ chạy trên một mã rẻ sẽ **không thấy gì**.
3. 🔴 **Vế *"chưa chia đòn bẩy"* vẫn SAI, kể cả trước số liệu này** — và đây là chỗ dễ kết luận
   ngược nhất. Freqtrade đòi `min_stake` 27,49 = `82,47 / 3`: nó **đã** chia đòn bẩy. Nhưng `stake`
   ta trả cũng là `notional / 3`. Hai vế **cùng** chia 3 nên tỉ số không đổi; chia thêm lần nữa ở
   phía ta sẽ làm mọi mã "qua" trong khi sàn thật không hề đổi. Cùng một quan sát (*"con số của
   Freqtrade đã tính đòn bẩy"*) dẫn tới hai kết luận trái ngược tuỳ người đọc có nhìn **cả hai vế**
   hay chỉ một. Test ghim: `test_don_bay_khong_co_mat_va_do_la_co_y`.

**Điều mục 4.2 KHÔNG đo được mà số liệu này đo được:** exception `SizingError` của ta bị Freqtrade
**NUỐT** (`strategy_safe_wrapper` hạ xuống WARNING, `rc = 0`) — backtest báo thành công với 72 lệnh
biến mất. Cùng hình dạng MT-16 (vii), nhưng lần này chứng kiến trên lượt chạy thật chứ không suy ra
từ mã nguồn.

### 4.6 Kết luận theo tiêu chí nghiệm thu gốc của TD-0082

**Min notional: CÓ vi phạm** (4/102 ở ca tốt nhất trên cả hai đường chạy; 100% ở
`Π mult_* ≤ 0,326` zone rộng với đường live, ≤ 0,175 với đường backtest) ⇒ theo đúng
tiêu chí gốc, phải **nâng `E_D` / đặt sàn / thu pool, và ghi DR**. Đây là quyết định của chủ dự án
(quy tắc 2) — TD-0171 dừng ở phép đo, **chưa** chọn phương án.
