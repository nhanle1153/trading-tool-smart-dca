"""Cửa GHI của hàng chờ ý tưởng — `registry/idea_queue.jsonl` (§9c.7, TD-0124).

Trước task này project chỉ có phần ĐỌC (5 phép kiểm trong `audit_checks.py`):
muốn nộp một ý tưởng phải gõ tay JSON đủ 20 khoá với `additionalProperties:
false`. Gõ sai một khoá là một dòng sổ bẩn, và sổ là append-only nên không
xoá lại được.

🔑 Triết lý: TỪ CHỐI GHI, không phải ghi rồi để audit báo sau. Sổ append-only
   không có đường lùi — một dòng bẩn nằm đó vĩnh viễn. Vì vậy mọi phép kiểm
   chạy TRƯỚC khi mở file, và `submit_idea()` raise thay vì ghi một phần.

Công cụ này chỉ mở CỬA NỘP (MT-12). Nó KHÔNG ghi được dòng `SELECTED` —
cửa CHỌN là hành động khác hẳn: 1 lần/quý, đòi thêm 4 trường
(`tin_hieu`/`quy_tac`/`nguong_bac_bo`/`so_bien_the`), và quý 3/2026 có
`HAN_NGACH_CHON: 0`. Tách vật lý hai cửa để không có đường nào một lần nộp
đơn vô tình trở thành một lần chọn.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema

from tool_d.ledger.audit_checks import (
    DEFAULT_IDEA_QUEUE_PATH,
    _quarter_of,
    _read_jsonl,
)

SCHEMA_PATH = Path("registry/schemas/idea_queue_entry.schema.json")

# 🚪 TRẦN NHẬP QUEUE (spec dòng 4095, §9c.7.4). KHÁC với trần CHỌN 5/quý
# (L-Z17) mà MT-11 đã nới thành cảnh báo.
#
# Vì sao trần NHẬP chặn CỨNG trong khi trần CHỌN chỉ cảnh báo: trần CHỌN là
# kỷ luật CON NGƯỜI (ý tưởng nào đáng thử) và không chảy vào N/DSR. Trần NHẬP
# thì có: với LLM, chi phí sinh ý tưởng ≈ 0, nên queue có thể có 100 ý tưởng/
# tuần trong khi trần chọn vẫn 5/quý. Tỉ lệ chọn 5% biến bước CHỌN thành nơi
# khai thác dữ liệu quy mô lớn — và nó VÔ HÌNH vì không ai ghi sổ cho bước
# chọn. Đây là chống nhiễu thống kê, cùng loại với L-Z16, không phải kỷ luật.
IDEA_QUEUE_INTAKE_PER_QUARTER_MAX = 10

# Cửa NỘP chỉ sinh được hai trạng thái này (xem docstring module).
TRANG_THAI_CUA_NOP = ("QUEUED", "REJECTED")

# Ba câu bộ lọc §0.1 — cùng luật `check_lz16`, áp ở cửa ghi.
BO_LOC_FIELDS = ("mechanism", "who_pays", "durability")

# 20 khoá `required` của schema, để điền `None` cho trường người nộp bỏ trống
# (schema đặt `additionalProperties: false` VÀ `required` cả 20 — một tờ đơn
# thiếu khoá `selected_at: null` là đơn không hợp lệ, dù nghĩa vẫn đúng).
KHOA_TU_DIEN = (
    "selected_at",
    "budget_a_slot",
    "selection_reason",
    "tin_hieu",
    "quy_tac",
    "nguong_bac_bo",
    "so_bien_the",
    "explore_evidence",
)


class IdeaQueueError(RuntimeError):
    """Đơn không hợp lệ — TỪ CHỐI ghi, sổ không bị đụng tới."""


def _utcnow_iso_seconds() -> str:
    """UTC ISO-8601 tới GIÂY — 🔴 KHÔNG dùng `registry._utcnow_iso()`.

    `registry.py` ghi micro giây vì L-Z10 đòi `registered_at < executed_at`
    CHẶT. Sổ ý tưởng thì ngược lại: schema bắt pattern chỉ tới giây, và
    `check_lz17` (`audit_checks.py`) + `check_td0120` đọc bằng
    `strptime(..., "%Y-%m-%dT%H:%M:%SZ")` — định dạng KHÔNG dung sai micro
    giây. Dùng nhầm hàm kia sẽ làm hai phép kiểm đó **crash ValueError**,
    tức audit chết giữa chừng chứ không fail sạch — hỏng đúng thứ tầng đo
    tồn tại để bảo vệ.
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_schema(schema_path: Path = SCHEMA_PATH) -> dict[str, Any]:
    return json.loads(schema_path.read_text(encoding="utf-8"))


def next_idea_id(path: Path = DEFAULT_IDEA_QUEUE_PATH) -> str:
    """`IQ-0001`, `IQ-0002`, … — tính từ số lớn nhất ĐÃ có trong sổ.

    Lấy max chứ không phải `len(entries) + 1`: sổ là nhật ký append-only,
    nếu về sau có dòng mang id do người nộp tự đặt thì đếm số dòng sẽ sinh
    ra một id trùng — mà trùng id là hai ý tưởng khác nhau mang cùng tên.
    """
    so = [
        int(e["idea_id"].split("-", 1)[1])
        for e in _read_jsonl(path)
        if isinstance(e.get("idea_id"), str) and e["idea_id"].startswith("IQ-")
    ]
    return f"IQ-{(max(so) + 1) if so else 1:04d}"


def _quarter_of_iso(ts: str) -> tuple[int, int]:
    d: date = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").date()
    return _quarter_of(d)


def dem_don_trong_quy(entries: list[dict[str, Any]], quy: tuple[int, int]) -> int:
    """Số đơn đã NHẬP trong một quý — đếm theo `created_at`, mọi `status`.

    Kể cả đơn `REJECTED`: trần NHẬP chặn ở NGUỒN (spec dòng 4095 —
    "Chặn ở NGUỒN rẻ hơn và hữu hình hơn chặn ở đầu ra"). Một đơn bị bộ lọc
    §0.1 loại vẫn đã tiêu công sinh + công đọc của quý đó.
    """
    n = 0
    for e in entries:
        ts = e.get("created_at")
        if not isinstance(ts, str):
            continue
        try:
            if _quarter_of_iso(ts) == quy:
                n += 1
        except ValueError:
            continue
    return n


def submit_idea(
    *,
    don: dict[str, Any],
    path: Path = DEFAULT_IDEA_QUEUE_PATH,
    schema_path: Path = SCHEMA_PATH,
) -> str:
    """Ghi MỘT đơn vào cuối sổ. Trả `idea_id`. Raise `IdeaQueueError` nếu từ chối.

    Điền hộ `idea_id` và `created_at` nếu người nộp bỏ trống, cùng các khoá
    `required` mà một đơn mới nộp chưa có nghĩa gì (điền `None`) — người nộp
    không phải nhớ 20 khoá, nhưng dòng ghi ra vẫn đủ 20.

    Sáu ca TỪ CHỐI, tất cả kiểm TRƯỚC khi mở file (xem docstring module).
    """
    e: dict[str, Any] = dict(don)  # không sửa dict của người gọi
    for khoa in KHOA_TU_DIEN:
        e.setdefault(khoa, None)
    e.setdefault("overlaps_with", [])
    e.setdefault("session_type", "IDEA")
    if not e.get("created_at"):
        e["created_at"] = _utcnow_iso_seconds()
    if not e.get("idea_id"):
        e["idea_id"] = next_idea_id(path)

    entries = _read_jsonl(path)

    # ── Ca 1 — schema (thiếu khoá / thừa khoá / sai enum / sai pattern) ──
    try:
        jsonschema.validate(e, _load_schema(schema_path))
    except jsonschema.ValidationError as exc:
        raise IdeaQueueError(
            f"Đơn không hợp lệ theo schema — TỪ CHỐI ghi.\n"
            f"  chỗ sai: {'/'.join(str(p) for p in exc.absolute_path) or '(gốc)'}\n"
            f"  lý do:   {exc.message}"
        ) from exc

    # ── Ca 2 — cửa NỘP không ghi được SELECTED ────────────────────────────
    if e["status"] not in TRANG_THAI_CUA_NOP:
        raise IdeaQueueError(
            f"status={e['status']} — cửa NỘP chỉ ghi được {list(TRANG_THAI_CUA_NOP)}. "
            "Chọn một ý tưởng ra khỏi hàng chờ là hành động KHÁC (MT-12): 1 lần/quý, "
            "đòi thêm tin_hieu/quy_tac/nguong_bac_bo/so_bien_the, và quý 3/2026 khai "
            "HAN_NGACH_CHON: 0."
        )

    # ── Ca 3 — TOOL_D_RESULTS phải REJECTED (cùng luật L-Z16) ─────────────
    if e["data_source"] == "TOOL_D_RESULTS" and e["status"] != "REJECTED":
        raise IdeaQueueError(
            "data_source=TOOL_D_RESULTS bắt buộc status=REJECTED (L-Z16) — ý tưởng nghĩ ra "
            "SAU khi xem kết quả Tool D là Loại B trá hình, không được vào hàng chờ Loại A."
        )

    # ── Ca 4 — trần NHẬP 10 đơn/quý ───────────────────────────────────────
    quy = _quarter_of_iso(e["created_at"])
    da_co = dem_don_trong_quy(entries, quy)
    if da_co >= IDEA_QUEUE_INTAKE_PER_QUARTER_MAX:
        raise IdeaQueueError(
            f"Quý {quy[1]}/{quy[0]} đã có {da_co} đơn — chạm trần NHẬP "
            f"{IDEA_QUEUE_INTAKE_PER_QUARTER_MAX}/quý (spec dòng 4095). "
            "Trần này chặn ở NGUỒN vì tỉ lệ chọn thấp biến bước CHỌN thành nơi khai "
            "thác dữ liệu quy mô lớn — và bước chọn thì không ai ghi sổ cho."
        )

    # ── Ca 5 — trùng idea_id ──────────────────────────────────────────────
    if any(x.get("idea_id") == e["idea_id"] for x in entries):
        raise IdeaQueueError(
            f"{e['idea_id']} đã có trong sổ — trùng id là hai ý tưởng khác nhau mang cùng "
            "tên. Sổ append-only không sửa lại được dòng cũ."
        )

    # ── Ca 6 — ba câu bộ lọc §0.1 (cùng luật check_lz16, áp ở cửa ghi) ────
    if e["data_source"] in ("MECHANISM", "EXPLORE"):
        thieu = [
            f for f in BO_LOC_FIELDS if not str(e.get(f) or "").strip() or e.get(f) == "n/a"
        ]
        if thieu:
            raise IdeaQueueError(
                f"Thiếu câu trả lời cho bộ lọc §0.1: {thieu}. "
                "'who_pays' là câu giết ý tưởng — không trả lời được AI TRẢ TIỀN thì "
                "ý tưởng không vào hàng chờ (spec dòng 4914)."
            )

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(e, ensure_ascii=False) + "\n")
    return e["idea_id"]
