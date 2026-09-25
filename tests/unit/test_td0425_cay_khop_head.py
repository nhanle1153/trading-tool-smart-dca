"""TD-0425 (`MT-86` phương án (a)) — bot dry-run / live D10 TỪ CHỐI khởi động khi cây làm việc lệch HEAD.

Sự cố 25/09/2026: `enable_short: true` còn trên đĩa, CHƯA commit, thì bot dry-run khởi động lại và chạy đường Short
~20 phút trước commit. Hai lớp test:

- `TestKiemCayKhopHead`: hàm thuần trên một repo git THẬT dựng trong `tmp_path` (không giả lập `git status` — thứ cần
  khoá chính là cách đọc đầu ra thật của git, gồm đổi tên, staged, chưa theo dõi).
- `TestChotNamTrongMain`: kiểm AST vị trí gọi trong `main()` của HAI bộ khởi động — chốt có mà không được gọi, hoặc gọi
  SAU `execvp`, là chốt không tồn tại (cùng khuôn `test_td0384_live_d10.py::TestThuTuChotTrongMain`).
"""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

import pytest

from tool_d.measurement.gitinfo import (
    THU_MUC_BOT_NAP,
    CayLechHeadError,
    GitInfoError,
    kiem_cay_khop_head,
)
from tool_d.ops.dry_run import EXIT_CAY_LECH_HEAD

REPO_ROOT = Path(__file__).resolve().parents[2]


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "-c", "commit.gpgsign=false", *args],
        cwd=repo, capture_output=True, text=True, check=True,
    ).stdout


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Repo git thật, một commit, có đủ ba vùng bot nạp + một vùng ngoài (`docs/`)."""
    r = tmp_path / "repo"
    for rel, noi_dung in {
        "config/tool_d_config.yaml": "tier_a:\n  enable_short: false\n",
        "src/tool_d/x.py": "A = 1\n",
        "user_data/strategies/ZoneAbsorption.py": "class ZoneAbsorption: ...\n",
        "docs/ghi-chu.md": "ghi chú\n",
    }.items():
        (r / rel).parent.mkdir(parents=True, exist_ok=True)
        (r / rel).write_text(noi_dung, encoding="utf-8")
    _git(r, "init", "-q")
    _git(r, "add", "-A")
    _git(r, "commit", "-q", "-m", "goc")
    return r


class TestKiemCayKhopHead:
    def test_cay_sach_tra_dung_sha_head(self, repo: Path) -> None:
        assert kiem_cay_khop_head(repo) == _git(repo, "rev-parse", "HEAD").strip()

    def test_ca_su_co_25_09_sua_yaml_chua_commit_thi_TU_CHOI(self, repo: Path) -> None:
        (repo / "config/tool_d_config.yaml").write_text("tier_a:\n  enable_short: true\n", encoding="utf-8")
        with pytest.raises(CayLechHeadError, match=r"config/tool_d_config\.yaml"):
            kiem_cay_khop_head(repo)

    @pytest.mark.parametrize("rel", ["src/tool_d/x.py", "user_data/strategies/ZoneAbsorption.py"])
    def test_sua_ma_hoac_chien_luoc_thi_TU_CHOI(self, repo: Path, rel: str) -> None:
        (repo / rel).write_text("# sửa dở\n", encoding="utf-8")
        with pytest.raises(CayLechHeadError, match=rel.replace(".", r"\.")):
            kiem_cay_khop_head(repo)

    def test_sua_da_staged_van_TU_CHOI(self, repo: Path) -> None:
        (repo / "src/tool_d/x.py").write_text("A = 2\n", encoding="utf-8")
        _git(repo, "add", "src/tool_d/x.py")
        with pytest.raises(CayLechHeadError):
            kiem_cay_khop_head(repo)

    def test_xoa_file_trong_vung_thi_TU_CHOI(self, repo: Path) -> None:
        (repo / "src/tool_d/x.py").unlink()
        with pytest.raises(CayLechHeadError, match=r"src/tool_d/x\.py"):
            kiem_cay_khop_head(repo)

    @pytest.mark.parametrize("rel", ["src/tool_d/moi.py", "user_data/strategies/Moi.py", "config/moi.yaml"])
    def test_file_CHUA_THEO_DOI_trong_vung_thi_TU_CHOI(self, repo: Path, rel: str) -> None:
        """Một `.py` mới chưa commit vẫn được import khi bot chạy — cùng loại với sửa file cũ."""
        (repo / rel).write_text("B = 1\n", encoding="utf-8")
        with pytest.raises(CayLechHeadError, match=rel.split("/")[-1].replace(".", r"\.")):
            kiem_cay_khop_head(repo)

    def test_doi_ten_tu_ngoai_vao_trong_vung_thi_TU_CHOI(self, repo: Path) -> None:
        _git(repo, "mv", "docs/ghi-chu.md", "src/tool_d/ghi_chu.py")
        with pytest.raises(CayLechHeadError):
            kiem_cay_khop_head(repo)

    def test_sua_NGOAI_vung_bot_nap_thi_KHONG_chan(self, repo: Path) -> None:
        """Tài liệu sửa dở (phiên khác đang viết `TASKS.md`/`docs/`) không đổi thứ bot chạy — chặn nó thì bot gần như
        không bao giờ lên được khi nhiều phiên chạy song song, và chốt đó sẽ bị gỡ."""
        (repo / "docs/ghi-chu.md").write_text("sửa\n", encoding="utf-8")
        (repo / "TASKS.md").write_text("mới\n", encoding="utf-8")
        (repo / "scratch_dl").mkdir()
        (repo / "scratch_dl/rac.bin").write_bytes(b"x")
        assert kiem_cay_khop_head(repo) == _git(repo, "rev-parse", "HEAD").strip()

    def test_khong_phai_repo_git_thi_FAIL_CLOSED(self, tmp_path: Path) -> None:
        """Không có `.git` (mount thiếu) ⇒ lỗi, KHÔNG coi là sạch."""
        with pytest.raises(GitInfoError):
            kiem_cay_khop_head(tmp_path)

    def test_loi_nhan_liet_ke_moi_file_lech(self, repo: Path) -> None:
        (repo / "config/tool_d_config.yaml").write_text("x: 1\n", encoding="utf-8")
        (repo / "src/tool_d/x.py").write_text("A = 3\n", encoding="utf-8")
        with pytest.raises(CayLechHeadError) as exc:
            kiem_cay_khop_head(repo)
        assert "config/tool_d_config.yaml" in str(exc.value) and "src/tool_d/x.py" in str(exc.value)
        assert "MT-86" in str(exc.value)

    def test_vung_bot_nap_dung_pham_vi_MT_86(self) -> None:
        assert THU_MUC_BOT_NAP == ("config/", "src/", "user_data/strategies/")

    def test_ma_thoat_khong_trung_ma_nao_khac_cua_du_an(self) -> None:
        """Log container phải đọc thẳng ra nguyên nhân từ mã thoát."""
        nguon = subprocess.run(
            ["git", "grep", "-h", "-E", r"^EXIT_[A-Z0-9_]+ *= *[0-9]+", "--", "src", "entrypoints"],
            cwd=REPO_ROOT, capture_output=True, text=True,
        ).stdout.splitlines()
        so = [int(d.split("=")[1].split("#")[0]) for d in nguon if not d.startswith("EXIT_CAY_LECH_HEAD")]
        assert EXIT_CAY_LECH_HEAD not in so


class TestChotNamTrongMain:
    @staticmethod
    def _goi_trong_main(nguon: Path) -> list[str]:
        cay = ast.parse(nguon.read_text(encoding="utf-8"))
        main = next(n for n in cay.body if isinstance(n, ast.FunctionDef) and n.name == "main")
        # Sắp theo (dòng, cột): `kiem_cay_khop_head(Path("."))` có hai lời gọi CÙNG dòng — lời gọi ngoài đứng trước.
        return [
            ten for _, _, ten in sorted(
                (n.lineno, n.col_offset, n.func.id if isinstance(n.func, ast.Name) else n.func.attr)
                for n in ast.walk(main)
                if isinstance(n, ast.Call) and isinstance(n.func, (ast.Name, ast.Attribute))
            )
        ]

    def test_dry_run_kiem_cay_la_VIEC_DAU_TIEN(self) -> None:
        goi = self._goi_trong_main(REPO_ROOT / "src/tool_d/ops/dry_run.py")
        assert goi[0] == "kiem_cay_khop_head", goi[:3]
        assert goi.index("kiem_cay_khop_head") < goi.index("execvp")

    def test_live_d10_kiem_cay_sau_credential_TRUOC_moi_loi_goi_mang_va_exec(self) -> None:
        goi = self._goi_trong_main(REPO_ROOT / "src/tool_d/ops/live_d10.py")
        i = goi.index("kiem_cay_khop_head")
        assert goi.index("validate_credentials_for_live") < i
        for sau in ("kiem_truoc_khi_bat", "get_exchange_info", "kiem_ro_da_commit", "dung_cau_hinh_live_d10", "execvp"):
            assert goi.index(sau) > i, f"{sau} chạy TRƯỚC kiem_cay_khop_head"
