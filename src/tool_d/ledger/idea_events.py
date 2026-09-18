"""Sổ ý tưởng là nhật ký sự kiện (DR-IQ-02) — dựng trạng thái hiện hành từ các dòng.

Hàm THUẦN trên danh sách dòng đã đọc: không đọc file, không import `audit_checks`
(nó import ngược lại module này). Cửa ghi (`idea_queue.py`) và phép kiểm sổ
(`audit_checks.py`) dùng CHUNG một hàm `duyet_so()`, để hai lớp không thể lệch
luật nhau.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# DR-IQ-02 §4.2 — mọi sự kiện sau dòng đầu phải mang y hệt các trường này.
TRUONG_NOP = (
    "source",
    "session_type",
    "data_source",
    "explore_evidence",
    "title",
    "mechanism",
    "who_pays",
    "durability",
    "phep_thu_du_kien",
    "filter_verdict",
    "overlaps_with",
    "created_at",
)

# DR-IQ-02 §4.1 — trạng thái hiện hành → sự kiện được phép tiếp theo.
# `None` = mã chưa có dòng nào. REJECTED/ARCHIVED là trạng thái cuối.
CHUYEN_HOP_LE: dict[str | None, frozenset[str]] = {
    None: frozenset({"QUEUED", "REJECTED"}),
    "QUEUED": frozenset({"SELECTED", "ARCHIVED"}),
    "SELECTED": frozenset({"VOIDED", "ARCHIVED"}),
}
# VOIDED đưa mã về lại hàng chờ.
TRANG_THAI_SAU = {"VOIDED": "QUEUED"}

SO_LAN_HUY_TOI_DA = 1  # DR-IQ-02 §4.3 điều 3, cùng khuôn giới hạn REFUND của sổ trial

DR_CODE_RE = re.compile(r"\bDR-[A-Z0-9]+(?:-[A-Z0-9]+)*")


def dr_co_that(ly_do: str, decisions_dir: Path) -> list[str]:
    """Các mã DR được trích trong `ly_do` mà CÓ file thật trong `decisions_dir`."""
    ma = DR_CODE_RE.findall(ly_do or "")
    if not decisions_dir.is_dir():
        return []
    ten = [p.name for p in decisions_dir.iterdir() if p.suffix == ".md"]
    return [m for m in ma if any(t == f"{m}.md" or t.startswith(f"{m}-") for t in ten)]


@dataclass
class KetQuaDuyet:
    trang_thai: dict[str, str] = field(default_factory=dict)
    dong_dau: dict[str, dict[str, Any]] = field(default_factory=dict)
    # Dòng SELECTED còn hiệu lực, theo thứ tự trong sổ.
    chon_hieu_luc: list[dict[str, Any]] = field(default_factory=list)
    # Dòng SELECTED đã bị một VOIDED huỷ — chỉ còn là dấu vết (§4.1).
    chon_da_huy: list[dict[str, Any]] = field(default_factory=list)
    so_lan_huy: Counter[str] = field(default_factory=Counter)
    vi_pham: list[str] = field(default_factory=list)


def duyet_so(
    entries: list[dict[str, Any]],
    *,
    decisions_dir: Path | None = None,
    slot_da_dung: set[str] | None = None,
) -> KetQuaDuyet:
    """Đọc lần lượt từng dòng, dựng trạng thái, gom mọi vi phạm luật DR-IQ-02.

    Dòng chuyển trạng thái SAI vẫn được ÁP (kèm vi phạm) chứ không bị bỏ qua:
    một dòng SELECTED thêm tay không qua cửa NỘP vẫn phải chịu mọi phép kiểm
    của lần chọn — bỏ qua nó là giấu một lần chọn đi.

    `decisions_dir` / `slot_da_dung` không truyền thì bỏ qua hai điều kiện
    của VOIDED cần đọc đĩa (DR có thật; không trial nào mang mã).
    """
    kq = KetQuaDuyet()
    # Vi phạm "trường nộp lệch" của một dòng SELECTED chỉ được chốt khi dòng đó
    # không bị huỷ về sau (§4.1: dòng đã huỷ chỉ còn là dấu vết).
    cho_chot: dict[int, list[str]] = {}
    chon_hien_tai: dict[str, int] = {}

    for k, e in enumerate(entries):
        ma = e.get("idea_id")
        st = e.get("status")
        vi_tri = f"{ma} (dòng {k + 1}, {st})"
        hien_tai = kq.trang_thai.get(ma)

        if st not in CHUYEN_HOP_LE.get(hien_tai, frozenset()):
            kq.vi_pham.append(
                f"{vi_tri}: không được ghi khi đang {hien_tai or 'chưa có dòng nào'}"
            )

        lech: list[str] = []
        if ma not in kq.dong_dau:
            kq.dong_dau[ma] = e
        else:
            dau = kq.dong_dau[ma]
            lech = [f for f in TRUONG_NOP if e.get(f) != dau.get(f)]
        loi_lech = (
            [f"{vi_tri}: trường nộp khác dòng đầu {lech} — muốn sửa ý tưởng thì nộp đơn mới"]
            if lech
            else []
        )

        if st == "SELECTED":
            kq.chon_hieu_luc.append(e)
            chon_hien_tai[ma] = k
            cho_chot[k] = loi_lech
        elif st == "VOIDED" and hien_tai == "SELECTED":
            kq.vi_pham.extend(loi_lech)
            k_bi_huy = chon_hien_tai.pop(ma)
            bi_huy = entries[k_bi_huy]
            cho_chot.pop(k_bi_huy, None)
            kq.chon_hieu_luc = [x for x in kq.chon_hieu_luc if x is not bi_huy]
            kq.chon_da_huy.append(bi_huy)
            kq.so_lan_huy[ma] += 1
            kq.vi_pham.extend(_kiem_voided(e, bi_huy, kq.so_lan_huy[ma], vi_tri,
                                           decisions_dir, slot_da_dung))
        else:
            kq.vi_pham.extend(loi_lech)

        kq.trang_thai[ma] = TRANG_THAI_SAU.get(st, st)

    for loi in cho_chot.values():
        kq.vi_pham.extend(loi)
    return kq


def _kiem_voided(
    e: dict[str, Any],
    bi_huy: dict[str, Any],
    lan_thu: int,
    vi_tri: str,
    decisions_dir: Path | None,
    slot_da_dung: set[str] | None,
) -> list[str]:
    loi: list[str] = []
    if e.get("selected_at") != bi_huy.get("selected_at"):
        loi.append(f"{vi_tri}: selected_at không chỉ đích danh lần chọn bị huỷ")
    if not e.get("voided_at"):
        loi.append(f"{vi_tri}: thiếu voided_at")
    if lan_thu > SO_LAN_HUY_TOI_DA:
        loi.append(f"{vi_tri}: huỷ lần {lan_thu} > tối đa {SO_LAN_HUY_TOI_DA}/mã")
    if decisions_dir is not None and not dr_co_that(e.get("void_reason") or "", decisions_dir):
        loi.append(f"{vi_tri}: void_reason không trích DR nào có thật trong {decisions_dir}")
    if slot_da_dung is not None and e.get("idea_id") in slot_da_dung:
        loi.append(
            f"{vi_tri}: đã có trial mang hypothesis_slot={e.get('idea_id')} — "
            "không được huỷ một lần chọn đã tiêu ngân sách N"
        )
    return loi
