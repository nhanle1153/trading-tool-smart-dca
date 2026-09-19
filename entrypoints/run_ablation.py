"""E3 — D0.9 ablation, 9 arm × 2 hướng (spec dòng 657).

Khung TD-0016: chỉ dựng `main()` gọi `measurement_guard()` ở dòng đầu tiên
sau parse tham số (canh bởi L-Z36, TD-0017). TD-0057 nối `run_audit()`
(E6, H16) ngay sau đó — "tự kiểm cả chính nó" TRƯỚC MỖI lần chạy (spec
dòng 660). TD-0072 nối thêm cổng H17 (TD-0316/`DR-LOCKBOX-02`: nay là `kiem_h17()`). Logic ablation
thật chưa có mã việc TD riêng tại thời điểm sửa file này, sẽ thêm khi
tới Khối tương ứng.

🔴 TD-0165 nối `kiem_cong_d35()` (`L-Z56` CRITICAL) — entrypoint này TỪ
CHỐI chạy khi kết quả Δ_R của cổng D3.5 chưa commit đầy đủ. Chốt đó đứng
TRƯỚC cổng H17 (`kiem_h17()`) có chủ đích: nó rẻ, và nó chặn đúng thứ tự sai
mà DR-015 §1 gọi là "trạng thái tệ nhất có thể".

TD-0335 (`DR-D4-14`) nối phần CHẠY, **sau** năm cổng trên và không đụng chữ nào của
chúng. Vòng lô sống ở `tool_d/ablation/chay_lo.py`; ở đây chỉ in kế hoạch và gọi nó.

🔴 **Khoá đo** (`tool_d/ablation/khoa_do.py`, `D4_DO_TAM_DUNG = True`): `--chay` bị từ chối
bằng `EXIT_D4_DO_TAM_DUNG` TRƯỚC mọi lần đặt chỗ — D4-đo đang tạm dừng theo `DR-IQ-01` §1.
Mặc định KHÔNG chạy (thiếu `--chay` ⇒ chỉ in kế hoạch, 0 suất), cùng khuôn E1.
"""

from __future__ import annotations

import argparse
import sys
from datetime import timedelta
from pathlib import Path

from tool_d.ablation import khoa_do
from tool_d.ablation.ban_ghi import LO_ARM_D4, BanGhiArmError, doc_pham_vi_delta_r
from tool_d.ablation.chay_lo import KeHoachLo, KhoaDoError, LoDungError, chay_lo
from tool_d.bo_chay.yeu_cau import BoChayError
from tool_d.config.loader import load_tool_d_config
from tool_d.dr015.cong_d35 import EXIT_CHUA_CO_DELTA_R, CongD35ChuaDongError, kiem_cong_d35
from tool_d.gates.d0_pre import require_d0_pre_complete
from tool_d.ledger.registry import TrialLedger
from tool_d.ledger.timerange import (
    TimerangeViolationError,
    assert_dataset_timerange,
    dataset_boundaries_from_config,
)
from tool_d.lockbox.h17 import in_va_ma_thoat, kiem_h17
from tool_d.measurement.gitinfo import GitInfoError, get_git_info
from tool_d.measurement.guard import EXIT_GUARD_BLOCKED, GuardOutcome, measurement_guard
from tool_d.measurement.provenance import ImageDigestError, doc_runtime_image_digest
from tool_d.pool_giai_doan import RoGiaiDoanError, ro_cho_tap
from tool_d.wfo.folds import FoldConfigError, sinh_folds
from touch_lockbox import EXIT_LOCKBOX_VERIFY_FAILED, LOCKBOX_DIR, LOCKBOX_FUTURES_DIR
from trial_ledger_audit import run_audit

ENTRYPOINT = "E3"
TAP = "WFO"

#: Mã MỚI, không tái dùng mã của E1 (105–107) hay của ai khác (tới 108) — một con số
#: mang hai nghĩa ở hai entrypoint là lỗi "một tên hai nghĩa" TD-0234 đã phải sửa.
#: Thiếu `--chay`: đã in kế hoạch, chưa tiêu gì. KHÔNG phải lỗi.
EXIT_E3_CHUA_XAC_NHAN_CHAY = 109
#: `--chay` nhưng khoá đo đang bật (`DR-D4-14` §2.2).
EXIT_D4_DO_TAM_DUNG = 110
#: Lô từ chối trước khi chạy, hoặc dừng giữa chừng vì lỗi MÁY.
EXIT_LO_DUNG = 111
#: Lô chạy xong nhưng có cờ đỏ tầng đo (`DR-D4-10` §2.2, N10) — không được đọc như thành công.
EXIT_CO_DO_TANG_DO = 112


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="E3 run_ablation.py — D0.9 ablation (lô DR-D4-12 §4, Long)")
    parser.add_argument(
        "--with-params-file",
        action="store_true",
        help="Cho phép chạy dù có <Strategy>.json cạnh strategy (0d.1) — cờ này được ghi vào provenance.",
    )
    parser.add_argument("--hypothesis-slot", help="BẮT BUỘC khi --chay. Không có mặc định (DR-D4-14 §4).")
    parser.add_argument(
        "--chay", action="store_true",
        help="BẮT BUỘC để thật sự chạy. Thiếu cờ này: chỉ in kế hoạch, 0 suất trial.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    args, _ = build_parser().parse_known_args(argv)

    report = measurement_guard(ENTRYPOINT, argv=argv, with_params_file=args.with_params_file)
    if report.outcome is GuardOutcome.BLOCKED:
        return EXIT_GUARD_BLOCKED

    gate_exit = require_d0_pre_complete(ENTRYPOINT)
    if gate_exit is not None:
        return gate_exit

    audit_exit, audit_text = run_audit()
    if audit_exit != 0:
        print(audit_text)
        return audit_exit

    # 🔴 L-Z56 (TD-0165) — đứng TRƯỚC mọi việc tốn thời gian, và trước cả
    # verify_seal: chạy ablation mà chưa có Δ_R đã commit là chính trạng
    # thái DR-015 §1 gọi là "tệ nhất có thể" (kết luận Z0-vs-DCA hình
    # thành TRƯỚC, thước kiểm SAU). Từ chối sớm, không đốt thời gian.
    try:
        kiem_cong_d35()
    except CongD35ChuaDongError as exc:
        print(exc)
        return EXIT_CHUA_CO_DELTA_R

    # H17 ở service CHE lockbox (DR-LOCKBOX-02, TD-0316): cách ly còn hiệu lực + seal không bị
    # sửa + sổ truy cập. Băm dữ liệu (`verify_all_seals`, L-Z14) là việc của E4 ở service
    # `lockbox` — ở đây dữ liệu bị che CÓ CHỦ ĐÍCH nên nó FAIL mọi lần (trước TD-0316: exit 89).
    ma_h17 = in_va_ma_thoat(
        kiem_h17(lockbox_dir=LOCKBOX_DIR, data_dir=LOCKBOX_FUTURES_DIR),
        ma_that_bai=EXIT_LOCKBOX_VERIFY_FAILED,
    )
    if ma_h17 is not None:
        return ma_h17

    # ── Từ đây là TD-0335. Năm cổng trên KHÔNG bị đụng. ─────────────────────
    try:
        cfg = load_tool_d_config()
        ro = ro_cho_tap(TAP)  # đọc YAML rổ; CHƯA chạm dữ liệu thị trường
        bien = dataset_boundaries_from_config(cfg)[TAP]
        # DR-D9-01: WFO = [T1, T2) NỬA MỞ — `bien.end` là T2, và giờ 00:00 của T2 là mốc LOCKBOX. Bản đầu (TD-0335) dùng
        # `bien.end + 1 ngày` và lấn một giờ qua mốc đó; lộ ra khi chốt 5m từ chối lượt đếm TD-0345 (19/09/2026).
        tu, den = bien.start, bien.end  # `den` KHÔNG bao gồm
        assert_dataset_timerange(dataset=TAP, observed_start=tu, observed_end=den - timedelta(days=1), boundary=bien)
    except (RoGiaiDoanError, TimerangeViolationError, KeyError) as exc:
        print(f"🛑 {type(exc).__name__}: {exc}")
        return EXIT_LO_DUNG

    print(f"KẾ HOẠCH LÔ — {ENTRYPOINT} (DR-D4-12 §4, DR-D4-14)")
    print("-" * 68)
    print(f"  arm (thứ tự chạy): {', '.join(LO_ARM_D4)}  — {len(LO_ARM_D4)} suất B2, Long")
    print(f"  tập            : {TAP}  (biên {bien.start} → {bien.end})")
    print(f"  rổ             : {ro.file_ro}  — {len(ro.trading)} mã, mốc {ro.moc}")
    print(f"  cửa sổ         : [{tu}, {den})   (cận phải KHÔNG bao gồm)")
    print("  timeframe-detail: 5m")
    print(f"  hypothesis_slot: {args.hypothesis_slot or '(chưa khai)'}")
    print(f"  khoá đo        : {'BẬT — D4-đo tạm dừng' if khoa_do.D4_DO_TAM_DUNG else 'tắt'}")
    print("-" * 68)

    if not args.chay:
        print("🛑 CHƯA CHẠY — thiếu cờ `--chay`. Không đặt chỗ, không chạm dữ liệu, 0 suất.")
        return EXIT_E3_CHUA_XAC_NHAN_CHAY

    # Khoá đo đứng TRƯỚC mọi kiểm cờ khác: khi D4-đo tạm dừng thì không có câu trả lời
    # nào khác cho `--chay`. `chay_lo()` tự kiểm lại lần nữa ở lệnh đầu của nó.
    if khoa_do.D4_DO_TAM_DUNG:
        print(f"🛑 {khoa_do.LY_DO_KHOA}")
        return EXIT_D4_DO_TAM_DUNG

    if not args.hypothesis_slot:
        print("🛑 `--chay` nhưng thiếu --hypothesis-slot — không có mặc định (DR-D4-14 §4).")
        return EXIT_LO_DUNG

    try:
        ket_qua = chay_lo(
            KeHoachLo(tu=tu, den_khong_gom=den, hypothesis_slot=args.hypothesis_slot),
            ledger=TrialLedger(),
            repo_dir=Path("."),
            thu_muc_ra=Path("runs"),
            folds=sinh_folds(cfg),
            delta_r_pham_vi=doc_pham_vi_delta_r(),
            git_info=get_git_info(Path(".")),
            runtime_image_digest=doc_runtime_image_digest(Path(".")),
        )
    except KhoaDoError as exc:
        print(f"🛑 {exc}")
        return EXIT_D4_DO_TAM_DUNG
    except (LoDungError, BoChayError, BanGhiArmError, FoldConfigError, GitInfoError, ImageDigestError) as exc:
        print(f"🛑 {type(exc).__name__}: {exc}")
        return EXIT_LO_DUNG

    co_do = [k.co_do for k in ket_qua if k.co_do]
    for k in ket_qua:
        print(f"  {k.arm:6s} {k.trial_id}  kết cục {k.ket_cuc}  → {k.duong_ban_ghi}")
    for dong in co_do:
        print(dong)
    return EXIT_CO_DO_TANG_DO if co_do else 0


if __name__ == "__main__":
    sys.exit(main())
