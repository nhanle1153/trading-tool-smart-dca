"""Đo mô tả (0 trial, DR-014 §2) — kiểm tra `_quet_zone_dinh`/`_zone_dinh_tren`
(TD-0189) có bug hay chỉ là một hiện tượng cấu trúc thị trường thật, sau
khi phiên `-be` báo 21/21 lệnh TP1 trên EXPLORE (88 mã, TD-0193) đều rơi
vào nạng — KHÔNG lệnh nào dùng zone đối diện.

Chạy: `docker compose -f docker/docker-compose.yml run --rm freqtrade
docs/du-lieu-do/td0189-diem-thoi-gian-zone-dinh-explore.py`

Hai phép đo:
  1. `_quet_zone_dinh` CÓ tìm được zone đỉnh CONFIRMED không (đúng logic
     sản xuất, `nguong_zss` đọc từ config thật) — bác bỏ giả thuyết "hàm
     không bao giờ trả gì" bằng cách đếm trực tiếp trên 4H thật.
  2. Tại một điểm thời gian NGẪU NHIÊN bất kỳ (không riêng lúc vào lệnh),
     tỉ lệ có ÍT NHẤT MỘT zone đỉnh CÒN SỐNG (chưa bị giá đóng cửa vượt
     qua kể từ lúc xác nhận) nằm trong 5%/12% phía trên giá — ước lượng
     KHÔNG điều kiện theo trend, nên là CẬN TRÊN của tỉ lệ thật tại các
     điểm entry (entry chỉ mở khi 4H/1D đã UP một thời gian — chính điều
     kiện làm zone đối diện gần đó dễ bị phá).

Kết luận (09/09/2026 đêm): `_quet_zone_dinh` HOẠT ĐỘNG ĐÚNG — 4775 zone
đỉnh confirmed trên 100 mã EXPLORE (219.338 nến 4H), không phải 0 hay
gần 0. Tỉ lệ điểm thời gian bất kỳ có ≥1 zone sống trong 5%: **17,6%**;
trong 12% (≈ trần tìm zone `4×R_eff` với `R_eff` điển hình ~3%): **35,9%**.
Đây là CẬN TRÊN không-điều-kiện-theo-trend; 21/21 lệnh THẬT rơi nạng dù
n nhỏ (không đủ để khẳng định tỉ lệ chính xác) là kết quả PLAUSIBLE, không
phải dấu hiệu bug — cùng chiều với DR-D4-06 (73-87% nạng khi áp thêm hạn
tuổi). `_zone_dinh_tren()` không tự lọc "còn sống" (chỉ lọc `> p_avg`),
nhưng trong ngữ cảnh uptrend đã xác nhận, zone bị phá thường đã NẰM DƯỚI
p_avg hiện tại nên bị lọc gián tiếp — hai cách lọc trùng nhau phần lớn
trong đúng ngữ cảnh entry thật (LONG-only, cần trend UP xác nhận).

Việc còn lại (KHÔNG làm ở đây, cần TD-0184 sinh Decision Log thật):
đo H-4 chính xác (`ty_le_khong_co_zone` / `ty_le_zone_qua_han`, DR-D4-06)
cần TỪNG lệnh thật với đúng p_avg/R_eff/thời điểm — không thể suy ra
đáng tin từ một phép đo không điều kiện như file này.
"""

from __future__ import annotations

import glob
import json
from pathlib import Path

import numpy as np
import pandas as pd
import talib

from tool_d.config.loader import load_tool_d_config, resolve
from tool_d.zone_detection import K_XAC_NHAN, la_diem_swing, zone_da_bi_huy
from tool_d.zone_strength import compression, touch_count, volume_ratio, zone_hop_le, zss

BUF_ZONE = 0.3
DATADIR = Path("user_data/data/explore/futures")


def _dem_confirmed(cao, thap, dong, vol, atr, nguong_zss: float) -> dict[int, float]:
    """CHÉP đúng logic `_quet_zone_dinh` (không viết lại phép tính, chỉ đổi
    kiểu trả về thành dict {nến_xác_nhận: giá} để phép đo bên dưới dùng lại
    được vị trí hình thành `i`)."""
    n = len(dong)
    ra: dict[int, float] = {}
    for i in range(K_XAC_NHAN, n):
        if not la_diem_swing(cao, i, loai="dinh"):
            continue
        if np.isnan(atr[i]) or dong[i] == 0:
            continue
        buf = BUF_ZONE * atr[i] / dong[i]
        zl, zh = cao[i] * (1 - buf), cao[i] * (1 + buf)
        j = i + K_XAC_NHAN
        if j >= n or zone_da_bi_huy(cao, i, j, loai="dinh"):
            continue
        v_r = volume_ratio(vol, i_swing=i)
        comp = compression(cao, thap, dong, i_hinh_thanh=i, i_hien_tai=j)
        if v_r is None or comp is None:
            continue
        tc = touch_count(cao, dong, zl, zh, i_swing=i, t=j, loai="dinh")
        if not zone_hop_le(
            zss_value=zss(touch=tc, ty_le_volume=v_r, do_nen=comp),
            so_touch=tc, tuoi_nen=K_XAC_NHAN, nguong_zss=nguong_zss,
        ):
            continue
        ra[j] = zl
    return ra


def phan_tich_mot_ma(path4h: Path, nguong_zss: float):
    df = pd.read_feather(path4h)
    cao, thap, dong, vol = (df[c].tolist() for c in ("high", "low", "close", "volume"))
    n = len(dong)
    atr = talib.ATR(np.asarray(cao, float), np.asarray(thap, float), np.asarray(dong, float), 14)
    zone_theo_j = _dem_confirmed(cao, thap, dong, vol, atr, nguong_zss)
    if not zone_theo_j:
        return len(zone_theo_j), []

    dinh_goc_theo_j = {}
    i_hinh_thanh = {j: j - K_XAC_NHAN for j in zone_theo_j}
    for j in zone_theo_j:
        dinh_goc_theo_j[j] = cao[i_hinh_thanh[j]]

    dang_song: dict[int, float] = {}
    ket_qua = []
    for t in range(n):
        if t in zone_theo_j:
            dang_song[t] = zone_theo_j[t]
        for j in [j for j, goc in dinh_goc_theo_j.items() if j in dang_song and dong[t] > goc]:
            del dang_song[j]
        if dong[t] == 0:
            continue
        tren_gia = [g for g in dang_song.values() if g > dong[t]]
        so_5 = sum(1 for g in tren_gia if (g - dong[t]) / dong[t] <= 0.05)
        so_12 = sum(1 for g in tren_gia if (g - dong[t]) / dong[t] <= 0.12)
        kc = (min(tren_gia) - dong[t]) / dong[t] * 100 if tren_gia else None
        ket_qua.append((so_5, so_12, kc))
    return len(zone_theo_j), ket_qua


def main() -> None:
    cfg = load_tool_d_config()
    nguong_zss = float(resolve(cfg, "tier_b.zss_threshold"))

    files = sorted(glob.glob(str(DATADIR / "*-4h-futures.feather")))
    tong_confirmed = 0
    tong_nen = 0
    co_5 = co_12 = 0
    khoang_cach: list[float] = []
    so_ma = 0

    for f in files:
        n_confirmed, kq = phan_tich_mot_ma(Path(f), nguong_zss)
        tong_confirmed += n_confirmed
        if not kq:
            continue
        so_ma += 1
        for s5, s12, kc in kq:
            tong_nen += 1
            co_5 += s5 > 0
            co_12 += s12 > 0
            if kc is not None:
                khoang_cach.append(kc)

    ra = {
        "nguon": "TD-0189, phản hồi phát hiện 21/21 TP1=nạng của phiên -be (TD-0193)",
        "so_file_4h": len(files),
        "so_ma_co_zone_dinh_confirmed": so_ma,
        "tong_zone_dinh_confirmed": tong_confirmed,
        "tong_nen_do": tong_nen,
        "ty_le_nen_co_zone_trong_5pct": co_5 / tong_nen if tong_nen else None,
        "ty_le_nen_co_zone_trong_12pct": co_12 / tong_nen if tong_nen else None,
        "khoang_cach_gan_nhat_pct": {
            "median": float(np.median(khoang_cach)) if khoang_cach else None,
            "p10": float(np.percentile(khoang_cach, 10)) if khoang_cach else None,
            "p90": float(np.percentile(khoang_cach, 90)) if khoang_cach else None,
            "n": len(khoang_cach),
        },
        "ket_luan": (
            "_quet_zone_dinh hoat dong dung (khong phai 0/bug) — ty le co zone "
            "trong tam KHONG DIEU KIEN theo trend la can tren cua ty le thuc te "
            "tai diem entry (entry can trend UP xac nhan, dieu kien lam zone doi "
            "dien gan do de bi pha)."
        ),
    }
    out = Path("docs/du-lieu-do/td0189-diem-thoi-gian-zone-dinh-explore.json")
    out.write_text(json.dumps(ra, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(ra, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
