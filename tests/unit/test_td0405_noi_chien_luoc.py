"""TD-0405 — tin Telegram lúc KHỚP đã nối vào `ZoneAbsorption.order_filled()` đúng chỗ, đúng nguồn số.

Hai lớp:
1. Đường sản xuất: `_bao_vao_lenh()` THẬT của chiến lược, trade giả tối thiểu mang `custom_data` đúng hình
   `KeHoachTranche`/`KeHoachCoLenh` — SL phải lấy từ kế hoạch, vốn từ `wallets.get_total` (không phải
   `get_total_stake_amount`, hàm đó nhân `tradable_balance_ratio`), gửi qua `dp.send_msg(always_send=True)`.
2. Hành vi `order_filled()`: lời gọi nằm SAU `_ghi_vao_lenh`, lỗi của nó bị chặn tại chỗ — tin nhắn hỏng không được cướp phần thiết yếu
   của lệnh (Freqtrade nuốt exception của callback, TD-0187).
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

from tool_d.sizing import KeHoachCoLenh
from tool_d.trade_plan import KeHoachTranche

REPO_ROOT = Path(__file__).resolve().parents[2]


def _chien_luoc():
    # `import` theo TÊN module, không `spec_from_file_location`: công cụ phá thật (`tests/tools/mutate_in_memory.py`)
    # thay `sys.modules["ZoneAbsorption"]` — nạp lại từ đĩa thì đi vòng qua bản phá, mọi phép phá ra XANH giả
    # (đã đo lần đầu: M1, M2 đều xanh).
    if str(REPO_ROOT / "user_data/strategies") not in sys.path:
        sys.path.insert(0, str(REPO_ROOT / "user_data/strategies"))
    import ZoneAbsorption  # noqa: PLC0415

    return ZoneAbsorption.ZoneAbsorption(config={"stake_currency": "USDT", "exchange": {"name": "binance"}})


class _Vi:
    def get_total(self, cur: str) -> float:
        assert cur == "USDT"
        return 2113.11

    def get_total_stake_amount(self) -> float:  # bẫy: số này đã nhân tradable_balance_ratio
        return 1584.83


def _trade(*, tranche: int = 1, amount: float = 1498.69 / 0.055):
    kh = KeHoachTranche(zone_low=0.052, zone_high=0.054, p1=0.055, p2=0.056, p3=0.057, sl=0.05761,
                        r_eff_plan=0.0475, atr_1h_tai_tranche1=0.0005)
    cl = KeHoachCoLenh(arm="Z3", n_full_usdt=4496.07, w_tranche=(1 / 3, 1 / 3, 1 / 3), l_exchange=5.0,
                       rho_pct=0.375, rho_eff_pct=0.375, mult={}, r_eff=0.0475, planned_risk_usdt=213.4,
                       planned_margin_usdt=899.2)
    du_lieu = {"ke_hoach": kh.to_dict(), "co_lenh": cl.to_dict(), "tag": {}}
    return SimpleNamespace(
        id=10, pair="LAB/USDT:USDT", is_short=True, leverage=5.0, nr_of_successful_entries=tranche,
        stake_amount=299.74 * tranche, amount=amount * tranche, open_rate=0.055,
        get_custom_data=du_lieu.get,
    )


def _gui(trade):
    s = _chien_luoc()
    da_gui = []
    s.dp = SimpleNamespace(send_msg=lambda msg, *, always_send=False: da_gui.append((msg, always_send)))
    s.wallets = _Vi()
    s._bao_vao_lenh(trade)
    return da_gui


def test_gui_dung_mot_tin_dung_so_mau() -> None:
    da_gui = _gui(_trade())
    assert len(da_gui) == 1
    tin, always_send = da_gui[0]
    assert always_send is True  # tin trùng nội dung (hai lệnh giống hệt) vẫn phải đi
    assert tin.splitlines() == [
        "🆕 Lệnh mới #10 LAB/USDT:USDT SHORT 5x",
        "Ký quỹ 299.74 USDT · vị thế 1,498.69 USDT",
        "Cắt lỗ 0.05761 (cách giá vào 4.75%)",
        "Rủi ro nếu chạm cắt lỗ: 71.12 USDT = 3.37% vốn (vốn 2,113.11 USDT, chưa gồm phí)",
    ]


def test_tranche_2_ghi_lan_tren_so_tranche_ke_hoach() -> None:
    tin = _gui(_trade(tranche=2))[0][0]
    assert tin.splitlines()[0] == "➕ Vào thêm lần 2/3 #10 LAB/USDT:USDT SHORT 5x"


def test_order_filled_bao_sau_ghi_so_va_tin_hong_khong_lot_ra(caplog) -> None:
    """Đi qua `order_filled()` THẬT (nhánh tranche 2 — không đụng `self._cho`): thứ tự gọi, và một lỗi bất kỳ của
    tầng gửi tin (ở đây `TypeError`) bị chặn tại chỗ + log ERROR, không lọt lên Freqtrade (nơi nó bị nuốt im lặng
    và, nếu đặt sai chỗ, cướp luôn phần ghi sổ phía sau)."""
    s = _chien_luoc()
    thu_tu = []
    s._cap_nhat_chot_loi = lambda trade, t: thu_tu.append("chot_loi")
    s._ghi_vao_lenh = lambda pair, trade, order: thu_tu.append("ghi_so")

    def _no(trade):
        thu_tu.append("bao")
        raise TypeError("giả lập tầng gửi tin hỏng")

    s._bao_vao_lenh = _no
    trade = SimpleNamespace(entry_side="sell", nr_of_successful_entries=2, pair="LAB/USDT:USDT")
    order = SimpleNamespace(ft_order_side="sell")
    with caplog.at_level("ERROR"):
        s.order_filled("LAB/USDT:USDT", trade, order, current_time=None)  # không được raise
    assert thu_tu == ["chot_loi", "ghi_so", "bao"]
    assert any("TD-0405" in r.getMessage() and r.levelname == "ERROR" for r in caplog.records)
