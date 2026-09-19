"""`TD-0336` → `TD-0341` (`DR-D4-14`) — GATE D0.9 §10.2 cho D4: khung hai nhánh + `L-Z57`.

🔄 **TD-0341 viết lại module này (19/09/2026).** Bản TD-0336 tự khai danh sách tiêu chí và nhận `Measured[bool]` —
tức một bộ đánh giá Nhánh 1 THỨ HAI song song với `thresholds.evaluate_branch1()` + `d9_gate.danh_gia_cong_d9()`.
Hai bộ ngưỡng song song sớm muộn trôi lệch (N1/MT-03). Nay:

* **Ngưỡng + danh sách tiêu chí số** = của CHUNG D4/D9: `thresholds.evaluate_branch1()` và `d9_gate.TIEU_CHI_KHAI`.
  Module này KHÔNG chứa một con số ngưỡng nào.
* **Phạm vi áp dụng** theo `DR-D9-02` (b′) đi qua tham số `arm` của `evaluate_branch1` — arm ứng viên `Z0-T1` là
  entry đơn ⇒ skewness-so-`Z1` "không áp dụng", liệt kê tường minh.
* **Chỉ D4 có thêm** hai tiêu chí dạng "bộ test PASS" mà `evaluate_branch1` cố ý không kiểm (docstring của nó):
  `h4d` (H4-D + H4-D-b) và `lz10_lz33` — nhận `Measured[bool]` do người gọi chạy bộ test đưa vào.
* D4 GHI PBO, không chặn (`pbo_chan=False`, spec :4326, `DR-D9-01` §7).

⚠️ Phần tách ba kết cục (không đạt / chưa đo / còn lại) có mặt ở đây và ở `d9_gate` — ~10 dòng. Không gộp được vì
`test_td0285` khoá bằng AST rằng `d9_gate` gọi TRỰC TIẾP `evaluate_branch1(pbo_chan=True)`; gộp là phải sửa khẳng
định một test khoá cũ (điều kiện dừng `DR-D4-14` §7). Đổi lại: `test_lz57_gate_d09` có ca ĐỐI CHIẾU D4↔D9 — cùng đầu
vào ⇒ cùng kết cục, nên hai nơi không thể trôi lệch mà không đỏ.

════ Ba kết cục — cùng luật `d9_gate` (DIỄN GIẢI, cãi lại được) ════

    có tiêu chí ĐO ĐƯỢC mà không đạt            ⇒ FAIL
    không, nhưng có ô chưa đo / DSR INCONCLUSIVE ⇒ INCONCLUSIVE
    còn lại                                      ⇒ PASS

════ `L-Z57` — không có đường nào từ gate này tới DỪNG DỰ ÁN ════

Kiểu kết quả không có giá trị "dừng dự án". Nhánh 1 không PASS ⇒ `buoc_tiep` trỏ `DR-011` (*"không vào live KHÔNG
đồng nghĩa dừng dự án"*). Nhánh 2 ra `Z0` ⇒ *"DỰ ÁN TIẾP TỤC BÌNH THƯỜNG"* (spec `:4311-4313`).

════ Nhánh 2 trong D4 — đã chốt ở DR, module chỉ thi hành ════

`DR-D4-10` §2.4 điều 1: mặc định `Z0` single-entry; D4 không phán quyết câu DCA. ⚠️ `Z0` ở đây là trục DCA; trục
trend của arm sản xuất chưa chốt (`MT-35`).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from tool_d.gates import thresholds
from tool_d.gates.arm_record import ARM_MUA_PHAN_QUYET, validate_arm_record
from tool_d.gates.d9_gate import TIEU_CHI_DSR, TIEU_CHI_KHAI
from tool_d.gates.ket_cuc import KetCuc
from tool_d.measurement.tri_state import Measured, Status

#: Hai tiêu chí Nhánh 1 dạng "bộ test PASS" — `evaluate_branch1` không kiểm chúng (docstring của nó).
TIEU_CHI_BO_TEST: tuple[str, ...] = ("h4d", "lz10_lz33")

#: Toàn bộ tiêu chí CHẶN của Nhánh 1 ở D4, theo thứ tự báo cáo. Ghép từ nguồn chung, không khai lại.
TIEU_CHI_NHANH_1: tuple[str, ...] = (TIEU_CHI_DSR, *TIEU_CHI_KHAI, *TIEU_CHI_BO_TEST)

#: Spec ghi rõ KHÔNG chặn ở D4: funding (*"không có ngưỡng chặn ở vòng này"*), PBO (🟡 P1).
CHI_BAO_CAO: frozenset[str] = frozenset({"funding_paid_cumulative", "pbo"})

CAU_HINH_MAC_DINH_NHANH_2 = "Z0"


class GateD09Error(ValueError):
    """Đầu vào sai HÌNH (khác 'chưa đủ điều kiện'). Fail-closed."""


@dataclass(frozen=True)
class KetQuaGateD09:
    nhanh_1: KetCuc
    truot: tuple[str, ...]
    thieu: tuple[str, ...]
    khong_ap_dung: tuple[str, ...]
    dsr_ket_cuc: Measured[str]
    vao_live: bool
    nhanh_2_da_chay: bool
    cau_hinh_chon: str | None
    buoc_tiep: str
    #: `L-Z57` — gate này KHÔNG có kết cục dừng dự án. Luôn `True`.
    du_an_tiep_tuc: bool = True
    bao_cao: Mapping[str, Measured[Any]] = field(default_factory=dict)
    ghi_chep_thieu: tuple[str, ...] = ()


def _kiem_ban_ghi(ban_ghi: Mapping[str, Any]) -> str:
    loi = validate_arm_record(ban_ghi)
    if loi:
        raise GateD09Error(f"bản ghi ứng viên không hợp lệ: {loi}")
    arm = ban_ghi.get("arm")
    if arm not in ARM_MUA_PHAN_QUYET or ban_ghi.get("pham_vi_phan_quyet") != "phan_quyet":
        raise GateD09Error(
            f"Nhánh 1 phán quyết trên arm {sorted(ARM_MUA_PHAN_QUYET)} (DR-D4-10 §2.1, MT-26 (C)); "
            f"nhận arm {arm!r} phạm vi {ban_ghi.get('pham_vi_phan_quyet')!r}"
        )
    return str(arm)


def _kiem_khoa(ten: str, dau_vao: Mapping[str, Any], hop_le: tuple[str, ...] | frozenset[str]) -> None:
    la = set(dau_vao) - set(hop_le)
    if la:
        raise GateD09Error(f"{ten}: khoá lạ {sorted(la)} — hợp lệ: {sorted(hop_le)}")
    for k, m in dau_vao.items():
        if not isinstance(m, Measured):
            raise GateD09Error(f"{ten}[{k}]: phải là Measured, nhận {type(m).__name__} (N6)")


def danh_gia_gate_d09(
    *,
    ban_ghi_ung_vien: Mapping[str, Any],
    chi_so: Mapping[str, Measured[float]] | None = None,
    bo_test: Mapping[str, Measured[bool]] | None = None,
    bao_cao: Mapping[str, Measured[Any]] | None = None,
    ket_luan_z0t1_vs_z0t2: str | None = None,
) -> KetQuaGateD09:
    """Hai nhánh §10.2 trên bản ghi ứng viên `Z0-T1`.

    :param chi_so: khoá ∈ `d9_gate.TIEU_CHI_KHAI` (số). Khoá thiếu ⇒ `pending`. Khoá lạ ⇒ raise.
    :param bo_test: khoá ∈ `TIEU_CHI_BO_TEST`, giá trị `Measured[bool]` từ lần chạy bộ test thật.
    :param bao_cao: chỉ `CHI_BAO_CAO` — không đổi kết cục.
    :param ket_luan_z0t1_vs_z0t2: spec `:4320-4321` *"không được bỏ trống"* ⇒ thiếu thì ghi vào `ghi_chep_thieu`.
    """
    arm = _kiem_ban_ghi(ban_ghi_ung_vien)
    chi_so = dict(chi_so or {})
    bo_test = dict(bo_test or {})
    bao_cao = dict(bao_cao or {})
    _kiem_khoa("chi_so", chi_so, TIEU_CHI_KHAI)
    _kiem_khoa("bo_test", bo_test, TIEU_CHI_BO_TEST)
    _kiem_khoa("bao_cao", bao_cao, CHI_BAO_CAO)
    for k, m in bo_test.items():
        if m.status is Status.OK and not isinstance(m.value, bool):
            raise GateD09Error(f"bo_test[{k}]: giá trị phải là bool, nhận {m.value!r}")

    metrics: dict[str, float] = {}
    chua_do: list[str] = []
    khong_dat: list[str] = []

    # DSR — kết cục đã phân loại trong bản ghi arm (`ablation/ban_ghi.py` → `phan_loai_ket_cuc`).
    kc_tho = ban_ghi_ung_vien["ket_cuc"]
    dsr_kc: Measured[str] = (
        Measured.ok(kc_tho["value"]) if kc_tho.get("status") == Status.OK.value
        else Measured(status=Status(kc_tho["status"]), value=None, note=kc_tho.get("note"))
    )
    dsr_adj = ban_ghi_ung_vien["chi_so"].get("dsr_adj", {})
    if dsr_kc.value in (KetCuc.PASS.value, KetCuc.FAIL.value) and dsr_adj.get("status") == Status.OK.value:
        metrics[TIEU_CHI_DSR] = float(dsr_adj["value"])
    else:
        chua_do.append(TIEU_CHI_DSR)

    for k in TIEU_CHI_KHAI:
        m = chi_so.get(k)
        if m is not None and m.status is Status.OK:
            metrics[k] = float(m.value)
        else:
            chua_do.append(k)

    kq = thresholds.evaluate_branch1(metrics, pbo_chan=False, arm=arm)
    khong_dat += [k for k in kq.failed_criteria if k not in chua_do]
    chua_do = [k for k in chua_do if k not in kq.khong_ap_dung]

    # Kết cục DSR của bản ghi phải KHỚP ngưỡng dùng chung — bản ghi dựng với ngưỡng khác là lỗi lắp ráp.
    if dsr_kc.value == KetCuc.PASS.value and TIEU_CHI_DSR in khong_dat:
        raise GateD09Error("bản ghi ghi DSR PASS nhưng dsr_adj < DSR_ADJ_EXPECTANCY_MIN — ngưỡng lệch nguồn chung")
    if dsr_kc.value == KetCuc.FAIL.value and TIEU_CHI_DSR not in khong_dat:
        raise GateD09Error("bản ghi ghi DSR FAIL nhưng dsr_adj ≥ DSR_ADJ_EXPECTANCY_MIN — ngưỡng lệch nguồn chung")

    for k in TIEU_CHI_BO_TEST:
        m = bo_test.get(k)
        if m is None or m.status is not Status.OK:
            chua_do.append(k)
        elif m.value is False:
            khong_dat.append(k)

    thu_tu = {k: i for i, k in enumerate(TIEU_CHI_NHANH_1)}
    truot = tuple(sorted(khong_dat, key=thu_tu.__getitem__))
    thieu = tuple(sorted(chua_do, key=thu_tu.__getitem__))
    nhanh_1 = KetCuc.FAIL if truot else (KetCuc.INCONCLUSIVE if thieu else KetCuc.PASS)
    ghi_chep_thieu = () if (ket_luan_z0t1_vs_z0t2 or "").strip() else ("ket_luan_z0t1_vs_z0t2",)
    chung = dict(
        nhanh_1=nhanh_1, truot=truot, thieu=thieu, khong_ap_dung=kq.khong_ap_dung, dsr_ket_cuc=dsr_kc,
        bao_cao=bao_cao, ghi_chep_thieu=ghi_chep_thieu,
    )

    if nhanh_1 is not KetCuc.PASS:
        chi_tiet = f"trượt {list(truot)}" if truot else f"chưa đủ {list(thieu)}"
        return KetQuaGateD09(
            **chung, vao_live=False, nhanh_2_da_chay=False, cau_hinh_chon=None,
            buoc_tiep=(
                f"Nhánh 1 = {nhanh_1.value} ({chi_tiet}) ⇒ KHÔNG VÀO LIVE; xử lý theo DR-011 (ba kết "
                "cục). 'Không vào live' KHÔNG đồng nghĩa 'dừng dự án' (spec §10.2). Nhánh 2 không chạy."
            ),
        )
    return KetQuaGateD09(
        **chung, vao_live=True, nhanh_2_da_chay=True, cau_hinh_chon=CAU_HINH_MAC_DINH_NHANH_2,
        buoc_tiep=(
            "Nhánh 1 = PASS. Nhánh 2 ⇒ chọn Z0, hệ thống SINGLE-ENTRY neo zone — DỰ ÁN TIẾP TỤC BÌNH "
            "THƯỜNG (spec §10.2; DR-D4-10 §2.4 điều 1: D4 không phán quyết câu DCA, DCA vào Idea Queue). "
            "⚠️ Trục TREND của arm sản xuất chưa chốt (MT-35)."
        ),
    )


__all__ = [
    "CAU_HINH_MAC_DINH_NHANH_2",
    "CHI_BAO_CAO",
    "GateD09Error",
    "KetQuaGateD09",
    "TIEU_CHI_BO_TEST",
    "TIEU_CHI_NHANH_1",
    "danh_gia_gate_d09",
]
