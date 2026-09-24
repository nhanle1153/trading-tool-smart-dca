# DR-TRIEN-KHAI-01 — Triển khai liên tục D5 → D9.5 trên dữ liệu lịch sử, dry-run song song, giữ cổng tiền D12

> **Ngày chốt:** 19/09/2026 · **Người quyết:** chủ dự án (phiên mã `dd855fee`: *"không chờ 1/10 hay 1/12… triển khai ngay
> để tool hoàn thiện, dựa vào backtest và walk-forward lịch sử, sau đó dry-run"*; trả lời 3 câu: dry-run song song ngay ·
> giữ cổng tiền ở D12 · suất (d) hạ xuống phụ, không chặn; duyệt kế hoạch).
> **Chi phí:** 0 trial cho chính DR này. Các suất sẽ tiêu ở D5 (≤ 16 B1) và D9 (≤ 16) theo `DR-D5-01`/`DR-D9-01`.
> Mã `DR-TRIEN-KHAI-01` đặt chỗ bằng commit `a97cc4c` (N12 mục 7c) trước khi file này tồn tại.

> 🔴 **PHIÊN SINH Ý TƯỞNG (IDEA) VÀ PHIÊN CHỌN KHÔNG ĐỌC FILE NÀY** (`DR-009`) — soạn bởi một phiên đã thấy số đo của Tool D.

---

## 0. Khai thẳng — đây là GHI ĐÈ, quyết SAU khi đã thấy số

Zone Absorption LONG là giả thuyết **đã có kết quả EXPLORE ≈ 0** (`DR-IQ-01` §0: `Z0-T1` mean −0,0015 R, KTC95
[−0,177; +0,175], cần 0,403 để PASS). DR này được quyết sau khi đã thấy con số đó, và sau khi `DR-D4-19` đã mở
lô đo D4. Không có điều kiện nối lại nào của `DR-IQ-01` §1 được **thoả** — chúng được **ghi đè**.

Các DR cũ **giữ nguyên chữ**; DR này chỉ thêm (không sửa file cũ).

## 1. Quyết định — những chữ bị ghi đè

| Chữ cũ | Ghi đè thành |
|---|---|
| `DR-IQ-01` §1: ZA LONG ⏸; nối lại chỉ khi có dữ liệu mới sau `T3` + DR viết trước | Nối lại toàn bộ đường ống D5 → D9 → D9.5 trên dữ liệu lịch sử **ngay** |
| `DR-IQ-01` §1 dòng *"không có cả hai cùng lúc"* | Bỏ. Suất (d) chạy độc lập, không chặn ZA; ZA không chặn suất (d) |
| `DR-HUONG-01` §2: B ❌, C là hướng chính | **B là hướng chính.** C phụ |
| `DR-HUONG-01` §5 (dữ liệu sau `T3` thuộc ai) | Không còn tranh chấp: ZA dùng lockbox `[T2,T3]` (seal 1 cấp lại theo `DR-LOCKBOX-01`); ý tưởng (d) nếu có phải có lockbox sau `T3` |
| `DR-D4-19` §3: INCONCLUSIVE ⇒ ZA về ⏸, D5 không tự mở | INCONCLUSIVE ⇒ **D5 mở** (trả lại `DR-D4-12` §2.3). FAIL ⇒ đường ống **vẫn tiếp tục**, kết cục ghi vào hạn chế của mọi cổng sau và vào cổng D12 |
| `DR-D4-19` §4: ZA về ⏸ sau lô | Bỏ vế *"về ⏸"*. Vế *"lật `D4_DO_TAM_DUNG` về `True`"* **giữ** (E3 không cần chạy lần hai) |
| `spec:2954`: không vào D11 khi D2 chưa verify bằng testnet / lệnh live tối thiểu | **D11 dry-run chạy song song D10.** Dry-run không đặt lệnh thật nên không cần D2 để an toàn; D2/D10 trở thành điều kiện của **D12** |

## 2. Giữ nguyên — không phải chờ đợi, chỉ bảo đảm số là thật

- `N = 114`, rào DSR 3,0777, mọi ngưỡng §10.2 và cổng D9 (`DR-D9-01`/`DR-D9-02`); sổ trial append-only; đặt chỗ trước khi chạy.
- Lockbox chạm **đúng một lần** (D9.5), trên rổ T2 và seal cấp lại (`DR-LOCKBOX-01`); luật lockbox (`TD-0274`) commit trước suất WFO đầu tiên.
- Cấm hyperopt, FreqAI, `*Parameter`; tham số chỉ từ `tool_d_config.yaml`; `enable_short: false`.
- Luật 🟡: không mang mâu thuẫn 🟡 qua go-live (`back-end-note.md:163`).

## 3. Cổng tiền D12 — viết TRƯỚC khi có kết quả D9/D9.5

Vào D12 (tiền thật ngoài ngân sách D10) cần **đủ cả bốn**:
1. Lockbox D9.5 **PASS**, **hoặc** một DR riêng của chủ dự án viết SAU khi nhìn số, khai rõ kết cục lockbox và lý do vẫn đưa tiền.
2. D10 PASS theo ba ngưỡng `DR-D11-01` §5.
3. ≥ 2 tuần dry-run chạy bằng **cấu hình cuối** (niêm phong sau D9), không sự cố vận hành chưa xử.
4. 0 mục `MT` 🟡/🔴 còn mở.

🔴 **KHÔNG phải điều kiện:** *"đường ống đã chạy xong"*; *"dry-run có lãi"* (dry-run ngắn không phải phép đo hiệu năng).

## 4. Dry-run — đọc số cho đúng

- Giai đoạn trước khi D9 chốt chạy bằng tham số hiện hành, **nhãn "dry-run vận hành"** — chỉ dùng kiểm máy, không trích làm hiệu năng.
- Mỗi lần khởi động lại với cấu hình mới ghi research-log; phép đếm 2 tuần của §3.3 bắt đầu từ lần khởi động bằng cấu hình cuối.
- Không thêm file vào `entrypoints/` (L-Z36); service gọi thẳng Freqtrade.

## 5. Điểm yếu

- Kết cục D4/D9/lockbox nhiều khả năng INCONCLUSIVE hoặc FAIL (`DR-IQ-01` §2.1). Đường ống hoàn thiện ≠ có lợi thế.
- Chạm lockbox bằng ZA tiêu lockbox duy nhất hiện có.
- Ngân sách dự kiến: 4 (D4) + ≤ 16 (D5) + ≤ 16 (D9) ≈ 36–40/114.

## 6. Thi hành

`TASKS.md` Khối 31 (`a97cc4c`): TD-0349 (DR này) · TD-0350 (dry-run D11 + heartbeat + watchdog) · TD-0351 (lật ⏸ → 🔓
D5–D9/lockbox) · TD-0352 (D9.5 chạm thật + `d9_5_complete`) · TD-0353 (tách file trạng thái vận hành theo runmode trước
D10). Các cổng `close_d5…d9_gate` dùng lại mã cũ (TD-0257/0267/0273/0279/0287). `DR-D10-02` + bộ chạy D10 chưa đặt chỗ.
`back-end-note.md` mục 7 (MT ghi đè + đóng `OQ-16`) và `CLAUDE.md` trạng thái chờ *"chuẩn hóa và lưu"*.

---

> 🔄 **ĐÍNH CHÍNH 24/09/2026 (`DR-LOCKBOX-04`, chủ dự án chốt, phiên mã `143375ad`) — nối cuối, chữ ở trên giữ nguyên.**
> Dòng §1 *"`DR-HUONG-01` §5 (dữ liệu sau `T3` thuộc ai)"* → *"ZA dùng lockbox `[T2,T3]` … ý tưởng (d) nếu có phải có
> lockbox sau `T3`"* **bị thay**: `DR-ZA-01` (21/09) chốt 0 suất thêm cho ZA LONG nên ZA không tới D9.5; đoạn `[T2,T3]`
> chuyển cho ứng viên (d) **đầu tiên**, dữ liệu sau `T3` thành lớp xác nhận trước khi tăng vốn quá mức D12. Các dòng
> khác của §1 và toàn bộ §2–§6 không đổi. Chi tiết: `DR-LOCKBOX-04`.
