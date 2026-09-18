"""TD-0326 (DR-IQ-02) — sổ ý tưởng là nhật ký sự kiện; cửa CHỌN và cửa HUỶ.

Trước TD-0326 mọi test của cửa CHỌN dựng một dòng SELECTED ĐỨNG MỘT MÌNH —
không test nào đi đường thật (QUEUED rồi SELECTED). Đường thật thì hỏng:
TD-0126 so dòng chọn với chính dòng QUEUED cùng mã ⇒ trùng 100% ⇒ đỏ (MT-65).
Lớp `TestDuongThat` là hồi quy cho đúng chỗ đó.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "entrypoints"))

from tool_d.ledger.audit_checks import (  # noqa: E402
    check_lz17_budget_a_slots_per_quarter,
    check_td0119_selected_du_phep_thu,
    check_td0120_selection_reason_trich_ma_tieu_chi,
    check_td0124_tran_nhap_don_moi_quy,
    check_td0126_explore_evidence_va_trung_mechanism,
    check_td0326_so_y_tuong_nhat_ky_su_kien,
)
from tool_d.ledger.idea_events import duyet_so  # noqa: E402
from tool_d.ledger.idea_queue import IdeaQueueError, chon_y_tuong, huy_chon  # noqa: E402
from trial_ledger_audit import run_audit  # noqa: E402

SCHEMA = REPO_ROOT / "registry/schemas/idea_queue_entry.schema.json"
Q4 = "2026-10-02T09:00:00Z"
Q4_SAU = "2026-10-05T09:00:00Z"


def _don(idea_id: str, mechanism: str = "funding cuc tri keo dai ep long don bay") -> dict:
    return {
        "idea_id": idea_id, "created_at": "2026-09-18T08:00:00Z", "source": "LLM",
        "session_type": "IDEA", "data_source": "MECHANISM", "explore_evidence": None,
        "title": f"y tuong {idea_id}", "mechanism": mechanism,
        "who_pays": "long don bay bi ep tra", "durability": "can chiu rui ro xu huong",
        "phep_thu_du_kien": "so forward R cuc tri voi trung tinh", "filter_verdict": "PASS",
        "overlaps_with": [], "status": "QUEUED", "selected_at": None, "budget_a_slot": None,
        "selection_reason": None, "tin_hieu": None, "quy_tac": None, "nguong_bac_bo": None,
        "so_bien_the": None,
    }


def _to_chon(idea_id: str, **kw) -> dict:
    t = {
        "idea_id": idea_id,
        "selection_reason": "theo TC-Q4-2026-01: co che doc lap voi thanh khoan zone",
        "tin_hieu": "funding >= p90 rolling 90 ngay, 3 ky lien tiep",
        "quy_tac": "short nen 1H ke tiep, SL entry + 2 ATR",
        "nguong_bac_bo": "CI 95% cua d chua 0 thi bac bo",
        "so_bien_the": 2,
    }
    t.update(kw)
    return t


def _ghi(path: Path, dong: list[dict]) -> None:
    path.write_text("".join(json.dumps(d, ensure_ascii=False) + "\n" for d in dong), encoding="utf-8")


def _doc(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


@pytest.fixture()
def moi_truong(tmp_path: Path) -> dict:
    d = tmp_path / "decisions"
    d.mkdir()
    for quy, han in ((3, 0), (4, 1)):
        (d / f"DR-Q{quy}-2026-tieu-chi-chon-y-tuong.md").write_text(
            f"```\nHAN_NGACH_CHON: {han}\n```\n## TC-Q{quy}-2026-01\n## TC-Q{quy}-2026-02\n",
            encoding="utf-8",
        )
    (d / "DR-IQ-02-so-y-tuong.md").write_text("# DR-IQ-02\n", encoding="utf-8")
    reg = tmp_path / "reg.jsonl"
    reg.touch()
    iq = tmp_path / "iq.jsonl"
    _ghi(iq, [_don("IQ-0001")])
    return {"iq": iq, "reg": reg, "dir": d}


def _chon(m: dict, t: dict, bay_gio: str = Q4) -> str:
    return chon_y_tuong(to_chon=t, path=m["iq"], schema_path=SCHEMA, tieu_chi_dir=m["dir"],
                        bay_gio=bay_gio)


def _huy(m: dict, idea_id: str = "IQ-0001", ly_do: str = "DR-IQ-02: chon truoc hieu luc") -> str:
    return huy_chon(idea_id=idea_id, ly_do=ly_do, path=m["iq"], registry_path=m["reg"],
                    decisions_dir=m["dir"], schema_path=SCHEMA, bay_gio=Q4)


def _trial(reg: Path, slot: str) -> None:
    prov = {"params_source": "yaml", "params_effective": {}, "git_sha": "a" * 40,
            "reproducible_from_sha": True, "data_hashes": {}, "cache_mode": "none",
            "guard_passed": True}
    with reg.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "event": "RESERVE", "trial_id": "D-0001", "registered_at": "2026-10-03T10:00:00Z",
            "budget_line": "B1", "hypothesis_slot": slot, "direction": "SHORT",
            "dataset": "CALIB", "param_under_test": "x", "param_value": 1,
            "params_frozen_hash": "f", "config_hash": "c", "code_commit": "a",
            "provenance": prov, "contribution": 1, "tool_id": "D",
        }, ensure_ascii=False) + "\n")


class TestDuongThat:
    def test_queued_roi_selected_chep_nguyen_van_thi_moi_phep_kiem_xanh(self, moi_truong) -> None:
        m = moi_truong
        _chon(m, _to_chon("IQ-0001"))
        dong = _doc(m["iq"])
        assert [d["status"] for d in dong] == ["QUEUED", "SELECTED"]
        assert dong[1]["mechanism"] == dong[0]["mechanism"]
        assert check_td0126_explore_evidence_va_trung_mechanism(m["iq"]).ok, "tự trùng chính mã mình"
        assert check_td0326_so_y_tuong_nhat_ky_su_kien(m["iq"], m["reg"], m["dir"]).ok
        assert check_td0120_selection_reason_trich_ma_tieu_chi(m["iq"], m["dir"]).ok
        assert check_td0119_selected_du_phep_thu(m["iq"]).ok
        assert check_td0124_tran_nhap_don_moi_quy(m["iq"]).ok

    def test_selected_at_la_dong_ho_may(self, moi_truong) -> None:
        _chon(moi_truong, _to_chon("IQ-0001"))
        assert _doc(moi_truong["iq"])[1]["selected_at"] == Q4

    def test_run_audit_goi_td0326(self, moi_truong) -> None:
        m = moi_truong
        _, text = run_audit(registry_path=m["reg"], idea_queue_path=m["iq"], tieu_chi_dir=m["dir"])
        assert "TD-0326" in text


class TestCuaChonTuChoi:
    @pytest.mark.parametrize(
        ("sua", "bay_gio", "chu"),
        [
            ({"selected_at": "2026-10-01T00:00:00Z"}, Q4, "selected_at"),
            ({"voided_at": Q4}, Q4, "không thuộc cửa CHỌN"),
            ({"mechanism": "co che khac han"}, Q4, "trường nộp"),
            ({"quy_tac": ""}, Q4, "cửa CHỌN"),
            ({"selection_reason": "chon vi nghe hop ly"}, Q4, "không trích"),
            ({"selection_reason": "theo TC-Q4-2026-09"}, Q4, "TC-Q4-2026-09"),
            ({}, "2026-08-01T00:00:00Z", "HAN_NGACH_CHON: 0"),
            ({}, "2027-02-01T00:00:00Z", "CHƯA có file tiêu chí"),
        ],
    )
    def test_tu_choi_va_so_khong_bi_dung(self, moi_truong, sua, bay_gio, chu) -> None:
        truoc = moi_truong["iq"].read_bytes()
        with pytest.raises(IdeaQueueError, match=chu):
            _chon(moi_truong, _to_chon("IQ-0001", **sua), bay_gio=bay_gio)
        assert moi_truong["iq"].read_bytes() == truoc

    def test_ma_khong_dang_queued(self, moi_truong) -> None:
        with pytest.raises(IdeaQueueError, match="không có trong sổ"):
            _chon(moi_truong, _to_chon("IQ-0099"))
        _chon(moi_truong, _to_chon("IQ-0001"))
        with pytest.raises(IdeaQueueError, match="đang SELECTED"):
            _chon(moi_truong, _to_chon("IQ-0001"))

    def test_het_han_ngach_quy(self, moi_truong) -> None:
        m = moi_truong
        with m["iq"].open("a", encoding="utf-8") as f:
            f.write(json.dumps(_don("IQ-0002", mechanism="hoan toan khac biet ve y"),
                               ensure_ascii=False) + "\n")
        _chon(m, _to_chon("IQ-0001"))
        with pytest.raises(IdeaQueueError, match="HAN_NGACH_CHON: 1"):
            _chon(m, _to_chon("IQ-0002"), bay_gio=Q4_SAU)


class TestCuaHuy:
    def test_huy_thi_lan_chon_khong_con_tinh_nhung_van_hien(self, moi_truong) -> None:
        m = moi_truong
        _chon(m, _to_chon("IQ-0001"))
        _huy(m)
        dong = _doc(m["iq"])
        assert [d["status"] for d in dong] == ["QUEUED", "SELECTED", "VOIDED"]
        assert dong[2]["selected_at"] == dong[1]["selected_at"]
        assert duyet_so(dong).trang_thai["IQ-0001"] == "QUEUED"
        td0120 = check_td0120_selection_reason_trich_ma_tieu_chi(m["iq"], m["dir"])
        assert td0120.measured.status.name == "PENDING"
        assert "ĐÃ HUỶ" in td0120.evidence
        assert check_td0119_selected_du_phep_thu(m["iq"]).measured.status.name == "PENDING"
        assert check_td0326_so_y_tuong_nhat_ky_su_kien(m["iq"], m["reg"], m["dir"]).ok

    def test_huy_roi_chon_lai_cung_quy_duoc(self, moi_truong) -> None:
        _chon(moi_truong, _to_chon("IQ-0001"))
        _huy(moi_truong)
        _chon(moi_truong, _to_chon("IQ-0001"), bay_gio=Q4_SAU)
        assert check_td0120_selection_reason_trich_ma_tieu_chi(
            moi_truong["iq"], moi_truong["dir"]).ok

    def test_tu_choi_khi_chua_chon(self, moi_truong) -> None:
        with pytest.raises(IdeaQueueError, match="đang QUEUED"):
            _huy(moi_truong)

    def test_tu_choi_khi_da_co_trial_mang_ma(self, moi_truong) -> None:
        _chon(moi_truong, _to_chon("IQ-0001"))
        _trial(moi_truong["reg"], "IQ-0001")
        truoc = moi_truong["iq"].read_bytes()
        with pytest.raises(IdeaQueueError, match="ngân sách N"):
            _huy(moi_truong)
        assert moi_truong["iq"].read_bytes() == truoc

    def test_tu_choi_huy_lan_hai(self, moi_truong) -> None:
        _chon(moi_truong, _to_chon("IQ-0001"))
        _huy(moi_truong)
        _chon(moi_truong, _to_chon("IQ-0001"), bay_gio=Q4_SAU)
        with pytest.raises(IdeaQueueError, match="hết lượt"):
            _huy(moi_truong)

    @pytest.mark.parametrize("ly_do", ["chon nham", "theo DR-KHONG-CO-99"])
    def test_tu_choi_ly_do_khong_trich_dr_co_that(self, moi_truong, ly_do) -> None:
        _chon(moi_truong, _to_chon("IQ-0001"))
        with pytest.raises(IdeaQueueError, match="DR có thật"):
            _huy(moi_truong, ly_do=ly_do)


class TestPhepKiemBatDongThemTay:
    """Sổ thêm tay được — TD-0326 phải bắt các ca mà cửa ghi đã chặn."""

    @staticmethod
    def _chon_tay(don: dict, **kw) -> dict:
        d = dict(don, status="SELECTED", selected_at="2026-10-02T09:00:00Z",
                 selection_reason="theo TC-Q4-2026-01", tin_hieu="a", quy_tac="b",
                 nguong_bac_bo="c", so_bien_the=1)
        d.update(kw)
        return d

    @staticmethod
    def _huy_tay(don: dict, **kw) -> dict:
        d = dict(don, status="VOIDED", selected_at="2026-10-02T09:00:00Z",
                 voided_at="2026-10-03T09:00:00Z", void_reason="DR-IQ-02: chon nham")
        d.update(kw)
        return d

    def _kiem(self, m: dict, dong: list[dict]):
        _ghi(m["iq"], dong)
        return check_td0326_so_y_tuong_nhat_ky_su_kien(m["iq"], m["reg"], m["dir"])

    def test_selected_dung_mot_minh_khong_qua_cua_nop(self, moi_truong) -> None:
        kq = self._kiem(moi_truong, [self._chon_tay(_don("IQ-0001"))])
        assert kq.is_fail and "chưa có dòng nào" in kq.evidence

    def test_selected_doi_truong_nop(self, moi_truong) -> None:
        d = _don("IQ-0001")
        kq = self._kiem(moi_truong, [d, self._chon_tay(d, mechanism="viet lai")])
        assert kq.is_fail and "trường nộp" in kq.evidence

    def test_selected_doi_truong_nop_roi_bi_huy_chi_con_dau_vet(self, moi_truong) -> None:
        """Đúng hình dạng IQ-0002 thật: dòng chọn 18/09 viết lại nội dung, rồi bị huỷ."""
        d = _don("IQ-0001")
        kq = self._kiem(moi_truong, [d, self._chon_tay(d, mechanism="viet lai"), self._huy_tay(d)])
        assert kq.ok, kq.evidence

    def test_voided_khi_da_co_trial(self, moi_truong) -> None:
        d = _don("IQ-0001")
        _trial(moi_truong["reg"], "IQ-0001")
        kq = self._kiem(moi_truong, [d, self._chon_tay(d), self._huy_tay(d)])
        assert kq.is_fail and "ngân sách N" in kq.evidence

    def test_voided_hai_lan(self, moi_truong) -> None:
        d = _don("IQ-0001")
        kq = self._kiem(moi_truong, [
            d, self._chon_tay(d), self._huy_tay(d),
            self._chon_tay(d, selected_at="2026-10-04T09:00:00Z"),
            self._huy_tay(d, selected_at="2026-10-04T09:00:00Z"),
        ])
        assert kq.is_fail and "tối đa" in kq.evidence

    def test_voided_khong_trich_dr(self, moi_truong) -> None:
        d = _don("IQ-0001")
        kq = self._kiem(moi_truong, [d, self._chon_tay(d), self._huy_tay(d, void_reason="nham")])
        assert kq.is_fail and "DR" in kq.evidence

    def test_voided_khong_chi_dich_danh(self, moi_truong) -> None:
        d = _don("IQ-0001")
        kq = self._kiem(moi_truong, [
            d, self._chon_tay(d), self._huy_tay(d, selected_at="2026-10-09T09:00:00Z")])
        assert kq.is_fail and "đích danh" in kq.evidence


class TestHanNgachVaTranNhap:
    def test_hai_lan_chon_hieu_luc_vuot_han_ngach_1(self, moi_truong) -> None:
        m = moi_truong
        a, b = _don("IQ-0001"), _don("IQ-0002", mechanism="hoan toan khac biet ve y")
        chon = TestPhepKiemBatDongThemTay._chon_tay
        _ghi(m["iq"], [a, b, chon(a), chon(b, selected_at="2026-10-03T09:00:00Z")])
        kq = check_td0120_selection_reason_trich_ma_tieu_chi(m["iq"], m["dir"])
        assert kq.is_fail and "HAN_NGACH_CHON: 1" in kq.evidence

    def test_lan_chon_da_huy_khong_tieu_suat_l_z17(self, moi_truong) -> None:
        """6 lần chọn trong quý, 5 đã huỷ ⇒ còn 1 ≤ trần 5. Đếm cả dòng đã huỷ thì 6 > 5."""
        chon, huy = TestPhepKiemBatDongThemTay._chon_tay, TestPhepKiemBatDongThemTay._huy_tay
        dong: list[dict] = []
        for i in range(1, 7):
            d = _don(f"IQ-{i:04d}", mechanism=f"co che {i}")
            dong += [d, chon(d)] + ([huy(d)] if i < 6 else [])
        _ghi(moi_truong["iq"], dong)
        kq = check_lz17_budget_a_slots_per_quarter(moi_truong["iq"])
        assert kq.ok and kq.evidence == "", kq.evidence

    def test_su_kien_chon_huy_khong_tinh_la_don_nop(self, moi_truong) -> None:
        m = moi_truong
        dong = [_don(f"IQ-{i:04d}", mechanism=f"co che so {i} rieng biet {i * 7}") for i in range(1, 11)]
        _ghi(m["iq"], dong)
        _chon(m, _to_chon("IQ-0001"))
        _huy(m)
        assert len(_doc(m["iq"])) == 12
        assert check_td0124_tran_nhap_don_moi_quy(m["iq"]).ok
