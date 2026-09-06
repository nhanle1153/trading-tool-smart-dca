"""Niêm phong lockbox — cơ chế DR-011 (spec dòng 3305-3320).

    1. Dữ liệu lockbox nằm ở thư mục RIÊNG, ngoài data-dir mặc định
       của Freqtrade — [[ARCHITECTURE.md]] mục 3.1 ("không chạm được ở
       tầng hệ điều hành", docker-compose không mount lockbox/data/ vào
       service backtest thường).
    2. Ghi SHA-256 của toàn bộ file dữ liệu + mốc thời gian vào
       `lockbox_seal_<n>.json`, commit vào git, KHÔNG SỬA.
    4. Sau lần chạm đầu tiên, đoạn đó coi như ĐÃ TIÊU.

Module này canh bởi **L-Z14**: SHA-256 dữ liệu lockbox phải khớp seal ở
MỌI lần kiểm. `write_seal()` áp "commit, KHÔNG sửa" bằng cách từ chối ghi
đè file đã tồn tại — cùng tinh thần append-only tuyệt đối của `N8`/
`ledger/registry.py`, nhưng ở mức "một file, ghi một lần" thay vì "một
sổ, mỗi dòng một sự kiện" (vì mỗi ĐOẠN niêm phong — gốc hoặc gia hạn
INCONCLUSIVE — là một file `lockbox_seal_<n>.json` riêng, spec dòng
3355-3360: gia hạn niêm phong đoạn MỚI thành seal MỚI, không sửa seal cũ).

🔴 D0-PRE CHƯA có dữ liệu lockbox thật (N2 — cấm chạm dữ liệu trước khi
D0-PRE đóng). Module này chỉ dựng CƠ CHẾ; TD-0084 (Khối 8, sau gate) mới
gọi `write_seal()` trên dữ liệu thật lần đầu.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tool_d.measurement.hashing import hash_many


@dataclass(frozen=True)
class Seal:
    """Một đoạn niêm phong. `segment` đếm từ 1 (spec dòng 3876-3880: 1 đoạn
    gốc + tối đa 2 gia hạn = tối đa segment 3).

    `date_range` giữ nguyên các khoá spec đòi cho đoạn gốc (T0/T1/T2/T3,
    dòng 3799) hoặc đoạn gia hạn (chỉ phần đoạn mới, dòng 3355-3357) — nghĩa
    cụ thể của các mốc là việc của TD-0084 khi niêm phong dữ liệu thật; ở
    đây chỉ giữ nguyên dict để ghi/đọc lại, không ép cấu trúc.
    """

    segment: int
    sealed_at: str
    date_range: dict[str, str]
    data_hashes: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "segment": self.segment,
            "sealed_at": self.sealed_at,
            "date_range": dict(self.date_range),
            "data_hashes": dict(self.data_hashes),
        }


def build_seal(
    *,
    segment: int,
    sealed_at: str,
    date_range: dict[str, str],
    data_files: dict[str, Path],
) -> Seal:
    """Dựng một khối niêm phong — hash TOÀN BỘ file trong `data_files`
    (tên hiển thị -> đường dẫn thật), dùng `hash_many` sẵn có (0d.5) để
    "MISSING" là quy ước lỗi DUY NHẤT, nhất quán với khối provenance."""
    return Seal(
        segment=segment,
        sealed_at=sealed_at,
        date_range=dict(date_range),
        data_hashes=hash_many(data_files),
    )


def write_seal(seal: Seal, path: Path) -> None:
    """Ghi file niêm phong. TỪ CHỐI nếu `path` đã tồn tại — "commit vào
    git, KHÔNG sửa" (spec dòng 3312) nghĩa là seal của một đoạn là bất
    biến. Gia hạn tạo FILE MỚI (`lockbox_seal_2.json`, `_3.json`...),
    không bao giờ sửa file cũ.
    """
    if path.exists():
        raise FileExistsError(
            f"{path} đã tồn tại — seal bất biến, không được ghi đè "
            "(spec dòng 3312). Gia hạn INCONCLUSIVE phải tạo file mới "
            "lockbox_seal_<n+1>.json, không sửa file cũ."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(seal.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def verify_seal(seal_path: Path, data_dir: Path) -> list[str]:
    """L-Z14 — tính lại SHA-256 từng file mà seal liệt kê, so với giá trị
    đã ghi lúc niêm phong. Trả về danh sách lỗi; RỖNG = khớp hoàn toàn.

    Chỉ hash đúng tập tên đã liệt kê trong seal (seal là danh sách ĐÓNG) —
    không quét thêm file khác trong `data_dir`, không đoán file nào "chắc
    cũng phải kiểm".
    """
    if not seal_path.is_file():
        return [f"không đọc được file seal: {seal_path}"]
    try:
        recorded: dict[str, Any] = json.loads(seal_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [f"seal hỏng JSON: {e}"]

    recorded_hashes = recorded.get("data_hashes")
    if not isinstance(recorded_hashes, dict) or not recorded_hashes:
        return [f"seal thiếu hoặc rỗng khoá 'data_hashes': {seal_path}"]

    actual = hash_many({name: data_dir / name for name in recorded_hashes})
    errors: list[str] = []
    for name, expected_hash in sorted(recorded_hashes.items()):
        got = actual.get(name)
        if got != expected_hash:
            errors.append(f"{name}: seal ghi {expected_hash!r}, đo được {got!r}")
    return errors


def discover_seals(lockbox_dir: Path) -> list[Path]:
    """Liệt kê mọi `lockbox_seal_<n>.json` trong `lockbox_dir`, sắp theo
    tên (tức theo số đoạn). Thư mục chưa tồn tại -> danh sách rỗng."""
    if not lockbox_dir.is_dir():
        return []
    return sorted(lockbox_dir.glob("lockbox_seal_*.json"))


def verify_all_seals(lockbox_dir: Path, data_dir: Path) -> list[str]:
    """H17 (spec dòng 4348) — "Kiểm SHA-256 lockbox mỗi lần khởi động
    pipeline". Kiểm TOÀN BỘ đoạn niêm phong đang có trong `lockbox_dir`.

    **0 seal là hợp lệ theo mặc định** — ở D0-PRE (trước TD-0084), chưa có
    đoạn nào được niêm phong; "không có gì để xác nhận" không phải lỗi.
    Dùng chung cho E4 (`--verify-seal`, TD-0071) và sẽ dùng lại ở đầu
    E1/E2/E3 (TD-0072) — một hàm duy nhất, không viết lại logic quét seal
    ở nhiều nơi.

    Lỗi trả về có tiền tố tên file seal để phân biệt được đoạn nào lệch
    khi có nhiều đoạn cùng lúc.
    """
    errors: list[str] = []
    for seal_path in discover_seals(lockbox_dir):
        for e in verify_seal(seal_path, data_dir):
            errors.append(f"{seal_path.name}: {e}")
    return errors
