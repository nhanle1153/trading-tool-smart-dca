"""`TD-0335` (`DR-D4-14`) — vòng LÔ của ablation D4: đặt chỗ → chạy → niêm phong → ghi → tiêu.

E3 (`entrypoints/run_ablation.py`) gọi `chay_lo()` sau năm cổng của nó. Tách ra đây để
test được mà không cần `main()` và năm cổng thật; mọi thứ tốn tiền (đặt chỗ, chạm dữ
liệu) nằm SAU khoá.

🔑 **Thứ tự là thiết kế, không tuỳ tiện:**

  0. KHOÁ ĐO (`khoa_do.D4_DO_TAM_DUNG`) — lệnh ĐẦU TIÊN. Không tham số nào vượt được nó;
     test mở khoá bằng cách vá chính hằng số, không có cửa sau.
  1. `ro_cho_tap("WFO")` — đọc YAML rổ, CHƯA chạm dữ liệu.
  2. băm dữ liệu — `DR-BC-01` §3: băm ≠ chạm, được đứng trước đặt chỗ.
  3. dựng môi trường cho TỪNG arm — `config_hash` của dòng RESERVE phải là của bản sẽ chạy.
     3b. dựng sàn ảo tính giá thanh lý (`DR-D4-17`) — hỏng ở đây thì 0 suất.
  4. 🔴 ĐẶT CHỖ ĐỦ CẢ LÔ TRƯỚC KHI CHẠY ARM ĐẦU — `DR-D4-10` §2.3: *"vẫn RESERVE cả 9 trước
     khi chạy arm đầu"*; `DR-D4-01` §4b từ chối *"chạy từng arm rồi dừng khi thấy kết quả"*.
     Đặt chỗ từng arm ngay trước khi chạy nó sẽ mở đúng cửa đó.
  5. mỗi arm: `chay_mot_luot` (L-Z52 bên trong) → `seal` NGAY → trích lệnh → bản ghi → ghi file
     → `consume`.

**Lỗi MÁY trước con dấu** (Freqtrade thoát ≠ 0, lõi từ chối) ⇒ hoàn trả arm đó VÀ mọi arm
chưa chạy, theo nguyên nhân máy (`DR-014` §3), rồi dừng lô. **Lỗi sau con dấu** ⇒ KHÔNG hoàn
trả được (`L-Z53`): arm đó `consume` với `rejection_reason` nêu lỗi, các arm chưa chạy được
hoàn trả, rồi dừng lô.

**`verdict` trong sổ luôn `INCONCLUSIVE` ở tầng arm.** Sổ ghi `KEPT`/`REJECTED`/`INCONCLUSIVE`
— phán quyết GIẢ THUYẾT (spec `:3750`), thứ gate §10.2 (`TD-0336`) quyết sau khi đủ lô, không
phải một arm tự quyết. Kết cục của arm (`PASS`/`INCONCLUSIVE`/`FAIL`) nằm trong bản ghi arm.
Cùng quy ước E1 (`run_backtest.py`).
"""

from __future__ import annotations

import json
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from tool_d.ablation import khoa_do
from tool_d.ablation.ban_ghi import LO_ARM_D4, co_do_nhom_c, dung_ban_ghi_arm
from tool_d.ablation.chi_so_export import bat_bien_1_7_lech, chi_so_tu_export
from tool_d.ablation.thanh_ly import HamThanhLy, tinh_liq_freqtrade
from tool_d.bo_chay.chay import BacktestHongError, chay_mot_luot
from tool_d.bo_chay.moi_truong import MoiTruongChay, dung_moi_truong
from tool_d.bo_chay.trich_lenh import lenh_tu_freqtrade
from tool_d.bo_chay.yeu_cau import BoChayError, GiayPhepChay, YeuCauChay, kiem_ma_thuoc_ro
from tool_d.config.loader import resolve
from tool_d.gates.dsr import N_DANG_KY
from tool_d.ledger.registry import TrialLedger
from tool_d.measurement.gitinfo import GitInfo
from tool_d.measurement.hashing import hash_many
from tool_d.measurement.provenance import Provenance
from tool_d.measurement.tri_state import Measured, Status
from tool_d.pool_giai_doan import ro_cho_tap
from tool_d.wfo.folds import Fold

TAP = "WFO"
DONG_NGAN_SACH = "B2"
HUONG = "LONG"
KHOA_ARM = "tier_c.arm_ablation.arm"


class KhoaDoError(BoChayError):
    """Khoá đo đang bật (`DR-D4-14` §2.2). Không đặt chỗ, không chạm dữ liệu."""


class LoDungError(BoChayError):
    """Lô dừng giữa chừng vì lỗi MÁY. Các arm đã tiêu giữ nguyên; arm chưa chạy đã hoàn trả."""


@dataclass(frozen=True)
class KeHoachLo:
    tu: date
    den_khong_gom: date
    hypothesis_slot: str
    arms: tuple[str, ...] = LO_ARM_D4
    chien_luoc: str = "ZoneAbsorption"
    timeframe_detail: str | None = "5m"
    #: CHỈ cho test — thu hẹp rổ đã lấy từ `ro_cho_tap()`, không thay nó (`YeuCauChay`).
    ma_gioi_han: tuple[str, ...] | None = None


@dataclass(frozen=True)
class KetQuaArm:
    arm: str
    trial_id: str
    duong_ban_ghi: Path
    ket_cuc: str | None
    co_do: str | None


def _tu_choi_neu_khoa() -> None:
    if khoa_do.D4_DO_TAM_DUNG:
        raise KhoaDoError(khoa_do.LY_DO_KHOA)


def _hoan_tra(ledger: TrialLedger, trial_ids: Sequence[str], nguyen_nhan: str) -> None:
    for tid in trial_ids:
        ledger.refund(tid, cause_machine=nguyen_nhan)


def chay_lo(
    ke_hoach: KeHoachLo,
    *,
    ledger: TrialLedger,
    repo_dir: Path,
    thu_muc_ra: Path,
    folds: Sequence[Fold],
    delta_r_pham_vi: Mapping[str, Any],
    git_info: GitInfo,
    runtime_image_digest: str,
    chay: Callable[..., Any] = chay_mot_luot,
    ham_thanh_ly: HamThanhLy | None = None,
) -> list[KetQuaArm]:
    """Chạy cả lô. Xem thứ tự ở docstring module.

    `ham_thanh_ly` (TD-0348, `DR-D4-17`): mặc định dựng sàn ảo Freqtrade từ config của arm đầu, TRƯỚC khi đặt chỗ.
    Dựng lỗi thì từ chối khi chưa tiêu suất nào, thay vì phát hiện sau con dấu, khi suất đã không hoàn lại được.
    """
    # 0 — khoá đo. Lệnh ĐẦU TIÊN (test khoá kiểm bằng AST).
    _tu_choi_neu_khoa()

    if not ke_hoach.arms or len(set(ke_hoach.arms)) != len(ke_hoach.arms):
        raise BoChayError(f"lô arm rỗng hoặc trùng: {ke_hoach.arms}")
    if not ke_hoach.hypothesis_slot:
        raise BoChayError("thiếu hypothesis_slot — không có mặc định (DR-D4-14 §4)")

    # 1 — rổ (đọc YAML, chưa chạm dữ liệu).
    ro = ro_cho_tap(TAP, repo_dir=repo_dir)
    ma = (
        kiem_ma_thuoc_ro(ke_hoach.ma_gioi_han, ro.trading)
        if ke_hoach.ma_gioi_han is not None
        else tuple(ro.trading)
    )

    # 2 — băm (DR-BC-01 §3: băm ≠ chạm).
    thu_muc_du_lieu = repo_dir / ro.thu_muc_du_lieu
    data_hashes = hash_many({f.name: f for f in sorted(thu_muc_du_lieu.glob("*.feather"))})

    # 3 — môi trường của từng arm.
    moi_truong: dict[str, MoiTruongChay] = {}
    goc_theo_arm: dict[str, Path] = {}
    for arm in ke_hoach.arms:
        goc = Path(tempfile.mkdtemp(prefix=f"e3_{arm.lower().replace('-', '_')}_"))
        goc_theo_arm[arm] = goc
        moi_truong[arm] = dung_moi_truong(
            repo_dir=repo_dir, goc=goc, ghi_de={KHOA_ARM: arm}, ma_trong_ro=ma
        )

    # 3b — hàm giá thanh lý cho `liq_buffer_ratio_mean` (DR-D4-17). Trước đặt chỗ: hỏng thì 0 suất.
    if ham_thanh_ly is None:
        try:
            ham_thanh_ly = tinh_liq_freqtrade(moi_truong[ke_hoach.arms[0]].config_freqtrade)
        except Exception as exc:
            raise BoChayError(f"không dựng được sàn ảo tính giá thanh lý (DR-D4-17): {exc}") from exc

    # 4 — ĐẶT CHỖ ĐỦ CẢ LÔ trước khi chạy arm đầu (DR-D4-10 §2.3).
    trial_theo_arm: dict[str, str] = {}
    for arm in ke_hoach.arms:
        mt = moi_truong[arm]
        try:
            trial_theo_arm[arm] = ledger.reserve(
                n_dang_ky=N_DANG_KY,
                budget_line=DONG_NGAN_SACH,
                hypothesis_slot=ke_hoach.hypothesis_slot,
                direction=HUONG,
                dataset=TAP,
                param_under_test=KHOA_ARM,
                param_value=arm,
                params_frozen_hash=mt.sha256_phu,
                config_hash=mt.sha256_phu,
                code_commit=git_info.sha,
                provenance={
                    "params_source": "yaml",
                    "params_effective": {KHOA_ARM: resolve(mt.cfg_phu, KHOA_ARM)},
                    "git_sha": git_info.sha,
                    "reproducible_from_sha": git_info.is_clean,
                    "data_hashes": data_hashes,
                    "cache_mode": "none",
                    "guard_passed": True,
                },
                contribution=1,
            )
        except Exception as exc:
            _hoan_tra(ledger, list(trial_theo_arm.values()), f"lo_khong_dat_cho_du:{type(exc).__name__}")
            raise LoDungError(f"không đặt chỗ đủ cả lô ({arm}): {exc}") from exc

    # 5 — chạy từng arm.
    ket_qua: list[KetQuaArm] = []
    for i, arm in enumerate(ke_hoach.arms):
        tid = trial_theo_arm[arm]
        con_lai = [trial_theo_arm[a] for a in ke_hoach.arms[i + 1 :]]
        mt = moi_truong[arm]
        try:
            kq = chay(
                YeuCauChay(
                    tap=TAP,
                    tu=ke_hoach.tu,
                    den_khong_gom=ke_hoach.den_khong_gom,
                    chien_luoc=ke_hoach.chien_luoc,
                    ghi_de_config={KHOA_ARM: arm},
                    timeframe_detail=ke_hoach.timeframe_detail,
                    ma_gioi_han=ke_hoach.ma_gioi_han,
                ),
                giay_phep=GiayPhepChay(ledger=ledger, trial_id=tid, budget_line=DONG_NGAN_SACH),
                repo_dir=repo_dir,
                goc_tam=goc_theo_arm[arm],
            )
        except BacktestHongError as exc:
            _hoan_tra(ledger, [tid, *con_lai], f"freqtrade_backtesting_exit_{exc.returncode}")
            raise LoDungError(f"arm {arm}: {exc}") from exc
        except BoChayError as exc:
            _hoan_tra(ledger, [tid, *con_lai], f"bo_chay_tu_choi:{type(exc).__name__}")
            raise LoDungError(f"arm {arm}: {exc}") from exc

        # Con dấu NGAY khi kết quả tồn tại, TRƯỚC khi tính hay in bất cứ gì (L-Z53).
        ledger.seal(tid, seal_path=f"runs/{tid}/metrics.seal")

        try:
            lenhs = [lenh_tu_freqtrade(t, cfg=mt.cfg_phu, arm=arm) for t in kq.lenh]
            # TD-0338/TD-0339 — chỉ số Nhánh 1 + bằng chứng DR-D4-04 §7 + bất biến §1.7, đọc THẲNG từ export.
            chi_so_them = chi_so_tu_export(
                lenh=kq.lenh, lenhs=lenhs, cfg=mt.cfg_phu,
                observed_start=kq.observed_start, observed_end=kq.observed_end, ham_thanh_ly=ham_thanh_ly,
            )
            ban_ghi = dung_ban_ghi_arm(
                arm=arm,
                lenhs=lenhs,
                cua_so=(kq.observed_start, kq.observed_end),
                folds=folds,
                so_ma_da_chay=len(kq.ma_da_chay),
                delta_r_pham_vi=delta_r_pham_vi,
                provenance=Provenance(
                    params_source="yaml",
                    params_effective={KHOA_ARM: resolve(mt.cfg_phu, KHOA_ARM)},
                    git_sha=git_info.sha,
                    reproducible_from_sha=git_info.is_clean,
                    data_hashes=data_hashes,
                    cache_mode="none",
                    guard_passed=True,
                    runtime_image_digest=runtime_image_digest,
                ),
                trial_id=tid,
                chi_so_them=chi_so_them,
            )
            thu_muc = thu_muc_ra / tid
            thu_muc.mkdir(parents=True, exist_ok=True)
            duong = thu_muc / "arm_result.json"
            duong.write_text(json.dumps(ban_ghi, indent=2, ensure_ascii=False), encoding="utf-8")
            # DR-D4-04 §7 (i): tên chiến lược ĐÃ chạy — lấy từ `KetQuaChay`, tức từ khoá báo cáo thật.
            (thu_muc / "ket_qua_chay.json").write_text(
                json.dumps(
                    {
                        "trial_id": tid, "arm": arm, "chien_luoc": kq.chien_luoc,
                        "config_sha256": kq.config_sha256, "so_lenh": kq.so_lenh,
                        "observed_start": kq.observed_start.isoformat(),
                        "observed_end": kq.observed_end.isoformat(),
                    },
                    indent=2, ensure_ascii=False,
                ),
                encoding="utf-8",
            )
        except Exception as exc:
            ledger.consume(
                tid,
                outcome={"expectancy": None, "sharpe": None, "n_trades": kq.so_lenh, "max_single_loss_ratio": None},
                verdict="INCONCLUSIVE",
                rejection_reason=f"loi_sau_niem_phong:{type(exc).__name__}: {exc}"[:500],
            )
            _hoan_tra(ledger, con_lai, f"lo_dung_sau_loi_arm_{arm}:{type(exc).__name__}")
            raise LoDungError(f"arm {arm} lỗi SAU con dấu (đã tiêu, L-Z53): {exc}") from exc

        mean_r = ban_ghi["chi_so"]["mean_r"]
        ledger.consume(
            tid,
            outcome={
                "expectancy": mean_r["value"] if mean_r["status"] == "ok" else None,
                "sharpe": None,
                "n_trades": len(lenhs),
                "max_single_loss_ratio": None,
            },
            verdict="INCONCLUSIVE",
        )
        kc = ban_ghi["ket_cuc"]["value"]
        kc_m: Measured[str] = Measured(status=Status(ban_ghi["ket_cuc"]["status"]), value=kc)
        co_do = co_do_nhom_c(arm, kc_m)
        b17 = chi_so_them["bat_bien_1_7_ty_so_trung_vi"]
        if bat_bien_1_7_lech(b17):
            dung = (
                f"🛑 arm {arm}: bất biến §1.7 LỆCH — trung vị D_fill/D_ke = {b17.value:.4f} (DR-D4-15). "
                "DỪNG: mở lại DR-D4-12 §1 toàn bộ (§9 điều kiện 2)."
            )
            co_do = f"{co_do}\n{dung}" if co_do else dung
        ket_qua.append(KetQuaArm(arm=arm, trial_id=tid, duong_ban_ghi=duong, ket_cuc=kc, co_do=co_do))
    return ket_qua


__all__ = ["KeHoachLo", "KetQuaArm", "KhoaDoError", "LoDungError", "chay_lo"]
