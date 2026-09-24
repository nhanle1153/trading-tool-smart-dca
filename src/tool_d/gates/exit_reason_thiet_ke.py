"""TD-0375 — máy canh cho `DR-PHAN-QUYET-01` §4.2 bước 3 (giải nợ §6 dòng 3, §8 điểm yếu 2).

Luật (DR §4.2, chủ dự án chốt 24/09/2026 — CHẶN CỨNG, không chỉ cảnh báo): trước suất ĐẦU TIÊN của một ứng viên,
phải có số đếm `exit_reason` trên EXPLORE (0 suất) và tỉ lệ `TIME_STOP` phải nằm trong `TIME_STOP_RATIO_BAND`.
Ngoài dải ⇒ dừng TRƯỚC khi tiêu suất: sửa thiết kế, hoặc chủ dự án khai bằng DR rằng ứng viên vào cổng D0.9 với tiêu
chí này biết trước là trượt.

Vì sao có máy: trước việc này §4.2 chỉ là chữ, và một nghĩa vụ chỉ nằm trong chữ là thứ `MT-71` vừa gọi tên. Hậu quả
cụ thể mà luật chặn: ZA LONG đo `TIME_STOP` 1/246 (`TD-0367`) — DG8 là cửa chết, và cổng D0.9 loại nhầm giả thuyết vì
thiết kế chứ không vì thiếu lợi thế (`MT-72`).

════ Hiện vật đọc ════

`docs/du-lieu-do/<IQ-xxxx>-exit-reason-explore.json`, đúng khuôn đầu ra của `do_td0193_lenh_nam_explore.py --ket-qua`
(khoá `lenh_that: {arm: {so_lenh, exit_reason}}`) — không viết bộ đo mới. Hiện vật phải ĐÃ COMMIT và khớp HEAD
(`DR-PHAN-QUYET-01` §2.3: file ngoài lịch sử không tái lập được — bài học `runs/D-0015`).

- MỌI arm trong `lenh_that` đều bị kiểm: một arm ngoài dải là đủ để từ chối (sai về phía khó tiêu suất hơn).
- Lối thoát duy nhất: khoá `dr_biet_truoc_truot` trỏ tới một file trong `docs/decisions/` ĐÃ COMMIT, có nhắc đích danh
  slot và `DR-PHAN-QUYET-01`. Máy chỉ kiểm giấy tồn tại và đúng địa chỉ; nội dung là việc của chủ dự án.

Không đổi ngưỡng nào: dải đọc từ `thresholds.py`, tên cửa thoát đọc từ `chi_so_export.py` (MT-03).

════ TD-0398 — lớp `CAN_RO_THEO_LICH` (`DR-CAN-RO-01`) ════

Rổ cân theo lịch không có cửa thoát theo thời gian (DG8) nào để chết, nên phép so DẢI không áp. Phép ĐẾM vẫn bắt buộc.
Hiện vật được miễn dải khi và chỉ khi thoả CẢ BA (DR §3):
  1. khoá `lop_chien_luoc = "CAN_RO_THEO_LICH"` + khoá `dr_thiet_ke` trỏ một DR đã commit, nhắc đích danh slot và
     `DR-CAN-RO-01`, chứa khối `DR-CAN-RO-01:LOP` có `slot` trùng — hỏng ⇒ TỪ CHỐI, không quay về mặc định;
  2. mọi nhãn `exit_reason` của mọi arm thuộc `NHAN_THOAT_CAN_RO` — lệch ⇒ KHÔNG được miễn, áp dải như cũ;
  3. tổng `CAN_RO` > 0 — bằng 0 ⇒ lớp đã khai không được chứng minh ⇒ TỪ CHỐI (N6).
Không khai lớp ⇒ hành vi `TD-0375` không đổi một bit.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from tool_d.ablation.chi_so_export import EXIT_CAN_RO, EXIT_TIME_STOP
from tool_d.dr015.cong_d35 import _da_commit
from tool_d.gates.thresholds import TIME_STOP_RATIO_BAND

#: Slot của ứng viên đi qua Idea Queue (MT-12). ZA LONG dùng slot `A-xx` nên không bị luật này áp.
SLOT_UNG_VIEN = re.compile(r"^IQ-\d{4}$")
DEFAULT_THU_MUC_ARTIFACT = Path("docs/du-lieu-do")
THU_MUC_DR = Path("docs/decisions")
KHOA_DR_BIET_TRUOC = "dr_biet_truoc_truot"
KHOA_LOP = "lop_chien_luoc"
KHOA_DR_THIET_KE = "dr_thiet_ke"
LOP_CAN_RO = "CAN_RO_THEO_LICH"
#: `DR-CAN-RO-01` §3 điều 2. `force_exit` = lệnh bị đóng khi backtest hết dữ liệu.
NHAN_THOAT_CAN_RO = frozenset({EXIT_CAN_RO, "stop_loss", "stoploss_on_exchange", "force_exit"})
_KHOI_LOP = re.compile(
    r"<!-- DR-CAN-RO-01:LOP:BEGIN -->\s*(?:```json)?\s*(\{.*?\})\s*(?:```)?\s*<!-- DR-CAN-RO-01:LOP:END -->", re.S
)


class ExitReasonThietKeError(ValueError):
    """§4.2 bước 3 chưa thoả — từ chối suất đầu tiên. Fail-closed."""


def la_slot_ung_vien(hypothesis_slot: str) -> bool:
    return bool(SLOT_UNG_VIEN.match(hypothesis_slot))


def duong_dan_artifact(hypothesis_slot: str, thu_muc: Path = DEFAULT_THU_MUC_ARTIFACT) -> Path:
    return thu_muc / f"{hypothesis_slot}-exit-reason-explore.json"


def _ty_le_time_stop(arm: str, ban_ghi: object) -> float:
    if not isinstance(ban_ghi, dict):
        raise ExitReasonThietKeError(f"arm {arm!r}: bản ghi không phải object")
    so_lenh = ban_ghi.get("so_lenh")
    ly_do = ban_ghi.get("exit_reason")
    if not isinstance(so_lenh, int) or isinstance(so_lenh, bool) or not isinstance(ly_do, dict):
        raise ExitReasonThietKeError(f"arm {arm!r}: thiếu `so_lenh` (int) hoặc `exit_reason` (object)")
    if so_lenh <= 0:
        # 0 lệnh ⇒ tỉ lệ không xác định; không được coi là 0% hay "trong dải" (N6).
        raise ExitReasonThietKeError(f"arm {arm!r}: 0 lệnh — tỉ lệ TIME_STOP không xác định")
    dem = list(ly_do.values())
    if not all(isinstance(v, int) and not isinstance(v, bool) and v >= 0 for v in dem):
        raise ExitReasonThietKeError(f"arm {arm!r}: `exit_reason` có số đếm không phải int ≥ 0")
    if sum(dem) != so_lenh:
        raise ExitReasonThietKeError(
            f"arm {arm!r}: tổng `exit_reason` ({sum(dem)}) ≠ `so_lenh` ({so_lenh}) — hiện vật không nhất quán"
        )
    return ly_do.get(EXIT_TIME_STOP, 0) / so_lenh


def _kiem_dr_biet_truoc(duong_dan: object, hypothesis_slot: str, repo_dir: Path) -> str | None:
    """`None` nếu giấy khai hợp lệ; ngược lại trả lý do."""
    if not isinstance(duong_dan, str) or not duong_dan:
        return f"`{KHOA_DR_BIET_TRUOC}` phải là đường dẫn (chuỗi)"
    p = Path(duong_dan)
    if p.is_absolute() or p.parent != THU_MUC_DR or p.suffix != ".md":
        return f"`{KHOA_DR_BIET_TRUOC}` phải trỏ tới một file .md ngay trong {THU_MUC_DR.as_posix()}/, nhận {duong_dan!r}"
    ly_do = _da_commit(p, repo_dir)
    if ly_do is not None:
        return f"DR khai trước: {ly_do}"
    noi_dung = (repo_dir / p).read_text(encoding="utf-8")
    if hypothesis_slot not in noi_dung or "DR-PHAN-QUYET-01" not in noi_dung:
        return f"DR khai trước {duong_dan} không nhắc đích danh {hypothesis_slot} và `DR-PHAN-QUYET-01`"
    return None


def _kiem_dr_thiet_ke_can_ro(duong_dan: object, hypothesis_slot: str, repo_dir: Path) -> str | None:
    """`DR-CAN-RO-01` §3 điều 1 — `None` nếu DR khai lớp hợp lệ; ngược lại trả lý do."""
    if not isinstance(duong_dan, str) or not duong_dan:
        return f"`{KHOA_DR_THIET_KE}` phải là đường dẫn (chuỗi)"
    p = Path(duong_dan)
    if p.is_absolute() or p.parent != THU_MUC_DR or p.suffix != ".md":
        return f"`{KHOA_DR_THIET_KE}` phải trỏ tới một file .md ngay trong {THU_MUC_DR.as_posix()}/, nhận {duong_dan!r}"
    ly_do = _da_commit(p, repo_dir)
    if ly_do is not None:
        return f"DR thiết kế: {ly_do}"
    noi_dung = (repo_dir / p).read_text(encoding="utf-8")
    if hypothesis_slot not in noi_dung or "DR-CAN-RO-01" not in noi_dung:
        return f"DR thiết kế {duong_dan} không nhắc đích danh {hypothesis_slot} và `DR-CAN-RO-01`"
    khop = _KHOI_LOP.findall(noi_dung)
    if len(khop) != 1:
        return f"DR thiết kế {duong_dan} phải có ĐÚNG MỘT khối `DR-CAN-RO-01:LOP`, thấy {len(khop)}"
    try:
        khoi = json.loads(khop[0])
    except json.JSONDecodeError as e:
        return f"khối `DR-CAN-RO-01:LOP` hỏng: {e}"
    if not isinstance(khoi, dict) or khoi.get("slot") != hypothesis_slot or khoi.get("lop") != LOP_CAN_RO:
        return f"khối `DR-CAN-RO-01:LOP` phải là {{\"slot\": \"{hypothesis_slot}\", \"lop\": \"{LOP_CAN_RO}\"}}, nhận {khoi!r}"
    return None


def _mien_dai_can_ro(kq: dict, lenh_that: dict, hypothesis_slot: str, repo_dir: Path) -> bool:
    """`True` ⇔ hiện vật thuộc lớp `CAN_RO_THEO_LICH` hợp lệ (được miễn phép so dải). Raise nếu khai lớp mà hỏng.

    Gọi SAU khi mọi arm đã qua `_ty_le_time_stop()` (hình dạng + tổng khớp `so_lenh`)."""
    if KHOA_LOP not in kq:
        return False
    if kq[KHOA_LOP] != LOP_CAN_RO:
        raise ExitReasonThietKeError(
            f"{hypothesis_slot}: `{KHOA_LOP}` = {kq[KHOA_LOP]!r} — chỉ nhận {LOP_CAN_RO!r} (`DR-CAN-RO-01`)"
        )
    loi_dr = _kiem_dr_thiet_ke_can_ro(kq.get(KHOA_DR_THIET_KE), hypothesis_slot, repo_dir)
    if loi_dr is not None:
        raise ExitReasonThietKeError(f"{hypothesis_slot}: khai lớp {LOP_CAN_RO} nhưng {loi_dr}")
    nhan_la = sorted({n for bg in lenh_that.values() for n in bg["exit_reason"]} - NHAN_THOAT_CAN_RO)
    if nhan_la:
        # §3 điều 2: có cửa thoát ngoài lớp ⇒ không phải rổ cân theo lịch thuần ⇒ áp dải như mọi slot.
        return False
    if sum(bg["exit_reason"].get(EXIT_CAN_RO, 0) for bg in lenh_that.values()) == 0:
        raise ExitReasonThietKeError(
            f"{hypothesis_slot}: khai lớp {LOP_CAN_RO} nhưng 0 lệnh `{EXIT_CAN_RO}` — lớp chưa được chứng minh"
        )
    return True


def kiem_exit_reason_thiet_ke(
    hypothesis_slot: str,
    *,
    repo_dir: Path = Path("."),
    thu_muc_artifact: Path = DEFAULT_THU_MUC_ARTIFACT,
) -> None:
    """Raise `ExitReasonThietKeError` nếu §4.2 bước 3 chưa thoả cho `hypothesis_slot`.

    `thu_muc_artifact` tương đối so với `repo_dir` (để kiểm đã commit)."""
    rel = duong_dan_artifact(hypothesis_slot, thu_muc_artifact)
    ly_do = _da_commit(rel, repo_dir)
    if ly_do is not None:
        raise ExitReasonThietKeError(
            f"chưa có số đếm `exit_reason` EXPLORE cho {hypothesis_slot} — {ly_do}. "
            f"Sinh bằng `do_td0193_lenh_nam_explore.py --ket-qua {rel.as_posix()}` (0 suất) rồi commit"
        )
    try:
        kq = json.loads((repo_dir / rel).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
        raise ExitReasonThietKeError(f"đọc lỗi {rel.as_posix()}: {e}") from e
    lenh_that = kq.get("lenh_that") if isinstance(kq, dict) else None
    if not isinstance(lenh_that, dict) or not lenh_that:
        raise ExitReasonThietKeError(f"{rel.as_posix()}: thiếu `lenh_that` (không có arm nào được đếm)")

    lo, hi = TIME_STOP_RATIO_BAND
    ty_le_theo_arm = {arm: _ty_le_time_stop(arm, ban_ghi) for arm, ban_ghi in lenh_that.items()}
    if _mien_dai_can_ro(kq, lenh_that, hypothesis_slot, repo_dir):
        return
    ngoai_dai = {arm: ty_le for arm, ty_le in ty_le_theo_arm.items() if not lo <= ty_le <= hi}
    if not ngoai_dai:
        return
    mo_ta = ", ".join(f"{a} = {v:.2%}" for a, v in sorted(ngoai_dai.items()))
    if KHOA_DR_BIET_TRUOC not in kq:
        raise ExitReasonThietKeError(
            f"{hypothesis_slot}: TIME_STOP ngoài dải [{lo:.0%}, {hi:.0%}] trên EXPLORE ({mo_ta}) — sửa thiết kế trước "
            f"khi tiêu suất, hoặc chủ dự án khai DR 'biết trước là trượt' qua khoá `{KHOA_DR_BIET_TRUOC}` "
            f"(`DR-PHAN-QUYET-01` §4.2 bước 3)"
        )
    loi_dr = _kiem_dr_biet_truoc(kq[KHOA_DR_BIET_TRUOC], hypothesis_slot, repo_dir)
    if loi_dr is not None:
        raise ExitReasonThietKeError(f"{hypothesis_slot}: TIME_STOP ngoài dải ({mo_ta}) và {loi_dr}")
