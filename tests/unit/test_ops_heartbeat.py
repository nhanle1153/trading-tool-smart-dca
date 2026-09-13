"""TD-0209 — tầng thuần ghi/đọc heartbeat (`src/tool_d/ops/heartbeat.py`)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from tool_d.ops.heartbeat import (
    Heartbeat,
    HeartbeatError,
    doc_heartbeat,
    ghi_heartbeat,
    tinh_trang_thai_tu_luc,
    tuoi_giay,
    tuoi_trang_thai_giay,
)

T0 = datetime(2026, 9, 14, 0, 0, 0, tzinfo=timezone.utc)


class TestTinhTrangThaiTuLuc:
    def test_lan_dau_tien_dat_now(self) -> None:
        assert tinh_trang_thai_tu_luc(None, "RUNNING", now=T0) == T0

    def test_trang_thai_khong_doi_giu_moc_cu(self) -> None:
        cu = Heartbeat(thoi_diem=T0, trang_thai="RUNNING", trang_thai_tu_luc=T0)
        moi_now = T0 + timedelta(seconds=5)
        assert tinh_trang_thai_tu_luc(cu, "RUNNING", now=moi_now) == T0

    def test_trang_thai_doi_dat_lai_now(self) -> None:
        cu = Heartbeat(thoi_diem=T0, trang_thai="RUNNING", trang_thai_tu_luc=T0)
        moi_now = T0 + timedelta(seconds=5)
        assert tinh_trang_thai_tu_luc(cu, "STOPPED", now=moi_now) == moi_now


class TestGhiVaDocHeartbeat:
    def test_ghi_roi_doc_lai_khop(self, tmp_path: Path) -> None:
        duong_dan = tmp_path / "heartbeat.json"
        ghi_heartbeat(duong_dan, trang_thai="RUNNING", now=T0)

        ket_qua = doc_heartbeat(duong_dan)

        assert ket_qua.doc_duoc
        assert ket_qua.heartbeat == Heartbeat(thoi_diem=T0, trang_thai="RUNNING", trang_thai_tu_luc=T0)

    def test_ghi_lan_hai_giu_tu_luc_neu_trang_thai_khong_doi(self, tmp_path: Path) -> None:
        duong_dan = tmp_path / "heartbeat.json"
        ghi_heartbeat(duong_dan, trang_thai="RUNNING", now=T0)
        cu = doc_heartbeat(duong_dan).heartbeat
        assert cu is not None

        lan_hai = T0 + timedelta(seconds=5)
        ghi_heartbeat(duong_dan, trang_thai="RUNNING", now=lan_hai, heartbeat_cu=cu)

        moi = doc_heartbeat(duong_dan).heartbeat
        assert moi is not None
        assert moi.thoi_diem == lan_hai
        assert moi.trang_thai_tu_luc == T0  # KHÔNG đổi — vẫn cùng trạng thái

    def test_ghi_lan_hai_dat_lai_tu_luc_neu_trang_thai_doi(self, tmp_path: Path) -> None:
        duong_dan = tmp_path / "heartbeat.json"
        ghi_heartbeat(duong_dan, trang_thai="RUNNING", now=T0)
        cu = doc_heartbeat(duong_dan).heartbeat
        assert cu is not None

        lan_hai = T0 + timedelta(seconds=5)
        ghi_heartbeat(duong_dan, trang_thai="STOPPED", now=lan_hai, heartbeat_cu=cu)

        moi = doc_heartbeat(duong_dan).heartbeat
        assert moi is not None
        assert moi.trang_thai == "STOPPED"
        assert moi.trang_thai_tu_luc == lan_hai

    def test_ghi_trang_thai_rong_raise(self, tmp_path: Path) -> None:
        with pytest.raises(HeartbeatError):
            ghi_heartbeat(tmp_path / "heartbeat.json", trang_thai="", now=T0)

    def test_ghi_khong_de_lai_file_tmp(self, tmp_path: Path) -> None:
        duong_dan = tmp_path / "heartbeat.json"
        ghi_heartbeat(duong_dan, trang_thai="RUNNING", now=T0)
        assert sorted(p.name for p in tmp_path.iterdir()) == ["heartbeat.json"]


class TestDocHeartbeatKhongDocDuoc:
    def test_file_khong_ton_tai(self, tmp_path: Path) -> None:
        ket_qua = doc_heartbeat(tmp_path / "khong_ton_tai.json")
        assert not ket_qua.doc_duoc
        assert ket_qua.heartbeat is None
        assert "không tìm thấy" in ket_qua.loi

    def test_json_hong(self, tmp_path: Path) -> None:
        duong_dan = tmp_path / "heartbeat.json"
        duong_dan.write_text("{ khong phai json", encoding="utf-8")
        ket_qua = doc_heartbeat(duong_dan)
        assert not ket_qua.doc_duoc

    def test_thieu_truong(self, tmp_path: Path) -> None:
        duong_dan = tmp_path / "heartbeat.json"
        duong_dan.write_text(json.dumps({"thoi_diem": T0.isoformat()}), encoding="utf-8")
        ket_qua = doc_heartbeat(duong_dan)
        assert not ket_qua.doc_duoc
        assert "thiếu trường" in ket_qua.loi

    def test_moc_thoi_gian_khong_parse_duoc(self, tmp_path: Path) -> None:
        duong_dan = tmp_path / "heartbeat.json"
        duong_dan.write_text(
            json.dumps({"thoi_diem": "khong-phai-iso", "trang_thai": "RUNNING", "trang_thai_tu_luc": T0.isoformat()}),
            encoding="utf-8",
        )
        ket_qua = doc_heartbeat(duong_dan)
        assert not ket_qua.doc_duoc

    def test_khong_bao_gio_raise(self, tmp_path: Path) -> None:
        duong_dan = tmp_path / "khong.json"
        # Không raise dù file không tồn tại — N6: watchdog cần GIÁ TRỊ, không phải exception
        doc_heartbeat(duong_dan)


class TestTuoi:
    def test_tuoi_giay(self) -> None:
        hb = Heartbeat(thoi_diem=T0, trang_thai="RUNNING", trang_thai_tu_luc=T0)
        assert tuoi_giay(hb, now=T0 + timedelta(seconds=42)) == 42.0

    def test_tuoi_trang_thai_giay(self) -> None:
        hb = Heartbeat(thoi_diem=T0, trang_thai="STOPPED", trang_thai_tu_luc=T0 - timedelta(seconds=10))
        assert tuoi_trang_thai_giay(hb, now=T0) == 10.0

    def test_tuoi_am_khong_bi_kep_ve_0(self) -> None:
        hb = Heartbeat(thoi_diem=T0, trang_thai="RUNNING", trang_thai_tu_luc=T0)
        assert tuoi_giay(hb, now=T0 - timedelta(seconds=5)) == -5.0
