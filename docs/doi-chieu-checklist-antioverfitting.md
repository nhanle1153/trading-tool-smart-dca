# Đối chiếu "Checklist anti-overfitting Freqtrade (5 giai đoạn)" với Tool D

> **TD-0208** · lập 10/09/2026 · **0 trial** (chỉ đọc tài liệu + đếm file trên đĩa,
> không chạm CALIB/WFO/LOCKBOX — N2)

---

## §0 — Địa vị của tài liệu này (đọc trước khi dùng)

**Đây KHÔNG phải nguồn sự thật.** Thứ tự ưu tiên của N1 giữ nguyên: `tool-d-smart-dca.md` (v8)
thắng mọi thứ, rồi `back-end-note.md`, `ARCHITECTURE.md`, `TASKS.md`. Checklist được đối chiếu ở
đây là **một quy trình ngoài, do chủ dự án đưa vào 10/09/2026**, dùng như một lần soi độc lập.

**Đây là ảnh chụp một thời điểm, không có nghĩa vụ cập nhật.** Mọi con số dưới đây đo tại
10/09/2026. Ai đọc lại sau đó **phải verify lại từ đĩa**, không trích dẫn tài liệu này như bằng
chứng hiện hành. Cố tình không dựng nghĩa vụ đồng bộ: một tài liệu thứ hai phải cập nhật theo spec
chính là hình dạng MT-03 sinh ra để cấm.

🔴 **Cảnh báo cho ai định làm theo checklist theo nghĩa đen.** Giai đoạn 2 của nó là *Hyperopt* và
Giai đoạn 4 là *FreqAI*. Cả hai **bị cấm tuyệt đối** trong Tool D (`tool-d-smart-dca.md:448`,
`:462`). Chạy `hyperopt` **một lần** làm `L-Z25` báo đỏ và theo spec thì **toàn bộ
`trial_registry` mất hiệu lực, phải khai lại N từ đầu**. Đây không phải "bước tiếp theo tạm bỏ
qua" — nó là một hành động không hoàn tác được.

⚠️ **Hạn dùng của phần số liệu — đã đo lại, không còn là phỏng đoán.**
Bản vá TD-0207 (`61479b7`) làm `_zone_dinh_tren` / `_tuoi_zone_dinh_nen` đọc đúng nguồn zone đỉnh;
`TASKS.md` (dòng TD-0206/TD-0207) đã ghi trước rằng vá xong **đổi mọi con số D4 đã đo**. Bản nháp
đầu của tài liệu này cảnh báo rằng **số lệnh** cũng có thể đổi — lập luận cơ chế: TP1 quyết định
lúc lệnh đóng, mà một lệnh đóng sớm thì giải phóng chỗ cho lệnh sau trên cùng cặp. Lập luận đó
**không sai về cơ chế nhưng đã bị một phép đo vượt qua**:

| Arm | Trước vá (`td0205-...json`) | Sau vá (`td0207-h4-sau-va.json`) |
|---|---|---|
| `Z0` | 22 lệnh · 44,8/năm · TP1 = 6 nạng, 0 zone | **22 lệnh · 44,8/năm** · TP1 = **7 zone, 1 nạng** |
| `Z0-T0` | 746 lệnh · 1.518,1/năm | ⚠️ **chưa đo lại** |
| `Z0-T1` | 160 lệnh · 325,6/năm | ⚠️ **chưa đo lại** |

⇒ **Con số trung tâm của §2 và §3 (`Z0`: 22 lệnh, 44,8/năm, `n ≈ 28`) đứng vững qua bản vá — bằng
phép đo, không bằng lập luận.** Phễu tín hiệu cũng trùng khít (2.621 zone → 1.104 → 32).
Hai con số `Z0-T0` = 746 và `Z0-T1` = 160 dùng ở **§2 (mục 1.1) và §3** vẫn là số **trước vá** và
chưa ai đo lại — chúng chỉ dùng làm đối chứng về **bậc độ lớn** (34 lần), không dùng làm phán quyết.

🔑 **Ranh giới phải giữ:** bản vá đổi **tầng chốt lời**, nên mọi con số **PnL / expectancy / R** đo
trước `61479b7` là của một hệ thống **không có TP theo zone** và không dùng lại được. Con số
**đếm lệnh** thì đã kiểm và không đổi (với `Z0`). Tài liệu này không trích một con số PnL nào —
vì trên đĩa **không có con số nào để trích** (xem GĐ1.4).

---

## §1 — Ánh xạ 5 giai đoạn của checklist vào lộ trình D0-PRE → D12

| Checklist | Tương ứng trong Tool D | Nhận xét |
|---|---|---|
| **GĐ1** Rule-based đơn giản | D0-PRE → D1 → D2 | Ánh xạ được. Đây là giai đoạn Tool D **chưa hoàn tất** theo chuẩn của checklist (xem §2) |
| **GĐ2** Hyperopt có kiểm soát | ❌ **KHÔNG TỒN TẠI — cấm tuyệt đối** (`:448-460`, test khoá `L-Z24`/`L-Z25`/`L-Z37`). Thay bằng: calibrate **thủ công** (ngân sách B1), DR-010 `N_ĐĂNG_KÝ = 114` (`src/tool_d/gates/dsr.py:24`), rào DSR **3,0777** | Tool D **chặt hơn**. Spec gọi hyperopt là *"mối nguy lớn nhất, lớn hơn FreqAI nhiều"* vì 500 epoch = 500 phép thử trên ngân sách 114 |
| **GĐ3** Forward test bằng dry-run | D11 — nhưng Tool D chèn **D3.5** và **D10 testnet** vào TRƯỚC nó, và §9b.3 chặn cứng: *"KHÔNG được vào D11 nếu D2 chưa verify"* (`:2954`) | Tool D **chặt hơn**: dry-run không kiểm chứng được hành vi sàn, chỉ testnet mới gọi API thật |
| **GĐ4** Thêm FreqAI | ❌ **CẤM** (`:462-473`) — ba lý do: không đếm được N ⇒ DSR vô nghĩa; không chạy được GATE D0.9; mô hình tự thích ứng không bao giờ "sai" quan sát được | N/A. Nhưng **các nguyên lý con vẫn áp dụng** — xem §2, mục GĐ4 |
| **GĐ5** Live vốn nhỏ, tăng dần | D12 + thang drawdown 5/8/20% (`config/tool_d_config.yaml:122`) + điểm quyết định mỗi 100 lệnh đóng + tái tạo 1 trial/25 lệnh + `DR-012` change-control | Tool D **chặt hơn**: ngưỡng dừng viết TRƯỚC, có máy canh, không phải kỷ luật con người |

**Đọc bảng này thế nào:** ba trong năm giai đoạn Tool D chặt hơn checklist, hai giai đoạn còn lại
Tool D cấm. Kết luận **không** phải "checklist thừa" — giá trị của nó nằm ở §2, nơi nó bắt đúng ba
chỗ dự án không có lớp canh nào.

---

## §2 — Đối chiếu từng mục

Bốn nhãn, không có nhãn thứ năm: `ĐẠT` · `KHÔNG ĐẠT` · `CHƯA ĐO` · `N/A — CẤM`.
🔴 **`CHƯA ĐO` không bao giờ được thay bằng `0.0`** (N6) — chưa đo là một trạng thái, không phải
một giá trị.

Nhãn nguồn: **`đo-được`** = có file kết quả trên đĩa · **`người-khai`** = chỉ có chữ (MT-10).

### GĐ1 — Rule-based chiến lược đơn giản

| Mục checklist | Trạng thái | Bằng chứng | Ghi chú |
|---|---|---|---|
| 1.1 Tối đa **2-4 điều kiện entry**, mỗi cái giải thích được edge | 🔴 **KHÔNG ĐẠT** (`đo-được`) | Phễu WFO: `docs/du-lieu-do/td0205-lenh-nam-wfo-explore.json` — 2.621 zone → 1.104 qua §3.3b (42,1%) → **32** tín hiệu sau lọc trend → **22 lệnh** | Xem phân tích ngay dưới bảng |
| 1.2 Backtest **2-3 năm**, đủ bull/bear/sideway | 🟡 **KHÔNG ĐẠT theo chữ — đánh đổi có ý thức** (`đo-được`) | `config/tool_d_config.yaml:123`: T0 2024-04-09, T1 2025-06-12, T2 2026-01-29, T3 2026-09-06 ⇒ CALIB **1,175 năm** · WFO **0,632 năm** · LOCKBOX **0,602 năm**; tổng 2,409 năm | Tổng đạt 2-3 năm nhưng **không phân vùng nào** đạt. DR-011 chỉ đòi lockbox ≥20% tổng (thực tế 25,0%) + ≥1 chế độ thị trường khác biệt — **chuẩn thấp hơn checklist**. Mốc đã niêm phong (`DR-D0PRE-07`), tài liệu này **không đề xuất đổi** |
| 1.3 Số lệnh **tối thiểu 100** để có ý nghĩa thống kê | 🔴 **KHÔNG ĐẠT** (`đo-được`) | `td0205-...json` `lenh_that.Z0`: **22 lệnh** trên 88 mã / 50,12 mã-năm ⇒ **44,8 lệnh/năm** quy đổi pool 102 ⇒ `n ≈ 28` trong cửa sổ WFO. Sàn riêng của Tool D còn cao hơn: **150 lệnh/năm** (`tool-d-smart-dca.md:4274`, *"ĐÂY LÀ SÀN, KHÔNG PHẢI TRẦN"*) | Và sàn nội bộ của WFO: `san_lenh_moi_fold: 30` × `so_fold: 3` = **90 lệnh** (`config/tool_d_config.yaml:129-132`) — đang có 22. ⚠️ Con số cũ **63,6/năm** là của cửa sổ [T0,T2] (`td0193-...json`), **không** phải cửa sổ ablation thật; TD-0205 đo lại riêng trên WFO và ra thấp hơn 30% |
| 1.4 **Expectancy dương** đã trừ phí + funding | 🔴 **CHƯA ĐO** (`đo-được` — đo được rằng *chưa có gì*) | `registry/trial_registry.jsonl`: **13 dòng sự kiện / 5 trial_id**, 4 CONSUMED đều `budget_line: B0` (tiêu chí pool) với `outcome.expectancy: null`; B1/B2/B3 = **0 trial**. `runs/` chỉ có `.gitkeep` + 3 file snapshot — **không thư mục trial nào**; tìm `*.seal` toàn repo ⇒ **0 file**. `user_data/backtest_results/`: 4 lần chạy, lớn nhất **35 lệnh / 2 cặp**, chiến lược `ZoneAbsorptionMinimal` (không phải bản sản xuất), và **untracked** | **Không có một con số expectancy/Sharpe/DSR nào đủ tư cách phán quyết trên toàn repo.** Đây là mục quan trọng nhất của cả bảng |

**Về 1.1 — vì sao đây là mục đáng lo nhất, không phải mục hình thức.**
Tool D không có 2-4 điều kiện entry. Nó có: zone absorption → lọc trend hai tầng (4H + 1D, gồm
hướng-1D + ADX ≥ 20 + tuổi trend ≥ 5 ngày) → xác nhận §3.3b `(a ∧ c) ∨ b` → tám cổng DG1–DG8 →
ba tranche → TP1/TP2 + nạng. Kiểm kê DOF: 26 tham số rút còn **12 tunable**.

Hậu quả **đo được**, không phải suy đoán: trên WFO, bộ lọc trend cắt **1.104 → 32**, tức **97,1%**.
Đối chứng: arm `Z0-T0` (bỏ hết lọc trend) cho **746 lệnh** so với `Z0` **22 lệnh** — gấp **34 lần**.

Dự án **có** cơ chế phạt phức tạp (kiểm kê DOF → N → rào DSR `√(2·ln N)`), nhưng **không có ngưỡng
nào bảo dừng**. Câu trả lời được thiết kế sẵn là ablation D4 (`Z0` vs `Z3` trả lời *"DCA có đáng
không"*, `Z0-T0`/`Z0-T1`/`Z0-T2` trả lời *"lọc trend có đáng không"*). 🔑 **Và đó chính là vòng
luẩn quẩn:** phức tạp ⇒ ít lệnh ⇒ không đủ mẫu để chứng minh phức tạp có đáng. Ablation D4 đang bị
chặn đúng bởi hệ quả của thứ nó sinh ra để đo.

### GĐ2 — Hyperopt có kiểm soát → **N/A: CẤM.** Nhưng từng mục con vẫn ánh xạ được

| Mục checklist | Trạng thái | Bằng chứng | Ghi chú |
|---|---|---|---|
| 2.1 Chỉ tối ưu **2-5 tham số** | 🟡 **KHÔNG ĐẠT** (`đo-được`) | 12 tham số `tier_b`. `config/param_status.yaml`: **12/12 `status: FROZEN`** và **12/12 `chua_calibrate: true`** — không cái nào `TUNED` | Con số đáng nhớ: ngân sách calibrate B1 dự kiến = 3 giá trị × 12 tham số × 2 hướng = **72 trial**, trong khi mỗi fold WFO chỉ có ~**9 lệnh** (28 chia 3). **Ngân sách tinh chỉnh lớn hơn số lệnh nhiều lần** |
| 2.1b Tham số thật sự điều khiển hành vi | 🔴 **KHÔNG ĐẠT** (`đo-được`) | `docs/du-lieu-do/td0195-duong-doc-tham-so-tier-b.json`: **7/12 không có đường đọc** từ YAML vào đường chạy (`zss_threshold`, `buf_sl_atr`, `wick_close_upper_frac`, `v_min`, `funding_rate_pct`, `dg6d_retrace_frac`, `dg6a_atr_ratio`) — thay vào đó là bản sao hardcode ở `src/tool_d/zone_strength.py`, `trade_plan.py`, `dg6_early_invalidation.py` | Đã có chỗ theo dõi: **MT-23 / TD-0195**. Không mở việc trùng. Nêu ở đây vì checklist hỏi đúng câu này và câu trả lời là "không". ⚠️ Xem ghi chú đơn vị ngay dưới bảng |
| 2.2 Chia **60-70% train / 30-40% test** | ✅ **CHẶT HƠN** (`đo-được`) | Ba phân vùng CALIB/WFO/LOCKBOX (DR-011) + lockbox **chạm đúng một lần**, niêm phong SHA-256 | Checklist chỉ đòi hai phần; Tool D có ba, phần cuối chỉ dùng được một lần trong đời dự án |
| 2.3 Chạy lại backtest bằng tham số tối ưu trên tập test riêng | 🔴 **CHƯA ĐO** (`đo-được`) | `registry/runtime_state.json` khoá `d3_han_che` **tự khai**: cổng D3 chứng nhận *bộ điều phối* H3-D đúng, **không** chứng nhận đã có kết quả walk-forward | **Chưa có lần chạy WFO thật nào.** Cổng D3 đã đóng nhưng nó cố ý không tự phong cho mình nhiều hơn thế |
| 2.4 Hàm loss không chỉ là "total profit" | ✅ **CHẶT HƠN** (`đo-được`) | §10.2 Nhánh 1 đòi đồng thời: DSR-adjusted expectancy ≥ ngưỡng, `liq_buffer ≥ 8`, `max_single_trade_loss / risk_budget ≤ 1.15`, skewness không âm hơn Z1 quá 0,5, PBO ≤ 0,5 qua CSCV | 🔴 **KHÔNG áp dụng mục *"chênh IS/OOS > 30-40% là đáng lo"* của checklist.** Đó là tiêu chí thứ hai cho câu hỏi §10.2 đã trả lời bằng DSR + PBO — thêm vào là tạo hai nguồn phán quyết, đúng thứ MT-03 cấm |
| 2.5 Walk-forward nhiều đoạn, không chỉ một lần train/test | ✅ **CHẶT HƠN về thiết kế, CHƯA ĐO về kết quả** | `so_fold: 3`, `train_khoi_tao_tuan: 12`, `test_tuan: 7` (`config/tool_d_config.yaml:129-131`) | Bộ điều phối có, **kết quả chưa có** (xem 2.3) |

⚠️ **Ghi chú về `funding_rate_pct` — một chỗ dễ đọc quá tay, đã kiểm và KHÔNG kết luận.**
`td0195-...json` ghi `khop_yaml: false` cho khoá này (YAML `-0.05` vs hằng `NGUONG_FUNDING_D =
-0.0005`). Nhìn qua thì giống lệch 100 lần, **nhưng phép so đó mù đơn vị**: tên khoá là
`funding_rate_pct` (đơn vị *phần trăm*) và chú thích ngay cạnh hằng số viết `# -0.05%`
(`src/tool_d/dg6_early_invalidation.py:38`) — tức `-0.05%` và `-0.0005` là **cùng một giá trị**.
Vậy đây **không phải** bug giá trị đã chứng minh. Cái đáng lo là thứ khác và có thật: **vì không
có đường đọc nào, chưa ai chốt được khoá YAML này sẽ mang đơn vị nào lúc nối dây** — hai cách hiểu
lệch nhau 100 lần và cả hai đều đọc xuôi. Ghi để người nối dây (MT-23/TD-0195) không phải đoán.
*(Số dòng `:25` trong file JSON đã lỗi thời — hằng số hiện ở `:38`.)*

### GĐ3 — Forward test bằng dry-run

| Mục checklist | Trạng thái | Bằng chứng | Ghi chú |
|---|---|---|---|
| 3.1 Dry-run vài tuần đến vài tháng, không rút ngắn | ⏳ Chưa tới lượt | D11 chưa mở; `registry/runtime_state.json` chỉ có 5 khoá cổng, mới nhất là `d3_5_complete` | — |
| 3.2 So sánh performance dry-run vs backtest kỳ vọng | ⏳ Chưa tới lượt, **nhưng đã có máy** | D3.5 (DR-015) đã đo sai lệch thước đo và niêm phong Δ_R | Tool D làm việc này **sớm hơn** checklist: đo lệch TRƯỚC khi có kết quả để so |
| 3.3 **Alert tự động** (Telegram/Discord) khi bất thường | 🟡 **CHƯA CÓ** (`đo-được`) | Chuỗi `telegram` chỉ xuất hiện ở `config/freqtrade/config.json` (mặc định tắt) và trong spec/template — **không module cảnh báo nào trong `src/`** | → **TD-0209** (mở 10/09/2026). 🔑 Khác Risk Supervisor §6.6: §6.6 giám sát margin/thanh lý, **không** giám sát *"tiến trình có đang chạy hay không"*. Hạn: trước D11 |
| 3.4 Xử lý edge case: mất API, lỗi lệnh, sàn maintenance | 🟡 **MỘT PHẦN** (`đo-được`) | Rate-limit + circuit breaker cho `binance_public.py`: **TD-0197 ✅**. Còn thiếu: validate fail-closed khi thiếu `BINANCE_API_KEY`/`BINANCE_API_SECRET` — mục (3) dòng `D10–D12` của `TASKS.md`, **vẫn 🔓 chưa có mã việc** | Không tự gộp vào TD-0209 — để chủ dự án quyết có tách số riêng |

### GĐ4 — Thêm FreqAI → **N/A: CẤM.** Nhưng hai nguyên lý con vẫn áp dụng và đáng đọc

| Mục checklist | Trạng thái | Bằng chứng | Ghi chú |
|---|---|---|---|
| 4.1 Số features hợp lý so với số mẫu training | 🔴 **ánh xạ được, và KHÔNG ĐẠT** | Từ vựng khác, cùng một nỗi lo: *"features vs mẫu"* của FreqAI = *"**12 DOF vs n ≈ 28 lệnh**"* của Tool D | Đây là lý do rào DSR tồn tại. Nhưng rào phạt **sau khi đo**; nó không cứu được việc mẫu quá nhỏ để phân biệt các arm với nhau (xem MT-26) |
| 4.2 Feature importance, loại feature đóng góp ~0 | ✅ **có cơ chế tương đương** | Chín arm ablation §10.1/§10.1b chính là phép đo "thành phần nào đóng góp gì" | Chưa chạy được (TD-0184 bị chặn) |
| 4.3 **Không có data leakage** | ✅ **ĐẠT** (`đo-được`) | Đã tự bắt hai ca thật: (i) `dp.get_pair_dataframe()` gọi từ callback trả **cả nến tương lai** — phải đi qua `_df_4h()` cắt `date + 4h ≤ now`; (ii) `lookahead-analysis` của Freqtrade đã chạy thật ở TD-0106, không thấy bias | Mục duy nhất của GĐ4 áp dụng được, và Tool D đạt |
| 4.4 / 4.5 Model lọc tín hiệu, hiểu train/test split của FreqAI | **N/A — CẤM** | `tool-d-smart-dca.md:462-473`; `L-Z24` kiểm `freqai.enabled = false` | — |

### GĐ5 — Live vốn nhỏ, tăng dần

| Mục checklist | Trạng thái | Bằng chứng | Ghi chú |
|---|---|---|---|
| 5.1 Vốn khởi điểm chấp nhận mất hoàn toàn | ⏳ Chưa tới lượt (D12) | `E_D = 750` USDT (`DR-D4-05`, nâng từ 500) | — |
| 5.2 Bảng theo dõi rolling mỗi ~50 lệnh | ✅ **CHẶT HƠN** | Điểm quyết định mỗi **100 lệnh đóng**; tái tạo ngân sách 1 trial / 25 lệnh, trần B3 ≤ 20 | Nhịp thưa hơn checklist nhưng gắn với **ngân sách trial**, không chỉ là bảng theo dõi |
| 5.3 **Định trước ngưỡng dừng**, không quyết cảm tính lúc đang lỗ | ✅ **CHẶT HƠN** | `dd_ladder_pct: { soft: 5, halt: 8, abort: 20 }` (`config/tool_d_config.yaml:122`, `DR-D0PRE-04`) — viết trước, có máy canh | Đúng tinh thần checklist, nhưng thi hành bằng máy thay vì kỷ luật con người |
| 5.4 Lịch review định kỳ cố định | ✅ **CHẶT HƠN** | `DR-012` change-control có hiệu lực từ D12; `L-Z26`/`L-Z28` chặn đổi tham số không qua sổ đề xuất | — |

---

## §3 — Bế tắc cỡ mẫu: các đường ra và cái giá của từng đường

**Tài liệu này KHÔNG chọn.** Quyết định thuộc chủ dự án và đang treo ở `DR-D4-08 §6`.

**Con số chặn** (đo trên EXPLORE, 0 trial; đã kiểm lại **sau** bản vá TD-0207 — xem bảng ở §0):

| Đại lượng | Đo được | Yêu cầu | Thiếu |
|---|---|---|---|
| Lệnh/năm quy đổi pool 102, arm `Z0`, cửa sổ WFO | **44,8** | ≥ **150** (§10.2, `:4274`) | 3,3 lần |
| Lệnh trong cả cửa sổ WFO (`n`) | **≈ 28** (22 lệnh thật / 88 mã EXPLORE) | ≥ **90** (30/fold × 3 fold) | 3,2 lần |
| Lệnh cho ý nghĩa thống kê theo checklist | **≈ 28** | ≥ **100** | 3,6 lần |

Ba yêu cầu độc lập nhau — **checklist ngoài, sàn §10.2 của spec, và sàn nội bộ của WFO** — đều bị
trượt cùng một hệ số ~3,3. Đó là điểm đáng chú ý: không phải một ngưỡng khắt khe bất thường, mà ba
chuẩn khác nguồn cùng nói một điều.

| Đường ra | Cái giá phải trả |
|---|---|
| **Nới bộ lọc trend Phần 2** | Đây là chốt cắt 97,1% nên nó là đòn bẩy mạnh nhất về số lệnh. Nhưng nới thì `Z0` **đổi định nghĩa** ⇒ mọi phép đo trước đó không so trực tiếp được (`DR-D4-08 §8`). Nặng hơn: nới **sau khi đã nhìn thấy** số lệnh chính là hình dạng overfitting mà checklist cảnh báo, và là thứ DR-010 sinh ra để chặn |
| **Mở rộng pool > 102 mã** | Đụng `DR-D0PRE-05` (tiêu chí pool đã chốt, tiêu 4 trial B0). Mã thêm vào là mã thanh khoản kém hơn ⇒ min-notional và `SizingError` tăng (đã đo: arm `Z0-T0` có 4.119 `sizing_error`, rớt 42 mã) |
| **Kéo dài cửa sổ về trước T0** | T0/T1/T2/T3 đã **niêm phong** (`DR-D0PRE-07`, `config/tool_d_config.yaml:123`, ghi rõ *"commit, không sửa"*). Và độ dài lịch sử OI đã verify ở D0-PRE là có hạn |
| **Hạ sàn 150 bằng một DR mới** | Làm được về thủ tục, nhưng DR phải viết **TRƯỚC khi thấy kết quả gate** (`:3956-3958`). Hạ một chốt **vì nó đang chặn** đúng là bài học cổng D3 đã trả giá: *"một chốt không bao giờ thoả được thì tệ hơn không có chốt"* — nhưng chiều ngược lại cũng đúng, một chốt hạ xuống vừa đủ để qua thì không còn là chốt |
| **Chấp nhận đọc D4 là INCONCLUSIVE** | `DR-D4-09` đã dựng sẵn phép so paired + tách INCONCLUSIVE khỏi FAIL, nên đọc được. Nhưng tiêu **9 suất trial** để mua một kết cục đã biết trước chính là thứ `DR-D4-08 §6` viết ra để chặn |
| **Dừng ở kết luận "Z0 single-entry"** | §10.1 nói thẳng: nếu Z0 ≥ Z3/Z3b thì bỏ DCA, Tool D thành single-entry, và đó là **kết quả TỐT, không phải thất bại**. Rẻ nhất về ngân sách. Giá phải trả: bỏ hẳn phần DCA — thứ đặt tên cho cả dự án |

🔑 **Một quan sát có thể đổi cách đọc bảng trên.** `Z0` là arm **đã lọc trend đầy đủ**; `Z0-T0`
(không lọc trend) cho **746 lệnh** trên cùng cửa sổ, `Z0-T1` cho **160**. Nếu câu hỏi D4 đọc theo
thứ tự — *trả lời "lọc trend có đáng không" TRƯỚC, rồi mới hỏi "DCA có đáng không"* — thì các arm
`Z0-T0`/`Z0-T1` **không thiếu mẫu**. Bế tắc cỡ mẫu là bế tắc của **những arm đã lọc trend**, không
phải của toàn bộ D4. Đây là **quan sát, không phải đề xuất đổi thứ tự** — đổi thứ tự đọc một
ablation đã đăng ký là việc phải qua DR.

---

## §4 — Phát hiện phụ (đề xuất, không tự sửa)

1. **Spec §10.2 để trống ô ngưỡng DSR, trong khi code đã có số.**
   `tool-d-smart-dca.md:4260` vẫn là `DSR-adjusted expectancy ≥ ......  🔴 PHẢI ĐIỀN SỐ Ở D0-PRE`,
   còn `src/tool_d/gates/thresholds.py:24` có `DSR_ADJ_EXPECTANCY_MIN = 0.10` theo `DR-D0PRE-03`
   (blocker B6 đã gỡ). **Code đi trước spec.** N1 nói spec thắng khi mâu thuẫn — nhưng ở đây spec
   là **ô trống**, không phải một giá trị khác, nên đây là trôi lệch tài liệu chứ không phải xung
   đột giá trị. Không tự sửa spec (quy tắc 5). Đề xuất ghi thành một mục MT.
   *(Ghi nhận kèm: `thresholds.py:30` giữ `BEST_KNOWN_DSR_ADJ_EXPECTANCY = -inf` — đúng N6, vì
   chưa có lần đánh giá nào.)*

2. **Bảng MT trong `back-end-note.md` có hai dòng trạng thái lỗi thời.** MT-15 ghi *"CHƯA CHỐT —
   chờ chủ dự án"* trong khi `DR-D4-03` đã chốt và thi hành; MT-18 vỡ format bảng nên dễ đọc nhầm.
   Đề xuất sửa dòng trạng thái, chờ duyệt (Phụ lục B) — không tự sửa file đặc tả.

3. **Mâu thuẫn thật giữa checklist và DR-014, đề xuất ghi thành MT (chờ lệnh "chuẩn hóa và lưu").**
   Checklist GĐ1 đòi expectancy dương ở **backtest thô, chưa tối ưu gì**, và cho phép vòng lặp
   *đo → sửa logic → đo lại*. `DR-014 §2` định nghĩa **mọi lần đánh giá cấu hình** trên
   CALIB/WFO/LOCKBOX = **1 trial**; N6 cấm điền `0.0` thay cho "chưa đo"; và `CTRL_OUTPUT_ALLOWED`
   cố ý **không chứa chỉ số hiệu năng nào** (`:3605-3607`). ⇒ **Vòng lặp của checklist không mua
   được trong ngân sách N = 114.** Ghi nhận theo quy tắc 11, **không tự chọn bên**.
   Họ hàng gần với **MT-19** nhưng khác đối tượng: MT-19 về **đại lượng mô tả**, cái này về **chỉ
   số hiệu năng**.

---

## Nguồn tham chiếu nhanh

- Cấm hyperopt: `tool-d-smart-dca.md:448-460` · cấm FreqAI: `:462-473` · chặn D11: `:2954` ·
  sàn 150 lệnh/năm: `:4274` · ô ngưỡng DSR còn trống: `:4260` · danh sách trắng CTRL: `:3605-3607`
- `N_ĐĂNG_KÝ = 114`: `src/tool_d/gates/dsr.py:24` · ngưỡng gate: `src/tool_d/gates/thresholds.py:24`
- Mốc dữ liệu + fold + thang drawdown: `config/tool_d_config.yaml:122-132`
- Trạng thái tham số: `config/param_status.yaml` · sổ trial: `registry/trial_registry.jsonl`
- Phép đo lệnh/năm: `docs/du-lieu-do/td0205-lenh-nam-wfo-explore.json` (WFO) và
  `td0193-lenh-nam-explore.json` ([T0,T2]) · đường đọc tham số: `td0195-duong-doc-tham-so-tier-b.json`
