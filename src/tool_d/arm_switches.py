"""TD-0183 — công tắc arm ablation: Z1 (SL), Z0-S1 (định cỡ), Z2 (bỏ DG5).

Bổ sung cho `arms.py` (TD-0182, công tắc TẦNG LỌC TREND). Hai module tách
nhau vì chúng bật/tắt hai thứ khác hẳn: `arms.py` chọn *bao nhiêu tầng lọc
trend còn hiệu lực*; module này chọn *cách tính SL*, *cách tính cỡ lệnh*,
và *cổng nào được xét*. Gộp lại sẽ thành một bảng cấu hình khổng lồ mà mỗi
dòng chỉ liên quan tới một cột.

🔴 **PHẠM VI RÚT GỌN — chủ dự án duyệt 08/09/2026, TD-0183 là 2,5/4.**
Hai vế KHÔNG làm, cả hai vì spec-vs-code chứ không phải thiếu công:

**(1) `Z0-V1` không có ở đây.** §10.1b định nghĩa nó đúng bằng *"tắt điều
kiện (c) volume"*, nên công tắc đó thuộc `entry_confirmation.py`, không
thuộc module này (MT-15, phiên `-d5` vá).

**(2) `Z2` chỉ làm vế "không DG5", KHÔNG làm vế "không `mult_zss`".**
`mult_zss` không có mặt ở tầng tính cỡ lệnh — `tranche1_notional()` nhận
thẳng `rho_pct`, không nhân hệ số nào. Tắt một thứ chưa bao giờ bật là
**cờ chết**, đúng thứ dòng TD-0183 tự cấm (*"mỗi công tắc một test chứng
minh nó đổi hành vi THẬT"*). Hệ quả phải đọc kèm kết quả D4: spec dòng
4164 nói cặp Z2/Z3 trả lời *"DG5 + `mult_zss` có giá trị đo được"*, nhưng
thực tế **chỉ đo được DG5**.

════ Vì sao BỌC chứ không sửa chữ ký hai hàm gốc ════

`tinh_ke_hoach()` và `tranche1_notional()` có người gọi thật
(`ZoneAbsorptionMinimal.py`, `build_pool.py`, nhiều test). Thêm tham số
bắt buộc vào chúng là bắt cả hệ thống khai một lựa chọn ablation ở những
chỗ không liên quan gì tới ablation. Ở đây bọc lại: đường chạy thường
**không đổi một dòng nào**, arm nào cần khác thì đi qua cửa này.
"""

from __future__ import annotations

from typing import Literal

from tool_d.notional import tranche1_notional
from tool_d.trade_plan import KeHoachTranche, tinh_ke_hoach

#: Chín cấu hình của B2 (§10.1 + §10.1b). `Z0-T2` KHÔNG có mặt: spec ghi
#: *"Mốc so sánh — không phải arm mới, không tốn trial thêm"*, nó CHÍNH LÀ
#: `Z0` (xem `arms.TANG_THEO_ARM`). Đếm nhầm là tiêu thừa một suất thật.
ARM_HOP_LE: tuple[str, ...] = (
    "Z0",
    "Z1",
    "Z2",
    "Z3",
    "Z3b",
    "Z0-T0",
    "Z0-T1",
    "Z0-V1",
    "Z0-S1",
)

#: §10.1 mô tả `Z1` là *"SL = 2.2×ATR cố định (kiểu v1)"*. Đây là **định
#: nghĩa của arm**, không phải tham số tune được: nó tái lập đúng thiết kế
#: v1 để so sánh. Đổi số này là đo một arm khác, không phải chỉnh một nút.
HE_SO_ATR_Z1 = 2.2

CheDoSL = Literal["ZONE", "ATR_CO_DINH"]
CheDoCoLenh = Literal["RUI_RO_CO_DINH", "NOTIONAL_CO_DINH"]

CHE_DO_SL_THEO_ARM: dict[str, CheDoSL] = {a: "ZONE" for a in ARM_HOP_LE}
CHE_DO_SL_THEO_ARM["Z1"] = "ATR_CO_DINH"

CHE_DO_CO_LENH_THEO_ARM: dict[str, CheDoCoLenh] = {
    a: "RUI_RO_CO_DINH" for a in ARM_HOP_LE
}
CHE_DO_CO_LENH_THEO_ARM["Z0-S1"] = "NOTIONAL_CO_DINH"

#: DG1–DG5 chỉ có nghĩa với arm CÓ tranche 2/3. Arm entry đơn không bao giờ
#: xét thêm tranche, nên không cổng nào áp dụng — khác hẳn "đủ năm cổng".
ARM_DON_TRANCHE: frozenset[str] = frozenset(
    {"Z0", "Z1", "Z0-T0", "Z0-T1", "Z0-V1", "Z0-S1"}
)
NAM_CONG: tuple[str, ...] = ("DG1", "DG2", "DG3", "DG4", "DG5")


class ArmSwitchError(ValueError):
    """Arm không hợp lệ, hoặc thiếu thứ arm đó bắt buộc phải khai."""


def _kiem_arm(arm: str) -> None:
    if arm not in ARM_HOP_LE:
        raise ArmSwitchError(
            f"arm {arm!r} không thuộc chín cấu hình B2 {ARM_HOP_LE}. "
            "Lưu ý `Z0-T2` KHÔNG phải arm — nó CHÍNH LÀ `Z0` (§10.1b)."
        )


# ── Z1: SL neo ATR thay vì neo zone ───────────────────────────────────

def sl_neo_atr(*, p1: float, atr_4h: float) -> float:
    """SL kiểu v1: `p1 − 2.2×ATR`, neo vào **điểm vào**, không vào zone.

    Đây là thiết kế mà spec dòng 1021 so sánh trực tiếp với thiết kế hiện
    tại (*"SL không còn cố định 2.2×ATR, mà theo zone"*).

    🔑 **Dùng `atr_4h`, cùng khung với chế độ ZONE — một diễn giải, ghi ra
    để cãi lại được.** Spec không nói `Z1` lấy ATR khung nào. Chọn cùng
    khung có chủ đích: câu hỏi của arm là *"neo zone hay neo ATR tốt hơn"*,
    nên chỉ được để **công thức** khác nhau. Cho hai chế độ hai khung ATR
    khác nhau thì kết quả trộn hai nguyên nhân và không tách ra được.
    """
    if atr_4h < 0:
        raise ArmSwitchError(f"atr_4h không được âm: {atr_4h}")
    return p1 - HE_SO_ATR_Z1 * atr_4h


def ke_hoach_theo_arm(
    *,
    arm: str,
    zone_low: float,
    zone_high: float,
    gia_dong_cua: float,
    atr_4h: float,
    atr_1h_tai_tranche1: float,
) -> KeHoachTranche:
    """`tinh_ke_hoach()` nguyên vẹn, chỉ thay `sl` khi arm đòi chế độ khác.

    🔴 `r_eff_plan` được tính LẠI theo `sl` mới. Bỏ sót chỗ này là lỗi im
    lặng đắt nhất có thể có ở đây: `r_eff` chảy thẳng vào cỡ lệnh (§6.8e),
    nên một `Z1` mang `r_eff` của zone sẽ vào lệnh với cỡ của arm KHÁC, và
    bảng kết quả vẫn trông hoàn toàn bình thường.

    Chế độ `ZONE` trả về **đúng đối tượng** của `tinh_ke_hoach()`, không
    dựng lại — để không có nguồn sự thật thứ hai cho công thức §3.1.
    """
    _kiem_arm(arm)
    goc = tinh_ke_hoach(
        zone_low=zone_low,
        zone_high=zone_high,
        gia_dong_cua=gia_dong_cua,
        atr_4h=atr_4h,
        atr_1h_tai_tranche1=atr_1h_tai_tranche1,
    )
    if CHE_DO_SL_THEO_ARM[arm] == "ZONE":
        return goc

    sl = sl_neo_atr(p1=goc.p1, atr_4h=atr_4h)
    p_avg = (goc.p1 + goc.p2 + goc.p3) / 3
    if sl <= 0:
        raise ArmSwitchError(
            f"arm {arm}: SL neo ATR ra {sl} ≤ 0 — giá không âm được. ATR ({atr_4h}) "
            f"quá lớn so với p1 ({goc.p1}). Chốt `sl < p_avg` một mình KHÔNG bắt được "
            "ca này (SL rất âm vẫn nhỏ hơn p_avg) và `r_eff` sẽ ra > 100%, tức cỡ "
            "lệnh nhỏ đi một cách vô nghĩa thay vì báo lỗi — fail-closed ở đây"
        )
    if sl >= p_avg:
        raise ArmSwitchError(
            f"arm {arm}: SL neo ATR ({sl}) không nằm dưới giá vào trung bình "
            f"({p_avg}) — ATR quá lớn so với zone. `r_eff` sẽ ≤ 0 và cỡ lệnh mất "
            "nghĩa; fail-closed thay vì sinh một con số âm chảy vào §6.8e"
        )
    return KeHoachTranche(
        zone_low=goc.zone_low,
        zone_high=goc.zone_high,
        p1=goc.p1,
        p2=goc.p2,
        p3=goc.p3,
        sl=sl,
        r_eff_plan=(p_avg - sl) / p_avg,
        atr_1h_tai_tranche1=goc.atr_1h_tai_tranche1,
    )


# ── Z0-S1: định cỡ theo VỐN thay vì theo RỦI RO ───────────────────────

def notional_tranche1_theo_arm(
    *,
    arm: str,
    e_d: float,
    rho_pct: float,
    r_eff: float,
    n_tranches: int,
    notional_ref_r_eff: float | None = None,
) -> float:
    """Notional tranche 1 theo chế độ định cỡ của arm.

    `RUI_RO_CO_DINH` (§6.8e): gọi thẳng `notional.tranche1_notional()`,
    không chép công thức.

    `NOTIONAL_CO_DINH` (arm `Z0-S1`): **không phụ thuộc `R_eff` của lệnh**.
    Đó chính là điều arm này kiểm chứng — §10.1b: *"nó KHÔNG phụ thuộc
    `R_eff` tính đúng; nếu công thức `R_eff` sai, rủi ro-cố-định sai theo,
    vốn-cố-định thì không"*. Vì thế `r_eff` **không được** tham gia nhánh
    này; có test ghim bằng cách đổi `r_eff` và đòi kết quả KHÔNG đổi.

    🔑 **DR-D4-07 — hai nhánh nay dùng CHUNG một hàm, khác nhau đúng một
    thứ: `R_eff` nào được truyền vào.** Nhánh rủi-ro-cố-định lấy `R_eff`
    THẬT của lệnh; nhánh vốn-cố-định lấy `notional_ref_r_eff` ĐÓNG BĂNG.
    Viết như vậy làm tính chất *"không phụ thuộc R_eff của lệnh"* thành
    **cấu trúc** chứ không phải một lời hứa cần test canh, và không chép
    lại công thức §6.8e ra chỗ thứ hai (bài học MT-03: hai bản sẽ trôi lệch).

    🔴 **`notional_ref_r_eff` BẮT BUỘC, cố ý KHÔNG có mặc định** — cùng lý
    do `dg5_zss_khong_suy_yeu()` bắt buộc ngưỡng (TD-0169). Trước
    DR-D4-07, tham số ở đây là `notional_co_dinh_usdt` (con số USDT cứng)
    và nó `null` trong cấu hình, nên arm `Z0-S1` **raise và sinh ra 0
    lệnh** trên 48 mã EXPLORE trong 22 tháng — một suất trial trong 114
    mua thông tin bằng không.

    🔴 **Vì sao THAM CHIẾU chứ không phải con số USDT:** notional phải giữ
    nguyên **thang tương đối** so với arm rủi-ro-cố-định, nếu không phép so
    trộn hai nguyên nhân (*cách tính cỡ lệnh* và *quy mô vị thế*). Một con
    số cứng mất tính chất đó ngay khi `E_D` đổi: `E_D` vừa đi 500 → 750
    (DR-D4-05), và một `300` chọn hồi 500 sẽ tương đương `R_ref` 0,625%
    lúc đó nhưng 0,9375% bây giờ — ý nghĩa của arm tự đổi 50% mà không ai
    quyết gì. Cùng họ với `E_D = 500` ghim trong docstring và
    `"2025-01-01"` ghim trong test.
    """
    _kiem_arm(arm)
    if CHE_DO_CO_LENH_THEO_ARM[arm] == "RUI_RO_CO_DINH":
        if notional_ref_r_eff is not None:
            raise ArmSwitchError(
                f"arm {arm} định cỡ theo RỦI RO nhưng lại được truyền "
                "`notional_ref_r_eff` — một trong hai chỗ đang hiểu sai arm này"
            )
        return tranche1_notional(
            e_d=e_d, rho_pct=rho_pct, r_eff=r_eff, n_tranches=n_tranches
        )

    if notional_ref_r_eff is None:
        raise ArmSwitchError(
            f"arm {arm} định cỡ theo VỐN nên phải khai `notional_ref_r_eff` "
            "(tier_c.arm_ablation). KHÔNG có mặc định: xem DR-D4-07 — con số này "
            "chọn để Z0-S1 triển khai CÙNG vốn trung bình với Z0, tự điền là "
            "thêm một bậc tự do không ai đếm."
        )
    if not 0 < notional_ref_r_eff < 1:
        raise ArmSwitchError(
            f"notional_ref_r_eff phải nằm trong (0, 1) — là TỈ LỆ, không phải "
            f"phần trăm; nhận {notional_ref_r_eff}. Truyền 3.0 thay vì 0.03 làm "
            "cỡ lệnh nhỏ đi 100 lần mà không có phép kiểm nào báo đỏ."
        )
    if n_tranches <= 0:
        raise ArmSwitchError(f"n_tranches phải > 0, nhận {n_tranches}")
    # 🔴 `r_eff` của lệnh KHÔNG xuất hiện ở đây — đó là toàn bộ điểm của arm.
    return tranche1_notional(
        e_d=e_d, rho_pct=rho_pct, r_eff=notional_ref_r_eff, n_tranches=n_tranches
    )


# ── Z2: bỏ DG5 ────────────────────────────────────────────────────────

def cong_ap_dung(arm: str) -> tuple[str, ...]:
    """Những cổng DG1–DG5 thực sự có hiệu lực với arm này.

    `Z2` bỏ **DG5** (§10.1: *"3 tranche neo zone, xác nhận entry ở tranche
    1, không DG5, không mult_zss"*). Arm entry đơn không có tranche 2/3 nên
    **không cổng nào** áp dụng — trả tuple rỗng, khác hẳn "đủ năm".
    """
    _kiem_arm(arm)
    if arm in ARM_DON_TRANCHE:
        return ()
    if arm == "Z2":
        return tuple(c for c in NAM_CONG if c != "DG5")
    return NAM_CONG


def duoc_them_tranche(*, arm: str, ket_qua_cong: dict[str, bool]) -> bool:
    """Có được bơm thêm tranche không, theo đúng tập cổng của arm.

    `ket_qua_cong` là đầu ra của `dg1_dg5_tranche_gates.danh_gia_tat_ca()`.
    Cổng nào arm không dùng thì **bỏ qua kết quả của nó**, kể cả khi nó
    `False` — đó chính là ý nghĩa của "tắt DG5".

    Thiếu một cổng arm CẦN → raise, không coi là `False` và cũng không coi
    là `True`: thiếu dữ liệu khác hẳn "cổng đã đóng", gộp hai thứ lại là
    cách một lỗi lắp ráp biến thành một quyết định giao dịch.
    """
    can = cong_ap_dung(arm)
    if not can:
        raise ArmSwitchError(
            f"arm {arm} là arm ENTRY ĐƠN — không bao giờ xét thêm tranche, nên câu "
            "hỏi 'được thêm tranche không' không áp dụng. Hỏi nó nghĩa là chỗ gọi "
            "đang nhầm arm này với arm có DCA."
        )
    thieu = [c for c in can if c not in ket_qua_cong]
    if thieu:
        raise ArmSwitchError(
            f"arm {arm} cần các cổng {can} nhưng thiếu {thieu} trong kết quả truyền vào"
        )
    return all(ket_qua_cong[c] for c in can)
