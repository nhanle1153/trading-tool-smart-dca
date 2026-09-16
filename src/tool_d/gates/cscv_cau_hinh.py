"""TD-0281 — cấu hình CSCV của D9, đối chiếu khối băm trong `DR-D9-01` §4.5.

════ Ba nguồn, một sự thật ════

Mỗi con số CSCV có ĐÚNG MỘT chỗ được viết ra để dùng:

- `so_khoi`  → `tier_c.cscv.so_khoi` (N4);
- sàn lệnh   → `tier_c.wfo_folds.san_lenh_moi_fold` (DR-D3-01 §5.2 — dùng lại, không gõ lại 30);
- ngưỡng PBO → `gates/thresholds.PBO_MAX` (spec :4287).

`DR-D9-01` §4.5 chép lại chúng trong một khối JSON có băm — không để CODE đọc
số từ DR (MT-03: hai nguồn), mà để MÁY bắt chỗ lệch: đổi `so_khoi` trong YAML
mà không sửa DR, hay sửa DR mà không sửa băm ⇒ raise, trước khi một tổ hợp
nào được tính. DR commit TRƯỚC mã giữ phần còn lại (`git log`).

Khác `DR-D5-01` (danh sách ứng viên CHỈ sống trong DR): ở đây giá trị sống
trong YAML vì chúng là tham số vận hành N4 phải đọc được qua `resolve()`; DR
chỉ giữ bản chép đối chiếu.

🔴 Fail-closed toàn tuyến: DR đọc không được · băm lệch · thiếu khoá · S lẻ ·
S × độ dài khối ≠ độ dài WFO · YAML ≠ DR ⇒ `CSCVCauHinhError`.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Any

from tool_d.calibration.ung_vien import bam_chuan_hoa
from tool_d.config.loader import ToolDConfig, resolve
from tool_d.gates.thresholds import PBO_MAX
from tool_d.ledger.timerange import dataset_boundaries_from_config
from tool_d.wfo.folds import FoldConfigError, san_lenh_moi_fold

DEFAULT_DR_D9_01_PATH = Path("docs/decisions/DR-D9-01-wfo-cscv-pbo.md")

_KHOI_RE = re.compile(
    r"<!-- DR-D9-01:CSCV:BEGIN -->\s*```json\s*\n(?P<json>.*?)\n```\s*<!-- DR-D9-01:CSCV:END -->",
    re.DOTALL,
)
_BAM_RE = re.compile(r"`sha256 = (?P<bam>[0-9a-f]{64})`")

#: Khoá `tier_c.cscv` được phép. Khoá lạ ⇒ raise: một tham số CSCV mới phải đi
#: qua DR trước (DR-D9-01 §8), không mọc thêm trong YAML.
KHOA_HOP_LE: frozenset[str] = frozenset({"so_khoi"})


class CSCVCauHinhError(RuntimeError):
    """Cấu hình CSCV không dùng được hoặc lệch `DR-D9-01`. Fail-closed."""


@dataclass(frozen=True)
class CauHinhCSCV:
    so_khoi: int
    do_dai_khoi: timedelta
    san_lenh_moi_nua: int
    pbo_max: float
    t1: datetime
    t2: datetime
    bam_dr: str

    def moc_khoi(self) -> tuple[datetime, ...]:
        """`so_khoi + 1` mốc UTC-naive: `[t1, t1+L, …, t2]`."""
        return tuple(self.t1 + i * self.do_dai_khoi for i in range(self.so_khoi + 1))


def doc_khoi_dr(dr_path: Path = DEFAULT_DR_D9_01_PATH) -> tuple[dict[str, Any], str]:
    """Đọc khối `DR-D9-01:CSCV` + kiểm băm. Trả (obj, băm)."""
    try:
        text = dr_path.read_text(encoding="utf-8")
    except OSError as e:
        raise CSCVCauHinhError(f"không đọc được {dr_path}: {e}") from e
    khoi = list(_KHOI_RE.finditer(text))
    if len(khoi) != 1:
        raise CSCVCauHinhError(f"{dr_path}: phải có ĐÚNG MỘT khối DR-D9-01:CSCV, thấy {len(khoi)}")
    bam_khai = _BAM_RE.findall(text)
    if len(bam_khai) != 1:
        raise CSCVCauHinhError(f"{dr_path}: phải có ĐÚNG MỘT dòng `sha256 = …`, thấy {len(bam_khai)}")
    try:
        obj = json.loads(khoi[0].group("json"))
    except json.JSONDecodeError as e:
        raise CSCVCauHinhError(f"khối CSCV không phải JSON hợp lệ: {e}") from e
    bam = bam_chuan_hoa(obj)
    if bam != bam_khai[0]:
        raise CSCVCauHinhError(
            f"BĂM LỆCH — khối CSCV băm ra {bam}, DR khai {bam_khai[0]}. "
            "Khối đã bị sửa mà không cập nhật băm (hoặc ngược lại)."
        )
    return obj, bam


def _so_nguyen_duong(ten: str, v: Any) -> int:
    if not isinstance(v, int) or isinstance(v, bool) or v <= 0:
        raise CSCVCauHinhError(f"`{ten}` phải là số nguyên dương, nhận {v!r}")
    return v


def doc_cau_hinh_cscv(cfg: ToolDConfig, *, dr_path: Path = DEFAULT_DR_D9_01_PATH) -> CauHinhCSCV:
    """Đọc cấu hình CSCV từ YAML và đối chiếu từng giá trị với `DR-D9-01` §4.5."""
    obj, bam = doc_khoi_dr(dr_path)
    try:
        khoi_dr = obj["cscv"]
        so_khoi_dr = khoi_dr["so_khoi"]
        gio_dr = khoi_dr["do_dai_khoi_gio"]
        pbo_max_dr = khoi_dr["pbo_max"]
        nguon_san_dr = khoi_dr["san_lenh_moi_nua"]
    except (KeyError, TypeError) as e:
        raise CSCVCauHinhError(f"khối CSCV của DR thiếu trường: {e!r}") from e

    try:
        khoi = resolve(cfg, "tier_c.cscv")
    except KeyError as e:
        raise CSCVCauHinhError(
            "Thiếu `tier_c.cscv` trong tool_d_config.yaml — cấu hình CSCV phải đến từ cấu hình (N4)."
        ) from e
    la = set(khoi) - KHOA_HOP_LE
    if la:
        raise CSCVCauHinhError(f"`tier_c.cscv` có khoá ngoài DR-D9-01: {sorted(la)}")
    if "so_khoi" not in khoi:
        raise CSCVCauHinhError("Thiếu `tier_c.cscv.so_khoi`.")
    so_khoi = _so_nguyen_duong("tier_c.cscv.so_khoi", khoi["so_khoi"])
    if so_khoi % 2 != 0 or so_khoi < 2:
        raise CSCVCauHinhError(f"`so_khoi` phải chẵn và ≥ 2 (IS/OOS chia đôi), nhận {so_khoi}")
    if so_khoi != so_khoi_dr:
        raise CSCVCauHinhError(f"YAML so_khoi = {so_khoi} ≠ DR-D9-01 §4.5 so_khoi = {so_khoi_dr}")

    if nguon_san_dr != "tier_c.wfo_folds.san_lenh_moi_fold":
        raise CSCVCauHinhError(f"DR khai nguồn sàn {nguon_san_dr!r}, code đọc tier_c.wfo_folds.san_lenh_moi_fold")
    try:
        san = san_lenh_moi_fold(cfg)
    except (FoldConfigError, KeyError) as e:
        raise CSCVCauHinhError(f"không đọc được sàn lệnh: {e}") from e

    if PBO_MAX != pbo_max_dr:
        raise CSCVCauHinhError(f"thresholds.PBO_MAX = {PBO_MAX} ≠ DR-D9-01 §4.5 pbo_max = {pbo_max_dr}")

    wfo = dataset_boundaries_from_config(cfg)["WFO"]
    t1 = datetime.combine(wfo.start, time())
    t2 = datetime.combine(wfo.end, time())
    tong_gio = (t2 - t1) / timedelta(hours=1)
    gio = _so_nguyen_duong("do_dai_khoi_gio (DR)", gio_dr)
    if gio * so_khoi != tong_gio:
        raise CSCVCauHinhError(
            f"{so_khoi} khối × {gio} giờ = {gio * so_khoi} giờ ≠ cửa sổ WFO [{wfo.start}, {wfo.end}) "
            f"= {tong_gio:g} giờ. TỪ CHỐI — không tự co khối cho vừa (DR-D9-01 §8)."
        )
    return CauHinhCSCV(
        so_khoi=so_khoi,
        do_dai_khoi=timedelta(hours=gio),
        san_lenh_moi_nua=san,
        pbo_max=PBO_MAX,
        t1=t1,
        t2=t2,
        bam_dr=bam,
    )


__all__ = [
    "CSCVCauHinhError",
    "CauHinhCSCV",
    "DEFAULT_DR_D9_01_PATH",
    "KHOA_HOP_LE",
    "doc_cau_hinh_cscv",
    "doc_khoi_dr",
]
