"""TD-0391 (`DR-XAC-NHAN-01` §9) — hai mảnh logic THUẦN cho rổ `XAC_NHAN` tại ngày CHỌN.

Dùng CHUNG cho cả hai đường của phép đối chiếu (E7 `--ro-xac-nhan` và kịch bản đo lại `TD-0231`), để hai đường chỉ
khác nhau ở phần chọn rổ — cùng khuôn `t0`/`t1` (`DR-D1-03` §2), vốn cũng chung nguồn đọc.

1. `mo_rong_khoang()` — nguồn khoảng tồn tại (`TD-0306`) dừng ở tháng cuối của nó. Mã còn sống ở tháng đó (không có
   `moc_ngung`) được nối `thang_cuoi` tới tháng của mốc; còn sống THẬT tại mốc hay không do file ngày quyết (có ⇒
   sống; 404 ⇒ `khong_do_duoc.kho_404`). Mã niêm yết SAU nguồn thì không vào rổ được vì sàn tuổi — hàm từ chối khi
   điều đó không còn đúng (mốc quá xa nguồn).
2. `doc_volume_cho_moc()` — tháng của mốc đọc kho NGÀY (đúng ngày mốc), mọi tháng khác (ngày onboard sát ngưỡng)
   đọc kho THÁNG như cũ.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from tool_d.config.tran_von import SO_Y_TUONG, _ngay_chon_hieu_luc


class RoXacNhanError(ValueError):
    """Không dựng được rổ `XAC_NHAN` đúng quy ước §9 — fail-closed."""


def _thang_so(s: str) -> int:
    y, m = (int(x) for x in s.split("-"))
    return y * 12 + (m - 1)


def mo_rong_khoang(
    khoang: Mapping[str, Mapping[str, Any]], moc: date, *, age_floor_days: int
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """Trả `(khoảng đã nối, danh sách mã được nối)`. Không sửa `khoang` gốc."""
    co_du = [k["thang_cuoi"] for k in khoang.values() if k.get("thang_dau") and k.get("thang_cuoi")]
    if not co_du:
        raise RoXacNhanError("khoang_ton_tai rỗng — không dựng rổ trên 0 ứng viên")
    cuoi_nguon = max(co_du)
    thang_moc = f"{moc.year:04d}-{moc.month:02d}"
    ra = {s: dict(k) for s, k in khoang.items()}
    if _thang_so(thang_moc) <= _thang_so(cuoi_nguon):
        return ra, []
    y, m = (int(x) for x in cuoi_nguon.split("-"))
    dau_thang_sau = date(y + m // 12, m % 12 + 1, 1)
    if dau_thang_sau + timedelta(days=age_floor_days) <= moc:
        raise RoXacNhanError(
            f"mốc {moc} cách nguồn khoảng tồn tại (tháng cuối {cuoi_nguon}) quá xa: mã niêm yết từ {dau_thang_sau} đã có "
            f"thể đủ {age_floor_days} ngày tuổi mà nguồn không biết tới — đo lại khoảng tồn tại trước (DR-XAC-NHAN-01 §9)"
        )
    noi: list[str] = []
    for s, k in ra.items():
        if k.get("thang_cuoi") == cuoi_nguon and k.get("thang_dau") and not k.get("moc_ngung"):
            k["thang_cuoi"] = thang_moc
            noi.append(s)
    return ra, sorted(noi)


def doc_volume_cho_moc(
    moc: date,
    *,
    doc_ngay: Callable[[str, date], Mapping[date, float]],
    doc_thang: Callable[[str, int, int], Mapping[date, float]],
) -> Callable[[str, int, int], Mapping[date, float]]:
    """Bộ đọc cùng chữ ký `doc_volume_thang` của `dung_ro_tai_moc()`."""

    def doc(sym: str, nam: int, thang: int) -> Mapping[date, float]:
        if (nam, thang) == (moc.year, moc.month):
            return doc_ngay(sym, moc)
        return doc_thang(sym, nam, thang)

    return doc


def lan_chon(slot: str, repo_dir: Path) -> tuple[date, str]:
    """`(ngày mốc, selected_at nguyên văn)` của lần CHỌN còn hiệu lực. Ngày mốc đi qua đúng hàm của cổng trần vốn
    (`tran_von._ngay_chon_hieu_luc`) để hai nơi không đọc sổ ý tưởng theo hai cách."""
    from tool_d.ledger.idea_events import duyet_so

    ngay = _ngay_chon_hieu_luc(slot, repo_dir)
    if isinstance(ngay, str):
        raise RoXacNhanError(ngay)
    dong = [json.loads(x) for x in (repo_dir / SO_Y_TUONG).read_text(encoding="utf-8").splitlines() if x.strip()]
    chon = [e for e in duyet_so(dong).chon_hieu_luc if e.get("idea_id") == slot]
    tho = str(chon[-1]["selected_at"])
    if datetime.strptime(tho, "%Y-%m-%dT%H:%M:%SZ").date() != ngay:  # hai lần đọc phải cùng một lần CHỌN
        raise RoXacNhanError(f"{slot}: selected_at {tho!r} lệch ngày mốc {ngay}")
    return ngay, tho
