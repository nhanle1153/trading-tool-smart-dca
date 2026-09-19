"""`TD-0345` (`DR-D4-16` §3–§4) — đếm MÔ TẢ một lượt chạy, đầu ra GIỚI HẠN CỨNG vào `CTRL_MO_TA_ALLOWED`.

Tầng THUẦN. Nhận lệnh export (`KetQuaChay.lenh`) và cửa sổ quan sát THẬT; trả dict mà mọi khoá ∈ allowlist — kiểm lại
ở cuối hàm, nên một khoá lạ thêm vào sau này (kể cả vô tình) làm hàm RAISE thay vì lọt ra artifact.

🔴 Lệnh export mang `profit_abs`, `exit_reason`… — hàm này KHÔNG đọc chúng. Chỉ đọc: `pair`, `open_date`, `orders`
(khớp vào lệnh). Không có đường nào để một con số lãi/lỗ ra khỏi đây.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import date, datetime, timezone
from typing import Any

from tool_d.ledger.registry import CTRL_MO_TA_ALLOWED


class DemMoTaError(ValueError):
    """Đầu vào hỏng hoặc đầu ra vượt allowlist. Fail-closed."""


def _thang(t: Mapping[str, Any]) -> str:
    od = t.get("open_date")
    if not isinstance(od, str) or not od:
        raise DemMoTaError(f"lệnh thiếu open_date: {t.get('pair')!r}")
    d = datetime.fromisoformat(od)
    if d.tzinfo is not None:
        d = d.astimezone(timezone.utc)
    return d.strftime("%Y-%m")


def _so_tranche_khop(t: Mapping[str, Any]) -> int:
    return sum(
        1 for o in (t.get("orders") or ())
        if o.get("ft_is_entry") and o.get("order_filled_timestamp") and float(o.get("amount") or 0) > 0
    )


def dem_mo_ta(lenh: Sequence[Mapping[str, Any]], *, observed_start: date, observed_end: date) -> dict[str, Any]:
    ngay = (observed_end - observed_start).days + 1
    if ngay <= 0:
        raise DemMoTaError(f"cửa sổ quan sát rỗng [{observed_start}, {observed_end}]")
    so = len(lenh)
    ra: dict[str, Any] = {
        "so_lenh": so,
        "lenh_moi_nam": so / (ngay / 365.25),
        "so_lenh_theo_thang": dict(sorted(Counter(_thang(t) for t in lenh).items())),
        "so_ma_co_lenh": len({t.get("pair") for t in lenh}),
        "phan_bo_so_tranche": {str(k): v for k, v in sorted(Counter(_so_tranche_khop(t) for t in lenh).items())},
    }
    ngoai = set(ra) - CTRL_MO_TA_ALLOWED
    if ngoai:
        raise DemMoTaError(f"đầu ra vượt allowlist DR-D4-16 §3: {sorted(ngoai)}")
    return ra


__all__ = ["DemMoTaError", "dem_mo_ta"]
