"""TD-0384 chặng 2b — `CtrlD10` nối đúng ba module thuần vào callback Freqtrade.

Dựng chiến lược THẬT bằng `import` (không `spec_from_file_location`) để công cụ phá-thật trong bộ nhớ thấy được; trade,
ví, sàn là đối tượng GIẢ tối thiểu. Có ca trộn ngày giờ naive/aware (SQLite vs bộ nhớ — bài học TD-0403)."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
from freqtrade.strategy import stoploss_from_absolute

from tool_d.ledger.decision_log import duong_dan_decision_log
from tool_d.notional import bo_loc_tu_market, san_tool_d
from tool_d.ops.ctrl_d10 import LY_DO_THOAT_DU_3, LY_DO_THOAT_HET_GIO, notional_moi_tranche

REPO_ROOT = Path(__file__).resolve().parents[2]
UTC = timezone.utc
T0 = datetime(2026, 10, 1, 12, tzinfo=UTC)
CAP = "DOGE/USDT:USDT"
MARKET = {"limits": {"cost": {"min": 5.0}, "amount": {"min": 1.0}}, "precision": {"amount": 1.0}}


def _module():
    duong = str(REPO_ROOT / "user_data/strategies")
    if duong not in sys.path:
        sys.path.insert(0, duong)
    import CtrlD10  # noqa: PLC0415

    return CtrlD10


def _chien_luoc(monkeypatch, *, trades=(), so_du=200.0, runmode="dry_run"):
    m = _module()
    s = m.CtrlD10(config={"stake_currency": "USDT", "exchange": {"name": "binance"}})
    s.dp = SimpleNamespace(runmode=SimpleNamespace(value=runmode), _exchange=SimpleNamespace(_markets={CAP: MARKET}))

    def get_total(_):
        if so_du is None:
            raise RuntimeError("ví không đọc được")
        return so_du

    s.wallets = SimpleNamespace(get_total=get_total)
    monkeypatch.setattr(m.Trade, "get_trades_proxy", staticmethod(lambda **_: list(trades)))
    return s


class _Trade(SimpleNamespace):
    def get_custom_data(self, k):
        return self.custom.get(k)

    def set_custom_data(self, k, v):
        self.custom[k] = v


def _trade(**ghi_de) -> _Trade:
    goc = dict(
        id=1, pair=CAP, custom={}, nr_of_successful_entries=1, has_open_orders=False, leverage=3.0, orders=[],
        entry_side="buy", open_date=T0.replace(tzinfo=None), stake_amount=10.0, is_open=True,
    )
    goc.update(ghi_de)
    return _Trade(**goc)


def _lenh(side, status, filled=None, **k):
    return SimpleNamespace(ft_order_side=side, status=status, order_filled_date=filled, **k)


class TestTinHieu:
    def test_luon_bat_tin_hieu_vao_de_may_canh_quyet(self, monkeypatch) -> None:
        df = _chien_luoc(monkeypatch).populate_entry_trend(pd.DataFrame({"close": [1.0, 2.0]}), {"pair": CAP})
        assert list(df["enter_long"]) == [1, 1]


class TestGiaTranche:
    def test_tranche_1_dung_gia_mua_tot_nhat(self, monkeypatch) -> None:
        s = _chien_luoc(monkeypatch)
        assert s.custom_entry_price(CAP, None, T0, 0.123, "CTRL_D10", "long") == 0.123

    @pytest.mark.parametrize(("da_khop", "gia"), [(1, 99.7), (2, 99.4)])
    def test_tranche_2_3_cho_o_muc_ke_hoach(self, monkeypatch, da_khop, gia) -> None:
        s = _chien_luoc(monkeypatch)
        t = _trade(custom={"ctrl_p1": 100.0}, nr_of_successful_entries=da_khop)
        assert s.custom_entry_price(CAP, t, T0, 101.0, "CTRL_D10", "long") == pytest.approx(gia)


class TestNganSachVaoLenh:
    def test_chua_co_vi_the_thi_cho_vao(self, monkeypatch) -> None:
        s = _chien_luoc(monkeypatch)
        assert s.confirm_trade_entry(CAP, "limit", 100.0, 0.3, "PO", T0, "CTRL_D10", "long") is True

    def test_con_vi_the_mo_thi_tu_choi_tuan_tu(self, monkeypatch) -> None:
        s = _chien_luoc(monkeypatch, trades=[_trade()])
        assert s.confirm_trade_entry(CAP, "limit", 100.0, 0.3, "PO", T0, "CTRL_D10", "long") is False

    def test_du_20_vi_the_thi_tu_choi(self, monkeypatch) -> None:
        dong = [_trade(id=i, is_open=False) for i in range(20)]
        s = _chien_luoc(monkeypatch, trades=dong)
        assert s.confirm_trade_entry(CAP, "limit", 100.0, 0.3, "PO", T0, "CTRL_D10", "long") is False

    def test_khong_doc_duoc_so_du_thi_tu_choi(self, monkeypatch) -> None:
        s = _chien_luoc(monkeypatch, so_du=None)
        assert s.confirm_trade_entry(CAP, "limit", 100.0, 0.3, "PO", T0, "CTRL_D10", "long") is False


class TestThemTranche:
    def test_binh_thuong_tra_stake_bang_notional_chia_don_bay(self, monkeypatch) -> None:
        s = _chien_luoc(monkeypatch)
        t = _trade(custom={"ctrl_p1": 100.0})
        kq = s.adjust_trade_position(t, T0, 100.0, 0, 5, 1000, 100.0, 100.0, 0, 0)
        san = san_tool_d(bo_loc_tu_market(CAP, MARKET, gia=99.7), strategy_stoploss=-0.99)
        assert kq == pytest.approx(notional_moi_tranche(san, s._ts) / 3.0)

    @pytest.mark.parametrize(
        "ghi_de",
        [{"has_open_orders": True}, {"nr_of_successful_entries": 3}, {"custom": {}}],
        ids=["lenh-dang-cho", "du-3-tranche", "thieu-p1"],
    )
    def test_cac_ca_khong_dat_tranche(self, monkeypatch, ghi_de) -> None:
        s = _chien_luoc(monkeypatch)
        t = _trade(**{"custom": {"ctrl_p1": 100.0}, **ghi_de})
        assert s.adjust_trade_position(t, T0, 100.0, 0, 5, 1000, 100.0, 100.0, 0, 0) is None

    def test_gia_da_duoi_muc_cho_thi_khong_dat_post_only(self, monkeypatch) -> None:
        s = _chien_luoc(monkeypatch)
        t = _trade(custom={"ctrl_p1": 100.0})
        assert s.adjust_trade_position(t, T0, 99.5, 0, 5, 1000, 100.0, 99.5, 0, 0) is None

    def test_vuot_tran_ky_quy_thi_khong_bom(self, monkeypatch) -> None:
        mo = _trade(custom={"ctrl_p1": 100.0}, stake_amount=99.0)
        s = _chien_luoc(monkeypatch, trades=[mo], so_du=200.0)
        assert s.adjust_trade_position(mo, T0, 100.0, 0, 5, 1000, 100.0, 100.0, 0, 0) is None


class TestStoploss:
    def test_sl_tuyet_doi_p1_tru_2_phan_tram(self, monkeypatch) -> None:
        s = _chien_luoc(monkeypatch)
        t = _trade(custom={"ctrl_p1": 100.0})
        kq = s.custom_stoploss(CAP, t, T0, 100.0, 0.0)
        assert kq == pytest.approx(stoploss_from_absolute(98.0, 100.0, is_short=False, leverage=3.0))

    def test_so_do_no_van_tra_sl(self, monkeypatch, caplog) -> None:
        s = _chien_luoc(monkeypatch)

        def no(trade, *, sl_price):
            raise TypeError("can't compare offset-naive and offset-aware datetimes")

        s._ghi_gap_ms = no
        with caplog.at_level(logging.ERROR):
            kq = s.custom_stoploss(CAP, _trade(custom={"ctrl_p1": 100.0}), T0, 100.0, 0.0)
        assert kq is not None and kq > 0
        assert any("TD-0384" in r.getMessage() for r in caplog.records if r.levelno >= logging.ERROR)

    def test_thieu_p1_thi_giu_sl_hien_co(self, monkeypatch) -> None:
        assert _chien_luoc(monkeypatch).custom_stoploss(CAP, _trade(), T0, 100.0, 0.0) is None


class TestThoat:
    def test_du_3_tranche_10_phut_thi_thoat_voi_ngay_gio_tron_kieu(self, monkeypatch) -> None:
        """`order_filled_date` naive (SQLite), `current_time` aware — không được nổ TypeError (TD-0403)."""
        s = _chien_luoc(monkeypatch)
        cuoi = (T0 + timedelta(minutes=30)).replace(tzinfo=None)
        t = _trade(nr_of_successful_entries=3, orders=[_lenh("buy", "closed", cuoi)])
        assert s.custom_exit(CAP, t, T0 + timedelta(minutes=40), 100.0, 0.0) == LY_DO_THOAT_DU_3

    def test_4_gio_thi_thoat(self, monkeypatch) -> None:
        s = _chien_luoc(monkeypatch)
        t = _trade(orders=[_lenh("buy", "closed", T0.replace(tzinfo=None))])
        assert s.custom_exit(CAP, t, T0 + timedelta(hours=4), 100.0, 0.0) == LY_DO_THOAT_HET_GIO


class TestSoDecisionLog:
    def test_order_filled_ghi_p1_mot_lan_va_ghi_so_theo_runmode(self, monkeypatch, tmp_path) -> None:
        s = _chien_luoc(monkeypatch)
        monkeypatch.chdir(tmp_path)
        t = _trade()
        lenh = SimpleNamespace(
            ft_order_side="buy", order_id="o1", order_filled_date=T0, safe_price=0.25, safe_amount_after_fee=40.0,
        )
        s.order_filled(CAP, t, lenh, T0)
        s.order_filled(CAP, t, SimpleNamespace(**{**vars(lenh), "safe_price": 0.2}), T0)  # không ghi đè p1
        assert t.custom["ctrl_p1"] == 0.25
        dong = (tmp_path / duong_dan_decision_log("dry_run")).read_text(encoding="utf-8").splitlines()
        assert [json.loads(d)["loai"] for d in dong] == ["VAO_RA_LENH"]

    def test_dem_su_kien_chi_dem_doi_sl_cung_runmode(self, monkeypatch, tmp_path) -> None:
        s = _chien_luoc(monkeypatch)
        monkeypatch.chdir(tmp_path)
        so = tmp_path / duong_dan_decision_log("dry_run")
        so.parent.mkdir(parents=True)
        so.write_text(
            "\n".join(json.dumps(x) for x in (
                {"loai": "DOI_SL", "nguon": "dry_run"},
                {"loai": "DOI_SL", "nguon": "live"},
                {"loai": "VAO_RA_LENH", "nguon": "dry_run"},
                {"loai": "DOI_SL", "nguon": "dry_run"},
            )) + "\n",
            encoding="utf-8",
        )
        assert s._so_su_kien_doi_sl() == 2
