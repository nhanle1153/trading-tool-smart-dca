"""L-Z38 — wrapper backtest từ chối chạy nếu thiếu `--cache none`.

KHÔNG tự chèn `--cache none` khi vắng mặt — nếu wrapper tự chèn, test
L-Z38 luôn xanh và mất tác dụng, và người vận hành có thể vô tình chạy
lệnh dính cache cũ mà không hề biết (spec dùng đúng chữ "từ chối", dòng 678).
"""

from __future__ import annotations

from collections.abc import Sequence

from tool_d.measurement.guard import extract_cache_mode

EXIT_CACHE_VIOLATION = 87


def assert_cache_none(argv: Sequence[str]) -> int | None:
    """Trả `EXIT_CACHE_VIOLATION` nếu thiếu `--cache none` trong argv,
    ngược lại trả `None` (được phép tiếp tục).

    Không raise — để `main()` của entrypoint tự quyết định thoát bằng
    exit code nào, nhất quán với cách `measurement_guard()` trả về.
    """
    if extract_cache_mode(argv) != "none":
        print(
            "🛑 TỪ CHỐI: thiếu `--cache none` (L-Z38). Không tự chèn — "
            "gõ lại lệnh kèm đúng cờ này."
        )
        return EXIT_CACHE_VIOLATION
    return None
