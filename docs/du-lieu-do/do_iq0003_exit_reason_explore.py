"""TD-0401 — đếm `exit_reason` của `RoFunding` (`IQ-0003`) trên EXPLORE, 0 suất (`DR-PHAN-QUYET-01` §4.2 bước 2).

Hiện vật `docs/du-lieu-do/IQ-0003-exit-reason-explore.json` là thứ cổng thiết kế (`TD-0375` + `TD-0398`,
`src/tool_d/gates/exit_reason_thiet_ke.py`) đòi trước suất ĐẦU TIÊN của slot. Khuôn `lenh_that: {arm: {so_lenh,
exit_reason}}` + khai lớp `CAN_RO_THEO_LICH` (`DR-CAN-RO-01` §3) trỏ `DR-D0-IQ0003`.

🔴 CHỈ ĐẾM. Hiện vật không mang PnL, expectancy hay bất kỳ chỉ số hiệu năng nào — cùng kỷ luật `do_td0193` / IQ-0001.
EXPLORE là tập dành cho SINH giả thuyết (§9c.4b), không phải tập phán quyết.

Môi trường dựng bằng đúng `dung_moi_truong(chien_luoc="RoFunding")` của bộ chạy E1 (file phủ lệnh thị trường + stop
tĩnh + ví theo vốn rổ). `tier_a.enable_short` ghi đè `true` CHỈ trong bản cấu hình tạm của lần đếm này — rổ không có
chân Short thì không phải rổ đã đăng ký; công tắc thật lật ở `TD-0402`.

⚠️ Giới hạn, ghi trong hiện vật: EXPLORE không có nến 5m ⇒ chạy KHÔNG `timeframe_detail` (stop khớp theo nến 1H).

Chạy (Docker): `docker compose -f docker/docker-compose.yml run --rm --entrypoint python freqtrade
docs/du-lieu-do/do_iq0003_exit_reason_explore.py --ket-qua docs/du-lieu-do/IQ-0003-exit-reason-explore.json`
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

from tool_d.bo_chay.moi_truong import dung_moi_truong
from tool_d.config.loader import load_tool_d_config, resolve
from tool_d.gates.exit_reason_thiet_ke import KHOA_DR_THIET_KE, KHOA_LOP, LOP_CAN_RO

REPO = Path(".").resolve()
THU_MUC_EXPLORE = REPO / "user_data" / "data" / "explore"
DR_THIET_KE = "docs/decisions/DR-D0-IQ0003-thiet-ke-ro-funding.md"
ARM = "RO"
DAU_HIEU_NUOT = "Strategy caused the following exception"


def _ma_explore() -> list[str]:
    """Mã có đủ nến 1h + funding + mark trên đĩa EXPLORE (dạng `ABCUSDT`)."""
    thu_muc = THU_MUC_EXPLORE / "futures"
    goc = sorted(p.name.split("_USDT_USDT-")[0] for p in thu_muc.glob("*_USDT_USDT-1h-futures.feather"))
    return [
        f"{m}USDT"
        for m in goc
        if (thu_muc / f"{m}_USDT_USDT-1h-funding_rate.feather").is_file()
        and (thu_muc / f"{m}_USDT_USDT-1h-mark.feather").is_file()
    ]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ket-qua", required=True, type=Path)
    args = ap.parse_args(argv)

    cfg = load_tool_d_config()
    t0 = str(resolve(cfg, "tier_c.data_split.t0")).replace("-", "")
    t2 = str(resolve(cfg, "tier_c.data_split.t2")).replace("-", "")
    ma = _ma_explore()
    goc = Path(tempfile.mkdtemp(prefix="iq0003_explore_"))
    mt = dung_moi_truong(
        repo_dir=REPO, goc=goc, ghi_de={"tier_a.enable_short": True}, ma_trong_ro=ma, chien_luoc="RoFunding"
    )
    bat_dau = time.time()
    proc = subprocess.run(
        [
            sys.executable, "-m", "freqtrade", "backtesting",
            "--config", str(mt.config_freqtrade), "--datadir", str(THU_MUC_EXPLORE), "--userdir", str(mt.userdir),
            "--strategy", "RoFunding", "--strategy-path", str(REPO / "user_data" / "strategies"),
            "--timerange", f"{t0}-{t2}", "--cache", "none", "--export", "trades",
        ],
        capture_output=True, text=True, cwd=goc,
    )
    log = proc.stdout + proc.stderr
    if proc.returncode != 0:
        print(f"🛑 backtest EXPLORE thất bại (rc={proc.returncode}):\n{log[-3000:]}")
        return 2
    nuot = sum(1 for d in log.splitlines() if DAU_HIEU_NUOT in d)

    from freqtrade.data.btanalysis import load_backtest_stats

    files = sorted((mt.userdir / "backtest_results").glob("backtest-result-*.zip"))
    lenh = load_backtest_stats(files[-1])["strategy"]["RoFunding"]["trades"]
    dem = Counter(t["exit_reason"] for t in lenh)
    if not lenh:
        print("🛑 0 lệnh — không có gì để đếm (không coi là đạt, N6)")
        return 3

    kq = {
        "nguon": "TD-0401 — DR-PHAN-QUYET-01 §4.2 bước 2 cho IQ-0003; 0 suất; CHỈ ĐẾM, không PnL",
        "dataset": "EXPLORE",
        "timerange": f"{t0}-{t2}",
        "so_ma": len(ma),
        "timeframe_detail": None,
        "lenh_that": {ARM: {"so_lenh": len(lenh), "exit_reason": dict(sorted(dem.items()))}},
        KHOA_LOP: LOP_CAN_RO,
        KHOA_DR_THIET_KE: DR_THIET_KE,
        "exception_bi_nuot": nuot,
        "giay": round(time.time() - bat_dau, 1),
        "ghi_chu": [
            "EXPLORE không có nến 5m ⇒ chạy không timeframe_detail; stop thảm hoạ khớp theo nến 1H",
            "tier_a.enable_short ghi đè true chỉ trong cấu hình tạm của lần đếm (TD-0402 lật công tắc thật)",
        ],
    }
    args.ket_qua.write_text(json.dumps(kq, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"so_lenh": len(lenh), "exit_reason": kq["lenh_that"][ARM]["exit_reason"], "nuot": nuot}, ensure_ascii=False))
    return 1 if nuot else 0


if __name__ == "__main__":
    sys.exit(main())
