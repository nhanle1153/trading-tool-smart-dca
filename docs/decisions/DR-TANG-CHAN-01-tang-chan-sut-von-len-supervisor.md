# DR-TANG-CHAN-01 — Tầng chặn sụt vốn (HALT 8% / ABORT 20%) lên Risk Supervisor cho MỌI chiến lược

> **Ngày chốt:** 26/09/2026 · **Người quyết:** chủ dự án (duyệt kế hoạch phân tích, chọn phương án C; lệnh "chuẩn hóa và lưu")
> · phiên mã `809d6cd8` soạn. **Mã việc:** `TD-0432` (DR này) · thi hành `TD-0433`…`TD-0439` (Khối 44 `TASKS.md`).
> **Chi phí:** 0 trial, không chạm dữ liệu thị trường.
> Commit RIÊNG và TRƯỚC mọi dòng mã (khuôn `DR-D11-03`).

## 1. Câu hỏi

`MT-40` phần còn lại: thang sụt vốn 5/8/20 (`DR-D0PRE-04`, Cấp C) — một trong BA tầng chặn vòng lặp thua lỗ (§12b.2) —
đặt ở **từng chiến lược** hay ở **Risk Supervisor** để áp cho mọi chiến lược? `TD-0426` (`23f6d3b`) đã xong phần sổ hai
sự kiện đặt lại đỉnh; DR này chỉ chốt NƠI thi hành.

## 2. Hiện trạng đo trên đĩa 26/09/2026

1. Thang chỉ sống trong `ZoneAbsorption` (`_dd_pct()` → `sizing.mult_dd()`). `RoFunding`/`RoFundingD10` — ứng viên từng
   sắp lên tiền — **không có tầng nào** (`git grep equity_peak|_dd_pct|mult_dd`).
2. Chiến lược đo trên `wallets.get_total()` = chỉ lãi/lỗ ĐÃ chốt. §12c.5 (`spec:4713-4714`) đòi *"equity đã bao gồm PnL
   chưa thực hiện"* — khoảng hở đã hoãn có chủ đích tới D11 (`equity_peak.py` docstring).
3. §6.6 (`spec:1949-1950`) đã giao việc cho Supervisor: *"Tool D có Risk Supervisor RIÊNG… tính mult_dd, mult_deploy,
   margin_ratio, kill-switch"*; ràng buộc (2) (`spec:1959-1966`) cho phép khai lại thang dd trong Supervisor, có `L-Z44`
   đối chiếu.
4. `risk_supervisor.HANG_SO_KHAI_LAI` **đã khai** `dd_soft/halt/abort_pct` và `L-Z44` kiểm khớp `tool_d_config.yaml` —
   nhưng **không dòng mã nào dùng chúng để chặn**. Cùng họ "lời khai có, thi hành không" (`MT-46`, `MT-06`).
5. Supervisor đã đọc `totalMarginBalance` từ sàn (`get_account_info`, gồm lãi/lỗ chưa chốt) và dừng được bot qua API
   (`freqtrade_control.dung_bot`, `/api/v1/stop`). Freqtrade có `/stopentry`: chặn mở lệnh mới, giữ vị thế đang mở
   (`freqtrade_control.py:14-17`) — đúng BƯỚC 1 của HALT §12c.5 (`spec:4737`, *"vị thế đang mở CHẠY BÌNH THƯỜNG… không đóng ép"*).
6. Dry-run D11 **không có Supervisor**, không bật API điều khiển; chỉ profile `d10` có `risk-supervisor-d10`.

## 3. Ba phương án

| | A. Giữ trong từng chiến lược | B. Chuyển hết lên Supervisor | C. Supervisor làm chủ, chiến lược làm theo |
|---|---|---|---|
| Chiến lược mới quên tầng chặn | có thể — đã xảy ra (`RoFunding`) | không thể | không thể + máy kiểm lớp mềm |
| Đo đúng §12c.5 | không | có | có |
| Lỗi callback bị Freqtrade nuốt (MT-16 vii) / bot treo | tầng chặn tắt theo | vẫn chặn | vẫn chặn |
| Bậc 5% nửa cỡ lệnh | có | **mất** — API không đổi được cỡ lệnh | có |
| Hai con số sụt vốn lệch nhau | — | — | không: một chủ đỉnh |

## 4. Quyết định — phương án C

1. **Supervisor là chủ DUY NHẤT của đỉnh + mức sụt** khi chạy dài (dry-run D11, D10, D12). Dùng lại nguyên
   `equity_peak.py` + sổ sự kiện `TD-0426`, file riêng dưới `runs/risk_supervisor/<runmode>/`. Chiến lược KHÔNG giữ đỉnh
   riêng ở các runmode này.
2. **Supervisor thi hành phần CỨNG**, dùng `HANG_SO_KHAI_LAI`: > 8% ⇒ `/stopentry` (HALT); > 20%, hoặc HALT lần thứ 4
   trong một chu kỳ 100 lệnh đóng (§12c.5, `spec:4756`) ⇒ `/stop` + cờ đỏ + ghi sự kiện `ABORT` vào sổ, **không tự gỡ** (cùng khuôn
   cờ đỏ thanh lý §6.6(2)).
3. **Chiến lược giữ phần MỀM** — bậc 5% nửa cỡ lệnh, việc Supervisor không làm được qua API — bằng cách đọc
   `dd_state.json` Supervisor công bố (ghi nguyên tử, có mốc giờ) qua **một hàm dùng chung**. Thiếu/cũ quá hạn ⇒ không mở
   lệnh mới (fail-closed, N6). **Backtest** không có Supervisor ⇒ giữ công thức hiện tại trong chiến lược — không đổi một
   con số nào đã đo.
4. **Máy kiểm:** test khoá AST — mọi chiến lược chạy được live/dry-run phải gọi hàm đọc dùng chung trong đường định cỡ.
5. **Mở lại sau HALT** theo đúng §12c.5 bước 2 (hết vị thế · 2 × `max_hold_bars` · dòng research-log), Supervisor kiểm cả
   ba mới cho `/start`, mở lại ở nửa cỡ. 0 hằng số mới.
6. **Parity (quy tắc 9, N11):** Supervisor chạy cả cho dry-run, bật API điều khiển bằng file cấu hình PHỦ chỉ nghe
   localhost (khuôn `DR-D11-03` §2.3 — không sửa `config/freqtrade/config.json` dùng chung). Không làm ⇒ lần đầu HALT thật
   được thi hành rơi vào lúc có tiền (D12).

## 5. Câu phải ĐO trước khi code (`TD-0433`) — không đoán

- (a) Freqtrade dry-run `/api/v1/balance`: tổng có gồm lãi/lỗ chưa chốt không ⇒ quyết nguồn equity của Supervisor ở dry-run.
- (b) Hạn *"`dd_state.json` quá cũ"*: dùng lại nhịp heartbeat watchdog (`TD-0209`) nếu hợp; cần con số mới ⇒ TRÌNH chủ dự
  án, không tự đặt.

## 6. Ngoài phạm vi

- Không đổi thang 5/8/20 (Hạng 0, `DR-D0PRE-04`), không đổi hai sự kiện đặt lại đỉnh (`DR-D6D8-01` §4.2, `TD-0426`).
- Không đổi hành vi backtest, không đo lại gì.
- `mult_deploy`, `margin_ratio` mà §6.6 cũng giao cho Supervisor: không thuộc DR này.

## 7. Quan hệ với việc khác

- `TD-0270` (⏸, cờ 🚩 *"xem lại trước D10 của ứng viên kế tiếp"*): phần Supervisor của nó chuyển sang Khối 44.
- `MT-40`: đóng khi `TD-0434`…`TD-0438` ✅.

## 8. Bổ sung 27/09/2026 — trần "3 HALT / chu kỳ 100 lệnh đóng" (chủ dự án chốt phương án (a))

**Câu hỏi:** §12c.5 (`spec:4756-4758`): *"TRẦN SỐ LẦN HALT: 3 lần trong một chu kỳ 100 lệnh đóng. Lần thứ 4 → ABORT bất
kể dd bao nhiêu."* Hai con số 3 và 100 chỉ có trong chữ spec, KHÔNG có trong `tool_d_config.yaml` ⇒ N4 cấm viết cứng.

**Chốt (a)** (chủ dự án, 27/09/2026, phiên mã `809d6cd8` đề xuất): thêm khoá Tầng C
`tier_c.tran_halt: { so_lan: 3, chu_ky_lenh_dong: 100 }` vào `tool_d_config.yaml` — giá trị CHÉP từ spec, không phải
số mới; Supervisor khai lại trong `HANG_SO_KHAI_LAI` (§6.6(2)) và `L-Z44` đối chiếu hai bản khai, đúng đường thang
5/8/20 đang đi. ❌ Loại (b) viết thẳng vào mã kèm trích dẫn: hai bản khai của cùng một con số mà không máy nào đối chiếu.

**Nghĩa đã chốt khi thi hành (`TD-0434`):**
- Chu kỳ = khối cố định theo §12c.1: lệnh đóng thứ `k` thuộc chu kỳ `k // chu_ky_lenh_dong`.
- Một lần HALT = một lần CHUYỂN sang HALT (gọi lại `/stopentry` mỗi vòng không phải lần HALT mới).
- Lần HALT thứ `so_lan + 1` trong cùng chu kỳ ⇒ ABORT (cùng đường ABORT §4 điều 2: lưu cờ đỏ → `/stop` → sự kiện `ABORT`).
- Nguồn đếm: `GET /api/v1/profit` → `closed_trade_count` (mọi lệnh đã đóng trong DB của bot, `rpc.py:594-623`,
  Freqtrade 2026.8; khai ở `api-integration-rules.md` 4.2 v1.7).
- Không đọc được số lệnh lúc chuyển sang HALT ⇒ lần HALT đó được tính vào MỌI chu kỳ (chỉ có thể làm ABORT tới SỚM
  hơn, không bao giờ muộn hơn — lệch về phía an toàn; N6: không bịa một con số lệnh).

**Hệ quả biết trước:** đổi `tool_d_config.yaml` đổi `config_hash` của các lần chạy SAU (không lần nào đã ghi sổ); không
thêm bậc tự do (Tầng C, không vào kiểm kê DOF — `dof.py` chỉ đọc `tier_b`).
