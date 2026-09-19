"""L-Z21 + L-Z22 (spec `:3906-3914`, §6.8d/§6.8f) — TD-0338.

Hai luật này nằm trong dải *"L-Z10 → L-Z33 PASS"* của Nhánh 1 §10.2 nhưng tới 19/09/2026 **chưa có test nào mang
tên chúng** — nên tiêu chí `lz10_lz33` của gate D4 (`gates/d0_9.py`) không bao giờ đo được. `admission.py` (TD-0188)
đã thi hành §6.8f; file này KHÔNG sửa nó, chỉ khoá đúng chữ của hai luật:

    L-Z21 — Không có bản ghi nào tham chiếu `max_open_D` như một hằng số cấu hình — grep toàn bộ code: KHÔNG được
            có biến `max_open_D` đọc từ config (§6.8d).
    L-Z22 🔴 CRITICAL — Với MỌI thời điểm có vị thế mở, kiểm CẢ HAI: Σ planned_risk ≤ daily_loss_budget_pct × E_D;
            Σ planned_margin ≤ 0.85 × E_D. Tính trên KẾ HOẠCH đầy đủ 3 tranche, không phải phần đã khớp (§6.8f).

L-Z22 viết dạng THUỘC TÍNH: "với mọi thời điểm" là phát biểu về MỌI chuỗi kết nạp, nên test đi qua nhiều chuỗi ứng
viên ngẫu nhiên (seed cố định) trên `kiem_ket_nap()` THẬT, và ở cả cấu hình mà vế rủi ro bind trước (L = 10x) lẫn vế
margin bind trước (3x) — bài học `test_admission`: ở 3x trần rủi ro không bao giờ bind, nên một cài đặt chỉ kiểm
margin vẫn xanh ở mọi ca 3x.
"""

from __future__ import annotations

import random
import re
from pathlib import Path
from types import MappingProxyType

import pytest

from tool_d.admission import TRAN_MARGIN_TREN_E_D, ViTheMo, kiem_ket_nap
from tool_d.config.loader import ToolDConfig, load_tool_d_config, resolve
from tool_d.sizing import HeSoMult, lap_ke_hoach_co_lenh

REPO_ROOT = Path(__file__).resolve().parents[2]


# ── L-Z21 ────────────────────────────────────────────────────────────────────


def _dong_khong_phai_chu_thich(p: Path) -> list[tuple[int, str]]:
    ra = []
    for i, dong in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        than = dong.split("#", 1)[0]
        if than.strip():
            ra.append((i, than))
    return ra


class TestLZ21:
    def test_khong_khoa_max_open_D_trong_cau_hinh(self) -> None:
        cfg = load_tool_d_config()
        for tang in ("tier_a", "tier_b", "tier_c", "tier_frozen"):
            assert "max_open_D" not in dict(getattr(cfg, tang)), f"{tang} có khoá max_open_D (§6.8d)"

    def test_khong_dong_ma_nao_doc_max_open_D(self) -> None:
        vi_pham = []
        for thu_muc in ("src", "entrypoints", "user_data/strategies", "config"):
            for p in (REPO_ROOT / thu_muc).rglob("*"):
                if p.suffix not in (".py", ".yaml", ".yml", ".json") or not p.is_file():
                    continue
                for i, than in _dong_khong_phai_chu_thich(p):
                    if re.search(r"\bmax_open_D\b", than):
                        vi_pham.append(f"{p.relative_to(REPO_ROOT)}:{i}")
        assert not vi_pham, f"L-Z21: max_open_D là KẾT QUẢ của §6.8f, không phải tham số — {vi_pham}"


# ── L-Z22 ────────────────────────────────────────────────────────────────────


def _cfg(*, l_exchange: float, daily_loss: float = 8.0, e_d: float = 500.0, rho_pct: float = 0.375) -> ToolDConfig:
    return ToolDConfig(
        tier_a=MappingProxyType({"E_D": e_d, "rho_pct": rho_pct, "L_exchange": l_exchange,
                                 "daily_loss_budget_pct": daily_loss}),
        tier_b=MappingProxyType({}),
        tier_frozen=MappingProxyType({"w_tranche": MappingProxyType({"value": (0.3333, 0.3333, 0.3334), "dof": 0})}),
        tier_c=MappingProxyType({"n_tranches": 3}),
        raw_text="", sha256="",
    )


def _chuoi_ket_nap(cfg: ToolDConfig, seed: int, so_ung_vien: int = 60) -> list[list[ViTheMo]]:
    """Chuỗi ứng viên ngẫu nhiên; vị thế đóng ngẫu nhiên giữa chừng. Trả trạng thái danh mục SAU mỗi bước."""
    rng = random.Random(seed)
    mo: list[ViTheMo] = []
    lich_su = []
    for _ in range(so_ung_vien):
        if mo and rng.random() < 0.25:
            mo.pop(rng.randrange(len(mo)))
        mult = HeSoMult(regime=1.0, zss=rng.uniform(0.5, 1.0), corr=1.0, dd=1.0, edge=1.0, deploy=1.0)
        kh = lap_ke_hoach_co_lenh(cfg=cfg, arm="Z3", r_eff=rng.uniform(0.009, 0.03), mult=mult)
        if kiem_ket_nap(cfg=cfg, ung_vien=kh, dang_mo=mo).duoc_mo:
            mo.append(ViTheMo.tu_ke_hoach(kh))
        lich_su.append(list(mo))
    return lich_su


class TestLZ22:
    @pytest.mark.parametrize("l_exchange", [3.0, 10.0])
    @pytest.mark.parametrize("seed", range(20))
    def test_MOI_thoi_diem_ca_hai_ve_duoi_tran(self, l_exchange, seed) -> None:
        cfg = _cfg(l_exchange=l_exchange)
        e_d = float(resolve(cfg, "tier_a.E_D"))
        tran_rui_ro = float(resolve(cfg, "tier_a.daily_loss_budget_pct")) / 100 * e_d
        tran_margin = TRAN_MARGIN_TREN_E_D * e_d
        assert TRAN_MARGIN_TREN_E_D == 0.85  # chữ của L-Z22
        for mo in _chuoi_ket_nap(cfg, seed):
            assert sum(v.planned_risk_usdt for v in mo) <= tran_rui_ro + 1e-9
            assert sum(v.planned_margin_usdt for v in mo) <= tran_margin + 1e-9

    @pytest.mark.parametrize("l_exchange, ve_bind", [(3.0, "margin"), (10.0, "rủi ro")])
    def test_moi_ve_deu_tung_bind_that(self, l_exchange, ve_bind) -> None:
        """Không có ca này thì một cài đặt BỎ một vế vẫn qua ca thuộc tính ở trên — vế đó không bao giờ bị thử."""
        cfg = _cfg(l_exchange=l_exchange)
        mo: list[ViTheMo] = []
        while True:
            kh = lap_ke_hoach_co_lenh(cfg=cfg, arm="Z3", r_eff=0.015,
                                      mult=HeSoMult(regime=1.0, zss=1.0, corr=1.0, dd=1.0, edge=1.0, deploy=1.0))
            kq = kiem_ket_nap(cfg=cfg, ung_vien=kh, dang_mo=mo)
            if not kq.duoc_mo:
                assert kq.rang_buoc_siet in (ve_bind, "cả hai"), kq.dien_giai()
                break
            mo.append(ViTheMo.tu_ke_hoach(kh))

    def test_tinh_tren_ke_hoach_day_du_khong_phai_phan_da_khop(self) -> None:
        kh = lap_ke_hoach_co_lenh(cfg=_cfg(l_exchange=3.0), arm="Z3", r_eff=0.015,
                                  mult=HeSoMult(regime=1.0, zss=1.0, corr=1.0, dd=1.0, edge=1.0, deploy=1.0))
        v = ViTheMo.tu_ke_hoach(kh)
        # Kế hoạch đầy đủ = cả ba tranche: rủi ro = N_full · R_eff, margin = N_full / L — không phải một phần ba.
        assert v.planned_risk_usdt == pytest.approx(kh.n_full_usdt * kh.r_eff)
        assert v.planned_margin_usdt == pytest.approx(kh.n_full_usdt / kh.l_exchange)
