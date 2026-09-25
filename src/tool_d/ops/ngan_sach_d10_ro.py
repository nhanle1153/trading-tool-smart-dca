"""TD-0412 — máy canh D10 cho ứng viên IQ-0003 `RoFunding` (`DR-D10-02` §6, §6.3) và vốn rổ D10.

Khác máy canh CTRL (`ngan_sach_d10.py`, DCA tuần tự ≤ 20 vị thế): rổ mở 2k vị thế CÙNG LÚC tại mỗi lần cân rổ, nên không
có "tuần tự" hay "20 vị thế". Luật (N1 — file này thi hành, không định nghĩa lại):
- §6.3 Q8: dừng mở vị thế mới khi đã có ≥ 30 lệnh vào/ra khớp VÀ ≥ 7 lần cân rổ; hạn 14 ngày từ vị thế đầu, gia hạn đúng
  một lần nếu chưa đủ mẫu. Lệnh RA không qua máy canh (đóng vị thế là chiều an toàn).
- Q2: tổng ký quỹ đang mở ≤ 50% số dư (cùng hằng với máy canh CTRL — một nguồn).
- §6.3 Q7: vốn rổ D10 = 2k × sàn Tool D lớn nhất trong rổ × `he_so_le_san` / `ro_don_bay` (với rổ 10 cặp: k = 3 ⇒ 6 × sàn × 1,10).

Trạng thái (số lệnh, số lần cân rổ, mốc đầu) do tầng gọi đọc TỪ DB live mỗi lần xét (MT-40). N6: số dư không đọc được ⇒ từ chối.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from tool_d.ops.ngan_sach_d10 import CUA_SO, GIA_HAN, TRAN_KY_QUY_TREN_SO_DU
from tool_d.ro_funding import so_k

DU_LENH_KHOP = 30  # DR-D10-02 §6.3 Q8
DU_LAN_CAN_RO = 7  # DR-D10-02 §6.3 Q8


class NganSachD10RoError(ValueError):
    """Đầu vào hỏng khi tính vốn D10 — fail-closed (N6)."""


@dataclass(frozen=True)
class TrangThaiD10Ro:
    so_lenh_khop: int  # lệnh vào + ra (không tính lệnh stop) đã khớp trong đợt D10
    so_lan_can_ro: int  # số lần cân rổ khác nhau có lệnh vào khớp
    moc_vi_the_dau: datetime | None
    ky_quy_dang_mo: float
    so_du: float | None


def du_mau(tt: TrangThaiD10Ro) -> bool:
    return tt.so_lenh_khop >= DU_LENH_KHOP and tt.so_lan_can_ro >= DU_LAN_CAN_RO


def han_chot(tt: TrangThaiD10Ro) -> datetime | None:
    """Mốc cuối được mở vị thế; `None` khi chưa có vị thế nào. Chưa đủ mẫu ⇒ gia hạn đúng một lần."""
    if tt.moc_vi_the_dau is None:
        return None
    han = tt.moc_vi_the_dau + CUA_SO
    if not du_mau(tt):
        han += GIA_HAN
    return han


def xet_vao_lenh(tt: TrangThaiD10Ro, *, ky_quy_lenh: float, now: datetime) -> tuple[str, ...]:
    """Lý do TỪ CHỐI một lệnh VÀO của rổ D10. Rỗng = được vào."""
    ly_do: list[str] = []
    if du_mau(tt):
        ly_do.append(
            f"đã đủ mẫu D10 ({tt.so_lenh_khop} lệnh ≥ {DU_LENH_KHOP}, {tt.so_lan_can_ro} lần cân rổ ≥ {DU_LAN_CAN_RO}) — "
            "dừng mở vị thế mới (DR-D10-02 §6.3 Q8)"
        )
    han = han_chot(tt)
    if han is not None and now >= han:
        ly_do.append(f"hết cửa sổ D10 lúc {han.isoformat()} (14 ngày + gia hạn đúng một lần) — không ép thêm")
    so_du = tt.so_du
    if so_du is None or not math.isfinite(so_du) or so_du <= 0:
        ly_do.append(f"số dư không đọc được ({so_du!r}) — không xét được trần ký quỹ (N6)")
    elif not math.isfinite(ky_quy_lenh) or ky_quy_lenh < 0 or not math.isfinite(tt.ky_quy_dang_mo):
        ly_do.append(f"ký quỹ không hợp lệ (đang mở {tt.ky_quy_dang_mo!r}, lệnh {ky_quy_lenh!r}) (N6)")
    elif tt.ky_quy_dang_mo + ky_quy_lenh > TRAN_KY_QUY_TREN_SO_DU * so_du:
        ly_do.append(
            f"ký quỹ sau lệnh {tt.ky_quy_dang_mo + ky_quy_lenh:.4f} > {TRAN_KY_QUY_TREN_SO_DU:.0%} số dư {so_du:.4f} "
            "(DR-D10-02 Q2)"
        )
    return tuple(ly_do)


def von_ro_d10(
    san_theo_cap: Iterable[float],
    *,
    so_cap_ro: int,
    ty_le_k: float,
    k_toi_thieu: int,
    he_so_le_san: float,
    don_bay: float,
) -> float:
    """§6.3 Q7: `2k × max(sàn) × he_so_le_san / ro_don_bay` — mọi vị thế (vốn × đòn bẩy / 2k) đều ≥ sàn lớn nhất × lề."""
    san = [float(x) for x in san_theo_cap]
    if not san or not all(math.isfinite(x) and x > 0 for x in san):
        raise NganSachD10RoError(f"sàn Tool D của rổ hỏng hoặc rỗng: {san!r} — không định vốn được (N6)")
    if don_bay <= 0 or he_so_le_san < 1:
        raise NganSachD10RoError(f"ro_don_bay={don_bay!r}, he_so_le_san={he_so_le_san!r} không hợp lệ")
    k = so_k(so_cap_ro, ty_le_k=ty_le_k, k_toi_thieu=k_toi_thieu)
    if 2 * k > so_cap_ro:
        raise NganSachD10RoError(f"2k = {2 * k} > {so_cap_ro} cặp trong rổ — hai chân sẽ chồng nhau")
    return 2 * k * max(san) * he_so_le_san / don_bay
