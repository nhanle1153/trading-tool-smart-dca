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
#: 🔄 20/09/2026 (`TD-0362`, chủ dự án chốt): **lật lại `True`** — lô `DR-D4-20` đã chạy xong đúng 4 suất
#: (`D-0019`…`D-0022` CONSUMED, cả bốn INCONCLUSIVE) nên vế *"lật lại"* của `DR-D4-19` §4 tới hạn;
#: `DR-TRIEN-KHAI-01` §1 bỏ vế *"ZA về ⏸"* nhưng **giữ** vế này. Cửa duy nhất tiêu suất `B2` đóng lại:
#: trước đó thứ chặn chỉ là một test chạy SAU, không phải cổng lúc chạy.
D4_DO_TAM_DUNG: bool = True

LY_DO_KHOA = (
    "D4-đo đang TẠM DỪNG — `DR-IQ-01` §1, khoá `D4_DO_TAM_DUNG` (`DR-D4-14` §2.2). "
    "Điều kiện lật khoá: `DR-D4-14` §6. Không đặt chỗ, không chạm dữ liệu, 0 suất."
)


#: TD-0373 (`DR-ZA-01` §2, chủ dự án chốt 21/09/2026) — khoá khâu ĐO của D5: **0 suất `B1`** cho Zone Absorption
#: LONG. Trước khoá này, chốt đó chỉ là chữ: `d4_complete = true` nên `registry.reserve()` nhận một suất `B1` hợp lệ
#: theo `DR-D5-01` ngay khi ai đó chạy E1. Cùng lý do là hằng số chứ không phải cờ/biến môi trường như khoá D4 ở trên.
#:
#: Chặn ở HAI tầng: `TrialLedger._kiem_cua_b1()` (cửa mọi đường ghi sổ đều đi qua) và E1 trước khi đọc dữ liệu.
#: Dòng `B0`/`B2`/`B3`/`CTRL` không đi qua khoá này.
#:
#: Điều kiện lật về `False` — đủ CẢ HAI, viết TRƯỚC: (1) có ứng viên được CHỌN qua Idea Queue (dòng CHỌN trên sổ ý
#: tưởng, `DR-Q4-2026`); (2) một DR mở khoá viết TRƯỚC khi đặt suất đầu tiên, nêu đích danh ứng viên và bảng ứng
#: viên D5 của nó. KHÔNG phải điều kiện: *"cổng D5 đã dựng xong"*; thời gian trôi; ZA LONG muốn thử lại
#: (`retest_forbidden`, `DR-ZA-01`).
D5_DO_TAM_DUNG: bool = True

LY_DO_KHOA_D5 = (
    "D5-đo đang KHOÁ — `DR-ZA-01` §2 (0 suất B1 cho Zone Absorption LONG), khoá `D5_DO_TAM_DUNG` (TD-0373). "
    "Mở khi có ứng viên được CHỌN qua Idea Queue và một DR mở khoá viết trước. Không đặt chỗ, 0 suất."
)
