"""TD-0239 — bộ sinh `VAO_RA_LENH` (`src/tool_d/vao_ra_lenh.py`), §8.3.

Test ĐƠN VỊ cho hàm thuần. Phần đo trên lệnh THẬT (chạy một lượt backtest
thật rồi đối chiếu số bản ghi với số fill, chạy lại cùng timerange ⇒ thêm
0 dòng) thuộc `tests/lock/test_td0239_vao_lenh_noi_vao_chien_luoc.py` —
cùng bài học `TD-0168` áp cho `test_gap_ms.py`: một hàm chỉ được canh
bằng mẫu dựng tay chưa chắc nằm trên đường sản xuất.
"""

from __future__ import annotations

from datetime import datetime

from tool_d.ledger.decision_log import NGUON_HOP_LE, TRUONG_KHOA, dedup_key
from tool_d.vao_ra_lenh import LOAI_VAO_RA_LENH, sinh_ban_ghi_vao_lenh

T0 = datetime(2026, 1, 1, 12, 0, 0)


def _ban_ghi(**ghi_de: object) -> dict:
    mac_dinh = dict(
        order_id="EX-ORDER-1",
        ts=T0,
        trade_id=42,
        pair="BTC/USDT:USDT",
        tranche=1,
        side="buy",
        price=41850.0,
        amount=0.012,
        nguon="backtest",
    )
    mac_dinh.update(ghi_de)
    return sinh_ban_ghi_vao_lenh(**mac_dinh)


class TestHinhDangBanGhi:
    def test_du_moi_truong_bat_buoc_cua_loai(self) -> None:
        """Bản ghi phải mang đủ trường mà `TRUONG_KHOA["VAO_RA_LENH"]`
        đòi — nếu không, `decision_log.dedup_key()` sẽ raise ở cửa ghi
        (điểm nghẽn duy nhất), và fail-closed đó sẽ bị Freqtrade nuốt
        trong callback (`TD-0187`). Ca này bắt lỗi TẠI ĐÂY, rẻ hơn nhiều
        so với chờ nó nổ giữa một lượt backtest."""
        bg = _ban_ghi()
        for truong in TRUONG_KHOA["VAO_RA_LENH"]:
            assert truong in bg, f"thiếu trường khoá bắt buộc {truong!r}"
            assert bg[truong], f"trường khoá {truong!r} rỗng"

    def test_loai_va_nguon_dung(self) -> None:
        bg = _ban_ghi()
        assert bg["loai"] == LOAI_VAO_RA_LENH == "VAO_RA_LENH"
        assert bg["nguon"] in NGUON_HOP_LE

    def test_ts_da_chuyen_thanh_chuoi_isoformat(self) -> None:
        """`decision_log` ghi JSON — `datetime` thô không tuần tự hoá
        được, phải chuyển ở NGUỒN, không phải ở cửa ghi."""
        bg = _ban_ghi()
        assert isinstance(bg["ts"], str)
        assert bg["ts"] == T0.isoformat()

    def test_giu_nguyen_cac_truong_khong_thuoc_khoa(self) -> None:
        """`tranche`/`pair`/`side`/`price`/`amount` KHÔNG tham gia khoá
        dedup (TRUONG_KHOA chỉ đòi `exchange_order_id`) nhưng vẫn phải có
        mặt trong bản ghi — đây là NỘI DUNG, không phải phần định danh."""
        bg = _ban_ghi(tranche=2, pair="ETH/USDT:USDT", side="sell",
                      price=2500.5, amount=1.25)
        assert bg["tranche"] == 2
        assert bg["pair"] == "ETH/USDT:USDT"
        assert bg["side"] == "sell"
        assert bg["price"] == 2500.5
        assert bg["amount"] == 1.25


class TestDiQuaCuaGhiThat:
    """Không tin bảng của chính module — gọi thẳng `dedup_key()` của
    `decision_log.py`, đúng đường mà `ghi_neu_chua_co()` sẽ đi qua."""

    def test_dedup_key_dung_duoc_exchange_order_id(self) -> None:
        bg = _ban_ghi(order_id="EX-999")
        assert dedup_key(bg) == "EX-999"

    def test_hai_tranche_khac_nhau_cung_trade_khong_trung_khoa(self) -> None:
        """Đúng lý do `TRUONG_KHOA` khoá theo `order_id` từng tranche,
        KHÔNG theo `trade_id` (spec §8.3) — nếu khoá theo `trade_id` thì
        ba tranche của một lệnh DCA sẽ gộp thành một, mất đúng thứ Tool D
        sinh ra để đo."""
        bg1 = _ban_ghi(order_id="EX-1", trade_id=7, tranche=1)
        bg2 = _ban_ghi(order_id="EX-2", trade_id=7, tranche=2)
        assert dedup_key(bg1) != dedup_key(bg2)

    def test_nguon_sai_thi_dedup_key_raise(self) -> None:
        """Kiểm-có-răng cho chính TD-0201 — không phải luật do module này
        tự đặt ra, mà là luật của `decision_log.py` mà module này phải
        tuân theo."""
        import pytest
        from tool_d.ledger.decision_log import DecisionLogError

        bg = _ban_ghi(nguon="khong-hop-le")
        with pytest.raises(DecisionLogError):
            dedup_key(bg)
