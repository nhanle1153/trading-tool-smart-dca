"""🔴 TD-0162 — DR-015 Bước 2: tỷ lệ KHÔNG khớp, đo từ dữ liệu khớp lệnh THẬT.

Hai thứ bộ test này canh chặt nhất, vì cả hai đều là chỗ một phép đo
trung thực dễ biến thành một con số tự tin mà sai:

1. **Đầu ra phải là KHOẢNG, không bao giờ là một số.** Vùng bất định là
   chỗ ta thật sự không biết; ép nó về một điểm là bịa thông tin. Có ca
   soi cả API của module để chắc rằng không tồn tại đường tắt trả về
   tỉ lệ vô hướng.
2. **Ba thứ phương án này không thấy được** (post-only bị từ chối, khớp
   một phần, vị trí hàng đợi) đều phải rơi vào vùng bất định — tức tính
   về phía bất lợi cho DCA. Nếu có đường nào làm kết luận LẠC QUAN hơn
   thực tế thì phép đo mất tư cách.
"""

from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path

import pytest

from tool_d.fill_probe import (
    SO_SU_KIEN_TOI_THIEU,
    FillProbeError,
    GiaoDich,
    KhoangNoFill,
    TrangThaiKhop,
    doc_dump_agg_trades,
    loc_cua_so,
    phan_loai_khop,
    tong_hop,
)


def _gd(gia: float, ts: int = 1000, kl: float = 1.0) -> GiaoDich:
    return GiaoDich(ts_ms=ts, gia=gia, khoi_luong=kl)


class TestPhanLoaiLong:
    """Mua chờ tại p."""

    def test_co_giao_dich_THAP_HON_p_thi_chac_chan_khop(self) -> None:
        # Ưu tiên giá-thời gian: người bán phải lấp hết lệnh mua ở p TRƯỚC
        # khi giá đi thấp hơn.
        kq = phan_loai_khop(huong="long", p=100.0, giao_dich=[_gd(101.0), _gd(99.9)])
        assert kq is TrangThaiKhop.CHAC_CHAN_KHOP

    def test_thap_nhat_DUNG_BANG_p_thi_bat_dinh(self) -> None:
        """Chạm đúng mức nhưng không xuyên qua — khớp hay không phụ thuộc
        vị trí hàng đợi, thứ dữ liệu giao dịch KHÔNG nói được."""
        kq = phan_loai_khop(huong="long", p=100.0, giao_dich=[_gd(100.0), _gd(105.0)])
        assert kq is TrangThaiKhop.BAT_DINH

    def test_khong_giao_dich_nao_duoi_p_thi_chac_chan_khong_khop(self) -> None:
        kq = phan_loai_khop(huong="long", p=100.0, giao_dich=[_gd(100.01), _gd(120.0)])
        assert kq is TrangThaiKhop.CHAC_CHAN_KHONG_KHOP


class TestPhanLoaiShort:
    """Bán chờ tại p — đảo dấu hoàn toàn."""

    def test_co_giao_dich_CAO_HON_p_thi_chac_chan_khop(self) -> None:
        kq = phan_loai_khop(huong="short", p=100.0, giao_dich=[_gd(99.0), _gd(100.1)])
        assert kq is TrangThaiKhop.CHAC_CHAN_KHOP

    def test_cao_nhat_DUNG_BANG_p_thi_bat_dinh(self) -> None:
        kq = phan_loai_khop(huong="short", p=100.0, giao_dich=[_gd(100.0), _gd(95.0)])
        assert kq is TrangThaiKhop.BAT_DINH

    def test_khong_giao_dich_nao_tren_p_thi_chac_chan_khong_khop(self) -> None:
        kq = phan_loai_khop(huong="short", p=100.0, giao_dich=[_gd(99.99)])
        assert kq is TrangThaiKhop.CHAC_CHAN_KHONG_KHOP

    def test_long_va_short_KHONG_cho_cung_ket_qua_tren_cung_du_lieu(self) -> None:
        """Đối chứng chống lỗi sao-chép-nhánh: nếu ai đó quên đảo dấu thì
        hai hướng sẽ cho cùng kết quả trên bộ dữ liệu này."""
        gd = [_gd(99.0)]
        assert phan_loai_khop(huong="long", p=100.0, giao_dich=gd) is TrangThaiKhop.CHAC_CHAN_KHOP
        assert (
            phan_loai_khop(huong="short", p=100.0, giao_dich=gd)
            is TrangThaiKhop.CHAC_CHAN_KHONG_KHOP
        )


class TestFailClosed:
    def test_cua_so_rong_la_CHAC_CHAN_khong_khop_khong_phai_bat_dinh(self) -> None:
        """Không có giao dịch nào nghĩa là không có ai để khớp với ta —
        đó là kết luận CHẮC CHẮN, không phải thiếu thông tin."""
        kq = phan_loai_khop(huong="long", p=100.0, giao_dich=[])
        assert kq is TrangThaiKhop.CHAC_CHAN_KHONG_KHOP

    @pytest.mark.parametrize("xau", ["LONG", "buy", "", "Long"])
    def test_huong_khong_hop_le_thi_raise(self, xau: str) -> None:
        with pytest.raises(FillProbeError, match="huong"):
            phan_loai_khop(huong=xau, p=100.0, giao_dich=[_gd(99.0)])

    @pytest.mark.parametrize("xau", [0.0, -1.0])
    def test_gia_khong_duong_thi_raise(self, xau: float) -> None:
        with pytest.raises(FillProbeError, match="p"):
            phan_loai_khop(huong="long", p=xau, giao_dich=[_gd(99.0)])

    def test_cua_so_dao_nguoc_thi_raise(self) -> None:
        with pytest.raises(FillProbeError, match="đảo ngược"):
            loc_cua_so([_gd(100.0)], tu_ms=2000, den_ms=1000)


class TestDauRaLaKHOANGKhongPhaiMotSo:
    """🔴 Trọng tâm của bộ test này."""

    def _ds(self, khop: int, bat_dinh: int, khong: int) -> list[TrangThaiKhop]:
        return (
            [TrangThaiKhop.CHAC_CHAN_KHOP] * khop
            + [TrangThaiKhop.BAT_DINH] * bat_dinh
            + [TrangThaiKhop.CHAC_CHAN_KHONG_KHOP] * khong
        )

    def test_thap_chi_tinh_ca_chac_chan_cao_cong_ca_bat_dinh(self) -> None:
        kq = tong_hop(self._ds(khop=70, bat_dinh=20, khong=10))
        assert kq.n == 100
        assert kq.thap.value == pytest.approx(0.10)
        assert kq.cao.value == pytest.approx(0.30)

    def test_vung_bat_dinh_lam_KHOANG_RONG_ra_khong_hep_lai(self) -> None:
        """Ba thứ không quan sát được (post-only bị từ chối, khớp một
        phần, vị trí hàng đợi) đều rơi vào đây — càng nhiều thì khoảng
        càng rộng, tức càng thận trọng."""
        hep = tong_hop(self._ds(khop=90, bat_dinh=0, khong=10))
        rong = tong_hop(self._ds(khop=60, bat_dinh=30, khong=10))
        assert hep.thap.value == rong.thap.value  # đầu dưới không đổi
        assert rong.cao.value > hep.cao.value  # chỉ đầu trên nới ra

    def test_cao_LUON_lon_hon_hoac_bang_thap(self) -> None:
        for b in range(0, 40, 7):
            kq = tong_hop(self._ds(khop=60 - b, bat_dinh=b, khong=40))
            assert kq.cao.value >= kq.thap.value

    def test_KHONG_co_duong_tat_tra_ve_mot_ti_le_vo_huong(self) -> None:
        """Nếu ai đó thêm `ty_le_khong_khop` hay `p_nf` trả về một số,
        người dùng sẽ lấy nó mà không thấy mình đang chọn đầu nào của
        khoảng. Ca này chặn đúng cửa đó."""
        cam = {"ty_le", "ty_le_khong_khop", "p_nf", "diem_giua", "trung_binh"}
        co = {t for t in dir(KhoangNoFill) if not t.startswith("_")}
        assert cam & co == set(), f"xuất hiện đường tắt trả về một số: {cam & co}"


class TestUnknownKhiMauQuaMong:
    def test_duoi_nguong_thi_ca_hai_dau_la_unreadable(self) -> None:
        kq = tong_hop([TrangThaiKhop.CHAC_CHAN_KHOP] * (SO_SU_KIEN_TOI_THIEU - 1))
        assert kq.thap.status.value == "unreadable"
        assert kq.cao.status.value == "unreadable"
        assert kq.thap.value is None and kq.cao.value is None
        assert not kq.du_su_kien

    def test_duoi_nguong_VAN_giu_so_dem_tung_loai(self) -> None:
        """Số đếm là quan sát THẬT; chỉ phép chia thành tỉ lệ mới là thứ
        không đủ cơ sở. Vứt luôn số đếm là vứt dữ liệu đã có."""
        kq = tong_hop(
            [TrangThaiKhop.CHAC_CHAN_KHOP] * 5 + [TrangThaiKhop.CHAC_CHAN_KHONG_KHOP] * 3
        )
        assert kq.n == 8 and kq.so_chac_chan_khop == 5 and kq.so_chac_chan_khong_khop == 3

    def test_dung_nguong_thi_doc_duoc(self) -> None:
        kq = tong_hop([TrangThaiKhop.CHAC_CHAN_KHOP] * SO_SU_KIEN_TOI_THIEU)
        assert kq.du_su_kien and kq.thap.status.value == "ok"

    def test_nguong_dung_bang_30_theo_spec(self) -> None:
        assert SO_SU_KIEN_TOI_THIEU == 30


def _dung_dump(tmp_path: Path, dong: list[list], *, them_tieu_de: bool) -> Path:
    p = tmp_path / "X-aggTrades-2024-08-15.zip"
    buf = io.StringIO()
    w = csv.writer(buf)
    if them_tieu_de:
        w.writerow(
            ["agg_trade_id", "price", "quantity", "first_trade_id",
             "last_trade_id", "transact_time", "is_buyer_maker"]
        )
    w.writerows(dong)
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("X-aggTrades-2024-08-15.csv", buf.getvalue())
    return p


class TestDocDump:
    DONG = [
        [1, "0.019", "100", 10, 11, 1723723200000, "true"],
        [2, "0.0191", "50", 12, 13, 1723723260000, "false"],
    ]

    @pytest.mark.parametrize("them_tieu_de", [True, False])
    def test_doc_duoc_ca_hai_dang_co_va_khong_co_tieu_de(
        self, tmp_path: Path, them_tieu_de: bool
    ) -> None:
        """Dump của Binance KHÔNG nhất quán giữa các giai đoạn: có ngày
        kèm dòng tiêu đề, có ngày không. Đọc nhầm tiêu đề thành dữ liệu
        sẽ ném `ValueError` giữa chừng một phép đo dài."""
        p = _dung_dump(tmp_path, self.DONG, them_tieu_de=them_tieu_de)
        gd = list(doc_dump_agg_trades(p))
        assert len(gd) == 2
        assert gd[0].gia == pytest.approx(0.019) and gd[0].ts_ms == 1723723200000

    def test_zip_khong_co_dung_mot_csv_thi_raise(self, tmp_path: Path) -> None:
        p = tmp_path / "hong.zip"
        with zipfile.ZipFile(p, "w") as z:
            z.writestr("a.csv", "1,2,3")
            z.writestr("b.csv", "4,5,6")
        with pytest.raises(FillProbeError, match="đúng 1 file"):
            list(doc_dump_agg_trades(p))

    def test_loc_cua_so_BAO_GOM_hai_dau(self, tmp_path: Path) -> None:
        p = _dung_dump(tmp_path, self.DONG, them_tieu_de=True)
        gd = list(doc_dump_agg_trades(p))
        assert len(loc_cua_so(gd, tu_ms=1723723200000, den_ms=1723723260000)) == 2
        assert len(loc_cua_so(gd, tu_ms=1723723200001, den_ms=1723723259999)) == 0


class TestDoTyLeKhongKhop:
    """Điều phối: chạy toàn bộ logic mà KHÔNG đụng mạng — hàm nạp giao
    dịch được tiêm vào. Test không đụng mạng là test luôn chạy được, thay
    vì bị skip lặng lẽ khi offline rồi coi như xanh."""

    def _su_kien(self, n: int) -> list:
        from tool_d.fill_probe import SuKienChoKhop

        return [
            SuKienChoKhop(symbol="XUSDT", huong="long", p=100.0, den_ms=10_000_000 + i, nhan=f"e{i}")
            for i in range(n)
        ]

    def test_cua_so_mo_ve_CA_HAI_phia_moc_backtest(self) -> None:
        """🔴 Bài học 08/09/2026: bản đầu chỉ lùi về trước và cho 15/91
        "chắc chắn không khớp" — nhưng 15/15 ca đó chạm được `p` trong 3
        GIỜ SAU mốc. `order_filled_timestamp` của backtest KHÔNG phải mốc
        giá thật chạm mức, và nó lệch CẢ HAI chiều."""
        from tool_d.fill_probe import do_ty_le_khong_khop

        goi: list[tuple] = []

        def nap(sym, tu, het):
            goi.append((sym, tu, het))
            return [_gd(99.0)]

        H = 3600 * 1000
        _, chi_tiet = do_ty_le_khong_khop(
            su_kien=self._su_kien(1), truoc_ms=3 * H, sau_ms=3 * H, nap_giao_dich=nap
        )
        sym, tu, het = goi[0]
        moc = chi_tiet[0]["moc_backtest_ms"]
        assert moc - tu == 3 * H and het - moc == 3 * H
        assert chi_tiet[0]["tu_ms"] == tu and chi_tiet[0]["het_ms"] == het

    def test_chi_tiet_giu_du_de_truy_nguoc_tung_ca(self) -> None:
        from tool_d.fill_probe import do_ty_le_khong_khop

        _, chi_tiet = do_ty_le_khong_khop(
            su_kien=self._su_kien(3),
            truoc_ms=1000,
            sau_ms=1000,
            nap_giao_dich=lambda s, a, b: [_gd(99.0)],
        )
        assert [c["nhan"] for c in chi_tiet] == ["e0", "e1", "e2"]
        assert all(c["trang_thai"] == "chac_chan_khop" for c in chi_tiet)
        assert all(c["gia_thap_nhat"] == 99.0 for c in chi_tiet)

    def test_cua_so_rong_ghi_None_khong_ghi_0(self) -> None:
        """Giá thấp nhất của một cửa sổ KHÔNG có giao dịch nào là `None`,
        không phải `0` — ghi 0 là bịa ra một mức giá chưa từng tồn tại."""
        from tool_d.fill_probe import do_ty_le_khong_khop

        _, chi_tiet = do_ty_le_khong_khop(
            su_kien=self._su_kien(1), truoc_ms=1000, sau_ms=1000, nap_giao_dich=lambda s, a, b: []
        )
        assert chi_tiet[0]["gia_thap_nhat"] is None
        assert chi_tiet[0]["trang_thai"] == "chac_chan_khong_khop"

    def test_cua_so_rong_hai_phia_thi_raise(self) -> None:
        from tool_d.fill_probe import do_ty_le_khong_khop

        with pytest.raises(FillProbeError, match="rỗng"):
            do_ty_le_khong_khop(
                su_kien=self._su_kien(1), truoc_ms=0, sau_ms=0, nap_giao_dich=lambda s, a, b: []
            )

    def test_cua_so_am_thi_raise(self) -> None:
        from tool_d.fill_probe import do_ty_le_khong_khop

        with pytest.raises(FillProbeError, match="truoc_ms"):
            do_ty_le_khong_khop(
                su_kien=self._su_kien(1), truoc_ms=-1, sau_ms=1000,
                nap_giao_dich=lambda s, a, b: []
            )

    def test_module_KHONG_tu_goi_mang(self) -> None:
        """🔴 R1 Single Egress: `fill_probe.py` không được là cửa mạng thứ
        hai. Mọi lệnh gọi ra Binance phải nằm ở `api_client/binance_public.py`."""
        import inspect

        import tool_d.fill_probe as mod

        src = inspect.getsource(mod)
        for cam in ("urllib", "requests", "httpx", "http.client", "socket"):
            assert cam not in src, f"fill_probe.py gọi mạng trực tiếp qua {cam} — vi phạm R1"
