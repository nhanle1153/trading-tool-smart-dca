"""TD-0092 — H19 phần 2: chỉ số ĐỘ PHỦ DỮ LIỆU (spec dòng 4350, LD-28).

Spec đòi hai thứ, và thứ hai mới là thứ khó:

    1. "Kèm chỉ số ĐỘ PHỦ DỮ LIỆU riêng" — đếm được, in ra được.
    2. 🔴 "**cấm suy nguyên nhân gốc từ khoảng trống mà không kiểm trực
       tiếp nguồn**" — Tool A mất nhiều ngày vì quy một khoảng trống cho
       "sàn thiếu dữ liệu", trong khi lỗi nằm ở script của chính mình.

Điều (2) là một quy tắc về HÀNH VI CON NGƯỜI, nên nếu chỉ viết vào tài
liệu thì nó sẽ bị vi phạm đúng lúc người ta đang vội. Module này biến nó
thành ràng buộc KIỂU DỮ LIỆU, cùng thủ pháp `Measured` dùng để cấm bịa số:

    • `Gap` KHÔNG có trường nào chứa được một phỏng đoán nguyên nhân.
    • `Coverage.gap_cause` là `Measured`, và `compute_coverage()` LUÔN
      trả về nó ở trạng thái `pending("chưa kiểm nguồn trực tiếp")`.
    • Cách DUY NHẤT để nó thành `ok(...)` là gọi một trong hai hàm quy
      trách nhiệm, và cả hai đều đòi **dữ liệu thật từ nguồn**, không
      nhận lời khai:
         - `attribute_from_listing_date()` — đối chiếu `onboardDate` của
           chính sàn (metadata thật).
         - `attribute_from_source_probe()` — hỏi lại sàn ĐÚNG cửa sổ bị
           trống. Sàn trả về nến ⇒ **lỗi của ta**. Sàn không có ⇒ sàn
           thật sự thiếu. Đây chính là phép kiểm mà Tool A đã bỏ qua, và
           nó rẻ tới mức không có lý do gì để bỏ qua.

Không có đường nào khác đặt được `gap_cause`, nên một báo cáo độ phủ
không bao giờ có thể mang một nguyên nhân do người viết code đoán ra.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import TYPE_CHECKING

from tool_d.data.backfill_guard import timestamps_ms
from tool_d.measurement.tri_state import Measured

if TYPE_CHECKING:  # pragma: no cover
    import pandas as pd

# Chỉ các khung Tool D dùng (§3.3c: 1H chính, 4H/1D informative, 5m
# timeframe_detail). 15m KHÔNG có ở đây — spec đã xoá (L-Z33).
TIMEFRAME_MS: dict[str, int] = {
    "5m": 5 * 60_000,
    "1h": 60 * 60_000,
    "4h": 4 * 60 * 60_000,
    "8h": 8 * 60 * 60_000,  # funding rate
    "1d": 24 * 60 * 60_000,
}


class GapCause(Enum):
    """Nguyên nhân khoảng trống — chỉ gán được từ dữ liệu nguồn thật."""

    CHUA_NIEM_YET = "chưa niêm yết tại thời điểm đó"
    SAN_KHONG_CO = "sàn thật sự không có dữ liệu (đã hỏi lại đúng cửa sổ)"
    LOI_CUA_TA = "🔴 sàn CÓ dữ liệu — lỗi ở phía ta (script tải/ghi)"

    def __str__(self) -> str:
        # `Measured.render()` gọi `str(value)`. Không có dòng này thì báo
        # cáo in ra "GapCause.LOI_CUA_TA" — đúng về kiểu, vô dụng với người
        # đọc, mà báo cáo độ phủ tồn tại là để người đọc.
        return self.value


@dataclass(frozen=True)
class Gap:
    """Một khoảng trống. CỐ Ý không có trường nào để ghi nguyên nhân —
    nguyên nhân thuộc về `Coverage.gap_cause` và chỉ đến từ nguồn thật."""

    start_ms: int
    end_ms: int
    n_missing: int


@dataclass(frozen=True)
class Coverage:
    name: str
    timeframe: str
    range_start_ms: int
    range_end_ms: int
    expected: int
    actual: int
    gaps: tuple[Gap, ...]
    gap_cause: Measured

    @property
    def ratio(self) -> float:
        return 0.0 if self.expected == 0 else self.actual / self.expected

    @property
    def is_full(self) -> bool:
        return self.actual >= self.expected

    def render(self) -> str:
        """Một dòng báo cáo. Nguyên nhân LUÔN đi qua `Measured.render()` —
        không có nhánh nào in được một nguyên nhân chưa kiểm nguồn."""
        head = (
            f"{self.name:<46s} {self.timeframe:<4s} "
            f"{self.actual:>7d}/{self.expected:<7d} = {self.ratio:6.1%}"
        )
        if self.is_full and not self.gaps:
            return head + "  đủ"
        return head + f"  {len(self.gaps)} khoảng trống — nguyên nhân: {self.gap_cause.render()}"


def expected_candles(*, timeframe: str, range_start_ms: int, range_end_ms: int) -> int:
    """Số nến ĐÁNG LẼ có trong [start, end]. Khung lạ -> raise, không đoán
    (fail-closed: đoán sai bước nến làm mọi tỉ lệ phủ sai theo)."""
    if timeframe not in TIMEFRAME_MS:
        raise ValueError(f"khung thời gian không nhận diện được: {timeframe!r}")
    if range_end_ms < range_start_ms:
        raise ValueError("range_end_ms < range_start_ms")
    step = TIMEFRAME_MS[timeframe]
    return (range_end_ms - range_start_ms) // step + 1


def compute_coverage(
    df: "pd.DataFrame",
    *,
    name: str,
    timeframe: str,
    range_start_ms: int,
    range_end_ms: int,
) -> Coverage:
    """Đếm độ phủ của `df` trong khoảng yêu cầu.

    🔴 Đếm theo KHOẢNG YÊU CẦU, không theo min/max của chính file: một file
    thiếu hẳn phần đuôi mà đếm theo min/max của nó thì luôn ra 100% — đúng
    loại chỉ số tự khen mình.

    `gap_cause` trả về LUÔN là `pending`. Muốn biết nguyên nhân thì phải
    gọi một trong hai hàm quy trách nhiệm bên dưới, và chúng đòi dữ liệu
    nguồn thật.
    """
    step = TIMEFRAME_MS[timeframe]
    exp = expected_candles(
        timeframe=timeframe, range_start_ms=range_start_ms, range_end_ms=range_end_ms
    )
    ts = timestamps_ms(df).to_numpy()
    ts = ts[(ts >= range_start_ms) & (ts <= range_end_ms)]
    present = set(ts.tolist())

    gaps: list[Gap] = []
    gap_start: int | None = None
    prev: int | None = None
    for t in range(range_start_ms, range_end_ms + 1, step):
        if t in present:
            if gap_start is not None:
                gaps.append(
                    Gap(
                        start_ms=gap_start,
                        end_ms=prev if prev is not None else gap_start,
                        n_missing=(prev - gap_start) // step + 1 if prev is not None else 1,
                    )
                )
                gap_start = None
        else:
            if gap_start is None:
                gap_start = t
            prev = t
    if gap_start is not None:
        gaps.append(
            Gap(
                start_ms=gap_start,
                end_ms=prev if prev is not None else gap_start,
                n_missing=(prev - gap_start) // step + 1 if prev is not None else 1,
            )
        )

    return Coverage(
        name=name,
        timeframe=timeframe,
        range_start_ms=range_start_ms,
        range_end_ms=range_end_ms,
        expected=exp,
        actual=len(present),
        gaps=tuple(gaps),
        gap_cause=Measured.pending(
            "chưa kiểm nguồn trực tiếp — cấm suy nguyên nhân từ khoảng trống (H19/LD-28)"
        ),
    )


def attribute_from_listing_date(coverage: Coverage, *, onboard_date_ms: int) -> Coverage:
    """Quy trách nhiệm bằng metadata THẬT của sàn (`exchangeInfo.onboardDate`).

    Chỉ áp được khi MỌI khoảng trống nằm hoàn toàn trước ngày lên sàn —
    tức mã chưa tồn tại, không có gì để thiếu. Còn khoảng trống nào sau
    ngày đó thì hàm này TỪ CHỐI kết luận (giữ nguyên `pending`), vì phần
    đó cần hỏi lại nguồn theo cửa sổ cụ thể.
    """
    if not coverage.gaps:
        return coverage
    if all(g.end_ms < onboard_date_ms for g in coverage.gaps):
        return replace(coverage, gap_cause=Measured.ok(GapCause.CHUA_NIEM_YET))
    return coverage


def cause_from_source_probe(candles_returned_by_source: int) -> GapCause:
    """Luật quy trách nhiệm, tách riêng để nơi nào chỉ cần KẾT LUẬN (vd E8
    `--probe-gap`) không phải dựng một `Coverage` giả chỉ để gọi hàm."""
    if candles_returned_by_source < 0:
        raise ValueError("số nến sàn trả về không thể âm")
    return GapCause.LOI_CUA_TA if candles_returned_by_source > 0 else GapCause.SAN_KHONG_CO


def attribute_from_source_probe(
    coverage: Coverage, *, gap: Gap, candles_returned_by_source: int
) -> Coverage:
    """Quy trách nhiệm bằng cách HỎI LẠI SÀN đúng cửa sổ bị trống.

    `candles_returned_by_source` là số nến sàn trả về cho đúng
    `[gap.start_ms, gap.end_ms]` khi gọi lại API — người gọi phải thực sự
    gọi (xem `entrypoints/backfill_data.py --probe-gap`), hàm này không
    tự suy ra được.

        > 0  ⇒ sàn CÓ dữ liệu mà ta thiếu ⇒ **lỗi của ta**
        = 0  ⇒ sàn thật sự không có

    Đây đúng là phép kiểm Tool A đã bỏ qua và mất nhiều ngày vì nó.
    """
    return replace(
        coverage, gap_cause=Measured.ok(cause_from_source_probe(candles_returned_by_source))
    )


def render_table(rows: list[Coverage], *, only_incomplete: bool = False) -> str:
    """Bảng độ phủ. Dòng tổng CỐ Ý không gộp nguyên nhân — gộp lại sẽ tạo
    ra đúng câu "phần lớn do sàn thiếu" mà H19 cấm."""
    shown = [c for c in rows if not (only_incomplete and c.is_full)]
    lines = [f"{'FILE':<46s} {'KHUNG':<4s} {'CÓ/CẦN':>17s}  GHI CHÚ", "-" * 100]
    lines += [c.render() for c in shown]
    lines.append("-" * 100)
    n_full = sum(1 for c in rows if c.is_full)
    n_gap = len(rows) - n_full
    unknown = sum(1 for c in rows if c.gaps and not c.gap_cause.is_ok())
    lines.append(
        f"Tổng {len(rows)} file: {n_full} đủ, {n_gap} thiếu. "
        f"{unknown} file có khoảng trống CHƯA kiểm nguồn — "
        "phải chạy `--probe-gap` trước khi kết luận bất cứ điều gì về nguyên nhân."
    )
    return "\n".join(lines)
