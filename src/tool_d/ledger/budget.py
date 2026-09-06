"""Kế toán ngân sách trial — DR-014 §2, §5 (spec dòng 3479-3546).

Kế toán THUẦN — không đọc/ghi file. `registry.py` gọi các hàm ở đây sau
khi đã tính `n_used`/`n_reserved` từ bản chiếu sổ sự kiện.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# §14 #28 — chốt trước, không sửa sau khi thấy dữ liệu (spec dòng 3541-3546).
REFUND_CAP_PER_HYPOTHESIS = 3


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
