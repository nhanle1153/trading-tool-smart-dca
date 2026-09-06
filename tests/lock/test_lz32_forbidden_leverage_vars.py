"""L-Z32 🔴 CRITICAL — grep toàn repo: KHÔNG có tham chiếu tới `L_D_max`,
`mult_cross`, `L_BASE`, `max_open_D` trong code hay config. Bốn thứ đã bị
XOÁ (v4/v6) — còn sót lại nghĩa là có hai nguồn sự thật cho cùng một số.
Spec dòng 3930-3932.

Bỏ qua dòng comment (`#...`) — config/tool_d_config.yaml cố ý ghi lại
"❌ L_D_max — v6 XOÁ" làm tài liệu lịch sử (dòng 34-35), đó là BẰNG CHỨNG
tuân thủ, không phải vi phạm.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCAN_DIRS = ("src", "entrypoints", "config")
SCAN_GLOBS = ("*.py", "*.yaml", "*.yml", "*.json")
FORBIDDEN = re.compile(r"\b(L_D_max|mult_cross|L_BASE|max_open_D)\b")


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


class TestKhongConTuThamSoDaXoa:
    def test_co_file_de_quet(self) -> None:
        assert len(_scanned_files()) > 0

    def test_khong_con_tham_chieu_bon_ten_da_xoa(self) -> None:
        vi_pham: list[str] = []
        for f in _scanned_files():
            text = _strip_comments(f.read_text(encoding="utf-8", errors="replace"))
            for match in FORBIDDEN.finditer(text):
                vi_pham.append(f"{f.relative_to(REPO_ROOT)}: {match.group(0)}")
        assert vi_pham == [], f"Phát hiện tham chiếu tới tên đã XOÁ: {vi_pham}"

    def test_bo_quet_co_rang(self) -> None:
        assert FORBIDDEN.search("max_leverage = L_D_max * 0.85") is not None

    def test_comment_lich_su_khong_bi_tinh_la_vi_pham(self) -> None:
        # Đúng nội dung thật ở config/tool_d_config.yaml dòng 34 — phải
        # KHÔNG bị đếm là vi phạm sau khi lọc comment.
        text = _strip_comments("  # ❌ L_D_max      — v6 XOÁ (≡ 0.85 × L_exchange, §6.8c)\n")
        assert FORBIDDEN.search(text) is None
