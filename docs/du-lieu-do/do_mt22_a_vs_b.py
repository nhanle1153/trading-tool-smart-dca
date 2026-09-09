"""Phép đo MÔ TẢ (0 trial) — lượng hoá đánh đổi MT-22: phương án A vs B.

A = cửa sổ chờ xác nhận §3.3b mở ĐÚNG MỘT LẦN, ở lần chạm đầu tiên sau
    confirmed_at_bar (đọc đúng chữ spec dòng 1075).
B = cửa sổ mở lại ở MỖI lần chạm cho tới khi có một lượt xác nhận thành công.

Chạy trên tập EXPLORE (DR-D0PRE-05 §4 — sinh giả thuyết, 0 trial, ngoài
phạm vi DR-014). KHÔNG đọc pool.

Dùng LẠI hàm thuần của dự án, không viết lại phép tính nào.
"""
from __future__ import annotations
import math, sys
from pathlib import Path
import numpy as np, pandas as pd, talib

from tool_d.zone_detection import K_XAC_NHAN, la_diem_swing, zone_da_bi_huy
from tool_d.zone_strength import compression, touch_count, volume_ratio, zone_hop_le, zss
from tool_d.entry_confirmation import (
    tim_xac_nhan_entry, la_nen_rejection, hap_thu_co_volume,
)

BUF_ZONE = 0.3
V_MIN = 1.0            # tier_b.v_min, FROZEN (DR-D4-03)
TUOI_ZONE_4H = 40      # §1.3
SO_NEN_CHO = 3         # §3.3b

def quet_zone_day(cao, thap, dong, vol, atr, ts_ms):
    """Chép ĐÚNG vòng quét zone đáy của ZoneAbsorption._tinh_zone_4h."""
    ra = []
    n = len(cao)
    for i in range(K_XAC_NHAN, n):
        if not la_diem_swing(thap, i, loai="day"):      continue
        if math.isnan(atr[i]) or dong[i] == 0:          continue
        buf = BUF_ZONE * atr[i] / dong[i]
        zl, zh = thap[i] * (1 - buf), thap[i] * (1 + buf)
        j = i + K_XAC_NHAN
        if j >= n or zone_da_bi_huy(thap, i, j, loai="day"): continue
        v_r = volume_ratio(vol, i_swing=i)
        comp = compression(cao, thap, dong, i_hinh_thanh=i, i_hien_tai=j)
        if v_r is None or comp is None:                 continue
        tc = touch_count(thap, dong, zl, zh, i_swing=i, t=j, loai="day")
        if not zone_hop_le(zss_value=zss(touch=tc, ty_le_volume=v_r, do_nen=comp),
                           so_touch=tc, tuoi_nen=K_XAC_NHAN):
            continue
        ra.append({"i": i, "j": j, "zl": zl, "zh": zh, "tc": tc,
                   "ts_i": ts_ms[i], "ts_j": ts_ms[j]})
    return ra

def su_kien_cham(low, zl, zh, tu, den):
    """Nhóm các nến 1H nằm trong zone thành SỰ KIỆN chạm (vào-rồi-ra)."""
    ra, dang = [], False
    for t in range(tu, min(den, len(low))):
        trong = zl <= low[t] <= zh
        if trong and not dang:
            ra.append(t); dang = True
        elif not trong:
            dang = False
    return ra

def main() -> int:
    thu_muc = Path("user_data/data/explore/futures")
    files = sorted(thu_muc.glob("*-4h-futures.feather"))
    tong = {"zone": 0, "co_moc_b": 0, "A": 0, "B": 0,
            "B_them_qua_ac": 0, "B_them_qua_b": 0, "A_qua_b": 0}
    for f4 in files:
        f1 = f4.with_name(f4.name.replace("-4h-", "-1h-"))
        if not f1.exists(): continue
        d4, d1 = pd.read_feather(f4), pd.read_feather(f1)
        if len(d4) < 60 or len(d1) < 240: continue
        cao4, thap4, dong4, vol4 = (d4[c].tolist() for c in ("high","low","close","volume"))
        ts4 = (d4["date"].astype("int64") // 10**6).tolist()
        atr4 = talib.ATR(np.asarray(cao4,float), np.asarray(thap4,float), np.asarray(dong4,float), timeperiod=14)
        zones = quet_zone_day(cao4, thap4, dong4, vol4, atr4, ts4)
        if not zones: continue

        mo1, cao1, thap1, dong1, vol1 = (d1[c].tolist() for c in ("open","high","low","close","volume"))
        ts1 = (d1["date"].astype("int64") // 10**6).tolist()
        rsi1 = talib.RSI(np.asarray(dong1,float), timeperiod=14).tolist()
        vma1 = pd.Series(vol1).rolling(20).mean().tolist()
        moc = {t: k for k, t in enumerate(ts1)}

        for z in zones:
            k_j = moc.get(z["ts_j"]);  k_i = moc.get(z["ts_i"])
            if k_j is None or k_i is None: continue
            tong["zone"] += 1
            # mốc cho (b): lần chạm 1H gần nhất TRƯỚC xác nhận (cửa sổ hình thành)
            truoc = [t for t in range(k_i, k_j) if z["zl"] <= thap1[t] <= z["zh"]]
            moc_b = None
            if truoc:
                t0 = truoc[-1]
                if not math.isnan(rsi1[t0]):
                    moc_b = (thap1[t0], rsi1[t0]); tong["co_moc_b"] += 1
            het = k_j + TUOI_ZONE_4H * 4
            sk = su_kien_cham(thap1, z["zl"], z["zh"], k_j, het)
            if not sk: continue

            def thu(t_cham, lct):
                return tim_xac_nhan_entry(mo1, cao1, thap1, dong1, rsi1, t_cham,
                    loai="day", bat_dieu_kien_c=True, volume=vol1, volume_ma=vma1,
                    v_min=V_MIN, lan_cham_truoc=lct, so_nen_cho_toi_da=SO_NEN_CHO)

            def qua_ac(c):
                return (la_nen_rejection(mo1[c], cao1[c], thap1[c], dong1[c], loai="day")
                        and hap_thu_co_volume(vol1[c], vma1[c], V_MIN))

            # A — chỉ lần chạm đầu tiên
            cA = thu(sk[0], moc_b)
            if cA is not None:
                tong["A"] += 1
                if not qua_ac(cA): tong["A_qua_b"] += 1
            # B — lặp tới khi thành công
            lct, cB, lan = moc_b, None, 0
            for t_cham in sk:
                cB = thu(t_cham, lct); lan += 1
                if cB is not None: break
                if not math.isnan(rsi1[t_cham]): lct = (thap1[t_cham], rsi1[t_cham])
            if cB is not None:
                tong["B"] += 1
                if cA is None:
                    if qua_ac(cB): tong["B_them_qua_ac"] += 1
                    else:          tong["B_them_qua_b"] += 1

    z = tong["zone"] or 1
    print(f"Tập EXPLORE: {len(files)} mã | zone hợp lệ: {tong['zone']:,}")
    print(f"Zone CÓ mốc so cho (b) ngay ở lần chạm đầu: {tong['co_moc_b']:,} "
          f"({tong['co_moc_b']/z:.1%})  <- nếu ~100% thì (b) KHÔNG chết ở phương án A\n")
    print("| Phương án | Zone vào được lệnh | Tỉ lệ |")
    print("|---|---|---|")
    print(f"| A (chỉ lần chạm đầu) | {tong['A']:,} | {tong['A']/z:.1%} |")
    print(f"| B (mọi lần chạm)     | {tong['B']:,} | {tong['B']/z:.1%} |")
    them = tong["B"] - tong["A"]
    print(f"\nB thêm so với A: {them:,} zone ({them/max(tong['A'],1):+.0%} so với A)")
    print(f"  trong đó xác nhận qua (a VÀ c): {tong['B_them_qua_ac']:,}")
    print(f"           xác nhận qua (b)     : {tong['B_them_qua_b']:,}")
    print(f"\nSố lệnh của A đến từ nhánh (b): {tong['A_qua_b']:,} "
          f"({tong['A_qua_b']/max(tong['A'],1):.1%} số lệnh của A)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
