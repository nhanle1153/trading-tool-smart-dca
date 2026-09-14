"""TD-0245 — dựng nội dung từ điển từ đĩa, và ghi ra `tu-dien-du-lieu.md`.

Tách khỏi `sinh_tu_dien.py` có chủ đích: ở đó là **hàm thuần** (vào: dữ liệu,
ra: chuỗi) nên test khoá gọi được mà không chạm hệ thống tệp; ở đây là phần
đọc artifact, quét mã, phân loại — tức phần **có tác dụng phụ**.

Chạy như một module, KHÔNG phải entrypoint thứ 9 (`L-Z36` khoá
`entrypoints/` ở đúng 8 file):

    docker compose -f docker/docker-compose.yml run --rm freqtrade \
        -m tool_d.tu_dien.ghi_tu_dien
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from tool_d.tu_dien.quet_cot import ChoDoc, la_ten_dac_trung, quet_ma_san_xuat
from tool_d.tu_dien.sinh_tu_dien import gop_dung_boi, sinh_noi_dung
from tool_d.tu_dien.y_nghia_cot import KHONG_PHAI_DOC_DB, TOOL_D_DOC_THEM, Y_NGHIA

REPO_ROOT = Path(__file__).resolve().parents[3]
FILE_ARTIFACT = REPO_ROOT / "docs/du-lieu-do/td0245-schema-sqlite-freqtrade.json"
FILE_TU_DIEN = REPO_ROOT / "tu-dien-du-lieu.md"

# Ngày khởi tạo từ điển. ĐÓNG BĂNG thay vì `date.today()`: nội dung file phải
# tất định để test khoá so được từng ký tự — lấy ngày hôm nay sẽ làm toàn bộ
# từ điển "đổi" mỗi nửa đêm mà không ai sửa gì.
NGAY_KHOI_TAO = date(2026, 9, 14).strftime("%d/%m/%Y")


def doc_artifact(duong_dan: Path = FILE_ARTIFACT) -> dict[str, Any]:
    if not duong_dan.is_file():
        raise FileNotFoundError(
            f"không thấy {duong_dan} — chạy "
            "docs/du-lieu-do/do_td0245_schema_sqlite_freqtrade.py trong Docker trước. "
            "Từ điển KHÔNG được viết từ trí nhớ (Quy tắc 8)"
        )
    return json.loads(duong_dan.read_text(encoding="utf-8"))


def cot_theo_bang(artifact: dict[str, Any]) -> dict[str, frozenset[str]]:
    return {b["ten"]: frozenset(c["ten"] for c in b["cot"]) for b in artifact["bang"]}


def ten_cot_dac_trung(artifact: dict[str, Any]) -> frozenset[str]:
    return frozenset(
        c["ten"] for b in artifact["bang"] for c in b["cot"] if la_ten_dac_trung(c["ten"])
    )


def quet_tat_ca(artifact: dict[str, Any], goc: Path = REPO_ROOT) -> list[ChoDoc]:
    """MỌI chỗ quét được, chưa phân loại.

    🔴 Đây mới là thứ `kiem_quy_tac_7()` cần. Truyền bản ĐÃ LỌC vào nó là một
    lỗi thật đã xảy ra khi viết TD-0245: các mục miễn trừ không bao giờ được
    đánh dấu "đã dùng" nên mục nào cũng bị báo `MIEN-TRU-CHET`. Lớp canh bắt
    được — nhưng nó bắt **người viết lớp canh**, không phải mã sản xuất, nên
    ghi lại ở đây để đường dùng đúng nằm ngay cạnh đường dùng sai.
    """
    return quet_ma_san_xuat(goc, ten_cot_dac_trung(artifact))


def quet_va_phan_loai(
    artifact: dict[str, Any], goc: Path = REPO_ROOT
) -> tuple[list[ChoDoc], list[ChoDoc]]:
    """Chia chỗ quét được thành (đọc DB, đã xét-không-phải-DB).

    Mọi chỗ khớp đều phải rơi vào đúng một trong hai rổ; cái nào không rơi vào
    rổ "không phải DB" thì mặc định là ĐỌC DB — fail-closed, vì bỏ sót một chỗ
    đọc thật nguy hơn là bắt khai thừa một chỗ.
    """
    thay = quet_tat_ca(artifact, goc)
    doc_db = [c for c in thay if (c.cot, c.duong_dan) not in KHONG_PHAI_DOC_DB]
    khong_phai = [c for c in thay if (c.cot, c.duong_dan) in KHONG_PHAI_DOC_DB]
    return doc_db, khong_phai


def dung_noi_dung(goc: Path = REPO_ROOT) -> str:
    artifact = doc_artifact(goc / "docs/du-lieu-do/td0245-schema-sqlite-freqtrade.json")
    doc_db, _ = quet_va_phan_loai(artifact, goc)
    return sinh_noi_dung(
        artifact=artifact,
        y_nghia=Y_NGHIA,
        dung_boi=gop_dung_boi(doc_db, cot_theo_bang(artifact), TOOL_D_DOC_THEM),
        ngay=NGAY_KHOI_TAO,
    )


def main() -> int:
    noi_dung = dung_noi_dung()
    FILE_TU_DIEN.write_text(noi_dung, encoding="utf-8")
    print(f"Đã ghi {FILE_TU_DIEN.relative_to(REPO_ROOT)} ({len(noi_dung.splitlines())} dòng)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
