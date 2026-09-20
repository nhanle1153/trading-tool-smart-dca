"""TD-0238 — Đỉnh equity phải BỀN VỮNG qua restart tiến trình (MT-40).

`ZoneAbsorption.py:286` khởi tạo `self._dinh_equity: float | None = None`
mỗi lần tiến trình strategy chạy — kể cả khi đó là một lần RESTART giữa
một đợt drawdown sâu, không phải lần chạy đầu tiên thật sự. Hậu quả:
`_dd_pct()` coi equity hiện tại là đỉnh, `dd_pct` về 0%, và `mult_dd()`
(`sizing.py`) không bao giờ chạm ngưỡng `soft`/`halt` — một trong BA
tầng Cấp C (`DR-D0PRE-04`, §12b.2) chặn vòng lặp thua lỗ tự vô hiệu hoá
sau mỗi lần restart.

Hai quyết định đã chốt qua `AskUserQuestion` với chủ dự án (14/09/2026):
(1) cơ chế = checkpoint SỐNG, ghi liên tục mỗi khi có đỉnh mới — KHÔNG
    tính lại từ DB Freqtrade (số dư gốc + cộng dồn `close_profit_abs`),
    vì cách đó bỏ sót phí funding tích luỹ trên vị thế ĐANG MỞ giữa hai
    lần đóng lệnh, có thể đánh giá THẤP đỉnh thật — nới lỏng HALT sai
    hướng an toàn;
(2) chính sách reset = KHÔNG BAO GIỜ — đỉnh là cực đại lịch sử của toàn
    bộ vòng đời sub-account Tool D, chỉ tăng không giảm. Không thêm
    tham số mới vào kiểm kê DOF (né bẫy `DR-D4-02`).

Module này KHÔNG đổi ý nghĩa "equity" (vẫn `wallets.get_total()`, đã
thực hiện) — khoảng hở "equity phải gồm PnL chưa thực hiện" (§12c.5) đã
được `ZoneAbsorption.py` (dòng 61-67) hoãn có chủ đích tới D11, ngoài
phạm vi việc này.

════ Vì sao một module riêng, không gộp vào `sizing.py`/`risk_supervisor.py` ════

`sizing.py` giới hạn ở công thức §6.2 + `KeHoachCoLenh` — `mult_dd()`
bản thân không đổi, chỉ nguồn của `dd_pct` đổi. `risk_supervisor.py`/
`TrangThaiBenVung` thuộc tiến trình RISK SUPERVISOR RIÊNG (§6.6, không
import code bot, TD-0241) — nhét trạng thái tiến trình STRATEGY vào đó
phá đúng ranh giới process vừa dựng xong. Khuôn ghi/đọc nguyên tử CỐ Ý
lặp lại (không factor chung với `risk_supervisor.py`): file đó vừa niêm
phong ở TD-0241, và phần lặp lại chỉ là khuôn I/O chung (~15 dòng),
không phải công thức nghiệp vụ nhân đôi (MT-03 chỉ lo nhân đôi TÍN HIỆU).
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

#: TD-0353 (`DR-TRIEN-KHAI-01`) — thay hằng `DUONG_DAN_MAC_DINH` dùng CHUNG mọi runmode. Dry-run D11 và lệnh live
#: tối thiểu D10 chạy song song; chung một file thì mỗi bên ghi đè đỉnh của bên kia ⇒ `mult_dd` của live tính trên
#: đỉnh của ví giấy (N11: dry-run TÁCH hẳn live).
THU_MUC_GOC = Path("runs/zone_absorption")
TEN_FILE = "equity_peak_state.json"


class DinhEquityError(ValueError):
    """Lỗi đọc/ghi/cập nhật đỉnh equity bền vững — fail-closed, không đoán (N6)."""


def duong_dan_theo_runmode(runmode: str) -> Path:
    """`runs/zone_absorption/<runmode>/equity_peak_state.json`. Chỉ live/dry_run có đỉnh bền vững."""
    if runmode not in ("live", "dry_run"):
        raise DinhEquityError(f"runmode {runmode!r} không có đỉnh equity bền vững — chỉ live/dry_run")
    return THU_MUC_GOC / runmode / TEN_FILE


@dataclass(frozen=True)
class DinhEquityBenVung:
    """Đỉnh equity ĐÃ QUAN SÁT, sống sót qua restart — bài học MT-40.
    Bất biến, cùng kỷ luật `KeHoachCoLenh`/`TrangThaiBenVung`."""

    dinh: float
    stake_currency: str  # phát hiện lệch đơn vị nếu config đổi stake_currency giữa hai lần chạy


def dinh_equity_moi(
    dinh_cu: DinhEquityBenVung | None, *, tong_hien_tai: float, stake_currency: str,
) -> DinhEquityBenVung:
    """Đỉnh MỚI = `max(đỉnh cũ, tong_hien_tai)` — CHÍNH SÁCH ĐÃ CHỐT:
    không bao giờ giảm, không bao giờ reset theo kỳ (14/09/2026, chủ dự án).

    - `dinh_cu=None` (lần đọc đầu tiên, chưa từng lưu) → đỉnh = `tong_hien_tai`.
    - `tong_hien_tai` NaN hoặc `<= 0` → raise (N6: không lấy số rác làm đỉnh).
    - `dinh_cu.stake_currency != stake_currency` → raise (fail-closed:
      không âm thầm trộn đơn vị nếu cấu hình đổi `stake_currency` giữa
      hai lần chạy).
    - `tong_hien_tai <= dinh_cu.dinh` → trả NGUYÊN `dinh_cu` (bất biến,
      không tạo instance mới khi không có gì đổi).
    """
    if math.isnan(tong_hien_tai) or tong_hien_tai <= 0:
        raise DinhEquityError(
            f"equity hiện tại phải hữu hạn và dương, nhận {tong_hien_tai} — "
            "một ví báo 0/âm/NaN là dấu hiệu đọc hỏng, không phải thị trường yên bình"
        )
    if dinh_cu is None:
        return DinhEquityBenVung(dinh=tong_hien_tai, stake_currency=stake_currency)
    if dinh_cu.stake_currency != stake_currency:
        raise DinhEquityError(
            f"đỉnh equity đã lưu ở đơn vị {dinh_cu.stake_currency!r}, cấu hình hiện tại "
            f"là {stake_currency!r} — không âm thầm trộn đơn vị"
        )
    if tong_hien_tai <= dinh_cu.dinh:
        return dinh_cu
    return DinhEquityBenVung(dinh=tong_hien_tai, stake_currency=stake_currency)


def luu_dinh_equity(trang_thai: DinhEquityBenVung, duong_dan: Path) -> None:
    """Ghi NGUYÊN TỬ (file tạm `.dang-ghi` + `rename`) — cùng khuôn
    `risk_supervisor.luu_trang_thai()`: tiến trình chết giữa chừng không
    được để lại một file mang TÊN THẬT nhưng nội dung dở dang."""
    duong_dan.parent.mkdir(parents=True, exist_ok=True)
    noi_dung = {"dinh": trang_thai.dinh, "stake_currency": trang_thai.stake_currency}
    tam = duong_dan.with_name(duong_dan.name + ".dang-ghi")
    tam.write_text(json.dumps(noi_dung, indent=2, ensure_ascii=False), encoding="utf-8")
    tam.replace(duong_dan)


def doc_dinh_equity(duong_dan: Path) -> DinhEquityBenVung | None:
    """Chưa có file (lần khởi động ĐẦU TIÊN thật sự) → `None` — ca DUY
    NHẤT "chưa đọc được" hợp lệ đọc thành "chưa có đỉnh", vì gọi nơi cần
    biết equity HIỆN TẠI để dùng làm đỉnh đầu tiên (không có ở đây).

    File TỒN TẠI mà hỏng (JSON lỗi/thiếu khoá/kiểu sai/`dinh` NaN hoặc
    `<= 0`) ⇒ RAISE — KHÔNG âm thầm coi là sạch, vì file hỏng có thể
    đang che một đỉnh thật đã ghi trước đó; coi nó là "chưa có" sẽ tự
    gỡ HALT (N6, cùng lý do `risk_supervisor.doc_trang_thai()` raise).
    """
    if not duong_dan.exists():
        return None
    try:
        tho = json.loads(duong_dan.read_text(encoding="utf-8"))
        dinh = float(tho["dinh"])
        stake_currency = tho["stake_currency"]
        if not isinstance(stake_currency, str) or not stake_currency:
            raise ValueError(f"stake_currency phải là chuỗi không rỗng, nhận {stake_currency!r}")
        if math.isnan(dinh) or dinh <= 0:
            raise ValueError(f"dinh phải hữu hạn và dương, nhận {dinh}")
        return DinhEquityBenVung(dinh=dinh, stake_currency=stake_currency)
    except (json.JSONDecodeError, OSError, KeyError, TypeError, ValueError) as exc:
        raise DinhEquityError(
            f"đỉnh equity đã lưu ở {duong_dan} tồn tại nhưng KHÔNG đọc được: {exc} — "
            "không tự coi là sạch, có thể đang che một đỉnh thật đã ghi trước đó"
        ) from exc


__all__ = [
    "THU_MUC_GOC",
    "DinhEquityBenVung",
    "DinhEquityError",
    "dinh_equity_moi",
    "doc_dinh_equity",
    "duong_dan_theo_runmode",
    "luu_dinh_equity",
]
