"""TD-0431 — loại 4 của phép kiểm backlog: dòng 🔒/🔓 mà chính dòng đã ghi dấu hoàn tất kèm ngày.

Sự cố sinh ra loại này: `TD-0386` còn 🔒 từ 24/09 tới 26/09/2026 dù commit hoàn tất `ff42b18` đã ghi
`✅ **24/09/2026:**` vào ô nghiệm thu. `--kiem-backlog` (`TD-0331`) CÓ báo — nhưng ở loại 1, cùng
hình với `TD-0405`/`TD-0427` là việc nhiều chặng đang dở hợp lệ. Nên ngoài ca dựng tay, file này
chạy trên ẢNH CHỤP LỊCH SỬ THẬT: `TASKS.md` tại cha của `37f2fd1` (commit sửa `TD-0386`).

🔴 Không có test nào đòi `TASKS.md` HIỆN TẠI sạch loại 4: đó sẽ là test canh chặn suite, trái
quyết định `OQ-15` (backlog chỉ báo, không chặn). Kiểm file hiện tại là việc của `--kiem-backlog`.

Nghiệm thu răng bằng công cụ `TD-0329` (`tests/tools/specs/td0431_khoa_da_ghi_xong.json`).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tool_d.ledger import backlog_check as B

REPO_ROOT = Path(__file__).resolve().parents[2]
COMMIT_SUA = "37f2fd1"  # TASKS.md: TD-0386 lật 🔒 → ✅; cha của nó là ảnh chụp lúc còn lỗi


def _bang(*dong: str) -> str:
    return "\n".join(
        ["| Mã việc | Nội dung | TT | Phụ thuộc | Tiêu chí XONG |", "|---|---|---|---|---|", *dong]
    ) + "\n"


def _loai4(tt: str, ten: str = "m", phu_thuoc: str = "—", tieu_chi: str = "x") -> list[str]:
    dong = B.doc_backlog(_bang(f"| TD-0007 | {ten} | {tt} | {phu_thuoc} | {tieu_chi} |"))
    return [v.ma for v in B.tim_van_de(dong, []) if v.loai == B.LOAI_KHOA_DA_GHI_XONG]


XONG = "full suite 0 đỏ — ✅ **24/09/2026:** DR `fe1da36`, config `3d4cdfd`"


class TestLoai4:
    def test_khoa_ma_da_ghi_xong_thi_bao(self) -> None:
        assert _loai4("🔒", tieu_chi=XONG) == ["TD-0007"]

    def test_mo_ma_da_ghi_xong_cung_bao(self) -> None:
        assert _loai4("🔓", tieu_chi=XONG) == ["TD-0007"]

    def test_dang_co_chu_truoc_ngay_van_bat(self) -> None:
        assert _loai4("🔒", tieu_chi="… · ✅ **Xong 19/09/2026 (`f9554cb`).** Chạy thật") == ["TD-0007"]

    def test_dau_xong_o_o_phu_thuoc_hay_o_tran_van_bat(self) -> None:
        assert _loai4("🔒", phu_thuoc="✅ **25/09/2026** xong") == ["TD-0007"]
        dong = B.doc_backlog(_bang("| TD-0007 | m | 🔒 | — | x | ✅ **24/09/2026:** ô tràn sau dấu gạch cuối"))
        assert [v.loai for v in B.tim_van_de(dong, [])] == [B.LOAI_KHOA_DA_GHI_XONG]

    def test_trang_thai_da_dong_hay_tam_dung_thi_khong_bao(self) -> None:
        assert _loai4("✅ `3d4cdfd`", tieu_chi=XONG) == []
        assert _loai4("❌", tieu_chi=XONG) == []
        assert _loai4("⏸", tieu_chi=XONG) == []  # phần đã làm trước khi dừng được mang dấu xong

    def test_dau_xong_chi_o_o_ten_viec_thi_khong_bao(self) -> None:
        assert _loai4("🔒", ten=f"làm tiếp sau TD-0006 ({XONG})") == []

    def test_dau_xong_khong_kem_ngay_thi_khong_bao(self) -> None:
        assert _loai4("🔒", phu_thuoc="TD-0330 ✅", tieu_chi="phần (i) ✅ `abc1234`, phần (ii) còn dở") == []

    def test_trang_thai_lan_chi_bao_loai_2(self) -> None:
        dong = B.doc_backlog(_bang(f"| TD-0007 | m | 🔓 ⏸ | — | {XONG} |"))
        assert [v.loai for v in B.tim_van_de(dong, [])] == [B.LOAI_TRANG_THAI_LAN]

    def test_moi_dong_bao_toi_da_mot_lan(self) -> None:
        assert _loai4("🔒", phu_thuoc="✅ **01/09/2026**", tieu_chi=XONG) == ["TD-0007"]

    def test_bao_cao_goi_ten_loai(self) -> None:
        ma, text = B.bao_cao(tasks_text=_bang(f"| TD-0007 | m | 🔒 | — | {XONG} |"), tieu_de_commit=[])
        assert ma == 1 and "đã ghi xong, chưa lật trạng thái" in text and "TD-0007" in text


# ── ẢNH CHỤP LỊCH SỬ THẬT ────────────────────────────────────────────────────────────


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-c", "safe.directory=*", "-C", str(REPO_ROOT), *args],
        capture_output=True, text=True, encoding="utf-8",
    )


@pytest.fixture(scope="module")
def anh_chup_that():
    if _git("cat-file", "-e", f"{COMMIT_SUA}^{{commit}}").returncode != 0:
        pytest.skip(f"commit {COMMIT_SUA} không có trong bản clone này (clone nông?)")
    kq = _git("show", f"{COMMIT_SUA}~1:TASKS.md")
    assert kq.returncode == 0, kq.stderr
    return B.tim_van_de(B.doc_backlog(kq.stdout), B.doc_tieu_de_commit(REPO_ROOT))


class TestAnhChupLichSuThat:
    def test_loai_4_bat_dung_mot_ca_TD_0386(self, anh_chup_that) -> None:
        assert [v.ma for v in anh_chup_that if v.loai == B.LOAI_KHOA_DA_GHI_XONG] == ["TD-0386"]

    def test_viec_nhieu_chang_dang_do_chi_o_loai_1(self, anh_chup_that) -> None:
        """`TD-0405`/`TD-0427` 🔒 có commit mã việc nhưng CHƯA ghi xong — loại 4 không được gộp chúng vào."""
        theo_ma = {}
        for v in anh_chup_that:
            theo_ma.setdefault(v.ma, set()).add(v.loai)
        assert theo_ma.get("TD-0405") == {B.LOAI_KHOA_CO_COMMIT}
        assert theo_ma.get("TD-0427") == {B.LOAI_KHOA_CO_COMMIT}
