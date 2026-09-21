"""🔒 TD-0364 (`MT-69`) — cổng §6.4 `L-Z3` trên đường VÀO LỆNH THẬT.

Ba tầng, mỗi tầng một câu hỏi khác nhau (khuôn `test_td0355_post_only_ld13.py`):
1. **Tầng thuần** (`tool_d/cong_thanh_ly.py`) — luật đúng chưa, và BA ca "không tính được" có đều thành TỪ CHỐI
   không (ham thiếu · cặp không có bảng bậc · kế hoạch không hợp lệ).
2. **Tranche 1** (`confirm_trade_entry`) — chốt có nằm trên đường chạy thật không, có fail-closed khi kế hoạch
   chưa từng đi qua cổng không, và có đứng TRƯỚC cổng kết nạp danh mục không.
3. **Tranche 2/3** (`adjust_trade_position`) — Freqtrade KHÔNG gọi `confirm_trade_entry` cho tranche 2/3
   (`backtesting.py:1190`, `if not pos_adjust`), nên chốt ở đó phải là một chốt RIÊNG.

🔴 Vì sao không ghim một con số tỉ số nào: ngưỡng 8 là `tier_c` (khoá, không tune) và được đọc từ
`config/tool_d_config.yaml` qua `resolve` — ghim lại ở đây là tạo nguồn thứ hai cho cùng một ngưỡng (N4/`MT-03`).
Test ghim QUAN HỆ (dưới ngưỡng ⇒ từ chối), không ghim con số.
"""

from __future__ import annotations

import ast
import importlib.util
import logging
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from tool_d.ablation.thanh_ly import HamThanhLy
from tool_d.cong_thanh_ly import MA_CONG, de_ghi_so, xet_cong_l_z3

REPO_ROOT = Path(__file__).resolve().parents[2]
NGUON_CHIEN_LUOC = REPO_ROOT / "user_data/strategies/ZoneAbsorption.py"
PAIR = "LTC/USDT:USDT"

# Kế hoạch mẫu: p_avg_plan = 99,0 và mẫu số (p_avg − sl) = 2,0 ⇒ tỉ số = (99 − liq)/2, chọn `liq` là chọn tỉ số.
P = (100.0, 99.0, 98.0)
W = (1 / 3, 1 / 3, 1 / 3)
SL = 97.0
N_FULL = 300.0
DON_BAY = 3.0


def _ham(liq: float | None) -> HamThanhLy:
    return HamThanhLy(tinh=lambda *a, **k: liq, liquidation_buffer=0.05)


def _xet(*, liq: float | None, nguong: float = 8.0, ham_none: bool = False, sl: float = SL, tranche: int = 1):
    return xet_cong_l_z3(
        pair=PAIR, p=P, sl=sl, w=W, n_full=N_FULL, don_bay=DON_BAY,
        ham=None if ham_none else _ham(liq), nguong=nguong, tranche=tranche,
    )


class TestTangThuan:
    def test_dem_day_thi_qua(self) -> None:
        kq = _xet(liq=79.0)  # (99 − 79)/2 = 10 ≥ 8
        assert kq.qua is True and kq.ly_do == ""
        assert kq.dem is not None and kq.dem.ty_so == pytest.approx(10.0)

    def test_dem_mong_thi_tu_choi(self) -> None:
        kq = _xet(liq=89.0)  # (99 − 89)/2 = 5 < 8
        assert kq.qua is False
        assert kq.dem is not None, "từ chối vì ĐO ĐƯỢC và thiếu — số phải còn đó để truy ngược"
        assert kq.dem.ty_so == pytest.approx(5.0)

    def test_bang_dung_nguong_thi_qua(self) -> None:
        """Spec viết `≥ 8`, không phải `> 8` — biên thuộc phía CHO MỞ."""
        assert _xet(liq=83.0).qua is True  # (99 − 83)/2 = 8

    @pytest.mark.parametrize(
        "kwargs,vi_sao",
        [
            ({"ham_none": True}, "không dựng được hàm giá thanh lý"),
            ({"liq": None}, "cặp không có trong bảng bậc đòn bẩy"),
            ({"liq": 79.0, "sl": 99.5}, "sl ≥ p_avg_plan ⇒ mẫu số không dương"),
        ],
    )
    def test_ba_ca_khong_tinh_duoc_deu_TU_CHOI(self, kwargs, vi_sao) -> None:
        """Fail-closed: không đo được ≠ đạt. Và `dem is None` — KHÔNG có số thay thế nào được bịa (N6)."""
        kq = _xet(**{"liq": 79.0, **kwargs})
        assert kq.qua is False, vi_sao
        assert kq.dem is None
        assert MA_CONG in kq.ly_do

    def test_ly_do_mang_ca_tu_va_mau(self) -> None:
        """Spec `:1885` điểm 2: *"không có hai số đầu thì L-Z3 fail mà không biết fail vì đâu"*."""
        t = _xet(liq=89.0).ly_do
        for phai_co in ("LIQ_BUFFER_TU_CHOI", PAIR, "tranche=1", "ty_so=", "liq_dist_pct=", "r_eff_pct="):
            assert phai_co in t

    def test_chieu_SHORT_dao_dau_ca_tu_lan_mau(self) -> None:
        """Spec `:1856`: *"case LONG (SHORT đảo dấu)"*. SHORT có `sl` và giá thanh lý đều NẰM TRÊN giá vào —
        áp công thức Long vào đó sẽ ra mẫu số âm và chặn sạch mọi lệnh Short (đo được: 11 ca đỏ của
        `test_td0321` ở lượt chạy đầu của TD-0364)."""
        kq = xet_cong_l_z3(
            pair=PAIR, p=(98.0, 99.0, 100.0), sl=101.0, w=W, n_full=N_FULL, don_bay=DON_BAY,
            ham=_ham(119.0), nguong=8.0, tranche=1, la_short=True,
        )
        assert kq.qua is True  # p_avg = 99 ⇒ (119 − 99)/(101 − 99) = 10
        assert kq.dem is not None and kq.dem.ty_so == pytest.approx(10.0)
        assert kq.dem.r_eff_pct > 0 and kq.dem.liq_dist_pct > 0

    def test_chieu_SHORT_dem_mong_van_bi_TU_CHOI(self) -> None:
        kq = xet_cong_l_z3(
            pair=PAIR, p=(98.0, 99.0, 100.0), sl=101.0, w=W, n_full=N_FULL, don_bay=DON_BAY,
            ham=_ham(109.0), nguong=8.0, tranche=1, la_short=True,
        )
        assert kq.qua is False and kq.dem is not None and kq.dem.ty_so == pytest.approx(5.0)

    def test_chieu_SHORT_bao_hang_giá_thanh_ly_cho_dung_chieu(self) -> None:
        """Hàm thanh lý phải được hỏi ĐÚNG hướng — hỏi sai hướng cho ra một giá vô nghĩa mà vẫn là một số."""
        thay: dict = {}

        def tinh(pair, open_rate, amount, stake, don_bay, la_short=False):
            thay["la_short"] = la_short
            return 119.0

        xet_cong_l_z3(
            pair=PAIR, p=(98.0, 99.0, 100.0), sl=101.0, w=W, n_full=N_FULL, don_bay=DON_BAY,
            ham=HamThanhLy(tinh=tinh, liquidation_buffer=0.05), nguong=8.0, tranche=1, la_short=True,
        )
        assert thay == {"la_short": True}

    def test_ham_5_doi_so_di_duong_SHORT_thi_TU_CHOI_co_ly_do(self) -> None:
        """Phiên `-f3` tái lập: hàm thanh lý viết theo giao ước 5 đối số mà đi chiều SHORT sẽ ăn `TypeError`.
        Nguy hơn cả `TypeError` là nếu ai bắt `Exception` quanh lời gọi thì nó thành *từ chối im lặng mọi lệnh
        Short*. Ở đây nó phải thành một TỪ CHỐI CÓ LÝ DO ĐỌC ĐƯỢC."""

        def cu_5_doi_so(pair, open_rate, amount, stake_amount, leverage):
            return 119.0

        kq = xet_cong_l_z3(
            pair=PAIR, p=(98.0, 99.0, 100.0), sl=101.0, w=W, n_full=N_FULL, don_bay=DON_BAY,
            ham=HamThanhLy(tinh=cu_5_doi_so, liquidation_buffer=0.05), nguong=8.0, tranche=1, la_short=True,
        )
        assert kq.qua is False and kq.dem is None
        assert "la_short" in kq.ly_do and "SHORT" in kq.ly_do

    def test_giao_uoc_TinhLiq_khai_dung_thuc_te(self) -> None:
        """Giao ước phải KHAI có `la_short`, nếu không người tái dùng không có cách nào biết chiều Short cần gì."""
        import inspect

        from tool_d.ablation.thanh_ly import TinhLiq

        assert "la_short" in inspect.signature(TinhLiq.__call__).parameters

    def test_de_ghi_so_giu_None_khi_chua_do(self) -> None:
        assert de_ghi_so(None) is None
        so = de_ghi_so(_xet(liq=79.0).dem)
        assert set(so) >= {"liq_buffer_ratio", "liq_dist_pct", "r_eff_pct"}


def _mo_dun():
    if str(REPO_ROOT / "user_data/strategies") not in sys.path:
        sys.path.insert(0, str(REPO_ROOT / "user_data/strategies"))
    spec = importlib.util.spec_from_file_location("ZoneAbsorptionTD0364", NGUON_CHIEN_LUOC)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _chien_luoc():
    return _mo_dun().ZoneAbsorption(config={"stake_currency": "USDT", "exchange": {"name": "binance"}})


class TestTranche1:
    """`confirm_trade_entry` — cửa từ chối ĐƯỢC framework hỗ trợ (`raise` bị nuốt, MT-16 vii)."""

    @staticmethod
    def _dung(s, liq: dict | None):
        cho = {"co_lenh": {}, "ke_hoach": {}, "tag": {}}
        if liq is not None:
            cho["liq"] = liq
        s._cho[PAIR] = cho
        s.confirm_trade_entry.__func__.__globals__["KeHoachCoLenh"] = SimpleNamespace(from_dict=lambda d: SimpleNamespace())
        s._gia_luc_dat[PAIR] = (96.0, 95.0)  # LD-13 cho qua: thị trường TRÊN giá mua
        s._qua_san_tool_d = lambda *a, **k: True
        # Bước NGAY SAU cổng L-Z3 là dựng tham số cho `kiem_ket_nap` — nó hỏi DB Freqtrade (không có trong
        # unit test). Dựng mốc ở chính bước đó: tới được đây nghĩa là cổng đã cho qua.
        s._vi_the_mo_khac_theo_ke_hoach = lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("đã đi quá cổng L-Z3")
        )
        return s.confirm_trade_entry(PAIR, "limit", 1.0, 95.0, "PO", None, "{}", "long")

    def test_dem_mong_thi_TU_CHOI(self, caplog) -> None:
        caplog.set_level(logging.INFO)
        s = _chien_luoc()
        assert self._dung(s, {"qua": False, "ly_do": "LIQ_BUFFER_TU_CHOI ... (L-Z3, §6.4)", "so": None}) is False
        assert "LIQ_BUFFER_TU_CHOI" in caplog.text
        assert PAIR not in s._cho, "kế hoạch phải bị dọn khi lệnh không được mở"

    def test_thieu_khoa_liq_thi_TU_CHOI_fail_closed(self, caplog) -> None:
        """Kế hoạch không đi qua đường định cỡ hiện tại ⇒ cổng chưa từng được xét ⇒ không được coi là đã qua."""
        caplog.set_level(logging.INFO)
        s = _chien_luoc()
        assert self._dung(s, None) is False
        assert "LIQ_BUFFER_CHUA_XET" in caplog.text

    def test_dem_day_thi_DI_TIEP_toi_cong_ket_nap(self) -> None:
        """Cổng không được nuốt lệnh hợp lệ."""
        s = _chien_luoc()
        with pytest.raises(AssertionError, match="đã đi quá cổng L-Z3"):
            self._dung(s, {"qua": True, "ly_do": "", "so": {"liq_buffer_ratio": 10.0}})


class TestTranche23:
    """`adjust_trade_position` — chốt RIÊNG, vì `confirm_trade_entry` không được gọi cho tranche 2/3."""

    @staticmethod
    def _dung(s, *, liq: float | None):
        m = _mo_dun()
        kh = m.KeHoachTranche(
            zone_low=98.0, zone_high=100.0, p1=P[0], p2=P[1], p3=P[2], sl=SL,
            r_eff_plan=0.03, atr_1h_tai_tranche1=1.0,
        )
        cl = m.KeHoachCoLenh(
            arm="Z0", n_full_usdt=N_FULL, w_tranche=W, l_exchange=DON_BAY, rho_pct=0.375,
            rho_eff_pct=0.375, mult={}, r_eff=0.03, planned_risk_usdt=9.0, planned_margin_usdt=100.0,
        )
        trade = SimpleNamespace(
            pair=PAIR, has_open_orders=False, nr_of_successful_exits=0, nr_of_successful_entries=1,
            is_short=False, id=1,
        )
        s._xet_tp1 = lambda *a, **k: None
        s._doc_ke_hoach = lambda t: (kh, cl, {})
        s._ham_tl, s._ham_tl_da_thu = _ham(liq), True
        s._zss_hien_tai = lambda *a, **k: (_ for _ in ()).throw(AssertionError("đã đi quá cổng L-Z3"))
        return s.adjust_trade_position(
            trade, None, 99.5, 0.0, 1.0, 1000.0,
            current_entry_rate=99.5, current_exit_rate=99.5, current_entry_profit=0.0, current_exit_profit=0.0,
        )

    def test_dem_mong_thi_KHONG_BOM_THEM(self, caplog) -> None:
        caplog.set_level(logging.INFO)
        s = _chien_luoc()
        assert self._dung(s, liq=89.0) is None  # tỉ số 5 < 8
        assert "LIQ_BUFFER_TU_CHOI" in caplog.text and "tranche=2" in caplog.text

    def test_khong_tinh_duoc_thi_KHONG_BOM_THEM(self) -> None:
        s = _chien_luoc()
        assert self._dung(s, liq=None) is None

    def test_dem_day_thi_DI_TIEP(self) -> None:
        s = _chien_luoc()
        with pytest.raises(AssertionError, match="đã đi quá cổng L-Z3"):
            self._dung(s, liq=79.0)


class TestVetTrongMa:
    @staticmethod
    def _than(ten_ham: str) -> str:
        nguon = NGUON_CHIEN_LUOC.read_text(encoding="utf-8")
        cay = ast.parse(nguon)
        lop = next(n for n in cay.body if isinstance(n, ast.ClassDef) and n.name == "ZoneAbsorption")
        ham = next(n for n in lop.body if isinstance(n, ast.FunctionDef) and n.name == ten_ham)
        return ast.get_source_segment(nguon, ham) or ""

    @staticmethod
    def _ten_ham_duoc_goi(nguon: Path) -> set[str]:
        """Tên các hàm THỰC SỰ được gọi, lấy bằng AST.

        🔑 Không dùng `in nguon` cho việc này: ba ca đỏ đầu tiên của chính file test này là do chuỗi cần kiểm
        nằm trong đúng dòng CHÚ THÍCH giải thích nó (cùng hình dạng `L-Z25`/`L-Z46` đã gặp). Dấu hiệu cú pháp
        không đo được tính chất ngữ nghĩa — bài học 08/09/2026.
        """
        ten: set[str] = set()
        for n in ast.walk(ast.parse(nguon.read_text(encoding="utf-8"))):
            if isinstance(n, ast.Call):
                f = n.func
                ten.add(f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else "")
        return ten

    def test_cong_dung_TRUOC_ket_nap_danh_muc(self) -> None:
        """An toàn của CHÍNH lệnh này hỏi trước, danh mục hỏi sau."""
        than = self._than("confirm_trade_entry")
        assert than.index('cho.get("liq")') < than.index("kq = kiem_ket_nap(")

    def test_tranche_2_3_co_chot_rieng(self) -> None:
        assert "_xet_cong_thanh_ly" in self._than("adjust_trade_position")

    def test_khong_dung_san_thu_hai(self) -> None:
        """`tinh_liq_freqtrade()` dựng một `Exchange` MỚI — trong chiến lược phải dùng sàn của bộ chạy
        (`ham_tu_exchange`), nếu không backtest và live có thể lệch mà không ai thấy (DR-D4-05)."""
        goi = self._ten_ham_duoc_goi(NGUON_CHIEN_LUOC)
        assert "tinh_liq_freqtrade" not in goi
        assert "ham_tu_exchange" in goi

    def test_khong_bia_so_khi_chua_do(self) -> None:
        """Tầng cổng không được có một hằng `0.0` nào trong MÃ (chú thích thì được) — N6 cấm điền số thay cho
        "chưa đo được"."""
        cay = ast.parse((REPO_ROOT / "src/tool_d/cong_thanh_ly.py").read_text(encoding="utf-8"))
        hang_so_0 = [
            n for n in ast.walk(cay)
            if isinstance(n, ast.Constant) and isinstance(n.value, float) and n.value == 0.0
        ]
        assert hang_so_0 == []
