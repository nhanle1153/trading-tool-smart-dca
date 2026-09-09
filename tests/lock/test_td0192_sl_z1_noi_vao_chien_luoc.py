"""🔒 TD-0192 — SL cố định của arm `Z1` phải đọc được TRÊN ĐƯỜNG CHIẾN LƯỢC
THẬT, không chỉ trong `arm_switches.py`.

Bài học TD-0188, áp lại nguyên văn: một cổng có thể đúng ở tầng MODULE
(`ke_hoach_theo_arm()`, `sl_neo_atr()` — có test khoá, có docstring cảnh
báo) mà vẫn KHÔNG BAO GIỜ được gọi trên đường sản xuất. Đúng thứ MT-21
đo được: 83/83 lệnh `Z1` trùng khít `Z0` trên EXPLORE, vì `_tinh_zone_4h`
gọi thẳng `tinh_ke_hoach()` (luôn chế độ ZONE) thay vì đi qua
`ke_hoach_theo_arm(arm=self._arm, ...)`.

Bộ test này gọi ĐÚNG `_tinh_zone_4h` — phương thức thật, được
`populate_indicators` gọi thật trong backtest — không dựng lại phép
tính SL ở đây (dựng lại là tái lập đúng bug: tự viết công thức đúng rồi
tự kiểm công thức đó, không kiểm được đường dây nối).
"""

from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest
import talib

REPO_ROOT = Path(__file__).resolve().parents[2]
NGUON_CHIEN_LUOC = REPO_ROOT / "user_data/strategies/ZoneAbsorption.py"


def _import_td0187():
    spec = importlib.util.spec_from_file_location(
        "t187", REPO_ROOT / "tests/lock/test_td0187_dinh_co_lenh_backtest_that.py"
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _import_chien_luoc():
    import sys

    if str(REPO_ROOT / "user_data/strategies") not in sys.path:
        sys.path.insert(0, str(REPO_ROOT / "user_data/strategies"))
    spec = importlib.util.spec_from_file_location("ZoneAbsorption", NGUON_CHIEN_LUOC)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def khung_4h() -> pd.DataFrame:
    """Chuỗi 4H thật của fixture TD-0187 — mang đúng một zone đáy hợp lệ
    (swing `i=870`, nến xác nhận `j=873`, đã đo trong TD-0189 chặng 2a)."""
    m = _import_td0187()
    rows4 = m._bars_4h_co_trend()
    rows1 = [x for bar in rows4 for x in m._chia_nho(bar, 4)]
    bat_dau = m._moc_bat_dau(len(rows1))
    idx4 = pd.date_range(bat_dau, periods=len(rows4), freq="4h", tz="UTC")
    df = pd.DataFrame(rows4, columns=["open", "high", "low", "close", "volume"])
    df.insert(0, "date", idx4)
    return df


def _ke_hoach_tai(df_ket_qua: pd.DataFrame, j: int) -> dict:
    tag = df_ket_qua["ke_hoach_json"].iloc[j]
    assert tag, f"nến {j} không mang kế hoạch — zone không xác nhận ở đây"
    return json.loads(tag)


class TestSLPhanBietTheoArmTrenChienLuocThat:
    """Gọi thẳng `ZoneAbsorption._tinh_zone_4h` — không mock, không dựng
    lại công thức."""

    def test_zone_XAC_NHAN_dung_o_nen_873(self, khung_4h: pd.DataFrame) -> None:
        """Chốt tiền đề — nếu bộ sinh dữ liệu đổi, ca này báo trước khi
        các ca dưới đây đỏ mập mờ vì lệch chỉ số."""
        ZA = _import_chien_luoc()
        s = ZA.ZoneAbsorption(config={"stake_currency": "USDT", "exchange": {"name": "binance"}})
        s._arm = "Z0"
        ra = s._tinh_zone_4h(khung_4h.copy())
        assert bool(ra["zone_valid"].iloc[873]), "fixture không còn xác nhận zone ở nến 873"

    def test_SL_cua_Z1_KHAC_SL_cua_Z0_cung_zone(self, khung_4h: pd.DataFrame) -> None:
        ZA = _import_chien_luoc()

        s0 = ZA.ZoneAbsorption(config={"stake_currency": "USDT", "exchange": {"name": "binance"}})
        s0._arm = "Z0"
        kh0 = _ke_hoach_tai(s0._tinh_zone_4h(khung_4h.copy()), 873)

        s1 = ZA.ZoneAbsorption(config={"stake_currency": "USDT", "exchange": {"name": "binance"}})
        s1._arm = "Z1"
        kh1 = _ke_hoach_tai(s1._tinh_zone_4h(khung_4h.copy()), 873)

        # 🔴 Chốt cốt lõi của TD-0192 — trước bản vá, hai dòng này BẰNG
        # NHAU (83/83 lệnh trùng khít trên EXPLORE, MT-21).
        assert kh1["sl"] != pytest.approx(kh0["sl"])
        assert kh1["p1"] == pytest.approx(kh0["p1"]), "p1 không đổi theo arm — chỉ SL đổi"
        assert kh1["p2"] == pytest.approx(kh0["p2"])
        assert kh1["p3"] == pytest.approx(kh0["p3"])

    def test_SL_cua_Z1_dung_cong_thuc_ATR_CO_DINH(self, khung_4h: pd.DataFrame) -> None:
        """Không chỉ *khác* — phải đúng công thức `p1 − 2,2×ATR(4H)`."""
        from tool_d.arm_switches import HE_SO_ATR_Z1

        ZA = _import_chien_luoc()
        s1 = ZA.ZoneAbsorption(config={"stake_currency": "USDT", "exchange": {"name": "binance"}})
        s1._arm = "Z1"
        kh1 = _ke_hoach_tai(s1._tinh_zone_4h(khung_4h.copy()), 873)

        atr = talib.ATR(
            khung_4h["high"].to_numpy(dtype=float),
            khung_4h["low"].to_numpy(dtype=float),
            khung_4h["close"].to_numpy(dtype=float),
            timeperiod=14,
        )
        sl_ky_vong = kh1["p1"] - HE_SO_ATR_Z1 * atr[873]
        assert kh1["sl"] == pytest.approx(sl_ky_vong, rel=1e-6)

    def test_SL_cua_Z0_KHONG_doi_dang_ZONE(self, khung_4h: pd.DataFrame) -> None:
        """Đối chứng: arm không đổi (`Z0`, `Z3`, `Z0-T1`, ...) phải cho
        CÙNG một SL — bản vá chỉ được rẽ nhánh cho arm `Z1`."""
        ZA = _import_chien_luoc()
        gia = []
        for arm in ("Z0", "Z3", "Z0-T1"):
            s = ZA.ZoneAbsorption(config={"stake_currency": "USDT", "exchange": {"name": "binance"}})
            s._arm = arm
            gia.append(_ke_hoach_tai(s._tinh_zone_4h(khung_4h.copy()), 873)["sl"])
        assert gia[0] == pytest.approx(gia[1]) == pytest.approx(gia[2])

    def test_r_eff_plan_CUA_Z1_KHAC_Z0_vi_SL_khac(self, khung_4h: pd.DataFrame) -> None:
        """🔴 Đúng cảnh báo trong docstring `ke_hoach_theo_arm()`: bỏ sót
        tính lại `r_eff_plan` là lỗi im lặng đắt nhất — nó chảy thẳng
        vào cỡ lệnh (§6.8e). SL đổi mà `r_eff_plan` không đổi nghĩa là
        `ke_hoach_theo_arm()` bị bỏ qua ở một nhánh khác, hoặc bị gọi sai."""
        ZA = _import_chien_luoc()
        s0 = ZA.ZoneAbsorption(config={"stake_currency": "USDT", "exchange": {"name": "binance"}})
        s0._arm = "Z0"
        s1 = ZA.ZoneAbsorption(config={"stake_currency": "USDT", "exchange": {"name": "binance"}})
        s1._arm = "Z1"
        kh0 = _ke_hoach_tai(s0._tinh_zone_4h(khung_4h.copy()), 873)
        kh1 = _ke_hoach_tai(s1._tinh_zone_4h(khung_4h.copy()), 873)
        r_eff0 = (sum(kh0[k] for k in ("p1", "p2", "p3")) / 3 - kh0["sl"]) / (
            sum(kh0[k] for k in ("p1", "p2", "p3")) / 3
        )
        r_eff1 = (sum(kh1[k] for k in ("p1", "p2", "p3")) / 3 - kh1["sl"]) / (
            sum(kh1[k] for k in ("p1", "p2", "p3")) / 3
        )
        assert r_eff1 != pytest.approx(r_eff0)


class TestKhongGoiThangTinhKeHoach:
    """Hỏi *có DÙNG không*, không phải *có NHẮC TỚI không* — bằng AST,
    theo bài học `L-Z25`/TD-0181/TD-0183: `_tinh_zone_4h` phải đi qua
    `ke_hoach_theo_arm()`, KHÔNG được gọi thẳng `tinh_ke_hoach()`."""

    @pytest.fixture(scope="module")
    def cay(self) -> ast.Module:
        return ast.parse(NGUON_CHIEN_LUOC.read_text(encoding="utf-8"))

    def test_khong_import_tinh_ke_hoach(self, cay: ast.Module) -> None:
        ten_import = {
            alias.asname or alias.name
            for node in ast.walk(cay)
            if isinstance(node, ast.ImportFrom)
            for alias in node.names
        }
        assert "tinh_ke_hoach" not in ten_import, (
            "`tinh_ke_hoach()` (không phân nhánh theo arm) vẫn được import — "
            "đường sản xuất phải đi qua `ke_hoach_theo_arm()` (TD-0192)"
        )

    def test_ke_hoach_theo_arm_DUOC_GOI(self, cay: ast.Module) -> None:
        goi = {
            n.func.id
            for n in ast.walk(cay)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
        }
        assert "ke_hoach_theo_arm" in goi
