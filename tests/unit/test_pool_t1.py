"""TD-0247 (`DR-D1-02`) — src/tool_d/pool_t1.py: hai bộ lọc ranh giới
cho việc dựng lại rổ pool point-in-time tại `T1`."""

from __future__ import annotations

from tool_d.pool_t1 import loai_tru_explore_hien_tai, loai_tru_tradifi_perpetual


def _symbol(symbol: str, contract_type: str = "PERPETUAL") -> dict:
    return {"symbol": symbol, "contractType": contract_type}


class TestLoaiTruExploreHienTai:
    def test_ma_dang_explore_bi_loai_du_du_tieu_chi_tai_t1(self) -> None:
        # DR-D1-03 §1.1: tập truyền vào là mã CÓ DỮ LIỆU EXPLORE đã dùng
        # (vd 9 mã ARKM/BRETT/… của rổ T1), KHÔNG phải khối explore: 430 mã.
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


# ─────────────────────────────────────────────────────────────────────────────
# DR-D1-03 (17/09/2026) — tập EXPLORE đã dùng, dựng rổ tại mốc, ghép rổ cuối.
# ─────────────────────────────────────────────────────────────────────────────

from datetime import date  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402

from tool_d.api_client.binance_public import KhoLuuTruError, NenThangKhongCoError  # noqa: E402
from tool_d.pool_t1 import (  # noqa: E402
    ThuMucExploreError,
    dung_ro_tai_moc,
    ghep_ro_t1,
    ma_co_du_lieu_explore,
)

T1 = date(2025, 6, 12)
SAN_VOL = 15_000_000.0


class TestMaCoDuLieuExplore:
    def _tao(self, thu_muc: Path, ten: list[str]) -> Path:
        thu_muc.mkdir(parents=True, exist_ok=True)
        for t in ten:
            (thu_muc / t).write_bytes(b"")
        return thu_muc

    def test_suy_ten_ma_tu_moi_loai_file_futures(self, tmp_path: Path) -> None:
        d = self._tao(
            tmp_path / "futures",
            [
                "ARKM_USDT_USDT-1h-futures.feather",
                "ARKM_USDT_USDT-1h-funding_rate.feather",
                "1000PEPE_USDT_USDT-4h-mark.feather",
                "币安人生_USDT_USDT-1d-futures.feather",
                "ghi-chu.txt",
            ],
        )
        assert ma_co_du_lieu_explore(d) == frozenset({"ARKMUSDT", "1000PEPEUSDT", "币安人生USDT"})

    def test_thu_muc_khong_ton_tai_thi_TU_CHOI_khong_tra_tap_rong(self, tmp_path: Path) -> None:
        with pytest.raises(ThuMucExploreError):
            ma_co_du_lieu_explore(tmp_path / "khong-co")

    def test_thu_muc_khong_co_feather_thi_TU_CHOI(self, tmp_path: Path) -> None:
        d = self._tao(tmp_path / "futures", ["README.md"])
        with pytest.raises(ThuMucExploreError):
            ma_co_du_lieu_explore(d)

    def test_feather_sai_quy_uoc_ten_thi_TU_CHOI_khong_doan(self, tmp_path: Path) -> None:
        d = self._tao(tmp_path / "futures", ["ARKM_USDT_USDT-1h-futures.feather", "la.feather"])
        with pytest.raises(ThuMucExploreError):
            ma_co_du_lieu_explore(d)


def _khoang(thang_dau: str, thang_cuoi: str = "2026-08") -> dict:
    return {"thang_dau": thang_dau, "thang_cuoi": thang_cuoi}


def _doc_gia(bang: dict) -> callable:
    """bang[(sym, nam, thang)] = dict ngày→volume, hoặc exception để raise."""

    def doc(sym: str, nam: int, thang: int):
        v = bang.get((sym, nam, thang))
        if v is None:
            raise NenThangKhongCoError(f"404 {sym} {nam}-{thang}")
        if isinstance(v, Exception):
            raise v
        return v

    return doc


def _dung(khoang: dict, bang: dict):
    return dung_ro_tai_moc(
        T1, khoang, doc_volume_thang=_doc_gia(bang), age_floor_days=180, volume_floor_usdt=SAN_VOL
    )


class TestDungRoTaiMoc:
    def test_du_tuoi_du_volume_thi_vao_ro(self) -> None:
        kq = _dung({"AUSDT": _khoang("2023-01")}, {("AUSDT", 2025, 6): {T1: SAN_VOL * 2}})
        assert kq.pool_dung == ("AUSDT",)
        assert kq.onboard_xap_xi == 1 and kq.onboard_chinh_xac == ()

    def test_volume_duoi_san_thi_truot(self) -> None:
        kq = _dung({"AUSDT": _khoang("2023-01")}, {("AUSDT", 2025, 6): {T1: SAN_VOL - 1}})
        assert kq.pool_dung == ()

    def test_kho_404_ghi_rieng_KHONG_tinh_la_truot(self) -> None:
        kq = _dung({"AUSDT": _khoang("2023-01")}, {})
        assert kq.pool_dung == () and kq.khong_do_duoc_404 == ("AUSDT",)
        assert kq.khong_do_duoc_thieu_ngay == ()

    def test_thieu_hang_dung_ngay_t1_ghi_rieng(self) -> None:
        kq = _dung({"AUSDT": _khoang("2023-01")}, {("AUSDT", 2025, 6): {date(2025, 6, 20): SAN_VOL * 2}})
        assert kq.pool_dung == () and kq.khong_do_duoc_thieu_ngay == ("AUSDT",)

    def test_sat_nguong_doc_NGAY_onboard_chinh_xac_va_no_quyet_dinh_ket_qua(self) -> None:
        """Kiểm có răng: mốc THÁNG 2024-12-01 cho tuổi 193 ngày (qua 180), nhưng
        ngày thật 2024-12-20 cho 174 ngày (trượt). Hàm phải đọc ngày thật."""
        bang = {
            ("AUSDT", 2025, 6): {T1: SAN_VOL * 2},
            ("AUSDT", 2024, 12): {date(2024, 12, 20): 1.0, date(2024, 12, 21): 1.0},
        }
        kq = _dung({"AUSDT": _khoang("2024-12")}, bang)
        assert kq.onboard_chinh_xac == ("AUSDT",)
        assert kq.pool_dung == ()

    def test_ma_chet_truoc_thang_t1_khong_la_ung_vien(self) -> None:
        khoang = {"AUSDT": _khoang("2023-01"), "DEADUSDT": _khoang("2023-01", "2025-03")}
        bang = {("AUSDT", 2025, 6): {T1: SAN_VOL * 2}, ("DEADUSDT", 2025, 6): {T1: SAN_VOL * 2}}
        kq = _dung(khoang, bang)
        assert kq.ung_vien_song == ("AUSDT",) and kq.pool_dung == ("AUSDT",)

    def test_ma_huy_niem_yet_cuoi_thang_t1_van_tinh_tai_t1(self) -> None:
        khoang = {"AUSDT": _khoang("2023-01"), "BUSDT": _khoang("2023-01", "2025-06")}
        bang = {("AUSDT", 2025, 6): {T1: SAN_VOL * 2}, ("BUSDT", 2025, 6): {T1: SAN_VOL * 2}}
        assert _dung(khoang, bang).pool_dung == ("AUSDT", "BUSDT")

    def test_loi_mang_KHONG_bi_nuot(self) -> None:
        bang = {("AUSDT", 2025, 6): KhoLuuTruError("mạng hỏng")}
        with pytest.raises(KhoLuuTruError):
            _dung({"AUSDT": _khoang("2023-01")}, bang)

    def test_khoang_rong_thi_tu_choi(self) -> None:
        with pytest.raises(ValueError):
            _dung({}, {})


class TestGhepRoT1:
    def test_loai_explore_va_tradifi_ghi_rieng_ly_do(self) -> None:
        ro = ghep_ro_t1(
            ("CUSDT", "AUSDT", "ARKMUSDT", "AAPLUSDT"),
            frozenset({"ARKMUSDT", "ZZZUSDT"}),
            [_symbol("AAPLUSDT", "TRADIFI_PERPETUAL"), _symbol("AUSDT")],
        )
        assert ro.trading == ("AUSDT", "CUSDT")
        assert ro.loai_explore_da_dung == ("ARKMUSDT",)
        assert ro.loai_tradifi == ("AAPLUSDT",)
