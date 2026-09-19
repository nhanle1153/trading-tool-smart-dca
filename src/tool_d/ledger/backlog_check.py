"""TD-0331 (OQ-15) — phép kiểm BACKLOG: khoá 🔒 quên đóng và cột trạng thái lệch ghi chú.

Sự cố sinh ra file này (19/09/2026): `TD-0319`/`TD-0320` còn 🔒 khoảng 10 giờ sau khi code
đã commit (`ac04799`, `b76ae3d`), vì phiên giữ khoá đóng `TD-0321` rồi bỏ quên hai dòng phụ
thuộc. Cùng họ: `TD-0184` ghi 🔓 ở cột trạng thái trong khi ghi chú cuối dòng là ⏸ (`DR-IQ-01`
§1) — người chỉ đọc cột trạng thái sẽ chọn nhầm một việc đang bị dừng. Không lớp canh nào thấy,
vì hai bảng (`TASKS.md`, lịch sử git) chưa từng được đặt cạnh nhau.

Ba loại phát hiện, MỌI loại chỉ là CẢNH BÁO:

  1. ``khoa_co_commit``: dòng 🔒 mà `git log` đã có commit mang tiêu đề bắt đầu bằng mã việc
     (quy ước `TD-xxxx: …`; commit khoá/hoàn tất bắt đầu bằng `TASKS.md:` nên tự loại).
  2. ``trang_thai_lan``: ô trạng thái mang ≥ 2 ký hiệu (*"🔓 ⏸"*) — không thể đúng cả hai.
  3. ``nghi_lech_tam_dung``: ô trạng thái KHÔNG có ⏸ (cũng không ✅/❌) nhưng dòng mang cụm
     *"⏸ TẠM DỪNG"* — cụm quy ước của `DR-IQ-01` §6 ("ghi ⏸ + mốc").

🔴 **Vì sao KHÔNG nối vào `run_audit()` hay cổng đóng:**
  • Loại 1 KHÔNG phải lỗi khi đứng một mình: việc nhiều chặng (`TD-0189`) có commit mã việc
    giữa chừng trong khi vẫn 🔒 đúng luật. Coi nó là lỗi chặn cổng thì chặn oan.
  • Nối vào `run_audit()` đổi tổng số phép kiểm mà nhiều test đang ghim.
  Nên đây là một báo cáo (cờ `--kiem-backlog` trên E6), người đọc quyết định — không phải test canh.

⚠️ Loại 3 là dấu hiệu CÚ PHÁP đo tính chất NGỮ NGHĨA — đúng thứ bài học 08/09 cảnh báo (*"đừng
đo tính chất ngữ nghĩa bằng dấu hiệu cú pháp"*). Vì thế nó tên là "nghi lệch", chỉ dựa vào một cụm
quy ước có chủ đích, và dễ có báo động giả (một dòng chỉ NHẮC tới việc đang tạm dừng). Loại 1 và 2
là so khớp cơ học, không có vấn đề đó.

Không ghi file nào; chỉ đọc `TASKS.md` và chạy `git log`. Không gọi mạng.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

KY_HIEU = ("🔓", "🔒", "✅", "⏸", "❌")
LOAI_KHOA_CO_COMMIT = "khoa_co_commit"
LOAI_TRANG_THAI_LAN = "trang_thai_lan"
LOAI_NGHI_LECH_TAM_DUNG = "nghi_lech_tam_dung"

_RE_MA = re.compile(r"^TD-\d{4}$")
_RE_TAM_DUNG = re.compile(r"⏸\s*\**\s*TẠM DỪNG")
_RE_DAU_TACH = re.compile(r"^\|[\s:|-]+\|$")

DEFAULT_TASKS_PATH = Path("TASKS.md")


class BacklogError(RuntimeError):
    """Không đọc được nguồn (git, file) — phần liên quan là "chưa đo được", không phải "sạch"."""


@dataclass(frozen=True)
class DongBacklog:
    ma: str
    trang_thai: str
    o_khac: tuple[str, ...]  # các ô còn lại (tên việc, phụ thuộc, ghi chú…)
    so_dong: int  # số dòng (1-based) trong TASKS.md


@dataclass(frozen=True)
class VanDe:
    loai: str
    ma: str
    so_dong: int
    mo_ta: str


def tach_o(dong: str) -> list[str]:
    """Tách một dòng bảng markdown thành các ô. Dấu ``|`` trong cặp dấu ngoặc ngược và dấu
    ``\\|`` đã escape KHÔNG phải ranh giới ô — cùng luật đếm cột của `test_td0233`."""
    s = dong.strip()
    if s.startswith("|"):
        s = s[1:]
    o: list[str] = []
    hien: list[str] = []
    trong_ma = False
    i = 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s) and s[i + 1] == "|":
            hien.append("|")
            i += 2
            continue
        if c == "`":
            trong_ma = not trong_ma
        if c == "|" and not trong_ma:
            o.append("".join(hien).strip())
            hien = []
        else:
            hien.append(c)
        i += 1
    cuoi = "".join(hien).strip()
    if cuoi:
        o.append(cuoi)
    return o


def _la_bang_backlog(tieu_de: list[str]) -> bool:
    """Bảng việc: ô đầu là "Mã…" và ô thứ ba là "TT" (bảng changelog, bảng giai đoạn… không thoả)."""
    return len(tieu_de) >= 3 and tieu_de[0].startswith("Mã") and tieu_de[2].strip() == "TT"


def doc_backlog(tasks_text: str) -> list[DongBacklog]:
    """Mọi dòng việc `TD-xxxx` trong CÁC BẢNG BACKLOG của `TASKS.md`."""
    dong = tasks_text.splitlines()
    ket: list[DongBacklog] = []
    trong_bang_backlog = False
    for i, d in enumerate(dong):
        if not d.startswith("|"):
            trong_bang_backlog = False
            continue
        if i + 1 < len(dong) and _RE_DAU_TACH.match(dong[i + 1].strip()) and "---" in dong[i + 1]:
            trong_bang_backlog = _la_bang_backlog(tach_o(d))  # dòng tiêu đề của một bảng mới
            continue
        if _RE_DAU_TACH.match(d.strip()) or not trong_bang_backlog:
            continue
        o = tach_o(d)
        if len(o) >= 3 and _RE_MA.match(o[0]):
            ket.append(DongBacklog(ma=o[0], trang_thai=o[2], o_khac=tuple(o[1:2] + o[3:]), so_dong=i + 1))
    return ket


def _ky_hieu_trong(o: str) -> list[str]:
    return [k for k in KY_HIEU if k in o]


def tim_van_de(
    dong_backlog: list[DongBacklog], tieu_de_commit: list[tuple[str, str]] | None
) -> list[VanDe]:
    """``tieu_de_commit`` là ``[(hash, tiêu đề)]``; ``None`` = không đọc được git ⇒ bỏ loại 1."""
    van_de: list[VanDe] = []
    for d in dong_backlog:
        ky = _ky_hieu_trong(d.trang_thai)
        if len(ky) >= 2:
            van_de.append(VanDe(LOAI_TRANG_THAI_LAN, d.ma, d.so_dong, f"ô trạng thái lẫn {' '.join(ky)}: {d.trang_thai!r}"))
        if "🔒" in d.trang_thai and tieu_de_commit is not None:
            mau = re.compile(rf"^{re.escape(d.ma)}(?!\d)")
            trung = [(h, t) for h, t in tieu_de_commit if mau.match(t)]
            if trung:
                ds = "; ".join(f"{h} {t[:60]}" for h, t in trung[:3])
                them = f" (+{len(trung) - 3})" if len(trung) > 3 else ""
                van_de.append(VanDe(LOAI_KHOA_CO_COMMIT, d.ma, d.so_dong, f"🔒 nhưng đã có {len(trung)} commit mã việc: {ds}{them}"))
        if not any(k in d.trang_thai for k in ("⏸", "✅", "❌")):
            if any(_RE_TAM_DUNG.search(o) for o in d.o_khac):
                van_de.append(VanDe(LOAI_NGHI_LECH_TAM_DUNG, d.ma, d.so_dong, f"trạng thái {d.trang_thai!r} nhưng dòng mang cụm '⏸ TẠM DỪNG'"))
    return van_de


def doc_tieu_de_commit(root: Path = Path(".")) -> list[tuple[str, str]]:
    """``[(hash ngắn, tiêu đề)]`` mọi commit, mới nhất trước. Lỗi ⇒ `BacklogError`."""
    try:
        kq = subprocess.run(
            ["git", "-c", "safe.directory=*", "-C", str(root), "log", "--format=%h%x09%s"],
            capture_output=True, text=True, encoding="utf-8", timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as loi:
        raise BacklogError(f"không chạy được git: {loi}") from loi
    if kq.returncode != 0:
        raise BacklogError(f"git log lỗi (rc={kq.returncode}): {kq.stderr.strip()[:200]}")
    ket: list[tuple[str, str]] = []
    for dong in kq.stdout.splitlines():
        h, _, t = dong.partition("\t")
        if h:
            ket.append((h, t))
    return ket


def bao_cao(
    tasks_path: Path = DEFAULT_TASKS_PATH,
    root: Path = Path("."),
    *,
    tasks_text: str | None = None,
    tieu_de_commit: list[tuple[str, str]] | None | str = "doc_git",
) -> tuple[int, str]:
    """Báo cáo văn bản + mã: 0 = không có cảnh báo, 1 = có (chỉ để CON NGƯỜI đọc, không chặn gì).

    ``tasks_text`` / ``tieu_de_commit`` cho phép test truyền dữ liệu (ảnh chụp lịch sử); mặc
    định đọc `TASKS.md` và `git log` thật. ``tieu_de_commit=None`` = coi như không có git."""
    if tasks_text is None:
        tasks_text = Path(tasks_path).read_text(encoding="utf-8")
    ghi_chu_git = ""
    if isinstance(tieu_de_commit, str):  # "doc_git"
        try:
            tieu_de_commit = doc_tieu_de_commit(root)
        except BacklogError as loi:
            tieu_de_commit = None
            ghi_chu_git = f"⏳ Loại 1 (khoá 🔒 có commit mã việc) CHƯA ĐO ĐƯỢC — {loi}"
    dong = doc_backlog(tasks_text)
    van_de = tim_van_de(dong, tieu_de_commit)
    dong_bao = [f"backlog: đọc {len(dong)} dòng việc; {len(van_de)} cảnh báo (chỉ báo, không chặn gì)"]
    if ghi_chu_git:
        dong_bao.append(ghi_chu_git)
    ten = {
        LOAI_KHOA_CO_COMMIT: "🔒 quên đóng?",
        LOAI_TRANG_THAI_LAN: "trạng thái lẫn",
        LOAI_NGHI_LECH_TAM_DUNG: "nghi lệch tạm dừng",
    }
    for v in sorted(van_de, key=lambda x: (x.loai, x.so_dong)):
        dong_bao.append(f"  [{ten[v.loai]}] {v.ma} (TASKS.md:{v.so_dong}): {v.mo_ta}")
    if van_de:
        dong_bao.append(
            "  ↳ Loại '🔒 quên đóng?' là BÌNH THƯỜNG với việc nhiều chặng — kiểm tay trước khi đóng "
            "(N12 mục 3, 7f); loại 'nghi lệch' là heuristic, có thể báo động giả."
        )
    return (1 if van_de else 0), "\n".join(dong_bao)
