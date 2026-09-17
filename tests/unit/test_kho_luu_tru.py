"""TD-0247 (`DR-D1-03` §4) — `tool_d.data.kho_luu_tru`: CSV tháng của kho → định dạng Freqtrade.

Khớp với dữ liệu Freqtrade THẬT đã đo bằng đối chiếu (AAVE, `docs/du-lieu-do/`);
ở đây khoá các quy tắc chuyển đổi để chúng không trôi.
"""

from __future__ import annotations

import pandas as pd
import pytest

from tool_d.data.kho_luu_tru import (
    COT_FUNDING,
    COT_NEN,
    DuLieuKhoError,
    doi_chieu_voi_freqtrade,
    funding_tu_kho,
    nen_tu_kho,
)

MOC_MS = "1714521600000"  # 2024-05-01 00:00 UTC
MOC_US = "1756684800000000"  # 2025-09-01 00:00 UTC, micro-giây


def _nen(moc: str, gia: float = 10.0, vol: float = 5.0) -> list[str]:
    return [moc, str(gia), str(gia + 1), str(gia - 1), str(gia + 0.5), str(vol), "0", "999", "1", "0", "0", "0"]


class TestNen:
    def test_dinh_dang_dung_cot_va_kieu(self) -> None:
        df = nen_tu_kho([_nen(MOC_MS)], la_mark=False)
        assert list(df.columns) == COT_NEN
        assert str(df["date"].dtype) == "datetime64[ms, UTC]"
        assert df.iloc[0]["date"] == pd.Timestamp("2024-05-01", tz="UTC")
        assert df.iloc[0]["volume"] == 5.0  # cột 5 = khối lượng tài sản cơ sở, KHÔNG phải quote (cột 7)

    def test_mark_volume_bang_0(self) -> None:
        assert nen_tu_kho([_nen(MOC_MS, vol=77.0)], la_mark=True).iloc[0]["volume"] == 0.0

    def test_moc_micro_giay_khong_roi_ve_1970(self) -> None:
        assert nen_tu_kho([_nen(MOC_US)], la_mark=False).iloc[0]["date"] == pd.Timestamp("2025-09-01", tz="UTC")

    def test_trung_moc_cung_gia_tri_thi_gop(self) -> None:
        assert len(nen_tu_kho([_nen(MOC_MS), _nen(MOC_MS)], la_mark=False)) == 1

    def test_trung_moc_KHAC_gia_tri_thi_TU_CHOI(self) -> None:
        with pytest.raises(DuLieuKhoError):
            nen_tu_kho([_nen(MOC_MS, gia=10.0), _nen(MOC_MS, gia=11.0)], la_mark=False)

    def test_hang_thieu_cot_thi_TU_CHOI(self) -> None:
        with pytest.raises(DuLieuKhoError):
            nen_tu_kho([[MOC_MS, "1", "2"]], la_mark=False)

    def test_0_hang_thi_TU_CHOI(self) -> None:
        with pytest.raises(DuLieuKhoError):
            nen_tu_kho([], la_mark=False)


class TestFunding:
    def test_lam_tron_xuong_gio_jitter_mili_giay(self) -> None:
        """Đo thật: kho ghi `1714665600002`, Freqtrade ghi tròn giờ."""
        df = funding_tu_kho([["1714665600002", "8", "0.00003613"]])
        assert list(df.columns) == COT_FUNDING
        assert df.iloc[0]["date"] == pd.Timestamp("2024-05-02 16:00", tz="UTC")
        assert df.iloc[0]["funding_rate"] == pytest.approx(0.00003613)

    def test_lech_tu_60_giay_thi_KHONG_lam_tron(self) -> None:
        with pytest.raises(DuLieuKhoError):
            funding_tu_kho([[str(1714665600000 + 60_000), "8", "0.0001"]])

    def test_duoi_60_giay_van_lam_tron(self) -> None:
        df = funding_tu_kho([[str(1714665600000 + 59_999), "8", "0.0001"]])
        assert df.iloc[0]["date"] == pd.Timestamp("2024-05-02 16:00", tz="UTC")


def test_doi_chieu_dem_dung_lech_va_moc_mot_ben() -> None:
    a = nen_tu_kho([_nen(MOC_MS, gia=10.0), _nen("1714525200000", gia=10.0)], la_mark=False)
    b = a.copy()
    b.loc[0, "close"] = 99.0
    b = b.iloc[[0]]
    kq = doi_chieu_voi_freqtrade(a, b)
    assert kq["chung"] == 1 and kq["chi_kho"] == 1 and kq["chi_freqtrade"] == 0
    assert kq["lech_theo_cot"]["close"] == 1 and kq["lech_theo_cot"]["open"] == 0
