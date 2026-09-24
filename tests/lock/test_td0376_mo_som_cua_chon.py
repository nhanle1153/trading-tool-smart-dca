"""🔒 TD-0376 (`DR-IQ-03`) — mở sớm cửa CHỌN: tiêu chí + hạn ngạch `DR-Q4-2026` hiệu lực từ 24/09/2026.

Canh bốn điều, mỗi điều chặn một cách hỏng khác nhau:
1. **Không có khối `MO_SOM` ⇒ hành vi cũ** (chọn cuối quý 3 bị từ chối — đúng thứ `MT-65` đã cắn).
2. **Mở sớm không thành thêm suất:** chọn sớm ăn vào quỹ quý 4, lần chọn thứ hai (kể cả sang quý 4) bị từ chối.
3. **Không lùi hơn `tu_ngay`**, và chỉ mã `TC-Q4` được trích.
4. **Fail-closed:** khối hỏng / trỏ file thiếu / hai khối chồng ⇒ raise, không quay về mặc định trong im lặng.
Cửa CHỌN và audit `TD-0120` đi qua CÙNG `tieu_chi_cho_ngay()` — có ca kiểm cả hai cho cùng một sổ.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from tool_d.ledger.audit_checks import (
    TieuChiError,
    check_td0120_selection_reason_trich_ma_tieu_chi,
    tieu_chi_cho_ngay,
)
from tool_d.ledger.idea_queue import IdeaQueueError, chon_y_tuong

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA = REPO_ROOT / "registry/schemas/idea_queue_entry.schema.json"
SOM = "2026-09-25T09:00:00Z"
TRUOC = "2026-09-23T09:00:00Z"
Q4 = "2026-10-02T09:00:00Z"
KHOI = '<!-- DR-IQ-03:MO_SOM:BEGIN -->\n```json\n{json}\n```\n<!-- DR-IQ-03:MO_SOM:END -->\n'


def _don(idea_id: str, mechanism: str) -> dict:
    return {
        "idea_id": idea_id, "created_at": "2026-09-18T08:00:00Z", "source": "LLM",
        "session_type": "IDEA", "data_source": "MECHANISM", "explore_evidence": None,
        "title": f"y tuong {idea_id}", "mechanism": mechanism,
        "who_pays": "ben thu ba tra", "durability": "can chiu rui ro",
        "phep_thu_du_kien": "so forward R voi trung tinh", "filter_verdict": "PASS",
        "overlaps_with": [], "status": "QUEUED", "selected_at": None, "budget_a_slot": None,
        "selection_reason": None, "tin_hieu": None, "quy_tac": None, "nguong_bac_bo": None,
        "so_bien_the": None,
    }


def _to_chon(idea_id: str, ma: str = "TC-Q4-2026-01") -> dict:
    return {
        "idea_id": idea_id, "selection_reason": f"theo {ma}: co che doc lap",
        "tin_hieu": "tin hieu x", "quy_tac": "quy tac y", "nguong_bac_bo": "CI 95% chua 0 thi bac bo",
        "so_bien_the": 2,
    }


@pytest.fixture()
def m(tmp_path: Path) -> dict:
    d = tmp_path / "decisions"
    d.mkdir()
    for quy, han in ((3, 0), (4, 1)):
        (d / f"DR-Q{quy}-2026-tieu-chi-chon-y-tuong.md").write_text(
            f"```\nHAN_NGACH_CHON: {han}\n```\n## TC-Q{quy}-2026-01\n## TC-Q{quy}-2026-02\n", encoding="utf-8"
        )
    iq = tmp_path / "iq.jsonl"
    iq.write_text(
        "".join(json.dumps(_don(i, f"co che {i} rieng biet hoan toan"), ensure_ascii=False) + "\n"
                for i in ("IQ-0001", "IQ-0002")),
        encoding="utf-8",
    )
    return {"dir": d, "iq": iq}


def _mo_som(m: dict, tu_ngay: str = "2026-09-24", tieu_chi: str = "DR-Q4-2026-tieu-chi-chon-y-tuong.md") -> None:
    (m["dir"] / "DR-IQ-03-mo-som.md").write_text(
        KHOI.format(json=json.dumps({"tieu_chi": tieu_chi, "tu_ngay": tu_ngay})), encoding="utf-8"
    )


def _chon(m: dict, t: dict, bay_gio: str) -> str:
    return chon_y_tuong(to_chon=t, path=m["iq"], schema_path=SCHEMA, tieu_chi_dir=m["dir"], bay_gio=bay_gio)


def _audit(m: dict):
    return check_td0120_selection_reason_trich_ma_tieu_chi(m["iq"], m["dir"])


class TestKhongCoMoSom:
    def test_chon_cuoi_quy_3_bi_tu_choi(self, m) -> None:
        with pytest.raises(IdeaQueueError, match="HAN_NGACH_CHON: 0"):
            _chon(m, _to_chon("IQ-0001"), SOM)

    def test_mac_dinh_tra_quy_lich(self, m) -> None:
        path, nam, quy = tieu_chi_cho_ngay(m["dir"], date(2026, 9, 25))
        assert (path.name, nam, quy) == ("DR-Q3-2026-tieu-chi-chon-y-tuong.md", 2026, 3)


class TestCoMoSom:
    def test_chon_som_ghi_duoc_va_audit_sach(self, m) -> None:
        _mo_som(m)
        _chon(m, _to_chon("IQ-0001"), SOM)
        assert _audit(m).ok

    def test_chon_som_tinh_vao_quy_4(self, m) -> None:
        _mo_som(m)
        path, nam, quy = tieu_chi_cho_ngay(m["dir"], date(2026, 9, 25))
        assert (path.name, nam, quy) == ("DR-Q4-2026-tieu-chi-chon-y-tuong.md", 2026, 4)

    def test_mot_suat_chung_chon_lan_hai_trong_quy_4_bi_tu_choi(self, m) -> None:
        _mo_som(m)
        _chon(m, _to_chon("IQ-0001"), SOM)
        with pytest.raises(IdeaQueueError, match="HAN_NGACH_CHON: 1"):
            _chon(m, _to_chon("IQ-0002"), Q4)

    def test_mot_suat_chung_chon_lan_hai_cung_trong_quy_3_bi_tu_choi(self, m) -> None:
        _mo_som(m)
        _chon(m, _to_chon("IQ-0001"), SOM)
        with pytest.raises(IdeaQueueError, match="HAN_NGACH_CHON: 1"):
            _chon(m, _to_chon("IQ-0002"), "2026-09-28T09:00:00Z")

    def test_audit_bat_hai_lan_chon_du_ghi_vong_qua_cua(self, m) -> None:
        """Ghi TAY dòng thứ hai (vòng qua cửa, như MT-65): audit vẫn phải đếm hai lần vào CÙNG quỹ quý 4."""
        _mo_som(m)
        _chon(m, _to_chon("IQ-0001"), SOM)
        dong = json.loads(m["iq"].read_text(encoding="utf-8").splitlines()[-1])
        dong2 = {**_don("IQ-0002", "co che IQ-0002 rieng biet hoan toan"), "status": "SELECTED",
                 "selected_at": Q4, "selection_reason": "theo TC-Q4-2026-02: x", "tin_hieu": "a",
                 "quy_tac": "b", "nguong_bac_bo": "c", "so_bien_the": 1, "budget_a_slot": dong.get("budget_a_slot")}
        with m["iq"].open("a", encoding="utf-8") as f:
            f.write(json.dumps(dong2, ensure_ascii=False) + "\n")
        kq = _audit(m)
        assert not kq.ok and "lần chọn thứ 2" in kq.evidence

    def test_truoc_tu_ngay_van_la_quy_3(self, m) -> None:
        _mo_som(m)
        with pytest.raises(IdeaQueueError, match="HAN_NGACH_CHON: 0"):
            _chon(m, _to_chon("IQ-0001"), TRUOC)

    def test_trich_ma_Q3_bi_tu_choi(self, m) -> None:
        _mo_som(m)
        with pytest.raises(IdeaQueueError, match="TC-Q3-2026-01"):
            _chon(m, _to_chon("IQ-0001", ma="TC-Q3-2026-01"), SOM)

    def test_ngay_trong_quy_4_khong_bi_khoi_mo_som_anh_huong(self, m) -> None:
        _mo_som(m)
        path, nam, quy = tieu_chi_cho_ngay(m["dir"], date(2026, 10, 2))
        assert (path.name, nam, quy) == ("DR-Q4-2026-tieu-chi-chon-y-tuong.md", 2026, 4)


class TestFailClosed:
    def test_khoi_hong(self, m) -> None:
        (m["dir"] / "DR-IQ-03-mo-som.md").write_text(KHOI.format(json="{khong phai json"), encoding="utf-8")
        with pytest.raises(TieuChiError, match="hỏng"):
            tieu_chi_cho_ngay(m["dir"], date(2026, 9, 25))

    def test_tro_file_khong_ton_tai(self, m) -> None:
        _mo_som(m, tieu_chi="DR-Q1-2027-tieu-chi-chon-y-tuong.md")
        with pytest.raises(TieuChiError, match="không tồn tại"):
            tieu_chi_cho_ngay(m["dir"], date(2026, 9, 25))

    def test_tu_ngay_khong_truoc_dau_quy(self, m) -> None:
        _mo_som(m, tu_ngay="2026-10-05")
        with pytest.raises(TieuChiError, match="không đứng TRƯỚC"):
            tieu_chi_cho_ngay(m["dir"], date(2026, 9, 25))

    def test_hai_khoi_cung_phu_mot_ngay(self, m) -> None:
        _mo_som(m)
        (m["dir"] / "DR-IQ-99-trung.md").write_text(
            KHOI.replace("DR-IQ-03", "DR-IQ-99").format(
                json=json.dumps({"tieu_chi": "DR-Q4-2026-tieu-chi-chon-y-tuong.md", "tu_ngay": "2026-09-20"})
            ),
            encoding="utf-8",
        )
        with pytest.raises(TieuChiError, match="nhiều khối"):
            tieu_chi_cho_ngay(m["dir"], date(2026, 9, 25))

    def test_cua_chon_doi_loi_thanh_tu_choi(self, m) -> None:
        (m["dir"] / "DR-IQ-03-mo-som.md").write_text(KHOI.format(json="{hong"), encoding="utf-8")
        with pytest.raises(IdeaQueueError, match="TỪ CHỐI"):
            _chon(m, _to_chon("IQ-0001"), SOM)


class TestDRThat:
    """Trên `docs/decisions/` THẬT: `DR-IQ-03` đọc được và làm đúng việc nó khai."""

    DIR = REPO_ROOT / "docs/decisions"

    def test_25_09_dung_tieu_chi_Q4_quy_4(self) -> None:
        path, nam, quy = tieu_chi_cho_ngay(self.DIR, date(2026, 9, 25))
        assert (path.name, nam, quy) == ("DR-Q4-2026-tieu-chi-chon-y-tuong.md", 2026, 4)

    def test_23_09_van_la_quy_3(self) -> None:
        path, _, quy = tieu_chi_cho_ngay(self.DIR, date(2026, 9, 23))
        assert (path.name, quy) == ("DR-Q3-2026-tieu-chi-chon-y-tuong.md", 3)

    def test_dr_iq_03_khong_chua_so_ket_qua_tool_d(self) -> None:
        """Phiên IDEA sạch phải đọc được DR-IQ-03 (DR-009): không số R, không kết cục ablation/DSR."""
        import re

        txt = (self.DIR / "DR-IQ-03-mo-som-cua-chon-q4-2026.md").read_text(encoding="utf-8")
        # Tên khái niệm ("rào DSR", "N = 114") được phép — đó là luật, không phải kết quả. Cấm KẾT QUẢ: tên arm,
        # thước kết quả, kết cục, và số thập phân kiểu kết quả đo (−0,22 / 0,43% / +0,0035).
        for cam in ("expectancy", "mean R", "KTC", "FAIL", "Z0-T1", "time_stop", "INCONCLUSIVE"):
            assert cam.lower() not in txt.lower(), cam
        assert not re.search(r"[−+-]?\d+,\d+\s*%?", txt), re.search(r"[−+-]?\d+,\d+\s*%?", txt)
