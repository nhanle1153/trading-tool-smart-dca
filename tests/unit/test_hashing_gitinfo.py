"""TD-0011 — hashing.sha256_of() và gitinfo.get_git_info().

Không gắn với một L-Zxx cụ thể — đây là hạ tầng cho khối xuất xứ (0d.5),
được test khoá thật sự ở L-Z40 (tests/lock/test_lz40_provenance.py).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tool_d.measurement.gitinfo import GitInfoError, get_git_info
from tool_d.measurement.hashing import MISSING, hash_many, sha256_of


class TestSha256Of:
    def test_file_ton_tai_ra_dung_hash(self, tmp_path: Path) -> None:
        f = tmp_path / "data.csv"
        f.write_bytes(b"hello tool d")
        import hashlib

        expected = hashlib.sha256(b"hello tool d").hexdigest()
        assert sha256_of(f) == expected

    def test_file_khong_ton_tai_ra_MISSING(self, tmp_path: Path) -> None:
        assert sha256_of(tmp_path / "khong_ton_tai.parquet") == MISSING

    def test_thu_muc_khong_phai_file_ra_MISSING(self, tmp_path: Path) -> None:
        d = tmp_path / "la_thu_muc"
        d.mkdir()
        assert sha256_of(d) == MISSING

    def test_khong_bao_gio_tra_none_hay_chuoi_rong(self, tmp_path: Path) -> None:
        result = sha256_of(tmp_path / "mat_tich.bin")
        assert result is not None
        assert result != ""
        assert result == MISSING


class TestHashMany:
    def test_tron_file_co_va_thieu(self, tmp_path: Path) -> None:
        f = tmp_path / "pool_100.csv"
        f.write_bytes(b"x")
        result = hash_many({"pool_100.csv": f, "oi.parquet": tmp_path / "khong_co.parquet"})
        assert result["oi.parquet"] == MISSING
        assert result["pool_100.csv"] != MISSING


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.d"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=path, check=True)
    (path / "a.txt").write_text("a")
    subprocess.run(["git", "add", "."], cwd=path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=path, check=True)


class TestGetGitInfo:
    def test_repo_sach(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        info = get_git_info(tmp_path)
        assert len(info.sha) == 40
        assert info.is_clean is True

    def test_repo_ban_bao_khong_sach(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        (tmp_path / "a.txt").write_text("da doi")
        info = get_git_info(tmp_path)
        assert info.is_clean is False

    def test_thu_muc_khong_phai_git_repo_thi_raise(self, tmp_path: Path) -> None:
        with pytest.raises(GitInfoError):
            get_git_info(tmp_path)

    def test_khong_bao_gio_tra_sha_rong(self, tmp_path: Path) -> None:
        # Không có cách hợp lệ nào để get_git_info trả về GitInfo với sha
        # rỗng — hoặc raise, hoặc trả sha 40 ký tự. Test này canh bất biến
        # đó bằng cách chỉ chấp nhận hai kết cục.
        try:
            info = get_git_info(tmp_path)
        except GitInfoError:
            return
        assert info.sha != ""
