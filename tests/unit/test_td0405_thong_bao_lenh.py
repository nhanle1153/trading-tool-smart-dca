"""TD-0405 — tin Telegram khi lệnh vào KHỚP: đúng số chủ dự án đưa (25/09/2026), và N6 (không bịa số)."""

from __future__ import annotations

import math

import pytest

from tool_d.ops.thong_bao_lenh import CHUA_DO, soan_tin_vao_lenh

# Mẫu chủ dự án: SHORT 5x, ký quỹ 299.74, vị thế 1,498.69, SL 0.05761 cách 4.75%, rủi ro 71.12 = 3.37% của 2,113.11.
GIA_VAO = 0.055
SL_SHORT = 0.05761
AMOUNT = 1498.69 / GIA_VAO


def _tin(**sua):
    tham_so = dict(
        trade_id=10, pair="LAB/USDT:USDT", is_short=True, leverage=5.0, tranche=1, so_tranche=3,
        stake_usdt=299.74, amount=AMOUNT, open_rate=GIA_VAO, sl=SL_SHORT, von_usdt=2113.11,
    )
    tham_so.update(sua)
    return soan_tin_vao_lenh(**tham_so)


def test_dung_khuon_mau_chu_du_an() -> None:
    assert _tin() == (
        "🆕 Lệnh mới #10 LAB/USDT:USDT SHORT 5x\n"
        "Ký quỹ 299.74 USDT · vị thế 1,498.69 USDT\n"
        "Cắt lỗ 0.05761 (cách giá vào 4.75%)\n"
        "Rủi ro nếu chạm cắt lỗ: 71.12 USDT = 3.37% vốn (vốn 2,113.11 USDT, chưa gồm phí)"
    )


def test_long_khoang_cat_lo_tinh_duoi_gia_vao() -> None:
    # Long 3x: vào 2.0, SL 1.9 ⇒ cách 5.00%; 100 đơn vị ⇒ rủi ro 10.00 = 1.00% của 1,000.
    tin = _tin(is_short=False, leverage=3.0, stake_usdt=66.67, amount=100.0, open_rate=2.0, sl=1.9, von_usdt=1000.0)
    dong = tin.splitlines()
    assert dong[0] == "🆕 Lệnh mới #10 LAB/USDT:USDT LONG 3x"
    assert dong[1] == "Ký quỹ 66.67 USDT · vị thế 200.00 USDT"
    assert dong[2] == "Cắt lỗ 1.9 (cách giá vào 5.00%)"
    assert dong[3] == "Rủi ro nếu chạm cắt lỗ: 10.00 USDT = 1.00% vốn (vốn 1,000.00 USDT, chưa gồm phí)"


def test_tranche_sau_doi_dong_dau_va_dung_tong_vi_the() -> None:
    """Số là TỔNG vị thế đã khớp — hàm nhận `amount`/`open_rate` của cả trade, không tự trừ phần cũ."""
    tin = _tin(tranche=2, amount=2 * AMOUNT, stake_usdt=599.48)
    dong = tin.splitlines()
    assert dong[0] == "➕ Vào thêm lần 2/3 #10 LAB/USDT:USDT SHORT 5x"
    assert dong[1] == "Ký quỹ 599.48 USDT · vị thế 2,997.38 USDT"
    assert dong[3].startswith("Rủi ro nếu chạm cắt lỗ: 142.24 USDT = 6.73% vốn")


def test_gia_rat_nho_khong_ra_dang_mu() -> None:
    tin = _tin(open_rate=0.00001200, sl=0.00001260, amount=1e8)
    assert "Cắt lỗ 0.0000126 (cách giá vào 5.00%)" in tin
    assert "e-" not in tin


@pytest.mark.parametrize("sl", [None, math.nan, 0.0])
def test_thieu_sl_khong_bia_so(sl) -> None:
    dong = _tin(sl=sl).splitlines()
    assert dong[2] == f"Cắt lỗ: {CHUA_DO}"
    assert dong[3] == f"Rủi ro nếu chạm cắt lỗ: {CHUA_DO}"
    assert "0.00 USDT" not in dong[3]


@pytest.mark.parametrize("von", [None, 0.0, -5.0, math.inf])
def test_thieu_von_van_in_rui_ro_usdt_nhung_khong_bia_phan_tram(von) -> None:
    dong = _tin(von_usdt=von).splitlines()
    assert dong[3] == f"Rủi ro nếu chạm cắt lỗ: 71.12 USDT = % vốn {CHUA_DO} (chưa gồm phí)"


def test_thieu_khoi_luong_khong_bia_vi_the_va_rui_ro() -> None:
    dong = _tin(amount=None).splitlines()
    assert dong[1] == f"Ký quỹ 299.74 USDT · vị thế {CHUA_DO}"
    assert dong[2] == "Cắt lỗ 0.05761"
    assert dong[3] == f"Rủi ro nếu chạm cắt lỗ: {CHUA_DO}"


@pytest.mark.parametrize(
    ("is_short", "sl"),
    [(True, 0.054), (True, GIA_VAO), (False, 0.056), (False, GIA_VAO)],
    ids=["short-sl-duoi", "short-sl-bang", "long-sl-tren", "long-sl-bang"],
)
def test_sl_sai_phia_bao_bat_thuong_khong_in_so(is_short, sl) -> None:
    dong = _tin(is_short=is_short, sl=sl).splitlines()
    assert dong[2].startswith("⚠️ Cắt lỗ") and "SAI phía" in dong[2]
    assert CHUA_DO in dong[3] and "USDT =" not in dong[3]
