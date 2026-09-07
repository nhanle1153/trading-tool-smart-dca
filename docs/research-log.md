# research-log.md — Nhật ký nghiên cứu Tool D

> **Append-only.** Không sửa, không xoá mục cũ. Ghi theo ngày, mục mới xuống dưới.
> Bắt buộc ghi mỗi lần: chẩn đoán "bot sai hay tầng đo sai" (§0d.7), quyết định chọn mốc dữ liệu
> (DR-011), và mỗi rủi ro tồn dư được chấp nhận có ý thức.

---

## 06/09/2026 — Khởi tạo repo, Giai đoạn 1–2

- Khởi tạo git repo, cây thư mục, 4 file quy trình.
- Chốt 7 quyết định nền tảng (xem `back-end-note.md` §0.2 và bảng đầu `TASKS.md`).
- Ghi nhận 7 mâu thuẫn, 5 trong đó đã chốt cách giải ngay (`back-end-note.md` mục 7).

### Rủi ro tồn dư được chấp nhận có ý thức

**RR-01 — L-Z25 không chứng minh được tuyệt đối rằng chưa từng chạy hyperopt.**
Spec (dòng 510) đòi grep cả "lịch sử lệnh". Kiểm được: `git grep` trên worktree,
`git log -S hyperopt --all` (bắt cả file đã xoá rồi), và `runs/cmd_audit.log` do wrapper tự ghi.
KHÔNG kiểm được: người dùng gõ thẳng `docker run ... freqtrade hyperopt` ngoài wrapper.
Chấp nhận vì cùng loại với thừa nhận của chính spec ở dòng 3317–3320 (cơ chế lockbox không cứng)
và 3507–3510. Biện pháp bù duy nhất là kỷ luật cá nhân — đã ghi thành điều cấm N3 trong `CLAUDE.md`.

**RR-02 — Lockbox chỉ tồn tại trên một ổ đĩa.** Dữ liệu lockbox không commit lên git (kích thước),
và spec dòng 4002 nói rõ không có lockbox thứ hai. Mất ổ = mất khả năng xác nhận cuối cùng của
cả dự án. Đã mở TD-0085 (backup ngoài git + **test khôi phục thật**) và OQ-08. Cho tới khi TD-0085
xong, đây là điểm hỏng đơn lẻ nghiêm trọng nhất của toàn bộ hạ tầng.

## 06/09/2026 — TD-0031, phát hiện lỗi số học trong comment gốc của spec §6.9.5

Xác nhận lại bảng DOF của DR-010 từng dòng (yêu cầu TD-0031). Hai phép cộng trực tiếp đều khớp
số cuối cùng của spec:
- Σ(v5 của 26 dòng bảng) + Σ(2 mục "bỏ sót" DG7, w_tranche) = 26 + 2 = **28** = DOF_gốc ✅
- Σ(cột dof_v6 của 26+2 dòng) = **12** = |tier_b| ✅

Nhưng **chuỗi trừ trung gian** trong comment gốc (chép nguyên văn từ spec §6.9.5 vào
`tool_d_config.yaml` ở TD-0013, trước khi TD-0031 sửa lại):
```
28 - 6 (đóng băng) - 4 (pool→B0) - 2 (xoá §2.4,§3.3c)
   - 1 (mult_dd→Cấp C) - 1 (L_BASE→mult_regime đóng băng)
   - 1 (zone_width, có điều kiện) = 12
```
Tính literal: `28−6−4−2−1−1−1 = 13`, không phải 12. **Nguyên nhân:** khoản "−1
(L_BASE→mult_regime đóng băng)" bị đếm **hai lần** — `mult_regime` (dof=−1) đã nằm sẵn trong
tổng "−6 (đóng băng)" của `tier_frozen` (5 khoá đóng góp: w_zss −2, mult_regime −1,
tp2_trail_atr −1, dg6b_bars_1h −1, trend_age_days −1 = −6), không phải một khoản trừ độc lập.

**Mức độ:** không phải mâu thuẫn 🔴 chặn tiến độ — không đổi bất kỳ số quyết định nào
(`tier_b=12`, `DOF_gốc=28`, `N_ĐĂNG_KÝ=114` đều được xác nhận độc lập bằng phép cộng trực tiếp,
không đi qua chuỗi trừ có lỗi). Xử lý: `config/dof_inventory.yaml` (TD-0031) dùng cách kiểm
KHÔNG đi qua chuỗi trừ này — cộng trực tiếp cột `v5`/`v5_dung_ra` và cột `dof_v6` của từng dòng.
`src/tool_d/config/dof.py` (`dof_report()`/`assert_dof_or_block()`) tự động hoá phép kiểm này,
canh bởi L-Z29 vế (b).

**Bài học:** đây đúng loại lỗi mà chính DR-010 sinh ra để chặn (v5 cũng từng có phép trừ không
ra số đúng, dòng 3168-3180 của spec) — cho thấy kiểm bằng tay dễ sai ngay cả khi người viết đã
cẩn thận, và củng cố lý do L-Z29 phải là kiểm TỰ ĐỘNG, không phải đối chiếu bằng mắt.

## 06/09/2026 (buổi tối) — 3 lần đánh dấu sai TASKS.md do 2 phiên chung 1 thư mục

Trong một phiên làm Khối 5, phát hiện **3 lần riêng biệt** một dòng `TASKS.md` bị đánh dấu ✅ dù
chưa có code/test thật tương ứng trên đĩa:

1. TD-0051 (`ledger/registry.py`) — do `sed` của chính phiên này chạy đúng lúc phiên kia cũng đang
   sửa `TASKS.md`, `git add` gộp cả hai thay đổi vào một commit.
2. TD-0052→0056 (5 dòng liền, Khối 5) — cùng cơ chế, quy mô lớn hơn (5 dòng một lúc).
3. TD-0057 (nối E6 vào E1/E2/E3) — `git add TASKS.md` chụp luôn một thay đổi ✅ mà phiên kia vừa
   ghi song song, trong khi `grep run_audit entrypoints/*.py` xác nhận E1/E2/E3 chưa hề gọi hàm đó.

**Nguyên nhân gốc:** `TASKS.md` là bảng sửa-tại-chỗ (mỗi lần đổi trạng thái = ghi đè dòng cũ), và
`git add <file>` chụp toàn bộ nội dung trên đĩa tại thời điểm gọi — không có cách nào để `git add`
phân biệt "dòng tôi vừa sửa" với "dòng phiên kia đang gõ dở cùng lúc" khi cả hai cùng sửa một file.

**Quyết định của chủ dự án** (hỏi trực tiếp, không tự chọn): KHÔNG đổi định dạng `TASKS.md` sang sổ
nhật ký append-only (dù đúng pattern MT-01 đã dùng cho `trial_registry.jsonl`), KHÔNG chuyển sang
git worktree riêng cho mỗi phiên — giữ nguyên cách làm việc hiện tại (2 phiên chung 1 thư mục), chỉ
**siết kỷ luật git**. Đã ghi thành quy tắc bắt buộc ở `CLAUDE.md` mục N12: luôn `git diff` đối chiếu
trước khi commit đụng `TASKS.md`, không bao giờ tin một dòng ✅ mà không xác minh bằng chứng trên
đĩa trước khi dùng nó làm điều kiện phụ thuộc cho việc tiếp theo.

**Rủi ro tồn dư đã chấp nhận có ý thức:** kỷ luật git là biện pháp con người, không phải cơ chế kỹ
thuật — vẫn có thể tái diễn nếu một phiên quên đối chiếu diff. Không có lớp chặn tự động nào khác
được dựng thêm theo quyết định này.

## 06/09/2026 (buổi tối) — TD-0080: xác nhận Open Interest chỉ có ~30 ngày lịch sử

Gọi thật `GET /futures/data/openInterestHist?symbol=BTCUSDT&period=1d&limit=500` (xin tối đa 500
bản ghi) — Binance chỉ trả về **31 bản ghi**, từ 2026-08-07 đến 2026-09-06 (**30 ngày**). Xác nhận
đúng nghi vấn spec dòng 4457-4460: endpoint OI history của Binance USDⓈ-M Futures **KHÔNG** giữ lịch
sử dài — giới hạn cứng ~30 ngày, không phụ thuộc `limit` xin nhiều hơn.

Xác nhận qua hai đường độc lập: (1) `curl` trực tiếp trong container, (2)
`entrypoints/backfill_data.py --probe-coverage` (TD-0080, gọi qua `src/tool_d/api_client/binance_public.py`
— điểm gọi mạng DUY NHẤT, R1 Single Egress). Cả hai cho cùng kết quả.

**Ảnh hưởng thiết kế (cần chủ dự án lưu ý khi tới D1 — chưa xử lý ở D0-PRE):**
- Bất kỳ ý tưởng dùng OI làm chỉ báo (VD Idea Queue IQ-0001 ví dụ trong fixture test) chỉ có thể
  backtest trên **cửa sổ 30 ngày gần nhất**, không thể dùng OI cho CALIB dài hạn (thường cần nhiều
  tháng). Đây là giới hạn CỨNG của nguồn dữ liệu, không phải thứ có thể "tải thêm" hay "trả tiền để
  có nhiều hơn" — Binance đơn giản không giữ dữ liệu đó.
- Nếu về sau muốn OI dài hạn hơn 30 ngày, phải tự lưu trữ liên tục từ bây giờ (bắt đầu tích luỹ lịch
  sử của chính mình) hoặc tìm nguồn thứ ba — cả hai đều là quyết định lớn, không tự động áp dụng.
- **Không ảnh hưởng D0-PRE hay Zone Absorption cốt lõi** (không dùng OI) — chỉ ảnh hưởng nếu Idea
  Queue sau này chọn một giả thuyết liên quan OI.

Không cần DR (không phải quyết định, chỉ là một sự thật đo được về hạ tầng dữ liệu bên ngoài).

## 06/09/2026 (đêm) — TD-0041/0042/0043: ba con số Tầng A/C và ngưỡng DSR đã chốt; TD-0082 kiểm min notional

Chủ dự án chốt sau khi xem bảng đánh đổi (không có backtest nào chạy — đúng yêu cầu spec là điền TRƯỚC
khi thấy số, dòng 3956-3958, 4425-4449):

- **DR-D0PRE-03** — ngưỡng `DSR-adjusted expectancy` Nhánh 1 = **0,10 R**. Spec để lộ hai khoảng trống
  (chưa có công thức, chưa có số); công thức chốt `mean(R) − √(2·ln N)·std(R)/√n_trades`, số suy từ chi
  phí backtest không thấy (trượt giá SL 0,02–0,04 R/lệnh) × hệ số an toàn 2–3. **Blocker B6 gỡ.**
  L-Z35 chuyển sang biến thể "kết quả tốt nhất hiện có vẫn FAIL" với best-known = −inf (chưa đo, N6).
- **DR-D0PRE-04** — thang drawdown giữ **5/8/20%** (Cấp C, Hạng 0). Test mới canh `halt == daily_loss_budget_pct`.
- **DR-D0PRE-06** — `E_D` **500**, `L_exchange` **3x**, `rho` 0,375%, lỗ/ngày 8%. Tôi khuyến nghị ≥ 1.000
  (giữ 91–98/102 mã qua L-Z20), chủ dự án chọn 500 và chấp nhận mất ~20% pool ở zone rộng.
  Phát hiện kèm: `tradable_balance_ratio` trong `config/freqtrade/config.json` là 0.99 (mặc định
  Freqtrade sót từ TD-0026), spec §6.8 đòi 0.5 với ví 1.000/E_D 500 → đã sửa.
- **TD-0082** — bảng `docs/min-notional-check.md` (E7 `--check-min-notional`, metadata thật): min notional
  **102/102 qua** ở ca xấu nhất (tranche 1 = 20,8 USDT; 4 mã sàn 20 USDT sát sàn — `E_D` < 480 sẽ rớt).
  L-Z20 làm tròn lot: 21/11/8 mã rớt ở R_eff 3%/1,5%/0,9% — hệ thống từ chối theo zone, không mất tiền,
  không sửa gì ở D0-PRE. Không cần DR (không có vi phạm min notional).

Ghi nhận từ phiên song song (front-end), chưa xử lý, không phải của phiên này: CLAUDE.md (chưa commit)
nêu mâu thuẫn `CTRL` có tính vào N hay không — `registry.n_used()` hiện cộng mọi trial CONSUMED kể cả
CTRL. Sẽ xử lý theo Quy tắc gốc #11 khi phiên kia commit xong (đợi để không giẫm file).

## 06/09/2026 (khuya) — TD-0084: chốt mốc CALIB/WFO/LOCKBOX bằng giá BTC futures thật + niêm phong

Đo chế độ thị trường bằng dữ liệu thật (1000 ngày nến 1d BTCUSDT futures, `get_klines()` mới thêm vào
`binance_public.py`) thay vì suy đoán trên giấy — không phải "chạm dữ liệu" theo MT-02 (đo BTC tổng
quát, không đánh giá cấu hình chiến lược nào).

Phát hiện: đỉnh toàn kỳ $124.628 ngày 06/10/2025, sau đó BTC rơi vào một đợt sập kéo dài — drawdown
liên tục dưới -30% từ 29/01/2026 tới nay (06/09/2026, hiện -38%, đỉnh sập -53% ngày 30/06/2026),
KHÔNG hồi phục lại trên -30% một lần nào suốt 220 ngày. Khác hẳn giai đoạn trước (drawdown trung bình
chỉ -11% đến -14%). Trình 3 phương án tỷ lệ LOCKBOX (20/25/30%), chủ dự án chọn 25%.

Mốc chốt (DR-D0PRE-07): T0=09/04/2024, T1=12/06/2025 (CALIB 429 ngày), T2=29/01/2026 (WFO 231 ngày),
T3=06/09/2026 (LOCKBOX 220 ngày, hôm nay). Tải thật 510 file OHLCV (1h/4h/1d + mark/funding_rate 1h,
futures, 102 mã pool) qua `freqtrade download-data` (service `lockbox`), niêm phong `lockbox_seal_1.json`
qua `touch_lockbox.py --seal-initial` (cờ mới, E4).

**Sự cố bắt được trước khi lan rộng:** `--verify-seal` FAIL 100% (510/510 "MISSING") ngay sau khi niêm
phong — không phải lỗi dữ liệu, mà là bug thật trong `run_backtest.py`/`run_wfo.py`/`run_ablation.py`/
`touch_lockbox.py`: `verify_all_seals()` được gọi với `LOCKBOX_DATA_DIR` (`lockbox/data`) trong khi
`build_seal()` hash file ở `lockbox/data/futures/` (Freqtrade `--trading-mode futures` luôn lồng thêm
thư mục con). Bug này tồn tại từ TD-0071/TD-0072 nhưng chưa từng bị bắt vì D0-PRE chưa có seal thật
(0 seal = verify PASS rỗng, che mất lỗi đường dẫn) — đúng mẫu hình N10: tưởng lỗi dữ liệu, hoá ra lỗi
tầng đo (ở đây là tầng verify, không phải tầng đo lường số liệu, nhưng cùng nguyên tắc "kiểm tầng đo
trước khi nghi ngờ dữ liệu"). Sửa cả 4 điểm gọi, thêm test khoá `test_dung_thu_muc_futures_khong_phai_thu_muc_data_cha`
chống hồi quy. Cũng dọn 5 file test BTC còn sót từ lúc thăm dò thủ công (BTC bị loại khỏi pool giao
dịch — EXCLUDE_FROM_TRADING) trước khi niêm phong, tránh lẫn vào seal vĩnh viễn.

Toàn bộ suite Docker: 342 passed sau khi cập nhật 3 file test theo trạng thái mới (seal thật tồn tại;
service `tests` che `lockbox/data/` nên `--verify-seal` ở đó PHẢI báo lệch — đúng thiết kế cách ly,
không phải lỗi; xác nhận PASS thật chỉ làm được qua service `lockbox`).

## 06/09/2026 (khuya, tiếp) — TD-0085: backup lockbox + test khôi phục thật

Chủ dự án chọn nơi lưu: một thư mục khác trên cùng máy (`E:\lockbox-backup-tool-d\`) — nhanh, làm
ngay được, nhưng chưa chống mất máy vật lý (nâng cấp cloud để sau, ghi ở DR-D0PRE-08 mục 4).

Dựng `src/tool_d/lockbox/backup.py` (sao chép seal + `lockbox/data/`, không sao chép sổ truy cập —
backup không phải một điểm chạm) + hai cờ CLI mới trên E4: `--backup-to`, `--verify-backup`.

**Chạy backup thật + khôi phục thật một lần (không phải seal giả trong `tmp_path`):**
1. `--backup-to E:/lockbox-backup-tool-d` → 510 file, 39MB, khớp nguồn.
2. `--verify-backup` trên bản backup → PASS.
3. Mô phỏng mất ổ đĩa gốc: copy bản BACKUP sang thư mục tạm hoàn toàn mới, `verify_seal()` độc lập →
   510/510 khớp, PASS. Xoá thư mục tạm sau khi xác nhận.

**Sự cố kỹ thuật gặp phải (không phải lỗi logic, môi trường Docker-trên-Windows):** thử backup ra
ngoài bind-mount qua đường dẫn container (`/workspace/../...`) thất bại vì đường dẫn đó nằm ngoài mọi
volume mount — không map được ra ổ đĩa host. `backup_lockbox()` là I/O file thuần (không cần
Freqtrade), nên chạy trực tiếp bằng Python host hợp lệ theo đúng phạm vi N7 (N7 chỉ áp cho BẰNG CHỨNG
đo lường/backtest, không áp cho thao tác vận hành copy file).

**Sự cố dây chuyền khi chạy full suite lần đầu sau TD-0085:** 3 test `periodic_report` fail thoáng qua
vì `git status --porcelain` (bên trong `get_git_info()`) timeout 10s — do hệ thống đang chạy nhiều
lệnh Docker liên tiếp (backup, download, nhiều lần `docker compose run`) cùng lúc, không phải do
lockbox/data (thư mục đó bị volume ẩn danh che trong service `tests`, không hề lớn ra ở đó). Chạy lại
sạch (không có tải Docker khác chạy song song) → 347/347 passed, hai lần liên tiếp — xác nhận đây là
nhiễu tải hệ thống, không phải hồi quy thật.

Toàn bộ suite Docker: 347 passed (tăng 5 so với TD-0084 — thêm `test_lockbox_backup.py`).

## 06/09/2026 (khuya, cuối) — TD-0086: 🚪 GATE D0-PRE ĐÓNG

Ba điều kiện chạy THẬT (không mock), theo đúng thứ tự spec đòi:

1. `docker compose run --rm tests -q tests/lock` → **215 passed, 0 failed**.
2. `entrypoints/trial_ledger_audit.py` → exit 0, "đã audit 4/6 (4 đạt, 0 chưa đạt, 2 chưa đo được)".
3. `entrypoints/periodic_report.py` → exit 0, 22/22 chỉ số "chưa đo được" (đúng thiết kế D0-PRE, chưa
   có lệnh đóng thật nào), không sentinel nào lọt (L-Z41 tự kiểm trong chính E5).

Thêm `--close-gate` vào E6 (`trial_ledger_audit.py`) — chạy `run_audit()` thật, chỉ ghi
`registry/runtime_state.json.d0_pre_complete: true` nếu audit sạch (fail=0), và tự từ chối ghi lại
nếu khoá đó đã có (bất biến, cùng triết lý "commit, không sửa" của lockbox seal). Chạy thật ngày
06/09/2026, xác nhận `is_d0_pre_complete()` trả `True`; chạy lại `--close-gate` một lần nữa → từ chối
đúng như thiết kế, không ghi đè.

Gắn tag `d0-pre-complete` tại commit đóng cổng. **D0-PRE (Khối 0→8) hoàn tất — 62/62 việc trong
TASKS.md.** `E1/E2/E3/E7/E8` từ nay có thể chạm CALIB/WFO/LOCKBOX thật khi Khối chiến lược (D1) tới
lượt — điều kiện tiên quyết là `is_d0_pre_complete()` (đã tồn tại từ trước, chưa từng được nối vào
entrypoint nào; nối vào E1/E2/E3/E7/E8 là việc của D1, ngoài phạm vi D0-PRE này).

Toàn bộ suite Docker cuối cùng của D0-PRE: **352 passed**, hai lần chạy liên tiếp không có test nào
gián đoạn (loại trừ hẳn nghi ngờ nhiễu tải hệ thống ở lần chạy trước, TD-0085).

## 07/09/2026 — TD-0092 (H19 phần 2): độ phủ dữ liệu + cấm suy nguyên nhân khoảng trống

Quy tắc LD-28 là quy tắc về **hành vi con người** ("cấm quy một khoảng trống cho *sàn thiếu dữ liệu*
khi chưa hỏi lại sàn" — Tool A mất nhiều ngày vì đúng điều này). Viết vào tài liệu thì sẽ bị vi phạm
đúng lúc đang vội, nên cưỡng chế bằng **kiểu dữ liệu**, cùng thủ pháp `Measured` cấm bịa số: `Gap`
không có trường nào chứa được phỏng đoán; `Coverage.gap_cause` luôn khởi tạo `pending`; chỉ hai hàm
quy trách nhiệm đặt được nó, và cả hai đòi dữ liệu nguồn thật (`onboardDate` của sàn, hoặc hỏi lại
sàn đúng cửa sổ trống).

**Ba lỗi chỉ lộ ra khi chạy trên dữ liệu thật, test tự dựng không bắt được:**

1. **Sai đơn vị thời gian 10⁶ lần.** Cột `date` của Freqtrade là `datetime64[ms]`, `astype("int64")`
   đã ra mili-giây, nhưng code chia thêm 1e6 như thể nó là nano-giây. `backfill_guard` (TD-0091)
   cũng dính, nhưng vô hại vì sai nhất quán ở cả hai vế phép so — đúng loại lỗi ngủ yên tới khi có
   file khác đơn vị. Sửa bằng `timestamps_ms()` dùng chung, chuẩn hoá về ms trước khi đổi số nguyên.
2. **Báo động giả trên 102 file lành lặn.** `*-1h-funding_rate.feather` mang nhãn `1h` trong TÊN,
   nhưng sàn trả funding mỗi 8 giờ → đo theo bước 1h ra "thiếu 87,5%". Một công cụ cảnh báo sai 102
   lần thì lần thứ 103 (đúng) cũng bị bỏ qua — đúng cơ chế làm một lớp gác trở thành vô dụng. Loại
   nhóm này khỏi bảng tính-theo-khung kèm giải thích, KHÔNG suy nhịp từ chính dữ liệu (suy ra thì một
   chuỗi mất đều đặn nửa số điểm vẫn "đủ 100%" — chỉ số tự khen mình).
3. `Measured.render()` in `GapCause.LOI_CUA_TA` thay vì câu chữ người đọc được.

**Kết quả đo thật trên 102 mã pool, khung 1h, khoảng [T2,T3] của lockbox:** 101 file đủ, **1 file
thiếu — TRIAUSDT, 204 nến** (29/01 → 06/02/2026). Đối chiếu `onboardDate` thật từ `exchangeInfo`:
mã lên sàn **06/02/2026 12:15 UTC**, tức khoảng trống kết thúc ngay trước ngày niêm yết → kết luận
"chưa niêm yết tại thời điểm đó", **từ metadata sàn, không phải suy đoán**.

**Cả hai đường `--probe-gap` đã chạy thật với sàn:** cửa sổ trước niêm yết → sàn trả 0/169 nến →
"sàn thật sự không có"; cửa sổ bình thường (01→05/03) → sàn trả 97/97 nến → nếu ta thiếu cửa sổ đó
thì kết luận là "🔴 lỗi ở phía ta". Đây chính là phép kiểm Tool A đã bỏ qua, và nó mất 2 giây.

Suite Docker: 414 passed.

## 07/09/2026 — TD-0093: backfill THẬT CALIB [T0,T1] + WFO [T1,T2] cho 102 mã — bắt được bug tải quá phạm vi

Tải qua `freqtrade download-data` (service `freqtrade`, KHÔNG phải `lockbox` — thư mục làm việc
`user_data/data/binance/futures`, tách biệt vật lý với lockbox theo đúng DR-011): 510 file (102 mã ×
5 loại — `1h/4h/1d-futures`, `1h-mark`, `1h-funding_rate`), pairs lấy từ `config/pool.yaml.trading`
(102 mã, ghi ra `runs/pool_pairs.json`), `--timerange 20240409-20260129` (T0→T2, gộp CALIB+WFO một
lần tải vì hai đoạn dùng chung thư mục — chỉ LOCKBOX cần thư mục riêng theo spec DR-011).

🔴 **Bug thật bắt được TRƯỚC khi lan rộng, không phải lỗi dữ liệu:** freqtrade 2026.8
`download-data --timerange <start>-<end>` **KHÔNG tôn trọng mốc `<end>`** — log in đúng
"From ... to 2026-01-29T00:00:00" nhưng file thật trên đĩa chứa nến tới tận **2026-09-05**
(gần T3, tức đã lấn hẳn vào phạm vi LOCKBOX). Tái hiện độc lập với 1 mã/1 khung duy nhất
(`BTC/USDT:USDT`, 1d) trong thư mục rỗng riêng — 880 nến thay vì 661 nến đáng lẽ có, xác nhận không
phải do 102 mã hay do trộn nhiều lệnh gọi. Mức lấn khác nhau giữa các mã/khung (không phải một hằng
số "làm tròn tới hôm nay" đơn giản), khớp giả thuyết: freqtrade tải theo lô (batch theo `limit` của
Binance) rồi giữ nguyên cả lô cuối vượt mốc, không cắt lại theo `--timerange` sau khi tải xong OHLCV
(nó chỉ dùng `--timerange` để LỌC khi backtest đọc lại, không phải để cắt file lúc tải).

**Vì sao đáng dừng lại thay vì bỏ qua:** dữ liệu THẬT của khoảng LOCKBOX [T2,T3] giờ nằm thêm một bản
sao trong thư mục làm việc bình thường — đúng nơi mọi entrypoint D1 sẽ đọc — trong khi toàn bộ cơ chế
DR-011 dựa vào lockbox là nơi DUY NHẤT chứa dữ liệu đó, tách biệt vật lý. Nếu về sau `run_wfo.py`
hay `run_backtest.py` quên áp đúng cận trên `--timerange` (lỗi con người, không phải lý thuyết), dữ
liệu tương lai vẫn ngồi sẵn trong cùng file để lọt vào. Không sửa vì đây "chỉ là file trên đĩa, giới
hạn thật nằm ở tham số chạy" — đúng tinh thần LD-27/LD-28: không tin dữ liệu tự lành, phải kiểm rồi
sửa.

**Xử lý:** cắt lại toàn bộ 510 file về đúng ≤ T2 (2026-01-29T00:00:00Z) bằng thao tác đọc-lọc-ghi
trên chính các file thật — không phải "backfill" (không có nến mới nào được thêm), nên không đi qua
`--snapshot-before`/`--verify-after` (hai cờ đó gác chiều NGƯỢC LẠI: chống mất nến cũ, không phải
chống thừa nến mới). 506/510 file có nến bị cắt (tối đa 1.000 nến/file). 5 file rỗng sau khi cắt là
`TRIA_USDT_USDT-*` cả 5 loại — ĐÚNG theo kỳ vọng: TRIAUSDT niêm yết 06/02/2026, sau T2, nên 0 nến
trong [T0,T2] là chính xác, không phải lỗi cắt.

Sau khi cắt: chạy lại `--snapshot-before` (chụp baseline ĐÚNG phạm vi cho lần backfill tiếp theo),
verify độc lập `touch_lockbox.py --verify-seal` → **PASS** (lockbox không hề bị đụng trong suốt quá
trình — bug nằm ở thư mục làm việc, không phải lockbox), rồi `--verify-after` ngay trên snapshot vừa
chụp làm phép thử không đổi gì → PASS (xác nhận cơ chế H19 hoạt động đúng trên baseline đã sửa).

**Bảng độ phủ thật (khung 1h, `--coverage`), không suy nguyên nhân khoảng trống nào:**
- CALIB [09/04/2024 → 12/06/2025]: **101 file đo được** (loại 1 `TRIA*` rỗng đúng lý do niêm yết
  sau), **56 đủ 100%, 45 thiếu** — phần lớn là mã niêm yết muộn hơn T0 (0% ở một số mã), khớp đúng
  vấn đề survivorship bias mà TD-0095/96 (H1-D) sẽ xử lý, KHÔNG kết luận nguyên nhân ở đây.
- WFO [12/06/2025 → 29/01/2026]: **101 file đo được, 76 đủ 100%, 25 thiếu** — ít hơn CALIB vì đoạn
  ngắn hơn và gần hiện tại hơn, ít mã bị hụt đầu kỳ.
- 102 file `funding_rate` bị loại khỏi cả hai bảng (nhịp 8h thật, không đo theo khung file — xem
  TD-0092), in rõ lý do thay vì một con số sai.

Suite Docker: 422 passed.

## 07/09/2026 — TD-0095: khảo sát nguồn danh sách lịch sử — tìm được nguồn thật, KHÔNG chấp nhận bias

Giả định mặc định trong TASKS.md ("Binance API không trả danh sách symbol đã huỷ niêm yết → chấp
nhận survivorship bias") **sai** — không kiểm tra kỹ trước khi ghi vào backlog. Đo thật trước khi
kết luận (đúng N6/N10): gọi trực tiếp kho lưu trữ tĩnh công khai `data.binance.vision`
(`GET https://s3-ap-northeast-1.amazonaws.com/data.binance.vision/`, ListObjects chuẩn S3, phân
trang qua `NextMarker`) — kho này giữ nguyên thư mục nến lịch sử của MỌI symbol từng có trên
futures, kể cả đã huỷ niêm yết (khác `exchangeInfo` chỉ phản ánh hiện tại).

Kết quả đo thật: 1.027 thư mục symbol trong archive → loại 51 hợp đồng kỳ hạn + 103 không phải
quote USDT → còn 874 ứng viên perpetual/USDT. Đối chiếu `exchangeInfo` thật cùng lúc: 658 symbol
đang có (528 TRADING, 129 SETTLING, 1 PENDING_TRADING). **874 − 658 = 219 symbol đã thật sự huỷ
niêm yết**, còn dấu vết trong archive. Xác nhận archive cho ra được MỐC NGÀY thật (không chỉ tên):
liệt kê thư mục `BTTUSDT/1h/` → file đầu `2021-04-06`, file cuối `2022-01-26` — đúng khoảng tồn tại
thật của một symbol đã biết là bị huỷ từ lâu.

Ghi `docs/decisions/DR-D1-01-nguon-danh-sach-lich-su.md`: TD-0096 (`pairlist_point_in_time(t)`)
phải nạp 219 symbol này vào tập ứng viên khi tính pool tại mốc `t` quá khứ, không mở DR chấp nhận
bias. Giới hạn thẳng thắn: đây là kho cộng đồng/tĩnh, không có SLA chính thức (rủi ro tồn dư chấp
nhận được — kho đã ổn định nhiều năm, được `python-binance`/`freqtrade` dùng làm nguồn chuẩn); chỉ
cho biết khoảng tồn tại, không cho volume lịch sử trực tiếp (việc đó thuộc TD-0096).

Đây không phải "chạm dữ liệu" theo MT-02 — chỉ là dò xem symbol nào từng tồn tại và khi nào, không
đánh giá cấu hình chiến lược nào trên CALIB/WFO/LOCKBOX.

## 07/09/2026 — TD-0096: pairlist_point_in_time(t) — pool tại quá khứ, chống lệch sống sót

Mở rộng `SymbolStat` (`src/tool_d/pool.py`) thêm `delisted_at: datetime | None`, và thêm
`pairlist_point_in_time(stats, *, t, age_floor_days, volume_floor_usdt)`: loại mã chưa lên sàn tại
`t` (`onboard_date > t`) và mã đã huỷ niêm yết trước `t` (`delisted_at <= t`, dữ liệu thật đến từ
DR-D1-01) — cả hai trường hợp là KHÔNG TỒN TẠI tại `t`, không phải "trượt tiêu chí", nên bị loại
khỏi cả `trading` lẫn `explore`. Sau đó tái dùng `compute_pool()` cho hai tiêu chí thật (tuổi,
volume) tại đúng `t`.

`stat.quote_volume_24h` trong lời gọi point-in-time PHẢI là volume TẠI `t` do người gọi cung cấp —
hàm không tự suy hay tải dữ liệu (giữ đúng pattern thuần/không mạng như `compute_pool()`). Việc kết
nối thật với nguồn volume lịch sử theo ngày (tải qua `data.binance.vision`, DR-D1-01) và toàn bộ 219
mã đã huỷ là việc của TD-0097 (verify trên dữ liệu thật) — TD-0096 chỉ đảm bảo hàm ĐÚNG khi được cấp
dữ liệu đúng, kiểm bằng dữ liệu dựng tay (đúng pattern TD-0100/0101).

6 test mới (`tests/unit/test_pool.py::TestPairlistPointInTime`): mã lên sàn sau `t` không có mặt; mã
huỷ trước `t` không có mặt (khác mã huỷ SAU `t` — vẫn còn sống tại `t`, có mặt bình thường); thêm dữ
liệu về tương lai (mã mới, mã sắp huỷ) vào input không đổi kết quả của các mã khác — đúng tính nhân
quả H1-D đòi; volume/tuổi vẫn áp dụng bình thường tại `t`; BTC/ETH vẫn luôn vào EXPLORE ở quá khứ.

Suite Docker: 439 passed (tăng 6, đúng số test mới thêm).

## 07/09/2026 — TD-0097: EXPLORE là vĩnh viễn — chặn lỗ hổng "hồi phục rồi quay lại trading"

Spec (§9c.4b, ràng buộc (b)) cấm tuyệt đối: mã đã vào EXPLORE không bao giờ được đưa vào pool giao
dịch sau này dù sau đó thoả tiêu chí — "ngoại lệ sẽ biến EXPLORE thành tập train". `pairlist_point_in_time()`
(TD-0096) một mình KHÔNG thi hành được ràng buộc này: nó vô trạng thái, mỗi lần gọi độc lập tính lại
từ dữ liệu tại đúng mốc `t` đó — một mã tụt volume ở mốc sớm (vào explore) rồi hồi phục ở mốc muộn sẽ
được tính lại là "trading" nếu chỉ gọi hàm đó riêng lẻ cho từng mốc.

Thêm `pairlist_over_time(stats_by_checkpoint, ...)`: quét các mốc THEO THỨ TỰ THỜI GIAN (tự sắp,
không phụ thuộc thứ tự khai báo của dict truyền vào — có test riêng cho việc này), cộng dồn một tập
cấm vĩnh viễn từ `explore` của mỗi mốc đã đi qua, áp lên `trading` của mọi mốc sau. Mã CHƯA từng bị
explore-hoá thì lần đầu thoả tiêu chí vẫn vào trading bình thường — ràng buộc chỉ áp cho mã ĐÃ có
tiền sử bị loại, không áp cho mã mới xuất hiện.

4 test mới (`TestPairlistOverTime`): mã tụt-rồi-hồi-volume vẫn ở explore vĩnh viễn kể cả khi volume
mốc sau cao hơn cả mốc đầu; mã mới lần đầu thoả tiêu chí vào trading bình thường; BTC/ETH explore ở
mọi mốc; kết quả không đổi khi xáo thứ tự khai báo checkpoint.

Suite Docker: 443 passed (tăng 4).

## 07/09/2026 — Review độc lập zone_detection.py/zone_strength.py (không thuộc task nào, chủ động trước cổng D1)

Với D1 chỉ còn TD-0106 mở (trên track zone detection do phiên song song đang giữ), thay vì tranh
việc trên file người khác vừa viết, chạy một subagent context sạch (chưa thấy hội thoại nào sinh ra
code này — đúng tinh thần rule 18 "clean-context reviewing") để rà lại 6 file: `zone_detection.py`,
`zone_strength.py`, và 4 test khoá/unit tương ứng (TD-0100→0105).

**Kết luận về causality/lookahead (H4-D, H4-D-b, H13): giữ nguyên, không bắt được lỗi.** Kiểm độc
lập từng phép toán: `la_diem_swing` biên đúng, không tràn chỉ số âm; `confirm_ratio` không có tham
số mảng nên KHÔNG THỂ đọc dữ liệu tương lai dù muốn; `zone_da_bi_huy` cắt đúng `[i+1, t]`;
`touch_count` vòng lặp đúng `(i_swing, t]`; `compression` dùng TA-Lib ATR toàn mảng nhưng AN TOÀN vì
ATR kiểu Wilder tự nó nhân quả (giá trị tại n chỉ phụ thuộc dữ liệu ≤ n) — khớp đúng với những gì
`test_td0105` thật sự kiểm.

🐛 **Bắt được một lỗi thật, KHÔNG phải lookahead — mở TD-0107:** `touch_count()`
(`zone_strength.py:56-61`) — máy trạng thái "đang trong cụm chờ bật ra" chỉ kiểm `bat_ra`, không
bao giờ kiểm `vo_huong_nguoc` MỘT KHI đã vào cụm (điều kiện đó chỉ áp dụng lúc QUYẾT ĐỊNH vào cụm).
Tái hiện thật: zone đáy `[100,102]`, giá `[101, 101, 90, 103]` (chạm 101 → vỡ sâu dưới 90 giữa chừng
→ sau đó bật lên 103) → `touch_count()` trả **1**, dù giá đã vỡ hẳn qua `zone_low` ở giữa. Không có
test nào trong 22 test của `test_zone_strength.py` phủ trường hợp vỡ-giữa-cụm (mọi test cụm giữ giá
trong `[zone_low, zone_high]` suốt lúc chờ). Không tự sửa — file thuộc track TD-0104/0106 phiên song
song đang giữ, ghi TD-0107 để họ xử lý, tránh giẫm code đang chạy `lookahead-analysis`.

Ghi nhận thêm (không mở task, mức nitpick): NaN ở `gia_cham`/`volume` bị so sánh im lặng thành
`False` thay vì raise; không có kiểm `t >= i_swing`; test chưa phủ swing có nhiều đáy/đỉnh bằng nhau
(plateau). Không nghiêm trọng bằng lỗi touch_count, ghi lại để không quên nếu có thời gian.

## 07/09/2026 — TD-0106: chạy `lookahead-analysis` thật trên Zone Detection Engine

Dựng `user_data/strategies/ZoneDetectionProbe.py` — chiến lược THĂM DÒ (không phải chiến lược thật,
không tranche/SL/TP/DG theo spec), tái dùng nguyên vẹn `zone_detection.py`/`zone_strength.py` để merge
khung 4H informative vào 1H chính (`merge_informative_pair`, đúng cấu hình `config/freqtrade/config.json`
dòng 22-23), sinh cột `zone_confirmed`/`zone_hop_le`/`mult_zss_adjusted`. Entry = mọi swing đã xác nhận
(không lọc theo ngưỡng ZSS §1.3 — mục tiêu là soi lookahead ở cơ chế XÁC NHẬN, không phải đánh giá chất
lượng zone). `minimal_roi=2%`/`stoploss=-5%`/`custom_exit` 24h là giá trị THĂM DÒ để có lệnh đóng thật
cho công cụ đếm — không liên quan gì tới định cỡ rủi ro thật (§6.8e, chưa xây ở D1).

**Trở ngại kỹ thuật (không phải lookahead):** `lookahead-analysis` ép `order_types=market`, xung đột với
`entry_pricing.price_side="same"` bắt buộc theo §3.5 của config thật. Không sửa config thật — dùng file
override tạm `-c <override>.json` chỉ đổi `price_side` thành `"other"` cho riêng lần chạy phân tích, xoá
ngay sau khi xong, không commit.

**Chạy thật trên dữ liệu CALIB thật (TD-0093), 2 mã, khung 1H/4H, `--timerange 20240601-20260101`:**

| Mã | total_signals | has_bias | biased_entry | biased_exit | biased_indicators |
|---|---|---|---|---|---|
| 1000BONK/USDT:USDT | 20 | **No** | 0 | 0 | (rỗng) |
| 1000PEPE/USDT:USDT | 20 | **No** | 0 | 0 | (rỗng) |

**Không có cờ nào được nêu ra** ở cả hai lần chạy — nên bảng "quy mỗi cờ về FP-1/FP-2/FP-3" mà TASKS.md
yêu cầu không có dòng nào để điền: đây là kết quả sạch, không phải "bỏ qua không kiểm". Khớp với đánh giá
độc lập cùng ngày ở mục review phía trên ("causality/lookahead: giữ nguyên, không bắt được lỗi") — hai
phương pháp khác nhau (chạy công cụ thật vs đọc code) cùng ra một kết luận.

**Giới hạn của kết quả, nói thẳng:** mới thử 2/102 mã, một khoảng thời gian, và entry rất thưa (20 tín
hiệu/mã) nên độ bao phủ thống kê thấp — không phải bằng chứng "không thể có lookahead", chỉ là "không
thấy trong lần thử này". `lookahead-analysis` bản thân công cụ cũng có false positive đã biết (FP-1/2/3,
§7.2) nên kết quả "No" ở đây không cần đối chiếu thêm gì — nếu có `has_bias=Yes` mới cần bảng quy lớp FP.
Nên chạy lại khi có nhiều mã/timerange hơn một khi D2 cần con số đáng tin hơn.

## 07/09/2026 — TD-0094: suýt viết cơ chế song song với L-Z55, dừng lại khi phát hiện

Bắt tay viết `enforce_timerange_ceiling()` (kiểm chuỗi `--timerange` yêu cầu so với `t2`) trước khi
kiểm xem đã có cơ chế nào tương tự chưa. Đọc lại `tests/lock/test_lz55_ctrl_explore_timerange_self_check.py`
mới phát hiện **đã có sẵn** `assert_dataset_timerange()` (`src/tool_d/ledger/timerange.py`, DR-014
§2, L-Z55) — đúng cơ chế cần, và ĐÚNG hơn bản đang viết dở: nó kiểm dữ liệu THẬT đã tải
(`observed_start/end` từ dataframe), không phải chuỗi CLI người dùng gõ — đúng bài học TD-0093 (yêu
cầu `--timerange` đúng không có nghĩa dữ liệu tải về đúng phạm vi). Xoá file vừa viết, không commit.

Vấn đề thật của L-Z55: viết từ TD-0055 (Khối 5, DR-014), có test khoá đầy đủ, nhưng **chưa từng được
nối với cấu hình thật** — không nơi nào trong code tạo `DatasetBoundary` từ `tool_d_config.yaml`,
mọi test đều tự dựng boundary tay. Đây đúng dạng "công cụ tồn tại nhưng không ai gọi" — nguy hiểm
ngang với không có công cụ, vì tạo cảm giác an toàn giả.

Việc thật đã làm: thêm `tier_c.data_split` (T0-T3, DR-D0PRE-07) vào `tool_d_config.yaml` + hàm
`dataset_boundaries_from_config()` nối config với `assert_dataset_timerange()`. 4 test mới, gồm tái
hiện đúng kịch bản TD-0093 (khai WFO, dữ liệu lấn qua LOCKBOX) bị `TimerangeViolationError` bắt.

**Giới hạn thật, ghi rõ thay vì giả vờ xong:** E1/E2/E3 hiện chỉ là khung guard (TD-0016), rơi thẳng
xuống `NotImplementedError` — CHƯA có bước tải dữ liệu thật để mà gọi self-check sau đó. Nối
`assert_dataset_timerange()` vào đúng điểm (ngay sau khi dataframe được tải, trước khi đưa vào logic
backtest/WFO/ablation) là việc của bất kỳ task tương lai nào viết logic đó thật — không đóng giả một
wiring chưa có chỗ để nối.

Suite Docker: 486 passed.

## 07/09/2026 — TD-0110: đóng cổng D1 thật — gỡ blocker B2

Cả hai nhánh việc D1 xong: track H1-D/backfill (TD-0093→0097, phiên này) và track zone
detection/H4-D/H13 (TD-0100→0107, phiên song song) — không giẫm việc nhau suốt toàn bộ D1, kiểm
`git log`/`git status`/diff trước mỗi lần đụng file dùng chung.

Xây `close_d1_gate()` (E6, `--close-d1-gate`) thay vì lặp lại khuôn cũ của `close_d0_pre_gate()`
(TD-0086) — MT-10 đã chỉ đúng lỗ hổng của khuôn cũ: 2/3 mục `evidence` là chuỗi gõ tay giả làm bằng
chứng máy. Hàm mới tự `subprocess` chạy `pytest -q` THẬT trong chính lần gọi (image đã có sẵn pytest,
không cần lồng `docker compose` bên trong container đang chạy) rồi ghi lại đúng output — nhãn
`do-duoc` (MT-10) đúng nghĩa cho MỌI mục `d1_evidence`, không còn mục nào là lời khai.

Test `close_d1_gate()` dùng `pytest_cmd` thay bằng lệnh giả nhanh (không đệ quy chạy lại suite thật
bên trong chính suite đang chạy nó) + monkeypatch `is_d0_pre_complete` trực tiếp trên module thay vì
`chdir` (chdir sẽ phá các đường dẫn tương đối mặc định khác như `config/tool_d_config.yaml`).

**Chạy thật, một lần:** `docker compose run --rm freqtrade entrypoints/trial_ledger_audit.py
--close-d1-gate` → 492 passed (toàn suite), audit sổ trial 4/6 đạt (L-Z10/11/12/15), 0 chưa đạt.
`registry/runtime_state.json` giữ nguyên khối `d0_pre_complete` cũ, thêm `d1_complete: true` +
`d1_evidence` gắn nhãn nguồn. Gắn tag `git tag d1-complete`.

**Còn tồn dư, ghi rõ thay vì giả vờ hết:** TD-0094 chỉ nối được `assert_dataset_timerange()` (L-Z55)
với cấu hình thật — CHƯA wiring được vào E1/E2/E3 vì ba entrypoint đó chưa có logic tải dữ liệu thật
(vẫn `NotImplementedError`, Khối 1). Việc nối self-check vào đúng điểm sau bước tải là trách nhiệm
của bất kỳ task D2+ nào viết logic backtest/WFO/ablation thật.

Suite Docker cuối: 492 passed.

## 07/09/2026 — TD-0111 (D2 mở): đọc source D1 — fill/no-fill limit-maker trong backtest ĐÚNG như spec

Đọc `/freqtrade/freqtrade/optimize/backtesting.py` (image 2026.8, cùng bản đã dùng ở TD-0028) để trả
lời giả định D1 (§9b.2): backtest futures có mô hình fill/no-fill THẬT cho lệnh limit, không phải
"đặt là khớp ngay tại giá mở nến" như lo ngại ban đầu.

Chuỗi bằng chứng: `_enter_trade()` (dòng 1121) tạo order rồi gọi ngay `_try_close_open_order()` (dòng
1273) — chỉ đóng nếu `_get_order_filled()` (dòng 787, `low <= rate <= high`) đúng, TRÊN CHÍNH nến đặt
lệnh. Không khớp thì lệnh "open" được `backtest_loop()` (dòng 1520-1566) kiểm lại MỖI nến sau đó.
Không bao giờ khớp thì `manage_open_orders()` (dòng 1330) huỷ theo `unfilledtimeout` cấu hình — với
lệnh tranche 2/3 (additional entry, `nr_of_successful_entries > 0`), CHỈ lệnh đó bị xoá, trade với
tranche đã khớp vẫn sống — khớp đúng ý nghĩa `entry_order_ttl_bars_1h` đã có sẵn trong
`tool_d_config.yaml`.

**Kết luận: D1 XÁC NHẬN ĐÚNG.** Rủi ro nêu trong spec ("sai thì D0.9 vô nghĩa") không xảy ra ở tầng
cơ chế fill/no-fill. Rủi ro thật của Tool D vẫn nằm ở D6 (đã xác nhận riêng ở TD-0028): quyết định
CÓ kích hoạt tranche mới hay không vẫn nhìn giá mở nến, tách biệt với việc lệnh có khớp hay không.

Không cần viết test mới cho TD-0111 (đúng phạm vi TD-0028 tiền lệ — thuần đọc source + trích dẫn,
không phải test đơn vị). Ghi vào `docs/freqtrade-source-read.md` mục 5, cập nhật ghi chú đầu file
(D1 đã đọc, D3/D5 còn lại cho TD-0112/0113, D4 hoãn Testnet/Live).

## 07/09/2026 — TD-0112 (D2): đọc source D3 — giá vào trung bình đúng công thức, custom_stoploss đọc được

Đọc `/freqtrade/freqtrade/persistence/trade_model.py` (`recalc_trade_from_orders()`, dòng 1265) +
`/freqtrade/freqtrade/strategy/interface.py` (`custom_stoploss`, dòng 446) để trả lời giả định D3
(§9b.2): Freqtrade có tính đúng giá vào trung bình khi DCA nhiều lần entry, và `custom_stoploss` có
đọc được giá đó không.

Công thức đúng VWAP: `current_stake += price * tmp_amount * side` cộng dồn qua mọi entry order đã
khớp, `self.open_rate = current_stake / current_amount` sau vòng lặp. Cập nhật NGAY sau mỗi lần
tranche khớp — `_enter_trade()` gọi `trade.recalc_trade_from_orders()` ngay sau
`_try_close_open_order()` (dòng 1273-1274, cùng vị trí đã xác nhận ở TD-0111/D1) — không có độ trễ
một nến. `custom_stoploss(trade: Trade, ...)` nhận thẳng object `trade` đầy đủ, đọc `trade.open_rate`
là lấy đúng giá trung bình mới nhất, không cần strategy tự tính hay lưu qua `custom_data`.

**Kết luận: D3 XÁC NHẬN ĐÚNG cả hai vế.** Rủi ro spec nêu nếu sai ("phải tự tính/quản lý giá trung
bình, thêm code") không xảy ra.

Suite Docker: 492 passed (không đổi, đọc source không sửa code chạy).

## 07/09/2026 — TD-0113: thực nghiệm thật xác nhận `timeframe_detail=5m` tôn trọng thứ tự khớp thật

Chi tiết đọc source + kết luận đầy đủ: `docs/freqtrade-source-read.md` mục 7 (D5). Tóm tắt phần
thực nghiệm ở đây để dễ tái hiện mà không cần giữ lại script/dữ liệu tạm (đã xoá sau khi dùng — không
phải bằng chứng cần giữ vĩnh viễn, khác các file thật của dự án).

**Cách dựng:** 1 cặp tổng hợp (mượn `BTC/USDT` để qua được kiểm tra `pair_whitelist` của ccxt, dữ liệu
hoàn toàn tự tạo, KHÔNG phải giá BTC thật), backtest spot cô lập (config/thư mục riêng, không đụng
`config/freqtrade/config.json` thật). `TimeframeDetailProbe.py` (giữ lại trong `user_data/strategies/`,
gắn nhãn THĂM DÒ) vào lệnh long ngay nến đầu, `minimal_roi={"0":0.01}`, `stoploss=-0.10`. Dữ liệu 1H:
giờ 00:00-01:00 phẳng (giữ vị thế), giờ 02:00 dao động mạnh trong đúng MỘT nến (open=100 high=105
low=85 close=90). Dữ liệu 5m tương ứng: 02:00-02:05 tăng lên 105 (đạt ROI SỚM), 02:25-02:30 sập xuống
85 (chạm stoploss, XẢY RA SAU). Chạy backtest 2 lần, chỉ đổi cờ `--timeframe-detail`:

| Chạy | `--timeframe-detail` | `exit_reason` | `profit_ratio` |
|---|---|---|---|
| A | *(không có)* | `stop_loss` | −0,1018 |
| B | `5m` | `roi` | +0,00998 |

**Cùng một nến 1H, cùng chiến lược, cùng lệnh — kết quả đảo hoàn toàn** chỉ vì bật `--timeframe-detail
5m`. Xác nhận đúng giả định D5: KHÔNG có `timeframe_detail`, Freqtrade áp policy cố định "Stoploss
trước ROI" trên biên độ của cả giờ gộp lại — SAI LỆCH so với thực tế đã đạt ROI sớm hơn rất nhiều so
với lúc chạm đáy. CÓ `timeframe_detail`, nến 5m đầu tiên đủ để đóng lệnh bằng ROI trước khi vòng lặp
đi tới nến sập giá.

**Giới hạn residual đã ghi vào mục 8 của `docs/freqtrade-source-read.md`:** nếu SL và ROI cùng rơi vào
đúng MỘT nến 5m (không phải hai nến 5m khác nhau như thực nghiệm trên), Freqtrade vẫn dùng policy cố
định chứ không dò chronology thật — 5m thu hẹp cửa sổ mơ hồ từ 1H xuống 5m, không triệt tiêu hoàn
toàn. Cần nhớ lại khi D3.5/D4 gặp tranche/SL/TP sát giá nhau.

Suite Docker: không đổi (492 passed) — đây là thực nghiệm CLI, không phải pytest, không sửa code sản
xuất nào. File tạm (`td0113_make_data.py`, `td0113_config.json`, dữ liệu feather trong `.tmp/`, các
`backtest-result-*.zip`) đã xoá sau khi trích xong số liệu ở trên — công thức dựng lại đầy đủ nằm
trong bảng trên nếu cần tái hiện.

## 07/09/2026 — TD-0121 (D2): DG8 Time Stop — đóng vị thế vô điều kiện khi hết hạn giữ lệnh

Dựng `src/tool_d/time_stop.py` (§4b, spec dòng 1445-1539): `is_time_stop_triggered()` quyết định
DG8 chỉ dựa trên `bars_since_tranche1 >= max_hold_bars` — CỐ Ý không có tham số nào về lãi/lỗ,
`trend_dir`, hay ZSS, vì spec nói rõ mỗi ngoại lệ thêm vào là một bậc tự do mới, và chính ngoại lệ
"đang lãi thì cho ở lại" là cách một time stop bị vô hiệu hoá trong thực tế (dòng 1461-1463).
`hold_duration_bars()` dùng chung công thức, không nhánh theo lý do đóng — áp dụng đều cho TP/SL/
DG6/DG7/DG8 (L-Z19, dựng phân bố hold cho §10.2).

19 test khoá (`test_lz18_time_stop_ceiling.py`, `test_lz19_hold_duration_recorded.py`): chữ ký hàm
không có "cửa" ngoại lệ (kiểm bằng `inspect.signature`); biên chính xác — kích hoạt ĐÚNG BẰNG
`max_hold_bars`, không sớm/muộn hơn (parametrize nhiều giá trị `max_hold_bars`); vượt biên (kiểm trễ
một nến) vẫn kích hoạt — không có khái niệm "quá hạn nên thôi"; `hold_duration_bars` tính đúng bất
kể `exit_tag` (TP1/TP2/STOP_LOSS/DG6/FUNDING_STOP/TIME_STOP).

`max_hold_bars` đọc từ `tier_b.max_hold_bars_4h` (đã có sẵn trong `tool_d_config.yaml`, mục #11) —
hàm không hardcode, người gọi tự đọc config truyền vào, giữ đúng pattern thuần của
`zone_detection.py`/`zone_strength.py`. Việc nối vào `IStrategy` thật là của TD-0114.

Suite Docker: 532 passed (gồm cả code TD-0119 của phiên song song đang làm dở, chưa commit).

## 07/09/2026 — TD-0122 (D2): DG7 Funding Stop — phát hiện task ban đầu thiếu 2/3 mã test spec gán

Trước khi khoá task, đọc lại §4c.4 (spec) thấy TASKS.md chỉ ghi `test_lz43_*` cho TD-0122, nhưng
spec thực gán CẢ BA mã cho DG7: **L-Z30** (🔴 CRITICAL — trần `funding_paid_cumulative`), **L-Z31**
(ghi ở mọi lệnh đã đóng), **L-Z43** (chiều dấu/cột dữ liệu). Thiếu L-Z30 nghĩa là thiếu đúng phép
kiểm quan trọng nhất (trần chi phí funding không được vượt). Sửa verify trước khi code, ghi vào
Lịch sử thay đổi checklist.

Dựng `src/tool_d/funding_stop.py` (§4c.2): `funding_paid_cumulative()` chỉ đảo dấu quy ước Freqtrade
(ÂM = đã trả) — một công thức DUY NHẤT đúng cho cả Long/Short, vì Freqtrade tự tính dấu funding theo
hướng lệnh (không cần code phân biệt lại, tránh đúng loại lỗi LD-14 mô tả: sai dấu làm DG7 im lặng
không bao giờ kích hoạt mà backtest vẫn sạch). `is_funding_stop_triggered()` CỐ Ý không nhận tham số
lãi/TP1/trend — áp dụng không điều kiện, cùng lý do DG8 (TD-0121).

15 test khoá trên 3 file, đúng 3 mã spec gán: L-Z30 (biên chính xác tại đúng ngưỡng; mô phỏng bước
funding trong biên 0.05×R_eff_plan không vượt trần 0.35); L-Z31 (tính được bất kể `exit_tag` —
TP1/TP2/STOP_LOSS/DG6/TIME_STOP/FUNDING_STOP); L-Z43 (LONG qua 3 mốc funding dương phải cho
`cumulative` dương — test còn minh hoạ rõ: quên đảo dấu sẽ cho kết quả ÂM, đúng loại lỗi LD-14 cảnh
báo, và test sẽ bắt được ngay).

`threshold_frac` (0.3, `tier_b.dg7_funding_frac` có sẵn) và `r_eff_plan` không hardcode trong hàm —
người gọi tự đọc config/kế hoạch truyền vào, đúng pattern thuần của các module DG khác.

Suite Docker: 559 passed.

## 07/09/2026 — TD-0114: bug thật bắt được bằng backtest thật (L-Z49) — custom_data khởi tạo từ dataframe đã merge không đáng tin

Dựng `ZoneAbsorptionMinimal.py` — chiến lược TỐI THIỂU THẬT (LONG only), tái dùng nguyên vẹn
`zone_detection`/`zone_strength` (Khối 11) + `dg6_early_invalidation`/`funding_stop`/`time_stop`
(TD-0121/0122/0123) + `trade_plan` (kế hoạch tranche mới, TD-0114). Mục tiêu: chứng minh bằng
backtest THẬT rằng kế hoạch ghi lúc tranche 1 khớp (`trade.custom_data`) sống sót nguyên vẹn qua
callback tranche 2/3 (`adjust_trade_position`) và `custom_exit` (L-Z49).

**Cơ chế kiểm từ BÊN NGOÀI:** mọi lệnh (entry 1/2/3) của cùng một trade phải mang cùng JSON kế
hoạch làm order tag — nếu `custom_data` bị mất/lệch, tag đọc lại ở tranche 2/3 sẽ khác `enter_tag`
của tranche 1, lộ ra ngay trong file backtest xuất ra mà không cần tin lời code.

**Chạy thật lần 1 (2 mã 1000BONK/1000PEPE, 2024-06-01→2025-06-01, dữ liệu CALIB thật):** 34 trade,
25 trade nhiều tranche. Đối chiếu tag: **2/25 trade (8%) có tag KHÔNG khớp** giữa tranche 1 và
tranche 2/3 — đúng loại lỗi L-Z49 sinh ra để bắt.

**Nguyên nhân (xác nhận bằng debug log trực tiếp trên trade lỗi):** phiên bản đầu, khi
`trade.custom_data` còn trống, tái tạo kế hoạch bằng cách đọc "hàng cuối" của dataframe đã merge
từ khung 4H (`merge_informative_pair(ffill=True)`). `ffill` chỉ giữ giá trị hợp lệ TRONG đúng cửa
sổ 4H của chính zone đó. Lệnh chờ tranche 1 là post-only, tối đa 3 nến 1H chờ khớp (§3.5) — nếu
lệnh khớp SAU khi đã lăn sang cửa sổ 4H kế tiếp (cửa sổ đó chưa có zone mới → cột trở lại NaN),
`get_analyzed_dataframe().iloc[-1]` tại đúng lúc khớp đọc phải NaN (hoặc tệ hơn, một zone MỚI khác
đã xác nhận ở cửa sổ đó). Debug log xác nhận trực tiếp: một trade mở lúc `2024-08-16 11:00` liên
tục đọc `p1_4h = nan` ở MỌI lần gọi `adjust_trade_position`/`custom_stoploss` suốt 3 ngày — tức
`custom_data` chưa từng khởi tạo thành công cho tới khi giá chạm `p2`, lúc đó "hàng cuối" đã thuộc
một zone hoàn toàn khác.

**Sửa:** đổi nguồn KHỞI TẠO kế hoạch sang `trade.enter_tag` — Freqtrade chốt cứng giá trị này vào
lệnh lúc TẠO (đúng nến tín hiệu, dữ liệu còn hợp lệ), không đọc lại dataframe về sau. Mã hoá 6
trường giá (`zone_low/high`, `p1/p2/p3/sl`) thành JSON gọn (`_ma_hoa_ke_hoach`), giải mã
(`_giai_ma_ke_hoach`) khi cần khởi tạo `custom_data` lần đầu. Sau lần khởi tạo đó, MỌI lần đọc sau
đi qua `trade.custom_data` như thiết kế ban đầu — đây mới đúng là phần L-Z49 thật sự kiểm (dữ liệu
ĐÃ ghi có sống sót qua nhiều lần đọc không, không phải "tính lại có ra cùng số không").

**Chạy lại sau khi sửa (cùng dữ liệu, cùng cấu hình):** 34 trade, 27 trade nhiều tranche, **0/27
mismatch**. `docker compose run --rm tests` toàn bộ suite: 587 passed (loại trừ 1 file đang được
tab song song sửa dở, xác nhận bằng `git status` không phải của phiên này).

**Bài học:** đây đúng dạng lỗi LD-04/LD-12 nói chung — một cơ chế "trông đúng" (đọc dataframe đã
tính sẵn) chỉ đúng trong trường hợp phổ biến (khớp lệnh nhanh, cùng cửa sổ), và chỉ lộ ra khi backtest
chạy đủ dài để gặp ca lệnh khớp trễ. Không thể phát hiện bằng đọc code hay test đơn vị hàm thuần —
chỉ bằng chạy backtest thật trên dữ liệu thật đủ dài, đúng lý do TD-0114 đòi hỏi "backtest thật",
không chấp nhận mock.

**Phạm vi CHƯA phủ** (ghi trong docstring `ZoneAbsorptionMinimal.py`, không giấu): LONG only (Short
hoãn theo §3.3d); entry KHÔNG dùng Phần 2 (`trend_context`)/§3.3b (`entry_confirmation`) — hai
module đó đã kiểm đúng độc lập (TD-0119/0120) nhưng nối vào tín hiệu vào lệnh thật cần thêm khung
dữ liệu 1D/RSI, để dành cho chiến lược sản xuất; DG1-DG5 (gate kích hoạt tranche mới) chưa xây —
tranche 2/3 kích hoạt thuần theo giá chạm p2/p3; DG6 điều kiện C/D luôn tắt (thiếu `trend_dir`/
không áp dụng Long-only).

---

## 07/09/2026 — TD-0115: đo lệch khớp tranche so với giá `timeframe_detail` 5m thật (L-Z50, D6)

**Câu hỏi:** mỗi tranche fill trong backtest thật (TD-0114) có `fill_price` nằm trong phạm vi giá
thật đã CHẠM `p_i` (kế hoạch) không, đo bằng dữ liệu 5m thật (không phải suy diễn từ 1H/4H)?

**Chuẩn bị dữ liệu:** pool backfill TD-0093 chỉ có 1h/4h/1d/mark/funding_rate — chưa từng tải 5m.
Tải mới bằng `freqtrade download-data -t 5m --timerange 20240601-20250601` cho đúng 2 mã đang dùng
để test chiến lược (`1000BONK/USDT:USDT`, `1000PEPE/USDT:USDT`). Xác nhận phạm vi tải khớp CHÍNH XÁC
`2024-06-01 00:00:00` → `2025-05-31 23:55:00` (105 120 dòng/mã, không dư — khác lỗi đã ghi ở TD-0093).

**Chạy backtest thật:** `ZoneAbsorptionMinimal`, `--timeframe-detail 5m --cache none`, cùng
timerange/dữ liệu CALIB thật — 35 trade, 91 lượt khớp tranche (35 tranche 1, 32 tranche 2,
24 tranche 3). `--cache none` dùng CÓ CHỦ ĐÍCH ở vòng đo chính thức này (không phải mặc định của
Freqtrade) — lý do xem mục "Phát hiện giữa chừng" bên dưới.

**Phương pháp đối chiếu:** với mỗi lệnh entry đã khớp, giải mã `ft_order_tag` (JSON kế hoạch —
đúng cơ chế TD-0114) lấy giá kế hoạch `p_i` theo đúng số tranche của trade đó; tra `fill_price`
so với `[low, high]` của nến 5m thật tại `order_filled_timestamp` (dò 3 mức: đúng nến, nến liền
trước, và cửa sổ 30 phút trước đó).

**Kết quả phân bố lệch (Δ% = (fill − planned) / planned):**

| Tranche | n | mean Δ% | std Δ% | max |Δ%| |
|---|---|---|---|---|
| 1 | 35 | −0,3151 | 0,9326 | 4,1239 |
| 2 | 32 | −0,3959 | 0,5787 | 2,3653 |
| 3 | 24 | −0,1235 | 0,2351 | 0,9185 |

Short: N/A (chiến lược tối thiểu chỉ LONG, xem TD-0114).

Toàn bộ 91/91 lệch đều **âm hoặc ~0** (fill rẻ hơn hoặc bằng giá kế hoạch cho lệnh LONG) —
**không có trường hợp nào fill đắt hơn kế hoạch**. Theo đúng yêu cầu của dòng TASKS.md: có lệch
(dù nhỏ) ở 91/91 fill → **ghi nhận D6 CHƯA giảm nhẹ bởi H5, không tự ý "coi như đạt"**; ảnh hưởng
thực tế luôn có lợi hoặc trung tính cho phía LONG, không tạo rủi ro ẩn.

**Đối chiếu "đã thật sự chạm `p_i` chưa" bằng dữ liệu 5m:**
- 56/91 (62%) — nến 5m đúng tại `order_filled_timestamp` chứa `p_i` trong `[low, high]`.
- 26/91 (29%) — nến ĐÚNG không chứa, nhưng nến 5m LIỀN TRƯỚC (5 phút sớm hơn) có chứa. Đây là độ
  trễ ghi nhận 1 nến giữa lúc giá THẬT chạm mức và lúc Freqtrade backtest xử lý xong + đóng dấu
  `order_filled_timestamp` — cơ chế đã đọc trong `docs/freqtrade-source-read.md` (TD-0028, D2a):
  `backtest_loop()` xử lý tuần tự theo nến chi tiết, có độ trễ tối thiểu 1 bước giữa "giá chạm"
  và "lệnh được xác nhận khớp trong vòng lặp kế tiếp". Không phải lỗi dữ liệu.
- 9/91 (10%) — không chạm `p_i` kể cả trong cửa sổ 30 phút. Kiểm tay từng ca (`1000BONK` 1 trade
  2 tranche cùng khớp 1 nến do giá gap xuyên nhiều mức 1 lượt; `1000PEPE` 3 trade mở cách nhau
  5-10 phút trên cùng 1 zone, giá đã gap xuống dưới cả `p1` từ trước khi lệnh vào sổ). Ở CẢ 9 ca,
  `fill_price` THẬT SỰ THẤP HƠN `planned` (0,12%–4,12%) — đúng hành vi lệnh giới hạn mua chuẩn: khi
  giá thị trường đã gap qua khỏi mức giới hạn TRƯỚC khi lệnh được đặt/xử lý, lệnh khớp ngay ở giá
  thị trường tốt hơn (rẻ hơn) thay vì chờ giá quay lại đúng mức giới hạn. Xác nhận bằng cách soát
  trực tiếp OHLC 5m quanh mốc — không phải lỗi tính zone/kế hoạch.

**Phát hiện giữa chừng (đã loại trừ, ghi lại để không tốn công tra lại sau):** vòng đo đầu tiên
(chạy 2 mã CÙNG LÚC, KHÔNG có `--cache none`) cho ra một ca tưởng như nghiêm trọng — giá kế hoạch
của tranche 1 một trade mở `2024-06-04` khớp với mức giá THẬT của `1000BONK` chỉ xảy ra quanh
`2025-06-13`..`2025-11-01` (lệch hơn 1 năm, ~2,3 lần giá trị). Nghi ngờ ban đầu: `_tinh_zone_4h()`
gán sai ngày/hàng khi merge 4H→1H. Đã cô lập bằng cách chạy lại với `--cache none` (loại bỏ khả
năng cache backtest giữ dữ liệu cũ) trên 1 mã riêng lẻ rồi trên cả 2 mã — **ca lệch >1 năm không
tái hiện ở bất kỳ lần chạy `--cache none` nào**, dữ liệu thật khớp chuẩn với kết quả bảng trên.
Kết luận: đây là lỗi Ở KỊCH BẢN ĐO (script phân tích tự viết, gán `p_i` theo THỨ TỰ lệnh mua trong
danh sách xuất ra — không đáng tin khi có nhiều trade/tranche khớp gần nhau), **không phải lỗi
trong `ZoneAbsorptionMinimal.py`/`trade_plan.py`**. Đúng quy trình chẩn đoán N10: đã đối chiếu
bằng dữ liệu thật (5m + 1H đều đồng thuận với nhau) trước khi kết luận, không đụng code chiến lược
vì lệch nằm ở tầng đo (script kiểm tra), không phải ở bot.

**Kết luận D6:** với chiến lược tối thiểu hiện tại (chưa có DG1-DG5 chặn nến/entry dồn dập), độ
lệch khớp tranche so với giá kế hoạch là nhỏ (tối đa 4,12%, trung bình dưới 0,4%), LUÔN có lợi cho
LONG, và có nguồn gốc giải thích được hoàn toàn bằng cơ chế khớp lệnh giới hạn + độ trễ 1 nến xử lý
— không phải bằng chứng D6 (rủi ro "giả thuyết đã sai") được giảm nhẹ bởi H5, vì đây không phải cơ
chế H5 đang đo; ghi nhận độc lập, không gộp kết luận.

**Provenance (§0d.5):** dữ liệu 5m — `freqtrade download-data`, Binance USDⓈ-M futures thật, tải
07/09/2026, `user_data/data/binance/futures/{1000BONK,1000PEPE}_USDT_USDT-5m-futures.feather`.
Backtest — `ZoneAbsorptionMinimal`, `config/freqtrade/config.json`, `--timerange 20240601-20250601
--timeframe-detail 5m --cache none`, kết quả xuất `user_data/backtest_results/backtest-result-
2026-09-07_04-06-36.zip`. Toàn bộ đối chiếu chạy trong Docker (`--entrypoint python freqtrade`),
đây là phân tích đọc dữ liệu tĩnh (không phải bằng chứng test khoá N7) — bằng chứng N7 chính thức
của TD-0114/L-Z49 không đổi.

## 07/09/2026 — TD-0116 (H15): latency network+auth thật; testnet bị loại bằng bằng chứng mã nguồn

**Testnet bị loại — đóng câu hỏi mở của §6.7 bằng source, không bằng phỏng đoán.** Spec dặn "không
nhận nguyên premise 'Freqtrade không hỗ trợ testnet'". Đọc Freqtrade 2026.8 đang cài:
`exchange/binance.py:52` đặt `"supports_demo_trading": False` kèm chú thích CỐ Ý — *"Intentionally
Disabled as it's a separate market - not a simulated live market"*; `exchange.py:884-890`
`validate_demo_trading()` raise `ConfigurationError` nếu bật. Bybit thì `True`, Binance bị tắt riêng.
`ccxt` bên dưới CÓ `set_sandbox_mode` nhưng Freqtrade không bao giờ gọi (grep `set_sandbox` → 0 kết
quả). **Lý do Freqtrade nêu quan trọng hơn việc "không hỗ trợ"**: testnet là *thị trường riêng*, nên
đo latency tới đó là đo hạ tầng bot không bao giờ dùng. Chuyển hẳn sang production.

**Một lỗi thiết kế của chính bản đo đầu, tự bắt được TRƯỚC khi lấy số:** `urllib.urlopen` mở TCP+TLS
MỚI mỗi lần gọi → mọi mẫu cõng thêm bắt tay TLS. Freqtrade/ccxt giữ kết nối bền, nên con số đó thổi
phồng đúng đại lượng dùng để đánh giá khoảng trống không-SL của D2c. Viết lại bằng `http.client` với
tham số `reuse_connection`, đo tách **LẠNH** (kết nối mới) và **ẤM** (dùng lại). Nếu không tách, số
báo cáo sẽ là ~3-6× số thật.

**Số đo chính thức** (Docker, production `fapi.binance.com`, mạng dân dụng VN, n=30/lượt, 07/09/2026):

| Phép đo | median | p95 | max | mẫu >1s |
|---|---|---|---|---|
| public `/fapi/v1/time` — **ẤM** | **136,4 ms** | 386,8 ms | 684 ms | 0/30 |
| ký `/fapi/v1/order/test` — **ẤM** | **138,3 ms** | 396,0 ms | 589 ms | 0/30 |
| public `/fapi/v1/time` — LẠNH | 818,2 ms | 3.520 ms | **10.994 ms** | 14/30 |
| ký `/fapi/v1/order/test` — LẠNH | 672,2 ms | 2.173 ms | 3.855 ms | 12/30 |

> **Chi phí auth + validate lệnh phía sàn = +1,9 ms** (đo theo cặp, cùng host, cùng phiên, kết nối ấm).

**Kết luận H15: mạng chi phối hoàn toàn, auth gần như miễn phí.** Với độ trễ cấu trúc sẵn có của
Tool D (zone confirm 12h + entry confirmation tối đa 3 nến 1H), 138 ms không đáng kể — đúng như §6.7
dự đoán khi xếp H15 là P1. Nhắc lại giới hạn spec tự nêu: `/order/test` dừng trước matching engine
nên đây là **cận dưới** của lệnh thật, không thay thế đo lại ở dry-run/live.

**Một quan sát về phương pháp, đáng giữ:** ở kết nối LẠNH, hiệu giữa endpoint ký và endpoint public
ra **âm** (−146 ms) — vô nghĩa về mặt vật lý. Đó là bằng chứng cho thấy nhiễu bắt tay TLS nuốt trọn
mọi khác biệt endpoint. **Không đo được chi phí endpoint trên kết nối lạnh** — chỉ đo được trên kết
nối ấm, theo cặp cùng host.

🔴 **Phát hiện ngoài phạm vi H15, quan trọng hơn con số H15:** latency kết nối **LẠNH không ổn định**
— qua 7 lượt đo, median dao động 264 → 943 ms, có lượt **14/30 mẫu vượt 1 giây**, max quan sát được
**11 giây**. Hệ quả trực tiếp cho **D2c** (§8.3): khoảng trống không-SL = `PROCESS_THROTTLE_SECS`
(5 s, TD-0028) **+ round-trip đặt lại SL**. Nếu đúng lúc đó phải dựng lại kết nối, cửa sổ không có SL
trên sàn có thể **vượt 15 giây**. Con số này cần nhớ khi chốt `L_exchange` (spec §9b.2: *"Nếu D2c
fail: hạ `L_exchange`"*) và khi đo `gap_ms` thật ở testnet/live.

**Chẩn đoán quyền API — làm bằng thực nghiệm, không đoán.** Ban đầu mọi endpoint futures trả `-2015`.
Tách nguyên nhân bằng bảng sau, thay vì sửa mò cấu hình tài khoản:

| Endpoint | Trước | Sau khi bật Futures |
|---|---|---|
| `GET /api/v3/account` (spot, đọc) | 200 OK | 200 OK |
| `POST /api/v3/order/test` (spot, lệnh) | `-2015` | — |
| `GET /fapi/v2/balance` (futures, đọc) | `-2015` | **200 OK** |
| `POST /fapi/v1/order/test` (futures, lệnh) | `-2015` | **200 OK** |

Sàn trả `-2015` (khoá/IP/quyền) chứ **không phải `-1022`** (chữ ký sai) → loại secret khỏi danh sách
nghi phạm ngay từ đầu. Spot đọc được nhưng futures không → khoanh đúng vào quyền Futures ở **mức tài
khoản phụ**, không phải mức API key. Chủ dự án bật Futures cho tài khoản phụ → cả hai endpoint futures
thông ngay. Hai giả thuyết trung gian đã bị **bác bỏ bằng bằng chứng**, ghi lại để không ai đề xuất
lại: (a) nhầm key testnet/production — cùng key thất bại ở CẢ hai host; (b) Portfolio Margin chặn —
ảnh chụp sau khi tắt PM cho thấy "Bật Futures" vẫn mờ.

**Ngày tạo API key: 07/09/2026** (§6.7 yêu cầu ghi, phục vụ audit thời gian key tồn tại). Tài khoản
phụ `smartdca_virtual@…`, loại HMAC.

⚠️ **Rủi ro tồn dư, chấp nhận có ý thức** (§6.7 đòi hai điều kiện, hiện chưa thoả đủ):
- **IP whitelist**: hiện để "Không giới hạn". Lý do chấp nhận: IP nhà mạng VN là IP **động**
  (`171.239.19.179` tại thời điểm đo), whitelist xong sẽ hỏng khi ISP đổi IP; tài khoản phụ không
  giữ tiền. **Phải siết lại trước D11 (dry-run) và D12 (live).**
- **"Cấp quyền chuyển chuyên dụng" (Universal Transfer) đang BẬT** — quyền chuyển tiền giữa ví, không
  cần cho bất kỳ việc gì của Tool D. Khuyến nghị tắt.

**Hai điều cùng trỏ một hướng cho D11/D12:** (1) latency dân dụng VN có đuôi nặng, bất ổn ở kết nối
lạnh; (2) Binance bắt whitelist IP cho quyền giao dịch, mà IP nhà là IP động → bot tự chết mỗi lần
đổi IP. Cả hai được giải bằng **VPS ở Tokyo** (IP tĩnh + gần hạ tầng Binance). Chưa chốt bây giờ —
ghi để tới lúc đó không phải phát hiện lại từ đầu.

Suite Docker: 616 passed (2 test `periodic_report`/`close_d0_pre_gate` đỏ thoáng qua do `git status`
timeout khi chạy nhiều container liên tiếp; chạy lại sạch 13/13 — đúng hiện tượng đã ghi ở TD-0085,
không phải hồi quy).

---

## 07/09/2026 — TD-0124 + TD-0125 (OQ-13): hai kênh nhập liệu có luật nhưng không có máy canh

Hai chỗ trong project ở cùng một tình trạng: **luật viết rất chặt, không dòng code nào thi hành**.
Cả hai đều là *kênh nhập liệu* — nơi con người/LLM đưa đề nghị vào hệ thống, và cũng là chỗ nguy
hiểm nhất của một project định lượng: luật nằm trên giấy thì đến lúc mệt hoặc đang thua sẽ tự nới.

- **Kênh 1 (hàng chờ ý tưởng).** TD-0118/0119/0120 đã dựng xong *toàn bộ phần ĐỌC* (5 phép kiểm,
  schema 20 trường, tiêu chí chọn Q3/2026 niêm phong) nhưng **không có writer** — mọi đơn phải gõ
  tay JSON đủ 20 khoá với `additionalProperties: false`. Gõ sai một khoá là một dòng sổ bẩn, mà sổ
  append-only thì không xoá lại được.
- **Kênh 2 (OQ-13).** `L-Z26` 🔴 CRITICAL có **0 dòng code**; `grep` toàn repo ra đúng 4 kết quả,
  tất cả là văn bản.

### Nguyên tắc thiết kế chung: biến ràng buộc thành cấu trúc dữ liệu

§12d.2 BƯỚC 3 đòi *"MỌI câu trong đề xuất phải TRÍCH một con số cụ thể"*. Cách rẻ là một ô "lý do"
văn xuôi kèm lời hứa sẽ trích số — nhưng thứ đó cần **có người nhớ luật** mới thi hành được, và
người thì quên. Cách đã chọn: `luan_diem` là **mảng có cấu trúc**, mỗi phần tử bắt buộc
`{chi_so, gia_tri (kiểu SỐ), dai_ky_vong, tham_so_tro_toi}` — câu không có số **không biểu diễn
được**. Cùng thủ thuật TD-0120 đã dùng cho `selection_reason`.

Hệ quả cùng hướng: cả hai công cụ **TỪ CHỐI GHI** thay vì ghi rồi để audit báo sau. Sổ append-only
không có đường lùi, nên mọi phép kiểm chạy TRƯỚC khi mở file.

### Hai lớp canh, một bộ luật

`kiem_de_xuat()` dùng CHUNG cho cửa ghi và cho `check_lz26_*`. Cửa ghi bịt lỗ "nộp đơn sai";
phép kiểm audit bịt lỗ "sửa sổ bằng tay". Nếu hai lớp có hai bản luật riêng thì lớp nào cũng có
thể là lớp sai, và không ai biết lớp nào đúng.

### Ba điều quyết có ý thức, ghi lại để khỏi phải nghĩ lại

1. **Công cụ nộp đơn = cờ trên E6, KHÔNG phải entrypoint thứ 9.** `entrypoints/` là danh sách ĐÓNG
   đúng 8 file (spec dòng 664 cấm E9, canh bởi L-Z36 + `entrypoint_registry.py`). E6 đã có tiền lệ
   ghi file (`--close-gate`). Phương án "CLI nằm ngoài `entrypoints/`" bị loại vì nó không vi phạm
   *chữ* của L-Z36 nhưng mở đúng lỗ hổng mà danh sách đóng tồn tại để bịt.
2. **`bao_cao_hash` do máy tự băm từ file báo cáo đã lưu, KHÔNG sửa `periodic_report.py`.** Sửa E5
   để nó tự in hash sẽ chạm vào *"ĐỔI NỘI DUNG BÁO CÁO = TIÊU 1 TRIAL"* (spec dòng 4808) và
   `FROZEN_CONTENT_HASH` mà TD-0062 niêm phong. Người nộp lưu đầu ra E5 thành file, trỏ đề xuất vào
   đó; máy băm và về sau kiểm lại — vừa gắn được vào đúng một kỳ, vừa phát hiện được nếu file bị sửa.
3. **Trần NHẬP 10 đơn/quý chặn CỨNG**, khác trần CHỌN (L-Z17) mà MT-11 đã nới thành cảnh báo. Trần
   CHỌN là kỷ luật con người, không chảy vào N/DSR. Trần NHẬP thì có: chi phí sinh ý tưởng bằng LLM
   xấp xỉ 0, nên tỉ lệ chọn thấp biến bước CHỌN thành nơi khai thác dữ liệu quy mô lớn — và bước
   chọn thì **không ai ghi sổ cho**. Đây là chống nhiễu, cùng loại L-Z16.

### Cạm bẫy né được, và cạm bẫy bị test bắt

**Né tường minh — định dạng thời gian.** `registry.py::_utcnow_iso()` ghi **micro giây** (L-Z10 đòi
`registered_at < executed_at` CHẶT). Nhưng `check_lz17` và `check_td0120` đọc bằng
`strptime(..., "%Y-%m-%dT%H:%M:%SZ")` — **không dung sai micro giây**. Dùng lại hàm kia sẽ làm hai
phép kiểm **CRASH ValueError**, tức audit chết giữa chừng chứ không fail sạch — hỏng đúng thứ tầng
đo tồn tại để bảo vệ. Viết `_utcnow_iso_seconds()` riêng, có test canh.

**Bị bắt — L-Z25.** Suite đỏ ở `test_lz25_no_hyperopt_trace.py`: chuỗi bị cấm xuất hiện trong
**thông báo lúc chạy** của `param_proposals.py` (docstring được `_strip_py_noise()` bỏ qua, chuỗi
f-string thì không). Đây là lock test làm đúng việc của nó. **Diễn đạt lại thông báo, không nới
phép kiểm** — đúng cách TD-0119 đã xử lý khi hai test cũ đỏ.

### Bằng chứng (Docker — N7)

| Đo | Kết quả |
|---|---|
| Suite trước khi thêm test mới | **629** passed (đo bằng `--ignore` chính file mới) |
| Sau TD-0124 | **657** = +28, đúng số test mới |
| Sau TD-0125 | **687** passed, **0 failed** = +30, đúng số test mới |
| E6 chạy thật trên sổ thật | exit 0, `đã audit 4/11 (4 đạt, 0 chưa đạt, 7 chưa đo được)` |
| Nộp mẫu trống / mẫu trỏ báo cáo chưa có | exit **96**, sổ **0 dòng** ở cả hai |
| Hộp cát: chạy E5 THẬT → nộp `PC-0001` gắn vào chính bản đó | L-Z26 ✅ đạt |
| Hộp cát: **sửa báo cáo sau khi nộp** | L-Z26 🔴 CHƯA ĐẠT, chỉ đúng `sha256 không khớp` |

Thử nghiệm chạy trong **hộp cát bên trong container**, không ghi rác vào sổ thật — sổ thật vẫn 0
dòng ở cả `idea_queue.jsonl` lẫn `param_change_proposals.jsonl`.

### Phạm vi KHÔNG phủ — ghi rõ để không nhầm là "đã xong"

- **§12c.3 đòi tham số Cấp B phải có HAI điểm quyết định LIÊN TIẾP cùng tín hiệu.** `L-Z26` chưa
  kiểm được điều này vì chưa có đánh số điểm quyết định (chưa có lệnh live nào). → **TD-0127**.
- `L-Z27` (B3 ≤ 20, chỉ tăng theo `floor(lệnh/25)`) và `L-Z28` (không đổi tham số giữa hai điểm
  quyết định) cùng khối §12d.4, cũng **0 dòng code**. → **TD-0127**, hạn chót D11.
- `explore_evidence` bắt buộc khi `data_source = EXPLORE`, và query trùng `mechanism` trước khi nộp
  — hai ràng buộc §9c.7.3/§9c.7.4 hiện mới nằm trong `description` của schema. → **TD-0126**.

### Ghi nhận lệch số, không tự sửa

Dòng TD-0120 trong `TASKS.md` ghi mốc **624 passed**; đo lại thật hôm nay là **629** (không có thay
đổi test nào giữa hai mốc — `git log c085e67..HEAD -- tests/` rỗng). Không sửa dòng cũ, chỉ ghi lại
đây. Bài học nhỏ nhưng đúng hướng N12: **con số viết trong file trạng thái không thay được phép đo**.

### Va chạm mã việc — cần chủ dự án quyết

`TD-0119` và `TD-0120` đang được dùng **HAI LẦN** cho hai việc khác hẳn nhau: `TASKS.md:203-204`
(Context Trend Filter / xác nhận entry, khối D2) và `TASKS.md:213-214` (tờ đơn hai cửa / niêm phong
tiêu chí). Vi phạm chính quy tắc 1 của `TASKS.md` — *"Số không bao giờ tái sử dụng"*. Đã lan vào mã
nguồn: docstring của `src/tool_d/entry_confirmation.py` ghi "TD-0120" và `src/tool_d/trend_context.py`
ghi "TD-0119", trỏ sang việc khác hẳn với hai dòng cùng số ở khối Idea Queue. **Không tự sửa** —
đánh số lại là quyết định của chủ dự án.
