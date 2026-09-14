r"""TD-0245 — quét mã sản xuất tìm chỗ ĐỌC cột database, để Quy tắc 7 có máy canh.

Quy tắc 7 (`CLAUDE.md:25`) cấm đọc/ghi một trường database khi chưa tra từ
điển. Cho tới TD-0245, luật đó chỉ sống trong `CLAUDE.md` — **không một dòng
mã nào thi hành**. Module này là phần "máy đọc" của lớp canh đó.

🔴 **Vì sao KHÔNG khớp mọi tên cột, và vì sao đó không phải sự lười.**
Bài học ngày 08/09 (đợt rà toàn bộ lớp canh): *"đừng đo tính chất NGỮ NGHĨA
bằng dấu hiệu CÚ PHÁP"* — phép đếm bằng heuristic cú pháp hôm đó cho hai kết
quả mâu thuẫn (20/46 rồi 0/46) nên **vô giá trị**. Tên cột như `id`, `amount`,
`status`, `pair`, `side`, `price`, `timeframe`, `leverage` cũng là tên thuộc
tính thông thường của hàng chục đối tượng KHÔNG phải `Trade`/`Order`
(`self.timeframe` của chiến lược là khung thời gian, **không** phải cột
`trades.timeframe`). Khớp mù theo tên sẽ dựng một từ điển **nói sai sự thật**
về ai đọc cái gì — tệ hơn không có.

Nên phép quét này cố ý **THIẾU HỤT CÓ KIỂM SOÁT**: chỉ xét tên cột **đặc
trưng** (có dấu gạch dưới — `close_profit_abs`, `realized_profit`,
`funding_fees`, `order_update_date`, `ft_order_side`…). Nó **bỏ sót** cột tên
chung, và **không bao giờ buộc tội oan**. Thiếu sót đi về phía an toàn: một
lần bỏ sót là một lần lớp canh im lặng, còn một lần buộc tội oan sẽ khiến
người ta gỡ luôn lớp canh (tiền lệ `TD-0147`: *"một chốt không bao giờ thoả
được thì tệ hơn không có chốt"*).

⚠️ **Những gì phép quét này KHÔNG thấy** (khai thẳng theo N6, đừng đọc quá
tay): truy cập động `getattr(trade, ten)`, truy cập kiểu `hang["close_date"]`,
và mọi cột tên chung không có gạch dưới. Nó chỉ thấy **truy cập theo thuộc
tính** với tên đặc trưng — hôm nay đó là đường mà 100% lệnh đọc DB của Tool D
đi qua (kiểm: `grep -rn "sqlalchemy\|session\|sqlite3" src/ entrypoints/
user_data/strategies/` cho **0 kết quả**, mọi truy cập đều qua ORM trong
callback).
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

# Thư mục mã SẢN XUẤT. `tests/` cố ý đứng ngoài: test được phép dựng đối
# tượng giả mang tên cột để kiểm chính lớp canh này, và nếu quét luôn tests/
# thì lớp canh sẽ tự báo động vì chính bộ test của nó.
THU_MUC_SAN_XUAT: tuple[str, ...] = (
    "src/tool_d",
    "entrypoints",
    "user_data/strategies",
)


def la_ten_dac_trung(ten: str) -> bool:
    """Tên cột có đủ đặc trưng để khớp theo thuộc tính mà không nhầm không?

    Tiêu chí **một dòng, máy kiểm được**: có dấu gạch dưới ở GIỮA tên. Không
    phải vì gạch dưới có phép màu, mà vì mọi cột dễ hiểu sai của `trades`
    (`close_profit_abs`, `realized_profit`, `funding_fees`, `max_stake_amount`)
    đều có, còn mọi tên đụng hàng với thuộc tính thường (`id`, `amount`,
    `status`, `pair`, `price`, `side`, `cost`, `filled`, `symbol`, `strategy`,
    `timeframe`, `leverage`, `exchange`) đều không.

    Tên bắt đầu bằng `_` bị loại: đó là quy ước "nội bộ" của Python, và Tool D
    dùng nó cho thuộc tính riêng của mình (`self._dinh_equity`).
    """
    return not ten.startswith("_") and "_" in ten.strip("_")


@dataclass(frozen=True)
class ChoDoc:
    """Một chỗ mã sản xuất đọc thuộc tính trùng tên một cột database."""

    cot: str
    duong_dan: str
    ham: str
    dong: int

    def nhan(self) -> str:
        """Nhãn ngắn cho cột *Dùng bởi* của từ điển.

        Cố ý **không** mang số dòng: từ điển sẽ lỗi thời sau mỗi lần ai đó
        thêm một dòng trống vào file kia. Dự án đã dính đúng lỗi này ít nhất
        ba lần (`back-end-note.md:129` trỏ `ZoneAbsorption.py:282`, thực tế
        `:286`; `CLAUDE.md:968` trỏ `ARCHITECTURE.md:229`, thực tế `:249`).
        """
        return f"{self.duong_dan}::{self.ham}"


class _Bo(ast.NodeVisitor):
    def __init__(self, ten_cot: frozenset[str], duong_dan: str) -> None:
        self.ten_cot = ten_cot
        self.duong_dan = duong_dan
        self.ngan_xep: list[str] = []
        self.thay: list[ChoDoc] = []

    def _vao_ham(self, node: ast.AST) -> None:
        self.ngan_xep.append(node.name)  # type: ignore[attr-defined]
        self.generic_visit(node)
        self.ngan_xep.pop()

    visit_FunctionDef = _vao_ham  # noqa: N815
    visit_AsyncFunctionDef = _vao_ham  # noqa: N815
    visit_ClassDef = _vao_ham  # noqa: N815

    def visit_Attribute(self, node: ast.Attribute) -> None:  # noqa: N802
        if node.attr in self.ten_cot:
            self.thay.append(
                ChoDoc(
                    cot=node.attr,
                    duong_dan=self.duong_dan,
                    ham=".".join(self.ngan_xep) or "<cấp module>",
                    dong=node.lineno,
                )
            )
        self.generic_visit(node)


def quet_mot_file(duong_dan: Path, goc: Path, ten_cot: frozenset[str]) -> list[ChoDoc]:
    cay = ast.parse(duong_dan.read_text(encoding="utf-8"), filename=str(duong_dan))
    bo = _Bo(ten_cot, duong_dan.relative_to(goc).as_posix())
    bo.visit(cay)
    return bo.thay


def quet_ma_san_xuat(goc: Path, ten_cot_dac_trung: frozenset[str]) -> list[ChoDoc]:
    """Mọi chỗ mã sản xuất đọc một cột ĐẶC TRƯNG, sắp xếp tất định.

    Tất định là điều kiện để bộ sinh từ điển tái lập được từng ký tự — test
    khoá so chuỗi sinh lại với file trên đĩa, nên thứ tự `os.walk` (phụ thuộc
    hệ thống tệp) không được rò vào kết quả.
    """
    thay: list[ChoDoc] = []
    for thu_muc in THU_MUC_SAN_XUAT:
        for f in sorted((goc / thu_muc).rglob("*.py")):
            thay.extend(quet_mot_file(f, goc, ten_cot_dac_trung))
    return sorted(thay, key=lambda c: (c.cot, c.duong_dan, c.dong))
