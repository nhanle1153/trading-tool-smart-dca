"""TD-0209 — file heartbeat: bằng chứng "tiến trình còn sống" ghi ra đĩa.

Chỉ tầng THUẦN (ghi/đọc/đánh giá tuổi) — CHƯA nối vào Freqtrade thật (chưa
có launcher live, D10-D12 chưa mở). Cùng khuôn đã dùng cho
`risk_supervisor.py`/`validate_credentials_for_live()`: hàm thuần trước,
nối vào tiến trình thật là việc SAU.

Payload mang BA trường, không phải một mốc thời gian trơn:
`thoi_diem` (proof-of-life — ghi mỗi vòng lặp), `trang_thai` (trạng thái
Freqtrade tại thời điểm ghi — chuỗi tự do, module này không hardcode enum
của Freqtrade để tránh import ngược), `trang_thai_tu_luc` (mốc `trang_thai`
HIỆN TẠI bắt đầu). Lý do cần trường thứ ba: tên việc TD-0209 đòi bắt được
CẢ HAI ca — tiến trình chết/treo (đo bằng tuổi của `thoi_diem`) VÀ tiến
trình còn sống nhưng bot đã dừng (đo bằng THỜI GIAN Ở TRẠNG THÁI đó, không
phải một that điểm) — nếu chỉ có `thoi_diem` thì không phân biệt được hai
ca khi cần chẩn đoán (`heartbeat_watchdog.py` là nơi dùng cả ba).

N6 — tri-state, không bịa số: đọc heartbeat trả `KetQuaDocHeartbeat` với
`loi` khác `None` cho MỌI ca không đọc được rõ ràng (file không tồn tại,
JSON hỏng, thiếu trường, `thoi_diem` không parse được) — không bao giờ
coi "đọc lỗi" là "đang OK", đúng chiều fail-closed như `trang_thai_tai_khoan()`.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


class HeartbeatError(ValueError):
    """Lỗi đầu vào của tầng ghi/đọc heartbeat — fail-closed, không đoán."""


@dataclass(frozen=True)
class Heartbeat:
    thoi_diem: datetime
    trang_thai: str
    trang_thai_tu_luc: datetime


@dataclass(frozen=True)
class KetQuaDocHeartbeat:
    """Cùng khuôn `KetQuaEndpoint` (`risk_supervisor.py`) — `loi=None` là
    MỘT sự thật rõ ràng ("đọc được, không có gì bất thường ở tầng đọc"),
    không phải trạng thái mặc định."""

    heartbeat: Heartbeat | None
    loi: str | None

    @property
    def doc_duoc(self) -> bool:
        return self.loi is None


def tinh_trang_thai_tu_luc(
    heartbeat_cu: Heartbeat | None, trang_thai_moi: str, *, now: datetime
) -> datetime:
    """`trang_thai_tu_luc` của lần ghi MỚI: giữ nguyên mốc cũ nếu trạng thái
    KHÔNG đổi so với lần ghi trước; đặt lại thành `now` nếu trạng thái vừa
    chuyển (hoặc đây là lần ghi đầu tiên, `heartbeat_cu is None`).

    Hàm THUẦN riêng (không gộp vào `ghi_heartbeat`) để test được logic
    "khi nào coi là một trạng thái MỚI" độc lập với việc ghi file thật.
    """
    if heartbeat_cu is not None and heartbeat_cu.trang_thai == trang_thai_moi:
        return heartbeat_cu.trang_thai_tu_luc
    return now


def ghi_heartbeat(duong_dan: Path, *, trang_thai: str, now: datetime, heartbeat_cu: Heartbeat | None = None) -> None:
    """Ghi ATOMIC (tmp file + `os.replace`) — watchdog đọc file này từ một
    tiến trình KHÁC, đang chạy song song; ghi trực tiếp không tmp có thể
    để watchdog đọc trúng một file JSON dở dang giữa lúc ghi.

    `heartbeat_cu` — truyền vào nếu tầng gọi đã có heartbeat lần trước
    trong bộ nhớ (tránh đọc lại đĩa mỗi vòng lặp chỉ để biết trạng thái
    CŨ); bỏ trống thì coi như đây là lần ghi đầu tiên (`trang_thai_tu_luc
    = now`) — an toàn hơn suy đoán sai một mốc cũ không có thật.
    """
    if not trang_thai:
        raise HeartbeatError("trang_thai rỗng — không có gì để ghi")
    tu_luc = tinh_trang_thai_tu_luc(heartbeat_cu, trang_thai, now=now)
    payload = {
        "thoi_diem": now.astimezone(timezone.utc).isoformat(),
        "trang_thai": trang_thai,
        "trang_thai_tu_luc": tu_luc.astimezone(timezone.utc).isoformat(),
    }
    tmp = duong_dan.with_suffix(duong_dan.suffix + ".tmp")
    tmp.write_text(json.dumps(payload), encoding="utf-8")
    os.replace(tmp, duong_dan)


def _parse_iso(gia_tri: object) -> datetime:
    if not isinstance(gia_tri, str):
        raise HeartbeatError(f"mốc thời gian không phải chuỗi: {gia_tri!r}")
    return datetime.fromisoformat(gia_tri)


def doc_heartbeat(duong_dan: Path) -> KetQuaDocHeartbeat:
    """KHÔNG BAO GIỜ raise — mọi lỗi đọc được gói vào `KetQuaDocHeartbeat.loi`
    (N6: đây là tầng biên đọc file bên ngoài, watchdog cần một GIÁ TRỊ để
    quyết định cảnh báo, không phải một exception làm sập vòng lặp giám sát
    — sập vòng lặp giám sát vì chính thứ nó giám sát là nghịch lý của cả
    tính năng)."""
    try:
        tho = json.loads(duong_dan.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return KetQuaDocHeartbeat(heartbeat=None, loi=f"không tìm thấy file heartbeat: {duong_dan}")
    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
        return KetQuaDocHeartbeat(heartbeat=None, loi=f"lỗi đọc/parse heartbeat: {exc}")

    try:
        heartbeat = Heartbeat(
            thoi_diem=_parse_iso(tho["thoi_diem"]),
            trang_thai=str(tho["trang_thai"]),
            trang_thai_tu_luc=_parse_iso(tho["trang_thai_tu_luc"]),
        )
    except (KeyError, HeartbeatError, ValueError) as exc:
        return KetQuaDocHeartbeat(heartbeat=None, loi=f"heartbeat thiếu trường/sai định dạng: {exc}")
    return KetQuaDocHeartbeat(heartbeat=heartbeat, loi=None)


def tuoi_giay(heartbeat: Heartbeat, *, now: datetime) -> float:
    """Âm (heartbeat ở TƯƠNG LAI so với `now`) là dấu hiệu đồng hồ hai máy
    lệch — KHÔNG kẹp về 0, để tầng gọi tự quyết định có coi là bất thường
    hay không thay vì bị che giấu ở đây."""
    return (now - heartbeat.thoi_diem).total_seconds()


def tuoi_trang_thai_giay(heartbeat: Heartbeat, *, now: datetime) -> float:
    return (now - heartbeat.trang_thai_tu_luc).total_seconds()
