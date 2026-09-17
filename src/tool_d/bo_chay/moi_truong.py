"""`TD-0312` — dựng thư mục chạy tạm + cấu hình phủ.

Khuôn lấy từ `_yaml_voi_arm()` (`docs/du-lieu-do/do_td0193_lenh_nam_explore.py:203`),
đã chạy thật, tổng quát hoá từ *"đổi đúng dòng `arm:`"* sang *"đổi một tập khoá
dotted bất kỳ"*.

🔴 **Phủ bằng THAY DÒNG VĂN BẢN, không `yaml.safe_load` → `yaml.dump`.** Dump sẽ
xoá sạch chú thích (mỗi khoá trong `tool_d_config.yaml` mang theo mã việc + mã DR
sinh ra nó) và làm `cfg.sha256` thành một con số **không truy ngược được về file đã
commit**. Xuất xứ của một phép đo mà không truy được về commit nào thì không còn là
xuất xứ.

🔑 **Phép thay dòng là một heuristic; thứ làm nó an toàn là HẬU KIỂM.** Sau khi ghi,
module này load lại bản phủ và khẳng định hai điều: (i) mọi khoá phủ có đúng giá trị
mới; (ii) **mọi khoá còn lại không đổi một giá trị nào**. Vế (ii) mới là vế đắt —
nó bắt được ca "phủ một dòng, lỡ trúng hai".
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tool_d.bo_chay.yeu_cau import BoChayError, gia_tri_yaml, ten_cap_freqtrade
from tool_d.config.loader import ToolDConfig, load_tool_d_config, resolve

TEN_FILE_CAU_HINH = "tool_d_config.yaml"


class MoiTruongError(BoChayError):
    """Không dựng được môi trường chạy đúng như khai — fail-closed."""


@dataclass(frozen=True)
class MoiTruongChay:
    """Một thư mục chạy đã sẵn sàng cho `freqtrade backtesting`.

    `thu_muc` là cwd của tiến trình con: `load_tool_d_config()` đọc
    `config/tool_d_config.yaml` **tương đối cwd** (`config/loader.py`), nên chép cả
    thư mục `config/` sang đây là cách đổi tham số mà KHÔNG chạm file trong repo.
    """

    thu_muc: Path
    config_freqtrade: Path
    userdir: Path
    cfg_phu: ToolDConfig
    sha256_phu: str


def _thay_mot_khoa(van_ban: str, dotted: str, value: Any) -> str:
    """Thay đúng MỘT dòng ứng với khoá lá của `dotted`, giữ nguyên thụt đầu dòng."""
    la = dotted.rsplit(".", 1)[-1]
    khop = [ln for ln in van_ban.splitlines() if ln.strip().startswith(f"{la}:")]
    if len(khop) != 1:
        raise MoiTruongError(
            f"khoá {dotted!r}: tìm thấy {len(khop)} dòng bắt đầu bằng {la!r} trong "
            f"{TEN_FILE_CAU_HINH}, cần đúng 1. Các dòng khớp: {khop}"
        )
    cu = khop[0]
    thut = cu[: len(cu) - len(cu.lstrip())]
    return van_ban.replace(cu, f"{thut}{la}: {gia_tri_yaml(value)}", 1)


def _moi_gia_tri(cfg: ToolDConfig) -> dict[str, Any]:
    """Làm phẳng cả bốn tầng thành `{'tier_x.a.b': giá trị}` để so từng khoá lá."""
    ra: dict[str, Any] = {}

    def _di(tien_to: str, nut: Any) -> None:
        if isinstance(nut, Mapping):
            for k, v in nut.items():
                _di(f"{tien_to}.{k}" if tien_to else str(k), v)
        else:
            ra[tien_to] = nut

    for ten in ("tier_a", "tier_b", "tier_frozen", "tier_c"):
        _di(ten, getattr(cfg, ten))
    return ra


def _hau_kiem(goc: ToolDConfig, phu: ToolDConfig, ghi_de: Mapping[str, Any]) -> None:
    """(i) khoá phủ mang giá trị mới; (ii) KHÔNG khoá nào khác đổi."""
    for dotted, value in ghi_de.items():
        thuc = resolve(phu, dotted)
        if thuc != value:
            raise MoiTruongError(
                f"phủ {dotted!r} = {value!r} nhưng đọc lại được {thuc!r} — cấu hình phủ không đúng"
            )

    truoc, sau = _moi_gia_tri(goc), _moi_gia_tri(phu)
    if set(truoc) != set(sau):
        raise MoiTruongError(
            f"cấu hình phủ làm MẤT/THÊM khoá: mất={sorted(set(truoc) - set(sau))}, "
            f"thêm={sorted(set(sau) - set(truoc))}"
        )
    ngoai_y_muon = {
        k: (truoc[k], sau[k]) for k in truoc if truoc[k] != sau[k] and k not in ghi_de
    }
    if ngoai_y_muon:
        raise MoiTruongError(
            f"cấu hình phủ đổi cả khoá KHÔNG được yêu cầu: {ngoai_y_muon} — "
            "phép thay dòng đã trúng nhầm chỗ"
        )


def dung_moi_truong(
    *,
    repo_dir: Path,
    goc: Path,
    ghi_de: Mapping[str, Any],
    ma_trong_ro: Sequence[str],
) -> MoiTruongChay:
    """Chép `config/` sang `goc`, áp `ghi_de`, ghi `cfg.json` cho Freqtrade.

    `ma_trong_ro` là danh sách mã **đã lấy từ `ro_cho_tap()`** — hàm này không tự
    đọc rổ ở đâu cả, nó chỉ đổi dạng tên và ghi vào `pair_whitelist`.
    """
    if not ma_trong_ro:
        raise MoiTruongError("danh sách mã rỗng — TỪ CHỐI dựng môi trường (backtest 0 mã là pass rỗng)")

    nguon_config = repo_dir / "config"
    if not (nguon_config / TEN_FILE_CAU_HINH).is_file():
        raise MoiTruongError(f"{nguon_config / TEN_FILE_CAU_HINH} không tồn tại")

    goc.mkdir(parents=True, exist_ok=True)
    dich_config = goc / "config"
    if dich_config.exists():
        shutil.rmtree(dich_config)
    shutil.copytree(nguon_config, dich_config)

    duong_yaml = dich_config / TEN_FILE_CAU_HINH
    van_ban = duong_yaml.read_text(encoding="utf-8")
    for dotted, value in ghi_de.items():
        van_ban = _thay_mot_khoa(van_ban, dotted, value)
    duong_yaml.write_text(van_ban, encoding="utf-8")

    cfg_goc = load_tool_d_config(nguon_config / TEN_FILE_CAU_HINH)
    cfg_phu = load_tool_d_config(duong_yaml)
    _hau_kiem(cfg_goc, cfg_phu, ghi_de)

    userdir = goc / "user_data"
    (userdir / "strategies").mkdir(parents=True, exist_ok=True)

    ft = json.loads((nguon_config / "freqtrade" / "config.json").read_text(encoding="utf-8"))
    ft["exchange"]["pair_whitelist"] = [ten_cap_freqtrade(m) for m in ma_trong_ro]
    ft["dry_run"] = True
    duong_ft = goc / "cfg.json"
    duong_ft.write_text(json.dumps(ft), encoding="utf-8")

    return MoiTruongChay(
        thu_muc=goc,
        config_freqtrade=duong_ft,
        userdir=userdir,
        cfg_phu=cfg_phu,
        sha256_phu=cfg_phu.sha256,
    )
