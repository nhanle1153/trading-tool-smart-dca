"""TD-0253 — danh sách ứng viên D5 (`DR-D5-01` §3.3) và phép kiểm một lần đặt chỗ B1.

════ Nguồn sự thật: CHÍNH tài liệu quyết định, có băm ════

Danh sách ứng viên KHÔNG được chép sang code hay YAML (MT-03: hai nguồn sự
thật trôi lệch nhau). Module này đọc khối JSON giữa hai dấu

    <!-- DR-D5-01:UNG_VIEN:BEGIN -->  …  <!-- DR-D5-01:UNG_VIEN:END -->

băm lại theo đúng quy tắc chuẩn hoá ghi trong DR, và so với dòng `sha256 = …`
của chính file. Lệch ⇒ raise. Sửa một ô trong bảng mà không sửa băm là bị bắt;
sửa cả hai thì `git log` của DR ghi lại — đúng thứ DR commit TRƯỚC mã để giữ.

════ Vì sao phép kiểm ở CỬA GHI, không ở audit ════

Chủ dự án chốt 16/09/2026 (Khối 19 chốt 10): một suất B1 sai giá trị mà đã vào
sổ thì đã chạm CALIB — sổ append-only không lùi được. Audit phát hiện SAU là
phát hiện một suất đã bẩn. `registry.TrialLedger.reserve()` gọi
`kiem_dat_cho_b1()` trước khi ghi dòng nào.

🔴 Module này KHÔNG import `tool_d.ledger.registry` (tránh vòng import) — nó
nhận bản chiếu theo hình dạng (`budget_line`, `param_under_test`,
`param_value`, `state`).
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

DEFAULT_DR_D5_01_PATH = Path("docs/decisions/DR-D5-01-pham-vi-ung-vien-luat-chon-calibration.md")

BUDGET_LINE_B1 = "B1"
PARAM_MOC = "D5_MOC"
"""Suất MỐC CHUNG (`DR-D5-01` §4, suất 1): mọi tham số ở giá trị hiện tại. `param_value = None`."""
PARAM_XAC_NHAN = "D5_XAC_NHAN"
"""Suất XÁC NHẬN GHÉP (§4, suất cuối): `param_value` = dict khoá → giá trị đã thắng."""

_KHOI_RE = re.compile(
    r"<!-- DR-D5-01:UNG_VIEN:BEGIN -->\s*```json\s*\n(?P<json>.*?)\n```\s*<!-- DR-D5-01:UNG_VIEN:END -->",
    re.DOTALL,
)
_BAM_RE = re.compile(r"`sha256 = (?P<bam>[0-9a-f]{64})`")


class UngVienError(ValueError):
    """Danh sách ứng viên đọc không được, băm lệch, hoặc một lần đặt chỗ B1 bị từ chối."""


@dataclass(frozen=True)
class ThamSoUngVien:
    nhom: str
    moc: Any
    thu: tuple[Any, ...]


@dataclass(frozen=True)
class BangUngVien:
    dr: str
    arm: str
    huong: str
    tran_suat: int
    tham_so: Mapping[str, ThamSoUngVien]
    sha256: str


def bam_chuan_hoa(obj: Any) -> str:
    """Quy tắc chuẩn hoá ghi ở `DR-D5-01` §3.3 — thay đổi hàm này là thay đổi băm của DR."""
    s = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def doc_bang_ung_vien(dr_path: Path = DEFAULT_DR_D5_01_PATH) -> BangUngVien:
    """Đọc + kiểm băm. Mọi lỗi ⇒ `UngVienError` (fail-closed)."""
    try:
        text = dr_path.read_text(encoding="utf-8")
    except OSError as e:
        raise UngVienError(f"không đọc được {dr_path}: {e}") from e
    khoi = list(_KHOI_RE.finditer(text))
    if len(khoi) != 1:
        raise UngVienError(f"{dr_path}: phải có ĐÚNG MỘT khối DR-D5-01:UNG_VIEN, thấy {len(khoi)}")
    bam_khai = _BAM_RE.findall(text)
    if len(bam_khai) != 1:
        raise UngVienError(f"{dr_path}: phải có ĐÚNG MỘT dòng `sha256 = …`, thấy {len(bam_khai)}")
    try:
        obj = json.loads(khoi[0].group("json"))
    except json.JSONDecodeError as e:
        raise UngVienError(f"khối ứng viên không phải JSON hợp lệ: {e}") from e
    bam = bam_chuan_hoa(obj)
    if bam != bam_khai[0]:
        raise UngVienError(
            f"BĂM LỆCH — khối ứng viên băm ra {bam}, DR khai {bam_khai[0]}. "
            "Bảng đã bị sửa mà không cập nhật băm (hoặc ngược lại)."
        )
    try:
        tham_so = {
            k: ThamSoUngVien(nhom=v["nhom"], moc=v["moc"], thu=tuple(v["thu"]))
            for k, v in obj["ung_vien"].items()
        }
        bang = BangUngVien(
            dr=obj["dr"], arm=obj["arm"], huong=obj["huong"], tran_suat=int(obj["tran_suat"]),
            tham_so=tham_so, sha256=bam,
        )
    except (KeyError, TypeError, ValueError) as e:
        raise UngVienError(f"khối ứng viên thiếu/sai trường: {e!r}") from e
    if obj.get("budget_line") != BUDGET_LINE_B1:
        raise UngVienError(f"khối ứng viên khai budget_line {obj.get('budget_line')!r}, phải là B1")
    return bang


def cung_gia_tri(a: Any, b: Any) -> bool:
    """So giá trị tham số: số so theo giá trị (1 == 1.0), còn lại so bằng `==`.
    `bool` KHÔNG được coi là số (True == 1 trong Python — sai nghĩa ở đây)."""
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(float(a), float(b), rel_tol=0.0, abs_tol=1e-12)
    return a == b


def _thuoc(v: Any, tap: Iterable[Any]) -> bool:
    return any(cung_gia_tri(v, x) for x in tap)


def _la_calib(p: Any) -> bool:
    """Bản chiếu thiếu `dataset` tính là CALIB — đếm THỪA vào trần D5 (chặn thừa, an toàn)
    chứ không bao giờ được nhận làm bằng chứng WFO (`DR-D9-01` §3.1 bảng, phương án a)."""
    return getattr(p, "dataset", None) in (None, "CALIB")


def _con_hieu_luc_b1(projections: Iterable[Any]) -> list[Any]:
    return [
        p for p in projections
        if getattr(p, "budget_line", None) == BUDGET_LINE_B1
        and getattr(getattr(p, "state", None), "value", None) != "REFUNDED"
    ]


def kiem_dat_cho_b1(
    projections: Iterable[Any],
    *,
    bang: BangUngVien,
    d4_complete: bool,
    d5_complete: bool,
    dataset: str,
    direction: str,
    param_under_test: str,
    param_value: Any,
) -> None:
    """Từ chối (raise `UngVienError`) một lần đặt chỗ B1 không thuộc `DR-D5-01`.

    Điều kiện, theo thứ tự rẻ → đắt: `d4_complete` (`DR-D5-01` §6.1, định nghĩa
    `DR-D4-11`) · `dataset == CALIB` · hướng khớp DR · tham số thuộc 7 khoá hoặc
    MỐC/XÁC NHẬN · giá trị thuộc danh sách · không trùng suất chưa hoàn trả ·
    MỐC ≤ 1, XÁC NHẬN ≤ 1 · tổng B1 CALIB chưa hoàn trả (RESERVED + CONSUMED) < trần.

    `dataset = WFO` (TD-0284, `DR-D9-01` §3/§3.1, phương án a — nhãn `B1` + `dataset`):
    nhánh RIÊNG, chặt hơn, xem `_kiem_dat_cho_b1_wfo()`. Nhánh CALIB giữ nguyên.
    """
    if d4_complete is not True:
        raise UngVienError("cổng D4 chưa đóng (`d4_complete` ≠ true) — KHÔNG đặt chỗ B1 (DR-D5-01 §6.1)")
    projections = list(projections)
    if dataset == "WFO":
        _kiem_dat_cho_b1_wfo(
            projections, bang=bang, d5_complete=d5_complete, direction=direction,
            param_under_test=param_under_test, param_value=param_value,
        )
        return
    if dataset != "CALIB":
        raise UngVienError(f"B1 chỉ chạy trên CALIB (DR-D5-01 §1), nhận {dataset!r}")
    if direction != bang.huong:
        raise UngVienError(f"B1 đợt này chỉ hướng {bang.huong} (DR-D5-01 §1), nhận {direction!r}")

    if param_under_test == PARAM_MOC:
        if param_value is not None:
            raise UngVienError(f"suất MỐC mang param_value = None, nhận {param_value!r}")
    elif param_under_test == PARAM_XAC_NHAN:
        if not isinstance(param_value, Mapping) or not param_value:
            raise UngVienError("suất XÁC NHẬN mang dict khoá → giá trị đã thắng, không rỗng")
        khac_moc = 0
        for k, v in param_value.items():
            if k not in bang.tham_so:
                raise UngVienError(f"XÁC NHẬN chứa tham số ngoài DR-D5-01: {k!r}")
            ts = bang.tham_so[k]
            if not _thuoc(v, (ts.moc, *ts.thu)):
                raise UngVienError(f"XÁC NHẬN: {k} = {v!r} không thuộc {{mốc}} ∪ thử {ts.thu!r}")
            khac_moc += not cung_gia_tri(v, ts.moc)
        if khac_moc == 0:
            raise UngVienError("XÁC NHẬN không đổi tham số nào khỏi mốc — không có gì để xác nhận (§5.3)")
    else:
        if param_under_test not in bang.tham_so:
            raise UngVienError(
                f"tham số {param_under_test!r} KHÔNG thuộc {len(bang.tham_so)} tham số calibrate của "
                f"DR-D5-01 §2.1 — gồm cả 5 tham số giữ FROZEN (§2.2)"
            )
        ts = bang.tham_so[param_under_test]
        if not _thuoc(param_value, ts.thu):
            raise UngVienError(
                f"{param_under_test} = {param_value!r} không thuộc giá trị thử {ts.thu!r} (DR-D5-01 §3). "
                "Giá trị mốc đi bằng suất D5_MOC, không đặt chỗ riêng."
            )

    # Trần 16 của D5 chỉ đếm suất CALIB — suất WFO của D9 có trần riêng (DR-D9-01 §3).
    con_hieu_luc = [p for p in _con_hieu_luc_b1(projections) if _la_calib(p)]
    for p in con_hieu_luc:
        if p.param_under_test != param_under_test:
            continue
        if param_under_test in (PARAM_MOC, PARAM_XAC_NHAN):
            raise UngVienError(f"đã có một suất {param_under_test} chưa hoàn trả ({p.trial_id}) — tối đa 1")
        if cung_gia_tri(p.param_value, param_value):
            raise UngVienError(
                f"trùng suất chưa hoàn trả {p.trial_id} cho {param_under_test} = {param_value!r} — "
                "không chạy lại 'vì nghi ngờ' (DR-D5-01 §4)"
            )
    if len(con_hieu_luc) >= bang.tran_suat:
        raise UngVienError(
            f"B1 đã có {len(con_hieu_luc)} suất chưa hoàn trả, trần DR-D5-01 là {bang.tran_suat}"
        )



def _kiem_dat_cho_b1_wfo(
    projections: list[Any],
    *,
    bang: BangUngVien,
    d5_complete: bool,
    direction: str,
    param_under_test: str,
    param_value: Any,
) -> None:
    """TD-0284 — suất B1 trên WFO cho D9 (`DR-D9-01` §3, §3.1, §6.1).

    Chuyển giao TƯỜNG MINH ≤ 16 suất B1 dư cho D9 (tiền lệ `DR-D4-01:113`: không
    tự động). Mỗi suất WFO phải chạy lại ĐÚNG một cấu hình đã CONSUMED trên CALIB:
    cổng vào `d5_complete` · hướng khớp DR · `(tham số, giá trị)` khớp một suất
    B1/CALIB/CONSUMED · không trùng suất WFO chưa hoàn trả · tổng WFO chưa hoàn
    trả < số suất CALIB đã CONSUMED.
    """
    if d5_complete is not True:
        raise UngVienError(
            "cổng vào D9 chưa mở (`d5_complete` ≠ true) — KHÔNG đặt chỗ B1 trên WFO (DR-D9-01 §6.1)"
        )
    if direction != bang.huong:
        raise UngVienError(f"B1/WFO đợt này chỉ hướng {bang.huong} (DR-D9-01 §1), nhận {direction!r}")
    calib = [
        p for p in projections
        if getattr(p, "budget_line", None) == BUDGET_LINE_B1
        and getattr(p, "dataset", None) == "CALIB"
        and getattr(getattr(p, "state", None), "value", None) == "CONSUMED"
    ]
    if not any(
        p.param_under_test == param_under_test and cung_gia_tri(p.param_value, param_value) for p in calib
    ):
        raise UngVienError(
            f"{param_under_test} = {param_value!r} không khớp suất B1 CALIB CONSUMED nào — tập CSCV là "
            "đúng các cấu hình D5 đã chạy (DR-D9-01 §2), không thêm cấu hình mới"
        )
    wfo = [p for p in _con_hieu_luc_b1(projections) if getattr(p, "dataset", None) == "WFO"]
    for p in wfo:
        if p.param_under_test == param_under_test and cung_gia_tri(p.param_value, param_value):
            raise UngVienError(
                f"trùng suất WFO chưa hoàn trả {p.trial_id} cho {param_under_test} = {param_value!r} — "
                "mỗi cấu hình đúng 1 suất WFO; chạy lại vì lỗi đi B3 (DR-D9-01 §3)"
            )
    if len(wfo) >= len(calib):
        raise UngVienError(
            f"B1/WFO đã có {len(wfo)} suất chưa hoàn trả, trần = số suất B1 CALIB CONSUMED = {len(calib)} "
            "(DR-D9-01 §3)"
        )


__all__ = [
    "BUDGET_LINE_B1",
    "BangUngVien",
    "DEFAULT_DR_D5_01_PATH",
    "PARAM_MOC",
    "PARAM_XAC_NHAN",
    "ThamSoUngVien",
    "UngVienError",
    "bam_chuan_hoa",
    "cung_gia_tri",
    "doc_bang_ung_vien",
    "kiem_dat_cho_b1",
]
