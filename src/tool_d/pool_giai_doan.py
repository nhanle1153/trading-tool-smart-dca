"""TD-0299 (`DR-D1-05`) — chọn rổ pool theo TẬP DỮ LIỆU. Một hàm duy nhất cho mọi bộ chạy.

Mỗi giai đoạn dữ liệu cần rổ ĐÚNG TẠI MỐC BẮT ĐẦU của nó (H1-D, `spec:438`, `:4338`). Rổ chọn
tại mốc muộn hơn đã loại sẵn những mã suy giảm/chết trong giai đoạn ⇒ lệch sống sót chiều PASS.

  CALIB   [T0,T1] → `config/pool_t0.yaml`  · `user_data/data/pool_t0/futures`
  WFO     [T1,T2] → `config/pool_t1.yaml`  · `user_data/data/pool_t1/futures`
  LOCKBOX [T2,T3] → TỪ CHỐI, vĩnh viễn ở hàm này. Rổ đúng tại `T2` là `config/pool_t2.yaml`
                    (TD-0307, giải phần rổ của `MT-60`), nhưng lần chạm lockbox DUY NHẤT chỉ đi qua
                    E4 tại D9.5 (`DR-LOCKBOX-01` §3, TD-0310/TD-0274) — không qua bảng này.

🔴 `config/pool.yaml` là rổ HÔM NAY (live) + sổ 4 suất B0 — hàm này KHÔNG BAO GIỜ trả nó.
Bộ chạy backtest không tự đọc file rổ nào; gọi `ro_cho_tap()`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


class RoGiaiDoanError(RuntimeError):
    """Không xác định được rổ đúng cho tập dữ liệu — fail-closed, không rơi về rổ khác."""


@dataclass(frozen=True)
class RoGiaiDoan:
    tap: str
    moc: str  # tên mốc trong `tier_c.data_split` ("t0" | "t1"), hoặc "xac_nhan" (ngày CHỌN, TD-0389)
    file_ro: Path
    thu_muc_du_lieu: Path
    trading: tuple[str, ...]


#: `DR-D1-05` §1 — bảng DUY NHẤT. 🔴 KHÔNG thêm LOCKBOX vào đây, kể cả khi rổ `T2` đã có:
#: lõi bộ chạy (Khối 27) không có cửa chặn LOCKBOX riêng — nó dựa vào đúng việc hàm này từ
#: chối (`test_td0312_loi_bo_chay.py:203`). Thêm vào bảng là gỡ chốt chặn duy nhất giữa bộ
#: chạy backtest và dữ liệu chỉ được chạm một lần. Rổ `T2` cho lần chạm đi đường RIÊNG của E4.
RO_THEO_TAP: dict[str, tuple[str, Path, Path]] = {
    "CALIB": ("t0", Path("config/pool_t0.yaml"), Path("user_data/data/pool_t0/futures")),
    "WFO": ("t1", Path("config/pool_t1.yaml"), Path("user_data/data/pool_t1/futures")),
    # TD-0389 (`DR-XAC-NHAN-01` §6 Q3, §7 Q5) — rổ tại ngày CHỌN của ứng viên (point-in-time). File do `TD-0391` sinh
    # (⏸ hoãn); chưa có file ⇒ `ro_cho_tap("XAC_NHAN")` TỪ CHỐI, không rơi về rổ khác.
    "XAC_NHAN": ("xac_nhan", Path("config/pool_xac_nhan.yaml"), Path("user_data/data/xac_nhan/futures")),
}

POOL_HOM_NAY = Path("config/pool.yaml")


def ro_cho_tap(tap: str, *, repo_dir: Path = Path(".")) -> RoGiaiDoan:
    """Rổ + thư mục dữ liệu cho `tap`. Từ chối: LOCKBOX (luôn luôn), tên tập lạ, file rổ thiếu/hỏng,
    file rổ mang mốc khác bảng, danh sách `trading` rỗng."""
    if tap == "LOCKBOX":
        raise RoGiaiDoanError(
            "LOCKBOX không đi qua ro_cho_tap(): rổ đúng tại T2 là config/pool_t2.yaml (TD-0307, giải "
            "phần rổ của MT-60), nhưng lần chạm lockbox DUY NHẤT chỉ đi qua E4 tại D9.5 và phải trỏ bản "
            "cấp lại của seal 1 (DR-LOCKBOX-01 §3, TD-0310/TD-0274). Hàm này là cửa chặn duy nhất của "
            "lõi bộ chạy — không mở cho LOCKBOX. Không dùng pool.yaml thay thế."
        )
    if tap not in RO_THEO_TAP:
        raise RoGiaiDoanError(f"tập {tap!r} không có trong bảng rổ theo giai đoạn {sorted(RO_THEO_TAP)}")
    moc, file_ro, thu_muc = RO_THEO_TAP[tap]
    if file_ro == POOL_HOM_NAY:  # canh chính bảng, phòng ai sửa bảng về pool.yaml
        raise RoGiaiDoanError("bảng rổ theo giai đoạn trỏ vào config/pool.yaml — cấm (DR-D1-05)")
    duong = repo_dir / file_ro
    if not duong.is_file():
        co = "--ro-xac-nhan --slot IQ-xxxx" if moc == "xac_nhan" else f"--ro-{moc}"  # TD-0391
        raise RoGiaiDoanError(f"{file_ro} chưa tồn tại — sinh bằng E7 {co} --ghi trước (DR-D1-05)")
    try:
        noi_dung = yaml.safe_load(duong.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise RoGiaiDoanError(f"{file_ro} không đọc được: {exc}") from exc
    if noi_dung.get(f"moc_{moc}") is None:
        raise RoGiaiDoanError(f"{file_ro} không mang khoá moc_{moc} — không phải rổ của mốc {moc}")
    trading = tuple(noi_dung.get("trading") or ())
    if not trading:
        raise RoGiaiDoanError(f"{file_ro} có danh sách trading rỗng")
    return RoGiaiDoan(tap=tap, moc=moc, file_ro=file_ro, thu_muc_du_lieu=thu_muc, trading=trading)
