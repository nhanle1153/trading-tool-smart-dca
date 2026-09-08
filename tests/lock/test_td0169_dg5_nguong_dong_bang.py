"""🔴 TD-0169 / DR-D4-02 — ngưỡng suy yếu ZSS của DG5: ĐÓNG BĂNG.

§4 định nghĩa DG5 bằng ngưỡng *"giảm > 30%"* nhưng bảng kiểm kê DR-010
KHÔNG có dòng nào cho DG5 — một bậc tự do chưa ai đếm. Chủ dự án chốt
đóng băng thay vì thêm vào `tier_b`.

Bộ test này canh đúng một mệnh đề, và nó là toàn bộ giá trị của phương án
đã chọn: **ghi nhận bậc tự do này TỒN TẠI mà KHÔNG tốn trial nào.** Nếu
khoá trôi sang `tier_b` thì `N_ĐĂNG_KÝ` nhảy 114 → 120 (**+6 trial**) và
rào DSR §10.2 đổi theo — một thay đổi đắt, đi qua im lặng, và chỉ lộ ra ở
cổng §10.2 nhiều tuần sau.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from tool_d.config.dof import dof_report, load_dof_inventory
from tool_d.config.loader import load_tool_d_config, resolve, tunable_param_names
from tool_d.dg1_dg5_tranche_gates import dg5_zss_khong_suy_yeu

KHOA = "dg5_zss_decay_max"
REPO_ROOT = Path(__file__).resolve().parents[2]


class TestNgUongDaCoChoDungTrongCauHinh:
    def test_nam_trong_tier_frozen_voi_gia_tri_0_30(self) -> None:
        cfg = load_tool_d_config()
        assert resolve(cfg, f"tier_frozen.{KHOA}") == {"value": 0.30, "dof": 0}

    def test_dof_bang_0_KHONG_phai_am(self) -> None:
        """`dof` âm nghĩa là "đóng băng thứ ĐÃ được đếm, nên trừ đi bấy
        nhiêu bậc tự do" (như `dg6b_bars_1h: -1`). DG5 chưa từng được
        đếm, nên trừ đi là trừ khống — đúng LỖI 1 của v5 mà bảng
        `khong_dem_vao_dof_goc` sinh ra để chặn."""
        cfg = load_tool_d_config()
        assert resolve(cfg, f"tier_frozen.{KHOA}.dof") == 0

    def test_gia_tri_la_TI_LE_khong_phai_phan_tram(self) -> None:
        """`30` thay vì `0.30` làm `zss >= zss1*(1-30)` luôn đúng ⇒ DG5 bị
        tắt mà không ai biết. Ghim đúng khoảng mà DG5 chấp nhận."""
        cfg = load_tool_d_config()
        assert 0 < resolve(cfg, f"tier_frozen.{KHOA}.value") < 1


class TestKhongTonMotTrialNao:
    """🔴 Toàn bộ lý do phương án đóng băng được chọn."""

    def test_KHONG_nam_trong_tier_b(self) -> None:
        cfg = load_tool_d_config()
        assert KHOA not in tunable_param_names(cfg)

    def test_tier_b_van_dung_12_muc(self) -> None:
        assert len(tunable_param_names(load_tool_d_config())) == 12

    def test_N_DANG_KY_van_la_114_khong_phai_120(self) -> None:
        """Nếu ca này đỏ với số 120 thì khoá đã trôi sang `tier_b` —
        `4 + 3×13×2 + 9×2 + 20 = 120`, tức **+6 trial** trên tổng ngân
        sách, đúng đơn giá "+1 tham số = +6 trial" của spec."""
        assert dof_report().n_dang_ky_computed == 114

    def test_rao_DSR_khong_doi(self) -> None:
        """`N` là mẫu số của rào DSR §10.2. Ghi cả hai số ra đây để lần
        sau ai đổi `N` cũng thấy ngay mình đang dịch cái rào nào."""
        assert math.sqrt(2 * math.log(114)) == pytest.approx(3.0777, abs=1e-4)
        assert math.sqrt(2 * math.log(120)) == pytest.approx(3.0943, abs=1e-4)

    def test_LZ29_van_xanh_tren_ca_ba_con_so(self) -> None:
        bc = dof_report()
        assert bc.dof_goc_declared == bc.dof_goc_from_v5_sum == 28
        assert bc.tier_b_declared_count == bc.tier_b_from_table_sum == 12


class TestGhiNhanTrongKiemKeDOF:
    def test_co_dong_trong_khong_dem_vao_dof_goc(self) -> None:
        """Đóng băng mà KHÔNG ghi vào kiểm kê là giấu bậc tự do dưới một
        cái tên khác — tệ hơn để nguyên, vì trông như đã xử lý."""
        inv = load_dof_inventory()
        assert KHOA in {m["khoa"] for m in inv["khong_dem_vao_dof_goc"]}

    def test_KHONG_nam_trong_bo_sot(self) -> None:
        """🔴 Phân biệt then chốt của DR-D4-02: `bo_sot` (DG7,
        `w_tranche`) là những mục CHÍNH SPEC thừa nhận thiếu và **đã cộng
        vào `DOF_gốc = 28`**. DG5 thì spec cũng không đếm — xếp vào đó là
        tuyên bố con số 28 trích nguyên văn là sai, và `dof_goc` sẽ phải
        thành 29."""
        inv = load_dof_inventory()
        assert KHOA not in {m.get("ten", "") for m in inv["bo_sot"]}
        assert inv["dof_goc"] == 28

    def test_ly_do_giai_thich_vi_sao_KHONG_dem_khong_chi_noi_da_dong_bang(self) -> None:
        """Một dòng lý do chỉ nói "đã đóng băng" không giúp ai — câu hỏi
        người đọc sau sẽ có là *vì sao nó không nằm trong 28*."""
        inv = load_dof_inventory()
        ly_do = next(
            m["ly_do"] for m in inv["khong_dem_vao_dof_goc"] if m["khoa"] == KHOA
        )
        assert "DG5" in ly_do and "DR-D4-02" in ly_do


class TestNoiVaoDG5That:
    def test_gia_tri_trong_cau_hinh_dung_duoc_thang_cho_dg5(self) -> None:
        """Vòng khép kín: con số trong cấu hình phải đi lọt qua chính hàm
        DG5 mà không bị `TrancheGateError` chặn. Thiếu ca này thì cấu
        hình và cổng có thể đồng ý trên giấy mà không bao giờ gặp nhau —
        đúng bài học TD-0130 (cửa ghi và schema không nhìn nhau)."""
        nguong = resolve(load_tool_d_config(), f"tier_frozen.{KHOA}.value")
        assert dg5_zss_khong_suy_yeu(
            zss_tai_tranche1=1.0, zss_hien_tai=0.70, nguong_giam_toi_da=nguong
        )
        assert not dg5_zss_khong_suy_yeu(
            zss_tai_tranche1=1.0, zss_hien_tai=0.69, nguong_giam_toi_da=nguong
        )

    def test_DG5_van_KHONG_co_gia_tri_mac_dinh(self) -> None:
        """Có chỗ trong cấu hình rồi KHÔNG có nghĩa là được phép đặt mặc
        định trong hàm — N4 đòi tham số đi qua `resolve()`, và một mặc
        định làm cổng vẫn chạy khi cấu hình chưa nạp."""
        import inspect

        p = inspect.signature(dg5_zss_khong_suy_yeu).parameters["nguong_giam_toi_da"]
        assert p.default is inspect.Parameter.empty


class TestQuyetDinhDaGhiThanhVAN:
    def test_DR_D4_02_ton_tai_va_ghi_ba_dieu_kien_mo_lai(self) -> None:
        """Điều kiện mở lại phải viết TRƯỚC khi có kết quả ablation —
        cùng khuôn DR-Q3-2026 và DR-D35-01. Không có nó thì việc mở khoá
        30% sau này luôn có thể được biện minh bằng một lập luận dựng sau
        khi đã nhìn thấy số."""
        van = (REPO_ROOT / "docs/decisions/DR-D4-02-dg5-nguong-dong-bang.md").read_text(
            encoding="utf-8"
        )
        assert "Điều kiện mở lại" in van
        assert "VÀ**, không phải HOẶC" in van
        # phải nói thẳng đây là chỗ giữ chưa calibrate, không phải số đã đo
        assert "CHƯA CALIBRATE" in van.upper()
