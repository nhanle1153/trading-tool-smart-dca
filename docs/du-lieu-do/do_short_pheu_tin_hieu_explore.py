"""Đo mô tả (0 trial, DR-014 §2 — ngoài phạm vi, EXPLORE) — TD-0184, Phương án A Bước 1.

Câu hỏi: PHỄU TÍN HIỆU phía SHORT (zone đỉnh → xác nhận §3.3b(dinh) → lọc
xu hướng DOWN) cho bao nhiêu tín hiệu/năm trên EXPLORE — để biết CỘNG với
Long (63,6 lệnh/năm quy đổi pool, đã đo) có đưa tổng lên sàn 150 (§10.2)
không.

🔴 RANH GIỚI, đọc trước khi dùng kết quả:
  1. **CHỈ ĐẾM TÍN HIỆU**, không chạy backtest/PnL — Short KHÔNG có tầng
     thực thi (đòn bẩy/định cỡ/SL/TP/tranche) trong `ZoneAbsorption.py`
     (`can_short = False`). Xây tầng đó là việc của D3.5-thu-nhỏ-cho-Short
     (`DR-D4-01` §2b), KHÔNG phải việc của phép đo này.
  2. **KHÔNG tự động mở khoá chạy Short thật cho D4** — dù kết quả có đẹp
     tới đâu, ba điều kiện `DR-D4-01` §2b (DG7 calibrate riêng cho Short,
     Δ_R(SHORT) đo qua `L-Z56`, ngân sách ≥9 suất) vẫn phải thoả đủ, riêng.
  3. **Short ≠ Long đảo dấu** (`§3.3d` bác thẳng giả định này — funding,
     nền biến động, short squeeze khác nhau). Đếm bằng cách lật `loai`/
     `huong_muc_tieu` là CẬN TRÊN của khả năng có tín hiệu hình học, KHÔNG
     phải bằng chứng lợi thế giao dịch — cùng cách `MT-22` gắn nhãn "cận
     trên" cho phương án B (không phải "đúng bằng").
  4. Không đi qua tầng định cỡ (`custom_stake_amount`/`mult_regime`) —
     tránh hẳn bug đang được vá ở TD-0197 (SizingError sai cho Z0-T0/T1).

Cấu trúc mirror ĐÚNG các hàm sản xuất trên `ZoneAbsorption.py` (KHÔNG chép
logic mới): `_tinh_zone_dinh_day_du()` mirror `_tinh_zone_4h()` (đảo
`thap`↔`cao`, `loai="dinh"`); `_xac_nhan_dinh()` mirror `_xac_nhan_3_3b()`
(cùng vậy, cộng SL-invalidation lật dấu); trend filter gọi THẲNG
`du_dieu_kien_trend_theo_tang(huong_muc_tieu="DOWN")` — hàm generic có
sẵn, không viết lại.

Chạy: `docker compose -f docker/docker-compose.yml run --rm freqtrade
docs/du-lieu-do/do_short_pheu_tin_hieu_explore.py [--max-coins N]`
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import talib

REPO = Path(__file__).resolve().parents[2]
THU_MUC = REPO / "user_data" / "data" / "explore" / "futures"
KET_QUA = REPO / "docs" / "du-lieu-do" / "do_short_pheu_tin_hieu_explore.json"

T0, T2 = pd.Timestamp("2024-04-09", tz="UTC"), pd.Timestamp("2026-01-29", tz="UTC")
POOL_SIZE = 102
K_XAC_NHAN = 3
NEN_1H_MOI_NEN_4H = 4
EMA_NHANH, EMA_CHAM = 20, 50


def _cac_ma() -> list[str]:
    ma = []
    for f in sorted(THU_MUC.glob("*-1h-futures.feather")):
        ten = f.name.replace("-1h-futures.feather", "")
        if all((THU_MUC / f"{ten}-{k}.feather").exists() for k in ("4h-futures", "1d-futures", "1h-mark", "1h-funding_rate")):
            ma.append(ten)
    return ma


def _nam_phu(df1: pd.DataFrame) -> float:
    if df1.empty:
        return 0.0
    a, b = max(df1["date"].iloc[0], T0), min(df1["date"].iloc[-1], T2)
    return max((b - a).total_seconds() / (365.25 * 86400), 0.0)


def _du_du_lieu(ten: str) -> bool:
    df1 = pd.read_feather(THU_MUC / f"{ten}-1h-futures.feather")
    df4 = pd.read_feather(THU_MUC / f"{ten}-4h-futures.feather")
    df1d = pd.read_feather(THU_MUC / f"{ten}-1d-futures.feather")
    return len(df1) >= 1200 and len(df4) >= 60 and len(df1d) >= 60 and _nam_phu(df1) > 0


def _tinh_zone_dinh_day_du(inf: pd.DataFrame, nguong_zss: float, buf_sl_he_so: float) -> pd.DataFrame:
    """Mirror `ZoneAbsorption._tinh_zone_4h()` — `loai="dinh"`, đảo
    `thap`↔`cao`. Trả `inf` cộng thêm `zone_valid_dinh`/`tag_dinh` (chứa
    zl/zh/sw/zss)/`trend_dir_4h`/`atr_4h`. KHÔNG viết lại `la_diem_swing`/
    `zone_da_bi_huy`/`touch_count`/`zone_hop_le`/`zss` — import thẳng
    (N1: một nguồn cho phép tính hình học zone, dù chiều nào)."""
    from tool_d.trend_context import trend_dir_tai
    from tool_d.zone_detection import la_diem_swing, zone_da_bi_huy
    from tool_d.zone_strength import compression, touch_count, volume_ratio, zone_hop_le, zss

    n = len(inf)
    thap, cao, dong, volume = (inf[c].tolist() for c in ("low", "high", "close", "volume"))
    ts_ms = (inf["date"].astype("int64") // 10**6).tolist()
    atr = talib.ATR(np.asarray(cao, float), np.asarray(thap, float), np.asarray(dong, float), timeperiod=14)
    ema_f = talib.EMA(np.asarray(dong, float), timeperiod=EMA_NHANH)
    ema_s = talib.EMA(np.asarray(dong, float), timeperiod=EMA_CHAM)
    trend = [trend_dir_tai(ema_f, ema_s, i) for i in range(n)]

    zone_valid = [False] * n
    tag_col = [""] * n
    for i in range(K_XAC_NHAN, n):
        if not la_diem_swing(cao, i, loai="dinh"):
            continue
        if math.isnan(atr[i]) or dong[i] == 0:
            continue
        buf = 0.3 * atr[i] / dong[i]  # BUF_ZONE §1.1 — hằng số chung, không phải tham số tunable
        zone_low, zone_high = cao[i] * (1 - buf), cao[i] * (1 + buf)
        j = i + K_XAC_NHAN
        if j >= n or zone_da_bi_huy(cao, i, j, loai="dinh"):
            continue
        v_r = volume_ratio(volume, i_swing=i)
        comp = compression(cao, thap, dong, i_hinh_thanh=i, i_hien_tai=j)
        if v_r is None or comp is None:
            continue
        tc = touch_count(cao, dong, zone_low, zone_high, i_swing=i, t=j, loai="dinh")
        diem = zss(touch=tc, ty_le_volume=v_r, do_nen=comp)
        if not zone_hop_le(zss_value=diem, so_touch=tc, tuoi_nen=K_XAC_NHAN, nguong_zss=nguong_zss) or math.isnan(atr[j]):
            continue
        zone_valid[j] = True
        tag_col[j] = json.dumps({"zl": zone_low, "zh": zone_high, "sw": int(ts_ms[i]), "zs": diem})

    inf = inf.copy()
    inf["zone_valid_dinh"] = zone_valid
    inf["tag_dinh"] = tag_col
    inf["trend_dir_4h"] = trend
    inf["atr_4h"] = atr
    return inf


def _moc_cham_truoc_xac_nhan_dinh(cao, rsi, zl: float, zh: float, k_i: int, k_start: int):
    """Mirror `_moc_cham_truoc_xac_nhan` — đỉnh THẬT (max, không phải
    min) của cụm chạm 1H CUỐI trong `[k_i, k_start)`."""
    moc = None
    t = max(k_i, 0)
    while t < k_start:
        if not (zl <= cao[t] <= zh):
            t += 1
            continue
        t_dinh, gia_dinh = t, cao[t]
        while t < k_start and (zl <= cao[t] <= zh):
            if cao[t] > gia_dinh:
                t_dinh, gia_dinh = t, cao[t]
            t += 1
        if rsi[t_dinh] == rsi[t_dinh]:  # not NaN
            moc = (gia_dinh, rsi[t_dinh])
    return moc


def _xac_nhan_dinh(df1: pd.DataFrame, inf4: pd.DataFrame, *, v_min: float, wick_frac: float,
                    bat_dieu_kien_c: bool, buf_sl_he_so: float) -> pd.DataFrame:
    """Mirror `ZoneAbsorption._xac_nhan_3_3b()` — `loai="dinh"`, SL-
    invalidation LẬT DẤU (zone đỉnh bị huỷ khi giá đóng cửa VƯỢT LÊN
    trên, không phải xuống dưới)."""
    from tool_d.entry_confirmation import quet_xac_nhan_zone
    from tool_d.zone_strength import NGUONG_TUOI_ZONE_TOI_DA

    n1 = len(df1)
    xac_nhan = [False] * n1
    so_zone = so_a = trung_nen = 0

    if n1 == 0 or inf4.empty or not inf4["zone_valid_dinh"].any():
        df1 = df1.copy()
        df1["xac_nhan_dinh"] = xac_nhan
        return df1

    cao, thap, dong = (df1[c].tolist() for c in ("high", "low", "close"))
    vol = df1["volume"].tolist()
    rsi = df1["rsi_1h"].tolist()
    vma = df1["volume_ma_1h"].tolist()
    mo = df1["open"].tolist()
    ngay1 = df1["date"].to_numpy(dtype="datetime64[ns]")
    ngay4 = inf4["date"].to_numpy(dtype="datetime64[ns]")
    dong4 = inf4["close"].tolist()
    atr4 = inf4["atr_4h"].tolist()
    bon_gio = np.timedelta64(4, "h")
    dong_cua4 = ngay4 + bon_gio

    for j in np.flatnonzero(inf4["zone_valid_dinh"].to_numpy(dtype=bool)):
        tag = json.loads(inf4["tag_dinh"].iloc[j])
        zl, zh = float(tag["zl"]), float(tag["zh"])
        so_zone += 1

        k_start = int(np.searchsorted(ngay1, dong_cua4[j]))
        if k_start >= n1:
            continue
        den = min(n1, k_start + NGUONG_TUOI_ZONE_TOI_DA * NEN_1H_MOI_NEN_4H)
        # SL LẬT DẤU — zone đỉnh (kháng cự) huỷ khi giá đóng cửa VƯỢT LÊN trên.
        sl_zone = zh * (1.0 + buf_sl_he_so * atr4[j] / zh)
        for m in range(j + 1, len(dong4)):
            if dong4[m] > sl_zone:
                den = min(den, int(np.searchsorted(ngay1, dong_cua4[m])))
                break
        if den <= k_start:
            continue

        k_i = int(np.searchsorted(ngay1, np.datetime64(int(tag["sw"]), "ms").astype("datetime64[ns]")))
        moc = _moc_cham_truoc_xac_nhan_dinh(cao, rsi, zl, zh, k_i, k_start)

        kq = quet_xac_nhan_zone(
            mo, cao, thap, dong, rsi, vol, vma,
            zone_low=zl, zone_high=zh, tu=k_start, den=den,
            v_min=v_min, loai="dinh",
            lan_cham_truoc_khi_xac_nhan=moc,
            bat_dieu_kien_c=bat_dieu_kien_c, wick_frac=wick_frac,
        )
        c = kq.nen_xac_nhan_that
        if c is None:
            continue
        if xac_nhan[c]:
            trung_nen += 1
            continue
        xac_nhan[c] = True
        so_a += 1

    df1 = df1.copy()
    df1["xac_nhan_dinh"] = xac_nhan
    return df1, so_zone, so_a, trung_nen


def do_pheu_short(ma: list[str]) -> dict:
    """Phễu tín hiệu SHORT — zone đỉnh → xác nhận(dinh) → trend DOWN."""
    sys.path.insert(0, str(REPO / "user_data" / "strategies"))
    from freqtrade.strategy import merge_informative_pair

    from tool_d.arms import du_dieu_kien_trend_theo_tang
    from tool_d.config.loader import load_tool_d_config, resolve
    from ZoneAbsorption import ZoneAbsorption

    cfg = load_tool_d_config()
    nguong_zss = float(resolve(cfg, "tier_b.zss_threshold"))
    buf_sl_he_so = float(resolve(cfg, "tier_b.buf_sl_atr"))
    v_min = float(resolve(cfg, "tier_b.v_min"))
    wick_frac = float(resolve(cfg, "tier_b.wick_close_upper_frac"))

    s = ZoneAbsorption(config={"stake_currency": "USDT", "exchange": {"name": "binance"}})
    tong = Counter()
    tin_hieu_theo_ma: dict[str, tuple[int, float]] = {}
    nam = 0.0
    t0 = time.time()

    for ten in ma:
        df1 = pd.read_feather(THU_MUC / f"{ten}-1h-futures.feather")
        df4 = pd.read_feather(THU_MUC / f"{ten}-4h-futures.feather")
        df1d = pd.read_feather(THU_MUC / f"{ten}-1d-futures.feather")
        nam_ma = _nam_phu(df1)
        nam += nam_ma
        d = df1.copy()
        d["atr_1h"] = talib.ATR(d["high"], d["low"], d["close"], timeperiod=14)
        d["rsi_1h"] = talib.RSI(d["close"], timeperiod=14)
        d["volume_ma_1h"] = d["volume"].rolling(20).mean()

        inf4 = _tinh_zone_dinh_day_du(df4.copy(), nguong_zss, buf_sl_he_so)
        d_xn, sz, sa, tn = _xac_nhan_dinh(d, inf4, v_min=v_min, wick_frac=wick_frac, bat_dieu_kien_c=True, buf_sl_he_so=buf_sl_he_so)
        tong["zone"] += sz
        tong["A_xac_nhan"] += sa
        tong["trung_nen"] += tn

        d2 = merge_informative_pair(d_xn, inf4, "1h", "4h", ffill=True)
        inf1d = s._tinh_trend_1d(df1d.copy())
        d2 = merge_informative_pair(d2, inf1d[["date", "adx", "trend_dir_1d", "tuoi_trend_1d"]], "1h", "1d", ffill=True)

        trong = (d2["date"] >= T0) & (d2["date"] <= T2)
        xn_mask = d2["xac_nhan_dinh"].astype(bool) & trong

        def _dat_dieu_kien_trend(hang) -> bool:
            h1d, h4h = hang["trend_dir_1d_1d"], hang["trend_dir_4h_4h"]
            adx, tuoi = hang["adx_1d"], hang["tuoi_trend_1d_1d"]
            if pd.isna(h1d) or pd.isna(h4h) or pd.isna(adx):
                return False
            return du_dieu_kien_trend_theo_tang(
                tang="DAY_DU", huong_muc_tieu="DOWN", huong_1d=h1d, huong_4h=h4h,
                adx_1d=adx, tuoi_nen_1d=None if pd.isna(tuoi) else int(tuoi),
            )

        tin_hieu_sau_trend = 0
        if xn_mask.any():
            qua_trend = d2.loc[xn_mask].apply(_dat_dieu_kien_trend, axis=1)
            tin_hieu_sau_trend = int(qua_trend.sum())
        tong["tin_hieu_sau_trend"] += tin_hieu_sau_trend
        tin_hieu_theo_ma[ten] = (tin_hieu_sau_trend, nam_ma)

    ra = {
        "so_ma": len(ma), "ma_nam": round(nam, 2),
        "zone_dinh": tong["zone"], "A_xac_nhan": tong["A_xac_nhan"], "trung_nen": tong["trung_nen"],
        "tin_hieu_sau_trend_down": tong["tin_hieu_sau_trend"],
        "ty_le_A_tren_zone": round(tong["A_xac_nhan"] / tong["zone"], 4) if tong["zone"] else None,
        "tin_hieu_moi_ma_nam": round(tong["tin_hieu_sau_trend"] / nam, 3) if nam else None,
        "tin_hieu_quy_doi_pool_102_moi_nam": round(tong["tin_hieu_sau_trend"] / nam * POOL_SIZE, 1) if nam else None,
        "tin_hieu_moi_ma_nam_theo_ma": _phan_vi([v / n for v, n in tin_hieu_theo_ma.values() if n > 0]),
        "giay": round(time.time() - t0, 1),
    }
    print(f"[phễu SHORT] {ra}", flush=True)
    return ra


def _phan_vi(xs: list[float]) -> dict:
    if not xs:
        return {}
    a = np.asarray(xs, float)
    return {"n": len(xs), "min": round(float(a.min()), 3), "P25": round(float(np.percentile(a, 25)), 3),
            "median": round(float(np.median(a)), 3), "P75": round(float(np.percentile(a, 75)), 3),
            "max": round(float(a.max()), 3), "mean": round(float(a.mean()), 3)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-coins", type=int, default=0)
    a = ap.parse_args()
    ma = [m for m in _cac_ma() if _du_du_lieu(m)]
    if a.max_coins:
        ma = ma[: a.max_coins]
    print(f"EXPLORE: {len(ma)} mã đủ file · timerange [{T0.date()},{T2.date()}]", flush=True)

    pheu_short = do_pheu_short(ma)

    # 🔴 Long đã đo Ở TẦNG LỆNH THẬT (62 lệnh, sau backtest+admission+sizing —
    # td0193-lenh-nam-explore.json), còn `pheu_short` ở đây CHỈ tới tầng TÍN
    # HIỆU (trước khi có tầng thực thi Short nào). Cộng thẳng hai con số khác
    # tầng là SO SÁNH SAI ĐƠN VỊ — đúng lớp lỗi `L-Z48c` (trộn hai đại lượng
    # cùng tên khác nghĩa). Tách hai cách đọc, không gộp thành MỘT số duy nhất:
    long_tin_hieu_nam = 96 / 99.4 * POOL_SIZE  # td0193: tin_hieu_sau_trend / ma_nam × 102
    long_lenh_that_nam = 63.6  # td0193: đã qua backtest thật (lệnh thật)
    ty_le_tin_hieu_thanh_lenh_long = long_lenh_that_nam / long_tin_hieu_nam  # ~0,646 — đo được, không giả định

    short_tin_hieu_nam = pheu_short["tin_hieu_quy_doi_pool_102_moi_nam"] or 0.0
    short_lenh_uoc_luong = round(short_tin_hieu_nam * ty_le_tin_hieu_thanh_lenh_long, 1)

    ra = {
        "nguon": "TD-0184 Phương án A Bước 1 — phễu TÍN HIỆU (không PnL) phía SHORT trên EXPLORE, 0 trial",
        "ranh_gioi": (
            "CHỈ đếm tín hiệu (zone đỉnh → xác nhận §3.3b(dinh) → trend DOWN). "
            "KHÔNG chạy backtest/PnL — Short không có tầng thực thi. KHÔNG tự mở khoá "
            "chạy Short thật cho D4 (vẫn cần đủ DR-D4-01 §2b). Short≠Long đảo dấu (§3.3d) "
            "— con số này là CẬN TRÊN của khả năng có tín hiệu hình học."
        ),
        "timerange": f"{T0:%Y%m%d}-{T2:%Y%m%d}", "san_nhanh_1": 150,
        "pheu_tin_hieu_short": pheu_short,
        "so_sanh_dung_tang": {
            "canh_bao": (
                "Long đã đo ở tầng LỆNH THẬT (sau backtest); Short ở đây chỉ tới tầng "
                "TÍN HIỆU (trước thực thi) — không cộng thẳng hai số khác tầng."
            ),
            "long_tin_hieu_nam_quy_doi_pool": round(long_tin_hieu_nam, 1),
            "long_lenh_that_nam_quy_doi_pool": long_lenh_that_nam,
            "ty_le_tin_hieu_thanh_lenh_that_DO_DUOC_tu_Long": round(ty_le_tin_hieu_thanh_lenh_long, 4),
            "short_tin_hieu_nam_quy_doi_pool": round(short_tin_hieu_nam, 1),
            "short_lenh_UOC_LUONG_ap_ty_le_cua_Long": short_lenh_uoc_luong,
            "canh_bao_uoc_luong": (
                "short_lenh_UOC_LUONG là GIẢ ĐỊNH (áp tỉ lệ tín-hiệu→lệnh của Long cho Short), "
                "KHÔNG PHẢI ĐO — Short không có tầng thực thi để đo tỉ lệ riêng của chính nó."
            ),
        },
        "tong_UOC_LUONG_long_lenh_that_cong_short_uoc_luong": round(long_lenh_that_nam + short_lenh_uoc_luong, 1),
        "tong_TOI_DA_ca_hai_o_tang_tin_hieu": round(long_tin_hieu_nam + short_tin_hieu_nam, 1),
        "dat_san_150_o_uoc_luong": (long_lenh_that_nam + short_lenh_uoc_luong) >= 150,
    }
    KET_QUA.write_text(json.dumps(ra, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(ra, ensure_ascii=False, indent=2))
    print(f"→ {KET_QUA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
