# DR-D4-08 — Nối §3.3b (xác nhận entry price-action) vào tín hiệu vào lệnh: hướng P1 + sáu diễn giải

> Quyết định của chủ dự án, 09/09/2026, sau phân tích hệ thống của phiên `be` (TD-0193). Commit
> **RIÊNG và TRƯỚC** mọi dòng mã thi hành — tiền lệ DR-D4-02 … DR-D4-07. Đã nhắn hai phiên song song
> (`-28`, `-46`) trước khi mở file này (N12 mục 6); cả hai xác nhận không giữ file/mã liên quan.
> Bằng chứng số: `docs/du-lieu-do/dg2-explore-quet-arm.json` (83 lệnh Z0 / 48 mã / [T0,T2]),
> `docs/du-lieu-do/do_mt22_a_vs_b.py` (A 43,1% · B 81,2%), 0 trial.

## 1. Vấn đề — nối §3.3b là ĐỔI cơ chế vào lệnh, không phải thêm một bộ lọc

| | Đang chạy (`ZoneAbsorption.py` trước DR này) | Spec §3.3b + §3.5 |
|---|---|---|
| Khi nào vào | **Ngay tại nến 4H xác nhận zone** `j`; limit `p1 = min(zone_high, close4H[j])`, sống 3 nến 1H | Sau `confirmed_at_bar`, **đợi lần chạm đầu** (low 1H vào zone), rồi **≤ 3 nến** tìm nến C thoả `(a∧c)∨(b)`, rồi `p1_order = min(zone_high, close(C))`, sống ≤ 3 nến, NO_FILL không đặt lại |
| Bộ lọc lúc chạm | Không có | Rejection wick + volume, hoặc phân kỳ RSI |
| Cơ hội vào / zone | Chỉ nếu giá còn trong/quay lại zone trong 3 nến sau `j` | Bất kỳ lúc nào trong vòng đời zone, nhưng chỉ **lần chạm đầu** (MT-22 A) |

Ba hệ quả dây chuyền: timing vào lệnh đổi hẳn; `p1` đổi ⇒ `p_avg`, `r_eff_plan`, `N_full` (cỡ lệnh)
và với `Z1` cả `sl` đổi — kế hoạch **phải tính lại tại C**; số lệnh đổi theo hướng **chưa biết**
(cửa sổ chạm rộng hơn, bộ lọc chặt hơn). Spec dòng 4148: *"thiếu xác nhận entry sẽ làm win rate MỌI
cấu hình thấp giả tạo"* — D4 chạy không có §3.3b là đo 9 arm của một hệ thống khác (MT-21).

## 2. Quyết định — hướng P1, vector hoá trong `populate_indicators`

Với mỗi zone đáy đã xác nhận ở khung 4H (`_tinh_zone_4h`), chạy `quet_xac_nhan_zone()` trên mảng
**1H** ngay trong `populate_indicators`, đặt `enter_long = 1` **tại nến C** với `enter_tag` = kế hoạch
**tính lại tại C**. Bộ lọc trend (Phần 2, theo arm) vẫn xét ở `populate_entry_trend`, **tại hàng C**
— cùng luật cũ áp lên nến tín hiệu mới, không phải luật mới.

Vì sao không phải hai phương án kia:

- **P2 — state machine trong callback** (`custom_entry_price`/`confirm_trade_entry`): đúng vùng
  `TD-0170` từng dính lookahead (`get_pair_dataframe` trả cả nến tương lai), state không tái lập giữa
  backtest và live, và Freqtrade **nuốt exception** callback (MT-16 vii). Loại.
- **P3 — nối từng phần (chỉ (a) trước)**: tái diễn MT-15 — `Z0 ≡ Z0-V1`, một suất trial đo khác biệt
  bằng không. Loại.

Với P1, backtest và live đi **cùng một đường** (populate chạy trên nến đã đóng), không có state giữa
callback, và đối chứng lookahead viết được theo khuôn `TD-0170` (cắt dataframe tại `C−1` ⇒ không tín
hiệu; tại `C` ⇒ có). Điểm phải canh: hàm quét nhìn về phía trước để tìm C, nên **bắt buộc** có test
chứng minh *tín hiệu tại C chỉ phụ thuộc dữ liệu ≤ C*.

## 3. Sáu diễn giải đã chốt — ghi ra để cãi lại được, KHÔNG code hai chiều sau cờ

| # | Câu hỏi spec để ngỏ | Chốt | Căn cứ |
|---|---|---|---|
| 1 | `tier_b.wick_close_upper_frac` điều khiển vế nào của (a)? `la_nen_rejection` có **hai** số ma `0.5` (bóng ≥ 0,5×range **và** đóng cửa ≥ thấp + 0,5×range) | **Cả hai vế cùng MỘT số** | Spec một câu, một dấu `[CẦN CALIBRATE]`, kiểm kê DOF đếm **một** tunable (#3). Tách làm hai là tự tạo một bậc tự do mà `dof_inventory.yaml` không biết (cảnh báo của `-46`). `param_status.yaml` ghi 0,5 là *"chính định nghĩa của chữ nửa trên"* — FROZEN |
| 2 | Mốc (giá, RSI) cho điều kiện (b) ở lần chạm đầu — cụm chạm 4H quy về nến 1H nào? (câu hỏi mở MT-22) | **Đáy thật của cụm chạm 1H CUỐI CÙNG trong cửa sổ hình thành** `[nến 1H mở cùng swing i, nến 1H đầu sau khi j đóng)`; RSI lấy **tại đúng nến đáy đó** | Nhất quán với diễn giải #1 của chặng 1 (`entry_confirmation.py`, sửa 09/09 do `-f4` bắt): mốc nông hơn đáy thật làm (b) dễ thoả hơn thiết kế, lệch về chiều nhiều lệnh (lạc quan). `zone_hop_le` đòi `so_touch ≥ 1` trong cửa sổ đó nên mốc **luôn tồn tại** (MT-22 đính chính) |
| 3 | Vòng quét bắt đầu ở nến 1H nào? | **Nến 1H đầu tiên SAU KHI nến 4H `j` ĐÓNG** (= `date4[j] + 4h`, đúng mốc `merge_informative_pair` cho 1H nhìn thấy `j`) | Bắt buộc, không có lựa chọn an toàn khác: tại các nến 1H *bên trong* `j`, zone **chưa** xác nhận (`K_XAC_NHAN` đếm tới lúc `j` đóng). ⚠️ Script đo MT-22 bắt đầu từ giờ **MỞ** của `j` (`moc.get(z["ts_j"])`) ⇒ 43,1%/81,2% mang lookahead nhẹ; con số sản xuất phải đo lại (§6) |
| 4 | ATR(4H) nào khi tính lại kế hoạch tại C? | **Đóng băng tại `j`** (`atr_4h[j]`) — chỉ `p1` đổi theo `close(C)`; với `Z1`: `sl = p1_order − 2,2 × ATR(j)` | SL của zone không được trôi theo thời gian chờ xác nhận (cùng lập luận DR-D4-06 §3: *"một mục tiêu không được phép trôi"*). `ke_hoach_theo_arm()` vẫn là **nơi duy nhất** phân nhánh SL (TD-0192) |
| 5 | Biên `den` của vòng quét (chặng 1 để cho tầng gọi)? | `den = min( k_start + 40 × 4 , nến 1H đầu tiên sau nến 4H đầu tiên ĐÓNG DƯỚI SL kiểu zone )` | §1.3 (40 nến 4H) áp đúng đối tượng cho zone ENTRY; và zone chết theo DG1 khi 4H đóng dưới `sl` — không có vế này, phản thực B vẫn quét tiếp trên một zone đã bị phá. SL dùng để huỷ là SL **kiểu zone** (§3.1), độc lập arm — `Z1` không được sống lâu hơn `Z0` trên cùng zone |
| 6 | Sửa fixture `test_td0187` trong cùng task hay tách? | **Cùng task** | Tách ra là để suite ở trạng thái xanh-vô-nghĩa (0 lệnh) giữa chừng — đúng hình dạng *"fixture đúng hệ thống cũ, im lặng sai hệ thống mới"* lần thứ **ba** (TD-0182, TD-0194, nay TD-0193). Ca đối chứng thường trực *"bộ sinh phải cho ≥ 1 nến xác nhận §3.3b"* gắn vào `_sinh_du_lieu` |

Ba chi tiết triển khai đi kèm (không phải diễn giải mới, ghi để không ai suy đoán):

- **Hai zone cho C cùng một nến 1H:** zone **xác nhận sớm hơn** giữ chỗ; zone sau bị bỏ và **đếm**
  (`XAC_NHAN_3_3B … trung_nen=`). Freqtrade chỉ mở một vị thế/pair nên hai tín hiệu cùng nến là vô nghĩa
  về thực thi; chọn theo thứ tự xác nhận để kết quả **tất định**, không phụ thuộc thứ tự dict.
- **`t4` (trend 4H ghi vào tag, mốc DG2):** lấy tại nến 4H **đã đóng gần nhất tại C**, không phải tại
  `j` — DG2 so *"trend không đổi hướng kể từ tranche 1"*, và tranche 1 giờ nằm ở C.
- **`Z0-V1` = `bat_dieu_kien_c=False`, mọi arm khác `True`** — bảng tường minh trong
  `entry_confirmation.py` (chỗ TD-0183 đã chỉ định), **không mặc định**, arm lạ ⇒ raise.

## 4. Phản thực B — CHỈ ghi, KHÔNG BAO GIỜ phát tín hiệu

`quet_xac_nhan_zone()` trả `nen_xac_nhan_phan_thuc` / `lan_cham_phan_thuc`; chiến lược ghi vào **hai
cột riêng** (`xac_nhan_phan_thuc_b`, `lan_cham_phan_thuc`) mà `populate_entry_trend` **không đọc**.
Test bắt buộc: bật/tắt ghi phản thực ⇒ tập lệnh thật **không đổi một lệnh** (MT-22). Điều kiện mở
lại giữ nguyên MT-22: *loại B ra* = 0 trial (chỉ đếm); *nhận B vào* = 1 suất trial B1 đăng ký trước.

## 5. Kế toán DOF — `N` KHÔNG đổi, 0 trial

- Không thêm tham số nào: `v_min` (#4, FROZEN 1,0) và `wick_close_upper_frac` (#3, FROZEN 0,5) **đã
  nằm trong 12** — nay mới thật sự có **đường đọc** (gỡ hai dòng `MIEN_TRU` của TD-0195, MT-23).
- `so_nen_cho = 3`: spec §3.5 ghi *"🔒 0 hằng số mới — dùng lại tối đa 3 nến chờ của §3.3b"*; hằng
  số định nghĩa, không phải ngưỡng tune.
- `dof_goc` 28 · `|tier_b|` 12 · **N = 114** · rào DSR **3,0777** — không đổi.

## 6. Điều kiện vào `TD-0184` — viết TRƯỚC, khuôn OQ-07

🔴 **Phát hiện hệ thống khi phân tích (chưa ai nêu tên):** `dg2-explore-quet-arm.json` cho `Z0`
**83 lệnh / 48 mã / 21,7 tháng ≈ 46 lệnh/năm**, quy đổi thô sang pool 102 mã ≈ **~97 lệnh/năm** —
**dưới sàn 150 lệnh/năm của Nhánh 1 (§10.2)** ngay cả TRƯỚC khi nối §3.3b. Kèm 21% lệnh đủ 3
tranche, 41% dừng ở 1, và `Z2 ≡ Z3` trên EXPLORE. Kết cục có xác suất cao nhất của D4 là
**INCONCLUSIVE vì thiếu mẫu** — hợp lệ theo DR-011, nhưng phải **biết trước** khi tiêu 9 suất.

Vì thế sau khi nối, **trước khi `TD-0184` đặt chỗ**, chạy một phép đo MÔ TẢ (EXPLORE, 0 trial — chỉ
đếm, không PnL, đúng ranh giới `DR-D0PRE-05` §4): lệnh/năm theo arm với mốc quét đúng (#3); tỉ lệ
zone vào lệnh của A; phân bố `wait_bars`; tỉ lệ `(a∧c)` vs `(b)`; NO_FILL. **Nếu lệnh/năm quy đổi
pool < 150 ⇒ dừng, trình chủ dự án** — không tự nới, không tự chạy tiếp.

## 7. Điều DR này KHÔNG chốt

- Không chốt `v_min`/`wick_close_upper_frac` là đúng — cả hai FROZEN chưa calibrate (DR-D4-03, TD-0190).
- Không chốt Δ_R của D3.5 còn áp cho cơ chế mới — **giả định** là còn (cùng cơ chế *limit tại mức*,
  `DR-015` Bước 1 đo `price_delta` theo mức tranche, không theo thời điểm đặt); ba artifact `L-Z56`
  **không đụng**. Ghi vào `d4_han_che` khi đóng cổng.
- Không chốt Short — LONG only (DR-D4-01); vòng quét dùng `loai="day"`.

## 8. Hệ quả phải ghi khi đọc kết quả D4 (điểm của `-46`)

Nối §3.3b làm `Z0` **thôi trùng** `Z0-V1` (MT-15/MT-21) — tức đổi **ý nghĩa** của một suất trial đã
được cấp. Mọi bảng arm đo **trước** DR này (`dg2-explore-quet-arm.json`) và **sau** nó **không so
trực tiếp được với nhau**; TD-0184 phải ghi `code_commit` ≥ commit thi hành DR này.

## 9. Điều kiện mở lại

1. Phép đo §6 cho lệnh/năm quy đổi < 150 ⇒ mở lại **cách đọc §3.3b** (không phải nới `so_nen_cho`) —
   trình chủ dự án cùng con số, quyết trước khi tiêu trial.
2. Phản thực B thoả điều kiện *nhận B vào* của MT-22 ⇒ trả 1 suất B1, không phải sửa DR này.
3. `test_doi_chung_am_lookahead` (cắt tại `C−1`) đỏ ⇒ đây là **lỗi**, DR-012 Hạng 1, sửa 0 trial —
   không phải điều kiện mở lại.

## 10. Việc thi hành (TD-0193 chặng 2 → 5)

| Chặng | Việc | Bằng chứng |
|---|---|---|
| 2 | `entry_confirmation.py`: `wick_frac` + `bat_dieu_kien_c` **bắt buộc** cho `la_nen_rejection`/`tim_xac_nhan_entry`/`quet_xac_nhan_zone`; bảng `bat_dieu_kien_c_cua_arm`; kết quả quét mang `nen_cham_dau` + `loai_xac_nhan` | test khoá L-Z6/TD-0193 cập nhật chữ ký, **giữ nguyên khẳng định** |
| 3 | `ZoneAbsorption.py`: cột `rsi_1h`/`volume_ma_1h`/`atr_4h`; `_xac_nhan_3_3b()`; `populate_entry_trend` đọc `xac_nhan_3_3b` thay `zone_valid_4h`; tag thêm `ec`/`wb`/`lc`; gỡ `MIEN_TRU` | fixture `test_td0187` có nến xác nhận; ca *"cùng giờ mở với Minimal"* đổi thành *"cùng zone, mở ≥ Minimal"* |
| 4 | Lớp canh: `Z0` ≠ `Z0-V1` trên fixture; đối chứng âm lookahead (cắt `C−1`/`C`) + phá thật; phản thực bật/tắt không đổi tập lệnh; AST `enter_long` chỉ gán qua một hàm; đối chứng thường trực trong `_sinh_du_lieu` | Docker (N7) |
| 5 | Phép đo §6 trên EXPLORE, ghi `docs/du-lieu-do/` + research-log | quyết định vào/không vào TD-0184 |

## 11. Lịch sử

| Ngày | Sự kiện |
|---|---|
| 09/09/2026 | Phân tích hệ thống (phiên `be`) — 9 khoảng hở khi đọc code, 3 phương án, đề xuất P1 |
| 09/09/2026 | Chủ dự án: *"đồng ý P1 & 6 điểm bạn đề xuất, bắt đầu code"* — DR này |
