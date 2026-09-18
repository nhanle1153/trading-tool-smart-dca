"""TD-0306 — đời sống THẬT của mã, giải `MT-59`.

`TD-0230` suy "mã còn sống" từ SỰ CÓ MẶT file nến tháng, mà kho vẫn sinh nến
`volume = 0` nhiều tháng sau khi sàn ngừng giao dịch. Các ca dưới dựng nến 1h giả
đúng hình đó (MKR ngừng thật 2025-09-08 08:00, kho vẫn có tới 2026-08) và khoá
rằng đời sống được đo từ nến CÓ GIAO DỊCH, không từ nến có mặt.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from tool_d.data.doi_song_ma import (
    CHET_TRONG_T2_T3,
    CHET_TRUOC_T2,
    KHONG_DO_DUOC,
    NGUON_CAN_TREN,
    NGUON_DO_THAT,
    SONG_TOI_HET_KHO,
    SONG_TOI_T3,
    KetQuaDoiSong,
    MauThuanNguonError,
    doi_chieu_exchange_info,
    khoang_ton_tai_moi,
    nghi_merge,
    phan_loai_doi_song,
)
from tool_d.data.pool_t1_du_lieu import DuLieuRoError

T2 = date(2026, 1, 29)
T3 = date(2026, 9, 6)
HET_KHO = date(2026, 9, 1)  # kho tháng tới hết 08/2026


def _nen(tu: str, den: str, ngung: str | None) -> pd.DataFrame:
    """Nến 1h `[tu, den)`; `volume > 0` tới và gồm `ngung`, sau đó `0` (nến giá thanh toán)."""
    d = pd.date_range(tu, den, freq="1h", inclusive="left", tz="UTC")
    vol = [1.0] * len(d) if ngung is None else [1.0 if t <= pd.Timestamp(ngung, tz="UTC") else 0.0 for t in d]
    return pd.DataFrame({"date": d, "volume": vol})


class TestPhanLoaiDoiSong:
    def test_ma_kieu_mkr_chet_truoc_t2_du_kho_con_nen_toi_thang_8(self) -> None:
        """Đúng hình MT-59: kho có nến tới 2026-08 nhưng volume = 0 từ 2025-09-08."""
        kq = phan_loai_doi_song(_nen("2025-08-01", "2026-09-01", "2025-09-08 08:00"), t2=T2, t3=T3, het_kho=HET_KHO)
        assert kq.trang_thai == CHET_TRUOC_T2
        assert kq.moc_ngung == pd.Timestamp("2025-09-08 08:00", tz="UTC")

    def test_ma_chet_giua_giai_doan_lockbox(self) -> None:
        kq = phan_loai_doi_song(_nen("2026-01-01", "2026-09-01", "2026-05-10 13:00"), t2=T2, t3=T3, het_kho=HET_KHO)
        assert kq.trang_thai == CHET_TRONG_T2_T3
        assert kq.moc_ngung == pd.Timestamp("2026-05-10 13:00", tz="UTC")

    def test_song_toi_het_kho_KHONG_bi_bao_la_ngung_ngay_cuoi_kho(self) -> None:
        """🔴 Bẫy chính: mốc cắt phải là min(T3, hết kho), không phải T3.

        Cắt ở T3 thì nến cuối 31/08 23:00 < T3 − 1h ⇒ bị báo "ngừng 31/08" chỉ vì
        kho không có tháng 9.
        """
        kq = phan_loai_doi_song(_nen("2026-07-01", "2026-09-01", None), t2=T2, t3=T3, het_kho=HET_KHO)
        assert kq.trang_thai == SONG_TOI_HET_KHO
        assert kq.moc_ngung is None

    def test_duoi_volume_0_ngan_o_cuoi_kho_KHONG_phai_ngung(self) -> None:
        """`DR-D1-03` §5: đuôi < 24 nến volume 0 là giờ vắng lệnh, không phải nến chết."""
        nen = _nen("2026-07-01", "2026-09-01", "2026-08-31 20:00")  # 3 giờ cuối volume 0
        kq = phan_loai_doi_song(nen, t2=T2, t3=T3, het_kho=HET_KHO)
        assert kq.trang_thai == SONG_TOI_HET_KHO
        assert kq.moc_ngung is None

    def test_kho_phu_qua_t3_thi_song_toi_t3(self) -> None:
        kq = phan_loai_doi_song(_nen("2026-08-01", "2026-09-07", None), t2=T2, t3=T3, het_kho=date(2026, 9, 7))
        assert kq.trang_thai == SONG_TOI_T3

    def test_khong_nen_nao_co_giao_dich_thi_raise_khong_doan(self) -> None:
        nen = _nen("2026-01-01", "2026-02-01", None).assign(volume=0.0)
        with pytest.raises(DuLieuRoError):
            phan_loai_doi_song(nen, t2=T2, t3=T3, het_kho=HET_KHO)


class TestDoiChieuExchangeInfo:
    @pytest.mark.parametrize("tt", [CHET_TRUOC_T2, CHET_TRONG_T2_T3])
    def test_kho_noi_chet_ma_hom_nay_van_giao_dich_thi_DUNG(self, tt: str) -> None:
        kq = KetQuaDoiSong(tt, pd.Timestamp("2025-09-08", tz="UTC"))
        with pytest.raises(MauThuanNguonError):
            doi_chieu_exchange_info(kq, dang_giao_dich_hom_nay=True, symbol="XUSDT")

    def test_song_toi_het_kho_va_hom_nay_giao_dich_thi_song_toi_t3(self) -> None:
        kq = KetQuaDoiSong(SONG_TOI_HET_KHO, None)
        assert doi_chieu_exchange_info(kq, dang_giao_dich_hom_nay=True, symbol="X") == SONG_TOI_T3

    def test_song_toi_het_kho_ma_hom_nay_khong_giao_dich_thi_KHONG_doan(self) -> None:
        """Chết sau hết kho, không biết trước hay sau T3 ⇒ không đo được (N6), không phải 'sống'."""
        kq = KetQuaDoiSong(SONG_TOI_HET_KHO, None)
        assert doi_chieu_exchange_info(kq, dang_giao_dich_hom_nay=False, symbol="X") == KHONG_DO_DUOC

    def test_chet_that_va_hom_nay_khong_giao_dich_giu_nguyen(self) -> None:
        kq = KetQuaDoiSong(CHET_TRONG_T2_T3, pd.Timestamp("2026-05-10", tz="UTC"))
        assert doi_chieu_exchange_info(kq, dang_giao_dich_hom_nay=False, symbol="X") == CHET_TRONG_T2_T3


class TestKhoangTonTaiMoi:
    CU = {
        "MKRUSDT": {"symbol": "MKRUSDT", "thang_dau": "2019-11", "thang_cuoi": "2026-08", "so_khoa": 164},
        "BTCUSDT": {"symbol": "BTCUSDT", "thang_dau": "2019-09", "thang_cuoi": "2026-08", "so_khoa": 168},
        "CHUADO": {"symbol": "CHUADO", "thang_dau": "2024-01", "thang_cuoi": "2026-08", "so_khoa": 64},
    }

    def _ra(self) -> dict:
        return khoang_ton_tai_moi(
            self.CU,
            {
                "MKRUSDT": (CHET_TRUOC_T2, pd.Timestamp("2025-09-08 08:00", tz="UTC")),
                "BTCUSDT": (SONG_TOI_T3, None),
            },
        )

    def test_thang_cuoi_do_tu_nen_co_giao_dich_KHONG_tu_file_co_mat(self) -> None:
        """Ca bắt MT-59: `thang_cuoi` phải về tháng ngừng thật, không giữ 2026-08 của kho."""
        ra = self._ra()
        assert ra["MKRUSDT"]["thang_cuoi"] == "2025-09"
        assert ra["MKRUSDT"]["thang_cuoi"] != self.CU["MKRUSDT"]["thang_cuoi"]
        assert ra["MKRUSDT"]["moc_ngung"] == "2025-09-08T08:00:00+00:00"
        assert ra["MKRUSDT"]["nguon_thang_cuoi"] == NGUON_DO_THAT

    def test_ma_chua_do_giu_so_cu_va_KHAI_la_can_tren(self) -> None:
        ra = self._ra()
        assert ra["CHUADO"]["thang_cuoi"] == "2026-08"
        assert ra["CHUADO"]["nguon_thang_cuoi"] == NGUON_CAN_TREN

    def test_giu_schema_td0230_de_drop_in(self) -> None:
        """`dung_ro_tai_moc()` đọc `thang_dau`/`thang_cuoi` — mọi mục phải còn đủ hai khoá."""
        for muc in self._ra().values():
            assert muc["thang_dau"] and muc["thang_cuoi"]
        assert set(self._ra()) == set(self.CU)

    def test_khong_sua_dict_dau_vao(self) -> None:
        self._ra()
        assert self.CU["MKRUSDT"]["thang_cuoi"] == "2026-08"


def test_nghi_merge_la_cac_ma_ngung_cung_gio() -> None:
    g = pd.Timestamp("2024-06-25 09:00", tz="UTC")
    ra = nghi_merge({"AGIXUSDT": g, "OCEANUSDT": g, "XUSDT": pd.Timestamp("2025-01-01", tz="UTC")})
    assert ra == {"AGIXUSDT": ["OCEANUSDT"], "OCEANUSDT": ["AGIXUSDT"]}
