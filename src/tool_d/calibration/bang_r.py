"""TD-0255 — bảng `r_trien_khai` THEO TỪNG LỆNH của một suất: cầu nối giữa E1 và `chon_gia_tri` (TD-0254).

`chon_gia_tri` so hai suất theo khoá `(pair, giờ mở)` (`DR-D5-01` §5). Để làm được việc đó SAU khi các suất đã chạy
xong, mỗi suất phải để lại `r_trien_khai` của TỪNG lệnh — không chỉ trung bình. E1 ghi file này sau con dấu (`L-Z53`); tầng đánh
giá D5 chỉ đọc file, không chạy lại gì.

Hai thước cạnh nhau, không phán xét (`DR-D4-12` §1.3): `r_trien_khai` (đơn vị phán quyết của `DR-D5-01` §5 —
*"R_realized theo rủi ro đã triển khai"*) và `r_realized` (mẫu số `planned_risk_usdt`). ⚠️ Docstring `chon_gia_tri.py:3` viết
*"`R_realized` theo lệnh"* — lệch chữ với `DR-D5-01` §5; tầng đánh giá đọc `r_trien_khai` theo DR (N1: spec/DR
thắng), và chỗ lệch được GHI LẠI chứ không sửa âm thầm.
"""

from __future__ import annotations

import json
import math
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

from tool_d.wfo.lenh import LenhWFO

TEN_FILE = "lenh_r.json"
THUOC_HOP_LE = ("r_trien_khai", "r_realized")


class BangRError(ValueError):
    """File bảng `r_trien_khai` hỏng, trùng khoá, hoặc thước lạ — fail-closed."""


def bang_r(lenhs: Sequence[LenhWFO]) -> list[dict[str, Any]]:
    """Mỗi lệnh một dòng, sắp theo `(open_date, pair)` — tất định, diff được giữa hai lần chạy."""
    ra = [
        {
            "pair": l.pair,
            "open_date": l.open_date.isoformat(),
            "close_date": l.close_date.isoformat(),
            "pnl_abs": l.pnl_abs,
            "r_trien_khai": l.r_trien_khai,
            "r_realized": l.r_realized,
        }
        for l in lenhs
    ]
    ra.sort(key=lambda d: (d["open_date"], d["pair"]))
    return ra


def ghi_bang_r(thu_muc: Path, lenhs: Sequence[LenhWFO], *, trial_id: str) -> Path:
    thu_muc.mkdir(parents=True, exist_ok=True)
    duong = thu_muc / TEN_FILE
    noi_dung = {"trial_id": trial_id, "so_lenh": len(lenhs), "lenh": bang_r(lenhs)}
    duong.write_text(json.dumps(noi_dung, indent=1, ensure_ascii=False), encoding="utf-8")
    return duong


def doc_bang_r(duong: Path, *, thuoc: str = "r_trien_khai") -> dict[tuple[str, datetime], float]:
    """`{(pair, giờ mở): giá trị thước}` — đúng hình `chon_gia_tri` nhận. Trùng khoá ⇒ raise: hai lệnh cùng mã cùng giờ mở là
    dữ liệu hỏng, không phải hai mẫu."""
    if thuoc not in THUOC_HOP_LE:
        raise BangRError(f"thước {thuoc!r} không thuộc {THUOC_HOP_LE}")
    try:
        noi_dung = json.loads(duong.read_text(encoding="utf-8"))
        dong = noi_dung["lenh"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise BangRError(f"{duong}: không đọc được bảng thước: {exc}") from exc
    if noi_dung.get("so_lenh") != len(dong):
        raise BangRError(f"{duong}: so_lenh {noi_dung.get('so_lenh')} khác {len(dong)} dòng")
    ra: dict[tuple[str, datetime], float] = {}
    for d in dong:
        khoa = (d["pair"], datetime.fromisoformat(d["open_date"]))
        if khoa in ra:
            raise BangRError(f"{duong}: trùng khoá {khoa}")
        r = d[thuoc]
        if not isinstance(r, (int, float)) or isinstance(r, bool) or not math.isfinite(r):
            raise BangRError(f"{duong}: {khoa} có {thuoc} không hữu hạn: {r!r}")
        ra[khoa] = float(r)
    return ra


__all__ = ["TEN_FILE", "BangRError", "bang_r", "doc_bang_r", "ghi_bang_r"]
