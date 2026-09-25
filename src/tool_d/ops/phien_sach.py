"""TD-0419 — dựng thư mục phiên IDEA/CHỌN sạch (DR-009) bằng MỘT lệnh, thay cho chép tay.

Chỉ dùng thư viện chuẩn (chạy bằng Python trên máy qua `scripts/tao_phien_sach.py`, không cần Docker). Mọi lựa chọn nằm
ở `docs/phien-sach/cau-hinh.json`; module này chỉ thi hành:

  1. chép đúng các file khai trong `file_chep` + file tiêu chí chọn của quý (tham số bắt buộc);
  2. trích các đoạn spec theo MỐC TIÊU ĐỀ (không theo số dòng — số dòng trôi, mốc tiêu đề thì không);
  3. dựng hàng chờ ý tưởng RÚT GỌN — chỉ các trường đối chiếu trùng (bài học MT-77: bản đầy đủ lẫn số đo Tool D);
  4. điền mẫu `README`/`LOI-MO-DAU`;
  5. DÒ mọi file sẽ chép sang bằng `mau_cam`; dính một dòng ⇒ DỪNG, xoá thư mục tạm, không để lại gì.

Fail-closed: thư mục đích đã tồn tại ⇒ từ chối (không ghi đè một phiên sạch đang dùng); mốc tiêu đề thiếu/trùng ⇒ từ
chối; file khai mà không có ⇒ từ chối.
"""

from __future__ import annotations

import json
import re
import shutil
import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path, PureWindowsPath
from typing import Any


class PhienSachError(RuntimeError):
    """Không dựng được thư mục sạch — TỪ CHỐI, không đoán."""


@dataclass(frozen=True)
class ViPham:
    file: str
    dong: int
    mau: str
    trich: str


def doc_cau_hinh(repo: Path) -> dict[str, Any]:
    return json.loads((repo / "docs/phien-sach/cau-hinh.json").read_text(encoding="utf-8"))


def trich_doan(van_ban: str, bat_dau: str, ket_thuc: str) -> str:
    """Đoạn từ dòng bắt đầu bằng `bat_dau` tới TRƯỚC dòng bắt đầu bằng `ket_thuc`. Mỗi mốc phải xuất hiện ĐÚNG MỘT lần."""
    dong = van_ban.split("\n")
    i = [k for k, d in enumerate(dong) if d.startswith(bat_dau)]
    j = [k for k, d in enumerate(dong) if d.startswith(ket_thuc)]
    if len(i) != 1 or len(j) != 1 or not i[0] < j[0]:
        raise PhienSachError(f"mốc tiêu đề {bat_dau!r} → {ket_thuc!r}: thấy {len(i)}/{len(j)} lần hoặc sai thứ tự")
    return "\n".join(dong[i[0] : j[0]]).rstrip("\n")


def rut_gon_hang_cho(van_ban_jsonl: str, giu_truong: list[str]) -> str:
    """Mỗi dòng sổ ý tưởng → chỉ giữ các trường khai (thiếu trường thì `null`, không bịa)."""
    ra = []
    for d in van_ban_jsonl.splitlines():
        if d.strip():
            e = json.loads(d)
            ra.append(json.dumps({k: e.get(k) for k in giu_truong}, ensure_ascii=False))
    return "\n".join(ra) + ("\n" if ra else "")


def do_vi_pham(ten_file: str, van_ban: str, mau_cam: list[str]) -> list[ViPham]:
    bieu_thuc = [(m, re.compile(m)) for m in mau_cam]
    ra = []
    for k, dong in enumerate(van_ban.split("\n"), start=1):
        for m, bt in bieu_thuc:
            if bt.search(dong):
                ra.append(ViPham(ten_file, k, m, dong.strip()[:120]))
    return ra


def dung_noi_dung(repo: Path, cau_hinh: dict[str, Any], *, tieu_chi: str, dich: Path, ngay: date) -> dict[str, str]:
    """`{tên file trong thư mục sạch: nội dung}` — chưa ghi gì ra đĩa."""
    noi_dung: dict[str, str] = {}
    danh_sach = list(cau_hinh["file_chep"]) + [tieu_chi]
    for rel in danh_sach:
        p = repo / rel
        if not p.is_file():
            raise PhienSachError(f"file khai trong cấu hình không có: {rel}")
        noi_dung[p.name] = p.read_text(encoding="utf-8")
    ts = cau_hinh["trich_spec"]
    spec = (repo / ts["nguon"]).read_text(encoding="utf-8")
    doan = [trich_doan(spec, a, b) for a, b in ts["doan"]]
    noi_dung[ts["dich"]] = (
        f"<!-- Trích NGUYÊN VĂN {ts['nguon']} ngày {ngay.isoformat()} theo mốc tiêu đề (scripts/tao_phien_sach.py). -->\n\n"
        + "\n\n---\n\n".join(doan)
        + "\n"
    )
    hc = cau_hinh["hang_cho"]
    noi_dung[hc["dich"]] = rut_gon_hang_cho((repo / hc["nguon"]).read_text(encoding="utf-8"), hc["giu_truong"])
    dien = {
        "{ngay}": ngay.isoformat(),
        "{tieu_chi}": Path(tieu_chi).name,
        "{thu_muc_windows}": str(PureWindowsPath(dich)),
    }
    for nguon, ten in cau_hinh["mau"].items():
        van_ban = (repo / nguon).read_text(encoding="utf-8")
        for k, v in dien.items():
            van_ban = van_ban.replace(k, v)
        noi_dung[ten] = van_ban
    return noi_dung


def tao_phien_sach(repo: Path, *, tieu_chi: str, dich: Path | None = None, ngay: date | None = None) -> tuple[Path, list[ViPham]]:
    """Dựng thư mục sạch. Trả `(thư mục, [])` khi xong; `(thư mục dự kiến, vi phạm)` khi DỪNG vì dò thấy số liệu — lúc đó
    KHÔNG có gì được ghi ở đích."""
    cau_hinh = doc_cau_hinh(repo)
    ngay = ngay or date.today()
    dich = dich or Path(cau_hinh["thu_muc_dich_mac_dinh"].format(ngay=ngay.isoformat()))
    if dich.exists():
        raise PhienSachError(f"{dich} đã tồn tại — không ghi đè một thư mục phiên sạch (có thể đang dùng)")
    noi_dung = dung_noi_dung(repo, cau_hinh, tieu_chi=tieu_chi, dich=dich, ngay=ngay)
    vi_pham = [v for ten, vb in sorted(noi_dung.items()) for v in do_vi_pham(ten, vb, cau_hinh["mau_cam"])]
    if vi_pham:
        return dich, vi_pham
    tam = Path(tempfile.mkdtemp(prefix="phien_sach_"))
    try:
        for ten, vb in noi_dung.items():
            (tam / ten).write_text(vb, encoding="utf-8", newline="\n")
        dich.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(tam), str(dich))
    finally:
        if tam.exists():
            shutil.rmtree(tam, ignore_errors=True)
    return dich, []
