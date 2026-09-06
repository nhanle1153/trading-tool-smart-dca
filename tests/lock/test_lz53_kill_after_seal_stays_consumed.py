"""L-Z53 🔴 CRITICAL — Giết tiến trình sau khi có kết quả fold đầu →
CONSUMED, hoàn trả phải RAISE. Spec dòng 3966-3968 (DR-014 §3: "CÓ con
dấu ⇒ CONSUMED. Người vận hành KHÔNG có quyền phủ quyết — gọi thẳng hàm
hoàn trả cũng phải bị từ chối").

Mô phỏng bằng TIẾN TRÌNH THẬT (subprocess + SIGKILL), không phải chỉ gọi
hàm trong cùng tiến trình — vì chính bản chất của rủi ro là "mất mạng /
OS kill" xảy ra ở TẦNG HỆ ĐIỀU HÀNH, và sổ ghi vào FILE trên đĩa phải
sống sót qua đó.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from tool_d.ledger.registry import SealedTrialError, TrialLedger, TrialState

WORKER_SCRIPT = '''
import sys
from pathlib import Path
from tool_d.ledger.registry import TrialLedger

ledger = TrialLedger(Path(sys.argv[1]))
tid = ledger.reserve(
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
    provenance={
        "params_source": "yaml", "params_effective": {}, "git_sha": "a" * 40,
        "reproducible_from_sha": True, "data_hashes": {}, "cache_mode": "none",
        "guard_passed": True,
    },
    contribution=1,
)
print(tid, flush=True)

# Mô phỏng "chỉ số fold đầu tiên vừa tồn tại trong bộ nhớ" -> đóng dấu
# NGAY, trước cả khi in/ghi kết quả (DR-014 §3).
ledger.seal(tid, seal_path=f"runs/{tid}/metrics.seal")
print("SEALED", flush=True)

# Bị giết ở ĐÂY — TRƯỚC KHI kịp gọi consume() để ghi outcome thật.
import time
time.sleep(120)
'''


class TestGietTienTrinhSauKhiSeal:
    def test_bi_sigkill_sau_seal_van_tinh_consumed_va_refund_raise(
        self, tmp_path: Path
    ) -> None:
        reg_path = tmp_path / "reg.jsonl"
        script_path = tmp_path / "worker.py"
        script_path.write_text(WORKER_SCRIPT, encoding="utf-8")

        proc = subprocess.Popen(
            [sys.executable, str(script_path), str(reg_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            trial_id_line = proc.stdout.readline()
            sealed_line = proc.stdout.readline()
            assert sealed_line.strip() == "SEALED", (
                f"worker chưa kịp seal — stdout={trial_id_line!r},{sealed_line!r} "
                f"stderr={proc.stderr.read() if proc.stderr else ''}"
            )
            trial_id = trial_id_line.strip()

            proc.kill()  # SIGKILL — không cho worker có cơ hội dọn dẹp
            proc.wait(timeout=10)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=10)

        # Tiến trình con đã CHẾT TRƯỚC KHI gọi consume() — nhưng vì đã
        # seal, bản chiếu (đọc lại từ FILE, không phải bộ nhớ tiến trình
        # đã mất) phải báo CONSUMED.
        ledger = TrialLedger(reg_path)
        proj = ledger.get(trial_id)
        assert proj.state is TrialState.CONSUMED
        assert proj.sealed is True
        assert proj.outcome_written is False  # chưa kịp ghi outcome thật — vẫn CONSUMED
        assert ledger.n_used() == 1

        # "Người vận hành KHÔNG có quyền phủ quyết" — gọi thẳng refund()
        # (dù bằng tay hay bằng script dọn dẹp) PHẢI bị từ chối.
        with pytest.raises(SealedTrialError):
            ledger.refund(trial_id, cause_machine="OS_KILL:SIGKILL")

    def test_chua_seal_thi_giet_tien_trinh_van_hoan_tra_binh_thuong(
        self, tmp_path: Path
    ) -> None:
        """Đối chứng: nếu bị giết TRƯỚC khi seal (chưa có chỉ số nào tồn
        tại), refund() vẫn phải hoạt động bình thường — L-Z53 không được
        làm mọi tiến trình bị giết đều thành CONSUMED, chỉ ca ĐÃ SEAL."""
        reg_path = tmp_path / "reg.jsonl"
        ledger = TrialLedger(reg_path)
        tid = ledger.reserve(
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
            provenance={
                "params_source": "yaml", "params_effective": {}, "git_sha": "a" * 40,
                "reproducible_from_sha": True, "data_hashes": {}, "cache_mode": "none",
                "guard_passed": True,
            },
            contribution=1,
        )
        # KHÔNG seal — mô phỏng OOM/kill trước khi có bất kỳ chỉ số nào.
        result = ledger.refund(tid, cause_machine="OOM:signal_9_before_first_metric")
        assert result is TrialState.REFUNDED
        assert ledger.get(tid).state is TrialState.REFUNDED
