"""TD-0085 — backup lockbox ra NGOÀI git (OQ-08, spec dòng 4002: không có
"lockbox thứ hai" — mất ổ đĩa chứa repo là mất khả năng xác nhận cuối cùng
vĩnh viễn, không thể tải lại vì LOCKBOX chỉ chạm đúng một lần).

Sao chép NGUYÊN VẸN hai thứ, không sửa gì:
    - `lockbox/data/` (OHLCV thật, không commit git — TD-0084)
    - mọi `lockbox_seal_<n>.json` (commit git, nhưng backup vẫn cần vì
      "khôi phục" nghĩa là dựng lại được TOÀN BỘ lockbox từ một bản sao
      duy nhất, không phụ thuộc git + backup rời nhau)

Không sao chép `lockbox_access.log` — sổ đó là NHẬT KÝ TRUY CẬP của repo
gốc (mỗi lần chạm thật), backup không phải một điểm truy cập, không tạo
ra sự kiện truy cập nào (đúng tinh thần DR-014/N8: chỉ ghi sổ khi dùng dữ
liệu để quyết định).
"""

from __future__ import annotations

import shutil
from pathlib import Path


def backup_lockbox(*, source_lockbox_dir: Path, dest_dir: Path) -> Path:
    """Sao chép `source_lockbox_dir` (vd `lockbox/`) sang `dest_dir/lockbox/`.

    Ghi đè bản backup cũ nếu đã có — backup PHẢI phản ánh đúng đủ trạng
    thái seal hiện tại (không phải bất biến như chính seal; append-only
    tuyệt đối là quy tắc của `trial_registry.jsonl`, không phải của một
    bản sao lưu). `source_lockbox_dir` phải tồn tại, không tự tạo rỗng
    rồi coi là "đã backup" (fail-closed, không bịa một bản backup trống).
    """
    if not source_lockbox_dir.is_dir():
        raise FileNotFoundError(f"{source_lockbox_dir} không tồn tại — chưa có gì để backup")

    dest_lockbox = dest_dir / source_lockbox_dir.name
    if dest_lockbox.exists():
        shutil.rmtree(dest_lockbox)
    dest_lockbox.mkdir(parents=True)

    for seal_path in sorted(source_lockbox_dir.glob("lockbox_seal_*.json")):
        shutil.copy2(seal_path, dest_lockbox / seal_path.name)

    src_data = source_lockbox_dir / "data"
    if src_data.is_dir():
        shutil.copytree(src_data, dest_lockbox / "data")

    return dest_lockbox
