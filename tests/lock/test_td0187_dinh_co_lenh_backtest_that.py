"""🔴 TD-0187 — tầng định cỡ §6.8f đo trên FILL của backtest THẬT (MT-16, DR-D4-04).

Ba điều `tests/unit/test_sizing.py` KHÔNG chứng minh được, và file này phải:

1. **Tỉ trọng tranche thật = ⅓ ⅓ ⅓.** Đọc `cost` từng lệnh vào trong file kết
   quả backtest — cùng cách MT-16 đo ra ¼-¼-½ trên 91 lượt khớp niêm phong.
   Một cấu hình `w_tranche` nạp được không nói gì về thứ đã chạy (ca
   `test_mot_phan_tu_..._VAN_qua_kiem_tong` đã ghim đúng giới hạn đó).
2. **D0.1 trên đường sản xuất:** `cost₁ ≈ (rho × E_D / R_eff) × w₁` với
   `R_eff` giải mã từ chính `enter_tag` của lệnh — tức cỡ lệnh THẬT biến
   theo `1/R_eff` và rủi ro kế hoạch = 1,875 USDT (DR-D0PRE-06).
3. **Đòn bẩy 3x thật sự được áp** — `trade["leverage"] == L_exchange`. Trước
   `ZoneAbsorption` không file nào cài `leverage()` ⇒ mọi backtest chạy 1x.

Và một phép đối chiếu: **`ZoneAbsorption` và `ZoneAbsorptionMinimal` cho
CÙNG zone trên CÙNG dữ liệu** (zl/zh/p1/p2/p3/sl bằng nhau). Phần zone của
file mới là bản chép của Minimal; ca này canh nó không trôi.

Bộ sinh dữ liệu tái dùng `_chia_nho`/`_ghi_feather` của L-Z49 qua importlib
(`tests/` không phải package). Khác L-Z49 ở hai chỗ có chủ đích: (a) 85
ngày UPTREND trước mẫu zone — để ADX(14,1D) ≥ 20 (mẩu §2.5 mà tầng định cỡ
đòi), (b) thêm khung 1D. Chuỗi phẳng của L-Z49 có ADX ≈ 0 nên với chiến
lược sản xuất sẽ không vào lệnh nào — và guard PASS RỖNG bên dưới bắt được.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CAP = "LTC_USDT_USDT"   # trong POOL (BTC/ETH là EXPLORE — DR-D0PRE-05); cost.min = 20 USDT
CAP2 = "XRP_USDT_USDT"  # mã THỨ HAI cho phép đo danh mục (TD-0188): cost.min = 5, bước khối lượng 0,1
SAN_XUAT, TOI_THIEU = "ZoneAbsorption", "ZoneAbsorptionMinimal"
TIMERANGE = "20250315-20250402"

# ── tái dùng bộ sinh nến của L-Z49 ────────────────────────────────────
_spec = importlib.util.spec_from_file_location(
    "lz49", REPO_ROOT / "tests" / "lock" / "test_lz49_lz50_backtest_nho.py"
)
_lz49 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_lz49)  # type: ignore[union-attr]
_chia_nho, _ghi_feather, _lenh_vao = _lz49._chia_nho, _lz49._ghi_feather, _lz49._lenh_vao


N_NGAY_GIAM = 60  # TD-0182 — pha GIẢM dựng trước, xem docstring bên dưới
N_NGAY_TANG = 85  # độ DÀI pha tăng, giữ nguyên từ bản `-e8`
GIA_DAY = 20.0
"""Đáy chữ V — TD-0182 đổi từ 60 xuống 20, và đây là một phép ĐO chứ không
phải nới tay cho test xanh.

Bản `-e8` chọn 60 sau khi sweep, với tiêu chí *"EMA(4H) sống sót qua cú rơi
của nến swing"* — tức chỉ đòi `trend_dir_4h` còn UP **tại nến tín hiệu**.
Hệ thống lúc đó không hỏi gì thêm. Nhưng DG2 (§4) so `trend_dir` tại tranche
2/3 với giá trị ghi trong tag lúc tranche 1, nên nay phải giữ UP **qua cả ba
nến tranche**, một đòi hỏi chặt hơn hẳn.

Sweep đo được (khoảng cách EMA20−EMA50 tại nến tín hiệu → hướng tại tín
hiệu, p1, p2, p3):

    60 → 0,169 → FLAT, DOWN, DOWN, DOWN     ← bản cũ: hỏng ngay tại tín hiệu
    40 → 0,730 → UP,   UP,   FLAT, FLAT
    30 → 1,010 → UP,   UP,   UP,   FLAT     ← còn hụt đúng một nến
    20 → 1,291 → UP,   UP,   UP,   UP       ← ngưỡng tối thiểu

20 là giá trị ĐẦU TIÊN đủ, không phải giá trị an toàn nhất — cùng kỷ luật
"chọn ngưỡng tối thiểu" mà `-e8` đã dùng khi chọn 60."""


#: TD-0194 — chỉ số nến 4H đặt hai ĐỈNH swing, tính từ công thức dốc chứ không
#: gõ tay. Chọn để `zone_low` của chúng rơi hai phía của trần tìm zone TP1
#: (`p_avg + 4,0 × R_eff ≈ 98,368` trên mẫu zone hiện tại):
#:    A ở 848 → đỉnh ~96,95 → zone_low ~96,81  → TRONG tầm (95,0 · 98,368)
#:    B ở 861 → đỉnh ~98,99 → zone_low ~98,85  → NGOÀI tầm
#: 🔴 Ràng buộc thật là GIÁ, KHÔNG phải TUỔI: `_zone_dinh_tren()` lọc
#: `zone > p_avg` nên đỉnh phải > 95,0, mà giá chỉ vượt 95 ở đoạn cuối pha
#: tăng. Cả hai phiên `-f4`/`-2f` ban đầu cùng khai nhầm `tuoi_nen ≤ 40` —
#: nhưng CẢ BA chỗ gọi `zone_hop_le()` truyền `tuoi_nen=K_XAC_NHAN` (hằng 3)
#: nên vế tuổi LUÔN thoả, và `DR-D4-06` đã bỏ hạn tuổi cho zone TP. Đúng cửa
#: sổ, sai lý do — ai nới ngưỡng tuổi rồi tưởng cửa sổ rộng ra sẽ chèn đỉnh ở
#: chỗ giá thấp và nó IM LẶNG không thành ứng viên.
I_DINH_TRONG_TAM, I_DINH_NGOAI_TAM = 848, 861

#: Chiều cao đỉnh khai TƯỜNG MINH, KHÔNG suy từ nến dốc tại chỗ đó.
#: 🔴 Bản đầu lấy `P = b[i][1]` và swing rơi nhầm sang nến `i-1`: nến dốc có
#: `open` so le `±0,2` nên `high` nhảy giữa `base+0,2` và `base+0,6` — nến LẺ
#: liền trước cao hơn đỉnh vừa đặt. Ràng buộc thật: `P` phải lớn hơn
#: `max(high[i-3 .. i-1]) = base(i-1) + 0,6 ≈ base(i) + 0,443` (ba nến SAU đã
#: là nến motif nên không tính). Đo, không đoán — đây đúng loại giả định
#: "nến dốc trơn tru" mà `low` hằng số từng làm sinh 26 swing giả.
CAO_DINH_TRONG_TAM, CAO_DINH_NGOAI_TAM = 97.4, 99.2


def _motif_dinh(cao_dinh: float) -> list[tuple[float, float, float, float, float]]:
    """Bốn nến tạo MỘT zone đỉnh hợp lệ, thay tại chỗ cho nến dốc.

    Thoả đồng thời bốn điều kiện của vòng quét đỉnh (`_quet_zone_dinh`):
      1. `la_diem_swing(cao, i, loai="dinh", k=3)` — ba nến sau `high` thấp hơn.
      2. `zone_da_bi_huy(..., loai="dinh")` sai — không nến nào đóng TRÊN zone.
      3. `touch_count(..., loai="dinh") ≥ 1` — nến `i+1` có `high` chui vào
         `[zone_low, zone_high]` **rồi đóng cửa DƯỚI `zone_low`**, tức trọn một
         cụm chạm-rồi-bật-ra trong đúng một nến. Đây là chiều ĐẢO so với zone
         đáy, và là chỗ đuôi tăng đơn điệu của bản cũ không bao giờ thoả được.
      4. `zss ≥ 0.5` — nến đỉnh mang volume cao (thành phần volume chạm trần),
         bù cho `touch = 1` chỉ đóng góp 1/3.

    Thay TẠI CHỖ (không chèn thêm) để chỉ số nến phía sau **không dịch** — mẫu
    zone đáy giữ nguyên vị trí 870 và mốc lịch giữ nguyên.
    """
    P = cao_dinh
    return [
        (P - 0.45, P, P - 0.55, P - 0.40, 4000.0),          # đỉnh, volume cao
        (P - 0.42, P - 0.05, P - 0.60, P - 0.50, 1200.0),   # chạm lại RỒI đóng dưới
        (P - 0.52, P - 0.30, P - 0.65, P - 0.45, 1000.0),
        (P - 0.47, P - 0.25, P - 0.60, P - 0.40, 1000.0),
    ]


def _bars_4h_co_trend() -> list[tuple[float, float, float, float, float]]:
    """`N_NGAY_GIAM` ngày downtrend 100 → 60, RỒI `N_NGAY_TANG` ngày
    uptrend 60 → 100, rồi ĐÚNG mẫu zone của L-Z49 neo ở mức 100, rồi đuôi
    tăng nhẹ đơn điệu để lệnh có chỗ đóng theo DG8 mà không tạo swing giả.

    🔴 **PHA GIẢM THÊM VÀO Ở TD-0182, và lý do là một phép ĐO chứ không
    phải một linh cảm.** Bản trước chỉ có đoạn dốc tăng đơn điệu. Đo trên
    chính bộ sinh này (92 nến 1D): `tuoi_trend_nen()` trả `None` ở
    **92/92** nến, vì EMA20/50 khung 1D **chỉ mang MỘT dấu trên toàn
    chuỗi** — dốc đơn điệu thì không bao giờ có cross, mà hàm đó đếm từ
    lần cross gần nhất. Điều kiện (4) của §2.5 (`tuổi ≥ 5`) do đó chặn
    100% số nến ⇒ `enter_long` KHÔNG BAO GIỜ được đặt ⇒ backtest ra **0
    lệnh** cho mọi arm `DAY_DU`.

    🔑 **Không ai viết sai dòng nào — fixture đúng với hệ thống CŨ.** Chú
    thích dốc `60→100` bên dưới ghi rõ đã sweep cho *"tuổi trend ≥5 ngày"*,
    nhưng là ở khung **4H**; lúc đó `populate_entry_trend` chỉ có mẩu
    ADX(1D). Phần nối TD-0182 mới bật cổng **hướng 1D + tuổi trend 1D**,
    và fixture im lặng sai với hệ thống MỚI. Cùng họ với bài học TD-0170:
    bộ test dựa vào chi tiết của bộ sinh **được thêm vì lý do khác**.

    Hình chữ V tạo ra một cross THẬT ở khung ngày. Vì sao pha giảm phải
    dài: `EMA50(1D)` ăn 49 nến warmup, mà `tuoi_trend_nen()` quét ngược
    gặp `NaN` là trả `None` — nên điểm cross phải nằm SAU vùng NaN thì
    mới đếm được tuổi. 60 ngày cho cross rơi vào khoảng ngày 75-80 trên
    tổng ~145, cách vùng NaN một quãng an toàn.

    ⚠️ Đáy chữ V là một swing THẬT nên sinh zone thật — nhưng nó nằm
    ngoài `TIMERANGE` (18 ngày cuối), nên KHÔNG tạo thêm lệnh nào và
    không làm lệch phép so `ZoneAbsorption` ↔ `Minimal`. Đó cũng là lý do
    `_sinh_du_lieu()` neo mốc KẾT THÚC chứ không neo mốc bắt đầu."""
    b: list[tuple[float, float, float, float, float]] = []
    n_giam = N_NGAY_GIAM * 6
    for k in range(n_giam):
        # Gương của đoạn dốc tăng: 100 → GIA_DAY, cùng biên độ nến. Kết thúc
        # ở ~GIA_DAY nên nối liền mạch với khởi điểm của pha tăng.
        base = 100.0 - (100.0 - GIA_DAY) * k / n_giam
        o = base + (0.2 if k % 2 else -0.2)
        b.append((o, o + 0.4, o - 0.4, o + (0.1 if k % 2 else -0.1), 1000.0))
    n_pre = N_NGAY_TANG * 6
    for k in range(n_pre):
        # 🔴 ĐO, không đoán — nguyên tắc của `-e8`, giữ nguyên; chỉ CON SỐ
        # đổi 60 → `GIA_DAY` = 20 vì DG2 đòi chặt hơn tiêu chí cũ (xem
        # docstring của `GIA_DAY`). Độ dài `n_pre` giữ nguyên cho warmup
        # 1000 nến 1H + tuổi trend ≥ 5 ngày.
        base = GIA_DAY + (100.0 - GIA_DAY) * k / n_pre
        o = base + (0.2 if k % 2 else -0.2)
        b.append((o, o + 0.4, o - 0.4, o + (0.1 if k % 2 else -0.1), 1000.0))
    # TD-0194 — thay TẠI CHỖ hai motif đỉnh; chỉ số phía sau không dịch.
    for i_dinh, cao_dinh in (
        (I_DINH_TRONG_TAM, CAO_DINH_TRONG_TAM),
        (I_DINH_NGOAI_TAM, CAO_DINH_NGOAI_TAM),
    ):
        motif = _motif_dinh(cao_dinh)
        b[i_dinh : i_dinh + len(motif)] = motif

    b += [
        (99.5, 99.5, 95.0, 96.0, 4000.0),      # swing đáy, volume cao
        (96.0, 96.8, 95.2, 96.6, 1200.0),
        (96.6, 97.0, 96.2, 96.8, 1000.0),
        (96.8, 97.1, 96.4, 96.9, 1000.0),      # nến tín hiệu
        # TD-0189 chặng 2b — HIGH hạ 97,0 → 96,9 (= open, bỏ wick trên).
        # 🔴 Lý do ĐO được, không phải nới tay: với `--timeframe-detail 5m`,
        # `adjust_trade_position`/`custom_exit` nhìn giá ở độ phân giải 5
        # phút cho vị thế ĐÃ MỞ (không chỉ open 1H — đọc mã nguồn
        # `backtesting.py:backtest_loop`, nhánh `has_detail`), nên wick
        # 97,0 của bản cũ CHẠM luôn ngưỡng TP1-nạng (`p_avg + 1,5×R_eff` ≈
        # 96,53) gần như ngay sau khi tranche 1 khớp ở nến NÀY — TP1 chốt
        # trước khi tranche 2/3 có cơ hội khớp, đúng hình dạng lỗi "fixture
        # đúng hệ thống CŨ (chưa có TP), im lặng sai hệ thống MỚI (có TP)"
        # đã gặp ở TD-0182/TD-0194. LOW=95,30 giữ nguyên (vẫn chạm p1).
        (95.50, 95.50, 95.30, 95.40, 1000.0),  # chạm p1 → tranche 1
        (94.98, 95.10, 94.90, 94.95, 1000.0),  # mở ≤ p2 → tranche 2
        (94.60, 94.70, 94.40, 94.60, 1000.0),  # mở ≤ p3 → tranche 3
        (94.65, 95.20, 94.55, 95.10, 1000.0),
        (95.10, 95.60, 95.00, 95.50, 1000.0),
        (95.50, 96.00, 95.40, 95.90, 1000.0),
    ]
    # 🔴 Bug thật bắt được bằng ĐO, không đoán: `low` HẰNG SỐ trong đuôi
    # tạo một cao nguyên phẳng, và `la_diem_swing()` so `gia[i] ==
    # min(cửa_sổ)` — với mọi giá trị BẰNG NHAU thì MỌI bar trong đuôi đều
    # "hoà điểm tối thiểu", sinh ra 26 swing GIẢ (đo được: index 523-546,
    # `low` = 95.5 không đổi). Zone giả ở đuôi có thể tạo lệnh THỨ HAI
    # ngoài ý muốn, làm `_lenh_du_ba_tranche()` chọn nhầm swing (đã xảy ra
    # — hàm chọn `found[-1]` tưởng là tín hiệu thật, hoá ra là swing giả
    # cuối đuôi). Sửa: `low` TĂNG ĐƠN ĐIỆU nghiêm ngặt, không còn hoà.
    for k in range(30):
        low = 95.5 + k * 0.01
        b.append((95.9, 96.3 + k * 0.01, low, 95.9 + (0.1 if k % 2 else -0.1) + k * 0.01, 1000.0))
    return b


KET_THUC_1H = pd.Timestamp("2025-04-02 15:00", tz="UTC")
"""Mốc nến 1H CUỐI CÙNG của bộ sinh — neo ở ĐUÔI, không ở đầu (xem chú
thích trong `_sinh_du_lieu`)."""


def _moc_bat_dau(so_nen_1h: int) -> pd.Timestamp:
    """Mốc nến 1H ĐẦU TIÊN, suy từ đuôi và độ dài chuỗi.

    🔴 Tồn tại để có MỘT nguồn sự thật cho mốc thời gian. Bản trước neo
    mốc đầu bằng hằng số `"2025-01-01"` viết ở hai chỗ, và ca
    `test_enter_tag_...` chép lại hằng số đó lần thứ ba để đổi giờ mở lệnh
    ra chỉ số nến. Khi TD-0182 kéo dài lịch sử (thêm pha giảm), mốc đầu
    dịch về 2024-11 nhưng ca test vẫn tính theo 2025-01-01 ⇒ nó soi **sai
    nến** — mà vẫn XANH, vì nến sai tình cờ cũng UP. Một phép kiểm xanh vì
    trùng hợp còn tệ hơn không có, nên mốc phải suy ra chứ không chép lại.
    """
    return KET_THUC_1H - pd.Timedelta(hours=so_nen_1h - 1)


def _dem_zone(rows4, loai: str) -> int:
    """Đếm zone HỢP LỆ của một loại trên chuỗi 4H — mô phỏng đúng vòng quét
    của chiến lược (`_tinh_zone_4h` cho `"day"`, `_quet_zone_dinh` cho
    `"dinh"`), dùng lại các hàm thuần, không chép phép tính."""
    import numpy as np
    import talib
    from tool_d.config.loader import load_tool_d_config, resolve
    from tool_d.zone_detection import K_XAC_NHAN, la_diem_swing, zone_da_bi_huy
    from tool_d.zone_strength import compression, touch_count, volume_ratio, zone_hop_le, zss

    # TD-0195 — đọc ngưỡng từ ĐÚNG nguồn chiến lược đọc. Ghim một số ở đây
    # sẽ làm phép đếm này lệch khỏi chiến lược ngay lần calibrate đầu tiên,
    # mà lệch theo kiểu vẫn XANH (nó chỉ đếm, không so với chiến lược).
    nguong_zss = float(resolve(load_tool_d_config(), "tier_b.zss_threshold"))

    cao = [b[1] for b in rows4]; thap = [b[2] for b in rows4]
    dong = [b[3] for b in rows4]; vol = [b[4] for b in rows4]
    atr = talib.ATR(np.asarray(cao, float), np.asarray(thap, float), np.asarray(dong, float), 14)
    gia = cao if loai == "dinh" else thap
    dem = 0
    for i in range(K_XAC_NHAN, len(rows4)):
        j = i + K_XAC_NHAN
        if j >= len(rows4) or not la_diem_swing(gia, i, loai=loai):
            continue
        if np.isnan(atr[i]) or dong[i] == 0 or zone_da_bi_huy(gia, i, j, loai=loai):
            continue
        buf = BUF_ZONE_TEST * atr[i] / dong[i]
        zl, zh = (gia[i] * (1 - buf), gia[i] * (1 + buf)) if loai == "dinh" else (gia[i], dong[i])
        v_r = volume_ratio(vol, i_swing=i)
        comp = compression(cao, thap, dong, i_hinh_thanh=i, i_hien_tai=j)
        if v_r is None or comp is None:
            continue
        tc = touch_count(gia, dong, min(zl, zh), max(zl, zh), i_swing=i, t=j, loai=loai)
        if zone_hop_le(zss_value=zss(touch=tc, ty_le_volume=v_r, do_nen=comp),
                       so_touch=tc, tuoi_nen=K_XAC_NHAN, nguong_zss=nguong_zss):
            dem += 1
    return dem


BUF_ZONE_TEST = 0.3  # = BUF_ZONE của chiến lược (§1.1)

#: Nến 4H "chạm p1 → tranche 1" — tìm theo GIÁ TRỊ (phải là DUY NHẤT), không
#: theo offset từ cuối: `test_td0189` cắt đuôi và nối kịch bản riêng sau nến
#: này nên offset −36 của bộ sinh gốc không còn đúng ở đó (đã dính thật).
NEN_4H_CHAM_P1 = (95.50, 95.50, 95.30, 95.40, 1000.0)


def _i_cham_p1(rows4) -> int:
    ung = [k for k, b in enumerate(rows4) if b == pytest.approx(NEN_4H_CHAM_P1)]
    assert len(ung) == 1, f"nến chạm p1 {NEN_4H_CHAM_P1} phải xuất hiện ĐÚNG MỘT lần, thấy {len(ung)}"
    return ung[0]

#: TD-0193 (DR-D4-08 §3 #6) — BỐN nến 1H thay cho `_chia_nho()` của nến 4H
#: "chạm p1". Gộp lại VẪN đúng nến 4H cũ (95.50, 95.50, 95.30, 95.40, 1000) nên
#: mọi phép tính khung 4H (zone, EMA/DG2, TP) KHÔNG đổi; chỉ hình dạng 1H đổi:
#:   b2 = lần CHẠM đầu (low 95,30 ∈ zone ≈ [94,66, 95,34]) đồng thời là nến
#:        REJECTION (range 0,20; bóng dưới 0,15 ≥ 0,5×0,20; đóng 95,45 ≥
#:        95,30 + 0,10) với volume 550 ≥ v_min × MA20(1H) ≈ 240 ⇒ (a VÀ c)
#:        ⇒ C = b2, wait_bars = 0.
#:   b3 = nến ĐẶT lệnh (p1_order = min(zone_high, close(C)) = zone_high ≈ 95,34;
#:        open 95,45 > 95,34 ⇒ limit; low 95,30 ≤ 95,34 ⇒ KHỚP); mọi giá ≤ 95,5
#:        nằm xa DƯỚI nạng TP1 (~96,53) nên TP1 không nổ trước tranche 2/3
#:        (bài học TD-0189 chặng 2b về wick và `--timeframe-detail 5m`).
#: Bản `_chia_nho()` cũ cho nến chạm (95.5, 95.5, 95.3, 95.3) đóng SÁT ĐÁY —
#: không phải rejection ⇒ hệ thống MỚI ra 0 lệnh ⇒ mọi khẳng định về lệnh
#: xanh-vô-nghĩa. Lần thứ BA "fixture đúng hệ thống cũ" (TD-0182, TD-0194).
NEN_1H_CHAM_P1: tuple[tuple[float, float, float, float, float], ...] = (
    (95.50, 95.50, 95.50, 95.50, 150.0),
    (95.50, 95.50, 95.50, 95.50, 150.0),
    (95.50, 95.50, 95.30, 95.45, 550.0),  # CHẠM + rejection + volume ⇒ C
    (95.45, 95.45, 95.30, 95.40, 150.0),  # đặt lệnh tại open, khớp tại 95,34
)


def _rows1_tu_rows4(rows4) -> list[tuple[float, float, float, float, float]]:
    """1H từ 4H: `_chia_nho` cho mọi nến, TRỪ nến "chạm p1" (xem `NEN_1H_CHAM_P1`).

    Đối chứng ngay tại đây (N6): nến bị thay phải là đúng nến 95,30 và bốn
    nến thay phải gộp lại ĐÚNG nến 4H cũ — sai một trong hai thì RAISE, không
    lặng lẽ sinh một chuỗi khác chuỗi mọi ca khác đang tin.
    """
    i = _i_cham_p1(rows4)
    goc = rows4[i]
    gop = (
        NEN_1H_CHAM_P1[0][0], max(b[1] for b in NEN_1H_CHAM_P1),
        min(b[2] for b in NEN_1H_CHAM_P1), NEN_1H_CHAM_P1[-1][3], sum(b[4] for b in NEN_1H_CHAM_P1),
    )
    assert gop == pytest.approx(goc), f"bốn nến 1H gộp thành {gop}, khác nến 4H gốc {goc}"
    rows1: list[tuple[float, float, float, float, float]] = []
    for k, bar in enumerate(rows4):
        rows1.extend(NEN_1H_CHAM_P1 if k == i else _chia_nho(bar, 4))
    return rows1


def _khang_dinh_bo_sinh_co_nen_xac_nhan_3_3b(rows4, rows1) -> None:
    """🔴 ĐỐI CHỨNG THƯỜNG TRỰC thứ hai (TD-0193): zone đáy của bộ sinh phải
    có ít nhất một lần chạm ĐƯỢC XÁC NHẬN theo §3.3b Phương án A — gọi đúng
    `quet_xac_nhan_zone()` sản xuất với cùng RSI/volume_MA mà chiến lược tính.
    Không có ⇒ hệ thống mới ra 0 lệnh và mọi ca dùng bộ sinh xanh-vô-nghĩa."""
    import numpy as np
    import talib
    from tool_d.entry_confirmation import quet_xac_nhan_zone
    from tool_d.zone_detection import K_XAC_NHAN, la_diem_swing, zone_da_bi_huy
    from tool_d.zone_strength import compression, touch_count, volume_ratio, zone_hop_le, zss

    cao4 = [b[1] for b in rows4]; thap4 = [b[2] for b in rows4]
    dong4 = [b[3] for b in rows4]; vol4 = [b[4] for b in rows4]
    atr4 = talib.ATR(np.asarray(cao4, float), np.asarray(thap4, float), np.asarray(dong4, float), 14)
    zones = []
    for i in range(K_XAC_NHAN, len(rows4)):
        j = i + K_XAC_NHAN
        if j >= len(rows4) or not la_diem_swing(thap4, i, loai="day"):
            continue
        if np.isnan(atr4[i]) or dong4[i] == 0 or zone_da_bi_huy(thap4, i, j, loai="day"):
            continue
        buf = BUF_ZONE_TEST * atr4[i] / dong4[i]
        zl, zh = thap4[i] * (1 - buf), thap4[i] * (1 + buf)
        v_r = volume_ratio(vol4, i_swing=i)
        comp = compression(cao4, thap4, dong4, i_hinh_thanh=i, i_hien_tai=j)
        if v_r is None or comp is None:
            continue
        tc = touch_count(thap4, dong4, zl, zh, i_swing=i, t=j, loai="day")
        if zone_hop_le(zss_value=zss(touch=tc, ty_le_volume=v_r, do_nen=comp), so_touch=tc,
                       tuoi_nen=K_XAC_NHAN, nguong_zss=0.5):
            zones.append((j, zl, zh))
    assert zones, "bộ sinh không có zone đáy hợp lệ — đối chứng thứ nhất lẽ ra đã bắt"

    mo1, cao1, thap1, dong1, vol1 = (list(x) for x in zip(*[(b[0], b[1], b[2], b[3], b[4]) for b in rows1]))
    rsi1 = talib.RSI(np.asarray(dong1, float), 14).tolist()
    vma1 = pd.Series(vol1).rolling(20).mean().tolist()
    co = False
    for j, zl, zh in zones:
        k_start = (j + 1) * 4  # nến 1H đầu tiên SAU khi nến 4H j đóng (DR-D4-08 §3 #3)
        kq = quet_xac_nhan_zone(
            mo1, cao1, thap1, dong1, rsi1, vol1, vma1,
            zone_low=zl, zone_high=zh, tu=k_start, den=min(len(rows1), k_start + 160),
            v_min=1.0, loai="day", lan_cham_truoc_khi_xac_nhan=None,
            bat_dieu_kien_c=True, wick_frac=0.5,
        )
        co = co or kq.nen_xac_nhan_that is not None
    assert co, (
        "không zone đáy nào của bộ sinh có lần chạm đầu được XÁC NHẬN §3.3b — "
        "hệ thống mới sẽ ra 0 lệnh, mọi ca dùng bộ sinh này XANH-VÔ-NGHĨA. "
        "Xem NEN_1H_CHAM_P1."
    )


def _khang_dinh_bo_sinh_du_hai_loai_zone() -> None:
    """🔴 ĐỐI CHỨNG THƯỜNG TRỰC — chạy MỌI lần bộ sinh được dùng.

    **Vì sao gắn vào `_sinh_du_lieu` chứ không để thành một ca test riêng:**
    một ca riêng chỉ chạy khi ai đó nhớ giữ nó; gắn ở đây thì mọi file dùng
    chung bộ sinh (`test_td0170`, và tầng TP của TD-0189) đều được che.

    **Vì sao cần:** trong MỘT ngày, bộ sinh này im lặng sai với hệ thống mới
    **hai lần**, và **không lần nào làm đỏ một ca nào**:
      1. TD-0182 — chuỗi 1D là dốc đơn điệu ⇒ `tuoi_trend_nen()` trả `None` ở
         92/92 nến ⇒ **0 lệnh**. Mà `0 lệnh` thì mọi khẳng định về lệnh đều
         **đúng-vô-nghĩa**.
      2. TD-0194 — **0 zone ĐỈNH** ⇒ nhánh *"TP1 lấy từ zone đối diện"* (§5.1)
         không có nguồn dữ liệu ⇒ H-4 = 100% nạng, mọi khẳng định về nhánh
         zone **xanh-vô-nghĩa**.

    Cả hai đều là *"fixture đúng với hệ thống CŨ, im lặng sai với hệ thống
    MỚI"* — không ai viết sai dòng nào. Ca này biến lần thứ ba thành **báo đỏ
    ngay tại bộ sinh**, thay vì chờ ai đó tình cờ đi đo phễu.

    ⚠️ Giới hạn tự khai: nó canh *"có tồn tại zone"*, KHÔNG canh *"zone rơi
    đúng chỗ cần"*. Vế thứ hai do `test_hai_zone_dinh_o_hai_phia_tran_TP`
    canh, và hai vế cố ý tách: cái này là điều kiện SỐNG của mọi ca dùng bộ
    sinh, cái kia là điều kiện riêng của tầng TP.
    """
    rows4 = _bars_4h_co_trend()
    for loai, ten in (("day", "ĐÁY"), ("dinh", "ĐỈNH")):
        assert _dem_zone(rows4, loai) >= 1, (
            f"bộ sinh không cho zone {ten} hợp lệ nào — mọi khẳng định dựa trên "
            f"nhánh {ten} sẽ XANH-VÔ-NGHĨA. Xem docstring hàm này."
        )


def _sinh_du_lieu(datadir: Path) -> None:
    _khang_dinh_bo_sinh_du_hai_loai_zone()
    rows4 = _bars_4h_co_trend()
    rows1 = _rows1_tu_rows4(rows4)
    _khang_dinh_bo_sinh_co_nen_xac_nhan_3_3b(rows4, rows1)
    # 🔴 TD-0182 — NEO MỐC KẾT THÚC, không neo mốc bắt đầu. `TIMERANGE`
    # chỉ phủ 18 ngày CUỐI (phần trước là warmup), nên nối thêm lịch sử
    # vào đầu chuỗi không sinh thêm lệnh nào — miễn là mẫu zone vẫn rơi
    # đúng chỗ cũ trên lịch. Neo mốc bắt đầu thì mẫu zone trôi ra khỏi
    # `TIMERANGE` và backtest ra 0 lệnh vì một lý do HOÀN TOÀN KHÁC với
    # lý do đang sửa — đúng loại nhầm lẫn tốn cả buổi để truy.
    bat_dau = _moc_bat_dau(len(rows1))
    idx1 = pd.date_range(bat_dau, periods=len(rows1), freq="1h", tz="UTC")
    df1 = pd.DataFrame(rows1, columns=["open", "high", "low", "close", "volume"])
    df1.insert(0, "date", idx1)
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    df4 = df1.set_index("date").resample("4h").agg(agg).reset_index()
    df1d = df1.set_index("date").resample("1D").agg(agg).reset_index()
    rows5 = [x for bar in rows1 for x in _chia_nho(bar, 12)]
    df5 = pd.DataFrame(rows5, columns=["open", "high", "low", "close", "volume"])
    df5.insert(0, "date", pd.date_range(bat_dau, periods=len(rows5), freq="5min", tz="UTC"))

    d = datadir / "futures"
    fund = pd.DataFrame({"date": idx1, "open": 0.0, "high": 0.0, "low": 0.0, "close": 0.0, "volume": 0.0})
    # CÙNG chuỗi giá cho cả hai mã: hai lệnh mở đồng thời ⇒ lệnh thứ hai
    # nhìn thấy danh mục KHÔNG rỗng. Đó là điều kiện để đo được §6.8f B2.
    for cap in (CAP, CAP2):
        _ghi_feather(df1, d / f"{cap}-1h-futures.feather")
        _ghi_feather(df1, d / f"{cap}-1h-mark.feather")
        _ghi_feather(df5, d / f"{cap}-5m-futures.feather")
        _ghi_feather(df5, d / f"{cap}-5m-mark.feather")
        _ghi_feather(df4, d / f"{cap}-4h-futures.feather")
        _ghi_feather(df1d, d / f"{cap}-1d-futures.feather")
        _ghi_feather(fund, d / f"{cap}-1h-funding_rate.feather")


def _chay(tmp: Path, chien_luoc: str, *, hai_ma: bool = False) -> dict:
    nhan = f"{chien_luoc}{'_2ma' if hai_ma else ''}"
    datadir, userdir = tmp / "data", tmp / f"userdir_{nhan}"
    if not (datadir / "futures").exists():
        _sinh_du_lieu(datadir)
    (userdir / "strategies").mkdir(parents=True, exist_ok=True)
    cfg = json.loads((REPO_ROOT / "config" / "freqtrade" / "config.json").read_text(encoding="utf-8"))
    cfg["exchange"]["pair_whitelist"] = ["LTC/USDT:USDT", "XRP/USDT:USDT"] if hai_ma else ["LTC/USDT:USDT"]
    cfg["max_open_trades"] = 2 if hai_ma else 1
    cfg["stake_amount"] = 100  # bị custom_stake_amount ghi đè — nếu KHÔNG, ca cỡ lệnh bên dưới đỏ
    cfg["dry_run"] = True
    cfg_path = tmp / f"cfg_{nhan}.json"
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable, "-m", "freqtrade", "backtesting",
            "--config", str(cfg_path), "--datadir", str(datadir), "--userdir", str(userdir),
            "--strategy", chien_luoc, "--strategy-path", str(REPO_ROOT / "user_data" / "strategies"),
            "--timerange", TIMERANGE, "--timeframe-detail", "5m", "--cache", "none", "--export", "trades",
        ],
        capture_output=True, text=True, timeout=900, cwd=REPO_ROOT,
    )
    assert proc.returncode == 0, f"backtest {chien_luoc} thất bại:\n{proc.stdout[-3000:]}\n{proc.stderr[-3000:]}"
    # 🔴 Freqtrade NUỐT exception từ callback (`strategy_safe_wrapper`: log
    # WARNING rồi đi tiếp). Lần chạy đầu của TD-0187: SizingError "stake <
    # min_stake" bị nuốt 12 lần, lệnh mẫu biến mất trong im lặng, rc vẫn 0.
    # Một chốt fail-closed mà bị nuốt là một chốt không tồn tại — nên log
    # sạch là điều kiện của fixture, không phải của riêng một ca.
    log = proc.stdout + proc.stderr
    nuot = [d for d in log.splitlines() if "Strategy caused the following exception" in d]
    assert not nuot, f"{chien_luoc}: {len(nuot)} exception bị Freqtrade nuốt — dòng đầu:\n{nuot[0][:300]}"
    from freqtrade.data.btanalysis import load_backtest_stats

    files = sorted((userdir / "backtest_results").glob("backtest-result-*.zip"))
    assert files, "không có file kết quả"
    kq = load_backtest_stats(files[-1])["strategy"][chien_luoc]
    kq["_log"] = log  # TD-0188 grep dấu vết KET_NAP trên đường chạy thật
    return kq


@pytest.fixture(scope="module")
def tmp_module(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("td0187")


@pytest.fixture(scope="module")
def kq_san_xuat(tmp_module) -> dict:
    return _chay(tmp_module, SAN_XUAT)


@pytest.fixture(scope="module")
def kq_toi_thieu(tmp_module) -> dict:
    return _chay(tmp_module, TOI_THIEU)


@pytest.fixture(scope="module")
def kq_hai_ma(tmp_module) -> dict:
    """Hai mã, `max_open_trades = 2` — lượt DUY NHẤT có danh mục KHÔNG rỗng.

    🔴 Vì sao phải có: với một mã, `dang_mo` luôn rỗng, nên một cài đặt bỏ
    hẳn việc đọc danh mục (`dang_mo=[]`) vẫn cho MỌI ca xanh. Đã phá thật để
    xác nhận: `19 passed` sau khi cắt danh mục — tức bộ test cũ chứng minh
    §6.8f B2 *chạy* nhưng KHÔNG chứng minh nó *đọc đúng thứ cần đọc*.
    """
    return _chay(tmp_module, SAN_XUAT, hai_ma=True)


def _lenh_du_ba_tranche(kq: dict) -> dict:
    ung = [t for t in kq["trades"] if len(_lenh_vao(t)) == 3]
    assert ung, f"không lệnh nào đủ 3 tranche — số tranche: {[len(_lenh_vao(t)) for t in kq['trades']]}"
    return ung[0]



class TestTD0194ZoneDinhChoTangTP:
    """🔴 TD-0194 — bộ sinh phải cho ĐỦ zone đỉnh để tầng TP §5.1 kiểm được.

    Trước bản này: **0 zone đỉnh** trên 910 nến (ứng viên swing 1, qua
    `touch ≥ 1` là 0). Đuôi tăng đơn điệu không bao giờ tạo được cụm
    *chạm-rồi-đóng-DƯỚI-zone* — chiều ĐẢO so với zone đáy.
    """

    def test_co_dung_HAI_zone_dinh_o_HAI_PHIA_tran_TP(self, kq_san_xuat) -> None:
        """🔴 HAI đỉnh, KHÔNG phải một — và đây là chỗ có RĂNG.

        Với **một** đỉnh duy nhất trong tầm, một bản nối hỏng kiểu *"lấy đại
        zone đỉnh nào cũng được, bỏ qua phép lọc `4,0 × R_eff`"* vẫn cho ra
        đúng zone đó ⇒ **xanh giả**. Hai đỉnh ở hai phía trần thì bản hỏng ấy
        sẽ chọn nhầm cái ngoài tầm và bị bắt.

        `R_eff` là **KHOẢNG GIÁ** (v8 dòng 1667 cấm viết "4R"), tính từ chính
        `enter_tag` của lệnh THẬT — không gõ tay, nên đổi bộ sinh thì ca này
        đi theo chứ không đỏ giả.
        """
        rows4 = _bars_4h_co_trend()
        assert _dem_zone(rows4, "dinh") == 2, "cần ĐÚNG hai đỉnh — xem docstring"

        t = _lenh_du_ba_tranche(kq_san_xuat)
        d = json.loads(t["enter_tag"])
        p_avg = (d["p1"] + d["p2"] + d["p3"]) / 3
        r_eff_gia = p_avg - d["sl"]          # KHOẢNG GIÁ, không phải tỉ lệ
        tran = p_avg + 4.0 * r_eff_gia

        trong = CAO_DINH_TRONG_TAM * (1 - 0.004)   # xấp xỉ mép dưới zone
        ngoai = CAO_DINH_NGOAI_TAM * (1 - 0.004)
        assert p_avg < trong < tran, (
            f"đỉnh TRONG tầm phải nằm trong ({p_avg:.3f}, {tran:.3f}), thực tế {trong:.3f}"
        )
        assert ngoai > tran, (
            f"đỉnh NGOÀI tầm phải > {tran:.3f}, thực tế {ngoai:.3f}"
        )

    def test_doi_chung_thuong_truc_co_RANG(self) -> None:
        """Chốt canh chính nó: nếu bộ sinh mất một loại zone thì
        `_khang_dinh_bo_sinh_du_hai_loai_zone()` phải RAISE, không im lặng."""
        with pytest.raises(AssertionError, match="ĐỈNH"):
            rows_khong_dinh = [b for b in _bars_4h_co_trend()]
            for i in (I_DINH_TRONG_TAM, I_DINH_NGOAI_TAM):
                # hạ đỉnh xuống ngang nến dốc ⇒ thôi là swing đỉnh
                rows_khong_dinh[i] = (95.0, 95.1, 94.9, 95.0, 1000.0)
            for loai, ten in (("day", "ĐÁY"), ("dinh", "ĐỈNH")):
                assert _dem_zone(rows_khong_dinh, loai) >= 1, (
                    f"bộ sinh không cho zone {ten} hợp lệ nào"
                )


class TestKhongPassRong:
    def test_co_lenh_va_co_lenh_du_ba_tranche(self, kq_san_xuat) -> None:
        assert len(kq_san_xuat["trades"]) >= 1, "0 lệnh — dữ liệu hỏng hoặc ADX(1D) < 20 chặn hết"
        _lenh_du_ba_tranche(kq_san_xuat)


class TestDonBay:
    def test_leverage_bang_L_exchange_khong_phai_1x(self, kq_san_xuat) -> None:
        """Trước file này không ai cài `leverage()` ⇒ 1x (MT-16 triệu chứng 5)."""
        from tool_d.config.loader import load_tool_d_config, resolve

        l_exchange = float(resolve(load_tool_d_config(), "tier_a.L_exchange"))
        for t in kq_san_xuat["trades"]:
            assert float(t["leverage"]) == pytest.approx(l_exchange), t["leverage"]
        assert l_exchange != 1.0, "cấu hình đang 1x thì ca này không phân biệt được gì"


class TestTiTrongTrancheThat:
    def test_ba_tranche_bang_nhau_KHONG_phai_1_1_2(self, kq_san_xuat) -> None:
        """🔴 Con số MT-16 đo được là 10 / 10 / 20. Ở đây phải là 1 : 1 : 1."""
        t = _lenh_du_ba_tranche(kq_san_xuat)
        cost = [float(o["cost"]) for o in _lenh_vao(t)]
        ty_le = [c / cost[0] for c in cost]
        assert all(abs(r - 1.0) < 0.01 for r in ty_le), f"tỉ lệ cost tranche = {ty_le} (MT-16 là [1, 1, 2])"


class TestD01TrenDuongSanXuat:
    def test_cost_tranche1_bang_N_full_nhan_w1_voi_R_eff_tu_chinh_tag(self, kq_san_xuat) -> None:
        """Rủi ro kế hoạch = rho × E_D = 1,875 USDT, cỡ lệnh biến theo 1/R_eff.
        `R_eff` lấy từ ĐÚNG enter_tag của lệnh — không dựng tay."""
        from tool_d.config.loader import load_tool_d_config, resolve

        cfg = load_tool_d_config()
        e_d = float(resolve(cfg, "tier_a.E_D"))
        rho = float(resolve(cfg, "tier_a.rho_pct")) / 100.0
        w = [float(x) for x in resolve(cfg, "tier_frozen.w_tranche.value")]

        t = _lenh_du_ba_tranche(kq_san_xuat)
        tag = json.loads(t["enter_tag"])
        p_avg = (tag["p1"] + tag["p2"] + tag["p3"]) / 3
        r_eff = (p_avg - tag["sl"]) / p_avg
        # Sáu hệ số §6.2 trong kịch bản này: zss đọc từ CHÍNH tag (không dựng
        # tay); regime = 1.0 vì dữ liệu 85 ngày uptrend cho ADX(1D) ≥ 25 (nếu
        # ca này đỏ ở hệ số 0,7 thì dữ liệu không mạnh như thiết kế — đó là
        # thông tin, không phải chỗ để nới); corr/dd/deploy = 1.0 vì chỉ một
        # vị thế, dd = 0, không vị thế khác; edge = 1.0 (chưa lệnh live).
        from tool_d.sizing import mult_zss

        mult = 1.0 * mult_zss(float(tag["zs"])) * 1.0 * 1.0 * 1.0 * 1.0
        assert 0.5 <= mult <= 1.0
        n_full = rho * mult * e_d / r_eff
        cost = [float(o["cost"]) for o in _lenh_vao(t)]
        # dung sai 1%: làm tròn khối lượng theo amount_precision + giá khớp lệch p_i một bước làm tròn
        assert cost[0] == pytest.approx(n_full * w[0], rel=0.01), (cost[0], n_full * w[0], r_eff)
        assert sum(cost) == pytest.approx(n_full, rel=0.01)
        # và tuyệt đối KHÔNG phải cỡ placeholder 10 USDT của config.json
        assert cost[0] > 15.0

    def test_stake_la_ky_quy_bang_cost_chia_L(self, kq_san_xuat) -> None:
        """🔴 TD-0189 chặng 2b — `t["stake_amount"]` KHÔNG còn dùng được làm
        mẫu số: từ khi TP1 nối vào, đó là stake HIỆN TẠI (sau khi đã trừ
        phần đã chốt lời), không phải tổng ba tranche lúc đỉnh. Dùng
        `t["max_stake_amount"]` — đỉnh `stake_amount` trong suốt vòng đời
        lệnh, đạt được ngay SAU khi tranche 3 khớp và TRƯỚC bất kỳ exit
        nào — vẫn đúng `≈ 3 × stake tranche 1` vì ba tranche cost bằng
        nhau (`TestTiTrongTrancheThat`)."""
        t = _lenh_du_ba_tranche(kq_san_xuat)
        o1 = _lenh_vao(t)[0]
        stake1 = float(o1.get("stake_amount") or o1.get("ft_stake_amount") or 0.0) or float(t["max_stake_amount"]) / 3
        assert stake1 * float(t["leverage"]) == pytest.approx(float(o1["cost"]), rel=0.02)


class TestTagMangDuKhoaMoi:
    def test_enter_tag_co_zs_t4_sw_va_t4_la_UP(self, kq_san_xuat) -> None:
        t = _lenh_du_ba_tranche(kq_san_xuat)
        tag = json.loads(t["enter_tag"])
        for k in ("zl", "zh", "p1", "p2", "p3", "sl", "zs", "t4", "sw"):
            assert k in tag, f"thiếu {k}"
        assert 0.0 < tag["zs"] <= 1.0
        # Không đoán hướng — TÍNH LẠI độc lập từ chính chuỗi 4H tổng hợp tại
        # nến đã đóng ngay trước giờ mở lệnh (bản đầu đoán "UP" và sai: cú rơi
        # 100→95 trong 4 nến kéo EMA20 xuống dưới EMA50 ⇒ DOWN là đúng dữ liệu).
        import numpy as np
        import talib
        from tool_d.trend_context import trend_dir_tai

        rows4 = _bars_4h_co_trend()
        dong = np.asarray([b[3] for b in rows4], dtype=float)
        # 🔴 Mốc đầu SUY RA từ `_moc_bat_dau()`, KHÔNG chép hằng số. Bản
        # trước viết cứng `"2025-01-01"`; TD-0182 kéo dài lịch sử làm mốc
        # thật lùi về 2024-11, nên chỉ số tính ra trỏ vào GIỮA đoạn dốc —
        # sai nến, mà vẫn xanh vì nến sai tình cờ cũng UP.
        t0 = _moc_bat_dau(len(rows4) * 4)
        mo = pd.Timestamp(t["open_date"])
        idx_nen_dong_truoc = int((mo - t0) / pd.Timedelta(hours=4)) - 1
        assert 0 <= idx_nen_dong_truoc < len(rows4), (
            f"chỉ số nến {idx_nen_dong_truoc} nằm ngoài chuỗi {len(rows4)} nến — "
            "mốc thời gian và bộ sinh đã lệch nhau"
        )
        ema_f, ema_s = talib.EMA(dong, timeperiod=20), talib.EMA(dong, timeperiod=50)
        # tín hiệu sinh ở nến j (đóng trước lệnh); trend ghi vào tag là trend TẠI j
        ky_vong = {trend_dir_tai(ema_f, ema_s, i) for i in (idx_nen_dong_truoc, idx_nen_dong_truoc - 1)}
        assert tag["t4"] in ky_vong, (tag["t4"], ky_vong, idx_nen_dong_truoc)
        assert len(t["enter_tag"]) <= 255, "order tag Binance giới hạn 255 ký tự"

    def test_moi_tag_tranche_2_3_khop_tranche_1(self, kq_san_xuat) -> None:
        """L-Z49 giữ nguyên trên chiến lược sản xuất."""
        t = _lenh_du_ba_tranche(kq_san_xuat)
        for o in _lenh_vao(t):
            assert o.get("ft_order_tag") == t["enter_tag"]


class TestCungZoneVoiMinimal:
    def test_san_xuat_va_toi_thieu_cho_CUNG_zone_tren_CUNG_du_lieu(self, kq_san_xuat, kq_toi_thieu) -> None:
        """Phần zone của `ZoneAbsorption` là bản chép của Minimal — canh nó không trôi."""
        assert kq_toi_thieu["trades"], "Minimal không vào lệnh trên dữ liệu này — bộ sinh đã lệch khỏi L-Z49"
        ta, tb = _lenh_du_ba_tranche(kq_san_xuat), _lenh_du_ba_tranche(kq_toi_thieu)
        # Cùng zone ⇒ cùng NGÀY mở và sản xuất mở KHÔNG SỚM HƠN Minimal. Bản
        # trước đòi cùng GIỜ — đúng khi cả hai vào ngay tại nến xác nhận zone;
        # TD-0193 (DR-D4-08) cho sản xuất vào tại nến xác nhận C của §3.3b
        # (sau lần chạm đầu), Minimal thì không có §3.3b — ca này ĐỎ ĐÚNG rồi
        # được SỬA khẳng định, không xoá (tiền lệ TD-0150). Lần chạy đầu
        # ZoneAbsorption KHÔNG có lệnh này (bị min_stake chặn trong im lặng)
        # mà chỉ có các zone ở đuôi — so tag của "lệnh đủ 3 tranche đầu tiên"
        # thôi thì không phát hiện được sự vắng mặt đó.
        assert ta["open_date"][:10] == tb["open_date"][:10], (ta["open_date"], tb["open_date"])
        assert ta["open_date"] >= tb["open_date"], (ta["open_date"], tb["open_date"])
        a, b = json.loads(ta["enter_tag"]), json.loads(tb["enter_tag"])
        # p1 KHÔNG so: Minimal = min(zone_high, close4H[j]); sản xuất = p1_order
        # §3.5 = min(zone_high, close(C)). Cùng zone thì bốn mức còn lại phải khớp.
        for k in ("zl", "zh", "p2", "p3", "sl"):
            assert a[k] == pytest.approx(b[k], abs=1e-9), (k, a[k], b[k])
        assert a["p1"] <= a["zh"] + 1e-9

    def test_minimal_van_1x_va_1_1_2_de_doi_chung(self, kq_toi_thieu) -> None:
        """Đối chứng âm: chính Minimal trên cùng dữ liệu vẫn cho 1x và 1:1:2 —
        tức khác biệt đo được ở các ca trên là do TẦNG ĐỊNH CỠ, không do dữ liệu."""
        t = [x for x in kq_toi_thieu["trades"] if len(_lenh_vao(x)) == 3]
        assert t, "Minimal không có lệnh đủ 3 tranche"
        cost = [float(o["cost"]) for o in _lenh_vao(t[0])]
        assert float(t[0]["leverage"]) == pytest.approx(1.0)
        assert cost[2] / cost[0] == pytest.approx(2.0, rel=0.02), f"Minimal phải ra 1:1:2, đo được {[c / cost[0] for c in cost]}"


class TestTD0188KetNapChayTrenDuongThat:
    """🔴 TD-0188 — §6.8f Bước 2 phải ĐƯỢC GỌI, không chỉ tồn tại.

    Bài học TD-0168 ở đúng chiều đã cắn dự án một lần: 33 phép kiểm canh
    một hàm mà đường sản xuất chưa từng gọi. `tests/unit/test_admission.py`
    chứng minh phép kiểm ĐÚNG; lớp này chứng minh nó CHẠY — bằng dấu vết
    `KET_NAP` mà `confirm_trade_entry` ghi ra trong chính lượt backtest.

    🔴 **Freqtrade BỌC log theo bề rộng terminal (~80 cột), nên MỘT bản ghi
    log KHÔNG phải một dòng vật lý.** Bản đầu của lớp này parse từng dòng và
    đỏ vì `dien_giai()` bị cắt ngay sau "KẾT NẠP" — chuỗi thật dài 77 ký tự,
    kiểm bằng cách gọi thẳng hàm trong container. Lỗi của TEST, không phải
    của máy. Nên mọi phép so ở đây chạy trên log đã **gộp khoảng trắng**.
    """

    @staticmethod
    def _log_phang(kq: dict) -> str:
        """Gộp toàn bộ log thành một chuỗi, chuẩn hoá khoảng trắng — vô hiệu
        hoá phép bọc dòng của Freqtrade."""
        return " ".join(kq["_log"].split())

    def test_co_dau_vet_KET_NAP_trong_log_backtest(self, kq_san_xuat) -> None:
        phang = self._log_phang(kq_san_xuat)
        assert "KET_NAP" in phang, "confirm_trade_entry không gọi kiem_ket_nap"
        assert "KẾT NẠP" in phang

    def test_so_lan_KET_NAP_khong_it_hon_so_lenh(self, kq_san_xuat) -> None:
        """Không lệnh nào lọt qua mà không đi qua cửa kết nạp."""
        nhan = self._log_phang(kq_san_xuat).count("KẾT NẠP")
        assert nhan >= len(kq_san_xuat["trades"]), (nhan, len(kq_san_xuat["trades"]))

    def test_tran_ghi_trong_log_dung_CAU_HINH_THAT(self, kq_san_xuat) -> None:
        """Trần đọc từ `tool_d_config.yaml` THẬT (425 = 0,85 × 500; 40 = 8% ×
        500), không phải hằng số dựng tay trong test."""
        import re

        from tool_d.admission import TRAN_MARGIN_TREN_E_D
        from tool_d.config.loader import load_tool_d_config, resolve

        cfg = load_tool_d_config()
        e_d = float(resolve(cfg, "tier_a.E_D"))
        m = re.search(r"rủi ro [\d.]+/([\d.]+) · margin [\d.]+/([\d.]+)", self._log_phang(kq_san_xuat))
        assert m, "không parse được dấu vết KET_NAP"
        assert float(m.group(1)) == pytest.approx(float(resolve(cfg, "tier_a.daily_loss_budget_pct")) / 100.0 * e_d)
        assert float(m.group(2)) == pytest.approx(TRAN_MARGIN_TREN_E_D * e_d)


class TestTD0188DocDanhMucTHAT:
    """🔴 Phép kiểm kết nạp phải đọc DANH MỤC THẬT, không phải danh sách rỗng.

    `TestTD0188KetNapChayTrenDuongThat` chứng minh cửa kết nạp được GỌI; lớp
    này chứng minh nó được gọi với ĐÚNG đầu vào. Hai câu khác nhau, và phép
    phá `dang_mo=[]` chỉ bị bắt bởi câu thứ hai.
    """

    @staticmethod
    def _phang(kq: dict) -> str:
        return " ".join(kq["_log"].split())

    def test_co_lenh_tren_CA_HAI_ma(self, kq_hai_ma) -> None:
        """Guard PASS RỖNG: mọi khẳng định dưới đây vô nghĩa nếu chỉ một mã
        vào lệnh."""
        cap = {t["pair"] for t in kq_hai_ma["trades"]}
        assert cap == {"LTC/USDT:USDT", "XRP/USDT:USDT"}, cap

    def test_co_lan_ket_nap_thay_danh_muc_KHONG_rong(self, kq_hai_ma) -> None:
        """🔴 Ca bắt được phép phá `dang_mo=[]`. Với danh mục rỗng vĩnh viễn,
        chuỗi "1 vị thế trước đó" KHÔNG BAO GIỜ xuất hiện."""
        phang = self._phang(kq_hai_ma)
        assert "KET_NAP" in phang
        assert "(1 vị thế trước đó)" in phang, "cửa kết nạp luôn thấy danh mục rỗng"

    def test_tong_margin_cong_don_theo_so_vi_the(self, kq_hai_ma) -> None:
        """Tổng margin ở lần kết nạp thứ hai phải LỚN HƠN lần đầu — bằng
        chứng số học rằng vị thế cũ thực sự được cộng vào."""
        import re

        phang = self._phang(kq_hai_ma)
        mau = re.compile(r"margin ([\d.]+)/[\d.]+ \((\d+) vị thế trước đó\)")
        theo_so_vi_the: dict[int, float] = {}
        for m in mau.finditer(phang):
            theo_so_vi_the.setdefault(int(m.group(2)), float(m.group(1)))
        assert 0 in theo_so_vi_the and 1 in theo_so_vi_the, theo_so_vi_the
        assert theo_so_vi_the[1] > theo_so_vi_the[0], theo_so_vi_the
