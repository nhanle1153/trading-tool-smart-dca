"""TD-0114 — mã hoá/giải mã kế hoạch qua order tag (`ZoneAbsorptionMinimal.py`).

Đây là mảnh PURE duy nhất tách được ra khỏi chiến lược (phần còn lại
cần trạng thái Freqtrade thật — `trade`, `dataprovider` — chỉ kiểm được
bằng backtest thật, xem `docs/research-log.md` 07/09/2026 cho bằng
chứng đầy đủ, gồm cả bug thật đã bắt và sửa).

`sys.path` chèn thẳng thư mục `user_data/strategies` — chiến lược
Freqtrade không phải một package cài đặt được, đây là cách duy nhất
import nó từ ngoài mà không cần chạy qua `freqtrade` CLI.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "user_data" / "strategies"))

from ZoneAbsorptionMinimal import _giai_ma_ke_hoach, _ma_hoa_ke_hoach  # noqa: E402
from tool_d.trade_plan import tinh_ke_hoach  # noqa: E402


class TestMaHoaGiaiMaKeHoach:
    def test_roundtrip_giu_nguyen_gia_tri(self) -> None:
        kh = tinh_ke_hoach(zone_low=90, zone_high=100, gia_dong_cua=95, atr_4h=2.0, atr_1h_tai_tranche1=0.0, buf_sl_he_so=0.4)
        tag = _ma_hoa_ke_hoach(kh)
        kh2 = _giai_ma_ke_hoach(tag, atr_1h_tai_tranche1=1.5)
        assert kh2 is not None
        assert kh2.zone_low == kh.zone_low
        assert kh2.zone_high == kh.zone_high
        assert kh2.p1 == kh.p1
        assert kh2.p2 == kh.p2
        assert kh2.p3 == kh.p3
        assert kh2.sl == kh.sl
        # atr_1h_tai_tranche1 KHÔNG nằm trong tag — được truyền riêng lúc
        # giải mã (đọc từ dataframe 1H tại thời điểm khởi tạo custom_data).
        assert kh2.atr_1h_tai_tranche1 == 1.5

    def test_tag_rong_hoac_none_tra_ve_none(self) -> None:
        assert _giai_ma_ke_hoach(None, atr_1h_tai_tranche1=0.0) is None
        assert _giai_ma_ke_hoach("", atr_1h_tai_tranche1=0.0) is None

    def test_tag_khong_phai_json_tra_ve_none_khong_raise(self) -> None:
        # Ca thật: tag của lệnh EXIT (vd "TIME_STOP") không phải JSON —
        # phải trả None êm, không được crash strategy.
        assert _giai_ma_ke_hoach("TIME_STOP", atr_1h_tai_tranche1=0.0) is None

    def test_tag_json_thieu_khoa_tra_ve_none(self) -> None:
        assert _giai_ma_ke_hoach('{"zl": 90}', atr_1h_tai_tranche1=0.0) is None

    def test_tag_gon_trong_gioi_han_255_ky_tu_cua_freqtrade(self) -> None:
        kh = tinh_ke_hoach(zone_low=0.0123456789, zone_high=0.0198765432, gia_dong_cua=0.015, atr_4h=0.0005, atr_1h_tai_tranche1=0.0, buf_sl_he_so=0.4)
        tag = _ma_hoa_ke_hoach(kh)
        assert len(tag.encode("utf-8")) <= 255
