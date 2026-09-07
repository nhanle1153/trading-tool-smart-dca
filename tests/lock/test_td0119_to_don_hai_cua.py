"""TD-0119 (MT-12) — tờ đơn ý tưởng có HAI CỬA.

Cửa NỘP rẻ: 3 câu kinh tế §0.1 + `phep_thu_du_kien` phác thảo.
Cửa CHỌN chặt: `tin_hieu` / `quy_tac` / `nguong_bac_bo` / `so_bien_the`
bắt buộc có nội dung — thiếu thì sổ bẩn, fail-closed.

Và `so_bien_the` phải ĐỐI CHIẾU được với sổ trial (`hypothesis_slot =
IQ-xxxx`), nếu không nó chỉ là lời khai trông như bằng chứng — đúng loại
sai lầm MT-10 vừa phải sửa.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "entrypoints"))

from tool_d.ledger.audit_checks import (  # noqa: E402
    CUA_CHON_FIELDS,
    check_td0119_selected_du_phep_thu,
    check_td0119_so_bien_the_khong_vuot_khai,
)
from trial_ledger_audit import EXIT_AUDIT_FAILED, run_audit  # noqa: E402

import pytest  # noqa: E402


def _don(idea_id: str, *, status: str = "QUEUED", du_cua_chon: bool = False,
         so_bien_the: int | None = None) -> dict:
    d = {
        "idea_id": idea_id,
        "created_at": "2026-07-01T00:00:00Z",
        "source": "LLM",
        "session_type": "IDEA",
        "data_source": "MECHANISM",
        "explore_evidence": None,
        "title": f"y tuong {idea_id}",
        "mechanism": "ai lam gi tao ra dich chuyen gia",
        "who_pays": "ai la nguoi thua o phia ben kia",
        "durability": "vi sao chua bi arbitrage het",
        "phep_thu_du_kien": "so ky vong khi co tin hieu voi khi khong co, tren cung tap",
        "filter_verdict": "PASS",
        "overlaps_with": [],
        "status": status,
        "selected_at": "2026-08-01T00:00:00Z" if status == "SELECTED" else None,
        "budget_a_slot": "A-01" if status == "SELECTED" else None,
        "selection_reason": "co che doc lap voi thanh khoan zone" if status == "SELECTED" else None,
        "tin_hieu": None, "quy_tac": None, "nguong_bac_bo": None, "so_bien_the": None,
    }
    if du_cua_chon:
        d["tin_hieu"] = "khoi luong trong vung / MA20 khoi luong, khung 1H"
        d["quy_tac"] = "cong vao diem ZSS, trong so w4"
        d["nguong_bac_bo"] = "khong cai thien pnl_abs >= 8% so voi ban goc thi loai"
        d["so_bien_the"] = 4 if so_bien_the is None else so_bien_the
    elif so_bien_the is not None:
        d["so_bien_the"] = so_bien_the
    return d


def _ghi(path: Path, dons: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(d, ensure_ascii=False) + "\n" for d in dons), encoding="utf-8"
    )


class TestCuaChon:
    @pytest.mark.parametrize("thieu", CUA_CHON_FIELDS)
    def test_selected_thieu_bat_ky_truong_nao_deu_ban_so(self, tmp_path: Path, thieu: str) -> None:
        iq = tmp_path / "iq.jsonl"
        don = _don("IQ-0001", status="SELECTED", du_cua_chon=True)
        don[thieu] = None
        _ghi(iq, [don])
        ket_qua = check_td0119_selected_du_phep_thu(iq)
        assert ket_qua.is_fail is True, f"thiếu '{thieu}' mà vẫn cho qua"
        assert thieu in ket_qua.evidence

    def test_selected_du_bon_truong_thi_dat(self, tmp_path: Path) -> None:
        iq = tmp_path / "iq.jsonl"
        _ghi(iq, [_don("IQ-0001", status="SELECTED", du_cua_chon=True)])
        assert check_td0119_selected_du_phep_thu(iq).ok is True

    def test_cua_nop_khong_bi_doi_bon_truong_do(self, tmp_path: Path) -> None:
        """Đơn mới nộp (QUEUED) chỉ cần 3 câu kinh tế + phác thảo phép thử
        — đây chính là chỗ 'hai cửa' khác 'tất cả ở cửa nộp'."""
        iq = tmp_path / "iq.jsonl"
        _ghi(iq, [_don("IQ-0002", status="QUEUED")])
        assert check_td0119_selected_du_phep_thu(iq).measured.status.name == "PENDING"

    def test_so_ban_chan_chay_that(self, tmp_path: Path) -> None:
        iq = tmp_path / "iq.jsonl"
        don = _don("IQ-0001", status="SELECTED", du_cua_chon=True)
        don["nguong_bac_bo"] = None
        _ghi(iq, [don])
        reg = tmp_path / "reg.jsonl"
        reg.touch()
        exit_code, text = run_audit(registry_path=reg, idea_queue_path=iq)
        assert exit_code == EXIT_AUDIT_FAILED, text
        assert "TD-0119a" in text


class TestSoBienTheDoiChieuSoTrial:
    @staticmethod
    def _trial(reg: Path, trial_id: str, slot: str) -> None:
        prov = {
            "params_source": "yaml", "params_effective": {}, "git_sha": "a" * 40,
            "reproducible_from_sha": True, "data_hashes": {}, "cache_mode": "none",
            "guard_passed": True,
        }
        with reg.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "event": "RESERVE", "trial_id": trial_id,
                "registered_at": "2026-08-10T10:00:00Z", "budget_line": "B1",
                "hypothesis_slot": slot, "direction": "LONG", "dataset": "CALIB",
                "param_under_test": "x", "param_value": 1, "params_frozen_hash": "f",
                "config_hash": f"c-{trial_id}", "code_commit": "a", "provenance": prov,
                "contribution": 1, "tool_id": "D",
            }, ensure_ascii=False) + "\n")
            f.write(json.dumps({
                "event": "CONSUME", "trial_id": trial_id,
                "executed_at": "2026-08-10T11:00:00Z",
                "outcome": {"expectancy": None, "sharpe": None, "n_trades": None,
                            "max_single_loss_ratio": None},
                "verdict": "INCONCLUSIVE", "rejection_reason": None, "retest_forbidden": True,
            }, ensure_ascii=False) + "\n")

    def test_tieu_nhieu_hon_khai_thi_so_ban(self, tmp_path: Path) -> None:
        iq = tmp_path / "iq.jsonl"
        _ghi(iq, [_don("IQ-0007", status="SELECTED", du_cua_chon=True, so_bien_the=2)])
        reg = tmp_path / "reg.jsonl"
        reg.touch()
        for i in range(3):  # khai 2, tiêu 3
            self._trial(reg, f"D-000{i + 1}", "IQ-0007")

        ket_qua = check_td0119_so_bien_the_khong_vuot_khai(iq, reg)
        assert ket_qua.is_fail is True
        assert "IQ-0007" in ket_qua.evidence

        exit_code, text = run_audit(registry_path=reg, idea_queue_path=iq)
        assert exit_code == EXIT_AUDIT_FAILED, text
        assert "TD-0119b" in text

    def test_tieu_dung_bang_khai_thi_dat(self, tmp_path: Path) -> None:
        iq = tmp_path / "iq.jsonl"
        _ghi(iq, [_don("IQ-0007", status="SELECTED", du_cua_chon=True, so_bien_the=2)])
        reg = tmp_path / "reg.jsonl"
        reg.touch()
        for i in range(2):
            self._trial(reg, f"D-000{i + 1}", "IQ-0007")
        assert check_td0119_so_bien_the_khong_vuot_khai(iq, reg).ok is True

    def test_trial_cua_y_tuong_khac_khong_bi_dem_nham(self, tmp_path: Path) -> None:
        iq = tmp_path / "iq.jsonl"
        _ghi(iq, [_don("IQ-0007", status="SELECTED", du_cua_chon=True, so_bien_the=1)])
        reg = tmp_path / "reg.jsonl"
        reg.touch()
        self._trial(reg, "D-0001", "IQ-0007")
        self._trial(reg, "D-0002", "A")       # slot cũ, không phải ý tưởng queue
        self._trial(reg, "D-0003", "IQ-0099")  # ý tưởng khác
        assert check_td0119_so_bien_the_khong_vuot_khai(iq, reg).ok is True
