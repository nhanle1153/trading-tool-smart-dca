# DR-D10-02 — Bộ chạy D10: lệnh live tối thiểu trên tài khoản phụ

> **Trạng thái: ✅ CHỐT 25/09/2026** — chủ dự án (Q1–Q5 trả lời 24/09, Q6 + trần ký quỹ 50% + duyệt chốt 25/09;
> soạn bởi phiên mã `dd89043d`). Hai bản NHÁP trước (`b88d692`, `8074550`) giữ trong lịch sử git.
> Commit CHỐT này là commit **RIÊNG, TRƯỚC** mọi dòng mã của bộ chạy D10 (`TD-0384`/`TD-0385`) — kiểm bằng
> `git merge-base --is-ancestor`, không bằng mắt.
> **Chi phí:** 0 trial. Mọi vị thế D10 là CTRL (`DR-D11-01` §4). Tiền thật: phí + trượt giá + rủi ro vị thế nhỏ.

---

## 0. Vì sao cần DR này

`DR-D11-01` đã chốt D10 **đo gì** (ba ngưỡng §5: D6 lệch khớp · D2c `gap_ms` · tỉ lệ khớp post-only), **ở đâu**
(lệnh live tối thiểu, không testnet) và **tốn bao nhiêu** (≤ 20 vị thế tuần tự, 14 ngày + gia hạn đúng 1 lần). Nó để
ngỏ **cách chạy**: `DR-D11-01` §4 viết *"cơ chế kỹ thuật để đẩy một vị thế qua tranche 2/3 … không chốt ở đây"*.
Hôm nay repo không có dòng mã nào đặt lệnh thật: `ops/dry_run.py` từ chối mọi cấu hình `dry_run ≠ true`, và
`validate_credentials_for_live()` (TD-0242) chưa được gọi ở đâu.

Chủ dự án xác nhận 24/09/2026: tài khoản phụ **đã có**, đã siết IP whitelist và tắt Universal Transfer (`DR-D11-01` §3).

🔴 **D10 đo MÁY, không đo chiến lược** (đính chính cùng ngày, `MT-78`). Bản nháp đầu viết *"arm sản xuất là `Z3` ⇒ D2c còn
sống"* và đề xuất chạy chính `ZoneAbsorption` — **sai tiền đề**: `DR-ZA-01` (21/09) đã bác bỏ ZA LONG ở cấu hình này,
và `DR-HUONG-01` + chủ dự án (24/09) chọn tìm chiến lược MỚI qua suất (d), không đưa ZA lên tiền thật. Chiến lược sẽ
lên tiền thật **chưa tồn tại**. Vì vậy D10 đo hạ tầng lệnh bằng lệnh **CTRL trung tính**: SL sống trên sàn, `gap_ms`
khi đổi khối lượng SL, post-only có khớp hay bị từ chối, trượt giá khớp. Không phụ thuộc chiến lược nào (Q1 bên dưới).
Phiên sinh bản nháp đầu đã bỏ sót `DR-ZA-01`; phiên mã `12c579bc` bắt được.

## 1. Điều đã chốt ở chỗ khác — DR này KHÔNG mở lại

- Ba ngưỡng PASS/FAIL và cách đọc: `DR-D11-01` §5 (bản gốc). Không số mới.
- Ngân sách: ≤ 20 vị thế, tuần tự, dừng sớm khi đủ ≥ 30 sự kiện đổi khối lượng SL; 14 ngày + gia hạn 1 lần; hết
  hạn thiếu mẫu ⇒ báo `n < 30`, không ép thêm (`DR-D11-01` §4).
- SL sống trên sàn, `gap_ms` đo bằng mẫu cưỡng bức, hạn chế tồn dư phải đọc kèm (`DR-D11-02` §3).
- D10 PASS là điều kiện của **D12**, không của D11 (`DR-TRIEN-KHAI-01` §1).
- Không entrypoint thứ 9 (`L-Z36`); không đọc tham số chiến lược từ env (N3/N4).

## 2. Phần kỹ thuật (không có đánh đổi kinh doanh; chốt cùng DR)

1. **Module vận hành riêng `src/tool_d/ops/live_d10.py`**, cùng khuôn `ops/dry_run.py`: đọc
   `config/freqtrade/config.json`, PHỦ `dry_run: false`, `db_url` live RIÊNG
   (`sqlite:////workspace/user_data/tradesv3_live_d10.sqlite`, N11), `bot_name`, rổ CTRL nhỏ (Q4), chiến lược **CTRL
   riêng** `user_data/strategies/CtrlD10.py` (không phải `ZoneAbsorption`, Q1), rồi `exec freqtrade trade`.
   Key chỉ qua biến môi trường (`FREQTRADE__EXCHANGE__KEY/SECRET`), không bao giờ ghi vào bản phủ.
2. **`validate_credentials_for_live()` gọi ở `main()`** của module đó + phép kiểm AST vị trí gọi (nợ đã khai ở dòng
   `D10–D12` của `TASKS.md`: allow-list "nằm trong `main`", không deny-list tên callback).
3. **Service `live-d10` + `live-d10-watchdog` + `risk-supervisor`** sau profile riêng `d10` (không chung profile
   `van_hanh` với dry-run để `up` nhầm không bật tiền thật), đều che `lockbox/data/`. `live-d10` **KHÔNG** có
   `restart: unless-stopped` (Q6) — khác hẳn dry-run. Heartbeat/đỉnh equity đã tách
   theo runmode (TD-0350/TD-0353) ⇒ chạy song song dry-run không ghi đè nhau.
4. **Máy canh ngân sách, fail-closed, đọc từ DB live** (không đếm trong RAM — sống qua restart, bài học MT-40):
   vị thế thứ 21 · vị thế thứ hai khi một vị thế đang mở (tuần tự) · quá hạn cửa sổ · **tổng ký quỹ đang mở sau lệnh
   này > 50% số dư** (Q2) · không đọc được số dư (N6) ⇒ `confirm_trade_entry` từ chối.
5. **Bộ đo ba ngưỡng** đọc DB live + sổ Decision Log của runmode `live` (bản ghi `DOI_SL` của TD-0244; đường theo
   runmode, việc tách sổ mở 24/09), ghi `docs/du-lieu-do/d10-*.json`. D6 trên CTRL chỉ báo trượt giá bps, không so
   với Δ_R (Q1, hạn chế).
6. **Mỗi vị thế một dòng CTRL** trong sổ trial. Cửa CTRL hôm nay nhận ba dạng (tái lập · đo thước ·
   `CTRL_OUTPUT_ALLOWED`); vị thế D10 **không khớp dạng nào** ⇒ cần thêm một dạng thứ tư "đo cơ chế vận hành" với
   danh sách đầu ra CHO PHÉP riêng (`fill_price`, `p_i`, `gap_ms`, `order_status`) — theo tiền lệ `MT-19` dạng thứ
   ba: thêm tên = DR mới, và DR đó chính là DR này.

## 3. Quyết định của chủ dự án

### Q1 — Vị thế D10 sinh ra từ đâu? ✅ ĐÃ CHỐT 24/09/2026 (chủ dự án, phiên mã `dd89043d`)

**Lệnh CTRL trung tính:** một chế độ đặt lệnh có chủ đích, gồm tranche 1 rồi tranche 2/3 đặt sát giá thị trường, trên
vài cặp thanh khoản cao, không đọc tín hiệu của chiến lược nào. Đủ 30 sự kiện đổi khối lượng SL trong vài ngày thay vì
hàng tháng. Bảng `DR-D11-02` §3.2 cho phép: `gap_ms` đo hành vi CỦA MÁY, và máy không phân biệt tranche thật hay cưỡng
bức. Các phương án chạy `ZoneAbsorption` (A, C của bản đầu) **bị loại** theo `DR-ZA-01`.

🔴 **Hạn chế, phải đọc kèm mọi kết luận D10:**
- **D6** (`DR-D11-01` §5.1) đo lệch khớp **theo R của một kế hoạch zone** (`(fill − p_i) / planned_risk`). Lệnh CTRL không
  có kế hoạch zone nên con số đó **không đo đúng nghĩa**. Trên CTRL chỉ báo được trượt giá theo bps. So với Δ_R niêm
  phong thì phải đợi có chiến lược suất (d).
- **Post-only** trên lệnh sát giá có thể bị từ chối **nhiều hơn** lệnh chờ ở zone xa giá, tức lệch về phía bất lợi.
  Chiều lệch này an toàn, nhưng không phải tỉ lệ của chiến lược.
- **D10 PASS trên CTRL chỉ chứng nhận HẠ TẦNG** (SL trên sàn, huỷ và đặt lại, key, bảo mật, giám sát). Nó không chứng
  nhận chiến lược nào. Cổng D12 (`DR-TRIEN-KHAI-01` §3 điều 2) đòi D10 PASS theo cả ba ngưỡng, kể cả D6 ⇒ D6 phải đo
  lại trên chiến lược suất (d) trước D12. Chưa có phần nào của D10 CTRL thay được bước đó.

### Q2 — Cỡ lệnh ✅ ĐÃ CHỐT 24/09/2026 (chủ dự án: tài khoản phụ có **100–300 USDT**)

Cỡ lệnh **không** đi qua `E_D`/`rho` của chiến lược (Q1 là CTRL). Mỗi tranche = **sàn Tool D của cặp đó**
(`san_tool_d()`, `DR-D4-05`) cộng một lề nhỏ, tức rẻ nhất có thể mà vẫn qua sàn (~30 USDT notional ở vài mã).
Với đòn bẩy 3x, ký quỹ mỗi tranche ≈ notional/3 ≈ 10 USDT ⇒ 20 vị thế **tuần tự** (Q1) vừa vốn 100–300 USDT, không đòi
vốn lớn nằm sẵn. ✅ **Trần phụ (chủ dự án chốt 25/09): tổng ký quỹ đang mở ≤ 50% số dư** — với 100–300 USDT là
50–150 USDT, giữ nửa còn lại làm đệm chống thanh lý.
Số dư tối thiểu để mở D10: ≥ 100 USDT (đúng cận dưới câu trả lời).

### Q3 — Máy kiểm bảo mật tài khoản trước mỗi lần khởi động ✅ ĐÃ CHỐT 24/09/2026: **CÓ máy kiểm**

Gọi `GET /sapi/v1/account/apiRestrictions` và **từ chối chạy** nếu `ipRestrict = false` hoặc quyền rút / chuyển nội bộ
đang bật. 🔴 **Hệ quả bắt buộc:** đây là một **endpoint ngoài mới** ⇒ theo quy tắc 12/17 của `CLAUDE.md`, phải điền
`api-integration-rules.md` **Mục 4** (dòng danh sách dịch vụ, bảng endpoint, bảng mã lỗi, ngưỡng, R1–R12) **TRƯỚC** khi
cho phép "bắt đầu code" phần này. Chưa làm — mã việc đặt chỗ khi mở.

### Q4 — Dry-run D11 và live D10 chung một IP ✅ ĐÃ CHỐT 24/09/2026: **rổ D10 nhỏ ≤ 10 cặp**

Dry-run giữ nguyên (~100 cặp, chạy liên tục). D10 chỉ theo dõi ≤ 10 cặp thanh khoản cao ⇒ ít tốn giới hạn API dùng chung.
D10 dùng **bot Telegram RIÊNG với token RIÊNG** (hai Freqtrade chung một token tranh `getUpdates`, lỗi 409 — đã ghi ở
`TD-0393`) và quyết riêng có cho nút điều khiển (`/stop`, `/forceexit`) hay không. Chưa đo được tần suất gọi API thực tế của
cả hai chạy cùng lúc: đọc log D10 đầu tiên, nếu gặp 429/418 thì dừng D10 và trình chủ dự án.

### Q5 — Hết ngân sách mà D2c vẫn `n < 30` ✅ ĐÃ CHỐT 24/09/2026: **D10 coi như CHƯA ĐẠT**

`DR-D11-01` §5.2 đã nói: báo p99 trên N thực, ghi hạn chế. Chốt thêm: `n < 30` sau khi hết ngân sách ⇒ **D10 chưa PASS ⇒
D12 không được mở**; muốn mở phải có **DR mới gia hạn ngân sách**, viết trước khi thấy số (tránh uốn luật).

### Q6 — Ai bấm nút ✅ ĐÃ CHỐT 25/09/2026: **BẬT BẰNG TAY MỖI PHIÊN**

Bộ chạy D10 **không tự bật**: không nằm trong `docker compose up` mặc định, không có `restart: unless-stopped`. Chủ dự án
gõ lệnh bật profile `d10` mỗi phiên. Hệ quả chấp nhận có ý thức: máy hoặc Docker khởi động lại ⇒ D10 **dừng** và không tự
chạy lại; lệnh đang mở vẫn có SL sống trên sàn (`stoploss_on_exchange`, `DR-D11-02`); watchdog D10 báo 🔴. Đổi lại, một
lần khởi động lại máy không bao giờ âm thầm bật bot tiền thật. Telegram báo mỗi vị thế mở/đóng qua bot RIÊNG của D10 (Q4).

## 4. Thi hành

Mã việc đặt chỗ ở Khối 31 `TASKS.md`. Thứ tự: DR này (commit riêng) → `api-integration-rules.md` Mục 4 (Q3 = có ⇒ bắt buộc)
→ bộ chạy + máy canh ngân sách + dạng CTRL thứ tư → bộ đo ba ngưỡng → chạy thật. Không đặt lệnh thật nào trước khi
đủ bốn bước đầu và full suite Docker xanh.
