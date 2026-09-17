"""TD-0247 (`DR-D1-03` §4) — `tool_d.data.pool_t1_du_lieu`: sao chép, nhập kho, cắt T2, kiểm đủ rổ."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from tool_d.api_client.binance_public import NenThangKhongCoError
from tool_d.data.pool_t1_du_lieu import (
    SAU_LOAI_FILE,
    DuLieuRoError,
    cac_thang,
    cat_den_moc,
    kiem_du_lieu_ro,
    nhap_ma_tu_kho,
    sao_chep_ma_co_san,
    ten_file,
)

MOC = {"t0": date(2024, 4, 9), "t1": date(2025, 6, 12), "t2": date(2026, 1, 29)}


def _df_nen(tu: str, den: str, tan_so: str) -> pd.DataFrame:
    d = pd.date_range(tu, den, freq=tan_so, tz="UTC")
    df = pd.DataFrame({"date": d, "open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 3.0})
    df["date"] = df["date"].astype("datetime64[ms, UTC]")
    return df


def test_ten_file_dung_quy_uoc_freqtrade() -> None:
    assert ten_file("1000PEPEUSDT", SAU_LOAI_FILE[0]) == "1000PEPE_USDT_USDT-1h-futures.feather"
    assert ten_file("MKRUSDT", SAU_LOAI_FILE[5]) == "MKR_USDT_USDT-1h-funding_rate.feather"
    with pytest.raises(DuLieuRoError):
        ten_file("MKRBTC", SAU_LOAI_FILE[0])


def test_cac_thang_qua_nam() -> None:
    assert cac_thang((2025, 11), (2026, 1)) == [(2025, 11), (2025, 12), (2026, 1)]


class TestSaoChep:
    def _tao_nguon(self, thu_muc: Path, ma: str) -> None:
        thu_muc.mkdir(parents=True, exist_ok=True)
        for lf in SAU_LOAI_FILE:
            (thu_muc / ten_file(ma, lf)).write_bytes(f"{ma}-{lf.khung}-{lf.hau_to}".encode())

    def test_chep_nguyen_byte_du_6_file(self, tmp_path: Path) -> None:
        self._tao_nguon(tmp_path / "nguon", "AUSDT")
        ra = sao_chep_ma_co_san(tmp_path / "nguon", tmp_path / "dich", ["AUSDT"])
        assert len(ra) == 6
        for lf in SAU_LOAI_FILE:
            f = ten_file("AUSDT", lf)
            assert (tmp_path / "dich" / f).read_bytes() == (tmp_path / "nguon" / f).read_bytes()

    def test_thieu_file_nguon_thi_KHONG_chep_gi(self, tmp_path: Path) -> None:
        self._tao_nguon(tmp_path / "nguon", "AUSDT")
        (tmp_path / "nguon" / ten_file("AUSDT", SAU_LOAI_FILE[3])).unlink()
        with pytest.raises(DuLieuRoError):
            sao_chep_ma_co_san(tmp_path / "nguon", tmp_path / "dich", ["AUSDT"])
        assert not (tmp_path / "dich").exists()

    def test_file_dich_da_co_thi_TU_CHOI_ghi_de(self, tmp_path: Path) -> None:
        self._tao_nguon(tmp_path / "nguon", "AUSDT")
        dich = tmp_path / "dich"
        dich.mkdir()
        (dich / ten_file("AUSDT", SAU_LOAI_FILE[0])).write_bytes(b"cu")
        with pytest.raises(DuLieuRoError):
            sao_chep_ma_co_san(tmp_path / "nguon", dich, ["AUSDT"])
        assert (dich / ten_file("AUSDT", SAU_LOAI_FILE[0])).read_bytes() == b"cu"


def _csv_gia(so_404: set[tuple[str, int, int]] | None = None):
    """Kho giả: mỗi tháng trả đúng 1 nến/1 funding tại ngày 15 của tháng."""
    so_404 = so_404 or set()
    goi: list[tuple] = []

    def doc(*, loai: str, symbol: str, nam: int, thang: int, khung: str | None) -> list[list[str]]:
        goi.append((loai, khung, nam, thang))
        if (loai, nam, thang) in so_404:
            raise NenThangKhongCoError("404")
        ms = str(int(pd.Timestamp(nam, thang, 15, tz="UTC").timestamp() * 1000))
        if loai == "fundingRate":
            return [[ms, "8", "0.0001"]]
        return [[ms, "1", "2", "0.5", "1.5", "3", "0", "9", "1", "0", "0", "0"]]

    return doc, goi


class TestNhapKho:
    def test_ma_huy_niem_yet_giua_wfo_du_6_file_trong_khoang(self, tmp_path: Path) -> None:
        doc, goi = _csv_gia()
        kq = nhap_ma_tu_kho(
            "MKRUSDT", dich=tmp_path, khoang={"thang_dau": "2023-01", "thang_cuoi": "2025-09"}, moc=MOC, doc_csv=doc
        )
        assert len(kq) == 6
        # 1h futures: tháng 2024-04 … 2025-09 = 18 tháng; nến ngày 15/04/2024 ≥ T0 nên giữ.
        assert kq["MKR_USDT_USDT-1h-futures.feather"] == 18
        # 5m: từ T1 (06/2025): tháng 6 nến ngày 15 ≥ 12/06 ⇒ giữ; 6..9 = 4 tháng.
        assert kq["MKR_USDT_USDT-5m-futures.feather"] == 4
        assert not any(t[2:] > (2025, 9) for t in goi)
        f = pd.read_feather(tmp_path / "MKR_USDT_USDT-1h-mark.feather")
        assert (f["volume"] == 0.0).all()

    def test_thang_thieu_GIUA_khoang_ton_tai_thi_TU_CHOI_va_KHONG_ghi_file_nao(self, tmp_path: Path) -> None:
        doc, _ = _csv_gia(so_404={("markPriceKlines", 2024, 8)})
        with pytest.raises(DuLieuRoError):
            nhap_ma_tu_kho(
                "MKRUSDT", dich=tmp_path, khoang={"thang_dau": "2023-01", "thang_cuoi": "2025-09"}, moc=MOC, doc_csv=doc
            )
        assert list(tmp_path.glob("*.feather")) == []

    def test_file_dich_da_co_thi_TU_CHOI(self, tmp_path: Path) -> None:
        doc, _ = _csv_gia()
        (tmp_path / "MKR_USDT_USDT-4h-futures.feather").write_bytes(b"cu")
        with pytest.raises(DuLieuRoError):
            nhap_ma_tu_kho(
                "MKRUSDT", dich=tmp_path, khoang={"thang_dau": "2023-01", "thang_cuoi": "2025-09"}, moc=MOC, doc_csv=doc
            )

    def test_khong_tai_thang_sau_T2_du_ma_con_song(self, tmp_path: Path) -> None:
        doc, goi = _csv_gia()
        nhap_ma_tu_kho("AUSDT", dich=tmp_path, khoang={"thang_dau": "2023-01", "thang_cuoi": "2026-08"}, moc=MOC, doc_csv=doc)
        assert max(t[2:] for t in goi) == (2026, 1)


class TestCatDenMoc:
    def test_bo_nen_sau_T2_giu_nen_T2(self, tmp_path: Path) -> None:
        _df_nen("2026-01-28", "2026-01-30", "12h").to_feather(tmp_path / "A_USDT_USDT-1h-futures.feather")
        kq = cat_den_moc(tmp_path, date(2026, 1, 29))
        df = pd.read_feather(tmp_path / "A_USDT_USDT-1h-futures.feather")
        assert df["date"].max() == pd.Timestamp("2026-01-29", tz="UTC")
        assert kq == {"A_USDT_USDT-1h-futures.feather": 2}

    def test_file_da_dung_khong_bi_ghi_lai(self, tmp_path: Path) -> None:
        f = tmp_path / "A_USDT_USDT-1h-futures.feather"
        _df_nen("2026-01-27", "2026-01-29", "12h").to_feather(f)
        truoc = f.read_bytes()
        assert cat_den_moc(tmp_path, date(2026, 1, 29)) == {}
        assert f.read_bytes() == truoc


class TestKiemDuLieuRo:
    def _ghi_du(self, thu_muc: Path, ma: str, tu: str = "2024-04-09", den: str = "2026-01-29") -> None:
        thu_muc.mkdir(parents=True, exist_ok=True)
        for lf in SAU_LOAI_FILE:
            bat_dau = "2025-06-12" if lf.tu_moc == "t1" and tu < "2025-06-12" else tu
            _df_nen(bat_dau, den, "1D").to_feather(thu_muc / ten_file(ma, lf))

    def test_ro_du_thi_khong_loi(self, tmp_path: Path) -> None:
        self._ghi_du(tmp_path, "AUSDT")
        assert kiem_du_lieu_ro(tmp_path, ["AUSDT"], {"AUSDT": {"thang_dau": "2023-01", "thang_cuoi": "2026-08"}}, MOC) == []

    def test_thieu_file_va_lan_T2_va_ket_thuc_som_deu_bao(self, tmp_path: Path) -> None:
        self._ghi_du(tmp_path, "AUSDT", den="2026-01-31")  # lấn T2
        self._ghi_du(tmp_path, "BUSDT", den="2025-12-01")  # còn sống mà dừng sớm
        (tmp_path / ten_file("BUSDT", SAU_LOAI_FILE[4])).unlink()  # thiếu mark
        khoang = {s: {"thang_dau": "2023-01", "thang_cuoi": "2026-08"} for s in ("AUSDT", "BUSDT", "CUSDT")}
        loi = kiem_du_lieu_ro(tmp_path, ["AUSDT", "BUSDT", "CUSDT"], khoang, MOC)
        assert any(x.startswith("A_USDT_USDT") and "sau T2" in x for x in loi)
        assert any(x.startswith("B_USDT_USDT") and "sớm hơn T2" in x for x in loi)
        assert "B_USDT_USDT-1h-mark.feather: THIẾU" in loi
        assert sum(x.startswith("C_USDT_USDT") and "THIẾU" in x for x in loi) == 6

    def test_ma_huy_niem_yet_ket_thuc_trong_thang_huy_la_hop_le(self, tmp_path: Path) -> None:
        self._ghi_du(tmp_path, "MKRUSDT", den="2025-09-20")
        khoang = {"MKRUSDT": {"thang_dau": "2023-01", "thang_cuoi": "2025-09"}}
        assert kiem_du_lieu_ro(tmp_path, ["MKRUSDT"], khoang, MOC) == []

    def test_bat_dau_muon_bi_bao(self, tmp_path: Path) -> None:
        self._ghi_du(tmp_path, "AUSDT", tu="2024-09-01")
        loi = kiem_du_lieu_ro(tmp_path, ["AUSDT"], {"AUSDT": {"thang_dau": "2023-01", "thang_cuoi": "2026-08"}}, MOC)
        assert any("muộn hơn cần" in x for x in loi)
