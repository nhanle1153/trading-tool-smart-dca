# TOOL D — SMART DCA NGẮN HẠN
## Zone Absorption │ Binance USDⓈ-M Futures │ Long + Short │ Triển khai theo tranche neo zone

> **Phiên bản:** v8 — HOÀN TẤT QUẢN TRỊ PHÉP THỬ + PHÂN XỬ Z0/DCA. Ba việc: (1) DR-014 — sổ hai trạng thái ĐẶT CHỖ/ĐÃ TIÊU cho trial, thay quy tắc 4 của §9c.2 bằng cơ chế máy quyết định, không dựa lời khai; (2) DR-015 — cổng D3.5 đo SAI LỆCH THƯỚC ĐO khớp tranche TRƯỚC ablation + quy tắc phân xử hiệu-chỉnh-hai-chiều tích hợp vào Nhánh 2 §10.2 (mặc định Z0 khi không phân xử được); (3) tu chính DR-013 — nguồn sự thật của `planned_risk_usdt` là TỔNG THANG KẾ HOẠCH sau làm tròn khối lượng, chốt luôn câu hỏi mở #27. N_ĐĂNG_KÝ = 114 KHÔNG ĐỔI. Trước đó: v7 — TOÀN VẸN PHÉP ĐO + BÀI HỌC TOOL A. Tiếp thu 42 bài học (LD-01→LD-42) từ nhật ký code Tool A, có phản biện: 31 áp dụng, 6 áp dụng có sửa, 5 không áp dụng (lý do ở Phụ lục C). Gỡ thêm 11 mâu thuẫn còn sót trong v6. Trước đó: v6 (hoà giải mâu thuẫn nội bộ), v5 (Freqtrade + vòng đời tham số), v4 (hợp nhất v3 + v3.1–v3.3).
> **Phiên bản cũ:** v4 — Gộp toàn bộ spec v3 + bản vá v3.1 (quản trị phép thử) + v3.2 (chân trời thời gian, DG8) + v3.3 (vốn & đòn bẩy, pool, sinh giả thuyết). **Đây là tài liệu DUY NHẤT — các file v3, v3.1, v3.2, v3.3 đã lỗi thời, không dùng nữa.**
> **Ngày:** 06/09/2026
> **Trạng thái:** 🔴 **CHƯA ĐƯỢC PHÉP CODE** — 7 hard blocker + 🆕 v7: PHẦN 0d (toàn vẹn phép đo) là hạng mục D0-PRE, làm TRƯỚC mọi dòng logic chiến lược
> **Quan hệ với tài liệu Tool A:** chỉ mượn **khuôn tài liệu** (DR, GATE, blocker, Decision Log, thứ tự hardening). Toàn bộ chỉ báo, ngưỡng, công thức rủi ro trong file này **tự đứng**, không tra ngược sang Tool A.
> Không phải khuyến nghị đầu tư. Tài liệu kỹ thuật nội bộ.
>
> ⚠️ **Toàn bộ con số minh hoạ trong tài liệu này là VÍ DỤ TÍNH TOÁN CÔNG THỨC, không phải kết quả backtest.** Không có backtest nào đã chạy. Mọi ngưỡng đánh dấu `[CẦN CALIBRATE]` là chỗ giữ, phải điền bằng dữ liệu thật ở D0.9 — không được coi là đã xác nhận.

### Changelog v7 → v8

```
═══ NGUỒN: ba DR nháp (tiêu-trial, mẫu-số-R, sai-lệch-khớp-tranche) ═══
Cả ba viết trên nền audit v5 → trước khi nhập phải đối chiếu lại với
v7. Ba mâu thuẫn DR-vs-spec được gỡ NGAY TRONG LẦN NHẬP, không nhập
nguyên văn:
   (i)   DR tiêu-trial §4.3 hợp thức hoá "đặt chỗ cho hyperopt" —
         mâu thuẫn trực diện §0c.2 (CẤM tuyệt đối) + L-Z25 (phát hiện
         hyperopt → registry mất hiệu lực). v8 tổng quát hoá thành
         "lô nhiều cấu hình", KHÔNG mở cửa cho hyperopt.
   (ii)  DR tiêu-trial lập luận "mẫu số DSR" — sai với Tool D: DSR
         trước live dùng N_ĐĂNG_KÝ (DR-010 quy tắc 3), không dùng
         N_ĐÃ_DÙNG. Vai trò thật của sổ hai trạng thái: cưỡng chế
         N_ĐÃ_DÙNG ≤ N_ĐĂNG_KÝ (luật dừng) + nuôi N sau live (§12c.2).
   (iii) DR sai-lệch §6 đòi "sửa điều kiện dừng bị đảo chiều" — đã
         sửa từ v6 (§10.2 hai nhánh). Chỉ giữ lại TEST khoá (L-Z57).

════════════ THÊM ════════════
THÊM  DR-014  — Sổ hai trạng thái ĐẶT CHỖ / ĐÃ TIÊU (LD-34, LD-31,
                LD-01/02): con dấu đo lường do bộ chạy tự ghi, trả
                lại đặt chỗ CHỈ theo nguyên nhân máy xác định, trần
                trả lại 3 lần/giả thuyết, nhiễm tham số tiêu gấp đôi,
                công thức Khả dụng. Thay quy tắc 4 của §9c.2.
THÊM  DR-015  — Cổng D3.5: đo sai lệch khớp tranche TRƯỚC ablation
                (Bước 1 offline trên CALIB, dòng CTRL 0 trial; Bước 2
                testnet tối thiểu; Bước 3 đối chứng âm Z0). Quy tắc
                phân xử hiệu chỉnh cực đoan hai chiều NHẬP THẲNG vào
                Nhánh 2 §10.2: "≥20%" phải SỐNG SÓT qua cả hai chiều.
                Không phân xử được → mặc định Z0. Simulator ngoài chỉ
                mở khoá khi (đổi người thắng giữa hai chiều) VÀ (lợi
                thế thô DCA ≥ 20%).
THÊM  §9c.2   — Schema registry: `contribution`, `state`
                (RESERVED/CONSUMED/REFUNDED), `seal_path`,
                `refund_cause_machine` (thay cờ `aborted` v7)
THÊM  L-Z52→L-Z58 — test khoá cứng cho DR-014/DR-015

════════════ SỬA ════════════
SỬA   DR-013  — TU CHÍNH: `planned_risk_usdt` := Σ(qty_i_kế_hoạch ×
                |p_i_kế_hoạch − sl_price|) trên THANG ĐẦY ĐỦ, khối
                lượng SAU làm tròn lot/min-notional, p1 = p1_order
                thật (§3.5). Khẳng định |tổng − rho_eff×E_D| ≤ 1%
                lúc entry (đúng L-Z20 sẵn có), vi phạm → TỪ CHỐI VÀO
                LỆNH. Bảng tên gọi ba chữ "R" — cấm chữ "R" trần.
SỬA   §10.2   — Nhánh 2 thêm tiền đề DR-015 + điều kiện sống-sót-
                hiệu-chỉnh; ô "không phân xử được" → Z0, dự án tiếp tục
SỬA   §3.5    — đoạn cảnh báo cuối: hiệu chỉnh D6 làm TRƯỚC khi đọc
                Nhánh 2 (D3.5), không phải "đọc lại sau D10"
SỬA   §9b.3   — D10 giữ vai trò XÁC NHẬN quy mô đầy đủ; lần đo ĐẦU
                của (1)/(3) chuyển lên D3.5
SỬA   §12     — chèn cổng D3.5 giữa D3 và D4; cập nhật D10; thêm
                D3.5 + con dấu DR-014 vào danh sách KHÔNG BAO GIỜ CẮT
SỬA   L-Z34   — đếm N_ĐÃ_DÙNG theo state == CONSUMED (DR-014)
SỬA   §14 #27 — ✅ CHỐT v8: N_full tính lại theo p1_order thật (D0.1
                thắng "đơn giản") — hệ quả trực tiếp của tu chính
                DR-013. Thêm #28, #29 (hai hằng số chọn của v8).

GIỮ   N_ĐĂNG_KÝ = 114: DR-014/015 không thêm tham số tunable nào.
      Cổng thăm dò D3.5 đi dòng CTRL (không tính vào N) với danh sách
      đầu ra bị giới hạn (DR-015 §3).
```

### Changelog v6 → v7

```
═══════ NGUỒN: bài học từ nhật ký code Tool A (file "bai-hoc-tu-tool-a", 06/09/2026) ═══════
Nguyên tắc tiếp thu: chỉ lấy bài học về CƠ CHẾ FREQTRADE, HẠ TẦNG ĐO
LƯỜNG, QUẢN TRỊ NGHIÊN CỨU. Không lấy bất kỳ ngưỡng/công thức/kết luận
chiến lược nào của Tool A. Mỗi bài học được PHẢN BIỆN trước khi đưa
vào (Phụ lục C liệt kê cái nào bị sửa, cái nào bị loại, và vì sao).

════════════ THÊM — TOÀN VẸN PHÉP ĐO (hạng mục D0-PRE mới) ════════════
THÊM  PHẦN 0d  — Bảy ràng buộc đo lường: guard file tham số ẩn
                 (LD-01/02), cache có dấu tham số (LD-03), env chỉ
                 cho vận hành + "điểm kiểm soát" (LD-04), khối
                 provenance (LD-05), ba trạng thái dữ liệu (LD-10),
                 cấm `*Parameter` của Freqtrade (hệ quả LD-01+LD-18),
                 chẩn đoán "bot sai hay tầng đo sai" (LD-06)
THÊM  DR-013   — ĐƠN VỊ ĐO: mọi chỉ số tổng hợp tính trên `pnl_abs`,
                 KHÔNG BAO GIỜ trên `profit_ratio` (LD-07); mẫu số R
                 = `planned_risk_usdt` đóng băng lúc entry (LD-08);
                 trả lời câu hỏi mở của LD-08 về R nhiều tranche
THÊM  §3.5     — Vòng đời LỆNH CHỜ tại zone: giá đặt, tuổi thọ, ánh
                 xạ đúng config Freqtrade (LD-12/13). v6 CHƯA TỪNG
                 định nghĩa tranche 1 sống bao lâu
THÊM  §9b      — Giả định D6 (adjust_trade_position khớp tại giá MỞ
                 nến trong backtest — LD-11, rủi ro số một) và D7
                 (custom_data sống qua callback — LD-17)
THÊM  §8       — `dedup_key` theo order_id từng tranche (LD-19),
                 append-only tuyệt đối (LD-20), bản ghi đổi KHỐI
                 LƯỢNG SL (LD-21, có sửa), danh sách đóng các giá trị
                 đóng băng lúc entry (LD-17)
THÊM  §9c.2    — Registry: `budget_line` thêm B0 (v6 sót), khối
                 provenance, cờ `aborted` + quy tắc "thế nào là đã
                 tiêu một trial" (LD-34)
THÊM  §9c.6    — L-Z34 (N thật sự nối vào code, LD-30), L-Z35
                 (placeholder fail-closed, LD-31), L-Z36→L-Z45
THÊM  §6.6     — Risk Supervisor: không import code bot, LIQUIDATED
                 = dừng toàn hệ thống (LD-22), trần API/phút Cấp C
                 (LD-23), bắt lỗi theo từng endpoint (LD-26)
THÊM  §7.2     — Ba lớp dương tính giả của lookahead-analysis (LD-15)
THÊM  §11      — H3-D nhận danh sách lỗi cụ thể phải tránh (LD-01→05)
                 thay cho câu "nguy cơ tái phạm bug"; H1-D survivorship
                 bias (LD-29); H19 backfill an toàn (LD-27/28)
THÊM  PHỤ LỤC C — Bảng ánh xạ LD-xx → §, và 5 bài học KHÔNG áp dụng

════════════ SỬA — MÂU THUẪN CÒN SÓT TRONG v6 ════════════
SỬA   §0c.2    — "N = 134", "16 tham số" → 114, 12  (v6 sót 2 chỗ)
SỬA   §3.3d    — w = [0.35,0.35,0.30] → [1/3,1/3,1/3]  (v6 sót ở bản SHORT)
SỬA   §8       — Decision Log: tranche_weights, "5 hệ số" → 6,
                 mult_breakdown thêm `regime`; liq_buffer_ratio ví dụ
                 12.86 đánh dấu CHƯA TRUY ĐƯỢC (§6.4b)
SỬA   §11      — XOÁ H7 "Custom loss": loss function là khái niệm của
                 HYPEROPT (bị cấm ở §0c.2) và phạt `zone_width` (đang
                 bị xoá ở §3.3). Hạng mục này tự mâu thuẫn hai lần
SỬA   §12      — D9.5 "FAIL → DỪNG DỰ ÁN" → BA KẾT CỤC (DR-011 v6 đã
                 sửa nhưng roadmap chưa); "D0.5 thêm ~1 tuần" → D0-PRE
SỬA   §12c.2/3 — "N = 134" → 114  (2 chỗ)
SỬA   L-Z13    — "ĐÚNG 1 bản ghi vĩnh viễn" mâu thuẫn với INCONCLUSIVE
                 gia hạn tối đa 2 lần (DR-011 v6). Sửa: 1 bản ghi MỖI
                 đoạn niêm phong, tối đa 3 đoạn
SỬA   §9b D2   — Viết lại theo LD-16: Freqtrade HUỶ-ĐẶT-LẠI STOP_MARKET
                 khi khối lượng đổi (đã xác nhận). Câu hỏi thật không
                 phải "Binance có cho sửa không" mà là "KHOẢNG TRỐNG
                 không SL kéo dài bao lâu" + "closePosition=true có
                 dùng được không". D0.2 KHÔNG bị vi phạm (giá SL không
                 đổi, chỉ khối lượng đổi) — v6 nói quá
SỬA   §1.2/§6.2 — Định nghĩa "chạm rồi bật ra" (touch_count) và
                 `corr_pool` bằng công thức. v6 để tên không có công
                 thức — đúng lỗi LD-35
GIỮ   Toàn bộ v6 không nêu ở trên. N_ĐĂNG_KÝ = 114 KHÔNG ĐỔI:
      v7 không thêm tham số tunable nào (tuổi thọ lệnh chờ dùng lại
      3 nến của §3.3b; cửa sổ corr 30 ngày là hằng số định nghĩa;
      trần API là Cấp C)
```

**Ba con số v8:** `N_ĐĂNG_KÝ = 114` (không đổi), 12 tunable + 8 khoá đóng băng (không đổi), **7 giả định D1–D7** (không đổi — nhưng D6 giờ được ĐO TRƯỚC ablation tại cổng D3.5, DR-015, thay vì chỉ đo ở D10).

---

### Changelog v5 → v6

```
════════════ SỬA — MÂU THUẪN CỨNG (code không xác định được giá trị) ════════════
SỬA   DR-010    — Kiểm kê DOF sai. v5 khai "đóng băng 9 → 26 giảm còn
                  16" nhưng `k` và ADX CHƯA TỪNG có trong danh sách 26
                  nên đóng băng chúng giảm 0. Trừ đúng: −6 → 20, không
                  phải 16. Kiểm kê lại toàn bộ: 12 tunable + 8 khoá
                  đóng băng. N: 134 → 114
SỬA   §4.1      — DG6-B: 6 nến 1H → 8 nến 1H (= DG4). v5 đóng băng ở 8
                  trong DR-010 nhưng §4.1 vẫn ghi 6
SỬA   §1.2      — w_a/w_b/w_c: chốt 1/3. Xoá "0.4/0.3/0.3" ở §1.2 và
                  DR-010 (v5 có 3 giá trị khác nhau cho 1 tham số)
SỬA   §6.4      — Định nghĩa `liq_buffer_ratio` bằng công thức. v5 so
                  một tỷ lệ % với "8 lần" — hai thang khác nhau. Gate
                  CRITICAL này trước đây KHÔNG tính được
SỬA   §10.2     — GATE tách thành BA kết cục (PASS/INCONCLUSIVE/FAIL)
                  và HAI nhánh. v5 để kết cục "Z0 thắng" (được §10.1
                  gọi là kết quả TỐT) kích hoạt điều khoản DỪNG DỰ ÁN
SỬA   §12c.3    — `k` → Cấp C (không có cơ chế mở khoá +6);
                  `DG6-B` ra khỏi Cấp B (đã đóng băng)
SỬA   §6.2      — `L_BASE` là tham số mồ côi (không có trong công thức
                  định cỡ duy nhất §6.8f) → thay bằng `mult_regime`
SỬA   DR-010    — DG7 `0.3 × R_eff` chưa từng được đếm → +1 DOF.
                  Gộp funding chỉ giảm được 1, không phải 2

════════════ XOÁ ════════════
XOÁ   §3.3c     — Đường nhanh 15m. Lý do: ghép khung NHỎ HƠN vào
                  dataframe 1H là bề mặt lookahead thứ hai mà PHẦN 7
                  không phủ; đường nhanh bỏ qua cả ba điều kiện xác
                  nhận (a)/(b)/(c), vi phạm checklist CRITICAL §13.
                  Lợi ích thật ≈6% độ trễ. Không tương xứng.  (−1 DOF)
XOÁ   §2.4      — BTC regime macro. Tiêu 1 DOF nhưng KHÔNG có arm
                  ablation nào bật/tắt nó và không nằm trong công thức
                  mặc định. Chuyển sang Idea Queue.            (−1 DOF)
XOÁ   `mult_cross` — v5 nói 3 kiểu ở 3 nơi (tuỳ chọn / P0 / "chốt:
                  chờ xác nhận"). Lý do tồn tại đã mất khi bỏ trần gộp
                  (§6.5). Xoá khỏi §6.2, §9.3, H2, §14
XOÁ   `L_D_max` — §6.8f tự chứng minh nó ≡ `0.85 × L_exchange`. Hai
                  nguồn sự thật cho một ràng buộc
XOÁ   §3.3      — `zone_width` min: XOÁ CÓ ĐIỀU KIỆN sau VERIFY ở
                  D0-PRE (nghi code chết: 2×buf = 0.6×ATR > 0.5×ATR)

════════════ THÊM ════════════
THÊM  §4c       — DG7 chuyển nhóm: chặn tranche → ĐÓNG VỊ THẾ. Gỡ lỗ
                  hổng "funding drain không có cơ chế đóng" (§4b.1b)
THÊM  §6.2      — Định nghĩa tường minh `deployed_ratio_tool_d` và
                  `mult_edge` (v5 để một biến không định nghĩa và một
                  công thức trỏ sang Tool A — vi phạm zero-dependency)
THÊM  §6.4b     — Công thức `liq_buffer_ratio`, tính trên KẾ HOẠCH đủ
                  3 tranche (v5 tính trên p1 → gate pass ở tranche 1
                  rồi vi phạm ở tranche 3)
THÊM  §11b.2    — Chỉ số H-4 (tỉ lệ TP_fallback). v5 changelog khai
                  "thêm H-4" nhưng §11b chưa từng được sửa
THÊM  §12c.5    — Thang phản ứng drawdown 3 mức: 5% / 8% HALT / 20%
                  DỪNG. Gỡ ca "một ngày xấu = tắt máy vĩnh viễn"
THÊM  L-Z29..33 — Test tự động chống tái diễn lỗi kiểm kê DOF
THÊM  PHỤ LỤC B — Căn cứ 18 lỗi của bản vá v6

════════════ SỬA — ĐỒNG BỘ SỐ LIỆU ════════════
SỬA   14 vị trí — 174/184/192/194 → 114 · "24 bậc tự do" → 12 ·
                  "16 tham số" → 12 · "5 cấu hình PBO" → 9 ·
                  "BẢY cấu hình D4" → CHÍN · "rank 31-60" (H1-D) → xoá
                  · "pool 30-50 mã" → ~100 · "D0.5" → "D0-PRE"
GIỮ   Toàn bộ v5 không nêu ở trên
```

**Ba con số đã chốt ở v6:** `N_ĐĂNG_KÝ = 114` (B0=4 · B1=72 · B2=18 · B3=20) → rào DSR ≈ **3,08**; **12** tham số tunable + **8** khoá đóng băng; điểm quyết định mỗi **100 lệnh đóng**, tái tạo **+1 trial / 25 lệnh**, trần B3 ≤ 20.

---

### Changelog v4 → v5

```
THÊM  PHẦN 0c   — 🔴 TƯƠNG THÍCH FREQTRADE: module nào DÙNG, module
                  nào CẤM. Hyperopt/FreqAI/Edge là mối nguy lớn nhất
THÊM  §12b      — Vòng đời tham số: nghiên cứu → live → xem lại
THÊM  §12c      — Giao thức ĐIỂM QUYẾT ĐỊNH (mỗi 100 lệnh)
                  + ngân sách trial TÁI TẠO (+1 / 25 lệnh mới)
                  + phân cấp tham số được đổi (3 cấp)
THÊM  §12d      — Báo cáo định kỳ + giao thức LLM phân tích
SỬA   DR-010    — đóng băng 9 tham số. 26 → 16. N: 192 → 134
SỬA   DR-009    — LLM ĐƯỢC phân tích báo cáo cố định (sửa lệnh cấm
                  quá rộng ở v3.3). Cấm đọc DB lệnh thô
SỬA   §10.2     — làm rõ 150 lệnh/năm là SÀN, không phải trần
SỬA   §11b      — thêm H-4; báo cáo thành script commit trước
GIỮ   Toàn bộ v4
```

*(Ba con số của v5 — `N = 134`, đóng băng 9 tham số — đã bị v6 thay. Xem changelog v5 → v6 ở trên.)*

---

### Changelog v3 → v4

```
v3.1  THÊM  DR-009 vai trò LLM · DR-010 ngân sách trial · DR-011 lockbox
            DR-012 change-control · PHẦN 9c · H16-H18 · blocker B6
v3.2  THÊM  PHẦN 2b chân trời chỉ báo · PHẦN 4b DG8 Time Stop
            §10.1b arm Z0-T0/Z0-T1 · blocker B7
v3.3  THÊM  §0.3b bỏ BTC/ETH · §0.3c pool ~100 mã · §1.3b nhiều zone
            §3.3b(c) volume lúc chạm · §6.8 vốn & đòn bẩy
            §9c.4b tập EXPLORE · PHẦN 11b component health
v4    HỢP NHẤT tất cả vào MỘT file. Lý do: ba tài liệu rời với tham
      chiếu chéo là ĐÚNG điều kiện đã gây ra sự cố D1-D5 bị rớt mất
      im lặng (§9b). Không lặp lại lỗi đó.

N_ĐĂNG_KÝ = 134   (v5 — ĐÃ BỊ v6 THAY BẰNG 114, xem changelog trên)
```

---

## 🔴 BẢY HARD BLOCKER

| # | Blocker | Gỡ ở đâu |
|---|---|---|
| **B1** | Câu chuyện kinh tế — **ĐÃ CHỐT ở v1**: Zone Absorption, không trùng ứng viên bị loại ở DR-005 của Tool A | §0.1 — chỉ còn việc định nghĩa "zone" bằng số |
| **B2** | Zone/swing detection có nguy cơ **lookahead cố hữu** — một swing chỉ "biết" được sau N nến xác nhận | §7 — đây là rủi ro kỹ thuật lớn nhất của riêng Tool D, Tool A không có dạng này |
| **B3** | DSR — pool chọn theo chiến lược (§0.3), overlap với Tool A là kết quả ĐO ĐƯỢC chứ không phải thiết kế; nhiều khả năng overlap CAO → DR-007 (union DSR) áp dụng trong thực tế | §9 |
| **B4** | Ablation D0.9 chưa chạy — giờ phải chứng minh **ba** mệnh đề, không phải một | §10.1 |
| **B5** 🆕 v3 | Giả định D2 (sửa khối lượng SL không huỷ-đặt-lại) chỉ verify được qua Testnet/Live — Dry-run KHÔNG đủ | §9b — mới phát hiện, roadmap trước nhảy thẳng backtest→dry-run |
| **B6** 🆕 v3.1 | **`N` (số trial) trong DSR ở §10.2 chưa được định nghĩa** → điều kiện GATE D0.9 không tính được. 🔴 **v6:** N đã có (=114) nhưng ngưỡng `DSR-adjusted expectancy ≥ ......` ở Nhánh 1 (§10.2) **vẫn còn trống** — B6 chưa gỡ xong cho tới khi con số đó được điền và commit ở D0-PRE | §9c, §10.2 |
| **B7** 🆕 v3.2 | **KHÔNG tồn tại cơ chế đóng vị thế theo thời gian.** DG4/DG7 chỉ chặn tranche; DG6-B vô hiệu vĩnh viễn khi giá đóng cửa vượt lại p1. Mâu thuẫn §1.3 (zone hết hạn 6,7 ngày) | §4b |

> 🔴 **B6 chặn D4 (Ablation D0.9).** Không chạy arm nào trước khi §9c.2/§9c.3/§9c.4 hoàn tất và niêm phong.
> 🔴 🆕 **v8 — D4 bị chặn THÊM bởi cổng D3.5 (DR-015):** chưa có kết quả thăm dò sai lệch khớp tranche (Bước 1–3) thì bộ chạy ablation TỪ CHỐI khởi động (L-Z56). Lý do: đọc kết quả Z0-vs-DCA rồi mới đo thước là trạng thái tệ nhất có thể — kết luận đã hình thành trên thước chưa kiểm.
> 🔴 **B7 chặn D7.** Nhưng KHÔNG chặn D4 — D0.9 phải chạy CÓ DG8 để phân bố hold phản ánh hệ thống thật (§4b.4).

---

# PHẦN 0 — ĐỊNH VỊ

## 0.1. Câu chuyện kinh tế — CHỐT: Zone Absorption

**Cơ chế:** giá quay lại một vùng đã có dòng lệnh lớn hình thành trước đó (vùng đảo chiều/tích luỹ trước một nhịp di chuyển giá rõ rệt) → dòng lệnh còn lại tại vùng đó hấp thụ áp lực bán/mua đối nghịch → xu hướng lớn hơn (đã xác nhận độc lập ở khung cao hơn, §0.2) tiếp diễn.

**Ai trả tiền:** người mua đuổi theo nhịp di chuyển ban đầu, bị rũ ra khi giá lùi về vùng cũ (chốt lời non/cắt lỗ sớm vì hoảng); người giao dịch ngược xu hướng "đón đầu đảo chiều" đúng tại vùng đó, bị kẹp khi vùng giữ vững và giá tiếp tục theo xu hướng lớn hơn.

**Vì sao khớp cơ chế DCA:** đây là trường hợp hiếm hoi mà "giá đi ngược hướng entry ban đầu" **mang thông tin định lượng được**, không chỉ là "tôi sai". Vùng có ranh giới xác định trước (không phải điểm giá đơn lẻ) → tự nhiên sinh ra một dải giá để triển khai tranche, và ranh giới ngoài của vùng tự nhiên là điểm invalidation — không cần đặt SL theo bội số ATR tuỳ ý như thiết kế v1.

**Độ bền:** trung bình. Khác Breakout Momentum (Tool A) ở chỗ nó không cần phá vỡ mức giá mới — nó cược vào **vùng cũ còn giá trị**, nên ít bị cạnh tranh trực tiếp bởi nhóm săn breakout thuần.

**Khác biệt cơ bản với "mean reversion" đã bị loại (DR-005 của Tool A):** mean-reversion cược "giá đi quá xa sẽ quay lại", không có điểm dừng logic ngoài SL áp đặt từ ngoài. Zone Absorption cược "xu hướng lớn hơn còn đúng, đây là nhịp rũ", và điểm dừng logic **chính là ranh giới zone bị phá** — invalidation nội tại của chính giả thuyết, không phải con số áp từ ngoài vào.

## 0.2. Ba tầng thời gian — tự suy ra, không mượn từ Tool A

Zone Absorption cần trả lời ba câu hỏi độc lập, mỗi câu cần một khung thời gian khác nhau:

| Câu hỏi | Vì sao cần khung riêng | Khung đề xuất |
|---|---|---|
| Xu hướng lớn hơn đang đi đâu? | Nếu không có xu hướng lớn hơn, "hấp thụ rồi tiếp diễn" không có gì để tiếp diễn | **1D** — cần đủ dài để lọc nhiễu, đủ ngắn để còn liên quan tới hold vài ngày |
| Zone nằm ở đâu, mạnh yếu thế nào? | Zone hình thành từ hành vi giá — cần đủ nến để một vùng "có ý nghĩa", nhưng không quá dài khiến zone cũ mất giá trị | **4H** — cân bằng giữa đủ dữ liệu hình thành zone và zone còn "tươi" |
| Khi nào triển khai từng tranche? | Cần độ phân giải đủ mịn để đặt limit order trong dải giá hẹp của zone | **1H** |

> ⚠️ **Đây không phải bê nguyên 1D/4H/1H của Tool A.** Trùng số nhưng khác lý do: Tool A dùng 1D cho TrendScore là để đo *động lượng*; ở đây 1D dùng để đo *có xu hướng lớn hơn hay không* — hai câu hỏi khác nhau, tình cờ cùng khung thời gian phù hợp. Nếu qua kiểm chứng thấy 1D quá thô cho việc lọc trend context, đây là điểm được phép đổi mà không ảnh hưởng phần còn lại.

## 0.3. Sàn & Pool — chọn theo YÊU CẦU CHIẾN LƯỢC, độc lập với Tool A về THIẾT KẾ

**Sàn:** Binance USDⓈ-M Futures, isolated, L_exchange = 5x — kế thừa vì đây là ràng buộc hạ tầng chung (sàn giao dịch), không phải lựa chọn chiến lược.

**Pool: chọn thuần theo yêu cầu của Zone Absorption, KHÔNG tham chiếu pool của Tool A khi thiết kế tiêu chí.**

> 🔴 **Sửa lỗi so với bản trước:** bản trước đề xuất "phân vùng theo rank (Tool A giữ 1-30, Tool D lấy 31-60)" — đây là **sai hướng**. Nó chọn pool để né overlap DSR, tức lấy kết luận thống kê làm tiêu chí chiến lược — ngược thứ tự đúng. Pool phải được chọn để phục vụ Zone Absorption hoạt động tốt nhất; overlap với Tool A là **hệ quả quan sát được sau đó**, không phải mục tiêu thiết kế.

```
Tiêu chí chọn pool — suy TỪ CHÍNH chiến lược Zone Absorption, không mượn Tool A:

   (i)   Volume 30D đủ lớn để volume_ratio (thành phần ZSS, §1.2)
         phản ánh tín hiệu thật, không phải nhiễu thống kê
   (ii)  Đủ lịch sử giao dịch để một zone có cơ hội được "touch" ≥1 lần
         trước khi hết hạn 40 nến 4H (§1.3) — coin quá mới không đủ dữ liệu
   (iii) Cost economics khả thi cho lệnh post-only (v7: ánh xạ config ở §3.5,
         KHÔNG phải `order_types = "limit_maker"`) — đây là thuộc tính CỦA SÀN
         (cấu trúc phí/slippage theo tier thanh khoản), áp dụng cho MỌI
         chiến lược dùng maker order, không riêng Tool A
   (iv)  Có khả năng tìm zone đối diện trong khoảng cách hợp lý để TP
         có nghĩa (§5.1)

🚪 Ngưỡng cụ thể cho (i)-(iv): [CẦN CALIBRATE bằng dữ liệu thật,
   không suy đoán trên giấy — đây là việc chạy code, không phải viết spec]
```

**Overlap với Tool A: ĐO, không THIẾT KẾ.**

```
Sau khi chọn pool theo tiêu chí trên (bước 1-2), CHẠY một phép so sánh
tập hợp với pool Tool A hiện tại để biết overlap thật (bước 3):

   overlap = |Tool_A_pool ∩ Tool_D_pool| / |Tool_A_pool ∪ Tool_D_pool|

   Nếu overlap CAO (nhiều khả năng — cả hai chiến lược đều cần thanh
   khoản tốt để hoạt động đúng, tự nhiên hội tụ về cùng nhóm coin):
      → DR-007 áp dụng, DSR gộp union — CHẤP NHẬN, đây là sự thật
        về dữ liệu, không phải thất bại của việc "độc lập hoá" Tool D
   Nếu overlap THẤP:
      → DSR tách được — cũng chấp nhận, không phải thành tích thiết kế

   🔴 KHÔNG được chọn lại pool sau khi thấy overlap cao để "cố tách
   cho bằng được" — đó là quay lại đúng lỗi đã sửa ở trên (lấy kết
   luận DSR làm tiêu chí chọn pool).
```

---

# PHẦN 0b — 🆕 v3.3: POOL (sửa §0.3)

## 0.3b. Loại BTC/ETH khỏi pool GIAO DỊCH, giữ nguyên dữ liệu

```
🔒 QUYẾT ĐỊNH VẬN HÀNH (không phải kết luận từ dữ liệu):
   BTCUSDT và ETHUSDT KHÔNG vào pool giao dịch Tool D.

   Lý do được ghi nhận là HỢP LỆ:
      Đây là hai thị trường hiệu quả nhất, nhiều người chơi chuyên
      nghiệp nhất → giả thuyết "vùng cũ còn giá trị" dễ bị arbitrage
      hết nhất ở đó. Lập luận theo CƠ CHẾ, đúng chuẩn §0.1.

   ⚠️ Lý do KHÔNG hợp lệ, ghi lại để không tái sử dụng về sau:
      ❌ "vốn cao" — sai cơ chế. USDⓈ-M perp mua theo notional, min
         notional ~5-20 USDT như mọi cặp khác. BTC không tốn vốn hơn.
      ❌ "lợi nhuận thấp" — hệ thống đã tự bù. Biến động thấp → zone
         hẹp → R_eff nhỏ → size LỚN hơn (§3.2). Định cỡ theo RỦI RO,
         không theo notional cố định.

🔴 DỮ LIỆU BTC/ETH VẪN PHẢI TẢI VÀ GIỮ:
   (a) 🔴 v6 — LÝ DO CŨ ĐÃ CHẾT: §2.4 (BTC regime) bị XOÁ ở v6.
       Ghi lại để không ai xoá luôn việc tải dữ liệu vì thấy lý do
       không còn. Nếu §2.4 quay lại qua Idea Queue, lý do này sống lại.
   (b) Hai mã này tạo thành xương sống của tập EXPLORE (§9c.4b)
       — ĐÂY GIỜ LÀ LÝ DO DUY NHẤT, và nó đủ.
```

## 0.3c. Mở rộng pool — mục tiêu ~100 mã, tiêu chí là hàng rào cứng

```
Mục tiêu:  ~100 mã (tăng từ 30-50)
Lý do THẬT (mạnh hơn "nhiều cơ hội hơn"):
   §10.2 yêu cầu ≥150 lệnh/năm. Một setup phải qua MƯỜI điều kiện
   nối bằng AND (ZSS, touch, tuổi zone, zone_width, trend 1D, đồng
   thuận 4H, ADX, tuổi trend, xác nhận entry, đệm thanh lý). Với
   30-50 mã, nhiều khả năng KHÔNG ĐỦ MẪU để kết luận bất cứ điều gì.
   → Mở pool là cách DUY NHẤT tăng mẫu mà KHÔNG nới lỏng bộ lọc.

🔴 BA CẢNH BÁO:
   (i)  Tiêu chí (i)-(iv) §0.3 là HÀNG RÀO CỨNG. Không ép cho đủ 100.
        Pool = số mã vượt tiêu chí, có thể 73 hay 88. Coin rank 60-100
        volume mỏng → volume_ratio trong ZSS nhiễu → hỏng chính thành
        phần đo dòng tiền.
   (ii) Số lệnh gấp đôi ≠ bằng chứng mạnh gấp đôi. Altcoin tương quan
        0.7-0.85 → SỐ MẪU HIỆU DỤNG nhỏ hơn số lệnh danh nghĩa nhiều.
        BẮT BUỘC báo cáo cả hai con số ở D0.9.
   (iii) Kiểm tra kết nạp §6.8f chặn số vị thế — 100 mã trong pool
        KHÔNG được phép thành 100 vị thế đồng thời. Thực tế 6-20.

🚪 BÁO CÁO TÁCH ở D0.9 — tốn 0 TRIAL, KHÔNG phải bộ lọc:
   (a) Theo TIER thanh khoản: Tier-2 (top alt) / Tier-3 (còn lại)
   (b) 🆕 Theo PHIÊN/GIỜ: thanh khoản crypto không đều — giờ châu Á
       thấp, cuối tuần mỏng, quanh mốc funding 8h có nhiễu

   🔴 CHỈ BÁO CÁO, KHÔNG biến thành bộ lọc ở vòng này. Biến thành bộ
      lọc = +2 tham số = +12 trial, trong khi chưa có bằng chứng nào.
      Nếu số liệu D0.9 cho thấy khác biệt rõ → đăng ký thành arm
      ablation ở vòng sau, không sửa tại chỗ.

   Cho bằng chứng để quyết ở D5, thay vì loại trước rồi không bao giờ
   biết mình đúng hay sai.
```

---

---

# PHẦN 0c — 🔴 v5: TƯƠNG THÍCH FREQTRADE

> **Quyết định đã chốt:** Tool D dùng **Freqtrade** làm repo cốt lõi.
>
> 🔴 **Làm rõ trước, vì đây là nguồn hiểu nhầm nguy hiểm:** **FreqAI KHÔNG PHẢI Freqtrade.** FreqAI là một **module tuỳ chọn** bên trong Freqtrade. Dùng Freqtrade không có nghĩa phải dùng FreqAI — chỉ cần không bật nó. Không có xung đột nào ở đây.
>
> Nhưng khi rà toàn bộ Freqtrade, có **ba module khác nguy hiểm hơn FreqAI** đối với kiến trúc quản trị của Tool D. Phần này liệt kê từng module.

## 0c.1. ✅ MODULE DÙNG — nền tảng của Tool D

| Module | Vai trò trong Tool D |
|---|---|
| Backtesting engine | Chạy D0.9, WFO |
| Pairlist / whitelist | Pool ~100 mã (§0.3c) — nhưng dùng **H1-D point-in-time viết riêng**, không dùng VolumePairList mặc định (nó có lookahead) |
| Exchange abstraction | Binance USDⓈ-M, isolated margin |
| **`adjust_trade_position`** | 🔴 **Cơ chế cốt lõi của tranche 2/3.** Không có nó thì không triển khai được DCA neo zone |
| `custom_stoploss` | Đặt SL neo zone (D0.2) — nhưng **KHÔNG** dùng để dời SL |
| Dry-run | Bước D11 |
| Telegram / WebUI | Chỉ theo dõi. **KHÔNG** dùng nút mua/bán thủ công |

## 0c.2. 🔴 MODULE CẤM TUYỆT ĐỐI

```
❌ HYPEROPT — MỐI NGUY LỚN NHẤT, lớn hơn FreqAI nhiều

   Hyperopt tự động dò tham số. MỘT lệnh chạy 500 epoch = 500 PHÉP THỬ.
   Ngân sách cả dự án là N = 114 (DR-010).
   → MỘT lệnh hyperopt phá huỷ toàn bộ DR-010 trong vài giờ, và không
     có cách nào khôi phục — bạn không thể "quên" kết quả đã thấy.
   → Đây là lý do CẤM này quan trọng hơn cấm FreqAI: hyperopt dễ chạy
     hơn nhiều, chỉ một dòng lệnh, và trông hoàn toàn vô hại.

   🔴 Calibrate 12 tham số PHẢI làm THỦ CÔNG, từng giá trị một, mỗi
      lần ghi trial_registry (§9c.2). Chậm là TÍNH NĂNG, không phải lỗi.
   🔴 Thêm vào H16: grep repo, phát hiện `hyperopt` trong bất kỳ script
      hay lệnh nào → CHẶN CHẠY.

❌ FREQAI — huấn luyện lại liên tục = số phép thử ngầm VÔ HẠN

   FreqAI tự huấn luyện lại mô hình trong lúc live để thích ứng thị
   trường. Ba lý do không tương thích:
     (a) Không đếm được N → DSR vô nghĩa
     (b) Backtest thật của FreqAI tốn thời gian tương đương chạy dry
         → KHÔNG chạy được GATE D0.9 trên nó
     (c) Mô hình tự thích ứng KHÔNG BAO GIỜ "sai" một cách quan sát
         được — nó chỉ thích ứng. Ngược lại toàn bộ triết lý bác-bỏ-được.

   Muốn thử ML → đó là GIẢ THUYẾT RIÊNG, ngân sách riêng, lockbox
   riêng. Không phải nâng cấp cho Tool D.

❌ EDGE POSITIONING — xung đột trực tiếp với D0.1

   Edge tự tính win rate / risk-reward rồi ĐIỀU CHỈNH KÍCH CỠ VỊ THẾ.
   D0.1 quy định size suy ngược từ ngân sách rủi ro cố định.
   → Hai cơ chế định cỡ chạy song song = quay lại đúng mâu thuẫn §6.8e
     vừa gỡ. Đặt `edge.enabled = false`, và L-Z24 kiểm điều đó.

❌ TRAILING STOP DỰNG SẴN của Freqtrade
   Tool D có TP2 trail riêng (§5.1) neo vào ATR và zone. Bật cả hai =
   hai logic thoát lệnh tranh nhau. Dùng `custom_exit`, không dùng
   `trailing_stop = true`.
```

## 0c.3. ⚠️ MODULE CÓ ĐIỀU KIỆN

| Module | Điều kiện |
|---|---|
| **Protections** (`CooldownPeriod`, `StoplossGuard`, `MaxDrawdown`) | ⚠️ Chồng chéo với DG1–DG8 và `mult_dd`. **Chọn MỘT nguồn sự thật.** Đề xuất: dùng logic Tool D, tắt protections — nếu không, hai hệ thống sẽ chặn lệnh vì lý do khác nhau và Decision Log không giải thích được vì sao lệnh bị bỏ |
| `minimal_roi` | ⚠️ Đặt `{"0": 10}` (thực tế là tắt). TP do §5.1 quyết định |
| `stoploss` (tĩnh) | ⚠️ Đặt giá trị rất rộng làm lưới cuối. SL thật do `custom_stoploss` neo zone |
| `use_exit_signal` | ✅ Bật — DG6/DG8 cần nó |
| `position_adjustment_enable` | ✅ **Bắt buộc bật** cho tranche |
| Lookahead-analysis dựng sẵn | ⚠️ **Cho false positive với chiến lược khớp lệnh trễ như tranche** (GitHub issue #12168). Phải đối chiếu thủ công bằng H4-D/H4-D-b, không tin kết quả tự động |

## 0c.4. Test bắt buộc

```
L-Z24 🆕 v5 — config Freqtrade thoả TẤT CẢ:                🔴 CRITICAL
         freqai.enabled          = false
         edge.enabled            = false
         trailing_stop           = false
         position_adjustment_enable = true
         use_exit_signal         = true
         protections             = []   (hoặc lý do ghi rõ)

L-Z25 🆕 v5 — grep toàn repo + lịch sử lệnh: KHÔNG có `hyperopt`
         Phát hiện một lần chạy hyperopt → trial_registry MẤT HIỆU
         LỰC, phải khai lại N từ đầu                       🔴 CRITICAL
```

---

# PHẦN 0d — 🆕 v7: TOÀN VẸN PHÉP ĐO — LÀM TRƯỚC MỌI DÒNG LOGIC CHIẾN LƯỢC

> **Nguồn:** ba sự cố nặng nhất trong nhật ký Tool A (TA-0087, TA-0096, TA-0144) có cùng một hình dạng: *một đầu vào không ai ghi lại đã làm sai kết quả mà không để lại dấu hiệu nào, và người vận hành tiếp tục xây phân tích lên con số sai đó.* Với Tool D, rủi ro này **cao hơn**, vì (a) DCA làm mẫu số của mọi chỉ số mơ hồ hơn lệnh đơn, (b) `adjust_trade_position()` là hàm có khoảng cách backtest-vs-live lớn nhất của Freqtrade (§9b D6), (c) toàn bộ khung N/DSR/lockbox dựa trên **đếm số lần chạm dữ liệu** — một lần chạy nhiễm tham số không chỉ làm sai một con số, nó làm hỏng sổ ngân sách trial.

> 🔴 **Vì sao đây là D0-PRE, không phải H-hardening:** mọi con số sinh ra trước khi PHẦN 0d hoạt động đều **không đáng tin theo định nghĩa**, và không có cách nào "tin lại" chúng về sau. Rẻ nhất là làm trước.

## 0d.1. Bảy ràng buộc

```
════ 0d.1 — GUARD FILE THAM SỐ ẨN (LD-01, LD-02) ════

   Freqtrade tự ghi <TênStrategy>.json cạnh file strategy sau MỖI lần
   hyperopt. File này ĐÈ `default=` của mọi `*Parameter` ở mọi lần
   chạy sau — kể cả backtesting — và thường nằm trong .gitignore nên
   không lộ qua git status / git SHA / lệnh chạy. Tool A dính BA lần.

   🔴 Tool D CẤM hyperopt (§0c.2), NHƯNG guard vẫn bắt buộc, vì:
      (a) một lần chạy hyperopt "nhầm tay" là đủ để file tồn tại mãi
      (b) file có thể được chép từ máy khác / repo Tool A
      (c) chi phí guard ≈ 0 (đọc file JSON + so sánh)

   RÀNG BUỘC:
   • Mọi script sinh số liệu dùng cho quyết định (backtest, WFO,
     ablation, lockbox, periodic_report) PHẢI gọi `measurement_guard()`
     TRƯỚC khi làm bất cứ việc gì tốn thời gian (LD-39).
   • Guard phát hiện <Strategy>.json (kể cả JSON hỏng → present=True)
     → DỪNG, in đúng nội dung file. KHÔNG tự xoá (có thể là kết quả
     người vận hành đang cố ý dùng). Cờ tường minh `--with-params-file`
     là cách DUY NHẤT đi tiếp, và cờ đó được ghi vào provenance.
   • 🔴 DANH SÁCH ĐÓNG các "đường sinh số liệu" (mỗi đường = 1
     entrypoint) ghi ở §0d.3. Entrypoint mới PHẢI vào danh sách VÀ
     vào test L-Z36 "mọi entrypoint đều gọi guard". Tool A có guard,
     nối vào 3 script, bỏ sót đúng script nuôi gate → lỗi tái phát
     nguyên vẹn.

════ 0d.2 — CẤM `*Parameter` CỦA FREQTRADE (hệ quả LD-01 + LD-18) ════

   Tool D đọc MỌI tham số từ `tool_d_config.yaml` (§6.9.5) — nguồn
   sự thật duy nhất. KHÔNG dùng IntParameter / DecimalParameter /
   CategoricalParameter / BooleanParameter.

   Lý do: (a) `*Parameter` là cửa vào của hyperopt và của file .json
   ẩn ở 0d.1 — không dùng thì hai bề mặt tấn công đó đóng theo;
   (b) LD-18: Tool A phải rà 8 điểm gọi để chúng đọc `.value` thay
   vì hằng số — một điểm sót là một bộ số sai âm thầm. Với một nguồn
   duy nhất (YAML → dict → truyền vào hàm), lớp lỗi này không tồn tại.
   → Test L-Z37: grep repo, KHÔNG có `Parameter(` từ freqtrade.strategy.

════ 0d.3 — CACHE LÀ NGUỒN NHIỄM BẬC HAI (LD-03) ════

   • `freqtrade backtesting` MẶC ĐỊNH cache kết quả 1 ngày. Sửa code
     rồi chạy lại vẫn ra số y hệt — Tool A chỉ phát hiện vì hai lần
     chạy trùng nhau đến từng chữ số.
     → Mọi lệnh backtest/WFO của Tool D: `--cache none`. KHÔNG ngoại lệ.
     → L-Z38: wrapper script từ chối chạy nếu thiếu `--cache none`.
   • Cache tự viết (resume WFO) PHẢI ghi kèm `params_hash` +
     `code_sha` + `data_hash`; đọc lại mà hash lệch → CẢNH BÁO TO và
     KHÔNG dùng. Quy trình có bước "xoá cache trước khi đo lại sau
     khi đổi mặc định".

════ 0d.4 — ENV CHỈ CHO VẬN HÀNH; CẢI TIẾN PHẢI THÀNH MẶC ĐỊNH (LD-04) ════

   Tool A: ba cải tiến đã đo, chỉ bật được qua biến môi trường;
   đường live cố ý bỏ qua env → bot thật chạy bộ tham số cũ VĨNH VIỄN.
   Không ai phát hiện vì backtest (có env) và live (không env) chưa
   bao giờ được đối chiếu.

   • Env CHỈ cho: khoá/mở, chế độ (dry/live/testnet), đường dẫn.
     KHÔNG BAO GIỜ cho tham số tín hiệu hay ngưỡng. L-Z39 grep.
   • 🚪 "ĐIỂM KIỂM SOÁT" — gate chính thức sau MỖI lần một tham số
     đổi trạng thái (DR-012 Hạng 2, hoặc mở khoá đóng băng):
        1. đưa giá trị mới vào tool_d_config.yaml, commit
        2. chạy lại MỘT backtest điểm kiểm soát KHÔNG set env nào,
           `--cache none`
        3. kết quả phải KHỚP với bản ghi registry của trial đã chấp
           nhận giá trị đó (sai số ≤ 0.1% expectancy)
        4. lệch → giá trị CHƯA được áp, điều tra trước
     Ghi vào registry như một trial `budget_line: CTRL`, KHÔNG tính
     vào N (không phải phép thử mới — là kiểm tra tái lập).

════ 0d.5 — KHỐI XUẤT XỨ (PROVENANCE) CHO MỌI CON SỐ (LD-05) ════

   Mỗi bản ghi kết quả (trial / fold / arm / lần chạm lockbox /
   periodic_report) PHẢI kèm:
      params_source        : "yaml" | "params_file" | "env"
                             (v7: chỉ "yaml" là hợp lệ; hai giá trị
                              kia tồn tại để guard có chỗ ghi vi phạm)
      params_effective     : dict tham số THẬT đã dùng (không phải
                             tên file — nội dung)
      git_sha              : commit
      reproducible_from_sha: false nếu working tree còn file chưa
                             commit (git SHA một mình KHÔNG đủ khi
                             nhiều phiên làm việc song song — LD-40)
      data_hashes          : {file: sha256} cho TỪNG file dữ liệu đầu
                             vào; file thiếu ghi "MISSING", KHÔNG bỏ
                             qua im lặng
      cache_mode           : "none" (bắt buộc)
      guard_passed         : true
   → L-Z40: bản ghi thiếu bất kỳ khoá nào ở trên = KHÔNG HỢP LỆ,
     không được dùng làm đầu vào gate.

════ 0d.6 — BA TRẠNG THÁI DỮ LIỆU, KHÔNG GỘP THÀNH 0 (LD-10) ════

   `0`, `[]`, `None` bị gộp làm một là nguồn "đèn xanh rỗng" kinh
   điển: một tiêu chí hiện "sạch" chỉ vì CHƯA AI CANH.

   • Mọi trường trạng thái/chỉ số phân biệt tối thiểu:
        pending     — chưa từng đo
        unreadable  — có nguồn nhưng hỏng / API lỗi
        ok          — đo được (kể cả kết quả rỗng, ví dụ 0 lệnh)
   • KHÔNG BAO GIỜ bịa 0.0 khi chưa đo. Trả None + "chưa đo được".
   • Giá trị lính canh (-1.0, "UNKNOWN") KHÔNG lọt ra báo cáo.
   • KHÔNG hiển thị số cũ kèm cảnh báo — một con số trên màn hình
     được đọc như câu trả lời bất kể chữ bên cạnh. Thà để trống.
   • Áp vào periodic_report.py (§12d.2) và bảng trạng thái GATE
     (§10.2): dòng tổng ghi "đã audit N/M (X đạt, Y chưa đạt,
     Z chưa đo được)" — KHÔNG chỉ đếm cái đạt (LD-33).

════ 0d.7 — CHẨN ĐOÁN: "BOT SAI" HAY "TẦNG ĐO SAI"? (LD-06) ════

   Khi thấy chỉ số bất thường, câu hỏi ĐẦU TIÊN — trước khi mở code
   chiến lược:
      "Lệnh THẬT trên sàn có đúng thiết kế không?"
   Trả lời bằng DỮ LIỆU LỆNH THẬT (giá đặt, khối lượng, giá SL thật
   trên sàn), đối chiếu với Decision Log (§8).
      → Khớp   → lỗi ở TẦNG ĐO. Sửa tầng đo. KHÔNG đụng chiến lược.
      → Lệch   → lỗi ở BOT. Bây giờ mới mở code chiến lược.
   Tool A đã từng suýt sửa logic chiến lược ĐANG ĐÚNG vì mẫu số của
   tầng đo sai (LD-08). Với Tool D, DCA làm hai lớp này khó tách hơn
   → thứ tự này là BẮT BUỘC, ghi vào research-log mỗi lần chẩn đoán.
```

## 0d.2. Danh sách ĐÓNG các đường sinh số liệu

```
Mỗi entrypoint dưới đây PHẢI gọi measurement_guard() ở dòng đầu tiên
sau parse tham số. Thêm entrypoint = thêm dòng ở đây + thêm vào L-Z36.

   E1  run_backtest.py         (wrapper cho freqtrade backtesting)
   E2  run_wfo.py              (H3-D orchestrator)
   E3  run_ablation.py         (D0.9, 9 arm × 2 hướng)
   E4  touch_lockbox.py        (DR-011 — thêm: ghi lockbox_access.log)
   E5  periodic_report.py      (§12d.2)
   E6  trial_ledger_audit.py   (H16 — tự kiểm cả chính nó)
   E7  build_pool.py           (H1-D point-in-time)
   E8  backfill_data.py        (H19 — sao lưu trước, verify sau)

🔴 Không có E9 "script thử nghiệm nhanh". Nếu cần "xem thử", đó là
   E1 với budget_line = B3 và ghi registry. (DR-010 quy tắc 1)
```

## 0d.3. Test bắt buộc

```
L-Z36 🔴 CRITICAL — MỌI entrypoint E1–E8 gọi measurement_guard()
      trước lệnh tốn thời gian đầu tiên. Test cơ chế: import từng
      module, kiểm hàm main gọi guard. Entrypoint không trong danh
      sách mà sinh file kết quả → FAIL.
L-Z37 🔴 CRITICAL — grep repo: KHÔNG có `IntParameter|DecimalParameter|
      CategoricalParameter|BooleanParameter|RealParameter`.
      KHÔNG có <Strategy>.json trong thư mục strategies (guard).
L-Z38 wrapper backtest từ chối chạy nếu thiếu `--cache none`.
L-Z39 grep repo: KHÔNG có os.environ / os.getenv đọc tên tham số
      Tầng B/C (danh sách tên lấy từ tool_d_config.yaml).
L-Z40 🔴 CRITICAL — mọi bản ghi kết quả có đủ 7 khoá provenance
      (0d.5); params_source == "yaml"; guard_passed == true.
      Thiếu → bản ghi KHÔNG HỢP LỆ cho gate.
L-Z41 periodic_report và bảng GATE: không có giá trị lính canh;
      mọi chỉ số có trạng thái ∈ {pending, unreadable, ok}.
```

---

# PHẦN 1 — ZONE DETECTION ENGINE

Đây là chỉ báo trung tâm của Tool D — vai trò tương đương "TrendScore + Vote 5 họ" của Tool A, nhưng đo một thứ hoàn toàn khác: **có một vùng giá đáng tin để hấp thụ hay không.**

## 1.1. Định nghĩa Zone — bằng số, không mô tả

```
Zone ứng viên tại nến 4H thứ i:
   • i là SWING POINT: giá trị cao/thấp nhất trong cửa sổ [i−k, i+k], k=3
     (tức là: cao/thấp hơn 3 nến trước VÀ 3 nến sau)
   • Zone = [swing_price × (1 − buf), swing_price × (1 + buf)]  cho đáy
     (đảo dấu cho đỉnh), buf = 0.3 × ATR(14, 4H)/price tại i
```

> 🔴 **Vấn đề nghiêm trọng: swing point ở đây cần 3 nến SAU để xác nhận.** Tại thời điểm nến i vừa đóng, hệ thống **chưa thể biết** đó có phải swing point hay không — phải đợi thêm 3 nến 4H (12h) nữa. Đây là **lookahead cố hữu** nếu code sai. Xử lý bắt buộc ở §7.

> 🆕 **Không dùng ngưỡng nhị phân — dùng độ tin cậy tăng dần, xem §7.4.** Zone không "vô dụng hoàn toàn" trước nến i+3 rồi "đầy đủ" đúng tại i+3 — độ tin cậy tăng dần theo số nến đã thực sự trôi qua, vẫn hoàn toàn nhân quả. Chi tiết công thức và lý do ở §7.4.

## 1.2. Zone Strength Score (ZSS) — điểm mạnh yếu

Không phải mọi zone như nhau. Ba yếu tố, mỗi yếu tố đo được từ dữ liệu OHLCV thuần (không cần order-flow/orderbook — hạ tầng hiện tại không có):

```python
# (a) Số lần giá đã "tôn trọng" zone trước đó (touch count, point-in-time)
touch_count = số lần giá chạm zone rồi bật ra trong [i, hiện_tại],
              KHÔNG tính lần đầu hình thành
   # 🔴 v7 — ĐỊNH NGHĨA BẰNG SỐ (LD-35: v6 chỉ có tên, "bật ra" không
   #    đo được). Case LONG (zone đáy), trên nến 4H:
   #      CHẠM    := low  ∈ [zone_low, zone_high]
   #      BẬT RA  := cùng nến đó HOẶC nến kế tiếp có close > zone_high
   #      1 touch := một cụm nến CHẠM liên tiếp kết thúc bằng BẬT RA
   #                 (cụm liên tiếp đếm 1, không đếm mỗi nến)
   #      Nến có close < zone_low → KHÔNG phải touch, zone bị phá (DG1)
   #    SHORT đảo dấu. Đây là ĐỊNH NGHĨA (Cấp C, cùng loại với k),
   #    không phải ngưỡng — 0 DOF.

# (b) Volume tương đối tại thời điểm hình thành zone
volume_ratio = volume(nến swing) / volume_MA(20, 4H)

# (c) Độ nén khi tiếp cận lại (compression on approach)
#     — ATR co lại khi giá tiến về zone thường đi kèm hấp thụ thật,
#       ATR giãn ra khi tiến về zone thường là breakout xuyên qua, không hấp thụ
compression = ATR(14,4H)_hiện_tại / ATR(14,4H)_lúc_hình_thành_zone

ZSS = w_a × min(touch_count, 3)/3
    + w_b × clip(volume_ratio, 0, 2)/2
    + w_c × clip(2 − compression, 0, 2)/2
    # 🔒 v6 — ĐÓNG BĂNG: w_a = w_b = w_c = 1/3.  KHÔNG tune.
    # frozen_rationale: prior KHÔNG-THÔNG-TIN. Bất kỳ bộ nào khác là
    # một TUYÊN BỐ về tầm quan trọng tương đối mà chưa có bằng chứng.
    # ZSS dùng làm hệ số LIÊN TỤC → thứ tự xếp hạng quan trọng hơn giá
    # trị tuyệt đối.  (v5 có BA giá trị khác nhau cho cùng tham số này:
    # 0.4/0.3/0.3 ở đây, 1/3 ở DR-010, [0.333,0.333,0.334] ở YAML.)
```

> **Vì sao không dùng CVD/order-flow:** hạ tầng dữ liệu hiện tại (Freqtrade + Binance klines) không có orderbook lịch sử đáng tin. Dùng volume/ATR proxy là lựa chọn có ý thức về giới hạn dữ liệu, không phải sơ suất. Nếu sau này có nguồn OI/CVD đáng tin, ZSS nên thêm thành phần — nhưng đó là thay đổi Phần 16-tương-đương, ngoài phạm vi v2 này.

## 1.3. Ngưỡng nhận zone hợp lệ

```
ZSS ≥ 0.5   [CẦN CALIBRATE]   → zone đủ mạnh để cân nhắc
touch_count ≥ 1                → KHÔNG dùng zone mới hình thành lần đầu,
                                  chưa có bằng chứng nó "được tôn trọng"
tuổi zone ≤ 40 nến 4H (~ 6.7 ngày)  → zone quá cũ mất liên quan
```

> Điều kiện `touch_count ≥ 1` quan trọng hơn nó trông: nó buộc hệ thống **chờ bằng chứng thứ hai** trước khi tin một vùng giá, thay vì tin ngay lần đầu tiên nhìn thấy — đây là hàng rào chống overfitting-vào-nhiễu tự nhiên, không cần thêm tham số.

---

# PHẦN 1b — 🆕 v3.3: NHIỀU ZONE TRÊN CÙNG MỘT COIN

> Chèn sau §1.3. Gỡ lỗ hổng: spec chưa từng nói xử lý ra sao khi nhiều zone cùng hợp lệ, và công thức định cỡ ở §6.2 mâu thuẫn với D0.1 (đã gỡ ở §6.8e).

## 1.3b. Bốn quy tắc — TẤT CẢ 0 tham số mới

```
QUY TẮC 1 — GỘP ZONE KỀ NHAU (không phải chọn giữa chúng)

   NẾU hai zone CÙNG LOẠI (cùng đáy hoặc cùng đỉnh) có khoảng cách
   biên < buf   (buf = 0.3 × ATR(14,4H)/price — ĐÃ CÓ ở §1.1)
      → GỘP: zone = [min(low_A,low_B), max(high_A,high_B)]
      → ZSS_gộp = max(ZSS_A, ZSS_B)
      → p1/p2/p3 trải trên zone đã gộp; SL ngoài biên GỘP

   Lý do kinh tế: hai vùng thanh khoản kề nhau LÀ một vùng hấp thụ
   rộng. Thuật toán swing cắt nó làm đôi là giả tạo, không phải thực tế.

   🔴 TRẦN CHỐNG GỘP DÂY CHUYỀN:
      zone sau gộp ≤ 2 × zone rộng nhất trong các zone thành phần.
      Không có trần này, gộp bắc cầu A-B-C-D sẽ nuốt cả biểu đồ và
      sinh ra một "zone" vô nghĩa với R_eff khổng lồ.
   🔴 GỘP PHẢI NHÂN QUẢ: chỉ gộp các zone đã có confirm_ratio > 0 tại
      thời điểm t. Không gộp với zone chưa hình thành → H4-D phải phủ.

QUY TẮC 2 — CHỌN ZONE (áp dụng SAU khi đã gộp)

   Trong các zone hợp lệ §1.3: lấy zone mà GIÁ ĐANG CHẠM.
   Nếu giá đang chạm nhiều zone chồng lấn: lấy ZSS cao nhất.
   🔒 FROZEN — quy tắc xác định, 0 bậc tự do, KHÔNG tune.

QUY TẮC 3 — TỐI ĐA 1 VỊ THẾ / COIN / THỜI ĐIỂM
   🔒 FROZEN. Zone thứ hai chỉ xét sau khi vị thế thứ nhất đã đóng.
   (Trước v3.3 đây là hành vi MẶC ĐỊNH NGẦM của Freqtrade, không phải
    quyết định có ý thức — giờ viết tường minh.)

QUY TẮC 4 — COOLDOWN SAU KHI ĐÓNG

   Sau khi đóng vị thế trên coin X, chờ 3 nến 4H (12h) trước khi xét
   zone mới trên X.
   🔒 Dùng lại k=3 ĐÃ CÓ ở §1.1 — 0 tham số mới.
   Lý do dùng đúng k: đó là khoảng thời gian tối thiểu để thị trường
   tạo được một cấu trúc swing mới, không phải con số tuỳ ý.

   🔴 v6 — NGOẠI LỆ ĐÃ BỊ ĐẢO NGƯỢC.

      v5 ghi: "KHÔNG cooldown nếu đóng bằng SL". Điều đó MÂU THUẪN với
      chính lý do tồn tại của Quy tắc 4, viết ngay dưới đây: "rủi ro
      thật là một cú sập kích hoạt liên tiếp nhiều lệnh trên cùng
      coin". Vị thế đóng bằng SL CHÍNH LÀ ca một cú sập. Ngoại lệ cũ
      tắt cooldown đúng ở kịch bản mà cooldown được tạo ra để chặn,
      và bật cooldown ở ca DG6-A (ATR giãn ≥1.8× — cũng là cú sập).
      Logic bị đảo.

      ✅ CÓ cooldown (3 nến 4H) khi đóng bằng:  SL · DG6-A/B/C/D · DG7
      ✅ MIỄN cooldown khi đóng bằng:            TP1+TP2 · DG8 TIME_STOP

      Lý do phân định: hai nhóm đầu đóng vì GIẢ THUYẾT SAI hoặc THỊ
      TRƯỜNG ĐANG XẤU — thông tin nói "đừng vào lại ngay". Hai nhóm
      sau đóng vì giả thuyết ĐÚNG (TP) hoặc HẾT HẠN (TIME_STOP) —
      không mang thông tin bất lợi nào về coin đó.
      🔒 0 tham số mới (vẫn dùng k = 3).
```

> **Về mối lo phí giao dịch:** entry dùng lệnh post-only (`PO`, §3.5), TP cũng là limit — churn không phải rủi ro chính. Rủi ro thật là **một cú sập kích hoạt liên tiếp nhiều lệnh trên cùng coin**, và Quy tắc 4 chặn đúng cái đó. Zone cách xa nhau KHÔNG làm tăng rủi ro mỗi lệnh, vì SL neo vào chính zone đang giao dịch — zone khác cách 15% không ảnh hưởng gì. Nó chỉ ảnh hưởng TP (§5.1), và ca "zone đối diện quá xa" đã có `TP_fallback`.

---

---

# PHẦN 2 — CONTEXT TREND FILTER

Trả lời câu hỏi: "xu hướng lớn hơn có đang tồn tại để mà tiếp diễn không?" Không có bộ lọc này, Zone Absorption thoái hoá thành mean-reversion thuần (chính là ứng viên đã bị loại).

> 🆕 **Nâng cấp sau phản biện — bản trước quá tối giản cho mức rủi ro treo vào nó.** Toàn bộ logic "an toàn để DCA" phụ thuộc vào trend còn đúng — một bộ lọc yếu ở đây khuếch đại rủi ro của cả hệ thống. Bổ sung §2.2, §2.3 dưới đây, không thay §2.1.

## 2.1. Định nghĩa gốc

```python
# Trên khung 1D
ema_fast = EMA(20, 1D)
ema_slow = EMA(50, 1D)

trend_dir = "UP"   if ema_fast > ema_slow and slope(ema_slow, 10) > 0
       else "DOWN" if ema_fast < ema_slow and slope(ema_slow, 10) < 0
       else "FLAT"

trend_strength = ADX(14, 1D)   # đo ĐỘ MẠNH, tách khỏi HƯỚNG
```

## 2.2. 🆕 Xác nhận đa khung — bắt buộc

```python
# Cùng công thức §2.1, tính thêm trên 4H
trend_dir_4H = ... (cùng công thức, timeframe 4H)

XÁC NHẬN = trend_dir(1D) == trend_dir_4H   # PHẢI đồng thuận cả hai khung
```

**Vì sao bắt buộc, không phải tuỳ chọn:** đây đúng loại sai lầm nguy hiểm nhất cho một chiến lược DCA — 1D "trông" như uptrend (EMA cross còn dương) trong khi cấu trúc 4H đã bắt đầu gãy (giá tạo đỉnh thấp dần). Nếu chỉ nhìn 1D, hệ thống tin nhầm trend còn nguyên và DCA vào đúng lúc xu hướng thật đang đảo — kịch bản thua lỗ nặng nhất mà bạn lo ngại.

## 2.3. 🆕 Tuổi xu hướng — không dùng cú cross vừa xảy ra

```
EMA20/50 (1D) đã cross theo đúng hướng ≥ 5 ngày   [CẦN CALIBRATE]
```

Một trend vừa cross hôm qua chưa đủ bằng chứng để tin — DCA vào một trend "mới toanh, chưa kiểm chứng" có rủi ro đảo chiều cao hơn nhiều so với trend đã đứng vững một thời gian.

## 2.4. 🔴 v6 — ĐÃ XOÁ: Regime macro BTC

```
XOÁ khỏi spec. Chuyển sang Idea Queue (§9c.7) như một giả thuyết
Loại A hợp lệ cho vòng sau.

LÝ DO XOÁ — ba điểm, không phải "thấy thừa":
   (1) Nó tiêu 1 bậc tự do (ngưỡng "ngược hẳn") = 6 trial B1,
       nhưng KHÔNG có arm ablation nào trong 9 cấu hình của B2
       bật/tắt được nó. Z0-T0 bỏ toàn bộ Phần 2, Z0-T1 giữ 4H —
       cả hai đều không cô lập được §2.4.
   (2) Nó không nằm trong điều kiện vào lệnh mặc định (§2.5), tức
       là một cơ chế TUỲ CHỌN đang tiêu ngân sách của cơ chế BẮT BUỘC.
   (3) Giữ nó vi phạm đúng nguyên tắc mà LỖI 9 (Phụ lục A) được viết
       ra để sửa: "chỉ báo phải tự chứng minh chỗ đứng bằng ablation".
       §2.4 được miễn trừ vì "mới và tuỳ chọn" — đó là đặc quyền theo
       nhãn, không phải bằng chứng.

⚠️ ĐIỀU KHÔNG THAY ĐỔI: rủi ro tương quan BTC–altcoin (0.7–0.85) là
   CÓ THẬT. Nó đã được xử ở chỗ khác và mạnh hơn: §6.8d bắt định cỡ
   danh mục với GIẢ ĐỊNH TƯƠNG QUAN = 1 — tức đã giả định trường hợp
   xấu nhất, chặt hơn một bộ lọc regime nhị phân.
   → Xoá §2.4 KHÔNG để hở rủi ro tương quan.

🚪 Muốn đưa lại: qua Idea Queue, tiêu 1 slot NGÂN SÁCH A, kèm một arm
   ablation riêng. Không được "thêm lại vì thấy hợp lý".
```

## 2.5. Điều kiện vào lệnh theo hướng zone — cập nhật

```
LONG tại zone đáy  →  trend_dir(1D) == "UP"    AND §2.2 xác nhận
                       AND trend_strength ≥ 20  AND §2.3 đủ tuổi
SHORT tại zone đỉnh →  tương tự, đảo hướng
FLAT, strength thấp, hoặc 1D/4H không đồng thuận → KHÔNG vào —
   loại thẳng thay vì cố gate mềm, đây chính là ca dễ lẫn với
   mean-reversion nhất
```

> ⚠️ **Cân nhắc cardinality:** §2.2 và §2.3 cộng thêm 2 điều kiện (không phải bậc tự do tune tự do — 4H timeframe cố định, chỉ "5 ngày" ở §2.3 là [CẦN CALIBRATE], tính 1 bậc tự do mới). Chấp nhận đánh đổi này vì mức rủi ro của DCA đòi hỏi trend filter đáng tin hơn phiên bản tối giản trước.

---

# PHẦN 2b — 🆕 v3.2: CHÂN TRỜI HIỆU DỤNG CỦA CHỈ BÁO

> Chèn ngay sau PHẦN 2, trước PHẦN 3. Gỡ LỖI 9 một phần và làm nền cho PHẦN 4b.

## 2b.1. Bảng chân trời — mọi chỉ báo, mọi tầng

Chân trời hiệu dụng của EMA(N) tính theo trọng tâm khối lượng = (N−1)/2 chu kỳ; bộ nhớ thực dụng ~N chu kỳ. ADX dùng làm mượt Wilder nên chân trời thực ~2×N.

| Tầng | Chỉ báo | Chân trời hiệu dụng | Vai trò THẬT |
|---|---|---|---|
| **Vĩ mô** | EMA20/50 (1D) + slope(EMA50,10) — §2.1 | **~20–50 ngày** | 🚫 **VETO** — không dự báo hướng ngắn hạn |
| | ADX(14, 1D) ≥ 20 — §2.5 | ~28 ngày | 🚫 Đo **ĐỘ MẠNH**, không đo hướng |
| | Tuổi trend ≥ 5 ngày — §2.3 | Bộ lọc | 🚫 Loại cú cross non |
| **Trung hạn** | **EMA20/50 (4H)** — §2.2 | **3,3 – 8,3 ngày** | ✅ **Chỉ báo HƯỚNG khớp với hold** |
| | Zone 4H, k=3 nến xác nhận — §1.1 | 🔴 v6: xác nhận TĂNG DẦN — dùng được từ i+1 (4h, `confirm_ratio` 0,33 → size 1/3), đầy đủ tại i+3 (12h). Zone sống ≤ 6,7 ngày (§1.3) | ✅ Vị trí + hướng ngụ ý (zone đáy → LONG) |
| | ZSS: touch/volume/compression — §1.2 | Theo cửa sổ hình thành zone | ✅ Chất lượng, không phải hướng |
| **Ngắn hạn** | **Rejection wick / RSI divergence (1H)** — §3.3b | **vài giờ – 1 ngày** | ✅ **Tín hiệu đảo chiều thật** |
| | ATR(14, 1H) — §6.4, DG6-A, TP2 | 14 giờ | Đo biến động |

## 2b.2. Phân định VETO vs TÍN HIỆU HƯỚNG — sửa một hiểu nhầm phổ biến

```
🔴 HƯỚNG NGẮN HẠN KHÔNG do tầng 1D quyết định.

   🔴 v6 — CÒN HAI TẦNG (§3.3c EMA9/21 15m đã bị XOÁ):
      §2.2  EMA20/50 (4H)          → 3,3 – 8,3 ngày
      §3.3b price action (1H)      → vài giờ – 1 ngày

   Hai tầng này trải từ vài giờ tới ~8 ngày → VẪN KHỚP với hold 4
   ngày (max_hold_bars = 24 nến 4H, §4b.3). Việc bỏ tầng 15m KHÔNG
   để hở khoảng nào trong dải: 15m chỉ chồng lên phần dưới của dải
   1H, không mở rộng dải.

   Tầng 1D (§2.1/2.3/2.5) là ngoại lệ duy nhất: lệch 20–50× so với
   hold dự kiến. Nó CHỈ hợp lệ với vai trò VETO, KHÔNG phải nguồn edge.

⚠️ Đính chính một cách hiểu sai cần ghi lại: KHÔNG có chỉ báo nào
   trong spec đo "xu hướng 1 năm". Cú cross EMA20/50 trên 1D phát
   hiện chuyển dịch ở thang ~1–2 THÁNG. Yêu cầu "phải biết xu hướng
   trong tháng đó" ĐÃ ĐƯỢC ĐÁP ỨNG bởi §2.1.

🔴 Vấn đề thật KHÔNG phải độ dài, mà là ĐỘ TRỄ:
   Cú cross EMA20/50 xác nhận chuyển dịch đã bắt đầu 20–40 ngày trước.
   §2.3 bắt chờ thêm ≥5 ngày sau cross.
   → Khi vào lệnh, xu hướng "được xác nhận" đã chạy ~1–1,5 tháng.
   → Với hold vài ngày, đây là cược vào phần ĐUÔI của xu hướng già.
   → Điều này KHÔNG tự động sai — nhưng chỉ hợp lệ nếu 1D là VETO.
     §10.1b tồn tại để KIỂM CHỨNG chứ không giả định điều đó.
```

> 🔴 **KHÔNG được rút ngắn tầng 1D theo trực giác để "khớp hold hơn"** (VD đổi EMA20/50 thành EMA10/20, hoặc bỏ hẳn). Hai lý do: (i) §2 tồn tại để Zone Absorption **không thoái hoá thành mean-reversion** — chính ứng viên đã bị loại ở DR-005 của Tool A; bộ lọc trend chậm là thứ duy nhất phân biệt hai chiến lược; (ii) bộ lọc nhanh hơn = nhiễu hơn = mất chính chức năng veto. Quy trình đúng: **đo bằng Z0-T0/Z0-T1 (§10.1b) rồi mới quyết**, không sửa theo cảm giác.

---

---

# PHẦN 3 — KIẾN TRÚC TRANCHE NEO ZONE (tối ưu so với v1)

## 3.1. Khác biệt cốt lõi so với thiết kế v1

Thiết kế v1 đặt tranche theo bội số ATR **tuỳ ý** (0 / 0.5 / 1.0 ATR) quanh giá tín hiệu — không neo vào bất kỳ cấu trúc thị trường nào. Thiết kế v2 đặt tranche **theo chính ranh giới zone đã phát hiện ở Phần 1** — mỗi mức giá có ý nghĩa cụ thể, không phải điểm chia đều tuỳ ý.

```python
# Zone đáy (case LONG), zone = [zone_low, zone_high]
p1 = zone_high        # biên NGOÀI zone — nơi giá vừa chạm vào zone
p2 = (zone_high + zone_low) / 2
p3 = zone_low          # biên TRONG zone — vùng hấp thụ mạnh nhất giả định

sl = zone_low × (1 − buf_sl)     # buf_sl = 0.4 × ATR(14,4H)/price   [CẦN CALIBRATE]
     # SL nằm NGOÀI zone — nếu giá phá qua cả zone, giả thuyết "vùng còn giá trị" SAI,
     # không phải "chưa đủ tiền vào"

w = [1/3, 1/3, 1/3]           # 🔒 v6 — ĐÓNG BĂNG, KHÔNG tune
     # 🔴 LỖI KẾ TOÁN ĐƯỢC SỬA Ở v6: v5 ghi w là "1 bậc tự do" ngay
     # tại đây, nhưng nó CHƯA TỪNG có trong bảng kiểm kê 26 DOF của
     # DR-010 → một tham số tune được, không ai đếm.
     # frozen_rationale: cùng lập luận với w_a/w_b/w_c (§1.2) — prior
     # KHÔNG-THÔNG-TIN. [0.35,0.35,0.30] là con số áp từ ngoài, không
     # có lý thuyết nào nói p1 đáng 35% còn p3 đáng 30%.
     # Câu hỏi "có nên dồn trọng số về tranche 1 không" KHÔNG được trả
     # lời bằng cách tune w — nó đã có arm riêng: Z0 (§10.1) là chính
     # trường hợp cực đoan w = [1, 0, 0].
```

**Vì sao đây là tối ưu, không chỉ khác:**

1. **SL có nghĩa kinh tế**, không phải bội số ATR áp đặt. Nó trùng với điểm mà chính giả thuyết bị bác bỏ (zone bị phá) — nên SL và DG1 (invalidation gate, §4) **là cùng một điều kiện nhìn từ hai góc** (giá đã chạm SL ⟺ zone đã bị phá). Thiết kế v1 có DG1 và SL là hai điều kiện tách rời, có thể lệch nhau.
2. **Zone hẹp → tranche sát nhau, rủi ro/lệnh tự nhiên nhỏ.** Zone rộng → tranche giãn ra, rủi ro/lệnh tự nhiên lớn hơn nhưng đi kèm zone "chất lượng" hơn (thường zone rộng hình thành từ nhiều phiên tích luỹ). Thiết kế v1 có độ rộng cố định bất kể chất lượng tín hiệu.
3. **Không thêm bậc tự do so với v1** — vẫn 3 tranche, vẫn 1 bộ trọng số tune được. Cấu trúc giá tranche giờ **suy ra từ zone**, không phải một tham số ATR-multiplier riêng — thực ra **giảm** một bậc tự do (bỏ tham số "khoảng cách tranche" của v1, vì giờ nó = hàm của zone_width, không tune).

## 3.2. Chứng minh worst-case vẫn bị chặn — tổng quát hoá

Cùng cấu trúc chứng minh ở v1 (đơn điệu theo số tranche khớp), giờ tổng quát cho zone bất kỳ:

```
L(n) = N_full × Σ(i≤n) w[i] × (p[i] − sl) / p[i]      với p[i] ∈ {p1, p2, p3} ⊂ [sl, ∞)
```

Vì `p[i] > sl` với mọi i (do sl đặt ngoài zone, nhỏ hơn zone_low) → mọi số hạng dương → `L(n)` đơn điệu tăng theo n, `max L = L(3) = rho × E` theo cách suy ngược N_full. **Kết luận không đổi so với v1, chỉ khác input là p[i] giờ neo zone thay vì neo ATR-multiplier.**

**Ví dụ minh hoạ bằng số** (zone_high=42300, zone_low=41850, buf_sl=0.4×ATR, ATR%=0.85%, rho=0.375%) — *đây là ví dụ tính công thức, không phải kết quả backtest*:

| Zone width | 1.06% giá |
|---|---|
| p1 / p2 / p3 | 42300 / 42075 / 41850 |
| SL | 41707.7 (1.40% dưới p1) |
| p_avg (khớp đủ) | 42086.2 |
| R_eff | 0.899% |
| N_full/E | **0.417** (so với v1: 0.248 — zone hẹp này cho size lớn hơn vì R_eff nhỏ hơn) |
| Đệm thanh lý | **~12.9 lần** (so với v1: 9.6 lần — cải thiện vì SL không còn cố định 2.2×ATR, mà theo zone) |

| Số tranche khớp | % ngân sách rủi ro |
|---|---|
| 1 | 54.5% |
| 2 | 88.5% |
| 3 | **99.8%** ✅ |

> ⚠️ **Zone hẹp → size lớn hơn, đây là con dao hai lưỡi cần gate riêng.** Zone quá hẹp có thể chỉ là nhiễu ngắn hạn được ZSS chấm điểm nhầm là "mạnh". Xử lý ở §3.3.

## 3.3. Ràng buộc chống zone-quá-hẹp

```
🔴 zone_width_pct ≥ 0.5 × ATR(14,4H)/price
   Zone hẹp hơn ngưỡng này bị coi là nhiễu, không phải vùng hấp thụ thật
   → notional bị suy ra sẽ vô lý lớn, đây là dấu hiệu chỉ báo đang sai,
     không phải cơ hội tốt

🔴 v6 — TRẠNG THÁI: XOÁ CÓ ĐIỀU KIỆN. VERIFY TRƯỚC, CHỐT N SAU.

   Nghi vấn code chết: zone dựng từ swing ± buf với buf = 0.3×ATR
   (§1.1) → bề rộng tối thiểu THEO CẤU TRÚC = 2×buf = 0.6×ATR, đã
   lớn hơn ngưỡng 0.5×ATR. Bộ lọc có thể KHÔNG BAO GIỜ kích hoạt.

   🔴 v6 BỔ SUNG — spec chưa bao giờ nói dùng ATR ở THỜI ĐIỂM NÀO,
      và câu trả lời quyết định bộ lọc sống hay chết:
         (i)  Cả hai đều là ATR HIỆN TẠI  → 0.6 > 0.5 luôn đúng
                                          → CODE CHẾT → XOÁ HẲN (−1 DOF)
         (ii) buf dùng ATR LÚC HÌNH THÀNH, ngưỡng dùng ATR HIỆN TẠI
                                          → khi ATR giãn ra, zone cũ
                                            hẹp SẼ bị lọc → không chết
                                          → NHƯNG lúc đó nó đang đo
                                            "biến động đã đổi bao nhiêu",
                                            KHÔNG phải "zone có hẹp bất
                                            thường không" — sai tên gọi,
                                            và trùng chức năng với thành
                                            phần (c) compression của ZSS
                                            (§1.2). Vẫn nên XOÁ.

   🚪 ĐỀ XUẤT CHỐT: dùng ATR HIỆN TẠI cho cả hai → bộ lọc chết → XOÁ.
      Rủi ro "zone quá hẹp → size vô lý lớn" ĐÃ có hai lớp chặn khác:
      gate đệm thanh lý §6.4 (chặn trực tiếp ca size lớn) và kiểm tra
      kết nạp §6.8f (chặn theo trần margin danh mục).

   🔴 THỨ TỰ BẮT BUỘC ở D0-PRE (v5 để hai việc này SONG SONG — sai):
      1. VERIFY zone_width có phải code chết không
      2. RỒI mới chốt N_ĐĂNG_KÝ và commit
      Vì kết quả bước 1 đổi N: chết → N = 114 · sống → N = 120.
```

## 3.3b. Xác nhận entry tranche 1 — bằng price action tại đúng thời điểm chạm

> **Phản biện đã dẫn tới bổ sung này:** ZSS (§1.2) chỉ đo chất lượng LỊCH SỬ của zone — không có gì xác nhận hấp thụ đang **thực sự diễn ra ngay lúc giá chạm zone**. Đây là lỗ hổng khiến win rate tranche 1 không tối ưu như đáng lẽ phải có.

```python
Khi giá chạm zone lần đầu (sau confirmed_at_bar, Phần 7), CHỜ nến 1H
đóng cửa với MỘT trong hai dấu hiệu:

(a) Nến rejection: bóng dưới (case LONG) ≥ 50% range nến,
    đóng cửa trong nửa trên của range                [CẦN CALIBRATE]
(b) Phân kỳ momentum: RSI(14,1H) tạo đáy CAO HƠN trong khi giá tạo
    đáy THẤP HƠN hoặc bằng, so với lần chạm zone gần nhất trước đó
    (dùng touch_count đã có sẵn ở §1.2, không thêm dữ liệu mới)

KHÔNG có (a) hoặc (b) trong tối đa 3 nến chờ → BỎ LƯỢT chạm này,
KHÔNG quay lại "tìm xác nhận" ở nến xa hơn (tránh overfitting ngược —
nới thời gian chờ tới khi tìm được xác nhận sẽ luôn "thành công"
trên dữ liệu lịch sử nhưng vô nghĩa)
```

## 3.3c. 🔴 v6 — ĐÃ XOÁ: Đường nhanh 15m

```
XOÁ toàn bộ. Không thay bằng cơ chế khác.

BA LÝ DO — theo thứ tự nghiêm trọng:

(1) 🔴 BỀ MẶT LOOKAHEAD THỨ HAI, PHẦN 7 KHÔNG PHỦ
    §3.3c (v5) viết: "EMA cắt trên 15m là chỉ báo nhân quả tự nhiên
    … vẫn cần merge_informative_pair để tránh lỗi lệch nến."
    Đây là chủ quan. `merge_informative_pair` được thiết kế để ghép
    khung LỚN HƠN vào khung nhỏ hơn (4H → 1H) bằng cách dịch một nến
    để chỉ dùng nến đã đóng. Ghép khung NHỎ HƠN (15m) vào dataframe
    1H là chiều NGƯỢC LẠI: tại thời điểm nến 1H thứ t mở, ba nến 15m
    còn lại của giờ đó CHƯA TỒN TẠI. Ghép ngây thơ → backtest thấy
    tín hiệu ở phút 45 nhưng gán cho quyết định ở phút 0.
    → Cùng LOẠI lỗi với B2 (zone lookahead), không phải nhẹ hơn.
      Và H4-D/H4-D-b (§7.2/§7.5) chỉ phủ zone detection.

(2) 🔴 VI PHẠM CHECKLIST CRITICAL CỦA CHÍNH SPEC
    Đường nhanh cho vào tranche 1 khi EMA 15m cắt, KHÔNG cần (a)
    rejection wick, (b) RSI divergence, hay (c) volume hấp thụ.
    Checklist §13 ghi: "❌ Mở tranche 1 khi CHƯA có xác nhận
    price-action (§3.3b) — CRITICAL".
    Nặng hơn: (c) được PHẦN 3b định nghĩa là BỔ NGỮ BẮT BUỘC cho (a).
    Đường nhanh tạo một nhánh entry KHÔNG qua bộ lọc volume — và đó
    lại là nhánh được dùng nhiều nhất trong thị trường biến động.

(3) LỢI ÍCH THẬT QUÁ NHỎ SO VỚI GIÁ
    Rút ngắn tối đa 45 phút trên một hệ thống có độ trễ nền 12h
    (zone confirm) + tối đa 3 nến 1H (xác nhận entry) ≈ cải thiện 6%.
    Đổi lấy: +1 DOF (= 6 trial), một bề mặt lookahead mới, một nhánh
    entry không qua bộ lọc volume.
    §6.7 đã dùng đúng lập luận này cho latency mạng: "Tool D có độ trễ
    cấu trúc lớn hơn network latency rất nhiều". Áp nhất quán.

⚠️ ĐIỂM THAY THẾ, nếu muốn timing mịn hơn về sau: KHÔNG quay lại
   ghép 15m vào dataframe 1H. Đường hợp lệ duy nhất là đổi timeframe
   CHÍNH của strategy thành 15m rồi ghép 1H/4H/1D LÊN bằng
   merge_informative_pair — đúng chiều, an toàn. Đó là thay đổi kiến
   trúc (L2), cần slot NGÂN SÁCH A + lockbox mới, không phải bản vá.
```

## 3.3d. 🔴 SHORT — viết tường minh, không chỉ "đảo dấu"

> **Sửa lỗi tài liệu trước:** Short trước đây chỉ được nhắc bằng "tương tự, đảo hướng" ở vài chỗ — không đủ an toàn. Có ít nhất ba điểm bất đối xứng thật giữa Long và Short cần xử lý riêng, không phải chỉ đảo dấu công thức.

**Zone đỉnh (case SHORT) — công thức đầy đủ, không suy ngược từ Long:**

```python
# Zone đỉnh, zone = [zone_low, zone_high] (đỉnh swing thay vì đáy, §1.1 đảo điều kiện)
p1 = zone_low          # biên NGOÀI zone — nơi giá vừa chạm vào từ dưới lên
p2 = (zone_high + zone_low) / 2
p3 = zone_high          # biên TRONG zone — vùng hấp thụ mạnh nhất giả định

sl = zone_high × (1 + buf_sl)     # SL nằm NGOÀI zone, PHÍA TRÊN
w  = [1/3, 1/3, 1/3]              # 🔒 giữ nguyên, đã đóng băng ở §3.1 (v7 sửa: v6 sót)

# §3.3b đảo hướng: rejection wick là bóng TRÊN (không phải dưới),
# RSI divergence là đỉnh THẤP HƠN trong khi giá đỉnh CAO HƠN/bằng.
# (v6: dòng EMA 15m đã xoá cùng §3.3c)
```

**Ba bất đối xứng cần xử lý riêng, không dùng chung ngưỡng với Long:**

| # | Bất đối xứng | Xử lý |
|---|---|---|
| **1** | **Funding — đã bị rơi mất ở bản v2 trước, phải thêm lại.** Funding không đối xứng theo hướng lệnh, phụ thuộc sentiment thị trường chung, không chỉ hướng bạn đang giữ | 🔴 **v6 — DG7 ĐÃ ĐỔI VAI: từ CHẶN TRANCHE thành ĐÓNG VỊ THẾ.** Xem §4c. Ngưỡng giữ nguyên `funding_paid_cumulative(từ tranche 1) ≥ 0.3 × R_eff`, tính riêng dấu theo Long/Short (Short nhận funding khi rate dương, trả khi rate âm — ngược Long) |
| **2** | **Biến động nền khác nhau** — downtrend thường nhanh/mạnh hơn uptrend tương ứng (đặc điểm quen thuộc của crypto) | DG6 điều kiện A (ATR ratio ngưỡng 1.8) **PHẢI calibrate riêng cho Short**, không dùng chung số với Long — đưa vào Ablation D0.9 như một chiều so sánh riêng (Z3b_long vs Z3b_short) |
| **3** | **Short squeeze** — giá giật ngược nhanh/mạnh khi short bị ép mua lại, không có tương đương chính xác ở chiều Long | 🆕 Thêm điều kiện D trong DG6 riêng cho Short: nếu funding rate 8h gần nhất < −0.05% (nhiều short đang mở, dễ bị squeeze) VÀ giá đã hồi > 50% quãng đường tới p1 → đóng sớm hơn ngưỡng 70% thông thường ở DG6-C [CẦN CALIBRATE] |

> 🚪 **Gate bổ sung bắt buộc trước khi bật Short:** chạy toàn bộ D0.9 (Z0-Z3b) **tách riêng theo hướng** — không giả định kết quả Long tự động áp dụng cho Short. Nếu chỉ có thời gian/dữ liệu chạy một hướng trước, làm Long trước (đối xứng tự nhiên hơn với hầu hết chỉ báo dùng), Short chạy sau khi có DG7 và ngưỡng riêng.

## 3.5. 🆕 v7 — VÒNG ĐỜI LỆNH CHỜ TẠI ZONE (LD-12, LD-13)

> **Lỗ hổng của v6:** spec nói "entry dùng `limit_maker`" ở ba chỗ (§0.3, §1.3b, DR-010) nhưng **chưa bao giờ định nghĩa** lệnh tranche 1 đặt ở giá nào, sống bao lâu, và ánh xạ vào config Freqtrade ra sao. Tool A đã để `unfilledtimeout` lệch với luật "lệnh chờ sống N nến" của spec mà không ai phát hiện, vì backtest vẫn chạy sạch.

```python
════ GIÁ ĐẶT ════
Sau khi §3.3b/(c) xác nhận tại nến 1H đóng cửa C:
   p1_order = min(zone_high, close(C))
      # zone_high nếu giá đã bật lên trên zone → chờ retest, maker
      # close(C) nếu giá vẫn trong zone → đặt ngay tại đó, KHÔNG đặt
      #   trên giá thị trường (lệnh post-only ở giá ≥ ask bị sàn từ
      #   chối, không phải khớp taker — LD-13)
   p2, p3 = giữ nguyên theo §3.1 (giữa zone, zone_low)
   🔴 Kế hoạch D0.3/D0.5 tính trên p1_order THẬT, không phải zone_high
      danh nghĩa. Decision Log ghi cả hai.

════ TUỔI THỌ ════
   Tranche 1:  lệnh chờ sống ≤ 3 nến 1H kể từ khi đặt.
               🔒 0 hằng số mới — dùng lại "tối đa 3 nến chờ" của §3.3b.
               Hết hạn chưa khớp → HUỶ, ghi entry_outcome = NO_FILL,
               KHÔNG đặt lại (đặt lại = nới thời gian chờ, đúng lỗi
               §3.3b cảnh báo).
   Tranche 2/3: lệnh chờ sống trong cửa sổ DG4 (≤ 8 nến 1H kể từ
               tranche 1 khớp), bị huỷ sớm hơn nếu DG1–DG5 fail.
               Đã có ở §4, ghi lại để một chỗ đủ.

════ ÁNH XẠ CONFIG FREQTRADE (LD-13 — đã kiểm bằng mã nguồn ở Tool A) ════
   order_types.entry            = "limit"
   order_time_in_force.entry    = "PO"        # post-only THẬT trên
                                              # Binance Futures.
                                              # "limit_maker" KHÔNG
                                              # phải giá trị hợp lệ
                                              # của order_types
   entry_pricing.price_side     = "same"      # "other" là cho taker
   unfilledtimeout.entry        = 180         # phút = 3 nến 1H, KHỚP
                                              # luật trên
   unfilledtimeout.unit         = "minutes"
   custom_entry_price()         → trả p1_order / p2 / p3 theo tranche
   → L-Z42: test đối chiếu config.json với hằng số spec — hai nơi
     không được tự do lệch nhau.

════ ĐIỀU BACKTEST KHÔNG ĐO ĐƯỢC (LD-12) — ghi để không ai lập luận sai ════
   • Backtest Freqtrade KHÔNG có sổ lệnh lịch sử. custom_entry_price
     trong backtest trả giá ĐÓNG NẾN TRƯỚC; trường trượt giá LUÔN =
     0.0; tỷ lệ khớp maker/post-only CHƯA TỪNG được đo.
   • 🔴 Tỷ lệ khớp và trượt giá của lệnh chờ trong vùng là GIẢ ĐỊNH
     chưa đo, chỉ kiểm chứng được ở D10/D11. KHÔNG dùng số backtest
     để lập luận về chất lượng khớp lệnh. Chỉ số "tỉ lệ khớp tranche
     1/2/3" trong periodic_report (§12d.2) là nơi đo THẬT.
```

> ⚠️ **Hệ quả lên Ablation D0.9:** vì backtest giả định tranche khớp tại giá mở nến (§9b D6) với trượt giá 0, **mọi arm DCA (Z1–Z3b) có nguy cơ được ưu ái một chiều so với Z0** — Z0 chỉ có một lần khớp, các arm DCA có ba (chiều thật của lệch phải ĐO, không giả định — DR-015 §1). 🔴 **v8 sửa thứ tự:** v7 để "đọc lại Nhánh 2 sau D10" — tức kết luận hình thành trước, thước kiểm sau. Giờ độ lệch được đo TRƯỚC ablation tại cổng **D3.5 (DR-015)** và nhúng thẳng vào cách đọc Nhánh 2 (§10.2); D10 chỉ còn là XÁC NHẬN quy mô đầy đủ.

## 3.4. D0 — năm nguyên lý bất biến (kế thừa nguyên tắc, không kế thừa công thức)

Giữ nguyên **5 nguyên lý** từ v1 vì chúng là nguyên lý quản trị rủi ro tổng quát, không phải nội dung chiến lược:

```
D0.1  Ngân sách rủi ro cố định TRƯỚC tranche 1 (giờ = rho × E, suy từ zone)
D0.2  SL tính MỘT LẦN tại zone_low, không bao giờ di chuyển
D0.3  Margin đặt trước cho TOÀN BỘ kế hoạch (notional suy từ zone)
D0.4  Không có tranche thứ 4
D0.5  L_total tính trên notional KẾ HOẠCH, không phải đã triển khai
```

### 3.4b. 🆕 v4 — Vì sao D0.4 không thể nới: DCA không giới hạn là BẤT KHẢ THI VỀ HÌNH HỌC

> Ghi lại để không phải lập luận lại. Phản biện đã nêu: *"tại sao không cố định vốn lệnh 1, còn các lần DCA sau thì không giới hạn?"*

**Hiểu nhầm cần sửa trước:** ba tranche KHÔNG phải ba vị thế.

```
Số vị thế đồng thời  =  kết quả kiểm tra kết nạp (§6.8f), 6–20 coin
Số tranche/vị thế    =  3           (D0.4)
→ ~21 lệnh song song, mỗi lệnh chia tối đa 3 lần khớp.
   Ba mức p1/p2/p3 cách nhau 1.06% GIÁ — đó là cách rải lệnh limit
   trong một dải hẹp, KHÔNG phải phân bổ danh mục.
```

**Tranche thứ 4 phải đặt ở đâu?**

```
        ┌──────────────────┐  ← zone_high = p1
        │   VÙNG HỢP LỆ    │  ← p2
        └──────────────────┘  ← zone_low  = p3
              ↕ buf_sl
        ═══════════════════   ← SL
              Dưới đây: GIẢ THUYẾT ĐÃ SAI

Chỉ còn khoảng giữa zone_low và SL — tức ĐỆM VÔ HIỆU HOÁ.
Mua ở đó = mua khi luận điểm của chính mình đang hỏng.
Dưới SL nữa thì SL đã kích hoạt, vị thế đã đóng.

🔴 "DCA không giới hạn" KHÔNG TƯƠNG THÍCH với SL neo zone. Muốn DCA
   vô hạn phải bỏ SL neo zone — mà đó chính là thứ phân biệt Zone
   Absorption với mean-reversion đã bị loại ở DR-005. Bỏ nó là bỏ
   chiến lược, không phải nới một tham số.
```

**Bốn nguyên lý sụp cùng lúc nếu bỏ D0.4:**

| Nguyên lý | Hỏng thế nào |
|---|---|
| **D0.1** | Không biết sẽ khớp bao nhiêu tranche → không tính được lỗ tối đa → không suy ngược ra size |
| **D0.3** | Đặt trước margin cho **bao nhiêu**? Không có số → không reserve được → tranche sau bị từ chối đúng lúc cần nhất |
| **D0.5** | "Kế hoạch" không còn con số → không tính được `L_total_D` → kiểm tra kết nạp §6.8f vô nghĩa |
| **§3.2** | Chứng minh worst-case dựa vào `n ≤ 3`. Bỏ trần → `L(n)` tăng đơn điệu **không có chặn trên** |

**Cơ chế tâm lý mà D0.4 chặn:** DCA không giới hạn **luôn** trông hợp lý ở từng bước (giá thấp hơn → giá vào trung bình tốt hơn → "chỉ cần hồi một chút là hoà"). Mỗi bước hợp lý, chuỗi bước thì không. Đây là martingale, và martingale luôn thắng cho tới lần thua cuối cùng.

**Điều người phản biện thực sự muốn, và đòn bẩy ĐÚNG để lấy nó:**

| Mong muốn | Chỉnh ở đâu |
|---|---|
| Nhiều mã hơn | Pool ~100 mã (§0.3c) |
| Nhiều lệnh song song hơn | `daily_loss_budget_pct` + `L_exchange` (§6.8d/§6.8f) |
| Mỗi lệnh nhỏ hơn, phân tán hơn | `rho` — hạ rho thì số lệnh vừa ngân sách tăng lên (§6.8f) |
| Không muốn DCA chút nào | **Z0** trong ablation (§10.1) — nếu Z0 ≥ Z3 thì bỏ DCA, đó là kết quả TỐT |

Số tranche KHÔNG phải chỗ điều chỉnh mức phân tán — nó là cấu trúc **bên trong** một vị thế.

**Về "vốn cố định vs rủi ro cố định":** đây là phần HỢP LỆ của phản biện và đã thành arm `Z0-S1` (§10.1b). Lập luận phản đối vốn-cố-định: với `R_eff` biến thiên 0.9%–3.0%, notional cố định 300 USDT cho lỗ 2.7–9.0 USDT khi chạm SL — **chênh 3,3 lần, và khoản lỗ nặng nhất tự động dồn vào zone rộng**, tức cược lớn nhất vào nơi ít thông tin nhất về điểm dừng. Phép tính "thắng 4/10 là lời" chỉ đúng khi lỗ đồng đều — tức chính cơ chế rủi ro-cố-định.

---

# PHẦN 3b — 🆕 v3.3: VOLUME TẠI LÚC CHẠM ZONE

## 3.3b — bổ sung điều kiện (c)

```
🔴 LỖ HỔNG: volume hiện chỉ được đo MỘT NỬA chỗ cần thiết.

   CÓ:    volume_ratio = volume(nến swing) / volume_MA(20,4H)   §1.2(b)
          → đo volume LÚC ZONE HÌNH THÀNH (quá khứ)
   THIẾU: volume TẠI THỜI ĐIỂM GIÁ QUAY LẠI CHẠM ZONE (hiện tại)

   Hai ca hệ thống hiện KHÔNG phân biệt được — cả hai đều có thể tạo
   ra rejection wick giống hệt nhau:
      Chạm + volume CAO + giá không xuyên  → có người THẬT đang hấp thụ
                                             (đúng điều §0.1 tuyên bố)
      Chạm + volume THẤP + giá dừng lại    → không ai bảo vệ, chỉ tạm
                                             nghỉ; lần chạm sau nhiều
                                             khả năng xuyên thủng
```

```python
(c) 🆕 Hấp thụ có volume:
    volume(nến 1H xác nhận) / volume_MA(20, 1H) ≥ v_min   [CẦN CALIBRATE]
    VÀ nến đó thoả điều kiện (a) rejection wick

   Kết hợp: (a AND c) HOẶC (b)  — không phải (a OR b OR c)
   Lý do: (c) là BỔ NGỮ cho (a), không phải tín hiệu độc lập.
          Volume cao mà không có rejection = có thể đang bị xuyên qua.
```

> **Vì sao vào §3.3b chứ KHÔNG vào ZSS:** ZSS đo **chất lượng lịch sử** của zone và được tính lại ở DG5. Volume lúc chạm là **sự kiện tại thời điểm vào lệnh**, không phải thuộc tính của zone. Trộn hai loại thông tin vào một điểm số làm DG5 mất khả năng diễn giải (ZSS giảm — vì zone xấu đi, hay vì lần chạm này volume thấp?).

```
🚪 Đăng ký qua Idea Queue (§9c.7) như một giả thuyết Loại A hợp lệ:
   mechanism:   dòng lệnh hấp thụ để lại dấu vết trên volume tại đúng
                thời điểm nó hoạt động
   who_pays:    người bán vào vùng hỗ trợ tin rằng nó sẽ thủng, bị hấp
                thụ bởi lệnh mua chờ sẵn và phải mua lại cao hơn
   durability:  cần dữ liệu tick-level để arbitrage chính xác; ở khung
                1H đây là proxy thô, ít bị cạnh tranh trực tiếp

   Chi phí: +1 tham số (v_min) = +6 trial
            +1 arm ablation × 2 hướng = +2 trial
            → ĐÂY LÀ THAM SỐ MỚI DUY NHẤT CỦA v3.3
```

---

---

# PHẦN 4 — GATE KÍCH HOẠT TRANCHE (thiết kế lại theo zone)

| Gate | Điều kiện | Khác gì v1 |
|---|---|---|
| **DG1 — Zone còn nguyên** | Chưa có nến 4H đóng cửa dưới `sl` (case LONG) | v1: điều kiện mơ hồ "tín hiệu còn hiệu lực". v2: **trùng chính xác với điều kiện SL** — không còn khoảng xám giữa hai khái niệm |
| **DG2 — Trend context còn đúng** | `trend_dir` không đổi hướng kể từ tranche 1 (Phần 2) | Cùng vai trò v1, chỉ báo khác |
| **DG3 — Margin còn nguyên** | Reserve chưa bị hệ thống khác ăn | Kế thừa nguyên |
| **DG4 — Trần thời gian chờ** | ≤ 8 nến 1H kể từ tranche 1 *(giảm từ 12 → 8: zone hẹp hơn breakout-pullback nên kỳ vọng hấp thụ diễn ra nhanh hơn — [CẦN CALIBRATE])* | Số khác, lý do khác |
| **DG5 — ZSS không suy yếu** | ZSS tính lại tại thời điểm xét tranche 2/3 không giảm > 30% so với lúc tranche 1 | 🆕 **Mới, không có ở v1.** Nếu volume/compression đổi chiều giữa lúc tranche 1 và tranche 2, zone đang "yếu đi" dù giá chưa chạm SL — tín hiệu sớm hơn giá |
| ~~**DG7**~~ | 🔴 **v6 — ĐÃ CHUYỂN sang nhóm ĐÓNG VỊ THẾ, xem §4c.** Không còn là gate kích hoạt tranche | Lý do chuyển ở §4c |

> **DG5 là điểm "smart" thật sự của tên gọi Smart DCA.** DCA ngây thơ chỉ nhìn giá. DG5 nhìn lại chất lượng zone mỗi lần trước khi bơm thêm tiền — nếu zone đang mất tính hợp lệ (volume giảm dần, ATR giãn ra bất thường) thì dừng bơm **trước khi** giá xác nhận điều đó bằng cách chạm SL.

## 4.1. 🔴 DG6 — Early Invalidation: ĐÓNG vị thế đã có, không chỉ chặn tranche mới

> **Phản biện đã dẫn tới bổ sung này:** DG1-DG5 ở trên đều chỉ trả lời "có nên thêm tranche không" — không có gate nào chủ động **đóng vị thế đã triển khai** trước khi giá chạm SL cứng. Đây là khoảng trống quan trọng nhất: hệ thống có thể đã "biết mình sai" (momentum đảo ngược, trend đổi hướng, không có phản ứng nào sau nhiều giờ) nhưng vẫn ôm nguyên vị thế chờ đúng giá SL.

```python
DG6 kiểm tra LIÊN TỤC sau khi tranche 1 đã khớp (không chỉ trước khi
thêm tranche như DG1-DG5):

   Điều kiện A — momentum đảo ngược đúng ngược giả thuyết ban đầu:
      ATR(14,1H)_hiện_tại / ATR(14,1H)_lúc_tranche_1_khớp ≥ 1.8  [CẦN CALIBRATE]
      VÀ giá đang ở phía bất lợi so với p_avg hiện tại
      (compression — lý do vào lệnh ở §1.2(c) — đã đảo thành giãn nở
       mạnh, đúng dấu hiệu KHÔNG phải hấp thụ)

   Điều kiện B — hết thời gian hợp lý mà chưa có phản ứng nào:
      ≥ 8 nến 1H kể từ tranche 1 khớp   🔒 v6 — ĐÓNG BĂNG, = DG4
      VÀ giá CHƯA từng đóng cửa vượt lại p1 (case LONG)
      (khác DG4 — DG4 chỉ ngừng THÊM tranche, đây ĐÓNG vị thế đã có)

      🔴 v6 SỬA MÂU THUẪN: v5 ghi "6 nến" ở đây nhưng DR-010 đóng
         băng ở "8 nến (KHÔNG phải 6)". Code sẽ không biết lấy số nào.
         Chốt 8. frozen_rationale: = DG4, tức "hết cửa sổ được phép
         rải tranche mà giá chưa phục hồi qua p1 → hấp thụ hỏng".
         ⚠️ Lý do CŨ "2×k" là SAI và đã bị v5 bác: k đếm bằng nến 4H,
            DG6-B đếm bằng nến 1H — trùng số giữa hai đơn vị khác nhau.

   Điều kiện C — đã đi 70% quãng đường tới SL, VÀ bối cảnh xu hướng đổi:
      price_decay_ratio = (p_avg − giá_hiện_tại)/(p_avg − sl) ≥ 0.7
      VÀ trend_dir (Phần 2, §2.2) đã đảo chiều hoặc mất xác nhận đa khung
      (khác DG2 — DG2 chỉ chặn tranche mới, đây đóng vị thế đã có)

   🆕 Điều kiện D — CHỈ áp dụng cho SHORT (§3.3d), rủi ro short squeeze:
      funding rate 8h gần nhất < −0.05%   [CẦN CALIBRATE]
      (nhiều short đang mở trên thị trường, dễ bị ép mua lại đồng loạt)
      VÀ giá đã hồi > 50% quãng đường tới p1 (ngưỡng THẤP HƠN 70% của
      điều kiện C — vì short squeeze có thể diễn ra rất nhanh, chờ tới
      70% có thể đã muộn)

(A) HOẶC (B) HOẶC (C) HOẶC (D nếu SHORT) đúng → ĐÓNG TOÀN BỘ vị thế
bằng MARKET, tag EARLY_EXIT_A / B / C / D, TRƯỚC khi chạm SL.
```

> **Vì sao (D) không có tương đương ở Long:** đây chính là bất đối xứng thật đã nêu ở §3.3d — không phải thiếu sót khi quên viết bản Long của (D), mà short squeeze là rủi ro đặc thù của việc bán khống, không có hiện tượng đối xứng chính xác ở chiều Long (long liquidation cascade có tồn tại nhưng cơ chế và tốc độ khác).

**Tương thích với D0.2 (SL tính một lần, không di chuyển):** DG6 **không đụng vào lệnh `STOP_MARKET` đã đặt trên sàn** — đây là quyết định đóng lệnh chủ động của bot, độc lập với SL. SL vẫn nằm nguyên làm lưới bảo hiểm cuối cùng nếu DG6 không kịp phản ứng (VD: gap giá bỏ qua cả điều kiện A/B/C).

**Đây là cơ chế MỚI, phải tự chứng minh giá trị, không mặc định tốt:**
```
🚪 Thêm vào Ablation D0.9: so sánh Z3 (không DG6) với Z3b (có DG6)
   Khả năng thật: DG6 giảm max_single_trade_loss và CVaR (đúng mục
   tiêu) NHƯNG có thể giảm cả expectancy trung bình — một số lệnh
   "tưởng sai" vẫn hồi trước khi chạm SL sẽ bị cắt sớm, mất phần hồi
   đó. Đây là đánh đổi thật, đo bằng D0.9, không giả định trước.
```

---

# PHẦN 4b — 🔴 v3.2: DG8 — TIME STOP

> Chèn ngay sau §4.1 (DG6). Gỡ blocker **B7**, LỖI 7 và LỖI 8.

## 4b.1. Vì sao đây là lỗ hổng, không phải thủ tục thừa

Xem LỖI 7 và LỖI 8 ở phần CĂN CỨ. Tóm tắt ba hệ quả:

```
(a) KHÔNG ĐO ĐƯỢC SỰ KHỚP KHUNG THỜI GIAN
    Không có max_hold thì không thể nói bộ chỉ báo (§2b.1) khớp hay
    lệch — vì không có "hold" để so. Toàn bộ PHẦN 2b treo vào DG8.

(b) FUNDING KHÔNG BỊ CHẶN
    DG7 (v5) chỉ chặn tranche mới, KHÔNG đóng vị thế. Với perp đòn bẩy
    5x, chi phí funding tích luỹ TUYẾN TÍNH theo thời gian, còn kỳ vọng
    lợi nhuận thì KHÔNG. Hold vô hạn = expectancy âm dần một cách
    chắc chắn, không phụ thuộc chiến lược đúng hay sai.

    🔴 v6 — CHẨN ĐOÁN NÀY ĐÚNG NHƯNG LỜI GIẢI CỦA v5 KHÔNG ĐỦ.
    v5 giao việc cho DG8, nhưng DG8 neo vào TUỔI ZONE (24 nến 4H),
    không neo vào CHI PHÍ. Trong 4 ngày có 12 lần thanh toán funding;
    nếu funding xấu kéo dài, chi phí vượt 0.3 × R_eff từ ngày thứ 2
    mà KHÔNG gate nào đóng vị thế cho tới hết ngày thứ 4.
    → Đây là CÙNG CẤU TRÚC với LỖI 7, khác trục: LỖI 7 = không có
      trần THỜI GIAN; đây = không có trần CHI PHÍ.
    → Gỡ ở §4c (DG7 chuyển nhóm), KHÔNG phải bằng cách hạ
      max_hold_bars — đó là dùng tham số ở trục sai để chữa vấn đề
      ở trục khác.

(c) PHÂN BỐ HOLD KHÔNG ĐO ĐƯỢC
    Không có trần thì D0.9 không báo cáo được `hold_duration`, và bạn
    sẽ phát hiện ở LIVE rằng có lệnh nằm 3 tuần — giai đoạn tốn tiền
    thật, đúng chế độ hỏng mà toàn bộ spec này được viết để tránh.
```

## 4b.2. Định nghĩa DG8

```python
DG8 — Time Stop. Thuộc nhóm ĐÓNG VỊ THẾ (cùng nhóm DG6),
      KHÔNG thuộc bảng gate kích hoạt tranche.

   Kiểm tra LIÊN TỤC sau khi tranche 1 khớp:

      bars_since_tranche1 (đếm bằng nến 4H) ≥ max_hold_bars
      → ĐÓNG TOÀN BỘ vị thế bằng MARKET, tag TIME_STOP

   🔴 ÁP DỤNG KHÔNG ĐIỀU KIỆN:
      • kể cả đang LÃI
      • kể cả TP1 ĐÃ CHẠM và TP2 đang trail
      • kể cả trend_dir vẫn còn đúng
      • kể cả ZSS vẫn cao

   Lý do không có ngoại lệ: mọi ngoại lệ đều là một bậc tự do mới,
   và ngoại lệ "đang lãi thì cho ở lại" chính là cách một time stop
   bị vô hiệu hoá trong thực tế (lệnh lãi mỏng luôn "sắp thành lãi to").
```

## 4b.3. Neo `max_hold_bars` vào §1.3, không chọn tuỳ ý

```
Suy từ thứ ĐÃ CÓ trong spec, không thêm giả định mới:

   §1.3 — zone hết hạn sau 40 nến 4H (~6,7 ngày)
   → Giả thuyết "zone này còn hấp thụ" có HẠN DÙNG 6,7 ngày
   → Vị thế cược vào giả thuyết đó KHÔNG THỂ sống lâu hơn giả thuyết

   ỨNG VIÊN CHỐT:  max_hold_bars = 24 nến 4H (= 4 ngày)   [CẦN CALIBRATE]

   Hai ràng buộc chặn trên/dưới:
      TRẦN:  < 40 nến 4H (6,7 ngày) — không được vượt tuổi zone tối đa
      SÀN:   ≥ 3× chân trời EMA20(4H) ≈ 3,3 ngày — đủ để tầng 4H
             (§2.2, chỉ báo hướng chính) "nói" hết một chu kỳ

   24 nến (4 ngày) nằm giữa hai ràng buộc này. Đây là ỨNG VIÊN, không
   phải kết luận — calibrate ở D0.9.

🔴 NẾU muốn hold tới 1 TUẦN (42 nến 4H): PHẢI nới §1.3 tương ứng
   TRƯỚC, kèm lý do định lượng. KHÔNG được để vị thế sống lâu hơn
   giả thuyết sinh ra nó — đó là mâu thuẫn logic, không phải đánh đổi.
```

## 4b.4. Vì sao DG8 phải có MẶT trong D0.9, không đợi D7

```
Cám dỗ: "để D0.9 chạy không DG8 cho sạch, thêm sau ở D7."
→ SAI. Nếu D0.9 chạy không time stop, phân bố hold trong ablation
  KHÔNG phản ánh hệ thống cuối cùng, và mọi metric (expectancy,
  CVaR, funding, số lệnh/năm) đều thuộc về một hệ thống KHÁC với
  hệ thống sẽ chạy live.

🚪 DG8 BẬT trong TẤT CẢ arm Z0-Z3b và Z0-T0/T1, cùng một giá trị
   max_hold_bars. Nó là thuộc tính của KHUNG THỬ NGHIỆM, không phải
   biến được so sánh.

   Muốn biết DG8 đáng giá bao nhiêu → đó là một ablation RIÊNG, phải
   đăng ký trial riêng, KHÔNG gộp vào D0.9 lần này. Chi phí: +2 trial
   (1 arm × 2 hướng). Đề xuất HOÃN — B7 là lỗ hổng an toàn, không phải
   ứng viên tối ưu hoá; ta thêm nó vì thiếu nó là sai, không vì kỳ
   vọng nó tăng lợi nhuận.
```

## 4b.5. Tương thích với D0.2 và DG6

```
Với D0.2 (SL tính một lần, không di chuyển):
   DG8 KHÔNG đụng vào lệnh STOP_MARKET trên sàn — giống hệt cơ chế
   DG6 (§4.1). Đây là quyết định đóng chủ động của bot; SL vẫn nằm
   nguyên làm lưới cuối.

Thứ tự ưu tiên khi nhiều điều kiện cùng đúng — 🔴 v6, BA mức:
   DG6 (A/B/C/D)  →  DG7 (§4c)  →  DG8

   DG6  giả thuyết ĐÃ SAI          (thông tin về thị trường)
   DG7  giả thuyết CÒN ĐÚNG nhưng KHÔNG CÒN ĐÁNG GIỮ  (chi phí)
   DG8  giả thuyết HẾT HẠN          (thời gian)

   Ghi đúng exit_tag để tách BA loại khi phân tích, không gộp thành
   một nhóm "early exit" — ba loại này trỏ tới ba nguyên nhân khác
   nhau và ba hành động khắc phục khác nhau.
```

## 4b.6. Test bắt buộc

```
L-Z18 🆕 KHÔNG có bản ghi lệnh nào với hold_duration_bars >
      max_hold_bars                                          🔴 CRITICAL
L-Z19 🆕 hold_duration_bars ghi ở MỌI lệnh đã đóng, mọi arm — kể cả
      lệnh đóng bằng TP/SL (để dựng phân bố hold, §10.2)
```

---

---

# PHẦN 4c — 🆕 v6: DG7 CHUYỂN NHÓM — FUNDING STOP

> Gỡ lỗ hổng đã được §4b.1(b) chẩn đúng nhưng chưa được chữa: **funding drain có cơ chế CHẶN, không có cơ chế ĐÓNG.**

## 4c.1. Vì sao chuyển nhóm chứ không thêm gate mới

```
🔴 PHƯƠNG ÁN ĐÃ BỊ BÁC BỎ — ghi lại để không ai đề xuất lại:
   "Giữ DG7 chặn tranche tại 0.3 × R_eff, THÊM DG9 đóng vị thế tại
    0.3 × R_eff."

   Vì sao sai: cùng MỘT ngưỡng. Thời điểm DG7 chặn tranche cũng chính
   là thời điểm DG9 đóng lệnh → DG7 không bao giờ có tác dụng quan
   sát được. ĐÓNG VỊ THẾ THỐNG TRỊ CHẶN TRANCHE tại cùng ngưỡng:
   nếu ta sắp đóng, việc từ chối thêm tranche không thay đổi gì.
   → Đó là dead code, đúng loại mà DR-010 nói "gây hiểu nhầm về sau".

   Hai ngưỡng khác nhau (chặn ở 0.15, đóng ở 0.30) thì hết dead code
   nhưng +1 DOF = +6 trial cho một cơ chế hai tầng chưa có bằng chứng
   nào cho thấy hai tầng tốt hơn một.

✅ PHƯƠNG ÁN CHỐT: MỘT gate, MỘT ngưỡng, đổi HÀNH ĐỘNG.
   DG7 rời bảng "gate kích hoạt tranche" (§4), vào nhóm đóng vị thế
   (cùng DG6, DG8). Số DOF không đổi. Số gate không đổi. Không dead code.
```

## 4c.2. Định nghĩa DG7 (v6)

```python
DG7 — Funding Stop. Thuộc nhóm ĐÓNG VỊ THẾ.
      KHÔNG thuộc bảng gate kích hoạt tranche (§4).

   Kiểm tra LIÊN TỤC sau khi tranche 1 khớp, tại mỗi mốc funding 8h:

      funding_paid_cumulative(từ tranche 1) ≥ 0.3 × R_eff
      → ĐÓNG TOÀN BỘ vị thế bằng MARKET, tag FUNDING_STOP

   DẤU: tính riêng theo hướng (§3.3d).
      LONG  trả funding khi rate > 0, nhận khi rate < 0
      SHORT ngược lại
      → `funding_paid_cumulative` chỉ cộng phần THỰC TRẢ; funding
        NHẬN được trừ đi (có thể âm → không bao giờ trigger, đúng).

   🔴 v7 — NGUỒN DỮ LIỆU (LD-14, kiểm bằng mã nguồn ở Tool A):
      • Freqtrade TỰ tích luỹ `trade.funding_fees` native ở CẢ
        backtest lẫn live. KHÔNG tự xây pipeline tích luỹ (LD-09:
        không tạo nguồn sự thật thứ hai).
      • Quy ước dấu Freqtrade: ÂM = đã trả.
        → funding_paid_cumulative = −trade.funding_fees
      • Dữ liệu funding lịch sử: giá trị nằm ở cột `open`, KHÔNG
        phải `close` (close luôn = 0.0).
      • Sai dấu hoặc sai cột → DG7 và DG6-D IM LẶNG không bao giờ
        kích hoạt, backtest vẫn sạch. → L-Z43 test khoá cứng chiều
        dấu: một lệnh LONG giả lập qua 3 mốc funding dương phải cho
        funding_paid_cumulative > 0.

   MẪU SỐ: R_eff là R_eff của KẾ HOẠCH đầy đủ 3 tranche (D0.5),
      cố định tại thời điểm lập plan. KHÔNG tính lại theo p_avg
      hiện tại — nếu tính lại, mẫu số đổi mỗi lần tranche khớp và
      ngưỡng trở thành mục tiêu di động.

   🔴 ÁP DỤNG KHÔNG ĐIỀU KIỆN, cùng lý do với DG8 (§4b.2):
      • kể cả đang LÃI
      • kể cả TP1 đã chạm
      • kể cả trend_dir vẫn đúng
```

## 4c.3. Vì sao 0.3 là ngưỡng hợp lý — và vì sao nó là 1 BẬC TỰ DO

```
Ý nghĩa: 30% ngân sách rủi ro của lệnh đã bị chi phí ăn mất TRƯỚC
KHI giá làm bất cứ điều gì. Còn lại 70% để giả thuyết chứng minh
mình đúng — và TP1 (§5.1) thường nằm ở khoảng 1–1,5 R_eff, nên
sau 0.3 R_eff chi phí, tỷ lệ lời/lỗ đã xấu đi ~40%.

🔴 v6 SỬA LỖI KẾ TOÁN: con số 0.3 này CHƯA TỪNG có trong bảng kiểm
   kê 26 DOF của DR-010. Nó là một ngưỡng tự do thật, không có lý
   thuyết chỉ đường. → v6 ĐẾM NÓ: +1 bậc tự do (mục #12, DR-010).

⚠️ KHÔNG được gộp nó với ngưỡng funding RATE (−0.05%, §3.3d/DG6-D).
   v5 khai "gộp ba ngưỡng funding thành một" — sai đơn vị:
      −0.05%      là funding RATE 8h            (%/8h)
      0.3 × R_eff là CHI PHÍ TÍCH LUỸ / rủi ro  (không đơn vị)
   Gộp được đúng HAI ngưỡng rate, không phải ba. Đó là lý do việc
   đóng băng ở v5 chỉ giảm được 1 DOF, không phải 2.
```

## 4c.4. Test bắt buộc

```
L-Z30 🆕 v6 — KHÔNG có lệnh đã đóng nào với
      funding_paid_cumulative > 0.35 × R_eff_plan
      (biên 0.05 cho độ trễ giữa hai mốc funding 8h)     🔴 CRITICAL
L-Z31 🆕 v6 — funding_paid_cumulative ghi ở MỌI lệnh đã đóng, mọi
      arm — kể cả lệnh đóng bằng TP/SL/DG6/DG8. Không có phân bố
      đầy đủ thì không biết ngưỡng 0.3 có bao giờ ràng buộc không
      (cùng lý do với L-Z19 cho hold_duration_bars)
```

> ⚠️ **Điều cần theo dõi ở D0.9, không giả định trước:** có khả năng DG7 gần như không bao giờ trigger vì DG8 (4 ngày) cắt trước. Nếu phân bố `funding_paid_cumulative` ở D0.9 cho thấy tỉ lệ trigger < 2%, DG7 là lưới an toàn cho ca funding cực đoan chứ không phải cơ chế hoạt động thường xuyên — **ghi nhận điều đó, đừng hạ ngưỡng để nó "có việc làm"**. Đó chính xác là hành vi mà §9c.5 cảnh báo.

---

---

# PHẦN 5 — TAKE-PROFIT (thiết kế riêng, không dùng R-multiple cố định)

## 5.1. Vì sao không dùng TP theo R-multiple

R-multiple cố định (VD "+1.0R") giả định biên độ kỳ vọng như nhau ở mọi lệnh. Với Zone Absorption, biên độ có sẵn trong dữ liệu: **khoảng cách tới zone đối diện gần nhất** (đỉnh/đáy swing gần nhất theo hướng ngược lại, cùng thuật toán Phần 1).

```python
TP1 = zone đối diện gần nhất theo hướng lệnh, trừ hao 20%   [CẦN CALIBRATE]
      # chốt 50% vị thế tại đây
      # 🟡 TUNABLE — mục #9 trong 12 DOF (DR-010)
TP2 = trail bằng ATR(14,1H) × 1.5 sau khi TP1 chạm
      # 🔒 ĐÓNG BĂNG. frozen_rationale: bội số ATR quy ước. Đây là
      #    tham số YẾU NHẤT trong danh sách đóng băng (ít lý thuyết
      #    dẫn đường nhất, nằm ở nhánh lợi nhuận) — nếu về sau chỉ
      #    được mở khoá MỘT tham số, đây là ứng viên đầu tiên (§12c.3)
```

**Vì sao trừ hao 20%:** zone đối diện thường có phản ứng giá (chính là lý do nó được nhận diện là zone) — kỳ vọng đóng một phần trước khi chạm để tránh bị đảo ngược ngay tại đó.

> ⚠️ Nếu không tìm thấy zone đối diện hợp lệ trong khoảng cách hợp lý (**> 4 × R_eff**), dùng TP theo bội số làm phương án dự phòng: `TP_fallback = p_avg + **1.5 × R_eff**` — ghi rõ tag `tp_source: "fallback_r_multiple"` trong Decision Log để sau này tách riêng đo hiệu quả hai loại TP.
>
> 🔴 **v8 — gọi tên cho đúng (DR-013 (2d)):** hai bội số 4.0/1.5 ở đây nhân với **R_eff — một KHOẢNG GIÁ**, không phải với R tiền tệ (`planned_risk_usdt`). Vì khoảng giá ứng với +1R tiền tệ **co lại mỗi khi thang khớp thêm tranche**, một mốc thoát dẫn xuất từ R tiền tệ sẽ trôi theo diễn biến khớp — đúng thứ mục tiêu thoát không được phép làm. Neo theo R_eff (đóng băng lúc entry) thì không trôi. Mọi chỗ trong code/tài liệu phải viết `4.0 × R_eff`, không bao giờ "4R".

```
🔒 v6 — ĐÓNG BĂNG CẢ HAI SỐ (4.0 và 1.5), 0 trial.

🔴 LỖI KẾ TOÁN ĐƯỢC SỬA: cả hai con số này CHƯA TỪNG có trong kiểm kê
   26 DOF của v5, dù chúng là ngưỡng tự do thật.

frozen_rationale: TP_fallback là NẠNG DỰ PHÒNG, không phải nguồn edge.
   Nếu phải tune nó để hệ thống có lãi, nghĩa là TP CHÍNH (zone đối
   diện) đang hỏng — đó là L2 (sai cấu trúc, §11b.1), xử bằng ablation
   arm mới + lockbox mới, KHÔNG bằng cách tune ngưỡng của nạng.

🚪 CƠ CHẾ PHÁT HIỆN: chỉ số H-4 (§11b.2) theo dõi tỉ lệ lệnh dùng
   TP_fallback. Vượt 40% → tiền đề "luôn tìm được zone đối diện trong
   khoảng cách hợp lý" SAI → phân loại L2.
   → Ba mảnh khớp thành vòng khép kín: đóng băng nạng → đo tần suất
     dùng nạng → vượt ngưỡng thì xét lại CẤU TRÚC, không xét lại nạng.
```

---

# PHẦN 6 — RISK ENGINE ĐỘC LẬP

## 6.1. Vì sao không tái dùng công thức `L_total` của Tool A

Bộ hệ số của Tool A (`mult_corr`, `mult_vol`, `mult_dd`...) được hiệu chỉnh cho đặc tính rủi ro của Breakout Momentum — trade tần suất cao, hold ngắn, rủi ro chính là breakout giả. Tool D có đặc tính khác hẳn: tần suất thấp hơn, hold dài hơn (chờ zone hấp thụ), rủi ro chính là zone sai/trend context đảo chiều giữa chừng. **Dùng chung ngưỡng là ép hai bài toán khác nhau vào một bộ tham số — đây chính là loại lỗi mà DR-002 của Tool A đã cảnh báo khi bỏ ¼ Kelly cứng nhắc.**

Cấu trúc công thức (nhân dồn các hệ số) được giữ vì nó là một pattern quản trị rủi ro tổng quát tốt, không phải nội dung chiến lược — nhưng **từng hệ số phải hiệu chỉnh riêng cho Tool D.**

## 6.2. Công thức — 🔴 v6 VIẾT LẠI

> **Bốn lỗi của v5 được sửa ở đây:** (1) `L_BASE` là tham số mồ côi — nằm trong kiểm kê DOF nhưng KHÔNG có trong công thức định cỡ duy nhất §6.8f; (2) `mult_cross` được mô tả ba kiểu ở ba nơi; (3) `deployed_ratio_tool_d` chưa bao giờ được định nghĩa; (4) `mult_edge` trỏ sang "công thức Tool A" — vi phạm tuyên bố zero-dependency ở header và §11.

```python
# ══════════════════════════════════════════════════════════════════
# 🔴 RÀNG BUỘC BAO TRÙM: MỌI hệ số mult_* PHẢI ≤ 1.0
#
#    rho là TRẦN ngân sách rủi ro mỗi lệnh (D0.1). Cho bất kỳ mult
#    nào > 1.0 là phá D0.1 và làm SỤP chứng minh worst-case ở §3.2
#    (`max L = L(3) = rho × E` không còn đúng).
#    → Ý "tín hiệu tốt thì cược to hơn" CHỈ được thực hiện bằng cách
#      HẠ size ở tín hiệu xấu, KHÔNG BAO GIỜ bằng cách NÂNG ở tín
#      hiệu tốt. Kết quả tương đối giống hệt; trần tuyệt đối được giữ.
# ══════════════════════════════════════════════════════════════════

# Hệ số 1 — 🆕 v6: mult_regime (THAY `L_BASE`, đã xoá)
mult_regime = 1.0   if ADX(14,1D) >= 25        # TREND_STRONG
         else 0.7                              # TREND_WEAK, 20 <= ADX < 25
   # KHÔNG có nhánh thứ ba: ADX < 20 đã bị §2.5 chặn KHÔNG VÀO LỆNH.
   # 🔒 ĐÓNG BĂNG (0.7 và ngưỡng 25). frozen_rationale: chỉ điều tiết
   #    KÍCH CỠ, không đổi TẬP LỆNH; ngưỡng 25 là quy ước Wilder cùng
   #    nguồn với ngưỡng 20 đã đóng băng — giữ quy ước = không tuyên
   #    bố phát hiện gì.
   #
   # 🔴 VÌ SAO XOÁ `L_BASE = {2.5, 1.0, 0.0}`:
   #    §6.8f chốt công thức định cỡ DUY NHẤT và L_BASE KHÔNG có mặt
   #    trong đó. Nó không tác động vào bất kỳ con số nào được tính,
   #    nhưng vẫn chiếm 1 DOF = 6 trial. Nhánh NO_TREND = 0.0 là thừa
   #    vì §2.5 đã chặn từ trước. Đây là tham số mồ côi đúng nghĩa.

# Hệ số 2 — chất lượng zone, ĐỘC QUYỀN của Tool D
mult_zss = clip(ZSS, 0.5, 1.0) / 1.0
           # ZSS thấp (nhưng vẫn qua ngưỡng §1.3) → size nhỏ hơn theo tỷ lệ
           # 0 DOF: suy thẳng từ ZSS, không có ngưỡng tự do
           # (§7.4: nhân thêm confirm_ratio → mult_zss_adjusted)

# Hệ số 3 — tương quan pool
mult_corr = 0.5 if corr_pool > 0.85 else (0.75 if corr_pool > 0.60 else 1.0)
            # 🟡 TUNABLE — mục #10 trong 12 DOF (DR-010)
            # 🔴 v7 — ĐỊNH NGHĨA corr_pool (LD-35: v6 chỉ có tên):
            #   corr_pool = mean( |corr( r_1H(coin_xét), r_1H(coin_j) )| )
            #               với j chạy trên MỌI vị thế ĐANG MỞ của Tool D,
            #               r_1H = log-return nến 1H, cửa sổ 30 ngày
            #               (720 nến) tính tới nến đã ĐÓNG gần nhất.
            #   Không có vị thế mở → corr_pool = 0 → mult_corr = 1.0.
            #   Cửa sổ 30 ngày: HẰNG SỐ ĐỊNH NGHĨA, liệt kê tường minh
            #   theo LD-35(b); không tune (đổi = đổi định nghĩa, Cấp C).
            #   Hai ngưỡng 0.60/0.85 mới là DOF #10.
            # Vì sao đây là DOF trong khi các mult_* khác thì không:
            # nó ĐỔI TẬP LỆNH gián tiếp qua kiểm tra kết nạp §6.8f
            # (size nhỏ hơn → margin ít hơn → nhét vừa thêm lệnh).
            # Cùng ngoại lệ với `L_exchange` ở §6.9.2.

# Hệ số 4 — drawdown riêng của Tool D
mult_dd = 1.0 if dd_tool_d <= 0.05 else (0.5 if dd_tool_d <= 0.08 else 0.0)
          # 🔒 CẤP C — KHOÁ VĨNH VIỄN, KHÔNG tune, KHÔNG tính vào N.
          # 🔴 v6 SỬA MÂU THUẪN: v5 vừa đánh dấu [CẦN CALIBRATE] +
          #    đếm 1 DOF, vừa xếp vào Cấp C "không bao giờ đổi", vừa
          #    dùng làm 1 trong BA TẦNG CHẶN vòng lặp thua lỗ (§12b.2).
          #    Không thể vừa là thứ được tối ưu trên backtest vừa là
          #    cầu dao bất khả xâm phạm. → Cầu dao thắng.
          # mult_dd = 0.0 KHÔNG phải "size = 0" mà là HALT — xem §12c.5
          # để biết cơ chế mở lại (v5 không có, và HALT của v5 bị
          # DEADLOCK: dừng mở lệnh → không có lệnh đóng → dd không
          # hồi VÀ điểm quyết định không bao giờ tới).

# Hệ số 5 — 🆕 v6: edge decay, VIẾT TƯỜNG MINH (không trỏ Tool A nữa)
edge_ratio_D = expectancy(50 lệnh live gần nhất, Tool D)
             / expectancy_kỳ_vọng(cấu hình đã qua lockbox)
mult_edge = 0.5 if edge_ratio_D < 0.5 else 1.0
   # 🔒 ĐÓNG BĂNG. frozen_rationale: "edge còn chưa tới một nửa mức
   #    đã được lockbox xác nhận" là dải phát hiện THÔ NHẤT có thể
   #    đặt — không phải một giá trị được chọn trong nhiều giá trị.
   #    Trước 50 lệnh live: mult_edge = 1.0 (chưa đủ mẫu để kết luận,
   #    §12c.1: n=50 cho SE 7,1pp).
   #
   # 🔴 v6 SỬA: v5 ghi "như công thức Tool A" — vi phạm trực tiếp
   #    tuyên bố ở header ("không tra ngược sang Tool A") và ở §11
   #    ("Zero-dependency đã chốt"). Một công thức không viết ra được
   #    là một công thức không code được.

# Hệ số 6 — 🆕 v6: tải triển khai, ĐỊNH NGHĨA TƯỜNG MINH
deployed_ratio_tool_d = Σ notional ĐÃ KHỚP (mọi vị thế mở)
                      / Σ notional KẾ HOẠCH đủ 3 tranche (mọi vị thế mở)
mult_deploy = 0.5 if deployed_ratio_tool_d > 0.85 else 1.0
   # 🔒 ĐÓNG BĂNG (0.85). frozen_rationale: dùng lại hằng số ĐÃ CÓ ở
   #    §6.8f (trần margin), 0 hằng số mới.
   #
   # 🔴 v6 SỬA: v5 dùng `deployed_ratio_tool_d` mà KHÔNG BAO GIỜ định
   #    nghĩa nó — một biến không định nghĩa nhân thẳng vào size.
   #    Định nghĩa trên là cách đọc DUY NHẤT khiến hệ số này KHÔNG
   #    trùng chức năng với trần margin §6.8f: nó đo "bao nhiêu phần
   #    KẾ HOẠCH đã thành THỰC", tức mức độ phơi nhiễm thật, trong khi
   #    §6.8f đo margin đã RESERVE theo kế hoạch (D0.3/D0.5) — hai
   #    con số khác nhau vì margin được đặt trước cho cả 3 tranche.
   #    ⚠️ Nếu đọc theo nghĩa "Σ margin / E_D" thì hệ số này là CODE
   #       CHẾT (trùng đúng ngưỡng 0.85 của §6.8f, không bao giờ kích
   #       hoạt ở trạng thái còn mở được lệnh). Ghi lại để không ai
   #       code theo nghĩa đó.

# ❌ Hệ số 7 — mult_cross: 🔴 v6 ĐÃ XOÁ HOÀN TOÀN
#    v5 mô tả nó BA KIỂU ở BA NƠI:
#       §6.2  "TUỲ CHỌN, không tính vào L_total_D mặc định"
#       §9.3  "VẪN GIỮ P0 bất kể overlap DSR ra sao"
#       §14#4 "✅ CHỐT v5 — chờ xác nhận bỏ hay giữ"  (tự mâu thuẫn)
#       §11 H2 "cộng mult_cross"  (vẫn là việc phải làm)
#    LÝ DO XOÁ: lý do tồn tại của nó là trần rủi ro GỘP giữa hai tool.
#    Trần gộp đã bị bỏ ở §6.5 (hai sub-account, vốn riêng, tự quản).
#    Giữ nó = giữ một cơ chế đã mất lý do tồn tại, ĐỒNG THỜI bắt H2
#    xây hạ tầng đọc chéo sub-account mà §6.6 vừa tuyên bố không cần.
#    Rủi ro sập đồng pha vẫn được ghi nhận ở §6.5 như một SỰ THẬT về
#    thị trường, không phải một hệ số.

# ══════════════════════════════════════════════════════════════════
# ✅ CÔNG THỨC ĐỊNH CỠ — DUY NHẤT. Đầy đủ ở §6.8f.
# ══════════════════════════════════════════════════════════════════
rho_eff  = rho * mult_regime * mult_zss * mult_corr
               * mult_dd * mult_edge * mult_deploy
N_full   = (rho_eff * E_D) / R_eff          # RỦI RO cố định (D0.1)
margin   = N_full / L_exchange              # L_exchange cấu hình được (§6.8)

# 🔴 v4 — BA DÒNG CÔNG THỨC CŨ ĐÃ BỊ XOÁ (giữ ghi chú để truy vết):
#     notional_per_idea = (L_total_D * E) / max_open_D
#     risk_per_idea_pct = (notional_per_idea / E) * R_eff
#     margin_per_idea   = notional_per_idea / 5
# LÝ DO XOÁ (§6.8e): định cỡ theo VỐN cố định, mâu thuẫn trực tiếp
# với D0.1 + §3.2 định cỡ theo RỦI RO cố định. D0.1 là nguyên lý bất
# biến nên nó thắng. Dòng thứ ba còn hardcode /5.

# L_total_D = Σ N_full(mọi vị thế) / E_D   ← ĐO ĐƯỢC, không phải đầu vào
# ❌ L_D_max — 🔴 v6 ĐÃ XOÁ, xem §6.8c. §6.8f tự chứng minh nó ≡
#    0.85 × L_exchange, tức cùng một ràng buộc viết theo hai cách.
```

## 6.3. Vì sao `mult_zss` là cải tiến quan trọng nhất so với v1

Thiết kế v1 dùng size cố định cho mọi tín hiệu qua gate (nhị phân: qua hoặc không qua). Thiết kế v2 **scale liên tục theo chất lượng zone**. Đây là khác biệt giữa "DCA" và "**Smart** DCA" đúng nghĩa: hệ thống không chỉ hỏi "có nên vào không", mà "nên vào với niềm tin bao nhiêu" — và trả lời bằng chính dữ liệu đã dùng để tìm ra zone, không thêm chỉ báo mới, không thêm bậc tự do (ZSS đã tồn tại từ Phần 1).

## 6.4. Margin & thanh lý — tính lại vì R_eff giờ biến thiên theo zone

```
🔴 Không còn một con số "đệm thanh lý" cố định như v1 (9.6 lần) —
   nó giờ PHỤ THUỘC ZONE, dao động theo zone_width thực tế.

GATE bắt buộc RIÊNG (không có ở v1) — 🔴 v6 ĐỊNH NGHĨA LẠI BẰNG CÔNG THỨC:

🔴 v5 VIẾT SAI THANG ĐO, gate này TRƯỚC ĐÂY KHÔNG TÍNH ĐƯỢC:
      "Buffer thanh lý = (p1 − liquidation_price)/p1"   ← một tỷ lệ %
      "NẾU buffer < 8 lần đệm SL"                        ← so với "8 lần"
   Vế trái là %, vế phải là bội số. Không so sánh được. Trong khi
   `liq_buffer_ratio` lại là trường BẮT BUỘC của Decision Log (§8),
   là test L-Z3 CRITICAL, và là một tiêu chí GATE D0.9 (§10.2).
```

## 6.4b. 🆕 v6 — Công thức `liq_buffer_ratio`

```python
# case LONG (SHORT đảo dấu). 🔴 Tính trên KẾ HOẠCH ĐẦY ĐỦ 3 TRANCHE
# (D0.3/D0.5), KHÔNG phải trên phần đã khớp.

p_avg_plan = Σ w[i] × p[i]              # giá vào TB nếu khớp đủ 3 tranche
liq_price  = f(p_avg_plan, N_full, margin_plan, mmr_binance)
             # mmr = maintenance margin rate theo bậc notional của Binance,
             # đọc từ API leverage-bracket, KHÔNG hardcode

liq_buffer_ratio = (p_avg_plan − liq_price) / (p_avg_plan − sl)

🚪 GATE §6.4:  liq_buffer_ratio ≥ 8  tại thời điểm xét tranche 1
               không thoả → TỪ CHỐI mở, bất kể ZSS cao thế nào
🔒 Ngưỡng 8: CẤP C, khoá vĩnh viễn, KHÔNG tune, KHÔNG tính vào N.
```

**Đọc thành lời:** *"khoảng cách tới thanh lý gấp mấy lần khoảng cách tới SL"* — đúng nghĩa "8 lần đệm SL" mà §6.4 muốn nói, và là một **tỷ số không đơn vị** nên so sánh được với 8.

```
🔴 BA ĐIỂM BẮT BUỘC ĐI KÈM:

(1) PHẢI dùng p_avg_plan, KHÔNG dùng p1.
    Đây là lỗi thật, không phải lỗi ký hiệu: liq_price dịch chuyển
    BẤT LỢI mỗi lần tranche khớp thêm (giá vào TB xấu đi, notional
    tăng). Gate tính trên p1 sẽ PASS ở tranche 1 rồi VI PHẠM ở
    tranche 3 — đúng lúc vị thế lớn nhất và rủi ro cao nhất.

(2) Decision Log ghi CẢ TỬ VÀ MẪU, không chỉ tỷ số:
       liq_dist_pct  = (p_avg_plan − liq_price)/p_avg_plan
       r_eff_pct     = (p_avg_plan − sl)/p_avg_plan
       liq_buffer_ratio
    Không có hai số đầu thì L-Z3 fail mà không biết fail vì đâu.

(3) 🔴 CON SỐ "12,9 lần" Ở VÍ DỤ §3.2 PHẢI TÍNH LẠI.
    Không truy được nó ra từ dữ liệu trong spec (không rõ v5 dùng p1
    hay p_avg, mmr bao nhiêu). Ghi nhận là CHƯA TRUY ĐƯỢC — mọi ví
    dụ số trong §3.2 và §6.8b phải chạy lại sau khi công thức này
    được code, TRƯỚC khi dùng làm căn cứ cho bất kỳ lập luận nào.
```

> ⚠️ **Ghi nhận vận hành, để không hiểu nhầm gate này đang làm việc:** §6.8b tự chỉ ra ở `L_exchange = 3` (mặc định YAML) đệm thanh lý ≈ 21,5× nên gate ≥8 *"gần như luôn qua"*. Nghĩa là ở cấu hình mặc định, gate này là **lưới an toàn cho ca 5x + zone cực hẹp**, không phải ràng buộc hoạt động thường xuyên. Ghi rõ để tránh ca "tưởng gate đang bảo vệ trong khi nó chưa từng kích hoạt lần nào". Phân bố `liq_buffer_ratio` thực tế được báo cáo ở `periodic_report.py` (§12d.2) chính vì lý do này.

Đây là hệ quả trực tiếp của việc SL neo zone thay vì cố định: zone hẹp cho size lớn (§3.2 minh hoạ: 0.417E) nhưng cũng cho đệm thanh lý hẹp hơn theo cùng tỷ lệ nghịch với zone rộng. Gate này là **cái phanh** cho chính cơ chế tối ưu ở §3.1 — không có nó, hệ thống sẽ tự nhiên bị hút về phía chọn zone càng hẹp càng tốt (vì size lớn hơn = "trông" hấp dẫn hơn trên backtest) mà không nhận ra nó đang đánh đổi bằng đệm thanh lý.

## 6.5. Ngân sách vốn — mỗi tool tự quản lý độc lập, không có cấp bậc

> 🆕 **Chốt lại theo quyết định của bạn** (thay bản trước đề xuất trần gộp + phân cấp Tool A/Tool D — không còn hợp lý khi vốn đã tách sub-account).

```
✅ Tool A và Tool D: hai sub-account riêng, vốn nạp riêng, TỰ QUẢN LÝ
   độc lập theo phần vốn được cấp cho từng tool. Không có khái niệm
   "trần gộp", không có "tool phụ/tool chính".

✅ Lý do đây là quyết định hợp lý: isolated margin (đã có sẵn ở cấp
   position) + sub-account riêng (§6.5b) đã tự nhiên chặn rủi ro
   thanh lý của Tool D không lan sang Tool A và ngược lại. Một trần
   L "gộp" phía trên hai giới hạn đã có sẵn này không ngăn thêm được
   rủi ro cụ thể nào — nó chỉ là bookkeeping thừa.

🔴 v6 — `L_D_max` ĐÃ XOÁ (§6.8c). Mức đòn bẩy danh mục của Tool D
   được quyết bởi HAI con số bạn đã chọn ở Tầng A: `L_exchange` và
   trần margin 0.85 × E_D (§6.8f). Không có con số thứ ba.
```

> **Một sự thật khách quan, ghi lại một lần, không phải khuyến nghị bắt buộc:** thị trường sập không phân biệt ví — nếu BTC giảm mạnh, cả hai sub-account có thể cùng lỗ cùng lúc dù vốn và quản lý hoàn toàn tách biệt. Đây là đặc điểm của thị trường crypto (altcoin correlated 0.7-0.85, v10 §1.3), không phải điều gì Tool D có thể tự giải quyết bằng thiết kế. Việc theo dõi rủi ro đồng pha này — nếu bạn muốn — là lựa chọn vận hành của riêng bạn, không phải yêu cầu bắt buộc của spec này nữa.

## 6.5b. Sub-account riêng cho từng tool — vận hành, KHÔNG phải thống kê

**Quyết định:** Tool A và Tool D chạy trên **hai sub-account Binance riêng**, vốn nạp riêng, mỗi tool tự chịu trách nhiệm quản lý phần vốn của mình.

**Cái này giải quyết:**
```
✅ mult_dd tính sạch — đọc thẳng equity curve từ API sub-account riêng
✅ Universal Transfer risk (§13.2 v10) giảm — API key phạm vi riêng
✅ Kỷ luật nạp/rút vốn theo quý dễ theo dõi, ít nhầm lẫn
✅ Rủi ro thanh lý của tool này không chạm được tới vốn của tool kia
   — đây là lý do trần gộp ở §6.5 (bản trước) trở nên thừa
```

**Cái này KHÔNG giải quyết — vẫn cần biết, dù không còn là yêu cầu bắt buộc:**
```
❌ DR-007 KHÔNG đổi vì sub-account. DSR deflate theo dữ liệu giá lịch
   sử đã chạm (backtest/hyperopt), không theo ví tiền. Xem Phần 9 —
   trạng thái DR-007 phụ thuộc overlap POOL (§0.3), không phụ thuộc
   cấu trúc tài khoản.
```

## 6.6. Risk Supervisor — mỗi tool một tiến trình riêng

> 🆕 Đổi so với bản trước (yêu cầu một Risk Supervisor gộp) — theo đúng quyết định của bạn: mỗi tool tự quản lý, mình không còn đề xuất hạ tầng giám sát chéo.

```
Tool D có Risk Supervisor RIÊNG, đọc MỘT sub-account của chính nó,
tính mult_dd, mult_deploy, margin_ratio, kill-switch — tất cả trong
phạm vi vốn của Tool D. Không cần đọc sub-account của Tool A.

🔴 v7 — BỐN RÀNG BUỘC VẬN HÀNH (LD-22, LD-23, LD-26):

(1) SL SỐNG TRÊN SÀN. KHÔNG BAO GIỜ viết kiểu "bot theo dõi giá rồi
    gửi lệnh đóng khi chạm SL" — cơ chế đó chết cùng tiến trình.
    (D0.2 + Assumption D2 đã ngụ ý; ghi tường minh.)

(2) SUPERVISOR KHÔNG IMPORT CODE BOT. Nó tự gọi API sàn để đọc ký
    quỹ/vị thế, sống độc lập với bot. Hệ quả chấp nhận: vài hằng số
    (E_D, thang dd 5/8/20, trần margin 0.85) bị KHAI LẠI CÓ CHỦ ĐÍCH
    — đây là ngoại lệ HỢP LỆ DUY NHẤT của nguyên tắc "một nguồn sự
    thật" (LD-09), và phải ghi chú tường minh tại chỗ khai lại + có
    test L-Z44 đối chiếu hai bản khai bằng nhau.
    Trạng thái LIQUIDATED = CỜ ĐỎ DỪNG TOÀN HỆ THỐNG, không phải
    dòng log cảnh báo.

(3) TRẦN SỐ LỆNH GỌI API — CẤP C, KHOÁ VĨNH VIỄN (tool_d_config
    tier_c.api_calls_per_min). Tool A bị Binance trả 418 (tự động
    cấm IP), án phạt tăng dần tới 3 ngày với ai TIẾP TỤC gọi trong
    lúc bị cấm — mất nhiều ngày vận hành.
    • Nhịp gọi theo NHỊP DỮ LIỆU THẬT ĐỔI: nến 1H đóng mỗi giờ →
      quét mỗi giờ. Gọi dày hơn KHÔNG tươi hơn. Tool D theo dõi zone
      + trạng thái tranche → cám dỗ polling dày rất lớn — cấm.
    • Gặp 418/429 → DỪNG NGAY giữa chừng, KHÔNG quét nốt các mã còn
      lại (mỗi lượt gọi thêm kéo dài án phạt).
    • Lùi giờ phân tầng: lỗi mạng lẻ tẻ lùi ngắn; rate-limit lùi dài.
    • Nhận diện lỗi theo HÌNH DẠNG exception, không theo chuỗi thông
      báo.

(4) MỘT ENDPOINT LỖI KHÔNG ĐƯỢC LÀM HỎNG CẢ SNAPSHOT. Bắt lỗi theo
    TỪNG endpoint; endpoint đã thành công vẫn dùng; endpoint lỗi ghi
    trạng thái `unreadable` (§0d.6), không phải 0.
```

## 6.7. 🆕 v3 — Network/Auth latency probe qua `/order/test`, không cần đợi A3

> **Đã verify qua tra cứu tài liệu Binance** (không suy đoán): `POST /fapi/v1/order/test` — *"this order will not be submitted to matching engine"* — xác nhận zero rủi ro tài chính, endpoint không bao giờ khớp lệnh thật dù tham số gì.

```
Dùng /order/test với key production để đo network+auth latency thật
tới Binance TRƯỚC khi vào giai đoạn dry-run/live — không cần đợi hạ
tầng hoàn thiện mới biết latency có vấn đề hay không.
```

**Một điểm cần biết trước khi tin con số đo được:** endpoint dừng trước bước matching engine, nên latency đo được là **cận dưới** của latency lệnh thật (bỏ qua round-trip xử lý khớp lệnh). Dùng làm ước lượng ban đầu, không thay thế đo lại ở giai đoạn dry-run/live.

**Với Tool D cụ thể — mức ưu tiên P1, không phải P0:** Tool D có độ trễ cấu trúc sẵn có lớn hơn network latency rất nhiều — zone confirm 12h (Phần 7) + entry confirmation tối đa 3 nến 1H (§3.3b). Chênh lệch vài trăm ms không đáng kể so với các độ trễ đã thiết kế sẵn. Vẫn nên làm (vệ sinh hạ tầng tốt, và key này đằng nào cũng cần dùng sau), nhưng không chặn tiến độ nếu chưa làm ngay.

```
🔴 Điều kiện bảo mật bắt buộc khi tạo key production sớm hơn dự kiến
   (rủi ro thật không nằm ở endpoint — nằm ở NĂNG LỰC của key vừa tạo,
   vì để gọi /order/test key cần bật quyền Futures Trading, cùng phạm
   vi với lệnh thật):

   • TẮT quyền rút tiền/chuyển khoản (Withdrawal) — không bao giờ cần
     cho cả /order/test lẫn vận hành Tool D
   • BẬT IP whitelist ngay từ đầu, giới hạn đúng IP máy chạy test/bot
   • Ghi ngày tạo key vào research-log — phục vụ audit thời gian key
     đã tồn tại trước khi hệ thống hoàn thiện
```

**Một điểm cần verify lại, không nhận nguyên premise "Freqtrade không hỗ trợ testnet":** tra cứu thấy bằng chứng trái chiều — có cấu hình Freqtrade thực tế dùng `Binance futures testnet API keys` (GitHub issue #12894, 3/2026), và testnet API-based USDⓈ-M Futures của Binance vẫn hoạt động (chỉ phần mock-trading trên app/web tạm ngưng nâng cấp từ 8/2025). Không có nghĩa phương án `/order/test` sai — chỉ là nên thử set testnet URL/sandbox mode trong config Freqtrade một lần, ghi lại lỗi cụ thể nếu có, trước khi khẳng định chắc chắn phải dùng key production. Nếu verify xong vẫn không dùng được, `/order/test` là lựa chọn hợp lý đã kiểm chứng ở trên.

---

# PHẦN 6b — 🔴 v3.3: CẤU HÌNH VỐN & ĐÒN BẨY

> Chèn sau §6.7. Spec trước cứng `L_exchange = 5x` và chưa bao giờ nói `E` lấy từ đâu, cũng chưa bao giờ định nghĩa `max_open_D` dù dùng nó làm mẫu số ở §6.2 (mâu thuẫn này gỡ ở §6.8e/§6.8f).

## 6.8. Ba con số khác nhau — spec trước đang trộn

```
E_D          Vốn PHÂN BỔ cho Tool D. NGƯỜI CHỌN.
             🔴 KHÔNG phải số dư ví. VD: ví 1000 USDT, E_D = 500.
             Cấu hình Freqtrade: tradable_balance_ratio = 0.5
             🔴 MỌI công thức §6.2 dùng E = E_D. Nếu để E đọc số dư ví,
                hệ thống tính size trên 1000 và 500 kia KHÔNG còn là đệm.

L_exchange   Đòn bẩy đặt trên sàn. NGƯỜI CHỌN, dải 2x-5x. Mặc định
             cũ 5x giờ thành TUỲ CHỌN, không phải hằng số.
             🔒 FROZEN theo quyết định vận hành — KHÔNG tune, KHÔNG
                tính vào N (không phải tham số chiến lược).

L_total_D    Bội số notional/vốn. HỆ THỐNG TỰ TÍNH, ĐO ĐƯỢC sau khi
             các vị thế đã mở: Σ N_full / E_D. Người KHÔNG chọn.
             🔴 v6: `L_D_max` đã bị XOÁ (§6.8c) — trần thật là ràng
             buộc margin 0.85 × E_D ở §6.8f, và nó đã bao hàm L_D_max.
```

## 6.8b. Hiểu nhầm phải sửa: hạ đòn bẩy KHÔNG giảm rủi ro mỗi lệnh

```
Rủi ro một lệnh = notional × R_eff
   R_eff = khoảng cách tới SL neo zone (§3.2)
   → Đổi 5x → 3x KHÔNG đụng vào cả hai số này.

Cái nó THỰC SỰ đổi:

   ┌────────────────────┬──────────────┬──────────────┐
   │                    │      5x      │      3x      │
   ├────────────────────┼──────────────┼──────────────┤
   │ Rủi ro/lệnh        │  không đổi   │  không đổi   │
   │ Margin cần         │  notional/5  │  notional/3  │ ← cần NHIỀU hơn
   │ Đệm thanh lý       │  ~12.9×      │  ~21.5×      │ ← TỐT hơn nhiều
   │ Gate ≥8× (§6.4)    │ có lúc chặn  │ gần như luôn qua │
   └────────────────────┴──────────────┴──────────────┘
   (số minh hoạ theo ví dụ zone ở §3.2, không phải kết quả backtest)

→ Hạ đòn bẩy = MUA đệm thanh lý bằng margin. Đánh đổi tốt, và nó nới
  lỏng nút thắt §6.4 đang từ chối các zone hẹp có ZSS cao.
```

## 6.8c. Ràng buộc spec chưa từng nêu

```
🔴 v6 — `L_D_max` ĐÃ BỊ XOÁ. Mục này giữ lại làm GHI CHÚ TOÁN HỌC.

   L_total_D  = Σ notional / E_D                     ← ĐO ĐƯỢC
   Margin cần = Σ notional / L_exchange

   Ràng buộc thật, và là ràng buộc DUY NHẤT cần kiểm:
      Σ margin ≤ 0.85 × E_D            (điều kiện (b), §6.8f)
   ⇔  Σ notional ≤ 0.85 × E_D × L_exchange
   ⇔  L_total_D ≤ 0.85 × L_exchange

   → "L_D_max" chỉ là vế phải của bất đẳng thức trên, viết lại dưới
     một cái tên khác. §6.8f đã tự chứng minh điều này ở phần KIỂM
     TRA CHÉO. Giữ cả hai = HAI NGUỒN SỰ THẬT cho MỘT ràng buộc —
     đúng loại lỗi mà §6.8e vừa mất công gỡ cho công thức định cỡ.

   ⚠️ Bằng chứng nó vô nghĩa trong thực tế: YAML v5 đặt L_D_max = 2.5
      với L_exchange = 3, trong khi 0.85 × 3 = 2.55. Trần "riêng" chỉ
      chặt hơn trần thật 2% — không chặn được ca nào mà §6.8f không
      chặn, nhưng vẫn là một ô nhập người dùng có thể điền sai.

   🚪 Ai muốn hạ đòn bẩy danh mục xuống: hạ `L_exchange`, hoặc hạ hệ
      số 0.85. KHÔNG thêm lại một trần thứ ba.

## 6.8d. Ngân sách rủi ro danh mục — đầu vào của kiểm tra kết nạp

> 🔴 **v4 — mục này đã được viết lại.** Bản trước định nghĩa `max_open_D` như một HẰNG SỐ (`= floor(40/1.875) = 21`). Cách đó **sai** và bị thay bằng kiểm tra kết nạp động ở §6.8f. Lý do sai: nó giả định mọi lệnh có cùng notional, trong khi với rủi ro cố định thì notional biến thiên theo `R_eff` — nên số lệnh nhét vừa ngân sách margin cũng biến thiên.

```
Người dùng chỉ điền MỘT con số ở đây:

   daily_loss_budget_pct = % lỗ TỐI ĐA chấp nhận trong MỘT ngày xấu
                           tính với GIẢ ĐỊNH TƯƠNG QUAN = 1

🔴 GIẢ ĐỊNH TƯƠNG QUAN = 1 LÀ BẮT BUỘC:
   Altcoin tương quan 0.7-0.85 với BTC (v10 §1.3). Trong một cú sập,
   tương quan thực tế TIẾN VỀ 1. Định cỡ theo giả định các lệnh độc
   lập = định cỡ cho một thị trường KHÔNG TỒN TẠI.

Con số này KHÔNG suy ra được từ dữ liệu — nó là khẩu vị rủi ro cá
nhân. Cùng với E_D và L_exchange, đây là ba con số người dùng phải
điền ở bước D0-PRE.

→ Nó được dùng làm điều kiện (a) trong kiểm tra kết nạp §6.8f.
→ Số vị thế tối đa là KẾT QUẢ của §6.8f, KHÔNG phải tham số ở đây.
```

## 6.8e. 🔴 v4 — HOÀ GIẢI HAI CÔNG THỨC ĐỊNH CỠ ĐANG MÂU THUẪN

> **Lỗi tài liệu tự phát hiện.** Spec chứa HAI công thức định cỡ cho ra kết quả khác nhau, và chưa bao giờ nói cái nào thắng.

```
§3.2 + D0.1  (RỦI RO cố định):
   N_full = (rho × E_D) / R_eff        →  rủi ro/lệnh KHÔNG ĐỔI
   (§3.2 nói rõ: "max L = L(3) = rho × E theo cách suy ngược N_full")

§6.2         (VỐN cố định):
   notional_per_idea = (L_total_D × E) / max_open_D
   risk_per_idea_pct = (notional_per_idea / E) × R_eff
                                        →  rủi ro/lệnh BIẾN THIÊN theo R_eff

🔴 Hai cái này không thể cùng đúng. Đây chính là tranh luận Z0-S1
   (§10.1b) đã nằm sẵn trong spec dưới dạng hai công thức đá nhau.
```

### Phán quyết

```
D0.1 là NGUYÊN LÝ BẤT BIẾN (§3.4) → nó thắng.

   → RỦI RO CỐ ĐỊNH định cỡ mỗi lệnh:  N_full = (rho × E_D) / R_eff
   → §6.2 KHÔNG phải công thức định cỡ. Nó là RÀNG BUỘC DANH MỤC —
     trần tổng, không phải suất chia đều.

🔴 SỬA §6.2: dòng `notional_per_idea = (L_total_D × E) / max_open_D`
   KHÔNG còn là công thức size. Nó được thay bằng KIỂM TRA KẾT NẠP
   ở §6.8f. Các hệ số mult_* (§6.2) vẫn giữ nguyên vai trò — chúng
   nhân vào rho hiệu dụng, không nhân vào notional trực tiếp.
```

## 6.8f. 🆕 v4 — KẾT NẠP VÀO DANH MỤC: `max_open_D` KHÔNG phải hằng số

```
BƯỚC 1 — Size lệnh ứng viên (rủi ro cố định, D0.1):
   rho_eff = rho × mult_zss × mult_corr × mult_dd × mult_edge × mult_deploy
   N_full  = (rho_eff × E_D) / R_eff
   margin  = N_full / L_exchange

BƯỚC 2 — KIỂM TRA KẾT NẠP. Chỉ mở nếu SAU KHI mở vẫn thoả CẢ HAI:

   (a) Σ rủi ro (mọi vị thế, tính trên KẾ HOẠCH đầy đủ — D0.5)
          ≤ daily_loss_budget_pct × E_D
       🔴 với GIẢ ĐỊNH TƯƠNG QUAN = 1 (§6.8d)

   (b) Σ margin (mọi vị thế, KẾ HOẠCH đầy đủ — D0.3)
          ≤ 0.85 × E_D

   Không thoả một trong hai → KHÔNG MỞ, bất kể ZSS cao thế nào.

🔑 HỆ QUẢ: số mã tối đa là KẾT QUẢ, không phải tham số.
   Nó dao động theo độ rộng zone của chính các lệnh đang mở.
```

### Ví dụ đầy đủ — `E_D`=500, `rho`=0.375%, `L_exchange`=3x, `daily_loss_budget`=8%

*(minh hoạ công thức, KHÔNG phải kết quả backtest)*

```
Rủi ro mỗi lệnh CỐ ĐỊNH = 0.375% × 500 = 1.875 USDT
Trần margin = 0.85 × 500 = 425 USDT
Trần rủi ro = 8% × 500 = 40 USDT  →  40/1.875 = 21 lệnh
```

| `R_eff` | Notional/lệnh | Margin/lệnh | Số mã tối đa | Ràng buộc siết |
|---|---|---|---|---|
| 0,9% (rất hẹp) | 208 USDT | 69,4 | **6** | margin |
| 1,5% | 125 USDT | 41,7 | **10** | margin |
| 2,0% | 94 USDT | 31,3 | **13** | margin |
| 3,0% (rộng) | 62 USDT | 20,8 | **20** | margin |

```
🔑 KIỂM TRA CHÉO — vì sao mọi hàng cho cùng một tổng:
   6 × 208 = 1250      20 × 62 = 1250
   Tổng notional ≤ 0.85 × E_D × L_exchange = 425 × 3 = 1275 ≈ 2.55 × E_D

   → 🔴 v6: chính phép kiểm tra chéo này là LÝ DO XOÁ `L_D_max`.
     Nó KHÔNG phải một trần độc lập — nó là `0.85 × L_exchange` viết
     dưới một cái tên khác. Xem §6.8c.

⚠️ Ở 3x, trần RỦI RO (21 lệnh) KHÔNG BAO GIỜ CHẠM TỚI — margin luôn
   siết trước. Ở 5x thì đảo lại với zone rộng. Đây là lý do phải kiểm
   CẢ HAI điều kiện, không chọn một.
```

> 🔴 **`mult_deploy` (§6.2 hệ số 6) giữ vai trò lớp phòng thủ thứ hai, nhưng CHỈ KHI đọc đúng định nghĩa v6:** `deployed_ratio_tool_d` = Σ notional **đã khớp** / Σ notional **kế hoạch** — tức mức phơi nhiễm THẬT, khác với margin đã reserve theo kế hoạch mà §6.8f kiểm. Nó chạy TRƯỚC bước kiểm tra kết nạp, không thay thế bước đó.
>
> ⚠️ Nếu code theo nghĩa "Σ margin / E_D" thì hệ số này là **code chết**: nó dùng đúng ngưỡng 0.85 của điều kiện (b), nên tại mọi trạng thái còn mở được lệnh thì `deployed_ratio ≤ 0.85` và hệ số luôn = 1.0. v5 không định nghĩa biến này nên cả hai cách đọc đều khả dĩ — đó là lý do v6 phải viết ra.

> ⚠️ **Điều này KHÔNG làm mất ý nghĩa của arm `Z0-S1` (§10.1b).** Z0-S1 vẫn cần chạy — nó kiểm chứng xem rủi-ro-cố-định (nay đã là phán quyết chính thức) có thực sự tốt hơn vốn-cố-định trên dữ liệu hay không. Phán quyết ở đây là về **tính nhất quán nội bộ**, không phải về **hiệu quả**. Hai câu hỏi khác nhau.

---

## 6.9. 🆕 v4 — BỀ MẶT CẤU HÌNH: cái gì được chỉnh, cái gì tiêu trial, cái gì khoá

> **Yêu cầu gốc:** *"trên giao diện bổ sung phần này để mình cài đặt tùy chỉnh qua thời gian."*
>
> 🔴 **Đây là tính năng nguy hiểm nhất trong toàn bộ tài liệu.** Một ô nhập liệu cho phép sửa ngưỡng bất cứ lúc nào **vô hiệu hoá toàn bộ DR-010 (ngân sách trial) và DR-012 (change-control)** mà không cần ai cố ý phá. Nó không được từ chối — nhưng phải PHÂN TẦNG.

### 6.9.1. Nguyên tắc phân tầng — một câu hỏi duy nhất

```
🔑 "Thay đổi này có làm ĐỔI TẬP LỆNH ĐƯỢC VÀO không?"

   KHÔNG  → chỉ đổi KÍCH CỠ  → TẦNG A, chỉnh tự do, 0 trial
   CÓ     → đổi TÍN HIỆU      → TẦNG B, TIÊU 1 TRIAL mỗi lần
   Nguyên lý D0 / gate an toàn → TẦNG C, KHOÁ VĨNH VIỄN

Lý do quy tắc này đúng: backtest đo EDGE của tập lệnh. Đổi kích cỡ
không đổi tập lệnh → kết quả backtest vẫn còn hiệu lực. Đổi ngưỡng
tín hiệu → tập lệnh khác → mọi kết quả đã có KHÔNG còn áp dụng, và
lần chỉnh đó là một phép thử mới, phải đếm vào N.
```

### 6.9.2. TẦNG A — chỉnh tự do, 0 trial

| Tham số | Ý nghĩa | Ràng buộc |
|---|---|---|
| `E_D` | Vốn phân bổ Tool D (VD 500 trong ví 1000) | `tradable_balance_ratio` phải khớp |
| `L_exchange` | Đòn bẩy sàn, dải 2x–5x | ⚠️ xem cảnh báo dưới |
| `rho` | Ngân sách rủi ro mỗi lệnh (%) | 🔒 **CHỈ đổi khi danh mục RỖNG** (0 vị thế mở) — chốt ở câu hỏi mở #16 |
| `daily_loss_budget_pct` | % lỗ tối đa chấp nhận trong một ngày xấu (giả định tương quan = 1) | Định nghĩa ở §6.8d; là điều kiện **(a)** của kiểm tra kết nạp §6.8f. *(v6: v5 lặp dòng này hai lần)* |
| ~~`max_open_D`~~ | ❌ **KHÔNG còn là tham số** | Thay bằng kiểm tra kết nạp động (§6.8f) — số mã là KẾT QUẢ |
| ~~`L_D_max`~~ | ❌ 🔴 **v6 — KHÔNG còn là tham số** | Nó ≡ `0.85 × L_exchange` (§6.8c). Trần thật là điều kiện **(b)** của §6.8f |
| `enable_long` / `enable_short` | Bật/tắt từng hướng | Short chỉ bật khi DG7 đã triển khai |
| `pool_size_target` | Mục tiêu số mã | Tiêu chí (i)-(iv) §0.3 vẫn là hàng rào cứng |

```
⚠️ NGOẠI LỆ DUY NHẤT — L_exchange KHÔNG hoàn toàn Tầng A:
   Nó đổi đệm thanh lý → đổi kết quả gate §6.4 (≥8×) → CÓ THỂ đổi
   tập lệnh (một số zone hẹp bị từ chối ở 5x sẽ được nhận ở 3x).
   → Đổi L_exchange BẮT BUỘC chạy lại phân bố liq_buffer trên CALIB
     và ghi kết quả vào research-log. Không tiêu trial, nhưng không
     phải "đổi rồi chạy luôn".
```

### 6.9.3. TẦNG B — chỉnh được, nhưng TIÊU 1 TRIAL mỗi lần

🔒 **v6 — chỉ còn 12 tham số** (danh sách đầy đủ + lý do ở DR-010):

`zss_threshold` · `buf_sl` · ngưỡng rejection wick 1H · `v_min` · ngưỡng funding rate (gộp §3.3d + DG6-D) · ngưỡng hồi 50% (DG6-D) · `DG4` · `DG6-A` tỉ lệ ATR · `TP1` trừ hao · ngưỡng `mult_corr` · `max_hold_bars` · **`DG7` ngưỡng `0.3 × R_eff`** 🆕

*(+1 nếu VERIFY ở D0-PRE cho thấy `zone_width` min KHÔNG phải code chết — §3.3)*

**8 KHOÁ ĐÓNG BĂNG** — `w_zss` (1/3) · `w_tranche` (1/3) 🆕 · ADX=20 · `mult_regime` 🆕 · TP2 trail=1.5 · funding rate=−0.05% · `DG6-B`=8 · tuổi trend=5 (có điều kiện) · và nhóm ngưỡng chẩn đoán (`mult_edge` 0.5, `mult_deploy` 0.85, TP_fallback 4.0/1.5, dải TIME_STOP 5–25%, H-4 40%).

Chúng **không nằm ở Tầng B** — thuộc quy trình mở khoá riêng ở §12c.3, đắt hơn: **+6 vào N**, không phải +1.

🔴 **`k` và `mult_dd` KHÔNG nằm trong nhóm này** — v6 chuyển cả hai sang **Tầng C / Cấp C**: không có cơ chế mở khoá +6, không có quy trình nào. Lý do ở §6.9.4.

```
🚪 QUY TRÌNH BẮT BUỘC mỗi lần chỉnh — không có đường tắt qua UI:
   1. Ghi trial_registry TRƯỚC khi đổi (§9c.2), có registered_at
   2. Ghi ngưỡng PASS bằng SỐ trước khi chạy lại (§9c.5)
   3. Trừ 1 trial khỏi ngân sách B3
   4. Nếu B3 = 0 → 🔴 KHÔNG ĐƯỢC ĐỔI. Phải mở giả thuyết mới ở
      NGÂN SÁCH A và chạy lại chu trình, gồm lockbox MỚI (DR-012)

🔴 UI PHẢI THỰC THI ĐIỀU NÀY, không chỉ hiển thị cảnh báo:
   • Ô nhập Tầng B KHOÁ CỨNG khi B3 = 0 — không phải popup "bạn có
     chắc không", mà là không nhập được
   • Bắt buộc điền lý do + ngưỡng PASS TRƯỚC khi nút Lưu bật lên
   • Mỗi lần lưu ghi một dòng trial_registry, tự động, không bỏ qua được

   Nếu UI cho phép sửa Tầng B mà không đi qua bốn bước trên, UI đó
   NGUY HIỂM HƠN việc không có UI. Thà sửa file YAML bằng tay.
```

### 6.9.4. TẦNG C — KHOÁ VĨNH VIỄN, không có ô nhập nào

```
❌ D0.1 – D0.5 (§3.4) — năm nguyên lý bất biến
❌ Ngưỡng đệm thanh lý = 8 (§6.4/§6.4b) — bảo vệ tính mạng tài khoản
❌ Sự TỒN TẠI của DG6 (§4.1), DG7 (§4c) và DG8 (§4b) — giá trị ngưỡng
   là Tầng B, nhưng bật/tắt chúng thì KHÔNG
❌ Điều kiện D của DG6 khi Short đang bật
❌ Số tranche = 3 (D0.4) — xem §3.4b để biết vì sao không nới được
❌ 🆕 v6 — `k` = 3 (§1.1)
   Lý do chuyển từ "đóng băng, mở khoá +6" sang Cấp C: `k` là ĐỊNH
   NGHĨA của swing, không phải một ngưỡng. Đổi `k` = đổi cái gì được
   COI LÀ zone = L2 (sai cấu trúc, §11b.1). Mà L2 theo DR-012 cần
   slot NGÂN SÁCH A + LOCKBOX MỚI — đắt hơn nhiều so với +6 trial.
   Để nó trong nhóm "mở khoá +6" là bán một thay đổi L2 với giá L1.
   ⚠️ v5 để `k_swing_confirm: 3` xuất hiện ở CẢ `tier_b` LẪN
      `tier_frozen` trong cùng một file YAML.
❌ 🆕 v6 — Thang drawdown 5% / 8% / 20% (`mult_dd`, §6.2 + §12c.5)
   Lý do: đây là một trong BA TẦNG CHẶN vòng lặp thua lỗ (§12b.2).
   v5 vừa đánh dấu nó [CẦN CALIBRATE] (tune được, tiêu trial) vừa
   xếp Cấp C (không bao giờ đổi). Không thể vừa là thứ được tối ưu
   trên backtest vừa là cầu dao. Cầu dao thắng.

🔴 Tầng C KHÔNG XUẤT HIỆN trong giao diện. Không phải "hiện dạng
   xám", không phải "cần mật khẩu" — KHÔNG CÓ Ô NHẬP. Một ô nhập
   bị khoá vẫn là lời mời tìm cách mở.
```

### 6.9.5. File cấu hình — chính nó là giao diện

```yaml
# tool_d_config.yaml — nguồn sự thật duy nhất, commit vào git
# 🔴 v6: ĐÂY là nguồn sự thật cho danh sách tham số. DR-010 KHÔNG lặp
#        lại danh sách — nó chỉ ghi LÝ DO. Danh sách xuất hiện ở hai
#        nơi chính là cơ chế đã gây ra toàn bộ đợt lệch số của v5.
# Sửa file này = tạo một commit = có dấu vết.

tier_a:                          # chỉnh tự do, 0 trial
  E_D:                    500          # USDT — KHÔNG phải số dư ví
  L_exchange:               3          # 2-5, xem §6.9.2 cảnh báo
  rho_pct:                  0.375      # chỉ đổi khi danh mục RỖNG
  daily_loss_budget_pct:    8.0
  enable_long:           true
  enable_short:          false         # chỉ bật khi DG7 (§4c) xong
  pool_size_target:       100

  _derived:                            # HỆ THỐNG TÍNH, không nhập tay
    max_open_positions:    null        # ← §6.8f, DAO ĐỘNG theo zone width
    margin_used_pct:       null        # ← Σ margin / E_D, trần 0.85
    risk_used_pct:         null        # ← Σ rủi ro / E_D, trần daily_loss
    l_total_d:             null        # ← Σ N_full / E_D, ĐO ĐƯỢC
  # ❌ L_D_max      — v6 XOÁ (≡ 0.85 × L_exchange, §6.8c)
  # ❌ max_open_D   — v4 XOÁ (là KẾT QUẢ của §6.8f, không phải tham số)

tier_b:                          # MỖI LẦN ĐỔI = 1 TRIAL từ B3.  12 mục
  _budget_remaining_B3:     20         # ← hệ thống giảm, không sửa tay
  zss_threshold:            0.5        #  1  §1.3
  buf_sl_atr:               0.4        #  2  §3.1
  wick_close_upper_frac:    0.5        #  3  §3.3b
  v_min:                  null         #  4  §3.3b   [CẦN CALIBRATE]
  funding_rate_pct:        -0.05       #  5  §3.3d + DG6-D (gộp)
  dg6d_retrace_frac:        0.5        #  6  §3.3d
  dg4_bars_1h:              8          #  7  §4
  dg6a_atr_ratio:           1.8        #  8  §4.1
  tp1_haircut_pct:         20          #  9  §5.1
  mult_corr_thresholds:  [0.60, 0.85]  # 10  §6.2 hệ số 3
  max_hold_bars_4h:        24          # 11  §4b.3
  dg7_funding_frac:         0.3        # 12  §4c   🆕 v6 — v5 chưa đếm
  # zone_width_min_atr:     0.5        # 13? — CHỜ VERIFY D0-PRE (§3.3)
  #                                    #   code chết → xoá, N=114
  #                                    #   không chết → bật lại, N=120

tier_frozen:                     # 🔒 MỞ KHOÁ = +6 vào N (§12c.3)
  _unfreeze_count:           0
  # 🔴 v6: `dof` = số BẬC TỰ DO khoá này loại bỏ khỏi kiểm kê gốc.
  #        KHÁC với số khoá. Đây chính là chỗ v5 đếm sai (khai "đóng
  #        băng 9 tham số" trong khi 2 trong số đó chưa từng được đếm).
  w_zss:            {value: [0.3333,0.3333,0.3334], dof: -2}  # §1.2
  w_tranche:        {value: [0.3333,0.3333,0.3334], dof:  0}  # §3.1 🆕
  adx_threshold:    {value: 20,    dof:  0}   # chưa từng có trong 26
  mult_regime:      {value: {strong: 1.0, weak: 0.7, adx_split: 25}, dof: -1}
  tp2_trail_atr:    {value: 1.5,   dof: -1}
  dg6b_bars_1h:     {value: 8,     dof: -1}   # = dg4_bars_1h
  trend_age_days:   {value: 5,     dof: -1, frozen_until: "Z0-T1_result"}
  mult_edge_thr:    {value: 0.5,   dof:  0}   # §6.2 hệ số 5 🆕
  mult_deploy_thr:  {value: 0.85,  dof:  0}   # §6.2 hệ số 6 🆕
  diag_thresholds:  {value: {time_stop_band: [0.05, 0.25],
                             tp_fallback_max_frac: 0.40,
                             tp_fallback_dist_r:   4.0,
                             tp_fallback_target_r: 1.5}, dof: 0}
  # Σ dof = -6.  Kiểm kê gốc 26 + DG7(1) + w_tranche(1) = 28
  #   28 - 6 (đóng băng) - 4 (pool → B0) - 2 (xoá §2.4, §3.3c)
  #   - 1 (mult_dd → Cấp C) - 1 (L_BASE → mult_regime đóng băng)
  #   - 1 (zone_width, có điều kiện)  =  12  ✅ khớp tier_b
  #   → xem DR-010 để đọc bảng đối chiếu đầy đủ

tier_c:                          # 🔒 KHOÁ — KHÔNG có ô nhập, ghi ở đây
  n_tranches:                3         # D0.4
  liq_buffer_min:            8         # §6.4b
  sl_immutable:           true         # D0.2
  dg6_enabled:            true         # bật/tắt: CẤM
  dg7_enabled:            true         # bật/tắt: CẤM   🆕 v6
  dg8_enabled:            true         # bật/tắt: CẤM
  k_swing_confirm:           3         # 🆕 v6 — CHUYỂN TỪ tier_b/frozen
  dd_ladder_pct:  {soft: 5, halt: 8, abort: 20}   # 🆕 v6 — §12c.5
  api_calls_per_min:        30         # 🆕 v7 — §6.6(3), LD-23. Điền
                                       #   theo nhịp thật: 100 mã / 60
                                       #   phút + lề. KHÔNG polling.
  entry_order_ttl_bars_1h:   3         # 🆕 v7 — §3.5, = §3.3b chờ
  corr_window_days:         30         # 🆕 v7 — §6.2 hệ số 3, định nghĩa
  # 🔴 v7: KHÔNG dùng *Parameter của Freqtrade cho BẤT KỲ khoá nào
  #        ở file này (§0d.2, L-Z37). Đọc YAML → dict → truyền vào hàm.
```

> 🔴 **v6 — Không còn đếm tay.** Test `L-Z29` (§9c.6) kiểm tự động: số khoá trong `tier_frozen` == số bản ghi có `frozen_rationale` trong registry, **và** `Σ dof(tier_frozen) + |tier_b| + các mục đã xoá == DOF_gốc` ghi ở D0-PRE. Lệch → chặn chạy. Đây là cách duy nhất để lỗi kiểm kê của v5 không tái diễn ở v7.

> 💡 **Đề xuất thứ tự triển khai:** file YAML trước, UI sau — và chỉ làm UI cho **Tầng A**. Tầng A là thứ bạn thật sự cần chỉnh thường xuyên (vốn, đòn bẩy, số lệnh song song, bật/tắt hướng). Tầng B chỉnh vài lần mỗi năm và mỗi lần đều cần đi kèm một quy trình đầy đủ — làm UI cho nó chỉ tạo ra ma sát thấp cho hành vi cần ma sát cao.

> ⚠️ **Một sự thật khó chịu, ghi lại một lần:** "cài đặt tùy chỉnh qua thời gian" nghe như tính năng tiện lợi, nhưng với hệ thống giao dịch nó là **kênh overfitting chậm** — mỗi lần chỉnh nhỏ đều hợp lý tại thời điểm đó, và sau một năm bạn có một hệ thống được fit vào chính chuỗi sự kiện đã xảy ra, không ai đếm được bao nhiêu phép thử đã tiêu. Phân tầng ở trên tồn tại để bạn vẫn chỉnh được cái cần chỉnh, mà cái nguy hiểm thì để lại dấu vết.

---

# PHẦN 7 — 🔴 LOOKAHEAD TRONG ZONE DETECTION (blocker B2, rủi ro riêng của Tool D)

Đây là mục quan trọng nhất về mặt kỹ thuật của toàn tài liệu. Tool A không có dạng lỗi này vì tín hiệu breakout của nó dùng dữ liệu tại-nến-hiện-tại. Zone/swing detection ở Tool D dùng dữ liệu **hai phía** (trước và sau điểm swing) theo chính định nghĩa toán học của nó.

> 🆕 **Đã tra cứu thực hành ngành để kiểm chứng hướng xử lý** — ba phát hiện quan trọng, trình bày ở §7.1–§7.3, dẫn tới thiết kế tối ưu hơn ở §7.4.

## 7.1. Vấn đề cụ thể — và xác nhận đây là bệnh chung, không phải lỗi chọn sai chỉ báo

```
Định nghĩa §1.1: nến i là swing nếu giá trị cao/thấp nhất trong [i−3, i+3]

Tại thời điểm nến i vừa đóng (real-time), hệ thống CHỈ CÓ dữ liệu đến i.
Không thể biết nến i có phải swing hay không cho tới khi nến i+3 đóng.
```

**Đã thử tìm phương án né hoàn toàn độ trễ này (VD: dùng Volume Profile POC/Value Area thay vì swing 2 phía) — kết quả: không có đường tắt.** Thực hành ngành xác nhận Volume Profile mắc đúng vấn đề tương tự: một vùng giá trị (Value Area) chỉ đáng tin **sau khi nhịp giá đã hoàn tất** — dùng nó trên một nhịp còn đang hình thành cho ra vùng còn trôi, không ổn định. Đây là thuộc tính toán học của khái niệm "vùng giá đã được thị trường xác nhận" nói chung — bất kỳ chỉ báo nào định nghĩa "điểm quan trọng trong quá khứ dựa trên phản ứng giá sau đó" đều mắc cùng vấn đề, không riêng swing 2 phía. Kết luận: **độ trễ xác nhận là chi phí không tránh được của chính ý tưởng "zone", không phải lỗi triển khai có thể sửa bằng cách đổi chỉ báo.**

```
❌ SAI (lookahead): backtest dùng zone ngay tại nến i, vì trong dữ liệu
   lịch sử, nến i+1..i+3 "đã tồn tại" và code vô tình đọc được
✅ ĐÚNG: zone chỉ được coi là "đã biết" (usable) từ nến i+3 trở đi —
   NHƯNG xem §7.4, "đã biết" không nhất thiết phải là ngưỡng nhị phân
```

## 7.2. Test bắt buộc — H4-D, có cập nhật quan trọng sau khi tra cứu

```
🔴 H4-D — Zone confirmation delay test    P0    NGÀY 1, TRƯỚC MỌI THỨ KHÁC

   Với mọi zone dùng trong backtest:
     assert zone.confirmed_at_bar_index - zone.swing_bar_index == 3
     assert mọi tranche fill có timestamp ≥ confirmed_at_bar (không phải swing_bar)
```

> 🔴 **v7 — DANH MỤC BA LỚP DƯƠNG TÍNH GIẢ ĐÃ BIẾT của `lookahead-analysis` (LD-15, Tool A truy tới gốc bằng mã nguồn Freqtrade):**
>
> | Lớp | Cơ chế | Có xảy ra ở backtest/live thật không |
> |---|---|---|
> | **FP-1** — issue #12168 | `custom_entry_price`/`adjust_entry_price` với khớp trễ hơn nến tín hiệu — **chính là tranche 2/3** | Không |
> | **FP-2** — artifact kích thước whitelist | Lần "full" nạp toàn bộ pair, lần "cut" chỉ 1 pair → chỉ báo đọc `dp.current_whitelist()` để tính trung bình toàn pool (ví dụ `corr_pool` §6.2) ra giá trị khác **về cấu trúc**, bị gắn cờ như rò rỉ | Không |
> | **FP-3** — nhạy cảm warm-up | `merge_informative_pair(ffill=True)` lấp biên đầu dataframe bằng giá trị cuối trước cửa sổ — chỉ dùng quá khứ, nhưng hai lần chạy với độ dài lịch sử khác nhau ra số khác nhau, khi `startup_candle_count` xấp xỉ mức nhỏ nhất công cụ thử | Không |
>
> **Quy tắc:** mỗi cờ lookahead PHẢI được **quy về một trong ba lớp trên (có bằng chứng) hoặc điều tra tới gốc**. Không được vừa bỏ qua vừa ghi "đạt". **Không sửa code sản xuất để chiều theo artifact của công cụ kiểm.** Cờ không quy được về lớp nào = lookahead THẬT cho tới khi chứng minh ngược lại.
>
> Chi tiết lớp FP-1 (ghi từ v5): lệnh `lookahead-analysis` gốc của Freqtrade có một issue đang mở trên GitHub (#12168, 8/2025): công cụ này **cho kết quả false positive** với chiến lược dùng `custom_entry_price`/`adjust_entry_price` khi lệnh khớp trễ hơn nến tín hiệu — **chính xác là cơ chế tranche của Tool D** (p2, p3 khớp trễ nhiều nến so với lúc zone được phát hiện). Nếu chạy công cụ này nguyên bản mà không biết trước, nhiều khả năng nó sẽ báo "biased" cho các lệnh tranche 2/3 hợp lệ.

```
Xử lý bắt buộc: KHÔNG dùng kết quả `lookahead-analysis` cho các cặp
entry-tranche một cách tự động. Cách làm đúng:
   1. Chạy `lookahead-analysis` như bình thường để bắt lỗi ở ZONE
      DETECTION (Phần 1) — đây vẫn là phần chính xác cần nó, vì lỗi
      lookahead thật sự nằm ở indicator, không nằm ở entry-logic
   2. Với riêng phần fill tranche 2/3 bị gắn cờ "biased": kiểm tra
      TAY từng ca — nếu timestamp fill ≥ confirmed_at_bar VÀ gate
      DG1-DG5 (§4) đều pass tại đúng thời điểm đó, đây là false
      positive đã biết, GHI LẠI lý do, không sửa code để "làm hài
      lòng" công cụ
   3. Theo dõi issue #12168 — nếu Freqtrade fix, chạy lại toàn bộ
      không cần bước 2 thủ công nữa
```

> **Vì sao đây là P0 tuyệt đối, đứng trước cả D0.9:** nếu lookahead tồn tại trong zone detection, **mọi kết quả Ablation D0.9** sẽ bị bơm lên một cách hệ thống — zone sẽ "trông" chính xác hơn thực tế vì backtest đang lén dùng tương lai để vẽ lại quá khứ. Chạy D0.9 trước khi gỡ B2 là lãng phí — kết quả không đáng tin dù có đẹp thế nào.

## 7.3. Hệ quả lên độ trễ tín hiệu thực chiến — vấn đề thật cần tối ưu

```
⚠️ Zone chỉ "sẵn sàng dùng" sớm nhất là 12h (3 nến 4H) sau khi hình
   thành. Thiết kế nhị phân (chưa đủ 3 nến = hoàn toàn không dùng
   được) LÃNG PHÍ thông tin: tại nến i+1, i+2, hệ thống ĐÃ CÓ bằng
   chứng một phần (giá chưa vượt qua i) nhưng bị buộc bỏ qua hoàn
   toàn cho tới đúng mốc i+3. Đây là chỗ tối ưu được — xem §7.4.
```

## 7.4. 🆕 Tối ưu hoá — độ tin cậy tăng dần, không phải ngưỡng nhị phân

**Vì sao không né được độ trễ (§7.1), nhưng có thể ngừng lãng phí nó trong lúc chờ.**

```python
confirm_ratio(i, t) = min(bars_elapsed(i, t), 3) / 3
   # bars_elapsed(i,t) = số nến 4H đã trôi qua kể từ i, TÍNH ĐẾN t hiện tại
   # — hoàn toàn nhân quả: tại mọi t, chỉ dùng dữ liệu ≤ t, không nhìn tương lai

   tại t = i:    confirm_ratio = 0     → CHƯA dùng được (giống thiết kế cũ)
   tại t = i+1:  confirm_ratio = 0.33  → dùng được, size giảm theo tỷ lệ
   tại t = i+2:  confirm_ratio = 0.67
   tại t = i+3:  confirm_ratio = 1.0   → đầy đủ (giống thiết kế cũ tại đây)

   Điều kiện HUỶ tại bất kỳ t nào trong lúc chờ:
      NẾU giá tại (i, t] tạo cực trị VƯỢT QUA i → zone này KHÔNG BAO GIỜ
      hợp lệ (không phải "chưa đủ tin cậy" — là "sai ngay từ đầu")

# Cắm thẳng vào mult_zss đã có (§6.2 hệ số 2), KHÔNG thêm cơ chế mới:
mult_zss_adjusted = mult_zss × confirm_ratio(i, t)
```

**Ba lý do đây là tối ưu thật, không phải thêm phức tạp không cần thiết:**

| Tiêu chí | Đáp ứng |
|---|---|
| Vẫn nhân quả 100%? | ✅ Tại mọi t chỉ dùng dữ liệu ≤ t — không mở lại B2 |
| Thêm bậc tự do? | ✅ **Không** — k=3 vẫn là tham số duy nhất, chỉ đổi cách dùng (liên tục thay vì nhị phân), không vi phạm cardinality budget |
| Tái dùng hạ tầng có sẵn? | ✅ Cắm thẳng vào `mult_zss`, không cần cơ chế/bảng riêng |

**Cái được:** hệ thống có thể vào tranche 1 sớm hơn 12h với size nhỏ hơn tương ứng — hợp lý kinh tế (tin ít hơn → cược ít hơn, không phải không cược gì). Đây là chỗ zone-scoring liên tục (đã thiết kế ở §6.3 cho ZSS) mở rộng tự nhiên sang cả trục thời gian xác nhận, không chỉ trục chất lượng zone.

**Cái giá phải trả, nói thẳng:** code phức tạp hơn thiết kế nhị phân — cần theo dõi trạng thái "ứng viên chưa xác nhận" theo thời gian thực cho mọi swing tiềm năng (không chỉ lọc một lần rồi xong), và test L-Z1 (§8.1) phải mở rộng kiểm tra `confirm_ratio` tính đúng tại mọi t, không chỉ kiểm tra nhị phân đủ/chưa đủ 3 nến.

## 7.5. Test bắt buộc bổ sung — H4-D mở rộng cho confirm_ratio

```
🔴 H4-D-b — Continuous confirmation causality test    P0

   Với MỌI cặp (i, t) trong dữ liệu backtest:
     assert confirm_ratio(i,t) được tính CHỈ từ dữ liệu ≤ t
     assert confirm_ratio(i,t) không đổi nếu dữ liệu SAU t thay đổi
            (test bằng cách cắt dữ liệu tại t, tính lại, so sánh —
             đây là cách "recursive-analysis" của Freqtrade kiểm tra
             tính ổn định công thức, áp dụng đúng tinh thần cho hàm mới)
```

---

# PHẦN 8 — DECISION LOG: KHỐI ZONE (thay Khối D của v1)

```jsonc
"block_zone_plan": {
  "plan_id":              "uuid",
  "zone_id":               "uuid",
  "zone_swing_bar":        "…",
  "zone_confirmed_at_bar": "…",
  "zone_low":              41850.0,
  "zone_high":             42300.0,
  "zss_at_entry":          0.62,
  "zss_components":        {"touch": 1, "volume_ratio": 1.3, "compression": 0.85},
  "entry_confirmation":    {"type": "rejection_wick", "wait_bars": 1},  // 🆕 §3.3b
                           // hoặc {"type": "rsi_divergence", "wait_bars": 2}
  "trend_dir_1d":          "UP",                 // 🆕 tách riêng theo khung
  "trend_dir_4h":          "UP",                 // 🆕 phải == 1D (§2.2)
  "trend_age_days":        7.5,                  // 🆕 phải ≥ 5 (§2.3)
  "trend_strength_at_entry": 24.1,
  "planned_notional":      0.417,
  "risk_budget_pct":       0.375,
  "rho_eff":               "…",        // sau khi nhân 6 hệ số mult_* (§6.2 v6)
  "planned_risk_usdt":     "…",        // 🆕 v4 — BẮT BUỘC cho L-Z20
  "planned_margin_usdt":   "…",        // 🆕 v4 — BẮT BUỘC cho L-Z22
  "l_exchange_at_entry":   3,          // 🆕 v4 — không hardcode 5 nữa
  "portfolio_risk_used_pct":   "…",    // 🆕 v4 — trạng thái lúc kết nạp
  "portfolio_margin_used_pct": "…",    // 🆕 v4
  "tranche_prices":        [42300.0, 42075.0, 41850.0],
  "tranche_weights":       [0.3333, 0.3333, 0.3334],   // 🔒 §3.1
  "sl_price":              41707.7,
  "sl_price_immutable_hash": "sha256…",
  "sl_equals_zone_invalidation": true,
  "tp1_source":            "zone_opposite",
  "liq_buffer_ratio":      12.86,      // ⚠️ VÍ DỤ CHƯA TRUY ĐƯỢC — tính lại theo §6.4b
  "liq_dist_pct":          "…",        // 🆕 v6/§6.4b — TỬ số, bắt buộc
  "r_eff_pct":             "…",        // 🆕 v6/§6.4b — MẪU số, bắt buộc
  "l_total_d_at_entry":    "…",
  "mult_breakdown": {"regime":"…","zss":"…","corr":"…","dd":"…","edge":"…","deploy":"…"}
},

"block_zone_fills": [
  {"tranche": 2, "ts": "…", "filled": true,
   "gates": {"DG1": true, "DG2": true, "DG3": true, "DG4": true,
             "DG5": true, "zss_recheck": 0.58}},
  {"tranche": 3, "ts": "…", "filled": false,
   "gates": {"DG5": false}, "zss_recheck": 0.38,
   "cancel_tag": "ZONE_QUALITY_DECAYED"}
],

"block_dg6_checks": [  // 🆕 §4.1 — ghi lại MỌI lần kiểm tra DG6, không chỉ lúc trigger
  {"ts": "…", "atr_ratio": 1.2, "price_decay_ratio": 0.3,
   "trend_still_valid": true, "triggered": false},
  {"ts": "…", "atr_ratio": 1.9, "price_decay_ratio": 0.55,
   "trend_still_valid": true, "triggered": true,
   "condition": "A", "exit_tag": "EARLY_EXIT_A",
   "exit_price": "…", "loss_avoided_est_vs_sl": "…"}  // ước tính lỗ tránh
                                                        // được nếu về sau chạm SL
]
```

## 8.1. Test bắt buộc — bổ sung so với v1

```
L-Z1  Mọi zone dùng trong backtest có confirmed_at_bar ≥ swing_bar + 3   🔴 CRITICAL
L-Z2  sl_equals_zone_invalidation luôn true — không có bản ghi nào false
L-Z3  liq_buffer_ratio ≥ 8 ở MỌI bản ghi tranche 1 đã khớp
L-Z4  Replay: touch_count tại thời điểm entry khớp với dữ liệu point-in-time
L-Z5  (kế thừa L-D1 đến L-D5 của v1, đổi field name)
L-Z6  🆕 Mọi tranche 1 đã khớp đều có entry_confirmation không rỗng (§3.3b)
L-Z7  🆕 Mọi lệnh EARLY_EXIT có ≥1 bản ghi block_dg6_checks với triggered=true
      NGAY TRƯỚC thời điểm đóng lệnh — không có EARLY_EXIT "vô cớ"
L-Z8  🆕 trend_dir_1d == trend_dir_4h tại MỌI bản ghi plan (§2.2)
```

---

## 8.2. 🆕 Bổ sung Decision Log — DG8 & hold duration

Thêm vào `block_zone_plan`:

```jsonc
"max_hold_bars":        24,          // 🆕 giá trị hiệu lực tại thời điểm plan
"tranche1_filled_at_bar": "…",       // 🆕 mốc đếm của DG8 (§4b.2)
```

Thêm khối mới, song song với `block_dg6_checks`:

```jsonc
"block_dg8": {                        // 🆕 v3.2
  "bars_since_tranche1_at_close": 24,
  "hold_duration_bars":           24,  // 🔴 BẮT BUỘC ở MỌI lệnh đã đóng,
                                       //    kể cả đóng bằng TP/SL (L-Z19)
  "closed_by_time_stop":          true,
  "exit_tag":                     "TIME_STOP",
  "pnl_at_time_stop":             "…",  // để đo đánh đổi của DG8
  "funding_paid_cumulative":      "…"   // liên kết DG7 — đo chi phí thời gian
}
```

> **Vì sao `hold_duration_bars` bắt buộc ở MỌI lệnh, không chỉ lệnh TIME_STOP:** không có phân bố đầy đủ thì không dựng được histogram hold, và tiêu chí "5%–25% TIME_STOP" ở §10.2 không kiểm được. Ghi chỉ ở lệnh bị cắt = mẫu chọn lọc, vô dụng cho chẩn đoán.

---

---

## 8.3. 🆕 v7 — Sổ nhật ký: khoá chống trùng, append-only, bản ghi lệnh thật (LD-17, LD-19, LD-20, LD-21)

```
🔴 LD-19 — Tool A đo được ~7–9 bản ghi cho 1 sự kiện thật, vì mỗi lần
   chạy lại backtest (và mỗi epoch hyperopt) ghi thêm một bộ bản ghi
   gần giống hệt vào file cũ (đặt tên theo mốc thời gian LỊCH SỬ,
   không theo giờ chạy). Không ảnh hưởng giao dịch, nhưng PHÁ HUỶ mọi
   phân tích dựa trên đếm — gồm chính đầu vào của GATE (H-1/H-3/H-4
   đều là TỈ LỆ).

════ DEDUP_KEY TẤT ĐỊNH — định nghĩa "1 sự kiện thật" trong DCA ════
   Mỗi TRANCHE là một sự kiện vào lệnh riêng → khoá theo order_id
   của TỪNG tranche, KHÔNG theo trade_id.
      bản ghi vào/ra lệnh   : dedup_key = f"{exchange_order_id}"
      bản ghi đổi SL        : dedup_key = f"{sl_order_id_new}"
      bản ghi đánh giá/plan : dedup_key = f"{pair}:{candle_ts}:{block}"
      bản ghi DG6/DG7 check : dedup_key = f"{trade_id}:{candle_ts}:{gate}"
   Ghi = NO-OP nếu key đã tồn tại. KHÔNG đọc-sửa-ghi-đè.
   → L-Z45: chạy hai lần liên tiếp cùng timerange ghi thêm ĐÚNG 0
     dòng, kể cả khi có tiến trình song song ghi cùng file.

════ APPEND-ONLY TUYỆT ĐỐI (LD-20) ════
   Bản ghi cũ KHÔNG BAO GIỜ sửa/xoá, kể cả khi biết là sai — ghi bản
   ghi MỚI với `corrects: <dedup_key cũ>`. Đây là điều kiện tiên
   quyết cho kiểm tra tái lập, và cùng quy tắc với trial_registry
   (§9c.2) và idea_queue. Tool A giữ nguyên ~402 dòng trùng cũ sau
   khi sửa lỗi, không dọn.

════ BẢN GHI ENTRY CHỈ HỢP LỆ KHI SL ĐÃ XÁC NHẬN TRÊN SÀN (LD-21) ════
   Validator TỪ CHỐI CỨNG bản ghi ENTRY (tranche 1) có
   `sl_on_exchange_confirmed != true` — không thể "làm giả" một lệnh
   an toàn trong sổ.

   🔴 v7 SỬA LD-21 CHO ĐÚNG THIẾT KẾ TOOL D: LD-21 viết "với DCA, SL
      được DỜI sau mỗi tranche". SAI với Tool D — D0.2 quy định GIÁ
      SL không bao giờ đổi. Thứ đổi sau mỗi tranche là KHỐI LƯỢNG của
      lệnh STOP_MARKET (reduce-only phải phủ vị thế đã lớn lên).
      → Mở rộng đúng: MỖI LẦN KHỐI LƯỢNG SL ĐỔI = MỘT BẢN GHI
        {ts, trade_id, tranche, sl_price (phải == plan, L-Z2),
         sl_qty_old, sl_qty_new, sl_order_id_old, sl_order_id_new,
         gap_ms (thời gian không có SL trên sàn — §9b D2)}
        và "SL hiện hành trên sàn" phải truy được từ sổ mà không cần
        tính lại.

════ DANH SÁCH ĐÓNG — GIÁ TRỊ ĐÓNG BĂNG LÚC ENTRY (LD-17) ════
   Lưu qua trade.set_custom_data() tại tranche 1, đọc lại qua
   /trades/{id}/custom-data. Tầng đo và dashboard ĐỌC, KHÔNG TÍNH LẠI
   (LD-09):
      zone_id, zone_low, zone_high, zone_confirmed_at_bar,
      zss_at_entry, zss_components, confirm_ratio_at_entry,
      p1_order, p2, p3, p_avg_plan, sl_price, R_eff_plan,
      planned_risk_usdt, planned_margin_usdt, N_full,
      rho_eff, mult_breakdown, tranche1_filled_at_bar,
      max_hold_bars, l_exchange_at_entry, tp1_price, tp1_source,
      liq_price_plan, liq_dist_pct, r_eff_pct, liq_buffer_ratio
   ⚠️ Assumption D7 (§9b): custom_data có SỐNG qua các callback trong
      backtest không — Tool A ghi nhận nghi vấn. Phải test TRƯỚC khi
      tin bất kỳ kết quả DCA nào.
```

## 📋 DR-013 — 🆕 v7: ĐƠN VỊ ĐO — `pnl_abs` và R (LD-07, LD-08)

```
BỐI CẢNH
   Tool A cộng dồn `profit_ratio` của 871 lệnh ra −1464% — con số
   không thể tồn tại. `profit_ratio` là lợi nhuận theo MẪU SỐ RIÊNG
   của từng lệnh (stake khác nhau). Với DCA, stake của MỘT trade đổi
   giữa chừng theo số tranche khớp → profit_ratio còn khó diễn giải
   hơn. Tool A cũng dùng `initial_stop_loss_abs` làm mẫu số R — sai,
   vì Freqtrade gán trường đó = stoploss TĨNH lúc mở, TRƯỚC khi
   custom_stoploss siết → mẫu số rộng gấp ~1,85 lần, sai toàn bộ chỉ
   số dẫn xuất KỂ CẢ số đã ghi vào sổ trial.

QUYẾT ĐỊNH
   (1) MỌI chỉ số tổng hợp (expectancy, Sharpe, DSR, CVaR, đường vốn)
       tính trên `pnl_abs` (USDT, đã trừ phí + funding).
       KHÔNG BAO GIỜ trên `profit_ratio`. Kiểm:
          starting_balance + Σ pnl_abs == final_balance  (từng fold)
       Ghép fold thành đường vốn liên tục bằng NHÂN hệ số, không cộng
       (mỗi fold backtest độc lập, tự reset vốn).

   (2) R_realized = pnl_abs / planned_risk_usdt
       planned_risk_usdt = rho_eff × E_D, ĐÓNG BĂNG tại tranche 1
       (đã có trong block_zone_plan, bắt buộc cho L-Z20).
       → Trả lời câu hỏi mở của LD-08 ("R theo giá vào tranche 1 hay
         giá vào trung bình?"): KHÔNG theo cái nào. Mẫu số là NGÂN
         SÁCH RỦI RO KẾ HOẠCH — vì D0.1 định nghĩa rủi ro mỗi lệnh
         chính là con số đó, và nó là thứ DUY NHẤT bất biến suốt vòng
         đời một trade nhiều tranche.
       Hệ quả đúng và có ý nghĩa: trade chỉ khớp tranche 1 rồi chạm SL
       có |R_realized| ≈ w[0] × (p1−sl)/(p_avg_plan−sl) < 1. Đó là
       thông tin thật ("DCA chưa kịp phát huy"), không phải lỗi.

   (3) Tầng đo NHẬN mẫu số qua tham số bắt buộc (đọc từ custom_data /
       Decision Log). Thiếu bản ghi → RAISE. KHÔNG lùi về hằng số
       trong code (hằng số có thể đã đổi — chia lại bằng hằng số cũ
       ra số sai ÂM THẦM).

   (4) Sharpe/DSR mỗi lệnh tính trên chuỗi R_realized, KHÔNG trên
       pnl_abs/E_D (E_D đổi khi nạp/rút vốn) và KHÔNG trên
       profit_ratio (mẫu số trôi theo tranche).

🔴 v8 — TU CHÍNH (nhập DR nháp "mẫu số R đa-tranche", có sửa)
   Bản nháp đề xuất R = Σ rủi ro toàn thang kế hoạch tới SL vùng —
   TRIẾT LÝ TRÙNG với quyết định (2) ở trên (cả hai đều là "ngân sách
   rủi ro kế hoạch, đóng băng lúc tranche 1, biết trước diễn biến").
   KHÔNG lập DR mới — hai DR cùng định nghĩa một chữ R là đúng lỗi
   "số ở hai nơi" đã phá v5. Tu chính tại đây, ba điểm:

   (2b) NGUỒN SỰ THẬT CỦA planned_risk_usdt — chốt phía nào khi hai
        cách tính lệch nhau vì làm tròn:
           planned_risk_usdt := Σ ( qty_i_kế_hoạch ×
                                    |p_i_kế_hoạch − sl_price| )
                                trên THANG ĐẦY ĐỦ theo thiết kế lệnh
        với qty_i SAU khi làm tròn lot-size / min-notional (đúng khối
        lượng sẽ gửi lên sàn), và p1 = p1_order THẬT của §3.5, không
        phải zone_high danh nghĩa.
        → rho_eff × E_D là NGÂN SÁCH; tổng thang là KẾ HOẠCH THI HÀNH.
          Khi lệch (lot thô, E_D nhỏ, zone hẹp), thứ có thể thật sự
          mất là KẾ HOẠCH — nên nó là mẫu số của R_realized.
        → KHẲNG ĐỊNH LÚC ENTRY: |tổng thang − rho_eff × E_D| ≤ 1% ×
          rho_eff × E_D — chính là L-Z20 sẵn có, giờ có chiều thi
          hành rõ: VI PHẠM → TỪ CHỐI VÀO LỆNH (zone quá hẹp / lot quá
          thô cho E_D hiện tại — nối vào kiểm min-notional ở D0-PRE),
          không phải ghi cảnh báo rồi vào.
        → ✅ Chốt luôn câu hỏi mở #27: N_full tính lại theo p1_order
          thật. D0.1 là nguyên lý; "đơn giản" không phải.

   (2c) TÍNH CHẤT PHẢI GIỮ (kiểm bằng test, không bằng lời):
        • Chạm SL sau khi khớp đủ thang = −1,00R trước phí; SAU phí +
          funding + trượt stop-market phải nằm trong [−1.15R, −1.00R)
          — trần 1.15 chính là `max_single_trade_loss / risk_budget
          ≤ 1.15` của §10.2/DR-011, hai con số này từ nay là MỘT.
        • Z0 chạm SL = cùng hàm tính, không nhánh code riêng —
          công thức thoái hoá tự nhiên khi thang chỉ có 1 tranche.
        • SL dời (hoà vốn v.v.) → R KHÔNG đổi. Thiếu bản ghi → raise
          (đã có ở (3)).
        • Trần thang = 3 tranche (D0.4) là điều kiện tồn tại của R —
          đã thoả từ thiết kế, ghi để thấy sự phụ thuộc.
        • Lưu THÀNH PHẦN THÔ tại tranche 1 (đã có ở §8.3: sl_price,
          p1_order/p2/p3, qty từng tranche) ⇒ mẫu số kiểu-A (riêng
          tranche 1) và kiểu-D (phần đã khớp) TÍNH LẠI ĐƯỢC bất cứ
          lúc nào làm số CHẨN ĐOÁN — nhưng CHỈ định nghĩa này nuôi
          gate/DSR, số khác phải mang tên khác.

   (2d) BẢNG TÊN GỌI — ba chữ "R" là ba đại lượng, cấm chữ "R" trần:
        ┌────────────────────┬─────────────────┬───────────────────┐
        │ Tên                │ Đơn vị          │ Là gì             │
        ├────────────────────┼─────────────────┼───────────────────┤
        │ R_eff / r_eff_pct  │ khoảng GIÁ (%)  │ p_avg_plan → SL,  │
        │                    │                 │ nuôi TP_fallback, │
        │                    │                 │ DG7, liq_buffer   │
        │ planned_risk_usdt  │ USDT            │ mẫu số duy nhất   │
        │                    │                 │ của R_realized    │
        │ R_realized         │ bội số (không   │ pnl_abs /         │
        │                    │ thứ nguyên)     │ planned_risk_usdt │
        └────────────────────┴─────────────────┴───────────────────┘
        Vì khối lượng tăng theo tranche mà planned_risk_usdt không
        đổi, khoảng GIÁ ứng với +1R co lại khi thang khớp thêm — nên
        MỤC TIÊU THOÁT phải neo giá/zone (§5.1 đã đúng), và mốc
        fallback phải gọi tường minh là "bội số R_eff" (khoảng giá),
        không bao giờ là "R" trần. Grep: L-Z48c.

TEST
   L-Z46 🔴 CRITICAL — grep tầng đo: KHÔNG có `profit_ratio` trong
         bất kỳ phép cộng/trung bình nào. KHÔNG có
         `initial_stop_loss_abs`.
   L-Z47 — Σ pnl_abs khớp final_balance từng fold, sai số < 0.01 USDT.
   L-Z48 — mọi R_realized có planned_risk_usdt > 0 từ bản ghi; lệnh
         thiếu bản ghi → tầng đo raise, không có giá trị mặc định.
   L-Z48b 🆕 v8 — mô phỏng khớp đủ thang rồi chạm SL vùng: R_realized
         ∈ [−1.15, −1.00); mô phỏng Z0 chạm SL: cùng dải, CÙNG một
         hàm tính (kiểm bằng call-graph, không bằng đọc code). Dời SL
         sau entry → planned_risk_usdt bất biến. Đổi số tranche trong
         thang thử nghiệm → planned_risk_usdt đổi tương ứng (chống
         mẫu-số-trang-trí, LD-30).
   L-Z48c 🆕 v8 — grep code + Decision Log: không có định danh/nhãn
         "R" trần; chỉ {R_eff, r_eff_pct, planned_risk_usdt,
         R_realized} và các dẫn xuất có tên đầy đủ.
```

---

# PHẦN 9 — DSR & TRẠNG THÁI DR-007

> 🆕 **Cập nhật — sửa lỗi lập luận ở bản trước.** Bản trước đề xuất chọn pool theo rank để CHỦ ĐỘNG né overlap — đây là sai hướng (xem §0.3). Phần này viết lại cho đúng: overlap là con số ĐO ĐƯỢC sau khi chọn pool theo chiến lược, không phải mục tiêu thiết kế.

## 9.0. DR-007 không lỗi thời — áp dụng dựa trên overlap ĐO ĐƯỢC, không phải overlap MONG MUỐN

```
DR-007 (v1): DSR phải gộp union trials NẾU dữ liệu overlap > 50%.
             Đây là quy tắc CÓ ĐIỀU KIỆN — hàm của overlap THẬT,
             không phải điều kiện được thiết kế để đạt hay né.

Quy trình đúng:
   1. Chọn pool Tool D theo tiêu chí chiến lược (§0.3) — KHÔNG nhìn Tool A
   2. Đo overlap thật với pool Tool A
   3. Áp DR-007 MÁY MÓC theo con số đo được — không có bước "chọn lại
      pool nếu overlap không như ý"
```

## 9.1. Kịch bản nhiều khả năng nhất — nói thẳng để không bất ngờ

```
⚠️ Dự kiến thực tế (chưa đo, chỉ là suy luận có cơ sở):
   ZSS (§1.2) dùng volume_ratio — cần volume đủ lớn để tín hiệu
   không nhiễu. Đây gần như CHẮC CHẮN kéo Tool D về nhóm coin
   thanh khoản cao — TRÙNG PHẦN LỚN với Tier 1 mà Tool A đã dùng,
   không phải vì thiết kế bắt chước, mà vì thanh khoản tốt là NGUỒN
   TÀI NGUYÊN HỮU HẠN của thị trường, cả hai chiến lược cùng cần.

   → Nhiều khả năng overlap SẼ CAO (có thể >50%), và DR-007 áp dụng.
   → Đây KHÔNG PHẢI thất bại của "độc lập hoá" — độc lập ở thiết kế/
     code/vốn vẫn giữ nguyên. Chỉ là DSR (thống kê) không tách được,
     và đó là sự thật về dữ liệu, không sửa được bằng cách viết lại code.
```

## 9.2. GATE — chạy đo, chấp nhận kết quả

```
🚪 H14 (Phần 11) đo overlap thật SAU KHI pool Tool D được chọn xong
   theo §0.3. Kết quả:
      < 50%  → DSR tách, mỗi tool tự đếm trial
      ≥ 50%  → DR-007 áp dụng, union trials — CHẤP NHẬN, ghi vào
                research-log, không quay lại đổi tiêu chí pool để né
   Đo lại mỗi lần rà soát pool hàng tháng — overlap có thể trôi
   theo thời gian dù tiêu chí chọn không đổi.
```

## 9.3. Cái vẫn KHÔNG tách được dù overlap thấp

```
🔴 v6 — `mult_cross` ĐÃ BỊ XOÁ (§6.2). Đoạn này của v5 là một trong
   BA mô tả mâu thuẫn nhau về cùng một hệ số, và là mô tả CHẶT NHẤT
   ("P0") trong khi §6.2 gọi nó là "tuỳ chọn".

   Rủi ro SẬP ĐỒNG PHA vẫn có thật — nhưng nó KHÔNG mất đi khi xoá
   hệ số này, vì nó đã được xử ở chỗ khác và mạnh hơn:
      §6.8d — định cỡ danh mục với GIẢ ĐỊNH TƯƠNG QUAN = 1
              (giả định trường hợp xấu nhất, chặt hơn một hệ số 0.5)
      §6.5b — isolated margin + sub-account riêng: thanh lý của tool
              này không chạm được vốn tool kia
   Một hệ số cắt size vì "Tool A đang có tín hiệu tương quan" chỉ có
   nghĩa khi tồn tại TRẦN GỘP giữa hai tool — mà trần gộp đã bị bỏ ở
   §6.5 theo đúng quyết định vận hành.

⚠️ research-log.md và ngân sách 5 giả thuyết/quý (§14D v10):
   VẪN NÊN dùng chung — rủi ro "nhiễm chéo qua chính bạn" (§11.1 v10)
   là rủi ro CON NGƯỜI, không phải dữ liệu. Không phụ thuộc overlap.
```

## 9.4. Sub-account (§6.5b) — không đổi, độc lập với kết quả overlap

Sub-account tách VỐN, không liên quan gì tới overlap dữ liệu (§9.1-9.2). Giữ nguyên bất kể DSR cuối cùng tách được hay không.

## 9.5. Ghi chú calibrate — kế thừa nguyên

```
🆕 Vì Zone Detection (Phần 1) và Trend Filter (Phần 2) là CHỈ BÁO MỚI,
   riêng của Tool D — bản thân việc HIỆU CHỈNH các ngưỡng [CẦN CALIBRATE]
   trong tài liệu này (ZSS threshold, ADX threshold, buf_sl, DG4,
   tiêu chí pool (i)-(iv) ở §0.3...) LÀ MỘT LẦN THỬ, phải ghi vào
   trial_registry TRƯỚC khi chạm dữ liệu thật.
```

---

# PHẦN 9b — 🔴 v3: GIẢ ĐỊNH CẦN VERIFY (D1-D5) + TESTNET — khôi phục sau khi phát hiện bị rớt mất

> **Lỗi tài liệu tự phát hiện:** roadmap (Phần 12) vẫn ghi "Verify D1-D5" ở bước D2, nhưng nội dung D1-D5 chưa từng được viết lại khi tài liệu chuyển sang thiết kế độc lập (chỉ còn tồn tại ở bản v1 cũ, tham chiếu tới cấu trúc Tool A không còn phù hợp). Viết lại đầy đủ, độc lập, dưới đây.

## 9b.1. Ba giai đoạn khác nhau — không được coi Dry-run thay thế Testnet

```
Backtest  → dữ liệu lịch sử, KHÔNG gọi API Binance
Dry-run   → giá THẬT (đọc public), khớp lệnh Freqtrade TỰ MÔ PHỎNG
             CỤC BỘ — KHÔNG gọi API đặt/sửa lệnh thật lên Binance
Testnet   → gọi API THẬT lên hệ thống khớp lệnh Binance (tiền giả)
             — nơi DUY NHẤT kiểm chứng hành vi sàn thật
Live      → tiền thật
```

**Hệ quả:** một giả định về **hành vi của Binance** (không phải giả định về logic Freqtrade) sẽ **không bao giờ bị bắt lỗi** ở backtest lẫn dry-run — cả hai đều không thực sự chạm vào API đặt/sửa lệnh của sàn. Chỉ testnet hoặc live mới lộ ra.

## 9b.2. Danh sách giả định D1-D5 — viết lại độc lập

| # | Giả định | Loại | Giai đoạn DUY NHẤT verify được | Nếu SAI thì sao |
|---|---|---|---|---|
| **D1** | `adjust_trade_position()` (Freqtrade) mô phỏng đúng fill limit maker trong BACKTEST futures, kể cả ca không khớp | Logic Freqtrade | Backtest (đọc source code + test đơn vị) | Toàn bộ kết quả D0.9 (Ablation) vô nghĩa |
| **🔴 D2** — 🔴 v7 VIẾT LẠI (LD-16) | **Khoảng trống không-SL khi khối lượng SL đổi sau mỗi tranche nằm trong giới hạn chấp nhận được.** Tách ba mệnh đề: **D2a** Freqtrade HUỶ + ĐẶT LẠI `STOP_MARKET` mỗi khi giá trị/khối lượng SL đổi — *đã xác nhận ở Tool A bằng mã nguồn*, không cần verify lại, chỉ cần đọc `git show` của phiên bản Freqtrade đang cài (LD-38/40). **D2b** Freqtrade có hỗ trợ `closePosition=true` cho stop order Binance Futures không — nếu có, khối lượng KHÔNG cần đổi khi tranche khớp và khoảng trống biến mất *(đọc mã nguồn trước, testnet sau)*. **D2c** Nếu D2b = không: `gap_ms` thực tế (§8.3) có p99 dưới ngưỡng chấp nhận không | D2a: logic Freqtrade · D2b: mã nguồn + sàn · D2c: hành vi sàn | D2a: đọc source · D2b: source + Testnet · **D2c: CHỈ Testnet/Live** | 🔴 **v6 nói quá:** D0.2 KHÔNG bị vi phạm — giá SL không đổi, chỉ khối lượng đổi. Rủi ro thật là **khoảng trống**, và với DCA tần suất thao tác này cao hơn Tool A nhiều (mỗi tranche = một lần). Nếu D2c fail: hạ `L_exchange` (gap ở đòn bẩy thấp ít nguy hiểm hơn) hoặc ghi rủi ro tồn dư vào DR — KHÔNG thiết kế lại §6 |
| **D3** | Freqtrade tính đúng giá vào trung bình khi nhiều lần entry, `custom_stoploss` đọc được nó | Logic Freqtrade | Backtest + đọc source | Phải tự tính/quản lý giá trung bình, thêm code |
| **D4** | Có thể reserve margin cho notional CHƯA triển khai (hoặc mô phỏng bằng cách hạ `max_open`) | Hành vi sàn + cấu hình | Testnet/Live (Binance có thực sự cho reserve margin trước không, hay chỉ tính theo notional đã khớp) | D0.3 không thực thi được, phải thiết kế lại §6 |
| **D5** | `timeframe-detail 5m` mô phỏng đúng thứ tự khớp trong cùng nến 1H khi nhiều mức giá (p1,p2,p3,SL,TP) cùng nằm trong một nến | Logic Freqtrade (backtest fidelity) | Backtest | Backtest thiên vị có lợi một cách hệ thống, đặc biệt nghiêm trọng với Tool D (5 mức giá/nến so với 2 của Tool A) |
| **🔴 D6** 🆕 v7 (LD-11) | **`adjust_trade_position()` trong backtest được đánh giá THEO NẾN, tại giá MỞ nến** — không theo dòng giá thật trong nến. Tool A phải ghi giới hạn này vào docstring. Với Tool D, TOÀN BỘ tranche 2/3 chạy qua hàm này → mọi số backtest DCA mang giả định "tranche khớp tại giá mở nến", trong khi thực tế là lệnh chờ trong vùng | Backtest fidelity | Backtest (đọc source, đo mức lệch với `timeframe_detail`) + **Testnet (D10): so sánh giá khớp tranche THẬT với giá backtest giả định, cùng khoảng thời gian** | Lệch một chiều CÓ LỢI cho mọi arm DCA so với Z0 (Z0 chỉ khớp một lần). Nhánh 2 §10.2 phải đọc lại. **Đây là rủi ro số một của toàn bộ kết quả Tool D** |
| **D7** 🆕 v7 (LD-17) | `trade.custom_data` GIỮ ỔN ĐỊNH giữa các lần gọi callback trong backtest (Tool A ghi nhận nghi vấn KHÔNG ổn định, chưa xác định nguyên nhân). Trạng thái tranche + danh sách đóng băng §8.3 sống trên cơ chế này suốt vòng đời lệnh | Logic Freqtrade | Backtest (test đơn vị dựng backtest nhỏ, kiểm trạng thái tranche không mất giữa callback) | Cơ chế DCA sai ÂM THẦM: tranche 2 không biết tranche 1 đã khớp ở giá nào → plan sai, SL sai. **Phải PASS trước khi tin bất kỳ kết quả DCA nào** |

> 🔴 **v7 xếp lại thứ tự nguy hiểm:** **D6** là giả định nguy hiểm nhất về **tính hợp lệ của kết quả** (chạm mọi con số backtest DCA, và lệch một chiều); **D2c** là giả định nguy hiểm nhất về **an toàn vận hành** (khoảng trống không SL đúng lúc rủi ro cao nhất). v6 gọi D2 là "nguy hiểm nhất" vì tin rằng nó phá D0.2 — không đúng: D0.2 nói về **giá** SL, D2 nói về **khối lượng**. Hai thứ này có thể cùng đúng.

## 9b.3. 🆕 Testnet — chèn tường minh vào pipeline, không nhảy thẳng backtest → dry-run

```
🚪 GATE MỚI, chặn giữa D9 (Walk-forward + GATE) và D10 (Dry-run cũ,
   đổi thành D11):

   D2 (giả định) PHẢI được verify qua MỘT trong hai cách, theo thứ
   tự ưu tiên:

   (a) Testnet — ưu tiên, 0 rủi ro tài chính:
       Set sandbox/testnet URL trong config Freqtrade, tạo tranche
       giả trên testnet, thử sửa khối lượng lệnh SL, quan sát Binance
       trả về gì. Đã có bằng chứng trái chiều về việc Freqtrade có
       hỗ trợ hay không (§6.7) — đây chính là bước thử THẬT, không
       suy đoán tiếp.

   (b) Live tối thiểu — CHỈ khi (a) xác nhận không khả thi:
       Một lệnh THẬT ở notional tối thiểu sàn cho phép (~5-20 USDT),
       tại sub-account Tool D, đúng quy trình tranche+SL của thiết
       kế, chỉ để verify hành vi sửa lệnh SL — KHÔNG phải để kiểm
       tra chiến lược. Rủi ro tài chính thật nhưng tối thiểu, có ý
       thức, ghi rõ mục đích trong research-log — khác hẳn "dry-run
       thay cho testnet" (không verify được gì) hay "bỏ qua bước
       này" (mù thông tin tới tận live thật).

   KHÔNG được vào D11 (Dry-run) nếu D2 chưa verify bằng (a) hoặc (b).

🔴 v7 — D10 PHẢI ĐO THÊM BA THỨ (không phải chỉ D2):

   (1) D6 — LỆCH KHỚP TRANCHE (LD-11): chạy cùng cấu hình trên testnet
       và backtest cùng khoảng thời gian; với MỖI tranche đã khớp ghi
       (giá khớp thật, giá backtest giả định, chênh bps). Báo cáo phân
       bố chênh, tách tranche 1/2/3, tách Long/Short.
       Ngưỡng chấp nhận: PLACEHOLDER FAIL-CLOSED (LD-31) — điền bằng
       DR trước khi chạy D10, KHÔNG sau khi thấy số.

   (2) D2b/D2c — closePosition=true có dùng được không; nếu không,
       phân bố gap_ms (§8.3) qua ≥ 30 lần đổi khối lượng SL.

   (3) TỶ LỆ KHỚP lệnh post-only tại zone (LD-12): tranche 1/2/3 đặt
       bao nhiêu, khớp bao nhiêu, NO_FILL bao nhiêu. Số này chưa từng
       có ở backtest.

   Ba số này ghi vào research-log KÈM provenance (§0d.5).
   🔴 v8: (1) và (3) có PHIÊN BẢN TỐI THIỂU chạy TRƯỚC ablation tại
   cổng D3.5 (DR-015 — Bước 1 offline trên CALIB + Bước 2 thăm dò
   mức-lệnh trên testnet + Bước 3 đối chứng âm Z0). D10 giữ vai trò
   XÁC NHẬN ở quy mô đầy đủ với chiến lược hoàn chỉnh — nếu số D10
   mâu thuẫn số D3.5 vượt biên hiệu chỉnh đã ghi, đó là phát hiện
   L2 (§11b.1): thước đã đổi giữa hai lần đo, xử theo quy trình L2,
   KHÔNG lặng lẽ lấy số mới.
```

## 9b.4. Test bắt buộc

```
L-Z9  🆕 D2 có kết quả VERIFIED (không phải "chắc là được") trước
      khi Decision Log ghi nhận bất kỳ plan nào dùng DG6 (§4.1) —
      vì DG6 giả định có thể đóng vị thế NGAY, phụ thuộc gián tiếp
      vào việc SL/lệnh trên sàn phản ánh đúng trạng thái mong muốn
L-Z49 🔴 CRITICAL 🆕 v7 — D7 PASS TRƯỚC D4: test đơn vị dựng backtest
      nhỏ (1 pair, 1 zone, 3 tranche), khẳng định custom_data ghi ở
      tranche 1 đọc lại NGUYÊN VẸN ở callback của tranche 2, 3, DG6,
      DG7, DG8 và custom_exit. FAIL → không chạy D0.9.
L-Z50 🆕 v7 — D6: mọi tranche fill trong backtest có
      fill_price == giá mà timeframe_detail 5m cho thấy đã CHẠM p_i
      (không phải open nến 1H). Lệch > 0 ở bất kỳ fill nào → ghi
      nhận D6 CHƯA được giảm nhẹ bởi H5, báo cáo phân bố lệch.
L-Z51 🆕 v7 — "đạt" trên đĩa (LD-32): KHÔNG tiêu chí nào của D1–D7
      hay GATE được đánh dấu VERIFIED/PASS nếu file trạng thái trên
      đĩa chưa có khoá tương ứng SINH RA TỪ MỘT LẦN CHẠY THẬT tới hết.
      Unit test có mock KHÔNG đủ. Tool A đã ghi "đạt" trong tài liệu
      cho một khoá chưa từng tồn tại trên đĩa.
```

---

# PHẦN 9c — 🆕 QUẢN TRỊ PHÉP THỬ
## Decision Records DR-009 → DR-012, ngân sách trial, lockbox, Idea Queue

## 📋 DR-009 — VAI TRÒ CỦA LLM: PHÂN LOẠI THEO NGUỒN THÔNG TIN

> **Trạng thái:** ACTIVE ngay khi bản vá được merge.
> **🔄 Sửa so với bản nháp đầu:** bản nháp cấm LLM sinh giả thuyết một cách chung chung — **quá chặt và sai trục**. Trục phân loại đúng không phải "LLM được làm gì" mà là **"đề xuất đó sinh ra từ nguồn thông tin nào"**. Cùng một câu chữ, nếu sinh ra từ cơ chế kinh tế thì sạch, nếu sinh ra từ việc đọc kết quả của Tool D thì là tìm kiếm trên dữ liệu đội lốt suy luận nhân quả.

### Vì sao trục phân loại là NGUỒN THÔNG TIN

```
Vấn đề KHÔNG PHẢI "LLM có thông minh không". Vấn đề là SỐ TRIAL NGẦM.

   Một đề xuất sinh ra sau khi đọc kết quả backtest mang theo một số
   trial ẩn: số giả thuyết mà mô hình đã ngầm cân nhắc và loại bỏ
   trước khi nói ra một câu. Con số đó KHÔNG ĐO ĐƯỢC, KHÔNG GHI SỔ
   ĐƯỢC → DSR không hiệu chỉnh được → N ở §9c.3 trở thành số dối.

   Một đề xuất sinh ra từ cơ chế kinh tế, MÙ với kết quả Tool D,
   không mang theo số trial ẩn nào. Nó tiêu đúng 1 slot, đếm được.

🔴 Đặc tính cần nhớ về LLM: thứ nó làm tốt nhất là SINH RA LỜI GIẢI
   THÍCH TRÔI CHẢY CHO BẤT KỲ MẪU HÌNH NÀO, kể cả nhiễu thuần tuý.
   Trong nghiên cứu định lượng, nút thắt không phải là tìm được lời
   giải thích — mà là TỪ CHỐI lời giải thích. Khi chi phí sinh giải
   thích tụt về 0, mọi mẫu ngẫu nhiên đều có một câu chuyện hay.
```

### ✅ LOẠI A — CHO PHÉP, vào Idea Queue (§9c.7)

> 🔴 **SỬA QUAN TRỌNG ở v3.3.** Bản v3.2 dùng cờ nhị phân `contaminated` với nghĩa "đã xem số liệu = hỏng". **Quy tắc đó quá thô và chặn nhầm.** Có hai loại số liệu khác hẳn nhau về mặt thống kê, và chỉ một loại gây nhiễu:
>
> | Loại | Ví dụ | Gây nhiễu? |
> |---|---|---|
> | **Cấu trúc thị trường** | Phân bố funding 2024; tần suất zone bị phá theo giờ; OI quanh vùng thanh khoản | ❌ **Không** — sự thật về THỊ TRƯỜNG, không phải về Tool D |
> | **Hiệu năng Tool D** | Tool D thua 12 lệnh khi ADX 21-23; win rate theo tier; equity curve | 🔴 **Có** — đây là fitting |
>
> Yêu cầu "ý tưởng phải dựa trên số liệu khách quan, không chém gió" nằm **hoàn toàn ở cột 1**, và v3.2 đã chặn nhầm cả cột đó. Trường `contaminated` (nhị phân) **được thay bằng `data_source`** (ba giá trị) ở §9c.7.3.

```
PHÂN LOẠI THEO data_source — hai giá trị đầu HỢP LỆ:

   ✅ "MECHANISM"  — suy từ cơ chế thị trường, lý thuyết, tài liệu
                     bên ngoài. Không chạm dữ liệu nào của dự án.
   ✅ "EXPLORE"    — 🆕 phân tích dữ liệu trên TẬP EXPLORE (§9c.4b):
                     BTC/ETH + coin trượt tiêu chí pool. Phân tích
                     thoải mái, KHÔNG giới hạn, KHÔNG tốn trial.
   🆕 v5 — NGOẠI LỆ CÓ KIỂM SOÁT cho GIAI ĐOẠN VẬN HÀNH:
      LLM ĐƯỢC đọc ĐẦU RA của `periodic_report.py` (§12d) — một bộ
      chỉ số CỐ ĐỊNH, commit trước khi live — và ĐƯỢC đề xuất đổi
      tham số theo §12c.3, với ràng buộc mọi câu phải TRÍCH SỐ.
      Lý do ngoại lệ hợp lệ: không gian tìm kiếm bị chặn bởi ĐỊNH
      NGHĨA BÁO CÁO, đã cố định trước khi có dữ liệu.
      🔴 VẪN CẤM: đọc DB lệnh thô, tự tính chỉ số mới, "kiểm tra
         thêm một góc nữa". Đó là tìm kiếm không chặn được.

   🔴 "TOOL_D_RESULTS" — LOẠI THẲNG (trừ ngoại lệ §12d ở trên). Bất kỳ ý tưởng nào sinh ra sau
                     khi đọc kết quả backtest/WFO/ablation của Tool D,
                     hoặc phân tích trên CALIB/WFO/LOCKBOX.

ĐIỀU KIỆN BẮT BUỘC cho Loại A:
   ❌ Không đọc kết quả backtest / WFO / ablation CỦA TOOL D
   ❌ Không đọc trường `outcome` của trial_registry
   ❌ Không phân tích trên CALIB / WFO / LOCKBOX
   ✅ ĐƯỢC đọc: spec, cơ chế thị trường, kiến thức chung, tài liệu
      bên ngoài, VÀ toàn bộ TẬP EXPLORE

MỌI ý tưởng Loại A phải qua BỘ LỌC §0.1 ĐÃ CÓ SẴN — không tạo bộ lọc mới:
   1. Cơ chế: ai làm gì tạo ra dịch chuyển giá?
   2. 🔴 AI TRẢ TIỀN? — ai là người thua ở phía bên kia giao dịch?
   3. Độ bền: vì sao chưa bị arbitrage hết?

   → Không trả lời được câu 2 → LOẠI NGAY, không tốn trial nào.
     Đây là bộ lọc rẻ nhất và hiệu quả nhất: phần lớn ý tưởng do LLM
     sinh ra chết ở đúng câu này.
```

### ❌ LOẠI B — CẤM TUYỆT ĐỐI

```
Bất kỳ đề xuất nào sinh ra SAU KHI LLM đọc kết quả định lượng Tool D:
   ❌ "Chỉ báo nào trong 5 cái này không phù hợp?"
   ❌ "Tại sao entry lại fail ở nhóm lệnh này?"
   ❌ "Nên chỉnh ngưỡng ZSS lên hay xuống?"
   ❌ "Regime đã đổi, nên thêm điều kiện gì?"
   ❌ Ra phán quyết PASS/FAIL trên bất kỳ GATE nào
   ❌ Được cấp quyền chạm dữ liệu lockbox (§9c.4)

⚠️ Loại B nguy hiểm ĐÚNG VÌ nó có cảm giác hữu ích nhất. Một bộ lọc
   sinh ra từ việc đọc tập lệnh thua là bộ lọc được fit vào chính tập
   lệnh thua đó. Nó SẼ có backtest đẹp. Nó SẼ có câu chuyện kinh tế
   thuyết phục. Và nó SẼ chết ở lockbox — lúc đó không còn lockbox
   thứ hai để biết mình đã sai ở đâu.
```

### 🚪 Ranh giới thực thi — tách phiên

```
Một phiên làm việc đã đọc kết quả định lượng thì TOÀN BỘ phiên đó bị
NHIỄM — không được sinh ý tưởng trong phiên đó nữa.

   PHIÊN "PHÂN TÍCH KẾT QUẢ"  →  được đọc số, KHÔNG được sinh ý tưởng
   PHIÊN "SINH Ý TƯỞNG"       →  được sinh ý tưởng, KHÔNG được đọc số

   🔴 Không trộn hai loại phiên. Đây là ràng buộc THỰC THI ĐƯỢC duy
      nhất với vận hành một người — không có cách kỹ thuật nào bắt
      LLM "quên" thứ đã nằm trong context.

   Mọi ý tưởng vào Idea Queue phải ghi `session_type: "IDEA"` và
   `data_source` ∈ {"MECHANISM", "EXPLORE"}. Nếu không chắc phiên đó
   có sạch không → mặc định ghi "TOOL_D_RESULTS", loại ý tưởng.

   ⚠️ "Phiên nhiễm" giờ có nghĩa hẹp hơn: phiên đã đọc KẾT QUẢ TOOL D.
      Phiên phân tích tập EXPLORE KHÔNG bị coi là nhiễm.
```

### Phạm vi khác — không đổi

```
✅ Soạn thảo, refactor, chuẩn hoá văn bản spec
✅ Phản biện cấu trúc lập luận, chỉ ra mâu thuẫn nội bộ tài liệu
✅ Kiểm kê cơ học (đếm tham số, tìm tham chiếu chết, dò trùng lặp)
✅ Sinh code theo spec ĐÃ CHỐT, kèm review của người

   💡 Đây mới là chỗ LLM có lợi thế bất đối xứng thật: kết luận của
      nó KIỂM CHỨNG ĐƯỢC TRONG 30 GIÂY bằng grep. Trong khi "chỉ báo
      X sẽ có edge" phải trả 8 tuần và một phần lockbox mới biết.
      Dùng LLM ở phía kiểm chứng RẺ, không phải phía kiểm chứng ĐẮT.

❌ Tự sửa spec mà không có bản diff được người duyệt từng mục
❌ Đóng vai "bộ nhớ" thay cho trial_registry/research-log

RÀNG BUỘC TRUY VẾT:
   Mọi phiên bản spec phải có changelog liệt kê mục ĐƯỢC THÊM, ĐƯỢC SỬA
   và ĐƯỢC XOÁ. Mục bị xoá phải ghi lý do. Lý do tồn tại điều khoản này
   là sự cố có thật: D1-D5 bị rớt mất im lặng (§9b), phát hiện muộn.
```

> ⚠️ **Đính chính kỹ thuật cần ghi lại để không hiểu nhầm về sau:** LLM có **memory** (đọc lại văn bản được nạp vào context) nhưng **KHÔNG có continuous learning** — trọng số mô hình không đổi theo kết quả của bạn. Không tồn tại vòng phản hồi "đề xuất → thấy fail → học → đề xuất tốt hơn". Cái tồn tại là "đọc kết quả fail → sinh một lời giải thích nghe hợp lý → đề xuất sửa", tức **fitting bằng ngôn ngữ**, không phải học. Mọi thiết kế quy trình giả định có continuous learning đều sai nền móng.

**Vì sao đây là DR chứ không phải ghi chú:** vai trò không được ghi thì mặc định trôi. Ở v1→v3 nó đã trôi một lần và mất nguyên danh sách giả định sống còn.

---

---

## 📋 DR-010 — NGÂN SÁCH TRIAL CỐ ĐỊNH, ĐĂNG KÝ TRƯỚC

> **Trạng thái:** ACTIVE. **Thay thế** cách hiểu "5 giả thuyết/quý" áp cho Tool D (LỖI 2).

```
HOÀ GIẢI §9.3 vs §9.5 — hai ngân sách KHÁC LOẠI, không cùng đơn vị:

   NGÂN SÁCH A — "5 giả thuyết/quý" (§9.3, kế thừa v10 §14D)
      Đơn vị: GIẢ THUYẾT KINH TẾ MỚI (ý tưởng về cơ chế thị trường)
      Ví dụ: "Zone Absorption có edge", "thêm OI vào ZSS có edge"
      Dùng chung Tool A + Tool D — vì rủi ro là con người, không phải dữ liệu
      → Zone Absorption tiêu 1 slot. Toàn bộ v1→v3 vẫn nằm trong 1 slot đó.

   NGÂN SÁCH B — TRIAL CALIBRATION (§9.5, MỚI ĐỊNH LƯỢNG ở đây)
      Đơn vị: MỘT LẦN ĐÁNH GIÁ MỘT CẤU HÌNH THAM SỐ TRÊN DỮ LIỆU
      Riêng cho Tool D, đếm vào N của DSR
      → ĐÂY là ngân sách mà v3 chưa từng đặt số

   🔴 Hai ngân sách này KHÔNG thay thế nhau. Trước bản vá này, spec
      dùng A để biện minh cho việc không đặt B — đó là lỗi phạm trù.
```

### 🔴 v6 — KIỂM KÊ BẬC TỰ DO: LÀM LẠI TỪ ĐẦU

> **Vì sao phải làm lại:** v5 khai *"đóng băng 9 tham số → 26 giảm còn 16"*. Phép trừ đó không ra được, và sai theo hai hướng cùng lúc.

```
🔴 LỖI 1 — ĐÓNG BĂNG THỨ CHƯA TỪNG ĐƯỢC ĐẾM
   `k` và `ADX threshold` KHÔNG có mặt trong bảng 26 DOF của v5.
   Đóng băng chúng giảm 0 bậc tự do, nhưng v5 tính chúng vào "9".

🔴 LỖI 2 — GỘP FUNDING CHỈ GIẢM ĐƯỢC 1, KHÔNG PHẢI 2
   Bảng 26 chỉ có HAI mục funding: §3.3d (−0.05%) và §4.1 DG6-C/D.
   Gộp 2 → 1 là −1. "Ngưỡng thứ ba" mà v5 nói tới là DG7 `0.3 × R_eff`
   — nhưng nó KHÁC ĐƠN VỊ (chi phí tích luỹ/rủi ro, không phải rate)
   nên không gộp được, VÀ nó chưa từng có trong bảng 26.

   → Trừ đúng theo danh sách v5:  −2 (w) −1 (funding) −1 (TP2)
     −1 (DG6-B) −1 (tuổi trend) = −6  →  26 − 6 = 20, KHÔNG phải 16.

🔴 LỖI 3 — BA THAM SỐ TỰ DO KHÔNG BAO GIỜ ĐƯỢC ĐẾM
   §3.1  w = [0.35,0.35,0.30]   ← §3.1 tự khai "1 bậc tự do" ngay
                                   tại chỗ, nhưng không có trong bảng
   §4c   DG7  0.3 × R_eff
   §5.1  TP_fallback  4.0 × R_eff  và  1.5 × R_eff
```

**Bảng đối chiếu — kiểm kê gốc và số phận từng mục:**

| §  | Tham số | v5 | v6 → | DOF v6 |
|---|---|---|---|---|
| §0.3 | tiêu chí pool (i)-(iv) | 4 | **B0** — chốt 1 lần bằng tiêu chí hạ tầng, không tune | 0 |
| §1.2 | `w_a/w_b/w_c` | 2 | 🔒 đóng băng 1/3 | 0 |
| §1.3 | ngưỡng ZSS | 1 | 🟡 tunable **#1** | 1 |
| §2.3 | tuổi trend | 1 | 🔒 đóng băng (có điều kiện) | 0 |
| §2.4 | "ngược hẳn" | 1 | ❌ **XOÁ** (§2.4) | 0 |
| §3.1 | `buf_sl` | 1 | 🟡 tunable **#2** | 1 |
| §3.1 | 🆕 `w` tranche | *(0 — bỏ sót)* | 🔒 đóng băng 1/3 | 0 |
| §3.3 | `zone_width` min | 1 | ❌ xoá **có điều kiện** (VERIFY D0-PRE) | 0 *(hoặc 1)* |
| §3.3b | ngưỡng rejection wick | 1 | 🟡 tunable **#3** | 1 |
| §3.3b | `v_min` | 1 | 🟡 tunable **#4** | 1 |
| §3.3c | số nến 15m | 1 | ❌ **XOÁ** (§3.3c) | 0 |
| §3.3d | funding rate | 1 | 🔒 đóng băng −0.05%, gộp với DG6-D | 0 |
| §3.3d | ngưỡng hồi 50% | 1 | 🟡 tunable **#6** | 1 |
| §4 | DG4 | 1 | 🟡 tunable **#7** | 1 |
| §4.1 | DG6-A tỉ lệ ATR | 1 | 🟡 tunable **#8** | 1 |
| §4.1 | DG6-B số nến | 1 | 🔒 đóng băng = DG4 = 8 | 0 |
| §4.1 | DG6-C/D funding | 1 | 🟡 tunable **#5** *(gộp với §3.3d)* | 1 |
| §4c | 🆕 DG7 `0.3 × R_eff` | *(0 — bỏ sót)* | 🟡 tunable **#12** | 1 |
| §5.1 | TP1 trừ hao | 1 | 🟡 tunable **#9** | 1 |
| §5.1 | TP2 trail | 1 | 🔒 đóng băng 1.5 | 0 |
| §5.1 | 🆕 TP_fallback 4.0 / 1.5 | *(0 — bỏ sót)* | 🔒 đóng băng | 0 |
| §6.2 | hệ số 1 — `L_BASE` | 1 | ❌ xoá → `mult_regime` 🔒 đóng băng | 0 |
| §6.2 | hệ số 3 — `mult_corr` | 1 | 🟡 tunable **#10** | 1 |
| §6.2 | hệ số 4 — `mult_dd` | 1 | 🔒 **CẤP C** — cầu dao, không tune | 0 |
| §6.2 | 🆕 `mult_edge` / `mult_deploy` | *(0 — không định nghĩa)* | 🔒 định nghĩa + đóng băng | 0 |
| §4b.3 | `max_hold_bars` | 1 | 🟡 tunable **#11** | 1 |
| **TỔNG** | | **26** *(thực: 28)* | | **12** |

```
════════════ NGÂN SÁCH CHỐT v6 ════════════

   B0. Pool §0.3(i)-(iv)  1 trial/tiêu chí, KHÔNG tune       →   4
   B1. Calibration        3 giá trị × 12 tham số × 2 hướng   →  72
   B2. Ablation D0.9      9 cấu hình × 2 hướng               →  18
   B3. Dự phòng           sự cố dữ liệu / chạy lại do bug    →  20
   ────────────────────────────────────────────────────────────────
   N_ĐĂNG_KÝ = 114     ← đi THẲNG vào công thức DSR ở §10.2
                         rào Sharpe ≈ √(2·ln 114) ≈ 3,08

   ⚠️ Nếu VERIFY ở D0-PRE cho thấy `zone_width` min KHÔNG chết:
      13 tham số → B1 = 78 → N = 120 → rào ≈ 3,09.
      CHỐT N SAU KHI VERIFY, không phải song song (§3.3).

🔴 VÌ SAO POOL TÁCH RA B0, KHÔNG NHÂN 3×2:
   Bốn tiêu chí pool được chốt MỘT LẦN ở D0-PRE bằng thuộc tính hạ
   tầng (volume đủ để `volume_ratio` không nhiễu, lịch sử đủ dài,
   cost economics cho lệnh post-only, có zone đối diện để TP có nghĩa)
   — KHÔNG bằng cách thử 3 giá trị rồi chọn cái cho backtest đẹp nhất.
   Chúng vẫn CHẠM DỮ LIỆU nên vẫn tính vào N, nhưng 1 trial/tiêu chí.
   🔴 Chỉnh lại một tiêu chí pool về sau = 1 trial từ B3, không miễn phí.

🔴 BA QUY TẮC BẤT BIẾN (giữ nguyên từ v5):
   (1) Mỗi lần CHẠM DỮ LIỆU để đánh giá một cấu hình = 1 trial, kể cả
       khi kết quả xấu, kể cả khi "chỉ xem thử", kể cả khi chạy lại vì
       nghi ngờ. Không có trial nào miễn phí.
   (2) Hết ngân sách → DỪNG DỰ ÁN Ở TRẠNG THÁI HIỆN TẠI. Muốn tiếp
       phải mở giả thuyết mới ở NGÂN SÁCH A.
   (3) N dùng cho DSR là N_ĐĂNG_KÝ (114), KHÔNG phải N_ĐÃ_DÙNG.

🔴 SAU KHI LIVE, N TĂNG THEO NGÂN SÁCH TÁI TẠO (§12c.2):
   N_hiện_tại = 114 + (số trial đã dùng sau live)
                    + 6 × (số tham số đóng băng đã mở khoá)
   DSR tính lại tại MỖI điểm quyết định với N hiện tại.
```

> ⚠️ **Hệ quả cần chấp nhận trước:** với N = 114, ngưỡng Sharpe kỳ vọng dưới giả thuyết null ≈ **3,08** (so với ≈2,15 nếu N=10). Rào cao hơn ~43%. Việc kiểm kê lại ở v6 hạ N từ 134 → 114 và rào từ 3,13 → 3,08 — **cải thiện 1,6%, gần như không đáng kể**. Đó là bằng chứng cho nguyên tắc đã ghi ở v5: `√(2·ln N)` tăng rất chậm theo N, nên **thêm vài trial gần như không tốn gì; thêm THAM SỐ mới tốn thật**. Giá trị thật của việc làm lại kiểm kê không phải hạ rào — mà là **N giờ là một con số truy được**, thay vì một con số không ai cộng ra được.

> 🔴 **Điều v6 KHÔNG làm, và không nên làm:** không đóng băng thêm để hạ N nữa. 12 tham số còn lại đều nằm ở chỗ không có lý thuyết nào chỉ đường (ngưỡng ZSS bao nhiêu là "đủ mạnh"? `buf_sl` 0.4 hay 0.5 ATR?). Đóng băng chúng bằng phỏng đoán rồi khai là "prior không-thông-tin" sẽ là **gian lận DSR có vẻ ngoài chính đáng** — hạ N mà không hạ số phép thử thật, vì rồi cũng sẽ phải thử.

---

---

## 📋 DR-011 — LOCKBOX OUT-OF-SAMPLE, CHẠM ĐÚNG MỘT LẦN

> **Trạng thái:** ACTIVE. Gỡ LỖI 4.

```
PHÂN CHIA DỮ LIỆU — chốt bằng NGÀY CỤ THỂ, niêm phong bằng hash,
TRƯỚC khi chạy bất kỳ backtest nào:

   ┌─────────────────────────┬──────────────┬────────────────────────┐
   │ Tập                     │ Được chạm    │ Dùng cho               │
   ├─────────────────────────┼──────────────┼────────────────────────┤
   │ CALIB   [T0 … T1]       │ Không giới   │ Calibration 12 tham số │
   │                         │ hạn (trong   │ (B0 + B1)   🔴 v6      │
   │                         │ ngân sách)   │                        │
   │ WFO     [T1 … T2]       │ Theo cơ chế  │ Walk-forward D3/D9,    │
   │                         │ walk-forward │ Ablation D0.9 (B2)     │
   │ LOCKBOX [T2 … T3]       │ 🔴 ĐÚNG 1 LẦN│ Xác nhận cuối cùng,    │
   │                         │              │ sau khi ngân sách hết  │
   └─────────────────────────┴──────────────┴────────────────────────┘

   🚪 ĐIỀU KIỆN CHẤT LƯỢNG LOCKBOX — không đạt thì lockbox là trang trí:
      (a) Độ dài ≥ 20% tổng dữ liệu khả dụng
      (b) Chứa ≥ 1 chế độ thị trường KHÁC BIỆT rõ rệt so với CALIB+WFO
          (ví dụ: một giai đoạn drawdown BTC > 30%, hoặc một giai đoạn
          sideway kéo dài) — kiểm tra bằng mắt trên chart BTC trước khi
          niêm phong, ghi lý do chọn mốc T2 vào research-log
      (c) Chứa ≥ 30 lệnh dự kiến cho cấu hình tốt nhất — nếu ít hơn,
          lockbox không đủ power thống kê và PHẢI kéo dài hoặc dời T2
      (d) LOCKBOX là đoạn GẦN HIỆN TẠI NHẤT (T3 = ngày niêm phong).
          Không được đặt lockbox ở giữa rồi WFO trên đoạn sau — như vậy
          là tự cho mình nhìn tương lai.

   🔒 CƠ CHẾ NIÊM PHONG (thực thi được với vận hành một người):
      1. Dữ liệu lockbox nằm ở thư mục RIÊNG, ngoài đường dẫn mặc định
         của Freqtrade data-dir
      2. Ghi SHA-256 của toàn bộ file dữ liệu + mốc T2/T3 vào
         `lockbox_seal.json`, commit vào git, KHÔNG sửa
      3. Mọi lần truy cập ghi vào `lockbox_access.log` với lý do,
         timestamp, và hash cấu hình được test
      4. Sau lần chạm đầu tiên, lockbox coi như ĐÃ TIÊU. Không có lần hai.

   ⚠️ Thừa nhận thẳng: cơ chế này KHÔNG NGĂN được bạn tự phá niêm phong
      — nó chỉ làm việc phá niêm phong trở nên HỮU HÌNH và có dấu vết.
      Với vận hành một người, đó là mức bảo đảm cao nhất khả thi. Không
      giả vờ nó là ràng buộc kỹ thuật cứng.
```

```
🚪 QUY TẮC QUYẾT ĐỊNH TRÊN LOCKBOX — VIẾT TRƯỚC KHI CHẠM:
   Phải điền đầy đủ và commit TRƯỚC lần chạm duy nhất. Sau khi thấy
   kết quả, KHÔNG được sửa quy tắc.

   Cấu hình đem ra lockbox: ......... (đúng MỘT cấu hình, chọn từ WFO)

🔴 v6 — ĐỊNH NGHĨA "MỘT LẦN CHẠM", vì v5 tự mâu thuẫn:
   v5 ghi "Hướng: Long / Short / cả hai, chạy tách" trong khi L-Z13
   kiểm `lockbox_access.log` có ĐÚNG 1 bản ghi vĩnh viễn. Chạy tách
   hai hướng = 2 lần chạm = L-Z13 fail.

   ✅ MỘT LẦN CHẠM = MỘT PHIÊN CHẠY DUY NHẤT, sinh HAI bộ metric
      (Long và Short) từ cùng một lệnh, ghi MỘT bản ghi access log.
      "Chạy tách" nghĩa là metric tách, KHÔNG phải phiên tách.

   Ngưỡng PASS — điền bằng SỐ trước khi chạy, cho TỪNG hướng:
      DSR-adjusted expectancy      ≥ ......
      max_single_trade_loss / risk_budget  ≤ 1.15
      liq_buffer_ratio trung bình  ≥ 8
      số lệnh thực tế              ≥ 30

🚪 BA KẾT CỤC — 🆕 v6. (v5 chỉ có PASS / DỪNG DỰ ÁN, và điều đó tạo
   áp lực gian lận cực lớn đúng tại thời điểm quan trọng nhất — §9c.5
   đã tự thừa nhận đây là "hành vi mà một người làm việc một mình DỄ
   TỰ THA THỨ NHẤT".)

   ✅ PASS          mọi ngưỡng đạt  →  vào D10 (testnet)

   🟡 INCONCLUSIVE  số lệnh thực tế < 30
                    → THIẾU MẪU, không phải THIẾU EDGE.
                    → KHÔNG kết luận. KHÔNG tune. KHÔNG chọn cấu
                      hình khác.
                    → Chờ tích luỹ dữ liệu mới, NIÊM PHONG LẠI đoạn
                      [T3_cũ … T3_mới] như một lockbox MỚI với hash
                      mới, và chỉ chạy trên ĐOẠN MỚI (không chạy lại
                      trên đoạn đã nhìn — đoạn đó đã tiêu).
                    🔒 TỐI ĐA 2 LẦN GIA HẠN. Lần thứ ba → FAIL mặc
                       định. Không có trần này, "chờ thêm dữ liệu"
                       trở thành cửa thoát vô hạn cho mọi lần FAIL.

   ❌ FAIL          số lệnh ≥ 30 VÀ ngưỡng không đạt
                    → Zone Absorption bị BÁC BỎ Ở CẤU HÌNH NÀY.
                    → Slot NGÂN SÁCH A đóng. Ghi `retest_forbidden`.
                    → 🔴 DỰ ÁN KHÔNG DỪNG. Ứng viên tiếp theo lấy từ
                      Idea Queue (§9c.7), chạy lại đủ chu trình với
                      LOCKBOX MỚI trên dữ liệu chưa từng dùng.
                    → 🔴 KHÔNG được: tune lại cấu hình vừa chết,
                      "thử cấu hình thứ hai" trên cùng lockbox, hay
                      nới ngưỡng PASS.

🔑 Khác biệt giữa hai câu "dự án tiếp tục" — đây là toàn bộ giá trị
   của lockbox, và là điểm dễ tự lừa mình nhất:
      ✅ tiếp tục bằng GIẢ THUYẾT KHÁC, dữ liệu sạch khác
      ❌ tiếp tục bằng cách hồi sinh giả thuyết đã bị dữ liệu bác bỏ
```

---

---

## 📋 DR-012 — CHANGE-CONTROL SAU KHI ĐÃ LIVE

> Gỡ khoảng trống mà điểm 3 của đề xuất gốc nhầm là "đã có" (DG-gate và Risk Supervisor gate LỆNH, không gate THAY ĐỔI THAM SỐ).

```
Sau khi vào D12 (vốn thật), mọi thay đổi được phân ba hạng:

   HẠNG 0 — CẤM VĨNH VIỄN, không có quy trình nào cho phép:
      • Sửa bất kỳ nguyên lý nào trong D0 (§3.4)
      • Nới ngưỡng liq_buffer_ratio = 8 (§6.4b)
      • Tắt DG6, DG7 (§4c), hoặc DG8; tắt điều kiện D của DG6 khi
        Short đang bật
      • Thêm tranche thứ tư
      • Đổi `k` (§1.1) — 🆕 v6, xem §6.9.4
      • 🆕 v6 — NỚI THANG DRAWDOWN 5/8/20% SAU KHI ĐÃ THẤY DRAWDOWN

        🔴 Ranh giới thời gian này phải viết ra vì nó là chỗ dễ tự
        tha thứ nhất trong toàn bộ tài liệu:
           ✅ HỢP LỆ:   đặt/sửa thang TRƯỚC khi chạm dữ liệu (D0-PRE).
                        Đó là khẩu vị rủi ro, không suy được từ dữ liệu.
           ❌ HẠNG 0:   sửa thang SAU KHI đã thấy một drawdown thật.
                        Lúc đó nó không còn là khẩu vị — nó là phản ứng
                        với một mẫu cụ thể, tức fitting bằng cầu dao.
        Câu sẽ xuất hiện trong đầu khi vi phạm: "8% chặt quá, crypto
        biến động mà". Nếu câu đó đúng, nó đã đúng ở D0-PRE.

   HẠNG 1 — Sửa lỗi (bug fix), không đổi hành vi kỳ vọng:
      → Cho phép, bắt buộc: ghi research-log + test hồi quy + Risk
        Supervisor xác nhận trạng thái sạch trước khi deploy

   HẠNG 2 — Đổi tham số / thêm điều kiện / đổi ngưỡng:
      → TIÊU 1 TRIAL từ ngân sách dự phòng (B3, §9c.3)
      → Nếu ngân sách dự phòng đã hết: KHÔNG ĐƯỢC ĐỔI. Muốn đổi phải
        mở giả thuyết mới ở NGÂN SÁCH A và chạy lại chu trình từ đầu,
        bao gồm một lockbox MỚI trên dữ liệu chưa từng dùng.
      → 🔴 Không có ngoại lệ cho "chỉ chỉnh nhẹ", "thị trường đã đổi",
        hay "chỉ tạm thời". Đây chính là những câu dẫn tới overfitting
        sau khi live, giai đoạn tốn tiền thật.

   🚪 Cổng phê duyệt: mọi thay đổi Hạng 1/2 phải qua một commit riêng,
      ghi rõ hạng, lý do, trial tiêu tốn (nếu Hạng 2), và trạng thái
      Risk Supervisor tại thời điểm deploy.

🆕 v3.3 — ÁNH XẠ VỚI PHÂN LOẠI SAI CÔNG THỨC (§11b.1):
   L1 (sai giá trị)    → Hạng 2, tiêu 1 trial từ B3
   L2 (sai cấu trúc)   → KHÔNG phải Hạng 2. Phải mở giả thuyết mới ở
                         NGÂN SÁCH A + cần LOCKBOX MỚI. Đây là dự án
                         mới đội lốt bản vá.
   L3 (sai giả thuyết) → Hạng 0. DỪNG DỰ ÁN. Không có quy trình sửa.

   🔴 Cạm bẫy nguy hiểm nhất: PHÂN LOẠI NHẦM L2/L3 THÀNH L1 để được
      dùng quy trình rẻ hơn. Dấu hiệu nhận biết: nếu phải đổi >1 tham
      số cùng lúc để "sửa", gần như chắc chắn đó là L2, không phải L1.
```

---

---

## 📋 DR-014 — 🆕 v8: SỔ HAI TRẠNG THÁI — "TIÊU MỘT TRIAL" ĐƯỢC TÍNH KHI NÀO

> **Trạng thái:** ACTIVE. Thay toàn bộ quy tắc 4 của §9c.2 (v7). Nguồn: LD-34, LD-31, LD-01/LD-02.
> **Ngoài phạm vi:** quy tắc chạm lockbox — DR-011 có luật riêng ("một lần chạm = một phiên"), cố ý không gộp.

```
NGUYÊN TẮC NỀN
   Một trial bị tiêu vào ĐÚNG KHOẢNH KHẮC kết quả của nó trở nên đọc
   được. Lạm phát thống kê sinh từ việc CHỌN LỰA giữa các kết quả đã
   quan sát, không sinh từ việc khởi chạy. Lần chạy chết trước khi có
   chỉ số nào = không mang thông tin = không gây lạm phát. Lần chạy
   đã in kết quả một phần = đã mang thông tin = tiêu, bất kể chạy hết
   hay không.

🔴 SỬA LẬP LUẬN CỦA BẢN NHÁP — vai trò thật trong Tool D:
   DSR TRƯỚC live dùng N_ĐĂNG_KÝ = 114 (DR-010 quy tắc 3), KHÔNG dùng
   N_ĐÃ_DÙNG. Sổ hai trạng thái KHÔNG nuôi mẫu số DSR ở giai đoạn
   nghiên cứu. Nó tồn tại vì BA việc khác:
      (a) Cưỡng chế luật dừng: N_ĐÃ_DÙNG ≤ N_ĐĂNG_KÝ tại mọi thời
          điểm (L-Z11). Kế toán "tiêu" lỏng → vượt trần âm thầm →
          N_ĐĂNG_KÝ cố định trở thành PHI-bảo-thủ.
      (b) SAU live, N = 114 + số trial đã dùng sau live (§12c.2) —
          ở đó định nghĩa "đã dùng" đi THẲNG vào DSR.
      (c) Chặn đường lách không-cần-cố-ý: dừng lần chạy khi kết quả
          sớm xấu → "chưa hoàn tất" → không ghi sổ. Hành vi này là
          phản xạ tự nhiên khi chờ một lần chạy dài, không cần ý xấu.

════ 1. HAI TRẠNG THÁI ════
   ĐẶT CHỖ (RESERVED) — tạo tại thời điểm đăng ký (registered_at):
      • Chiếm ngân sách Khả dụng NGAY LẬP TỨC, mức = `contribution`.
      • CHƯA vào N_ĐÃ_DÙNG.
      • Không có đặt chỗ hợp lệ → bộ chạy TỪ CHỐI khởi động (L-Z52).
        Đây là phần cơ khí của L-Z34: N nối vào code ở cả đầu VÀO,
        không chỉ đầu ra.
   ĐÃ TIÊU (CONSUMED) — không thể hoàn tác:
      • Vào N_ĐÃ_DÙNG với đúng `contribution` đã khai.
      • Kích hoạt tại khoảnh khắc đầu tiên có BẤT KỲ chỉ số nào đọc
        được: ghi ra đĩa, in ra màn hình, hay kết quả fold đầu tiên —
        cái nào đến trước.

════ 2. SỔ KẾ TOÁN ════
   Khả dụng = (N_ĐĂNG_KÝ + N_tái_sinh §12c.2)
              − Σ contribution(CONSUMED) − Σ contribution(RESERVED)
   • Trial ĐÃ TIÊU không bao giờ quay lại pool.
   • Trial tái sinh CỘNG vào pool, không xoá phần đã tiêu.
   • Trần B3 ≤ 20 áp lên pool tái sinh (§12c.2), không áp lên phần
     đã tiêu.
   • Dòng CTRL (điểm kiểm soát §0d.4) và mọi lần chạy trên EXPLORE:
     ngoài sổ này — nhưng bộ chạy PHẢI tự khẳng định timerange/tập
     dữ liệu bằng assert (L-Z55), không nhận khai báo của người chạy.
     Phạm vi áp DR-014 = mọi lần chạy chạm CALIB / WFO / LOCKBOX với
     mục đích đánh giá.

════ 3. CON DẤU ĐO LƯỜNG — CƠ CHẾ, KHÔNG PHẢI QUY ƯỚC ════
   • Bộ chạy tự ghi file con dấu (`seal_path`) ngay khi chỉ số đầu
     tiên TỒN TẠI trong bộ nhớ, TRƯỚC cả khi in/ghi kết quả.
   • CÓ con dấu ⇒ CONSUMED. Người vận hành KHÔNG có quyền phủ quyết —
     gọi thẳng hàm hoàn trả cũng phải bị từ chối (L-Z53).
   • KHÔNG có con dấu ⇒ bộ chạy tự ghi `refund_cause_machine` từ exit
     code / exception / guard-block. KHÔNG lấy từ lời khai.
   🔴 Đây là điểm đảo chiều so với `abort_evidence` của v7: v7 vẫn là
   lời khai kèm tang vật do người nộp; v8 là máy tự ghi, người không
   có đường nhập liệu. Trả-lại-dựa-trên-lời-khai làm toàn bộ thiết kế
   thành trang trí — cùng nguyên tắc LD-01/LD-02.
   ⚠️ Kênh phụ thừa nhận thẳng: thời lượng chạy / tiến độ fold vẫn
   quan sát được từ ngoài và KHÔNG bị con dấu bắt. Đó là rò rỉ mức
   thấp, chấp nhận; trần trả lại ở mục 5 là lớp phòng thủ cho đúng
   kênh này.

════ 4. ĐƠN VỊ ĐẶT CHỖ — KHÔNG PHẢI LUÔN BẰNG 1 ════
   `contribution` = mức đóng góp vào N, khai TRƯỚC khi chạy:
      • Backtest / WFO đơn cấu hình → 1.
      • MỘT LỆNH chạy lô đánh giá NHIỀU cấu hình → số cấu hình.
   Phải đặt chỗ ĐỦ toàn bộ mức trước khi khởi chạy. Bộ chạy không xác
   định được mức → ghi MỨC TỐI ĐA CÓ THỂ, không phải tối thiểu
   (fail-closed, LD-31). Khả dụng < contribution → TỪ CHỐI.
   🔴 KHÁC BẢN NHÁP — KHÔNG CÓ ĐIỀU KHOẢN HYPEROPT: bản nháp quy định
   "một lần hyperopt → số trial hiệu dụng đã khai". Điều khoản đó
   HỢP THỨC HOÁ một module bị CẤM TUYỆT ĐỐI (§0c.2) và mâu thuẫn
   L-Z25 (phát hiện hyperopt → registry MẤT HIỆU LỰC toàn bộ). Một DR
   không được mở cửa sau cho thứ spec đã đóng cửa trước. Quy tắc lô ở
   trên phủ mọi nhu cầu hợp lệ còn lại.

════ 5. TRẢ LẠI ĐẶT CHỖ ════
   Điều kiện DUY NHẤT: lần chạy kết thúc TRƯỚC khi con dấu được đóng.
   Bảng phân loại:
   ┌──────────────────────────────────────────────┬──────────────────┐
   │ Guard chặn trước khi chạy (0d.1: nhiễm tham  │ REFUNDED         │
   │ số, thiếu dữ liệu, sai timerange)            │                  │
   │ Mất mạng / OOM / OS kill, CHƯA có chỉ số nào │ REFUNDED         │
   │ Người dừng tay SAU khi có kết quả một phần   │ CONSUMED         │
   │ Chạy xong, thấy kết quả                      │ CONSUMED         │
   │ Chạy xong rồi phát hiện nhiễm tham số        │ CONSUMED — cho   │
   │                                              │ cấu hình bị nhiễm│
   │ Khởi chạy KHÔNG có đặt chỗ mà vẫn chạy được  │ CONSUMED +       │
   │ (lách qua bộ chạy)                           │ contaminated,    │
   │                                              │ khớp quy tắc 1   │
   │                                              │ §9c.2            │
   └──────────────────────────────────────────────┴──────────────────┘
   🔒 TRẦN TRẢ LẠI: 3 lần cho CÙNG một giả thuyết (cùng hypothesis_
   slot + param_under_test + param_value). Lần thứ 4 không có con dấu
   → vẫn CONSUMED. Đây thuần tuý là lớp phòng thủ dự phòng cho trường
   hợp con dấu hỏng + kênh phụ ở mục 3, KHÔNG phải yêu cầu thống kê —
   nếu con dấu hoạt động đúng, về lý thuyết lặp vô hạn cũng sạch.
   Số 3 là lựa chọn, không phải định lý (§14 #28) — chốt trước, không
   sửa sau khi thấy dữ liệu.

════ 6. NHIỄM THAM SỐ TIÊU GẤP ĐÔI — HỆ QUẢ CÓ CHỦ ĐÍCH ════
   Phát hiện một lần chạy đã đo CẤU HÌNH KHÁC cấu hình dự định (LD-01):
      • Lần chạy đó CONSUMED cho cấu hình bị nhiễm — kết quả đã được
        nhìn, thông tin đã rò vào quá trình quyết định, không thu hồi
        được (tiền lệ Tool A: người vận hành đã xây tiếp phân tích
        lên con số nhiễm).
      • Cấu hình DỰ ĐỊNH vẫn chưa được thử → cần MỘT ĐẶT CHỖ MỚI.
      • KHÔNG được xoá lần chạy khỏi sổ với lý do "không hợp lệ".
   → Nhiễm tham số = sự cố đắt gấp đôi = động lực đúng để nuôi guard
     0d.1 sống.
```

**Test khoá cứng — xem L-Z52 → L-Z55 (§9c.6).**

---

## 📋 DR-015 — 🆕 v8: CỔNG D3.5 — SAI LỆCH THƯỚC ĐO KHỚP TRANCHE & QUY TẮC PHÂN XỬ Z0 vs DCA

> **Trạng thái:** ACTIVE. Phải hoàn tất **TRƯỚC** khi chạy bất kỳ arm ablation nào (L-Z56) — chốt sau khi đã thấy kết quả ablation thì mất hiệu lực chống thiên vị.
> Nguồn: LD-11, LD-12, LD-15; giả định D6 (§9b.2); §3.5 (đoạn cảnh báo cuối). Dùng R đã đóng băng của DR-013 làm đơn vị quy đổi.

```
════ 1. VẤN ĐỀ ════
   Z0 và các nhánh DCA KHÔNG được đo bằng cùng một bộ máy:
      • Z0 đi đường vào lệnh chuẩn Freqtrade — một lần khớp.
      • Tranche 2+ đi qua adjust_trade_position() — đánh giá THEO
        NẾN, tại giá MỞ nến (D6).
   ⇒ Chênh lệch quan sát được = chênh CHIẾN LƯỢC thật + chênh THƯỚC
   ĐO, backtest không tách được. Sai số CỘNG DỒN theo số tranche:
   nhánh k tranche chịu k lần, Z0 chịu một — không tự triệt tiêu.
   CHIỀU của lệch chưa xác định (phụ thuộc điều kiện kích hoạt tranche
   và cách chọn nến lấy giá mở) — vì thế phải ĐO, không giả định.
   lookahead-analysis KHÔNG được dùng làm bằng chứng cho/chống ở vùng
   này (ba lớp dương tính giả — §7.2, LD-15, issue #12168).

🔴 v7 để trạng thái tệ nhất có thể: D6 chỉ được đo ở D10 (SAU
   ablation), rồi "đọc lại Nhánh 2". Tức kết luận Z0-vs-DCA hình
   thành TRƯỚC, thước được kiểm SAU. v8 tách phép thăm dò tối thiểu
   ra thành cổng D3.5 chặn TRƯỚC D4. D10 giữ vai trò xác nhận đầy đủ
   ở quy mô lớn hơn — không bị thay thế.

════ 2. BA BƯỚC ĐO — DỪNG NGAY KHI ĐỦ KẾT LUẬN ════

   BƯỚC 1 — Khoảng cách mô hình hoá (offline, không cần testnet):
      Mỗi lần điều kiện kích hoạt tranche thoả, ghi: giá backtest
      dùng cho tranche đó / giá vùng thiết kế thực sự định đặt /
      chênh lệch quy ra đơn vị R đóng băng của lệnh đó (DR-013).
      Đầu ra: PHÂN PHỐI lệch theo từng chỉ số tranche, tách Long/Short.
      → Đây là L-Z50 nâng từ "test" lên "phép đo có phân phối".
      🔴 PHÂN VÙNG DỮ LIỆU — bản nháp nói "trên chính dữ liệu dùng cho
      ablation" (= WFO). KHÔNG. Chạy trên CALIB: cơ học khớp lệnh
      (độ mịn nến + định nghĩa kích hoạt) không phụ thuộc đoạn ngày,
      còn chạy trên WFO trước ablation là nhìn trước cấu trúc chạm
      zone của tập đánh giá. Chỉ khi CALIB < 30 sự kiện kích hoạt
      tranche 2+ mới được mở rộng sang WFO, và khi đó đầu ra bị GIỚI
      HạN CỨNG vào danh sách: {chênh lệch giá, chỉ số tranche, hướng}
      — TUYỆT ĐỐI không PnL, không win/loss, không metric theo arm.
      Bộ chạy cưỡng chế danh sách này, không phải người.
      🔴 KẾ TOÁN: dòng CTRL, 0 trial (đo THƯỚC, không đánh giá cấu
      hình) — nhất quán DR-014 mục 2, kèm assert timerange (L-Z55).

   BƯỚC 2 — Tỷ lệ khớp trên testnet (thăm dò độc lập, mức lệnh —
   KHÔNG cần chiến lược hoàn chỉnh, không cần bot chạy thật):
      Đặt lệnh chờ post-only tại các mốc vùng trong khoảng thời gian
      định trước; ghi khớp đủ / khớp một phần / không khớp + giá khớp
      thật; đối chiếu giả định backtest cùng khoảng. Mục tiêu duy
      nhất: đo ca "giá chạm vùng nhưng lệnh KHÔNG khớp" — thứ backtest
      gần như chắc chắn đang giả định = luôn khớp (§3.5, LD-12).
      QUY MÔ CHỐT TRƯỚC (§14 #29): 14 ngày, ≥ 30 sự kiện chạm mốc
      trên toàn pool. Thiếu → gia hạn ĐÚNG 1 lần thêm 14 ngày. Vẫn
      thiếu → tỷ lệ khớp ghi UNKNOWN, Bước 1 vẫn bắt buộc, và mục 4
      phải chạy thêm kịch bản "x% tranche không khớp" với x = phần
      NO_FILL đã quan sát + toàn bộ phần chưa quan sát (fail-closed);
      rủi ro tồn dư ghi vào research-log.
      Khớp MỘT PHẦN: trạng thái thứ ba, trọng số = tỷ lệ đã khớp khi
      đưa vào hiệu chỉnh — không ép về nhị phân.

   BƯỚC 3 — Đối chứng âm (BẮT BUỘC): chạy CẢ Bước 1 và Bước 2 cho
      nhánh Z0. Không có mốc tham chiếu thì con số lệch của DCA không
      biết là lớn hay nhỏ. Hai nhánh lệch tương đương ⇒ sai số phần
      lớn triệt tiêu khi so sánh. Chỉ DCA lệch ⇒ xác nhận đúng vấn đề.

════ 3. TỔNG HỢP THÀNH MỘT CON SỐ ════
   Với mỗi lệnh mô phỏng: lệch-mỗi-lệnh = Σ |lệch| các tranche ≥ 2
   (đơn vị R). Con số hiệu chỉnh Δ_R:
      Δ_R = P90(phân phối lệch-mỗi-lệnh)  nếu n ≥ 30
      Δ_R = max quan sát được             nếu n < 30   (fail-closed)
   Phân vị cao, không trung vị — nhất quán LD-31: thước nghi ngờ thì
   nghi về phía bất lợi cho cơ chế phức tạp hơn. Tính riêng Long/Short.
   Cộng thêm thành phần NO_FILL từ Bước 2: mỗi tranche có xác suất
   không khớp p_nf thì kịch bản hiệu chỉnh bất lợi coi tranche đó
   không tồn tại (DCA mất phần hấp thụ backtest đã cho).

════ 4. QUY TẮC PHÂN XỬ — HIỆU CHỈNH CỰC ĐOAN HAI CHIỀU ════
   Cố ý KHÔNG đặt ngưỡng phần trăm cho "lệch bao nhiêu là nhiều" —
   ngưỡng tuỳ tiện là chỗ uốn kết luận sau khi thấy số.
      Chiều 1: giả định TOÀN BỘ Δ_R đã có lợi cho DCA → trừ Δ_R khỏi
               expectancy/lệnh (đơn vị R) của mọi arm DCA → so lại.
      Chiều 2: giả định ngược — cộng Δ_R cho DCA → so lại.
   ┌─────────────────────────────┬───────────────────────────────────┐
   │ Cùng một nhánh thắng Ở CẢ   │ Kết luận VỮNG trước sai số đo.    │
   │ HAI chiều                   │ Chấp nhận; ghi biên hiệu chỉnh    │
   │                             │ kèm kết quả.                      │
   │ Người thắng ĐỔI giữa hai    │ Chênh hai nhánh NHỎ HƠN sai số    │
   │ chiều                       │ thước ⇒ backtest KHÔNG ĐỦ TƯ CÁCH │
   │                             │ phân xử ⇒ áp mục 5.               │
   └─────────────────────────────┴───────────────────────────────────┘
   Lợi thế lớn tự sống sót qua hiệu chỉnh — quy tắc chỉ kích hoạt
   đúng lúc chênh lệch nằm trong vùng nhiễu của thước.
   🔴 THI HÀNH: quy tắc này KHÔNG đứng riêng — nó được nhúng thẳng
   vào Nhánh 2 của GATE D0.9 (§10.2): điều kiện "≥ 20%" chỉ tính là
   CÓ khi sống sót qua CẢ HAI chiều.

════ 5. KHI KHÔNG PHÂN XỬ ĐƯỢC ════
   5.1 MẶC ĐỊNH VỀ Z0. Gánh nặng chứng minh thuộc cơ chế phức tạp
       hơn: Z0 ít bất định đo lường hơn (một lần khớp, đường chuẩn),
       tiêu ít trial hơn, và nhất quán nguyên tắc đã ghi trong spec —
       DCA là lưới an toàn hiếm dùng, tranche 1 phải tự đứng. Dự án
       TIẾP TỤC bình thường (khớp §10.2 Nhánh 2 nhánh "KHÔNG").
       Phản biện đã ghi nhận: có thể loại một cơ chế thật sự tốt chỉ
       vì chưa đo được. Chấp nhận — quy tắc chỉ áp trong vùng DCA
       CHƯA chứng minh được lợi thế vượt sai số thước; lợi thế mỏng
       đo bằng thước không đáng tin không đủ điều kiện đem ra vốn thật.
   5.2 MỞ KHOÁ PHƯƠNG ÁN ĐẮT (tự xây bộ mô phỏng khớp lệnh ngoài
       Freqtrade) — CHỈ khi CẢ HAI cùng đúng:
          (a) người thắng ĐỔI giữa hai chiều (mục 4), VÀ
          (b) lợi thế THÔ của DCA trước hiệu chỉnh ≥ 20% — dùng lại
              đúng hằng số Nhánh 2, 0 DOF mới. ("Lớn" không được để
              mơ hồ — mơ hồ chính là tội mục 4 vừa cấm.)
       Bộ mô phỏng tự nó cần kiểm chứng ⇒ thêm một vòng phụ thuộc;
       chi phí chỉ có lý khi phần thưởng đủ lớn.
   5.3 KHÔNG CHẤP NHẬN: nới mục 4 sau khi thấy kết quả; chọn DCA vì
       "đã đầu tư nhiều công sức"; dùng lookahead-analysis sạch làm
       bằng chứng không-có-vấn-đề (LD-15).

════ 6. QUAN HỆ VỚI ĐIỀU KIỆN DỪNG ════
   Bản nháp yêu cầu "sửa điều kiện dừng bị đảo chiều (Z0 thắng →
   halt)" cùng lần sửa này. ĐÃ SỬA TỪ v6: §10.2 hai nhánh — Z0 thắng
   Nhánh 2 = dự án tiếp tục, không có điều khoản dừng. v8 chỉ giữ
   TEST khoá chống hồi quy (L-Z57), không sửa gì thêm.
```

**Test khoá cứng — xem L-Z56 → L-Z58 (§9c.6).**

---

## 9c.0. Ngân sách trial, registry và lockbox

> Chèn ngay sau PHẦN 9b, trước PHẦN 10.

## 9c.1. Vì sao đây là phần chặn D0.9, không phải thủ tục hành chính

§10.2 hiện yêu cầu `DSR-adjusted expectancy ≥ 20%`. DSR là hàm của số trial `N`. v3 không định nghĩa `N` ở bất kỳ đâu → điều kiện GATE không tính được → **GATE D0.9 hiện không phải một phép kiểm tra, mà là một câu chữ**. Phần này gỡ đúng chỗ đó.

## 9c.2. `trial_registry` — schema cho Tool D

Gỡ LỖI 3. Định dạng JSONL, mỗi dòng một trial, append-only.

```jsonc
{
  "trial_id":        "D-0001",
  "tool_id":         "D",
  "registered_at":   "2026-09-05T09:00:00Z",   // TRƯỚC khi chạy
  "executed_at":     "2026-09-05T14:22:00Z",   // sau khi chạy
  "budget_line":     "B1",                      // B0 pool | B1 calib | B2 ablation | B3 dự phòng
                                                 // | CTRL (điểm kiểm soát §0d.4, KHÔNG tính vào N)
                                                 // 🔴 v7: v6 sót B0 dù DR-010 đã tách
  "hypothesis_slot": "A-03",                    // slot ở NGÂN SÁCH A (§9c.3)
  "direction":       "LONG",                    // LONG | SHORT
  "dataset":         "CALIB",                   // CALIB | WFO | LOCKBOX
  "param_under_test": "zss_threshold",
  "param_value":      0.55,
  "params_frozen_hash": "sha256…",              // toàn bộ tham số còn lại
  "config_hash":      "sha256…",                // hash cấu hình đầy đủ
  "code_commit":      "a1b2c3d",
  "provenance": {                               // 🆕 v7 — §0d.5, BẮT BUỘC (L-Z40)
    "params_source":         "yaml",
    "params_effective_hash": "sha256…",
    "reproducible_from_sha": true,
    "data_hashes":           {"pool_100.csv": "sha256…", "oi.parquet": "MISSING"},
    "cache_mode":            "none",
    "guard_passed":          true
  },
  "contribution":     1,                        // 🆕 v8 — DR-014 §4: mức đóng góp
                                                 //   khai TRƯỚC khi chạy. Lần chạy
                                                 //   đơn cấu hình = 1; lô nhiều cấu
                                                 //   hình = số cấu hình. Không khai
                                                 //   được → bộ chạy TỪ CHỐI (fail-closed)
  "state":            "CONSUMED",               // 🆕 v8 — DR-014: RESERVED |
                                                 //   CONSUMED | REFUNDED
                                                 //   (THAY cờ `aborted` của v7)
  "seal_path":        "runs/D-0001/metrics.seal",// 🆕 v8 — con dấu đo lường, DR-014 §3
  "refund_cause_machine": null,                 // 🆕 v8 — CHỈ máy điền (exit code /
                                                 //   exception / guard-block), DR-014 §3
  "outcome": {
    "expectancy": null,        // ĐIỀN SAU KHI CHẠY, không được sửa
    "sharpe": null,
    "n_trades": null,
    "max_single_loss_ratio": null
  },
  "verdict":          "REJECTED",               // KEPT | REJECTED | INCONCLUSIVE
  "rejection_reason": "win rate giảm 6pp so với 0.50, không bù bằng RR",
  "retest_forbidden": true                      // thay cho "failed-hypothesis log"
}
```

**Ba quy tắc thực thi:**

```
1. `registered_at` PHẢI có trước `executed_at`. Bản ghi nào có
   registered_at rỗng hoặc muộn hơn executed_at = VI PHẠM, đánh dấu
   trial đó là contaminated và VẪN tính vào N.
2. `outcome` chỉ được ghi MỘT LẦN. File append-only, phát hiện sửa
   dòng cũ = toàn bộ registry mất hiệu lực.
3. `retest_forbidden: true` thay thế hoàn toàn khái niệm
   "failed-hypothesis log" của đề xuất gốc — KHÔNG tạo thêm file mới,
   KHÔNG nhét vào DR. Một query trên registry là đủ.

4. 🔴 v8 — THẾ NÀO LÀ "ĐÃ TIÊU MỘT TRIAL": xem DR-014 (thay toàn bộ
   quy tắc 4 của v7). Tóm tắt để đọc registry:
      • Mốc tiêu = khoảnh khắc đầu tiên BẤT KỲ chỉ số nào trở nên đọc
        được (con dấu đo lường do BỘ CHẠY tự ghi, trước cả khi in).
      • state: RESERVED (chiếm ngân sách, chưa vào N_ĐÃ_DÙNG) →
        CONSUMED (không hoàn tác) hoặc REFUNDED (chỉ khi KHÔNG có con
        dấu, nguyên nhân do MÁY xác định, trần 3 lần/giả thuyết).
      • Không có "nửa trial". Không có quyền phủ quyết của người vận
        hành ở cả hai chiều.
   → L-Z11 đếm N_ĐÃ_DÙNG = Σ contribution của các dòng state==CONSUMED.
   🔴 Điểm v7 nói MƠ HỒ, v8 nói thẳng: cơ chế v7 dựa trên
   `abort_evidence` do người nộp — vẫn là LỜI KHAI có kèm tang vật.
   DR-014 đảo chiều: bộ chạy tự ghi con dấu và tự ghi nguyên nhân
   dừng; người vận hành không có đường nhập liệu nào vào hai trường đó.
```

> 🔴 **Vì sao không gộp vào DR:** DR là hợp đồng kiến trúc bất biến, số lượng nhỏ, đọc bởi người. Registry là sổ đếm cơ học, số lượng hàng trăm, đọc bởi script. Gộp lại làm DR phình thành nhật ký nghiên cứu và mất chức năng gốc.

## 9c.3. Ngân sách trial — xem DR-010

`N_ĐĂNG_KÝ = 114` (B0=4, B1=72, B2=18, B3=20). Kiểm kê đầy đủ, bảng đối chiếu và ba quy tắc bất biến ở **DR-010**. Danh sách tham số là `tool_d_config.yaml` (§6.9.5), **không lặp lại ở đây** — đó chính là cơ chế đã gây ra đợt lệch số của v5.

> 🔴 **v6 — các ghi chú kế toán của v3.1/v3.2/v4 ở mục này đã bị xoá.** Chúng ghi `B1 144→150`, `B2 10→14`, `N 174→184→192→194` — toàn bộ đã lỗi thời sau khi kiểm kê được làm lại ở DR-010. Giữ lại chỉ tạo thêm số để đối chiếu nhầm.

## 9c.4. Lockbox — xem DR-011

Ba tập CALIB / WFO / LOCKBOX, bốn điều kiện chất lượng (a)-(d), cơ chế niêm phong bằng SHA-256 + access log. Chi tiết ở **DR-011**.

```
🚪 GATE MỚI — chặn trước D1 (không phải trước D4):
   Phải hoàn tất TRƯỚC KHI chạy backtest đầu tiên (bước D0-PRE):
      ✅ `lockbox_seal.json` đã commit, chứa T0/T1/T2/T3 + hash
      ✅ Bốn điều kiện chất lượng (a)-(d) của DR-011 đã kiểm và ghi lý do
      ✅ `trial_registry.jsonl` đã tạo, schema §9c.2
      ✅ N_ĐĂNG_KÝ đã chốt và commit
      ✅ Danh sách tham số ĐÓNG BĂNG đã chốt, có frozen_rationale
   Thiếu MỘT mục → không được chạm dữ liệu.
```

## 9c.4b. 🆕 v3.3 — TẬP EXPLORE: phân vùng thứ tư, dành cho SINH giả thuyết

```
VẤN ĐỀ v3.2 để lại: quy tắc "không xem số liệu" chặn nhầm cả phân tích
cấu trúc thị trường — trong khi giả thuyết TỐT phải dựa trên số liệu,
không phải suy diễn trên giấy.

GIẢI PHÁP: một phân vùng dữ liệu thứ tư, chỉ dùng để SINH giả thuyết.

   ┌───────────┬──────────────────────────────┬─────────────────────┐
   │ Tập       │ Nội dung                     │ Dùng cho            │
   ├───────────┼──────────────────────────────┼─────────────────────┤
   │ EXPLORE   │ BTC + ETH (§0.3b: giữ dữ     │ 🆕 SINH giả thuyết  │
   │           │ liệu, không giao dịch)       │ Phân tích KHÔNG     │
   │           │ + mọi coin TRƯỢT tiêu chí    │ giới hạn, 0 trial   │
   │           │ pool §0.3                    │                     │
   ├───────────┼──────────────────────────────┼─────────────────────┤
   │ CALIB     │ pool giao dịch, [T0…T1]      │ Calibration (B1)    │
   │ WFO       │ pool giao dịch, [T1…T2]      │ WFO + Ablation (B2) │
   │ LOCKBOX   │ pool giao dịch, [T2…T3]      │ Xác nhận, 1 lần     │
   └───────────┴──────────────────────────────┴─────────────────────┘

🔴 HAI RÀNG BUỘC CỨNG:
   (a) EXPLORE KHÔNG BAO GIỜ dùng để validate bất cứ thứ gì
   (b) Coin nào đã ở EXPLORE thì KHÔNG BAO GIỜ được đưa vào pool giao
       dịch sau này — kể cả khi nó bắt đầu thoả tiêu chí §0.3.
       Không có ngoại lệ; ngoại lệ sẽ biến EXPLORE thành tập train.

✅ VÌ SAO SẠCH: đây không phải dữ liệu mà Tool D được ĐÁNH GIÁ trên đó.
✅ VÌ SAO DÙNG ĐƯỢC: cơ chế thị trường (hấp thụ, funding, OI, cấu trúc
   phiên) mang tính phổ quát đủ để giả thuyết tìm thấy ở đây có nghĩa
   ở pool giao dịch.

⚠️ GIỚI HẠN — ghi nhận thẳng, không giả vờ sạch tuyệt đối:
   BTC/ETH tương quan 0.7-0.85 với altcoin. EXPLORE KHÔNG độc lập
   hoàn toàn với pool giao dịch. Nó tốt hơn NHIỀU so với khai thác
   trên tập đánh giá, nhưng không miễn phí về mặt lý thuyết. Một giả
   thuyết tìm thấy trên EXPLORE vẫn phải TRẢ TRIAL đầy đủ khi được
   kiểm chứng trên pool giao dịch — EXPLORE miễn phí ở bước SINH,
   không miễn phí ở bước KIỂM CHỨNG.
```

## 9c.5. Người vận hành — ràng buộc thay cho "LLM không được thấy metric"

Đề xuất gốc nhắm sai đối tượng: **không có LLM nào trong vòng lặp Tool D**. Người nhìn metric rồi chỉnh tham số là **người vận hành**. §9.3 đã tự thừa nhận đây là rủi ro con người.

```
Cơ chế "cổng thống kê lọc trước khi cho xem" KHÔNG KHẢ THI với vận
hành một người — không thể "chưa nhìn" thứ mình vừa chạy.

Thay thế bằng cơ chế KHẢ THI: ĐĂNG KÝ QUY TẮC QUYẾT ĐỊNH TRƯỚC.

   Trước mỗi trial, điền vào registry TRƯỚC khi chạy:
      • Ngưỡng PASS cụ thể bằng số
      • Hành động nếu PASS / nếu FAIL
   Sau khi chạy, đọc kết quả và áp quy tắc MÁY MÓC.

   ❌ Cấm: "kết quả 18%, gần 20% rồi, chắc do mẫu ngắn, nới xuống 15%"
      → đây là hành vi phá vỡ toàn bộ giá trị của việc đăng ký trước,
        và là hành vi mà một người làm việc một mình DỄ TỰ THA THỨ NHẤT.
```

## 9c.6. Test bắt buộc

```
L-Z10 🆕 Mọi bản ghi trial_registry có registered_at < executed_at    🔴 CRITICAL
L-Z11 🆕 Tổng số trial ĐÃ DÙNG ≤ N_ĐĂNG_KÝ tại mọi thời điểm
L-Z12 🆕 Không có config_hash nào xuất hiện 2 lần với outcome khác nhau
      (nếu có → có chạy lại không ghi sổ, registry mất hiệu lực)
L-Z13 🆕 lockbox_access.log có ĐÚNG 0 bản ghi cho tới sau D9;
      🔴 v7 sửa: sau đó ĐÚNG 1 bản ghi CHO MỖI ĐOẠN NIÊM PHONG, tối đa
      3 đoạn (1 gốc + 2 gia hạn INCONCLUSIVE, DR-011). Mỗi bản ghi phải
      trỏ tới một `lockbox_seal_<n>.json` KHÁC NHAU với hash khác nhau.
      Hai bản ghi cùng seal = vi phạm
L-Z14 🆕 SHA-256 dữ liệu lockbox khớp lockbox_seal.json ở MỌI lần kiểm
L-Z15 🆕 Mọi tham số [CẦN CALIBRATE] đều có TRẠNG THÁI trong registry:
      TUNED (có trial) hoặc FROZEN (có frozen_rationale).
      Không tham số nào ở trạng thái "im lặng"                        🔴 CRITICAL
L-Z16 🆕 Mọi bản ghi idea_queue có data_source ∈ {MECHANISM, EXPLORE}
      VÀ trả lời được cả ba câu của bộ lọc §0.1 (đặc biệt câu "AI TRẢ
      TIỀN"). Bản ghi TOOL_D_RESULTS phải có status=REJECTED  🔴 CRITICAL
L-Z17 🆕 Số slot NGÂN SÁCH A đã tiêu ≤ 5/quý — KHÔNG nới vì có LLM
      hỗ trợ sinh ý tưởng                                             (DR-009)
L-Z18 🆕 v3.2 — KHÔNG có bản ghi lệnh nào với
      hold_duration_bars > max_hold_bars                    🔴 CRITICAL (§4b.6)
L-Z19 🆕 v3.2 — hold_duration_bars ghi ở MỌI lệnh đã đóng, mọi arm,
      kể cả lệnh đóng bằng TP/SL                                      (§4b.6)

🆕 v4 — CƠ CHẾ THỰC THI PHÁN QUYẾT §6.8e (không chỉ tuyên bố văn xuôi):

L-Z20 🔴 CRITICAL — MỘT CÔNG THỨC ĐỊNH CỠ DUY NHẤT
      Với MỌI bản ghi plan, kiểm:
         |planned_risk_usdt − rho_eff × E_D|  <  0.01 × rho_eff × E_D
      Tức rủi ro KẾ HOẠCH phải bằng ngân sách rủi ro, sai số < 1%.
      → Nếu code lỡ triển khai công thức VỐN cố định (đã xoá ở §6.2),
        planned_risk_usdt sẽ BIẾN THIÊN theo R_eff và test này FAIL.
      → Đây là cách phán quyết §6.8e được THỰC THI. Không có test này,
        phán quyết chỉ là một câu trong tài liệu, không ràng buộc code.

L-Z21 🆕 Không có bản ghi nào tham chiếu `max_open_D` như một hằng số
      cấu hình — grep toàn bộ code: KHÔNG được có biến `max_open_D`
      đọc từ config                                                (§6.8d)

L-Z22 🆕 Với MỌI thời điểm có vị thế mở, kiểm CẢ HAI:
         Σ planned_risk  ≤ daily_loss_budget_pct × E_D
         Σ planned_margin ≤ 0.85 × E_D
      Tính trên KẾ HOẠCH đầy đủ 3 tranche (D0.3/D0.5), không phải
      phần đã khớp                                          (§6.8f)  🔴 CRITICAL

🆕 v6 — CHỐNG TÁI DIỄN LỖI KIỂM KÊ DOF (nguyên nhân gốc của v5):

L-Z29 🔴 CRITICAL — KẾ TOÁN BẬC TỰ DO TỰ KIỂM
      (a) số khoá trong `tier_frozen` == số bản ghi có
          `frozen_rationale` trong trial_registry
      (b) |tier_b| + |mục đã xoá| + |Σ dof(tier_frozen)| + |B0|
          == DOF_gốc đã commit ở D0-PRE
      (c) N_ĐĂNG_KÝ == 4 + 3×|tier_b|×2 + |arm B2|×2 + 20
      Lệch ở bất kỳ vế nào → CHẶN CHẠY, không cảnh báo suông.
      → Đây là cách duy nhất để lỗi "26 − 9 = 16" không lặp ở v7.

L-Z30 🔴 CRITICAL — KHÔNG có lệnh đã đóng nào với
      funding_paid_cumulative > 0.35 × R_eff_plan          (§4c.4)
L-Z31 funding_paid_cumulative ghi ở MỌI lệnh đã đóng, mọi arm  (§4c.4)
L-Z32 KHÔNG có tham chiếu tới `L_D_max`, `mult_cross`, `L_BASE`,
      `max_open_D` trong code hay config — grep toàn repo   🔴 CRITICAL
      (bốn thứ đã bị XOÁ; còn sót = hai nguồn sự thật)
L-Z33 KHÔNG có tham chiếu tới khung 15m trong strategy hay config
      (§3.3c đã xoá). Timeframe hợp lệ: 1H chính; 4H/1D informative
      ghép LÊN bằng merge_informative_pair; 5m chỉ dùng cho
      `timeframe_detail` của backtest engine              🔴 CRITICAL

🆕 v7 — N PHẢI NỐI VÀO CODE, NGƯỠNG PHẢI FAIL-CLOSED (LD-30, LD-31):

L-Z34 🔴 CRITICAL — N KHÔNG PHẢI SỐ TRANG TRÍ.
      Test tham số hoá: gọi hàm tính ngưỡng DSR với N=114 và với
      N=228; hai đầu ra PHẢI khác nhau và khớp √(2·ln N) trong sai số
      1e-6. Đầu ra không đổi khi N đổi → N đang nằm trong chú thích,
      không nằm trong phép tính. Tool A tin một con số DOF trong 4
      tháng trước khi phát hiện nó không đi vào phép tính nào.
      → N đọc từ trial_registry (🔴 v8: Σ contribution của dòng
        state==CONSUMED, cộng nền N_ĐĂNG_KÝ theo DR-010/§12c.2),
        KHÔNG từ hằng số trong code, KHÔNG từ tài liệu.
L-Z35 🔴 CRITICAL — PLACEHOLDER FAIL-CLOSED.
      Mọi ngưỡng GATE chưa được điền bằng DR (hiện: DSR-adjusted
      expectancy ở Nhánh 1 §10.2; ngưỡng lệch khớp D6 ở §9b.3) PHẢI
      là +inf trong code (hoặc −inf tuỳ chiều), KHÔNG phải None,
      KHÔNG phải 0. Gate KHÔNG THỂ VÔ TÌNH PASS.
      Kèm test khoá cứng: "kết quả tốt nhất hiện có vẫn FAIL" — chạy
      lại mỗi lần thay ngưỡng, chống hồi quy về trạng thái "gần đạt".
      Khi chốt ngưỡng thật, DR phải viết TRƯỚC khi biết kết quả lần
      đánh giá tiếp theo, và nêu rõ hệ quả: "chốt ngưỡng này đồng
      nghĩa thừa nhận hệ thống hiện CHƯA qua gate".

🆕 v8 — SỔ HAI TRẠNG THÁI (DR-014) & CỔNG SAI LỆCH (DR-015):

L-Z52 🔴 CRITICAL — Khởi chạy khi KHÔNG có đặt chỗ hợp lệ, hoặc khi
      Khả dụng < contribution khai báo → bộ chạy TỪ CHỐI, exit ≠ 0,
      không chạm dữ liệu. Đổi contribution khai báo → Khả dụng đổi
      tương ứng (chống số-trang-trí, LD-30).
L-Z53 🔴 CRITICAL — Giết tiến trình SAU khi kết quả fold/epoch đầu
      tồn tại → con dấu ĐÃ có → state = CONSUMED; gọi thẳng hàm hoàn
      trả với trial đó → hàm RAISE, không trả lại được.
L-Z54 — Guard 0d.1 chặn trước khi chạy → state = REFUNDED,
      refund_cause_machine != null do máy điền, N_ĐÃ_DÙNG KHÔNG đổi.
      Lần trả lại thứ 4 cho cùng một giả thuyết → CONSUMED (trần
      DR-014 §5). Mô phỏng cả bốn dòng bảng phân loại DR-014 §5.
L-Z55 — Mọi lần chạy dòng CTRL / EXPLORE có assert timerange-tập-dữ
      liệu do BỘ CHẠY tự kiểm PASS trong log; thiếu assert → lần chạy
      đó bị coi là chạm tập đánh giá → phải có đặt chỗ (fail-closed).
L-Z56 🔴 CRITICAL — Chạy bất kỳ arm ablation nào khi chưa có kết quả
      Δ_R của cổng D3.5 (cả ba bước, cả hai hướng) đã commit → bộ
      chạy TỪ CHỐI (DR-015 §1).
L-Z57 🔴 CRITICAL — Bộ kết quả giả lập "Z0 vượt trội mọi arm DCA" đưa
      qua GATE §10.2 → kết cục = "chọn Z0, dự án TIẾP TỤC", KHÔNG có
      đường nào dẫn tới DỪNG DỰ ÁN (khoá chống hồi quy về lỗi v5).
L-Z58 — Hiệu chỉnh hai chiều (DR-015 §4) trên bộ giả lập có chênh
      lệch NHỎ hơn Δ_R → hệ thống kết luận "KHÔNG PHÂN XỬ ĐƯỢC" và
      chọn Z0 theo §5.1, không chọn DCA; trên bộ có chênh LỚN hơn →
      kết luận không đổi giữa hai chiều và biên hiệu chỉnh được ghi
      kèm kết quả.
```

---

## 9c.7. 🆕 IDEA QUEUE — hàng chờ giả thuyết Loại A

> Thực thi DR-009 Loại A. Đây là **hàng chờ**, không phải hàng thực thi: vào queue **không tiêu trial nào**; chỉ khi được chọn ra để chạy mới tiêu 1 slot NGÂN SÁCH A.

### 9c.7.1. Vì sao cần queue mà KHÔNG nới ngân sách

```
🔴 Điểm dễ hiểu nhầm nhất: Idea Queue KHÔNG làm tăng thông lượng
   nghiên cứu. Nút thắt của Tool D không nằm ở nguồn cung ý tưởng.

   Nguồn cung ý tưởng     → vô hạn, không phải nút thắt
   Trial budget           → 114, HẾT LÀ HẾT          🔴 nút thắt
   Thời gian kiểm chứng   → ~8 tuần/chiến lược        🔴 nút thắt
   Lockbox chưa bị nhìn   → có ĐÚNG MỘT, chạm 1 lần  🔴 nút thắt cứng nhất

   → Tăng cung ý tưởng từ 5/quý lên 50/ngày KHÔNG làm gì cả.
   → Tệ hơn: khi có 50 ứng viên mà chỉ chạy được 5, BƯỚC CHỌN trở
     thành nơi overfitting xảy ra, và nó VÔ HÌNH vì không ai ghi sổ
     cho bước chọn.

🚪 Vì vậy: trần NGÂN SÁCH A giữ nguyên 5 giả thuyết/quý, dùng chung
   Tool A + Tool D (§9.3). Có LLM hay không, con số này KHÔNG ĐỔI.
   Queue chỉ làm một việc: khiến bước CHỌN trở nên hữu hình và có
   tiêu chí ghi trước.
```

### 9c.7.2. Giá trị thật của queue: chống "tù kiến thức" có kiểm soát

```
Rủi ro "tù kiến thức" (edge chết khi regime đổi) là RỦI RO THẬT —
spec đã tự thừa nhận qua §6.2 hệ số 5 (edge decay).

Nhưng thuốc chữa KHÔNG PHẢI là nới lỏng vòng lặp nghiên cứu:

   ❌ Sai thuốc: "phân tích linh hoạt nhiều yếu tố" — một hệ linh hoạt
      là một hệ KHÔNG THỂ BÁC BỎ; không có tiêu chí nói nó sai nên
      không bao giờ biết nó sai. Bạn đã chọn phía kia của đánh đổi
      này một cách có ý thức khi viết D0 và DG1-DG7.

   ✅ Đúng thuốc: CHẤP NHẬN chiến lược sẽ chết, có sẵn quy trình khai
      tử + thay thế. Ba mảnh đã có trong spec, chỉ chưa nối lại:
         • §6.2 hệ số 5 (edge decay)  → phát hiện edge chết
         • DR-012 Hạng 2               → quy trình đổi, có tính phí trial
         • NGÂN SÁCH A còn slot trống  → nguồn ứng viên thay thế
      Idea Queue là mảnh thứ tư: NƠI CHỨA ứng viên thay thế, đã qua
      lọc, sẵn sàng khi cần — thay vì phải nghĩ vội lúc đang thua.

   🔴 Chết có kiểm soát ≠ liên tục sửa để khỏi chết.
```

### 9c.7.3. Schema `idea_queue.jsonl`

Append-only, cùng thư mục với `trial_registry.jsonl`.

```jsonc
{
  "idea_id":         "IQ-0007",
  "created_at":      "2026-09-10T08:00:00Z",
  "source":          "LLM",                 // LLM | HUMAN | EXTERNAL
  "session_type":    "IDEA",                // BẮT BUỘC = "IDEA" (DR-009)
  "data_source":     "EXPLORE",             // 🆕 v3.3 — thay `contaminated`
                                            // MECHANISM | EXPLORE  → hợp lệ
                                            // TOOL_D_RESULTS       → LOẠI
  "explore_evidence": "…",                  // 🆕 BẮT BUỘC nếu data_source
                                            // = EXPLORE: nêu rõ đã phân tích
                                            // gì, trên coin/khoảng nào
  "title":           "…",

  // Bộ lọc §0.1 — cả ba PHẢI có nội dung, không được để rỗng
  "mechanism":       "ai làm gì tạo ra dịch chuyển giá",
  "who_pays":        "ai là người thua ở phía bên kia",   // 🔴 câu giết ý tưởng
  "durability":      "vì sao chưa bị arbitrage hết",

  "filter_verdict":  "PASS",                // PASS | FAIL_NO_PAYER | FAIL_MECHANISM
                                            //      | FAIL_DURABILITY | DUPLICATE
  "overlaps_with":   ["DR-005 mean-reversion"],  // đối chiếu ứng viên đã loại

  "status":          "QUEUED",              // QUEUED | SELECTED | ARCHIVED | REJECTED
  "selected_at":     null,
  "budget_a_slot":   null,                  // điền khi SELECTED, vd "A-04"
  "selection_reason": null                  // 🔴 BẮT BUỘC khi SELECTED — xem 9c.7.4
}
```

### 9c.7.4. Quy tắc chọn ra khỏi queue — chỗ dễ rò rỉ nhất

```
🔴 v3.3 — LỖ HỔNG TỰ PHÁT HIỆN TRONG DR-009:

   DR-009 bịt mắt LLM nhưng KHÔNG bịt mắt NGƯỜI CHỌN.
      LLM mù kết quả → sinh 50 ý tưởng sạch → BẠN chọn 5
                                                ↑
                                    Bạn ĐÃ XEM hết kết quả Tool D.
                                    Bước CHỌN bị nhiễm 100%.
   → Toàn bộ số trial ngầm chuyển từ LLM sang bước chọn, và vẫn
     KHÔNG ĐO ĐƯỢC. Bịt mắt agent mà không bịt mắt người chọn chỉ
     chuyển vấn đề sang chỗ ít được quản trị hơn.

🚪 CHỌN MÙ HAI BƯỚC — bắt buộc:
   1. TRƯỚC khi mở queue: viết tiêu chí chọn cho quý này (VD "ưu tiên
      cơ chế độc lập với thanh khoản zone"), commit vào git
   2. Chấm điểm từng ý tưởng THEO ĐÚNG tiêu chí đó, KHÔNG thêm tiêu chí
   3. `selection_reason` phải TRÍCH tiêu chí đã commit, không viết mới

🚪 TRẦN NHẬP QUEUE: 10 ý tưởng/quý.
   Lý do: với LLM, chi phí sinh ý tưởng ≈ 0 → queue có thể có 100 ý
   tưởng/tuần trong khi trần chọn vẫn 5/quý. Tỉ lệ chọn 5% biến bước
   CHỌN thành nơi khai thác dữ liệu quy mô lớn. Chặn ở NGUỒN rẻ hơn
   và hữu hình hơn chặn ở đầu ra.

🔴 Ba ràng buộc gốc, vẫn giữ nguyên:

   (1) `selection_reason` phải viết BẰNG CƠ CHẾ KINH TẾ, không được
       tham chiếu bất kỳ kết quả định lượng nào của Tool D.
       ❌ "chọn vì Tool D đang thua ở regime sideway"  ← Loại B trá hình
       ✅ "chọn vì cơ chế của nó độc lập với thanh khoản zone"

   (2) Chọn tối đa 1 ý tưởng/quý ra khỏi queue, đúng bằng nhịp
       NGÂN SÁCH A. Không dồn slot, không chọn bù.

   (3) Ý tưởng bị FAIL ở bộ lọc §0.1 chuyển `status: REJECTED` và
       KHÔNG được nộp lại dưới tên khác. Trước khi thêm ý tưởng mới,
       query queue theo `mechanism` để phát hiện trùng lặp —
       tương đương `retest_forbidden` của trial_registry (§9c.2).

⚠️ Thừa nhận thẳng: (1) không thực thi được bằng máy, chỉ bằng kỷ luật.
   Nhưng buộc phải VIẾT RA lý do chọn làm cho việc tự lừa mình trở nên
   khó hơn đáng kể so với chọn trong đầu rồi hợp lý hoá sau.
```

### 9c.7.5. Điều KHÔNG được dùng queue để làm

```
❌ Không dùng queue để biện minh cho việc chạy nhiều chiến lược song
   song bằng "vốn thử nghiệm ít tiền".
   Lý do định lượng: với t ≈ Sharpe × √T (T tính bằng năm), để phân
   biệt Sharpe thật = 1.0 khỏi nhiễu ở mức t ≈ 2 cần ~4 NĂM dữ liệu
   live; Sharpe = 2.0 cần ~1 năm. Vốn nhỏ giới hạn THIỆT HẠI, không
   giới hạn SAI LẦM THỐNG KÊ. Chạy 10 ứng viên song song bằng tiền
   thật = multiple testing với power THẤP HƠN backtest.
   → Live vốn nhỏ (D12) giữ đúng vai trò cũ: kiểm chứng VẬN HÀNH,
     không phải kiểm chứng EDGE.

❌ Không dùng queue để né lockbox. Mỗi ứng viên được chọn cần một
   lockbox trên dữ liệu CHƯA TỪNG DÙNG (DR-011, DR-012 Hạng 2).
   Không có dữ liệu sạch → không có ứng viên mới. Đây là ràng buộc
   cứng nhất và là lý do trần 5/quý không thể nới dù có LLM.
```

---

---

# PHẦN 10 — GATE

## 10.1. 🔴 D0.9 — Ablation, giờ phải chứng minh BA mệnh đề

> 🆕 **Nâng cấp sau phản biện về entry quality + DG6.** Mọi cấu hình Z0-Z3 dưới đây giờ dùng xác nhận entry tranche 1 (§3.3b) làm mặc định — so sánh công bằng, vì thiếu xác nhận entry sẽ làm win rate MỌI cấu hình thấp giả tạo, không riêng gì Z0.

Thiết kế trước tách hai câu hỏi (zone-anchor, DCA). Giờ thêm câu hỏi thứ ba (DG6 — early exit) và làm rõ triết lý cốt lõi: **Z0 chính là phép thử "có cần DCA hay không" mà bạn muốn** — nếu Z0 (entry đơn, có xác nhận, neo zone) đã đủ tốt, Tool D trở thành hệ thống single-entry, DCA chỉ còn là lưới an toàn ít dùng.

| # | Cấu hình | Câu hỏi tách riêng |
|---|---|---|
| **Z0** | Entry đơn tại p1, có xác nhận entry (§3.3b), SL = zone-based, full size | Baseline — CHỈ zone + xác nhận entry, KHÔNG DCA. **Đây là ứng viên bạn thật sự muốn nếu nó đủ mạnh** |
| **Z1** | Entry đơn, xác nhận entry, SL = 2.2×ATR cố định (kiểu v1) | Zone-SL có tốt hơn ATR-multiplier-SL không? |
| **Z2** | 3 tranche neo zone, xác nhận entry ở tranche 1, không DG5, không mult_zss | Chia tranche có giá trị so với Z0 không? |
| **Z3** | 3 tranche đầy đủ DG1-DG5, mult_zss, KHÔNG DG6 | "Phần Smart" của DCA có giá trị? |
| **Z3b** | 🆕 Như Z3, CỘNG DG6 (Early Invalidation, §4.1) | DG6 có cải thiện risk-adjusted outcome không, đánh đổi expectancy ra sao? |

```
Đọc kết quả:
   Z0 > Z1  ?  →  SL neo zone tốt hơn ATR-multiplier
   Z2 > Z0  ?  →  Chia tranche có giá trị
   Z3 > Z2  ?  →  DG5 + mult_zss có giá trị đo được
   Z3b vs Z3 ?  →  DG6 giảm max_single_loss/CVaR bao nhiêu, đổi lấy
                    bao nhiêu expectancy — ĐÂY LÀ ĐÁNH ĐỔI, không phải
                    "Z3b luôn thắng"

🔴 NẾU Z0 ≥ Z3 (hoặc Z3b):  GIỮ Zone Absorption, BỎ DCA — Tool D trở
   thành hệ thống single-entry-neo-zone. Đây là kết quả TỐT, đúng
   hướng bạn muốn ("không muốn DCA, rất rủi ro") — không phải thất
   bại của dự án.

   🔴 v6 — SỬA MÂU THUẪN NGHIÊM TRỌNG NHẤT CỦA v5:
      Câu trên nói "kết quả TỐT", nhưng §10.2 (v5) đặt "{Z3,Z3b} vượt
      Z0 ≥ 20%" làm TIÊU CHÍ ĐẦU TIÊN của GATE, và kết bằng "Thiếu
      MỘT tiêu chí → DỪNG". Tức là: kết cục được mô tả là tốt nhất
      lại KÍCH HOẠT ĐIỀU KHOẢN DỪNG DỰ ÁN.
      Nặng hơn: v5 KHÔNG có tiêu chí PASS độc lập nào cho Z0. Toàn bộ
      §10.2 là so sánh TƯƠNG ĐỐI Z3 vs Z0 — nên Z0 có thể "thắng" Z3
      mà vẫn là một hệ thống thua tiền, và GATE không phát hiện được.
      → §10.2 được viết lại thành HAI NHÁNH ở v6.
🟡 NẾU Z0 > Z2 nhưng Z3(b) > Z0:  phần "Smart" đang GÁNH cho DCA yếu
   — kiểm tra out-of-sample riêng cho DG5/ZSS/DG6 trước khi tin.
```

> 🔴 **Bắt buộc chạy TÁCH RIÊNG theo hướng (§3.3d):** toàn bộ bảng Z0-Z3b ở trên phải chạy **hai lần độc lập** — một cho Long, một cho Short — không giả định kết quả Long tự động áp dụng cho Short (funding, biến động nền, short squeeze là ba bất đối xứng đã nêu ở §3.3d). Nếu giới hạn thời gian, ưu tiên Long trước (đối xứng tự nhiên hơn với hầu hết chỉ báo), Short chạy sau khi có DG7 và ngưỡng riêng đã calibrate.

## 10.1b. 🆕 Arm kiểm chứng bộ lọc trend

> Gỡ **LỖI 9**. Chèn ngay sau §10.1, trước §10.2.

```
🔴 VẤN ĐỀ: cả năm cấu hình Z0-Z3b đều CHỨA NGUYÊN Phần 2 — bốn điều
   kiện lọc (trend_dir 1D + xác nhận 4H + ADX≥20 + tuổi ≥5 ngày).
   Không arm nào bật/tắt chúng. Nếu tầng 1D vô dụng, hoặc có hại vì
   lọc mất setup tốt, thiết kế ablation hiện tại KHÔNG PHÁT HIỆN ĐƯỢC.
```

| # | Cấu hình | Câu hỏi tách riêng |
|---|---|---|
| **Z0-T0** | Zone + xác nhận entry (§3.3b), **KHÔNG bộ lọc trend nào** | Phần 2 có đóng góp gì không? Nếu Z0-T0 ≈ Z0, bốn điều kiện lọc đang chỉ làm **giảm số mẫu** mà không tăng chất lượng |
| **Z0-T1** | Chỉ giữ **4H** (§2.2). Bỏ tầng 1D: bỏ §2.1 hướng-1D, bỏ ADX(1D)≥20, bỏ tuổi trend ≥5 ngày | 🔴 **Arm quan trọng nhất:** tầng 1D có giá trị RIÊNG, hay §2.2 (4H) đã chứa hết thông tin? Đây là arm trả lời trực tiếp câu hỏi "khung thời gian có khớp hold không" |
| **Z0-T2** | Đầy đủ Phần 2 = **Z0 hiện tại** | Mốc so sánh — không phải arm mới, không tốn trial thêm |
| **Z0-S1** 🆕 v4 | Như Z0 nhưng **notional CỐ ĐỊNH** mỗi lệnh, thay vì rủi ro cố định (§6.2) | Định cỡ theo VỐN hay theo RỦI RO tốt hơn? Lập luận ủng hộ vốn cố định: nó KHÔNG phụ thuộc `R_eff` tính đúng — nếu công thức `R_eff` sai, rủi ro-cố-định sai theo, vốn-cố-định thì không. Đây là lập luận **robustness** hợp lệ, đáng đo |
| **Z0-V1** 🔴 v6 — *viết ra lần đầu* | Như Z0 nhưng **TẮT điều kiện (c) volume tại lúc chạm zone** (§3.3b/PHẦN 3b), tức chỉ cần (a) HOẶC (b) | `v_min` có giá trị đo được không? 🔴 v5 tính arm này vào B2 (9 cấu hình) nhưng **chưa bao giờ định nghĩa nó thành một hàng** — một arm được cấp ngân sách mà không có mô tả là một arm không chạy được |

```
Đọc kết quả:
   Z0-T0 ≈ Z0-T2  ?  →  Phần 2 KHÔNG đóng góp. Xem xét bỏ bớt để lấy
                         lại số mẫu — nhưng CẢNH BÁO: bỏ hẳn có nguy
                         cơ thoái hoá thành mean-reversion (DR-005).
                         Ưu tiên rút về Z0-T1 thay vì về Z0-T0.
   Z0-T1 ≥ Z0-T2  ?  →  Tầng 1D KHÔNG có giá trị riêng ngoài 4H.
                         → Bỏ §2.1/2.3/2.5-ADX, giữ §2.2.
                         → Đồng thời GIẢM 3 bậc tự do (tuổi trend,
                           ADX ngưỡng, và "ngược hẳn" ở §2.4 thành
                           vô nghĩa) → N giảm, rào DSR thấp xuống.
   Z0-T1 < Z0-T2  ?  →  Tầng 1D CÓ giá trị veto thật, giữ nguyên
                         Phần 2. Câu hỏi khung thời gian được trả lời
                         bằng số, không bằng lập luận.
   Z0-T0 > Z0-T2  ?  →  🔴 Phần 2 đang GÂY HẠI. Cần điều tra kỹ trước
                         khi tin — nhiều khả năng do mẫu nhỏ ở arm bị
                         lọc chặt. Kiểm tra số lệnh trước khi kết luận.

🚪 Chi phí: 2 arm mới × 2 hướng = 4 trial, tính vào B2.
   🔴 v6 — kế toán cũ của mục này (B2 10→14, N 174→184) đã lỗi thời.
   Con số hiện hành: B2 = 18 (9 cấu hình × 2 hướng), N = 114 (DR-010).

🔴 DG8 (§4b) BẬT trong CẢ Z0-T0 và Z0-T1, cùng max_hold_bars như mọi
   arm khác (§4b.4). DG8 là thuộc tính khung thử nghiệm, không phải
   biến so sánh.

🔴 Chạy TÁCH RIÊNG Long/Short như mọi arm khác (§10.1, §3.3d).

Đọc kết quả Z0-S1:
   Z0-S1 < Z0    →  rủi ro-cố-định thắng, giữ §6.2 nguyên
   Z0-S1 ≈ Z0    →  hai cách tương đương → GIỮ rủi ro-cố-định vì nó
                     cho nhiều lệnh song song hơn với cùng E_D
   Z0-S1 > Z0    →  🔴 tín hiệu R_eff đang tính SAI (phân loại L2,
                     §11b.1), KHÔNG phải "vốn cố định tốt hơn".
                     Điều tra R_eff trước khi đổi cơ chế định cỡ.

🚪 Chi phí: 1 arm × 2 hướng = 2 trial. Đã nằm trong B2 = 18 (DR-010).
```

---

---

## 10.2. Điều kiện GATE D0.9 — 🔴 v6 VIẾT LẠI THÀNH HAI NHÁNH

> **Lỗi của v5 được sửa ở đây:** GATE cũ trộn hai câu hỏi khác loại vào một danh sách AND — *"hệ thống có đủ tốt không"* và *"cấu hình nào tốt hơn"*. Hệ quả: kết cục "Z0 thắng, bỏ DCA" (được §10.1 gọi là kết quả tốt) rơi vào nhánh DỪNG.

```
════════ NHÁNH 1 — NGƯỠNG TUYỆT ĐỐI ════════
Áp cho CẤU HÌNH TỐT NHẤT, bất kể nó là Z0, Z3 hay Z3b.
Đây là câu hỏi "hệ thống có đủ tốt để đem tiền thật ra không".

   ✅ DSR-adjusted expectancy ≥ ......   🔴 PHẢI ĐIỀN SỐ Ở D0-PRE
      🆕 v7: cho tới khi điền, giá trị trong code = +inf (L-Z35).
      Gate này KHÔNG THỂ pass bằng cách quên điền.
      (v5 để trống ô này — đó là lý do GATE chưa từng là một phép
       kiểm tra. Điền TRƯỚC khi chạm dữ liệu, §9c.5.)
      DSR tính với N = N_ĐĂNG_KÝ = 114 (DR-010), KHÔNG phải số trial
      đã dùng, KHÔNG phải số cấu hình ablation.
      Nếu overlap pool ≥ 50% (H14) → DR-007 → N là UNION với Tool A,
      lấy từ trial_registry Tool A tại thời điểm chạy GATE.

   ✅ H4-D + H4-D-b (§7.2/§7.5) PASS
   ✅ liq_buffer_ratio trung bình ≥ 8 xuyên suốt mẫu (§6.4b)
   ✅ max_single_trade_loss / risk_budget ≤ 1.15
   ✅ skewness(cấu hình tốt nhất) không âm hơn skewness(Z1) quá 0.5
   ✅ số lệnh/năm ≥ 150
      🔴 ĐÂY LÀ SÀN, KHÔNG PHẢI TRẦN — ngưỡng tối thiểu để có đủ mẫu.
      Không có giới hạn trên. Ước lượng bằng tính tay ở D0-PRE.
   ✅ Phân bố hold_duration_bars báo cáo cho MỌI arm; tỉ lệ TIME_STOP
      trong dải 5%–25%   🔒 FROZEN, ngưỡng chẩn đoán, không tính vào N
         > 25% → max_hold_bars quá ngắn, cắt trước khi giả thuyết kịp
         < 5%  → DG8 chưa bao giờ ràng buộc, 24 nến chỉ là trang trí
   ✅ 🆕 v6 — Phân bố funding_paid_cumulative / R_eff báo cáo cho MỌI
      arm (L-Z31). Không có ngưỡng chặn ở vòng này — chỉ để biết DG7
      (§4c) có bao giờ ràng buộc không.
   ✅ 🆕 v6 — Tỉ lệ dùng TP_fallback báo cáo (chỉ số H-4, §11b.2).
      > 40% → tiền đề TP sai (L2) → KHÔNG vào live, xử theo §11b.1
   ✅ L-Z10 → L-Z33 (§9c.6, §4b.6, §4c.4) PASS
   ✅ PBO ≤ 0.5 qua CSCV trên 9 cấu hình, tính riêng mỗi hướng
      (H18) — 🟡 P1 ở lần chạy đầu, xem ghi chú dưới

   🔴 THIẾU MỘT TIÊU CHÍ Ở NHÁNH 1 → KHÔNG VÀO LIVE.
      Xử lý theo BA KẾT CỤC của DR-011 (PASS / INCONCLUSIVE / FAIL) —
      "không vào live" KHÔNG đồng nghĩa "dừng dự án".

════════ NHÁNH 2 — CHỌN CẤU HÌNH ════════
CHỈ chạy nếu Nhánh 1 đã PASS. Đây là câu hỏi "cấu hình nào".

   🔴 v8 — TIỀN ĐỀ: cổng D3.5 (DR-015) đã có kết quả Δ_R (Long/Short
   riêng) TRƯỚC khi bất kỳ arm nào chạy (L-Z56). Câu hỏi dưới đây
   được trả lời qua HIỆU CHỈNH CỰC ĐOAN HAI CHIỀU của DR-015 §4 —
   "vượt ≥ 20%" chỉ tính là CÓ khi sống sót Ở CẢ HAI chiều hiệu
   chỉnh. Người thắng đổi giữa hai chiều = backtest không đủ tư cách
   phân xử = rơi vào nhánh "KHÔNG" (mặc định Z0, DR-015 §5.1) — dự án
   TIẾP TỤC bình thường, đây không phải kết cục xấu.

   Tốt nhất trong {Z3, Z3b} vượt Z0 ≥ 20% DSR-adjusted expectancy
   (sống sót qua cả hai chiều hiệu chỉnh Δ_R)?
      ✅ CÓ    → chọn cấu hình DCA đầy đủ.
                 Kèm điều kiện: Z1 < Z0 HOẶC
                 (Z1 ≥ Z0 nhưng liq_buffer(Z0) ≥ liq_buffer(Z1) × 1.3)
      ✅ KHÔNG → chọn Z0, hệ thống SINGLE-ENTRY neo zone.
                 🔴 DỰ ÁN TIẾP TỤC BÌNH THƯỜNG. Đây là kết cục được
                 §10.1 và §3.4b mô tả là ĐÚNG HƯỚNG. Không có điều
                 khoản dừng nào ở nhánh này.
                 → Hệ quả kế toán: bỏ DCA làm chết DG5 và một phần
                   DG1-DG4 → kiểm kê lại DOF và HẠ N cho vòng sau
                   (ghi vào research-log, không tự động áp).

   ✅ Z0-T1 vs Z0-T2 (§10.1b) có kết luận GHI LẠI, dù kết luận là
      "giữ nguyên Phần 2" — không được bỏ trống
   ✅ Đọc kết quả Z0-S1 theo đúng bảng §10.1b (đặc biệt ca Z0-S1 > Z0
      → nghi R_eff tính SAI, KHÔNG phải "vốn cố định tốt hơn")
```

> 🔴 **Vì sao tách hai nhánh là bắt buộc, không phải làm đẹp tài liệu:** một GATE chỉ có hai kết cục (PASS / chết) tạo áp lực gian lận cực lớn đúng tại thời điểm quan trọng nhất, và §9c.5 đã tự thừa nhận rằng người vận hành một mình sẽ nới ngưỡng trong ca "18%, gần 20% rồi". Tách nhánh không làm ngưỡng dễ hơn — Nhánh 1 vẫn tuyệt đối và vẫn phải điền số trước. Nó chỉ đảm bảo **kết cục tốt không bị nhầm thành kết cục xấu**, và đó là chỗ v5 sai.

**Ghi chú về PBO (🟡 P1, không chặn ở lần chạy đầu):** PBO qua CSCV cần ≥ 8 phân hoạch để có ý nghĩa. 🔴 v6: với **9** cấu hình (không phải 5 như v5 ghi), lập luận "quá ít để có power" đã yếu đi đáng kể — nhưng ước lượng vẫn thô vì các arm không độc lập (Z3b ⊃ Z3 ⊃ Z2). Đề xuất thực dụng: **tính và ghi lại PBO nhưng chưa dùng làm điều kiện chặn ở D0.9 lần đầu**; nâng lên P0 ở GATE TOOL D (D9), nơi WFO đã sinh đủ cặp IS/OOS để CSCV có power. Không nên đưa vào như tiêu chí cứng khi biết trước nó thiếu power — đó là thêm nghi thức, không thêm thông tin.

---

---

# PHẦN 11 — HARDENING

> 🆕 **Zero-dependency đã chốt** — không tái dùng bất kỳ module nào của Tool A (`lib/pool-builder`, orchestrator...), kể cả phần đã hardened. Bảng dưới đổi so với đề xuất ban đầu.

| Hạng mục | Trạng thái | Ghi chú |
|---|---|---|
| **H1-D Point-in-time pairlist** | 🔴 **VIẾT LẠI TỪ ĐẦU** | 🆕 v7 — SURVIVORSHIP BIAS (LD-29): API Binance KHÔNG trả symbol đã huỷ niêm yết. H1-D phải có nguồn danh sách lịch sử riêng (snapshot `exchangeInfo` định kỳ, hoặc nguồn ngoài); nếu không có → ghi tường minh vào DR "đang chấp nhận survivorship bias, ước lượng hướng lệch: có lợi" — KHÔNG im lặng. Mỗi lần đổi pool = backfill lại toàn bộ dữ liệu phụ trợ, và MỌI số cũ không so sánh được. Không dùng `lib/pool-builder`. Phải re-verify lookahead từ đầu — đây là hạng mục v10 gọi "đường găng", tốn nhiều tuần nhất ở Tool A. 🔴 v6 — XOÁ yêu cầu cũ "verify cơ chế phân vùng rank 31-60": §0.3 đã BÁC BỎ DỨT KHOÁT cơ chế phân vùng theo rank (nó chọn pool để né overlap DSR — lấy kết luận thống kê làm tiêu chí chiến lược). Đây là tàn dư của thiết kế cũ nằm trong hạng mục hardening quan trọng nhất. Thay bằng: verify pool point-in-time không lệch theo thời gian, và verify ranh giới tập EXPLORE (§9c.4b) không bị rò |
| H2 Portfolio Context | ⚠️ Viết mới, kiến trúc tương tự | Không tái dùng code, nhưng khái niệm giữ. 🔴 v6: **bỏ `mult_cross`** (đã xoá ở §6.2) — H2 KHÔNG cần đọc chéo sub-account Tool A, đúng theo §6.6 |
| **H3-D Walk-forward orchestrator** | 🔴 **VIẾT LẠI TỪ ĐẦU** | 🔴 v7 — thay câu "nguy cơ tái phạm bug" bằng DANH SÁCH CỤ THỂ các bug đã xảy ra ở Tool A mà H3-D PHẢI có test chống lại, trước khi được coi là xong: (1) file tham số ẩn đè default — guard §0d.1; (2) guard bỏ sót entrypoint — L-Z36; (3) `--cache day` mặc định — L-Z38; (4) cache fold không mang hash cấu hình — §0d.3; (5) cộng dồn `profit_ratio` qua fold — DR-013; (6) ghép fold bằng CỘNG thay vì NHÂN — DR-013; (7) bản ghi trùng khi chạy lại cùng timerange — L-Z45; (8) ghi trạng thái ở cuối main nhưng chưa bao giờ chạy tới hết — L-Z51; (9) giá trị lính canh lọt ra báo cáo — L-Z41. Zero-dependency là về CODE, không phải về BÀI HỌC |
| **H4-D Zone lookahead** | 🔴 **MỚI, P0 tuyệt đối** | §7.2/§7.5 — bao gồm caveat Freqtrade issue #12168 (false positive với entry trễ), cộng test causality cho `confirm_ratio` liên tục |
| H5 timeframe-detail 5m | 🔴 Bắt buộc P0, viết mới | Cùng lý do v1 (nhiều mức giá/nến), cộng: xác nhận swing 4H không lệch do intrabar |
| ~~H7 Custom loss~~ | ❌ 🔴 **v7 XOÁ** | "Custom loss function" là khái niệm của **Hyperopt** — module bị CẤM TUYỆT ĐỐI ở §0c.2. Và nó phạt `zone_width`, tham số đang bị xoá có điều kiện ở §3.3. Hạng mục tự mâu thuẫn hai lần với chính spec |
| H9/H10 | 🔴 Viết lại, kịch bản riêng | Đệm thanh lý biến thiên (§6.4) — stress test theo dải zone_width |
| **H13 — ZSS component audit** | 🆕 Mới | `touch_count`, `volume_ratio`, `compression` không dùng dữ liệu ngoài `confirmed_at_bar` |
| **H14 — Pool overlap monitor** | 🆕 Mới, gắn với §0.3/§9 | Đo overlap thật mỗi lần rà soát pool hàng tháng, ghi số liệu — KHÔNG dùng để điều chỉnh tiêu chí chọn pool ngược lại (§0.3 cảnh báo rõ) |
| **H16 — Trial ledger audit** 🆕 v3.1 | 🔴 P0, chặn D1 | Script kiểm L-Z10/11/12/15 (§9c.6), chạy tự động trước MỖI lần backtest. Fail → chặn chạy, không cảnh báo suông. **Mở rộng:** kiểm luôn L-Z16/L-Z17 trên `idea_queue.jsonl` — bản ghi thiếu `who_pays`, hoặc có `data_source = TOOL_D_RESULTS` mà `status != REJECTED` → fail. **v3.2:** kiểm luôn L-Z18/L-Z19 trên kết quả backtest. **v4:** kiểm L-Z20/21/22 — thực thi phán quyết định cỡ §6.8e, fail thì CHẶN CHẠY |
| **H17 — Lockbox seal integrity** 🆕 v3.1 | 🔴 P0, chặn D1 | Kiểm SHA-256 lockbox mỗi lần khởi động pipeline (L-Z13/14). Phát hiện lockbox bị chạm ngoài quy trình → dừng toàn bộ, ghi sự cố vào research-log |
| **H18 — PBO/CSCV** 🆕 v3.1 | 🟡 P1 ở D4, nâng P0 ở D9 | Cài đặt CSCV. Ở D4 chỉ ghi số; ở D9 (WFO đủ fold) dùng làm điều kiện chặn |
| **H19 — Backfill an toàn** 🆕 v7 (LD-27/28) | 🔴 P0, chặn lần backfill đầu tiên | Script ghi dữ liệu lịch sử PHẢI: (a) sao lưu trước; (b) GỘP với dữ liệu cũ, không ghi đè theo khoảng ngày yêu cầu (Tool A suýt xoá nhiều năm dữ liệu vì bẫy này); (c) verify phần cũ giữ nguyên byte-for-byte sau khi chạy; (d) tải hỏng → KHÔNG ghi cache rỗng, ghi trạng thái `unreadable` (§0d.6). Kèm chỉ số ĐỘ PHỦ DỮ LIỆU riêng; **cấm suy nguyên nhân gốc từ khoảng trống mà không kiểm trực tiếp nguồn** — Tool A mất nhiều ngày vì quy một khoảng trống cho "sàn thiếu dữ liệu" trong khi lỗi là script của mình |
| **H20 — measurement_guard + provenance** 🆕 v7 (§0d) | 🔴 P0, chặn D1, làm ĐẦU TIÊN | Guard file tham số ẩn, danh sách đóng entrypoint E1–E8, khối provenance 7 khoá, ba trạng thái dữ liệu. Chi phí: vài chục dòng. Không có nó thì MỌI con số phía sau không đáng tin theo định nghĩa |
| **H15 — Network/auth latency probe** 🆕 v3 | 🟡 P1, không chặn — thực hiện SỚM, song song D1 | Dùng `POST /fapi/v1/order/test` với key production để đo network+auth latency thật tới Binance, không cần đợi tới giai đoạn dry-run/live. Chi tiết và điều kiện bảo mật ở §6.7 |

> ⚠️ **Chi phí đã chấp nhận, ghi lại để không quên khi lập lịch:** H1-D và H3-D viết từ đầu là hai hạng mục tốn thời gian nhất trong toàn bộ v10 gốc (H1 được gọi "đường găng", H3 bị điều chỉnh độ khó 2→3 giữa chừng vì ước lượng ban đầu thấp). Không có gì đảm bảo Tool D làm nhanh hơn — cộng thêm buffer thay vì lạc quan theo lộ trình gốc.

---

# PHẦN 11b — 🆕 v3.3: COMPONENT HEALTH — PHÁT HIỆN CÔNG THỨC HỎNG

> Trả lời câu hỏi "nếu công thức cố định sai thì sao". `mult_edge` (§6.2 hệ số 5) đo edge TỔNG THỂ; không có gì đo từng THÀNH PHẦN.

## 11b.1. Ba loại sai, ba phản ứng khác nhau

| Loại | Ví dụ | Ai sửa | Chi phí | Cho phép? |
|---|---|---|---|---|
| **L1 — Sai GIÁ TRỊ** (cấu trúc đúng) | `k=3` nên là 5; ZSS ngưỡng 0.5 nên là 0.6 | Người, tại gate định kỳ | 1 trial từ B3 | ✅ Có quy trình (DR-012 Hạng 2) |
| **L2 — Sai CẤU TRÚC** | Swing 2 phía sai về bản chất; ZSS thiếu thành phần | Người, qua ablation arm mới | 1 slot NGÂN SÁCH A + **lockbox mới** | ⚠️ Đắt, hiếm |
| **L3 — Sai GIẢ THUYẾT** | Zone Absorption không có edge | **Không ai sửa** | — | 🔴 **DỪNG DỰ ÁN** |

```
🔴 KHÔNG CÓ ĐƯỜNG NÀO TỪ L3 VỀ L1.
   Nếu giả thuyết gốc sai, mọi lần tinh chỉnh tham số chỉ là fit nhiễu
   — và nó sẽ LUÔN "cải thiện" backtest, đó chính là cái bẫy.
   Ranh giới này do DR-012 Hạng 0 bảo vệ.
```

## 11b.2. Ba chỉ số — 0 tham số mới, CHỈ ghi và cảnh báo

```
H-1  Tỉ lệ zone bị HUỶ trong lúc chờ xác nhận (§7.4 điều kiện huỷ)
     Tăng bất thường → k=3 không còn phù hợp regime hiện tại   → L1

H-2  Tương quan giữa ZSS lúc entry và kết quả lệnh
     Tiến về 0 → ZSS không còn mang thông tin                  → L2

H-3  Tỉ lệ lệnh đóng bằng TIME_STOP (§10.2, dải 5-25%)
     Ra ngoài dải → max_hold_bars sai thang                    → L1

H-4  🆕 v6 — Tỉ lệ lệnh dùng TP_fallback (§5.1), ngưỡng 40%
     Vượt 40% → tiền đề "luôn tìm được zone đối diện trong khoảng
     cách hợp lý" SAI. Đây KHÔNG phải lỗi giá trị của ngưỡng 4.0
     hay 1.5 — nó là lỗi CẤU TRÚC của thiết kế TP        → L2
     🔒 Ngưỡng 40%: chẩn đoán, đóng băng, KHÔNG tính vào N

🔴 CHỈ GHI VÀ CẢNH BÁO. KHÔNG tự động sửa. KHÔNG tự động dừng.
   Mọi thay đổi vẫn phải qua DR-012.
```

> **Vì sao BỐN chỉ số, không phải 20:** mỗi chỉ số theo dõi là **một cơ hội nữa để nhìn số rồi tinh chỉnh**. Càng nhiều dashboard, càng nhiều cửa để tự lừa mình. Bốn chỉ số này được chọn theo một tiêu chí duy nhất: **mỗi cái phủ một thành phần chưa có chỉ số nào phủ**, và mỗi cái phân loại được L1 hay L2.
>
> | | Phủ thành phần | Phân loại |
> |---|---|---|
> | H-1 | thời gian xác nhận zone (`k`) | L1 |
> | H-2 | chất lượng zone (ZSS) | L2 |
> | H-3 | chân trời hold (`max_hold_bars`) | L1 |
> | H-4 🆕 | **tiền đề TP** — mảng mù duy nhất còn lại của v5 | L2 |
>
> 🔴 **v6 sửa một lỗi đồng bộ của v5:** changelog v5 khai *"SỬA §11b — thêm H-4"* và §12d.2 đã dùng H-4 trong `periodic_report.py`, nhưng §11b chưa bao giờ được sửa. Một chỉ số được tính trong báo cáo mà không có định nghĩa trong spec là một chỉ số không ai diễn giải được.

---

---

# PHẦN 12 — LỘ TRÌNH

```
D0     🔴 GATE ĐIỀU KIỆN: Tool A đã qua A2                          ← chặn tất cả
D0-PRE 🆕 v4 — TIỀN ĐĂNG KÝ, CHẶN TUYỆT ĐỐI:   (đổi tên từ "D0.5"
       để không trùng ký hiệu với nguyên lý D0.5 ở §3.4)                       Tuần 0–1
          • 🔴 v6 — THỨ TỰ BẮT BUỘC, KHÔNG LÀM SONG SONG:
             1. VERIFY `zone_width` min có phải code chết không (§3.3)
             2. Xác nhận lại bảng đối chiếu DOF của DR-010 từng dòng
             3. RỒI mới chốt N_ĐĂNG_KÝ (114 nếu chết, 120 nếu không)
                và commit. L-Z29 phải PASS trước khi commit.
          • 🔴 v6 — ĐIỀN NGƯỠNG `DSR-adjusted expectancy ≥ ......` ở
            Nhánh 1 (§10.2) bằng SỐ và commit. Đây là ô v5 để trống,
            và nó là lý do B6 chưa gỡ xong.
          • 🔴 v6 — ĐIỀN thang drawdown 5/8/20% (§12c.5). Sau bước này
            nó thành Hạng 0, không sửa được nữa (DR-012).
          • 🆕 v6 — KIỂM MIN NOTIONAL: đối chiếu min notional từng cặp
            trong pool với notional tranche 1 NHỎ NHẤT có thể
            (`confirm_ratio` 0,33 × w[0] × N_full tại R_eff lớn nhất).
            Vi phạm → nâng E_D, hoặc đặt SÀN cho `confirm_ratio`.
            Không kiểm → lệnh bị sàn từ chối IM LẶNG, và triệu chứng
            duy nhất là "ít lệnh hơn dự kiến" mà không rõ vì sao.
          • 🔴 v7 — PHẦN 0d HOẠT ĐỘNG TRƯỚC MỌI THỨ KHÁC: measurement_guard,
            danh sách E1–E8, provenance 7 khoá, `--cache none` cưỡng
            bức, L-Z36→L-Z41 chạy được. Con số nào sinh ra trước bước
            này KHÔNG được dùng cho bất kỳ quyết định nào.
          • 🆕 v7 — DR-013 (đơn vị đo) commit; L-Z46 grep sạch
            `profit_ratio` trong tầng đo
          • 🆕 v7 — Đọc `git show` mã nguồn Freqtrade ĐANG CÀI cho: D2a
            (huỷ-đặt-lại stop), D2b (closePosition), D6 (adjust_trade_
            position tại open), D7 (custom_data). Ghi kết quả đọc source
            vào research-log TRƯỚC khi viết bất kỳ test nào (LD-38)
          • Tạo trial_registry.jsonl (§9c.2) + idea_queue.jsonl (§9c.7.3)
          • 🆕 v3.3 — Chốt pool ~100 mã, loại BTC/ETH khỏi giao dịch,
            phân tách tập EXPLORE (§9c.4b) và niêm phong ranh giới
          • 🆕 v3.3 — Điền E_D, L_exchange, % lỗ tối đa/ngày xấu
            → kiểm tra kết nạp §6.8f hoạt động (v6: bỏ kiểm L_D_max)
          • 🔴 v5 — Cấu hình Freqtrade theo §0c: freqai=false,
            edge=false, trailing_stop=false, position_adjustment=true.
            L-Z24 + L-Z25 chạy được
          • 🆕 v5 — Viết + commit periodic_report.py (§12d.2)
          • 🆕 v5 — Ước lượng SỐ LỆNH/NĂM bằng tính tay: nếu < 150 thì
            §10.2 fail ngay từ thiết kế, phải xử lý TRƯỚC khi code
          • 🆕 v4 — VERIFY ĐỘ DÀI LỊCH SỬ OI mà Binance API trả về
            (~nửa ngày). Nếu chỉ ~30 ngày → KHÔNG backtest được →
            câu hỏi mở #2 (OI vào ZSS) chết ngay tại đây, không cần
            thiết kế tiếp. Làm TRƯỚC vì kết quả ảnh hưởng tới thiết kế.
          • Chia CALIB/WFO/LOCKBOX, kiểm 4 điều kiện (a)-(d), niêm
            phong lockbox_seal.json (DR-011)
          • H16 + H17 hoạt động
       🔴 KHÔNG ĐƯỢC CHẠM DỮ LIỆU TRƯỚC KHI D0-PRE XONG.
          Một backtest "chỉ xem thử" trước bước này làm hỏng toàn bộ
          giá trị của tiền đăng ký — không sửa được về sau.
────────────────────────────────────────────────────────────────────
D1     🆕 v7: H20 (§0d) TRƯỚC, rồi H1-D + H4-D + H13 + H19          Tuần 1–3
D2     Verify D1-D7 (v7: +D6, +D7; D2 tách a/b/c) + H15             Tuần 3–4
       ↳ 🔴 L-Z49 (D7) PASS là điều kiện vào D4
D3     H3-D Walk-forward orchestrator                               Tuần 4–6
D3.5   🆕 v8 — 🚪 CỔNG SAI LỆCH THƯỚC ĐO (DR-015), CHẶN D4:         Tuần 6
       ↳ Bước 1: phân phối lệch khớp tranche offline, trên CALIB,
         dòng CTRL (0 trial), đầu ra giới hạn {lệch, tranche, hướng}
       ↳ Bước 2: thăm dò mức-lệnh trên testnet — 14 ngày / ≥ 30 sự
         kiện chạm mốc; gia hạn đúng 1 lần; vẫn thiếu → NO_FILL xử
         fail-closed (DR-015 §2)
       ↳ Bước 3: đối chứng âm Z0 cho cả hai bước
       ↳ Xuất Δ_R (P90, tách Long/Short) — commit TRƯỚC khi D4 chạy
       ↳ Đòi testnet dựng SỚM hơn kế hoạch v7 (vốn để ở D10) — chi
         phí một lần, dùng lại nguyên vẹn cho D10
D4     🔴 ABLATION D0.9 — 🔴 v6: CHÍN cấu hình × 2 hướng            Tuần 6–8
          Z0, Z1, Z2, Z3, Z3b + Z0-T0, Z0-T1 + Z0-V1 + Z0-S1
       ↳ tiêu ngân sách B2 (18 trial); DSR dùng N=114
         (hoặc union nếu DR-007)
       ↳ 🔴 v6 — GATE đọc theo HAI NHÁNH (§10.2), không phải một
         danh sách AND. Kết cục "Z0 thắng" KHÔNG dừng dự án.
       ↳ 🔴 v8 — Nhánh 2 đọc QUA hiệu chỉnh hai chiều Δ_R của D3.5
         (DR-015 §4). Không phân xử được → Z0, tiếp tục bình thường.
       ↳ 🔴 DG8 (§4b) BẬT trong TẤT CẢ arm — không phải biến so sánh
────────────────────────────────────────────────────────────────────
D5–D9  (giữ nguyên)                                                 Tuần 9–17
D9.5   🆕 v3.1 — LOCKBOX: chạm ĐÚNG MỘT LẦN (DR-011)                Tuần 17
       ↳ 🔴 v7 sửa (v6 sót): BA KẾT CỤC theo DR-011 — PASS / INCONCLUSIVE
         (gia hạn ≤ 2, chỉ trên đoạn dữ liệu MỚI) / FAIL (dự án tiếp
         tục bằng giả thuyết KHÁC, lockbox MỚI). Không tune lại cấu
         hình đã FAIL. Không thử cấu hình thứ hai trên cùng lockbox.
D10    TESTNET — XÁC NHẬN QUY MÔ ĐẦY ĐỦ (🔴 v8: không còn là lần ĐẦU
       đo D6 — lần đầu ở D3.5): verify D2b/D2c + đo lại D6 với chiến
       lược hoàn chỉnh + tỷ lệ khớp post-only (§9b.3). Ngưỡng chấp
       nhận điền bằng DR TRƯỚC khi chạy (L-Z35). Số D10 mâu thuẫn số
       D3.5 vượt biên đã ghi → L2 (§11b.1)                          Tuần 17–18
D11    Dry-run                                                      Tuần 18–20
D12    Vốn nhỏ — từ đây DR-012 (change-control) có hiệu lực         tiếp theo

🔴 KHÔNG BAO GIỜ CẮT: (giữ nguyên danh sách cũ) + D0-PRE, D9.5, H16, H17,
   DG8 (§4b), arm Z0-T1 (§10.1b), 🆕 v8: cổng D3.5 (DR-015) và con
   dấu đo lường + sổ hai trạng thái (DR-014)
```

> ⚠️ **Chi phí thời gian:** D0-PRE thêm ~1 tuần (v7: +PHẦN 0d, ước thêm 2–4 ngày nữa). Đây là 1 tuần mua lấy việc GATE D0.9 trở thành phép kiểm tra tính được thay vì câu chữ. Không có cách nào rẻ hơn — bỏ qua nó không tiết kiệm được gì, chỉ dời chi phí sang lúc mất tiền thật.

---

---

# PHẦN 12b — 🆕 v5: VÒNG ĐỜI THAM SỐ

> Trả lời: *"tham số cứ theo đề xuất tạm, nhưng cần dữ liệu qua thời gian để quyết lại. Cứ cố định mà sai thì thành vòng lặp thua lỗ."*

## 12b.1. Năm trạng thái của một tham số

```
① ĐỀ XUẤT        Giá trị khởi điểm trong spec, có lý do, CHƯA kiểm
                  → mọi tham số hiện đang ở đây
        ↓ D4/D5 (calibration, tiêu trial từ B1)
② ĐÃ CALIBRATE   Chọn từ ≤3 ứng viên trên tập CALIB
        ↓ D9 (walk-forward)
③ ĐÃ WFO         Sống sót qua nhiều fold
        ↓ D9.5 (lockbox, chạm 1 lần)
④ ĐÃ XÁC NHẬN    Vượt lockbox → khoá khi vào live
        ↓ mỗi 100 lệnh đóng (§12c)
⑤ ĐANG VẬN HÀNH  Xem lại tại điểm quyết định, đổi được theo phân cấp

🔒 Tham số ĐÓNG BĂNG (§DR-010) đi thẳng ① → ④, bỏ qua ② và ③.
   Đó chính là ý nghĩa của đóng băng: không tiêu trial để calibrate.
   Nhưng chúng VẪN vào ⑤ — vẫn xem lại được, chỉ tốn hơn (§12c.3).
```

## 12b.2. Vì sao "cố định sai" KHÔNG tạo được vòng lặp thua lỗ

```
🔑 Vòng lặp thua lỗ cần MỘT điều kiện: hệ thống TIẾP TỤC vào lệnh
   trong khi đang thua. Điều kiện đó bị chặn ở ba tầng:

   mult_dd     drawdown Tool D > 8%  →  HALT (§12c.5, KHÔNG phải
               "size = 0 vĩnh viễn" như v5 viết)
   DG7 + DG8   mỗi vị thế có trần CHI PHÍ (§4c) và trần THỜI GIAN (§4b)
   D0.1 + SL   lỗ mỗi lệnh chặn trên tại rho × E_D

   → Kịch bản xấu nhất một chu kỳ: mất 8% E_D rồi HALT.
   → Với E_D = 500: −40 USDT rồi hệ thống ngừng mở lệnh mới.
   → Trần tuyệt đối trước khi bác bỏ giả thuyết: 20% (§12c.5).

🔴 Điểm quan trọng: các tham số ĐƯỢC ĐÓNG BĂNG (k, ADX, trọng số ZSS,
   trail, funding) đều KHÔNG nằm trong ba tầng chặn trên. Ba tầng
   chặn thuộc CẤP C (§12c.3) — không bao giờ đóng băng nhầm vì không
   bao giờ được đổi.

   Đóng băng sai → lãi ít hơn mức có thể đạt. KHÔNG → cháy tài khoản.
   Đây là hai loại rủi ro khác hạng, và thiết kế cố ý dồn mọi thứ
   nguy hiểm vào nhóm không được chạm.
```

---

# PHẦN 12c — 🆕 v5: ĐIỂM QUYẾT ĐỊNH & NGÂN SÁCH TÁI TẠO

## 12c.1. Chu kỳ theo SỐ LỆNH, không theo lịch

```
Sai số chuẩn win rate = √(p(1−p)/n),  p ≈ 0.5:
   n =  12 (≈1 tháng)  → SE 14.4pp  → KTC 95% ±28pp   ← VÔ DỤNG
   n =  50             → SE  7.1pp  → ±14pp
   n = 100             → SE  5.0pp  → ±10pp           ← dùng được

🔴 Với 12 lệnh, win rate 45% và 65% KHÔNG PHÂN BIỆT ĐƯỢC. Đổi tham số
   theo tháng = đổi theo nhiễu — và bạn sẽ LUÔN thấy một lý do, vì
   nhiễu luôn có hình dạng.
```

| | Chu kỳ | Được làm gì |
|---|---|---|
| **Báo cáo định kỳ** | Hàng tháng | Đọc, theo dõi xu hướng, phát hiện bất thường **vận hành**. 🔴 KHÔNG đổi tham số |
| **ĐIỂM QUYẾT ĐỊNH** | Mỗi **100 lệnh đã đóng** | Được đổi tham số theo §12c.3 |

> Bạn có tầm nhìn hàng tháng; quyền đổi gắn với **số mẫu**, không gắn với lịch. Với 150 lệnh/năm → mỗi ~8 tháng. Với 400 lệnh/năm → mỗi ~3 tháng. **Số lệnh thực tế là KẾT QUẢ, chưa ai biết** — ước lượng ở D0-PRE.

## 12c.2. Ngân sách trial TÁI TẠO

```
🔴 SỬA LỖI NỀN CỦA v3.1–v4: ngân sách cạn vĩnh viễn là luật của
   GIAI ĐOẠN NGHIÊN CỨU, nơi dữ liệu hữu hạn và mỗi lần nhìn tiêu
   một phần thông tin. Áp nó lên GIAI ĐOẠN VẬN HÀNH là sai:

   Mỗi tháng live sinh ra dữ liệu OOS THẬT — chưa ai nhìn, không lặp
   lại được, không thể fit ngược. Dữ liệu mới ⇒ ngân sách mới.

🆕 QUY TẮC TÁI TẠO:
   Mỗi 25 lệnh đã đóng mới  →  +1 trial vào B3
      150 lệnh/năm → +6 trial/năm
      Mỗi điểm quyết định (100 lệnh) → có 4 trial để dùng

   🔒 TRẦN TÍCH LUỸ: B3 ≤ 20. Không để dành 3 năm rồi tiêu một lúc —
      như vậy là quay lại khai thác dữ liệu quy mô lớn.

   🔴 N TĂNG THEO: N = 114 + (số trial đã dùng sau live).
      DSR tính lại tại MỖI điểm quyết định với N hiện tại.
      Tái tạo ngân sách KHÔNG có nghĩa phép thử trở nên miễn phí.
```

Tỉ lệ 1/25 là lựa chọn, không phải định lý — nhưng **nguyên tắc** (ngân sách tỉ lệ với dữ liệu mới) có căn cứ. Đặt 20 hay 30 đều được, miễn chốt trước và không sửa khi đã thấy dữ liệu.

## 12c.3. PHÂN CẤP tham số được đổi

| Cấp | Tham số | Điều kiện đổi | Vì sao |
|---|---|---|---|
| **A — đổi được** | `max_hold_bars`, `v_min`, ngưỡng `ZSS`, `TP1` trừ hao | 1 điểm quyết định + bằng chứng từ báo cáo + 1 trial | Nhánh **LỢI NHUẬN**. Sai → lãi ít, không cháy |
| **B — khó đổi** | `buf_sl`, `DG6-A`, `DG4`, `DG6-D` (funding rate + hồi 50%), **`DG7` 0.3×R_eff** 🆕, ngưỡng `mult_corr` | **HAI** điểm quyết định LIÊN TIẾP cùng tín hiệu + 1 trial | Nhánh **RỦI RO**. Sai → mất tiền thật |
| **C — không bao giờ** | D0.1–D0.5, đệm thanh lý 8×, số tranche = 3, sự tồn tại DG6/DG7/DG8, **`k`** 🆕, **thang drawdown 5/8/20%** 🆕 | ❌ Không có quy trình, không có ô nhập | **Đây là cầu dao.** Chúng là thứ chặn vòng lặp thua lỗ |

```
🔴 v6 — BA SỬA ĐỔI so với bảng v5, mỗi cái gỡ một mâu thuẫn:

   `TP2 trail`   Cấp A → 🔒 ĐÓNG BĂNG. v5 vừa đóng băng nó ở DR-010
                 vừa để nó ở Cấp A "đổi được". Tham số đóng băng
                 KHÔNG được nằm ở Tầng B/Cấp A (§6.9.3).
                 ⚠️ Nó vẫn là ứng viên MỞ KHOÁ đầu tiên nếu về sau
                    chỉ được mở một tham số.

   `DG6-B`       ra khỏi Cấp B. Đã đóng băng = DG4 (§4.1). v5 gộp nó
                 vào "DG6-A/B/C" ở Cấp B trong khi DR-010 đóng băng nó.

   `k`, `mult_dd`  → Cấp C, KHÔNG có cơ chế mở khoá +6.
                 Lý do đầy đủ ở §6.9.4. Tóm tắt: `k` là định nghĩa
                 (đổi = L2, cần lockbox mới, đắt hơn +6 nhiều);
                 `mult_dd` là cầu dao (không thể vừa tune vừa là
                 cầu dao).
```

```
🔑 NGUYÊN TẮC: tham số ảnh hưởng LỢI NHUẬN thì linh hoạt;
              tham số ảnh hưởng TỒN VONG thì cứng.

🔴 MỞ KHOÁ MỘT THAM SỐ ĐÃ ĐÓNG BĂNG (DR-010): +6 vào N, không phải
   +1. Lý do: N = 114 được biện minh BỞI CHÍNH việc đóng băng. Đóng
   băng để hạ N rồi âm thầm mở khoá là gian lận DSR — kiểu gian lận
   khó tự phát hiện nhất vì mỗi bước đều có vẻ hợp lý.
```

## 12c.4. 🔴 LỖI ≠ THAM SỐ — phần lớn việc giai đoạn đầu là MIỄN PHÍ

```
✅ SỬA TỰ DO, 0 trial, KHÔNG GIỚI HẠN SỐ LẦN  (DR-012 Hạng 1):
   • Lệnh limit không khớp do sai tick size / step size
   • Timeout API, retry logic, xử lý rate limit
   • Sai đơn vị, sai làm tròn, sai múi giờ
   • SL không sửa được khối lượng (giả định D2 hỏng)
   • Log thiếu trường, báo cáo tính sai
   • Bất kỳ chỗ nào code KHÔNG làm đúng như spec mô tả

🔴 TIÊU TRIAL  (DR-012 Hạng 2):
   • Đổi ngưỡng ZSS 0.5 → 0.55
   • Đổi max_hold_bars 24 → 32
   • Bất kỳ chỗ nào SPEC được thay đổi

🔑 Phân biệt: "code không khớp spec" là LỖI (miễn phí sửa).
             "spec không khớp thị trường" là THAM SỐ (tiêu trial).

→ Nỗi lo "giai đoạn đầu nhiều thiếu sót nhưng bị khoá tay" phần lớn
  KHÔNG thành hiện thực: thiếu sót giai đoạn đầu chủ yếu là loại thứ
  nhất, và loại đó luôn miễn phí, không giới hạn.
```

---

## 12c.5. 🆕 v6 — THANG PHẢN ỨNG DRAWDOWN: ba mức, không phải một

> Gỡ hai vấn đề cùng lúc: (a) v5 đặt `mult_dd` ngưỡng **bằng đúng** `daily_loss_budget_pct` (cả hai = 8%), nghĩa là **đúng một ngày xấu tối đa là hệ thống tự tắt vĩnh viễn**; (b) mọi phương án "HALT tạm rồi mở lại" ngây thơ đều **deadlock**.

```
🔴 VÌ SAO 8% CỦA v5 ĐẶT SAI CHỖ — bằng chính số của spec:
   daily_loss_budget_pct = 8%   → một ngày xấu tối đa (tương quan = 1)
   mult_dd ngưỡng        = 8%   → tắt vĩnh viễn
   HAI CON SỐ NÀY BẰNG NHAU. Một sự kiện mang thông tin về THỊ TRƯỜNG
   (sập tương quan) kích hoạt một phản ứng dành cho thông tin về EDGE
   (giả thuyết đã chết). Sai loại.

🔴 VÌ SAO "CRYPTO BIẾN ĐỘNG MẠNH" KHÔNG PHẢI LÝ DO NỚI NGƯỠNG:
   Drawdown của Tool D KHÔNG tỉ lệ với biến động thị trường — nó tỉ
   lệ với (số lệnh thua × rho). Biến động đã được hấp thụ ở tầng định
   cỡ: zone rộng → R_eff lớn → notional nhỏ → lỗ vẫn đúng rho × E_D.
   Đó chính là việc D0.1 làm. Nới ngưỡng dd không giúp "chịu được
   biến động"; nó chỉ cho phép THUA NHIỀU LỆNH HƠN trước khi dừng.
   → Lý do hợp lệ để sửa là (a) ở trên, không phải "crypto biến động".

🔴 VẤN ĐỀ THẬT: `mult_dd` không phân biệt được
      20 lệnh thua trong 1 NGÀY   (thông tin về thị trường)
      20 lệnh thua rải rác 3 THÁNG (thông tin về edge)
   Hai thứ đòi hỏi hai phản ứng khác nhau. Thang ba mức làm việc đó.
```

### Thang chốt

```
dd_tool_d  ≤ 5%   →  mult_dd = 1.0    bình thường
5% < dd    ≤ 8%   →  mult_dd = 0.5    GIẢM TỐC, vẫn giao dịch
dd         > 8%   →  HALT             ngừng MỞ lệnh mới
dd         > 20%  →  ABORT            bác bỏ giả thuyết (L3, §11b.1)

🔒 CẤP C. Cả ba con số. Điền ở D0-PRE, sau đó là DR-012 Hạng 0.

dd_tool_d đo từ ĐỈNH equity của sub-account Tool D (§6.5b), tính
trên equity đã bao gồm PnL chưa thực hiện.
```

### HALT — cơ chế mở lại, và vì sao phương án ngây thơ bị deadlock

```
🔴 PHƯƠNG ÁN ĐÃ BỊ BÁC BỎ (là đề xuất đầu tiên, tự phát hiện sai):
   "HALT tại 8%, tự mở lại khi dd hồi về ≤ 5% HOẶC tại điểm quyết
    định gần nhất."

   Cả HAI điều kiện đều KHÔNG BAO GIỜ TỚI:
      • dừng mở lệnh mới → không có lệnh đóng mới → dd ĐỨNG YÊN
        (sau khi các vị thế còn lại đóng hết) → không bao giờ ≤ 5%
      • điểm quyết định = mỗi 100 LỆNH ĐÓNG (§12c.1) → không có
        lệnh mới → không bao giờ đủ 100
   → "HALT tạm" trở thành HALT VĨNH VIỄN. Đúng thứ nó được tạo ra
     để tránh. Một cơ chế phục hồi mà điều kiện phục hồi phụ thuộc
     vào chính hoạt động bị đình chỉ là một deadlock.

✅ CƠ CHẾ CHỐT — mở lại theo THỜI GIAN LỊCH, không theo kết quả:

   BƯỚC 1  HALT kích hoạt:
           • ngừng MỞ vị thế mới
           • vị thế đang mở CHẠY BÌNH THƯỜNG theo DG6/DG7/DG8/SL/TP
             (không đóng ép — đóng ép biến một drawdown chưa thực
              hiện thành lỗ thực hiện, làm dd XẤU ĐI)

   BƯỚC 2  Điều kiện mở lại — CẢ BA:
           (a) mọi vị thế đã đóng hết
           (b) đã qua 2 × max_hold_bars kể từ vị thế cuối đóng
               = 48 nến 4H = 8 ngày
               🔒 0 hằng số mới — dùng lại `max_hold_bars` (§4b.3)
           (c) người vận hành ghi MỘT bản ghi vào research-log xác
               nhận đã đọc `periodic_report.py` của kỳ đó
               (không phải phê duyệt — chỉ xác nhận đã nhìn)

   BƯỚC 3  Mở lại ở mult_dd = 0.5 (nửa size), giữ cho tới khi
           dd ≤ 5%. Nửa size vẫn giao dịch → dd CÓ THỂ hồi → không
           deadlock.

   BƯỚC 4  Nếu trong lúc chạy nửa size mà dd > 20% → ABORT.

🔴 TRẦN SỐ LẦN HALT: 3 lần trong một chu kỳ 100 lệnh đóng.
   Lần thứ 4 → ABORT bất kể dd bao nhiêu.
   Lý do: HALT lặp lại là bằng chứng edge hỏng, không phải xui.
```

> ⚠️ **Điều thang này KHÔNG giải quyết, nói thẳng:** nó không làm hệ thống lãi hơn, và không làm giả thuyết đúng hơn. Nó chỉ đảm bảo một cú sập tương quan không bị nhầm thành bằng chứng "Zone Absorption đã chết". Nếu edge thật sự không tồn tại, thang này chỉ kéo dài thời gian tới ABORT — và đó là chi phí có ý thức, đổi lấy việc không giết nhầm một giả thuyết còn sống.

---

# PHẦN 12d — 🆕 v5: BÁO CÁO ĐỊNH KỲ & GIAO THỨC LLM PHÂN TÍCH

> Sửa lệnh cấm quá rộng ở DR-009 v3.3. Lập luận được chấp nhận: *"cần phân tích số liệu khổng lồ một cách khách quan; con người không phân tích sâu sắc được."* Đúng. Nhưng phải chặn đúng chỗ.

## 12d.1. Vì sao lục tìm tự do trong dữ liệu thô là nguy hiểm

```
LLM đọc 500 lệnh thô có thể NGẦM kiểm tra hàng trăm giả thuyết
("nhóm nào thua nhiều?", "giờ nào xấu?", "ZSS bao nhiêu thì tệ?")
trước khi nói ra MỘT câu. Số phép thử ngầm đó KHÔNG ĐO ĐƯỢC.

→ Bạn nhận một đề xuất nghe rất thuyết phục, có số liệu hẳn hoi, và
  KHÔNG có cách nào biết nó là tín hiệu hay là nhiễu được kể thành
  câu chuyện. Đây là chế độ hỏng nguy hiểm nhất vì nó trông giống
  hệt phân tích tốt.
```

## 12d.2. Giải pháp: PHÂN TÍCH ĐĂNG KÝ TRƯỚC + DIỄN GIẢI TỰ DO

```
BƯỚC 1 — Script CỐ ĐỊNH `periodic_report.py`, commit vào git TRƯỚC
         khi live. Tính CÙNG một bộ chỉ số mỗi kỳ:

   H-1  tỉ lệ zone bị huỷ khi chờ xác nhận (§7.4)     → k còn đúng?
   H-2  tương quan ZSS lúc entry ↔ kết quả lệnh       → ZSS còn tin được?
   H-3  tỉ lệ đóng bằng TIME_STOP (dải 5–25%)         → max_hold đúng thang?
   H-4  tỉ lệ dùng TP_fallback (ngưỡng 40%)           → tiền đề TP còn đúng?
   • Win rate + expectancy, TÁCH Long/Short
   • Phân bố hold_duration_bars (mọi lệnh)
   • Phân bố liq_buffer_ratio thực tế vs ngưỡng 8
   • Tỉ lệ khớp tranche 1 / 2 / 3
   • Funding tích luỹ / R_eff
   • Tách theo tier thanh khoản, theo phiên
   • Số mẫu HIỆU DỤNG (điều chỉnh tương quan) vs số lệnh danh nghĩa
   • Ngân sách: B3 còn lại, N hiện tại, DSR hiện tại
   • 🆕 v7 — Tỉ lệ khớp post-only tranche 1/2/3 + NO_FILL (§3.5)
   • 🆕 v7 — Phân bố gap_ms mỗi lần đổi khối lượng SL (§8.3, D2c)
   • 🆕 v7 — Khối provenance ở ĐẦU báo cáo (§0d.5): git_sha,
     reproducible_from_sha, data_hashes, guard_passed
   • 🆕 v7 — MỌI chỉ số mang trạng thái pending/unreadable/ok (§0d.6);
     dòng tổng: "đã audit N/M (X đạt, Y chưa đạt, Z chưa đo được)"
     — KHÔNG có giá trị lính canh, KHÔNG có số cũ kèm cảnh báo

   🔴 ĐỔI NỘI DUNG BÁO CÁO = TIÊU 1 TRIAL. Nếu không, bạn sẽ thêm
      chỉ số mới cho tới khi tìm được cái trông bất thường.

BƯỚC 2 — LLM đọc ĐẦU RA của script. KHÔNG đọc DB lệnh thô.
   ✅ Được: diễn giải, chỉ chỉ số nào ra ngoài dải, so sánh các kỳ,
            đề xuất tham số nào nên xét, nêu giả thuyết nguyên nhân
   ❌ Cấm:  truy vấn dữ liệu thô, tự tính chỉ số mới, "để tôi kiểm
            tra thêm một góc nữa"

BƯỚC 3 — RÀNG BUỘC CHỐNG CHÉM GIÓ (thực thi được):
   🔴 MỌI câu trong đề xuất phải TRÍCH một con số cụ thể từ báo cáo.
      Câu không trích được số → gạch bỏ, không xét.
      Đề xuất không có số nào → LOẠI TOÀN BỘ.
   🔴 Đề xuất phải nêu rõ: chỉ số nào, giá trị bao nhiêu, ngoài dải
      bao nhiêu, và tham số nào được trỏ tới.

BƯỚC 4 — NGƯỜI DUYỆT VÀ NGƯỜI TRIỂN KHAI.
   LLM không có quyền quyết, không được đề xuất mở khoá tham số Cấp
   C, không được đề xuất đổi ngân sách.
   🆕 v6 — Mọi đề xuất phải TỰ KHAI phân loại theo §11b.1:
      L1 (sai giá trị)    → DR-012 Hạng 2, 1 trial từ B3
      L2 (sai cấu trúc)   → slot NGÂN SÁCH A + LOCKBOX MỚI
      L3 (sai giả thuyết) → ABORT, không có quy trình sửa
   Đề xuất không tự khai được hạng → LOẠI.
   🔴 Dấu hiệu L2 đội lốt L1 (DR-012): phải đổi >1 tham số cùng lúc
      để "sửa". Đây là cạm bẫy nguy hiểm nhất vì L1 rẻ hơn nhiều.

BƯỚC 5 — 🆕 v6: ĐƯỜNG TRIỂN KHAI DUY NHẤT.
   Thay đổi được áp bằng cách SỬA `tool_d_config.yaml` + commit git.
   🔴 Giao diện KHÔNG có ô nhập cho Tầng B và Tầng C (§6.9.3/§6.9.4)
      — không phải "khoá xám", không phải "cần mật khẩu", mà là
      KHÔNG TỒN TẠI ô nhập. Chỉ Tầng A có UI.
```

> 🔑 **Ranh giới đúng nằm ở đâu — điểm dễ hiểu nhầm nhất của DR-009.** Việc **người** là người quyết và tự tay sửa code **không làm giảm số phép thử ngầm** mà LLM đã tiêu khi đọc dữ liệu. Nếu LLM đọc 500 lệnh thô, nó đã ngầm loại hàng trăm giả thuyết trước khi nói một câu — con số đó không đo được dù người duyệt kỹ đến đâu. Người duyệt được **nội dung** đề xuất, không duyệt được **không gian tìm kiếm** đã sinh ra nó.
>
> → Vì vậy ranh giới không phải *"ai bấm nút"*, mà là ***"không gian tìm kiếm có bị chặn TRƯỚC không"***. Đó chính xác là điều §12d làm đúng: báo cáo cố định, commit trước khi live, LLM diễn giải trong một không gian hữu hạn đã đăng ký. Trong khuôn khổ đó, LLM tổng hợp — phân tích — đề xuất là **hợp lệ và được khuyến khích**; quyết định và triển khai là của người.

> 🔑 **Vì sao cách này bounded:** không gian tìm kiếm bị chặn bởi **định nghĩa báo cáo**, đã cố định trước khi có dữ liệu. LLM diễn giải trong một không gian hữu hạn đã đăng ký, thay vì tìm kiếm trong không gian vô hạn. Bạn được phân tích sâu; số phép thử ngầm được chặn.

## 12d.3. Ba nguồn kích hoạt hợp lệ để đổi tham số

```
(1) Chỉ số Component Health ra ngoài dải (H-1…H-4)
    VD H-2 tiến về 0 → bằng chứng trọng số ZSS sai → xét w_a/w_b/w_c

(2) GATE FAIL kèm chẩn đoán TRỎ ĐÚNG tham số đó
    VD TIME_STOP cắt 60% lệnh lãi → trỏ max_hold_bars,
       KHÔNG trỏ ADX

(3) Điều kiện đóng-băng-có-điều-kiện được thoả
    VD Z0-T1 xong → tuổi trend vào danh sách xét lại

🔴 KHÔNG hợp lệ: "thấy kết quả chưa đẹp, thử nới xem sao".
   Đó chính xác là hành vi mà toàn bộ ngân sách trial được dựng để chặn.
```

## 12d.4. Test

```
L-Z26 🆕 v5 — Mọi thay đổi tham số sau live có: nguồn kích hoạt ∈
         {HEALTH, GATE_FAIL, CONDITIONAL_UNFREEZE}, chỉ số cụ thể,
         giá trị cụ thể, và 1 trial đã trừ khỏi B3       🔴 CRITICAL
L-Z27 🆕 v5 — B3 ≤ 20 tại mọi thời điểm; B3 chỉ tăng theo công thức
         floor(lệnh_mới / 25), không tăng bằng tay
L-Z28 🆕 v5 — Không có thay đổi tham số nào xảy ra giữa hai điểm
         quyết định (trừ DR-012 Hạng 1 — sửa lỗi)
```

---

# PHẦN 13 — CHECKLIST

## ❌ Không bao giờ

```
❌ Dùng zone với confirm_ratio tính sai / nhìn dữ liệu > t hiện tại    (§7.1/§7.4, CRITICAL)
❌ Tin kết quả `lookahead-analysis` gốc cho fill tranche 2/3 mà không
   kiểm tra tay theo caveat issue #12168                              (§7.2)
❌ Di chuyển SL sau tranche 1                                     (D0.2)
❌ Khớp tranche khi DG5 fail (ZSS suy yếu) dù giá chưa chạm SL     (§4)
❌ Mở tranche 1 khi liq_buffer_ratio < 8                           (§6.4)
❌ Mở tranche 1 khi CHƯA có xác nhận price-action (§3.3b)          (CRITICAL — mới)
❌ Bỏ qua DG6 và chờ SL cứng khi (A)/(B)/(C) đã đúng               (§4.1, CRITICAL — mới)
❌ Vào lệnh khi 1D và 4H trend không đồng thuận (§2.2)             (mới)
❌ Tune ngưỡng [CẦN CALIBRATE] "bằng mắt" mà không ghi trial_registry (§9)
❌ Chạy D0.9 trước khi H4-D + H4-D-b pass                          (§7.2/§7.5)
❌ Cho đòn bẩy danh mục Tool D phụ thuộc vào Tool A — mỗi tool tự chọn theo vốn riêng (§6.5). *(v6: `L_D_max` đã xoá, §6.8c)*
❌ Dùng chung ngưỡng DG6/DG7 cho cả Long và Short mà không calibrate
   riêng (§3.3d, CRITICAL — mới) — biến động nền và funding bất đối xứng
❌ Bật Short khi DG7 (funding drain) chưa triển khai                (§3.3d, mới)
❌ Bỏ qua điều kiện D của DG6 khi Short đang mở (rủi ro short squeeze) (§4.1, mới)

❌ Chạy backtest bất kỳ trước khi **D0-PRE** hoàn tất        (§9c.4, CRITICAL)
   *(v6: đổi tên D0.5 → D0-PRE đã làm ở v4, checklist chưa cập nhật)*
❌ Chạm dữ liệu LOCKBOX trước D9.5, hoặc chạm lần thứ hai    (DR-011, CRITICAL)
❌ Tăng N_ĐĂNG_KÝ sau khi đã nhìn bất kỳ kết quả nào          (DR-010)
❌ Báo cáo DSR mà không nêu N đã dùng để tính                (§10.2)
❌ Sửa `outcome` của một trial đã ghi                        (§9c.2)
❌ Để LLM truy vấn DB LỆNH THÔ, hoặc tự tính chỉ số ngoài
   periodic_report.py, rồi đề xuất thay đổi     (Loại B, DR-009, CRITICAL)
   ✅ 🆕 v6 — ĐƯỢC: LLM đọc ĐẦU RA `periodic_report.py` (§12d), tổng
      hợp, phân tích, đề xuất — mọi câu phải TRÍCH SỐ, và đề xuất phải
      tự khai hạng L1/L2/L3. Người duyệt, người triển khai bằng cách
      sửa YAML + commit. UI không có ô nhập Tầng B/C.
❌ Trộn phiên "phân tích kết quả" với phiên "sinh ý tưởng"    (DR-009, CRITICAL)
❌ Nhận ý tưởng vào Idea Queue khi không trả lời được "AI TRẢ TIỀN" (§9c.7)
❌ Nới trần 5 giả thuyết/quý vì có LLM hỗ trợ sinh ý tưởng    (§9c.7.1)
❌ Viết selection_reason tham chiếu kết quả định lượng Tool D (§9c.7.4)
❌ Dùng "live vốn nhỏ" làm cơ chế xác nhận EDGE thay lockbox  (§9c.7.5)
❌ 🆕 v3.2 — Giữ vị thế quá max_hold_bars vì "đang lãi" hoặc
   "TP1 đã chạm"                                            (§4b.2, CRITICAL)
❌ 🆕 v3.2 — Đặt max_hold_bars ≥ 40 nến 4H mà không nới §1.3 trước
   — vị thế không được sống lâu hơn giả thuyết sinh ra nó    (§4b.3, CRITICAL)
❌ 🆕 v3.2 — Rút ngắn tầng 1D (§2.1/2.3) theo trực giác trước khi có
   kết quả Z0-T1                                                     (§2b.2)
❌ 🆕 v3.2 — Chạy D0.9 mà TẮT DG8 ở một số arm để "so sánh cho sạch"
   — DG8 là thuộc tính khung thử nghiệm                              (§4b.4)
❌ 🆕 v3.3 — Đưa coin từ tập EXPLORE vào pool giao dịch, dù nó đã
   thoả tiêu chí §0.3                                       (§9c.4b, CRITICAL)
❌ 🆕 v3.3 — Để E trong công thức §6.2 đọc SỐ DƯ VÍ thay vì E_D (§6.8)
❌ 🔴 v6 — Thêm lại `L_D_max`, `mult_cross`, `L_BASE`, `max_open_D`,
   hay bất kỳ tham chiếu khung 15m nào     (§6.8c/§6.2/§3.3c, L-Z32/33)
❌ 🆕 v3.3 — Tính ngân sách rủi ro danh mục với giả định các lệnh độc
   lập; PHẢI dùng giả định tương quan = 1                   (§6.8d, CRITICAL)
❌ 🆕 v4 — Đưa `max_open_D` trở lại thành hằng số cấu hình  (§6.8f, L-Z21)
❌ 🆕 v3.3 — Gộp zone vượt trần 2× zone rộng nhất (gộp dây chuyền)  (§1.3b)
❌ 🆕 v3.3 — Mở queue TRƯỚC khi commit tiêu chí chọn của quý        (§9c.7.4)
❌ 🆕 v3.3 — Phân loại L2/L3 thành L1 để dùng quy trình sửa rẻ hơn  (DR-012)
❌ 🆕 v4 — Đưa tham số Tầng C vào giao diện dưới BẤT KỲ hình thức nào,
   kể cả "hiện dạng xám" hay "cần mật khẩu"                (§6.9.4, CRITICAL)
❌ 🆕 v4 — Cho sửa tham số Tầng B qua UI mà không ghi trial_registry
   và không trừ ngân sách B3                               (§6.9.3, CRITICAL)
❌ 🆕 v4 — Đổi L_exchange rồi chạy luôn, không chạy lại phân bố
   liq_buffer trên CALIB                                            (§6.9.2)
❌ 🆕 v4 — Dùng `notional_per_idea = L_total_D × E / max_open_D` làm
   công thức SIZE — nó đã bị thay bằng kiểm tra kết nạp  (§6.8e, CRITICAL)
❌ 🆕 v4 — Mở vị thế khi vi phạm (a) trần rủi ro HOẶC (b) trần margin,
   dù ZSS cao thế nào                                      (§6.8f, CRITICAL)
❌ 🆕 v4 — Đổi `rho` khi còn vị thế đang mở                        (§6.9.2)
❌ 🔴 v5 — CHẠY HYPEROPT dưới bất kỳ hình thức nào. Một lệnh 500
   epoch = 500 phép thử, phá huỷ N=114 trong vài giờ  (§0c.2, CRITICAL)
❌ 🔴 v5 — Bật FreqAI, Edge positioning, hoặc trailing_stop dựng sẵn
   của Freqtrade                                        (§0c.2, CRITICAL)
❌ 🆕 v5 — Đổi tham số GIỮA hai điểm quyết định (trừ sửa lỗi Hạng 1)
❌ 🆕 v5 — Đổi nội dung periodic_report.py mà không tiêu 1 trial (§12d.2)
❌ 🆕 v5 — Cho LLM truy vấn DB lệnh thô thay vì đọc báo cáo cố định (§12d.2)
❌ 🆕 v5 — Chấp nhận đề xuất của LLM có câu không trích được số  (§12d.2)
❌ 🆕 v5 — Tăng B3 bằng tay thay vì theo công thức floor(lệnh/25) (§12c.2)
❌ Nới ngưỡng PASS sau khi thấy kết quả gần đạt              (§9c.5)
❌ Đổi tham số sau D12 mà không tiêu trial dự phòng          (DR-012)
❌ Tune một tham số đã ở trạng thái FROZEN                   (§9c.3, CRITICAL)
```

## ✅ Luôn phải có

```
✅ confirmed_at_bar tách biệt swing_bar trong MỌI bản ghi zone
✅ sl_equals_zone_invalidation == true trong MỌI plan
✅ zss_recheck ghi lại ở MỌI lần xét tranche 2/3, kể cả khi fill
✅ liq_buffer_ratio ghi và audit sau mỗi lệnh
✅ DG6 kiểm tra LIÊN TỤC (không chỉ trước khi thêm tranche) suốt đời
   vị thế đã mở, tag EARLY_EXIT_A/B/C(/D nếu Short) khi trigger
✅ trend_dir(1D) và trend_dir(4H) đồng thuận trước khi vào lệnh
✅ Risk Supervisor RIÊNG cho từng tool, đọc đúng một sub-account (§6.6)
✅ D0.9 (Z0-Z3b) chạy TÁCH RIÊNG cho Long và Short, không dùng chung
   kết quả (§10.1, mới)

✅ Mọi trial có registered_at TRƯỚC executed_at
✅ Mọi tham số [CẦN CALIBRATE] ở đúng một trạng thái: TUNED hoặc FROZEN
✅ H16 + H17 chạy pass trước MỖI lần backtest
✅ Changelog liệt kê mục THÊM/SỬA/XOÁ ở mỗi phiên bản spec  (DR-009)
✅ Mọi bản ghi idea_queue có đủ ba trường mechanism/who_pays/durability
✅ session_type và data_source ghi rõ ở MỌI ý tưởng vào queue (DR-009)
✅ Query trùng lặp theo `mechanism` trước khi thêm ý tưởng mới (§9c.7.4)
✅ 🆕 v3.2 — hold_duration_bars ghi ở MỌI lệnh đã đóng, mọi arm (§4b.6)
✅ 🆕 v3.2 — DG8 kiểm tra LIÊN TỤC suốt đời vị thế, tag TIME_STOP
   tách biệt với EARLY_EXIT_A/B/C/D                                  (§4b.5)
✅ 🆕 v3.3 — Mọi ý tưởng queue có data_source ∈ {MECHANISM, EXPLORE}
   và explore_evidence nếu là EXPLORE                               (§9c.7.3)
✅ 🆕 v3.3 — Tối đa 1 vị thế/coin; cooldown 3 nến 4H sau khi đóng
   🔴 v6 ĐẢO NGOẠI LỆ: CÓ cooldown khi đóng bằng SL/DG6/DG7;
   MIỄN khi đóng bằng TP hoặc TIME_STOP                              (§1.3b)
✅ 🔴 v6 — H-1/H-2/H-3/**H-4** ghi hàng tuần khi live, CHỈ cảnh báo  (§11b.2)
✅ 🆕 v6 — DG7 (§4c) kiểm LIÊN TỤC tại mỗi mốc funding 8h, tag
   FUNDING_STOP tách biệt với EARLY_EXIT_* và TIME_STOP
✅ 🆕 v6 — `funding_paid_cumulative` và `liq_dist_pct`/`r_eff_pct`
   ghi ở MỌI lệnh đã đóng                                 (L-Z31, §6.4b)
✅ 🆕 v6 — L-Z29 (kế toán DOF tự kiểm) PASS trước khi commit N
✅ 🆕 v4 — tool_d_config.yaml commit vào git; mọi thay đổi là một
   commit riêng có dấu vết                                          (§6.9.5)
✅ 🆕 v4 — Kiểm tra kết nạp (a)+(b) chạy TRƯỚC mỗi lần mở vị thế,
   tính trên KẾ HOẠCH đầy đủ 3 tranche (D0.3/D0.5)                  (§6.8f)
✅ 🔴 v5 — L-Z24 (config Freqtrade) + L-Z25 (không hyperopt) chạy
   trước MỖI lần backtest và MỖI lần deploy                        (§0c.4)
✅ 🆕 v5 — periodic_report.py commit vào git TRƯỚC khi live       (§12d.2)
✅ 🆕 v5 — Mọi tham số đóng băng có frozen_rationale trong registry (DR-010)
✅ 🆕 v3.3 — Báo cáo D0.9 tách theo tier thanh khoản và số mẫu
   HIỆU DỤNG (không chỉ số lệnh danh nghĩa)                (§0.3c)
✅ Quy tắc quyết định (ngưỡng PASS bằng số) ghi TRƯỚC khi chạy (§9c.5)

🆕 v7 — TOÀN VẸN PHÉP ĐO (PHẦN 0d, DR-013, §8.3):
✅ measurement_guard() ở dòng đầu MỌI entrypoint E1–E8         (L-Z36)
✅ `--cache none` ở MỌI lệnh backtest/WFO                        (L-Z38)
✅ Khối provenance 7 khoá ở MỌI bản ghi kết quả                 (L-Z40)
✅ Mọi chỉ số tổng hợp tính trên pnl_abs; R = pnl_abs /
   planned_risk_usdt đóng băng lúc entry                      (DR-013)
✅ dedup_key theo order_id TỪNG TRANCHE; ghi = no-op nếu trùng (L-Z45)
✅ Mỗi lần đổi KHỐI LƯỢNG SL = một bản ghi có gap_ms            (§8.3)
✅ Ba trạng thái pending/unreadable/ok; không lính canh        (L-Z41)
✅ Ngưỡng chưa điền = +inf trong code, không phải None          (L-Z35)
✅ "Đạt" chỉ khi có bằng chứng trên đĩa từ lần chạy THẬT       (L-Z51)
✅ Khi test sai → sửa TEST, giữ ràng buộc (LD-36). Verify chính
   phép verify: TypeError không phải "đã chặn đúng" (LD-37)
✅ Mâu thuẫn phát hiện → ghi mục riêng, phân loại, chờ người
   chốt — KHÔNG âm thầm chọn một bên (LD-42)

❌ 🆕 v7 — Dùng IntParameter/DecimalParameter/… của Freqtrade     (L-Z37)
❌ 🆕 v7 — Đọc tham số Tầng B/C từ biến môi trường               (L-Z39)
❌ 🆕 v7 — Cộng/trung bình `profit_ratio`; dùng
   `initial_stop_loss_abs` làm mẫu số                          (L-Z46)
❌ 🆕 v7 — Polling API dày hơn nhịp nến; gọi tiếp sau 418/429    (§6.6)
❌ 🆕 v7 — Backfill ghi đè theo khoảng ngày; ghi cache rỗng khi
   tải hỏng                                                     (H19)
❌ 🆕 v7 — Sửa code sản xuất để chiều theo artifact của
   lookahead-analysis (FP-2/FP-3)                              (§7.2)
❌ 🆕 v7 — Đánh dấu VERIFIED cho D1–D7 bằng unit test có mock    (L-Z51)
```

---

# PHẦN 14 — CÒN MỞ (v4)

| # | Câu hỏi | Ảnh hưởng |
|---|---|---|
| 1 | `k` = 3 nến xác nhận swing — có nên khác theo biến động thị trường không, hay cố định? | §1.1, §7 |
| 2 | ZSS có nên thêm OI (open interest) làm thành phần thứ tư khi có nguồn dữ liệu đáng tin? | §1.2 |
| 3 | Zone đối diện dùng cho TP — nếu không tồn tại trong pool **~100 mã** (§0.3c) ở khung 4H, có nên mở rộng sang shadow pool lớn hơn chỉ để tìm TP (không để vào lệnh)? 🔴 v6: chỉ số **H-4** (§11b.2) giờ đo trực tiếp tần suất ca này — câu hỏi sẽ được trả lời bằng số ở D0.9 | §5.1, §11b.2 |
| 5 | Có nên giữ phương án `TP_fallback` (R-multiple) vĩnh viễn, hay chỉ là nạng tạm trong lúc pool nhỏ? | §5.1 |
| 6 🆕 | Dữ liệu Binance USDⓈ-M khả dụng có đủ dài để lockbox thoả cả (a) ≥20% VÀ (c) ≥30 lệnh không? Nếu không đủ, chọn gì: lockbox ngắn nhưng có thật, hay không có lockbox? | DR-011 |
| ~~7~~ ✅ **CHỐT v6** | Kiểm kê lại toàn bộ: 12 tunable + 8 khoá đóng băng → **N = 114**, rào ≈ **3,08**. Câu hỏi "có nên biết trước" được trả lời: có, và nó đã được làm ở D0-PRE | DR-010 |
| 8 🆕 | Nếu overlap ≥ 50% (kịch bản §9.1 cho là nhiều khả năng), N union với Tool A là bao nhiêu? Con số này có thể lớn tới mức GATE D0.9 bất khả thi về mặt toán học — cần ước lượng SỚM, không đợi tới D4 | §10.2, DR-007 |
| 9 🆕 | Ràng buộc "tách phiên IDEA / phiên PHÂN TÍCH" (DR-009) chỉ thực thi được bằng kỷ luật cá nhân. Có cơ chế kỹ thuật nào rẻ hơn không — ví dụ hai thư mục project riêng, thư mục IDEA không chứa file kết quả nào? | DR-009 |
| 10 🆕 | Nếu lockbox chỉ có ĐÚNG MỘT và mỗi ứng viên mới cần dữ liệu chưa dùng, thì ứng viên thứ hai lấy lockbox ở đâu? Phải chờ tích luỹ dữ liệu mới (~mỗi quý thêm 1 quý), hay chấp nhận lockbox ngắn dần? Đây là trần cứng cho nhịp thay thế chiến lược | DR-011, §9c.7.5 |
| 11 🆕 v3.2 | **DG8 vs TP2 trail — xung đột thật chưa giải quyết.** §4b.2 chốt DG8 áp dụng KHÔNG ĐIỀU KIỆN, kể cả khi TP1 đã chạm và TP2 đang trail một lệnh lãi. Lập luận ủng hộ: sau TP1, vị thế không còn cưỡi giả thuyết zone nữa mà cưỡi trend trail — hạn dùng của zone (§1.3) không còn áp dụng, nên cắt là mất lãi vô cớ. Lập luận phản đối: mọi ngoại lệ là một bậc tự do mới, và "đang lãi thì cho ở lại" chính là cách time stop bị vô hiệu trong thực tế. **Mặc định v3.2 = không ngoại lệ** (bảo thủ, 0 tham số thêm). Nếu D0.9 cho thấy TIME_STOP cắt nhiều lệnh lãi, đây là arm ablation riêng phải đăng ký trial, KHÔNG được sửa tại chỗ | §4b.2, §5.1 |
| 13 🆕 v3.3 | Trần gộp zone "2× zone rộng nhất" (§1.3b QT1) là con số áp từ ngoài, chưa có căn cứ. Có nên suy ra từ zone_width tối thiểu (§3.3) thay vì đặt cứng 2×? | §1.3b |
| 14 🆕 v3.3 | Tập EXPLORE dựa trên BTC/ETH tương quan 0.7-0.85 với pool giao dịch. Mức "rò rỉ" này lớn cỡ nào, và có đo được không? Nếu không đo được, có nên coi giả thuyết sinh từ EXPLORE là tốn nửa trial thay vì 0 trial? | §9c.4b |
| ~~16~~ ✅ **ĐÃ CHỐT v4** | `rho` CHỈ đổi khi danh mục rỗng (0 vị thế mở). Lý do: đổi giữa chừng làm lệnh cũ/mới khác kích cỡ, phá tính so sánh được của mẫu | §6.9.2 |
| 17 🆕 v4 | §6.8f cho số mã dao động 6–20 tuỳ zone width. Có nên đặt SÀN tối thiểu (VD ≥8 mã) để đảm bảo phân tán, tức từ chối zone quá hẹp ngay cả khi qua §6.4? Hay để tự nhiên? | §6.8f |
| ~~1~~ ✅ **CHỐT v5** | `k` = 3, đóng băng. Đây là định nghĩa swing, không phải ngưỡng | DR-010 |
| ~~4~~ ✅ **CHỐT v6 — BỎ HẲN** | `mult_cross` bị xoá. v5 đánh dấu "CHỐT" nhưng nội dung là "chờ xác nhận" — đó không phải chốt. Lý do bỏ ở §6.2 và §9.3 | §6.2 |
| 18 🆕 v5 | Tỉ lệ tái tạo ngân sách 1 trial / 25 lệnh là lựa chọn, không phải định lý. Sau 2 điểm quyết định đầu, có nên hiệu chỉnh lại bằng số mẫu HIỆU DỤNG (đã điều chỉnh tương quan) thay vì số lệnh danh nghĩa không? | §12c.2 |
| 19 🆕 v5 | Nếu `protections` của Freqtrade bị tắt hoàn toàn (§0c.3), có mất lớp bảo vệ nào mà DG1–DG8 không phủ không? Cần đối chiếu từng protection một ở D0-PRE | §0c.3 |
| 15 🆕 v3.3 | Trần nhập queue 10 ý tưởng/quý — con số này chưa có căn cứ ngoài trực giác "đủ để chọn, không đủ để khai thác". Có cách đặt nó theo nguyên tắc nào không? | §9c.7.4 |
| 12 🆕 v3.2 | `max_hold_bars` đếm bằng nến 4H (§4b.2) trong khi DG4/DG6-B đếm bằng nến 1H. Có nên thống nhất một đơn vị không, hay giữ khác nhau vì DG8 neo vào §1.3 (đơn vị 4H) còn DG4/DG6 neo vào nhịp triển khai (đơn vị 1H)? 🔴 v6 nghiêng về **giữ khác nhau** — chúng neo vào hai thứ khác nhau — nhưng phải ghi đơn vị vào TÊN BIẾN (`max_hold_bars_4h`, `dg4_bars_1h`) để không lặp lại lỗi "2×k" đã bị bác ở DR-010 | §4b.2, §4 |
| 20 🆕 v6 | Ngưỡng `DSR-adjusted expectancy` ở Nhánh 1 (§10.2) phải điền bằng số ở D0-PRE. Đặt bao nhiêu? Đặt quá cao = gần như chắc chắn FAIL sau 8 tuần; quá thấp = GATE mất ý nghĩa. Có cách suy nó từ chi phí giao dịch + funding kỳ vọng thay vì chọn tuỳ ý không? | §10.2, B6 |
| 21 🆕 v6 | Nếu Nhánh 2 chọn **Z0** (bỏ DCA), DG5 và một phần DG1–DG4 trở thành code chết, và kiểm kê DOF phải làm lại → N giảm. Nhưng N đã được dùng để tính DSR ở chính GATE vừa chạy. Có được tính lại DSR với N mới không, hay N đã đăng ký là bất biến? *(Nghiêng về: KHÔNG tính lại cho GATE đã chạy — N đăng ký là cam kết về không gian tìm kiếm. N mới chỉ áp cho vòng SAU.)* | §10.2, DR-010 |
| 22 🆕 v6 | DG7 (§4c) có thể gần như không bao giờ trigger vì DG8 (4 ngày) cắt trước. Nếu tỉ lệ trigger < 2% ở D0.9, giữ nó như lưới an toàn hay xoá để lấy lại 1 DOF? *(Nghiêng về: GIỮ. Nó rẻ — 1 DOF — và ca nó bảo vệ là ca funding cực đoan, đúng loại rủi ro đuôi mà spec này được viết để chặn.)* | §4c |
| 23 🆕 v6 | Trần 3 lần HALT / 100 lệnh và thời gian chờ 2 × `max_hold_bars` (§12c.5) là con số chọn, chưa có căn cứ ngoài "dùng lại hằng số đã có". Có nguyên tắc nào đặt chúng tốt hơn không? | §12c.5 |
| 24 🆕 v7 | **D2b:** Freqtrade có hỗ trợ `closePosition=true` cho stop order Binance Futures không? Nếu có, khoảng trống không-SL biến mất và D2c không cần đo. Nếu không, có đáng patch Freqtrade cục bộ không (→ thêm một nguồn sự thật thứ hai cho exchange layer, vi phạm LD-09)? *(Trả lời bằng đọc source ở D0-PRE.)* | §9b D2, §8.3 |
| 25 🆕 v7 | **Ngưỡng chấp nhận lệch khớp D6** (bps giữa giá khớp testnet và giá backtest giả định): điền bao nhiêu? Đây là placeholder +inf (L-Z35). Gợi ý cách suy: lệch trung vị phải nhỏ hơn biên 20% của Nhánh 2 §10.2 quy ra bps trên expectancy — nếu không, Nhánh 2 không phân biệt được DCA thật tốt hơn hay chỉ được backtest ưu ái | §9b.3, §10.2 |
| 26 🆕 v7 | `api_calls_per_min = 30` (tier_c) là ước lượng 100 mã/giờ + lề. Binance giới hạn theo weight, không theo số lệnh — cần quy đổi weight thật của các endpoint Tool D dùng (klines, positionRisk, openOrders) trước khi khoá | §6.6 |
| ~~27~~ ✅ **CHỐT v8** | N_full tính lại theo `p1_order` thật — hệ quả trực tiếp của tu chính DR-013 (2b): `planned_risk_usdt` là tổng thang KẾ HOẠCH THI HÀNH, mà kế hoạch thi hành đặt lệnh ở p1_order, không ở zone_high danh nghĩa. D0.1 là nguyên lý; "đơn giản" không phải | §3.5, §3.1, DR-013 |
| 28 🆕 v8 | Trần trả lại đặt chỗ 3 lần/giả thuyết (DR-014 §5) là con số chọn, không phải định lý — nó là lớp phòng thủ cho kênh phụ (thời lượng chạy/tiến độ fold quan sát được từ ngoài con dấu). Có cách đo độ rò của kênh phụ này để đặt trần theo nguyên tắc không? | DR-014 |
| 29 🆕 v8 | Quy mô Bước 2 của D3.5 (14 ngày / ≥ 30 sự kiện chạm mốc, gia hạn 1 lần) là cỡ mẫu chọn theo khả thi, chưa phải theo power. Sau lần chạy đầu, có nên suy cỡ mẫu từ phương sai tỷ lệ khớp quan sát được cho các lần xác nhận sau (D10)? Chú ý: chỉ được chỉnh cho lần SAU, không hồi tố | DR-015 |

---

## Ghi chú cuối

So với v1, thay đổi lớn nhất không phải là thêm chi tiết — là **loại bỏ hai điểm ăn theo Tool A một cách vô thức**: bội số ATR tuỳ ý cho SL/tranche, và bộ hệ số rủi ro dùng chung ngưỡng. Cả hai giờ đều **suy ra từ chính cấu trúc zone**, hoặc **hiệu chỉnh độc lập** với lý do tường minh.

Cái giá của độc lập này là rõ ràng: nhiều chỗ `[CẦN CALIBRATE]` hơn v1, vì không còn được mượn số đã "quen mắt" từ Tool A. Đó là đánh đổi đúng — số mượn mà không kiểm chứng nguy hiểm hơn số trống chờ calibrate.

**Hết v7.**

---

# PHỤ LỤC A — CĂN CỨ CỦA CÁC BẢN VÁ v3.1 → v3.3

> Giữ lại để mọi thay đổi ở v4 đều truy được về một lỗi cụ thể trong v3, không phải "thêm cho chặt".

Ghi lại để bản vá không bị coi là "thêm thủ tục cho vui":

```
LỖI 1 — §10.2 yêu cầu "DSR-adjusted expectancy ≥ 20%" nhưng KHÔNG ĐỊNH
        NGHĨA N. DSR là hàm của N (số trial). Không có N → không có DSR
        → điều kiện GATE là câu chữ, không phải phép kiểm tra.

LỖI 2 — MÂU THUẪN TRỰC TIẾP giữa §9.3 và §9.5:
          §9.3: kế thừa "ngân sách 5 giả thuyết/quý" (§14D v10)
          §9.5: "việc HIỆU CHỈNH các ngưỡng [CẦN CALIBRATE] LÀ MỘT LẦN
                 THỬ, phải ghi vào trial_registry"
        Kiểm kê thực tế v3: 26 lần xuất hiện [CẦN CALIBRATE], trừ 6 lần
        là ghi chú meta → 20 vị trí nội dung, chứa ~24 BẬC TỰ DO.
        24 tham số không thể nằm trong 5 giả thuyết/quý. Hai điều khoản
        này chưa từng được hoà giải ở bất kỳ đâu trong tài liệu.

LỖI 3 — `trial_registry` được THAM CHIẾU 3 lần (§6.2 hệ số 5, §9.5,
        checklist Phần 13) nhưng CHƯA TỪNG ĐƯỢC ĐỊNH NGHĨA SCHEMA cho
        Tool D. Một trường bắt buộc mà không có cấu trúc = không thực thi.

LỖI 4 — "out-of-sample" xuất hiện ĐÚNG 1 LẦN trong 1.108 dòng (§10.1,
        dạng gợi ý "kiểm tra out-of-sample riêng cho DG5/ZSS/DG6 trước
        khi tin"). Không có định nghĩa tập dữ liệu, không có mốc thời
        gian, không có cơ chế niêm phong. Walk-forward (D3/D9) KHÔNG
        thay thế được: WFO vẫn để người vận hành nhìn kết quả rồi quay
        lại chỉnh ngưỡng — kênh nhiễm đi qua CON NGƯỜI, không qua code.
        §9.3 đã tự thừa nhận rủi ro này ("nhiễm chéo qua chính bạn")
        nhưng không có cơ chế nào chặn nó.

LỖI 5 — Toàn bộ tài liệu KHÔNG có một dòng nào ghi vai trò của LLM
        trong quy trình soạn thảo, dù v1→v3 được soạn bằng LLM. Hệ quả
        đã xảy ra thật: §9b ghi nhận danh sách giả định D1-D5 BỊ RỚT
        MẤT IM LẶNG giữa các phiên bản, roadmap vẫn trỏ tới nội dung
        không còn tồn tại. Đây chính xác là chế độ hỏng của quy trình
        soạn thảo không truy vết được.

LỖI 6 — PBO (Probability of Backtest Overfitting) không xuất hiện lần
        nào. DSR và PBO đo hai thứ khác nhau và bù nhau; với 5 arm × 2
        hướng, CSCV là khả thi về mặt tính toán.

🆕 v3.2 ────────────────────────────────────────────────────────────

LỖI 7 — KHÔNG CÓ MAX HOLD. Dò toàn bộ 1.108 dòng: không có max_hold,
        không có timeout, không có time stop. Đường đi thực tế của
        một vị thế:
           DG1-DG5  → chỉ chặn tranche mới, KHÔNG đóng
           DG4      → giới hạn CỬA SỔ TRIỂN KHAI (8 nến 1H), không
                      phải giới hạn hold
           DG7      → funding drain, nhưng nằm trong bảng "GATE KÍCH
                      HOẠT TRANCHE" → CŨNG CHỈ CHẶN TRANCHE
           DG6-A    → cần ATR giãn ≥1.8×
           DG6-B    → cần giá CHƯA TỪNG đóng cửa vượt lại p1
                      🔴 Đóng cửa vượt p1 MỘT LẦN → B chết vĩnh viễn
           DG6-C/D  → cần giá đi 70% (50%) về phía SL
           TP/SL    → phụ thuộc giá, không phụ thuộc thời gian

        KỊCH BẢN KHÔNG AI CHẶN ĐƯỢC: LONG khớp p1 → giá nhích lên
        đóng cửa trên p1 một lần (DG6-B chết) → đi ngang trong vùng
        lãi mỏng, chưa chạm TP1, chưa về 70% phía SL, trend chưa đảo.
        → A/B/C đều fail, DG7 không đóng, KHÔNG CÓ TIME STOP.
        → Vị thế 5x nằm trả funding VÔ THỜI HẠN.

LỖI 8 — MÂU THUẪN NỘI BỘ §1.3 vs vòng đời vị thế:
           §1.3: zone hết hạn sau 40 nến 4H (~6,7 ngày) vì "zone quá
                 cũ mất liên quan"
           Thực tế: vị thế DỰA TRÊN zone đó không có hạn dùng nào
        Nếu giả thuyết chỉ sống 6,7 ngày, vị thế cược vào giả thuyết
        đó KHÔNG THỂ sống lâu hơn. Đây là mâu thuẫn logic, không phải
        thiếu sót nhỏ.

LỖI 9 — ABLATION KHÔNG KIỂM CHỨNG PHẦN 2. Cả năm cấu hình Z0-Z3b đều
        CHỨA NGUYÊN bộ lọc trend (trend_dir 1D + xác nhận 4H + ADX≥20
        + tuổi ≥5 ngày) = 4 điều kiện lọc. Không arm nào bật/tắt nó.
        → Nếu tầng 1D vô dụng hoặc có hại (lọc mất setup tốt), thiết
          kế ablation hiện tại KHÔNG THỂ PHÁT HIỆN.
        → Vi phạm chính nguyên tắc "chỉ báo phải tự chứng minh chỗ
          đứng bằng ablation". §2.4 (BTC regime) được đưa vào ablation
          vì "mới", còn §2.1/2.2/2.3 được miễn trừ chỉ vì có mặt từ
          v1 — đó là đặc quyền theo THÂM NIÊN, không phải BẰNG CHỨNG.
```

---


---

# PHỤ LỤC B — CĂN CỨ CỦA BẢN VÁ v6

> Cùng nguyên tắc với Phụ lục A: mọi thay đổi ở v6 phải truy được về một lỗi cụ thể trong v5, không phải "thêm cho chặt". Đánh số tiếp từ LỖI 9.

```
════════ NHÓM I — KIỂM KÊ SAI (nguyên nhân gốc, lan ra 14 vị trí) ════════

LỖI 10 — PHÉP TRỪ 26 → 16 KHÔNG RA ĐƯỢC.
         DR-010 khai "đóng băng 9 tham số → 26 giảm còn 16". Nhưng `k`
         và `ADX threshold` CHƯA TỪNG có trong bảng 26, nên đóng băng
         chúng giảm 0. Và gộp funding chỉ giảm được 1 (bảng 26 chỉ có
         HAI mục funding), không phải 2.
         Trừ đúng: −6 → 20. Không phải 16.
         → N = 134 là một con số không ai cộng ra được.
         → Lan sang: B1, N, rào DSR, §10.2, §12c.2, DR-011, roadmap D4.

LỖI 11 — BA THAM SỐ TỰ DO KHÔNG BAO GIỜ ĐƯỢC ĐẾM.
         §3.1  w = [0.35,0.35,0.30]  — §3.1 tự khai "1 bậc tự do"
               ngay tại chỗ, nhưng không có trong bảng kiểm kê
         §4/DG7  ngưỡng 0.3 × R_eff
         §5.1  TP_fallback 4.0 × R_eff và 1.5 × R_eff
         → Kiểm kê thật là 28, không phải 26.

LỖI 12 — SỐ LIỆU LỖI THỜI Ở 14 VỊ TRÍ.
         174/184/192/194 (5 chỗ) · "24 bậc tự do" (3 chỗ) · "16 tham
         số" · "5 cấu hình PBO" · "BẢY cấu hình" D4 · "B2 = 14 trial"
         · "N = 184" · "pool 30-50 mã" · "D0.5" (đã đổi tên ở v4)
         · "rank 31-60" trong H1-D (§0.3 đã BÁC BỎ cơ chế này).

════════ NHÓM II — MỘT THAM SỐ, NHIỀU GIÁ TRỊ/TRẠNG THÁI ════════

LỖI 13 — `k` có BA trạng thái đồng thời: `tier_b` (đổi được, 1 trial),
         `tier_frozen` (mở khoá +6), §12c.3 Cấp C (không bao giờ).
         Dòng `k_swing_confirm: 3` xuất hiện HAI LẦN trong cùng file
         YAML, ở hai tier khác nhau.

LỖI 14 — DG6-B có HAI giá trị: §4.1 ghi "≥ 6 nến 1H", DR-010 đóng
         băng ở "8 nến (KHÔNG phải 6)". Code không xác định được.
         Đồng thời §12c.3 vẫn để `DG6-A/B/C` ở Cấp B "đổi được" trong
         khi B đã đóng băng — vi phạm chính §6.9.3.

LỖI 15 — `w_a/w_b/w_c` có BA giá trị: 0.4/0.3/0.3 (§1.2), 1/3
         (DR-010 thân bảng), [0.333,0.333,0.334] (YAML) — và ghi chú
         DR-010 dòng cuối lại đề xuất 0.4/0.3/0.3 lần nữa.

LỖI 16 — `mult_cross` được mô tả BA kiểu ở BỐN nơi: "tuỳ chọn, không
         tính vào mặc định" (§6.2) · "VẪN GIỮ P0" (§9.3) · "✅ CHỐT
         v5 — chờ xác nhận bỏ hay giữ" (§14 #4, tự mâu thuẫn trong
         một dòng) · "cộng mult_cross" như việc phải làm (§11 H2).

LỖI 17 — `mult_dd` ngưỡng 8% vừa là [CẦN CALIBRATE] + 1 DOF (tiêu 6
         trial), vừa là Cấp C "không bao giờ đổi" (§12c.3), vừa là 1
         trong BA TẦNG CHẶN vòng lặp thua lỗ (§12b.2). Không thể vừa
         là thứ được tối ưu trên backtest vừa là cầu dao.

════════ NHÓM III — CÔNG THỨC KHÔNG TÍNH ĐƯỢC / KHÔNG ĐỊNH NGHĨA ════════

LỖI 18 — GATE §6.4 (CRITICAL) SAI THANG ĐO.
         "Buffer thanh lý = (p1 − liq_price)/p1"  ← tỷ lệ %
         "NẾU buffer < 8 lần đệm SL"               ← bội số
         Không so sánh được. Trong khi `liq_buffer_ratio` là trường
         BẮT BUỘC của Decision Log, là L-Z3 CRITICAL, và là tiêu chí
         GATE D0.9. Thêm: v5 tính trên p1 thay vì p_avg kế hoạch →
         gate PASS ở tranche 1 rồi VI PHẠM ở tranche 3.

LỖI 19 — `L_BASE` là THAM SỐ MỒ CÔI. §6.8f chốt công thức định cỡ
         DUY NHẤT và L_BASE không có trong đó. Nó không tác động vào
         bất kỳ con số nào được tính, nhưng chiếm 1 DOF = 6 trial.

LỖI 20 — `deployed_ratio_tool_d` (§6.2 hệ số 6) KHÔNG BAO GIỜ ĐƯỢC
         ĐỊNH NGHĨA. Một biến không định nghĩa nhân thẳng vào size.
         Tuỳ cách đọc, hệ số này hoặc có nghĩa, hoặc là code chết
         (nếu đọc là "Σ margin / E_D" thì nó trùng đúng ngưỡng 0.85
         của §6.8f và không bao giờ kích hoạt).

LỖI 21 — `mult_edge = "như công thức Tool A"` VI PHẠM TRỰC TIẾP
         tuyên bố zero-dependency ở header ("không tra ngược sang
         Tool A") và ở §11 ("Zero-dependency đã chốt"). Một công
         thức không viết ra được là một công thức không code được.

LỖI 22 — `L_D_max` là NGUỒN SỰ THẬT THỨ HAI cho ràng buộc margin.
         §6.8f tự chứng minh L_D_max ≡ 0.85 × L_exchange. YAML v5
         đặt 2.5 với L_exchange = 3 (0.85×3 = 2.55) — trần "riêng"
         chỉ chặt hơn trần thật 2%.

════════ NHÓM IV — LOGIC ĐẢO NGƯỢC / LỖ HỔNG ════════

LỖI 23 — GATE D0.9 KHIẾN KẾT CỤC TỐT NHẤT KÍCH HOẠT ĐIỀU KHOẢN DỪNG.
         §10.1: "NẾU Z0 ≥ Z3 → BỎ DCA. Đây là kết quả TỐT."
         §10.2: tiêu chí đầu tiên là "{Z3,Z3b} vượt Z0 ≥ 20%", kết
                bằng "Thiếu MỘT tiêu chí → DỪNG".
         Nặng hơn: KHÔNG có tiêu chí PASS độc lập nào cho Z0 — toàn
         bộ §10.2 là so sánh tương đối, nên Z0 có thể thắng Z3 mà
         vẫn là hệ thống thua tiền, và GATE không phát hiện được.

LỖI 24 — NGOẠI LỆ COOLDOWN ĐẢO NGƯỢC LÝ DO TỒN TẠI CỦA CHÍNH NÓ.
         §1.3b QT4 nói lý do có cooldown là chặn "một cú sập kích
         hoạt liên tiếp nhiều lệnh trên cùng coin", rồi ngay dưới
         miễn cooldown cho ca đóng bằng SL — mà đóng bằng SL CHÍNH
         LÀ ca một cú sập. Đồng thời DG6-A (ATR giãn ≥1.8×, cũng là
         cú sập) lại BỊ cooldown.

LỖI 25 — FUNDING DRAIN CHỈ CÓ CƠ CHẾ CHẶN, KHÔNG CÓ CƠ CHẾ ĐÓNG.
         §4b.1(b) tự chẩn đúng nhưng giao việc cho DG8 — mà DG8 neo
         vào TUỔI ZONE, không neo vào CHI PHÍ. Trong 4 ngày có 12
         lần funding; chi phí có thể vượt 0.3 × R_eff từ ngày thứ 2
         mà không gate nào đóng vị thế. Cùng cấu trúc với LỖI 7,
         khác trục (chi phí thay vì thời gian).

LỖI 26 — ĐƯỜNG NHANH 15m MỞ BỀ MẶT LOOKAHEAD THỨ HAI VÀ VI PHẠM
         CHECKLIST CRITICAL CỦA CHÍNH SPEC.
         (a) `merge_informative_pair` ghép khung LỚN → nhỏ; ghép 15m
             vào dataframe 1H là chiều NGƯỢC LẠI — tại lúc nến 1H mở,
             ba nến 15m còn lại chưa tồn tại. PHẦN 7 chỉ phủ zone.
         (b) Cho vào tranche 1 mà không cần (a)/(b)/(c) — trong khi
             §13 ghi "❌ Mở tranche 1 khi CHƯA có xác nhận
             price-action — CRITICAL", và (c) volume là BỔ NGỮ BẮT
             BUỘC cho (a) theo PHẦN 3b.

LỖI 27 — `mult_dd` = 8% BẰNG ĐÚNG `daily_loss_budget_pct` = 8%.
         Nghĩa là đúng MỘT ngày xấu tối đa (20 lệnh cùng chạm SL với
         tương quan = 1) là hệ thống tự tắt VĨNH VIỄN. Một sự kiện
         mang thông tin về THỊ TRƯỜNG kích hoạt phản ứng dành cho
         thông tin về EDGE.

════════ NHÓM V — MỤC KHAI TRONG CHANGELOG NHƯNG CHƯA LÀM ════════

LỖI 28 — Changelog v5 khai "SỬA §11b — thêm H-4", và §12d.2 đã dùng
         H-4 trong periodic_report.py, nhưng §11b.2 vẫn chỉ có ba chỉ
         số và vẫn lập luận "vì sao chỉ 3 chỉ số". Một chỉ số được
         tính mà không có định nghĩa là một chỉ số không diễn giải được.

LỖI 29 — Checklist §13 vẫn cấm tuyệt đối "để LLM đọc kết quả định
         lượng rồi đề xuất thay đổi" — mâu thuẫn với ngoại lệ §12d
         mà chính v5 vừa mở ở DR-009.

LỖI 30 — DR-011 ghi "chạm ĐÚNG MỘT LẦN" nhưng quy tắc quyết định lại
         ghi "Hướng: Long / Short / cả hai, chạy tách". Chạy tách hai
         hướng = 2 lần chạm = L-Z13 (kiểm ĐÚNG 1 bản ghi) fail.

LỖI 31 — §2b.1 bảng chân trời vẫn ghi zone "12h để xác nhận" — phản
         ánh thiết kế NHỊ PHÂN đã bị §7.4 thay bằng `confirm_ratio`
         liên tục (dùng được từ i+1). Lập luận §2b.2 về độ trễ đang
         dựa trên con số cũ.

LỖI 32 — §6.9.2 bảng Tầng A lặp `daily_loss_budget_pct` HAI DÒNG,
         trỏ hai mục khác nhau (§6.8d và §6.8f).

LỖI 33 — §2.4 (BTC regime) tiêu 1 DOF = 6 trial nhưng KHÔNG có arm
         ablation nào trong 9 cấu hình bật/tắt được nó, và không nằm
         trong điều kiện vào lệnh mặc định §2.5. Vi phạm đúng nguyên
         tắc mà LỖI 9 được viết ra để sửa.

════════ HAI LỖI TRONG CHÍNH ĐỀ XUẤT SỬA — ghi lại để truy vết ════════

LỖI 34 — Đề xuất ban đầu của bản vá v6 là "giữ DG7 chặn tranche tại
         0.3 và THÊM DG9 đóng vị thế tại 0.3". Cùng ngưỡng → đóng
         vị thế THỐNG TRỊ chặn tranche → DG7 thành dead code.
         → Sửa: DG7 CHUYỂN NHÓM, không thêm gate mới (§4c.1).

LỖI 35 — Đề xuất ban đầu cho thang drawdown là "HALT tại 8%, mở lại
         khi dd ≤ 5% HOẶC tại điểm quyết định". DEADLOCK: dừng mở
         lệnh → không có lệnh đóng → dd đứng yên VÀ không bao giờ đủ
         100 lệnh cho điểm quyết định.
         → Sửa: mở lại theo THỜI GIAN LỊCH + nửa size (§12c.5).
```

> 🔑 **Mẫu hình chung của 26 lỗi trên, ghi lại một lần:** không lỗi nào là lỗi kiến thức. Tất cả đều là lỗi **đồng bộ** — một quyết định được ghi ở nơi này nhưng nơi kia chưa cập nhật, hoặc một con số được sửa ở một chỗ mà năm chỗ tham chiếu nó thì không. Đây chính xác là chế độ hỏng mà §9b (sự cố D1-D5 rớt mất im lặng) và DR-009 (ràng buộc changelog) đã được viết ra để chặn — và nó vẫn xảy ra ở quy mô lớn hơn. Kết luận thực dụng: **ràng buộc bằng văn bản không đủ; phải có test tự động.** Đó là lý do v6 thêm L-Z29 (kế toán DOF tự kiểm), L-Z32 (grep tham chiếu đã xoá) và L-Z33 (grep 15m) vào H16 — ba thứ máy kiểm được trong vài giây, thay cho việc người đọc lại 3.400 dòng.


---

# PHỤ LỤC C — 🆕 v7: ÁNH XẠ BÀI HỌC TOOL A → SPEC, VÀ NHỮNG BÀI HỌC KHÔNG ÁP DỤNG

> Nguồn: `bai-hoc-tu-tool-a-cho-spec-tool-d.md` (06/09/2026), rút từ `CLAUDE.md`, `TASKS.md`, `back-end-note.md` của Tool A. Nguyên tắc: **chỉ lấy cơ chế, không lấy kết luận**. Mỗi bài học được đọc lại với câu hỏi *"Tool D có cùng cấu trúc lỗi này không?"* — không phải *"Tool A đã làm gì?"*.

## C.1. Áp dụng nguyên (31)

| LD | Nội dung | Vào § | Test |
|---|---|---|---|
| 01 | Guard file tham số ẩn | §0d.1 | L-Z36, L-Z37 |
| 02 | Guard phủ mọi entrypoint, danh sách đóng | §0d.2 | L-Z36 |
| 03 | `--cache none`; cache tự viết mang hash | §0d.3 | L-Z38 |
| 04 | Env chỉ cho vận hành; "điểm kiểm soát" | §0d.4 | L-Z39, CTRL |
| 05 | Khối provenance 7 khoá | §0d.5, §9c.2 | L-Z40 |
| 06 | "Bot sai" vs "tầng đo sai" — hỏi trước | §0d.7 | — |
| 07 | `pnl_abs`, không `profit_ratio`; ghép fold bằng nhân | DR-013 | L-Z46, L-Z47 |
| 09 | Một nguồn sự thật; trùng lặp có chủ đích phải ghi | §6.6(2), §4c.2 | L-Z44 |
| 10 | Ba trạng thái dữ liệu; cấm bịa 0.0 | §0d.6, §12d.2 | L-Z41 |
| 11 | `adjust_trade_position` tại giá mở nến | §9b D6, §3.5, §9b.3 | L-Z50 |
| 12 | Backtest không có sổ lệnh; khớp/trượt là giả định | §3.5 | — |
| 13 | `PO` không `limit_maker`; `price_side=same`; TTL khớp spec | §3.5 | L-Z42 |
| 14 | Funding: cột `open`, native `funding_fees`, âm = trả | §4c.2 | L-Z43 |
| 15 | Ba lớp dương tính giả lookahead | §7.2 | — |
| 17 | Đóng băng giá trị lúc entry qua custom_data; test ổn định | §8.3, §9b D7 | L-Z49 |
| 19 | `dedup_key` theo order_id từng tranche | §8.3 | L-Z45 |
| 20 | Append-only tuyệt đối | §8.3 | — |
| 22 | SL trên sàn; supervisor không import bot; LIQUIDATED = dừng | §6.6(1)(2) | L-Z44 |
| 23 | Trần API; 418/429 dừng ngay; lùi giờ phân tầng | §6.6(3), tier_c | — |
| 26 | Bắt lỗi theo từng endpoint | §6.6(4) | — |
| 27 | Backfill: sao lưu + gộp + verify byte-for-byte | H19 | — |
| 28 | Độ phủ dữ liệu; cấm suy nguyên nhân từ khoảng trống | H19 | — |
| 29 | Survivorship bias; đổi pool = số cũ vô hiệu | H1-D | — |
| 30 | N phải nối vào code | §9c.6 | **L-Z34** |
| 31 | Ngưỡng chốt trước; placeholder fail-closed | §10.2, §9b.3 | **L-Z35** |
| 32 | "Đạt" cần bằng chứng trên đĩa từ lần chạy thật | §9c.6 | L-Z51 |
| 33 | Tách "đã audit" khỏi "đã đạt" | §0d.6, §12d.2 | L-Z41 |
| 34 | Trial bị huỷ: quy tắc "đã tiêu" | §9c.2 quy tắc 4 | L-Z11 |
| 35 | Đại lượng chỉ có tên → công thức / placeholder / xoá | §1.2 touch, §6.2 corr_pool | — |
| 36–42 | Kỷ luật quy trình (sửa test không nới code; verify phép verify; đọc source; guard trước việc tốn giờ; `git show`; không tự áp gợi ý LLM; ghi mâu thuẫn không tự chọn) | §13, §0d, D0-PRE | — |

## C.2. Áp dụng CÓ SỬA (6) — vì Tool D không cùng cấu trúc lỗi

| LD | Tool A nói | Vì sao không bê nguyên | Tool D làm |
|---|---|---|---|
| **08** | Đọc lại đúng con số bot ghi làm mẫu số R; hỏi "R theo tranche 1 hay p_avg?" | Câu hỏi đặt sai khung: cả hai đều là GIÁ, mà giá đổi theo tranche. Thứ bất biến suốt vòng đời trade nhiều tranche là **ngân sách rủi ro kế hoạch** (D0.1) | R = `pnl_abs / planned_risk_usdt` (DR-013). Trade khớp 1 tranche rồi SL có ∣R∣ < 1 — đó là thông tin, không phải lỗi |
| **16** | "Với DCA thì SL bị DỜI sau mỗi tranche ⇒ tần suất cao" | **Sai với Tool D:** D0.2 cấm dời **giá** SL. Thứ đổi là **khối lượng** lệnh stop. LD-16 đúng về tần suất, sai về bản chất | D2 tách ba mệnh đề a/b/c; câu hỏi thật là **khoảng trống** và **closePosition** (§9b D2, §8.3). v6 cũng sai theo hướng ngược lại — nói D2 "phá D0.2" |
| **18** | Rà mọi điểm gọi đọc `self.<param>.value` | Chỉ cần thiết khi dùng `*Parameter`. Tool D cấm hyperopt → không có lý do dùng `*Parameter` | **Cấm `*Parameter` luôn** (§0d.2, L-Z37). Lớp lỗi biến mất thay vì được canh |
| **21** | "Mỗi lần dời SL cũng là một bản ghi" | Cùng lỗi với LD-16 | "Mỗi lần đổi **khối lượng** SL = một bản ghi, kèm `gap_ms`" (§8.3) |
| **11** (hệ quả) | Đo lệch khớp tranche ở testnet | Đúng, nhưng chưa đủ: lệch này **thiên vị một chiều** giữa arm DCA và Z0 — Tool A không có ablation kiểu này nên không gặp | Ghi tường minh ở §3.5: Nhánh 2 §10.2 phải **đọc lại** sau D10; ngưỡng lệch là placeholder +inf (câu hỏi mở #25) |
| **Ma trận ưu tiên** LD-18 "làm khi bắt đầu hyperopt" | — | Tool D không bao giờ bắt đầu hyperopt | Xếp lại thành 🌟 Ngôi Sao dưới dạng L-Z37 (1 dòng grep), không phải 💤 |

## C.3. KHÔNG áp dụng (5) — và vì sao

| LD | Nội dung | Lý do không đưa vào spec |
|---|---|---|
| **24** | Auto-restart đếm-rồi-dừng trong code | Hạ tầng hosting, không phải chiến lược hay đo lường. Đúng nhưng thuộc runbook vận hành, không thuộc spec — đưa vào đây là làm loãng (chính file bài học cũng thừa nhận tiêu chí này ở mục 4 phần phản biện) |
| **25** | Ổ đĩa mount che khuất file trong image | Cùng lý do. Ghi vào runbook triển khai, không phải spec |
| **Phản biện #1** | Kết luận về định cỡ theo notional vs rủi ro | File bài học tự loại — đúng. Tool D đã có Z0-S1 và lập luận riêng ở §3.4b. Thứ đáng lấy là **phương pháp chẩn đoán** (tương quan hạng vốn-cấp ↔ kết quả; phản chứng giữ tập lệnh đổi cách định cỡ) — nhưng phương pháp đó chính là arm Z0-S1 đã có, không cần thêm |
| **Phản biện #3** | "Cân nhắc số tiêu chí gate theo khả năng đo thật" | Ý kiến hợp lý nhưng **không có việc phải làm**: 12 tiêu chí Nhánh 1 đều đo được ở D4 trên backtest. Thứ được lấy là LD-33 (hiển thị "đã audit N/M") để biết cái nào chưa đo — không cắt tiêu chí |
| **Phản biện #4** | Kỷ luật "chỉ code khi được ra lệnh" | Quy tắc quy trình chung, không phải bài học từ sự cố. Đã là cách làm việc hiện tại |

## C.4. Điều v7 KHÔNG thay đổi — nói rõ để không ai tưởng đã đổi

```
• N_ĐĂNG_KÝ = 114. Không thêm tham số tunable. Ba hằng số mới
  (entry_order_ttl = 3 nến §3.3b, corr_window = 30 ngày, api_calls_per_min)
  đều là ĐỊNH NGHĨA hoặc Cấp C — L-Z29(b) không đổi.
• Không ngưỡng, công thức, kết luận chiến lược nào của Tool A được
  đưa vào. File bài học đã lọc; Phụ lục này kiểm lại lần hai.
• Toàn bộ v6 giữ nguyên trừ 11 mâu thuẫn còn sót (changelog).
```

> 🔑 **Mẫu hình chung của 42 bài học, ghi một lần:** Tool A không thua vì chiến lược. Tool A thua thời gian vì **tầng đo lường** — và mọi sự cố nặng đều có dạng *"một đầu vào không ai ghi lại"*. v6 đã chặn lớp lỗi *đồng bộ tài liệu* bằng test tự động (L-Z29/32/33). v7 chặn lớp lỗi *đồng bộ giữa tài liệu và con số* bằng cùng cách: guard, provenance, dedup, fail-closed — tất cả là **cơ chế máy kiểm được**, không phải lời dặn.
