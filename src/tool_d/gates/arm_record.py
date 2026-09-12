"""TD-0232 — bản ghi kết quả MỘT ARM của ablation D0.9: thi hành `MT-36`.

🔴 **Vì sao module này tồn tại TRƯỚC bộ chạy `TD-0184`.** `n = 206` mà
`DR-D4-10` §2.1 dẫn được tính trên **toàn** cửa sổ `[T1,T2]` (231 ngày), trong
khi ba cửa sổ **test** của sơ đồ fold (`DR-D3-01`, `folds.py:174-185`) chỉ phủ
**147/231 ngày** — đoạn 84 ngày đầu là train-only ở **cả ba** fold. Hai cách
đọc cho `n` = 206 vs ~131, tức thuế nhiễu `h/√n` lệch **25%**. Mà `dsr.py:52`
nhận `n_trades: int` **không có ngữ nghĩa cửa sổ nào**, và `chay_wfo`/
`sinh_folds` **không có người gọi nào** từ `run_ablation.py`. ⇒ Bộ chạy sẽ
quyết câu đó **bằng cách vô tình** nếu không có chỗ nào bắt nó khai.

`MT-36` (chủ dự án chốt 13/09/2026): Nhánh 1 phán quyết trên `n_phan_quyet`
(chỉ đoạn TEST); `n_mo_ta` (toàn cửa sổ) báo kèm, dán nhãn **MÔ TẢ**.

🔑 **Vì sao SCHEMA + hai bất biến, chứ không phải một phép kiểm lúc audit.**
`TD-0127` đã dạy: *một phép kiểm có thể bị bỏ qua, một tham số không tồn tại
thì không ai truyền vào được*. `arm_result.schema.json` đặt **cả hai** trường
là `required` ⇒ một bản ghi chỉ mang một con số `n` là **không biểu diễn
được**, không phải *bị báo đỏ sau*.

Ba bất biến JSON Schema **không** so được (nó không so hai trường với nhau),
nên chúng sống ở đây:

1. `n_phan_quyet <= n_mo_ta` — đoạn test là **tập con** của toàn cửa sổ. Vi
   phạm nghĩa là hai con số đến từ hai phép đếm khác nhau, và khi đó **cả hai**
   đều không đọc được.
2. `pham_vi_phan_quyet` phải khớp **bảng đã chốt** ở `DR-D4-10` §2.1/§2.3 —
   không để bộ đọc tự suy từ `n` (§8 chặng a nói thẳng thế). `Z0-T1` là cấu
   hình ứng viên **DUY NHẤT**; `Z0-T0` là arm **chẩn đoán**; bảy arm nhóm C mua
   **thống kê mô tả**. Một arm nhóm C khai `phan_quyet` là đúng thứ §2.2 sinh
   ra để chặn: *"nếu nhóm C ra bất cứ kết cục nào KHÁC INCONCLUSIVE ⇒ nghi ngờ
   BỘ ĐO trước, không mừng"*.
3. `ket_cuc` có giá trị thì giá trị phải thuộc `KetCuc` — và một arm `mo_ta`
   **không được** mang kết cục `PASS`: suất đó không mua một phán quyết.

🔴 **Module này KHÔNG viết lại phép kiểm nào.** `validate_provenance_tool_d()`
(8 khoá, TD-0229) và kiểu `Measured` (cấm bịa `0.0` ở tầng KIỂU DỮ LIỆU) đã
tồn tại; việc ở đây là **NỐI** chúng vào bản ghi arm — cùng khuôn
`wfo/fold_record.py`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

from tool_d.arm_switches import ARM_HOP_LE
from tool_d.gates.ket_cuc import KetCuc
from tool_d.measurement.provenance import Provenance, validate_provenance_tool_d
from tool_d.measurement.tri_state import Measured, Status

#: `DR-D4-10` §2.1/§2.3 — arm nào mua một PHÁN QUYẾT Nhánh 1. Đúng MỘT phần
#: tử: `Z0-T1` là *"cấu hình ứng viên DUY NHẤT vượt sàn 150 lệnh/năm"*
#: (`DR-D4-10:174`), sau khi `MT-26` (C) hạ `Z0-T0` xuống arm chẩn đoán.
#:
#: 🔴 Đây là một tập CHO PHÉP, không phải một danh sách cấm — thêm một arm vào
#: đây là một QUYẾT ĐỊNH (phải có DR), không phải một lần gõ thêm. Bài học
#: `TD-0130`: blocklist chỉ chặn được tên đã nghĩ ra trước.
ARM_MUA_PHAN_QUYET: frozenset[str] = frozenset({"Z0-T1"})

#: Bảy arm nhóm C — `DR-D4-10` §2.2 khai chúng là INCONCLUSIVE **ngay tại DR**,
#: kèm phép tính §1.2. Suất của chúng mua **thống kê mô tả**.
ARM_NHOM_C: frozenset[str] = frozenset(ARM_HOP_LE) - {"Z0-T1", "Z0-T0"}

PHAM_VI_HOP_LE: frozenset[str] = frozenset({"phan_quyet", "mo_ta"})

#: `DR-D4-09` §2.3: *"Báo cáo BẮT BUỘC cho MỌI arm — ba con số, không phải
#: một … Thiếu một ⇒ bản ghi kết quả không hợp lệ."* `n` đã là hai trường
#: riêng; đây là phần còn lại, cộng `mean_r`/`std_r` (thuế nhiễu và `DSR_adj`
#: không đọc được mà không có chúng) và `ty_le_rui_ro_da_trien_khai` (ràng buộc
#: `MT-25`: đo `std_R` một mình là mua một con số không biết đọc theo chiều nào).
CHI_SO_BAT_BUOC: frozenset[str] = frozenset(
    {"mean_r", "std_r", "thue_nhieu", "dsr_adj", "ty_le_rui_ro_da_trien_khai"}
)


class ArmRecordError(RuntimeError):
    """Bản ghi arm không dựng được hoặc không hợp lệ cho gate."""


def pham_vi_theo_arm(arm: str) -> str:
    """Cờ `pham_vi_phan_quyet` mà `DR-D4-10` §2.1 đã gán cho arm này.

    🔴 Hàm này là nguồn duy nhất của phép gán đó. `DR-D4-10` §8 chặng (a) viết
    rõ: cờ gán theo §2.1, **không** để bộ đọc tự suy từ `n` — vì suy từ `n`
    nghĩa là một arm bỗng "được phán quyết" chỉ vì nó tình cờ có nhiều lệnh.
    """
    if arm not in ARM_HOP_LE:
        raise ArmRecordError(
            f"arm {arm!r} không thuộc chín cấu hình B2 {ARM_HOP_LE}. "
            "Lưu ý `Z0-T2` KHÔNG phải arm — nó CHÍNH LÀ `Z0` (§10.1b)."
        )
    return "phan_quyet" if arm in ARM_MUA_PHAN_QUYET else "mo_ta"


def _kiem_measured(ten: str, m: Any, loi: list[str]) -> Any:
    """Trả `value` nếu đọc được, `None` nếu không. Ghi lỗi vào `loi`."""
    if not isinstance(m, Mapping) or "status" not in m:
        loi.append(f"chỉ số {ten}: thiếu `status` (L-Z41)")
        return None
    hop_le = {s.value for s in Status}
    if m["status"] not in hop_le:
        loi.append(f"chỉ số {ten}: status {m['status']!r} không thuộc {sorted(hop_le)}")
        return None
    if m["status"] != Status.OK.value and m.get("value") is not None:
        loi.append(
            f"chỉ số {ten}: status={m['status']} nhưng value={m.get('value')!r} — "
            "cấm hiện số cũ kèm cảnh báo (N6)"
        )
        return None
    if m["status"] == Status.OK.value and m.get("value") is None:
        loi.append(f"chỉ số {ten}: status=ok nhưng value=None")
        return None
    return m.get("value")


def validate_arm_record(d: Mapping[str, Any]) -> list[str]:
    """Danh sách lỗi; rỗng = bản ghi **HỢP LỆ CHO GATE**.

    Kiểm ba bất biến ở docstring module, cộng khối xuất xứ (gọi thẳng
    `validate_provenance_tool_d()` — không chép luật `L-Z40`/`MT-07` vào đây).

    ⚠️ Hàm này **không** thay `arm_result.schema.json`: schema canh *hình
    dạng* (khoá bắt buộc, enum, `additionalProperties: false`), hàm này canh
    *quan hệ giữa các trường* — thứ JSON Schema không so được.
    """
    loi: list[str] = []

    arm = d.get("arm")
    if arm not in ARM_HOP_LE:
        loi.append(f"arm {arm!r} không thuộc {ARM_HOP_LE}")

    # ── Bất biến 1: đoạn test là TẬP CON của toàn cửa sổ ────────────────
    n_pq, n_mt = d.get("n_phan_quyet"), d.get("n_mo_ta")
    if not isinstance(n_pq, int) or isinstance(n_pq, bool):
        loi.append(f"thiếu hoặc sai kiểu `n_phan_quyet`: {n_pq!r} (MT-36)")
    if not isinstance(n_mt, int) or isinstance(n_mt, bool):
        loi.append(f"thiếu hoặc sai kiểu `n_mo_ta`: {n_mt!r} (MT-36)")
    if isinstance(n_pq, int) and isinstance(n_mt, int) and n_pq > n_mt:
        loi.append(
            f"n_phan_quyet ({n_pq}) > n_mo_ta ({n_mt}) — đoạn test là TẬP CON của "
            "toàn cửa sổ, nên vi phạm này nghĩa là hai con số đến từ hai phép "
            "đếm khác nhau và KHI ĐÓ CẢ HAI đều không đọc được (MT-36)"
        )

    cs_pq = d.get("cua_so_phan_quyet")
    if not isinstance(cs_pq, list) or not cs_pq:
        loi.append(
            "thiếu `cua_so_phan_quyet` — `n_phan_quyet` không có nguồn thì nó chỉ "
            "là một con số được khai, không phải một con số được đếm"
        )

    # ── Bất biến 2: cờ phạm vi phải khớp bảng DR-D4-10 §2.1 ─────────────
    pv = d.get("pham_vi_phan_quyet")
    if pv not in PHAM_VI_HOP_LE:
        loi.append(f"pham_vi_phan_quyet {pv!r} không thuộc {sorted(PHAM_VI_HOP_LE)}")
    elif arm in ARM_HOP_LE:
        mong_doi = pham_vi_theo_arm(arm)
        if pv != mong_doi:
            loi.append(
                f"arm {arm!r} phải mang pham_vi_phan_quyet={mong_doi!r}, bản ghi "
                f"khai {pv!r} — DR-D4-10 §8 chặng (a): cờ gán theo §2.1, KHÔNG để "
                "bộ đọc tự suy từ `n`"
                + (
                    ". Arm nhóm C khai `phan_quyet` là đúng thứ §2.2 sinh ra để "
                    "chặn: nhóm C đã được khai INCONCLUSIVE NGAY TẠI DR"
                    if arm in ARM_NHOM_C
                    else ""
                )
            )

    # ── Chỉ số bắt buộc (DR-D4-09 §2.3) ─────────────────────────────────
    chi_so = d.get("chi_so")
    if not isinstance(chi_so, Mapping):
        loi.append("thiếu `chi_so` (DR-D4-09 §2.3)")
    else:
        for ten in sorted(CHI_SO_BAT_BUOC - set(chi_so)):
            loi.append(
                f"thiếu chỉ số bắt buộc `{ten}` — DR-D4-09 §2.3: thiếu một ⇒ bản "
                "ghi kết quả KHÔNG HỢP LỆ"
            )
        for ten, m in chi_so.items():
            _kiem_measured(ten, m, loi)

    # ── Bất biến 3: kết cục ─────────────────────────────────────────────
    kc = d.get("ket_cuc")
    gia_tri = _kiem_measured("ket_cuc", kc, loi) if kc is not None else None
    if kc is None:
        loi.append("thiếu `ket_cuc` (DR-D4-09 §2.2 — BA kết cục, không phải hai)")
    elif gia_tri is not None:
        hop_le = {k.value for k in KetCuc}
        if gia_tri not in hop_le:
            loi.append(f"ket_cuc {gia_tri!r} không thuộc {sorted(hop_le)}")
        elif gia_tri == KetCuc.PASS.value and pv == "mo_ta":
            loi.append(
                f"arm {arm!r} mang pham_vi_phan_quyet='mo_ta' nhưng ket_cuc='PASS' "
                "— suất đó KHÔNG mua một phán quyết. DR-D4-10 §2.3 cấm đọc "
                "`DSR_adj` của nhóm C như một phán quyết"
            )

    # ── Khối xuất xứ ────────────────────────────────────────────────────
    if "provenance" not in d:
        loi.append("thiếu khối provenance (L-Z40 + MT-07)")
    else:
        loi.extend(
            f"provenance: {e}" for e in validate_provenance_tool_d(d["provenance"])
        )

    return loi


def _measured_to_dict(m: Measured[Any]) -> dict[str, Any]:
    """Ba trạng thái ra JSON. `value` chỉ có mặt khi `status == ok` — bất biến
    đó do `Measured.__post_init__` bảo đảm, ở đây chỉ chép lại."""
    return {"status": m.status.value, "value": m.value, "note": m.note}


def build_arm_record(
    *,
    arm: str,
    huong: str,
    n_phan_quyet: int,
    n_mo_ta: int,
    cua_so_phan_quyet: Sequence[tuple[date, date]],
    cua_so_mo_ta: tuple[date, date],
    chi_so: Mapping[str, Measured[Any]],
    ket_cuc: Measured[str],
    provenance: Provenance,
    trial_id: str | None = None,
) -> dict[str, Any]:
    """Dựng một bản ghi arm hợp lệ với `arm_result.schema.json`.

    🔴 **`pham_vi_phan_quyet` KHÔNG phải tham số.** Nó được suy từ `arm` qua
    `pham_vi_theo_arm()`, nên *"khai sai cờ phạm vi"* là **không biểu diễn
    được** ở đường này — cùng thủ pháp `TD-0127` đã dùng khi bỏ hẳn tham số
    `n_tai_sinh` khỏi `TrialLedger`: một phép kiểm có thể bị bỏ qua, một tham
    số không tồn tại thì không ai truyền vào được.

    Fail-closed: dựng xong **tự kiểm** bằng `validate_arm_record()` và raise
    nếu không hợp lệ. Một bản ghi kết quả D4 không hợp lệ mà vẫn được trả về
    là một bản ghi sẽ đi tiếp vào gate.
    """
    if n_phan_quyet > n_mo_ta:
        raise ArmRecordError(
            f"n_phan_quyet ({n_phan_quyet}) > n_mo_ta ({n_mo_ta}) — đoạn test là "
            "TẬP CON của toàn cửa sổ (MT-36)"
        )
    if not cua_so_phan_quyet:
        raise ArmRecordError(
            "cua_so_phan_quyet rỗng — `n_phan_quyet` phải có nguồn đếm được"
        )
    ban_ghi: dict[str, Any] = {
        "loai": "ARM_RESULT",
        "arm": arm,
        "huong": huong,
        "dataset": "WFO",
        "pham_vi_phan_quyet": pham_vi_theo_arm(arm),
        "n_phan_quyet": n_phan_quyet,
        "n_mo_ta": n_mo_ta,
        "cua_so_phan_quyet": [
            {"start": a.isoformat(), "end": b.isoformat()} for a, b in cua_so_phan_quyet
        ],
        "cua_so_mo_ta": {
            "start": cua_so_mo_ta[0].isoformat(),
            "end": cua_so_mo_ta[1].isoformat(),
        },
        "chi_so": {k: _measured_to_dict(v) for k, v in chi_so.items()},
        "ket_cuc": _measured_to_dict(ket_cuc),
        "trial_id": trial_id,
        "provenance": provenance.to_dict(),
    }
    loi = validate_arm_record(ban_ghi)
    if loi:
        raise ArmRecordError("bản ghi arm không hợp lệ: " + "; ".join(loi))
    return ban_ghi
