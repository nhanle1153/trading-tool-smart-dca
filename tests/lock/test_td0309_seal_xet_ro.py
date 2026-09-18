"""TD-0309 (`MT-60`, `DR-LOCKBOX-01`) — seal phải KHAI rổ, và khai phải đúng.

Ca bắt đúng `MT-60` dùng DỮ LIỆU THẬT của repo (đọc, không sửa): tên 510 file của
`lockbox/lockbox_seal_1.json` + `config/pool_t2.yaml` (86 mã). Seal 1 băm 102 mã của `pool.yaml` —
khai nó là rổ `T2` thì phép kiểm PHẢI bắt ra lệch. `verify_all_seals()` (chỉ băm) không bắt được, và
test khoá `L-Z14` của nó giữ nguyên nghĩa.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest
import yaml

from tool_d.data.pool_t1_du_lieu import SAU_LOAI_FILE, ten_file
from tool_d.lockbox.ro_seal import (
    KHAI_DUNG,
    KHAI_SAI,
    KHONG_KHAI,
    doc_mien_khai_pool,
    kiem_pool_seal,
    verify_lockbox,
)
from tool_d.lockbox.seal import Seal, build_seal, seal_hieu_luc_doan_1, write_seal

REPO = Path(__file__).resolve().parents[2]
POOL_T2 = REPO / "config" / "pool_t2.yaml"
SEAL_1 = REPO / "lockbox" / "lockbox_seal_1.json"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _trading_t2() -> list[str]:
    return list(yaml.safe_load(POOL_T2.read_text(encoding="utf-8"))["trading"])


def _pool_t2() -> dict:
    return {"moc": "t2", "file": "config/pool_t2.yaml", "sha256": _sha(POOL_T2), "trading": _trading_t2()}


def _du_file(trading: list[str]) -> dict[str, str]:
    return {ten_file(s, lf): "x" * 64 for s in trading for lf in SAU_LOAI_FILE}


class TestKiemPoolSeal:
    def test_MT60_seal_1_that_khai_ro_T2_thi_KHAI_SAI(self) -> None:
        """🔴 Ca bắt đúng MT-60: 510 file của seal 1 thật (102 mã pool.yaml) ≠ rổ T2 (86 mã)."""
        seal = {"data_hashes": json.loads(SEAL_1.read_text(encoding="utf-8"))["data_hashes"], "pool": _pool_t2()}
        tt, loi = kiem_pool_seal(seal, repo_dir=REPO)
        assert tt == KHAI_SAI
        assert any("KHÔNG thuộc rổ khai" in x for x in loi)
        assert any("KHÔNG có dữ liệu" in x for x in loi)

    def test_seal_dung_ro_T2_du_6_loai_thi_KHAI_DUNG(self) -> None:
        seal = {"data_hashes": _du_file(_trading_t2()), "pool": _pool_t2()}
        assert kiem_pool_seal(seal, repo_dir=REPO) == (KHAI_DUNG, [])

    def test_thieu_file_5m_cua_mot_ma_thi_KHAI_SAI(self) -> None:
        """Q6: lockbox phải có 5m như D5/D9 — seal 5 loại (như seal 1) không đủ."""
        dh = _du_file(_trading_t2())
        del dh[ten_file(_trading_t2()[0], next(lf for lf in SAU_LOAI_FILE if lf.khung == "5m"))]
        tt, loi = kiem_pool_seal({"data_hashes": dh, "pool": _pool_t2()}, repo_dir=REPO)
        assert tt == KHAI_SAI and any("thiếu 1 file bắt buộc" in x for x in loi)

    def test_ro_bi_sua_sau_khi_niem_phong_thi_KHAI_SAI(self, tmp_path: Path) -> None:
        (tmp_path / "config").mkdir()
        shutil.copy(POOL_T2, tmp_path / "config" / "pool_t2.yaml")
        pool = _pool_t2()
        (tmp_path / "config" / "pool_t2.yaml").write_text(POOL_T2.read_text(encoding="utf-8") + "# sua\n", encoding="utf-8")
        tt, loi = kiem_pool_seal({"data_hashes": _du_file(_trading_t2()), "pool": pool}, repo_dir=tmp_path)
        assert tt == KHAI_SAI and any("sha256 KHÁC" in x for x in loi)

    def test_seal_khong_khoa_pool_la_KHONG_KHAI_khong_phai_dat(self) -> None:
        assert kiem_pool_seal({"data_hashes": {"a": "b"}}) == (KHONG_KHAI, [])


class TestVerifyLockbox:
    def _lockbox(self, tmp_path: Path, ten: str) -> tuple[Path, Path]:
        data = tmp_path / "data"
        data.mkdir(exist_ok=True)
        (data / "a.csv").write_text("aaa", encoding="utf-8")
        lb = tmp_path / "lockbox"
        write_seal(build_seal(segment=1, sealed_at="t", date_range={}, data_files={"a.csv": data / "a.csv"}), lb / ten)
        return lb, data

    def test_khong_khai_va_khong_duoc_mien_thi_LOI(self, tmp_path: Path) -> None:
        lb, data = self._lockbox(tmp_path, "lockbox_seal_2.json")
        kq = verify_lockbox(lb, data, repo_dir=tmp_path, mien_khai_pool=frozenset({"lockbox_seal_1.json"}))
        assert not kq.dat and kq.loi_bam == () and len(kq.loi_ro) == 1

    def test_khong_khai_nhung_duoc_mien_thi_dat_VA_hien_ghi_chu_rieng(self, tmp_path: Path) -> None:
        """Miễn ≠ đạt: không lỗi, nhưng phải HIỆN ra — không lặng lẽ thành PASS."""
        lb, data = self._lockbox(tmp_path, "lockbox_seal_1.json")
        kq = verify_lockbox(lb, data, repo_dir=tmp_path, mien_khai_pool=frozenset({"lockbox_seal_1.json"}))
        assert kq.dat and len(kq.ghi_chu_mien) == 1 and "KHÔNG phải 'đạt'" in kq.ghi_chu_mien[0]

    def test_cau_hinh_that_mien_dung_seal_1_va_chi_seal_1(self) -> None:
        assert doc_mien_khai_pool(REPO / "config" / "tool_d_config.yaml") == frozenset({"lockbox_seal_1.json"})

    def test_thieu_khoa_cau_hinh_thi_KHONG_mien_gi(self, tmp_path: Path) -> None:
        """Fail-closed: không có danh sách miễn thì mọi seal không khai rổ đều là lỗi."""
        cfg = yaml.safe_load((REPO / "config" / "tool_d_config.yaml").read_text(encoding="utf-8"))
        cfg["tier_c"].pop("lockbox")
        p = tmp_path / "cfg.yaml"
        p.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
        assert doc_mien_khai_pool(p) == frozenset()


class TestSealHieuLucDoan1:
    def _ghi(self, lb: Path, ten: str, thay_the: str | None) -> None:
        write_seal(Seal(segment=1, sealed_at="t", date_range={}, data_hashes={"a": "b"}, thay_the=thay_the), lb / ten)

    def test_chi_co_seal_1_thi_tra_seal_1(self, tmp_path: Path) -> None:
        self._ghi(tmp_path, "lockbox_seal_1.json", None)
        assert seal_hieu_luc_doan_1(tmp_path) == tmp_path / "lockbox_seal_1.json"

    def test_co_ban_cap_lai_thi_seal_1_KHONG_BAO_GIO_duoc_tra(self, tmp_path: Path) -> None:
        self._ghi(tmp_path, "lockbox_seal_1.json", None)
        self._ghi(tmp_path, "lockbox_seal_1_cap_lai.json", "lockbox_seal_1.json")
        assert seal_hieu_luc_doan_1(tmp_path) == tmp_path / "lockbox_seal_1_cap_lai.json"

    def test_hai_ban_cap_lai_thi_TU_CHOI(self, tmp_path: Path) -> None:
        self._ghi(tmp_path, "lockbox_seal_1.json", None)
        self._ghi(tmp_path, "lockbox_seal_1_cap_lai.json", "lockbox_seal_1.json")
        self._ghi(tmp_path, "lockbox_seal_1_cap_lai_b.json", "lockbox_seal_1.json")
        with pytest.raises(ValueError, match="tối đa MỘT"):
            seal_hieu_luc_doan_1(tmp_path)

    def test_seal_cu_to_dict_khong_doi(self) -> None:
        """Seal không khai rổ/không cấp lại ra ĐÚNG dict như trước TD-0309 — seal 1 và test cũ nguyên vẹn."""
        d = Seal(segment=1, sealed_at="t", date_range={}, data_hashes={"a": "b"}).to_dict()
        assert set(d) == {"segment", "sealed_at", "date_range", "data_hashes"}
