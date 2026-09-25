"""TD-0419 — tạo thư mục phiên IDEA/CHỌN sạch (DR-009) bằng một lệnh. Chạy bằng Python trên máy (không cần Docker):

    python scripts/tao_phien_sach.py --tieu-chi docs/decisions/DR-Q1-2027-tieu-chi-chon-y-tuong.md

Tuỳ chọn `--dich <thư mục>` (mặc định theo `docs/phien-sach/cau-hinh.json`, có ngày). Mã thoát: 0 xong · 3 DỪNG vì dò
thấy số liệu Tool D (không ghi gì) · 2 lỗi cấu hình/đầu vào. Không phải entrypoint đo (không chạm dữ liệu thị trường,
không ghi sổ) — nằm ngoài `entrypoints/` (L-Z36).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from tool_d.ops.phien_sach import PhienSachError, tao_phien_sach  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Tạo thư mục phiên IDEA/CHỌN sạch (DR-009)")
    ap.add_argument("--tieu-chi", required=True, help="file tiêu chí chọn của quý, đường dẫn tương đối trong repo")
    ap.add_argument("--dich", type=Path, default=None, help="thư mục đích (mặc định theo cấu hình, có ngày)")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # cửa sổ lệnh Windows mặc định cp1252, không in được ✅/🛑
    try:
        dich, vi_pham = tao_phien_sach(REPO, tieu_chi=args.tieu_chi, dich=args.dich)
    except PhienSachError as exc:
        print(f"🛑 {exc}")
        return 2
    if vi_pham:
        print(f"🛑 DỪNG — dò thấy {len(vi_pham)} dòng có dấu hiệu số liệu Tool D; KHÔNG ghi gì vào {dich}:")
        for v in vi_pham:
            print(f"   {v.file}:{v.dong}  [{v.mau}]  {v.trich}")
        return 3
    print(f"✅ Đã tạo {dich}")
    print("Bước tiếp theo:")
    print(f"  1. Trong VS Code, mở thư mục {dich} (KHÔNG phải repo) và mở một phiên Claude Code MỚI.")
    print("  2. Dán câu ở mục 1 của LOI-MO-DAU.md vào phiên đó.")
    print("  3. Bật script canh (tự nộp/chọn): mục 2 của LOI-MO-DAU.md — PowerShell riêng, không qua Claude.")
    print(f"     python scripts/canh_phien_sach.py --thu-muc \"{dich}\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
