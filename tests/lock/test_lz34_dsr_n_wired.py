"""L-Z34 🔴 CRITICAL — N KHÔNG PHẢI SỐ TRANG TRÍ (spec dòng 3940-3948).

Test tham số hoá: gọi hàm tính ngưỡng DSR với N=114 và N=228; hai đầu ra
PHẢI khác nhau và khớp √(2·ln N) trong sai số 1e-6. Đầu ra không đổi khi N
đổi → N đang nằm trong chú thích, không nằm trong phép tính.
"""

from __future__ import annotations

import math

import pytest

from tool_d.gates.dsr import N_DANG_KY, dsr_hurdle, effective_n


class TestDsrHurdleNNoiVaoPhepTinh:
    def test_n_114_va_228_ra_ket_qua_khac_nhau(self) -> None:
        h114 = dsr_hurdle(114)
        h228 = dsr_hurdle(228)
        assert h114 != h228, "N đổi mà kết quả không đổi -> N nằm trong chú thích, không trong phép tính"

    @pytest.mark.parametrize("n", [2, 10, 50, 114, 228, 1000])
    def test_khop_cong_thuc_can_2_ln_n_sai_so_1e6(self, n: int) -> None:
        assert dsr_hurdle(n) == pytest.approx(math.sqrt(2 * math.log(n)), abs=1e-6)

    def test_n_dang_ky_khop_dr_d0pre_02(self) -> None:
        # Hằng số N_DANG_KY phải khớp quyết định đã chốt (TD-0032) — nếu
        # ai đó sửa N_DANG_KY trong dsr.py mà không qua DR mới, test này bắt.
        assert N_DANG_KY == 114

    def test_gia_tri_thuc_te_n_114(self) -> None:
        # Spec (dòng 149, 3240) làm tròn 2 chữ số: "≈ 3.08". Giá trị chính
        # xác √(2·ln 114) ≈ 3.0777 — kiểm bằng làm tròn, không so trực
        # tiếp với "3.08" (đó là số đã làm tròn, không phải giá trị gốc).
        assert round(dsr_hurdle(114), 2) == 3.08


class TestFailClosed:
    def test_n_bang_1_thi_raise(self) -> None:
        with pytest.raises(ValueError):
            dsr_hurdle(1)

    def test_n_am_thi_raise(self) -> None:
        with pytest.raises(ValueError):
            dsr_hurdle(-5)

    def test_khong_bao_gio_tra_nan_hay_gia_tri_linh_canh(self) -> None:
        for n in (2, 114, 1000):
            result = dsr_hurdle(n)
            assert not math.isnan(result)
            assert result > 0


class TestEffectiveN:
    def test_truoc_live_bang_dung_n_dang_ky(self) -> None:
        assert effective_n() == 114
        assert effective_n(n_consumed_since_live=0) == 114

    def test_sau_live_cong_them_khong_thay_the(self) -> None:
        # §12c.2 "nuôi N sau live" — CỘNG THÊM vào N_ĐĂNG_KÝ, không thay thế nó.
        assert effective_n(n_consumed_since_live=25) == 139

    def test_am_thi_raise(self) -> None:
        with pytest.raises(ValueError):
            effective_n(n_consumed_since_live=-1)
