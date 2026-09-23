"""🔒 TD-0369 (`DR-ZA-01` §4.3) — máy canh xuất xứ cổng: `provenance.git_sha` của bản ghi arm so với sha
cổng đang chứng nhận.

Phát hiện thật sinh ra việc này: cổng D4 ghi `d4_git_sha = 7c8c8f8` (mã ĐÃ có `L-Z3`) trong khi bốn bản
ghi arm mang `provenance.git_sha = 29f9f52` (mã ĐÃ ĐO, CHƯA có `L-Z3`) — cách nhau 9 commit, gồm `TD-0364`
đổi hành vi vào lệnh. `d4_han_che` không nói ra khoảng lệch, nên người đọc `runtime_state.json` tin nhầm
mốc chứng nhận là mốc đã đo.

Ba trạng thái, KHÔNG hai — bài học `MT-71` (phiên `69e2254e` nhắc): "không đọc được sha" rất dễ bị code
thành "không lệch ⇒ cho qua", đúng hình PASS RỖNG. Test này khoá cho cả ba, và khoá riêng thứ tự kiểm
(không-đọc-được đứng TRƯỚC lệch, để một bản ghi hỏng không bị đọc nhầm thành "khớp vì tình cờ bằng nhau").
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "entrypoints"))

from trial_ledger_audit import (  # noqa: E402
    XUAT_XU_KHONG_DOC_DUOC,
    XUAT_XU_KHOP,
    XUAT_XU_LECH,
    _bao_cao_xuat_xu,
    _sanh_xuat_xu,
    _xuat_xu_ban_ghi_arm,
)

SHA = "a" * 40
SHA_KHAC = "b" * 40


def _bg(arm: str, git_sha) -> dict:
    """Hình dạng tối thiểu của một bản ghi arm — chỉ hai khoá mà `_xuat_xu_ban_ghi_arm` đọc."""
    return {"arm": arm, "provenance": {"git_sha": git_sha}}


class TestTrichXuatGitSha:
    def test_doc_dung_moi_arm(self) -> None:
        ra = _xuat_xu_ban_ghi_arm([_bg("Z0-T1", SHA), _bg("Z0", SHA_KHAC)])
        assert ra == {"Z0-T1": SHA, "Z0": SHA_KHAC}

    @pytest.mark.parametrize("hong", [None, "", 123, [], {}])
    def test_gia_tri_hong_thanh_None(self, hong) -> None:
        assert _xuat_xu_ban_ghi_arm([_bg("Z0-T1", hong)]) == {"Z0-T1": None}

    def test_thieu_ca_khoa_provenance(self) -> None:
        assert _xuat_xu_ban_ghi_arm([{"arm": "Z0-T1"}]) == {"Z0-T1": None}


class TestSanhXuatXu:
    def test_mot_arm_khop(self) -> None:
        assert _sanh_xuat_xu({"Z0-T1": SHA}, sha_chung_nhan=SHA) == XUAT_XU_KHOP

    def test_nhieu_arm_deu_khop(self) -> None:
        assert _sanh_xuat_xu({"Z0-T1": SHA, "Z0": SHA}, sha_chung_nhan=SHA) == XUAT_XU_KHOP

    def test_mot_arm_lech(self) -> None:
        assert _sanh_xuat_xu({"Z0-T1": SHA_KHAC}, sha_chung_nhan=SHA) == XUAT_XU_LECH

    def test_mot_trong_nhieu_arm_lech_van_la_lech(self) -> None:
        assert _sanh_xuat_xu({"Z0-T1": SHA, "Z0": SHA_KHAC}, sha_chung_nhan=SHA) == XUAT_XU_LECH

    def test_rong_la_khong_doc_duoc(self) -> None:
        assert _sanh_xuat_xu({}, sha_chung_nhan=SHA) == XUAT_XU_KHONG_DOC_DUOC

    def test_mot_arm_thieu_sha_la_khong_doc_duoc(self) -> None:
        assert _sanh_xuat_xu({"Z0-T1": None}, sha_chung_nhan=SHA) == XUAT_XU_KHONG_DOC_DUOC

    def test_thieu_sha_UU_TIEN_hon_lech_khong_bi_doc_nham_thanh_khop_hay_lech(self) -> None:
        """🔴 Ca chống PASS RỖNG cốt lõi: MỘT arm thiếu sha, MỘT arm lệch — không đọc được phải THẮNG,
        không phải rơi vào nhánh 'lệch' (vẫn báo, nhưng sai loại) hay tệ hơn là 'khớp'."""
        ra = _sanh_xuat_xu({"Z0-T1": None, "Z0": SHA_KHAC}, sha_chung_nhan=SHA)
        assert ra == XUAT_XU_KHONG_DOC_DUOC

    def test_mot_arm_thieu_sha_giua_cac_arm_khop_van_khong_doc_duoc(self) -> None:
        """Đa số khớp không được che lấp thiểu số không đọc được."""
        ra = _sanh_xuat_xu({"Z0-T1": SHA, "Z0": SHA, "Z3": None}, sha_chung_nhan=SHA)
        assert ra == XUAT_XU_KHONG_DOC_DUOC


class TestBaoCaoXuatXu:
    def test_khop_khong_co_dau_do(self) -> None:
        bao_cao = _bao_cao_xuat_xu({"Z0-T1": SHA}, sha_chung_nhan=SHA)
        assert "KHỚP" in bao_cao and "🔴" not in bao_cao

    def test_lech_chi_liet_ke_arm_LECH_khong_liet_arm_khop(self) -> None:
        bao_cao = _bao_cao_xuat_xu({"Z0-T1": SHA_KHAC, "Z0": SHA}, sha_chung_nhan=SHA)
        assert "LỆCH" in bao_cao and "Z0-T1" in bao_cao
        # `Z0` khớp sha chứng nhận ⇒ không thuộc danh sách lệch — chỉ `Z0-T1` được nêu tên.
        vi_tri = {a: bao_cao.find(a) for a in ("Z0-T1", "Z0")}
        assert vi_tri["Z0-T1"] != -1
        # "Z0" là tiền tố con của "Z0-T1" nên không thể chỉ đếm `in`; đếm số LẦN "Z0" xuất hiện KHÔNG
        # phải là một phần của "Z0-T1".
        chi_z0_doc_lap = bao_cao.replace("Z0-T1", "").count("Z0")
        assert chi_z0_doc_lap == 0, bao_cao

    def test_khong_doc_duoc_neu_ten_arm_thieu(self) -> None:
        bao_cao = _bao_cao_xuat_xu({"Z0-T1": None, "Z0": SHA}, sha_chung_nhan=SHA)
        assert "KHÔNG ĐỌC ĐƯỢC" in bao_cao and "Z0-T1" in bao_cao

    def test_bao_cao_khong_bao_gio_rong(self) -> None:
        for theo_arm in ({}, {"Z0-T1": SHA}, {"Z0-T1": SHA_KHAC}, {"Z0-T1": None}):
            assert _bao_cao_xuat_xu(theo_arm, sha_chung_nhan=SHA).strip()
