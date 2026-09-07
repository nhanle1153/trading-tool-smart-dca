# freqtrade-source-read.md — Đọc mã nguồn Freqtrade đang cài (TD-0028)

> Bắt buộc theo §12 (spec dòng 4442-4445): "đọc `git show` mã nguồn Freqtrade cho D2a/D2b/D6/D7
> ghi research-log", làm **TRƯỚC** khi viết bất kỳ test nào về các giả định đó (Nguyên tắc chẩn
> đoán 0d.7). File này là kết quả đọc đó — không suy đoán, mọi khẳng định trích đường dẫn +
> số dòng thật trong image đang chạy.
>
> Giả định D1, D3, D4, D5 (spec §9b.2) KHÔNG thuộc phạm vi TD-0028 — chỉ D2a, D2b, D6, D7 được
> liệt kê tường minh ở §12. D1/D3/D5 đọc ở D2 (TD-0111/0112/0113 — xem mục 5 trở đi). D4 chỉ
> verify được ở Testnet/Live (bảng §9b.2), không đọc source được — hoãn tới D3.5/D9.5+.

## 0. Định danh phiên bản đang đọc

| Trường | Giá trị |
|---|---|
| Freqtrade version | `2026.8` |
| Freqtrade source commit (`freqtrade_commit`, ghi trong chính image) | `9f10e357a93c1dcf10c2a2b367659214d89c073e` |
| Base image | `freqtradeorg/freqtrade@sha256:7031bca43ed7668ebf421725dd5016acade6ef88b0771db3e08c96e6d19a42db` |
| Image `docker-tests` build từ Dockerfile trên | `sha256:64965a4bed08db9e6d0e9e8a926ab9993936f4ed3dc141ad4c64a6525c7a4fd1` |
| Python trong image | `3.14.7` (Debian 13 trixie) |
| CCXT | `4.5.76` |
| Đường dẫn mã nguồn trong container | `/freqtrade/freqtrade/` (bản cài **editable**, `pip show freqtrade` → `Editable project location: /freqtrade`) |
| Cách tra lại | `docker compose run --rm --entrypoint cat tests /opt/freqtrade_source_commit.txt` |

Mọi số dòng dưới đây là số dòng trong file **tại thời điểm đọc** (06/09/2026, TD-0028). Nếu image đổi (pull lại `stable`), số dòng có thể lệch — phải đọc lại, không dùng số cũ.

---

## 1. D2a — Freqtrade HUỶ + ĐẶT LẠI `STOP_MARKET` khi khối lượng SL đổi

**Kết luận: XÁC NHẬN ĐÚNG.** Spec (dòng 3172) nói D2a "đã xác nhận ở Tool A bằng mã nguồn, không cần verify lại" — TD-0028 đọc lại trên phiên bản Freqtrade hiện tại (2026.8, khác bản Tool A dùng) để chắc cơ chế còn tồn tại nguyên vẹn.

**Đường dẫn:** `/freqtrade/freqtrade/freqtradebot.py`

Cơ chế gồm **hai bước tách rời** (không phải một hàm "cancel-then-recreate" nguyên tử):

**Bước 1 — Huỷ ngay khi lệnh tranche khớp**, dòng 1074–1078, trong `update_trade_state()`:
```python
if pos_adjust:
    if order_status == "closed":
        logger.info(f"DCA order closed, trade should be up to date: {trade}")
        trade = self.cancel_stoploss_on_exchange(trade)
    else:
        logger.info(f"DCA order {order_status}, will wait for resolution: {trade}")
```
`pos_adjust` là cờ đánh dấu lệnh vừa khớp là một lần **DCA/position-adjustment** (tranche 2, 3 của Tool D) — không phải entry đầu. Khi lệnh đó `closed`, Freqtrade **huỷ SL hiện tại ngay lập tức**, không chờ vòng lặp tiếp theo.

Đường huỷ thứ hai (dự phòng, đối chiếu ví với sàn), dòng 601–609:
```python
if prev_trade_amount != trade.amount:
    # Cancel stoploss on exchange if the amount changed
    trade = self.cancel_stoploss_on_exchange(trade)
```

**Bước 2 — Tạo lại ở vòng lặp kế tiếp**, trong `handle_stoploss_on_exchange()` (dòng 1467–1518): nếu `len(stoploss_orders) == 0` (đúng trạng thái sau Bước 1), gọi:
```python
stop_price = trade.stoploss_or_liquidation
if self.create_stoploss_order(trade=trade, stop_price=stop_price):
    return False
```
`create_stoploss_order()` (dòng 1431) dùng `amount=trade.amount` — **giá trị MỚI** (đã cộng tranche vừa khớp, vì `trade.recalc_trade_from_orders()` chạy trước đó trong `update_trade_state`).

**Hệ quả trực tiếp cho D2c (khoảng trống):** Bước 1 và Bước 2 nằm ở **hai lần gọi hàm xử lý khác nhau** của vòng lặp bot chính — không có gì đảm bảo Bước 2 chạy ngay sau Bước 1 trong cùng một chu kỳ. Cận trên lý thuyết của khoảng trống = chu kỳ polling của worker:

```python
# /freqtrade/freqtrade/constants.py, dòng 17
PROCESS_THROTTLE_SECS = 5  # sec
```
tức mặc định **tối đa ~5 giây + độ trễ round-trip API** không có SL trên sàn sau mỗi lần tranche khớp — đây chính là con số cần đo thật (`gap_ms`, §8.3) ở D2c qua testnet, TD-0028 chỉ xác nhận **cơ chế** và **cận trên lý thuyết**, không đo `gap_ms` thật (đúng thứ tự spec: D2a đọc source, D2c chỉ verify được ở Testnet/Live).

**Kết luận đối chiếu với DR-013/§9b.2:** khớp hoàn toàn với mô tả spec — "D0.2 KHÔNG bị vi phạm (giá SL không đổi, chỉ khối lượng đổi)" đúng, vì `stop_price` truyền vào `create_stoploss_order` luôn là `trade.stoploss_or_liquidation` (không đổi giữa các tranche cùng một zone) — chỉ `amount` khác.

---

## 2. D2b — Freqtrade có hỗ trợ `closePosition=true` cho stop order Binance Futures không

**Kết luận: KHÔNG HỖ TRỢ.**

```
grep -rn "closePosition\|close_position" /freqtrade/freqtrade/exchange/*.py
→ không có kết quả nào
```

Quét toàn bộ `freqtrade/exchange/` (bao gồm `exchange.py`, `binance.py`) — không có tham số `closePosition` ở bất kỳ đâu trong luồng tạo lệnh stop (`create_stoploss`, `stoploss_adjust`, `_get_stop_order_type`). Freqtrade tự quản lý khối lượng SL bằng tay (huỷ+đặt lại, mục 1), không dùng cờ `closePosition=true` của Binance Futures API (cờ đó để sàn tự đóng TOÀN BỘ vị thế bất kể khối lượng, không cần đặt lại khi khối lượng đổi).

**Hệ quả:** nhánh D2b của spec (dòng 3175: "nếu có, khối lượng KHÔNG cần đổi khi tranche khớp và khoảng trống biến mất") **không áp dụng** — con đường duy nhất là D2c (đo `gap_ms` thật). Không cần chờ testnet để loại trừ D2b nữa — TD-0028 đã loại trừ bằng đọc mã nguồn, theo đúng thứ tự spec quy định ("D2b: mã nguồn + sàn", cột "D2b" đã xong phần "mã nguồn").

---

## 3. D6 — `adjust_trade_position()` trong backtest đánh giá THEO NẾN, tại giá MỞ nến

**Kết luận: XÁC NHẬN ĐÚNG — đây là rủi ro số một của kết quả Tool D, đúng như spec cảnh báo.**

**Đường dẫn:** `/freqtrade/freqtrade/optimize/backtesting.py`

Hàm `_check_adjust_trade_for_candle()` (dòng 718), được gọi từ `_check_trade_exit()` (dòng 987, khi `self.strategy.position_adjustment_enable` bật — **bắt buộc bật với Tool D**), dòng 719–720:
```python
def _check_adjust_trade_for_candle(
    self, trade: LocalTrade, row: tuple, current_time: datetime
) -> LocalTrade:
    current_rate: float = row[OPEN_IDX]
    current_profit = trade.calc_profit_ratio(current_rate)
```
`row[OPEN_IDX]` là **giá mở của nến** đang xử lý — không phải giá thật tại thời điểm lệnh tranche khớp trong nến. `current_rate` này được truyền thẳng vào `_adjust_trade_position_internal()` (dòng 726) làm cả `current_entry_rate` lẫn `current_exit_rate` — tức **toàn bộ quyết định** (có nên vào tranche mới không, lợi nhuận hiện tại bao nhiêu) của `adjust_trade_position()` do strategy viết đều nhìn thấy **đúng một giá duy nhất: giá mở nến**, bất kể nến đó biến động thế nào.

Khi quyết định là "vào thêm" (`stake_amount > 0.0`, dòng 739), lệnh tranche được đặt qua `_enter_trade()` (dòng 1121), và hàm này (dòng 1146–1148) cũng dùng `row[OPEN_IDX]` làm giá đề xuất mặc định:
```python
propose_rate, stake_amount, leverage, min_stake_amount = (
    self.get_valid_entry_price_and_stake(
        pair, row, row[OPEN_IDX], stake_amount_, ...
    )
)
```
(Strategy có thể override qua `custom_entry_price()` — Tool D dùng lệnh chờ tại `p1/p2/p3` tính trước nên có override, nhưng **quyết định có kích hoạt tranche hay không** ở bước trước đó vẫn dựa trên giá mở nến, không phải giá `p_i` thật.)

**Đối chiếu với L-Z50 (spec dòng 3985-3987):** L-Z50 đòi "mọi tranche fill trong backtest có `fill_price == giá mà timeframe_detail 5m cho thấy đã CHẠM p_i` (không phải open nến 1H)" — TD-0028 xác nhận rủi ro L-Z50 được viết ra để canh là **có thật trong mã nguồn**, không phải suy đoán. `timeframe_detail` là một luồng dữ liệu tách biệt (không đọc ở TD-0028 này, để dành khi implement L-Z50 thật) dùng để mô phỏng giá trong-nến chi tiết hơn — nhưng **quyết định vào tranche** (`_check_adjust_trade_for_candle`) không tự động dùng nó, phải kiểm lại khi implement zone detection xem có cần tự gọi API `timeframe_detail` riêng cho bước quyết định hay chỉ cho bước xác định giá khớp.

**Hệ quả đúng như spec (dòng 3184-3185):** lệch này **có lợi một chiều** cho mọi arm DCA so với Z0 (Z0 chỉ khớp một lần ở entry, không lặp lại phép "nhìn giá mở nến" nhiều lần như DCA). Nhánh 2 của §10.2 phải đọc kết quả này QUA hiệu chỉnh Δ_R của cổng D3.5 — đúng như spec đã thiết kế (DR-015), TD-0028 chỉ xác nhận cơ chế gây lệch là có thật.

---

## 4. D7 — `trade.custom_data` GIỮ ỔN ĐỊNH giữa các lần gọi callback trong backtest

**Kết luận: CƠ CHẾ AN TOÀN — nhưng có một điều kiện tiên quyết PHẢI đúng khi implement (ghi ở dưới), và một phát hiện phụ đáng chú ý về phạm vi biến toàn cục.**

**Đường dẫn:** `/freqtrade/freqtrade/persistence/custom_data.py` + `/freqtrade/freqtrade/optimize/backtesting.py`

### 4.1. Cơ chế lưu trữ ở chế độ backtest (`use_db=False`)

`CustomDataWrapper.custom_data` (dòng ~86) là một **list cấp CLASS** (không phải cấp instance):
```python
class CustomDataWrapper:
    use_db = True
    custom_data: list[_CustomData] = []
```
Khi backtest, `use_db=False` — mọi `set_custom_data()`/`get_custom_data()` đọc/ghi thẳng vào list này, lọc theo `ft_trade_id == trade_id` (dòng 132, 121-138). Đây KHÔNG phải một dict-per-trade — là MỘT danh sách DÙNG CHUNG cho toàn bộ trade trong backtest, lọc bằng vòng lặp mỗi lần đọc.

### 4.2. `trade_id` có ổn định qua các callback không — CÓ, với điều kiện

`LocalTrade.id` (dòng 401, `trade_model.py`) mặc định là `0` ở cấp class — **nhưng** mỗi trade THẬT được tạo trong backtest (`_enter_trade`, dòng 1208-1213 `backtesting.py`) được gán ngay:
```python
if trade is None:
    self.trade_id_counter += 1
    trade = LocalTrade(id=self.trade_id_counter, ...)
```
`id` được gán **tại thời điểm tạo trade**, trước khi bất kỳ callback nào (kể cả entry đầu) có cơ hội gọi `custom_data`. Tranche 2/3 tái sử dụng **cùng object `trade`** (nhánh `if trade is None` không chạy lại) — tức cùng `id` xuyên suốt vòng đời lệnh. Do đó `get_custom_data`/`set_custom_data` lọc đúng theo `id` đó, ổn định qua tranche 1→2→3→DG6/7/8→custom_exit, **khớp đúng khẳng định của spec** (dòng 3193: "custom_data ghi ở tranche 1 đọc lại NGUYÊN VẸN ở callback của tranche 2, 3...").

🔴 **Phát hiện phụ — nhánh nguy hiểm nếu bị gọi sai chỗ:** `set_custom_data()` (dòng ~144, `custom_data.py`) có: `if trade_id is None: trade_id = 0`. Nếu bất kỳ đoạn code Tool D nào gọi `set_custom_data`/`get_custom_data` **trước khi trade có `id` thật** (id vẫn là giá trị mặc định của class `0`, hoặc gọi với `trade_id=None` tường minh), NHIỀU trade khác nhau sẽ vô tình dùng chung `trade_id=0` — **custom_data của các cặp giao dịch khác nhau sẽ trộn lẫn**. Với Tool D (giao dịch đồng thời ~100 cặp), đây là lớp lỗi ngầm nguy hiểm hơn cả điều D7 gốc đang canh — **L-Z49 cần bổ sung một khẳng định phụ** (khi implement thật, ghi vào research-log, không sửa spec ở D0-PRE): mọi lần gọi `trade.set_custom_data()`/`get_custom_data()` phải xảy ra **sau** khi trade đã có `id` thật (tức trong các callback thường như `custom_stoploss`, `adjust_trade_position`, KHÔNG bao giờ ở bước tính giá entry trước khi trade tồn tại).

### 4.3. Chống rò rỉ giữa các lần backtest khác nhau (liên quan DR-010/L-Z12)

`reset_backtest()` (dòng 486-493, `backtesting.py`), docstring **"called once for every call to backtest()"**:
```python
def reset_backtest(self, enable_protections: bool = False):
    self.disable_database_use()
    PairLocks.reset_locks()
    Trade.reset_trades()
    CustomDataWrapper.reset_custom_data()
```
`Trade.reset_trades()` và `CustomDataWrapper.reset_custom_data()` (dòng 106-110, `custom_data.py`: xoá sạch list class khi `not use_db`) chạy **cùng nhau**, mỗi lần `backtest()` được gọi. Xác nhận: **miễn E1 (`run_backtest.py`) gọi đúng API `backtest()` cấp cao của Freqtrade** (không gọi tắt qua API nội bộ bỏ qua `reset_backtest`), mỗi trial trong D0.9/ablation không rò rỉ `custom_data` từ trial trước — quan trọng cho tính độc lập giữa các cấu hình so sánh ở GATE §10.2.

---

## 5. D1 (TD-0111) — `adjust_trade_position()` mô phỏng đúng fill limit-maker trong backtest, kể cả ca KHÔNG khớp

**Kết luận: XÁC NHẬN ĐÚNG.** Backtest futures của Freqtrade có mô hình fill/no-fill thật cho lệnh
limit, không phải "cứ đặt là khớp".

**Đường dẫn:** `/freqtrade/freqtrade/optimize/backtesting.py`

**Bước 1 — đặt lệnh, kiểm khớp ngay trong CHÍNH nến đặt lệnh.** `_enter_trade()` (dòng 1121) tạo
`Order` với `status="open"`, rồi gọi ngay (dòng 1273):
```python
order._trade_bt = trade
trade.orders.append(order)
self._try_close_open_order(order, trade, current_time, row)
```
`_try_close_open_order()` (dòng 802) chỉ đóng lệnh nếu `_get_order_filled()` (dòng 787) trả `True`:
```python
def _get_order_filled(self, rate: float, row: tuple) -> bool:
    """Rate is within candle, therefore filled"""
    return row[LOW_IDX] <= rate <= row[HIGH_IDX]
```
Giá đề xuất (`propose_rate`) cho lệnh limit được tính ở `get_valid_entry_price_and_stake()` (dòng
1024-1054) qua `custom_entry_price()` — với chiều long chỉ bị kẹp trần `min(propose_rate, row[HIGH_IDX])`
(chặn đề xuất giá cao hơn cả nến, tránh biến limit thành stop-limit mà Freqtrade live không hỗ trợ),
**không kẹp sàn** — nghĩa là một limit đặt dưới `row[LOW_IDX]` (đúng tình huống lệnh chờ zone
absorption của Tool D) **không bị ép khớp giả** ở bước này; nó chỉ khớp thật nếu giá sau đó thật sự
chạm tới, đúng cơ chế `_get_order_filled`.

**Bước 2 — nếu KHÔNG khớp ngay, lệnh vẫn "open" và được kiểm LẠI mỗi nến sau đó.**
`backtest_loop()` (dòng 1520), mục "3. Process entry orders" (dòng 1563-1566):
```python
for trade in list(LocalTrade.bt_trades_open_pp[pair]):
    order = trade.select_order(trade.entry_side, is_open=True)
    if self._try_close_open_order(order, trade, current_time, row):
        self.wallets.update()
```
Chạy lại đúng phép kiểm `_get_order_filled` ở Bước 1, cho mọi nến tiếp theo — đây chính là "ca
KHÔNG khớp" spec đòi phải mô phỏng đúng: giá không chạm thì lệnh cứ chờ, không tự khớp.

**Bước 3 — hết hạn/hủy nếu không bao giờ khớp.** `manage_open_orders()` (dòng 1330, gọi ở mục "1.
Manage currently open orders" của `backtest_loop`, dòng 1538-1542) gọi `check_order_cancel()` (dòng
1378), dùng `strategy.ft_check_timed_out()` (tôn trọng `order_time_in_force`/`unfilledtimeout` cấu
hình) để quyết định huỷ:
```python
if timedout:
    if order.side == trade.entry_side:
        self.timedout_entry_orders += 1
        if trade.nr_of_successful_entries == 0:
            return True  # xoá cả trade — entry ĐẦU chưa từng khớp
        else:
            del trade.orders[trade.orders.index(order)]  # chỉ xoá lệnh DCA/tranche này
```
🔑 **Trực tiếp liên quan tranche Tool D:** nếu lệnh tranche 2/3 (một "additional entry order", vì
`trade.nr_of_successful_entries > 0` lúc đó) hết hạn theo `entry_order_ttl_bars_1h` (đã có trong
`config/tool_d_config.yaml.tier_c`) mà chưa khớp, CHỈ lệnh đó bị xoá — trade với tranche 1 đã khớp
vẫn sống tiếp, không bị huỷ theo. Ngược lại nếu là entry ĐẦU TIÊN chưa từng khớp, cả trade bị xoá
(`handle_left_open()`, dòng 1278, cũng dọn nốt các trade còn "has_open_orders và
nr_of_successful_entries == 0" ở cuối backtest — "Ignore trade if entry-order did not fill yet").

**Kết luận đối chiếu spec:** giả định D1 (bảng §9b.2: *"`adjust_trade_position()` mô phỏng đúng fill
limit maker trong BACKTEST futures, kể cả ca không khớp"*) — ĐÚNG. Rủi ro nếu SAI ("Toàn bộ kết quả
D0.9 (Ablation) vô nghĩa") KHÔNG xảy ra ở tầng cơ chế fill/no-fill này. Rủi ro thật của Tool D nằm ở
chỗ khác đã xác nhận riêng: D6 (mục 3 trên) — quyết định CÓ vào tranche hay không vẫn nhìn giá mở
nến, tách biệt với việc lệnh đó có khớp hay không.

---

## 6. D3 (TD-0112) — Freqtrade tính đúng giá vào trung bình khi nhiều lần entry, `custom_stoploss` đọc được nó

**Kết luận: XÁC NHẬN ĐÚNG.**

**Đường dẫn:** `/freqtrade/freqtrade/persistence/trade_model.py` (tính giá) +
`/freqtrade/freqtrade/strategy/interface.py` (điểm đọc)

**Công thức giá trung bình — `recalc_trade_from_orders()`** (dòng 1265), duyệt mọi order đã khớp
(`o.ft_is_open or not o.filled` thì bỏ qua), cộng dồn theo trọng số khối lượng — đúng định nghĩa
VWAP (Volume-Weighted Average Price), dòng 1286-1297:
```python
tmp_amount = FtPrecise(o.safe_amount_after_fee)
tmp_price = FtPrecise(o.safe_price)
is_exit = o.ft_order_side != self.entry_side
side = FtPrecise(-1 if is_exit else 1)
if tmp_amount > ZERO and tmp_price is not None:
    current_amount += tmp_amount * side
    price = avg_price if is_exit else tmp_price
    current_stake += price * tmp_amount * side
    if current_amount > ZERO and not is_exit:
        avg_price = current_stake / current_amount
```
Sau vòng lặp, nếu trade còn mở (dòng 1325-1329):
```python
if current_amount_tr > 0.0:
    self.open_rate = price_to_precision(
        float(current_stake / current_amount), ...
    )
```
`self.open_rate` — thuộc tính DUY NHẤT mọi nơi khác trong Freqtrade coi là "giá vào lệnh" — được
gán lại bằng đúng `Σ(giá_i × khối_lượng_i) / Σ(khối_lượng_i)` trên MỌI entry order đã khớp (kể cả
tranche 1, 2, 3 của Tool D), không phải giá của entry gần nhất hay entry đầu tiên.

**Thời điểm cập nhật — ngay sau mỗi lần tranche khớp, cùng vị trí đã xác nhận ở D1 (mục 5):**
`_enter_trade()` trong `backtesting.py`, dòng 1273-1274:
```python
self._try_close_open_order(order, trade, current_time, row)
trade.recalc_trade_from_orders()
```
Gọi lại NGAY SAU khi một order (kể cả order tranche) khớp — `trade.open_rate` luôn phản ánh đúng
giá trung bình MỚI NHẤT trước khi bất kỳ logic exit/stoploss nào của cùng chu kỳ backtest chạy tiếp,
không có độ trễ một nến.

**`custom_stoploss` đọc được giá này** — chữ ký hàm (`interface.py`, dòng 446-454) nhận thẳng đối
tượng `trade: Trade` đầy đủ, không phải một con số giá tách rời:
```python
def custom_stoploss(
    self, pair: str, trade: Trade, current_time: datetime,
    current_rate: float, current_profit: float, after_fill: bool, **kwargs,
) -> float | None:
```
Một implementation thật chỉ cần đọc `trade.open_rate` bên trong hàm này để lấy đúng giá trung bình
đã tính ở trên — không cần tự tính lại, không cần lưu trạng thái riêng qua `custom_data`.

**Kết luận đối chiếu spec (bảng §9b.2, D3):** *"Freqtrade tính đúng giá vào trung bình khi nhiều lần
entry, `custom_stoploss` đọc được nó"* — ĐÚNG cả hai vế. Rủi ro nêu trong spec nếu SAI ("phải tự
tính/quản lý giá trung bình, thêm code") KHÔNG xảy ra — `custom_stoploss` khi implement thật chỉ
cần `trade.open_rate`, không cần cơ chế tính tay song song (tránh đúng loại "hai nguồn sự thật" mà
MT-03/MT-08 đã cảnh báo ở nơi khác của project này).

---

## 7. D5 (TD-0113) — `timeframe_detail=5m`: thứ tự khớp khi nhiều mức giá cùng nằm trong nến 1H

**Kết luận: XÁC NHẬN ĐÚNG, với một giới hạn quan trọng cần nói rõ.** `timeframe_detail` khiến thứ tự
khớp giữa các nến 5m PHẢN ÁNH ĐÚNG trình tự thời gian thật — nhưng bên TRONG một nến 5m (đơn vị nhỏ
nhất khả dụng), nếu nhiều điều kiện thoát cùng đúng, Freqtrade dùng một THỨ TỰ ƯU TIÊN CỐ ĐỊNH, không
phải "dò xem cái nào xảy ra trước thật".

**Đường dẫn:** `/freqtrade/freqtrade/optimize/backtesting.py` (vòng lặp nến chi tiết) +
`/freqtrade/freqtrade/strategy/interface.py` (thứ tự ưu tiên thoát lệnh)

**Cơ chế trải nến 1H thành các nến 5m — hoàn toàn tuần tự theo thời gian thật.**
`_time_generator_det()` (dòng 1616) sinh `current_time` tăng dần đều bước `timeframe_detail_td` (5m)
từ đầu tới cuối nến chính — không có cách nào đảo thứ tự:
```python
current_time = start_date
i = 0
while current_time <= end_date:
    yield current_time, i == 0, True, i
    i += 1
    current_time += self.timeframe_detail_td
```
`get_detail_data()` (dòng 1582) cắt đúng các nến 5m thật nằm trong `[current_time, current_time+1h)`
bằng `searchsorted` trên timestamp thật, không đoán. Vòng lặp tiêu thụ (`time_pair_generator_det`,
dòng 1678) gọi `self.backtest_loop(row, pair, current_time_det, ...)` **một lần cho mỗi nến 5m**, theo
đúng thứ tự sinh ra ở trên — cả kiểm khớp lệnh vào (`_try_close_open_order`, dùng lại đúng cơ chế đã
xác nhận ở mục 5/TD-0111) lẫn kiểm thoát lệnh (`_check_trade_exit`) đều chạy lại trên MỖI nến 5m, không
phải một lần duy nhất trên cả nến 1H gộp.

**Nhưng BÊN TRONG một nến (5m hay 1H khi không có detail): thứ tự ưu tiên CỐ ĐỊNH, không phải thời
gian thật.** `IStrategy.should_exit()` (dòng 1419) ghi rõ trong comment (dòng 1505-1508):
```python
# Sequence:
# Exit-signal
# Stoploss
# ROI
# Trailing stoploss
```
Tức nếu MỘT nến (dù là nến 5m) có cả điều kiện stoploss lẫn ROI cùng đúng, stoploss LUÔN được trả về
trước ROI trong danh sách `exits`, và `_check_trade_exit` (dòng 980) lấy điều đầu tiên thoát được —
đây là lựa chọn CHÍNH SÁCH bảo thủ có chủ đích của Freqtrade, không phải suy luận từ dữ liệu — vì OHLC
của bất kỳ khung nào (kể cả 5m) cũng không tự nó nói được biến động thật đã đi theo hướng nào trước
trong nội bộ nến đó.

**Thực nghiệm thật xác nhận cả hai vế, chạy 2 lần với CÙNG một OHLC 1H, chỉ khác cờ `--timeframe-detail`:**
Dựng 1 cặp tổng hợp, 1 lệnh long mở tại giờ 01:00 (giá 100), sang giờ 02:00 giá dao động mạnh trong
đúng MỘT nến 1H: 5 phút đầu tăng lên 105 (đủ đạt ROI 1%, `minimal_roi={"0":0.01}`, dư biên độ để trừ
phí), sau đó sập xuống 85 ở phút 25-30 (chạm `stoploss=-0.10`). Nến 1H gộp: `open=100 high=105 low=85
close=90`.

| Chạy | `--timeframe-detail` | `exit_reason` | `profit_ratio` | `close_date` |
|---|---|---|---|---|
| A | *(không có)* | **stop_loss** | **-0.1018** | 2024-01-01 02:00:00 |
| B | `5m` | **roi** | **+0.00998** | 2024-01-01 02:00:00 |

Cùng một nến 1H, cùng một chiến lược, cùng một lệnh — CHỈ đổi cờ `--timeframe-detail` mà kết quả đảo
hoàn toàn từ LỖ 10,18% (stop_loss) sang LÃI ~1% (roi). Không có `--timeframe-detail`: Freqtrade coi cả
giờ là MỘT đơn vị, áp policy "Stoploss trước ROI" trên `low=85`/`high=105` của cả giờ → chọn stop_loss
dù giá thật đã đạt ROI SỚM HƠN rất nhiều so với lúc chạm đáy. Có `--timeframe-detail 5m`: nến 5m đầu
tiên (02:00-02:05, high=105) đã tự đủ để đóng lệnh bằng ROI — vòng lặp không bao giờ đi tới nến 5m sau
đó (02:25-02:30) nơi giá sập, vì lệnh đã đóng từ trước.

**Kết luận đối chiếu spec (D5):** *"thứ tự khớp khi nhiều mức giá cùng nằm trong một nến 1H tôn trọng
dòng 5m"* — ĐÚNG **giữa các nến 5m khác nhau** trong cùng giờ (đây chính là cơ chế `timeframe_detail`
tồn tại để giải quyết). **Chưa đúng theo nghĩa tuyệt đối bên trong một nến 5m đơn lẻ** — nếu SL và
ROI/TP cùng rơi vào đúng MỘT nến 5m (5 phút), Freqtrade vẫn áp policy cố định (Stoploss trước). Với
Tool D, đây là rủi ro dư (residual risk) đã thu hẹp đáng kể (từ cửa sổ mơ hồ 1H xuống 5m) chứ không
triệt tiêu hoàn toàn — cần ghi vào phần "giới hạn đã biết" khi D3.5/D4 dùng kết quả backtest có
tranche/SL/TP sát nhau về giá.

---

## 8. Việc cần làm khi implement thật (không phải việc của TD-0028, ghi lại để không quên)

- Khi viết `custom_stoploss`/`adjust_trade_position` thật (sau D0-PRE): thêm assert nội bộ `trade.id != 0` (hoặc `trade.id is not None`) trước MỌI lần gọi `set_custom_data`/`get_custom_data` — vá lỗ hổng ở mục 4.2.
- L-Z49 (test đơn vị D7, spec dòng 3979-3984) nên thêm kịch bản: hai trade MỞ ĐỒNG THỜI (hai cặp khác nhau), xác nhận `custom_data` của chúng KHÔNG trộn lẫn — không chỉ kiểm một trade duy nhất qua nhiều callback như spec mô tả tối thiểu.
- E1 (`run_backtest.py`) khi có logic thật, phải gọi qua đường `Backtesting.backtest()` cấp cao (đi qua `reset_backtest()`) — không tự ý gọi thẳng các hàm nội bộ như `_enter_trade`/`_check_adjust_trade_for_candle` để "tối ưu tốc độ", vì sẽ bỏ qua bước reset và vi phạm mục 4.3.
- D2c (`gap_ms` thật) và tỉ lệ khớp post-only — đo ở D3.5 (Bước 2, testnet) và D10, không đo được ở D0-PRE (đọc mã nguồn không thay thế được đo thật, theo đúng phân loại "Giai đoạn DUY NHẤT verify được" của bảng §9b.2).
- (TD-0113) Rủi ro dư: SL và ROI/TP cùng rơi vào ĐÚNG một nến 5m vẫn bị `timeframe_detail` xử lý theo policy cố định (Stoploss trước ROI), không phải chronology thật — nếu D4/D3.5 sau này cần độ chính xác cao hơn 5m cho việc so khớp tranche sát giá nhau, cân nhắc `timeframe_detail=1m` (đắt hơn về thời gian chạy) thay vì coi 5m là đủ tuyệt đối.
