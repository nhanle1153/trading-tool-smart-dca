"""TD-0230 — đo ĐỘ LỆCH SỐNG SÓT của `config/pool.yaml`. **0 trial.**

🔴 **Câu hỏi:** `config/pool.yaml` (102 mã) được chốt bằng `compute_pool()`
(`entrypoints/build_pool.py:226`) — tức tiêu chí đo tại **thời điểm chốt
(09/2026)** — rồi sắp được dùng để backtest **[T0, T2] = 04/2024 →
01/2026**. Rổ đó lệch bao nhiêu so với rổ ĐÚNG tại quá khứ?

🔴 **Vì sao 0 trial và không vướng `MT-19`:** phép đo này **không đọc một
nến pool nào**. Nó liệt kê kho tĩnh `data.binance.vision` — **metadata của
SÀN**, cùng đường `DR-D1-01` §1-2 đã đi thật khi tìm 219 mã đã huỷ niêm
yết. `MT-19` chặn phép đo mô tả trên *dữ liệu pool*; đây không phải.

🔴 **RANH GIỚI — đọc trước khi dùng số:** con số (2)/(3) là **CẬN TRÊN**.
Chúng lọc theo **khoảng tồn tại** của mã, **chưa** áp tiêu chí volume
≥ 15tr USDT tại `t` (volume lịch sử cần tải nến thật, mà với mã pool thì
việc đó **chặn cứng ở `MT-19`**). Nên kết quả trả lời *"rổ có thể thiếu
TỐI ĐA bao nhiêu mã"*, **KHÔNG** trả lời *"pool đúng tại `T1` gồm những
mã nào"*. Lẫn hai câu là đọc quá tay.

⚠️ **Độ phân giải THÁNG.** Ta đọc nhánh `monthly/` (≈12 khoá/năm) thay vì
`daily/` (≈365) để một lượt liệt kê là đủ. Hệ quả: mã lên/rời sàn **giữa
tháng** không phân giải được — những ca đó vào ô riêng
`cung_thang_khong_phan_giai_duoc`, **không** bị gộp vào một bên nào (N6:
không đo được thì nói không đo được).

🔴 **Kịch bản này KHÔNG sửa `config/pool.yaml`** và không đề xuất sửa.
`build_pool.py` **từ chối ghi đè** file đó có chủ đích (spec `:350-352`:
không được chọn lại pool sau khi đã thấy kết quả). Sửa pool là quyết định
của chủ dự án, có giá riêng (spec `:4338` — backfill lại toàn bộ, **mọi số
cũ không so sánh được**).

Chạy (N7 — bằng chứng phải từ Docker; service `freqtrade` vì entrypoint là
`python`, **không** service `tests` vốn có entrypoint `pytest`):

    docker compose -f docker/docker-compose.yml run --rm freqtrade \
        docs/du-lieu-do/do_td0230_lech_song_sot_pool.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass, asdict
from datetime import date
from pathlib import Path

import yaml

from tool_d.api_client.binance_public import (
    KhoLuuTruError,
    get_exchange_info,
    liet_ke_kho_luu_tru,
)
from tool_d.config.loader import load_tool_d_config, resolve
from tool_d.pool import EXCLUDE_FROM_TRADING

REPO = Path(__file__).resolve().parents[2]
POOL_YAML = REPO / "config" / "pool.yaml"
KET_QUA = REPO / "docs" / "du-lieu-do" / "td0230-lech-song-sot-pool.json"

GOC_KHO = "data/futures/um/monthly/klines/"

# Mốc phân vùng — ✅ DR-D0PRE-07, niêm phong. Đọc từ YAML để không có hai
# nguồn sự thật (N1/N4); hằng ở đây chỉ là tên khoá.
KHOA_MOC = "tier_c.data_split"

# `BTCUSDT_210326` — hợp đồng KỲ HẠN, Tool D chỉ giao dịch PERPETUAL.
_RE_KY_HAN = re.compile(r"_\d{6}$")
# `BTCUSDT-1d-2024-04.zip` → nhóm 1 = "2024-04"
_RE_THANG = re.compile(r"-1d-(\d{4}-\d{2})\.zip$")


@dataclass(frozen=True)
class KhoangTonTai:
    """Khoảng tồn tại của một mã, đo từ kho lưu trữ. `None` = KHÔNG ĐO
    ĐƯỢC (không có nhánh `monthly/1d`), **không phải** "không tồn tại" —
    N6 cấm gộp hai trạng thái đó."""

    symbol: str
    thang_dau: str | None
    thang_cuoi: str | None
    so_khoa: int


def _moc_phan_vung() -> dict[str, date]:
    cfg = load_tool_d_config(REPO / "config" / "tool_d_config.yaml")
    tho = resolve(cfg, KHOA_MOC)
    return {k: date.fromisoformat(str(v)) for k, v in tho.items()}


def _thang(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def _pool_hien_tai() -> tuple[str, ...]:
    noi_dung = yaml.safe_load(POOL_YAML.read_text(encoding="utf-8"))
    return tuple(noi_dung["trading"])


def _ung_vien_trong_kho() -> tuple[str, ...]:
    """Mọi thư mục mã từng tồn tại trong kho, sau khi loại hợp đồng kỳ hạn
    và mã không phải quote USDT — đúng hai phép loại của `DR-D1-01` §1."""
    kq = liet_ke_kho_luu_tru(prefix=GOC_KHO, delimiter="/")
    ten: list[str] = []
    for thu_muc in kq.thu_muc:
        sym = thu_muc[len(GOC_KHO) :].rstrip("/")
        if not sym or _RE_KY_HAN.search(sym) or not sym.endswith("USDT"):
            continue
        ten.append(sym)
    print(f"  kho: {len(kq.thu_muc)} thư mục, {len(ten)} ứng viên perpetual/USDT "
          f"({kq.so_trang} trang)")
    return tuple(sorted(ten))


def _khoang_ton_tai(symbol: str) -> KhoangTonTai:
    kq = liet_ke_kho_luu_tru(prefix=f"{GOC_KHO}{symbol}/1d/")
    thang = sorted(m.group(1) for k in kq.khoa if (m := _RE_THANG.search(k)))
    if not thang:
        return KhoangTonTai(symbol=symbol, thang_dau=None, thang_cuoi=None, so_khoa=len(kq.khoa))
    return KhoangTonTai(
        symbol=symbol, thang_dau=thang[0], thang_cuoi=thang[-1], so_khoa=len(kq.khoa)
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--max-ma",
        type=int,
        default=0,
        help="0 = đo hết. >0 = chạy thử trên N mã đầu (KHÔNG dùng làm bằng chứng: "
        "một tập con không trả lời được câu hỏi về TOÀN BỘ rổ)",
    )
    ap.add_argument("--ket-qua", type=Path, default=KET_QUA)
    args = ap.parse_args(argv)

    moc = _moc_phan_vung()
    t0, t1, t2 = moc["t0"], moc["t1"], moc["t2"]
    thang_t0, thang_t1, thang_t2 = _thang(t0), _thang(t1), _thang(t2)
    print(f"mốc: T0={t0} ({thang_t0})  T1={t1} ({thang_t1})  T2={t2} ({thang_t2})")

    pool = _pool_hien_tai()
    print(f"pool hiện tại: {len(pool)} mã (config/pool.yaml)")

    ung_vien = _ung_vien_trong_kho()

    # `exchangeInfo` để biết mã nào CÒN trên sàn hôm nay — dùng để đối
    # chiếu với kho, đúng phép trừ của `DR-D1-01` §1 (874 − 658 = 219).
    info = get_exchange_info()
    con_tren_san = {
        s["symbol"]
        for s in info["symbols"]
        if s.get("contractType") == "PERPETUAL" and s.get("quoteAsset") == "USDT"
    }
    print(f"exchangeInfo: {len(con_tren_san)} mã perpetual/USDT còn trên sàn")

    can_do = sorted(set(pool) | set(ung_vien))
    if args.max_ma > 0:
        can_do = can_do[: args.max_ma]
        print(f"⚠️ CHẠY THỬ — chỉ {len(can_do)} mã, KHÔNG phải bằng chứng")

    print(f"đo khoảng tồn tại của {len(can_do)} mã…")
    khoang: dict[str, KhoangTonTai] = {}
    bat_dau = time.monotonic()
    for i, sym in enumerate(can_do, 1):
        khoang[sym] = _khoang_ton_tai(sym)
        if i % 50 == 0 or i == len(can_do):
            print(f"  {i}/{len(can_do)}  ({time.monotonic() - bat_dau:.0f}s)")

    def song_tai(sym: str, thang_moc: str) -> bool | None:
        k = khoang.get(sym)
        if k is None or k.thang_dau is None or k.thang_cuoi is None:
            return None
        if k.thang_dau == thang_moc or k.thang_cuoi == thang_moc:
            return None  # cùng tháng — không phân giải được
        return k.thang_dau < thang_moc < k.thang_cuoi

    # ── Con số (1): mã POOL chưa tồn tại tại T0 / T1 ────────────────────
    def chua_ton_tai(thang_moc: str) -> dict[str, list[str]]:
        chua, cung_thang, khong_do_duoc = [], [], []
        for sym in pool:
            k = khoang.get(sym)
            if k is None or k.thang_dau is None:
                khong_do_duoc.append(sym)
            elif k.thang_dau == thang_moc:
                cung_thang.append(sym)
            elif k.thang_dau > thang_moc:
                chua.append(sym)
        return {
            "chua_ton_tai": sorted(chua),
            "cung_thang_khong_phan_giai_duoc": sorted(cung_thang),
            "khong_do_duoc": sorted(khong_do_duoc),
        }

    so_1 = {"tai_T0": chua_ton_tai(thang_t0), "tai_T1": chua_ton_tai(thang_t1)}

    # ── Con số (2): mã sống tại T1 mà pool KHÔNG có ─────────────────────
    # §0.3b: BTC/ETH KHÔNG BAO GIỜ vào pool giao dịch — loại ra, không
    # tính là "thiếu".
    ngoai_pool_song_tai_t1: list[str] = []
    ngoai_pool_cung_thang: list[str] = []
    ngoai_pool_khong_do_duoc: list[str] = []
    for sym in ung_vien:
        if sym in pool or sym in EXCLUDE_FROM_TRADING:
            continue
        v = song_tai(sym, thang_t1)
        if v is None:
            k = khoang.get(sym)
            if k is not None and k.thang_dau is not None and (
                k.thang_dau == thang_t1 or k.thang_cuoi == thang_t1
            ):
                ngoai_pool_cung_thang.append(sym)
            else:
                ngoai_pool_khong_do_duoc.append(sym)
        elif v:
            ngoai_pool_song_tai_t1.append(sym)

    # ── Con số (3): trong nhóm (2), bao nhiêu huỷ niêm yết TRƯỚC T2 ─────
    huy_truoc_t2 = [
        sym
        for sym in ngoai_pool_song_tai_t1
        if (k := khoang[sym]).thang_cuoi is not None and k.thang_cuoi < thang_t2
    ]
    da_roi_khoi_san = [s for s in huy_truoc_t2 if s not in con_tren_san]

    ket_qua = {
        "nguon": "TD-0230, 12/09/2026 — đo ĐỘ LỆCH SỐNG SÓT của config/pool.yaml. "
        "Liệt kê kho tĩnh data.binance.vision (metadata SÀN), 0 trial, "
        "KHÔNG đọc một nến pool nào.",
        "ranh_gioi": (
            "CẬN TRÊN. Con số (2)/(3) lọc theo KHOẢNG TỒN TẠI của mã, CHƯA áp tiêu chí "
            "volume >= 15tr USDT tại t (volume lịch sử cần nến thật; với mã pool thì "
            "chặn cứng ở MT-19). ⇒ trả lời 'rổ có thể thiếu TỐI ĐA bao nhiêu mã', KHÔNG "
            "trả lời 'pool đúng tại T1 gồm những mã nào'. Độ phân giải THÁNG: mã lên/rời "
            "sàn giữa tháng vào ô cung_thang_khong_phan_giai_duoc, không gộp về bên nào "
            "(N6). KHÔNG sửa config/pool.yaml và không đề xuất sửa."
        ),
        "cach_doc": (
            "Viết TRƯỚC khi chạy (khuôn DR-D4-08 §6). (1)+(2) nhỏ (<= ~5% mỗi bên) ⇒ lệch "
            "không đáng kể, D4 chạy được trên pool hiện tại KÈM HẠN CHẾ ĐÃ GHI, và đó là "
            "một DỮ KIỆN không phải hy vọng. (2) hoặc (3) LỚN ⇒ mọi số D4 trên pool này "
            "mang lệch sống sót theo CHIỀU PASS, và tiêu suất B2 trước khi sửa pool là mua "
            "một kết luận mà spec :4338 sẽ vô hiệu hoá ('mỗi lần đổi pool = MỌI số cũ "
            "không so sánh được'). Dù kết quả thế nào cũng KHÔNG tự đổi pool — đó là "
            "quyết định của chủ dự án."
        ),
        "moc": {"t0": t0.isoformat(), "t1": t1.isoformat(), "t2": t2.isoformat()},
        "trial": 0,
        "quy_mo": {
            "pool_hien_tai": len(pool),
            "thu_muc_trong_kho": len(ung_vien),
            "con_tren_san_exchangeinfo": len(con_tren_san),
            "da_do_khoang_ton_tai": len(khoang),
            "chay_thu_max_ma": args.max_ma or None,
        },
        "so_1_ma_pool_chua_ton_tai": {
            moc_ten: {k: len(v) for k, v in bang.items()} for moc_ten, bang in so_1.items()
        },
        "so_1_chi_tiet": so_1,
        "so_2_ma_song_tai_T1_ma_pool_khong_co": {
            "n": len(ngoai_pool_song_tai_t1),
            "cung_thang_khong_phan_giai_duoc": len(ngoai_pool_cung_thang),
            "khong_do_duoc": len(ngoai_pool_khong_do_duoc),
            "danh_sach": sorted(ngoai_pool_song_tai_t1),
        },
        "so_3_trong_so_2_huy_niem_yet_truoc_T2": {
            "n": len(huy_truoc_t2),
            "da_roi_khoi_exchangeinfo": len(da_roi_khoi_san),
            "danh_sach": sorted(huy_truoc_t2),
        },
        "khoang_ton_tai": {s: asdict(k) for s, k in sorted(khoang.items())},
    }

    args.ket_qua.write_text(
        json.dumps(ket_qua, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"\nđã ghi {args.ket_qua}")
    print(f"  (1) mã pool chưa tồn tại tại T0: {len(so_1['tai_T0']['chua_ton_tai'])}"
          f" / tại T1: {len(so_1['tai_T1']['chua_ton_tai'])}  (trên {len(pool)})")
    print(f"  (2) mã sống tại T1 mà pool không có: {len(ngoai_pool_song_tai_t1)}")
    print(f"  (3) trong đó huỷ niêm yết trước T2: {len(huy_truoc_t2)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KhoLuuTruError as exc:
        # N6 — fail-closed. KHÔNG ghi một artifact nửa vời: một con số
        # "thiếu ít mã hơn" là lệch đúng theo chiều PASS.
        print(f"DỪNG, không ghi kết quả: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
