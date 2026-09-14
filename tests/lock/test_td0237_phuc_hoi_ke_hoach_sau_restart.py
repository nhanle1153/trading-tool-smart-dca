"""🔒 TD-0237 (MT-41) — kế hoạch cỡ lệnh phải sống sót qua restart.

`custom_stake_amount()` cất kế hoạch tạm vào `self._cho[pair]` (RAM của
tiến trình). `order_filled()` mới tiêu thụ nó, và giữa hai mốc là một lệnh
post-only chờ khớp tới 180 phút (`unfilledtimeout.entry`). Một lần restart
trong cửa sổ đó làm mất `self._cho`; trước bản vá này, `order_filled()`
`raise SizingError` — và `strategy_safe_wrapper` của Freqtrade NUỐT
exception của callback (MT-16 vii, đã đo), nên vị thế mở ra không có
`co_lenh`/`ke_hoach`, rồi mọi callback khác cũng raise theo, và Freqtrade
rơi về lưới cuối `stoploss = −0,99`.

Bộ test này gọi ĐÚNG `ZoneAbsorption.order_filled()` — không dựng lại
logic phục hồi ở đây (dựng lại là tái lập đúng bug TD-0192/TD-0168: tự
viết công thức đúng rồi tự kiểm công thức đó, không kiểm được đường dây
nối). Ba việc KHÔNG thuộc phạm vi TD-0237 (đọc chỉ báo 1H, quét zone đỉnh,
tính lại chốt lời) cần `self.dp` thật — cô lập bằng monkeypatch, đúng
khuôn TD-0192 gọi thẳng `_tinh_zone_4h` mà không dựng lại nó.

Phần TOÁN THUẦN (công thức suy ngược `n_full`) đã khoá ở
`tests/unit/test_sizing.py::TestPhucHoiKeHoachSauRestart`.
"""

from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
NGUON_CHIEN_LUOC = REPO_ROOT / "user_data/strategies/ZoneAbsorption.py"


def _import_chien_luoc():
    if str(REPO_ROOT / "user_data/strategies") not in sys.path:
        sys.path.insert(0, str(REPO_ROOT / "user_data/strategies"))
    spec = importlib.util.spec_from_file_location("ZoneAbsorption", NGUON_CHIEN_LUOC)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class _LenhGia:
    """Đủ thuộc tính `order_filled()` đọc từ `order` — không phải Order
    thật của Freqtrade."""

    def __init__(self, ft_order_side: str = "buy") -> None:
        self.ft_order_side = ft_order_side


class _ViTheGia:
    """Đủ thuộc tính `order_filled()` đọc/ghi trên `trade` — KHÔNG phải
    Trade thật (DB Freqtrade), chỉ mang dữ liệu + ghi lại `set_custom_data`
    để đối chiếu. `enter_tag`/`stake_amount` là hai thứ Freqtrade LƯU BỀN
    VỮNG thật sự (khác `self._cho`, sống trong RAM) — đây chính là hai
    nguồn TD-0237 dùng để suy ngược kế hoạch."""

    def __init__(self, *, pair: str, enter_tag: str | None, stake_amount: float, id_: int = 1) -> None:
        self.pair = pair
        self.enter_tag = enter_tag
        self.entry_side = "buy"
        self.stake_amount = stake_amount
        self.id = id_
        self.nr_of_successful_entries = 1
        self.open_rate = 100.0
        self._custom_data: dict[str, object] = {}

    def set_custom_data(self, key: str, value: object) -> None:
        self._custom_data[key] = value

    def get_custom_data(self, key: str, default=None):
        return self._custom_data.get(key, default)


def _dung_strategy(ZA):
    s = ZA.ZoneAbsorption(config={"stake_currency": "USDT", "exchange": {"name": "binance"}})
    s._arm = "Z0"
    # order_filled() còn gọi BỐN việc KHÔNG thuộc phạm vi TD-0237 (equity/
    # zone đỉnh/chốt lời/Decision Log) và cần self.dp thật — cô lập, không
    # dựng lại. TD-0239 (_ghi_vao_lenh, đọc self.dp.runmode.value) thêm vào
    # SAU — cùng lý do ba hàm kia đã có: `_LenhGia`/`_ViTheGia` ở trên là
    # mock TỐI THIỂU cho ĐÚNG kịch bản MT-41, không phải Order/Trade/dp
    # thật của Freqtrade.
    s._hang_hien_tai = lambda pair: None
    s._zone_dinh_tren = lambda pair, current_time, p_avg: []
    s._cap_nhat_chot_loi = lambda trade, current_time: None
    s._ghi_vao_lenh = lambda pair, trade, order: None
    return s


def _tag(ZA, *, zl=90.0, zh=100.0, p1=97.0, p2=95.0, p3=90.0, sl=88.0) -> str:
    kh = ZA.KeHoachTranche(
        zone_low=zl, zone_high=zh, p1=p1, p2=p2, p3=p3, sl=sl,
        r_eff_plan=0.0, atr_1h_tai_tranche1=0.0,
    )
    return ZA._ma_hoa(kh, zss_value=0.6, trend_4h="UP", swing_ts_ms=1_700_000_000_000)


PAIR = "BTC/USDT:USDT"


class TestKhongRestartHanhViKhongDoi:
    """Đối chứng — đường KHÔNG restart (kịch bản bình thường, `self._cho`
    còn nguyên) phải giữ ĐÚNG hành vi cũ, không bị bản vá đổi."""

    def test_co_cho_thi_dung_cho_khong_di_phuc_hoi(self) -> None:
        ZA = _import_chien_luoc()
        s = _dung_strategy(ZA)
        tag = _tag(ZA)
        s._cho[PAIR] = {
            "co_lenh": {
                "arm": "Z0", "n_full_usdt": 300.0, "w_tranche": [0.25, 0.25, 0.5],
                "l_exchange": 3.0, "rho_pct": 0.375, "rho_eff_pct": 0.375,
                "mult": {"regime": 1.0, "zss": 1.0, "corr": 1.0, "dd": 1.0, "edge": 1.0, "deploy": 1.0},
                "r_eff": 0.02, "planned_risk_usdt": 6.0, "planned_margin_usdt": 100.0,
            },
            "ke_hoach": {
                "zone_low": 90.0, "zone_high": 100.0, "p1": 97.0, "p2": 95.0, "p3": 90.0,
                "sl": 88.0, "r_eff_plan": 0.02, "atr_1h_tai_tranche1": 0.0,
            },
            "tag": {"zl": 90.0, "zh": 100.0, "p1": 97.0, "p2": 95.0, "p3": 90.0, "sl": 88.0,
                    "zs": 0.6, "t4": "UP", "sw": 1_700_000_000_000},
        }
        trade = _ViTheGia(pair=PAIR, enter_tag=tag, stake_amount=25.0)  # KHÁC 25 so với kế hoạch cũ
        s.order_filled(PAIR, trade, _LenhGia(), current_time=None)
        assert PAIR not in s._cho, "kế hoạch tiêu thụ xong phải bị xoá khỏi RAM"
        # Giá trị GHI phải đúng bản trong `_cho` (300.0), KHÔNG suy ngược
        # từ `stake_amount` giả (25.0) — vì đường KHÔNG restart không đi
        # qua `_phuc_hoi_ke_hoach_sau_restart` chút nào.
        assert trade.get_custom_data("co_lenh")["n_full_usdt"] == pytest.approx(300.0)


class TestKichBanRestartTASKS0237:
    """Kịch bản literal của Tiêu chí XONG (`TASKS.md` TD-0237): có kế
    hoạch trong `_cho` ⇒ xoá sạch bộ nhớ tiến trình ⇒ `order_filled` vẫn
    lắp được kế hoạch."""

    def test_xoa_sach_cho_thi_order_filled_van_lap_duoc_ke_hoach(self) -> None:
        ZA = _import_chien_luoc()
        s = _dung_strategy(ZA)
        tag = _tag(ZA)
        stake1_that = 42.0
        trade = _ViTheGia(pair=PAIR, enter_tag=tag, stake_amount=stake1_that)

        # 🔴 Đúng kịch bản MT-41: `self._cho` KHÔNG BAO GIỜ được điền ở
        # tiến trình NÀY — mô phỏng "restart giữa lúc đặt lệnh và lúc
        # tranche 1 khớp": RAM sạch (tiến trình mới), nhưng `trade`/`order`
        # đã tồn tại bền vững ở Freqtrade (DB), y hệt `trade`/`order` giả
        # lập ở trên.
        assert PAIR not in s._cho

        s.order_filled(PAIR, trade, _LenhGia(), current_time=None)

        co_lenh = trade.get_custom_data("co_lenh")
        assert co_lenh is not None, "order_filled không lắp được kế hoạch sau restart"
        assert trade.get_custom_data("ke_hoach") is not None
        assert trade.get_custom_data("tag") is not None

        # n_full/planned_risk/planned_margin — phần THẬT SỰ được risk
        # management hạ lưu đọc (adjust_trade_position, kết nạp danh mục)
        # — phải CHÍNH XÁC theo công thức suy ngược (khoá toán ở
        # test_sizing.py; ở đây chỉ đối chiếu qua chính đường sản xuất).
        l_exchange = float(co_lenh["l_exchange"])
        w0 = float(co_lenh["w_tranche"][0])
        n_full_ky_vong = stake1_that * l_exchange / w0
        assert co_lenh["n_full_usdt"] == pytest.approx(n_full_ky_vong, rel=1e-9)
        assert co_lenh["planned_risk_usdt"] == pytest.approx(
            n_full_ky_vong * co_lenh["r_eff"], rel=1e-9
        )

        # mult/rho_eff_pct KHÔNG suy ngược được — phải là NaN (N6: không
        # bịa số, không sentinel), KHÔNG 0.0.
        assert math.isnan(co_lenh["rho_eff_pct"])
        assert all(math.isnan(v) for v in co_lenh["mult"].values())

    def test_ke_hoach_thieu_ca_cho_lan_enter_tag_thi_raise_khong_nuot_im_lang(self) -> None:
        """'Thiếu là lỗi lắp ráp, không phải chưa có' (Tiêu chí XONG,
        TASKS.md TD-0237) — KHÔNG được nới `SizingError` thành cảnh báo."""
        ZA = _import_chien_luoc()
        s = _dung_strategy(ZA)
        trade = _ViTheGia(pair=PAIR, enter_tag=None, stake_amount=42.0)
        with pytest.raises(ZA.SizingError):
            s.order_filled(PAIR, trade, _LenhGia(), current_time=None)

    def test_stake_amount_0_khong_bia_ke_hoach(self) -> None:
        """Order đã fill mà `stake_amount` đọc về 0/âm là dữ liệu hỏng —
        raise, không suy ngược ra một kế hoạch vô nghĩa."""
        ZA = _import_chien_luoc()
        s = _dung_strategy(ZA)
        trade = _ViTheGia(pair=PAIR, enter_tag=_tag(ZA), stake_amount=0.0)
        with pytest.raises(ZA.SizingError):
            s.order_filled(PAIR, trade, _LenhGia(), current_time=None)
