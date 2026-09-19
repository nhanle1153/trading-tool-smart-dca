"""`DR-D4-14` §2.2 — khoá khâu ĐO của D4. Đây là chỗ DUY NHẤT của quyết định.

`True` ⇒ E3 (`entrypoints/run_ablation.py`) từ chối `--chay` TRƯỚC `reserve()`, trước
cả khi băm hay mở một file dữ liệu: 0 suất `B2` nào được tiêu.

🔴 Vì sao là một hằng số trong code chứ không phải cờ dòng lệnh hay biến môi trường
(chủ dự án chốt 19/09/2026, khuôn TD-0171): một cờ gõ được thì một lệnh gõ đủ cờ là
tiêu suất dù quyết định tạm dừng vẫn còn. Ở đây muốn mở phải SỬA MỘT DÒNG CÓ NHẮC TỚI
QUYẾT ĐỊNH, trong một commit ai cũng thấy — và test khoá
`tests/lock/test_td0335_e3_bo_chay_ablation.py` ghim giá trị này kèm `assert` nêu đích
danh `DR-IQ-01` và `DR-D4-14`.

Điều kiện lật về `False` (`DR-D4-14` §6, viết TRƯỚC) — đủ CẢ BA:
  1. `DR-IQ-01` §1 thoả nguyên chữ (dữ liệu MỚI sau `T3 = 2026-09-06` + DR nối lại viết
     TRƯỚC khi đo; không ý tưởng suất (d) nào đang trong chu trình);
  2. `TD-0261` ✅ (N theo H14/DR-007);
  3. đã đo lại `n` của 4 arm trên rổ T1 (0 trial, chỉ đếm).
KHÔNG phải điều kiện: *"code đã dựng xong"*; ý tưởng (d) ra FAIL/INCONCLUSIVE; thời gian trôi.
"""

from __future__ import annotations

#: `DR-IQ-01` §1 + `DR-D4-14` §2.2. Lật giá trị này = nối lại D4-đo — cần DR nối lại.
#: 19/09/2026: `False` theo `DR-D4-19` (chủ dự án GHI ĐÈ điều kiện 1 của `DR-D4-14` §6, không thoả nó) —
#: đúng MỘT lô 4 arm, xong thì lật lại `True` (`DR-D4-19` §4).
D4_DO_TAM_DUNG: bool = False

LY_DO_KHOA = (
    "D4-đo đang TẠM DỪNG — `DR-IQ-01` §1, khoá `D4_DO_TAM_DUNG` (`DR-D4-14` §2.2). "
    "Điều kiện lật khoá: `DR-D4-14` §6. Không đặt chỗ, không chạm dữ liệu, 0 suất."
)
