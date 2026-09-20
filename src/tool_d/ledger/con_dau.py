"""TD-0357 (`DR-D4-20`) — HIỆN VẬT của con dấu: file `metrics.seal` mà sổ trial khai.

`ledger.seal(trial_id, seal_path="runs/<trial>/metrics.seal")` được gọi ở ba chỗ (`ablation/chay_lo.py`,
`entrypoints/run_backtest.py`, `entrypoints/build_pool.py`) nhưng **không dòng mã nào sinh ra file đó**. Hậu quả đã
xảy ra thật: suất `D-0015` của lô `DR-D4-19` tiêu vì lỗi SAU con dấu (`708a268`), và vì export backtest nằm trong
thư mục tạm của container `--rm` nên **không còn gì để đọc lại** — một suất trong 114 mất mà không để lại hiện vật.

Luật của module này:
- **Ghi TRƯỚC khi gọi `seal()`.** Sổ không được khai một đường dẫn chưa tồn tại. Ghi hỏng ⇒ chưa niêm phong ⇒
  suất còn hoàn lại được (`L-Z53`).
- **Từ chối ghi đè** (khuôn `lockbox/seal.py`): con dấu là hiện vật một lần.
- **Chỉ sự thật thô của lượt chạy** — cửa sổ đọc được, số lệnh, số mã, băm cấu hình, tên chiến lược. Không xếp
  hạng, không phán quyết: đó là việc của bản ghi arm và của cổng.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TEN_FILE = "metrics.seal"


class ConDauError(RuntimeError):
    """Không ghi được hiện vật con dấu — fail-closed: chưa niêm phong thì chưa tiêu suất."""


def duong_con_dau(thu_muc_runs: Path, trial_id: str) -> Path:
    return thu_muc_runs / trial_id / TEN_FILE


def duong_khai_so(trial_id: str) -> str:
    """Chuỗi ghi vào sổ trial. `registry/schemas/trial_event.schema.json:95` đòi ĐÚNG dạng
    `runs/<trial>/metrics.seal` (tương đối gốc repo) — một chỗ sinh cho mọi nơi gọi, thay vì mỗi
    entrypoint tự ghép rồi lệch nhau."""
    return f"runs/{trial_id}/{TEN_FILE}"


def noi_dung_con_dau(trial_id: str, kq: Any, *, them: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Đọc thẳng từ `KetQuaChay` — không nhận lời khai của tầng gọi (MT-10)."""
    ra: dict[str, Any] = {
        "trial_id": trial_id,
        "niem_phong_luc_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tap": kq.tap,
        "moc_ro": kq.moc_ro,
        "file_ro": str(kq.file_ro),
        "chien_luoc": kq.chien_luoc,
        "config_sha256": kq.config_sha256,
        "timerange_yeu_cau": kq.timerange_yeu_cau,
        "observed_start": kq.observed_start.isoformat(),
        "observed_end": kq.observed_end.isoformat(),
        "so_ma_da_chay": len(kq.ma_da_chay),
        "so_lenh": kq.so_lenh,
    }
    if them:
        trung = sorted(set(them) & set(ra))
        if trung:
            raise ConDauError(f"khoá thêm trùng khoá gốc của con dấu: {trung}")
        ra.update(them)
    return ra


def ghi_con_dau(
    thu_muc_runs: Path, trial_id: str, kq: Any, *, them: Mapping[str, Any] | None = None
) -> Path:
    """Ghi nguyên tử (`.dang-ghi` + `os.replace`) rồi trả đường dẫn. Đã có file ⇒ raise."""
    duong = duong_con_dau(thu_muc_runs, trial_id)
    if duong.exists():
        raise ConDauError(f"{duong} đã tồn tại — con dấu là hiện vật MỘT LẦN, không ghi đè")
    duong.parent.mkdir(parents=True, exist_ok=True)
    tam = duong.with_name(duong.name + ".dang-ghi")
    van_ban = json.dumps(noi_dung_con_dau(trial_id, kq, them=them), indent=2, ensure_ascii=False)
    tam.write_text(van_ban + chr(10), encoding="utf-8")
    os.replace(tam, duong)
    return duong


__all__ = ["TEN_FILE", "ConDauError", "duong_con_dau", "duong_khai_so", "ghi_con_dau", "noi_dung_con_dau"]
