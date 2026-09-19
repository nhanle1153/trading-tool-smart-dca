"""`TD-0334` (`DR-D4-14`) — lệnh đã trích của MỘT arm → bản ghi arm hợp lệ cho gate.

Tầng THUẦN (trừ `doc_pham_vi_delta_r`, chỉ đọc một artifact đã commit). Không gọi
Freqtrade, không đụng sổ trial. Người gọi: bộ chạy E3 (`chay_lo.py`, TD-0335).

════ Module này KHÔNG viết lại luật nào ════

* Công thức `R_trien_khai` (theo rủi ro đã triển khai) — `wfo/lenh.py` (`DR-D4-12` §1.4).
* Thuế nhiễu + ba kết cục — `gates/ket_cuc.py` (`DR-D4-09` §2.2).
* Cờ phạm vi, cấm `mo_ta` mang `PASS`, khai phạm vi Δ_R — `gates/arm_record.py`
  (`build_arm_record` tự kiểm và raise).
Việc ở đây là NỐI chúng, và đếm cho đúng.

════ Kết cục của arm MÔ TẢ — DIỄN GIẢI, ghi ra để cãi lại được ════

`DR-D4-10` §2.3 nói suất của arm `mo_ta` *"không mua một phán quyết"*, nhưng §2.2 lại
đòi nhóm C *"ra INCONCLUSIVE"* như một **dự báo phải xác nhận**. Hai câu chỉ cùng đúng
nếu kết cục của arm mô tả **được tính** (cùng công thức, cùng ngưỡng) nhưng **không được
đọc như phán quyết**. Nên: mọi arm tính `ket_cuc` bằng `phan_loai_ket_cuc()`; arm `mo_ta`
ra `PASS` thì `build_arm_record` TỪ CHỐI (đã có từ TD-0232); arm nhóm C ra khác
INCONCLUSIVE thì `co_do_nhom_c()` trả lời cờ đỏ tầng đo (N10) để bộ chạy báo — không
nuốt, không *"mừng"*.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

from tool_d.gates.arm_record import ARM_NHOM_C, build_arm_record
from tool_d.gates.dsr import N_DANG_KY
from tool_d.gates.ket_cuc import KetCuc, KetQuaPhanLoai, phan_loai_ket_cuc
from tool_d.gates.thresholds import DSR_ADJ_EXPECTANCY_MIN
from tool_d.measurement.provenance import Provenance
from tool_d.measurement.tri_state import Measured
from tool_d.wfo.folds import Fold
from tool_d.wfo.lenh import LenhWFO, cat_lat_theo_fold

#: `DR-D4-12` §4.1 — lô D4: 4/9 arm, Long-only. Ghim ở ĐÚNG MỘT chỗ. Thứ tự là thứ tự
#: chạy: `Z0-T1` (phán quyết) trước, rồi mốc paired `Z0`, chẩn đoán `Z0-T0`, số đo DCA `Z3`.
#: Đổi tập này là một QUYẾT ĐỊNH (DR), không phải một lần gõ thêm — `DR-D4-12` §4.4.
LO_ARM_D4: tuple[str, ...] = ("Z0-T1", "Z0", "Z0-T0", "Z3")

#: Artifact thô của thước Δ_R (D3.5) — cùng file `dr015/cong_d35.py` đọc.
DEFAULT_DU_LIEU_DELTA_R = Path("docs/du-lieu-do/dr015-luot-khop-tranche.json")


class BanGhiArmError(RuntimeError):
    """Không dựng được bản ghi arm từ lệnh đã có. Fail-closed."""


def _mean(xs: Sequence[float]) -> float:
    return math.fsum(xs) / len(xs)


def _std_mau(xs: Sequence[float]) -> float:
    """Độ lệch chuẩn MẪU (chia `n − 1`) — cùng quy ước `so_paired`."""
    m = _mean(xs)
    return math.sqrt(math.fsum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def thong_ke_arm(
    lenhs: Sequence[LenhWFO], *, nguong: float = DSR_ADJ_EXPECTANCY_MIN, n_trials: int = N_DANG_KY
) -> tuple[dict[str, Measured[float]], Measured[str], KetQuaPhanLoai | None]:
    """`(chi_so, ket_cuc, phan_loai)` của một arm, trên `R_trien_khai` (`DR-D4-12` §1).

    `n < 2` ⇒ `std` không định nghĩa được ⇒ mọi chỉ số phụ thuộc nó là `unreadable`
    kèm lý do — KHÔNG `0.0` (N6). `n = 0` ⇒ cả `mean_r` cũng `unreadable`.
    """
    n = len(lenhs)
    r = [l.r_trien_khai for l in lenhs]
    ty_le = [l.rui_ro_da_trien_khai_usdt / l.planned_risk_usdt for l in lenhs]
    r_ngan_sach = [l.r_realized for l in lenhs]

    if n == 0:
        ly_do = "0 lệnh — không có gì để đo"
        rong: Measured[float] = Measured.unreadable(ly_do)
        chi_so = {k: rong for k in ("mean_r", "std_r", "thue_nhieu", "dsr_adj", "ty_le_rui_ro_da_trien_khai", "mean_r_ngan_sach")}
        return chi_so, Measured.unreadable(ly_do), None

    chi_so: dict[str, Measured[float]] = {
        "mean_r": Measured.ok(_mean(r)),
        "ty_le_rui_ro_da_trien_khai": Measured.ok(_mean(ty_le)),
        # `DR-D4-12` §1.4: R theo ngân sách rủi ro vẫn tính và báo CẠNH BÊN, không phán quyết.
        "mean_r_ngan_sach": Measured.ok(_mean(r_ngan_sach)),
    }
    if n < 2:
        ly_do = f"n = {n} < 2 — độ lệch chuẩn mẫu không định nghĩa được"
        for k in ("std_r", "thue_nhieu", "dsr_adj"):
            chi_so[k] = Measured.unreadable(ly_do)
        return chi_so, Measured.unreadable(ly_do), None

    pl = phan_loai_ket_cuc(mean_r=_mean(r), std_r=_std_mau(r), n_trades=n, nguong=nguong, n_trials=n_trials)
    chi_so["std_r"] = Measured.ok(_std_mau(r))
    chi_so["thue_nhieu"] = Measured.ok(pl.thue)
    chi_so["dsr_adj"] = Measured.ok(pl.gia_tri)
    return chi_so, Measured.ok(pl.ket_cuc.value), pl


def lenh_theo_thang(lenhs: Sequence[LenhWFO]) -> dict[str, int]:
    """Số lệnh theo tháng MỞ lệnh (`YYYY-MM`) — phần bù MÔ TẢ cho phép kiểm ổn định thời
    gian mà Nhánh 1 mất khi bỏ fold (`arm_record.py`, TD-0234). Không phải ngưỡng."""
    return dict(sorted(Counter(l.open_date.strftime("%Y-%m") for l in lenhs).items()))


def co_do_nhom_c(arm: str, ket_cuc: Measured[str]) -> str | None:
    """`DR-D4-10` §2.2 — nhóm C ra kết cục KHÁC INCONCLUSIVE ⇒ cờ đỏ TẦNG ĐO (N10).

    Trả lời nhắn đọc được, hoặc `None`. Không raise: bản ghi FAIL của nhóm C vẫn là một
    bản ghi hợp lệ, và giấu nó đi là mất đúng bằng chứng cần để chẩn đoán.
    """
    if arm not in ARM_NHOM_C or ket_cuc.value is None:
        return None
    if ket_cuc.value == KetCuc.INCONCLUSIVE.value:
        return None
    return (
        f"🚩 arm {arm} (nhóm C) ra {ket_cuc.value} — DR-D4-10 §2.2 đã dự báo INCONCLUSIVE. "
        "Nghi ngờ BỘ ĐO trước (thang R_trien_khai sai, lookahead, kế toán), không mừng. "
        "Câu hỏi đầu tiên theo N10: lệnh THẬT có đúng thiết kế không?"
    )


def doc_pham_vi_delta_r(path: Path = DEFAULT_DU_LIEU_DELTA_R) -> dict[str, Any]:
    """`delta_r_pham_vi` (MT-37) đọc từ artifact thô của D3.5 — không khai tay.

    Hôm nay: 2 cặp, 91 lượt khớp, CALIB, `ZoneAbsorptionMinimal`.
    """
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
        nguon = d["_nguon"]
        pham_vi = {
            "so_ma": len(nguon["cap"]),
            "so_fill": len(d["luot_khop"]),
            "dataset": nguon["tap_du_lieu"],
            "chien_luoc": nguon["chien_luoc"],
        }
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise BanGhiArmError(f"không đọc được phạm vi Δ_R từ {path}: {exc!r}") from exc
    return pham_vi


def dung_ban_ghi_arm(
    *,
    arm: str,
    lenhs: Sequence[LenhWFO],
    cua_so: tuple[date, date],
    folds: Sequence[Fold],
    so_ma_da_chay: int,
    delta_r_pham_vi: Mapping[str, Any],
    provenance: Provenance,
    trial_id: str | None,
    huong: str = "LONG",
    nguong: float = DSR_ADJ_EXPECTANCY_MIN,
    chi_so_them: Mapping[str, Measured[Any]] | None = None,
) -> dict[str, Any]:
    """Một bản ghi arm, đã qua `validate_arm_record()` (bên trong `build_arm_record`).

    :param cua_so: `(observed_start, observed_end)` — ngày THẬT engine đọc (TD-0148),
        không phải ngày xin chạy.
    :param chi_so_them: khoá `measured` thêm vào `chi_so` (`chi_so_export.chi_so_tu_export`, TD-0338/0339) — schema
        cho phép khoá thêm; trùng khoá cơ sở ⇒ raise.
    :param folds: sơ đồ fold của WFO (`wfo/folds.sinh_folds`) — chỉ để ĐẾM `n_chi_test`
        (MT-36); Nhánh 1 phán quyết trên toàn cửa sổ (`NGUON_PHAN_QUYET_D4`).
    """
    if huong != "LONG":
        raise BanGhiArmError(f"huong={huong!r} — D4 đợt này Long-only (DR-D4-01)")
    if not lenhs:
        raise BanGhiArmError(
            f"arm {arm}: 0 lệnh — bản ghi arm không biểu diễn được một lượt không có lệnh "
            "(`lenh_theo_thang` bắt buộc khác rỗng). Đây là KHÔNG ĐO ĐƯỢC, không phải FAIL."
        )
    tu, den = cua_so
    t1 = datetime.combine(tu, time())
    # `observed_end` là NGÀY cuối có nến ⇒ cận nửa mở là đầu ngày hôm sau.
    t2 = datetime.combine(den, time()) + timedelta(days=1)
    lat = cat_lat_theo_fold(lenhs, folds, t1=t1, t2=t2)
    n_chi_test = sum(len(x) for x in lat)

    chi_so, ket_cuc, _ = thong_ke_arm(lenhs, nguong=nguong)
    trung = set(chi_so) & set(chi_so_them or {})
    if trung:
        raise BanGhiArmError(f"chi_so_them trùng khoá cơ sở {sorted(trung)} — không ghi đè số đã tính")
    chi_so = {**chi_so, **(chi_so_them or {})}
    return build_arm_record(
        arm=arm,
        huong=huong,
        n_toan_cua_so=len(lenhs),
        n_chi_test=n_chi_test,
        cua_so_toan_bo=cua_so,
        cua_so_chi_test=[(f.test_start, f.test_end) for f in folds],
        lenh_theo_thang=lenh_theo_thang(lenhs),
        so_ma_da_chay=so_ma_da_chay,
        delta_r_pham_vi=delta_r_pham_vi,
        chi_so=chi_so,
        ket_cuc=ket_cuc,
        provenance=provenance,
        trial_id=trial_id,
    )


__all__ = [
    "BanGhiArmError",
    "DEFAULT_DU_LIEU_DELTA_R",
    "LO_ARM_D4",
    "co_do_nhom_c",
    "doc_pham_vi_delta_r",
    "dung_ban_ghi_arm",
    "lenh_theo_thang",
    "thong_ke_arm",
]
