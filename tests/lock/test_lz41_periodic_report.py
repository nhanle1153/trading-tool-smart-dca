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

import json
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


def _run(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    """TD-0240 — CÔ LẬP BẮT BUỘC khỏi DB sản xuất thật. `db_url` trong
    `config/freqtrade/config.json` là đường TUYỆT ĐỐI — không cô lập
    được bằng `cwd` (khác bài học `TD-0239`, nơi đường dẫn là tương đối).
    Không truyền ba cờ này sẽ tạo `user_data/tradesv3_dryrun.sqlite`
    THẬT trong repo mỗi lần chạy (đã xảy ra thật, bắt bởi `test_td0245_
    tu_dien_soi_schema_that.py::test_khong_sinh_file_sqlite_trong_repo`)."""
    freqtrade_config = tmp_path / "config.json"
    freqtrade_config.write_text(
        json.dumps({"db_url": f"sqlite:///{tmp_path / 'test.sqlite'}"}), encoding="utf-8"
    )
    return subprocess.run(
        [
            sys.executable, str(E5),
            "--freqtrade-config-path", str(freqtrade_config),
            "--decision-log-path", str(tmp_path / "decision_log.jsonl"),
            "--registry-path", str(tmp_path / "trial_registry.jsonl"),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


class TestDauRaThatCuaE5KhongCoSentinel:
    def test_chay_thanh_cong(self, tmp_path: Path) -> None:
        result = _run(tmp_path)
        assert result.returncode == 0, result.stdout + result.stderr

    def test_scan_for_sentinels_sach(self, tmp_path: Path) -> None:
        result = _run(tmp_path)
        assert scan_for_sentinels(result.stdout) == []

    def test_khong_co_unknown(self, tmp_path: Path) -> None:
        result = _run(tmp_path)
        assert "UNKNOWN" not in result.stdout

    def test_khong_co_na(self, tmp_path: Path) -> None:
        result = _run(tmp_path)
        assert "N/A" not in result.stdout

    def test_khong_co_am_1_doc_lap(self, tmp_path: Path) -> None:
        result = _run(tmp_path)
        assert _TOKEN_AM_1.search(result.stdout) is None

    def test_khong_co_00_gia(self, tmp_path: Path) -> None:
        # TD-0240: giờ CÓ chỉ số OK thật (BUDGET_*), nhưng trên sổ trial
        # RỖNG cả ba đều render "0"/số dương khác 0.0 (n_used() là INT,
        # dsr_hurdle(114) > 0) — nên "0.0" vẫn không có lý do hợp lệ nào
        # để xuất hiện. Nếu dòng này đỏ trong tương lai (khi một chỉ số
        # OK khác mang đúng giá trị 0.0 hợp lệ), đó là tín hiệu phải sửa
        # lại test này cho khớp ngữ cảnh mới — không phải bằng chứng bug.
        result = _run(tmp_path)
        assert "0.0" not in result.stdout

    def test_moi_chi_so_hien_chua_do_duoc(self, tmp_path: Path) -> None:
        """TD-0240 — `BUDGET_B3_REMAINING`/`BUDGET_N_CURRENT`/
        `BUDGET_DSR_CURRENT` giờ LUÔN tính được (ledger tự khởi tạo,
        không cần lệnh nào) — giả định cũ "TOÀN BỘ chưa đo được" đã lỗi
        thời. Giữ nguyên tinh thần: mọi chỉ số KHÁC (chưa có nguồn dữ
        liệu cấu trúc, hoặc có nguồn nhưng chưa có lệnh thật) vẫn phải
        hiện đúng câu, không rơi vào 0.0/UNKNOWN/lính canh nào (các ca
        khác trong lớp này đã canh riêng điều đó)."""
        result = _run(tmp_path)
        for m in build_metrics():
            assert m.code in result.stdout
        so_luon_tinh_duoc = 3  # BUDGET_B3_REMAINING, BUDGET_N_CURRENT, BUDGET_DSR_CURRENT
        assert result.stdout.count("chưa đo được") >= len(build_metrics()) - so_luon_tinh_duoc

    def test_khoi_xuat_xu_o_dau_dau_ra_that(self, tmp_path: Path) -> None:
        result = _run(tmp_path)
        assert result.stdout.index("KHỐI XUẤT XỨ") < result.stdout.index("BÁO CÁO ĐỊNH KỲ")
