"""L-Z40 🔴 CRITICAL — mọi bản ghi kết quả có đủ 7 khoá provenance (0d.5);
params_source == "yaml"; guard_passed == true. Thiếu → bản ghi KHÔNG HỢP
LỆ cho gate. Spec dòng 597-616, 681-683.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tool_d.measurement.gitinfo import GitInfoError
from tool_d.measurement.provenance import (
    REQUIRED_PROVENANCE_KEYS,
    Provenance,
    build_provenance,
    cache_key,
    validate_provenance,
)


def _ban_ghi_day_du() -> dict:
    return {
        "params_source": "yaml",
        "params_effective": {"zss_threshold": 0.55},
        "git_sha": "a" * 40,
        "reproducible_from_sha": True,
        "data_hashes": {"pool_100.csv": "deadbeef", "oi.parquet": "MISSING"},
        "cache_mode": "none",
        "guard_passed": True,
    }


class TestDuBayKhoa:
    """8 ca: 1 đủ + 7 thiếu-từng-khoá (spec đúng 7 khoá bắt buộc)."""

    def test_dung_bay_khoa_duoc_dinh_nghia(self) -> None:
        assert len(REQUIRED_PROVENANCE_KEYS) == 7

    def test_ban_ghi_day_du_thi_hop_le(self) -> None:
        assert validate_provenance(_ban_ghi_day_du()) == []

    @pytest.mark.parametrize("khoa_thieu", sorted(REQUIRED_PROVENANCE_KEYS))
    def test_thieu_tung_khoa_thi_khong_hop_le(self, khoa_thieu: str) -> None:
        record = _ban_ghi_day_du()
        del record[khoa_thieu]
        errors = validate_provenance(record)
        assert errors != []
        assert any(khoa_thieu in e for e in errors)


class TestNoiDung:
    def test_params_source_khac_yaml_thi_khong_hop_le(self) -> None:
        record = _ban_ghi_day_du()
        record["params_source"] = "params_file"  # guard đã chặn, dùng cờ vượt
        errors = validate_provenance(record)
        assert errors != []
        assert any("params_source" in e for e in errors)

    def test_guard_passed_false_thi_khong_hop_le(self) -> None:
        record = _ban_ghi_day_du()
        record["guard_passed"] = False
        errors = validate_provenance(record)
        assert any("guard_passed" in e for e in errors)

    def test_cache_mode_khac_none_thi_khong_hop_le(self) -> None:
        record = _ban_ghi_day_du()
        record["cache_mode"] = "day"
        errors = validate_provenance(record)
        assert any("cache_mode" in e for e in errors)

    def test_git_sha_UNKNOWN_thi_khong_hop_le(self) -> None:
        record = _ban_ghi_day_du()
        record["git_sha"] = "UNKNOWN"
        errors = validate_provenance(record)
        assert any("git_sha" in e for e in errors)

    def test_git_sha_rong_thi_khong_hop_le(self) -> None:
        record = _ban_ghi_day_du()
        record["git_sha"] = ""
        errors = validate_provenance(record)
        assert any("git_sha" in e for e in errors)


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.d"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=path, check=True)
    (path / "a.txt").write_text("a")
    subprocess.run(["git", "add", "."], cwd=path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=path, check=True)


class TestBuildProvenance:
    def test_dung_thanh_phan_va_hop_le(self, tmp_path: Path) -> None:
        # Repo git và thư mục dữ liệu tách biệt (giống thật: user_data/data
        # bị .gitignore, không nằm trong working tree được theo dõi) — để
        # test này chỉ kiểm working tree SẠCH, không lẫn với ca "có file dữ
        # liệu chưa track" (ca đó đúng ra PHẢI báo bẩn, xem test dưới).
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        _init_repo(repo_dir)
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        data_file = data_dir / "pool_100.csv"
        data_file.write_bytes(b"x")

        prov = build_provenance(
            params_source="yaml",
            params_effective={"zss_threshold": 0.55},
            repo_dir=repo_dir,
            data_files={"pool_100.csv": data_file, "oi.parquet": data_dir / "khong_co.parquet"},
            cache_mode="none",
            guard_passed=True,
        )
        assert prov.data_hashes["oi.parquet"] == "MISSING"
        assert prov.reproducible_from_sha is True
        assert validate_provenance(prov.to_dict()) == []

    def test_file_chua_track_trong_repo_cung_bao_ban(self, tmp_path: Path) -> None:
        # Ngược lại với ca trên: một file MỚI, CHƯA track, nằm ngay trong
        # working tree của repo — git status --porcelain coi đây là bẩn
        # (mặc định liệt kê untracked). reproducible_from_sha phải phản
        # ánh đúng, không được "khoan dung" cho untracked.
        _init_repo(tmp_path)
        (tmp_path / "chua_track.txt").write_text("moi")
        prov = build_provenance(
            params_source="yaml",
            params_effective={},
            repo_dir=tmp_path,
            data_files={},
            cache_mode="none",
            guard_passed=True,
        )
        assert prov.reproducible_from_sha is False

    def test_working_tree_ban_thi_reproducible_false(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        (tmp_path / "a.txt").write_text("da doi, chua commit")
        prov = build_provenance(
            params_source="yaml",
            params_effective={},
            repo_dir=tmp_path,
            data_files={},
            cache_mode="none",
            guard_passed=True,
        )
        assert prov.reproducible_from_sha is False
        # Vẫn hợp lệ cho gate (spec không cấm working tree bẩn, chỉ cấm
        # thiếu khoá / params_source sai / guard_passed sai) — nhưng cờ
        # reproducible_from_sha phải phản ánh đúng sự thật.
        assert validate_provenance(prov.to_dict()) == []

    def test_khong_phai_git_repo_thi_raise_khong_tra_UNKNOWN(self, tmp_path: Path) -> None:
        with pytest.raises(GitInfoError):
            build_provenance(
                params_source="yaml",
                params_effective={},
                repo_dir=tmp_path,
                data_files={},
                cache_mode="none",
                guard_passed=True,
            )


class TestCacheKey:
    def test_giong_input_ra_cung_khoa(self) -> None:
        p1 = Provenance(
            params_source="yaml",
            params_effective={"a": 1},
            git_sha="a" * 40,
            reproducible_from_sha=True,
            data_hashes={"f": "h"},
            cache_mode="none",
            guard_passed=True,
        )
        p2 = Provenance(**{**p1.to_dict(), "guard_passed": False})  # guard_passed không vào key
        assert cache_key(p1) == cache_key(p2)

    def test_khac_params_ra_khoa_khac(self) -> None:
        base = dict(
            params_source="yaml",
            git_sha="a" * 40,
            reproducible_from_sha=True,
            data_hashes={"f": "h"},
            cache_mode="none",
            guard_passed=True,
        )
        p1 = Provenance(params_effective={"a": 1}, **base)
        p2 = Provenance(params_effective={"a": 2}, **base)
        assert cache_key(p1) != cache_key(p2)
