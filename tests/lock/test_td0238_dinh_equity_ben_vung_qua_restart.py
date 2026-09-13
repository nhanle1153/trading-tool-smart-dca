"""🔒 TD-0238 (MT-40) — Đỉnh equity phải bền vững qua restart.

`_dinh_equity` trước bản vá này chỉ sống trong RAM (`ZoneAbsorption.py`
`__init__`), nên mỗi lần tiến trình restart, `_dd_pct()` coi equity hiện
tại là đỉnh ⇒ `dd_pct` về 0% ⇒ `mult_dd()` (`sizing.py`) không bao giờ
chạm ngưỡng `soft`/`halt` — một trong BA tầng Cấp C (`DR-D0PRE-04`,
§12b.2) chặn vòng lặp thua lỗ tự vô hiệu hoá.

Bộ test này gọi ĐÚNG `ZoneAbsorption.bot_start()`/`_dd_pct()` — không
dựng lại logic phục hồi ở đây (cùng lý do TD-0237: tự viết công thức
đúng rồi tự kiểm công thức đó không kiểm được đường dây nối). Phần TOÁN
THUẦN (`dinh_equity_moi`, ghi/đọc nguyên tử) đã khoá ở
`tests/unit/test_equity_peak.py`.

🔴 Đã đọc mã nguồn Freqtrade thật (`/freqtrade/freqtrade/strategy/interface.py`
`ft_bot_start()`/`strategy_safe_wrapper`, N7/rule 6, cùng khuôn TD-0028)
trước khi chốt thiết kế: `ft_bot_start()` gọi
`strategy_safe_wrapper(self.bot_start)()` KHÔNG truyền `default_retval`/
`supress_error` — khác các callback có giá trị mặc định an toàn (vd
`confirm_trade_entry`), nhánh này RE-RAISE thành `StrategyError`, KHÔNG
nuốt im lặng như MT-16(vii)/MT-41. Một `bot_start()` raise vì file hỏng/
lệch `stake_currency` do đó làm bot KHÔNG khởi động được — đúng hướng an
toàn (fail-closed), không phải một chốt vô hình.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from tool_d.sizing import HeSoMult, mult_dd

REPO_ROOT = Path(__file__).resolve().parents[2]
NGUON_CHIEN_LUOC = REPO_ROOT / "user_data/strategies/ZoneAbsorption.py"


def _import_chien_luoc():
    if str(REPO_ROOT / "user_data/strategies") not in sys.path:
        sys.path.insert(0, str(REPO_ROOT / "user_data/strategies"))
    spec = importlib.util.spec_from_file_location("ZoneAbsorption", NGUON_CHIEN_LUOC)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class _ViGia:
    """Đủ để `_dd_pct()` đọc — KHÔNG phải `Wallets` thật của Freqtrade."""

    def __init__(self, tong: float) -> None:
        self._tong = tong

    def get_total(self, currency: str) -> float:
        return self._tong


def _dp_gia(runmode: str) -> SimpleNamespace:
    return SimpleNamespace(runmode=SimpleNamespace(value=runmode))


def _dung_strategy(ZA, *, duong_dan: Path, runmode: str = "dry_run", stake_currency: str = "USDT"):
    s = ZA.ZoneAbsorption(config={"stake_currency": stake_currency, "exchange": {"name": "binance"}})
    s._duong_dan_dinh_equity = duong_dan
    s.dp = _dp_gia(runmode)
    s.bot_start()
    return s


class TestKichBanRestartTASKS0238:
    """Tiêu chí XONG literal của `TASKS.md` TD-0238: dựng chuỗi số dư có
    đỉnh rồi sụt quá `halt`, khởi động lại giữa chừng ⇒ vẫn HALT."""

    def test_dinh_roi_sut_qua_halt_khoi_dong_lai_giua_chung_van_HALT(self, tmp_path) -> None:
        ZA = _import_chien_luoc()
        duong_dan = tmp_path / "equity_peak_state.json"

        s1 = _dung_strategy(ZA, duong_dan=duong_dan)
        s1.wallets = _ViGia(1000.0)
        s1._dd_pct()  # đỉnh = 1000
        s1.wallets = _ViGia(1100.0)
        s1._dd_pct()  # đỉnh mới = 1100 — ghi đĩa (runmode=dry_run)

        # "Restart" = dựng INSTANCE MỚI trỏ cùng file — không kế thừa RAM
        # của s1 theo bất kỳ cách nào (đối tượng khác hẳn).
        s2 = _dung_strategy(ZA, duong_dan=duong_dan)
        assert s2._dinh_equity == pytest.approx(1100.0), (
            "đỉnh phải nạp lại từ nguồn bền vững lúc bot_start(), không phải RAM"
        )

        s2.wallets = _ViGia(1000.0)  # tụt ~9,09% từ đỉnh 1100 — vượt halt 8%
        dd = s2._dd_pct()
        assert mult_dd(dd_pct=dd, soft_pct=5.0, halt_pct=8.0) == 0.0
        mult = HeSoMult(
            regime=1.0, zss=1.0, corr=1.0,
            dd=mult_dd(dd_pct=dd, soft_pct=5.0, halt_pct=8.0),
            edge=1.0, deploy=1.0,
        )
        assert mult.la_halt is True

    def test_KHONG_restart_cung_so_cho_ket_qua_HALT_nhu_nhau(self, tmp_path) -> None:
        """Đối chứng — không restart, cùng chuỗi số, phải cho cùng kết
        quả HALT (bản vá không đổi công thức cũ, chỉ đổi NGUỒN của đỉnh)."""
        ZA = _import_chien_luoc()
        duong_dan = tmp_path / "equity_peak_state.json"
        s = _dung_strategy(ZA, duong_dan=duong_dan)
        s.wallets = _ViGia(1000.0)
        s._dd_pct()
        s.wallets = _ViGia(1100.0)
        s._dd_pct()
        s.wallets = _ViGia(1000.0)
        dd = s._dd_pct()
        assert mult_dd(dd_pct=dd, soft_pct=5.0, halt_pct=8.0) == 0.0

    def test_runmode_backtest_khong_tao_file_tren_dia(self, tmp_path) -> None:
        """Backtest/hyperopt/plot KHÔNG được rò trạng thái giữa các lượt
        chạy — mỗi lượt backtest phải độc lập, không ảnh hưởng số đã đo."""
        ZA = _import_chien_luoc()
        duong_dan = tmp_path / "equity_peak_state.json"
        s = _dung_strategy(ZA, duong_dan=duong_dan, runmode="backtest")
        for tong in (1000.0, 1100.0, 1200.0, 900.0):
            s.wallets = _ViGia(tong)
            s._dd_pct()
        assert not duong_dan.exists()
        # Vẫn tính đúng dd trong RAM — chỉ không bền vững hoá.
        assert s._dinh_equity == pytest.approx(1200.0)

    def test_runmode_dry_run_ghi_file_moi_lan_co_dinh_moi(self, tmp_path) -> None:
        ZA = _import_chien_luoc()
        duong_dan = tmp_path / "equity_peak_state.json"
        s = _dung_strategy(ZA, duong_dan=duong_dan, runmode="dry_run")
        s.wallets = _ViGia(1000.0)
        s._dd_pct()
        assert duong_dan.exists()
        noi_dung_1 = duong_dan.read_text(encoding="utf-8")
        s.wallets = _ViGia(1100.0)
        s._dd_pct()
        noi_dung_2 = duong_dan.read_text(encoding="utf-8")
        assert noi_dung_1 != noi_dung_2

    def test_don_vi_stake_currency_doi_giua_hai_lan_chay_thi_raise(self, tmp_path) -> None:
        ZA = _import_chien_luoc()
        duong_dan = tmp_path / "equity_peak_state.json"
        s1 = _dung_strategy(ZA, duong_dan=duong_dan, stake_currency="USDT")
        s1.wallets = _ViGia(1000.0)
        s1._dd_pct()

        with pytest.raises(ZA.DinhEquityError):
            _dung_strategy(ZA, duong_dan=duong_dan, stake_currency="BUSD")
