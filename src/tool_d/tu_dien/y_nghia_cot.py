"""TD-0245 — ý nghĩa CÓ BẰNG CHỨNG của từng cột, và đăng ký chỗ Tool D đọc.

🔴 **Ba trạng thái, cấm bịa** (chủ dự án chốt 14/09/2026, đúng tinh thần N6).
Quy tắc 7 nói thẳng: *"không suy đoán ý nghĩa từ tên trường hay từ code cũ"*.
Vậy nên một cột chỉ được mang ý nghĩa khi ý nghĩa đó **đọc ra từ mã nguồn
Freqtrade** và có `file:line` đi kèm. Cột chưa tra thì bộ sinh ghi
`⏳ chưa tra cứu` — **không** để trống mập mờ, **không** đoán từ tên.

Điền nghĩa cho cả 109 cột "cho đủ" là đúng thứ Quy tắc 7 cấm, và nguy hơn
không có từ điển: một dòng bịa **trông y hệt** một dòng đã tra.

════ Bằng chứng lấy từ đâu ════

Mọi số dòng dưới đây đọc trong **ảnh Docker của project**, không phải trên
host (Freqtrade không cài trên host — N7):

    Freqtrade 2026.8 · source commit 9f10e357a93c1dcf10c2a2b367659214d89c073e
    image sha256:7031bca43ed7668ebf421725dd5016acade6ef88b0771db3e08c96e6d19a42db

⚠️ **Image đổi thì phải ĐỌC LẠI, không dùng số cũ** (cùng cảnh báo
`docs/freqtrade-source-read.md:26`). Số dòng là ảnh chụp, không phải hằng số.

════ Hai cái bẫy đắt nhất, đã đọc mã để xác nhận ════

1. 🔴 **`trades.close_profit_abs` KHÔNG phải "lãi đã thực hiện" khi trade còn
   mở.** `trade_model.py:1318-1321` — sau một lần thoát TỪNG PHẦN mà vị thế
   vẫn còn:

       self.realized_profit  = close_profit_abs   # CỘNG DỒN mọi lần thoát
       self.close_profit_abs = prof.profit_abs    # CHỈ lần thoát CUỐI CÙNG

   Chỉ khi đóng HẲN (`:1342-1344`) `close_profit_abs` mới là TỔNG.

   Với Tool D đây không phải chuyện lý thuyết: TP1 chốt 50% qua
   `adjust_trade_position` ⇒ có `PARTIAL_EXIT` ⇒ trade **còn mở** với một lần
   thoát đã xảy ra. Hôm nay TP1 chỉ nổ **một lần** nên hai trường **bằng
   nhau**, tức một phép kiểm viết hôm nay sẽ **XANH** rồi sai im lặng ngày có
   lần thoát thứ hai. Đúng hình dạng *"fixture đúng hệ thống CŨ, im lặng sai
   với hệ thống MỚI"* mà dự án đã dính ba lần.

   ⇒ Muốn "lãi đã thực hiện" thì đọc `realized_profit`. Muốn "tổng lãi kể cả
   phần chưa thực hiện" thì `trade_model.py:1187`:
   `total_profit_abs = profit_abs + self.realized_profit`.

2. 🔴 **Quy ước DẤU của `funding_fees`.** `trade_model.py:1130-1131`:
   *"Positive funding_fees -> Trade has gained from fees. Negative -> Trade had
   to pay"*. Và funding **đã nằm trong** `close_profit_abs` rồi
   (`:1128-1135`, nhánh FUTURES: long cộng, short trừ). Ai trừ funding thêm
   một lần nữa là **tính hai lần và sai dấu**. (Canh bởi `L-Z43`.)

Hai điều trên cộng lại là câu trả lời cho DR-013 *"pnl_abs đã trừ phí +
funding"*: `calculate_profit()` docstring `:1160` — *"All calculations include
fees."*
"""

from __future__ import annotations

from dataclasses import dataclass

NGUON_BANG_CHUNG = (
    "Freqtrade 2026.8, source commit 9f10e357a93c1dcf10c2a2b367659214d89c073e, "
    "image sha256:7031bca43ed7668ebf421725dd5016acade6ef88b0771db3e08c96e6d19a42db"
)

# Thư mục mã nguồn Freqtrade trong ảnh — tiền tố của mọi bằng chứng dưới đây.
GOC_MA_NGUON = "/freqtrade/freqtrade/persistence/"


@dataclass(frozen=True)
class NghiaCot:
    """Ý nghĩa một cột, kèm bằng chứng đọc được.

    `bang_chung` KHÔNG có giá trị mặc định: một mục không trích được nguồn thì
    không được phép tồn tại ở đây — nó thuộc về trạng thái `⏳ chưa tra cứu`,
    và bộ sinh tự lo phần đó.
    """

    y_nghia: str
    bang_chung: str
    gia_tri_hop_le: str = "—"


def _tm(dong: str) -> str:
    return f"{GOC_MA_NGUON}trade_model.py:{dong}"


def _wh(dong: str) -> str:
    return f"{GOC_MA_NGUON}wallet_history.py:{dong}"


def _cd(dong: str) -> str:
    return f"{GOC_MA_NGUON}custom_data.py:{dong}"


# (bảng, cột) -> nghĩa. CHỈ những cột đã thực sự đọc mã nguồn.
Y_NGHIA: dict[tuple[str, str], NghiaCot] = {
    # ───────────────────────── trades ─────────────────────────
    ("trades", "id"): NghiaCot(
        "Khoá chính của một lệnh (trade). Mọi tranche DCA của cùng một lệnh "
        "dùng CHUNG id này — nên đếm theo `id` là đếm LỆNH, không phải đếm lần vào",
        _tm("1717"),
    ),
    ("trades", "exchange"): NghiaCot("Tên sàn thực hiện lệnh", _tm("1731")),
    ("trades", "pair"): NghiaCot(
        "Cặp giao dịch, dạng `BASE/QUOTE` (có hậu tố `:QUOTE` ở futures)", _tm("1732")
    ),
    ("trades", "is_open"): NghiaCot(
        "Lệnh còn mở hay đã đóng hẳn. Mẫu số của mọi tỉ lệ trên 'lệnh đã đóng' "
        "phải lọc `is_open = 0`",
        _tm("1735"),
        "0 hoặc 1",
    ),
    ("trades", "fee_open"): NghiaCot(
        "TỈ LỆ phí của lệnh vào (không phải số tiền). Số tiền là `fee_open_cost`",
        _tm("1736"),
    ),
    ("trades", "fee_close"): NghiaCot(
        "TỈ LỆ phí của lệnh ra. Số tiền là `fee_close_cost`", _tm("1741")
    ),
    ("trades", "open_rate"): NghiaCot(
        "Giá vào TRUNG BÌNH hiện tại của lệnh. Với DCA, giá trị này ĐỔI sau mỗi "
        "tranche khớp (tính lại ở `recalc_trade_from_orders`) — không phải giá "
        "của tranche 1",
        _tm("1745"),
    ),
    ("trades", "realized_profit"): NghiaCot(
        "Lãi/lỗ tuyệt đối ĐÃ THỰC HIỆN, CỘNG DỒN qua mọi lần thoát từng phần. "
        "Đây mới là 'đã thực hiện' — KHÔNG phải `close_profit_abs`",
        _tm("1751 · 1320"),
    ),
    ("trades", "close_profit"): NghiaCot(
        "Lãi/lỗ theo TỈ LỆ. 🔴 DR-013 CẤM dùng tỉ lệ cho mọi chỉ số tổng hợp "
        "(mẫu số riêng từng lệnh; với DCA còn đổi giữa chừng) — dùng `pnl_abs`",
        _tm("1752"),
    ),
    ("trades", "close_profit_abs"): NghiaCot(
        "🔴 BẪY: khi trade CÒN MỞ sau một lần thoát từng phần, đây CHỈ là lãi của "
        "lần thoát CUỐI CÙNG, không phải tổng. Chỉ khi đóng hẳn nó mới là TỔNG. "
        "Đã bao gồm phí VÀ funding. Deprecated ở tầng RPC (bí danh `profit_abs`)",
        _tm("1753 · 1318-1321 · 1342-1344 · 1160 · 747"),
    ),
    ("trades", "stake_amount"): NghiaCot(
        "Ký quỹ đã bỏ ra, TỔNG hiện tại của mọi tranche đã khớp (đã chia đòn bẩy). "
        "Với DCA giá trị này LỚN DẦN — không phải cỡ lệnh lúc mở",
        _tm("1754"),
    ),
    ("trades", "max_stake_amount"): NghiaCot(
        "Ký quỹ lớn nhất lệnh từng chiếm, cộng dồn theo từng lần vào", _tm("1755")
    ),
    ("trades", "amount"): NghiaCot(
        "Khối lượng vị thế hiện tại theo đơn vị tài sản cơ sở (đã trừ phần đã thoát)",
        _tm("1756"),
    ),
    ("trades", "open_date"): NghiaCot(
        "Thời điểm mở lệnh (tranche 1). ⚠️ Lưu KHÔNG kèm múi giờ; Freqtrade coi là "
        "UTC và phơi bản có múi giờ qua thuộc tính `open_date_utc`",
        _tm("1758"),
    ),
    ("trades", "close_date"): NghiaCot(
        "Thời điểm đóng hẳn lệnh; `NULL` khi lệnh còn mở. Cùng quy ước múi giờ với "
        "`open_date`",
        _tm("1759"),
    ),
    ("trades", "exit_reason"): NghiaCot(
        "Lý do thoát. Với Tool D đây là chuỗi do `custom_exit()` trả về "
        "(ví dụ `TIME_STOP`), hoặc tên cơ chế của Freqtrade",
        _tm("1773"),
    ),
    ("trades", "enter_tag"): NghiaCot(
        "Nhãn vào lệnh do chiến lược gán. Tool D nhét kế hoạch tranche đã mã hoá "
        "vào đây và giải mã lại khi khởi động lại",
        _tm("1776"),
    ),
    ("trades", "leverage"): NghiaCot(
        "Đòn bẩy của lệnh. `stake_amount × leverage = giá trị vị thế`", _tm("1787")
    ),
    ("trades", "is_short"): NghiaCot(
        "Hướng lệnh. 🔴 Quy ước DẤU của funding đảo theo cột này", _tm("1788"), "0 hoặc 1"
    ),
    ("trades", "funding_fees"): NghiaCot(
        "Funding tích luỹ đã CHỐT. 🔴 DƯƠNG = lệnh ĐƯỢC NHẬN, ÂM = phải TRẢ. "
        "Đã được cộng/trừ vào `close_profit_abs` rồi — trừ lần nữa là tính hai lần",
        _tm("1795 · 1128-1135"),
    ),
    ("trades", "funding_fee_running"): NghiaCot(
        "Funding đang chạy của phần vị thế CHƯA đóng — tách khỏi `funding_fees` để "
        "phần đã chốt không đổi khi giá funding kỳ sau thay đổi",
        _tm("1796"),
    ),
    # ───────────────────────── orders ─────────────────────────
    ("orders", "id"): NghiaCot("Khoá chính của một lệnh đặt lên sàn", _tm("85")),
    ("orders", "ft_trade_id"): NghiaCot(
        "Khoá ngoại trỏ `trades.id`. Một trade có NHIỀU order (mỗi tranche một order, "
        "cộng các lệnh SL và lệnh thoát)",
        _tm("86"),
    ),
    ("orders", "ft_order_side"): NghiaCot(
        "Vai trò của order trong lệnh. 🔴 `stoploss` là giá trị RIÊNG, không phải "
        "`buy`/`sell` — đây là cách duy nhất lọc ra lịch sử SL",
        _tm("91-92"),
        "buy · sell · stoploss",
    ),
    ("orders", "ft_amount"): NghiaCot(
        "Khối lượng Freqtrade YÊU CẦU (khác `amount` do sàn báo về)", _tm("95")
    ),
    ("orders", "order_id"): NghiaCot(
        "Mã order do SÀN cấp. Tool D dùng làm khoá chống trùng của Decision Log "
        "(§8.3) — mỗi tranche một sự kiện",
        _tm("99"),
    ),
    ("orders", "status"): NghiaCot(
        "Trạng thái order theo CCXT. `canceled` là mốc suy ra khoảng trống không-SL "
        "(`gap_ms`)",
        _tm("100"),
        "open · closed · canceled · expired · rejected",
    ),
    ("orders", "amount"): NghiaCot(
        "Khối lượng order theo SÀN báo về. Khối lượng ĐÃ khớp là `filled`", _tm("106")
    ),
    ("orders", "order_date"): NghiaCot(
        "Thời điểm order được TẠO. Mốc kết thúc khoảng trống không-SL", _tm("111")
    ),
    ("orders", "order_filled_date"): NghiaCot(
        "Thời điểm order KHỚP; `NULL` nếu chưa khớp. Đây là mốc khớp thật, khác "
        "`order_date`",
        _tm("112"),
    ),
    ("orders", "order_update_date"): NghiaCot(
        "Lần cuối trạng thái order đổi. Với order SL đã huỷ, đây là mốc BẮT ĐẦU "
        "khoảng trống không-SL",
        _tm("113"),
    ),
    # ────────────────────── wallet_history ──────────────────────
    # 🔴 Bảng này là ứng viên trực tiếp cho TD-0238 (đỉnh equity bền vững qua
    #    restart) — Freqtrade tự ghi, sống qua restart. Nhưng xem `timestamp`:
    #    độ phân giải NGÀY, nên đỉnh trong ngày KHÔNG tái lập được từ đây.
    ("wallet_history", "id"): NghiaCot("Khoá chính", _wh("18")),
    ("wallet_history", "timestamp"): NghiaCot(
        "Mốc bản ghi. 🔴 Độ phân giải NGÀY — ràng buộc duy nhất `(timestamp, currency)` "
        "khoá ĐÚNG MỘT bản ghi mỗi đồng mỗi ngày, nên đỉnh equity TRONG NGÀY không "
        "suy được từ bảng này",
        _wh("19 · 40-43"),
    ),
    ("wallet_history", "currency"): NghiaCot("Đồng của dòng ví này", _wh("20")),
    ("wallet_history", "rate"): NghiaCot(
        "Giá 1 đơn vị `currency` quy theo `quote_currency`", _wh("21-23")
    ),
    ("wallet_history", "quote_currency"): NghiaCot(
        "Đồng định giá cho `rate` và các cột `total_*`", _wh("24-25")
    ),
    ("wallet_history", "balance"): NghiaCot(
        "Số dư theo đơn vị `currency` (chưa quy đổi)", _wh("27-28")
    ),
    ("wallet_history", "total_quote"): NghiaCot(
        "Tổng giá trị ví quy theo `quote_currency` — đại lượng 'equity' chuẩn tắc. "
        "Với futures tính bằng `collateral` + PnL",
        _wh("30-32"),
    ),
    ("wallet_history", "total_position_value"): NghiaCot(
        "Tổng giá trị vị thế, ĐÃ nhân đòn bẩy", _wh("33-34")
    ),
    ("wallet_history", "collateral"): NghiaCot("Ký quỹ đang giữ", _wh("35")),
    ("wallet_history", "leverage"): NghiaCot("Đòn bẩy tại thời điểm chụp", _wh("36")),
    ("wallet_history", "bot_managed"): NghiaCot(
        "Phần ví do bot này quản lý hay không — lọc cột này để không tính nhầm tiền "
        "của người/bot khác trên cùng tài khoản",
        _wh("38"),
        "0 hoặc 1",
    ),
    # ───────────────────── trade_custom_data ─────────────────────
    # Nơi Tool D cất dữ liệu RIÊNG của mình (kế hoạch tranche, chốt lời...).
    # ⚠️ Ý nghĩa BÊN TRONG `cd_value` là của Tool D, KHÔNG thuộc phạm vi đợt này.
    ("trade_custom_data", "id"): NghiaCot("Khoá chính", _cd("36")),
    ("trade_custom_data", "ft_trade_id"): NghiaCot(
        "Khoá ngoại trỏ `trades.id`. Ràng buộc duy nhất `(ft_trade_id, cd_key)` ⇒ "
        "mỗi lệnh mỗi khoá đúng một bản ghi",
        _cd("34 · 37"),
    ),
    ("trade_custom_data", "cd_key"): NghiaCot(
        "Tên khoá do chiến lược đặt (Tool D dùng `co_lenh`, `ke_hoach`, `tag`, "
        "`zone_dinh`, `chot_loi`)",
        _cd("41"),
    ),
    ("trade_custom_data", "cd_type"): NghiaCot(
        "Tên kiểu Python của giá trị, dùng để dựng lại khi đọc ra", _cd("42")
    ),
    ("trade_custom_data", "cd_value"): NghiaCot(
        "Giá trị đã tuần tự hoá thành văn bản. 🔴 Hình dạng BÊN TRONG là của Tool D "
        "và CHƯA có schema nào mô tả — ngoài phạm vi TD-0245",
        _cd("43"),
    ),
    ("trade_custom_data", "created_at"): NghiaCot("Lúc bản ghi được tạo", _cd("44")),
    ("trade_custom_data", "updated_at"): NghiaCot(
        "Lúc sửa lần cuối; `NULL` nếu chưa sửa lần nào", _cd("45")
    ),
}


# ════════════════════════════════════════════════════════════════════
# Đăng ký chỗ Tool D ĐỌC cột database — phần "máy thi hành" của Quy tắc 7.
# ════════════════════════════════════════════════════════════════════

# Cột Tool D đọc nhưng phép quét AST KHÔNG thấy được, vì tên quá chung để
# khớp theo thuộc tính mà không nhầm (xem `quet_cot.la_ten_dac_trung`).
# Khai tay ở đây, mỗi mục đã đối chiếu mã thật.
#
# 🔴 Mọi mục trong đăng ký này bị test khoá ép hai điều: cột phải TỒN TẠI
#    trong schema đo được (bắt tên bịa/tên đã đổi), và phải có nghĩa trong
#    `Y_NGHIA` (bắt việc đọc một trường chưa ai tra).
TOOL_D_DOC_THEM: dict[tuple[str, str], tuple[str, ...]] = {
    ("trades", "id"): ("user_data/strategies/ZoneAbsorption.py",),
    ("trades", "is_open"): ("user_data/strategies/ZoneAbsorption.py",),
    ("trades", "leverage"): ("user_data/strategies/ZoneAbsorption.py",),
    ("orders", "status"): (
        "src/tool_d/gap_ms.py",
        "user_data/strategies/ZoneAbsorption.py",
    ),
    ("orders", "amount"): (
        "src/tool_d/gap_ms.py",
        "user_data/strategies/ZoneAbsorption.py",
    ),
}


# Chỗ phép quét khớp trúng tên cột nhưng KHÔNG phải đọc database.
# Khoá theo (cột, đường dẫn) — cố ý KHÔNG kèm tên hàm hay số dòng, để một lần
# đổi tên hàm ở file khác không làm lớp canh này đỏ oan.
#
# 🔴 Danh sách này là CỬA HẸP, không phải cửa thoát: mọi chỗ khớp mà không nằm
#    trong đây và cũng không nằm trong đăng ký đọc đều làm test ĐỎ. Tức thêm
#    một chỗ đọc DB mới thì buộc phải khai — đúng thứ Quy tắc 7 đòi.
KHONG_PHAI_DOC_DB: dict[tuple[str, str], str] = {
    ("stake_currency", "src/tool_d/equity_peak.py"): (
        "thuộc tính của dataclass `DinhEquityBenVung` do Tool D tự định nghĩa "
        "(TD-0238), trùng tên với cột `trades.stake_currency` chứ không đọc DB"
    ),
    ("stake_currency", "user_data/strategies/ZoneAbsorption.py"): (
        "đọc `da_luu.stake_currency` của chính dataclass trên; đơn vị tiền của "
        "cấu hình lấy từ `self.config[\"stake_currency\"]`, là truy cập từ điển "
        "chứ không phải cột DB"
    ),
}
