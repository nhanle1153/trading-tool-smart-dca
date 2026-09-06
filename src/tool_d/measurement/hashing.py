"""SHA-256 của file dữ liệu — một phần của khối xuất xứ (ràng buộc 0d.5).

Thiếu file KHÔNG được nuốt lỗi im lặng: trả "MISSING" (chuỗi hằng theo đúng
quy ước của spec, dòng 610: `{"oi.parquet": "MISSING"}`), không trả None,
không raise cho lỗi đọc file thường gặp.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

_CHUNK_SIZE = 1 << 20  # 1 MiB — đọc theo khối, không load nguyên file dữ
# liệu thị trường (có thể rất lớn) vào bộ nhớ chỉ để hash.

MISSING = "MISSING"


def sha256_of(path: Path) -> str:
    """Trả sha256 hex (thường) của file, hoặc "MISSING" nếu không đọc được.

    Quy mọi lỗi đọc (không tồn tại, là thư mục, không có quyền, hỏng ổ đĩa
    giữa chừng...) về đúng MỘT giá trị hằng "MISSING" — không phải None,
    không phải chuỗi rỗng, không phải im lặng trả về giá trị cũ.
    """
    try:
        if not path.is_file():
            return MISSING
        digest = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(_CHUNK_SIZE), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return MISSING


def hash_many(paths: dict[str, Path]) -> dict[str, str]:
    """{tên hiển thị: đường dẫn} -> {tên hiển thị: sha256 hex hoặc "MISSING"}.

    Dùng để dựng trường `data_hashes` của khối xuất xứ (0d.5).
    """
    return {name: sha256_of(p) for name, p in paths.items()}
