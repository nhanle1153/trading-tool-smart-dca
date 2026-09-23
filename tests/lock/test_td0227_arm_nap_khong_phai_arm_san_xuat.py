"""🔒 TD-0227 — `tier_c.arm_ablation.arm` là arm NẠP, không phải arm sản xuất.

Chữ gốc của TD-0227 là đổi khoá này từ `"Z3"` sang `"Z0"` (`DR-D4-10` §2.4). `MT-35` (13/09/2026) chốt
LUẬT thay vì chốt arm: *arm sản xuất = arm PASS Nhánh 1; `Z0-T1` INCONCLUSIVE/FAIL ⇒ KHÔNG có arm sản xuất,
`Z0` không phải phương án dự phòng*. Cổng D4 đóng 21/09/2026 với `Z0-T1` FAIL (`DR-ZA-01`) ⇒ điều kiện đổi
không bao giờ xảy ra. Chủ dự án chốt 24/09/2026: đóng TD-0227, KHÔNG đổi arm.

Giá trị `"Z3"` còn lại chỉ để chiến lược nạp được và dry-run vận hành chạy (`DR-ZA-01` §5,
`DR-TRIEN-KHAI-01` §4). Ghim QUYẾT ĐỊNH ở đúng một chỗ, và chỗ đó nêu đích danh `MT-35` + `DR-ZA-01` (khuôn
TD-0171): đổi giá trị này là đổi arm chạy dry-run/live, nên phải sửa một dòng có nhắc tới quyết định, không
phải một hằng số vô danh. Không khẳng định gì về hiệu năng.

⚠️ `test_td0244_stoploss_on_exchange.py` cũng ghim `"Z3"`, vì lý do KHÁC (trạng thái N/A của D2c, `MT-43`).
Đổi arm thì cả hai cùng đỏ, và đó là chủ ý: mỗi ca buộc xét lại đúng một quyết định.
"""

from __future__ import annotations

from tool_d.arm_switches import ARM_HOP_LE
from tool_d.config.loader import load_tool_d_config, resolve

KHOA_ARM = "tier_c.arm_ablation.arm"


def _arm() -> str:
    return str(resolve(load_tool_d_config(), KHOA_ARM))


def test_arm_nap_giu_nguyen_theo_mt35_va_dr_za_01() -> None:
    arm = _arm()
    assert arm == "Z3", (
        f"{KHOA_ARM} đã đổi từ 'Z3' sang {arm!r}. Đây là arm chạy dry-run và (khi tới D12) live. "
        "Theo MT-35: arm sản xuất = arm PASS Nhánh 1; DR-ZA-01 ghi Z0-T1 FAIL ở cổng D4 ⇒ hiện KHÔNG có arm "
        "sản xuất, và Z0 không phải phương án dự phòng. Đổi giá trị này cần một DR MỚI sau khi có arm PASS "
        "Nhánh 1 — sửa dòng assert này đồng thời nêu mã DR đó."
    )


def test_arm_nap_thuoc_tap_hop_le() -> None:
    assert _arm() in ARM_HOP_LE
