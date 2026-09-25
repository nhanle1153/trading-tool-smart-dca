"""TD-0422 — canh thư mục phiên IDEA/CHỌN sạch: tự nộp đơn, chỉ chọn khi chủ dự án gõ xác nhận. Chạy bằng Python trên
máy, để cửa sổ mở suốt buổi làm ý tưởng (Ctrl+C để dừng):

    python scripts/canh_phien_sach.py --thu-muc C:\\Users\\ADMIN\\phien-y-tuong-sach-2026-09-25

Phiên sạch đặt file vào `<thư mục>\\cho-nop\\` KHI chủ dự án bảo nộp: `don-N.yaml` ⇒ tự nộp; `to-chon.yaml` ⇒ hỏi
`CHON` ở cửa sổ này rồi mới chọn. Kết quả đã lọc (chỉ dòng ✅/🛑) ghi vào `<thư mục>\\ket-qua-nop.txt` cho phiên sạch
tự đọc. Không phải entrypoint đo — nằm ngoài `entrypoints/` (L-Z36).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from tool_d.ops.canh_phien_sach import (  # noqa: E402
    FILE_KET_QUA,
    THU_MUC_CHO,
    CanhPhienSachError,
    Viec,
    doc_da_xu_ly,
    ghi_da_xu_ly,
    kiem_thu_muc,
    lenh_docker,
    quet,
    xu_ly,
)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Canh thư mục phiên IDEA/CHỌN sạch (TD-0422)")
    ap.add_argument("--thu-muc", type=Path, required=True, help="thư mục do scripts/tao_phien_sach.py tạo")
    ap.add_argument("--chu-ky", type=float, default=3.0, help="giây giữa hai lần quét (mặc định 3)")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)  # cp1252 không in được ✅/🛑; in ngay từng dòng
    try:
        thu_muc = kiem_thu_muc(args.thu_muc, REPO)
    except CanhPhienSachError as exc:
        print(f"🛑 {exc}")
        return 2
    (thu_muc / THU_MUC_CHO).mkdir(exist_ok=True)

    def chay(viec: Viec) -> tuple[str, int]:
        print(f"… đang chạy {viec.ten} (Docker, khoảng 10–30 giây)")
        # stderr bỏ đi như `2>$null` của lệnh tay; stdout KHÔNG in ra — chỉ dòng đã lọc được in/ghi.
        kq = subprocess.run(lenh_docker(REPO, thu_muc, viec), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            cwd=REPO, check=False)
        return kq.stdout.decode("utf-8", errors="replace"), kq.returncode

    da_xu_ly = doc_da_xu_ly(thu_muc)  # bền qua khởi động lại: nộp lại cùng một đơn là tiêu thêm trần 10 đơn/quý
    bo_qua: dict[str, str] = {}  # chỉ trong lần chạy này: to-chon.yaml chưa được xác nhận
    lan_truoc: dict[str, str] = {}
    print(f"👀 Đang canh {thu_muc / THU_MUC_CHO} — kết quả ghi vào {thu_muc / FILE_KET_QUA}. Ctrl+C để dừng.")
    try:
        while True:
            viec, lan_truoc = quet(thu_muc, {**da_xu_ly, **bo_qua}, lan_truoc)
            for v in viec:
                ket_qua, da_chay = xu_ly(v, thu_muc=thu_muc, chay=chay, hoi=input)
                print(f"{v.ten}: {ket_qua}")
                if da_chay:
                    da_xu_ly[v.ten] = v.bam
                    ghi_da_xu_ly(thu_muc, da_xu_ly)
                else:
                    bo_qua[v.ten] = v.bam
                    print("   (hỏi lại khi to-chon.yaml đổi nội dung, hoặc khi bật lại cửa sổ canh)")
            time.sleep(args.chu_ky)
    except KeyboardInterrupt:
        print("Đã dừng canh.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
