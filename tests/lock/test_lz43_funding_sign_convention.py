"""L-Z43 (§4c.2, TD-0122) — khoá chiều dấu funding. Sai dấu hoặc sai
cột dữ liệu → DG7 và DG6-D IM LẶNG không bao giờ kích hoạt, backtest
vẫn sạch (LD-14) — đây là loại lỗi nguy hiểm nhất vì không gây crash.

Test khoá cứng chiều dấu: một lệnh LONG giả lập qua 3 mốc funding
DƯƠNG (LONG trả funding khi rate > 0, §4c.2) phải cho
`funding_paid_cumulative > 0` — tức thật sự bị coi là "đã trả".
"""

from __future__ import annotations

from tool_d.funding_stop import funding_paid_cumulative


class TestChieuDauFreqtrade:
    def test_long_qua_3_moc_funding_duong_thi_cumulative_duong(self) -> None:
        # Freqtrade quy ước ÂM = đã trả. LONG trả funding 3 lần liên
        # tiếp khi rate > 0 -> trade.funding_fees cộng dồn ÂM.
        mot_moc = -0.05
        trade_funding_fees_sau_3_moc = mot_moc * 3
        assert funding_paid_cumulative(trade_funding_fees_sau_3_moc) > 0

    def test_dao_dau_sai_se_bi_bat(self) -> None:
        # Nếu ai đó vô tình bỏ dấu trừ (bug LD-14 mô tả), giá trị sẽ
        # ÂM thay vì dương -> test trên sẽ FAIL, đúng mục đích khoá.
        trade_funding_fees_sau_3_moc = -0.15
        gia_tri_dung = funding_paid_cumulative(trade_funding_fees_sau_3_moc)
        gia_tri_sai_neu_quen_dao_dau = trade_funding_fees_sau_3_moc
        assert gia_tri_dung != gia_tri_sai_neu_quen_dao_dau
        assert gia_tri_dung > 0 > gia_tri_sai_neu_quen_dao_dau

    def test_nhan_funding_rong_thi_cumulative_am(self) -> None:
        # Ròng lại NHẬN funding (Freqtrade ghi DƯƠNG) -> cumulative âm,
        # không bao giờ kích hoạt DG7 -- đúng thiết kế (§4c.2).
        assert funding_paid_cumulative(0.2) < 0
