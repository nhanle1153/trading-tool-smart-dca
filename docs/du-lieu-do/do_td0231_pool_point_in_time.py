"""TD-0231 — dựng lại POOL ĐÚNG TẠI `T0`/`T1`/`T2`. **0 trial.**

🔴 **Câu hỏi:** `config/pool.yaml` nhận mã có volume 24h ≥ 15tr USDT **đo tại
thời điểm chốt pool (09/2026)**. Một mã đủ ngưỡng giữa 2025 mà nay dưới ngưỡng
là một mã **đã suy giảm** — loại nó ra làm `expectancy` **đẹp lên**. Đó là lệch
sống sót đi qua cửa *tiêu chí lọc* thay vì cửa *huỷ niêm yết*, và là **kênh duy
nhất còn chưa đo** của `MT-34` (`TD-0230` đã đo hai kênh kia).

🔑 **Kịch bản này KHÔNG viết lại logic pool.** Nó là **người gọi** mà docstring
`src/tool_d/pool.py:112` đòi và chưa từng tồn tại:

    🔴 `stat.quote_volume_24h` PHẢI là volume TẠI thời điểm `t` (người gọi tự
    cung cấp từ dữ liệu lịch sử) — hàm này không tự suy volume.

Nó cấp đúng thứ đó rồi gọi `pairlist_point_in_time()` và `pairlist_over_time()`
đã có sẵn + đã có test đơn vị.

🔴 **Vì sao 0 trial và không vướng `MT-19`:** ứng viên là mã **KHÔNG thuộc pool**;
nguồn là kho tĩnh `data.binance.vision` (metadata + nến lịch sử của SÀN). `MT-19`
chặn phép đo mô tả trên *dữ liệu pool*. `DR-014 §2` chỉ tính *đánh giá cấu hình*.

🔴 **RANH GIỚI — đọc trước khi dùng số:**

- **Trung thành tiêu chí gốc:** `compute_pool()` so `quote_volume_24h` của ticker
  24h = **một ngày**. Nên ở đây lấy `quote_volume` của **đúng ngày `t`**, KHÔNG
  đổi sang trung vị 30 ngày. Đổi là phát minh một tiêu chí mới rồi so nó với một
  pool dựng bằng tiêu chí cũ — hai bên khác tiêu chí thì hiệu không mang nghĩa
  (đúng lỗi vừa bắt được ở con số 219 của `DR-D1-01`).
- **Tuổi niêm yết:** `TD-0230` chỉ cho **tháng** đầu. Ca nào `|tuổi − 180| ≤ 31`
  ngày thì tải thêm file tháng đầu để lấy **ngày** chính xác; ca nào cách xa
  ngưỡng thì dùng mốc tháng. Artifact ghi rõ mã nào dùng mốc **chính xác**, mã
  nào dùng **xấp xỉ** — không gộp hai loại.
- **Không đo được ≠ trượt tiêu chí** (N6): 404, hoặc file tháng có nhưng không có
  hàng của đúng ngày `t`, vào ô riêng. 🔴 Gộp chúng vào *"trượt tiêu chí"* là
  lệch đúng chiều làm rổ **trông đúng hơn thực tế**.

🔴 **KHÔNG sửa `config/pool.yaml`, và không đề xuất sửa.** `build_pool.py` **từ
chối ghi đè** có chủ đích (spec `:350-352`: không được chọn lại pool sau khi đã
thấy kết quả); spec `:4338`: đổi pool ⇒ backfill lại toàn bộ + **mọi số cũ không
so sánh được**. Sửa pool là quyết định của chủ dự án.

Chạy (N7 — bằng chứng phải từ Docker; service `freqtrade` vì entrypoint là
`python`, **không** service `tests` vốn có entrypoint `pytest`):

    docker compose -f docker/docker-compose.yml run --rm freqtrade \
        docs/du-lieu-do/do_td0231_pool_point_in_time.py
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import yaml

from tool_d.api_client.binance_public import (
    KhoLuuTruError,
    NenThangKhongCoError,
    doc_quote_volume_1d_thang,
)
from tool_d.config.loader import load_tool_d_config, resolve
from tool_d.pool import SymbolStat, pairlist_over_time, pairlist_point_in_time

REPO = Path(__file__).resolve().parents[2]
POOL_YAML = REPO / "config" / "pool.yaml"
NGUON_TD0230 = REPO / "docs" / "du-lieu-do" / "td0230-lech-song-sot-pool.json"
KET_QUA = REPO / "docs" / "du-lieu-do" / "td0231-pool-point-in-time.json"

# ✅ DR-D0PRE-05 — cùng hai hằng `entrypoints/build_pool.py:31-32` đã dùng để
# chốt `config/pool.yaml`. Trích lại ở đây để phép so là so CÙNG tiêu chí.
AGE_FLOOR_DAYS = 180
VOLUME_FLOOR_USDT = 15_000_000.0

# Ca "sát ngưỡng tuổi" thì mốc THÁNG không đủ phân giải ⇒ tải thêm file tháng
# đầu để lấy NGÀY chính xác. 31 = biên tối đa của một tháng.
BIEN_SAT_NGUONG_NGAY = 31

RANH_GIOI = (
    "Trung thanh tieu chi goc: compute_pool() so quote_volume_24h cua ticker 24h = MOT "
    "NGAY, nen day lay quote_volume cua DUNG NGAY t, KHONG doi sang trung vi 30 ngay "
    "(doi la phat minh mot tieu chi moi roi so voi pool dung bang tieu chi cu). "
    "Tuoi niem yet: TD-0230 chi cho THANG dau; ca nao |tuoi - 180| <= 31 ngay thi tai "
    "them file thang dau de lay NGAY chinh xac, ca khac dung moc thang — artifact ghi "
    "ro ma nao chinh xac, ma nao xap xi, KHONG gop. KHONG DO DUOC != TRUOT TIEU CHI "
    "(N6): 404 hoac file thang co nhung khong co hang cua dung ngay t deu vao o rieng; "
    "gop chung vao 'truot tieu chi' la lech dung chieu lam ro TRONG DUNG HON thuc te. "
    "KHONG sua config/pool.yaml va khong de xuat sua."
)

CACH_DOC = (
    "Viet TRUOC khi chay (khuon DR-D4-08 §6). K = ma THUOC pool dung tai T1 ma "
    "config/pool.yaml KHONG co; M = ma trong pool.yaml KHONG thuoc pool dung tai T1. "
    "K/|pool_T1| <= ~10% => ro lech nho, duong B (chay D4 + khai d4_han_che) CO CAN CU, "
    "va do la mot DU KIEN khong phai hy vong. K lon => WFO dang do SAI RO theo chieu "
    "PASS, phai xu truoc khi tieu suat B2 — spec :4338 se vo hieu hoa ket luan neu pool "
    "doi sau. Du K bang bao nhieu cung KHONG tu doi config/pool.yaml: do la quyet dinh "
    "cua chu du an, co gia rieng (backfill lai toan bo). "
    "⚠️ Moc T0 co gia tri THAP hon T1 cho cau hoi D4: moi bang chung D4 mang timerange "
    "20250612-20260129 (DR-D4-09:23 'khong phai toan bo [T0,T2]') va du lieu 5m chi ton "
    "tai cho [T1,T2] (TD-0200) => lech trong CALIB khong chay vao phan quyet Z0-T1."
)


@dataclass(frozen=True)
class KetQuaMoc:
    moc: date
    ung_vien_song: int
    do_duoc: int
    khong_do_duoc_404: tuple[str, ...]
    khong_do_duoc_thieu_ngay: tuple[str, ...]
    onboard_chinh_xac: tuple[str, ...]
    onboard_xap_xi: int
    pool_dung: tuple[str, ...]
    explore_dung: tuple[str, ...]


def _moc_phan_vung() -> dict[str, date]:
    cfg = load_tool_d_config(REPO / "config" / "tool_d_config.yaml")
    tho = resolve(cfg, "tier_c.data_split")
    return {k: date.fromisoformat(str(v)) for k, v in tho.items()}


def _pool_hien_tai() -> tuple[str, ...]:
    return tuple(yaml.safe_load(POOL_YAML.read_text(encoding="utf-8"))["trading"])


def _khoang_td0230() -> dict[str, dict]:
    d = json.loads(NGUON_TD0230.read_text(encoding="utf-8"))
    return d["khoang_ton_tai"]


def _thang_so(s: str) -> int:
    y, m = s.split("-")
    return int(y) * 12 + int(m)


def _thang_cua(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def _dau_thang(s: str) -> date:
    y, m = s.split("-")
    return date(int(y), int(m), 1)


def _cuoi_thang(s: str) -> date:
    y, m = (int(x) for x in s.split("-"))
    return date(y + (m == 12), (m % 12) + 1, 1) - timedelta(days=1)


def _ngay_onboard_chinh_xac(symbol: str, thang_dau: str) -> date | None:
    """Ngày nến ĐẦU TIÊN thật, đọc từ file tháng đầu. `None` = không đọc được."""
    y, m = (int(x) for x in thang_dau.split("-"))
    try:
        return min(doc_quote_volume_1d_thang(symbol=symbol, nam=y, thang=m))
    except (NenThangKhongCoError, KhoLuuTruError):
        return None


def _dung_mot_moc(
    moc: date, khoang: dict[str, dict], *, im_lang: bool = False, max_ma: int = 0
) -> KetQuaMoc:
    thang_moc = _thang_cua(moc)
    song: list[str] = []
    for sym, k in khoang.items():
        if not k["thang_dau"] or not k["thang_cuoi"]:
            continue
        if _thang_so(k["thang_dau"]) <= _thang_so(thang_moc) <= _thang_so(k["thang_cuoi"]):
            song.append(sym)
    song.sort()
    if max_ma > 0:
        song = song[:max_ma]
        print(f"    ⚠️ CHẠY THỬ — chỉ {len(song)} mã, KHÔNG phải bằng chứng")

    stats: list[SymbolStat] = []
    ko_404: list[str] = []
    ko_thieu_ngay: list[str] = []
    ob_chinh_xac: list[str] = []
    ob_xap_xi = 0
    bat_dau = time.monotonic()

    for i, sym in enumerate(song, 1):
        k = khoang[sym]
        try:
            vol_thang = doc_quote_volume_1d_thang(
                symbol=sym, nam=moc.year, thang=moc.month
            )
        except NenThangKhongCoError:
            ko_404.append(sym)
            continue
        if moc not in vol_thang:
            # File tháng CÓ nhưng không có hàng của đúng ngày `moc` ⇒ ngày đó
            # mã không giao dịch. Là DỮ KIỆN, nhưng không phải "trượt tiêu
            # chí" — ghi riêng (N6).
            ko_thieu_ngay.append(sym)
            continue

        # Tuổi: mốc THÁNG trước, chỉ tải thêm khi SÁT ngưỡng.
        onboard = _dau_thang(k["thang_dau"])
        tuoi_xap_xi = (moc - onboard).days
        if abs(tuoi_xap_xi - AGE_FLOOR_DAYS) <= BIEN_SAT_NGUONG_NGAY:
            that = _ngay_onboard_chinh_xac(sym, k["thang_dau"])
            if that is not None:
                onboard = that
                ob_chinh_xac.append(sym)
            else:
                ob_xap_xi += 1
        else:
            ob_xap_xi += 1

        delisted = (
            None
            if k["thang_cuoi"] == max(
                v["thang_cuoi"] for v in khoang.values() if v["thang_cuoi"]
            )
            else _cuoi_thang(k["thang_cuoi"])
        )
        stats.append(
            SymbolStat(
                symbol=sym,
                onboard_date=datetime.combine(onboard, datetime.min.time(), tzinfo=timezone.utc),
                quote_volume_24h=vol_thang[moc],
                delisted_at=(
                    datetime.combine(delisted, datetime.min.time(), tzinfo=timezone.utc)
                    if delisted
                    else None
                ),
            )
        )
        if not im_lang and (i % 100 == 0 or i == len(song)):
            print(f"    {i}/{len(song)}  ({time.monotonic() - bat_dau:.0f}s)")

    kq = pairlist_point_in_time(
        stats,
        t=datetime.combine(moc, datetime.min.time(), tzinfo=timezone.utc),
        age_floor_days=AGE_FLOOR_DAYS,
        volume_floor_usdt=VOLUME_FLOOR_USDT,
    )
    return KetQuaMoc(
        moc=moc,
        ung_vien_song=len(song),
        do_duoc=len(stats),
        khong_do_duoc_404=tuple(ko_404),
        khong_do_duoc_thieu_ngay=tuple(ko_thieu_ngay),
        onboard_chinh_xac=tuple(ob_chinh_xac),
        onboard_xap_xi=ob_xap_xi,
        pool_dung=kq.trading,
        explore_dung=kq.explore,
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--moc",
        default="t1",
        help="danh sách mốc cách nhau bởi dấu phẩy: t0,t1,t2. Mặc định `t1` — "
        "mốc DUY NHẤT chạy vào phán quyết D4",
    )
    ap.add_argument(
        "--max-ma",
        type=int,
        default=0,
        help="0 = đo hết. >0 = chạy thử trên N mã đầu (KHÔNG dùng làm bằng chứng)",
    )
    ap.add_argument("--ket-qua", type=Path, default=KET_QUA)
    args = ap.parse_args(argv)

    moc_all = _moc_phan_vung()
    ten_moc = [x.strip() for x in args.moc.split(",") if x.strip()]
    for t in ten_moc:
        if t not in moc_all:
            raise SystemExit(f"mốc {t!r} không có trong tier_c.data_split")

    pool = _pool_hien_tai()
    khoang = _khoang_td0230()
    print(f"pool hiện tại: {len(pool)} mã · ứng viên từ TD-0230: {len(khoang)} mã")
    print(f"mốc sẽ dựng: {', '.join(f'{t}={moc_all[t]}' for t in ten_moc)}")

    ket: dict[str, KetQuaMoc] = {}
    for t in ten_moc:
        print(f"\n=== dựng pool đúng tại {t} = {moc_all[t]} ===")
        ket[t] = _dung_mot_moc(moc_all[t], khoang, max_ma=args.max_ma)
        r = ket[t]
        print(
            f"  sống tại {t}: {r.ung_vien_song} · đo được: {r.do_duoc} · "
            f"404: {len(r.khong_do_duoc_404)} · thiếu ngày: "
            f"{len(r.khong_do_duoc_thieu_ngay)} · pool đúng: {len(r.pool_dung)}"
        )

    bang: dict[str, object] = {
        "nguon": "TD-0231, 13/09/2026 — dựng lại POOL ĐÚNG TẠI mốc quá khứ bằng "
        "pairlist_point_in_time() đã có sẵn. Volume tại t đọc từ nến 1d monthly của "
        "kho data.binance.vision. 0 trial, ứng viên KHÔNG thuộc pool.",
        "ranh_gioi": RANH_GIOI,
        "cach_doc": CACH_DOC,
        "trial": 0,
        "tieu_chi": {
            "age_floor_days": AGE_FLOOR_DAYS,
            "volume_floor_usdt": VOLUME_FLOOR_USDT,
            "_doc": "cùng hai hằng build_pool.py:31-32 đã dùng để chốt config/pool.yaml",
        },
        "moc": {t: moc_all[t].isoformat() for t in ten_moc},
        "pool_hien_tai": {"n": len(pool), "danh_sach": sorted(pool)},
    }

    for t, r in ket.items():
        dung = set(r.pool_dung)
        hien = set(pool)
        K = sorted(dung - hien)
        M = sorted(hien - dung)
        bang[f"pool_dung_tai_{t}"] = {
            "n": len(r.pool_dung),
            "ung_vien_song": r.ung_vien_song,
            "do_duoc": r.do_duoc,
            "khong_do_duoc_404": {
                "n": len(r.khong_do_duoc_404),
                "danh_sach": sorted(r.khong_do_duoc_404),
            },
            "khong_do_duoc_thieu_ngay": {
                "n": len(r.khong_do_duoc_thieu_ngay),
                "danh_sach": sorted(r.khong_do_duoc_thieu_ngay),
            },
            "onboard_moc_chinh_xac": {
                "n": len(r.onboard_chinh_xac),
                "danh_sach": sorted(r.onboard_chinh_xac),
            },
            "onboard_moc_xap_xi_theo_thang": r.onboard_xap_xi,
            "danh_sach": sorted(r.pool_dung),
            "K_thuoc_pool_dung_ma_pool_yaml_KHONG_co": {
                "n": len(K),
                "ty_le_tren_pool_dung": (
                    round(len(K) / len(r.pool_dung), 4) if r.pool_dung else None
                ),
                "danh_sach": K,
            },
            "M_trong_pool_yaml_ma_KHONG_thuoc_pool_dung": {
                "n": len(M),
                "ty_le_tren_pool_yaml": round(len(M) / len(pool), 4),
                "danh_sach": M,
            },
        }

    # §9c.4b — "mã EXPLORE thì KHÔNG BAO GIỜ được vào pool giao dịch sau này".
    # Chạy trên đường THẬT lần đầu (trước nay chỉ có test đơn vị dựng tay).
    if len(ket) >= 2:
        theo_moc = {
            datetime.combine(moc_all[t], datetime.min.time(), tzinfo=timezone.utc): [
                SymbolStat(
                    symbol=s,
                    onboard_date=datetime(2000, 1, 1, tzinfo=timezone.utc),
                    quote_volume_24h=VOLUME_FLOOR_USDT * 2,
                )
                for s in ket[t].pool_dung
            ]
            for t in ten_moc
        }
        qua_thoi_gian = pairlist_over_time(
            theo_moc,
            age_floor_days=AGE_FLOOR_DAYS,
            volume_floor_usdt=VOLUME_FLOOR_USDT,
        )
        bang["rang_buoc_9c4b_explore_khong_vao_lai"] = {
            "_doc": "pairlist_over_time() trên đường chạy THẬT (trước nay chỉ có test "
            "đơn vị dựng tay). Mỗi mốc nạp chính tập pool đúng của mốc đó; mã từng "
            "rơi vào explore ở mốc sớm phải bị khoá khỏi trading ở mọi mốc SAU.",
            "theo_moc": {
                k.date().isoformat(): {
                    "trading": len(v.trading),
                    "explore": len(v.explore),
                }
                for k, v in sorted(qua_thoi_gian.items())
            },
        }

    args.ket_qua.write_text(
        json.dumps(bang, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"\nđã ghi {args.ket_qua}")
    for t in ten_moc:
        b = bang[f"pool_dung_tai_{t}"]
        print(
            f"  {t}: pool đúng {b['n']} mã · "
            f"K = {b['K_thuoc_pool_dung_ma_pool_yaml_KHONG_co']['n']} "
            f"({b['K_thuoc_pool_dung_ma_pool_yaml_KHONG_co']['ty_le_tren_pool_dung']}) · "
            f"M = {b['M_trong_pool_yaml_ma_KHONG_thuoc_pool_dung']['n']}"
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KhoLuuTruError as exc:
        # N6 — fail-closed. KHÔNG ghi một artifact nửa vời: một con số "rổ
        # lệch ít hơn" là lệch đúng theo chiều PASS.
        print(f"DỪNG, không ghi kết quả: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
