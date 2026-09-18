"""Seal có KHAI RỔ không, và khai có đúng không — TD-0309, giải `MT-60` (`DR-LOCKBOX-01`).

`MT-60`: `lockbox_seal_1.json` băm 510 file = 102 mã của `config/pool.yaml` (rổ đo 09/2026, CUỐI giai
đoạn lockbox), trong khi rổ đúng cho LOCKBOX là rổ tại `T2` (`config/pool_t2.yaml`, 86 mã). Lệch gần
một nửa, theo chiều PASS, đúng tại cổng cuối. `verify_seal()` là danh sách ĐÓNG — nó băm lại đúng các
file đã ghi và KHÔNG nhìn tới danh sách mã nào, nên seal sai rổ PASS `L-Z14` mãi mãi.

Ba trạng thái (N6), không gộp:
- `KHAI_DUNG`  — seal khai rổ, và rổ khai khớp dữ liệu seal lẫn file rổ trên đĩa;
- `KHAI_SAI`   — seal khai rổ nhưng không khớp (kèm lý do);
- `KHONG_KHAI` — seal không mang khoá `pool` (seal cũ). KHÔNG phải "đạt": bên gọi phải xử tường
  minh, chỉ chấp nhận khi tên seal nằm trong danh sách miễn của cấu hình.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

from tool_d.config.loader import load_tool_d_config, resolve
from tool_d.data.pool_t1_du_lieu import SAU_LOAI_FILE, ten_file
from tool_d.lockbox.seal import discover_seals, verify_all_seals

KHAI_DUNG = "khai_dung"
KHAI_SAI = "khai_sai"
KHONG_KHAI = "khong_khai"

#: Cùng mẫu `pool_t1._TEN_FILE_FUTURES` — tên file dữ liệu Freqtrade futures.
_TEN_FILE = re.compile(r"^(?P<base>.+)_USDT_USDT-[^/]+\.feather$")

KHOA_MIEN_KHAI = "tier_c.lockbox.seal_mien_khai_pool"


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ma_trong_data_hashes(data_hashes: Mapping[str, str]) -> tuple[set[str], list[str]]:
    """(tập mã suy từ tên file, các tên file không đọc ra mã được)."""
    ma: set[str] = set()
    la: list[str] = []
    for ten in data_hashes:
        m = _TEN_FILE.match(ten)
        if m:
            ma.add(f"{m.group('base')}USDT")
        else:
            la.append(ten)
    return ma, sorted(la)


def kiem_pool_seal(seal: Mapping[str, Any], *, repo_dir: Path = Path(".")) -> tuple[str, list[str]]:
    """Trạng thái khai rổ của một seal (dict đã đọc từ JSON). Không I/O ngoài đọc file rổ."""
    pool = seal.get("pool")
    if pool is None:
        return KHONG_KHAI, []

    loi: list[str] = []
    data_hashes: Mapping[str, str] = seal.get("data_hashes") or {}
    trading = list(pool.get("trading") or [])
    if not trading:
        return KHAI_SAI, ["pool.trading rỗng — seal khai rổ nhưng không có mã nào"]

    # (a) tập mã trong dữ liệu seal == tập mã rổ khai.
    ma, la = ma_trong_data_hashes(data_hashes)
    if la:
        loi.append(f"{len(la)} tên file không đọc ra mã được: {la[:5]}")
    thieu, thua = sorted(set(trading) - ma), sorted(ma - set(trading))
    if thieu:
        loi.append(f"{len(thieu)} mã trong rổ khai nhưng seal KHÔNG có dữ liệu: {thieu[:10]}")
    if thua:
        loi.append(f"{len(thua)} mã seal có dữ liệu nhưng KHÔNG thuộc rổ khai: {thua[:10]}")

    # (b) mỗi mã đủ đúng các loại file của kế hoạch dữ liệu WFO (`DR-LOCKBOX-01` Q6: lockbox chạy
    # cùng cấu hình D5/D9) — lấy từ `SAU_LOAI_FILE`, không chép danh sách thứ hai (MT-03).
    thieu_file = sorted(ten_file(sym, lf) for sym in trading for lf in SAU_LOAI_FILE if ten_file(sym, lf) not in data_hashes)
    if thieu_file:
        loi.append(f"thiếu {len(thieu_file)} file bắt buộc (6 loại/mã, có 5m): {thieu_file[:5]}")

    # (c)(d)(e) file rổ trên đĩa: còn nguyên byte như lúc niêm phong, đúng mốc, đúng danh sách.
    duong = repo_dir / str(pool.get("file", ""))
    if not duong.is_file():
        loi.append(f"file rổ {pool.get('file')!r} không tồn tại")
    else:
        if _sha256(duong) != pool.get("sha256"):
            loi.append(f"{pool.get('file')}: sha256 KHÁC lúc niêm phong — rổ đã bị sửa sau khi niêm phong")
        noi_dung = yaml.safe_load(duong.read_text(encoding="utf-8")) or {}
        if noi_dung.get(f"moc_{pool.get('moc')}") is None:
            loi.append(f"{pool.get('file')} không mang khoá moc_{pool.get('moc')} — không phải rổ của mốc khai")
        if list(noi_dung.get("trading") or []) != trading:
            loi.append(f"{pool.get('file')}: danh sách trading KHÁC danh sách seal khai")

    return (KHAI_SAI, loi) if loi else (KHAI_DUNG, [])


def doc_mien_khai_pool(config_path: Path = Path("config/tool_d_config.yaml")) -> frozenset[str]:
    """Tên seal được miễn khai rổ — đọc từ cấu hình (`tier_c`, đổi = DR). Thiếu khoá ⇒ rỗng: không
    có miễn trừ nào, tức mọi seal không khai rổ đều là lỗi (fail-closed)."""
    try:
        v = resolve(load_tool_d_config(config_path), KHOA_MIEN_KHAI)
    except (KeyError, TypeError):
        return frozenset()
    return frozenset(v or ())


@dataclass(frozen=True)
class KetQuaLockbox:
    loi_bam: tuple[str, ...]
    loi_ro: tuple[str, ...]
    #: Seal được MIỄN khai rổ — in ra DÒNG RIÊNG, không trộn vào PASS (không phải "đạt").
    ghi_chu_mien: tuple[str, ...]

    @property
    def dat(self) -> bool:
        return not (self.loi_bam or self.loi_ro)


def verify_lockbox(
    lockbox_dir: Path,
    data_dir: Path,
    *,
    repo_dir: Path = Path("."),
    mien_khai_pool: frozenset[str] | None = None,
) -> KetQuaLockbox:
    """Kiểm TOÀN DIỆN lockbox: băm (`L-Z14`, qua `verify_all_seals` nguyên vẹn) + rổ (`MT-60`).

    Seal không khai rổ là LỖI, trừ khi tên nó nằm trong danh sách miễn của cấu hình — và ngay cả
    khi được miễn, nó vẫn hiện thành một ghi chú riêng chứ không lặng lẽ thành PASS.
    """
    mien = doc_mien_khai_pool(repo_dir / "config" / "tool_d_config.yaml") if mien_khai_pool is None else mien_khai_pool
    loi_ro: list[str] = []
    ghi_chu: list[str] = []
    for sp in discover_seals(lockbox_dir):
        try:
            d = json.loads(sp.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            loi_ro.append(f"{sp.name}: không đọc được JSON — không xét được rổ: {exc}")
            continue
        trang_thai, loi = kiem_pool_seal(d, repo_dir=repo_dir)
        if trang_thai == KHAI_SAI:
            loi_ro += [f"{sp.name}: {x}" for x in loi]
        elif trang_thai == KHONG_KHAI:
            if sp.name in mien:
                ghi_chu.append(
                    f"{sp.name}: KHÔNG khai rổ — MIỄN theo cấu hình ({KHOA_MIEN_KHAI}). "
                    "Đây KHÔNG phải 'đạt': seal này không chứng minh được nó niêm phong đúng rổ."
                )
            else:
                loi_ro.append(
                    f"{sp.name}: KHÔNG khai rổ và KHÔNG nằm trong danh sách miễn — không biết seal "
                    "niêm phong rổ nào (MT-60)"
                )
    return KetQuaLockbox(
        loi_bam=tuple(verify_all_seals(lockbox_dir, data_dir)),
        loi_ro=tuple(loi_ro),
        ghi_chu_mien=tuple(ghi_chu),
    )
