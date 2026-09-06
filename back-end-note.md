# back-end-note.md — Tool D (Smart DCA)

> **Đây là LỚP MỎNG.** Nguồn sự thật kỹ thuật là `tool-d-smart-dca.md` (v8, 5.419 dòng, ở gốc repo).
> File này chỉ giữ những thứ spec không có chỗ chứa: phạm vi Giai đoạn 1, quyết định nền tảng,
> Open Questions, Mâu thuẫn, và Lịch sử thay đổi. **Không chép nội dung spec vào đây** —
> chép thành hai bản là nguồn sinh mâu thuẫn số một (Nguyên tắc 10 của quy trình).
> Cập nhật theo Phụ lục B.5: nối thêm có ngày tháng, không ghi đè.

---

## 0. Phạm vi — Giai đoạn 1 [v1.0]

*Nội dung của `template/form-xac-dinh-pham-vi.md`, điền ngày 06/09/2026.*

| Trường | Nội dung |
|---|---|
| Tên project | Tool D — Smart DCA ngắn hạn (Zone Absorption) |
| Ngày xác định phạm vi | 06/09/2026 |
| Vấn đề cần giải quyết | Kiểm chứng có kỷ luật xem chiến lược "hấp thụ tại vùng giá" (Zone Absorption) triển khai theo tranche neo zone trên Binance USDⓈ-M Futures có kỳ vọng dương thật hay không. **Nếu không giải quyết:** rơi vào cái bẫy phổ biến nhất của giao dịch định lượng — thử đủ nhiều cấu hình thì kiểu gì cũng ra một bản backtest đẹp, rồi mất tiền thật vì con số đó chỉ là may mắn được tuyển chọn. |
| Đối tượng người dùng | Một người dùng duy nhất (chủ dự án). Không có nhiều vai trò. |
| Quy mô dự kiến | 1 người. ~100 cặp giao dịch trong pool. Ước lượng ≥150 lệnh/năm (SÀN — dưới ngưỡng này là hỏng từ thiết kế, xem §10.2). |

### 0.1. Danh sách chức năng theo ưu tiên

| Chức năng | Ưu tiên | Ghi chú |
|---|---|---|
| Hạ tầng toàn vẹn phép đo (PHẦN 0d) | **Phải có — TRƯỚC MỌI THỨ** | Không có nó thì mọi con số sinh ra sau đều vô nghĩa (spec dòng 521) |
| Sổ quản trị phép thử (DR-010/011/014) | **Phải có** | Ngân sách N=114, lockbox chạm đúng một lần |
| Cấu hình + tương thích Freqtrade (§0c) | **Phải có** | |
| Bộ test khoá L-Zxx | **Phải có** | Là cách duy nhất biết các ràng buộc còn sống |
| Zone Detection Engine (PHẦN 1) | Nên có — **sau cổng D0-PRE** | |
| Kiến trúc tranche + gate DG1–DG8 | Nên có — sau D0-PRE | |
| Risk Engine độc lập (PHẦN 6) | Nên có — sau D0-PRE | |
| Ablation D0.9 (PHẦN 10) | Nên có — D4, sau cổng D3.5 | |
| Live vốn nhỏ | Chưa cần — D12 | |

### 0.2. Quyết định nền tảng [v1.0]

| Hạng mục | Lựa chọn | Lý do |
|---|---|---|
| Ngôn ngữ/Framework | Python + **Freqtrade** | Spec §0c chỉ định. Dùng `adjust_trade_position` (cốt lõi tranche 2/3) và `custom_stoploss` |
| Môi trường chạy | **Docker Desktop** | Python host là 3.14, Freqtrade cần 3.11–3.13 và không hỗ trợ Windows native. Cũng thoả nguyên tắc 7 (parity) |
| Lưu trữ | **JSONL append-only** (`trial_registry`, `idea_queue`) + SQLite của Freqtrade cho lệnh | Sổ nghiên cứu cần append-only kiểm toán được, không cần DB quan hệ. **Không có ERD / từ điển dữ liệu ở D0-PRE** — chưa có bảng nào |
| Sàn | Binance USDⓈ-M Futures, isolated margin | §0.3 |
| Mã nguồn | Git local + GitHub **private** | Ràng buộc 0d.5 đòi `git_sha` trong mọi bản ghi kết quả |
| Hosting | **Không có.** Chạy local; live (D12) sẽ quyết sau | Bot giữ API key sàn, không hợp với PaaS công cộng |

### 0.3. Gate kiểm tra Giai đoạn 1

- [x] **Nhiều loại người dùng/vai trò?** → **KHÔNG** (1 người). Không dùng `form-phan-quyen.md`.
- [x] **Pipeline đa-agent + tối ưu KPI (Phụ lục A)?** → **KHÔNG.** Ba điều kiện kích hoạt đều chưa đúng. Không dùng `form-sow-kpi.md`.
- [x] **Gate G1–G4 của `api-integration-rules.md`?** → 🔴 **CÓ** (G1, G2, G4 đều CÓ: gọi REST/WebSocket Binance; dùng SDK ccxt qua Freqtrade; poll dữ liệu OHLCV/OI). → ✅ **Đã hoàn thành** (TD-0079, 06/09/2026): `api-integration-rules.md` Mục 4.1–4.4 điền đủ 4 bảng (dịch vụ, endpoint, mã lỗi, ngưỡng) cho cả nhóm đọc dữ liệu (D0-PRE) lẫn nhóm đặt lệnh (D3.5+); `provider-map.md` điền cho Binance USDⓈ-M Futures (không có provider dự phòng — lý do ghi trong file, spec gắn chặt với hành vi riêng của Binance). Bảng nghiệm thu R1-R12 (Mục 5) chưa chạy — chờ tới khi có `api_client` thật gọi mạng lần đầu (Khối 8).

---

## 1–5. UI Behavior / Data Shape / Draft API / Validation / Edge Cases

**N/A.** Tool D không có giao diện người dùng. Giao diện duy nhất là dòng lệnh (8 entrypoint E1–E8)
và Telegram/WebUI dựng sẵn của Freqtrade ở chế độ **chỉ theo dõi** (§0c.1).
Hợp đồng dữ liệu tương ứng nằm ở §8 của spec (Decision Log) và §9c.2 (schema registry) — không chép lại ở đây.

---

## 6. Open Questions [v1.0]

*Điều CHƯA quyết định. Khác với Mâu thuẫn (mục 7) — là điều ĐÃ quyết nhưng xung đột nhau.*

| # | Câu hỏi mở | Ảnh hưởng nếu chưa trả lời | Mức độ |
|---|---|---|---|
| OQ-01 | ✅ **Đã giải** (TD-0041, 06/09/2026) — Ngưỡng **DSR-adjusted expectancy** Nhánh 1 §10.2 | `docs/decisions/DR-D0PRE-03-nguong-dsr-expectancy.md`: công thức `mean(R) − √(2·ln N)·std(R)/√n`, ngưỡng **0,10 R** (suy từ chi phí backtest không thấy × hệ số an toàn). **Blocker B6 gỡ.** L-Z35 sang biến thể best-known (−inf, chưa đo) vẫn FAIL | — |
| OQ-02 | ✅ **Đã giải** (TD-0043, 06/09/2026) — `E_D`, `L_exchange`, `rho`, % lỗ/ngày | `docs/decisions/DR-D0PRE-06-von-va-don-bay.md`: **500 USDT / 3x / 0,375% / 8%**; `tradable_balance_ratio` 0.99→0.5. Chủ dự án chọn 500 dù khuyến nghị ≥ 1.000 — chấp nhận ~20% pool bị L-Z20 từ chối ở zone rộng (`docs/min-notional-check.md`, TD-0082) | — |
| OQ-03 | ✅ **Đã giải** (TD-0042, 06/09/2026) — Thang drawdown | `docs/decisions/DR-D0PRE-04-thang-drawdown.md`: giữ **5/8/20%**, Cấp C Hạng 0. Test khoá `halt == daily_loss_budget_pct` | — |
| OQ-04 | ✅ **Đã giải** (TD-0083, 06/09/2026) — Ngưỡng lọc pool §0.3 (i)–(iv) | `docs/decisions/DR-D0PRE-05-pool-criteria.md`: volume 24h ≥15tr USDT (i), tuổi niêm yết ≥180 ngày (ii), (iii)/(iv) không cần ngưỡng riêng — thoả gián tiếp/kiểm tại thời điểm vào lệnh. Trên dữ liệu thật 06/09/2026 (528 hợp đồng): **102 mã** vào pool giao dịch, 426 vào EXPLORE (gồm BTC/ETH). `config/pool.yaml` đã ghi, tiêu 4 trial B0 (D-0001→D-0004) | — |
| OQ-05 | ✅ **Đã giải** (TD-0084, 06/09/2026) — Mốc chia T0/T1/T2/T3 | `docs/decisions/DR-D0PRE-07-t0-t1-t2-t3.md`: T0=09/04/2024, T1=12/06/2025, T2=29/01/2026, T3=06/09/2026 (hôm nay). T2 neo vào chế độ thị trường THẬT — BTC sập liên tục >30% từ 29/01/2026 (đỉnh sập -53%), khác hẳn CALIB/WFO (dd trung bình -11% đến -14%). `lockbox_seal_1.json` đã niêm phong (510 file OHLCV thật, 102 mã). Phát hiện kèm: sửa bug thật `verify_all_seals()` trỏ sai thư mục (LOCKBOX_DATA_DIR thay vì LOCKBOX_FUTURES_DIR) tồn tại từ TD-0071/72, không bị bắt vì trước đó chưa có seal thật | — |
| OQ-06 | `v_min` (§3.3b) — hiện `null` | Không được điền ở D0-PRE (phải calibrate bằng dữ liệu ở B1), nhưng L-Z15 đòi nó **có trạng thái**, không được "im lặng" → ghi `TUNED_PENDING` | 🟡 |
| OQ-07 | Tiêu chí chọn ý tưởng của quý (§9c.7.4) | Phải commit **trước khi** mở Idea Queue — mở trước là điều cấm (spec dòng 4935) | 🟡 |
| OQ-08 | ✅ **Đã giải** (TD-0085, 06/09/2026) — Backup lockbox ra ngoài git | `docs/decisions/DR-D0PRE-08-lockbox-backup.md`: chủ dự án chọn thư mục khác trên cùng máy (`E:\lockbox-backup-tool-d\`) để bắt đầu — chưa chống mất máy vật lý, nâng cấp cloud để sau. Test khôi phục THẬT đã chạy 1 lần: backup 510 file → verify PASS → khôi phục vào thư mục tạm mới → verify PASS độc lập | — |
| OQ-09 | Ngưỡng Circuit Breaker cho Risk Supervisor (§6.6): số lỗi liên tiếp kích hoạt + backoff khởi điểm/tối đa — `api-integration-rules.md` (TD-0079) tạm đề xuất 5 lỗi / 1s→60s, spec KHÔNG có số cụ thể | Không chặn D0-PRE (chi tiết triển khai R3, không phải tham số tín hiệu — không tính vào N_ĐĂNG_KÝ theo Nguyên tắc 9) nhưng cần chốt trước khi implement Risk Supervisor thật (D1) | 🟡 Chốt trước D1 |
| OQ-10 | Số lệnh/năm thật (sàn 150, §10.2) — ước lượng tay (`docs/estimate-trades-per-year.md`, TD-0081) cho khoảng **129–1.652 lệnh/năm** (long-only, 102 mã), vắt ngang sàn 150, không kết luận nhị phân được bằng suy luận | Không chặn D0-PRE. Chặn D4 nếu số đo thật ở D1 (H1-D + zone detection trên CALIB) < 150 | 🟡 Đo lại thật ở D1, không coi ước lượng tay là kết luận cuối |

---

## 7. Mâu thuẫn & Cần làm rõ [v1.0]

| # | Mâu thuẫn phát hiện | Giữa cái gì với cái gì | Mức độ | Cách giải quyết | Ngày | Người quyết |
|---|---|---|---|---|---|---|
| MT-01 | Sổ trial vừa phải **append-only tuyệt đối** (dòng 3762: *"phát hiện sửa dòng cũ = toàn bộ registry mất hiệu lực"*) vừa phải **chuyển trạng thái** RESERVED→CONSUMED/REFUNDED tại chỗ (dòng 3738, DR-014). Không thể làm cả hai | Nội tại spec: §9c.2 quy tắc 2 vs DR-014 | 🔴 Chặn TD-0050 | **ĐÃ CHỐT:** `trial_registry.jsonl` là **sổ nhật ký sự kiện** — mỗi dòng một sự kiện (RESERVE / SEAL / CONSUME / REFUND / CONTAMINATE) mang cùng `trial_id`. Trạng thái là **bản chiếu** tính lại khi đọc, không phải trường trên đĩa. Giữ nguyên append-only tuyệt đối, và được thêm dấu vết ai-làm-gì-lúc-nào | 06/09/2026 | Chủ dự án |
| MT-02 | *"KHÔNG ĐƯỢC CHẠM DỮ LIỆU TRƯỚC KHI D0-PRE XONG"* (dòng 4464) vs chính D0-PRE lại chứa việc "chốt pool ~100 mã" (dòng 4447) và "verify độ dài lịch sử OI" (dòng 4457) — hai việc bắt buộc gọi API Binance | Nội tại spec: §12 với chính nó | 🔴 Chặn TD-0080 | **ĐÃ CHỐT:** "chạm" = **đánh giá cấu hình** trên CALIB / WFO / LOCKBOX (theo DR-014 mục 2, dòng 3490–3494). Đo thông tin mô tả không sinh chỉ số chiến lược nên không phải "chạm", nhưng vẫn ghi sổ dòng `CTRL` (0 trial), bắt buộc có assert khoảng thời gian, và **bị đẩy xuống Khối 8** — sau khi tầng chống nhiễm đã sống | 06/09/2026 | Chủ dự án |
| MT-03 | Hai nguồn sự thật cho ngân sách B3: `tool_d_config.yaml` có `_budget_remaining_B3: 20` *"hệ thống giảm, không sửa tay"* (dòng 2338) vs DR-014 tính Khả dụng từ registry (dòng 3484–3485) | §6.9.5 vs DR-014 | 🟡 Phải giải trước TD-0051 | **ĐÃ CHỐT:** **registry là nguồn sự thật**. Khoá YAML đổi thành `_budget_remaining_B3: null  # derived — xem registry`, loader **raise** nếu nó khác `null`. Chính spec cảnh báo đây là cơ chế đã gây đợt lệch số của v5 (dòng 3315–3317) | 06/09/2026 | Chủ dự án |
| MT-04 | `zone_width` xuất hiện hai chỗ với hai số phận: comment `"13?"` trong `tier_b` (dòng 2351–2353) vs `0 (hoặc 1)` trong bảng DOF (dòng 3210) | §6.9.5 vs DR-010 | ✅ Đã giải (TD-0030) | **CHẾT** — `docs/decisions/DR-D0PRE-01-zone-width-verify.md`: `zone_width_pct` LUÔN BẰNG chính xác `0.6×ATR/price` theo cấu trúc §1.1, ngưỡng lọc là `0.5×ATR/price` — với cùng mốc ATR/price, `0.6≥0.5` là hằng đẳng thức, không phải điều kiện. Đã xoá hẳn khỏi `tool_d_config.yaml`, không để lại comment. `N_ĐĂNG_KÝ = 114` | 06/09/2026 | Claude (phân tích cấu trúc, không cần dữ liệu) |
| MT-05 | Quy trình vibe-code Giai đoạn 4 viết cho web app trên Render (Image Preview, health check `/health`, DB staging) — không áp thẳng được cho bot trading local | `QUY-TRINH-VIBE-CODE.md` GĐ4 vs bản chất project | 🟡 | **ĐÃ CHỐT:** ánh xạ ghi ở `CLAUDE.md` mục N11. Giữ "cùng 1 Dockerfile"; thay Image Preview bằng image digest local; "URL preview" → Binance testnet (D3.5 / D10) → dry-run (D11); production → D12 vốn nhỏ. **GĐ4 không áp cho D0-PRE** | 06/09/2026 | Chủ dự án |
| MT-06 | L-Z25 đòi grep cả *"lịch sử lệnh"* (dòng 510) để chứng minh chưa từng chạy hyperopt — nhưng lịch sử shell nằm ngoài repo và shell trong container là ephemeral | Yêu cầu test vs khả năng kỹ thuật | 🟡 | Kiểm được: `git grep` worktree + `git log -S hyperopt --all` (bắt cả file đã xoá) + `runs/cmd_audit.log` do wrapper tự ghi. **Không** kiểm được: người gọi `docker run … freqtrade hyperopt` thủ công. Rủi ro tồn dư — ghi `docs/research-log.md`, cùng loại thừa nhận với dòng 3317–3320 | 06/09/2026 | Chủ dự án |
| MT-07 | Khối xuất xứ spec quy định **đúng 7 khoá** (dòng 597–616), nhưng chạy trong Docker thì phiên bản Freqtrade nằm trong image chứ không nằm trong git → không truy được về sau | §0d.5 vs quyết định dùng Docker | 🟡 | **ĐÃ CHỐT:** thêm khoá thứ 8 `runtime_image_digest`. Không phá L-Z40 (test đòi *đủ* 7 khoá, không cấm khoá thứ 8) | 06/09/2026 | Chủ dự án |
| MT-08 | `registry.py` **chưa thi hành** phần kế toán `CTRL` đã chốt ở MT-02, ba lỗi: (1) `TrialProjection` không lưu `budget_line` nên `n_used()`/`n_reserved()` cộng cả dòng CTRL; (2) `reserve()` chặn `contribution < 1` nên dòng *"CTRL 0 trial"* mà MT-02 yêu cầu **không ghi được**; (3) `reserve()` kiểm ngân sách cho mọi dòng nên khi N cạn thì **không ghi được điểm kiểm soát** — đúng lúc sắp go-live là lúc cần kiểm tra tái lập nhất | Code `src/tool_d/ledger/registry.py` vs §0d.4 dòng 594 + DR-014 §2 dòng 3490 + dòng 3608 + dòng 3715 + quyết định **MT-02** | 🟡 Chưa gây thiệt hại (sổ hiện 4 trial đều B0, **chưa có dòng CTRL nào**) nhưng **phải sửa trước dòng CTRL đầu tiên, tức trước D3.5** | **ĐÃ CHỐT — phương án A + cơ chế xác thực:** (1) `TrialProjection` mang `budget_line`; `n_used()`, `n_reserved()` và phép kiểm ngân sách trong `reserve()` **loại CTRL ra**; giữ nguyên bất biến `contribution >= 1` (không mở đường mức 0). (2) CTRL phải khai thuộc **một trong hai dạng, máy kiểm chứ không nhận lời khai** (cùng triết lý DR-014 §3): *tái lập* (§0d.4) — có `reproduces_trial_id` và `config_hash`/`params_frozen_hash` **bằng đúng** bản ghi trial đó; *đo thước* (D3.5 Bước 1, MT-02) — đầu ra giới hạn cứng vào danh sách trắng không chứa chỉ số hiệu năng nào (spec dòng 3605–3607). Không thoả dạng nào → **từ chối ghi CTRL** (fail-closed), tính như trial thường. (3) Test khoá mới **L-Z56**: 1 trial B1 + 1 trial CTRL đều CONSUMED → `n_used() == 1`; và `reserve()` dòng CTRL vẫn thành công khi ngân sách đã cạn. **Vì sao cần (2):** L-Z55 một mình KHÔNG đủ cho CTRL — một điểm kiểm soát hợp lệ *có* chạm CALIB nên không vi phạm timerange; chỗ phân biệt phải là **ĐẦU RA**, không phải dữ liệu chạm. **Quy mô sai số nếu bỏ qua** (suy từ hằng số spec, không cần dữ liệu): điểm kiểm soát chạy sau mỗi lần một tham số đổi trạng thái, Tầng B có 12 tham số, trần B3 = 20 → cận trên ~20–25 trial trên 114 (**~18–22% ngân sách**); nguy hơn con số là **động cơ chạy ngược** — càng kỷ luật càng bị phạt, dẫn tới bỏ điểm kiểm soát. Méo mó DSR không đáng kể (N 114→134 nâng ngưỡng √(2·ln N) +1,7%) | 07/09/2026 | Chủ dự án |

> 🔴 Chặn tiến độ: dừng code ngay, xử lý trước khi tiếp tục.
> 🟡 Có thể chốt sau: ghi nhận, tiếp tục phần khác, **bắt buộc** giải quyết trước Giai đoạn 5 — không mang mâu thuẫn 🟡 vượt qua go-live.

---

## 8. Lịch sử thay đổi

| Mục thay đổi | Loại | Nội dung cũ | Nội dung mới | Lý do | Ngày |
|---|---|---|---|---|---|
| Toàn bộ file | ➕ Thêm mới | — | Khởi tạo lớp mỏng: phạm vi GĐ1, quyết định nền tảng, 8 Open Questions, 7 Mâu thuẫn | Giai đoạn 1–2 của quy trình vibe-code | 06/09/2026 |
| Mục 7 | ➕ Thêm mới | 7 mâu thuẫn (MT-01…MT-07) | Thêm **MT-08** — `registry.py` chưa thi hành phần kế toán `CTRL` đã chốt ở MT-02; chốt phương án A + cơ chế xác thực CTRL | Phía front-end phát hiện khi dựng tầng gấp trạng thái cho dashboard (phải chép đúng luật của `registry.py`). MT-02 và MT-01…MT-07 **giữ nguyên**, không sửa nội dung đã chốt | 07/09/2026 |
