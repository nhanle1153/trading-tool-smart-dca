"""🔴 TD-0168 — dấu vết từng ca của DR-015 Bước 2 phải được LƯU, và phải
là dấu vết của CHÍNH con số đã niêm phong.

Hai thứ bộ test này canh chặt nhất:

1. **Từ chối ghi khi lần chạy mới lệch artifact.** Đây là toàn bộ lý do
   file dấu vết đáng tin: nó sinh từ một đường chạy KHÁC đường đã cho ra
   `p_nf = [0,0]` (vòng chốt TD-0162 viết thẳng, không gọi
   `do_ty_le_khong_khop()`). Một dấu vết không khớp con số đang dùng thì
   tệ hơn không có — nó để lại hai bộ số cho người sau tự hoà giải.

2. **Dấu vết không được gán nhầm sự kiện.** `NapGomTheoNgay` bám vào thứ
   tự gọi để ghi `ts_xuyen_dau_ms`; nếu ràng buộc đó im lặng thì một dòng
   dấu vết mang cửa sổ của ca này và thời điểm xuyên của ca khác, mà mọi
   con số TỔNG vẫn đúng y nguyên. Không phép kiểm tổng nào bắt được.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from tool_d.dr015.buoc1_lech_tranche import _p90
from tool_d.dr015.buoc2_chi_tiet import (
    CUA_SO_MS,
    Buoc2ChiTietError,
    NapGomTheoNgay,
    _bien_xam_nhap_pct,
    _doi_chieu_niem_phong,
    _ngay_can,
    _phan_vi,
    _symbol_san,
    chay,
    dung_su_kien,
)
from tool_d.fill_probe import GiaoDich, SuKienChoKhop, tong_hop, TrangThaiKhop

REPO_ROOT = Path(__file__).resolve().parents[2]
DU_LIEU_THAT = json.loads(
    (REPO_ROOT / "docs/du-lieu-do/dr015-luot-khop-tranche.json").read_text(encoding="utf-8")
)

MOT_NGAY_MS = 24 * 60 * 60 * 1000
# 2024-06-05T12:00:00Z — giữa ngày, để cửa sổ ±3h không bắc qua nửa đêm.
GIUA_NGAY_MS = 1717588800000


def _sk(i: int, *, den_ms: int, p: float = 100.0, symbol: str = "XUSDT", huong: str = "long"):
    return SuKienChoKhop(symbol=symbol, huong=huong, p=p, den_ms=den_ms, nhan=str(i))


def _kho_gia_lap(theo_ngay: dict[tuple[str, date], list[GiaoDich]]):
    """Trả `(tai, doc, so_lan_doc)` — cửa mạng giả, KHÔNG chạm đĩa."""
    dem: dict[Path, int] = {}

    def tai(*, symbol: str, ngay: date, thu_muc_cache: Path, **_):
        if (symbol, ngay) not in theo_ngay:
            raise AssertionError(f"test không dựng dump cho {symbol} {ngay}")
        return Path(f"/gia-lap/{symbol}-{ngay}.zip")

    def doc(duong_dan: Path):
        dem[duong_dan] = dem.get(duong_dan, 0) + 1
        ten = duong_dan.name[: -len(".zip")]
        symbol, ngay = ten.split("-", 1)
        return list(theo_ngay[(symbol, date.fromisoformat(ngay))])

    return tai, doc, dem


class TestAnhXaSuKien:
    """Dựng sai sự kiện thì mọi con số phía sau nói về một phép đo khác."""

    def test_91_su_kien_tu_du_lieu_that_dung_anh_xa(self) -> None:
        su_kien, tranche = dung_su_kien(DU_LIEU_THAT)
        rows = DU_LIEU_THAT["luot_khop"]
        assert len(su_kien) == len(tranche) == 91
        for i, (sk, r) in enumerate(zip(su_kien, rows, strict=True)):
            assert sk.p == r["p_ke_hoach"]
            assert sk.den_ms == r["fill_ts_ms"]
            assert sk.huong == r["huong"]
            assert sk.nhan == str(i)
        assert {sk.symbol for sk in su_kien} == {"1000PEPEUSDT", "1000BONKUSDT"}

    def test_symbol_bo_ca_hai_hau_to_cua_cap_hop_dong(self) -> None:
        assert _symbol_san("1000BONK/USDT:USDT") == "1000BONKUSDT"

    def test_du_lieu_rong_thi_raise_khong_tra_danh_sach_rong(self) -> None:
        with pytest.raises(Buoc2ChiTietError):
            dung_su_kien({"luot_khop": []})


class TestCuaSoBacQuaNuaDem:
    """Bỏ sót dump thứ hai làm cửa sổ HẸP lại một cách lặng lẽ — và cửa sổ
    hẹp đẩy ca từ 'chắc chắn khớp' sang 'không khớp', tức đúng chiều thổi
    phồng p_nf."""

    def test_giua_ngay_can_mot_dump(self) -> None:
        assert _ngay_can(tu_ms=GIUA_NGAY_MS - CUA_SO_MS, het_ms=GIUA_NGAY_MS + CUA_SO_MS) == [
            date(2024, 6, 5)
        ]

    def test_sat_nua_dem_can_HAI_dump(self) -> None:
        nua_dem = 1717632000000  # 2024-06-06T00:00:00Z
        assert _ngay_can(tu_ms=nua_dem - CUA_SO_MS, het_ms=nua_dem + CUA_SO_MS) == [
            date(2024, 6, 5),
            date(2024, 6, 6),
        ]


class TestNapGomTheoNgay:
    def test_moi_dump_chi_doc_MOT_luot_du_nhieu_su_kien_cung_ngay(self) -> None:
        """Nếu số này lớn hơn 1 thì phép đo mở lại 599 MB nhiều lần — đó
        chính là lý do vòng chốt cũ không đi qua hàm của module."""
        gd = [GiaoDich(ts_ms=GIUA_NGAY_MS, gia=99.0, khoi_luong=1.0)]
        tai, doc, dem = _kho_gia_lap({("XUSDT", date(2024, 6, 5)): gd})
        su_kien = [_sk(i, den_ms=GIUA_NGAY_MS + i * 1000) for i in range(5)]
        nap = NapGomTheoNgay(
            su_kien, truoc_ms=CUA_SO_MS, sau_ms=CUA_SO_MS, thu_muc_cache=Path("/x"), tai=tai, doc=doc
        )
        for sk in su_kien:
            nap(sk.symbol, sk.den_ms - CUA_SO_MS, sk.den_ms + CUA_SO_MS)
        assert list(dem.values()) == [1]
        assert nap.so_lan_doc_dump == 1

    def test_giai_phong_dump_khi_khong_su_kien_nao_con_can(self) -> None:
        """Bộ nhớ phải bị chặn theo cửa sổ, không theo tổng số sự kiện."""
        theo_ngay = {
            ("XUSDT", date(2024, 6, 5)): [GiaoDich(ts_ms=GIUA_NGAY_MS, gia=99.0, khoi_luong=1.0)],
            ("XUSDT", date(2024, 6, 6)): [
                GiaoDich(ts_ms=GIUA_NGAY_MS + MOT_NGAY_MS, gia=99.0, khoi_luong=1.0)
            ],
        }
        tai, doc, _ = _kho_gia_lap(theo_ngay)
        su_kien = [_sk(0, den_ms=GIUA_NGAY_MS), _sk(1, den_ms=GIUA_NGAY_MS + MOT_NGAY_MS)]
        nap = NapGomTheoNgay(
            su_kien, truoc_ms=CUA_SO_MS, sau_ms=CUA_SO_MS, thu_muc_cache=Path("/x"), tai=tai, doc=doc
        )
        nap(su_kien[0].symbol, su_kien[0].den_ms - CUA_SO_MS, su_kien[0].den_ms + CUA_SO_MS)
        assert list(nap._kho) == []  # ngày 05 đã hết người cần
        nap(su_kien[1].symbol, su_kien[1].den_ms - CUA_SO_MS, su_kien[1].den_ms + CUA_SO_MS)
        assert list(nap._kho) == []

    def test_goi_SAI_THU_TU_thi_raise_chu_khong_gan_nham_dau_vet(self) -> None:
        """🔴 Ca quan trọng nhất của lớp này: sai thứ tự làm dấu vết mang
        cửa sổ của ca này và thời điểm xuyên của ca khác, trong khi MỌI
        con số tổng vẫn đúng nguyên."""
        gd = [GiaoDich(ts_ms=GIUA_NGAY_MS, gia=99.0, khoi_luong=1.0)]
        tai, doc, _ = _kho_gia_lap({("XUSDT", date(2024, 6, 5)): gd})
        su_kien = [_sk(0, den_ms=GIUA_NGAY_MS), _sk(1, den_ms=GIUA_NGAY_MS + 1000)]
        nap = NapGomTheoNgay(
            su_kien, truoc_ms=CUA_SO_MS, sau_ms=CUA_SO_MS, thu_muc_cache=Path("/x"), tai=tai, doc=doc
        )
        with pytest.raises(Buoc2ChiTietError, match="thứ tự"):
            nap(su_kien[1].symbol, su_kien[1].den_ms - CUA_SO_MS, su_kien[1].den_ms + CUA_SO_MS)

    def test_goi_nhieu_hon_so_su_kien_thi_raise(self) -> None:
        gd = [GiaoDich(ts_ms=GIUA_NGAY_MS, gia=99.0, khoi_luong=1.0)]
        tai, doc, _ = _kho_gia_lap({("XUSDT", date(2024, 6, 5)): gd})
        su_kien = [_sk(0, den_ms=GIUA_NGAY_MS)]
        nap = NapGomTheoNgay(
            su_kien, truoc_ms=CUA_SO_MS, sau_ms=CUA_SO_MS, thu_muc_cache=Path("/x"), tai=tai, doc=doc
        )
        nap("XUSDT", GIUA_NGAY_MS - CUA_SO_MS, GIUA_NGAY_MS + CUA_SO_MS)
        with pytest.raises(Buoc2ChiTietError, match="chỉ có 1 sự kiện"):
            nap("XUSDT", GIUA_NGAY_MS - CUA_SO_MS, GIUA_NGAY_MS + CUA_SO_MS)

    def test_ts_xuyen_dau_la_giao_dich_XUYEN_dau_tien_khong_phai_som_nhat(self) -> None:
        """Giao dịch sớm nhất trong cửa sổ có thể chưa xuyên qua `p`. Lấy
        nhầm cái đó thì `tre_phut` nói về một sự kiện không xảy ra."""
        gd = [
            GiaoDich(ts_ms=GIUA_NGAY_MS - 1000, gia=101.0, khoi_luong=1.0),  # chưa xuyên
            GiaoDich(ts_ms=GIUA_NGAY_MS + 500, gia=99.0, khoi_luong=1.0),  # xuyên
            GiaoDich(ts_ms=GIUA_NGAY_MS + 900, gia=98.0, khoi_luong=1.0),
        ]
        tai, doc, _ = _kho_gia_lap({("XUSDT", date(2024, 6, 5)): gd})
        su_kien = [_sk(0, den_ms=GIUA_NGAY_MS, p=100.0)]
        nap = NapGomTheoNgay(
            su_kien, truoc_ms=CUA_SO_MS, sau_ms=CUA_SO_MS, thu_muc_cache=Path("/x"), tai=tai, doc=doc
        )
        nap("XUSDT", GIUA_NGAY_MS - CUA_SO_MS, GIUA_NGAY_MS + CUA_SO_MS)
        assert nap.ts_xuyen_dau_ms == [GIUA_NGAY_MS + 500]

    def test_khong_ca_nao_xuyen_thi_ts_la_None_khong_phai_0(self) -> None:
        """N6: không quan sát được KHÁC với 'xảy ra tại mốc 0'."""
        gd = [GiaoDich(ts_ms=GIUA_NGAY_MS, gia=100.0, khoi_luong=1.0)]  # đúng bằng p
        tai, doc, _ = _kho_gia_lap({("XUSDT", date(2024, 6, 5)): gd})
        su_kien = [_sk(0, den_ms=GIUA_NGAY_MS, p=100.0)]
        nap = NapGomTheoNgay(
            su_kien, truoc_ms=CUA_SO_MS, sau_ms=CUA_SO_MS, thu_muc_cache=Path("/x"), tai=tai, doc=doc
        )
        nap("XUSDT", GIUA_NGAY_MS - CUA_SO_MS, GIUA_NGAY_MS + CUA_SO_MS)
        assert nap.ts_xuyen_dau_ms == [None]


class TestBienXamNhap:
    def test_long_dung_gia_THAP_nhat_va_am_nghia_la_da_xuyen(self) -> None:
        c = {"huong": "long", "p": 100.0, "gia_thap_nhat": 99.0, "gia_cao_nhat": 105.0}
        assert _bien_xam_nhap_pct(c) == pytest.approx(-1.0)

    def test_short_dao_dau_de_AM_van_nghia_la_da_xuyen(self) -> None:
        """Cùng quy ước cho cả hai chiều, nếu không thì một cột đổi nghĩa
        giữa chừng khi bật Short."""
        c = {"huong": "short", "p": 100.0, "gia_thap_nhat": 95.0, "gia_cao_nhat": 101.0}
        assert _bien_xam_nhap_pct(c) == pytest.approx(-1.0)


class TestPhanViKhongTroiLechVoiTD0161:
    def test_phan_vi_0_9_khop_dung_p90_cua_buoc1(self) -> None:
        """Hai hàm phân vị trong cùng một dự án phải cùng quy tắc, nếu
        không thì 'P90' nghĩa khác nhau tuỳ file người đọc mở."""
        for ds in ([1.0, 2.0, 3.0], [5.0], list(range(11)), [0.3, 0.1, 0.7, 0.2]):
            assert _phan_vi(ds, 0.90) == pytest.approx(_p90(list(map(float, ds))), abs=1e-15)


class TestTuChoiGhiKhiLechNiemPhong:
    """🔴 Chốt sống còn: dấu vết chỉ có giá trị khi nó là dấu vết của
    CHÍNH con số đang dùng."""

    @staticmethod
    def _bo_khop(n: int = 40):
        """`n` ca đều CHẮC CHẮN KHỚP, xuyên 1% dưới p, xuyên trước mốc 1 phút."""
        chi_tiet = [
            {
                "huong": "long",
                "p": 100.0,
                "gia_thap_nhat": 99.0,
                "gia_cao_nhat": 101.0,
                "moc_backtest_ms": GIUA_NGAY_MS,
                "tre_phut": -1.0,
            }
            for _ in range(n)
        ]
        khoang = tong_hop([TrangThaiKhop.CHAC_CHAN_KHOP] * n)
        niem_phong = {
            "ket_qua": {
                "chac_chan_khop": n,
                "bat_dinh": 0,
                "chac_chan_khong_khop": 0,
                "p_nf_thap": 0.0,
                "p_nf_cao": 0.0,
            },
            "bien_xam_nhap_pct": {
                "sau_nhat": -1.0,
                "nong_nhat": -1.0,
                "trung_vi": -1.0,
                "so_ca_nong_hon_0_05pct": 0,
            },
            "tre_so_voi_moc_backtest_phut": {
                "min": -1.0,
                "max": -1.0,
                "trung_vi": -1.0,
                "so_ca_xuyen_TRUOC_moc": n,
            },
        }
        return khoang, chi_tiet, niem_phong

    def test_khop_hoan_toan_thi_tra_tom_tat(self) -> None:
        khoang, chi_tiet, niem_phong = self._bo_khop()
        tom = _doi_chieu_niem_phong(khoang=khoang, chi_tiet=chi_tiet, niem_phong=niem_phong)
        assert tom["so_ca"] == 40
        assert tom["bien_xam_nhap_pct"]["trung_vi"] == pytest.approx(-1.0)

    def test_lech_SO_DEM_thi_TU_CHOI(self) -> None:
        khoang, chi_tiet, niem_phong = self._bo_khop()
        niem_phong["ket_qua"]["chac_chan_khong_khop"] = 3
        with pytest.raises(Buoc2ChiTietError, match="chac_chan_khong_khop"):
            _doi_chieu_niem_phong(khoang=khoang, chi_tiet=chi_tiet, niem_phong=niem_phong)

    def test_lech_p_nf_thi_TU_CHOI(self) -> None:
        khoang, chi_tiet, niem_phong = self._bo_khop()
        niem_phong["ket_qua"]["p_nf_cao"] = 0.1648
        with pytest.raises(Buoc2ChiTietError, match="p_nf_cao"):
            _doi_chieu_niem_phong(khoang=khoang, chi_tiet=chi_tiet, niem_phong=niem_phong)

    def test_lech_BIEN_XAM_NHAP_thi_TU_CHOI_du_so_dem_van_dung(self) -> None:
        """Số đếm khớp mà biên lệch nghĩa là cùng kết luận trên một tập
        giao dịch KHÁC — đúng thứ chỉ dấu vết mới lộ ra."""
        khoang, chi_tiet, niem_phong = self._bo_khop()
        niem_phong["bien_xam_nhap_pct"]["sau_nhat"] = -9.2828
        with pytest.raises(Buoc2ChiTietError, match="bien.sau_nhat"):
            _doi_chieu_niem_phong(khoang=khoang, chi_tiet=chi_tiet, niem_phong=niem_phong)

    def test_lech_DO_TRE_thi_TU_CHOI(self) -> None:
        khoang, chi_tiet, niem_phong = self._bo_khop()
        niem_phong["tre_so_voi_moc_backtest_phut"]["so_ca_xuyen_TRUOC_moc"] = 7
        with pytest.raises(Buoc2ChiTietError, match="so_ca_xuyen_TRUOC_moc"):
            _doi_chieu_niem_phong(khoang=khoang, chi_tiet=chi_tiet, niem_phong=niem_phong)

    def test_P10_P90_KHONG_nam_trong_phep_doi_chieu(self) -> None:
        """Cố ý đứng ngoài: artifact không ghi cách nội suy, nên chênh ở
        đó là chênh QUY ƯỚC. Một phép kiểm báo đỏ vì lý do sai sớm muộn
        bị gỡ, và gỡ rồi thì mất luôn phần đúng của nó."""
        khoang, chi_tiet, niem_phong = self._bo_khop()
        niem_phong["bien_xam_nhap_pct"]["P10"] = -999.0
        niem_phong["bien_xam_nhap_pct"]["P90"] = 999.0
        _doi_chieu_niem_phong(khoang=khoang, chi_tiet=chi_tiet, niem_phong=niem_phong)


class TestChayTronVenKhongChamMang:
    """End-to-end qua `chay()`, cửa mạng thay bằng dump giả."""

    @staticmethod
    def _dung_ho_so(tmp_path: Path, n: int = 35):
        # Mỗi ca một MÃ riêng, cố ý: cửa sổ ±3h rộng hơn khoảng cách giữa
        # các ca rất nhiều, nên nếu dùng chung mã thì mọi cửa sổ bao trùm
        # cùng một tập giao dịch và `tre_phut` của ca sau bị neo vào giao
        # dịch của ca đầu. Tách mã cho mỗi ca đúng một quan sát.
        rows, kho = [], {}
        for i in range(n):
            den = GIUA_NGAY_MS + i * 60_000
            rows.append(
                {
                    "trade_idx": i,
                    "pair": f"X{i}/USDT:USDT",
                    "huong": "long",
                    "tranche": (i % 3) + 1,
                    "p_ke_hoach": 100.0,
                    "fill_ts_ms": den,
                }
            )
            kho[(f"X{i}USDT", date(2024, 6, 5))] = [
                GiaoDich(ts_ms=den - 60_000, gia=99.0, khoi_luong=1.0)
            ]
        tho = tmp_path / "tho.json"
        tho.write_text(json.dumps({"luot_khop": rows}), encoding="utf-8")
        np = tmp_path / "niem-phong.json"
        np.write_text(
            json.dumps(
                {
                    "ket_qua": {
                        "chac_chan_khop": n,
                        "bat_dinh": 0,
                        "chac_chan_khong_khop": 0,
                        "p_nf_thap": 0.0,
                        "p_nf_cao": 0.0,
                    },
                    "bien_xam_nhap_pct": {
                        "sau_nhat": -1.0,
                        "nong_nhat": -1.0,
                        "trung_vi": -1.0,
                        "so_ca_nong_hon_0_05pct": 0,
                    },
                    "tre_so_voi_moc_backtest_phut": {
                        "min": -1.0,
                        "max": -1.0,
                        "trung_vi": -1.0,
                        "so_ca_xuyen_TRUOC_moc": n,
                    },
                }
            ),
            encoding="utf-8",
        )
        return tho, np, kho

    def test_ghi_du_dau_vet_tung_ca_va_moi_dong_truy_nguoc_duoc(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        tho, np_, kho = self._dung_ho_so(tmp_path)
        tai, doc, _ = _kho_gia_lap(kho)
        monkeypatch.setattr("tool_d.dr015.buoc2_chi_tiet.tai_dump_agg_trades", tai)
        monkeypatch.setattr("tool_d.dr015.buoc2_chi_tiet.doc_dump_agg_trades", doc)
        ra = tmp_path / "chi-tiet.json"

        noi_dung = chay(
            thu_muc_cache=tmp_path,
            du_lieu_tho_path=tho,
            niem_phong_path=np_,
            chi_tiet_path=ra,
        )

        tren_dia = json.loads(ra.read_text(encoding="utf-8"))
        assert tren_dia == noi_dung
        assert len(tren_dia["chi_tiet"]) == 35
        c = tren_dia["chi_tiet"][0]
        # đủ để truy ngược MỘT ca: dòng gốc, cửa sổ, quan sát, kết luận
        for khoa in (
            "nhan", "symbol", "huong", "p", "tranche",
            "tu_ms", "moc_backtest_ms", "het_ms",
            "so_giao_dich_trong_cua_so", "gia_thap_nhat", "gia_cao_nhat",
            "bien_xam_nhap_pct", "ts_xuyen_dau_ms", "tre_phut", "trang_thai",
        ):
            assert khoa in c, f"thiếu {khoa} — không truy ngược được từng ca"
        assert [x["nhan"] for x in tren_dia["chi_tiet"]] == [str(i) for i in range(35)]
        assert {x["tranche"] for x in tren_dia["chi_tiet"]} == {1, 2, 3}
        assert c["tre_phut"] == pytest.approx(-1.0)

    def test_LECH_niem_phong_thi_KHONG_GHI_FILE_NAO(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Kiểm có răng cho chốt fail-closed: từ chối phải xảy ra TRƯỚC
        khi chạm đĩa, không phải ghi rồi báo lỗi."""
        tho, np_, kho = self._dung_ho_so(tmp_path)
        hong = json.loads(np_.read_text(encoding="utf-8"))
        hong["ket_qua"]["chac_chan_khong_khop"] = 15
        np_.write_text(json.dumps(hong), encoding="utf-8")
        tai, doc, _ = _kho_gia_lap(kho)
        monkeypatch.setattr("tool_d.dr015.buoc2_chi_tiet.tai_dump_agg_trades", tai)
        monkeypatch.setattr("tool_d.dr015.buoc2_chi_tiet.doc_dump_agg_trades", doc)
        ra = tmp_path / "chi-tiet.json"

        with pytest.raises(Buoc2ChiTietError, match="TỪ CHỐI"):
            chay(thu_muc_cache=tmp_path, du_lieu_tho_path=tho, niem_phong_path=np_, chi_tiet_path=ra)
        assert not ra.exists()


class TestKhongDungVaoArtifactDaNiemPhong:
    """Cổng D3.5 đã đóng lên ba artifact; file dấu vết phải đứng NGOÀI."""

    def test_file_dau_vet_khong_nam_trong_FILE_KET_QUA_D35(self) -> None:
        from tool_d.dr015.cong_d35 import FILE_KET_QUA_D35

        duong_dan = [p for _, p in FILE_KET_QUA_D35]
        assert len(FILE_KET_QUA_D35) == 3
        assert "docs/du-lieu-do/dr015-buoc2-chi-tiet.json" not in duong_dan

    def test_module_khong_ghi_vao_bat_ky_artifact_niem_phong_nao(self) -> None:
        """Chốt AST-lite: tên ba file niêm phong chỉ được xuất hiện ở chỗ
        ĐỌC để đối chiếu, không có đường nào ghi đè chúng."""
        import inspect

        import tool_d.dr015.buoc2_chi_tiet as mod

        src = inspect.getsource(mod)
        assert "dr015-buoc1-delta-r.json" not in src
        assert "dr015-buoc3-doi-chung-z0.json" not in src
        assert "write_text" in src  # có ghi, và chỉ ghi một chỗ
        assert src.count("write_text") == 1
