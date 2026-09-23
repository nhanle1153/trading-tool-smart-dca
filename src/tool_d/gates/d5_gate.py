"""TD-0257 (Việc 3) — tiêu chí đóng cổng D5, khuôn `gates/d4_gate.py`.

Trả **lý do từ chối đọc được**, không trả `bool`. Kiểm **quan hệ**, không kiểm hằng số: số suất B1 so với
trần của bảng ứng viên đã băm, quyết định tính lại (`calibration/ket_qua_b1.py`) so với `param_status.yaml`.
Luật lấy từ `DR-D5-01`; module này KHÔNG khai lại luật chọn giá trị — nó gọi kết quả của `tinh_quyet_dinh_b1()`.

🔴 Hành vi mong đợi trên sổ thật hôm nay (`DR-ZA-01` §5, viết TRƯỚC): TỪ CHỐI — 0 suất `D5_MOC`, vì D5 của
Zone Absorption LONG không tiêu suất nào (`DR-ZA-01` §2, khoá `D5_DO_TAM_DUNG`). Đó là cổng làm đúng việc.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from tool_d.calibration.ket_qua_b1 import KetQuaB1
from tool_d.calibration.ung_vien import PARAM_MOC, PARAM_XAC_NHAN, BangUngVien, cung_gia_tri

#: `DR-D5-01` §2.2 — năm tham số KHÔNG calibrate ở D5 (bốn *"bất khả"* + `mult_corr_thresholds`). Dòng `TD-0257`
#: trong `TASKS.md` ghi *"bốn"*; DR ghi năm và DR thắng (N1).
THAM_SO_KHONG_CALIBRATE: frozenset[str] = frozenset(
    {"dg4_bars_1h", "dg6a_atr_ratio", "dg6d_retrace_frac", "funding_rate_pct", "mult_corr_thresholds"}
)

#: `DR-D5-01` §4 — trần hạ còn 15 khi `TD-0251` báo không lệnh mốc nào giữ đủ 24 nến.
TRAN_KHI_KHONG_LENH_GIU_DU = 15


class D5GateError(TypeError):
    """Đầu vào sai KIỂU — khác với *"chưa đủ điều kiện"*."""


def kiem_tieu_chi_dong_d5(
    *,
    ket_qua: KetQuaB1,
    bang: BangUngVien,
    so_b1_calib_consumed: int,
    param_status: Mapping[str, Mapping[str, Any]],
    co_lenh_moc_giu_du: bool | None = None,
) -> list[str]:
    """Danh sách LÝ DO TỪ CHỐI đóng cổng D5. Rỗng = đủ điều kiện.

    :param ket_qua: kết quả tính lại từ sổ (`tinh_quyet_dinh_b1`).
    :param bang: bảng ứng viên đã kiểm băm (`doc_bang_ung_vien`).
    :param so_b1_calib_consumed: số suất B1 trên CALIB đã CONSUMED, đếm từ sổ.
    :param param_status: mục `params` của `config/param_status.yaml`.
    :param co_lenh_moc_giu_du: kết quả `TD-0251` — `False` ⇒ trần 15. `None` = chưa đo ⇒ trần của bảng (16),
        và tầng gọi phải ghi điều đó vào hạn chế.
    """
    if not isinstance(ket_qua, KetQuaB1):
        raise D5GateError(f"ket_qua phải là KetQuaB1, nhận {type(ket_qua)!r}")
    if not isinstance(so_b1_calib_consumed, int) or isinstance(so_b1_calib_consumed, bool):
        raise D5GateError(f"so_b1_calib_consumed phải là số nguyên, nhận {so_b1_calib_consumed!r}")
    if not isinstance(param_status, Mapping):
        raise D5GateError(f"param_status phải là mapping, nhận {type(param_status)!r}")

    loi: list[str] = []

    # §4 + §6.3 — mốc.
    for ten, ly_do in sorted(ket_qua.thieu.items()):
        loi.append(f"{ten}: chưa tính được — {ly_do}")
    if ket_qua.so_lenh_moc == 0:
        loi.append(f"{PARAM_MOC} có 0 lệnh — DR-D5-01 §6.3: DỪNG D5")

    # §4 — trần.
    tran = TRAN_KHI_KHONG_LENH_GIU_DU if co_lenh_moc_giu_du is False else bang.tran_suat
    if so_b1_calib_consumed > tran:
        loi.append(f"{so_b1_calib_consumed} suất B1 CALIB CONSUMED > trần {tran} (DR-D5-01 §4)")

    if ket_qua.moc_trial is None or ket_qua.so_lenh_moc is None:
        return loi  # không có mốc thì mọi phép phía sau vô nghĩa — đã có lý do ở trên

    # §5 — mọi tham số phải có quyết định; thiếu không bao giờ là "giữ mốc" (N6).
    for ten in sorted(bang.tham_so):
        if ten not in ket_qua.quyet_dinh and ten not in ket_qua.thieu:
            loi.append(f"{ten}: không có quyết định nào (DR-D5-01 §5)")
    for ten in ket_qua.tham_so_bo_c():
        loi.append(
            f"{ten}: luật nói BỎ điều kiện (c) — DR-D5-01 §3.1 đòi một thay đổi RIÊNG có test, không áp qua "
            "cổng này"
        )

    # §4 + §5.3 — xác nhận ghép.
    doi = ket_qua.tham_so_doi()
    if doi:
        if ket_qua.xac_nhan_trial is None:
            loi.append(f"có tham số đổi {sorted(doi)} mà chưa có suất {PARAM_XAC_NHAN} CONSUMED (DR-D5-01 §4)")
        else:
            gt = ket_qua.gia_tri_xac_nhan or {}
            khop = set(gt) == set(doi) and all(cung_gia_tri(gt[k], doi[k]) for k in doi)
            if not khop:
                loi.append(
                    f"suất {PARAM_XAC_NHAN} ({ket_qua.xac_nhan_trial}) ghép {gt!r} ≠ các giá trị luật chọn "
                    f"{doi!r} — xác nhận một cấu hình khác thứ đã thắng"
                )
    elif ket_qua.xac_nhan_trial is not None:
        loi.append(
            f"có suất {PARAM_XAC_NHAN} ({ket_qua.xac_nhan_trial}) nhưng không tham số nào đổi — DR-D5-01 §4 chỉ "
            "cho suất cuối khi ≥ 1 tham số đổi"
        )

    # TD-0256 + §5.3 — `param_status.yaml` khớp giá trị PHẢI chạy.
    cuoi = ket_qua.gia_tri_cuoi(bang)
    for ten, ts in sorted(bang.tham_so.items()):
        if ten in ket_qua.thieu or ten in ket_qua.tham_so_bo_c():
            continue
        muc = param_status.get(ten)
        if not isinstance(muc, Mapping):
            loi.append(f"param_status.yaml thiếu mục {ten!r}")
            continue
        can = "FROZEN" if cung_gia_tri(cuoi[ten], ts.moc) else "TUNED"
        if muc.get("status") != can or not cung_gia_tri(muc.get("value"), cuoi[ten]):
            loi.append(
                f"param_status.yaml {ten}: {muc.get('status')!r} = {muc.get('value')!r}, "
                f"phải {can} = {cuoi[ten]!r} theo quyết định tính lại"
            )

    # §2.2 — năm tham số không calibrate vẫn FROZEN.
    for ten in sorted(THAM_SO_KHONG_CALIBRATE):
        muc = param_status.get(ten)
        if not isinstance(muc, Mapping) or muc.get("status") != "FROZEN":
            loi.append(f"{ten} phải FROZEN (DR-D5-01 §2.2), đang {None if muc is None else muc.get('status')!r}")

    return loi


def d5_han_che(ket_qua: KetQuaB1, *, co_lenh_moc_giu_du: bool | None) -> str:
    """`DR-D5-01` §7 — bảy điều, cộng danh sách tham số giữ mốc/pending tính từ sổ, cộng hạn chế máy thu được."""
    dong = [
        "(1) CHỈ LONG — kết luận D5 không áp cho SHORT.",
        "(2) CHỈ CALIB (trạng thái ②) — chưa qua WFO/LOCKBOX; giá trị chọn ở đây chưa được kiểm ngoài mẫu.",
        "(3) 5/12 tham số KHÔNG calibrate (DR-D5-01 §2.2): "
        + ", ".join(sorted(THAM_SO_KHONG_CALIBRATE))
        + " — bốn bất khả trên đường đo hiện có, mult_corr cần dữ liệu danh mục live.",
        "(4) MỘT tham số mỗi lần; tương tác chỉ được kiểm ở suất xác nhận ghép (§5.3).",
        "(5) 'Giữ mốc' nghĩa là KHÔNG PHÂN BIỆT ĐƯỢC sau khi trừ nhiễu, không phải 'đã chứng minh tốt nhất'.",
        "(6) v_min = 0 chỉ GẦN NHƯ tắt điều kiện (c); bỏ (c) là thay đổi riêng (§3.1).",
        "(7) Không số EXPLORE nào được dùng làm bằng chứng.",
    ]
    giu = ket_qua.tham_so_giu_moc()
    dong.append(
        "(8) Giữ mốc / pending: "
        + ("; ".join(f"{k} — {v}" for k, v in sorted(giu.items())) if giu else "không có")
        + "."
    )
    if co_lenh_moc_giu_du is None:
        dong.append("(9) TD-0251 chưa đo — trần lấy của bảng ứng viên, không hạ theo §4.")
    if ket_qua.han_che:
        dong.append("(10) Hạn chế máy thu được: " + " | ".join(ket_qua.han_che))
    return "\n".join(dong)


__all__ = [
    "D5GateError",
    "THAM_SO_KHONG_CALIBRATE",
    "TRAN_KHI_KHONG_LENH_GIU_DU",
    "d5_han_che",
    "kiem_tieu_chi_dong_d5",
]
