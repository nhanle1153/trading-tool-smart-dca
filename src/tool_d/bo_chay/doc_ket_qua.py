"""`TD-0312` — đọc kết quả backtest, và khai phạm vi ngày THẬT.

🔴 **Đây là chỗ bẫy TD-0148 nằm.** `orchestrator.py` đã viết trước khi có bộ chạy:
*"Nó vẫn tin lời khai của bộ chạy. Một bộ chạy trả ngày dự kiến thay vì ngày thật
đọc được từ dataframe sẽ vô hiệu hoá nó hoàn toàn."* Module này là mảnh đó, nên hai
nguồn ngày được phân biệt tường minh:

  `timerange`          — chuỗi `--timerange` chép nguyên ⇒ ngày **DỰ KIẾN**. CẤM dùng.
  `backtest_start_ts`  — mốc nến đầu THẬT SỰ được đánh giá.
  `backtest_end_ts`    — mốc nến cuối THẬT SỰ được đánh giá.

Cả hai mốc `_ts` đều bị **kẹp bởi dữ liệu**, không chỉ bởi `--timerange` — đo được
ngày 18/09/2026 (`td0312-can-tren-timerange.json`): xin tới `2025-01-20` trên bộ dữ
liệu dài tới `2025-01-25` thì cận trên theo yêu cầu; còn artifact `L-Z49` xin tới
`20250120` trên dữ liệu chỉ dài tới `2025-01-11 19:00` thì `backtest_end` = `2025-01-11
19:00`. Đó chính là thứ làm phép kiểm `L-Z55` có nghĩa.

🔴 **Bẫy đơn vị, đã đo, không phải phòng xa:** file `*.meta.json` nằm cạnh zip ghi
`backtest_start_ts` bằng **GIÂY** (`1736409600`), còn báo cáo bên trong zip ghi cùng
tên khoá bằng **MILI-GIÂY** (`1736409600000`). Hai file, hai đơn vị, cùng tên khoá.
Module này chỉ đọc trong zip qua `load_backtest_stats`, và có khẳng định vệ sinh để
nếu ai đổi nguồn thì nó nổ ngay thay vì trả một ngày năm 1970.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from tool_d.bo_chay.yeu_cau import BoChayError

#: Trường của một lệnh được chép sang `KetQuaChay.lenh`. Danh sách ĐÓNG, không phải
#: blocklist: `DR-013` chốt đơn vị đo là `pnl_abs`, và `L-Z46` cấm tuyệt đối hai định
#: danh đơn vị khác ở tầng đo. Chép có chọn là cách khiến một trường bị cấm không thể
#: đi vào tầng đo *bằng cách lọt qua* — blocklist chỉ chặn được tên đã nghĩ ra trước.
TRUONG_LENH = (
    "pair",
    "open_date",
    "close_date",
    "profit_abs",
    "amount",
    "enter_tag",
    "exit_reason",
    "is_short",
    "leverage",
    "stake_amount",
    "max_stake_amount",
    "orders",
    # TD-0342 — nghĩa cột duyệt 19/09/2026 (`y_nghia_cot.py`): giá thanh lý ƯỚC TÍNH, đã dịch về phía giá vào.
    "liquidation_price",
)

#: Khoảng năm hợp lệ cho một mốc đọc ra. Hẹp có chủ đích: mọi mốc của dự án nằm trong
#: `[T0, T3]` = 2024-2026. Một mốc năm 1970 (đọc nhầm giây thành mili-giây) hay năm
#: 56000 (ngược lại) phải NỔ, không được đi tiếp thành một con số trông bình thường.
NAM_HOP_LE = (2020, 2030)


class DocKetQuaError(BoChayError):
    """Không đọc được kết quả đủ tin để dùng — fail-closed, không trả số vá víu."""


def _mot_moc(kq: Mapping[str, Any], khoa: str) -> date:
    if khoa not in kq:
        raise DocKetQuaError(
            f"báo cáo backtest không có khoá {khoa!r} — TỪ CHỐI suy ngày từ `timerange` "
            "(đó là ngày DỰ KIẾN, dùng nó là vô hiệu hoá L-Z55 — TD-0148)"
        )
    tho = kq[khoa]
    if not isinstance(tho, (int, float)):
        raise DocKetQuaError(f"{khoa} = {tho!r} không phải số")
    khi = datetime.fromtimestamp(tho / 1000, timezone.utc)
    if not (NAM_HOP_LE[0] <= khi.year <= NAM_HOP_LE[1]):
        raise DocKetQuaError(
            f"{khoa} = {tho!r} cho ra {khi.isoformat()} — ngoài {NAM_HOP_LE}. "
            "Nhiều khả năng nguồn đọc đã đổi đơn vị (zip ghi MILI-GIÂY, *.meta.json ghi GIÂY)."
        )
    return khi.date()


def doc_tu_bao_cao(kq: Mapping[str, Any]) -> dict[str, Any]:
    """Phần THUẦN: một báo cáo chiến lược đã mở sẵn → các trường ta cần.

    Tách khỏi `doc_ket_qua()` để mọi nhánh TỪ CHỐI kiểm được mà không phải chạy
    một lượt backtest thật. Một nhánh fail-closed chỉ chạy được sau 30 giây
    backtest là một nhánh sẽ không có ai kiểm.
    """
    for khoa in ("starting_balance", "final_balance"):
        if khoa not in kq:
            raise DocKetQuaError(f"báo cáo thiếu {khoa!r} — không kiểm được cân đối vốn (L-Z47)")

    lenh_tho = kq.get("trades") or []
    thieu_pnl = [i for i, t in enumerate(lenh_tho) if "profit_abs" not in t]
    if thieu_pnl:
        raise DocKetQuaError(
            f"{len(thieu_pnl)} lệnh không có `profit_abs` — đơn vị đo của dự án là `pnl_abs` "
            "(DR-013); TỪ CHỐI thay bằng đơn vị khác"
        )
    lenh = tuple({k: t[k] for k in TRUONG_LENH if k in t} for t in lenh_tho)

    return {
        "observed_start": _mot_moc(kq, "backtest_start_ts"),
        "observed_end": _mot_moc(kq, "backtest_end_ts"),
        "timerange_trong_bao_cao": kq.get("timerange"),
        "starting_balance": float(kq["starting_balance"]),
        "final_balance": float(kq["final_balance"]),
        "pnl_abs": tuple(float(t["profit_abs"]) for t in lenh_tho),
        "lenh": lenh,
    }


def doc_ket_qua(duong_zip: Path, chien_luoc: str) -> dict[str, Any]:
    """Mở zip kết quả, trả về đúng những gì đọc được — không diễn giải, không vá.

    Trả `dict` chứ không phải `KetQuaChay` vì module này không biết gì về rổ hay
    cấu hình; `chay.py` mới là chỗ ghép hai nửa lại.
    """
    try:
        from freqtrade.data.btanalysis import load_backtest_stats
    except ImportError as exc:  # pragma: no cover — chỉ xảy ra ngoài Docker
        raise DocKetQuaError(
            "không import được freqtrade — bộ chạy chỉ chạy trong Docker (N7)"
        ) from exc

    if not duong_zip.is_file():
        raise DocKetQuaError(f"không có file kết quả {duong_zip}")

    tat_ca = load_backtest_stats(duong_zip)
    theo_chien_luoc = tat_ca.get("strategy") or {}
    if chien_luoc not in theo_chien_luoc:
        raise DocKetQuaError(
            f"báo cáo không có chiến lược {chien_luoc!r}; có: {sorted(theo_chien_luoc)}"
        )
    return doc_tu_bao_cao(theo_chien_luoc[chien_luoc])
