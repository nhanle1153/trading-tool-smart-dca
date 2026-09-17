"""TD-0293 — ĐO độ trễ git trong container dưới ba mức tải, TRƯỚC khi đổi thời hạn.

Vì sao: `measurement/gitinfo._run_git` đặt `timeout=10` (s) cho MỖI lời gọi git;
`get_git_info()` gọi hai lần (`rev-parse HEAD`, `status --porcelain`). Dưới tải,
`test_td0143::test_code_sha_lay_dung_tu_git` đỏ vì quá hạn (17/09/2026), chạy
riêng thì xanh. Con số 10 chưa từng được đo. File này đo; thời hạn mới SUY từ số.

Đo đúng hai lệnh mà đường sản xuất chạy, cùng cờ `--no-optional-locks`.
Mỗi mẫu cũng ghi `/proc/loadavg` để đọc được tải lúc lấy mẫu.

Chạy (mỗi mức một lần, trong container — N7):
  docker compose -f docker/docker-compose.yml run --rm freqtrade \\
      docs/du-lieu-do/do_td0293_tre_git_status.py do --muc nhan
  (mức `mot_suite` / `hai_suite`: xoá file cờ, khởi động 1 / 2 lượt full suite ở
   container KHÁC — bộ chạy tạo file cờ khi MỌI lượt đã xong — rồi chạy lệnh trên
   với `--muc` tương ứng và `--co-dung <file cờ>`)
  docker compose ... freqtrade docs/du-lieu-do/do_td0293_tre_git_status.py tong_hop

0 trial: không đọc dữ liệu thị trường, không đánh giá cấu hình.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
THU_MUC_RA = REPO / "docs" / "du-lieu-do"
MUC = ("nhan", "mot_suite", "hai_suite")
LENH = {
    "rev_parse": ["git", "--no-optional-locks", "rev-parse", "HEAD"],
    "status": ["git", "--no-optional-locks", "status", "--porcelain"],
}
# Trần an toàn của PHÉP ĐO (không phải thời hạn đề xuất): một lệnh treo thì
# ghi nhận là quá trần thay vì treo cả phép đo.
TRAN_DO_S = 600

# Công thức thời hạn — viết TRƯỚC khi có số:
#   thoi_han = max(10, lam_tron_len_5(HE_SO × max_mot_lenh_o_muc_nang_nhat))
# HE_SO = 2: mức "hai suite chồng" chưa phải tải tệ nhất có thể; thời hạn dài
# hơn chỉ làm một lỗi git thật lộ ra chậm hơn (vẫn raise, không nuốt), còn
# thời hạn ngắn hơn làm đỏ giả. 10 = giá trị cũ, không hạ.
HE_SO = 2
SAN_CU_S = 10


def _loadavg() -> list[float]:
    try:
        return [float(x) for x in Path("/proc/loadavg").read_text().split()[:3]]
    except OSError:
        return []


def _mot_lenh(lenh: list[str]) -> float:
    t = time.perf_counter()
    kq = subprocess.run(lenh, cwd=REPO, capture_output=True, timeout=TRAN_DO_S, check=False)
    dt = time.perf_counter() - t
    if kq.returncode != 0:
        raise RuntimeError(f"{' '.join(lenh)} exit {kq.returncode}: {kq.stderr.decode(errors='replace')}")
    return dt


def _phan_vi(xs: list[float], q: float) -> float:
    s = sorted(xs)
    k = (len(s) - 1) * q
    lo, hi = math.floor(k), math.ceil(k)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def _thong_ke(xs: list[float]) -> dict:
    return {
        "n": len(xs), "min": min(xs), "p50": _phan_vi(xs, 0.5), "p90": _phan_vi(xs, 0.9),
        "p99": _phan_vi(xs, 0.99), "max": max(xs),
        "ghi_chu_phan_vi": "nội suy tuyến tính giữa hai mẫu kề (kiểu numpy 'linear')",
    }


def do(muc: str, so_mau: int, nghi_s: float, ghi_chu: str, co_dung: Path | None) -> Path:
    """Lấy `so_mau` mẫu; hoặc, nếu có `co_dung`, lấy tới khi file cờ đó xuất hiện.

    🔴 Mức có tải PHẢI dùng `co_dung` (bộ chạy suite tạo file khi mọi suite đã
    xong): lấy theo số mẫu cố định thì mẫu cuối rơi vào lúc suite đã kết thúc —
    trộn mức nhàn vào mức tải (bản đầu dính đúng lỗi này: suite 4 phút 30, khung
    mẫu ~7 phút). Mẫu đang dở lúc cờ xuất hiện vẫn giữ (nó bắt đầu khi còn tải).
    """
    if co_dung is not None and co_dung.exists():
        raise SystemExit(f"{co_dung} đã tồn tại TRƯỚC khi đo — xoá rồi khởi động lại suite")
    # 🔴 Đã cắn 17/09/2026: Git Bash (MSYS) đổi `/workspace/x` thành
    # `C:/Program Files/Git/workspace/x` trước khi tới Docker ⇒ cờ không bao giờ
    # xuất hiện ⇒ bộ đo chạy ~1 giờ 40 phút trên máy NHÀN mà không báo gì.
    # Thư mục cha không tồn tại = đường dẫn hỏng, dừng NGAY. Dùng đường dẫn tương đối.
    if co_dung is not None and not co_dung.parent.is_dir():
        raise SystemExit(f"thư mục cha của cờ không tồn tại: {co_dung.parent} — đường dẫn bị đổi dọc đường?")
    mau = []
    bat_dau = datetime.now(timezone.utc).isoformat()
    i = 0
    while True:
        m = {"i": i, "t": datetime.now(timezone.utc).isoformat(), "loadavg": _loadavg()}
        for ten, lenh in LENH.items():
            m[f"{ten}_s"] = _mot_lenh(lenh)
        mau.append(m)
        i += 1
        if co_dung is not None:
            if co_dung.exists():
                break
        elif i >= so_mau:
            break
        time.sleep(nghi_s)
    ra = {
        "td": "TD-0293", "muc": muc, "bat_dau": bat_dau,
        "ket_thuc": datetime.now(timezone.utc).isoformat(),
        "dung_theo": str(co_dung) if co_dung is not None else f"so_mau={so_mau}",
        "nproc": os.cpu_count(), "nghi_giua_mau_s": nghi_s, "ghi_chu_tai": ghi_chu,
        "lenh": {k: " ".join(v) for k, v in LENH.items()},
        "thong_ke": {
            ten: _thong_ke([m[f"{ten}_s"] for m in mau]) for ten in LENH
        } | {"get_git_info_tong": _thong_ke([m["rev_parse_s"] + m["status_s"] for m in mau])},
        "mau": mau,
    }
    p = THU_MUC_RA / f"td0293-tre-git-{muc}.json"
    p.write_text(json.dumps(ra, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return p


def tong_hop() -> Path:
    cac_muc = {}
    for muc in MUC:
        p = THU_MUC_RA / f"td0293-tre-git-{muc}.json"
        d = json.loads(p.read_text(encoding="utf-8"))
        if d["thong_ke"]["status"]["n"] < 30:
            raise SystemExit(f"{p.name}: n = {d['thong_ke']['status']['n']} < 30 — chưa đủ mẫu")
        cac_muc[muc] = {"nguon": p.name, "ghi_chu_tai": d["ghi_chu_tai"],
                        "thong_ke": d["thong_ke"]}
    nang_nhat = cac_muc["hai_suite"]["thong_ke"]
    max_mot_lenh = max(nang_nhat["status"]["max"], nang_nhat["rev_parse"]["max"])
    thoi_han = max(SAN_CU_S, 5 * math.ceil(HE_SO * max_mot_lenh / 5))
    ra = {
        "td": "TD-0293",
        "cau_hoi": "thời hạn MỖI lời gọi git trong gitinfo._run_git",
        "cong_thuc": f"max({SAN_CU_S}, lam_tron_len_5({HE_SO} × max_mot_lenh(hai_suite)))",
        "max_mot_lenh_hai_suite_s": max_mot_lenh,
        "thoi_han_de_xuat_s": thoi_han,
        "ket_luan": (
            f"Thời hạn giữ {SAN_CU_S} s — công thức viết trước ra đúng giá trị cũ, KHÔNG đổi mã. "
            "Ca đỏ gốc (test_td0143 quá hạn 10 s, 17/09/2026) KHÔNG tái hiện được bằng tải full suite, "
            "kể cả hai lượt chồng: nguyên nhân CHƯA BIẾT. Đừng đọc file này là 'đã giải thích ca đỏ'."
            if thoi_han == SAN_CU_S else
            f"Thời hạn đề xuất {thoi_han} s (> {SAN_CU_S} s cũ) theo công thức viết trước."
        ),
        "cac_muc": cac_muc,
        "file_loai": {
            "td0293-tre-git-mot_suite-ban1-tron-muc.json":
                "KHÔNG dùng: lấy theo số mẫu cố định, 15/45 mẫu rơi sau khi suite đã xong (trộn mức nhàn)",
        },
        "han_che": [
            "Mức tải là chạy full suite thật, không phải tải tổng hợp; tải nền của phiên khác ghi ở ghi_chu_tai.",
            "Một máy, một ngày; 'hai suite chồng' chưa phải cận trên của tải có thể xảy ra — vì thế có HE_SO.",
        ],
    }
    p = THU_MUC_RA / "td0293-tre-git-status.json"
    p.write_text(json.dumps(ra, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return p


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="lenh", required=True)
    a = sub.add_parser("do")
    a.add_argument("--muc", choices=MUC, required=True)
    a.add_argument("--so-mau", type=int, default=40)
    a.add_argument("--nghi-s", type=float, default=5.0)
    a.add_argument("--ghi-chu-tai", default="")
    a.add_argument("--co-dung", type=Path, default=None,
                   help="đường dẫn (trong repo) file cờ bộ chạy suite tạo khi xong; bắt buộc cho mức có tải")
    sub.add_parser("tong_hop")
    ns = ap.parse_args()
    if ns.lenh == "do":
        if ns.muc != "nhan" and ns.co_dung is None:
            raise SystemExit("mức có tải phải dùng --co-dung (xem docstring hàm do)")
        print(do(ns.muc, ns.so_mau, ns.nghi_s, ns.ghi_chu_tai, ns.co_dung))
    else:
        print(tong_hop())


if __name__ == "__main__":
    main()
