"""TD-0240 — đọc DB Freqtrade thật qua chính ORM của Freqtrade (`init_db()`
+ `Trade.get_trades()`), không tự viết SQL/SQLAlchemy song song.

════ Vì sao dùng ORM của Freqtrade, không tự đọc file SQLite ════
Cùng lý do `TD-0245` đã chọn: đọc bằng `init_db()` là đúng đường mà CHÍNH
Freqtrade dùng khi khởi động bot, nên mọi phép tính (`close_profit_abs`,
`entry_side`, …) đi qua đúng định nghĩa của nó — không tạo ra một cách
hiểu dữ liệu THỨ HAI (LD-09). Tự viết SQL riêng để đọc `trades`/`orders`
sẽ phải TỰ DIỄN GIẢI LẠI ý nghĩa cột (đúng loại rủi ro Quy tắc 7 cảnh báo
— ví dụ `close_profit_abs` là bẫy đã ghi trong từ điển: chỉ là TỔNG khi
trade đã đóng hẳn).

════ BẮT BUỘC nhận `db_url` làm tham số, KHÔNG có mặc định ngầm ════
🔴 Bài học trả giá ở `TD-0239` cùng ngày: `DEFAULT_DECISION_LOG_PATH` là
một hằng số module-level trỏ vào đường dẫn cố định của repo, và một test
gọi lại đường chạy sản xuất với `cwd` sai đã ghi thẳng vào sổ THẬT. Hàm
ở đây không lặp lại lỗi đó — không có `DEFAULT_DB_URL` nào trong module
này. `entrypoints/periodic_report.py` (nơi ĐÚNG để có mặc định trỏ vào
DB thật của dự án) tự đọc `db_url` từ `config/freqtrade/config.json` rồi
truyền vào; test luôn phải tự tạo một DB tạm và truyền `db_url` của nó.

════ Vì sao trả `LenhTomTat` (dataclass thuần), không trả `Trade` thẳng ════
Cùng khuôn `gap_ms.LenhSl`: tách phần ĐỌC (I/O, phụ thuộc Freqtrade ORM)
khỏi phần TÍNH (thuần, test bằng dữ liệu dựng tay không cần DB thật).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class LenhTomTat:
    """Một dòng `trades`, RÚT GỌN đúng những trường TD-0240 cần — không
    phơi toàn bộ `Trade` ORM ra ngoài module này."""

    is_open: bool
    is_short: bool
    exit_reason: str | None
    close_profit_abs: float | None  # CHỈ đọc khi is_open=False (bẫy đã tra: TỔNG chỉ đúng khi đóng hẳn)
    open_date_utc: datetime
    close_date_utc: datetime | None
    so_tranche_khop: int  # đếm order entry_side đã status=="closed"


class FreqtradeDbError(RuntimeError):
    """Không đọc được DB — fail-closed, KHÔNG trả danh sách rỗng lặng lẽ
    (rỗng-vì-lỗi khác hẳn rỗng-vì-chưa-có-lệnh, N6)."""


def doc_danh_sach_lenh(db_url: str) -> list[LenhTomTat]:
    """Đọc TOÀN BỘ `trades` qua `Trade.get_trades()` của chính Freqtrade.

    :param db_url: chuỗi kết nối SQLAlchemy đầy đủ (vd
        ``sqlite:////duong/tuyet/doi/tradesv3_dryrun.sqlite``). KHÔNG có
        giá trị mặc định — xem docstring module.
    :raises FreqtradeDbError: import/kết nối thất bại. Một DB CHƯA TỪNG
        CHẠY (chưa có bảng nào) vẫn trả `[]` — đó là "chưa có lệnh nào",
        không phải lỗi đọc (N6: hai trạng thái khác nhau).
    """
    try:
        from freqtrade.persistence import Trade, init_db
    except ImportError as exc:  # pragma: no cover - chỉ xảy ra ngoài Docker
        raise FreqtradeDbError(
            f"không import được freqtrade.persistence: {exc}. "
            "Module này chỉ chạy đúng trong container đã cài Freqtrade (N7)."
        ) from exc

    try:
        init_db(db_url)
        ket_qua = [_rut_gon(t) for t in Trade.get_trades().all()]
    except Exception as exc:  # noqa: BLE001 - fail-closed, bọc lại thành lỗi có tên
        raise FreqtradeDbError(f"đọc DB {db_url!r} thất bại: {exc}") from exc
    return ket_qua


def _rut_gon(trade) -> LenhTomTat:
    so_tranche = sum(
        1
        for o in trade.orders
        if o.ft_order_side == trade.entry_side and o.status == "closed"
    )
    return LenhTomTat(
        is_open=bool(trade.is_open),
        is_short=bool(trade.is_short),
        exit_reason=trade.exit_reason,
        close_profit_abs=(None if trade.is_open else trade.close_profit_abs),
        open_date_utc=trade.open_date_utc,
        close_date_utc=trade.close_date_utc,
        so_tranche_khop=so_tranche,
    )


def doc_db_url_tu_config(config_path: Path) -> str:
    """Đọc `db_url` từ chính `config/freqtrade/config.json` — KHÔNG khai
    lại đường dẫn DB ở một nơi thứ hai (LD-09). Fail-closed nếu thiếu."""
    import json

    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    db_url = cfg.get("db_url")
    if not db_url:
        raise FreqtradeDbError(f"{config_path} thiếu khoá 'db_url'")
    return db_url
