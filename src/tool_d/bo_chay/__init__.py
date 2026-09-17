"""`TD-0312` (`DR-BC-01`) — lõi bộ chạy backtest thật, dùng chung cho E1/E2/E3.

🔑 **Điều quan trọng nhất của gói này không phải nó chạy được Freqtrade, mà là nó
làm cho MỘT SAI LẦM trở nên KHÔNG BIỂU DIỄN ĐƯỢC.** `YeuCauChay` chỉ mang `tap:
str`; nó không có trường nào nhận đường dẫn file rổ hay thư mục dữ liệu. Muốn biết
chạy trên mã nào, lõi **bắt buộc** phải gọi `ro_cho_tap()` (`DR-D1-05` §1). Không
có đường nào khác để truyền một danh sách mã vào — kể cả nhầm.

Vì sao điều đó đáng giá: rổ chọn tại mốc muộn hơn đã loại sẵn những mã suy giảm/chết
trong giai đoạn ⇒ lệch sống sót **theo chiều PASS**, và `verify_seal()` không xét
danh sách pool nên **không lớp canh nào báo đỏ** (`MT-60` ghi đúng hình dạng này).

🔴 **Gói này KHÔNG tự đặt chỗ trial.** Nó đòi một `GiayPhepChay` đã có và tự đọc lại
sổ để kiểm — không nhận lời khai. Lý do không tự đặt chỗ là lý do `orchestrator.py`
đã ghi và `DR-BC-01` §2 giữ nguyên: *nó không biết `budget_line` nào, và đoán hộ là
cách chắc chắn tiêu sai ngân sách.*
"""

from tool_d.bo_chay.chay import ChuaDatChoError, chay_mot_luot
from tool_d.bo_chay.doc_ket_qua import DocKetQuaError, doc_ket_qua
from tool_d.bo_chay.moi_truong import MoiTruongChay, MoiTruongError, dung_moi_truong
from tool_d.bo_chay.yeu_cau import (
    BoChayError,
    GiayPhepChay,
    KetQuaChay,
    YeuCauChay,
    chuoi_timerange,
    ten_cap_freqtrade,
)

__all__ = [
    "BoChayError",
    "ChuaDatChoError",
    "DocKetQuaError",
    "GiayPhepChay",
    "KetQuaChay",
    "MoiTruongChay",
    "MoiTruongError",
    "YeuCauChay",
    "chay_mot_luot",
    "chuoi_timerange",
    "doc_ket_qua",
    "dung_moi_truong",
    "ten_cap_freqtrade",
]
