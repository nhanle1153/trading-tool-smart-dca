"""TD-0209 — watchdog thuần (`src/tool_d/ops/heartbeat_watchdog.py`)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from tool_d.ops.heartbeat import ghi_heartbeat
from tool_d.ops.heartbeat_watchdog import (
    CANH_BAO,
    PHUC_HOI,
    TrangThaiWatchdog,
    chay_mot_vong,
    danh_gia_heartbeat,
    quyet_dinh_loai_tin,
    xay_noi_dung_tin,
)
from tool_d.ops.heartbeat import KetQuaDocHeartbeat, Heartbeat
from tool_d.ops.telegram_client import KetQuaGuiTelegram

T0 = datetime(2026, 9, 14, 0, 0, 0, tzinfo=timezone.utc)


def _hb(trang_thai: str = "RUNNING", *, thoi_diem: datetime = T0, tu_luc: datetime = T0) -> KetQuaDocHeartbeat:
    return KetQuaDocHeartbeat(
        heartbeat=Heartbeat(thoi_diem=thoi_diem, trang_thai=trang_thai, trang_thai_tu_luc=tu_luc), loi=None
    )


class TestDanhGiaHeartbeat:
    def test_khong_doc_duoc_la_bat_thuong(self) -> None:
        ket_qua = KetQuaDocHeartbeat(heartbeat=None, loi="file mất")
        danh_gia = danh_gia_heartbeat(ket_qua, now=T0)
        assert danh_gia.bat_thuong
        assert "không đọc được" in danh_gia.ly_do

    def test_heartbeat_moi_va_running_la_binh_thuong(self) -> None:
        danh_gia = danh_gia_heartbeat(_hb(), now=T0 + timedelta(seconds=5))
        assert not danh_gia.bat_thuong
        assert danh_gia.ly_do is None

    def test_heartbeat_cu_qua_nguong_la_bat_thuong(self) -> None:
        danh_gia = danh_gia_heartbeat(_hb(), now=T0 + timedelta(seconds=301))
        assert danh_gia.bat_thuong
        assert "cũ" in danh_gia.ly_do

    def test_heartbeat_dung_nguong_khong_bat_thuong(self) -> None:
        danh_gia = danh_gia_heartbeat(_hb(), now=T0 + timedelta(seconds=300))
        assert not danh_gia.bat_thuong

    def test_stopped_ngan_ngay_khong_bat_thuong(self) -> None:
        ket_qua = _hb("STOPPED", thoi_diem=T0, tu_luc=T0)
        danh_gia = danh_gia_heartbeat(ket_qua, now=T0 + timedelta(seconds=100))
        assert not danh_gia.bat_thuong

    def test_stopped_qua_lau_la_bat_thuong(self) -> None:
        ket_qua = _hb("STOPPED", thoi_diem=T0, tu_luc=T0 - timedelta(seconds=301))
        danh_gia = danh_gia_heartbeat(ket_qua, now=T0)
        assert danh_gia.bat_thuong
        assert "STOPPED" in danh_gia.ly_do

    def test_nguong_truyen_vao_duoc_ghi_de(self) -> None:
        danh_gia = danh_gia_heartbeat(_hb(), now=T0 + timedelta(seconds=10), nguong_heartbeat_cu_s=5.0)
        assert danh_gia.bat_thuong


class TestQuyetDinhLoaiTin:
    def test_lan_dau_binh_thuong_khong_bao(self) -> None:
        assert quyet_dinh_loai_tin(None, False) is None

    def test_lan_dau_da_bat_thuong_bao_canh_bao(self) -> None:
        assert quyet_dinh_loai_tin(None, True) == CANH_BAO

    def test_chuyen_ok_sang_bat_thuong_bao_canh_bao(self) -> None:
        assert quyet_dinh_loai_tin(False, True) == CANH_BAO

    def test_chuyen_bat_thuong_sang_ok_bao_phuc_hoi(self) -> None:
        assert quyet_dinh_loai_tin(True, False) == PHUC_HOI

    def test_giu_nguyen_binh_thuong_khong_bao(self) -> None:
        assert quyet_dinh_loai_tin(False, False) is None

    def test_giu_nguyen_bat_thuong_khong_bao_lap(self) -> None:
        assert quyet_dinh_loai_tin(True, True) is None


class TestXayNoiDungTin:
    def test_canh_bao_co_ly_do(self) -> None:
        from tool_d.ops.heartbeat_watchdog import KetQuaDanhGia

        noi_dung = xay_noi_dung_tin(
            CANH_BAO, KetQuaDanhGia(bat_thuong=True, ly_do="ly do X"), ten_tien_trinh="tool_d", now=T0
        )
        assert "BẤT THƯỜNG" in noi_dung
        assert "ly do X" in noi_dung
        assert "tool_d" in noi_dung

    def test_phuc_hoi_khong_can_ly_do(self) -> None:
        from tool_d.ops.heartbeat_watchdog import KetQuaDanhGia

        noi_dung = xay_noi_dung_tin(
            PHUC_HOI, KetQuaDanhGia(bat_thuong=False, ly_do=None), ten_tien_trinh="tool_d", now=T0
        )
        assert "PHỤC HỒI" in noi_dung

    def test_loai_la_gi_raise(self) -> None:
        from tool_d.ops.heartbeat_watchdog import KetQuaDanhGia

        with pytest.raises(ValueError):
            xay_noi_dung_tin("LA_GI", KetQuaDanhGia(bat_thuong=False, ly_do=None), ten_tien_trinh="tool_d", now=T0)


class TestChayMotVong:
    def test_binh_thuong_khong_gui_gi(self, tmp_path: Path) -> None:
        duong_dan = tmp_path / "heartbeat.json"
        ghi_heartbeat(duong_dan, trang_thai="RUNNING", now=T0)

        goi: list[str] = []
        trang_thai_moi, ket_qua_gui = chay_mot_vong(
            duong_dan,
            TrangThaiWatchdog(),
            now=T0,
            gui_tin_nhan_fn=lambda text: goi.append(text) or KetQuaGuiTelegram(True, None, None),
        )

        assert ket_qua_gui is None
        assert goi == []
        assert trang_thai_moi == TrangThaiWatchdog(bat_thuong_da_bao=None)

    def test_bat_thuong_gui_thanh_cong_cap_nhat_trang_thai(self, tmp_path: Path) -> None:
        duong_dan = tmp_path / "heartbeat.json"
        ghi_heartbeat(duong_dan, trang_thai="RUNNING", now=T0)
        now_bat_thuong = T0 + timedelta(seconds=400)

        goi: list[str] = []
        trang_thai_moi, ket_qua_gui = chay_mot_vong(
            duong_dan,
            TrangThaiWatchdog(),
            now=now_bat_thuong,
            gui_tin_nhan_fn=lambda text: goi.append(text) or KetQuaGuiTelegram(True, None, None),
        )

        assert len(goi) == 1
        assert "BẤT THƯỜNG" in goi[0]
        assert ket_qua_gui is not None and ket_qua_gui.thanh_cong
        assert trang_thai_moi == TrangThaiWatchdog(bat_thuong_da_bao=True)

    def test_gui_that_bai_giu_nguyen_trang_thai_de_thu_lai(self, tmp_path: Path) -> None:
        duong_dan = tmp_path / "heartbeat.json"
        ghi_heartbeat(duong_dan, trang_thai="RUNNING", now=T0)
        now_bat_thuong = T0 + timedelta(seconds=400)

        trang_thai_moi, ket_qua_gui = chay_mot_vong(
            duong_dan,
            TrangThaiWatchdog(),
            now=now_bat_thuong,
            gui_tin_nhan_fn=lambda text: KetQuaGuiTelegram(False, "retry", "mô phỏng lỗi"),
        )

        assert ket_qua_gui is not None and not ket_qua_gui.thanh_cong
        assert trang_thai_moi == TrangThaiWatchdog(bat_thuong_da_bao=None)  # KHÔNG đổi — thử lại vòng sau

    def test_phuc_hoi_sau_khi_da_bao_bat_thuong(self, tmp_path: Path) -> None:
        duong_dan = tmp_path / "heartbeat.json"
        ghi_heartbeat(duong_dan, trang_thai="RUNNING", now=T0)

        goi: list[str] = []
        trang_thai_moi, _ = chay_mot_vong(
            duong_dan,
            TrangThaiWatchdog(bat_thuong_da_bao=True),
            now=T0 + timedelta(seconds=1),
            gui_tin_nhan_fn=lambda text: goi.append(text) or KetQuaGuiTelegram(True, None, None),
        )

        assert len(goi) == 1
        assert "PHỤC HỒI" in goi[0]
        assert trang_thai_moi == TrangThaiWatchdog(bat_thuong_da_bao=False)
