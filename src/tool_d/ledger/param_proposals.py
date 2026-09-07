"""Cửa GHI của sổ đề xuất đổi tham số — Kênh 2 (§12c.3 + §12d, OQ-13, TD-0125).

Sổ THỨ BA của project, append-only như hai sổ kia. §12c.3 và §12d quy định
rất chặt kênh này, nhưng `L-Z26` 🔴 CRITICAL trước task này có **0 dòng code**
và chưa có sổ ghi đề xuất nào — luật đủ, máy canh không có gì.

🔑 Điểm thiết kế then chốt — vì sao `luan_diem` là MẢNG CÓ CẤU TRÚC:
   §12d.2 BƯỚC 3 đòi *"MỌI câu trong đề xuất phải TRÍCH một con số cụ thể;
   câu không trích được số → gạch bỏ"*. Một ô lý do viết văn xuôi kèm lời
   hứa sẽ trích số là thứ phải có NGƯỜI nhớ luật mới thi hành được — và
   người thì quên, nhất là lúc đang thua. Một mảng bắt buộc `gia_tri` kiểu
   số khiến câu không có số **không biểu diễn được**. Cùng thủ thuật TD-0120
   đã dùng cho `selection_reason`.

🔑 Vì sao MỘT đề xuất chỉ được trỏ MỘT tham số (ca 6):
   Đề xuất cả một *bộ* tham số tối ưu là `hyperopt` viết bằng tiếng Việt —
   cùng hành vi tìm kiếm, nhưng mất phần đếm được số lần thử. Spec chỉ cho
   một tham số, một điểm quyết định. Đây cũng là dấu hiệu **L2 đội lốt L1**
   (§12d.2 dòng 4832: *"phải đổi >1 tham số cùng lúc để sửa"*) — cạm bẫy
   nguy hiểm nhất vì L1 rẻ hơn L2 rất nhiều.

🔑 Vì sao `bao_cao_hash` do máy tự băm từ file, KHÔNG sửa `periodic_report.py`:
   sửa E5 để nó tự in hash sẽ chạm vào *"ĐỔI NỘI DUNG BÁO CÁO = TIÊU 1 TRIAL"*
   (spec dòng 4808) và `FROZEN_CONTENT_HASH` mà TD-0062 đã niêm phong. Người
   nộp lưu đầu ra E5 thành file, trỏ đề xuất vào đó; máy băm và về sau kiểm
   lại — vừa gắn được vào đúng một kỳ, vừa phát hiện được nếu file bị sửa.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema

from tool_d.config.loader import DEFAULT_CONFIG_PATH, ToolDConfig, load_tool_d_config, resolve
from tool_d.ledger.audit_checks import _read_jsonl

DEFAULT_PROPOSALS_PATH = Path("registry/param_change_proposals.jsonl")
SCHEMA_PATH = Path("registry/schemas/param_change_proposal.schema.json")


class ParamProposalError(RuntimeError):
    """Đề xuất không hợp lệ — TỪ CHỐI ghi, sổ không bị đụng tới."""


def _utcnow_iso_seconds() -> str:
    """UTC ISO-8601 tới GIÂY — cùng quy ước `idea_queue.py`, KHÔNG micro giây."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_schema(schema_path: Path = SCHEMA_PATH) -> dict[str, Any]:
    return json.loads(schema_path.read_text(encoding="utf-8"))


def hash_bao_cao(path: Path) -> str:
    """sha256 của một bản báo cáo E5 đã lưu."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def next_de_xuat_id(path: Path = DEFAULT_PROPOSALS_PATH) -> str:
    so = [
        int(e["de_xuat_id"].split("-", 1)[1])
        for e in _read_jsonl(path)
        if isinstance(e.get("de_xuat_id"), str) and e["de_xuat_id"].startswith("PC-")
    ]
    return f"PC-{(max(so) + 1) if so else 1:04d}"


def _tang_cua(dotted: str) -> str:
    return dotted.split(".", 1)[0]


def kiem_de_xuat(
    e: dict[str, Any],
    *,
    cfg: ToolDConfig,
    schema_path: Path = SCHEMA_PATH,
    goc: Path = Path("."),
) -> list[str]:
    """Trả về danh sách vi phạm (rỗng = hợp lệ). KHÔNG raise, KHÔNG ghi gì.

    Tách khỏi `submit_proposal()` để `check_lz26_*` dùng lại được ĐÚNG bộ
    luật đó khi soi sổ đã ghi — hai lớp (cửa ghi và audit) không được phép
    lệch luật nhau, nếu không lớp nào cũng có thể là lớp sai.
    """
    vi_pham: list[str] = []

    # ── Ca 1 — schema ─────────────────────────────────────────────────────
    try:
        jsonschema.validate(e, _load_schema(schema_path))
    except jsonschema.ValidationError as exc:
        cho = "/".join(str(p) for p in exc.absolute_path) or "(gốc)"
        return [f"sai schema tại '{cho}': {exc.message}"]

    ma = e["de_xuat_id"]

    # ── Ca 5 — tham số phải CÓ THẬT trong tool_d_config.yaml ──────────────
    ton_tai = True
    try:
        resolve(cfg, e["tham_so_tro_toi"])
    except KeyError as exc:
        ton_tai = False
        vi_pham.append(f"{ma}: tham_so_tro_toi không có thật trong config — {exc}")

    # ── Ca 2 — Cấp C KHÔNG có ô nhập ──────────────────────────────────────
    if e["cap_tham_so"] == "C":
        vi_pham.append(
            f"{ma}: cap_tham_so=C — §12c.3 'không có quy trình, không có ô nhập'. "
            "Đây là cầu dao, không phải núm vặn."
        )
    if ton_tai and _tang_cua(e["tham_so_tro_toi"]) == "tier_c":
        vi_pham.append(
            f"{ma}: {e['tham_so_tro_toi']} thuộc tier_c — Cấp C, không có ô nhập "
            "(khai cap_tham_so khác cũng không đổi được điều đó)"
        )

    # ── Ca 3+4 — luận điểm phải có, và phải trích SỐ ──────────────────────
    luan_diem = e["luan_diem"]
    if not luan_diem:
        vi_pham.append(f"{ma}: luan_diem rỗng — §12d.2 BƯỚC 3: đề xuất không có số nào → LOẠI TOÀN BỘ")
    for k, ld in enumerate(luan_diem):
        gt = ld.get("gia_tri")
        if not isinstance(gt, (int, float)) or isinstance(gt, bool):
            vi_pham.append(
                f"{ma}: luận điểm #{k + 1} ('{ld.get('chi_so')}') không trích được một con số"
            )

    # ── Ca 6 — MỘT đề xuất, MỘT tham số ───────────────────────────────────
    tro_toi = {ld.get("tham_so_tro_toi") for ld in luan_diem if ld.get("tham_so_tro_toi")}
    if len(tro_toi) > 1:
        vi_pham.append(
            f"{ma}: các luận điểm trỏ tới {len(tro_toi)} tham số khác nhau "
            f"({sorted(tro_toi)}) — đề xuất một BỘ tham số là tìm kiếm tham số hàng loạt "
            "viết bằng tiếng Việt (§0c.2 CẤM), và là dấu hiệu L2 đội lốt L1 (§12d.2 dòng "
            "4832). Một tham số, một điểm quyết định."
        )
    if tro_toi and e["tham_so_tro_toi"] not in tro_toi:
        vi_pham.append(
            f"{ma}: tham_so_tro_toi='{e['tham_so_tro_toi']}' không khớp tham số các luận "
            f"điểm trỏ tới ({sorted(tro_toi)})"
        )

    # ── Ca 7 — báo cáo phải có thật và còn nguyên vẹn ─────────────────────
    bc = goc / e["bao_cao_path"]
    if not bc.exists():
        vi_pham.append(f"{ma}: không thấy bản báo cáo {e['bao_cao_path']}")
    elif hash_bao_cao(bc) != e["bao_cao_hash"]:
        vi_pham.append(
            f"{ma}: sha256 của {e['bao_cao_path']} không khớp bao_cao_hash đã ghi — "
            "báo cáo đã bị sửa sau khi đề xuất được nộp, hoặc đề xuất trỏ nhầm kỳ"
        )

    # ── Ca 8 — APPLIED phải tiêu một trial ────────────────────────────────
    if e["status"] == "APPLIED" and not e["trial_id"]:
        vi_pham.append(
            f"{ma}: status=APPLIED mà trial_id rỗng — §12c.3: mỗi lần đổi tham số "
            "tiêu 1 trial từ B3"
        )

    return vi_pham


def submit_proposal(
    *,
    de_xuat: dict[str, Any],
    path: Path = DEFAULT_PROPOSALS_PATH,
    config_path: Path = DEFAULT_CONFIG_PATH,
    schema_path: Path = SCHEMA_PATH,
    goc: Path = Path("."),
) -> str:
    """Ghi MỘT đề xuất vào cuối sổ. Trả `de_xuat_id`. Raise `ParamProposalError`.

    Điền hộ `de_xuat_id`, `created_at`, và `bao_cao_hash` (băm từ chính file
    người nộp trỏ tới — máy tự tính, người không có đường nhập liệu, đúng
    triết lý DR-014 §3).
    """
    e: dict[str, Any] = dict(de_xuat)
    e.setdefault("trial_id", None)
    e.setdefault("status", "PROPOSED")
    e.setdefault("gia_tri_hien_tai", None)
    e.setdefault("gia_tri_de_xuat", None)
    if not e.get("created_at"):
        e["created_at"] = _utcnow_iso_seconds()
    if not e.get("de_xuat_id"):
        e["de_xuat_id"] = next_de_xuat_id(path)

    bc_path = e.get("bao_cao_path")
    if isinstance(bc_path, str) and bc_path and not e.get("bao_cao_hash"):
        bc = goc / bc_path
        if not bc.exists():
            # Báo đúng nguyên nhân gốc. Nếu để rơi xuống schema, người nộp sẽ
            # thấy "bao_cao_hash: None is not of type 'string'" — đúng về kỹ
            # thuật nhưng trỏ sai chỗ cần sửa.
            raise ParamProposalError(
                f"Không thấy bản báo cáo {bc_path} — đề xuất phải gắn vào ĐÚNG MỘT bản "
                "báo cáo có thật (§12d.2 BƯỚC 2: chỉ đọc đầu ra periodic_report.py). "
                "Chạy E5 và lưu đầu ra thành file trước, rồi trỏ bao_cao_path vào đó."
            )
        e["bao_cao_hash"] = hash_bao_cao(bc)

    if any(x.get("de_xuat_id") == e["de_xuat_id"] for x in _read_jsonl(path)):
        raise ParamProposalError(f"{e['de_xuat_id']} đã có trong sổ — sổ append-only, không ghi đè.")

    vi_pham = kiem_de_xuat(e, cfg=load_tool_d_config(config_path), schema_path=schema_path, goc=goc)
    if vi_pham:
        raise ParamProposalError("Đề xuất bị LOẠI — không ghi gì cả:\n  - " + "\n  - ".join(vi_pham))

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(e, ensure_ascii=False) + "\n")
    return e["de_xuat_id"]
