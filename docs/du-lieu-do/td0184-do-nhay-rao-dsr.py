"""Đo mô tả — 0 trial, KHÔNG chạm dữ liệu (thuần toán trên công thức đã có).

Câu hỏi (chủ dự án, sau phát hiện của phiên `be`): đạt sàn 150 lệnh/năm
(§10.2 Nhánh 1) có đủ để qua RÀO DSR (cũng ở Nhánh 1) không? Ablation
D4 chạy trên cửa sổ WFO ~0,63 năm (spec dòng 3287), nên `n` THẬT dùng
cho rào DSR luôn nhỏ hơn nhiều "lệnh/năm" — ví dụ 150/năm → n ≈ 95.

🔴 KHÔNG đo `std_R`/`mean_R` thật ở đây — làm vậy cần tính `pnl_abs`
trên lệnh THẬT (CALIB/WFO/EXPLORE), mà:
  - CALIB/WFO: tính là "chạm dữ liệu" (DR-014 §2, đánh giá cấu hình),
    tiêu 1 trial — chính là việc TD-0184 định làm, đang bị chặn.
  - EXPLORE: 🔄 ĐÍNH CHÍNH 16/09/2026 (`MT-24`, `DR-D4-13`). Bản đầu của
    docstring này đặt trong ngoặc kép, như trích nguyên văn, một câu gán
    cho `DR-D0PRE-05` §4 là cấm expectancy/PnL theo arm. Điều khoản đó
    KHÔNG chứa câu ấy — đó là một TRÍCH DẪN BỊA (bản cũ còn trong git).
    Chữ thật: spec §9c.4b cho EXPLORE "Phân tích KHÔNG giới hạn, 0 trial";
    ràng buộc cứng là (a) không dùng để validate, (b) mã EXPLORE không
    bao giờ sang pool. ⇒ `std_R` ĐO ĐƯỢC trên EXPLORE, 0 trial, nhưng
    CHỈ để lên kế hoạch cỡ mẫu, KHÔNG làm căn cứ phán quyết
    (`DR-D4-13` §1.2).
File này vẫn KHÔNG lấy `std_R`/`mean_R` thật — không phải vì bị cấm, mà
vì câu hỏi của nó trả lời được bằng bảng độ nhạy (bản đầu viết lý do là
"không có đường vòng hợp lệ"; lý do đó SAI theo đính chính trên) — nên chỉ
dựng BẢNG ĐỘ NHẠY: ứng với mỗi giả định `std_R`, cần `mean_R` bao nhiêu
để qua rào ở các `n` khác nhau. Không có ô nào trong bảng là "sự thật
đo được" — mọi cột `std_R` đều là ĐIỀU KIỆN GIẢ ĐỊNH, ghi rõ để không ai
đọc nhầm thành kết quả đo.

Công thức — trích NGUYÊN VĂN từ `src/tool_d/gates/dsr.py` (không chép
lại, IMPORT thẳng để không có hai nguồn cho cùng một phép tính — N1):

    dsr_adjusted_expectancy = mean_R − dsr_hurdle(N) × std_R / √n
    dsr_hurdle(N) = √(2·ln N),  N = N_ĐĂNG_KÝ = 114 (DR-D0PRE-02)
    Ngưỡng PASS: dsr_adjusted_expectancy ≥ 0,10 (DSR_ADJ_EXPECTANCY_MIN)

Chạy: `docker compose -f docker/docker-compose.yml run --rm tests
python docs/du-lieu-do/td0184-do-nhay-rao-dsr.py` (không cần freqtrade,
không chạm feather nào — thuần Python + import nội bộ).
"""

from __future__ import annotations

import json
from pathlib import Path

from tool_d.gates.dsr import N_DANG_KY, dsr_hurdle
from tool_d.gates.thresholds import DSR_ADJ_EXPECTANCY_MIN

HURDLE = dsr_hurdle(N_DANG_KY)

# `n` ứng với vài mốc lệnh/năm × 0,63 năm (cửa sổ WFO, spec dòng 3287) —
# và vài mốc "để biết cần đi xa tới đâu" (300/600/1000) — KHÔNG phải dự
# đoán sẽ đạt được, chỉ để đọc được hình dạng đường cong.
NAM_WFO = 0.63
MOC_LENH_NAM = [63.6, 100, 150, 300, 600, 950, 1500]
MOC_STD_R = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]


def mean_r_can_dat(*, std_r: float, n: int) -> float:
    """Đảo ngược công thức: `mean_R` tối thiểu để `dsr_adjusted_expectancy
    == DSR_ADJ_EXPECTANCY_MIN` — không gọi `dsr_adjusted_expectancy()` với
    `mean_r` dò tay, giải trực tiếp cho chính xác tuyệt đối."""
    if n < 2:
        raise ValueError(f"n phải >= 2, nhận {n}")
    return DSR_ADJ_EXPECTANCY_MIN + HURDLE * std_r / (n**0.5)


def main() -> None:
    bang = []
    for lenh_nam in MOC_LENH_NAM:
        n = max(2, round(lenh_nam * NAM_WFO))
        hang = {"lenh_nam": lenh_nam, "n_that_tren_wfo_0_63_nam": n}
        for std_r in MOC_STD_R:
            hang[f"mean_R_can_std={std_r}"] = round(mean_r_can_dat(std_r=std_r, n=n), 4)
        bang.append(hang)

    ra = {
        "nguon": "TD-0184 — độ nhạy rào DSR theo lệnh/năm và std_R giả định, 0 trial, KHÔNG chạm dữ liệu",
        "canh_bao": (
            "std_R là GIẢ ĐỊNH, KHÔNG PHẢI ĐO ĐƯỢC — không có đường hợp lệ để đo "
            "mean_R/std_R thật mà không tiêu trial (WFO) hoặc phạm DR-D0PRE-05 §4 (EXPLORE)."
        ),
        "cong_thuc": "mean_R_can = DSR_ADJ_EXPECTANCY_MIN + sqrt(2*ln(N_DANG_KY)) * std_R / sqrt(n)",
        "N_DANG_KY": N_DANG_KY,
        "dsr_hurdle": round(HURDLE, 4),
        "DSR_ADJ_EXPECTANCY_MIN": DSR_ADJ_EXPECTANCY_MIN,
        "nam_wfo": NAM_WFO,
        "bang": bang,
    }
    out = Path("docs/du-lieu-do/td0184-do-nhay-rao-dsr.json")
    out.write_text(json.dumps(ra, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(ra, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
