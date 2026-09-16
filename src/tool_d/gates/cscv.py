"""TD-0282 — PBO qua CSCV (H18, nâng P0 ở D9). Hàm THUẦN, không I/O.

Theo Bailey, Borwein, López de Prado & Zhu (2014), *The Probability of Backtest
Overfitting*; mọi lựa chọn triển khai chốt TRƯỚC ở `DR-D9-01` §4 — module này
không được quyết thêm điều gì.

════ Thuật toán (DR-D9-01 §4.3) ════

1. Lệnh của mỗi cấu hình gán vào một trong `S` khối lịch theo `open_date`.
2. Cấu hình có CÙNG dãy `(open_date, r_trien_khai)` gộp làm một (§2) — giữ cả
   hai là đếm một điểm hai lần và kéo hạng.
3. Với mỗi cách chọn `S/2` khối làm IS (phần còn lại OOS):
   `n*` = argmax trung bình `R_trien_khai` trên IS; `ω̄` = hạng OOS của `n*`
   (1 = kém nhất, hoà ⇒ hạng trung bình) chia `(N + 1)`; `λ = ln(ω̄ / (1 − ω̄))`.
   Hoà ở đỉnh IS ⇒ `λ` = trung bình λ của các cấu hình cùng đỉnh.
4. `PBO = #(λ ≤ 0) / số tổ hợp`.

════ Ba trạng thái, không bịa số (N6) ════

- Dưới 2 cấu hình phân biệt ⇒ `unreadable` (không có gì để xếp hạng).
- Một cấu hình có ít hơn `san_lenh_moi_nua` lệnh ở nửa IS HOẶC OOS của tổ hợp
  ⇒ tổ hợp đó `unreadable`.
- PBO là SỐ chỉ khi MỌI tổ hợp đọc được (§4.4). Không tính trên tập con tổ hợp
  — bỏ tổ hợp theo số lệnh là chọn mẫu sau khi dữ liệu đã chạy.

🔴 Lệnh có `open_date` ngoài `[t1, t2)` hoặc trị số không hữu hạn ⇒ RAISE: đó
là lỗi nối dữ liệu, không phải một lệnh để lặng lẽ bỏ.

Trung bình dùng `math.fsum` — cùng một tập số cho cùng một tổng bất kể thứ tự
cộng, nên phép so "hoà" bằng `==` là tất định.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from itertools import combinations
from typing import Mapping, Protocol, Sequence

from tool_d.gates.cscv_cau_hinh import CauHinhCSCV
from tool_d.measurement.tri_state import Measured


class CSCVError(ValueError):
    """Đầu vào CSCV hỏng (lệnh ngoài cửa sổ, trị số không hữu hạn, S lẻ). Fail-closed."""


class LenhCoR(Protocol):
    """Hình dạng tối thiểu một lệnh cần có — `wfo/lenh.py::LenhWFO` (TD-0283) thoả."""

    @property
    def open_date(self) -> datetime: ...

    @property
    def r_trien_khai(self) -> float: ...


@dataclass(frozen=True)
class ToHop:
    """Một tổ hợp IS/OOS. `lam` chỉ có khi `ly_do_khong_doc` là None."""

    khoi_is: tuple[int, ...]
    lam: float | None
    ly_do_khong_doc: str | None


@dataclass(frozen=True)
class KetQuaPBO:
    pbo: Measured[float]
    so_cau_hinh_dau_vao: int
    so_cau_hinh_phan_biet: int
    cau_hinh_gop_trung: tuple[tuple[str, ...], ...]
    so_to_hop: int
    so_to_hop_doc_duoc: int
    to_hop: tuple[ToHop, ...]


def _hang_phan_so(gia_tri: Sequence[float]) -> list[float]:
    """Hạng tăng dần, 1 = nhỏ nhất; hoà ⇒ trung bình các hạng chiếm chỗ."""
    thu_tu = sorted(range(len(gia_tri)), key=lambda i: gia_tri[i])
    hang = [0.0] * len(gia_tri)
    i = 0
    while i < len(thu_tu):
        j = i
        while j + 1 < len(thu_tu) and gia_tri[thu_tu[j + 1]] == gia_tri[thu_tu[i]]:
            j += 1
        tb = (i + 1 + j + 1) / 2
        for k in range(i, j + 1):
            hang[thu_tu[k]] = tb
        i = j + 1
    return hang


def _logit(omega: float) -> float:
    return math.log(omega / (1.0 - omega))


def tinh_pbo(lenh_theo_cau_hinh: Mapping[str, Sequence[LenhCoR]], ch: CauHinhCSCV) -> KetQuaPBO:
    """PBO của tập cấu hình `lenh_theo_cau_hinh` (khoá = định danh cấu hình)."""
    S = ch.so_khoi
    if S < 2 or S % 2 != 0:
        raise CSCVError(f"so_khoi phải chẵn và ≥ 2, nhận {S}")
    if ch.t2 - ch.t1 != S * ch.do_dai_khoi:
        raise CSCVError(f"{S} × {ch.do_dai_khoi} ≠ [{ch.t1}, {ch.t2})")

    # 1. Gán khối + kiểm đầu vào.
    tong: dict[str, list[list[float]]] = {}
    chu_ky: dict[str, tuple[tuple[datetime, float], ...]] = {}
    for ten in sorted(lenh_theo_cau_hinh):
        theo_khoi: list[list[float]] = [[] for _ in range(S)]
        for lenh in lenh_theo_cau_hinh[ten]:
            od, r = lenh.open_date, lenh.r_trien_khai
            if not (ch.t1 <= od < ch.t2):
                raise CSCVError(f"{ten}: lệnh open_date {od} ngoài [{ch.t1}, {ch.t2}) — lỗi nối dữ liệu")
            if not isinstance(r, (int, float)) or isinstance(r, bool) or not math.isfinite(r):
                raise CSCVError(f"{ten}: r_trien_khai không hữu hạn: {r!r}")
            theo_khoi[(od - ch.t1) // ch.do_dai_khoi].append(float(r))
        tong[ten] = theo_khoi
        chu_ky[ten] = tuple(sorted((l.open_date, float(l.r_trien_khai)) for l in lenh_theo_cau_hinh[ten]))

    # 2. Gộp cấu hình trùng khít (§2).
    nhom: dict[tuple[tuple[datetime, float], ...], list[str]] = {}
    for ten in sorted(chu_ky):
        nhom.setdefault(chu_ky[ten], []).append(ten)
    dai_dien = [ds[0] for ds in nhom.values()]
    gop = tuple(tuple(ds) for ds in nhom.values() if len(ds) > 1)
    N = len(dai_dien)

    so_to_hop = math.comb(S, S // 2)
    if N < 2:
        return KetQuaPBO(
            pbo=Measured.unreadable(f"{N} cấu hình phân biệt sau gộp — CSCV cần ≥ 2 (DR-D9-01 §2)"),
            so_cau_hinh_dau_vao=len(lenh_theo_cau_hinh),
            so_cau_hinh_phan_biet=N,
            cau_hinh_gop_trung=gop,
            so_to_hop=so_to_hop,
            so_to_hop_doc_duoc=0,
            to_hop=(),
        )

    # 3. Mỗi tổ hợp.
    ket_qua: list[ToHop] = []
    for khoi_is in combinations(range(S), S // 2):
        khoi_oos = tuple(b for b in range(S) if b not in khoi_is)
        tb_is: list[float] = []
        tb_oos: list[float] = []
        ly_do: str | None = None
        for ten in dai_dien:
            lenh_is = [r for b in khoi_is for r in tong[ten][b]]
            lenh_oos = [r for b in khoi_oos for r in tong[ten][b]]
            if len(lenh_is) < ch.san_lenh_moi_nua or len(lenh_oos) < ch.san_lenh_moi_nua:
                ly_do = (
                    f"{ten}: IS {len(lenh_is)} / OOS {len(lenh_oos)} lệnh < sàn {ch.san_lenh_moi_nua}"
                )
                break
            tb_is.append(math.fsum(lenh_is) / len(lenh_is))
            tb_oos.append(math.fsum(lenh_oos) / len(lenh_oos))
        if ly_do is not None:
            ket_qua.append(ToHop(khoi_is=khoi_is, lam=None, ly_do_khong_doc=ly_do))
            continue
        dinh = max(tb_is)
        cung_dinh = [i for i, v in enumerate(tb_is) if v == dinh]
        hang_oos = _hang_phan_so(tb_oos)
        lam = math.fsum(_logit(hang_oos[i] / (N + 1)) for i in cung_dinh) / len(cung_dinh)
        ket_qua.append(ToHop(khoi_is=khoi_is, lam=lam, ly_do_khong_doc=None))

    doc_duoc = [t for t in ket_qua if t.lam is not None]
    if len(doc_duoc) < so_to_hop:
        dau = next(t.ly_do_khong_doc for t in ket_qua if t.lam is None)
        pbo: Measured[float] = Measured.unreadable(
            f"{so_to_hop - len(doc_duoc)}/{so_to_hop} tổ hợp dưới sàn — PBO chỉ là số khi mọi tổ hợp "
            f"đọc được (DR-D9-01 §4.4). Ví dụ: {dau}"
        )
    else:
        pbo = Measured.ok(sum(1 for t in doc_duoc if t.lam <= 0.0) / so_to_hop)

    return KetQuaPBO(
        pbo=pbo,
        so_cau_hinh_dau_vao=len(lenh_theo_cau_hinh),
        so_cau_hinh_phan_biet=N,
        cau_hinh_gop_trung=gop,
        so_to_hop=so_to_hop,
        so_to_hop_doc_duoc=len(doc_duoc),
        to_hop=tuple(ket_qua),
    )


__all__ = ["CSCVError", "KetQuaPBO", "LenhCoR", "ToHop", "tinh_pbo"]
