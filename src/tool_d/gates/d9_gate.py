"""TD-0285 — phán quyết cổng D9 (`DR-D9-01` §6.2): Nhánh 1 §10.2 + PBO CHẶN (P0).

Hàm THUẦN. Không đọc sổ, không đọc file — E2 (TD-0286) và `close_d9_gate()`
(TD-0287) gọi CÙNG hàm này, để điều kiện chạy và điều kiện đóng cổng là một.

════ Ba kết cục — DIỄN GIẢI, cãi lại được ════

DR-011 (spec :3350-3365): FAIL = *"đo đủ VÀ ngưỡng không đạt"*; INCONCLUSIVE =
*"không kết luận được"* (thiếu mẫu). `DR-D4-09` §2.2 thay mốc "n < 30" bằng
thuế nhiễu (`phan_loai_ket_cuc`). Ghép lại, cho cổng NHIỀU tiêu chí:

    KHÔNG ĐẠT  = tiêu chí ĐO ĐƯỢC mà không đạt (expectancy phân loại FAIL,
                 PBO là số > PBO_MAX, tiêu chí khác có số và trượt ngưỡng)
    CHƯA ĐO    = tiêu chí `pending`/`unreadable`, hoặc expectancy INCONCLUSIVE
                 (thuế nhiễu > ngưỡng — không phân biệt "đạt" với "may")

    có KHÔNG ĐẠT            ⇒ FAIL
    không, nhưng có CHƯA ĐO ⇒ INCONCLUSIVE
    còn lại                 ⇒ PASS

FAIL đứng trước INCONCLUSIVE: một tiêu chí đã đo và trượt là đủ để bác cấu hình;
chờ thêm dữ liệu cho tiêu chí KHÁC không cứu được nó. Không thêm con số nào.

🔴 `n_trials` BẮT BUỘC, không mặc định (`DR-D9-01` §3): rào DSR của D9 theo `N`
hiện hành — DR-007 union có thể đổi `N`. Mặc định 114 ở đây là ghim cứng lặng lẽ.

🔴 Hôm nay `skewness_diff_vs_z1` là `pending` (Z1 bị cắt, `DR-D4-12` §4.5) ⇒ D9
không PASS được (`MT-53`). Đó là đúng — không phải lý do bỏ tiêu chí.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Sequence

from tool_d.gates import thresholds
from tool_d.gates.cscv import KetQuaPBO
from tool_d.gates.ket_cuc import KetCuc, KetQuaPhanLoai, phan_loai_ket_cuc
from tool_d.measurement.tri_state import Measured

TIEU_CHI_DSR = "dsr_adjusted_expectancy"
TIEU_CHI_PBO = "pbo"

#: Tiêu chí số của Nhánh 1 mà NGƯỜI GỌI phải khai (kể cả khai `pending`).
#: Expectancy tính tại đây từ lệnh; PBO lấy từ `tinh_pbo` — không nhận từ ngoài.
TIEU_CHI_KHAI: tuple[str, ...] = (
    "liq_buffer_ratio_mean",
    "max_single_trade_loss_over_risk_budget",
    "skewness_diff_vs_z1",
    "trades_per_year",
    "tp_fallback_ratio",
    # TD-0277 (MT-46): dải TIME_STOP 5–25% nay là tiêu chí CHẶN của Nhánh 1.
    # Khai ở đây để "chưa đo" rơi vào INCONCLUSIVE — thiếu khai thì
    # `evaluate_branch1` sẽ FAIL nó như đã đo mà trượt, tức FAIL GIẢ.
    "time_stop_ratio",
)


class CongD9Error(ValueError):
    """Đầu vào cổng D9 hỏng. Fail-closed: raise, không trả một kết cục."""


@dataclass(frozen=True)
class KetQuaCongD9:
    ket_cuc: KetCuc
    khong_dat: tuple[str, ...]
    chua_do: tuple[str, ...]
    phan_loai_expectancy: KetQuaPhanLoai | None
    pbo: Measured[float]
    n_trials: int
    n_lenh_phan_quyet: int

    def dien_giai(self) -> str:
        return (
            f"D9 {self.ket_cuc.value} · N = {self.n_trials} · n = {self.n_lenh_phan_quyet} · "
            f"không đạt {list(self.khong_dat)} · chưa đo {list(self.chua_do)} · PBO {self.pbo.render()}"
        )


def danh_gia_cong_d9(
    *,
    r_trien_khai_test: Sequence[float],
    n_trials: int,
    chi_so: Mapping[str, Measured[float]],
    ket_qua_pbo: KetQuaPBO,
) -> KetQuaCongD9:
    """Kết cục D9 của cấu hình đã chọn, trên lệnh ĐOẠN TEST (`MT-36`)."""
    if not isinstance(n_trials, int) or isinstance(n_trials, bool) or n_trials < 2:
        raise CongD9Error(f"n_trials phải là số nguyên ≥ 2 đọc từ kế toán, nhận {n_trials!r}")
    thieu = [k for k in TIEU_CHI_KHAI if k not in chi_so]
    la = sorted(set(chi_so) - set(TIEU_CHI_KHAI))
    if thieu or la:
        raise CongD9Error(
            f"chi_so phải khai ĐÚNG {list(TIEU_CHI_KHAI)} (chưa đo thì khai `pending`) — "
            f"thiếu {thieu}, thừa {la}. Expectancy và PBO không nhận từ ngoài."
        )
    for k in TIEU_CHI_KHAI:
        if not isinstance(chi_so[k], Measured):
            raise CongD9Error(f"{k} phải là Measured, nhận {chi_so[k]!r} (N6)")

    xs = [float(x) for x in r_trien_khai_test]
    if any(not math.isfinite(x) for x in xs):
        raise CongD9Error("r_trien_khai_test có trị không hữu hạn")

    metrics: dict[str, float] = {}
    chua_do: list[str] = []
    khong_dat: list[str] = []

    for k in TIEU_CHI_KHAI:
        if chi_so[k].is_ok():
            metrics[k] = float(chi_so[k].value)
        else:
            chua_do.append(k)

    phan_loai: KetQuaPhanLoai | None = None
    if len(xs) < 2:
        chua_do.append(TIEU_CHI_DSR)
    else:
        m = math.fsum(xs) / len(xs)
        s = math.sqrt(math.fsum((x - m) ** 2 for x in xs) / (len(xs) - 1))
        phan_loai = phan_loai_ket_cuc(
            mean_r=m, std_r=s, n_trades=len(xs), nguong=thresholds.DSR_ADJ_EXPECTANCY_MIN, n_trials=n_trials
        )
        metrics[TIEU_CHI_DSR] = phan_loai.gia_tri
        if phan_loai.ket_cuc is KetCuc.INCONCLUSIVE:
            chua_do.append(TIEU_CHI_DSR)

    if ket_qua_pbo.pbo.is_ok():
        metrics[TIEU_CHI_PBO] = float(ket_qua_pbo.pbo.value)
    else:
        chua_do.append(TIEU_CHI_PBO)

    ket_qua_nhanh1 = thresholds.evaluate_branch1(metrics, pbo_chan=True)
    for k in ket_qua_nhanh1.failed_criteria:
        if k not in chua_do:
            khong_dat.append(k)

    if khong_dat:
        kc = KetCuc.FAIL
    elif chua_do:
        kc = KetCuc.INCONCLUSIVE
    else:
        kc = KetCuc.PASS
    return KetQuaCongD9(
        ket_cuc=kc,
        khong_dat=tuple(khong_dat),
        chua_do=tuple(chua_do),
        phan_loai_expectancy=phan_loai,
        pbo=ket_qua_pbo.pbo,
        n_trials=n_trials,
        n_lenh_phan_quyet=len(xs),
    )


__all__ = ["CongD9Error", "KetQuaCongD9", "TIEU_CHI_KHAI", "danh_gia_cong_d9"]
