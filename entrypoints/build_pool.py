"""E7 — chốt pool giao dịch (TD-0083) + tập EXPLORE (§0.3, §0.3b, §9c.4b).

🔴 H1-D ĐẦY ĐỦ (pairlist point-in-time chống survivorship bias khi
backtest xuyên nhiều mốc thời gian, spec dòng 4354) là việc RIÊNG của D1
(xem TASKS.md "Việc đã biết là sẽ có, chưa mở") — CHƯA viết ở đây.
TD-0083 chỉ làm việc HẸP HƠN: CHỐT MỘT LẦN danh sách pool giao dịch +
tập EXPLORE tại thời điểm hiện tại, tiêu 4 trial B0 (DR-D0PRE-05).

Khung TD-0016: `main()` gọi `measurement_guard()` ở dòng đầu tiên. Ghi
`config/pool.yaml` — MỘT LẦN, không được chọn lại sau khi thấy overlap
với Tool A (spec dòng 350-352): nếu file đã tồn tại, TỪ CHỐI ghi đè.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from tool_d.api_client.binance_public import BinancePublicApiError, get_exchange_info, get_ticker_24hr
from tool_d.gates.dsr import N_DANG_KY
from tool_d.ledger.registry import BudgetExhaustedError, TrialLedger
from tool_d.measurement.gitinfo import get_git_info
from tool_d.measurement.guard import EXIT_GUARD_BLOCKED, GuardOutcome, measurement_guard
from tool_d.pool import build_symbol_stats, compute_pool

ENTRYPOINT = "E7"

# DR-D0PRE-05 — chốt theo lý do độc lập, KHÔNG suy ngược từ pool_size_target.
AGE_FLOOR_DAYS = 180
VOLUME_FLOOR_USDT = 15_000_000.0

POOL_OUTPUT_PATH = Path("config/pool.yaml")

EXIT_POOL_ALREADY_COMMITTED = 94
EXIT_FETCH_FAILED = 95
EXIT_BUDGET_EXHAUSTED = 96

# 4 tiêu chí §0.3 — mỗi tiêu chí tiêu đúng 1 trial B0, KHÔNG phân biệt
# việc kết luận có ra một con số ngưỡng hay không (DR-D0PRE-05 mục 3/5).
CRITERIA = (
    (
        "volume_24h_usdt",
        VOLUME_FLOOR_USDT,
        "Ngưỡng 15.000.000 USDT/ngày — đủ sâu để volume_ratio (ZSS) không "
        "bị chi phối bởi vài lệnh cá biệt (DR-D0PRE-05 mục 2.i)",
    ),
    (
        "listing_age_days",
        AGE_FLOOR_DAYS,
        "Ngưỡng 180 ngày — đủ lịch sử liên tục cho CALIB/WFO, loại mã mới "
        "niêm yết đang biến động bất thường (DR-D0PRE-05 mục 2.ii)",
    ),
    (
        "post_only_cost_economics",
        None,
        "Không cần ngưỡng riêng — thuộc tính chung của sàn, thoả gián "
        "tiếp qua ngưỡng volume (DR-D0PRE-05 mục 2.iii)",
    ),
    (
        "tp_opposite_zone_distance",
        None,
        "Không cần ngưỡng pool tĩnh — kiểm tại thời điểm vào lệnh, không "
        "phải thuộc tính tĩnh của một mã (DR-D0PRE-05 mục 2.iv)",
    ),
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="E7 build_pool.py — chốt pool giao dịch (TD-0083)")
    parser.add_argument(
        "--with-params-file",
        action="store_true",
        help="Cho phép chạy dù có <Strategy>.json cạnh strategy (0d.1) — cờ này được ghi vào provenance.",
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Thực sự tiêu 4 trial B0 và ghi config/pool.yaml. Thiếu cờ này chỉ IN kết quả (chạy thử, không ghi sổ).",
    )
    parser.add_argument(
        "--ro-t1",
        action="store_true",
        help=(
            "TD-0247 / DR-D1-03: dựng lại rổ pool ĐÚNG TẠI T1 (0 trial, không ghi sổ). "
            "Thiếu --ghi chỉ IN kết quả; có --ghi thì ghi config/pool_t1.yaml (từ chối ghi đè)."
        ),
    )
    parser.add_argument(
        "--ro-t0",
        action="store_true",
        help=(
            "TD-0300 / DR-D1-05: dựng rổ pool ĐÚNG TẠI T0 cho CALIB (0 trial). "
            "Thiếu --ghi chỉ IN; có --ghi thì ghi config/pool_t0.yaml (từ chối ghi đè)."
        ),
    )
    parser.add_argument(
        "--ghi",
        action="store_true",
        help="Đi kèm --ro-t1/--ro-t0: thực sự ghi config/pool_<mốc>.yaml.",
    )
    parser.add_argument(
        "--check-min-notional",
        action="store_true",
        help="TD-0082: đối chiếu min notional + độ thô bước lot của pool đã chốt với tranche 1 nhỏ nhất (chỉ đọc, 0 trial).",
    )
    return parser


# TD-0082 — ba độ rộng zone spec dùng minh hoạ ở §6.8f (rộng / trung bình / hẹp).
R_EFF_GRID = (0.03, 0.015, 0.009)

# TD-0171 — dải `Π mult_*` (§6.2). Bảng cũ chỉ đo ĐÚNG MỘT điểm (1,0) mà
# không nói ra là mình đang đo điểm nào, nên đọc thành "mọi trường hợp".
# `mult_edge = 1.0` ở mọi điểm: backtest chưa đủ 50 lệnh live (spec dòng 1774).
MULT_GRID: tuple[tuple[str, float], ...] = (
    ("1,000 — mọi hệ số tối đa (ca TỐT NHẤT, tương đương bảng cũ)", 1.0),
    ("0,700 — regime weak (ADX 20–25)", 0.7),
    ("0,434 — weak × ZSS 0,62 (ZSS đo thật ở MT-16)", 0.7 * 0.62),
    ("0,326 — thêm corr 0,75", 0.7 * 0.62 * 0.75),
    ("0,175 — weak × ZSS sàn 0,5 × corr 0,5", 0.7 * 0.5 * 0.5),
    ("0,044 — ca XẤU NHẤT khả dĩ (thêm dd soft 0,5 × deploy 0,5)", 0.7 * 0.5 * 0.5 * 0.5 * 1.0 * 0.5),
)

#: `stoploss` của Freqtrade vào sàn qua `stoploss_reserve`. Đọc từ config
#: THẬT, không chép hằng số — chép là tạo nguồn sự thật thứ hai (MT-03).
FREQTRADE_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "freqtrade" / "config.json"


def _doc_stoploss() -> float:
    import json

    return float(json.loads(FREQTRADE_CONFIG_PATH.read_text(encoding="utf-8"))["stoploss"])


def check_min_notional() -> int:
    """In bảng đối chiếu (markdown) cho pool đã chốt. Chỉ đọc metadata sàn —
    không phải "chạm dữ liệu" (DR-014 mục 2), không ghi sổ."""
    from tool_d.config.loader import load_tool_d_config
    from tool_d.api_client.binance_public import get_ticker_price
    from tool_d.notional import build_symbol_filters, check_symbol, sl_hieu_dung

    if not POOL_OUTPUT_PATH.exists():
        print(f"🛑 {POOL_OUTPUT_PATH} chưa có — chốt pool (TD-0083) trước.")
        return EXIT_FETCH_FAILED
    pool = set(yaml.safe_load(POOL_OUTPUT_PATH.read_text(encoding="utf-8"))["trading"])
    cfg = load_tool_d_config()
    e_d, rho, n_tr = cfg.tier_a["E_D"], cfg.tier_a["rho_pct"], cfg.tier_c["n_tranches"]
    try:
        filters = build_symbol_filters(get_exchange_info(), get_ticker_price(), pool)
    except (BinancePublicApiError, ValueError) as exc:
        print(f"🛑 Tải/ghép dữ liệu thất bại: {exc}")
        return EXIT_FETCH_FAILED

    sl_cfg = _doc_stoploss()
    print(f"Pool: {len(filters)} mã | E_D={e_d} | rho={rho}% | n_tranches={n_tr} | strategy.stoploss={sl_cfg}")

    # 🔴 HAI đường chạy, HAI sàn khác nhau. In cả hai: một cấu hình qua sàn ở
    # backtest (D4) vẫn có thể rớt sàn ở live (D11/D12), im lặng.
    for duong_chay in ("backtest_vao_lenh", "live_vao_lenh"):
        stoploss = sl_hieu_dung(duong_chay, strategy_stoploss=sl_cfg)
        ve = {"cost": 0, "amount": 0}
        for f in filters:
            c0 = check_symbol(
                f, e_d=e_d, rho_pct=rho, mult_product=1.0, r_eff=R_EFF_GRID[0],
                n_tranches=n_tr, stoploss=stoploss,
            )
            ve[c0.san_ve_thang] += 1

        print(f"\n### Qua sàn min-notional — đường chạy `{duong_chay}` (stoploss {stoploss})\n")
        print(f"Vế quyết định sàn: cost {ve['cost']} mã | amount (minQty×giá) {ve['amount']} mã\n")
        print("| Π mult_* | " + " | ".join(f"R_eff {r:.1%}" for r in R_EFF_GRID) + " |")
        print("|---|" + "---|" * len(R_EFF_GRID))
        for ten, m in MULT_GRID:
            o = []
            for r in R_EFF_GRID:
                checks = [
                    check_symbol(
                        f, e_d=e_d, rho_pct=rho, mult_product=m, r_eff=r,
                        n_tranches=n_tr, stoploss=stoploss,
                    )
                    for f in filters
                ]
                ok = sum(c.passes_min_notional for c in checks)
                o.append(f"{ok}/{len(checks)} (tr.1 = {checks[0].tranche1_notional_usdt:.2f})")
            print(f"| {ten} | " + " | ".join(o) + " |")
        bad = [
            c
            for c in (
                check_symbol(
                    f, e_d=e_d, rho_pct=rho, mult_product=1.0, r_eff=R_EFF_GRID[0],
                    n_tranches=n_tr, stoploss=stoploss,
                )
                for f in filters
            )
            if not c.passes_min_notional
        ]
        print(f"\nRớt ở ca TỐT NHẤT (Π mult_* = 1, zone 3%): {len(bad)}/{len(filters)}"
              + (" — " + ", ".join(f"{c.symbol} (sàn {c.san_usdt:.2f})" for c in bad) if bad else ""))
    stoploss = sl_hieu_dung("backtest_vao_lenh", strategy_stoploss=sl_cfg)

    print("\n### L-Z20 (làm tròn lot) — KHÔNG phụ thuộc mult_* (dung sai neo vào rho thô)\n")
    print("| R_eff | Qua L-Z20 |")
    print("|---|---|")
    for r in R_EFF_GRID:
        checks = [
            check_symbol(
                f, e_d=e_d, rho_pct=rho, mult_product=1.0, r_eff=r,
                n_tranches=n_tr, stoploss=stoploss,
            )
            for f in filters
        ]
        print(f"| {r:.1%} | {sum(c.passes_lz20 for c in checks)}/{len(checks)} |")

    return 0


RO_T1_OUTPUT_PATH = Path("config/pool_t1.yaml")
MOC_RO_HOP_LE = ("t0", "t1")  # DR-D1-05: T2 ⏸ (MT-60)
THU_MUC_EXPLORE = Path("user_data/data/explore/futures")
NGUON_TD0230 = Path("docs/du-lieu-do/td0230-lech-song-sot-pool.json")
NGUON_TD0231 = Path("docs/du-lieu-do/td0231-pool-point-in-time.json")

EXIT_RO_T1_LECH_TD0231 = 97
EXIT_RO_T1_CAY_BAN = 98
EXIT_RO_T1_EXPLORE = 99


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def sinh_ro_t1(**kw) -> int:
    """Giữ tên cũ (TD-0247) — rổ tại `T1`. Xem `sinh_ro_tai_moc()`."""
    return sinh_ro_tai_moc(moc_ten="t1", **kw)


def sinh_ro_tai_moc(
    *,
    moc_ten: str,
    ghi: bool,
    repo_dir: Path = Path("."),
    doc_volume_thang=None,
    lay_exchange_info=None,
    thay_doi_chua_commit=None,
    bay_gio=None,
    lay_git_info=None,
) -> int:
    """TD-0247 / TD-0300 (`DR-D1-03` §2, `DR-D1-05`) — bộ sinh rổ ĐÚNG TẠI MỘT MỐC có xuất xứ.
    **0 trial**, không ghi sổ. `moc_ten` ∈ `MOC_RO_HOP_LE` (mốc `tier_c.data_split`); đích
    `config/pool_<moc_ten>.yaml`; đối chiếu `td0231["pool_dung_tai_<moc_ten>"]`.

    Thứ tự fail-closed:
      1. (khi `ghi`) file đích đã tồn tại ⇒ từ chối ghi đè (khuôn E7);
      2. (khi `ghi`) có thay đổi chưa commit trong vùng ảnh hưởng phép đo ⇒ từ chối,
         vì `git_sha` ghi vào file phải trỏ đúng mã đã sinh ra nó;
      3. thư mục EXPLORE không đọc được / rỗng ⇒ từ chối (tập rỗng nhận lại mã phải loại);
      4. tính lại rổ đủ tiêu chí tại mốc từ kho lưu trữ; KHÔNG khít `TD-0231` ⇒ từ chối;
      5. ghép rổ cuối (− EXPLORE đã dùng − TRADIFI).

    Các tham số hàm (`doc_volume_thang`, `lay_exchange_info`, `thay_doi_chua_commit`,
    `bay_gio`, `lay_git_info`) chỉ để test tiêm thay mạng/git — mặc định là đường sản xuất thật.
    """
    import json
    from datetime import date, datetime, timezone

    from tool_d.api_client.binance_public import KhoLuuTruError, doc_quote_volume_1d_thang
    from tool_d.config.loader import load_tool_d_config, resolve
    from tool_d.measurement.gitinfo import thay_doi_anh_huong_phep_do
    from tool_d.pool_t1 import ThuMucExploreError, dung_ro_tai_moc, ghep_ro_t1, ma_co_du_lieu_explore

    doc_volume_thang = doc_volume_thang or (
        lambda sym, nam, thang: doc_quote_volume_1d_thang(symbol=sym, nam=nam, thang=thang)
    )
    lay_exchange_info = lay_exchange_info or get_exchange_info
    thay_doi_chua_commit = thay_doi_chua_commit or thay_doi_anh_huong_phep_do
    bay_gio = bay_gio or (lambda: datetime.now(timezone.utc))
    lay_git_info = lay_git_info or get_git_info

    if moc_ten not in MOC_RO_HOP_LE:
        raise ValueError(f"moc_ten {moc_ten!r} không thuộc {MOC_RO_HOP_LE} (DR-D1-05: rổ T2 ⏸ MT-60)")
    duong_ra = Path(f"config/pool_{moc_ten}.yaml")
    MOC = moc_ten.upper()
    dich = repo_dir / duong_ra
    if ghi and dich.exists():
        print(
            f"🛑 {duong_ra} đã tồn tại — rổ {MOC} ĐÃ được sinh. KHÔNG sinh lại "
            "(spec dòng 350-352: không chọn lại pool sau khi đã thấy kết quả). "
            "Xoá thủ công + ghi DR mới nếu thực sự cần."
        )
        return EXIT_POOL_ALREADY_COMMITTED
    if ghi:
        ban = thay_doi_chua_commit(repo_dir)
        if ban:
            print(
                "🛑 Có thay đổi chưa commit trong vùng ảnh hưởng phép đo — git_sha ghi vào "
                "file rổ sẽ KHÔNG trỏ đúng mã đã sinh ra nó. Commit trước:\n  "
                + "\n  ".join(ban)
            )
            return EXIT_RO_T1_CAY_BAN

    try:
        explore_da_dung = ma_co_du_lieu_explore(repo_dir / THU_MUC_EXPLORE)
    except ThuMucExploreError as exc:
        print(f"🛑 {exc}")
        return EXIT_RO_T1_EXPLORE

    cfg = load_tool_d_config(repo_dir / "config" / "tool_d_config.yaml")
    moc_ngay = date.fromisoformat(str(resolve(cfg, "tier_c.data_split")[moc_ten]))
    khoang = json.loads((repo_dir / NGUON_TD0230).read_text(encoding="utf-8"))["khoang_ton_tai"]
    td0231 = json.loads((repo_dir / NGUON_TD0231).read_text(encoding="utf-8"))

    print(f"Mốc {MOC} = {moc_ngay} · ứng viên từ TD-0230: {len(khoang)} mã · EXPLORE đã dùng: {len(explore_da_dung)} mã")
    try:
        kq = dung_ro_tai_moc(
            moc_ngay,
            khoang,
            doc_volume_thang=doc_volume_thang,
            age_floor_days=AGE_FLOOR_DAYS,
            volume_floor_usdt=VOLUME_FLOOR_USDT,
        )
        exchange_info = lay_exchange_info()
    except (KhoLuuTruError, BinancePublicApiError) as exc:
        print(f"🛑 Tải dữ liệu thất bại, KHÔNG sinh rổ nửa vời: {exc}")
        return EXIT_FETCH_FAILED

    # DR-D1-03 §2 — đối chiếu độc lập: hai đường chạy cùng logic phải ra cùng một rổ.
    tham_chieu = td0231[f"pool_dung_tai_{moc_ten}"]
    lech_moc = td0231["moc"].get(moc_ten) != moc_ngay.isoformat()
    chi_moi = sorted(set(kq.pool_dung) - set(tham_chieu["danh_sach"]))
    chi_td0231 = sorted(set(tham_chieu["danh_sach"]) - set(kq.pool_dung))
    if lech_moc or chi_moi or chi_td0231:
        print(
            f"🛑 Rổ đủ tiêu chí tại {MOC} tính lại KHÔNG khít TD-0231 — một trong hai đường "
            f"đang sai, không ghi.\n  mốc TD-0231: {td0231['moc'].get(moc_ten)} vs {moc_ngay}\n"
            f"  chỉ có ở lần tính mới ({len(chi_moi)}): {chi_moi}\n"
            f"  chỉ có ở TD-0231 ({len(chi_td0231)}): {chi_td0231}"
        )
        return EXIT_RO_T1_LECH_TD0231

    ro = ghep_ro_t1(kq.pool_dung, explore_da_dung, exchange_info["symbols"])
    print(
        f"Đủ tiêu chí tại {MOC}: {len(kq.pool_dung)} (khít TD-0231) · loại EXPLORE đã dùng: "
        f"{len(ro.loai_explore_da_dung)} · loại TRADIFI: {len(ro.loai_tradifi)} · "
        f"RỔ {MOC}: {len(ro.trading)} mã"
    )
    print(
        f"Không đo được — 404: {len(kq.khong_do_duoc_404)} · thiếu ngày: "
        f"{len(kq.khong_do_duoc_thieu_ngay)} (ghi riêng, KHÔNG tính là trượt tiêu chí)"
    )
    if not ghi:
        print(f"\n(chạy thử — thêm --ghi để ghi {duong_ra})")
        return 0

    git_info = lay_git_info(repo_dir)
    dich.parent.mkdir(parents=True, exist_ok=True)
    dich.write_text(
        yaml.dump(
            {
                "_doc": (
                    f"TD-0247/TD-0300 / DR-D1-03, DR-D1-05 — rổ pool ĐÚNG TẠI {MOC}, sinh bằng E7 "
                    f"--ro-{moc_ten} --ghi. 0 trial. KHÔNG phải config/pool.yaml (rổ hôm nay, DR-D1-05 §1)."
                ),
                f"moc_{moc_ten}": moc_ngay.isoformat(),
                "criteria": {
                    "volume_24h_usdt_min": VOLUME_FLOOR_USDT,
                    "listing_age_days_min": AGE_FLOOR_DAYS,
                },
                "trading": list(ro.trading),
                "loai": {
                    "explore_da_dung": list(ro.loai_explore_da_dung),
                    "tradifi_perpetual": list(ro.loai_tradifi),
                },
                "khong_do_duoc": {
                    "kho_404": list(kq.khong_do_duoc_404),
                    "thieu_hang_dung_ngay_t1": list(kq.khong_do_duoc_thieu_ngay),
                },
                "dem": {
                    "ung_vien_song_tai_t1": len(kq.ung_vien_song),
                    "du_tieu_chi_tai_t1": len(kq.pool_dung),
                    "onboard_ngay_chinh_xac": len(kq.onboard_chinh_xac),
                    "onboard_xap_xi_theo_thang": kq.onboard_xap_xi,
                },
                "explore_da_dung_chup_luc_sinh": {
                    "thu_muc": str(THU_MUC_EXPLORE),
                    "n": len(explore_da_dung),
                    "danh_sach": sorted(explore_da_dung),
                },
                "xuat_xu": {
                    "git_sha": git_info.sha,
                    "sinh_luc_utc": bay_gio().isoformat(),
                    "nguon_khoang_ton_tai": {"file": str(NGUON_TD0230), "sha256": _sha256(repo_dir / NGUON_TD0230)},
                    "doi_chieu_td0231": {
                        "file": str(NGUON_TD0231),
                        "sha256": _sha256(repo_dir / NGUON_TD0231),
                        "khit": True,
                    },
                    "trial": 0,
                },
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    print(f"\n✅ Đã ghi {duong_ra} — {len(ro.trading)} mã, git_sha {git_info.sha[:7]}, 0 trial")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    args, _ = build_parser().parse_known_args(argv)

    report = measurement_guard(ENTRYPOINT, argv=argv, with_params_file=args.with_params_file)
    if report.outcome is GuardOutcome.BLOCKED:
        return EXIT_GUARD_BLOCKED

    if args.ro_t1:
        return sinh_ro_t1(ghi=args.ghi)
    if args.ro_t0:
        return sinh_ro_tai_moc(moc_ten="t0", ghi=args.ghi)

    if args.check_min_notional:
        return check_min_notional()

    if args.commit and POOL_OUTPUT_PATH.exists():
        print(
            f"🛑 {POOL_OUTPUT_PATH} đã tồn tại — pool ĐÃ được chốt trước đó. "
            "KHÔNG được chọn lại (spec dòng 350-352, §9c.4b ràng buộc (b)). "
            "Xoá thủ công + ghi DR mới nếu thực sự cần đổi tiêu chí."
        )
        return EXIT_POOL_ALREADY_COMMITTED

    try:
        exchange_info = get_exchange_info()
        tickers = get_ticker_24hr()
    except BinancePublicApiError as exc:
        print(f"🛑 Tải dữ liệu thất bại: {exc}")
        return EXIT_FETCH_FAILED

    stats = build_symbol_stats(exchange_info, tickers)
    result = compute_pool(stats, age_floor_days=AGE_FLOOR_DAYS, volume_floor_usdt=VOLUME_FLOOR_USDT)

    print(f"Tổng hợp đồng PERPETUAL/USDT đang TRADING: {len(stats)}")
    print(f"Pool giao dịch: {len(result.trading)} mã")
    print(f"Tập EXPLORE: {len(result.explore)} mã (gồm BTC/ETH)")

    if not args.commit:
        print("\n(chạy thử — dùng --commit để tiêu 4 trial B0 và ghi file thật)")
        return 0

    ledger = TrialLedger()
    git_info = get_git_info(Path("."))
    trial_ids: list[str] = []
    try:
        for param_name, value, note in CRITERIA:
            tid = ledger.reserve(
                n_dang_ky=N_DANG_KY,
                budget_line="B0",
                hypothesis_slot="POOL-0.3",
                direction="LONG",
                dataset="N/A",
                param_under_test=param_name,
                param_value=value,
                params_frozen_hash="n/a",
                config_hash="n/a",
                code_commit=git_info.sha,
                provenance={
                    "params_source": "yaml",
                    "params_effective": {param_name: value},
                    "git_sha": git_info.sha,
                    "reproducible_from_sha": git_info.is_clean,
                    "data_hashes": {},
                    "cache_mode": "none",
                    "guard_passed": True,
                },
                contribution=1,
            )
            trial_ids.append(tid)
            ledger.seal(tid, seal_path=f"runs/{tid}/metrics.seal")
            ledger.consume(
                tid,
                outcome={
                    "expectancy": None,
                    "sharpe": None,
                    "n_trades": None,
                    "max_single_loss_ratio": None,
                },
                verdict="KEPT",
                rejection_reason=note,
                retest_forbidden=True,
            )
    except BudgetExhaustedError as exc:
        print(f"🛑 Hết ngân sách B0: {exc}")
        return EXIT_BUDGET_EXHAUSTED

    POOL_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    POOL_OUTPUT_PATH.write_text(
        yaml.dump(
            {
                "committed_at_git_sha": git_info.sha,
                "criteria": {
                    "volume_24h_usdt_min": VOLUME_FLOOR_USDT,
                    "listing_age_days_min": AGE_FLOOR_DAYS,
                },
                "trading": list(result.trading),
                "explore": list(result.explore),
                "b0_trial_ids": trial_ids,
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    print(f"\n✅ Đã ghi {POOL_OUTPUT_PATH}, tiêu {len(trial_ids)} trial B0: {trial_ids}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
