"""TD-0060 — danh sách chỉ số CỐ ĐỊNH của E5 (§12d.2 BƯỚC 1).

TD-0062 (sau) khoá danh sách này bằng test hồi quy giữ hash của TOÀN BỘ
danh sách mã — lớp `TestBuildMetricsOD0PRE` kiểm TÍNH CHẤT của
`build_metrics()` gọi KHÔNG THAM SỐ (mọi chỉ số pending, không trùng mã),
không đóng băng nội dung.

TD-0240 thêm hai lớp: `TestChiSoTinhDuocTuDuLieuThat` kiểm 8/22 chỉ số
TÍNH ĐÚNG từ dữ liệu dựng tay (thay cho D0-PRE cứng), và
`TestUnreadablePhanBietVoiPending` kiểm N6 (lỗi đọc ≠ chưa có dữ liệu).
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from tool_d.arm_switches import ARM_DON_TRANCHE
from tool_d.ledger.registry import TrialLedger
from tool_d.measurement.tri_state import Status
from tool_d.reporting.freqtrade_db import LenhTomTat
from tool_d.reporting.report_model import build_metrics


class TestBuildMetricsOD0PRE:
    def test_moi_chi_so_deu_pending(self) -> None:
        metrics = build_metrics()
        assert metrics != []
        assert all(m.measured.status is Status.PENDING for m in metrics)

    def test_khong_ma_nao_trung_lap(self) -> None:
        metrics = build_metrics()
        codes = [m.code for m in metrics]
        assert len(codes) == len(set(codes))

    def test_moi_chi_so_co_nhan_va_ly_do_pending(self) -> None:
        for m in build_metrics():
            assert m.label.strip() != ""
            assert m.measured.note is not None and m.measured.note.strip() != ""

    def test_goi_hai_lan_khong_chia_se_state(self) -> None:
        # Measured bất biến (frozen) nên vô hại, nhưng khẳng định rõ mỗi
        # lần build_metrics() là một danh sách MỚI, không phải cache dùng lại.
        a = build_metrics()
        b = build_metrics()
        assert a is not b
        assert [m.code for m in a] == [m.code for m in b]

    def test_cac_chi_so_bat_buoc_theo_spec_12d2_deu_co_mat(self) -> None:
        # Không kiểm HẾT (đó là việc đóng băng của TD-0062) — chỉ kiểm vài
        # mã trọng yếu spec nêu đích danh (H-1..H-4, ba dòng ngân sách),
        # để phát hiện sớm nếu ai vô tình xoá nhầm khi sửa file.
        codes = {m.code for m in build_metrics()}
        for bat_buoc in (
            "H1",
            "H2",
            "H3",
            "H4",
            "BUDGET_B3_REMAINING",
            "BUDGET_N_CURRENT",
            "BUDGET_DSR_CURRENT",
        ):
            assert bat_buoc in codes


class TestChiSoTinhDuocTuDuLieuThat:
    """TD-0240 — 8/22 chỉ số tính THẬT từ dữ liệu đã đọc sẵn (hàm THUẦN,
    không tự mở DB/file — dựng dữ liệu tay ở đây)."""

    def _lenh(
        self,
        *,
        is_open: bool = False,
        is_short: bool = False,
        exit_reason: str | None = "TP2_TRAIL",
        close_profit_abs: float | None = 10.0,
        so_tranche_khop: int = 1,
    ) -> LenhTomTat:
        return LenhTomTat(
            is_open=is_open,
            is_short=is_short,
            exit_reason=exit_reason,
            close_profit_abs=close_profit_abs,
            open_date_utc=datetime(2026, 1, 1, tzinfo=timezone.utc),
            close_date_utc=None if is_open else datetime(2026, 1, 2, tzinfo=timezone.utc),
            so_tranche_khop=so_tranche_khop,
        )

    def test_h3_tinh_dung_ti_le_time_stop(self) -> None:
        trades = [
            self._lenh(exit_reason="TIME_STOP"),
            self._lenh(exit_reason="TIME_STOP"),
            self._lenh(exit_reason="TP2_TRAIL"),
            self._lenh(exit_reason="trailing_stop_loss"),
        ]
        m = build_metrics(trades=trades)
        h3 = next(x for x in m if x.code == "H3")
        assert h3.measured.status is Status.OK
        assert h3.measured.value == pytest.approx(0.5)

    def test_h3_lenh_con_mo_khong_tinh_vao_mau_so(self) -> None:
        trades = [self._lenh(exit_reason="TIME_STOP"), self._lenh(is_open=True, exit_reason=None)]
        m = build_metrics(trades=trades)
        h3 = next(x for x in m if x.code == "H3")
        assert h3.measured.value == pytest.approx(1.0), "lệnh còn mở không được vào mẫu số"

    def test_winrate_tach_dung_long_short(self) -> None:
        trades = [
            self._lenh(is_short=False, close_profit_abs=5.0),
            self._lenh(is_short=False, close_profit_abs=-2.0),
            self._lenh(is_short=True, close_profit_abs=3.0),
        ]
        m = build_metrics(trades=trades)
        long_ = next(x for x in m if x.code == "WINRATE_LONG")
        short_ = next(x for x in m if x.code == "WINRATE_SHORT")
        assert long_.measured.value == pytest.approx(0.5)
        assert short_.measured.value == pytest.approx(1.0)

    def test_tranche_fill_1_luon_tinh_duoc_bat_ke_arm(self) -> None:
        trades = [self._lenh(so_tranche_khop=1), self._lenh(so_tranche_khop=3)]
        for arm in (None, "Z3", "Z0"):
            m = build_metrics(trades=trades, arm=arm)
            f1 = next(x for x in m if x.code == "TRANCHE_FILL_1")
            assert f1.measured.status is Status.OK
            assert f1.measured.value == pytest.approx(1.0)

    def test_tranche_fill_2_tinh_duoc_tren_arm_co_dca(self) -> None:
        assert "Z3" not in ARM_DON_TRANCHE, "Z3 phải là arm CÓ DCA để ca này có nghĩa"
        trades = [self._lenh(so_tranche_khop=1), self._lenh(so_tranche_khop=2)]
        m = build_metrics(trades=trades, arm="Z3")
        f2 = next(x for x in m if x.code == "TRANCHE_FILL_2")
        assert f2.measured.status is Status.OK
        assert f2.measured.value == pytest.approx(0.5)

    def test_tranche_fill_2_PENDING_tren_arm_don_tranche_KHONG_phai_OK_0(self) -> None:
        """🔴 Ca quan trọng nhất — phát hiện của phiên `-54` (TD-0246):
        trên arm ∈ ARM_DON_TRANCHE, DG1-DG5 không bao giờ được xét
        (`arm_switches.py:73-75`, `ZoneAbsorption.py:894-895` return
        trước khi gọi `duoc_them_tranche()`). Dù CÓ lệnh trong `trades`,
        không lệnh nào ĐẠT tranche 2 vì nó CẤU TRÚC KHÔNG THỂ XẢY RA —
        nếu module này trả `Measured.ok(0.0)`, đó là gộp "0 cấu trúc"
        thành "đã đo và bằng 0", đúng cái bẫy TD-0246 đặt tên. Phải là
        PENDING, không phải OK."""
        assert "Z0" in ARM_DON_TRANCHE
        trades = [self._lenh(so_tranche_khop=1), self._lenh(so_tranche_khop=1)]
        m = build_metrics(trades=trades, arm="Z0")
        f2 = next(x for x in m if x.code == "TRANCHE_FILL_2")
        f3 = next(x for x in m if x.code == "TRANCHE_FILL_3")
        assert f2.measured.status is Status.PENDING, f2.measured
        assert f3.measured.status is Status.PENDING, f3.measured
        assert "ARM_DON_TRANCHE" in (f2.measured.note or "")

    def test_tranche_fill_2_pending_khi_chua_biet_arm(self) -> None:
        trades = [self._lenh(so_tranche_khop=2)]
        m = build_metrics(trades=trades, arm=None)
        f2 = next(x for x in m if x.code == "TRANCHE_FILL_2")
        assert f2.measured.status is Status.PENDING

    def test_budget_tinh_duoc_ngay_ca_khi_so_rong(self, tmp_path) -> None:
        so_rong = tmp_path / "trial_registry.jsonl"
        ledger = TrialLedger(so_rong)
        m = build_metrics(ledger=ledger, so_lenh_da_dong=0)
        n_hien_tai = next(x for x in m if x.code == "BUDGET_N_CURRENT")
        dsr_hien_tai = next(x for x in m if x.code == "BUDGET_DSR_CURRENT")
        b3 = next(x for x in m if x.code == "BUDGET_B3_REMAINING")
        assert n_hien_tai.measured.status is Status.OK
        assert n_hien_tai.measured.value == 0
        assert dsr_hien_tai.measured.status is Status.OK
        assert dsr_hien_tai.measured.value > 0
        assert b3.measured.status is Status.OK

    def test_sl_gap_ms_pending_khi_rong_ok_khi_co_du_lieu(self) -> None:
        rong = build_metrics(gap_ms_values=())
        assert next(x for x in rong if x.code == "SL_GAP_MS_DIST").measured.status is Status.PENDING

        co_du_lieu = build_metrics(gap_ms_values=[100.0, 200.0, 300.0])
        m = next(x for x in co_du_lieu if x.code == "SL_GAP_MS_DIST")
        assert m.measured.status is Status.OK
        assert m.measured.value == {"n": 3, "min": 100.0, "p50": 200.0, "max": 300.0}


class TestUnreadablePhanBietVoiPending:
    """N6 — 'lỗi đọc' (unreadable) khác 'chưa có dữ liệu' (pending).
    Không được gộp thành cùng một trạng thái."""

    def test_trades_error_lam_cac_chi_so_lien_quan_thanh_unreadable(self) -> None:
        m = build_metrics(trades_error="đọc DB thất bại: file khoá")
        for code in ("H3", "WINRATE_LONG", "WINRATE_SHORT", "TRANCHE_FILL_1", "TRANCHE_FILL_2", "TRANCHE_FILL_3"):
            metric = next(x for x in m if x.code == code)
            assert metric.measured.status is Status.UNREADABLE, code

    def test_ledger_error_lam_budget_thanh_unreadable(self) -> None:
        m = build_metrics(ledger_error="mở sổ thất bại")
        for code in ("BUDGET_B3_REMAINING", "BUDGET_N_CURRENT", "BUDGET_DSR_CURRENT"):
            assert next(x for x in m if x.code == code).measured.status is Status.UNREADABLE

    def test_gap_ms_error_uu_tien_hon_rong(self) -> None:
        m = build_metrics(gap_ms_values=(), gap_ms_error="đọc decision_log.jsonl thất bại")
        assert next(x for x in m if x.code == "SL_GAP_MS_DIST").measured.status is Status.UNREADABLE
