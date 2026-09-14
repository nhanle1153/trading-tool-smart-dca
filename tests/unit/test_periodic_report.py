"""TD-0060 — E5 `periodic_report.py`: khối xuất xứ ở đầu + bảng chỉ số
CỐ ĐỊNH. Test grep chuyên biệt cho L-Z41 trên đầu ra thật (subprocess CLI
đầy đủ) là TD-0061, chưa làm ở đây — test này kiểm ở mức HÀM
(`render_report`) là chính, cùng một smoke test CLI để khoá exit code +
không crash khi chạy như tiến trình con.

════ TD-0240 — CÔ LẬP BẮT BUỘC khỏi DB sản xuất thật ════
🔴 Bài học TRẢ GIÁ ngay trong đợt này (khác `TD-0239`): `db_url` trong
`config/freqtrade/config.json` là đường TUYỆT ĐỐI
(`sqlite:////workspace/user_data/tradesv3_dryrun.sqlite`) — không có
cách nào cô lập bằng `cwd`/copy `config/` như `TD-0239` đã làm (đó là
đường TƯƠNG ĐỐI). Lần chạy full suite ĐẦU TIÊN của các test này (trước
khi có `_moi_truong_co_lap`) đã tự tạo `user_data/tradesv3_dryrun.sqlite`
THẬT trong repo — bắt bởi `test_td0245_tu_dien_soi_schema_that.py::
test_khong_sinh_file_sqlite_trong_repo`. Mọi lời gọi `render_report()`/
CLI ở dưới ĐỀU truyền `tmp_path` qua ba tham số/cờ mới của TD-0240
(`freqtrade_config_path`, `decision_log_path`, `registry_path`).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from tool_d.measurement.tri_state import scan_for_sentinels
from tool_d.reporting.report_model import build_metrics

REPO_ROOT = Path(__file__).resolve().parents[2]
E5 = REPO_ROOT / "entrypoints" / "periodic_report.py"

sys.path.insert(0, str(REPO_ROOT / "entrypoints"))


def _moi_truong_co_lap(tmp_path: Path) -> dict[str, Path]:
    """Dựng một `config/freqtrade/config.json` TẠM với `db_url` trỏ vào
    `tmp_path` — KHÔNG copy toàn bộ `config/` thật (không cần, chỉ
    `render_report()` đọc mỗi `db_url` từ file này qua
    `freqtrade_db.doc_db_url_tu_config()`)."""
    freqtrade_config = tmp_path / "config.json"
    freqtrade_config.write_text(
        json.dumps({"db_url": f"sqlite:///{tmp_path / 'test.sqlite'}"}), encoding="utf-8"
    )
    return {
        "freqtrade_config_path": freqtrade_config,
        "decision_log_path": tmp_path / "decision_log.jsonl",
        "registry_path": tmp_path / "trial_registry.jsonl",
    }


def _run(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    duong_dan = _moi_truong_co_lap(tmp_path)
    return subprocess.run(
        [
            sys.executable, str(E5),
            "--freqtrade-config-path", str(duong_dan["freqtrade_config_path"]),
            "--decision-log-path", str(duong_dan["decision_log_path"]),
            "--registry-path", str(duong_dan["registry_path"]),
            *args,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


class TestRenderReportOMucHam:
    def test_co_khoi_xuat_xu_o_dau(self, tmp_path: Path) -> None:
        import periodic_report  # type: ignore[import-not-found]

        text = periodic_report.render_report(
            report_guard_passed=True, params_source="yaml", **_moi_truong_co_lap(tmp_path)
        )
        vi_tri_khoi_xuat_xu = text.index("KHỐI XUẤT XỨ")
        vi_tri_bang = text.index("BÁO CÁO ĐỊNH KỲ")
        assert vi_tri_khoi_xuat_xu < vi_tri_bang  # xuất xứ Ở ĐẦU (spec dòng 4797)
        for khoa in ("git_sha:", "reproducible_from_sha:", "guard_passed:", "cache_mode:", "params_source:", "data_hashes:"):
            assert khoa in text

    def test_moi_hang_chi_so_deu_chua_dat(self, tmp_path: Path) -> None:
        import periodic_report  # type: ignore[import-not-found]

        text = periodic_report.render_report(
            report_guard_passed=True, params_source="yaml", **_moi_truong_co_lap(tmp_path)
        )
        for m in build_metrics():
            assert m.code in text
        assert "chưa đo được" in text

    def test_khong_co_gia_tri_linh_canh(self, tmp_path: Path) -> None:
        import periodic_report  # type: ignore[import-not-found]

        text = periodic_report.render_report(
            report_guard_passed=True, params_source="yaml", **_moi_truong_co_lap(tmp_path)
        )
        assert scan_for_sentinels(text) == []

    def test_dong_tong_dung_dinh_dang_audit_line(self, tmp_path: Path) -> None:
        """TD-0240 — giả định cũ "0 đạt" đã LỖI THỜI: `BUDGET_*` (3 chỉ số)
        luôn tính được (ledger tự khởi tạo, không cần lệnh nào). Kiểm
        ĐỊNH DẠNG + kế toán khớp `n`, không hard-code con số "đạt" cụ thể."""
        import periodic_report  # type: ignore[import-not-found]

        text = periodic_report.render_report(
            report_guard_passed=True, params_source="yaml", **_moi_truong_co_lap(tmp_path)
        )
        n = len(build_metrics())
        khop = re.search(
            r"đã audit (\d+)/(\d+) \((\d+) đạt, (\d+) chưa đạt, (\d+) chưa đo được\)", text
        )
        assert khop, f"không thấy dòng audit_line đúng định dạng:\n{text}"
        da_audit, tong, dat, chua_dat, chua_do = (int(x) for x in khop.groups())
        assert tong == n
        assert dat + chua_dat + chua_do == n
        assert da_audit == dat + chua_dat
        assert dat >= 3, "BUDGET_B3_REMAINING/N_CURRENT/DSR_CURRENT phải luôn tính được"


class TestChayNhuTienTrinhCon:
    def test_chay_binh_thuong_exit_0(self, tmp_path: Path) -> None:
        result = _run(tmp_path)
        assert result.returncode == 0, result.stdout + result.stderr
        assert "chưa đo được" in result.stdout
        assert "KHỐI XUẤT XỨ" in result.stdout

    def test_dau_ra_khong_co_sentinel(self, tmp_path: Path) -> None:
        result = _run(tmp_path)
        assert scan_for_sentinels(result.stdout) == []

    def test_khong_dung_den_db_that_cua_repo(self, tmp_path: Path) -> None:
        """Kiểm-có-răng cho chính việc CÔ LẬP: nếu ai đó lỡ bỏ cờ
        `--freqtrade-config-path` khỏi `_run()`, ca này phải bắt được
        TRƯỚC khi một lượt chạy nào khác kịp tạo `.sqlite` rác trong
        repo (đúng lỗi `test_khong_sinh_file_sqlite_trong_repo` đã bắt)."""
        duong_that = REPO_ROOT / "user_data" / "tradesv3_dryrun.sqlite"
        ton_tai_truoc = duong_that.exists()
        _run(tmp_path)
        assert duong_that.exists() == ton_tai_truoc, "E5 đã tạo DB THẬT trong repo"
