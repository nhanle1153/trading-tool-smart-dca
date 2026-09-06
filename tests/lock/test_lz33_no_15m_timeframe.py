"""L-Z33 🔴 CRITICAL — KHÔNG có tham chiếu tới khung 15m trong strategy hay
config (§3.3c đã xoá). Timeframe hợp lệ: 1H chính; 4H/1D informative ghép
LÊN bằng merge_informative_pair; 5m CHỈ dùng cho `timeframe_detail` của
backtest engine. Spec dòng 3933-3936.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCAN_DIRS = ("src", "entrypoints", "config", "user_data/strategies")
SCAN_GLOBS = ("*.py", "*.yaml", "*.yml", "*.json")
# \b bao quanh "15m" — không khớp bên trong token dài hơn (vd "115m").
FORBIDDEN = re.compile(r"\b15m\b", re.IGNORECASE)


def _strip_comments(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))


def _scanned_files() -> list[Path]:
    files: list[Path] = []
    for d in SCAN_DIRS:
        base = REPO_ROOT / d
        if not base.exists():
            continue
        for pattern in SCAN_GLOBS:
            files.extend(base.rglob(pattern))
    return files


class TestCamKhung15m:
    def test_co_file_de_quet(self) -> None:
        assert len(_scanned_files()) > 0

    def test_khong_con_tham_chieu_khung_15m(self) -> None:
        vi_pham: list[str] = []
        for f in _scanned_files():
            text = _strip_comments(f.read_text(encoding="utf-8", errors="replace"))
            for match in FORBIDDEN.finditer(text):
                vi_pham.append(f"{f.relative_to(REPO_ROOT)}: {match.group(0)}")
        assert vi_pham == [], f"Phát hiện tham chiếu khung 15m: {vi_pham}"

    def test_bo_quet_co_rang(self) -> None:
        assert FORBIDDEN.search('timeframe = "15m"') is not None

    def test_khung_5m_va_1h_khong_bi_bat_nham(self) -> None:
        # 5m (timeframe_detail) và 1h/4h/1d (hợp lệ) không được lọt vào bẫy
        # cùng regex — chứng minh regex không quá tay.
        assert FORBIDDEN.search('timeframe_detail = "5m"') is None
        assert FORBIDDEN.search('timeframe = "1h"') is None
