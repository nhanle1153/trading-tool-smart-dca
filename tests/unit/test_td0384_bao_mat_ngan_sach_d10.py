"""TD-0384 chặng 1 — máy kiểm bảo mật tài khoản phụ (`api-integration-rules.md` 4.4c) và máy canh ngân sách D10
(`DR-D11-01` §4, `DR-D10-02` Q2). Mọi key/secret dưới đây là GIẢ; không gọi mạng thật."""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from tool_d.api_client.binance_public import (
    SPOT_BASE_URL,
    BinancePrivateApiError,
    dat_lai_trang_thai_mang_cho_kiem,
    get_api_restrictions,
)
from tool_d.ops.kiem_bao_mat_d10 import BaoMatD10Error, danh_gia_quyen_key, kiem_truoc_khi_bat
from tool_d.ops.ngan_sach_d10 import (
    DU_SU_KIEN_DOI_SL,
    TRAN_VI_THE,
    TrangThaiD10,
    han_chot,
    xet_them_tranche,
    xet_vi_the_moi,
)

UTC = timezone.utc
T0 = datetime(2026, 10, 1, tzinfo=UTC)

#: Cấu hình ĐẠT theo bảng 4.4c.
DAT = {
    "ipRestrict": True,
    "enableWithdrawals": False,
    "enableInternalTransfer": False,
    "permitsUniversalTransfer": False,
    "enableFutures": True,
    "enableReading": True,  # trường thừa không ảnh hưởng
}


class TestGetApiRestrictions:
    def setup_method(self) -> None:
        dat_lai_trang_thai_mang_cho_kiem()

    def test_goi_spot_base_url_dung_duong_va_ky(self) -> None:
        cm = MagicMock()
        cm.__enter__.return_value.read.return_value = b'{"ipRestrict": true}'
        with patch("time.sleep"), patch("tool_d.api_client.binance_public.urllib.request.urlopen") as mo:
            mo.return_value = cm
            assert get_api_restrictions(api_key="k-gia", api_secret="s-gia") == {"ipRestrict": True}
        req = mo.call_args[0][0]
        assert req.full_url.startswith(f"{SPOT_BASE_URL}/sapi/v1/account/apiRestrictions?")
        assert "signature=" in req.full_url and "timestamp=" in req.full_url
        assert req.headers.get("X-mbx-apikey") == "k-gia"
        assert "s-gia" not in req.full_url  # secret chỉ dùng để KÝ, không bao giờ đi trên URL


class TestDanhGiaQuyenKey:
    def test_cau_hinh_dat_thi_duoc_bat(self) -> None:
        kq = danh_gia_quyen_key(DAT)
        assert kq.duoc_bat and kq.ly_do_tu_choi == ()

    @pytest.mark.parametrize(
        ("truong", "gia_tri_sai"),
        [
            ("ipRestrict", False),
            ("enableWithdrawals", True),
            ("enableInternalTransfer", True),
            ("permitsUniversalTransfer", True),
            ("enableFutures", False),
        ],
    )
    def test_moi_co_sai_la_mot_ly_do_rieng(self, truong, gia_tri_sai) -> None:
        kq = danh_gia_quyen_key({**DAT, truong: gia_tri_sai})
        assert not kq.duoc_bat
        assert len(kq.ly_do_tu_choi) == 1 and f"`{truong}`" in kq.ly_do_tu_choi[0]

    @pytest.mark.parametrize("truong", ["ipRestrict", "enableWithdrawals", "enableFutures"])
    def test_thieu_truong_thi_tu_choi(self, truong) -> None:
        du_lieu = {k: v for k, v in DAT.items() if k != truong}
        kq = danh_gia_quyen_key(du_lieu)
        assert not kq.duoc_bat and "thiếu trường" in kq.ly_do_tu_choi[0]

    @pytest.mark.parametrize("gia_tri", ["false", 0, None, "False"])
    def test_khong_phai_bool_thi_tu_choi_khong_doan(self, gia_tri) -> None:
        """Chuỗi "false" là truthy trong Python — đọc lỏng thì `ipRestrict="false"` sẽ lọt qua như `True`."""
        kq = danh_gia_quyen_key({**DAT, "ipRestrict": gia_tri})
        assert not kq.duoc_bat and "không phải bool" in kq.ly_do_tu_choi[0]

    def test_gom_het_ly_do_khong_dung_o_ly_do_dau(self) -> None:
        kq = danh_gia_quyen_key({**DAT, "ipRestrict": False, "enableWithdrawals": True})
        assert len(kq.ly_do_tu_choi) == 2

    @pytest.mark.parametrize("du_lieu", [[], "ok", None, 1])
    def test_khong_phai_object_json_thi_tu_choi(self, du_lieu) -> None:
        assert not danh_gia_quyen_key(du_lieu).duoc_bat


class TestKiemTruocKhiBat:
    def test_dat_thi_tra_ket_qua(self) -> None:
        kq = kiem_truoc_khi_bat(api_key="k", api_secret="s", goi_fn=lambda **_: DAT)
        assert kq.duoc_bat

    def test_khong_dat_thi_raise_liet_ke_ly_do(self) -> None:
        with pytest.raises(BaoMatD10Error, match="ipRestrict"):
            kiem_truoc_khi_bat(api_key="k", api_secret="s", goi_fn=lambda **_: {**DAT, "ipRestrict": False})

    @pytest.mark.parametrize("loi", [BinancePrivateApiError("-2015 Invalid API-key, IP"), TimeoutError(), ValueError()])
    def test_moi_loi_doc_deu_tu_choi_fail_closed(self, loi) -> None:
        def no(**_):
            raise loi

        with pytest.raises(BaoMatD10Error, match="không đọc được"):
            kiem_truoc_khi_bat(api_key="k", api_secret="s", goi_fn=no)


def _tt(**ghi_de) -> TrangThaiD10:
    goc = dict(
        so_vi_the_da_mo=0,
        so_vi_the_dang_mo=0,
        moc_vi_the_dau=None,
        so_su_kien_doi_sl=0,
        ky_quy_dang_mo=0.0,
        so_du=200.0,
    )
    goc.update(ghi_de)
    return TrangThaiD10(**goc)


class TestNganSachViTheMoi:
    def test_trang_thai_dau_tien_duoc_mo(self) -> None:
        assert xet_vi_the_moi(_tt(), ky_quy_lenh=10.0, now=T0) == ()

    def test_du_20_vi_the_thi_tu_choi(self) -> None:
        ly_do = xet_vi_the_moi(_tt(so_vi_the_da_mo=TRAN_VI_THE, moc_vi_the_dau=T0), ky_quy_lenh=10.0, now=T0)
        assert any("hết ngân sách" in x for x in ly_do)

    def test_19_vi_the_van_duoc_mo(self) -> None:
        tt = _tt(so_vi_the_da_mo=TRAN_VI_THE - 1, moc_vi_the_dau=T0)
        assert xet_vi_the_moi(tt, ky_quy_lenh=10.0, now=T0 + timedelta(days=1)) == ()

    def test_con_vi_the_dang_mo_thi_tu_choi_tuan_tu(self) -> None:
        ly_do = xet_vi_the_moi(_tt(so_vi_the_da_mo=1, so_vi_the_dang_mo=1, moc_vi_the_dau=T0), ky_quy_lenh=10.0, now=T0)
        assert any("TUẦN TỰ" in x for x in ly_do)

    def test_du_30_su_kien_thi_dung_som(self) -> None:
        tt = _tt(so_vi_the_da_mo=5, moc_vi_the_dau=T0, so_su_kien_doi_sl=DU_SU_KIEN_DOI_SL)
        assert any("dừng sớm" in x for x in xet_vi_the_moi(tt, ky_quy_lenh=10.0, now=T0))


class TestCuaSo:
    def test_chua_co_vi_the_thi_cua_so_chua_bat_dau(self) -> None:
        assert han_chot(_tt()) is None

    def test_chua_du_mau_thi_gia_han_dung_mot_lan(self) -> None:
        assert han_chot(_tt(so_vi_the_da_mo=3, moc_vi_the_dau=T0)) == T0 + timedelta(days=28)

    def test_du_ca_hai_thi_khong_gia_han(self) -> None:
        tt = _tt(so_vi_the_da_mo=TRAN_VI_THE, so_su_kien_doi_sl=DU_SU_KIEN_DOI_SL, moc_vi_the_dau=T0)
        assert han_chot(tt) == T0 + timedelta(days=14)

    def test_trong_han_gia_han_duoc_mo(self) -> None:
        tt = _tt(so_vi_the_da_mo=3, moc_vi_the_dau=T0)
        assert xet_vi_the_moi(tt, ky_quy_lenh=10.0, now=T0 + timedelta(days=20)) == ()

    def test_het_han_thi_tu_choi(self) -> None:
        tt = _tt(so_vi_the_da_mo=3, moc_vi_the_dau=T0)
        ly_do = xet_vi_the_moi(tt, ky_quy_lenh=10.0, now=T0 + timedelta(days=28))
        assert any("hết cửa sổ" in x for x in ly_do)


class TestTranKyQuy:
    def test_dung_50_phan_tram_van_duoc(self) -> None:
        assert xet_vi_the_moi(_tt(so_du=200.0), ky_quy_lenh=100.0, now=T0) == ()

    def test_vuot_50_phan_tram_thi_tu_choi(self) -> None:
        ly_do = xet_vi_the_moi(_tt(so_du=200.0), ky_quy_lenh=100.01, now=T0)
        assert any("50%" in x for x in ly_do)

    @pytest.mark.parametrize("so_du", [None, math.nan, 0.0, -5.0, math.inf])
    def test_so_du_khong_doc_duoc_thi_tu_choi(self, so_du) -> None:
        # Kiểm ĐÚNG lý do "không đọc được", không chỉ chữ "số dư": câu vượt trần ký quỹ cũng chứa "số dư", nên kiểm
        # lỏng thì so_du=0 / -5 xanh vì lý do SAI (phá thật M5 lộ ra, 25/09/2026).
        assert any("số dư không đọc được" in x for x in xet_vi_the_moi(_tt(so_du=so_du), ky_quy_lenh=1.0, now=T0))

    @pytest.mark.parametrize("ky_quy", [math.nan, -1.0, math.inf])
    def test_ky_quy_khong_hop_le_thi_tu_choi(self, ky_quy) -> None:
        assert any("ký quỹ" in x for x in xet_vi_the_moi(_tt(), ky_quy_lenh=ky_quy, now=T0))


class TestThemTranche:
    def test_vi_the_dang_mo_khong_chan_tranche_cua_chinh_no(self) -> None:
        tt = _tt(so_vi_the_da_mo=1, so_vi_the_dang_mo=1, moc_vi_the_dau=T0, ky_quy_dang_mo=10.0)
        assert xet_them_tranche(tt, ky_quy_them=10.0, now=T0 + timedelta(hours=1)) == ()

    def test_tranche_van_chiu_tran_ky_quy(self) -> None:
        tt = _tt(so_vi_the_da_mo=1, so_vi_the_dang_mo=1, moc_vi_the_dau=T0, ky_quy_dang_mo=95.0, so_du=200.0)
        assert any("50%" in x for x in xet_them_tranche(tt, ky_quy_them=10.0, now=T0))

    def test_tranche_dung_khi_da_du_su_kien(self) -> None:
        tt = _tt(so_vi_the_da_mo=4, so_vi_the_dang_mo=1, moc_vi_the_dau=T0, so_su_kien_doi_sl=DU_SU_KIEN_DOI_SL)
        assert any("dừng sớm" in x for x in xet_them_tranche(tt, ky_quy_them=1.0, now=T0))
