"""🔴 L-Z47 + ghép fold bằng NHÂN (TD-0142) — hai trong chín bug có
thật của Tool A mà spec dòng 4340 bắt H3-D phải có test chống lại.

  L-Z47 (spec dòng 2798): `starting_balance + Σ pnl_abs == final_balance`
  từng fold, sai số < 0,01 USDT.

  Ghép fold (DR-013, spec dòng 2708-2710): đường vốn liên tục dựng bằng
  **NHÂN hệ số**, KHÔNG cộng `pnl_abs` xuyên fold.

🔴 Ca có răng nhất ở đây là `TestNhanKhongPhaiCong`. Nó dựng số sao cho
CỘNG và NHÂN ra hai kết quả CÁCH XA nhau (2.500 vs 3.000) — vì trên lãi/
lỗ nhỏ hai phép này gần như trùng nhau, nên một bộ test dùng số hiền sẽ
xanh cả khi code cộng nhầm. Bug chỉ lộ đúng lúc có fold biến động mạnh,
tức đúng lúc con số quan trọng nhất.
"""

from __future__ import annotations

import pytest

from tool_d.wfo.equity import (
    DUNG_SAI_CAN_DOI_USDT,
    CanDoiFoldError,
    FoldEquity,
    ghep_duong_von,
    he_so_tong,
    kiem_can_doi_fold,
)


def _fold(chi_so: int, start: float, pnl: tuple[float, ...]) -> FoldEquity:
    """Fold cân đối theo đúng định nghĩa — dùng cho ca hợp lệ."""
    return FoldEquity(
        chi_so=chi_so, starting_balance=start, final_balance=start + sum(pnl), pnl_abs=pnl
    )


class TestLZ47CanDoiTungFold:
    def test_fold_can_doi_thi_khong_raise(self) -> None:
        kiem_can_doi_fold(_fold(1, 1000.0, (120.5, -40.25, 33.75)))

    def test_lech_duoi_dung_sai_thi_chap_nhan(self) -> None:
        # Làm tròn dấu phẩy động tích luỹ qua vài trăm lệnh là bình thường.
        f = FoldEquity(1, 1000.0, 1100.0 + 0.009, (100.0,))
        kiem_can_doi_fold(f)

    def test_lech_vuot_dung_sai_thi_RAISE(self) -> None:
        # 🔴 KHÔNG kiểm đúng tại mốc `1100 + DUNG_SAI` — bản đầu của test
        # này làm vậy và ĐỎ: `(1100.0 + 0.01) - 1100.0` ra
        # 0,009999999999990905 chứ không phải 0,01, nên `>=` không kích
        # hoạt. Đó là hành vi đúng của dấu phẩy động, không phải lỗi
        # module. Kiểm sát mốc một ngưỡng float là kiểm chính sai số biểu
        # diễn, không kiểm luật — nên lấy giá trị vượt rõ ràng.
        f = FoldEquity(1, 1000.0, 1100.0 + 5 * DUNG_SAI_CAN_DOI_USDT, (100.0,))
        with pytest.raises(CanDoiFoldError, match="KHÔNG cân đối"):
            kiem_can_doi_fold(f)

    def test_bo_sot_mot_lenh_thi_bi_bat(self) -> None:
        """Đây là điều L-Z47 sinh ra để bắt: bộ chạy báo số dư cuối không
        giải thích được bằng chính các lệnh nó liệt kê."""
        f = FoldEquity(1, 1000.0, 1250.0, (100.0, 150.0, 90.0))  # thừa 90 trong list
        with pytest.raises(CanDoiFoldError, match="KHÔNG cân đối"):
            kiem_can_doi_fold(f)

    @pytest.mark.parametrize("start", [0.0, -100.0])
    def test_starting_balance_khong_duong_thi_raise(self, start: float) -> None:
        with pytest.raises(CanDoiFoldError, match="starting_balance"):
            kiem_can_doi_fold(FoldEquity(1, start, start, ()))

    def test_fold_khong_co_lenh_nao_van_can_doi(self) -> None:
        # Fold không sinh lệnh nào là kết quả HỢP LỆ (và với 19-47 lệnh/
        # fold theo DR-D3-01 thì không phải chuyện lạ) — không được raise.
        kiem_can_doi_fold(FoldEquity(1, 1000.0, 1000.0, ()))


class TestNhanKhongPhaiCong:
    """🔴 Ca cốt lõi — bug Tool A số (6)."""

    # fold 1: 1000 -> 2000 (hệ số 2,0) · fold 2: 1000 -> 1500 (hệ số 1,5)
    # NHÂN : 1000 × 2,0 × 1,5 = 3000   ✅ đúng
    # CỘNG : 1000 + 1000 + 500 = 2500  ❌ sai
    FOLDS = (_fold(1, 1000.0, (1000.0,)), _fold(2, 1000.0, (500.0,)))

    def test_ghep_bang_NHAN_ra_3000_khong_phai_2500(self) -> None:
        duong = ghep_duong_von(self.FOLDS, von_ban_dau=1000.0)
        assert duong == pytest.approx((1000.0, 2000.0, 3000.0))
        # Nói thẳng ra con số của cách CỘNG để ai đọc test cũng thấy hai
        # cách khác nhau bao nhiêu, thay vì chỉ thấy một số đúng.
        cong_sai = 1000.0 + sum(f.tong_pnl_abs for f in self.FOLDS)
        assert cong_sai == pytest.approx(2500.0)
        assert duong[-1] != pytest.approx(cong_sai)

    def test_moi_fold_reset_von_nen_he_so_moi_la_dai_luong_so_sanh_duoc(self) -> None:
        # Cả hai fold đều khởi điểm 1000 (bộ chạy tự reset vốn) — lãi fold 1
        # KHÔNG chảy vào vốn khởi điểm fold 2.
        assert self.FOLDS[0].starting_balance == self.FOLDS[1].starting_balance
        assert self.FOLDS[0].he_so == pytest.approx(2.0)
        assert self.FOLDS[1].he_so == pytest.approx(1.5)

    def test_fold_lo_lam_duong_von_co_lai(self) -> None:
        folds = (_fold(1, 1000.0, (-500.0,)), _fold(2, 1000.0, (200.0,)))
        duong = ghep_duong_von(folds, von_ban_dau=1000.0)
        assert duong == pytest.approx((1000.0, 500.0, 600.0))  # 500 × 1,2

    def test_he_so_tong_la_tich_cac_he_so(self) -> None:
        assert he_so_tong(self.FOLDS) == pytest.approx(2.0 * 1.5)

    def test_thu_tu_fold_doi_thi_duong_von_giua_doi_theo(self) -> None:
        """Vì sao phải chặn thứ tự sai: tích cuối cùng KHÔNG đổi (phép nhân
        giao hoán) nên một danh sách sai thứ tự vẫn cho tổng trông hợp lý —
        chỉ các điểm GIỮA là bịa. Đó là lý do `ghep_duong_von()` từ chối
        thay vì tự sắp xếp."""
        dao = (
            FoldEquity(1, 1000.0, 1500.0, (500.0,)),
            FoldEquity(2, 1000.0, 2000.0, (1000.0,)),
        )
        duong = ghep_duong_von(dao, von_ban_dau=1000.0)
        assert duong[-1] == pytest.approx(3000.0)  # tổng giống hệt
        assert duong[1] == pytest.approx(1500.0)  # nhưng điểm giữa khác 2000


class TestGhepFoldFailClosed:
    def test_danh_sach_rong_thi_raise(self) -> None:
        with pytest.raises(CanDoiFoldError, match="Không có fold"):
            ghep_duong_von((), von_ban_dau=1000.0)

    def test_von_ban_dau_khong_duong_thi_raise(self) -> None:
        with pytest.raises(CanDoiFoldError, match="von_ban_dau"):
            ghep_duong_von((_fold(1, 1000.0, (10.0,)),), von_ban_dau=0.0)

    @pytest.mark.parametrize("chi_so", [(1, 3), (2, 1), (0, 1), (1, 1)])
    def test_chi_so_khong_phai_day_1_k_thi_RAISE_khong_tu_sap_xep(
        self, chi_so: tuple[int, int]
    ) -> None:
        folds = (_fold(chi_so[0], 1000.0, (100.0,)), _fold(chi_so[1], 1000.0, (100.0,)))
        with pytest.raises(CanDoiFoldError, match="liên tiếp"):
            ghep_duong_von(folds, von_ban_dau=1000.0)

    def test_fold_chua_can_doi_thi_khong_duoc_ghep(self) -> None:
        # Ghép một fold chưa cân đối = nhân một số đã biết là sai vào toàn
        # bộ phần đuôi đường vốn.
        hong = FoldEquity(1, 1000.0, 9999.0, (100.0,))
        with pytest.raises(CanDoiFoldError, match="KHÔNG cân đối"):
            ghep_duong_von((hong,), von_ban_dau=1000.0)

    def test_tai_khoan_chay_thi_TU_CHOI_ghep_tiep(self) -> None:
        """`final_balance <= 0`: hệ số <= 0 nhân vào sẽ làm đổi dấu mọi
        điểm phía sau và cho ra đường vốn vô nghĩa."""
        chay = FoldEquity(1, 1000.0, -50.0, (-1050.0,))
        with pytest.raises(CanDoiFoldError, match="cháy"):
            ghep_duong_von((chay, _fold(2, 1000.0, (100.0,))), von_ban_dau=1000.0)

    def test_tra_ve_du_k_cong_1_diem_ke_ca_diem_dau(self) -> None:
        folds = tuple(_fold(i, 1000.0, (100.0,)) for i in range(1, 4))
        assert len(ghep_duong_von(folds, von_ban_dau=1000.0)) == len(folds) + 1


class TestLZ46PhuLuonModuleMoi:
    def test_module_wfo_nam_trong_pham_vi_quet_LZ46(self) -> None:
        """`L-Z46` quét `src/**/*.py` bằng rglob nên `wfo/equity.py` tự
        động được phủ — ca này khoá điều đó lại, để nếu ai thu hẹp phạm
        vi quét của L-Z46 thì có test đỏ chỉ đúng chỗ."""
        # `tests/` không phải package (không có __init__.py) nên
        # `import tests.lock...` không chạy — nạp theo đường dẫn file.
        import importlib.util
        from pathlib import Path

        duong_dan = Path(__file__).with_name("test_lz46_profit_ratio_banned.py")
        spec = importlib.util.spec_from_file_location("lz46_module", duong_dan)
        assert spec and spec.loader
        lz46 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(lz46)

        assert "src" in lz46.SCAN_DIRS
        files = {p.name for p in lz46._python_files()}
        assert "equity.py" in files and "folds.py" in files
