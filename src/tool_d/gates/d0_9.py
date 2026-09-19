"""`TD-0336` (`DR-D4-14`) — GATE D0.9 §10.2, phần DỰNG: khung hai nhánh + `L-Z57`.

Tầng THUẦN. Nó không tính một tiêu chí nào từ lệnh — nó nhận kết quả từng tiêu chí dưới dạng
`Measured[bool]` và trả lời hai câu của §10.2 (spec `:4251-4335`):

    Nhánh 1 — "hệ thống có đủ tốt để đem tiền thật ra không" (ngưỡng tuyệt đối)
    Nhánh 2 — "cấu hình nào" (chỉ chạy khi Nhánh 1 PASS)

════ Phạm vi đợt này — chủ dự án chốt 19/09/2026: "khung + L-Z57" ════

Hôm nay CHỈ `dsr_adj` có nguồn máy (bản ghi arm `Z0-T1`, `ablation/ban_ghi.py`). Tám tiêu chí
chặn còn lại chưa có đường trích từ lệnh thật; người gọi không đưa ⇒ `pending` ⇒ Nhánh 1
**không thể PASS**, và kết quả liệt kê đích danh cái thiếu. Một cổng tự điền "đạt" cho ô chưa
đo là PASS RỖNG dựng sẵn — đúng thứ `L-Z35` (ngưỡng trống = `+inf`) sinh ra để chặn.

════ Ba kết cục của Nhánh 1 — DIỄN GIẢI, ghi ra để cãi lại được ════

Spec: *"THIẾU MỘT TIÊU CHÍ Ở NHÁNH 1 → KHÔNG VÀO LIVE. Xử lý theo BA KẾT CỤC của DR-011"*.
  * **FAIL**         — có tiêu chí ĐO ĐƯỢC mà không đạt (kể cả `dsr_adj` ra FAIL theo `DR-D4-09`).
  * **INCONCLUSIVE** — không tiêu chí nào trượt, nhưng có ô chưa đo/đọc lỗi, hoặc `dsr_adj` ra
                       INCONCLUSIVE (thuế nhiễu > ngưỡng).
  * **PASS**         — đủ mọi ô, mọi ô đạt.
FAIL xét TRƯỚC INCONCLUSIVE: một tiêu chí đã trượt thì "không vào live" đã chắc, thêm mẫu cho ô
khác không đổi được điều đó.

════ `L-Z57` — không có đường nào từ gate này tới DỪNG DỰ ÁN ════

Kiểu kết quả **không có** giá trị "dừng dự án". Nhánh 1 không PASS ⇒ `buoc_tiep` trỏ `DR-011`
(nơi ba kết cục được xử lý; *"không vào live KHÔNG đồng nghĩa dừng dự án"*). Nhánh 2 ra `Z0` ⇒
*"DỰ ÁN TIẾP TỤC BÌNH THƯỜNG"* (spec `:4311-4313`). Đây là khoá chống hồi quy về lỗi v5.

════ Nhánh 2 trong D4 — đã chốt ở DR, module chỉ thi hành ════

`DR-D4-10` §2.4 điều 1: **mặc định `Z0` single-entry**; D4 không phán quyết câu DCA (DCA vào
Idea Queue, *"chưa từng được đo, không phải đã thất bại"*). `Z1`/`Z3b` đã bị cắt khỏi lô
(`DR-D4-12` §4) nên vế *"tốt nhất trong {Z3, Z3b}"* và điều kiện `Z1` của spec không có đầu vào.
⚠️ `Z0` ở đây là trục **DCA**; trục **trend** của arm sản xuất chưa chốt (`MT-35`).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from tool_d.gates.arm_record import ARM_MUA_PHAN_QUYET, validate_arm_record
from tool_d.gates.ket_cuc import KetCuc
from tool_d.measurement.tri_state import Measured, Status

#: Tiêu chí CHẶN của Nhánh 1, đúng thứ tự spec `:4258-4288`. `dsr_adj` đứng đầu và là ô DUY
#: NHẤT gate tự đọc (từ bản ghi arm); tám ô sau do người gọi đưa vào.
TIEU_CHI_NHANH_1: tuple[tuple[str, str], ...] = (
    ("dsr_adj", "DSR-adjusted expectancy ≥ ngưỡng (0,10; DR-D0PRE-03), N = 114"),
    ("h4d", "H4-D + H4-D-b PASS (§7.2/§7.5)"),
    ("liq_buffer", "liq_buffer_ratio trung bình ≥ 8 xuyên suốt mẫu (§6.4b)"),
    ("lo_don_lenh", "max_single_trade_loss / risk_budget ≤ 1.15"),
    ("skewness_z1", "skewness(cấu hình tốt nhất) không âm hơn skewness(Z1) quá 0.5 — ⚠️ Z1 đã cắt (DR-D4-12 §4), MT-53/TD-0289"),
    ("so_lenh_nam", "số lệnh/năm ≥ 150, MỖI HƯỚNG (MT-29) — SÀN, không phải trần"),
    ("time_stop", "tỉ lệ TIME_STOP trong dải 5%–25% (phân bố hold báo cáo cho mọi arm)"),
    ("h4_tp_fallback", "tỉ lệ TP_fallback (H-4) ≤ 40% (§11b.2)"),
    ("lz10_lz33", "L-Z10 → L-Z33 PASS (§9c.6, §4b.6, §4c.4)"),
)

#: Spec ghi rõ KHÔNG chặn: funding "không có ngưỡng chặn ở vòng này"; PBO "🟡 P1 … chưa dùng làm
#: điều kiện chặn ở D0.9 lần đầu". Nhận để báo cáo, không bao giờ đổi kết cục.
CHI_BAO_CAO: frozenset[str] = frozenset({"funding_paid_cumulative", "pbo"})

MA_TIEU_CHI: frozenset[str] = frozenset(ma for ma, _ in TIEU_CHI_NHANH_1)
_MA_NGOAI_DSR: tuple[str, ...] = tuple(ma for ma, _ in TIEU_CHI_NHANH_1 if ma != "dsr_adj")

CAU_HINH_MAC_DINH_NHANH_2 = "Z0"


class GateD09Error(ValueError):
    """Đầu vào sai HÌNH (khác 'chưa đủ điều kiện'). Fail-closed."""


@dataclass(frozen=True)
class KetQuaGateD09:
    nhanh_1: KetCuc
    tieu_chi: Mapping[str, Measured[bool]]
    truot: tuple[str, ...]
    thieu: tuple[str, ...]
    dsr_ket_cuc: Measured[str]
    vao_live: bool
    nhanh_2_da_chay: bool
    cau_hinh_chon: str | None
    buoc_tiep: str
    #: `L-Z57` — gate này KHÔNG có kết cục dừng dự án. Luôn `True`; là một trường để bộ đọc
    #: không phải suy nó từ văn bản.
    du_an_tiep_tuc: bool = True
    bao_cao: Mapping[str, Measured[Any]] = field(default_factory=dict)
    ghi_chep_thieu: tuple[str, ...] = ()


def _dsr_tu_ban_ghi(ban_ghi: Mapping[str, Any]) -> tuple[Measured[bool], Measured[str]]:
    loi = validate_arm_record(ban_ghi)
    if loi:
        raise GateD09Error(f"bản ghi ứng viên không hợp lệ: {loi}")
    if ban_ghi.get("arm") not in ARM_MUA_PHAN_QUYET or ban_ghi.get("pham_vi_phan_quyet") != "phan_quyet":
        raise GateD09Error(
            f"Nhánh 1 phán quyết trên arm {sorted(ARM_MUA_PHAN_QUYET)} (DR-D4-10 §2.1, MT-26 (C)); "
            f"nhận arm {ban_ghi.get('arm')!r} phạm vi {ban_ghi.get('pham_vi_phan_quyet')!r}"
        )
    kc = ban_ghi["ket_cuc"]
    if kc.get("status") != Status.OK.value:
        chua: Measured[Any] = Measured(status=Status(kc["status"]), value=None, note=kc.get("note"))
        return chua, chua
    gia_tri = kc["value"]
    kc_m: Measured[str] = Measured.ok(gia_tri)
    if gia_tri == KetCuc.PASS.value:
        return Measured.ok(True), kc_m
    if gia_tri == KetCuc.FAIL.value:
        return Measured.ok(False), kc_m
    return Measured.pending("dsr_adj INCONCLUSIVE — thuế nhiễu > ngưỡng (DR-D4-09 §2.2)"), kc_m


def danh_gia_gate_d09(
    *,
    ban_ghi_ung_vien: Mapping[str, Any],
    tieu_chi_khac: Mapping[str, Measured[bool]] | None = None,
    bao_cao: Mapping[str, Measured[Any]] | None = None,
    ket_luan_z0t1_vs_z0t2: str | None = None,
) -> KetQuaGateD09:
    """Hai nhánh §10.2 trên bản ghi ứng viên `Z0-T1` + các tiêu chí người gọi đo được.

    :param tieu_chi_khac: khoá ∈ tám tiêu chí ngoài `dsr_adj`. Khoá thiếu ⇒ `pending`.
        Khoá lạ ⇒ raise (gõ nhầm tên không được lặng lẽ thành "chưa đo").
    :param bao_cao: chỉ các khoá ở `CHI_BAO_CAO` — không đổi kết cục.
    :param ket_luan_z0t1_vs_z0t2: spec `:4320-4321` — *"có kết luận GHI LẠI … không được bỏ
        trống"*. Thiếu ⇒ ghi vào `ghi_chep_thieu`, không đổi kết cục Nhánh 1.
    """
    tieu_chi_khac = dict(tieu_chi_khac or {})
    bao_cao = dict(bao_cao or {})
    la = set(tieu_chi_khac) - set(_MA_NGOAI_DSR)
    if la:
        raise GateD09Error(
            f"tiêu chí lạ {sorted(la)} — hợp lệ: {list(_MA_NGOAI_DSR)} "
            "('dsr_adj' do gate tự đọc từ bản ghi arm, không nhận từ ngoài)"
        )
    la_bc = set(bao_cao) - CHI_BAO_CAO
    if la_bc:
        raise GateD09Error(f"khoá báo cáo lạ {sorted(la_bc)} — hợp lệ: {sorted(CHI_BAO_CAO)}")
    for ma, m in tieu_chi_khac.items():
        if not isinstance(m, Measured):
            raise GateD09Error(f"tiêu chí {ma}: phải là Measured[bool], nhận {type(m).__name__}")
        if m.status is Status.OK and not isinstance(m.value, bool):
            raise GateD09Error(f"tiêu chí {ma}: giá trị phải là bool, nhận {m.value!r}")

    dsr_o, dsr_kc = _dsr_tu_ban_ghi(ban_ghi_ung_vien)
    tieu_chi: dict[str, Measured[bool]] = {"dsr_adj": dsr_o}
    for ma in _MA_NGOAI_DSR:
        tieu_chi[ma] = tieu_chi_khac.get(ma) or Measured.pending(f"chưa có nguồn đo cho '{ma}' (DR-D4-14, TD-0336)")

    truot = tuple(ma for ma, _ in TIEU_CHI_NHANH_1 if tieu_chi[ma].status is Status.OK and tieu_chi[ma].value is False)
    thieu = tuple(ma for ma, _ in TIEU_CHI_NHANH_1 if tieu_chi[ma].status is not Status.OK)

    if truot:
        nhanh_1 = KetCuc.FAIL
    elif thieu:
        nhanh_1 = KetCuc.INCONCLUSIVE
    else:
        nhanh_1 = KetCuc.PASS

    ghi_chep_thieu = () if (ket_luan_z0t1_vs_z0t2 or "").strip() else ("ket_luan_z0t1_vs_z0t2",)

    if nhanh_1 is not KetCuc.PASS:
        chi_tiet = f"trượt {list(truot)}" if truot else f"chưa đủ {list(thieu)}"
        return KetQuaGateD09(
            nhanh_1=nhanh_1, tieu_chi=tieu_chi, truot=truot, thieu=thieu, dsr_ket_cuc=dsr_kc,
            vao_live=False, nhanh_2_da_chay=False, cau_hinh_chon=None,
            buoc_tiep=(
                f"Nhánh 1 = {nhanh_1.value} ({chi_tiet}) ⇒ KHÔNG VÀO LIVE; xử lý theo DR-011 (ba kết "
                "cục). 'Không vào live' KHÔNG đồng nghĩa 'dừng dự án' (spec §10.2). Nhánh 2 không chạy."
            ),
            bao_cao=bao_cao, ghi_chep_thieu=ghi_chep_thieu,
        )

    return KetQuaGateD09(
        nhanh_1=nhanh_1, tieu_chi=tieu_chi, truot=(), thieu=(), dsr_ket_cuc=dsr_kc,
        vao_live=True, nhanh_2_da_chay=True, cau_hinh_chon=CAU_HINH_MAC_DINH_NHANH_2,
        buoc_tiep=(
            "Nhánh 1 = PASS. Nhánh 2 ⇒ chọn Z0, hệ thống SINGLE-ENTRY neo zone — DỰ ÁN TIẾP TỤC BÌNH "
            "THƯỜNG (spec §10.2; DR-D4-10 §2.4 điều 1: D4 không phán quyết câu DCA, DCA vào Idea Queue). "
            "⚠️ Trục TREND của arm sản xuất chưa chốt (MT-35)."
        ),
        bao_cao=bao_cao, ghi_chep_thieu=ghi_chep_thieu,
    )


__all__ = [
    "CAU_HINH_MAC_DINH_NHANH_2",
    "CHI_BAO_CAO",
    "GateD09Error",
    "KetQuaGateD09",
    "MA_TIEU_CHI",
    "TIEU_CHI_NHANH_1",
    "danh_gia_gate_d09",
]
