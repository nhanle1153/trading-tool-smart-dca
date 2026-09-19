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


#: Ba dạng khai CTRL (TD-0130 · MT-19/TD-0344) — mỗi dòng CTRL khai ĐÚNG MỘT.
_KHOA_DANG_CTRL = ("reproduces_trial_id", "ctrl_output_whitelist", "ctrl_mo_ta_whitelist")


def _kiem_so_that(events: list[dict]) -> None:
    """TD-0346 — quan hệ của sổ trial thật, thay cho số đếm ghim cứng.

    * Trial THẬT (không phải CTRL): mọi dòng là B0 và đủ 4 (TD-0083, chốt pool). Đây vẫn là ghim CHẶT có chủ đích —
      một trial B1/B2/B3 xuất hiện là một QUYẾT ĐỊNH tiêu suất, phải có người cập nhật dòng này kèm DR.
    * CTRL (0 trial, MT-08): số lượng tự do, nhưng mỗi dòng khai ĐÚNG MỘT trong ba dạng.

    🔄 19/09/2026 (chủ dự án duyệt sửa khẳng định, `DR-D4-19` §5): đúng cái QUYẾT ĐỊNH mà dòng trên chờ — lô D4
    `DR-D4-19` tiêu suất `B2`. B0 vẫn ghim đủ 4; B2 chỉ hợp lệ khi mang `hypothesis_slot = DR-D4-19` và số suất B2
    KHÔNG bị REFUND ≤ 4 (một lô 4 arm, `DR-D4-12` §4). B1/B3 vẫn cấm. RESERVE B2 đã REFUND (lượt 1, `a2f4c60`)
    không tiêu suất nên không vào trần.
    """
    reserve = [e for e in events if e["event"] == "RESERVE"]
    that = [e for e in reserve if e["budget_line"] != "CTRL"]
    assert all(e["budget_line"] in ("B0", "B2") for e in that), [(e["trial_id"], e["budget_line"]) for e in that]
    b0 = [e for e in that if e["budget_line"] == "B0"]
    assert len(b0) == 4, f"{len(b0)} trial B0 — tiêu suất mới là quyết định cần DR"
    b2 = [e for e in that if e["budget_line"] == "B2"]
    assert all(e["hypothesis_slot"] == "DR-D4-19" for e in b2), [(e["trial_id"], e["hypothesis_slot"]) for e in b2]
    hoan = {e["trial_id"] for e in events if e["event"] == "REFUND"}
    b2_khong_hoan = [e["trial_id"] for e in b2 if e["trial_id"] not in hoan]
    assert len(b2_khong_hoan) <= 4, f"{b2_khong_hoan}: quá một lô 4 arm DR-D4-19 — cần DR mới"
    for e in reserve:
        if e["budget_line"] == "CTRL":
            dang = [k for k in _KHOA_DANG_CTRL if k in e]
            assert len(dang) == 1, f"{e['trial_id']}: CTRL khai {dang} — phải đúng một dạng"


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

    Cập nhật 16/09/2026 (TD-0259): câu "`idea_queue.jsonl` vẫn rỗng" ở trên
    hết đúng — OQ-07 đã đóng 07/09 (`DR-Q3-2026`, cửa NỘP mở) và `1a00c66`
    (TD-0226) nộp hợp lệ `IQ-0001`. Ca "sổ ý tưởng phải rỗng" vì thế đỏ từ
    14/09; thay bằng đúng khuôn của `trial_registry` ngay dưới: sổ thật
    không rỗng + mọi dòng khớp schema.
    """

    def test_hai_file_jsonl_ton_tai(self) -> None:
        assert (REPO_ROOT / "registry/trial_registry.jsonl").exists()
        assert (REPO_ROOT / "registry/idea_queue.jsonl").exists()

    def test_idea_queue_that_moi_dong_hop_le_theo_schema(self) -> None:
        # Chốt `len > 0` KHÔNG phải trang trí: thiếu nó thì sổ rỗng cho vòng
        # `for` chạy 0 lần ⇒ PASS RỖNG. Và nó không lỗi thời được như ca cũ
        # (TD-0259): sổ append-only chỉ lớn lên — ghim QUAN HỆ, không ghim `== 1`.
        entries = _load_jsonl(REPO_ROOT / "registry/idea_queue.jsonl")
        assert len(entries) > 0, (
            "idea_queue trống — IQ-0001 (TD-0226, 1a00c66) đã bị xoá nhầm? "
            "Sổ append-only không được co lại."
        )
        for e in entries:
            jsonschema.validate(e, IDEA_QUEUE_SCHEMA)

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
        #
        # 🔄 TD-0346 (19/09/2026, chủ dự án duyệt sửa khẳng định — điều kiện dừng `DR-D4-16` §6): dòng cũ
        # `len(reserve_events) == 5` ghim SỐ ĐẾM cả CTRL — đỏ mỗi lần có một điểm kiểm soát hợp lệ (TD-0345 thêm 5).
        # Thay bằng QUAN HỆ (bài học TD-0171): trial THẬT vẫn ghim chặt (đổi = một quyết định), CTRL thì kiểm HÌNH.
        _kiem_so_that(_load_jsonl(REPO_ROOT / "registry/trial_registry.jsonl"))

    def test_quan_he_co_rang_mot_trial_B2_lot_vao_la_do(self) -> None:
        """Kiểm-có-răng TD-0346, viết thành ca: bản sao sổ thật + một RESERVE B2 ⇒ phải raise."""
        events = _load_jsonl(REPO_ROOT / "registry/trial_registry.jsonl")
        gia = dict(next(e for e in events if e["event"] == "RESERVE" and e["budget_line"] == "B0"))
        gia.update(trial_id="D-9999", budget_line="B2")
        with pytest.raises(AssertionError):
            _kiem_so_that([*events, gia])

    def test_quan_he_co_rang_B2_dung_slot_nhung_qua_mot_lo_la_do(self) -> None:
        """DR-D4-19: slot đúng không đủ — suất B2 thứ năm không REFUND (vượt lô 4 arm) ⇒ phải raise."""
        events = _load_jsonl(REPO_ROOT / "registry/trial_registry.jsonl")
        mau = dict(next(e for e in events if e["event"] == "RESERVE" and e["budget_line"] == "B0"))
        gia = [
            {**mau, "trial_id": f"D-99{i:02d}", "budget_line": "B2", "hypothesis_slot": "DR-D4-19"} for i in range(5)
        ]
        with pytest.raises(AssertionError):
            _kiem_so_that([*events, *gia])

    def test_quan_he_co_rang_ctrl_khai_chong_la_do(self) -> None:
        events = _load_jsonl(REPO_ROOT / "registry/trial_registry.jsonl")
        gia = dict(next(e for e in events if e["event"] == "RESERVE" and e["budget_line"] == "CTRL"))
        gia.update(trial_id="D-9998", reproduces_trial_id="D-0001", ctrl_output_whitelist=["price_delta"])
        with pytest.raises(AssertionError):
            _kiem_so_that([*events, gia])
