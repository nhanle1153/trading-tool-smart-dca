"""🔒 TD-0282 — `gates/cscv.py::tinh_pbo()` (`DR-D9-01` §4).

Mọi đáp án dưới đây TÍNH TAY từ định nghĩa, không chạy hàm rồi chép kết quả
vào — chép lại đầu ra là ghim hành vi hiện tại, không kiểm đúng/sai.

Dữ liệu dựng: mỗi khối một ngày, mỗi lệnh một số `r_trien_khai`. Ký hiệu
`A=[3,3,0,0]` = cấu hình A có một lệnh mỗi khối với các trị đó.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import datetime, timedelta

import pytest

from tool_d.gates.cscv import CSCVError, tinh_pbo
from tool_d.gates.cscv_cau_hinh import CauHinhCSCV
from tool_d.measurement.tri_state import Status

T1 = datetime(2025, 1, 1)


@dataclass(frozen=True)
class Lenh:
    open_date: datetime
    r_trien_khai: float


def _ch(so_khoi: int = 4, san: int = 1, gio: int = 24) -> CauHinhCSCV:
    L = timedelta(hours=gio)
    return CauHinhCSCV(
        so_khoi=so_khoi, do_dai_khoi=L, san_lenh_moi_nua=san, pbo_max=0.5,
        t1=T1, t2=T1 + so_khoi * L, bam_dr="test",
    )


def _cau_hinh(tri: list[float], *, gio_trong_khoi: int = 1) -> list[Lenh]:
    """Một lệnh mỗi khối (khối dài 24 giờ)."""
    return [Lenh(T1 + timedelta(days=b, hours=gio_trong_khoi), v) for b, v in enumerate(tri)]


class TestDapAnTinhTay:
    def test_is_best_luon_doi_so_oos_thi_pbo_bang_1(self) -> None:
        """A=[0,1,2,5] (trung bình 2), B=[2,2,2,2]. Không cặp khối nào của A có trung bình
        đúng 2 ⇒ không hoà. A_IS + A_OOS = 4 ⇒ A thắng IS đúng khi A thua OOS, và ngược lại.
        Mọi tổ hợp: IS-best xếp hạng 1/2 OOS ⇒ ω = 1/3 ⇒ λ = ln(1/2) < 0 ⇒ PBO = 6/6."""
        kq = tinh_pbo({"A": _cau_hinh([0, 1, 2, 5]), "B": _cau_hinh([2, 2, 2, 2])}, _ch())
        assert kq.pbo.status is Status.OK and kq.pbo.value == 1.0
        assert kq.so_to_hop == kq.so_to_hop_doc_duoc == 6
        assert all(math.isclose(t.lam, math.log(0.5)) for t in kq.to_hop)

    def test_thu_hang_ben_vung_thi_pbo_bang_0(self) -> None:
        """A tốt hơn B ở MỌI khối ⇒ IS-best = A, OOS hạng 2/2 ⇒ ω = 2/3 ⇒ λ = ln 2 > 0."""
        kq = tinh_pbo({"A": _cau_hinh([1, 1, 1, 1]), "B": _cau_hinh([0, 0, 0, 0])}, _ch())
        assert kq.pbo.value == 0.0
        assert all(math.isclose(t.lam, math.log(2)) for t in kq.to_hop)

    def test_ba_cau_hinh_tinh_tung_lambda_va_hoa_dinh(self) -> None:
        """A=[3,3,0,0], B=[0,0,3,3], C=[1,1,1,1]; N = 3 ⇒ ω = hạng/4.
        IS {0,1}: A thắng (3), OOS A=0 hạng 1 ⇒ λ = ln(1/3).
        IS {2,3}: B thắng, OOS B=0 hạng 1 ⇒ λ = ln(1/3).
        IS {0,2},{0,3},{1,2},{1,3}: A=B=1,5 HOÀ ĐỈNH; OOS A=B=1,5 > C=1 ⇒ hạng 2,5 cả hai
        ⇒ ω = 0,625 ⇒ λ = ln(5/3), trung bình hai cấu hình cùng đỉnh vẫn ln(5/3).
        PBO = 2/6."""
        kq = tinh_pbo(
            {"A": _cau_hinh([3, 3, 0, 0]), "B": _cau_hinh([0, 0, 3, 3]), "C": _cau_hinh([1, 1, 1, 1])},
            _ch(),
        )
        lam = {t.khoi_is: t.lam for t in kq.to_hop}
        assert math.isclose(lam[(0, 1)], -math.log(3)) and math.isclose(lam[(2, 3)], -math.log(3))
        for k in [(0, 2), (0, 3), (1, 2), (1, 3)]:
            assert math.isclose(lam[k], math.log(5 / 3)), k
        assert math.isclose(kq.pbo.value, 2 / 6)

    def test_hoa_dinh_lay_trung_binh_lambda_khong_chon_theo_ten(self) -> None:
        """IS {0,1}: A=B=2 hoà đỉnh. OOS {2,3}: A=4 (hạng 3/3), B=0 (hạng 1/3), C=1 (hạng 2).
        λ_A = ln(3), λ_B = ln(1/3) ⇒ trung bình 0 ⇒ tính là λ ≤ 0. Chọn theo tên (A) sẽ ra ln 3."""
        kq = tinh_pbo(
            {"A": _cau_hinh([2, 2, 4, 4]), "B": _cau_hinh([2, 2, 0, 0]), "C": _cau_hinh([1, 1, 1, 1])},
            _ch(),
        )
        lam = {t.khoi_is: t.lam for t in kq.to_hop}
        assert math.isclose(lam[(0, 1)], 0.0, abs_tol=1e-12)


class TestBaTrangThai:
    def test_duoi_san_moi_to_hop_thi_unreadable_khong_phai_0(self) -> None:
        kq = tinh_pbo({"A": _cau_hinh([0, 1, 2, 5]), "B": _cau_hinh([2, 2, 2, 2])}, _ch(san=3))
        assert kq.pbo.status is Status.UNREADABLE
        assert kq.pbo.value is None
        assert kq.so_to_hop_doc_duoc == 0

    def test_mot_phan_to_hop_duoi_san_thi_ca_pbo_unreadable(self) -> None:
        """C chỉ có lệnh ở khối 0,1 ⇒ tổ hợp OOS={0,1}… đủ, IS={0,1} thì OOS rỗng ⇒ dưới sàn.
        Có tổ hợp đọc được nhưng KHÔNG được tính PBO trên tập con (DR-D9-01 §4.4)."""
        c = [Lenh(T1 + timedelta(hours=1), 1.0), Lenh(T1 + timedelta(days=1, hours=1), 1.0)]
        kq = tinh_pbo({"A": _cau_hinh([0, 1, 2, 5]), "C": c}, _ch(san=1))
        assert 0 < kq.so_to_hop_doc_duoc < kq.so_to_hop
        assert kq.pbo.status is Status.UNREADABLE and "tổ hợp dưới sàn" in kq.pbo.note

    def test_gop_cau_hinh_trung_khit(self) -> None:
        """D ≡ A từng lệnh ⇒ gộp; kết quả như chỉ có A, B, C."""
        a = _cau_hinh([3, 3, 0, 0])
        co_d = tinh_pbo(
            {"A": a, "D": list(reversed(a)), "B": _cau_hinh([0, 0, 3, 3]), "C": _cau_hinh([1, 1, 1, 1])}, _ch()
        )
        assert co_d.cau_hinh_gop_trung == (("A", "D"),)
        assert co_d.so_cau_hinh_dau_vao == 4 and co_d.so_cau_hinh_phan_biet == 3
        assert math.isclose(co_d.pbo.value, 2 / 6)

    def test_duoi_hai_cau_hinh_phan_biet_thi_unreadable(self) -> None:
        a = _cau_hinh([1, 2, 3, 4])
        kq = tinh_pbo({"A": a, "A2": list(a)}, _ch())
        assert kq.so_cau_hinh_phan_biet == 1
        assert kq.pbo.status is Status.UNREADABLE


class TestTuChoiDauVao:
    @pytest.mark.parametrize("od", [T1 - timedelta(seconds=1), T1 + timedelta(days=4)])
    def test_lenh_ngoai_cua_so_raise(self, od: datetime) -> None:
        with pytest.raises(CSCVError, match="ngoài"):
            tinh_pbo({"A": [Lenh(od, 1.0)], "B": _cau_hinh([1, 1, 1, 1])}, _ch())

    @pytest.mark.parametrize("xau", [math.nan, math.inf, "1.0", True])
    def test_tri_so_khong_huu_han_raise(self, xau) -> None:
        with pytest.raises(CSCVError, match="hữu hạn"):
            tinh_pbo({"A": [Lenh(T1, xau)], "B": _cau_hinh([1, 1, 1, 1])}, _ch())

    def test_so_khoi_le_raise(self) -> None:
        with pytest.raises(CSCVError, match="chẵn"):
            tinh_pbo({"A": _cau_hinh([1, 2, 3])}, _ch(so_khoi=3))

    def test_cua_so_khong_bang_so_khoi_nhan_do_dai(self) -> None:
        ch = _ch()
        hong = CauHinhCSCV(**{**ch.__dict__, "t2": ch.t2 + timedelta(hours=1)})
        with pytest.raises(CSCVError):
            tinh_pbo({"A": _cau_hinh([1, 2, 3, 4])}, hong)

    def test_bien_khoi_nua_mo(self) -> None:
        """Lệnh đúng mốc 24:00 thuộc khối 1, không thuộc khối 0."""
        a = [Lenh(T1 + timedelta(days=b), v) for b, v in enumerate([0, 1, 2, 5])]
        kq = tinh_pbo({"A": a, "B": _cau_hinh([2, 2, 2, 2])}, _ch())
        assert kq.pbo.value == 1.0  # cùng đáp án ca PBO = 1 ⇒ gán khối không lệch một


class TestQuyMoThat:
    def test_s8_ra_70_to_hop_va_pbo_trong_doan(self) -> None:
        ch = _ch(so_khoi=8, san=30, gio=693)
        rng = random.Random(20260917)
        lenh = {
            f"cfg{k}": [
                Lenh(T1 + timedelta(hours=rng.randrange(0, 8 * 693)), rng.gauss(0.05 * k, 1.0))
                for _ in range(400)
            ]
            for k in range(6)
        }
        kq = tinh_pbo(lenh, ch)
        assert kq.so_to_hop == 70 == kq.so_to_hop_doc_duoc
        assert kq.pbo.status is Status.OK and 0.0 <= kq.pbo.value <= 1.0
