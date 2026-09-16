"""🔒 TD-0283 — `wfo/lenh.py`: bản ghi từng lệnh, công thức `DR-D4-12` §1.4, cắt lát.

Canh:
1. **Công thức rủi ro đã triển khai** tính tay từ định nghĩa §1.4.
2. **Hai thước cạnh nhau** — `r_trien_khai` và `r_realized` khác mẫu số, không lẫn.
3. **Cắt lát theo fold dùng fold THẬT** (`sinh_folds` trên YAML thật): đoạn train-only
   đầu cửa sổ không vào lát nào (`MT-36`), biên nửa mở, lệnh ngoài cửa sổ ⇒ raise.
4. **Cắt lát theo khối** khớp đúng phép gán khối của `tinh_pbo` — hai nơi gán khối
   mà lệch nhau là hai thước cho một câu hỏi.
5. **Lệnh đủ hình dạng để `tinh_pbo` nhận** (`LenhCoR`).
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from tool_d.config.loader import load_tool_d_config
from tool_d.gates.cscv import tinh_pbo
from tool_d.gates.cscv_cau_hinh import DEFAULT_DR_D9_01_PATH, doc_cau_hinh_cscv
from tool_d.wfo.folds import sinh_folds
from tool_d.wfo.lenh import (
    LenhWFO,
    LenhWFOError,
    TrancheKhop,
    cat_lat_theo_fold,
    cat_lat_theo_khoi,
    rui_ro_da_trien_khai_usdt,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CFG = load_tool_d_config(REPO_ROOT / "config" / "tool_d_config.yaml")
CH = doc_cau_hinh_cscv(CFG, dr_path=REPO_ROOT / DEFAULT_DR_D9_01_PATH)
FOLDS = sinh_folds(CFG)
T1, T2 = CH.t1, CH.t2


def _l(od: datetime, pnl: float = 1.0, *, rui_ro: float = 2.0, ke_hoach: float = 4.0, pair: str = "X/USDT") -> LenhWFO:
    return LenhWFO(
        pair=pair, open_date=od, close_date=od + timedelta(hours=5), pnl_abs=pnl,
        rui_ro_da_trien_khai_usdt=rui_ro, planned_risk_usdt=ke_hoach,
    )


class TestCongThucRuiRo:
    def test_hai_tranche_tinh_tay(self) -> None:
        """sl = 90. T1: 300 USDT tại 100 ⇒ 300×10/100 = 30. T2: 200 tại 95 ⇒ 200×5/95 = 10,526…"""
        v = rui_ro_da_trien_khai_usdt([TrancheKhop(300, 100), TrancheKhop(200, 95)], sl=90)
        assert math.isclose(v, 30 + 200 * 5 / 95)

    def test_chi_tranche_da_khop_moi_tinh(self) -> None:
        """Một tranche khớp thì rủi ro chỉ của tranche đó — không phải ngân sách ba tranche."""
        assert math.isclose(rui_ro_da_trien_khai_usdt([TrancheKhop(300, 100)], sl=90), 30.0)

    def test_khong_tranche_nao_raise(self) -> None:
        with pytest.raises(LenhWFOError, match="không có tranche"):
            rui_ro_da_trien_khai_usdt([], sl=90)

    @pytest.mark.parametrize("entry", [90, 85])
    def test_entry_khong_tren_sl_raise(self, entry: float) -> None:
        with pytest.raises(LenhWFOError, match="không có rủi ro dương"):
            rui_ro_da_trien_khai_usdt([TrancheKhop(300, entry)], sl=90)

    @pytest.mark.parametrize("xau", [0, -1, math.nan, math.inf, True])
    def test_stake_xau_raise(self, xau) -> None:
        with pytest.raises(LenhWFOError):
            rui_ro_da_trien_khai_usdt([TrancheKhop(xau, 100)], sl=90)


class TestBanGhiLenh:
    def test_hai_thuoc_khac_mau_so(self) -> None:
        l = _l(T1, pnl=3.0, rui_ro=2.0, ke_hoach=4.0)
        assert l.r_trien_khai == 1.5 and l.r_realized == 0.75

    @pytest.mark.parametrize(
        "sua",
        [
            {"pair": ""},
            {"close_date": T1 - timedelta(seconds=1)},
            {"pnl_abs": math.nan},
            {"rui_ro_da_trien_khai_usdt": 0.0},
            {"planned_risk_usdt": -1.0},
            {"open_date": T1.replace(tzinfo=__import__("datetime").timezone.utc)},
        ],
    )
    def test_ban_ghi_hong_raise(self, sua: dict) -> None:
        base = dict(pair="X/USDT", open_date=T1, close_date=T1 + timedelta(hours=1), pnl_abs=1.0,
                    rui_ro_da_trien_khai_usdt=1.0, planned_risk_usdt=1.0)
        base.update(sua)
        if "open_date" in sua:
            base["close_date"] = sua["open_date"] + timedelta(hours=1)
        with pytest.raises(LenhWFOError):
            LenhWFO(**base)


class TestCatLatTheoFold:
    def test_fold_that_va_doan_train_only(self) -> None:
        """Fold thật: test [2025-09-04, 10-23) · [10-23, 12-11) · [12-11, 2026-01-29)."""
        lenh = [
            _l(datetime(2025, 6, 12)),            # train-only ⇒ không vào lát nào
            _l(datetime(2025, 9, 3, 23, 59)),     # train-only, sát biên
            _l(datetime(2025, 9, 4)),             # fold 1, biên dưới
            _l(datetime(2025, 10, 22, 23)),       # fold 1
            _l(datetime(2025, 10, 23)),           # fold 2 (nửa mở)
            _l(datetime(2026, 1, 28, 23, 59)),    # fold 3, sát T2
        ]
        lat = cat_lat_theo_fold(lenh, FOLDS, t1=T1, t2=T2)
        assert [len(x) for x in lat] == [2, 1, 1]
        assert sum(len(x) for x in lat) < len(lenh)  # n_chi_test ≤ n_toan_cua_so (MT-36)

    @pytest.mark.parametrize("od", [T1 - timedelta(seconds=1), T2])
    def test_lenh_ngoai_cua_so_raise(self, od: datetime) -> None:
        with pytest.raises(LenhWFOError, match="ngoài"):
            cat_lat_theo_fold([_l(od)], FOLDS, t1=T1, t2=T2)


class TestCatLatTheoKhoi:
    def test_moi_lenh_dung_mot_khoi_va_bien_nua_mo(self) -> None:
        moc = CH.moc_khoi()
        lenh = [_l(moc[b] + timedelta(hours=h)) for b in range(CH.so_khoi) for h in (0, 692)]
        lenh.append(_l(moc[3] - timedelta(seconds=1)))  # thuộc khối 2, không phải 3
        lat = cat_lat_theo_khoi(lenh, CH)
        assert len(lat) == 8
        assert [len(x) for x in lat] == [2, 2, 3, 2, 2, 2, 2, 2]
        assert sum(len(x) for x in lat) == len(lenh)

    def test_khop_phep_gan_khoi_cua_tinh_pbo(self) -> None:
        """A tốt hơn B ở khối lẻ, kém ở khối chẵn; lát của `cat_lat_theo_khoi` và PBO của
        `tinh_pbo` phải dựa trên CÙNG phép gán. Kiểm: tái tạo trung bình theo khối từ lát."""
        moc = CH.moc_khoi()
        a = [_l(moc[b] + timedelta(hours=k), pnl=(1.0 if b % 2 else -1.0)) for b in range(8) for k in range(40)]
        b_ = [_l(moc[b] + timedelta(hours=k), pnl=0.0, pair="Y/USDT") for b in range(8) for k in range(40)]
        lat_a = cat_lat_theo_khoi(a, CH)
        assert all(all(l.pnl_abs == (1.0 if i % 2 else -1.0) for l in x) for i, x in enumerate(lat_a))
        kq = tinh_pbo({"A": a, "B": b_}, CH)
        assert kq.so_to_hop == kq.so_to_hop_doc_duoc == 70
        assert kq.pbo.is_ok()
