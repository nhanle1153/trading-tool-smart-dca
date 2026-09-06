"""Ba trạng thái dữ liệu — ràng buộc 0d.6 (spec dòng 618-633).

Không được gộp "chưa đo" thành 0. Không được dùng giá trị lính canh. Không
được hiện số cũ kèm cảnh báo — thà để trống. Canh bởi L-Z41.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Generic, TypeVar

T = TypeVar("T")


class Status(Enum):
    """Ba trạng thái, không gộp thành 0 (spec dòng 618-633)."""

    PENDING = "pending"  # chưa chạy phép đo
    UNREADABLE = "unreadable"  # đã cố đo nhưng đọc lỗi
    OK = "ok"  # đo được, value hợp lệ


@dataclass(frozen=True)
class Measured(Generic[T]):
    """Một con số có thể chưa đo được, hoặc đo lỗi, hoặc đo xong.

    `render()` là đường DUY NHẤT đưa số ra báo cáo — không nhánh nào khác
    được phép format giá trị này để in ra. Không có nhánh "hiện số cũ kèm
    cảnh báo" (spec dòng 629-630): trạng thái unreadable chỉ hiện lý do,
    không bao giờ hiện một số cũ nào.

    Bất biến (`__post_init__` canh): `value` chỉ tồn tại khi `status == OK`.
    Đây là cách cấm "bịa 0.0 khi chưa đo" ở tầng KIỂU DỮ LIỆU, không phải
    bằng quy ước gọi hàm — không có cách nào tạo ra một `Measured` mang cả
    status=PENDING lẫn value=0.0.
    """

    status: Status
    value: T | None
    note: str | None = None

    def __post_init__(self) -> None:
        if self.status is Status.OK and self.value is None:
            raise ValueError("status=OK nhưng value=None — không hợp lệ")
        if self.status is not Status.OK and self.value is not None:
            raise ValueError(
                f"status={self.status.value} nhưng value={self.value!r} — "
                "chỉ status=OK mới được mang value (cấm hiện số cũ kèm cảnh báo)"
            )

    @classmethod
    def pending(cls, why: str) -> "Measured[T]":
        """Chưa chạy phép đo. `why`: lý do, VD 'chưa có kết quả backtest'."""
        return cls(status=Status.PENDING, value=None, note=why)

    @classmethod
    def unreadable(cls, why: str) -> "Measured[T]":
        """Đã cố đo nhưng đọc lỗi. `why`: lý do, VD 'file .seal hỏng'."""
        return cls(status=Status.UNREADABLE, value=None, note=why)

    @classmethod
    def ok(cls, value: T) -> "Measured[T]":
        """Đo được, giá trị hợp lệ."""
        return cls(status=Status.OK, value=value, note=None)

    def render(self) -> str:
        """Chuỗi hiển thị DUY NHẤT được phép dùng để in giá trị này ra báo
        cáo (E5) hoặc bảng GATE. Không bao giờ trả "0.0"/"-1"/"UNKNOWN" cho
        trạng thái khác OK — vì với trạng thái khác OK, không có `value` để
        mà trả (xem bất biến ở `__post_init__`).
        """
        if self.status is Status.PENDING:
            return f"chưa đo được ({self.note})" if self.note else "chưa đo được"
        if self.status is Status.UNREADABLE:
            return f"lỗi đọc: {self.note}" if self.note else "lỗi đọc"
        return str(self.value)

    def is_ok(self) -> bool:
        return self.status is Status.OK


# Giá trị lính canh — nếu chúng lọt ra khỏi render() thì đó là dấu hiệu của
# lỗi tầng đo cũ (bịa số khi chưa đo, hoặc để sót placeholder), KHÔNG PHẢI
# kết quả đo thật (spec dòng 629-630, test L-Z41).
#
# 0.0 CỐ Ý không nằm trong danh sách: 0.0 là một giá trị đo được HỢP LỆ (ví
# dụ "0 lệnh TIME_STOP" là một kết quả thật). Việc cấm "0.0 giả" được đảm
# bảo bằng bất biến kiểu dữ liệu ở Measured, không phải bằng cách cấm chuỗi
# "0.0" xuất hiện trong văn bản — cấm theo chuỗi sẽ tạo dương tính giả trên
# những giá trị 0.0 hợp lệ.
_SENTINEL_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?<![\w.+-])-1(?![\w.])"),  # "-1" như một token độc lập
    re.compile(r"\bUNKNOWN\b"),
    re.compile(r"\bN/A\b"),
)


def scan_for_sentinels(rendered_output: str) -> list[str]:
    """Dò một khối văn bản đã render (VD toàn bộ nội dung periodic_report)
    tìm giá trị lính canh lọt ra ngoài (L-Z41). Trả về danh sách mẫu vi phạm
    tìm thấy; rỗng = sạch.
    """
    return [p.pattern for p in _SENTINEL_PATTERNS if p.search(rendered_output)]


def audit_line(*, ok: int, fail: int, unmeasured: int, total: int) -> str:
    """Dòng tổng kết bắt buộc của bảng GATE (spec dòng 632):
    "đã audit N/M (X đạt, Y chưa đạt, Z chưa đo được)".
    """
    if ok + fail + unmeasured != total:
        raise ValueError(
            f"ok({ok}) + fail({fail}) + unmeasured({unmeasured}) != "
            f"total({total}) — kế toán sai, không được in ra"
        )
    audited = ok + fail
    return (
        f"đã audit {audited}/{total} "
        f"({ok} đạt, {fail} chưa đạt, {unmeasured} chưa đo được)"
    )
