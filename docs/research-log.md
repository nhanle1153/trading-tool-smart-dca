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
