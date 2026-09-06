"""L-Z41 (phần cơ chế) — Measured[T]: ba trạng thái, không giá trị lính canh.

Spec dòng 618-633, 684-686. Phần kiểm trên đầu ra THẬT của periodic_report
(E5) nằm ở tests/lock/test_lz41_periodic_report.py (TD-0061, sau khi E5 tồn
tại) — file này chỉ kiểm cơ chế của chính tri_state.py (TD-0010).
"""

from __future__ import annotations

import pytest

from tool_d.measurement.tri_state import Measured, Status, audit_line, scan_for_sentinels


class TestMeasuredBatVien:
    def test_pending_khong_mang_value(self) -> None:
        m = Measured.pending("chưa có kết quả backtest")
        assert m.status is Status.PENDING
        assert m.value is None

    def test_unreadable_khong_mang_value(self) -> None:
        m = Measured.unreadable("file .seal hỏng")
        assert m.status is Status.UNREADABLE
        assert m.value is None

    def test_ok_bat_buoc_mang_value(self) -> None:
        m = Measured.ok(0.0)
        assert m.status is Status.OK
        assert m.value == 0.0

    def test_khong_the_tao_ok_voi_value_none(self) -> None:
        with pytest.raises(ValueError):
            Measured(status=Status.OK, value=None)

    def test_khong_the_tao_pending_voi_value_khac_none(self) -> None:
        # Đây chính là "hiện số cũ kèm cảnh báo" mà spec cấm (dòng 629-630).
        with pytest.raises(ValueError):
            Measured(status=Status.PENDING, value=0.0, note="cũ")

    def test_khong_the_tao_unreadable_voi_value_khac_none(self) -> None:
        with pytest.raises(ValueError):
            Measured(status=Status.UNREADABLE, value=-1, note="lỗi")


class TestRender:
    def test_pending_render_khong_phai_so(self) -> None:
        text = Measured.pending("chưa có kết quả backtest").render()
        assert "chưa đo được" in text
        assert "0.0" not in text
        assert "-1" not in text

    def test_unreadable_render_hien_ly_do_khong_hien_so(self) -> None:
        text = Measured.unreadable("file .seal hỏng").render()
        assert "file .seal hỏng" in text
        assert text != "0.0"

    def test_ok_render_ra_dung_gia_tri(self) -> None:
        assert Measured.ok(3.14).render() == "3.14"
        assert Measured.ok(0.0).render() == "0.0"  # 0.0 THẬT là hợp lệ khi OK

    def test_is_ok(self) -> None:
        assert Measured.ok(1).is_ok() is True
        assert Measured.pending("x").is_ok() is False
        assert Measured.unreadable("x").is_ok() is False


class TestScanForSentinels:
    def test_sach_khong_co_gi(self) -> None:
        assert scan_for_sentinels("expectancy: chưa đo được (chưa có kết quả)") == []

    def test_bat_duoc_UNKNOWN(self) -> None:
        assert scan_for_sentinels("giá trị: UNKNOWN") != []

    def test_bat_duoc_NA(self) -> None:
        assert scan_for_sentinels("kết quả: N/A") != []

    def test_bat_duoc_am_1_doc_lap(self) -> None:
        assert scan_for_sentinels("n_trades: -1") != []

    def test_khong_bao_dong_gia_voi_so_am_khac(self) -> None:
        # -10, -1.5 không phải giá trị lính canh -1 — không được báo động giả.
        assert scan_for_sentinels("drawdown: -10 pct") == []
        assert scan_for_sentinels("skew: -1.5") == []

    def test_khong_bao_dong_gia_voi_0_0_hop_le(self) -> None:
        assert scan_for_sentinels("time_stop_ratio: 0.0") == []


class TestAuditLine:
    def test_dinh_dang_dung_nhu_spec(self) -> None:
        line = audit_line(ok=3, fail=1, unmeasured=6, total=10)
        assert line == "đã audit 4/10 (3 đạt, 1 chưa đạt, 6 chưa đo được)"

    def test_ke_toan_sai_thi_raise_khong_duoc_in_ra(self) -> None:
        with pytest.raises(ValueError):
            audit_line(ok=3, fail=1, unmeasured=6, total=999)

    def test_registry_rong_toan_bo_chua_do(self) -> None:
        line = audit_line(ok=0, fail=0, unmeasured=10, total=10)
        assert line == "đã audit 0/10 (0 đạt, 0 chưa đạt, 10 chưa đo được)"
