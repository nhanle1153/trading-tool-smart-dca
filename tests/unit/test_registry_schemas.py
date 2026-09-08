"""TD-0050 — schema JSON cho trial_registry.jsonl (sổ sự kiện, MT-01) và
idea_queue.jsonl. Validate fixture mẫu cho đủ 5 loại sự kiện + 3 dòng
idea_queue tiêu biểu (QUEUED/SELECTED/REJECTED-vì-TOOL_D_RESULTS).
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TRIAL_EVENT_SCHEMA = json.loads(
    (REPO_ROOT / "registry/schemas/trial_event.schema.json").read_text(encoding="utf-8")
)
IDEA_QUEUE_SCHEMA = json.loads(
    (REPO_ROOT / "registry/schemas/idea_queue_entry.schema.json").read_text(encoding="utf-8")
)


def _load_jsonl(path: Path) -> list[dict]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


class TestTrialEventFixtureHopLe:
    def test_du_5_loai_su_kien(self) -> None:
        events = _load_jsonl(REPO_ROOT / "tests/fixtures/trial_events_valid.jsonl")
        kinds = {e["event"] for e in events}
        assert kinds == {"RESERVE", "SEAL", "CONSUME", "REFUND", "CONTAMINATE"}

    def test_moi_dong_hop_le_theo_schema(self) -> None:
        events = _load_jsonl(REPO_ROOT / "tests/fixtures/trial_events_valid.jsonl")
        for e in events:
            jsonschema.validate(e, TRIAL_EVENT_SCHEMA)

    def test_hai_su_kien_cung_trial_id_gop_lai_thanh_1_trial(self) -> None:
        # D-0001 có 3 sự kiện (RESERVE, SEAL, CONSUME) + 1 CONTAMINATE sau đó.
        events = _load_jsonl(REPO_ROOT / "tests/fixtures/trial_events_valid.jsonl")
        d0001 = [e for e in events if e["trial_id"] == "D-0001"]
        assert len(d0001) == 4
        assert [e["event"] for e in d0001] == ["RESERVE", "SEAL", "CONSUME", "CONTAMINATE"]


class TestTrialEventSchemaCoRang:
    def test_thieu_khoa_bat_buoc_thi_khong_hop_le(self) -> None:
        bad = {"event": "RESERVE", "trial_id": "D-0001"}  # thiếu gần hết
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(bad, TRIAL_EVENT_SCHEMA)

    def test_event_khong_thuoc_5_loai_thi_khong_hop_le(self) -> None:
        bad = {"event": "DELETE", "trial_id": "D-0001"}
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(bad, TRIAL_EVENT_SCHEMA)

    def test_refund_thieu_refund_cause_machine_thi_khong_hop_le(self) -> None:
        bad = {"event": "REFUND", "trial_id": "D-0001", "refunded_at": "2026-09-06T10:00:00Z"}
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(bad, TRIAL_EVENT_SCHEMA)

    def test_provenance_thieu_1_khoa_thi_reserve_khong_hop_le(self) -> None:
        good = json.loads(
            (REPO_ROOT / "tests/fixtures/trial_events_valid.jsonl").read_text().splitlines()[0]
        )
        del good["provenance"]["guard_passed"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(good, TRIAL_EVENT_SCHEMA)

    def test_trial_id_sai_dinh_dang_thi_khong_hop_le(self) -> None:
        bad = {
            "event": "SEAL",
            "trial_id": "khong-dung-dinh-dang",
            "sealed_at": "2026-09-06T10:00:00Z",
            "seal_path": "runs/x/metrics.seal",
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(bad, TRIAL_EVENT_SCHEMA)


class TestIdeaQueueFixtureHopLe:
    def test_moi_dong_hop_le_theo_schema(self) -> None:
        entries = _load_jsonl(REPO_ROOT / "tests/fixtures/idea_queue_valid.jsonl")
        assert len(entries) == 3
        for e in entries:
            jsonschema.validate(e, IDEA_QUEUE_SCHEMA)

    def test_co_du_cac_trang_thai_tieu_bieu(self) -> None:
        entries = _load_jsonl(REPO_ROOT / "tests/fixtures/idea_queue_valid.jsonl")
        statuses = {e["status"] for e in entries}
        assert statuses == {"QUEUED", "SELECTED", "REJECTED"}


class TestIdeaQueueSchemaCoRang:
    def test_session_type_khac_idea_thi_khong_hop_le(self) -> None:
        entries = _load_jsonl(REPO_ROOT / "tests/fixtures/idea_queue_valid.jsonl")
        bad = dict(entries[0])
        bad["session_type"] = "OTHER"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(bad, IDEA_QUEUE_SCHEMA)

    def test_data_source_khong_thuoc_3_gia_tri_thi_khong_hop_le(self) -> None:
        entries = _load_jsonl(REPO_ROOT / "tests/fixtures/idea_queue_valid.jsonl")
        bad = dict(entries[0])
        bad["data_source"] = "GUESS"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(bad, IDEA_QUEUE_SCHEMA)


class TestFileRegistryThatHopLe:
    """Từ TD-0083 (chốt pool), `trial_registry.jsonl` KHÔNG còn rỗng — 4
    trial B0 thật đã ghi vào đó. `idea_queue.jsonl` vẫn rỗng (chưa mở
    Idea Queue, OQ-07 chưa chốt tiêu chí chọn). Kiểm bằng schema thay vì
    kiểm rỗng — đúng bản chất "sổ SẼ có nội dung theo thời gian", không
    phải "sổ mãi mãi rỗng ở D0-PRE".
    """

    def test_hai_file_jsonl_ton_tai(self) -> None:
        assert (REPO_ROOT / "registry/trial_registry.jsonl").exists()
        assert (REPO_ROOT / "registry/idea_queue.jsonl").exists()

    def test_idea_queue_van_rong_chua_mo(self) -> None:
        # OQ-07: tiêu chí chọn ý tưởng của quý phải commit TRƯỚC khi mở
        # queue (spec dòng 4935) — chưa chốt, nên vẫn phải rỗng.
        assert (REPO_ROOT / "registry/idea_queue.jsonl").read_text(encoding="utf-8") == ""

    def test_trial_registry_that_moi_dong_hop_le_theo_schema(self) -> None:
        events = _load_jsonl(REPO_ROOT / "registry/trial_registry.jsonl")
        assert len(events) > 0, "registry trống — TD-0083 chưa commit hay đã bị xoá nhầm?"
        for e in events:
            jsonschema.validate(e, TRIAL_EVENT_SCHEMA)

    def test_moi_su_kien_thuoc_budget_line_b0(self) -> None:
        # Đến thời điểm sửa file này, MỌI trial thật đã tiêu đều là B0
        # (TD-0083, chốt pool) — chưa có B1/B2/B3 nào. Nếu test này đỏ vì
        # đã có trial khác, đó là tín hiệu TỐT (nghiên cứu đã tiến thêm)
        # — cập nhật lại giả định, không phải dấu hiệu lỗi.
        #
        # Cập nhật 08/09/2026 (TD-0161): đúng dự đoán trên — sổ thật có thêm
        # 1 dòng CTRL (D3.5 Bước 1, budget_line="CTRL", 0 trial, không tính
        # vào N — MT-08). CTRL đứng NGOÀI ngân sách B0-B3 theo thiết kế, nên
        # loại nó khỏi phép kiểm "mọi B0" thay vì gộp nó vào B0.
        events = _load_jsonl(REPO_ROOT / "registry/trial_registry.jsonl")
        reserve_events = [e for e in events if e["event"] == "RESERVE"]
        b0_events = [e for e in reserve_events if e["budget_line"] != "CTRL"]
        assert all(e["budget_line"] == "B0" for e in b0_events)
        assert len(b0_events) == 4
        assert len(reserve_events) == 5
