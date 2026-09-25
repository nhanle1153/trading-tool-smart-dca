"""🔒 TD-0430 (`MT-89`) — máy kiểm độ mạnh thống kê ở cửa CHỌN.

Canh:
1. **Số học:** máy tính `Φ(μ·√n/σ − h)` với `h = dsr_hurdle(N_DANG_KY)` — không chép `N`/`h`; biên `μ = h·σ/√n` ⇒ 0,5.
2. **Fail-closed:** quý khai `DO_MANH_TOI_THIEU` mà tờ chọn thiếu `do_manh`, thiếu khoá, số hỏng, hoặc xác suất MÁY TÍNH
   dưới ngưỡng ⇒ `IdeaQueueError`, sổ không đổi một byte. Số tự khai (`xac_suat_khai`) không cứu được tờ chọn.
3. **Quý không khai ngưỡng** ⇒ hành vi cũ, không đòi `do_manh`.
4. **Audit `TD-0120` ca (f)** bắt dòng lọt cửa (ghi tay) — cùng hàm với cửa.
5. **Trên đĩa THẬT:** `DR-Q1-2027` khai đúng một ngưỡng; sổ ý tưởng thật vẫn sạch; code không chép con số ngưỡng.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

import pytest

from tool_d.gates import do_manh_chon
from tool_d.gates.do_manh_chon import kiem_do_manh, xac_suat_phat_hien
from tool_d.gates.dsr import N_DANG_KY, dsr_hurdle
from tool_d.ledger.audit_checks import check_td0120_selection_reason_trich_ma_tieu_chi
from tool_d.ledger.idea_queue import IdeaQueueError, chon_y_tuong

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA = REPO_ROOT / "registry/schemas/idea_queue_entry.schema.json"
TIEU_CHI_DOI = "```\nHAN_NGACH_CHON: 1\nDO_MANH_TOI_THIEU: 0.50\n```\n## TC-Q1-2027-00\n## TC-Q1-2027-01\n"
H = dsr_hurdle(N_DANG_KY)


def _mu_bien(sigma: float = 1.0, n: int = 100) -> float:
    return H * sigma / math.sqrt(n)


def _do_manh(**sua) -> dict:
    return {"don_vi": "loi suat ngay", "sigma": 1.0, "n_lockbox": 100, "mu": 0.5,
            "nguon_sigma": "du lieu tho EXPLORE", **sua}


def _don(idea_id: str) -> dict:
    return {
        "idea_id": idea_id, "created_at": "2026-12-18T08:00:00Z", "source": "LLM",
        "session_type": "IDEA", "data_source": "MECHANISM", "explore_evidence": None,
        "title": f"y tuong {idea_id}", "mechanism": f"co che {idea_id} rieng biet hoan toan",
        "who_pays": "ben thu ba tra", "durability": "can chiu rui ro",
        "phep_thu_du_kien": "so forward voi trung tinh", "filter_verdict": "PASS",
        "overlaps_with": [], "status": "QUEUED", "selected_at": None, "budget_a_slot": None,
        "selection_reason": None, "tin_hieu": None, "quy_tac": None, "nguong_bac_bo": None,
        "so_bien_the": None,
    }


def _to_chon(idea_id: str, ma: str = "TC-Q1-2027-00", do_manh: dict | None = None) -> dict:
    t = {"idea_id": idea_id, "selection_reason": f"theo {ma}: co che doc lap", "tin_hieu": "x", "quy_tac": "y",
         "nguong_bac_bo": "CI 95% chua 0 thi bac bo", "so_bien_the": 1}
    if do_manh is not None:
        t["do_manh"] = do_manh
    return t


@pytest.fixture()
def m(tmp_path: Path) -> dict:
    d = tmp_path / "decisions"
    d.mkdir()
    (d / "DR-Q1-2027-tieu-chi-chon-y-tuong.md").write_text(TIEU_CHI_DOI, encoding="utf-8")
    (d / "DR-Q2-2027-tieu-chi-chon-y-tuong.md").write_text(
        "```\nHAN_NGACH_CHON: 1\n```\n## TC-Q2-2027-01\n", encoding="utf-8")
    iq = tmp_path / "iq.jsonl"
    iq.write_text("".join(json.dumps(_don(i)) + "\n" for i in ("IQ-0001", "IQ-0002")), encoding="utf-8")
    return {"dir": d, "iq": iq}


def _chon(m: dict, t: dict, bay_gio: str = "2027-01-10T10:00:00Z") -> str:
    return chon_y_tuong(to_chon=t, path=m["iq"], schema_path=SCHEMA, tieu_chi_dir=m["dir"], bay_gio=bay_gio)


class TestSoHoc:
    def test_h_la_rao_dsr_cua_du_an(self) -> None:
        z = 0.5 * math.sqrt(100) / 1.0 - dsr_hurdle(N_DANG_KY)
        assert xac_suat_phat_hien(mu=0.5, sigma=1.0, n=100) == pytest.approx(0.5 * (1 + math.erf(z / math.sqrt(2))))

    def test_bien_mu_bang_h_sigma_chia_can_n_la_mot_nua(self) -> None:
        assert xac_suat_phat_hien(mu=_mu_bien(), sigma=1.0, n=100) == pytest.approx(0.5, abs=1e-12)

    @pytest.mark.parametrize("sigma, n", [(0.0, 10), (-1.0, 10), (1.0, 0)])
    def test_dau_vao_hong_raise_khong_tra_linh_canh(self, sigma: float, n: int) -> None:
        with pytest.raises(ValueError):
            xac_suat_phat_hien(mu=1.0, sigma=sigma, n=n)


class TestKiemDoManh:
    def test_quy_khong_khai_nguong_khong_doi(self) -> None:
        assert kiem_do_manh(None, "HAN_NGACH_CHON: 1\n") == []

    def test_tren_bien_qua_duoi_bien_truot(self) -> None:
        assert kiem_do_manh(_do_manh(mu=_mu_bien() * (1 + 1e-9)), TIEU_CHI_DOI) == []
        loi = kiem_do_manh(_do_manh(mu=_mu_bien() * (1 - 1e-6)), TIEU_CHI_DOI)
        assert len(loi) == 1 and "xác suất phát hiện máy tính" in loi[0]

    def test_so_tu_khai_khong_cuu_duoc(self) -> None:
        loi = kiem_do_manh(_do_manh(mu=0.1, xac_suat_khai=0.99), TIEU_CHI_DOI)
        assert len(loi) == 1 and "0.99" in loi[0] and "máy không dùng" in loi[0]

    def test_loi_tu_choi_neu_mu_can_co(self) -> None:
        loi = kiem_do_manh(_do_manh(mu=0.1), TIEU_CHI_DOI)
        assert f"{_mu_bien():.6g}" in loi[0]

    @pytest.mark.parametrize("do_manh, khop", [
        (None, "không có khối do_manh"),
        ("sigma=1", "không có khối do_manh"),
        ({k: v for k, v in _do_manh().items() if k != "sigma"}, "thiếu sigma"),
        (_do_manh(don_vi="  "), "don_vi"),
        (_do_manh(sigma=0.0), "sigma phải > 0"),
        (_do_manh(sigma=-1.0), "sigma phải > 0"),
        (_do_manh(sigma=float("nan")), "sigma phải là số hữu hạn"),
        (_do_manh(mu=float("inf")), "mu phải là số hữu hạn"),
        (_do_manh(mu=True), "mu phải là số hữu hạn"),
        (_do_manh(mu="0.5"), "mu phải là số hữu hạn"),
        (_do_manh(n_lockbox=0), "n_lockbox"),
        (_do_manh(n_lockbox=100.0), "n_lockbox"),
        (_do_manh(n_lockbox=True), "n_lockbox"),
    ])
    def test_fail_closed(self, do_manh, khop: str) -> None:
        loi = kiem_do_manh(do_manh, TIEU_CHI_DOI)
        assert any(khop in x for x in loi), loi

    @pytest.mark.parametrize("dong", [
        "DO_MANH_TOI_THIEU: 0.5\nDO_MANH_TOI_THIEU: 0.6\n",
        "DO_MANH_TOI_THIEU: abc\n",
        "DO_MANH_TOI_THIEU: 1.5\n",
        "DO_MANH_TOI_THIEU: 0\n",
    ])
    def test_nguong_hong_la_vi_pham(self, dong: str) -> None:
        assert kiem_do_manh(_do_manh(), dong) != []


class TestCuaChon:
    @pytest.mark.parametrize("do_manh, khop", [
        (None, "không có khối do_manh"),
        (_do_manh(mu=0.1), "xác suất phát hiện máy tính"),
        (_do_manh(sigma=0.0), "sigma phải > 0"),
    ])
    def test_tu_choi_so_khong_doi_byte(self, m, do_manh, khop: str) -> None:
        truoc = m["iq"].read_bytes()
        with pytest.raises(IdeaQueueError, match=khop):
            _chon(m, _to_chon("IQ-0001", do_manh=do_manh))
        assert m["iq"].read_bytes() == truoc

    @pytest.mark.parametrize("do_manh", [
        {**_do_manh(), "khoa_la": 1},
        {k: v for k, v in _do_manh().items() if k != "nguon_sigma"},
    ])
    def test_schema_chan_khoi_do_manh_sai_hinh(self, m, do_manh) -> None:
        truoc = m["iq"].read_bytes()
        with pytest.raises(IdeaQueueError, match="schema"):
            _chon(m, _to_chon("IQ-0001", do_manh=do_manh))
        assert m["iq"].read_bytes() == truoc

    def test_du_manh_ghi_duoc_dong_mang_do_manh_audit_sach(self, m) -> None:
        _chon(m, _to_chon("IQ-0001", do_manh=_do_manh()))
        dong = json.loads(m["iq"].read_text(encoding="utf-8").splitlines()[-1])
        assert dong["status"] == "SELECTED" and dong["do_manh"] == _do_manh()
        assert check_td0120_selection_reason_trich_ma_tieu_chi(m["iq"], m["dir"]).ok

    def test_quy_khong_khai_nguong_giu_hanh_vi_cu(self, m) -> None:
        _chon(m, _to_chon("IQ-0001", ma="TC-Q2-2027-01"), bay_gio="2027-04-10T10:00:00Z")
        dong = json.loads(m["iq"].read_text(encoding="utf-8").splitlines()[-1])
        assert dong["status"] == "SELECTED" and "do_manh" not in dong


class TestAudit:
    def test_ca_f_bat_dong_ghi_tay_lot_cua(self, m) -> None:
        e = {**_don("IQ-0001"), "status": "SELECTED", "selected_at": "2027-01-10T10:00:00Z",
             **{k: v for k, v in _to_chon("IQ-0001").items() if k != "idea_id"}}
        with m["iq"].open("a", encoding="utf-8") as f:
            f.write(json.dumps(e) + "\n")
        kq = check_td0120_selection_reason_trich_ma_tieu_chi(m["iq"], m["dir"])
        assert not kq.ok and "IQ-0001" in kq.evidence and "do_manh" in kq.evidence


class TestDiaThat:
    DIR = REPO_ROOT / "docs/decisions"

    def test_dr_q1_2027_khai_dung_mot_nguong_trong_khoang(self) -> None:
        txt = (self.DIR / "DR-Q1-2027-tieu-chi-chon-y-tuong.md").read_text(encoding="utf-8")
        khai = do_manh_chon.DO_MANH_RE.findall(txt)
        assert len(khai) == 1 and 0 < float(khai[0]) < 1
        assert kiem_do_manh(None, txt) != []

    def test_so_y_tuong_that_van_sach(self) -> None:
        kq = check_td0120_selection_reason_trich_ma_tieu_chi(REPO_ROOT / "registry/idea_queue.jsonl", self.DIR)
        assert kq.ok, kq.evidence

    @pytest.mark.parametrize("rel", ["src/tool_d/gates/do_manh_chon.py", "src/tool_d/ledger/idea_queue.py"])
    def test_code_khong_chep_nguong(self, rel: str) -> None:
        # Bài học TD-0315: con số của MỘT quý chép vào code sẽ ở lại khi quý đổi.
        assert not re.search(r"(?<![\d.])0[.,]5(0)?(?![\d])", (REPO_ROOT / rel).read_text(encoding="utf-8"))
