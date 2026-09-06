"""TD-0060 — danh sách chỉ số CỐ ĐỊNH của E5 (§12d.2 BƯỚC 1).

TD-0062 (sau) khoá danh sách này bằng test hồi quy giữ hash của TOÀN BỘ
danh sách mã — test ở đây chỉ kiểm TÍNH CHẤT của `build_metrics()` tại
D0-PRE (mọi chỉ số pending, không trùng mã), không đóng băng nội dung.
"""

from __future__ import annotations

from tool_d.measurement.tri_state import Status
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
