# TASKS.md — Backlog Tổng & Tracker Công việc — Tool D

> Khởi tạo cuối Giai đoạn 2, ngày 06/09/2026. Mã project: **TD**.
> Backlog này chỉ phủ **D0-PRE**. Các giai đoạn D1→D12 sẽ thêm việc khi tới lượt.
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
| TD-0041 | 🔴 **ĐIỀN ngưỡng DSR-adjusted expectancy §10.2 — blocker B6** (OQ-01). Viết DR **trước** khi biết kết quả lần đánh giá tiếp theo | 🔓 | TD-0040, TD-0033 | `DR-D0PRE-03` có SỐ; hằng số không còn `inf`; L-Z35 chuyển sang biến thể "best-known vẫn FAIL" và vẫn xanh |
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
| TD-0082 | Kiểm **min notional** từng cặp vs notional tranche 1 nhỏ nhất | 🔓 | TD-0043, TD-0079 | Bảng đối chiếu; có vi phạm → nâng `E_D` hoặc đặt sàn, ghi DR |
| TD-0083 | Chốt pool ~100 mã, loại BTC/ETH khỏi giao dịch, tách tập EXPLORE (OQ-04) | ✅ | TD-0079, TD-0056 | E7 chạy, ghi **4 trial B0** vào sổ; `pytest -k lz11` vẫn xanh |
| TD-0084 | Chia CALIB / WFO / LOCKBOX, kiểm 4 điều kiện DR-011, niêm phong `lockbox_seal_1.json` (OQ-05) | 🔓 | TD-0083, TD-0070 | `touch_lockbox.py --verify-seal` PASS; sổ truy cập vẫn **0 bản ghi** |
| TD-0085 | Thiết lập **backup lockbox ngoài git + test khôi phục thật một lần** (OQ-08) | 🔓 | TD-0084 | Khôi phục từ backup vào thư mục tạm → `verify_seal` PASS trên bản khôi phục |
| TD-0086 | 🚪 **GATE D0-PRE** — ghi `runtime_state.json.d0_pre_complete` từ **một lần chạy thật** | 🔓 | TD-0020…TD-0085 | `docker compose run --rm tests tests/lock` 0 failed **và** `trial_ledger_audit.py` exit 0 **và** `periodic_report.py` sạch → `git tag d0-pre-complete` |

---

## Việc đã biết là sẽ có, chưa mở

| Giai đoạn | Nội dung | Chặn bởi |
|---|---|---|
| D1 | H20, H1-D (pool point-in-time), H4-D (lookahead — **blocker B2**), H13, H19 | TD-0086 |
| D2 | Verify giả định D1–D7, H15. L-Z49 (D7) là điều kiện vào D4 | D1 |
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
