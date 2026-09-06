"""L-Z41 (phần đầu ra thật) — grep đầu ra CLI THẬT của E5 `periodic_report.py`
tìm giá trị lính canh (spec dòng 629-630, 684-686). Phần kiểm CƠ CHẾ của
`tri_state.py` (Measured bất biến, `scan_for_sentinels`, `audit_line`) nằm
ở `test_lz41_tri_state.py` (TD-0010) — file này KHOÁ HÀNH VI của chính E5
khi chạy như tiến trình con, cùng phong cách `test_run_backtest_cache.py`
(TD-0018) và `test_touch_lockbox.py` (TD-0071).

TD-0060 tự gọi `scan_for_sentinels()` bên trong `periodic_report.py` trước
khi in (phòng lỗi lập trình) — test này ĐỘC LẬP với cơ chế tự kiểm đó: nó
grep trực tiếp `stdout` bằng cùng hàm dùng chung `scan_for_sentinels()`
CỘNG THÊM kiểm chuỗi thô theo đúng câu chữ Verify của TD-0061 ("-1",
"UNKNOWN", "0.0 giả"), để không phụ thuộc vào việc entrypoint có tự kiểm
đúng hay không — nếu ai đó lỡ xoá bước tự kiểm trong `periodic_report.py`,
test này vẫn đứng độc lập bắt được sentinel lọt ra.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from tool_d.measurement.tri_state import scan_for_sentinels
from tool_d.reporting.report_model import build_metrics

REPO_ROOT = Path(__file__).resolve().parents[2]
E5 = REPO_ROOT / "entrypoints" / "periodic_report.py"

# "-1" như một token độc lập — không bắt nhầm "-10", "-15" (đúng ranh giới
# mà scan_for_sentinels() đã dùng, lặp lại tường minh ở đây để test này
# không phụ thuộc import nội bộ của tri_state.py cho phần literal check).
_TOKEN_AM_1 = re.compile(r"(?<![\w.+-])-1(?![\w.])")


def _run() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(E5)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


class TestDauRaThatCuaE5KhongCoSentinel:
    def test_chay_thanh_cong(self) -> None:
        result = _run()
        assert result.returncode == 0, result.stdout + result.stderr

    def test_scan_for_sentinels_sach(self) -> None:
        result = _run()
        assert scan_for_sentinels(result.stdout) == []

    def test_khong_co_unknown(self) -> None:
        result = _run()
        assert "UNKNOWN" not in result.stdout

    def test_khong_co_na(self) -> None:
        result = _run()
        assert "N/A" not in result.stdout

    def test_khong_co_am_1_doc_lap(self) -> None:
        result = _run()
        assert _TOKEN_AM_1.search(result.stdout) is None

    def test_khong_co_00_gia(self) -> None:
        # Ở D0-PRE KHÔNG chỉ số nào ở trạng thái OK (xem report_model.py) —
        # nên "0.0" không có lý do hợp lệ nào để xuất hiện trong đầu ra.
        # Nếu dòng này đỏ trong tương lai (khi có chỉ số OK thật mang giá
        # trị 0.0 hợp lệ), đó là tín hiệu phải sửa lại test này cho khớp
        # ngữ cảnh mới — không phải bằng chứng bug.
        result = _run()
        assert "0.0" not in result.stdout

    def test_moi_chi_so_hien_chua_do_duoc(self) -> None:
        result = _run()
        for m in build_metrics():
            assert m.code in result.stdout
        assert result.stdout.count("chưa đo được") >= len(build_metrics())

    def test_khoi_xuat_xu_o_dau_dau_ra_that(self) -> None:
        result = _run()
        assert result.stdout.index("KHỐI XUẤT XỨ") < result.stdout.index("BÁO CÁO ĐỊNH KỲ")
