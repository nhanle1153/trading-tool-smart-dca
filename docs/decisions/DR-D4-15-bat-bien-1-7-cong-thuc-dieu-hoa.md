# DR-D4-15 — Sửa bất biến `DR-D4-12` §1.7: so fill với công thức ĐÚNG, mốc 5%

> **Ngày chốt:** 19/09/2026 · **Người quyết:** chủ dự án (chọn phương án A trong ba, phiên mã `69768527`)
> **Chi phí:** **0 trial** · quyết TRƯỚC khi có bất kỳ lệnh D4 thật nào (khoá `D4_DO_TAM_DUNG` vẫn bật).
> Mã `DR-D4-15` + `TD-0340` đặt chỗ bằng commit `d69c3b9` (N12 mục 7c).

> 🔴 **PHIÊN SINH Ý TƯỞNG (IDEA) VÀ PHIÊN CHỌN KHÔNG ĐỌC FILE NÀY** (`DR-009`).

---

## 1. Chữ cũ sai ở tầng CÔNG THỨC, không cần tới fill

`DR-D4-12` §1.7: *"Ở lệnh khớp đủ ba tranche: `Σ rui_ro_da_trien_khai` có bằng `planned_risk_usdt` không? Công thức nói
**có** (đó là ý nghĩa của `p_avg`)… Lệch ⇒ DỪNG, báo."*

Tranche có notional bằng nhau (`sizing.py:242`, `w_tranche` ≈ ⅓ mỗi phần, `tool_d_config.yaml:82`), còn `p_avg` là trung
bình CỘNG (`trade_plan.py:156`). Với các tranche khớp đúng giá kế hoạch:

    Σ rui_ro   = N_full · Σ w_j · (p_j − sl) / p_j   = N_full · (1 − sl · Σ w_j / p_j)
    planned    = N_full · (p_avg − sl) / p_avg        = N_full · (1 − sl / p_avg)

`Σ w_j/p_j ≥ 1/p_avg` (trung bình điều hoà ≤ trung bình cộng) ⇒ **Σ rui_ro ≤ planned**, bằng nhau chỉ khi `p1 = p2 = p3`.
Ví dụ `p = (100, 98, 96)`, `sl = 94`: tỉ số **0,99342**; zone hẹp `(100; 99,5; 99)`, `sl = 97`: **0,99933**
(`docs/research-log.md`, 19/09/2026). Giữ chữ cũ ⇒ D4 DỪNG vì một hệ quả số học, không vì fill.

## 2. Quyết định — phương án (A)

Chủ dự án chọn giữa ba đường:

| Đường | Hậu quả | Chốt |
|---|---|---|
| **(A)** So fill với công thức ĐÚNG + mốc 5% | Khử hẳn phần đại số; phần lệch còn lại chỉ do fill ⇒ lớp canh giữ đúng mục đích §1.7 | ✅ |
| (B) Chỉ đo và báo, bỏ điều kiện dừng | Mất lớp canh: fill backtest lệch nặng vẫn không chặn phán quyết trên một đơn vị `R` sai | ❌ |
| (C) Dung sai cố định 1% quanh `planned_risk_usdt` | Trộn đại số với fill; backtest khớp tranche 2/3 ở giá mở nến (DR-015) ⇒ nhiều khả năng dừng giả | ❌ |

### 2.1 Định nghĩa thi hành

Với mỗi lệnh `i` khớp **đủ ba** tranche, đọc trên export thật:

    D_fill(i) = Σ_j  amount_j · (fill_j − sl)                        (= rui_ro_da_trien_khai, DR-D4-12 §1.4)
    D_ke(i)   = N_full(i) · Σ_j  w_j · (p_j − sl) / p_j              (giá KẾ HOẠCH p_j, sl từ enter_tag)
    r(i)      = D_fill(i) / D_ke(i)

`N_full(i)` là giá trị đã dùng để định cỡ — suy ngược từ ký quỹ tranche 1 đã khớp (`DR-D4-14` §10); `w` đọc từ cấu
hình phủ của lượt chạy.

**DỪNG** ⇔ `|trung_vi(r) − 1| > 0,05` trên các lệnh đủ ba tranche của lượt chạy.

### 2.2 Căn cứ của từng lựa chọn — DIỄN GIẢI, cãi lại được

- **Mốc 5%**: lấy từ ngưỡng `0,95` đã có ở `DR-D4-12` §9.1 (*"hai vế đơn vị trùng nhau"*), đối xứng hai phía.
  **Không thêm con số nào** vào kiểm kê DOF; không tham số nào trong `tool_d_config.yaml`.
- **Trung vị, không từng lệnh**: backtest khớp tranche 2/3 ở giá mở nến (`DR-015`, §9b D6), nên MỘT lệnh lẻ có thể lệch
  xa mà không nói gì về hệ thống. Câu §1.7 hỏi về đơn vị `R` của cả lượt chạy, nên đọc trên trung vị.
- **Chỉ lệnh đủ ba tranche**, đúng chữ §1.7. Lệnh một tranche (`Z0-T1`, `Z0`, `Z0-T0` — arm một tranche) không có phần
  đại số nào để khử, nên không vào phép so. Trong lô D4 chỉ `Z3` có lệnh đủ ba tranche.
- **0 lệnh đủ ba tranche** ⇒ tỉ số `unreadable` kèm lý do; **không** dừng (không có gì để kết luận), và **không** điền
  `1.0`. Ghi vào `d4_han_che`.

## 3. Thứ DR này KHÔNG đổi

- Mẫu số phán quyết Nhánh 1 vẫn là `rui_ro_da_trien_khai` (`DR-D4-12` §1).
- `ty_le_rui_ro_da_trien_khai` vẫn báo như cũ; `DR-D4-12` §9.1 giữ nguyên.
- `sizing.py` không đổi một dòng — đây là đại lượng ĐỌC ở tầng đo.

## 4. Thi hành

- Commit DR này **RIÊNG và TRƯỚC** mọi dòng mã.
- Đính chính tại chỗ `DR-D4-12` §1.7 — nối vào CUỐI dòng có sẵn, giữ nguyên chữ cũ.
- Tính `r(i)` và trung vị ở tầng thuần (`src/tool_d/ablation/chi_so_export.py`), ghi vào `chi_so` của bản ghi arm
  (schema đã cho khoá thêm dạng `measured`). Cổng D4 (`close_d4_gate()`) TỪ CHỐI khi điều kiện DỪNG thoả.
- Kiểm-có-răng bắt buộc: thay `D_ke` bằng `planned_risk_usdt` (chữ cũ) ⇒ ca lệnh-đủ-ba-tranche khớp-đúng-giá phải ĐỎ.

## 5. Điều kiện mở lại — viết TRƯỚC

- `w_tranche` đổi khỏi notional bằng nhau, hoặc `p_avg` đổi định nghĩa ⇒ `D_ke` phải viết lại cho khớp.
- ❌ **KHÔNG** phải điều kiện mở lại: lượt đo thật cho tỉ số gần mốc; hoặc kết quả `Z0-T1` không như mong đợi.
