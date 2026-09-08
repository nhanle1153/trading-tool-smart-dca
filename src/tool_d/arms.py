"""TD-0182 — công tắc TẦNG LỌC TREND cho arm ablation Z0-T0 / Z0-T1 / Z0-T2.

§10.1b nêu vấn đề bằng chữ rất thẳng: *"cả năm cấu hình Z0-Z3b đều CHỨA
NGUYÊN Phần 2 — bốn điều kiện lọc. Không arm nào bật/tắt chúng. Nếu tầng
1D vô dụng, hoặc có hại vì lọc mất setup tốt, thiết kế ablation hiện tại
KHÔNG PHÁT HIỆN ĐƯỢC."* Module này là cái công tắc đó.

════ Ba tầng, và ranh giới giữa chúng là gì ════

| Arm | Tầng | Còn lại điều kiện nào của Phần 2 |
|---|---|---|
| `Z0-T0` | `KHONG`  | không điều kiện nào |
| `Z0-T1` | `CHI_4H` | duy nhất: hướng 4H khớp hướng vào lệnh |
| `Z0-T2` | `DAY_DU` | cả bốn (§2.1 hướng-1D · §2.2 đồng thuận · ADX(1D)≥20 · tuổi ≥5) |

🔑 **`Z0-T2` KHÔNG phải arm thứ ba tốn trial — nó CHÍNH LÀ `Z0`.** Spec
§10.1b ghi *"Mốc so sánh — không phải arm mới, không tốn trial thêm"*.
Đếm nó thành một arm riêng là tiêu thừa một suất trên tổng 114 (đã ghi ở
DR-D4-01 §3). Ở đây `Z0` và `Z0-T2` cố ý ánh xạ về CÙNG một tầng.

════ Vì sao `CHI_4H` KHÔNG gọi `xac_nhan_da_khung()` ════

Đọc lướt thì `Z0-T1` = "bỏ tầng 1D, giữ §2.2" nghe như vẫn gọi hàm xác
nhận đa khung. Nhưng `xac_nhan_da_khung(huong_1d, huong_4h)` **so 1D với
4H** — nó CHÍNH LÀ tầng 1D đang được bỏ. Giữ nó lại thì `Z0-T1` vẫn phụ
thuộc 1D và arm không đo được thứ nó sinh ra để đo.

Xác nhận đa khung khi chỉ còn một khung thoái hoá thành: **hướng 4H khớp
hướng vào lệnh**. Đây là một diễn giải, không phải chữ của spec — ghi ra
để cãi lại được, cùng cách `cong_d35._huong_can_co()` ghi diễn giải của
nó.

════ Vì sao module này KHÔNG đọc file cấu hình ════

Nó nhận `tang` đã phân giải sẵn, không tự gọi `load_tool_d_config()`.
Giữ hàm THUẦN thì test được bằng số dựng tay và không phải mock đường
đọc file — cùng khuôn `trend_context.py` (nhận EMA/ADX tính sẵn, không
tự gọi TA-Lib). Tầng gọi lo việc đọc `tier_c.arm_ablation.tang_loc_trend`
qua `loader.py` (N4 — YAML là nguồn duy nhất; L-Z39 — KHÔNG từ env).
"""

from __future__ import annotations

from typing import Literal

from tool_d.trend_context import (
    NGUONG_ADX,
    K_TUOI_TREND_TOI_THIEU,
    TrendDir,
    du_dieu_kien_vao_lenh,
)

TangLocTrend = Literal["KHONG", "CHI_4H", "DAY_DU"]

TANG_HOP_LE: tuple[TangLocTrend, ...] = ("KHONG", "CHI_4H", "DAY_DU")

#: Ánh xạ tên arm → tầng. `Z0` và `Z0-T2` TRÙNG nhau có chủ đích (xem
#: docstring module): Z0-T2 là mốc so sánh, không phải arm mới.
#:
#: 🔴 **9 khoá — trùng đúng `arm_switches.ARM_HOP_LE` + alias `Z0-T2`.**
#: Chỉ `Z0-T0`/`Z0-T1` đổi trục trend; trục MÀ ARM ĐÓ THỰC SỰ ĐO
#: (SL/cỡ lệnh/DG/volume) không liên quan tới trục trend, nên Z1, Z2, Z3,
#: Z3b, Z0-V1, Z0-S1 đều giữ `DAY_DU` — tắt trend filter cho chúng sẽ đo
#: một biến thứ hai không ai đăng ký (MT-15's bài học: trộn hai trục vào
#: một arm). Bản đầu (TD-0182 phần độc lập, trước khi nối vào chiến lược)
#: chỉ có 4 khoá vì lúc đó chưa cần chạy CHIẾN LƯỢC với arm khác ngoài
#: nhóm T0/T1/T2 — thiếu sót lộ ra ngay khi `ZoneAbsorption` nạp với
#: `arm_ablation.arm = "Z3"` (cấu hình mặc định) và `tang_cua_arm` raise.
TANG_THEO_ARM: dict[str, TangLocTrend] = {
    "Z0-T0": "KHONG",
    "Z0-T1": "CHI_4H",
    "Z0-T2": "DAY_DU",
    "Z0": "DAY_DU",
    "Z1": "DAY_DU",
    "Z2": "DAY_DU",
    "Z3": "DAY_DU",
    "Z3b": "DAY_DU",
    "Z0-V1": "DAY_DU",
    "Z0-S1": "DAY_DU",
}


class ArmKhongHopLeError(ValueError):
    """Tầng lọc hoặc tên arm không nằm trong danh sách đóng. Fail-closed.

    Không có nhánh "mặc định về DAY_DU": một tên gõ sai mà lặng lẽ chạy
    như Z0 sẽ sinh ra một arm ghi nhãn `Z0-T1` nhưng đo `Z0-T2`, và
    không có gì trong kết quả lộ ra điều đó.
    """


def tang_cua_arm(ten_arm: str) -> TangLocTrend:
    """Tên arm → tầng lọc. Raise nếu tên không có trong bảng."""
    if ten_arm not in TANG_THEO_ARM:
        raise ArmKhongHopLeError(
            f"Arm không rõ: {ten_arm!r}. Danh sách đóng: {sorted(TANG_THEO_ARM)}."
        )
    return TANG_THEO_ARM[ten_arm]


def du_dieu_kien_trend_theo_tang(
    *,
    tang: TangLocTrend,
    huong_muc_tieu: TrendDir,
    huong_1d: TrendDir,
    huong_4h: TrendDir,
    adx_1d: float,
    tuoi_nen_1d: int | None,
) -> bool:
    """Phần 2 đã lọc theo `tang`. `True` = được phép vào lệnh.

    `DAY_DU` gọi THẲNG `du_dieu_kien_vao_lenh()` của `trend_context`,
    không chép lại bốn điều kiện — chép sang đây sẽ tạo nguồn sự thật
    thứ hai và hai bản trôi lệch, đúng lỗi MT-03 đã ghi sổ.
    """
    if tang not in TANG_HOP_LE:
        raise ArmKhongHopLeError(
            f"Tầng lọc không rõ: {tang!r}. Danh sách đóng: {list(TANG_HOP_LE)}."
        )

    if tang == "KHONG":
        return True

    if tang == "CHI_4H":
        # Chỉ §2.2 sau khi bỏ tầng 1D — xem docstring module về vì sao
        # KHÔNG gọi `xac_nhan_da_khung()` ở đây.
        return huong_4h == huong_muc_tieu

    return du_dieu_kien_vao_lenh(
        huong_muc_tieu=huong_muc_tieu,
        huong_1d=huong_1d,
        huong_4h=huong_4h,
        adx_1d=adx_1d,
        tuoi_nen=tuoi_nen_1d,
    )


__all__ = [
    "K_TUOI_TREND_TOI_THIEU",
    "NGUONG_ADX",
    "TANG_HOP_LE",
    "TANG_THEO_ARM",
    "ArmKhongHopLeError",
    "TangLocTrend",
    "du_dieu_kien_trend_theo_tang",
    "tang_cua_arm",
]
