# DR-D11-02 — SL sống trên sàn (bật `stoploss_on_exchange`), và định nghĩa đo `gap_ms`

> **Ngày chốt:** 13/09/2026 · **Người quyết:** chủ dự án · **Việc:** MT-39 (back-end-note mục 7), TD-0244
> 🔒 **Commit RIÊNG và TRƯỚC mọi dòng mã.** Cùng khuôn DR-D4-01…DR-D4-10.
> Soạn với sự tham gia rà soát chéo của hai phiên Claude Code song song khác trên cùng repo
> (N12 mục 6 — đã báo tên file này trước khi viết, không trùng tài liệu nào đang soạn dở).

---

## 1. Cái đang hỏng (MT-39)

`config/freqtrade/config.json` đặt `stoploss_on_exchange: false`, với chú thích tại chỗ:
*"vì `custom_stoploss` (§0c.1) xử lý nội bộ, không đẩy SL lên sàn"*. Trong khi đó §6.6(1)
(`tool-d-smart-dca.md:1955-1957`) viết: *"SL SỐNG TRÊN SÀN. KHÔNG BAO GIỜ viết kiểu bot theo
dõi giá rồi gửi lệnh đóng khi chạm SL — cơ chế đó chết cùng tiến trình"*. `ZoneAbsorption.py:972`
thi hành đúng cơ chế nội bộ mà §6.6(1) cấm.

## 2. 🔑 Phát hiện thay đổi cách đóng khung cả vấn đề: đây KHÔNG phải một đánh đổi thiết kế

Chú thích trong `config.json` sai về mặt kỹ thuật. Đọc mã nguồn Freqtrade 2026.8:

- `interface.py:1566-1582` (`ft_stoploss_adjust`) ghi giá trị trả về của `custom_stoploss()`
  vào `trade.stop_loss` bất kể `stoploss_on_exchange` bật hay tắt.
- `trade.stoploss_or_liquidation` đọc lại đúng giá trị đó.
- `freqtradebot.py:1512` (`create_stoploss_order`) dùng `stop_price=trade.stoploss_or_liquidation`
  khi tạo lệnh trên sàn.

Tức "`custom_stoploss` xử lý nội bộ" và "đẩy SL lên sàn" **không loại trừ nhau** — chúng là hai
nửa của cùng một luồng dữ liệu. Grep `stoploss_on_exchange` toàn bộ `tool-d-smart-dca.md` (v8):
**0 kết quả** — đặc tả gốc chưa từng yêu cầu tắt cờ này. Dòng `false` trong config nhiều khả năng
là lỗi triển khai không khớp spec (khuôn `DR-012 Hạng 1`), không phải một quyết định kiến trúc đã
cân nhắc trade-off. Ghi lại thành DR ở đây vì hậu quả vận hành đủ lớn (rủi ro tiền thật khi tiến
trình chết giữa lúc có vị thế), không phải vì bản thân việc sửa cần một trade-off mới.

## 3. Quyết định

### 3.1 Bật `stoploss_on_exchange: true`

Freqtrade sẽ tự huỷ + đặt lại lệnh `STOP_MARKET` trên sàn mỗi khi `custom_stoploss()` đổi giá trị
hoặc mỗi khi khối lượng vị thế đổi (D2a, đã xác nhận bằng đọc mã nguồn ở TD-0028,
`docs/freqtrade-source-read.md` mục 1). D2b (`closePosition=true`) đã xác nhận **không tồn tại**
trên Binance Futures qua Freqtrade — nhánh "khối lượng không cần đổi" của spec dòng 3175 không
áp dụng; khoảng trống cancel→recreate là có thật và phải đo, không thể loại bỏ (§3.3 dưới).

Việc triển khai (không thuộc phạm vi DR này, để dành cho lúc code TD-0244/liên quan):
- Sửa `config/freqtrade/config.json`: `stoploss_on_exchange: true` + xoá/sửa chú thích sai tiền đề.
- `order_types.stoploss` giữ nguyên `"market"` (đã đúng, ra `STOP_MARKET`/D2a).
- Không cần sửa `custom_stoploss()` — chữ ký hiện tại (không khai `after_fill`) là **đúng thiết
  kế, không phải thiếu sót** (xem §4).

### 3.2 `gap_ms` đo bằng MẪU GÂY RA (cưỡng bức sự kiện), không chờ tích luỹ tự nhiên

Đo trên dữ liệu thật (`docs/du-lieu-do/td0213-arm-dca-sau-va.json`, arm mặc định): tranche 1
không sinh sự kiện đổi khối lượng SL; TP1 cũng không sinh (Binance Futures:
`stoploss_blocks_assets = False` ⇒ Freqtrade **không** huỷ SL trước lệnh exit — xác nhận qua
`binance.py:58` + `freqtradebot.py:1101-1103,2145`). Nguồn duy nhất sinh `gap_ms` là **tranche 2
và 3 khớp** — hiếm hơn nhiều so với số lệnh mở, khiến tích luỹ tự nhiên trên roadmap hiện tại
chậm tới mức không thực tế cho một cổng chặn D11.

Spec đã tự trả lời câu này, không cần quyết định mới về NGUYÊN TẮC — chỉ cần đọc đúng chỗ
(`tool-d-smart-dca.md:2939-2942`, chính là phương án (a) của D2/D2c):

> *"Testnet — ưu tiên, 0 rủi ro tài chính: Set sandbox/testnet URL trong config Freqtrade, **tạo
> tranche GIẢ trên testnet, thử SỬA khối lượng lệnh SL**, quan sát Binance trả về gì … đây chính
> là bước thử THẬT, không suy đoán tiếp."*

và `spec:2966` chỉ đòi *"phân bố `gap_ms` qua ≥ 30 lần đổi khối lượng SL"* — không có chữ nào
buộc 30 lần đó phải đến từ giao dịch chiến lược thật. **Phân biệt với ngưỡng khác cùng con số
"≥ 30" trong dự án, để không áp nhầm kỷ luật:**

| Phép đo | Đo cái gì | Mẫu bắt buộc tự nhiên? |
|---|---|---|
| `DR-015` Bước 2 (tỉ lệ không khớp, `spec:3618`) | hành vi **THỊ TRƯỜNG** (lệnh có khớp không) | ✅ **PHẢI** — gây ra một lượt khớp thì đã trả lời hộ câu hỏi đang đo |
| D10 — phân bố `gap_ms` (`spec:2966`) | hành vi **CỦA MÁY** (Freqtrade huỷ rồi đặt lại mất bao lâu) | ❌ **KHÔNG** — máy không phân biệt tranche thật hay tranche cưỡng bức trên testnet |

**Quyết định:** `TD-0244` (bộ sinh `gap_ms`) đọc mẫu từ các lần đổi khối lượng SL cưỡng bức trên
môi trường đo (testnet, dựng ở `TD-0243`/`DR-D11-01`), khai rõ trong Decision Log là **đo cơ chế
hệ thống**, không phải đo hiệu năng chiến lược — cùng logic đã dùng cho CTRL/đo-thước ở `MT-08`:
không tính vào ngân sách nghiên cứu `N=114`, **0 trial**.

🔴 **Hạn chế tồn dư, PHẢI đọc kèm mọi báo cáo `p99(gap_ms)`:** mẫu cưỡng bức đo được **ĐỘ DÀI**
của khoảng trống cancel→recreate, nhưng **không** đo được **XÁC SUẤT** khoảng trống đó trùng với
lúc giá đang chạy ngược mạnh. Thiệt hại thật trên tiền thật là **tích** của hai đại lượng đó; mẫu
gây ra chỉ cấp một thừa số. Một `p99(gap_ms)` nhỏ và đẹp **không** có nghĩa là "cửa sổ an toàn" —
nó chỉ nói máy phản ứng nhanh, không nói gì về việc giá có kịp chạy trong lúc đó hay không. Không
khai rõ điều này thì con số dễ bị đọc quá tay.

⚠️ Cận trên latency thực đo được ở `TD-0116` (latency LẠNH, không phải cùng phép đo `gap_ms` này
nhưng cùng họ rủi ro): 14/30 mẫu > 1 giây, max 11 giây — tức cửa sổ không-SL-trên-sàn có thể vượt
xa cận trên lý thuyết `PROCESS_THROTTLE_SECS = 5s`. Ngưỡng chấp nhận số cho D10 (bao nhiêu ms là
đạt) thuộc phạm vi `DR-D11-01` (`TD-0243`), không phải DR này — DR này chỉ chốt **cơ chế đo là
gì** và **giới hạn của phép đo là gì**.

## 4. Vì sao KHÔNG cần thêm tham số `after_fill` vào `custom_stoploss()`

Giả thuyết ban đầu (một phiên song song đưa ra, đã tự kiểm và tự bác bằng đọc mã nguồn — ghi lại
để không ai đặt lại câu hỏi này): thiếu `after_fill` có thể khiến SL bị Freqtrade đặt tạm về mức
lưới cuối cứng ngay sau mỗi lần tranche khớp, cho tới vòng lặp kế tiếp.

**Đã bác bằng mã nguồn:** `persistence/trade_model.py:854`:
```python
if stoploss is None or (initial and not (self.stop_loss is None or self.stop_loss == 0)):
    return
```
Lệnh `trade.adjust_stop_loss(open_rate, strategy.stoploss, initial=True)` gọi ngay sau mỗi fill
(`freqtradebot.py:2407`) là **no-op** một khi `trade.stop_loss` đã được đặt lần đầu (luôn đúng từ
sau tranche 1). Không có cửa sổ nào SL bị hạ về lưới cuối giữa các tranche.

Về bản chất: `after_fill` tồn tại để **tính lại** SL khi giá vào trung bình đổi sau một lần fill.
D0.2 quy định giá SL (`kh.sl`) **bất biến theo zone**, không phụ thuộc giá vào trung bình — không
có gì để tính lại. Chữ ký hiện tại của `ZoneAbsorption.py:972` (không khai `after_fill`) là **đúng
thiết kế**; thêm nó vào sẽ mở một đường tính lại SL mà §0c.1 dòng 441 cấm tường minh (*"`custom_
stoploss` … nhưng KHÔNG dùng để dời SL"*).

## 5. Phát hiện phụ, ghi lại để không lặp lại việc kiểm tra

- **Lưới cuối hiệu dụng là `−0,99`, KHÔNG phải `−0,30`.** `ZoneAbsorption.py:233` khai `stoploss
  = -0.30` kèm lý luận về hệ số sàn stake, nhưng `resolvers/strategy_resolver.py:97-104` xác nhận
  thứ tự ưu tiên **Configuration → Strategy → default**; `config/freqtrade/config.json:39` đặt
  `-0.99` và **ghi đè** giá trị trong chiến lược. Khớp với `MT-41` và `test_td0171_*.py:33`. Đây
  là giá trị thật sự được đẩy lên sàn nếu `custom_stoploss()` không chạy được vì lý do nào đó (ví
  dụ exception bị nuốt — `MT-16`(vii)). Chú thích `:224-232` trong chiến lược đang lý luận trên
  một con số sai; cần sửa khi tới lượt động vào file đó, và nên có một test ghim `-0.99` (chưa có
  — grep `stoploss = -0.30` trong `tests/` = 0 kết quả).
- **LD-21 (`spec:2659-2662`) đòi Decision Log từ chối cứng bản ghi ENTRY thiếu
  `sl_on_exchange_confirmed == true`.** Trường này hiện có 0 dòng code (chỉ tồn tại trong spec) vì
  `TD-0239` (nối Decision Log vào sản xuất) vẫn 🔓 — chưa cấp bách, nhưng khi TD-0239 chạy, chọn
  phương án (a) ở DR này khiến ràng buộc đó **tự thoả**, không cần code thêm gì để giả trường đó.
- **Không có test khoá nào ghim `stoploss_on_exchange` ở trạng thái tắt** — grep
  `tests/` cho `stoploss_on_exchange` = 0 kết quả; `L-Z24` chỉ ghim `trailing_stop` ·
  `use_exit_signal` · `position_adjustment_enable` · `freqai` · `edge` · `protections`. Bật cờ
  này không thuộc ba điều kiện của §7.1 (khuôn sửa test khoá `L-Z58`).
- **Đính chính một câu trích dẫn sai trong `back-end-note.md:128` (MT-39):** câu viết *"`spec:4506`
  xếp §6.6 vào nhóm KHÔNG BAO GIỜ CẮT"* không đúng nguyên văn — `spec:4506-4508` liệt kê D0-PRE,
  D9.5, H16, H17, DG8, arm Z0-T1, cổng D3.5, DR-014, và không có §6.6. Đây là diễn giải, không phải
  chữ spec. Không đổi kết luận (§6.6(1) vẫn là lệnh cấm tường minh ở chỗ khác), nhưng khi mở
  APPEND cho MT-39 cần không lặp lại câu trích sai này.

## 6. Ranh giới với `DR-D11-01` (TD-0243, phiên khác đang soạn song song)

Để tránh "một Ý, hai file" (N12 mục 6):

- **DR-D11-02 (đây):** SL sống ở đâu · quyết định bật `stoploss_on_exchange` · định nghĩa
  `gap_ms` đo cái gì, đo bằng mẫu nào (cưỡng bức) · hạn chế tồn dư của phép đo đó. Bảng phân biệt
  hai loại "≥ 30" ở §3.2 là **bản gốc duy nhất** — `DR-D11-01` trỏ tới đây, không chép lại (N1).
- **`DR-D11-01`:** dựng môi trường đo (testnet hay lệnh live tối thiểu — quyết định đó thuộc phiên
  kia) · **ngưỡng chấp nhận số** cho cả ba phép đo của D10 (lệch khớp tranche D6, `gap_ms`, tỉ lệ
  khớp post-only), đọc `gap_ms` trên định nghĩa mẫu-gây-ra đã chốt ở §3.2 trên. **Tại thời điểm
  DR này được viết (13/09/2026), `DR-D11-01` CHƯA tồn tại** — `TD-0243` vẫn 🔓, chưa được chủ dự
  án bật đèn xanh trong phiên đang giữ nó. Không suy diễn nội dung của nó; đây chỉ là phân công
  phạm vi cho lúc nó được viết.

## 7. Điều DR này KHÔNG chốt

- **Không chốt ngưỡng số nào** cho `gap_ms` (bao nhiêu ms là đạt) — thuộc `DR-D11-01`.
- **Không chốt môi trường đo** (testnet vs lệnh live tối thiểu) — thuộc `DR-D11-01`/`TD-0243`.
- **Không tự sửa `MT-39` trong `back-end-note.md`** — theo N9, cần trả lời 3 câu hỏi trong chat
  và lệnh "chuẩn hóa và lưu" trước khi ghi (APPEND, không viết lại — Phụ lục B.5).
- **Không viết một dòng mã nào** — chờ "bắt đầu code" trong phiên đang giữ TD-0244.

## 8. Lịch sử

- **13/09/2026** — tạo; chủ dự án chốt phương án (a) (đẩy SL lên sàn) sau khi so ba đường (SL
  trên sàn / SL nội bộ + khai rủi ro / hai lớp SL); sau đó chốt tiếp cách đo `gap_ms` là cưỡng bức
  sự kiện trên môi trường đo, không chờ tích luỹ tự nhiên. Rà soát chéo bởi hai phiên Claude Code
  song song khác trên cùng repo (đọc mã nguồn Freqtrade 2026.8 trong image `docker-tests`, xác
  nhận độc lập D2a/D2b, bác một giả thuyết `after_fill`, phát hiện lỗi tiền đề trong chú thích
  config, phát hiện LD-21, phát hiện `-0.99` vs `-0.30`).
