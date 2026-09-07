"""TD-0130 (MT-08) — Dòng CTRL KHÔNG tính vào N, và phải khai được dạng.

Spec nói CTRL không tính vào N ở 5 chỗ (§0d.4 dòng 594, DR-014 §2 dòng 3490
"ngoài sổ này", dòng 3608 "dòng CTRL, 0 trial", dòng 3715, changelog v8 dòng
71). Chủ dự án chốt MT-02 rồi MT-08 (back-end-note.md mục 7, 07/09/2026).
File này là phần THI HÀNH: trước nó, chính sách đã chốt nhưng code cộng cả
CTRL vào N_ĐÃ_DÙNG và chặn ghi điểm kiểm soát khi ngân sách cạn.

🔴 KHÔNG dùng mã `L-Z56` — spec đã gán mã đó cho một test khác của DR-015
(MT-09). Đặt tên theo mã việc.

Vì sao cần CỬA XÁC THỰC chứ không nhận lời khai (MT-08): L-Z55 một mình
KHÔNG đủ cho CTRL — một điểm kiểm soát HỢP LỆ *có* chạm CALIB nên không vi
phạm timerange. Chỗ phân biệt "điểm kiểm soát thật" với "trial trốn kế toán
bằng cách khai CTRL" phải là ĐẦU RA, không phải dữ liệu chạm.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from tool_d.ledger.registry import (
    BudgetExhaustedError,
    CtrlClaimError,
    LedgerError,
    TrialLedger,
)


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


def _kw(**overrides) -> dict:
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


def _ctrl_do_thuoc(**overrides) -> dict:
    """CTRL dạng *đo thước* (D3.5 Bước 1) — đầu ra sạch chỉ số hiệu năng."""
    return _kw(
        budget_line="CTRL",
        ctrl_output_whitelist=["price_delta", "tranche_index", "direction"],
        **overrides,
    )


def _so_dai(path: Path) -> int:
    if not path.exists():
        return 0
    return len([ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()])


def _tieu_het(ledger: TrialLedger, n_dang_ky: int) -> None:
    """Tiêu sạch ngân sách bằng các trial THẬT (B1), để dựng đúng tình
    huống MT-08 mô tả: N cạn đúng lúc cần chạy điểm kiểm soát nhất."""
    for _ in range(n_dang_ky):
        tid = ledger.reserve(**_kw(n_dang_ky=n_dang_ky))
        ledger.seal(tid, seal_path="runs/td/metrics.seal")


# ── 1. Kế toán: CTRL đứng ngoài N ────────────────────────────────────


class TestCtrlDungNgoaiN:
    def test_ctrl_consumed_khong_cong_vao_n_used(self, tmp_path: Path) -> None:
        """1 trial B1 + 1 trial CTRL đều CONSUMED → n_used() == 1."""
        ledger = TrialLedger(tmp_path / "reg.jsonl")
        t_that = ledger.reserve(**_kw())
        t_ctrl = ledger.reserve(**_ctrl_do_thuoc())
        ledger.seal(t_that, seal_path="runs/td/metrics.seal")
        ledger.seal(t_ctrl, seal_path="runs/td/metrics.seal")

        assert ledger.n_used() == 1

    def test_ctrl_reserved_khong_cong_vao_n_reserved(self, tmp_path: Path) -> None:
        ledger = TrialLedger(tmp_path / "reg.jsonl")
        ledger.reserve(**_kw())
        ledger.reserve(**_ctrl_do_thuoc())

        assert ledger.n_reserved() == 1

    def test_available_khong_bi_ctrl_an_mon(self, tmp_path: Path) -> None:
        """Chạy 5 điểm kiểm soát không được làm hụt một suất nghiên cứu nào."""
        ledger = TrialLedger(tmp_path / "reg.jsonl")
        for _ in range(5):
            tid = ledger.reserve(**_ctrl_do_thuoc(n_dang_ky=10))
            ledger.seal(tid, seal_path="runs/td/metrics.seal")

        assert ledger.available(n_dang_ky=10) == 10


# ── 2. Ngân sách cạn vẫn ghi được điểm kiểm soát ─────────────────────


class TestNganSachCanVanGhiDuocCtrl:
    def test_ctrl_van_dat_cho_duoc_khi_da_can_sach(self, tmp_path: Path) -> None:
        """Đúng lúc sắp go-live là lúc cần kiểm tra tái lập nhất (MT-08)."""
        reg = tmp_path / "reg.jsonl"
        ledger = TrialLedger(reg)
        _tieu_het(ledger, 2)
        assert ledger.available(n_dang_ky=2) == 0

        tid = ledger.reserve(**_ctrl_do_thuoc(n_dang_ky=2))

        assert tid
        assert ledger.available(n_dang_ky=2) == 0  # vẫn 0, không âm

    def test_dong_that_van_bi_chan_khi_can_khong_noi_lay(self, tmp_path: Path) -> None:
        """Nới cho CTRL không được nới lây sang dòng nghiên cứu thật."""
        ledger = TrialLedger(tmp_path / "reg.jsonl")
        _tieu_het(ledger, 2)

        with pytest.raises(BudgetExhaustedError):
            ledger.reserve(**_kw(n_dang_ky=2))


# ── 3. Cửa xác thực CTRL — fail-closed ───────────────────────────────


class TestCuaXacThucCtrl:
    def test_khong_khai_dang_nao_thi_tu_choi_ghi(self, tmp_path: Path) -> None:
        reg = tmp_path / "reg.jsonl"
        ledger = TrialLedger(reg)

        with pytest.raises(CtrlClaimError):
            ledger.reserve(**_kw(budget_line="CTRL"))

        assert _so_dai(reg) == 0  # sổ KHÔNG dài thêm dòng nào

    def test_khai_ca_hai_dang_thi_tu_choi(self, tmp_path: Path) -> None:
        """Khai hai dạng cùng lúc = chừa đường lách sang dạng dễ hơn."""
        reg = tmp_path / "reg.jsonl"
        ledger = TrialLedger(reg)
        goc = ledger.reserve(**_kw())

        with pytest.raises(CtrlClaimError):
            ledger.reserve(**_ctrl_do_thuoc(reproduces_trial_id=goc))

        assert _so_dai(reg) == 1  # chỉ còn đúng dòng RESERVE của trial gốc

    def test_do_thuoc_co_chi_so_hieu_nang_thi_tu_choi(self, tmp_path: Path) -> None:
        """Spec dòng 3605-3607: TUYỆT ĐỐI không PnL, không win/loss."""
        reg = tmp_path / "reg.jsonl"
        ledger = TrialLedger(reg)

        with pytest.raises(CtrlClaimError):
            ledger.reserve(
                **_kw(
                    budget_line="CTRL",
                    ctrl_output_whitelist=["price_delta", "pnl_abs"],
                )
            )

        assert _so_dai(reg) == 0

    def test_do_thuoc_danh_sach_rong_thi_tu_choi(self, tmp_path: Path) -> None:
        """Khai dạng đo thước với đầu ra rỗng = khai suông, không đo gì."""
        ledger = TrialLedger(tmp_path / "reg.jsonl")

        with pytest.raises(CtrlClaimError):
            ledger.reserve(**_kw(budget_line="CTRL", ctrl_output_whitelist=[]))

    def test_do_thuoc_danh_sach_sach_thi_ghi_duoc(self, tmp_path: Path) -> None:
        reg = tmp_path / "reg.jsonl"
        ledger = TrialLedger(reg)

        tid = ledger.reserve(**_ctrl_do_thuoc())

        assert tid
        assert _so_dai(reg) == 1

    def test_tai_lap_tro_trial_khong_co_that_thi_tu_choi(self, tmp_path: Path) -> None:
        reg = tmp_path / "reg.jsonl"
        ledger = TrialLedger(reg)

        with pytest.raises(CtrlClaimError):
            ledger.reserve(**_kw(budget_line="CTRL", reproduces_trial_id="D-9999"))

        assert _so_dai(reg) == 0

    def test_tai_lap_hash_lech_thi_tu_choi(self, tmp_path: Path) -> None:
        """Tái lập mà đổi cấu hình thì không còn là tái lập nữa."""
        reg = tmp_path / "reg.jsonl"
        ledger = TrialLedger(reg)
        goc = ledger.reserve(**_kw(params_frozen_hash="fh1", config_hash="ch1"))

        with pytest.raises(CtrlClaimError):
            ledger.reserve(
                **_kw(
                    budget_line="CTRL",
                    reproduces_trial_id=goc,
                    params_frozen_hash="fh1",
                    config_hash="ch-KHAC",
                )
            )

        assert _so_dai(reg) == 1

    def test_tai_lap_hash_khop_dung_thi_ghi_duoc(self, tmp_path: Path) -> None:
        reg = tmp_path / "reg.jsonl"
        ledger = TrialLedger(reg)
        goc = ledger.reserve(**_kw(params_frozen_hash="fh1", config_hash="ch1"))

        tid = ledger.reserve(
            **_kw(
                budget_line="CTRL",
                reproduces_trial_id=goc,
                params_frozen_hash="fh1",
                config_hash="ch1",
            )
        )

        assert tid
        assert _so_dai(reg) == 2


# ── 4. Bất biến cũ không bị nới ──────────────────────────────────────


class TestCuaGhiKhongDuocLechSchema:
    """🔴 Cửa ghi và schema phải là MỘT nguồn sự thật.

    Các test schema có sẵn (`tests/unit/test_registry_schemas.py`) chỉ đối
    chiếu **fixture gõ tay** — không dòng nào đối chiếu đầu ra THẬT của
    `reserve()`. Khe hở đó để lọt đúng một lớp lỗi: cửa ghi thêm khoá mới,
    schema `additionalProperties: false` chưa biết khoá đó, và không ai
    phát hiện cho tới khi dòng CTRL đầu tiên được ghi vào sổ thật.

    Lớp test này khoá đường đó lại: mọi sự kiện do `reserve()` sinh ra phải
    hợp lệ theo chính schema mà audit dùng.
    """

    @staticmethod
    def _schema() -> dict:
        goc = Path(__file__).resolve().parents[2]
        return json.loads(
            (goc / "registry/schemas/trial_event.schema.json").read_text(encoding="utf-8")
        )

    def _su_kien_dau(self, reg: Path) -> dict:
        return json.loads(reg.read_text(encoding="utf-8").splitlines()[-1])

    def test_ctrl_do_thuoc_ghi_ra_hop_le_theo_schema(self, tmp_path: Path) -> None:
        reg = tmp_path / "reg.jsonl"
        TrialLedger(reg).reserve(**_ctrl_do_thuoc())

        jsonschema.validate(self._su_kien_dau(reg), self._schema())

    def test_ctrl_tai_lap_ghi_ra_hop_le_theo_schema(self, tmp_path: Path) -> None:
        reg = tmp_path / "reg.jsonl"
        ledger = TrialLedger(reg)
        goc = ledger.reserve(**_kw())
        ledger.reserve(**_kw(budget_line="CTRL", reproduces_trial_id=goc))

        jsonschema.validate(self._su_kien_dau(reg), self._schema())

    def test_dong_thuong_ghi_ra_hop_le_theo_schema(self, tmp_path: Path) -> None:
        reg = tmp_path / "reg.jsonl"
        TrialLedger(reg).reserve(**_kw())

        jsonschema.validate(self._su_kien_dau(reg), self._schema())


class TestBatBienCuGiuNguyen:
    def test_contribution_0_van_bi_tu_choi_ke_ca_voi_ctrl(self, tmp_path: Path) -> None:
        """MT-08 chốt rõ: giữ nguyên `contribution >= 1`, KHÔNG mở mức 0.
        Dòng CTRL vẫn khai 1 — chỉ là không được CỘNG vào N."""
        ledger = TrialLedger(tmp_path / "reg.jsonl")

        with pytest.raises(LedgerError):
            ledger.reserve(**_ctrl_do_thuoc(contribution=0))

    def test_dong_thuong_khong_can_khai_dang_nao(self, tmp_path: Path) -> None:
        """Cửa xác thực chỉ áp cho CTRL — không làm phiền dòng nghiên cứu."""
        ledger = TrialLedger(tmp_path / "reg.jsonl")

        assert ledger.reserve(**_kw())
