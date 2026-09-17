"""🔒 TD-0294 — nến xác nhận §3.3b đã ĐÓNG ≤ SL kiểu zone thì KHÔNG phải xác nhận.

Lộ ra khi đo TD-0291: `SizingError('R_eff phải > 0')` bị Freqtrade nuốt. Đo phễu
EXPLORE (0 trial): 20/2.102 xác nhận có `p1 ≤ sl`. `r_eff_plan` dùng `p_avg` ba
tranche nên CHE một phần ⇒ lệnh MỞ dưới SL; xác nhận ma còn chiếm chỗ `trung_nen`.

════ Vì sao cô lập bộ quét ════

Điều kiện CHẠM là đáy nến trong zone, còn C có thể là nến 1–2 nến SAU lần chạm
(`wait_bars`) — dựng một chuỗi giá thật thoả đồng thời (a)/(b)/(c) CHO ĐÚNG ca này
rất dễ thành ca xanh vì lý do khác (PASS rỗng). Bộ quét `quet_xac_nhan_zone` đã có
test khoá riêng (`test_td0193_quet_xac_nhan_zone.py`); ở đây thay nó bằng bản trả C
định sẵn để canh ĐÚNG phép kiểm sau-quét trong `_xac_nhan_3_3b` của chiến lược THẬT.

Dữ liệu: giá 100, ATR 4H = 5, `buf_sl_atr` thật (0,4) ⇒ `sl_zone = zl − 2`.
Zone A `[98, 99]` ⇒ SL 96 · Zone B `[90, 91]` ⇒ SL 88. Nến 4H không đóng dưới SL
nào ⇒ `den` không bị cắt ⇒ chỉ phép kiểm TD-0294 quyết.
"""

from __future__ import annotations

import importlib.util
import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from tool_d.entry_confirmation import KetQuaQuetXacNhanZone
from tool_d.trade_plan import sl_kieu_zone, tinh_ke_hoach

REPO_ROOT = Path(__file__).resolve().parents[2]
NGUON = REPO_ROOT / "user_data/strategies/ZoneAbsorption.py"
C = 150
ATR4 = 5.0


def _mod():
    if str(REPO_ROOT / "user_data/strategies") not in sys.path:
        sys.path.insert(0, str(REPO_ROOT / "user_data/strategies"))
    spec = importlib.util.spec_from_file_location("ZoneAbsorption", NGUON)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)  # type: ignore[union-attr]
    return m


@pytest.fixture(scope="module")
def mod():
    return _mod()


def _chien_luoc(mod, arm: str):
    s = mod.ZoneAbsorption(config={"stake_currency": "USDT", "exchange": {"name": "binance"}})
    s._arm = arm
    return s


def _df1(close_c: float) -> pd.DataFrame:
    n = 400
    d = pd.DataFrame({
        "date": pd.date_range("2025-01-01", periods=n, freq="1h", tz="UTC"),
        "open": 100.0, "high": 101.0, "low": 99.5, "close": 100.0, "volume": 1000.0,
        "rsi_1h": 50.0, "volume_ma_1h": 900.0,
    })
    d.loc[C, ["open", "high", "low", "close"]] = [close_c + 1.0, close_c + 1.5, close_c - 3.0, close_c]
    return d


def _df4(zones: list[tuple[int, float, float]]) -> pd.DataFrame:
    n = 100
    d = pd.DataFrame({
        "date": pd.date_range("2025-01-01", periods=n, freq="4h", tz="UTC"),
        "close": 100.0, "atr_4h": ATR4, "trend_dir_4h": "UP", "zone_valid": False, "ke_hoach_json": "",
    })
    for j, zl, zh in zones:
        sw = int(d["date"].iloc[j - 3].timestamp() * 1000)
        d.loc[j, "zone_valid"] = True
        d.loc[j, "ke_hoach_json"] = json.dumps({"zl": zl, "zh": zh, "zs": 0.6, "sw": sw})
    return d


ZONE_A = (20, 98.0, 99.0)
ZONE_B = (21, 90.0, 91.0)


@pytest.fixture
def quet_gia(mod, monkeypatch):
    """Bộ quét trả C cho MỌI zone có cửa sổ chứa C — đúng hình kết quả thật."""

    def _gia(*_a, tu: int, den: int, **_k):
        if not (tu <= C < den):
            return KetQuaQuetXacNhanZone(None, None, 0)
        return KetQuaQuetXacNhanZone(
            nen_xac_nhan_that=C, nen_xac_nhan_phan_thuc=C, lan_cham_phan_thuc=1,
            nen_cham_dau_that=C, loai_xac_nhan_that="ac",
        )

    monkeypatch.setattr(mod, "quet_xac_nhan_zone", _gia)


def _chay(mod, arm: str, close_c: float, zones) -> pd.DataFrame:
    s = _chien_luoc(mod, arm)
    d = _df1(close_c)
    s._xac_nhan_3_3b(d, _df4(zones), "TEST/USDT:USDT")
    return d


def _sl(zl: float, mod) -> float:
    return sl_kieu_zone(zone_low=zl, atr_4h=ATR4, buf_sl_he_so=_chien_luoc(mod, "Z0")._buf_sl_he_so)


@pytest.mark.usefixtures("quet_gia")
class TestKhongXacNhanKhiThungSl:
    def test_z0_t1_dong_duoi_sl_khong_xac_nhan(self, mod, caplog) -> None:
        with caplog.at_level(logging.INFO):
            d = _chay(mod, "Z0-T1", _sl(98.0, mod) - 1.0, [ZONE_A])
        assert not d["xac_nhan_3_3b"].any()
        assert any("thung_sl=1" in r.getMessage() for r in caplog.records), "không đếm vào log XAC_NHAN_3_3B"

    def test_z1_cung_zone_thung_cung_khong_xac_nhan(self, mod) -> None:
        """Z1 có kh.sl = p1 − 2,2×ATR < p1 theo cấu tạo — so `kh.sl` sẽ để lọt;
        phép kiểm phải theo SL KIỂU ZONE, độc lập arm (#5: Z1 không sống lâu hơn Z0)."""
        d = _chay(mod, "Z1", _sl(98.0, mod) - 1.0, [ZONE_A])
        assert not d["xac_nhan_3_3b"].any()

    def test_ca_bi_p_avg_che_van_khong_xac_nhan(self, mod) -> None:
        """close(C) nhỉnh dưới SL: p1 < sl nhưng p_avg ba tranche > sl ⇒ R_eff DƯƠNG ⇒
        bản cũ MỞ LỆNH dưới SL, không exception nào. Kiểm cả tiền đề của ca."""
        sl = _sl(98.0, mod)
        close_c = sl - 0.1
        kh = tinh_ke_hoach(zone_low=98.0, zone_high=99.0, gia_dong_cua=close_c, atr_4h=ATR4,
                           atr_1h_tai_tranche1=0.0, buf_sl_he_so=_chien_luoc(mod, "Z0")._buf_sl_he_so)
        assert kh.p1 < kh.sl and kh.r_eff_plan > 0, "tiền đề ca 'p_avg che' không còn đúng"
        d = _chay(mod, "Z0-T1", close_c, [ZONE_A])
        assert not d["xac_nhan_3_3b"].any()

    def test_dong_bang_dung_sl_khong_xac_nhan(self, mod) -> None:
        d = _chay(mod, "Z0-T1", _sl(98.0, mod), [ZONE_A])
        assert not d["xac_nhan_3_3b"].any()


@pytest.mark.usefixtures("quet_gia")
class TestDoiChungVaTraCho:
    def test_dong_tren_sl_van_xac_nhan_va_p1_tren_sl(self, mod) -> None:
        """Đối chứng: phép kiểm không chặn thừa. Quan hệ ghim: xác nhận ⇒ p1 > kh.sl."""
        d = _chay(mod, "Z0-T1", _sl(98.0, mod) + 0.5, [ZONE_A])
        assert d["xac_nhan_3_3b"].iloc[C]
        kh = json.loads(d["ke_hoach_json_3_3b"].iloc[C])
        assert kh["p1"] > kh["sl"]

    def test_xac_nhan_ma_khong_chiem_cho_zone_lanh(self, mod, caplog) -> None:
        """close(C) = 95: thủng SL zone A (96), KHÔNG thủng SL zone B (88). Bản cũ: A
        chiếm chỗ tại C, B bị đếm `trung_nen` ⇒ kế hoạch tại C là của A. Bản vá: C
        thuộc B."""
        with caplog.at_level(logging.INFO):
            d = _chay(mod, "Z0-T1", 95.0, [ZONE_A, ZONE_B])
        assert d["xac_nhan_3_3b"].iloc[C]
        assert json.loads(d["ke_hoach_json_3_3b"].iloc[C])["zl"] == 90.0
        assert any("trung_nen=0 thung_sl=1" in r.getMessage() for r in caplog.records)


class TestMotNguonCongThuc:
    def test_tinh_ke_hoach_dung_dung_sl_kieu_zone(self) -> None:
        for zl, atr, b in [(98.0, 5.0, 0.4), (0.0185, 0.0007, 0.3), (0.4955, 0.02, 0.5)]:
            kh = tinh_ke_hoach(zone_low=zl, zone_high=zl * 1.01, gia_dong_cua=zl * 1.02, atr_4h=atr,
                               atr_1h_tai_tranche1=0.0, buf_sl_he_so=b)
            assert kh.sl == sl_kieu_zone(zone_low=zl, atr_4h=atr, buf_sl_he_so=b)

    def test_chien_luoc_goi_sl_kieu_zone_khong_tu_tinh_lai(self) -> None:
        src = NGUON.read_text(encoding="utf-8")
        assert "sl_zone = sl_kieu_zone(" in src
        assert "zl * (1.0 - self._buf_sl_he_so" not in src, "công thức SL viết lại lần hai trong chiến lược"
        tp = (REPO_ROOT / "src/tool_d/trade_plan.py").read_text(encoding="utf-8")
        assert "sl = sl_kieu_zone(" in tp

    def test_dieu_kien_dung_truoc_kiem_trung_nen(self) -> None:
        """Thứ tự chỉ quyết ĐẾM (hành vi trả chỗ do `continue` trước khi gán): một C thủng SL
        rơi vào nến đã có chỗ phải đếm `thung_sl`, không lẫn vào `trung_nen`. Đo 17/09: đảo
        thứ tự thì ca hành vi vẫn xanh — chỉ ca này đỏ."""
        src = NGUON.read_text(encoding="utf-8")
        assert src.index("if dong[c] <= sl_zone:") < src.index("if xac_nhan[c]:")
        assert np.isfinite(ATR4)
