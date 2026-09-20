"""🔒 TD-0355/TD-0356 (`DR-D4-20`) — luật post-only LD-13 trên đường vào lệnh THẬT.

Ba tầng, mỗi tầng hỏi một câu khác nhau:
1. **Tầng thuần** (`tool_d/post_only.py`) — luật đúng chưa, hai chiều, ca biên, đầu vào rác.
2. **Tranche 1** (`confirm_trade_entry`) — chốt có nằm trên đường chạy thật không, có fail-closed khi
   thiếu số để so không, và có đứng TRƯỚC các phép kiểm tốn công khác không.
3. **Tranche 2/3** (`adjust_trade_position`) — chiều cổng đã đảo: đặt lệnh chờ khi giá còn ở phía maker.
   (Bốn ca chiều nằm ở `test_td0321_duong_short_backtest_that.py`, đã đảo cùng ngày; ở đây kiểm phần
   `confirm_trade_entry` KHÔNG được gọi cho tranche 2/3 — Freqtrade chỉ gọi nó khi `not pos_adjust`,
   `backtesting.py:1190` — nên chốt của tranche 2/3 bắt buộc phải nằm trong `adjust_trade_position`.)

🔴 Đường chạy THẬT của bản vá đã được các test backtest thật canh: `test_td0187_*`, `test_td0321_*`,
`test_lz49_lz50_*` (đều xanh sau vá). Số trên dữ liệu thị trường thật là việc của `TD-0358`.
"""

from __future__ import annotations

import ast
import importlib.util
import logging
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from tool_d.post_only import PostOnlyError, bi_san_tu_choi, ly_do_tu_choi

REPO_ROOT = Path(__file__).resolve().parents[2]
NGUON_CHIEN_LUOC = REPO_ROOT / "user_data/strategies/ZoneAbsorption.py"
PAIR = "LTC/USDT:USDT"


class TestTangThuan:
    @pytest.mark.parametrize(
        "gia_lenh,gia_tt,la_short,bi_tu_choi",
        [
            (100.0, 99.0, False, True),    # LONG: mua 100 khi thị trường 99 ⇒ lấy thanh khoản ⇒ từ chối
            (100.0, 101.0, False, False),  # LONG: mua 100 khi thị trường 101 ⇒ nằm chờ ⇒ hợp lệ
            (100.0, 101.0, True, True),    # SHORT: bán 100 khi thị trường 101 ⇒ từ chối
            (100.0, 99.0, True, False),    # SHORT: bán 100 khi thị trường 99 ⇒ hợp lệ
        ],
    )
    def test_hai_chieu(self, gia_lenh, gia_tt, la_short, bi_tu_choi) -> None:
        assert bi_san_tu_choi(gia_lenh, gia_tt, la_short=la_short) is bi_tu_choi

    def test_bang_nhau_thi_cho_dat(self) -> None:
        """Lề nghiêng về phía CHO ĐẶT: lệnh đúng giá thị trường còn có thể nằm phía maker."""
        assert bi_san_tu_choi(100.0, 100.0, la_short=False) is False
        assert bi_san_tu_choi(100.0, 100.0, la_short=True) is False

    @pytest.mark.parametrize("xau", [0.0, -1.0, float("nan"), float("inf"), True, "95"])
    def test_dau_vao_rac_bi_tu_choi(self, xau) -> None:
        with pytest.raises(PostOnlyError):
            bi_san_tu_choi(xau, 100.0, la_short=False)
        with pytest.raises(PostOnlyError):
            bi_san_tu_choi(100.0, xau, la_short=False)

    def test_ly_do_dem_duoc(self) -> None:
        t = ly_do_tu_choi(PAIR, gia_lenh=95.0, gia_thi_truong=94.0, la_short=False, tranche=2)
        assert t.startswith("POST_ONLY_TU_CHOI ") and PAIR in t and "tranche=2" in t and "LD-13" in t


def _mo_dun():
    if str(REPO_ROOT / "user_data/strategies") not in sys.path:
        sys.path.insert(0, str(REPO_ROOT / "user_data/strategies"))
    spec = importlib.util.spec_from_file_location("ZoneAbsorptionTD0355", NGUON_CHIEN_LUOC)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _chien_luoc():
    return _mo_dun().ZoneAbsorption(config={"stake_currency": "USDT", "exchange": {"name": "binance"}})


class TestTranche1:
    """`confirm_trade_entry` — cửa từ chối ĐƯỢC framework hỗ trợ (trả `False`; `raise` bị nuốt, MT-16 vii)."""

    @staticmethod
    def _dung(s, *, gia_thi_truong: float, gia_lenh: float = 95.0):
        s._cho[PAIR] = {"co_lenh": {}, "ke_hoach": {}, "tag": {}}
        # Bước NGAY SAU chốt LD-13 là đọc kế hoạch cỡ lệnh; thay nó bằng vật tối thiểu để ca "đi tiếp"
        # dừng đúng ở `_qua_san_tool_d`, không vỡ vì một dict rỗng.
        s.confirm_trade_entry.__func__.__globals__["KeHoachCoLenh"] = SimpleNamespace(from_dict=lambda d: SimpleNamespace())
        s._gia_luc_dat[PAIR] = (gia_thi_truong, gia_lenh)
        s._qua_san_tool_d = lambda *a, **k: (_ for _ in ()).throw(AssertionError("đã đi quá chốt LD-13"))
        return s.confirm_trade_entry(
            PAIR, "limit", 1.0, gia_lenh, "PO", None, "{}", "long"
        )

    def test_tu_choi_khi_thi_truong_duoi_gia_lenh(self, caplog) -> None:
        caplog.set_level(logging.INFO)
        s = _chien_luoc()
        assert self._dung(s, gia_thi_truong=94.0) is False
        assert "POST_ONLY_TU_CHOI" in caplog.text
        assert PAIR not in s._cho, "kế hoạch cỡ lệnh phải bị dọn khi lệnh không được đặt"

    def test_thieu_gia_thi_TU_CHOI_fail_closed(self) -> None:
        """Không có số để so ⇒ không biết sàn có nhận không ⇒ từ chối, không đoán (N6)."""
        s = _chien_luoc()
        s._cho[PAIR] = {"co_lenh": {}, "ke_hoach": {}, "tag": {}}
        s._gia_luc_dat.pop(PAIR, None)
        assert s.confirm_trade_entry(PAIR, "limit", 1.0, 95.0, "PO", None, "{}", "long") is False

    def test_hop_le_thi_DI_TIEP_toi_phep_kiem_san(self) -> None:
        """Chốt LD-13 không được nuốt lệnh hợp lệ: giá thị trường TRÊN giá mua ⇒ đi tiếp."""
        s = _chien_luoc()
        with pytest.raises(AssertionError, match="đã đi quá chốt LD-13"):
            self._dung(s, gia_thi_truong=96.0)

    def test_custom_entry_price_cat_lai_dung_hai_gia(self) -> None:
        """Nguồn DUY NHẤT của hai số: chính lời gọi Freqtrade vừa dùng để đặt lệnh."""
        s = _chien_luoc()
        tag = (
            '{"zl":94.65,"zh":95.35,"p1":95.35,"p2":95.0,"p3":94.65,"sl":94.2,'
            '"zs":0.6,"t4":"UP","sw":1743000000000}'
        )
        gia = s.custom_entry_price(PAIR, None, None, 96.0, tag, "long")
        assert gia == 95.35
        assert s._gia_luc_dat[PAIR] == (96.0, 95.35)


class TestThuTuTrongMa:
    @staticmethod
    def _than(ten_ham: str) -> str:
        cay = ast.parse(NGUON_CHIEN_LUOC.read_text(encoding="utf-8"))
        lop = next(n for n in cay.body if isinstance(n, ast.ClassDef) and n.name == "ZoneAbsorption")
        ham = next(n for n in lop.body if isinstance(n, ast.FunctionDef) and n.name == ten_ham)
        return ast.get_source_segment(NGUON_CHIEN_LUOC.read_text(encoding="utf-8"), ham) or ""

    def test_chot_ld13_dung_TRUOC_phep_kiem_ton_cong(self) -> None:
        than = self._than("confirm_trade_entry")
        assert than.index("bi_san_tu_choi") < than.index("kiem_ket_nap")
        assert than.index("bi_san_tu_choi") < than.index("_qua_san_tool_d")

    def test_tranche_2_3_co_chot_rieng(self) -> None:
        """Freqtrade KHÔNG gọi `confirm_trade_entry` cho tranche 2/3 (`backtesting.py:1190`,
        `if not pos_adjust`) ⇒ chốt phải nằm trong `adjust_trade_position`."""
        assert "bi_san_tu_choi" in self._than("adjust_trade_position")

    def test_khong_con_cong_chieu_cu(self) -> None:
        """Chiều cũ (*"chỉ bơm khi giá đã xuống tới mức"*) không được lặng lẽ quay lại."""
        than = self._than("adjust_trade_position")
        assert "current_rate > muc" not in than and "current_rate < muc" not in than
