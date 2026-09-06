# DR-D0PRE-04 — Chốt thang phản ứng drawdown 5% / 8% / 20% (§12c.5, TD-0042)

> OQ-03. 🔒 **Cấp C** (§12c.3): sau commit này là **DR-012 Hạng 0 — không có quy trình sửa, không có ô
> nhập**. Chủ dự án xác nhận ngày 06/09/2026, TRƯỚC khi có bất kỳ backtest nào (spec dòng 4428).

## 1. Giá trị chốt

```
dd_tool_d  ≤ 5%   →  mult_dd = 1.0    bình thường
5% < dd    ≤ 8%   →  mult_dd = 0.5    GIẢM TỐC, vẫn giao dịch
dd         > 8%   →  HALT             ngừng MỞ lệnh mới (mở lại theo lịch, §12c.5 BƯỚC 1-4)
dd         > 20%  →  ABORT            bác bỏ giả thuyết (L3, §11b.1)
```

`dd_tool_d` đo từ **đỉnh equity của sub-account Tool D**, tính trên equity đã gồm PnL chưa thực hiện.
Trần **3 lần HALT / 100 lệnh đóng** → lần thứ 4 ABORT bất kể dd (câu hỏi mở #23 của spec vẫn mở —
con số này giữ nguyên, không phải đối tượng của DR này).

## 2. Vì sao giữ đúng thang spec, không siết, không nới

Spec §12c.5 đã **tự suy** thang này từ hai lỗi của v5 (8% vừa là lỗ/ngày vừa là tắt vĩnh viễn; mọi
"HALT tạm" ngây thơ đều deadlock). Điều còn lại cho chủ dự án là **xác nhận khẩu vị**. Ba phương án
đã trình, quy ra tiền với `E_D` = 500 (DR-D0PRE-06) và rủi ro/lệnh 1,875 USDT:

| Phương án | Giảm tốc | HALT | ABORT | Hệ quả kinh doanh |
|---|---|---|---|---|
| **5 / 8 / 20 (chốt)** | −25 USDT (~13 lệnh thua) | −40 USDT (~21 lệnh) | −100 USDT (~53 lệnh) | HALT = đúng một ngày xấu tối đa (`daily_loss_budget` 8%): cú sập tương quan kích **tạm dừng**, không kích **bác bỏ** — đúng loại phản ứng cho đúng loại thông tin |
| Siết 4 / 6 / 15 | −20 | −30 | −75 | Dừng sớm hơn, nhưng HALT giả nhiều hơn với edge thật-mà-mỏng; 3 HALT/100 lệnh = ABORT → dễ giết nhầm giả thuyết còn sống |
| Nới 6 / 10 / 25 | −30 | −50 | −125 | HALT 10% > lỗ/ngày 8%: một cú sập tương quan trọn vẹn **không còn kích HALT** — mất đúng cơ chế §12c.5 được tạo ra để có |

Chủ dự án chọn **giữ 5 / 8 / 20**.

## 3. Ràng buộc ghép cặp phải giữ mãi

`dd_ladder_pct.halt` (8) **== `daily_loss_budget_pct`** (8, DR-D0PRE-06). Đây không phải trùng hợp:
§12c.5 lập luận "một ngày xấu tối đa → HALT tạm" chỉ đúng khi hai số bằng nhau. Nếu chủ dự án đổi
`daily_loss_budget_pct` (Tầng A, được phép), thang này **không** đổi theo (Cấp C) — lập luận ghép cặp
mất hiệu lực và phải ghi nhận lại. Test `tests/unit/test_dd_ladder_locked.py` canh cả hai điều.

## 4. Điều thang này KHÔNG làm (spec dòng 4761, nhắc lại để không kỳ vọng sai)

Không làm hệ thống lãi hơn, không làm giả thuyết đúng hơn. Chỉ đảm bảo một cú sập tương quan không bị
đọc nhầm thành "Zone Absorption đã chết". Nếu edge không tồn tại, thang chỉ kéo dài thời gian tới ABORT.
