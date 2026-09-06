"""L-Z36 🔴 CRITICAL — mọi entrypoint E1-E8 gọi measurement_guard() trước
lệnh tốn thời gian đầu tiên; danh sách đóng không lọt/thừa entrypoint
(spec dòng 546-550, 671-674).
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from tool_d.measurement.entrypoint_registry import (
    CLOSED_ENTRYPOINTS,
    ENTRYPOINTS_DIR,
    assert_closed_entrypoint_set,
)
from tool_d.measurement.guard_ast_check import find_guard_violation


def test_closed_list_matches_disk() -> None:
    assert_closed_entrypoint_set(ENTRYPOINTS_DIR)


@pytest.mark.parametrize("filename", sorted(CLOSED_ENTRYPOINTS.values()))
def test_main_calls_guard_before_expensive_work(filename: str) -> None:
    violation = find_guard_violation(ENTRYPOINTS_DIR / filename)
    assert violation is None, violation


def test_teeth_extra_entrypoint_not_in_closed_list_fails(tmp_path: Path) -> None:
    """Chứng minh test có răng (verify TD-0017): thêm e9_tmp.py ngoài danh
    sách đóng vào một bản sao thư mục entrypoints/ -> phải FAIL."""
    shadow = tmp_path / "entrypoints"
    shutil.copytree(ENTRYPOINTS_DIR, shadow)
    (shadow / "e9_tmp.py").write_text("def main() -> None:\n    pass\n", encoding="utf-8")

    with pytest.raises(AssertionError):
        assert_closed_entrypoint_set(shadow)


def test_teeth_missing_entrypoint_fails(tmp_path: Path) -> None:
    """Xoá một E-số khỏi bản sao -> phải FAIL (không chỉ canh file thừa)."""
    shadow = tmp_path / "entrypoints"
    shutil.copytree(ENTRYPOINTS_DIR, shadow)
    (shadow / "run_backtest.py").unlink()

    with pytest.raises(AssertionError):
        assert_closed_entrypoint_set(shadow)


def test_teeth_missing_guard_call_fails(tmp_path: Path) -> None:
    """Entrypoint không gọi guard -> AST phải bắt được."""
    bad = tmp_path / "no_guard.py"
    bad.write_text(
        "def main() -> int:\n"
        "    do_expensive_work()\n"
        "    return 0\n",
        encoding="utf-8",
    )
    assert find_guard_violation(bad) is not None


def test_teeth_call_before_guard_fails(tmp_path: Path) -> None:
    """Có lệnh khác chạy TRƯỚC measurement_guard() -> phải bắt được
    (đúng ràng buộc 'TRƯỚC khi làm bất cứ việc gì tốn thời gian', spec dòng 541)."""
    bad = tmp_path / "guard_too_late.py"
    bad.write_text(
        "from tool_d.measurement.guard import measurement_guard\n\n"
        "def main() -> int:\n"
        "    do_expensive_work()\n"
        "    measurement_guard('E1')\n"
        "    return 0\n",
        encoding="utf-8",
    )
    assert find_guard_violation(bad) is not None


def test_teeth_decorator_wrapped_main_fails(tmp_path: Path) -> None:
    """main() bị bọc decorator -> phải bắt được (CLAUDE.md quy tắc N5:
    không bọc decorator, vì AST không suy luận được qua decorator)."""
    bad = tmp_path / "decorated.py"
    bad.write_text(
        "from tool_d.measurement.guard import measurement_guard\n\n"
        "def some_decorator(fn):\n"
        "    return fn\n\n"
        "@some_decorator\n"
        "def main() -> int:\n"
        "    measurement_guard('E1')\n"
        "    return 0\n",
        encoding="utf-8",
    )
    assert find_guard_violation(bad) is not None
