"""🔴 TD-0191 / DR-D4-07 — thang notional của arm đối chứng `Z0-S1`.

Trước bản này, `Z0-S1` nhận một con số USDT cứng (`notional_co_dinh_usdt`)
mà cấu hình để `null` ⇒ arm **raise** ⇒ backtest sinh ra **0 lệnh** trên 48
mã EXPLORE trong 22 tháng. Một arm không chạy được nghĩa là một suất trial
trong 114 mua thông tin bằng không.

Nay notional là **đại lượng dẫn xuất**: `rho_pct/100 × E_D / notional_ref_r_eff`.

🔑 **Tính chất chính bộ test này canh — và nó KHÔNG phải "giá trị hiện tại
đúng bằng 93,75".** Một test ghim con số hiện tại sẽ **vẫn xanh** nếu ai đó
quay lại một hằng số USDT cứng bằng 93,75, tức nó không canh được đúng thứ
DR-D4-07 sinh ra để bảo vệ. Tính chất thật là **quan hệ**:

  (a) notional **PHẢI đổi khi `E_D` đổi** — đây là toàn bộ lý do chọn công
      thức thay vì con số. `E_D` vừa đi 500 → 750; một số cứng chọn hồi 500
      sẽ tự đổi ý nghĩa arm 50% mà không ai quyết gì.
  (b) notional **KHÔNG được đổi khi `R_eff` của lệnh đổi** — bất biến cũ của
      TD-0183, giữ nguyên; đó là điều arm này kiểm chứng (§10.1b).

Hai vế phải cùng đúng. Chỉ (b) thì một hằng số cứng cũng thoả; chỉ (a) thì
một công thức có dính `R_eff` cũng thoả.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tool_d.arm_switches import ArmSwitchError, notional_tranche1_theo_arm
from tool_d.config.loader import load_tool_d_config, resolve

REPO_ROOT = Path(__file__).resolve().parents[2]
RHO, N_TR = 0.375, 3


def _goi(*, arm="Z0-S1", e_d=750.0, r_eff=0.03, ref=0.03):
    return notional_tranche1_theo_arm(
        arm=arm, e_d=e_d, rho_pct=RHO, r_eff=r_eff, n_tranches=N_TR,
        notional_ref_r_eff=ref,
    )


class TestHaiVeQuanHe:
    """Cốt lõi: canh QUAN HỆ, không canh giá trị."""

    def test_doi_theo_E_D(self) -> None:
        """(a) — vế mà một hằng số USDT cứng KHÔNG thoả được."""
        assert _goi(e_d=1500.0) == pytest.approx(2 * _goi(e_d=750.0))

    def test_KHONG_doi_theo_r_eff_cua_lenh(self) -> None:
        """(b) — bất biến của TD-0183, giữ nguyên. `r_eff` gấp ba, kết quả y hệt."""
        assert _goi(r_eff=0.01) == _goi(r_eff=0.03) == _goi(r_eff=0.09)

    def test_ti_le_nghich_voi_tham_chieu(self) -> None:
        assert _goi(ref=0.015) == pytest.approx(2 * _goi(ref=0.03))

    def test_cung_cong_thuc_voi_arm_rui_ro_co_dinh(self) -> None:
        """Z0-S1 tại `ref` = X phải bằng ĐÚNG Z0 tại `R_eff` = X.

        Đây là cách phát biểu "hai arm khác nhau đúng một thứ: R_eff nào được
        đưa vào". Nếu ai đó chép lại công thức §6.8e ra chỗ thứ hai rồi hai
        bản trôi lệch (bài học MT-03), ca này đỏ.
        """
        for x in (0.012, 0.03, 0.055):
            assert _goi(ref=x) == pytest.approx(
                notional_tranche1_theo_arm(
                    arm="Z0", e_d=750.0, rho_pct=RHO, r_eff=x, n_tranches=N_TR
                )
            )


class TestFailClosed:
    def test_thieu_tham_chieu_thi_RAISE(self) -> None:
        with pytest.raises(ArmSwitchError, match="notional_ref_r_eff"):
            notional_tranche1_theo_arm(
                arm="Z0-S1", e_d=750.0, rho_pct=RHO, r_eff=0.03, n_tranches=N_TR
            )

    def test_truyen_cho_arm_rui_ro_co_dinh_thi_RAISE(self) -> None:
        with pytest.raises(ArmSwitchError, match="hiểu sai arm này"):
            _goi(arm="Z0")

    @pytest.mark.parametrize("xau", [0.0, -0.03, 1.0, 3.0, 100.0])
    def test_tham_chieu_ngoai_khoang_0_1_thi_RAISE(self, xau: float) -> None:
        """`3.0` thay vì `0.03` làm cỡ lệnh nhỏ đi 100 lần — không phép kiểm
        nào khác báo đỏ, nên chốt đơn vị phải nằm ngay tại cửa."""
        with pytest.raises(ArmSwitchError, match="TỈ LỆ"):
            _goi(ref=xau)


class TestCauHinhTHAT:
    """Ghim trạng thái đã chốt trên file THẬT, và ghim luôn kế toán DOF."""

    def test_cau_hinh_khai_tham_chieu_bang_0_03(self) -> None:
        cfg = load_tool_d_config()
        assert resolve(cfg, "tier_c.arm_ablation.notional_ref_r_eff") == 0.03

    def test_dof_inventory_co_khai_khoa_moi(self) -> None:
        """Một hằng số KHÔNG được khai chính là lỗi DR-D4-02 sinh ra để chặn."""
        doc = yaml.safe_load((REPO_ROOT / "config/dof_inventory.yaml").read_text(encoding="utf-8"))
        khoa = {m["khoa"] for m in doc["khong_dem_vao_dof_goc"]}
        assert "notional_ref_r_eff" in khoa

    def test_N_DANG_KY_khong_doi(self) -> None:
        """🔴 Con số đắt nhất của cả quyết định: thêm khoá này KHÔNG được
        đụng mẫu số rào DSR §10.2."""
        doc = yaml.safe_load((REPO_ROOT / "config/dof_inventory.yaml").read_text(encoding="utf-8"))
        assert doc["dof_goc"] == 28

    def test_gia_tri_dan_xuat_tren_cau_hinh_that(self) -> None:
        """Ghi lại con số để đọc được, NHƯNG tính từ cấu hình chứ không gõ tay
        — nếu `E_D` đổi lần nữa thì ca này đi theo, không đỏ giả."""
        cfg = load_tool_d_config()
        e_d = float(resolve(cfg, "tier_a.E_D"))
        rho = float(resolve(cfg, "tier_a.rho_pct"))
        ref = float(resolve(cfg, "tier_c.arm_ablation.notional_ref_r_eff"))
        n_full = (rho / 100.0) * e_d / ref
        assert n_full == pytest.approx(93.75)
        assert _goi(e_d=e_d, ref=ref) == pytest.approx(n_full / N_TR)
