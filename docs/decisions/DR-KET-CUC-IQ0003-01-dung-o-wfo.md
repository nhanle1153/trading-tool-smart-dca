# DR-KET-CUC-IQ0003-01 — IQ-0003 dừng ở WFO: INCONCLUSIVE vì thiếu độ mạnh thống kê, không chạm lockbox

> **Ngày chốt:** 25/09/2026 · **Người quyết:** chủ dự án (chọn *"Dừng ở WFO, giữ lockbox"*, rồi *"Dừng hết, kể cả D10"* khi
> được báo va chạm với quyết định D10 ở phiên mã `dd89043d`) · phiên mã `12c579bc` soạn.
> **Chi phí:** 0 trial. Mã `DR-KET-CUC-IQ0003-01` + `TD-0414` đặt chỗ bằng commit `82fa025` (N12 mục 7c).

> 🔴 **PHIÊN IDEA/CHỌN KHÔNG ĐỌC FILE NÀY** (`DR-009`): có số đo của Tool D.

---

## 1. Kết cục

**IQ-0003 (rổ funding chéo trung tính, `RoFunding`, slot `A-Q4-2026-01`): `INCONCLUSIVE` vì thiếu độ mạnh thống kê.**

- Đây **không** phải bằng chứng thua. Không gán L3 (`DR-PHAN-QUYET-01`: chỉ phán khi phép đo có khả năng trả FAIL vì lý do
  thật). Không `retest_forbidden`.
- Hai suất đã tiêu (B3, `NEUTRAL`, cùng một biến thể `IQ-0003-v1`): `D-0023` CALIB và `D-0024` WFO. Số nằm ở hai hiện vật đã
  commit, không chép lại ở đây: `docs/du-lieu-do/IQ-0003-D-0023-calib-loi-suat-ngay.json`,
  `docs/du-lieu-do/IQ-0003-D-0024-wfo-loi-suat-ngay.json`. Ở cả hai, `can_duoi = mean − h·std/√n` **âm**: lãi trung bình
  không phân biệt được với 0 ở cỡ mẫu đó.

## 2. Vì sao không chạm lockbox `[T2, T3]`

1. **Điều (2) của `nguong_bac_bo` gần như chắc chắn cho FAIL chỉ vì cỡ mẫu.** σ lớn nhất đã commit (quy tắc `max`,
   `DR-PHAN-QUYET-01` §2.3) = 0,014474 /ngày (D-0024); lockbox ≈ 217 ngày có rổ ⇒ `T = h·σ/√n ≈ 0,00302 /ngày`
   (≈ 0,30%/ngày), gấp khoảng 4 lần mean WFO và 27 lần mean CALIB. FAIL ở lockbox ⇒ `retest_forbidden` + lockbox dùng
   hết: đóng vĩnh viễn một ý tưởng vì phép đo không đủ mạnh, không vì ý tưởng sai.
2. **`DR-LOCKBOX-03` không ánh xạ được sang ứng viên này.** Luật đòi `d9_ket_cuc == PASS`, hoặc INCONCLUSIVE kèm ngưỡng ký
   TRƯỚC khi đọc kết quả D9. IQ-0003 không có D9 (một cấu hình ⇒ PBO `unreadable`, `DR-D9-01` §4.4), và kết quả WFO đã được
   đọc.
3. **Viết ngưỡng mới hay nới điều (2) sau khi đã thấy CALIB + WFO** là chọn thước sau khi nhìn số — đúng thứ spec cấm.

## 3. Hệ quả

- **Lockbox `[T2, T3]` CHƯA CHẠM.** `DR-LOCKBOX-04` §2.5 gắn nó cho ứng viên suất (d) đầu tiên; dùng cho ứng viên khác cần DR
  mới. Seal 1 giữ nguyên; không tải dữ liệu, không cấp lại seal.
- **Suất (d) coi như đã dùng:** hạn ngạch quý 4/2026 = 1 đã tiêu cho IQ-0003 (`DR-IQ-03` §3.1); không chọn bù.
- **Sổ ý tưởng:** IQ-0003 giữ trạng thái SELECTED. Chưa có công cụ `ARCHIVED` (`DR-IQ-02` §6) và không ghi tay.
- **D10 cho IQ-0003 KHÔNG chạy** (chủ dự án chốt *"Dừng hết, kể cả D10"*). Việc `TD-0412` / `TD-0413` của phiên mã
  `dd89043d` do phiên đó tự căn trạng thái; hạ tầng đã commit giữ nguyên để dùng lại.
- **Hạ tầng dựng cho IQ-0003 giữ nguyên, dùng lại được:** `RoFunding`, `tool_d.ro_funding(_do)`, file phủ theo chiến lược,
  hướng `NEUTRAL`, đếm biến thể theo cấu hình, cổng `CAN_RO_THEO_LICH`.

## 4. Điều kiện mở lại — viết TRƯỚC

Tiếp tục IQ-0003 chỉ khi một phép đo MỚI (dữ liệu chưa ai nhìn, ví dụ sau `T3`) có `T` nhỏ hơn mức mean hợp lý. Tính sẵn:
`n cần ≈ (h·σ/mean)²`. Với σ = 0,014474 và mean = mean WFO (≈ 0,00081 /ngày) ⇒ **n ≈ 3.000 ngày có rổ (~8 năm)**; với mean
CALIB ⇒ hơn 150.000 ngày. **Trên thực tế không mở lại bằng đường này.** Mở lại bằng cách khác (rào thống kê khác, gộp nhiều
nguồn dữ liệu) là quyết định của vòng thiết kế lại (`DR-TAI-THIET-KE-01`), phải viết TRƯỚC khi thấy dữ liệu mới.

❌ Không phải điều kiện mở lại: *"WFO có lãi"*, *"funding đúng chiều"*, *"tiếc công dựng"*.
