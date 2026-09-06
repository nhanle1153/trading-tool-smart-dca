"""`assert_dataset_timerange()` — bộ chạy TỰ kiểm tra timerange, không
nhận lời khai của người chạy (L-Z55, DR-014 §2, spec dòng 3492-3494,
3973-3975).

Phạm vi áp DR-014 (đặt chỗ/tiêu/hoàn trả) = mọi lần chạy chạm CALIB/WFO/
LOCKBOX với mục đích đánh giá. Dòng CTRL (điểm kiểm soát §0d.4) và mọi
lần chạy trên tập EXPLORE nằm NGOÀI sổ đó — nhưng để "ngoài sổ" không
biến thành lỗ hổng ("khai là CTRL/EXPLORE để né đặt chỗ, rồi lặng lẽ đọc
CALIB/WFO/LOCKBOX"), bộ chạy PHẢI tự khẳng định timerange bằng assert,
không nhận nhãn dataset do người/code gọi tự xưng.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from tool_d.config.loader import ToolDConfig, resolve


class TimerangeViolationError(RuntimeError):
    """Dữ liệu quan sát được nằm ngoài ranh giới của dataset đã khai —
    coi là CHẠM TẬP ĐÁNH GIÁ (L-Z55, fail-closed)."""


@dataclass(frozen=True)
class DatasetBoundary:
    """Ranh giới thời gian của MỘT dataset, lấy từ cấu hình đã niêm
    phong (TD-0084 — chưa chốt mốc T0-T3 ở D0-PRE). KHÔNG được tính
    "boundary" từ cùng nguồn với "observed" trong cùng một lời gọi —
    nếu cả hai đến từ cùng chỗ không đáng tin, hàm này không bảo vệ
    được gì (xem docstring `assert_dataset_timerange`).
    """

    name: str  # "CALIB" | "WFO" | "LOCKBOX" | "EXPLORE" | "CTRL"
    start: date
    end: date


def assert_dataset_timerange(
    *,
    dataset: str,
    observed_start: date,
    observed_end: date,
    boundary: DatasetBoundary,
) -> None:
    """Raise `TimerangeViolationError` nếu:
      - `dataset` không khớp tên của `boundary` (nhãn tự xưng sai dataset), hoặc
      - `[observed_start, observed_end]` không nằm TRỌN trong
        `[boundary.start, boundary.end]`.

    Đây là bộ chạy TỰ KIỂM — gọi hàm này với `boundary` lấy từ cấu hình
    ĐÃ NIÊM PHONG của chính dataset đó, không phải giá trị người gọi tự
    tính rồi truyền vào cả hai vế của phép so sánh.
    """
    if dataset != boundary.name:
        raise TimerangeViolationError(
            f"Khai dataset={dataset!r} nhưng ranh giới đối chiếu là "
            f"của {boundary.name!r} — không khớp, TỪ CHỐI."
        )
    if observed_start < boundary.start or observed_end > boundary.end:
        raise TimerangeViolationError(
            f"Dữ liệu quan sát [{observed_start}, {observed_end}] nằm NGOÀI "
            f"ranh giới dataset {dataset!r} [{boundary.start}, {boundary.end}] "
            "— coi là CHẠM TẬP ĐÁNH GIÁ (L-Z55)."
        )


def dataset_boundaries_from_config(cfg: ToolDConfig) -> dict[str, DatasetBoundary]:
    """TD-0094 — `DatasetBoundary` cho CALIB/WFO/LOCKBOX đọc từ
    `tier_c.data_split` (T0-T3, DR-D0PRE-07, niêm phong "commit, không
    sửa") — nguồn sự thật DUY NHẤT (N4), không hardcode ngày ở nơi gọi.

    Sinh ra để nối với `assert_dataset_timerange()`: bên gọi (backtest/
    WFO/ablation, TD-0093 đã chứng minh KHÔNG được tin file trên đĩa về
    phạm vi ngày) đọc `[observed_start, observed_end]` THẬT từ dataframe
    đã tải, rồi assert với đúng `boundary` tương ứng ở đây — không được
    tính `observed_*` và `boundary` từ cùng một nguồn không đáng tin
    (xem docstring `DatasetBoundary`).
    """
    split = resolve(cfg, "tier_c.data_split")
    t0, t1, t2, t3 = (
        datetime.strptime(split[k], "%Y-%m-%d").date() for k in ("t0", "t1", "t2", "t3")
    )
    return {
        "CALIB": DatasetBoundary("CALIB", t0, t1),
        "WFO": DatasetBoundary("WFO", t1, t2),
        "LOCKBOX": DatasetBoundary("LOCKBOX", t2, t3),
    }
