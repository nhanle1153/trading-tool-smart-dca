"""TD-0382 — chốt trần vốn D12 + lớp xác nhận trên dữ liệu sau `T3` (`DR-LOCKBOX-04` §2 dòng 3, §3).

Chủ dự án chốt 24/09/2026 (phiên mã `143375ad`), bốn câu:
  1. Trần D12 = đúng giá trị ĐANG chốt lúc viết (`E_D` 750, `rho_pct` 0,375, `L_exchange` 3), ghi ở
     `tier_c.lop_xac_nhan_sau_t3.tran_d12` — đổi trần = một commit.
  2. "Tăng vốn" = tăng BẤT KỲ khoá nào trong ba khoá đó (giữ `E_D` mà nhân đôi `rho_pct` vẫn là tăng tiền rủi ro).
  3. CHẶN CỨNG lúc đọc cấu hình: `load_tool_d_config()` gọi hàm này ⇒ mọi lần chạy (live, dry-run, backtest) từ chối.
     Chiến lược gọi loader trong `__init__`, ngoài `strategy_safe_wrapper` của Freqtrade ⇒ lỗi không bị nuốt (TD-0187).
  4. Bằng chứng xác nhận = file kết quả đo ĐÃ COMMIT (`hien_vat`), cùng khuôn `TD-0375`. Bộ đo sinh file là việc riêng.

Không vượt trần ⇒ không kiểm gì thêm, không gọi git. Vượt trần ⇒ phải có hiện vật hợp lệ, không thì `TranVonError`.

⚠️ Điểm mù đã biết: máy kiểm hiện vật ĐÃ COMMIT và NỘI DUNG đạt ngưỡng; nó không kiểm được con số trong đó do bộ đo thật
sinh ra trên đúng cấu hình đã chạm lockbox. Commit làm việc đó nhìn thấy được, không làm nó đúng (cùng điểm mù `TD-0375`).
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from datetime import date, datetime
from pathlib import Path
from typing import Any

KHOA_KHOI = "lop_xac_nhan_sau_t3"
#: Ba khoá `tier_a` mà tăng lên là tăng tiền thật có thể mất (câu 2).
KHOA_VON = ("E_D", "rho_pct", "L_exchange")
DR_NGUON = "DR-LOCKBOX-04"
_SLOT_RE = re.compile(r"^IQ-\d{4}$")


def _loi(msg: str) -> Exception:
    # Import trễ: `loader` import module này, tránh vòng import.
    from tool_d.config.loader import TranVonError

    return TranVonError(f"TỪ CHỐI cấu hình — {msg} ({DR_NGUON}, TD-0382)")


def _so(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _doc_khoi(tier_c: Mapping[str, Any]) -> Mapping[str, Any]:
    khoi = tier_c.get(KHOA_KHOI)
    if not isinstance(khoi, Mapping):
        raise _loi(f"thiếu khối tier_c.{KHOA_KHOI} trong khi tier_a có khai tham số vốn")
    tran = khoi.get("tran_d12")
    if not isinstance(tran, Mapping):
        raise _loi(f"thiếu tier_c.{KHOA_KHOI}.tran_d12")
    return khoi


def cac_khoa_vuot_tran(tier_a: Mapping[str, Any], tier_c: Mapping[str, Any]) -> list[str]:
    """Danh sách `"khoá: giá_trị > trần"`; rỗng ⇒ không vượt. `tier_a` không khai khoá vốn nào ⇒ rỗng.

    Khoá vốn có mặt trong `tier_a` mà trần thiếu / không phải số ⇒ raise (fail-closed): trần hỏng không được đọc là "không có
    trần"."""
    co_khai = [k for k in KHOA_VON if k in tier_a]
    if not co_khai:
        return []
    tran = _doc_khoi(tier_c)["tran_d12"]
    vuot: list[str] = []
    for k in co_khai:
        gia_tri, tran_k = tier_a[k], tran.get(k)
        if not _so(tran_k):
            raise _loi(f"trần tran_d12.{k} phải là số, nhận {tran_k!r}")
        if not _so(gia_tri):
            raise _loi(f"tier_a.{k} phải là số để so với trần, nhận {gia_tri!r}")
        if gia_tri > tran_k:
            vuot.append(f"{k}: {gia_tri} > trần {tran_k}")
    return vuot


def _doc_t3(tier_c: Mapping[str, Any]) -> date:
    try:
        return datetime.strptime(tier_c["data_split"]["t3"], "%Y-%m-%d").date()
    except (KeyError, TypeError, ValueError) as e:
        raise _loi(f"không đọc được tier_c.data_split.t3: {e!r}") from e


def ly_do_chua_xac_nhan(tier_c: Mapping[str, Any], repo_dir: Path) -> list[str]:
    """Rỗng ⇒ lớp xác nhận ĐẠT. Ngược lại: mọi lý do chưa đạt (liệt kê hết, không dừng ở lý do đầu)."""
    khoi = _doc_khoi(tier_c)
    ly_do: list[str] = []

    n_min = khoi.get("n_lenh_toi_thieu")
    if not isinstance(n_min, int) or isinstance(n_min, bool) or n_min < 30:
        ly_do.append(f"n_lenh_toi_thieu phải là số nguyên ≥ 30 (sàn DR-011), nhận {n_min!r}")
    chi_so = khoi.get("chi_so")
    if not isinstance(chi_so, str) or not chi_so.strip():
        ly_do.append("chi_so chưa điền (DR-LOCKBOX-04 §3 ⏳ chủ dự án)")
    nguong = khoi.get("nguong")
    # L-Z35 / N6: ngưỡng chưa điền = +inf, không phải None/0 — gate không thể vô tình PASS.
    nguong_so = nguong if _so(nguong) else math.inf
    if nguong_so == math.inf:
        ly_do.append(f"nguong chưa điền ⇒ +inf, nhận {nguong!r}")

    duong = khoi.get("hien_vat")
    if not isinstance(duong, str) or not duong.strip():
        return ly_do + ["hien_vat: chưa khai đường dẫn file kết quả đo"]
    rel = Path(duong)
    from tool_d.dr015.cong_d35 import _da_commit

    loi_commit = _da_commit(rel, repo_dir)
    if loi_commit is not None:
        return ly_do + [f"hiện vật xác nhận: {loi_commit}"]
    try:
        hv = json.loads((repo_dir / rel).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return ly_do + [f"hiện vật xác nhận đọc không được: {e!r}"]
    if not isinstance(hv, Mapping):
        return ly_do + ["hiện vật xác nhận phải là object JSON"]

    if hv.get("dr") != DR_NGUON:
        ly_do.append(f"hiện vật: dr phải là {DR_NGUON!r}, nhận {hv.get('dr')!r}")
    slot = hv.get("hypothesis_slot")
    if not isinstance(slot, str) or not _SLOT_RE.match(slot):
        ly_do.append(f"hiện vật: hypothesis_slot phải dạng IQ-xxxx, nhận {slot!r}")
    t3 = _doc_t3(tier_c)
    try:
        tu_ngay = datetime.strptime(hv.get("tu_ngay"), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        ly_do.append(f"hiện vật: tu_ngay phải dạng YYYY-MM-DD, nhận {hv.get('tu_ngay')!r}")
    else:
        if tu_ngay <= t3:
            ly_do.append(f"hiện vật: tu_ngay {tu_ngay} không nằm SAU T3 = {t3} (dữ liệu đó thuộc lockbox/WFO)")
    n_lenh = hv.get("n_lenh")
    if not isinstance(n_lenh, int) or isinstance(n_lenh, bool):
        ly_do.append(f"hiện vật: n_lenh phải là số nguyên, nhận {n_lenh!r}")
    elif isinstance(n_min, int) and n_lenh < n_min:
        ly_do.append(f"hiện vật: n_lenh {n_lenh} < {n_min}")
    if isinstance(chi_so, str) and hv.get("chi_so") != chi_so:
        ly_do.append(f"hiện vật: chi_so {hv.get('chi_so')!r} khác chỉ số đã chốt {chi_so!r}")
    gia_tri = hv.get("gia_tri")
    if not _so(gia_tri):
        ly_do.append(f"hiện vật: gia_tri phải là số hữu hạn, nhận {gia_tri!r}")
    elif not gia_tri >= nguong_so:
        ly_do.append(f"hiện vật: gia_tri {gia_tri} < ngưỡng {nguong_so}")
    return ly_do


def kiem_tran_von_d12(tier_a: Mapping[str, Any], tier_c: Mapping[str, Any], *, repo_dir: Path) -> None:
    """Điểm vào duy nhất, `load_tool_d_config()` gọi. Không vượt trần ⇒ trả về ngay. Vượt ⇒ lớp xác nhận phải ĐẠT."""
    vuot = cac_khoa_vuot_tran(tier_a, tier_c)
    if not vuot:
        return
    ly_do = ly_do_chua_xac_nhan(tier_c, repo_dir)
    if ly_do:
        raise _loi(
            "vốn vượt trần D12 (" + "; ".join(vuot) + ") mà lớp xác nhận sau T3 CHƯA ĐẠT: " + "; ".join(ly_do)
            + ". Giữ vốn ở trần, hoặc commit hiện vật xác nhận đạt ngưỡng đã chốt TRƯỚC."
        )
