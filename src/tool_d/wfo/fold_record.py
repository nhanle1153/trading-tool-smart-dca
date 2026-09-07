"""TD-0146 — bản ghi kết quả của MỘT fold: đủ xuất xứ (`L-Z40`) và mọi
chỉ số đi qua ba trạng thái (`L-Z41`).

🔴 **Module này KHÔNG viết lại phép kiểm nào.** Hai máy canh đã tồn tại
từ D0-PRE: `validate_provenance()` (`measurement/provenance.py`) và kiểu
`Measured` (`measurement/tri_state.py`, cấm bịa `0.0` ở tầng KIỂU DỮ
LIỆU chứ không bằng quy ước gọi hàm). Việc ở đây là **NỐI** chúng vào
bản ghi fold.

════ Sàn số lệnh — thi hành điều DR-D3-01 §5.2 đã khai TRƯỚC ════

Fold có ít hơn `san_lenh_moi_fold` lệnh trong cửa sổ test thì MỌI chỉ số
của nó là `unreadable`, **không phải một con số**. Đây là chỗ luật đó
thành máy: với 19–47 lệnh/fold (DR-D3-01 §4), rất dễ có fold rơi xuống
dưới sàn, và một expectancy tính trên 12 lệnh trông y hệt một expectancy
tính trên 400 lệnh khi nó đã nằm trong bảng.

Quan trọng: `unreadable` ở đây KHÁC `pending`.
  • `pending`   = chưa chạy phép đo.
  • `unreadable` = ĐÃ chạy, nhưng mẫu quá mỏng để con số mang thông tin.
Gộp hai cái làm một sẽ mất đúng thông tin cần cho phán quyết cuối của
D3 ("orchestrator ĐÚNG, thống kê CHƯA ĐỌC ĐƯỢC" — DR-D3-01 §5.3).

════ Vì sao có `fold_record.schema.json` VÀ một test đối chiếu ĐẦU RA THẬT ════

Schema của project đặt `additionalProperties: false`. Một khoá mới thêm
vào code mà quên thêm vào schema sẽ **không** bị bắt bởi bộ test hiện
có, vì bộ đó chỉ đối chiếu FIXTURE GÕ TAY với schema — hai thứ do cùng
một người sửa cùng lúc, nên chúng luôn khớp nhau và cùng lệch khỏi code.
Nó chỉ nổ đúng lần ghi thật đầu tiên. (Phiên song song vừa dính đúng lỗi
này với `trial_event.schema.json`: **735 test xanh vẫn không bắt được.**)

Nên `tests/unit/test_fold_record.py` đối chiếu **đầu ra thật của
`build_fold_record()`** với schema, không đối chiếu fixture.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from tool_d.measurement.provenance import Provenance, validate_provenance
from tool_d.measurement.tri_state import Measured, Status
from tool_d.wfo.folds import Fold

if TYPE_CHECKING:  # chỉ để chú kiểu — tránh vòng import với orchestrator
    from tool_d.wfo.orchestrator import KetQuaFold


class FoldRecordError(RuntimeError):
    """Bản ghi fold không dựng được hoặc không hợp lệ cho gate."""


def _measured_to_dict(m: Measured[Any]) -> dict[str, Any]:
    """Ba trạng thái ra JSON. `value` chỉ có mặt khi `status == ok` — bất
    biến này do `Measured.__post_init__` bảo đảm, ở đây chỉ chép lại."""
    return {"status": m.status.value, "value": m.value, "note": m.note}


def build_fold_record(
    *,
    fold: Fold,
    provenance: Provenance,
    so_lenh: int,
    san_lenh_moi_fold: int,
    chi_so_do: Mapping[str, Measured[Any]],
    tu_cache: bool = False,
) -> dict[str, Any]:
    """Dựng bản ghi một fold.

    `chi_so_do`: tên chỉ số → `Measured`. Bên gọi truyền `Measured.ok(...)`
    cho thứ đã đo và `Measured.pending(...)` cho thứ chưa — KHÔNG truyền
    số trần, vì số trần không mang trạng thái và sẽ mở lại đúng cửa mà
    `L-Z41` đóng.

    🔴 Nếu `so_lenh < san_lenh_moi_fold`: mọi chỉ số bị **ép** thành
    `unreadable` kèm lý do, **kể cả những chỉ số bên gọi đã tính ra số**.
    Ép chứ không phải cảnh báo: một con số đã nằm trong bảng thì sẽ được
    đọc, bất kể chú thích bên cạnh nói gì.
    """
    if so_lenh < 0:
        raise FoldRecordError(f"so_lenh không thể âm, nhận: {so_lenh}")
    if san_lenh_moi_fold < 1:
        raise FoldRecordError(f"san_lenh_moi_fold phải >= 1, nhận: {san_lenh_moi_fold}")
    if not chi_so_do:
        raise FoldRecordError(
            "Bản ghi fold không có chỉ số nào — một bản ghi rỗng đi qua mọi phép "
            "kiểm mà không chứng minh điều gì (PASS RỖNG)."
        )

    du_lenh = so_lenh >= san_lenh_moi_fold
    ly_do_mong = (
        f"mẫu quá mỏng: {so_lenh} lệnh < sàn {san_lenh_moi_fold} đã khai trước "
        "ở DR-D3-01 §5.2"
    )
    chi_so = {
        ten: _measured_to_dict(m if du_lenh else Measured.unreadable(ly_do_mong))
        for ten, m in chi_so_do.items()
    }

    return {
        "loai": "FOLD_RESULT",
        "fold": {
            "chi_so": fold.chi_so,
            "train_start": fold.train_start.isoformat(),
            "train_end": fold.train_end.isoformat(),
            "test_start": fold.test_start.isoformat(),
            "test_end": fold.test_end.isoformat(),
        },
        "so_lenh": so_lenh,
        "san_lenh_moi_fold": san_lenh_moi_fold,
        "du_lenh": du_lenh,
        "tu_cache": tu_cache,
        "chi_so": chi_so,
        "provenance": provenance.to_dict(),
    }


def build_fold_record_tu_ket_qua(
    *,
    ket_qua: "KetQuaFold",
    provenance: Provenance,
    san_lenh_moi_fold: int,
    chi_so_do: Mapping[str, Measured[Any]] | None = None,
) -> dict[str, Any]:
    """Cầu nối DUY NHẤT từ `KetQuaFold` (kết quả trong bộ nhớ, TD-0145) sang
    bản ghi fold ghi ra đĩa.

    🔴 Vì sao cần hàm này chứ không để mỗi nơi tự dựng dict: `KetQuaFold`
    và bản ghi trên đĩa là HAI TẦNG khác nhau (một cái sống trong một lần
    chạy, một cái sống mãi và bị audit). Nhưng nếu không có đúng một đường
    nối giữa chúng thì chỗ nào cần ghi sẽ tự dựng lấy, và ta có hai bộ
    tuần tự hoá trôi lệch nhau — đúng lý do `decision_log.py` được đặt ở
    `ledger/` chứ không phải `wfo/`.

    `he_so` của `KetQuaFold` được đưa thẳng vào `chi_so` dưới tên
    `he_so_tang_truong`, không để bên gọi tự nhớ — quên nó là mất đúng
    con số chính của fold. Bên gọi truyền thêm chỉ số khác qua `chi_so_do`
    nhưng KHÔNG được đè tên đó (raise), vì đè lên sẽ thay con số đã qua
    `L-Z47` bằng một con số không rõ nguồn.

    `tu_cache` được ghi vào bản ghi: một fold LẤY LẠI TỪ CACHE là con số do
    một lần chạy TRƯỚC sinh ra. Vân tay cache đã bảo đảm nó khớp cấu
    hình/code/dữ liệu, nhưng người đọc bản ghi vẫn cần biết con số này
    được tính lại hay dùng lại — đó là câu hỏi xuất xứ, và §0d.5 tồn tại
    để trả lời đúng loại câu hỏi đó.
    """
    them = dict(chi_so_do or {})
    if "he_so_tang_truong" in them:
        raise FoldRecordError(
            "`chi_so_do` không được mang khoá `he_so_tang_truong` — nó đến từ "
            "`KetQuaFold.he_so` đã qua L-Z47; đè lên là thay số đã kiểm bằng "
            "số không rõ nguồn."
        )
    return build_fold_record(
        fold=ket_qua.fold,
        provenance=provenance,
        so_lenh=ket_qua.so_lenh,
        san_lenh_moi_fold=san_lenh_moi_fold,
        chi_so_do={"he_so_tang_truong": ket_qua.he_so, **them},
        tu_cache=ket_qua.tu_cache,
    )


def validate_fold_record(d: Mapping[str, Any]) -> list[str]:
    """Danh sách lỗi; rỗng = bản ghi HỢP LỆ CHO GATE.

    Gọi thẳng `validate_provenance()` cho khối xuất xứ — không chép lại
    luật của `L-Z40` vào đây. Ngoài ra kiểm hai bất biến riêng của bản ghi
    fold mà `L-Z41` không tự biết:
      • mọi chỉ số phải mang `status` thuộc ba trạng thái hợp lệ, và
        `value` chỉ được khác `None` khi `status == ok` (cấm bịa số);
      • `du_lenh` phải khớp với `so_lenh`/`san_lenh_moi_fold` — một bản
        ghi khai `du_lenh: true` trong khi mẫu mỏng là bản ghi tự cấp cho
        mình quyền hiển thị số.
    """
    loi: list[str] = []

    if "provenance" not in d:
        loi.append("thiếu khối provenance (L-Z40)")
    else:
        loi.extend(f"provenance: {e}" for e in validate_provenance(d["provenance"]))

    chi_so = d.get("chi_so")
    if not isinstance(chi_so, Mapping) or not chi_so:
        loi.append("thiếu `chi_so` hoặc không có chỉ số nào")
    else:
        hop_le = {s.value for s in Status}
        for ten, m in chi_so.items():
            if not isinstance(m, Mapping) or "status" not in m:
                loi.append(f"chỉ số {ten}: thiếu `status` (L-Z41)")
                continue
            if m["status"] not in hop_le:
                loi.append(f"chỉ số {ten}: status {m['status']!r} không thuộc {sorted(hop_le)}")
                continue
            if m["status"] != Status.OK.value and m.get("value") is not None:
                loi.append(
                    f"chỉ số {ten}: status={m['status']} nhưng vẫn mang value="
                    f"{m['value']!r} — cấm hiện số cũ kèm cảnh báo (§0d.6)"
                )
            if m["status"] == Status.OK.value and m.get("value") is None:
                loi.append(f"chỉ số {ten}: status=ok nhưng value=None")

    so_lenh, san = d.get("so_lenh"), d.get("san_lenh_moi_fold")
    if isinstance(so_lenh, int) and isinstance(san, int):
        if d.get("du_lenh") != (so_lenh >= san):
            loi.append(
                f"`du_lenh`={d.get('du_lenh')!r} không khớp so_lenh={so_lenh} "
                f"và sàn={san} — bản ghi tự cấp cho mình quyền hiển thị số."
            )
    else:
        loi.append("thiếu `so_lenh` hoặc `san_lenh_moi_fold`")

    return loi
