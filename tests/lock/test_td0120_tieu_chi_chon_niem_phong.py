"""TD-0120 (OQ-07) — `selection_reason` phải TRÍCH mã tiêu chí đã niêm phong.

§9c.7.4 bắt viết tiêu chí chọn TRƯỚC khi mở hàng chờ, commit vào git, và
`selection_reason` phải trích tiêu chí đã commit chứ không viết mới. Spec
tự thừa nhận phần "viết bằng cơ chế kinh tế" không máy nào kiểm được —
nhưng phần TRÍCH DẪN thì kiểm được, cùng thủ thuật §12d dùng cho báo cáo
định kỳ ("mọi câu phải trích một con số").

Bốn ca sổ bẩn được canh ở đây, và ca (c)/(d) là fail-closed: chọn khi quý
đó chưa niêm phong tiêu chí, hoặc chọn trong quý đã khai hạn ngạch 0.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "entrypoints"))

from tool_d.ledger.audit_checks import (  # noqa: E402
    DEFAULT_TIEU_CHI_DIR,
    check_td0120_selection_reason_trich_ma_tieu_chi,
)

TIEU_CHI_THAT = REPO_ROOT / "docs/decisions/DR-Q3-2026-tieu-chi-chon-y-tuong.md"


def _don(idea_id: str, *, selection_reason: str | None,
         selected_at: str = "2026-08-15T00:00:00Z") -> dict:
    return {
        "idea_id": idea_id, "created_at": "2026-07-01T00:00:00Z", "source": "LLM",
        "session_type": "IDEA", "data_source": "MECHANISM", "explore_evidence": None,
        "title": "y tuong", "mechanism": "co che", "who_pays": "ai tra tien",
        "durability": "vi sao ben",
        "phep_thu_du_kien": "so ket qua co tin hieu vs khong",
        "filter_verdict": "PASS", "overlaps_with": [], "status": "SELECTED",
        "selected_at": selected_at, "budget_a_slot": "A-01",
        "selection_reason": selection_reason,
        "tin_hieu": "cong thuc", "quy_tac": "noi vao ZSS",
        "nguong_bac_bo": "khong cai thien 8% thi loai", "so_bien_the": 4,
    }


def _ghi(path: Path, dons: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(d, ensure_ascii=False) + "\n" for d in dons), encoding="utf-8"
    )


def _thu_muc_tieu_chi(tmp_path: Path, *, han_ngach: int, quy: int = 3, nam: int = 2026) -> Path:
    d = tmp_path / "decisions"
    d.mkdir(exist_ok=True)
    (d / f"DR-Q{quy}-{nam}-tieu-chi-chon-y-tuong.md").write_text(
        f"# tieu chi quy {quy}/{nam}\n\n"
        f"```\nHAN_NGACH_CHON: {han_ngach}\n```\n\n"
        f"## TC-Q{quy}-{nam}-01 — co che doc lap\n"
        f"## TC-Q{quy}-{nam}-02 — ai tra tien\n",
        encoding="utf-8",
    )
    return d


class TestFileTieuChiThat:
    def test_file_quy_3_2026_ton_tai_va_khai_han_ngach_0(self) -> None:
        """File niêm phong thật phải đọc được bằng CHÍNH các mẫu mà phép
        kiểm dùng — nếu không, luật chỉ nằm trên giấy."""
        assert TIEU_CHI_THAT.exists()
        from tool_d.ledger.audit_checks import HAN_NGACH_RE, TC_CODE_RE

        noi_dung = TIEU_CHI_THAT.read_text(encoding="utf-8")
        m = HAN_NGACH_RE.search(noi_dung)
        assert m is not None and int(m.group(1)) == 0
        assert {x.group(0) for x in TC_CODE_RE.finditer(noi_dung)} == {
            "TC-Q3-2026-01", "TC-Q3-2026-02", "TC-Q3-2026-03", "TC-Q3-2026-04"
        }

    def test_duong_dan_mac_dinh_tro_dung_thu_muc_decisions(self) -> None:
        assert DEFAULT_TIEU_CHI_DIR == Path("docs/decisions")


class TestBonCaSoBan:
    def test_a_khong_trich_ma_nao(self, tmp_path: Path) -> None:
        iq = tmp_path / "iq.jsonl"
        _ghi(iq, [_don("IQ-0001", selection_reason="chon vi co che nghe hop ly")])
        kq = check_td0120_selection_reason_trich_ma_tieu_chi(
            iq, _thu_muc_tieu_chi(tmp_path, han_ngach=1)
        )
        assert kq.is_fail is True
        assert "không trích mã tiêu chí nào" in kq.evidence

    def test_b_trich_ma_khong_co_that(self, tmp_path: Path) -> None:
        iq = tmp_path / "iq.jsonl"
        _ghi(iq, [_don("IQ-0001", selection_reason="theo TC-Q3-2026-09, co che doc lap")])
        kq = check_td0120_selection_reason_trich_ma_tieu_chi(
            iq, _thu_muc_tieu_chi(tmp_path, han_ngach=1)
        )
        assert kq.is_fail is True
        assert "TC-Q3-2026-09" in kq.evidence

    def test_c_quy_chua_niem_phong_tieu_chi(self, tmp_path: Path) -> None:
        """Fail-closed — đúng điều cấm ở spec dòng 4935."""
        iq = tmp_path / "iq.jsonl"
        _ghi(iq, [_don("IQ-0001", selection_reason="theo TC-Q1-2027-01",
                       selected_at="2027-02-01T00:00:00Z")])
        kq = check_td0120_selection_reason_trich_ma_tieu_chi(
            iq, _thu_muc_tieu_chi(tmp_path, han_ngach=1)
        )
        assert kq.is_fail is True
        assert "CHƯA có file tiêu chí" in kq.evidence

    def test_d_quy_khai_han_ngach_0_ma_van_chon(self, tmp_path: Path) -> None:
        iq = tmp_path / "iq.jsonl"
        _ghi(iq, [_don("IQ-0001", selection_reason="theo TC-Q3-2026-01, co che doc lap")])
        kq = check_td0120_selection_reason_trich_ma_tieu_chi(
            iq, _thu_muc_tieu_chi(tmp_path, han_ngach=0)
        )
        assert kq.is_fail is True
        assert "HAN_NGACH_CHON: 0" in kq.evidence


class TestCaHopLe:
    def test_trich_dung_ma_va_han_ngach_con_cho_thi_dat(self, tmp_path: Path) -> None:
        iq = tmp_path / "iq.jsonl"
        _ghi(iq, [_don("IQ-0001",
                       selection_reason="theo TC-Q3-2026-01: co che doc lap voi thanh khoan zone")])
        kq = check_td0120_selection_reason_trich_ma_tieu_chi(
            iq, _thu_muc_tieu_chi(tmp_path, han_ngach=1)
        )
        assert kq.ok is True, kq.evidence

    def test_chua_chon_ai_thi_chua_do_duoc(self, tmp_path: Path) -> None:
        iq = tmp_path / "iq.jsonl"
        iq.touch()
        kq = check_td0120_selection_reason_trich_ma_tieu_chi(
            iq, _thu_muc_tieu_chi(tmp_path, han_ngach=0)
        )
        assert kq.measured.status.name == "PENDING"
