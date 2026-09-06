"""L-Z46 🔴 CRITICAL — grep tầng đo: KHÔNG có `profit_ratio` (đơn vị đo phải
là `pnl_abs`, DR-013) và KHÔNG có `initial_stop_loss_abs` (không dùng làm
mẫu số — spec dòng 5027-5028). Spec dòng 2795-2797.

Cấm tuyệt đối cả hai định danh trong tầng đo, không chỉ trong phép cộng/
trung bình — dễ kiểm và không để lọt biến thể "gán trước rồi mới cộng".
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCAN_DIRS = ("src", "entrypoints")
FORBIDDEN = re.compile(r"\b(profit_ratio|initial_stop_loss_abs)\b")


def _strip_comments(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))


def _python_files() -> list[Path]:
    files: list[Path] = []
    for d in SCAN_DIRS:
        base = REPO_ROOT / d
        if base.exists():
            files.extend(base.rglob("*.py"))
    return files


class TestCamProfitRatioVaInitialStopLossAbs:
    def test_co_file_de_quet(self) -> None:
        assert len(_python_files()) > 0

    def test_khong_co_profit_ratio_hay_initial_stop_loss_abs(self) -> None:
        vi_pham: list[str] = []
        for f in _python_files():
            text = _strip_comments(f.read_text(encoding="utf-8", errors="replace"))
            for match in FORBIDDEN.finditer(text):
                vi_pham.append(f"{f.relative_to(REPO_ROOT)}: {match.group(0)}")
        assert vi_pham == [], f"Phát hiện đơn vị đo bị cấm ở tầng đo (DR-013): {vi_pham}"

    def test_bo_quet_co_rang(self) -> None:
        assert FORBIDDEN.search("avg = sum(t.profit_ratio for t in trades) / len(trades)") is not None
        assert FORBIDDEN.search("risk_denominator = trade.initial_stop_loss_abs") is not None

    def test_pnl_abs_khong_bi_bat_nham(self) -> None:
        assert FORBIDDEN.search("total = sum(t.pnl_abs for t in trades)") is None
