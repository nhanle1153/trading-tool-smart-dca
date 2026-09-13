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

### Đính chính (cùng ngày, ngay sau khi commit) — mốc 629 vs 624 KHÔNG phải lệch số

Mục trên viết *"không có thay đổi test nào giữa hai mốc — `git log c085e67..HEAD -- tests/` rỗng"*.
Câu đó **đúng tại thời điểm đo** nhưng **kết luận rút ra từ nó thì sai**. Nguồn thật của +5 lộ ra
ngay sau đó: commit `2659a5d` của **phiên Claude Code song song** (TD-0117 —
`tests/lock/test_lz49_lz50_backtest_nho.py`, đúng **5 test**) được ghi vào **giữa** hai lần tôi
chạy `git log`. Mốc **624** ở dòng TD-0120 **vẫn đúng** tại thời điểm nó được ghi; không ai ghi sai
con số nào.

Không xoá đoạn trên (append-only) — giữ lại vì bản thân cái sai này là bài học:

🔑 **Khi hai phiên cùng chạy trên một thư mục, `git log` là ảnh chụp, không phải sự thật đứng yên.**
N12 đã cảnh báo điều này cho `git add`; hoá ra nó áp cho **mọi phép đo dựa trên trạng thái repo**,
kể cả số test. Cách làm đã dùng để đo `+28`/`+30` là cách đúng và cần giữ: **đo baseline lại ngay
trước khi so, bằng `--ignore` chính file test mới**, thay vì lấy con số từ file trạng thái. Nếu chỉ
so với "624 ghi trong TASKS.md" thì đã kết luận nhầm là mình thêm 33 test.

---

## 07/09/2026 (tiếp) — dọn hai lỗ hổng vận hành + TD-0126

Ba việc nối tiếp đợt TD-0124/TD-0125, mỗi việc có một bài học riêng.

### 1. 🔴 Suýt xoá bản backup lockbox vì gọi nhầm nó là "rác"

Tôi liệt kê hai thư mục lạ ở gốc repo là "rác từ lệnh shell nhầm" và xin phép xoá. Chủ dự án
đồng ý. Nhưng khi **mở ra xem trước khi xoá**, thư mục `C:` hoá ra chứa **511 file dữ liệu
lockbox**, khớp từng byte (sha256) với `lockbox/data/` thật.

Nguyên nhân: ai đó truyền đường dẫn Windows `C:\Program Files\Git\lockbox-backup-tool-d` vào
`backup_lockbox(dest_dir=...)` từ Git Bash; nó bị tạo thành thư mục **tương đối** ngay trong
repo. Tên thật của thư mục là `C` + **U+F03A** (dấu hai chấm giả, vùng private-use) — Windows
không cho phép `:` trong tên file, nên hệ thống thay bằng ký tự nhìn giống hệt.

🔑 **Bài học 1 — "rác" là một kết luận, không phải một quan sát.** Tôi rút kết luận đó từ *tên*
thư mục chứ không từ *nội dung*. Quy tắc "nhìn vào đích trước khi xoá hay ghi đè" đã cứu ở đây;
nếu tôi tin cái tên thì đã xoá bản sao lưu của tài nguyên khan hiếm nhất dự án.

🔑 **Bài học 2 — ký tự nhìn giống nhau không phải cùng một ký tự.** `pathlib.Path("C:/…")` trên
Windows hiểu là **ổ đĩa C:**, nên phép so sánh đầu tiên của tôi trả về "backup có 0 file" — một
kết quả sai mà lại *trông* hợp lý (khớp với giả thuyết "thư mục rỗng/rác"). Chỉ khi in ra
`[hex(ord(c)) for c in ten]` mới lộ ra `0xf03a`. Số liệu ủng hộ giả thuyết sẵn có là lúc phải
nghi ngờ phép đo nhất.

**Phát hiện nghiêm trọng hơn cái tên:** bản sao này nằm **ngoài** đường dẫn mà
`docker-compose.yml` che, nên nó **lọt hoàn toàn vào container**:

| | trước | sau |
|---|---|---|
| `/workspace/lockbox/data` (phải bị che) | 0 file ✅ | 0 file ✅ |
| tổng `.feather` thấy từ container `tests` | **1023** 🔴 | **513** ✅ |
| con dấu đọc được (L-Z13/L-Z14 cần) | 1 | 1 ✅ |

Tức là suốt thời gian đó, dữ liệu lockbox **chạm được từ trong container** — phá đúng thứ
`ARCHITECTURE.md` 3.1 gọi là *"chỗ duy nhất biến 'không được chạm dữ liệu lockbox' thành
'không chạm được ở tầng hệ điều hành'"*. Không có bằng chứng nào cho thấy nó ĐÃ bị đọc (mọi
entrypoint vẫn đi qua `verify_seal`/`touch_lockbox`, và `lockbox_access.log` không có dòng lạ),
nhưng hàng rào đã hở.

**Cách xử:** không xoá — **chép → verify sha256 → mới xoá bản cũ** (move là một nhịp; đứt giữa
chừng thì mất cả hai). Script tự dừng khi phát hiện `E:\lockbox-backup-tool-d` **đã tồn tại** —
và bản ngoài đó hoá ra là backup **đầy đủ, đúng từng byte, 512/512 kể cả file niêm phong**. Nên
bản trong repo chỉ là bản THỪA; xoá không mất gì. Đã xoá, đã verify lại container.

### 2. Va chạm mã việc TD-0119/TD-0120 — chọn đổi phía nào

Hai mã bị dùng HAI LẦN cho hai việc khác hẳn. Không đổi số thì vi phạm quy tắc 1 của
`TASKS.md` tồn tại mãi; đổi sai phía thì phá bằng chứng đã ghi.

🔑 **Tiêu chí quyết định: phía nào có ĐỊNH DANH MÁY ĐỌC thì phía đó không đổi.** Cặp Idea Queue
đã ăn vào tên file test, tên hàm `check_td0119*`/`check_td0120*`, và chuỗi
`TD-0119a`/`TD-0119b`/`TD-0120` mà **E6 in ra trong đầu ra thật** — đổi chúng là đổi luôn bằng
chứng đã chép vào `TASKS.md` và `DR-Q3-2026-tieu-chi-chon-y-tuong.md`. Cặp D2 chỉ nằm trong
docstring và ô phụ thuộc. → đổi cặp **D2**: TD-0119 → **TD-0128**, TD-0120 → **TD-0129**.

Vì **lịch sử git không viết lại được**, ambiguity trong commit cũ không thể xoá — chỉ có thể
làm cho nó tra ngược được. Nên kèm **TỪ ĐIỂN ĐỔI TÊN** (bảng 4 chiều ở đầu Khối 13) + alias
trong docstring. Đây là cách chống "nhớ sai" mà chủ dự án lo, không phải chống bằng cách không
đổi gì cả.

### 3. TD-0126 — bug thật trong chính code chống trùng

Hai ràng buộc §9c.7 trước đây chỉ nằm trong `description` của schema (văn bản mô tả, không phải
luật). Nay có máy: `explore_evidence` bắt buộc khi EXPLORE, và so `mechanism` để chặn nộp lại ý
tưởng đã bị loại dưới tên khác.

🐛 **Test bắt được bug của tôi:** `đ` (U+0111) **không tách được bằng NFD** — nó là ký tự CƠ SỞ,
nét gạch là một phần của chữ chứ không phải dấu tổ hợp. Không thay tay thì `re` nuốt luôn nó:
`"đóng"` → `"ong"` trong khi `"dong"` giữ nguyên, và hai cách viết cùng một cơ chế lại thành hai
cơ chế khác nhau — đúng ca luật này sinh ra để bắt. Sửa code, không sửa test.

🔑 **Về ngưỡng nghi trùng (`NGUONG_NGHI_TRUNG = 0.6`):** cố ý thiết kế để đặt sai thì **rẻ** —
hậu quả là người nộp phải khai thêm một dòng `overlaps_with`, không phải mất một ý tưởng hay
lệch một phép đo. Một ngưỡng mà đặt sai thì tốn kém sẽ trở thành một cái núm để vặn. Vì vậy nó
KHÔNG vào `tool_d_config.yaml` (không phải tham số Tầng A/B/C, không chảy vào số nào).

**5 test cũ (TD-0118/TD-0124) đỏ đúng lúc sửa** vì fixture của chúng nộp nhiều đơn cùng
`mechanism`. Chỉ đổi **dữ liệu mẫu**; không nới phép kiểm, không sửa một dòng `assert` nào.

### Bằng chứng (Docker)

`699 → 720 passed, 0 failed` (+21 đúng bằng số test mới). E6 thật: exit 0, `đã audit 4/12`.
Ghi nhận: mốc 699 đã gồm 12 test `test_close_d2_gate.py` của **phiên song song** — lần này đo
baseline ngay trước khi so, đúng bài học đã ghi ở đính chính phía trên.

### Còn treo

**TD-0127** (`L-Z27` + `L-Z28`) hoãn có lý do, không phải quên: `L-Z28` cần **đánh số điểm
quyết định** và `L-Z27` phần *"chỉ tăng theo `floor(lệnh/25)`"* cần **lệnh live** — cả hai chưa
tồn tại. Viết test bây giờ là viết test cho cơ chế chưa có, phải giả lập bằng mock, đúng thứ
**L-Z51** cấm. Hạn chót vẫn là **trước D11**.

---

## 07/09/2026 — 🚪 GATE D2 ĐÓNG (TD-0117), tag `d2-complete`

`registry/runtime_state.json.d2_complete = true`, sinh từ một lần chạy THẬT trong Docker
(`E6 --close-d2-gate`, exit 0). Cả ba mục evidence mang nhãn `do-duoc` đúng nghĩa MT-10 —
hàm đóng cổng TỰ chạy pytest trong chính lần gọi đó, không nhận chuỗi gõ tay:
`full_suite` 720 passed · `lz49_lz50` 5 passed · `trial_ledger_audit` 4/12 đạt, 0 chưa đạt.
`d2_git_sha = 6613ce9` — HEAD tại thời điểm chạy (gồm cả TD-0126 của phiên song song), tức
ghi đúng CÂY ĐÃ ĐƯỢC KIỂM, không ghi sha commit của riêng người đóng cổng.

**Điều đáng ghi lại nhất — vì sao cổng D2 có một phép kiểm mà cổng D1 không có.**
Cổng D1 chỉ hỏi *"suite xanh chưa?"*. Với D2 câu đó KHÔNG đủ: xoá hẳn
`tests/lock/test_lz49_lz50_backtest_nho.py` đi thì suite vẫn xanh, và cổng vẫn đóng ngon
lành — trong khi hai phép kiểm cốt lõi của D2 đã biến mất. Nên `close_d2_gate()` chạy RIÊNG
đúng file đó và đòi **số ca PASS >= 1**: exit 0 mà không ca nào chạy bị từ chối thẳng
("PASS RỖNG, không phải bằng chứng"). Đây là cùng một hình dạng lỗi đã cắn ở TD-0084
(`verify_all_seals()` PASS vì không có seal nào để kiểm) — lần đó bị bắt sau khi đã có seal
thật; lần này chốt được viết TRƯỚC.

Kiểm chốt đó có răng: vô hiệu hoá đúng nhánh `so_ca_lz < 1` → đúng ca
`test_lz_exit_0_nhung_0_ca_thi_tu_choi` đỏ, 11 ca còn lại vẫn xanh (nếu cả bộ cùng đỏ thì
test đang canh thứ khác). Đã khôi phục nguyên trạng.

**Không tự phong cho D2 nhiều hơn nó có.** `d2_hoan_lai` (nhãn `nguoi-khai`, KHÔNG giả làm
bằng chứng máy) ghi thẳng: **D2b** (closePosition phía sàn), **D2c** (khoảng trống không-SL),
**D4** (khớp lệnh thật) KHÔNG kiểm được ở tầng backtest — HOÃN tới D3.5/D9.5+, **không phải
"đã qua"**. Riêng D2c còn một rủi ro đã đo được ở TD-0116: latency LẠNH bất ổn (14/30 mẫu
>1s, max 11 giây) → cửa sổ không-SL có thể vượt 15 giây. Phải giải quyết trước khi có lệnh thật.

Bất biến đã kiểm: chạy lại `--close-d2-gate` → exit **94**, từ chối ghi lại, file không đổi.

Cũng ghi nhận (lặp lại bài học của mốc 629 vs 624): mốc suite dịch từ **699** lúc commit code
sang **720** lúc đóng cổng, do phiên song song commit TD-0126 xen vào giữa. Không phải lệch số —
nhưng là lý do `d2_git_sha` phải lấy HEAD lúc chạy chứ không lấy commit của mình.


---

## 07/09/2026 (khuya) — TD-0143 + tai nạn N12 lần thứ tư

### TD-0143 — cache resume WFO phải mang vân tay (§0d.3, bug Tool A số 4)

`src/tool_d/wfo/cache.py`. Đây là chỗ Tool A *"sửa code rồi chạy lại vẫn ra số y hệt"*, và chỉ
phát hiện được vì hai lần chạy trùng nhau **đến từng chữ số**. Cache sai không báo lỗi — nó lặng
lẽ trả lại quá khứ, và số ra trông hợp lệ, chạy được, ghi vào sổ được.

🔑 **Quyết định thiết kế đáng ghi: BA trạng thái, không phải hai.**

```
HIT   — vân tay khớp        -> dùng lại
MISS  — chưa có mục cache   -> chạy mới, IM LẶNG (bình thường)
STALE — có mục nhưng LỆCH   -> 🔴 CẢNH BÁO TO, chạy mới, KHÔNG dùng
```

Cái bẫy ở đây tinh vi hơn nó trông: nếu gộp `STALE` vào `MISS` thì **kết quả cuối vẫn ĐÚNG** —
đằng nào cũng chạy lại — nên **không test nào đỏ và không ai nhận ra**. Thứ mất đi không phải
tính đúng đắn mà là *tín hiệu*: "có gì đó đã đổi mà mình không chủ ý đổi". Yêu cầu của việc này
viết thẳng điều đó (*"không âm thầm dùng tiếp, cũng không âm thầm BỎ"*), nên `STALE` là trạng
thái riêng, không bao giờ trả payload, và có một test chuyên đòi hai trạng thái phân biệt được.

Ranh giới thứ hai, cũng cố ý: **lệch vân tay là BÌNH THƯỜNG** (đổi code/tham số/dữ liệu là việc
hằng ngày) → `STALE`. **File hỏng hoặc thiếu khoá là LỖI** → `raise CacheError`. Gộp hai thứ này
sẽ khiến một file cache hỏng bị che dưới dạng "chắc do đổi code".

Cảnh báo được viết dài có chủ đích, in cả giá trị cũ lẫn mới và nói rõ *"đây KHÔNG phải lỗi"* —
một cảnh báo không giải thích được vì sao nó bật lên sẽ bị coi là báo động giả và bị tắt.

**Dùng lại hạ tầng, không băm lại:** `params_hash` lấy `cfg.sha256` (loader đã băm nguyên văn
YAML), `code_sha` lấy `get_git_info().sha`, `data_hash` gộp tất định từ chính dict đã nằm trong
khối provenance 0d.5. Nhờ vậy cache và provenance **không thể kể hai câu chuyện khác nhau** về
cùng một lần chạy. `get_git_info()` cố ý không bọc try/except: một vân tay mang `code_sha =
"UNKNOWN"` sẽ khớp với chính nó ở lần sau và biến cache thành đúng cái bẫy nó sinh ra để chặn.

**Bài học mượn từ phiên song song, áp ngay:** phiên `-da` vừa mất một vòng ở TD-0130 vì thêm khoá
vào sự kiện RESERVE mà quên `trial_event.schema.json` — **735 test xanh KHÔNG bắt được**, vì bộ
test chỉ đối chiếu *fixture gõ tay*, chưa dòng nào đối chiếu **đầu ra thật**. Ở đây không có file
schema riêng để lệch (`KHOA_BAT_BUOC` dùng chung cho cả hàm ghi lẫn hàm đọc) và có test soi thẳng
đầu ra thật của `ghi_cache()`.

Bằng chứng: 33 test khoá xanh; `--collect-only` đo ngay trước khi so cho **784 → 817 = đúng +33**.

### 🔴 Tai nạn N12 lần thứ TƯ — lần này ở dạng mới

Tôi `git add` hai file TD-0143, soạn commit message, gọi `git commit` → **"nothing added to
commit"**. Chúng đã bị commit mất rồi, bởi `4ec0fd3` của phiên `-da`:

```
4ec0fd3  "TASKS.md: TD-0127 hoàn tất (🔒→✅) — L-Z27 + L-Z28 đã có máy canh"
 TASKS.md                                       |   2 +-
 src/tool_d/wfo/cache.py                        | 271 ++++++++    <- TD-0143, phiên khác
 tests/lock/test_td0143_cache_fold_mang_hash.py | 253 ++++++++    <- TD-0143, phiên khác
```

`CLAUDE.md` ghi tai nạn này đã xảy ra **3 lần**, cả 3 đều ở dạng *"task bị đánh ✅ giả"*. Đây là
lần thứ tư và là **dạng mới**: không ai bị đánh dấu sai, mà **code của một phiên bị chôn dưới
nhãn commit của việc khác**. Hệ quả không phải mất dữ liệu (nội dung trên đĩa khớp đúng bản
commit, `git diff HEAD` rỗng) mà là **lịch sử git nói sai về ai làm gì** — và lịch sử git thì
không viết lại được một cách an toàn khi bốn phiên đang commit đồng thời.

**Đã chọn KHÔNG rebase/reset.** Rebase lúc này nguy hiểm hơn hẳn cái sai nó sửa: ba phiên khác
đang có commit đi sau, một cú viết lại lịch sử sẽ kéo theo xung đột trên chính thư mục họ đang
gõ. Cách xử: **ghi thẳng sự thật** vào dòng TD-0143 của `TASKS.md` (*"code nằm trong 4ec0fd3,
không phải commit riêng"*) và vào entry này. Một dòng lịch sử sai kèm chú thích đúng thì tra
ngược được; một lịch sử bị viết lại giữa lúc bốn phiên đang chạy thì không cứu được.

🔑 **Điều N12 chưa nói mà lần này dạy thêm:** quy tắc hiện viết cho `TASKS.md` và các file trạng
thái dùng chung. Nhưng cơ chế gây hại — `git add` chụp *trạng thái đĩa*, không chụp *ý định của
người gọi* — áp cho **mọi file**, kể cả file mà phiên kia vừa tạo ra và chưa ai biết là có. Vùng
nguy hiểm nhất hiện tại là `src/tool_d/wfo/`: ba phiên cùng ghi vào đó (`folds.py`, `equity.py`,
`cache.py`). Cách phòng duy nhất đáng tin là `git add` **liệt kê đích danh từng file**, không bao
giờ `-A`, `-a`, hay thêm cả thư mục. Đã nhắn phiên `-da`.

### Ghi nhận thêm: hai test đỏ do TẢI, không phải hồi quy

Lần chạy full suite giữa chừng có `test_close_d1_gate` và `test_close_d2_gate` đỏ. Hai test đó
gọi `pytest` THẬT lồng bên trong (chủ ý — để nhãn bằng chứng `do-duoc` đúng nghĩa, MT-10), nên
khi bốn phiên cùng chạy container thì chúng chạm timeout. Chạy riêng: 23/23 xanh. Cùng hiện tượng
đã ghi ở TD-0085. **Không phải hồi quy — nhưng phải chạy riêng để xác nhận trước khi kết luận,
không được suy đoán.**

### Đính chính (cùng đêm) — chẩn đoán nguyên nhân N12 ở trên SAI

Mục trên viết: *"Nguyên nhân gần như chắc chắn: `git add -A` / `git commit -a`, hoặc `git add`
một thư mục"*, và kết luận *"cách phòng duy nhất đáng tin là `git add` liệt kê đích danh từng
file"*. **Cả hai đều sai**, và cái sai thứ hai nguy hiểm hơn vì nó cho cảm giác đã an toàn.

Phiên `-da` phản biện lại kèm bằng chứng, và tôi đã tự kiểm chứng:

```
git rev-parse --git-dir   -> .git        (một, không phải worktree riêng)
git worktree list         -> 1 worktree
GIT_INDEX_FILE            -> không đặt
```

**Bốn phiên dùng CHUNG một file `.git/index`.** Lệnh của họ là `git add TASKS.md && git commit -m
...` — đúng một file, đích danh, không `-A`. Bằng chứng đối chứng: 9 commit khác cùng phiên, cùng
kiểu lệnh, đều sạch.

🔑 **Cơ chế thật:** `git commit` không commit *"những gì tôi vừa add"* — nó commit **TOÀN BỘ
INDEX**. Trình tự đã xảy ra:

```
tôi:  git add cache.py test_td0143.py     -> index có 2 file của tôi
tôi:  (đang soạn commit message…)
họ:   git add TASKS.md                    -> index có 3 file, của HAI phiên
họ:   git commit -m "TD-0127 hoàn tất"    -> gói cả 3
tôi:  git commit                          -> "nothing added to commit"
```

Điều này cũng giải thích đúng thông báo lạ mà tôi nhận được.

**Vì sao khuyến nghị của tôi không cứu được:** `git add <đích danh>` chống được `-A`, nhưng không
chống được index dùng chung — vì vấn đề không nằm ở việc *add cái gì*, mà ở việc *commit lấy từ
đâu*. Ngay cả bước "đọc `git diff --cached` trước khi commit" mà N12 đòi cũng còn kẽ hở: giữa lúc
đọc và lúc commit, phiên kia vẫn kịp stage.

🚪 **Cách thật sự đóng được cửa sổ đó:**

```
git commit -- <đường/dẫn/file> [file2 …]
```

Có pathspec thì `--only` là **mặc định**: git commit đúng những path đó lấy từ working tree, **bỏ
qua phần còn lại của index**, và giữ nguyên file phiên khác đang stage. Không cần `git add` trước,
nên cũng bớt một lần ghi vào index dùng chung.

⚠️ **Điều `git commit -- <paths>` KHÔNG cứu được, vẫn phải tự lo:** với file thật sự dùng chung
(`TASKS.md`, `CLAUDE.md`, `back-end-note.md`), pathspec vẫn chụp **nội dung working tree** của file
đó tại thời điểm commit — nên vẫn phải đọc diff trước. Đó là N12 gốc, không liên quan index.

**Điều đáng ghi nhất, vượt ra ngoài git:** tôi chẩn đoán bằng cách nhìn *hình dạng hậu quả* (nhiều
file lạ trong một commit → "chắc dùng `-A`") thay vì kiểm *cơ chế* (`git rev-parse --git-dir`).
Giả thuyết khớp hiện tượng, nghe hợp lý, và **sai**. Cùng một hình dạng lỗi với ca `pathlib` sáng
nay: phép đo trả về kết quả ủng hộ giả thuyết sẵn có nên tôi không kiểm lại. Ở đây thì phiên khác
kiểm hộ — nhưng chỉ vì họ có bằng chứng đối chứng (9 commit sạch) mà tôi không thèm tìm.

`CLAUDE.md` mục **N12** hiện chỉ nói về `git add -A` và về nội dung file bị chụp nhầm; nó **không
nói gì về index dùng chung**, mà đó mới là cửa đã sập lần này. Sửa quy tắc trong `CLAUDE.md` là
quyết định của chủ dự án — đã báo, không tự sửa.

## 07/09/2026 — Rà soát độc lập khối D3: `L-Z55` trông như đang canh, nhưng gần như không canh gì

**Bối cảnh.** Backlog hết việc rảnh, chủ dự án giao rà soát độc lập khối D3 (TD-0140→TD-0146) trước
khi cổng D3 đóng. Phiên rà soát **không viết dòng nào** trong khối này — ba phiên khác viết — nên
ngữ cảnh vốn đã sạch theo đúng nghĩa quy tắc 18 nhắm tới.

**Kết luận chung: chất lượng cao.** Hai chỗ đáng ghi vì chúng chống đúng loại lỗi khó: test `L-Z47`
dựng số sao cho CỘNG và NHÂN cách xa nhau (2500 vs 3000) — số hiền thì code cộng nhầm vẫn xanh;
`cache.py` tách `STALE` khỏi `MISS` — gộp lại thì kết quả vẫn đúng nên không test nào đỏ, mà mất
đúng tín hiệu "có gì đó đổi ngoài ý muốn". 102 test D3 xanh.

**Phát hiện chính (→ TD-0148).** `folds.kiem_folds()` gọi `assert_dataset_timerange()` và docstring
module quảng cáo điều đó như một tính năng đầu bảng. Nhưng cả hai vế của phép so sánh đều suy từ
`wfo.start`: `train_start` CHÍNH LÀ `wfo.start`, `test_end` là `wfo.start` + số ngày từ config, biên
cũng từ `wfo`. Đúng cái bẫy mà `DatasetBoundary` **tự cảnh báo trong docstring của chính nó**:
*"KHÔNG được tính boundary từ cùng nguồn với observed — nếu cả hai đến từ cùng chỗ không đáng tin,
hàm này không bảo vệ được gì."* Phép kiểm chỉ có thể đỏ khi phép cộng vượt `wfo.end`, mà điều đó đã
được `can_ngay > co_ngay` bắt ở dòng trên. Nó chỉ có răng với danh sách fold **dựng tay** (đường test
đi) — không có răng với danh sách do `sinh_folds()` sinh.

Nặng hơn: phép kiểm ở tầng **dữ liệu thật** không được gọi ở đâu trong đường chạy WFO (`run_wfo.py`,
`orchestrator.py` — grep sạch).

**Gốc rễ không phải "ai đó quên gọi".** Bộ chạy backtest được tiêm vào dưới dạng
`Callable[[Fold], FoldEquity]`, mà `FoldEquity` chỉ có `starting_balance`/`final_balance`/`pnl_abs`
— **không mang một mẩu thông tin nào về dữ liệu đã thật sự đọc**. Orchestrator không thể kiểm kể cả
khi muốn: kiểu dữ liệu không có chỗ để đặt câu hỏi đó.

**Vì sao đáng dừng lại.** Không phải lo xa: TD-0093 (cùng ngày) đã ghi rằng
`download-data --timerange` KHÔNG cắt file — nến vùng LOCKBOX (tới 2026-09-05) đang nằm sẵn trong
đúng thư mục WFO sẽ đọc, và `--timerange` chỉ LỌC lúc backtest đọc lại. Một lần khai sai cận trên là
lọt, im lặng. LOCKBOX chỉ được chạm ĐÚNG MỘT LẦN (D9.5) — chạm nhầm thì không có đường lùi.

**Mức nghiêm trọng, nói cho cân:** hôm nay **không sai số nào** (chưa có bộ chạy backtest thật). Nó
cắn ở lần chạy WFO thật đầu tiên (D3.5+). Nên không gấp hôm nay, nhưng **phải xong trước khi cổng D3
đóng** — vì cổng đóng là lúc mọi người thôi nhìn phần này.

**Chủ dự án chốt phương án A + C** (bốn phương án đã cân: A đổi kiểu dữ liệu; B để tới D3.5; C chỉ
nói lại cho đúng; D tiêm thêm callback riêng):
- **A** — `FoldEquity` mang `observed_start`/`observed_end` BẮT BUỘC; `chay_wfo()` kiểm hai tầng
  (trong biên WFO **và** trong đúng cửa sổ của chính fold đó) trước `L-Z47`. Tầng thứ hai chặt hơn
  và bắt thêm **rò rỉ giữa các fold**, thứ L-Z55 nguyên bản không phủ. → **TD-0148**, chặn cổng D3.
- **C** — hạ lời tuyên bố trong docstring `folds.py` xuống đúng sự thật (làm ngay, commit này).

**Ba điều ghi rõ để không lặp lại chính sai lầm đang sửa:**
1. Ngay cả A cũng **chưa bảo đảm gì trên dữ liệu thật** tới D3.5 — bộ chạy thật chưa tồn tại, phép
   kiểm mới chỉ được nuôi bằng bộ chạy giả. *Cơ chế* tại chỗ ≠ *bảo đảm* có thật.
2. A **vẫn tin lời khai của bộ chạy**. Bộ chạy trả ngày *dự kiến* thay vì ngày *thật đọc được* sẽ vô
   hiệu hoá nó → bộ chạy thật (D3.5) bắt buộc đọc từ dataframe, và phải có test khoá riêng.
3. Bẫy lệch quy ước: cửa sổ fold **nửa mở** `[start, end)` vs ngày từ dataframe **bao gồm hai đầu**.
   Trộn hai quy ước là lệch đúng một ngày — mà một ngày ở đây là một ngày dữ liệu tương lai.

**Hình dạng lỗi lặp lần thứ ba trong ngày:** *thứ trông như đã được canh, nhưng chưa ai thử xem nó
có canh thật không.* Hai lần trước: (a) `trial_event.schema.json` không biết khoá mới mà 735 test
xanh không bắt được, vì test chỉ đối chiếu fixture gõ tay chứ chưa lần nào đối chiếu ĐẦU RA THẬT;
(b) `N12` mục 5 viết ra đã hở đúng ở ca file MỚI. Điểm chung: **lớp bảo vệ giả nguy hơn không có lớp
nào**, vì có nó thì người ta thôi cảnh giác.

**Hai phát hiện phụ (chưa mở task, đã báo phiên chủ quản):** (1) `folds.py` khi sơ đồ fold không vừa
dữ liệu báo *"sửa DR-D3-01 qua kênh L-Z26"*, nhưng `wfo_folds` nằm dưới `tier_c` mà
`param_proposals` **từ chối thẳng** mọi đề xuất chạm `tier_c` — hướng dẫn chỉ vào một cánh cửa chắc
chắn đóng. Đặt fold dưới `tier_c` là ĐÚNG (cầu dao, không phải núm vặn); chỗ sai là câu hướng dẫn.
(2) `cache.py:169` dùng `assert` trần cho một bất biến quan trọng — chạy Python chế độ tối ưu là nó
biến mất; nên là `raise CacheError`.

## 08/09/2026 — Rà TOÀN BỘ lớp canh bằng cách PHÁ THẬT: 19/19 đều có răng, và câu hỏi chẩn đoán sắc hơn

**Câu hỏi chủ dự án đặt ra:** *"phép kiểm này đã bao giờ được cho ăn một đầu vào SAI để xem nó có đỏ
không? — đó là thứ phân biệt lớp canh thật với lớp canh giả."*

**Cách đếm bằng heuristic ĐÃ THẤT BẠI, ghi lại để không ai làm lại.** Đếm dấu hiệu cú pháp
(`pytest.raises`, `assert not ...`) cho **20/46 file "không có ca sai"**. Nới heuristic theo tên test
thì ra **0/46**. Hai con số mâu thuẫn nhau ⇒ phép đo vô giá trị. Nguyên nhân: ca sai được viết bằng
vô số cách (`assert quet(mau_gia) == ["..."]`, `assert ma_thoat == 90`…) mà không mẫu cú pháp nào phủ
hết. **Bài học: đừng đo một tính chất ngữ nghĩa bằng dấu hiệu cú pháp.**

**Cách trả lời dứt khoát: PHÁ THẬT (mutation testing).** Clone repo ra lab riêng trong thư mục tạm
(`git clone --local`, KHÔNG `cp -r` — bản chép đầu bị LỆCH GIỮA CHỪNG vì phiên khác đang sửa
`equity.py` đúng lúc đó), mount vào `/workspace` (mount `/lab` vướng `safe.directory` của git),
baseline 539 test lock xanh. Rồi phá đúng thứ mỗi lớp canh bảo vệ, chạy test canh nó, khôi phục.

**Kết quả: 19 phép phá hợp lệ, 19/19 ĐỀU BỊ BẮT.** Gồm: ghép fold bằng CỘNG thay vì NHÂN; CTRL bị
tính vào N; bỏ trần B3; cache lệch vân tay vẫn trả payload; timerange không bao giờ raise; đề xuất
Cấp C được nhận; đơn vị đo bị cấm lọt vào `src/`; `IntParameter`; khung 15m; entrypoint thứ 9;
`contribution=0`; chỉ số THIẾU mặc định thành số ĐẠT; trần lỗ thiếu thành 0.0; best-known thành số
bịa; `verify_seal` bỏ qua hash lệch; `dedup_key` nhận trường rỗng; `render()` trả 0.0 cho "chưa đo"
(cả ở tầng hàm lẫn ở báo cáo E5 thật); bỏ bất biến "chưa đo thì không mang giá trị".

🔴 **HAI LẦN MÁY BÁO "XANH" ĐỀU LÀ NGƯỜI PHÁ SAI, KHÔNG PHẢI LỚP CANH GIẢ** — và đây là phần đáng ghi
nhất: lần một sửa một dòng chú thích, lần hai đổi chuỗi `value` của một `Enum` mà `render()` không
dùng. Cả hai **không đổi hành vi**, nên test xanh là ĐÚNG. Nếu tin ngay kết quả đầu tiên thì đã báo
hai lớp canh tốt là "giả". **Phá xong phải tự hỏi: phép sửa của mình có thật sự đổi hành vi không?**
Phiên song song cùng ngày mắc đúng dạng này hai lần (dữ liệu test sai bị tưởng là bug thật).

**KẾT LUẬN LẬT NGƯỢC GIẢ THUYẾT BAN ĐẦU.** Nếu mọi lớp canh đều có răng thì ba sự cố trong ngày
KHÔNG phải do lớp canh cùn. Nhìn lại cả ba:

| Sự cố | Có ca sai không? | Cái thật sự thiếu |
|---|---|---|
| `trial_event.schema.json` không biết khoá mới (735 test xanh không bắt) | CÓ (fixture hỏng → bị từ chối) | chưa bao giờ cho ăn **đầu ra thật** của `reserve()` |
| `L-Z55` ở `folds.kiem_folds()` | CÓ (fold dựng tay) | trên **đường thật** hai vế cùng nguồn → tự đúng |
| `N12` mục 5 hở ở ca file MỚI | KHÔNG có phép kiểm máy nào | — |

Điểm chung không phải "thiếu ca sai" mà là: **ca sai chỉ đi qua MẪU DỰNG TAY, chưa bao giờ đi qua
ĐƯỜNG SẢN XUẤT THẬT.** Lớp canh sắc, nhưng chĩa nhầm hướng.

🔑 **Câu hỏi chẩn đoán nâng cấp — dùng câu này từ nay:**
*"Ca sai đó có đi qua ĐƯỜNG SẢN XUẤT THẬT không, hay chỉ qua một mẫu dựng tay?"*
TD-0149 (đọc lại từ ĐĨA thay vì soi dict trong bộ nhớ) chính là câu trả lời đúng cho câu hỏi này.

**Rà tiếp theo câu hỏi mới** — 29 file bị nghi "chỉ dùng mẫu tay" tách thành ba nhóm, KHÔNG phải 29
lỗi:
1. **~9 file quét thẳng cây nguồn thật** (L-Z32/33/37/39/46/48c, TD-0057, L-Z24, L-Z42) — hiện vật
   được soi CHÍNH LÀ `src/` thật. Không phải khoảng hở; phép đo của tôi chỉ không nhận ra.
2. **~10 file mà BỘ SINH THẬT CHƯA TỒN TẠI** (L-Z1/6/18/19/30/31/34/35/43, TD-0105) — bộ sinh là
   chiến lược chạy trên dữ liệu, chưa viết. Mẫu tay là lựa chọn DUY NHẤT hôm nay. **Đây là nợ phải
   trả khi bộ sinh ra đời (D3.5+), không phải lỗi hôm nay** — nhưng phải nhớ, vì đó đúng là lúc
   khoảng hở loại này sinh ra.
3. **Phần còn lại CÓ phủ đường thật, đôi khi ở FILE KHÁC.** Ví dụ `check_td0120` trông như chỉ chạy
   trên đơn dựng tay, nhưng `test_td0124_cong_cu_nop_don.py` chạy nó trên đơn do `submit_idea()` THẬT
   sinh ra. `L-Z13` gọi `append_access_record()` thật; `L-Z45` gọi `ghi_neu_chua_co()`/`ghi_nhieu()`
   thật. **Bài học phụ: đo phủ sóng theo TỪNG FILE là sai đơn vị** — phủ sóng có thể nằm ở file khác.

**Không tìm thấy khoảng hở loại "bộ sinh đã có mà chưa ai nối" nào còn sót**, ngoài ba cái đã tìm và
đã đóng trong ngày (TD-0148, TD-0149, TD-0150). **Giới hạn của kết luận này, nói rõ:** phần đối chiếu
chéo giữa các file làm TAY trên 4 file tiêu biểu, không phải cả 29 — nên đây là "không thấy", không
phải "chứng minh không có".

---

## 08/09/2026 — 🚪 GATE D3 ĐÓNG (TD-0147), tag `d3-complete`

`registry/runtime_state.json.d3_complete = true`, sinh từ một lần chạy THẬT trong Docker
(`E6 --close-d3-gate` qua service **`freqtrade`**, exit 0). Ba mục evidence đều `do-duoc` đúng
nghĩa MT-10: `full_suite` **973 passed** · `test_khoa_d3` (L-Z47 22 · L-Z45 23 · TD-0148 14,
**mỗi file chạy RIÊNG một lượt**) · audit sổ trial **5/14 đạt, 0 chưa đạt**. Chạy lại → exit
**94**, từ chối ghi đè.

### Ba điều lần chạy thật này dạy ra, không có cái nào thấy được từ code

**1. 🔴 Ba cổng D1/D2/D3 đều ghi `git_sha` nhưng KHÔNG cổng nào kiểm cây làm việc có sạch không.**
Lần chạy đóng cổng D3 ĐẦU TIÊN có 8 ca đỏ ở `test_lz27_lz28` + `test_td0130`; chạy lại riêng
ngay sau đó: **40/40 xanh**. Nguyên nhân: suite của cổng chạy **6,5 phút**, đúng lúc phiên song
song sửa dở `registry.py` (67 dòng chưa commit).

Lần đó cổng từ chối vì suite đỏ. **Nhưng nếu các sửa đổi kia tình cờ không làm đỏ test nào thì
cổng ĐÃ ĐÓNG, với `d3_git_sha` trỏ tới một commit KHÔNG chứa thứ vừa được kiểm** — bằng chứng
tự mâu thuẫn: nó nói *"đã kiểm ở sha X"* trong khi cái được kiểm là *"X cộng vài file ai đó
đang gõ dở"*. Cổng là hành động một chiều, nên không được để nó dựa vào may.

Đã vá cho D3: từ chối khi cây có thay đổi chưa commit, kiểm **TRƯỚC** cả suite (từ chối sớm,
không tốn 4 phút), và ghi `d3_cay_sach: true`.

🔴 **Hạn chế KHÔNG sửa được của D1 và D2:** hai cổng đó đóng khi cây có sạch hay không thì
**giờ không truy lại được**, vì chúng không ghi. Không sửa hai cổng đã đóng — chúng bất biến,
sửa là viết lại bằng chứng đã niêm phong. Ghi nhận ở đây để người sau biết mức tin cậy của
`d1_git_sha`/`d2_git_sha` thấp hơn `d3_git_sha`.

**2. Chốt đầu tiên viết ra QUÁ CHẶT, và một chốt không bao giờ thoả được thì tệ hơn không có
chốt.** Bản đầu dùng thẳng `GitInfo.is_clean`, mà `git status --porcelain` tính cả file CHƯA
THEO DÕI — repo này luôn có ảnh chụp màn hình, `scratch_dl/`, `.playwright-mcp/` ở gốc. Chạy
thật lần hai: cổng từ chối dù **không file theo dõi nào bị sửa**. Nếu để vậy, sớm muộn ai đó
gỡ bỏ chốt.

Sửa bằng cách phân loại đúng cái đang cần bảo vệ:
- file **đã theo dõi** bị sửa/xoá/staged → LUÔN tính (đổi hành vi mà không nằm trong sha);
- file **chưa theo dõi** → chỉ tính khi nằm trong `src/` `tests/` `entrypoints/` `config/`
  `registry/schemas/`. Một file `.py` chưa commit trong `tests/` **vẫn được pytest thu** và
  **vẫn không có trong commit** — đúng loại làm bằng chứng sai. Ảnh chụp màn hình thì không.

Thông báo từ chối nay **liệt kê đúng file nào gây chặn**, để người đọc biết phải bảo ai commit.

**3. Suite của repo KHÔNG độc lập với service Docker — "N passed" là phát biểu về MỘT service.**
Lần chạy đầu tôi dùng service `lockbox` theo lời khuyên "E1/E2/E3 phải chạy qua `lockbox`". Lời
khuyên đó đúng cho E1/E2/E3 (chúng gọi `verify_all_seals()`) nhưng **sai với E6**. Service
`lockbox` là service DUY NHẤT *không che* `lockbox/data/` (dành cho E4 sau D9), nên 3 test vốn
khẳng định *"dữ liệu lockbox phải bị che"* đỏ hoàn toàn đúng:
`test_touch_lockbox.py::test_trong_container_tests_du_lieu_bi_che_nen_verify_fail` và 2 ca
`test_run_backtest_cache.py`. Ai chạy nhầm service sẽ tưởng hồi quy.

### Bẫy PASS RỖNG bắt được trong chính đợt này (cái thứ ba của khối D3)

Fixture `_cay_sach` (autouse) thay `_thay_doi_anh_huong_phep_do` bằng lambda trả rỗng — nên lớp
test kiểm CHÍNH hàm đó sẽ gọi bản GIẢ và xanh mà chưa bao giờ chạy vào logic phân loại. Giữ
tham chiếu `PHAN_LOAI_THAT` từ lúc import. Cùng họ với hai ca trước: `flock` bị gỡ mà test đồng
thời vẫn xanh (TD-0144), và schema chỉ soi fixture chứ không soi đầu ra thật (TD-0146).

### Kiểm có răng, đủ ba lớp

- Gộp ba file test cốt lõi vào MỘT lượt pytest → đúng ca `test_moi_file_chay_RIENG_khong_gop`
  đỏ, 12 ca còn lại xanh. (Gộp lại thì một file bị xoá vẫn cho tổng > 0 nhờ hai file kia.)
- Vô hiệu hoá tầng (b) của TD-0148 → đúng 5 ca đỏ, 9 ca tầng (a) xanh.
- Đổi phép NHÂN thành CỘNG ở `equity.py` → đúng 4 ca đỏ, 18 ca xanh.

### Phạm vi thật của cổng D3 — đọc sai chỗ này là hỏng cả D3.5

`d3_han_che` (nhãn `nguoi-khai`) ghi thẳng: **cổng D3 chứng nhận BỘ ĐIỀU PHỐI H3-D đúng, KHÔNG
chứng nhận đã có kết quả walk-forward.** Chưa có bộ chạy backtest thật (E2 dừng ở
`EXIT_CHUA_CO_BO_CHAY`); mọi phép kiểm mới chỉ được nuôi bằng **bộ chạy GIẢ**. Và TD-0148 **vẫn
tin lời khai của bộ chạy** — bộ chạy trả ngày *dự kiến* thay vì ngày *thật đọc từ dataframe* sẽ
vô hiệu hoá nó hoàn toàn. Khi D3.5 viết bộ chạy thật: **bắt buộc đọc ngày từ dataframe, và phải
có test khoá riêng cho đúng điều đó.**

---

## 08/09/2026 — 🚪 GATE D3.5 ĐÓNG (TD-0166), tag `d3-5-complete` — Khối 15 khép lại

`runtime_state.json.d3_5_complete = true`, sinh từ một lần chạy THẬT trong Docker qua service
**`freqtrade`** (`E6 --close-d3-5-gate`, exit 0). Bốn mục evidence đều `do-duoc`: `full_suite`
**1102 passed** · `test_khoa_d3_5` (Bước 1 **23** · Bước 2 **33** · Bước 3 **14** · L-Z58 **28** ·
L-Z56 **14**, mỗi file chạy RIÊNG) · `cong_d35_kiem_cong` · audit sổ trial **5/14 đạt, 0 chưa đạt**.
`d3_5_git_sha = 9596beb` khớp đúng HEAD; chạy lại → exit **94**.

**Xác nhận cổng và E3 nhất quán:** sau khi đóng, chạy `E3 run_ablation.py` đi qua được `L-Z56` và
dừng ở `NotImplementedError` của logic ablation (việc của D4) — đúng như thiết kế.

### Thiết kế đáng giữ lại: cổng dùng CHUNG máy với E3

Ba cổng trước chỉ chạy test rồi ghi file. Cổng D3.5 gọi thẳng **`kiem_cong_d35()`** — chính hàm
mà E3 dùng để TỪ CHỐI chạy ablation. Nhờ vậy *"điều kiện đóng cổng D3.5"* và *"điều kiện được
chạy ablation"* là **MỘT**. Nếu tách đôi thành hai danh sách song song, sớm muộn sẽ có lúc "cổng
đã đóng" mà E3 vẫn từ chối chạy, và **không ai biết bên nào đúng**.

### Lỗ hổng tìm được khi làm TD-0165, đáng nhớ hơn cả bản vá

`L-Z56` đòi *"kết quả Δ_R … **đã commit**"*. Nhưng TD-0161 **tính Δ_R trong bộ nhớ** rồi ghi dòng
CTRL vào sổ trial — **không lưu con số ra file nào**. Tức **không có gì để "đã commit"**, và Δ_R
có thể đổi lặng lẽ SAU khi thấy kết quả ablation: đúng thứ DR-015 §1 gọi là *"trạng thái tệ nhất
có thể"*. Sinh `docs/du-lieu-do/dr015-buoc1-delta-r.json` bằng cách **gọi `tinh_buoc1()`** của
TD-0161, không tính lại bằng công thức riêng.

Và thêm một chốt spec không đòi: **tính lại Δ_R từ dữ liệu thô đã commit rồi đối chiếu artifact**.
Một file commit từ tháng trước vẫn "đã commit" hoàn hảo trong khi công thức đã đổi — lúc đó
ablation chạy với con số không còn là thứ code hiện tại sinh ra.

### 🔴 Con số của Bước 2 từng SAI, và cách nó bị bắt

Vòng đo đầu của TD-0162 cho **15/91 "không khớp" (16,5%)** — đủ lớn để đảo kết luận Z0-vs-DCA.
Kiểm lại: **15/15 ca đó chạm được `p` SAU mốc backtest**. Nguyên nhân: `order_filled_timestamp`
KHÔNG phải mốc giá thật chạm mức, và nó lệch **cả hai chiều** (TD-0115 đã ghi chiều ngược lại).
Neo cửa sổ một phía vào một mốc lệch hai chiều là **tự tạo ra kết quả**.

Đo độ nhạy đầy đủ thay vì chọn một cửa sổ: p_nf = 16,5% ở cửa sổ 0 → **0% ở cửa sổ ≥ 15 PHÚT**,
phẳng tới 3h. Đường cong **dựng đứng** nên kết luận không dựa vào giả định rộng tay — trễ tối đa
**+4,4 phút**, dưới một nến 5m, và 76/91 ca xuyên TRƯỚC mốc.

### Phát hiện lật ngược giả thuyết nền của DR-015 (Bước 3)

Δ_R(Z0) = **0,1552** vs Δ_R(DCA) = **0,1612** → tỉ lệ **1,04**, tức **TƯƠNG ĐƯƠNG**. DR-015 giả
định sai số cộng dồn theo số tranche nên DCA chịu nhiều hơn; dữ liệu nói tranche 1 — thứ Z0 cũng
có — lệch gần bằng hệt. **Hệ quả cho §4:** phép hiệu chỉnh bất đối xứng (chỉ trừ Δ_R khỏi DCA)
**rộng hơn bất lợi thực của riêng DCA**. Vì thế `ket_luan_buoc3` được làm thành **tham số BẮT
BUỘC** của §4 — cách duy nhất khiến không ai đọc kết quả mà thiếu câu đó.

Cũng ghi: hai nhánh bằng nhau ở P90 nhưng **hình dạng phân phối khác hẳn** (Z0 trung vị ~0 + vài
ca lệch lớn; DCA lệch nhỏ nhưng đều). Bằng nhau ở một phân vị không có nghĩa chịu sai số y hệt.

### Bốn hạn chế đã ghi vào `d3_5_han_che` — cổng này dễ bị đọc quá tay nhất

Nó có `p_nf = 0` trông rất sạch. (1) Bước 2 đo **gián tiếp**, không đặt lệnh thật; ba thứ không
quan sát được (post-only bị từ chối, khớp một phần, vị trí hàng đợi) đều tính về phía bất lợi.
(2) Chỉ **LONG**; `Δ_R(SHORT)` là `unreadable` — bật Short thì `L-Z56` sẽ **chặn** ablation.
(3) Bước 3 kết luận **tương đương**. (4) `p_nf = 0` đo trên tập backtest **ĐÃ CẤP** khớp — đúng
tập §3 cần, **không** trả lời câu rộng hơn.

### Bài học quy trình

- **Một phép kiểm "đã có" vẫn có thể bỏ sót đúng nhánh cần canh.** Rà soát độc lập bắt được lỗi
  trong `phan_xu()` (TD-0167): nhánh `z0 == 0` khẳng định *"Z0 không lệch còn DCA có lệch"* mà
  không kiểm `dca`. Test `test_z0_bang_0_khong_chia_cho_0` **đã tồn tại** nhưng chỉ thử một tổ
  hợp. Nguyên tắc rút ra: **viết ca biên thì liệt kê CÁC TỔ HỢP của biên, không chỉ một đại diện.**
- **Tai nạn N12 lặp lại:** commit `TASKS.md` của phiên này nuốt một dòng của phiên khác. Pathspec
  KHÔNG cứu được khi cả hai cùng sửa MỘT file — đúng giới hạn N12 mục 5 đã ghi sẵn. Điều rút ra:
  với `TASKS.md` phải đọc `git diff` **ngay trước lúc commit**, không phải lúc bắt đầu sửa.
- **Trùng lặp còn lại, ghi nhận chứ không sửa:** vòng lặp chạy-riêng-từng-file của
  `close_d3_gate()` nay trùng với helper `_chay_rieng_tung_file()`. KHÔNG refactor code của một
  cổng ĐÃ ĐÓNG. Đây là trùng lặp của một **cơ chế an toàn** — đáng gộp khi có dịp an toàn.


## 09/09/2026 — DG2 có giết tranche 3 không? Đo trên dữ liệu thật (TD-0182, phiên `-f4`)

**Chẩn đoán §0d.7: "bot sai" hay "tầng đo sai"?** → **Tầng đo sai (fixture), bot đúng.**

### Chuỗi bốn giả thuyết, mỗi cái bị một phép đo bác

| # | Giả thuyết nghe hợp lý | Phép đo bác nó | Thời gian đo |
|---|---|---|---|
| 1 | "125 dòng nối TD-0182 bị lỗi nên 0 lệnh" | `tuoi_trend_nen()` trả `None` ở **92/92** nến 1D; EMA20/50 chỉ **một dấu** trên toàn chuỗi ⇒ dốc đơn điệu không bao giờ cross | < 1 phút |
| 2 | "pha giảm tôi thêm vào làm lật EMA 4H" | EMA 4H quanh nến tín hiệu **giống hệt từng con số** cũ/mới | < 1 phút |
| 3 | "DG2 đọc chặt giết tranche 3 một cách hệ thống" | 48 mã alt EXPLORE, [T0,T2]: chặt **21,0%** vs lỏng **22,2%** đủ ba tranche | 2 lượt backtest |
| 4 | "DG4 cũng chặn nên vá dốc chưa đủ" | Các dòng `DG4: False` nằm ở **+11h**, tức phần đuôi log tôi đã cắt bằng `tail -30`; ở mốc +8h chỉ DG2 chặn | đọc lại log |

### Kết luận

**DG2 đọc chặt (`UP → FLAT` cũng fail) KHÔNG giết tranche 3.** Giá của nó là **1,2 điểm
phần trăm** ≈ một lệnh trên 81. Diễn giải của phiên `-2f` đứng vững; không mở DR.

Fixture cũ khớp đủ 3 tranche là **TRÙNG HỢP**: hệ thống cũ không lọc trend nên lệnh mở
lúc 4H đang DOWN ⇒ `t4=DOWN` ⇒ tranche 2/3 vẫn DOWN ⇒ `DOWN == DOWN` cho qua. Hệ thống
mới bắt vào lệnh khi 4H UP, cú lùi kéo EMA20 xuống dưới EMA50 trong 1-2 nến ⇒ chặn.
**Fixture cũ nghiệm thu cỗ máy DCA bằng một lệnh mà hệ thống mới sẽ không bao giờ mở.**

### Hai con số về hệ thống, KHÔNG phải về fixture — phải đọc kèm mọi kết quả D4

- **Chỉ ~21% số lệnh bơm đủ ba tranche; 41% dừng ở một tranche.** Ablation D4 sắp đo
  một hệ thống mà tranche 2/3 hiếm khi xảy ra.
- **DG4 (trần chờ 8 nến 1H) chặn nhiều gấp bảy DG2.** ⚠️ Nhưng tỉ lệ theo *lần xét cổng*
  **thổi phồng cổng DAI** (hết cửa sổ rồi thì mọi lần hỏi sau đều chặn) và **làm nhẹ cổng
  THOÁNG QUA**. Con số đáng tin là phân bố theo LỆNH. `dg4_bars_1h` là tham số `tier_b`
  **chưa hề calibrate** (TD-0190: 12/12 đều là chỗ giữ).

### Hình dạng lỗi thứ tư của dự án: BỘ SINH LỖI THỜI SO VỚI HỆ THỐNG NÓ NUÔI

Ba hình dạng đã ghi trước đây: *lớp canh cùn* · *chĩa nhầm hướng* (ca sai chỉ đi qua mẫu
dựng tay) · *người bị canh tự chọn phạm vi bị canh* (TD-0190). Cái thứ tư:
**không ai viết sai dòng nào — fixture đúng với hệ thống CŨ và im lặng sai với hệ thống MỚI.**
Nó im lặng theo hướng nguy nhất: không lỗi cú pháp, không ngoại lệ, chỉ **0 lệnh** — mà
`0 lệnh` thì **mọi khẳng định về lệnh đều đúng-vô-nghĩa**. Nếu hai file test đó không có
chốt PASS RỖNG thì cả 17 ca đã XANH và không ai biết gì.

### Bẫy PASS RỖNG tự tạo rồi tự bắt — trường hợp cụ thể nhất từ trước tới nay

`test_enter_tag_co_zs_t4_sw_va_t4_la_UP` chép hằng số `"2025-01-01"` (lần thứ BA trong
file) để đổi giờ mở lệnh ra chỉ số nến. Kéo dài lịch sử làm mốc thật lùi về 2024-11:

    chỉ số ĐÚNG (suy ra)          : 873  → nến giá 96,90  dir=UP   ← nến tín hiệu
    chỉ số CŨ (hardcode 2025-01-01): 513  → nến giá 44,30  dir=UP   ← giữa đoạn dốc
    lệch 360 nến = 60 NGÀY, và vẫn XANH vì nến sai tình cờ cũng UP

Vá bằng `_moc_bat_dau()` suy từ đuôi — một nguồn sự thật cho mốc — cộng chốt chặn chỉ số
ngoài phạm vi.

### Lỗi chỉ lộ trên dữ liệu THẬT

`zone_valid_4h` mang `NaN` ở vùng warmup; pandas từ chối dùng mảng chứa `NaN` làm mặt nạ
⇒ backtest **crash**. Bộ sinh tổng hợp không có vùng warmup đó nên không bao giờ chạm tới.
Cùng họ: `download-data --timerange` **không tôn trọng mốc kết thúc** (bug TD-0093) tái
hiện y nguyên — **10/10 file** lấn quá T2, hai file `1d`/`funding_rate` chạy tới
**2026-09-07/08**, lấn sâu 7 tháng vào vùng LOCKBOX.

### 🔑 Bài học về LỜI KHAI, mở rộng bài học `TD-0041` đã ghi ở CLAUDE.md

Tôi chuyển cho phiên `-94` mô tả của TD-0082 (*"chưa nhân `mult_*`, chưa chia đòn bẩy"*)
**như thể đã kiểm chứng** — tôi chỉ trích lại chữ. Họ đo lại và bác vế đòn bẩy: `min_stake`
của Freqtrade đã chia đòn bẩy, mà `stake` ta trả cũng chia, **hai vế cùng chia nên đòn bẩy
triệt tiêu khỏi phép so**; "sửa cho khớp" bằng cách chia thêm lần nữa sẽ làm mọi mã qua
trong khi sàn thật không đổi. Nguyên nhân thật với BTC là vế `minQty × giá` (78,54) thắng
`MIN_NOTIONAL` (50).

N12 mục 3 dạy đừng tin dấu ✅ trong `TASKS.md`; CLAUDE.md đã ghi *"một dòng trạng thái có
ngày tháng trông giống một sự thật hơn là một cái ✅"*. Đây là **cùng cái bẫy ở chỗ thứ ba**:
> **Một dòng MÔ TẢ VIỆC cũng là lời khai, không phải bằng chứng.**

### Ghi chú phạm vi — đừng đọc quá tay

- 72 exception `SizingError` trên BTC/ETH là bằng chứng về **cơ chế**, KHÔNG phải vi phạm
  của pool: BTC/ETH **không nằm trong pool giao dịch** (§0.3b, chỉ ở EXPLORE).
- Con số 17/81 đo trên **48 mã alt EXPLORE**, cùng họ với ca pool nhưng **chưa ai đo** con
  số cho pool 102 mã.

## 09/09/2026 (tiếp) — Quét 9 arm trên EXPLORE: HAI loại "arm trùng nhau", và bốn lần tôi nói quá phạm vi đã đo

Phiên `-f4`. Bằng chứng: `docs/du-lieu-do/dg2-explore-quet-arm.json` (48 mã EXPLORE alt,
`[T0,T2]`, `E_D = 750`, **0 trial** — `DR-D0PRE-05 §4` cho EXPLORE sinh giả thuyết).
Ranh giới cố ý: chỉ đếm lệnh / phân bố tranche / phân bố `R_eff`. **KHÔNG** đo expectancy
theo arm — EXPLORE bị cấm dùng để validate.

### Vì sao quét: D4 sắp đặt chỗ 9 suất trial trong 114

| arm | lệnh | 1tr | 2tr | 3tr |
|---|---|---|---|---|
| Z0 · Z1 · Z0-V1 | 83 | 83 | 0 | 0 |
| Z2 · Z3 | 83 | 34 | 34 | 15 |
| Z3b | 84 | 35 | 34 | 15 |
| Z0-T0 | 1202 | 1202 | 0 | 0 |
| Z0-T1 | 292 | 292 | 0 | 0 |
| Z0-S1 (trước DR-D4-07) | **0** | — | — | — |

So **TỪNG LỆNH** (mã + giờ mở + số tranche + giờ đóng): `Z2` ≡ `Z3` và `Z0` ≡ `Z0-V1`,
**0 lệch trên 83 lệnh**.

### 🔴 HAI loại "trùng nhau" — khác nhau về BẢN CHẤT, và cách xử trái ngược

| | `Z1`, `Z0-V1` ≡ `Z0` | `Z2` ≡ `Z3` |
|---|---|---|
| Nguyên nhân | **Công tắc KHÔNG được nối vào chiến lược** | DG5 có nối, nhưng **không ràng buộc lần nào** |
| Bản chất | **LỖI cài đặt** | **PHÁT HIỆN về dữ liệu** |
| Sửa được không | Có — nối vào | Không có gì để "sửa" |
| Đổi tham số có tác dụng? | **KHÔNG** — `v_min` chưa từng được đọc | Có, nếu ngưỡng đổi |

Đo (đếm ký hiệu trong `ZoneAbsorption.py` tại `ebc5089`):

```
entry_confirmation / tim_xac_nhan_entry / bat_dieu_kien_c : 0   ← §3.3b KHÔNG nối
sl_neo_atr / ke_hoach_theo_arm / CHE_DO_SL_THEO_ARM       : 0   ← SL của Z1 KHÔNG nối
── đối chứng, những thứ CÓ nối ──
danh_gia_tat_ca 3 · cong_ap_dung 2 · duoc_them_tranche 3
tang_cua_arm 2 · du_dieu_kien_trend_theo_tang 4
```

`v_min` chỉ xuất hiện trong chính `entry_confirmation.py` và hai dòng chú thích ⇒ **đường
chạy sản xuất chưa bao giờ đọc nó**. Phát hiện của phiên `-94`.

🔑 **Vì sao phân biệt này đắt:** hai giả thuyết dẫn tới **hai hành động khác nhau**. Nếu
`Z0-V1` ≡ `Z0` vì *"`v_min = 1.0` trung tính"* thì siết `v_min` sẽ tách được hai arm. Nếu vì
*"code không hề gọi"* thì đổi `v_min` **không làm gì cả**. Tôi đưa ra giả thuyết thứ nhất từ
**hậu quả** (83/83 trùng khít); `-94` đọc **cơ chế** và bác. Con số của tôi đúng, lời giải
thích thì không.

Cùng hình dạng `TD-0188` đã đặt tên: **canh đúng chỗ nhưng đường chạy không bao giờ đi qua**.
`test_td0183_cong_tac_arm.py` canh công tắc ở tầng module và **xanh** — không test nào ở tầng
chiến lược hỏi *"công tắc này có được GỌI không"*.

### Bốn lần tôi phát biểu vượt quá phạm vi đã đo — cùng một buổi, cùng một người bắt

| # | Tôi nói | Thực tế |
|---|---|---|
| 1 | *"chưa chia đòn bẩy"* (chép mô tả TD-0082) | `min_stake` và `stake` **cùng** chia ⇒ triệt tiêu |
| 2 | *"`E_D` 750 xoá sạch 17 lỗi định cỡ"* | Đúng — nhưng là **sàn Freqtrade**, không phải sàn Tool D (chặt hơn 36%, chưa nối) |
| 3 | Áp `MT-19` vào câu hỏi về 4 mã pool | Câu đó chỉ cần **metadata sàn**, không cần dữ liệu giá pool ⇒ không bị chặn |
| 4 | *"log không lọt vì mức DEBUG"* | Cả hai dòng đã là `logger.info`; tôi suy từ ca của mình (`GATE_CHECK` **thật sự** là DEBUG) sang ca của họ mà không `grep` |

Cả bốn **không sai ở phép đo** mà sai ở **nhãn dán lên phép đo**. Và cả bốn bị bắt bởi **một
người khác chạy lại**, **không** bởi bất kỳ lớp canh nào — vì không công cụ nào ở đây kiểm
tra *phạm vi hiệu lực* của một con số đúng.

📌 Ghi thêm một vế mà `-94` chỉ ra: ở ca #4, **chính tôi** là người đã tự bắt cùng cái bẫy ba
giờ trước (thấy `GATE_CHECK: 0` và suýt kết luận *"không cổng nào chặn"*, rồi tự kiểm ra là
`_chay()` không truyền `-vv`). Tức cơ chế tự sửa **đã có hiệu lực một lần** trước khi thất
bại ở lần thứ hai — hiểu đúng nó là *"chưa thành phản xạ"*, không phải *"không có"*.

### Ảnh trong gương của PASS RỖNG — tên do `-94` đặt

| | PASS RỖNG | Chặn nhầm |
|---|---|---|
| Chốt nằm ở | đúng chỗ, nhưng **không thể đỏ** | **sai chỗ**, chặn câu nó vốn không chặn |
| Im lặng theo chiều | **nguy hiểm** — số đẹp, tưởng đã kiểm | **an toàn** — tưởng mình đang thận trọng |
| Cơ hội bị lộ | còn, khi kết quả vô lý | **không có** |

Vế cuối là chỗ đắt: hậu quả duy nhất của chặn nhầm là **một phép đo không bao giờ được chạy**
— mà một phép đo không chạy thì **không để lại dấu vết nào để nghi ngờ**, và **không ai đi
kiểm một chốt vì nó quá nghiêm**. Ca hôm nay suýt tiêu một suất trial cho thứ đọc miễn phí.

Và một hạng thứ ba, phát hiện khi phá thật `TD-0191`: **PASS RỖNG do CHỌN SAI BẤT BIẾN**.
Quay `Z0-S1` về hằng số USDT cứng → 4 ca đỏ, **nhưng ca *"không phụ thuộc `R_eff`"* VẪN XANH**
— một hằng số dĩ nhiên thoả bất biến ấy. Bất biến **đúng**; nó chỉ không phân biệt được thứ
cần phân biệt. Khác *lớp canh cùn* (bất biến vô nghĩa) và khác *chĩa nhầm hướng* (ca sai
không đi qua). `-94` báo cùng buổi họ dính đúng dạng đó với 7 ca AST/chuỗi.

### Hệ quả cho D4 — chưa đặt chỗ

Sau `DR-D4-07`, `Z0-S1` chạy được (0 → 83 lệnh). Còn lại: **`Z1` và `Z0-V1` là bản sao của
`Z0` do lỗi nối** — hai suất trial mua thông tin bằng không, và đây là lỗi **sửa được**, khác
hẳn `Z2`≡`Z3`. `-94` đang báo cáo đầy đủ cho chủ dự án; **không phiên nào tự sửa**, vì nối
§3.3b đổi hành vi vào lệnh của toàn hệ thống và vùng đó có rủi ro lookahead thật (cùng vùng
`TD-0170` từng dính).

⚠️ Giới hạn: mọi con số trên đo trên **EXPLORE alt**, không phải pool 102 mã. `Z2`≡`Z3` là
phát biểu về **tập dữ liệu này**, không phải về DG5 nói chung.

---

## 09/09/2026 (tiếp, phiên `-46`) — TD-0195: một tham số "tunable" mà đường chạy không đọc; phép đối chứng đo được giá của nó

### Câu hỏi không ai đặt: giá trị trong YAML có CHẢY tới phép tính không?

Dự án đã có `L-Z15` (khai `TUNED`/`FROZEN` đủ chưa), có `dof_inventory.yaml` (đếm bậc tự do),
có `param_status.yaml`, có kiểm kê DOF nuôi rào DSR. Cả bốn đều nói về **tư cách** của một
tham số. Không cái nào hỏi **đường đi** của nó.

Đo tĩnh bằng AST (`docs/du-lieu-do/do_duong_doc_tham_so_tier_b.py`, 0 trial, không mở một nến
nào): **7 trong 12 khoá `tier_b` không có một literal `"tier_b.<khoá>"` nào** ở vị trí giá trị
trong `src/`, `user_data/strategies/`, `entrypoints/` — tức `resolve()` không thể được gọi cho
chúng. Giá trị thật đến từ hằng số cứng trong `.py`:

| khoá `tier_b` | hằng số cứng | hàm đóng cứng | có trên đường chạy sản xuất? |
|---|---|---|---|
| `zss_threshold` | `zone_strength.py:20 NGUONG_ZSS` | `zone_hop_le` | ✅ `ZoneAbsorption:314`/`:400` |
| `buf_sl_atr` | `trade_plan.py:20 BUF_SL_HE_SO` | `tinh_ke_hoach` | ✅ qua `ke_hoach_theo_arm` `:322` |
| `dg6a_atr_ratio` | `dg6_early_invalidation.py:22` | `dieu_kien_a` | ✅ `:808` |
| `dg6d_retrace_frac` | `:26 NGUONG_HOI_GIA_D` | `dieu_kien_d` | ❌ chưa ai gọi (`d=False` cứng) |
| `funding_rate_pct` | `:25 NGUONG_FUNDING_D` | `dieu_kien_d` | ❌ như trên |
| `wick_close_upper_frac` | số ma `0.5` (`entry_confirmation:134,136`) | `_la_nen_rejection` | ❌ MT-21 |
| `v_min` | — (đối số, chưa ai truyền) | — | ❌ MT-21 |

### 🔑 Phép đối chứng — đo được GIÁ của lỗ hổng, thay vì suy luận về nó

Suy luận *"đổi YAML sẽ không có tác dụng"* nghe hiển nhiên, nhưng dự án này đã bị **sáu lần**
một phát biểu nghe hợp lý bị một phép đo dưới một phút bác (ghi 09/09 phần trên). Nên đo:

Lab dựng bằng `git clone --local` (không `cp -r` — bài học 08/09). Đổi `zss_threshold` từ
`0.5` lên `0.99` trong YAML, chạy `test_td0187` (backtest THẬT) ở hai commit:

| cây | kết quả | nghĩa là |
|---|---|---|
| `0152158` — TRƯỚC bản vá | **17 passed** | ngưỡng gần như không thể đạt, mà **mọi thứ vẫn xanh** |
| `0b5112d` — SAU bản vá | **1 failed, 16 errors** (số zone hợp lệ → 0) | YAML thật sự điều khiển phép tính |

Dòng đầu là bằng chứng trực tiếp: một trial B3 chi cho việc calibrate `zss_threshold` sẽ mua
về **thông tin bằng không**, và bảng kết quả trông hoàn toàn bình thường vì hai cấu hình cho
ra cùng một tập lệnh. Đây là **cùng họ MT-15** (bẫy PASS RỖNG đốt ngân sách) nhưng ở tầng
khác: MT-15 làm hai *arm* trùng nhau, cái này làm hai *cấu hình* trùng nhau.

🔴 **Và nó im lặng hơn MT-15 một bậc.** MT-15 ít nhất còn để lại hai cột giống hệt nhau trong
bảng arm. Ở đây, hai cấu hình khác nhau trong sổ trial cho cùng một kết quả — mà **sổ trial
ghi cấu hình, không ghi tập lệnh**, nên không có chỗ nào để hai cột đứng cạnh nhau mà lộ ra.

### Lớp canh, và giới hạn của chính nó — được chứng minh bằng phép phá, không bằng lời

`tests/lock/test_td0195_*` quét AST đòi mỗi khoá `tier_b` có ít nhất một literal đường dẫn.
Kiểm có răng: trả `NGUONG_ZSS` về hằng số cứng ⇒ **đúng 1 ca đỏ** (`test_hang_so_khong_quay_lai`).

🔑 Nhưng phép phá đó cũng phơi ra **giới hạn của lớp canh, đúng chỗ docstring tự khai**: ca
`test_co_it_nhat_mot_duong_doc[zss_threshold]` **VẪN XANH** sau khi phá — vì `ZoneAbsorption`
vẫn *đọc* YAML rồi *truyền xuống*, chỉ có hàm nhận là bỏ qua giá trị đó. Literal vẫn còn, nên
phép kiểm tĩnh vẫn thấy "có đường đọc". **Lớp canh chứng minh được chiều PHỦ ĐỊNH (không có
literal ⇒ chắc chắn không đọc), không chứng minh được chiều KHẲNG ĐỊNH.** Vế khẳng định do
phép đối chứng đổi-YAML ở trên gánh, và đó là lý do phải làm nó chứ không dừng ở AST.

### Vì sao XOÁ hằng số chứ không đổi tên hay để làm mặc định

Ba hằng số bị xoá hẳn. Giữ lại làm giá trị mặc định của đối số nghe tiện và không phá test nào
— nhưng đó chính là cơ chế đã sinh ra lỗ hổng: một đường gọi quên khai sẽ chạy bằng con số ai
đó viết một lần trong quá khứ, **và không có gì báo**. Cùng lý do `bat_dieu_kien_c` của
`entry_confirmation` không có mặc định (nếu có, hai arm lại nhập làm một).

Fixture `L-Z49` (`ZoneAbsorptionMinimal`) và `ZoneDetectionProbe` cũng phải đọc YAML: một
fixture giữ bản sao riêng thì thứ nó chứng minh chạy được là **một cấu hình không ai chạy**.

### 📌 Phát hiện phụ chưa xử — ĐƠN VỊ, và vì sao không vá luôn

`funding_rate_pct` trong YAML là **-0.05** (phần trăm); hằng số cũ là **-0.0005** (tỉ lệ). Cùng
một số vật lý, khác đơn vị. Nối mà quên ÷100 thì ngưỡng sai **100 lần** — đúng lớp lỗi `L-Z48c`
sinh ra để chặn. Vì `dieu_kien_d()` chưa có người gọi trên đường chạy, vá bây giờ là vá một
đường không ai đi, và câu đơn vị phải chốt TRƯỚC. Đã ghi vào `MIEN_TRU` của lớp canh kèm điều
kiện gỡ, và lớp canh có ca **báo đỏ khi miễn trừ hết hạn** — một danh sách miễn trừ không tự
dọn sẽ lặng lẽ phình ra cho tới lúc che mất chính thứ nó được lập ra để theo dõi.

### 🐛 Lỗi của chính bản vá, và thứ đã bắt được nó

`_quet_zone_dinh` là `@staticmethod`; tôi truyền `self._nguong_zss` vào. Mọi backtest
`ZoneAbsorption` crash `NameError` — **5 failed + 27 errors**. Không phải đọc lại code bắt
được, mà là **chạy suite**. Đọc lại chỉ xác nhận thứ mình đã tin; chạy là thứ phân biệt "sửa
xong" với "tưởng là xong". Sau khi sửa: **1481 passed, 0 failed** (Docker, 2:18).

### Phối hợp ba phiên — quy ước N12 mục 6 hoạt động đúng như thiết kế

Ba phiên cùng thư mục. Trước khi mở tài liệu/mã việc mới tôi nhắn cả hai; `-28` (đang giữ
`take_profit.py`/`ZoneAbsorption.py` dở) trả lời rồi commit xong mới tới lượt tôi, `-be` xác
nhận không giữ gì. Khi commit, `api-integration-rules.md` của `-28` đang sửa dở nằm trong cây —
`git commit -- <pathspec đích danh>` bỏ qua nó đúng như N12 mục 5 mô tả. Kiểm lại sau commit:
file đó **không** nằm trong commit của tôi.

---

## 09/09/2026 (tiếp, phiên `be`) — TD-0193: nối §3.3b, và con số đầu tiên đo trên hệ thống ĐỦ tầng nói gì về D4

### Bối cảnh và cách đi

TD-0193 là mảnh cuối của tầng vào lệnh (MT-21): `entry_confirmation.py` có test khoá từ TD-0129,
`quet_xac_nhan_zone()` có từ chặng 1 (`c80e3bd`), nhưng `ZoneAbsorption.py` chưa gọi một dòng
nào — `Z0 ≡ Z0-V1` 83/83 lệnh. Trước khi code, phân tích hệ thống trình chủ dự án (không phải
"nối một bộ lọc" mà là **đổi cơ chế vào lệnh**: từ *vào ngay tại nến 4H xác nhận zone* sang *vào
tại nến 1H xác nhận C sau lần chạm đầu*), chốt `DR-D4-08` (P1 + sáu diễn giải) rồi mới có lệnh
"bắt đầu code". Bốn commit thi hành: `99114fb` (tầng thuần) → `19dfabc` (nối + fixture + 15 ca
khoá) → `2a76b74` (đo). Full suite Docker **1552 passed, 0 failed** = 1524 + 11 + 15 + 2, đúng cộng.

### Chín khoảng hở tìm ra khi ĐỌC (không có trong TASKS.md) — ba cái đáng nhớ

1. **`quet_xac_nhan_zone` ghi cứng `bat_dieu_kien_c=True`** — tức arm `Z0-V1` KHÔNG biểu diễn được
   qua chính hàm sinh ra để nối §3.3b. Nối nguyên như thế là tái diễn MT-15 ngay sau khi vừa bịt,
   và không phép kiểm nào ở tầng hàm thuần báo (mọi ca đều `True`). Thứ bắt được là câu hỏi
   *"arm này đi vào hàm này bằng đối số nào?"* — hỏi ở tầng NỐI, không phải tầng hàm.
2. **Script đo MT-22 bắt đầu quét từ giờ MỞ của nến 4H `j`** (`moc.get(z["ts_j"])`), tức 4 nến 1H
   *trước khi* zone xác nhận — lookahead nhẹ trong một phép đo mô tả. Đo lại với mốc đúng
   (`date4[j] + 4h`): A **42,8%** vs 43,1% cũ — con số gần như không đổi, nhưng **cơ chế** thì sai,
   và ở sản xuất cùng cái sai đó là lookahead thật. Đúng bài học `4ec0fd3`: đúng con số không
   chứng minh đúng cơ chế.
3. **Fixture `test_td0187` lỗi thời lần thứ BA** (TD-0182, TD-0194, nay TD-0193): nến "chạm p1"
   qua `_chia_nho()` đóng SÁT ĐÁY, không phải rejection ⇒ hệ thống mới ra 0 lệnh ⇒ 13+ ca
   xanh-vô-nghĩa. Vá bằng **bốn nến 1H tường minh gộp lại ĐÚNG nến 4H cũ** (khung 4H không đổi
   một giá trị) + đối chứng thường trực thứ hai gắn vào `_sinh_du_lieu` gọi đúng hàm sản xuất.
   📌 Bản đầu tìm nến chạm theo offset −36 từ cuối — vỡ ngay ở fixture `test_td0189` vì file đó
   cắt đuôi rồi nối kịch bản riêng. Tìm theo GIÁ TRỊ (phải duy nhất) thay vì theo vị trí.

### Phép phá và giới hạn tự khai

- Đối chứng âm lookahead có răng: bản chép ghi tín hiệu tại C−1 ⇒ ca cắt-tại-C đỏ. **Nhưng** phép
  phá "quét từ giờ mở `j`" (lỗi thật của script MT-22) **KHÔNG cắn** trên bộ sinh này — không có
  lần chạm nào bên trong `j`. Canh riêng bằng AST + ca thời gian `C ≥ close(j)`. Ghi ra vì đây là
  đúng dạng *"lớp canh sắc nhưng fixture không có ca để nó cắn"* (08/09).
- Test Z0 ≠ Z0-V1 bản đầu đòi `sum(Z0) < sum(Z0-V1)` — SAI: Z0 vẫn vào ở nến khác trong cửa sổ
  (qua (b)), hai tập có cùng LỰC LƯỢNG mà khác PHẦN TỬ. Tiêu chí đúng là *tập tín hiệu khác nhau*,
  chính là thứ MT-21 đo (83/83 trùng khít), không phải *ít hơn*.

### 🔴 Con số quan trọng nhất — và nó không phải về §3.3b

`docs/du-lieu-do/td0193-lenh-nam-explore.json` (88 mã EXPLORE, 99,4 mã-năm, [T0,T2], 0 trial,
chỉ đếm):

| Bước | Số | |
|---|---|---|
| Zone đáy hợp lệ | 4.918 | |
| §3.3b A xác nhận | 2.103 | 42,8% zone; nhánh (b) 46% |
| Sau bộ lọc trend Phần 2 | **96** | **4,6%** số xác nhận |
| Lệnh thật (backtest, cấu hình thật) | **62** (Z3 = Z0) | 0,62/mã-năm ⇒ quy đổi pool **63,6/năm** |

**Sàn Nhánh 1 (§10.2) là 150 lệnh/năm.** Theo `DR-D4-08` §6: DỪNG, không đặt chỗ TD-0184, trình
chủ dự án. Ba điều phải đọc kèm: (a) **bộ lọc trend là chốt cắt 95%, không phải §3.3b** — nới
§3.3b không cứu được số mẫu; (b) EXPLORE ≠ pool, quy đổi ×102/88 là tỉ lệ thô; (c) không
`--timeframe-detail` (EXPLORE không có 5m) — đủ để ĐẾM lệnh, không đủ để nói gì về TP.

### 📌 Phát hiện phụ, ngoài phạm vi, chỉ ghi

TP1 nổ 21/62 lệnh, **100% là nạng** (`TP1_fallback_r_multiple`), **0** lệnh TP theo zone đỉnh —
H-4 = 100% trên EXPLORE. Có thể là dữ liệu (không zone đỉnh trong `4,0 × R_eff`) hoặc là
`_zone_dinh_tren` trên dữ liệu thật; chưa phân biệt được, chưa ai đo. Không sửa trong TD-0193
(quy tắc 4) — báo `-28` (TD-0189) và ghi vào TASKS.

### Bài học về cách làm

Phân tích trước khi code tốn hơn một giờ và tìm ra chín khoảng hở mà "nối vào" theo TASKS.md sẽ
không thấy — nhưng thứ đắt nhất lại không nằm trong chín cái đó: **con số lệnh/năm** chỉ đo được
*sau khi* nối, và nó nói D4 sắp đo một hệ thống chưa đủ mẫu để nói gì. Nếu không có điều kiện
§6 viết TRƯỚC trong DR, phiên này đã đóng TD-0193 ✅ và TD-0184 sẽ đặt chỗ 9 suất ngay.

### Bổ sung theo góp ý của `-46` — hai câu có thể đổi HƯỚNG kết luận, cả hai đều lật một giả thuyết

**(1) Trong 95% mà bộ lọc trend cắt, bao nhiêu là điều kiện tuổi (hiện tượng đo `None`/NaN)?**
Tách bốn điều kiện §2.5 tại 2.103 nến C:

| Điều kiện | Còn lại | Cắt |
|---|---|---|
| Tại C | 2.103 | — |
| §2.1 hướng 1D = UP | **400** | **81%** (DOWN 1.339 · FLAT 364 · NaN warmup 126) |
| §2.2 4H đồng hướng | 160 | 60% của phần còn |
| §2.5 ADX ≥ 20 | 137 | 14% |
| §2.3 tuổi ≥ 5 | **96** | chỉ **41** tín hiệu (2% số C) trượt riêng vì tuổi |

Giả thuyết của `-46` **không đứng** — và đó là kết quả tốt: chốt cắt là **§2.1 hướng 1D**, một
**tính chất cấu trúc** của chiến lược (zone đáy hình thành chủ yếu trong xu hướng giảm; hệ thống
chỉ mua chúng trong xu hướng tăng), không phải hiện tượng của phép đo. Hệ quả cho D4: hai arm
`Z0-T0`/`Z0-T1` (§10.1b) chính là câu hỏi *"tầng 1D đáng giá bao nhiêu mẫu"* — và số mẫu của chúng
sẽ **lớn gấp nhiều lần** các arm còn lại, tức bảng arm sẽ so những cỡ mẫu rất khác nhau.

**(2) Phép quy đổi 88 mã EXPLORE → 102 mã pool sai về hướng nào?** `EXPLORE ∩ pool(trading) = 0`
(tách hẳn theo `DR-D0PRE-05`) nên không kiểm chéo được mà không chạm pool (MT-19). Nhưng phân bố
theo mã lộ ra một hướng lệch rõ: **median 0 tín hiệu/mã-năm** (quá nửa số mã KHÔNG có tín hiệu
nào trong 1,8 năm), P75 1,33, max 3,87; **BTC + ETH — KHÔNG thuộc pool — góp 13/96 tín hiệu (13,5%)
từ 2/88 mã**. ⇒ 98,5 tín hiệu/năm và 63,6 lệnh/năm là **CẬN TRÊN theo chiều BTC/ETH** (bỏ hai mã
đó: 0,87/mã-năm ⇒ ~88 tín hiệu/năm). Phần alt còn lại lệch hướng nào so với pool (thanh khoản
≥ 15M, tuổi niêm yết ≥ 180 ngày) — **chưa biết**, ghi là chưa biết. Kết luận "dưới sàn 150" vì thế
**không phải quá sớm**: sửa theo chiều đã biết thì con số còn thấp hơn.

📌 Bản đầu của phép so trùng tên gộp cả khối `explore` của `pool.yaml` ⇒ "trùng 100/100" — vô
nghĩa nhưng trông như một kết quả. Tự bắt vì 100/100 quá đẹp; sửa `_ten_pool()` đọc đúng khối
`trading`.

## 09/09/2026 (tiếp, phiên mới) — TD-0189: 21/21 lệnh TP1 đều rơi nạng — bug hay cấu trúc thị trường?

Phiên `be` báo (đo trên chính con số ở mục trên, 62 lệnh THẬT của TD-0193 trên EXPLORE): **0/21**
lệnh có TP1 nào dùng zone đối diện — 100% `TP1_fallback_r_multiple`. Đây là code của tôi
(`_quet_zone_dinh`/`_zone_dinh_tren`, TD-0189), nên nhận đo lại trước khi ai đó coi 0% là một kết
luận về D4.

**Không phải bug.** Đo trực tiếp (`docs/du-lieu-do/td0189-diem-thoi-gian-zone-dinh-explore.py`,
0 trial, DR-014 §2) trên chính 100 mã EXPLORE: `_quet_zone_dinh` tìm được **4.775 zone đỉnh
CONFIRMED** trên 219.338 nến 4H (91/100 mã có ít nhất một) — hàm hoạt động, không phải trả về
rỗng có hệ thống.

🔑 **Nhưng tại một điểm thời gian bất kỳ (KHÔNG điều kiện theo trend), tỉ lệ có ≥1 zone đỉnh CÒN
SỐNG (chưa bị giá đóng cửa vượt qua) nằm trong 5% phía trên giá chỉ 17,6%; trong 12% (≈ trần tìm
zone `4×R_eff` ở `R_eff` điển hình ~3%) là 35,9%.** Đây là **CẬN TRÊN** của tỉ lệ thật tại các
điểm ENTRY, vì entry chỉ mở khi 4H/1D đã xác nhận UP một thời gian (Phần 2) — đúng điều kiện làm
zone đối diện gần đó nhiều khả năng ĐÃ bị phá (giá đã vượt qua trong chính cú tăng dẫn tới entry).
`_zone_dinh_tren()` không tự lọc "còn sống", chỉ lọc `zone > p_avg` — nhưng trong ngữ cảnh uptrend
đã xác nhận, một zone bị phá thường đã nằm DƯỚI `p_avg` hiện tại (giá đã đi qua nó) nên bị lọc
gián tiếp; hai cách lọc trùng nhau phần lớn ĐÚNG trong ngữ cảnh entry thật (LONG-only).

Kết luận: 0/21 (n nhỏ, không đủ khẳng định tỉ lệ chính xác) là kết quả **PLAUSIBLE**, cùng chiều
với DR-D4-06 (79-87% nạng khi áp hạn tuổi) — không phải dấu hiệu lỗi trong `_quet_zone_dinh`.

⚠️ **Việc CHƯA làm, và không nên làm bằng script rời:** đo H-4 chính xác (`ty_le_khong_co_zone`/
`ty_le_zone_qua_han`, DR-D4-06 §3) cần TỪNG lệnh thật với đúng `p_avg`/`R_eff`/thời điểm tại lúc
xét TP — không suy ra đáng tin từ một phép đo không điều kiện như trên. Đợi TD-0184 (bộ chạy E3,
Decision Log thật) sinh dữ liệu đúng hạt, đo lại từ đó — tránh dựng một đường đo song song rồi có
hai con số cho cùng một câu hỏi (đúng bài học N1/MT-03).

## 09/09/2026 — TD-0200: tải 5m cho 102 mã pool trên WFO; và H19 (a) sao lưu là một ✅ RỖNG

**Vì sao dừng lại thay vì chạy ablation:** pool có 5m cho đúng **2/102 mã**, mà cả hai phủ
`[2024-06-01, 2025-05-31]` — **kết thúc TRƯỚC T1 (2025-06-12)** ⇒ số mã dùng được cho WFO là **0/102**.
Không có 5m thì `--timeframe-detail 5m` vô hiệu, và spec gọi đó là *"backtest thiên vị có lợi một
cách hệ thống"* (D5, dòng 2923) / *"rủi ro số một của toàn bộ kết quả Tool D"* (D6, dòng 2924) /
*"🔴 Bắt buộc P0"* (H5, dòng 4342). 🔴 **Chiều thiên vị không trung tính:** mọi arm DCA có ba lần
khớp so với một của Z0 (spec dòng 1215) ⇒ thiếu 5m ưu ái arm DCA **đúng chiều** Nhánh 2 §10.2 đang
phán quyết. Chủ dự án chốt **phương án A** (tải trước) thay vì chạy rồi ghi hạn chế.

**Kết quả (0 trial — DR-014 §2 chỉ tính *đánh giá cấu hình*):** 102/102 mã tải xong trong 6 phút 08;
**101 mã có 5m dùng được** (TRIA rỗng — niêm yết 06/02/2026, sau T2, đúng như 5 file `TRIA*` khác);
**5.887.071 nến**, phạm vi `2025-06-12 00:00` → `2026-01-28 23:55`. Độ phủ đo bằng chính hàm
`_load_bt_data_detail()` gọi (`history.load_data(..., startup_candles=0)`), không phải bằng đếm file
trên đĩa: **101 mã nạp được 1h, 101 mã nạp được 5m, 0 mã có 1h mà thiếu 5m.**

🔑 **Vì sao mẫu số là "mã có 1h" chứ không phải "/102":** mã niêm yết sau T1 chỉ có 5m từ ngày niêm
yết; lấy /102 làm một chốt **không bao giờ thoả được** vì một lý do không phải khuyết tật — đúng bài
học *"chốt không bao giờ thoả thì tệ hơn không có chốt"* của cổng D3. (Phiên `-dc` đã đổi mẫu số của
dải cảnh báo dashboard theo đó, `de66235`.)

🔴 **Đọc trước khi ai đó tin một lượt backtest pool:** `backtesting.py:1739` có `and pair in
self.detail_data`. Mã **thiếu 5m KHÔNG làm backtest đỏ** — nó lặng lẽ chạy ở 1H trong khi mã khác
chạy 5m, và bảng kết quả trộn hai độ phân giải mà không cột nào nói ra. Vì thế *"có 5m"* phải KIỂM
ĐỘ PHỦ, không suy từ *"lệnh tải exit 0"*. TD-0184 phải ghi độ phủ 5m vào bản ghi kết quả.

### Bốn phát hiện, ba trong đó bác chính chẩn đoán đầu của tôi

**1. Bẫy TD-0093 còn sống, và KHÔNG ĐỀU GIỮA CÁC KHUNG.** Tải thử 1 mã (ADA) cho ra 5m **đúng phạm
vi tuyệt đối** (66.528 nến, không dư một nến), trong khi CÙNG lượt đó `mark` lấn tới `2026-02-16` và
`funding_rate` lấn tới `2026-09-10` — 7 tháng vào LOCKBOX. Rồi trên 102 mã thì **4 mã** (`NOM`,
`PROM`, `STRK`, `VIRTUAL`) lấn đúng 24 nến 5m qua T2. ⇒ *"khung này tải đúng phạm vi"* **không suy ra
được** cho khung khác, và *"mã này đúng"* không suy ra được cho 102 mã. Đã cắt; đã verify seal
lockbox PASS (service `lockbox`, service duy nhất thấy `lockbox/data/`).

**2. 🔴 Lệnh tải KHÔNG được cho chạm thư mục pool.** `download-data -t 5m` ở chế độ futures **luôn
kéo thêm** `1h-mark` + `1h-funding_rate` — tức nó sẽ ghi đè hai loại file đã cắt đúng ≤ T2 từ
TD-0093, rồi lại lấn ra. Nên tải vào thư mục **nháp** rồi chỉ chép `*-5m-futures.feather`. Đây là
chọn có ý thức, không phải cẩn thận thừa: 204 file lẽ ra không có lý do gì bị đụng.

**3. 🔴 H19 `--verify-after` bắt được một hư hại THẬT do chính lần nhập này gây ra — lớp gác đúng,
người sai.** `shutil.copy2` cho cả 101 mã: với 99 mã chưa có file 5m thì copy = tạo mới; với
`1000BONK`/`1000PEPE` thì đã có file 5m cũ của TD-0115 và copy = **GHI ĐÈ**, mất 105.120 nến mỗi
file. H19 in đúng: *"khoảng cũ có 105120 nến, sau khi tải còn 0 — dữ liệu cũ bị ghi đè/cắt bớt,
KHÔNG phải gộp"*. Đã gộp lại từ bản sao lưu (`105.120 + 66.528 = 171.648`, không trùng một nến —
hai đoạn rời nhau, còn hở `01→11/06/2025` nằm ngoài cả hai vùng cần), verify lại **PASS 507 file**.
📌 Ghi ra để không ai đọc nhầm thành *"H19 báo động giả"*: đây đúng cái bẫy LD-27 mà H19 sinh ra để
chặn, và nó chặn được ngay lần đầu có người đi vào.

**4. 🔴 `E8 --snapshot-before` in `✅ H19 (a) đã sao lưu` mà KHÔNG có bản sao lưu nào — hai đường
độc lập cùng dẫn tới đó.** Bằng chứng lạnh: `C:\tool-d-data-backup` **không tồn tại** trước hôm nay,
dù TD-0093 đã chạy `--snapshot-before` trên 510 file hồi 07/09.

- **Đường A (mọi shell, tham số mặc định):** `--backup-root` mặc định là `../tool-d-data-backup`;
  trong container cwd là `/workspace` và `docker-compose.yml` chỉ mount `..:/workspace`, nên đích là
  `/tool-d-data-backup` — **không nằm trên volume nào**, bốc hơi khi `--rm`.
- **Đường B (Git Bash):** truyền tay `--backup-root /backup` thì MSYS đổi thành
  `C:/Program Files/Git/backup` TRƯỚC khi tới container. Chuỗi đó **không bắt đầu bằng `/`** nên
  Linux hiểu là đường dẫn **TƯƠNG ĐỐI so với `/workspace`** ⇒ 93 MB ghi thẳng vào **gốc repo**, dưới
  thư mục tên `C` + **U+F03A** — **lần thứ BA** hình dạng này xuất hiện trong dự án (hai lần trước:
  `backup_lockbox(dest_dir=...)` suýt bị xoá nhầm, ghi trong CLAUDE.md).

🔑 **Chẩn đoán đầu của tôi SAI, và sai theo hướng dễ chịu:** tôi kết luận *"bản sao lưu bốc hơi trong
container"* và nói với cả chủ dự án lẫn phiên `-dc` như vậy. Nó không bốc hơi — nó **rơi vào trong
repo**. Chỉ phát hiện vì `git status` hiện một dòng `??` lạ. Cùng bài học `4ec0fd3`: **chẩn đoán theo
HÌNH DẠNG HẬU QUẢ (*"không thấy bản sao lưu ở chỗ mong đợi"*) thay vì kiểm CƠ CHẾ (*"nó đi đâu?"*)
thì giả thuyết vẫn khớp hiện tượng mà vẫn sai.** Đã đối chiếu tên + kích thước + 8 mẫu sha256 (khớp
hết) với bản ngoài repo rồi mới xoá — đúng tiền lệ 07/09 khi thư mục `C` + U+F03A hoá ra chứa bản
backup lockbox thật.

🔑 **Câu đáng giữ, rộng hơn ca này:** *một thao tác GHI từ trong container ra ngoài `/workspace` là
ghi vào hư không, và không có gì báo.* Vế `(c)` chụp vân tay của cùng hàm đó sống sót **chỉ vì** nó
ghi vào `runs/` — tức trong `/workspace`. **Cùng một hàm, hai vế, một vế thật một vế ảo, cùng in ✅.**
Phạm vi đã ĐO (không suy rộng): grep 8 file `entrypoints/` cho ra **đúng 4 cờ nhận đường dẫn, tất cả
trong `backfill_data.py`** (`--data-dir`, `--backup-root`, `--snapshot-out`, `--verify-after`);
`--with-params-file` có ở 8/8 file nhưng là cờ **bool**, tên nó lừa mắt khi grep.

⏳ **Chưa sửa, đã trình chủ dự án (quy tắc 2):** `E8` nên KIỂM FILE TRÊN HOST sau khi chép rồi mới in
✅ — mã thoát 0 không chứng minh gì về **vị trí** ghi. Khuôn đúng đã có sẵn ở repo front-end
(`scripts/thu-thap-du-lieu.mjs` → `chayLockTestsQuaDocker()`: `existsSync()` trên đường tuyệt đối,
không thấy file thì trả `coDuLieu: false` kèm lý do thay vì in dấu thành công). Cùng lúc, đề xuất ghi
quy ước *"chạy entrypoint có cờ đường dẫn thì dùng PowerShell, không dùng Git Bash"* vào `CLAUDE.md`
— không tự ghi, đó là file trạng thái dùng chung (N12).

**Provenance (§0d.5):** `freqtrade download-data --pairs-file runs/pool_pairs.json -t 5m
--timerange 20250612-20260129 --datadir scratch_dl/tai-5m --data-format-ohlcv feather`, Binance
USDⓈ-M futures thật, tải 09/09/2026 qua service `freqtrade`. Sao lưu trước khi ghi:
`C:\tool-d-data-backup\futures` (512 file, 93 MB) + vân tay `runs/backfill_snapshot_5m_truoc.json`
(507 file — 5 file `TRIA*` rỗng nên `read_candles` trả `unreadable`, đúng N6, không phải bỏ sót).

### Phụ lục TD-0200 (cùng ngày) — "route thứ ba" bị bác; và `mtime` sau copy là thuộc tính của NGUỒN

Phiên `-46` đọc mục trên rồi đo lại độc lập và thấy khác: `C:\tool-d-data-backup\futures` **CÓ**
512 file, mtime **07/09**, *không file nào* mtime sau 08/09 — kể cả sau khi TD-0200 vừa chạy. Từ đó
nêu giả thuyết có **route thứ ba**: một lần chạy `backfill_data.py` TRỰC TIẾP trên host hồi 07/09
(hàm `backup_data_dir()` là Python thuần `shutil`+`pathlib`, chạy được bằng Python 3.14 của host),
khi đó `../tool-d-data-backup` resolve tự nhiên ra đúng chỗ ⇒ *"H19 chỉ nói dối KHI CHẠY QUA
DOCKER"*, chứ không phải luôn luôn.

**Đo lại, và giả thuyết bị bác:**

| | |
|---|---|
| `CreationTime` thư mục `C:\tool-d-data-backup` | **2026-09-10 08:35:09** |
| `LastWriteTime` file mẫu (`1000BONK-1d`) | 2026-09-07 01:43:44 |
| `CreationTime` file mẫu | **2026-09-10 08:35:52** |
| `LastWriteTime` file NGUỒN trong repo | 2026-09-07 01:43:44 — **trùng khít** |

**Cơ chế:** `backup_data_dir()` gọi `shutil.copytree`, mặc định dùng `copy2`, mà `copy2` **giữ
nguyên mtime của nguồn**. Nên `mtime = 07/09` là mtime của lần TD-0093 **TẢI DỮ LIỆU**, không phải
của lần **SAO LƯU**. `CreationTime` của cả thư mục lẫn từng file đều là hôm nay, trong đúng lượt
PowerShell đã in `✅ H19 (a) đã sao lưu -> /backup/futures`.

Đối chứng thứ hai, độc lập với dấu vết trên đĩa: `Glob` trên `C:\tool-d-data-backup` chạy **TRƯỚC**
lượt snapshot đầu tiên trả về *"Directory does not exist"* — đo trực tiếp vào đúng câu hỏi, thay vì
suy từ vết để lại. (Chênh 93 vs 95 MB là MiB vs MB — 97,6 MB thập phân; chênh `01:43` vs `10:37` là
múi giờ giữa Git Bash và PowerShell.)

🔑 **Bài học, và nó là của `-46`: `mtime` sau một thao tác copy là thuộc tính của NGUỒN, không phải
bằng chứng về thời điểm THAO TÁC.** Muốn hỏi *"thứ này có từ bao giờ"* thì hỏi `CreationTime`, hoặc
tốt hơn: đo *"nó có tồn tại không"* NGAY TRƯỚC khi hành động, rồi dùng phép đo đó làm mốc. Cùng họ
với bài học `4ec0fd3` (*chẩn đoán theo hình dạng hậu quả thay vì kiểm cơ chế*), nhưng ở đây dấu vết
đủ thật để hai phiên suýt đọc sai theo **hai hướng ngược nhau** — một bên kết luận *"chưa bao giờ có
bản sao lưu"*, một bên kết luận *"đã có từ 07/09"*, cả hai từ cùng một thư mục.

📌 **Kết luận của mục chính GIỮ NGUYÊN, không nới:** vẫn chỉ có hai route, và không route nào tạo ra
bản sao lưu ở đúng chỗ. Nhưng giả thuyết route-thứ-ba của `-46` đáng ghi lại vì nó **có thể đúng**
cho một dự án khác: `backfill_data.py` thật sự chạy được trên host, và khi đó `--backup-root` mặc
định thật sự trỏ đúng chỗ. Tức bản vá cho `E8` không được dựa vào giả định *"luôn chạy trong
Docker"* — phép kiểm phải là *"file có đáp xuống đích không"*, hỏi trên chính hệ tệp đang chạy.

## 09/09/2026 (tiếp) — TD-0184 Phương án A: đo Short + phát hiện rào DSR không tự qua dù đạt sàn 150

Chủ dự án chốt Phương án A cho vấn đề 63,6 lệnh/năm < sàn 150 (§10.2 Nhánh 1): đo phía SHORT trên
EXPLORE trước (0 trial, chỉ đếm), rồi làm đồng thời với việc đo độ nhạy rào DSR — phiên `be` nêu
một phát hiện lớn hơn hẳn câu hỏi ban đầu, đáng ghi lại nguyên vẹn cách nó lộ ra.

**Phát hiện của `be` (đã tự verify độc lập, không tin lời khai):** Nhánh 1 có HAI rào, không phải
một. Sàn 150 lệnh/năm là rào thứ nhất; rào DSR (`mean_R − dsr_hurdle(N)×std_R/√n ≥ 0,10`, code thật
ở `gates/dsr.py`/`gates/thresholds.py`, `dsr_hurdle(114) = √(2·ln 114) = 3,0777` — verify khớp)
là rào thứ hai, ĐỘC LẬP. Ablation D4 chạy trên cửa sổ WFO chỉ **0,63 năm** (spec dòng 3287), nên
`n` thật dùng cho rào DSR luôn nhỏ hơn "lệnh/năm" rất nhiều: đạt ĐÚNG sàn 150/năm thì `n ≈ 95`, và
với `std_R` giả định 1,25 thì `mean_R` cần đạt **0,49** mới qua — một con số rất cao cho một hệ
thống DCA. 🔴 **Đạt sàn 150 KHÔNG tự động qua được rào DSR** — hai điều kiện trong cùng Nhánh 1
không kéo nhau, và spec không nói rõ điều đó.

🔑 **`std_R`/`mean_R` KHÔNG được tự đo ở đây, dù có vẻ là bước hiển nhiên tiếp theo.** Tính hai đại
lượng đó cần `pnl_abs` lệnh thật — trên CALIB/WFO là "chạm dữ liệu" (DR-014 §2), tiêu 1 trial, đúng
việc TD-0184 định làm và đang bị chặn; trên EXPLORE thì `DR-D0PRE-05` §4 cấm thẳng ("KHÔNG
expectancy, KHÔNG PnL theo arm"). Không có đường vòng hợp lệ. Xử bằng
`docs/du-lieu-do/td0184-do-nhay-rao-dsr.py`: BẢNG ĐỘ NHẠY thuần toán (import thẳng công thức từ
`gates/dsr.py`, không chép lại — N1), quét nhiều giả định `std_R` × nhiều mốc lệnh/năm, không đo
bất kỳ dữ liệu nào. Mọi ô trong bảng là ĐIỀU KIỆN GIẢ ĐỊNH, không phải kết quả đo — ghi rõ trong
chính file để không ai đọc nhầm.

**Đo Short (Bước 1, `docs/du-lieu-do/do_short_pheu_tin_hieu_explore.py`):** mirror ĐÚNG các hàm sản
xuất (`_tinh_zone_4h`→zone đỉnh, `_xac_nhan_3_3b`→`loai="dinh"` + SL-invalidation lật dấu,
`du_dieu_kien_trend_theo_tang(huong_muc_tieu="DOWN")` — hàm đã generic sẵn, không viết lại), CHỈ
đếm TÍN HIỆU, không chạy backtest (Short không có tầng thực thi — `can_short=False`, không đi qua
`custom_stake_amount`/`mult_regime` nên không dính bug TD-0197 đang được vá). Kết quả trên 88 mã
EXPLORE: **368,4 tín hiệu/năm quy đổi pool** (Long chỉ 98,5 tín hiệu/năm cùng tầng) — khớp hướng đã
đoán (64% thời gian 1D DOWN vs 19% UP cho Long). 🔴 **So SAI TẦNG là lỗi dễ mắc nhất ở đây:** Long
đã đo tới tầng LỆNH THẬT (63,6/năm, sau backtest+admission+sizing), Short chỉ đo tới tầng TÍN HIỆU
— cộng thẳng hai số khác tầng là trộn hai đại lượng cùng tên khác nghĩa (họ lỗi `L-Z48c`). Áp tỉ lệ
tín-hiệu→lệnh ĐO ĐƯỢC của Long (64,56%) cho Short (GIẢ ĐỊNH, không đo — Short không có tầng thực
thi riêng để đo tỉ lệ của chính nó) ⇒ ước lượng Short ≈ 237,8 lệnh/năm ⇒ tổng ước lượng ≈ 301,4 —
vượt xa sàn 150.

**Đọc hai kết quả CÙNG NHAU, không tách rời:** sàn 150 có vẻ giải quyết được nếu mở Short (dù còn
phải qua đủ ba điều kiện `DR-D4-01` §2b, và D4 hiện chỉ có giá trị cho LONG theo chính DR đó — mở
Short cho D4 là quyết định RIÊNG, không tự động theo sau việc "đủ mẫu"). Nhưng rào DSR cần `n`
lớn hơn nhiều so với những gì cửa sổ WFO 0,63 năm có thể cho dù tần suất/năm cao tới đâu, TRỪ KHI
tần suất đạt tới hàng nghìn lệnh/năm (bảng độ nhạy: ~950-1500 lệnh/năm mới đưa `mean_R` cần thiết
xuống mức khả thi ~0,16-0,23 ở `std_R`=1,25) — một bậc độ lớn khác hẳn câu hỏi "đạt sàn 150".
Ghi cho chủ dự án quyết: mở rộng cửa sổ WFO, hay chấp nhận D4 khó kết luận bằng thống kê cổ điển ở
quy mô dữ liệu hiện có, hay hướng khác — không tự chọn.

---

## 10/09/2026 — Ba chốt của TD-0184 là MỘT bất đẳng thức; và rào DSR bất biến theo thang đo

**Bối cảnh.** Chủ dự án yêu cầu phân tích tổng thể ba thứ đang chặn TD-0184 (số mẫu 63,6 lệnh/năm <
sàn 150; E3 không có đường chạy hợp lệ; `std(R_realized)` chưa ai đo) rồi đề xuất đường đi. Kết quả
dưới đây thuần toán trên công thức đã có + số đã đo, **0 trial, không chạm dữ liệu nào**.

### 1. Ba chốt không độc lập

`DSR_adj = mean_R − h·std_R/√n ≥ 0,10 R` (`gates/dsr.py:52-69`, `h = √(2·ln 114) = 3,0777`), với
`n = (lệnh/năm) × (số năm cửa sổ)`. "63,6 < 150" nói về **tử số của `n`**; "`std_R` chưa đo" nói về
**`std_R`**; "E3 không chạy được" là **điều kiện quan sát** cả hai. Ba biến của cùng một bất đẳng
thức — gỡ riêng một cái không kết luận được gì.

### 2. 🔑 Kết quả trung tâm — sàn Sharpe mỗi lệnh, BẤT BIẾN theo thang đo

Chia hai vế cho `std_R`, đặt `S = mean_R/std_R`:

```
S ≥ 0,10/std_R + h/√n
                 ╰────╯  SÀN KHÔNG THỂ HẠ, độc lập hoàn toàn với std_R
```

| n | lệnh/năm (WFO 0,63 năm) | Sàn `S` = h/√n |
|---|---|---|
| **40 (hiện tại)** | **63,6** | **0,487** |
| 95 | 150 (sàn §10.2) | 0,316 |
| 191 | 301 (nếu mở Short) | 0,223 |
| 545 | 301 + cửa sổ CALIB+WFO | 0,132 |

Vì sao đáng ghi: nó khiến `std_R` — thứ cả dự án đang chờ — thành **thứ yếu** cho câu hỏi *"có nên
tiêu 9 suất trial không"*. Dù `std_R` bằng bao nhiêu, ở n = 40 hệ thống phải đạt `S ≥ 0,487`.

⚠️ **Phát biểu phải kèm điều kiện, đừng rút gọn** (phiên `be` bắt được chỗ này khi tôi viết trần):
`S ≥ 0,10/std_R + h/√n` cho thấy `std_R` nhỏ làm `S` cần TĂNG — nhưng điều đó chỉ là một **cách sửa**
chứ không phải một sự thật phổ quát, và nó chỉ có hiệu lực khi `std_R` nhỏ **vì đơn vị R bị co**
(MT-25 vế i). Nếu `std_R` nhỏ vì phân tán thật sự chặt thì cách đọc cũ (giữ `mean_R` cố định) đúng.
Cả hai đều là phép chia đúng của cùng một bất đẳng thức; **phép chia không tự chọn hộ giả định nào
đúng** — cái chọn hộ là **cơ chế** (Z0 khớp 100% một tranche trong khi mẫu số dùng thang ba tranche).

### 3. Sàn 150 và rào DSR không được hiệu chỉnh theo nhau

Đạt đúng sàn 150 ⇒ n = 95 ⇒ thuế nhiễu `3,0777 × 1,25/√95 = 0,395 R` — **gấp 3,9 lần chính ngưỡng
0,10 R** mà nó phải bảo vệ. Để thuế nhiễu chỉ bằng ngưỡng cần **n ≥ 1.480 ≈ 2.340 lệnh/năm**. Sàn
150 vì thế không làm được việc mà chú thích của nó nói (*"ngưỡng tối thiểu để có đủ mẫu"*, spec dòng
4275). **Ghi nhận, KHÔNG đề nghị sửa số** — sửa một chốt vì nó đang chặn là đúng thứ `CLAUDE.md` cấm.

### 4. Nhánh 2 thiếu lực hơn Nhánh 1

`so_paired()` (`ket_cuc.py:183-211`) ở n_giao = 40: cổng hỏi *"vượt ≥ 20%"* nhưng chỉ phân biệt được
mức vượt **212% (ρ=0,95) → 405% (ρ=0,8)** khi `e_A = 0,10 R`. ⇒ **ở n = 40 CẢ HAI nhánh của GATE
D0.9 đều không phán quyết được**, suy ra được TRƯỚC khi tiêu suất trial nào. Chạy 9 arm bây giờ là
tiêu 7,9% ngân sách mua một kết cục đã biết.

### 5. Đòn bẩy: chỉ `√n`, và `N` KHÔNG phải đòn bẩy

Phễu đo được (TD-0193): bộ lọc trend một mình chiếm **×21,9** trong tổng ×79,3 lần thu hẹp từ zone
xuống lệnh; bên trong nó chốt cắt là **§2.1 hướng 1D** (2.103 → 400, cắt 81%).

Hạ `N` để nới rào **không dùng được**: `h = √(2·ln N)` quá trơ — N 114 → 30 chỉ hạ hurdle **15,3%**;
phải xuống N = 5 mới hạ 41,7%. Và động vào nó là nới chuẩn của chính mình (tiền lệ OQ-06).

### 6. Ưu thế Short 3,74× chủ yếu là chế độ thị trường — nhưng lý do ĐÚNG để mở Short là thứ khác

Ưu thế tầng tín hiệu `368,4/98,5 = 3,740`; tỉ lệ cơ hội `DOWN/UP = 1339/400 = 3,348` ⇒ phần cấu trúc
chỉ **×1,117**, trong sai số. Đọc *"Short tốt hơn Long"* là **sai**. Lý do đúng: Long-only treo `n`
vào **19,0%** cơ hội, Long+Short đưa lên **82,7%** (×4,35) và làm `n` **bớt phụ thuộc chế độ thị
trường** — lập luận về **độ vững của cỡ mẫu**, không phải về edge.

### 7. 🔴 `n = 40` bản thân nó là NGOẠI SUY, chưa ai đo

63,6 lệnh/năm đo trên **[T0,T2] = 1,81 năm** rồi nhân 0,632 năm để ra `n` trên **WFO [T1,T2]**. Cơ
hội Long treo vào tỉ lệ 1D = UP, mà tỉ lệ đó trên [T0,T2] là 19,0% — một cửa sổ 7 tháng lệch xa được
cả hai chiều. **Con số trung tâm chưa được đo trên chính cửa sổ nó sẽ được dùng**, và đo nó là việc
rẻ nhất trong toàn bộ danh sách ⇒ làm trước.

### 8. Ba mâu thuẫn đã ghi sổ

`MT-24` (trích dẫn bịa về ranh giới EXPLORE) · `MT-25` (đơn vị R của Z0 bị co ⇒ `DR-D4-09` §7 điều 1
không dùng được như đang viết) · `MT-26` (`DSR_adj` thiên lệch theo cỡ mẫu). Cả ba **chưa giải**,
chờ chủ dự án — commit `e9c928f`.

🔑 **Bài học phương pháp của phiên:** cả ba phát hiện đến từ việc **đọc lại nguồn được viện dẫn**
thay vì tin câu trích, và từ việc **viết một đại lượng dưới dạng bất biến** (Sharpe) thay vì so hai
số phụ thuộc thang. Cùng họ với bài học `TD-0082` đã ghi (*"một dòng mô tả việc cũng là lời khai,
không phải bằng chứng"*) — lần này lời khai đi qua **bốn** tài liệu trước khi có ai mở nguồn ra đọc.

---

## 10/09/2026 (tiếp) — TD-0205: `n` thật trên WFO là **28**, không phải 40. Bước 1a tự nó đóng câu hỏi.

**Việc.** `n = 40` là ngoại suy: 63,6 lệnh/năm đo trên [T0,T2] = 1,81 năm rồi nhân 0,632 năm.
Đo lại phễu + backtest **riêng trong cửa sổ WFO [T1,T2]** — cửa sổ ablation D4 thật sự chạy.
88 mã EXPLORE, **0 trial**, `docs/du-lieu-do/td0205-lenh-nam-wfo-explore.json`.

### Kết quả — thấp hơn ngoại suy 30%

| arm | lệnh/năm [T0,T2] | **lệnh/năm WFO** | tỉ lệ | **n trên WFO** | sàn `S` = h/√n |
|---|---|---|---|---|---|
| `Z0-T0` | 1.276,5 | **1.518,1** | ×1,19 | 960 | 0,099 |
| `Z0-T1` | 333,5 | **325,6** | ×0,98 | 206 | 0,214 |
| **`Z0`** | 63,6 | **44,8** | **×0,70** | **28** | **0,578** |

Z0 chỉ có **22 lệnh thật** trên toàn bộ 88 mã EXPLORE trong 7,6 tháng WFO.
Sàn Sharpe mỗi lệnh tăng từ 0,487 lên **0,578**.

### 🔑 Ba arm dịch chuyển KHÁC HƯỚNG — đó là bằng chứng CƠ CHẾ, không phải tương quan

`Z0-T0` (không lọc trend) **tăng** ×1,19; `Z0-T1` (chỉ lọc 4H) **đứng yên** ×0,98; `Z0` (đủ bộ lọc,
gồm §2.1 hướng 1D) **giảm** ×0,70. Đúng thứ tự phụ thuộc vào tầng 1D. Nguyên nhân đo được ở phễu
trend tại nến C:

| | WFO [T1,T2] | [T0,T2] |
|---|---|---|
| 1D = UP | **175 / 1.104 = 15,85%** | 400 / 2.103 = 19,02% |
| 1D = DOWN | 787 = 71,3% | 1.339 = 63,7% |

`z = −2,22` ⇒ **phân biệt được ở mức 95%**. WFO là một cửa sổ **nghịch chiều Long** hơn mức trung
bình — đúng thứ F4/MT ghi là rủi ro: Long-only treo `n` vào tỉ lệ UP.

⚠️ **Không phải hiện tượng thiếu dữ liệu, đã kiểm ngược:** độ phủ mã-năm của WFO là **90%**
(50,12 / 88 × 0,632) trong khi [T0,T2] chỉ **63%** (99,40 / 88 × 1,807). Độ phủ **cao hơn** mà số
lệnh/năm vẫn thấp hơn ⇒ sụt giảm là tính chất của cửa sổ, không phải của phép đo.

### Bất định — và vì sao kết luận vẫn vững

22 lệnh là số nhỏ, phải khai: CI95 Poisson cho `k = 22` là [12,8 · 31,2] lệnh ⇒ lệnh/năm
[26,1 · 63,5] ⇒ `n` ∈ [16 · 40] ⇒ sàn `S` ∈ [**0,486** · 0,758].

🔑 **Đầu LẠC QUAN NHẤT của khoảng tin cậy cho sàn `S` = 0,486 — đúng bằng con số ngoại suy cũ.**
Tức phép đo này **không thể** làm tình hình tốt hơn giả định cũ, chỉ có thể xấu đi. Kết luận
*"ở cỡ mẫu này GATE D0.9 không phán quyết được"* **vững trên toàn bộ khoảng**, không phụ thuộc
điểm ước lượng — và không phụ thuộc `std_R` (§2 của mục 10/09 trước: sàn `h/√n` bất biến theo thang).

⇒ **Bước 1a tự nó đóng câu hỏi. Không cần đo `std_R` để quyết "có tiêu 9 suất trial không".**
Câu trả lời là **KHÔNG**, và nó tốn 0 trial để có.

### MT-26 nặng thêm một bậc

Khoảng cách cỡ mẫu `Z0-T0 / Z0` là **34×** (đo trên [T0,T2] trước đây là 20×). Khi so `DSR_adj`
với cùng `mean_R` và `std_R = 1,25`, `Z0-T0` được cộng không **+0,599 R = 6,0 lần** chính ngưỡng
0,10 R (trước: +0,473 R = 4,7 lần). Xếp hạng arm theo `DSR_adj` thô càng chắc chắn cho arm **bỏ bộ
lọc trend** thắng — và cửa sổ WFO nghịch chiều Long làm điều đó tệ hơn chứ không nhẹ đi.

### Ghi chú kỷ luật

- Đường chạy cũ **không đổi một byte**: `--tu/--den/--ket-qua/--nguon/--ranh-gioi` đều mặc định
  giữ nguyên; verify trong Docker rằng `nguon`/`ranh_gioi`/`timerange` mặc định khớp đúng artifact
  `td0193-*.json` đã commit. Có chốt **từ chối chạy** nếu đổi cửa sổ mà quên `--ket-qua`.
- `ranh_gioi` mặc định **giữ nguyên chữ cũ** (mang trích dẫn sai của MT-24) để artifact TD-0193 còn
  tái lập được — sửa mặc định là tạo ra một lần *"không tự sinh lại được cái mình đã công bố"*.
  Thêm chú thích trỏ MT-24 + một dòng **cảnh báo không chặn** khi chạy với mặc định (gợi ý phiên
  `be`): hậu quả quên cờ chỉ là chuỗi mô tả sai, không đại lượng nào đổi, nên chặn cứng sẽ là chốt
  đắt hơn thứ nó bảo vệ.
- 📌 **Lỗi tự bắt, ghi để không lặp:** lượt chạy đầu dùng `2>&1 | tail -40` — đúng bẫy đã ghi sổ
  ngày 08/09 (*"giữ TRỌN output rồi mới lọc"*). Dừng sau ~1 phút, chạy lại ghi trọn ra file. Biết
  luật mà vẫn dính, vì nó nằm trong thói quen gõ lệnh chứ không nằm trong bước suy nghĩ.

---

## 10/09/2026 (tiếp) — TD-0206: H-4 = 100% là LỖI MÃ. Và một hình dạng lỗi MỚI: kiểm BÊN SINH không kiểm được ĐƯỜNG ĐI

**Câu hỏi.** `td0193`/`td0205` đo được **723/723 lần TP1 rơi nạng**, 0 lần chốt theo zone đối diện —
trong khi ngưỡng Nhánh 1 §10.2 là ≤ 40% và spec dòng 4285-4286 ghi *"> 40% → tiền đề TP sai (L2) →
KHÔNG vào live"*. Cấu trúc thị trường hay lỗi? Hai câu trả lời dẫn tới hai hành động trái ngược.

### Kết quả: LỖI MÃ, kiểm ở tầng CƠ CHẾ

Đo trên **đường sản xuất thật** (thêm log vào chính chiến lược, parse như khuôn `KET_NAP` — KHÔNG
tái lập logic, đúng bài học TD-0168). 88 mã EXPLORE, WFO, 22 lệnh, **0 trial**:

```
so_lan_goi_zone_dinh_tren    22            <- CÓ được gọi, 22/22
co_cot_zone_dinh_gia         {'False': 22} <- cột VẮNG MẶT 22/22
cot_thay_duoc_mau            date,open,high,low,close,volume
nguon_tp                     {'fallback_r_multiple': 22}
```

**Cơ chế:** `_df_4h()` gọi `dp.get_pair_dataframe()` → trả **OHLCV thô, đúng 6 cột**. Nhưng
`zone_dinh_gia` được tính ở `ZoneAbsorption.py:382` trên khung 4H rồi **merge vào 1H với hậu tố
`_4h`** (dòng 301) ⇒ tên thật là `zone_dinh_gia_4h` trên dataframe **đã phân tích**. Nên
`_zone_dinh_tren` rơi vào `return []` **100% số lần**, TP1 **luôn** dùng nạng.

**Bán kính — đúng hai hàm, và cả hai là đường TP-theo-zone:**

| hàm | đọc gì | trạng thái |
|---|---|---|
| `_close_4h_ke_tu` · `_trend_4h_hien_tai` · `_zss_hien_tai` | `close`/`high`/`low`/`volume`, tự tính lại | ✅ sống |
| `_zone_dinh_tren` | `zone_dinh_gia` | ❌ luôn trả `[]` |
| `_tuoi_zone_dinh_nen` | `zone_dinh_gia` | ❌ `tp_zone_age_bars` luôn `None` |

Mẫu hình nhất quán: hàm nào **tự tính lại từ OHLCV thô** thì sống; đúng hai hàm cố **đọc một cột do
`populate_indicators` sinh ra** thì chết.

### 🔑 HÌNH DẠNG LỖI THỨ NĂM — kiểm BÊN SINH không kiểm được ĐƯỜNG ĐI

Bốn cái đã ghi: *lớp canh cùn* · *chĩa nhầm hướng* · *người bị canh tự chọn phạm vi* · *bộ sinh dữ
liệu lỗi thời*. Cái mới khác cả bốn.

`td0189-diem-thoi-gian-zone-dinh-explore.py` kết luận (dòng 20-21) ***"`_quet_zone_dinh` HOẠT ĐỘNG
ĐÚNG — 4775 zone đỉnh confirmed"***. **Câu đó ĐÚNG.** `_quet_zone_dinh` thật sự chạy đúng và sinh ra
4.775 zone. Nhưng bên ĐỌC không nhìn thấy đầu ra của nó. **Kiểm bên SINH rồi kết luận cả đường đi
lành — đó là chỗ hở.** Một phép kiểm sắc, chĩa đúng hướng, chạy trên dữ liệu thật, và vẫn bỏ lọt,
vì nó dừng lại ở nửa đường ống.

Cùng họ với TD-0168 (*"thứ được canh không nằm trên đường chạy"*) nhưng ở chiều ngược: ở đây thứ
được canh **có** nằm trên đường chạy — chỉ là **khúc sau của đường ống thì không**.

### 🔑 Và một lập luận VÒNG TRÒN, do phiên `be` bắt

Cùng docstring, dòng 24-27: *"21/21 lệnh THẬT rơi nạng… là kết quả PLAUSIBLE, **không phải dấu hiệu
bug** — cùng chiều với DR-D4-06"*. Tức lấy **chính con số 100% quan sát trong sản xuất** làm bằng
chứng CỦNG CỐ rằng không có bug. Nay biết con số đó là **hệ quả cơ khí của bug** (`_zone_dinh_tren`
trả `[]` bất kể zone thật có sống hay không) ⇒ **dùng triệu chứng của bug làm bằng chứng bug không
tồn tại**. Phải đính chính: giữ 17,6%/35,9% (tự đo được, vẫn đúng), rút lại câu suy từ 21/21.

### ✅ `MT-20` và `DR-D4-06` KHÔNG bị lung lay — đã kiểm, không suy đoán

Lo ngại đầu của tôi là tiền đề của MT-20 (*"§1.3 và §5.1 không thể cùng đúng"*) dựa trên tỉ lệ nạng
sinh từ đường chết. **Sai.** `be` tra, tôi kiểm lại độc lập: `do_tuoi_zone_dinh_explore.py` và
`td0189-diem-thoi-gian-zone-dinh-explore.py` chỉ `import tool_d.zone_detection`/`zone_strength`
(hàm THUẦN) và `pd.read_feather()` trực tiếp — **không** import `ZoneAbsorption`, **không** gọi
`_df_4h`/`get_pair_dataframe`. Chúng **chép tay** vòng quét (dòng 39 tự khai). ⇒ con số 73-87% độc
lập với bug, **tiền đề của MT-20/DR-D4-06 đứng vững**.

📌 Trớ trêu đáng ghi: chính việc **chép tay logic** — thứ MT-03 cấm vì "hai bản sẽ trôi lệch" — lại
là lý do hai phép đo đó sống sót qua bug này. Không phải lý lẽ để nới MT-03; chỉ là ghi nhận rằng
độc lập-đường-đo có giá trị riêng của nó, khác với độc lập-nguồn-sự-thật.

### Ba hệ quả

1. **Nhánh 1 KHÔNG thật sự fail ở H-4.** 100% là defect, không phải bằng chứng chống. Suýt đọc thành
   phán quyết L2 *"không vào live"* trên một lỗi mã.
2. **Mọi arm đo tới giờ đo một hệ thống KHÔNG có tầng chốt lời theo zone** (`td0193`, `td0205`,
   `dg2-explore-quet-arm`). Chạy D4 lúc này là tiêu 9 suất mua số của một cỗ máy khác.
3. **`DR-D4-06` ràng buộc 1** (*"ghi `tp_zone_age_bars` mỗi lệnh"*) **chưa bao giờ thoả được** — một
   ràng buộc đã khai mà cấu trúc không cho phép đúng.

### Bản vá — CHƯA làm, có một câu ngữ nghĩa phải quyết trước

Vá thuộc **DR-012 Hạng 1** (mã không khớp spec) ⇒ 0 trial, không cần DR mới. Nhưng
`merge_informative_pair(..., ffill=True)` **kéo dài** giá zone gần nhất qua các nến sau, nên
`notna()` trên `zone_dinh_gia_4h` cho **giá trị LẶP**, khác hẳn *"tập các zone đã xác nhận"* mà
`_zone_dinh_tren` định lấy. Đổi tên cột mà không xử ffill là **đổi im lặng ý nghĩa của TP1** — đúng
lớp `L-Z48c`. Và vá xong **đổi mọi con số D4 đã đo** ⇒ phải ghi như `DR-D4-08` §8.

---

## 10/09/2026 — Sự cố commit chéo thứ NĂM, và lần đầu ở chiều N12 đã tự khai là không chặn được

**Sự việc.** Phiên `c0` sửa dòng `TD-0211` trong `TASKS.md` (mở rộng 1917 → 3774 ký tự: đổi 🔒→✅,
gắn ô Xác nhận, đính chính một con số sai của chính mình). Trước khi `c0` kịp commit, phiên `c3`
chèn dòng `TD-0212` vào cùng file rồi chạy `git commit -- TASKS.md`. Commit `2992482` mang nhãn
*"khoá TD-0212"* nhưng chứa **cả hai** thay đổi. `c0` sau đó chạy `git commit` thì nhận
*"nothing added to commit"*.

**Thiệt hại: KHÔNG CÓ.** Nội dung `TD-0211` vào lịch sử nguyên vẹn (kiểm 8 chuỗi mốc: `✅`,
`Xác nhận`, `ff87475`, `n ≈ 162`, `λ < 0,138`, `18,2%`, `MT-29`, `§2.4`). Chỉ **xuất xứ** sai: phần
hoàn tất `TD-0211` nằm dưới nhãn commit của một việc khác. Không viết lại lịch sử — tiền lệ
`4ec0fd3`: ghi nhận, gắn đính chính, giữ nguyên chữ cũ.

**Cả hai phiên phát hiện độc lập, gần như đồng thời, và chẩn đoán trùng khớp.** Đã thoả thuận
trước khi ghi: `c0` viết mục này, `c3` không viết — tránh tái diễn `DR-D4-06` (hai file cho một
sự việc).

### Ba điều mới so với bốn sự cố trước

**1. Lần đầu ở chiều mà N12 mục 5 đã TỰ KHAI là không chặn được.** Bảng trong N12 ghi hai chiều:
*"mình gây hại cho phiên khác"* → ✅ chặn được; *"mình bị phiên khác cuốn đi"* → ❌ không. Bốn sự cố
trước (`4ec0fd3` và họ hàng) đều là chiều thứ nhất. Đây là chiều thứ hai — **ứng nghiệm đúng một
dự đoán viết sẵn**. Một quy tắc dự báo đúng thất bại của chính nó thì phần dự báo đó **không cần
sửa**; nó cần được ghi là đã xảy ra, để lần sau không ai coi đó là lý thuyết.

**2. 🔑 Nhưng cơ chế là một đường THỨ BA mà N12 chưa mô tả — và nó thủng cả cái khoá N12 đề nghị.**
N12 mô tả chiều thứ hai là *"file mình vừa `git add` bị họ cuốn đi"*, tức qua **index dùng chung**,
và đề nghị đóng bằng `GIT_INDEX_FILE` riêng hoặc worktree riêng. Lần này **không ai `add` gì cả**:
`c3` dùng pathspec, mà `git commit -- <path>` lấy thẳng **working tree** của path đó, bỏ qua index.
⇒ Cơ chế là **working tree dùng chung**, không phải index dùng chung.
🔴 Hệ quả thực tế: **`GIT_INDEX_FILE` riêng KHÔNG đóng được đường này.** Chỉ worktree riêng mới
đóng. Chủ dự án đã cố ý chọn không dùng worktree, nên đây là rủi ro tồn dư **có ý thức** — ghi ra
để không ai tưởng `GIT_INDEX_FILE` là đủ.

**3. Nguyên nhân trực tiếp: cả hai phiên đều thay "đọc diff" bằng "đọc TÓM TẮT diff".**
`c3` xem `--numstat`, thấy `2 1` (thêm 2 xoá 1, thay vì `1 0` như chủ định) và vẫn commit vì lệnh
`diff` và `commit` gộp chung nên không kịp đọc. `c0` thì chạy `git diff -U0 -- TASKS.md | grep "^@@"`
để xem **phạm vi hunk** — cũng là thống kê, không phải nội dung. N12 mục 1 đòi *"đọc lại TOÀN BỘ
diff"*; cả hai đều đọc một đại lượng **dẫn xuất** từ diff rồi tưởng đã làm đúng. Cùng lớp lỗi với
*"đo tính chất NGỮ NGHĨA bằng dấu hiệu CÚ PHÁP"* (08/09) và *"sai ở NHÃN dán lên phép đo"* (09/09).

### Đề xuất — vì "đọc hết diff" là một chốt không thoả được

`TASKS.md` dài hơn 400 dòng, mỗi dòng việc dài hàng nghìn ký tự. *"Đọc hết diff"* nghe đúng nhưng
không ai làm thật — đúng dạng **chốt không bao giờ thoả được** mà cổng D3 đã trả giá, và chốt loại
đó sớm muộn bị bỏ qua trong im lặng.

Thay bằng một phép so **hẹp và máy kiểm được**: trước khi commit một file trạng thái dùng chung,
lọc diff xuống **đúng những mã việc mình chủ định đụng** rồi đối chiếu danh sách đó —
`git diff -- TASKS.md | grep -oE "^[-+]\| TD-[0-9]{4}" | sort -u`. Ra đúng tập mã mình định sửa
thì commit; ra thêm mã lạ thì dừng. Rẻ, đọc được trong hai giây, và bắt được **cả hai** sự cố đã
xảy ra (`4ec0fd3` nuốt file lạ, `2992482` nuốt dòng lạ).

⚠️ Cách `c3` tự chốt (tách `diff` và `commit` thành hai lệnh) đúng hướng nhưng **không đủ**: cửa sổ
giữa hai lệnh chính là chỗ phiên kia ghi vào. Nó thu hẹp, không đóng.

---

## 12/09/2026 — Một khẳng định SAI về mã đi qua tin nhắn giữa hai phiên, và chỉ bị bắt vì nó được viết vào FILE

**Bối cảnh:** chủ dự án chốt Tool D sẽ dùng FreqAI (ngược §0c.2 + N3, đã mở Khối 17 —
`TD-0216…TD-0225`). Trong lúc chia việc, phiên `[3f7d14]` nhắn cho phiên `[f5177d]` một câu mô tả
hệ thống sau khi `DR-D4-10 §2.4` chốt `Z0` single-entry:

> *"giả định đúng từ nay là `Z0` single-entry — không có tranche 2/3, `adjust_trade_position`
> không còn trên đường chạy sản xuất."*

Vế cuối **SAI**. `ZoneAbsorption.py:886-887` gọi `_xet_tp1()` **TRƯỚC** chốt arm ở `:891`, nên
`arm = Z0` chỉ tắt **nhánh bơm tranche**; callback đó vẫn là đường **TP1 chốt 50%**
(`stake_amount` âm ⇒ `ExitType.PARTIAL_EXIT`). `[f5177d]` chép nguyên khẳng định đó vào đầu Khối 17,
trong phần *"đọc trước khi viết `DR-FAI-01` §phạm vi"*. Đã sửa ở `e668c8c` (đính chính tại chỗ,
giữ chữ cũ).

### Hai lỗi khác nhau, không gộp thành một

| Phiên | Lỗi | Họ hàng |
|---|---|---|
| `[3f7d14]` | **Khẳng định về mã mà chưa mở mã** — và người nhận tin không có cách nào biết điều đó | `TD-0082`, ở chiều **người khai** |
| `[f5177d]` | Nhận một câu trong hội thoại làm **tiền đề đã kiểm chứng**, rồi ghi vào file đặc tả | `TD-0082`, ở chiều **người tin lời khai** |

🔴 Đừng rút gọn thành *"phiên nhận suy rộng quá tay"* — nó **không** suy rộng, nó chép đúng. Cũng
đừng rút gọn thành *"phiên khai ẩu"* rồi coi phiên nhận là nạn nhân: ghi một câu của người khác vào
file đặc tả **dưới tên mình** là hành động nhận trách nhiệm về câu đó.

### 🔑 Điều đáng giữ nhất — cơ chế cứu được lần này KHÔNG phải kỷ luật tự kiểm

`[3f7d14]` phát hiện ra mình sai **không phải** khi rà lại câu của mình, mà khi đi **kiểm câu của
người khác**: họ mở `ZoneAbsorption.py` để xác minh ghi chú `[f5177d]` vừa thêm vào Khối 17, rồi
mới thấy nhánh TP1.

⇒ **Tin nhắn giữa hai phiên không bị soi; chỉ FILE mới bị soi.** Một câu sai sống trong hội thoại
thì không lớp canh nào của dự án nhìn thấy — không diff, không test, không review. Cùng câu đó vừa
rơi vào một file là lập tức có người đọc. Lần này ta **may** vì câu sai đi qua một file trước khi
đi vào một DR.

**Hệ quả thực hành (không phải quy tắc mới, chỉ là cách đọc lại quy tắc cũ):** khi một phiên khác
mô tả *hành vi của mã* và mô tả đó sắp thành tiền đề cho một quyết định, **mở file trước khi ghi**,
không phải sau khi bị bác. Chi phí ở đây là một lệnh `sed -n`; giá của việc bỏ qua là một tiền đề
sai nằm trong `DR-FAI-01` §phạm vi — và nếu ai đó vì tin nó mà bọc/bỏ `adjust_trade_position` thì
**TP1 chết IM LẶNG** (Freqtrade hạ exception của callback thành WARNING rồi đi tiếp với `rc = 0` —
`MT-16 (vii)`: *"một chốt fail-closed bị nuốt là một chốt KHÔNG TỒN TẠI"*).

⚠️ **Giới hạn của kết luận:** đây là *"đã thấy một ca"*, không phải *"đã đo tần suất"*. Không ai
đếm được có bao nhiêu khẳng định khác đã đi qua kênh tin nhắn giữa các phiên mà không rơi vào file
nào — theo định nghĩa, những cái đó không để lại dấu vết để đếm.

🔴 **Cập nhật cuối ngày 12/09 — giới hạn ngay trên đã bị chính ngày hôm đó vượt qua: BỐN ca, BA phiên.**
(1) `[3f7d14]` khẳng định `adjust_trade_position` rời đường chạy sản xuất — chưa mở `ZoneAbsorption.py`;
(2) `[f5177d]` chép khẳng định đó vào `TASKS.md` như tiền đề đã kiểm chứng; (3) `[3f7d14]` đề nghị phép
kiểm `grep -c "......"` mô tả như thể đã chạy — chạy thử thì nó **tự khớp với chính dòng lệnh của nó**,
không bao giờ về 0; (4) `[67bb21]` nhắn *"tôi nghĩ bạn chưa thấy dòng cuối §0c.2"* về một bản nháp mà
`§1` đang **trích nguyên văn** chính dòng đó — chưa mở file.

⇒ Vẫn **không** đo được tần suất thật (ca không rơi vào file thì không đếm được), nhưng **cận dưới
bốn ca một ngày** đủ để bỏ cách đọc *"chuyện hiếm"*. Không ca nào là cẩu thả; cả bốn đều xảy ra khi
**trao đổi nhanh bằng tin nhắn về một file không ai đang mở**.

🔑 **Biến thể nguy nhất là ca (4), và `[67bb21]` tự nêu ra nó:** bọc một khẳng định trong *"tôi nghĩ
bạn chưa thấy…"* biến nó từ phát biểu về **VĂN BẢN** thành phỏng đoán về **NGƯỜI**. Phát biểu về văn
bản thì mở file là bác được trong hai giây; phỏng đoán về người thì người nhận phải **tự chứng minh
mình đã đọc** — tốn hơn, và dễ khiến họ nhận bừa cho xong. Cùng họ *"chốt bị nới vì một lý do nghe
hợp lý"*: thứ khó cãi lại không phải thứ sai nhất, mà là thứ đắt nhất để cãi.

### 🔑 Cơ chế thứ hai, tách riêng vì nó KHÁC: mất thông tin ở lớp DIỄN ĐẠT

Cùng ngày, cùng phiên `[67bb21]`, một ca thứ hai **không cùng cơ chế với bốn ca trên**. Họ định
thuật lại cho chủ dự án: *"cả hai đường đều đang bị chặn — A bị §0c.2 bác, B bị `HAN_NGACH_CHON: 0`"*.
Hai vế **không cùng hạng**: A có một **CÁI GIÁ** (đi được ngay, nhưng phải đè `DR-D0PRE-02` hoặc khai
DSR không áp dụng — `DR-FAI-01 §7.3.5`), B có một **CƠ CHẾ CHẶN** (`DR-Q3-2026:108` — quý khai `0` mà
có dòng `SELECTED` ⇒ sổ bẩn). Nén hai hạng đó vào một chữ *"bị chặn"* biến câu hỏi ***"đè lên chốt
nào"*** thành ***"dừng hay không"*** — với người đang quyết, hai câu đó dẫn tới hai hành động khác hẳn.

**Vì sao tách khỏi bốn ca trên:** bốn ca kia mất thông tin ở lớp **ĐO** (chưa mở file). Ca này **đo
đúng, suy đúng**, rồi mất thông tin ở lớp **DIỄN ĐẠT** — lúc tóm tắt. Không phép kiểm nào của dự án
nhìn thấy loại này: nó không sai một dữ kiện nào, và **câu đọc lên vẫn trôi**. Cùng họ với *"sai ở
NHÃN dán lên phép đo"* (09/09, sáu lần trong một buổi).

### 🔑 Cơ chế thứ BA, và là cái khó bắt nhất: mọi MẢNH đều đúng, chỉ PHẠM VI kết luận sai

Ca thứ năm của ngày, do `[f5177d]` gây ra và `[3f7d14]` bắt. Câu lọt vào `DR-FAI-01 §3`:
*"D4 Long-only **không chạy**, 0 suất trial tiêu"*, suy từ `44,8 lệnh/năm < sàn 150` của `MT-29`.

Kiểm `td0212-ba-arm-sau-va.json`: `Z0` = **44,8** (trượt) · `Z0-T1` = **325,6** (vượt) ·
`Z0-T0` = **1.396,0** (vượt). ⇒ `44,8` là số của **MỘT arm**, không phải của D4. Câu đó đúng với
**7/9 arm**, sai với hai arm Phần 2 — và nó **ngầm trả lời** câu 1 của `MT-26` khi `MT-26` đang
ghi CHƯA GIẢI.

**Vì sao tách khỏi hai cơ chế trên — và vì sao nó khó bắt nhất:** `MT-29` **tồn tại thật**, trích
dẫn **đúng**, con số `44,8` **đúng**, phép trừ `44,8 < 150` **đúng**. **Mọi mảnh đều kiểm được, và
không mảnh nào sai.** Chỉ **phạm vi** của kết luận là sai. Hai cơ chế trên còn có một thứ sai để
mà tìm (một file chưa mở, một chữ nén hai hạng); cái này **không có gì sai để thấy** — chỉ có một
lượng tử hoá thầm lặng từ *"arm này"* sang *"D4"*.

🔴 **Câu chẩn đoán rút ra, dùng được ngay:** ***một dẫn chiếu có thật KHÔNG chứng minh phần suy ra
từ nó.*** Kiểm được `MT-29` có thật ≠ kiểm được *"nên D4 không chạy"*. Hôm đó `[f5177d]` kiểm
`back-end-note.md:118`, thấy đúng, rồi nhận cả hệ quả — **kiểm một nửa rồi tin cả câu**.

⚠️ Và một điều `[3f7d14]` nói lại cho công bằng, giữ vì nó chặn cách đọc sai: đây **không** phải
lỗi *nặng hơn* ca `adjust_trade_position`, nó là lỗi **cùng loại** — ở ca kia `[3f7d14]` là **nguồn**
của câu sai, ở ca này nguồn là `[67bb21]`. Ba phiên, cùng một họ, không ai cẩu thả.

### 🔑 Vế đối, và là loại lỗi mà VÒNG ĐỌC CHÉO KHÔNG cứu được

Cả ngày 12/09 có một câu được ghi đi ghi lại: *"một quy tắc mình vừa phát biểu không tự động trở
thành một quy tắc mình đang tuân thủ"*. `[3f7d14]` thêm **vế đối**, và nó nguy hơn:

> ***Một quyết định đúng không tự động chứng minh lý do dẫn tới nó là đúng.***

**Vì sao vế đối nguy hơn vế gốc:** vế gốc còn **bị người khác bắt được** — bốn ca hôm nay đều do
phiên khác bắt. Vế đối thì **KHÔNG AI BẮT**, vì kết quả đúng nên chẳng ai đi soi lý do. Nó chỉ
hiện ra khi **chính mình tự tách hai thứ**. ⇒ Đây là loại lỗi mà lớp bảo vệ mạnh nhất của ngày
hôm nay — đọc chéo giữa các phiên — **không chạm tới được**.

**Ca duy nhất thuộc loại đó hôm nay:** `[f5177d]` từ chối chạy một phép đo vì *provenance* (lời
thuật không kiểm được). Việc từ chối **đúng** — nhưng đúng vì `§4(b)` **phụ thuộc `§6`**, một
ràng buộc mà lý do provenance **không hề nhìn thấy**; một lệnh `grep` mới tìm ra. Nếu lời thuật
kia chính xác 100% thì lý do provenance vẫn không tìm ra cái chặn thật.

🔴 **Hậu quả nếu không tự tách:** ca đó sẽ vào sổ thành *"kỷ luật provenance đã cứu một bàn"* —
một **bài học SAI rút từ một kết quả ĐÚNG**, và bài học sai đó sẽ được dẫn lại ở ca tiếp theo
**nơi provenance không phải vấn đề**. Đó là cách một trực giác *"đã được việc một lần"* thay chỗ
cho một phép kiểm.

📌 **Một biến thể nhỏ của cùng hiện tượng, cùng ngày, cùng phiên:** `[f5177d]` nhắn rằng sẽ ghi
mục `research-log` này *"khi tới lượt có lệnh chuẩn hóa và lưu"* — trong khi **N9 liệt đúng ba
file** (`back-end-note.md` / `ARCHITECTURE.md` / `tu-dien-du-lieu.md`) và `research-log.md`
**không nằm trong đó**; N10 còn đi hướng ngược lại (*"bắt buộc ghi mỗi lần chẩn đoán"*). Đối
chứng: chính phiên đó đã commit **năm** mục log trong ngày mà **không** có lệnh nào. ⇒ **Hành
động đúng, phát biểu quy tắc sai** — và cái sai đó chỉ lộ ra khi có người đọc lại chính văn bản
quy tắc. Hình dạng y hệt vế đối: kết quả đúng che mất lý do sai.

🔴 Chỗ đắt nhất: `[67bb21]` **tự dạy chính sự phân biệt đó** cho phiên khác ở tin nhắn ngay trước
(*"câu hỏi là FreqAI vào theo TƯ CÁCH NÀO, không phải CÓ HAY KHÔNG"*), rồi tự xoá nó khi tóm tắt —
vì trong một bản tóm tắt thì *"bị chặn"* **gọn hơn** *"đi được nhưng phải trả giá X"*. ⇒ **Chi phí
của việc rút gọn rơi đúng vào chỗ người đọc cần phân biệt nhất.** Rút gọn không phải thao tác trung
tính: nó bỏ đi **sự phân biệt**, và giữ lại **kết luận** — mà kết luận thì lúc nào cũng đọc trôi hơn.

**Và khoảng hở này không vá được bằng một test** (bổ sung của `[3f7d14]`, nhận): nó không phải một
lỗi trong mã, nó là **tính chất của việc hai phiên nói chuyện với nhau**. Thứ duy nhất thu hẹp được
là kỷ luật *"mở file trước khi khẳng định về mã"* — và chi tiết sắc nhất của cả ca này là
`[3f7d14]` vi phạm đúng kỷ luật đó **trong cùng buổi họ đang dạy lại nó cho một phiên khác**. Một
quy tắc mình vừa phát biểu không tự động trở thành một quy tắc mình đang tuân thủ.

---

## 12/09/2026 (tiếp) — TD-0230: pool mà D4 sắp backtest là ảnh chụp HÔM NAY. Và hai bài học về *phạm vi* của một khẳng định.

### 1. Phát hiện: `MT-08` ở lần thứ hai, tại một chỗ đắt hơn nhiều

Đi tìm câu trả lời cho ba việc chủ dự án hỏi (đổi ảnh Docker · chạy D4 cho `Z0-T1` · FreqAI), rà
soát bắt được một thứ **không nằm trong cả ba**:

| Khẳng định | Bằng chứng, tự kiểm trên đĩa |
|---|---|
| `delisted_at` chưa bao giờ được điền ngoài test | `grep -rn "delisted_at" --include=*.py` → **đúng 5 kết quả**: `src/tool_d/pool.py:32` (khai báo), `:115` (dùng), **3 chỗ còn lại đều trong `tests/unit/test_pool.py`** |
| Bộ sinh `SymbolStat` DUY NHẤT chỉ đọc hiện tại | `pool.py:41 build_symbol_stats()` lọc `status == "TRADING"` + `quote_volume_24h` từ ticker **24h hiện tại** ⇒ `delisted_at` luôn `None` |
| `config/pool.yaml` không phải point-in-time | `entrypoints/build_pool.py:226` gọi `compute_pool()`; docstring `:3-7` của chính file đó tự khai *"H1-D ĐẦY ĐỦ … là việc RIÊNG của D1 — **CHƯA viết ở đây**"* |
| Không có việc nào mở để viết phần đó | Khối 10 `TASKS.md:146-156` = **đúng ba dòng** TD-0095/0096/0097, **cả ba ✅**, và cả ba chỉ là **hàm thuần + test dựng tay** |
| Một quyết định đã chốt đòi ngược lại | `DR-D1-01` §3 (`:51`): *"**Không mở DR chấp nhận survivorship bias.** TD-0096 phải nạp thêm 219 symbol này … vào tập ứng viên khi tính pool tại mốc `t` lùi về quá khứ"* |

⇒ `pool.yaml` (102 mã, tiêu chí đo tại **09/2026**) sắp được dùng để backtest **[T0,T2] = 04/2024 →
01/2026**. Hai chiều lệch, **cả hai cùng chiều "trông đẹp hơn thật"**: mã đã chết bị loại khỏi rổ
(219 mã, `DR-D1-01` §1 đo thật) và mã chưa sinh vẫn nằm trong rổ (`listing_age_days_min: 180` đo
tại lúc chốt, nên một mã lên sàn 01/2026 vẫn "đủ tuổi" vào 09/2026 dù không tồn tại suốt CALIB).

🔑 **Đây là `MT-08` ở lần thứ hai — cùng hình dạng, khác chỗ, và chỗ này đắt hơn:** một chính sách
đã chốt mà phần thi hành **chưa bao giờ tồn tại**, trong khi dòng việc mang nhãn ✅. `N12` mục 3
(*"đừng tin chữ ✅ khi nó là điều kiện phụ thuộc"*) viết ra đúng cho ca này — và lần này ✅ **không
sai**: TD-0096 thật sự đã viết `pairlist_point_in_time()` và thật sự có test. Thứ sai là **phạm vi**
của cái ✅ đó: nó chứng nhận một **hàm**, và bị đọc thành chứng nhận một **năng lực**.

🔴 **Vì sao nó đứng TRƯỚC câu ảnh Docker** — câu mà chủ dự án đang hỏi: ảnh Docker quyết định *con số
có tái lập được hay không*; pool quyết định *con số có ĐÚNG hay không*. Và chiều lệch của pool là
**chiều PASS** — loại lệch mà không cổng nào tự bắt được. Cộng với spec `:4338` (*"mỗi lần đổi pool
= backfill lại toàn bộ, **MỌI số cũ không so sánh được**"*), nó là món **đắt lên theo thời gian**:
sửa trước khi tiêu `B2` thì rẻ, sau thì mất cả suất trial lẫn kết luận.

### 2. Phát hiện thứ hai: khoá `arm` là MỘT chuỗi nhưng gộp HAI trục

Đo trên `td0212-ba-arm-sau-va.json`, cả ba đều single-entry (`phan_bo_tranche` 100% tranche 1):

| arm | tầng trend | lệnh (88 mã, WFO) | quy đổi pool 102 /năm | sàn 150 mỗi hướng (`MT-29`) |
|---|---|---|---|---|
| `Z0-T0` | `KHONG` | 686 | 1.396,0 | ✅ nhưng là arm **chẩn đoán** |
| `Z0-T1` | `CHI_4H` | 160 | **325,6** | ✅ **ứng viên duy nhất** |
| `Z0` | `DAY_DU` | 22 | **44,8** | ❌ dưới sàn; `Z0 ⊆ Z0-T1` tuyệt đối |

`DR-D4-10` §2.4 chốt **trục DCA** (`Z0` thay `Z3`). **Không chốt nào nói trục TREND của arm sản
xuất.** Nên `TD-0227` đặt `arm: "Z0"` sẽ cho production chạy tiền thật ở cấu hình mà `MT-29` đã chốt
là **không thể qua sàn**, trong khi thứ D4 phán quyết là `Z0-T1`. Ghi nhận theo quy tắc 11, chủ dự
án chốt **treo `TD-0227`**, không tự chọn bên.

### 3. Bài học đo lường: một phép kiểm-có-răng cho ra 3 đỏ ở chỗ tôi dự 2

`TD-0230` cần một hàm liệt kê S3. Phá thật bốn lần trong Docker, khôi phục `diff -q` giống
byte-đối-byte mỗi lần:

| Phá | Dự | Thật |
|---|---|---|
| bỏ phân trang | 2 đỏ | **3 đỏ** |
| cắt im lặng ở trần trang | 1 đỏ | 1 đỏ ✅ |
| lỗi mạng trả rỗng thay vì raise | 1 đỏ | 1 đỏ ✅ |
| `iter("Prefix")` hút cả thẻ cấp gốc | — | 4 đỏ |

Ca thứ ba của phép phá đầu (`test_qua_TRAN_TRANG`) đỏ vì **trần trang chỉ có nghĩa khi phân trang
tồn tại** — bỏ phân trang thì không bao giờ chạm trần. Dự đoán thiếu một ca là chuyện nhỏ; điều
đáng ghi là **nó đi đúng chiều an toàn**: phép phá bắt được NHIỀU hơn dự, không phải ít hơn. Con số
đáng lo là chiều ngược lại.

📌 **Và phép đo tự xác nhận rằng phân trang không phải lo xa:** lượt liệt kê gốc trả **1018 thư mục
qua 2 trang**. Mỗi trang giới hạn 1000 — dừng ở trang đầu là mất 18 mã **trong im lặng**, đúng
chiều "rổ thiếu ít hơn thực tế". `DR-D1-01` §1 đã nêu đúng chỗ này bằng chữ; nay có một phép kiểm
canh nó. Đối chứng độc lập: `exchangeInfo` trả **658** mã perpetual/USDT — **khớp đúng con số 658
của `DR-D1-01` §1** đo cách đây 5 ngày.

### 4. 🔴 Đính chính phạm vi của chính `TD-0229` (hôm qua) — và nó do phiên khác nêu ra

Phiên `[f5177d]` chỉ ra một đường mà khung lựa chọn *"giữ digest HOẶC đổi sang `_freqai`"* của tôi
**không có**: ảnh ta chạy là ảnh **DẪN XUẤT** (`FROM …@sha256:7031bca4…` rồi `pip install --user`),
nên thêm `datasieve` + `lightgbm` vào **chính bước pip đó** giữ nguyên base digest. Họ đã đo bằng
`pip install --dry-run` trong container: **đúng hai gói được cài, không gói nào bị nâng cấp.**

Điều đó buộc tôi đọc lại chính hàm mình viết hôm qua. `doc_runtime_image_digest()` đọc dòng
`FROM …@sha256:` của `docker/Dockerfile` ⇒ nó ghi **digest ẢNH GỐC**, không ghi nội dung các lớp
dẫn xuất. Phát biểu chính xác, ba mức — không phải một:

| Thay đổi | Có bị bắt? | Bắt bởi cái gì |
|---|---|---|
| đổi dòng `FROM` (base digest) | ✅ | **cả hai**: `git_sha` và `runtime_image_digest` |
| thêm gói pip vào Dockerfile, **đã commit** | ✅ | **`git_sha`** — Dockerfile nằm trong git, và `cache_key` gộp `git_sha` |
| dựng lại ảnh từ Dockerfile **sửa mà chưa commit**, hoặc `pip install` ngay trong container đang chạy | ❌ | **không gì cả** — không đầu vào nào của `cache_key` đổi |

⇒ Câu tôi nói hôm qua (*"đổi ảnh Docker nay không còn im lặng"*) **đúng cho hai dòng đầu**, và dòng
thứ ba là một khoảng hở còn nguyên. Khoảng hở đó **không phải do khoá thứ 8 yếu** — nó là hệ quả của
việc mọi thứ canh môi trường đều canh **mô tả của ảnh** (Dockerfile trong git), chứ không canh **ảnh
đang chạy**. Muốn đóng thì phải ghi digest của ảnh DẪN XUẤT lúc chạy, và `docker history` trên ảnh
đó đã được thử và **thất bại** (`DR-FAI-01` §4b điều 5: `Dockerfile*` không có trong ảnh vì cài
editable; `docker history` trả `No such image`).

🔑 **Bài học, và nó KHÁC bài học của `MT-08` ở mục 1 dù nghe giống:** ở mục 1, một cái ✅ chứng nhận
một *hàm* bị đọc thành chứng nhận một *năng lực*. Ở đây, một *phép vá có thật, đã kiểm-có-răng ba
lần* bị **chính tác giả** phát biểu rộng hơn phạm vi nó phủ. Cả hai là lỗi **PHẠM VI**, không phải
lỗi nội dung — và không lớp canh nào của dự án nhìn thấy loại này, vì mọi phép kiểm đều kiểm *mã*,
không kiểm *câu nói về mã*. Đây là lần thứ hai trong hai ngày liên tiếp (`12/09` mục trước: một
khẳng định sai về mã đi qua tin nhắn giữa hai phiên).

📌 Và một chi tiết đáng giữ về **cách** nó bị bắt: lý lẽ tôi thuật cho quyết định *"giữ digest"* —
*"ảnh `_freqai` có thể khác cả pandas/numpy/ta-lib"* — là **điều 2 của `DR-FAI-01` §4b**, và nó
**đúng**. Nhưng nó chỉ bác **một** phương án. Một lý lẽ đúng bác đúng thứ nó nhắm tới; nếu khung
lựa chọn chỉ có hai ô thì nó **trông như** đã bác cả hai. Chi phí của việc dựng khung hẹp rơi vào
chỗ không ai kiểm: **phương án không được đặt lên bàn**.

⚠️ Quyết định *"giữ nguyên digest"* của chủ dự án **không đổi** vì đường thứ ba: lý do họ chuẩn y là
spec `:472-473` (*"Muốn thử ML → giả thuyết riêng, **ngân sách riêng, lockbox riêng**"*) — một lý do
về **quản trị**, không về hạ tầng. Đường thứ ba giải bài toán *kỹ thuật* (ảnh chạy được FreqAI)
nhưng không giải bài toán *quản trị* (ML không đi trên đường sản xuất của Tool D). Hai câu khác
nhau, và chỉ câu thứ hai được hỏi.

---

## 13/09/2026 — Phủ sóng theo DỮ LIỆU, không theo số phép kiểm. Và bốn lỗi của chính phiên này.

### 1. `MT-36` — câu thứ tư, chưa ai đặt, và nó đứng trước ba câu đang treo

Đi trả lời ba câu chủ dự án hỏi (`MT-34` · `MT-35` · FreqAI), rà soát bắt được một câu **không nằm
trong cả ba**: `n = 206` mà `DR-D4-10` §2.1 dẫn **không phải một số lệnh quan sát được**. Nó là **160
lệnh trên 88 mã EXPLORE** → quy đổi 88→102 → annualize trên **toàn** `[T1,T2]`. Tái lập đúng:
`325,6 × 231/365,25 = 205,9`, và cùng công thức cho `Z0` = 28, `Z0-T0` = 883.

Mà `folds.py:174-185` (neo gốc) cho ba cửa sổ **test** = `2025-09-04→10-23`, `10-23→12-11`,
`12-11→2026-01-29` — đoạn **84 ngày đầu là train-only ở CẢ BA fold**, tức test chỉ phủ **147/231 ngày**.

| Phán quyết trên | `n` | `h/√n` | Rào `mean_R` (std 1,25) |
|---|---|---|---|
| Toàn cửa sổ | 206 | 0,2144 | 0,368 |
| Chỉ test | ~131 | 0,2689 | **0,436** |

🔴 **Và không gì buộc chọn vế nào:** `dsr.py:52` nhận `n_trades: int` với ràng buộc **duy nhất**
`>= 2`; `chay_wfo`/`sinh_folds` **không có người gọi nào** từ `run_ablation.py`. ⇒ `TD-0184` sẽ quyết
câu này **bằng cách vô tình**, và **không phép kiểm nào của dự án nhìn thấy loại lỗi đó**.

Chốt (chủ dự án, 13/09): báo **cả hai**, phán quyết trên test-only. Và nó đã có **máy** ngay
(`TD-0232`) thay vì một câu trong DR — vì `MT-08` đã dạy hai lần rằng một chính sách không có máy thì
sẽ có người phải vá sau.

### 2. 🔴 Lỗi của phiên này: phép kiểm ĐÚNG, áp SAI CHỖ

Dòng `TD-0229` trong `TASKS.md` — **tôi viết hôm qua** — có **6 ô** trong khi header bảng có **5 cột**.
Markdown bỏ ô vượt, nên toàn bộ khối *"Xác nhận `5b34e1b`: full suite 1673 passed…"* (**2029 ký tự**,
gồm cả ba phép kiểm-có-răng) **vô hình khi render**. Nội dung vẫn nguyên trong file; chỉ mất ở bản
render.

🔑 Chi tiết đáng giữ: **cùng ngày hôm nay tôi ĐÃ chạy phép đếm dấu `|` cấu trúc cho
`back-end-note.md`** (34/34 dòng đúng) rồi commit — nhưng **không** chạy nó trên dòng `TASKS.md` mình
vừa viết. Phép kiểm đúng, áp sai chỗ. Và nó là **bản THẬT của thứ `MT-18` từng báo động**: `MT-18` là
báo động **giả** (4/12 dấu `|` đã escape đúng), đây mới là ca thật.

📌 Soát toàn file **theo từng bảng** (không dùng một con số chung — `TASKS.md` có 20 bảng, bảng
changelog 6 cột là **đúng**): còn **27 dòng khác** lệch cột so với header của chính bảng đó. **Không
tự sửa** — 27 dòng do nhiều phiên viết qua nhiều ngày, sửa hàng loạt một file trạng thái dùng chung là
đúng hiểm hoạ `N12`. Phiên `[f5177d]` tự kiểm Khối 17: **0 dòng lệch**, nên không dòng nào của họ.

### 3. 🔑 Bài học lớn nhất: phủ sóng theo DỮ LIỆU, không theo số phép kiểm

`tai_dump_agg_trades()` (TD-0162, đường đo của `DR-015` Bước 2) có một lỗi **sống** từ lúc viết:
đường dẫn URL dùng symbol **thô**, mà `http.client._encode_request` gọi `request.encode("ascii")` ⇒
một ký tự ngoài ASCII làm nó raise **trước khi gửi**.

Và sàn **có** mã tên phi ASCII — **một trong số đó nằm trong chính pool 102 mã giao dịch**:
`币安人生USDT`. Kho lưu trữ/explore còn `我踏马来了USDT` · `牛来USDT` · `龙虾USDT` · `哈基米USDT`.

**Nó không bị bắt bởi một test, cũng không bởi việc đọc lại mã.** Nó bị bắt vì tôi **copy khuôn** sang
một hàm mới, rồi hàm mới **chạy trên tập rộng hơn** và nổ ở mã thứ ~600/629.

⇒ Ghép với hai mục đã ghi, thành **ba ca cùng một họ**:

| Ngày | Ca | Điểm chung |
|---|---|---|
| 08/09 | *"ca sai chỉ đi qua MẪU DỰNG TAY, chưa bao giờ đi qua ĐƯỜNG SẢN XUẤT THẬT"* | lớp canh sắc nhưng chĩa nhầm hướng |
| 08/09 (TD-0182) | *"bộ sinh dữ liệu LỖI THỜI so với hệ thống nó nuôi"* | không ai viết sai dòng nào |
| 13/09 | lỗi phi ASCII, bắt bởi **chạy cùng một đường trên nhiều dữ liệu hơn** | — |

**Câu rút ra (phiên `[f5177d]` phát biểu, tôi nhận):** ***phủ sóng theo DỮ LIỆU, không theo số lượng
phép kiểm.*** Một hàm có 30 test trên 5 mã ASCII vẫn chết ở mã thứ 600.

📌 Và chi tiết biến bản vá từ *phòng xa* thành *chặn một lỗi chắc chắn xảy ra*: mã đó nằm trong pool
**giao dịch**, không phải chỉ trong kho. Nếu chỉ trong kho thì còn cãi được là ngoài phạm vi.

### 4. 🔴 Lỗi thứ hai của phiên này: lẫn *"không được đụng"* với *"không được xem"*

Tôi viết *"không mở artifact niêm phong để kiểm"* và để một câu ở mức **SUY** (*"nếu lần đó có mã phi
ASCII thì nó đã phải crash"*). Nhưng kỷ luật niêm phong cấm **SỬA** và cấm **CHẠY LẠI** — **không cấm
ĐỌC**. Một lệnh đọc đóng hẳn khoảng hở: `dr015-luot-khop-tranche.json` → `_nguon.cap` =
`['1000BONK/USDT:USDT','1000PEPE/USDT:USDT']`, **91 lượt, 2 cặp, cả hai ASCII**.

🔑 **Thận trọng đặt sai chỗ không bảo vệ gì cả, chỉ hạ chất lượng câu trả lời** — và nó đắt hơn sự bất
cẩn ở chỗ **nó trông như kỷ luật tốt, nên không ai soi**. Cùng họ *"rác là một kết luận rút từ cái
tên, không phải một quan sát"* (07/09), ở chiều ngược: lần này tôi **từ chối quan sát vì một cái nhãn**.

📌 Phép đọc đó lộ ra `MT-37`: `Δ_R(LONG) = 0,1612` đo trên **đúng hai cặp**, mà `d3_5_han_che` — bản
tự khai của chính cổng D3.5 — khai **bốn** hạn chế và **không** khai phạm vi mã (thử tám chuỗi, cả
tám vắng).

### 5. `TD-0231` — con số, và một lỗi thiết kế bước verify của chính tôi

Dựng lại pool **đúng tại `T1`** bằng `pairlist_point_in_time()` **đã có sẵn từ TD-0096** — kịch bản
này là **người gọi mà docstring `pool.py:112` đòi suốt và chưa từng tồn tại**.

Tại `T1` (mốc duy nhất chạy vào phán quyết D4): `pool.yaml` **102** · pool đúng **116** · **chung 55**
· `K = 61` (**52,6%**). Cách đọc viết **TRƯỚC** (commit `ab290eb` trước lượt chạy) đặt ngưỡng ≲10%
⇒ **gấp hơn năm lần** ⇒ kết cục *"K lớn"*: WFO đang đo **sai rổ** theo chiều PASS.

Phần **không nhiễu**: 24/47 mã của `M` **không tồn tại** tại `T1` ⇒ không thể thuộc pool đúng, bất kể
volume.

🔴 **Và một lỗi của chính tôi trong bước verify:** phép chạy `pairlist_over_time()` trong artifact
**không chứng minh gì cả** — tôi nạp cho mỗi mốc **đúng tập pool đúng của mốc đó** với volume giả `2×`
sàn, nên dĩ nhiên `explore = 0` ở cả ba mốc. Ràng buộc §9c.4b **không được thi hành**. Kế hoạch ghi
việc đó là một phép kiểm; thi hành xong nó thành một phép kiểm **rỗng**, và chỉ lộ ra khi tôi đọc lại
đầu ra thay vì tin dòng kế hoạch. Khai ra thay vì để nó trông như một phép kiểm đã chạy.

⚠️ Hạn chế thứ hai, cũng là lỗi artifact: **không lưu volume từng mã** ⇒ không ai định lượng được
nhiễu ngưỡng volume một-ngày. Kết luận không phụ thuộc nó (52,6% vs 10%) nhưng **tính tái lập thì có**.

### 6. Hai vòng bác một đề xuất, hai lý do khác nhau, không vòng nào thừa

Phiên `[f5177d]` đề xuất thêm một vế fail-closed vào `§4` (`buoc4_hieu_chinh_hai_chieu`) để cưỡng chế
phạm vi `Δ_R`. Tôi bác bằng **giá**: người gọi ngoài module là **đúng một file và nó là TEST KHOÁ**
(`test_lz58:39`), nên tham số bắt buộc ⇒ phải sửa `L-Z58` ⇒ ba điều kiện `§7.1`; còn tham số **có mặc
định** ⇒ **fail-OPEN**, một PASS RỖNG dựng sẵn từ lúc sinh.

Họ định né bằng cách cho hàm **tự đọc** artifact — rồi tự bác lần hai, bằng một lý do **khác hẳn**:
module đó là **tầng thuần** (0 lời gọi đọc file) và docstring `:6-8` khai thẳng *"§4 cố ý KHÔNG đặt
ngưỡng phần trăm — **ngưỡng tuỳ tiện là chỗ uốn kết luận sau khi thấy số**"*. ⇒ Đề xuất **sai TẦNG,
không sai ý**; chỗ đúng là **tầng nuôi `§4`** (bộ chạy ablation), nơi `run_ablation.py` còn ở
`NotImplementedError` nên **chưa có test khoá nào phải sửa**.

🔑 **Nếu chỉ có vòng bác thứ nhất thì họ đã đi tìm đường né — và đường né vi phạm hai tính chất thiết
kế mà lúc đó chưa ai biết là có.** Hai vòng, hai lý do độc lập, không vòng nào thừa. Và bài học họ tự
ghi: **đề xuất một thay đổi cho một module mà chưa đọc docstring của nó**.

📌 Cả hai phương án — cái được chọn và cái bị loại — đều ghi vào `MT-37`, đúng lý do đã ghi hai phép
kiểm **thất bại** vào `DR-FAI-01` §4b: người sau khỏi đề xuất lại thứ đã bị bác.
