"""TD-0118 — L-Z17 (trần 5 suất NGÂN SÁCH A mỗi quý) là phép kiểm
CHỈ CẢNH BÁO: vượt trần thì báo rõ, nhưng KHÔNG chặn chạy.

Quyết định chủ dự án 07/09/2026 (MT-11) — sửa có ý thức dòng H16 của spec
("Fail → chặn chạy, không cảnh báo suông") cho RIÊNG L-Z17: con số 5 là kỷ
luật con người, không chảy vào N/DSR, và đòn bẩy cũ phạt sai chỗ (vượt trần
CHỌN ý tưởng lại khoá việc ĐO).

🔴 Nửa còn lại của test này quan trọng ngang phần trên: L-Z16 (ý tưởng nghĩ
ra sau khi xem kết quả Tool D) PHẢI vẫn chặn cứng — đó là chống nhiễm dữ
liệu, không phải kỷ luật cá nhân. Nới lây sang L-Z16 là hỏng.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "entrypoints"))

from tool_d.ledger.audit_checks import (  # noqa: E402
    BUDGET_A_SLOTS_PER_QUARTER_MAX,
    WARN_ONLY_CODES,
    check_lz17_budget_a_slots_per_quarter,
)
from trial_ledger_audit import run_audit  # noqa: E402


def _don(idea_id: str, *, status: str, selected_at: str | None = None,
         data_source: str = "MECHANISM") -> dict:
    """Một tờ đơn hợp lệ theo §9c.7.3 — đủ ba câu của bộ lọc §0.1."""
    return {
        "idea_id": idea_id,
        "created_at": "2026-07-01T00:00:00Z",
        "source": "HUMAN",
        "session_type": "IDEA",
        "data_source": data_source,
        "explore_evidence": None,
        "title": f"y tuong {idea_id}",
        "mechanism": "ai lam gi tao ra dich chuyen gia",
        "who_pays": "ai la nguoi thua o phia ben kia",
        "durability": "vi sao chua bi arbitrage het",
        "filter_verdict": "PASS",
        "overlaps_with": [],
        "status": status,
        "selected_at": selected_at,
        "budget_a_slot": None if selected_at is None else f"A-{idea_id[-2:]}",
        "selection_reason": None if selected_at is None else "co che doc lap voi thanh khoan zone",
    }


def _ghi(path: Path, dons: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(d, ensure_ascii=False) + "\n" for d in dons),
        encoding="utf-8",
    )


class TestVuotTranChiCanhBao:
    def test_sau_don_selected_cung_quy_van_exit_0(self, tmp_path: Path) -> None:
        assert BUDGET_A_SLOTS_PER_QUARTER_MAX == 5, "trần vẫn là 5 — TD-0118 không đổi con số"
        iq = tmp_path / "iq.jsonl"
        _ghi(iq, [
            _don(f"IQ-000{i}", status="SELECTED", selected_at=f"2026-08-0{i}T00:00:00Z")
            for i in range(1, 7)  # 6 suất trong CÙNG quý 3/2026 -> vượt trần 5
        ])
        reg = tmp_path / "reg.jsonl"
        reg.touch()

        exit_code, text = run_audit(registry_path=reg, idea_queue_path=iq)

        assert exit_code == 0, f"vượt trần Ngân sách A KHÔNG được chặn chạy:\n{text}"
        assert "L-Z17" in text
        assert "VƯỢT TRẦN" in text, f"phải báo rõ là đã vượt, không im lặng:\n{text}"

    def test_ban_than_phep_kiem_van_bao_chua_dat(self, tmp_path: Path) -> None:
        """Cảnh báo ≠ bỏ qua: phép kiểm vẫn kết luận CHƯA ĐẠT, chỉ khác ở
        chỗ kết luận đó không được nối vào exit code."""
        iq = tmp_path / "iq.jsonl"
        _ghi(iq, [
            _don(f"IQ-000{i}", status="SELECTED", selected_at=f"2026-08-0{i}T00:00:00Z")
            for i in range(1, 7)
        ])
        ket_qua = check_lz17_budget_a_slots_per_quarter(iq)
        assert ket_qua.is_fail is True
        assert ket_qua.code in WARN_ONLY_CODES

    def test_dung_tran_5_thi_dat(self, tmp_path: Path) -> None:
        iq = tmp_path / "iq.jsonl"
        _ghi(iq, [
            _don(f"IQ-000{i}", status="SELECTED", selected_at=f"2026-08-0{i}T00:00:00Z")
            for i in range(1, 6)  # đúng 5
        ])
        assert check_lz17_budget_a_slots_per_quarter(iq).ok is True


class TestLZ16KhongBiNoiLay:
    def test_tool_d_results_khong_bi_reject_van_chan_cung(self, tmp_path: Path) -> None:
        iq = tmp_path / "iq.jsonl"
        _ghi(iq, [_don("IQ-0009", status="QUEUED", data_source="TOOL_D_RESULTS")])
        reg = tmp_path / "reg.jsonl"
        reg.touch()

        exit_code, text = run_audit(registry_path=reg, idea_queue_path=iq)

        assert exit_code != 0, f"L-Z16 là chống nhiễm dữ liệu, PHẢI chặn cứng:\n{text}"
        assert "L-Z16" in text
        assert "CHƯA ĐẠT" in text

    def test_lz16_khong_nam_trong_danh_sach_chi_canh_bao(self) -> None:
        assert "L-Z16" not in WARN_ONLY_CODES
        assert WARN_ONLY_CODES == frozenset({"L-Z17"})
