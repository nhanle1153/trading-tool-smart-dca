"""TD-0345 (`DR-D4-16` §3–§4) — hàm đếm mô tả: đầu ra CHỈ các tên allowlist, không số lãi/lỗ nào lọt ra.

Canh:
1. Mọi khoá đầu ra ∈ `CTRL_MO_TA_ALLOWED` — và hàm tự RAISE nếu một khoá lạ xuất hiện (phá thật bằng vá hằng số).
2. Lệnh mang `profit_abs`, `exit_reason`, `liquidation_price`: không giá trị nào của chúng xuất hiện trong đầu ra
   (kiểm bằng cách tìm chính con số đó trong JSON đầu ra, không chỉ tìm tên khoá).
3. Số đếm đúng: tổng, theo tháng, số mã, phân bố số tranche đã khớp.
"""

from __future__ import annotations

import json
from datetime import date

import pytest

import tool_d.ablation.dem_mo_ta as mod
from tool_d.ablation.dem_mo_ta import DemMoTaError, dem_mo_ta
from tool_d.ledger.registry import CTRL_MO_TA_ALLOWED


def _o(ts: int) -> dict:
    return {"amount": 1.0, "safe_price": 100.0, "ft_is_entry": True, "order_filled_timestamp": ts}


LENH = [
    {"pair": "A/USDT:USDT", "open_date": "2025-07-01 04:00:00+00:00", "orders": [_o(1)],
     "profit_abs": 123.456789, "exit_reason": "TP2_TRAIL", "liquidation_price": 77.7},
    {"pair": "A/USDT:USDT", "open_date": "2025-07-20 04:00:00+00:00", "orders": [_o(1), _o(2), _o(3)],
     "profit_abs": -98.765432, "exit_reason": "stop_loss"},
    {"pair": "B/USDT:USDT", "open_date": "2025-08-02 11:00:00+00:00", "orders": [_o(1), _o(2)],
     "profit_abs": 4.321098, "exit_reason": "TIME_STOP"},
]
CUA_SO = dict(observed_start=date(2025, 6, 12), observed_end=date(2026, 1, 28))


class TestDauRa:
    def test_chi_ten_allowlist(self) -> None:
        assert set(dem_mo_ta(LENH, **CUA_SO)) <= CTRL_MO_TA_ALLOWED

    def test_khong_so_lai_lo_nao_lot_ra(self) -> None:
        chuoi = json.dumps(dem_mo_ta(LENH, **CUA_SO))
        for bi_cam in ("123.456789", "-98.765432", "4.321098", "77.7", "TP2_TRAIL", "stop_loss", "TIME_STOP",
                       "profit", "exit_reason", "liquidation"):
            assert bi_cam not in chuoi, bi_cam

    def test_so_dem_dung(self) -> None:
        r = dem_mo_ta(LENH, **CUA_SO)
        assert r["so_lenh"] == 3 and r["so_ma_co_lenh"] == 2
        assert r["so_lenh_theo_thang"] == {"2025-07": 2, "2025-08": 1}
        assert r["phan_bo_so_tranche"] == {"1": 1, "2": 1, "3": 1}
        ngay = (CUA_SO["observed_end"] - CUA_SO["observed_start"]).days + 1
        assert r["lenh_moi_nam"] == pytest.approx(3 / (ngay / 365.25))


class TestTuChoi:
    def test_khoa_la_thi_RAISE_khong_lot_ra(self, monkeypatch) -> None:
        """Phá thật: thu hẹp allowlist mà hàm đọc ⇒ một khoá hợp lệ hôm nay trở thành 'lạ' ⇒ phải raise."""
        monkeypatch.setattr(mod, "CTRL_MO_TA_ALLOWED", frozenset({"so_lenh"}))
        with pytest.raises(DemMoTaError, match="allowlist"):
            dem_mo_ta(LENH, **CUA_SO)

    def test_cua_so_rong(self) -> None:
        with pytest.raises(DemMoTaError):
            dem_mo_ta(LENH, observed_start=date(2025, 2, 1), observed_end=date(2025, 1, 1))

    def test_thieu_open_date(self) -> None:
        with pytest.raises(DemMoTaError):
            dem_mo_ta([{"pair": "X", "orders": []}], **CUA_SO)
