"""H19 — backfill an toàn (TD-0091, spec dòng 4350, bài học LD-27/28).

Bốn ràng buộc spec đòi, và cách module này thi hành từng cái:

    (a) SAO LƯU TRƯỚC        -> `backup_data_dir()` chụp nguyên thư mục dữ
                                liệu sang nơi khác TRƯỚC khi tải.
    (b) GỘP, KHÔNG GHI ĐÈ     -> `verify_old_candles_preserved()` bắt được
                                mọi trường hợp dữ liệu cũ bị ghi đè theo
                                khoảng ngày yêu cầu (đúng cái bẫy suýt xoá
                                nhiều năm dữ liệu của Tool A).
    (c) VERIFY PHẦN CŨ        -> so ở mức NẾN, không ở mức byte của file.
        BYTE-FOR-BYTE           Gộp thêm nến MỚI làm bytes file đổi một cách
                                HỢP LỆ; so bytes cả file sẽ báo động giả 100%
                                và người ta sẽ tắt nó đi. Phép so đúng: mọi
                                nến trong khoảng CŨ phải còn nguyên, từng
                                trường một, không sai một chữ số.
    (d) TẢI HỎNG -> `unreadable` -> `read_candles()` trả `Measured.unreadable(...)`
                                khi file hỏng/không đọc được, KHÔNG trả
                                DataFrame rỗng (§0d.6, N6: cấm bịa 0).

🔴 Điều module này KHÔNG làm, nói thẳng: nó không tự tải dữ liệu. Việc tải
là của `freqtrade download-data` (đã kiểm chứng ở TD-0084). Module này là
LỚP GÁC quanh lần tải đó — chụp trước, so sau. Gộp hai việc vào một hàm sẽ
làm lớp gác phụ thuộc vào chính thứ nó phải giám sát.
"""

from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from tool_d.measurement.tri_state import Measured

if TYPE_CHECKING:  # pragma: no cover - chỉ để gợi ý kiểu, không nạp pandas khi import
    import pandas as pd

# Freqtrade ghi NHIỀU schema khác nhau trong cùng một thư mục dữ liệu —
# xác nhận trên 510 file thật của lockbox (TD-0084):
#     *-futures.feather / *-mark.feather : date, open, high, low, close, volume
#     *-funding_rate.feather             : date, funding_rate
# Lớp gác KHÔNG được khoá cứng vào schema OHLCV: bản đầu làm vậy và âm thầm
# bỏ qua đúng 102 file funding_rate (1/5 tổng dữ liệu) — mất bảo vệ cho
# chính dữ liệu DG7 (§4c) cần. Quy tắc chung: bắt buộc có cột `date`, cộng
# ÍT NHẤT một cột giá trị; digest chạy trên mọi cột, xếp theo tên.
TIMESTAMP_COLUMN = "date"
OHLCV_COLUMNS = ("date", "open", "high", "low", "close", "volume")  # tham chiếu, không phải ràng buộc


@dataclass(frozen=True)
class RangeDigest:
    """Dấu vân tay của MỘT file dữ liệu tại thời điểm chụp.

    Chỉ giữ khoảng [first_ts, last_ts] và digest của đúng khoảng đó — đủ để
    khẳng định "phần cũ còn nguyên" sau khi gộp, mà không phải giữ lại toàn
    bộ nến trong bộ nhớ (CALIB+WFO cỡ vài triệu nến).
    """

    name: str
    n_rows: int
    first_ts_ms: int
    last_ts_ms: int
    digest: str


def _digest_frame(df: "pd.DataFrame") -> str:
    """SHA-256 trên các cột nến, băm thẳng bộ nhớ numpy.

    🔴 Vì sao KHÔNG lặp từng dòng bằng Python: bản đầu của hàm này làm vậy
    và mất **> 10 phút** trên dữ liệu thật (510 file × ~5.300 nến, đo trong
    Docker) — một lớp gác chậm tới mức không ai chạy thì tương đương không
    có lớp gác. Băm theo cột là O(n) memcpy, xong trong vài giây.

    Ép `float64`/`int64` tường minh để digest không phụ thuộc dtype mà
    pandas suy ra; cùng một image Docker (N7) thì thứ tự byte cố định, mà
    digest cũng chỉ được so TRONG một lần chạy (chụp trước ↔ verify sau),
    không lưu xuống đĩa để so giữa các máy.
    """
    h = hashlib.sha256()
    h.update(df[TIMESTAMP_COLUMN].astype("int64").to_numpy().tobytes())
    for col in sorted(c for c in df.columns if c != TIMESTAMP_COLUMN):
        h.update(col.encode("utf-8"))
        h.update(df[col].to_numpy(dtype="float64").tobytes())
    return h.hexdigest()


def read_candles(path: Path) -> Measured:
    """Đọc một file nến. Hỏng/không đọc được -> `unreadable`, KHÔNG BAO GIỜ
    trả DataFrame rỗng (§0d.6 (d) của H19: cấm ghi/coi cache rỗng là dữ liệu).
    """
    import pandas as pd

    if not path.is_file():
        return Measured.unreadable(f"không có file: {path}")
    try:
        df = pd.read_feather(path)
    except Exception as exc:  # noqa: BLE001 — mọi lỗi đọc đều là `unreadable`
        return Measured.unreadable(f"{path.name}: đọc feather thất bại ({exc})")
    if TIMESTAMP_COLUMN not in df.columns:
        return Measured.unreadable(f"{path.name}: thiếu cột `{TIMESTAMP_COLUMN}`")
    if len(df.columns) < 2:
        return Measured.unreadable(f"{path.name}: chỉ có cột thời gian, không có cột giá trị nào")
    if df.empty:
        return Measured.unreadable(f"{path.name}: 0 nến — file rỗng KHÔNG phải dữ liệu")
    return Measured.ok(df)


def snapshot_dir(data_dir: Path, pattern: str = "*.feather") -> dict[str, RangeDigest]:
    """Chụp dấu vân tay MỌI file dữ liệu hiện có. Chạy TRƯỚC khi tải.

    File không đọc được bị BỎ QUA khỏi snapshot kèm không báo lỗi ở đây —
    nó vốn đã hỏng từ trước lần tải này, không phải thứ lần tải này làm hỏng;
    trách nhiệm của `read_candles()`/độ phủ (TD-0092), không phải của phép
    so "phần cũ còn nguyên".
    """
    out: dict[str, RangeDigest] = {}
    if not data_dir.is_dir():
        return out
    for path in sorted(data_dir.glob(pattern)):
        m = read_candles(path)
        if not m.is_ok():
            continue
        df = m.value
        ts = df["date"].astype("int64") // 1_000_000  # ns -> ms
        out[path.name] = RangeDigest(
            name=path.name,
            n_rows=len(df),
            first_ts_ms=int(ts.min()),
            last_ts_ms=int(ts.max()),
            digest=_digest_frame(df),
        )
    return out


def verify_old_candles_preserved(
    before: dict[str, RangeDigest], data_dir: Path
) -> list[str]:
    """(b)+(c) — với MỌI file đã có trước khi tải: mọi nến trong khoảng CŨ
    phải còn nguyên vẹn từng trường. Trả danh sách vi phạm; rỗng = an toàn.

    Ba dạng vi phạm bắt được:
      - file biến mất       (bị xoá)
      - thiếu nến trong khoảng cũ (bị ghi đè bằng dải hẹp hơn — bẫy LD-27)
      - nến cũ đổi giá trị  (bị ghi đè bằng dữ liệu khác)
    """
    errors: list[str] = []
    for name, snap in sorted(before.items()):
        m = read_candles(data_dir / name)
        if not m.is_ok():
            errors.append(f"{name}: mất hoặc không đọc được sau khi tải ({m.note})")
            continue
        df = m.value
        ts = df["date"].astype("int64") // 1_000_000
        old_part = df[(ts >= snap.first_ts_ms) & (ts <= snap.last_ts_ms)].reset_index(drop=True)
        if len(old_part) != snap.n_rows:
            errors.append(
                f"{name}: khoảng cũ có {snap.n_rows} nến, sau khi tải còn {len(old_part)} "
                "— dữ liệu cũ bị ghi đè/cắt bớt, KHÔNG phải gộp"
            )
            continue
        if _digest_frame(old_part) != snap.digest:
            errors.append(f"{name}: nến trong khoảng cũ ĐỔI GIÁ TRỊ sau khi tải")
    return errors


def backup_data_dir(*, source_dir: Path, dest_root: Path) -> Path:
    """(a) — sao lưu TRƯỚC khi tải. Ghi đè bản sao lưu cũ (bản sao lưu phản
    ánh trạng thái ngay trước lần tải này, không phải sổ append-only).

    Raise nếu `source_dir` không tồn tại — không tự tạo thư mục rỗng rồi coi
    như "đã sao lưu" (fail-closed).
    """
    if not source_dir.is_dir():
        raise FileNotFoundError(f"{source_dir} không tồn tại — không có gì để sao lưu")
    dest = dest_root / source_dir.name
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(source_dir, dest)
    return dest
