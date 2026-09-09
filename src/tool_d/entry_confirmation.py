"""§3.3b + PHẦN 3b — Xác nhận entry tranche 1 bằng price-action (TD-0129,
trước 07/09/2026 đánh số TD-0120; L-Z6).

ZSS (§1.2) chỉ đo chất lượng LỊCH SỬ của zone; đây là lớp xác nhận hấp
thụ đang diễn ra NGAY LÚC giá chạm zone, tối đa 3 nến chờ, KHÔNG mở rộng
cửa sổ (chống overfitting ngược — nới thời gian chờ tới khi thấy xác
nhận sẽ luôn "thành công" trên dữ liệu lịch sử nhưng vô nghĩa).

RSI(14,1H) và volume_MA(20,1H) tính ở tầng gọi (cùng kiểu với ATR trong
`zone_strength.py`) — module này chỉ nhận mảng đã tính sẵn.

════ Công thức: `(a VÀ c) HOẶC (b)` — KHÔNG phải `(a OR b OR c)` ════

    (a) nến rejection          §3.3b(a)
    (b) phân kỳ momentum RSI   §3.3b(b)
    (c) hấp thụ có volume      PHẦN 3b — BỔ NGỮ BẮT BUỘC cho (a)

Spec PHẦN 3b nói thẳng vì sao (c) không đứng riêng: *"Volume cao mà
không có rejection = có thể đang bị xuyên qua."*

🔴 **MT-15 — vì sao bản đầu SAI, và vì sao nó không chỉ là thiếu một bộ
lọc.** Bản đầu (TD-0129) thi hành `(a) HOẶC (b)`: (c) có **0 dòng code**.
Nhưng §10.1b định nghĩa arm `Z0-V1` **đúng bằng "tắt (c)"**, tức `(a)
HOẶC (b)` — chính là thứ code khi đó đang có. Hệ quả: `Z0` **trùng khớp**
`Z0-V1`, một suất trial trong `N=114` tiêu để đo một khác biệt **bằng
không**, và bảng kết quả trông hoàn toàn bình thường — chỉ là hai cột
giống hệt nhau. Không phép kiểm nào báo đỏ vì nó. Đây là bẫy PASS RỖNG ở
một dạng khác các lần trước: **nó không làm hỏng phép đo, nó đốt ngân
sách phép thử.**

Vì thế `bat_dieu_kien_c` là tham số **BẮT BUỘC, không mặc định** — cùng
khuôn `truoc_ms`/`sau_ms` của `fill_probe` (TD-0162). Một mặc định ở đây
nghĩa là arm nào quên khai sẽ lặng lẽ chạy như arm khác, và hai arm lại
nhập làm một.

`v_min` = `tier_b.v_min`, hiện **FROZEN ở 1.0** (DR-D4-03) — mốc trung
tính của tỉ lệ so với chính trung bình 20 kỳ của nó, **chỗ giữ CHƯA
CALIBRATE**. Đọc kèm mọi kết quả có `Z0` tham gia.

════ TD-0193 — `quet_xac_nhan_zone()`: chuỗi lần chạm trong vòng đời zone ════

`tim_xac_nhan_entry()` ở trên trả lời cho MỘT lần chạm. §3.3b/MT-22 còn
cần câu hỏi rộng hơn: một zone có thể bị chạm NHIỀU lần trong vòng đời —
mỗi lần là một cơ hội xác nhận riêng, với cửa sổ chờ 3 nến riêng.

🔴 **MT-22 (09/09/2026, chủ dự án chốt) — Phương án A: cửa sổ chờ xác
nhận mở ĐÚNG MỘT LẦN, ở lần chạm đầu tiên.** Trượt ở lần đó thì BỎ LƯỢT
zone này VĨNH VIỄN cho giao dịch thật — không quay lại tìm ở lần chạm
xa hơn. Lý do chọn A thay vì "mở lại mỗi lần chạm" (B): đo trên 4.944
zone thật (EXPLORE, `docs/du-lieu-do/do_mt22_a_vs_b.py`) A cho 43,1% zone
vào lệnh, B cho 81,2% — B mua thêm gần gấp đôi số lần thử trên CÙNG một
zone, và hướng sai của B (vào lệnh nhờ thử nhiều lần) nguy hiểm hơn
hướng sai của A (bỏ lỡ).

**Ghi PHẢN THỰC cho B — CHỈ để đếm, KHÔNG BAO GIỜ phát tín hiệu thật.**
Điều kiện mở lại BẤT ĐỐI XỨNG (chốt cùng MT-22, sau khi `-f4` bác bản đầu
"0 trial cho cả hai chiều"): *loại B ra* — làm được, 0 trial, chỉ cần
ĐẾM (phần B thêm quá ít, hoặc dồn vào lần chạm muộn khi zone gần hết
hạn). *Nhận B vào* — KHÔNG có đường tắt, phải trả một suất trial B1
đăng ký trước; con số phản thực là CẬN TRÊN của B (chạy trên đường A nên
không có các vị thế mà B đã mở, bỏ qua cổng kết nạp danh mục §6.8f và
ảnh hưởng lên `mult_corr`/`mult_deploy` của lệnh sau), không phải bằng
chứng expectancy.

════ Diễn giải, ghi ra để cãi lại được ════

1. **Mốc cho (b) ở lượt sau = (giá, RSI) TẠI NẾN CHẠM** của lượt trước
   (bar bắt đầu lượt, `t`), KHÔNG phải tại nến nào trong cửa sổ xác nhận
   của lượt đó. (b) đo hình dạng giá GIỮA HAI LẦN CHẠM — quan hệ đó
   không đổi theo việc lượt trước có tìm được xác nhận hay không (đúng
   khuôn "bất kỳ", không phải "đã xác nhận").
2. **"Chạm"** = một CỤM nến liên tiếp nằm trong `[zone_low, zone_high]`,
   kết thúc khi giá RA khỏi khoảng đó — cùng khái niệm cụm của
   `touch_count()`, nhưng dùng lại VỊ TỪ trần (`zone_low <= gia <=
   zone_high`), KHÔNG dùng lại hàm đó: `touch_count()` cần biết điểm
   BẬT RA để đếm cụm ĐÃ HOÀN TẤT — tức đọc nến SAU — sai ngữ cảnh câu
   "tại `t` có phải điểm BẮT ĐẦU một lượt chạm không" mà hàm này cần trả
   lời ngay tại `t`, không nhìn về sau.
3. **`den`** (biên cứng của cửa sổ quét) do TẦNG GỌI truyền, hàm này
   không tự suy ra. Khuyến nghị dùng đúng `NGUONG_TUOI_ZONE_TOI_DA`
   (`zone_strength.py`, §1.3, 40 nến 4H) quy đổi sang 1H — vì
   `zone_hop_le()` hiện gọi với `tuoi_nen=K_XAC_NHAN` (hằng 3), cùng
   tautology mà `MT-19`/`TD-0189` bắt được ở zone TP (`3 <= 40` luôn
   đúng, không kiểm được tuổi thật). Khác với zone TP (nơi §1.3 áp dụng
   có tranh cãi, thành `MT-20`/`DR-D4-06`), với zone ENTRY thì §1.3 là
   đúng đối tượng nó viết ra để áp — không cần diễn giải riêng.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, Sequence

SO_NEN_CHO_MAC_DINH = 3


class ThieuDuLieuVolumeError(ValueError):
    """`bat_dieu_kien_c=True` nhưng thiếu `volume` / `volume_ma` / `v_min`.

    Fail-closed, KHÔNG âm thầm bỏ qua (c): bỏ qua nghĩa là chạy `Z0-V1`
    dưới nhãn `Z0`, và không gì trong kết quả lộ ra điều đó — đúng lỗ
    hổng MT-15 sinh ra để đóng.
    """


def la_nen_rejection(mo: float, cao: float, thap: float, dong: float, *, loai: Literal["day", "dinh"]) -> bool:
    """§3.3b(a) — bóng đối hướng ≥50% range nến, đóng cửa nửa còn lại.

    Zone đáy (`loai="day"`, case LONG): bóng DƯỚI ≥50% range, đóng cửa
    trong nửa TRÊN. Zone đỉnh (`loai="dinh"`) đảo dấu.
    """
    bien_do = cao - thap
    if bien_do <= 0:
        return False
    if loai == "day":
        bong_duoi = min(mo, dong) - thap
        return bong_duoi >= 0.5 * bien_do and dong >= thap + 0.5 * bien_do
    bong_tren = cao - max(mo, dong)
    return bong_tren >= 0.5 * bien_do and dong <= cao - 0.5 * bien_do


def phan_ky_momentum(
    *, rsi_hien_tai: float, gia_hien_tai: float, rsi_truoc: float, gia_truoc: float, loai: Literal["day", "dinh"]
) -> bool:
    """§3.3b(b) — zone đáy: RSI tạo đáy CAO HƠN trong khi giá tạo đáy
    THẤP HƠN hoặc BẰNG so với lần chạm trước. Zone đỉnh đảo dấu."""
    if loai == "day":
        return rsi_hien_tai > rsi_truoc and gia_hien_tai <= gia_truoc
    return rsi_hien_tai < rsi_truoc and gia_hien_tai >= gia_truoc


def hap_thu_co_volume(volume_nen: float, volume_ma_1h: float, v_min: float) -> bool:
    """PHẦN 3b điều kiện (c) — `volume(nến xác nhận) / volume_MA(20,1H) ≥ v_min`.

    🔴 KHÔNG phải tín hiệu độc lập. Việc AND với (a) nằm ở
    `tim_xac_nhan_entry()`; hàm này chỉ trả lời vế volume.

    Mẫu số không hợp lệ (≤ 0 hoặc NaN) → `False`. Không có mẫu số nghĩa
    là *chưa biết*, và "chưa biết" ở cổng vào lệnh phải tính về phía
    KHÔNG vào — cùng tinh thần `volume_ratio`/`compression` của
    `zone_strength.py` trả `None` thay vì đoán.
    """
    if volume_ma_1h != volume_ma_1h or volume_nen != volume_nen:  # NaN != NaN
        return False
    if volume_ma_1h <= 0:
        return False
    return volume_nen / volume_ma_1h >= v_min


def tim_xac_nhan_entry(
    mo: Sequence[float],
    cao: Sequence[float],
    thap: Sequence[float],
    dong: Sequence[float],
    rsi: Sequence[float],
    i_cham: int,
    *,
    loai: Literal["day", "dinh"],
    bat_dieu_kien_c: bool,
    volume: Sequence[float] | None = None,
    volume_ma: Sequence[float] | None = None,
    v_min: float | None = None,
    lan_cham_truoc: tuple[float, float] | None = None,
    so_nen_cho_toi_da: int = SO_NEN_CHO_MAC_DINH,
) -> int | None:
    """Quét tối đa `so_nen_cho_toi_da` nến kể từ `i_cham` (nến giá vừa
    chạm zone), tìm nến đầu tiên thoả **`(a VÀ c) HOẶC (b)`**. Trả về
    chỉ số nến đó, hoặc `None` nếu hết hạn mà chưa có — KHÔNG BAO GIỜ
    tìm tiếp ngoài cửa sổ này (đúng lời spec, chống overfitting ngược).

    `bat_dieu_kien_c` **bắt buộc khai** (xem docstring module — MT-15):
      • `True`  → arm `Z0` và mọi arm khác: đòi đủ `volume`/`volume_ma`/`v_min`.
      • `False` → arm `Z0-V1`: công thức thoái về `(a) HOẶC (b)`.

    `lan_cham_truoc` = (giá, RSI) của lần chạm zone gần nhất — `None`
    nếu đây là lần chạm đầu tiên (không có gì để so, chỉ còn phần (a)).
    """
    if bat_dieu_kien_c and (volume is None or volume_ma is None or v_min is None):
        raise ThieuDuLieuVolumeError(
            "bat_dieu_kien_c=True đòi đủ volume, volume_ma và v_min. Thiếu một "
            "trong ba thì KHÔNG được bỏ qua (c) — bỏ qua là chạy Z0-V1 dưới "
            "nhãn Z0 (MT-15)."
        )

    gia_bien_muc = thap if loai == "day" else cao
    cuoi = min(i_cham + so_nen_cho_toi_da, len(dong))
    for j in range(i_cham, cuoi):
        # (a VÀ c) — (c) là BỔ NGỮ của (a), không đứng riêng.
        if la_nen_rejection(mo[j], cao[j], thap[j], dong[j], loai=loai):
            if not bat_dieu_kien_c or hap_thu_co_volume(volume[j], volume_ma[j], v_min):
                return j
        # HOẶC (b) — phân kỳ momentum KHÔNG đi kèm (c).
        # 🔑 Nến bị (c) loại ở trên VẪN rơi xuống đây: công thức là
        # `(a VÀ c) HOẶC (b)`, không phải `nếu (a) thì (c) ngược lại (b)`.
        if lan_cham_truoc is not None:
            gia_truoc, rsi_truoc = lan_cham_truoc
            if phan_ky_momentum(
                rsi_hien_tai=rsi[j], gia_hien_tai=gia_bien_muc[j], rsi_truoc=rsi_truoc, gia_truoc=gia_truoc, loai=loai
            ):
                return j
    return None


@dataclass(frozen=True)
class KetQuaQuetXacNhanZone:
    """Kết quả `quet_xac_nhan_zone()` — xem docstring module (TD-0193)."""

    nen_xac_nhan_that: int | None
    """Nến xác nhận theo Phương án A (MT-22, đang thi hành). `None` =
    lần chạm đầu tiên KHÔNG xác nhận trong cửa sổ chờ ⇒ BỎ LƯỢT, zone
    không giao dịch nữa dù giá có quay lại chạm sau đó."""

    nen_xac_nhan_phan_thuc: int | None
    """Nến xác nhận NẾU chạy Phương án B (mọi lượt chạm, tới khi thành
    công). CHỈ để ghi sổ — KHÔNG BAO GIỜ dùng để phát tín hiệu thật.
    `None` = không lượt chạm nào trong toàn vòng đời zone xác nhận
    được."""

    lan_cham_phan_thuc: int
    """Lượt chạm thứ mấy (1-based) mà phản thực xác nhận. `0` nếu
    `nen_xac_nhan_phan_thuc is None`. `== 1` nghĩa là B trùng A (không
    mua thêm gì); `> 1` nghĩa là B mua thêm nhờ được thử lại — đây là
    con số đáng đếm cho điều kiện mở lại BẤT ĐỐI XỨNG của MT-22."""


def quet_xac_nhan_zone(
    mo: Sequence[float],
    cao: Sequence[float],
    thap: Sequence[float],
    dong: Sequence[float],
    rsi: Sequence[float],
    volume: Sequence[float],
    volume_ma: Sequence[float],
    *,
    zone_low: float,
    zone_high: float,
    tu: int,
    den: int,
    v_min: float,
    loai: Literal["day", "dinh"],
    lan_cham_truoc_khi_xac_nhan: tuple[float, float] | None,
    so_nen_cho_toi_da: int = SO_NEN_CHO_MAC_DINH,
) -> KetQuaQuetXacNhanZone:
    """Quét TOÀN BỘ vòng đời chờ xác nhận của MỘT zone trên `[tu, den)`.

    §3.3b/MT-22 Phương án A: chỉ lần chạm ĐẦU TIÊN quyết định
    `nen_xac_nhan_that`. Vòng lặp vẫn tiếp tục sau đó — không vì mục
    đích giao dịch thật, mà để ghi `nen_xac_nhan_phan_thuc` (Phương án
    B). `nen_xac_nhan_that` được gán ĐÚNG MỘT LẦN, ở lượt đầu, và không
    đổi dù hàm quét xa tới đâu sau đó (bất biến — có test ghim).

    `zone_low <= gia_bien_muc[t] <= zone_high` là vị từ CHẠM — xem diễn
    giải #2 trong docstring module về vì sao không dùng `touch_count()`.
    """
    gia_bien_muc = thap if loai == "day" else cao
    lan_cham_truoc = lan_cham_truoc_khi_xac_nhan
    lan = 0
    nen_xac_nhan_that: int | None = None
    nen_xac_nhan_phan_thuc: int | None = None
    lan_cham_phan_thuc = 0

    t = tu
    while t < den:
        if not (zone_low <= gia_bien_muc[t] <= zone_high):
            t += 1
            continue

        # `t` là điểm BẮT ĐẦU một lượt chạm mới.
        lan += 1
        c = tim_xac_nhan_entry(
            mo, cao, thap, dong, rsi, t,
            loai=loai, bat_dieu_kien_c=True,
            volume=volume, volume_ma=volume_ma, v_min=v_min,
            lan_cham_truoc=lan_cham_truoc, so_nen_cho_toi_da=so_nen_cho_toi_da,
        )
        if lan == 1:
            nen_xac_nhan_that = c  # Phương án A: gán MỘT LẦN, không đổi nữa.
        if c is not None:
            nen_xac_nhan_phan_thuc = c
            lan_cham_phan_thuc = lan
            break

        # Mốc cho lượt sau — TẠI NẾN CHẠM `t` (diễn giải #1). NaN thì
        # KHÔNG raise (quét lịch sử dài, một nến hỏng giữa chừng không
        # được làm hỏng toàn vòng quét) — chỉ đơn giản không cập nhật
        # được mốc, lượt sau thiếu mốc cho (b).
        if rsi[t] == rsi[t]:  # not NaN
            lan_cham_truoc = (gia_bien_muc[t], rsi[t])

        # Nhảy qua HẾT lượt chạm hiện tại (tới khi giá RA khỏi zone)
        # trước khi tìm lượt kế — một cụm liên tiếp chỉ là MỘT lượt.
        while t < den and (zone_low <= gia_bien_muc[t] <= zone_high):
            t += 1

    return KetQuaQuetXacNhanZone(
        nen_xac_nhan_that=nen_xac_nhan_that,
        nen_xac_nhan_phan_thuc=nen_xac_nhan_phan_thuc,
        lan_cham_phan_thuc=lan_cham_phan_thuc,
    )
