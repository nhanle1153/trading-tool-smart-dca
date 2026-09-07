"""TD-0126 — hai ràng buộc §9c.7 trước đây CHỈ nằm trong `description` của
schema, tức văn bản mô tả chứ không phải luật máy cưỡng chế được:

  (a) §9c.7.3 — `explore_evidence` BẮT BUỘC khi `data_source == EXPLORE`.
      Thiếu nó thì không phân biệt được EXPLORE với TOOL_D_RESULTS, mất
      luôn ranh giới mà trường `data_source` sinh ra để giữ (DR-009).

  (b) §9c.7.4 ràng buộc (3) — ý tưởng bị loại KHÔNG được nộp lại dưới tên
      khác; *"trước khi thêm ý tưởng mới, query queue theo `mechanism`"*,
      tương đương `retest_forbidden` của sổ trial.

Máy không kiểm được hai cơ chế có THẬT SỰ trùng nhau không — nhưng chặn
được ca dễ xảy ra nhất: nộp lại gần như nguyên văn dưới một cái tên khác.
Ngưỡng nghi trùng cố ý có hậu quả NHẸ (phải khai `overlaps_with`), không
phải mất đơn — một ngưỡng mà đặt sai thì tốn kém sẽ thành cái núm để vặn.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "entrypoints"))

from tool_d.ledger.audit_checks import (  # noqa: E402
    WARN_ONLY_CODES,
    check_td0126_explore_evidence_va_trung_mechanism,
)
from tool_d.ledger.idea_queue import (  # noqa: E402
    NGUONG_NGHI_TRUNG,
    IdeaQueueError,
    do_trung,
    submit_idea,
    tim_nghi_trung,
)
from trial_ledger_audit import EXIT_AUDIT_FAILED, run_audit  # noqa: E402

SCHEMA = REPO_ROOT / "registry/schemas/idea_queue_entry.schema.json"

CO_CHE_A = "quy phong ho bat buoc dong vi the o vung gia cu khi chi so tai can bang"
CO_CHE_B = "dong tien ETF chay vao luc dong cua phien My tao ap luc mua co dinh"


def _don(**doi) -> dict:
    d = {
        "source": "LLM",
        "data_source": "MECHANISM",
        "title": "y tuong",
        "mechanism": CO_CHE_A,
        "who_pays": "ben bat buoc phong ho theo chi so",
        "durability": "rang buoc uy thac, khong arbitrage het",
        "phep_thu_du_kien": "so ky vong khi co tin hieu voi khi khong co",
        "filter_verdict": "PASS",
        "status": "QUEUED",
    }
    d.update(doi)
    return d


def _so_dong(p: Path) -> int:
    return len([x for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]) if p.exists() else 0


def _nop(so: Path, **doi) -> str:
    return submit_idea(don=_don(**doi), path=so, schema_path=SCHEMA)


@pytest.fixture
def so(tmp_path: Path) -> Path:
    return tmp_path / "idea_queue.jsonl"


class TestExploreEvidence:
    def test_explore_thieu_bang_chung_thi_tu_choi(self, so: Path) -> None:
        with pytest.raises(IdeaQueueError, match="explore_evidence"):
            _nop(so, data_source="EXPLORE", explore_evidence=None)
        assert _so_dong(so) == 0

    def test_explore_bang_chung_toan_khoang_trang_cung_tu_choi(self, so: Path) -> None:
        with pytest.raises(IdeaQueueError):
            _nop(so, data_source="EXPLORE", explore_evidence="   ")
        assert _so_dong(so) == 0

    def test_explore_co_bang_chung_thi_ghi_duoc(self, so: Path) -> None:
        _nop(so, data_source="EXPLORE", explore_evidence="phan tich OI 30 mã, 2024-2025")
        assert _so_dong(so) == 1

    def test_mechanism_khong_bi_doi_explore_evidence(self, so: Path) -> None:
        """Ràng buộc chỉ áp cho EXPLORE — MECHANISM không cần bằng chứng dữ liệu."""
        _nop(so, data_source="MECHANISM", explore_evidence=None)
        assert _so_dong(so) == 1

    def test_audit_bat_duoc_dong_sua_tay(self, so: Path, tmp_path: Path) -> None:
        don = _don(idea_id="IQ-0001", created_at="2026-07-01T00:00:00Z",
                   data_source="EXPLORE", explore_evidence=None)
        for k in ("selected_at", "budget_a_slot", "selection_reason", "tin_hieu",
                  "quy_tac", "nguong_bac_bo", "so_bien_the"):
            don[k] = None
        don["overlaps_with"] = []
        don["session_type"] = "IDEA"
        so.write_text(json.dumps(don, ensure_ascii=False) + "\n", encoding="utf-8")

        ket_qua = check_td0126_explore_evidence_va_trung_mechanism(so)
        assert ket_qua.is_fail is True
        assert "explore_evidence" in ket_qua.evidence

        reg = tmp_path / "reg.jsonl"
        reg.touch()
        exit_code, text = run_audit(registry_path=reg, idea_queue_path=so)
        assert exit_code == EXIT_AUDIT_FAILED, text
        assert "TD-0126" in text


class TestDoTrungMechanism:
    def test_giong_het_thi_bang_1(self) -> None:
        assert do_trung(CO_CHE_A, CO_CHE_A) == 1.0

    def test_khong_chung_tu_nao_thi_bang_0(self) -> None:
        assert do_trung("alpha bravo charlie", "delta echo foxtrot") == 0.0

    def test_bo_dau_tieng_viet(self) -> None:
        """Cùng một cơ chế hay được viết cả có dấu lẫn không dấu trong repo này —
        so sánh có dấu sẽ bỏ sót đúng ca cần bắt."""
        assert do_trung("quỹ phòng hộ bắt buộc đóng vị thế",
                        "quy phong ho bat buoc dong vi the") == 1.0

    def test_hai_co_che_khac_han_thi_duoi_nguong(self) -> None:
        assert do_trung(CO_CHE_A, CO_CHE_B) < NGUONG_NGHI_TRUNG

    def test_rong_thi_bang_0_khong_raise(self) -> None:
        assert do_trung("", CO_CHE_A) == 0.0


class TestChanNopLaiYTuongDaBiLoai:
    def test_nop_lai_co_che_da_bi_LOAI_duoi_ten_khac_thi_TU_CHOI(self, so: Path) -> None:
        """🔴 Ca chính của §9c.7.4 ràng buộc (3) — tương đương retest_forbidden."""
        _nop(so, idea_id="IQ-0001", title="ten cu", status="REJECTED",
             filter_verdict="FAIL_NO_PAYER")
        with pytest.raises(IdeaQueueError, match="ĐÃ BỊ LOẠI"):
            _nop(so, idea_id="IQ-0002", title="ten hoan toan khac")
        assert _so_dong(so) == 1, "ý tưởng đã bị loại vẫn lọt lại vào hàng chờ"

    def test_nghi_trung_don_dang_cho_thi_doi_KHAI_overlaps_with(self, so: Path) -> None:
        _nop(so, idea_id="IQ-0001")
        with pytest.raises(IdeaQueueError, match="overlaps_with"):
            _nop(so, idea_id="IQ-0002", title="ten khac")
        assert _so_dong(so) == 1

    def test_khai_overlaps_with_roi_thi_ghi_duoc(self, so: Path) -> None:
        """Máy không đoán hộ 'có thật là trùng không' — nó chỉ đòi người nộp
        NHÌN THẤY đơn kia và nói ra."""
        _nop(so, idea_id="IQ-0001")
        _nop(so, idea_id="IQ-0002", title="ten khac", overlaps_with=["IQ-0001"])
        assert _so_dong(so) == 2

    def test_co_che_khac_han_thi_khong_bi_can(self, so: Path) -> None:
        _nop(so, idea_id="IQ-0001")
        _nop(so, idea_id="IQ-0002", mechanism=CO_CHE_B, title="co che khac")
        assert _so_dong(so) == 2

    def test_khai_overlaps_with_KHONG_mo_duong_cho_don_da_bi_loai(self, so: Path) -> None:
        """Khai `overlaps_with` là cách nói 'tôi đã thấy đơn kia, đây là cơ chế
        khác'. Nó hợp lệ — nhưng chỉ vì người nộp phải viết ra, không phải vì
        máy tin. Ghi lại hành vi này để lần sau ai siết thêm thì thấy nó là
        quyết định có ý thức, không phải kẽ hở bỏ quên."""
        _nop(so, idea_id="IQ-0001", status="REJECTED", filter_verdict="FAIL_NO_PAYER")
        _nop(so, idea_id="IQ-0002", title="khac", overlaps_with=["IQ-0001"])
        assert _so_dong(so) == 2

    def test_tim_nghi_trung_sap_xep_cao_truoc(self, so: Path) -> None:
        entries = [
            {"idea_id": "IQ-0001", "status": "QUEUED", "mechanism": CO_CHE_A},
            {"idea_id": "IQ-0002", "status": "QUEUED", "mechanism": CO_CHE_A + " them vai tu nua"},
        ]
        ra = tim_nghi_trung(entries, CO_CHE_A)
        assert [x[0] for x in ra] == ["IQ-0001", "IQ-0002"]
        assert ra[0][2] >= ra[1][2]


class TestAuditSoDaGhi:
    @staticmethod
    def _ghi(so: Path, dons: list[dict]) -> None:
        with so.open("w", encoding="utf-8") as f:
            for i, d in enumerate(dons):
                d.setdefault("idea_id", f"IQ-{i + 1:04d}")
                d.setdefault("created_at", "2026-07-01T00:00:00Z")
                d.setdefault("overlaps_with", [])
                d.setdefault("explore_evidence", None)
                f.write(json.dumps(d, ensure_ascii=False) + "\n")

    def test_so_rong_thi_chua_do_duoc(self, so: Path) -> None:
        so.touch()
        assert check_td0126_explore_evidence_va_trung_mechanism(so).measured.status.name == "PENDING"

    def test_hai_don_trung_sua_tay_thi_so_ban(self, so: Path) -> None:
        self._ghi(so, [_don(), _don(title="ten khac")])
        ket_qua = check_td0126_explore_evidence_va_trung_mechanism(so)
        assert ket_qua.is_fail is True
        assert "IQ-0002" in ket_qua.evidence

    def test_moi_cap_trung_chi_bao_MOT_lan(self, so: Path) -> None:
        """Đơn nộp SAU phải khai đơn nộp TRƯỚC, không ngược lại — nếu so cả hai
        chiều thì mỗi cặp bị đếm hai lần và báo cáo phồng lên gấp đôi."""
        self._ghi(so, [_don(), _don(title="ten khac")])
        assert check_td0126_explore_evidence_va_trung_mechanism(so).evidence.count("cơ chế trùng") == 1

    def test_da_khai_overlaps_with_thi_dat(self, so: Path) -> None:
        self._ghi(so, [_don(), _don(title="ten khac", overlaps_with=["IQ-0001"])])
        assert check_td0126_explore_evidence_va_trung_mechanism(so).ok is True

    def test_td0126_CHAN_CUNG_khong_phai_canh_bao(self) -> None:
        assert "TD-0126" not in WARN_ONLY_CODES
        assert WARN_ONLY_CODES == frozenset({"L-Z17"})
