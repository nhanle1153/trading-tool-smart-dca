"""Cửa GHI của hàng chờ ý tưởng — `registry/idea_queue.jsonl` (§9c.7, TD-0124).

Trước task này project chỉ có phần ĐỌC (5 phép kiểm trong `audit_checks.py`):
muốn nộp một ý tưởng phải gõ tay JSON đủ 20 khoá với `additionalProperties:
false`. Gõ sai một khoá là một dòng sổ bẩn, và sổ là append-only nên không
xoá lại được.

🔑 Triết lý: TỪ CHỐI GHI, không phải ghi rồi để audit báo sau. Sổ append-only
   không có đường lùi — một dòng bẩn nằm đó vĩnh viễn. Vì vậy mọi phép kiểm
   chạy TRƯỚC khi mở file, và `submit_idea()` raise thay vì ghi một phần.

Công cụ này chỉ mở CỬA NỘP (MT-12). Nó KHÔNG ghi được dòng `SELECTED` —
cửa CHỌN là hành động khác hẳn: tối đa 1 lần/quý và đòi thêm 4 trường
(`tin_hieu`/`quy_tac`/`nguong_bac_bo`/`so_bien_the`). Tách vật lý hai cửa để
không có đường nào một lần nộp đơn vô tình trở thành một lần chọn.

🔴 Hạn ngạch CHỌN của một quý nằm ở `docs/decisions/DR-Q{n}-{năm}-tieu-chi-
   chon-y-tuong.md` của ĐÚNG quý đó, và máy đọc động (`audit_checks.HAN_NGACH_RE`
   + `_tieu_chi_path()`). Cố ý KHÔNG chép con số nào vào đây: bản trước có chép,
   nguồn đổi sang quý sau, bản chép ở lại — và vì nó nằm trong chuỗi in ra lúc
   chạy nên người đọc tưởng máy đang nói sự thật hiện tại (TD-0315).
"""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema

from tool_d.ledger.audit_checks import (
    CUA_CHON_FIELDS,
    DEFAULT_IDEA_QUEUE_PATH,
    DEFAULT_TIEU_CHI_DIR,
    HAN_NGACH_RE,
    TC_CODE_RE,
    _quarter_of,
    _read_jsonl,
    _tieu_chi_path,
)
from tool_d.ledger.idea_events import SO_LAN_HUY_TOI_DA, TRUONG_NOP, dr_co_that, duyet_so
from tool_d.ledger.registry import DEFAULT_REGISTRY_PATH, TrialLedger

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

# TD-0126 — ngưỡng coi hai `mechanism` là NGHI trùng nhau (Jaccard trên từ
# có nghĩa). 🔴 Đây KHÔNG phải tham số Tầng A/B/C và không được đưa vào
# `tool_d_config.yaml`: nó không chảy vào bất kỳ con số đo nào, không tiêu
# trial, và hậu quả khi đặt sai chỉ là người nộp phải khai thêm một dòng
# `overlaps_with` — không phải mất một ý tưởng hay lệch một phép đo. Chọn
# hậu quả nhẹ như vậy là có ý thức: một ngưỡng mà đặt sai thì tốn kém sẽ
# trở thành một cái núm để vặn.
NGUONG_NGHI_TRUNG = 0.6

# Từ quá ngắn không mang thông tin phân biệt — bỏ trước khi so.
DO_DAI_TU_TOI_THIEU = 3


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


def _tu_co_nghia(text: str) -> set[str]:
    """Tách `mechanism` thành tập từ để so trùng — bỏ dấu, bỏ từ quá ngắn.

    Bỏ dấu tiếng Việt vì cùng một cơ chế hay được viết cả có dấu lẫn không
    dấu trong repo này (so sánh có dấu sẽ bỏ sót đúng ca cần bắt).
    """
    # 🔴 `đ` (U+0111) KHÔNG tách được bằng NFD — nó là ký tự CƠ SỞ riêng, nét
    # gạch không phải dấu tổ hợp. Không thay tay thì `re` nuốt luôn nó:
    # "đóng" -> "ong" trong khi "dong" giữ nguyên, và hai cách viết cùng một
    # cơ chế lại thành hai cơ chế khác nhau — đúng ca test này sinh ra để bắt.
    thay_d = text.lower().replace("đ", "d")
    khong_dau = "".join(
        c for c in unicodedata.normalize("NFD", thay_d) if unicodedata.category(c) != "Mn"
    )
    tu = re.findall(r"[a-z0-9]+", khong_dau)
    return {t for t in tu if len(t) >= DO_DAI_TU_TOI_THIEU}


def do_trung(a: str, b: str) -> float:
    """Jaccard trên tập từ có nghĩa. 1.0 = cùng bộ từ, 0.0 = không chung từ nào."""
    ta, tb = _tu_co_nghia(a), _tu_co_nghia(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def tim_nghi_trung(
    entries: list[dict[str, Any]], mechanism: str, *, bo_qua_id: str | None = None
) -> list[tuple[str, str, float]]:
    """Các đơn đã có mà `mechanism` nghi trùng — (idea_id, status, tỉ lệ), cao trước.

    §9c.7.4 ràng buộc (3): *"Trước khi thêm ý tưởng mới, query queue theo
    `mechanism` để phát hiện trùng lặp — tương đương `retest_forbidden` của
    trial_registry"*.
    """
    ra = [
        (e["idea_id"], e.get("status", ""), do_trung(mechanism, e.get("mechanism") or ""))
        for e in entries
        if e.get("idea_id") != bo_qua_id
    ]
    return sorted([x for x in ra if x[2] >= NGUONG_NGHI_TRUNG], key=lambda x: -x[2])


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

    Chỉ đếm DÒNG ĐẦU của mỗi mã (DR-IQ-02): dòng chọn/huỷ là sự kiện trên
    một đơn đã có, không phải đơn nộp mới.
    """
    n = 0
    for e in duyet_so(entries).dong_dau.values():
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

    Tám ca TỪ CHỐI, tất cả kiểm TRƯỚC khi mở file (xem docstring module).
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
            "Chọn một ý tưởng ra khỏi hàng chờ là hành động KHÁC (MT-12): tối đa 1 lần/quý, "
            "đòi thêm tin_hieu/quy_tac/nguong_bac_bo/so_bien_the. Hạn ngạch CHỌN của quý "
            "hiện hành đọc ở docs/decisions/DR-Q<n>-<năm>-tieu-chi-chon-y-tuong.md — đọc "
            "file đó, đừng tin một con số chép sẵn ở đây (TD-0315)."
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

    # ── Ca 7 — EXPLORE phải nêu đã phân tích gì (§9c.7.3) ─────────────────
    if e["data_source"] == "EXPLORE" and not str(e.get("explore_evidence") or "").strip():
        raise IdeaQueueError(
            "data_source=EXPLORE nhưng `explore_evidence` rỗng — §9c.7.3 bắt nêu rõ đã phân "
            "tích GÌ, trên coin/khoảng nào. Không có câu đó thì không phân biệt được EXPLORE "
            "với TOOL_D_RESULTS, tức mất luôn ranh giới mà `data_source` sinh ra để giữ."
        )

    # ── Ca 8 — nghi trùng `mechanism` (§9c.7.4 ràng buộc 3) ───────────────
    nghi = tim_nghi_trung(list(duyet_so(entries).dong_dau.values()), e["mechanism"])
    da_khai = set(e.get("overlaps_with") or [])
    chua_khai = [x for x in nghi if x[0] not in da_khai]
    if chua_khai:
        bi_loai = [x for x in chua_khai if x[1] == "REJECTED"]
        mo_ta = "; ".join(f"{i} ({st}, trùng {t:.0%})" for i, st, t in chua_khai)
        if bi_loai:
            raise IdeaQueueError(
                f"Cơ chế này trùng một ý tưởng ĐÃ BỊ LOẠI: {mo_ta}. §9c.7.4 ràng buộc (3): ý "
                "tưởng bị loại **KHÔNG được nộp lại dưới tên khác** — tương đương "
                "`retest_forbidden` của sổ trial. Nếu thật sự là cơ chế khác, hãy viết "
                "`mechanism` cho rõ chỗ khác nhau và khai id đó vào `overlaps_with`."
            )
        raise IdeaQueueError(
            f"Cơ chế này nghi trùng đơn đã có: {mo_ta}. Khai chúng vào `overlaps_with` (nếu "
            "là cơ chế khác, chỉ giống chữ), hoặc đặt `filter_verdict: DUPLICATE` + "
            "`status: REJECTED` (nếu đúng là trùng). Máy không tự đoán hộ — nhưng cũng không "
            "cho nộp im lặng một cơ chế đã nằm trong hàng chờ."
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(e, ensure_ascii=False) + "\n")
    return e["idea_id"]


# ── Cửa CHỌN và cửa HUỶ (DR-IQ-02) ────────────────────────────────────
# Tờ chọn chỉ được mang các khoá này. `selected_at` KHÔNG nằm trong danh sách:
# máy đóng dấu (§4.5) — ngày chọn do người điền chính là gốc của MT-65.
KHOA_TO_CHON = frozenset(
    {"idea_id", "status", "selection_reason", "budget_a_slot", *CUA_CHON_FIELDS, *TRUONG_NOP}
)


def _vi_pham_moi(truoc: list[str], sau: list[str]) -> list[str]:
    return [v for v in sau if v not in truoc]


def _ghi_dong(path: Path, e: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(e, ensure_ascii=False) + "\n")


def chon_y_tuong(
    *,
    to_chon: dict[str, Any],
    path: Path = DEFAULT_IDEA_QUEUE_PATH,
    schema_path: Path = SCHEMA_PATH,
    tieu_chi_dir: Path = DEFAULT_TIEU_CHI_DIR,
    bay_gio: str | None = None,
) -> str:
    """Ghi sự kiện SELECTED cho một mã đang QUEUED. Raise `IdeaQueueError` nếu từ chối.

    Trường nộp lấy từ DÒNG ĐẦU của mã (DR-IQ-02 §4.2); tờ chọn chỉ mang thêm
    các trường cửa CHỌN. Mọi điều kiện kiểm TRƯỚC khi mở file. `bay_gio` chỉ
    để test cố định đồng hồ — đường chạy thật để trống.
    """
    t = dict(to_chon)
    ma = t.get("idea_id")
    if t.get("selected_at") is not None:
        raise IdeaQueueError(
            "Tờ chọn tự điền selected_at — TỪ CHỐI (DR-IQ-02 §4.5). Máy đóng dấu thời điểm chọn "
            "lúc ghi; một ngày chọn do người điền chính là gốc của MT-65."
        )
    la = sorted(set(k for k, v in t.items() if v is not None) - KHOA_TO_CHON)
    if la:
        raise IdeaQueueError(f"Tờ chọn mang khoá không thuộc cửa CHỌN: {la}")
    if t.get("status") not in (None, "SELECTED"):
        raise IdeaQueueError(f"status={t.get('status')} — cửa CHỌN chỉ ghi SELECTED")

    entries = _read_jsonl(path)
    duyet = duyet_so(entries)
    if duyet.trang_thai.get(ma) != "QUEUED":
        raise IdeaQueueError(
            f"{ma} đang {duyet.trang_thai.get(ma) or 'không có trong sổ'} — chỉ chọn được mã đang "
            "QUEUED (DR-IQ-02 §4.1)."
        )
    dau = duyet.dong_dau[ma]
    lech = [f for f in TRUONG_NOP if f in t and t[f] != dau.get(f)]
    if lech:
        raise IdeaQueueError(
            f"Tờ chọn đổi trường nộp {lech} so với đơn đã nộp — TỪ CHỐI (DR-IQ-02 §4.2). Muốn sửa "
            f"ý tưởng thì nộp đơn mới với overlaps_with: [\"{ma}\"] rồi chọn đơn đó."
        )

    e = {k: v for k, v in dau.items() if k not in ("voided_at", "void_reason")}
    e["status"] = "SELECTED"
    e["selected_at"] = bay_gio or _utcnow_iso_seconds()
    e["budget_a_slot"] = t.get("budget_a_slot")
    e["selection_reason"] = t.get("selection_reason")
    for f in CUA_CHON_FIELDS:
        e[f] = t.get(f)

    try:
        jsonschema.validate(e, _load_schema(schema_path))
    except jsonschema.ValidationError as exc:
        raise IdeaQueueError(
            f"Tờ chọn không hợp lệ theo schema — TỪ CHỐI ghi.\n"
            f"  chỗ sai: {'/'.join(str(p) for p in exc.absolute_path) or '(gốc)'}\n"
            f"  lý do:   {exc.message}"
        ) from exc

    thieu = [f for f in CUA_CHON_FIELDS if e[f] is None or (isinstance(e[f], str) and not e[f].strip())]
    if thieu:
        raise IdeaQueueError(f"Thiếu trường cửa CHỌN {thieu} (MT-12, TD-0119a).")

    nam, quy = _quarter_of_iso(e["selected_at"])
    file_tc = _tieu_chi_path(tieu_chi_dir, nam, quy)
    if not file_tc.exists():
        raise IdeaQueueError(f"Quý {quy}/{nam} CHƯA có file tiêu chí ({file_tc}) — TỪ CHỐI chọn.")
    noi_dung = file_tc.read_text(encoding="utf-8")
    m = HAN_NGACH_RE.search(noi_dung)
    if m is None:
        raise IdeaQueueError(f"{file_tc} không khai HAN_NGACH_CHON — TỪ CHỐI chọn (fail-closed).")
    han_ngach = int(m.group(1))
    da_chon = sum(
        1
        for x in duyet.chon_hieu_luc
        if x.get("selected_at") and _quarter_of_iso(x["selected_at"]) == (nam, quy)
    )
    if da_chon >= han_ngach:
        raise IdeaQueueError(
            f"Quý {quy}/{nam} đã có {da_chon} lần chọn còn hiệu lực, HAN_NGACH_CHON: {han_ngach} "
            f"({file_tc.name}) — TỪ CHỐI chọn (DR-IQ-02 §4.4)."
        )
    ma_trich = {x.group(0) for x in TC_CODE_RE.finditer(e["selection_reason"] or "")}
    ma_hop_le = {x.group(0) for x in TC_CODE_RE.finditer(noi_dung)}
    if not ma_trich:
        raise IdeaQueueError("selection_reason không trích mã tiêu chí nào (TD-0120).")
    if ma_trich - ma_hop_le:
        raise IdeaQueueError(
            f"selection_reason trích mã không có trong {file_tc.name}: {sorted(ma_trich - ma_hop_le)}"
        )

    moi = _vi_pham_moi(duyet.vi_pham, duyet_so([*entries, e]).vi_pham)
    if moi:
        raise IdeaQueueError("Dòng chọn sẽ làm sổ vi phạm DR-IQ-02:\n  " + "\n  ".join(moi))

    _ghi_dong(path, e)
    return ma


def huy_chon(
    *,
    idea_id: str,
    ly_do: str,
    path: Path = DEFAULT_IDEA_QUEUE_PATH,
    registry_path: Path = DEFAULT_REGISTRY_PATH,
    decisions_dir: Path = DEFAULT_TIEU_CHI_DIR,
    schema_path: Path = SCHEMA_PATH,
    bay_gio: str | None = None,
) -> str:
    """Ghi sự kiện VOIDED — huỷ lần chọn đang hiệu lực của `idea_id` (DR-IQ-02 §4.3).

    Năm điều kiện, kiểm hết TRƯỚC khi mở file: đang SELECTED · không trial nào
    mang `hypothesis_slot` bằng mã này · chưa từng huỷ · `ly_do` trích DR có
    thật · `voided_at` do máy đóng dấu.
    """
    entries = _read_jsonl(path)
    duyet = duyet_so(entries)
    if duyet.trang_thai.get(idea_id) != "SELECTED":
        raise IdeaQueueError(
            f"{idea_id} đang {duyet.trang_thai.get(idea_id) or 'không có trong sổ'} — chỉ huỷ được "
            "lần chọn đang hiệu lực."
        )
    if duyet.so_lan_huy[idea_id] >= SO_LAN_HUY_TOI_DA:
        raise IdeaQueueError(f"{idea_id} đã bị huỷ chọn một lần — hết lượt (DR-IQ-02 §4.3 điều 3).")
    slot = {p.hypothesis_slot for p in TrialLedger(registry_path).projections().values()}
    if idea_id in slot:
        raise IdeaQueueError(
            f"Đã có trial mang hypothesis_slot={idea_id} — không được huỷ một lần chọn đã tiêu "
            "ngân sách N (DR-IQ-02 §4.3 điều 2)."
        )
    if not dr_co_that(ly_do, decisions_dir):
        raise IdeaQueueError(
            f"Lý do huỷ phải trích một DR có thật trong {decisions_dir} (DR-IQ-02 §4.3 điều 4)."
        )

    bi_huy = [x for x in duyet.chon_hieu_luc if x.get("idea_id") == idea_id][-1]
    dau = duyet.dong_dau[idea_id]
    e: dict[str, Any] = {k: dau.get(k) for k in TRUONG_NOP}
    e.update(
        idea_id=idea_id,
        status="VOIDED",
        selected_at=bi_huy.get("selected_at"),
        voided_at=bay_gio or _utcnow_iso_seconds(),
        void_reason=ly_do,
        budget_a_slot=None,
        selection_reason=None,
    )
    for f in CUA_CHON_FIELDS:
        e[f] = None

    try:
        jsonschema.validate(e, _load_schema(schema_path))
    except jsonschema.ValidationError as exc:
        raise IdeaQueueError(f"Dòng huỷ không hợp lệ theo schema: {exc.message}") from exc

    moi = _vi_pham_moi(
        duyet_so(entries, decisions_dir=decisions_dir, slot_da_dung=slot).vi_pham,
        duyet_so([*entries, e], decisions_dir=decisions_dir, slot_da_dung=slot).vi_pham,
    )
    if moi:
        raise IdeaQueueError("Dòng huỷ sẽ làm sổ vi phạm DR-IQ-02:\n  " + "\n  ".join(moi))

    _ghi_dong(path, e)
    return idea_id
