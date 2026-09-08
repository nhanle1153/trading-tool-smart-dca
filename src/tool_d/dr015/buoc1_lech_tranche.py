"""TD-0161 — DR-015 Bước 1: quy đổi phân phối lệch khớp tranche sang bội
số `R_realized` và tính `Δ_R` (spec §2 Bước 1, §3).

🔴 **KHÔNG đo lại.** Dùng đúng 91 lượt khớp của TD-0115, đã trích ra file
có theo dõi `docs/du-lieu-do/dr015-luot-khop-tranche.json` (TD-0161, xác
minh độc lập khớp 35/32/24 với bảng research-log). Module này chỉ ĐỌC và
QUY ĐỔI — không chạm backtest, không chạm dữ liệu thị trường thô.

════ Đơn vị: vì sao `lệch_R` phải NHÂN với khối lượng ════

`docs/decisions/DR-013-don-vi-do.md` (2d) định nghĩa `R_realized =
pnl_abs / planned_risk_usdt` — cả tử lẫn mẫu đều là USDT. `(fill − p_i)`
chỉ là một CHÊNH LỆCH GIÁ (USDT/đơn vị cơ sở), không cùng đơn vị với
`planned_risk_usdt` (tổng USDT). Muốn "lệch tính bằng R_realized" phải trước hết
quy chênh lệch giá đó ra USDT bằng khối lượng THẬT đã khớp của tranche đó,
rồi mới chia cho `planned_risk_usdt`:

    lệch_R(tranche i) = qty_i_thật × (fill_i − p_i_kế_hoạch) / planned_risk_usdt

════ `planned_risk_usdt` — vì sao phải SUY, không đọc được ════

DR-013 tu chính (v8, §2b): `planned_risk_usdt = Σ qty_i_kế_hoạch × |p_i −
sl|` **trên THANG ĐẦY ĐỦ theo thiết kế lệnh** — tức cả 3 tranche, kể cả
tranche KHÔNG khớp (trade chạm SL sớm). Dữ liệu trích chỉ có khối lượng
CỦA TRANCHE ĐÃ KHỚP; tranche chưa khớp không có `amount` thật.

🔴 **Phát hiện khi viết task này, đã xác minh bằng dữ liệu — không phải
suy diễn:** `ZoneAbsorptionMinimal.adjust_trade_position()` trả về
`trade.stake_amount` (KHÔNG phải một hằng số hay 1/3 tổng) làm khối
lượng USDT cộng thêm mỗi tranche. Vì Freqtrade cập nhật `stake_amount`
CỘNG DỒN sau mỗi lần khớp, kết quả là một cấp số THEO CẤP LUỸ THỪA, không
phải chia đều: tranche 2 cộng thêm ĐÚNG BẰNG khối lượng tranche 1 (tổng
sau tranche 2 = 2×), tranche 3 cộng thêm ĐÚNG BẰNG tổng đã có (tổng sau
tranche 3 = 4×). Đã kiểm tay 8/8 trade đủ 3 tranche: `cost2/cost1 ≈
1.000` và `cost3/(cost1+cost2) ≈ 1.000` ở cả 8, sai số < 0.1%. Đây KHÔNG
phải cách tính `TRONG_SO_TRANCHE = 1/3` trong `trade_plan.py` — hằng số
đó chỉ dùng để tính `p_avg` (trung bình GIÁ), không liên quan khối lượng.
Không phải bug (không đụng vào `ZoneAbsorptionMinimal.py` ở task này) —
chỉ là một thiết kế position-sizing không được đặt tên rõ, ghi lại để
người sau khỏi phải dò lại.

**Hệ quả cho tranche KHÔNG khớp:** dùng chính mẫu hình đã xác minh đó để
ước lượng khối lượng LẼ RA sẽ dùng — không suy diễn tuỳ ý, suy từ hành vi
đã đo được nhiều lần trên chính dữ liệu này:

    cost[1] = cost thật (luôn có — mọi trade đều khớp tranche 1)
    cost[2] = cost thật NẾU đã khớp, ngược lại = cost[1]
    cost[3] = cost thật NẾU đã khớp, ngược lại = cost[1] + cost[2]

rồi `qty_i = cost[i] / p_i_kế_hoạch` (giá kế hoạch, không phải giá khớp
thật — đây là khối lượng THIẾT KẾ, không phải khối lượng đã trả).

════ `p1`/`p2`/`p3`/`sl` cho MỌI trade, kể cả tranche chưa khớp ════

Không cần đọc lại tag gốc: `zone_low`/`zone_high`/`sl` có mặt trên MỌI
dòng của một trade (kể cả dòng tranche 1), và công thức `tinh_ke_hoach()`
(`trade_plan.py`) là:

    p1 = giá kế hoạch của DÒNG tranche=1 (luôn có, luôn khớp)
    p2 = (zone_high + zone_low) / 2
    p3 = zone_low

Đã đối chiếu: `p2`/`p3` tính lại theo công thức này khớp TUYỆT ĐỐI với
`p_ke_hoach` của các dòng tranche 2/3 đã khớp (xem test) — nên dùng công
thức cho tranche CHƯA khớp là an toàn, không phải ngoại suy mù.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from tool_d.config.loader import DEFAULT_CONFIG_PATH, load_tool_d_config
from tool_d.ledger.registry import DEFAULT_REGISTRY_PATH, TrialLedger
from tool_d.ledger.timerange import assert_dataset_timerange, dataset_boundaries_from_config
from tool_d.measurement.hashing import sha256_of
from tool_d.measurement.provenance import build_provenance
from tool_d.measurement.tri_state import Measured

DEFAULT_DU_LIEU_THO_PATH = Path("docs/du-lieu-do/dr015-luot-khop-tranche.json")

# Sàn số mẫu của §3 — dưới sàn này dùng max thay vì P90 (fail-closed).
SAN_N_CHO_P90 = 30


class Buoc1Error(RuntimeError):
    """Dữ liệu thô không dùng được — thiếu trường, sai hình dạng, hoặc
    không phải LONG duy nhất mà module giả định."""


@dataclass(frozen=True)
class KetQuaBuoc1:
    """Kết quả Bước 1 cho MỘT hướng (Long hoặc Short)."""

    huong: str
    so_lenh: int
    lech_moi_lenh: tuple[float, ...]  # 1 giá trị / trade, đã lấy |.|, đơn vị R_realized
    delta_r: Measured[float]
    dung_p90: bool  # True nếu n >= SAN_N_CHO_P90 (dùng P90), False nếu dùng max


def _doc_du_lieu_tho(path: Path = DEFAULT_DU_LIEU_THO_PATH) -> dict[str, Any]:
    if not path.exists():
        raise Buoc1Error(f"Không thấy dữ liệu thô: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _gom_theo_trade(rows: list[dict[str, Any]]) -> dict[int, dict[int, dict[str, Any]]]:
    theo_trade: dict[int, dict[int, dict[str, Any]]] = defaultdict(dict)
    for r in rows:
        theo_trade[r["trade_idx"]][r["tranche"]] = r
    return dict(theo_trade)


def _uoc_luong_cost_tranche(cost_da_biet: dict[int, float]) -> dict[int, float]:
    """Suy khối lượng USDT (đã kế hoạch) cho CẢ 3 tranche, dùng mẫu hình
    cấp-luỹ-thừa đã xác minh trên chính dữ liệu này (xem docstring module).
    Tranche đã khớp dùng số THẬT; tranche chưa khớp dùng số SUY.
    """
    if 1 not in cost_da_biet:
        raise Buoc1Error("Trade thiếu dòng tranche 1 — không thể có, kiểm lại dữ liệu nguồn")
    c1 = cost_da_biet[1]
    c2 = cost_da_biet.get(2, c1)
    c3 = cost_da_biet.get(3, c1 + c2)
    return {1: c1, 2: c2, 3: c3}


def _gia_ke_hoach_ca_ba_tranche(mot_dong_bat_ky: dict[str, Any], p1: float) -> dict[int, float]:
    """`p2`/`p3` suy từ `zone_low`/`zone_high` — có trên MỌI dòng, kể cả
    dòng của tranche chưa từng khớp trong CÙNG trade (vì zone là thuộc
    tính của cả trade, không phải của riêng một tranche)."""
    zl, zh = mot_dong_bat_ky["zone_low"], mot_dong_bat_ky["zone_high"]
    return {1: p1, 2: (zh + zl) / 2, 3: zl}


def _planned_risk_usdt(cost_full: dict[int, float], p: dict[int, float], sl: float) -> float:
    return sum(cost_full[i] / p[i] * abs(p[i] - sl) for i in (1, 2, 3))


def _lech_moi_lenh(fills: dict[int, dict[str, Any]], p: dict[int, float], planned_risk_usdt: float) -> float:
    """Σ|lệch_R| các tranche >= 2 ĐÃ khớp. Tranche 1 KHÔNG tính (spec §3 —
    Z0 cũng có tranche 1 nên phần đó triệt tiêu khi so sánh; tính vào sẽ
    thổi phồng Δ_R một chiều). Trade chỉ khớp tranche 1 → trả 0.0 (không
    phải "không đo được" — nó THỰC SỰ không có lệch nào ở tranche >= 2,
    và spec nói "mỗi lệnh" đều có một lệch-mỗi-lệnh, kể cả bằng 0)."""
    tong = 0.0
    for i in (2, 3):
        if i not in fills:
            continue
        qty_that = fills[i]["amount"]
        lech_gia = fills[i]["fill_price"] - p[i]
        tong += abs(qty_that * lech_gia / planned_risk_usdt)
    return tong


def _p90(gia_tri: list[float]) -> float:
    """Phân vị 90, nội suy tuyến tính (numpy.percentile mặc định) — spec
    không chỉ định phương pháp nội suy, ghi rõ lựa chọn để không ai tưởng
    đây là công thức duy nhất có thể."""
    xs = sorted(gia_tri)
    n = len(xs)
    if n == 1:
        return xs[0]
    vi_tri = 0.90 * (n - 1)
    duoi = math.floor(vi_tri)
    tren = math.ceil(vi_tri)
    if duoi == tren:
        return xs[duoi]
    trong_so = vi_tri - duoi
    return xs[duoi] * (1 - trong_so) + xs[tren] * trong_so


def tinh_buoc1(du_lieu_tho: dict[str, Any]) -> dict[str, KetQuaBuoc1]:
    """Tính `KetQuaBuoc1` cho cả hai hướng. Short luôn `unreadable` —
    `ZoneAbsorptionMinimal` hiện LONG-only (TD-0114), N6 cấm bịa 0.0."""
    rows = du_lieu_tho["luot_khop"]
    huong_co_that = {r["huong"] for r in rows}
    if huong_co_that - {"long", "short"}:
        raise Buoc1Error(f"Dữ liệu có hướng lạ ngoài long/short: {huong_co_that}")

    theo_trade = _gom_theo_trade(rows)

    ket_qua: dict[str, KetQuaBuoc1] = {}
    for huong_muc, huong_du_lieu in (("LONG", "long"), ("SHORT", "short")):
        trades_huong = {
            tid: fills for tid, fills in theo_trade.items()
            if any(r["huong"] == huong_du_lieu for r in fills.values())
        }
        if not trades_huong:
            ket_qua[huong_muc] = KetQuaBuoc1(
                huong=huong_muc, so_lenh=0, lech_moi_lenh=(),
                delta_r=Measured.unreadable(
                    f"chưa có lệnh {huong_muc} nào trong dữ liệu — ZoneAbsorptionMinimal "
                    "hiện LONG-only (TD-0114)"
                ),
                dung_p90=False,
            )
            continue

        lech_theo_trade: list[float] = []
        for tid, fills in trades_huong.items():
            p1 = fills[1]["p_ke_hoach"]
            sl = fills[1]["sl"]
            p = _gia_ke_hoach_ca_ba_tranche(fills[1], p1)
            cost_that = {i: fills[i]["cost"] for i in fills}
            cost_full = _uoc_luong_cost_tranche(cost_that)
            risk = _planned_risk_usdt(cost_full, p, sl)
            lech_theo_trade.append(_lech_moi_lenh(fills, p, risk))

        n = len(lech_theo_trade)
        dung_p90 = n >= SAN_N_CHO_P90
        delta = _p90(lech_theo_trade) if dung_p90 else max(lech_theo_trade)
        ket_qua[huong_muc] = KetQuaBuoc1(
            huong=huong_muc,
            so_lenh=n,
            lech_moi_lenh=tuple(lech_theo_trade),
            delta_r=Measured.ok(delta),
            dung_p90=dung_p90,
        )
    return ket_qua


def kiem_timerange_calib(rows: list[dict[str, Any]], *, config_path: Path = DEFAULT_CONFIG_PATH) -> None:
    """L-Z55 ĐÚNG NGHĨA — ngày quan sát lấy từ CHÍNH timestamp khớp lệnh
    THẬT trong dữ liệu (không phải ngày cấu hình dự kiến), đối chiếu ranh
    giới CALIB đọc từ cấu hình đã niêm phong. Hai nguồn khác nhau — đúng
    yêu cầu của `DatasetBoundary` (không tự so nó với chính nó)."""
    ts_ms = [r["fill_ts_ms"] for r in rows]
    observed_start = datetime.fromtimestamp(min(ts_ms) / 1000, tz=timezone.utc).date()
    observed_end = datetime.fromtimestamp(max(ts_ms) / 1000, tz=timezone.utc).date()
    cfg = load_tool_d_config(config_path)
    boundary = dataset_boundaries_from_config(cfg)["CALIB"]
    assert_dataset_timerange(
        dataset="CALIB", observed_start=observed_start, observed_end=observed_end, boundary=boundary
    )


def ghi_dong_ctrl(
    *,
    ledger: TrialLedger,
    du_lieu_tho_path: Path = DEFAULT_DU_LIEU_THO_PATH,
    config_path: Path = DEFAULT_CONFIG_PATH,
    repo_dir: Path = Path("."),
) -> str:
    """Ghi dòng `RESERVE budget_line=CTRL` cho phép đo Bước 1 — đo THƯỚC,
    không đánh giá cấu hình (DR-014 §2), KHÔNG tính vào N (MT-08/TD-0130).

    Khai dạng *đo thước*: `ctrl_output_whitelist` giới hạn đúng ba trường
    spec cho phép (dòng 3605-3607) — `price_delta`/`tranche_index`/
    `direction`. Đây là khai VỀ HÌNH DẠNG đầu ra thô của phép đo (mỗi lượt
    khớp là một `price_delta` gắn với một `tranche_index` và một
    `direction`), không phải giới hạn con số `Δ_R` tổng hợp cuối cùng.
    """
    cfg = load_tool_d_config(config_path)
    data_path_abs = repo_dir / du_lieu_tho_path
    provenance = build_provenance(
        params_source="yaml",
        params_effective=dict(cfg.tier_b),
        repo_dir=repo_dir,
        data_files={"dr015_luot_khop_tranche": data_path_abs},
        cache_mode="none",
        guard_passed=True,
    )
    return ledger.reserve(
        n_dang_ky=0,  # không dùng cho CTRL (bỏ qua kiểm ngân sách)
        budget_line="CTRL",
        hypothesis_slot="DR-015-BUOC1",
        direction="LONG",
        dataset="CALIB",
        param_under_test="dr015_buoc1_lech_tranche_R",
        param_value=None,
        params_frozen_hash=cfg.sha256,
        config_hash=cfg.sha256,
        code_commit=provenance.git_sha,
        provenance=provenance.to_dict(),
        contribution=1,
        ctrl_output_whitelist=["price_delta", "tranche_index", "direction"],
    )


def chay(
    *,
    du_lieu_tho_path: Path = DEFAULT_DU_LIEU_THO_PATH,
    config_path: Path = DEFAULT_CONFIG_PATH,
    registry_path: Path = DEFAULT_REGISTRY_PATH,
    repo_dir: Path = Path("."),
) -> tuple[dict[str, KetQuaBuoc1], str]:
    """Chạy trọn Bước 1: kiểm timerange -> tính Δ_R hai hướng -> ghi CTRL.

    Trả `(kết quả theo hướng, trial_id dòng CTRL)`.
    """
    du_lieu_tho = _doc_du_lieu_tho(du_lieu_tho_path)
    kiem_timerange_calib(du_lieu_tho["luot_khop"], config_path=config_path)
    ket_qua = tinh_buoc1(du_lieu_tho)
    ledger = TrialLedger(registry_path)
    trial_id = ghi_dong_ctrl(
        ledger=ledger, du_lieu_tho_path=du_lieu_tho_path, config_path=config_path, repo_dir=repo_dir
    )
    return ket_qua, trial_id
