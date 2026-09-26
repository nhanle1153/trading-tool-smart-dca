"""TD-0385 (`DR-D11-01` §5, `DR-D10-02` §2 mục 5 + §5.3, `DR-CONG-AN-TOAN-01` §3.2) — bộ đo BA ngưỡng D10 cho lệnh DCA.

Anh em của `ops/do_d10.py` (TD-0413, bản cho `RoFunding` lệnh thị trường). File này dành cho chiến lược CÓ DCA + post-only
— hôm nay là `CtrlD10`. Ngưỡng là bản gốc ở DR (N1), file này chỉ thi hành:

- **D2c `gap_ms`** (`DR-D11-01` §5.2): p99 qua ≥ 30 sự kiện đổi khối lượng SL (bản ghi `DOI_SL`, `nguon = live`)
  **≤ 15.000 ms**. `n < 30` ⇒ báo p99 trên N thật, ghi hạn chế, KHÔNG thay bằng max; D10 chưa đạt (`DR-D10-02` Q5).
  🔴 Hạn chế phải đọc kèm: mẫu cưỡng bức chỉ đo ĐỘ DÀI khoảng trống, không đo xác suất trùng lúc giá chạy ngược.
- **Post-only** (`DR-D11-01` §5.3): KHÔNG có ngưỡng %. Lệnh vào kết thúc mà sàn từ chối (`expired`/`rejected`, không
  khớp), khớp một phần, hoặc huỷ không khớp ⇒ BẤT KỲ ca nào cũng là bằng chứng một lỗ mù có thật ⇒ trình chủ dự án,
  không tự phán (verdict không thể là KEPT).
- **D6 lệch khớp** (`DR-D11-01` §5.1, công thức `DR-D35-01` §4): chỉ tranche ≥ 2 đã khớp.
  • Có `planned_risk_usdt` (chiến lược có kế hoạch rủi ro): `lệch_R = Σ filled·|average − ft_price| / planned_risk`,
    thống kê P90 khi `n ≥ 30`, ngược lại **max** (fail-closed, `DR-D35-01` §4 — cách đọc ghi ở `DR-CONG-AN-TOAN-01` §4),
    so với Δ_R LONG niêm phong. Vượt ⇒ REJECTED (L2, trình chủ dự án — không lấy số D10 làm số mới).
  • Lệnh CTRL (không có kế hoạch zone): CHỈ báo trượt giá bps, KHÔNG so Δ_R (`DR-D10-02` Q1). D10 PASS trên CTRL chỉ
    chứng nhận HẠ TẦNG ⇒ `dat_dieu_kien_d12 = False` luôn, cho tới khi D6 đo trên chiến lược thật.

🔴 N6 — `orders.average` chỉ có nghĩa khi `filled > 0` (dry-run gán `average = giá đặt` ngay lúc TẠO lệnh — từ điển,
TD-0441). Mọi phép đọc giá khớp ở đây lọc `filled > 0` trước. Số hỏng (≤ 0, NaN) ⇒ đếm "không đọc được", không đoán.

Kết cục (sổ trial chỉ nhận ba giá trị): `REJECTED` = vượt ngưỡng · `INCONCLUSIVE` = thiếu mẫu / lỗ mù post-only / số
không đọc được / đợt chưa kết thúc · `KEPT` = không lý do nào ở trên. Đầu ra chi tiết đúng danh sách cho phép
`CTRL_VAN_HANH_ALLOWED` (`fill_price`, `p_i`, `order_status`, `gap_ms`).
"""

from __future__ import annotations

import json
import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tool_d.dr015.buoc2_chi_tiet import _phan_vi
from tool_d.gap_ms import LOAI_DOI_SL
from tool_d.ops.ngan_sach_d10 import DU_SU_KIEN_DOI_SL

NGUONG_GAP_MS_P99 = 15_000.0  # DR-D11-01 §5.2 — ranh giới rủi ro TD-0116; hằng vận hành đã chốt bằng DR (khuôn ngan_sach_d10)
DU_MAU_D6 = 30  # DR-D35-01 §4: n ≥ 30 ⇒ P90, ngược lại max
FILE_DELTA_R = Path("docs/du-lieu-do/dr015-buoc1-delta-r.json")  # DR-D11-01 §5.1 — Δ_R niêm phong D3.5
TAG_CTRL = "CTRL_D10"  # = `CtrlD10.TAG_CTRL` (khoá bằng test) — nhãn `trades.enter_tag` của lệnh CTRL
NGUON_LIVE = "live"

TRANG_THAI_KET_THUC = frozenset({"closed", "canceled", "expired", "rejected"})
TRANG_THAI_SAN_TU_CHOI = frozenset({"expired", "rejected"})  # Binance GTX: post-only sẽ khớp ngay ⇒ sàn cho hết hạn

LY_DO_CTRL_KHONG_SO_DELTA_R = (
    "D6 trên lệnh CTRL chỉ báo trượt giá bps, KHÔNG so Δ_R (DR-D10-02 Q1): CTRL không có kế hoạch zone ⇒ D6 phải đo lại "
    "trên chiến lược thật trước D12"
)
HAN_CHE_GAP_MS = (
    "mẫu cưỡng bức chỉ đo ĐỘ DÀI khoảng trống cancel→recreate, KHÔNG đo XÁC SUẤT trùng lúc giá chạy ngược mạnh "
    "(DR-D11-01 §5.2, DR-D11-02 §3.2)"
)


class DoD10DcaError(RuntimeError):
    """Không đo được một cách trung thực — fail-closed (N6)."""


# ─────────────────────────────── đầu vào thuần ───────────────────────────────


@dataclass(frozen=True)
class LenhDat:
    """Một dòng `orders` rút gọn đúng những cột đã tra từ điển (TD-0441)."""

    trade_id: int
    order_id: str
    vai_tro: str  # "vao" · "ra" · "stoploss"
    loai_lenh: str | None  # orders.order_type
    trang_thai: str | None  # orders.status
    gia_ke_hoach: float | None  # orders.ft_price — p_i
    gia_khop_tb: float | None  # orders.average — CHỈ có nghĩa khi da_khop > 0
    khoi_luong: float | None  # orders.amount
    da_khop: float | None  # orders.filled
    moc_khop: datetime | None  # orders.order_filled_date


def _so_hop_le(x: float | None) -> bool:
    return x is not None and math.isfinite(x) and x > 0


def _utc(moc: datetime) -> datetime:
    return moc.replace(tzinfo=timezone.utc) if moc.tzinfo is None else moc.astimezone(timezone.utc)


# ─────────────────────────────── ba phép đo ───────────────────────────────


@dataclass(frozen=True)
class KetQuaGap:
    n: int
    p99: float | None
    max: float | None


def do_gap_ms(gia_tri: Iterable[float]) -> KetQuaGap:
    xs = [float(x) for x in gia_tri]
    hong = [x for x in xs if not math.isfinite(x) or x < 0]
    if hong:
        raise DoD10DcaError(f"gap_ms hỏng trong sổ: {hong[:5]} — không đo trên số rác (N6)")
    if not xs:
        return KetQuaGap(n=0, p99=None, max=None)
    return KetQuaGap(n=len(xs), p99=_phan_vi(xs, 0.99), max=max(xs))


@dataclass(frozen=True)
class KetQuaPostOnly:
    so_lenh_vao_ket_thuc: int
    san_tu_choi: tuple[str, ...]
    khop_mot_phan: tuple[str, ...]
    huy_khong_khop: tuple[str, ...]
    dang_mo: tuple[str, ...]
    khong_doc_duoc: tuple[str, ...]


def do_post_only(lenh: Iterable[LenhDat]) -> KetQuaPostOnly:
    """Phân loại mọi lệnh VÀO dạng limit. Không có ngưỡng % (DR-D11-01 §5.3)."""
    ket_thuc = 0
    tu_choi: list[str] = []
    mot_phan: list[str] = []
    huy: list[str] = []
    mo: list[str] = []
    hong: list[str] = []
    for x in lenh:
        if x.vai_tro != "vao" or x.loai_lenh != "limit":
            continue
        if x.trang_thai not in TRANG_THAI_KET_THUC:
            (mo if x.trang_thai == "open" else hong).append(x.order_id)
            continue
        if x.da_khop is None or x.khoi_luong is None or not math.isfinite(x.da_khop) or not _so_hop_le(x.khoi_luong):
            hong.append(x.order_id)
            continue
        ket_thuc += 1
        if 0 < x.da_khop < x.khoi_luong:
            mot_phan.append(x.order_id)
        elif x.da_khop == 0 and x.trang_thai in TRANG_THAI_SAN_TU_CHOI:
            tu_choi.append(x.order_id)
        elif x.da_khop == 0:
            huy.append(x.order_id)
    return KetQuaPostOnly(ket_thuc, tuple(tu_choi), tuple(mot_phan), tuple(huy), tuple(mo), tuple(hong))


def tranche_da_khop(lenh_cua_trade: Iterable[LenhDat]) -> list[tuple[int, LenhDat]]:
    """(số tranche, lệnh) của các lệnh VÀO đã khớp (`filled > 0`), theo mốc khớp — cùng cách đếm
    `nr_of_successful_entries` của Freqtrade mà `CtrlD10` dùng để chọn p2/p3."""
    khop = [x for x in lenh_cua_trade if x.vai_tro == "vao" and x.da_khop is not None and x.da_khop > 0]
    if any(x.moc_khop is None for x in khop):
        raise DoD10DcaError(f"lệnh vào đã khớp mà thiếu order_filled_date: {[x.order_id for x in khop if x.moc_khop is None]}")
    khop.sort(key=lambda x: _utc(x.moc_khop))  # type: ignore[arg-type]
    return [(i + 1, x) for i, x in enumerate(khop)]


@dataclass(frozen=True)
class KetQuaD6:
    so_voi_delta_r: bool
    n_tranche: int  # số tranche ≥ 2 đã khớp đọc được
    n_lenh: int  # số lệnh (trade) góp vào thống kê theo R_realized
    lech_bps_p90: float | None
    lech_bps_max: float | None
    thong_ke_r: float | None  # P90 (n ≥ 30) hoặc max (n < 30) của lệch-mỗi-lệnh, đơn vị R_realized
    dung_p90: bool | None
    delta_r: float | None
    khong_doc_duoc: tuple[str, ...]
    chi_tiet: tuple[dict[str, Any], ...] = field(default_factory=tuple)


def do_d6(
    lenh: Iterable[LenhDat],
    *,
    planned_risk: Mapping[int, float] | None,
    delta_r: float | None,
) -> KetQuaD6:
    """`planned_risk is None` ⇒ chế độ CTRL (chỉ bps). Ngược lại mỗi trade có tranche ≥ 2 phải có planned_risk > 0."""
    theo_trade: dict[int, list[LenhDat]] = {}
    for x in lenh:
        theo_trade.setdefault(x.trade_id, []).append(x)

    bps: list[float] = []
    lech_moi_lenh: list[float] = []
    hong: list[str] = []
    chi_tiet: list[dict[str, Any]] = []
    for trade_id in sorted(theo_trade):
        tong_r = 0.0
        trade_hong = False
        for tranche, x in tranche_da_khop(theo_trade[trade_id]):
            if tranche < 2:
                continue
            if not (_so_hop_le(x.gia_khop_tb) and _so_hop_le(x.gia_ke_hoach)):
                hong.append(x.order_id)
                trade_hong = True
                continue
            lech_gia = abs(x.gia_khop_tb - x.gia_ke_hoach)  # type: ignore[operator]
            b = lech_gia / x.gia_ke_hoach * 10_000  # type: ignore[operator]
            bps.append(b)
            chi_tiet.append({"trade_id": trade_id, "tranche": tranche, "fill_price": x.gia_khop_tb,
                             "p_i": x.gia_ke_hoach, "order_status": x.trang_thai, "lech_bps": b})
            if planned_risk is not None:
                pr = planned_risk.get(trade_id)
                if not _so_hop_le(pr):
                    hong.append(x.order_id)
                    trade_hong = True
                    continue
                tong_r += x.da_khop * lech_gia / pr  # type: ignore[operator]
        if planned_risk is not None and not trade_hong:
            lech_moi_lenh.append(tong_r)  # trade chỉ khớp tranche 1 ⇒ 0.0 thật (DR-D35-01 §4)

    thong_ke: float | None = None
    dung_p90: bool | None = None
    if planned_risk is not None and lech_moi_lenh:
        dung_p90 = len(lech_moi_lenh) >= DU_MAU_D6
        thong_ke = _phan_vi(lech_moi_lenh, 0.90) if dung_p90 else max(lech_moi_lenh)
    return KetQuaD6(
        so_voi_delta_r=planned_risk is not None,
        n_tranche=len(bps),
        n_lenh=len(lech_moi_lenh),
        lech_bps_p90=_phan_vi(bps, 0.90) if bps else None,
        lech_bps_max=max(bps) if bps else None,
        thong_ke_r=thong_ke,
        dung_p90=dung_p90,
        delta_r=delta_r if planned_risk is not None else None,
        khong_doc_duoc=tuple(hong),
        chi_tiet=tuple(chi_tiet),
    )


# ─────────────────────────────── phán quyết ───────────────────────────────


@dataclass(frozen=True)
class KetQuaD10Dca:
    gap: KetQuaGap
    post_only: KetQuaPostOnly
    d6: KetQuaD6
    verdict: str
    ly_do: tuple[str, ...]
    dat_dieu_kien_d12: bool

    def ra_dict(self) -> dict[str, Any]:
        g, p, d = self.gap, self.post_only, self.d6
        return {
            "nguon": "TD-0385 — DR-D11-01 §5, DR-D10-02 §2 mục 5 + §5.3, DR-CONG-AN-TOAN-01",
            "gap_ms": {"n": g.n, "p99": g.p99, "max": g.max, "nguong_p99": NGUONG_GAP_MS_P99,
                       "du_mau": DU_SU_KIEN_DOI_SL, "han_che": HAN_CHE_GAP_MS},
            "post_only": {"so_lenh_vao_ket_thuc": p.so_lenh_vao_ket_thuc, "san_tu_choi": list(p.san_tu_choi),
                          "khop_mot_phan": list(p.khop_mot_phan), "huy_khong_khop": list(p.huy_khong_khop),
                          "dang_mo": list(p.dang_mo), "khong_doc_duoc": list(p.khong_doc_duoc),
                          "tham_chieu": "p_nf_cao = 0,0% (dr015-buoc2-ty-le-khong-khop.json) — không ngưỡng %"},
            "d6": {"so_voi_delta_r": d.so_voi_delta_r, "n_tranche": d.n_tranche, "n_lenh": d.n_lenh,
                   "lech_bps_p90": d.lech_bps_p90, "lech_bps_max": d.lech_bps_max, "thong_ke_r": d.thong_ke_r,
                   "dung_p90": d.dung_p90, "delta_r": d.delta_r, "khong_doc_duoc": list(d.khong_doc_duoc),
                   "ghi_chu": None if d.so_voi_delta_r else LY_DO_CTRL_KHONG_SO_DELTA_R},
            "verdict": self.verdict,
            "ly_do": list(self.ly_do),
            "dat_dieu_kien_d12": self.dat_dieu_kien_d12,
            "chi_tiet_d6": list(d.chi_tiet),
        }


def danh_gia(gap: KetQuaGap, post_only: KetQuaPostOnly, d6: KetQuaD6) -> KetQuaD10Dca:
    fail: list[str] = []
    if gap.n >= DU_SU_KIEN_DOI_SL and gap.p99 is not None and gap.p99 > NGUONG_GAP_MS_P99:
        fail.append(f"p99(gap_ms) {gap.p99:.0f} ms > {NGUONG_GAP_MS_P99:.0f} ms qua {gap.n} sự kiện — hạ L_exchange "
                    "hoặc ghi rủi ro tồn dư: chủ dự án chọn (DR-D11-01 §5.2)")
    if d6.so_voi_delta_r and d6.thong_ke_r is not None and d6.delta_r is not None and d6.thong_ke_r > d6.delta_r:
        fail.append(f"D6 {'P90' if d6.dung_p90 else 'max'} lệch {d6.thong_ke_r:.6f} R_realized > Δ_R {d6.delta_r:.6f} R_realized — "
                    "L2 (§11b.1), trình chủ dự án, KHÔNG lấy số D10 làm số mới (DR-D11-01 §5.1)")

    chua: list[str] = []
    if gap.n < DU_SU_KIEN_DOI_SL:
        chua.append(f"gap_ms n = {gap.n} < {DU_SU_KIEN_DOI_SL}: p99 trên N thật là hạn chế — D10 chưa đạt (DR-D10-02 Q5)")
    lo_mu = len(post_only.san_tu_choi) + len(post_only.khop_mot_phan) + len(post_only.huy_khong_khop)
    if lo_mu:
        chua.append(f"post-only: {len(post_only.san_tu_choi)} sàn từ chối · {len(post_only.khop_mot_phan)} khớp một phần · "
                    f"{len(post_only.huy_khong_khop)} huỷ không khớp — lỗ mù có thật, ghi research-log + trình chủ dự án "
                    "(DR-D11-01 §5.3)")
    if post_only.so_lenh_vao_ket_thuc == 0:
        chua.append("không có lệnh vào limit nào kết thúc — chưa có gì để đo post-only")
    if post_only.dang_mo:
        chua.append(f"{len(post_only.dang_mo)} lệnh vào còn mở — đợt chưa kết thúc")
    hong = post_only.khong_doc_duoc + d6.khong_doc_duoc
    if hong:
        chua.append(f"{len(hong)} lệnh không đọc được số — không đoán (N6): {list(hong)[:5]}")
    if d6.so_voi_delta_r and d6.thong_ke_r is None:
        chua.append("D6 chưa có lệnh nào khớp tranche ≥ 2 đọc được — chưa so được Δ_R")

    if fail:
        verdict, ly_do = "REJECTED", fail + chua
    elif chua:
        verdict, ly_do = "INCONCLUSIVE", chua
    else:
        verdict, ly_do = "KEPT", []
    if not d6.so_voi_delta_r:
        ly_do = [*ly_do, LY_DO_CTRL_KHONG_SO_DELTA_R]
    return KetQuaD10Dca(gap=gap, post_only=post_only, d6=d6, verdict=verdict, ly_do=tuple(ly_do),
                        dat_dieu_kien_d12=verdict == "KEPT" and d6.so_voi_delta_r)


def ket_cuc_so_trial(kq: KetQuaD10Dca) -> dict[str, Any]:
    """`outcome` của CONSUME — schema sổ chỉ nhận bốn khoá; D10 đo MÁY nên không có kỳ vọng / Sharpe / lỗ lớn nhất.
    `n_trades` = số lệnh vào đã kết thúc. Chi tiết nằm ở hiện vật (`seal_path`)."""
    return {"expectancy": None, "sharpe": None, "n_trades": kq.post_only.so_lenh_vao_ket_thuc, "max_single_loss_ratio": None}


# ─────────────────────────────── tầng đọc ───────────────────────────────


def doc_delta_r_long(repo_dir: Path = Path(".")) -> float:
    """Δ_R LONG từ artifact niêm phong D3.5 — không số mới (DR-D11-01 §5)."""
    d = json.loads((repo_dir / FILE_DELTA_R).read_text(encoding="utf-8"))
    long_ = d["delta_r"]["LONG"]
    if long_.get("trang_thai") != "ok" or not _so_hop_le(long_.get("gia_tri")):
        raise DoD10DcaError(f"Δ_R LONG niêm phong không đọc được: {long_!r}")
    return float(long_["gia_tri"])


def doc_gap_ms_live(duong: Path) -> list[float]:
    """`gap_ms` của mọi bản ghi `DOI_SL` nguồn `live`. Sổ chưa có ⇒ `[]` (chưa có sự kiện); đọc hỏng ⇒ RAISE (N6:
    rỗng-vì-lỗi khác rỗng-vì-chưa-có)."""
    if not duong.exists():
        return []
    ra: list[float] = []
    for so_dong, dong in enumerate(duong.read_text(encoding="utf-8").splitlines(), start=1):
        if not dong.strip():
            continue
        try:
            d = json.loads(dong)
        except json.JSONDecodeError as exc:
            raise DoD10DcaError(f"{duong}:{so_dong} không phải JSON: {exc}") from exc
        if d.get("loai") == LOAI_DOI_SL and d.get("nguon") == NGUON_LIVE:
            if "gap_ms" not in d:
                raise DoD10DcaError(f"{duong}:{so_dong} bản ghi DOI_SL thiếu gap_ms")
            ra.append(float(d["gap_ms"]))
    return ra


def doc_lenh_db(db_url: str) -> list[LenhDat]:
    """Đọc `orders` của DB live qua ORM của chính Freqtrade (khuôn `reporting/freqtrade_db.py`). Mọi trade phải là lệnh
    CTRL (`enter_tag == TAG_CTRL`): bộ đo DCA không phán lệnh của chiến lược khác (RoFunding dùng `ops/do_d10.py`)."""
    tien_to = "sqlite:///"
    if not db_url.startswith(tien_to):
        raise DoD10DcaError(f"chỉ đọc DB SQLite, nhận {db_url!r}")
    if not Path(db_url[len(tien_to):]).is_file():
        # `init_db` trên đường chưa có file sẽ TẠO một DB rỗng — rồi bộ đo báo "0 lệnh" như thể đã đo (N6: pending).
        raise DoD10DcaError(f"DB live chưa tồn tại: {db_url} — D10 chưa chạy, chưa có gì để đo (pending)")
    try:
        from freqtrade.persistence import Trade, init_db
    except ImportError as exc:  # pragma: no cover - chỉ xảy ra ngoài Docker
        raise DoD10DcaError(f"không import được freqtrade.persistence: {exc} — chạy trong ảnh project (N7)") from exc
    try:
        init_db(db_url)
        trades = Trade.get_trades().all()
    except Exception as exc:  # noqa: BLE001 - fail-closed, bọc lại thành lỗi có tên
        raise DoD10DcaError(f"đọc DB {db_url!r} thất bại: {exc}") from exc

    la = [t.id for t in trades if t.enter_tag != TAG_CTRL]
    if la:
        raise DoD10DcaError(f"DB có trade không phải lệnh CTRL ({TAG_CTRL}): {la[:10]} — bộ đo DCA không áp")
    ra: list[LenhDat] = []
    for t in trades:
        for o in t.orders:
            if o.ft_order_side == "stoploss":
                vai_tro = "stoploss"
            elif o.ft_order_side == t.entry_side:
                vai_tro = "vao"
            else:
                vai_tro = "ra"
            ra.append(LenhDat(
                trade_id=int(t.id),
                order_id=str(o.order_id),
                vai_tro=vai_tro,
                loai_lenh=o.order_type,
                trang_thai=o.status,
                gia_ke_hoach=o.ft_price,
                gia_khop_tb=o.average,
                khoi_luong=o.amount,
                da_khop=o.filled,
                moc_khop=o.order_filled_date,
            ))
    return ra


def do_d10_dca(*, db_url: str, decision_log: Path) -> KetQuaD10Dca:
    """Đo cả ba ngưỡng trên DB live + sổ Decision Log live. Lệnh CTRL ⇒ D6 chế độ bps: không planned_risk, không so
    Δ_R (`DR-D10-02` Q1). Chiến lược DCA thật sau này nối `planned_risk` + `doc_delta_r_long()` vào `do_d6`."""
    lenh = doc_lenh_db(db_url)
    return danh_gia(
        do_gap_ms(doc_gap_ms_live(decision_log)),
        do_post_only(lenh),
        do_d6(lenh, planned_risk=None, delta_r=None),
    )
