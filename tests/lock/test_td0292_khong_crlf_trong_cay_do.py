"""TD-0292 — test khoá: file ĐÃ THEO DÕI trong cây đo có `\\r\\n` trên đĩa ⇒ ĐỎ.

Vì sao cần (đo, không suy):
  (a) `.gitattributes` ép `eol=lf`, index luôn LF, nhưng host Windows vẫn ghi
      CRLF ra đĩa. Khi stat cache lệch, `git status --porcelain` báo `M` ẢO cho
      file có nội dung y hệt index ⇒ `thay_doi_anh_huong_phep_do()` coi cây bẩn
      ⇒ mọi `close_dN_gate` TỪ CHỐI đóng (đã xảy ra 17/09/2026). Lỗi chỉ lộ
      đúng lúc cần đóng cổng, không lúc nào khác.
  (b) `measurement/hashing.sha256_of()` đọc NHỊ PHÂN — nhạy đuôi dòng nếu một
      file văn bản trong cây đo vào `hash_many`.

🔴 KHÔNG phải vì `config_hash` hay khối băm DR: `loader.py`, `ung_vien.py`,
`cscv_cau_hinh.py` đều đọc `read_text()` (chế độ văn bản chuẩn hoá `\\r\\n`),
đã đo LF/CRLF cùng một băm. Ghi đúng lý do để không ai "sửa" nhầm chỗ đó.

Phạm vi = `gitinfo.THU_MUC_ANH_HUONG_PHEP_DO` (import, KHÔNG chép — đổi vùng đo
của cổng thì test này đi theo) + `docs/decisions/DR-*.md` có dòng
`` `sha256 = …` ``. Đuôi dòng lấy từ chính git (`ls-files --eol`, cột `w/`):
cùng phép phân loại văn bản/nhị phân mà `.gitattributes` áp, không tự đoán.

Sửa khi đỏ (đã đo 17/09/2026 trên 31 file): chuyển file về LF, rồi
`git add -- <file>` — blob trùng HEAD nên KHÔNG stage gì, chỉ làm mới stat.
Chính bước chuyển về LF cũng sinh `M` ảo ngay lập tức, và
`git update-index --refresh` KHÔNG gỡ được (báo "needs update", exit 1).
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from tool_d.measurement.gitinfo import THU_MUC_ANH_HUONG_PHEP_DO

REPO_ROOT = Path(__file__).resolve().parents[2]

DR_CO_KHOI_BAM = "docs/decisions/DR-*.md"
_KHOI_BAM = re.compile(r"`sha256 = [0-9a-f]{64}`")
_EOL_HONG = ("w/crlf", "w/mixed")

# Thời hạn rộng có chủ ý: đây là test về ĐUÔI DÒNG, không phải về độ trễ git.
# Hết hạn thì raise (đỏ rõ ràng), không treo suite — xem TD-0293 cho thời hạn
# của đường sản xuất.
_THOI_HAN_GIT_S = 120


def _ls_files_eol(repo_dir: Path, pathspecs: tuple[str, ...]) -> dict[str, str]:
    """{đường dẫn: cột `w/…`} cho mọi file ĐÃ THEO DÕI khớp pathspec."""
    kq = subprocess.run(
        ["git", "--no-optional-locks", "ls-files", "--eol", "-z", "--", *pathspecs],
        cwd=repo_dir,
        capture_output=True,
        timeout=_THOI_HAN_GIT_S,
        check=True,
    )
    ra: dict[str, str] = {}
    for muc in kq.stdout.decode("utf-8").split("\0"):
        if not muc:
            continue
        truong, _, duong_dan = muc.partition("\t")
        cot = truong.split()
        if len(cot) < 2 or not cot[1].startswith("w/"):
            raise AssertionError(f"không đọc được dòng `git ls-files --eol`: {muc!r}")
        ra[duong_dan] = cot[1]
    return ra


def quet_cay_do(repo_dir: Path) -> tuple[dict[str, str], list[str]]:
    """(các file đã quét → cột `w/`, các file đuôi dòng hỏng). Thuần theo repo_dir."""
    thu_muc = _ls_files_eol(repo_dir, THU_MUC_ANH_HUONG_PHEP_DO)
    dr = {
        p: w
        for p, w in _ls_files_eol(repo_dir, (DR_CO_KHOI_BAM,)).items()
        if _KHOI_BAM.search((repo_dir / p).read_text(encoding="utf-8"))
    }
    da_quet = {**thu_muc, **dr}
    hong = sorted(p for p, w in da_quet.items() if w in _EOL_HONG)
    return da_quet, hong


def test_cay_do_khong_co_file_crlf() -> None:
    _, hong = quet_cay_do(REPO_ROOT)
    assert not hong, (
        f"{len(hong)} file đã theo dõi trong cây đo có CRLF trên đĩa (index là LF) — "
        "`git status` có thể báo M ẢO và cổng từ chối đóng. Chuyển về LF rồi "
        "`git add -- <file>` (blob trùng HEAD ⇒ không stage gì; `update-index --refresh` "
        f"không đủ):\n  " + "\n  ".join(hong)
    )


def test_phep_quet_khong_rong() -> None:
    """Chặn PASS RỖNG: pathspec sai / git không thấy repo ⇒ quét 0 file ⇒ ca trên xanh vô nghĩa."""
    da_quet, _ = quet_cay_do(REPO_ROOT)
    for thu_muc in THU_MUC_ANH_HUONG_PHEP_DO:
        assert any(p.startswith(thu_muc) for p in da_quet), f"không quét được file nào trong {thu_muc}"
    assert "src/tool_d/measurement/gitinfo.py" in da_quet
    # Hai DR đang có khối băm máy đọc (`ung_vien.py`, `cscv_cau_hinh.py`).
    assert "docs/decisions/DR-D5-01-pham-vi-ung-vien-luat-chon-calibration.md" in da_quet
    assert "docs/decisions/DR-D9-01-wfo-cscv-pbo.md" in da_quet


# ── Kiểm có răng trên repo hộp cát ────────────────────────────────────────

def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "core.autocrlf=false", *args],
        cwd=repo, check=True, capture_output=True, timeout=_THOI_HAN_GIT_S,
    )


@pytest.fixture
def repo_cat(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    (tmp_path / ".gitattributes").write_bytes(b"* text=auto eol=lf\n")
    tep = {
        "config/a.yaml": b"x: 1\ny: 2\n",
        "src/m.py": b"A = 1\nB = 2\n",
        "docs/decisions/DR-CO-BAM.md": b"# DR\n`sha256 = " + b"a" * 64 + b"`\n",
        "docs/decisions/DR-KHONG-BAM.md": b"# DR\nkhong co khoi bam\n",
        "khac/ngoai.md": b"a\nb\n",
    }
    for p, noi_dung in tep.items():
        (tmp_path / p).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / p).write_bytes(noi_dung)
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "goc")
    return tmp_path


def _sang_crlf(p: Path) -> None:
    p.write_bytes(p.read_bytes().replace(b"\n", b"\r\n"))


def test_co_rang_bat_dung_file_trong_pham_vi(repo_cat: Path) -> None:
    for p in ("config/a.yaml", "docs/decisions/DR-CO-BAM.md",
              "docs/decisions/DR-KHONG-BAM.md", "khac/ngoai.md"):
        _sang_crlf(repo_cat / p)
    # Lẫn: một dòng CRLF giữa các dòng LF.
    (repo_cat / "src/m.py").write_bytes(b"A = 1\r\nB = 2\n")
    # Chưa theo dõi: KHÔNG thuộc test này (cổng đã bắt riêng file chưa theo dõi).
    (repo_cat / "config/moi.yaml").write_bytes(b"z: 3\r\n")

    _, hong = quet_cay_do(repo_cat)
    assert hong == ["config/a.yaml", "docs/decisions/DR-CO-BAM.md", "src/m.py"]


def test_co_rang_cay_lf_thi_sach(repo_cat: Path) -> None:
    da_quet, hong = quet_cay_do(repo_cat)
    assert hong == []
    assert set(da_quet) == {"config/a.yaml", "src/m.py", "docs/decisions/DR-CO-BAM.md"}
