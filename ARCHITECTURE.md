# ARCHITECTURE.md — Tool D (Smart DCA)

> Tạo ở Giai đoạn 2 của quy trình vibe-code, ngày 06/09/2026.
> Nguồn sự thật kỹ thuật: `tool-d-smart-dca.md` (v8). File này mô tả **cách tổ chức mã nguồn**,
> không chép lại nội dung chiến lược.
> Xem sơ đồ Mermaid bằng `Ctrl+K V` trong VS Code.

---

## 1. Ý tưởng kiến trúc trong một câu

Tool D không phải "một con bot". Nó là **một cái cân và một cuốn sổ**, bên trong có một con bot.

Cái cân (PHẦN 0d — toàn vẹn phép đo) đảm bảo mọi con số sinh ra là thật.
Cuốn sổ (PHẦN 9c — quản trị phép thử) đảm bảo ta không thử quá nhiều lần rồi tự lừa mình bằng
cấu hình may mắn nhất. Con bot (Freqtrade strategy) chỉ là thứ được cân — và nó **chưa được viết**.

Hệ quả kiến trúc: **cân và sổ phải hoạt động trước, và phải chặn được con bot khi chúng chưa sẵn sàng.**

---

## 2. Sơ đồ tổng thể

```mermaid
flowchart TD
    subgraph CFG["Nguồn sự thật cấu hình"]
        YAML["config/tool_d_config.yaml<br/>NGUỒN DUY NHẤT cho tham số"]
        DOF["config/dof_inventory.yaml<br/>bảng bậc tự do"]
        FTC["config/freqtrade/config.json"]
    end

    subgraph GUARD["Tầng chống nhiễm — PHẦN 0d"]
        MG["measurement_guard()<br/>quét file tham số ẩn + env lạ"]
        PROV["provenance<br/>7+1 khoá xuất xứ"]
        TRI["Measured[T]<br/>pending / unreadable / ok"]
        CACHE["assert_cache_none()"]
    end

    subgraph LEDGER["Sổ sách — PHẦN 9c"]
        REG["trial_registry.jsonl<br/>SỔ NHẬT KÝ SỰ KIỆN, append-only"]
        PROJ["bản chiếu trạng thái<br/>RESERVED / CONSUMED / REFUNDED"]
        IQ["idea_queue.jsonl"]
        PCP["param_change_proposals.jsonl<br/>đề xuất đổi tham số, L-Z26"]
        LB["lockbox/<br/>seal + sổ truy cập"]
    end

    subgraph EP["8 entrypoint — DANH SÁCH ĐÓNG"]
        E1["E1 run_backtest"]
        E2["E2 run_wfo"]
        E3["E3 run_ablation"]
        E4["E4 touch_lockbox"]
        E5["E5 periodic_report"]
        E6["E6 trial_ledger_audit"]
        E7["E7 build_pool"]
        E8["E8 backfill_data"]
    end

    subgraph GATE["Cổng đánh giá"]
        TH["thresholds<br/>chưa điền = +inf"]
        DSR["dsr_hurdle(N)<br/>N đọc từ registry"]
    end

    STRAT["user_data/strategies/<br/>🔴 RỖNG ở D0-PRE"]
    DATA[("user_data/data/<br/>CALIB · WFO")]
    LBDATA[("lockbox/data/<br/>chạm ĐÚNG MỘT LẦN")]

    YAML --> MG
    DOF --> LEDGER
    EP --> MG
    MG --> PROV
    MG -->|phát hiện file ẩn| STOP["🛑 exit 86<br/>in nội dung, KHÔNG tự xoá"]
    E1 & E2 & E3 --> E6
    E6 --> LEDGER
    E1 & E2 & E3 --> CACHE
    E1 & E2 & E3 -->|reserve → seal → consume| REG
    REG --> PROJ
    PROJ -->|Khả dụng < contribution| REFUSE["🛑 TỪ CHỐI CHẠY"]
    PROV --> REG
    E1 & E2 & E3 -.->|CHỈ SAU cổng D0-PRE| DATA
    E4 -->|sau D9| LBDATA
    E4 --> LB
    E5 --> TRI
    TRI --> RPT["báo cáo định kỳ<br/>không giá trị lính canh"]
    REG --> DSR
    DSR --> TH
    FTC --> STRAT

    style STOP fill:#c0392b,color:#fff
    style REFUSE fill:#c0392b,color:#fff
    style STRAT fill:#7f8c8d,color:#fff
    style LBDATA fill:#8e44ad,color:#fff
```

---

## 3. Cây thư mục và lý do

```
tool-d-smart-dca/                  ← git root = E:\Trading Tool_Smart DCA
├─ tool-d-smart-dca.md             ← 🔴 SPEC v8, NGUỒN SỰ THẬT, chỉ đọc
├─ CLAUDE.md  ARCHITECTURE.md  TASKS.md  back-end-note.md
├─ template/                       ← khuôn mẫu quy trình, CHỈ ĐỌC
├─ .gitattributes                  ← ép LF (xem 3.2)
├─ docs/
│  ├─ research-log.md              ← append-only (§0d.7)
│  ├─ freqtrade-source-read.md     ← đọc mã nguồn Freqtrade cho D2a/D2b/D6/D7
│  ├─ decisions/DR-D0PRE-*.md
│  └─ tool-d-dashboard-thiet-ke.html ← ảnh chụp giao diện Tool A, dùng tham
│                                      chiếu khi code UI dashboard (TD-0007)
├─ config/
│  ├─ tool_d_config.yaml           ← §6.9.5 — NGUỒN SỰ THẬT tham số
│  ├─ dof_inventory.yaml           ← nuôi L-Z29
│  └─ freqtrade/config.json
├─ user_data/strategies/           ← RỖNG ở D0-PRE. Guard canh đúng thư mục này
├─ user_data/data/                 ← CALIB · WFO (gitignored)
├─ lockbox/                        ← NGOÀI user_data (xem 3.1)
├─ registry/                       ← trial_registry.jsonl · idea_queue.jsonl ·
│                                    param_change_proposals.jsonl · runtime_state.json
│  └─ schemas/                     ← NGUỒN SỰ THẬT hình dạng 3 sổ (xem mục 7)
├─ src/tool_d/
│  ├─ measurement/  guard · provenance · tri_state · hashing · gitinfo
│  ├─ config/       loader · dof
│  ├─ ledger/       registry · budget · audit_checks · idea_queue · param_proposals
│  ├─ lockbox/      seal · access_log
│  ├─ gates/        thresholds · dsr
│  └─ reporting/    report_model
├─ entrypoints/                    ← ĐÚNG 8 file, không hơn (xem 3.3)
├─ tests/lock/                     ← 1 file / 1 test khoá L-Zxx
├─ tests/unit/  tests/fixtures/
├─ runs/                           ← runs/<trial_id>/metrics.seal (gitignored)
└─ docker/                         ← Dockerfile · docker-compose.yml
```

### 3.1. Vì sao `lockbox/` nằm ngoài `user_data/`

DR-011 (spec dòng 3309) yêu cầu vậy. Nhưng lý do thực dụng hơn: nó cho phép `docker-compose.yml`
**không mount** thư mục này vào service backtest thường. Việc đó biến "không được chạm" từ một
điều luật thành *không chạm được ở tầng hệ điều hành*. Spec tự thừa nhận cơ chế lockbox chỉ là
kỷ luật, không cứng (dòng 3317–3320) — đây là chỗ duy nhất siết thêm được một bậc mà không tốn gì.

### 3.2. Vì sao ép LF trong `.gitattributes`

Host là Windows, môi trường sinh số là container Linux. Ràng buộc 0d.5 đòi `data_hashes` là
SHA-256 từng file. Nếu git checkout CRLF thì **cùng một file cho hai hash khác nhau** tuỳ nơi đọc,
và `reproducible_from_sha` trở thành nhiễu. Đây là lỗi lặng — phải chặn ở tầng repo.

### 3.3. Vì sao `entrypoints/` là một thư mục phẳng riêng

§0d.2 (dòng 649–666) đòi một **danh sách đóng** các đường sinh số liệu. Một thư mục *chính là*
danh sách đó, và test L-Z36 kiểm được máy móc: `set(entrypoints/*.py) == {E1..E8}`.
Nếu rải entrypoint trong `src/` thì test này không viết được.

Spec ghi rõ: *"Không có E9 script thử nghiệm nhanh. Nếu cần xem thử, đó là E1 với
`budget_line = B3` và ghi registry"* (dòng 664–665). Vì vậy **sự vắng mặt của
`scripts/quick_test.py` hay `notebooks/` là một quyết định kiến trúc**, không phải thiếu sót.

### 3.4. Vì sao `registry/` tách khỏi `user_data/`

Freqtrade ghi và dọn trong `user_data`. Sổ append-only đời dài không được nằm chung một
đường sinh-xoá với thứ mà framework tự quản lý.

---

## 4. Ba bất biến kiến trúc

Ba điều này đúng ở mọi thời điểm, và có test canh:

1. **Không có đường vòng qua guard.** Mọi đường sinh số liệu đi qua đúng 8 cửa, mỗi cửa gọi
   `measurement_guard()` ở dòng đầu tiên sau parse tham số. Canh bằng L-Z36 (kiểm bằng AST,
   không phải grep — và **cấm bọc guard trong decorator** vì decorator làm test phải suy luận
   và dễ PASS giả).
2. **Không có con số không rõ xuất xứ.** Mọi bản ghi kết quả mang khối xuất xứ 7+1 khoá.
   Thiếu một khoá → bản ghi **không hợp lệ cho gate**. Canh bằng L-Z40.
3. **Không có gate vô tình PASS.** Ngưỡng chưa điền = `+inf`, không phải `None`, không phải `0.0`.
   Canh bằng L-Z35, kèm phép thử "kết quả tốt nhất hiện có vẫn phải FAIL".

---

## 5. Luồng một lần chạy (sau khi D0-PRE đóng)

```mermaid
sequenceDiagram
    participant U as Người dùng
    participant E1 as E1 run_backtest
    participant G as measurement_guard
    participant A as E6 audit sổ
    participant L as Sổ trial
    participant F as Freqtrade

    U->>E1: chạy, kèm --cache none
    E1->>G: guard(entrypoint="E1")
    alt phát hiện file tham số ẩn
        G-->>U: 🛑 exit 86 + in nội dung file (KHÔNG xoá)
    end
    E1->>E1: assert_cache_none(argv)
    Note over E1: thiếu cờ → 🛑 exit 87, KHÔNG tự chèn
    E1->>A: run_audit(strict=True)
    A-->>E1: exit≠0 nếu sổ có vi phạm
    E1->>L: reserve(contribution=n)
    Note over L: Khả dụng < n → 🛑 TỪ CHỐI, chưa chạm dữ liệu
    E1->>F: backtesting
    F-->>E1: chỉ số đầu tiên vừa đọc được
    E1->>L: seal() — bộ chạy TỰ ghi, TRƯỚC cả khi in
    Note over L: từ đây không hoàn tác được nữa
    E1->>L: consume(outcome) — ghi ĐÚNG MỘT LẦN
    E1-->>U: kết quả + khối xuất xứ
```

Điểm đáng chú ý: **con dấu (`seal`) được đóng trước khi in kết quả**, không phải sau. Vì mốc
"đã tiêu một phép thử" là khoảnh khắc đầu tiên bất kỳ chỉ số nào trở nên đọc được (DR-014) —
nếu đóng dấu sau khi in thì người vận hành có một khoảng để nhìn kết quả rồi giết tiến trình
và giả vờ chưa từng chạy.

---

## 6. Ranh giới: cái gì được viết ở D0-PRE, cái gì không

| Được viết | Chưa được viết |
|---|---|
| Tầng chống nhiễm (`measurement/`) | Zone Detection Engine (PHẦN 1) |
| Sổ trial + lockbox (`ledger/`, `lockbox/`) | Kiến trúc tranche, gate DG1–DG8 |
| Loader cấu hình, kế toán DOF (`config/`) | Take-profit (PHẦN 5) |
| Ngưỡng gate fail-closed (`gates/`) | Risk Engine (PHẦN 6) |
| E5 báo cáo + E6 audit **đầy đủ** | Bất kỳ file nào trong `user_data/strategies/` |
| E1/E2/E3/E7/E8 dạng **khung từ chối chạy** | Bất kỳ lần chạy nào chạm CALIB/WFO/LOCKBOX |
| Test khoá không cần dữ liệu | Test khoá cần dữ liệu (L-Z1→9, 18→22, 30, 31, 43→50, 56→58) |

---

## 7. Sơ đồ quan hệ dữ liệu (ERD)

**Chưa có.** D0-PRE không tạo bảng cơ sở dữ liệu nào — sổ sách là JSONL append-only,
không phải DB quan hệ. `tu-dien-du-lieu.md` sẽ khởi tạo khi Freqtrade bắt đầu ghi SQLite lệnh
(sớm nhất là D3.5 testnet). Đây là quyết định có ý thức, không phải bỏ sót.

**Cập nhật 07/09/2026 (TD-0125) — đã có SỔ THỨ BA, quyết định hoãn vẫn giữ.**
`registry/param_change_proposals.jsonl` (đề xuất đổi tham số, §12c.3/§12d) nhập cùng
`trial_registry.jsonl` và `idea_queue.jsonl`. Chủ dự án chốt **giữ hoãn** `tu-dien-du-lieu.md`,
vì đợt này thêm một **sổ JSONL**, không thêm bảng CSDL nào — điều kiện kích hoạt ở đoạn trên
(Freqtrade ghi SQLite lệnh) vẫn chưa xảy ra.

🔑 **Nguồn sự thật hình dạng mỗi sổ là file JSON Schema trong `registry/schemas/`, không phải
một bảng chép tay trong `.md`.** Schema là thứ **máy đọc và cưỡng chế thật** (`jsonschema.validate`
ở cửa ghi, `additionalProperties: false`); một bảng .md song song sẽ là **nguồn sự thật thứ hai
cho cùng một hình dạng** — đúng cơ chế đã gây toàn bộ đợt lệch số của spec v5 và là bài học
**MT-03**. Ba schema hiện có:

| Sổ | Schema | Cưỡng chế bởi |
|---|---|---|
| `trial_registry.jsonl` | `trial_event.schema.json` | `ledger/registry.py` · L-Z10/11/12 · **TD-0130** (kế toán CTRL + cửa xác thực) |
| `idea_queue.jsonl` | `idea_queue_entry.schema.json` | `ledger/idea_queue.py` · L-Z16/17 · TD-0119a/b · TD-0120 · TD-0124 |
| `param_change_proposals.jsonl` | `param_change_proposal.schema.json` | `ledger/param_proposals.py` · **L-Z26** |

Khi `tu-dien-du-lieu.md` được khởi tạo ở D3.5, nó mô tả **bảng SQLite của Freqtrade** — và nếu có
mô tả cả ba sổ JSONL này thì phải **sinh/kiểm tự động từ schema**, không chép tay (xem TD-0126/0127
để biết cách đã dùng cho các ràng buộc chỉ nằm trong `description`).

---

## 8. Lịch sử thay đổi kiến trúc

| Ngày | Thay đổi | Sơ đồ/thiết kế cũ | Sơ đồ/thiết kế mới | Lý do |
|---|---|---|---|---|
| 06/09/2026 | Khởi tạo | — | Cây thư mục + 3 bất biến + luồng một lần chạy | Giai đoạn 2 của quy trình vibe-code |
| 07/09/2026 | Sổ thứ ba + hai cửa GHI | `LEDGER` có 2 sổ JSONL; `entrypoints/` 8 file, tất cả chỉ ĐỌC sổ | Thêm `param_change_proposals.jsonl` + `registry/schemas/` vào sơ đồ và cây thư mục; `ledger/` thêm `idea_queue` · `param_proposals`; mục 7 ghi rõ schema là nguồn sự thật hình dạng sổ | TD-0124 + TD-0125 (OQ-13): hai kênh nhập liệu có luật nhưng không có máy canh. 🔑 Cửa ghi đặt làm **cờ trên E6**, KHÔNG phải entrypoint thứ 9 — `entrypoints/` vẫn **đúng 8 file** (§0d.2 dòng 664, L-Z36). Phương án “CLI nằm ngoài `entrypoints/`” bị loại có ý thức: không vi phạm *chữ* của L-Z36 nhưng mở đúng lỗ hổng danh sách đóng tồn tại để bịt |
| 07/09/2026 | `trial_event.schema.json` biết thêm 2 trường **chỉ dành cho dòng CTRL**: `reproduces_trial_id` (dạng *tái lập*) và `ctrl_output_whitelist` (dạng *đo thước*, khai luôn danh sách CHO PHÉP + `minItems: 1` + `uniqueItems`) | Sự kiện RESERVE có 15 khoá; dòng CTRL không khai được vì sao nó được miễn kế toán | Thêm 2 khoá tuỳ chọn; lời khai CTRL nằm TRONG sổ để audit tự đối chiếu lại được | TD-0130 (MT-08): CTRL đứng ngoài ngân sách N nên *khai CTRL* là đặc quyền — không thể nhận lời khai suông. **Không thêm bảng CSDL nào** → quyết định hoãn `tu-dien-du-lieu.md` tới D3.5 **giữ nguyên**, nguồn sự thật vẫn là schema trên đĩa. Ràng buộc liên-dòng (hash khớp bản ghi gốc) cố ý **không** nhân đôi vào schema — nó ở cửa ghi, một chỗ |
