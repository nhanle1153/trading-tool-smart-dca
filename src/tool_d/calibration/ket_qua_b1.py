"""TD-0257 (Việc 2) — tính lại quyết định D5 từ SỔ + `lenh_r.json`, không nhận lời khai.

Trước file này không có hiện vật nào ghi *"tham số nào đổi, tham số nào giữ mốc"*: `chon_gia_tri.py` có luật
nhưng không ai gọi nó trên dữ liệu thật và lưu kết quả. Cổng D5 cần đúng câu trả lời đó (`DR-D5-01` §7:
*"tham số nào INCONCLUSIVE giữ mốc"*). Ở đây cổng **tính lại** mỗi lần chạy thay vì đọc một file kết quả —
một file trung gian là một thứ có thể trôi khỏi dữ liệu nó mô tả (bài học `TD-0168`: thứ được canh phải nằm
trên đường chạy thật, và `MT-10`: máy đọc, không nhận lời khai).

Hàm THUẦN theo nghĩa không ghi gì: đọc bản chiếu sổ (truyền vào) và `runs/<trial_id>/lenh_r.json`.

════ Ba chỗ diễn giải, ghi ra để cãi lại được ════

1. **Thước = `r_trien_khai`.** `DR-D5-01` §5 ghi đơn vị là *"theo rủi ro đã triển khai (`DR-D4-12` §1)"*; docstring của
   `chon_gia_tri.py` gọi đầu vào là *"R_realized"*. DR thắng (N1). Cùng thước E1 đưa vào `outcome.expectancy`.
2. **Thứ tự lỏng → chặt của nhóm LỌC LỆNH** chép từ bảng `DR-D5-01` §5.2 vào `THU_TU_LONG_DEN_CHAT`, và được
   ĐỐI CHIẾU với bảng ứng viên đã băm lúc chạy: tập giá trị lệch nhau ⇒ `KetQuaB1Error` (DR đổi mà hằng này
   không đổi theo thì không được âm thầm dùng thứ tự cũ).
3. **`BO_DIEU_KIEN_C` (`v_min` *"0 thắng"*) KHÔNG áp được qua đường này.** §3.1: bỏ (c) *"đi qua một thay đổi
   riêng có test, không lọt vào YAML dưới dạng một số"*. Quyết định đó được ghi, nhưng tính là **chưa áp dụng
   được** — tầng cổng coi nó là lý do từ chối, không phải một giá trị mới.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from tool_d.calibration.bang_r import TEN_FILE, BangRError, doc_bang_r
from tool_d.calibration.chon_gia_tri import (
    HanhDong,
    KetQuaXacNhan,
    QuyetDinh,
    chon_ket_cuc,
    chon_loc_lenh,
    so_ket_cuc,
    so_loc_lenh,
    xac_nhan_ghep,
)
from tool_d.calibration.ung_vien import (
    BUDGET_LINE_B1,
    PARAM_MOC,
    PARAM_XAC_NHAN,
    BangUngVien,
    _la_calib,
    cung_gia_tri,
)

#: `DR-D5-01` §2.1 — tên hai nhóm như trong khối ứng viên đã băm.
NHOM_KET_CUC = "KET_CUC"
NHOM_LOC_LENH = "LOC_LENH"

#: `DR-D5-01` §5.2 (bảng *"Thứ tự lỏng → chặt"*). Đối chiếu với bảng ứng viên lúc chạy — xem docstring mô-đun.
THU_TU_LONG_DEN_CHAT: dict[str, tuple[float, ...]] = {
    "zss_threshold": (0.4, 0.5, 0.6),
    "v_min": (0.0, 1.0, 1.5),
    "wick_close_upper_frac": (0.5, 0.6, 0.67),
}

#: `DR-D5-01` §3.1 — giá trị mà *"thắng"* nghĩa là BỎ điều kiện (c), không phải một số mới.
GIA_TRI_TAT: dict[str, float] = {"v_min": 0.0}

#: Thước đọc từ `lenh_r.json` — diễn giải 1.
THUOC = "r_trien_khai"


class KetQuaB1Error(ValueError):
    """Đầu vào không khớp DR (bảng ứng viên đổi mà hằng thứ tự không đổi, nhóm lạ…) — lỗi CÀI ĐẶT, không phải
    một kết quả đo."""


@dataclass(frozen=True)
class KetQuaB1:
    """Kết quả D5 tính lại từ sổ. Không có trường nào nhận từ người khai."""

    moc_trial: str | None
    so_lenh_moc: int | None
    quyet_dinh: dict[str, QuyetDinh]
    """Tham số → quyết định, CHỈ cho tham số tính được. Tham số thiếu dữ liệu nằm ở `thieu`."""
    thieu: dict[str, str]
    """Tham số (hoặc `D5_MOC`/`D5_XAC_NHAN`) → vì sao chưa tính được. N6: thiếu không bao giờ là *"giữ mốc"*."""
    xac_nhan_trial: str | None = None
    xac_nhan: KetQuaXacNhan | None = None
    gia_tri_xac_nhan: dict[str, Any] | None = None
    """`param_value` của suất `D5_XAC_NHAN` (dict khoá → giá trị) đọc từ sổ."""
    han_che: tuple[str, ...] = field(default=())

    def tham_so_doi(self) -> dict[str, Any]:
        """Tham số mà luật §5 nói ĐỔI (chưa xét xác nhận ghép)."""
        return {k: q.gia_tri for k, q in self.quyet_dinh.items() if q.hanh_dong is HanhDong.DOI}

    def tham_so_bo_c(self) -> list[str]:
        return [k for k, q in self.quyet_dinh.items() if q.hanh_dong is HanhDong.BO_DIEU_KIEN_C]

    def tham_so_giu_moc(self) -> dict[str, str]:
        """Tham số giữ mốc, kèm lý do — gồm cả GIU_MOC lẫn PENDING (`DR-D5-01` §7: *"giữ mốc"* = không phân
        biệt được, không phải *"đã chứng minh tốt nhất"*)."""
        return {
            k: f"{q.hanh_dong.value}: {q.ly_do}"
            for k, q in self.quyet_dinh.items()
            if q.hanh_dong in (HanhDong.GIU_MOC, HanhDong.PENDING)
        }

    def gia_tri_cuoi(self, bang: BangUngVien) -> dict[str, Any]:
        """Giá trị PHẢI chạy sau D5, theo §5.3: xác nhận ghép ĐẠT ⇒ áp mọi giá trị đổi; còn lại ⇒ TOÀN BỘ mốc."""
        cuoi = {k: ts.moc for k, ts in bang.tham_so.items()}
        if self.tham_so_doi() and self.xac_nhan is not None and self.xac_nhan.xac_nhan is True:
            cuoi.update(self.tham_so_doi())
        return cuoi


def _suat_b1_calib(proj: Iterable[Any]) -> list[Any]:
    from tool_d.ledger.registry import TrialState

    return [
        p for p in proj
        if p.budget_line == BUDGET_LINE_B1 and _la_calib(p) and p.state is TrialState.CONSUMED
    ]


def _doc_r(runs_dir: Path, trial_id: str) -> tuple[dict[tuple[str, datetime], float] | None, str | None]:
    try:
        return doc_bang_r(runs_dir / trial_id / TEN_FILE, thuoc=THUOC), None
    except BangRError as e:
        return None, f"{trial_id}: {e}"


def _kiem_thu_tu(bang: BangUngVien) -> None:
    for ten, ts in bang.tham_so.items():
        if ts.nhom not in (NHOM_KET_CUC, NHOM_LOC_LENH):
            raise KetQuaB1Error(f"{ten}: nhóm {ts.nhom!r} không thuộc DR-D5-01 §2.1")
        if ts.nhom != NHOM_LOC_LENH:
            continue
        tt = THU_TU_LONG_DEN_CHAT.get(ten)
        tap_dr = [ts.moc, *ts.thu]
        if tt is None or len(tt) != len(tap_dr) or not all(any(cung_gia_tri(a, b) for b in tt) for a in tap_dr):
            raise KetQuaB1Error(
                f"{ten}: thứ tự lỏng→chặt {tt!r} không khớp bảng ứng viên {tap_dr!r} — DR-D5-01 §5.2 đổi mà "
                "THU_TU_LONG_DEN_CHAT chưa đổi theo"
            )


def tinh_quyet_dinh_b1(proj: Iterable[Any], *, runs_dir: Path, bang: BangUngVien) -> KetQuaB1:
    """Tính lại quyết định của MỌI tham số trong bảng ứng viên từ các suất B1 CALIB đã CONSUMED."""
    _kiem_thu_tu(bang)
    suat = _suat_b1_calib(proj)
    thieu: dict[str, str] = {}
    han_che: list[str] = []

    moc = [p for p in suat if p.param_under_test == PARAM_MOC]
    if len(moc) != 1:
        thieu[PARAM_MOC] = f"cần đúng 1 suất {PARAM_MOC} CONSUMED, thấy {len(moc)}"
        return KetQuaB1(moc_trial=None, so_lenh_moc=None, quyet_dinh={}, thieu=thieu)
    moc_tid = moc[0].trial_id
    r_moc, loi = _doc_r(runs_dir, moc_tid)
    if r_moc is None:
        thieu[PARAM_MOC] = f"không đọc được bảng thước của mốc — {loi}"
        return KetQuaB1(moc_trial=moc_tid, so_lenh_moc=None, quyet_dinh={}, thieu=thieu)

    # (tham số, giá trị) → bảng thước; trùng suất cho cùng (tham số, giá trị) là lỗi kế toán, không lấy suất nào.
    r_thu: dict[str, list[tuple[Any, dict]]] = {}
    for p in suat:
        if p.param_under_test in (PARAM_MOC, PARAM_XAC_NHAN):
            continue
        if p.param_under_test not in bang.tham_so:
            thieu[p.param_under_test] = f"{p.trial_id}: tham số không thuộc bảng ứng viên DR-D5-01"
            continue
        r, loi = _doc_r(runs_dir, p.trial_id)
        if r is None:
            thieu[p.param_under_test] = f"không đọc được bảng thước — {loi}"
            continue
        ds = r_thu.setdefault(p.param_under_test, [])
        if any(cung_gia_tri(v, p.param_value) for v, _ in ds):
            thieu[p.param_under_test] = f"hai suất cho cùng giá trị {p.param_value!r}"
            continue
        ds.append((p.param_value, r))

    quyet_dinh: dict[str, QuyetDinh] = {}
    for ten, ts in sorted(bang.tham_so.items()):
        if ten in thieu:
            continue
        co = r_thu.get(ten, [])
        thieu_gia_tri = [v for v in ts.thu if not any(cung_gia_tri(v, x) for x, _ in co)]
        if ts.nhom == NHOM_KET_CUC:
            if thieu_gia_tri:
                thieu[ten] = f"thiếu suất cho giá trị {thieu_gia_tri!r}"
                continue
            kq = {v: so_ket_cuc(r_moc=r_moc, r_thu=r) for v, r in co}
            quyet_dinh[ten] = chon_ket_cuc(moc=ts.moc, ket_qua=kq)
            for v, k in kq.items():
                if k.mau_thuan:
                    han_che.append(f"{ten}={v!r}: phép giao nói thắng, phần chênh nói thua ⇒ giữ mốc (§5.1)")
        else:
            tt = THU_TU_LONG_DEN_CHAT[ten]
            theo_gt = {ts.moc: r_moc, **{v: r for v, r in co}}

            def _r(v: Any) -> dict | None:
                return next((r for x, r in theo_gt.items() if cung_gia_tri(x, v)), None)

            so_sanh = {}
            for a, b in zip(tt, tt[1:]):
                ra, rb = _r(a), _r(b)
                if ra is not None and rb is not None:
                    so_sanh[(a, b)] = so_loc_lenh(r_long=ra, r_chat=rb)
            moc_tt = next(v for v in tt if cung_gia_tri(v, ts.moc))
            try:
                quyet_dinh[ten] = chon_loc_lenh(
                    thu_tu_long_den_chat=tt, moc=moc_tt, so_sanh=so_sanh, gia_tri_tat=GIA_TRI_TAT.get(ten)
                )
            except ValueError as e:  # `ChonGiaTriError` — thiếu phép so cho một cặp kề mà luật cần xét
                thieu[ten] = f"thiếu suất để xét bước kế tiếp — {e}"
                continue
            for cap, k in so_sanh.items():
                if k.n_chi_o_chat > 0:
                    han_che.append(f"{ten} {cap!r}: {k.n_chi_o_chat} lệnh chỉ ở giá trị chặt — không lồng nhau (§5.2)")

    xn = [p for p in suat if p.param_under_test == PARAM_XAC_NHAN]
    xn_tid = xn_kq = xn_gt = None
    if len(xn) > 1:
        thieu[PARAM_XAC_NHAN] = f"{len(xn)} suất {PARAM_XAC_NHAN} — trần là 1 (§4)"
    elif xn:
        xn_tid, xn_gt = xn[0].trial_id, xn[0].param_value
        r_ghep, loi = _doc_r(runs_dir, xn_tid)
        if r_ghep is None:
            thieu[PARAM_XAC_NHAN] = f"không đọc được bảng thước — {loi}"
        else:
            xn_kq = xac_nhan_ghep(r_moc=r_moc, r_ghep=r_ghep)
            han_che.extend(xn_kq.han_che)

    return KetQuaB1(
        moc_trial=moc_tid,
        so_lenh_moc=len(r_moc),
        quyet_dinh=quyet_dinh,
        thieu=thieu,
        xac_nhan_trial=xn_tid,
        xac_nhan=xn_kq,
        gia_tri_xac_nhan=xn_gt if isinstance(xn_gt, dict) else None,
        han_che=tuple(han_che),
    )


__all__ = [
    "GIA_TRI_TAT",
    "KetQuaB1",
    "KetQuaB1Error",
    "THU_TU_LONG_DEN_CHAT",
    "THUOC",
    "tinh_quyet_dinh_b1",
]
