"""`TD-0312` — kiểu vào/ra của lõi bộ chạy, và hai hàm đổi dạng.

Mọi chốt thiết kế của gói nằm ở HÌNH DẠNG các kiểu dưới đây, không ở phép kiểm:

* `YeuCauChay` **không có** trường đường dẫn rổ / thư mục dữ liệu ⇒ bộ chạy
  không thể tự đọc file rổ, nó buộc phải đi qua `ro_cho_tap()`.
* `KetQuaChay` tách `timerange_yeu_cau` (ngày **DỰ KIẾN**) khỏi `observed_*`
  (ngày **THẬT**) thành hai trường khác tên ⇒ không ai lẫn hai thứ đó vào nhau
  mà không nhìn thấy mình đang làm thế (bẫy TD-0148).
* `GiayPhepChay` mang cả `ledger` chứ không chỉ `trial_id` ⇒ lõi đọc lại sổ
  được, không phải tin một chuỗi người gọi đưa.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, time, timezone
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # tránh vòng import; chỉ cần cho chú thích kiểu
    from tool_d.ledger.registry import TrialLedger


class BoChayError(RuntimeError):
    """Lỗi chung của lõi bộ chạy. Mọi nhánh đều fail-closed: không có đường nào
    trả về một kết quả 'gần đúng'."""


@dataclass(frozen=True)
class GiayPhepChay:
    """Bằng chứng ĐÃ có đặt chỗ hợp lệ trước khi chạm dữ liệu (`L-Z52`).

    Không phải lời khai: `chay_mot_luot()` tự đọc `ledger` và đòi trạng thái
    `RESERVED` ở dòng đầu, TRƯỚC khi mở bất kỳ file nào dưới thư mục dữ liệu.

    `budget_line` đi kèm để bản ghi kết quả khai được nó mà không phải tra
    ngược sổ — **không** để lõi tự chọn dòng ngân sách (`DR-BC-01` §4).
    """

    ledger: TrialLedger
    trial_id: str
    budget_line: str


@dataclass(frozen=True)
class YeuCauChay:
    """Một lượt backtest. Cửa sổ là NỬA MỞ `[tu, den_khong_gom)` — cùng quy ước
    với `Fold` (`wfo/folds.py`), để hai bên không phải đổi qua đổi lại.

    `ma_gioi_han` CHỈ dành cho test: nó thu hẹp rổ đã lấy từ `ro_cho_tap()`,
    **không** thay thế được rổ. Mã không có trong rổ thì bị từ chối.
    """

    tap: str  # "CALIB" | "WFO" — truyền THẲNG cho `ro_cho_tap()`, không diễn giải
    tu: date
    den_khong_gom: date
    chien_luoc: str
    ghi_de_config: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))
    timeframe_detail: str | None = None
    ma_gioi_han: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        if self.den_khong_gom <= self.tu:
            raise BoChayError(
                f"cửa sổ rỗng/đảo ngược: [{self.tu}, {self.den_khong_gom}) — "
                "nhớ `den_khong_gom` là cận KHÔNG BAO GỒM"
            )


@dataclass(frozen=True)
class KetQuaChay:
    """Kết quả một lượt chạy. Ba nhóm trường, cố ý không trộn.

    🔴 **Nhóm ngày phải đọc kỹ.** `timerange_yeu_cau` là thứ ta ĐÒI; `observed_*`
    là thứ engine THẬT SỰ đọc được và có thể hẹp hơn (dữ liệu ngắn hơn, hoặc
    thiếu nến warm-up). Chỉ `observed_*` được dùng cho `L-Z55`. Một bộ chạy trả
    ngày dự kiến thay cho ngày thật sẽ vô hiệu hoá phép kiểm đó hoàn toàn —
    `orchestrator.py` đã cảnh báo đúng chỗ này trước khi có ai viết bộ chạy.

    `du_lieu_co_*` là phạm vi ngày **CÓ SẴN trong file** của các mã đã chạy, đọc
    trực tiếp từ feather. Nó ở đây vì câu hỏi *"đọc nến của tập TRƯỚC để khởi động
    chỉ báo có tính là chạm tập đó không?"* **chưa ai chốt** (`DR-BC-01` §6.4) —
    khai ra để khi có người hỏi thì có số mà trả lời, thay vì phải nhớ.

    🔴 Đặt tên đúng thứ đo được: đây là **CẬN TRÊN** của những gì warm-up có thể
    đã đọc, **không phải** phép đo những gì nó thực sự đọc. Báo cáo của Freqtrade
    không có khoá nào khai phạm vi nạp (đã kiểm toàn bộ khoá của `load_backtest_stats`
    ngày 18/09/2026: chỉ có `backtest_start_ts`/`backtest_end_ts`, là cửa sổ ĐÁNH GIÁ).
    Gọi nó là "phạm vi nạp" sẽ là một cái nhãn hứa nhiều hơn con số.
    """

    # — nguồn rổ: đi ra từ `ro_cho_tap()`, không phải bộ chạy tự đọc —
    tap: str
    moc_ro: str
    file_ro: Path
    thu_muc_du_lieu: Path
    ma_da_chay: tuple[str, ...]
    # — ngày —
    timerange_yeu_cau: str
    observed_start: date
    observed_end: date
    du_lieu_co_tu: date | None
    du_lieu_co_den: date | None
    # — vốn + lệnh —
    starting_balance: float
    final_balance: float
    pnl_abs: tuple[float, ...]
    lenh: tuple[Mapping[str, Any], ...]
    # — xuất xứ —
    config_sha256: str
    duong_ket_qua: Path

    @property
    def so_lenh(self) -> int:
        return len(self.pnl_abs)


def ten_cap_freqtrade(ma: str) -> str:
    """`"AAVEUSDT"` → `"AAVE/USDT:USDT"` — nghịch đảo của `_symbol_san()`
    (`dr015/buoc2_chi_tiet.py:88`).

    Từ chối mã không kết thúc bằng `USDT` thay vì đoán: rổ chỉ chứa cặp USDT-M
    (`pool.py`), nên một mã lạ ở đây nghĩa là rổ sai, không phải cần linh hoạt.
    """
    if not ma.endswith("USDT") or len(ma) <= 4:
        raise BoChayError(f"mã {ma!r} không có đuôi USDT — không dựng được tên cặp Freqtrade")
    return f"{ma[:-4]}/USDT:USDT"


def chuoi_timerange(tu: date, den_khong_gom: date) -> str:
    """Cửa sổ NỬA MỞ `[tu, den_khong_gom)` → chuỗi `--timerange` **dạng unix giây**.

    🔴 Dạng `YYYYMMDD` KHÔNG dùng được ở đây, và đây là kết quả ĐO chứ không phải
    suy luận (`docs/du-lieu-do/td0312-can-tren-timerange.json`, 0 trial):

        --timerange 20241215-20250120     → backtest_end = 2025-01-20 00:00  (BAO GỒM)
        --timerange 1734220800-1737331199 → backtest_end = 2025-01-19 23:00  (đúng)

    Cận trên dạng ngày **bao gồm** nến tại mốc ⇒ thừa đúng một nến so với cửa sổ
    nửa mở. Với fold cuối của WFO, `test_end` = `T2` = đúng nến cuối cùng có trong
    dữ liệu, nên một nến thừa ở đó là **một ngày dữ liệu tương lai** — và
    `kiem_pham_vi_du_lieu()` sẽ raise, đúng như nó phải thế. Lùi cận trên 1 giây
    và truyền bằng unix giây cắt đúng, không mất nến nào.
    """
    if den_khong_gom <= tu:
        raise BoChayError(f"cửa sổ rỗng/đảo ngược: [{tu}, {den_khong_gom})")
    bat_dau = int(datetime.combine(tu, time.min, tzinfo=timezone.utc).timestamp())
    ket_thuc = int(datetime.combine(den_khong_gom, time.min, tzinfo=timezone.utc).timestamp()) - 1
    return f"{bat_dau}-{ket_thuc}"


def gia_tri_yaml(value: Any) -> str:
    """Giá trị Python → một scalar YAML hợp lệ, dùng cho cấu hình phủ.

    Dùng JSON vì mọi scalar JSON là scalar YAML hợp lệ với cùng nghĩa
    (`"Z0"` → chuỗi, `true` → bool, `null` → None) — không phải vì tiện, mà vì
    nó tránh phải tự viết luật trích dẫn YAML rồi sai ở một ca hiếm.
    """
    if isinstance(value, (str, int, float, bool)) or value is None:
        return json.dumps(value)
    raise BoChayError(
        f"giá trị phủ {value!r} không phải scalar — cấu hình phủ chỉ đổi từng khoá lá, "
        "không thay cả nhánh (đổi cả nhánh làm phép hậu kiểm 'đúng một khoá đổi' vô nghĩa)"
    )


def kiem_ma_thuoc_ro(ma_xin: Sequence[str], ro_trading: Sequence[str]) -> tuple[str, ...]:
    """Thu hẹp rổ theo `ma_gioi_han`. Mã ngoài rổ ⇒ từ chối, không lặng lẽ bỏ qua."""
    ngoai = [m for m in ma_xin if m not in set(ro_trading)]
    if ngoai:
        raise BoChayError(
            f"mã {sorted(ngoai)} không có trong rổ ({len(ro_trading)} mã) — "
            "`ma_gioi_han` chỉ THU HẸP rổ, không thêm mã vào rổ"
        )
    thu_tu = {m: i for i, m in enumerate(ro_trading)}
    return tuple(sorted(ma_xin, key=lambda m: thu_tu[m]))
