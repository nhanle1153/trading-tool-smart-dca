"""TD-0329 (OQ-14a) — công cụ PHÁ-THẬT TRONG BỘ NHỚ.

"Kiểm có răng" (phá code thật, xem test có đỏ không) là kỷ luật chính của dự án, nhưng
trước đây làm bằng tay: sửa file trên đĩa, chạy, nhớ khôi phục. Cách đó (i) không tái
lập được sau này, (ii) để đường sản xuất ở trạng thái bị phá giữa chừng, (iii) dễ quên
khôi phục — đúng hình dạng lỗi mà `N12` sinh ra để chặn ở tầng git.

Công cụ này làm cùng việc mà **đĩa không đổi một byte**: đọc mã nguồn, đổi MỘT khối dòng
trong bản sao ở bộ nhớ, nạp bản đó vào `sys.modules` TRƯỚC khi pytest chạy, rồi chạy tập
test đã chỉ định. Phép phá được ghi thành đặc tả JSON (`tests/tools/specs/*.json`), nên
chạy lại được và tự phát hiện khi mã nguồn đã trôi khỏi đặc tả.

Dùng (trong Docker, N7), từ gốc repo::

    docker compose -f docker/docker-compose.yml run --rm --entrypoint python tests \\
        tests/tools/mutate_in_memory.py --spec tests/tools/specs/td0320_moi_hon.json --variant all

Đặc tả gồm ``module``, ``file``, ``khoi_dong`` (các dòng của khối, đã ``strip``; dòng đầu
phải xuất hiện đúng MỘT lần trong file), ``bien_the`` (tên → dòng thay thế, ``null`` là
đối chứng không phá), ``tests``, và tuỳ chọn ``ky_vong`` (``"xanh"``/``"do"`` cho từng
biến thể, viết TRƯỚC khi chạy) cùng ``ky_vong_do_gom`` (các test PHẢI đỏ).

Một biến thể có thể là ĐỐI TƯỢNG ``{"khoi_dong": [...], "thay": ...}`` để phá một khối KHÁC
với khối mặc định — một đặc tả phủ được nhiều vị trí phá (TD-0331 dùng 6 vị trí).

🔴 **Không phải entrypoint thứ 9** (``L-Z36``): nằm ở ``tests/tools/``, không ở
``entrypoints/``, và không ghi dữ liệu thị trường hay sổ nào.

⚠️ **Giới hạn khai trước:** chỉ phá được test CHẠY TRONG CÙNG TIẾN TRÌNH. Test dùng tiến
trình con (backtest thật) KHÔNG thấy bản phá trong bộ nhớ — đừng đưa chúng vào ``tests``
của đặc tả và đừng kết luận gì về chúng từ đây.

⚠️ Mỗi tiến trình chỉ chạy MỘT biến thể: nạp một module bản phá vào ``sys.modules`` làm ô
nhiễm trạng thái, nên ``--variant all`` sinh một tiến trình con cho mỗi biến thể.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import subprocess
import sys
import types
from dataclasses import dataclass
from pathlib import Path


class DotBienError(RuntimeError):
    """Đặc tả không khớp mã nguồn thật, hoặc biến thể không đổi được gì."""


@dataclass(frozen=True)
class DacTa:
    module: str
    file: str
    khoi_dong: tuple[str, ...]
    bien_the: dict
    tests: tuple[str, ...]
    ky_vong: dict
    ky_vong_do_gom: dict
    mo_ta: str = ""

    @classmethod
    def tu_json(cls, path: Path) -> "DacTa":
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        thieu = [k for k in ("module", "file", "khoi_dong", "bien_the", "tests") if k not in d]
        if thieu:
            raise DotBienError(f"đặc tả thiếu khoá: {thieu}")
        if not d["khoi_dong"]:
            raise DotBienError("khoi_dong rỗng")
        return cls(
            module=d["module"],
            file=d["file"],
            khoi_dong=tuple(d["khoi_dong"]),
            bien_the=dict(d["bien_the"]),
            tests=tuple(d["tests"]),
            ky_vong=dict(d.get("ky_vong") or {}),
            ky_vong_do_gom={k: list(v) for k, v in (d.get("ky_vong_do_gom") or {}).items()},
            mo_ta=d.get("mo_ta", ""),
        )


# ── phần THUẦN: không đụng đĩa, không đụng sys.modules ──────────────────────────────


def tim_khoi(lines: list[str], khoi_dong: tuple[str, ...]) -> int:
    """Chỉ số dòng đầu của khối. Dòng đầu phải xuất hiện đúng MỘT lần, và cả khối phải
    khớp từng dòng (đã ``strip``) — mã nguồn trôi khỏi đặc tả thì lỗi ngay, không phá bừa."""
    dau = khoi_dong[0]
    ung_vien = [i for i, dong in enumerate(lines) if dong.strip() == dau]
    if len(ung_vien) != 1:
        raise DotBienError(f"dòng đầu {dau!r} xuất hiện {len(ung_vien)} lần (cần đúng 1)")
    i = ung_vien[0]
    if i + len(khoi_dong) > len(lines):
        raise DotBienError(f"khối {len(khoi_dong)} dòng vượt quá cuối file (bắt đầu ở dòng {i + 1})")
    thuc = tuple(lines[i + k].strip() for k in range(len(khoi_dong)))
    if thuc != tuple(khoi_dong):
        raise DotBienError(f"khối ở dòng {i + 1} lệch đặc tả: thực tế {thuc!r}")
    return i


def dot_bien(src: str, dac_ta: DacTa, ten_bien_the: str) -> str:
    """Bản sao mã nguồn đã đổi khối theo biến thể. ``None`` = đối chứng (trả nguyên xi,
    nhưng VẪN kiểm đặc tả khớp mã thật). Giữ thụt lề và ký tự xuống dòng của dòng đầu."""
    if ten_bien_the not in dac_ta.bien_the:
        raise DotBienError(f"không có biến thể {ten_bien_the!r}; có: {sorted(dac_ta.bien_the)}")
    lines = src.splitlines(keepends=True)
    # Khối MẶC ĐỊNH luôn được kiểm (kể cả với M0): đặc tả lệch mã thật thì báo, không phá bừa.
    tim_khoi(lines, dac_ta.khoi_dong)
    thay = dac_ta.bien_the[ten_bien_the]
    if thay is None:
        return src
    khoi = dac_ta.khoi_dong
    if isinstance(thay, dict):
        # Biến thể có khối RIÊNG: một đặc tả phủ nhiều vị trí phá, thay vì mỗi vị trí một file.
        khoi = tuple(thay["khoi_dong"])
        thay = thay["thay"]
    i = tim_khoi(lines, khoi)
    moi = [thay] if isinstance(thay, str) else list(thay)
    dau = lines[i]
    thut = dau[: len(dau) - len(dau.lstrip())]
    eol = dau[len(dau.rstrip("\r\n")):] or "\n"
    lines[i : i + len(khoi)] = [thut + m + eol for m in moi]
    ket = "".join(lines)
    if ket == src:
        raise DotBienError(f"biến thể {ten_bien_the!r} không đổi gì so với mã gốc")
    return ket


def nap_ban_pha(ten_module: str, src: str, duong_dan: str) -> types.ModuleType:
    """Nạp ``src`` làm module ``ten_module`` trong ``sys.modules``.

    Phải gọi TRƯỚC khi import bất kỳ thứ gì phụ thuộc vào module này: ai đã ``from … import``
    bản gốc sẽ giữ tham chiếu cũ và không thấy bản phá — nên từ chối nếu module đã được nạp.
    Module vào ``sys.modules`` TRƯỚC khi ``exec`` (``dataclass`` tra module qua đó)."""
    cha, _, con = ten_module.rpartition(".")
    goi_cha = importlib.import_module(cha) if cha else None
    if ten_module in sys.modules:
        raise DotBienError(
            f"{ten_module} đã được nạp trước — module khác có thể đã giữ tham chiếu bản gốc"
        )
    mod = types.ModuleType(ten_module)
    mod.__file__ = os.path.abspath(duong_dan)
    mod.__package__ = cha
    sys.modules[ten_module] = mod
    try:
        exec(compile(src, duong_dan, "exec"), mod.__dict__)
    except BaseException:
        sys.modules.pop(ten_module, None)
        raise
    if goi_cha is not None:
        setattr(goi_cha, con, mod)
    return mod


_RE_FAILED = re.compile(r"^FAILED (\S+)", re.M)
_RE_TOM_TAT = re.compile(r"^(?:=+ )?(\d+ (?:failed|passed|error).*?) in [\d.]+s", re.M)


def tom_tat(dau_ra: str) -> dict:
    """``{"do": [nodeid…], "tom_tat": "1 failed, 58 passed"}`` từ đầu ra pytest ``-q -rf``."""
    khop = _RE_TOM_TAT.findall(dau_ra)
    tt = khop[-1] if khop else ""
    if not tt:
        cuoi = [l for l in dau_ra.splitlines() if re.search(r"\b(passed|failed|error)", l)]
        tt = cuoi[-1].strip() if cuoi else "không đọc được tóm tắt"
    return {"do": _RE_FAILED.findall(dau_ra), "tom_tat": tt}


# ── phần chạy ───────────────────────────────────────────────────────────────────────


def chay_mot_bien_the(spec_path: Path, ten: str, root: Path) -> int:
    """Chạy MỘT biến thể trong tiến trình này; trả mã thoát của pytest."""
    os.chdir(root)
    sys.path.insert(0, str(root / "src"))
    dac_ta = DacTa.tu_json(Path(spec_path))
    src = (root / dac_ta.file).read_text(encoding="utf-8")  # CHỈ ĐỌC — công cụ không ghi file nào
    ban_pha = dot_bien(src, dac_ta, ten)
    nap_ban_pha(dac_ta.module, ban_pha, str(root / dac_ta.file))

    import pytest

    return int(pytest.main([*dac_ta.tests, "-p", "no:cacheprovider", "-q", "-rf", "--no-header"]))


def chay_tat_ca(spec_path: Path, root: Path, in_ra) -> int:
    """Mỗi biến thể một tiến trình con; in bảng; so với ``ky_vong`` nếu có.

    Mã thoát: 0 = mọi biến thể khớp dự đoán (hoặc không có dự đoán); 1 = có lệch; 2 = lỗi công cụ."""
    dac_ta = DacTa.tu_json(Path(spec_path))
    lech: list[str] = []
    in_ra(f"== {dac_ta.module} · {dac_ta.file} · {len(dac_ta.tests)} file test")
    for ten in dac_ta.bien_the:
        kq = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--spec", str(spec_path),
             "--variant", ten, "--root", str(root)],
            capture_output=True, text=True, encoding="utf-8",
        )
        if kq.returncode not in (0, 1):
            in_ra(f"== {ten}: LỖI CÔNG CỤ (rc={kq.returncode})")
            in_ra((kq.stdout + kq.stderr)[-1500:])
            return 2
        tt = tom_tat(kq.stdout)
        ket_qua = "xanh" if kq.returncode == 0 else "do"
        in_ra(f"== {ten}: {ket_qua.upper()} ({tt['tom_tat']})")
        for nodeid in tt["do"]:
            in_ra(f"     đỏ: {nodeid}")
        if ten in dac_ta.ky_vong and dac_ta.ky_vong[ten] != ket_qua:
            lech.append(f"{ten}: dự đoán {dac_ta.ky_vong[ten]}, thực tế {ket_qua}")
        thieu = [n for n in dac_ta.ky_vong_do_gom.get(ten, []) if n not in tt["do"]]
        if thieu:
            lech.append(f"{ten}: test PHẢI đỏ mà không đỏ: {thieu}")
    if lech:
        in_ra("== LỆCH DỰ ĐOÁN:")
        for dong in lech:
            in_ra(f"   - {dong}")
        return 1
    in_ra("== khớp dự đoán" if dac_ta.ky_vong or dac_ta.ky_vong_do_gom else "== (đặc tả không có dự đoán)")
    return 0


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Phá-thật trong bộ nhớ (TD-0329) — đĩa không đổi.")
    ap.add_argument("--spec", required=True, help="đường dẫn đặc tả JSON")
    ap.add_argument("--variant", required=True, help="tên biến thể, hoặc 'all'")
    ap.add_argument("--root", default=".", help="gốc repo (mặc định: thư mục hiện tại)")
    a = ap.parse_args(argv)
    root = Path(a.root).resolve()
    spec = Path(a.spec)
    if not spec.is_absolute():
        spec = (root / spec).resolve()
    try:
        if a.variant == "all":
            return chay_tat_ca(spec, root, print)
        return chay_mot_bien_the(spec, a.variant, root)
    except DotBienError as loi:
        print(f"LỖI ĐẶC TẢ: {loi}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
