# DR-SHORT-02 — Mở lại khâu ĐO Short bằng công tắc CHUNG `tier_a.enable_short` (ghi đè có ý thức)

> **Ngày chốt:** 24/09/2026 · **Người quyết:** chủ dự án (trả lời `MT-83`, **xác nhận hai lần**, lần hai sau khi được
> báo hệ quả đo trên đĩa) · phiên mã `12c579bc` thi hành. Khuyến nghị của phiên thi hành là **công tắc riêng** cho
> ứng viên; chủ dự án chọn khác, và DR này ghi đúng quyết định đó.
> **Chi phí:** 0 trial. Mã `DR-SHORT-02` + `TD-0399` đặt chỗ bằng commit `9ce15cd` (N12 mục 7c). Commit **RIÊNG và
> TRƯỚC** `TD-0402` (lật khoá).

> 🔴 **PHIÊN IDEA/CHỌN KHÔNG ĐỌC FILE NÀY** (`DR-009`): soạn bởi một phiên đã thấy số đo của Tool D.

---

## 1. Bối cảnh

`IQ-0003` (SELECTED `729e27f`) là rổ trung tính notional: luôn có **chân Short** song song chân Long. Công tắc Short
của cả hệ thống đang tắt: `config/tool_d_config.yaml:29` `enable_short: false`. `DR-SHORT-01` §2 tách Short làm
*D-dựng* (✅ đã làm) và *D-đo* (⏸). `DR-HUONG-01` §3 và `DR-D4-01` §2b viết điều kiện mở D-đo **trước**.

`MT-83` hỏi: chân Short của `IQ-0003` bật bằng công tắc riêng của ứng viên, hay bằng công tắc chung
`tier_a.enable_short`? Chủ dự án chọn **công tắc chung**.

## 2. Quyết định

1. **`tier_a.enable_short` là công tắc Short DUY NHẤT của hệ thống**, dùng chung cho `ZoneAbsorption` và chiến lược
   rổ của `IQ-0003` (`TD-0400`). Không thêm khoá riêng cho ứng viên.
2. **Lật khoá thành `true` là việc của `TD-0402`**, làm sau khi DR này commit, và **sau khi chủ dự án chọn lúc khởi động
   lại bot dry-run** (§4 điều 1).
3. **Đây là GHI ĐÈ, khai thẳng, không giả vờ điều kiện đã thoả.** Khi khoá bật, ZA SHORT được mở lệnh ở **dry-run D11**
   dù các điều kiện D-đo sau **CHƯA đạt**:
   - `DR-HUONG-01` §3: ý tưởng (d) có kết cục tại cổng, và có DR viết trước khi đo để tách lợi thế khỏi xu hướng giai đoạn;
   - `DR-D4-01` §2b: DG7 có ngưỡng riêng đã calibrate · Δ_R(SHORT) `ok` đã commit · còn ≥ 9 suất.

   Tiền lệ cùng dạng: `DR-IQ-03` §2, `DR-D4-19` — ghi đè một điều kiện viết trước, **khai là ghi đè**.

## 3. Cái gì KHÔNG bị ghi đè

- **Khâu đo tính suất của ZA SHORT vẫn khoá bằng máy.** `L-Z56` (`kiem_cong_d35()`, `src/tool_d/dr015/cong_d35.py:111`)
  vẫn từ chối mọi lần chạy ablation khi `enable_short: true` mà thiếu Δ_R(SHORT) `ok`. DR này **không sửa**
  `L-Z56`, `cong_d35.py`, hay artifact niêm phong D3.5. Hệ quả: khi khoá bật, **mọi** lần chạy E3 (kể cả của ZA LONG)
  bị chặn tới khi có Δ_R(SHORT). ZA LONG đã `retest_forbidden` (`DR-ZA-01`) nên không mất gì. `IQ-0003` không đi qua
  ablation D3.5 theo hình dạng của ZA; thước đo sai lệch cho chân Short của nó là câu (2) của `MT-83`, trả lời trong
  `DR-D0-IQ0003`.
- `DR-ZA-01` (ZA LONG bị loại, `retest_forbidden`) giữ nguyên.
- Kết quả dry-run của ZA SHORT **không** là bằng chứng lợi thế, không vào `N`, không vào phán quyết nào của D0.9. Nó chỉ
  là dữ liệu vận hành (lệnh Short có đặt/khớp/đóng đúng không).

## 4. Hệ quả đã biết — chấp nhận có ý thức

1. **Bot dry-run D11 đang chạy `ZoneAbsorption`** (`src/tool_d/ops/dry_run.py:39`), đọc đúng khoá này
   (`user_data/strategies/ZoneAbsorption.py:353`, đọc lúc khởi tạo). Sau lần khởi động lại đầu tiên kể từ khi bật, ZA
   **mở lệnh Short** trên dry-run, chung `E_D`, chung trần lệnh, chung thang drawdown với Long (`DR-SHORT-01` §4).
   Futures one-way: cặp đang mở Long thì tín hiệu Short trên cặp đó bị bỏ, và ngược lại.
2. **Tải API tăng.** Khi `enable_short` bật, `informative_pairs()` khai thêm `(pair, khung_funding, "funding_rate")`
   cho **mọi** cặp (`TD-0328`). Tần suất gọi `fetchFundingRateHistory` ở live **chưa đo**; pool ~100 cặp có nguy cơ
   chạm giới hạn API Binance. Dòng `TD-0328` ghi điều kiện: đọc log dry-run/testnet **trước** khi mở `enable_short`.
   DR này không đợi được điều kiện đó (đo chỉ có được sau khi bật), nên thay bằng điều kiện đảo ngược ở §5.
3. **Một test khoá phải đổi khẳng định.** `tests/lock/test_td0321_duong_short_backtest_that.py::…::
   test_ghim_enable_short_false_trong_yaml_that` ghim `False` và nêu đích danh quyết định cũ. `TD-0402` đổi dòng đó
   thành ghim `True` **và nêu `DR-SHORT-02`** — không xoá test.
4. **Đường Long của ZA không đổi một bit** khi Short bật (`test_td0321`: *"YAML thật trên cùng dữ liệu …"*). `TD-0402`
   phải chạy lại đúng các ca đó sau khi lật khoá.

## 5. Điều kiện dừng / đảo ngược (viết TRƯỚC)

- Trong **24 giờ đầu** sau khi bot dry-run khởi động lại với khoá bật: thấy lỗi giới hạn API (HTTP 429/418, *"Too many
  requests"*, bị ban IP) trong log ⇒ **lật khoá về `false`**, khởi động lại, ghi `docs/research-log.md`, báo chủ dự án.
  Lật về vì lý do này **không** cần DR mới.
- Bất kỳ lệnh Long nào của ZA lệch hành vi so với trước khi bật (mã, giờ mở, lý do đóng) trên fixture test ⇒ **dừng**
  `TD-0402`, không merge.
- Cần sửa `L-Z56`, `cong_d35.py` hay artifact niêm phong để đi tiếp ⇒ đó là mở khâu đo tính suất của ZA SHORT, **ngoài**
  phạm vi DR này ⇒ **dừng**, cần DR riêng.

## 6. Điểm yếu — khai thẳng

- Quyết định được đưa ra **sau** khi đã thấy kết quả ZA LONG — đúng hình dạng mà `DR-HUONG-01` §3 viết trước để chặn.
  Đối trọng duy nhất còn lại là máy (`L-Z56`) và §3: dry-run không sinh con số được tính cho phán quyết nào.
- Một công tắc cho hai chiến lược nghĩa là **không thể** bật Short cho `IQ-0003` mà giữ ZA ở Long-only. Muốn tách về sau
  ⇒ cần DR mới + khoá riêng.

## 7. Không thuộc DR này

- Không lật khoá (việc của `TD-0402`). Không sửa mã chiến lược nào.
- Không calibrate DG7/DG6-A cho Short, không đo Δ_R(SHORT), không chạy lại phễu tín hiệu Short.
- Không sửa chữ của `DR-SHORT-01`, `DR-HUONG-01`, `DR-D4-01`. Dòng đính chính trỏ về DR này sẽ nối cuối chúng khi có lệnh
  "chuẩn hóa và lưu" cho `back-end-note.md` (`MT-83` → ✅ đã thi hành).
