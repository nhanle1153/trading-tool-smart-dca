"""TD-0187 — TẦNG ĐỊNH CỠ LỆNH theo RỦI RO CỐ ĐỊNH (§6.8f Bước 1, §6.2) — MT-16, DR-D4-04.

Cho tới trước module này, repo KHÔNG có tầng định cỡ: `custom_stake_amount`
0 dòng, 5/6 hệ số §6.2 0 dòng, và `config.json:10` `stake_amount: 10` là
cỡ THẬT của mọi lệnh (đo trên 91 lượt khớp đã niêm phong: 39,98 USDT/lệnh
hằng số, tỉ trọng ¼-¼-½). Chi tiết ở MT-16.

════ Công thức — chép ĐÚNG §6.8f B1, không diễn giải ════

    rho_eff = rho × mult_regime × mult_zss × mult_corr × mult_dd × mult_edge × mult_deploy
    N_full  = (rho_eff × E_D) / R_eff              ← notional ĐẦY ĐỦ ba tranche
    stake_i = N_full × w_tranche[i] / L_exchange   ← KÝ QUỸ tranche i (xem dưới)

🔴 **`stake` của Freqtrade là KÝ QUỸ (collateral), KHÔNG phải notional.**
Tài liệu: *"The actual position size will be the initial capital multiplied
by the leverage."* Nên hàm trả cho `custom_stake_amount()` /
`adjust_trade_position()` phải chia `L_exchange`, và chiến lược PHẢI cài
`leverage()` trả `L_exchange` — không cài thì Freqtrade mặc định **1x**
(tài liệu: *"If not implemented, leverage defaults to 1x"*). Repo trước
module này không có `leverage()` ở đâu cả ⇒ mọi backtest tới nay chạy 1x,
không phải 3x đã chốt ở DR-D0PRE-06. Đó là triệu chứng thứ năm của MT-16.

════ Bất biến D0.1, và test nào canh nó ════

Với arm định cỡ theo rủi ro: `planned_risk_usdt = N_full × R_eff = rho_eff
× E_D` — **KHÔNG phụ thuộc `R_eff`**. Zone rộng → `R_eff` lớn → `N_full`
nhỏ → lỗ khi chạm SL vẫn đúng `rho_eff × E_D`. Test ghim: đổi `R_eff` gấp
ba, `planned_risk_usdt` không đổi tới 1e-9. Arm `Z0-S1` (vốn cố định) CỐ Ý
vi phạm bất biến này — đó chính là điều arm ấy kiểm chứng (§10.1b).

🔴 **RÀNG BUỘC BAO TRÙM (§6.2): mọi `mult_*` ≤ 1.0.** `rho` là TRẦN. Tín
hiệu tốt không được cược to hơn; chỉ được HẠ ở tín hiệu xấu. `HeSoMult`
từ chối khởi tạo nếu bất kỳ hệ số nào > 1.0 hoặc < 0 — không có đường nào
trong module sinh ra `rho_eff > rho`.

════ Vì sao module này KHÔNG chép lại công thức của `arm_switches` ════

`N_full` đi qua `arm_switches.notional_tranche1_theo_arm()` (TD-0183) rồi
nhân ngược `n_tranches` — hàm đó đã phân nhánh RỦI-RO-CỐ-ĐỊNH / VỐN-CỐ-ĐỊNH
(`Z0-S1`) và đã có test riêng. Chép công thức sang đây là tạo nguồn sự
thật thứ hai (MT-03). Tương tự, module này chỉ nhận số đã tính sẵn (ADX,
ZSS, corr, dd, deployed_ratio) — không đọc dataframe, không biết Freqtrade —
cùng khuôn `trend_context.py` / `dg1_dg5_tranche_gates.py`.

════ Câu hỏi bắt buộc trước mọi kết luận "phải đo lại" (bài học hôm nay) ════

Hai lần trong ngày 08/09, hai phiên cùng suy ra sai rằng dựng tầng này thì
"phải đo lại Δ_R". Sai vì `lệch_R = qty × Δgiá / planned_risk` có cỡ lệnh ở
**cả tử lẫn mẫu** — nó không nhìn thấy cỡ lệnh (kiểm: ×1/×3/×20 giống hệt
tới bit cuối). Câu chặn: *"đại lượng này có nhìn thấy thứ tôi sắp đổi
không?"* Hỏi câu đó trước khi mở bất kỳ artifact đã niêm phong nào.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

from tool_d.arm_switches import (
    CHE_DO_CO_LENH_THEO_ARM,
    notional_tranche1_theo_arm,
)
from tool_d.config.loader import ToolDConfig, resolve

#: Số lệnh live tối thiểu để `mult_edge` có nghĩa (§6.2 hệ số 5, §12c.1).
#: Dưới ngưỡng này `mult_edge = 1.0` — "chưa đủ mẫu để kết luận", KHÔNG
#: phải "edge tốt". Trong backtest D4 luôn là trường hợp này.
SO_LENH_LIVE_TOI_THIEU_CHO_EDGE = 50

#: Dung sai cho Σ w_tranche == 1 (YAML ghi 0.3333/0.3333/0.3334).
DUNG_SAI_TONG_TRONG_SO = 1e-3


class SizingError(ValueError):
    """Đầu vào định cỡ không hợp lệ. Fail-closed: raise, không trả một
    con số "hợp lý" — một cỡ lệnh sai không làm gì báo lỗi, nó chỉ âm
    thầm đổi mọi con số của §10.2."""


# ── Sáu hệ số §6.2 — mỗi hàm một hệ số, nhận số đã tính sẵn ──────────

def mult_regime(*, adx_1d: float, strong: float, weak: float, adx_split: float, adx_threshold: float) -> float:
    """§6.2 hệ số 1. `ADX ≥ adx_split` → `strong`; `adx_threshold ≤ ADX <
    adx_split` → `weak`. **KHÔNG có nhánh thứ ba**: `ADX < adx_threshold`
    đã bị §2.5 chặn không vào lệnh — tới được đây với ADX như thế là
    tầng trên đã hỏng, raise chứ không bịa `0.0`."""
    if adx_1d != adx_1d:  # NaN
        raise SizingError("ADX(1D) là NaN — không định cỡ trên số chưa tính được")
    if adx_1d < adx_threshold:
        raise SizingError(
            f"ADX(1D) = {adx_1d} < ngưỡng vào lệnh {adx_threshold} — §2.5 đáng lẽ đã "
            "chặn từ trước; tới được tầng định cỡ nghĩa là bộ lọc trend không chạy"
        )
    return strong if adx_1d >= adx_split else weak


def mult_zss(zss_value: float) -> float:
    """§6.2 hệ số 2 — `clip(ZSS, 0.5, 1.0) / 1.0`. 0 DOF."""
    if zss_value != zss_value:
        raise SizingError("ZSS là NaN")
    return min(max(zss_value, 0.5), 1.0) / 1.0


def mult_corr(*, corr_pool: float, nguong: Sequence[float]) -> float:
    """§6.2 hệ số 3 — `0.5` nếu `corr_pool > nguong[1]`, `0.75` nếu
    `> nguong[0]`, ngược lại `1.0`. `corr_pool` là trung bình |corr| với
    MỌI vị thế đang mở; không vị thế → 0 → 1.0 (chỗ gọi lo phần đó)."""
    if len(nguong) != 2 or not (0 <= nguong[0] < nguong[1] <= 1):
        raise SizingError(f"mult_corr_thresholds phải là [thấp, cao] trong [0,1], nhận {list(nguong)}")
    if corr_pool != corr_pool or not (0 <= corr_pool <= 1):
        raise SizingError(f"corr_pool phải trong [0,1], nhận {corr_pool}")
    if corr_pool > nguong[1]:
        return 0.5
    if corr_pool > nguong[0]:
        return 0.75
    return 1.0


def mult_dd(*, dd_pct: float, soft_pct: float, halt_pct: float) -> float:
    """§6.2 hệ số 4 / §12c.5 — `1.0` nếu `dd ≤ soft`, `0.5` nếu `≤ halt`,
    **`0.0` = HALT** (ngừng MỞ lệnh mới, KHÔNG phải "size 0"). Đơn vị
    PHẦN TRĂM trong tên biến để không lẫn 0.05 với 5 (bài học DG4)."""
    if dd_pct != dd_pct or dd_pct < 0:
        raise SizingError(f"dd_pct phải ≥ 0, nhận {dd_pct}")
    if not (0 < soft_pct < halt_pct):
        raise SizingError(f"thang dd phải 0 < soft ({soft_pct}) < halt ({halt_pct})")
    if dd_pct <= soft_pct:
        return 1.0
    if dd_pct <= halt_pct:
        return 0.5
    return 0.0


def mult_edge(*, edge_ratio: float | None, so_lenh_live: int, nguong: float) -> float:
    """§6.2 hệ số 5 — `0.5` nếu `edge_ratio < nguong`, ngược lại `1.0`.
    **Trước `SO_LENH_LIVE_TOI_THIEU_CHO_EDGE` lệnh live: luôn `1.0`** (spec
    dòng 1774). Truyền `edge_ratio` khi chưa đủ mẫu là mâu thuẫn → raise."""
    if so_lenh_live < 0:
        raise SizingError(f"so_lenh_live phải ≥ 0, nhận {so_lenh_live}")
    if so_lenh_live < SO_LENH_LIVE_TOI_THIEU_CHO_EDGE:
        if edge_ratio is not None:
            raise SizingError(
                f"mới {so_lenh_live} lệnh live (< {SO_LENH_LIVE_TOI_THIEU_CHO_EDGE}) mà đã "
                "truyền edge_ratio — spec dòng 1774: chưa đủ mẫu thì mult_edge = 1.0, "
                "không tính"
            )
        return 1.0
    if edge_ratio is None or edge_ratio != edge_ratio:
        raise SizingError("đủ 50 lệnh live nhưng edge_ratio thiếu/NaN")
    return 0.5 if edge_ratio < nguong else 1.0


def mult_deploy(*, deployed_ratio: float, nguong: float) -> float:
    """§6.2 hệ số 6 — `0.5` nếu `deployed_ratio > nguong` (0.85, dùng lại
    trần margin §6.8f). `deployed_ratio` = Σ notional ĐÃ KHỚP / Σ notional
    KẾ HOẠCH đủ 3 tranche, trên mọi vị thế mở — đo "bao nhiêu phần kế
    hoạch đã thành thực". ⚠️ Đọc theo nghĩa "Σ margin / E_D" thì hệ số
    này là CODE CHẾT (spec cảnh báo rõ) — chỗ gọi phải đưa đúng tỉ số."""
    if deployed_ratio != deployed_ratio or not (0 <= deployed_ratio <= 1 + 1e-9):
        raise SizingError(f"deployed_ratio phải trong [0,1], nhận {deployed_ratio}")
    return 0.5 if deployed_ratio > nguong else 1.0


@dataclass(frozen=True)
class HeSoMult:
    """Sáu hệ số §6.2. Từ chối khởi tạo nếu bất kỳ hệ số nào ngoài [0, 1]
    — RÀNG BUỘC BAO TRÙM của §6.2, thi hành ở CỬA VÀO chứ không ở chỗ dùng."""

    regime: float
    zss: float
    corr: float
    dd: float
    edge: float
    deploy: float

    def __post_init__(self) -> None:
        for ten, gia_tri in asdict(self).items():
            if gia_tri != gia_tri or not (0.0 <= gia_tri <= 1.0):
                raise SizingError(
                    f"mult_{ten} = {gia_tri} nằm ngoài [0, 1] — §6.2: rho là TRẦN, mọi "
                    "mult_* ≤ 1.0; tín hiệu tốt không được cược to hơn"
                )

    def tich(self) -> float:
        return self.regime * self.zss * self.corr * self.dd * self.edge * self.deploy

    @property
    def la_halt(self) -> bool:
        """`mult_dd == 0.0` ⇒ HALT (§12c.5): ngừng MỞ lệnh mới. Chỗ gọi
        phải kiểm cờ này TRƯỚC khi hỏi cỡ — hỏi cỡ lúc HALT là raise."""
        return self.dd == 0.0

    def to_dict(self) -> dict[str, float]:
        """Đúng hình `mult_breakdown` của bản ghi PLAN §8.3."""
        return asdict(self)


# ── Kế hoạch cỡ lệnh — chốt MỘT LẦN lúc tranche 1, sống trong custom_data ─

@dataclass(frozen=True)
class KeHoachCoLenh:
    """Mọi thứ tranche 2/3 cần để tự định cỡ mà KHÔNG tính lại — cùng
    nguyên tắc `KeHoachTranche` (L-Z49): ghi một lần, đọc lại nguyên vẹn."""

    arm: str
    n_full_usdt: float          # notional đầy đủ ba tranche
    w_tranche: tuple[float, float, float]
    l_exchange: float
    rho_pct: float
    rho_eff_pct: float
    mult: dict[str, float]
    r_eff: float
    planned_risk_usdt: float    # = N_full × R_eff
    planned_margin_usdt: float  # = N_full / L_exchange

    def notional_tranche(self, i: int) -> float:
        return self.n_full_usdt * self.w_tranche[_chi_so(i)]

    def stake_tranche(self, i: int) -> float:
        """🔴 KÝ QUỸ tranche `i` (1-based) — đây là giá trị trả cho
        `custom_stake_amount()` (i=1) và `adjust_trade_position()` (i=2,3).
        Chia `L_exchange` vì stake của Freqtrade là collateral."""
        return self.notional_tranche(i) / self.l_exchange

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["w_tranche"] = list(self.w_tranche)
        return d

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "KeHoachCoLenh":
        d = dict(d)
        d["w_tranche"] = tuple(d["w_tranche"])
        return cls(**d)


def _chi_so(i: int) -> int:
    if i not in (1, 2, 3):
        raise SizingError(f"tranche phải là 1, 2 hoặc 3, nhận {i}")
    return i - 1


def doc_trong_so_tranche(cfg: ToolDConfig) -> tuple[float, float, float]:
    """`tier_frozen.w_tranche.value` — đọc qua `resolve()` (N4), kiểm Σ = 1.

    Đây là con số mà `trade_plan.py:21` gọi "ĐÓNG BĂNG" nhưng chưa từng
    được thi hành (thực tế ¼-¼-½, MT-16 cơ chế). Từ đây nó được thi hành
    thật, và test khoá đo nó từ fill của backtest thật."""
    w = tuple(float(x) for x in resolve(cfg, "tier_frozen.w_tranche.value"))
    if len(w) != 3 or any(x <= 0 for x in w):
        raise SizingError(f"w_tranche phải là 3 số dương, nhận {w}")
    if abs(sum(w) - 1.0) > DUNG_SAI_TONG_TRONG_SO:
        raise SizingError(f"Σ w_tranche = {sum(w)} ≠ 1 (dung sai {DUNG_SAI_TONG_TRONG_SO})")
    return w  # type: ignore[return-value]


def lap_ke_hoach_co_lenh(
    *,
    cfg: ToolDConfig,
    arm: str,
    r_eff: float,
    mult: HeSoMult,
    notional_ref_r_eff: float | None = None,
) -> KeHoachCoLenh:
    """Dựng kế hoạch cỡ lệnh cho MỘT lệnh, lúc tranche 1 — §6.8f Bước 1.

    Bước 2 (kết nạp danh mục Σ risk / Σ margin) là TD-0188, không ở đây:
    hàm này trả lời *"lệnh này to bao nhiêu"*, không trả lời *"có được mở
    không"*. Gộp hai câu là cách một lệnh bị từ chối trông giống một lệnh
    cỡ 0.
    """
    if mult.la_halt:
        raise SizingError(
            "mult_dd = 0.0 là HALT (§12c.5): ngừng MỞ lệnh mới. Chỗ gọi phải chặn ở "
            "confirm_trade_entry, không được hỏi cỡ lệnh rồi nhận về 0"
        )
    if r_eff != r_eff or r_eff <= 0:
        raise SizingError(f"R_eff phải > 0, nhận {r_eff}")

    e_d = float(resolve(cfg, "tier_a.E_D"))
    rho_pct = float(resolve(cfg, "tier_a.rho_pct"))
    l_exchange = float(resolve(cfg, "tier_a.L_exchange"))
    n_tranches = int(resolve(cfg, "tier_c.n_tranches"))
    if e_d <= 0 or rho_pct <= 0 or l_exchange < 1 or n_tranches != 3:
        raise SizingError(
            f"cấu hình không hợp lệ: E_D={e_d}, rho_pct={rho_pct}, L_exchange={l_exchange}, "
            f"n_tranches={n_tranches} (module này viết cho đúng 3 tranche, §3.1)"
        )
    w = doc_trong_so_tranche(cfg)

    rho_eff_pct = rho_pct * mult.tich()

    # N_full qua ĐÚNG hàm của arm_switches (phân nhánh Z0-S1 ở đó), rồi
    # nhân ngược n_tranches — hàm ấy chia đều 1/n, còn tỉ trọng thật áp ở
    # `stake_tranche()` theo w_tranche đọc từ cấu hình.
    t1 = notional_tranche1_theo_arm(
        arm=arm,
        e_d=e_d,
        rho_pct=rho_eff_pct,
        r_eff=r_eff,
        n_tranches=n_tranches,
        notional_ref_r_eff=notional_ref_r_eff,
    )
    n_full = t1 * n_tranches

    return KeHoachCoLenh(
        arm=arm,
        n_full_usdt=n_full,
        w_tranche=w,
        l_exchange=l_exchange,
        rho_pct=rho_pct,
        rho_eff_pct=rho_eff_pct,
        mult=mult.to_dict(),
        r_eff=r_eff,
        planned_risk_usdt=n_full * r_eff,
        planned_margin_usdt=n_full / l_exchange,
    )


def che_do_co_lenh(arm: str) -> str:
    """`RUI_RO_CO_DINH` hay `NOTIONAL_CO_DINH` — đọc từ bảng của
    `arm_switches`, không định nghĩa lại."""
    if arm not in CHE_DO_CO_LENH_THEO_ARM:
        raise SizingError(f"arm không rõ: {arm!r}")
    return CHE_DO_CO_LENH_THEO_ARM[arm]


__all__ = [
    "DUNG_SAI_TONG_TRONG_SO",
    "SO_LENH_LIVE_TOI_THIEU_CHO_EDGE",
    "HeSoMult",
    "KeHoachCoLenh",
    "SizingError",
    "che_do_co_lenh",
    "doc_trong_so_tranche",
    "lap_ke_hoach_co_lenh",
    "mult_corr",
    "mult_dd",
    "mult_deploy",
    "mult_edge",
    "mult_regime",
    "mult_zss",
]
