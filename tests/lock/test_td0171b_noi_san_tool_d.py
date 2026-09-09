"""TD-0171b — nối `san_tool_d()` vào chiến lược (DR-D4-05 §2.1, phần C).

🔴 Trước bản này, phép kiểm sàn DUY NHẤT trên đường chạy là
`custom_stake_amount:449` — `raise SizingError` khi `stake1 < min_stake`.
Hai lỗi trong một dòng:

1. **`raise` trong callback bị Freqtrade NUỐT** (`strategy_safe_wrapper` hạ
   xuống WARNING, `rc = 0` — MT-16 vii) ⇒ lệnh biến mất **im lặng**, đúng
   thứ DR-D4-05 sinh ra để chặn. Một chốt fail-closed bị nuốt là một chốt
   KHÔNG TỒN TẠI.
2. **So với `min_stake` của Freqtrade**, tức sàn của ĐÚNG MỘT đường chạy
   (backtest vào lệnh, 5,53 ở mã sàn 5) — không phải sàn Tool D (`max` mọi
   đường chạy, 7,50). DR-D4-05 §2.1 chốt lấy `max` để backtest và live
   hành xử GIỐNG NHAU; dùng `min_stake` là bỏ đúng tính chất đó.

Bản này chuyển phép từ chối sang `confirm_trade_entry` — cửa từ chối
**được framework hỗ trợ** (trả `False`, không phải exception), nên nó
KHÔNG bị nuốt — và ghi một dòng log để phép từ chối **đếm được**, đúng
chữ "từ chối tường minh + ghi sổ" của DR.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

CHIEN_LUOC = Path(__file__).resolve().parents[2] / "user_data" / "strategies" / "ZoneAbsorption.py"


def _nguon() -> str:
    return CHIEN_LUOC.read_text(encoding="utf-8")


class TestBoLocTuMarket:
    def test_dung_bo_loc_ccxt_thanh_SymbolFilters(self) -> None:
        from tool_d.notional import bo_loc_tu_market

        market = {
            "limits": {"cost": {"min": 5.0}, "amount": {"min": 0.001}},
            "precision": {"amount": 0.001},
        }
        f = bo_loc_tu_market("BTC/USDT:USDT", market, gia=100_000.0)
        assert f.min_notional_usdt == 5.0
        assert f.min_qty == 0.001
        assert f.price == 100_000.0

    def test_thieu_gioi_han_thi_RAISE_khong_gan_0(self) -> None:
        """N6: thiếu dữ liệu sàn là *không đo được*, không phải *sàn = 0*.
        Gán 0 làm mọi mã "qua sàn" — fail-OPEN ở đúng chốt fail-closed."""
        from tool_d.notional import bo_loc_tu_market

        for hong in (
            {"limits": {"cost": {"min": None}, "amount": {"min": 0.001}}},
            {"limits": {"cost": {"min": 5.0}, "amount": {"min": None}}},
            {"limits": {}},
        ):
            with pytest.raises(ValueError):
                bo_loc_tu_market("X/USDT:USDT", hong, gia=1.0)

    def test_gia_khong_duong_thi_raise(self) -> None:
        from tool_d.notional import bo_loc_tu_market

        market = {"limits": {"cost": {"min": 5.0}, "amount": {"min": 0.001}}}
        with pytest.raises(ValueError):
            bo_loc_tu_market("X/USDT:USDT", market, gia=0.0)


class TestNoiVaoChienLuoc:
    def test_confirm_trade_entry_GOI_kiem_san_tool_d(self) -> None:
        """Chốt phải nằm ở cửa trả `bool`, KHÔNG ở `custom_stake_amount`."""
        src = _nguon()
        i_confirm = src.index("def confirm_trade_entry")
        i_ke_tiep = src.index("def order_filled")
        than = src[i_confirm:i_ke_tiep]
        assert "kiem_san_tool_d" in than, "phép kiểm sàn không nằm trong confirm_trade_entry"

    def test_KHONG_dung_min_stake_cua_freqtrade_lam_san(self) -> None:
        """`min_stake` là sàn của MỘT đường chạy; DR-D4-05 §2.1 đòi `max`
        mọi đường. Ca này ghim để không ai "đơn giản hoá" về lại min_stake."""
        src = _nguon()
        i = src.index("def confirm_trade_entry")
        than = src[i : src.index("def order_filled")]
        assert "min_stake" not in than

    def test_co_dong_log_de_tu_choi_DEM_DUOC(self) -> None:
        """Từ chối im lặng là thứ DR sinh ra để chặn — phải có dấu vết."""
        src = _nguon()
        assert 'SAN_TOOL_D' in src

    def test_custom_stake_amount_KHONG_con_DUNG_min_stake_lam_san(self) -> None:
        """🔴 Dòng `raise` cũ phải ĐI: nó bị nuốt, nên nó là một chốt không
        tồn tại — giữ lại là giữ một thứ trông như đang canh.

        Hỏi bằng **AST**: *"có DÙNG `min_stake` trong thân hàm không"*, chứ
        không phải *"có NHẮC TỚI không"*. Bản đầu của ca này khớp chuỗi và
        **bắt nhầm chính dòng chú thích giải thích vì sao không dùng nữa** —
        đúng hình dạng `L-Z25` đã gặp với `hyperopt`, và TD-0181 đã gặp lần
        thứ hai. AST bỏ qua chú thích, nên nó hỏi đúng câu.

        `min_stake` vẫn là THAM SỐ của callback (Freqtrade truyền vào, ta
        không bỏ được) — nên chỉ soi `body`, không soi `args`.
        """
        import ast

        cay = ast.parse(_nguon())
        ham = next(
            n for n in ast.walk(cay)
            if isinstance(n, ast.FunctionDef) and n.name == "custom_stake_amount"
        )
        dung = [
            n for lenh in ham.body for n in ast.walk(lenh)
            if isinstance(n, ast.Name) and n.id == "min_stake"
        ]
        assert not dung, (
            f"`min_stake` còn được DÙNG {len(dung)} lần trong custom_stake_amount — "
            "sàn phải kiểm ở confirm_trade_entry, nơi từ chối không bị nuốt"
        )


class TestChotCoRANG:
    """🔴 Ba ca ĐẦU của file này đều là phép kiểm TĨNH (AST/chuỗi) — chúng
    chứng minh mã có HÌNH DẠNG đúng, **không** chứng minh nó HÀNH XỬ đúng.

    Phá thật lần đầu (cho nhánh không-đọc-được-bộ-lọc trả `True`, tức
    fail-OPEN) → **7/7 vẫn xanh**. Tức chính file này từng là một PASS RỖNG,
    đúng họ lỗi dự án đã đếm tới cái thứ sáu. Ba ca dưới đây gọi THẲNG hàm.
    """

    @staticmethod
    def _nap():
        import importlib.util

        spec = importlib.util.spec_from_file_location("za_td0171b", CHIEN_LUOC)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    @staticmethod
    def _gia(mod, markets):
        from types import SimpleNamespace

        tu = SimpleNamespace(
            dp=SimpleNamespace(_exchange=SimpleNamespace(_markets=markets)),
            stoploss=-0.99,
        )
        return mod.ZoneAbsorption._qua_san_tool_d.__get__(tu, mod.ZoneAbsorption)

    @staticmethod
    def _ke_hoach(notional: float):
        from types import SimpleNamespace

        return SimpleNamespace(notional_tranche=lambda i: notional)

    MARKET = {"limits": {"cost": {"min": 5.0}, "amount": {"min": 0.001}}}

    def test_khong_doc_duoc_bo_loc_thi_TU_CHOI(self) -> None:
        """Ca fail-closed. Đây chính là ca mà phép phá đầu tiên vô hiệu hoá
        mà không test nào báo đỏ."""
        mod = self._nap()
        ham = self._gia(mod, {})  # không có pair nào → KeyError
        assert ham("X/USDT:USDT", self._ke_hoach(1000.0), 1.0) is False

    def test_duoi_san_thi_TU_CHOI(self) -> None:
        mod = self._nap()
        ham = self._gia(mod, {"X/USDT:USDT": self.MARKET})
        # sàn Tool D ở mã sàn 5 = 7,50
        assert ham("X/USDT:USDT", self._ke_hoach(7.49), 1.0) is False

    def test_tren_san_thi_CHO_QUA(self) -> None:
        """Cần ca này để chốt không phải "luôn từ chối" — một chốt luôn
        đóng cũng thoả hai ca trên."""
        mod = self._nap()
        ham = self._gia(mod, {"X/USDT:USDT": self.MARKET})
        assert ham("X/USDT:USDT", self._ke_hoach(7.51), 1.0) is True


# 🔴 KHOẢNG TRỐNG CÒN LẠI, ghi ra thay vì ship một phép kiểm không giải
# thích được — và nó là khoảng trống ĐÚNG CHỖ NGUY HIỂM NHẤT.
#
# Chốt fail-closed đọc `_markets`; nếu dict đó rỗng thì nó từ chối MỌI lệnh
# trong IM LẶNG, backtest ra 0 lệnh, và toàn bộ ca tĩnh phía trên vẫn xanh —
# đúng bài học TD-0188 (*"canh đúng chỗ nhưng đường chạy không bao giờ qua"*).
# Nên ở đây CẦN một ca đòi dấu vết `SAN_TOOL_D` trên lượt chạy THẬT.
#
# Tôi đã viết ca đó và **không làm cho nó đáng tin được**: gọi `_chay()` của
# TD-0187 ngoài fixture của chính nó thì log trả về 59k ký tự mà **KHÔNG có
# `SAN_TOOL_D` LẪN `KET_NAP`** — trong khi ca `KET_NAP` của TD-0188 lại XANH
# trong suite trên cùng hàm ấy. Tức chênh lệch nằm ở điều kiện chạy fixture
# mà tôi chưa truy ra, KHÔNG phải ở chốt. Ship một ca đỏ vì lý do chưa hiểu
# thì sớm muộn bị gỡ, và gỡ rồi mất luôn phần đúng của nó (bài học phân vị
# TD-0168); ship một ca xanh nhờ nới điều kiện thì tệ hơn nữa.
#
# Cái đang đỡ chỗ này, và giới hạn của nó:
#   - `TestChotCoRANG` gọi THẲNG `_qua_san_tool_d` — đã bắt được phép phá
#     fail-OPEN mà 7 ca tĩnh để lọt. Nhưng nó dựng `self` giả, nên KHÔNG
#     chứng minh `_markets` có dữ liệu trên đường backtest thật.
#   - `test_td0187_*` xanh trên CÙNG chiến lược này ⇒ backtest vẫn sinh lệnh
#     ⇒ chốt đã cho qua ít nhất một lần. Đây là suy luận GIÁN TIẾP, ở file
#     khác, và sẽ im lặng nếu ai đó đổi fixture của họ.
#
# ⇒ Việc còn nợ: nối ca dấu vết vào đúng fixture module-scope của TD-0187.
