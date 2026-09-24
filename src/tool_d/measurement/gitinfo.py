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
    for trang_thai, duong_dan in _loc_status_anh_huong(dong):
        if trang_thai == "??":
            ket_qua.append(f"[chưa theo dõi, trong vùng đo] {duong_dan}")
        else:
            ket_qua.append(f"[{trang_thai.strip()}] {duong_dan}")
    return ket_qua


def _loc_status_anh_huong(dong: list[str]) -> list[tuple[str, str]]:
    """Quy tắc lọc DUY NHẤT cho *"thay đổi chưa commit nào ảnh hưởng phép đo"* — `thay_doi_anh_huong_phep_do()` và
    `bam_thay_doi_chua_commit()` cùng gọi, không chép (MT-03). Trả `(trạng_thái, đường_dẫn)` từ `git status --porcelain`."""
    ket_qua: list[tuple[str, str]] = []
    for d in dong:
        if not d.strip():
            continue
        trang_thai, duong_dan = d[:2], d[3:].strip().strip('"')
        if trang_thai == "??" and not duong_dan.startswith(THU_MUC_ANH_HUONG_PHEP_DO):
            continue
        ket_qua.append((trang_thai, duong_dan))
    return ket_qua


def bam_thay_doi_chua_commit(repo_dir: Path) -> str:
    """TD-0380 (`DR-DINH-DANH-01` §4.1) — sha256 NỘI DUNG mọi thay đổi chưa commit ảnh hưởng phép đo.

    22/22 dòng RESERVE tới 24/09/2026 mang `reproducible_from_sha = False`: với 2–3 phiên cùng một thư mục, cây gần như
    không bao giờ sạch, nên `code_commit` một mình KHÔNG định danh được mã đã chạy. Băm này bù phần đó: hai lần chạy
    cùng commit mà khác thay đổi dở ⇒ khác băm. Cây sạch ⇒ băm của danh sách rỗng (một giá trị thật, không phải lính canh).

    FAIL-CLOSED: git lỗi ⇒ `GitInfoError` (qua `_run_git`), KHÔNG trả "sạch" — khác `thay_doi_anh_huong_phep_do()`
    vốn bỏ qua mã thoát. Chỉ băm, không lưu nội dung: biết *"khác mã"*, không tái dựng được mã (DR §8).
    """
    import hashlib
    import json

    # `checkStat=minimal` + `trustctime=false`: index do git Windows ghi, container Linux thấy inode/uid/ctime khác
    # ⇒ git mặc định đọc lại NỘI DUNG mọi file mỗi lần (đo 24/09/2026: 1,9 s/lần). Chỉ so mtime + kích thước thì
    # 0,9 s, danh sách thay đổi Y HỆT (đo cùng lúc). Cờ `-c` chỉ sống trong lệnh này — không ghi config, không ghi index.
    dong = _run_git(
        ["-c", "core.checkStat=minimal", "-c", "core.trustctime=false", "status", "--porcelain"], repo_dir
    ).splitlines()
    muc: list[tuple[str, str, str]] = []
    for trang_thai, duong_dan in _loc_status_anh_huong(dong):
        if " -> " in duong_dan:  # đổi tên: băm theo đường dẫn MỚI
            duong_dan = duong_dan.split(" -> ", 1)[1].strip().strip('"')
        p = repo_dir / duong_dan
        if p.is_dir():  # thư mục chưa theo dõi được git gộp thành một dòng `dir/`
            for f in sorted(x for x in p.rglob("*") if x.is_file()):
                muc.append((trang_thai, f.relative_to(repo_dir).as_posix(), _sha256_file(f)))
        elif p.is_file():
            muc.append((trang_thai, duong_dan, _sha256_file(p)))
        else:
            muc.append((trang_thai, duong_dan, "XOA"))
    muc.sort()
    return hashlib.sha256(json.dumps(muc, ensure_ascii=False).encode("utf-8")).hexdigest()


def _sha256_file(p: Path) -> str:
    import hashlib

    return hashlib.sha256(p.read_bytes()).hexdigest()
