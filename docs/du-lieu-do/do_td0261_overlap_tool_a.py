"""TD-0261 (`DR-D1-04`) — H14: overlap rổ T1 Tool D với pool Tool A + chụp số trial Tool A TẠI LÚC ĐO, áp DR-007 máy móc.

0 trial. Không đọc dữ liệu thị trường: chỉ hai danh sách mã và một số đếm. Mọi định nghĩa ở `DR-D1-04` §2, commit trước
phép đo (`aa130b1`). Repo Tool A chỉ ĐỌC, gắn `:ro`.

Chạy trong Docker (N7):
  MSYS_NO_PATHCONV=1 docker compose -f docker/docker-compose.yml run --rm \
      -v "<thư mục Tool A>:/tool_a:ro" freqtrade docs/du-lieu-do/do_td0261_overlap_tool_a.py --tool-a /tool_a
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

import yaml  # noqa: E402

from tool_d.gates.dsr import N_DANG_KY, dsr_hurdle  # noqa: E402

KET_QUA = REPO / "docs" / "du-lieu-do" / "td0261-overlap-tool-a.json"
RO_D = REPO / "config" / "pool_t1.yaml"
NGUONG = 0.50  # MT-50: ≥
MAU_A = re.compile(r"^([A-Z0-9]+)/USDT:USDT$")
MAU_D = re.compile(r"^[A-Z0-9]+USDT$")
RAO_CU = ("3,0777", "3.0777")
#: `DR-D1-04` §2 — ba file Tool A mà phép đo đọc. Một file đang sửa dở ⇒ từ chối.
FILE_A = ("tool-a/config.json", "logs/trials/trial_registry.json", "lib/trial_registry/dsr_trial_count.py")


class TuChoiDo(RuntimeError):
    pass


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


#: Repo Tool A trên host chạy `core.autocrlf=true`, `core.filemode=false` (đọc 19/09/2026), nên cây làm việc là CRLF. Git
#: trong container không có cấu hình host ⇒ lượt đầu thấy cả ba file "đang sửa" (diff 169/169 dòng, chỉ khác xuống
#: dòng) và TỪ CHỐI trước khi tính gì. Truyền đúng cấu hình host. Nội dung đổi thật vẫn hiện ra như cũ.
_GIT_NHU_HOST = ("-c", "safe.directory=*", "-c", "core.autocrlf=true", "-c", "core.fileMode=false")


def _git(thu_muc: Path, *args: str) -> str:
    r = subprocess.run(["git", *_GIT_NHU_HOST, "-C", str(thu_muc), *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise TuChoiDo(f"git {' '.join(args)} ở {thu_muc}: {r.stderr.strip()[:300]}")
    return r.stdout.strip()


def pool_tool_a(cfg: dict) -> list[str]:
    pl = cfg.get("pairlists") or []
    if [p.get("method") for p in pl] != ["StaticPairList"]:
        raise TuChoiDo(f"pairlists Tool A = {pl} — không phải đúng một StaticPairList, whitelist tĩnh không phải pool thật")
    ra = []
    for cap in cfg["exchange"]["pair_whitelist"]:
        m = MAU_A.match(cap)
        if not m:
            raise TuChoiDo(f"mã Tool A {cap!r} không khớp {MAU_A.pattern}")
        ra.append(f"{m.group(1)}USDT")
    if len(set(ra)) != len(ra):
        raise TuChoiDo("whitelist Tool A có mã trùng sau quy đổi")
    return ra


def pool_tool_d(ro: dict) -> list[str]:
    ra = list(ro["trading"])
    lech = [m for m in ra if not MAU_D.match(m)]
    if lech:
        raise TuChoiDo(f"mã Tool D không khớp {MAU_D.pattern}: {lech[:10]}")
    if len(set(ra)) != len(ra):
        raise TuChoiDo("rổ T1 có mã trùng")
    return ra


def jaccard(a: set[str], d: set[str]) -> float:
    if not (a | d):
        raise TuChoiDo("hai rổ đều rỗng")
    return len(a & d) / len(a | d)


def _nap_ham_tool_a(duong: Path):
    spec = importlib.util.spec_from_file_location("tool_a_dsr_trial_count", duong)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.project_dsr_denominator


def dr_mang_rao_cu() -> list[str]:
    return sorted(
        p.name for p in (REPO / "docs" / "decisions").glob("*.md")
        if any(r in p.read_text(encoding="utf-8") for r in RAO_CU)
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tool-a", required=True, help="thư mục repo Tool A (gắn :ro)")
    a = ap.parse_args()
    tool_a = Path(a.tool_a)
    if KET_QUA.exists():
        print(f"🛑 {KET_QUA} đã tồn tại — không ghi đè, không đo lại", flush=True)
        return 3
    try:
        sha_a = _git(tool_a, "rev-parse", "HEAD")
        dang_sua = _git(tool_a, "status", "--porcelain", "--", *FILE_A)
        if dang_sua:
            raise TuChoiDo(f"file Tool A đang sửa dở — không chụp trạng thái chưa commit:\n{dang_sua}")
        cfg_a = json.loads((tool_a / FILE_A[0]).read_text(encoding="utf-8"))
        a_ds = pool_tool_a(cfg_a)
        d_ds = pool_tool_d(yaml.safe_load(RO_D.read_text(encoding="utf-8")))
        so_a = json.loads((tool_a / FILE_A[1]).read_text(encoding="utf-8"))
        mau_so = _nap_ham_tool_a(tool_a / FILE_A[2])(so_a)
    except TuChoiDo as exc:
        print(f"🛑 TỪ CHỐI ĐO (DR-D1-04 §2): {exc}", flush=True)
        return 4

    A, D = set(a_ds), set(d_ds)
    ov = jaccard(A, D)
    ap_dung = ov >= NGUONG
    n_union = N_DANG_KY + mau_so.total
    kq = {
        "nguon": "TD-0261 — DR-D1-04 (aa130b1), H14 + DR-007, 0 trial, không đọc dữ liệu thị trường",
        "chup_luc_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tool_d": {"git_sha": _git(REPO, "rev-parse", "HEAD"), "ro": "config/pool_t1.yaml",
                   "sha256_ro": _sha256(RO_D), "so_ma": len(D)},
        "tool_a": {"git_sha": sha_a, "file_doc_sach": True,
                   "sha256_cay_lam_viec": {f: _sha256(tool_a / f) for f in FILE_A},
                   "git_blob_da_commit": {f: _git(tool_a, "rev-parse", f"HEAD:{f}") for f in FILE_A},
                   "pairlists": cfg_a["pairlists"], "so_ma": len(A),
                   "so_trial_trong_so": len(so_a), "N_A": mau_so.total,
                   "trial_chua_khai_tinh_la_1": mau_so.undeclared_trial_ids},
        "overlap": {"cong_thuc": "|A ∩ D| / |A ∪ D| (spec :341)", "giao": len(A & D), "hop": len(A | D),
                    "gia_tri": ov, "nguong": NGUONG, "danh_sach_giao": sorted(A & D)},
        "dr_007": {
            "ap_dung": ap_dung,
            "N_cong_D4": n_union if ap_dung else N_DANG_KY,
            "rao_dsr": dsr_hurdle(n_union if ap_dung else N_DANG_KY),
            "N_union_neu_ap": n_union, "rao_neu_ap": dsr_hurdle(n_union),
            "N_tach": N_DANG_KY, "rao_tach": dsr_hurdle(N_DANG_KY),
        },
        "dr_phai_doc_lai_con_so": dr_mang_rao_cu() if ap_dung else [],
        "han_che": [
            "Bản chụp TẠI LÚC ĐO (MT-56), không phải lúc chạy cổng: Tool A tiêu thêm trial sau giờ chụp thì N thật lớn hơn",
            "Chỉ trùng MÃ, không đo trùng KHOẢNG THỜI GIAN dữ liệu giữa hai tool — spec :341 định nghĩa theo tập mã",
            "Nối N vào gates/dsr.py và cổng D4 là việc riêng (DR-D1-04 §4) — artifact này không đổi mã nào",
        ],
    }
    KET_QUA.write_text(json.dumps(kq, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"|A| {len(A)} · |D| {len(D)} · giao {len(A & D)} · hợp {len(A | D)} · overlap {ov:.4f} "
          f"⇒ DR-007 {'ÁP DỤNG' if ap_dung else 'không áp'} · N_A {mau_so.total} · N cổng D4 "
          f"{kq['dr_007']['N_cong_D4']} · rào {kq['dr_007']['rao_dsr']:.4f}", flush=True)
    print(f"→ {KET_QUA}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
