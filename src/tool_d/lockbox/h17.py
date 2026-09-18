"""H17 ở service CHE lockbox — `DR-LOCKBOX-02` (TD-0316).

H17 (spec `:4348`) gộp hai phép canh hai mối nguy khác nhau: lockbox bị ĐỌC ngoài quy trình
(ngăn bằng cách ly, ghi dấu bằng sổ truy cập `L-Z13`) và lockbox bị SỬA (băm SHA-256 `L-Z14`).
Ở service chạy pipeline (`freqtrade`, `tests`) dữ liệu lockbox bị che CÓ CHỦ ĐÍCH
(ARCHITECTURE 3.1), nên `L-Z14` ở đây FAIL mọi lần về định nghĩa — trước DR này E1/E2/E3 thoát
89 ở chính service chúng chạy. Băm dữ liệu vì thế chuyển về E4 ở service `lockbox`
(`verify_all_seals()`); module này là phần H17 CHẠY ĐƯỢC ở service che:

1. **Cách ly còn hiệu lực** — tiến trình KHÔNG đọc được file dữ liệu lockbox nào. Thử ĐỌC THẬT
   từng file seal liệt kê, và quét thư mục dữ liệu — không chỉ hỏi "thư mục có trống không".
2. **File seal không bị sửa** — mọi `lockbox_seal_*.json` được git theo dõi, sạch, và chỉ
   được commit ĐÚNG MỘT LẦN (`DR-D0PRE-07` §6: *"commit, không sửa"*).
3. **Sổ truy cập** — 🔴 KHAI THẲNG: trước khi `TD-0274` nối đường GHI cho lần chạm, sổ trống
   không chứng minh gì (trống vì chưa ai ghi, không phải vì không ai chạm). Kiểm để có sẵn chỗ,
   KHÔNG được đếm là một tấm chắn.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from tool_d.lockbox.access_log import read_access_log, validate_access_log, validate_before_d9
from tool_d.lockbox.seal import discover_seals
from tool_d.measurement.gitinfo import GitInfoError, _run_git

#: Dải 86–107 đã có chủ toàn repo (đo 18/09/2026). "Cách ly vỡ" là sự cố KHÁC hẳn "seal lệch":
#: nó nghĩa là pipeline có thể nhìn trộm lockbox — nên không dùng chung mã 89.
EXIT_LOCKBOX_CACH_LY_VO = 108

TEN_SO_TRUY_CAP = "lockbox_access.log"
#: Liệt kê tối đa bấy nhiêu file đọc được trong thông báo — vỡ cách ly thì 1 file là đủ để dừng.
TOI_DA_LIET_KE = 5


@dataclass(frozen=True)
class KetQuaH17:
    cach_ly_vo: tuple[str, ...]
    seal_bi_sua: tuple[str, ...]
    so_truy_cap: tuple[str, ...]

    @property
    def dat(self) -> bool:
        return not (self.cach_ly_vo or self.seal_bi_sua or self.so_truy_cap)


def _ten_file_trong_seal(lockbox_dir: Path) -> set[str]:
    ten: set[str] = set()
    for sp in discover_seals(lockbox_dir):
        try:
            ten |= set(json.loads(sp.read_text(encoding="utf-8")).get("data_hashes") or {})
        except (OSError, ValueError):
            continue  # seal hỏng là việc của kiem_seal_khong_bi_sua / E4, không phải của phép cách ly
    return ten


def kiem_cach_ly(lockbox_dir: Path, data_dir: Path) -> list[str]:
    """File dữ liệu lockbox mà tiến trình này ĐỌC ĐƯỢC. Rỗng = cách ly còn hiệu lực."""
    doc_duoc: set[Path] = set()
    for ten in _ten_file_trong_seal(lockbox_dir):
        f = data_dir / ten
        try:
            with open(f, "rb") as fh:
                fh.read(1)
            doc_duoc.add(f)
        except OSError:
            pass
    if data_dir.is_dir():
        doc_duoc |= {f for f in data_dir.rglob("*") if f.is_file()}
    if not doc_duoc:
        return []
    ds = sorted(str(f) for f in doc_duoc)
    them = f" … (+{len(ds) - TOI_DA_LIET_KE})" if len(ds) > TOI_DA_LIET_KE else ""
    return [f"đọc được {len(ds)} file dữ liệu lockbox từ tiến trình pipeline: {ds[:TOI_DA_LIET_KE]}{them}"]


def kiem_seal_khong_bi_sua(repo_dir: Path, lockbox_dir: Path) -> list[str]:
    """Seal chưa commit / có thay đổi / bị commit lại. Không đọc được git ⇒ lỗi (fail-closed)."""
    loi: list[str] = []
    for sp in discover_seals(lockbox_dir):
        rel = os.path.relpath(sp, repo_dir)
        # `status` TRƯỚC, `log` chỉ khi đã sạch: seal chưa commit thì `git log` có thể lỗi trước
        # (repo chưa commit nào) và che mất nguyên nhân thật — vẫn fail-closed nhưng nói sai lý do.
        try:
            trang_thai = _run_git(["status", "--porcelain", "--", rel], repo_dir).strip()
            if trang_thai:
                loi.append(f"{rel}: có thay đổi chưa commit hoặc chưa được git theo dõi ({trang_thai})")
                continue
            so_commit = len(_run_git(["log", "--format=%H", "--", rel], repo_dir).split())
        except GitInfoError as exc:
            loi.append(f"{rel}: không đọc được git — không chứng minh được seal chưa bị sửa: {exc}")
            continue
        if so_commit != 1:
            loi.append(
                f"{rel}: được commit {so_commit} lần — seal chỉ được commit ĐÚNG MỘT LẦN "
                "(DR-D0PRE-07 §6, 'commit, không sửa')"
            )
    return loi


def _da_qua_d9_5(runtime_state_path: Path) -> bool:
    try:
        st = json.loads(runtime_state_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return st.get("d9_5_complete") is True


def kiem_so_truy_cap(lockbox_dir: Path, runtime_state_path: Path) -> list[str]:
    so = lockbox_dir / TEN_SO_TRUY_CAP
    if not so.exists():
        return []
    ban_ghi = read_access_log(so)
    return validate_access_log(ban_ghi) if _da_qua_d9_5(runtime_state_path) else validate_before_d9(ban_ghi)


def kiem_h17(
    *,
    repo_dir: Path = Path("."),
    lockbox_dir: Path,
    data_dir: Path,
    runtime_state_path: Path = Path("registry/runtime_state.json"),
) -> KetQuaH17:
    return KetQuaH17(
        cach_ly_vo=tuple(kiem_cach_ly(lockbox_dir, data_dir)),
        seal_bi_sua=tuple(kiem_seal_khong_bi_sua(repo_dir, lockbox_dir)),
        so_truy_cap=tuple(kiem_so_truy_cap(lockbox_dir, runtime_state_path)),
    )


def in_va_ma_thoat(kq: KetQuaH17, *, ma_that_bai: int) -> int | None:
    """In kết quả cho E1/E2/E3; trả mã thoát nếu phải dừng, `None` nếu qua."""
    if kq.cach_ly_vo:
        print("🛑 H17 — CÁCH LY LOCKBOX ĐÃ VỠ: tiến trình pipeline đọc được dữ liệu lockbox (DR-LOCKBOX-02 §2):")
        for e in kq.cach_ly_vo:
            print(f"  - {e}")
        print("  Pipeline không bao giờ cần dữ liệu lockbox; lần chạm duy nhất đi qua E4. Soát docker-compose.")
        return EXIT_LOCKBOX_CACH_LY_VO
    if not kq.dat:
        print("🛑 H17 FAIL — lockbox (DR-LOCKBOX-02):")
        for e in (*kq.seal_bi_sua, *kq.so_truy_cap):
            print(f"  - {e}")
        return ma_that_bai
    return None
