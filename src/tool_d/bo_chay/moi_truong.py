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


#: TD-0400 (`DR-D0-IQ0003` §4) — khoá Freqtrade mà một file phủ theo chiến lược ĐƯỢC chạm. Danh sách CHO PHÉP: khoá
#: `test_lz24` ghim (`trailing_stop`, `position_adjustment_enable`, `use_exit_signal`, `edge`, …) không nằm ở đây.
KHOA_PHU_CHO_PHEP = frozenset({"order_types", "order_time_in_force", "entry_pricing", "exit_pricing"})
THU_MUC_PHU = Path("freqtrade") / "phu"
#: Khoá chú thích/dẫn xuất của file phủ. Khoá `_…` lạ ⇒ từ chối (không lặng lẽ bỏ qua một ý định).
KHOA_PHU_META = frozenset({"_ghi_chu", "_vi_tu_khoa", "_stoploss_tu_khoa"})


def _ap_file_phu(ft: dict[str, Any], nguon_config: Path, chien_luoc: str, cfg_phu: ToolDConfig) -> None:
    """Áp `config/freqtrade/phu/<chien_luoc>.json` nếu có (ZA không có file ⇒ không đổi một bit).

    Khoá thường gộp NÔNG vào khối cùng tên (khoá không nhắc giữ nguyên, vd `stoploss_on_exchange`). `_ghi_chu` là
    chú thích; `_stoploss_tu_khoa` dựng `stoploss` tĩnh từ YAML (xem thân hàm); `_vi_tu_khoa`: ví mô phỏng = `resolve(cfg_phu, khoá) / tradable_balance_ratio`, để tiền giao dịch
    được ĐÚNG bằng vốn chiến lược khai trong YAML (N4) — ví chung 1000 × 0,75 = 750 là vốn của ZA. Khoá lạ ⇒ từ chối."""
    duong = nguon_config / THU_MUC_PHU / f"{chien_luoc}.json"
    if not duong.is_file():
        return
    phu = json.loads(duong.read_text(encoding="utf-8"))
    la = sorted(k for k in phu if k not in KHOA_PHU_CHO_PHEP | KHOA_PHU_META)
    if la:
        raise MoiTruongError(f"{duong}: khoá không được phủ {la} — chỉ nhận {sorted(KHOA_PHU_CHO_PHEP)}")
    for khoa in KHOA_PHU_CHO_PHEP & phu.keys():
        ft[khoa] = {**ft.get(khoa, {}), **phu[khoa]}
    if "_vi_tu_khoa" in phu:
        von = resolve(cfg_phu, phu["_vi_tu_khoa"])
        if von is None or not isinstance(von, (int, float)) or von <= 0:
            raise MoiTruongError(f"{phu['_vi_tu_khoa']} = {von!r} — vốn chiến lược {chien_luoc} chưa chốt (fail-closed)")
        ft["dry_run_wallet"] = float(von) / float(ft["tradable_balance_ratio"])
    if "_stoploss_tu_khoa" in phu:
        # Stop TĨNH của Freqtrade (nhãn `stop_loss`), không `custom_stoploss`: Freqtrade gắn nhãn `trailing_stop_loss`
        # cho mọi lần custom_stoploss dời stop khỏi mức ban đầu — đo được ở TD-0400, và nhãn đó nằm ngoài lớp
        # `CAN_RO_THEO_LICH` (`DR-CAN-RO-01` §3). Tỉ lệ stop của Freqtrade tính trên KÝ QUỸ ⇒ nhân đòn bẩy sàn.
        k = phu["_stoploss_tu_khoa"]
        pct, lev = resolve(cfg_phu, k["phan_tram"]), resolve(cfg_phu, k["don_bay_san"])
        if not all(isinstance(v, (int, float)) and v > 0 for v in (pct, lev)) or pct * lev >= 100:
            raise MoiTruongError(f"{duong}: stop {pct!r}% × đòn bẩy {lev!r} không dựng được stoploss hợp lệ")
        ft["stoploss"] = -float(pct) * float(lev) / 100


def dung_moi_truong(
    *,
    repo_dir: Path,
    goc: Path,
    ghi_de: Mapping[str, Any],
    ma_trong_ro: Sequence[str],
    chien_luoc: str | None = None,
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
    if chien_luoc is not None:
        _ap_file_phu(ft, nguon_config, chien_luoc, cfg_phu)
    duong_ft = goc / "cfg.json"
    duong_ft.write_text(json.dumps(ft), encoding="utf-8")

    return MoiTruongChay(
        thu_muc=goc,
        config_freqtrade=duong_ft,
        userdir=userdir,
        cfg_phu=cfg_phu,
        sha256_phu=cfg_phu.sha256,
    )
