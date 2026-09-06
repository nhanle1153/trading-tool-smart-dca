"""Sổ truy cập lockbox — DR-011 điểm 3 (spec dòng 3313) + **L-Z13** (§9c.6).

    L-Z13 🆕 lockbox_access.log có ĐÚNG 0 bản ghi cho tới sau D9;
          🔴 v7 sửa: sau đó ĐÚNG 1 bản ghi CHO MỖI ĐOẠN NIÊM PHONG, tối
          đa 3 đoạn (1 gốc + 2 gia hạn INCONCLUSIVE, DR-011). Mỗi bản ghi
          phải trỏ tới một `lockbox_seal_<n>.json` KHÁC NHAU với hash
          khác nhau. Hai bản ghi cùng seal = vi phạm.

Định dạng: JSONL append-only, cùng triết lý sổ sự kiện của `N8`
(`ledger/registry.py`) — mỗi dòng một lần truy cập, không sửa/xoá dòng cũ.

`seal_file_hash` là SHA-256 NỘI DUNG file seal (không phải `data_hashes`
bên trong nó) — biến "một seal khác" (spec) thành một con số máy so được:
seal gia hạn LUÔN là file mới với nội dung mới, nên hash luôn khác, và hai
lần truy cập cùng một đoạn (đọc lại đúng file cũ) luôn bị bắt.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Spec dòng 3358: "TỐI ĐA 2 LẦN GIA HẠN" = 1 đoạn gốc + 2 gia hạn = 3 đoạn.
MAX_SEGMENTS = 3


@dataclass(frozen=True)
class AccessRecord:
    accessed_at: str
    reason: str
    config_hash: str
    seal_path: str
    seal_file_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "accessed_at": self.accessed_at,
            "reason": self.reason,
            "config_hash": self.config_hash,
            "seal_path": self.seal_path,
            "seal_file_hash": self.seal_file_hash,
        }


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_access_record(
    *, reason: str, config_hash: str, seal_path: Path, accessed_at: str | None = None
) -> AccessRecord:
    """Dựng một bản ghi truy cập từ file seal ĐÃ niêm phong. `accessed_at`
    mặc định là giờ hệ thống (UTC) — truyền tường minh trong test để kết
    quả tái lập được.
    """
    content = seal_path.read_text(encoding="utf-8")
    return AccessRecord(
        accessed_at=accessed_at or _utcnow_iso(),
        reason=reason,
        config_hash=config_hash,
        seal_path=str(seal_path),
        seal_file_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
    )


def read_access_log(log_path: Path) -> list[dict[str, Any]]:
    """Đọc toàn bộ sổ. File chưa tồn tại -> sổ rỗng (chưa từng truy cập),
    không phải lỗi — đúng trạng thái "0 bản ghi trước D9"."""
    if not log_path.is_file():
        return []
    records = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


def validate_before_d9(records: list[dict[str, Any]]) -> list[str]:
    """L-Z13, nửa "trước D9": ĐÚNG 0 bản ghi."""
    if records:
        return [f"{len(records)} bản ghi tồn tại trước D9 — lockbox đã bị chạm sớm"]
    return []


def validate_access_log(records: list[dict[str, Any]]) -> list[str]:
    """L-Z13, nửa "sau D9": tối đa `MAX_SEGMENTS` bản ghi, mỗi bản ghi một
    `seal_path` khác nhau VÀ một `seal_file_hash` khác nhau.

    Kiểm THUẦN trên dữ liệu đã đọc — không I/O — để dựng ca giả trong test
    không cần ghi file thật.
    """
    errors: list[str] = []
    if len(records) > MAX_SEGMENTS:
        errors.append(
            f"{len(records)} bản ghi > tối đa {MAX_SEGMENTS} đoạn niêm phong "
            "(1 gốc + 2 gia hạn INCONCLUSIVE, spec dòng 3358)"
        )

    seen_paths: dict[Any, int] = {}
    seen_hashes: dict[Any, int] = {}
    for i, r in enumerate(records):
        path = r.get("seal_path")
        h = r.get("seal_file_hash")
        if path in seen_paths:
            errors.append(
                f"bản ghi {i} và {seen_paths[path]} cùng seal_path {path!r} "
                "— hai lần chạm cùng một đoạn niêm phong (L-Z13)"
            )
        else:
            seen_paths[path] = i
        if h in seen_hashes:
            errors.append(
                f"bản ghi {i} và {seen_hashes[h]} cùng seal_file_hash {h!r} "
                "— hai bản ghi cùng seal (L-Z13)"
            )
        else:
            seen_hashes[h] = i
    return errors


def append_access_record(log_path: Path, record: AccessRecord) -> None:
    """Ghi thêm MỘT dòng — append-only tuyệt đối, không mở file ở chế độ
    ghi đè, không sửa dòng đã ghi.

    Fail-closed: tự kiểm bằng `validate_access_log` trên "sổ + dòng sắp
    ghi" TRƯỚC khi ghi — từ chối tạo ra một dòng vi phạm rồi để việc phát
    hiện dồn sang lần kiểm sau.
    """
    would_be = read_access_log(log_path) + [record.to_dict()]
    errors = validate_access_log(would_be)
    if errors:
        raise ValueError(f"Từ chối ghi sổ truy cập lockbox — vi phạm L-Z13: {errors}")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")
