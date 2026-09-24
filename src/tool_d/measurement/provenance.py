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
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field, fields
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


# Tập của TOOL D = 7 khoá spec + khoá thứ 8 (MT-07). CỐ Ý tách khỏi
# `REQUIRED_PROVENANCE_KEYS`: hằng số kia phải giữ đúng nghĩa "tập spec §0d.5
# đòi" (dòng 597-616 liệt kê đúng 7). Gộp hai thứ vào một tên là đúng lớp trôi
# ngữ nghĩa mà dự án đã dính nhiều lần — "spec đòi" và "Tool D đòi thêm" là hai
# phát biểu khác nhau và phải kiểm được riêng.
KHOA_XUAT_XU_TOOL_D: frozenset[str] = REQUIRED_PROVENANCE_KEYS | {
    "runtime_image_digest"
}

# Dấu hiệu "đang chạy trong ảnh của chính project này": file do
# `docker/Dockerfile` nướng vào lúc build. Không có nó ⇒ không phải ảnh ta ghim.
DAU_HIEU_ANH = Path("/opt/freqtrade_source_commit.txt")

# `FROM <repo>@sha256:<64 hex>` — digest ghim ở ĐÚNG MỘT chỗ: docker/Dockerfile.
_RE_FROM_DIGEST = re.compile(r"^FROM\s+\S+@(sha256:[0-9a-f]{64})\s*$", re.MULTILINE)
_RE_DIGEST_HOP_LE = re.compile(r"sha256:[0-9a-f]{64}")


class ImageDigestError(RuntimeError):
    """Không xác định được digest ảnh đang chạy.

    CỐ Ý là exception chứ không phải giá trị trả về: N6 cấm giá trị lính canh
    (`""`, `"UNKNOWN"`), và một khối xuất xứ khai sai môi trường còn tệ hơn một
    khối không tồn tại — nó trông như bằng chứng.
    """


def doc_runtime_image_digest(
    repo_dir: Path,
    *,
    dau_hieu_anh: Path | None = None,
) -> str:
    """Đọc digest ảnh đang chạy — khoá xuất xứ thứ 8 (MT-07). FAIL-CLOSED.

    Hai vế, cả hai đều cần:

    1. **Đang chạy trong ảnh của project** — `DAU_HIEU_ANH` do `docker/Dockerfile`
       nướng vào lúc build. Chạy trên host (soạn thảo) thì file này không có, và
       theo N7 lần chạy đó không phải bằng chứng nên KHÔNG được ghi xuất xứ.
    2. **Digest ghim** — đọc dòng `FROM ...@sha256:...` của `docker/Dockerfile`.

    Vế 1 một mình không đủ (không nói ảnh nào); vế 2 một mình không đủ (chỉ nói
    *ghim* gì, không nói đang *chạy* gì). Hai vế cùng đúng thì mới kết luận được.
    """
    dau_hieu = DAU_HIEU_ANH if dau_hieu_anh is None else dau_hieu_anh
    if not dau_hieu.is_file():
        raise ImageDigestError(
            f"không thấy {dau_hieu} — không chạy trong ảnh Docker của project. "
            "Theo N7, lần chạy ngoài Docker không phải bằng chứng, nên không "
            "được ghi khối xuất xứ."
        )
    dockerfile = repo_dir / "docker" / "Dockerfile"
    if not dockerfile.is_file():
        raise ImageDigestError(f"không thấy {dockerfile} để đọc digest ghim")
    khop = _RE_FROM_DIGEST.findall(dockerfile.read_text(encoding="utf-8"))
    if len(khop) != 1:
        raise ImageDigestError(
            f"{dockerfile}: cần ĐÚNG MỘT dòng `FROM ...@sha256:<64 hex>`, "
            f"tìm thấy {len(khop)}"
        )
    return khop[0]


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


def validate_provenance_tool_d(d: Mapping[str, Any]) -> list[str]:
    """Kiểm theo chuẩn TOOL D = `validate_provenance()` + khoá thứ 8 (MT-07).

    Tách khỏi `validate_provenance()` CÓ CHỦ ĐÍCH: hàm kia thi hành spec §0d.5
    (đúng 7 khoá) và phải giữ nguyên nghĩa đó — N1, spec là nguồn sự thật. Hàm
    này thi hành thêm một ràng buộc **của riêng dự án**, và người đọc phải phân
    biệt được hai thứ khi một trong hai đổi.

    🔴 `null` bị TỪ CHỐI, không phải bỏ qua: đó chính là trạng thái khoá thứ 8
    nằm suốt từ MT-07 (06/09/2026) tới TD-0229 — khai có khoá, giá trị rỗng,
    không ai kiểm. Một khoá xuất xứ mà `null` cũng qua được thì nó không canh gì.
    """
    errors = list(validate_provenance(d))
    if "runtime_image_digest" not in d:
        errors.append("thiếu khoá bắt buộc (Tool D, MT-07): runtime_image_digest")
        return errors
    digest = d.get("runtime_image_digest")
    if not isinstance(digest, str) or not _RE_DIGEST_HOP_LE.fullmatch(digest):
        errors.append(
            "runtime_image_digest phải là 'sha256:<64 hex>' — N6 cấm giá trị "
            f"lính canh và cấm null, nhận: {digest!r}"
        )
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
            # TD-0229 — khoá thứ 8 vào khoá cache. Đây là chỗ DUY NHẤT biến
            # "đã ghi là phải cẩn thận" thành "không làm sai được": đổi ảnh
            # Docker ⇒ khoá cache đổi ⇒ kết quả cũ KHÔNG thể bị dùng lại cho
            # môi trường mới. Trước TD-0229, đổi `docker/Dockerfile:21` là một
            # thao tác im lặng hoàn toàn — suite xanh, cache vẫn trúng.
            "runtime_image_digest": prov.runtime_image_digest,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def van_tay_lan_chay(
    *,
    provenance: Mapping[str, Any],
    config_hash: str,
    code_commit: str,
    bam_thay_doi_chua_commit: str,
    dataset: str,
    direction: str,
    param_under_test: str,
    param_value: Any,
) -> str:
    """TD-0380 (`DR-DINH-DANH-01` §4.1) — định danh LẦN CHẠY, khác định danh CẤU HÌNH (`config_hash`).

    Gộp đủ năm yếu tố quyết định một kết quả: tham số (`config_hash` — toàn bộ yaml, vì `params_effective` của E1 chỉ
    chứa khoá bị ghi đè) · mã (`code_commit` + băm thay đổi chưa commit) · dữ liệu · phạm vi (`dataset`, `direction`,
    `param_under_test`/`param_value` — với E3 đó chính là arm) · môi trường. Phần `params_effective + git_sha +
    data_hashes + runtime_image_digest` đi qua `cache_key()` (DR §4.1: dùng lại, KHÔNG sửa — đổi nó là làm lạnh cache
    WFO). `runtime_image_digest` là `None` ở dòng E1/E3; digest ghim nằm ở `docker/Dockerfile`, tức đã được mã phủ.
    """
    payload = json.dumps(
        {
            # Chỉ lấy đúng các trường của `Provenance`: khối xuất xứ sai hình dạng phải để schema ở cửa ghi
            # (`TrialLedger._append`, TD-0150) báo lỗi, không để một `TypeError` ở đây giành báo trước.
            "cache_key": cache_key(Provenance(**{f.name: provenance.get(f.name) for f in fields(Provenance)})),
            "config_hash": config_hash,
            "code_commit": code_commit,
            "bam_thay_doi_chua_commit": bam_thay_doi_chua_commit,
            "dataset": dataset,
            "direction": direction,
            "param_under_test": param_under_test,
            "param_value": param_value,
        },
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
