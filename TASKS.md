# TASKS.md — Backlog Tổng & Tracker Công việc — Tool D

> Khởi tạo cuối Giai đoạn 2, ngày 06/09/2026. Mã project: **TD**.
> Backlog phủ **D0-PRE** (Khối 0–8, ✅ đóng cổng 06/09/2026) và **D1** (Khối 9–12, mở 07/09/2026).
> Các giai đoạn D2→D12 sẽ thêm việc khi tới lượt.
> Nguồn tạo "Mục lớn": danh sách chức năng ưu tiên ở `back-end-note.md` §0.1 (GĐ1)
> kết hợp với các khối trong `ARCHITECTURE.md` (GĐ2).

## Quy tắc vận hành file này

1. **Mã việc:** `TD-{4 số}`. Số **không bao giờ tái sử dụng**, kể cả khi việc bị hủy.
2. **Trạng thái:** 🔓 Chưa làm · 🔒 Đang làm · ✅ Done · ❌ Đã hủy.
3. **Trước khi code một việc:** đổi 🔓 → 🔒. Chỉ 1 người/1 tab nên bước khóa được nới lỏng, nhưng vẫn đổi trạng thái để theo dõi.
4. **Khi xong:** đổi 🔒 → ✅ — và chỉ khi **lệnh verify ở cột cuối đã chạy và cho đúng kết quả**, không phải khi "code trông có vẻ đúng".
5. **Việc bị hủy:** không xóa dòng — đổi ❌, giữ nguyên mã.
6. **Cập nhật trạng thái:** tự do, ngay lập tức.
7. **Cập nhật nội dung việc:** ghi vào "Lịch sử thay đổi checklist" bên dưới.

> 🔴 **THỨ TỰ KHỐI 3 LÀ BẮT BUỘC TUẦN TỰ** (spec dòng 4420–4424): (1) → (2) → (3), không làm song song.
> 🔴 **KHỐI 1 PHẢI XONG TRƯỚC MỌI KHỐI KHÁC** (dòng 4436–4439): con số nào sinh ra trước khi tầng chống nhiễm sống thì không dùng được cho bất kỳ quyết định nào.

---

## Checklist công việc

### Khối 0 — Hạ tầng repo

| Mã | Tên việc | TT | Phụ thuộc | Verify — chạy gì, thấy gì thì xong |
|---|---|---|---|---|
| TD-0001 | `git init`, `.gitignore`, `.gitattributes` (ép LF), cây thư mục | ✅ | — | `git check-attr text -- src/tool_d/x.py` → `text: set` |
| TD-0002 | Khởi tạo 4 file quy trình: `CLAUDE.md`, `ARCHITECTURE.md`, `back-end-note.md`, `TASKS.md` | ✅ | TD-0001 | 4 file tồn tại; `back-end-note.md` có đủ mục 0–8 |
| TD-0003 | Tạo repo GitHub **private**, push `main` | ✅ | TD-0002 | `git remote -v` có origin (`github.com/nhanle1153/trading-tool-smart-dca`); `git log origin/main` khớp local — đã push thành công |
| TD-0004 | `docker/Dockerfile` (base Freqtrade **pin theo digest** + `git` + pytest + `safe.directory`) và `docker-compose.yml` (3 service; **KHÔNG mount `lockbox/data/`** vào `tests`; `TZ=UTC`) | ✅ | TD-0001 | `docker compose run --rm tests python -c "import freqtrade,pytest,yaml;print('ok')"` |
| TD-0005 | Xác minh `git_sha` lấy được **từ trong container** | ✅ | TD-0004 | `docker compose run --rm tests git rev-parse HEAD` in đúng SHA của host, không phải rỗng |
| TD-0006 | Quyết định số phận `dashboard-ui/` (project Node có `.git` riêng và có `.env`) — submodule / repo riêng / gộp thẳng vào. Hiện đang bị `.gitignore` chặn | ✅ | TD-0001 | Chủ dự án chọn "repo riêng" (lý do: backend D0-PRE có spec kiến trúc khoá cứng + Docker context riêng, không muốn ~1500 gói npm của front-end lẫn vào). Đã tạo `origin` mới (`github.com/nhanle1153/front-end-trading-tool-smart-dca`) và push `main` thành công — `git log origin/main` khớp local. `dashboard-ui/` tiếp tục bị `.gitignore` chặn khỏi repo backend (đúng theo quyết định) |
| TD-0007 | Xác nhận `tool-d-dashboard-thiet-ke.html` (651KB, ảnh chụp giao diện Tool A dùng làm tham chiếu) có nên nằm trong repo này không | ✅ | TD-0001 | Đã chuyển sang `docs/tool-d-dashboard-thiet-ke.html`, lý do ghi trong `ARCHITECTURE.md` mục 3, `.dockerignore` đã hết trùng lặp |

### Khối 1 — PHẦN 0d, tầng chống nhiễm phép đo (LÀM TRƯỚC MỌI THỨ)

| Mã | Tên việc | TT | Phụ thuộc | Verify |
|---|---|---|---|---|
| TD-0010 | `measurement/tri_state.py` — `Measured[T]`, ba trạng thái, `render()` không có nhánh "số cũ kèm cảnh báo" | ✅ | TD-0004 | `pytest -k lz41` xanh |
| TD-0011 | `measurement/hashing.py` + `gitinfo.py` — sha256 file (thiếu → `"MISSING"`), git sha + cờ working tree bẩn | ✅ | TD-0005 | file thiếu → trả `"MISSING"`, không nuốt exception |
| TD-0012 | `measurement/provenance.py` — 7+1 khoá, `validate_provenance()`. Chốt luôn định dạng `cache_key(prov)` để D3 không phải sửa ngược | ✅ | TD-0011 | `pytest -k lz40` xanh, **8 ca** (đủ khoá + thiếu từng khoá) |
| TD-0013 | `config/tool_d_config.yaml` chép nguyên §6.9.5 + `config/loader.py`. Áp MT-03: `_budget_remaining_B3: null # derived` | ✅ | TD-0004 | `tunable_param_names()` trả về **đúng 12** |
| TD-0014 | Test **L-Z37** (cấm `*Parameter`, cấm `<Strategy>.json`) và **L-Z39** (cấm env đọc tham số Tầng B/C) | ✅ | TD-0013 | `pytest -k "lz37 or lz39"` xanh |
| TD-0015 | `measurement/guard.py` — `measurement_guard()` | ✅ | TD-0013 | Tạo `user_data/strategies/Fake.json` **hỏng** → exit **86**, stdout in nội dung, và **file vẫn còn nguyên** |
| TD-0016 | 8 khung entrypoint E1–E8, mỗi file gọi guard ở dòng đầu `main()` | ✅ | TD-0015 | `ls entrypoints/*.py` đúng 8 file, không hơn — đã xác nhận (8/8: run_backtest, run_wfo, run_ablation, touch_lockbox, periodic_report, trial_ledger_audit, build_pool, backfill_data); import sạch + `pytest` 65 passed trong Docker |
| TD-0017 | Test **L-Z36** — AST + danh sách đóng | ✅ | TD-0016 | `pytest -k lz36` xanh (14 ca, gồm 5 ca "răng"); thêm `entrypoints/e9_tmp.py` thật vào thư mục → FAIL đúng như spec, đã xoá; `pytest` toàn bộ 82 passed trong Docker |
| TD-0018 | `assert_cache_none()` trong E1 — **từ chối**, không tự chèn | ✅ | TD-0016 | `python entrypoints/run_backtest.py --timerange X` → exit **87** — đã xác nhận trong Docker (service `freqtrade`); `--cache none` rơi xuống `NotImplementedError` (Khối 2/3, chưa phải lỗi); `pytest -k run_backtest_cache` 3 ca xanh |
| TD-0019 | Bộ test grep: **L-Z32** (tên biến đã xoá), **L-Z33** (cấm 15m), **L-Z46** (cấm `profit_ratio` ở tầng đo), **L-Z48c** (cấm nhãn "R" trần) | ✅ | TD-0016 | `pytest -k "lz32 or lz33 or lz46 or lz48c"` xanh (17 ca, gồm 8 ca "răng") trong Docker; toàn bộ suite 99 passed |
| TD-0020 | 🚪 **CỔNG KHỐI 1** — chạy toàn bộ L-Z36→L-Z41 trong Docker | ✅ | TD-0010…0019 | `docker compose run --rm tests tests/lock/test_lz36_entrypoint_guard.py tests/lock/test_lz37_forbidden_parameter.py tests/unit/test_run_backtest_cache.py tests/lock/test_lz39_env_tunable_param.py tests/lock/test_lz40_provenance.py tests/lock/test_lz41_tri_state.py` → 65 passed, 0 failed (lệnh gốc sai cú pháp — xem Lịch sử thay đổi checklist). `pytest` toàn bộ → 99 passed. Gắn tag `d0pre-0d-live` |

### Khối 2 — Đơn vị đo + cấu hình Freqtrade

| Mã | Tên việc | TT | Phụ thuộc | Verify |
|---|---|---|---|---|
| TD-0025 | `docs/decisions/DR-013-don-vi-do.md` — mọi chỉ số trên `pnl_abs`, bảng phân biệt ba chữ "R" | ✅ | TD-0020 | File có bảng ba chữ "R" (R_eff/r_eff_pct, planned_risk_usdt, R_realized) đúng spec dòng 2777-2787; mục "cấm chữ R trần" có ví dụ đúng/sai; bảng test L-Z46/47/48/48b/48c đối chiếu trạng thái D0-PRE |
| TD-0026 | `config/freqtrade/config.json` theo §0c.3 + ánh xạ lệnh chờ §3.5 | ✅ | TD-0020 | `docker compose run --rm freqtrade -m freqtrade show-config -c config/freqtrade/config.json` → exit 0, không lỗi (xác nhận trong Docker). Ghi chú: `protections` bị freqtrade 2026.8 DEPRECATE khỏi config.json (chuyển sang thuộc tính class của strategy, D1+) — TD-0027/L-Z24 phải kiểm ở đúng chỗ mới, xem comment trong file config |
| TD-0027 | Test **L-Z24** (cờ cấm), **L-Z25** (không dấu vết hyperopt), **L-Z42** (config khớp hằng số spec) | ✅ | TD-0026 | `pytest -k "lz24 or lz25 or lz42"` xanh |
| TD-0028 | Đọc mã nguồn Freqtrade **đang cài** cho giả định D2a/D2b/D6/D7 → `docs/freqtrade-source-read.md`. **Làm TRƯỚC khi viết bất kỳ test nào về chúng** | ✅ | TD-0004 | File có 4 mục, mỗi mục trích đường dẫn + số dòng trong image, kèm image digest |

### Khối 3 — 🔴 THỨ TỰ CỨNG 1→2→3, KHÔNG SONG SONG

| Mã | Tên việc | TT | Phụ thuộc | Verify |
|---|---|---|---|---|
| TD-0030 | **(1)** Verify `zone_width` min có phải **code chết** không (§3.3). Phân tích spec, **không chạm dữ liệu**. Kết luận nhị phân → `DR-D0PRE-01`. Giải MT-04 | ✅ | TD-0020 | DR có kết luận CHẾT/SỐNG + lý do; nếu CHẾT thì xoá hẳn khỏi YAML, không để lại comment |
| TD-0031 | **(2)** Xác nhận lại bảng DOF của DR-010 **từng dòng** → `config/dof_inventory.yaml` | ✅ | TD-0030 | `python -m tool_d.config.dof --check` in DOF gốc và các thành phần khớp bảng |
| TD-0032 | **(3)** Chốt `N_ĐĂNG_KÝ` (114 nếu chết / 120 nếu không) → `DR-D0PRE-02` | ✅ | TD-0031 | 🔴 `pytest -k lz29` **PASS trước khi `git commit`** (spec dòng 4424) |
| TD-0033 | `gates/dsr.py` + test **L-Z34** — N đọc từ registry, không phải hằng số | ✅ | TD-0032 | `pytest -k lz34` xanh; `dsr_hurdle(114)` ≠ `dsr_hurdle(228)`, khớp √(2·ln N) sai số 1e-6 |

### Khối 4 — Điền các ô trống bắt buộc

| Mã | Tên việc | TT | Phụ thuộc | Verify |
|---|---|---|---|---|
| TD-0040 | `gates/thresholds.py` fail-closed + test **L-Z35** | ✅ | TD-0020 | `pytest -k lz35` xanh; đưa kết quả cực tốt giả lập qua gate → vẫn **FAIL** |
| TD-0041 | 🔴 **ĐIỀN ngưỡng DSR-adjusted expectancy §10.2 — blocker B6** (OQ-01). Viết DR **trước** khi biết kết quả lần đánh giá tiếp theo | ✅ | TD-0040, TD-0033 | `DR-D0PRE-03` có SỐ; hằng số không còn `inf`; L-Z35 chuyển sang biến thể "best-known vẫn FAIL" và vẫn xanh |
| TD-0042 | 🔴 **ĐIỀN thang drawdown 5/8/20%** (OQ-03). Sau bước này là **Hạng 0, không sửa được** | ✅ | TD-0013 | `DR-D0PRE-04` commit; giá trị trong YAML khớp DR |
| TD-0043 | 🔴 **ĐIỀN `E_D`, `L_exchange`, `rho_pct`, % lỗ tối đa ngày xấu** theo vốn thật (OQ-02) | ✅ | TD-0013 | Commit riêng; `pytest -k lz29` vẫn xanh |

### Khối 5 — Sổ phép thử + audit

| Mã | Tên việc | TT | Phụ thuộc | Verify |
|---|---|---|---|---|
| TD-0050 | Schema JSON cho `trial_registry.jsonl` (**dạng sổ sự kiện**, theo MT-01) và `idea_queue.jsonl`; tạo hai file rỗng | ✅ | TD-0012 | `jsonschema` validate fixture mẫu cho cả 5 loại sự kiện |
| TD-0051 | `ledger/registry.py` + `budget.py` — reserve / seal / consume / refund, công thức Khả dụng, bản chiếu trạng thái. Áp MT-03 | ✅ | TD-0050 | Chuỗi reserve→seal→consume: `available()` đúng ở từng bước |
| TD-0052 | Test **L-Z52** — hết ngân sách thì từ chối, chưa chạm dữ liệu | ✅ | TD-0051 | `pytest -k lz52` xanh; spy khẳng định **0 lần** đọc `user_data/data` |
| TD-0053 | Test **L-Z53** — giết tiến trình sau khi có kết quả fold đầu → CONSUMED, hoàn trả phải RAISE | ✅ | TD-0051 | `docker compose run --rm tests -k lz53` xanh |
| TD-0054 | Test **L-Z54** — 4 dòng bảng DR-014 + trần trả lại 3 lần | ✅ | TD-0051 | `pytest -k lz54` — 5 ca xanh |
| TD-0055 | `assert_dataset_timerange()` + test **L-Z55** — bộ chạy tự kiểm, không nhận lời khai | ✅ | TD-0051 | `pytest -k lz55` xanh |
| TD-0056 | E6 `trial_ledger_audit.py` **đầy đủ** (H16) + test L-Z10/11/12/15/16/17 | ✅ | TD-0051 | Sổ rỗng → exit 0, in `"đã audit N/M (X đạt, Y chưa đạt, Z chưa đo được)"`; sổ bẩn → exit≠0 |
| TD-0057 | Nối E6 vào **đầu** E1/E2/E3 (chạy trước mỗi lần backtest) | ✅ | TD-0056 | Test AST: `run_audit` được gọi trong `main()` của E1–E3 |

### Khối 6 — Báo cáo định kỳ

| Mã | Tên việc | TT | Phụ thuộc | Verify |
|---|---|---|---|---|
| TD-0060 | E5 `periodic_report.py` **đầy đủ** (§12d.2), mọi chỉ số ở trạng thái `pending` | ✅ | TD-0010, TD-0051 | `python entrypoints/periodic_report.py` in khối xuất xứ ở đầu + bảng toàn "chưa đo được" — xác nhận (commit `03bfeef`): khối xuất xứ Ở ĐẦU, 21 chỉ số §12d.2 BƯỚC 1 toàn "chưa đo được", dòng tổng `audit_line()`. `pytest -k "report_model or periodic_report"` → 12 passed trong Docker; toàn bộ suite → 264 passed |
| TD-0061 | Test **L-Z41** trên đầu ra **thật** của E5 | ✅ | TD-0060 | Grep đầu ra: không có `-1`, `UNKNOWN`, `0.0` giả — xác nhận (commit `a38fca7`, `tests/lock/test_lz41_periodic_report.py`): chạy E5 thật như tiến trình con, `scan_for_sentinels()` sạch + literal check độc lập. `pytest -k lz41` → 27 passed; toàn bộ suite → 272 passed trong Docker |
| TD-0062 | Đóng băng nội dung báo cáo (đổi = tiêu 1 trial, spec dòng 4810) | ✅ | TD-0060 | Test hồi quy giữ hash danh sách chỉ số — xác nhận (commit `6c4d3fc`): `content_fingerprint()` + `FROZEN_CONTENT_HASH` trong `tests/unit/test_report_content_frozen.py`, nhạy với cả thứ tự lẫn nhãn. Toàn bộ suite → 276 passed trong Docker |

### Khối 7 — Lockbox

| Mã | Tên việc | TT | Phụ thuộc | Verify |
|---|---|---|---|---|
| TD-0070 | `lockbox/seal.py` + `access_log.py` + test **L-Z13 / L-Z14** | ✅ | TD-0012 | Sổ truy cập rỗng → PASS (`validate_before_d9([])==[]`); thêm 1 bản ghi trước D9 → FAIL; sửa 1 byte dữ liệu → `verify_seal` FAIL. `docker compose run --rm tests -k "lz13 or lz14"` → 25 passed (xác nhận trong Docker) |
| TD-0071 | E4 `touch_lockbox.py` chế độ `--verify-seal` (H17); chế độ chạm thật vẫn TỪ CHỐI tới sau D9 | ✅ | TD-0070 | Chạy được, **0 bản ghi** được thêm vào sổ truy cập — xác nhận: `--verify-seal` PASS (0 seal ở D0-PRE) và chế độ mặc định TỪ CHỐI, cả hai đều không tạo `lockbox_access.log`. `pytest -k "lz14 or touch_lockbox"` → 34 passed trong Docker |
| TD-0072 | Nối H17 vào đầu pipeline E1/E2/E3 | ✅ | TD-0071 | Test AST: `verify_seal` được gọi trong `main()` |

### Khối 8 — Việc chạm dữ liệu (CHỈ SAU khi Khối 1–7 xanh)

> Ranh giới theo MT-02: "chạm" = đánh giá cấu hình trên CALIB/WFO/LOCKBOX.
> Đo thông tin mô tả là dòng `CTRL`, 0 trial, bắt buộc có assert khoảng thời gian.

| Mã | Tên việc | TT | Phụ thuộc | Verify |
|---|---|---|---|---|
| TD-0079 | Hoàn thành Mục 2–4 của `api-integration-rules.md` (R1–R12) + `provider-map.md` cho Binance. **Bắt buộc trước dòng code gọi mạng đầu tiên** | ✅ | TD-0020 | Bản điền ở gốc repo, Mục 4 đủ 4 bảng (dịch vụ, endpoint, mã lỗi, ngưỡng) |
| TD-0080 | E8 chế độ `--probe-coverage`: verify độ dài lịch sử **Open Interest** Binance thật sự trả về | ✅ | TD-0079 | In số ngày thật; nếu chỉ ~30 ngày → ghi research-log, ảnh hưởng thiết kế chỉ báo |
| TD-0081 | Ước lượng **số lệnh/năm** bằng tính tay. **< 150 → hỏng từ thiết kế, xử lý ngay** | ✅ | TD-0083 | `docs/estimate-trades-per-year.md` có phép tính và kết luận nhị phân |
| TD-0082 | Kiểm **min notional** từng cặp vs notional tranche 1 nhỏ nhất | ✅ | TD-0043, TD-0079 | Bảng đối chiếu; có vi phạm → nâng `E_D` hoặc đặt sàn, ghi DR |
| TD-0083 | Chốt pool ~100 mã, loại BTC/ETH khỏi giao dịch, tách tập EXPLORE (OQ-04) | ✅ | TD-0079, TD-0056 | E7 chạy, ghi **4 trial B0** vào sổ; `pytest -k lz11` vẫn xanh |
| TD-0084 | Chia CALIB / WFO / LOCKBOX, kiểm 4 điều kiện DR-011, niêm phong `lockbox_seal_1.json` (OQ-05) | ✅ | TD-0083, TD-0070 | `touch_lockbox.py --verify-seal` PASS; sổ truy cập vẫn **0 bản ghi** |
| TD-0085 | Thiết lập **backup lockbox ngoài git + test khôi phục thật một lần** (OQ-08) | ✅ | TD-0084 | Khôi phục từ backup vào thư mục tạm → `verify_seal` PASS trên bản khôi phục |
| TD-0086 | 🚪 **GATE D0-PRE** — ghi `runtime_state.json.d0_pre_complete` từ **một lần chạy thật** | ✅ | TD-0020…TD-0085 | `docker compose run --rm tests tests/lock` 0 failed **và** `trial_ledger_audit.py` exit 0 **và** `periodic_report.py` sạch → `git tag d0-pre-complete` |

---

### Khối 9 — D1: cổng D0-PRE có hiệu lực + hạ tầng dữ liệu an toàn (H19)

> D1 = "H20 (§0d) TRƯỚC, rồi H1-D + H4-D + H13 + H19" (spec dòng 4468). **H20 đã xong ở D0-PRE**
> (Khối 1). Khối 9 làm hai việc còn thiếu để chạm dữ liệu thật một cách an toàn.
> 🔴 H19 **chặn lần backfill đầu tiên** (spec dòng 4350) — Tool A suýt xoá nhiều năm dữ liệu vì bẫy
> "ghi đè theo khoảng ngày yêu cầu". Backfill lockbox ở TD-0084 không dính bẫy này vì ghi vào thư
> mục RỖNG, nhưng CALIB/WFO thì có dữ liệu chồng lấn — bắt buộc qua H19.

| Mã | Tên việc | TT | Phụ thuộc | Verify |
|---|---|---|---|---|
| TD-0090 | Nối `is_d0_pre_complete()` vào đầu **E1/E2/E3/E7/E8** — từ chối chạy khi cổng chưa đóng (§N2) | ✅ | TD-0086 | Test AST: 5 entrypoint gọi `is_d0_pre_complete` trong `main()`; giả lập `runtime_state.json` thiếu khoá → exit 90 |
| TD-0091 | 🔴 **H19** — E8 backfill an toàn: (a) sao lưu trước, (b) **GỘP** không ghi đè, (c) verify phần cũ **byte-for-byte**, (d) tải hỏng → `unreadable`, KHÔNG cache rỗng | ✅ | TD-0090 | Test: backfill chồng lên dữ liệu cũ → hash phần cũ KHÔNG đổi; mô phỏng tải hỏng → không sinh file rỗng |
| TD-0092 | 🔴 **H19** — chỉ số **ĐỘ PHỦ DỮ LIỆU** riêng; cấm suy nguyên nhân gốc từ khoảng trống mà chưa kiểm nguồn | ✅ | TD-0091 | E8 in bảng độ phủ theo mã × khung; khoảng trống hiện "chưa kiểm nguồn", không kết luận thay người |
| TD-0093 | Backfill THẬT **CALIB [T0,T1]** + **WFO [T1,T2]** cho 102 mã qua E8 đã an toàn (DR-D0PRE-07) | ✅ | TD-0091, TD-0092 | `touch_lockbox.py --verify-seal` vẫn PASS (lockbox không bị đụng); bảng độ phủ CALIB/WFO ghi vào research-log |
| TD-0094 | 🔴 Phát hiện ở TD-0093: `freqtrade download-data --timerange` **không tôn trọng mốc kết thúc** (tải lố tới gần T3, lấn phạm vi LOCKBOX vào thư mục làm việc). File trên đĩa KHÔNG đáng tin về phạm vi — cơ chế tự kiểm đúng (`assert_dataset_timerange`, L-Z55, DR-014 §2) đã có sẵn nhưng chưa nối được với cấu hình thật. Nối `tier_c.data_split` (T0-T3, DR-D0PRE-07) với L-Z55 qua `dataset_boundaries_from_config()` | ✅ | TD-0093 | `pytest -k timerange` → 10 passed (gồm tái hiện đúng kịch bản TD-0093: khai WFO, dữ liệu lấn qua LOCKBOX → `assert_dataset_timerange` raise). **Phạm vi:** E1/E2/E3 CHƯA có logic tải dữ liệu thật (D1 chỉ dựng khung guard, NotImplementedError) nên CHƯA có chỗ để gọi self-check sau khi tải — việc nối `assert_dataset_timerange()` vào đúng điểm sau bước tải dữ liệu là phần việc của bất kỳ task nào viết logic backtest/WFO/ablation thật sau này, không phải của TD-0094 |

---

### Khối 10 — D1: H1-D pairlist point-in-time (🔴 ĐƯỜNG GĂNG)

> Spec dòng 4338 + 4354: H1-D là hạng mục **tốn thời gian nhất** của v10 gốc, phải **viết lại từ đầu**,
> không dùng `lib/pool-builder`. Mỗi lần đổi pool = backfill lại toàn bộ và **mọi số cũ không so sánh được**.

| Mã | Tên việc | TT | Phụ thuộc | Verify |
|---|---|---|---|---|
| TD-0095 | Khảo sát **nguồn danh sách lịch sử** (symbol đã huỷ niêm yết — API Binance KHÔNG trả). Không có → DR ghi tường minh *"đang chấp nhận survivorship bias, ước lượng hướng lệch: có lợi"*, KHÔNG im lặng | ✅ | TD-0093 | Kết luận + bằng chứng đo trong `docs/research-log.md`; nếu chấp nhận bias → có DR riêng |
| TD-0096 | `pairlist_point_in_time(t)` — pool hợp lệ **tại thời điểm t** theo đúng 4 tiêu chí §0.3, tính point-in-time (tuổi ≥180 ngày, volume ≥15tr USDT — DR-D0PRE-05) | ✅ | TD-0095 | Test: tại t lùi 1 năm, mã niêm yết sau t KHÔNG có mặt; kết quả KHÔNG đổi khi thêm dữ liệu sau t |
| TD-0097 | Verify pool point-in-time **không lệch theo thời gian** + ranh giới tập **EXPLORE không rò** (§9c.4b) | ✅ | TD-0096 | Test: mã EXPLORE (gồm BTC/ETH) không lọt vào pool giao dịch tại BẤT KỲ t nào |

---

### Khối 11 — D1: Zone detection + H4-D (🔴 P0 TUYỆT ĐỐI, trước mọi logic chiến lược khác)

> Spec dòng 2432: *"H4-D — Zone confirmation delay test · P0 · NGÀY 1, TRƯỚC MỌI THỨ KHÁC"*.
> Đây là **blocker B2**. Lookahead trong zone detection làm **mọi kết quả D0.9 bị bơm lên có hệ thống**.
> 🔴 Không sửa code sản xuất để chiều artifact của `lookahead-analysis` (spec dòng 2455).

| Mã | Tên việc | TT | Phụ thuộc | Verify |
|---|---|---|---|---|
| TD-0100 | Swing detection §1.1 (k=3, xác nhận 2 phía) — hàm THUẦN, không đọc dữ liệu sau `t` | ✅ | TD-0090 | `la_diem_swing()` trong `src/tool_d/zone_detection.py` — xác nhận (commit `f14c847`): 8 test trong `tests/unit/test_zone_detection.py` xanh trong Docker (swing đáy/đỉnh đúng/sai, chưa đủ nến sau → chưa xác nhận thay vì "không phải swing", dữ liệu tương lai ngoài cửa sổ không đổi kết quả). `docker compose run --rm tests` toàn bộ suite → 422 passed |
| TD-0101 | `confirm_ratio(i, t)` §7.4 — liên tục 0/0.33/0.67/1.0 + điều kiện **HUỶ** khi giá tạo cực trị vượt qua `i` | ✅ | TD-0100 | `confirm_ratio()` + `zone_da_bi_huy()` trong `src/tool_d/zone_detection.py` — xác nhận (commit `58fd5ca`): 16 test (`test_zone_detection.py`) xanh trong Docker — 4 mốc 0/0.33/0.67/1.0, giữ 1.0 sau `i+k`, huỷ vĩnh viễn không tự phục hồi, dữ liệu sau `t` không đổi kết quả. Toàn bộ suite → 430 passed |
| TD-0102 | 🔴 **H4-D** (§7.2) — `assert confirmed_at_bar − swing_bar == 3`; mọi tranche fill có timestamp ≥ `confirmed_at_bar` | ✅ | TD-0101, TD-0093 | `tests/lock/test_lz1_confirmed_at_bar.py` — xác nhận (commit `8a33239`): 3 test xanh trong Docker, dùng fixture feather-shape TỰ TẠO (không đọc thẳng `user_data/data/` — bị `.gitignore` chặn, không phải bằng chứng Docker portable được), gồm 1 ca CỐ Ý có khoảng trống kiểu CALIB thật (TD-0092) — khẳng định thời gian trôi qua PHẢI ≥ k nến, không bao giờ ít hơn. Toàn bộ suite → 433 passed. **Phạm vi:** chỉ phần bất biến `confirmed_at_bar − swing_bar`; phần "tranche fill có timestamp ≥ confirmed_at_bar" CHƯA kiểm được — D1 chưa có code đặt lệnh, để dành cho task đó |
| TD-0103 | 🔴 **H4-D-b** (§7.5) — cắt dữ liệu tại `t`, tính lại, `confirm_ratio(i,t)` KHÔNG đổi | ✅ | TD-0101 | Mở rộng `tests/lock/test_lz1_confirmed_at_bar.py` (spec dòng 2510: H4-D-b là phần mở rộng của L-Z1, không phải mã riêng) — xác nhận (commit `8e18aad`): 15 test xanh trong Docker — chữ ký `confirm_ratio()` không có tham số mảng (không thể đọc dữ liệu sau t dù muốn), `confirm_ratio`/`zone_da_bi_huy` parametrize nhiều cặp (i,t) mẫu, so mảng đầy đủ với mảng bị cắt đúng tại t → bằng nhau tuyệt đối. Toàn bộ suite → 458 passed |
| TD-0104 | **ZSS** §1.2 — 3 thành phần (`touch_count` theo định nghĩa số LD-35, `volume_ratio`, `compression`) + ngưỡng nhận zone §1.3 | ✅ | TD-0102, TD-0103 | `src/tool_d/zone_strength.py` — xác nhận (commit `f4dcfa3`): 22 test trong `tests/unit/test_zone_strength.py` xanh trong Docker (touch_count cụm/point-in-time/không tính nến hình thành, volume_ratio MA20, compression qua TA-Lib ATR, `zss()` đúng công thức + kẹp trần/sàn, `zone_hop_le()` cả 3 điều kiện §1.3). Toàn bộ suite → 480 passed. **Phạm vi:** "close < zone_low → zone bị phá (DG1)" chỉ thi hành ở mức "không tính touch" — gate DG1 thật (§4) chưa có code đối tượng để nối vào ở D1 |
| TD-0105 | 🔴 **H13** — audit thành phần ZSS: KHÔNG dùng dữ liệu ngoài `confirmed_at_bar` | ✅ | TD-0104 | `tests/lock/test_td0105_zss_confirmed_at_bar_audit.py` — xác nhận (commit `05c1b10`): tính `touch_count`+`volume_ratio`+`compression`+`zss()` tại `confirmed_at_bar` trên chuỗi dài, cắt mảng đúng tại đó, tính lại — cả 4 giá trị giống hệt tuyệt đối. Không có mã `L-Z` cho H13 (spec chỉ đặt tên), dùng tên tự đặt `test_td0105_...`. Toàn bộ suite → 481 passed |
| TD-0106 | Chạy `lookahead-analysis` của Freqtrade trên zone detection; **mỗi** cờ phải quy về FP-1/FP-2/FP-3 **có bằng chứng** hoặc điều tra tới gốc | ✅ | TD-0104 | Xác nhận (commit `64ca450`, chi tiết `docs/research-log.md` 07/09/2026): `ZoneDetectionProbe.py` chạy `freqtrade lookahead-analysis` thật qua Docker trên dữ liệu CALIB thật, 2 mã, `has_bias=No` cả hai — 0 cờ nào được nêu ra nên không có gì để quy về FP-1/2/3 (kết quả sạch, không phải "bỏ qua"). Khớp đánh giá độc lập đọc-code cùng ngày. Giới hạn ghi rõ: mới 2/102 mã, tín hiệu thưa — nên chạy lại rộng hơn khi D2 cần số đáng tin hơn |
| TD-0107 | 🐛 Phát hiện qua review độc lập (không phải lookahead): `touch_count()` (`src/tool_d/zone_strength.py:56-61`) — khi `dang_trong_cum=True`, vòng lặp chỉ kiểm `bat_ra`, KHÔNG kiểm `vo_huong_nguoc` — một cú vỡ mạnh xuyên `zone_low`/`zone_high` giữa lúc đang chờ bật ra bị bỏ qua, sau đó bật ra hợp lệ vẫn được tính là 1 touch. Tái hiện: zone day [100,102], giá `[101, 101, 90, 103]` (chạm→vỡ sâu dưới 90→bật lên 103) → `touch_count()` trả 1, không phải 0 | ✅ | TD-0104 | Xác nhận (commit `e424d63`): thêm nhánh `elif vo_huong_nguoc` khi `dang_trong_cum=True` → huỷ cụm thay vì bỏ qua. Test tái hiện đúng kịch bản báo cáo, từ 1 (sai) → 0 (đúng); 23 test `test_zone_strength.py` xanh, không phá test cũ nào. Toàn bộ suite → 482 passed |

---

### Khối 12 — D1: cổng

| Mã | Tên việc | TT | Phụ thuộc | Verify |
|---|---|---|---|---|
| TD-0110 | 🚪 **GATE D1** — H1-D + H4-D + H4-D-b + H13 + H19 đều PASS → **gỡ blocker B2** | ✅ | TD-0093…TD-0106 | Toàn bộ test khoá D1 xanh trong Docker; ghi `runtime_state.json.d1_complete` từ một lần chạy thật; `git tag d1-complete`. 🔴 **Khối `evidence` phải gắn nhãn nguồn `{nguon: do-duoc\|nguoi-khai, noi_dung: …}` theo MT-10** — `do-duoc` chỉ cho chuỗi do code sinh trong chính lần chạy đó |

---

### Khối 13 — D2: Verify giả định D1–D7 (§9b.2) + H15

> Spec dòng 4469-4470: *"D2 Verify D1-D7 (v7: +D6, +D7; D2 tách a/b/c) + H15 · 🔴 L-Z49 (D7) PASS là
> điều kiện vào D4"*. TD-0028 (D0-PRE) đã đọc source cho **D2a, D2b, D6, D7** (kết luận: D2a ĐÚNG,
> D2b KHÔNG hỗ trợ `closePosition`, D6 ĐÚNG dùng giá mở nến, D7 cơ chế an toàn + cảnh báo `trade.id`)
> — xem `docs/freqtrade-source-read.md`. **D1, D3, D4, D5 CHƯA đọc** (file đó tự ghi rõ "sẽ đọc khi
> tới D2"). D2c/D4 (Testnet/Live-only, spec bảng §9b.2) **KHÔNG thuộc phạm vi D2** — hoãn tới D3.5/
> D9.5+, không chặn cổng D2.
>
> 🔴 TD-0114/TD-0115 là lần ĐẦU TIÊN dự án cần một `IStrategy` thật chạy qua Freqtrade backtesting
> (không còn là hàm thuần `src/tool_d/`) — dùng `zone_detection.py`/`zone_strength.py` đã có ở D1.

| Mã | Tên việc | TT | Phụ thuộc | Verify |
|---|---|---|---|---|
| TD-0111 | **D1** — đọc source `adjust_trade_position()` mô phỏng fill limit-maker trong backtest futures (kể cả ca KHÔNG khớp) → nối vào `docs/freqtrade-source-read.md` | ✅ | TD-0110 | Trích đường dẫn + số dòng thật trong image (LD-38/40); kết luận nhị phân ĐÚNG/SAI mô tả spec |
| TD-0112 | **D3** — đọc source cách Freqtrade tính giá vào trung bình khi nhiều lần entry + xác nhận `custom_stoploss` đọc được đúng giá đó | ✅ | TD-0110 | `docs/freqtrade-source-read.md` có mục D3; test đơn vị dựng backtest nhỏ đa-entry xác nhận giá trung bình đúng công thức |
| TD-0113 | **D5** — đọc source hành vi `timeframe-detail 5m`: thứ tự khớp khi nhiều mức giá (p1,p2,p3,SL,TP) cùng nằm trong một nến 1H | ✅ | TD-0110 | Xác nhận (commit `58547ab`): `docs/freqtrade-source-read.md` mục 7 (đường dẫn + số dòng thật) + `docs/research-log.md` 07/09/2026. Backtest thật 2 lần CÙNG một nến 1H tổng hợp, chỉ đổi `--timeframe-detail`: không có → `stop_loss` (-10,18%); có `5m` → `roi` (+1%) — đảo hoàn toàn kết quả, xác nhận đúng thứ tự dòng 5m thật. **Giới hạn residual ghi rõ:** trong CÙNG một nến 5m đơn lẻ, Freqtrade vẫn dùng policy cố định Stoploss-trước-ROI, không phải chronology thật — 5m thu hẹp cửa sổ mơ hồ, không triệt tiêu hoàn toàn |
| TD-0119 | **Phần 2 — Context Trend Filter**: `trend_dir`/`trend_dir_4h` (EMA20/50 + slope, §2.1), xác nhận đa khung (§2.2, L-Z8), tuổi trend ≥5 nến (§2.3), điều kiện vào lệnh §2.5 | ✅ | TD-0104 | `src/tool_d/trend_context.py` — xác nhận (commit `0ae1a82`): 16 test trong `tests/unit/test_trend_context.py` xanh trong Docker (`trend_dir_tai` UP/DOWN/FLAT + fail-closed khi thiếu dữ liệu/NaN, `xac_nhan_da_khung` đồng thuận, `tuoi_trend_nen` tìm điểm cross hoặc `None`, `du_dieu_kien_vao_lenh` cả 4 điều kiện §2.5). Toàn bộ suite → 532 passed. **Phạm vi:** L-Z8 "tại mọi bản ghi plan" cần plan thật (§8) — chưa có code đặt lệnh để sinh plan; nối khi TD-0114 dựng chiến lược |
| TD-0120 | **§3.3b — Xác nhận entry bằng price-action**: rejection wick (hình học nến) HOẶC RSI(14,1H) divergence dùng lại `touch_count` (TD-0104) — tối đa 3 nến chờ, không nới hạn (L-Z6) | ✅ | TD-0104, TD-0119 | `src/tool_d/entry_confirmation.py` — xác nhận (commit `eb1619c`): 12 test `tests/lock/test_lz6_*` xanh trong Docker (rejection đáy/đỉnh, phân kỳ RSI, quét đúng tối đa 3 nến — KHÔNG mở rộng cửa sổ tìm kiếm). Toàn bộ suite → 544 passed. **Phạm vi:** cần bản ghi tranche fill thật (§3.5) để kiểm "mọi tranche 1 đều có entry_confirmation" đầy đủ — nối khi TD-0114 dựng chiến lược |
| TD-0121 | **DG8 — Time Stop**: `bars_since_tranche1 ≥ 24 nến 4H` → đóng MARKET vô điều kiện (kể cả đang lãi/ZSS cao/trend đúng), tag `TIME_STOP` (§4b) | ✅ | TD-0104 | `tests/lock/test_lz18_*`/`test_lz19_*` — không bản ghi nào có `hold_duration_bars > max_hold_bars`; `hold_duration_bars` ghi ở MỌI lệnh đóng kể cả TP/SL |
| TD-0122 | **DG7 — Funding Stop**: `funding_paid_cumulative = -trade.funding_fees` (đọc thẳng field native Freqtrade, KHÔNG tự xây pipeline tích luỹ — LD-09) ≥ 0.3×R_eff → đóng MARKET, tag `FUNDING_STOP` (§4c.2) | 🔒 | TD-0112 | 🔴 **L-Z30 CRITICAL** — không lệnh đã đóng nào có `funding_paid_cumulative > 0.35×R_eff_plan` (biên 0.05 cho độ trễ mốc funding 8h); **L-Z31** — `funding_paid_cumulative` ghi ở MỌI lệnh đã đóng, mọi arm; **L-Z43** — LONG giả lập qua 3 mốc funding dương phải cho `funding_paid_cumulative > 0`, đọc đúng cột `open` (không phải `close`) |
| TD-0123 | **DG6 — Early Invalidation**: điều kiện A (ATR ratio ≥1.8 + `compression` đảo dấu, TD-0104) / B (≥8 nến 1H chưa hồi qua p1) / C (`price_decay_ratio` ≥0.7 + `trend_dir` đảo, TD-0119) / D (short squeeze, chỉ Short) → đóng MARKET (§4.1) | 🔒 | TD-0119 | Test đơn vị từng điều kiện A/B/C/D độc lập + tổ hợp OR; D chỉ kích hoạt khi `is_short=True` |
| TD-0114 | 🔴 **L-Z49 CRITICAL, D7** — dựng `IStrategy` tối thiểu THẬT (1 pair, 1 zone, 3 tranche) dùng `zone_detection`/`zone_strength` đã có; chạy backtest thật; xác nhận `custom_data` ghi ở tranche 1 đọc lại NGUYÊN VẸN ở callback tranche 2/3 + DG6/7/8 + `custom_exit`. FAIL → chặn D4 | 🔓 | TD-0111, TD-0112, TD-0113, TD-0119, TD-0120, TD-0121, TD-0122, TD-0123 | Chạy backtest thật trong Docker (service `freqtrade`, dữ liệu CALIB); test khoá `L-Z49` PASS; FAIL thì ghi rõ, KHÔNG chạy D0.9 |
| TD-0115 | 🔴 **L-Z50, D6** — đo lệch khớp tranche: mọi tranche fill trong backtest thật (TD-0114) có `fill_price` so với giá `timeframe_detail` 5m cho thấy đã CHẠM `p_i`; ghi phân bố lệch, tách tranche 1/2/3, tách Long/Short | 🔓 | TD-0114 | Chạy backtest thật; bảng phân bố lệch ghi `docs/research-log.md` kèm provenance (§0d.5); lệch > 0 ở fill nào → ghi nhận D6 CHƯA giảm nhẹ bởi H5, không tự ý "coi như đạt" |
| TD-0116 | **H15** — network/auth latency probe `POST /fapi/v1/order/test` với API key THẬT (§6.7 điều kiện bảo mật) — 🟡 P1, không chặn cổng D2 | 🔓 | — | Đo latency network+auth thật, ghi `docs/research-log.md`. 🔴 **Cần chủ dự án xác nhận trước khi cấu hình API key thật vào máy** (secret, phạm vi quyền, sub-account) — không tự ý tạo/nạp key |
| TD-0117 | 🚪 **GATE D2** — D1/D3/D5/D6/D7 (phần verify được ở backtest) PASS, L-Z49/L-Z50/L-Z51 xanh → điều kiện vào D3 | 🔓 | TD-0111…TD-0116 | Toàn bộ test khoá D2 xanh trong Docker; ghi `runtime_state.json.d2_complete` từ một lần chạy thật (bằng chứng `do-duoc`, MT-10); `git tag d2-complete`. Ghi rõ D2b/D2c/D4 (Testnet/Live-only) hoãn tới D3.5/D9.5+, không phải "đã qua" |
| TD-0118 | **Idea Queue** — nới `L-Z17` (trần Ngân sách A 5/quý) thành **cảnh báo, KHÔNG chặn chạy** (quyết định chủ dự án 07/09/2026); giữ nguyên con số 5 và giữ `L-Z16` chặn cứng; ghi **MT-11** vào `back-end-note.md` | ✅ | TD-0086 | `run_audit()` trả exit **0** khi sổ có 6 dòng SELECTED cùng quý (vẫn in dòng cảnh báo), và trả exit **≠ 0** khi có dòng `data_source=TOOL_D_RESULTS` mà `status != REJECTED`; test khoá mới `tests/lock/test_td0118_*`; suite Docker tăng đúng số test mới, không giảm. **Xác nhận** (commit `012a9ef` + `277b9e9`): `WARN_ONLY_CODES = {"L-Z17"}` trong `audit_checks.py`, `run_audit()` loại nó khỏi exit code nhưng vẫn in ⚠️ VƯỢT TRẦN; 5 test khoá `test_td0118_*` xanh trong Docker, gồm test canh riêng để `L-Z16` KHÔNG bị nới lây; toàn bộ suite **492 → 497 passed**; chạy thật E6 trên sổ thật → `đã audit 4/6 (4 đạt, 0 chưa đạt, 2 chưa đo được)`, exit 0. MT-11 + OQ-07 + dòng Lịch sử đã ghi `back-end-note.md` |

---

## Việc đã biết là sẽ có, chưa mở

| Giai đoạn | Nội dung | Chặn bởi |
|---|---|---|
| ~~D1~~ ✅ **ĐÃ MỞ 07/09/2026** | H20 ✅ (xong ở D0-PRE) · H1-D · H4-D · H13 · H19 → **Khối 9–12** bên trên (TD-0090…TD-0110) | — |
| ~~D2~~ ✅ **ĐÃ MỞ 07/09/2026** | Verify giả định D1–D7 (§9b.2), H15 → **Khối 13** bên trên (TD-0111…TD-0117). L-Z49 (D7) là điều kiện vào D4 | — |
| D3 | H3-D walk-forward orchestrator | D2 |
| D3.5 | 🚪 Cổng sai lệch thước đo (DR-015) — **chặn D4**, cần testnet | D3 |
| D4 | 🔴 Ablation D0.9, 9 cấu hình × 2 hướng — **blocker B4** | D3.5 + TD-0041 (B6) |
| D9.5 | Lockbox chạm **đúng một lần** | D9 |
| D10–D12 | Testnet quy mô đầy đủ → dry-run → live vốn nhỏ | D9.5 |

---

## Lịch sử thay đổi checklist

| Mã việc | Loại | Nội dung cũ | Nội dung mới | Lý do | Ngày |
|---|---|---|---|---|---|
| TD-0001…TD-0086 | ➕ Thêm mới | — | Khởi tạo backlog D0-PRE, 9 khối, 41 việc | Cuối Giai đoạn 2 của quy trình vibe-code | 06/09/2026 |
| TD-0006, TD-0007 | ➕ Thêm mới | — | Hai việc xử lý `dashboard-ui/` và file HTML thiết kế | Hai thứ này xuất hiện trong thư mục project trong lúc khởi tạo repo, do một tiến trình khác ghi vào — không nằm trong phạm vi đã chốt ở Giai đoạn 1 | 06/09/2026 |
| TD-0001, TD-0002 | ♻️ Sửa đổi | 🔓 | ✅ | Đã hoàn thành trong cùng buổi khởi tạo | 06/09/2026 |
| TD-0007 | ♻️ Sửa đổi | 🔓 | ✅ | Chủ dự án chọn phương án "chuyển vào docs/" trong 3 phương án đề xuất | 06/09/2026 |
| TD-0003 | ♻️ Sửa đổi | 🔓 | ✅ | Chủ dự án cung cấp link repo GitHub, đã thêm remote `origin` và push thành công | 06/09/2026 |
| TD-0018 | ♻️ Sửa đổi | 🔓 | ✅ | Nối `assert_cache_none()` (đã có sẵn ở `gates/cache_policy.py`) vào `main()` của E1 ngay sau `measurement_guard()`; thêm `tests/unit/test_run_backtest_cache.py` (3 ca, gọi E1 qua subprocess vì `entrypoints/` không nằm trên `pythonpath`) | 06/09/2026 |
| TD-0006 | ♻️ Sửa đổi | 🔓 | ✅ | Chủ dự án chọn phương án "repo riêng" trong 3 phương án đề xuất (submodule / repo riêng / gộp thẳng) — lúc này `dashboard-ui/` đã có nội dung thật (8 trang dashboard Tool A/D dựng trên horizon-ui-chakra), không còn là thư mục rỗng. Đã gỡ remote `origin` cũ (trỏ về repo gốc `horizon-ui/horizon-ui-chakra`, nguy cơ push nhầm), chủ dự án cấp link `github.com/nhanle1153/front-end-trading-tool-smart-dca`, đã thêm remote và push `main` thành công | 06/09/2026 |
| TD-0020 | ♻️ Sửa đổi | Cột verify: `docker compose run --rm tests tests/lock -k "lz3[6-9] or lz4[01]"` | Cột verify: liệt kê trực tiếp đường dẫn 6 file test (xem dòng TD-0020) | Lệnh gốc có hai lỗi kỹ thuật, phát hiện lúc chạy thật: (1) `pytest -k` không hỗ trợ character-class regex `[6-9]`/`[01]` — chỉ khớp chuỗi con văn bản, nên biểu thức gốc chọn được **0/79** test kể cả các L-Z đang tồn tại; (2) giới hạn đường dẫn `tests/lock` bỏ sót L-Z38 (TD-0018) — test của nó nằm ở `tests/unit/test_run_backtest_cache.py` (hợp lý vì nó gọi E1 qua subprocess, không phải kiểm tĩnh) và tên hàm/class không chứa chuỗi "lz38" nên không `-k` nào chọn được. Sửa bằng cách liệt kê thẳng 6 đường dẫn file, không phụ thuộc keyword. Không đổi vị trí file của TD-0018 — đó là quyết định hợp lý của người viết, chỉ sửa cách gọi ở cổng | 06/09/2026 |
| TD-0094 | ♻️ Sửa đổi | Nội dung: "E1/E2/E7 (backtest/WFO/ablation)" | Nội dung: "E1/E2/E3 (backtest/WFO/ablation)" | Sai số entrypoint lúc viết task — `E7` thật ra là `entrypoints/build_pool.py` (không liên quan), ablation là `entrypoints/run_ablation.py` = `E3` (`ENTRYPOINT = "E3"`, xác nhận trực tiếp trong file). Phát hiện lúc đọc lại trước khi khoá task để code | 07/09/2026 |
| TD-0094 | ♻️ Sửa đổi | "tự cưỡng chế cận trên timerange" ở E1/E2/E3, verify đòi "entrypoint từ chối chạy" | Thu hẹp phạm vi: nối T0-T3 với `assert_dataset_timerange()` (L-Z55) đã có sẵn, KHÔNG viết cơ chế song song mới; verify đổi thành `pytest -k timerange` + ghi rõ E1/E2/E3 chưa có bước tải dữ liệu thật để nối self-check vào | Lúc bắt tay viết mới phát hiện E1/E2/E3 (Khối 1, TD-0016) chỉ là khung guard, rơi thẳng xuống `NotImplementedError` — không có dataframe nào đã tải để mà kiểm `observed_start/end`. Viết một hàm mới chỉ kiểm chuỗi `--timerange` yêu cầu (chưa kiểm dữ liệu THẬT đã tải) sẽ là cơ chế yếu hơn `assert_dataset_timerange()` đã có sẵn từ trước (L-Z55) — đúng loại lỗi "hai nguồn sự thật" MT-03/MT-08 đã cảnh báo. Không đóng giả một wiring chưa có chỗ để nối | 07/09/2026 |
