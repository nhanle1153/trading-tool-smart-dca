"""TD-0255 (`DR-TRIEN-KHAI-01`) — phần PHỦ cấu hình của một suất B1 SUY từ đúng thứ khai vào sổ.

🔴 Vì sao module này tồn tại: E1 nhận `--param-under-test`/`--param-value` (vào dòng RESERVE) và `--ghi-de` (thứ
THẬT SỰ chạy) qua hai cờ độc lập. Với B1 hai thứ đó phải là MỘT: sổ ghi `zss_threshold = 0.4` mà lượt chạy phủ giá
trị khác là một suất trial mua phép đo KHÁC thứ đã ghi, và không lớp canh nào thấy — đúng hình `MT-23`
(*"sổ ghi CẤU HÌNH, không ghi TẬP LỆNH"*). Nên với B1, E1 TỪ CHỐI `--ghi-de` và gọi hàm này.

Arm lấy từ bảng ứng viên của chính `DR-D5-01` (`Z0-T1`), KHÔNG từ `tool_d_config.yaml`: khoá
`tier_c.arm_ablation.arm` của file giữ `"Z3"` là arm NẠP/dry-run, không phải arm sản xuất (`TD-0227` đóng không
đổi arm theo `MT-35` + `DR-ZA-01`, `ca40f96`), mà D5 chạy `Z0-T1` bất kể file ghi gì (`DR-D5-01` §1).

Hàm này chỉ ÁNH XẠ. Giá trị có thuộc danh sách thử không, có trùng suất chưa hoàn không — việc của
`kiem_dat_cho_b1()` ở cửa ghi sổ (một luật, một chỗ).
"""

from __future__ import annotations

from typing import Any

from tool_d.calibration.ung_vien import PARAM_MOC, PARAM_XAC_NHAN, BangUngVien, UngVienError

KHOA_ARM = "tier_c.arm_ablation.arm"
TANG_THAM_SO = "tier_b"


def ghi_de_cho_b1(param_under_test: str, param_value: Any, bang: BangUngVien) -> dict[str, Any]:
    """`{khoá dotted: giá trị}` cho `dung_moi_truong()`. Luôn có khoá arm."""
    ghi_de: dict[str, Any] = {KHOA_ARM: bang.arm}
    if param_under_test == PARAM_MOC:
        if param_value is not None:
            raise UngVienError(f"{PARAM_MOC} không mang giá trị (mọi tham số ở mốc), nhận {param_value!r}")
        return ghi_de
    if param_under_test == PARAM_XAC_NHAN:
        if not isinstance(param_value, dict) or not param_value:
            raise UngVienError(f"{PARAM_XAC_NHAN} cần dict khoá → giá trị đã thắng, nhận {param_value!r}")
        cap = dict(param_value)
    else:
        cap = {param_under_test: param_value}
    for khoa, gia_tri in cap.items():
        if khoa not in bang.tham_so:
            raise UngVienError(f"{khoa!r} không thuộc {sorted(bang.tham_so)} (DR-D5-01 §2.1)")
        ghi_de[f"{TANG_THAM_SO}.{khoa}"] = gia_tri
    return ghi_de


__all__ = ["KHOA_ARM", "ghi_de_cho_b1"]
