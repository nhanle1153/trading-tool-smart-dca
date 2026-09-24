"""TD-0244 — bộ sinh `gap_ms` (§8.3 LD-21, D2c), nguồn DUY NHẤT cho D2c.

════ Vì sao tồn tại ════
Trước module này, `gap_ms` chỉ có ĐÚNG một chỗ trong toàn repo:
`report_model.py:71`, và đó là NHÃN của chỉ số `SL_GAP_MS_DIST` — không có
bộ sinh nào đứng sau. Spec §8.3 (LD-21) đòi: *"MỖI LẦN KHỐI LƯỢNG SL ĐỔI =
MỘT BẢN GHI {ts, trade_id, tranche, sl_price, sl_qty_old, sl_qty_new,
sl_order_id_old, sl_order_id_new, gap_ms}"*.

════ Vì sao là hàm THUẦN, không đọc `trade.orders` trực tiếp ════
Freqtrade không cấp callback riêng cho "lệnh SL trên sàn vừa bị huỷ/vừa
được tạo lại" — cơ chế huỷ+đặt-lại (D2a, `docs/freqtrade-source-read.md`
mục 1) chạy NGẦM trong vòng lặp chính. Cách duy nhất quan sát được là đọc
lại lịch sử `trade.orders` (Freqtrade lưu MỌI Order, kể cả đã `canceled`,
không xoá) mỗi khi có cơ hội (`custom_stoploss`, gọi mỗi ~5s —
`PROCESS_THROTTLE_SECS`). Hàm ở đây tách phần suy luận thuần (đọc lịch sử
lệnh, sinh bản ghi) khỏi phần đọc Freqtrade thật, theo đúng khuôn mọi
module `tool_d.*` khác (DG1-DG5, entry_confirmation, …) — test được bằng
fixture, không cần dựng backtest.

════ Vì sao AN TOÀN gọi lại TOÀN BỘ lịch sử mỗi lần, không giữ trạng thái
tiến trình (né hình dạng lỗi MT-40/MT-41) ════
`self._cho`/`self._dinh_equity` (MT-41/MT-40) chỉ sống trong bộ nhớ tiến
trình Freqtrade → mất sạch khi restart, và phần mất đi không để lại dấu
vết nào để nghi ngờ. Hàm này KHÔNG giữ trạng thái nào giữa các lần gọi:
mỗi lần được gọi lại với TOÀN BỘ lịch sử lệnh của trade, sinh lại MỌI bản
ghi suy được, kể cả những bản ghi đã sinh ở lần gọi trước. Cửa ghi
(`ledger.decision_log.ghi_neu_chua_co`, LD-19) tự NO-OP theo
`dedup_key = sl_order_id_new` nếu khoá đã có trong sổ — nên gọi lại không
sinh trùng, và một lần restart giữa chừng không làm mất một `gap_ms` nào
(khác hẳn `self._cho`): lần gọi kế tiếp sau restart đọc lại đúng lịch sử
đó từ DB Freqtrade (bền, không phải bộ nhớ tiến trình) và ghi bù.

════ Vì sao KHÔNG suy đoán khi thiếu `order_update_date` (N6) ════
Nếu Freqtrade chưa kịp cập nhật mốc huỷ (hoặc dữ liệu không đọc được),
hàm BỎ QUA cặp đó thay vì bịa `gap_ms` — một mẫu thiếu tốt hơn một mẫu sai
lặng lẽ lẫn vào phân bố p99 mà `DR-D11-01`/`DR-D11-02` dùng để phán quyết
D2c.

════ Ranh giới với TD-0239 ════
Module này CHỈ sinh bản ghi loại `DOI_SL` (đổi khối lượng SL). Đường ghi
tổng quát của Decision Log (mọi tranche khớp, `hold_duration`, DG6/DG7
check, …) là phạm vi của `TD-0239` (🔓 lúc module này được viết) — không
lấn sang.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

LOAI_DOI_SL = "DOI_SL"


def _utc(moc: datetime) -> datetime:
    """Đưa MỌI mốc thời gian về UTC-aware (TD-0403).

    Freqtrade lưu ngày giờ của `Order` vào SQLite ở dạng UTC KHÔNG mang múi giờ, nên trong CÙNG một `trade.orders`
    lệnh nạp từ DB là *naive* còn lệnh vừa tạo trong bộ nhớ là *aware*. So hai loại đó (`sorted`, `<=`) ném
    `TypeError` — đo được trên dry-run D11 (07:01:38 và 07:55:53, 24/09/2026), cả hai ngay sau khi một lệnh SL
    mới được tạo. Naive được coi là UTC (đúng cách Freqtrade lưu), KHÔNG là giờ địa phương."""
    return moc.replace(tzinfo=timezone.utc) if moc.tzinfo is None else moc.astimezone(timezone.utc)


@dataclass(frozen=True)
class LenhSl:
    """Một dòng Order (`ft_order_side == "stoploss"`) đọc từ `trade.orders`.

    Chỉ mang đúng các trường cần cho phép suy luận — KHÔNG phụ thuộc kiểu
    `Order` thật của Freqtrade, để fixture test không cần dựng ORM.
    """

    order_id: str
    status: str  # "open" | "canceled" | "closed" | "triggered" | …
    amount: float
    order_date: datetime  # lúc lệnh này được TẠO trên sàn
    order_update_date: datetime | None  # lúc trạng thái đổi lần cuối


def sinh_ban_ghi_doi_sl(
    *,
    lenh_sl: list[LenhSl],
    moc_khop_entry: list[datetime],
    trade_id: int,
    sl_price: float,
    nguon: str,
) -> list[dict[str, Any]]:
    """Sinh bản ghi Decision Log `DOI_SL` cho MỌI lần khối lượng SL đổi
    suy được từ lịch sử `lenh_sl`.

    :param lenh_sl: TOÀN BỘ lệnh stoploss của trade (mọi trạng thái, mọi
        thời điểm) — không cần sắp xếp trước, hàm tự sắp theo `order_date`.
    :param moc_khop_entry: thời điểm KHỚP của mỗi lần entry/tranche đã
        đóng (dùng để suy `tranche` — không suy từ `trade.nr_of_successful_
        entries` vì con số đó là TẠI THỜI ĐIỂM GỌI, không phải tại thời
        điểm lệnh SL cũ tương ứng được tạo).
    :param sl_price: giá SL kế hoạch — D0.2: bất biến trong suốt trade,
        nên dùng chung cho mọi bản ghi sinh ra ở một lần gọi (L-Z2: phải
        khớp giá trong sổ với giá kế hoạch — kiểm ở nơi gọi/nơi đọc sổ).
    :param nguon: `"backtest" | "dry_run" | "live"` — dùng thẳng
        `self.dp.runmode.value` phía chiến lược, KHÔNG suy đoán ở đây
        (TD-0201, `NGUON_HOP_LE`).

    Lệnh SL ĐẦU TIÊN của trade (đặt lúc tranche 1 khớp) không sinh bản
    ghi — nó không phải một lần ĐỔI, là lần ĐẶT đầu.
    """
    # TD-0403: chuẩn hoá TRƯỚC mọi phép so/trừ, nhưng bản ghi vẫn mang `order_date` GỐC (`ts` giữ đúng dạng đầu vào —
    # dedup theo `sl_order_id_new` chứ không theo `ts`, nên không đổi định dạng sổ hay khẳng định cũ).
    theo_thu_tu = sorted(((_utc(o.order_date), o) for o in lenh_sl), key=lambda t: t[0])
    moc_sap = sorted(_utc(m) for m in moc_khop_entry)

    ban_ghi: list[dict[str, Any]] = []
    for (_, cu), (moi_utc, moi) in zip(theo_thu_tu, theo_thu_tu[1:]):
        if cu.status != "canceled":
            # Không phải một cặp huỷ→tạo-lại (vd. hai lệnh SL mở đồng thời
            # do một lỗi lạ nào đó) — không suy đoán, bỏ qua (N6).
            continue
        if cu.order_update_date is None:
            continue
        gap_ms = (moi_utc - _utc(cu.order_update_date)).total_seconds() * 1000.0
        tranche = sum(1 for m in moc_sap if m <= moi_utc)
        ban_ghi.append(
            {
                "loai": LOAI_DOI_SL,
                "nguon": nguon,
                "ts": moi.order_date.isoformat(),
                "trade_id": trade_id,
                "tranche": tranche,
                "sl_price": sl_price,
                "sl_qty_old": cu.amount,
                "sl_qty_new": moi.amount,
                "sl_order_id_old": cu.order_id,
                "sl_order_id_new": moi.order_id,
                "gap_ms": gap_ms,
            }
        )
    return ban_ghi
