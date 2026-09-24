# DR-D0-IQ0003 — Thiết kế D0 của ứng viên suất (d) `IQ-0003`: rổ funding chéo trung tính, cân lại hằng ngày

> **Ngày chốt:** 24/09/2026 · **Người quyết:** chủ dự án (chốt `MT-80`…`MT-83` và năm câu kỹ thuật 24/09/2026) · phiên mã
> `12c579bc` soạn và thi hành.
> **Chi phí:** 0 trial. Mã `DR-D0-IQ0003` + `TD-0394` đặt chỗ bằng commit `9ce15cd` (N12 mục 7c). Commit **RIÊNG và
> TRƯỚC** mọi dòng mã chiến lược (`TD-0400`).
> **Trạng thái:** §1–§9 CHỐT. §10 còn ba câu mở, phải chốt **trước suất trial đầu tiên** của slot `IQ-0003`, không chặn
> việc dựng mã.

> 🔴 **PHIÊN IDEA/CHỌN KHÔNG ĐỌC FILE NÀY** (`DR-009`).
> 🔴 **Phiên soạn đã nhiễm: DR này chỉ DỊCH tờ chọn sang máy, không đánh giá ý tưởng, không thêm biến thể.** Chỗ nào tờ chọn
> mơ hồ, cách đọc do chủ dự án chốt và được ghi là **DIỄN GIẢI**.

---

## 1. Ứng viên

`IQ-0003` SELECTED `2026-09-24T14:07:20Z` (`729e27f`), slot `A-Q4-2026-01`, `so_bien_the: 1`, `overlaps_with:
["IQ-0002"]`. Nguồn sự thật là bốn trường cửa CHỌN trong `registry/idea_queue.jsonl` (`tin_hieu`, `quy_tac`,
`nguong_bac_bo`, `so_bien_the`). DR này **không chép lại** chúng, chỉ ánh xạ sang tham số và mã.

## 2. Tham số (N4) — không đổi `N = 114`

Tất cả nằm ngoài `tier_b`, nên `|tier_b|` vẫn 12 và `N` vẫn 114 (`src/tool_d/config/dof.py`). Chống tinh chỉnh ngầm là việc
của `DR-BIEN-THE-01`: đổi **bất kỳ** khoá nào dưới đây sau suất đầu tiên là biến thể thứ hai, vượt `so_bien_the: 1` ⇒ máy chặn.

| Khoá | Giá trị | Từ đâu trong tờ chọn |
|---|---|---|
| `tier_c.ro_funding.ro_cua_so_gio` | `72` | *"9 kỳ chốt gần nhất (3 ngày)"* — xem §3 điều 2 (DIỄN GIẢI) |
| `tier_c.ro_funding.ro_ty_le_k` | `0.20` | *"k = max(3, làm tròn xuống 20% …)"* |
| `tier_c.ro_funding.ro_k_toi_thieu` | `3` | như trên |
| `tier_c.ro_funding.ro_so_coin_toi_thieu` | `6` | *"Pool có dưới 6 coin đủ điều kiện thì không mở rổ"* |
| `tier_c.ro_funding.ro_gio_can_ro_utc` | `0` | *"nến 1H mở lúc 00:00 UTC"* |
| `tier_c.ro_funding.ro_stop_tham_hoa_pct` | `25` | *"đi ngược 25% so với giá vào"* |
| `tier_c.ro_funding.ro_don_bay` | `1` | *"đòn bẩy 1x mỗi chân"* |
| `tier_a.von_ro_usdt` | `null` → điền theo §10 câu (c) | vốn riêng của rổ (chủ dự án chốt 24/09/2026) |
| `tier_a.enable_long` / `tier_a.enable_short` | dùng chung (`DR-SHORT-02`) | rổ cần cả hai chân |

`tier_a.von_ro_usdt: null` ⇒ chiến lược **từ chối chạy** (fail-closed), không lấy mặc định.

<!-- DR-BIEN-THE-01:KHOA:BEGIN -->
```json
{"slot": "IQ-0003", "khoa": ["tier_a.enable_long", "tier_a.enable_short", "tier_a.von_ro_usdt", "tier_c.ro_funding.ro_cua_so_gio", "tier_c.ro_funding.ro_ty_le_k", "tier_c.ro_funding.ro_k_toi_thieu", "tier_c.ro_funding.ro_so_coin_toi_thieu", "tier_c.ro_funding.ro_gio_can_ro_utc", "tier_c.ro_funding.ro_stop_tham_hoa_pct", "tier_c.ro_funding.ro_don_bay"]}
```
<!-- DR-BIEN-THE-01:KHOA:END -->

## 3. Tín hiệu

1. **Thời điểm cân rổ:** mỗi ngày, lệnh khớp tại **giá mở nến 1H 00:00 UTC**. Theo cơ chế Freqtrade (tín hiệu trên nến đã
   đóng, khớp ở giá mở nến kế tiếp), tín hiệu đặt trên nến 1H mang nhãn `23:00`, nến đó đóng lúc `00:00`. Dữ liệu dùng:
   mọi dòng funding có `date ≤ 00:00` của ngày cân rổ. Kỳ chốt `00:00` đã biết tại `00:00`, nên không nhìn trước.
2. **Chỉ số xếp hạng (DIỄN GIẢI, chủ dự án chốt):** **TỔNG** funding rate của mọi kỳ chốt có `date` trong
   `(t − 72h, t]`. Đo trên đĩa: ở `pool_t1` có 43/107 mã chốt mỗi 4h, 54 mã mỗi 8h, số còn lại hỗn hợp. "9 kỳ" và "3 ngày"
   chỉ trùng nhau với mã 8h; trung bình mỗi kỳ sẽ xếp mã 4h thấp hơn thật. Tổng trong 72h là khoản funding thật một vị thế
   trả trong 3 ngày, đúng vế *"3 ngày"* và đúng cơ chế *"ai trả tiền"* của tờ chọn.
3. **Đủ điều kiện:** mã nằm trong `pair_whitelist` của lần chạy (rổ của giai đoạn, `ro_cho_tap()`,
   `src/tool_d/pool_giai_doan.py`), **và** dòng funding đầu tiên của mã có `date ≤ t − 72h` (tờ chọn: *"chưa đủ 9 kỳ …
   thì không xếp hạng"*, đọc theo điều 2), **và** có nến 1H tại `t`. BTC, ETH và mã EXPLORE bị loại tường minh trong mã,
   dù `pool_t*.yaml` đã loại sẵn (chốt kép, rẻ).
4. **Nhóm:** xếp giảm dần theo chỉ số; hoà thì xếp theo tên mã (tất định). SHORT = `k` mã đầu, LONG = `k` mã cuối,
   `k = max(ro_k_toi_thieu, floor(ro_ty_le_k × n_du_dieu_kien))`. `n_du_dieu_kien < ro_so_coin_toi_thieu` ⇒ **không
   nhóm nào** trong ngày (điều 5).
5. **Chuyển trạng thái tại mỗi lần cân rổ:** mã vẫn cùng nhóm ⇒ giữ nguyên, không cân lại cỡ; mã rời nhóm (kể cả khi
   ngày đó không có nhóm nào) ⇒ đóng; mã vào nhóm ⇒ mở; mã đổi nhóm ⇒ đóng rồi mở chiều mới. Không có lệnh nào ngoài lần
   cân rổ, trừ stop thảm hoạ.

## 4. Quy tắc vào/ra

- **Cỡ vị thế:** notional mỗi vị thế mới = `von_ro_usdt / (2 × k)` với `k` của ngày mở. Đòn bẩy `ro_don_bay` (1) qua
  `leverage()`, **không** dùng `tier_a.L_exchange` của ZA.
- **Lệnh:** lệnh **thị trường** vào và ra (tờ chọn). Cấu hình Freqtrade chung (`config/freqtrade/config.json`) ép lệnh chờ
  post-only cho ZA và thắng thiết lập của chiến lược. **Chủ dự án chốt:** file phủ riêng
  `config/freqtrade/phu/<TenChienLuoc>.json` (chỉ `order_types`, `order_time_in_force`, `entry_pricing`, `exit_pricing`),
  bộ chạy **tự** áp khi chạy đúng chiến lược đó (E1 `--chien-luoc`, sau này cả dry-run). ZA không đổi một bit. File phủ
  **không** được chứa khoá nào `test_lz24` ghim.
- **Thoát do cân rổ:** `custom_exit` trả nhãn `CAN_RO` (hằng `EXIT_CAN_RO`, `DR-CAN-RO-01` §2 điều 3).
- **Stop thảm hoạ:** `custom_stoploss` trả `stoploss_from_absolute(giá_vào × (1 ∓ ro_stop_tham_hoa_pct/100), …,
  is_short=…, leverage=trade.leverage)`. Bài học `MT-16` (vii): không trả tỉ lệ thô. Mã bị stop không mở lại trước lần
  cân rổ sau; điều này tự đúng vì chỉ mở lệnh tại lần cân rổ.
- **Không chốt lời, không DCA:** `position_adjustment_enable` (ghim `true` bởi `L-Z24` cho ZA) được giữ, nhưng chiến lược
  **không** cài `adjust_trade_position`.
- **Phí và funding:** phí taker và funding thật theo từng kỳ chốt, do Freqtrade futures tính từ dữ liệu `funding_rate` +
  `mark` trên đĩa. Tổng funding nhận ròng của mỗi lệnh đọc từ `trade.funding_fees`.
- **Chống nuốt ngoại lệ:** test khoá của chiến lược cấm dòng log *"Strategy caused the following exception"*, cùng khuôn
  `test_td0187`. Một chốt fail-closed bị nuốt là một chốt không tồn tại.

## 5. Lớp thoát lệnh (`DR-CAN-RO-01`)

<!-- DR-CAN-RO-01:LOP:BEGIN -->
```json
{"slot": "IQ-0003", "lop": "CAN_RO_THEO_LICH"}
```
<!-- DR-CAN-RO-01:LOP:END -->

Nhãn thoát hợp lệ của chiến lược: `CAN_RO`, `stop_loss`, `stoploss_on_exchange`, `force_exit`. Chiến lược **không** sinh
nhãn nào khác. Nếu số đếm EXPLORE (`TD-0401`) thấy nhãn khác, đó là lỗi mã, không phải lý do nới tập.

**Vai trò DG8** (`DR-PHAN-QUYET-01` §4.2 bước 1): ứng viên **không có** cửa thoát theo thời gian. Lối thoát dự kiến chiếm
đa số là `CAN_RO`. Dải `TIME_STOP` không áp (`DR-CAN-RO-01`).

## 6. Hướng và lockbox

- **Lockbox:** đoạn `[T2,T3]`, chạm **một lần** ở D9.5 (`DR-LOCKBOX-04`: DR commit `cf74603` trước lần chọn `729e27f`,
  điều kiện §4.1 thoả). Chữ *"lockbox MỚI"* trong `nguong_bac_bo` được đọc là lockbox chưa ứng viên nào chạm. `[T2,T3]`
  thoả điều đó (`MT-79`).
- **Hướng (`MT-82`, chủ dự án chốt):** rổ là **một** hướng `NEUTRAL`. Ngưỡng PASS lockbox viết cho cả rổ, bám
  `nguong_bac_bo`. Kèm **báo cáo tách chân** Long/Short (pnl, funding, số lệnh mỗi chân) **chỉ ghi, không phán quyết**, để
  lộ phần lệch theo chế độ thị trường mà `DR-LOCKBOX-04` §4.3 lo. Việc viết ngưỡng là `TD-0274` cho ứng viên này.
- **Lớp xác nhận sau `T3`** (`DR-LOCKBOX-04` §3, `DR-XAC-NHAN-01`): áp như mọi ứng viên suất (d). Chỉ số `mean_r` của ô ký
  đã điền (`TD-0386`) dùng đơn vị R, mà rổ không có R ⇒ xem §10 câu (a).

## 7. Phán quyết (chủ dự án chốt: "ngưỡng đã đăng ký + cổng chung")

**Bác bỏ** nếu **bất kỳ** điều nào dưới đây xảy ra. Bốn điều đầu đúng nghĩa `nguong_bac_bo`, đo trên lockbox:

1. **Độ bền thứ hạng:** trung bình qua các lần cân rổ của tương quan hạng Spearman giữa chỉ số §3.2 tại `t` và tổng
   funding thực chốt trong `(t, t + 24h]` của cùng các mã đủ điều kiện < `0.3`.
2. **Lãi ròng:** tổng `pnl_abs` (DR-013, sau phí + funding) ≤ 0, **hoặc** không vượt cổng thống kê của §7 điều 5.
3. **Đối chứng ngẫu nhiên:** lãi ròng không vượt phân vị 95 của 1000 rổ ngẫu nhiên cùng cấu trúc: cùng ngày cân rổ,
   cùng `k`, cùng notional, cùng stop, mã chọn ngẫu nhiên trong cùng tập đủ điều kiện. Hạt giống ngẫu nhiên cố định, ghi
   trong hiện vật.
4. **Đúng cơ chế:** phần funding nhận ròng < 50% lãi ròng. Lãi ròng ≤ 0 thì điều 2 đã bác bỏ.
5. **Cổng thống kê chung** thay cho `dsr_adjusted_expectancy`: đơn vị và công thức xem §10 câu (a).
6. **Cổng chung khác giữ nguyên:** `L-Z3` đệm thanh lý (ở 1x gần như luôn thoả, vẫn đo).

**Tiêu chí D0.9 hiện có KHÔNG áp, kèm lý do** (`src/tool_d/gates/thresholds.py`):

| Tiêu chí | Vì sao không áp |
|---|---|
| `skewness_diff_vs_z1` | So với arm `Z1` của ZA; rổ không có arm `Z1` |
| `time_stop_ratio` | Rổ không có cửa `TIME_STOP` (`DR-CAN-RO-01`) |
| `max_single_trade_loss_over_risk_budget` | Mẫu số là ngân sách rủi ro theo R của ZA; lỗ tối đa mỗi vị thế của rổ bị chặn bởi stop 25% (+ trượt giá), đo và **báo cáo**, không phán quyết |
| `dsr_adjusted_expectancy ≥ 0,10 R` | Đơn vị R không tồn tại với rổ ⇒ thay bằng §7 điều 5 |

Máy phán quyết của rổ là **hàm riêng**; không sửa `thresholds.py` của ZA.

## 8. Thước đo sai lệch cho lệnh thị trường (`MT-83` câu 2)

- `DR-015` / Δ_R đo sai lệch **khớp lệnh chờ theo tranche**. Rổ không có lệnh chờ ⇒ **không áp**. `L-Z56` vẫn chặn E3 khi
  `enable_short` bật (`DR-SHORT-02` §3). Rổ không chạy qua E3.
- Backtest khớp tại giá mở nến + phí taker, **không** mô hình trượt giá: tờ chọn không khai trượt giá, và thêm một mô hình
  là thêm một tham số.
- **Trượt giá thật đo ở D10** trên mỗi lần cân rổ: giá khớp so với giá mở nến 1H. Ngưỡng chấp nhận: §10 câu (b).

## 9. Dữ liệu và rổ

- CALIB: `pool_t0` (143 mã, `ro_cho_tap("CALIB")`). Funding bắt đầu đúng `T0` ⇒ lần cân rổ đầu tiên sớm nhất `T0 + 3 ngày`.
  18 mã huỷ niêm yết giữa chừng ⇒ tự rời tập đủ điều kiện khi hết nến 1H (§3 điều 3).
- WFO: `pool_t1` (107 mã). `max_open_trades` hiện 100 ≥ `2 × k` lớn nhất (`k ≤ 28` với 143 mã).
- EXPLORE (`TD-0401`, 0 suất): 100 mã `user_data/data/explore/futures`, **không có 5m** ⇒ bộ đếm chạy không
  `timeframe_detail`. Hiện vật ghi rõ điều này.
- Không entrypoint mới (`L-Z36`): E1 chạy chiến lược qua `--chien-luoc`.

## 10. Còn mở — chốt TRƯỚC suất trial đầu tiên của `IQ-0003`

- **(a) Đơn vị của cổng thống kê (§7 điều 5) và của lớp xác nhận.** Đề xuất: một quan sát = một ngày giữ rổ; lợi suất ngày
  = `pnl_abs` của ngày / `von_ro_usdt`. Cổng: `mean − h·std/√n > 0` với `h = √(2·ln N)` như rào DSR hiện hành
  (`N` hiện hành). Không có ngưỡng tối thiểu kiểu `0,10 R` vì R không tồn tại. Chờ chủ dự án.
- **(b) Ngưỡng trượt giá chấp nhận ở D10.** Chưa điền = `+inf` theo `L-Z35`, để cổng không thể vô tình PASS.
- **(c) Giá trị `tier_a.von_ro_usdt`.** Quy tắc: `≥ 1,1 × 2 × k_max × sàn_max`. `sàn_max` = sàn `san_tool_d()`
  (`DR-D4-05`) lớn nhất trên các mã của `pool_t0` ∪ `pool_t1` ở đòn bẩy 1. `k_max` = `k` với cỡ rổ lớn nhất. Con số đo
  bằng metadata sàn (0 suất, đo mô tả), rồi chủ dự án chốt.

## 11. Thi hành

- `TD-0400`: chiến lược theo §2–§5 + file phủ §4 + khoá YAML §2 + test khoá (rổ trên dữ liệu tổng hợp, tính trung tính,
  nhãn thoát, không nuốt ngoại lệ, không nhìn trước ở điều §3.1).
- `TD-0401`: số đếm `exit_reason` EXPLORE theo `DR-CAN-RO-01` §3 (khoá `lop_chien_luoc` + `dr_thiet_ke` trỏ file này).
- Máy phán quyết §7 và đối chứng ngẫu nhiên §7 điều 3: việc riêng, mở mã khi tới D0.9 của ứng viên.
