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
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from tool_d.ablation.chi_so_export import EXIT_TIME_STOP
from tool_d.dr015.cong_d35 import _da_commit
from tool_d.gates.thresholds import TIME_STOP_RATIO_BAND

#: Slot của ứng viên đi qua Idea Queue (MT-12). ZA LONG dùng slot `A-xx` nên không bị luật này áp.
SLOT_UNG_VIEN = re.compile(r"^IQ-\d{4}$")
DEFAULT_THU_MUC_ARTIFACT = Path("docs/du-lieu-do")
THU_MUC_DR = Path("docs/decisions")
KHOA_DR_BIET_TRUOC = "dr_biet_truoc_truot"


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
    ngoai_dai = {}
    for arm, ban_ghi in lenh_that.items():
        ty_le = _ty_le_time_stop(arm, ban_ghi)
        if not lo <= ty_le <= hi:
            ngoai_dai[arm] = ty_le
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
