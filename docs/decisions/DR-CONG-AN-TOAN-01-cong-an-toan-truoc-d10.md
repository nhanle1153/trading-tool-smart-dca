# DR-CONG-AN-TOAN-01 — Cổng an toàn trước D10 cho MỌI ứng viên

> **Ngày chốt:** 27/09/2026 · **Người quyết:** chủ dự án (duyệt kế hoạch phân tích 4 việc "trước D12", trả lời 3 câu) ·
> phiên mã `bcfaf7f8` soạn. **Mã việc:** `TD-0440` (DR này) · thi hành `TD-0441`…`TD-0445` + `TD-0269`, `TD-0272`,
> `TD-0385` (Khối 45 `TASKS.md`, đặt chỗ `acdbd33`).
> **Chi phí:** 0 trial, không chạm dữ liệu thị trường.
> Commit RIÊNG và TRƯỚC mọi dòng mã (khuôn `DR-TANG-CHAN-01`). Chỉ THÊM — chữ các DR cũ giữ nguyên.

## 1. Câu hỏi

Ba việc bảo vệ vốn — stress thanh lý (`TD-0269`), thang sụt vốn (`TD-0270`), sự cố vận hành có răng (`TD-0272`) — nằm
ở D6–D7, chỉ ứng viên **nhiều biến thể** đi qua. Ứng viên **một cấu hình** (loại cửa CHỌN đang nhắm) đi thẳng
D10 → D11 → D12 (`DR-VONG-DOI-01` §2 bước 7), và `DR-TRIEN-KHAI-01` §3 không có điều kiện tương đương. Ba dòng đó mang
cờ 🚩 *"xem lại trước D10 của ứng viên kế tiếp"*. Câu trả lời đo trên đĩa 27/09/2026: **chưa có tương đương**.

## 2. Hiện trạng đo trên đĩa 27/09/2026

1. `TD-0237`/`TD-0238` (kế hoạch cỡ lệnh + đỉnh equity sống qua restart) chỉ phủ `ZoneAbsorption`.
2. 418/429: chỉ test client riêng của Tool D (`binance_public.py`); bot đặt lệnh qua Freqtrade/ccxt — đường đó không có test.
3. Thiếu key: có ở `ops/live_d10.py` và `ops/risk_supervisor_daemon.py` (`TD-0242`, `TD-0384`).
4. LIQUIDATED: Supervisor dừng **một** bot nó trỏ tới, có cờ đỏ; chỉ chạy ở profile `d10`.
5. Stress thanh lý: có mảnh tính (`ablation/thanh_ly.py`, `ablation/chi_so_export.py`), **không** có mã kịch bản nào.
6. Thang sụt vốn: Khối 44 (`DR-TANG-CHAN-01`) đang thi hành cho mọi chiến lược.
7. Bộ đo ba ngưỡng D10 (`TD-0385`): chưa có; D10 chưa từng chạy live.

## 3. Quyết định — chủ dự án chốt 27/09/2026

1. **Cổng áp MỌI ứng viên, chặn TRƯỚC D10** (không chỉ trước D12) — D10 đã là tiền thật; thiếu kiểm thì lần đầu gặp sự
   cố rơi vào lúc có tiền. Bật D10 cần **đủ cả bốn**:
   - **(a)** Khối 44 ✅ (`TD-0434`…`TD-0438`; `MT-40` đóng). Thay `TD-0270` — không code riêng.
   - **(b)** Bộ kiểm sự cố `TD-0272` xanh trên **đúng** chiến lược + bộ khởi chạy sẽ lên tiền: restart giữa vị thế · 418/429
     · thiếu key · thanh lý (d).
   - **(c)** Stress thanh lý `TD-0269` trên **cấu hình cuối** của ứng viên đạt tiêu chí `DR-D6D8-01` §4.1 ở mọi kịch bản
     (`liq_buffer_ratio ≥ 8`, `max_single_trade_loss / risk_budget ≤ 1.15`); biên độ kịch bản theo đúng luật §4.1 (nguồn
     công khai ngoài repo, × 1,5, commit TRƯỚC lần chạy đầu). Kịch bản làm vỡ tiêu chí ⇒ không bật D10, trình chủ dự án.
   - **(d)** **Thanh lý ⇒ dừng MỌI bot cùng tài khoản sàn** + cờ đỏ; mọi bộ khởi chạy tiền thật đọc cờ và từ chối. Dry-run
     không có thanh lý thật nên không thuộc phạm vi.
2. **`TD-0385` dựng đủ bản DCA ngay** (ba ngưỡng `DR-D11-01` §5), không chờ ứng viên. Ứng viên không DCA dùng nguyên tắc
   N/A của `DR-D10-02` §6.1 (`MT-43`) như cũ.
3. **Máy thi hành, không lời khai:** `ops/live_d10.py` `main()` đọc artifact bằng chứng (b)(c) gắn `git_sha` cấu hình cuối;
   thiếu hoặc lệch ⇒ từ chối khởi động (fail-closed, N6) — `TD-0445`.
4. **Phần riêng chiến lược** của (b) (vd kế hoạch cỡ lệnh sống qua restart kiểu `TD-0237`) thành **mục bắt buộc của DR
   thiết kế D0** mỗi ứng viên (`DR-VONG-DOI-01` §2 bước 1), kèm test theo khuôn `tests/lock/test_td0237_*`.

## 4. Ghi nhận cách đọc (không phải quyết định mới)

- D6 khi `n < 30`: `DR-D11-01` §5.1 đòi *"đúng phương pháp `DR-D35-01` §4"*, mà §4 đó dùng **max** khi `n < 30`
  (fail-closed). Lệnh cấm thay phân vị bằng max ở `DR-D11-01` §5.2 viết cho `gap_ms`, không cho D6. Bộ đo `TD-0385` theo
  cách đọc này và báo thẳng `n`. Chủ dự án đọc khác ⇒ ghi `MT` 🟡, sửa bộ đo.

## 5. Ngoài phạm vi

- Không đổi thang 5/8/20, ngưỡng 8 / 1.15, ba ngưỡng D10, `N`, rào `h`.
- Không đổi luật D5–D9 cho ứng viên nhiều biến thể; với họ, `TD-0269`/`TD-0272` vẫn là việc D7 như `DR-D6D8-01`.
- Không mở lại D10 cho IQ-0003 (`DR-KET-CUC-IQ0003-01`).

## 6. Quan hệ với DR khác

- Bổ sung `DR-VONG-DOI-01` §2 bước 7 và `DR-TRIEN-KHAI-01` §3: cổng này đứng **trước** D10, bốn điều kiện D12 giữ nguyên.
- `DR-TANG-CHAN-01`: điều kiện (a).
- `DR-D6D8-01` §4.1: tiêu chí và luật biên độ của (c).
- `DR-D11-01` §5, `DR-D10-02` §2 mục 5 và §5.3: phép đo và cách ghi kết cục của `TD-0385`.
