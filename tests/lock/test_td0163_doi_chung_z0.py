"""🔴 TD-0163 — DR-015 Bước 3: đối chứng âm Z0 (BẮT BUỘC).

Bước này quyết định tính CÔNG BẰNG của §4: quy tắc phân xử trừ/cộng Δ_R
vào **mọi arm DCA** và không đụng Z0. Phép hiệu chỉnh bất đối xứng đó chỉ
chính đáng nếu sai số thước thật sự đặc thù của tranche 2+.

Hai thứ bộ test canh chặt nhất:

1. **Không được viết lại phép tính của TD-0161.** Có ca ghim việc dùng
   lại hàm nội bộ — chép công thức sang module này sẽ tạo nguồn sự thật
   thứ hai, hai bản trôi lệch, và "đối chứng" hoá ra so hai THƯỚC khác
   nhau chứ không so hai NHÁNH.
2. **Phải có vế `chi_z0_lech`.** Spec chỉ liệt kê hai vế ("tương đương",
   "chỉ DCA lệch"). Nếu dữ liệu cho thấy Z0 lệch NHIỀU HƠN thì giả thuyết
   nền của DR-015 bị bác — không có chỗ ghi kết cục đó nghĩa là ép nó vào
   một trong hai vế còn lại, tức giấu một phát hiện ngược.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from tool_d.dr015.buoc1_lech_tranche import Buoc1Error, tinh_buoc1
from tool_d.dr015.buoc3_doi_chung_z0 import (
    BIEN_TUONG_DUONG,
    KetQuaDoiChung,
    phan_xu,
    tinh_doi_chung,
)
from tool_d.measurement.tri_state import Measured

REPO_ROOT = Path(__file__).resolve().parents[2]
DU_LIEU = json.loads(
    (REPO_ROOT / "docs/du-lieu-do/dr015-luot-khop-tranche.json").read_text(encoding="utf-8")
)


def _kq(nhanh: str, delta: float | None, n: int = 35) -> KetQuaDoiChung:
    return KetQuaDoiChung(
        nhanh=nhanh,
        huong="LONG",
        so_lenh=n,
        lech_moi_lenh=(),
        delta_r=Measured.ok(delta) if delta is not None else Measured.unreadable("chưa đo"),
        dung_p90=n >= 30,
    )


class TestDungLaiPhepTinhCuaTD0161:
    """🔴 Nguồn sự thật DUY NHẤT cho `lệch_R`."""

    def test_delta_r_cua_DCA_KHOP_CHINH_XAC_TD_0161(self) -> None:
        """Nếu số này lệch dù chỉ ở chữ số thứ 12 thì hai module đang tính
        bằng hai công thức khác nhau, và mọi so sánh sau đó vô nghĩa."""
        dca = tinh_doi_chung(DU_LIEU)["DCA"].delta_r.value
        assert dca == pytest.approx(tinh_buoc1(DU_LIEU)["LONG"].delta_r.value, abs=1e-12)

    def test_dung_dung_ham_noi_bo_cua_TD_0161_khong_chep_lai(self) -> None:
        import inspect

        import tool_d.dr015.buoc3_doi_chung_z0 as mod

        src = inspect.getsource(mod)
        for ten in ("_planned_risk_usdt", "_uoc_luong_cost_tranche", "_gia_ke_hoach_ca_ba_tranche", "_p90"):
            assert f"from tool_d.dr015.buoc1_lech_tranche import" in src or ten in src
        # và KHÔNG định nghĩa lại chúng
        assert "def _planned_risk_usdt" not in src
        assert "def _p90" not in src


class TestDoiChungTrenDuLieuThat:
    def test_hai_nhanh_cung_so_lenh_va_cung_mau_so(self) -> None:
        """Cùng 35 trade, cùng `planned_risk_usdt` — nếu số lệnh lệch nhau
        thì hai nhánh đang được đo trên hai tập khác nhau."""
        dc = tinh_doi_chung(DU_LIEU)
        assert dc["Z0"].so_lenh == dc["DCA"].so_lenh == 35

    def test_ca_hai_dung_P90_vi_n_du_30(self) -> None:
        dc = tinh_doi_chung(DU_LIEU)
        assert dc["Z0"].dung_p90 and dc["DCA"].dung_p90

    def test_khong_dung_ra_nhanh_SHORT_rong_cho_bang_can_doi(self) -> None:
        """N6: chưa có lệnh Short thì không bịa ra một nhánh Short."""
        assert set(tinh_doi_chung(DU_LIEU)) == {"Z0", "DCA"}

    def test_du_lieu_khong_co_LONG_thi_raise(self) -> None:
        rong = {"luot_khop": [dict(r, huong="short") for r in DU_LIEU["luot_khop"]]}
        with pytest.raises(Buoc1Error, match="LONG"):
            tinh_doi_chung(rong)


class TestPhanXuBaVe:
    def test_tuong_duong_khi_ti_le_trong_bien(self) -> None:
        px = phan_xu({"Z0": _kq("Z0", 0.10), "DCA": _kq("DCA", 0.15)})
        assert px.ket_luan == "tuong_duong"
        assert "TRIỆT TIÊU" in px.dien_giai

    def test_chi_dca_lech_khi_vuot_bien(self) -> None:
        px = phan_xu({"Z0": _kq("Z0", 0.05), "DCA": _kq("DCA", 0.50)})
        assert px.ket_luan == "chi_dca_lech"
        assert "CHÍNH ĐÁNG" in px.dien_giai

    def test_chi_z0_lech_KHI_NGUOC_gia_thuyet_nen(self) -> None:
        """🔴 Vế spec KHÔNG liệt kê. Z0 lệch nhiều hơn nghĩa là giả thuyết
        'sai số cộng dồn theo số tranche' bị dữ liệu bác — phải ghi được,
        không được ép vào hai vế kia."""
        px = phan_xu({"Z0": _kq("Z0", 0.50), "DCA": _kq("DCA", 0.05)})
        assert px.ket_luan == "chi_z0_lech"
        assert "NGƯỢC" in px.dien_giai and "phạt nhầm" in px.dien_giai

    def test_thieu_delta_thi_KHONG_ket_luan_tuong_duong_suong(self) -> None:
        """Thiếu dữ liệu KHÁC với 'đã đo và thấy tương đương'. Gộp hai cái
        là biến một ô trống thành một kết luận."""
        px = phan_xu({"Z0": _kq("Z0", None), "DCA": _kq("DCA", 0.15)})
        assert px.ty_le_dca_tren_z0.status.value == "unreadable"
        assert "KHÔNG được coi là" in px.dien_giai

    def test_z0_bang_0_khong_chia_cho_0(self) -> None:
        px = phan_xu({"Z0": _kq("Z0", 0.0), "DCA": _kq("DCA", 0.15)})
        assert px.ket_luan == "chi_dca_lech"
        assert px.ty_le_dca_tren_z0.status.value == "unreadable"

    def test_CA_HAI_bang_0_la_tuong_duong_khong_phai_chi_dca_lech(self) -> None:
        """🔴 TD-0167 — lỗ hổng do rà soát độc lập bắt được.

        Bản đầu chỉ kiểm `z0.value == 0` rồi trả thẳng `chi_dca_lech` kèm
        câu "Z0 không lệch chút nào còn DCA có lệch". Nếu DCA CŨNG bằng 0
        thì câu đó SAI SỰ THẬT, và nó nằm đúng chỗ người đọc dùng để quyết
        định có áp Δ_R lên DCA hay không.

        Ca `z0=0, dca=0.15` ở test trên KHÔNG lộ ra lỗ này — đó là lý do
        một phép kiểm "đã có" vẫn có thể bỏ sót đúng nhánh cần canh.
        """
        px = phan_xu({"Z0": _kq("Z0", 0.0), "DCA": _kq("DCA", 0.0)})
        assert px.ket_luan == "tuong_duong"
        assert px.ty_le_dca_tren_z0.status.value == "unreadable"  # 0/0 vẫn không xác định
        assert "CẢ HAI" in px.dien_giai
        assert "còn DCA có lệch" not in px.dien_giai

    def test_bien_tuong_duong_doi_xung_hai_chieu(self) -> None:
        """Biên phải đối xứng theo tỉ lệ: gấp 2 lần và bằng 1/2 lần đều là
        'lệch', không được nghiêng về một phía."""
        assert BIEN_TUONG_DUONG > 1
        tren = phan_xu({"Z0": _kq("Z0", 1.0), "DCA": _kq("DCA", BIEN_TUONG_DUONG * 1.01)})
        duoi = phan_xu({"Z0": _kq("Z0", BIEN_TUONG_DUONG * 1.01), "DCA": _kq("DCA", 1.0)})
        assert tren.ket_luan == "chi_dca_lech" and duoi.ket_luan == "chi_z0_lech"


class TestKetQuaThat:
    """Ghim kết luận THẬT trên dữ liệu thật. Nếu ai đổi phép tính mà quên
    cập nhật kết luận ở research-log/TASKS thì ca này đỏ."""

    def test_ket_luan_that_la_TUONG_DUONG(self) -> None:
        px = phan_xu(tinh_doi_chung(DU_LIEU))
        assert px.ket_luan == "tuong_duong"
        assert px.ty_le_dca_tren_z0.value == pytest.approx(1.04, abs=0.05)
