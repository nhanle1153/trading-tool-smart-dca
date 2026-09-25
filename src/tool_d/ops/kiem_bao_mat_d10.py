"""TD-0384 (`DR-D10-02` Q3) — máy kiểm bảo mật TÀI KHOẢN PHỤ trước MỖI lần bật bộ chạy D10 (tiền thật).

Chủ dự án chốt 24/09/2026: checklist tay (IP whitelist bật, quyền rút / chuyển tiền tắt — `DR-D11-01` §3) có thể bị
mở lại mà không ai hay; máy phải tự đọc cờ quyền của CHÍNH API key rồi TỪ CHỐI bật nếu một cờ sai. Bảng quyết định là
bản gốc ở `api-integration-rules.md` 4.4c (N1: không chép luật sang chỗ khác — file này thi hành, không định nghĩa lại).

Hai phần, cùng khuôn toàn dự án (hàm THUẦN trước, lời gọi mạng sau):
- `danh_gia_quyen_key(du_lieu)` — thuần, nhận JSON trả về, trả DANH SÁCH lý do từ chối (rỗng = được bật).
- `kiem_truoc_khi_bat(...)` — gọi `get_api_restrictions()` rồi phán quyết; MỌI lỗi đọc (mạng, HTTP, -2014/-2015,
  -1021, breaker mở) ⇒ từ chối. Fail-closed: không đọc được cấu hình key thì coi như KHÔNG an toàn.

🔴 N6 — không đoán mặc định cho một cờ bảo mật: thiếu trường, hoặc trường không phải `bool` thật (chuỗi `"false"`,
`0`, `None`), đều là lý do từ chối. Một chuỗi `"false"` đọc thành "đúng" theo kiểu Python là đúng thứ lỗi im lặng
mà một cổng an toàn không được phép có.

⚠️ Tên trường theo tài liệu Binance, CHƯA verify bằng gọi thật — việc đầu tiên khi có key tài khoản phụ là gọi thật
MỘT lần và đối chiếu (`api-integration-rules.md` 1.6).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from tool_d.api_client.binance_public import get_api_restrictions

#: Bảng 4.4c: trường → giá trị BẮT BUỘC để được bật D10, kèm lý do in ra khi lệch.
DIEU_KIEN_BAT: tuple[tuple[str, bool, str], ...] = (
    ("ipRestrict", True, "IP whitelist đang TẮT — lộ key là mất quyền điều khiển từ bất kỳ đâu"),
    ("enableWithdrawals", False, "quyền RÚT tiền đang BẬT — key D10 chỉ cần giao dịch futures"),
    ("enableInternalTransfer", False, "quyền chuyển tiền NỘI BỘ đang BẬT"),
    ("permitsUniversalTransfer", False, "Universal Transfer đang BẬT (DR-D11-01 §3 đòi tắt)"),
    ("enableFutures", True, "key KHÔNG có quyền futures — bộ chạy sẽ không đặt được lệnh"),
)


class BaoMatD10Error(RuntimeError):
    """TỪ CHỐI bật D10 — cấu hình bảo mật tài khoản phụ không đạt, hoặc không đọc được (fail-closed)."""


@dataclass(frozen=True)
class KetQuaKiemBaoMat:
    ly_do_tu_choi: tuple[str, ...]

    @property
    def duoc_bat(self) -> bool:
        return not self.ly_do_tu_choi


def danh_gia_quyen_key(du_lieu: Any) -> KetQuaKiemBaoMat:
    """Phán quyết thuần trên JSON của `apiRestrictions`. Gom HẾT lý do (không dừng ở lý do đầu) để người vận hành sửa
    một lần thay vì chạy đi chạy lại."""
    if not isinstance(du_lieu, Mapping):
        return KetQuaKiemBaoMat((f"dữ liệu trả về không phải object JSON (nhận {type(du_lieu).__name__})",))
    ly_do: list[str] = []
    for truong, can, giai_thich in DIEU_KIEN_BAT:
        if truong not in du_lieu:
            ly_do.append(f"thiếu trường `{truong}` — không đoán mặc định cho cờ bảo mật (N6)")
            continue
        gia_tri = du_lieu[truong]
        if not isinstance(gia_tri, bool):
            ly_do.append(f"`{truong}` = {gia_tri!r} không phải bool — không đoán (N6)")
            continue
        if gia_tri is not can:
            ly_do.append(f"`{truong}` = {gia_tri}: {giai_thich}")
    return KetQuaKiemBaoMat(tuple(ly_do))


def kiem_truoc_khi_bat(
    *,
    api_key: str,
    api_secret: str,
    goi_fn: Callable[..., Any] = get_api_restrictions,
) -> KetQuaKiemBaoMat:
    """Đọc cờ quyền rồi phán quyết. Không đạt ⇒ `BaoMatD10Error` (liệt kê mọi lý do). Đạt ⇒ trả kết quả.

    Mọi `Exception` khi đọc đều đổi thành `BaoMatD10Error`: gồm cả -2015 (IP không trong whitelist). Gọi từ IP ngoài
    whitelist bị từ chối nghĩa là whitelist ĐANG hoạt động, nhưng bộ chạy vẫn phải dừng vì không kiểm được các cờ còn
    lại — và vì chính lệnh đặt lệnh sau đó cũng sẽ bị từ chối như vậy (`api-integration-rules.md` 4.3)."""
    try:
        du_lieu = goi_fn(api_key=api_key, api_secret=api_secret)
    except Exception as exc:  # noqa: BLE001 — cố ý bắt rộng: KHÔNG đọc được thì KHÔNG bật (fail-closed)
        raise BaoMatD10Error(
            f"TỪ CHỐI bật D10 — không đọc được cờ quyền của API key ({type(exc).__name__}: {exc}). "
            "Kiểm: key/secret tài khoản phụ, IP máy này có trong whitelist, đồng hồ máy (lỗi -1021)."
        ) from exc
    ket_qua = danh_gia_quyen_key(du_lieu)
    if not ket_qua.duoc_bat:
        raise BaoMatD10Error(
            "TỪ CHỐI bật D10 — cấu hình bảo mật tài khoản phụ không đạt (DR-D10-02 Q3):\n  - "
            + "\n  - ".join(ket_qua.ly_do_tu_choi)
        )
    return ket_qua
