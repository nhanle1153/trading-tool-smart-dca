"""TD-0316 (`DR-LOCKBOX-02`) — H17 ở service CHE lockbox.

Ba phép chạy được ở service pipeline (dữ liệu lockbox bị che có chủ đích): cách ly còn hiệu lực,
file seal không bị sửa, sổ truy cập. Phép seal dùng một repo git TẠM THẬT — không giả lập git,
vì thứ cần khoá chính là hành vi của git (theo dõi / sạch / số lần commit).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from tool_d.lockbox.h17 import (
    EXIT_LOCKBOX_CACH_LY_VO,
    KetQuaH17,
    in_va_ma_thoat,
    kiem_cach_ly,
    kiem_seal_khong_bi_sua,
    kiem_so_truy_cap,
)

TEN = "A_USDT_USDT-1h-futures.feather"


def _seal(lockbox: Path, ten_file: str = "lockbox_seal_1.json", data: dict | None = None) -> Path:
    lockbox.mkdir(parents=True, exist_ok=True)
    sp = lockbox / ten_file
    sp.write_text(json.dumps({"segment": 1, "data_hashes": data or {TEN: "a" * 64}}), encoding="utf-8")
    return sp


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "-c", "commit.gpgsign=false", *args],
        cwd=repo, check=True, capture_output=True,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "core.autocrlf", "false")
    return tmp_path


class TestCachLy:
    def test_du_lieu_bi_che_thi_dat(self, tmp_path: Path) -> None:
        _seal(tmp_path / "lockbox")
        assert kiem_cach_ly(tmp_path / "lockbox", tmp_path / "lockbox" / "data" / "futures") == []

    def test_doc_duoc_file_seal_liet_ke_thi_VO(self, tmp_path: Path) -> None:
        _seal(tmp_path / "lockbox")
        d = tmp_path / "lockbox" / "data" / "futures"
        d.mkdir(parents=True)
        (d / TEN).write_bytes(b"x")
        loi = kiem_cach_ly(tmp_path / "lockbox", d)
        assert len(loi) == 1 and TEN in loi[0]

    def test_file_KHONG_nam_trong_seal_cung_la_vo(self, tmp_path: Path) -> None:
        """Quét thư mục, không chỉ thử tên trong seal — dữ liệu chưa niêm phong lọt vào cũng là vỡ."""
        _seal(tmp_path / "lockbox")
        d = tmp_path / "lockbox" / "data" / "futures"
        d.mkdir(parents=True)
        (d / "LA_USDT_USDT-5m-futures.feather").write_bytes(b"x")
        assert kiem_cach_ly(tmp_path / "lockbox", d)

    def test_khong_seal_nao_va_khong_du_lieu_thi_dat(self, tmp_path: Path) -> None:
        assert kiem_cach_ly(tmp_path / "lockbox", tmp_path / "lockbox" / "data" / "futures") == []


class TestSealKhongBiSua:
    def test_commit_dung_mot_lan_va_sach_thi_dat(self, repo: Path) -> None:
        _seal(repo / "lockbox")
        _git(repo, "add", "lockbox")
        _git(repo, "commit", "-q", "-m", "seal")
        assert kiem_seal_khong_bi_sua(repo, repo / "lockbox") == []

    def test_chua_commit_thi_loi(self, repo: Path) -> None:
        _seal(repo / "lockbox")
        loi = kiem_seal_khong_bi_sua(repo, repo / "lockbox")
        assert len(loi) == 1 and "chưa commit" in loi[0]

    def test_sua_sau_khi_commit_thi_loi(self, repo: Path) -> None:
        sp = _seal(repo / "lockbox")
        _git(repo, "add", "lockbox")
        _git(repo, "commit", "-q", "-m", "seal")
        sp.write_text(sp.read_text(encoding="utf-8") + " ", encoding="utf-8")
        assert kiem_seal_khong_bi_sua(repo, repo / "lockbox")

    def test_commit_lai_lan_hai_thi_loi_du_cay_sach(self, repo: Path) -> None:
        """Sửa rồi commit lại cho SẠCH vẫn phải bị bắt — 'commit, không sửa' (DR-D0PRE-07 §6)."""
        sp = _seal(repo / "lockbox")
        _git(repo, "add", "lockbox")
        _git(repo, "commit", "-q", "-m", "seal")
        sp.write_text(json.dumps({"segment": 1, "data_hashes": {TEN: "b" * 64}}), encoding="utf-8")
        _git(repo, "commit", "-q", "-am", "sua seal")
        loi = kiem_seal_khong_bi_sua(repo, repo / "lockbox")
        assert len(loi) == 1 and "2 lần" in loi[0]

    def test_khong_doc_duoc_git_thi_loi_KHONG_bo_qua(self, tmp_path: Path) -> None:
        """Không phải repo git ⇒ không chứng minh được gì ⇒ lỗi (fail-closed), không coi là sạch."""
        _seal(tmp_path / "lockbox")
        assert kiem_seal_khong_bi_sua(tmp_path, tmp_path / "lockbox")


class TestSoTruyCap:
    def test_khong_co_so_thi_rong(self, tmp_path: Path) -> None:
        assert kiem_so_truy_cap(tmp_path, tmp_path / "rt.json") == []

    def test_co_ban_ghi_truoc_d9_5_thi_loi(self, tmp_path: Path) -> None:
        (tmp_path / "lockbox_access.log").write_text(json.dumps({"seal_path": "x"}) + "\n", encoding="utf-8")
        assert kiem_so_truy_cap(tmp_path, tmp_path / "rt.json")


class TestMaThoat:
    def test_cach_ly_vo_la_ma_rieng_108(self) -> None:
        kq = KetQuaH17(cach_ly_vo=("x",), seal_bi_sua=("y",), so_truy_cap=())
        assert in_va_ma_thoat(kq, ma_that_bai=89) == EXIT_LOCKBOX_CACH_LY_VO == 108

    def test_seal_bi_sua_dung_ma_that_bai(self) -> None:
        kq = KetQuaH17(cach_ly_vo=(), seal_bi_sua=("y",), so_truy_cap=())
        assert in_va_ma_thoat(kq, ma_that_bai=89) == 89

    def test_dat_thi_None(self) -> None:
        assert in_va_ma_thoat(KetQuaH17((), (), ()), ma_that_bai=89) is None
