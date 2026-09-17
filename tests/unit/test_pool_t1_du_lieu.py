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
    duoi_nen_chet,
    kiem_du_lieu_ro,
    moc_ngung_giao_dich,
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


def _csv_gia(so_404: set[tuple[str, int, int]] | None = None, chet_tu: tuple[int, int] | None = None):
    """Kho giả: mỗi tháng trả đúng 1 nến/1 funding tại ngày 15 của tháng.

    `chet_tu=(nam, thang)`: từ tháng đó nến phẳng `volume = 0` và funding 404 — đúng hình
    dạng đo được ở MKR/FLM (`DR-D1-03` §5)."""
    so_404 = so_404 or set()
    goi: list[tuple] = []

    def doc(*, loai: str, symbol: str, nam: int, thang: int, khung: str | None) -> list[list[str]]:
        goi.append((loai, khung, nam, thang))
        chet = chet_tu is not None and (nam, thang) >= chet_tu
        if (loai, nam, thang) in so_404 or (chet and loai == "fundingRate"):
            raise NenThangKhongCoError("404")
        ms = str(int(pd.Timestamp(nam, thang, 15, tz="UTC").timestamp() * 1000))
        if loai == "fundingRate":
            return [[ms, "8", "0.0001"]]
        if chet:
            return [[ms, "7", "7", "7", "7", "0", "0", "0", "0", "0", "0", "0"]]
        return [[ms, "1", "2", "0.5", "1.5", "3", "0", "9", "1", "0", "0", "0"]]

    return doc, goi


class TestNhapKho:
    def test_ma_huy_niem_yet_giua_wfo_du_6_file_trong_khoang(self, tmp_path: Path) -> None:
        doc, goi = _csv_gia()
        kq = nhap_ma_tu_kho(
            "MKRUSDT", dich=tmp_path, khoang={"thang_dau": "2023-01", "thang_cuoi": "2025-09"}, moc=MOC, doc_csv=doc
        )
        assert len(kq.so_hang) == 6
        # 1h futures: tháng 2024-04 … 2025-09 = 18 tháng; nến ngày 15/04/2024 ≥ T0 nên giữ.
        assert kq.so_hang["MKR_USDT_USDT-1h-futures.feather"] == 18
        # 5m: từ T1 (06/2025): tháng 6 nến ngày 15 ≥ 12/06 ⇒ giữ; 6..9 = 4 tháng.
        assert kq.so_hang["MKR_USDT_USDT-5m-futures.feather"] == 4
        # Kho hết file sau 09/2025 ⇒ nến cuối có giao dịch 15/09/2025 < T2 ⇒ là mốc ngừng.
        assert kq.moc_ngung == pd.Timestamp("2025-09-15", tz="UTC")
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


class TestMocNgungGiaoDich:
    def test_nen_chet_sau_moc_bi_CAT_va_funding_404_sau_moc_KHONG_la_loi(self, tmp_path: Path) -> None:
        """Hình dạng MKR: nến vẫn có tới T2 nhưng phẳng volume 0 từ 10/2025, funding 404."""
        doc, goi = _csv_gia(chet_tu=(2025, 10))
        kq = nhap_ma_tu_kho(
            "MKRUSDT", dich=tmp_path, khoang={"thang_dau": "2023-01", "thang_cuoi": "2026-08"}, moc=MOC, doc_csv=doc
        )
        assert kq.moc_ngung == pd.Timestamp("2025-09-15", tz="UTC")
        assert kq.gia_dong_cuoi == 1.5  # nến giao dịch cuối, KHÔNG phải nến chết (7.0)
        for lf in SAU_LOAI_FILE:
            df = pd.read_feather(tmp_path / ten_file("MKRUSDT", lf))
            assert df["date"].max() <= kq.moc_ngung
        # Không tải funding/mark/4h/1d/5m của tháng sau tháng ngừng.
        assert not any(t[0] != "klines" and t[2:] > (2025, 9) for t in goi)
        assert not any(t[0] == "klines" and t[1] != "1h" and t[2:] > (2025, 9) for t in goi)

    def test_ma_con_song_toi_T2_khong_co_moc_ngung(self) -> None:
        df = _df_nen("2026-01-27", "2026-01-29", "1h")
        assert moc_ngung_giao_dich(df, MOC["t2"]) is None

    def test_khong_nen_nao_co_giao_dich_thi_TU_CHOI(self) -> None:
        df = _df_nen("2026-01-27", "2026-01-29", "1h").assign(volume=0.0)
        with pytest.raises(DuLieuRoError):
            moc_ngung_giao_dich(df, MOC["t2"])

    def test_dem_duoi_nen_chet(self) -> None:
        df = _df_nen("2026-01-01", "2026-01-03", "1h")
        df.loc[df.index[-30:], "volume"] = 0.0
        assert duoi_nen_chet(df) == 30


class TestKiemMocNgung:
    def _ghi(self, thu_muc: Path, ma: str, den: str, vol_cuoi_0: int = 0) -> None:
        thu_muc.mkdir(parents=True, exist_ok=True)
        for lf in SAU_LOAI_FILE:
            bat_dau = "2025-06-12" if lf.tu_moc == "t1" else "2024-04-09"
            df = _df_nen(bat_dau, den, "1h" if lf is SAU_LOAI_FILE[0] else "1D")
            if vol_cuoi_0:
                df.loc[df.index[-vol_cuoi_0:], "volume"] = 0.0
            df.to_feather(thu_muc / ten_file(ma, lf))

    def test_ma_da_khai_moc_ngung_ket_thuc_dung_moc_la_hop_le(self, tmp_path: Path) -> None:
        self._ghi(tmp_path, "MKRUSDT", den="2025-09-08 08:00")
        khoang = {"MKRUSDT": {"thang_dau": "2023-01", "thang_cuoi": "2026-08"}}
        moc_ngung = {"MKRUSDT": pd.Timestamp("2025-09-08 08:00", tz="UTC")}
        assert kiem_du_lieu_ro(tmp_path, ["MKRUSDT"], khoang, MOC, moc_ngung) == []

    def test_ma_ket_thuc_som_KHONG_khai_thi_bao(self, tmp_path: Path) -> None:
        self._ghi(tmp_path, "MKRUSDT", den="2025-09-08 08:00")
        khoang = {"MKRUSDT": {"thang_dau": "2023-01", "thang_cuoi": "2026-08"}}
        loi = kiem_du_lieu_ro(tmp_path, ["MKRUSDT"], khoang, MOC)
        assert any("sớm hơn T2" in x for x in loi)

    def test_duoi_nen_chet_chua_khai_thi_bao_du_ket_thuc_dung_T2(self, tmp_path: Path) -> None:
        self._ghi(tmp_path, "AUSDT", den="2026-01-29", vol_cuoi_0=48)
        khoang = {"AUSDT": {"thang_dau": "2023-01", "thang_cuoi": "2026-08"}}
        loi = kiem_du_lieu_ro(tmp_path, ["AUSDT"], khoang, MOC)
        assert any("nến chết chưa khai" in x for x in loi)


# ─── TD-0301 (DR-D1-05) — rổ T0, mốc cuối T1. TD-0252 (§3b.1): thêm 5m tính từ T0 ───


class TestRoT0:
    def test_nhap_kho_t0_co_5m_tu_T0_va_cat_tai_T1(self, tmp_path: Path) -> None:
        """TD-0252 đảo vế của ca cũ (`…khong_5m`, len == 5): rổ T0 nay SÁU loại, và 5m tính từ
        `T0` chứ không phải `T1` — đó mới là bất biến bị lật."""
        from tool_d.data.pool_t1_du_lieu import SAU_LOAI_FILE_T0

        doc, goi = _csv_gia()
        kq = nhap_ma_tu_kho(
            "AUSDT", dich=tmp_path, khoang={"thang_dau": "2023-01", "thang_cuoi": "2026-08"}, moc=MOC,
            doc_csv=doc, loai_file=SAU_LOAI_FILE_T0, moc_cuoi="t1",
        )
        assert len(kq.so_hang) == 6 and any("5m" in k for k in kq.so_hang)
        assert max(t[2:] for t in goi) == (2025, 6)  # không tải tháng sau T1
        # 5m phải được tải từ THÁNG CỦA T0 (2024-04), không phải từ T1 — vế này là TD-0252.
        thang_5m = [t[2:] for t in goi if t[1] == "5m"]
        assert min(thang_5m) == (2024, 4)
        for lf in SAU_LOAI_FILE_T0:
            assert pd.read_feather(tmp_path / ten_file("AUSDT", lf))["date"].max() <= pd.Timestamp("2025-06-12", tz="UTC")
        # Kho giả chỉ có 1 nến/tháng (ngày 15) nên nến cuối ≤ T1 là 15/05 ⇒ bị coi là mốc ngừng; mã thật
        # có nến tới sát T1. Ca này chỉ khoá: 6 loại file, 5m từ T0, không tháng sau T1, không nến sau T1.

    def test_ke_hoach_nam_loai_cu_van_dung_duoc(self, tmp_path: Path) -> None:
        """Giữ ca cũ dưới dạng khẳng định về `NAM_LOAI_FILE_T0` — hằng đó vẫn mô tả 715 file mà
        TD-0301 đã đặt trên đĩa, và vẫn là đầu vào để tính "còn thiếu những loại nào"."""
        from tool_d.data.pool_t1_du_lieu import NAM_LOAI_FILE_T0

        doc, _ = _csv_gia()
        kq = nhap_ma_tu_kho(
            "AUSDT", dich=tmp_path, khoang={"thang_dau": "2023-01", "thang_cuoi": "2026-08"}, moc=MOC,
            doc_csv=doc, loai_file=NAM_LOAI_FILE_T0, moc_cuoi="t1",
        )
        assert len(kq.so_hang) == 5 and not any("5m" in k for k in kq.so_hang)

    def test_ke_hoach_khong_bat_dau_bang_1h_futures_thi_tu_choi(self, tmp_path: Path) -> None:
        from tool_d.data.pool_t1_du_lieu import NAM_LOAI_FILE_T0

        doc, _ = _csv_gia()
        with pytest.raises(DuLieuRoError):
            nhap_ma_tu_kho(
                "AUSDT", dich=tmp_path, khoang={"thang_dau": "2023-01", "thang_cuoi": "2026-08"}, moc=MOC,
                doc_csv=doc, loai_file=tuple(reversed(NAM_LOAI_FILE_T0)), moc_cuoi="t1",
            )

    def test_kiem_t0_lan_T1_bao_loi_va_DOI_5m(self, tmp_path: Path) -> None:
        """TD-0252 đảo vế cũ (`not any("5m" in x …)`): kế hoạch rổ T0 nay ĐÒI 5m, nên thiếu nó
        phải thành một dòng lỗi."""
        from tool_d.data.pool_t1_du_lieu import NAM_LOAI_FILE_T0, SAU_LOAI_FILE_T0

        for lf in NAM_LOAI_FILE_T0:  # cố ý ghi 5 loại cũ, CHƯA có 5m
            _df_nen("2024-04-09", "2025-06-14", "1D").to_feather(tmp_path / ten_file("AUSDT", lf))
        khoang = {"AUSDT": {"thang_dau": "2023-01", "thang_cuoi": "2026-08"}}
        loi = kiem_du_lieu_ro(tmp_path, ["AUSDT"], khoang, MOC, loai_file=SAU_LOAI_FILE_T0, moc_cuoi="t1")
        assert any("sau T1" in x for x in loi)
        assert any("5m" in x and "THIẾU" in x for x in loi)
        cat_den_moc(tmp_path, MOC["t1"])
        # Bổ sung nốt 5m ⇒ sạch.
        _df_nen("2024-04-09", "2025-06-11", "1D").to_feather(
            tmp_path / ten_file("AUSDT", SAU_LOAI_FILE_T0[-1])
        )
        assert kiem_du_lieu_ro(tmp_path, ["AUSDT"], khoang, MOC, loai_file=SAU_LOAI_FILE_T0, moc_cuoi="t1") == []

    def test_kiem_t0_bat_5m_bat_dau_tai_T1_la_THIEU_DAU(self, tmp_path: Path) -> None:
        """🔴 Ca VÀNG — hình dạng THẬT của 65/66 file 5m đang nằm trên đĩa: chúng bắt đầu đúng
        tại `T1`. Chép nguyên vào rổ T0 rồi cắt `≤ T1` còn đúng một nến, mà file một nến KHÔNG
        rỗng nên `cat_den_moc()` không raise. Chốt duy nhất bắt được là phép kiểm "bắt đầu muộn
        hơn cần", và nó chỉ chạy khi 5m mang `tu_moc = "t0"` (DR-D1-05 §3b.2)."""
        from tool_d.data.pool_t1_du_lieu import NAM_LOAI_FILE_T0, SAU_LOAI_FILE_T0

        for lf in NAM_LOAI_FILE_T0:
            _df_nen("2024-04-09", "2025-06-11", "1D").to_feather(tmp_path / ten_file("AUSDT", lf))
        # 5m "chép nhầm từ rổ T1": bắt đầu đúng tại T1.
        _df_nen("2025-06-12", "2025-06-12", "1D").to_feather(
            tmp_path / ten_file("AUSDT", SAU_LOAI_FILE_T0[-1])
        )
        khoang = {"AUSDT": {"thang_dau": "2023-01", "thang_cuoi": "2026-08"}}
        loi = kiem_du_lieu_ro(tmp_path, ["AUSDT"], khoang, MOC, loai_file=SAU_LOAI_FILE_T0, moc_cuoi="t1")
        assert any("5m" in x and "muộn hơn cần" in x for x in loi)
        assert not any("5m" in x and "THIẾU" in x for x in loi)  # file CÓ, chỉ là thiếu phần đầu
