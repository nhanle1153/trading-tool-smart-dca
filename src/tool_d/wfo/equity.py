"""TD-0142 — cân đối vốn từng fold (`L-Z47`) và ghép fold thành đường
vốn liên tục bằng **NHÂN**, không cộng (DR-013, spec dòng 2708-2710).

Module này tồn tại để bịt **hai bug có thật của Tool A** mà spec dòng
4340 bắt H3-D phải có test chống lại trước khi được coi là xong:

  (5) cộng dồn **tỉ lệ lợi nhuận tương đối** (tên trường Freqtrade bị
      DR-013 cấm ở tầng đo — cố ý KHÔNG gõ thẳng tên ở đây, xem ghi chú
      cuối docstring) qua fold — canh bởi `L-Z46`, vốn grep toàn bộ
      `src/` + `entrypoints/` nên module này tự động nằm trong phạm vi
      quét, không phải khai báo thêm;
  (6) **ghép fold bằng CỘNG thay vì NHÂN** — canh ở đây.

🔴 **Vì sao NHÂN chứ không CỘNG.** Mỗi fold là một backtest ĐỘC LẬP, tự
reset vốn về `starting_balance` (DR-013). Lãi của fold 1 KHÔNG được đưa
vào vốn khởi điểm của fold 2 — bộ chạy không làm thế. Nên đại lượng duy
nhất so sánh được giữa các fold là **hệ số tăng trưởng** `final /
starting`, và đường vốn liên tục là tích các hệ số đó. Cộng `pnl_abs`
thẳng qua các fold là cộng những con số tính trên các mẫu số khác nhau
— cùng đúng một loại sai lầm đã cho Tool A ra `−1464%`.

Sai lệch còn tinh vi hơn: CỘNG và NHÂN cho kết quả gần nhau khi lãi/lỗ
mỗi fold nhỏ, nên bug này KHÔNG lộ ra trên dữ liệu hiền — nó chỉ lộ khi
có một fold biến động mạnh, tức đúng lúc con số quan trọng nhất.

📌 Ghi chú về cách diễn đạt ở mục (5): `L-Z46` grep cả docstring (nó
KHÔNG có bước bỏ chú thích như `L-Z25`), nên ngay cả câu văn giải thích
rằng ta đang chặn trường đó cũng bị tính là vi phạm. Bản đầu của file
này gõ thẳng tên trường và làm `L-Z46` đỏ. Cách xử là **diễn đạt lại,
KHÔNG nới phép kiểm** — phép kiểm đang làm đúng việc của nó; thứ cần
sửa là câu chữ của mình. (Cùng cách xử phiên song song đã dùng khi
`L-Z25` bắt tên công cụ tối ưu bị cấm trong chuỗi thông báo của
`param_proposals.py`.)
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

# L-Z47 (spec dòng 2798): sai số cho phép giữa `starting + Σ pnl_abs` và
# `final_balance`. 0,01 USDT = một xu — đủ chỗ cho làm tròn dấu phẩy
# động tích luỹ qua vài trăm lệnh, KHÔNG đủ chỗ cho một lệnh bị bỏ sót.
DUNG_SAI_CAN_DOI_USDT = 0.01


class CanDoiFoldError(RuntimeError):
    """Cân đối vốn của một fold không khớp (`L-Z47`), hoặc dữ liệu fold
    không dùng được để ghép đường vốn. Fail-closed: raise, KHÔNG trả về
    một con số đã biết là sai."""


@dataclass(frozen=True)
class FoldEquity:
    """Kết quả vốn của MỘT fold, đọc từ đầu ra backtest của fold đó.

    `pnl_abs` là danh sách lãi/lỗ TỪNG LỆNH tính bằng USDT đã trừ phí và
    funding (DR-013 §1) — giữ cả danh sách chứ không chỉ tổng, vì `L-Z47`
    là phép đối chiếu giữa tổng-các-lệnh và số dư cuối do bộ chạy báo:
    truyền sẵn tổng vào thì hai vế cùng một nguồn và phép kiểm mất nghĩa
    (cùng bẫy `DatasetBoundary` đã cảnh báo ở `ledger/timerange.py`).
    """

    chi_so: int  # 1-based, khớp `Fold.chi_so`
    starting_balance: float
    final_balance: float
    pnl_abs: tuple[float, ...]

    @property
    def tong_pnl_abs(self) -> float:
        return sum(self.pnl_abs)

    @property
    def he_so(self) -> float:
        """Hệ số tăng trưởng của fold = `final / starting`. Đây là đại
        lượng DUY NHẤT so sánh được giữa các fold khi mỗi fold tự reset
        vốn."""
        return self.final_balance / self.starting_balance


def kiem_can_doi_fold(fold: FoldEquity) -> None:
    """🔴 `L-Z47` — `starting_balance + Σ pnl_abs == final_balance`, sai
    số < 0,01 USDT.

    Đây không phải phép kiểm hình thức: nó bắt được lệnh bị bỏ sót khỏi
    danh sách, phí/funding tính thiếu, và mọi trường hợp bộ chạy báo số
    dư không giải thích được bằng chính các lệnh nó liệt kê.
    """
    if fold.starting_balance <= 0:
        raise CanDoiFoldError(
            f"Fold {fold.chi_so}: starting_balance = {fold.starting_balance} "
            "— phải > 0 (không có hệ số tăng trưởng nào định nghĩa được từ vốn 0 hoặc âm)."
        )
    lech = abs(fold.starting_balance + fold.tong_pnl_abs - fold.final_balance)
    if lech >= DUNG_SAI_CAN_DOI_USDT:
        raise CanDoiFoldError(
            f"Fold {fold.chi_so} KHÔNG cân đối (L-Z47): "
            f"starting {fold.starting_balance} + Σ pnl_abs {fold.tong_pnl_abs} "
            f"= {fold.starting_balance + fold.tong_pnl_abs}, nhưng final_balance "
            f"= {fold.final_balance}. Lệch {lech} USDT >= dung sai "
            f"{DUNG_SAI_CAN_DOI_USDT}. Số dư không giải thích được bằng chính "
            "các lệnh đã liệt kê — điều tra trước, KHÔNG dùng con số này."
        )


def ghep_duong_von(folds: Sequence[FoldEquity], *, von_ban_dau: float) -> tuple[float, ...]:
    """Ghép các fold thành đường vốn liên tục bằng **NHÂN hệ số**.

    Trả về `(von_ban_dau, sau_fold_1, sau_fold_2, …)` — tức `len(folds)+1`
    điểm, điểm đầu là vốn khởi điểm. Trả cả điểm đầu thay vì chỉ các điểm
    sau để bên vẽ/tính drawdown không phải tự chèn lại nó (và tự chèn sai).

    Mỗi fold được `kiem_can_doi_fold()` TRƯỚC khi hệ số của nó được dùng —
    ghép một fold chưa cân đối là nhân một con số đã biết là sai vào toàn
    bộ phần đuôi của đường vốn.

    TỪ CHỐI (fail-closed, không tự sửa):
      • danh sách rỗng;
      • `chi_so` không phải đúng dãy `1..k` — thứ tự sai thì tích vẫn ra
        một con số trông hợp lý nhưng đường vốn ở giữa là bịa. Không tự
        sắp xếp lại: dữ liệu vào sai thứ tự là dấu hiệu bên gọi hiểu sai,
        sắp hộ chỉ giấu lỗi đó đi;
      • `final_balance <= 0` (tài khoản cháy). Hệ số <= 0 nhân vào sẽ
        làm đổi dấu mọi điểm phía sau và cho ra đường vốn vô nghĩa. Đây
        là sự kiện phải nhìn tận mắt, không phải thứ để nhân tiếp.
    """
    if not folds:
        raise CanDoiFoldError("Không có fold nào để ghép đường vốn.")
    if von_ban_dau <= 0:
        raise CanDoiFoldError(f"von_ban_dau phải > 0, nhận: {von_ban_dau}")

    chi_so = [f.chi_so for f in folds]
    if chi_so != list(range(1, len(folds) + 1)):
        raise CanDoiFoldError(
            f"chi_so của các fold phải là dãy liên tiếp 1..{len(folds)} theo đúng "
            f"thứ tự thời gian, nhận: {chi_so}. TỪ CHỐI — không tự sắp xếp lại."
        )

    duong_von = [von_ban_dau]
    for f in folds:
        kiem_can_doi_fold(f)
        if f.final_balance <= 0:
            raise CanDoiFoldError(
                f"Fold {f.chi_so} có final_balance = {f.final_balance} <= 0 "
                "(tài khoản cháy). TỪ CHỐI ghép tiếp — hệ số <= 0 nhân vào sẽ "
                "làm đổi dấu toàn bộ phần đuôi đường vốn."
            )
        duong_von.append(duong_von[-1] * f.he_so)
    return tuple(duong_von)


def he_so_tong(folds: Sequence[FoldEquity]) -> float:
    """Hệ số tăng trưởng gộp của cả chuỗi fold = tích các hệ số.

    Bằng `ghep_duong_von(...)[-1] / von_ban_dau` theo định nghĩa; giữ hàm
    riêng để chỗ dùng chỉ cần một con số không phải tự chia lại (và tự
    chia nhầm bằng phép cộng).
    """
    return ghep_duong_von(folds, von_ban_dau=1.0)[-1]
