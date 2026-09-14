"""TD-0245 — Quy tắc 7 thành MÁY: không được đọc một cột chưa tra từ điển.

Cho tới TD-0245, Quy tắc 7 (`CLAUDE.md:25`) chỉ là chữ trong tài liệu. Dự án
đã học nhiều lần rằng chữ không tự thi hành: `MT-08` (chính sách `CTRL` chốt
ở năm chỗ trong spec mà `registry.py` vẫn cộng sai suốt nhiều ngày),
`L-Z26`/`TD-0125` (luật đổi tham số viết rất chặt, **0 dòng code**). Module
này là phần thi hành.

🔴 **Vì sao trả về DANH SÁCH vi phạm chứ không `bool`:** một lớp canh nói
"sai" mà không nói sai ở đâu thì lần đầu ai đó gặp nó sẽ đi tìm cách tắt, chứ
không đi tìm cách sửa. Cùng lý do `kiem_san_tool_d()` của `DR-D4-05` trả lý do
đọc được thay vì `bool`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from tool_d.tu_dien.quet_cot import ChoDoc


@dataclass(frozen=True)
class ViPham:
    ma: str
    chi_tiet: str

    def __str__(self) -> str:  # pragma: no cover - chỉ để thông báo lỗi dễ đọc
        return f"[{self.ma}] {self.chi_tiet}"


def _cot_theo_bang(artifact: Mapping[str, Any]) -> dict[str, frozenset[str]]:
    return {b["ten"]: frozenset(c["ten"] for c in b["cot"]) for b in artifact["bang"]}


def kiem_quy_tac_7(
    *,
    artifact: Mapping[str, Any],
    y_nghia: Mapping[tuple[str, str], Any],
    tool_d_doc_them: Mapping[tuple[str, str], Sequence[str]],
    khong_phai_doc_db: Mapping[tuple[str, str], str],
    cho_doc: Sequence[ChoDoc],
) -> list[ViPham]:
    """Mọi vi phạm Quy tắc 7 tìm được. Rỗng = sạch.

    Năm phép kiểm, mỗi phép đóng một đường lách khác nhau:

    * `KHONG-CO-COT`  — từ điển/đăng ký nhắc một cột **không tồn tại** trong
      schema đo được. Đây là ca Quy tắc 7 sợ nhất: một cái tên nhớ nhầm hoặc
      đã bị Freqtrade đổi, mà mã vẫn đọc.
    * `DOC-COT-CHUA-TRA` — mã sản xuất đọc một cột chưa có nghĩa trong từ điển.
    * `KHAI-DOC-CHUA-TRA` — đăng ký khai là có đọc, nhưng cột vẫn `⏳`.
    * `MIEN-TRU-CHET` — một mục miễn trừ không còn khớp chỗ nào. Danh sách
      miễn trừ mà không ai dọn thì sớm muộn che mất một ca thật; bắt nó chết là
      cách duy nhất giữ cửa hẹp mãi hẹp.
    * `MIEN-TRU-THIEU-LY-DO` — miễn trừ không kèm lý do đọc được thì không
      khác gì tắt lớp canh.
    """
    theo_bang = _cot_theo_bang(artifact)
    moi_cot: set[str] = set()
    for cot in theo_bang.values():
        moi_cot |= cot

    vi_pham: list[ViPham] = []

    for bang, cot in sorted(set(y_nghia) | set(tool_d_doc_them)):
        if bang not in theo_bang:
            vi_pham.append(
                ViPham("KHONG-CO-COT", f"bảng {bang!r} không có trong schema đo được")
            )
        elif cot not in theo_bang[bang]:
            vi_pham.append(
                ViPham("KHONG-CO-COT", f"{bang}.{cot} không có trong schema đo được")
            )

    for khoa in sorted(tool_d_doc_them):
        if khoa not in y_nghia:
            vi_pham.append(
                ViPham(
                    "KHAI-DOC-CHUA-TRA",
                    f"{khoa[0]}.{khoa[1]} được khai là Tool D có đọc, nhưng chưa có "
                    "nghĩa trong y_nghia_cot.Y_NGHIA",
                )
            )

    da_dung_mien_tru: set[tuple[str, str]] = set()
    for c in cho_doc:
        khoa_mt = (c.cot, c.duong_dan)
        if khoa_mt in khong_phai_doc_db:
            da_dung_mien_tru.add(khoa_mt)
            continue
        for bang, cot in theo_bang.items():
            if c.cot in cot and (bang, c.cot) not in y_nghia:
                vi_pham.append(
                    ViPham(
                        "DOC-COT-CHUA-TRA",
                        f"{c.duong_dan}::{c.ham} (dòng {c.dong}) đọc {bang}.{c.cot} "
                        "nhưng cột đó chưa tra trong tu-dien-du-lieu.md",
                    )
                )

    for khoa_mt, ly_do in sorted(khong_phai_doc_db.items()):
        if khoa_mt not in da_dung_mien_tru:
            vi_pham.append(
                ViPham(
                    "MIEN-TRU-CHET",
                    f"miễn trừ {khoa_mt[0]!r} ở {khoa_mt[1]!r} không còn khớp chỗ nào "
                    "— xoá nó đi, đừng để danh sách miễn trừ phình ra",
                )
            )
        if not ly_do.strip():
            vi_pham.append(
                ViPham(
                    "MIEN-TRU-THIEU-LY-DO",
                    f"miễn trừ {khoa_mt[0]!r} ở {khoa_mt[1]!r} không có lý do",
                )
            )

    return sorted(vi_pham, key=lambda v: (v.ma, v.chi_tiet))
