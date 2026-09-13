"""TD-0236 / `DR-D4-11` — tiêu chí đóng cổng D4, bằng HIỆN VẬT không bằng số trial.

`back-end-note.md:80` (`OQ-11` PA3, 07/09/2026) định nghĩa cổng là *"đếm được
**đúng 18** trial `B2` CONSUMED"*. `MT-38` ghi nhận nó va với `DR-D4-01:15`
(cấp **9**, Long-only). Nhưng con số chỉ là lớp nông nhất — lý do thật để
viết module này nằm ở `DR-D4-10:211-213`, thứ đã hạ **7/9 suất xuống thống kê
MÔ TẢ**:

    Nếu cổng đếm N dòng `B2` CONSUMED, nó sẽ PASS KỂ CẢ KHI toàn bộ N suất
    đó đều là loại MÔ TẢ và `Z0-T1` — cấu hình DUY NHẤT D4 còn phán quyết
    được — chưa từng chạy.

Tức một cổng XANH trong khi thứ duy nhất nó tồn tại để chứng nhận đã KHÔNG
xảy ra. Không ca đỏ nào, không triệu chứng nào. Đây là PASS RỖNG nằm sẵn
trong **định nghĩa** cổng, không phải trong một phép kiểm — nên hạ khoá 18
xuống 9 không sửa được nó.

════ Nguyên tắc: bỏ HẰNG SỐ, giữ QUAN HỆ ════

Module này KHÔNG chứa số `18`, cũng không chứa số `9`. Cả hai là hằng số sẽ
lỗi thời — `18` đã lỗi thời sau 24 giờ. Điều kiện kế toán ở đây là một
**quan hệ**: *"số trial `B2` đã tiêu khớp số arm đã chạy"*, đúng ở mọi phạm
vi D4 tương lai (Long-only, cả hai hướng, hay một phạm vi chưa nghĩ ra).

Bài học `TD-0171` áp nguyên — tách ghim QUAN HỆ khỏi ghim QUYẾT ĐỊNH: quan
hệ nằm ở `_kiem_ke_toan()`; **quyết định** (phạm vi Long-only của đợt này)
nằm ở `d4_huong`, đúng MỘT chỗ, và chỗ đó buộc người sửa phải viết ra một
chữ có nghĩa thay vì đổi một hằng số vô danh.

════ Dùng lại máy đã có, không khai lại luật ════

`validate_arm_record()` đã thi hành: cờ `pham_vi_phan_quyet` gán theo bảng
`DR-D4-10` §2.1 (`arm_record.py:242-252`), cấm arm `mo_ta` mang `PASS`
(`:283-288`), và bắt khai `delta_r_pham_vi` + `so_ma_da_chay` (`:216-241`,
`TD-0234`/`MT-37`). Module này **gọi** nó chứ không chép luật sang — hai
danh sách song song sớm muộn trôi lệch (bài học cổng D3.5: *"điều kiện đóng
cổng"* và *"điều kiện được chạy ablation"* cố ý là MỘT hàm).

🔴 PHẠM VI: module này chỉ trả lời *"đã đủ điều kiện đóng cổng chưa"*. Nó
KHÔNG ghi khoá — `close_d4_gate()` là việc của `TD-0186`, và hàm đó phải
GỌI hàm này chứ không khai lại tiêu chí.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from tool_d.gates.arm_record import ARM_MUA_PHAN_QUYET, validate_arm_record
from tool_d.gates.ket_cuc import KetCuc

#: Hướng hợp lệ cho `d4_huong`. `DR-D4-01:15` chốt đợt này chạy **Long
#: trước**; khoá phải khai tường minh để *"đã đóng cho Long"* không bao giờ
#: bị đọc thành *"đã đóng cho cả hai hướng"* (`TASKS.md` TD-0186).
HUONG_HOP_LE: frozenset[str] = frozenset({"LONG", "SHORT"})

#: `d4_han_che` phải NHẮC TỚI câu DCA — `DR-D4-10` §8 chặng (d)(g).
#: ⚠️ Đây cố ý chỉ là phép kiểm SỰ CÓ MẶT, không phải kiểm nội dung: một lời
#: khai của người không máy nào xác minh được, và §0d.6 tách *"đã audit"*
#: khỏi *"đã đạt"* đúng vì lý do đó. Giá trị của nó là làm việc BỎ SÓT trở
#: nên bất khả, không phải làm việc khai gian trở nên bất khả.
_TU_KHOA_HAN_CHE: str = "DCA"

_KET_CUC_HOP_LE: frozenset[str] = frozenset(k.value for k in KetCuc)


class D4GateError(ValueError):
    """Đầu vào không đủ để phán xét. Fail-closed: raise, KHÔNG trả "chưa đủ
    điều kiện" — *"dữ liệu hỏng"* khác hẳn *"cổng chưa đóng được"*, và gộp
    hai thứ là cách một lỗi lắp ráp biến thành một kết luận về tiến độ."""


def _gia_tri_measured(m: Any) -> Any:
    """Lấy `value` của một khối `Measured` đã qua `validate_arm_record()`."""
    if isinstance(m, Mapping):
        return m.get("value")
    return None


def _kiem_arm_phan_quyet(ban_ghi: Sequence[Mapping[str, Any]]) -> list[str]:
    """Điều kiện 1 — mọi arm thuộc `ARM_MUA_PHAN_QUYET` phải có bản ghi hợp
    lệ, mang `pham_vi_phan_quyet='phan_quyet'` và một `ket_cuc` thật."""
    loi: list[str] = []
    theo_arm = {d.get("arm"): d for d in ban_ghi if isinstance(d, Mapping)}
    for arm in sorted(ARM_MUA_PHAN_QUYET):
        d = theo_arm.get(arm)
        if d is None:
            loi.append(
                f"thiếu bản ghi arm {arm!r} — đây là cấu hình DUY NHẤT D4 còn "
                "phán quyết được (DR-D4-10 §2.1). Cổng KHÔNG được đóng khi nó "
                "chưa chạy, dù mọi arm mô tả đã đủ"
            )
            continue
        if d.get("pham_vi_phan_quyet") != "phan_quyet":
            loi.append(
                f"arm {arm!r} mang pham_vi_phan_quyet="
                f"{d.get('pham_vi_phan_quyet')!r}, phải là 'phan_quyet'"
            )
        kc = _gia_tri_measured(d.get("ket_cuc"))
        if kc not in _KET_CUC_HOP_LE:
            loi.append(
                f"arm {arm!r} không mang kết cục đọc được: {kc!r} — phải thuộc "
                f"{sorted(_KET_CUC_HOP_LE)} (DR-D4-09 §2.2: BA kết cục, và "
                "'chưa đo được' là INCONCLUSIVE chứ không phải để trống)"
            )
    return loi


def _kiem_ke_toan(ban_ghi: Sequence[Mapping[str, Any]], so_b2_consumed: int) -> list[str]:
    """Điều kiện 6 — QUAN HỆ, không hằng số: số trial `B2` đã tiêu phải khớp
    số arm đã chạy. Cố ý không so với `18` hay `9`."""
    if so_b2_consumed != len(ban_ghi):
        return [
            f"kế toán lệch: sổ có {so_b2_consumed} dòng B2 CONSUMED nhưng có "
            f"{len(ban_ghi)} bản ghi arm. Cổng so QUAN HỆ này, KHÔNG so với một "
            "hằng số — xem DR-D4-11 §3"
        ]
    return []


def kiem_tieu_chi_dong_d4(
    *,
    ban_ghi_arm: Sequence[Mapping[str, Any]],
    so_dong_b2_consumed: int,
    d4_huong: str | None,
    d4_han_che: str | None,
) -> list[str]:
    """Trả về danh sách LÝ DO TỪ CHỐI đóng cổng D4. Rỗng = đủ điều kiện.

    Trả *lý do đọc được* chứ không trả `bool` — cùng lý do
    `kiem_san_tool_d()` của `DR-D4-05` làm thế: một cổng từ chối mà không
    nói vì sao sẽ bị gỡ chứ không được sửa.

    :param ban_ghi_arm: các bản ghi kết quả arm của D4 (mỗi phần tử đã hoặc
        sẽ đi qua ``validate_arm_record``).
    :param so_dong_b2_consumed: số sự kiện CONSUME mang ``budget_line='B2'``
        đếm được trong ``registry/trial_registry.jsonl``.
    :param d4_huong: hướng D4 đã chạy, phải khai tường minh.
    :param d4_han_che: lời khai hạn chế, phải nhắc tới câu DCA.
    :raises D4GateError: đầu vào sai KIỂU (khác với "chưa đủ điều kiện").
    """
    if not isinstance(ban_ghi_arm, Sequence) or isinstance(ban_ghi_arm, (str, bytes)):
        raise D4GateError(f"ban_ghi_arm phải là một dãy bản ghi, nhận {type(ban_ghi_arm)!r}")
    if not isinstance(so_dong_b2_consumed, int) or isinstance(so_dong_b2_consumed, bool):
        raise D4GateError(f"so_dong_b2_consumed phải là số nguyên, nhận {so_dong_b2_consumed!r}")
    if so_dong_b2_consumed < 0:
        raise D4GateError(f"so_dong_b2_consumed âm: {so_dong_b2_consumed}")

    loi: list[str] = []

    # Điều kiện 2 + 3 — giao TRỌN cho validate_arm_record(), không khai lại
    # luật: nó đã cấm `mo_ta` + PASS (arm_record.py:283-288) và đã bắt khai
    # `delta_r_pham_vi`/`so_ma_da_chay` (:216-241).
    for i, d in enumerate(ban_ghi_arm):
        if not isinstance(d, Mapping):
            raise D4GateError(f"bản ghi arm thứ {i} không phải mapping: {type(d)!r}")
        for msg in validate_arm_record(d):
            loi.append(f"bản ghi arm {d.get('arm', f'#{i}')!r}: {msg}")

    loi += _kiem_arm_phan_quyet(ban_ghi_arm)

    # Điều kiện 4 — hướng khai tường minh.
    if d4_huong not in HUONG_HOP_LE:
        loi.append(
            f"d4_huong {d4_huong!r} không thuộc {sorted(HUONG_HOP_LE)} — phải khai "
            "tường minh để 'đã đóng cho Long' không bị đọc thành 'đã đóng cho cả "
            "hai hướng' (DR-D4-01:113)"
        )

    # Điều kiện 5 — lời khai hạn chế phải nhắc câu DCA.
    if not isinstance(d4_han_che, str) or not d4_han_che.strip():
        loi.append(
            "thiếu d4_han_che — DR-D4-10 §8 chặng (d)(g) đòi khai rõ D4 KHÔNG "
            "phán quyết câu DCA"
        )
    elif _TU_KHOA_HAN_CHE not in d4_han_che:
        loi.append(
            f"d4_han_che không nhắc tới {_TU_KHOA_HAN_CHE!r} — DR-D4-10 §2.4 chốt "
            "câu DCA đi Idea Queue, và cổng phải khai điều đó chứ không im lặng"
        )

    loi += _kiem_ke_toan(ban_ghi_arm, so_dong_b2_consumed)
    return loi
