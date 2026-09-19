"""TD-0331 (OQ-15) — phép kiểm backlog `tool_d.ledger.backlog_check` + cờ `--kiem-backlog` của E6.

Cái đáng canh nhất không phải hàm thuần, mà là **nó có bắt được sự cố thật đã sinh ra nó
không**. Bài học `TD-0170`/`08/09` của dự án: một lớp canh chỉ được nuôi bằng mẫu dựng tay có
thể xanh mãi mà chưa từng nhìn thấy ca sai đi qua ĐƯỜNG THẬT. Nên ngoài các ca dựng tay, file này
chạy trên ẢNH CHỤP LỊCH SỬ THẬT: `TASKS.md` tại commit `844468a` (lúc `TD-0319`/`TD-0320` còn 🔒
dù code đã commit, và `TD-0184` ghi 🔓 dù ghi chú là ⏸) cùng `git log` thật.

Nghiệm thu răng của chính file này bằng công cụ `TD-0329`
(`tests/tools/specs/td0331_backlog_check.json`), chạy trong `test_td0329_mutate_in_memory.py`.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tool_d.ledger import backlog_check as B

REPO_ROOT = Path(__file__).resolve().parents[2]
COMMIT_ANH_CHUP = "844468a"  # TASKS.md lúc TD-0319/TD-0320 còn 🔒 và TD-0184 ghi 🔓 dù ⏸


def _bang(*dong: str) -> str:
    """Bảng backlog tối thiểu, đúng hình tiêu đề thật (ô 1 'Mã việc', ô 3 'TT')."""
    return "\n".join(
        ["| Mã việc | Nội dung | TT | Phụ thuộc | Tiêu chí XONG |", "|---|---|---|---|---|", *dong]
    ) + "\n"


class TestTachO:
    def test_nam_o_co_ban(self) -> None:
        assert B.tach_o("| TD-0001 | việc | 🔓 | — | xong |") == ["TD-0001", "việc", "🔓", "—", "xong"]

    def test_dau_gach_dung_trong_ngoac_nguoc_khong_tach(self) -> None:
        o = B.tach_o("| TD-0001 | chạy `a | b` rồi | 🔒 | x | y |")
        assert o == ["TD-0001", "chạy `a | b` rồi", "🔒", "x", "y"]

    def test_dau_gach_da_escape_khong_tach(self) -> None:
        assert B.tach_o("| TD-0001 | a \\| b | 🔓 | x | y |")[1] == "a | b"

    def test_khong_co_dau_gach_cuoi_van_lay_o_cuoi(self) -> None:
        assert B.tach_o("| a | b | c")[-1] == "c"


class TestDocBacklog:
    def test_chi_doc_bang_backlog_khong_doc_bang_changelog(self) -> None:
        text = (
            "| Mã | Loại | Nội dung cũ | Nội dung mới | Lý do | Ngày |\n|---|---|---|---|---|---|\n"
            "| TD-0006 | ♻️ Sửa đổi | 🔒 | x | y | 01/01 |\n\n"
            + _bang("| TD-0001 | việc | 🔓 | — | xong |")
        )
        assert [d.ma for d in B.doc_backlog(text)] == ["TD-0001"]

    def test_ghi_dung_so_dong_va_o_khac(self) -> None:
        text = "tiêu đề\n\n" + _bang("| TD-0007 | việc | 🔒 | TD-0001 | xong |")
        (d,) = B.doc_backlog(text)
        assert d.so_dong == 5 and d.trang_thai == "🔒"
        assert d.o_khac == ("việc", "TD-0001", "xong")

    def test_dong_khong_phai_ma_viec_bi_bo_qua(self) -> None:
        text = _bang("| TD-0001 · TD-0002 | gộp | 🔓 | — | — |", "| ghi chú | x | 🔓 | — | — |")
        assert B.doc_backlog(text) == []


COMMITS = [
    ("aaa1111", "TD-0007: dựng module"),
    ("bbb2222", "TASKS.md: khoa TD-0007 (module)"),
    ("ccc3333", "TD-00071: việc khác hẳn"),
]


class TestLoai1KhoaCoCommit:
    def _van_de(self, dong: str, commits=COMMITS):
        return B.tim_van_de(B.doc_backlog(_bang(dong)), commits)

    def test_khoa_co_commit_ma_viec_thi_bao(self) -> None:
        (v,) = self._van_de("| TD-0007 | m | 🔒 | — | x |")
        assert v.loai == B.LOAI_KHOA_CO_COMMIT and v.ma == "TD-0007"
        assert "aaa1111" in v.mo_ta and "bbb2222" not in v.mo_ta

    def test_commit_khoa_va_hoan_tat_khong_tinh(self) -> None:
        """`TASKS.md: khoa TD-0007` KHÔNG bắt đầu bằng mã việc ⇒ không bị coi là commit code."""
        assert self._van_de("| TD-0007 | m | 🔒 | — | x |", [("bbb2222", "TASKS.md: khoa TD-0007 (module)")]) == []

    def test_ranh_gioi_ma_khong_khop_ma_dai_hon(self) -> None:
        assert self._van_de("| TD-0007 | m | 🔒 | — | x |", [("ccc3333", "TD-00071: việc khác")]) == []

    def test_khoa_khong_co_commit_thi_khong_bao(self) -> None:
        assert self._van_de("| TD-0007 | m | 🔒 | — | x |", [("z", "TD-0009: khác")]) == []

    def test_da_xong_hoac_dang_mo_thi_khong_bao(self) -> None:
        assert self._van_de("| TD-0007 | m | ✅ `aaa1111` | — | x |") == []
        assert self._van_de("| TD-0007 | m | 🔓 | — | x |") == []

    def test_khong_doc_duoc_git_thi_bo_loai_1_khong_no(self) -> None:
        assert self._van_de("| TD-0007 | m | 🔒 | — | x |", None) == []


class TestLoai2TrangThaiLan:
    def _loai(self, o: str) -> list[str]:
        return [v.loai for v in B.tim_van_de(B.doc_backlog(_bang(f"| TD-0007 | m | {o} | — | x |")), [])]

    def test_hai_ky_hieu_thi_bao(self) -> None:
        assert self._loai("🔓 ⏸") == [B.LOAI_TRANG_THAI_LAN]

    def test_mot_ky_hieu_hoac_ky_hieu_kem_hash_thi_khong(self) -> None:
        assert self._loai("🔓") == [] and self._loai("⏸") == [] and self._loai("✅ `ac04799`") == []


class TestLoai3NghiLechTamDung:
    def _loai(self, tt: str, ghi_chu: str) -> list[str]:
        return [v.loai for v in B.tim_van_de(B.doc_backlog(_bang(f"| TD-0007 | m | {tt} | — | {ghi_chu} |")), [])]

    def test_mo_nhung_ghi_chu_noi_tam_dung_thi_nghi(self) -> None:
        assert self._loai("🔓", "… ⏸ TẠM DỪNG 17/09/2026 theo DR-IQ-01 §1") == [B.LOAI_NGHI_LECH_TAM_DUNG]
        assert self._loai("🔓", "… ⏸ **TẠM DỪNG** …") == [B.LOAI_NGHI_LECH_TAM_DUNG]

    def test_trang_thai_da_co_dau_thi_khong_nghi(self) -> None:
        assert self._loai("⏸", "⏸ TẠM DỪNG") == []
        assert self._loai("✅", "⏸ TẠM DỪNG") == []
        assert self._loai("❌", "⏸ TẠM DỪNG") == []

    def test_khong_co_cum_thi_khong_nghi(self) -> None:
        assert self._loai("🔓", "một ghi chú bình thường, có ⏸ nhưng không phải cụm đó") == []


class TestBaoCao:
    def test_khong_canh_bao_thi_ma_0(self) -> None:
        ma, text = B.bao_cao(tasks_text=_bang("| TD-0007 | m | 🔓 | — | x |"), tieu_de_commit=[])
        assert ma == 0 and "0 cảnh báo" in text

    def test_co_canh_bao_thi_ma_1_va_noi_ro_chi_bao(self) -> None:
        ma, text = B.bao_cao(tasks_text=_bang("| TD-0007 | m | 🔒 | — | x |"), tieu_de_commit=COMMITS)
        assert ma == 1
        assert "TD-0007" in text and "chỉ báo, không chặn" in text and "BÌNH THƯỜNG" in text

    def test_khong_co_git_thi_noi_chua_do_duoc_va_van_bao_loai_2_3(self, tmp_path) -> None:
        text_tasks = _bang("| TD-0007 | m | 🔓 ⏸ | — | x |", "| TD-0008 | m | 🔒 | — | x |")
        ma, text = B.bao_cao(tasks_text=text_tasks, root=tmp_path)  # tmp_path KHÔNG phải repo git
        assert "CHƯA ĐO ĐƯỢC" in text
        assert ma == 1 and "TD-0007" in text  # loại 2 vẫn báo
        assert "TD-0008" not in text  # loại 1 không thể báo mà không có git — và không được giả vờ đã kiểm


# ── ẢNH CHỤP LỊCH SỬ THẬT ────────────────────────────────────────────────────────────


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-c", "safe.directory=*", "-C", str(REPO_ROOT), *args],
        capture_output=True, text=True, encoding="utf-8",
    )


@pytest.fixture(scope="module")
def anh_chup_that():
    if _git("cat-file", "-e", f"{COMMIT_ANH_CHUP}^{{commit}}").returncode != 0:
        pytest.skip(f"commit {COMMIT_ANH_CHUP} không có trong bản clone này (clone nông?)")
    kq = _git("show", f"{COMMIT_ANH_CHUP}:TASKS.md")
    assert kq.returncode == 0, kq.stderr
    van_de = B.tim_van_de(B.doc_backlog(kq.stdout), B.doc_tieu_de_commit(REPO_ROOT))
    return {(v.loai, v.ma) for v in van_de}


class TestAnhChupLichSuThat:
    """Ba ca thật sinh ra `OQ-15`. Nếu phép kiểm không bắt được chúng thì nó chưa từng làm việc
    của mình — dù mọi ca dựng tay ở trên đều xanh."""

    def test_bat_hai_khoa_quen_dong(self, anh_chup_that) -> None:
        assert (B.LOAI_KHOA_CO_COMMIT, "TD-0319") in anh_chup_that
        assert (B.LOAI_KHOA_CO_COMMIT, "TD-0320") in anh_chup_that

    def test_bat_trang_thai_lech_cua_TD_0184(self, anh_chup_that) -> None:
        assert (B.LOAI_NGHI_LECH_TAM_DUNG, "TD-0184") in anh_chup_that

    def test_bat_hai_o_trang_thai_lan(self, anh_chup_that) -> None:
        assert (B.LOAI_TRANG_THAI_LAN, "TD-0308") in anh_chup_that
        assert (B.LOAI_TRANG_THAI_LAN, "TD-0310") in anh_chup_that

    def test_khong_bao_nham_viec_da_xong_cung_chuoi(self, anh_chup_that) -> None:
        """`TD-0321`/`TD-0322` ✅ tại ảnh chụp và cũng có commit mã việc — không được báo."""
        ma_bi_bao = {ma for _, ma in anh_chup_that}
        assert "TD-0321" not in ma_bi_bao and "TD-0322" not in ma_bi_bao


# ── E6: cờ nối đúng, không đổi luồng audit, không ghi file ──────────────────────────────


class TestCoE6:
    def test_parser_co_co_va_ma_thoat_khong_dung_hang_khac(self) -> None:
        sys.path.insert(0, str(REPO_ROOT))
        import entrypoints.trial_ledger_audit as e6

        assert e6.build_parser().parse_args(["--kiem-backlog"]).kiem_backlog is True
        assert e6.build_parser().parse_args([]).kiem_backlog is False
        ma = [v for k, v in vars(e6).items() if k.startswith("EXIT_") and isinstance(v, int)]
        assert len(ma) == len(set(ma)), "hai hằng EXIT_* trùng số — mã thoát mất khả năng phân biệt"
        assert e6.EXIT_BACKLOG_CO_CANH_BAO == 97

    def test_chay_that_qua_E6_in_bao_cao_va_khong_ghi_file(self) -> None:
        tasks = REPO_ROOT / "TASKS.md"
        truoc = hashlib.sha256(tasks.read_bytes()).hexdigest()
        kq = subprocess.run(
            [sys.executable, "entrypoints/trial_ledger_audit.py", "--kiem-backlog"],
            capture_output=True, text=True, encoding="utf-8", cwd=str(REPO_ROOT),
            env={**os.environ, "PYTHONPATH": "src"},
        )
        assert kq.returncode in (0, 97), kq.stdout + kq.stderr
        assert "backlog: đọc" in kq.stdout, kq.stdout + kq.stderr
        assert hashlib.sha256(tasks.read_bytes()).hexdigest() == truoc, "cờ báo cáo đã GHI vào TASKS.md"
