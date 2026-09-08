"""TD-0181 — DG1–DG5 (§4): năm cổng KÍCH HOẠT tranche mới.

Năm cổng này trả lời đúng một câu: *"có được bơm thêm tranche không?"*
Chúng **không** đóng vị thế đã có — đó là việc của nhóm DG6/DG7/DG8
(`dg6_early_invalidation.py`, §4.1). Nhầm hai nhóm là nhầm giữa "ngừng
thêm tiền" và "rút tiền ra", hai hành động khác hẳn nhau về hậu quả.

Mỗi cổng là một hàm THUẦN: nhận số đã tính sẵn, trả `bool`, không đọc
file, không gọi TA-Lib, không biết gì về Freqtrade. Cùng khuôn với
`trend_context.py` và `dg6_early_invalidation.py` — để test được bằng số
dựng tay, và để chỗ gọi phải nói rõ nó đang truyền cái gì vào.

════ 🔴 Hai chỗ CỐ Ý không tự quyết, đã báo chủ dự án ════

**1. Ngưỡng 30% của DG5 không có trong `tool_d_config.yaml`, cũng không
có trong bảng kiểm kê DOF.** Spec §4 định nghĩa DG5 là *"ZSS tính lại
không giảm > 30% so với lúc tranche 1"*, nhưng bảng DOF (§ kiểm kê) có
dòng cho DG4, DG6-A, DG6-B, DG6-C/D, DG7, `max_hold_bars` — **không có
dòng nào cho DG5**. Đây đúng hình dạng thiếu sót mà chính bảng đó đã tự
sửa một lần: dòng DG7 ghi *"(0 — bỏ sót)"*.

Hệ quả nếu tự điền: thêm khoá vào `tier_b` là **+1 DOF**, mà `N_ĐĂNG_KÝ
= 114` là mẫu số của rào DSR §10.2 và đã cam kết. Đó là quyết định kiến
trúc, không phải chi tiết triển khai. Nên `dg5_zss_khong_suy_yeu()` nhận
`nguong_giam_toi_da` là **tham số BẮT BUỘC, không có mặc định** — cùng
cách `fill_probe.do_ty_le_khong_khop()` bắt buộc `truoc_ms`/`sau_ms`.
Không mặc định thì không ai vô tình chạy với một con số chưa ai duyệt,
và cũng không có hằng số lậu nào nằm ngoài kiểm kê.

**2. DG1 gần như không bao giờ fail khi SL là lệnh THẬT trên sàn.** §4
định nghĩa DG1 = *"chưa có nến 4H đóng cửa dưới `sl`"*, nhưng nếu SL là
lệnh chờ sống thì giá chạm `sl` là vị thế đã đóng — không còn tranche
nào để xét. Tức DG1 chỉ có thể fail ở ca biên (nhảy giá qua mức, hoặc
SL đánh giá theo giá đóng cửa). Spec dòng 998 nói DG1 và SL *"là cùng
một điều kiện nhìn từ hai góc"*, đúng với quan sát này. Cổng vẫn được
cài đủ theo đúng chữ của §4 — nhận xét trên là để không ai đọc một dòng
`DG1: true` trong decision log rồi tưởng nó mang nhiều thông tin hơn
thực tế.

════ Vì sao KHÔNG dùng lại `SO_NEN_TOI_THIEU_B` của DG6 cho DG4 ════

Hai con số cùng bằng 8 nhưng **khác hạng**: `dg4_bars_1h` là 🟡 tunable
#7 (đổi được, mỗi lần đổi tốn 1 trial từ B3), còn `dg6b_bars_1h` là 🔒
ĐÓNG BĂNG với `dof: -1` và ghi chú *"= dg4_bars_1h"*. Gộp làm một hằng
số sẽ biến một tham số đóng băng thành tham số tune được — đúng chiều
nới lỏng mà kiểm kê DOF tồn tại để chặn. DG4 ở đây đọc từ cấu hình (N4),
DG6 giữ hằng số đóng băng của nó.
"""

from __future__ import annotations

import math
from typing import Literal, Sequence

from tool_d.trend_context import TrendDir

Huong = Literal["long", "short"]


class TrancheGateError(ValueError):
    """Đầu vào không đủ cơ sở để phán quyết. Fail-closed: raise chứ không
    trả `False` — `False` nghĩa là "đã xét và cổng đóng", khác hẳn "không
    xét được", và gộp hai thứ đó lại là cách một lỗi dữ liệu biến thành
    một quyết định giao dịch trông bình thường."""


def _kiem_huong(huong: str) -> None:
    if huong not in ("long", "short"):
        raise TrancheGateError(f"huong phải là 'long' hoặc 'short', nhận: {huong!r}")


def dg1_zone_con_nguyen(
    *, close_4h_ke_tu_tranche1: Sequence[float], sl: float, huong: Huong
) -> bool:
    """DG1 — chưa có nến 4H nào ĐÓNG CỬA vượt qua `sl`.

    Dùng giá ĐÓNG CỬA, không phải `low`/`high`: một cái râu xuyên xuống
    rồi thu lại chưa phải bằng chứng zone bị phá — đó là chính hành vi
    hấp thụ mà chiến lược đi tìm. Đây là chữ của §4, và nó cũng là lý do
    v2 bỏ điều kiện mơ hồ *"tín hiệu còn hiệu lực"* của v1.

    Danh sách rỗng (chưa có nến 4H nào đóng kể từ tranche 1) → `True`:
    chưa có bằng chứng phá zone. Đây là trạng thái thật, không phải
    thiếu dữ liệu — nên KHÔNG raise.
    """
    _kiem_huong(huong)
    if huong == "long":
        return all(c >= sl for c in close_4h_ke_tu_tranche1)
    return all(c <= sl for c in close_4h_ke_tu_tranche1)


def dg2_trend_con_dung(
    *, trend_dir_tai_tranche1: TrendDir, trend_dir_hien_tai: TrendDir
) -> bool:
    """DG2 — `trend_dir` không đổi kể từ tranche 1 (Phần 2, §2.1).

    So sánh ĐỒNG NHẤT, nên `UP → FLAT` cũng là fail. Đây là một **diễn
    giải**, ghi ra để cãi lại được: đọc hẹp thì *"đổi hướng"* chỉ có
    nghĩa `UP → DOWN`. Chọn cách chặt hơn vì hai lẽ — `FLAT` được định
    nghĩa là *"chưa có bằng chứng trend"* (không phải "trend yếu"), và
    §2.5 đã tự loại `FLAT` ở bước vào lệnh; cho phép bơm thêm tiền vào
    một bối cảnh mà chính hệ thống sẽ không cho mở lệnh mới là mâu thuẫn
    với chính nó. Cùng phép so đồng nhất mà `xac_nhan_da_khung()` dùng.
    """
    return trend_dir_tai_tranche1 == trend_dir_hien_tai


def dg3_margin_con_nguyen(
    *, margin_reserve_con_lai: float, margin_can_cho_tranche: float
) -> bool:
    """DG3 — phần margin đã giữ chỗ cho tranche này chưa bị hệ thống khác
    ăn mất.

    Số âm ở một trong hai vế là dấu hiệu kế toán margin đã hỏng ở tầng
    trên, không phải "cổng đóng" — raise chứ không trả `False`.
    """
    if margin_reserve_con_lai < 0 or margin_can_cho_tranche < 0:
        raise TrancheGateError(
            f"margin không được âm: còn lại={margin_reserve_con_lai}, "
            f"cần={margin_can_cho_tranche} — kế toán margin ở tầng trên đã hỏng"
        )
    return margin_reserve_con_lai >= margin_can_cho_tranche


def dg4_con_trong_cua_so_cho(*, so_nen_1h_da_troi: int, dg4_bars_1h: int) -> bool:
    """DG4 — không quá `dg4_bars_1h` nến 1H kể từ khi tranche 1 KHỚP.

    Đơn vị nằm trong TÊN BIẾN (`_1h`, `_bars_`) theo câu hỏi mở #12 — để
    không lặp lại lỗi *"2×k"* đã bị bác ở DR-010, nơi một con số không
    mang đơn vị bị hiểu theo hai thang khác nhau.

    `dg4_bars_1h` là tham số bắt buộc, đọc từ `tool_d_config.yaml`
    (`tier_b.dg4_bars_1h`, tunable #7) — N4 cấm hardcode. Ngưỡng là
    **≤**, đúng chữ *"≤ 8 nến"* của §4.
    """
    if so_nen_1h_da_troi < 0:
        raise TrancheGateError(f"số nến đã trôi không được âm: {so_nen_1h_da_troi}")
    if dg4_bars_1h <= 0:
        raise TrancheGateError(
            f"dg4_bars_1h phải > 0, nhận {dg4_bars_1h} — cửa sổ chờ bằng 0 làm "
            "tranche 2/3 KHÔNG BAO GIỜ khớp được, tức tắt DCA một cách âm thầm"
        )
    return so_nen_1h_da_troi <= dg4_bars_1h


def dg5_zss_khong_suy_yeu(
    *, zss_tai_tranche1: float, zss_hien_tai: float, nguong_giam_toi_da: float
) -> bool:
    """DG5 — ZSS tính lại không giảm quá `nguong_giam_toi_da` (tỉ lệ, ví
    dụ `0.30` cho 30%) so với lúc tranche 1.

    🔴 `nguong_giam_toi_da` **không có mặc định** — xem mục 1 của
    docstring module. Ngưỡng 30% của §4 chưa có trong `tool_d_config.yaml`
    và chưa có dòng nào trong kiểm kê DOF; điền hộ một con số ở đây là
    tạo ra một bậc tự do không ai đếm, đúng thứ `N_ĐĂNG_KÝ` tồn tại để
    kiểm soát.

    So sánh theo **tỉ lệ tương đối**, không phải hiệu tuyệt đối: chữ của
    §4 là *"giảm > 30%"*. Cả hai `zss` phải do `zone_strength.zss()`
    sinh ra — module này KHÔNG tính lại ZSS, chỉ so hai giá trị; viết
    lại phép tính là tạo nguồn sự thật thứ hai cho cùng một đại lượng.
    """
    if not 0 < nguong_giam_toi_da < 1:
        raise TrancheGateError(
            f"nguong_giam_toi_da phải nằm trong (0, 1), nhận {nguong_giam_toi_da} "
            "— đây là TỈ LỆ giảm (0.30 = 30%), không phải phần trăm"
        )
    # 🐛 TD-0170 — `NaN` phải RAISE, không được trả `False`.
    #
    # `NaN >= x` là `False` theo IEEE-754, nên bản đầu của hàm này **im
    # lặng trả `False`** khi `zss_hien_tai` không tính được — tức gộp
    # *"không đo được"* vào *"cổng đóng"*, đúng hai thứ `TrancheGateError`
    # sinh ra để tách và N6 cấm gộp. Đường chạy thật đưa `NaN` vào đây
    # thật: `ZoneAbsorption._zss_hien_tai()` trả `float("nan")` khi
    # `volume_ratio`/`compression` thiếu dữ liệu.
    #
    # Nguy hơn một ô trống: một cổng "đóng" trông giống hệt một quyết định
    # đã cân nhắc, nên không ai đi hỏi vì sao. Và `ZoneAbsorption.py:505`
    # đã ghi sẵn *"dg5 fail-closed với NaN (TrancheGateError)"* — một chú
    # thích mô tả theo Ý ĐỊNH chứ không theo thứ code làm, cùng hạng
    # `_comment_stake_amount` của MT-16.
    if math.isnan(zss_hien_tai) or math.isnan(zss_tai_tranche1):
        raise TrancheGateError(
            f"ZSS không đọc được (zss_tai_tranche1={zss_tai_tranche1}, "
            f"zss_hien_tai={zss_hien_tai}) — 'không đo được' KHÁC 'cổng đóng'. "
            "Bên gọi phải xử tường minh, không nhận một `False` im lặng"
        )
    if zss_tai_tranche1 <= 0:
        raise TrancheGateError(
            f"zss_tai_tranche1 = {zss_tai_tranche1} ≤ 0 — zone đã vào lệnh phải có "
            "ZSS ≥ ngưỡng §1.3; giá trị này nghĩa là ZSS lúc tranche 1 không được "
            "ghi lại đúng, và 'giảm bao nhiêu %' so với 0 là câu hỏi vô nghĩa"
        )
    return zss_hien_tai >= zss_tai_tranche1 * (1 - nguong_giam_toi_da)


def danh_gia_tat_ca(
    *,
    close_4h_ke_tu_tranche1: Sequence[float],
    sl: float,
    huong: Huong,
    trend_dir_tai_tranche1: TrendDir,
    trend_dir_hien_tai: TrendDir,
    margin_reserve_con_lai: float,
    margin_can_cho_tranche: float,
    so_nen_1h_da_troi: int,
    dg4_bars_1h: int,
    zss_tai_tranche1: float,
    zss_hien_tai: float,
    nguong_giam_toi_da: float,
) -> dict[str, bool]:
    """Cả năm cổng, trả về đúng hình dạng khối `gates` của decision log
    (§8): `{"DG1": bool, ..., "DG5": bool}`.

    Có hàm này vì hình dạng bản ghi đó là thứ được ĐẶC TẢ; để mỗi chỗ
    gọi tự lắp lấy là mời hai bản ghi trôi lệch tên khoá. Nó **không**
    quyết định gì thêm — không có công tắc bật/tắt cổng ở đây (Z2 tắt
    DG5 là việc của TD-0183), và **không** gộp năm `bool` thành một
    `bool`: ai cần "được bơm không" thì tự `all(...)`, và khi đó họ nhìn
    thấy mình đang bỏ qua thông tin cổng nào đã chặn.
    """
    return {
        "DG1": dg1_zone_con_nguyen(
            close_4h_ke_tu_tranche1=close_4h_ke_tu_tranche1, sl=sl, huong=huong
        ),
        "DG2": dg2_trend_con_dung(
            trend_dir_tai_tranche1=trend_dir_tai_tranche1,
            trend_dir_hien_tai=trend_dir_hien_tai,
        ),
        "DG3": dg3_margin_con_nguyen(
            margin_reserve_con_lai=margin_reserve_con_lai,
            margin_can_cho_tranche=margin_can_cho_tranche,
        ),
        "DG4": dg4_con_trong_cua_so_cho(
            so_nen_1h_da_troi=so_nen_1h_da_troi, dg4_bars_1h=dg4_bars_1h
        ),
        "DG5": dg5_zss_khong_suy_yeu(
            zss_tai_tranche1=zss_tai_tranche1,
            zss_hien_tai=zss_hien_tai,
            nguong_giam_toi_da=nguong_giam_toi_da,
        ),
    }
