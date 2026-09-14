"""TD-0246 — tham số `tier_b` nào ĐANG GÁNH VIỆC trên arm ứng viên `Z0-T1`?

🔴 **Vì sao việc này đứng TRƯỚC `TD-0184`** (chủ dự án duyệt 14/09/2026):
`param_status.yaml` khai **12/12** tham số `tier_b` là `FROZEN` + `chua_calibrate`.
Kiểm được **4** lời khai, và **1 trong 4 là SAI**: `dg7_funding_frac` khai *"DG7 chỉ
áp cho SHORT nên chưa có đường chạy nào chạm tới"* trong khi nó **kết thúc 19,4%
số lệnh** của arm ứng viên. Ba cái kia (`max_hold_bars_4h`, `dg6d_retrace_frac`,
`funding_rate_pct`) khai **trung thực** — ghi ra để có MẪU SỐ, vì một bảng chỉ
liệt kê cái sai thì người đọc không biết tỉ lệ.

🔴 **Đính chính của chính bản này:** bản nháp đầu viết *"cả hai lời khai đều
lệch"*, gộp `dg7` với `max_hold_bars_4h`. Đọc `param_status.yaml:161-164` thì
`max_hold` khai đúng (*"chính spec gọi nó là ỨNG VIÊN CHỐT kèm dấu [CẦN
CALIBRATE], tức tự khai đây là số tạm"*) — thứ lệch là **hàm ý của spec §10.2**
(dải TIME_STOP 5-25%), không phải lời khai trong `param_status`. Hai thứ khác
nhau, và gộp chúng là đúng lớp lỗi dự án gọi tên nhiều nhất: **sai ở NHÃN dán
lên phép đo, không sai ở phép đo**.

Mọi con số expectancy mà D4 sắp mua là con số **của bộ máy này**, nên không biết
tham số nào gánh việc thì `mean_R` đo được là `mean_R` của một hệ **chưa được mô
tả đúng**.

════ Ranh giới: 0 trial, và KHÔNG chạy backtest nào ════

Script này **chỉ đọc artifact đã có trên đĩa** (`td0212`, `td0228`) + phân loại
theo **đường đọc mã đã kiểm tay**. Nó KHÔNG chạy `freqtrade backtesting`, KHÔNG
chạm CALIB/WFO/LOCKBOX, KHÔNG tính một chỉ số hiệu năng nào. Căn cứ 0 trial:
`DR-014` §2 chỉ tính *đánh giá cấu hình*.

════ 🔴 BA HẠNG, và vì sao câu hỏi ban đầu SAI ĐƠN VỊ với một nửa ════

Kế hoạch ban đầu hỏi *"mỗi tham số ràng buộc bao nhiêu % LỆNH"*. Đọc mã thì câu
đó **chỉ có nghĩa với tham số dạng CỔNG**. Với tham số là **đầu vào LIÊN TỤC**
(ngưỡng ZSS, hệ số buf_sl, haircut TP1...) thì không có sự kiện *"bị chặn"* nào
để đếm — chúng dịch chuyển KẾT QUẢ chứ không CHẶN lệnh. Hỏi "% lệnh" ở đó là
hỏi sai đơn vị, và trả về một con số cho nó sẽ là bịa.

    HANG_CONG      — có sự kiện chặn/kết thúc đếm được  → tính % LỆNH
    HANG_BAT_KHA   — cấu trúc KHÔNG THỂ ràng buộc trên arm này → 0% có LÝ DO
    HANG_LIEN_TUC  — đầu vào liên tục → `pending`, KHÔNG điền 0.0 (N6)

Phân biệt này là kết quả của việc đọc mã, không phải một lựa chọn trình bày:
`HANG_BAT_KHA` và `HANG_LIEN_TUC` **đều** cho 0 sự kiện chặn, nhưng chúng nghĩa
khác nhau hoàn toàn — một cái *"không thể xảy ra"*, một cái *"đếm sai thứ"*.
Gộp chúng lại là đúng thứ `N6` cấm: một con số 0 không phân biệt được với
*chưa đo*.

════ 🔴 Nhãn trung thực: phần PHÂN LOẠI là ĐỌC TAY, không phải phép đo ════

Cột `duong_doc` và `hang` dưới đây do người đọc mã và gán, kèm `file:line` để
kiểm lại được. Chỉ cột `ty_le_lenh` là máy tính từ artifact. Trộn hai thứ dưới
một nhãn *"đo được"* chính là hình dạng lỗi mà dự án đã đặt tên nhiều lần:
**sai ở NHÃN dán lên phép đo, không sai ở phép đo**.

Chạy trong Docker (N7):
  docker compose -f docker/docker-compose.yml run --rm freqtrade \
      docs/du-lieu-do/do_td0246_tham_so_nao_ganh_viec.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ARTIFACT_ARM = REPO / "docs" / "du-lieu-do" / "td0212-ba-arm-sau-va.json"
ARTIFACT_DCA = REPO / "docs" / "du-lieu-do" / "td0228-z0-vs-dca-tap-lenh.json"
KET_QUA = REPO / "docs" / "du-lieu-do" / "td0246-tham-so-nao-ganh-viec.json"

ARM_UNG_VIEN = "Z0-T1"

HANG_CONG = "CONG"
HANG_BAT_KHA = "BAT_KHA_TREN_ARM_NAY"
HANG_LIEN_TUC = "DAU_VAO_LIEN_TUC"

#: Đọc tay, mỗi dòng kèm bằng chứng. `exit_reason` = tên lý do thoát mà tham số
#: này sinh ra (chỉ HANG_CONG có); `None` nghĩa là không có sự kiện đếm được.
THAM_SO: dict[str, dict[str, object]] = {
    "dg7_funding_frac": {
        "hang": HANG_CONG,
        "exit_reason": "FUNDING_STOP",
        "duong_doc": "user_data/strategies/ZoneAbsorption.py:1160 (custom_exit, VÔ ĐIỀU KIỆN)",
        "ghi_chu": (
            "🔴 LỜI KHAI SAI. param_status.yaml:198-201 khai 'DG7 chỉ áp cho SHORT nên hiện "
            "chưa có đường chạy nào chạm tới; cùng lý do với dg6d_retrace_frac'. Nhưng "
            "funding_stop.py:7-8 tự khai 'ÁP DỤNG KHÔNG ĐIỀU KIỆN' và :11-14 nói thẳng công "
            "thức -trade.funding_fees ĐÃ ĐÚNG CHO CẢ LONG LẪN SHORT. Cơ chế trôi: lý lẽ được "
            "kế thừa BẰNG THAM CHIẾU ('cùng lý do với dg6d') sang một chỗ nó không còn đúng — "
            "người viết không bịa, họ trỏ tới một lý lẽ THẬT, chỉ trỏ nhầm chỗ."
        ),
    },
    "max_hold_bars_4h": {
        "hang": HANG_CONG,
        "exit_reason": "TIME_STOP",
        "duong_doc": "user_data/strategies/ZoneAbsorption.py:1155 (custom_exit, VÔ ĐIỀU KIỆN)",
        "ghi_chu": (
            "✅ LỜI KHAI TRUNG THỰC — param_status.yaml:161-164 khai 'chính spec gọi nó là "
            "ỨNG VIÊN CHỐT kèm dấu [CẦN CALIBRATE], tức tự khai đây là số tạm; mở lại cần "
            "phân bố thời-gian-tới-kết-cục của lệnh thật'. KHÔNG khai 'chưa ai chạm'. "
            "🔑 Và con số 0% ĐO ĐƯỢC ở đây CHÍNH LÀ thứ điều kiện mở lại của nó đòi: không "
            "lệnh nào chạm trần 24 nến. Thứ LỆCH là hàm ý của spec §10.2 (dải TIME_STOP "
            "5-25%, tự chú '< 5% → 24 nến chỉ là trang trí'), không phải lời khai. "
            "🔴 Kèm một khoảng hở riêng: TIME_STOP_RATIO_BAND (thresholds.py:37) xuất hiện "
            "ĐÚNG MỘT LẦN toàn repo — tại dòng định nghĩa; nó KHÔNG có trong "
            "evaluate_branch1() cùng file dù bảy hằng số còn lại đều có."
        ),
    },
    "dg4_bars_1h": {
        "hang": HANG_BAT_KHA,
        "exit_reason": None,
        "duong_doc": "user_data/strategies/ZoneAbsorption.py:1040 (trong danh_gia_tat_ca)",
        "ghi_chu": (
            "🔴 CÓ đường đọc nhưng KHÔNG BAO GIỜ TỚI: ZoneAbsorption.py:1006-1007 "
            "'if cong_ap_dung(self._arm) == (): return None' đứng TRƯỚC lời gọi ở :1031. "
            "arm_switches.py:73-75 ARM_DON_TRANCHE chứa Z0-T1 ⇒ cong_ap_dung trả () ⇒ "
            "DG1-DG5 KHÔNG BAO GIỜ ĐƯỢC XÉT trên arm ứng viên."
        ),
    },
    "dg6a_atr_ratio": {
        "hang": HANG_BAT_KHA,
        "exit_reason": "DG6_EARLY_INVALIDATION",
        "duong_doc": "user_data/strategies/ZoneAbsorption.py:279 + :1186",
        "ghi_chu": (
            "DG6 chỉ chạy ở arm Z3b (ZoneAbsorption.py:1101-1102 'if self._arm != \"Z3b\": "
            "return None') ⇒ bất khả trên Z0-T1. Trên Z3b nó nổ ĐÚNG 1/22 lệnh (td0228)."
        ),
    },
    "dg6d_retrace_frac": {
        "hang": HANG_BAT_KHA,
        "exit_reason": None,
        "duong_doc": "KHÔNG CÓ — 0 lời gọi resolve(tier_b.dg6d_retrace_frac) trong src/ và user_data/strategies/",
        "ghi_chu": (
            "✅ LỜI KHAI ĐÚNG, đã kiểm: dg6_early_invalidation.py:98 '\"\"\"CHỈ áp dụng cho "
            "SHORT — rủi ro short squeeze (§3.3d).\"\"\"' và :99 'if huong != \"short\"'. "
            "Cộng với 0 đường đọc sản xuất ⇒ 'chưa có đường chạy nào chạm tới' là ĐÚNG. "
            "Đây là MẪU SỐ của bảng: không phải mọi lời khai đều sai."
        ),
    },
    "funding_rate_pct": {
        "hang": HANG_BAT_KHA,
        "exit_reason": None,
        "duong_doc": "KHÔNG CÓ — 0 lời gọi resolve(tier_b.funding_rate_pct) trong src/ và user_data/strategies/",
        "ghi_chu": (
            "✅ LỜI KHAI TRUNG THỰC, khác LOẠI với dg7: param_status.yaml:117-122 không khai "
            "'chưa ai chạm' mà khai một MÂU THUẪN NỘI TẠI CỦA SPEC (dòng 1384 mang dấu "
            "[CẦN CALIBRATE] nhưng bảng DOF ghi §3.3d đóng băng -0.05%). Ghi nhận chứ không "
            "tự hoà giải — đúng quy tắc 11."
        ),
    },
    "zss_threshold": {
        "hang": HANG_LIEN_TUC,
        "exit_reason": None,
        "duong_doc": "user_data/strategies/ZoneAbsorption.py:277",
        "ghi_chu": "Ngưỡng chất lượng zone ở tầng ENTRY — dịch tập tín hiệu, không sinh sự kiện chặn đếm được trên LỆNH.",
    },
    "buf_sl_atr": {
        "hang": HANG_LIEN_TUC,
        "exit_reason": None,
        "duong_doc": "user_data/strategies/ZoneAbsorption.py:278 → trade_plan.py:71-74",
        "ghi_chu": "Vào `sl` ⇒ vào `r_eff_plan` ⇒ vào cỡ lệnh VÀ vào mẫu số của R. Ràng buộc MỌI lệnh, nên '% lệnh' vô nghĩa.",
    },
    "wick_close_upper_frac": {
        "hang": HANG_LIEN_TUC,
        "exit_reason": None,
        "duong_doc": "user_data/strategies/ZoneAbsorption.py:283 → entry_confirmation.py:156",
        "ghi_chu": "Điều kiện hình dạng nến xác nhận — dịch tập tín hiệu ở tầng ENTRY.",
    },
    "v_min": {
        "hang": HANG_LIEN_TUC,
        "exit_reason": None,
        "duong_doc": "entry_confirmation.py:183 hap_thu_co_volume()",
        "ghi_chu": (
            "Điều kiện (c) volume. FROZEN 1.0 tại chỗ (DR-D4-03). Dịch tập tín hiệu; và arm "
            "Z0-V1 tồn tại ĐÚNG để tắt nó — nhưng Z0-V1 không nằm trong 4 arm D4 sẽ chạy."
        ),
    },
    "tp1_haircut_pct": {
        "hang": HANG_LIEN_TUC,
        "exit_reason": None,
        "duong_doc": "take_profit.py:141 + :170",
        "ghi_chu": "Trừ hao mức TP1 — dịch MỨC chốt lời, không chặn lệnh nào. Đo được gián tiếp qua tp1_theo_nguon.",
    },
    "mult_corr_thresholds": {
        "hang": HANG_LIEN_TUC,
        "exit_reason": None,
        "duong_doc": "user_data/strategies/ZoneAbsorption.py:710 → sizing.py:134",
        "ghi_chu": "Hệ số §6.2 — dịch CỠ LỆNH (≤ 1.0 theo ràng buộc bao trùm), không chặn lệnh.",
    },
}


def _doc_arm(path: Path, arm: str) -> dict:
    d = json.loads(path.read_text(encoding="utf-8"))
    v = (d.get("lenh_that") or {}).get(arm)
    if not v:
        raise SystemExit(f"{path.name} không có arm {arm!r} — kiểm lại artifact")
    return v


def main() -> int:
    z = _doc_arm(ARTIFACT_ARM, ARM_UNG_VIEN)
    so_lenh = int(z["so_lenh"])
    exits: dict[str, int] = dict(z["exit_reason"])

    bang: dict[str, dict[str, object]] = {}
    for ten, mo_ta in THAM_SO.items():
        dong = dict(mo_ta)
        er = mo_ta["exit_reason"]
        if mo_ta["hang"] == HANG_CONG and isinstance(er, str):
            n = exits.get(er, 0)
            dong["so_lenh_bi_rang_buoc"] = n
            dong["ty_le_lenh"] = round(100.0 * n / so_lenh, 1)
        elif mo_ta["hang"] == HANG_BAT_KHA:
            # 0 ở đây là SUY RA ĐƯỢC, không phải bịa: đường chạy bị chặn
            # trước khi tham số được đọc (xem `duong_doc` + `ghi_chu`). N6
            # cấm điền 0.0 cho thứ CHƯA ĐO — không cấm cho thứ đã chứng
            # minh là không thể xảy ra. Nhưng phải kèm lý do, nếu không nó
            # lại thành một số 0 không đọc được.
            dong["so_lenh_bi_rang_buoc"] = 0
            dong["ty_le_lenh"] = 0.0
            dong["ly_do_bang_0"] = "cấu trúc chặn trước khi tham số được đọc — xem duong_doc"
        else:
            # N6 — CẤM điền 0.0 cho thứ SAI ĐƠN VỊ: không có sự kiện chặn
            # nào để đếm, nên 0 sẽ bị đọc thành "không ảnh hưởng gì".
            dong["so_lenh_bi_rang_buoc"] = None
            dong["ty_le_lenh"] = "pending"
            dong["ly_do_pending"] = "đầu vào liên tục — dịch KẾT QUẢ, không CHẶN lệnh; đo được cần phân tích độ nhạy, và việc đó TỐN TRIAL"
        bang[ten] = dong

    theo_hang: dict[str, list[str]] = {}
    for ten, d in bang.items():
        theo_hang.setdefault(str(d["hang"]), []).append(ten)

    ra = {
        "nguon": (
            "TD-0246, 14/09/2026 — tham số tier_b nào ĐANG GÁNH VIỆC trên arm ứng viên "
            f"{ARM_UNG_VIEN}. Dẫn từ artifact ĐÃ CÓ trên đĩa (td0212, td0228) + đường đọc mã "
            "đã kiểm tay. KHÔNG chạy backtest nào."
        ),
        "ranh_gioi": (
            "0 trial: không đánh giá cấu hình nào, không chạm CALIB/WFO/LOCKBOX, không tính "
            "một chỉ số hiệu năng nào (DR-014 §2). CHỈ đếm exit_reason đã có trong artifact. "
            "🔴 NHÃN: cột `hang` và `duong_doc` là ĐỌC TAY kèm file:line — chỉ `ty_le_lenh` là "
            "máy tính. Không đọc cả bảng dưới một nhãn 'đo được'."
        ),
        "arm": ARM_UNG_VIEN,
        "so_lenh_arm": so_lenh,
        "exit_reason_arm": exits,
        "dinh_nghia_hang": {
            HANG_CONG: "có sự kiện chặn/kết thúc đếm được ⇒ tính % LỆNH",
            HANG_BAT_KHA: "cấu trúc KHÔNG THỂ ràng buộc trên arm này ⇒ 0% CÓ LÝ DO",
            HANG_LIEN_TUC: "đầu vào liên tục, không phải cổng ⇒ '% lệnh' SAI ĐƠN VỊ ⇒ pending (N6)",
        },
        "tong_ket": {
            "so_tham_so": len(THAM_SO),
            "theo_hang": {k: len(v) for k, v in sorted(theo_hang.items())},
            "loi_khai_da_kiem_SAI": ["dg7_funding_frac"],
            "loi_khai_da_kiem_DUNG": [
                "max_hold_bars_4h", "dg6d_retrace_frac", "funding_rate_pct",
            ],
            "ty_le_loi_khai_sai": "1/4 lời khai đã kiểm",
            "dinh_chinh": (
                "Bản nháp đầu của TD-0246 viết 'cả hai lời khai đều SAI' (dg7 + "
                "max_hold_bars_4h). Đọc param_status.yaml:161-164 thì max_hold khai TRUNG "
                "THỰC; thứ lệch là hàm ý spec §10.2, không phải lời khai. Giữ câu này để "
                "con số 1/4 không bị đọc thành 2/2."
            ),
            "loi_khai_CHUA_KIEM": sorted(
                t for t in THAM_SO
                if t not in {"dg7_funding_frac", "dg6d_retrace_frac", "funding_rate_pct",
                             "max_hold_bars_4h", "dg4_bars_1h", "dg6a_atr_ratio"}
            ),
        },
        "phat_hien_lon_nhat": (
            "🔴 DG1-DG5 KHÔNG BAO GIỜ ĐƯỢC XÉT trên 6/9 arm — arm_switches.py:73-75 "
            "ARM_DON_TRANCHE = {Z0, Z1, Z0-T0, Z0-T1, Z0-V1, Z0-S1}, cong_ap_dung() trả () "
            "cho cả sáu, và ZoneAbsorption.py:1006-1007 return None TRƯỚC lời gọi "
            "danh_gia_tat_ca ở :1031. Trong đó có CẢ arm ứng viên sản xuất (Z0-T1) và CẢ mốc "
            "so (Z0). ⇒ Năm cổng — phần 'Smart' của Smart DCA — là BẤT ĐỘNG trên cấu hình sẽ "
            "lên tiền thật. Trong 4 arm D4 sắp chạy, chỉ Z3 còn xét DG1-DG5."
        ),
        "bang": bang,
    }
    KET_QUA.write_text(json.dumps(ra, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"arm {ARM_UNG_VIEN}: {so_lenh} lệnh · exit_reason {exits}")
    for ten, d in sorted(bang.items(), key=lambda kv: (str(kv[1]["hang"]), kv[0])):
        print(f"  {str(d['hang']):22s} {ten:24s} ty_le_lenh={d['ty_le_lenh']}")
    print(f"\ntổng kết: {ra['tong_ket']['theo_hang']}")
    print(f"→ {KET_QUA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
