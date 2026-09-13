"""TD-0233 — mọi dòng của một bảng markdown phải khớp SỐ CỘT của header bảng đó.

🔴 **Vì sao cần một cái MÁY, không phải kỷ luật.** Markdown **bỏ mọi ô vượt quá
số cột của header**. Một dòng 6 ô trong bảng 5 cột thì ô thứ 6 **vô hình ở bản
render** (GitHub) — nội dung vẫn nguyên trong file, nên đọc raw thì không mất gì,
và **không ai phát hiện được bằng cách đọc file**.

Bằng chứng rằng kỷ luật con người không đủ, đo trong 24 giờ: dòng `TD-0229` của
`TASKS.md` vỡ ngày 12/09/2026 — **2029 ký tự** khối *"Xác nhận `5b34e1b`…"* (gồm
cả ba phép kiểm-có-răng) bị render bỏ — **trong cùng ngày phiên viết nó chạy ĐÚNG
phép đếm này cho `back-end-note.md`** (34/34 dòng đúng) rồi commit. *Phép kiểm
đúng, áp sai chỗ.*

⚠️ Và nó là **bản THẬT của thứ `MT-18` từng báo động**: `MT-18` là báo động **GIẢ**
(4 trong 12 dấu `|` của dòng đó đã được escape đúng ⇒ 7 dấu cấu trúc ⇒ 7 cột, đúng).
Đó là lý do phép đếm ở đây phải **bỏ phần trong backtick** và **bỏ `\\|` đã escape**
trước khi đếm — đếm dấu `|` thô thì vừa báo đỏ giả vừa bỏ sót ca thật.

🔴 **KHÔNG có một con số cột chung.** `TASKS.md` có **20 bảng**, và bảng changelog ở
cuối có **6 cột — ĐÚNG**. Một phép kiểm ghim hằng `5` sẽ báo đỏ giả cho cả bảng đó.
Vì thế `TestLogicTheoTungBang` pin đúng tính chất *"so với header của CHÍNH bảng
đó"* bằng markdown dựng tay: thiếu lớp đó thì một bản cài sai (ghim hằng 5) vẫn
xanh trên `TestFileThatSach`.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

#: File trạng thái dùng chung — nơi nội dung bị render bỏ gây thiệt hại thật.
FILE_CAN_CANH: tuple[str, ...] = (
    "TASKS.md",
    "back-end-note.md",
    "ARCHITECTURE.md",
)

_RE_BACKTICK = re.compile(r"`[^`]*`")
_RE_PHAN_CACH = re.compile(r"^\|[\s:|-]+\|\s*$")
_RE_FENCE = re.compile(r"^\s*```")


def dem_cot(dong: str) -> int:
    """Số CỘT của một dòng bảng markdown.

    Hai phép bỏ, cả hai bắt buộc (bài học `MT-18`):
      • bỏ phần trong backtick — `` `a|b` `` là MỘT ô, không phải hai;
      • bỏ `\\|` đã escape — nó là dấu gạch dọc hiển thị, không phải vách ô.
    """
    tho = _RE_BACKTICK.sub("X", dong)
    tho = tho.replace(r"\|", "")
    return tho.count("|") - 1


def quet_bang(noi_dung: str) -> list[tuple[int, int, int, str]]:
    """Trả danh sách `(so_dong, cot_header, cot_dong, trich)` của mọi dòng LỆCH.

    Quét theo **TỪNG BẢNG**: một dòng phân cách `|---|` mở một bảng, header là
    dòng ngay trước nó, và các dòng `|` liền sau là dữ liệu của **bảng đó**.
    Bỏ qua phần trong khối ``` (ví dụ mã có thể chứa dấu `|` hợp lệ).
    """
    lines = noi_dung.split("\n")
    trong_fence = False
    lech: list[tuple[int, int, int, str]] = []
    i = 0
    while i < len(lines):
        if _RE_FENCE.match(lines[i]):
            trong_fence = not trong_fence
            i += 1
            continue
        if (
            not trong_fence
            and _RE_PHAN_CACH.match(lines[i])
            and i > 0
            and lines[i - 1].lstrip().startswith("|")
        ):
            n_head = dem_cot(lines[i - 1])
            j = i + 1
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                if _RE_FENCE.match(lines[j]):
                    break
                n = dem_cot(lines[j])
                if n != n_head:
                    lech.append((j + 1, n_head, n, lines[j][:60]))
                j += 1
            i = j
            continue
        i += 1
    return lech


class TestLogicTheoTungBang:
    """Pin tính chất *"so với header của CHÍNH bảng đó"* — thiếu lớp này thì một
    bản cài ghim hằng số 5 vẫn xanh trên các file thật."""

    BANG_5 = "| a | b | c | d | e |\n|---|---|---|---|---|\n"
    BANG_6 = "| a | b | c | d | e | f |\n|---|---|---|---|---|---|\n"

    def test_bang_dung_thi_sach(self) -> None:
        assert quet_bang(self.BANG_5 + "| 1 | 2 | 3 | 4 | 5 |\n") == []

    def test_hai_bang_KHAC_SO_COT_trong_cung_file_deu_sach(self) -> None:
        """`TASKS.md` thật có đúng tình huống này: 19 bảng 5 cột + 1 bảng
        changelog 6 cột. Không có một con số chung nào dùng được."""
        tai_lieu = (
            self.BANG_5
            + "| 1 | 2 | 3 | 4 | 5 |\n\n"
            + self.BANG_6
            + "| 1 | 2 | 3 | 4 | 5 | 6 |\n"
        )
        assert quet_bang(tai_lieu) == []

    def test_o_THUA_trong_bang_5_cot_bi_bat(self) -> None:
        lech = quet_bang(self.BANG_5 + "| 1 | 2 | 3 | 4 | 5 | 6 |\n")
        assert len(lech) == 1 and lech[0][1:3] == (5, 6)

    def test_o_THUA_trong_bang_6_cot_CUNG_bi_bat(self) -> None:
        """🔴 Vế quyết định: một bản cài ghim hằng `5` sẽ cho ca này XANH (vì
        6 ≠ 5 nên nó tưởng đã bắt) — nhưng nó sẽ đồng thời báo đỏ GIẢ cho
        `test_hai_bang_...` ở trên. Hai ca phải cùng đúng."""
        lech = quet_bang(self.BANG_6 + "| 1 | 2 | 3 | 4 | 5 | 6 | 7 |\n")
        assert len(lech) == 1 and lech[0][1:3] == (6, 7)

    def test_o_THIEU_cung_bi_bat(self) -> None:
        """Dòng ít ô hơn header thì markdown chèn ô rỗng — không mất nội dung,
        nhưng các ô sau đó **dịch sang cột khác** (`TD-0192` đang ở tình trạng
        này với 4 cột)."""
        lech = quet_bang(self.BANG_5 + "| 1 | 2 | 3 | 4 |\n")
        assert len(lech) == 1 and lech[0][1:3] == (5, 4)

    def test_backtick_chua_dau_gach_doc_KHONG_tinh_la_vach_o(self) -> None:
        assert quet_bang(self.BANG_5 + "| `a|b` | 2 | 3 | 4 | 5 |\n") == []

    def test_dau_gach_doc_ESCAPE_KHONG_tinh_la_vach_o(self) -> None:
        r"""Đây chính là chỗ `MT-18` báo động GIẢ: `\|` là dấu hiển thị."""
        assert quet_bang(self.BANG_5 + r"| a \| b | 2 | 3 | 4 | 5 |" + "\n") == []

    def test_khoi_ba_backtick_bi_bo_qua(self) -> None:
        """`CLAUDE.md`/`TASKS.md` có khối mã chứa dấu `|` hợp lệ."""
        tai_lieu = self.BANG_5 + "```\n| khong | phai | mot | dong | bang | dau |\n```\n"
        assert quet_bang(tai_lieu) == []


class TestFileThatSach:
    """Các file trạng thái dùng chung phải KHÔNG có dòng nào lệch cột."""

    @pytest.mark.parametrize("ten", FILE_CAN_CANH)
    def test_moi_dong_khop_header_bang_cua_no(self, ten: str) -> None:
        duong = REPO_ROOT / ten
        assert duong.is_file(), f"{ten} không tồn tại"
        lech = quet_bang(duong.read_text(encoding="utf-8"))
        if lech:
            chi_tiet = "\n".join(
                f"  dòng {d}: header {h} cột, dòng này {c} cột  |  {t}"
                for d, h, c, t in lech
            )
            pytest.fail(
                f"{ten}: {len(lech)} dòng lệch số cột so với header của chính "
                f"bảng đó. Markdown BỎ ô vượt quá số cột header ⇒ nội dung đó "
                f"VÔ HÌNH khi render.\n{chi_tiet}"
            )
