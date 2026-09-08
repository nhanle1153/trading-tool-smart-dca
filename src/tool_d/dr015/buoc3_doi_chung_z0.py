"""TD-0163 — DR-015 Bước 3: ĐỐI CHỨNG ÂM cho nhánh Z0 (BẮT BUỘC).

Spec §2 Bước 3, nguyên văn lý do: *"Không có mốc tham chiếu thì con số
lệch của DCA không biết là lớn hay nhỏ. Hai nhánh lệch tương đương ⇒ sai
số phần lớn triệt tiêu khi so sánh. Chỉ DCA lệch ⇒ xác nhận đúng vấn
đề."*

════ Vì sao bước này quyết định tính CÔNG BẰNG của §4 ════

Quy tắc phân xử §4 trừ/cộng Δ_R vào expectancy của **mọi arm DCA**, và
KHÔNG đụng tới Z0. Phép hiệu chỉnh bất đối xứng đó chỉ chính đáng nếu
sai số thước thật sự **đặc thù của tranche 2+**. Nếu tranche 1 — thứ Z0
cũng có — lệch tương đương, thì phần lớn sai số là **chung cho cả hai
nhánh** và sẽ tự triệt tiêu khi so sánh; lúc đó áp Δ_R chỉ lên DCA là
phạt nhầm.

Đây chính là điều Bước 3 tồn tại để phát hiện, và nó phải chạy TRƯỚC khi
ai nhìn thấy kết quả ablation (§1: chốt sau khi thấy kết quả thì mất hiệu
lực chống thiên vị).

════ Cách dựng đối chứng — và vì sao dùng CÙNG mẫu số ════

`ZoneAbsorptionMinimal` không có arm Z0 riêng để chạy, nhưng **tranche 1
của nó CHÍNH LÀ điểm vào của Z0** (§D0.9: *"Z0 — entry đơn, có xác nhận,
neo zone"*). Nên đối chứng dựng bằng cách phân hoạch chính 91 lượt khớp:

    Z0  (đối chứng) : |lệch_R| của tranche 1        — mỗi lệnh 1 giá trị
    DCA (TD-0161)   : Σ|lệch_R| các tranche ≥ 2     — mỗi lệnh 1 giá trị

Cả hai dùng **cùng một `planned_risk_usdt`** của chính trade đó. Chọn vậy
có chủ đích, và nó không thiên vị bên nào vì **`lệch_R` bất biến theo quy
mô ở bậc nhất**: Z0 vào cả cục ở `p1` thì `qty` lớn hơn, nhưng
`planned_risk_usdt` cũng lớn lên gần đúng cùng tỉ lệ, nên thương số gần
như không đổi. Dùng một mẫu số thứ hai (giả định cỡ lệnh của Z0) sẽ đưa
thêm một giả định vào đúng chỗ đang cần đối chứng sạch.

🔴 **KHÔNG viết lại phép tính.** Module này gọi thẳng các hàm nội bộ của
`buoc1_lech_tranche.py` (TD-0161). Chép lại công thức sang đây là tạo
nguồn sự thật thứ hai cho cùng một đại lượng — hai bản sẽ trôi lệch, và
lúc đó "đối chứng" so hai thước khác nhau chứ không so hai nhánh. Có test
ghim việc dùng lại này để nếu TD-0161 đổi thì ta biết ngay.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tool_d.dr015.buoc1_lech_tranche import (
    SAN_N_CHO_P90,
    Buoc1Error,
    _gia_ke_hoach_ca_ba_tranche,
    _gom_theo_trade,
    _p90,
    _planned_risk_usdt,
    _uoc_luong_cost_tranche,
)
from tool_d.measurement.tri_state import Measured


@dataclass(frozen=True)
class KetQuaDoiChung:
    """Δ_R của MỘT nhánh, cùng đơn vị và cùng cách tính với TD-0161."""

    nhanh: str  # "Z0" | "DCA"
    huong: str
    so_lenh: int
    lech_moi_lenh: tuple[float, ...]
    delta_r: Measured[float]
    dung_p90: bool


@dataclass(frozen=True)
class PhanXuDoiChung:
    """Kết luận của Bước 3 — ba vế của spec, không có vế thứ tư."""

    ket_luan: str  # "tuong_duong" | "chi_dca_lech" | "chi_z0_lech"
    ty_le_dca_tren_z0: Measured[float]
    dien_giai: str


def _lech_tranche1(fills: dict[int, dict[str, Any]], p: dict[int, float], risk: float) -> float:
    """|lệch_R| của RIÊNG tranche 1 — đối xứng với `_lech_moi_lenh()` của
    TD-0161 (vốn chỉ tính tranche ≥ 2). Cùng công thức, khác tập tranche."""
    qty = fills[1]["amount"]
    return abs(qty * (fills[1]["fill_price"] - p[1]) / risk)


def tinh_doi_chung(du_lieu_tho: dict[str, Any]) -> dict[str, KetQuaDoiChung]:
    """Δ_R cho CẢ HAI nhánh trên cùng bộ dữ liệu, cùng mẫu số.

    Trả `{"Z0": ..., "DCA": ...}`. Chỉ tính hướng LONG — Short chưa có dữ
    liệu (TD-0114 LONG-only) và `N6` cấm bịa 0.0; hàm này KHÔNG dựng ra
    một nhánh Short rỗng để bảng trông cân đối.
    """
    rows = [r for r in du_lieu_tho["luot_khop"] if r["huong"] == "long"]
    if not rows:
        raise Buoc1Error("Không có lượt khớp LONG nào — không dựng được đối chứng")

    theo_trade = _gom_theo_trade(rows)
    lech_z0: list[float] = []
    lech_dca: list[float] = []
    for fills in theo_trade.values():
        p1 = fills[1]["p_ke_hoach"]
        p = _gia_ke_hoach_ca_ba_tranche(fills[1], p1)
        cost_full = _uoc_luong_cost_tranche({i: fills[i]["cost"] for i in fills})
        risk = _planned_risk_usdt(cost_full, p, fills[1]["sl"])
        lech_z0.append(_lech_tranche1(fills, p, risk))
        lech_dca.append(
            sum(
                abs(fills[i]["amount"] * (fills[i]["fill_price"] - p[i]) / risk)
                for i in (2, 3)
                if i in fills
            )
        )

    ket_qua = {}
    for nhanh, ds in (("Z0", lech_z0), ("DCA", lech_dca)):
        n = len(ds)
        dung_p90 = n >= SAN_N_CHO_P90
        ket_qua[nhanh] = KetQuaDoiChung(
            nhanh=nhanh,
            huong="LONG",
            so_lenh=n,
            lech_moi_lenh=tuple(ds),
            delta_r=Measured.ok(_p90(ds) if dung_p90 else max(ds)),
            dung_p90=dung_p90,
        )
    return ket_qua


# Biên "tương đương" — chọn TRƯỚC khi nhìn số, và chọn theo lập luận chứ
# không theo dữ liệu: hai đại lượng chênh nhau dưới 2 lần thì không nhánh
# nào áp đảo về sai số thước. Đây là con số CHỌN, không phải định lý —
# ghi ra để sau này cãi lại được, đúng cách DR-D3-01 §5.2 làm với sàn 30.
BIEN_TUONG_DUONG = 2.0


def phan_xu(doi_chung: dict[str, KetQuaDoiChung]) -> PhanXuDoiChung:
    """Ba vế của spec §2 Bước 3, không có vế thứ tư.

    🔴 Vế `chi_z0_lech` KHÔNG có trong spec — spec chỉ liệt kê "tương
    đương" và "chỉ DCA lệch". Thêm vào đây có chủ đích: nếu dữ liệu cho
    thấy **Z0 lệch nhiều hơn**, giả thuyết nền của DR-015 (*sai số cộng
    dồn theo số tranche nên DCA chịu nhiều hơn*) bị dữ liệu bác. Không có
    chỗ ghi kết cục đó nghĩa là ép nó vào một trong hai vế còn lại — tức
    giấu một phát hiện ngược.
    """
    z0, dca = doi_chung["Z0"].delta_r, doi_chung["DCA"].delta_r
    if not (z0.is_ok() and dca.is_ok()):
        return PhanXuDoiChung(
            ket_luan="tuong_duong",
            ty_le_dca_tren_z0=Measured.unreadable("thiếu Δ_R của ít nhất một nhánh"),
            dien_giai="Không đủ dữ liệu để phân xử — KHÔNG được coi là 'tương đương'.",
        )
    if z0.value == 0 and dca.value == 0:
        # TD-0167: KHÔNG nhánh nào lệch. Ca này phải tách khỏi ca dưới —
        # gộp lại sẽ in ra "Z0 không lệch chút nào còn DCA có lệch" trong khi
        # DCA cũng bằng 0, tức một câu SAI SỰ THẬT ở đúng chỗ người đọc dùng
        # để quyết định có áp Δ_R lên DCA hay không. Tỉ lệ 0/0 không xác định
        # được nên vẫn `unreadable`, nhưng KẾT LUẬN thì xác định: tương đương.
        return PhanXuDoiChung(
            ket_luan="tuong_duong",
            ty_le_dca_tren_z0=Measured.unreadable("cả hai nhánh Δ_R = 0 — tỉ lệ 0/0 không xác định"),
            dien_giai=(
                "CẢ HAI nhánh đều không lệch (Δ_R = 0) — không có sai số thước nào để phân "
                "xử. Hiệu chỉnh §4 theo chiều nào cũng không đổi kết quả."
            ),
        )
    if z0.value == 0:
        return PhanXuDoiChung(
            ket_luan="chi_dca_lech",
            ty_le_dca_tren_z0=Measured.unreadable("Δ_R của Z0 bằng 0 — tỉ lệ không xác định"),
            dien_giai="Z0 không lệch chút nào còn DCA có lệch — sai số đặc thù tranche 2+.",
        )

    ty_le = dca.value / z0.value
    if ty_le > BIEN_TUONG_DUONG:
        kl, dg = "chi_dca_lech", (
            f"DCA lệch gấp {ty_le:.2f} lần Z0 (> {BIEN_TUONG_DUONG}) — xác nhận đúng vấn "
            "đề DR-015 nêu: sai số cộng dồn theo số tranche. Hiệu chỉnh bất đối xứng của "
            "§4 (chỉ áp Δ_R lên DCA) là CHÍNH ĐÁNG."
        )
    elif ty_le < 1 / BIEN_TUONG_DUONG:
        kl, dg = "chi_z0_lech", (
            f"Z0 lệch gấp {1/ty_le:.2f} lần DCA — NGƯỢC với giả thuyết nền của DR-015. "
            "Sai số thước KHÔNG đặc thù tranche 2+; áp Δ_R chỉ lên DCA là phạt nhầm. "
            "Phải đưa lên chủ dự án trước khi chạy §4."
        )
    else:
        kl, dg = "tuong_duong", (
            f"Hai nhánh lệch tương đương (DCA/Z0 = {ty_le:.2f}, trong biên "
            f"[{1/BIEN_TUONG_DUONG:.2f}, {BIEN_TUONG_DUONG:.2f}]) — sai số phần lớn TRIỆT "
            "TIÊU khi so sánh hai nhánh. Δ_R vẫn dùng cho §4 nhưng phải ghi kèm: phần lớn "
            "nó KHÔNG phải bất lợi riêng của DCA."
        )
    return PhanXuDoiChung(ket_luan=kl, ty_le_dca_tren_z0=Measured.ok(ty_le), dien_giai=dg)
