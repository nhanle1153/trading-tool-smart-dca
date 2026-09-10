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


def timestamps_ms(df: "pd.DataFrame") -> "pd.Series":
    """Mốc thời gian của từng nến, tính bằng **mili-giây** kể từ epoch.

    🔴 Không dùng thẳng `astype("int64")`: kết quả phụ thuộc ĐƠN VỊ của
    cột (`datetime64[ms]` ra ms, `datetime64[ns]` ra ns). Freqtrade hiện
    ghi `datetime64[ms, UTC]`, nhưng dựa vào đó là dựa vào một chi tiết
    có thể đổi theo phiên bản — và nếu hai file khác đơn vị thì mọi phép
    so mốc thời gian sai lệch 10^6 lần mà không báo lỗi. Chuẩn hoá về ms
    trước rồi mới đổi sang số nguyên.
    """
    import pandas as pd

    return pd.to_datetime(df[TIMESTAMP_COLUMN], utc=True).astype("datetime64[ms, UTC]").astype("int64")


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
    h.update(timestamps_ms(df).to_numpy().tobytes())
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
        ts = timestamps_ms(df)
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
        ts = timestamps_ms(df)
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


class BackupVerificationError(RuntimeError):
    """TD-0203 — bản sao lưu vừa chép KHÔNG khớp nguồn. Bản sao lưu CŨ (nếu
    có) chưa hề bị đụng tới khi lỗi này raise — xem thứ tự trong
    `backup_data_dir()`."""


def _file_digest(path: Path) -> str:
    """SHA-256 theo BYTES thô của một file, đọc theo khối để không nạp cả
    file (~vài trăm MB mỗi lần chạy TD-0200) vào bộ nhớ cùng lúc.

    🔴 KHÔNG dùng `_digest_frame()`: hàm đó giả định nội dung là bảng nến
    (`pandas`) — bản sao lưu là một THƯ MỤC BẤT KỲ, phải đúng cho mọi file,
    kể cả file không phải `.feather`."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _verify_copy_matches_source(*, source_dir: Path, copied_dir: Path) -> None:
    """So NGUỒN với bản vừa chép: cùng tập tên file tương đối, cùng kích
    thước, cùng sha256 từng file. Raise `BackupVerificationError` ở vi
    phạm ĐẦU TIÊN gặp phải (đủ để từ chối bản sao lưu; không cần liệt kê
    hết — người gọi giữ nguyên bản CŨ khi hàm này raise).
    """
    src_files = sorted(p.relative_to(source_dir) for p in source_dir.rglob("*") if p.is_file())
    dst_files = sorted(p.relative_to(copied_dir) for p in copied_dir.rglob("*") if p.is_file())
    if src_files != dst_files:
        thieu = set(src_files) - set(dst_files)
        thua = set(dst_files) - set(src_files)
        raise BackupVerificationError(
            f"tập file lệch sau khi chép: thiếu {sorted(map(str, thieu))}, "
            f"thừa {sorted(map(str, thua))}"
        )
    for rel in src_files:
        src_f, dst_f = source_dir / rel, copied_dir / rel
        src_size, dst_size = src_f.stat().st_size, dst_f.stat().st_size
        if src_size != dst_size:
            raise BackupVerificationError(
                f"{rel}: kích thước lệch — nguồn {src_size} bytes, bản chép {dst_size} bytes"
            )
        if _file_digest(src_f) != _file_digest(dst_f):
            raise BackupVerificationError(f"{rel}: sha256 lệch sau khi chép — nội dung khác nguồn")


def backup_data_dir(*, source_dir: Path, dest_root: Path) -> Path:
    """(a) — sao lưu TRƯỚC khi tải. Ghi đè bản sao lưu cũ (bản sao lưu phản
    ánh trạng thái ngay trước lần tải này, không phải sổ append-only).

    Raise nếu `source_dir` không tồn tại — không tự tạo thư mục rỗng rồi coi
    như "đã sao lưu" (fail-closed).

    🔴 TD-0203 — trước bản vá này, hàm chỉ có ba dòng (`rmtree` → `copytree`
    → `return`), KHÔNG kiểm bản sao lưu có thật sự đáp xuống đích hay
    không — người gọi in `✅ đã sao lưu` chỉ vì không có exception. Bằng
    chứng thật: `--snapshot-before` chạy TD-0093 (07/09/2026) không để lại
    một byte nào ở đích, mà lệnh vẫn báo thành công (`docs/research-log.md`
    09-10/09/2026). Nay chép ra một thư mục TẠM cạnh đích, ĐỐI CHIẾU byte-
    đối-byte với nguồn (`_verify_copy_matches_source`), rồi MỚI thay thế
    bản cũ — theo đúng thứ tự dưới đây, không đảo:

        chép -> dest.tmp
        đối chiếu dest.tmp với source_dir  (lệch -> raise, dest.tmp bị xoá,
                                             dest CŨ giữ nguyên, KHÔNG mất)
        rmtree(dest) NẾU đối chiếu qua      (chỉ xoá cái cũ SAU KHI có cái
                                             mới đã được xác nhận đúng)
        dest.tmp.rename(dest)

    Bản CŨ trước đây bị `rmtree` NGAY DÒNG ĐẦU, trước cả khi `copytree` bắt
    đầu — copy hỏng giữa chừng (hết đĩa, container bị giết, …) từng khiến
    MẤT CẢ HAI bản, đúng lúc cần bản sao lưu nhất.

    🔑 Phép so là byte-đối-byte, KHÔNG phải ở mức nến như
    `verify_old_candles_preserved()` — hàm đó phải khoan dung việc gộp
    THÊM nến mới làm bytes đổi HỢP LỆ; sao lưu thì không gộp gì cả, một
    byte lệch là một byte sai.

    ⚠️ Điều bản vá này KHÔNG giải quyết được, nói thẳng: nếu `dest_root`
    trỏ tới một nơi không bền (vd một thư mục không được mount ra ngoài
    container, sẽ mất khi container bị `--rm`), phép đối chiếu TRONG CÙNG
    một lần chạy vẫn PASS — file THẬT SỰ ở đó tại thời điểm kiểm, chỉ là
    nó biến mất SAU KHI tiến trình kết thúc. Không có phép kiểm nào chạy
    trong một tiến trình DUY NHẤT phát hiện được điều này (không thể biết
    trước tương lai của chính filesystem mình đang ghi); đó là lý do
    `entrypoints/backfill_data.py` đổi mặc định `--backup-root` sang một
    đường dẫn NẰM TRONG cây làm việc (`runs/`, giống quy ước của
    `--snapshot-out`) thay vì một heuristic đoán "đây có phải volume thật
    không" — mọi heuristic kiểu đó (so `st_dev`, …) báo động giả trên host
    (giả thuyết "route thứ ba" của phiên `-46`, TD-0200: hàm này là Python
    thuần, chạy được cả trên host lẫn trong container).
    """
    if not source_dir.is_dir():
        raise FileNotFoundError(f"{source_dir} không tồn tại — không có gì để sao lưu")
    resolved_source, resolved_root = source_dir.resolve(), dest_root.resolve()
    if str(resolved_root) == resolved_root.anchor:
        raise ValueError(f"dest_root ({dest_root}) là gốc hệ thống file — từ chối, quá nguy hiểm")
    if resolved_root == resolved_source or resolved_root in resolved_source.parents:
        raise ValueError(f"dest_root ({dest_root}) trùng hoặc chứa source_dir ({source_dir})")

    dest = dest_root / source_dir.name
    tmp = dest_root / f".{source_dir.name}.tmp-backup"
    if tmp.exists():
        shutil.rmtree(tmp)
    shutil.copytree(source_dir, tmp)
    try:
        _verify_copy_matches_source(source_dir=source_dir, copied_dir=tmp)
    except BackupVerificationError:
        shutil.rmtree(tmp, ignore_errors=True)
        raise

    if dest.exists():
        shutil.rmtree(dest)
    tmp.rename(dest)
    return dest
