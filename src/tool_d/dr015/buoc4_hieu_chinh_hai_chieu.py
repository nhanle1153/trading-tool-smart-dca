"""TD-0164 — DR-015 §4: quy tắc phân xử bằng HIỆU CHỈNH CỰC ĐOAN HAI CHIỀU.
Canh bởi `L-Z58`.

════ Điều spec cố ý KHÔNG làm, và vì sao ════

§4 mở đầu bằng một câu đáng nhớ: *"Cố ý KHÔNG đặt ngưỡng phần trăm cho
'lệch bao nhiêu là nhiều' — ngưỡng tuỳ tiện là chỗ uốn kết luận sau khi
thấy số."* Nên module này **không có** hằng số nào kiểu `LECH_TOI_DA`.
Thay vào đó nó chạy hai kịch bản cực đoan và chỉ hỏi **người thắng có
đổi không**:

    Chiều 1 (bất lợi cho DCA) : expectancy_DCA − Δ_R
    Chiều 2 (có lợi cho DCA)  : expectancy_DCA + Δ_R

  • Cùng một nhánh thắng ở CẢ HAI  ⇒ kết luận VỮNG trước sai số đo.
  • Người thắng ĐỔI giữa hai chiều ⇒ chênh hai nhánh NHỎ HƠN sai số
    thước ⇒ backtest KHÔNG ĐỦ TƯ CÁCH phân xử ⇒ áp §5 (mặc định Z0).

Lợi thế lớn tự sống sót qua hiệu chỉnh; quy tắc chỉ kích hoạt đúng lúc
chênh lệch nằm trong vùng nhiễu của thước.

Hằng số **20%** duy nhất ở đây KHÔNG phải do module này đặt — nó là hằng
số sẵn có của §10.2 Nhánh 2 (*"vượt Z0 ≥ 20% DSR-adjusted expectancy"*),
dùng lại nguyên vẹn, **0 DOF mới**.

════ 🔴 Không đọc §4 mà thiếu kết luận Bước 3 ════

`ket_luan_buoc3` là tham số **BẮT BUỘC**, không có mặc định. Lý do không
phải hình thức: §4 áp Δ_R **chỉ lên các arm DCA** và không đụng Z0. Phép
phạt bất đối xứng đó chỉ chính đáng nếu sai số thước đặc thù của tranche
2+ — và **Bước 3 tồn tại để kiểm đúng điều đó**.

Đo thật (TD-0163): Δ_R(Z0) = 0,1552 vs Δ_R(DCA) = 0,1612, tỉ lệ **1,04**
⇒ **tương đương**. Tức phần lớn Δ_R là sai số **CHUNG cho cả hai nhánh**
và tự triệt tiêu khi so sánh. Kết quả §4 vì thế phải luôn đi kèm câu đó;
để nó thành tham số bắt buộc là cách duy nhất khiến không ai đọc thiếu.

════ Thành phần NO_FILL (§3) ════

§3 đòi cộng thêm: *"mỗi tranche có xác suất không khớp `p_nf` thì kịch
bản hiệu chỉnh bất lợi coi tranche đó không tồn tại"*. Việc đó cần biết
expectancy của arm DCA **khi tranche 2/3 không khớp** — một con số riêng,
KHÔNG suy được từ expectancy đầy đủ. Nên:

  • `p_nf_cao == 0` (đúng như TD-0162 đo được) → thành phần này bằng 0,
    không cần thêm dữ liệu;
  • `p_nf_cao > 0` mà thiếu `expectancy_r_khong_tranche` → **RAISE**.
    Fail-closed: bỏ qua một thành phần bất lợi vì thiếu dữ liệu là làm
    kết quả lạc quan hơn thực tế, đúng thứ §3 thêm nó vào để chặn.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from tool_d.measurement.tri_state import Measured

# Hằng số của §10.2 Nhánh 2, dùng lại nguyên vẹn — 0 DOF mới.
NGUONG_VUOT = 0.20
# Spec §10.2: "Tốt nhất trong {Z3, Z3b} vượt Z0 ≥ 20%".
ARM_UNG_VIEN = ("Z3", "Z3b")
TEN_ARM_DOI_CHUNG = "Z0"


class PhanXuError(RuntimeError):
    """Đầu vào không đủ để phân xử. Fail-closed: raise chứ không rơi về
    một kết luận mặc định trông vô hại."""


@dataclass(frozen=True)
class Arm:
    """Một cấu hình ablation. `expectancy_r` là DSR-adjusted expectancy
    mỗi lệnh, tính theo đơn vị `R_realized` (DR-013: mọi chỉ số tổng hợp
    trên `pnl_abs`, quy đổi bằng `planned_risk_usdt` đóng băng tại tranche
    1).

    📌 Dùng tên đầy đủ `R_realized` chứ không viết tắt một chữ: `L-Z48c`
    cấm nhãn trần vì nó trôi giữa hai nghĩa "khoảng giá" và "hệ số nhân"
    mà không ai phát hiện. Phép kiểm đó grep CẢ docstring (không tha chú
    thích như `L-Z25`), và nó đã bắt đúng chỗ này trong bản đầu — sửa câu
    chữ, KHÔNG nới phép kiểm."""

    ten: str
    la_dca: bool
    expectancy_r: float
    # Chỉ cần khi p_nf > 0 — expectancy nếu tranche 2/3 KHÔNG khớp.
    expectancy_r_khong_tranche: float | None = None


@dataclass(frozen=True)
class MotChieu:
    ten_chieu: str
    expectancy_tot_nhat_dca: float
    arm_tot_nhat: str
    loi_the_tuong_doi: float  # (DCA − Z0) / |Z0|
    vuot_nguong: bool


@dataclass(frozen=True)
class KetQuaPhanXu:
    chieu_bat_loi: MotChieu
    chieu_co_loi: MotChieu
    phan_xu_duoc: bool
    arm_chon: str
    bien_hieu_chinh_delta_r: float
    loi_the_tho: float  # trước mọi hiệu chỉnh
    mo_khoa_5_2: bool
    dien_giai: str


def _tot_nhat_dca(arms: Mapping[str, Arm], *, dieu_chinh: float, p_nf_cao: float) -> tuple[str, float]:
    """Arm DCA tốt nhất trong {Z3, Z3b} sau khi cộng `dieu_chinh` vào
    expectancy. `p_nf_cao > 0` → dùng expectancy-không-tranche (kịch bản
    bất lợi coi tranche không tồn tại), trộn theo trọng số `p_nf_cao`."""
    ung_vien = [a for ten, a in arms.items() if ten in ARM_UNG_VIEN]
    if not ung_vien:
        raise PhanXuError(
            f"Không có arm nào trong {ARM_UNG_VIEN} — §10.2 Nhánh 2 so Z0 với "
            "tốt nhất của đúng hai arm đó, không phải với arm DCA bất kỳ."
        )
    tot_ten, tot_gia = "", float("-inf")
    for a in ung_vien:
        e = a.expectancy_r
        if p_nf_cao > 0:
            if a.expectancy_r_khong_tranche is None:
                raise PhanXuError(
                    f"p_nf_cao = {p_nf_cao} > 0 nhưng arm {a.ten} thiếu "
                    "`expectancy_r_khong_tranche`. §3 đòi kịch bản bất lợi coi tranche "
                    "không tồn tại — bỏ qua thành phần này vì thiếu dữ liệu sẽ làm kết "
                    "quả LẠC QUAN hơn thực tế."
                )
            e = (1 - p_nf_cao) * e + p_nf_cao * a.expectancy_r_khong_tranche
        e += dieu_chinh
        if e > tot_gia:
            tot_ten, tot_gia = a.ten, e
    return tot_ten, tot_gia


def hieu_chinh_hai_chieu(
    *,
    arms: Mapping[str, Arm],
    delta_r: Measured[float],
    p_nf_cao: Measured[float],
    ket_luan_buoc3: str,
) -> KetQuaPhanXu:
    """Chạy §4 và trả kết luận.

    `ket_luan_buoc3` ∈ {"tuong_duong", "chi_dca_lech", "chi_z0_lech"} —
    BẮT BUỘC, xem docstring module.

    🔴 `Z0.expectancy_r <= 0` → RAISE. "Vượt Z0 ≥ 20%" là so sánh TƯƠNG
    ĐỐI; với mẫu số không dương thì tỉ lệ đó vô nghĩa (và đổi dấu tuỳ ý
    khi Z0 âm). Trường hợp đó phải đưa lên người quyết, không được để
    một công thức âm thầm trả ra con số.
    """
    if ket_luan_buoc3 not in ("tuong_duong", "chi_dca_lech", "chi_z0_lech"):
        raise PhanXuError(f"`ket_luan_buoc3` không hợp lệ: {ket_luan_buoc3!r}")
    if not delta_r.is_ok():
        raise PhanXuError("Δ_R chưa đo được — §4 không chạy được, KHÔNG mặc định 0.")
    if not p_nf_cao.is_ok():
        raise PhanXuError("p_nf chưa đo được — §4 không chạy được, KHÔNG mặc định 0.")
    if TEN_ARM_DOI_CHUNG not in arms:
        raise PhanXuError(f"Thiếu arm đối chứng {TEN_ARM_DOI_CHUNG}.")

    z0 = arms[TEN_ARM_DOI_CHUNG].expectancy_r
    if z0 <= 0:
        raise PhanXuError(
            f"expectancy_r của Z0 = {z0} <= 0 — 'vượt Z0 >= 20%' là so sánh TƯƠNG ĐỐI, "
            "vô nghĩa (và đổi dấu tuỳ ý) với mẫu số không dương. Đưa lên người quyết."
        )

    d, pnf = delta_r.value, p_nf_cao.value

    def _chieu(ten: str, dieu_chinh: float) -> MotChieu:
        arm, e = _tot_nhat_dca(arms, dieu_chinh=dieu_chinh, p_nf_cao=pnf)
        loi_the = (e - z0) / abs(z0)
        return MotChieu(ten, e, arm, loi_the, loi_the >= NGUONG_VUOT)

    bat_loi = _chieu("bat_loi_cho_DCA (−Δ_R)", -d)
    co_loi = _chieu("co_loi_cho_DCA (+Δ_R)", +d)

    _, e_tho = _tot_nhat_dca(arms, dieu_chinh=0.0, p_nf_cao=pnf)
    loi_the_tho = (e_tho - z0) / abs(z0)

    phan_xu_duoc = bat_loi.vuot_nguong == co_loi.vuot_nguong
    mo_khoa_5_2 = (not phan_xu_duoc) and loi_the_tho >= NGUONG_VUOT

    canh_bao_buoc3 = ""
    if ket_luan_buoc3 == "tuong_duong":
        canh_bao_buoc3 = (
            " ⚠️ Bước 3 kết luận hai nhánh lệch TƯƠNG ĐƯƠNG — phần lớn Δ_R là sai số CHUNG "
            "cho cả Z0 lẫn DCA và tự triệt tiêu khi so sánh, nên biên hiệu chỉnh ở đây "
            "RỘNG HƠN bất lợi thực của riêng DCA."
        )
    elif ket_luan_buoc3 == "chi_z0_lech":
        canh_bao_buoc3 = (
            " 🔴 Bước 3 kết luận Z0 lệch NHIỀU HƠN DCA — giả thuyết nền của DR-015 bị dữ "
            "liệu bác; áp Δ_R chỉ lên DCA là phạt nhầm. Kết quả dưới đây KHÔNG dùng được "
            "cho đến khi chủ dự án phán quyết."
        )

    if phan_xu_duoc and bat_loi.vuot_nguong:
        arm_chon = bat_loi.arm_tot_nhat
        dien_giai = (
            f"VỮNG: {arm_chon} vượt Z0 ≥ {NGUONG_VUOT:.0%} ở CẢ HAI chiều hiệu chỉnh "
            f"(bất lợi {bat_loi.loi_the_tuong_doi:+.1%}, có lợi {co_loi.loi_the_tuong_doi:+.1%}); "
            f"biên hiệu chỉnh Δ_R = {d:.4f}." + canh_bao_buoc3
        )
    elif phan_xu_duoc:
        arm_chon = TEN_ARM_DOI_CHUNG
        dien_giai = (
            f"VỮNG: KHÔNG arm DCA nào vượt Z0 ≥ {NGUONG_VUOT:.0%} ở cả hai chiều "
            f"(bất lợi {bat_loi.loi_the_tuong_doi:+.1%}, có lợi {co_loi.loi_the_tuong_doi:+.1%}) "
            "→ chọn Z0, hệ thống SINGLE-ENTRY neo zone. 🔴 DỰ ÁN TIẾP TỤC BÌNH THƯỜNG — "
            "§10.1 và §3.4b mô tả đây là ĐÚNG HƯỚNG, không có điều khoản dừng nào."
            + canh_bao_buoc3
        )
    else:
        arm_chon = TEN_ARM_DOI_CHUNG
        dien_giai = (
            f"KHÔNG PHÂN XỬ ĐƯỢC: người thắng ĐỔI giữa hai chiều "
            f"(bất lợi {bat_loi.loi_the_tuong_doi:+.1%}, có lợi {co_loi.loi_the_tuong_doi:+.1%}) "
            "⇒ chênh hai nhánh NHỎ HƠN sai số thước ⇒ backtest không đủ tư cách phân xử "
            "⇒ §5.1 MẶC ĐỊNH VỀ Z0. Dự án TIẾP TỤC bình thường."
            + (
                f" §5.2 MỞ KHOÁ phương án đắt: lợi thế THÔ {loi_the_tho:+.1%} ≥ "
                f"{NGUONG_VUOT:.0%}."
                if mo_khoa_5_2
                else f" §5.2 KHÔNG mở khoá: lợi thế thô {loi_the_tho:+.1%} < {NGUONG_VUOT:.0%}."
            )
            + canh_bao_buoc3
        )

    return KetQuaPhanXu(
        chieu_bat_loi=bat_loi,
        chieu_co_loi=co_loi,
        phan_xu_duoc=phan_xu_duoc,
        arm_chon=arm_chon,
        bien_hieu_chinh_delta_r=d,
        loi_the_tho=loi_the_tho,
        mo_khoa_5_2=mo_khoa_5_2,
        dien_giai=dien_giai,
    )
