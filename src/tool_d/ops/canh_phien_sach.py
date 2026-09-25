"""TD-0422 — canh thư mục phiên IDEA/CHỌN sạch: tự nộp đơn, chỉ chọn khi chủ dự án gõ xác nhận.

Thay việc chủ dự án copy-dán lệnh PowerShell ở mục 2 `LOI-MO-DAU.md` và dán tay dòng ✅/🛑 về phiên sạch. Ranh giới
`DR-009` giữ nguyên:
  • phiên sạch KHÔNG chạy lệnh nào — nó chỉ đặt file vào `cho-nop/` khi chủ dự án bảo nộp (bản nháp ngoài `cho-nop/`
    không bao giờ bị nộp: mỗi lần nộp, kể cả bị từ chối, tính vào trần 10 đơn/quý);
  • thứ quay về thư mục phiên sạch chỉ là dòng đã LỌC bằng đúng luật của khối PowerShell cũ (`loc_ket_qua`) — báo cáo
    kiểm tra sổ in sau dòng ✅ có thể chứa số Tool D, không bao giờ được ghi ra;
  • `to-chon.yaml` (một lượt, không lấy lại được) chỉ chạy khi chủ dự án gõ đúng `CHON` ở cửa sổ canh.
Không phải entrypoint đo (không chạm dữ liệu thị trường; ghi sổ qua E6 như lệnh tay).
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

THU_MUC_CHO = "cho-nop"
FILE_KET_QUA = "ket-qua-nop.txt"
FILE_DA_XU_LY = ".canh-da-xu-ly.json"
TEN_TO_CHON = "to-chon.yaml"
MAU_DON = re.compile(r"^don-\d+\.yaml$")
#: Cùng luật với khối PowerShell `LOI-MO-DAU.md` mục 2 — dòng đầu phải là dòng ghi sổ thành công.
MAU_THANH_CONG = re.compile(r"IQ-\d{4}.*registry/idea_queue\.jsonl")
MA_TU_CHOI = 96  # EXIT_DON_TU_CHOI của entrypoints/trial_ledger_audit.py
XAC_NHAN_CHON = "CHON"
KHONG_NHAN_RA = "KHONG NHAN RA KET QUA (ma thoat {ma}) - KHONG ghi gi them; chu du an bao phien trong repo."


class CanhPhienSachError(ValueError):
    """Thư mục không phải thư mục phiên sạch, hoặc nằm trong repo — từ chối canh."""


@dataclass(frozen=True)
class Viec:
    ten: str  # tên file trong `cho-nop/`
    bam: str  # sha256 nội dung — sửa file sau khi 🛑 là một việc mới
    la_chon: bool


def loc_ket_qua(stdout: str, ma_thoat: int) -> str:
    """Thứ DUY NHẤT được ghi về phiên sạch. Thành công ⇒ chỉ dòng đầu; từ chối (96, mở đầu 🛑) ⇒ lời từ chối;
    còn lại ⇒ một câu cảnh báo, không lọt chữ nào của output."""
    dong = stdout.splitlines()
    if dong and MAU_THANH_CONG.search(dong[0]):
        return dong[0].strip()
    if ma_thoat == MA_TU_CHOI and dong and dong[0].startswith("🛑"):
        return stdout.strip()
    return KHONG_NHAN_RA.format(ma=ma_thoat)


def kiem_thu_muc(thu_muc: Path, repo: Path) -> Path:
    thu_muc = thu_muc.resolve()
    if not (thu_muc / "LOI-MO-DAU.md").is_file() or not (thu_muc / "README.md").is_file():
        raise CanhPhienSachError(f"{thu_muc} không phải thư mục do scripts/tao_phien_sach.py tạo")
    if thu_muc == repo.resolve() or repo.resolve() in thu_muc.parents:
        raise CanhPhienSachError(f"{thu_muc} nằm trong repo — phiên sạch phải ở ngoài repo (DR-009)")
    return thu_muc


def doc_da_xu_ly(thu_muc: Path) -> dict[str, str]:
    p = thu_muc / FILE_DA_XU_LY
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}


def ghi_da_xu_ly(thu_muc: Path, da_xu_ly: dict[str, str]) -> None:
    (thu_muc / FILE_DA_XU_LY).write_text(json.dumps(da_xu_ly, ensure_ascii=False, indent=1), encoding="utf-8")


def quet(thu_muc: Path, da_xu_ly: dict[str, str], lan_truoc: dict[str, str]) -> tuple[list[Viec], dict[str, str]]:
    """File sẵn sàng = băm KHÔNG đổi giữa hai lần quét (đã ghi xong) và khác băm đã xử lý. Trả (việc, băm lần này)."""
    cho = thu_muc / THU_MUC_CHO
    bam_nay: dict[str, str] = {}
    if cho.is_dir():
        for f in sorted(cho.iterdir()):
            if f.is_file() and (MAU_DON.match(f.name) or f.name == TEN_TO_CHON):
                bam_nay[f.name] = hashlib.sha256(f.read_bytes()).hexdigest()
    viec = [
        Viec(ten, bam, ten == TEN_TO_CHON)
        for ten, bam in bam_nay.items()
        if lan_truoc.get(ten) == bam and da_xu_ly.get(ten) != bam
    ]
    viec.sort(key=lambda v: (v.la_chon, int(re.sub(r"\D", "", v.ten) or 0)))  # nộp đơn trước, chọn sau cùng
    return viec, bam_nay


def lenh_docker(repo: Path, thu_muc: Path, viec: Viec) -> list[str]:
    co = "--chon-y-tuong" if viec.la_chon else "--nop-y-tuong"
    return [
        "docker", "compose", "-f", str(repo / "docker" / "docker-compose.yml"), "run", "--rm",
        "-v", f"{thu_muc}:/don:ro", "freqtrade", "entrypoints/trial_ledger_audit.py",
        co, f"/don/{THU_MUC_CHO}/{viec.ten}",
    ]


def xu_ly(
    viec: Viec,
    *,
    thu_muc: Path,
    chay: Callable[[Viec], tuple[str, int]],
    hoi: Callable[[str], str],
    bay_gio: Callable[[], datetime] = datetime.now,
) -> tuple[str, bool]:
    """Chạy một việc, ghi dòng đã lọc vào `ket-qua-nop.txt`. Trả (dòng đó, đã chạy lệnh chưa). `chay` trả (stdout,
    mã thoát). Chủ dự án không xác nhận chọn ⇒ không chạy, (…, False): người gọi chỉ bỏ qua tới khi file đổi."""
    da_chay = True
    if viec.la_chon:
        tra_loi = hoi(f"Chọn ý tưởng theo {THU_MUC_CHO}/{viec.ten}? Chỉ có MỘT lượt, không lấy lại được. "
                      f"Gõ {XAC_NHAN_CHON} để chọn, gì khác để bỏ qua: ")
        if tra_loi.strip() != XAC_NHAN_CHON:
            ket_qua, da_chay = "⏸ Chủ dự án CHƯA xác nhận — chưa chọn, sổ không đổi.", False
        else:
            ket_qua = loc_ket_qua(*chay(viec))
    else:
        ket_qua = loc_ket_qua(*chay(viec))
    with (thu_muc / FILE_KET_QUA).open("a", encoding="utf-8") as f:
        f.write(f"{bay_gio():%Y-%m-%d %H:%M:%S}  {viec.ten}\n{ket_qua}\n\n")
    return ket_qua, da_chay
