"""PHẦN 5 §5.1 — chốt lời (TD-0189, MT-17, DR-D4-04 §4).

Hàm THUẦN, không biết gì về Freqtrade. Phần nối vào `custom_exit` là
chặng 2, làm sau khi phiên sở hữu `ZoneAbsorption.py` commit xong.

Ba mảnh của §5.1, đúng thứ tự spec dựng:

  TP1  = zone đối diện gần nhất, TRỪ HAO `tp1_haircut_pct` — chốt 50%.
  TP2  = trail bằng ATR(14,1H) × `tp2_trail_atr` sau khi TP1 chạm.
  nạng = khi không có zone đối diện trong `tp_fallback_dist_r × R_eff`
         thì dùng `p_avg + tp_fallback_target_r × R_eff`, gắn tag
         `tp_source: "fallback_r_multiple"`.

🔴 ĐƠN VỊ — chỗ dễ sai nhất của cả file. Spec (dòng 1670) nói hai bội
số 4.0/1.5 nhân với `R_eff`, và `R_eff` ở đó là một **KHOẢNG GIÁ**.
Nhưng `KeHoachTranche.r_eff_plan` trong `trade_plan.py` là một **TỈ LỆ**
(`(p_avg − sl) / p_avg`). Hai đại lượng khác đơn vị mang tên gần giống
nhau — đúng lớp lỗi §5.1 tự cảnh báo và `L-Z48c` sinh ra để chặn. Nên
mọi phép đổi đi qua `khoang_r_eff()`, không nhân trực tiếp ở đâu khác.

🔴 RÀNG BUỘC CHO CHẶNG 2, đo bởi phiên `-94` ở TD-0171 (`7ee9006`) —
ghi ở đây vì nó vô hình với mọi hàm trong file này. TP1 chốt **50% vị
thế**, nên một lệnh sinh ra HAI đại lượng phải qua sàn min-notional,
không phải một: lệnh thoát một phần, và phần vị thế CÒN LẠI.

Và **không có "một cái sàn"** — Freqtrade truyền một hằng `stoploss`
khác nhau ở mỗi đường chạy, nên phần dư có sàn RIÊNG, lại khác giữa
backtest và live:

    backtesting.py:723   phần dư backtest   stoploss −0,1   sàn 5,83
    freqtradebot.py:846  phần dư live       stoploss −0,99  sàn 2,50

tức **backtest chặt hơn live 2,3 lần ở đúng nhánh này**, ngược chiều
với đường vào lệnh (ở đó live mới là bên chặt hơn, sàn 7,50). Chặng 2
chứng minh trên fill backtest thật thì đi qua **5,83**, KHÔNG phải 7,50.

⚠️ Đòn bẩy **triệt tiêu ở đường vào lệnh nhưng KHÔNG triệt tiêu ở đường
phần dư**: `remaining = (trade.amount − amount) × rate` là NOTIONAL ở
cả hai, nhưng sàn live bị chia `trade.leverage` còn sàn backtest thì
không. Câu chặn *"đại lượng này có NHÌN THẤY thứ tôi sắp đổi không?"*
ở đây trả lời CÓ.

Ca cắn KHÔNG phải ca biên, nhưng ⚠️ **con số cụ thể ĐỔI THEO `E_D`
(DR-D4-05), đừng ghim một giá trị `E_D` vào chặng 2** — ở `E_D = 500`
(giá trị cũ), Π `mult_*` = 0,434, zone 3% ⇒ tranche 1 = 9,04 ⇒ nửa còn
lại 4,52 < 5,83 ⇒ phần dư rớt sàn; ở `E_D = 750` (chốt mới, `7972c4f`)
cùng ca đó **qua sàn** (6,78 > 5,83). Nhánh vẫn cắn thật ở zone rộng
hơn hoặc `Π mult_*` thấp hơn — chỉ là ví dụ minh hoạ phải ĐỌC TỪ
CẤU HÌNH lúc viết test chặng 2, không phải một con số chép tay ở đây.
Và `backtesting.py:1173` là một `if` KHÔNG có `else`: dưới sàn thì rơi
thẳng qua, không log, không ngoại lệ. Hệ quả nặng hơn ca vào lệnh —
lệnh vào biến mất thì bảng kết quả thiếu một dòng, còn **chốt lời
biến mất thì lệnh vẫn nằm đó chạy tiếp tới SL hoặc DG8**, tức tầng TP
im lặng không tồn tại trong khi mọi chỉ số vẫn có số để in.

🔴 Sàn để so KHÔNG phải sàn của một đường chạy riêng lẻ — `-94`
(`DR-D4-05`, `08afba1`) dựng `notional.kiem_san_tool_d()`: sàn Tool D
là **`max` sàn của MỌI đường chạy** (backtest/live × vào lệnh/tranche
2-3/phần dư), cố ý CHẶT HƠN Freqtrade để backtest và live hành xử
giống nhau. Chặng 2 GỌI `notional.kiem_san_tool_d(f, notional_usdt=...,
strategy_stoploss=...)`, KHÔNG gọi `san_min_notional_freqtrade()` một
đường lẻ và KHÔNG viết bản thứ hai — hai bản sao của cùng một luật sàn
là cơ chế đã gây lệch số của v5. Kết quả trả `KetQuaSan` có `.dat`,
`.san_usdt`, `.ve_thang`, `.ly_do` — **`.ly_do` PHẢI được ghi vào
Decision Log khi từ chối**, không được im lặng bỏ qua.

📊 Phân bố tranche ảnh hưởng trực tiếp thiết kế TP2 (đo bởi `-f4` trên
dữ liệu thật, 08/09-09/09): chỉ **~21%** số lệnh bơm đủ ba tranche,
**41%** dừng ở MỘT tranche. TP2 trail sau TP1 phần lớn chạy trên một
vị thế chỉ có một tranche — đọc kèm mọi kết quả D4, không phải ca hiếm.

🔴 CẢNH BÁO CRASH, đo bởi phiên `-f4` trên DỮ LIỆU THẬT (TD-0182, chưa
commit): `zone_valid_4h` mang `NaN` ở vùng warmup của khung informative;
pandas TỪ CHỐI dùng một mảng có `NaN` làm mặt nạ boolean ⇒ backtest
CRASH thẳng, không phải một `False` an toàn. Bộ sinh dữ liệu tổng hợp
(fixture) không có vùng warmup đó nên KHÔNG bao giờ chạm lỗi này — đúng
hình dạng *"fixture đúng với hệ thống CŨ, im lặng sai với hệ thống
MỚI"* đã gặp ở D3.5. `custom_exit()` của chặng 2 cũng đọc cột
informative (giá zone đối diện, ATR 1H) — mọi cột đọc qua `_df_4h()`
hay tương đương PHẢI qua `math.isnan()` trước khi dùng làm điều kiện,
không được dùng thẳng trong so sánh/mặt nạ. Test chặng 2 phải dùng dữ
liệu có vùng warmup thật, không phải fixture tổng hợp sạch NaN.

🔒 `tp_fallback_dist_r` và `tp_fallback_target_r` ĐÓNG BĂNG, 0 trial
(spec dòng 1674-1682). `frozen_rationale` của chính spec: nạng dự phòng
KHÔNG phải nguồn edge — *"nếu phải tune nó để hệ thống có lãi, nghĩa là
TP CHÍNH đang hỏng — đó là L2, xử bằng ablation arm mới, KHÔNG bằng
cách tune ngưỡng của nạng"*. Vòng khép kín ba mảnh: đóng băng nạng →
đo tần suất dùng nạng (`ty_le_dung_nang()`, chỉ số H-4) → vượt 40% thì
xét lại CẤU TRÚC. Test khoá TD-0189 ghim cả hai khoá **không được**
nằm trong `tier_b`: dời sang đó là quyết định N 114 → 126, +12 trial,
rào DSR 3,0777 → 3,1101 — phải là một DR có ý thức, không phải một
dòng sửa lặng lẽ.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from tool_d.config.loader import ToolDConfig, resolve

# §5.1 — "chốt 50% vị thế tại đây". Không phải tham số: spec viết thẳng
# con số, không mang dấu [CẦN CALIBRATE], không có khoá cấu hình nào.
TY_LE_CHOT_TP1 = 0.5

TP_SOURCE_ZONE = "zone_doi_dien"
TP_SOURCE_NANG = "fallback_r_multiple"  # chuỗi tag do spec dòng 1668 quy định


class TakeProfitError(ValueError):
    """Không tính được mức chốt lời.

    Fail-closed, và cố ý KHÁC "không có zone đối diện" (ca đó có đường
    xử riêng là nạng). Đây là *không đo được* — N6 cấm gộp vào một giá
    trị bình thường. Cùng chốt với `TrancheGateError` của DG5.
    """


@dataclass(frozen=True)
class ThamSoTP:
    """Bốn con số của §5.1, đọc từ cấu hình — không hằng số lậu."""

    tp1_haircut_pct: float
    tp2_trail_atr: float
    tp_fallback_dist_r: float
    tp_fallback_target_r: float


# 🔑 ĐIỂM BẢN LỀ của phương án (a) — chủ dự án chốt 08/09/2026.
# Hai khoá nạng hiện sống trong khối `diag_thresholds`, một khối TRỘN
# hai loại: `time_stop_band`/`tp_fallback_max_frac` là ngưỡng chẩn
# đoán thật, còn `tp_fallback_dist_r`/`_target_r` điều khiển hành vi
# giao dịch. Khối đó là bản chép NGUYÊN VĂN spec dòng 2369-2372 nên
# KHÔNG dời (N1: cấu hình không tự rời khỏi chữ spec khi chữ đó không
# sai). Gom cả bốn đường dẫn vào ĐÚNG MỘT chỗ ở đây: nếu về sau có DR
# tách khoá thì sửa đúng bảng này, không lần theo cả file.
DUONG_DAN_THAM_SO = {
    "tp1_haircut_pct": "tier_b.tp1_haircut_pct",
    "tp2_trail_atr": "tier_frozen.tp2_trail_atr.value",
    "tp_fallback_dist_r": "tier_frozen.diag_thresholds.value.tp_fallback_dist_r",
    "tp_fallback_target_r": "tier_frozen.diag_thresholds.value.tp_fallback_target_r",
}


def _so_duong(ten: str, gia_tri: object) -> float:
    if not isinstance(gia_tri, (int, float)) or isinstance(gia_tri, bool):
        raise TakeProfitError(f"{ten} phải là số, nhận {gia_tri!r}")
    so = float(gia_tri)
    if math.isnan(so):
        raise TakeProfitError(
            f"{ten} không đọc được (NaN) — 'không đo được' KHÁC 'bằng 0'; "
            "bên gọi phải xử tường minh (N6)"
        )
    if so <= 0:
        raise TakeProfitError(f"{ten} phải dương, nhận {so}")
    return so


def doc_tham_so_tp(cfg: ToolDConfig) -> ThamSoTP:
    """Đọc bốn tham số §5.1 qua `resolve()` — cách DUY NHẤT được phép (N4).

    Thiếu bất kỳ khoá nào thì `resolve` raise `KeyError`: một mức chốt
    lời tính bằng số mặc định nào đó là thứ không ai duyệt.
    """
    doc = {ten: resolve(cfg, dotted) for ten, dotted in DUONG_DAN_THAM_SO.items()}

    haircut = doc["tp1_haircut_pct"]
    if not isinstance(haircut, (int, float)) or isinstance(haircut, bool):
        raise TakeProfitError(f"tp1_haircut_pct phải là số, nhận {haircut!r}")
    haircut = float(haircut)
    if math.isnan(haircut) or not 0.0 <= haircut < 100.0:
        raise TakeProfitError(
            f"tp1_haircut_pct phải trong [0, 100) phần trăm, nhận {haircut}"
        )

    return ThamSoTP(
        tp1_haircut_pct=haircut,
        tp2_trail_atr=_so_duong("tp2_trail_atr", doc["tp2_trail_atr"]),
        tp_fallback_dist_r=_so_duong("tp_fallback_dist_r", doc["tp_fallback_dist_r"]),
        tp_fallback_target_r=_so_duong(
            "tp_fallback_target_r", doc["tp_fallback_target_r"]
        ),
    )


def khoang_r_eff(*, p_avg: float, r_eff_plan: float) -> float:
    """Đổi `r_eff_plan` (TỈ LỆ) sang `R_eff` (KHOẢNG GIÁ) — điểm đổi đơn
    vị DUY NHẤT của module.

    `trade_plan.tinh_ke_hoach()` trả `r_eff_plan = (p_avg − sl) / p_avg`;
    hai bội số của §5.1 nhân với khoảng giá. Nhân thẳng vào tỉ lệ ra một
    số nhỏ hơn giá hàng nghìn lần mà vẫn là số dương trông hợp lý — sai
    im lặng, không có ngoại lệ nào nổ.
    """
    gia = _so_duong("p_avg", p_avg)
    ti_le = _so_duong("r_eff_plan", r_eff_plan)
    return gia * ti_le


def tp1_tu_zone(
    *, p_avg: float, gia_zone_doi_dien: float, tp1_haircut_pct: float
) -> float:
    """TP1 = `p_avg` + (1 − haircut) × (zone − `p_avg`), hướng LONG.

    🔑 DIỄN GIẢI, ghi ra để cãi lại được: spec viết *"zone đối diện gần
    nhất, trừ hao 20%"* mà không nói trừ hao trên đại lượng nào. Trừ
    trên KHOẢNG CÁCH tới zone (lấy 80% quãng đường) là cách đọc duy
    nhất mạch lạc — trừ 20% trên GIÁ zone thì với một zone cách 3% mức
    chốt rơi xuống dưới cả giá vào lệnh, tức lệnh thắng thành lệnh lỗ.
    Lý do spec nêu (*"đóng một phần TRƯỚC KHI chạm"*) khớp cách đọc này.
    """
    gia = _so_duong("p_avg", p_avg)
    zone = _so_duong("gia_zone_doi_dien", gia_zone_doi_dien)
    if math.isnan(tp1_haircut_pct) or not 0.0 <= tp1_haircut_pct < 100.0:
        raise TakeProfitError(
            f"tp1_haircut_pct phải trong [0, 100) phần trăm, nhận {tp1_haircut_pct}"
        )
    if zone <= gia:
        raise TakeProfitError(
            f"zone đối diện (LONG) phải NẰM TRÊN p_avg: zone={zone}, p_avg={gia} "
            "— một zone ở dưới là zone cùng chiều, không phải zone đối diện"
        )
    return gia + (1.0 - tp1_haircut_pct / 100.0) * (zone - gia)


@dataclass(frozen=True)
class KeHoachChotLoi:
    tp1_gia: float
    tp_source: str
    khoang_r_eff_gia: float
    tran_tim_zone_gia: float
    ty_le_chot_tp1: float = TY_LE_CHOT_TP1

    @property
    def dung_nang(self) -> bool:
        return self.tp_source == TP_SOURCE_NANG


def chon_muc_tp1(
    *,
    p_avg: float,
    r_eff_plan: float,
    gia_cac_zone_doi_dien: Sequence[float],
    tham_so: ThamSoTP,
) -> KeHoachChotLoi:
    """§5.1 đầy đủ: zone đối diện gần nhất trong tầm, nếu không thì nạng.

    `gia_cac_zone_doi_dien` là giá các zone `loai="dinh"` CÒN HỢP LỆ do
    tầng gọi lọc sẵn — module này không dựng lại `zone_detection`.

    Biên: zone cách ĐÚNG BẰNG `tp_fallback_dist_r × R_eff` vẫn tính là
    "trong tầm", vì spec loại bằng chữ *"> 4 × R_eff"*. Cùng quy ước
    biên với DG4 (*"≤ 8 nến"*).
    """
    khoang = khoang_r_eff(p_avg=p_avg, r_eff_plan=r_eff_plan)
    tran = tham_so.tp_fallback_dist_r * khoang

    for z in gia_cac_zone_doi_dien:
        if not isinstance(z, (int, float)) or isinstance(z, bool) or math.isnan(z):
            raise TakeProfitError(
                f"giá zone đối diện không đọc được: {z!r} — bỏ qua lặng lẽ sẽ "
                "biến 'không đo được' thành 'không có zone', tức âm thầm dùng nạng"
            )

    trong_tam = [float(z) for z in gia_cac_zone_doi_dien if float(z) - p_avg <= tran]
    gan_nhat = min((z for z in trong_tam if z > p_avg), default=None)

    if gan_nhat is None:
        return KeHoachChotLoi(
            tp1_gia=p_avg + tham_so.tp_fallback_target_r * khoang,
            tp_source=TP_SOURCE_NANG,
            khoang_r_eff_gia=khoang,
            tran_tim_zone_gia=tran,
        )

    return KeHoachChotLoi(
        tp1_gia=tp1_tu_zone(
            p_avg=p_avg,
            gia_zone_doi_dien=gan_nhat,
            tp1_haircut_pct=tham_so.tp1_haircut_pct,
        ),
        tp_source=TP_SOURCE_ZONE,
        khoang_r_eff_gia=khoang,
        tran_tim_zone_gia=tran,
    )


def tp2_muc_trail(
    *, gia_cao_nhat_sau_tp1: float, atr_1h: float, tp2_trail_atr: float
) -> float:
    """TP2 §5.1 — trail `ATR(14,1H) × tp2_trail_atr` dưới đỉnh kể từ TP1.

    Chỉ có nghĩa SAU khi TP1 chạm; bên gọi chịu trách nhiệm điều kiện đó.
    DG8 vẫn áp dụng KHÔNG ĐIỀU KIỆN kể cả khi TP2 đang trail (câu hỏi mở
    #11) — không xử ở đây, ghi ra để chặng 2 không quên.
    """
    dinh = _so_duong("gia_cao_nhat_sau_tp1", gia_cao_nhat_sau_tp1)
    atr = _so_duong("atr_1h", atr_1h)
    he_so = _so_duong("tp2_trail_atr", tp2_trail_atr)
    muc = dinh - he_so * atr
    if muc <= 0:
        raise TakeProfitError(
            f"mức trail ra số không dương ({muc}) — ATR({atr}) quá lớn so với "
            f"đỉnh ({dinh}); trả về sẽ thành một mức thoát không bao giờ chạm"
        )
    return muc


def ty_le_dung_nang(tp_sources: Sequence[str]) -> float:
    """Chỉ số H-4 (§11b.2) — tỉ lệ lệnh dùng nạng. Vượt 0,40 ⇒ phân loại L2.

    🔴 Danh sách RỖNG thì RAISE, không trả 0.0. "Chưa có lệnh nào" và
    "có lệnh nhưng không lệnh nào dùng nạng" là hai sự thật khác hẳn, và
    0.0 là con số ĐẠT đẹp nhất có thể — đúng thứ N6 cấm.
    """
    if not tp_sources:
        raise TakeProfitError(
            "chưa có lệnh nào để tính H-4 — trạng thái là `pending`, "
            "KHÔNG phải 0.0 (N6)"
        )
    la = set(tp_sources) - {TP_SOURCE_ZONE, TP_SOURCE_NANG}
    if la:
        raise TakeProfitError(f"tp_source lạ: {sorted(la)}")
    return sum(1 for s in tp_sources if s == TP_SOURCE_NANG) / len(tp_sources)
