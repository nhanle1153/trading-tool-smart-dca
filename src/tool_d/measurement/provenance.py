"""Khối xuất xứ — ràng buộc 0d.5 (spec dòng 597-616). Canh bởi L-Z40.

Bảy khoá spec đòi: params_source, params_effective, git_sha,
reproducible_from_sha, data_hashes, cache_mode, guard_passed. Thêm khoá thứ
tám `runtime_image_digest` (quyết định MT-07 trong back-end-note.md): vì ta
chạy trong Docker, phiên bản Freqtrade nằm trong image chứ không nằm trong
git — không ghi digest thì sau này không truy lại được "lúc đó chạy
Freqtrade bản nào". Không phá L-Z40 vì test chỉ đòi ĐỦ 7 khoá, không cấm
khoá thứ 8.

Ghi vào 4 nơi (spec + ARCHITECTURE.md mục 2): khối `provenance` trong mỗi
sự kiện của `trial_registry.jsonl`, `runs/<trial_id>/provenance.json`, đầu
báo cáo `periodic_report`, và mỗi bản ghi `lockbox_access.log`.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

from tool_d.measurement.gitinfo import get_git_info
from tool_d.measurement.hashing import hash_many

# Đúng 7 khoá spec đòi (dòng 597-616). Đây là tập kiểm của L-Z40 — không
# thêm runtime_image_digest vào đây, để test "đủ 7 khoá" không bị nhầm với
# "đủ 8 khoá" khi spec chỉ đòi 7.
REQUIRED_PROVENANCE_KEYS: frozenset[str] = frozenset(
    {
        "params_source",
        "params_effective",
        "git_sha",
        "reproducible_from_sha",
        "data_hashes",
        "cache_mode",
        "guard_passed",
    }
)


@dataclass(frozen=True)
class Provenance:
    params_source: Literal["yaml", "params_file", "env"]
    params_effective: dict[str, Any]
    git_sha: str
    reproducible_from_sha: bool
    data_hashes: dict[str, str]
    cache_mode: Literal["none"]
    guard_passed: bool
    # Khoá thứ 8, xem docstring module. None khi chưa xác định được digest
    # (VD chạy ngoài Docker khi soạn thảo — không dùng làm bằng chứng, N7).
    runtime_image_digest: str | None = field(default=None)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_provenance(
    *,
    params_source: str,
    params_effective: Mapping[str, Any],
    repo_dir: Path,
    data_files: Mapping[str, Path],
    cache_mode: str,
    guard_passed: bool,
    runtime_image_digest: str | None = None,
) -> Provenance:
    """Dựng một khối xuất xứ đầy đủ.

    `get_git_info` có thể raise `GitInfoError` — KHÔNG bắt lỗi đó ở đây và
    âm thầm trả "UNKNOWN". Nơi gọi (entrypoint) phải để nó dừng chương
    trình; một bản ghi không có git_sha thật không đáng để tồn tại.
    """
    git_info = get_git_info(repo_dir)
    return Provenance(
        params_source=params_source,  # type: ignore[arg-type]
        params_effective=dict(params_effective),
        git_sha=git_info.sha,
        reproducible_from_sha=git_info.is_clean,
        data_hashes=hash_many(dict(data_files)),
        cache_mode=cache_mode,  # type: ignore[arg-type]
        guard_passed=guard_passed,
        runtime_image_digest=runtime_image_digest,
    )


def validate_provenance(d: Mapping[str, Any]) -> list[str]:
    """Kiểm một khối xuất xứ (dict thô, VD đọc từ JSONL) theo L-Z40.

    Trả về danh sách lỗi; rỗng = hợp lệ cho gate. Kiểm cả cấu trúc (đủ 7
    khoá) lẫn nội dung (params_source == "yaml", guard_passed == true,
    cache_mode == "none", git_sha không phải giá trị lính canh) — spec
    dòng 681-683 gộp cả ba điều kiện làm một: "Thiếu → bản ghi KHÔNG HỢP
    LỆ cho gate".
    """
    errors: list[str] = []

    missing = REQUIRED_PROVENANCE_KEYS - set(d.keys())
    for key in sorted(missing):
        errors.append(f"thiếu khoá bắt buộc: {key}")
    if missing:
        # Thiếu khoá thì các kiểm nội dung bên dưới vô nghĩa (KeyError) —
        # dừng sớm, đã đủ để kết luận "không hợp lệ".
        return errors

    if d.get("params_source") != "yaml":
        errors.append(
            "params_source phải là 'yaml' để hợp lệ cho gate, nhận: "
            f"{d.get('params_source')!r}"
        )
    if d.get("guard_passed") is not True:
        errors.append(f"guard_passed phải là True, nhận: {d.get('guard_passed')!r}")
    if d.get("cache_mode") != "none":
        errors.append(f"cache_mode phải là 'none', nhận: {d.get('cache_mode')!r}")
    git_sha = d.get("git_sha")
    if not git_sha or git_sha == "UNKNOWN":
        errors.append(f"git_sha không hợp lệ: {git_sha!r}")

    return errors


def cache_key(prov: Provenance) -> str:
    """Khoá cache cho WFO tự viết (0d.3, dòng 572-575): gộp params_hash +
    code_sha + data_hash thành một khoá duy nhất.

    Chưa dùng ở D0-PRE (H3-D orchestrator là việc của D3) — chốt định dạng
    sớm ở đây để khi D3 tới lượt không phải sửa ngược provenance.py.
    """
    payload = json.dumps(
        {
            "params_effective": prov.params_effective,
            "git_sha": prov.git_sha,
            "data_hashes": prov.data_hashes,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
