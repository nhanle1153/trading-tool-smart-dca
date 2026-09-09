"""🔒 TD-0199 — BA kết cục (`DR-D4-09` §2.2) và phép so PAIRED (§2.1).

Điều đắt nhất mà bộ test này giữ **không phải một công thức** mà là một
phân biệt: *"đo được, không đạt"* (FAIL) khác *"không đo được"*
(INCONCLUSIVE). §10.2 hiện gộp cả hai thành "KHÔNG VÀO LIVE", và hậu quả
cụ thể của việc gộp là **bỏ DCA vĩnh viễn** dựa trên một phép đo không có
khả năng phát hiện mức hiệu ứng đang hỏi (`DR-D4-09` §4).

Bốn lớp: ba kết cục · biên giới giữa chúng · phép so paired (mẫu số phải
là `n_giao`) · fail-closed. Mỗi lớp kèm phép phá tương ứng.
"""

from __future__ import annotations

import math

import pytest

from tool_d.gates.dsr import dsr_hurdle
from tool_d.gates.ket_cuc import (
    KetCuc,
    KetCucError,
    phan_loai_ket_cuc,
    so_paired,
    thue_nhieu,
)

H = dsr_hurdle(114)  # 3,0777 — N_ĐĂNG_KÝ, DR-D0PRE-02


class TestThueNhieu:
    def test_dung_cong_thuc_cua_dsr_khong_chep_lai(self) -> None:
        """MT-03: một nguồn sự thật. Nếu ai đó chép `√(2·ln N)` vào module
        này thì hai bản sẽ trôi lệch khi N đổi — ca này neo chúng lại."""
        assert thue_nhieu(std_r=1.25, n_trades=40) == pytest.approx(H * 1.25 / math.sqrt(40))

    def test_giam_theo_can_bac_hai_cua_n(self) -> None:
        """Gấp 4 lần mẫu ⇒ thuế giảm đúng một nửa. Đây là lý do "thêm dữ
        liệu" không cứu được chênh lệch cỡ mẫu giữa các arm (DR-D4-09 §1.4)."""
        assert thue_nhieu(std_r=1.0, n_trades=40) == pytest.approx(
            2 * thue_nhieu(std_r=1.0, n_trades=160)
        )

    def test_n_qua_nho_hoac_std_am_thi_RAISE(self) -> None:
        for xau in ({"n_trades": 1}, {"n_trades": 0}, {"std_r": -0.1}, {"std_r": float("nan")}):
            with pytest.raises(KetCucError):
                thue_nhieu(**{"std_r": 1.0, "n_trades": 40, **xau})


class TestBaKetCuc:
    NGUONG = 0.10  # DSR_ADJ_EXPECTANCY_MIN (DR-D0PRE-03)

    def test_PASS_khi_vuot_nguong_SAU_khi_tru_thue(self) -> None:
        r = phan_loai_ket_cuc(mean_r=0.60, std_r=1.0, n_trades=1000, nguong=self.NGUONG)
        assert r.ket_cuc is KetCuc.PASS

    def test_PASS_thang_ca_khi_thue_LON(self) -> None:
        """🔴 Thứ tự xét là bản chất: `DSR_adj` ĐÃ trừ thuế, nên vượt được là
        vượt *sau khi* đã trả giá cho N phép thử. Nếu ca này ra INCONCLUSIVE
        thì cơ chế bảo vệ đang chặn chính kết quả nó vừa xác nhận."""
        r = phan_loai_ket_cuc(mean_r=2.0, std_r=1.25, n_trades=40, nguong=self.NGUONG)
        assert r.thue > self.NGUONG and r.ket_cuc is KetCuc.PASS

    def test_INCONCLUSIVE_khi_thue_lon_hon_nguong(self) -> None:
        """n=40, std=1,25 — đúng cỡ mẫu THẬT của 7 arm nhóm C trên WFO
        (DR-D4-09 §1.1). Thuế 0,608 ≫ ngưỡng 0,10."""
        r = phan_loai_ket_cuc(mean_r=0.15, std_r=1.25, n_trades=40, nguong=self.NGUONG)
        assert r.ket_cuc is KetCuc.INCONCLUSIVE
        assert r.thue == pytest.approx(0.6079, abs=1e-3)

    def test_FAIL_khi_do_duoc_va_khong_dat(self) -> None:
        """Thuế nhỏ (mẫu lớn) mà vẫn không đạt ⇒ đây là bằng chứng CHỐNG,
        khác hẳn ca trên."""
        r = phan_loai_ket_cuc(mean_r=0.05, std_r=0.5, n_trades=5000, nguong=self.NGUONG)
        assert r.thue <= self.NGUONG and r.ket_cuc is KetCuc.FAIL

    def test_CUNG_mean_r_hai_ket_cuc_khac_nhau_chi_vi_n(self) -> None:
        """🔑 Ca quan trọng nhất file này: cùng một `mean_r` không đạt ngưỡng,
        nhưng n nhỏ ⇒ INCONCLUSIVE, n lớn ⇒ FAIL. Nếu hai ca này cho cùng kết
        cục thì phân biệt của DR-D4-09 đã biến mất."""
        nho = phan_loai_ket_cuc(mean_r=0.05, std_r=1.0, n_trades=40, nguong=self.NGUONG)
        lon = phan_loai_ket_cuc(mean_r=0.05, std_r=1.0, n_trades=5000, nguong=self.NGUONG)
        assert nho.ket_cuc is KetCuc.INCONCLUSIVE
        assert lon.ket_cuc is KetCuc.FAIL

    def test_bien_gioi_thue_bang_dung_nguong_la_FAIL(self) -> None:
        """`thuế > ngưỡng` mới INCONCLUSIVE — bằng đúng thì KHÔNG. Chọn chiều
        này vì nó bảo thủ: bằng nhau thì phép đo vừa đủ phân định."""
        n = 400
        std = 0.10 * math.sqrt(n) / H  # cho thuế == đúng 0,10
        r = phan_loai_ket_cuc(mean_r=0.0, std_r=std, n_trades=n, nguong=0.10)
        assert r.thue == pytest.approx(0.10) and r.ket_cuc is KetCuc.FAIL

    def test_NaN_thi_RAISE_khong_gop_vao_FAIL(self) -> None:
        """N6: 'chưa đo' KHÁC 'đo được và không đạt'. Trả FAIL ở đây là tái
        lập đúng lỗi mà cả DR-D4-09 sinh ra để chặn, chỉ ở tầng sâu hơn."""
        for xau in ({"mean_r": float("nan")}, {"nguong": float("nan")}):
            with pytest.raises(KetCucError):
                phan_loai_ket_cuc(**{"mean_r": 0.2, "std_r": 1.0, "n_trades": 40,
                                     "nguong": 0.10, **xau})

    def test_dien_giai_in_du_BA_con_so(self) -> None:
        """DR-D4-09 §2.3: `DSR_adj` đứng một mình không nói được 'edge yếu'
        hay 'chưa đủ mẫu'."""
        s = phan_loai_ket_cuc(mean_r=0.15, std_r=1.25, n_trades=40, nguong=0.10).dien_giai()
        assert "thuế nhiễu" in s and "n = 40" in s and "INCONCLUSIVE" in s


class TestSoPaired:
    def test_paired_thang_khi_hieu_on_dinh(self) -> None:
        """B hơn A đúng 0,30 R ở MỌI lệnh ⇒ std(d) = 0 ⇒ thuế = 0."""
        a = [0.1, -1.0, 0.5, 2.0, -1.0, 0.3]
        b = [x + 0.30 for x in a]
        r = so_paired(r_a=a, r_b=b, n_a=len(a), n_b=len(b), ty_le_vuot=0.20)
        assert r.ket_cuc is KetCuc.PASS
        assert r.std_hieu == pytest.approx(0.0) and r.thue == pytest.approx(0.0)
        assert r.rho == pytest.approx(1.0)

    def test_paired_LOI_HON_doc_lap_tren_cung_du_lieu(self) -> None:
        """🔑 Lý do tồn tại của §2.1: hai arm tương quan mạnh thì std của HIỆU
        nhỏ hơn hẳn std của từng arm ⇒ thuế nhiễu nhỏ hơn."""
        a = [0.5, -1.0, 1.5, -1.0, 0.8, -1.0, 2.0, 0.2]
        b = [x + 0.2 for x in a]
        r = so_paired(r_a=a, r_b=b, n_a=len(a), n_b=len(b), ty_le_vuot=0.20)
        std_a = math.sqrt(sum((x - sum(a) / len(a)) ** 2 for x in a) / (len(a) - 1))
        doc_lap = H * std_a * math.sqrt(2) / math.sqrt(len(a))
        assert r.thue < doc_lap / 10, (r.thue, doc_lap)

    def test_mau_so_la_n_giao_KHONG_phai_n_a(self) -> None:
        """🔴 Dùng `n_a` là khai một cỡ mẫu mà phép so không có."""
        a, b = [0.1, 0.2, 0.3, 0.4], [0.5, 0.6, 0.7, 0.9]
        r = so_paired(r_a=a, r_b=b, n_a=100, n_b=90, ty_le_vuot=0.20)
        assert r.n_giao == 4 and r.n_a == 100 and r.n_b == 90
        d = [y - x for x, y in zip(a, b)]
        md = sum(d) / 4
        sd = math.sqrt(sum((x - md) ** 2 for x in d) / 3)
        assert r.thue == pytest.approx(H * sd / math.sqrt(4))

    def test_n_giao_lon_hon_n_arm_thi_RAISE(self) -> None:
        with pytest.raises(KetCucError, match="n_giao"):
            so_paired(r_a=[0.1] * 5, r_b=[0.2] * 5, n_a=3, n_b=9, ty_le_vuot=0.20)

    def test_lech_do_dai_thi_RAISE_chua_ghep_cap(self) -> None:
        with pytest.raises(KetCucError, match="cùng độ dài"):
            so_paired(r_a=[0.1, 0.2], r_b=[0.2], n_a=2, n_b=1, ty_le_vuot=0.20)

    def test_INCONCLUSIVE_o_co_mau_THAT_cua_nhom_C(self) -> None:
        """n=40, hiệu nhiễu — đúng tình huống DR-D4-09 §4 dự báo."""
        import random

        rnd = random.Random(0)
        a = [rnd.gauss(0.10, 1.25) for _ in range(40)]
        b = [x + rnd.gauss(0.02, 1.0) for x in a]  # B hơn A đúng 20% của 0,10
        r = so_paired(r_a=a, r_b=b, n_a=40, n_b=40, ty_le_vuot=0.20)
        assert r.ket_cuc is KetCuc.INCONCLUSIVE, r.dien_giai()

    def test_ty_le_vuot_ngoai_khoang_thi_RAISE(self) -> None:
        """20% là 0.20, không phải 20 — cùng lớp lỗi đơn vị L-Z48c."""
        for xau in (20.0, 0.0, 1.0, -0.2):
            with pytest.raises(KetCucError, match="ty_le_vuot"):
                so_paired(r_a=[0.1] * 4, r_b=[0.2] * 4, n_a=4, n_b=4, ty_le_vuot=xau)

    def test_NaN_trong_R_thi_RAISE(self) -> None:
        with pytest.raises(KetCucError, match="NaN"):
            so_paired(r_a=[0.1, float("nan"), 0.3, 0.4], r_b=[0.2] * 4, n_a=4, n_b=4, ty_le_vuot=0.20)

    def test_hai_arm_phang_thi_rho_KHONG_bia_1(self) -> None:
        """Tương quan không xác định khi phương sai = 0 — trả 0.0 và nói ra
        qua `std_hieu`, không bịa 1.0 (N6)."""
        r = so_paired(r_a=[0.5] * 6, r_b=[0.5] * 6, n_a=6, n_b=6, ty_le_vuot=0.20)
        assert r.rho == 0.0 and r.std_hieu == pytest.approx(0.0)

    def test_dien_giai_in_n_giao_va_rho(self) -> None:
        s = so_paired(r_a=[0.1, 0.2, 0.3, 0.4], r_b=[0.3, 0.4, 0.5, 0.6],
                      n_a=10, n_b=12, ty_le_vuot=0.20).dien_giai()
        assert "n_giao 4" in s and "ρ" in s


class TestKhongThemThamSoNaoVaoDOF:
    def test_moc_INCONCLUSIVE_suy_tu_chinh_nguong(self) -> None:
        """DR-D4-09 §6 + §2.2: mốc là `thuế > ngưỡng của chính tiêu chí`, KHÔNG
        phải một hằng số riêng. Đổi ngưỡng ⇒ mốc đi theo; nếu có hằng số ẩn
        thì ca này đỏ."""
        cao = phan_loai_ket_cuc(mean_r=0.0, std_r=1.0, n_trades=100, nguong=0.50)
        thap = phan_loai_ket_cuc(mean_r=0.0, std_r=1.0, n_trades=100, nguong=0.01)
        assert cao.thue == thap.thue  # cùng thuế
        assert cao.ket_cuc is KetCuc.FAIL           # thuế 0,308 ≤ ngưỡng 0,50
        assert thap.ket_cuc is KetCuc.INCONCLUSIVE  # thuế 0,308 > ngưỡng 0,01

    def test_khong_hang_so_nguong_nao_trong_module(self) -> None:
        """AST-lite: module không được mang một ngưỡng của riêng nó."""
        import ast
        from pathlib import Path

        src = Path(__file__).resolve().parents[2] / "src/tool_d/gates/ket_cuc.py"
        cay = ast.parse(src.read_text(encoding="utf-8"))
        gan = [
            n for n in cay.body
            if isinstance(n, ast.Assign)
            and isinstance(getattr(n, "value", None), ast.Constant)
            and isinstance(n.value.value, float)
        ]
        assert not gan, f"module không được có hằng số ngưỡng riêng: {[ast.dump(g) for g in gan]}"
