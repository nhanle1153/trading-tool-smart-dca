"""L-Z52 🔴 CRITICAL — Khởi chạy khi không có đặt chỗ hợp lệ / Khả dụng <
contribution → bộ chạy TỪ CHỐI, exit ≠ 0, KHÔNG chạm dữ liệu.
Spec dòng 3962-3965 (DR-014 §1: "Không có đặt chỗ hợp lệ → bộ chạy TỪ
CHỐI khởi động — đây là phần cơ khí của L-Z34: N nối vào code ở cả đầu
VÀO, không chỉ đầu ra").
"""

from __future__ import annotations

import builtins
from pathlib import Path

import pytest

from tool_d.ledger.registry import BudgetExhaustedError, TrialLedger


def _prov() -> dict:
    return {
        "params_source": "yaml",
        "params_effective": {},
        "git_sha": "a" * 40,
        "reproducible_from_sha": True,
        "data_hashes": {},
        "cache_mode": "none",
        "guard_passed": True,
    }


def _reserve_kwargs(**overrides) -> dict:
    kwargs = dict(
        n_dang_ky=114,
        budget_line="B1",
        hypothesis_slot="A-03",
        direction="LONG",
        dataset="CALIB",
        param_under_test="zss_threshold",
        param_value=0.55,
        params_frozen_hash="fh",
        config_hash="ch",
        code_commit="abc123",
        provenance=_prov(),
        contribution=1,
    )
    kwargs.update(overrides)
    return kwargs


class TestTuChoiTruocKhiChamDuLieu:
    def test_het_ngan_sach_thi_raise_truoc_khi_ghi_bat_ky_su_kien_nao(
        self, tmp_path: Path
    ) -> None:
        reg_path = tmp_path / "reg.jsonl"
        ledger = TrialLedger(reg_path)
        ledger.reserve(**_reserve_kwargs(n_dang_ky=1, contribution=1))
        assert reg_path.read_text(encoding="utf-8").count("\n") == 1  # đúng 1 sự kiện

        with pytest.raises(BudgetExhaustedError):
            ledger.reserve(**_reserve_kwargs(n_dang_ky=1, contribution=1))

        # Bị từ chối -> KHÔNG ghi thêm sự kiện nào vào sổ (không có "nửa
        # đặt chỗ", không có dấu vết của lần bị từ chối trong sổ chính).
        assert reg_path.read_text(encoding="utf-8").count("\n") == 1

    def test_spy_khang_dinh_0_lan_doc_user_data(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Dựng spy trên `open()` toàn cục, khẳng định KHÔNG lần nào mở
        file dưới `user_data/data` trong suốt một lần `reserve()` bị từ
        chối — đây chính là bằng chứng "chưa chạm dữ liệu" (spec dòng
        3471-3472, không chỉ là quy ước gọi hàm theo đúng thứ tự).
        """
        opened_paths: list[str] = []
        real_open = builtins.open

        def spy_open(file, *args, **kwargs):  # noqa: ANN001
            opened_paths.append(str(file))
            return real_open(file, *args, **kwargs)

        monkeypatch.setattr(builtins, "open", spy_open)

        ledger = TrialLedger(tmp_path / "reg.jsonl")
        ledger.reserve(**_reserve_kwargs(n_dang_ky=1, contribution=1))

        opened_paths.clear()  # chỉ tính từ đây — bỏ qua I/O của lần reserve thành công ở trên
        with pytest.raises(BudgetExhaustedError):
            ledger.reserve(**_reserve_kwargs(n_dang_ky=1, contribution=1))

        cham_data = [p for p in opened_paths if "user_data" + "/data" in p.replace("\\", "/")]
        assert cham_data == [], f"Đã chạm user_data/data khi lẽ ra phải bị từ chối trước: {cham_data}"

    def test_khong_co_dat_cho_hop_le_tuc_reserve_chua_tung_goi(self, tmp_path: Path) -> None:
        """Nhánh còn lại của L-Z52: "không có đặt chỗ hợp lệ" — tức trial_id
        chưa từng được reserve() — mọi thao tác khác trên nó (seal/consume)
        phải bị chặn (UnknownTrialError), không có đường lách."""
        from tool_d.ledger.registry import UnknownTrialError

        ledger = TrialLedger(tmp_path / "reg.jsonl")
        with pytest.raises(UnknownTrialError):
            ledger.seal("D-9999", seal_path="runs/D-9999/metrics.seal")
        with pytest.raises(UnknownTrialError):
            ledger.consume(
                "D-9999",
                outcome={"expectancy": None, "sharpe": None, "n_trades": None, "max_single_loss_ratio": None},
                verdict="INCONCLUSIVE",
            )

    def test_kha_dung_dung_bang_0_van_cho_phep_reserve_0(self, tmp_path: Path) -> None:
        # Ranh giới: available == contribution vẫn phải PASS (không phải
        # "<=" bị hiểu nhầm thành "<").
        ledger = TrialLedger(tmp_path / "reg.jsonl")
        tid = ledger.reserve(**_reserve_kwargs(n_dang_ky=1, contribution=1))
        assert tid == "D-0001"
        assert ledger.available(n_dang_ky=1) == 0
