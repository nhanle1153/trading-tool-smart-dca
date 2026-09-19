"""TD-0323 (DR-SHORT-01) — DG6-D (short squeeze) nối vào `ZoneAbsorption.custom_exit`.

Trước đợt này chiến lược truyền `d=False` cứng vào `dg6_dong_vi_the()`: `dieu_kien_d()`
(TD-0320) tồn tại nhưng KHÔNG ai gọi, nên hai khoá `tier_b.funding_rate_pct` và
`tier_b.dg6d_retrace_frac` không chảy tới phép tính nào. Mọi phép kiểm ở đây chạy
trên chính lớp `ZoneAbsorption` THẬT (nạp từ `user_data/strategies/`), với `dp` và
`trade` giả TỐI THIỂU — chỉ thay thứ Freqtrade cấp, không thay logic của ta.

Phạm vi: chỉ arm `Z3b` + SHORT, cả hai đang tắt ở sản xuất (`enable_short: false`).
File này đo CƠ CHẾ nối, không đo hiệu năng gì (0 trial).

Bốn ràng buộc, mỗi cái có ca riêng và có răng (phá thật → ca đó đỏ):
  1. **Đơn vị** — YAML ghi `-0.05` (phần trăm), hàm so với TỈ LỆ `-0.0005`: chia 100
     đúng MỘT chỗ. Sai ⇒ ngưỡng lệch 100 lần mà không phép kiểm kiểu nào khác bắt.
  2. **Lookahead** — funding của tương lai không được ảnh hưởng quyết định tại `t`.
  3. **Giá vào** = tranche khớp GẦN NHẤT (chủ dự án chốt 19/09/2026), không phải `open_rate`.
  4. **Thiếu dữ liệu ⇒ `d=False`**, không bịa số (N6), kèm cảnh báo một lần mỗi cặp.
"""

from __future__ import annotations

import ast
import importlib.util
import logging
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from tool_d.config.loader import load_tool_d_config, resolve
from tool_d.trade_plan import KeHoachTranche

REPO_ROOT = Path(__file__).resolve().parents[2]
CHIEN_LUOC_PATH = REPO_ROOT / "user_data" / "strategies" / "ZoneAbsorption.py"
PAIR = "AAA/USDT:USDT"
T0 = pd.Timestamp("2025-03-27 12:00", tz="UTC")

# Kế hoạch SHORT: p1 ở mép dưới zone, p3 ở mép trên (giá bơm dần LÊN).
KH = KeHoachTranche(
    zone_low=94.65, zone_high=95.35, p1=94.65, p2=95.0, p3=95.35,
    sl=95.8, r_eff_plan=0.0085, atr_1h_tai_tranche1=0.3,
)
GIA_TRANCHE_1, GIA_TRANCHE_CUOI = 94.65, 95.35
GIA_HIEN_TAI_HOI_DU = 94.90  # hồi (95.35−94.90)/(95.35−94.65) ≈ 0,643 > 0,5 — theo tranche gần nhất
GIA_HIEN_TAI_HOI_CHUA_DU = 95.20  # ≈ 0,214 < 0,5


def _chien_luoc():
    spec = importlib.util.spec_from_file_location("ZoneAbsorptionTD0323", CHIEN_LUOC_PATH)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)  # type: ignore[union-attr]
    s = m.ZoneAbsorption(config={"stake_currency": "USDT", "exchange": {"name": "binance"}})
    s._arm = "Z3b"  # DG6 chỉ bật ở arm này
    s._doc_ke_hoach = lambda trade: (KH, None, {})
    return s


class _DpGia:
    """Chỉ cấp thứ Freqtrade cấp: khung funding, và ghi lại mọi lần bị hỏi."""

    def __init__(self, funding: pd.DataFrame | None) -> None:
        self.funding = funding
        self.goi: list[tuple] = []

    def get_funding_rate_timeframe(self) -> str:
        return "1h"

    def get_pair_dataframe(self, pair, timeframe=None, candle_type=""):
        self.goi.append((pair, timeframe, candle_type))
        return self.funding

    def get_analyzed_dataframe(self, pair, timeframe):
        return None, None  # A và B không có dữ liệu ⇒ cô lập đúng điều kiện D


def _funding(*cap: tuple[str, float]) -> pd.DataFrame:
    """Khung funding đúng hình dạng Freqtrade trả: cột `date` (UTC), `funding_rate`."""
    return pd.DataFrame(
        {
            "date": pd.to_datetime([m for m, _ in cap], utc=True),
            "funding_rate": [v for _, v in cap],
        }
    )


class _Lenh:
    def __init__(self, gia: float) -> None:
        self.safe_price = gia


def _trade(*, la_short: bool = True, gia_khop: tuple[float, ...] = (GIA_TRANCHE_1, GIA_TRANCHE_CUOI)):
    return SimpleNamespace(
        is_short=la_short, id=1, pair=PAIR, open_date_utc=T0 - pd.Timedelta(hours=1),
        funding_fees=0.0, nr_of_successful_exits=0,
        open_rate=95.0,  # cố tình KHÁC gia_khop[-1] để phân biệt hai cách chọn giá vào
        entry_side="sell" if la_short else "buy",
        select_filled_orders=lambda side, _g=gia_khop: [_Lenh(g) for g in _g],
    )


def _goi(s, funding: pd.DataFrame | None, *, gia_hien_tai: float, trade=None, thoi_diem=T0):
    s.dp = _DpGia(funding)
    return s.custom_exit(PAIR, trade or _trade(), thoi_diem, gia_hien_tai, 0.0)


FUNDING_SAU = _funding(("2025-03-27 04:00", -0.0006), ("2025-03-27 12:00", -0.0006))


class TestDonVi:
    def test_ghim_quyet_dinh_yaml_la_phan_tram(self) -> None:
        """Ghim QUYẾT ĐỊNH ở đúng một dòng: YAML đang là `-0.05` (phần trăm, FROZEN).
        Đổi giá trị này thì dòng dưới phải sửa CÓ Ý THỨC — hai ca hành vi bên dưới
        phụ thuộc vào con số này."""
        assert resolve(load_tool_d_config(), "tier_b.funding_rate_pct") == -0.05

    def test_nguong_funding_chia_100_dung_mot_cho(self) -> None:
        s = _chien_luoc()
        goc = float(resolve(load_tool_d_config(), "tier_b.funding_rate_pct"))
        assert s._dg6d_nguong_funding == pytest.approx(goc / 100)
        assert s._dg6d_nguong_funding == pytest.approx(-0.0005)

    def test_nguong_hoi_gia_KHONG_chia_100(self) -> None:
        s = _chien_luoc()
        assert s._dg6d_nguong_hoi == float(resolve(load_tool_d_config(), "tier_b.dg6d_retrace_frac"))

    def test_funding_lech_tren_ngung_thi_khong_no(self) -> None:
        """-0.0004 (= −0,04%) chưa sâu tới −0,05% ⇒ không nổ. Nếu quên ÷100 thì
        ngưỡng là −0,05 (5%) và cả ca dưới lẫn ca này đều không nổ — ca dưới mới
        là ca bắt lỗi đơn vị."""
        s = _chien_luoc()
        f = _funding(("2025-03-27 12:00", -0.0004))
        assert _goi(s, f, gia_hien_tai=GIA_HIEN_TAI_HOI_DU) is None

    def test_funding_sau_hon_ngung_thi_no(self) -> None:
        s = _chien_luoc()
        f = _funding(("2025-03-27 12:00", -0.0006))
        assert _goi(s, f, gia_hien_tai=GIA_HIEN_TAI_HOI_DU) == "DG6_EARLY_INVALIDATION"


class TestDieuKienD:
    def test_hoi_chua_du_thi_khong_no(self) -> None:
        assert _goi(_chien_luoc(), FUNDING_SAU, gia_hien_tai=GIA_HIEN_TAI_HOI_CHUA_DU) is None

    def test_long_khong_bao_gio_no_va_khong_doc_funding(self) -> None:
        s = _chien_luoc()
        kq = _goi(s, FUNDING_SAU, gia_hien_tai=GIA_HIEN_TAI_HOI_DU, trade=_trade(la_short=False))
        assert kq is None
        assert s.dp.goi == [], "đường LONG không được đụng tới dữ liệu funding"

    def test_arm_khac_Z3b_khong_danh_gia_DG6(self) -> None:
        s = _chien_luoc()
        s._arm = "Z3"
        assert _goi(s, FUNDING_SAU, gia_hien_tai=GIA_HIEN_TAI_HOI_DU) is None

    def test_gia_vao_la_tranche_khop_GAN_NHAT_khong_phai_open_rate(self) -> None:
        """Phân biệt hai cách chọn: theo tranche cuối (95,35) hồi 0,643 ⇒ nổ; theo
        `open_rate` (95,0) sẽ ra ≈ 0,29 ⇒ KHÔNG nổ. Chủ dự án chốt tranche cuối."""
        s = _chien_luoc()
        assert _goi(s, FUNDING_SAU, gia_hien_tai=GIA_HIEN_TAI_HOI_DU) == "DG6_EARLY_INVALIDATION"

    def test_chua_co_lenh_khop_nao_thi_khong_no(self) -> None:
        s = _chien_luoc()
        kq = _goi(s, FUNDING_SAU, gia_hien_tai=GIA_HIEN_TAI_HOI_DU, trade=_trade(gia_khop=()))
        assert kq is None


class TestKhongLookahead:
    def test_funding_tuong_lai_khong_anh_huong(self) -> None:
        """Tại T0 chỉ có kỳ −0.0001 (không đủ sâu); kỳ −0.002 nằm ở T0+1h (TƯƠNG LAI).
        Nếu lấy `iloc[-1]` không cắt thì DG6-D nổ — nó KHÔNG được nổ."""
        s = _chien_luoc()
        f = _funding(("2025-03-27 08:00", -0.0001), ("2025-03-27 13:00", -0.002))
        assert _goi(s, f, gia_hien_tai=GIA_HIEN_TAI_HOI_DU) is None

    def test_cat_du_lieu_tai_t_khong_doi_ket_qua(self) -> None:
        """Cắt khung tại `t` (bỏ hết hàng > t) không được đổi `_funding_8h(t)`."""
        s = _chien_luoc()
        day_du = _funding(
            ("2025-03-27 04:00", -0.0002), ("2025-03-27 12:00", -0.0003),
            ("2025-03-27 13:00", -0.009), ("2025-03-27 20:00", -0.009),
        )
        da_cat = day_du[day_du["date"] <= T0]
        s.dp = _DpGia(day_du)
        a = s._funding_8h(PAIR, T0)
        s.dp = _DpGia(da_cat)
        b = s._funding_8h(PAIR, T0)
        assert a == b == pytest.approx(-0.0003)

    def test_ky_funding_dung_mo_moc_t_thi_da_biet(self) -> None:
        s = _chien_luoc()
        s.dp = _DpGia(_funding(("2025-03-27 12:00", -0.0007)))
        assert s._funding_8h(PAIR, T0) == pytest.approx(-0.0007)

    def test_goi_dp_dung_khung_va_candle_type_funding(self) -> None:
        s = _chien_luoc()
        s.dp = _DpGia(_funding(("2025-03-27 12:00", -0.0007)))
        s._funding_8h(PAIR, T0)
        assert s.dp.goi == [(PAIR, "1h", "funding_rate")]

    def test_ast_funding_8h_cat_theo_current_time(self) -> None:
        cay = ast.parse(CHIEN_LUOC_PATH.read_text(encoding="utf-8"))
        node = next(n for n in ast.walk(cay) if isinstance(n, ast.FunctionDef) and n.name == "_funding_8h")
        assert any(isinstance(x, ast.Name) and x.id == "current_time" for x in ast.walk(node))
        assert any(isinstance(x, ast.Compare) for x in ast.walk(node)), "không thấy phép so sánh cắt thời gian"
        assert not any(
            isinstance(x, ast.Attribute) and x.attr in ("now", "utcnow") for x in ast.walk(node)
        ), "cắt theo datetime.now() là sai trong backtest — phải theo current_time"


class TestThieuDuLieu:
    @pytest.mark.parametrize(
        "khung",
        [
            None,
            pd.DataFrame({"date": pd.to_datetime([], utc=True), "funding_rate": []}),
            _funding(("2025-03-27 12:00", float("nan"))),
            _funding(("2025-03-28 00:00", -0.002)),  # chỉ có tương lai
        ],
        ids=["None", "rong", "NaN", "chi_tuong_lai"],
    )
    def test_thieu_thi_khong_no_va_khong_bia_so(self, khung) -> None:
        s = _chien_luoc()
        assert _goi(s, khung, gia_hien_tai=GIA_HIEN_TAI_HOI_DU) is None
        assert s._funding_8h(PAIR, T0) is None

    def test_canh_bao_mot_lan_moi_cap(self, caplog) -> None:
        s = _chien_luoc()
        with caplog.at_level(logging.WARNING):
            for _ in range(3):
                _goi(s, None, gia_hien_tai=GIA_HIEN_TAI_HOI_DU)
        assert sum("DG6D_THIEU_FUNDING" in r.getMessage() for r in caplog.records) == 1

    def test_thieu_cot_funding_rate_cung_la_thieu(self) -> None:
        s = _chien_luoc()
        khung = pd.DataFrame({"date": pd.to_datetime(["2025-03-27 12:00"], utc=True), "x": [1.0]})
        assert _goi(s, khung, gia_hien_tai=GIA_HIEN_TAI_HOI_DU) is None
