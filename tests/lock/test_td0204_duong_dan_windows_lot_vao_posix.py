"""TD-0204 — đường dẫn kiểu Windows lọt vào tiến trình POSIX, hỏng IM
LẶNG. Ba sự cố THẬT ở ba chỗ khác nhau (TD-0200, `docs/research-log.md`
09-10/09/2026): Git Bash (MSYS) tự dịch một đường dẫn POSIX (`/backup`)
thành dạng ổ đĩa Windows (`C:/Program Files/Git/backup`) TRƯỚC khi truyền
vào tiến trình Linux trong container. Chuỗi kết quả KHÔNG mở đầu bằng
`/` nên Linux hiểu nó là đường dẫn TƯƠNG ĐỐI, và một thao tác ghi âm
thầm ghi sai chỗ trong khi lệnh vẫn báo thành công.

Hai lớp canh, độc lập:
    1. `find_windows_path_leak()` nối vào `measurement_guard()` — chặn
       NGAY tại cửa vào, trước khi bất kỳ entrypoint nào làm việc gì.
    2. Quét TOÀN BỘ cây làm việc cấm ký tự U+F03A trong tên file/thư mục
       — bắt được HẬU QUẢ đã xảy ra (một artifact lạc chỗ), kể cả khi
       lớp 1 bị đi vòng bằng cách nào đó.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from tool_d.measurement.guard import GuardOutcome, find_windows_path_leak, measurement_guard

REPO_ROOT = Path(__file__).resolve().parents[2]

# Cây con của MỘT repo khác (dashboard-ui, tách riêng — xem CLAUDE.md mục
# TD-0006/TD-0007), và `.git` nội bộ của mọi repo. Loại trừ có lý do, đo
# được (không phải linh cảm hiệu năng — bài học của phiên `-dc`, FE-0064:
# `node_modules` chiếm 57.175/59.828 mục, 95,6%, của TOÀN BỘ cây; là gói
# bên thứ ba do npm tạo trực tiếp trên Windows, không đi qua đường
# MSYS-dịch-rồi-vào-container mà TD-0204 canh).
_BO_QUA_TEN_THU_MUC = {".git", "node_modules", "__pycache__"}

_U_F03A = "\uf03a"


def _quet_ky_tu_la(root: Path) -> list[str]:
    vi_pham: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _BO_QUA_TEN_THU_MUC]
        for name in list(dirnames) + filenames:
            if _U_F03A in name:
                vi_pham.append(str(Path(dirpath) / name))
    return vi_pham


class TestFindWindowsPathLeak:
    """`find_windows_path_leak()` — chỉ hàm thuần, không đụng `measurement_guard()`."""

    def test_duong_dan_tuyet_doi_dang_token_rieng_bi_bat(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(os, "name", "posix")
        leak = find_windows_path_leak(["--backup-root", "C:/Program Files/Git/backup"])
        assert leak == "C:/Program Files/Git/backup"

    def test_duong_dan_kieu_gach_cheo_nguoc_bi_bat(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(os, "name", "posix")
        leak = find_windows_path_leak(["--backup-root", "C:\\Program Files\\Git\\backup"])
        assert leak is not None

    def test_dang_co_dau_bang_trong_cung_mot_token_bi_bat(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(os, "name", "posix")
        leak = find_windows_path_leak(["--backup-root=C:/Program Files/Git/backup"])
        assert leak == "--backup-root=C:/Program Files/Git/backup"

    def test_duong_dan_posix_binh_thuong_khong_bi_bat(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(os, "name", "posix")
        argv = ["--backup-root", "/backup", "--data-dir", "runs/backfill_backup", "--cache", "none"]
        assert find_windows_path_leak(argv) is None

    def test_tren_host_windows_khong_bi_coi_la_ro_ri(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # 🔴 N6: không bịa vi phạm. Trên chính host Windows của dự án,
        # `C:\...` là đường dẫn HỢP LỆ.
        monkeypatch.setattr(os, "name", "nt")
        leak = find_windows_path_leak(["--backup-root", "C:\\tool-d-data-backup"])
        assert leak is None

    def test_khong_khop_mot_chu_cai_roi_dau_hai_cham_roi_chu_so(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Ca biên: một chữ cái + `:` + CHỮ SỐ (kiểu `host:port` với
        # hostname một ký tự) — không phải dấu phân cách đường dẫn
        # (`\` hoặc `/`) ngay sau `:`, KHÔNG được coi là đường dẫn ổ đĩa.
        monkeypatch.setattr(os, "name", "posix")
        assert find_windows_path_leak(["--api-server", "x:8080"]) is None

    def test_khong_khop_C_dung_mot_minh(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(os, "name", "posix")
        assert find_windows_path_leak(["C:"]) is None


class TestMeasurementGuardChanRoRi:
    """Kiểm dây nối thật: `measurement_guard()` phải trả BLOCKED, không
    chỉ hàm thuần `find_windows_path_leak()` đúng — đúng bài học N5
    (gọi tường minh, không phải một hàm mồ côi không ai gọi tới)."""

    def test_guard_chan_khi_co_ro_ri(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(os, "name", "posix")
        strategy_dir = tmp_path / "strategies"
        strategy_dir.mkdir()
        report = measurement_guard(
            "E8",
            strategy_dir=strategy_dir,
            config_path=Path("config/tool_d_config.yaml"),
            argv=["--backup-root", "C:/Program Files/Git/backup"],
        )
        assert report.outcome is GuardOutcome.BLOCKED
        assert report.guard_passed is False
        assert report.windows_path_leak == "C:/Program Files/Git/backup"

    def test_guard_khong_chan_khi_argv_sach(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(os, "name", "posix")
        strategy_dir = tmp_path / "strategies"
        strategy_dir.mkdir()
        report = measurement_guard(
            "E8",
            strategy_dir=strategy_dir,
            config_path=Path("config/tool_d_config.yaml"),
            argv=["--backup-root", "runs/backfill_backup"],
        )
        assert report.outcome is GuardOutcome.PASS
        assert report.windows_path_leak is None

    def test_ro_ri_duoc_bat_TRUOC_ca_file_tham_so_an(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # Hai lý do BLOCKED cùng lúc -> thông báo về đường dẫn phải xuất
        # hiện, vì đó là chuyện của CHÍNH lệnh gọi, đứng trước câu hỏi
        # "cấu hình nào đang được dùng".
        monkeypatch.setattr(os, "name", "posix")
        strategy_dir = tmp_path / "strategies"
        strategy_dir.mkdir()
        (strategy_dir / "X.json").write_text("{}")

        report = measurement_guard(
            "E8",
            strategy_dir=strategy_dir,
            config_path=Path("config/tool_d_config.yaml"),
            argv=["--backup-root", "C:/Program Files/Git/backup"],
        )
        assert report.windows_path_leak is not None
        assert report.hidden_param_files == {}  # chưa kịp quét tới bước đó
        out = capsys.readouterr().out
        assert "ĐƯỜNG DẪN WINDOWS" in out


class TestQuetKyTuLaTrongRepo:
    """Lớp canh THỨ HAI, độc lập với `measurement_guard()`: cấm ký tự
    U+F03A (dấu hai chấm giả mà NTFS dùng để hiển thị một `:` không hợp
    lệ trong tên file) xuất hiện ở BẤT KỲ đâu trong cây làm việc — bắt
    được hậu quả đã xảy ra, không phụ thuộc máy canh ở cửa vào có bị đi
    vòng hay không.
    """

    def test_repo_that_khong_co_ky_tu_la(self) -> None:
        vi_pham = _quet_ky_tu_la(REPO_ROOT)
        assert vi_pham == [], f"Phát hiện ký tự U+F03A trong đường dẫn: {vi_pham}"

    def test_bo_quet_co_rang(self, tmp_path: Path) -> None:
        (tmp_path / f"C{_U_F03A}").mkdir()
        (tmp_path / f"C{_U_F03A}" / "Program Files").mkdir()
        assert _quet_ky_tu_la(tmp_path) == [str(tmp_path / f"C{_U_F03A}")]

    def test_loai_tru_node_modules_co_ly_do_do_duoc(self) -> None:
        # Đối chứng cho quyết định loại trừ — KHÔNG phải linh cảm hiệu
        # năng (bài học FE-0064): node_modules của dashboard-ui (repo
        # KHÁC) phải chiếm phần LỚN cây nếu bị quét, nên loại trừ nó có
        # nghĩa; loại trừ `data`/`user_data` thì KHÔNG, vì đó chính là
        # nơi TD-0200 tìm thấy sự cố thật — không được loại trừ.
        assert "data" not in _BO_QUA_TEN_THU_MUC
        assert "user_data" not in _BO_QUA_TEN_THU_MUC
