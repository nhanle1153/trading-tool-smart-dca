"""TD-0291 — luật cổng sống còn (`DR-SONG-CON-01` §2–§4). Hàm THUẦN, không I/O.

Câu hỏi DUY NHẤT: *có đáng tiêu suất đo vào Zone Absorption LONG không?* Đây là
cổng DỪNG, **không** phải phán quyết PASS/FAIL của cổng nào (`DR-D4-13` §1.2).

Luật áp máy móc, theo đúng thứ tự `DR-SONG-CON-01` §4, trên số GỘP `[T0, T2)`:

    1. n < SAN_N                                            ⇒ KHONG_KET_LUAN
    2. cận trên khoảng tin cậy 95% < 0                      ⇒ DUNG
    3. mean ≥ M  VÀ  mean > 0 ở CẢ HAI cửa sổ CALIB, WFO    ⇒ DI
    4. còn lại                                              ⇒ KHONG_TIEU_SUAT

    M      = DSR_ADJ_EXPECTANCY_MIN + dsr_hurdle(N) · std / √n_cong
    n_cong = (n / mã-năm) × số mã pool × năm-test (3 đoạn test D4, MT-36)

Không gõ lại hằng số nào đã có: ngưỡng `0,10` đọc `gates.thresholds`, rào đọc
`gates.dsr.dsr_hurdle`. `N` truyền vào (DR-007 union có thể đổi `N`).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from tool_d.gates import thresholds
from tool_d.gates.dsr import dsr_hurdle
from tool_d.measurement.tri_state import Measured

SAN_N: int = 30
"""`DR-SONG-CON-01` §3: mốc 30 lệnh của DR-011 (spec :3352), không phải số mới."""

Z_95: float = 1.96
"""Khoảng tin cậy 95% hai phía, xấp xỉ chuẩn — `DR-SONG-CON-01` §2 (n ≥ SAN_N)."""


class KetLuanSongCon(Enum):
    KHONG_KET_LUAN = "KHONG_KET_LUAN"
    DUNG = "DUNG"
    DI = "DI"
    KHONG_TIEU_SUAT = "KHONG_TIEU_SUAT"


class SongConError(ValueError):
    """Đầu vào hỏng (trị không hữu hạn, mẫu số ≤ 0, N < 2). Fail-closed."""


@dataclass(frozen=True)
class ThongKe:
    n: int
    mean: Measured[float]
    std: Measured[float]
    ci_duoi: Measured[float]
    ci_tren: Measured[float]


@dataclass(frozen=True)
class KetQuaSongCon:
    ket_luan: KetLuanSongCon
    ly_do: str
    calib: ThongKe
    wfo: ThongKe
    gop: ThongKe
    n_cong: Measured[float]
    m_can: Measured[float]
    n_trials: int


def thong_ke(r: Sequence[float]) -> ThongKe:
    """n · mean · std mẫu (n−1) · khoảng tin cậy 95%. Dưới 2 lệnh ⇒ `unreadable` (N6)."""
    xs = [float(x) for x in r]
    if any(not math.isfinite(x) for x in xs):
        raise SongConError("có trị R_trien_khai không hữu hạn — lỗi nối dữ liệu, không bỏ lặng lẽ")
    n = len(xs)
    if n < 2:
        u = Measured.unreadable(f"n = {n} < 2 — không có std")
        return ThongKe(n=n, mean=Measured.ok(xs[0]) if n == 1 else u, std=u, ci_duoi=u, ci_tren=u)
    m = math.fsum(xs) / n
    s = math.sqrt(math.fsum((x - m) ** 2 for x in xs) / (n - 1))
    h = Z_95 * s / math.sqrt(n)
    return ThongKe(n=n, mean=Measured.ok(m), std=Measured.ok(s), ci_duoi=Measured.ok(m - h), ci_tren=Measured.ok(m + h))


def danh_gia_song_con(
    *,
    r_calib: Sequence[float],
    r_wfo: Sequence[float],
    ma_nam: float,
    so_ma_pool: int,
    nam_test: float,
    n_trials: int,
) -> KetQuaSongCon:
    """Áp `DR-SONG-CON-01` §4. `r_*` là `R_trien_khai` từng lệnh của hai cửa sổ con."""
    if not isinstance(n_trials, int) or isinstance(n_trials, bool) or n_trials < 2:
        raise SongConError(f"n_trials phải là số nguyên ≥ 2 đọc từ kế toán, nhận {n_trials!r}")
    for ten, v in (("ma_nam", ma_nam), ("nam_test", nam_test)):
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) or v <= 0:
            raise SongConError(f"{ten} phải hữu hạn > 0, nhận {v!r}")
    if not isinstance(so_ma_pool, int) or isinstance(so_ma_pool, bool) or so_ma_pool < 1:
        raise SongConError(f"so_ma_pool phải là số nguyên ≥ 1, nhận {so_ma_pool!r}")

    tk_calib, tk_wfo = thong_ke(r_calib), thong_ke(r_wfo)
    tk_gop = thong_ke([*r_calib, *r_wfo])
    n = tk_gop.n
    chua = Measured.unreadable("chưa tới bước tính — luật dừng ở bước trước")

    def _kq(kl: KetLuanSongCon, ly_do: str, n_cong=chua, m_can=chua) -> KetQuaSongCon:
        return KetQuaSongCon(
            ket_luan=kl, ly_do=ly_do, calib=tk_calib, wfo=tk_wfo, gop=tk_gop,
            n_cong=n_cong, m_can=m_can, n_trials=n_trials,
        )

    # Luật 1
    if n < SAN_N:
        return _kq(KetLuanSongCon.KHONG_KET_LUAN, f"n gộp = {n} < {SAN_N} (luật 1)")
    mean, std = tk_gop.mean.value, tk_gop.std.value

    n_cong_v = n / ma_nam * so_ma_pool * nam_test
    n_cong = Measured.ok(n_cong_v)
    if n_cong_v < 2:
        m_can: Measured[float] = Measured.unreadable(f"n_cong = {n_cong_v:.3f} < 2")
    else:
        m_can = Measured.ok(thresholds.DSR_ADJ_EXPECTANCY_MIN + dsr_hurdle(n_trials) * std / math.sqrt(n_cong_v))

    # Luật 2
    if tk_gop.ci_tren.value < 0:
        return _kq(
            KetLuanSongCon.DUNG,
            f"cận trên KTC95 = {tk_gop.ci_tren.value:.4f} < 0 — lỗ rõ sau phí (luật 2)",
            n_cong, m_can,
        )

    # Luật 3
    hai_cua_so_duong = (
        tk_calib.n >= 2 and tk_wfo.n >= 2
        and tk_calib.mean.value > 0 and tk_wfo.mean.value > 0
    )
    if m_can.is_ok() and mean >= m_can.value and hai_cua_so_duong:
        return _kq(
            KetLuanSongCon.DI,
            f"mean = {mean:.4f} ≥ M = {m_can.value:.4f} và dương ở cả CALIB lẫn WFO (luật 3)",
            n_cong, m_can,
        )

    # Luật 4
    ly = []
    if not m_can.is_ok():
        ly.append(f"M không tính được ({m_can.note})")
    elif mean < m_can.value:
        ly.append(f"mean = {mean:.4f} < M = {m_can.value:.4f}")
    if not hai_cua_so_duong:
        ly.append("không dương ở cả hai cửa sổ CALIB/WFO (hoặc một cửa sổ < 2 lệnh)")
    return _kq(KetLuanSongCon.KHONG_TIEU_SUAT, "; ".join(ly) + " (luật 4)", n_cong, m_can)


__all__ = [
    "KetLuanSongCon", "KetQuaSongCon", "SAN_N", "SongConError", "ThongKe", "Z_95",
    "danh_gia_song_con", "thong_ke",
]
