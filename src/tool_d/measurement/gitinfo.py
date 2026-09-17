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


# Thư mục mà một file chưa theo dõi nằm trong đó VẪN làm hỏng bằng chứng:
# pytest thu cả file `.py` chưa commit trong `tests/`, và `src/`/`entrypoints/`/
# `config/`/`registry/schemas/` đều chảy thẳng vào kết quả chạy.
THU_MUC_ANH_HUONG_PHEP_DO = ("src/", "tests/", "entrypoints/", "config/", "registry/schemas/")


def thay_doi_anh_huong_phep_do(repo_dir: Path) -> list[str]:
    """Các thay đổi chưa commit CÓ THỂ làm lệch kết quả đo. Rỗng = an toàn.

    Chuyển từ `entrypoints/trial_ledger_audit.py` (cổng D3, TD-0147) sang đây
    ngày 17/09/2026 để E7 `--ro-t1` (TD-0247, `DR-D1-03` §2) dùng CHUNG một
    quy tắc — không chép lại (MT-03). E6 import lại dưới tên cũ.

    KHÔNG dùng thẳng `GitInfo.is_clean`: nó coi mọi thứ chưa commit là bẩn,
    kể cả ảnh chụp màn hình và thư mục nháp ở gốc repo. Với repo này (luôn
    có rác như vậy) thì cổng sẽ KHÔNG BAO GIỜ đóng được — và một chốt không
    bao giờ thoả được sẽ bị người ta gỡ bỏ, tức tệ hơn là không có.

    Phân biệt:
      • file ĐÃ THEO DÕI bị sửa/xoá/staged → LUÔN tính, vì nó đổi hành vi
        mà không nằm trong sha sẽ được ghi;
      • file CHƯA THEO DÕI → chỉ tính khi nằm trong `THU_MUC_ANH_HUONG_PHEP_DO`.
        Một file `.py` chưa commit trong `tests/` VẪN được pytest thu và
        VẪN không có trong commit — đúng loại làm bằng chứng sai.
    """
    dong = subprocess.run(
        ["git", "--no-optional-locks", "status", "--porcelain"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    ).stdout.splitlines()

    ket_qua: list[str] = []
    for d in dong:
        if not d.strip():
            continue
        trang_thai, duong_dan = d[:2], d[3:].strip().strip('"')
        if trang_thai == "??":
            if duong_dan.startswith(THU_MUC_ANH_HUONG_PHEP_DO):
                ket_qua.append(f"[chưa theo dõi, trong vùng đo] {duong_dan}")
        else:
            ket_qua.append(f"[{trang_thai.strip()}] {duong_dan}")
    return ket_qua
