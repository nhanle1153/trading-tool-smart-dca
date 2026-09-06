"""L-Z48c 🆕 v8 — grep code (+ Decision Log, khi log đó tồn tại): không có
định danh/nhãn "R" TRẦN; chỉ {R_eff, r_eff_pct, planned_risk_usdt,
R_realized} và các dẫn xuất có tên đầy đủ. Spec dòng 2807-2809.

"R" trần trôi giữa hai định nghĩa "khoảng giá" và "hệ số nhân" mà không ai
phát hiện — đúng lớp lỗi §5.1 cảnh báo (spec dòng 2789-2792). Decision Log
(§8) chưa tồn tại ở D0-PRE (chưa có lệnh thật nào) nên chưa quét được —
thêm vào SCAN khi entrypoint ghi Decision Log ra đời.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCAN_DIRS = ("src", "entrypoints")
# \bR\b khớp "R" ĐỨNG MỘT MÌNH — "R_eff", "r_eff_pct", "R_realized" có ký
# tự \w (_ hoặc chữ) ngay sau "R" nên KHÔNG có \b ở đó, không bị bắt nhầm.
FORBIDDEN = re.compile(r"\bR\b")
ALLOWED_FULL_NAMES = {"R_eff", "r_eff_pct", "planned_risk_usdt", "R_realized"}


def _strip_comments(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))


def _python_files() -> list[Path]:
    files: list[Path] = []
    for d in SCAN_DIRS:
        base = REPO_ROOT / d
        if base.exists():
            files.extend(base.rglob("*.py"))
    return files


class TestCamNhanRTran:
    def test_co_file_de_quet(self) -> None:
        assert len(_python_files()) > 0

    def test_khong_co_nhan_r_tran(self) -> None:
        vi_pham: list[str] = []
        for f in _python_files():
            text = _strip_comments(f.read_text(encoding="utf-8", errors="replace"))
            for match in FORBIDDEN.finditer(text):
                vi_pham.append(f"{f.relative_to(REPO_ROOT)}: cột {match.start()}")
        assert vi_pham == [], f"Phát hiện nhãn 'R' trần (phải dùng tên đầy đủ): {vi_pham}"

    def test_bo_quet_co_rang_bien_gan_bang_R(self) -> None:
        assert FORBIDDEN.search("tp_fallback = p_avg + 1.5 * R") is not None

    def test_bo_quet_co_rang_nhan_dinh_trong_ngoac_kep(self) -> None:
        assert FORBIDDEN.search('tag = "R"') is not None

    def test_ten_day_du_khong_bi_bat_nham(self) -> None:
        for name in ALLOWED_FULL_NAMES:
            assert FORBIDDEN.search(f"{name} = 1.0") is None, name
