"""TD-0252 (`DR-D1-05` §3b) — 5m cho CALIB `[T0,T1]` trên rổ `T0`.

Khoá bốn thứ mà lượt nhập 143 mã dựa vào:

  1. rổ `T1` KHÔNG bị kéo theo (5m của nó vẫn tính từ `T1`) — nếu vỡ, 107 mã phải tải lại;
  2. `nhap_them_loai_file()` fail-closed và KHÔNG tự đo lại mốc ngừng giao dịch;
  3. `kiem_du_lieu_ro()` không đếm đuôi nến chết trên khung 5m khi kế hoạch đã lọc;
  4. phép đo độ phủ nhìn đúng thứ `backtesting.py:1739` hỏi.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from tool_d.api_client.binance_public import NenThangKhongCoError
from tool_d.data.do_phu_chi_tiet import (
    KHONG_CO_KHUNG_CHI_TIET,
    THUNG_GIUA_CHUOI,
    cho_thieu_khung_chi_tiet,
    tom_tat_theo_ma,
)
from tool_d.data.pool_t1_du_lieu import (
    NEN_CHET_TOI_THIEU,
    LOAI_5M_T0,
    NAM_LOAI_FILE_T0,
    SAU_LOAI_FILE,
    SAU_LOAI_FILE_T0,
    DuLieuRoError,
    duoi_nen_chet,
    kiem_du_lieu_ro,
    kiem_pham_vi_dataset,
    nhap_them_loai_file,
    ten_file,
)
from tool_d.ledger.timerange import DatasetBoundary

MOC = {"t0": date(2024, 4, 9), "t1": date(2025, 6, 12), "t2": date(2026, 1, 29)}
KHOANG = {"thang_dau": "2023-01", "thang_cuoi": "2026-08"}


def _df(tu: str, den: str, tan_so: str, volume: float = 3.0) -> pd.DataFrame:
    d = pd.date_range(tu, den, freq=tan_so, tz="UTC")
    df = pd.DataFrame({"date": d, "open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": volume})
    df["date"] = df["date"].astype("datetime64[ms, UTC]")
    return df


def _kho_gia(so_404: set[tuple[int, int]] | None = None):
    """Kho giả: mỗi tháng một nến tại ngày 15. Trả (doc_csv, danh sách lời gọi)."""
    so_404 = so_404 or set()
    goi: list[tuple] = []

    def doc(*, loai: str, symbol: str, nam: int, thang: int, khung: str | None) -> list[list[str]]:
        goi.append((loai, khung, nam, thang))
        if (nam, thang) in so_404:
            raise NenThangKhongCoError("404")
        ms = str(int(pd.Timestamp(nam, thang, 15, tz="UTC").timestamp() * 1000))
        return [[ms, "1", "2", "0.5", "1.5", "3", "0", "9", "1", "0", "0", "0"]]

    return doc, goi


# ─── 1. Rổ T1 không bị kéo theo ───


def test_ro_t1_giu_nguyen_5m_tu_T1() -> None:
    """Bất biến ĐẮT NHẤT của TD-0252: 107 mã rổ T1 đã có 5m phủ [T1,T2]. Nếu 5m của
    `SAU_LOAI_FILE` đổi sang `t0` thì `kiem_du_lieu_ro()` coi cả 107 mã là thiếu đầu."""
    nam_m = next(lf for lf in SAU_LOAI_FILE if lf.khung == "5m")
    assert nam_m.tu_moc == "t1"
    assert LOAI_5M_T0.tu_moc == "t0"
    assert nam_m != LOAI_5M_T0
    assert len(SAU_LOAI_FILE_T0) == 6 and len(NAM_LOAI_FILE_T0) == 5


# ─── 2. nhap_them_loai_file() ───


def test_them_5m_dung_moc_ngung_DUOC_CAP_khong_do_lai(tmp_path: Path) -> None:
    """Mốc ngừng do người gọi cấp (đọc từ artifact TD-0301). Hàm KHÔNG đo lại — đo trên 5m
    có thể ra mốc khác mốc của file 1h cùng mã ⇒ hai file kết thúc lệch nhau."""
    doc, _ = _kho_gia()
    ngung = pd.Timestamp("2024-09-15", tz="UTC")
    so_hang = nhap_them_loai_file(
        "AUSDT", dich=tmp_path, khoang=KHOANG, moc=MOC, doc_csv=doc,
        loai_file=(LOAI_5M_T0,), moc_cuoi="t1", moc_ngung=ngung,
    )
    assert list(so_hang) == ["A_USDT_USDT-5m-futures.feather"]
    df = pd.read_feather(tmp_path / ten_file("AUSDT", LOAI_5M_T0))
    assert df["date"].max() <= ngung
    assert df["date"].min() >= pd.Timestamp(MOC["t0"], tz="UTC")


def test_them_5m_khong_co_moc_ngung_thi_cat_tai_moc_cuoi_ro(tmp_path: Path) -> None:
    doc, _ = _kho_gia()
    nhap_them_loai_file(
        "AUSDT", dich=tmp_path, khoang=KHOANG, moc=MOC, doc_csv=doc,
        loai_file=(LOAI_5M_T0,), moc_cuoi="t1",
    )
    df = pd.read_feather(tmp_path / ten_file("AUSDT", LOAI_5M_T0))
    assert df["date"].max() <= pd.Timestamp(MOC["t1"], tz="UTC")


def test_file_dich_da_ton_tai_thi_TU_CHOI_va_khong_ghi_gi(tmp_path: Path) -> None:
    (tmp_path / ten_file("AUSDT", LOAI_5M_T0)).write_bytes(b"cu")
    doc, goi = _kho_gia()
    with pytest.raises(DuLieuRoError, match="không ghi đè"):
        nhap_them_loai_file(
            "AUSDT", dich=tmp_path, khoang=KHOANG, moc=MOC, doc_csv=doc,
            loai_file=(LOAI_5M_T0,), moc_cuoi="t1",
        )
    assert (tmp_path / ten_file("AUSDT", LOAI_5M_T0)).read_bytes() == b"cu"
    assert goi == []  # từ chối TRƯỚC khi gọi mạng


def test_danh_sach_loai_rong_thi_TU_CHOI(tmp_path: Path) -> None:
    doc, _ = _kho_gia()
    with pytest.raises(DuLieuRoError, match="rỗng"):
        nhap_them_loai_file(
            "AUSDT", dich=tmp_path, khoang=KHOANG, moc=MOC, doc_csv=doc,
            loai_file=(), moc_cuoi="t1",
        )


def test_moc_ngung_muon_hon_moc_cuoi_ro_thi_TU_CHOI(tmp_path: Path) -> None:
    """Cấp nhầm artifact mốc ngừng của rổ khác (vd rổ T1, mốc cuối T2)."""
    doc, _ = _kho_gia()
    with pytest.raises(DuLieuRoError, match="mốc ngừng"):
        nhap_them_loai_file(
            "AUSDT", dich=tmp_path, khoang=KHOANG, moc=MOC, doc_csv=doc,
            loai_file=(LOAI_5M_T0,), moc_cuoi="t1",
            moc_ngung=pd.Timestamp("2025-12-01", tz="UTC"),
        )


def test_kho_thieu_thang_thi_TU_CHOI_khong_lap(tmp_path: Path) -> None:
    """N6 — thiếu tháng là dữ kiện, không phải 0. Và không ghi file dở."""
    doc, _ = _kho_gia(so_404={(2024, 7)})
    with pytest.raises(DuLieuRoError, match="kho thiếu tháng"):
        nhap_them_loai_file(
            "AUSDT", dich=tmp_path, khoang=KHOANG, moc=MOC, doc_csv=doc,
            loai_file=(LOAI_5M_T0,), moc_cuoi="t1",
        )
    assert list(tmp_path.glob("*.feather")) == []


def test_dung_het_roi_moi_ghi_tat_ca_hoac_khong(tmp_path: Path) -> None:
    """Hai loại, loại thứ hai hỏng ⇒ không file nào được ghi."""
    hong = LOAI_5M_T0.__class__("4h", "futures", "klines", "t0")
    doc, _ = _kho_gia(so_404={(2024, 4)})
    with pytest.raises(DuLieuRoError):
        nhap_them_loai_file(
            "AUSDT", dich=tmp_path, khoang=KHOANG, moc=MOC, doc_csv=doc,
            loai_file=(LOAI_5M_T0, hong), moc_cuoi="t1",
        )
    assert list(tmp_path.glob("*.feather")) == []


# ─── 3. kiem_du_lieu_ro() với kế hoạch đã lọc ───


def test_ke_hoach_chi_5m_khong_dem_duoi_nen_chet(tmp_path: Path) -> None:
    """Với kế hoạch lọc còn mỗi 5m, phần tử 0 LÀ file 5m. Nếu phép kiểm dựa vào VỊ TRÍ
    (`lf is loai_file[0]`) thì `duoi_nen_chet()` chạy trên nến 5m ⇒ báo động giả."""
    # Đuôi phải DÀI hơn NEN_CHET_TOI_THIEU (24), nếu không phép kiểm không kích hoạt được và
    # ca này thành PASS RỖNG — đã tự dính một lần khi viết, bắt bằng phá thật.
    assert NEN_CHET_TOI_THIEU == 24
    df = pd.concat(
        [
            _df("2024-04-09", "2025-06-09", "1D"),
            _df("2025-06-10 00:00", "2025-06-11 05:00", "1h", volume=0.0),
        ],
        ignore_index=True,
    )
    assert duoi_nen_chet(df) > NEN_CHET_TOI_THIEU  # ca có răng: đuôi đủ dài để phép kiểm nổ
    df.to_feather(tmp_path / ten_file("AUSDT", LOAI_5M_T0))
    khoang = {"AUSDT": KHOANG}
    loi = kiem_du_lieu_ro(tmp_path, ["AUSDT"], khoang, MOC, loai_file=(LOAI_5M_T0,), moc_cuoi="t1")
    assert not any("nến chết" in x for x in loi)


def test_file_hong_thi_mot_dong_loi_khong_traceback(tmp_path: Path) -> None:
    (tmp_path / ten_file("AUSDT", LOAI_5M_T0)).write_bytes(b"khong phai feather")
    loi = kiem_du_lieu_ro(
        tmp_path, ["AUSDT"], {"AUSDT": KHOANG}, MOC, loai_file=(LOAI_5M_T0,), moc_cuoi="t1"
    )
    assert any("KHÔNG ĐỌC ĐƯỢC" in x for x in loi)


# ─── 4. L-Z55 trên dữ liệu rổ thật ───


def _bien_calib() -> DatasetBoundary:
    return DatasetBoundary(name="CALIB", start=MOC["t0"], end=MOC["t1"])


def test_lz55_bat_nen_vuot_T1_va_nen_truoc_T0(tmp_path: Path) -> None:
    _df("2024-04-09", "2025-06-14", "1D").to_feather(tmp_path / ten_file("AUSDT", LOAI_5M_T0))
    _df("2024-04-01", "2025-06-11", "1D").to_feather(tmp_path / ten_file("BUSDT", LOAI_5M_T0))
    loi = kiem_pham_vi_dataset(
        tmp_path, ["AUSDT", "BUSDT"], (LOAI_5M_T0,), dataset="CALIB", boundary=_bien_calib()
    )
    assert len(loi) == 2 and all("L-Z55" in x for x in loi)


def test_lz55_nhan_dataset_sai_thi_tu_choi(tmp_path: Path) -> None:
    _df("2024-04-09", "2025-06-11", "1D").to_feather(tmp_path / ten_file("AUSDT", LOAI_5M_T0))
    loi = kiem_pham_vi_dataset(
        tmp_path, ["AUSDT"], (LOAI_5M_T0,), dataset="WFO", boundary=_bien_calib()
    )
    assert len(loi) == 1 and "không khớp" in loi[0]


def test_lz55_du_lieu_nam_tron_thi_sach(tmp_path: Path) -> None:
    _df("2024-04-09", "2025-06-11", "1D").to_feather(tmp_path / ten_file("AUSDT", LOAI_5M_T0))
    assert kiem_pham_vi_dataset(
        tmp_path, ["AUSDT"], (LOAI_5M_T0,), dataset="CALIB", boundary=_bien_calib()
    ) == []


# ─── 5. Độ phủ — đúng câu `backtesting.py:1739` hỏi ───


def test_do_phu_bat_ma_co_1h_ma_vang_5m() -> None:
    chinh = {"A/USDT:USDT": _df("2024-04-09", "2024-04-11", "1h")}
    assert cho_thieu_khung_chi_tiet(chinh, {}) [0].ly_do == KHONG_CO_KHUNG_CHI_TIET


def test_do_phu_bat_THUNG_GIUA_CHUOI() -> None:
    """Điều mà phép đếm mã KHÔNG thấy: mã có mặt nhưng chuỗi 5m thủng ở giữa."""
    chinh = {"A/USDT:USDT": _df("2024-04-09", "2024-04-11", "1h")}
    ct = _df("2024-04-09", "2024-04-11", "5min")
    ct = ct[~ct["date"].between(pd.Timestamp("2024-04-10 03:00", tz="UTC"), pd.Timestamp("2024-04-10 03:55", tz="UTC"))]
    thieu = cho_thieu_khung_chi_tiet(chinh, {"A/USDT:USDT": ct.reset_index(drop=True)})
    assert len(thieu) == 1 and thieu[0].ly_do == THUNG_GIUA_CHUOI
    assert thieu[0].so_gio_thieu == 1 and "2024-04-10 03:00" in thieu[0].vi_du_gio[0]
    assert "thủng 1/" in thieu[0].mo_ta()


def test_do_phu_du_thi_rong() -> None:
    chinh = {"A/USDT:USDT": _df("2024-04-09", "2024-04-11", "1h")}
    ct = {"A/USDT:USDT": _df("2024-04-09", "2024-04-11", "5min")}
    assert cho_thieu_khung_chi_tiet(chinh, ct) == []


def test_do_phu_mot_nen_5m_trong_gio_cuoi_van_tinh_la_du() -> None:
    """Mã ngừng giao dịch cắt tại mốc ngừng: giờ cuối chỉ còn 1/12 nến 5m (DR-D1-05 §3b.5)."""
    chinh = {"A/USDT:USDT": _df("2024-04-09 00:00", "2024-04-09 02:00", "1h")}
    ct = _df("2024-04-09 00:00", "2024-04-09 02:00", "5min")
    assert cho_thieu_khung_chi_tiet(chinh, {"A/USDT:USDT": ct}) == []


def test_tom_tat_ma_thieu_mang_None_khong_phai_0() -> None:
    """N6 — chưa đo được khác với đo ra 0."""
    bang = tom_tat_theo_ma({}, {}, ["A/USDT:USDT"])
    assert bang["A/USDT:USDT"]["so_nen_chi_tiet"] is None
    assert bang["A/USDT:USDT"]["so_gio_chinh_thieu_chi_tiet"] is None
