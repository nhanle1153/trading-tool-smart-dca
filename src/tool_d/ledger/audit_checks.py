"""Các phép kiểm tự động cho `trial_ledger_audit.py` (E6, H16).

Mỗi hàm trả về `CheckResult` — không raise, không in gì, chỉ tính toán.
`entrypoints/trial_ledger_audit.py` gọi tất cả rồi tổng hợp bằng
`tri_state.audit_line()`.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml

from tool_d.config.loader import DEFAULT_CONFIG_PATH, load_tool_d_config
from tool_d.ledger import budget as _budget
from tool_d.ledger.registry import DEFAULT_REGISTRY_PATH, TrialLedger, TrialState
from tool_d.measurement.tri_state import Measured

DEFAULT_IDEA_QUEUE_PATH = Path("registry/idea_queue.jsonl")
DEFAULT_PARAM_STATUS_PATH = Path("config/param_status.yaml")

#: Trạng thái hợp lệ của một tham số [CẦN CALIBRATE].
#: `TUNED`/`FROZEN` là hai trạng thái spec cho phép (dòng 3882-3883).
#: `TUNED_PENDING` là trạng thái TRUNG GIAN của project ở D0-PRE, khi
#: registry còn rỗng nên chưa trial nào tồn tại được — nó CHỈ hợp lệ cho
#: tham số còn `null`; một tham số đã có giá trị mà vẫn `TUNED_PENDING`
#: là nói "chưa calibrate" trong khi con số đã đang được dùng.
TRANG_THAI_THAM_SO_HOP_LE = frozenset({"TUNED", "FROZEN", "TUNED_PENDING"})
DEFAULT_TIEU_CHI_DIR = Path("docs/decisions")

BUDGET_A_SLOTS_PER_QUARTER_MAX = 5  # DR-009, §9.3 — không nới vì có LLM
IDEA_QUEUE_INTAKE_PER_QUARTER_MAX = 10  # spec dòng 4095 — trần NHẬP, khác trần CHỌN

# Phép kiểm CHỈ CẢNH BÁO — vượt thì báo, không chặn chạy.
# Quyết định chủ dự án 07/09/2026 (MT-11): trần 5 suất Ngân sách A là kỷ luật
# CON NGƯỜI (chọn ý tưởng nào đáng thử), không phải bất biến kỹ thuật — nó
# không chảy vào N/DSR. Đòn bẩy cũ phạt sai chỗ: vượt trần CHỌN Ý TƯỞNG lại
# khoá luôn việc ĐO. Nới riêng L-Z17, sửa có ý thức dòng H16 (spec 4347).
# 🔴 L-Z16 KHÔNG nằm ở đây và không bao giờ được đưa vào: đó là chống nhiễm
#    dữ liệu (ý tưởng nghĩ ra sau khi xem kết quả Tool D), không phải kỷ luật.
WARN_ONLY_CODES = frozenset({"L-Z17"})


@dataclass(frozen=True)
class CheckResult:
    code: str  # "L-Z10", ...
    measured: Measured[bool]
    evidence: str = ""

    @property
    def ok(self) -> bool:
        return self.measured.is_ok() and self.measured.value is True

    @property
    def is_fail(self) -> bool:
        return self.measured.is_ok() and self.measured.value is False


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def _parse_iso(ts: str) -> datetime:
    """Đọc cả hai dạng: có micro giây (ghi bởi `registry.py` thật) và
    chỉ tới giây (fixture tay) — xem ghi chú ở `registry._utcnow_iso()`.
    """
    fmt = "%Y-%m-%dT%H:%M:%S.%fZ" if "." in ts else "%Y-%m-%dT%H:%M:%SZ"
    return datetime.strptime(ts, fmt)


# ── L-Z10 ─────────────────────────────────────────────────────────────
def check_lz10_registered_before_executed(
    registry_path: Path = DEFAULT_REGISTRY_PATH,
) -> CheckResult:
    """registered_at < executed_at cho MỌI trial (spec dòng 3872)."""
    events = _read_jsonl(registry_path)
    reserved_at: dict[str, str] = {
        e["trial_id"]: e["registered_at"] for e in events if e["event"] == "RESERVE"
    }
    violations: list[str] = []
    for e in events:
        if e["event"] != "CONSUME":
            continue
        tid = e["trial_id"]
        r_at = reserved_at.get(tid)
        if r_at is None:
            violations.append(f"{tid}: CONSUME không có RESERVE trước đó")
            continue
        if not (_parse_iso(r_at) < _parse_iso(e["executed_at"])):
            violations.append(f"{tid}: registered_at={r_at} không < executed_at={e['executed_at']}")
    if not events:
        return CheckResult("L-Z10", Measured.pending("registry rỗng, chưa có sự kiện nào"))
    return CheckResult(
        "L-Z10",
        Measured.ok(len(violations) == 0),
        evidence="; ".join(violations),
    )


# ── L-Z11 ─────────────────────────────────────────────────────────────
def check_lz11_n_used_le_n_dang_ky(
    registry_path: Path = DEFAULT_REGISTRY_PATH, *, n_dang_ky: int
) -> CheckResult:
    """N_ĐÃ_DÙNG ≤ N_ĐĂNG_KÝ tại mọi thời điểm (spec dòng 3873)."""
    ledger = TrialLedger(registry_path)
    n_used = ledger.n_used()
    return CheckResult(
        "L-Z11",
        Measured.ok(n_used <= n_dang_ky),
        evidence=f"N_ĐÃ_DÙNG={n_used}, N_ĐĂNG_KÝ={n_dang_ky}",
    )


# ── L-Z12 ─────────────────────────────────────────────────────────────
def check_lz12_no_duplicate_config_hash_different_outcome(
    registry_path: Path = DEFAULT_REGISTRY_PATH,
) -> CheckResult:
    """Không config_hash nào xuất hiện ở 2 trial với outcome khác nhau
    (spec dòng 3874-3875: "nếu có → có chạy lại không ghi sổ, registry
    mất hiệu lực")."""
    events = _read_jsonl(registry_path)
    config_hash_by_trial: dict[str, str] = {
        e["trial_id"]: e["config_hash"] for e in events if e["event"] == "RESERVE"
    }
    outcome_by_trial: dict[str, dict] = {
        e["trial_id"]: e["outcome"] for e in events if e["event"] == "CONSUME"
    }
    if not events:
        return CheckResult("L-Z12", Measured.pending("registry rỗng"))

    by_hash: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    for tid, outcome in outcome_by_trial.items():
        ch = config_hash_by_trial.get(tid)
        if ch is not None:
            by_hash[ch].append((tid, outcome))

    violations: list[str] = []
    for ch, entries in by_hash.items():
        if len(entries) < 2:
            continue
        first_tid, first_outcome = entries[0]
        for tid, outcome in entries[1:]:
            if outcome != first_outcome:
                violations.append(
                    f"config_hash={ch}: {first_tid} và {tid} có outcome khác nhau"
                )
    return CheckResult("L-Z12", Measured.ok(len(violations) == 0), evidence="; ".join(violations))


# ── L-Z15 ─────────────────────────────────────────────────────────────
def check_lz15_calibrate_params_have_status(
    config_path: Path = DEFAULT_CONFIG_PATH,
    status_path: Path = DEFAULT_PARAM_STATUS_PATH,
) -> CheckResult:
    """Mọi tham số [CẦN CALIBRATE] phải có TRẠNG THÁI tường minh —
    `TUNED` (có trial) hoặc `FROZEN` (có `frozen_rationale`). Thiếu mặt,
    hoặc có mặt mà trạng thái rỗng nghĩa, đều là "im lặng": CẤM (spec
    dòng 3882-3884).

    🔴 **DR-D4-03 §6 — vì sao bản trước KHÔNG đủ, và vì sao chỗ hở chỉ
    lộ ra đúng lúc ta sửa MT-15.** Bản trước suy danh sách [CẦN
    CALIBRATE] từ *"khoá nào đang `null`"*. Cách đó hợp lý khi mọi tham
    số chưa calibrate đều còn `null` — nhưng **khoảnh khắc `v_min` nhận
    giá trị 1.0, nó thôi là `null` và phép kiểm THÔI CANH nó**, không ai
    còn hỏi con số đó từ đâu ra. Một tham số **có giá trị, không trial,
    không `frozen_rationale`** đúng là trạng thái "im lặng" dòng 3884
    cấm — và máy cũ không thấy được.

    Tức chính hành động vá MT-15 sẽ **tự làm câm lớp canh duy nhất** đang
    theo dõi tham số đó. Đây là bẫy PASS RỖNG thứ năm của dự án, và khác
    bốn cái trước ở chỗ: bốn cái kia có sẵn, cái này **do ta tạo ra khi
    sửa**.

    Nay: `param_status.yaml` là **nguồn sự thật cho DANH SÁCH**, và mọi
    mục trong đó bị soi **bất kể đã có giá trị hay chưa**. Luật cũ giữ
    nguyên, không nới: khoá `null` mà không khai vẫn là vi phạm.
    """
    cfg = load_tool_d_config(config_path)
    moi_tham_so = sorted(k for k in cfg.tier_b if not k.startswith("_"))
    null_params = sorted(k for k in moi_tham_so if cfg.tier_b[k] is None)

    if not status_path.exists():
        return CheckResult(
            "L-Z15",
            Measured.ok(False),
            evidence=f"thiếu {status_path}, nhưng có {len(moi_tham_so)} tham số tier_b cần trạng thái",
        )

    status_doc = yaml.safe_load(status_path.read_text(encoding="utf-8")) or {}
    khai_bao = status_doc.get("params") or {}
    declared = khai_bao.keys()

    vi_pham: list[str] = []

    # (1) TD-0190 — DANH SÁCH lấy từ `tier_b`, KHÔNG từ `param_status.yaml`.
    #
    # 🔴 Vì sao đổi nguồn danh sách, và vì sao bản trước vẫn chưa đủ dù đã
    # siết một lần: DR-D4-03 §6 đặt `param_status.yaml` làm *"nguồn sự
    # thật cho DANH SÁCH"*, nên phép kiểm chỉ soi những mục **có người tự
    # khai**. Kiểm kê TD-0190 cho thấy hậu quả bằng số: danh sách có ĐÚNG
    # MỘT mục (`v_min`) trong khi **11/12** tham số `tier_b` có giá trị,
    # **0 trial** (sổ thật: `param_under_test` chưa từng là một khoá
    # `tier_b`), **0 `frozen_rationale`** — tức đúng trạng thái "im lặng"
    # spec dòng 3884 cấm. Phép kiểm vẫn XANH suốt.
    #
    # Đây KHÔNG phải lớp canh cùn, cũng không phải chĩa nhầm hướng — hai
    # hình dạng dự án đã gặp. Nó là hình dạng thứ ba: **người bị canh tự
    # chọn phạm vi bị canh**. Một danh sách tự khai thì bỏ trống là hợp lệ.
    #
    # `tier_b` là danh sách ĐÓNG (đúng 12 khoá, `L-Z29` canh con số đó),
    # nên lấy nó làm nguồn thì phạm vi không co lại được nữa.
    vi_pham += [
        f"{p}: có trong tier_b nhưng không khai trạng thái"
        + (" (giá trị null)" if p in null_params else f" (đang mang giá trị {cfg.tier_b[p]!r})")
        for p in moi_tham_so
        if p not in declared
    ]

    # (2) MỚI: mọi mục ĐÃ KHAI phải có trạng thái hợp lệ — kể cả khi khoá
    #     đã có giá trị. Đây là phần bản cũ không phủ.
    for ten in sorted(declared):
        muc = khai_bao.get(ten) or {}
        trang_thai = (muc.get("status") or "").strip()
        if trang_thai not in TRANG_THAI_THAM_SO_HOP_LE:
            vi_pham.append(
                f"{ten}: status={trang_thai!r} không thuộc {sorted(TRANG_THAI_THAM_SO_HOP_LE)}"
            )
            continue
        # FROZEN mà không nói VÌ SAO thì đúng bằng im lặng: con số vẫn ở
        # đó, lý do thì không, và không ai truy được nó từ đâu ra.
        if trang_thai == "FROZEN" and not (muc.get("frozen_rationale") or "").strip():
            vi_pham.append(f"{ten}: FROZEN nhưng thiếu frozen_rationale")
        # `TUNED_PENDING` nghĩa là "chưa có gì để calibrate được" — chỉ
        # đúng khi khoá còn `null`. Một tham số ĐÃ CÓ GIÁ TRỊ mà vẫn khai
        # `TUNED_PENDING` là nói "chưa calibrate" trong khi con số đó đang
        # được hệ thống dùng thật; đó chính là ca bản cũ không thấy.
        if trang_thai == "TUNED_PENDING" and cfg.tier_b.get(ten) is not None:
            vi_pham.append(
                f"{ten}: TUNED_PENDING nhưng đã có giá trị {cfg.tier_b.get(ten)!r} — "
                "phải là TUNED (có trial) hoặc FROZEN (có frozen_rationale)"
            )

    if vi_pham:
        return CheckResult("L-Z15", Measured.ok(False), evidence="; ".join(vi_pham))

    # 🔴 TD-0190 — ĐẠT rồi vẫn phải NÓI RA con số, và đây là lý do.
    #
    # "Đạt" ở đây chỉ trả lời *"cả 12 đã KHAI trạng thái chưa?"* — nhưng
    # người đọc sẽ nghe thành *"cả 12 đã được QUYẾT đúng chưa?"*. Hai câu
    # khác nhau, và khoảng cách giữa chúng chính là hình dạng của mọi bẫy
    # PASS RỖNG dự án đã gặp: một phép kiểm xanh trả lời câu hẹp hơn câu
    # người ta tưởng.
    #
    # Sự thật tại 08/09/2026: **không tham số `tier_b` nào từng được tune
    # bằng một trial** — `param_under_test` trong sổ thật chưa từng là một
    # khoá `tier_b`. Cả 12 đều là CHỖ GIỮ. `chua_calibrate` khai điều đó
    # dưới dạng MÁY ĐỌC ĐƯỢC thay vì chôn trong 12 đoạn văn xuôi, và con
    # số dưới đây đi thẳng vào đầu ra E6, tức vào BẰNG CHỨNG CỔNG.
    cho_giu = sorted(t for t in declared if (khai_bao.get(t) or {}).get("chua_calibrate"))
    da_tune = sorted(
        t for t in declared if (khai_bao.get(t) or {}).get("status") == "TUNED"
    )
    return CheckResult(
        "L-Z15",
        Measured.ok(True),
        evidence=(
            f"{len(declared)}/{len(moi_tham_so)} tham số tier_b đã khai trạng thái; "
            f"{len(cho_giu)} ở CHỖ GIỮ chưa calibrate, {len(da_tune)} đã TUNED bằng trial"
            + (f" — chỗ giữ: {cho_giu}" if cho_giu else "")
        ),
    )


# ── L-Z16 ─────────────────────────────────────────────────────────────
def check_lz16_idea_queue_filter_and_tool_d_results(
    idea_queue_path: Path = DEFAULT_IDEA_QUEUE_PATH,
) -> CheckResult:
    """data_source ∈ {MECHANISM, EXPLORE} phải trả lời đủ 3 câu bộ lọc
    §0.1 (mechanism/who_pays/durability không rỗng); data_source ==
    TOOL_D_RESULTS phải có status=REJECTED (spec dòng 3885-3887)."""
    entries = _read_jsonl(idea_queue_path)
    if not entries:
        return CheckResult("L-Z16", Measured.pending("idea_queue rỗng"))

    violations: list[str] = []
    for e in entries:
        ds = e.get("data_source")
        if ds in ("MECHANISM", "EXPLORE"):
            for field in ("mechanism", "who_pays", "durability"):
                if not (e.get(field) or "").strip() or e[field] == "n/a":
                    violations.append(f"{e['idea_id']}: thiếu câu trả lời '{field}'")
        elif ds == "TOOL_D_RESULTS":
            if e.get("status") != "REJECTED":
                violations.append(
                    f"{e['idea_id']}: data_source=TOOL_D_RESULTS nhưng status={e.get('status')} != REJECTED"
                )
    return CheckResult("L-Z16", Measured.ok(len(violations) == 0), evidence="; ".join(violations))


# ── L-Z17 ─────────────────────────────────────────────────────────────
def _quarter_of(d: date) -> tuple[int, int]:
    return d.year, (d.month - 1) // 3 + 1


def check_lz17_budget_a_slots_per_quarter(
    idea_queue_path: Path = DEFAULT_IDEA_QUEUE_PATH,
) -> CheckResult:
    """Số slot NGÂN SÁCH A đã tiêu (status==SELECTED) ≤ 5/quý — KHÔNG
    nới vì có LLM (spec dòng 3888-3889, DR-009)."""
    entries = _read_jsonl(idea_queue_path)
    selected = [e for e in entries if e.get("status") == "SELECTED" and e.get("selected_at")]
    if not entries:
        return CheckResult("L-Z17", Measured.pending("idea_queue rỗng"))

    counts: Counter[tuple[int, int]] = Counter()
    for e in selected:
        d = datetime.strptime(e["selected_at"], "%Y-%m-%dT%H:%M:%SZ").date()
        counts[_quarter_of(d)] += 1

    over = {q: c for q, c in counts.items() if c > BUDGET_A_SLOTS_PER_QUARTER_MAX}
    return CheckResult(
        "L-Z17",
        Measured.ok(len(over) == 0),
        evidence=f"quý vượt trần: {over}" if over else "",
    )



# ── TD-0119 (MT-12) ───────────────────────────────────────────────────
CUA_CHON_FIELDS = ("tin_hieu", "quy_tac", "nguong_bac_bo", "so_bien_the")


def check_td0119_selected_du_phep_thu(
    idea_queue_path: Path = DEFAULT_IDEA_QUEUE_PATH,
) -> CheckResult:
    """CỬA CHỌN (MT-12): dòng `status == SELECTED` phải khai đủ bốn
    trường biến ý tưởng thành phép thử chạy được — `tin_hieu`,
    `quy_tac`, `nguong_bac_bo`, `so_bien_the`.

    Vì sao đặt ở cửa CHỌN chứ không phải cửa NỘP: một ý tưởng có thể
    nằm chờ vài quý; bắt viết đủ phép toán cho cả 10 đơn/quý là làm 10
    lần công cho 1 lần dùng, và con số viết lúc nộp sẽ lạc hậu. Điều
    kiện của tiền-đăng-ký chỉ là "viết TRƯỚC khi thấy kết quả của CHÍNH
    phép thử này" — lúc chọn vẫn thoả.

    Fail-closed, cùng khuôn `selection_reason` đã có sẵn ở §9c.7.4.
    """
    entries = _read_jsonl(idea_queue_path)
    selected = [e for e in entries if e.get("status") == "SELECTED"]
    if not selected:
        return CheckResult("TD-0119a", Measured.pending("chưa có ý tưởng nào được CHỌN"))

    violations: list[str] = []
    for e in selected:
        for field in CUA_CHON_FIELDS:
            gia_tri = e.get(field)
            thieu = gia_tri is None or (isinstance(gia_tri, str) and not gia_tri.strip())
            if thieu:
                violations.append(f"{e['idea_id']}: SELECTED nhưng thiếu '{field}'")
    return CheckResult(
        "TD-0119a", Measured.ok(len(violations) == 0), evidence="; ".join(violations)
    )


def check_td0119_so_bien_the_khong_vuot_khai(
    idea_queue_path: Path = DEFAULT_IDEA_QUEUE_PATH,
    registry_path: Path = DEFAULT_REGISTRY_PATH,
) -> CheckResult:
    """`so_bien_the` khai ở cửa CHỌN phải được ĐỐI CHIẾU với sổ trial,
    nếu không nó chỉ là lời khai (đúng loại sai lầm MT-10 vừa phải sửa).

    Quy ước nối hai sổ: trial sinh ra từ một ý tưởng trong hàng chờ ghi
    `hypothesis_slot = <idea_id>` (dạng `IQ-xxxx`). Số trial CONSUMED
    mang slot đó phải ≤ số đã khai. Vượt = tiêu ngân sách N nhiều hơn
    mức đăng ký trước — đúng thứ N=114 sinh ra để chặn.
    """
    entries = _read_jsonl(idea_queue_path)
    khai = {
        e["idea_id"]: e.get("so_bien_the")
        for e in entries
        if e.get("status") == "SELECTED" and e.get("so_bien_the") is not None
    }
    if not khai:
        return CheckResult(
            "TD-0119b", Measured.pending("chưa có ý tưởng CHỌN nào khai so_bien_the")
        )

    da_dung: Counter[str] = Counter()
    for proj in TrialLedger(registry_path).projections().values():
        if proj.state is TrialState.CONSUMED and proj.hypothesis_slot in khai:
            da_dung[proj.hypothesis_slot] += 1

    violations = [
        f"{idea_id}: đã tiêu {da_dung[idea_id]} trial > {so_khai} đã khai"
        for idea_id, so_khai in khai.items()
        if da_dung[idea_id] > so_khai
    ]
    return CheckResult(
        "TD-0119b", Measured.ok(len(violations) == 0), evidence="; ".join(violations)
    )



# ── TD-0124 (trần NHẬP hàng chờ) ──────────────────────────────────────
def check_td0124_tran_nhap_don_moi_quy(
    idea_queue_path: Path = DEFAULT_IDEA_QUEUE_PATH,
) -> CheckResult:
    """Trần NHẬP hàng chờ 10 đơn/quý (spec dòng 4095, §9c.7.4).

    `submit_idea()` đã chặn tại cửa ghi, nhưng cửa ghi không phải đường
    DUY NHẤT tới file — sổ vẫn sửa tay được. Phép kiểm này canh trạng
    thái sổ, không canh hành vi công cụ; hai lớp bịt hai lỗ khác nhau.

    🔴 CHẶN CỨNG, không đưa vào `WARN_ONLY_CODES`. Khác trần CHỌN
    (L-Z17) mà MT-11 đã nới: trần CHỌN là kỷ luật con người và không
    chảy vào N/DSR. Trần NHẬP thì có — chi phí sinh ý tưởng bằng LLM
    xấp xỉ 0, nên tỉ lệ chọn 5% biến bước CHỌN thành nơi khai thác dữ
    liệu quy mô lớn, VÔ HÌNH vì không ai ghi sổ cho bước chọn. Cùng
    loại với L-Z16 (chống nhiễu), không phải kỷ luật cá nhân.
    """
    entries = _read_jsonl(idea_queue_path)
    if not entries:
        return CheckResult("TD-0124", Measured.pending("idea_queue rỗng"))

    counts: Counter[tuple[int, int]] = Counter()
    for e in entries:
        ts = e.get("created_at")
        if not isinstance(ts, str):
            continue
        try:
            counts[_quarter_of(_parse_iso(ts).date())] += 1
        except ValueError:
            continue

    over = {q: c for q, c in counts.items() if c > IDEA_QUEUE_INTAKE_PER_QUARTER_MAX}
    return CheckResult(
        "TD-0124",
        Measured.ok(len(over) == 0),
        evidence=f"quý vượt trần NHẬP {IDEA_QUEUE_INTAKE_PER_QUARTER_MAX}/quý: {over}" if over else "",
    )


# ── TD-0120 (OQ-07) ───────────────────────────────────────────────────
TC_CODE_RE = re.compile(r"TC-Q([1-4])-(\d{4})-(\d{2})")
HAN_NGACH_RE = re.compile(r"^HAN_NGACH_CHON:\s*(\d+)\s*$", re.MULTILINE)


def _tieu_chi_path(tieu_chi_dir: Path, nam: int, quy: int) -> Path:
    return tieu_chi_dir / f"DR-Q{quy}-{nam}-tieu-chi-chon-y-tuong.md"


def check_td0120_selection_reason_trich_ma_tieu_chi(
    idea_queue_path: Path = DEFAULT_IDEA_QUEUE_PATH,
    tieu_chi_dir: Path = DEFAULT_TIEU_CHI_DIR,
) -> CheckResult:
    """§9c.7.4 bắt viết tiêu chí chọn TRƯỚC khi mở hàng chờ và commit vào
    git; `selection_reason` phải TRÍCH tiêu chí đã commit, không viết mới.

    Spec tự thừa nhận phần "viết bằng cơ chế kinh tế" không thực thi được
    bằng máy. Nhưng phần TRÍCH DẪN thì được — cùng thủ thuật §12d dùng cho
    báo cáo định kỳ ("mọi câu phải trích một con số"). Bốn ca sổ bẩn:

      (a) SELECTED mà `selection_reason` không trích mã `TC-Qx-yyyy-nn` nào
      (b) trích một mã KHÔNG có thật trong file tiêu chí của quý đó
      (c) quý đó CHƯA có file tiêu chí (fail-closed — đúng điều cấm ở
          spec dòng 4935: mở queue trước khi commit tiêu chí)
      (d) quý đó khai `HAN_NGACH_CHON: 0` mà vẫn có dòng SELECTED

    Máy KHÔNG kiểm được câu đó có trung thực không — nhưng chặn được ca dễ
    xảy ra nhất: chọn theo tiêu chí mới nghĩ ra SAU khi đã nhìn thấy đơn.
    """
    entries = _read_jsonl(idea_queue_path)
    selected = [e for e in entries if e.get("status") == "SELECTED" and e.get("selected_at")]
    if not selected:
        return CheckResult("TD-0120", Measured.pending("chưa có ý tưởng nào được CHỌN"))

    violations: list[str] = []
    for e in selected:
        idea_id = e["idea_id"]
        d = datetime.strptime(e["selected_at"], "%Y-%m-%dT%H:%M:%SZ").date()
        nam, quy = _quarter_of(d)
        path = _tieu_chi_path(tieu_chi_dir, nam, quy)
        if not path.exists():
            violations.append(f"{idea_id}: quý {quy}/{nam} CHƯA có file tiêu chí ({path})")
            continue

        noi_dung = path.read_text(encoding="utf-8")
        ma_hop_le = {m.group(0) for m in TC_CODE_RE.finditer(noi_dung)}

        han_ngach = HAN_NGACH_RE.search(noi_dung)
        if han_ngach and int(han_ngach.group(1)) == 0:
            violations.append(
                f"{idea_id}: quý {quy}/{nam} khai HAN_NGACH_CHON: 0 nhưng vẫn có dòng SELECTED"
            )

        ly_do = e.get("selection_reason") or ""
        ma_trich = {m.group(0) for m in TC_CODE_RE.finditer(ly_do)}
        if not ma_trich:
            violations.append(f"{idea_id}: selection_reason không trích mã tiêu chí nào")
        else:
            khong_co_that = ma_trich - ma_hop_le
            if khong_co_that:
                violations.append(
                    f"{idea_id}: trích mã không có trong file tiêu chí quý {quy}/{nam}: "
                    + ", ".join(sorted(khong_co_that))
                )
    return CheckResult(
        "TD-0120", Measured.ok(len(violations) == 0), evidence="; ".join(violations)
    )



# ── TD-0126 (§9c.7.3 + §9c.7.4 ràng buộc 3) ───────────────────────────
def check_td0126_explore_evidence_va_trung_mechanism(
    idea_queue_path: Path = DEFAULT_IDEA_QUEUE_PATH,
) -> CheckResult:
    """Hai ràng buộc trước đây chỉ nằm trong `description` của schema —
    tức là văn bản mô tả, không phải luật máy cưỡng chế được:

      (a) §9c.7.3 — `explore_evidence` BẮT BUỘC có nội dung khi
          `data_source == EXPLORE`. Thiếu nó thì không phân biệt được
          EXPLORE với TOOL_D_RESULTS, mất luôn ranh giới mà trường
          `data_source` sinh ra để giữ (DR-009).

      (b) §9c.7.4 ràng buộc (3) — ý tưởng đã bị loại KHÔNG được nộp lại
          dưới tên khác. Máy so `mechanism` (Jaccard trên từ có nghĩa,
          bỏ dấu) và đòi đơn mới phải KHAI id trùng vào `overlaps_with`.

    Không kiểm được ý tưởng có thật sự trùng nhau về cơ chế hay không —
    nhưng chặn được ca dễ xảy ra nhất: nộp lại nguyên văn dưới tên khác.
    """
    from tool_d.ledger.idea_queue import tim_nghi_trung

    entries = _read_jsonl(idea_queue_path)
    if not entries:
        return CheckResult("TD-0126", Measured.pending("idea_queue rỗng"))

    violations: list[str] = []
    for e in entries:
        if e.get("data_source") == "EXPLORE" and not str(e.get("explore_evidence") or "").strip():
            violations.append(f"{e['idea_id']}: data_source=EXPLORE nhưng thiếu explore_evidence")

    # So từng đơn với các đơn ĐỨNG TRƯỚC nó trong sổ — sổ là nhật ký theo
    # thứ tự thời gian, nên "đơn nộp sau phải khai đơn nộp trước", không
    # ngược lại (nếu không mỗi cặp trùng sẽ bị đếm hai lần).
    for k, e in enumerate(entries):
        truoc = entries[:k]
        da_khai = set(e.get("overlaps_with") or [])
        for idea_id, status, ty_le in tim_nghi_trung(truoc, e.get("mechanism") or ""):
            if idea_id in da_khai:
                continue
            nhan = "ĐÃ BỊ LOẠI" if status == "REJECTED" else status
            violations.append(
                f"{e['idea_id']}: cơ chế trùng {ty_le:.0%} với {idea_id} ({nhan}) "
                "mà không khai vào overlaps_with"
            )

    return CheckResult("TD-0126", Measured.ok(len(violations) == 0), evidence="; ".join(violations))


# ── L-Z26 (OQ-13, §12d.4) ─────────────────────────────────────────────
DEFAULT_PROPOSALS_PATH = Path("registry/param_change_proposals.jsonl")


def check_lz26_de_xuat_doi_tham_so(
    proposals_path: Path = DEFAULT_PROPOSALS_PATH,
    registry_path: Path = DEFAULT_REGISTRY_PATH,
    config_path: Path = DEFAULT_CONFIG_PATH,
    goc: Path = Path("."),
) -> CheckResult:
    """L-Z26 🔴 CRITICAL — mọi thay đổi tham số sau live có: nguồn kích hoạt
    thuộc {HEALTH, GATE_FAIL, CONDITIONAL_UNFREEZE}, chỉ số cụ thể, giá trị
    cụ thể, và 1 trial đã trừ khỏi B3 (spec dòng 4868-4870).

    Dùng lại ĐÚNG bộ luật của cửa ghi (`param_proposals.kiem_de_xuat`) — hai
    lớp không được lệch luật nhau, nếu không lớp nào cũng có thể là lớp sai.
    Cửa ghi bịt lỗ "nộp đơn sai"; phép kiểm này bịt lỗ "sửa sổ bằng tay".

    Thêm một ca chỉ audit làm được, vì nó cần sổ trial: dòng `APPLIED` phải
    trỏ tới một trial CÓ THẬT và đã CONSUMED. Không nhận lời khai suông —
    cùng khuôn nối hai sổ của `check_td0119_so_bien_the_khong_vuot_khai`.
    """
    # Import cục bộ: `param_proposals` import `_read_jsonl` từ chính module
    # này, đặt ở đầu file sẽ thành vòng import.
    from tool_d.ledger.param_proposals import kiem_de_xuat

    entries = _read_jsonl(proposals_path)
    if not entries:
        return CheckResult("L-Z26", Measured.pending("chưa có đề xuất đổi tham số nào"))

    cfg = load_tool_d_config(config_path)
    violations: list[str] = []
    for e in entries:
        violations.extend(kiem_de_xuat(e, cfg=cfg, goc=goc))

    consumed = {
        tid
        for tid, proj in TrialLedger(registry_path).projections().items()
        if proj.state is TrialState.CONSUMED
    }
    for e in entries:
        if e.get("status") != "APPLIED":
            continue
        tid = e.get("trial_id")
        if tid and tid not in consumed:
            violations.append(
                f"{e.get('de_xuat_id')}: APPLIED khai trial_id={tid} nhưng sổ trial không có "
                "trial đó ở trạng thái CONSUMED — lời khai, không phải bằng chứng"
            )

    return CheckResult("L-Z26", Measured.ok(len(violations) == 0), evidence="; ".join(violations))


# ── L-Z27 / L-Z28 (TD-0127, §12d.4) ───────────────────────────────────
def check_lz27_tran_b3(
    registry_path: Path = DEFAULT_REGISTRY_PATH,
    *,
    so_lenh_da_dong: int = 0,
) -> CheckResult:
    """L-Z27 — B3 ≤ 20 tại mọi thời điểm (spec dòng 4871-4872).

    Nửa còn lại của L-Z27 ("B3 chỉ tăng theo `floor(lệnh/25)`, không tăng
    bằng tay") KHÔNG kiểm ở đây, và cố ý như vậy: nó được thi hành bằng
    HÌNH DẠNG API — `TrialLedger.available()/reserve()` không có tham số
    nào nhận một con số ngân sách, chỉ nhận số lệnh rồi tự áp công thức
    `budget.b3_tai_sinh()`. Một phép kiểm lúc audit chỉ phát hiện SAU KHI
    ngân sách đã bị nống; một tham số không tồn tại thì không ai truyền
    vào được. Test canh phần đó nằm ở `TestKhongTheTangBangTay`.
    """
    projections = TrialLedger(registry_path).projections()
    if not projections:
        return CheckResult("L-Z27", Measured.pending("registry rỗng"))

    da_tieu = sum(
        p.contribution
        for p in projections.values()
        if p.budget_line == "B3" and p.state is not TrialState.REFUNDED
    )
    tran = _budget.B3_TRAN_TICH_LUY + _budget.b3_tai_sinh(so_lenh_da_dong)
    return CheckResult(
        "L-Z27",
        Measured.ok(da_tieu <= tran),
        evidence=(
            f"B3 đã dùng={da_tieu}, trần={tran} "
            f"(20 gốc + {_budget.b3_tai_sinh(so_lenh_da_dong)} tái sinh "
            f"từ {so_lenh_da_dong} lệnh đã đóng)"
        ),
    )


def check_lz28_doi_tham_so_dung_diem_quyet_dinh(
    proposals_path: Path = DEFAULT_PROPOSALS_PATH,
    *,
    so_lenh_da_dong: int | None = None,
) -> CheckResult:
    """L-Z28 — không thay đổi tham số nào GIỮA hai điểm quyết định
    (spec dòng 4873-4874; điểm quyết định = mỗi 100 lệnh đóng, §12c.1).

    🔴 FAIL-CLOSED (chốt của chủ dự án 07/09/2026): một đề xuất đã APPLIED
    mà không chứng minh được là rơi đúng điểm quyết định thì BÁO ĐỎ, không
    im lặng cho qua. Im lặng ở đây nghĩa là một tham số đã đổi thật trên
    tiền thật mà không ai kiểm được nó đổi có đúng lúc không.

    🔎 Ngoại lệ "trừ DR-012 Hạng 1" KHÔNG cần ô khai nào: §12c.4 định
    nghĩa Hạng 1 là *"code không làm đúng như spec mô tả"* — đó là LỖI,
    sửa tự do 0 trial, KHÔNG phải đổi tham số, nên nó không bao giờ đi vào
    sổ này (sổ dành cho Hạng 2). Thêm một ô "đây là sửa lỗi" sẽ mở đúng
    cái cửa mà L-Z28 sinh ra để đóng.
    """
    da_ap_dung = [e for e in _read_jsonl(proposals_path) if e.get("status") == "APPLIED"]
    if not da_ap_dung:
        return CheckResult(
            "L-Z28", Measured.pending("chưa có đề xuất nào ở trạng thái APPLIED")
        )

    ma = ", ".join(e["de_xuat_id"] for e in da_ap_dung)
    if so_lenh_da_dong is None:
        return CheckResult(
            "L-Z28",
            Measured.ok(False),
            evidence=(
                f"{len(da_ap_dung)} đề xuất đã APPLIED ({ma}) nhưng CHƯA CHỨNG MINH ĐƯỢC "
                "là rơi đúng điểm quyết định — chưa có nguồn số lệnh đã đóng. "
                "Fail-closed: không chứng minh được thì báo đỏ, không cho qua"
            ),
        )

    dqd = _budget.diem_quyet_dinh_da_qua(so_lenh_da_dong)
    dung_diem = dqd >= 1 and so_lenh_da_dong % _budget.LENH_MOI_DIEM_QUYET_DINH == 0
    if dung_diem:
        evidence = f"{len(da_ap_dung)} đề xuất APPLIED tại điểm quyết định #{dqd} ({so_lenh_da_dong} lệnh)"
    elif dqd < 1:
        evidence = (
            f"{len(da_ap_dung)} đề xuất đã APPLIED ({ma}) khi mới có {so_lenh_da_dong} "
            f"lệnh đóng — CHƯA tới điểm quyết định đầu tiên "
            f"({_budget.LENH_MOI_DIEM_QUYET_DINH} lệnh)"
        )
    else:
        evidence = (
            f"{len(da_ap_dung)} đề xuất đã APPLIED ({ma}) tại {so_lenh_da_dong} lệnh — "
            f"GIỮA điểm quyết định #{dqd} và #{dqd + 1}, đúng thứ L-Z28 cấm "
            "(spec dòng 4952)"
        )
    return CheckResult("L-Z28", Measured.ok(dung_diem), evidence=evidence)


ALL_CHECKS = (
    "check_lz10_registered_before_executed",
    "check_lz11_n_used_le_n_dang_ky",
    "check_lz12_no_duplicate_config_hash_different_outcome",
    "check_lz15_calibrate_params_have_status",
    "check_lz16_idea_queue_filter_and_tool_d_results",
    "check_lz17_budget_a_slots_per_quarter",
    "check_td0119_selected_du_phep_thu",
    "check_td0119_so_bien_the_khong_vuot_khai",
    "check_td0120_selection_reason_trich_ma_tieu_chi",
    "check_td0124_tran_nhap_don_moi_quy",
    "check_lz26_de_xuat_doi_tham_so",
    "check_td0126_explore_evidence_va_trung_mechanism",
    "check_lz27_tran_b3",
    "check_lz28_doi_tham_so_dung_diem_quyet_dinh",
)
