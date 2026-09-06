"""TD-0060 — E5 `periodic_report.py`: khối xuất xứ ở đầu + bảng chỉ số
CỐ ĐỊNH, mọi chỉ số `pending` ở D0-PRE. Test grep chuyên biệt cho L-Z41
trên đầu ra thật (subprocess CLI đầy đủ) là TD-0061, chưa làm ở đây — test
này kiểm ở mức HÀM (`render_report`) là chính, cùng một smoke test CLI để
khoá exit code + không crash khi chạy như tiến trình con.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from tool_d.measurement.tri_state import scan_for_sentinels
from tool_d.reporting.report_model import build_metrics

REPO_ROOT = Path(__file__).resolve().parents[2]
E5 = REPO_ROOT / "entrypoints" / "periodic_report.py"

sys.path.insert(0, str(REPO_ROOT / "entrypoints"))


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(E5), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


class TestRenderReportOMucHam:
    def test_co_khoi_xuat_xu_o_dau(self) -> None:
        import periodic_report  # type: ignore[import-not-found]

        text = periodic_report.render_report(report_guard_passed=True, params_source="yaml")
        vi_tri_khoi_xuat_xu = text.index("KHỐI XUẤT XỨ")
        vi_tri_bang = text.index("BÁO CÁO ĐỊNH KỲ")
        assert vi_tri_khoi_xuat_xu < vi_tri_bang  # xuất xứ Ở ĐẦU (spec dòng 4797)
        for khoa in ("git_sha:", "reproducible_from_sha:", "guard_passed:", "cache_mode:", "params_source:", "data_hashes:"):
            assert khoa in text

    def test_moi_hang_chi_so_deu_chua_dat(self) -> None:
        import periodic_report  # type: ignore[import-not-found]

        text = periodic_report.render_report(report_guard_passed=True, params_source="yaml")
        for m in build_metrics():
            assert m.code in text
            assert "chưa đo được" in text

    def test_khong_co_gia_tri_linh_canh(self) -> None:
        import periodic_report  # type: ignore[import-not-found]

        text = periodic_report.render_report(report_guard_passed=True, params_source="yaml")
        assert scan_for_sentinels(text) == []

    def test_dong_tong_dung_dinh_dang_audit_line(self) -> None:
        import periodic_report  # type: ignore[import-not-found]

        text = periodic_report.render_report(report_guard_passed=True, params_source="yaml")
        n = len(build_metrics())
        assert f"đã audit 0/{n} (0 đạt, 0 chưa đạt, {n} chưa đo được)" in text


class TestChayNhuTienTrinhCon:
    def test_chay_binh_thuong_exit_0(self) -> None:
        result = _run()
        assert result.returncode == 0
        assert "chưa đo được" in result.stdout
        assert "KHỐI XUẤT XỨ" in result.stdout

    def test_dau_ra_khong_co_sentinel(self) -> None:
        result = _run()
        assert scan_for_sentinels(result.stdout) == []
