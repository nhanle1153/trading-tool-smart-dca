"""TD-0247 (`DR-D1-02`) — src/tool_d/pool_t1.py: hai bộ lọc ranh giới
cho việc dựng lại rổ pool point-in-time tại `T1`."""

from __future__ import annotations

from tool_d.pool_t1 import loai_tru_explore_hien_tai, loai_tru_tradifi_perpetual


def _symbol(symbol: str, contract_type: str = "PERPETUAL") -> dict:
    return {"symbol": symbol, "contractType": contract_type}


class TestLoaiTruExploreHienTai:
    def test_ma_dang_explore_bi_loai_du_du_tieu_chi_tai_t1(self) -> None:
        # Đúng tình huống DR-D1-02: 9 mã đủ tiêu chí tại T1 nhưng đang
        # bị config/pool.yaml (09/2026) xếp vào explore.
        ung_vien = ("ARKMUSDT", "BRETTUSDT", "AAAUSDT")
        explore_hien_tai = ("ARKMUSDT", "BRETTUSDT", "ZZZUSDT")
        assert loai_tru_explore_hien_tai(ung_vien, explore_hien_tai) == ("AAAUSDT",)

    def test_ma_khong_trong_explore_thi_giu_nguyen(self) -> None:
        assert loai_tru_explore_hien_tai(("AAAUSDT", "BBBUSDT"), ()) == ("AAAUSDT", "BBBUSDT")

    def test_khong_lam_thay_doi_thu_tu(self) -> None:
        ung_vien = ("ZUSDT", "AUSDT", "MUSDT")
        assert loai_tru_explore_hien_tai(ung_vien, ("MUSDT",)) == ("ZUSDT", "AUSDT")

    def test_danh_sach_explore_rong_khong_loai_gi(self) -> None:
        ung_vien = ("AAAUSDT",)
        assert loai_tru_explore_hien_tai(ung_vien, frozenset()) == ung_vien


class TestLoaiTruTradifiPerpetual:
    def test_ma_co_phieu_token_hoa_bi_loai(self) -> None:
        exchange_info = [
            _symbol("AAPLUSDT", contract_type="TRADIFI_PERPETUAL"),
            _symbol("BTCUSDT", contract_type="PERPETUAL"),
        ]
        ung_vien = ("AAPLUSDT", "BTCUSDT")
        assert loai_tru_tradifi_perpetual(ung_vien, exchange_info) == ("BTCUSDT",)

    def test_ma_da_huy_niem_yet_vang_mat_khoi_exchange_info_khong_bi_loai(self) -> None:
        # BTTUSDT (ví dụ DR-D1-01) không còn xuất hiện trong exchangeInfo
        # hôm nay dưới bất kỳ contractType nào — đây chính là loại mã
        # data.binance.vision tồn tại để giữ dấu vết, KHÔNG được loại.
        exchange_info = [_symbol("BTCUSDT", contract_type="PERPETUAL")]
        ung_vien = ("BTCUSDT", "BTTUSDT")
        assert loai_tru_tradifi_perpetual(ung_vien, exchange_info) == ("BTCUSDT", "BTTUSDT")

    def test_ma_perpetual_that_thi_giu_nguyen(self) -> None:
        exchange_info = [_symbol("AAAUSDT", contract_type="PERPETUAL")]
        assert loai_tru_tradifi_perpetual(("AAAUSDT",), exchange_info) == ("AAAUSDT",)

    def test_danh_sach_exchange_info_rong_khong_loai_gi(self) -> None:
        ung_vien = ("AAAUSDT", "BBBUSDT")
        assert loai_tru_tradifi_perpetual(ung_vien, []) == ung_vien

    def test_mot_ma_co_the_vua_perpetual_vua_khong_o_hai_ban_ghi_khac(self) -> None:
        # exchangeInfo trả MỘT bản ghi cho mỗi symbol tại một thời điểm —
        # ca này canh rằng hàm đọc đúng trường, không giả định vị trí.
        exchange_info = [
            _symbol("ANTHROPICUSDT", contract_type="TRADIFI_PERPETUAL"),
        ]
        assert loai_tru_tradifi_perpetual(("ANTHROPICUSDT",), exchange_info) == ()
