# DR-D4-14 — Dựng bộ chạy D4, KHOÁ khâu đo

> **Ngày chốt:** 19/09/2026 · **Người quyết:** chủ dự án (lệnh *"bắt đầu code triển khai tiếp tục D4"* + trả lời
> ba câu hỏi phạm vi/khoá/sổ việc, duyệt kế hoạch — phiên mã `69768527`)
> **Chi phí:** **0 trial** · Không đo trên CALIB/WFO/LOCKBOX/EXPLORE · Không chạm lockbox · Không gỡ ⏸ nào.
> Mã `DR-D4-14` + `TD-0332`…`TD-0337` đặt chỗ bằng commit `eb1a9aa` (N12 mục 7c) trước khi file này tồn tại.

> 🔴 **PHIÊN SINH Ý TƯỞNG (IDEA) VÀ PHIÊN CHỌN KHÔNG ĐỌC FILE NÀY** (`DR-009`) — soạn bởi một phiên đã thấy
> số đo của Tool D.

---

## 1. Yêu cầu và chỗ nó va

Chủ dự án yêu cầu *"tiếp tục D4"*. Hiện trạng trên đĩa 19/09/2026: `entrypoints/run_ablation.py:78` vẫn
`NotImplementedError`; chưa có `close_d4_gate()`; `runtime_state.json` chưa có `d4_complete`; sổ trial 13 dòng,
4/114 suất.

Yêu cầu va với hai quyết định đã chốt (quy tắc 11 — ghi, không tự chọn bên):

| Quyết định | Chữ đang có |
|---|---|
| `DR-IQ-01` §1 (17/09) | TD-0184 bộ chạy ablation · cổng D4 (TD-0185/0186) ⏸. Nối lại **chỉ** khi có dữ liệu MỚI sau `T3 = 2026-09-06` đủ đổi kết luận, kèm DR viết TRƯỚC khi đo. Cấm song song với một ý tưởng suất (d) đang chạy |
| `DR-HUONG-01` §2 (18/09) | Phương án B *"gỡ ⏸, chạy D4 → D9 cho ZA LONG"* = ❌ không làm |

## 2. Quyết định

Chủ dự án chọn giữa ba mức (*chỉ dựng* · *dựng + đo ngay* · *chỉ việc 0-trial trong D4*):

1. ✅ **Chỉ DỰNG, khâu ĐO khoá.** D4 tách làm hai, cùng khuôn `DR-SHORT-01` §2:
   - **D4-dựng** — ✅ được làm: bộ chạy E3, tầng thuần lệnh → bản ghi arm, gate §10.2 + `L-Z57`, hàm đóng cổng
     D4. Kiểm bằng **dữ liệu tổng hợp** trong `tmp_path` và **sổ trial tạm** — không phải dữ liệu thị trường,
     nên không phải "chạm" (`DR-014` §2, N2).
   - **D4-đo** — ⏸ **giữ nguyên**: `DR-IQ-01` §1 và `DR-HUONG-01` §2 đứng nguyên **từng chữ**. DR này không
     thay, không nới, không diễn giải lại chúng. `TD-0184`/`TD-0185`/`TD-0186` giữ ⏸ và từ nay mang nghĩa phần đo.
2. ✅ **Khoá đo là một hằng số ghim trong code**, không phải cờ dòng lệnh hay biến môi trường:
   `src/tool_d/ablation/khoa_do.py` → `D4_DO_TAM_DUNG = True`. E3 đọc nó và **từ chối `--chay` TRƯỚC `reserve()`**,
   trước cả khi băm hay mở một file dữ liệu. Một test khoá ghim `True` với dòng `assert` nêu đích danh
   `DR-IQ-01` + DR này (khuôn TD-0171: ghim QUYẾT ĐỊNH ở đúng một chỗ). Lật khoá ⇒ phải sửa một dòng có nhắc
   tới quyết định, trong một commit ai cũng thấy.
3. ✅ **Sổ việc: Khối 30 mới, mã mới** — không dùng lại TD-0184/0185/0186, để một mã không mang hai nghĩa
   (*"dựng ✅ mà đo vẫn ⏸"* rất dễ bị đọc thành *"D4 xong"*).

## 3. Vì sao D4-dựng không phá kỷ luật thống kê — và khai thẳng điểm yếu

**Khai thẳng:** DR này được quyết **SAU** khi đã thấy kết quả EXPLORE của ZA LONG (`DR-IQ-01` §0: `Z0-T1`
mean −0,0015 R, KTC95 [−0,177; +0,175]).

**Vì sao vẫn an toàn:** thứ bị chặn là *chọn phép đo sau khi thấy kết quả*. Viết code **không phải phép đo**:
không sinh con số hiệu năng nào trên dữ liệu thật, không tiêu suất nào. Mọi thứ có thể bị kết quả EXPLORE dẫn
dắt nằm ở D4-đo, và D4-đo khoá bằng máy.

**Rủi ro còn lại, không giả vờ là không có:** bộ chạy có sẵn làm việc *"chạy thử D4"* rẻ đi — chỉ còn một dòng
để lật. Đối trọng là máy: khoá nằm trong code có test ghim, `--chay` từ chối trước `reserve()`, và sổ trial
append-only ghi lại mọi suất đã tiêu.

**Được gì:** khi điều kiện `DR-IQ-01` §1 thoả, D4 chạy được ngay — không mất 3–5 phiên viết code vào đúng lúc
dễ bị kết quả dẫn dắt nhất.

## 4. Phạm vi (Khối 30 của `TASKS.md`)

| Việc | Nội dung |
|---|---|
| `TD-0332` | DR này |
| `TD-0333` | Trích lệnh Freqtrade → `LenhWFO` (`wfo/lenh.py`), chuyển logic `_r_trien_khai` của `do_td0291_song_con_explore.py:109` vào `src/` — docstring `lenh.py:9-14` đã gọi đích danh việc này là của bộ chạy D4 |
| `TD-0334` | `src/tool_d/ablation/`: `khoa_do.py` (khoá) + `ban_ghi.py` — lô 4 arm `DR-D4-12` §4 (`Z0-T1`, `Z0`, `Z0-T0`, `Z3`), lệnh → chỉ số → `build_arm_record()` |
| `TD-0335` | Bộ chạy E3 theo khuôn E1 (`run_backtest.py`, TD-0313): kế hoạch → `--chay` → khoá → mỗi arm `reserve(B2, WFO)` → `chay_mot_luot()` → `refund` theo máy / `seal` → bản ghi → `consume` |
| `TD-0336` | Gate D0.9 §10.2 + `L-Z57` (tầng thuần `gates/d0_9.py`), gọi `phan_loai_ket_cuc`/`so_paired`/`hieu_chinh_hai_chieu` sẵn có |
| `TD-0337` | `close_d4_gate()` (`--close-d4-gate` trên E6), khuôn `close_d3_5_gate`, gọi `kiem_tieu_chi_dong_d4()` (`DR-D4-11` §3) |

Năm cổng đứng trước chỗ `NotImplementedError` của E3 (guard dòng đầu — N5/`L-Z36`, D0-PRE, audit, `L-Z56`,
H17) **giữ nguyên thứ tự và nội dung**.

`hypothesis_slot` của suất D4: **không DR nào của D4 chốt**. E3 vì thế đòi cờ `--hypothesis-slot` **không có mặc
định** (cùng lý do `DR-BC-01` §4 với `budget_line`); giá trị do DR nối lại chốt.

## 5. KHÔNG làm (thuộc D4-đo, ⏸)

- Đặt chỗ bất kỳ suất `B2` nào trên sổ thật · chạy E3 trên rổ/dữ liệu thật · đo lại `n` 4 arm trên rổ T1
  (phần đếm của TD-0184) · TD-0261 · đổi `D4_DO_TAM_DUNG` thành `False`.
- Đổi arm sản xuất (`TD-0227`) — chờ cổng D4 và `MT-35`.
- Lật 11 dòng căn ⏸ ở `13cd37e` · sửa `DR-IQ-01`, `DR-HUONG-01`, `DR-D4-11`, `DR-D4-12`.
- Đổi `ARM_B2_COUNT`, `N = 114`, rào DSR.
- **Không** đổi thứ tự ưu tiên của `DR-HUONG-01`: suất (d) vẫn là hướng chính.

## 6. Điều kiện lật khoá (viết TRƯỚC)

Lật `D4_DO_TAM_DUNG` về `False` chỉ khi **đủ cả ba**:
1. Điều kiện `DR-IQ-01` §1 thoả **nguyên chữ** (dữ liệu mới sau `T3` + DR nối lại viết TRƯỚC khi đo, khai ZA
   LONG đã có EXPLORE ≈ 0; không có ý tưởng suất (d) nào đang trong chu trình).
2. `TD-0261` ✅ (N theo H14/DR-007, đo trước suất B2 đầu tiên — spec `:4267-4268`).
3. Đã đo lại `n` của 4 arm trên rổ T1 (0 trial, chỉ đếm) — spec `:4338` làm số cũ `325,6` · `n = 206` · `44,8`
   mất hiệu lực.

Commit lật khoá phải trỏ về DR nối lại. ❌ **KHÔNG** phải điều kiện: *"code đã dựng xong"*; ý tưởng (d) ra
FAIL/INCONCLUSIVE; thời gian trôi qua.

## 7. Điều kiện dừng / đảo ngược

- Một phép kiểm cũ phải sửa khẳng định mới xanh ⇒ dừng, báo chủ dự án.
- Cần sửa `L-Z56`, `L-Z36`, artifact niêm phong D3.5, hay `validate_arm_record()` để đi tiếp ⇒ dừng.
- Sổ trial thật đổi dù một dòng, hoặc `runtime_state.json` đổi ⇒ dừng, đó là D4-đo lọt vào D4-dựng.
- Export Freqtrade không mang được `planned_risk_usdt` của từng lệnh ⇒ dừng, báo — không bịa (N6).
- Code mới cần đọc một cột DB Freqtrade chưa có nghĩa duyệt trong `y_nghia_cot.py` ⇒ dừng (N13 mục 3).

## 8. Hành vi mong đợi sau khi dựng xong — ghi trước để không đọc nhầm là lỗi

- `run_ablation.py --chay` trên máy thật ⇒ thoát bằng mã khoá, sổ trial không đổi.
- `trial_ledger_audit.py --close-d4-gate` trên trạng thái thật ⇒ **từ chối** (0 bản ghi arm, 0 suất B2). Đó là
  cổng làm đúng việc, không phải cổng hỏng.

## 9. Việc giấy tờ còn treo

`ARCHITECTURE.md` (cây thêm `src/tool_d/ablation/`) và một mục `MT` ở `back-end-note.md` §7 trỏ về DR này (va
chạm với `DR-IQ-01` §1 / `DR-HUONG-01` §2, giải bằng tách dựng/đo) — chờ lệnh *"chuẩn hóa và lưu"* theo N9.
