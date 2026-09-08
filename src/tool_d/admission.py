"""TD-0188 — KIỂM TRA KẾT NẠP DANH MỤC (§6.8f Bước 2) — MT-16, DR-D4-04.

`sizing.py` trả lời *"lệnh này TO bao nhiêu"*. Module này trả lời một câu
khác hẳn: *"có được MỞ không"*. Gộp hai câu là cách một lệnh bị từ chối
trông giống một lệnh cỡ 0 — và cỡ 0 thì không ai đọc ra được lý do.

════ Hai điều kiện, xét SAU KHI mở, phải thoả CẢ HAI ════

    (a) Σ rủi ro (mọi vị thế, KẾ HOẠCH đầy đủ — D0.5) ≤ daily_loss_budget_pct × E_D
        🔴 với GIẢ ĐỊNH TƯƠNG QUAN = 1 (§6.8d)
    (b) Σ margin (mọi vị thế, KẾ HOẠCH đầy đủ — D0.3) ≤ 0.85 × E_D

    Không thoả một trong hai → KHÔNG MỞ, **bất kể ZSS cao thế nào**.

🔑 **"KẾ HOẠCH ĐẦY ĐỦ" là chỗ dễ sai nhất.** Cả hai tổng tính trên notional
của **cả ba tranche**, kể cả tranche chưa khớp — vì margin đã được giữ chỗ
(D0.3) và rủi ro đã cam kết (D0.5) ngay từ tranche 1. Tính theo phần ĐÃ
khớp sẽ cho mở nhiều lệnh hơn mức chịu được, và sai lệch chỉ lộ ra đúng lúc
mọi lệnh đều khớp đủ — tức đúng lúc thị trường sập.

🔴 **Vì sao TƯƠNG QUAN = 1 là bắt buộc** (§6.8d): altcoin tương quan 0,7–0,85
với BTC, và trong một cú sập tương quan thực tế **tiến về 1**. Định cỡ theo
giả định các lệnh độc lập là định cỡ cho một thị trường KHÔNG TỒN TẠI. Nên
điều kiện (a) **cộng thẳng** rủi ro, không có hệ số giảm nào.

════ Số vị thế tối đa là KẾT QUẢ, không phải tham số ════

`max_open_trades = 100` trong `config/freqtrade/config.json` chỉ là trần an
toàn phía Freqtrade (= `pool_size_target`). Số vị thế THẬT do chính hai điều
kiện trên quyết định, và nó **dao động theo độ rộng zone** của các lệnh đang
mở — zone hẹp thì `R_eff` nhỏ, notional lớn, nhét được ít mã hơn.

Bảng ví dụ của spec (`E_D`=500, `rho`=0,375%, `L`=3x, `daily_loss`=8%):

| `R_eff` | Notional/lệnh | Margin/lệnh | Số mã tối đa | Ràng buộc siết |
|---|---|---|---|---|
| 0,9 % | 208 | 69,4 | **6**  | margin |
| 1,5 % | 125 | 41,7 | **10** | margin |
| 2,0 % |  94 | 31,3 | **13** | margin |
| 3,0 % |  62 | 20,8 | **20** | margin |

🔑 Mọi hàng cho **cùng một tổng notional** (6×208 = 20×62 = 1250) — vì trần
thật là `0.85 × E_D × L_exchange` = 1275. Đó chính là lý do v6 **XOÁ trần đòn
bẩy tổng của danh mục** (§6.8c): nó không phải một trần độc lập, nó là
`0.85 × L_exchange` mang một cái tên khác. `tinh_tran_notional_danh_muc()`
và test khoá của nó ghim đúng bất biến này.

⚠️ Tên cũ của trần đã xoá đó **cố ý không viết ra ở đây**: `L-Z32` (CRITICAL)
grep toàn repo và **không strip docstring**. Bản đầu của module này viết
thẳng tên và làm `L-Z32` đỏ — đúng hình dạng đã cắn nhiều lần trước ở các
luật cấm-chuỗi khác (`L-Z25`, `L-Z46`), luôn xử bằng **diễn đạt lại, KHÔNG
nới phép kiểm**. Quy ước từ đây: nhắc lệnh cấm bằng MÃ LUẬT (`L-Z32`,
`L-Z46`, …), không lặp lại chính chuỗi bị cấm — kể cả khi đang kể chuyện
về lần trước bị cấm, như đoạn này suýt tự vi phạm. Muốn tra tên cũ thì đọc
`§6.8c` hoặc `config/tool_d_config.yaml` — nơi nó nằm dưới dạng chú thích
lịch sử mà `L-Z32` cố ý cho phép (test có strip comment).

⚠️ **Ở 3x, trần RỦI RO không bao giờ chạm tới** — margin luôn siết trước
(21 lệnh vs 6–20). Ở 5x với zone rộng thì đảo lại. Đây là lý do phải kiểm
**CẢ HAI** điều kiện chứ không chọn một; bỏ (a) vì "nó không bao giờ bind"
là đúng ở 3x và sai ở 5x, mà `L_exchange` là Tầng A **chỉnh tự do**.

════ Quan hệ với `mult_deploy` (§6.2 hệ số 6) ════

`mult_deploy` chạy TRƯỚC, ở tầng định cỡ, và đo **mức phơi nhiễm THẬT**
(Σ notional đã khớp / Σ notional kế hoạch). Module này đo **margin đã giữ
chỗ theo kế hoạch**. Hai con số khác nhau; `mult_deploy` là lớp phòng thủ
thứ hai, **không thay thế** bước kết nạp (spec cảnh báo rõ: đọc nó theo
nghĩa "Σ margin / E_D" thì nó thành code chết vì trùng đúng ngưỡng 0,85).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from tool_d.config.loader import ToolDConfig, resolve
from tool_d.sizing import KeHoachCoLenh

#: Trần margin trên `E_D` — §6.8f điều kiện (b). HẰNG SỐ CẤP C.
#:
#: 🔑 Cố ý KHÔNG thêm khoá YAML mới cho nó. `tier_frozen.mult_deploy_thr`
#: đã mang đúng con số này, và `frozen_rationale` của nó ghi rõ *"dùng lại
#: hằng số ĐÃ CÓ ở §6.8f (trần margin), 0 hằng số mới"* — tức §6.8f là GỐC,
#: `mult_deploy` là bên MƯỢN. Thêm một khoá thứ ba là tạo nguồn sự thật thứ
#: hai cho cùng một số (bài học MT-03). Thay vào đó có test khoá ghim hằng
#: số này BẰNG `tier_frozen.mult_deploy_thr.value`: lệch nhau là đỏ.
TRAN_MARGIN_TREN_E_D = 0.85


class AdmissionError(ValueError):
    """Đầu vào kết nạp không hợp lệ. Fail-closed: raise, KHÔNG trả
    `duoc_mo=False` — "dữ liệu hỏng" khác hẳn "danh mục đã đầy", và gộp
    hai thứ là cách một lỗi kế toán biến thành một quyết định giao dịch."""


@dataclass(frozen=True)
class ViTheMo:
    """Một vị thế đang mở, ở mức KẾ HOẠCH ĐẦY ĐỦ (không phải phần đã khớp)."""

    planned_risk_usdt: float
    planned_margin_usdt: float

    def __post_init__(self) -> None:
        for ten, v in (("planned_risk_usdt", self.planned_risk_usdt),
                       ("planned_margin_usdt", self.planned_margin_usdt)):
            if v != v or v <= 0:
                raise AdmissionError(
                    f"{ten} = {v} phải > 0 — một vị thế đang mở luôn có rủi ro và "
                    "margin dương; số 0 hoặc âm là kế toán ở tầng trên đã hỏng"
                )

    @classmethod
    def tu_ke_hoach(cls, kh: KeHoachCoLenh) -> "ViTheMo":
        return cls(planned_risk_usdt=kh.planned_risk_usdt, planned_margin_usdt=kh.planned_margin_usdt)


@dataclass(frozen=True)
class KetQuaKetNap:
    duoc_mo: bool
    tong_rui_ro_sau_khi_mo: float
    tran_rui_ro: float
    tong_margin_sau_khi_mo: float
    tran_margin: float
    so_vi_the_truoc: int

    @property
    def rui_ro_dat(self) -> bool:
        return self.tong_rui_ro_sau_khi_mo <= self.tran_rui_ro

    @property
    def margin_dat(self) -> bool:
        return self.tong_margin_sau_khi_mo <= self.tran_margin

    @property
    def rang_buoc_siet(self) -> str | None:
        """Điều kiện nào CHẶN. `None` khi được mở.

        Khi cả hai cùng vượt, trả `"cả hai"` — không chọn một để báo, vì
        người đọc sẽ nới đúng cái được báo rồi vẫn bị chặn bởi cái kia."""
        if self.duoc_mo:
            return None
        if not self.rui_ro_dat and not self.margin_dat:
            return "cả hai"
        return "rủi ro" if not self.rui_ro_dat else "margin"

    def dien_giai(self) -> str:
        if self.duoc_mo:
            return (
                f"KẾT NẠP — rủi ro {self.tong_rui_ro_sau_khi_mo:.4f}/{self.tran_rui_ro:.4f} · "
                f"margin {self.tong_margin_sau_khi_mo:.4f}/{self.tran_margin:.4f} "
                f"({self.so_vi_the_truoc} vị thế trước đó)"
            )
        return (
            f"TỪ CHỐI ({self.rang_buoc_siet}) — rủi ro {self.tong_rui_ro_sau_khi_mo:.4f}/"
            f"{self.tran_rui_ro:.4f} · margin {self.tong_margin_sau_khi_mo:.4f}/"
            f"{self.tran_margin:.4f} ({self.so_vi_the_truoc} vị thế trước đó)"
        )


def tinh_tran_notional_danh_muc(*, e_d: float, l_exchange: float) -> float:
    """Trần notional TOÀN DANH MỤC = `0.85 × E_D × L_exchange`.

    Đây KHÔNG phải một điều kiện thứ ba — nó là điều kiện (b) viết ở đơn vị
    notional, và là con số làm mọi hàng trong bảng ví dụ §6.8f cho cùng tổng
    1250. Hàm này tồn tại để test khoá được bất biến đó, và để không ai dựng
    lại trần đòn bẩy tổng mà v6 đã xoá (§6.8c — xem cảnh báo `L-Z32` ở
    docstring module về việc KHÔNG viết tên cũ ra)."""
    if e_d <= 0 or l_exchange < 1:
        raise AdmissionError(f"E_D = {e_d} phải > 0 và L_exchange = {l_exchange} phải ≥ 1")
    return TRAN_MARGIN_TREN_E_D * e_d * l_exchange


def kiem_ket_nap(
    *,
    cfg: ToolDConfig,
    ung_vien: KeHoachCoLenh,
    dang_mo: Sequence[ViTheMo],
) -> KetQuaKetNap:
    """§6.8f Bước 2 — `duoc_mo=True` chỉ khi CẢ HAI điều kiện thoả SAU KHI mở.

    `dang_mo` là các vị thế **khác** (không gồm ứng viên). Chỗ gọi chịu
    trách nhiệm không đưa trùng — đưa trùng làm tổng bị đếm hai lần và
    lệnh bị từ chối oan, một hỏng hóc an toàn nhưng vẫn là hỏng hóc.
    """
    e_d = float(resolve(cfg, "tier_a.E_D"))
    daily_loss_pct = float(resolve(cfg, "tier_a.daily_loss_budget_pct"))
    if e_d <= 0 or not (0 < daily_loss_pct <= 100):
        raise AdmissionError(f"E_D = {e_d}, daily_loss_budget_pct = {daily_loss_pct} không hợp lệ")

    tran_rui_ro = daily_loss_pct / 100.0 * e_d
    tran_margin = TRAN_MARGIN_TREN_E_D * e_d
    tong_rui_ro = sum(v.planned_risk_usdt for v in dang_mo) + ung_vien.planned_risk_usdt
    tong_margin = sum(v.planned_margin_usdt for v in dang_mo) + ung_vien.planned_margin_usdt

    kq = KetQuaKetNap(
        duoc_mo=False,  # đặt lại ngay dưới; khởi tạo False là fail-closed nếu ai sửa ẩu
        tong_rui_ro_sau_khi_mo=tong_rui_ro,
        tran_rui_ro=tran_rui_ro,
        tong_margin_sau_khi_mo=tong_margin,
        tran_margin=tran_margin,
        so_vi_the_truoc=len(dang_mo),
    )
    return KetQuaKetNap(
        duoc_mo=kq.rui_ro_dat and kq.margin_dat,
        tong_rui_ro_sau_khi_mo=tong_rui_ro,
        tran_rui_ro=tran_rui_ro,
        tong_margin_sau_khi_mo=tong_margin,
        tran_margin=tran_margin,
        so_vi_the_truoc=len(dang_mo),
    )


__all__ = [
    "TRAN_MARGIN_TREN_E_D",
    "AdmissionError",
    "KetQuaKetNap",
    "ViTheMo",
    "kiem_ket_nap",
    "tinh_tran_notional_danh_muc",
]
