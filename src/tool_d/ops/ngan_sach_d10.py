"""TD-0384 — máy canh NGÂN SÁCH của bộ chạy D10 (lệnh live tối thiểu, tiền thật, mọi vị thế là CTRL / 0 trial).

Nguồn luật (N1 — file này THI HÀNH, không định nghĩa lại):
- `DR-D11-01` §4: tối đa **20 vị thế**, mở **tuần tự**; cửa sổ **14 ngày**, gia hạn **ĐÚNG MỘT lần** thêm 14 ngày nếu
  chưa đủ 20 vị thế hoặc chưa đủ 30 sự kiện; dừng SỚM khi đã gom đủ **≥ 30 sự kiện đổi khối lượng SL**; hết hạn thì dừng,
  không ép thêm vị thế.
- `DR-D10-02` Q2 (chủ dự án 25/09/2026): trần phụ **tổng ký quỹ đang mở ≤ 50% số dư**.

Các ngưỡng là hằng số vận hành đã chốt bằng DR (cùng khuôn `heartbeat_watchdog.NGUONG_HEARTBEAT_CU_S`), không phải tham
số tín hiệu Tầng B/C — không đi qua `tool_d_config.yaml`, không tính DOF. Đổi một số ở đây = đổi DR.

🔴 Trạng thái (số vị thế đã mở, mốc vị thế đầu, số sự kiện) do tầng gọi ĐỌC TỪ DB live + sổ Decision Log mỗi lần xét,
KHÔNG đếm trong RAM — sống qua restart (bài học MT-40). Module này chỉ nhận số đã đọc và phán quyết.

🔴 N6 — số dư không đọc được (`None`, NaN, ≤ 0) là lý do TỪ CHỐI, không phải "coi như đủ".
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta

TRAN_VI_THE = 20  # DR-D11-01 §4
CUA_SO = timedelta(days=14)  # DR-D11-01 §4
GIA_HAN = timedelta(days=14)  # DR-D11-01 §4 — đúng MỘT lần
DU_SU_KIEN_DOI_SL = 30  # DR-D11-01 §4/§5.2 — đủ thì dừng sớm
TRAN_KY_QUY_TREN_SO_DU = 0.5  # DR-D10-02 Q2


@dataclass(frozen=True)
class TrangThaiD10:
    """Ảnh chụp trạng thái D10 tại lúc xét, do tầng gọi đọc từ nguồn bền (DB live + Decision Log)."""

    so_vi_the_da_mo: int  # mọi vị thế D10 TỪNG mở (kể cả đã đóng)
    so_vi_the_dang_mo: int
    moc_vi_the_dau: datetime | None  # lúc mở vị thế D10 đầu tiên; None = chưa mở vị thế nào
    so_su_kien_doi_sl: int  # số bản ghi `DOI_SL` của runmode live
    ky_quy_dang_mo: float  # tổng ký quỹ (USDT) các vị thế đang mở
    so_du: float | None  # tổng số dư ví stake (USDT); None = không đọc được


def han_chot(tt: TrangThaiD10) -> datetime | None:
    """Mốc cuối được mở vị thế. `None` khi chưa có vị thế nào (cửa sổ chưa bắt đầu).

    Gia hạn đúng một lần khi CHƯA đủ 20 vị thế HOẶC chưa đủ 30 sự kiện (chữ `DR-D11-01` §4). Đã đủ cả hai thì bộ chạy
    đã dừng sớm từ trước, nên xét bằng số hiện tại cho cùng kết quả với xét tại ngày thứ 14."""
    if tt.moc_vi_the_dau is None:
        return None
    han = tt.moc_vi_the_dau + CUA_SO
    if tt.so_vi_the_da_mo < TRAN_VI_THE or tt.so_su_kien_doi_sl < DU_SU_KIEN_DOI_SL:
        han += GIA_HAN
    return han


def _ly_do_chung(tt: TrangThaiD10, *, ky_quy_them: float, now: datetime) -> list[str]:
    ly_do: list[str] = []
    if tt.so_su_kien_doi_sl >= DU_SU_KIEN_DOI_SL:
        ly_do.append(f"đã đủ {tt.so_su_kien_doi_sl} ≥ {DU_SU_KIEN_DOI_SL} sự kiện đổi SL — D10 dừng sớm (DR-D11-01 §4)")
    han = han_chot(tt)
    if han is not None and now >= han:
        ly_do.append(f"hết cửa sổ D10 lúc {han.isoformat()} (14 ngày + gia hạn đúng một lần) — không ép thêm")
    so_du = tt.so_du
    if so_du is None or not math.isfinite(so_du) or so_du <= 0:
        ly_do.append(f"số dư không đọc được ({so_du!r}) — không xét được trần ký quỹ (N6)")
    elif not math.isfinite(ky_quy_them) or ky_quy_them < 0 or not math.isfinite(tt.ky_quy_dang_mo):
        ly_do.append(f"ký quỹ không hợp lệ (đang mở {tt.ky_quy_dang_mo!r}, thêm {ky_quy_them!r}) (N6)")
    elif tt.ky_quy_dang_mo + ky_quy_them > TRAN_KY_QUY_TREN_SO_DU * so_du:
        ly_do.append(
            f"ký quỹ sau lệnh {tt.ky_quy_dang_mo + ky_quy_them:.4f} > {TRAN_KY_QUY_TREN_SO_DU:.0%} số dư "
            f"{so_du:.4f} (DR-D10-02 Q2)"
        )
    return ly_do


def xet_vi_the_moi(tt: TrangThaiD10, *, ky_quy_lenh: float, now: datetime) -> tuple[str, ...]:
    """Lý do TỪ CHỐI mở một vị thế MỚI (tranche 1). Rỗng = được mở."""
    ly_do = _ly_do_chung(tt, ky_quy_them=ky_quy_lenh, now=now)
    if tt.so_vi_the_da_mo >= TRAN_VI_THE:
        ly_do.insert(0, f"đã mở {tt.so_vi_the_da_mo} ≥ {TRAN_VI_THE} vị thế — hết ngân sách D10 (DR-D11-01 §4)")
    if tt.so_vi_the_dang_mo > 0:
        ly_do.insert(0, f"còn {tt.so_vi_the_dang_mo} vị thế đang mở — D10 mở TUẦN TỰ (DR-D11-01 §4)")
    return tuple(ly_do)


def xet_them_tranche(tt: TrangThaiD10, *, ky_quy_them: float, now: datetime) -> tuple[str, ...]:
    """Lý do TỪ CHỐI bơm thêm tranche vào vị thế đang mở. Không xét trần 20/tuần tự (không tạo vị thế mới), nhưng
    xét dừng sớm, hết cửa sổ và trần ký quỹ — một tranche thêm là tiền thật thêm."""
    return tuple(_ly_do_chung(tt, ky_quy_them=ky_quy_them, now=now))
