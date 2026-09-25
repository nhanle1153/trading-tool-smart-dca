"""TD-0412 (`DR-D10-02` §6, §6.3) — D10 đo cho IQ-0003: máy canh rổ, vốn D10, bộ khởi chạy `RoFundingD10`, lớp con chiến lược.

Mọi metadata sàn, trade, ví là GIẢ; không gọi mạng thật."""

from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from tool_d.ops.live_d10 import (
    CHIEN_LUOC_HOP_LE,
    KHOA_CAU_HINH_D10,
    TEN_CHIEN_LUOC,
    TEN_CHIEN_LUOC_RO,
    LiveD10Error,
    dung_cau_hinh_live_d10,
)
from tool_d.ops.ngan_sach_d10_ro import (
    DU_LAN_CAN_RO,
    DU_LENH_KHOP,
    NganSachD10RoError,
    TrangThaiD10Ro,
    han_chot,
    von_ro_d10,
    xet_vao_lenh,
)
from tool_d.ro_funding import RoFundingError

REPO_ROOT = Path(__file__).resolve().parents[2]
UTC = timezone.utc
T0 = datetime(2026, 10, 1, 0, tzinfo=UTC)
MA = [f"C{i}" for i in range(10)]
RO10 = tuple(f"{m}/USDT:USDT" for m in MA)
EXCHANGE_INFO = {"symbols": [
    {"symbol": f"{m}USDT", "filters": [{"filterType": "MIN_NOTIONAL", "notional": "5"},
                                        {"filterType": "LOT_SIZE", "stepSize": "1", "minQty": "1"}]}
    for m in MA
]}
GIA = [{"symbol": f"{m}USDT", "price": str(0.5 + i)} for i, m in enumerate(MA)]


def _tt(**ghi_de) -> TrangThaiD10Ro:
    goc = dict(so_lenh_khop=0, so_lan_can_ro=0, moc_vi_the_dau=None, ky_quy_dang_mo=0.0, so_du=250.0)
    goc.update(ghi_de)
    return TrangThaiD10Ro(**goc)


class TestMayCanhRo:
    def test_trang_thai_dau_duoc_vao(self) -> None:
        assert xet_vao_lenh(_tt(), ky_quy_lenh=16.0, now=T0) == ()

    def test_du_ca_hai_nguong_thi_dung_mo_moi(self) -> None:
        tt = _tt(so_lenh_khop=DU_LENH_KHOP, so_lan_can_ro=DU_LAN_CAN_RO, moc_vi_the_dau=T0)
        assert any("đủ mẫu" in x for x in xet_vao_lenh(tt, ky_quy_lenh=1.0, now=T0))

    @pytest.mark.parametrize(("lenh", "lan"), [(DU_LENH_KHOP, DU_LAN_CAN_RO - 1), (DU_LENH_KHOP - 1, DU_LAN_CAN_RO)])
    def test_thieu_mot_trong_hai_thi_chua_du(self, lenh, lan) -> None:
        tt = _tt(so_lenh_khop=lenh, so_lan_can_ro=lan, moc_vi_the_dau=T0)
        assert xet_vao_lenh(tt, ky_quy_lenh=1.0, now=T0) == ()

    def test_chua_du_mau_thi_gia_han_dung_mot_lan(self) -> None:
        assert han_chot(_tt(moc_vi_the_dau=T0)) == T0 + timedelta(days=28)
        assert any("hết cửa sổ" in x for x in xet_vao_lenh(_tt(moc_vi_the_dau=T0), ky_quy_lenh=1.0, now=T0 + timedelta(days=28)))

    def test_du_mau_thi_khong_gia_han(self) -> None:
        tt = _tt(so_lenh_khop=DU_LENH_KHOP, so_lan_can_ro=DU_LAN_CAN_RO, moc_vi_the_dau=T0)
        assert han_chot(tt) == T0 + timedelta(days=14)

    def test_tran_ky_quy_50_phan_tram(self) -> None:
        assert xet_vao_lenh(_tt(ky_quy_dang_mo=100.0, so_du=250.0), ky_quy_lenh=25.0, now=T0) == ()
        assert any("50%" in x for x in xet_vao_lenh(_tt(ky_quy_dang_mo=100.0, so_du=250.0), ky_quy_lenh=25.01, now=T0))

    @pytest.mark.parametrize("so_du", [None, math.nan, 0.0, math.inf])
    def test_so_du_khong_doc_duoc_thi_tu_choi(self, so_du) -> None:
        assert any("số dư không đọc được" in x for x in xet_vao_lenh(_tt(so_du=so_du), ky_quy_lenh=1.0, now=T0))


class TestVonD10:
    def test_ro_10_cap_la_6_lan_san_lon_nhat_nhan_le(self) -> None:
        """k = max(3, ⌊0,2 × 10⌋) = 3 ⇒ 2k = 6 (DR-D10-02 §6.3 Q7)."""
        von = von_ro_d10([10.0, 30.0, 12.0], so_cap_ro=10, ty_le_k=0.2, k_toi_thieu=3, he_so_le_san=1.1, don_bay=1.0)
        assert von == pytest.approx(6 * 30.0 * 1.1)

    def test_moi_vi_the_it_nhat_bang_san_nhan_le(self) -> None:
        von = von_ro_d10([7.0, 19.0], so_cap_ro=10, ty_le_k=0.2, k_toi_thieu=3, he_so_le_san=1.1, don_bay=1.0)
        assert von / 6 >= 19.0 * 1.1 - 1e-9

    def test_ro_qua_nho_hai_chan_chong_nhau_thi_tu_choi(self) -> None:
        with pytest.raises(NganSachD10RoError, match="chồng"):
            von_ro_d10([5.0, 5.0], so_cap_ro=5, ty_le_k=0.2, k_toi_thieu=3, he_so_le_san=1.1, don_bay=1.0)

    @pytest.mark.parametrize("san", [[], [5.0, 0.0], [5.0, math.nan]])
    def test_san_hong_thi_tu_choi(self, san) -> None:
        with pytest.raises(NganSachD10RoError):
            von_ro_d10(san, so_cap_ro=10, ty_le_k=0.2, k_toi_thieu=3, he_so_le_san=1.1, don_bay=1.0)


class TestBoKhoiChayRo:
    def test_mac_dinh_la_rofunding_d10(self) -> None:
        assert TEN_CHIEN_LUOC == TEN_CHIEN_LUOC_RO == "RoFundingD10" and "CtrlD10" in CHIEN_LUOC_HOP_LE

    def test_ap_file_phu_lenh_thi_truong_va_ghi_von(self, tmp_path) -> None:
        kq = dung_cau_hinh_live_d10(ro=RO10, exchange_info=EXCHANGE_INFO, gia=GIA, repo_dir=REPO_ROOT, thu_muc_ra=tmp_path)
        phu = json.loads(kq.duong_dan.read_text(encoding="utf-8"))
        assert phu["strategy"] == "RoFundingD10" and phu["dry_run"] is False
        assert phu["order_types"]["entry"] == "market" and phu["order_types"]["exit"] == "market"
        assert phu["order_types"]["stoploss_on_exchange"] is True  # SL thảm hoạ sống trên sàn (DR-D10-02 §6.1)
        assert phu["stoploss"] < 0 and phu["stoploss"] > -0.99  # stop thảm hoạ từ file phủ, không phải lưới −0,99
        von = phu[KHOA_CAU_HINH_D10]["von_ro_usdt"]
        assert von == kq.von_ro_usdt and von > 0
        assert phu["max_open_trades"] >= 6  # rổ mở 2k vị thế CÙNG LÚC — không bị chốt tuần tự của CTRL cắt

    def test_von_bang_cong_thuc_tren_san_that_cua_ro(self, tmp_path) -> None:
        from tool_d.notional import build_symbol_filters, san_tool_d

        kq = dung_cau_hinh_live_d10(ro=RO10, exchange_info=EXCHANGE_INFO, gia=GIA, repo_dir=REPO_ROOT, thu_muc_ra=tmp_path)
        stop = json.loads(kq.duong_dan.read_text(encoding="utf-8"))["stoploss"]
        san = [san_tool_d(f, strategy_stoploss=stop) for f in build_symbol_filters(EXCHANGE_INFO, GIA, {f"{m}USDT" for m in MA})]
        assert kq.von_ro_usdt == pytest.approx(6 * max(san) * 1.1)

    def test_thieu_metadata_san_thi_tu_choi(self, tmp_path) -> None:
        with pytest.raises(LiveD10Error, match="metadata sàn"):
            dung_cau_hinh_live_d10(ro=RO10, repo_dir=REPO_ROOT, thu_muc_ra=tmp_path)

    def test_chien_luoc_la_thi_tu_choi(self, tmp_path) -> None:
        with pytest.raises(LiveD10Error, match="không hợp lệ"):
            dung_cau_hinh_live_d10(ro=RO10, chien_luoc="ZoneAbsorption", repo_dir=REPO_ROOT, thu_muc_ra=tmp_path)


def _module():
    duong = str(REPO_ROOT / "user_data/strategies")
    if duong not in sys.path:
        sys.path.insert(0, duong)
    import RoFundingD10  # noqa: PLC0415

    return RoFundingD10


def _lenh(side, filled):
    return SimpleNamespace(ft_order_side=side, status="closed", order_filled_date=filled)


def _chien_luoc(monkeypatch, *, von=200.0, trades=(), so_du=250.0):
    m = _module()
    cfg = {"stake_currency": "USDT", "exchange": {"name": "binance"}}
    if von is not None:
        cfg[KHOA_CAU_HINH_D10] = {"von_ro_usdt": von}
    s = m.RoFundingD10(config=cfg)
    s.wallets = SimpleNamespace(get_total=lambda _c: so_du)
    monkeypatch.setattr(m.Trade, "get_trades_proxy", staticmethod(lambda **_: list(trades)))
    return s


class TestLopCon:
    def test_von_d10_thay_von_san_xuat(self, monkeypatch) -> None:
        assert _chien_luoc(monkeypatch, von=198.0)._von == 198.0

    @pytest.mark.parametrize("von", [None, 0, -5, math.nan, True, "200"])
    def test_thieu_hay_hong_von_d10_thi_tu_choi_khong_roi_ve_von_san_xuat(self, monkeypatch, von) -> None:
        m = _module()
        cfg = {"stake_currency": "USDT", "exchange": {"name": "binance"}}
        if von is not None:
            cfg[KHOA_CAU_HINH_D10] = {"von_ro_usdt": von}
        with pytest.raises(RoFundingError, match="vốn D10"):
            m.RoFundingD10(config=cfg)

    def test_luc_can_ro_trang_thai_dau_duoc_vao(self, monkeypatch) -> None:
        s = _chien_luoc(monkeypatch)
        assert s.confirm_trade_entry("C0/USDT:USDT", "market", 10.0, 1.0, "GTC", T0, "RO", "long") is True

    def test_ngoai_gio_can_ro_van_bi_chot_goc_chan(self, monkeypatch) -> None:
        s = _chien_luoc(monkeypatch)
        assert s.confirm_trade_entry("C0/USDT:USDT", "market", 10.0, 1.0, "GTC", T0 + timedelta(hours=5), "RO", "long") is False

    def test_du_mau_thi_dung_mo_moi(self, monkeypatch) -> None:
        """30 lệnh khớp trên 7 lần cân rổ (ngày giờ SQLite không múi giờ) ⇒ dừng mở vị thế mới."""
        trades = []
        for ngay in range(7):
            moc = (T0 - timedelta(days=7 - ngay)).replace(tzinfo=None)
            orders = [_lenh("buy", moc) for _ in range(3)] + [_lenh("sell", moc + timedelta(days=1)) for _ in range(2)]
            trades.append(SimpleNamespace(orders=orders, entry_side="buy", open_date=moc, stake_amount=5.0, is_open=False))
        s = _chien_luoc(monkeypatch, trades=trades)
        assert s._trang_thai_d10().so_lenh_khop == 35 and s._trang_thai_d10().so_lan_can_ro == 7
        assert s.confirm_trade_entry("C0/USDT:USDT", "market", 10.0, 1.0, "GTC", T0, "RO", "long") is False

    def test_cac_lenh_cung_mot_lan_can_ro_dem_la_mot(self, monkeypatch) -> None:
        """Lệnh thị trường của một lần cân rổ khớp cách nhau vài giây — vẫn là MỘT lần cân rổ."""
        g = T0.replace(tzinfo=None)
        orders = [_lenh("buy", g + timedelta(seconds=1)), _lenh("buy", g + timedelta(seconds=40))]
        t = SimpleNamespace(orders=orders, entry_side="buy", open_date=g, stake_amount=5.0, is_open=True)
        assert _chien_luoc(monkeypatch, trades=[t])._trang_thai_d10().so_lan_can_ro == 1

    def test_lenh_stop_khong_tinh_la_lenh_do(self, monkeypatch) -> None:
        orders = [_lenh("buy", T0.replace(tzinfo=None)), SimpleNamespace(ft_order_side="stoploss", status="closed",
                                                                         order_filled_date=T0.replace(tzinfo=None))]
        t = SimpleNamespace(orders=orders, entry_side="buy", open_date=T0, stake_amount=5.0, is_open=True)
        assert _chien_luoc(monkeypatch, trades=[t])._trang_thai_d10().so_lenh_khop == 1

    def test_vuot_tran_ky_quy_thi_tu_choi(self, monkeypatch) -> None:
        mo = SimpleNamespace(orders=[], entry_side="buy", open_date=T0, stake_amount=120.0, is_open=True)
        s = _chien_luoc(monkeypatch, trades=[mo], so_du=250.0)
        assert s.confirm_trade_entry("C0/USDT:USDT", "market", 20.0, 1.0, "GTC", T0, "RO", "long") is False
