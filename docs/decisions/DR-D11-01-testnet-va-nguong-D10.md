# DR-D11-01 — Môi trường verify D2 tại D10, và ba ngưỡng chấp nhận

> **Ngày chốt:** 13/09/2026 · **Người quyết:** chủ dự án · **Việc:** TD-0243 (Khối 18)
> 🔒 **File này phải commit RIÊNG và TRƯỚC mọi dòng mã đo D10.** `spec:2962-2963` (L-Z35): ngưỡng
> chấp nhận điền **TRƯỚC khi chạy D10, KHÔNG sau khi thấy số** — cùng khuôn DR-D35-01/DR-D3-01.

---

## 1. Vì sao khối này tồn tại — testnet-qua-Freqtrade đã bị loại TRƯỚC TD-0243, không phải do DR này

`spec:4480` giả định testnet *"dựng ở D3.5, dùng lại nguyên vẹn cho D10"*. `DR-D35-01` (08/09/2026)
đã **loại** testnet cho Bước 2 của D3.5 — nhưng vì một lý do hẹp (sổ lệnh testnet mỏng, không đại
diện cho xác suất khớp thật) và **không cần chạy Freqtrade** cho phép đo đó. D10 là chuyện khác hẳn:
D10 cần quan sát **hành vi của chính con bot** (huỷ+đặt lại SL, tranche khớp, tỉ lệ post-only) —
không đo được nếu Freqtrade không chạy được trên testnet.

Và Freqtrade **không chạy được** trên Binance testnet, đã xác nhận bằng đọc mã nguồn từ trước
(`TD-0116`, 07/09/2026): `exchange/binance.py:52` đặt `"supports_demo_trading": False` **cố ý**
(*"Intentionally Disabled — it's a separate market"*), `exchange.py:884-890` raise
`ConfigurationError` nếu bật. `ccxt` bên dưới có `set_sandbox_mode` nhưng Freqtrade không bao giờ
gọi. Đây không phải phát hiện mới của TD-0243 — nó đã nằm trên đĩa từ trước D3.5, nhưng chưa ai nối
nó với D10/D11 cho tới khi rà soát Khối 18.

`D2b` cũng đã đóng bằng đọc mã nguồn (`TD-0028`, `docs/freqtrade-source-read.md` mục 2): Freqtrade
**không** có đường `closePosition=true` cho stop order Binance Futures — không có lối tắt nào tránh
được việc đo `gap_ms` thật (D2c).

**Kết luận:** phương án (a) của `spec:2938-2943` (set sandbox URL) không thể thực thi cho cả ba phép
đo D10 (D6, D2c, tỉ lệ post-only) — cả ba đều cần Freqtrade chạy thật và/hoặc sổ lệnh thật. Vá
Freqtrade để ép sandbox mode (bật `set_sandbox_mode` cục bộ) chỉ có thể giúp D2c một phần (cơ chế
timing nội bộ ít phụ thuộc độ sâu sổ lệnh hơn), còn D6 và tỉ lệ post-only vẫn cần dữ liệu sổ lệnh
thật — nghĩa là vẫn phải làm lệnh live sau đó, và bản vá tạo thêm một nguồn sự thật thứ hai cho tầng
sàn (vi phạm LD-09, đúng thứ câu hỏi mở #24 của spec đã cảnh báo). Không đáng.

## 2. QUYẾT ĐỊNH A — Verify D2/D10 bằng lệnh live tối thiểu (phương án (b) của `spec:2945-2952`)

Chủ dự án chốt 13/09/2026: đi thẳng phương án (b), không thử vá Freqtrade. Điều kiện *"CHỈ khi (a)
xác nhận không khả thi"* (`spec:2945`) đã thoả — (a) bị loại bằng bằng chứng mã nguồn, không phải
suy đoán.

Mục đích **duy nhất**: verify cơ chế đặt/sửa lệnh (D2c), đo lệch khớp tranche thật (D6), đo tỉ lệ
khớp post-only (LD-12). **Không** phải để kiểm chiến lược — đúng ranh giới `spec:2949-2952` vạch
giữa "verify hành vi sửa lệnh SL" và "dry-run thay cho testnet".

## 3. QUYẾT ĐỊNH B — Siết bảo mật tài khoản phụ NGAY trước khi đặt lệnh live tối thiểu

`TD-0116` (07/09/2026) đã ghi hai rủi ro tồn dư, chấp nhận có ý thức nhưng lịch siết là **"trước
D11"**: IP whitelist đang "Không giới hạn" (IP nhà mạng VN động), Universal Transfer đang BẬT.

Vì Quyết định A đưa tiền thật vào sớm hơn kế hoạch — ngay ở D10, không phải D11/D12 — chủ dự án
chốt 13/09/2026: **siết cả hai NGAY trước khi đặt lệnh live tối thiểu của D10**, không đợi tới D11.
IP whitelist xử bằng dải IP nhà mạng hoặc bật ngay trước phiên đặt lệnh rồi xác minh lại (không thể
whitelist một IP tĩnh vì ISP cấp IP động); Universal Transfer tắt hẳn.

## 4. 🔴 Phát hiện quy mô — "lệnh live tối thiểu" KHÔNG đồng nghĩa "một lệnh"

Đọc lại `spec:2966` và `TD-0244`: D10 đòi phân bố `gap_ms` qua **≥ 30 lần đổi khối lượng SL** — mỗi
lần đổi khối lượng SL tương ứng một tranche 2/3 khớp (tranche 1 không đổi khối lượng SL, nó là lần
đặt đầu). Một vị thế DCA đầy đủ (3 tranche) cho tối đa 2 sự kiện đổi khối lượng (khi tranche 2, rồi
tranche 3 khớp) — **không phải mọi vị thế đều bơm tới tranche 3** (ghi nhận từ TD-0182: ablation D4
đo được chỉ ~21% lệnh bơm đủ ba tranche trên dữ liệu EXPLORE). Quy đổi thô: cần khoảng **15-30 vị
thế DCA thật** (không phải 15-30 lệnh notional tối thiểu một lần) mới có cơ hội chạm mốc 30 sự kiện,
và mỗi vị thế cần thời gian tồn tại thật để tranche 2/3 kích hoạt hay bị TIME_STOP.

**Đây KHÔNG phải một quyết định của DR này — đây là phát hiện cần trình lại chủ dự án**, vì nó đổi
bản chất của "lệnh live tối thiểu" từ *một hành động xác nhận cơ chế* thành *một giai đoạn vận hành
tối thiểu kéo dài*. Chủ dự án đã chốt khuôn **"giống D3.5 Bước 2"** (cửa sổ 14 ngày, gia hạn đúng 1
lần, không đủ thì xử fail-closed, không ép thêm vị thế cho đủ số) — **nhưng một phép đo độc lập từ
phiên `-3f` (đang soạn `DR-D11-02` cho MT-39) đến SAU khi chốt khuôn này đã làm khuôn đó vô hiệu**:
tốc độ TỰ NHIÊN sinh sự kiện đổi khối lượng SL đo được trên dữ liệu thật chỉ **~12 lần / 50 mã-năm**,
quy đổi **~24 lần/năm** cho pool 102 mã — nghĩa là cần **~15 THÁNG** vận hành tự nhiên mới tự nhiên
đủ 30 mẫu, không phải 14 ngày. 14 ngày (khuôn D3.5 Bước 2) được thiết kế cho một tốc độ sự kiện khác
hẳn (chạm zone), không áp dụng được cho sự kiện đổi khối lượng SL.

🔴 **Mục này QUAY LẠI trạng thái CHỜ, ghi đè lên quyết định "giống D3.5 Bước 2" ở trên** — không
phải vì quyết định đó sai lúc chốt (thông tin ~15 tháng chưa có lúc đó), mà vì dữ liệu mới xuất hiện
ngay sau đó. `-3f` đang mang đúng câu hỏi này (có "cưỡng bức sinh sự kiện" trên môi trường đo hay
không, khai rõ là đo cơ chế chứ không phải đo chiến lược) lên chủ dự án qua `DR-D11-02`, vì ngưỡng/
cách đo D2c của Mục 5.2 dưới đây phụ thuộc trực tiếp câu trả lời đó. **Không hỏi trùng ở đây** —
chờ `DR-D11-02` commit xong rồi Mục 4 + 5.2 mới chốt, tránh hai phiên hỏi chồng cùng một quyết định
(N12 mục 6). D6 (§5.1) và tỉ lệ post-only (§5.3) KHÔNG phụ thuộc số sự kiện đổi SL — mỗi tranche
khớp đều sinh một điểm dữ liệu cho hai chỉ số đó bất kể có tới tranche 3 hay không, nên hai ngưỡng
đó vẫn chốt được độc lập với câu hỏi quy mô này.

## 5. Ba ngưỡng chấp nhận D10 (điền TRƯỚC khi chạy, `L-Z35`)

Nguyên tắc chung: **không bịa ngưỡng mới từ số không** — cả ba đều neo vào một con số ĐÃ NIÊM PHONG
hoặc đã được chính spec/TD trước đó nêu ra, tránh đúng loại lỗi `N6`/`DR-D35-01` §2 cảnh báo ("một
con số tự tin nhưng sai nguy hiểm hơn một ô trống").

### 5.1 D6 — lệch khớp tranche (bps/đơn vị R)

**Ngưỡng: D10 P90(lệch-mỗi-lệnh) ≤ Δ_R đã niêm phong ở D3.5** (`docs/du-lieu-do/dr015-buoc1-delta-r.json`,
TD-0161/TD-0165): **LONG = 0,161206 R**. Short dùng lại giá trị LONG (quy ước đã chốt ở DR-D35-01
§4, vì Short hiện `unreadable`) cho tới khi có lệnh Short thật.

Đo bằng ĐÚNG phương pháp DR-D35-01 §4 (`lệch_R = (fill_price − p_i) / planned_risk_usdt`, đóng băng
tại tranche 1, tranche ≥2 mới tính), để hai con số **so được với nhau, không phải hai thước khác
nhau**.

**PASS:** D10 P90 ≤ 0,161206 R (Long) — biên hiệu chỉnh D3.5 vẫn đủ.
**FAIL → L2 (`§11b.1`), KHÔNG tự lấy số D10 làm số mới:** D10 P90 > 0,161206 R nghĩa là thước đã
đổi giữa hai lần đo (`spec:2977-2979`), đúng phân loại "sai CẤU TRÚC" của `§11b.1` — xử bằng ablation
arm mới, tốn 1 slot Ngân sách A + lockbox mới. Không tự phán ở đây; trình chủ dự án.

### 5.2 D2c — `gap_ms` (khoảng trống không-SL trên sàn)

⚠️ **Phụ thuộc `DR-D11-02` (MT-39, phiên song song đang soạn):** ngưỡng này chỉ có nghĩa nếu SL
sống thật trên sàn (phương án (a) mà phiên đó vừa chốt). Nếu `DR-D11-02` đổi hướng, mục này phải
viết lại — đã báo phiên đó, không tự đoán thay họ.

**Ngưỡng: p99(gap_ms) qua ≥30 sự kiện đổi khối lượng SL ≤ 15.000 ms.** Neo vào chính rủi ro
`TD-0116` đã đo và tự nhắc *"cần nhớ khi chốt `L_exchange`"*: `PROCESS_THROTTLE_SECS` = 5s
(`TD-0028`) là nền, cộng round-trip đặt lại SL; latency mạng LẠNH đo được có mẫu tới 11 giây
(14/30 mẫu > 1s). 15 giây là đúng con số `TD-0116` đã tự nêu làm ranh giới rủi ro, dùng lại — không
phải hằng số mới.

**PASS:** p99 ≤ 15.000 ms → `L_exchange` (hiện 3×, `DR-D0PRE-06`) giữ nguyên.
**FAIL:** p99 > 15.000 ms → theo đúng `spec:2920` fallback đã ghi sẵn: **hạ `L_exchange`** hoặc
**ghi rủi ro tồn dư vào DR** — KHÔNG thiết kế lại §6. Chọn nhánh nào là quyết định của chủ dự án tại
thời điểm đó, không tự chọn trước.

### 5.3 Tỉ lệ khớp post-only (LD-12)

**Tham chiếu: `p_nf_cao` = 0,0% đã niêm phong ở Bước 2 DR-015** (`docs/du-lieu-do/dr015-buoc2-ty-le-khong-khop.json`,
TD-0162, 91 lượt CALIB, suy từ dữ liệu khớp lệnh thật). Số đó tự khai **KHÔNG quan sát được** ba lỗ
mù: lệnh bị sàn từ chối do post-only, khớp một phần, vị trí hàng đợi (`DR-D35-01` §3.3) — đúng ba
thứ D10 lần đầu tiên đo được thật, vì nó đặt lệnh thật thay vì suy luận.

**Không đặt một ngưỡng % tuỳ ý** (cùng tinh thần cấm ở DR-015 §4: *"ngưỡng tuỳ tiện là chỗ uốn kết
luận sau khi thấy số"*). Thay vào đó:

- D10 NO_FILL/khớp-một-phần quan sát được **≈ 0%** (trong biên sai số của cỡ mẫu D10, luôn nhỏ hơn
  nhiều so với 91 của Bước 2) → phù hợp bước đầu với tham chiếu 0,0%, tiếp tục D11 bình thường.
- D10 quan sát được **BẤT KỲ** NO_FILL/khớp-một-phần nào → bằng chứng trực tiếp rằng ít nhất một
  trong ba lỗ mù là thật, không phải giả thuyết. Ghi vào `docs/research-log.md` kèm provenance, đối
  chiếu lại giả định NO_FILL=0 đang ẩn trong `§10.2`/Nhánh 2, và coi là ứng viên L2 (`§11b.1`) —
  KHÔNG tự phán mức độ nghiêm trọng, trình chủ dự án kèm số liệu thật.

## 6. Liên kết

- Nguồn: `tool-d-smart-dca.md` §9b.1-9b.4 (dòng 2898-2997), roadmap D10/D11 (dòng 4492-4504), câu
  hỏi mở #24/#25 (dòng 5067-5068).
- Testnet-qua-Freqtrade bị loại: `docs/research-log.md` 07/09/2026 (TD-0116), `docs/freqtrade-source-read.md`
  mục 2 (TD-0028, D2b).
- Δ_R niêm phong: `docs/du-lieu-do/dr015-buoc1-delta-r.json` (TD-0161/165), đối chứng
  `dr015-buoc3-doi-chung-z0.json` (TD-0163).
- `p_nf` niêm phong: `docs/du-lieu-do/dr015-buoc2-ty-le-khong-khop.json` (TD-0162), quyết định nền
  `DR-D35-01`.
- Phụ thuộc: `DR-D11-02` (MT-39, SL trên sàn) cho mục 5.2. Nếu đổi hướng, sửa mục 5.2 tại đây —
  không tạo DR thứ ba trùng phạm vi (N12 mục 6).
- Mục 4 (quy mô/thời lượng) **CHƯA chốt** — chờ xác nhận chủ dự án trước khi viết entrypoint đặt
  lệnh live.
