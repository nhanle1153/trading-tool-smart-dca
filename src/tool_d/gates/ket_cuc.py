"""TD-0199 — đọc kết quả ablation theo CỠ MẪU (`DR-D4-09` §2.1, §2.2).

Hai thứ §10.2 hiện KHÔNG phân biệt được, mà chúng dẫn tới hành động trái ngược:

    "đo được, và không đạt"      → FAIL          → xử theo DR-011
    "không đo được"              → INCONCLUSIVE  → thêm mẫu / đổi thiết kế

Gate hiện gộp cả hai thành *"KHÔNG VÀO LIVE"*. Hậu quả cụ thể, không giả
định: nếu Nhánh 2 trả *"Z3 không vượt Z0 ≥ 20%"* và bị đọc thành FAIL thì
hệ quả là **bỏ DCA vĩnh viễn** — dựa trên một phép đo mà chính công thức
của dự án chứng minh là không có khả năng phát hiện mức hiệu ứng đang hỏi
(`DR-D4-09` §4: ở `n = 40`, phát hiện được "vượt 20% của 0,10 R" cần
`n ≈ 7.400`).

════ "Thuế nhiễu" — một tên gọi, không phải một công thức mới ════

`dsr.dsr_adjusted_expectancy()` đã là `mean_R − h·std/√n` với
`h = √(2·ln N)`. Phần bị trừ đi có tên: **thuế nhiễu**. Module này KHÔNG
chép lại công thức — nó gọi `dsr_hurdle()` (MT-03: một nguồn sự thật).

🔴 Thuế nhiễu là đại lượng phải ĐƯỢC BÁO CÁO, không chỉ được trừ ngầm: một
`DSR_adj` đứng một mình không nói được nó là *"edge yếu"* hay *"chưa đủ
mẫu"*. Cùng tinh thần `L-Z15` in con số ngay cả khi ĐẠT (TD-0190).

════ Vì sao viết TRƯỚC khi có bất kỳ con số expectancy nào ════

Spec dòng 3956-3958 đòi mọi thay đổi ngưỡng/cách đọc phải viết TRƯỚC khi
thấy kết quả. Đây là mã hoá một ĐỊNH NGHĨA đã chốt ở `DR-D4-09`, không
phải một lớp canh cho đường chưa chạy — người gọi là TD-0184 (bản ghi kết
quả) và TD-0185 (`L-Z57`).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from tool_d.gates.dsr import N_DANG_KY, dsr_hurdle


class KetCuc(Enum):
    PASS = "PASS"
    INCONCLUSIVE = "INCONCLUSIVE"
    FAIL = "FAIL"


class KetCucError(ValueError):
    """Đầu vào không đủ để phân loại. Fail-closed: raise, KHÔNG trả FAIL —
    "không phân loại được" mà bị ghi thành FAIL là đúng lỗi `DR-D4-09` §2.2
    sinh ra để chặn, chỉ ở một tầng sâu hơn."""


def thue_nhieu(*, std_r: float, n_trades: int, n_trials: int = N_DANG_KY) -> float:
    """`h · std_R / √n` — phần `dsr_adjusted_expectancy()` trừ đi.

    Gọi `dsr_hurdle()` chứ không chép `√(2·ln N)` (MT-03).
    """
    if n_trades < 2:
        raise KetCucError(f"n_trades phải ≥ 2 để có std, nhận {n_trades}")
    if std_r != std_r or std_r < 0:
        raise KetCucError(f"std_r phải ≥ 0 và không NaN, nhận {std_r}")
    return dsr_hurdle(n_trials) * std_r / math.sqrt(n_trades)


@dataclass(frozen=True)
class KetQuaPhanLoai:
    ket_cuc: KetCuc
    gia_tri: float
    """Đại lượng đã trừ thuế nhiễu (vd `DSR_adj`) — thứ đem so với ngưỡng."""
    nguong: float
    thue: float
    n_trades: int

    def dien_giai(self) -> str:
        return (
            f"{self.ket_cuc.value} — giá trị {self.gia_tri:.4f} vs ngưỡng {self.nguong:.4f} "
            f"· thuế nhiễu {self.thue:.4f} · n = {self.n_trades}"
        )


def phan_loai_ket_cuc(
    *, mean_r: float, std_r: float, n_trades: int, nguong: float, n_trials: int = N_DANG_KY
) -> KetQuaPhanLoai:
    """`DR-D4-09` §2.2 — BA kết cục.

        thuế = h·std/√n ;  giá trị = mean_r − thuế
        PASS          : giá trị ≥ ngưỡng
        INCONCLUSIVE  : giá trị < ngưỡng  VÀ  thuế > ngưỡng
        FAIL          : giá trị < ngưỡng  VÀ  thuế ≤ ngưỡng

    🔑 **Thứ tự xét là bản chất, không phải chi tiết:** PASS được xét TRƯỚC.
    Một arm vừa vượt ngưỡng vừa có thuế nhiễu lớn vẫn là PASS — vì
    `DSR_adj` đã trừ thuế rồi, vượt được là vượt *sau khi* đã trả giá cho
    số phép thử. Đảo thứ tự sẽ biến chính cơ chế bảo vệ thành cái chặn
    những kết quả nó vừa xác nhận.

    🔴 **Vì sao mốc của INCONCLUSIVE là `thuế > ngưỡng`, không phải một con
    số mới** — DIỄN GIẢI, ghi ra để cãi lại được: khi sai số của phép đo
    lớn hơn chính ngưỡng nó phải phân định, phép đo không phân biệt được
    *"đạt"* với *"may mắn"* — kết luận theo hướng nào cũng không có căn cứ.
    Mốc này SUY TỪ chính ngưỡng của tiêu chí đang xét, nên **không thêm một
    tham số nào vào kiểm kê DOF** (`DR-D4-09` §6). Đặt một hằng số riêng
    (vd "thuế ≤ 0,05") sẽ là bịa một tham số không ai đăng ký — đúng lỗi
    `DR-D4-02` sinh ra để chặn.
    """
    if nguong != nguong:
        raise KetCucError("ngưỡng là NaN — không phân loại trên số chưa tính được")
    if mean_r != mean_r:
        raise KetCucError("mean_r là NaN — 'chưa đo' KHÁC 'đo được và bằng 0' (N6)")
    t = thue_nhieu(std_r=std_r, n_trades=n_trades, n_trials=n_trials)
    gia_tri = mean_r - t
    if gia_tri >= nguong:
        kc = KetCuc.PASS
    elif t > nguong:
        kc = KetCuc.INCONCLUSIVE
    else:
        kc = KetCuc.FAIL
    return KetQuaPhanLoai(ket_cuc=kc, gia_tri=gia_tri, nguong=nguong, thue=t, n_trades=n_trades)


@dataclass(frozen=True)
class KetQuaSoPaired:
    ket_cuc: KetCuc
    n_giao: int
    n_a: int
    n_b: int
    mean_hieu: float
    std_hieu: float
    rho: float
    thue: float
    can_duoi_hieu: float
    """`mean(d) − h·std(d)/√n_giao` — cận dưới của hiệu sau khi trừ thuế."""
    muc_can_vuot: float
    """`ty_le_vuot × mean(R_A)`."""

    def dien_giai(self) -> str:
        return (
            f"{self.ket_cuc.value} — cận dưới hiệu {self.can_duoi_hieu:.4f} vs cần "
            f"{self.muc_can_vuot:.4f} · ρ {self.rho:.3f} · thuế {self.thue:.4f} · "
            f"n_giao {self.n_giao} (A {self.n_a} / B {self.n_b})"
        )


def so_paired(
    *,
    r_a: Sequence[float],
    r_b: Sequence[float],
    n_a: int,
    n_b: int,
    ty_le_vuot: float,
    n_trials: int = N_DANG_KY,
) -> KetQuaSoPaired:
    """`DR-D4-09` §2.1 — B có vượt A ít nhất `ty_le_vuot` không, so PAIRED.

        d_i = R_B,i − R_A,i   trên tập GIAO (cùng `(pair, giờ mở)`)
        PASS ⟺ mean(d) − h·std(d)/√n_giao ≥ ty_le_vuot × mean(R_A)

    `r_a`/`r_b` phải **đã được ghép cặp** bởi tầng gọi và cùng độ dài —
    module này không biết `pair`/thời gian, đúng khuôn "hàm thuần nhận số
    đã tính sẵn". `n_a`/`n_b` là cỡ mẫu ĐẦY ĐỦ của từng arm, chỉ để BÁO
    CÁO: mẫu số của phép so luôn là `n_giao` (`DR-D4-09` §2.1).

    🔴 **Vì sao mẫu số là `n_giao` chứ không phải `n_a`:** dùng `n_a` là
    khai một cỡ mẫu mà phép so không có. Nếu `n_giao ≠ n_a` thì giả định
    *"cùng tập entry"* đã sai với nhóm arm đang xét và tầng gọi phải chuyển
    sang phép so KHÔNG paired (`DR-D4-09` §7 điều kiện mở lại 3) — hàm này
    trả `n_giao`/`n_a`/`n_b` ra ngoài chính để chỗ đó kiểm được.

    Kết cục theo §2.2, áp cho chính phép so này: ngưỡng là `muc_can_vuot`.
    """
    if len(r_a) != len(r_b):
        raise KetCucError(f"r_a ({len(r_a)}) và r_b ({len(r_b)}) phải cùng độ dài — chưa ghép cặp?")
    n = len(r_a)
    if n < 2:
        raise KetCucError(f"n_giao phải ≥ 2 để có std, nhận {n}")
    if not (0 < ty_le_vuot < 1):
        raise KetCucError(f"ty_le_vuot phải trong (0,1) — 20% là 0.20, nhận {ty_le_vuot}")
    if n > min(n_a, n_b):
        raise KetCucError(f"n_giao ({n}) không thể lớn hơn n_a ({n_a}) hay n_b ({n_b})")

    d = [float(b) - float(a) for a, b in zip(r_a, r_b)]
    if any(x != x for x in d):
        raise KetCucError("có NaN trong R — 'chưa đo' KHÁC 'đo được' (N6)")
    mean_d = sum(d) / n
    var_d = sum((x - mean_d) ** 2 for x in d) / (n - 1)
    std_d = math.sqrt(var_d)

    mean_a = sum(r_a) / n
    var_a = sum((x - mean_a) ** 2 for x in r_a) / (n - 1)
    mean_b = sum(r_b) / n
    var_b = sum((x - mean_b) ** 2 for x in r_b) / (n - 1)
    # ρ chỉ để BÁO CÁO (điều kiện mở lại 2 của DR-D4-09 §7). Hai arm phẳng
    # tuyệt đối thì tương quan KHÔNG xác định — trả 0.0 và nói ra qua std=0,
    # không bịa 1.0.
    if var_a <= 0 or var_b <= 0:
        rho = 0.0
    else:
        cov = sum((x - mean_a) * (y - mean_b) for x, y in zip(r_a, r_b)) / (n - 1)
        rho = cov / math.sqrt(var_a * var_b)

    t = dsr_hurdle(n_trials) * std_d / math.sqrt(n)
    can_duoi = mean_d - t
    muc = ty_le_vuot * mean_a
    if can_duoi >= muc:
        kc = KetCuc.PASS
    elif t > abs(muc):
        kc = KetCuc.INCONCLUSIVE
    else:
        kc = KetCuc.FAIL
    return KetQuaSoPaired(
        ket_cuc=kc, n_giao=n, n_a=n_a, n_b=n_b, mean_hieu=mean_d, std_hieu=std_d,
        rho=rho, thue=t, can_duoi_hieu=can_duoi, muc_can_vuot=muc,
    )


__all__ = [
    "KetCuc",
    "KetCucError",
    "KetQuaPhanLoai",
    "KetQuaSoPaired",
    "phan_loai_ket_cuc",
    "so_paired",
    "thue_nhieu",
]
