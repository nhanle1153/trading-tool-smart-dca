"""TD-0338 + TD-0339 (`DR-D4-14`, `DR-D4-15`) — test khoá cho `ablation/chi_so_export.py`.

Canh:
1. Từng chỉ số đọc đúng nguồn trong export, không đo được ⇒ `unreadable` (N6), tag TP1 lạ ⇒ raise.
2. 🔴 `DR-D4-15` §4 — lệnh khớp ĐÚNG giá kế hoạch cho tỉ số §1.7 = 1 (khử hẳn phần đại số); còn chữ cũ (so với
   `planned_risk_usdt`) cho 0,9934 ở cùng lệnh. Nếu ai đổi `D_ke` về `planned_risk` thì ca đầu ĐỎ.
3. Chạy trên export THẬT của fixture `test_td0187` (tiền lệ nạp `_chay` như `test_td0333`): mọi chỉ số tính được,
   tỉ trọng tranche ⅓⅓⅓ đạt, và §1.7 có số.
"""

from __future__ import annotations

import importlib.util
import json
import math
from datetime import date, datetime
from pathlib import Path

import pytest

from tool_d.ablation.chi_so_export import (
    TAG_TP1_NANG,
    TAG_TP1_ZONE,
    ChiSoExportError,
    bat_bien_1_7,
    bat_bien_1_7_lech,
    chi_so_tu_export,
    lenh_moi_nam,
    liq_buffer_ratio_mean,
    max_lo_don_lenh_tren_ngan_sach,
    skewness,
    spearman,
    stake_theo_r_eff,
    ti_trong_tranche,
    time_stop_ratio,
    tp_fallback_ratio,
)
from tool_d.config.loader import load_tool_d_config, resolve
from tool_d.measurement.tri_state import Measured, Status
from tool_d.sizing import doc_trong_so_tranche
from tool_d.wfo.lenh import LenhWFO

REPO_ROOT = Path(__file__).resolve().parents[2]
CFG = load_tool_d_config()
W = doc_trong_so_tranche(CFG)
P, SL = (100.0, 98.0, 96.0), 94.0


def _tag(p=P, sl=SL) -> str:
    return json.dumps({"zl": 95, "zh": 101, "p1": p[0], "p2": p[1], "p3": p[2], "sl": sl, "zs": 0.5, "t4": "UP", "sw": 0})


def _o(amount: float, gia: float, ts: int, *, vao: bool = True, tag: str | None = None) -> dict:
    return {"amount": amount, "safe_price": gia, "ft_is_entry": vao, "order_filled_timestamp": ts,
            "ft_order_tag": tag, "cost": amount * gia}


def _lenh_ba_tranche_dung_gia(n_full: float = 300.0) -> dict:
    """Ba tranche khớp ĐÚNG giá kế hoạch, notional = n_full · w_j."""
    return {"pair": "LTC/USDT:USDT", "enter_tag": _tag(), "is_short": False, "exit_reason": "TP2_TRAIL",
            "orders": [_o(n_full * w / p, p, i + 1) for i, (w, p) in enumerate(zip(W, P))]}


class TestH4:
    def test_dem_theo_tag_TP1(self) -> None:
        lenh = [{"orders": [_o(1, 100, 1), _o(0.5, 105, 2, vao=False, tag=TAG_TP1_ZONE)]},
                {"orders": [_o(1, 100, 1), _o(0.5, 103, 2, vao=False, tag=TAG_TP1_NANG)]},
                {"orders": [_o(1, 100, 1), _o(0.5, 103, 2, vao=False, tag=TAG_TP1_NANG)]},
                {"orders": [_o(1, 100, 1)]}]
        assert tp_fallback_ratio(lenh).value == pytest.approx(2 / 3)

    def test_tag_TP1_la_thi_raise(self) -> None:
        with pytest.raises(ChiSoExportError, match="lạ"):
            tp_fallback_ratio([{"orders": [_o(0.5, 103, 2, vao=False, tag="TP1_moi")]}])

    def test_khong_TP1_nao_thi_unreadable(self) -> None:
        assert tp_fallback_ratio([{"orders": [_o(1, 100, 1)]}]).status is Status.UNREADABLE


class TestChiSoDon:
    def test_time_stop(self) -> None:
        lenh = [{"exit_reason": "TIME_STOP"}, {"exit_reason": "TP2_TRAIL"}, {"exit_reason": "stop_loss"}, {"exit_reason": "TIME_STOP"}]
        assert time_stop_ratio(lenh).value == 0.5
        assert time_stop_ratio([]).status is Status.UNREADABLE

    def test_lo_don_lenh_san_khong(self) -> None:
        d = datetime(2025, 7, 1)
        assert max_lo_don_lenh_tren_ngan_sach([LenhWFO("X", d, d, -5.0, 2.0, 4.0), LenhWFO("X", d, d, 3.0, 2.0, 4.0)]).value == 1.25
        assert max_lo_don_lenh_tren_ngan_sach([LenhWFO("X", d, d, 3.0, 2.0, 4.0)]).value == 0.0

    def test_lenh_moi_nam(self) -> None:
        assert lenh_moi_nam(100, date(2025, 1, 1), date(2025, 12, 31)).value == pytest.approx(100 / (365 / 365.25))

    def test_skewness(self) -> None:
        assert skewness([1.0, 1.0, 1.0, 10.0]).value > 0
        assert skewness([1.0, 2.0]).status is Status.UNREADABLE
        assert skewness([2.0, 2.0, 2.0]).status is Status.UNREADABLE

    def test_spearman(self) -> None:
        assert spearman([1, 2, 3, 4], [10, 20, 30, 40]).value == pytest.approx(1.0)
        assert spearman([1, 2, 3, 4], [4, 3, 2, 1]).value == pytest.approx(-1.0)
        assert spearman([5, 5, 5, 5], [1, 2, 3, 4]).status is Status.UNREADABLE  # stake HẰNG SỐ


class TestBangChungDRD404:
    def test_ti_trong_dat_va_truot(self) -> None:
        assert ti_trong_tranche([_lenh_ba_tranche_dung_gia()]).value is True
        lech = _lenh_ba_tranche_dung_gia()
        lech["orders"][2]["amount"] *= 1.02
        assert ti_trong_tranche([lech]).value is False
        assert ti_trong_tranche([{"orders": [_o(1, 100, 1)]}]).status is Status.UNREADABLE

    def test_stake_theo_r_eff_rho_duong(self) -> None:
        lenh = []
        for i, sl in enumerate((97.0, 95.0, 93.0, 90.0)):  # R_eff tăng dần ⇒ notional phải giảm dần
            p_avg = sum(P) / 3
            r_eff = (p_avg - sl) / p_avg
            notional = 3.0 / r_eff
            lenh.append({"pair": "X", "enter_tag": _tag(sl=sl), "orders": [_o(notional / 100, 100, i + 1)]})
        assert stake_theo_r_eff(lenh).value == pytest.approx(1.0)


class TestBatBien17:
    def test_khop_dung_gia_ke_hoach_ty_so_BANG_mot(self) -> None:
        m = bat_bien_1_7([_lenh_ba_tranche_dung_gia()], cfg=CFG)
        assert m.value == pytest.approx(1.0, abs=1e-12)
        assert not bat_bien_1_7_lech(m)

    def test_chu_cu_so_voi_planned_risk_thi_LECH_do_dai_so(self) -> None:
        """Kiểm-có-răng DR-D4-15 §4, viết thành ca: cùng lệnh khớp hoàn hảo, so với `planned_risk` (chữ cũ §1.7)
        cho 0,9934 — tức phép so cũ thấy "lệch" dù fill không sai gì."""
        t = _lenh_ba_tranche_dung_gia()
        n_full = 300.0
        d_fill = sum(o["amount"] * (o["safe_price"] - SL) for o in t["orders"])
        p_avg = sum(P) / 3
        planned = n_full * (p_avg - SL) / p_avg
        assert d_fill / planned == pytest.approx(0.99342, abs=1e-4)

    def test_fill_lech_hon_5_phan_tram_thi_DUNG(self) -> None:
        t = _lenh_ba_tranche_dung_gia()
        for o in t["orders"][1:]:
            o["amount"] *= 1.2  # tranche 2/3 khớp khối lượng lớn hơn kế hoạch 20%
        assert bat_bien_1_7_lech(bat_bien_1_7([t], cfg=CFG))

    def test_khong_lenh_du_ba_tranche_thi_unreadable_khong_dung(self) -> None:
        m = bat_bien_1_7([{"enter_tag": _tag(), "orders": [_o(1, 100, 1)]}], cfg=CFG)
        assert m.status is Status.UNREADABLE and not bat_bien_1_7_lech(m)

    def test_lech_chi_khi_ok(self) -> None:
        assert bat_bien_1_7_lech(Measured.ok(0.94)) and bat_bien_1_7_lech(Measured.ok(1.06))
        assert not bat_bien_1_7_lech(Measured.ok(0.96))


class TestLiqBuffer:
    def test_cong_thuc_spec_1866(self) -> None:
        # p_avg = 98, sl = 94 ⇒ mẫu số 4; liq 66 ⇒ (98 − 66) / 4 = 8,0 ; liq 58 ⇒ 10,0 ; trung bình 9,0
        lenh = [{"enter_tag": _tag(), "liquidation_price": 66.0}, {"enter_tag": _tag(), "liquidation_price": 58.0}]
        assert liq_buffer_ratio_mean(lenh).value == pytest.approx(9.0)

    def test_thieu_mot_lenh_thi_unreadable_khong_bo_lenh(self) -> None:
        lenh = [{"enter_tag": _tag(), "liquidation_price": 66.0}, {"enter_tag": _tag(), "liquidation_price": None}]
        m = liq_buffer_ratio_mean(lenh)
        assert m.status is Status.UNREADABLE and "1/2" in m.note


class TestTongHop:
    def test_short_bi_tu_choi(self) -> None:
        with pytest.raises(ChiSoExportError, match="SHORT"):
            chi_so_tu_export(lenh=[{"is_short": True}], lenhs=[], cfg=CFG,
                             observed_start=date(2025, 1, 1), observed_end=date(2025, 2, 1))


def _nap_td0187():
    spec = importlib.util.spec_from_file_location(
        "td0187_cs", REPO_ROOT / "tests" / "lock" / "test_td0187_dinh_co_lenh_backtest_that.py"
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def export_that(tmp_path_factory):
    from tool_d.bo_chay.trich_lenh import lenh_tu_freqtrade

    td = _nap_td0187()
    tmp = tmp_path_factory.mktemp("td0338")
    kq = td._chay(tmp, td.SAN_XUAT)
    cfg = load_tool_d_config(tmp / "config" / "tool_d_config.yaml")
    lenhs = [lenh_tu_freqtrade(t, cfg=cfg, arm="Z3") for t in kq["trades"]]
    return kq["trades"], lenhs, cfg


class TestExportThat:
    def test_moi_chi_so_tinh_duoc_va_tranche_dat(self, export_that) -> None:
        lenh, lenhs, cfg = export_that
        cs = chi_so_tu_export(lenh=lenh, lenhs=lenhs, cfg=cfg,
                              observed_start=date(2025, 3, 15), observed_end=date(2025, 4, 1))
        for k in ("time_stop_ratio", "max_single_trade_loss_over_risk_budget", "trades_per_year",
                  "ti_trong_tranche_dat", "bat_bien_1_7_ty_so_trung_vi"):
            assert cs[k].status is Status.OK, (k, cs[k])
        # TD-0342 — đo 19/09/2026: backtest fixture TỔNG HỢP cho `liquidation_price = None` (Freqtrade cần bảng bậc
        # đòn bẩy của cặp, `get_maintenance_ratio_and_amt`). Chỉ số phải NÓI RA điều đó, không bịa số (N6).
        # Export trên rổ thật có giá thanh lý hay không: CHƯA đo (khâu đo khoá) — xem TD-0343.
        assert cs["liq_buffer_ratio_mean"].status is Status.UNREADABLE
        assert "liquidation_price" in cs["liq_buffer_ratio_mean"].note
        assert cs["ti_trong_tranche_dat"].value is True
        assert math.isfinite(cs["bat_bien_1_7_ty_so_trung_vi"].value)
        assert resolve(cfg, "tier_a.L_exchange") > 0
