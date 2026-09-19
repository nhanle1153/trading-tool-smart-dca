# DR-D1-04 — H14: đo overlap rổ T1 với pool Tool A, chụp số trial Tool A TẠI LÚC ĐO, áp DR-007 máy móc

> **Ngày chốt:** 19/09/2026 · **Người quyết:** chủ dự án (xác nhận thư mục Tool A và duyệt chạy phép đo, phiên mã `69768527`)
> **Chi phí:** **0 trial**, không đọc dữ liệu thị trường. **Commit TRƯỚC phép đo** (yêu cầu 17/09 ở `TD-0261`).
> Mã `DR-D1-04` giữ từ 17/09 ở `back-end-note.md` MT-56 (`d092d43`). `DR-D4-18` (đặt chỗ trùng, `5536b07`) đã rút ở `62bcc80`.

> 🔴 **PHIÊN SINH Ý TƯỞNG (IDEA) VÀ PHIÊN CHỌN KHÔNG ĐỌC FILE NÀY** (`DR-009`).

---

## 1. Chỗ va, ghi theo quy tắc 11

| Quyết định cũ | Chữ đang có | DR này đổi gì |
|---|---|---|
| `DR-IQ-01` §1 (17/09) | `TD-0261` ⏸ cùng Khối 20–22 | **Gỡ ⏸ CHỈ `TD-0261`**. Mọi ⏸ khác đứng nguyên. Khoá đo D4 (`D4_DO_TAM_DUNG = True`) **không đổi** |
| Spec `:4268` | N gộp lấy từ sổ Tool A *"tại thời điểm chạy GATE"* | Chụp **tại lúc đo overlap** (chủ dự án chốt 17/09, `MT-56`), để cổng D4 tái lập được. Chiều trôi của chữ spec là fail-safe (N chỉ tăng); bản chụp thì mất tính fail-safe đó, đổi lấy tái lập |
| `DR-D6D8-01` D6.1 | *"chốt N của D9"* | Đã đính chính 17/09: đây là đầu vào **cổng D4**. DR này đo cho cổng D4 trên rổ D4 dùng. D9 dùng lại con số khi rổ không đổi |

## 2. Định nghĩa, chốt TRƯỚC khi thấy con số

| Thứ | Định nghĩa | Vì sao |
|---|---|---|
| **Tool_D_pool** | `config/pool_t1.yaml` khoá `trading` (107 mã, `TD-0247`, mốc T1) | Rổ mà D4 đo trên WFO (`ro_cho_tap("WFO")`). **Không** dùng `pool.yaml` (ảnh chụp 09/2026, `DR-D1-02` §6) |
| **Tool_A_pool** | `exchange.pair_whitelist` của `tool-a/config.json` trong repo Tool A (`pairlists` = `StaticPairList`, tức chính danh sách đang chạy) | Chủ dự án chỉ đường dẫn 19/09. **Không** dùng ảnh chụp dashboard 31/08 (40 mã, tự ghi *"chưa đọc được whitelist đang chạy"*) |
| **Quy đổi mã** | Tool A `BASE/USDT:USDT` → `BASEUSDT`, so **đúng từng ký tự**. Mã Tool A không khớp `^[A-Z0-9]+/USDT:USDT$`, hoặc mã Tool D không khớp `^[A-Z0-9]+USDT$` ⇒ **từ chối đo** | `1000PEPE` và `PEPE` là hai hợp đồng khác nhau, không ghép. Pairlist động thay cho `StaticPairList` ⇒ cũng từ chối, vì whitelist tĩnh khi đó không phải pool thật |
| **overlap** | `\|A ∩ D\| / \|A ∪ D\|` (Jaccard, spec `:341`) | Chữ spec. Artifact ghi thêm `\|A\|`, `\|D\|`, `\|A ∩ D\|` và danh sách giao để tính lại được. **Không** dùng tỉ số nào khác để quyết |
| **Ngưỡng** | `overlap ≥ 0,50` ⇒ DR-007 áp dụng | `MT-50` chốt `≥` (17/09). Đúng 50,0% cũng gộp |
| **N_A** | `project_dsr_denominator(registry).total` gọi **chính hàm của Tool A** (`lib/trial_registry/dsr_trial_count.py`) trên `logs/trials/trial_registry.json` | Đó là mẫu số DSR Tool A tự dùng: cộng `n_arms_counted_for_dsr`, trial chưa khai tính 1 và nêu tên. Viết lại hàm bên Tool D sẽ tạo nguồn sự thật thứ hai |
| **N gộp** | `N_union = N_ĐĂNG_KÝ + N_A = 114 + N_A`; rào mới = `dsr_hurdle(N_union)` = `√(2·ln N_union)` | *"N là UNION với Tool A"*: hai sổ trial không giao nhau nên hợp là tổng. Tool D giữ mẫu số **đã đăng ký** (`DR-010`/`DR-D0PRE-02`), không đổi sang số đã tiêu |
| **Xuất xứ** | Artifact ghi git SHA repo Tool A + cây sạch hay không ở hai file đọc, `sha256` của `tool-a/config.json`, `trial_registry.json`, `dsr_trial_count.py`, `config/pool_t1.yaml`, git SHA Tool D, giờ chụp UTC | Bản chụp phải tái lập được (lý do của `MT-56`). File Tool A đang sửa dở ⇒ **từ chối đo**, không chụp một trạng thái chưa commit |

## 3. Kết cục, áp máy móc

- **overlap < 0,50:** DSR tách. N của cổng D4 giữ **114**, rào **3,0777**. Ghi research-log.
- **overlap ≥ 0,50:** DR-007 áp dụng. N của cổng D4 = `114 + N_A`. Artifact **liệt kê đích danh** mọi DR trong
  `docs/decisions/` mang rào `3,0777` (quét chuỗi tại lúc đo; 17/09 đếm được 11). Đó là những DR **phải đọc lại con số**.
  Không được coi *"quyết định không đổi nên DR vẫn đúng"* (yêu cầu ở `TD-0261`).
- **Cả hai trường hợp:** **không** đổi tiêu chí pool, **không** chọn lại rổ (spec `:346`: *"KHÔNG được chọn lại pool sau khi
  thấy overlap cao"*).

## 4. Không thuộc DR này

- **Nối N gộp vào mã** (`gates/dsr.py` `N_DANG_KY`, `effective_n`, cổng D4 `close_d4_gate`, `DR-D9-01`) là việc riêng. Trình
  chủ dự án ở lần *"chuẩn hóa và lưu"* tới, sau khi có con số. DR này **chỉ đo và ghi**.
- **Sổ trial Tool D không có dòng nào.** Phép đo chỉ đọc hai danh sách mã và một số đếm, không đọc nến, không đánh giá cấu
  hình nào. Theo `DR-014` §2 thì không "chạm", cùng hạng với việc dựng rổ `TD-0247` (0 trial).
- **Repo Tool A chỉ ĐỌC**, gắn vào container ở chế độ `:ro`.
- **H14 đo lại hằng tháng** (spec `:2855`, `:4346`) là giám sát, không thuộc lần chụp này.

## 5. Chạy (N7)

```
MSYS_NO_PATHCONV=1 docker compose -f docker/docker-compose.yml run --rm \
  -v "<thư mục Tool A>:/tool_a:ro" freqtrade docs/du-lieu-do/do_td0261_overlap_tool_a.py --tool-a /tool_a
```

Artifact: `docs/du-lieu-do/td0261-overlap-tool-a.json`. Có sẵn ⇒ từ chối ghi đè.
