"""TD-0413 — bộ đo D10 cho `RoFunding` (tầng thuần): trượt giá, SL trên sàn, đủ mẫu, kết cục cho sổ trial."""

from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jsonschema
import pytest

from tool_d.ops.do_d10 import (
    LY_DO_NA_GAP_MS,
    LY_DO_NA_POST_ONLY,
    NGUONG_TRUOT_GIA,
    LenhKhop,
    ViTheD10,
    danh_gia,
    gio_can_ro,
    ket_cuc_so_trial,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((REPO_ROOT / "registry/schemas/trial_event.schema.json").read_text(encoding="utf-8"))
UTC = timezone.utc
T0 = datetime(2026, 10, 1, 0, tzinfo=UTC)


def _mau(truot: float, *, ngay: int = 7, moi_ngay: int = 5, gia: float = 100.0):
    """`ngay` lần cân rổ × `moi_ngay` lệnh, khớp vài giây sau đầu giờ (ngày giờ SQLite không múi giờ)."""
    lenh, mo = [], {}
    for d in range(ngay):
        gio = T0 + timedelta(days=d)
        mo[("C/USDT:USDT", gio)] = gia
        for i in range(moi_ngay):
            lenh.append(LenhKhop(d * 10 + i, "C/USDT:USDT", "buy" if i % 2 else "sell",
                                 (gio + timedelta(seconds=3 + i)).replace(tzinfo=None), gia * (1 + truot), "closed"))
    vi_the = [ViTheD10(x.trade_id, x.pair, True) for x in lenh]
    return lenh, mo, vi_the


class TestKetCuc:
    def test_du_mau_truot_duoi_nguong_thi_kept(self) -> None:
        kq = danh_gia(*_mau(0.0003))
        assert kq.verdict == "KEPT" and kq.so_lenh == 35 and kq.so_lan_can_ro == 7
        assert kq.truot_gia_tb == pytest.approx(0.0003)

    def test_truot_vuot_nguong_thi_rejected(self) -> None:
        kq = danh_gia(*_mau(0.0006))
        assert kq.verdict == "REJECTED" and any("trượt giá" in x for x in kq.ly_do)

    def test_dung_nguong_van_dat(self) -> None:
        assert danh_gia(*_mau(NGUONG_TRUOT_GIA * 0.999)).verdict == "KEPT"

    def test_truot_am_tinh_theo_tri_tuyet_doi(self) -> None:
        assert danh_gia(*_mau(-0.0006)).verdict == "REJECTED"

    def test_vi_the_thieu_stop_thi_rejected_du_truot_tot(self) -> None:
        lenh, mo, vi_the = _mau(0.0001)
        vi_the[3] = ViTheD10(vi_the[3].trade_id, vi_the[3].pair, False)
        kq = danh_gia(lenh, mo, vi_the)
        assert kq.verdict == "REJECTED" and kq.vi_the_thieu_stop == (vi_the[3].trade_id,)

    @pytest.mark.parametrize(("ngay", "moi_ngay"), [(6, 6), (7, 4)], ids=["thieu-lan-can-ro", "thieu-lenh"])
    def test_thieu_mau_thi_inconclusive(self, ngay, moi_ngay) -> None:
        kq = danh_gia(*_mau(0.0001, ngay=ngay, moi_ngay=moi_ngay))
        assert kq.verdict == "INCONCLUSIVE" and any("thiếu mẫu" in x for x in kq.ly_do)

    def test_thieu_gia_mo_nen_thi_inconclusive_khong_doan(self) -> None:
        lenh, mo, vi_the = _mau(0.0001)
        mo.pop(("C/USDT:USDT", T0))
        kq = danh_gia(lenh, mo, vi_the)
        assert kq.verdict == "INCONCLUSIVE" and kq.so_lenh_thieu_gia == 5

    @pytest.mark.parametrize("gia_khop", [math.nan, 0.0, -1.0])
    def test_gia_khop_hong_la_thieu_gia(self, gia_khop) -> None:
        lenh, mo, vi_the = _mau(0.0001)
        lenh[0] = LenhKhop(lenh[0].trade_id, lenh[0].pair, lenh[0].side, lenh[0].khop_luc, gia_khop, "closed")
        assert danh_gia(lenh, mo, vi_the).so_lenh_thieu_gia == 1

    def test_lenh_stop_khong_tinh_vao_mau(self) -> None:
        lenh, mo, vi_the = _mau(0.0001)
        lenh.append(LenhKhop(999, "C/USDT:USDT", "stoploss", T0.replace(tzinfo=None), 50.0, "closed"))
        assert danh_gia(lenh, mo, vi_the).so_lenh == 35


class TestHienVat:
    def test_na_co_ly_do_khong_phai_so_0(self) -> None:
        d = danh_gia(*_mau(0.0001)).ra_dict()
        assert d["gap_ms"] == LY_DO_NA_GAP_MS and d["ty_le_khop_post_only"] == LY_DO_NA_POST_ONLY

    def test_chi_tiet_dung_ten_dau_ra_cho_phep(self) -> None:
        d = danh_gia(*_mau(0.0001)).ra_dict()
        assert {"fill_price", "p_i", "order_status"} <= set(d["chi_tiet"][0])
        assert not any(k for k in d["chi_tiet"][0] if "pnl" in k or "profit" in k)

    def test_gio_can_ro_chuan_hoa_utc(self) -> None:
        assert gio_can_ro(datetime(2026, 10, 1, 0, 0, 7)) == T0
        assert gio_can_ro(datetime(2026, 10, 1, 7, 0, 7, tzinfo=timezone(timedelta(hours=7)))) == T0

    def test_ket_cuc_khop_schema_consume(self) -> None:
        kq = danh_gia(*_mau(0.0001))
        su_kien = {"event": "CONSUME", "trial_id": "D-0001", "executed_at": "2026-10-08T00:00:00Z",
                   "outcome": ket_cuc_so_trial(kq), "verdict": kq.verdict, "rejection_reason": None, "retest_forbidden": True}
        jsonschema.validate(su_kien, SCHEMA)
