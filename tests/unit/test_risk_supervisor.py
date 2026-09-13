"""🔒 TD-0196 (OQ-09) — Risk Supervisor §6.6, tầng THUẦN.

Không cần backtest/Docker-network thật ở đây (N7 áp cho bằng chứng chạm
DỮ LIỆU THỊ TRƯỜNG; đây là state machine + phân loại lỗi, không chạm gì
tới CALIB/WFO/LOCKBOX) — nhưng vẫn chạy trong Docker theo quy ước chung.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from tool_d.risk_supervisor import (
    BACKOFF_KHOI_DIEM_S,
    BACKOFF_TOI_DA_S,
    DUNG_HAN,
    HANG_SO_KHAI_LAI,
    KHONG_NHAN_DIEN,
    LIQUIDATED,
    LOI_LOGIC,
    NGUONG_BREAKER_MAC_DINH,
    OK,
    RETRY,
    UNREADABLE,
    KetQuaEndpoint,
    RiskSupervisorError,
    TrangThaiBenVung,
    TrangThaiBreaker,
    doc_nguong_breaker,
    doc_snapshot_an_toan,
    doc_trang_thai,
    ghi_nhan_ket_qua,
    kiem_khai_lai_khop_ban_goc,
    luu_trang_thai,
    phan_loai_ma_loi,
    phat_hien_thanh_ly,
    trang_thai_tai_khoan,
)

T0 = datetime(2026, 9, 10, 0, 0, 0, tzinfo=timezone.utc)


class TestDocNguongBreaker:
    def test_thieu_env_dung_mac_dinh_5(self) -> None:
        assert doc_nguong_breaker(env={}) == 5 == NGUONG_BREAKER_MAC_DINH

    def test_doc_dung_gia_tri_env(self) -> None:
        assert doc_nguong_breaker(env={"TOOLD_BREAKER_THRESHOLD": "7"}) == 7

    def test_env_khong_phai_so_RAISE(self) -> None:
        with pytest.raises(RiskSupervisorError):
            doc_nguong_breaker(env={"TOOLD_BREAKER_THRESHOLD": "abc"})

    def test_env_duoi_1_RAISE(self) -> None:
        with pytest.raises(RiskSupervisorError):
            doc_nguong_breaker(env={"TOOLD_BREAKER_THRESHOLD": "0"})


class TestPhanLoaiMaLoi:
    """Đối chiếu ĐÚNG bảng Mục 4.3 của api-integration-rules.md, không
    phải bảng chép tay ở đây — mọi ca dưới trỏ về đúng dòng của bảng đó."""

    @pytest.mark.parametrize("http", [429, 500, 502, 503, 599])
    def test_retry_theo_http(self, http: int) -> None:
        assert phan_loai_ma_loi(http_status=http) == RETRY

    @pytest.mark.parametrize("ma", [-1003, -1015])
    def test_retry_theo_ma_binance(self, ma: int) -> None:
        assert phan_loai_ma_loi(ma_binance=ma) == RETRY

    def test_418_la_dung_han(self) -> None:
        assert phan_loai_ma_loi(http_status=418) == DUNG_HAN

    @pytest.mark.parametrize("ma", [-1121, -2010, -2011, -2019])
    def test_loi_logic(self, ma: int) -> None:
        assert phan_loai_ma_loi(ma_binance=ma) == LOI_LOGIC

    def test_ma_khong_co_trong_bang_la_khong_nhan_dien(self) -> None:
        assert phan_loai_ma_loi(ma_binance=-99999) == KHONG_NHAN_DIEN
        assert phan_loai_ma_loi(http_status=404) == KHONG_NHAN_DIEN

    def test_khong_truyen_gi_RAISE(self) -> None:
        with pytest.raises(RiskSupervisorError):
            phan_loai_ma_loi()


class TestBreakerTichLuyRETRY:
    def test_duoi_nguong_khong_mo(self) -> None:
        tt = TrangThaiBreaker()
        for _ in range(NGUONG_BREAKER_MAC_DINH - 1):
            tt = ghi_nhan_ket_qua(tt, RETRY, now=T0)
        assert tt.mo_tam is False
        assert tt.so_loi_lien_tiep == NGUONG_BREAKER_MAC_DINH - 1
        assert tt.duoc_phep_goi(now=T0) is True

    def test_dung_nguong_thi_mo_va_backoff_khoi_diem(self) -> None:
        tt = TrangThaiBreaker()
        for _ in range(NGUONG_BREAKER_MAC_DINH):
            tt = ghi_nhan_ket_qua(tt, RETRY, now=T0)
        assert tt.mo_tam is True
        assert tt.backoff_s == BACKOFF_KHOI_DIEM_S

    def test_thanh_cong_reset_sach(self) -> None:
        tt = TrangThaiBreaker(so_loi_lien_tiep=4)
        tt = ghi_nhan_ket_qua(tt, None, now=T0)
        assert tt == TrangThaiBreaker()

    def test_backoff_nhan_doi_moi_lan_mo_lai_tu_dang_mo(self) -> None:
        """Kịch bản: breaker đã mở (backoff hiện tại > 0), tiếp tục nhận
        RETRY khi vẫn đang mở — backoff phải NHÂN ĐÔI từ giá trị đang có,
        không phải tính lại từ khởi điểm."""
        tt = TrangThaiBreaker(mo_tam=True, backoff_s=4.0, so_loi_lien_tiep=10, thoi_diem_mo=T0)
        tt = ghi_nhan_ket_qua(tt, RETRY, now=T0 + timedelta(seconds=1))
        assert tt.backoff_s == pytest.approx(8.0)

    def test_backoff_ket_tran_60s(self) -> None:
        tt = TrangThaiBreaker(mo_tam=True, backoff_s=40.0, so_loi_lien_tiep=10, thoi_diem_mo=T0)
        tt = ghi_nhan_ket_qua(tt, RETRY, now=T0)
        assert tt.backoff_s == BACKOFF_TOI_DA_S

    def test_chuoi_backoff_dung_1_2_4_8_16_32_60(self) -> None:
        tt = TrangThaiBreaker()
        for _ in range(NGUONG_BREAKER_MAC_DINH):
            tt = ghi_nhan_ket_qua(tt, RETRY, now=T0)
        ky_vong = [1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 60.0, 60.0]
        thuc_te = []
        for _ in ky_vong:
            thuc_te.append(tt.backoff_s)
            tt = ghi_nhan_ket_qua(tt, RETRY, now=T0)
        assert thuc_te == ky_vong


class TestLoiLogicVaKhongNhanDienKhongCongVaoBreaker:
    """🔴 Kiểm có răng — nếu ai đó lỡ gộp LOI_LOGIC vào nhánh RETRY, ca
    này bắt được ngay: 100 lỗi logic liên tiếp KHÔNG được mở breaker."""

    @pytest.mark.parametrize("loai", [LOI_LOGIC, KHONG_NHAN_DIEN])
    def test_khong_tang_bo_dem_du_lap_lai_nhieu_lan(self, loai: str) -> None:
        tt = TrangThaiBreaker()
        for _ in range(100):
            tt = ghi_nhan_ket_qua(tt, loai, now=T0)
        assert tt == TrangThaiBreaker()

    def test_loai_loi_la_chuoi_khac_RAISE(self) -> None:
        with pytest.raises(RiskSupervisorError):
            ghi_nhan_ket_qua(TrangThaiBreaker(), "khong-ton-tai", now=T0)


class TestDungHanLaCoDoVinhVien:
    def test_dat_co_dung_han(self) -> None:
        tt = ghi_nhan_ket_qua(TrangThaiBreaker(), DUNG_HAN, now=T0)
        assert tt.dung_han is True
        assert tt.duoc_phep_goi(now=T0) is False

    def test_thanh_cong_sau_do_KHONG_go_duoc_co(self) -> None:
        """Đúng chữ spec dòng 1965 — CỜ ĐỎ, không phải log cảnh báo tự
        phục hồi. Không hàm nào trong module này được phép gỡ nó."""
        tt = ghi_nhan_ket_qua(TrangThaiBreaker(), DUNG_HAN, now=T0)
        tt2 = ghi_nhan_ket_qua(tt, None, now=T0 + timedelta(hours=1))
        assert tt2.dung_han is True
        assert tt2 == tt

    def test_retry_sau_do_cung_khong_go_duoc(self) -> None:
        tt = ghi_nhan_ket_qua(TrangThaiBreaker(), DUNG_HAN, now=T0)
        tt2 = ghi_nhan_ket_qua(tt, RETRY, now=T0)
        assert tt2.dung_han is True


class TestDuocPhepGoi:
    def test_dang_trong_cua_so_backoff_tu_choi(self) -> None:
        tt = TrangThaiBreaker(mo_tam=True, thoi_diem_mo=T0, backoff_s=10.0)
        assert tt.duoc_phep_goi(now=T0 + timedelta(seconds=5)) is False

    def test_het_cua_so_backoff_cho_phep(self) -> None:
        tt = TrangThaiBreaker(mo_tam=True, thoi_diem_mo=T0, backoff_s=10.0)
        assert tt.duoc_phep_goi(now=T0 + timedelta(seconds=10)) is True

    def test_trang_thai_sach_luon_cho_phep(self) -> None:
        assert TrangThaiBreaker().duoc_phep_goi(now=T0) is True


class TestKhaiLaiCoChuDich:
    """L-Z44 — đối chiếu `HANG_SO_KHAI_LAI` với `tool_d_config.yaml` THẬT."""

    def test_khop_ban_goc_that(self) -> None:
        from tool_d.config.loader import load_tool_d_config, resolve

        cfg = load_tool_d_config()
        lech = kiem_khai_lai_khop_ban_goc(cfg, doc_resolve=resolve)
        assert lech == [], lech

    def test_KIEM_CO_RANG_lech_thi_bao_dung_truong(self) -> None:
        gia_lap = {"a": 1}

        def resolve_gia(_cfg: object, duong_dan: str) -> float:
            if duong_dan == "tier_a.E_D":
                return HANG_SO_KHAI_LAI.e_d + 1.0  # cố ý lệch
            return {
                "tier_c.dd_ladder_pct.soft": HANG_SO_KHAI_LAI.dd_soft_pct,
                "tier_c.dd_ladder_pct.halt": HANG_SO_KHAI_LAI.dd_halt_pct,
                "tier_c.dd_ladder_pct.abort": HANG_SO_KHAI_LAI.dd_abort_pct,
                # TD-0241 — thêm đường của `tran_margin_ty_le`. KHẲNG ĐỊNH
                # của ca này KHÔNG đổi (vẫn đúng 1 chỗ lệch, vẫn là `e_d`);
                # chỉ bộ giả lập được dạy thêm một đường mà hàm thật nay có
                # đối chiếu. Nếu ai đó gỡ dòng này cho "đỡ vướng" thì ca
                # quay về KeyError chứ không âm thầm xanh — nới ở đây là
                # nới thấy được.
                "tier_frozen.mult_deploy_thr.value": HANG_SO_KHAI_LAI.tran_margin_ty_le,
            }[duong_dan]

        lech = kiem_khai_lai_khop_ban_goc(gia_lap, doc_resolve=resolve_gia)
        assert len(lech) == 1
        assert "e_d" in lech[0]


class TestTrangThaiTaiKhoan:
    def test_true_la_liquidated(self) -> None:
        assert trang_thai_tai_khoan(la_thanh_ly=True) == LIQUIDATED

    def test_false_la_ok(self) -> None:
        assert trang_thai_tai_khoan(la_thanh_ly=False) == OK

    def test_none_la_unreadable_KHONG_phai_ok(self) -> None:
        """🔴 N6 — chốt quan trọng nhất của hàm này: không đọc được PHẢI
        khác OK, vì đây là cờ an toàn, im lặng ở đây là fail-OPEN."""
        assert trang_thai_tai_khoan(la_thanh_ly=None) == UNREADABLE
        assert UNREADABLE != OK


class TestSnapshotAnToanTungEndpoint:
    def test_mot_endpoint_loi_khong_lam_mat_ket_qua_endpoint_khac(self) -> None:
        def loi() -> None:
            raise RiskSupervisorError("mạng lỗi")

        kq = doc_snapshot_an_toan({"margin": lambda: 123.0, "vi_the": loi})
        assert kq["margin"] == KetQuaEndpoint(ten="margin", gia_tri=123.0, loi=None)
        assert kq["margin"].doc_duoc is True
        assert kq["vi_the"].doc_duoc is False
        assert "mạng lỗi" in kq["vi_the"].loi

    @pytest.mark.parametrize("loai_loi", [TimeoutError, ConnectionError])
    def test_timeout_va_connection_error_cung_duoc_co_lap(self, loai_loi: type[Exception]) -> None:
        def loi() -> None:
            raise loai_loi("mất kết nối")

        kq = doc_snapshot_an_toan({"x": loi})
        assert kq["x"].doc_duoc is False

    def test_KIEM_CO_RANG_loi_lap_trinh_KHONG_bi_nuot(self) -> None:
        """🔴 Cùng bài học MT-16(vii): một exception KHÔNG thuộc danh sách
        đã khai (lỗi lập trình thật của tầng gọi) PHẢI văng ra, không được
        `doc_snapshot_an_toan` nuốt thành 'unreadable' rồi che mất bug."""

        def loi_lap_trinh() -> None:
            raise TypeError("bug thật của code gọi, không phải lỗi mạng")

        with pytest.raises(TypeError):
            doc_snapshot_an_toan({"x": loi_lap_trinh})

    def test_khong_endpoint_nao_thi_tra_dict_rong(self) -> None:
        assert doc_snapshot_an_toan({}) == {}


class TestPhatHienThanhLy:
    """TD-0241 — `phat_hien_thanh_ly()` đọc `force_orders` (đã lọc
    `autoCloseType=LIQUIDATION` phía server)."""

    def test_mang_rong_la_khong_thanh_ly(self) -> None:
        assert phat_hien_thanh_ly([], tu_thoi_diem_ms=1000) is False

    def test_lenh_moi_hon_moc_la_thanh_ly(self) -> None:
        assert phat_hien_thanh_ly([{"time": 2000}], tu_thoi_diem_ms=1000) is True

    def test_lenh_dung_moc_tinh_la_thanh_ly(self) -> None:
        assert phat_hien_thanh_ly([{"time": 1000}], tu_thoi_diem_ms=1000) is True

    def test_lenh_cu_hon_moc_khong_tinh(self) -> None:
        """Lệnh thanh lý CŨ (trước khi vị thế hiện tại được mở) không được
        tính — nếu không, một lần thanh lý lịch sử sẽ mãi mãi khiến daemon
        báo LIQUIDATED dù tài khoản đã hồi phục và mở vị thế mới."""
        assert phat_hien_thanh_ly([{"time": 500}], tu_thoi_diem_ms=1000) is False

    def test_mot_lenh_moi_giua_nhieu_lenh_cu_van_bat_duoc(self) -> None:
        lenh = [{"time": 100}, {"time": 200}, {"time": 5000}]
        assert phat_hien_thanh_ly(lenh, tu_thoi_diem_ms=1000) is True

    def test_thieu_truong_time_RAISE_khong_doan(self) -> None:
        with pytest.raises(RiskSupervisorError, match="'time'"):
            phat_hien_thanh_ly([{"symbol": "BTCUSDT"}], tu_thoi_diem_ms=1000)


class TestBenVungTrangThaiQuaRestart:
    """TD-0241 — `luu_trang_thai()`/`doc_trang_thai()`. Bài học `MT-40`/
    `MT-41`: một cờ an toàn chỉ sống trong RAM là một cờ không tồn tại sau
    khi tiến trình restart."""

    def test_chua_co_file_tra_ve_trang_thai_sach(self, tmp_path) -> None:
        duong_dan = tmp_path / "khong_ton_tai" / "state.json"
        trang_thai = doc_trang_thai(duong_dan)
        assert trang_thai == TrangThaiBenVung(breaker=TrangThaiBreaker())
        assert trang_thai.la_thanh_ly is False

    def test_ghi_roi_doc_lai_khop_nguyen_ban(self, tmp_path) -> None:
        duong_dan = tmp_path / "state.json"
        goc = TrangThaiBenVung(
            breaker=TrangThaiBreaker(
                so_loi_lien_tiep=3, mo_tam=True, thoi_diem_mo=T0, backoff_s=4.0
            ),
            la_thanh_ly=False,
        )
        luu_trang_thai(goc, duong_dan)
        assert doc_trang_thai(duong_dan) == goc

    def test_co_do_thanh_ly_song_sot_qua_ghi_doc(self, tmp_path) -> None:
        duong_dan = tmp_path / "state.json"
        goc = TrangThaiBenVung(breaker=TrangThaiBreaker(dung_han=True), la_thanh_ly=True)
        luu_trang_thai(goc, duong_dan)
        doc_lai = doc_trang_thai(duong_dan)
        assert doc_lai.la_thanh_ly is True
        assert doc_lai.breaker.dung_han is True

    def test_ghi_nguyen_tu_khong_de_lai_file_tam(self, tmp_path) -> None:
        duong_dan = tmp_path / "state.json"
        luu_trang_thai(TrangThaiBenVung(breaker=TrangThaiBreaker()), duong_dan)
        assert duong_dan.exists()
        assert not (tmp_path / "state.json.dang-ghi").exists()

    def test_file_hong_RAISE_khong_am_tham_coi_la_sach(self, tmp_path) -> None:
        """🔴 Ca quan trọng nhất: file CÓ tồn tại mà đọc hỏng KHÔNG được
        coi là "chưa từng ghi" — nó có thể đang che một `dung_han=True`
        ghi từ trước. Khác hẳn ca 'chưa có file' ở trên."""
        duong_dan = tmp_path / "state.json"
        duong_dan.write_text("khong phai json hop le", encoding="utf-8")
        with pytest.raises(RiskSupervisorError, match="KHÔNG đọc được"):
            doc_trang_thai(duong_dan)

    def test_thieu_khoa_ben_trong_cung_raise(self, tmp_path) -> None:
        duong_dan = tmp_path / "state.json"
        duong_dan.write_text('{"breaker": {}}', encoding="utf-8")
        with pytest.raises(RiskSupervisorError):
            doc_trang_thai(duong_dan)
