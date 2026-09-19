"""TD-0345 (`DR-D4-16` §4) — đếm `n` 4 arm D4 trên rổ T1, cửa sổ WFO. CTRL dạng *đo mô tả*, 0 trial trong N.

Điều kiện 3 của `DR-D4-14` §6: số `325,6` lệnh/năm · `n = 206` · `44,8` (rổ `pool.yaml` cũ) mất hiệu lực sau khi rổ T1
point-in-time được dựng (spec `:4338`) ⇒ đếm lại trên rổ mới.

Mỗi arm: RESERVE CTRL (`ctrl_mo_ta_whitelist`, sổ THẬT) → `chay_mot_luot` (L-Z52: có đặt chỗ trước khi chạm dữ liệu) →
SEAL → `dem_mo_ta` (chỉ tên allowlist) → CONSUME (`INCONCLUSIVE`, outcome không số hiệu năng). Lỗi MÁY trước con dấu ⇒
hoàn trả theo nguyên nhân máy.

🔴 Chủ dự án gỡ ⏸ CHỈ phần đếm này (`DR-D4-16` §1). Kịch bản KHÔNG in, KHÔNG ghi bất kỳ số lãi/lỗ nào: Freqtrade chạy
trong tiến trình con có `capture_output`, và chỉ `dem_mo_ta()` được chạm vào danh sách lệnh.

Chạy trong Docker (N7):
  docker compose -f docker/docker-compose.yml run --rm freqtrade docs/du-lieu-do/do_td0345_dem_n_4_arm_ro_t1.py
"""
from __future__ import annotations

import json
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from tool_d.ablation.ban_ghi import LO_ARM_D4  # noqa: E402
from tool_d.ablation.dem_mo_ta import dem_mo_ta  # noqa: E402
from tool_d.bo_chay.chay import BacktestHongError, chay_mot_luot  # noqa: E402
from tool_d.bo_chay.moi_truong import dung_moi_truong  # noqa: E402
from tool_d.bo_chay.yeu_cau import BoChayError, GiayPhepChay, YeuCauChay  # noqa: E402
from tool_d.config.loader import load_tool_d_config  # noqa: E402
from tool_d.gates.dsr import N_DANG_KY  # noqa: E402
from tool_d.ledger.registry import CTRL_MO_TA_ALLOWED, TrialLedger  # noqa: E402
from tool_d.ledger.timerange import cua_so_tap, dataset_boundaries_from_config  # noqa: E402
from tool_d.measurement.gitinfo import get_git_info  # noqa: E402
from tool_d.measurement.hashing import hash_many  # noqa: E402
from tool_d.pool_giai_doan import ro_cho_tap  # noqa: E402

KET_QUA = REPO / "docs" / "du-lieu-do" / "td0345-dem-n-4-arm-ro-t1.json"
KHOA_ARM = "tier_c.arm_ablation.arm"
TAP = "WFO"
#: `DR-D4-12` §4.1 — số trên rổ CŨ (`pool.yaml`), để ghi CẠNH số mới, không phán xét.
SO_CU = {
    "Z0-T1": {"n": 206, "lenh_moi_nam_quy_doi": 325.6},
    "Z0": {"n": 28, "lenh_moi_nam_quy_doi": 44.8},
    "Z0-T0": {"n": 883},
    "Z3": {"n": 28},
}


def main() -> int:
    if KET_QUA.exists():
        print(f"🛑 {KET_QUA} đã tồn tại — không ghi đè, không đếm lại", flush=True)
        return 3
    cfg = load_tool_d_config(REPO / "config" / "tool_d_config.yaml")
    bien = dataset_boundaries_from_config(cfg)[TAP]
    # DR-D9-01: WFO = [T1, T2) NỬA MỞ — giờ 00:00 của ngày T2 là mốc LOCKBOX, không thuộc WFO. Lượt đầu (19/09) xin
    # [T1, T2 + 1 ngày) và chốt 5m từ chối đúng giờ đó (98/107 mã) — D-0006 đã hoàn trả theo nguyên nhân máy.
    tu, den = cua_so_tap(bien)  # TD-0347
    ro = ro_cho_tap(TAP, repo_dir=REPO)
    thu_muc = REPO / ro.thu_muc_du_lieu
    data_hashes = hash_many({f.name: f for f in sorted(thu_muc.glob("*.feather"))})
    git = get_git_info(REPO)
    so = TrialLedger(path=REPO / "registry" / "trial_registry.jsonl")
    print(f"rổ {ro.file_ro} · {len(ro.trading)} mã · WFO [{tu}, {den}) · git {git.sha[:12]} sạch={git.is_clean}", flush=True)

    ket: dict[str, dict] = {}
    for arm in LO_ARM_D4:
        goc = Path(tempfile.mkdtemp(prefix=f"td0345_{arm.lower().replace('-', '_')}_"))
        mt = dung_moi_truong(repo_dir=REPO, goc=goc, ghi_de={KHOA_ARM: arm}, ma_trong_ro=ro.trading)
        tid = so.reserve(
            n_dang_ky=N_DANG_KY, budget_line="CTRL", hypothesis_slot="TD-0345", direction="LONG", dataset=TAP,
            param_under_test=KHOA_ARM, param_value=arm, params_frozen_hash=mt.sha256_phu, config_hash=mt.sha256_phu,
            code_commit=git.sha,
            provenance={"params_source": "yaml", "params_effective": {KHOA_ARM: arm}, "git_sha": git.sha,
                        "reproducible_from_sha": git.is_clean, "data_hashes": data_hashes, "cache_mode": "none",
                        "guard_passed": True},
            contribution=1, ctrl_mo_ta_whitelist=sorted(CTRL_MO_TA_ALLOWED),
        )
        t = time.time()
        try:
            kq = chay_mot_luot(
                YeuCauChay(tap=TAP, tu=tu, den_khong_gom=den, chien_luoc="ZoneAbsorption",
                           ghi_de_config={KHOA_ARM: arm}, timeframe_detail="5m"),
                giay_phep=GiayPhepChay(ledger=so, trial_id=tid, budget_line="CTRL"),
                repo_dir=REPO, goc_tam=goc,
            )
        except BacktestHongError as exc:
            so.refund(tid, cause_machine=f"freqtrade_backtesting_exit_{exc.returncode}")
            print(f"🛑 {arm}: backtest hỏng rc={exc.returncode} — đã hoàn trả {tid}", flush=True)
            return 4
        except BoChayError as exc:
            so.refund(tid, cause_machine=f"bo_chay_tu_choi:{type(exc).__name__}")
            print(f"🛑 {arm}: {type(exc).__name__}: {str(exc)[:300]} — đã hoàn trả {tid}", flush=True)
            return 5
        so.seal(tid, seal_path=f"runs/{tid}/metrics.seal")
        dem = dem_mo_ta(kq.lenh, observed_start=kq.observed_start, observed_end=kq.observed_end)
        so.consume(tid, outcome={"expectancy": None, "sharpe": None, "n_trades": dem["so_lenh"],
                                 "max_single_loss_ratio": None}, verdict="INCONCLUSIVE")
        ket[arm] = {"trial_id": tid, "observed": [kq.observed_start.isoformat(), kq.observed_end.isoformat()],
                    "so_ma_da_chay": len(kq.ma_da_chay), **dem}
        print(f"  {arm:6s} {tid}  so_lenh {dem['so_lenh']:5d}  lenh/nam {dem['lenh_moi_nam']:8.1f}  "
              f"ma co lenh {dem['so_ma_co_lenh']:3d}  tranche {dem['phan_bo_so_tranche']}  ({time.time() - t:.0f}s)",
              flush=True)

    kq_json = {
        "nguon": "TD-0345 — DR-D4-16 §4, CTRL đo mô tả (MT-19), 0 trial trong N",
        "chay_luc_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "git_sha": git.sha, "cay_sach": git.is_clean,
        "ro": str(ro.file_ro), "moc_ro": ro.moc, "so_ma_ro": len(ro.trading),
        "cua_so": [tu.isoformat(), den.isoformat()], "timeframe_detail": "5m",
        "allowlist": sorted(CTRL_MO_TA_ALLOWED),
        "arm": ket,
        "so_cu_ro_pool_yaml": SO_CU,
        "han_che": [
            "Chỉ SỐ ĐẾM (DR-D4-16 §3) — không một đại lượng lãi/lỗ nào được đọc hay ghi",
            "Thêm một lượt nhìn cửa sổ WFO cho giả thuyết đang tạm dừng (DR-D4-16 §1, chủ dự án chấp nhận)",
            "Số cũ đo trên pool.yaml (102 mã, ảnh chụp 09/2026) — không so trực tiếp (spec :4338); ghi cạnh để thấy độ lệch",
            "lenh_moi_nam = so_lenh / năm phủ của cửa sổ QUAN SÁT trên toàn rổ — không quy đổi pool như số cũ",
        ],
    }
    KET_QUA.write_text(json.dumps(kq_json, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"→ {KET_QUA}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
