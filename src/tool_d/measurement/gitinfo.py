"""git_sha + cờ working tree bẩn — một phần của khối xuất xứ (0d.5, dòng
607-609): `git_sha`, `reproducible_from_sha` (false nếu working tree bẩn).

🔴 Cấm tuyệt đối `git_sha == "" hoặc "UNKNOWN"` lọt vào provenance. Đây
đúng loại lỗi lặng mà PHẦN 0d tồn tại để chặn: bind mount Windows->Linux
gây "dubious ownership" (git trả rỗng thay vì lỗi rõ ràng), image thiếu
`git`, hoặc `.git` không được mount vào container. Vì vậy các hàm ở đây
RAISE khi không xác định được, không bao giờ trả về giá trị lính canh —
nơi gọi (provenance.py) tự quyết định xử lý raise đó thế nào.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


class GitInfoError(RuntimeError):
    """git không truy vấn được. KHÔNG được bắt lỗi này rồi trả "UNKNOWN"."""


@dataclass(frozen=True)
class GitInfo:
    sha: str
    is_clean: bool


def _run_git(args: list[str], cwd: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "--no-optional-locks", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise GitInfoError(f"không gọi được git {args}: {exc}") from exc
    if result.returncode != 0:
        raise GitInfoError(
            f"git {' '.join(args)} thất bại (exit {result.returncode}): "
            f"{result.stderr.strip()}"
        )
    return result.stdout


def get_git_info(repo_dir: Path) -> GitInfo:
    """git_sha + cờ working tree bẩn.

    Raise `GitInfoError` nếu không xác định được — KHÔNG BAO GIỜ trả
    "UNKNOWN" hay chuỗi rỗng.
    """
    sha = _run_git(["rev-parse", "HEAD"], repo_dir).strip()
    if not sha:
        # "dubious ownership" và một số lỗi git khác trả exit 0 kèm stdout
        # rỗng thay vì lỗi rõ ràng — chặn thêm ở đây cho chắc.
        raise GitInfoError("git rev-parse HEAD trả rỗng")
    status = _run_git(["status", "--porcelain"], repo_dir)
    return GitInfo(sha=sha, is_clean=(status.strip() == ""))
