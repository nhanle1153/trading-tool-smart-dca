"""Phép đo MÔ TẢ (0 trial) — tuổi của zone ĐỈNH lúc được dùng làm TP1.

Câu hỏi cần trả lời trước khi quyết có áp hạn dùng 40 nến (§1.3) cho zone
đỉnh hay không:

  (1) Trong số các nến có ít nhất một zone đỉnh nằm TRÊN giá và TRONG TẦM
      `4.0 × R_eff`, bao nhiêu phần trăm mà zone GẦN NHẤT đã quá 40 nến?
  (2) Nếu áp hạn dùng, tỉ lệ "không tìm được zone" (proxy của H-4) tăng từ
      bao nhiêu lên bao nhiêu? Có vượt ngưỡng 40% mà spec dòng 1684 dùng
      để phán quyết L2 không?

🔴 Chạy trên tập **EXPLORE**, KHÔNG phải pool. `DR-D0PRE-05` §4: EXPLORE
dùng để SINH giả thuyết, 0 trial, nằm ngoài phạm vi DR-014 — đây chính là
đường vòng hợp lệ mà MT-19 chỉ ra. Không đọc một byte nào của pool/CALIB.

Dùng LẠI các hàm thuần của dự án, không viết lại phép tính nào (MT-03).
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import talib

from tool_d.zone_detection import K_XAC_NHAN, la_diem_swing, zone_da_bi_huy
from tool_d.zone_strength import compression, touch_count, volume_ratio, zone_hop_le, zss

BUF_ZONE = 0.3  # §1.1 — cùng hằng số ZoneAbsorption.py:141
TUOI_TOI_DA = 40  # §1.3
# 4.0 × R_eff với R_eff 1%–3% (dải §6.8f) ⇒ tầm tìm zone 4%–12%.
DAI_TAM = (0.04, 0.08, 0.12)


def quet_dinh(cao, thap, dong, volume, atr):
    """Chép ĐÚNG vòng quét của ZoneAbsorption._quet_zone_dinh, trả (j, giá)."""
    ra = []
    n = len(cao)
    for i in range(K_XAC_NHAN, n):
        if not la_diem_swing(cao, i, loai="dinh"):
            continue
        if math.isnan(atr[i]) or dong[i] == 0:
            continue
        buf = BUF_ZONE * atr[i] / dong[i]
        zone_low, zone_high = cao[i] * (1 - buf), cao[i] * (1 + buf)
        j = i + K_XAC_NHAN
        if j >= n or zone_da_bi_huy(cao, i, j, loai="dinh"):
            continue
        v_r = volume_ratio(volume, i_swing=i)
        comp = compression(cao, thap, dong, i_hinh_thanh=i, i_hien_tai=j)
        if v_r is None or comp is None:
            continue
        tc = touch_count(cao, dong, zone_low, zone_high, i_swing=i, t=j, loai="dinh")
        if not zone_hop_le(
            zss_value=zss(touch=tc, ty_le_volume=v_r, do_nen=comp),
            so_touch=tc,
            tuoi_nen=K_XAC_NHAN,
        ):
            continue
        ra.append((j, zone_low))
    return ra


def main() -> int:
    thu_muc = Path("user_data/data/explore/futures")
    files = sorted(thu_muc.glob("*-4h-futures.feather"))
    if not files:
        print("Không thấy dữ liệu EXPLORE 4h")
        return 1

    # đếm theo từng dải tầm: [có zone bất kỳ, có zone còn hạn, zone gần nhất quá hạn]
    dem = {b: [0, 0, 0] for b in DAI_TAM}
    tong_nen = 0
    tuoi_mau: list[int] = []

    for f in files:
        df = pd.read_feather(f)
        if len(df) < 60:
            continue
        cao, thap, dong, vol = (df[c].tolist() for c in ("high", "low", "close", "volume"))
        atr = talib.ATR(
            np.asarray(cao, float), np.asarray(thap, float), np.asarray(dong, float), timeperiod=14
        )
        dinh = quet_dinh(cao, thap, dong, vol, atr)
        if not dinh:
            continue
        for t in range(60, len(df)):
            gia = dong[t]
            if gia <= 0:
                continue
            tong_nen += 1
            # zone đã xác nhận tới t, nằm TRÊN giá — đúng bộ lọc _zone_dinh_tren
            tren = [(j, z) for (j, z) in dinh if j <= t and z > gia]
            for band in DAI_TAM:
                tran = gia * (1 + band)
                trong_tam = [(j, z) for (j, z) in tren if z <= tran]
                if not trong_tam:
                    continue
                dem[band][0] += 1
                j_gan, _ = min(trong_tam, key=lambda x: x[1])
                tuoi = t - j_gan
                if band == 0.08:
                    tuoi_mau.append(tuoi)
                if tuoi <= TUOI_TOI_DA:
                    dem[band][1] += 1
                else:
                    dem[band][2] += 1

    print(f"Tập EXPLORE: {len(files)} mã 4H | {tong_nen:,} nến-quan-sát\n")
    print("| Tầm tìm zone | Có zone trên giá | Zone gần nhất CÒN HẠN (≤40) | QUÁ HẠN | % quá hạn |")
    print("|---|---|---|---|---|")
    for band in DAI_TAM:
        co, con, qua = dem[band]
        pct = qua / co * 100 if co else float("nan")
        print(f"| ≤ {band:.0%} | {co:,} | {con:,} | {qua:,} | **{pct:.1f}%** |")

    print("\n| Tầm | Tỉ lệ KHÔNG có zone (nạng) — HIỆN TẠI | ... NẾU áp hạn dùng 40 nến |")
    print("|---|---|---|")
    for band in DAI_TAM:
        co, con, _ = dem[band]
        nang_gio = (tong_nen - co) / tong_nen * 100
        nang_moi = (tong_nen - con) / tong_nen * 100
        print(f"| ≤ {band:.0%} | {nang_gio:.1f}% | **{nang_moi:.1f}%** |")

    if tuoi_mau:
        a = np.asarray(tuoi_mau)
        print(
            f"\nTuổi zone gần nhất (tầm 8%), nến 4H: trung vị {np.median(a):.0f} | "
            f"P75 {np.percentile(a, 75):.0f} | P90 {np.percentile(a, 90):.0f} | max {a.max()}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
