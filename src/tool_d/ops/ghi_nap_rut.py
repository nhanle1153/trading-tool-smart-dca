"""TD-0439 (`DR-TANG-CHAN-01`, `DR-D6D8-01` §4.2 sự kiện (a)) — người vận hành ghi một lần NẠP/RÚT vốn vào sổ đỉnh của
Risk Supervisor, để đỉnh DỊCH đúng số tiền thay vì đọc khoản rút thành "sụt vốn" (HALT oan) hay khoản nạp thành "đỉnh mới".

    docker compose -f docker/docker-compose.yml run --rm --entrypoint python tests -m tool_d.ops.ghi_nap_rut \\
        --runmode live --so-tien -100 --ghi-chu "rút 100 USDT về ví chính"

🔑 QUY ƯỚC THỨ TỰ — để mọi lệch tạm thời giữa sổ và tiền thật đều ra phía AN TOÀN (dd hiện CAO hơn thật ⇒ có thể HALT oan,
không bao giờ che sụt thật; `equity_peak.py`):
  • NẠP (số dương): ghi TRƯỚC khi chuyển tiền vào.
  • RÚT (số âm): ghi SAU khi tiền đã rời tài khoản.

Ghi vào sổ của Supervisor (chủ đỉnh DUY NHẤT — `DR-TANG-CHAN-01` §4 điều 1), qua `equity_peak.ghi_su_kien()` (kiểm sự kiện
bằng chính bộ đọc trước khi ghi, append-only). 🔴 KHÔNG phải entrypoint thứ 9 (N3, `L-Z36`): không đánh giá cấu hình, không
chạm dữ liệu thị trường — cùng hạng công cụ vận hành với `ops/dry_run.py`.
"""

from __future__ import annotations

import argparse
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

from tool_d.equity_peak import NAP_RUT, DinhEquityError, SuKienDinh, duong_dan_so_su_kien, ghi_su_kien
from tool_d.ops.risk_supervisor_daemon import DON_VI_EQUITY_SAN, duong_dan_dinh_supervisor, duong_dan_theo_runmode
from tool_d.tang_chan import RUNMODE_CO_SUPERVISOR

#: Số KHÔNG trùng mã nào khác của dự án (99–115 đã dùng; test canh ở TD-0425).
EXIT_GHI_NAP_RUT_TU_CHOI = 116

NHAC_QUY_UOC = (
    "Quy ước: NẠP ghi TRƯỚC khi chuyển tiền vào; RÚT ghi SAU khi tiền đã rời tài khoản "
    "(mọi lệch tạm thời ra phía an toàn — equity_peak.py)."
)


def ghi(runmode: str, *, so_tien: float, ghi_chu: str, now: datetime, state_path: Path | None = None) -> Path:
    """Ghi MỘT dòng `NAP_RUT` vào sổ của Supervisor `runmode`. Trả đường dẫn sổ. Sai hình ⇒ `DinhEquityError` (không ghi)."""
    if runmode not in RUNMODE_CO_SUPERVISOR:
        raise DinhEquityError(f"runmode {runmode!r} không có Supervisor — chỉ {RUNMODE_CO_SUPERVISOR}")
    if not math.isfinite(so_tien) or so_tien == 0:
        raise DinhEquityError(f"so_tien phải hữu hạn và khác 0 (dương = nạp, âm = rút), nhận {so_tien}")
    so = duong_dan_so_su_kien(duong_dan_dinh_supervisor(state_path or duong_dan_theo_runmode(runmode)))
    ghi_su_kien(so, SuKienDinh(loai=NAP_RUT, stake_currency=DON_VI_EQUITY_SAN, luc_utc=now.isoformat(),
                               ghi_chu=ghi_chu, so_tien=float(so_tien)))
    return so


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="TD-0439 — ghi một lần nạp/rút vốn vào sổ đỉnh của Risk Supervisor")
    p.add_argument("--runmode", required=True, choices=RUNMODE_CO_SUPERVISOR)
    p.add_argument("--so-tien", required=True, type=float, help="USDT; dương = nạp, âm = rút")
    p.add_argument("--ghi-chu", required=True, help="ai, vì sao, chuyển đi/về đâu — bắt buộc, để truy vết")
    p.add_argument("--state-path", type=Path, default=None, help="mặc định runs/risk_supervisor/<runmode>/state.json")
    a = p.parse_args(argv)
    print(NHAC_QUY_UOC, file=sys.stderr)
    try:
        so = ghi(a.runmode, so_tien=a.so_tien, ghi_chu=a.ghi_chu, now=datetime.now(timezone.utc), state_path=a.state_path)
    except DinhEquityError as exc:
        print(f"TỪ CHỐI ghi: {exc}", file=sys.stderr)
        return EXIT_GHI_NAP_RUT_TU_CHOI
    loai = "NẠP" if a.so_tien > 0 else "RÚT"
    print(f"đã ghi {loai} {abs(a.so_tien)} {DON_VI_EQUITY_SAN} vào {so} — Supervisor áp ở vòng kế tiếp", file=sys.stderr)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
