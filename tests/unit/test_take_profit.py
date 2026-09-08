"""TD-0189 — hành vi của tầng chốt lời §5.1 (`src/tool_d/take_profit.py`).

Test ĐƠN VỊ cho hàm thuần. Phần đo trên backtest THẬT thuộc chặng 2
(nối `custom_exit`), sau khi phiên sở hữu `ZoneAbsorption.py` commit —
bài học TD-0168: một hàm chỉ được canh bằng mẫu dựng tay là một hàm
chưa chắc nằm trên đường sản xuất.
"""

from __future__ import annotations

import math

import pytest

from tool_d.take_profit import (
    TP_SOURCE_NANG,
    TP_SOURCE_ZONE,
    TY_LE_CHOT_TP1,
    KeHoachChotLoi,
    TakeProfitError,
    ThamSoTP,
    chon_muc_tp1,
    khoang_r_eff,
    tp1_tu_zone,
    tp2_muc_trail,
    ty_le_dung_nang,
)

# Bộ tham số dùng chung: đúng bốn con số của spec §5.1.
THAM_SO = ThamSoTP(
    tp1_haircut_pct=20.0,
    tp2_trail_atr=1.5,
    tp_fallback_dist_r=4.0,
    tp_fallback_target_r=1.5,
)


class TestDoiDonVi:
    """🔴 Chỗ dễ sai nhất: `r_eff_plan` là TỈ LỆ, `R_eff` của §5.1 là KHOẢNG GIÁ."""

    def test_doi_ti_le_sang_khoang_gia(self) -> None:
        assert khoang_r_eff(p_avg=100.0, r_eff_plan=0.03) == pytest.approx(3.0)

    def test_khoang_ti_le_thuan_voi_gia(self) -> None:
        """Cùng một tỉ lệ trên giá gấp mười thì khoảng giá cũng gấp mười —
        phép nhân thẳng vào tỉ lệ sẽ cho cùng một số ở cả hai mức giá."""
        a = khoang_r_eff(p_avg=100.0, r_eff_plan=0.03)
        b = khoang_r_eff(p_avg=1000.0, r_eff_plan=0.03)
        assert b == pytest.approx(10 * a)

    @pytest.mark.parametrize("xau", [0.0, -1.0, float("nan")])
    def test_gia_khong_doc_duoc_thi_RAISE(self, xau: float) -> None:
        with pytest.raises(TakeProfitError):
            khoang_r_eff(p_avg=xau, r_eff_plan=0.03)

    @pytest.mark.parametrize("xau", [0.0, -0.01, float("nan")])
    def test_ti_le_khong_doc_duoc_thi_RAISE(self, xau: float) -> None:
        with pytest.raises(TakeProfitError):
            khoang_r_eff(p_avg=100.0, r_eff_plan=xau)


class TestTP1TuZone:
    def test_tru_hao_tren_KHOANG_CACH_khong_phai_tren_gia(self) -> None:
        """p_avg=100, zone=110 ⇒ quãng 10, trừ hao 20% ⇒ TP1 = 108.

        Cách đọc kia (trừ 20% GIÁ zone) cho 88 — DƯỚI giá vào lệnh, biến
        một lệnh thắng thành lệnh lỗ. Ghim con số để diễn giải không trôi.
        """
        assert tp1_tu_zone(
            p_avg=100.0, gia_zone_doi_dien=110.0, tp1_haircut_pct=20.0
        ) == pytest.approx(108.0)

    def test_tp1_luon_nam_giua_p_avg_va_zone(self) -> None:
        tp1 = tp1_tu_zone(p_avg=250.0, gia_zone_doi_dien=300.0, tp1_haircut_pct=20.0)
        assert 250.0 < tp1 < 300.0

    def test_haircut_0_thi_TP1_dung_bang_zone(self) -> None:
        assert tp1_tu_zone(
            p_avg=100.0, gia_zone_doi_dien=110.0, tp1_haircut_pct=0.0
        ) == pytest.approx(110.0)

    def test_zone_NAM_DUOI_p_avg_thi_RAISE(self) -> None:
        """Zone dưới giá vào lệnh là zone CÙNG CHIỀU. Trả một con số ở đây
        sẽ đặt mức chốt lời dưới giá vào lệnh mà không ai báo."""
        with pytest.raises(TakeProfitError, match="NẰM TRÊN"):
            tp1_tu_zone(p_avg=100.0, gia_zone_doi_dien=90.0, tp1_haircut_pct=20.0)

    @pytest.mark.parametrize("xau", [-1.0, 100.0, 120.0, float("nan")])
    def test_haircut_ngoai_khoang_thi_RAISE(self, xau: float) -> None:
        with pytest.raises(TakeProfitError):
            tp1_tu_zone(p_avg=100.0, gia_zone_doi_dien=110.0, tp1_haircut_pct=xau)


class TestChonMucTP1:
    """p_avg=100, r_eff_plan=0.02 ⇒ R_eff = 2.0 giá ⇒ trần tìm zone = 8.0."""

    def test_zone_TRONG_TAM_thi_dung_zone(self) -> None:
        kh = chon_muc_tp1(
            p_avg=100.0,
            r_eff_plan=0.02,
            gia_cac_zone_doi_dien=[105.0],
            tham_so=THAM_SO,
        )
        assert kh.tp_source == TP_SOURCE_ZONE
        assert not kh.dung_nang
        assert kh.tp1_gia == pytest.approx(104.0)  # 100 + 0.8 × 5
        assert kh.tran_tim_zone_gia == pytest.approx(8.0)

    def test_zone_QUA_XA_thi_dung_nang(self) -> None:
        kh = chon_muc_tp1(
            p_avg=100.0,
            r_eff_plan=0.02,
            gia_cac_zone_doi_dien=[130.0],
            tham_so=THAM_SO,
        )
        assert kh.tp_source == TP_SOURCE_NANG
        assert kh.dung_nang
        assert kh.tp1_gia == pytest.approx(103.0)  # 100 + 1.5 × 2.0

    def test_KHONG_co_zone_nao_thi_dung_nang(self) -> None:
        kh = chon_muc_tp1(
            p_avg=100.0, r_eff_plan=0.02, gia_cac_zone_doi_dien=[], tham_so=THAM_SO
        )
        assert kh.tp_source == TP_SOURCE_NANG

    def test_bien_DUNG_BANG_tran_van_tinh_la_trong_tam(self) -> None:
        """Spec loại bằng chữ *"> 4 × R_eff"* ⇒ bằng đúng thì KHÔNG loại.
        Cùng quy ước biên với DG4 (*"≤ 8 nến"*)."""
        kh = chon_muc_tp1(
            p_avg=100.0,
            r_eff_plan=0.02,
            gia_cac_zone_doi_dien=[108.0],
            tham_so=THAM_SO,
        )
        assert kh.tp_source == TP_SOURCE_ZONE

    def test_nhich_qua_bien_mot_chut_thi_sang_nang(self) -> None:
        kh = chon_muc_tp1(
            p_avg=100.0,
            r_eff_plan=0.02,
            gia_cac_zone_doi_dien=[108.001],
            tham_so=THAM_SO,
        )
        assert kh.tp_source == TP_SOURCE_NANG

    def test_chon_zone_GAN_NHAT_trong_nhieu_zone(self) -> None:
        kh = chon_muc_tp1(
            p_avg=100.0,
            r_eff_plan=0.02,
            gia_cac_zone_doi_dien=[107.0, 103.0, 106.0],
            tham_so=THAM_SO,
        )
        assert kh.tp1_gia == pytest.approx(102.4)  # 100 + 0.8 × 3

    def test_zone_duoi_p_avg_KHONG_duoc_chon_lam_TP(self) -> None:
        """Một zone dưới giá vào lệnh vẫn 'trong tầm' theo phép trừ, nhưng
        nó không phải zone đối diện — phải rơi sang nạng, không phải chọn nó."""
        kh = chon_muc_tp1(
            p_avg=100.0,
            r_eff_plan=0.02,
            gia_cac_zone_doi_dien=[95.0, 98.0],
            tham_so=THAM_SO,
        )
        assert kh.tp_source == TP_SOURCE_NANG

    def test_gia_zone_NaN_thi_RAISE_chu_khong_am_tham_dung_nang(self) -> None:
        """🔴 Bỏ qua lặng lẽ sẽ biến *không đo được* thành *không có zone*,
        tức tự chuyển sang nạng và làm chỉ số H-4 nói dối theo hướng an
        toàn giả. Cùng chốt với `TrancheGateError` của DG5 khi gặp NaN."""
        with pytest.raises(TakeProfitError, match="không đọc được"):
            chon_muc_tp1(
                p_avg=100.0,
                r_eff_plan=0.02,
                gia_cac_zone_doi_dien=[float("nan")],
                tham_so=THAM_SO,
            )

    def test_ty_le_chot_mac_dinh_la_mot_nua(self) -> None:
        kh = chon_muc_tp1(
            p_avg=100.0, r_eff_plan=0.02, gia_cac_zone_doi_dien=[105.0], tham_so=THAM_SO
        )
        assert kh.ty_le_chot_tp1 == TY_LE_CHOT_TP1 == 0.5

    def test_ke_hoach_BAT_BIEN(self) -> None:
        kh = chon_muc_tp1(
            p_avg=100.0, r_eff_plan=0.02, gia_cac_zone_doi_dien=[105.0], tham_so=THAM_SO
        )
        with pytest.raises(Exception):
            kh.tp1_gia = 1.0  # type: ignore[misc]
        assert isinstance(kh, KeHoachChotLoi)


class TestTP2Trail:
    def test_muc_trail_la_dinh_tru_boi_so_ATR(self) -> None:
        assert tp2_muc_trail(
            gia_cao_nhat_sau_tp1=110.0, atr_1h=2.0, tp2_trail_atr=1.5
        ) == pytest.approx(107.0)

    def test_ATR_khong_doc_duoc_thi_RAISE(self) -> None:
        with pytest.raises(TakeProfitError):
            tp2_muc_trail(
                gia_cao_nhat_sau_tp1=110.0, atr_1h=float("nan"), tp2_trail_atr=1.5
            )

    def test_ATR_qua_lon_lam_muc_trail_am_thi_RAISE(self) -> None:
        """Một mức thoát không dương là mức không bao giờ chạm — trả về
        lặng lẽ nghĩa là lệnh mất hẳn đường thoát theo TP2."""
        with pytest.raises(TakeProfitError, match="không dương"):
            tp2_muc_trail(gia_cao_nhat_sau_tp1=10.0, atr_1h=100.0, tp2_trail_atr=1.5)


class TestChiSoH4:
    def test_danh_sach_RONG_thi_RAISE_khong_tra_0(self) -> None:
        """🔴 N6: *chưa đo* KHÁC *đo được 0*. Và 0.0 lại đúng là con số
        ĐẠT đẹp nhất có thể cho H-4 — im lặng ở đây là im lặng có lợi."""
        with pytest.raises(TakeProfitError, match="pending"):
            ty_le_dung_nang([])

    def test_tinh_dung_ti_le(self) -> None:
        nguon = [TP_SOURCE_ZONE, TP_SOURCE_NANG, TP_SOURCE_ZONE, TP_SOURCE_NANG]
        assert ty_le_dung_nang(nguon) == pytest.approx(0.5)

    def test_toan_zone_thi_bang_khong(self) -> None:
        assert ty_le_dung_nang([TP_SOURCE_ZONE] * 3) == 0.0

    def test_nguon_la_thi_RAISE(self) -> None:
        with pytest.raises(TakeProfitError, match="lạ"):
            ty_le_dung_nang([TP_SOURCE_ZONE, "tp_bang_tay"])

    def test_nguong_H4_cua_spec_la_0_40(self) -> None:
        """Ghim quan hệ: 41% dùng nạng thì vượt ngưỡng L2 của §5.1."""
        nguon = [TP_SOURCE_NANG] * 41 + [TP_SOURCE_ZONE] * 59
        assert ty_le_dung_nang(nguon) > 0.40


class TestKhongCoNaNLotQua:
    def test_moi_duong_ra_deu_la_so_that(self) -> None:
        kh = chon_muc_tp1(
            p_avg=100.0, r_eff_plan=0.02, gia_cac_zone_doi_dien=[105.0], tham_so=THAM_SO
        )
        for ten, gia_tri in (
            ("tp1_gia", kh.tp1_gia),
            ("khoang_r_eff_gia", kh.khoang_r_eff_gia),
            ("tran_tim_zone_gia", kh.tran_tim_zone_gia),
        ):
            assert not math.isnan(gia_tri), ten
            assert gia_tri > 0, ten
