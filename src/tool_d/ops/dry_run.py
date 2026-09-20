"""TD-0350 (`DR-TRIEN-KHAI-01` §4) — dựng và khởi chạy bot DRY-RUN (D11) của `ZoneAbsorption`.

Dry-run chạy SONG SONG với đường ống kiểm định D5→D9.5 (chủ dự án chốt 19/09/2026, ghi đè `spec:2954`): nó không
đặt lệnh thật nên an toàn kể cả khi D2/D10 chưa verify; D10 PASS là điều kiện của **D12**, không của D11.

Hai phần, cùng khuôn toàn dự án (hàm THUẦN trước, lời gọi tiến trình sau):
- `dung_cau_hinh_dry_run()` — đọc `config/freqtrade/config.json` (nguồn sự thật DUY NHẤT của cấu hình Freqtrade),
  chỉ PHỦ ba khoá vận hành (`strategy`, `initial_state`, `bot_name`) + rổ mã, rồi ghi bản phủ ra `runs/`
  (đã `.gitignore`). Không một tham số chiến lược nào ở đây — Tầng B/C vẫn chỉ đọc `config/tool_d_config.yaml` (N4).
- `main()` — dựng bản phủ rồi `exec` thẳng `freqtrade trade`.

🔴 KHÔNG phải entrypoint thứ 9 (N3, `L-Z36`): module này không đánh giá cấu hình nào trên CALIB/WFO/LOCKBOX và
không sinh file kết quả đo — cùng hạng công cụ vận hành với `heartbeat_watchdog.py`
(`api-integration-rules.md` Mục 4.4b).

Fail-closed, TỪ CHỐI DỰNG chứ không đoán:
- `dry_run` của file gốc phải là `true` — module này KHÔNG BAO GIỜ tự lật sang tiền thật. Đường live (D10/D12) là
  quyết định riêng, cấu hình riêng, không phải một cờ ở đây.
- `api_key`/`secret` phải RỖNG — dry-run không cần key, và key trong file đã commit là rò bí mật.
- Rổ `config/pool.yaml` (rổ HÔM NAY — `pool_giai_doan.POOL_HOM_NAY`) phải có `trading` không rỗng: một bot chạy
  với 0 mã là "đang chạy" mà không bao giờ vào lệnh — pass rỗng ở tầng vận hành.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

from tool_d.bo_chay.yeu_cau import ten_cap_freqtrade
from tool_d.pool_giai_doan import POOL_HOM_NAY

TEN_CHIEN_LUOC = "ZoneAbsorption"
CAU_HINH_FREQTRADE_GOC = Path("config/freqtrade/config.json")
#: Thư mục trạng thái vận hành của dry-run — dưới `runs/` (đã `.gitignore`), TÁCH khỏi live (N11).
THU_MUC_VAN_HANH = Path("runs/van_hanh/dry_run")
TEN_FILE_CAU_HINH_PHU = "cfg.json"
TEN_FILE_LOG = "freqtrade.log"


class DryRunError(RuntimeError):
    """Không dựng được cấu hình dry-run an toàn — fail-closed."""


@dataclass(frozen=True)
class CauHinhDryRun:
    duong_dan: Path
    so_cap: int


def _doc_ro(duong_ro: Path) -> tuple[str, ...]:
    if not duong_ro.is_file():
        raise DryRunError(f"{duong_ro} không tồn tại — sinh rổ hôm nay bằng E7 build_pool.py trước")
    try:
        noi_dung = yaml.safe_load(duong_ro.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise DryRunError(f"{duong_ro} không đọc được: {exc}") from exc
    trading = tuple(noi_dung.get("trading") or ())
    if not trading:
        raise DryRunError(f"{duong_ro} có danh sách trading rỗng — bot dry-run 0 mã là pass rỗng")
    return trading


def dung_cau_hinh_dry_run(
    *, repo_dir: Path = Path("."), duong_ro: Path | None = None, thu_muc_ra: Path | None = None
) -> CauHinhDryRun:
    """Ghi `<thu_muc_ra>/cfg.json` = cấu hình gốc + ba khoá vận hành + rổ. Trả đường dẫn và số cặp."""
    goc = repo_dir / CAU_HINH_FREQTRADE_GOC
    if not goc.is_file():
        raise DryRunError(f"{goc} không tồn tại")
    ft = json.loads(goc.read_text(encoding="utf-8"))

    if ft.get("dry_run") is not True:
        raise DryRunError(
            f"{CAU_HINH_FREQTRADE_GOC} có dry_run = {ft.get('dry_run')!r} — module dry-run TỪ CHỐI chạy trên một "
            "cấu hình không phải dry-run (đường tiền thật là quyết định riêng)"
        )
    san = ft.get("exchange") or {}
    if san.get("key") or san.get("api_key") or san.get("secret"):
        raise DryRunError(
            f"{CAU_HINH_FREQTRADE_GOC} chứa api_key/secret khác rỗng — dry-run không cần key, và key trong file "
            "đã commit là rò bí mật"
        )

    trading = _doc_ro(duong_ro if duong_ro is not None else repo_dir / POOL_HOM_NAY)

    ft["strategy"] = TEN_CHIEN_LUOC
    ft["exchange"]["pair_whitelist"] = [ten_cap_freqtrade(m) for m in trading]
    # `stopped` trong file gốc đúng cho mọi lần chạy KHÔNG chủ đích; service dry-run là chủ đích, và không có
    # Telegram/API server nào để gửi lệnh /start ⇒ để `stopped` thì bot không bao giờ chạy.
    ft["initial_state"] = "running"
    ft["bot_name"] = "tool_d_dry_run"

    ra = thu_muc_ra if thu_muc_ra is not None else repo_dir / THU_MUC_VAN_HANH
    ra.mkdir(parents=True, exist_ok=True)
    duong = ra / TEN_FILE_CAU_HINH_PHU
    duong.write_text(json.dumps(ft, ensure_ascii=False, indent=1), encoding="utf-8")
    return CauHinhDryRun(duong_dan=duong, so_cap=len(trading))


def lenh_freqtrade(cau_hinh: CauHinhDryRun) -> list[str]:
    """Dòng lệnh `freqtrade trade` — tách ra để test đọc được mà không phải `exec`."""
    return [
        "freqtrade", "trade",
        "--config", str(cau_hinh.duong_dan),
        "--strategy", TEN_CHIEN_LUOC,
        "--strategy-path", "user_data/strategies",
        "--userdir", "user_data",
        "--logfile", str(cau_hinh.duong_dan.parent / TEN_FILE_LOG),
    ]


def main() -> None:  # pragma: no cover — exec tiến trình thật; phần thuần đã khoá bằng test
    cau_hinh = dung_cau_hinh_dry_run()
    lenh = lenh_freqtrade(cau_hinh)
    print(f"dry-run: {cau_hinh.so_cap} cặp, cấu hình {cau_hinh.duong_dan}", file=sys.stderr, flush=True)
    os.execvp(lenh[0], lenh)


if __name__ == "__main__":  # pragma: no cover
    main()
