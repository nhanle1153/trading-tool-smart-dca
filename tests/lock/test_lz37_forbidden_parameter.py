"""L-Z37 🔴 CRITICAL — grep repo: KHÔNG có IntParameter|DecimalParameter|
CategoricalParameter|BooleanParameter|RealParameter. KHÔNG có
<Strategy>.json trong thư mục strategies (guard). Spec dòng 675-677.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCAN_DIRS = ("src", "entrypoints")
FORBIDDEN = re.compile(
    r"\b(IntParameter|DecimalParameter|CategoricalParameter|"
    r"BooleanParameter|RealParameter)\b"
)


def _python_files() -> list[Path]:
    files: list[Path] = []
    for d in SCAN_DIRS:
        base = REPO_ROOT / d
        if base.exists():
            files.extend(base.rglob("*.py"))
    return files


class TestKhongDungParameterCuaFreqtrade:
    def test_khong_co_file_python_nao_trong_src_entrypoints(self) -> None:
        # Không có gì để quét thì test này vô nghĩa — phải luôn có ít nhất
        # một file, nếu không nghĩa là SCAN_DIRS sai đường dẫn.
        assert len(_python_files()) > 0

    def test_khong_co_dau_hieu_cua_Parameter_freqtrade(self) -> None:
        vi_pham: list[str] = []
        for f in _python_files():
            text = f.read_text(encoding="utf-8", errors="replace")
            for match in FORBIDDEN.finditer(text):
                vi_pham.append(f"{f.relative_to(REPO_ROOT)}: {match.group(0)}")
        assert vi_pham == [], f"Phát hiện *Parameter của Freqtrade: {vi_pham}"

    def test_bo_quet_co_rang_phat_hien_duoc_vi_pham_gia_lap(self, tmp_path: Path) -> None:
        # Chứng minh regex có răng — không chỉ là test luôn xanh vì
        # không tìm gì cả.
        bad_file = tmp_path / "bad_strategy.py"
        bad_file.write_text("threshold = IntParameter(1, 10, default=5)")
        text = bad_file.read_text()
        assert FORBIDDEN.search(text) is not None


class TestKhongCoFileThamSoAnCanhStrategy:
    def test_thu_muc_strategies_khong_co_file_json(self) -> None:
        strategies_dir = REPO_ROOT / "user_data" / "strategies"
        assert strategies_dir.exists(), "user_data/strategies/ phải tồn tại"
        json_files = list(strategies_dir.glob("*.json"))
        assert json_files == [], (
            f"Phát hiện file tham số ẩn trong strategies/: {json_files} — "
            "đây chính là cái bẫy LD-01/LD-02 đã hạ Tool A ba lần (0d.1)."
        )
