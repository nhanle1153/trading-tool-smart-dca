"""Swing detection thuần — PHẦN 1 §1.1 (TD-0100).

Hàm THUẦN: chỉ dùng phần tử có trong mảng `gia` được truyền vào, không
đọc gì khác. Đây chính là cách thi hành ràng buộc point-in-time của
H4-D (§7.2): tại nến `i` vừa đóng, hệ thống thật CHỈ CÓ dữ liệu tới `i`
— nên swing tại `i` chỉ xác nhận được từ nến `i+k` trở đi, không sớm hơn.
Việc "không đọc dữ liệu sau t" được đảm bảo bằng thiết kế (slice trên
đúng mảng được đưa vào), không phải một điều kiện kiểm tra thêm.
"""

from __future__ import annotations

from typing import Literal, Sequence

K_XAC_NHAN = 3  # §1.1 — cố định, 0 tham số mới


def la_diem_swing(
    gia: Sequence[float], i: int, *, loai: Literal["day", "dinh"], k: int = K_XAC_NHAN
) -> bool:
    """True nếu nến `i` là swing point trong cửa sổ [i-k, i+k] (§1.1).

    `gia` là dãy giá thấp (đáy) hoặc giá cao (đỉnh) tương ứng với `loai`.
    Trả về False (chưa xác nhận được — không phải "không phải swing")
    khi `gia` chưa đủ dài để có đủ `k` nến sau `i`.
    """
    if i - k < 0 or i + k >= len(gia):
        return False
    cua_so = gia[i - k : i + k + 1]
    diem = gia[i]
    if loai == "day":
        return diem == min(cua_so)
    return diem == max(cua_so)
