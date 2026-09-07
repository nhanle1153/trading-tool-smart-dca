"""TD-0124 — công cụ nộp đơn ý tưởng: cửa GHI của `idea_queue.jsonl`.

Sổ là append-only TUYỆT ĐỐI, không có đường lùi. Vì vậy phép kiểm nào cũng
phải chạy TRƯỚC khi mở file, và bằng chứng "đã từ chối" không phải là một
exception — mà là **file không dài thêm một dòng nào**. Test nào cũng
assert cả hai.

Kèm trần NHẬP 10 đơn/quý (spec dòng 4095) — điều MT-11 ghi là "mới là văn
bản; chưa code". Trần này chặn ở NGUỒN, và chặn CỨNG (khác trần CHỌN
L-Z17 đã được MT-11 nới thành cảnh báo): chi phí sinh ý tưởng bằng LLM xấp
xỉ 0, nên tỉ lệ chọn thấp biến bước CHỌN thành nơi khai thác dữ liệu quy mô
lớn — và bước chọn thì không ai ghi sổ cho.
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
    check_lz17_budget_a_slots_per_quarter,
    check_td0120_selection_reason_trich_ma_tieu_chi,
    check_td0124_tran_nhap_don_moi_quy,
)
from tool_d.ledger.idea_queue import (  # noqa: E402
    IDEA_QUEUE_INTAKE_PER_QUARTER_MAX,
    IdeaQueueError,
    next_idea_id,
    submit_idea,
)
from trial_ledger_audit import EXIT_AUDIT_FAILED, run_audit  # noqa: E402

SCHEMA = REPO_ROOT / "registry/schemas/idea_queue_entry.schema.json"


def _don(**doi) -> dict:
    """Tờ đơn hợp lệ tối thiểu ở cửa NỘP — 3 câu §0.1 + phác thảo phép thử."""
    d = {
        "source": "LLM",
        "data_source": "MECHANISM",
        "title": "hap thu lenh o vung thanh khoan cu",
        "mechanism": "quy phong ho bat buoc dong vi the o vung gia cu",
        "who_pays": "ben bat buoc phong ho theo chi so, khong duoc chon gia",
        "durability": "rang buoc uy thac, khong the arbitrage het",
        "phep_thu_du_kien": "so ky vong khi co tin hieu voi khi khong co, cung tap",
        "filter_verdict": "PASS",
        "status": "QUEUED",
    }
    d.update(doi)
    return d


def _so_dong(path: Path) -> int:
    if not path.exists():
        return 0
    return len([x for x in path.read_text(encoding="utf-8").splitlines() if x.strip()])


def _nop(path: Path, **doi) -> str:
    return submit_idea(don=_don(**doi), path=path, schema_path=SCHEMA)


@pytest.fixture
def so(tmp_path: Path) -> Path:
    return tmp_path / "idea_queue.jsonl"


class TestGhiHopLe:
    def test_ghi_duoc_mot_dong_du_20_khoa(self, so: Path) -> None:
        idea_id = _nop(so)
        assert idea_id == "IQ-0001"
        assert _so_dong(so) == 1

        dong = json.loads(so.read_text(encoding="utf-8").splitlines()[0])
        khoa_bat_buoc = set(json.loads(SCHEMA.read_text(encoding="utf-8"))["required"])
        assert khoa_bat_buoc <= set(dong), "dòng ghi ra thiếu khoá required của schema"
        assert dong["session_type"] == "IDEA"
        assert dong["overlaps_with"] == []
        # Các trường của cửa CHỌN phải là null, không phải chuỗi rỗng.
        for f in ("tin_hieu", "quy_tac", "nguong_bac_bo", "so_bien_the", "selected_at"):
            assert dong[f] is None

    def test_audit_van_sach_sau_khi_nop(self, so: Path, tmp_path: Path) -> None:
        _nop(so)
        reg = tmp_path / "reg.jsonl"
        reg.touch()
        exit_code, text = run_audit(registry_path=reg, idea_queue_path=so)
        assert exit_code == 0, text

    def test_created_at_dung_dinh_dang_hai_phep_kiem_kia_doc_duoc(self, so: Path) -> None:
        """🔴 Cạm bẫy micro giây: `registry._utcnow_iso()` ghi micro giây, còn
        `check_lz17`/`check_td0120` đọc bằng strptime CHỈ tới giây. Dùng nhầm
        hàm kia làm hai phép kiểm CRASH ValueError — audit chết giữa chừng
        chứ không fail sạch."""
        _nop(so)
        # Không raise là điều kiện phải giữ; giá trị trả về không quan trọng ở đây.
        check_lz17_budget_a_slots_per_quarter(so)
        check_td0120_selection_reason_trich_ma_tieu_chi(so, REPO_ROOT / "docs/decisions")


class TestSauCaTuChoi:
    """Mỗi ca: raise VÀ file không dài thêm."""

    @pytest.mark.parametrize(
        "doi",
        [
            {"source": "KHONG_CO_THAT"},  # sai enum
            {"filter_verdict": "CHAC_LA_ON"},  # sai enum
            {"title": ""},  # minLength
            {"session_type": "TUNE"},  # const
            {"khoa_la_hoac": 1},  # additionalProperties: false
        ],
        ids=["source", "filter_verdict", "title-rong", "session_type", "khoa-thua"],
    )
    def test_ca1_sai_schema(self, so: Path, doi: dict) -> None:
        with pytest.raises(IdeaQueueError):
            _nop(so, **doi)
        assert _so_dong(so) == 0

    def test_ca2_cua_nop_khong_ghi_duoc_selected(self, so: Path) -> None:
        """Tách vật lý hai cửa: một lần nộp đơn không được vô tình thành một
        lần CHỌN (1 lần/quý, quý 3/2026 hạn ngạch 0)."""
        with pytest.raises(IdeaQueueError, match="cửa NỘP"):
            _nop(so, status="SELECTED")
        assert _so_dong(so) == 0

    def test_ca2_archived_cung_bi_tu_choi(self, so: Path) -> None:
        with pytest.raises(IdeaQueueError):
            _nop(so, status="ARCHIVED")
        assert _so_dong(so) == 0

    def test_ca3_tool_d_results_ma_khong_rejected(self, so: Path) -> None:
        with pytest.raises(IdeaQueueError, match="L-Z16"):
            _nop(so, data_source="TOOL_D_RESULTS", status="QUEUED")
        assert _so_dong(so) == 0

    def test_ca3_tool_d_results_rejected_thi_ghi_duoc(self, so: Path) -> None:
        """Ghi lại để khỏi nghĩ lại lần nữa — được; chạy nó — không."""
        _nop(so, data_source="TOOL_D_RESULTS", status="REJECTED")
        assert _so_dong(so) == 1

    def test_ca4_don_thu_11_cung_quy_bi_tu_choi(self, so: Path) -> None:
        for i in range(IDEA_QUEUE_INTAKE_PER_QUARTER_MAX):
            _nop(so, created_at=f"2026-07-{i + 1:02d}T00:00:00Z")
        assert _so_dong(so) == IDEA_QUEUE_INTAKE_PER_QUARTER_MAX

        with pytest.raises(IdeaQueueError, match="trần NHẬP"):
            _nop(so, created_at="2026-08-01T00:00:00Z")  # vẫn quý 3
        assert _so_dong(so) == IDEA_QUEUE_INTAKE_PER_QUARTER_MAX, "đơn thứ 11 vẫn lọt vào sổ"

    def test_ca4_quy_sau_thi_ghi_duoc(self, so: Path) -> None:
        for i in range(IDEA_QUEUE_INTAKE_PER_QUARTER_MAX):
            _nop(so, created_at=f"2026-07-{i + 1:02d}T00:00:00Z")
        _nop(so, created_at="2026-10-01T00:00:00Z")  # quý 4
        assert _so_dong(so) == IDEA_QUEUE_INTAKE_PER_QUARTER_MAX + 1

    def test_ca4_don_rejected_van_tinh_vao_tran_nhap(self, so: Path) -> None:
        """Trần chặn ở NGUỒN: một đơn bị bộ lọc loại vẫn đã tiêu công sinh
        và công đọc của quý đó."""
        for i in range(IDEA_QUEUE_INTAKE_PER_QUARTER_MAX):
            _nop(so, created_at=f"2026-07-{i + 1:02d}T00:00:00Z", status="REJECTED")
        with pytest.raises(IdeaQueueError, match="trần NHẬP"):
            _nop(so, created_at="2026-09-30T00:00:00Z")

    def test_ca5_trung_idea_id(self, so: Path) -> None:
        _nop(so, idea_id="IQ-0042")
        with pytest.raises(IdeaQueueError, match="đã có trong sổ"):
            _nop(so, idea_id="IQ-0042")
        assert _so_dong(so) == 1

    @pytest.mark.parametrize("thieu", ["mechanism", "who_pays", "durability"])
    def test_ca6_thieu_cau_bo_loc(self, so: Path, thieu: str) -> None:
        with pytest.raises(IdeaQueueError, match="§0.1"):
            _nop(so, **{thieu: "   "})
        assert _so_dong(so) == 0

    @pytest.mark.parametrize("thieu", ["mechanism", "who_pays", "durability"])
    def test_ca6_tra_loi_n_a_khong_tinh_la_tra_loi(self, so: Path, thieu: str) -> None:
        with pytest.raises(IdeaQueueError):
            _nop(so, **{thieu: "n/a"})
        assert _so_dong(so) == 0


class TestNextIdeaId:
    def test_so_rong(self, so: Path) -> None:
        assert next_idea_id(so) == "IQ-0001"

    def test_lay_max_khong_phai_dem_dong(self, so: Path) -> None:
        """Đếm số dòng sẽ sinh id TRÙNG nếu sổ có dòng mang id tự đặt."""
        _nop(so, idea_id="IQ-0007")
        assert next_idea_id(so) == "IQ-0008"
        assert _nop(so) == "IQ-0008"
        assert next_idea_id(so) == "IQ-0009"


class TestPhepKiemAuditCanhSoDaGhi:
    """Cửa ghi không phải đường DUY NHẤT tới file — sổ vẫn sửa tay được."""

    @staticmethod
    def _ghi_tay(path: Path, n: int, thang: str = "07") -> None:
        with path.open("a", encoding="utf-8") as f:
            for i in range(n):
                d = _don(idea_id=f"IQ-{i + 1:04d}", created_at=f"2026-{thang}-01T00:00:00Z")
                d.update(
                    {
                        "session_type": "IDEA",
                        "overlaps_with": [],
                        "explore_evidence": None,
                        "selected_at": None,
                        "budget_a_slot": None,
                        "selection_reason": None,
                        "tin_hieu": None,
                        "quy_tac": None,
                        "nguong_bac_bo": None,
                        "so_bien_the": None,
                    }
                )
                f.write(json.dumps(d, ensure_ascii=False) + "\n")

    def test_so_rong_thi_chua_do_duoc(self, so: Path) -> None:
        so.touch()
        assert check_td0124_tran_nhap_don_moi_quy(so).measured.status.name == "PENDING"

    def test_dung_tran_thi_dat(self, so: Path) -> None:
        self._ghi_tay(so, IDEA_QUEUE_INTAKE_PER_QUARTER_MAX)
        assert check_td0124_tran_nhap_don_moi_quy(so).ok is True

    def test_vuot_tran_do_sua_tay_thi_so_ban(self, so: Path, tmp_path: Path) -> None:
        self._ghi_tay(so, IDEA_QUEUE_INTAKE_PER_QUARTER_MAX + 1)
        ket_qua = check_td0124_tran_nhap_don_moi_quy(so)
        assert ket_qua.is_fail is True
        assert "trần NHẬP" in ket_qua.evidence

        reg = tmp_path / "reg.jsonl"
        reg.touch()
        exit_code, text = run_audit(registry_path=reg, idea_queue_path=so)
        assert exit_code == EXIT_AUDIT_FAILED, text
        assert "TD-0124" in text

    def test_tran_nhap_CHAN_CUNG_khong_phai_canh_bao(self) -> None:
        """Khác L-Z17 (trần CHỌN, MT-11 nới thành cảnh báo). Nếu ai đó về sau
        đưa TD-0124 vào WARN_ONLY_CODES thì test này phải đỏ."""
        assert "TD-0124" not in WARN_ONLY_CODES
        assert WARN_ONLY_CODES == frozenset({"L-Z17"})
