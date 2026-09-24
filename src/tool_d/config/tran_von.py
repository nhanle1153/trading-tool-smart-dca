"""TD-0382 — chốt trần vốn D12 + lớp xác nhận trên dữ liệu sau `T3` (`DR-LOCKBOX-04` §2 dòng 3, §3).

Chủ dự án chốt 24/09/2026 (phiên mã `143375ad`), bốn câu:
  1. Trần D12 = đúng giá trị ĐANG chốt lúc viết (`E_D` 750, `rho_pct` 0,375, `L_exchange` 3), ghi ở
     `tier_c.lop_xac_nhan_sau_t3.tran_d12` — đổi trần = một commit.
  2. "Tăng vốn" = tăng BẤT KỲ khoá nào trong ba khoá đó (giữ `E_D` mà nhân đôi `rho_pct` vẫn là tăng tiền rủi ro).
  3. CHẶN CỨNG lúc đọc cấu hình: `load_tool_d_config()` gọi hàm này ⇒ mọi lần chạy (live, dry-run, backtest) từ chối.
     Chiến lược gọi loader trong `__init__`, ngoài `strategy_safe_wrapper` của Freqtrade ⇒ lỗi không bị nuốt (TD-0187).
  4. Bằng chứng xác nhận = file kết quả đo ĐÃ COMMIT (`hien_vat`), cùng khuôn `TD-0375`. Bộ đo sinh file là việc riêng.

Không vượt trần ⇒ không kiểm gì thêm, không gọi git. Vượt trần ⇒ phải có hiện vật hợp lệ, không thì `TranVonError`.

TD-0387 siết thêm ba điều theo quyết định "backtest từ ngày CHỌN, đo một lần" (ô ký `DR-LOCKBOX-04` §3, `DR-XAC-NHAN-01`):
  a. `tu_ngay` ≥ ngày của lần CHỌN **còn hiệu lực** của `hypothesis_slot` (`registry/idea_queue.jsonl`, qua
     `idea_events.duyet_so` — lần đã `VOIDED` không tính). Không có lần chọn còn hiệu lực ⇒ chưa đạt.
  b. Hiện vật có **đúng một commit** trong lịch sử git — đo lại rồi commit đè là "đo tới khi đẹp".
  c. `config_sha256` của hiện vật phải là `config_hash` của một bản ghi trong `lockbox/lockbox_access.log`. Chưa có lần
     chạm nào ⇒ chưa đạt (không xác nhận trước lockbox). Nghĩa của mã băm do đường chạm thật (`TD-0352`) định; bộ đo
     (`TD-0389`) phải ghi đúng cùng loại băm.

⚠️ Điểm mù còn lại: máy vẫn không chứng minh được con số trong hiện vật do chính bộ đo sinh ra. (b) + (c) thu hẹp, không đóng.
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
#: TD-0404 (`DR-LOCKBOX-04` bổ sung 24/09/2026): thêm vốn RIÊNG của rổ `IQ-0003` — vốn mới nằm ngoài ba khoá kia.
KHOA_VON = ("E_D", "rho_pct", "L_exchange", "von_ro_usdt")
#: Khoá vốn được phép `null` ở `tier_a` (= chưa cấp vốn, bỏ qua). Có số mà trần `null` ⇒ VƯỢT: trần phải điền CÙNG commit
#: với vốn (`DR-D0-IQ0003` §10 câu c), không để trống rồi đọc thành "không có trần".
KHOA_VON_CO_THE_TRONG = ("von_ro_usdt",)
DR_NGUON = "DR-LOCKBOX-04"
_SLOT_RE = re.compile(r"^IQ-\d{4}$")
#: TD-0387 — đường dẫn tương đối so với `repo_dir`.
SO_Y_TUONG = Path("registry/idea_queue.jsonl")
SO_TRUY_CAP_LOCKBOX = Path("lockbox/lockbox_access.log")


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
        if k in KHOA_VON_CO_THE_TRONG:
            if gia_tri is None:
                continue
            if k not in tran:
                raise _loi(f"thiếu trần tran_d12.{k}")
            if tran_k is None:
                vuot.append(
                    f"{k}: {gia_tri} mà trần tran_d12.{k} còn trống — điền trần cùng commit với tier_a.{k}"
                )
                continue
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


def _ngay_chon_hieu_luc(slot: str, repo_dir: Path) -> date | str:
    """TD-0387 (a) — ngày (UTC) của lần CHỌN còn hiệu lực của `slot`, hoặc lý do không có."""
    from tool_d.ledger.idea_events import duyet_so

    duong = repo_dir / SO_Y_TUONG
    try:
        dong = [json.loads(x) for x in duong.read_text(encoding="utf-8").splitlines() if x.strip()]
    except (OSError, ValueError) as e:
        return f"sổ ý tưởng {SO_Y_TUONG.as_posix()} đọc không được: {e!r}"
    chon = [e for e in duyet_so(dong).chon_hieu_luc if e.get("idea_id") == slot]
    if not chon:
        return f"{slot} không có lần CHỌN còn hiệu lực trong {SO_Y_TUONG.as_posix()}"
    try:
        return datetime.strptime(str(chon[-1].get("selected_at")), "%Y-%m-%dT%H:%M:%SZ").date()
    except ValueError:
        return f"{slot}: selected_at {chon[-1].get('selected_at')!r} không đọc được"


def _so_commit(rel: Path, repo_dir: Path) -> int | str:
    """TD-0387 (b) — số commit từng chạm file hiện vật (theo cả đổi tên)."""
    import subprocess

    kq = subprocess.run(
        ["git", "--no-optional-locks", "log", "--follow", "--format=%H", "--", rel.as_posix()],
        cwd=repo_dir, capture_output=True, text=True,
    )
    if kq.returncode != 0:
        return f"git log lỗi: {kq.stderr.strip()!r}"
    return len([x for x in kq.stdout.splitlines() if x.strip()])


def _hash_da_cham_lockbox(repo_dir: Path) -> set[str] | str:
    """TD-0387 (c) — tập `config_hash` của mọi bản ghi trong sổ truy cập lockbox."""
    from tool_d.lockbox.access_log import read_access_log

    try:
        ban_ghi = read_access_log(repo_dir / SO_TRUY_CAP_LOCKBOX)
    except (OSError, ValueError) as e:
        return f"sổ truy cập lockbox đọc không được: {e!r}"
    return {str(r.get("config_hash")) for r in ban_ghi if r.get("config_hash")}


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
    so_commit = _so_commit(rel, repo_dir)
    if so_commit != 1:
        ly_do.append(
            f"hiện vật xác nhận phải có ĐÚNG MỘT commit (đo một lần, DR-XAC-NHAN-01 Q2), nhận {so_commit}"
        )
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
        if isinstance(slot, str) and _SLOT_RE.match(slot):
            ngay_chon = _ngay_chon_hieu_luc(slot, repo_dir)
            if isinstance(ngay_chon, str):
                ly_do.append(f"hiện vật: {ngay_chon}")
            elif tu_ngay < ngay_chon:
                ly_do.append(
                    f"hiện vật: tu_ngay {tu_ngay} trước ngày CHỌN {ngay_chon} của {slot} — dữ liệu đó người ra ý tưởng"
                    " có thể đã thấy (ô ký DR-LOCKBOX-04 §3)"
                )
    cfg_hv = hv.get("config_sha256")
    hash_cham = _hash_da_cham_lockbox(repo_dir)
    if isinstance(hash_cham, str):
        ly_do.append(hash_cham)
    elif not hash_cham:
        ly_do.append("chưa có lần chạm lockbox nào — không xác nhận trước lockbox")
    elif cfg_hv not in hash_cham:
        ly_do.append(f"hiện vật: config_sha256 {cfg_hv!r} không khớp cấu hình nào đã chạm lockbox")
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
