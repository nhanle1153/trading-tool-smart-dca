"""Kế toán ngân sách trial — DR-014 §2, §5 (spec dòng 3479-3546).

Kế toán THUẦN — không đọc/ghi file. `registry.py` gọi các hàm ở đây sau
khi đã tính `n_used`/`n_reserved` từ bản chiếu sổ sự kiện.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# §14 #28 — chốt trước, không sửa sau khi thấy dữ liệu (spec dòng 3541-3546).
REFUND_CAP_PER_HYPOTHESIS = 3

# §12c.2 — ngân sách trial TÁI TẠO. Hai hằng số chốt trước, không sửa khi
# đã thấy dữ liệu (spec: "Đặt 20 hay 30 đều được, miễn chốt trước").
LENH_MOI_CHO_MOT_TRIAL = 25  # +1 trial / 25 lệnh đã đóng
B3_TRAN_TICH_LUY = 20  # 🔒 trần TÍCH LUỸ, spec dòng 4604
LENH_MOI_DIEM_QUYET_DINH = 100  # §12c.1 — điểm quyết định mỗi 100 lệnh đóng


def b3_tai_sinh(so_lenh_da_dong: int) -> int:
    """Ngân sách B3 sinh thêm từ dữ liệu OOS thật (§12c.2, L-Z27).

    `floor(lệnh / 25)`, chặn trần 20. Trần là phần quan trọng: nó chặn
    kịch bản *"để dành 3 năm rồi tiêu một lúc"* — dồn lại tiêu một lượt
    thì quay về đúng khai thác dữ liệu quy mô lớn, thứ mà cả ngân sách
    trial được dựng để chặn.

    🔴 Hàm này là ĐƯỜNG DUY NHẤT để B3 tăng. L-Z27 cấm "tăng bằng tay",
    nên `TrialLedger` không nhận một con số ngân sách nào từ người gọi —
    chỉ nhận SỐ LỆNH rồi tự áp công thức. Cùng thủ pháp `luan_diem` của
    TD-0125: cái không nên khai thì làm cho nó KHÔNG BIỂU DIỄN ĐƯỢC, thay
    vì viết luật rồi trông chờ người nhớ luật.
    """
    if so_lenh_da_dong < 0:
        raise ValueError(f"số lệnh đã đóng không thể âm: {so_lenh_da_dong}")
    return min(so_lenh_da_dong // LENH_MOI_CHO_MOT_TRIAL, B3_TRAN_TICH_LUY)


def diem_quyet_dinh_da_qua(so_lenh_da_dong: int) -> int:
    """Số điểm quyết định đã đi qua = `floor(lệnh / 100)` (§12c.1).

    Quyền đổi tham số gắn với SỐ MẪU, không gắn với lịch — nên con số này
    suy từ lệnh đã đóng, không ai đặt được bằng tay.
    """
    if so_lenh_da_dong < 0:
        raise ValueError(f"số lệnh đã đóng không thể âm: {so_lenh_da_dong}")
    return so_lenh_da_dong // LENH_MOI_DIEM_QUYET_DINH


@dataclass(frozen=True)
class HypothesisKey:
    """Khoá của trần trả lại 3 lần (DR-014 §5): cùng hypothesis_slot +
    param_under_test + param_value được coi là "cùng một giả thuyết".
    """

    hypothesis_slot: str
    param_under_test: str
    param_value: Any

    def matches(self, *, hypothesis_slot: str, param_under_test: str, param_value: Any) -> bool:
        return (
            self.hypothesis_slot == hypothesis_slot
            and self.param_under_test == param_under_test
            and self.param_value == param_value
        )


def available(*, n_dang_ky: int, n_tai_sinh: int, n_used: int, n_reserved: int) -> int:
    """Khả dụng = (N_ĐĂNG_KÝ + N_tái_sinh) − Σcontrib(CONSUMED) −
    Σcontrib(RESERVED) (DR-014 §2, spec dòng 3484-3485).

    Trial ĐÃ TIÊU không bao giờ quay lại pool — hàm này không có đường
    nào "hoàn" n_used, đúng thiết kế "không thể hoàn tác".
    """
    return n_dang_ky + n_tai_sinh - n_used - n_reserved
