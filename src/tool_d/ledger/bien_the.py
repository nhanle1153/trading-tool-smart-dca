"""TD-0396 — `DR-BIEN-THE-01`: định danh một BIẾN THỂ (= một cấu hình) của ứng viên `IQ-xxxx`.

`so_bien_the` ở cửa CHỌN đếm cấu hình phân biệt, không đếm suất. Định danh cấu hình = sha256 của đúng những khoá
`tool_d_config.yaml` mà chiến lược của slot đọc — danh sách khai trong DR thiết kế D0 (khối `DR-BIEN-THE-01:KHOA`,
đã commit), KHÔNG phải `config_hash` cả file: file đổi vì tham số ZA hay việc vận hành thì ứng viên không đổi gì vẫn
bị đếm thêm biến thể (DR §2 điều 3).

Fail-closed: không có khối, nhiều hơn một khối cho cùng slot, khối hỏng, DR chưa commit ⇒ `BienTheError`.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from tool_d.config.loader import ToolDConfig, resolve
from tool_d.dr015.cong_d35 import _da_commit

THU_MUC_DR = Path("docs/decisions")
_KHOI_KHOA = re.compile(
    r"<!-- DR-BIEN-THE-01:KHOA:BEGIN -->\s*(?:```json)?\s*(\{.*?\})\s*(?:```)?\s*<!-- DR-BIEN-THE-01:KHOA:END -->",
    re.S,
)
_HASH = re.compile(r"^[0-9a-f]{64}$")


class BienTheError(ValueError):
    """Không định danh được biến thể — TỪ CHỐI, không đoán."""


def la_bien_the_hash(gia_tri: object) -> bool:
    return isinstance(gia_tri, str) and bool(_HASH.match(gia_tri))


def doc_khoa_bien_the(hypothesis_slot: str, *, repo_dir: Path = Path(".")) -> tuple[str, ...]:
    """Danh sách khoá của slot, đọc từ khối `DR-BIEN-THE-01:KHOA` trong `docs/decisions/*.md` đã commit.

    Đúng MỘT khối trên toàn thư mục mang `slot` này — hai DR cùng khai một slot là hai nguồn sự thật (N1)."""
    thay: list[tuple[Path, list[str]]] = []
    for p in sorted((repo_dir / THU_MUC_DR).glob("*.md")):
        for tho in _KHOI_KHOA.findall(p.read_text(encoding="utf-8")):
            try:
                khoi = json.loads(tho)
            except json.JSONDecodeError as e:
                # Khối hỏng mà nhắc tới slot đang tra ⇒ từ chối, không đoán. Khối hỏng của slot KHÁC (vd khối VÍ DỤ
                # `"IQ-xxxx"` trong chính `DR-BIEN-THE-01` §3) không nói gì về slot này ⇒ bỏ qua.
                if hypothesis_slot in tho:
                    raise BienTheError(f"{p.name}: khối `DR-BIEN-THE-01:KHOA` của {hypothesis_slot} hỏng: {e}") from e
                continue
            if isinstance(khoi, dict) and khoi.get("slot") == hypothesis_slot:
                thay.append((p, khoi.get("khoa")))
    if len(thay) != 1:
        raise BienTheError(
            f"{hypothesis_slot}: cần ĐÚNG MỘT khối `DR-BIEN-THE-01:KHOA` trong {THU_MUC_DR.as_posix()}/, thấy {len(thay)}"
        )
    p, khoa = thay[0]
    ly_do = _da_commit(p.relative_to(repo_dir), repo_dir)
    if ly_do is not None:
        raise BienTheError(f"{hypothesis_slot}: DR khai khoá — {ly_do}")
    if (
        not isinstance(khoa, list)
        or not khoa
        or not all(isinstance(k, str) and k.startswith("tier_") for k in khoa)
        or len(set(khoa)) != len(khoa)
    ):
        raise BienTheError(f"{p.name}: `khoa` phải là danh sách khoá `tier_*` không rỗng, không trùng; nhận {khoa!r}")
    return tuple(khoa)


def tinh_bien_the_hash(cfg: ToolDConfig, khoa: Sequence[str]) -> str:
    """sha256 của JSON chuẩn hoá `{khoa: giá trị}` (`sort_keys`, không khoảng trắng). Khoá không có ⇒ `KeyError`."""
    gia_tri: dict[str, Any] = {k: resolve(cfg, k) for k in khoa}
    van_ban = json.dumps(gia_tri, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    return hashlib.sha256(van_ban.encode("utf-8")).hexdigest()
