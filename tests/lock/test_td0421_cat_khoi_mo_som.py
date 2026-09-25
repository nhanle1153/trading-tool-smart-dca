"""🔒 TD-0421 (`DR-IQ-04`) — mở sớm cửa CHỌN quý 1/2027 từ 25/09/2026, CẮT tường minh khối mở sớm của `DR-IQ-03`.

Canh:
1. **Cắt đúng:** trước điểm cắt vẫn theo khối cũ (lần chọn IQ-0003 ngày 24/09 không đổi tiêu chí), từ điểm cắt theo
   khối mới và tính vào quỹ quý của khối mới.
2. **Fail-closed:** cắt DR không có khối / cắt khối không chồng / chồng mà không khai cắt ⇒ `TieuChiError`.
3. **Mở sớm không thành thêm lượt:** chọn sớm ăn vào quỹ quý 1/2027; lần hai (kể cả đã sang 2027) bị từ chối.
4. **Trên `docs/decisions/` THẬT:** `DR-IQ-04` làm đúng việc nó khai, và phiên IDEA sạch đọc được nó.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

import pytest

from tool_d.ledger.audit_checks import TieuChiError, check_td0120_selection_reason_trich_ma_tieu_chi, tieu_chi_cho_ngay
from tool_d.ledger.idea_queue import IdeaQueueError, chon_y_tuong

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA = REPO_ROOT / "registry/schemas/idea_queue_entry.schema.json"
Q4 = "DR-Q4-2026-tieu-chi-chon-y-tuong.md"
Q1 = "DR-Q1-2027-tieu-chi-chon-y-tuong.md"


def _khoi(dr: str, obj: dict) -> str:
    return f"<!-- {dr}:MO_SOM:BEGIN -->\n```json\n{json.dumps(obj)}\n```\n<!-- {dr}:MO_SOM:END -->\n"


def _don(idea_id: str) -> dict:
    return {
        "idea_id": idea_id, "created_at": "2026-09-18T08:00:00Z", "source": "LLM",
        "session_type": "IDEA", "data_source": "MECHANISM", "explore_evidence": None,
        "title": f"y tuong {idea_id}", "mechanism": f"co che {idea_id} rieng biet hoan toan",
        "who_pays": "ben thu ba tra", "durability": "can chiu rui ro",
        "phep_thu_du_kien": "so forward voi trung tinh", "filter_verdict": "PASS",
        "overlaps_with": [], "status": "QUEUED", "selected_at": None, "budget_a_slot": None,
        "selection_reason": None, "tin_hieu": None, "quy_tac": None, "nguong_bac_bo": None,
        "so_bien_the": None,
    }


def _to_chon(idea_id: str, ma: str = "TC-Q1-2027-01") -> dict:
    return {"idea_id": idea_id, "selection_reason": f"theo {ma}: co che doc lap", "tin_hieu": "x", "quy_tac": "y",
            "nguong_bac_bo": "CI 95% chua 0 thi bac bo", "so_bien_the": 1}


@pytest.fixture()
def m(tmp_path: Path) -> dict:
    d = tmp_path / "decisions"
    d.mkdir()
    for ten, han in (("DR-Q3-2026-tieu-chi-chon-y-tuong.md", 0), (Q4, 1), (Q1, 1)):
        ma = ten[3:10]
        (d / ten).write_text(f"```\nHAN_NGACH_CHON: {han}\n```\n## TC-{ma}-01\n", encoding="utf-8")
    (d / "DR-IQ-03-mo-som.md").write_text(_khoi("DR-IQ-03", {"tieu_chi": Q4, "tu_ngay": "2026-09-24"}),
                                          encoding="utf-8")
    iq = tmp_path / "iq.jsonl"
    iq.write_text("".join(json.dumps(_don(i)) + "\n" for i in ("IQ-0001", "IQ-0002")), encoding="utf-8")
    return {"dir": d, "iq": iq}


def _dr_iq_04(m: dict, **obj) -> None:
    (m["dir"] / "DR-IQ-04-mo-som.md").write_text(
        _khoi("DR-IQ-04", {"tieu_chi": Q1, "tu_ngay": "2026-09-25", "cat_khoi": "DR-IQ-03", **obj}), encoding="utf-8"
    )


def _chon(m: dict, t: dict, bay_gio: str) -> str:
    return chon_y_tuong(to_chon=t, path=m["iq"], schema_path=SCHEMA, tieu_chi_dir=m["dir"], bay_gio=bay_gio)


class TestCatDung:
    @pytest.mark.parametrize("ngay, ky_vong", [
        (date(2026, 9, 23), ("DR-Q3-2026-tieu-chi-chon-y-tuong.md", 2026, 3)),
        (date(2026, 9, 24), (Q4, 2026, 4)),
        (date(2026, 9, 25), (Q1, 2027, 1)),
        (date(2026, 9, 30), (Q1, 2027, 1)),
        (date(2026, 11, 15), (Q1, 2027, 1)),
        (date(2027, 2, 1), (Q1, 2027, 1)),
    ])
    def test_moi_ngay_mot_tieu_chi(self, m, ngay: date, ky_vong: tuple) -> None:
        _dr_iq_04(m)
        path, nam, quy = tieu_chi_cho_ngay(m["dir"], ngay)
        assert (path.name, nam, quy) == ky_vong

    def test_chon_som_ghi_duoc_va_audit_sach(self, m) -> None:
        _dr_iq_04(m)
        _chon(m, _to_chon("IQ-0001"), "2026-09-25T10:00:00Z")
        assert check_td0120_selection_reason_trich_ma_tieu_chi(m["iq"], m["dir"]).ok

    def test_mot_luot_chon_lan_hai_sang_2027_bi_tu_choi(self, m) -> None:
        _dr_iq_04(m)
        _chon(m, _to_chon("IQ-0001"), "2026-09-25T10:00:00Z")
        with pytest.raises(IdeaQueueError, match="HAN_NGACH_CHON: 1"):
            _chon(m, _to_chon("IQ-0002"), "2027-01-05T10:00:00Z")

    def test_trich_ma_Q4_sau_diem_cat_bi_tu_choi(self, m) -> None:
        _dr_iq_04(m)
        with pytest.raises(IdeaQueueError, match="TC-Q4-2026-01"):
            _chon(m, _to_chon("IQ-0001", ma="TC-Q4-2026-01"), "2026-09-26T10:00:00Z")


class TestFailClosed:
    def test_chong_ma_khong_khai_cat(self, m) -> None:
        (m["dir"] / "DR-IQ-04-mo-som.md").write_text(
            _khoi("DR-IQ-04", {"tieu_chi": Q1, "tu_ngay": "2026-09-25"}), encoding="utf-8")
        with pytest.raises(TieuChiError, match="nhiều khối"):
            tieu_chi_cho_ngay(m["dir"], date(2026, 9, 26))

    def test_cat_dr_khong_co_khoi(self, m) -> None:
        _dr_iq_04(m, cat_khoi="DR-IQ-77")
        with pytest.raises(TieuChiError, match="không có khối"):
            tieu_chi_cho_ngay(m["dir"], date(2026, 9, 26))

    def test_cat_khoi_khong_chong(self, m) -> None:
        _dr_iq_04(m, tu_ngay="2026-10-02")
        with pytest.raises(TieuChiError, match="không chồng"):
            tieu_chi_cho_ngay(m["dir"], date(2026, 10, 5))

    def test_cat_khoi_khong_phai_chuoi(self, m) -> None:
        _dr_iq_04(m, cat_khoi=["DR-IQ-03"])
        with pytest.raises(TieuChiError, match="hỏng"):
            tieu_chi_cho_ngay(m["dir"], date(2026, 9, 26))


class TestDRThat:
    DIR = REPO_ROOT / "docs/decisions"

    def test_24_09_van_la_Q4_de_IQ_0003_khong_doi_tieu_chi(self) -> None:
        path, nam, quy = tieu_chi_cho_ngay(self.DIR, date(2026, 9, 24))
        assert (path.name, nam, quy) == (Q4, 2026, 4)

    def test_tu_25_09_dung_Q1_2027(self) -> None:
        path, nam, quy = tieu_chi_cho_ngay(self.DIR, date(2026, 9, 25))
        assert (path.name, nam, quy) == (Q1, 2027, 1)

    def test_audit_so_y_tuong_that_van_sach(self) -> None:
        kq = check_td0120_selection_reason_trich_ma_tieu_chi(REPO_ROOT / "registry/idea_queue.jsonl", self.DIR)
        assert kq.ok, kq.evidence

    def test_phien_sach_duoc_chep_dr_iq_04(self) -> None:
        cau_hinh = json.loads((REPO_ROOT / "docs/phien-sach/cau-hinh.json").read_text(encoding="utf-8"))
        assert "docs/decisions/DR-IQ-04-mo-som-cua-chon-q1-2027.md" in cau_hinh["file_chep"]

    def test_dr_iq_04_khong_chua_so_ket_qua_tool_d(self) -> None:
        txt = (self.DIR / "DR-IQ-04-mo-som-cua-chon-q1-2027.md").read_text(encoding="utf-8")
        for cam in ("expectancy", "mean R", "KTC", "FAIL", "time_stop", "INCONCLUSIVE", "IQ-0003"):
            assert cam.lower() not in txt.lower(), cam
        assert not re.search(r"[−+-]?\d+,\d+\s*%?", txt)
