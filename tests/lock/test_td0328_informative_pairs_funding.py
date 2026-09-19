"""TD-0328 — `informative_pairs()` khai `funding_rate` cho LIVE/dry-run, chỉ khi SHORT bật.

Khoảng hở (nợ còn lại của TD-0323): ở live/dry-run `dp.get_pair_dataframe(...,
candle_type="funding_rate")` đọc bộ nhớ đệm do CHÍNH `informative_pairs()` nạp. Hàm
đó chỉ trả 4H/1D ⇒ `_funding_8h()` nhận khung rỗng ⇒ DG6-D không bao giờ nổ. Backtest
không bị ảnh hưởng: Freqtrade chỉ gọi `gather_informative_pairs()` ở `freqtradebot.py`
(đọc mã nguồn 2026.8), backtest tự tải funding từ đĩa.

Ba ràng buộc, mỗi cái có ca riêng và có răng (phá thật → đúng ca đó đỏ):
  1. **`enable_short=False` ⇒ giá trị trả về GIỐNG HỆT** như trước TD-0328, từng phần tử,
     so với danh sách viết tay — đường LONG không đổi một bit (`DR-SHORT-01` §7).
  2. **`enable_short=True` ⇒ thêm `(pair, khung_funding, "funding_rate")` cho MỌI cặp**,
     khung lấy từ `dp.get_funding_rate_timeframe()` chứ không hard-code.
  3. **Freqtrade THẬT chấp nhận định dạng**: đi qua `IStrategy.gather_informative_pairs()`
     (không chỉ chuỗi ta tự viết) và ra `CandleType.FUNDING_RATE` đúng khung.

⚠️ Giới hạn: không gọi được sàn thật (không mạng, không testnet ở phạm vi này). File này
chứng minh ĐỊNH DẠNG và đường LONG, KHÔNG chứng minh tần suất gọi API ở live — điều đó
ghi ở dòng `TD-0328` trong `TASKS.md` là điều kiện trước khi mở `enable_short`.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from freqtrade.enums import CandleType

REPO_ROOT = Path(__file__).resolve().parents[2]
CHIEN_LUOC_PATH = REPO_ROOT / "user_data" / "strategies" / "ZoneAbsorption.py"
PAIRS = ["AAA/USDT:USDT", "BBB/USDT:USDT"]
KHUNG_FUNDING_GIA = "8h"  # cố tình KHÁC "1h" thật của Binance để phân biệt với hard-code


class _DpGia:
    def current_whitelist(self):
        return list(PAIRS)

    def get_funding_rate_timeframe(self) -> str:
        return KHUNG_FUNDING_GIA


def _chien_luoc(*, enable_short: bool):
    spec = importlib.util.spec_from_file_location("ZoneAbsorptionTD0328", CHIEN_LUOC_PATH)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)  # type: ignore[union-attr]
    s = m.ZoneAbsorption(
        config={
            "stake_currency": "USDT",
            "exchange": {"name": "binance"},
            "candle_type_def": CandleType.FUTURES,
        }
    )
    s._enable_short = enable_short
    s.dp = _DpGia()
    return s


# Danh sách VIẾT TAY của hành vi trước TD-0328 — không sinh từ code đang kiểm.
CU = [(p, "4h") for p in PAIRS] + [(p, "1d") for p in PAIRS]


class TestDuongLongKhongDoi:
    def test_tat_short_tra_dung_danh_sach_cu(self) -> None:
        assert _chien_luoc(enable_short=False).informative_pairs() == CU

    def test_tat_short_khong_hoi_khung_funding(self) -> None:
        """Tắt thì không được đụng tới thứ gì của funding — kể cả việc hỏi `dp`."""

        class _DpCam(_DpGia):
            def get_funding_rate_timeframe(self) -> str:
                raise AssertionError("đường LONG không được hỏi khung funding")

        s = _chien_luoc(enable_short=False)
        s.dp = _DpCam()
        assert s.informative_pairs() == CU

    def test_qua_freqtrade_that_tat_short_khong_co_funding(self) -> None:
        tap = _chien_luoc(enable_short=False).gather_informative_pairs()
        assert all(t[2] != CandleType.FUNDING_RATE for t in tap)
        assert len(tap) == len(CU)


class TestBatShort:
    def test_giu_nguyen_phan_cu_va_them_dung_bo_ba_funding(self) -> None:
        kq = _chien_luoc(enable_short=True).informative_pairs()
        assert kq[: len(CU)] == CU, "phần 4H/1D không được đổi thứ tự hay nội dung"
        assert kq[len(CU):] == [(p, KHUNG_FUNDING_GIA, "funding_rate") for p in PAIRS]

    def test_khung_lay_tu_dp_khong_hard_code(self) -> None:
        kq = _chien_luoc(enable_short=True).informative_pairs()
        khung = {t[1] for t in kq if len(t) == 3}
        assert khung == {KHUNG_FUNDING_GIA}, "dp báo 8h — bất kỳ '1h' nào là hard-code"

    def test_moi_cap_deu_co_funding(self) -> None:
        kq = _chien_luoc(enable_short=True).informative_pairs()
        assert {t[0] for t in kq if len(t) == 3} == set(PAIRS)


class TestFreqtradeThatChapNhan:
    def test_gather_informative_pairs_doi_dung_candle_type_funding(self) -> None:
        tap = _chien_luoc(enable_short=True).gather_informative_pairs()
        funding = [t for t in tap if t[2] == CandleType.FUNDING_RATE]
        assert sorted(funding) == sorted((p, KHUNG_FUNDING_GIA, CandleType.FUNDING_RATE) for p in PAIRS)

    def test_phan_4h_1d_van_mang_candle_type_futures(self) -> None:
        tap = _chien_luoc(enable_short=True).gather_informative_pairs()
        cu = [t for t in tap if t[2] != CandleType.FUNDING_RATE]
        assert len(cu) == len(CU)
        assert {t[2] for t in cu} == {CandleType.FUTURES}
