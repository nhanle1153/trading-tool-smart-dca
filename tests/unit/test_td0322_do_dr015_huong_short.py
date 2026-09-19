"""TD-0322 — bộ đo DR-015 (Bước 1 + Bước 3) SẴN hướng Short, KHÔNG chạy.

`DR-SHORT-01` §5: dựng, không đo. Hai ràng buộc quyết định hình dạng file này:

1. **Đường Long không đổi một bit** (§7). Tham số hướng mặc định là `long`;
   ca dữ liệu THẬT (91 lượt khớp niêm phong D3.5) phải cho đúng con số
   `L-Z56` đang ghim.
2. **Short chỉ bật khi được truyền tường minh.** Dữ liệu toàn Short vào
   `tinh_doi_chung()` mặc định vẫn phải nổ `Buoc1Error` (ghim của TD-0163).

Fixture Short dựng tay trong bộ nhớ — không đọc/ghi `docs/du-lieu-do/` và
không chạm sổ trial: đây là phép kiểm CƠ CHẾ, không phải đo Δ_R(SHORT).
"""

from __future__ import annotations

import pytest

from tool_d.dr015.buoc1_lech_tranche import (
    Buoc1Error,
    _doc_du_lieu_tho,
    _gia_ke_hoach_ca_ba_tranche,
    tinh_buoc1,
)
from tool_d.dr015.buoc3_doi_chung_z0 import tinh_doi_chung

# Zone 100–110, Short neo mép TRÊN (p3 = 110), SL nằm TRÊN zone.
ZONE_LOW, ZONE_HIGH, SL_SHORT = 100.0, 110.0, 115.0
GIA = {"zone_low": ZONE_LOW, "zone_high": ZONE_HIGH, "sl": SL_SHORT}

# Tranche 1 khớp 100.5 (kế hoạch 100), tranche 2 khớp đúng 105, tranche 3
# khớp 111 (kế hoạch 110 = zone_high). Mỗi tranche amount = 1.
RISK_SHORT = (100.5 / 100.0) * abs(100.0 - SL_SHORT) + (105.0 / 105.0) * abs(105.0 - SL_SHORT) + (
    111.0 / 110.0
) * abs(110.0 - SL_SHORT)


def _rows_short() -> list[dict]:
    return [
        {**GIA, "trade_idx": 1, "tranche": 1, "huong": "short",
         "p_ke_hoach": 100.0, "fill_price": 100.5, "amount": 1.0, "cost": 100.5},
        {**GIA, "trade_idx": 1, "tranche": 2, "huong": "short",
         "p_ke_hoach": 105.0, "fill_price": 105.0, "amount": 1.0, "cost": 105.0},
        {**GIA, "trade_idx": 1, "tranche": 3, "huong": "short",
         "p_ke_hoach": 110.0, "fill_price": 111.0, "amount": 1.0, "cost": 111.0},
    ]


class TestGiaKeHoachTheoHuong:
    def test_mac_dinh_la_long_p3_bang_zone_low(self) -> None:
        p = _gia_ke_hoach_ca_ba_tranche(GIA, 110.0)
        assert p == {1: 110.0, 2: 105.0, 3: ZONE_LOW}

    def test_long_tuong_minh_giong_mac_dinh(self) -> None:
        assert _gia_ke_hoach_ca_ba_tranche(GIA, 110.0, "long") == _gia_ke_hoach_ca_ba_tranche(
            GIA, 110.0
        )

    def test_short_p3_bang_zone_high(self) -> None:
        p = _gia_ke_hoach_ca_ba_tranche(GIA, 100.0, "short")
        assert p == {1: 100.0, 2: 105.0, 3: ZONE_HIGH}

    def test_huong_la_thi_raise(self) -> None:
        with pytest.raises(Buoc1Error):
            _gia_ke_hoach_ca_ba_tranche(GIA, 100.0, "ngang")


class TestTinhBuoc1Short:
    def test_short_tinh_duoc_va_dung_p3_zone_high(self) -> None:
        kq = tinh_buoc1({"luot_khop": _rows_short()})
        assert kq["SHORT"].so_lenh == 1
        assert kq["SHORT"].delta_r.is_ok()
        # Chỉ tranche 3 lệch (111 vs 110), tranche 2 khớp đúng, tranche 1 không tính.
        assert kq["SHORT"].lech_moi_lenh[0] == pytest.approx(1.0 / RISK_SHORT, rel=1e-12)

    def test_kiem_co_rang_p3_zone_low_cho_so_khac(self) -> None:
        """Nếu nhánh Short lỡ dùng `zone_low` làm p3 thì lệch phải ra số KHÁC
        (lệch 11 thay vì 1) — ca này đỏ khi ai đó trả `3: zl` về như cũ."""
        kq = tinh_buoc1({"luot_khop": _rows_short()})
        risk_sai = (100.5 / 100.0) * 15.0 + 10.0 + (111.0 / 100.0) * abs(100.0 - SL_SHORT)
        so_sai = 11.0 / risk_sai
        assert kq["SHORT"].lech_moi_lenh[0] != pytest.approx(so_sai, rel=1e-3)

    def test_long_van_unreadable_khi_khong_co_lenh_long(self) -> None:
        kq = tinh_buoc1({"luot_khop": _rows_short()})
        assert kq["LONG"].so_lenh == 0
        assert not kq["LONG"].delta_r.is_ok()
        assert kq["LONG"].delta_r.status.value == "unreadable"


class TestDuongLongKhongDoi:
    """§7 DR-SHORT-01: dữ liệu THẬT, tham số hướng để mặc định."""

    def test_delta_r_long_that_dung_con_so_niem_phong(self) -> None:
        du_lieu = _doc_du_lieu_tho()
        kq = tinh_buoc1(du_lieu)
        assert kq["LONG"].so_lenh > 0
        assert kq["LONG"].delta_r.value == pytest.approx(0.16120552895757337, abs=1e-12)
        assert kq["SHORT"].so_lenh == 0

    def test_doi_chung_long_mac_dinh_giong_tuong_minh(self) -> None:
        du_lieu = _doc_du_lieu_tho()
        a = tinh_doi_chung(du_lieu)
        b = tinh_doi_chung(du_lieu, huong="long")
        assert a == b
        assert {k: v.huong for k, v in a.items()} == {"Z0": "LONG", "DCA": "LONG"}


class TestDoiChungShort:
    def test_mac_dinh_du_lieu_toan_short_van_no(self) -> None:
        """Ghim TD-0163: không truyền hướng ⇒ vẫn là LONG ⇒ dữ liệu toàn short nổ."""
        with pytest.raises(Buoc1Error, match="LONG"):
            tinh_doi_chung({"luot_khop": _rows_short()})

    def test_short_tuong_minh_chay_duoc(self) -> None:
        kq = tinh_doi_chung({"luot_khop": _rows_short()}, huong="short")
        assert set(kq) == {"Z0", "DCA"}
        assert kq["Z0"].huong == "SHORT" and kq["DCA"].huong == "SHORT"
        # Z0 = |lệch| tranche 1 = 0.5 ; DCA = tranche 2 (0) + tranche 3 (1) = 1.
        assert kq["Z0"].lech_moi_lenh[0] == pytest.approx(0.5 / RISK_SHORT, rel=1e-12)
        assert kq["DCA"].lech_moi_lenh[0] == pytest.approx(1.0 / RISK_SHORT, rel=1e-12)

    def test_short_tuong_minh_ma_khong_co_dong_short_thi_no(self) -> None:
        du_lieu = _doc_du_lieu_tho()  # toàn long
        with pytest.raises(Buoc1Error, match="SHORT"):
            tinh_doi_chung(du_lieu, huong="short")

    def test_huong_la_thi_raise(self) -> None:
        with pytest.raises(Buoc1Error):
            tinh_doi_chung({"luot_khop": _rows_short()}, huong="ngang")
