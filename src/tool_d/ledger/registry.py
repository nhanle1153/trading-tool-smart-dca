"""TrialLedger — đọc/ghi `trial_registry.jsonl`. DR-014 (sổ hai trạng thái).

Sổ NHẬT KÝ SỰ KIỆN (MT-01, back-end-note.md mục 7): mỗi dòng một sự kiện
(RESERVE/SEAL/CONSUME/REFUND/CONTAMINATE), append-only TUYỆT ĐỐI — không
bao giờ sửa hay xoá một dòng đã ghi. Trạng thái hiện tại của một trial là
BẢN CHIẾU tính lại bằng cách đọc hết sổ, không phải trường ghi tại chỗ.

Đường DUY NHẤT tới CALIB/WFO/LOCKBOX phải đi qua `reserve()` trước khi
chạm dữ liệu (L-Z52) — không có đặt chỗ hợp lệ, bộ chạy TỪ CHỐI khởi
động, KHÔNG được chạm dữ liệu trước.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from tool_d.ledger.budget import REFUND_CAP_PER_HYPOTHESIS, HypothesisKey
from tool_d.ledger import budget as _budget

DEFAULT_REGISTRY_PATH = Path("registry/trial_registry.jsonl")


class TrialState(Enum):
    RESERVED = "RESERVED"
    CONSUMED = "CONSUMED"
    REFUNDED = "REFUNDED"


class LedgerError(RuntimeError):
    """Lỗi chung của sổ trial."""


class UnknownTrialError(LedgerError):
    """Thao tác trên một trial_id chưa từng RESERVE."""


class BudgetExhaustedError(LedgerError):
    """Khả dụng < contribution — TỪ CHỐI khởi động, KHÔNG chạm dữ liệu (L-Z52)."""


class SealedTrialError(LedgerError):
    """Cố hoàn trả một trial ĐÃ có con dấu — không có quyền phủ quyết
    của người vận hành (L-Z53, spec dòng 3499-3500)."""


class AlreadyFinalizedError(LedgerError):
    """Trial đã CONSUMED/REFUNDED — không ghi outcome hay hoàn trả lại
    lần hai (outcome chỉ được ghi ĐÚNG MỘT LẦN, spec dòng 3762)."""


@dataclass
class TrialProjection:
    """Bản chiếu trạng thái của MỘT trial — tính lại từ sổ sự kiện,
    KHÔNG phải trường lưu sẵn trên đĩa.
    """

    trial_id: str
    state: TrialState
    contribution: int
    hypothesis_slot: str
    param_under_test: str
    param_value: Any
    sealed: bool = False
    outcome: dict[str, Any] | None = field(default=None)


def _utcnow_iso() -> str:
    """UTC, ISO-8601, kết thúc bằng Z — bắt buộc (G.12: cấm giờ local,
    L-Z10 đòi registered_at < executed_at, chỉ đúng khi cùng múi giờ).
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class TrialLedger:
    def __init__(self, path: Path = DEFAULT_REGISTRY_PATH) -> None:
        self._path = path
        if not self._path.exists():
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.touch()

    # ── đọc sổ / bản chiếu ──────────────────────────────────────────
    def _read_events(self) -> list[dict[str, Any]]:
        text = self._path.read_text(encoding="utf-8")
        return [json.loads(line) for line in text.splitlines() if line.strip()]

    def _append(self, event: Mapping[str, Any]) -> None:
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

    def projections(self) -> dict[str, TrialProjection]:
        """Tính lại trạng thái MỌI trial từ đầu sổ."""
        result: dict[str, TrialProjection] = {}
        for e in self._read_events():
            tid = e["trial_id"]
            kind = e["event"]
            if kind == "RESERVE":
                result[tid] = TrialProjection(
                    trial_id=tid,
                    state=TrialState.RESERVED,
                    contribution=e["contribution"],
                    hypothesis_slot=e["hypothesis_slot"],
                    param_under_test=e["param_under_test"],
                    param_value=e["param_value"],
                )
            elif kind == "SEAL":
                result[tid].sealed = True
            elif kind == "CONSUME":
                result[tid].state = TrialState.CONSUMED
                result[tid].outcome = e["outcome"]
            elif kind == "REFUND":
                result[tid].state = TrialState.REFUNDED
            elif kind == "CONTAMINATE":
                pass  # dấu vết audit — không đổi state
        return result

    def get(self, trial_id: str) -> TrialProjection:
        proj = self.projections().get(trial_id)
        if proj is None:
            raise UnknownTrialError(f"chưa từng reserve: {trial_id}")
        return proj

    # ── kế toán ───────────────────────────────────────────────────
    def n_used(self) -> int:
        """N_ĐÃ_DÙNG = Σ contribution của dòng state==CONSUMED (L-Z11)."""
        return sum(
            p.contribution for p in self.projections().values() if p.state is TrialState.CONSUMED
        )

    def n_reserved(self) -> int:
        return sum(
            p.contribution for p in self.projections().values() if p.state is TrialState.RESERVED
        )

    def available(self, *, n_dang_ky: int, n_tai_sinh: int = 0) -> int:
        return _budget.available(
            n_dang_ky=n_dang_ky,
            n_tai_sinh=n_tai_sinh,
            n_used=self.n_used(),
            n_reserved=self.n_reserved(),
        )

    def refund_count(self, key: HypothesisKey) -> int:
        events = self._read_events()
        reserve_by_trial = {e["trial_id"]: e for e in events if e["event"] == "RESERVE"}
        count = 0
        for e in events:
            if e["event"] != "REFUND":
                continue
            r = reserve_by_trial.get(e["trial_id"])
            if r is not None and key.matches(
                hypothesis_slot=r["hypothesis_slot"],
                param_under_test=r["param_under_test"],
                param_value=r["param_value"],
            ):
                count += 1
        return count

    # ── ghi sự kiện ───────────────────────────────────────────────
    def _next_trial_id(self) -> str:
        n_reserves_ever = sum(1 for e in self._read_events() if e["event"] == "RESERVE")
        return f"D-{n_reserves_ever + 1:04d}"

    def reserve(
        self,
        *,
        n_dang_ky: int,
        n_tai_sinh: int = 0,
        tool_id: str = "D",
        budget_line: str,
        hypothesis_slot: str,
        direction: str,
        dataset: str,
        param_under_test: str,
        param_value: Any,
        params_frozen_hash: str,
        config_hash: str,
        code_commit: str,
        provenance: Mapping[str, Any],
        contribution: int,
    ) -> str:
        """Đặt chỗ. Raise `BudgetExhaustedError` nếu Khả dụng < contribution
        — TRƯỚC KHI CHẠM BẤT KỲ DỮ LIỆU NÀO (L-Z52, spec dòng 3471-3472).
        """
        if contribution < 1:
            raise LedgerError("contribution phải >= 1 — không có mức 0 (fail-closed)")
        khadung = self.available(n_dang_ky=n_dang_ky, n_tai_sinh=n_tai_sinh)
        if khadung < contribution:
            raise BudgetExhaustedError(
                f"Khả dụng ({khadung}) < contribution ({contribution}) — TỪ CHỐI khởi động"
            )
        trial_id = self._next_trial_id()
        self._append(
            {
                "event": "RESERVE",
                "trial_id": trial_id,
                "tool_id": tool_id,
                "registered_at": _utcnow_iso(),
                "budget_line": budget_line,
                "hypothesis_slot": hypothesis_slot,
                "direction": direction,
                "dataset": dataset,
                "param_under_test": param_under_test,
                "param_value": param_value,
                "params_frozen_hash": params_frozen_hash,
                "config_hash": config_hash,
                "code_commit": code_commit,
                "provenance": dict(provenance),
                "contribution": contribution,
            }
        )
        return trial_id

    def seal(self, trial_id: str, *, seal_path: str) -> None:
        """Bộ chạy TỰ gọi ngay khi chỉ số đầu tiên tồn tại trong bộ nhớ,
        TRƯỚC cả khi in/ghi kết quả (DR-014 §3). Từ đây, `refund()` cho
        trial này PHẢI raise `SealedTrialError`.
        """
        proj = self.get(trial_id)
        if proj.sealed:
            raise AlreadyFinalizedError(f"{trial_id} đã có con dấu, không đóng dấu lần hai")
        self._append(
            {
                "event": "SEAL",
                "trial_id": trial_id,
                "sealed_at": _utcnow_iso(),
                "seal_path": seal_path,
            }
        )

    def consume(
        self,
        trial_id: str,
        *,
        outcome: Mapping[str, Any],
        verdict: str,
        rejection_reason: str | None = None,
        retest_forbidden: bool = True,
    ) -> None:
        """Ghi outcome — ĐÚNG MỘT LẦN (spec dòng 3762: sửa dòng cũ = sổ
        mất hiệu lực; ở đây thể hiện bằng raise nếu gọi lần hai).
        """
        proj = self.get(trial_id)
        if proj.state is not TrialState.RESERVED:
            raise AlreadyFinalizedError(
                f"{trial_id} đã ở trạng thái {proj.state.value}, không consume lại được"
            )
        self._append(
            {
                "event": "CONSUME",
                "trial_id": trial_id,
                "executed_at": _utcnow_iso(),
                "outcome": dict(outcome),
                "verdict": verdict,
                "rejection_reason": rejection_reason,
                "retest_forbidden": retest_forbidden,
            }
        )

    def refund(self, trial_id: str, *, cause_machine: str) -> TrialState:
        """Hoàn trả đặt chỗ. `cause_machine` PHẢI do MÁY xác định (exit
        code / exception / guard-block) — không nhận lời khai người vận
        hành (DR-014 §3).

        Raise `SealedTrialError` nếu ĐÃ có con dấu (L-Z53) — không có
        đường phủ quyết.

        Đã hoàn trả đủ `REFUND_CAP_PER_HYPOTHESIS` (3) lần cho CÙNG một
        giả thuyết → CƯỠNG CHẾ CONSUMED thay vì hoàn trả lần này (DR-014
        §5: "Lần thứ 4 không có con dấu → vẫn CONSUMED"). Trả về trạng
        thái CUỐI CÙNG để caller biết chuyện gì vừa xảy ra.
        """
        proj = self.get(trial_id)
        if proj.sealed:
            raise SealedTrialError(f"{trial_id} đã có con dấu — không được hoàn trả (L-Z53)")
        if proj.state is not TrialState.RESERVED:
            raise AlreadyFinalizedError(f"{trial_id} đã ở trạng thái {proj.state.value}")

        key = HypothesisKey(proj.hypothesis_slot, proj.param_under_test, proj.param_value)
        if self.refund_count(key) >= REFUND_CAP_PER_HYPOTHESIS:
            self._append(
                {
                    "event": "CONSUME",
                    "trial_id": trial_id,
                    "executed_at": _utcnow_iso(),
                    "outcome": {
                        "expectancy": None,
                        "sharpe": None,
                        "n_trades": None,
                        "max_single_loss_ratio": None,
                    },
                    "verdict": "INCONCLUSIVE",
                    "rejection_reason": (
                        f"cưỡng chế CONSUMED — đã chạm trần trả lại "
                        f"{REFUND_CAP_PER_HYPOTHESIS} lần cho cùng giả thuyết (DR-014 §5); "
                        f"nguyên nhân gốc lần này: {cause_machine}"
                    ),
                    "retest_forbidden": True,
                }
            )
            return TrialState.CONSUMED

        self._append(
            {
                "event": "REFUND",
                "trial_id": trial_id,
                "refunded_at": _utcnow_iso(),
                "refund_cause_machine": cause_machine,
            }
        )
        return TrialState.REFUNDED

    def mark_contaminated(self, trial_id: str, *, reason: str) -> None:
        """DR-014 §6 — nhiễm tham số tiêu gấp đôi. Trial PHẢI đã CONSUMED
        (kết quả đã bị nhìn, không thu hồi được) — chỉ thêm dấu vết audit,
        KHÔNG xoá hay đổi trạng thái ("KHÔNG được xoá lần chạy khỏi sổ
        với lý do 'không hợp lệ'", spec dòng 3557).
        """
        proj = self.get(trial_id)
        if proj.state is not TrialState.CONSUMED:
            raise LedgerError(
                f"chỉ đánh dấu nhiễm cho trial ĐÃ CONSUMED, {trial_id} đang ở "
                f"trạng thái {proj.state.value}"
            )
        self._append(
            {
                "event": "CONTAMINATE",
                "trial_id": trial_id,
                "contaminated_at": _utcnow_iso(),
                "reason": reason,
            }
        )
