"""TD-0430 — máy kiểm độ mạnh thống kê ở cửa CHỌN (giải nợ `MT-89`, `DR-VONG-DOI-01` §3, `TC-Q1-2027-00`).

Luật (chủ dự án chốt 25/09/2026): tờ chọn khai đơn vị đo, `σ`, `n` dự kiến trên lockbox, lợi thế tự khai `μ`; xác suất
phát hiện ≈ `Φ(μ·√n/σ − h)` với rào `h = √(2·ln N)` phải đạt ngưỡng của file tiêu chí quý. Dưới ngưỡng ⇒ không chọn.

Vì sao có máy: trước việc này phép tính chỉ nằm trong chữ của tờ chọn. Một phép thử không có khả năng PASS ở cỡ mẫu hiện
có tiêu suất và lockbox mà không trả lời được câu hỏi nào — và điều đó chỉ lộ ra MUỘN, sau khi đã tiêu suất (`MT-89`).

════ Máy tự tính, không tin số khai ════

`h` lấy từ `dsr.dsr_hurdle(N_DANG_KY)` — không chép `N` hay `h` vào đây. Tờ chọn có thể mang `xac_suat_khai`, nhưng số
đó chỉ được in cạnh số máy tính để người đọc thấy lệch; quyết định chỉ theo số máy tính.

════ Ngưỡng đọc từ file tiêu chí quý ════

Dòng `DO_MANH_TOI_THIEU: <p>` trong `DR-Q{n}-{năm}-tieu-chi-chon-y-tuong.md`, cùng kiểu `HAN_NGACH_CHON`. Cố ý KHÔNG
chép con số vào đây (bài học `TD-0315`). Quý không khai dòng này ⇒ không đòi (quý 3, 4/2026 viết trước luật).
Khai nhiều lần, hoặc giá trị ngoài `(0, 1)` ⇒ vi phạm (fail-closed).

════ Hạn chế — ghi thẳng ════

Máy KHÔNG kiểm được `σ`, `μ` có trung thực không, cũng không kiểm `n_lockbox` có khớp độ dài lockbox. Nó chặn hai ca:
tính sai, và quên tính.
"""

from __future__ import annotations

import math
import re
from statistics import NormalDist
from typing import Any

from tool_d.gates.dsr import N_DANG_KY, dsr_hurdle

DO_MANH_RE = re.compile(r"^DO_MANH_TOI_THIEU:\s*(\S+)\s*$", re.MULTILINE)

# Khoá bắt buộc của khối `do_manh` trong tờ chọn; `xac_suat_khai` tuỳ chọn, chỉ để in cạnh.
KHOA_CHUOI = ("don_vi", "nguon_sigma")
KHOA_SO = ("sigma", "mu")
KHOA_NGUYEN = ("n_lockbox",)
KHOA_BAT_BUOC = (*KHOA_CHUOI, *KHOA_SO, *KHOA_NGUYEN)


_CHUAN = NormalDist()


def xac_suat_phat_hien(*, mu: float, sigma: float, n: int, n_trials: int = N_DANG_KY) -> float:
    """`Φ(μ·√n/σ − h)`, `h = √(2·ln N)`. Raise nếu `σ ≤ 0` hoặc `n < 1` — không trả số lính canh (N6)."""
    if not sigma > 0:
        raise ValueError(f"sigma phải > 0, nhận {sigma!r}")
    if n < 1:
        raise ValueError(f"n phải ≥ 1, nhận {n!r}")
    return _CHUAN.cdf(mu * math.sqrt(n) / sigma - dsr_hurdle(n_trials))


def _la_so(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def kiem_do_manh(do_manh: Any, noi_dung_tieu_chi: str, *, n_trials: int = N_DANG_KY) -> list[str]:
    """Danh sách vi phạm (rỗng = qua). Cửa CHỌN (`idea_queue.chon_y_tuong`) và audit `TD-0120` cùng gọi hàm này."""
    khai = DO_MANH_RE.findall(noi_dung_tieu_chi)
    if not khai:
        return []
    if len(khai) > 1:
        return [f"file tiêu chí khai DO_MANH_TOI_THIEU {len(khai)} lần — không biết dùng số nào"]
    try:
        nguong = float(khai[0])
    except ValueError:
        return [f"DO_MANH_TOI_THIEU: {khai[0]!r} không phải số"]
    if not 0 < nguong < 1:
        return [f"DO_MANH_TOI_THIEU: {khai[0]} nằm ngoài (0, 1)"]

    if not isinstance(do_manh, dict):
        return [
            f"file tiêu chí đòi độ mạnh ≥ {nguong} nhưng tờ chọn không có khối do_manh "
            f"(khai {', '.join(KHOA_BAT_BUOC)}) — MT-89"
        ]
    loi = [f"do_manh thiếu {k}" for k in KHOA_BAT_BUOC if k not in do_manh]
    loi += [f"do_manh.{k} phải là chuỗi có nội dung" for k in KHOA_CHUOI
            if k in do_manh and not (isinstance(do_manh[k], str) and do_manh[k].strip())]
    loi += [f"do_manh.{k} phải là số hữu hạn, nhận {do_manh[k]!r}" for k in KHOA_SO
            if k in do_manh and not _la_so(do_manh[k])]
    loi += [f"do_manh.{k} phải là số nguyên ≥ 1, nhận {do_manh[k]!r}" for k in KHOA_NGUYEN
            if k in do_manh and not (isinstance(do_manh[k], int) and not isinstance(do_manh[k], bool)
                                     and do_manh[k] >= 1)]
    if not loi and not do_manh["sigma"] > 0:
        loi.append(f"do_manh.sigma phải > 0, nhận {do_manh['sigma']!r}")
    if loi:
        return loi

    mu, sigma, n = do_manh["mu"], do_manh["sigma"], do_manh["n_lockbox"]
    h = dsr_hurdle(n_trials)
    p = xac_suat_phat_hien(mu=mu, sigma=sigma, n=n, n_trials=n_trials)
    if p >= nguong:
        return []
    khai_p = do_manh.get("xac_suat_khai")
    ghi_canh = f"; tờ chọn tự khai {khai_p!r} — máy không dùng số đó" if khai_p is not None else ""
    mu_can = (h + _CHUAN.inv_cdf(nguong)) * sigma / math.sqrt(n)
    return [
        f"xác suất phát hiện máy tính = {p:.4f} < DO_MANH_TOI_THIEU {nguong} "
        f"(μ={mu}, σ={sigma}, n={n}, N={n_trials}, h={h:.4f}; cần μ ≥ {mu_can:.6g} {do_manh['don_vi']})"
        f"{ghi_canh} — không được chọn (TC-00, MT-89)"
    ]

