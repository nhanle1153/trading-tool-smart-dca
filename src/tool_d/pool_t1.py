"""TD-0247 (`DR-D1-02`) — hai bộ lọc ranh giới cho việc dựng lại rổ pool
point-in-time tại `T1`.

Logic THUẦN, không gọi mạng, không sửa `pool.py` (`DR-D1-02` §2.3 —
`pairlist_point_in_time()`/`pairlist_over_time()` giữ nguyên, đây là
module RIÊNG chạy TRƯỚC/SAU chúng, không thay thế).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence


def loai_tru_explore_hien_tai(
    ung_vien: Iterable[str], explore_hien_tai: Iterable[str]
) -> tuple[str, ...]:
    """`DR-D1-02` §2.3 — bất kỳ mã nào đang bị `compute_pool()` xếp vào
    khối `explore:` của `config/pool.yaml` HIỆN TẠI (tính bằng dữ liệu
    09/2026) đều bị loại VĨNH VIỄN khỏi rổ `T1`, dù nó đủ tiêu chí §0.3
    tại `T1`. Không có ngoại lệ (spec dòng 3831-3833, §9c.4b ràng buộc
    (b)) — kể cả khi phần "đã ở EXPLORE" là xếp loại MUỘN HƠN mốc `T1`
    ta đang dựng lại (chiều ngược của tình huống chữ spec hình dung,
    xem `DR-D1-02` §2.2).

    KHÔNG hardcode tên mã nào ở đây — `explore_hien_tai` phải luôn được
    đọc THẬT từ `config/pool.yaml` mỗi lần gọi, tránh mở một nguồn sự
    thật thứ hai (`MT-03`).
    """
    loai = frozenset(explore_hien_tai)
    return tuple(s for s in ung_vien if s not in loai)


def loai_tru_tradifi_perpetual(
    ung_vien: Iterable[str], exchange_info_symbols: Sequence[dict]
) -> tuple[str, ...]:
    """TD-0247 bẫy (iii) / `DR-D1-01` §1 — ứng viên liệt kê từ kho lưu
    trữ tĩnh (`data.binance.vision`) chỉ lọc được theo TÊN (hậu tố
    `USDT`), nên hút cả `TRADIFI_PERPETUAL` (cổ phiếu token hoá đang
    giao dịch, ví dụ `AAPLUSDT`, `ANTHROPICUSDT` — kết thúc bằng `USDT`,
    `status=TRADING`, nhưng `contractType` KHÁC `"PERPETUAL"`).

    Loại bất kỳ mã nào XUẤT HIỆN trong `exchangeInfo` hôm nay với
    `contractType` KHÁC `"PERPETUAL"` — đó là tín hiệu chắc chắn nó
    không phải perpetual crypto, bất kể đã "huỷ niêm yết" theo nghĩa
    nào khác. Mã VẮNG MẶT hoàn toàn khỏi `exchangeInfo` (đã thật sự
    biến mất khỏi sàn — đúng ý `DR-D1-01`) KHÔNG bị loại ở đây: kho lưu
    trữ là nguồn DUY NHẤT còn giữ dấu vết của những mã đó.
    """
    khong_phai_perp_con_niem_yet = {
        s["symbol"] for s in exchange_info_symbols if s.get("contractType") != "PERPETUAL"
    }
    return tuple(s for s in ung_vien if s not in khong_phai_perp_con_niem_yet)
