"""🔒 TD-0198 — `mult_regime()` không được raise cho arm CỐ Ý tắt bộ lọc ADX(1D).

`sizing.mult_regime()` raise `SizingError` khi `ADX(1D) < ngưỡng` với lý do
*"§2.5 đáng lẽ đã chặn từ trước; tới được tầng định cỡ nghĩa là bộ lọc trend
không chạy"*. Giả định ĐÚNG cho arm `DAY_DU`, **SAI THEO ĐỊNH NGHĨA** cho
`Z0-T0` (§10.1b: *"KHÔNG bộ lọc trend nào"*) và `Z0-T1` (*"bỏ ADX(1D)≥20"*)
— với hai arm đó, "bộ lọc trend không chạy" chính là thứ chúng đo.

════ Vì sao đây không phải chuyện gọn gàng mã nguồn — đo được ════

Freqtrade **nuốt** exception của callback (`strategy_safe_wrapper` hạ thành
WARNING rồi đi tiếp, `rc = 0` — MT-16 vii), nên mỗi lần raise là **một lệnh
biến mất trong im lặng**. Đo trên 88 mã EXPLORE (commit `70542cb`, 0 trial):
**588 lệnh của `Z0-T0`** và **123 của `Z0-T1`** mất theo đường đó; `Z0`/`Z3`
mất 0 (arm `DAY_DU` không bao giờ chạm nhánh này).

🔴 Và chúng KHÔNG ngẫu nhiên: đúng tập `ADX(1D) < 20` — tức **chính tập lệnh
làm nên khác biệt của hai arm ấy**. Nặng hơn MT-15 một bậc: MT-15 là hai arm
TRÙNG nhau (một suất trial mua *thông tin bằng 0*); ở đây arm chạy một cấu
hình **KHÁC** thứ nó khai (*thông tin sai*), mà bảng kết quả vẫn bình thường.

════ Bốn lớp ════

1. **Hàm thuần** — DAY_DU vẫn raise (chốt cũ nguyên vẹn); KHONG/CHI_4H trả
   `weak`; tham số BẮT BUỘC, không mặc định (khuôn `bat_dieu_kien_c`).
2. **Ánh xạ arm → cờ** — `co_loc_adx_1d` phủ đủ 10 khoá của `TANG_THEO_ARM`,
   và ĐÚNG hai arm được tắt (không phải "arm nào cũng tắt cho tiện").
3. **Đường nối** (AST + instance thật) — chiến lược truyền cờ SUY TỪ ARM vào
   `mult_regime`, không phải hằng số/cờ khai tay.
4. **Có răng** — mỗi lớp kèm phép phá tương ứng ngay trong ca test.
"""

from __future__ import annotations

import ast
import importlib.util
import inspect
import sys
from pathlib import Path

import pytest

from tool_d.arms import TANG_HOP_LE, TANG_THEO_ARM, ArmKhongHopLeError, co_loc_adx_1d, tang_cua_arm
from tool_d.sizing import SizingError, mult_regime

REPO_ROOT = Path(__file__).resolve().parents[2]
NGUON_CHIEN_LUOC = REPO_ROOT / "user_data" / "strategies" / "ZoneAbsorption.py"

K = dict(strong=1.0, weak=0.7, adx_split=25.0, adx_threshold=20.0)


class TestHamThuan:
    def test_DAY_DU_van_RAISE_chot_cu_nguyen_ven(self) -> None:
        """Lớp canh duy nhất bắt được 'bộ lọc trend chết' (MT-21 đã xảy ra
        thật một lần) — TD-0198 KHÔNG được làm nó câm."""
        with pytest.raises(SizingError, match="§2.5"):
            mult_regime(adx_1d=19.9, da_loc_adx=True, **K)

    @pytest.mark.parametrize("adx", [19.9, 10.0, 0.0])
    def test_arm_TAT_loc_thi_tra_weak_KHONG_raise(self, adx: float) -> None:
        assert mult_regime(adx_1d=adx, da_loc_adx=False, **K) == K["weak"]

    def test_tren_nguong_thi_HAI_ARM_GIONG_NHAU(self) -> None:
        """Bản vá chỉ mở đúng vùng `ADX < adx_threshold`. Nếu nó đổi cả vùng
        trên ngưỡng thì đã lặng lẽ đổi cỡ lệnh của 7 arm còn lại."""
        for adx in (20.0, 24.99, 25.0, 40.0):
            assert mult_regime(adx_1d=adx, da_loc_adx=True, **K) == mult_regime(
                adx_1d=adx, da_loc_adx=False, **K
            )

    def test_NaN_van_raise_bat_ke_co(self) -> None:
        """'Không đo được' KHÁC 'trend yếu' — N6. Cờ arm không được nới điều đó."""
        for co in (True, False):
            with pytest.raises(SizingError, match="NaN"):
                mult_regime(adx_1d=float("nan"), da_loc_adx=co, **K)

    def test_da_loc_adx_la_tham_so_BAT_BUOC(self) -> None:
        """Không mặc định — một mặc định `True` sẽ giữ nguyên bug cho arm quên
        khai; một mặc định `False` sẽ làm câm chốt của 7 arm kia. Cùng khuôn
        `entry_confirmation.tim_xac_nhan_entry(bat_dieu_kien_c=...)` (MT-15)."""
        p = inspect.signature(mult_regime).parameters["da_loc_adx"]
        assert p.default is inspect.Parameter.empty
        assert p.kind is inspect.Parameter.KEYWORD_ONLY


class TestAnhXaArmSangCo:
    def test_dung_HAI_arm_duoc_tat_khong_hon_khong_kem(self) -> None:
        tat = sorted(a for a in TANG_THEO_ARM if not co_loc_adx_1d(tang_cua_arm(a)))
        assert tat == ["Z0-T0", "Z0-T1"], (
            f"chỉ Z0-T0 (KHÔNG bộ lọc nào) và Z0-T1 (bỏ tầng 1D) được tắt §2.5; thấy {tat}"
        )

    def test_phu_du_moi_khoa_cua_bang_arm(self) -> None:
        for arm in TANG_THEO_ARM:
            assert isinstance(co_loc_adx_1d(tang_cua_arm(arm)), bool)

    def test_Z0_va_Z0_T2_cung_ket_qua(self) -> None:
        """`Z0-T2` là alias của `Z0` (§10.1b) — nếu lệch nhau ở đây thì mốc
        so sánh và arm nền đã thành hai thứ khác nhau."""
        assert co_loc_adx_1d(tang_cua_arm("Z0")) is co_loc_adx_1d(tang_cua_arm("Z0-T2")) is True

    def test_tang_la_thi_RAISE_khong_mac_dinh_ve_DAY_DU(self) -> None:
        for la in ("day_du", "", "DAYDU"):
            with pytest.raises(ArmKhongHopLeError):
                co_loc_adx_1d(la)  # type: ignore[arg-type]

    def test_moi_tang_hop_le_deu_co_cau_tra_loi(self) -> None:
        assert {t: co_loc_adx_1d(t) for t in TANG_HOP_LE} == {
            "KHONG": False, "CHI_4H": False, "DAY_DU": True
        }


class TestDuongNoiTrenChienLuoc:
    @pytest.fixture(scope="class")
    def cay(self) -> ast.Module:
        return ast.parse(NGUON_CHIEN_LUOC.read_text(encoding="utf-8"))

    def test_mult_regime_duoc_goi_KEM_co(self, cay: ast.Module) -> None:
        """Bài học TD-0188/TD-0192: hàm đúng ở tầng module vẫn có thể KHÔNG
        BAO GIỜ được gọi đúng trên đường sản xuất."""
        goi = [
            n for n in ast.walk(cay)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "mult_regime"
        ]
        assert len(goi) == 1, f"phải có ĐÚNG một chỗ gọi mult_regime, thấy {len(goi)}"
        kw = {k.arg for k in goi[0].keywords}
        assert "da_loc_adx" in kw, "chiến lược gọi mult_regime mà KHÔNG khai cờ arm"

    def test_co_duoc_SUY_TU_ARM_khong_phai_hang_so(self, cay: ast.Module) -> None:
        """🔴 Chỗ dễ hỏng nhất: truyền thẳng `True`/`False` sẽ làm ca AST trên
        vẫn xanh trong khi cờ không còn theo arm nữa."""
        goi = next(
            n for n in ast.walk(cay)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "mult_regime"
        )
        gt = next(k.value for k in goi.keywords if k.arg == "da_loc_adx")
        assert isinstance(gt, ast.Attribute) and gt.attr == "_da_loc_adx", ast.dump(gt)

        gan = [
            n for n in ast.walk(cay)
            if isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Attribute) and t.attr == "_da_loc_adx" for t in n.targets)
        ]
        assert len(gan) == 1, "`_da_loc_adx` phải được gán ĐÚNG một lần"
        assert isinstance(gan[0].value, ast.Call) and gan[0].value.func.id == "co_loc_adx_1d", (
            "phải suy từ arm qua `co_loc_adx_1d(...)`, không gán hằng số hay cờ khai tay"
        )

    def test_instance_that_suy_dung_co(self) -> None:
        """Đi qua chính `__init__` của chiến lược, không dựng lại phép suy."""
        if str(REPO_ROOT / "user_data/strategies") not in sys.path:
            sys.path.insert(0, str(REPO_ROOT / "user_data/strategies"))
        spec = importlib.util.spec_from_file_location("ZoneAbsorption", NGUON_CHIEN_LUOC)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        s = mod.ZoneAbsorption(config={"stake_currency": "USDT", "exchange": {"name": "binance"}})
        assert s._da_loc_adx is co_loc_adx_1d(tang_cua_arm(s._arm))
        # Đổi arm ⇒ cờ phải đi theo (chứng minh nó là hàm của arm, không phải hằng)
        for arm, cho in (("Z0-T0", False), ("Z0-T1", False), ("Z3", True)):
            assert co_loc_adx_1d(tang_cua_arm(arm)) is cho


class TestKiemCoRang:
    """Phá thật trên BẢN CHÉP, không đụng file sản xuất (khuôn TD-0170)."""

    def test_bo_nhanh_moi_thi_arm_tat_loc_RAISE_tro_lai(self) -> None:
        src = (REPO_ROOT / "src/tool_d/sizing.py").read_text(encoding="utf-8")
        goc = "if da_loc_adx and adx_1d < adx_threshold:"
        assert src.count(goc) == 1, "dòng chốt đã đổi — cập nhật phép phá"
        hong = src.replace(goc, "if adx_1d < adx_threshold:")
        ns: dict = {}
        exec(compile(hong, "sizing_hong", "exec"), ns)  # noqa: S102 — bản chép trong bộ nhớ
        with pytest.raises(Exception, match="§2.5"):
            ns["mult_regime"](adx_1d=19.9, da_loc_adx=False, **K)
        # và bản THẬT thì không
        assert mult_regime(adx_1d=19.9, da_loc_adx=False, **K) == K["weak"]

    def test_dao_anh_xa_arm_thi_ca_tren_do(self) -> None:
        """Nếu `co_loc_adx_1d` trả True cho mọi tầng thì bug quay lại nguyên vẹn."""
        assert co_loc_adx_1d("KHONG") is False and co_loc_adx_1d("DAY_DU") is True
