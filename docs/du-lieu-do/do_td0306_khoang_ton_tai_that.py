"""TD-0306 — đo lại ĐỜI SỐNG THẬT của các mã rổ `T2`, giải `MT-59`. **0 trial.**

🔴 **Câu hỏi:** `khoang_ton_tai` của `TD-0230` suy "còn sống" từ SỰ CÓ MẶT file
nến tháng, mà kho `data.binance.vision` vẫn sinh nến giá thanh toán `volume = 0`
nhiều tháng sau khi sàn ngừng giao dịch. Với rổ `T2` (94 mã, `TD-0231`
`pool_dung_tai_t2.danh_sach`): mã nào thật ra đã chết TRƯỚC `T2` (lọt rổ chỉ vì
`MT-59`), mã nào chết GIỮA `[T2, T3]` (đầu vào cắt dữ liệu của `TD-0308`)?

Cách đo (`DR-LOCKBOX-01` Q3 bước 1 + iv + v + vi):
- Chỉ 94 mã lọt rổ, khoảng tồn tại cũ làm CẬN TRÊN (sai lệch của kho chỉ một
  chiều: kéo đời sống dài ra), không đo cả 864 mã.
- Mỗi mã đọc nến 1h futures của kho, từ `thang_cuoi` cũ LÙI dần cho tới tháng đầu
  tiên có `volume > 0`; phân loại bằng `tool_d.data.doi_song_ma`, vốn dùng lại
  `moc_ngung_giao_dich()` (`DR-D1-03` §5) — không viết khuôn đo mới.
- Nguồn ĐỘC LẬP thứ hai: `exchangeInfo` hôm nay. Kho nói chết mà sàn nói còn giao
  dịch ⇒ mâu thuẫn ⇒ KHÔNG GHI artifact.

🔴 **Vì sao 0 trial và không ghi dòng `CTRL`:** chỉ đọc kho công khai (metadata
SÀN) và `exchangeInfo`, không đọc một nến nào của thư mục pool hay lockbox, không
đánh giá cấu hình nào — cùng đường `TD-0230`/`0231`/`0247`/`0301`.
`CTRL_OUTPUT_ALLOWED` (`registry.py`) chỉ nhận 3 trường, artifact này không có
trường nào ⇒ ghi `CTRL` là khai sai sự thật.

🔴 **Không sửa `td0230` / `td0247`** — bằng chứng đã commit. Artifact MỚI.

Chạy (N7 — bằng chứng phải từ Docker; service `freqtrade`):

    docker compose -f docker/docker-compose.yml run --rm freqtrade \\
        docs/du-lieu-do/do_td0306_khoang_ton_tai_that.py [--thu N]

`--thu N`: chỉ đo N mã đầu, in kết quả, KHÔNG ghi artifact (kiểm đường mạng).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

from tool_d.api_client.binance_public import (
    KhoLuuTruError,
    NenThangKhongCoError,
    doc_csv_thang_kho,
    get_exchange_info,
)
from tool_d.config.loader import load_tool_d_config, resolve
from tool_d.data.doi_song_ma import (
    CHET_TRONG_T2_T3,
    CHET_TRUOC_T2,
    KHONG_DO_DUOC,
    KetQuaDoiSong,
    MauThuanNguonError,
    doi_chieu_exchange_info,
    khoang_ton_tai_moi,
    nghi_merge,
    phan_loai_doi_song,
)
from tool_d.data.kho_luu_tru import nen_tu_kho

REPO = Path(__file__).resolve().parents[2]
TD0230 = REPO / "docs/du-lieu-do/td0230-lech-song-sot-pool.json"
TD0231 = REPO / "docs/du-lieu-do/td0231-pool-point-in-time.json"
OUT = REPO / "docs/du-lieu-do/td0306-khoang-ton-tai-that.json"

#: `DR-LOCKBOX-01` §5 — kỳ vọng nền số mã rổ T2 chết thật trong [T2,T3]; là CẬN DƯỚI
#: (đoạn này BTC −53%). 0 mã ⇒ P ≈ 4% ⇒ đáng nghi phép đo trước.
KY_VONG_CHET_TRONG = (3.1, 3.4)


def _thang(s: str) -> tuple[int, int]:
    y, m = s.split("-")
    return int(y), int(m)


def _thang_truoc(y: int, m: int) -> tuple[int, int]:
    return (y - 1, 12) if m == 1 else (y, m - 1)


def _dau_thang_sau(s: str) -> date:
    y, m = _thang(s)
    return date(y + (m == 12), m % 12 + 1, 1)


def _git_sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "khong_doc_duoc"


#: Mã mà con số phụ thuộc vào. Bẩn ⇒ `git_sha` ghi vào artifact trỏ tới một commit
#: KHÔNG chứa mã đã sinh ra số — đúng lỗi cổng D1/D2/D3 (`CLAUDE.md`, *"ghi `git_sha` mà
#: không cổng nào kiểm cây sạch"*), và lần chạy đầu của chính kịch bản này đã dính.
DUONG_PHU_THUOC = ("src/", "config/", "docs/du-lieu-do/do_td0306_khoang_ton_tai_that.py")


def _cay_ban() -> list[str]:
    """Dòng `git status --porcelain` trên phần mã con số phụ thuộc. Không đọc được git ⇒
    coi là bẩn (fail-closed): không chứng minh được xuất xứ thì không ghi."""
    try:
        ra = subprocess.run(
            ["git", "status", "--porcelain", "--", *DUONG_PHU_THUOC],
            cwd=REPO, capture_output=True, text=True, check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        return [f"không đọc được git status: {exc}"]
    return [d for d in ra.splitlines() if d.strip()]


def do_mot_ma(sym: str, k: dict, *, t2: date, t3: date) -> tuple[KetQuaDoiSong | None, str | None, int]:
    """(kết quả, lý do không đo được, số file tháng đã đọc)."""
    thang_dau = _thang(k["thang_dau"])
    y, m = _thang(k["thang_cuoi"])
    phan: list[pd.DataFrame] = []
    while True:
        try:
            hang = doc_csv_thang_kho(loai="klines", symbol=sym, nam=y, thang=m, khung="1h")
        except NenThangKhongCoError as exc:
            return None, f"kho thiếu tháng {y:04d}-{m:02d} giữa khoảng tồn tại: {exc}", len(phan)
        nen = nen_tu_kho(hang, la_mark=False)
        phan.append(nen)
        if (nen["volume"] > 0).any():
            break
        if (y, m) <= thang_dau:
            return None, "không tháng nào trong khoảng tồn tại có volume > 0", len(phan)
        y, m = _thang_truoc(y, m)
    nen_du = pd.concat(phan).sort_values("date", kind="stable").reset_index(drop=True)
    kq = phan_loai_doi_song(nen_du, t2=t2, t3=t3, het_kho=_dau_thang_sau(k["thang_cuoi"]))
    return kq, None, len(phan)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--thu", type=int, default=None, help="chỉ đo N mã đầu, KHÔNG ghi artifact")
    args = ap.parse_args(argv)

    ghi = args.thu is None
    if ghi and OUT.exists():
        print(f"🛑 {OUT.relative_to(REPO)} đã tồn tại — artifact là bằng chứng, không ghi đè.")
        return 2
    if ghi:
        ban = _cay_ban()
        if ban:
            print("🛑 Cây bẩn ở phần mã con số phụ thuộc — git_sha sẽ không chứa mã đã sinh ra số. Commit trước:")
            for d in ban:
                print(f"  {d}")
            return 6

    cfg = load_tool_d_config()
    moc = resolve(cfg, "tier_c.data_split")
    t2, t3 = date.fromisoformat(moc["t2"]), date.fromisoformat(moc["t3"])

    khoang_cu: dict = json.loads(TD0230.read_text(encoding="utf-8"))["khoang_ton_tai"]
    ro: list[str] = json.loads(TD0231.read_text(encoding="utf-8"))["pool_dung_tai_t2"]["danh_sach"]
    if args.thu is not None:
        ro = ro[: args.thu]
    thieu = [s for s in ro if s not in khoang_cu]
    if thieu:
        print(f"🛑 {len(thieu)} mã rổ T2 không có trong khoang_ton_tai của TD-0230: {thieu}")
        return 3

    luc_ei = datetime.now(timezone.utc)
    ei = get_exchange_info()
    dang_gd = {
        s["symbol"]
        for s in ei["symbols"]
        if s.get("status") == "TRADING" and s.get("contractType") == "PERPETUAL" and s.get("quoteAsset") == "USDT"
    }
    print(f"exchangeInfo {luc_ei.isoformat(timespec='seconds')}: {len(dang_gd)} hợp đồng USDT vĩnh cửu đang TRADING")

    do_that: dict[str, tuple[str, pd.Timestamp | None]] = {}
    chi_tiet: dict[str, dict] = {}
    mau_thuan: list[str] = []
    so_file = 0
    for i, sym in enumerate(ro, 1):
        try:
            kq, ly_do, n = do_mot_ma(sym, khoang_cu[sym], t2=t2, t3=t3)
        except KhoLuuTruError as exc:
            # Lỗi mạng/zip — không phải dữ kiện. Fail-closed: dừng, không ghi nửa chừng.
            print(f"🛑 {sym}: lỗi đọc kho — {exc}")
            return 4
        so_file += n
        gd = sym in dang_gd
        if kq is None:
            do_that[sym] = (KHONG_DO_DUOC, None)
            chi_tiet[sym] = {"trang_thai": KHONG_DO_DUOC, "ly_do": ly_do, "dang_giao_dich_hom_nay": gd, "so_file": n}
        else:
            try:
                cuoi = doi_chieu_exchange_info(kq, dang_giao_dich_hom_nay=gd, symbol=sym)
            except MauThuanNguonError as exc:
                mau_thuan.append(str(exc))
                cuoi = kq.trang_thai
            do_that[sym] = (cuoi, kq.moc_ngung)
            chi_tiet[sym] = {
                "trang_thai_kho": kq.trang_thai,
                "trang_thai": cuoi,
                "moc_ngung": kq.moc_ngung.isoformat() if kq.moc_ngung is not None else None,
                "dang_giao_dich_hom_nay": gd,
                "so_file": n,
            }
        print(f"[{i:>3}/{len(ro)}] {sym:<18} {do_that[sym][0]:<17} {chi_tiet[sym].get('moc_ngung') or ''}")

    if mau_thuan:
        print(f"\n🛑 {len(mau_thuan)} MÂU THUẪN giữa kho và exchangeInfo — KHÔNG ghi artifact, cần người xem:")
        for x in mau_thuan:
            print(f"  - {x}")
        return 5

    chet_truoc = sorted(s for s, (tt, _) in do_that.items() if tt == CHET_TRUOC_T2)
    ngung_trong = {s: ng for s, (tt, ng) in do_that.items() if tt == CHET_TRONG_T2_T3 and ng is not None}
    merge = nghi_merge(ngung_trong)
    khong_do = sorted(s for s, (tt, _) in do_that.items() if tt == KHONG_DO_DUOC)
    khoang_moi = khoang_ton_tai_moi(khoang_cu, do_that)
    lech = {
        s: {"thang_cuoi_td0230": khoang_cu[s]["thang_cuoi"], "thang_cuoi_that": khoang_moi[s]["thang_cuoi"]}
        for s in do_that
        if khoang_moi[s]["thang_cuoi"] != khoang_cu[s]["thang_cuoi"]
    }

    canh_bao: list[str] = []
    if not ngung_trong:
        canh_bao.append(
            "0 mã rổ T2 chết trong [T2,T3] — kỳ vọng nền ~3,1–3,4 (cận dưới), P(0) ≈ 4%. "
            "ĐÁNG NGHI phép đo trước: phải đối chiếu ít nhất một mã cụ thể đã biết còn giao dịch tới T3 "
            "trước khi nhận kết quả này (DR-LOCKBOX-01 §5)."
        )
    if khong_do:
        canh_bao.append(f"{len(khong_do)} mã KHÔNG ĐO ĐƯỢC (N6) — không gộp vào 'sống': {khong_do}")

    print("\n=== TÓM TẮT ===")
    print(f"đo {len(do_that)} mã · {so_file} file tháng · 0 trial")
    print(f"MT-59 làm lệch pool_dung tại T2 (chết TRƯỚC T2 mà vẫn lọt rổ): {len(chet_truoc)} {chet_truoc}")
    print(f"chết TRONG [T2,T3]: {len(ngung_trong)} {sorted(ngung_trong)} · kỳ vọng nền {KY_VONG_CHET_TRONG}")
    print(f"nghi merge (ngừng cùng giờ): {merge or 'không'}")
    print(f"không đo được: {len(khong_do)} {khong_do}")
    for c in canh_bao:
        print(f"⚠️ {c}")

    if not ghi:
        print("\n(--thu: KHÔNG ghi artifact)")
        return 0

    artifact = {
        "nguon": (
            "TD-0306 / DR-LOCKBOX-01 Q3 bước 1 + iv + v + vi — đời sống THẬT của 94 mã rổ T2 "
            "(TD-0231 pool_dung_tai_t2.danh_sach): nến 1h futures của kho data.binance.vision, lùi từ "
            "thang_cuoi của TD-0230 tới tháng đầu có volume > 0; phân loại bằng tool_d.data.doi_song_ma "
            "(dùng lại moc_ngung_giao_dich, DR-D1-03 §5); đối chiếu exchangeInfo làm nguồn độc lập. 0 trial."
        ),
        "ranh_gioi": [
            "Chỉ đo 94 mã lọt rổ T2; 770 mã còn lại trong khoang_ton_tai giữ số TD-0230 làm CẬN TRÊN, "
            "nhãn nguon_thang_cuoi = can_tren_td0230 — không phải số đo.",
            "Kho tháng tới hết 08/2026; khoảng từ hết kho tới T3 không nhìn thấy từ kho. Mã sống tới hết kho "
            "chỉ được nâng thành song_toi_t3 khi exchangeInfo hôm nay còn TRADING; ngược lại là khong_do_duoc.",
            "exchangeInfo đọc tại luc_exchange_info. Một mã bị huỷ rồi niêm yết lại giữa [T2, hôm nay] "
            "sẽ hiện là mâu thuẫn và làm dừng phép đo — không bị gộp im lặng.",
            "nghi_merge chỉ là dấu hiệu (ngừng cùng giờ), không phải phán quyết chết-thật/rebrand.",
        ],
        "git_sha": _git_sha(),
        "chay_luc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "luc_exchange_info": luc_ei.isoformat(timespec="seconds"),
        "moc": {"t2": moc["t2"], "t3": moc["t3"]},
        "trial": 0,
        "so_ma_do": len(do_that),
        "so_file_thang": so_file,
        "mt59_lech_pool_dung_tai_t2": chet_truoc,
        "chet_trong_t2_t3": {
            s: {"moc_ngung": ng.isoformat(), "nghi_merge_voi": merge.get(s, [])} for s, ng in sorted(ngung_trong.items())
        },
        "ky_vong_nen_chet_trong_t2_t3": list(KY_VONG_CHET_TRONG),
        "khong_do_duoc": khong_do,
        "canh_bao": canh_bao,
        "doi_chieu_td0230": lech,
        "chi_tiet_94_ma": chi_tiet,
        "khoang_ton_tai": khoang_moi,
    }
    OUT.write_text(json.dumps(artifact, ensure_ascii=False, indent=1, sort_keys=False) + "\n", encoding="utf-8", newline="\n")
    print(f"\n✅ ghi {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
