"""Kiểm bằng AST: main() của entrypoint gọi measurement_guard() TRƯỚC lệnh
tốn thời gian đầu tiên, và không bọc trong decorator (spec dòng 671-674,
16 trong CLAUDE.md — "KHÔNG bọc trong decorator, L-Z36 kiểm bằng AST").

Đọc mã nguồn tĩnh (ast.parse), KHÔNG import/execute file — entrypoint thật
sẽ raise NotImplementedError hoặc làm việc nặng nếu chạy tới cuối main().
"""

from __future__ import annotations

import ast
from pathlib import Path

GUARD_FUNC_NAME = "measurement_guard"

# Những lệnh được coi là "dựng tham số", không phải "việc tốn thời gian" —
# đúng những gì khung TD-0016 dùng để chuẩn bị argv/args trước khi gọi guard.
ALLOWED_CALL_NAMES_BEFORE_GUARD = {"list", "build_parser", "parse_known_args"}


def _call_root_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _contains_call_to(node: ast.AST, name: str) -> bool:
    return any(
        isinstance(sub, ast.Call) and _call_root_name(sub) == name for sub in ast.walk(node)
    )


def find_guard_violation(path: Path) -> str | None:
    """Trả về mô tả vi phạm (str), hoặc None nếu file hợp lệ.

    Vi phạm gồm: không có `def main` ở top-level; `main` bị decorator bọc;
    `main` không gọi measurement_guard(); hoặc có lệnh khác (ngoài danh sách
    cho phép ở trên) chạy TRƯỚC lệnh gọi guard.
    """
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        return f"{path}: không đọc được ({exc})"

    tree = ast.parse(source, filename=str(path))
    main_defs = [
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main"
    ]
    if not main_defs:
        return f"{path}: không có hàm main() ở top-level module"
    main_fn = main_defs[0]

    if main_fn.decorator_list:
        return f"{path}: main() bị bọc decorator — L-Z36 cấm, phải thấy guard trực tiếp bằng AST"

    guard_index = None
    for i, stmt in enumerate(main_fn.body):
        if _contains_call_to(stmt, GUARD_FUNC_NAME):
            guard_index = i
            break

    if guard_index is None:
        return f"{path}: main() không gọi {GUARD_FUNC_NAME}()"

    for stmt in main_fn.body[:guard_index]:
        for sub in ast.walk(stmt):
            if isinstance(sub, ast.Call):
                name = _call_root_name(sub)
                if name is not None and name not in ALLOWED_CALL_NAMES_BEFORE_GUARD:
                    return (
                        f"{path}: gọi `{name}(...)` TRƯỚC {GUARD_FUNC_NAME}() — "
                        "vi phạm 'guard trước lệnh tốn thời gian đầu tiên' (spec dòng 541)"
                    )

    return None
