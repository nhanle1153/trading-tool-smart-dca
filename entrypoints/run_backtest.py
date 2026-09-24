"""E1 — wrapper cho freqtrade backtesting (spec dòng 655).

Khung TD-0016: `main()` gọi `measurement_guard()` ở dòng đầu tiên sau parse
tham số (canh bởi L-Z36, TD-0017). TD-0018 nối thêm `assert_cache_none()`
(L-Z38) ngay sau guard — TỪ CHỐI nếu thiếu `--cache none`, không tự chèn.
TD-0057 nối `run_audit()` (E6, H16) ngay sau đó — "tự kiểm cả chính nó"
TRƯỚC MỖI lần backtest (spec dòng 660). TD-0072 nối thêm cổng H17 (TD-0316/`DR-LOCKBOX-02`: nay là `kiem_h17()`, không còn `verify_all_seals()`)
(H17) — không cho chạy nếu lockbox đang có seal không khớp dữ liệu.

TD-0313 (`DR-BC-01`) nối phần CHẠY THẬT, **sau** năm cổng trên và không đụng
một chữ nào của chúng. Ba điểm đáng đọc trước khi sửa file này:

🔑 **`--tap` là MỘT chuỗi nuôi BA chỗ** — `ro_cho_tap(tap)` (rổ + thư mục dữ
   liệu), `dataset_boundaries_from_config(cfg)[tap]` (biên `L-Z55`), và
   `ledger.reserve(dataset=tap)` (dòng sổ). Một nguồn ⇒ ba thứ không thể lệch
   nhau mà không ai thấy. `--tap LOCKBOX` KHÔNG có cửa chặn riêng ở đây:
   `ro_cho_tap()` đã từ chối và nêu `MT-60`, và hai cửa cho một luật là hai
   nguồn sự thật.

🔴 **Mặc định KHÔNG chạy.** Thiếu `--chay` thì E1 in kế hoạch rồi thoát
   `EXIT_CHUA_XAC_NHAN_CHAY`, **không đặt chỗ, không chạm dữ liệu**. Một lượt
   chạy thật trên CALIB/WFO là *đánh giá cấu hình* = "chạm" (`DR-014` §2) =
   tiêu 1 suất trong 114, và `seal()` làm nó không hoàn lại được (`L-Z53`).
   Một cờ gõ nhầm không được phép tiêu một suất.

🔴 **`--budget-line` KHÔNG có mặc định** (`DR-BC-01` §4). Câu N3 của `CLAUDE.md`
   gợi `B3` về ngữ nghĩa, nhưng biến nó thành mặc định CLI là đúng thứ
   `orchestrator.py:26-28` gọi tên: *"đoán hộ là cách chắc chắn tiêu sai ngân
   sách"* — người gõ lệnh sẽ không bao giờ phải nhìn thấy mình đang tiêu dòng nào.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import date
from pathlib import Path
from typing import Any

from tool_d.ablation import khoa_do
from tool_d.bo_chay.chay import BacktestHongError, chay_mot_luot
from tool_d.bo_chay.moi_truong import dung_moi_truong
from tool_d.bo_chay.trich_lenh import lenh_tu_freqtrade
from tool_d.bo_chay.yeu_cau import BoChayError, GiayPhepChay, YeuCauChay
from tool_d.calibration.bang_r import ghi_bang_r
from tool_d.calibration.ghi_de_b1 import KHOA_ARM, ghi_de_cho_b1
from tool_d.calibration.ung_vien import BUDGET_LINE_B1, UngVienError, doc_bang_ung_vien
from tool_d.config.loader import load_tool_d_config, resolve
from tool_d.gates.cache_policy import assert_cache_none
from tool_d.gates.d0_pre import require_d0_pre_complete
from tool_d.gates.exit_reason_thiet_ke import la_slot_ung_vien
from tool_d.ledger.bien_the import BienTheError, doc_khoa_bien_the, tinh_bien_the_hash
from tool_d.gates.dsr import N_DANG_KY
from tool_d.ledger.con_dau import duong_khai_so, ghi_con_dau
from tool_d.ledger.registry import (
    BUDGET_LINE_XAC,
    CTRL_BUDGET_LINE,
    TAP_XAC_NHAN,
    THAM_SO_CUA_SO_XAC,
    TrialLedger,
)
from tool_d.ledger.timerange import (
    TimerangeViolationError,
    assert_dataset_timerange,
    bien_xac_nhan,
    cua_so_tap,
    dataset_boundaries_from_config,
)
from tool_d.lockbox.h17 import in_va_ma_thoat, kiem_h17
from tool_d.measurement.gitinfo import get_git_info
from tool_d.measurement.guard import EXIT_GUARD_BLOCKED, GuardOutcome, measurement_guard
from tool_d.measurement.hashing import hash_many
from tool_d.pool_giai_doan import RoGiaiDoanError, ro_cho_tap
from touch_lockbox import EXIT_LOCKBOX_VERIFY_FAILED, LOCKBOX_DIR, LOCKBOX_FUTURES_DIR
from trial_ledger_audit import run_audit

ENTRYPOINT = "E1"

#: Thiếu `--chay`: đã in kế hoạch, chưa tiêu gì. KHÔNG phải lỗi.
#: Mã MỚI, không tái dùng `97` của `run_wfo.py` — giữ nguyên con số mà đổi nghĩa là
#: đúng lỗi "một tên hai nghĩa ở hai thời điểm" mà TD-0234 vừa phải sửa.
EXIT_CHUA_XAC_NHAN_CHAY = 105
#: `freqtrade backtesting` thoát khác 0 ⇒ đã `refund()` theo nguyên nhân MÁY.
EXIT_BACKTEST_HONG = 106
#: Lõi bộ chạy từ chối trước khi chạy (rổ sai, thiếu 5m, timerange sai…).
EXIT_BO_CHAY_TU_CHOI = 107

#: TD-0373 — `--budget-line B1` khi khoá `D5_DO_TAM_DUNG` đang bật (`DR-ZA-01` §2). Mã MỚI, không tái dùng
#: `110` của E3: hai khoá, hai quyết định, hai mã.
EXIT_D5_DO_TAM_DUNG = 113

DONG_NGAN_SACH = ("B1", "B2", "B3", "CTRL", "XAC")
TAP_HOP_LE = ("CALIB", "WFO", "XAC_NHAN")

#: TD-0389 (`DR-XAC-NHAN-01` §6 Q2, §7) — hai chế độ TÁCH BIỆT trên tập `XAC_NHAN`, mỗi chế độ đúng một dòng ngân sách.
#: ĐẾM không sinh con số hiệu năng nào (không `ket_qua.json`, không bảng R); TÍNH ghi hiện vật lớp xác nhận.
DONG_THEO_CHE_DO = {"DEM": "CTRL", "TINH": "XAC"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="E1 run_backtest.py — wrapper cho freqtrade backtesting")
    parser.add_argument(
        "--with-params-file",
        action="store_true",
        help="Cho phép chạy dù có <Strategy>.json cạnh strategy (0d.1) — cờ này được ghi vào provenance.",
    )
    parser.add_argument("--tap", choices=TAP_HOP_LE, help="Tập dữ liệu — quyết định rổ qua ro_cho_tap().")
    parser.add_argument("--tu", help="YYYY-MM-DD, mặc định = đầu biên của --tap.")
    parser.add_argument("--den", help="YYYY-MM-DD, cận KHÔNG BAO GỒM. Mặc định = mốc cuối tập (DR-D9-01).")
    parser.add_argument("--chien-luoc", default="ZoneAbsorption")
    parser.add_argument("--budget-line", choices=DONG_NGAN_SACH, help="BẮT BUỘC khi --chay. Không có mặc định.")
    parser.add_argument("--hypothesis-slot", help="BẮT BUỘC khi --chay.")
    parser.add_argument("--param-under-test", help="BẮT BUỘC khi --chay.")
    parser.add_argument("--param-value", help="BẮT BUỘC khi --chay. Đọc như JSON, không parse được thì giữ chuỗi.")
    parser.add_argument("--direction", default="LONG", choices=("LONG", "SHORT"))
    parser.add_argument(
        "--ghi-de", action="append", default=[], metavar="KHOA=GIATRI",
        help="Phủ một khoá dotted của tool_d_config.yaml, lặp lại được. Ví dụ tier_c.arm_ablation.arm=Z0",
    )
    parser.add_argument("--timeframe-detail", help="Ví dụ 5m. TỪ CHỐI nếu rổ không có dữ liệu khung đó.")
    parser.add_argument(
        "--che-do", choices=tuple(DONG_THEO_CHE_DO),
        help="BẮT BUỘC với --tap XAC_NHAN, không có mặc định: DEM (CTRL, chỉ đếm lệnh) hoặc TINH (XAC, tính mean_r một lần).",
    )
    parser.add_argument(
        "--chay", action="store_true",
        help="BẮT BUỘC để thật sự chạy. Thiếu cờ này: chỉ in kế hoạch, 0 suất trial.",
    )
    return parser


def _doc_ghi_de(cac_cap: list[str]) -> dict[str, Any]:
    ra: dict[str, Any] = {}
    for cap in cac_cap:
        if "=" not in cap:
            raise BoChayError(f"--ghi-de {cap!r} không có dấu '=' — cần dạng KHOA=GIATRI")
        khoa, _, gia_tri = cap.partition("=")
        try:
            ra[khoa.strip()] = json.loads(gia_tri)
        except json.JSONDecodeError:
            ra[khoa.strip()] = gia_tri
    return ra


def _cua_so(args, bien) -> tuple[date, date]:
    """Mặc định = trọn tập `--tap` NỬA MỞ `[start, end)` (`DR-D9-01`); tính và kiểm ở `cua_so_tap()` (TD-0347).

    Bản TD-0313 mặc định `bien.end + 1 ngày` với lý do *"mới phủ hết nến cuối"* — SAI: `bien.end` đã là cận không
    bao gồm (mốc 00:00 của tập sau), nên +1 ngày đọc thêm trọn một ngày của tập đó (với WFO: LOCKBOX)."""
    return cua_so_tap(
        bien,
        tu=date.fromisoformat(args.tu) if args.tu else None,
        den=date.fromisoformat(args.den) if args.den else None,
    )


def _doc_param_value(chuoi: str | None):
    if chuoi is None:
        return None
    try:
        return json.loads(chuoi)
    except json.JSONDecodeError:
        return chuoi


def _ghi_de_cua_luot(args) -> dict[str, Any]:
    """TD-0255 — B1: phần phủ SUY từ `--param-under-test`/`--param-value` (thứ vào SỔ), và TỪ CHỐI
    `--ghi-de`. Sổ và lượt chạy phải là MỘT cấu hình (bài học `MT-23`: sổ ghi CẤU HÌNH, không ghi TẬP
    LỆNH). Dòng ngân sách khác giữ `--ghi-de` như cũ."""
    if args.budget_line != BUDGET_LINE_B1:
        return _doc_ghi_de(args.ghi_de)
    if args.ghi_de:
        raise BoChayError(
            "B1 KHÔNG nhận --ghi-de: phần phủ suy từ --param-under-test/--param-value để sổ và lượt "
            "chạy là MỘT cấu hình (TD-0255)"
        )
    if not args.param_under_test:
        raise BoChayError("B1 cần --param-under-test (D5_MOC / D5_XAC_NHAN / tên tham số DR-D5-01 §2.1)")
    try:
        return ghi_de_cho_b1(args.param_under_test, _doc_param_value(args.param_value), doc_bang_ung_vien())
    except UngVienError as exc:
        raise BoChayError(str(exc)) from exc


def _kiem_ke_hoach_xac_nhan(args, cfg) -> None:
    """TD-0389 — kiểm lượt `--tap XAC_NHAN` TRƯỚC khi đọc rổ hay tốn dòng sổ nào. Raise `BoChayError`.

    `--param-under-test`/`--param-value` do E1 SUY (cùng khuôn B1, TD-0255): người gõ lệnh không tự khai cửa sổ được —
    sổ và lượt chạy phải cùng một cửa sổ."""
    if not args.che_do:
        raise BoChayError(f"--tap XAC_NHAN cần --che-do {'/'.join(DONG_THEO_CHE_DO)} — không có mặc định")
    if args.budget_line and args.budget_line != DONG_THEO_CHE_DO[args.che_do]:
        raise BoChayError(
            f"--che-do {args.che_do} đi với --budget-line {DONG_THEO_CHE_DO[args.che_do]}, nhận {args.budget_line}"
        )
    if args.param_under_test or args.param_value:
        raise BoChayError("XAC_NHAN KHÔNG nhận --param-under-test/--param-value: E1 suy từ --che-do và cửa sổ")
    if not args.hypothesis_slot or not args.den:
        raise BoChayError("XAC_NHAN cần --hypothesis-slot IQ-xxxx và --den (ngày đo, cận không bao gồm)")
    if args.che_do == "TINH":
        if args.direction != "LONG":
            raise BoChayError("TINH hiện chỉ nhận LONG (lenh_tu_freqtrade LONG-only) — kiểm TRƯỚC khi tốn dòng XAC")
        hien_vat = Path(".") / str(resolve(cfg, "tier_c.lop_xac_nhan_sau_t3.hien_vat"))
        if hien_vat.exists():
            raise BoChayError(f"{hien_vat} đã tồn tại — lớp xác nhận chỉ đo MỘT lần (DR-XAC-NHAN-01 §6 Q2)")


def _bien_tap(args, cfg):
    """Biên của `--tap`: ba tập niêm phong đọc từ `data_split`; `XAC_NHAN` dựng động từ sổ ý tưởng (TD-0389)."""
    if args.tap == TAP_XAC_NHAN:
        return bien_xac_nhan(cfg, args.hypothesis_slot, ngay_do=date.fromisoformat(args.den), repo_dir=Path("."))
    return dataset_boundaries_from_config(cfg)[args.tap]


def _lenh_da_dong(lenh: tuple[dict, ...]) -> list[dict]:
    """TD-0389 — lệnh ĐÃ ĐÓNG thật: bỏ lệnh bị Freqtrade ép đóng ở cuối cửa sổ (`force_exit`). ĐẾM và TÍNH dùng CÙNG
    hàm này nên tính trên đúng các lệnh đã đếm (DR-XAC-NHAN-01 §6 Q2)."""
    return [t for t in lenh if t.get("exit_reason") != "force_exit"]


def _ghi_hien_vat_xac_nhan(cfg, *, slot: str, tu: date, den: date, n_lenh: int, mean_r: float, config_sha256: str,
                           trial_id: str) -> Path:
    """TD-0389 — hiện vật đúng các khoá `tran_von.ly_do_chua_xac_nhan` kiểm. Từ chối ghi đè (một lần đo)."""
    duong = Path(".") / str(resolve(cfg, "tier_c.lop_xac_nhan_sau_t3.hien_vat"))
    duong.parent.mkdir(parents=True, exist_ok=True)
    with duong.open("x", encoding="utf-8") as f:
        json.dump(
            {
                "dr": "DR-LOCKBOX-04",
                "hypothesis_slot": slot,
                "tu_ngay": tu.isoformat(),
                "den_khong_gom": den.isoformat(),
                "n_lenh": n_lenh,
                "chi_so": str(resolve(cfg, "tier_c.lop_xac_nhan_sau_t3.chi_so")),
                "gia_tri": mean_r,
                "config_sha256": config_sha256,
                "trial_id": trial_id,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )
        f.write("\n")
    return duong


def _thieu_co(args) -> list[str]:
    """Cờ BẮT BUỘC khi `--chay`. Không cái nào có mặc định — xem docstring module."""
    return [
        ten
        for ten, gia_tri in (
            ("--tap", args.tap),
            ("--budget-line", args.budget_line),
            ("--hypothesis-slot", args.hypothesis_slot),
            ("--param-under-test", args.param_under_test),
            ("--param-value", args.param_value),
        )
        if not gia_tri
    ]


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    args, _ = build_parser().parse_known_args(argv)

    report = measurement_guard(ENTRYPOINT, argv=argv, with_params_file=args.with_params_file)
    if report.outcome is GuardOutcome.BLOCKED:
        return EXIT_GUARD_BLOCKED

    gate_exit = require_d0_pre_complete(ENTRYPOINT)
    if gate_exit is not None:
        return gate_exit

    cache_exit = assert_cache_none(argv)
    if cache_exit is not None:
        return cache_exit

    audit_exit, audit_text = run_audit()
    if audit_exit != 0:
        print(audit_text)
        return audit_exit

    # H17 ở service CHE lockbox (DR-LOCKBOX-02, TD-0316): cách ly còn hiệu lực + seal không bị
    # sửa + sổ truy cập. Băm dữ liệu (`verify_all_seals`, L-Z14) là việc của E4 ở service
    # `lockbox` — ở đây dữ liệu bị che CÓ CHỦ ĐÍCH nên nó FAIL mọi lần (trước TD-0316: exit 89).
    ma_h17 = in_va_ma_thoat(
        kiem_h17(lockbox_dir=LOCKBOX_DIR, data_dir=LOCKBOX_FUTURES_DIR),
        ma_that_bai=EXIT_LOCKBOX_VERIFY_FAILED,
    )
    if ma_h17 is not None:
        return ma_h17

    # TD-0373 — khoá đo D5: dòng B1 bị từ chối TRƯỚC khi đọc rổ, cấu hình hay dữ liệu, và trước `reserve()`.
    # Cửa `TrialLedger._kiem_cua_b1()` chặn lần nữa — đây là lớp sớm để không ai tốn công chuẩn bị một lượt.
    if args.budget_line == BUDGET_LINE_B1 and khoa_do.D5_DO_TAM_DUNG:
        print(f"🛑 {khoa_do.LY_DO_KHOA_D5}")
        return EXIT_D5_DO_TAM_DUNG

    # ── Từ đây là TD-0313. Năm cổng trên KHÔNG bị đụng. ──────────────────────
    if not args.tap:
        print(f"🛑 thiếu --tap (chọn: {', '.join(TAP_HOP_LE)})")
        return EXIT_BO_CHAY_TU_CHOI

    xac_nhan = args.tap == TAP_XAC_NHAN
    try:
        cfg = load_tool_d_config()
        if xac_nhan:
            _kiem_ke_hoach_xac_nhan(args, cfg)
        elif args.che_do or args.budget_line == "XAC":
            raise BoChayError("--che-do / --budget-line XAC chỉ dùng với --tap XAC_NHAN (TD-0389)")
        ro = ro_cho_tap(args.tap)  # đọc YAML rổ; CHƯA chạm dữ liệu thị trường
        bien = _bien_tap(args, cfg)
        tu, den = _cua_so(args, bien)
        if xac_nhan:
            args.param_under_test = THAM_SO_CUA_SO_XAC
            args.param_value = json.dumps({"che_do": args.che_do, "tu": tu.isoformat(), "den": den.isoformat()})
        ghi_de = _ghi_de_cua_luot(args)
        # Kiểm KẾ HOẠCH trước khi tốn một suất: một cửa sổ đã sai so với biên tập
        # thì không đáng tiêu trial để phát hiện. `den` là cận KHÔNG BAO GỒM nên
        # ngày cuối THỰC SỰ được đọc là `den - 1`.
        from datetime import timedelta

        assert_dataset_timerange(
            dataset=args.tap, observed_start=tu, observed_end=den - timedelta(days=1), boundary=bien
        )
    except (RoGiaiDoanError, TimerangeViolationError, BoChayError, KeyError, ValueError) as exc:
        print(f"🛑 {type(exc).__name__}: {exc}")
        return EXIT_BO_CHAY_TU_CHOI

    print(f"KẾ HOẠCH CHẠY — {ENTRYPOINT}")
    print("-" * 68)
    print(f"  tập            : {args.tap}  (biên {bien.start} → {bien.end})")
    print(f"  rổ             : {ro.file_ro}  — {len(ro.trading)} mã, mốc {ro.moc}")
    print(f"  dữ liệu        : {ro.thu_muc_du_lieu}")
    print(f"  cửa sổ         : [{tu}, {den})   (cận phải KHÔNG bao gồm)")
    print(f"  chiến lược     : {args.chien_luoc}")
    print(f"  ghi đè cấu hình: {ghi_de or '(không)'}")
    print(f"  timeframe-detail: {args.timeframe_detail or '(không)'}")
    if xac_nhan:
        print(f"  chế độ         : {args.che_do}  (slot {args.hypothesis_slot}, TD-0389)")
    print("-" * 68)

    if not args.chay:
        print("🛑 CHƯA CHẠY — thiếu cờ `--chay`. Không đặt chỗ, không chạm dữ liệu, 0 suất.")
        print("   Một lượt chạy thật trên CALIB/WFO tiêu 1 suất trong 114 và seal() không lùi được.")
        return EXIT_CHUA_XAC_NHAN_CHAY

    thieu = _thieu_co(args)
    if thieu:
        print(f"🛑 `--chay` nhưng thiếu {', '.join(thieu)} — không có mặc định (DR-BC-01 §4).")
        return EXIT_BO_CHAY_TU_CHOI

    param_value = _doc_param_value(args.param_value)

    # Dựng cấu hình phủ TRƯỚC khi đặt chỗ: dòng RESERVE phải mang `config_hash` và
    # `params_effective` CỦA BẢN SẼ CHẠY, không phải của file trong repo. `chay_mot_luot`
    # dựng lại trên cùng `goc` (tất định, cùng kết quả) — xem `goc_tam` bên dưới.
    import tempfile

    goc = Path(tempfile.mkdtemp(prefix=f"e1_{args.tap.lower()}_"))
    try:
        mt = dung_moi_truong(
            repo_dir=Path("."), goc=goc, ghi_de=ghi_de, ma_trong_ro=ro.trading, chien_luoc=args.chien_luoc
        )
    except BoChayError as exc:
        print(f"🛑 {exc}")
        return EXIT_BO_CHAY_TU_CHOI

    # `DR-BC-01` §3 — BĂM ≠ CHẠM: đọc byte để tính sha256 không phải "đánh giá cấu
    # hình" (`DR-014` §2), nên được phép đứng TRƯỚC `reserve()`. Phạm vi của ngoại lệ
    # đó hẹp đúng bằng câu vừa rồi; mọi việc đọc khác vẫn phải đứng SAU đặt chỗ.
    thu_muc = Path(".") / ro.thu_muc_du_lieu
    data_hashes = hash_many({f.name: f for f in sorted(thu_muc.glob("*.feather"))})

    # TD-0396 (`DR-BIEN-THE-01` §3) — dòng vào `N` của slot ứng viên `IQ-xxxx` mang định danh CẤU HÌNH, tính trên
    # bản phủ SẼ CHẠY (`mt.cfg_phu`), theo danh sách khoá DR thiết kế đã commit. Không tính được ⇒ từ chối (fail-closed).
    bien_the_hash = None
    if la_slot_ung_vien(args.hypothesis_slot) and args.budget_line not in (CTRL_BUDGET_LINE, BUDGET_LINE_XAC):
        try:
            bien_the_hash = tinh_bien_the_hash(mt.cfg_phu, doc_khoa_bien_the(args.hypothesis_slot))
        except (BienTheError, KeyError) as exc:
            print(f"🛑 không định danh được biến thể của {args.hypothesis_slot} — {exc}")
            return EXIT_BO_CHAY_TU_CHOI

    git_info = get_git_info(Path("."))
    ledger = TrialLedger()
    trial_id = ledger.reserve(  # L-Z52 — TRƯỚC khi chạm dữ liệu
        n_dang_ky=N_DANG_KY,
        budget_line=args.budget_line,
        hypothesis_slot=args.hypothesis_slot,
        direction=args.direction,
        dataset=args.tap,
        param_under_test=args.param_under_test,
        param_value=param_value,
        params_frozen_hash=mt.sha256_phu,
        config_hash=mt.sha256_phu,
        code_commit=git_info.sha,
        provenance={
            "params_source": "yaml",
            "params_effective": {k: resolve(mt.cfg_phu, k) for k in ghi_de},
            "git_sha": git_info.sha,
            "reproducible_from_sha": git_info.is_clean,
            "data_hashes": data_hashes,
            "cache_mode": "none",
            "guard_passed": True,
        },
        contribution=1,
        # TD-0389 — chế độ ĐẾM là CTRL *đo mô tả* đúng `["so_lenh"]` (DR-XAC-NHAN-01 §7); dòng khác không khai gì.
        ctrl_mo_ta_whitelist=["so_lenh"] if xac_nhan and args.che_do == "DEM" else None,
        bien_the_hash=bien_the_hash,
    )
    print(f"đã đặt chỗ {trial_id} (dòng {args.budget_line})")

    try:
        kq = chay_mot_luot(
            YeuCauChay(
                tap=args.tap,
                tu=tu,
                den_khong_gom=den,
                chien_luoc=args.chien_luoc,
                ghi_de_config=ghi_de,
                timeframe_detail=args.timeframe_detail,
            ),
            giay_phep=GiayPhepChay(ledger=ledger, trial_id=trial_id, budget_line=args.budget_line),
            repo_dir=Path("."),
            goc_tam=goc,
        )
    except BacktestHongError as exc:
        # Nguyên nhân do MÁY xác định (mã thoát thật), không nhận lời khai người
        # vận hành — `DR-014` §3. Chưa `seal()` nên `refund()` còn hợp lệ (`L-Z53`).
        ledger.refund(trial_id, cause_machine=f"freqtrade_backtesting_exit_{exc.returncode}")
        print(f"🛑 {exc}")
        return EXIT_BACKTEST_HONG
    except BoChayError as exc:
        ledger.refund(trial_id, cause_machine=f"bo_chay_tu_choi:{type(exc).__name__}")
        print(f"🛑 {exc}")
        return EXIT_BO_CHAY_TU_CHOI

    # `seal()` NGAY khi chỉ số đầu tiên tồn tại, TRƯỚC khi in/ghi kết quả
    # (`registry.py:558-561`) — đó là thứ làm `L-Z53` có nghĩa.
    # TD-0357 — hiện vật con dấu ghi TRƯỚC lời khai trong sổ; hỏng ⇒ chưa niêm phong ⇒ còn hoàn được.
    thu_muc_ra = Path("runs") / trial_id
    try:
        ghi_con_dau(Path("runs"), trial_id, kq)
    except Exception as exc:
        ledger.refund(trial_id, cause_machine=f"khong_ghi_duoc_con_dau:{type(exc).__name__}")
        print(f"🛑 không ghi được hiện vật con dấu: {exc}")
        return EXIT_BO_CHAY_TU_CHOI
    ledger.seal(trial_id, seal_path=duong_khai_so(trial_id))

    thu_muc_ra.mkdir(parents=True, exist_ok=True)
    # TD-0389: chế độ ĐẾM chỉ được sinh ra số lệnh + khoảng ngày (DR-XAC-NHAN-01 §6 Q2) ⇒ KHÔNG ghi `ket_qua.json`
    # (mang số dư đầu/cuối), KHÔNG dựng bảng R. Con dấu (`ghi_con_dau`) chỉ mang cửa sổ/số mã/số lệnh/băm — giữ.
    dem = xac_nhan and args.che_do == "DEM"
    if not dem:
        (thu_muc_ra / "ket_qua.json").write_text(
            json.dumps(
                {
                    "trial_id": trial_id,
                    "tap": kq.tap,
                    "file_ro": str(kq.file_ro),
                    "moc_ro": kq.moc_ro,
                    "so_ma": len(kq.ma_da_chay),
                    "timerange_yeu_cau": kq.timerange_yeu_cau,
                    "observed_start": kq.observed_start.isoformat(),
                    "observed_end": kq.observed_end.isoformat(),
                    "du_lieu_co_tu": kq.du_lieu_co_tu.isoformat() if kq.du_lieu_co_tu else None,
                    "du_lieu_co_den": kq.du_lieu_co_den.isoformat() if kq.du_lieu_co_den else None,
                    "starting_balance": kq.starting_balance,
                    "final_balance": kq.final_balance,
                    "so_lenh": kq.so_lenh,
                    "config_sha256": kq.config_sha256,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    # TD-0255 — R THEO TỪNG LỆNH cho tầng chọn giá trị D5 (`calibration/bang_r.py`). SAU con dấu: lỗi ở
    # đây KHÔNG hoàn lại được (`L-Z53`) ⇒ vẫn `consume`, kèm lý do; ĐÚNG MỘT lời gọi `consume` (TD-0313).
    # TD-0389: trên XAC_NHAN, ĐẾM và TÍNH cùng dùng `_lenh_da_dong` — tính đúng trên các lệnh đã đếm.
    loi_sau_dau: str | None = None
    expectancy: float | None = None
    lenh_luot = _lenh_da_dong(kq.lenh) if xac_nhan else list(kq.lenh)
    so_lenh = len(lenh_luot) if xac_nhan else kq.so_lenh
    try:
        if not dem:
            arm = str(resolve(mt.cfg_phu, KHOA_ARM))
            lenhs = [lenh_tu_freqtrade(t, cfg=mt.cfg_phu, arm=arm) for t in lenh_luot]
            ghi_bang_r(thu_muc_ra, lenhs, trial_id=trial_id)
            so_lenh = len(lenhs)
            # mean R THEO RỦI RO ĐÃ TRIỂN KHAI (`DR-D5-01` §5, `DR-D4-12` §1). 0 lệnh ⇒ None, không 0.0 (N6).
            expectancy = math.fsum(l.r_trien_khai for l in lenhs) / len(lenhs) if lenhs else None
            if xac_nhan and expectancy is not None:
                duong_hv = _ghi_hien_vat_xac_nhan(
                    cfg, slot=args.hypothesis_slot, tu=tu, den=den, n_lenh=so_lenh, mean_r=expectancy,
                    config_sha256=kq.config_sha256, trial_id=trial_id,
                )
                print(f"hiện vật lớp xác nhận: {duong_hv} — commit ĐÚNG MỘT LẦN (TD-0387)")
    except Exception as exc:
        loi_sau_dau = f"loi_sau_niem_phong:{type(exc).__name__}: {exc}"[:500]

    ledger.consume(
        trial_id,
        outcome={
            "expectancy": expectancy,
            "sharpe": None,
            "n_trades": so_lenh,
            "max_single_loss_ratio": None,
        },
        verdict="INCONCLUSIVE",
        rejection_reason=loi_sau_dau,
    )
    if loi_sau_dau is not None:
        print(f"🛑 lỗi SAU con dấu (suất đã tiêu, L-Z53): {loi_sau_dau}")
        return EXIT_BO_CHAY_TU_CHOI
    print(f"✅ {so_lenh} lệnh · đọc được [{kq.observed_start}, {kq.observed_end}] · {thu_muc_ra}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
