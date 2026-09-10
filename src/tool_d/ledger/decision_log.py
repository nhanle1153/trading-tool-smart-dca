"""TD-0144 — `dedup_key` tất định + cửa ghi append-only cho Decision Log
(§8.3, LD-17/LD-19/LD-20). Canh bởi 🔴 **L-Z45**.

🔴 **Bug Tool A số (7)**, spec dòng 4340: *bản ghi trùng khi chạy lại
cùng timerange*. Tool A đo được **~7–9 bản ghi cho MỘT sự kiện thật**,
vì mỗi lần chạy lại backtest ghi thêm một bộ bản ghi gần giống hệt vào
file cũ (đặt tên theo mốc thời gian LỊCH SỬ, không theo giờ chạy). Nó
không ảnh hưởng lệnh nào, nên **không ai thấy** — nhưng nó phá huỷ mọi
phân tích dựa trên ĐẾM, mà H-1/H-3/H-4 của GATE đều là TỈ LỆ.

🔴 **Đặt ở `ledger/` chứ không phải `wfo/`, có chủ đích.** Việc mở nó là
TD-0144 (khối D3), nhưng Decision Log là sổ của §8.3 — chiến lược chạy
thật cũng ghi vào đây. Để trong `wfo/` sẽ ngụ ý "chỉ dùng cho
walk-forward", và hệ quả gần như chắc chắn là sau này ai đó viết lại một
bản thứ hai cho đường live, rồi hai bản trôi lệch nhau.

════ Định nghĩa "MỘT sự kiện thật" (spec §8.3) ════

Mỗi **TRANCHE** là một sự kiện vào lệnh riêng → khoá theo `order_id` của
TỪNG tranche, **KHÔNG theo `trade_id`**. Khoá theo `trade_id` sẽ gộp ba
tranche của cùng một trade thành một, tức mất đúng thứ Tool D sinh ra để
đo.

════ Append-only tuyệt đối (LD-20) ════

Bản ghi cũ **KHÔNG BAO GIỜ** sửa/xoá, kể cả khi biết là sai — ghi bản
ghi MỚI mang `corrects: <dedup_key cũ>`. Module này chỉ mở file ở chế độ
nối thêm; không có đường nào trong đây sửa được một dòng đã ghi.

════ Đồng thời (L-Z45: "kể cả khi có tiến trình song song ghi cùng file") ════

Đọc-tập-khoá rồi mới ghi là một thao tác PHẢI nguyên tử: giữa hai bước
đó, một tiến trình khác có thể ghi đúng khoá ấy, và cả hai cùng thấy
"chưa có" rồi cùng ghi. Nên toàn bộ đọc+ghi nằm trong một `flock` độc
quyền trên chính file sổ.

Module này do đó cần POSIX (`fcntl`) — đúng môi trường chạy thật của
Tool D: mọi thứ chạy trong container Linux (N7, và quy tắc parity: cùng
một Dockerfile cho local–staging–prod). Không có nhánh dự phòng "chạy
tạm không khoá" trên nền khác: một cửa ghi im lặng bỏ khoá là cửa ghi
sinh bản ghi trùng đúng lúc có nhiều tiến trình, tức đúng lúc cần nó
nhất.
"""

from __future__ import annotations

import fcntl
import json
import os
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

# Trường bắt buộc để dựng khoá, theo đúng bốn dòng của spec §8.3.
TRUONG_KHOA: dict[str, tuple[str, ...]] = {
    "VAO_RA_LENH": ("exchange_order_id",),
    "DOI_SL": ("sl_order_id_new",),
    "PLAN": ("pair", "candle_ts", "block"),
    "GATE_CHECK": ("trade_id", "candle_ts", "gate"),
}

# TD-0201 — §8.3 KHÔNG định nghĩa trường phân biệt NGUỒN bản ghi (backtest /
# dry-run / live), nhưng module này CỐ Ý phục vụ cả ba (xem docstring đầu
# file: "chiến lược chạy thật cũng ghi vào đây"). Thiếu trường này, một lần
# đọc sổ để đếm/báo cáo không tách được lệnh backtest với lệnh dry-run/live
# — đúng lỗi Tool A đã dính (đếm phóng đại vì gộp cả hai nguồn).
#
# KHÔNG tham gia `TRUONG_KHOA`/`dedup_key()`: cùng một sự kiện thật (cùng
# `exchange_order_id`, v.v.) không đổi khoá chỉ vì đổi nguồn ghi — đó là hai
# trục độc lập. `nguon` là một trường NỘI DUNG bắt buộc, không phải một
# thành phần khoá.
NGUON_HOP_LE = ("backtest", "dry_run", "live")


class DecisionLogError(RuntimeError):
    """Bản ghi không dựng được khoá, hoặc vi phạm bất biến append-only.
    Fail-closed: raise TRƯỚC khi chạm file — sổ append-only không có
    đường lùi."""


def dedup_key(record: Mapping[str, Any]) -> str:
    """Khoá tất định của một bản ghi. Cùng sự kiện thật → cùng khoá, ở
    mọi lần chạy, trên mọi máy.

    TỪ CHỐI (không tự bịa khoá):
      • thiếu `loai`, hoặc `loai` không thuộc bốn loại của §8.3;
      • thiếu `nguon`, hoặc `nguon` không thuộc {backtest, dry_run, live}
        (TD-0201) — `nguon` KHÔNG tham gia khoá, nhưng bị kiểm ở ĐÂY vì
        đây là điểm nghẽn DUY NHẤT mọi bản ghi đi qua trước khi chạm file
        (bài học TD-0150: vá rải rác ở nhiều hàm để lọt qua điểm chưa vá);
      • thiếu bất kỳ trường dựng khoá nào;
      • trường dựng khoá rỗng/`None`. Đây KHÔNG phải bắt bẻ hình thức:
        khoá `":" * n` dựng từ các trường rỗng sẽ TRÙNG NHAU giữa những
        sự kiện hoàn toàn khác nhau, và hậu quả là các bản ghi khác nhau
        âm thầm nuốt lẫn nhau — hỏng nặng hơn hẳn so với ghi trùng.
    """
    loai = record.get("loai")
    if loai not in TRUONG_KHOA:
        raise DecisionLogError(
            f"`loai` = {loai!r} không thuộc {sorted(TRUONG_KHOA)} (§8.3). "
            "TỪ CHỐI dựng khoá — không đoán loại bản ghi."
        )
    nguon = record.get("nguon")
    if nguon not in NGUON_HOP_LE:
        raise DecisionLogError(
            f"`nguon` = {nguon!r} không thuộc {NGUON_HOP_LE} (TD-0201). "
            "TỪ CHỐI ghi — không mặc định 'chắc là backtest': một bản ghi "
            "không khai nguồn là một bản ghi không thể tách khỏi các nguồn "
            "khác khi đếm/báo cáo sau này, đúng lỗi Tool A đã dính."
        )
    phan: list[str] = []
    for ten in TRUONG_KHOA[loai]:
        if ten not in record:
            raise DecisionLogError(f"Bản ghi {loai} thiếu trường dựng khoá `{ten}`.")
        gia_tri = record[ten]
        if gia_tri is None or str(gia_tri).strip() == "":
            raise DecisionLogError(
                f"Bản ghi {loai} có `{ten}` rỗng — khoá dựng từ trường rỗng sẽ "
                "trùng với mọi bản ghi rỗng khác và làm chúng nuốt lẫn nhau."
            )
        phan.append(str(gia_tri))
    return ":".join(phan)


def doc_khoa_da_co(path: Path) -> set[str]:
    """Tập khoá đã có trong sổ. File chưa tồn tại → tập rỗng (sổ mới).

    Dòng hỏng (không phải JSON) → raise, KHÔNG bỏ qua: bỏ qua một dòng
    hỏng nghĩa là coi khoá trong đó như chưa tồn tại, và lần ghi kế tiếp
    sẽ tạo đúng bản trùng mà `L-Z45` tồn tại để chặn.
    """
    if not path.exists():
        return set()
    khoa: set[str] = set()
    for so_dong, dong in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not dong.strip():
            continue
        try:
            ban_ghi = json.loads(dong)
        except json.JSONDecodeError as exc:
            raise DecisionLogError(
                f"{path}:{so_dong} không phải JSON hợp lệ — TỪ CHỐI đọc tiếp. "
                "Bỏ qua dòng hỏng sẽ làm khoá trong đó bị coi như chưa tồn tại."
            ) from exc
        khoa.add(ban_ghi.get("dedup_key") or dedup_key(ban_ghi))
    return khoa


def _ghi_mot_dong(f, ban_ghi: Mapping[str, Any], khoa: str) -> None:
    f.seek(0, os.SEEK_END)
    f.write(json.dumps({**ban_ghi, "dedup_key": khoa}, ensure_ascii=False, sort_keys=True) + "\n")
    f.flush()
    os.fsync(f.fileno())


def ghi_neu_chua_co(path: Path, record: Mapping[str, Any]) -> bool:
    """Ghi một bản ghi. Trả `True` nếu ĐÃ ghi, `False` nếu khoá đã tồn
    tại (**no-op**, không đọc-sửa-ghi-đè — spec §8.3).

    Toàn bộ "đọc tập khoá → quyết định → nối thêm" nằm trong một `flock`
    độc quyền, nên hai tiến trình cùng ghi một khoá chỉ có đúng một
    thắng. Không khoá thì cả hai cùng thấy "chưa có" rồi cùng ghi.

    `corrects` (LD-20): bản sửa là một bản ghi MỚI trỏ về khoá cũ. Khoá
    được trỏ tới phải TỒN TẠI trong sổ — bản sửa trỏ vào hư không thì
    không sửa được gì, mà lại làm sổ trông như đã được sửa.
    """
    khoa = dedup_key(record)  # dựng khoá TRƯỚC khi mở file: sai thì không chạm sổ
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a+", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            f.seek(0)
            da_co = doc_khoa_da_co(path)
            if khoa in da_co:
                return False
            sua = record.get("corrects")
            if sua is not None and sua not in da_co:
                raise DecisionLogError(
                    f"Bản ghi khai `corrects` = {sua!r} nhưng khoá đó KHÔNG có "
                    f"trong {path}. TỪ CHỐI — bản sửa trỏ vào hư không làm sổ "
                    "trông như đã được sửa trong khi chưa sửa gì."
                )
            _ghi_mot_dong(f, record, khoa)
            return True
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def ghi_nhieu(path: Path, records: Iterable[Mapping[str, Any]]) -> int:
    """Ghi một loạt bản ghi, trả về SỐ DÒNG thực sự được thêm.

    🔴 Đây là hàm mà `L-Z45` đo: chạy hai lần liên tiếp cùng một
    timerange thì lần thứ hai phải trả về **đúng 0**.

    Cố ý KHÔNG gom cả loạt vào một lần khoá: một tiến trình ghi loạt dài
    sẽ giữ khoá lâu và chặn mọi tiến trình khác. Đổi lại, một loạt bị
    ngắt giữa chừng sẽ ghi được phần đầu — điều đó ĐÚNG với sổ
    append-only (phần đã ghi là sự thật đã xảy ra) và lần chạy lại sẽ
    no-op đúng phần đó rồi ghi tiếp phần còn thiếu.
    """
    return sum(1 for r in records if ghi_neu_chua_co(path, r))
