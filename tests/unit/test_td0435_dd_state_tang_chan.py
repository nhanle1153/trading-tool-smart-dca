"""TD-0435 (`DR-TANG-CHAN-01` §4 điều 3) — Supervisor công bố `dd_state.json`, chiến lược đọc để áp bậc 5% (nửa cỡ lệnh).

Bốn lớp: tệp công bố (`ghi_dd_state`/`doc_dd_state`) · hàm đọc dùng chung (`tang_chan.mult_dd_tu_supervisor`, fail-closed) ·
daemon công bố mức sụt vừa đo · hai chiến lược lên tiền qua đường sản xuất thật (`ZoneAbsorption._mult_dd`,
`RoFundingD10.custom_stake_amount`/`confirm_trade_entry`) — live/dry-run đọc Supervisor, backtest giữ công thức cũ.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

import tool_d.tang_chan as tang_chan
from tool_d.ops.heartbeat_watchdog import NGUONG_HEARTBEAT_CU_S
from tool_d.ops.risk_supervisor_daemon import chay_mot_vong_giam_sat
from tool_d.ro_funding import RoFundingError
from tool_d.risk_supervisor import (
    ABORT,
    BINH_THUONG,
    HALT,
    NUA_CO,
    RiskSupervisorError,
    TrangThaiBenVung,
    TrangThaiBreaker,
    doc_dd_state,
    doc_trang_thai,
    ghi_dd_state,
    luu_trang_thai,
)
from tool_d.tang_chan import duong_dan_dd_state, mult_dd_tu_supervisor

REPO_ROOT = Path(__file__).resolve().parents[2]
T0 = datetime(2026, 9, 27, 12, 0, 0, tzinfo=timezone.utc)
SOFT, HALT_PCT = 5.0, 8.0


def _cong_bo(goc: Path, runmode: str = "dry_run", *, muc=BINH_THUONG, dd=2.0, co_do=False, luc=T0) -> None:
    ghi_dd_state(duong_dan_dd_state(runmode, goc=goc), muc=muc, dd_pct=dd, co_do=co_do, now=luc)


def _m(goc: Path, runmode: str = "dry_run", now: datetime = T0) -> float:
    return mult_dd_tu_supervisor(runmode, now=now, soft_pct=SOFT, halt_pct=HALT_PCT, goc=goc)


class TestTepCongBo:
    def test_ghi_doc_lai(self, tmp_path) -> None:
        p = tmp_path / "dd_state.json"
        ghi_dd_state(p, muc=NUA_CO, dd_pct=6.5, co_do=False, now=T0)
        st = doc_dd_state(p)
        assert (st.muc, st.dd_pct, st.co_do, st.luc_utc) == (NUA_CO, 6.5, False, T0)
        assert not (tmp_path / "dd_state.json.dang-ghi").exists()

    @pytest.mark.parametrize(
        "noi_dung",
        ["khong json", "{}", json.dumps({"muc": "PAUSE", "dd_pct": 1, "co_do": False, "luc_utc": T0.isoformat()}),
         json.dumps({"muc": HALT, "dd_pct": -1, "co_do": False, "luc_utc": T0.isoformat()}),
         json.dumps({"muc": HALT, "dd_pct": 1, "co_do": "false", "luc_utc": T0.isoformat()}),
         json.dumps({"muc": HALT, "dd_pct": 1, "co_do": False, "luc_utc": "2026-09-27T12:00:00"})],
    )
    def test_sai_hinh_thi_raise(self, tmp_path, noi_dung: str) -> None:
        p = tmp_path / "dd_state.json"
        p.write_text(noi_dung, encoding="utf-8")
        with pytest.raises(RiskSupervisorError):
            doc_dd_state(p)

    def test_thieu_file_thi_raise(self, tmp_path) -> None:
        with pytest.raises(RiskSupervisorError):
            doc_dd_state(tmp_path / "khong_co.json")


class TestHamDocDungChung:
    @pytest.mark.parametrize("dd,he_so", [(0.0, 1.0), (5.0, 1.0), (6.0, 0.5), (8.0, 0.5), (8.5, 0.0)])
    def test_binh_thuong_theo_thang(self, tmp_path, dd: float, he_so: float) -> None:
        _cong_bo(tmp_path, dd=dd)
        assert _m(tmp_path) == he_so

    @pytest.mark.parametrize("muc,he_so", [(HALT, 0.0), (ABORT, 0.0), (NUA_CO, 0.5)])
    def test_theo_muc_supervisor(self, tmp_path, muc: str, he_so: float) -> None:
        _cong_bo(tmp_path, muc=muc, dd=1.0)
        assert _m(tmp_path) == he_so

    def test_NUA_CO_van_nua_co_du_dd_da_nho(self, tmp_path) -> None:
        """§12c.5 BƯỚC 3: nửa cỡ tới khi Supervisor chuyển về BINH_THUONG — chiến lược không tự quyết theo dd."""
        _cong_bo(tmp_path, muc=NUA_CO, dd=1.0)
        assert _m(tmp_path) == 0.5

    def test_co_do_thi_0_du_muc_binh_thuong(self, tmp_path) -> None:
        _cong_bo(tmp_path, muc=BINH_THUONG, dd=0.0, co_do=True)
        assert _m(tmp_path) == 0.0

    def test_thieu_file_thi_0_KHONG_mo_lenh(self, tmp_path) -> None:
        assert _m(tmp_path) == 0.0

    def test_binh_thuong_chua_do_duoc_dd_thi_0(self, tmp_path) -> None:
        _cong_bo(tmp_path, dd=None)
        assert _m(tmp_path) == 0.0

    def test_cu_qua_han_heartbeat_thi_0(self, tmp_path) -> None:
        _cong_bo(tmp_path, luc=T0)
        assert _m(tmp_path, now=T0 + timedelta(seconds=NGUONG_HEARTBEAT_CU_S - 1)) == 1.0
        assert _m(tmp_path, now=T0 + timedelta(seconds=NGUONG_HEARTBEAT_CU_S + 1)) == 0.0

    def test_moc_gio_o_tuong_lai_xa_thi_0(self, tmp_path) -> None:
        _cong_bo(tmp_path, luc=T0 + timedelta(hours=1))
        assert _m(tmp_path) == 0.0

    def test_moi_runmode_mot_file(self, tmp_path) -> None:
        _cong_bo(tmp_path, "live", dd=0.0)
        assert _m(tmp_path, "live") == 1.0 and _m(tmp_path, "dry_run") == 0.0

    def test_backtest_khong_co_supervisor(self, tmp_path) -> None:
        with pytest.raises(ValueError):
            _m(tmp_path, "backtest")


class TestDaemonCongBoMucSut:
    def test_vong_ghi_dd_pct_cuoi_va_KHONG_luu_xuong_dia(self, tmp_path) -> None:
        tt, _ = chay_mot_vong_giam_sat(
            TrangThaiBenVung(breaker=TrangThaiBreaker()), now=T0, doc_account_fn=lambda: {},
            doc_position_fn=lambda: [], doc_force_orders_fn=lambda: [],
            doc_breaker_hien_tai_fn=lambda: TrangThaiBreaker(), tu_thoi_diem_ms=1000,
            dung_bot_fn=lambda: None, tinh_dd_fn=lambda _a: 3.25, tam_ngung_fn=lambda: None,
            ghi_abort_fn=lambda: None, luu_truoc_fn=lambda _t: None,
        )
        assert tt.dd_pct_cuoi == 3.25
        p = tmp_path / "state.json"
        luu_trang_thai(tt, p)
        assert "dd_pct_cuoi" not in json.loads(p.read_text(encoding="utf-8"))
        assert doc_trang_thai(p).dd_pct_cuoi is None, "số cũ sau restart không được đọc lại như số mới (N6)"

    def test_main_cong_bo_moi_vong_nhanh_loi_va_khi_tu_choi_vi_co_do(self) -> None:
        import ast

        cay = ast.parse((REPO_ROOT / "src/tool_d/ops/risk_supervisor_daemon.py").read_text(encoding="utf-8"))
        main = next(n for n in cay.body if isinstance(n, ast.FunctionDef) and n.name == "main")
        goi = [n for n in ast.walk(main) if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "_cong_bo"]
        assert len(goi) >= 3, "công bố: sau mỗi vòng + nhánh lỗi /stop + lúc từ chối khởi động vì cờ đỏ"


def _nap_za():
    duong = str(REPO_ROOT / "user_data/strategies")
    if duong not in sys.path:
        sys.path.insert(0, duong)
    spec = importlib.util.spec_from_file_location("ZoneAbsorption", REPO_ROOT / "user_data/strategies/ZoneAbsorption.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class TestZoneAbsorptionDuongSanXuat:
    @pytest.fixture
    def za(self):
        m = _nap_za()
        return m.ZoneAbsorption(config={"stake_currency": "USDT", "exchange": {"name": "binance"}})

    @pytest.mark.parametrize("runmode", ["dry_run", "live"])
    def test_live_dry_run_doc_supervisor(self, za, tmp_path, monkeypatch, runmode: str) -> None:
        monkeypatch.setattr(tang_chan, "THU_MUC_SUPERVISOR", tmp_path)
        za.dp = SimpleNamespace(runmode=SimpleNamespace(value=runmode))
        assert za._mult_dd(T0) == 0.0, "chưa có Supervisor ⇒ không mở lệnh"
        _cong_bo(tmp_path, runmode, dd=6.0)
        assert za._mult_dd(T0) == 0.5
        _cong_bo(tmp_path, runmode, muc=HALT, dd=9.0)
        assert za._mult_dd(T0) == 0.0

    def test_backtest_giu_cong_thuc_cu_khong_doc_supervisor(self, za, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr(tang_chan, "THU_MUC_SUPERVISOR", tmp_path)
        _cong_bo(tmp_path, "dry_run", muc=HALT, dd=50.0)
        za.dp = SimpleNamespace(runmode=SimpleNamespace(value="backtest"))
        za.wallets = SimpleNamespace(get_total=lambda _c: 1000.0)
        assert za._mult_dd(T0) == 1.0


def _nap_d10():
    duong = str(REPO_ROOT / "user_data/strategies")
    if duong not in sys.path:
        sys.path.insert(0, duong)
    import RoFundingD10  # noqa: PLC0415

    return RoFundingD10


class TestRoFundingD10DuongSanXuat:
    @pytest.fixture
    def d10(self, monkeypatch, tmp_path):
        m = _nap_d10()
        monkeypatch.setattr(tang_chan, "THU_MUC_SUPERVISOR", tmp_path)
        s = m.RoFundingD10(config={"stake_currency": "USDT", "exchange": {"name": "binance"},
                                   m.KHOA_CAU_HINH_D10: {"von_ro_usdt": 200.0}})
        s.dp = SimpleNamespace(runmode=SimpleNamespace(value="live"))
        monkeypatch.setattr(m.RoFunding, "custom_stake_amount", lambda self, *a, **k: 40.0)
        return s

    def _stake(self, s, min_stake=5.0):
        return s.custom_stake_amount("BTC/USDT:USDT", T0, 100.0, 40.0, min_stake, 1000.0, 2.0, "RO", "long")

    def test_binh_thuong_nguyen_co(self, d10, tmp_path) -> None:
        _cong_bo(tmp_path, "live", dd=1.0)
        assert self._stake(d10) == 40.0

    def test_bac_5_phan_tram_nua_co(self, d10, tmp_path) -> None:
        _cong_bo(tmp_path, "live", dd=6.0)
        assert self._stake(d10) == 20.0

    def test_khong_supervisor_thi_raise_khong_mo_lenh(self, d10) -> None:
        with pytest.raises(RoFundingError, match="hệ số dd = 0"):
            self._stake(d10)

    def test_nua_co_duoi_san_thi_raise_khong_cat_ngam(self, d10, tmp_path) -> None:
        _cong_bo(tmp_path, "live", dd=6.0)
        with pytest.raises(RoFundingError, match="min_stake"):
            self._stake(d10, min_stake=25.0)

    def test_confirm_tu_choi_khi_HALT(self, d10, tmp_path, monkeypatch) -> None:
        _cong_bo(tmp_path, "live", muc=HALT, dd=9.0)
        monkeypatch.setattr(type(d10).__mro__[1], "confirm_trade_entry", lambda self, *a, **k: True)
        assert d10.confirm_trade_entry("BTC/USDT:USDT", "market", 1.0, 100.0, "gtc", T0, "RO", "long") is False
